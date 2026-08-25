"""V-M116: a direct negative control over the WHOLE M116 measurement set.

If any file in the campaign had been narrowed by PIL at any point, its green
plane could hold at most 256 distinct levels. This counts them, on every arm
file M116 scored, plus the election maps pick_single.py reads.

This is evidence about the FILES, which is the only thing that settles it for
a campaign whose scripts I did not write.
"""
from pathlib import Path
import numpy as np, tifffile

ROOT = Path(r"C:\dev\strehl-out\M116")
worst = None
n = 0
for p in sorted((ROOT / "measure").glob("*.tif")):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p.name} loaded as {a.dtype}, NOT uint16"
    lv = len(np.unique(a[:, :, 1]))
    n += 1
    if worst is None or lv < worst[1]:
        worst = (p.name, lv)
    flag = "  <-- SUSPECT (<=256)" if lv <= 256 else ""
    print(f"  {p.name:28s} dtype {a.dtype}  green levels {lv:6d}{flag}")
print(f"\n  {n} measurement files, all uint16, fewest distinct green levels: "
      f"{worst[1]} in {worst[0]}")

print("\n  election maps read by pick_single.py (16-bit greyscale):")
for p in sorted((ROOT / "maps").glob("*A0-index.tif")):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p.name} loaded as {a.dtype}, NOT uint16"
    print(f"  {p.name:32s} dtype {a.dtype} ndim {a.ndim} "
          f"min {a.min()} max {a.max()} distinct {len(np.unique(a))}")
