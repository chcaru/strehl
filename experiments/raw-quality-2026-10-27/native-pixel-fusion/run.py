"""Root-owned frozen build and bounded native pixel-fusion observations."""
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
AREA = ROOT / "experiments/raw-quality-2026-10-27/native-pixel-fusion"
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-27"
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("native_pixel_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)


def ref(path):
    path = Path(path).resolve()
    return dict(path=str(path), **b.binding(path))


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def source_bindings():
    command = ["git", "--work-tree=" + str(ROOT), "ls-files", "--",
               "*.rs", "Cargo.toml", "Cargo.lock", "**/Cargo.toml"]
    listed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
    paths = {ROOT / path for path in listed}
    for campaign in ("raw-quality-2026-10-26", "raw-quality-2026-10-27"):
        paths.update((ROOT / "experiments" / campaign).rglob("*.rs"))
    paths.update([ROOT / "crates/strehl-core/src/cfa-lattice.rs",
                  ROOT / "crates/strehl-cli/src/direct-cfa-gather.rs"])
    return [ref(path) for path in sorted(paths) if path.is_file()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "screen", "cost", "full"))
    parser.add_argument("build_id", type=int)
    parser.add_argument("--iteration", type=int, default=1)
    args = parser.parse_args()
    assert args.build_id > 0 and args.iteration > 0
    CAMPAIGN.mkdir(exist_ok=True)
    build = CAMPAIGN / f"native-pixel-build-{args.build_id}"
    out = build if args.mode == "build" else CAMPAIGN / f"native-pixel-{args.mode}-{args.iteration}"
    assert not out.exists(), "fresh immutable output directory required"
    out.mkdir()
    if args.mode == "build":
        sources = source_bindings()
        save(out / "sources.json", sources)
        command = ["cargo", "test", "--locked", "--offline", "--release", "-p", "strehl-cli", "--lib", "--no-run",
                   "--features", "native-direct-planes,native-correction-variance,native-gpu-gather",
                   "--jobs", "4", "--message-format=json-render-diagnostics"]
        env, removed = b.clean_environment()
        env.update(CARGO_INCREMENTAL="0", CARGO_BUILD_JOBS="4", STREHL_TEST_TMP=str(CAMPAIGN / "test-tmp"))
        save(out / "invocation.json", dict(command=command, removed_environment=removed, build_jobs=4,
             sources=len(sources), runner=ref(__file__),
             scope="Build directly supervised; numerical jobs separately bounded after build exits."))
        started = time.monotonic()
        with (out / "artifacts.jsonl").open("xb") as stdout, (out / "build.log").open("xb") as stderr:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
        save(out / "build-process.json", dict(exit_code=result.returncode, wall_seconds=time.monotonic()-started))
        log = (out / "build.log").read_text(encoding="utf-8", errors="replace")
        print(log[-18000:])
        assert result.returncode == 0
        assert "Compiling strehl-cli" in log, "fresh affected compilation required"
        assert all(ref(row["path"]) == row for row in sources), "source changed during build"
        rows = [json.loads(line) for line in (out / "artifacts.jsonl").read_text().splitlines() if line.startswith("{")]
        assert any(row.get("reason") == "build-finished" and row.get("success") for row in rows)
        executables = [row["executable"] for row in rows if row.get("reason") == "compiler-artifact"
                       and row.get("executable") and row.get("target", {}).get("name") == "strehl_cli"
                       and row.get("profile", {}).get("test")]
        assert len(executables) == 1
        exe = out / "cli-tests.exe"
        shutil.copyfile(executables[0], exe)
        assert b.binding(exe) == b.binding(executables[0])
        save(out / "executable.json", ref(exe))
        print(json.dumps(ref(exe)))
        return

    sources = json.loads((build / "sources.json").read_text())
    assert all(ref(row["path"]) == row for row in sources), "build-bound source changed"
    exe = build / "cli-tests.exe"
    assert ref(exe) == json.loads((build / "executable.json").read_text())
    fields = dict(RAYON_NUM_THREADS="4", STREHL_PYRAMID_WORKERS="4", STREHL_ALIGN="1",
                  STREHL_FULLRES_GATHER="1", STREHL_DIRECT_PLANES="rounded", STREHL_PROBE_GATHER="green",
                  STREHL_WARP_WRITEBACK="parallel", STREHL_GPU_GATHER="on", STREHL_GPU_GATHER_LOG="off",
                  STREHL_GPU_SCHEDULE="device", STREHL_DEFECT="off", STREHL_FINE_SUPPORT="off",
                  STREHL_TEMPORAL_ENERGY="off", STREHL_SPATIAL_NOISE_FLOOR="off")
    if args.mode == "screen":
        fields["STREHL_NATIVE_PIXEL_OUT"] = str(out / "output")
        test = "independent_controls::fixed_native_pixel_screen"
        bounds = dict(wall_seconds=120, cpu_seconds=480, log_bytes=16 << 20, committed_bytes=4 << 30)
    else:
        config = out / "config.json"
        save(config, dict(schema=1, out_dir=str(out / "output"), expected_test_executable_sha256=b.binding(exe)["sha256"]))
        fields["STREHL_NATIVE_PIXEL_CONFIG"] = str(config)
        fields["STREHL_WARPMAP"] = str(ROOT / "outputs/raw-quality-2026-10-26/flat-1s-baseline/alignment.txt")
        test = "full::flat_source30_checkpoint" if args.mode == "cost" else "full::flat60_complete_observation"
        bounds = dict(wall_seconds=120 if args.mode == "cost" else 600,
                      cpu_seconds=480 if args.mode == "cost" else 2400,
                      log_bytes=32 << 20, committed_bytes=(8 if args.mode == "cost" else 12) << 30)
    env, removed = b.clean_environment(fields.items())
    command = [str(exe), "merge_cmd::native_pixel_fusion::" + test, "--ignored", "--exact", "--nocapture", "--test-threads=1"]
    save(out / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
         executable=ref(exe), runner=ref(__file__), helper=ref(HELPER), bounds=bounds,
         scope="Root-authorized fixed observation; successful execution does not imply photographic improvement."))
    api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    observations = []
    stop_observer = threading.Event()

    def observe_host():
        psutil.cpu_percent(None)
        while not stop_observer.is_set():
            row = dict(monotonic_seconds=time.monotonic(), host_cpu_percent=psutil.cpu_percent(None),
                       available_ram_bytes=psutil.virtual_memory().available)
            try:
                gpu = subprocess.run(["nvidia-smi", "--query-gpu=timestamp,index,name,utilization.gpu,memory.used,memory.total",
                                      "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=False)
                row.update(gpu_exit=gpu.returncode, gpu=gpu.stdout.strip())
            except Exception as error:
                row["gpu_error"] = str(error)
            observations.append(row)
            stop_observer.wait(3)

    observer = threading.Thread(target=observe_host, daemon=True)
    observer.start()
    try:
        result = b.run(command, env, ROOT, out / "process.log", api=api, **bounds)
    finally:
        stop_observer.set()
        observer.join(timeout=6)
        save(out / "host-observation.json", dict(scope="Whole-host/device samples, not process-exclusive memory or a clean timing comparison.",
             logical_cpus=psutil.cpu_count(), physical_cpus=psutil.cpu_count(logical=False),
             ram_bytes=psutil.virtual_memory().total, rows=observations))
    save(out / "process.json", result)
    print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_memory")}))
    log = (out / "process.log").read_text(encoding="utf-8", errors="replace")
    print(log[-18000:])
    assert result["exit_code"] == 0 and result["error"] is None
    assert result["terminal_job_accounting"] and not result["cleanup_errors"]
    assert "running 1 test" in log and "1 passed; 0 failed" in log
    assert all(ref(row["path"]) == row for row in sources), "source changed during execution"
    reports = sorted((out / "output").glob("*.json"))
    assert reports, "no native observation receipt"
    save(out / "completion.json", dict(reports=[ref(path) for path in reports], source_bindings_unchanged=True,
         photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
