"""Prepared three-stage comparator: build, unaligned product development, MIT fork.

No stage runs on import. Each stage must be explicitly selected. Originals are inputs only.
"""
from pathlib import Path
import argparse, importlib.util, json, shutil, sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = HERE / "vitamin-c-baseline-1"
FORK = ROOT / "experiments/M175-fork-arm/bin/focus-stack.exe"
FORK_SHA = "691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac"
SOURCES = ["crates/strehl-cli/examples/quality-batch-develop.rs", "crates/strehl-cli/src/image_out.rs",
           "crates/strehl-cli/Cargo.toml", "crates/strehl-core/Cargo.toml", "crates/strehl-raw/Cargo.toml",
           "crates/strehl-plugin/Cargo.toml", "experiments/native-gpu-gather/Cargo.toml", "Cargo.toml", "Cargo.lock"]
# Every local dependency source/shader, not just the directly named entry points.
for directory in ("crates/strehl-core/src", "crates/strehl-raw/src", "crates/strehl-plugin/src", "experiments/native-gpu-gather/src"):
    SOURCES += [str(p.relative_to(ROOT)) for p in sorted((ROOT / directory).rglob("*")) if p.is_file()]
SOURCES = sorted(set(SOURCES))
spec = importlib.util.spec_from_file_location("vitamin_bounds", ROOT / "experiments/m193c-output-grid/bounded-process.py")
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2); stream.write("\n")


def ref(path):
    return dict(path=str(path), **m.binding(path))


