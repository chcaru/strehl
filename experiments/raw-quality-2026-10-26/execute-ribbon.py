"""Root-scheduled bounded independent ribbon controls; no photographic inputs."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
SOURCE = ROOT / "experiments/raw-quality-2026-10-26/ribbon-visibility"
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("ribbon_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)

out = CAMPAIGN / "ribbon-visibility-job-1"
assert not out.exists()
out.mkdir()
env, removed = b.clean_environment()
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    env[key] = "1"
command = [sys.executable, "-I", "-B", "-X", "faulthandler",
           str(SOURCE / "independent-controls.py"),
           "--out", str(CAMPAIGN / "ribbon-visibility-1")]


def save(name, value):
    with (out / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


paths = [*sorted(SOURCE.glob("*.py")), HELPER, Path(__file__).resolve()]
bound = [b.binding(path) for path in paths]
save("invocation.json", dict(command=command, bindings=bound,
    removed_environment=removed, worker_count=1, committed_bytes=4 << 30,
    wall_seconds=120, original_raw_reads=0, full_stack_output=False,
    healthy="Independent forward controls then at most one 73-evaluation fit within120s; final observations and receipt."))
harness = ROOT / "experiments/m12-scorecard/m12-harness.py"
result = b.run(command, env, ROOT, out / "process.log",
    api=b.load_job_api(b.binding(harness)), wall_seconds=120, cpu_seconds=120,
    log_bytes=4 << 20, committed_bytes=4 << 30)
save("process.json", result)
assert bound == [b.binding(path) for path in paths], "Frozen source changed during run"
print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_memory")}, indent=2))
assert result["exit_code"] == 0 and result["error"] is None
