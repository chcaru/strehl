"""V-MOTE P2 -- measure the mote depth on the flats from first principles.

The statistic, fixed before it was run:

    core  = mean of the normalised flat over a disc of radius R_CORE quads
    bg    = a 2nd-order polynomial in (dx,dy) least-squares fitted to the
            annulus R_IN <= r <= R_OUT, evaluated at the site
    depth = 100 * (core / bg - 1)     [negative = darker than background]

A POLYNOMIAL FIT is used instead of the census's box mean because the site is
38 quads from the bottom edge and a box mean of radius 64 is truncated there.
A truncated *mean* is biased by any gradient; a truncated *model fit* is not,
provided the model is right.  Whether it is right is not asserted -- it is
commissioned below on the same field, at the same edge distance.

Commissioning arms, all at control sites with the SAME edge distance as the
real site so that edge falloff is in the null rather than argued away:

  A0 CLEAN     no plant, N control sites -> the null distribution.  A site that
               reads far from 0 here means the edge fabricates motes.
  A1 PLANT-    a -4.00% disc of the real mote's radius -> must read ~-4%.
  A2 PLANT+    a +4.00% disc -> must read ~+4%.  A statistic that calls a
               bright spot a shadow has the wrong sign and cannot be trusted.
  A3 DIVIDE    the real mote divided out -> must read ~0.
"""
import os, sys
import numpy as np

CACHE = r"C:\dev\strehl-out\V-MOTE\cache"
QH, QW = 2344, 3520
SITE = (3434, 2305)          # embedded map, mote 2, in QUADS
MOTE1 = (3202, 119)
R_CORE = 8
ANNULI = [(25, 37), (45, 80)]
PLANT_R = 17                 # measured half-width of the real disc, quads
NCTRL = 240

yy, xx = np.mgrid[0:QH, 0:QW]


def depth(f, cx, cy, r_in, r_out, r_core=R_CORE, order=2):
    """Return (depth_pct, n_annulus, n_core)."""
    x0, x1 = max(0, cx - r_out), min(QW, cx + r_out + 1)
    y0, y1 = max(0, cy - r_out), min(QH, cy + r_out + 1)
    sub = f[y0:y1, x0:x1]
    dy = (np.arange(y0, y1) - cy)[:, None] * np.ones((1, x1 - x0))
    dx = np.ones((y1 - y0, 1)) * (np.arange(x0, x1) - cx)[None, :]
    r = np.hypot(dx, dy)
    ann = (r >= r_in) & (r <= r_out)
    core = r <= r_core
    if ann.sum() < 30 or core.sum() < 5:
        return float("nan"), int(ann.sum()), int(core.sum())
    a, b = dx[ann], dy[ann]
    cols = [np.ones_like(a), a, b]
    if order >= 2:
        cols += [a * a, a * b, b * b]
    A = np.stack(cols, 1)
    coef, *_ = np.linalg.lstsq(A, sub[ann], rcond=None)
    bg = coef[0]                      # value at dx=dy=0
    return 100.0 * (float(sub[core].mean()) / float(bg) - 1.0), int(ann.sum()), int(core.sum())


def plant(f, cx, cy, frac, radius=PLANT_R):
    g = f.copy()
    y0, y1 = max(0, cy - radius), min(QH, cy + radius + 1)
    x0, x1 = max(0, cx - radius), min(QW, cx + radius + 1)
    d = np.hypot(xx[y0:y1, x0:x1] - cx, yy[y0:y1, x0:x1] - cy)
    m = d <= radius
    g[y0:y1, x0:x1][m] *= (1.0 + frac)
    return g


def ctrl_sites(cy, n=NCTRL, exclude=((3434, 2305), (3202, 119))):
    """Control sites at the SAME row (same edge distance) as the real site."""
    out = []
    for cx in range(120, QW - 120, 13):
        if all(abs(cx - ex) > 120 or cy != ey for ex, ey in exclude):
            out.append((cx, cy))
    return out[:n]


def main():
    fields = {k: np.load(os.path.join(CACHE, "flat_%s.npy" % k)).astype(np.float64)
              for k in ("all", "odd", "even", "b1", "b2")}
    f = fields["all"]
    cx, cy = SITE
    print("site quad (%d,%d) = photosite (%d,%d)" % (cx, cy, 2 * cx, 2 * cy))
    print("edge distances (quads): left %d right %d top %d bottom %d"
          % (cx, QW - 1 - cx, cy, QH - 1 - cy))

    for (r_in, r_out) in ANNULI:
        print("\n==== annulus %d..%d quads ====" % (r_in, r_out))
        sites = ctrl_sites(cy)
        # A0 CLEAN
        v = np.array([depth(f, sx, sy, r_in, r_out)[0] for sx, sy in sites])
        v = v[np.isfinite(v)]
        print("  A0 CLEAN   n=%3d  mean %+0.3f%%  sd %0.3f  p05 %+0.3f  p95 %+0.3f  min %+0.3f  max %+0.3f"
              % (len(v), v.mean(), v.std(ddof=1), np.percentile(v, 5),
                 np.percentile(v, 95), v.min(), v.max()))
        # A1/A2 plants at the 3 cleanest control sites
        idx = np.argsort(np.abs(v))[:3]
        for tag, frac in (("A1 PLANT-", -0.04), ("A2 PLANT+", +0.04)):
            reads = []
            for k in idx:
                sx, sy = sites[k]
                reads.append(depth(plant(f, sx, sy, frac), sx, sy, r_in, r_out)[0])
            print("  %s planted %+0.2f%% r=%d -> reads %s   recovery %0.3fx"
                  % (tag, 100 * frac, PLANT_R,
                     " ".join("%+0.3f%%" % z for z in reads),
                     float(np.mean(reads)) / (100 * frac)))
        # the real site
        d_all, na, nc = depth(f, cx, cy, r_in, r_out)
        print("  --- mote 2 at (%d,%d): annulus n=%d core n=%d" % (cx, cy, na, nc))
        for k in ("all", "odd", "even", "b1", "b2"):
            dk = depth(fields[k], cx, cy, r_in, r_out)[0]
            print("      %-5s depth %+0.3f%%" % (k, dk))
        # A3 divide the mote out
        # multiplicative restoration of exactly the measured depth over PLANT_R
        d3 = depth(plant(f, cx, cy, -d_all / 100.0), cx, cy, r_in, r_out)[0]
        print("      A3 DIVIDE  after dividing the measured depth out: %+0.3f%%" % d3)
        # mote 1 for reference
        print("      mote 1 (%d,%d) depth %+0.3f%%"
              % (MOTE1[0], MOTE1[1], depth(f, MOTE1[0], MOTE1[1], r_in, r_out)[0]))
        z = (d_all - v.mean()) / v.std(ddof=1)
        print("  => mote 2 = %+0.3f%%, %.2f sd of the edge-matched clean null" % (d_all, z))

    # row profile: the falloff and the mote, side by side, no model at all
    print("\n==== raw row profile through the site, no background model ====")
    print("   normalised flat, mean of rows %d..%d, every 10 quads" % (cy - 3, cy + 3))
    band = fields["all"][cy - 3:cy + 4, :].mean(0)
    for x0 in range(3334, 3520, 10):
        print("      x=%4d  %.5f%s" % (x0, band[x0], "   <-- SITE" if abs(x0 - cx) < 5 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
