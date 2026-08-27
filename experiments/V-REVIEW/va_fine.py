"""Fine radial profile: resolve the apparent conflict between the 1:1 crop
(estimator looks BRIGHTER at the rim) and the band table (estimator reads
DARKER at 20-50 px). Both cannot be loose talk; one of them is wrong or the
feature is narrower than the coarse band.

5 px bins from the subject edge out to 300 px, both arms, same mask.
"""
import os, sys, json
import numpy as np, tifffile
from scipy import ndimage

ACC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
LEVEL = 257.0


def luma(a): return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def otsu(v):
    h, _ = np.histogram(v, bins=512, range=(0, 65535)); h = h.astype(np.float64)
    w = np.cumsum(h); m = np.cumsum(h * np.arange(512)); tot, mt = w[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        vb = (mt * w / tot - m) ** 2 / (w * (tot - w))
    vb[~np.isfinite(vb)] = -1
    return (np.argmax(vb) + 0.5) * 65535.0 / 512.0


for SUB in ("flower-bud-alone-cpl", "bee-1-cpl"):
    A = luma(tifffile.imread(os.path.join(ACC, "%s--SHIP-V4.tiff" % SUB)).astype(np.float64))
    B = luma(tifffile.imread(os.path.join(OUT, "%s--estimator.tiff" % SUB)).astype(np.float64))
    A2, B2 = A[::2, ::2], B[::2, ::2]
    t = otsu(A2); d = A2 < t
    if d.mean() > 0.5: d = ~d
    d = ndimage.binary_closing(ndimage.binary_opening(d, np.ones((5, 5))), np.ones((9, 9)))
    lab, k = ndimage.label(d)
    sz = ndimage.sum(d, lab, range(1, k + 1))
    d = ndimage.binary_fill_holes(lab == (int(np.argmax(sz)) + 1))
    dt = ndimage.distance_transform_edt(~d) * 2.0
    fm = (dt >= 800) & (dt < 2000) & (~d)
    if fm.sum() < 5000: fm = (dt >= 400) & (~d)
    fa, fb = np.median(A2[fm]), np.median(B2[fm])
    print("=" * 78)
    print("%s   fine radial profile, 5 px bins, display levels vs own far field" % SUB)
    print("=" * 78)
    print("  %8s %6s %12s %12s %12s" % ("px", "n", "pyramid", "estimator", "pyr-est"))
    rows = []
    for lo in range(0, 120, 5):
        m = (dt >= lo) & (dt < lo + 5) & (~d)
        if m.sum() < 300: continue
        pa = (np.median(A2[m]) - fa) / LEVEL
        pb = (np.median(B2[m]) - fb) / LEVEL
        rows.append((lo, pa, pb))
        print("  %4d-%-4d %6d %+12.2f %+12.2f %+12.2f" % (lo, lo + 5, m.sum(), pa, pb, pa - pb))
    for lo in range(120, 300, 30):
        m = (dt >= lo) & (dt < lo + 30) & (~d)
        if m.sum() < 300: continue
        pa = (np.median(A2[m]) - fa) / LEVEL
        pb = (np.median(B2[m]) - fb) / LEVEL
        print("  %4d-%-4d %6d %+12.2f %+12.2f %+12.2f" % (lo, lo + 30, m.sum(), pa, pb, pa - pb))
    ov = [r for r in rows if r[2] > 0]
    print("  sign convention: POSITIVE = brighter than that arm's own far field.")
    if ov:
        pk = max(ov, key=lambda r: r[2])
        print("  estimator OVERSHOOT peaks %+.2f levels at %d-%d px; it is positive"
              " out to %d px" % (pk[2], pk[0], pk[0] + 5, max(r[0] for r in ov) + 5))
    un = [r for r in rows if r[2] < 0]
    if un:
        pk = min(un, key=lambda r: r[2])
        print("  estimator UNDERSHOOT troughs %+.2f levels at %d-%d px" % (pk[1 + 1], pk[0], pk[0] + 5))
    pv = [r for r in rows if r[1] > 0]
    print("  pyramid max deviation over 0-120 px: %+.2f levels"
          % max((abs(r[1]) for r in rows), default=0.0))
    print()
