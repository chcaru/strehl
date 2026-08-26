"""Sanity + speed probe before building anything.

Checks, per subject:
  - raw_image_visible shape and that [0::2, 1::2] really is a GREEN sub-lattice
    (raw_colors_visible == 1 there), because V-VEILCLAW's probe hardcodes that
    slice and this map has to reuse the same response or it is a different
    instrument.
  - master .tiff shape and dtype (must be uint16, corpus rule).
  - wall time of one decode, so the run can be budgeted.
"""
import pathlib
import sys
import time

import numpy as np
import rawpy
import tifffile

RAWROOT = pathlib.Path(r"D:\personal\macro")
MASTERS = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1")


def main():
    subs = sorted(p.name for p in RAWROOT.iterdir()
                  if p.is_dir() and any(p.glob("*.ARW")))
    print(f"{'subject':<40}{'nframes':>8}{'raw hw':>14}{'green':>13}"
          f"{'cfa01':>7}{'master hw':>14}{'dtype':>9}{'sec/frame':>10}")
    for s in subs:
        files = sorted((RAWROOT / s).glob("*.ARW"))
        t0 = time.time()
        with rawpy.imread(str(files[len(files) // 2])) as r:
            vis = np.array(r.raw_image_visible, copy=True)
            col = np.array(r.raw_colors_visible[:2, :2], copy=True)
        dt = time.time() - t0
        mp = MASTERS / f"{s}.tiff"
        if mp.exists():
            with tifffile.TiffFile(str(mp)) as tf:
                pg = tf.pages[0]
                mshape, mdt = tuple(pg.shape), str(pg.dtype)
        else:
            mshape, mdt = ("--",), "--"
        g = vis[0::2, 1::2]
        print(f"{s:<40}{len(files):>8}{str(vis.shape):>14}{str(g.shape):>13}"
              f"{int(col[0, 1]):>7}{str(mshape):>14}{mdt:>9}{dt:>10.2f}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
