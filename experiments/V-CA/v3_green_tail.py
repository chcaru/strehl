"""V-CA v3 -- how BIG are the green-plane changes a red-only correction makes?

Fact 1589 / M110 s14.8 record that 94.41 % of green pixels move.  A fraction is
not a magnitude.  This prints the distribution of |dG| in 8-bit display levels
(1 lv = 257 DN of the 16-bit render), which is the unit that decides whether a
change is visible, and the same for red and blue for scale.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M110-sheet")
LV = 257.0
QS = [50, 90, 99, 99.9, 99.99, 100]


def run(subject):
    off = tifffile.imread(str(ROOT / subject / "default.tif"))
    on = tifffile.imread(str(ROOT / subject / "ca.tif"))
    print(f"\n===== {subject} =====")
    print(f"  {'plane':<6}" + "".join(f"{('p'+str(q)):>10}" for q in QS)
          + f"{'frac>1lv':>10}{'frac>4lv':>10}")
    for ci, nm in ((0, "R"), (1, "G"), (2, "B")):
        d = np.abs(on[..., ci].astype(np.int32) - off[..., ci].astype(np.int32)).astype(np.float32)
        qs = np.percentile(d, QS) / LV
        f1 = float((d > LV).mean() * 100)
        f4 = float((d > 4 * LV).mean() * 100)
        print(f"  {nm:<6}" + "".join(f"{v:10.3f}" for v in qs)
              + f"{f1:9.2f}%{f4:9.2f}%")


if __name__ == "__main__":
    for s in sys.argv[1:]:
        run(s)
