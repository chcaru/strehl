from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from types import ModuleType
from typing import Any


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
HARNESS_PATH = ROOT / "experiments" / "m12-scorecard" / "m12-harness.py"
OUT = LANE / "out" / "negative-control"
RECORD = LANE / "results" / "negative-control.json"
STACK = Path(r"D:\personal\macro\bee-1-cpl")
SIDECAR_N33 = (
    ROOT
    / "experiments"
    / "m12-scorecard"
    / "out"
    / "campaign-8009447e-m139"
    / "cache"
    / "n33"
    / "bee-1-cpl-1e602b3b331cbbea.warpmap.txt"
)
PRE_COMMIT = "1a6fd10c94dcb4b780f6af78c46c62a156c39b71"
POST_COMMIT = "a97275817c58e164f75c7cd3d80ca99444a2a145"
PRE_BINARY = LANE / "out" / "builds" / "pre" / "bin" / "strehl.exe"
POST_BINARY = LANE / "out" / "builds" / "post" / "bin" / "strehl.exe"
PRE_BINARY_SHA256 = (
    "5C87BE23B654373192B4A561C232779A870ED1614C0BDD69EF9284376D854A93"
)
POST_BINARY_SHA256 = (
    "0EC15D05CCA90352101BC07088A29D75E64450DC678C5607BA90A778D0BF4E96"
)
SIDECAR_N33_SHA256 = (
    "A4B99B954EF98C0065FC35A36203545AEEF9A50997BC6B53F68BF859D9CE79DF"
)
WORKERS = (1, 2, 4, 8, 16)
FLAGS = (
    "--merge",
    "pyramid",
    "--pyramid-gate",
    "2.0",
    "--resampler",
    "catmull-rom",
    "--cover",
    "scale",
    "--linear-srgb",
    "--demosaic",
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


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "m172_negative_control_harness",
        HARNESS_PATH,
    )
    require(spec is not None and spec.loader is not None, "could not load M12 harness")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def make_plan(
    *,
    arm: str,
    limit: int,
    aligned: bool,
    workers: int,
    axis: str,
) -> dict[str, Any]:
    alignment = "on" if aligned else "off"
    return {
        "run_id": f"{arm}-n{limit}-{alignment}-w{workers}",
        "arm": arm,
        "source_commit": PRE_COMMIT if arm == "pre" else POST_COMMIT,
        "limit": limit,
        "alignment": alignment,
        "workers": workers,
        "axis": axis,
    }


def plans() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(
        make_plan(
            arm="pre",
            limit=16,
            aligned=False,
            workers=worker,
            axis="worker-spread",
        )
        for worker in WORKERS
    )
    rows.extend(
        make_plan(
            arm="pre",
            limit=17,
            aligned=False,
            workers=worker,
            axis="raise-n-by-one",
        )
        for worker in (1, 16)
    )
    rows.extend(
        make_plan(
            arm="pre",
            limit=33,
            aligned=False,
            workers=worker,
            axis="raise-n",
        )
        for worker in (1, 16)
    )
    rows.extend(
        make_plan(
            arm="pre",
            limit=33,
            aligned=True,
            workers=worker,
            axis="alignment-and-worker-spread",
        )
        for worker in WORKERS
    )
    rows.extend(
        make_plan(
            arm="post",
            limit=33,
            aligned=True,
            workers=worker,
            axis="repaired-control",
        )
        for worker in WORKERS
    )
    require(
        len({row["run_id"] for row in rows}) == len(rows),
        "run IDs are not unique",
    )
    return rows


