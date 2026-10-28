"""Root-owned build and bounded actual-consumer shared-color guide screen."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("color_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
mode = sys.argv[1]
assert mode in ("build", "screen")
suffix = sys.argv[2] if len(sys.argv) > 2 else "1"
assert suffix.isdecimal()
out = CAMPAIGN / ("insect-color-" + mode + "-" + suffix)
assert not out.exists()
out.mkdir()

def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

def reference(path):
    return {"path": str(Path(path).resolve()), **b.binding(path)}

api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
if mode == "build":
    command = ["git", "--work-tree=" + str(ROOT), "ls-files", "--", "*.rs", "Cargo.toml", "Cargo.lock", "**/Cargo.toml"]
    listed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    paths = {ROOT / p for p in listed}
    paths.update((ROOT / "experiments/raw-quality-2026-10-26").rglob("*.rs"))
    paths.update([ROOT / "crates/strehl-core/src/cfa-lattice.rs", ROOT / "crates/strehl-cli/src/direct-cfa-gather.rs"])
    sources = [reference(p) for p in sorted(paths) if p.is_file()]
    save(out / "sources.json", sources)
    command = ["cargo", "test", "--locked", "--offline", "--release", "-p", "strehl-cli", "--lib", "--no-run",
        "--features", "native-direct-planes,native-correction-variance,native-gpu-gather", "--jobs", "8",
        "--message-format=json-render-diagnostics"]
    env, removed = b.clean_environment()
    env.update(CARGO_INCREMENTAL="0", CARGO_BUILD_JOBS="8", STREHL_TEST_TMP=str(CAMPAIGN / "test-tmp"))
    save(out / "invocation.json", {"command": command, "removed_environment": removed,
        "source_count": len(sources), "runner": reference(__file__), "helper": reference(HELPER), "workers": 8})
    result = b.run(command, env, ROOT, out / "process.log", api=api,
        wall_seconds=900, cpu_seconds=5000, log_bytes=32 << 20, committed_bytes=24 << 30)
    save(out / "process.json", result)
    print(json.dumps({k: result[k] for k in ("exit_code", "error", "wall_seconds", "job_memory")}, indent=2))
    assert result["exit_code"] == 0 and result["error"] is None
    assert all(reference(row["path"]) == row for row in sources), "source changed during build"
    log = (out / "process.log").read_text(encoding="utf-8", errors="replace")
    assert "Compiling strehl-cli" in log
    executables = []
    for line in log.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("reason") == "compiler-artifact" and row.get("executable") and row.get("target", {}).get("name") == "strehl_cli" and row.get("profile", {}).get("test"):
            executables.append(row["executable"])
    assert len(executables) == 1, executables
    exe = out / "cli-tests.exe"
    shutil.copyfile(executables[0], exe)
    save(out / "executable.json", reference(exe))
else:
    build = CAMPAIGN / ("insect-color-build-" + suffix)
    sources = json.loads((build / "sources.json").read_text())
    assert all(reference(row["path"]) == row for row in sources)
    exe = build / "cli-tests.exe"
    assert reference(exe) == json.loads((build / "executable.json").read_text())
    fields = dict(RAYON_NUM_THREADS="2", STREHL_PYRAMID_WORKERS="2", STREHL_ALIGN="1", STREHL_FULLRES_GATHER="1",
        STREHL_DIRECT_PLANES="rounded", STREHL_PROBE_GATHER="green", STREHL_WARP_WRITEBACK="parallel",
        STREHL_GPU_GATHER="on", STREHL_GPU_GATHER_LOG="off", STREHL_GPU_SCHEDULE="device", STREHL_DEFECT="off",
        STREHL_FINE_SUPPORT="off", STREHL_FIX_CA="off", STREHL_INSECT_COLOR_OUT=str(out / "output"))
    env, removed = b.clean_environment(fields.items())
    command = [str(exe), "merge_cmd::insect_color::controls::fixed_shared_snr_actual_consumer_screen", "--exact", "--nocapture", "--test-threads=1"]
    save(out / "invocation.json", {"command": command, "environment": fields, "removed_environment": removed,
        "executable": reference(exe), "runner": reference(__file__), "helper": reference(HELPER)})
    result = b.run(command, env, ROOT, out / "process.log", api=api,
        wall_seconds=240, cpu_seconds=600, log_bytes=8 << 20, committed_bytes=4 << 30)
    save(out / "process.json", result)
    print(json.dumps({k: result[k] for k in ("exit_code", "error", "wall_seconds", "job_memory")}, indent=2))
    assert result["exit_code"] == 0 and result["error"] is None
    assert all(reference(row["path"]) == row for row in sources)
    report = out / "output/screen.json"
    screen = json.loads(report.read_text())
    save(out / "completion.json", {"report": reference(report), "source_bindings_unchanged": True, "screen_status": screen.get("status"),
        "scope": "Generated actual-consumer screen only; independent interpretation and complete photographs still required."})
