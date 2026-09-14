"""One diagnostic: admit original container-pinned samples to the frozen solver.

This treats censored lower bounds as measured values and is deliberately NOT a
valid censored likelihood. No RAW decoding, map fitting, or parameter change.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "joint-pins-placebo-1"
SOLVER_SHA = "3e5b208df4f3f43d97ef2669c95a8252b6eb9526c86216c685bb555f674e15d4"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child():
    import numpy as np
    import tifffile
    from PIL import Image
    held = HERE / "joint-comparison-1"
    pins = {str(path): digest(path) for path in (
        HERE / "joint-inputs.py", HERE / "joint-cfa-lanczos.py",
        held / "joint-nine-camera-rgb.f32", held / "joint-nine-diagnostics.json",
        held / "joint-nine-diagnostics.npz")}
    assert pins[str(HERE / "joint-cfa-lanczos.py")] == SOLVER_SHA
    solver = module("pins_placebo_solver", HERE / "joint-cfa-lanczos.py")
    inputs = module("pins_placebo_inputs", HERE / "joint-inputs.py")
    shape, data, source_receipt = inputs.load()
    original_valid = data["valid"]
    admitted = np.ones_like(original_valid)
    started = time.process_time()
    rgb, diagnostic = solver.reconstruct(shape, data["xy"], data["values"],
        data["variance"], data["channels"], admitted)
    cpu = time.process_time() - started
    assert np.isfinite(rgb).all() and all(c["converged"] for c in diagnostic["channels"])
    arrays = {k: diagnostic.pop(k) for k in (
        "predictions", "data_residuals", "support_counts", "used_mask")}
    np.savez_compressed(OUT / "joint-nine-admit-pins-diagnostics.npz", **arrays)
    diagnostic["cpu_seconds"] = cpu
    save(OUT / "joint-nine-admit-pins-diagnostics.json", diagnostic)
    path = OUT / "joint-nine-admit-pins-camera-rgb.f32"
    rgb.astype("<f4", copy=False).tofile(path)
    old = np.fromfile(held / "joint-nine-camera-rgb.f32", dtype="<f4").reshape(*shape, 3)
    old_diagnostic = json.loads((held / "joint-nine-diagnostics.json").read_text())
    with np.load(held / "joint-nine-diagnostics.npz", allow_pickle=False) as old_arrays:
        previous_used = old_arrays["used_mask"]
        assert np.array_equal(previous_used, arrays["used_mask"] & original_valid)
        changed = arrays["used_mask"] & ~previous_used
        assert not np.any(previous_used & ~arrays["used_mask"])
        support_changed = int(np.count_nonzero(old_arrays["support_counts"] != arrays["support_counts"]))
    comparison = []
    for ch, name in enumerate(("R", "G", "B")):
        delta = rgb[32:-32, 32:-32, ch].astype("f8") - old[32:-32, 32:-32, ch]
        comparison.append(dict(channel=name,
            newly_admitted_observations=int(np.count_nonzero(changed & (data["channels"] == ch))),
            previous_observations=old_diagnostic["channels"][ch]["observations"],
            observations=diagnostic["channels"][ch]["observations"],
            previous_iterations=old_diagnostic["channels"][ch]["iterations"],
            iterations=diagnostic["channels"][ch]["iterations"],
            previous_median_variance=old_diagnostic["channels"][ch]["median_provided_variance"],
            median_variance=diagnostic["channels"][ch]["median_provided_variance"],
            changed_interior_pixels=int(np.count_nonzero(delta)),
            interior_rmse_delta=float(np.sqrt(np.mean(delta*delta))),
            interior_mean_delta=float(np.mean(delta)),
            interior_maximum_absolute_delta=float(np.max(np.abs(delta)))))
    config = json.loads((held / "render-config.json").read_text())
    config["out"] = str(OUT / "render")
    config["candidates"] = [{"name": "joint-nine-admit-pins", "rgb": str(path)}]
    save(OUT / "render-config.json", config)
    exe = HERE / "patch-render-build-2/saved-rgb-render.exe"
    assert digest(exe) == "3fea4f37deeb5935406d47e050276d72cf9eec5c624f268963b67d4a63f2ea49"
    command = [str(exe), str(OUT / "render-config.json")]
    rendered = subprocess.run(command, capture_output=True, text=True, timeout=30)
    (OUT / "render.log").write_text(rendered.stdout+rendered.stderr, encoding="utf-8")
    assert rendered.returncode == 0, rendered.stderr
    receipt = json.loads((OUT / "render/receipt.json").read_text())
    assert receipt["baseline_differing_u16_samples"] == 0
    for name in receipt["outputs"]:
        image = tifffile.imread(OUT / "render" / (name+".tiff"))[32:-32, 32:-32]
        assert image.shape == (328, 328, 3)
        Image.fromarray((image.astype(np.uint32)*255//65535).astype(np.uint8)).save(
            OUT / "render" / (name+"-native.png"))
    assert all(digest(Path(path)) == sha for path, sha in pins.items())
    save(OUT / "receipt.json", dict(status="PINS_ADMISSION_PLACEBO_COMPLETE",
        source_pins=pins, shape=list(shape), trim=32, cpu_seconds=cpu,
        originally_invalid_observations=int(np.count_nonzero(~original_valid)),
        newly_admitted_observations=int(np.count_nonzero(changed)),
        changed_support_count_entries=support_changed, comparison=comparison,
        product_baseline_differing_u16_samples=0,
        render_command=command, source_frame_indices=[f["index"] for f in source_receipt["frames"]],
        limits="Diagnostic only: container-pinned lower bounds are incorrectly treated as measurements. Only validity changed; the unchanged solver also recomputes its variance median. No recovery, registration, or image-quality claim."))
    print(json.dumps(dict(status="PINS_ADMISSION_PLACEBO_COMPLETE", cpu_seconds=cpu,
        newly_admitted_observations=int(np.count_nonzero(changed)), comparison=comparison)), flush=True)


def main():
    if "--child" in sys.argv:
        child()
        return
    OUT.mkdir(exist_ok=False)
    bounded = module("pins_placebo_bounded", ROOT / "experiments/m193c-output-grid/bounded-process.py")
    env, _ = bounded.clean_environment(dict(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", RAYON_NUM_THREADS="1").items())
    api = bounded.load_job_api(bounded.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    command = [sys.executable, "-I", "-B", "-X", "faulthandler", str(Path(__file__)), "--child"]
    result = bounded.run(command, env, ROOT, OUT / "process.log", api=api,
        wall_seconds=60, cpu_seconds=30, log_bytes=1<<20, committed_bytes=2<<30)
    save(OUT / "process.json", dict(command=command, result=result))
    print(json.dumps(dict(exit_code=result["exit_code"], error=result["error"], accounting=result["job_accounting"])))
    assert result["exit_code"] == 0 and result["error"] is None and result["terminal_job_accounting"]


if __name__ == "__main__":
    main()
