"""Run the completed Cargo artifact after the separate build Job reached its cleanup boundary."""
from pathlib import Path
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
BUILD = CAMPAIGN / "insect-color-build-1"
OUT = CAMPAIGN / "insect-color-post-cleanup-screen-1"
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("observed_color_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
assert not OUT.exists()
OUT.mkdir()

def ref(path):
    return {"path": str(Path(path).resolve()), **b.binding(path)}

def save(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

sources = json.loads((BUILD / "sources.json").read_text())
assert all(ref(row["path"]) == row for row in sources)
rows = []
for line in (BUILD / "process.log").read_text().splitlines():
    try:
        rows.append(json.loads(line))
    except ValueError:
        pass
assert any(row.get("reason") == "build-finished" and row.get("success") for row in rows)
artifacts = [row["executable"] for row in rows if row.get("reason") == "compiler-artifact" and row.get("executable")
    and row.get("target", {}).get("name") == "strehl_cli" and row.get("profile", {}).get("test")]
assert len(artifacts) == 1
original = ref(artifacts[0])
exe = OUT / "cli-tests.exe"
shutil.copyfile(artifacts[0], exe)
assert b.binding(exe) == b.binding(artifacts[0]) == {k:original[k] for k in ("sha256", "bytes")}
fields = dict(RAYON_NUM_THREADS="2", STREHL_PYRAMID_WORKERS="2", STREHL_ALIGN="1", STREHL_FULLRES_GATHER="1",
    STREHL_DIRECT_PLANES="rounded", STREHL_PROBE_GATHER="green", STREHL_WARP_WRITEBACK="parallel",
    STREHL_GPU_GATHER="on", STREHL_GPU_GATHER_LOG="off", STREHL_GPU_SCHEDULE="device", STREHL_DEFECT="off",
    STREHL_FINE_SUPPORT="off", STREHL_FIX_CA="off", STREHL_INSECT_COLOR_OUT=str(OUT / "output"))
env, removed = b.clean_environment(fields.items())
command = [str(exe), "merge_cmd::insect_color::controls::fixed_shared_snr_actual_consumer_screen", "--exact", "--nocapture", "--test-threads=1"]
save("invocation.json", {"command": command, "environment": fields, "removed_environment": removed,
    "executable": ref(exe), "original_artifact": original, "sources_manifest": ref(BUILD / "sources.json"),
    "build_log_observation": ref(BUILD / "process.log"), "runner": ref(__file__),
    "build_state": "Cargo emitted completed test artifact and build-finished success; Cargo exit0 separately verified; build Job timed out draining one owned descendant and terminated it.",
    "scope": "Independent test Job; no claim of clean build-wrapper exit or photograph."})
api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
result = b.run(command, env, ROOT, OUT / "process.log", api=api,
    wall_seconds=240, cpu_seconds=600, log_bytes=8 << 20, committed_bytes=4 << 30)
save("process.json", result)
print(json.dumps({k:result[k] for k in ("exit_code", "error", "wall_seconds", "job_memory")}, indent=2))
assert result["exit_code"] == 0 and result["error"] is None
assert all(ref(row["path"]) == row for row in sources)
assert ref(artifacts[0]) == original
report = OUT / "output/screen.json"
screen = json.loads(report.read_text())
save("completion.json", {"report": ref(report), "screen_status": screen.get("status"), "sources_unchanged": True,
    "build_cleanup_pending_at_dispatch": False, "scope": "Generated screen, not photographic admission."})
