"""Is the 28.5x a units or mask artifact?  Sweep the aura zone (binned vs
full-res convention) and the mask threshold.  A claim that only survives one
arbitrary choice is not a measurement."""
import os, sys
import numpy as np, cv2, tifffile

ROOT = r"C:\dev\strehl-out\V-REVIEW\halo2"
subj = sys.argv[1] if len(sys.argv) > 1 else "flower-bud-alone-cpl"

def lum(a):
    return (0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]).astype(np.float32)

P = lum(tifffile.imread(os.path.join(ROOT, subj + "--pyramid.tiff")).astype(np.float32))
E = lum(tifffile.imread(os.path.join(ROOT, subj + "--estimator.tiff")).astype(np.float32))
M = 0.5 * (P + E)

print("%-6s %-14s %9s %9s %10s %10s %8s" % ("pctl", "aura zone", "mask%", "n aura", "pyr depr", "est depr", "ratio"))
for pctl in (20, 30, 40, 50):
    thr = float(np.percentile(M, pctl))
    sub = (M < thr).astype(np.uint8)
    sub = cv2.morphologyEx(sub, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(sub, 8)
    if n > 1:
        sub = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    d = cv2.distanceTransform(1 - sub, cv2.DIST_L2, 5)
    bg = (sub == 0)
    for (lo, hi, tag) in ((40, 100, "40-100 binned"), (80, 200, "80-200 binned")):
        a = (d >= lo) & (d <= hi) & bg
        f = (d >= 400) & (d <= 900) & bg
        if a.sum() < 5000 or f.sum() < 5000:
            print("%-6d %-14s %9.2f %9d %10s %10s %8s" % (pctl, tag, 100.0*sub.mean(), a.sum(), "-", "-", "too few"))
            continue
        dp = float(np.median(P[f]) - np.median(P[a]))
        de = float(np.median(E[f]) - np.median(E[a]))
        print("%-6d %-14s %9.2f %9d %10.1f %10.1f %8s"
              % (pctl, tag, 100.0*sub.mean(), a.sum(), dp, de,
                 ("%.2fx" % (de/dp)) if abs(dp) > 1e-6 else "n/a"))
print("")
print("CLAIM under test: pyramid 166 DN, estimator 4739 DN, ratio 28.5x")
