r"""Is the 'per-level is flat' reading a result, or is my site set blind to it?

`hul_potency.py` shows --per-level moves 3.79-17.47% of SAMPLES, yet
`hul_report.py` reads its band ratio as 0.9989-1.0000 at the frozen sites. Those
two facts are compatible in two very different ways:

  (a) PerLevel changes many pixels but does not change mid-band contrast, i.e.
      the level-0 clamp is not the mechanism. A real result.
  (b) PerLevel changes pixels somewhere my 48 high-contrast sites do not look,
      and my gauge is simply pointed away from the effect. A sampling artifact.

A conclusion of "no change" is only meaningful if the probe is shown to be
non-trivial AND to move under a real disturbance. This separates (a) from (b)
three ways, none of which uses the site list:

  1. GLOBAL band ratio over the entire frame, no site selection at all.
  2. The change is measured WHERE IT IS LARGEST: the top-1% |delta| tiles are
      located, and the band ratio is recomputed on those tiles specifically.
      If PerLevel raises or lowers mid-band contrast anywhere, it is there.
  3. The |delta| seen at my sites is compared with the |delta| over the frame,
      so a site set that sits in quiet regions is visible as such.
"""
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hul_measure as hm                                           # noqa: E402
import sharpaxis as sa                                             # noqa: E402
from lad_measure import band, finite, WIN                          # noqa: E402

TILE = 256


def lum_of(path):
    return sa.lum(np.asarray(tifffile.imread(path)))


def main():
    subs = sys.argv[1:] or ["foam", "112MSDCF", "coffee-bubbles"]
    for sub in subs:
        pa, pb = hm.arm_path(sub, "inputrange"), hm.arm_path(sub, "perlevel")
        pu = hm.arm_path(sub, "unclamped")
        if not (os.path.exists(pa) and os.path.exists(pb)):
            print("== %-22s INCOMPLETE" % sub)
            continue
        A, B = lum_of(pa), lum_of(pb)
        print("== %-22s lattice %s" % (sub, A.shape))

        # 1. global band ratio, no site selection whatsoever
        ga, gb = band(A), band(B)
        print("   GLOBAL band ratio (whole frame, no sites) : %.6f"
              % (gb / ga if finite(ga, gb) and ga > 0 else float("nan")))
        if os.path.exists(pu):
            U = lum_of(pu)
            gu = band(U)
            print("   GLOBAL band ratio, unclamped              : %.6f"
                  % (gu / ga if finite(ga, gu) and ga > 0 else float("nan")))
            del U

        # 2. find where the two arms differ MOST, and measure there
        d = np.abs(A - B)
        H, W = d.shape
        th, tw = H // TILE, W // TILE
        tiles = d[:th * TILE, :tw * TILE].reshape(th, TILE, tw, TILE).mean(axis=(1, 3))
        order = np.dstack(np.unravel_index(np.argsort(tiles.ravel())[::-1], tiles.shape))[0]
        hot = [(int(r) * TILE, int(c) * TILE) for r, c in order[:24]]
        rs = []
        for (y, x) in hot:
            if y + WIN > H or x + WIN > W:
                continue
            va, vb = band(A[y:y + WIN, x:x + WIN]), band(B[y:y + WIN, x:x + WIN])
            if finite(va, vb) and va > 0:
                rs.append(vb / va)
        if rs:
            rs = np.asarray(rs)
            print("   band ratio AT THE 24 MOST-CHANGED TILES   : median %.6f  min %.6f  max %.6f"
                  % (np.median(rs), rs.min(), rs.max()))
        else:
            print("   band ratio AT THE MOST-CHANGED TILES      : REFUSED (no admissible tile)")

        # 3. is my site set sitting where the action is?
        sites = hm.pick_sites(A, n=48)
        site_d = [float(np.mean(d[s["y"]:s["y"] + WIN, s["x"]:s["x"] + WIN])) for s in sites]
        print("   mean |delta| over whole frame             : %.3f DN" % float(d.mean()))
        print("   mean |delta| at my 48 frozen sites        : %.3f DN" % float(np.mean(site_d)))
        print("   mean |delta| in the 24 hottest tiles      : %.3f DN"
              % float(np.mean([tiles[r, c] for r, c in order[:24]])))
        del A, B, d


if __name__ == "__main__":
    main()
