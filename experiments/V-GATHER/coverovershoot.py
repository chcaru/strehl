"""Overshoot, measured directly rather than through a gradient proxy.

A kernel with no negative lobes outputs a CONVEX COMBINATION of its inputs, so
it can never produce a value outside the local range of the source. That is
physics, not a threshold, and it fixes the score of two arms in advance:
nearest and bilinear MUST read ~0 excursion no matter what the subject is.

Local range is dilated by +-2 px so that a 1 px integer-registration residual
cannot manufacture a false excursion. Excursion is reported as a FRACTION of the
local range, so it is invariant to exposure and tone.
"""
import os, sys
import numpy as np
import tifffile
from scipy.ndimage import affine_transform, maximum_filter, minimum_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma
import coverprice as C
from coverkernel import magnify

DIL = 5          # +-2 px dilation
FRAC = 0.02      # count an excursion only past 2% of the local range


def excursion(pairs):
    over, n = 0, 0
    mags = []
    for ref, mov, _ in pairs:
        hi = maximum_filter(ref, size=DIL)
        lo = minimum_filter(ref, size=DIL)
        rng = np.maximum(hi - lo, 1e-6)
        d = np.maximum(mov - hi, lo - mov) / rng
        m = d > FRAC
        over += int(m.sum())
        n += d.size
        if m.any():
            mags.append(float(np.percentile(d[m], 99)))
    return 100.0 * over / n, (float(np.median(mags)) if mags else 0.0)


if __name__ == "__main__":
    a = luma(tifffile.imread(C.OFF)[..., :3].astype(np.float32))
    b = luma(tifffile.imread(C.ON)[..., :3].astype(np.float32))
    sy, sx, oy, ox, n, _, _ = C.fit_scale(a, b)
    s = 0.5 * (sy + sx)

    print("%-42s %12s %12s  %s" % ("arm", "px over (%)", "p99 depth", "physics"))
    print("-" * 88)
    null = [(r, r.copy(), 1.0) for r, _, _ in C.matched(a, a, 1.0, 1.0, oy, ox)]
    p, d = excursion(null)
    print("%-42s %12.4f %12.4f  %s" % ("NULL   image against itself", p, d,
                                       "MUST be 0.0000"))
    for label, order, phys in (("nearest  (order 0)", 0, "CANNOT overshoot"),
                               ("bilinear (order 1)", 1, "CANNOT overshoot"),
                               ("cubic    (order 3)", 3, "CAN overshoot")):
        mg = magnify(a, s, oy, ox, order)
        p, d = excursion(C.matched(a, mg, s, s, oy, ox))
        print("%-42s %12.4f %12.4f  %s" % ("SYNTH  " + label, p, d, phys))
        del mg
    p, d = excursion(C.matched(a, b, sy, sx, oy, ox))
    print("%-42s %12.4f %12.4f  %s" % ("MEASURED  STREHL_COVER", p, d, "<- the question"))
