r"""Is ORCH's -206.7 DN flat-site darkening a MERGE effect or a TONE-PLACEMENT
artifact that their one-parameter correction could not remove?

contrast_ab.py corrects with a single multiplicative factor: scale = medianA/medianB.
That is a GAIN. The run banner shows the arm moves the tone stage's BLACK point
(0.00211 -> 0.00243, +15.2%) while the WHITE point barely moves (+0.24%).
A gain cannot correct an offset. So the test is: refit B to A with an AFFINE
map (gain AND offset, fitted on the whole image by least squares) and see
whether the flat-site darkening survives.

If the darkening collapses under an affine match, it was tone placement.
"""
import os
import sys

import numpy as np
import tifffile

S = 256
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\bf112"


def lum(p):
    a = tifffile.imread(p)
    if a.ndim == 3:
        return a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def sites(a):
    g = np.hypot(*np.gradient(a))
    H, W = a.shape
    ny, nx = H // S, W // S
    tg = g[:ny * S, :nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    order = np.argsort(tg.ravel())
    out = []
    for grp in (order[:12], order[-12:]):
        m = np.zeros(a.shape, bool)
        for f in grp:
            ty, tx = divmod(int(f), nx)
            m[ty * S:(ty + 1) * S, tx * S:(tx + 1) * S] = True
        out.append(m)
    return out


for pre in ("srgb", "lin"):
    A = os.path.join(OUT, "%s__A-unset.tiff" % pre)
    B = os.path.join(OUT, "%s__F4.tiff" % pre)
    a, b = lum(A), lum(B)
    fm, em = sites(a)
    print("\n=== %s  (A-unset vs F4 = 4,1,1,1,1,1,1) ===" % pre)
    # 1. ORCH's correction: gain only, anchored on the median
    g = np.median(a) / np.median(b)
    b1 = b * g
    print("  ORCH gain-only  (x%.4f): FLAT lift %+8.1f DN   EDGE lift %+8.1f DN"
          % (g, b1[fm].mean() - a[fm].mean(), b1[em].mean() - a[em].mean()))
    # 2. affine: gain AND offset, least squares over the whole frame
    A_ = np.vstack([b.ravel()[::37], np.ones(b.ravel()[::37].size)]).T
    sol, *_ = np.linalg.lstsq(A_, a.ravel()[::37], rcond=None)
    b2 = b * sol[0] + sol[1]
    print("  affine gain+off (x%.4f %+.1f): FLAT lift %+8.1f DN   EDGE lift %+8.1f DN"
          % (sol[0], sol[1], b2[fm].mean() - a[fm].mean(), b2[em].mean() - a[em].mean()))
