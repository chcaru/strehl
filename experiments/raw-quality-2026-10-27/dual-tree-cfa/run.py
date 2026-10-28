"""Root-only fixed dual-tree controls, full-size cost, then conditional full299."""
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
spec = importlib.util.spec_from_file_location("dual_tree_prior_runner", PRIOR)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
b, ref, save = prior.b, prior.ref, prior.save


def complete_binding(path, exe):
    record = json.loads((path / "completion.json").read_text())
    assert record["executable"] == ref(exe) and record["source_bindings_unchanged"]
    assert all(ref(row["path"]) == row for row in record["reports"])
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "screen", "cost", "full"))
    parser.add_argument("build_id", type=int)
    parser.add_argument("--iteration", type=int, default=1)
    parser.add_argument("--screen-iteration", type=int, default=1)
    parser.add_argument("--cost-iteration", type=int, default=1)
    args = parser.parse_args()
    assert min(args.build_id, args.iteration, args.screen_iteration, args.cost_iteration) > 0
    build = OUT / f"dual-tree-cfa-build-{args.build_id}"
    runner_bindings = [ref(path) for path in (__file__, PRIOR, prior.HELPER,
                      ROOT / "experiments/m12-scorecard/m12-harness.py")]
    out = build if args.mode == "build" else OUT / f"dual-tree-cfa-{args.mode}-{args.iteration}"
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
        assert result.returncode == 0 and "Compiling strehl-cli" in log
        assert all(ref(row["path"]) == row for row in runner_bindings), "runner changed during build"
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
        save(build / "executable.json", ref(exe))
        print(json.dumps(ref(exe)))
        return

    sources = json.loads((build / "sources.json").read_text())
    assert all(ref(row["path"]) == row for row in sources), "build-bound source changed"
    exe = build / "cli-tests.exe"
    assert ref(exe) == json.loads((build / "executable.json").read_text())
    if args.mode != "screen":
        previous = OUT / f"dual-tree-cfa-screen-{args.screen_iteration}"
        complete_binding(previous, exe)
        screen = json.loads((previous / "output/screen.json").read_text())
        assert screen["status"] == "COMPLETE_DUAL_TREE_GENERATED_DIAGNOSTIC"
        assert screen["all_cases_completed"] and screen["mechanical_pass"]
        assert isinstance(screen["quality_pass"], bool)
        assert screen["admission"] is False and screen["photographic_admission"] is False
    if args.mode == "full":
        previous = OUT / f"dual-tree-cfa-cost-{args.cost_iteration}"
        complete_binding(previous, exe)
        cost = json.loads((previous / "output/receipt.json").read_text())
        assert cost["status"] == "SOURCE149_DUAL_TREE_COST_COMPLETE"
        assert cost["mechanical_pass"] and cost["source_count"] == 1
        assert cost["source_index"] == 149 and cost["noise_probe_draws"] == 16
        assert cost["input_preservation"] and cost["admission"] is False
        projected = 299 * cost["source_phase_seconds"] + cost["finish_seconds"] + 120
        assert 0 < projected <= 1200, "CPU full299 refuses cost projection; preserve result and use separately qualified GPU route"
        save(out / "cost-decision.json", dict(projected_seconds=projected, limit_seconds=1200,
             measured_full_workflow=False, source_receipt=ref(previous / "output/receipt.json")))

    fields = dict(RAYON_NUM_THREADS="4", STREHL_PYRAMID_WORKERS="4", STREHL_ALIGN="1",
                  STREHL_FULLRES_GATHER="1", STREHL_DIRECT_PLANES="off", STREHL_PROBE_GATHER="green",
                  STREHL_WARP_WRITEBACK="parallel", STREHL_GPU_GATHER="off", STREHL_FIX_CA="off",
                  STREHL_DEFECT="off", STREHL_TEMPORAL_ENERGY="off", STREHL_SPATIAL_NOISE_FLOOR="off",
                  STREHL_DEMOSAIC="malvar")
    if args.mode == "screen":
        fields["STREHL_DUAL_TREE_CFA_CONTROL_OUT"] = str(out / "output")
        test = "independent_controls::generated_controls"
        bounds = dict(wall_seconds=120, cpu_seconds=480, log_bytes=16 << 20, committed_bytes=4 << 30)
    else:
        config = out / "config.json"
        save(config, dict(schema=1, mode=args.mode, out_dir=str(out / "output"),
                         expected_test_executable_sha256=b.binding(exe)["sha256"]))
        fields["STREHL_DUAL_TREE_CFA_CONFIG"] = str(config)
        fields["STREHL_WARPMAP"] = str(ROOT / "outputs/raw-quality-2026-10-26/weevil-107-ca-off-alignment.txt")
        test = "full::weevil_source149_cost" if args.mode == "cost" else "full::weevil299_complete"
        bounds = dict(wall_seconds=300 if args.mode == "cost" else 1200,
                      cpu_seconds=1200 if args.mode == "cost" else 4800,
                      log_bytes=32 << 20, committed_bytes=14 << 30)
    env, removed = b.clean_environment(fields.items())
    command = [str(exe), "merge_cmd::dual_tree_cfa::" + test, "--ignored", "--exact", "--nocapture", "--test-threads=1"]
    save(out / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
         executable=ref(exe), runner=ref(__file__), helper=ref(PRIOR), bounded_helper=ref(prior.HELPER), bounds=bounds,
         scope="Fixed native-CFA dual-tree diagnostic. Complete source/probes cost precedes full299; no quality admission."))
    api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    observations, stop = [], threading.Event()

    def observe():
        psutil.cpu_percent(None)
        while not stop.is_set():
            observations.append(dict(monotonic_seconds=time.monotonic(), host_cpu_percent=psutil.cpu_percent(None),
                                     available_ram_bytes=psutil.virtual_memory().available))
            stop.wait(2)

    observer = threading.Thread(target=observe, daemon=True)
    observer.start()
    try:
        result = b.run(command, env, ROOT, out / "process.log", api=api, **bounds)
    finally:
        stop.set()
        observer.join(timeout=3)
        save(out / "host-observation.json", dict(scope="Whole-host load, not a clean competitive timing.",
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
    assert all(ref(row["path"]) == row for row in runner_bindings), "runner changed during execution"
    reports = sorted((out / "output").glob("*.json"))
    assert reports
    report = json.loads((out / "output" / ("screen.json" if args.mode == "screen" else "receipt.json")).read_text())
    assert report["mechanical_pass"] and report["admission"] is False
    if args.mode == "screen":
        assert report["status"] == "COMPLETE_DUAL_TREE_GENERATED_DIAGNOSTIC"
        assert report["all_cases_completed"] and isinstance(report["quality_pass"], bool)
        assert report["photographic_admission"] is False
    else:
        assert report["status"] == ("SOURCE149_DUAL_TREE_COST_COMPLETE" if args.mode == "cost" else "COMPLETE299_DUAL_TREE_DIAGNOSTIC")
        assert report["input_preservation"] and report["quality_claim"] is False
        assert report["source_count"] == (1 if args.mode == "cost" else 299)
        assert report["noise_probe_draws"] == 16 and report["photographic_admission"] is False
        if args.mode == "cost":
            assert report["source_index"] == 149
        if args.mode == "full":
            assert report["baseline_pixel_golden_exact"]
    save(out / "completion.json", dict(mode=args.mode, reports=[ref(path) for path in reports],
         runner_bindings=runner_bindings,
         source_bindings_unchanged=True, executable=ref(exe), expected_test_count=1,
         photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