def protocol() -> dict[str, Any]:
    return {
        "schema": "M172-negative-control-v1",
        "question": (
            "Can the exact pre-D9 binary produce distinct output hashes under an "
            "admissible worker-count configuration?"
        ),
        "pre_registration": {
            "original_gate": (
                "N=16, alignment off, pre W1 pixel hash must differ from pre W16"
            ),
            "structural_null_prediction": (
                "At N=16/W16, ceil(N/workers)=1. Absorbing one-frame partials "
                "left-to-right is predicted to reproduce W1's frame order, so this "
                "specific pair may be incapable of exposing regrouping."
            ),
            "worker_spread_red": (
                "At N=16 alignment off, at least one of W2/W4/W8 must differ from "
                "another worker count for the output gate to have power without "
                "changing the stimulus."
            ),
            "frame_count_red": (
                "At fixed W1/W16 and alignment off, N=17 or N=33 must differ to "
                "show that raising N activates a nontrivial chunk grouping."
            ),
            "alignment_red": (
                "At N=33, compare alignment off and on independently; the aligned "
                "pre arm must contain at least two worker hashes because it is the "
                "registered M139 configuration."
            ),
            "repair_green": (
                "The post-D9 N=33 aligned arm must have one pixel hash and one TIFF "
                "hash across W1/W2/W4/W8/W16."
            ),
            "prequantization_follow_up": (
                "Hash f32 plane bits immediately after BandMerge::finish and before "
                "u16 encoding. Probe on/off must leave the TIFF hash unchanged."
            ),
        },
        "input": {
            "stack": str(STACK),
            "selection": "lexicographically sorted first N native ARWs",
            "prohibited_holdout_used": False,
        },
        "configuration": {
            "flags": list(FLAGS),
            "backend": "pyramid",
            "pyramid_gate": 2.0,
            "resampler": "catmull-rom",
            "cover": "scale",
            "output": "full-sensor demosaiced linear-sRGB uint16 TIFF",
            "photometric": "not available on pyramid backend",
            "automatic_retries": False,
        },
        "binaries": {
            "pre": {
                "commit": PRE_COMMIT,
                "path": str(PRE_BINARY),
                "sha256": PRE_BINARY_SHA256,
            },
            "post": {
                "commit": POST_COMMIT,
                "path": str(POST_BINARY),
                "sha256": POST_BINARY_SHA256,
            },
        },
        "alignment": {
            "off": {"STREHL_ALIGN": "0", "STREHL_WARPMAP": None},
            "on_n33": {
                "STREHL_ALIGN": None,
                "STREHL_WARPMAP": str(SIDECAR_N33),
                "sidecar_sha256": SIDECAR_N33_SHA256,
                "sidecar_source": "M139 registered N=33 cache",
            },
        },
        "plans": plans(),
    }


def worker_stderr(arm: str, workers: int) -> list[str]:
    if arm == "pre":
        return [
            f"memory plan     : {workers} workers x",
            f"{workers} workers)",
        ]
    return [
        "canonical chunks, 1 reusable frame worker",
        f"1 retained + 1 scratch accumulator, {workers} execution threads",
        "changes threads, never arithmetic.",
        f"{workers} execution threads)",
    ]


def required_stderr(plan: dict[str, Any]) -> list[str]:
    alignment = (
        "alignment       : ON (sidecar-override)"
        if plan["alignment"] == "on"
        else "alignment       : OFF"
    )
    return [
        "strehl stack -- LAPLACIAN MULTI-BAND MERGE "
        "(--merge pyramid; THE DEFAULT PATH)",
        "noise gate      : 2.00 x",
        alignment,
        "16-bit RGB, linear sRGB",
        "Full sensor resolution",
        *worker_stderr(plan["arm"], plan["workers"]),
    ]


def group_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    for row in records:
        key = (row["arm"], row["limit"], row["alignment"])
        groups.setdefault(key, []).append(row)
    result = []
    for (arm, limit, alignment), rows in sorted(groups.items()):
        rows.sort(key=lambda row: row["workers"])
        pixel_by_worker = {
            str(row["workers"]): row["pixel_sha256"] for row in rows
        }
        tiff_by_worker = {
            str(row["workers"]): row["output_sha256"] for row in rows
        }
        differing_pairs = [
            [left["workers"], right["workers"]]
            for left, right in combinations(rows, 2)
            if left["pixel_sha256"] != right["pixel_sha256"]
        ]
        result.append(
            {
                "arm": arm,
                "limit": limit,
                "alignment": alignment,
                "workers": [row["workers"] for row in rows],
                "pixel_sha256_by_worker": pixel_by_worker,
                "tiff_sha256_by_worker": tiff_by_worker,
                "distinct_pixel_sha256": len(set(pixel_by_worker.values())),
                "distinct_tiff_sha256": len(set(tiff_by_worker.values())),
                "differing_worker_pairs": differing_pairs,
            }
        )
    return result


