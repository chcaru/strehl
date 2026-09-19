"""Bounded build, generated controls, and fixed-tone full RAW consumer replay."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("bounded", ROOT / "experiments/m193c-output-grid/bounded-process.py")
b = importlib.util.module_from_spec(spec); sys.modules[spec.name] = b; spec.loader.exec_module(b)

def save(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, indent=2); f.write("\n")

def ref(path):
    return dict(path=str(path), **b.binding(path))

def job(command, fields, out, wall=600):
    env, removed = b.clean_environment(fields.items())
    save(out / "invocation.json", dict(command=command, environment=fields, removed_environment=removed, runner=ref(Path(__file__))))
    api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    result = b.run(command, env, ROOT, out / "process.log", api=api, wall_seconds=wall,
                   cpu_seconds=3600, log_bytes=16 << 20, committed_bytes=16 << 30)
    save(out / "process.json", result)
    print(json.dumps({k: result[k] for k in ("exit_code", "error", "wall_seconds")}), flush=True)
    assert result["exit_code"] == 0 and result["error"] is None
    assert result["terminal_job_accounting"] and not result["cleanup_errors"]

def source_paths():
    prior = json.loads((ROOT / "experiments/quality-september14/matched-source-build-sources.json").read_text())
    paths = {ROOT / row["path"] for row in prior}
    paths.update(HERE / n for n in ("implementation.rs", "independent-controls.rs", "run.py"))
    paths.update(ROOT / n for n in ("experiments/native-direct-planes/implementation.rs", "crates/strehl-cli/src/merge_cmd.rs",
                 "crates/strehl-cli/src/image_out.rs", "crates/strehl-core/src/demosaic.rs", "Cargo.lock"))
    return sorted(paths)

def build(out):
    out.mkdir()
    (HERE / "implementation.rs").touch()
    sources = [ref(p) for p in source_paths()]
    save(out / "sources.json", sources)
    argv = ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl", "--test", "byte-freeze", "--no-run", "--release",
        "--features", "native-pyramid-profile,native-gpu-gather,native-direct-planes", "--jobs", "2",
        "--target-dir", str(ROOT / "target/native-pyramid-profile"), "--message-format=json-render-diagnostics", "--locked", "--offline"]
    job(argv, dict(RAYON_NUM_THREADS="8", CARGO_INCREMENTAL="0"), out)
    log = (out / "process.log").read_text(encoding="utf-8", errors="replace")
    assert "Compiling strehl-cli" in log
    artifacts = {}
    for line in log.splitlines():
        try: row = json.loads(line)
        except ValueError: continue
        if row.get("reason") == "compiler-artifact" and row.get("executable") and row.get("target", {}).get("name") == "strehl":
            key = "cli-tests" if row["profile"]["test"] else "strehl"
            assert key not in artifacts
            exe = out / (key + ".exe"); shutil.copyfile(row["executable"], exe); artifacts[key] = ref(exe)
    assert set(artifacts) == {"cli-tests", "strehl"}
    assert all(ref(Path(row["path"])) == row for row in sources)
    save(out / "executables.json", artifacts)

def chip_configuration():
    old = ROOT / "experiments/quality-september14"
    manifest = json.loads((old / "local-placement-consumer-inputs-1/manifest.json").read_text())
    warp = old / "chip-baseline-1/chip.warpmap.txt"
    placements = {int(p[0]): p[2:6] for line in warp.read_text().splitlines()
                  if len(p := line.split()) > 5 and p[0].isdigit() and p[1] == "placed"}
    rows = []
    for frame in manifest["frames"]:
        rows.append(dict(file_name=Path(frame["source"]).name, transform_bits=placements[frame["index"]],
                         delta_source_native=frame["delta_source_native"]))
    cfg = dict(schema_version=1, source_dir=str(Path(manifest["frames"][0]["source"]).parent),
               expected_frame_count=299, native_geometry=[7032, 4688], support_native=[1332, 1104, 392, 392],
               taper_native=32, frames=rows)
    save(HERE / "chip-config.json", cfg)
    zero = json.loads(json.dumps(cfg))
    for row in zero["frames"]: row["delta_source_native"] = [0.0, 0.0]
    save(HERE / "chip-zero-config.json", zero)

def replay(args, out):
    out.mkdir()
    artifacts = json.loads((args.build / "executables.json").read_text())
    exe = args.build / "cli-tests.exe"
    assert ref(exe) == artifacts["cli-tests"]
    sources = json.loads((args.build / "sources.json").read_text())
    assert all(ref(Path(row["path"])) == row for row in sources)
    save(out / "sources.json", sources)
    fields = dict(RAYON_NUM_THREADS="8", STREHL_PYRAMID_WORKERS="8", STREHL_ALIGN="1",
        STREHL_FULLRES_GATHER="1", STREHL_DIRECT_PLANES="rounded", STREHL_PROBE_GATHER="green",
        STREHL_WARP_WRITEBACK="parallel", STREHL_GPU_GATHER="on", STREHL_GPU_SCHEDULE="device",
        STREHL_GPU_GATHER_LOG="off", STREHL_DEFECT="off")
    if args.phase == "controls":
        command = [str(exe), "local_placement::independent_controls::", "--nocapture", "--test-threads=1"]
        job(command, dict(RAYON_NUM_THREADS="8"), out, 120)
        log = (out / "process.log").read_text()
        assert "0 passed" not in log and "test result: ok." in log
        return
    rawdir = Path("D:/personal/macro/requests/misc-diagnostic/uncapped-IC-chip-cpl")
    files = sorted(rawdir.glob("*.ARW"))
    assert [p.stem for p in files] == [f"DSC{i:05d}" for i in range(1, 300)]
    inputs = [dict(path=str(p), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns) for p in files]
    warp = ROOT / "experiments/quality-september14/chip-baseline-1/chip.warpmap.txt"
    cfg = dict(dir=str(rawdir), map=str(warp), out=str(out / "output"), frames=299,
               tone=dict(black=0.004293, white=0.946441, contrast=0.55),
               regions=[dict(name="pale-circuit", frame=149, x=1070, y=930, width=384, height=384)], observe=False)
    save(out / "config.json", cfg)
    fields.update(STREHL_WARPMAP=str(warp), STREHL_MATCHED_SOURCE_CONFIG=str(out / "config.json"))
    if args.phase in ("candidate", "zero"):
        placement = HERE / ("chip-config.json" if args.phase == "candidate" else "chip-zero-config.json")
        fields["STREHL_LOCAL_PLACEMENT_FILE"] = str(placement)
        save(out / "placement-binding.json", ref(placement))
    save(out / "inputs.json", dict(inputs=inputs, warp=ref(warp), executable=ref(exe)))
    command = [str(exe), "merge_cmd::matched_source_tests::matched_source_actual_consumer", "--exact", "--ignored", "--nocapture", "--test-threads=1"]
    job(command, fields, out)
    for record in inputs:
        st = Path(record["path"]).stat()
        assert (st.st_size, st.st_mtime_ns) == (record["bytes"], record["mtime_ns"])
    assert all(ref(Path(row["path"])) == row for row in sources)
    save(out / "completion.json", dict(status="FULL_STACK_REPLAYED", image=ref(out / "output/replay.tiff"),
        original_metadata_unchanged=True, input_frames=299, pinned_tone=True))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("configure", "build", "controls", "baseline", "candidate", "zero"))
    parser.add_argument("--build", type=Path, default=HERE / "build-1")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.phase == "configure": chip_configuration()
    elif args.phase == "build": build((args.out or args.build).resolve())
    else: replay(args, (args.out or HERE / (args.phase + "-1")).resolve())
