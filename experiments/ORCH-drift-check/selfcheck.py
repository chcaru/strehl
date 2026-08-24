"""Falsify my own fact 1235.

I claimed the aligned render is visibly sharper than the zoom-only null on
co-located crops. M97 measured +0.038 px on the ruler and reported no visible
difference on the same bee renders.

The confound that would make me wrong is the same one that fooled me at
thumbnail scale (discipline 606): if the two renders differ in EFFECTIVE
MAGNIFICATION, the more-magnified one looks sharper for reasons unrelated to
registration, and my crops are not comparing like with like.

So measure the relative scale between the two renders directly. If it is not
1.000 my claim is confounded and fact 1235 must be corrected.
"""
import os
import numpy as np
import tifffile

D = r"C:\dev\strehl-out\M86-align"
a = tifffile.imread(os.path.join(D, "bee-3-ALIGNED.tif")).astype(np.float32).mean(axis=2)
z = tifffile.imread(os.path.join(D, "bee3-zoomnull.tif")).astype(np.float32).mean(axis=2)
H, W = a.shape


def ncc(x, y):
    x = x - x.mean(); y = y - y.mean()
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d > 0 else 0.0


def rescale(img, s):
    """Scale about the image centre, sampling with nearest neighbour so that no
    interpolation blur is added to either arm (the quantity under test IS blur)."""
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w]
    sy = np.rint((yy - cy) / s + cy).astype(np.int64)
    sx = np.rint((xx - cx) / s + cx).astype(np.int64)
    ok = (sy >= 0) & (sy < h) & (sx >= 0) & (sx < w)
    out = np.zeros_like(img)
    out[ok] = img[sy[ok], sx[ok]]
    return out, ok


# central window, away from any frame-boundary effects
y0, x0, N = H // 2 - 700, W // 2 - 700, 1400
A = a[y0:y0 + N, x0:x0 + N]
Z = z[y0:y0 + N, x0:x0 + N]

print("baseline NCC (no rescale): %.6f" % ncc(A, Z))

best = (None, -2.0)
for s in np.arange(0.970, 1.0301, 0.0025):
    Zs, ok = rescale(Z, float(s))
    v = ncc(A[ok], Zs[ok])
    if v > best[1]:
        best = (float(s), v)
    print("  scale %.4f  NCC %.6f" % (s, v))

print()
print("BEST relative scale (zoomnull -> aligned): %.4f at NCC %.6f" % best)
if abs(best[0] - 1.0) < 0.0026:
    print("VERDICT: the two renders are at the SAME magnification.")
    print("         My crop comparison was NOT confounded by scale.")
else:
    print("VERDICT: SCALE DIFFERS by %.2f%%. Fact 1235 IS CONFOUNDED and must be corrected."
          % (100 * (best[0] - 1.0)))
