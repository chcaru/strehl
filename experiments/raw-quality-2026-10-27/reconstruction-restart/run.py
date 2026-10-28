"""Root-owned frozen build and bounded fixed reconstruction restart."""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "experiments/raw-quality-2026-10-27/native-pixel-fusion/run.py"
spec = importlib.util.spec_from_file_location("held_native_build", BASE)
shared = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shared
spec.loader.exec_module(shared)
b, ref, save = shared.b, shared.ref, shared.save
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-27"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "screen", "cache"))
    parser.add_argument("build_id", type=int)
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--screen-iteration", type=int, default=1)
    args = parser.parse_args()
    assert args.build_id > 0 and args.iteration > 0 and args.screen_iteration > 0
    build = CAMPAIGN / f"reconstruction-restart-build-{args.build_id}"
    out = build if args.mode == "build" else CAMPAIGN / f"reconstruction-restart-{args.mode}-{args.iteration}"
    assert not out.exists(), "fresh output required"
    out.mkdir(parents=True)
    if args.mode == "build":
        sources = shared.source_bindings()
        save(out / "sources.json", sources)
        command = ["cargo", "test", "--locked", "--offline", "--release", "-p", "strehl-cli", "--lib", "--no-run",
                   "--features", "native-direct-planes,native-correction-variance,native-gpu-gather",
                   "--jobs", "4", "--message-format=json-render-diagnostics"]
        env, removed = b.clean_environment()
        env.update(CARGO_INCREMENTAL="0", CARGO_BUILD_JOBS="4", STREHL_TEST_TMP=str(CAMPAIGN / "test-tmp"))
        save(out / "invocation.json", dict(command=command, removed_environment=removed, build_jobs=4,
             sources=len(sources), runner=ref(__file__), shared_runner=ref(BASE)))
        started = time.monotonic()
        with (out / "artifacts.jsonl").open("xb") as stdout, (out / "build.log").open("xb") as stderr:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
        save(out / "build-process.json", dict(exit_code=result.returncode, wall_seconds=time.monotonic()-started))
        log = (out / "build.log").read_text(encoding="utf-8", errors="replace")
        print(log[-12000:])
        assert result.returncode == 0 and "Compiling strehl-cli" in log
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
    prefix = "merge_cmd::reconstruction_restart::"
    if args.mode == "screen":
        fields["STREHL_CONSISTENT_RECONSTRUCTION_OUT"] = str(out / "output")
        fields["STREHL_RECONSTRUCTION_RESTART_CONTROL_OUT"] = str(out / "restart-output")
        command = [str(exe), prefix + "independent_controls::", "--nocapture", "--test-threads=1"]
        expected_tests = 5
    else:
        for earlier in ("screen",):
            completed = CAMPAIGN / f"reconstruction-restart-{earlier}-{args.screen_iteration}/completion.json"
            value = json.loads(completed.read_text())
            assert value["executable"] == ref(exe) and value["source_bindings_unchanged"]
            assert all(ref(row["path"]) == row for row in value["reports"]), "prerequisite report changed"
            original_screen = json.loads((completed.parent / "output/screen.json").read_text())
            extra_screen = json.loads((completed.parent / "restart-output/screen.json").read_text())
            assert original_screen["status"] == "SCREEN_COMPLETE" and original_screen["mechanical_pass"] and original_screen["numerical_pass"]
            assert extra_screen["all_pass"] is True
        config = out / "config.json"
        save(config, dict(schema=1, out_dir=str(out / "output"), expected_test_executable_sha256=b.binding(exe)["sha256"]))
        fields["STREHL_RECONSTRUCTION_RESTART_CONFIG"] = str(config)
        command = [str(exe), prefix + "cache_adapter::cached_chip_pair", "--ignored", "--exact", "--nocapture", "--test-threads=1"]
        expected_tests = 1
    bounds = dict(wall_seconds=180 if args.mode == "cache" else 120,
                  cpu_seconds=720 if args.mode == "cache" else 480,
                  log_bytes=32 << 20, committed_bytes=(6 if args.mode == "cache" else 4) << 30)
    env, removed = b.clean_environment(fields.items())
    host_before = dict(cpu_percent=psutil.cpu_percent(interval=1), available_ram_bytes=psutil.virtual_memory().available,
                       logical_cpus=psutil.cpu_count(), physical_cpus=psutil.cpu_count(logical=False))
    save(out / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
         executable=ref(exe), runner=ref(__file__), shared_runner=ref(BASE), helper=ref(shared.HELPER), bounds=bounds,
         host_before=host_before, expected_tests=expected_tests, prerequisite_screen_iteration=args.screen_iteration,
         scope="Operational bounded observation, no photographic improvement from test completion."))
    api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    result = b.run(command, env, ROOT, out / "process.log", api=api, **bounds)
    save(out / "process.json", result)
    print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_memory")}))
    log = (out / "process.log").read_text(encoding="utf-8", errors="replace")
    print(log[-12000:])
    unchanged = all(ref(row["path"]) == row for row in sources)
    save(out / "postcheck.json", dict(source_bindings_unchanged=unchanged,
         host_cpu_percent=psutil.cpu_percent(interval=1), available_ram_bytes=psutil.virtual_memory().available))
    assert result["exit_code"] == 0 and result["error"] is None
    assert result["terminal_job_accounting"] and not result["cleanup_errors"] and unchanged
    assert f"running {expected_tests} test" in log and f"{expected_tests} passed; 0 failed" in log
    reports = sorted((out / "output").glob("*.json"))
    if args.mode == "screen":
        reports.extend(sorted((out / "restart-output").glob("*.json")))
    assert reports, "no observation receipt"
    if args.mode == "cache":
        scientific = json.loads((out / "output/cache-result.json").read_text())
        assert scientific["status"] in ("CACHED_NUMERICAL_PASS", "CACHED_NUMERICAL_REFUSAL")
        assert scientific["inputs_unchanged"] is True and scientific["old_historical_exact"] is True
        assert scientific["all_restart_planes_admitted"] == (scientific["status"] == "CACHED_NUMERICAL_PASS")
    save(out / "completion.json", dict(reports=[ref(path) for path in reports], executable=ref(exe),
         source_bindings_unchanged=True, photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
