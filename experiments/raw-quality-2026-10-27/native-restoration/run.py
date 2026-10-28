"""Root-owned bounded native restoration screen and complete saved-CFA replay."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import threading
import time

import psutil

ROOT = Path(__file__).resolve().parents[3]
AREA = Path(__file__).resolve().parent
OUT = ROOT / "outputs/raw-quality-2026-10-27"
PRIOR = ROOT / "experiments/raw-quality-2026-10-27/reconstruction-photo-observation/run.py"
spec = importlib.util.spec_from_file_location("restoration_prior_runner", PRIOR)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
b, ref, save = prior.b, prior.ref, prior.save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "screen", "weevil", "flat"))
    parser.add_argument("build_id", type=int)
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--screen-iteration", type=int, default=1)
    args = parser.parse_args()
    assert min(args.build_id, args.iteration, args.screen_iteration) > 0
    build = OUT / f"native-restoration-build-{args.build_id}"
    out = build if args.mode == "build" else OUT / f"native-restoration-{args.mode}-{args.iteration}"
    assert not out.exists(), "fresh immutable output directory required"
    out.mkdir(parents=True)
    if args.mode == "build":
        sources = prior.source_bindings()
        save(out / "sources.json", sources)
        command = ["cargo", "test", "--locked", "--offline", "--release", "-p", "strehl-cli", "--lib", "--no-run",
                   "--features", "native-direct-planes,native-correction-variance,native-gpu-gather",
                   "--jobs", "4", "--message-format=json-render-diagnostics"]
        env, removed = b.clean_environment()
        env.update(CARGO_INCREMENTAL="0", CARGO_BUILD_JOBS="4", STREHL_TEST_TMP=str(OUT / "test-tmp"))
        save(out / "invocation.json", dict(command=command, removed_environment=removed, build_jobs=4,
             sources=len(sources), runner=ref(__file__), helper=ref(PRIOR)))
        started = time.monotonic()
        with (out / "artifacts.jsonl").open("xb") as stdout, (out / "build.log").open("xb") as stderr:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
        save(out / "build-process.json", dict(exit_code=result.returncode, wall_seconds=time.monotonic()-started))
        log = (out / "build.log").read_text(encoding="utf-8", errors="replace")
        print(log[-12000:])
        assert result.returncode == 0
        assert "Compiling strehl-cli" in log, "fresh affected compilation required"
        assert all(ref(row["path"]) == row for row in sources), "source changed during build"
        rows = [json.loads(line) for line in (out / "artifacts.jsonl").read_text().splitlines() if line.startswith("{")]
        assert any(row.get("reason") == "build-finished" and row.get("success") for row in rows)
        executables = [row["executable"] for row in rows if row.get("reason") == "compiler-artifact"
                       and row.get("executable") and row.get("target", {}).get("name") == "strehl_cli"
                       and row.get("profile", {}).get("test")]
        assert len(executables) == 1
        exe = build / "cli-tests.exe"
        shutil.copyfile(executables[0], exe)
        assert b.binding(exe) == b.binding(executables[0])
        save(build / "executable.json", ref(exe))
        print(json.dumps(ref(exe)))
        return

    sources = json.loads((build / "sources.json").read_text())
    assert all(ref(row["path"]) == row for row in sources), "build-bound source changed"
    exe = build / "cli-tests.exe"
    assert ref(exe) == json.loads((build / "executable.json").read_text())
    if args.mode != "screen":
        screen = OUT / f"native-restoration-screen-{args.screen_iteration}"
        completion = json.loads((screen / "completion.json").read_text())
        assert completion["executable"] == ref(exe) and completion["source_bindings_unchanged"]
        assert all(ref(row["path"]) == row for row in completion["reports"])
        # Scientific interpretation is recorded separately. This binds a completed
        # producing-path screen; a successful test alone never qualifies a photo.
        assert completion["mode"] == "screen"
        generated = json.loads((screen / "output/screen.json").read_text())
        assert generated["status"] == "COMPLETE_GENERATED_DIAGNOSTIC"
        assert generated["all_cases_completed"] is True and generated["hard_valid"] is True
        assert generated["admission"] is False and generated["photographic_admission"] is False
        assert isinstance(generated["quality_pass"], bool), "retain the actual generated quality verdict"
    config = out / "config.json"
    save(config, dict(schema=1, out_dir=str(out / "output"), expected_test_executable_sha256=b.binding(exe)["sha256"]))
    fields = dict(RAYON_NUM_THREADS="4", STREHL_PYRAMID_WORKERS="4",
                  STREHL_NATIVE_RESTORATION_CONFIG=str(config), STREHL_DEMOSAIC="malvar")
    env, removed = b.clean_environment(fields.items())
    test = "generated_controls" if args.mode == "screen" else "replay_" + args.mode
    command = [str(exe), "merge_cmd::native_restoration::" + test, "--ignored", "--exact", "--nocapture", "--test-threads=1"]
    bounds = dict(wall_seconds=120 if args.mode == "screen" else 180,
                  cpu_seconds=480 if args.mode == "screen" else 720,
                  log_bytes=16 << 20, committed_bytes=(4 if args.mode == "screen" else 6) << 30)
    save(out / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
         executable=ref(exe), runner=ref(__file__), helper=ref(PRIOR), bounded_helper=ref(prior.HELPER), bounds=bounds,
         scope="Saved full CFA replay; no RAW decode or new alignment. CPU reconstruction/writer; no GPU performance claim."))
    api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    observations = []
    stop = threading.Event()

    def observe_host():
        psutil.cpu_percent(None)
        while not stop.is_set():
            observations.append(dict(monotonic_seconds=time.monotonic(), host_cpu_percent=psutil.cpu_percent(None),
                                     available_ram_bytes=psutil.virtual_memory().available))
            stop.wait(2)

    observer = threading.Thread(target=observe_host, daemon=True)
    observer.start()
    try:
        result = b.run(command, env, ROOT, out / "process.log", api=api, **bounds)
    finally:
        stop.set()
        observer.join(timeout=3)
        save(out / "host-observation.json", dict(scope="Whole-host load, not a clean speed comparison.",
             logical_cpus=psutil.cpu_count(), physical_cpus=psutil.cpu_count(logical=False),
             ram_bytes=psutil.virtual_memory().total, rows=observations))
    save(out / "process.json", result)
    print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_memory")}))
    log = (out / "process.log").read_text(encoding="utf-8", errors="replace")
    print(log[-12000:])
    assert result["exit_code"] == 0 and result["error"] is None
    assert result["terminal_job_accounting"] and not result["cleanup_errors"]
    assert "running 1 test" in log and "1 passed; 0 failed" in log
    assert all(ref(row["path"]) == row for row in sources), "source changed during execution"
    reports = sorted((out / "output").glob("*.json"))
    assert reports, "missing native report"
    if args.mode == "screen":
        generated = json.loads((out / "output/screen.json").read_text())
        assert generated["status"] == "COMPLETE_GENERATED_DIAGNOSTIC"
        assert generated["all_cases_completed"] is True and generated["hard_valid"] is True
        assert generated["admission"] is False and generated["photographic_admission"] is False
        assert isinstance(generated["quality_pass"], bool)
    else:
        receipt = json.loads((out / "output/receipt.json").read_text())
        assert receipt["status"] == "COMPLETE_NATIVE_RESTORATION_DIAGNOSTIC"
        assert receipt["dataset"] == args.mode and receipt["admission"] is False and receipt["quality_claim"] is False
        assert receipt["baseline_pixel_golden_exact"] and receipt["baseline_material_metadata_golden_exact"]
        assert receipt["pair_material_metadata_exact"] and receipt["sensor_off_bit_exact"]
        assert receipt["RAW_reads"] == 0 and receipt["original_RAW_read_or_written"] is False
    save(out / "completion.json", dict(mode=args.mode, reports=[ref(path) for path in reports],
         source_bindings_unchanged=True, executable=ref(exe), expected_test_count=1,
         photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