def job(argv, out, label, limits):
    env, removed = m.clean_environment([("RAYON_NUM_THREADS", "8"), ("CARGO_INCREMENTAL", "0")])
    save(out / (label + "-invocation.json"), dict(command=argv, removed_environment=removed,
         explicit_environment=dict(RAYON_NUM_THREADS="8", CARGO_INCREMENTAL="0"), limits=limits))
    api = m.load_job_api(m.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    result = m.run(argv, env, ROOT, out / (label + ".log"), api=api, **limits)
    save(out / (label + "-process.json"), result)
    print(json.dumps({k: result[k] for k in ("exit_code", "error", "wall_seconds")}), flush=True)
    assert result["exit_code"] == 0 and result["error"] is None
    assert result["terminal_job_accounting"] and not result["cleanup_errors"]


def inputs_unchanged(inputs):
    for row in inputs:
        stat = Path(row["path"]).stat()
        assert (stat.st_size, stat.st_mtime_ns) == (row["bytes"], row["mtime_ns"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["build", "develop", "fork"])
    parser.add_argument("--out", type=Path, default=HERE / "vitamin-c-comparator-1")
    args = parser.parse_args(); out = args.out.resolve()
    assert out.is_relative_to(HERE) and out != HERE
    baseline = json.loads((BASE / "invocation.json").read_text())
    inputs = baseline["inputs"]
    assert len(inputs) == 70
    assert [Path(r["path"]).name for r in inputs] == [f"DSC{i:05}.ARW" for i in range(94,164)]
    inputs_unchanged(inputs)
    assert m.binding(FORK)["sha256"] == FORK_SHA
    if args.stage == "build":
        out.mkdir()
        build = out / "build"; build.mkdir()
        sources = [ref(ROOT / p) for p in SOURCES]
        argv = ["cargo", "build", "-p", "strehl-cli", "--example", "quality-batch-develop", "--release",
                "--features", "native-pyramid-profile,native-gpu-gather,native-direct-planes",
                "--target-dir", str(ROOT / "target/native-pyramid-profile"), "--jobs", "2",
                "--locked", "--offline", "--message-format=json-render-diagnostics"]
        save(build / "sources.json", sources)
        job(argv, build, "build", dict(wall_seconds=600,cpu_seconds=1800,log_bytes=16<<20,committed_bytes=8<<30))
        log = (build / "build.log").read_text(encoding="utf-8",errors="replace")
        assert "Compiling strehl-cli" in log
        artifacts = []
        for line in log.splitlines():
            try: row = json.loads(line)
            except ValueError: continue
            if row.get("reason") == "compiler-artifact" and row.get("executable") and row.get("target",{}).get("name") == "quality-batch-develop":
                artifacts.append(row["executable"])
        assert len(artifacts) == 1
        exe = build / "quality-batch-develop.exe"; shutil.copyfile(artifacts[0], exe)
        assert all(ref(Path(r["path"])) == r for r in sources)
        save(build / "executable.json", ref(exe))
        return
    assert out.is_dir()
    build = out / "build"
    binary = json.loads((build / "executable.json").read_text())
    exe = Path(binary["path"]); assert ref(exe) == binary
    sources = json.loads((build / "sources.json").read_text())
    assert all(ref(Path(r["path"])) == r for r in sources)
    if args.stage == "develop":
        # Seventy native RGB16 frames need ~13.85 GB, plus fork output and headroom.
        free = shutil.disk_usage(out).free
        assert free >= 22<<30, f"need 22 GiB free, found {free} bytes"
        cfg = dict(inputs=[r["path"] for r in inputs], input_dir=str(Path(inputs[0]["path"]).parent),
                   out=str(out / "developed"), tone=[0.090420,0.914606,0.550],
                   expected_xyz_to_cam=[[.7460,-.2365,-.0588],[-.5687,1.3442,.2474],[-.0624,.1156,.6584]],
                   fixture_dir=str(HERE / "star-matched-source-1/output"),
                   fixture_original_u16=str(HERE / "star-porous-translation-1/porous-grain/rawler-129.bin"))
        save(out / "develop-config.json",cfg)
        save(out / "development-provenance.json",dict(inputs=inputs,executable=binary,
             baseline=ref(BASE / "vitamin-c.tiff"),sources=sources,free_bytes_before=free,
             baseline_description_tone_precision="6 decimal places; not exact original f32",
             independent_geometry=True,external_ca_correction=False,baseline_ca_correction=True,
             interpretation="Product developer shared; external tone occurs before merge; complete workflows, not merge-only"))
        job([str(exe),str(out / "develop-config.json")],out,"develop",
            dict(wall_seconds=360,cpu_seconds=1800,log_bytes=4<<20,committed_bytes=3<<30))
        receipt = json.loads((out / "developed/receipt.json").read_text())
        assert receipt["status"] == "70_UNALIGNED_NATIVE_RGB16_DEVELOPED" and len(receipt["frames"]) == 70
        assert receipt["golden"]["differing"] == 0
        assert receipt["golden"]["normalized_f32_differences"] == 0
        import tifffile
        with tifffile.TiffFile(receipt["frames"][0]["output"]) as tf, tifffile.TiffFile(BASE / "vitamin-c.tiff") as bf:
            page = tf.pages[0]
            assert page.shape == (4688,7032,3) and str(page.dtype) == "uint16"
            assert page.tags[34675].value == bf.pages[0].tags[34675].value
            format_witness = dict(shape=list(page.shape),dtype=str(page.dtype),icc_equal_baseline=True,
                                  icc_bytes=len(page.tags[34675].value))
        assert sum(p.stat().st_size for p in (out / "developed").iterdir() if p.is_file()) < 15<<30
        inputs_unchanged(inputs)
        save(out / "development-complete.json",dict(status="DEVELOPED_NOT_STACKED",receipt=ref(out / "developed/receipt.json"),original_metadata_unchanged=True,format_witness=format_witness))
        return
    receipt = json.loads((out / "developed/receipt.json").read_text())
    files = [Path(r["output"]) for r in receipt["frames"]]
    assert len(files) == 70
    for file, row in zip(files, receipt["frames"]):
        assert m.binding(file) == dict(sha256=row["output_sha256"], bytes=row["output_bytes"])
    result = out / "fork.tiff"; assert not result.exists()
    # Native fork neighbour alignment and middle reference; fixed usual merge defaults.
    # Disable photometric matching to preserve the deliberately shared development.
    argv = [str(FORK),f"--output={result}","--threads=8","--batchsize=2","--no-opencl",
            "--no-whitebalance","--no-contrast","--consistency=2","--denoise=1.0",
            "--input-colorspace=none","--output-colorspace=srgb","--output-bitdepth=16"]
    argv += [str(p) for p in files]
    save(out / "fork-freeze.json",dict(executable=ref(FORK),development_receipt=ref(out / "developed/receipt.json"),
         command=argv,settings="default neighbour alignment at max2048, reference middle35, consistency2, denoise1; no photo matching; CPU8 batch2",
         scope="whole-product photographic comparison with independent geometry; not merge-only or formal SOTA scorecard"))
    job(argv,out,"fork",dict(wall_seconds=600,cpu_seconds=2400,log_bytes=16<<20,committed_bytes=12<<30))
    import tifffile
    with tifffile.TiffFile(result) as tf:
        shape=list(tf.pages[0].shape); dtype=str(tf.pages[0].dtype)
    assert len(shape)==3 and shape[2]==3 and dtype=="uint16"
    inputs_unchanged(inputs)
    assert ref(exe)==binary and m.binding(FORK)["sha256"]==FORK_SHA
    save(out / "comparison-ready.json",dict(status="WHOLE_OUTPUT_READY_FOR_PHOTOGRAPHIC_REVIEW",image=ref(result),
         shape=shape,dtype=dtype,baseline=ref(BASE / "vitamin-c.tiff"),original_metadata_unchanged=True,
         requirement="Inspect actual overlap at native scale with independent registration; overview is orientation only; no quality inference from change counts"))


if __name__ == "__main__":
    main()
