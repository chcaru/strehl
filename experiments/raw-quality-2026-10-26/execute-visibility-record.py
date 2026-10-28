"""Root release of one prepared saved-alpha diagnostic, no new fit or RAW reads."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
SCRIPT = ROOT / "experiments/raw-quality-2026-10-26/structured-visibility/diagnose-record.py"
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("visibility_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
out = CAMPAIGN / "structured-visibility-job-record-1"
assert not out.exists()
out.mkdir()
env, removed = b.clean_environment()
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    env[key] = "1"
command = [sys.executable, "-I", "-B", "-X", "faulthandler", str(SCRIPT), "--out", str(CAMPAIGN / "structured-visibility-record-1")]

def save(name, value):
    with (out / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

bound = {"script": b.binding(SCRIPT), "helper": b.binding(HELPER), "runner": b.binding(__file__)}
save("invocation.json", {"command": command, "bindings": bound, "removed_environment": removed,
    "threads": 1, "committed_bytes": 4 << 30, "torch_allocator_bytes": 4 << 30,
    "wall_seconds": 120, "healthy": "Controls, saved-prediction replay and terminal result within120s; no optimization."})
harness = ROOT / "experiments/m12-scorecard/m12-harness.py"
result = b.run(command, env, ROOT, out / "process.log", api=b.load_job_api(b.binding(harness)),
    wall_seconds=120, cpu_seconds=120, log_bytes=4 << 20, committed_bytes=4 << 30)
save("process.json", result)
assert bound == {"script": b.binding(SCRIPT), "helper": b.binding(HELPER), "runner": b.binding(__file__)}
print(json.dumps({k:result[k] for k in ("exit_code", "error", "wall_seconds", "job_memory")}, indent=2))
assert result["exit_code"] == 0 and result["error"] is None
