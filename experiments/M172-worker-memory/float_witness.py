from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import negative_control as output_control


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
PATCH = LANE / "float-witness.patch"
OUT = LANE / "out" / "float-witness"
RECORD = LANE / "results" / "float-witness.json"
WITNESS_RE = re.compile(
    r"^M172 f32 witness : fnv1a128=([0-9A-F]{32}) samples=([0-9]+)$",
    re.MULTILINE,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path, block_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def compact_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value["updated_utc"] = utc_now()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, indent=2, sort_keys=True, allow_nan=False)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def git_text(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "--no-pager", *args],
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed with {result.returncode}: "
            f"{(result.stderr or result.stdout).strip()}"
        )
    return result.stdout.strip()


def load_harness() -> ModuleType:
    path = output_control.HARNESS_PATH
    spec = importlib.util.spec_from_file_location("m172_float_harness", path)
    require(spec is not None and spec.loader is not None, f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def build_paths(arm: str) -> dict[str, Path]:
    root = OUT / "builds" / arm
    target = root / "target"
    return {
        "root": root,
        "archive": root / "source.tar",
        "source": root / "source",
        "target": target,
        "target_binary": target / "release" / "strehl.exe",
        "binary": root / "bin" / "strehl.exe",
        "log": root / "build.log",
    }


def build_arm(arm: str, commit: str) -> dict[str, Any]:
    paths = build_paths(arm)
    if paths["root"].exists():
        shutil.rmtree(paths["root"])
    paths["source"].mkdir(parents=True)
    archive_command = [
        "git",
        "-C",
        str(ROOT),
        "--no-pager",
        "archive",
        "--format=tar",
        f"--output={paths['archive']}",
        commit,
    ]
    print(f"[build] {arm}: archive {commit}", flush=True)
    result = subprocess.run(
        archive_command,
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(
        result.returncode == 0,
        f"git archive failed: {(result.stderr or result.stdout).strip()}",
    )
    with tarfile.open(paths["archive"], "r") as bundle:
        bundle.extractall(paths["source"], filter="data")

    apply_command = [
        "git",
        "apply",
        "--whitespace=nowarn",
        str(PATCH.resolve()),
    ]
    apply_env = os.environ.copy()
    apply_env["GIT_CEILING_DIRECTORIES"] = str(paths["source"].parent.resolve())
    result = subprocess.run(
        apply_command,
        cwd=paths["source"],
        env=apply_env,
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(
        result.returncode == 0,
        f"float witness patch failed on {arm}: "
        f"{(result.stderr or result.stdout).strip()}",
    )
    patched_source = (
        paths["source"] / "crates" / "strehl-cli" / "src" / "merge_cmd.rs"
    )

    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(paths["target"].resolve())
    env["CARGO_INCREMENTAL"] = "0"
    env["STREHL_BUILD_ID"] = commit
    env["CARGO_TERM_COLOR"] = "never"
    command = [
        "cargo",
        "build",
        "--release",
        "--locked",
        "--package",
        "strehl-cli",
        "--manifest-path",
        str(paths["source"] / "Cargo.toml"),
    ]
    paths["log"].parent.mkdir(parents=True, exist_ok=True)
    print(f"[build] {arm}: cargo build --release --locked", flush=True)
    with paths["log"].open("w", encoding="utf-8", newline="\n") as log:
        log.write(f"source_commit={commit}\n")
        log.write(f"patch_sha256={sha256_file(PATCH)}\n")
        log.write(f"CARGO_TARGET_DIR={env['CARGO_TARGET_DIR']}\n")
        log.write(f"CARGO_INCREMENTAL={env['CARGO_INCREMENTAL']}\n")
        log.write(f"STREHL_BUILD_ID={env['STREHL_BUILD_ID']}\n")
        log.write("$ " + subprocess.list2cmdline(command) + "\n\n")
        log.flush()
        result = subprocess.run(
            command,
            cwd=paths["source"],
            env=env,
            text=True,
            errors="replace",
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    if result.returncode:
        tail = paths["log"].read_text(encoding="utf-8", errors="replace")[-6000:]
        raise RuntimeError(f"{arm} diagnostic build failed:\n{tail}")
    build_log = paths["log"].read_text(encoding="utf-8", errors="replace")
    require(
        "Compiling strehl-cli" in build_log,
        f"{arm} build log does not prove strehl-cli was rebuilt",
    )
    require(paths["target_binary"].is_file(), f"{arm} binary was not built")
    paths["binary"].parent.mkdir(parents=True)
    shutil.copy2(paths["target_binary"], paths["binary"])
    binary_sha256 = sha256_file(paths["binary"])
    version = subprocess.run(
        [str(paths["binary"]), "--version"],
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(version.returncode == 0, f"{arm} diagnostic --version failed")
    version_output = "\n".join(
        value.strip() for value in (version.stdout, version.stderr) if value.strip()
    )
    require(commit in version_output, f"{arm} build ID is not the pinned commit")
    return {
        "arm": arm,
        "source_commit": commit,
        "source_tree": git_text("rev-parse", f"{commit}^{{tree}}"),
        "source_method": "git archive",
        "source_archive_sha256": sha256_file(paths["archive"]),
        "patch": str(PATCH),
        "patch_sha256": sha256_file(PATCH),
        "patched_merge_cmd_sha256": sha256_file(patched_source),
        "build_command": command,
        "build_environment": {
            "CARGO_TARGET_DIR": env["CARGO_TARGET_DIR"],
            "CARGO_INCREMENTAL": "0",
            "STREHL_BUILD_ID": commit,
        },
        "build_log": str(paths["log"]),
        "build_log_sha256": sha256_file(paths["log"]),
        "compile_line_seen": True,
        "binary": str(paths["binary"]),
        "binary_bytes": paths["binary"].stat().st_size,
        "binary_sha256": binary_sha256,
        "version_output": version_output,
        "completed_utc": utc_now(),
    }


def validate_build(build: dict[str, Any], arm: str, commit: str) -> None:
    require(build["arm"] == arm, f"{arm} build arm mismatch")
    require(build["source_commit"] == commit, f"{arm} source commit mismatch")
    require(build["patch_sha256"] == sha256_file(PATCH), f"{arm} patch changed")
    binary = Path(build["binary"])
    require(binary.is_file(), f"{arm} diagnostic binary is missing")
    require(
        sha256_file(binary) == build["binary_sha256"],
        f"{arm} diagnostic binary changed",
    )


def plans() -> list[dict[str, Any]]:
    rows = [
        {
            "run_id": f"pre-n16-off-w{worker}-probe-on",
            "arm": "pre",
            "limit": 16,
            "alignment": "off",
            "workers": worker,
            "probe": "on",
        }
        for worker in output_control.WORKERS
    ]
    rows.append(
        {
            "run_id": "pre-n16-off-w4-probe-off",
            "arm": "pre",
            "limit": 16,
            "alignment": "off",
            "workers": 4,
            "probe": "off",
        }
    )
    for arm in ("pre", "post"):
        rows.extend(
            {
                "run_id": f"{arm}-n33-on-w{worker}-probe-on",
                "arm": arm,
                "limit": 33,
                "alignment": "on",
                "workers": worker,
                "probe": "on",
            }
            for worker in (1, 16)
        )
    require(len(rows) == 10, "unexpected float-witness plan count")
    return rows


def protocol() -> dict[str, Any]:
    return {
        "schema": "M172-float-witness-v1",
        "question": (
            "Does worker-dependent regrouping change f32 merge output before "
            "demosaic and u16 quantization?"
        ),
        "instrument": {
            "location": (
                "immediately after BandMerge::finish and before demosaic/u16 encoding"
            ),
            "input": (
                "plane count, each plane length, then every f32::to_bits() value "
                "in plane-major order, serialized little-endian"
            ),
            "hash": "FNV-1a-128",
            "environment": "STREHL_M172_FLOAT_WITNESS=1",
            "patch": str(PATCH),
            "patch_sha256": sha256_file(PATCH),
            "observer_inertness": (
                "N=16 alignment-off pre W4 is rendered with the probe on and off; "
                "both full TIFF and pixel SHA-256 must match each other and the "
                "unmodified production binary."
            ),
        },
        "expectations": {
            "pre_n16_worker_spread": (
                "At least two f32 fingerprints across W1/W2/W4/W8/W16."
            ),
            "pre_n16_w1_w16_structural_null": (
                "W1 and W16 remain equal because W16 owns one frame per chunk."
            ),
            "pre_n33_aligned_red": "W1 and W16 f32 fingerprints differ.",
            "post_n33_aligned_green": "W1 and W16 f32 fingerprints match.",
        },
        "configuration": output_control.protocol()["configuration"],
        "input": output_control.protocol()["input"],
        "sidecar": {
            "path": str(output_control.SIDECAR_N33),
            "sha256": output_control.SIDECAR_N33_SHA256,
        },
        "plans": plans(),
    }


def production_reference() -> dict[tuple[str, int, str, int], dict[str, str]]:
    data = json.loads(output_control.RECORD.read_text(encoding="utf-8"))
    require(
        data["protocol_sha256"] == compact_sha256(data["protocol"]),
        "output-control protocol hash is invalid",
    )
    result = {}
    for row in data["records"]:
        key = (row["arm"], row["limit"], row["alignment"], row["workers"])
        result[key] = {
            "pixel_sha256": row["pixel_sha256"],
            "output_sha256": row["output_sha256"],
        }
    return result


def summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    fingerprints = {
        row["run_id"]: row["f32_fingerprint"]
        for row in records
        if row["probe"] == "on"
    }
    pre_n16 = [
        row
        for row in records
        if row["arm"] == "pre"
        and row["limit"] == 16
        and row["probe"] == "on"
    ]
    pre_n33 = [
        row
        for row in records
        if row["arm"] == "pre" and row["limit"] == 33
    ]
    post_n33 = [
        row
        for row in records
        if row["arm"] == "post" and row["limit"] == 33
    ]
    probe_on = next(
        row
        for row in records
        if row["run_id"] == "pre-n16-off-w4-probe-on"
    )
    probe_off = next(
        row
        for row in records
        if row["run_id"] == "pre-n16-off-w4-probe-off"
    )
    result = {
        "f32_fingerprint_by_run": fingerprints,
        "pre_n16_distinct_f32": len(
            {row["f32_fingerprint"] for row in pre_n16}
        ),
        "pre_n16_w1_w16_match": (
            next(row for row in pre_n16 if row["workers"] == 1)["f32_fingerprint"]
            == next(row for row in pre_n16 if row["workers"] == 16)[
                "f32_fingerprint"
            ]
        ),
        "pre_n33_w1_w16_differ": (
            pre_n33[0]["f32_fingerprint"] != pre_n33[1]["f32_fingerprint"]
        ),
        "post_n33_w1_w16_match": (
            post_n33[0]["f32_fingerprint"] == post_n33[1]["f32_fingerprint"]
        ),
        "probe_on_off_pixel_match": (
            probe_on["pixel_sha256"] == probe_off["pixel_sha256"]
        ),
        "probe_on_off_tiff_match": (
            probe_on["output_sha256"] == probe_off["output_sha256"]
        ),
        "all_outputs_match_unmodified_binary": all(
            row["matches_unmodified_production"] for row in records
        ),
    }
    result["all_expectations_pass"] = (
        result["pre_n16_distinct_f32"] >= 2
        and result["pre_n16_w1_w16_match"]
        and result["pre_n33_w1_w16_differ"]
        and result["post_n33_w1_w16_match"]
        and result["probe_on_off_pixel_match"]
        and result["probe_on_off_tiff_match"]
        and result["all_outputs_match_unmodified_binary"]
    )
    return result


def run() -> int:
    output_control.validate_inputs()
    registered = protocol()
    protocol_sha256 = compact_sha256(registered)
    if RECORD.exists():
        record = json.loads(RECORD.read_text(encoding="utf-8"))
        require(
            record["protocol_sha256"] == protocol_sha256,
            "existing float record belongs to another protocol",
        )
    else:
        record = {
            "schema": "M172-float-witness-record-v1",
            "created_utc": utc_now(),
            "protocol": registered,
            "protocol_sha256": protocol_sha256,
            "builds": {},
            "records": [],
            "summary": None,
        }
        atomic_write(RECORD, record)

    for arm, commit in (
        ("pre", output_control.PRE_COMMIT),
        ("post", output_control.POST_COMMIT),
    ):
        if arm not in record["builds"]:
            record["builds"][arm] = build_arm(arm, commit)
            atomic_write(RECORD, record)
        validate_build(record["builds"][arm], arm, commit)

    harness = load_harness()
    references = production_reference()
    completed = {row["run_id"] for row in record["records"]}
    for sequence, plan in enumerate(registered["plans"]):
        if plan["run_id"] in completed:
            continue
        destination = OUT / "runs" / f"{plan['run_id']}.tiff"
        cache = OUT / "cache" / plan["run_id"]
        temp = OUT / "temp" / plan["run_id"]
        for path in (
            destination,
            destination.with_suffix(".tiff.stdout.log"),
            destination.with_suffix(".tiff.stderr.log"),
        ):
            path.unlink(missing_ok=True)
        build = record["builds"][plan["arm"]]
        fixed_env = (
            {"STREHL_M172_FLOAT_WITNESS": "1"}
            if plan["probe"] == "on"
            else {}
        )
        required = output_control.required_stderr(plan)
        if plan["probe"] == "on":
            required.append("M172 f32 witness : fnv1a128=")
        print(f"[{sequence + 1:02d}/{len(registered['plans']):02d}] {plan['run_id']}")
        try:
            observed = harness.run_once(
                exe=Path(build["binary"]),
                stack=output_control.STACK,
                limit=plan["limit"],
                workers=plan["workers"],
                destination=destination,
                cache=cache,
                temp=temp,
                flags=list(output_control.FLAGS),
                sidecar=(
                    output_control.SIDECAR_N33
                    if plan["alignment"] == "on"
                    else None
                ),
                align_off=plan["alignment"] == "off",
                fixed_env=fixed_env,
                required_log_substrings=required,
                kind="float-witness",
                repetition=None,
                sweep="prequantization",
                measured_commit=(
                    output_control.PRE_COMMIT
                    if plan["arm"] == "pre"
                    else output_control.POST_COMMIT
                ),
                external_busy_max=1.0,
            )
            require(observed["valid"], str(observed["invalid_reasons"]))
            stderr_path = destination.with_suffix(".tiff.stderr.log")
            stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
            matches = WITNESS_RE.findall(stderr)
            if plan["probe"] == "on":
                require(len(matches) == 1, "expected exactly one f32 witness")
                fingerprint, sample_count = matches[0]
            else:
                require(not matches, "probe-off run emitted an f32 witness")
                fingerprint, sample_count = None, None
            key = (
                plan["arm"],
                plan["limit"],
                plan["alignment"],
                plan["workers"],
            )
            reference = references[key]
            matches_production = (
                observed["pixel_sha256"] == reference["pixel_sha256"]
                and observed["output_sha256"] == reference["output_sha256"]
            )
            require(
                matches_production,
                f"{plan['run_id']} diagnostic changed the production output",
            )
            row = {
                **plan,
                **observed,
                "sequence_index": sequence,
                "f32_fingerprint": fingerprint,
                "f32_sample_count": (
                    int(sample_count) if sample_count is not None else None
                ),
                "unmodified_reference": reference,
                "matches_unmodified_production": matches_production,
                "output_retained": False,
            }
            row["record_sha256"] = compact_sha256(row)
            record["records"].append(row)
            atomic_write(RECORD, record)
        finally:
            destination.unlink(missing_ok=True)

    record["summary"] = summary(record["records"])
    atomic_write(RECORD, record)
    require(
        record["summary"]["all_expectations_pass"],
        f"float-witness expectations failed: {record['summary']}",
    )
    print(json.dumps(record["summary"], indent=2))
    return 0


def self_test() -> int:
    line = "M172 f32 witness : fnv1a128=0123456789ABCDEF0123456789ABCDEF samples=42"
    assert WITNESS_RE.findall(line) == [
        ("0123456789ABCDEF0123456789ABCDEF", "42")
    ]
    mutated = line.replace("samples=42", "sample_count=42")
    assert not WITNESS_RE.findall(mutated)
    assert len(plans()) == 10
    print("float_witness.py self-test: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    return self_test() if args.self_test else run()


if __name__ == "__main__":
    raise SystemExit(main())
