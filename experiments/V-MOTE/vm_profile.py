"""V-MOTE P3 -- how big is the mote, where does its skirt end, and how much does
the choice of reference annulus move the answer.

Adds the arm vm_depth.py was missing: a plant WIDER than the annulus inner
radius, which is the failure V-REVIEW-dust section 3 measured (an annulus that
sits inside the feature absorbs the feature).  A1/A2 in vm_depth.py cannot fail
-- the plant never touches the annulus -- so they commission the arithmetic and
the sign, nothing more.  A4 below can fail and is reported whether it does.
"""
import os, sys
import numpy as np
from vm_depth import depth, plant, ctrl_sites, QH, QW, SITE, R_CORE

CACHE = r"C:\dev\strehl-out\V-MOTE\cache"
SWEEP = [(25, 37), (30, 45), (40, 60), (45, 80), (55, 90), (60, 110), (90, 140), (100, 170)]


def main():
    f = np.load(os.path.join(CACHE, "flat_all.npy")).astype(np.float64)
    cx, cy = SITE

    print("==== radial profile of mote 2, background from r in [90,140] ====")
    R = 150
    y0, y1 = max(0, cy - R), min(QH, cy + R + 1)
    x0, x1 = max(0, cx - R), min(QW, cx + R + 1)
    sub = f[y0:y1, x0:x1]
    dy = (np.arange(y0, y1) - cy)[:, None] * np.ones((1, x1 - x0))
    dx = np.ones((y1 - y0, 1)) * (np.arange(x0, x1) - cx)[None, :]
    r = np.hypot(dx, dy)
    ann = (r >= 90) & (r <= 140)
    A = np.stack([np.ones(ann.sum()), dx[ann], dy[ann], dx[ann]**2,
                  dx[ann]*dy[ann], dy[ann]**2], 1)
    coef, *_ = np.linalg.lstsq(A, sub[ann], rcond=None)
    bgf = (coef[0] + coef[1]*dx + coef[2]*dy + coef[3]*dx**2
           + coef[4]*dx*dy + coef[5]*dy**2)
    res = 100.0 * (sub / bgf - 1.0)
    print("   r  n      median%%   p10%%    p90%%")
    for lo in range(0, 90, 5):
        m = (r >= lo) & (r < lo + 5)
        v = res[m]
        print("  %3d %5d   %+7.3f  %+7.3f  %+7.3f"
              % (lo, m.sum(), np.median(v), np.percentile(v, 10), np.percentile(v, 90)))

    print("\n==== A4 WIDE PLANT -- can the annulus absorb the feature? ====")
    sites = ctrl_sites(cy)
    v = np.array([depth(f, sx, sy, 45, 80)[0] for sx, sy in sites])
    idx = np.argsort(np.abs(v))[:3]
    for pr in (17, 25, 35, 50):
        for (ri, ro) in ((25, 37), (45, 80)):
            reads = [depth(plant(f, sites[k][0], sites[k][1], -0.04, radius=pr),
                           sites[k][0], sites[k][1], ri, ro)[0] for k in idx]
            print("   plant -4.00%% radius %2d, annulus %3d..%3d -> %+0.3f%%  (%.3fx)"
                  % (pr, ri, ro, np.mean(reads), np.mean(reads) / -4.0))

    print("\n==== annulus sweep on the REAL site ====")
    for (ri, ro) in SWEEP:
        d, na, nc = depth(f, cx, cy, ri, ro)
        vv = np.array([depth(f, sx, sy, ri, ro)[0] for sx, sy in sites])
        vv = vv[np.isfinite(vv)]
        print("   annulus %3d..%3d  n=%5d  depth %+0.3f%%   clean-null mean %+0.3f sd %0.3f"
              % (ri, ro, na, d, vv.mean(), vv.std(ddof=1)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
