"""Root schedules one full-size cost checkpoint or the complete299 observation."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("green_phase_photo_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
mode = sys.argv[1]
assert mode in ("cost", "full")
build_id = sys.argv[2]
iteration = sys.argv[3] if len(sys.argv) > 3 else "1"
assert build_id.isdecimal() and iteration.isdecimal()
BUILD = CAMPAIGN / ("green-phase-build-" + build_id)
SCREEN = CAMPAIGN / ("green-phase-screen-" + build_id)
OUT = CAMPAIGN / ("green-phase-" + mode + "-job-" + iteration)
OUTPUT = OUT / "output"


def ref(path):
    return {"path": str(Path(path).resolve()), **b.binding(path)}


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


sources = json.loads((BUILD / "sources.json").read_text())
assert all(ref(row["path"]) == row for row in sources)
exe = BUILD / "cli-tests.exe"
assert ref(exe) == json.loads((BUILD / "executable.json").read_text())
screen = json.loads((SCREEN / "output/screen.json").read_text())
assert screen["status"] == "SCREEN_COMPLETE" and screen["candidate_live"]
assert not screen["severe_generated_guard"], "root must review severe generated damage; no automatic photo release"
assert json.loads((SCREEN / "process.json").read_text())["exit_code"] == 0
assert not OUT.exists()
OUT.mkdir()
cost = None
if mode == "full":
    COST = CAMPAIGN / ("green-phase-cost-job-" + iteration)
    cost = json.loads((COST / "output/cost.json").read_text())
    process = json.loads((COST / "process.json").read_text())
    assert cost["status"] == "SOURCE149_COST_COMPLETE" and cost["baseline_identity"]["exact"]
    assert process["exit_code"] == 0 and process["error"] is None
    assert cost["projected299_seconds_without_margin"] < 3000
    assert process["job_memory"]["peak_job_memory_used_bytes"] < (12 << 30)
    assert json.loads((COST / "invocation.json").read_text())["executable"] == ref(exe)
config_path = OUT / "config.json"
save(config_path, dict(schema=1, out_dir=str(OUTPUT),
     baseline_linear_sha256="8f3d9ec977f06d8fd44e070f27ab97e398611436cef17271fa6b889067ea1960",
     expected_test_executable_sha256=b.binding(exe)["sha256"]))
fields = dict(RAYON_NUM_THREADS="4", STREHL_PYRAMID_WORKERS="4", STREHL_ALIGN="1", STREHL_FULLRES_GATHER="1",
              STREHL_DIRECT_PLANES="rounded", STREHL_PROBE_GATHER="green", STREHL_WARP_WRITEBACK="parallel",
              STREHL_GPU_GATHER="on", STREHL_GPU_GATHER_LOG="off", STREHL_GPU_SCHEDULE="device", STREHL_DEFECT="off",
              STREHL_FINE_SUPPORT="off", STREHL_FIX_CA="off", STREHL_TEMPORAL_ENERGY="off",
              STREHL_SPATIAL_NOISE_FLOOR="off", STREHL_GREEN_PHASE_GUIDE_CONFIG=str(config_path))
env, removed = b.clean_environment(fields.items())
test = "weevil_source149_full_cost" if mode == "cost" else "weevil299_complete_observation"
command = [str(exe), "merge_cmd::green_phase_guide::full::" + test,
           "--ignored", "--exact", "--nocapture", "--test-threads=1"]
bounds = dict(wall_seconds=240 if mode == "cost" else 3600,
              cpu_seconds=900 if mode == "cost" else 18000,
              log_bytes=32 << 20, committed_bytes=14 << 30)
save(OUT / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
     executable=ref(exe), runner=ref(__file__), helper=ref(HELPER), config=ref(config_path),
     screen=ref(SCREEN / "output/screen.json"), bounds=bounds,
     cost=ref(COST / "output/cost.json") if cost is not None else None,
     scope="One-source feasibility is not a photograph; complete trial has separate14GiB allowance for retained and scratch accumulators."))
api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
gpu_rows = []
gpu_stop = threading.Event()
def observe_gpu():
    while not gpu_stop.is_set():
        try:
            observed = subprocess.run(["nvidia-smi", "--query-gpu=timestamp,index,name,utilization.gpu,memory.used,memory.total",
                                       "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=False)
            gpu_rows.append(dict(monotonic_seconds=time.monotonic(), exit_code=observed.returncode,
                                 output=observed.stdout.strip(), error=observed.stderr.strip()))
        except Exception as error:
            gpu_rows.append(dict(monotonic_seconds=time.monotonic(), error=str(error)))
        gpu_stop.wait(5)
gpu_thread = threading.Thread(target=observe_gpu, daemon=True)
gpu_thread.start()
try:
    result = b.run(command, env, ROOT, OUT / "process.log", api=api, **bounds)
finally:
    gpu_stop.set()
    gpu_thread.join(timeout=6)
    save(OUT / "gpu-observation.json", dict(scope="Whole-device sampled utilization and memory; includes other host processes, not process-exclusive peak.", rows=gpu_rows))
save(OUT / "process.json", result)
print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_memory")}))
print((OUT / "process.log").read_text(encoding="utf-8", errors="replace")[-10000:])
assert result["exit_code"] == 0 and result["error"] is None
assert result["terminal_job_accounting"] and not result["cleanup_errors"]
assert all(ref(row["path"]) == row for row in sources)
report = OUTPUT / ("cost.json" if mode == "cost" else "completion.json")
data = json.loads(report.read_text())
assert data["status"] == ("SOURCE149_COST_COMPLETE" if mode == "cost" else "COMPLETE299_OBSERVATION_READY")
assert data["frames"] == (1 if mode == "cost" else 299)
assert data["baseline_identity"]["exact"]
save(OUT / "completion.json", dict(report=ref(report), source_bindings_unchanged=True,
     photographic_improvement_claimed=False))
