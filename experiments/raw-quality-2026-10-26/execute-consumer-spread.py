"""Root's one bounded exact-CFA consumer observation, without reconstruction."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
OUT = CAMPAIGN / "insect-consumer-spread-job-1"
SOURCE = ROOT / "experiments/raw-quality-2026-10-26/insect-consumer-spread/discriminate.py"
spec = importlib.util.spec_from_file_location("spread_bounded", ROOT / "experiments/m193c-output-grid/bounded-process.py")
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
assert b.binding(SOURCE)["sha256"] == "487b2987b2cf291661346c32736b63891d8def9ace912a40030441863b8f40de"
assert not OUT.exists()
OUT.mkdir()


def save(name, value):
    with (OUT / name).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


fields = {key: "1" for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
env, removed = b.clean_environment(fields.items())
command = [sys.executable, "-I", "-B", "-X", "faulthandler", str(SOURCE),
           "--out", str(CAMPAIGN / "insect-consumer-spread-1")]
save("invocation.json", dict(command=command, environment=fields, removed_environment=removed,
     source=b.binding(SOURCE), runner=b.binding(__file__), scope="Two fixed references, one bristle; no image-quality claim."))
api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
result = b.run(command, env, ROOT, OUT / "process.log", api=api,
               wall_seconds=30, cpu_seconds=60, log_bytes=4 << 20, committed_bytes=1 << 30)
save("process.json", result)
print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_memory")}))
print((OUT / "process.log").read_text())
assert result["exit_code"] == 0 and result["error"] is None
