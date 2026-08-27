"""Correct by the phase distribution a magnification ACTUALLY samples.

coverresample.py divided by the cost at 0.5 px, which is each kernel's WORST
sub-pixel phase. A magnification about the centre visits phase frac((p-o)*s),
which sweeps uniformly across the field -- so the worst case over-corrects and
inflates the non-ringing ceiling. An over-estimated ceiling that COVER happens
to sit under is not a refutation, it is a flattering artifact of my own arm.

Average the kernel cost over uniformly sampled phases instead, then re-adjudicate.

NULL arm retained: phase 0 must read 1.000000 for every order.
"""
import os, sys
import numpy as np
import tifffile
from scipy.ndimage import affine_transform
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, orig_detail
import coverprice as C

I2 = np.eye(2)
NPH = 8


def cost_over_phases(a, sites, order):
    vals = []
    for k in range(NPH):
        off = k / NPH
        r = affine_transform(a, I2, offset=(off, off), order=order,
                             mode="reflect", prefilter=(order > 1))
        v = float(np.median([orig_detail(r[y:y + C.P, x:x + C.P])
                             / orig_detail(a[y:y + C.P, x:x + C.P])
                             for y, x in sites]))
        vals.append((off, v))
        del r
    return vals


if __name__ == "__main__":
    full = luma(tifffile.imread(C.OFF)[..., :3].astype(np.float32))
    a = np.ascontiguousarray(full[1400:3400, 2200:4200])
    del full
    h, w = a.shape
    sites = [(y, x) for (y, x) in C.sites(0, 192, h, w, 64)
             if float(a[y:y + C.P, x:x + C.P].std()) >= C.STD_FLOOR]
    print("crop %s, %d textured patches, %d sub-pixel phases\n" % (a.shape, len(sites), NPH))

    meas = {0: 0.9496, 1: 0.8369, 3: 0.9370}
    print("%-10s %s" % ("kernel", "  ".join("ph%.3f" % (k / NPH) for k in range(NPH))))
    print("-" * 80)
    mean = {}
    for order, name in ((0, "nearest"), (1, "bilinear"), (3, "cubic")):
        vals = cost_over_phases(a, sites, order)
        mean[order] = float(np.mean([v for _, v in vals]))
        print("%-10s %s   mean %.4f"
              % (name, "  ".join("%.4f" % v for _, v in vals), mean[order]))
    print("\nphase 0 is the NULL and must read 1.000000 -- see column one.")

    print("\n%-30s %11s %11s %11s %11s"
          % ("kernel", "measured", "cost@0.5", "cost@mean", "corrected"))
    print("-" * 80)
    ceil_nr = -1
    for order, name, ring in ((0, "nearest", False), (1, "bilinear", False),
                              (3, "cubic", True)):
        corr = meas[order] / mean[order]
        print("%-30s %11.4f %11s %11.4f %11.4f"
              % (name + (" -- CANNOT ring" if not ring else " -- can ring"),
                 meas[order], "-", mean[order], corr))
        if not ring:
            ceil_nr = max(ceil_nr, corr)

    print("\nADJUDICATION  (phase-averaged, single-resample basis)")
    print("  highest NON-RINGING kernel = %.4f" % ceil_nr)
    print("  STREHL_COVER               = %.4f" % 1.0167)
    if 1.0167 <= ceil_nr:
        print("  REFUTED: COVER is at or below a kernel that physically cannot ring.")
    else:
        print("  COVER sits %.4f above the non-ringing ceiling." % (1.0167 - ceil_nr))
