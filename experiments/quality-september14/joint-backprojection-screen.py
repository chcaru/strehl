"""One prescribed four-update RAW correction of the verified local eight-frame mean.

Failure criteria: visible colour stipple, loss of rung separation, or worse flat
noise invalidate promotion even when the data residual decreases. No tuning.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import time
import numpy as np
import tifffile
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT = HERE / "joint-backprojection-comparison-1"


def main():
    import importlib.util
    def module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        obj = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(obj)
        return obj
    helper = module("screen_helpers", HERE / "joint-local-screen.py")
    save = helper.save
    solver_path = HERE / "joint-cfa-backprojection.py"
    solver_sha = hashlib.sha256(solver_path.read_bytes()).hexdigest()
    assert solver_sha == "18de9215052d96eb959db3208ed81cace73a82050f5f96b3825a2b86b7b96f8e"
    solver = module("bp_screen_solver", solver_path)
    inputs = module("bp_screen_inputs", HERE / "joint-inputs.py")
    shape, data, receipt = inputs.load()
    alignment_path = HERE / "local-green-translation-1/result.json"
    assert hashlib.sha256(alignment_path.read_bytes()).hexdigest() == "ed8880a95a4dc7f0af5da6b27968ae74805eb205780d5281c84790c53eac1b6e"
    alignment = json.loads(alignment_path.read_text())
    assert alignment["source_map_sha256"] == receipt["map_sha256"]
    frames = {f["index"]: f for f in receipt["frames"]}
    corrected = data["xy"].copy()
    for row in alignment["frames"]:
        index = row["frame"]
        if index == 145:
            assert row["at_translation_bound"]
            continue
        assert not row["at_translation_bound"] and row["converged"]
        delta = complex(*row["delta_source_native"]) / complex(*frames[index]["a"])
        corrected[data["frame"] == index] -= np.array([delta.real, delta.imag])
    assert np.array_equal(corrected[data["frame"] == 149], data["xy"][data["frame"] == 149])
    initial_path = HERE / "mhc-catmul-mean-2/local-map-eight-mean-camera-rgb.f32"
    initial_sha = hashlib.sha256(initial_path.read_bytes()).hexdigest()
    assert initial_sha == "17d71a20faaa7d4cdb249c381aeab6ad3ef5faa48c61203eea3a130d6443522a"
    initial = np.fromfile(initial_path, dtype="<f4").reshape(*shape, 3)
    before = initial.copy()
    valid = data["valid"] & (data["frame"] != 145)
    OUT.mkdir()
    started = time.process_time()
    rgb, diag = solver.reconstruct(shape, corrected, data["values"], data["variance"],
                                   data["channels"], valid, initial)
    diag["cpu_seconds"] = time.process_time() - started
    assert np.array_equal(initial.view(np.uint32), before.view(np.uint32))
    assert np.isfinite(rgb).all() and diag["fixed_iterations"] == 4
    arrays = {k: diag.pop(k) for k in ("predictions", "data_residuals", "support_counts", "used_mask")}
    np.savez_compressed(OUT / "diagnostics.npz", **arrays)
    save(OUT / "diagnostics.json", diag)
    output_path = OUT / "local-eight-four-updates-camera-rgb.f32"
    rgb.astype("<f4", copy=False).tofile(output_path)
    source = HERE / "matched-chip-on-1"
    stem = "pale-circuit-frame149-raw"
    exe = HERE / "patch-render-build-2/saved-rgb-render.exe"
    assert hashlib.sha256(exe.read_bytes()).hexdigest() == "3fea4f37deeb5935406d47e050276d72cf9eec5c624f268963b67d4a63f2ea49"
    h, w = shape
    cfg = dict(receipt=str(source / "receipt.json"), width=w, height=h,
        baseline_rgb=str(source / (stem + "-mhc-camera-rgb.f32")),
        baseline_tiff=str(source / (stem + ".tiff")), out=str(OUT / "render"),
        candidates=[dict(name="local-eight-mean", rgb=str(initial_path)),
                    dict(name="local-eight-four-updates", rgb=str(output_path))],
        xyz_to_cam=[[.746, -.2365, -.0588], [-.5687, 1.3442, .2474], [-.0624, .1156, .6584]])
    save(OUT / "render-config.json", cfg)
    command = [str(exe), str(OUT / "render-config.json")]
    run = subprocess.run(command, capture_output=True, text=True, timeout=30)
    (OUT / "render.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    assert run.returncode == 0, run.stderr
    rendered = json.loads((OUT / "render/receipt.json").read_text())
    assert rendered["baseline_differing_u16_samples"] == 0
    for name in rendered["outputs"]:
        im = tifffile.imread(OUT / "render" / (name + ".tiff"))[32:-32, 32:-32]
        Image.fromarray((im.astype(np.uint32) * 255 // 65535).astype(np.uint8)).save(
            OUT / "render" / (name + "-native.png"))
    save(OUT / "receipt.json", dict(solver_sha256=solver_sha, initializer_sha256=initial_sha,
        admitted_frames=list(range(146, 154)), fixed_updates=4, trim=32,
        baseline_product_pixels_exact=True, initializer_bits_unchanged=True,
        render_command=command,
        scope="Same eight saved RAW patches, corrected local source geometry. No fitted gain/bias applied. Clipped observations excluded from updates. Initializer retains its original pinned-sample handling. This is not full-depth stack fusion or a noise-quality claim."))
    print(json.dumps(dict(cpu_seconds=diag["cpu_seconds"], baseline_product_pixels_exact=True)))


if __name__ == "__main__":
    main()
