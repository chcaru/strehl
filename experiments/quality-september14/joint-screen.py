"""Bounded common-grid RAW reconstruction and independent-frame prediction.

Run only after reviewing the independent synthetic result. No additional RAW
decode. Render through the saved actual product developer with baseline equality.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import subprocess
import time
import numpy as np
import tifffile
from PIL import Image

HERE = Path(__file__).resolve().parent
SOLVERS = {
    "bilinear": ("joint-cfa.py", "05fe15bece42cb44f667219c35423261358bc4b8c5b594b0c2630c545748b490"),
    "lanczos": ("joint-cfa-lanczos.py", "3e5b208df4f3f43d97ef2669c95a8252b6eb9526c86216c685bb555f674e15d4"),
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False,
                  default=lambda value: value.item() if isinstance(value, np.generic) else value.tolist())
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls-reviewed", action="store_true", required=True)
    parser.add_argument("--output-dir", default="joint-comparison-1")
    parser.add_argument("--solver", choices=list(SOLVERS), default="lanczos")
    args = parser.parse_args()
    assert args.controls_reviewed
    out = (HERE/args.output_dir).resolve()
    assert out.parent == HERE and out.name.startswith("joint-comparison-")
    out.mkdir()
    solver_file, solver_sha = SOLVERS[args.solver]
    assert hashlib.sha256((HERE/solver_file).read_bytes()).hexdigest() == solver_sha
    solver = load_module("fixed_joint_solver", HERE/solver_file)
    inputs = load_module("fixed_joint_inputs", HERE/"joint-inputs.py")
    shape, data, source_receipt = inputs.load()
    xy, v, variance, channels, valid = (data[k] for k in ("xy", "values", "variance", "channels", "valid"))
    hold = np.isin(data["frame"], [147, 151])
    training = valid & ~hold
    origin = complex(*source_receipt["target_origin_native"])
    center = complex(3516, 2344)
    wrong_xy = xy.copy()
    for frame in source_receipt["frames"]:
        mask = data["frame"] == frame["index"]
        z = xy[mask,0] + 1j*xy[mask,1] + origin
        source_z = center + complex(*frame["a"])*(z-center) + 2*complex(*frame["b_plane"])
        wrong = 2*(source_z-origin) - (z-origin)
        wrong_xy[mask,0], wrong_xy[mask,1] = wrong.real, wrong.imag
    candidates = []
    outputs = {}
    for name, positions, admitted in (("joint-nine", xy, valid),
                                      ("joint-seven-heldout", xy, training),
                                      ("wrong-map-seven", wrong_xy, training)):
        started = time.process_time()
        rgb, diagnostic = solver.reconstruct(shape, positions, v, variance, channels, admitted)
        elapsed = time.process_time()-started
        assert np.isfinite(rgb).all()
        arrays = {k: diagnostic.pop(k) for k in ("predictions", "data_residuals", "support_counts", "used_mask")}
        np.savez_compressed(out/(name+"-diagnostics.npz"), **arrays)
        diagnostic["cpu_seconds"] = elapsed
        save(out/(name+"-diagnostics.json"), diagnostic)
        assert all(c["converged"] for c in diagnostic["channels"]), "Numerical solve did not converge"
        path = out/(name+"-camera-rgb.f32")
        rgb.astype("<f4", copy=False).tofile(path)
        outputs[name] = rgb
        candidates.append(dict(name=name, rgb=str(path)))
        print(name, f"completed in {elapsed:.3f} CPU s", flush=True)
    source = HERE/"matched-chip-on-1"
    stem = "pale-circuit-frame149-raw"
    baseline_path = source/(stem+"-mhc-camera-rgb.f32")
    baseline = np.fromfile(baseline_path, dtype="<f4").reshape(*shape, 3)
    # Same held-out measurements for every arm, with a fixed 32-pixel interior.
    h, w = shape
    common = hold & valid & (xy[:,0]>=32) & (xy[:,0]<w-33) & (xy[:,1]>=32) & (xy[:,1]<h-33)
    assert common.sum() > 10000
    rows = []
    for name, rgb in [("reference149-mhc", baseline), *outputs.items()]:
        for channel in range(3):
            indices = np.flatnonzero(common & (channels == channel))
            predicted = solver._design(shape, xy[indices]) @ rgb[...,channel].ravel()
            error = predicted-v[indices]
            rows.append(dict(arm=name, channel=channel, observations=len(indices),
                             rmse=float(np.sqrt(np.mean(error*error, dtype=np.float64))),
                             mean_error=float(np.mean(error, dtype=np.float64)),
                             mean_error_squared_over_observation_variance=float(np.mean(error*error/variance[indices], dtype=np.float64))))
    save(out/"heldout.json", dict(frames=[147,151], common_observations=int(common.sum()), results=rows,
        limits="Seven-frame arms exclude these observations. Nine-frame arm includes them and is NOT held-out validation. Residual can favour blur; observation variance excludes reconstruction uncertainty and optical/geometry mismatch, so ratios are not calibrated chi-square tests."))
    exe = HERE/"patch-render-build-2/saved-rgb-render.exe"
    assert hashlib.sha256(exe.read_bytes()).hexdigest() == "3fea4f37deeb5935406d47e050276d72cf9eec5c624f268963b67d4a63f2ea49"
    config = dict(receipt=str(source/"receipt.json"), width=w, height=h,
                  baseline_rgb=str(baseline_path), baseline_tiff=str(source/(stem+".tiff")),
                  out=str(out/"render"), candidates=candidates,
                  xyz_to_cam=[[.746,-.2365,-.0588],[-.5687,1.3442,.2474],[-.0624,.1156,.6584]])
    save(out/"render-config.json", config)
    command = [str(exe), str(out/"render-config.json")]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    (out/"render.log").write_text(result.stdout+result.stderr, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    rendering = json.loads((out/"render/receipt.json").read_text())
    assert rendering["baseline_differing_u16_samples"] == 0
    for name in rendering["outputs"]:
        image = tifffile.imread(out/"render"/(name+".tiff"))[32:-32,32:-32]
        Image.fromarray((image.astype(np.uint32)*255//65535).astype(np.uint8)).save(out/"render"/(name+"-native.png"))
    save(out/"receipt.json", dict(solver_sha256=solver_sha, solver=args.solver, product_baseline_exact=True,
        render_command=command, target_shape=list(shape), trim=32,
        coordinate_scope="Reference149 original sensor gauge, no CA correction, native1x only",
        invalid_clipped_observations=int((~valid).sum()),
        scope="Small focused-window experiment; no all-depth fusion or default change"))


if __name__ == "__main__":
    main()
