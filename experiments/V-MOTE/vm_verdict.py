"""V-MOTE P6 -- price the search, and locate the mote per master.

Two arms.

ARM S (the mechanism arm).  V-EYES's census reports the MINIMUM over a +-170 px
neighbourhood.  A minimum over a search is biased deep by an amount set by the
local roughness and the number of independent looks, so the number means nothing
until the same search is run somewhere the mote is not.  Here the identical
+-170 px search is run at edge-matched control anchors in the same master.

ARM L (the location arm).  A tight +-70 px search about the sensor coordinate --
tight enough that it cannot wander onto scene content -- reports where the mote
actually lands per master, and how deep it is against an edge-matched null.

Speed: the annulus geometry is translation-invariant away from the frame edge,
so the least-squares pseudo-inverse is built ONCE and every site is a matvec.
Sites whose annulus is clipped by the frame are handled by the slow path.
Equality of the two paths is asserted at the start (arm E).
"""
import os, sys
import numpy as np
import tifffile
from vm_master import vm_depth, dv5, to8, SITE_P, SITE_M, R_CORE, R_IN, R_OUT

MAST = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
SUBS = ["highly-angled-ruler-mm-cpl", "flower-bud-alone-cpl", "109MSDCF",
        "119MSDCF", "couch-fibers-cpl", "pencil-flatter-angle-cpl",
        "dry-erase-marker-head-cpl", "bee-1-cpl", "lavendar-cpl",
        "flower-bud-with-background-fern-cpl", "pencil-steep-angle-cpl",
        "lead-1-cpl", "coffee-bean", "bee-2-cpl"]

_dy, _dx = np.mgrid[-R_OUT:R_OUT + 1, -R_OUT:R_OUT + 1].astype(np.float64)
_r = np.hypot(_dx, _dy)
_ANN = (_r >= R_IN) & (_r <= R_OUT)
_CORE = _r <= R_CORE
_A = np.stack([np.ones(_ANN.sum()), _dx[_ANN], _dy[_ANN], _dx[_ANN]**2,
               _dx[_ANN]*_dy[_ANN], _dy[_ANN]**2], 1)
_PINV0 = np.linalg.pinv(_A)[0]          # row that yields the constant term
_NCORE = int(_CORE.sum())


def fast_depth(g, cx, cy):
    h, w = g.shape
    if not (R_OUT <= cx < w - R_OUT and R_OUT <= cy < h - R_OUT):
        return vm_depth(g, cx, cy)[0]
    sub = g[cy - R_OUT:cy + R_OUT + 1, cx - R_OUT:cx + R_OUT + 1]
    bg = float(_PINV0 @ sub[_ANN])
    if bg <= 1.0:
        return float("nan")
    return 100.0 * (float(sub[_CORE].sum()) / _NCORE / bg - 1.0)


def search_min(g, cx, cy, rad, step=10):
    h, w = g.shape
    best, bx, by = 1e9, -1, -1
    for y in range(cy - rad, cy + rad + 1, step):
        for x in range(cx - rad, cx + rad + 1, step):
            if not (20 < x < w - 20 and 20 < y < h - 20):
                continue
            v = fast_depth(g, x, y)
            if np.isfinite(v) and v < best:
                best, bx, by = v, x, y
    return best, bx, by


def main():
    for n in SUBS:
        a = tifffile.imread(os.path.join(MAST, n + ".tiff"))
        h, w = a.shape[:2]
        g = a[..., 1].astype(np.float64)
        del a
        g8 = to8(g)
        _, bg8, sd8, _ = dv5(g8, *SITE_M)
        fb = "FLAT+BRIGHT" if (bg8 >= 90 and sd8 <= 8) else "not flat/bright"
        print("\n=== %s  (%dx%d)  DELIVER-V5 admissibility at (7008,4450): bg %.1f DN8 sd %.1f -> %s"
              % (n, w, h, bg8, sd8, fb), flush=True)
        # ARM E: fast path equals slow path on an interior site
        e_fast, e_slow = fast_depth(g, 3000, 4610), vm_depth(g, 3000, 4610)[0]
        print("  ARM E  fast %+0.6f%% vs slow %+0.6f%%  delta %.2e  %s"
              % (e_fast, e_slow, abs(e_fast - e_slow),
                 "OK" if abs(e_fast - e_slow) < 1e-6 else "MISMATCH -- results void"))
        d170, sx, sy = search_min(g, SITE_P[0], SITE_P[1], 170)
        ctrl = []
        for ax in range(400, 6400, 300):
            v, _, _ = search_min(g, ax, SITE_P[1], 170)
            if np.isfinite(v):
                ctrl.append(v)
        ctrl = np.array(ctrl)
        print("  ARM S  +-170 search at the site : %+0.2f%% at (%d,%d)" % (d170, sx, sy))
        print("         same search, %2d edge-matched control anchors on row y=%d:"
              % (len(ctrl), SITE_P[1]))
        print("           mean %+0.2f%%  sd %0.2f  median %+0.2f%%  min %+0.2f%%  max %+0.2f%%"
              % (ctrl.mean(), ctrl.std(ddof=1), np.median(ctrl), ctrl.min(), ctrl.max()))
        print("           => site is %.2f sd of the CONTROL SEARCH null; rank %d of %d"
              % ((d170 - ctrl.mean()) / ctrl.std(ddof=1),
                 int((ctrl < d170).sum()) + 1, len(ctrl) + 1))
        d70, lx, ly = search_min(g, SITE_P[0], SITE_P[1], 70, step=5)
        fixed = np.array([v for ax in range(400, 6400, 50)
                          for v in [fast_depth(g, ax, SITE_P[1])] if np.isfinite(v)])
        print("  ARM L  +-70 search  : %+0.2f%% at (%d,%d)  offset from sensor coord (%+d,%+d)"
              % (d70, lx, ly, lx - SITE_P[0], ly - SITE_P[1]))
        print("         fixed-point edge-matched null n=%d: mean %+0.2f%% sd %0.2f p01 %+0.2f%%"
              % (len(fixed), fixed.mean(), fixed.std(ddof=1), np.percentile(fixed, 1)))
        print("         => %.2f sd" % ((d70 - fixed.mean()) / fixed.std(ddof=1)))
        del g, g8
    return 0


if __name__ == "__main__":
    sys.exit(main())
