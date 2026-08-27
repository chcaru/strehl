"""vh_hull.py -- convex-hull test for manufactured halo.

THEOREM.  PIL resize is separable and normalises each 1-D kernel to sum 1, so an
output pixel is a weighted sum of master pixels inside the kernel support with
weights summing to 1.  If every weight were non-negative the output would lie in
[min, max] of that support.  BOX and BILINEAR have no negative lobes; BICUBIC and
LANCZOS do.  Therefore an output value ABOVE the local master max is information
that was not in the master: it is manufactured by the kernel's negative lobes.

No edge finder, no plateau, no site picking -- so no phantom-site failure mode.

Units are 8-bit DN, because viewable.py reduces AFTER 16->8, so 8-bit DN is what
the owner's eye actually saw.
"""
import sys, os, json
import numpy as np
from PIL import Image
import tifffile

SHIP_V4 = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\halo"
GALLERY_MAXW = 1400

KERNELS = {"box": Image.BOX, "bilinear": Image.BILINEAR,
           "bicubic": Image.BICUBIC, "lanczos": Image.LANCZOS}
NEG_LOBES = {"box": False, "bilinear": False, "bicubic": True, "lanczos": True}


def to8(a16):
    """Exactly viewable.py's 16->8 conversion."""
    return ((a16.astype(np.uint32) + 128) >> 8).clip(0, 255).astype(np.uint8)


def reduce_f(a8, kernel, maxw=GALLERY_MAXW):
    """Resize the 8-bit plane in float mode: no output rounding, no clipping,
    so the hull bound is exact to float precision."""
    h, w = a8.shape
    nh = round(h * maxw / w)
    im = Image.fromarray(a8.astype(np.float32), mode="F")
    return np.asarray(im.resize((maxw, nh), KERNELS[kernel]), dtype=np.float32)


def hull_bounds(a8, maxw=GALLERY_MAXW, support=18):
    """Local max/min of the master over a generous kernel support, sampled at the
    master coordinate of each output pixel centre.  A LARGER support only makes
    the bound more conservative (bigger max, smaller excess), so one generous
    support for every kernel is safe."""
    import cv2
    h, w = a8.shape
    nh = round(h * maxw / w)
    k = np.ones((2 * support + 1, 2 * support + 1), np.uint8)
    hi = cv2.dilate(a8, k)
    lo = cv2.erode(a8, k)
    sx = w / maxw
    sy = h / nh
    xs = np.clip(np.round((np.arange(maxw) + 0.5) * sx - 0.5).astype(int), 0, w - 1)
    ys = np.clip(np.round((np.arange(nh) + 0.5) * sy - 0.5).astype(int), 0, h - 1)
    return hi[np.ix_(ys, xs)].astype(np.float32), lo[np.ix_(ys, xs)].astype(np.float32)


def excess_stats(out, hi, lo):
    exc = np.maximum(out - hi, 0.0)
    dfc = np.maximum(lo - out, 0.0)
    both = np.maximum(exc, dfc)
    n = both.size
    return {
        "max_excess": float(exc.max()),
        "max_deficit": float(dfc.max()),
        "p99_99": float(np.percentile(both, 99.99)),
        "p99_9": float(np.percentile(both, 99.9)),
        "frac_gt_1dn": float((both > 1.0).sum()) / n,
        "frac_gt_2dn": float((both > 2.0).sum()) / n,
        "frac_gt_4dn": float((both > 4.0).sum()) / n,
        "n_px": int(n),
    }
