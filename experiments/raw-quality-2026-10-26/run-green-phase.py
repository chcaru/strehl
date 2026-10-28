"""Root-owned build and bounded screen for the fixed green-phase consumer."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("green_phase_bounded", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
mode = sys.argv[1]
assert mode in ("build", "screen")
suffix = sys.argv[2] if len(sys.argv) > 2 else "1"
assert suffix.isdecimal()
out = CAMPAIGN / ("green-phase-" + mode + "-" + suffix)
assert not out.exists()
out.mkdir()


def ref(path):
    return {"path": str(Path(path).resolve()), **b.binding(path)}


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


if mode == "build":
    listed = subprocess.run(["git", "--work-tree=" + str(ROOT), "ls-files", "--",
                             "*.rs", "Cargo.toml", "Cargo.lock", "**/Cargo.toml"],
                            cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    paths = {ROOT / path for path in listed}
    paths.update((ROOT / "experiments/raw-quality-2026-10-26").rglob("*.rs"))
    paths.update([ROOT / "crates/strehl-core/src/cfa-lattice.rs", ROOT / "crates/strehl-cli/src/direct-cfa-gather.rs"])
    sources = [ref(path) for path in sorted(paths) if path.is_file()]
    save(out / "sources.json", sources)
    command = ["cargo", "test", "--locked", "--offline", "--release", "-p", "strehl-cli", "--lib", "--no-run",
               "--features", "native-direct-planes,native-correction-variance,native-gpu-gather", "--jobs", "8",
               "--message-format=json-render-diagnostics"]
    env, removed = b.clean_environment()
    env.update(CARGO_INCREMENTAL="0", CARGO_BUILD_JOBS="8", STREHL_TEST_TMP=str(CAMPAIGN / "test-tmp"))
    save(out / "invocation.json", dict(command=command, removed_environment=removed, workers=8,
         source_count=len(sources), runner=ref(__file__),
         scope="Cargo directly supervised; measurements run in a separate bounded job after build exit."))
    started = time.monotonic()
    with (out / "artifacts.jsonl").open("xb") as stdout, (out / "build.log").open("xb") as stderr:
        process = subprocess.run(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, check=False)
    save(out / "build-process.json", dict(exit_code=process.returncode, wall_seconds=time.monotonic()-started))
    print((out / "build.log").read_text(encoding="utf-8", errors="replace"))
    assert process.returncode == 0
    assert "Compiling strehl-cli" in (out / "build.log").read_text(encoding="utf-8", errors="replace")
    assert all(ref(row["path"]) == row for row in sources), "source changed during build"
    rows = []
    for line in (out / "artifacts.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    assert any(row.get("reason") == "build-finished" and row.get("success") for row in rows)
    artifacts = [row["executable"] for row in rows if row.get("reason") == "compiler-artifact"
                 and row.get("executable") and row.get("target", {}).get("name") == "strehl_cli"
                 and row.get("profile", {}).get("test")]
    assert len(artifacts) == 1
    exe = out / "cli-tests.exe"
    shutil.copyfile(artifacts[0], exe)
    assert b.binding(exe) == b.binding(artifacts[0])
    save(out / "executable.json", ref(exe))
    print(json.dumps(ref(exe)))
else:
    build = CAMPAIGN / ("green-phase-build-" + suffix)
    sources = json.loads((build / "sources.json").read_text())
    assert all(ref(row["path"]) == row for row in sources)
    exe = build / "cli-tests.exe"
    assert ref(exe) == json.loads((build / "executable.json").read_text())
    fields = dict(RAYON_NUM_THREADS="2", STREHL_PYRAMID_WORKERS="2", STREHL_ALIGN="1", STREHL_FULLRES_GATHER="1",
                  STREHL_DIRECT_PLANES="rounded", STREHL_PROBE_GATHER="green", STREHL_WARP_WRITEBACK="parallel",
                  STREHL_GPU_GATHER="on", STREHL_GPU_GATHER_LOG="off", STREHL_GPU_SCHEDULE="device", STREHL_DEFECT="off",
                  STREHL_FINE_SUPPORT="off", STREHL_FIX_CA="off", STREHL_GREEN_PHASE_OUT=str(out / "output"))
    env, removed = b.clean_environment(fields.items())
    command = [str(exe), "merge_cmd::green_phase_guide::independent_controls::fixed_green_phase_actual_consumer_screen",
               "--ignored", "--exact", "--nocapture", "--test-threads=1"]
    save(out / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
         executable=ref(exe), runner=ref(__file__), helper=ref(HELPER)))
    api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    result = b.run(command, env, ROOT, out / "process.log", api=api,
                   wall_seconds=240, cpu_seconds=600, log_bytes=8 << 20, committed_bytes=4 << 30)
    save(out / "process.json", result)
    print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds", "job_memory")}))
    log = (out / "process.log").read_text(encoding="utf-8", errors="replace")
    print(log[-16000:])
    assert result["exit_code"] == 0 and result["error"] is None
    assert "running 1 test" in log and "1 passed; 0 failed" in log
    assert all(ref(row["path"]) == row for row in sources)
    report = out / "output/screen.json"
    screen = json.loads(report.read_text())
    save(out / "completion.json", dict(report=ref(report), screen_status=screen.get("status"),
         sources_unchanged=True, scope="Generated consumer screen; independent photographic decision still required."))
