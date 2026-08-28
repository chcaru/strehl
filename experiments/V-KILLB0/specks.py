"""V-KILLB0 dark-speck (dust / hot-pixel) census.

The specific worry: on the paper sweep at 64x a population of dark specks
became VISIBLE once the texture around them was smoothed.  Trading grain for
visible dust is not an improvement, so this counts them.

METHOD.  Local background = median filter of radius 5.  residual = lum - bg.
A speck is a connected component of pixels with residual < -k * s, where s is a
ROBUST per-image scale (1.4826 * MAD of the residual) so the threshold does not
follow the very grain the arm is removing.  ** The threshold is deliberately
computed on the DEFAULT arm and reused for both arms **: a threshold refit per
arm would silently rescale itself with the noise and could report "no change"
on an arm where specks became objectively easier to see.

Reported: count, total depth, and -- the number that actually matches the eye --
CONTRAST, |residual| / local background, since a 100 DN pit on a 2000 DN ground
is visible and the same pit on 60000 DN is not.
"""
import sys

import numpy as np
from scipy.ndimage import median_filter, label, find_objects

import bandprobe as bp

RAD = 5
K = 5.0
MAXPIX = 40


def specks(lum, thresh, bg=None):
    if bg is None:
        bg = median_filter(lum, size=2 * RAD + 1)
    res = lum - bg
    mask = res < -thresh
    lab, n = label(mask)
    if n == 0:
        return 0, 0.0, [], bg
    sizes = np.bincount(lab.ravel())
    keep = np.nonzero((sizes >= 1) & (sizes <= MAXPIX))[0]
    keep = keep[keep != 0]
    depth = 0.0
    contrasts = []
    for l in keep:
        sel = lab == l
        d = -res[sel].sum()
        depth += d
        contrasts.append(float(-res[sel].min() / max(bg[sel].mean(), 1.0)))
    return len(keep), float(depth), contrasts, bg


def main():
    A, B, label_ = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")
    # a central window keeps the median filter affordable
    la = bp.channels(bp.load(A))["L"]
    lb = bp.channels(bp.load(B))["L"]
    h, w = la.shape
    y0, x0 = h // 2 - 1024, w // 2 - 1024
    la = la[y0:y0 + 2048, x0:x0 + 2048]
    lb = lb[y0:y0 + 2048, x0:x0 + 2048]

    bgA = median_filter(la, size=2 * RAD + 1)
    resA = la - bgA
    s = 1.4826 * np.median(np.abs(resA - np.median(resA)))
    thresh = K * s
    print(f"== SPECKS {label_}   window 2048x2048 @({y0},{x0})  "
          f"MAD scale(default arm) = {s:.2f} DN  threshold = {thresh:.2f} DN")

    # commissioning: plant 200 pits of known depth into a COPY of A
    rng = np.random.default_rng(11)
    planted = la.copy()
    ys = rng.integers(20, 2028, 200)
    xs = rng.integers(20, 2028, 200)
    pit = 8.0 * s
    for y, x in zip(ys, xs):
        planted[y, x] -= pit
    n0, _, _, _ = specks(la, thresh, bgA)
    n1, _, _, _ = specks(planted, thresh)
    ok = n1 - n0 >= 100
    print(f"  [C1 PLANT] 200 pits of {pit:.1f} DN: count {n0} -> {n1} "
          f"(+{n1 - n0})  {'PASS' if ok else 'FAIL'}")
    nn, _, _, _ = specks(la.copy(), thresh, bgA)
    print(f"  [C0 NULL] same pixels: {n0} vs {nn}  "
          f"{'PASS' if n0 == nn else 'FAIL'}")

    nA, dA, cA, _ = specks(la, thresh, bgA)
    nB, dB, cB, _ = specks(lb, thresh)
    cA = np.array(cA) if cA else np.array([0.0])
    cB = np.array(cB) if cB else np.array([0.0])
    print(f"  default : count {nA:6d}  total depth {dA:12.0f}  "
          f"median contrast {np.median(cA):.4f}  p90 {np.percentile(cA, 90):.4f}")
    print(f"  arm     : count {nB:6d}  total depth {dB:12.0f}  "
          f"median contrast {np.median(cB):.4f}  p90 {np.percentile(cB, 90):.4f}")
    print(f"  ratio   : count x{(nB / nA if nA else float('nan')):.3f}   "
          f"depth x{(dB / dA if dA else float('nan')):.3f}   "
          f"median contrast x{(np.median(cB) / np.median(cA) if np.median(cA) else float('nan')):.3f}")


if __name__ == "__main__":
    main()
