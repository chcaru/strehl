"""Fixed source/merge comparisons through the actual test-only RAW consumer."""
from pathlib import Path
import importlib.util, sys, json, hashlib

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
s = importlib.util.spec_from_file_location("bounded", ROOT / "experiments/m193c-output-grid/bounded-process.py")
m = importlib.util.module_from_spec(s); sys.modules[s.name] = m; s.loader.exec_module(m)

def save(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2); f.write("\n")

def ref(path):
    return dict(path=str(path), **m.binding(path))

assert len(sys.argv) == 2
label = sys.argv[1]
assert label in {"printer-on", "printer-off", "printer-placebo", "chip-on", "checker-on"}
printer = label.startswith("printer-")
if printer:
    name, count, old, stem = "3d-printer-piece-cpl", 105, "baseline-1", "printer"
    tone = dict(black=0.008555, white=0.359037, contrast=0.55)
    regions = [dict(name="junction", frame=41, x=3350, y=2450, width=384, height=384),
               dict(name="fibre", frame=39, x=3084, y=3100, width=300, height=300)]
    if label == "printer-placebo":
        regions = [dict(name="surface-placebo", frame=39, x=1150, y=1300, width=300, height=300)]
elif label == "chip-on":
    name, count, old, stem = "uncapped-IC-chip-cpl", 299, "chip-baseline-1", "chip"
    tone = dict(black=0.004293, white=0.946441, contrast=0.55)
    regions = [dict(name="pale-circuit", frame=149, x=1070, y=930, width=384, height=384)]
else:
    name, count, old, stem = "tiny-high-res-calibration-checker-slide-cpl", 150, "checker-baseline-1", "checker"
    tone = dict(black=0.006166, white=0.278799, contrast=0.55)
    regions = [dict(name="checker-middle", frame=75, x=2650, y=2570, width=384, height=384),
               dict(name="white", frame=75, x=3200, y=1600, width=384, height=384)]

rawdir = Path("D:/personal/macro/requests/misc-diagnostic") / name
files = sorted(rawdir.glob("*.ARW"))
assert [p.stem for p in files] == [f"DSC{i:05d}" for i in range(1, count+1)]
inputs = [dict(path=str(p), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns) for p in files]
source_files = json.loads((HERE / "matched-source-build-sources.json").read_text())
for record in source_files:
    assert hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest() == record["sha256"]
exe = HERE / "matched-source-build-1/cli-tests.exe"
held = json.loads((HERE / "matched-source-build-1/executables.json").read_text())["cli-tests"]
assert m.binding(exe)["sha256"] == held["sha256"]
out = HERE / ("matched-" + label + "-1")
config_path = HERE / ("matched-" + label + "-config.json")
warp = HERE / old / (stem + ".warpmap.txt")
config = dict(dir=str(rawdir), map=str(warp), out=str(out), frames=count,
              tone=tone, regions=regions, observe=label != "printer-off")
assert not out.exists()
save(config_path, config)
fields = dict(RAYON_NUM_THREADS="8", STREHL_PYRAMID_WORKERS="8", STREHL_ALIGN="1",
    STREHL_WARPMAP=str(warp), STREHL_FULLRES_GATHER="1", STREHL_DIRECT_PLANES="rounded",
    STREHL_PROBE_GATHER="green", STREHL_WARP_WRITEBACK="parallel", STREHL_GPU_GATHER="on",
    STREHL_GPU_SCHEDULE="device", STREHL_GPU_GATHER_LOG="off", STREHL_DEFECT="off",
    STREHL_MATCHED_SOURCE_CONFIG=str(config_path))
env, removed = m.clean_environment(fields.items())
argv = [str(exe), "merge_cmd::matched_source_tests::matched_source_actual_consumer",
        "--exact", "--ignored", "--nocapture", "--test-threads=1"]
save(HERE / ("matched-" + label + "-invocation.json"), dict(inputs=inputs, configuration=config,
    map=ref(warp), executable=ref(exe), source_files=source_files, runner=ref(Path(__file__)),
    command=argv, environment=fields, removed_environment=removed))
api = m.load_job_api(m.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
r = m.run(argv, env, ROOT, HERE / ("matched-" + label + ".log"), api=api,
          wall_seconds=600, cpu_seconds=3600, log_bytes=4 << 20, committed_bytes=16 << 30)
save(HERE / ("matched-" + label + "-process.json"), r)
print(json.dumps(dict(label=label, exit_code=r["exit_code"], error=r["error"], wall_seconds=r["wall_seconds"])), flush=True)
assert r["exit_code"] == 0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"]
for record in inputs:
    st = Path(record["path"]).stat()
    assert (st.st_size, st.st_mtime_ns) == (record["bytes"], record["mtime_ns"])
for record in source_files:
    assert hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest() == record["sha256"]
assert sum(p.stat().st_size for p in out.iterdir() if p.is_file()) < 512 << 20
save(out / "completion.json", dict(status="MATCHED_SOURCE_REPLAYED", replay=ref(out / "replay.tiff"),
    patches=ref(out / "receipt.json"), original_metadata_unchanged=True))