def validate_inputs() -> None:
    require(STACK.is_dir(), f"input stack is missing: {STACK}")
    for path, expected, label in (
        (PRE_BINARY, PRE_BINARY_SHA256, "pre binary"),
        (POST_BINARY, POST_BINARY_SHA256, "post binary"),
        (SIDECAR_N33, SIDECAR_N33_SHA256, "N=33 sidecar"),
    ):
        require(path.is_file(), f"{label} is missing: {path}")
        actual = sha256_file(path)
        require(actual == expected, f"{label} hash changed: {actual} != {expected}")


def run() -> int:
    validate_inputs()
    registered = protocol()
    protocol_sha256 = compact_sha256(registered)
    if RECORD.exists():
        campaign = json.loads(RECORD.read_text(encoding="utf-8"))
        require(
            campaign["protocol_sha256"] == protocol_sha256,
            "existing record belongs to a different protocol",
        )
    else:
        campaign = {
            "schema": "M172-negative-control-record-v1",
            "created_utc": utc_now(),
            "protocol": registered,
            "protocol_sha256": protocol_sha256,
            "records": [],
            "summary": [],
        }
        atomic_write(RECORD, campaign)

    harness = load_harness()
    completed = {row["run_id"] for row in campaign["records"]}
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
        arm = plan["arm"]
        binary = PRE_BINARY if arm == "pre" else POST_BINARY
        sidecar = SIDECAR_N33 if plan["alignment"] == "on" else None
        print(f"[{sequence + 1:02d}/{len(registered['plans']):02d}] {plan['run_id']}")
        try:
            observed = harness.run_once(
                exe=binary,
                stack=STACK,
                limit=plan["limit"],
                workers=plan["workers"],
                destination=destination,
                cache=cache,
                temp=temp,
                flags=list(FLAGS),
                sidecar=sidecar,
                align_off=plan["alignment"] == "off",
                fixed_env={},
                required_log_substrings=required_stderr(plan),
                kind="negative-control",
                repetition=None,
                sweep=plan["axis"],
                measured_commit=plan["source_commit"],
                external_busy_max=1.0,
            )
            require(observed["valid"], str(observed["invalid_reasons"]))
            require(
                observed["binary"]["sha256"]
                == (PRE_BINARY_SHA256 if arm == "pre" else POST_BINARY_SHA256),
                "harness measured the wrong binary",
            )
            row = {
                **plan,
                **observed,
                "sequence_index": sequence,
                "output_retained": False,
            }
            row["record_sha256"] = compact_sha256(row)
            campaign["records"].append(row)
            campaign["summary"] = group_summary(campaign["records"])
            atomic_write(RECORD, campaign)
        finally:
            destination.unlink(missing_ok=True)
    print(json.dumps(campaign["summary"], indent=2))
    return 0


def self_test() -> int:
    assert (16 + 16 - 1) // 16 == 1
    assert (17 + 16 - 1) // 16 == 2
    sample = [
        {
            "arm": "pre",
            "limit": 16,
            "alignment": "off",
            "workers": 1,
            "pixel_sha256": "A" * 64,
            "output_sha256": "C" * 64,
        },
        {
            "arm": "pre",
            "limit": 16,
            "alignment": "off",
            "workers": 16,
            "pixel_sha256": "B" * 64,
            "output_sha256": "D" * 64,
        },
    ]
    summary = group_summary(sample)[0]
    assert summary["distinct_pixel_sha256"] == 2
    assert summary["differing_worker_pairs"] == [[1, 16]]
    sample[1]["pixel_sha256"] = "A" * 64
    summary = group_summary(sample)[0]
    assert summary["distinct_pixel_sha256"] == 1
    assert summary["differing_worker_pairs"] == []
    assert len(plans()) == 19
    print("negative_control.py self-test: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    return self_test() if args.self_test else run()


if __name__ == "__main__":
    raise SystemExit(main())
