"""Run independent controls against the exact candidate compiler artifact."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PREFIX = "merge_cmd::gatefloor::m194c_independent_tests::"
TESTS = ["independent_sequence_layout_legacy_and_seed",
         "independent_actual_probe_layout_and_live_metadata",
         "independent_empty_nan_and_real_merge_fallback",
         "independent_original_inert_fallback_power_retained",
         "independent_actual_writer_layout_and_power"]


def sha(path):
    return hashlib.file_digest(Path(path).open("rb"), "sha256").hexdigest()


def unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError(f"duplicate key: {k}")
        result[k] = v
    return result


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def write(path, data):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write("\n")


def bind_build(path, expected_sha):
    if sha(path) != expected_sha:
        raise ValueError("build record hash mismatch")
    record = load(path)
    if not record["pass"] or not record["rebuilt_cli"] or record["exit_code"] != 0:
        raise ValueError("not a completed rebuilt candidate")
    log = Path(record["log"])
    if sha(log) != record["log_sha256"] or b"Compiling strehl-cli" not in log.read_bytes():
        raise ValueError("compile proof mismatch")
    artifacts = []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("{"):
            continue
        item = json.loads(line)
        if (item.get("reason") == "compiler-artifact" and item.get("executable")
                and item.get("target", {}).get("name") == "strehl"
                and item.get("profile", {}).get("test")):
            artifacts.append(Path(item["executable"]).resolve())
    if artifacts != [Path(record["compiler_artifact"]["path"]).resolve()]:
        raise ValueError("compiler artifact lineage mismatch")
    exe = Path(record["test_executable"]["path"])
    for binding in [record["compiler_artifact"], record["test_executable"]]:
        p = Path(binding["path"])
        if p.stat().st_size != binding["bytes"] or sha(p) != binding["sha256"]:
            raise ValueError("candidate executable binding mismatch")
    if record["compiler_artifact"]["sha256"] != record["test_executable"]["sha256"]:
        raise ValueError("copied executable differs")
    if record["sources_before"] != record["sources_after"]:
        raise ValueError("product sources moved during build")
    if record["included_test_sources_before"] != record["included_test_sources_after"]:
        raise ValueError("included tests moved during build")
    sources = dict(record["sources_after"])
    sources.update(record["included_test_sources_after"])
    if "experiments/m194c-probe-layout/independent-tests.rs" not in sources:
        raise ValueError("independent test not bound by compilation")
    if any(sha(ROOT / p) != value for p, value in sources.items()):
        raise ValueError("compiled source no longer current")
    return exe, sources


def check_tiffs(directory):
    import numpy as np
    import tifffile
    records = {}
    for p in sorted(directory.glob("*.tif")):
        with tifffile.TiffFile(p) as tif:
            if len(tif.pages) != 1:
                raise ValueError("unexpected TIFF pages")
            page = tif.pages[0]
            a = page.asarray()
            if a.dtype != np.dtype("uint16") or a.ndim != 3 or a.shape[2] != 3:
                raise ValueError("unexpected delivered TIFF type")
            records[p.stem] = dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size,
                shape=list(a.shape), pixel_sha256=hashlib.sha256(a.astype("<u2").tobytes()).hexdigest(),
                software=page.tags["Software"].value,
                description=page.tags["ImageDescription"].value,
                minimum=int(a.min()), maximum=int(a.max()))
    for prefix, shape in [("whole", [190, 274, 3]), ("crop", [156, 224, 3])]:
        baseline = records[prefix + "-baseline"]
        if baseline["shape"] != shape or baseline["minimum"] == baseline["maximum"]:
            raise ValueError("delivered stimulus dimensions or variation invalid")
        for label in ["layout1", "layout2", "poison1", "poison2", "observer1", "observer2"]:
            got = records[prefix + "-" + label]
            if any(got[k] != baseline[k] for k in ["sha256", "pixel_sha256", "shape"]):
                raise ValueError(f"delivered layout/observer not identical: {label}")
        for label in ["single-site", "active", "noise", "warp", "wb"]:
            got = records[prefix + "-" + label]
            if got["sha256"] == baseline["sha256"] or got["pixel_sha256"] == baseline["pixel_sha256"]:
                raise ValueError(f"delivered power control is inert: {label}")
    if len(records) != 24:
        raise ValueError("incomplete delivered TIFF matrix")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-record", type=Path, required=True)
    parser.add_argument("--build-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194c-independent-controls-v1", build_record=str(args.build_record.resolve()),
                  build_sha256=args.build_sha256, started_utc=datetime.now(timezone.utc).isoformat(),
                  runner_sha256=sha(__file__), prereg_sha256=sha(HERE / "independent-preregister.md"),
                  amendment_sha256=sha(HERE / "independent-amendment-1.md"),
                  amendment_2_sha256=sha(HERE / "independent-amendment-2.md"),
                  dispositions={"original_sinusoid_fallback_power": "retained omitted-reset expected failure; equalities unpowered",
                                "checkerboard_fallback_power": "separate component control with corrected next_frame lifecycle",
                                "raw_NaN": "direct core fault injection, not production finite-prefix caller fallback",
                                "stats_flags": "inert options in prepared pyramid path; not active observer commissioning"},
                  python=sys.version, checks=[], pass_=False)
    try:
        exe, sources = bind_build(args.build_record, args.build_sha256)
        result["compiled_source_count"] = len(sources)
        for gather in ["0", "1"]:
            env = {k: v for k, v in os.environ.items() if not k.upper().startswith("STREHL_")}
            for key in ["RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RAYON_NUM_THREADS", "CARGO_TARGET_DIR"]:
                env.pop(key, None)
            env.update(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER=gather,
                       STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
            command = [str(exe), PREFIX, "--test-threads=1", "--nocapture"]
            started = datetime.now(timezone.utc).isoformat()
            proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
            text = proc.stdout.decode("utf-8", "replace")
            log = out / f"gather-{gather}.log"
            log.write_bytes(proc.stdout + proc.stderr)
            child = dict(gather=gather, command=command, exit_code=proc.returncode,
                         started_utc=started, ended_utc=datetime.now(timezone.utc).isoformat(),
                         environment={k: v for k, v in env.items() if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"},
                         log=str(log), log_sha256=sha(log),
                         evidence_lines=[line for line in text.splitlines() if "M194C_INDEPENDENT" in line])
            child["pass"] = (proc.returncode == 0 and "5 passed; 0 failed" in text
                             and all(PREFIX + t in text for t in TESTS)
                             and "should panic" in text)
            if child["pass"]:
                dirs = set(re.findall(r" dir=(.+)", text))
                if len(dirs) != 1:
                    child["pass"] = False
                    child["artifact_failure"] = "writer output directory not unique"
                else:
                    try:
                        child["tiffs"] = check_tiffs(Path(dirs.pop()))
                    except Exception as e:
                        child["pass"] = False
                        child["artifact_failure"] = repr(e)
            result["checks"].append(child)
            write(out / f"gather-{gather}.json", child)
            print(json.dumps({k: child[k] for k in ["gather", "exit_code", "pass"]}), flush=True)
        result["sources_unchanged"] = all(sha(ROOT / p) == value for p, value in sources.items())
        result["pass_"] = result["sources_unchanged"] and all(c["pass"] for c in result["checks"])
    except Exception as e:
        result["exception"] = repr(e)
    result["ended_utc"] = datetime.now(timezone.utc).isoformat()
    write(out / "result.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}), flush=True)
    return 0 if result["pass_"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
