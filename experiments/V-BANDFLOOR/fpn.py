r"""Is the REPRODUCIBLE band-0 content at flat sites scene texture, or
fixed-pattern SENSOR noise?

splithalf.py measures reproducibility across disjoint frame subsets of the SAME
scene. Fixed-pattern noise is identical in every frame, so it would reproduce
too, and would be scored as "real". That is the documented fooling direction.

CONTROL: fixed-pattern noise lives at fixed SENSOR coordinates, so it should be
common to renders of DIFFERENT SUBJECTS from the same camera. Scene texture
should not be. Correlate band-0 of two different subjects' masters at the same
output coordinates, searching a small shift range so a constant crop offset
cannot hide a real pattern.

Reads only; both masters are the shipping default arm A-unset.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402
import nscale as ns                                                # noqa: E402
import splithalf as sh                                             # noqa: E402

OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def pearson(a, b):
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / max(np.sqrt((a * a).sum() * (b * b).sum()), 1e-30))


def main():
    # same-scene halves: the number under test
    e, _, _ = ns.load64(os.path.join(OUT, "119MSDCF__EVEN__A-unset.tiff"))
    o, _, _ = ns.load64(os.path.join(OUT, "119MSDCF__ODD__A-unset.tiff"))
    # different scene, same camera/sensor
    x, _, _ = ns.load64(os.path.join(OUT, "113MSDCF__EVEN__A-unset.tiff"))
    y, _, _ = ns.load64(os.path.join(OUT, "113MSDCF__ODD__A-unset.tiff"))
    print("shapes 119 %s   113 %s" % (e.shape, x.shape))

    be, bo, bx, by = (sh.band0(g) for g in (e, o, x, y))
    H = min(be.shape[0], bx.shape[0])
    W = min(be.shape[1], bx.shape[1])
    m = 24                                       # margin for the shift search

    def crop(a, dy=0, dx=0):
        return a[m + dy:H - m + dy, m + dx:W - m + dx]

    print("\n  SAME SCENE, disjoint frames (the reproducibility under test)")
    print("    119 EVEN vs 119 ODD    r = %+.4f" % pearson(crop(be), crop(bo)))
    print("    113 EVEN vs 113 ODD    r = %+.4f" % pearson(crop(bx), crop(by)))

    print("\n  DIFFERENT SCENE, same camera (fixed-pattern control)")
    best = None
    for dy in range(-8, 9, 2):
        for dx in range(-8, 9, 2):
            r = pearson(crop(be), crop(bx, dy, dx))
            if best is None or abs(r) > abs(best[0]):
                best = (r, dy, dx)
    print("    119 EVEN vs 113 EVEN   r = %+.4f at zero shift" % pearson(crop(be), crop(bx)))
    print("    best over dy,dx in [-8,8] step 2:  r = %+.4f at dy=%+d dx=%+d"
          % (best[0], best[1], best[2]))
    best2 = None
    for dy in range(-8, 9, 2):
        for dx in range(-8, 9, 2):
            r = pearson(crop(bo), crop(by, dy, dx))
            if best2 is None or abs(r) > abs(best2[0]):
                best2 = (r, dy, dx)
    print("    119 ODD  vs 113 ODD    best r = %+.4f at dy=%+d dx=%+d"
          % (best2[0], best2[1], best2[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
