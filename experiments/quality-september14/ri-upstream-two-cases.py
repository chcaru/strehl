"""Two frozen failures through untouched upstream float64 RI, isolated process.

Explicit diagnostic-only dtype exception: no adapter import, no RAW, no sweep.
"""
from pathlib import Path
import hashlib
import json
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
UPSTREAM = HERE / "residual-interpolation-reference/source"
BASELINE = HERE / "residual-interpolation-controls-1/result.json"
started = time.process_time()
bindings = json.loads((HERE / "residual-interpolation-reference/float32-adaptation.json").read_text())
for name, expected in bindings.items():
    assert hashlib.sha256((UPSTREAM/name).read_bytes()).hexdigest() == expected["original_sha256"]
sys.path.insert(0, str(UPSTREAM))
from demosaic_RI import demosaic_RI
for name in ("demosaic_RI", "mosaic_bayer", "RIgreen_interpolation", "RIGuidefilterResidual",
             "RIguidedfilter3gf", "RIred_interpolation", "RIblue_interpolation", "RIHaResidual", "filtertools"):
    assert Path(sys.modules[name].__file__).resolve().parent == UPSTREAM.resolve(), "source isolation failed"
baseline = json.loads(BASELINE.read_text())
y, x = np.mgrid[:96, :96]
masks = ((y % 2 == 0) & (x % 2 == 0), (y+x) % 2 == 1, (y % 2 == 1) & (x % 2 == 1))
rows = []
for index, kind, frequency in ((9, "independent-chroma", .08), (40, "neutral", .30)):
    case = baseline["cases"][index]
    assert (case["kind"], case["frequency"], case["orientation"], case["phase"]) == (kind, frequency, "diag-plus", .17)
    theta = 2*np.pi*(case["fx"]*x + case["fy"]*y) + case["phase"]
    if kind == "neutral":
        field = .35 + .12*np.cos(theta)
        truth = np.stack((field, field, field), axis=-1).astype(np.float32)
    else:
        truth = np.stack((.42+.10*np.cos(theta+.41), np.full_like(theta, .35),
                          .29+.10*np.sin(theta-.27)), axis=-1).astype(np.float32)
    cfa = np.empty((96,96), dtype=np.float32)
    for c, mask in enumerate(masks):
        cfa[mask] = truth[...,c][mask]
    assert hashlib.sha256(cfa.tobytes()).hexdigest() == case["input_sha256"], "frozen input differs"
    # Match the adapter's scaled f32 samples exactly, then change only internal dtype.
    scaled = (cfa*np.float32(255)).astype(np.float64)
    assert scaled.min() >= 0 and scaled.max() <= 255
    sparse = np.zeros((96,96,3), dtype=np.float64)
    for c, mask in enumerate(masks):
        sparse[...,c][mask] = scaled[mask]
    rgb = demosaic_RI(sparse, "rggb", 1.0, "RI")
    assert rgb.dtype == np.float64 and np.isfinite(rgb).all()
    error = rgb[32:-32,32:-32]/255 - truth[32:-32,32:-32].astype(np.float64)
    chroma = np.stack((error[...,0]-error[...,1], error[...,2]-error[...,1]), axis=-1)
    metrics = dict(rgb_rmse=float(np.sqrt(np.mean(error**2))),
                   chroma_rmse=float(np.sqrt(np.mean(chroma**2))), green_mse=float(np.mean(error[...,1]**2)),
                   signed_bias_rgb=np.mean(error, axis=(0,1)).tolist())
    previous = case["readings"]["32"]
    mhc = previous["previous"]["mhc"]["metrics"]
    rows.append(dict(index=index, kind=kind, frequency=frequency, orientation="diag-plus", phase=.17,
        input_sha256=case["input_sha256"], scaled_input_minmax=[float(scaled.min()),float(scaled.max())],
        unmodified_upstream_float64=metrics, adapted_float32=previous["ri"], shipped_mhc=mhc,
        still_regresses_vs_shipped_mhc=metrics["rgb_rmse"]>1.05*mhc["rgb_rmse"] and metrics["rgb_rmse"]-mhc["rgb_rmse"]>.0005))
for name, expected in bindings.items():
    assert hashlib.sha256((UPSTREAM/name).read_bytes()).hexdigest() == expected["original_sha256"]
elapsed = time.process_time()-started
assert elapsed < 60
result = dict(status="TWO_UNMODIFIED_UPSTREAM_CASES_EXECUTED", cases=rows, cpu_seconds=elapsed,
    source_directory=str(UPSTREAM), original_source_bindings=bindings, trim=32,
    scope="Untouched BSD upstream RI float64, original clips and boundary rules; two fixed frozen synthetic cases only, no adapter or RAW")
out = HERE / "ri-upstream-two-cases-1.json"
with out.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
print(json.dumps({"cases": rows, "cpu_seconds": elapsed}))
