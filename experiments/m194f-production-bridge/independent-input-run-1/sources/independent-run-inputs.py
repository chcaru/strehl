"""Run the seven M194f input/configuration controls or CLI suite on a pinned build."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILTER = "merge_cmd::known_scene_benchmark::joint_pupil_bridge::"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key " + key)
        result[key] = value
    return result


def read(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build-record", type=Path, required=True)
    ap.add_argument("--build-sha256", required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--suite", action="store_true")
    args = ap.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    record_path = args.build_record.resolve()
    if sha(record_path) != args.build_sha256:
        raise ValueError("external build digest mismatch")
    build = read(record_path)
    if build["schema"] != "m194f-consumer-build-v1" or build["pass"] is not True:
        raise ValueError("build did not pass")
    if build["sources_before"] != build["sources_after"]:
        raise ValueError("build source bytes differed")
    expected_sources = build["sources_after"]
    own_rust = "experiments/m194f-production-bridge/independent-reader-controls.rs"
    if own_rust not in expected_sources:
        raise ValueError("independent test source omitted from build binding")
    source_before = {name: sha(ROOT / name) for name in expected_sources}
    if source_before != expected_sources:
        raise ValueError("compiled source differs from current bytes")
    for key in ("compiler_artifact", "test_executable"):
        ref = build[key]
        if type(ref["bytes"]) is not int or Path(ref["path"]).stat().st_size != ref["bytes"] or sha(ref["path"]) != ref["sha256"]:
            raise ValueError("actual compiler/copy binding mismatch")
    if any(build["compiler_artifact"][k] != build["test_executable"][k] for k in ("sha256", "bytes")):
        raise ValueError("compiler and copied test binary differ")
    log = Path(build["log"])
    if sha(log) != build["log_sha256"] or b"Compiling strehl-cli" not in log.read_bytes():
        raise ValueError("actual compile log does not bind CLI rebuild")
    driver = HERE / "consumer-run.py"
    if sha(driver) != build["driver_sha256"]:
        raise ValueError("driver source differs from build record")
    spec = importlib.util.spec_from_file_location("m194f_input_run_driver", driver)
    d = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(d)
    if d.sources() != expected_sources:
        raise ValueError("current explicit compiler source set differs")
    owned_names = [Path(__file__), HERE / "independent-reader-controls.rs", HERE / "independent-input-design.md", driver]
    owned_before = {str(p.relative_to(ROOT)): sha(p) for p in owned_names}
    snapshots = output / "sources"
    snapshots.mkdir()
    for path in owned_names:
        (snapshots / path.name).write_bytes(path.read_bytes())
    for name in ("crates/strehl-cli/src/merge_cmd/joint-pupil-bridge.rs", "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs"):
        (snapshots / Path(name).name).write_bytes((ROOT / name).read_bytes())
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("STREHL_") and k.upper() not in {
        "RAYON_NUM_THREADS", "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_TARGET_DIR"}}
    required = dict(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER="1", STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
    env.update(required)
    exe = Path(build["test_executable"]["path"])
    command = [str(exe), *([] if args.suite else [FILTER]), "--test-threads=1", "--nocapture"]
    existing = {p.resolve() for p in HERE.glob("independent-input-*") if p.is_dir()}
    start = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, check=False)
    end = datetime.now(timezone.utc).isoformat()
    raw = proc.stdout + proc.stderr
    (output / "raw.log").write_bytes(raw)
    generated = sorted({p.resolve() for p in HERE.glob("independent-input-*") if p.is_dir()} - existing)
    summaries = []
    for folder in generated:
        terminal = folder / "result.json"
        checks = read(folder / "checks.json") if (folder / "checks.json").exists() else []
        terminal_value = read(terminal) if terminal.exists() else None
        summaries.append(dict(directory=str(folder), result_sha256=sha(terminal) if terminal.exists() else None,
                              pass_=bool(terminal_value and terminal_value["pass"] is True),
                              check_count=len(checks), checks=checks))
    source_after = {name: sha(ROOT / name) for name in expected_sources}
    owned_after = {str(p.relative_to(ROOT)): sha(p) for p in owned_names}
    source_set_after = d.sources()
    unchanged = (source_before == source_after == source_set_after and owned_before == owned_after
                 and sha(record_path) == args.build_sha256 and sha(exe) == build["test_executable"]["sha256"])
    test_summaries = [line for line in proc.stdout.decode("utf-8", "replace").splitlines() if line.startswith("test result:")]
    match = re.fullmatch(
        r"test result: ok\. ([0-9]+) passed; 0 failed; ([0-9]+) ignored; 0 measured; [0-9]+ filtered out; finished in [0-9.]+s",
        test_summaries[0]) if len(test_summaries) == 1 else None
    summary_pass = bool(match and (int(match[1]) >= 7 if args.suite else (int(match[1]) == 7 and int(match[2]) == 2)))
    passed = proc.returncode == 0 and summary_pass and unchanged and len(summaries) == 6 and all(s["pass_"] for s in summaries)
    result = dict(schema="m194f-controls-command-v1", passed=passed, command=command,
                  interpreter_argv=sys.orig_argv, xoptions=sys._xoptions, executable=sys.executable,
                  started_utc=start, completed_utc=end, environment=required, build_record=str(record_path),
                  build_sha256=args.build_sha256, test_executable=build["test_executable"], exit_code=proc.returncode, test_summaries=test_summaries,
                  sources_before=source_before, sources_after=source_after, source_set_after=source_set_after,
                  owned_before=owned_before, owned_after=owned_after, unchanged=unchanged,
                  log=str(output / "raw.log"), log_sha256=sha(output / "raw.log"), test_groups=summaries,
                  independent_results=[dict(path=str(Path(s["directory"]) / "result.json"), sha256=s["result_sha256"],
                       bytes=(Path(s["directory"]) / "result.json").stat().st_size) for s in summaries if s["result_sha256"]],
                  check_count=sum(s["check_count"] for s in summaries), scope="input/parsing/source/plan/reread; no quality authority")
    write(output / "result.json", result)
    print(json.dumps(dict(passed=passed, exit_code=proc.returncode, groups=len(summaries), checks=result["check_count"],
                         result_sha256=sha(output / "result.json"), test_summaries=test_summaries)), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
