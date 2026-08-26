"""Commissioning control for the path change: the patched instrument must
reproduce the pre-patch measurement exactly. If any array differs, the SHIP-V1
numbers are not comparable to the GALLERY-FIXED-SRGB numbers and the whole
paired diff is void."""
import numpy as np
from pathlib import Path
a = np.load(Path(r"C:\dev\strehl-out\V-BESTFRAME") / "109MSDCF__paircov_fine.npz")
b = np.load(Path(r"C:\dev\strehl-out\V-BESTFRAME-CTRL") / "109MSDCF__paircov_fine.npz")
ka, kb = sorted(a.files), sorted(b.files)
print("keys identical:", ka == kb)
assert ka == kb, (ka, kb)
bad = 0
for k in ka:
    x, y = a[k], b[k]
    if x.shape != y.shape:
        print(f"  {k:14s} SHAPE {x.shape} vs {y.shape}  DIFFER"); bad += 1; continue
    if x.dtype.kind in "fc":
        same = np.array_equal(x, y, equal_nan=True)
    else:
        same = np.array_equal(x, y)
    d = "" if same else "  <-- DIFFERS"
    if not same:
        bad += 1
        with np.errstate(invalid="ignore"):
            print(f"  {k:14s} {str(x.shape):16s} max|diff| "
                  f"{np.nanmax(np.abs(x.astype(float)-y.astype(float))):.6g}{d}")
    else:
        print(f"  {k:14s} {str(x.shape):16s} identical")
print()
print("ARRAYS DIFFERING:", bad)
print("VERDICT:", "instrument UNCHANGED by the path patch" if bad == 0
      else "INSTRUMENT CHANGED -- comparison void")
