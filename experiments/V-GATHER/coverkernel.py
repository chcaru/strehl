"""What KIND of resample is COVER's upsample? Bracketed by kernels of known physics.

orig_detail reads COVER=on at 1.0167 where an ideal magnification must read 1/s
= 0.9475 exactly (g(x)=f(x/s) => |g'| = |f'|/s). The tempting inference is that
the 7.3% excess is kernel overshoot, i.e. ringing.

THAT INFERENCE IS NOT ALLOWED WITHOUT AN ARM THAT COULD REFUTE IT. Nearest
neighbour has no negative lobes and physically CANNOT ring, yet it preserves
hard pixel steps and therefore also reads high. If nearest reads at or above
COVER, the excess is aliasing, not ringing, and the ringing reading is wrong.

Arms, all applied to the SAME COVER=0 master at the SAME fitted scale about the
SAME fitted centre, then measured through the identical matched-patch path:
  nearest  (order 0)  no negative lobes -- CANNOT ring. Aliases.
  bilinear (order 1)  no negative lobes -- CANNOT ring. Blurs.
  cubic    (order 3)  HAS negative lobes -- can ring.
"""
import os, sys
import numpy as np
import tifffile
from scipy.ndimage import affine_transform
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, acutance, orig_detail
import coverprice as C


def magnify(a, s, oy, ox, order):
    m = np.array([[1.0 / s, 0.0], [0.0, 1.0 / s]])
    off = np.array([oy - oy / s, ox - ox / s])
    return affine_transform(a, m, offset=off, order=order, mode="reflect",
                            prefilter=(order > 1))


if __name__ == "__main__":
    a = luma(tifffile.imread(C.OFF)[..., :3].astype(np.float32))
    b = luma(tifffile.imread(C.ON)[..., :3].astype(np.float32))
    sy, sx, oy, ox, n, ry, rx = C.fit_scale(a, b)
    s = 0.5 * (sy + sx)
    print("fitted scale %.5f about (%.0f, %.0f) from %d patches" % (s, oy, ox, n))

    print("\n%-46s %13s %13s %s" % ("arm", "orig_detail", "acutance", "can it ring?"))
    print("-" * 92)
    print("%-46s %13.4f %13.4f %s" % ("IDEAL magnification (analytic 1/s)",
                                      1.0 / s, float("nan"), "no -- exact"))
    rows = []
    for label, order, ring in (("nearest  (order 0)", 0, "NO -- no negative lobes"),
                               ("bilinear (order 1)", 1, "NO -- no negative lobes"),
                               ("cubic    (order 3)", 3, "yes -- negative lobes")):
        mg = magnify(a, s, oy, ox, order)
        pairs = C.matched(a, mg, s, s, oy, ox)
        o, c = C.ratios(pairs)
        rows.append((label, np.median(o), np.median(c), len(pairs)))
        print("%-46s %13.4f %13.4f %s  (%d pairs)"
              % ("SYNTHETIC " + label, np.median(o), np.median(c), ring, len(pairs)))
        del mg

    pairs = C.matched(a, b, sy, sx, oy, ox)
    o, c = C.ratios(pairs)
    print("%-46s %13.4f %13.4f %s  (%d pairs)"
          % ("MEASURED  STREHL_COVER's own upsample", np.median(o), np.median(c),
             "<- the question", len(pairs)))

    nearest = rows[0][1]
    cover = float(np.median(o))
    print("\nADJUDICATION")
    print("  non-ringing floor (nearest, cannot ring) = %.4f" % nearest)
    print("  COVER                                    = %.4f" % cover)
    if cover <= nearest:
        print("  COVER sits AT OR BELOW a kernel that cannot ring, so orig_detail's")
        print("  excess over 1/s is NOT evidence of ringing. REFUTED.")
    else:
        print("  COVER sits ABOVE a kernel that cannot ring, by %.4f." % (cover - nearest))
        print("  Overshoot survives the arm that could have refuted it.")
