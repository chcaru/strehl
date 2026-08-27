"""Retry the overshoot instrument with the patch small enough for its own arms.

At scale 1.0554 a P px patch stretches 0.0554*P px across itself. With P=96 that
is 5.3 px, far more than the +-2 px local-range dilation can absorb, so content
near the patch edge falls outside the range for a REGISTRATION reason and the
arms that cannot overshoot read 2.9% instead of 0. P=32 stretches 1.8 px, which
the dilation does absorb.

If the two cannot-overshoot arms still miss zero, the instrument is not
commissioned and its reading on COVER may not be reported.
"""
import os, sys
import numpy as np
import tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coverprice as C
C.P = 32
C.REFINE = 6
C.STD_FLOOR = 200.0
from sharplib import luma
from coverkernel import magnify
from coverovershoot import excursion

if __name__ == "__main__":
    a = luma(tifffile.imread(C.OFF)[..., :3].astype(np.float32))
    b = luma(tifffile.imread(C.ON)[..., :3].astype(np.float32))
    sy, sx, oy, ox, n, _, _ = C.fit_scale(a, b)
    s = 0.5 * (sy + sx)
    print("P=%d  within-patch stretch %.1f px vs +-2 px dilation\n" % (C.P, 0.0554 * C.P))
    print("%-42s %12s %12s  %s" % ("arm", "px over (%)", "p99 depth", "physics"))
    print("-" * 88)
    null = [(r, r.copy(), 1.0) for r, _, _ in C.matched(a, a, 1.0, 1.0, oy, ox, 384, 420)]
    p, d = excursion(null)
    print("%-42s %12.4f %12.4f  %s" % ("NULL   image against itself", p, d, "MUST be 0"))
    floors = []
    for label, order, phys in (("nearest  (order 0)", 0, "CANNOT overshoot"),
                               ("bilinear (order 1)", 1, "CANNOT overshoot"),
                               ("cubic    (order 3)", 3, "CAN overshoot")):
        mg = magnify(a, s, oy, ox, order)
        p, d = excursion(C.matched(a, mg, s, s, oy, ox, 384, 420))
        if order in (0, 1):
            floors.append(p)
        print("%-42s %12.4f %12.4f  %s" % ("SYNTH  " + label, p, d, phys))
        del mg
    pc, dc = excursion(C.matched(a, b, sy, sx, oy, ox, 384, 420))
    print("%-42s %12.4f %12.4f  %s" % ("MEASURED  STREHL_COVER", pc, dc, "<- the question"))
    print("\nCOMMISSIONING VERDICT")
    worst = max(floors)
    print("  cannot-overshoot arms read up to %.4f%% where physics demands 0." % worst)
    if worst > 0.5:
        print("  NOT COMMISSIONED -- the floor is not zero, so COVER's %.4f%% may" % pc)
        print("  not be attributed to overshoot. REFUSED.")
    else:
        print("  COMMISSIONED -- floor is %.4f%%, COVER reads %.4f%%." % (worst, pc))
