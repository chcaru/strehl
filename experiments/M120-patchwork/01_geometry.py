"""M120 step 1: inventory the geometry of every artifact this milestone will use.

No claims here. Shapes, dtypes, ranges only, so that nothing is overlaid before
it is known to be on the same grid.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile

TARGETS = [
    r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif",
    r"C:\dev\strehl-out\bee3-full.tif",
    r"C:\dev\strehl-out\bee3-g0.tif",
    r"C:\dev\strehl-out\bee3-g1.tif",
    r"C:\dev\strehl-out\M93-out\armF-f144.tif",
    r"C:\dev\strehl-out\M93-out\armC-aligned-gate0.tif",
    r"C:\dev\strehl-out\M96-election-margin\bee-3-cpl\elected-index.tif",
    r"C:\dev\strehl-out\M96-election-margin\bee-3-cpl\elected-index-null-iid.tif",
    r"C:\dev\strehl-out\M96-election-margin\bee-3-cpl\margin-q8.tif",
    r"C:\dev\strehl-out\M96-election-margin\bee-3-cpl\confusion-radius.tif",
    r"C:\dev\strehl-out\M96-election-margin\bee-3-cpl\elected-index-crop.tif",
]


def main() -> int:
    for t in TARGETS:
        p = Path(t)
        if not p.exists():
            print(f"MISSING  {t}")
            continue
        with tifffile.TiffFile(p) as tf:
            pg = tf.pages[0]
            arr = pg.asarray()
            print(
                f"{p.name:38s} shape={arr.shape} dtype={arr.dtype} "
                f"min={arr.min()} max={arr.max()} "
                f"photometric={pg.photometric} n_pages={len(tf.pages)}"
            )
            if arr.dtype != np.uint8 and arr.ndim == 2:
                u = np.unique(arr)
                print(f"    n_unique={u.size} first={u[:6]} last={u[-6:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
