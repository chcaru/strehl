"""Root release of one calibration-header domain observation; no pixel decode."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
SOURCE = ROOT / "experiments/raw-quality-2026-10-26/ca-metadata"
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("headers_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)

out = CAMPAIGN / "ca-header-domain-job-1"
assert not out.exists()
out.mkdir()
env, removed = b.clean_environment()
env["RAYON_NUM_THREADS"] = "1"
command = [sys.executable, "-I", "-B", "-X", "faulthandler",
           str(SOURCE / "header-domain.py"),
           "--out", str(CAMPAIGN / "ca-header-domain-1")]


def save(name, value):
    with (out / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


paths = [SOURCE / "header-domain.py", SOURCE / "header-observation.json",
         CAMPAIGN / "baseline-strehl.exe", HELPER, Path(__file__).resolve()]
bound = [b.binding(path) for path in paths]
save("invocation.json", dict(command=command, bindings=bound,
    removed_environment=removed, worker_count=1, committed_bytes=4 << 30,
    wall_seconds=120, maximum_native_header_inspections=144, pixel_decodes=0,
    healthy="One progress record per selected source;144 verified records and complete terminal receipt within120s."))
harness = ROOT / "experiments/m12-scorecard/m12-harness.py"
result = b.run(command, env, ROOT, out / "process.log",
    api=b.load_job_api(b.binding(harness)), wall_seconds=120, cpu_seconds=120,
    log_bytes=4 << 20, committed_bytes=4 << 30)
save("process.json", result)
assert bound == [b.binding(path) for path in paths], "Frozen source changed during run"
print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_memory")}, indent=2))
assert result["exit_code"] == 0 and result["error"] is None
