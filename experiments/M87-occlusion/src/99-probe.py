"""M87 / 99 -- probe only.  Confirm ORCH's pinned arms carry ROI_LEG and that a
subject silhouette exists there, before designing the s25-V gate ladder.

Writes nothing but stdout.  READ-ONLY on D:\\personal\\macro and on ORCH's
scratch (reads ORCH's pinned TIFFs, writes none of them).
"""
import pathlib

import numpy as np
import tifffile

GATE = pathlib.Path(r"C:\dev\strehl-out\ORCH-gate")
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
Y0, Y1, X0, X1 = 1200, 1900, 300, 1400  # m87lib ROIS["ROI_LEG"]

a = tifffile.imread(GATE / "pin-bee-3-cpl-gate-4.00.tif")
print(f"arm shape {a.shape} dtype {a.dtype}")
print(f"ROI_LEG y {Y0}:{Y1} x {X0}:{X1} in range: "
      f"{Y1 <= a.shape[0] and X1 <= a.shape[1]}")
g = a[Y0:Y1, X0:X1, 1].astype(np.float64)
print(f"ROI_LEG green: min {g.min():.0f} max {g.max():.0f} "
      f"median {np.median(g):.0f}")
for p in (1, 5, 25, 50, 75, 95, 99):
    print(f"  p{p:<3d} {np.percentile(g, p):9.1f}")
del a

for n in ("bee3-leg-sel.npy", "bee3-leg-luma.npy", "bee3-leg-argbest.npy"):
    f = CACHE / n
    if f.exists():
        m = np.load(f, mmap_mode="r")
        print(f"cache {n}: shape {m.shape} dtype {m.dtype}")
    else:
        print(f"cache {n}: ABSENT")
