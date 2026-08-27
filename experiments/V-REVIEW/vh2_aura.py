"""Re-measure the estimator-vs-pyramid aura depression independently.
Mask is built from the MEAN of both arms so it cannot favour either.
Statistic is self-referenced (depression below each arm's OWN far field), which
is the right shape if the two merges sit at different levels -- but that is
CHECKED here, not assumed."""
import os, sys
import numpy as np, cv2, tifffile

ROOT = r"C:\dev\strehl-out\V-REVIEW\halo2"
subj = sys.argv[1] if len(sys.argv) > 1 else "flower-bud-alone-cpl"

def lum(a):
    return (0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]).astype(np.float32)

P = lum(tifffile.imread(os.path.join(ROOT, subj + "--pyramid.tiff")).astype(np.float32))
E = lum(tifffile.imread(os.path.join(ROOT, subj + "--estimator.tiff")).astype(np.float32))
print("subject %s   raster %dx%d" % (subj, P.shape[1], P.shape[0]))
print("PHOTOMETRIC CHECK (must not assume a common space)")
print("   pyramid   median %8.1f  p1 %8.1f  p99 %8.1f" % (np.median(P), np.percentile(P, 1), np.percentile(P, 99)))
print("   estimator median %8.1f  p1 %8.1f  p99 %8.1f" % (np.median(E), np.percentile(E, 1), np.percentile(E, 99)))
print("   global level ratio estimator/pyramid = %.4f" % (np.median(E) / max(np.median(P), 1e-9)))

M = 0.5 * (P + E)
thr = float(np.percentile(M, 40))
sub = (M < thr).astype(np.uint8)
sub = cv2.morphologyEx(sub, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
n, lab, st, _ = cv2.connectedComponentsWithStats(sub, 8)
if n > 1:
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    sub = (lab == big).astype(np.uint8)
print("   subject mask: %.2f%% of frame, threshold %.0f DN" % (100.0 * sub.mean(), thr))

d = cv2.distanceTransform(1 - sub, cv2.DIST_L2, 5)
def med(mask):
    v = mask & (sub == 0)
    return float(np.median(P[v])), float(np.median(E[v])), int(v.sum())

aura = (d >= 80) & (d <= 200)
print("")
print("%-22s %10s %10s %10s" % ("zone", "pyramid", "estimator", "n px"))
pa, ea, na = med(aura)
print("%-22s %10.1f %10.1f %10d" % ("aura 80-200 px", pa, ea, na))
print("")
print("FAR-FIELD COMMISSIONING -- the term the verdict divides by")
print("%-22s %10s %10s %10s %12s %12s %8s" % ("far field def", "pyr far", "est far", "n px", "pyr depr", "est depr", "ratio"))
for lo, hi in ((300, 600), (400, 900), (600, 1200), (300, 10000), (800, 10000)):
    f = (d >= lo) & (d <= hi)
    pf, ef, nf = med(f)
    dp, de = pf - pa, ef - ea
    print("%-22s %10.1f %10.1f %10d %12.1f %12.1f %8s"
          % ("d in [%d,%d]" % (lo, hi), pf, ef, nf, dp, de,
             ("%.2fx" % (de / dp)) if abs(dp) > 1e-6 else "n/a"))
