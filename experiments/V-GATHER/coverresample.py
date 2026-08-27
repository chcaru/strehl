"""Divide out the confound: my synthetic arms resample TWICE, COVER resamples ONCE.

fit_to_cover composes the scale into every placement (t' = S_k . t, align_cmd.rs
2233-2245), so COVER's magnification rides the SAME interpolation as the
alignment warp. My synthetic arms take the already-warped COVER=0 output and
resample it again. They therefore carry one extra kernel blur that COVER does
not, which biases them LOW and could manufacture COVER's excess without any
ringing at all.

Price that extra resample directly: scale exactly 1.0, sub-pixel offset only, so
the ONLY thing measured is the kernel's own blur. Then correct each synthetic
arm by it.

NULL ARM: the same resample at offset exactly 0 must read 1.000000 for every
order, or the harness is measuring itself.
"""
import os, sys
import numpy as np
import tifffile
from scipy.ndimage import affine_transform
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, acutance, orig_detail
import coverprice as C

I2 = np.eye(2)


def resample_only(a, off, order):
    return affine_transform(a, I2, offset=(off, off), order=order,
                            mode="reflect", prefilter=(order > 1))


def patch_ratio(a, r, sites):
    o = [orig_detail(r[y:y + C.P, x:x + C.P]) / orig_detail(a[y:y + C.P, x:x + C.P])
         for y, x in sites]
    c = [acutance(r[y:y + C.P, x:x + C.P]) / acutance(a[y:y + C.P, x:x + C.P])
         for y, x in sites]
    return float(np.median(o)), float(np.median(c))


if __name__ == "__main__":
    a = luma(tifffile.imread(C.OFF)[..., :3].astype(np.float32))
    h, w = a.shape
    sites = [(y, x) for (y, x) in C.sites(0, 384, h, w, 420)
             if float(a[y:y + C.P, x:x + C.P].std()) >= C.STD_FLOOR]
    print("%d textured patches, identical coordinates in both arms\n" % len(sites))

    print("%-44s %13s %13s" % ("arm", "orig_detail", "acutance"))
    print("-" * 72)
    cost = {}
    for order, name in ((0, "nearest "), (1, "bilinear"), (3, "cubic   ")):
        r = resample_only(a, 0.0, order)
        o0, c0 = patch_ratio(a, r, sites)
        print("%-44s %13.6f %13.6f" % ("NULL  %s, offset 0.0 px" % name, o0, c0))
        del r
    print()
    for order, name in ((0, "nearest "), (1, "bilinear"), (3, "cubic   ")):
        r = resample_only(a, 0.5, order)
        o5, c5 = patch_ratio(a, r, sites)
        cost[order] = o5
        print("%-44s %13.6f %13.6f" % ("COST  %s, offset 0.5 px" % name, o5, c5))
        del r

    print("\nCORRECTED synthetic magnification (one resample, not two)")
    print("%-44s %13s %13s %13s" % ("kernel", "as measured", "resamp cost", "corrected"))
    print("-" * 88)
    meas = {0: 0.9496, 1: 0.8369, 3: 0.9370}
    for order, name in ((0, "nearest  -- CANNOT ring"), (1, "bilinear -- CANNOT ring"),
                        (3, "cubic    -- can ring")):
        print("%-44s %13.4f %13.4f %13.4f"
              % (name, meas[order], cost[order], meas[order] / cost[order]))
    floor = max(meas[0] / cost[0], meas[1] / cost[1])
    print("\nADJUDICATION  (corrected, single-resample basis)")
    print("  highest NON-RINGING kernel = %.4f" % floor)
    print("  STREHL_COVER               = %.4f" % 1.0167)
    if 1.0167 <= floor:
        print("  REFUTED: COVER sits at or below a kernel that cannot ring. The")
        print("  excess over 1/s is explained by resample count, not overshoot.")
    else:
        print("  COVER still sits %.4f ABOVE the non-ringing ceiling." % (1.0167 - floor))
