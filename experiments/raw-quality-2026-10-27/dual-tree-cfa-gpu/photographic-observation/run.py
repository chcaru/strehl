"""Root-only one complete photograph; original practical-speed gate stays failed."""
from pathlib import Path
from types import SimpleNamespace
import csv
import io
import importlib.util
import json
import subprocess
import sys
import threading
import time
import psutil

HERE = Path(__file__).resolve().parent
AREA = HERE.parent
ROOT = AREA.parents[2]
OUT = ROOT / "outputs/raw-quality-2026-10-27"
spec = importlib.util.spec_from_file_location("frozen_dual_tree_gpu_runner", AREA / "run.py")
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
b, ref, save, prior, PRIOR = r.b, r.ref, r.save, r.prior, r.PRIOR


def main():
    assert len(sys.argv) == 1, "fixed one-run observation accepts no parameter overrides"
    args = SimpleNamespace(mode="full")
    build = OUT / "dual-tree-cfa-gpu-build-2"
    sources = json.loads((build / "sources.json").read_text())
    assert all(ref(row["path"]) == row for row in sources), "frozen build-bound source changed"
    exe = build / "cli-tests.exe"
    assert ref(exe) == json.loads((build / "executable.json").read_text())
    assert ref(exe)["sha256"] == "84b8a52c6027179fd7808f70ceceed721437d26ec3e670146e2beacc9b7ae8a7"
    screen_path = OUT / "dual-tree-cfa-gpu-screen-2"
    cost_path = OUT / "dual-tree-cfa-gpu-cost-1"
    r.complete_binding(screen_path, exe)
    r.complete_binding(cost_path, exe)
    screen = json.loads((screen_path / "output/screen.json").read_text())
    assert screen["status"] == "COMPLETE_DUAL_TREE_GPU_GENERATED_DIAGNOSTIC"
    assert screen["all_cases_completed"] and screen["mechanical_pass"]
    assert screen["quality_pass"] is False and screen["admission"] is False and screen["photographic_admission"] is False
    cost = json.loads((cost_path / "output/receipt.json").read_text())
    assert cost["status"] == "SOURCE149_DUAL_TREE_COST_COMPLETE"
    assert cost["mechanical_pass"] and cost["source_count"] == 1 and cost["source_index"] == 149
    assert cost["noise_probe_draws"] == 16 and cost["input_preservation"]
    assert cost["admission"] is False and cost["quality_claim"] is False
    projected = 299 * cost["source_phase_seconds"] + cost["finish_seconds"] + 120
    assert 1200 < projected <= 4800, "retain failed original gate; require finite observation budget"
    out = OUT / "dual-tree-cfa-gpu-photograph-1"
    assert not out.exists(), "fresh immutable output directory required"
    out.mkdir(parents=True)
    runner_bindings = [ref(p) for p in (Path(__file__), HERE / "brief.md", AREA / "run.py", PRIOR,
                       prior.HELPER, ROOT / "experiments/m12-scorecard/m12-harness.py")]
    save(out / "cost-decision.json", dict(projected_seconds=projected, original_limit_seconds=1200,
         original_practical_speed_gate_passed=False, observation_wall_budget_seconds=4800,
         generated_quality_pass=False, photographic_improvement_claimed=False,
         source_receipt=ref(cost_path / "output/receipt.json"), screen_receipt=ref(screen_path / "output/screen.json")))
    fields = dict(RAYON_NUM_THREADS="4", STREHL_PYRAMID_WORKERS="4", STREHL_ALIGN="1",
                  STREHL_FULLRES_GATHER="1", STREHL_DIRECT_PLANES="off", STREHL_PROBE_GATHER="green",
                  STREHL_WARP_WRITEBACK="parallel", STREHL_GPU_GATHER="off", STREHL_FIX_CA="off",
                  STREHL_DEFECT="off", STREHL_TEMPORAL_ENERGY="off", STREHL_SPATIAL_NOISE_FLOOR="off",
                  STREHL_DEMOSAIC="malvar", CUDA_VISIBLE_DEVICES="0", CUBLAS_WORKSPACE_CONFIG=":4096:8",
                  OMP_NUM_THREADS="4", MKL_NUM_THREADS="4", OPENBLAS_NUM_THREADS="1")
    cache = out / "cuda-cache"
    cache.mkdir()
    fields["CUDA_CACHE_PATH"] = str(cache)
    if args.mode == "screen":
        fields["STREHL_DUAL_TREE_CFA_GPU_CONTROL_OUT"] = str(out / "output")
        test = "independent_controls::generated_controls"
        bounds = dict(wall_seconds=120, cpu_seconds=480, log_bytes=16 << 20, committed_bytes=8 << 30)
    else:
        config = out / "config.json"
        save(config, dict(schema=1, mode=args.mode, out_dir=str(out / "output"),
                         expected_test_executable_sha256=b.binding(exe)["sha256"]))
        fields["STREHL_DUAL_TREE_CFA_CONFIG"] = str(config)
        fields["STREHL_WARPMAP"] = str(ROOT / "outputs/raw-quality-2026-10-26/weevil-107-ca-off-alignment.txt")
        test = "full::weevil_source149_cost" if args.mode == "cost" else "full::weevil299_complete"
        bounds = dict(wall_seconds=300 if args.mode == "cost" else 4800,
                      cpu_seconds=1200 if args.mode == "cost" else 19200,
                      log_bytes=32 << 20, committed_bytes=16 << 30)
    gpu_config = out / "gpu-config.json"
    python, server = ref(sys.executable), ref(AREA / "gpu-server.py")
    save(gpu_config, dict(schema=1, python=python["path"], python_sha256=python["sha256"],
         server=server["path"], server_sha256=server["sha256"], out_dir=str(out), device_limit_bytes=24 << 30))
    fields["STREHL_DUAL_TREE_CFA_GPU_CONFIG"] = str(gpu_config)
    runtime_bindings = [ref(gpu_config), python, server]
    env, removed = b.clean_environment(fields.items())
    for key in ("PYTORCH_CUDA_ALLOC_CONF", "PYTORCH_ALLOC_CONF", "CUDA_LAUNCH_BLOCKING",
                "TORCH_ALLOW_TF32_CUBLAS_OVERRIDE", "NVIDIA_TF32_OVERRIDE"):
        if key in env:
            del env[key]
            removed.append(key)
    query = ["nvidia-smi", "--query-gpu=index,name,uuid,driver_version,memory.total,memory.used",
             "--format=csv,noheader,nounits"]
    device = subprocess.run(query, cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
    rows = list(csv.reader(io.StringIO(device.stdout)))
    save(out / "device-preflight.json", dict(command=query, exit_code=device.returncode,
         stdout=device.stdout, stderr=device.stderr,
         scope="Read-only whole-device free-memory preflight; worker peaks cover only its Torch allocator."))
    assert device.returncode == 0 and rows and len(rows[0]) == 6
    assert rows[0][0].strip() == "0" and "RTX 5090" in rows[0][1]
    assert (int(rows[0][4]) - int(rows[0][5])) * (1 << 20) >= 26 << 30, "GPU requires 26GiB free before launch"
    command = [str(exe), "merge_cmd::dual_tree_cfa_gpu::" + test, "--ignored", "--exact", "--nocapture", "--test-threads=1"]
    save(out / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
         executable=ref(exe), runner=ref(__file__), helper=ref(PRIOR), bounded_helper=ref(prior.HELPER), bounds=bounds,
         gpu_config=ref(gpu_config), python=python, server=server,
         scope="One unchanged complete photographic observation. Original1200s practical-speed gate remains failed; no quality admission."))
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
    assert all(ref(row["path"]) == row for row in runtime_bindings), "GPU runtime binding changed"
    reports = sorted((out / "output").glob("*.json"))
    assert reports
    report = json.loads((out / "output" / ("screen.json" if args.mode == "screen" else "receipt.json")).read_text())
    workers = sorted(out.glob("gpu-worker-*"))
    assert workers and (args.mode == "screen" or len(workers) == 1)
    worker_receipts = []
    for worker in workers:
        server_path, bridge_path = worker / "server-receipt.json", worker / "bridge-receipt.json"
        gpu = json.loads(server_path.read_text())
        bridge = json.loads(bridge_path.read_text())
        assert gpu["status"] == "COMPLETE_DUAL_TREE_CUDA_WORKER" and gpu["complete"]
        assert gpu["backend"] == "torch-cuda-f32" and gpu["device_limit_bytes"] == 24 << 30
        assert 0 < gpu["peak_allocated_bytes"] <= gpu["peak_reserved_bytes"] <= 24 << 30
        assert gpu["server_sha256"] == server["sha256"]
        assert bridge["status"] == "COMPLETE_DUAL_TREE_CUDA_BRIDGE" and bridge["complete"]
        assert bridge["child_exit_code"] == 0 and bridge["parent_in_job"] and bridge["child_in_job"]
        assert bridge["bindings_unchanged"] and bridge["server_receipt"] == ref(server_path)
        if args.mode != "screen":
            count = 1 if args.mode == "cost" else 299
            assert gpu["source_count"] == bridge["source_count"] == count
            assert gpu["source_ids"] == bridge["source_ids"] == ([149] if count == 1 else list(range(299)))
            assert bridge["probe_draws_total"] == 16 * count
        worker_receipts.extend([ref(server_path), ref(bridge_path)])
    assert report["mechanical_pass"] and report["admission"] is False
    if args.mode == "screen":
        assert report["status"] == "COMPLETE_DUAL_TREE_GPU_GENERATED_DIAGNOSTIC"
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
         runtime_bindings=runtime_bindings,
         worker_receipts=worker_receipts,
         source_bindings_unchanged=True, executable=ref(exe), expected_test_count=1,
         photographic_improvement_claimed=False))


if __name__ == "__main__":
    main()
