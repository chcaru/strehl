"""Root-scheduled bounded execution of the frozen insect placement observation."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
SCRIPT = ROOT / "experiments/raw-quality-2026-10-26/insect-placement/run.py"
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("placement_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
mode = sys.argv[1]
assert mode in ("controls", "stage", "measure")
out = CAMPAIGN / ("insect-placement-" + mode)
assert not out.exists()
out.mkdir()
env, removed = b.clean_environment()
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    env[key] = "4"
if mode == "controls":
    code = "import runpy,json; m=runpy.run_path(" + repr(str(SCRIPT)) + "); print(json.dumps(m['controls'](),indent=2))"
    command = [sys.executable, "-B", "-X", "faulthandler", "-c", code]
elif mode == "stage":
    command = [sys.executable, "-B", "-X", "faulthandler", str(SCRIPT), "stage", "--out", str(CAMPAIGN / "insect-placement-cache")]
else:
    command = [sys.executable, "-B", "-X", "faulthandler", str(SCRIPT), "measure", "--cache", str(CAMPAIGN / "insect-placement-cache"), "--out", str(CAMPAIGN / "insect-placement-observation")]

def save(name, value):
    with (out / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

bound = {"script": b.binding(SCRIPT), "helper": b.binding(HELPER), "runner": b.binding(__file__)}
save("invocation.json", {"command": command, "bindings": bound, "removed_environment": removed,
    "threads": 4, "committed_bytes": 4 << 30, "wall_seconds": 120 if mode == "stage" else 60,
    "healthy": "Control result or per-source progress, terminal receipt and exit0 inside the declared bounds."})
harness = ROOT / "experiments/m12-scorecard/m12-harness.py"
result = b.run(command, env, ROOT, out / "process.log", api=b.load_job_api(b.binding(harness)),
    wall_seconds=120 if mode == "stage" else 60, cpu_seconds=240,
    log_bytes=4 << 20, committed_bytes=4 << 30)
save("process.json", result)
assert bound == {"script": b.binding(SCRIPT), "helper": b.binding(HELPER), "runner": b.binding(__file__)}
print(json.dumps(result, indent=2))
assert result["exit_code"] == 0 and result["error"] is None
