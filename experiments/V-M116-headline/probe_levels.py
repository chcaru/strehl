"""V-M116 probe 1: what are the arm files, actually?

Loads the M116 measurement renders and reports level, dtype and shape, so that
any multiplicative gain difference between arms -- which would enter D=log10(sd)
directly and cancel out of Q=D-N -- is visible before any metric is computed.

HAZARD (AGENTS.md): PIL.Image.open() silently downconverts 16-bit RGB TIFF to
8-bit. tifffile only, dtype asserted on the line after the load.
"""
import sys
from pathlib import Path
import numpy as np
import tifffile

M = Path(r"C:\dev\strehl-out\M116\measure")
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
ARMS = ["B0", "B1u", "M0u", "A0", "M0"]

def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} came back {a.dtype}, NOT uint16"
    return a

print(f"tifffile {tifffile.__version__}  numpy {np.__version__}")
for s in SUBJECTS:
    print(f"\n=== {s} ===")
    print(f"{'arm':5s} {'shape':>18s} {'dtype':>8s} {'levels':>7s} "
          f"{'min':>7s} {'p01':>9s} {'median':>9s} {'mean':>10s} {'p99':>9s} {'max':>7s} {'sat%':>7s}")
    for arm in ARMS:
        p = M / f"{s}__{arm}.tif"
        if not p.exists():
            print(f"{arm:5s} MISSING")
            continue
        a = load(p)
        g = a[:, :, 1].astype(np.float64)
        lv = len(np.unique(a[:, :, 1]))
        sat = 100.0 * float((a[:, :, 1] >= 16383).mean())
        print(f"{arm:5s} {str(a.shape):>18s} {str(a.dtype):>8s} {lv:7d} "
              f"{g.min():7.0f} {np.percentile(g,1):9.1f} {np.median(g):9.1f} "
              f"{g.mean():10.2f} {np.percentile(g,99):9.1f} {g.max():7.0f} {sat:7.3f}")
    # gain check between the two compared arms, on robust statistics
    b0 = load(M / f"{s}__B0.tif")[:, :, 1].astype(np.float64)
    b1 = load(M / f"{s}__B1u.tif")[:, :, 1].astype(np.float64)
    for q in (10, 25, 50, 75, 90):
        v0, v1 = np.percentile(b0, q), np.percentile(b1, q)
        print(f"  p{q:02d}: B0 {v0:10.2f}  B1u {v1:10.2f}  ratio {v1/max(v0,1e-9):8.4f}")
    print(f"  mean ratio B1u/B0 = {b1.mean()/b0.mean():.4f}   "
          f"log10 = {np.log10(b1.mean()/b0.mean()):+.5f} dex")
