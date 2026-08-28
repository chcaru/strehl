"""Do two strehl renders of one subject differ by a TRANSLATION, or by more?

The ladder aligns every site with an integer-only shift, and the shifts it found
are not consistent with a rigid displacement. Within a single rung, the six
site offsets spanned 35 px in y and 79 px in x:

    rung  18  a->ref  (-18,-34) (-16,26) (-8,-38) (4,-29) (12,-35) (17,-53)

A translation gives one offset everywhere. A spread that large means the two
renders are related by something with structure across the field, and the
obvious candidate is a residual SCALE: bee-3-cpl drifts 232.7 px corner to
corner across its bracket, each render picks its own alignment reference from
whichever frames it was given, and there is no flag to pin it. A 1% scale
difference over a 7032 px frame is 70 px of displacement at the edges, which is
the size of the effect.

This fits offset = t + (s-1) * (position - centre) by least squares over a grid
of sites and reports how much of the offset field the model absorbs. It is a
falsifiable claim: if the residual after fitting is as large as the raw spread,
the arms do not differ by a scale and the spread is something else.

It matters beyond this lane. Every cross-arm difference statistic in this project
-- strehl against enfuse, N=63 against N=32, arm a against arm b -- assumes the
two images can be brought onto a common grid. If they differ by a scale, no
single shift does that, and a per-site shift only works where the site is small
enough that the scale looks like a translation inside it.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402
import nscene  # noqa: E402

OUT = r"C:\dev\strehl-out\V-H2H2\ladder2\out"
SITE, PAD = 384, 64
GRID_Y, GRID_X = 4, 6
MARGIN = 700


def green(p, expo):
    return bandlib.display(tifffile.imread(p)[..., 1].astype(np.float64), expo)


def fit(pts, offs):
    """Two models of the offset field, reported together.

    ISOTROPIC  offset = t + k * (p - centre)              3 parameters
    AFFINE     offset = t + M @ (p - centre), M 2x2       6 parameters

    The isotropic model is the one a pure magnification change produces. The
    affine model is what "each render chose its own alignment reference frame"
    produces in general: the reference frame differs in scale, rotation and shear
    as well as position, because the bracket drifts and rotates as it is racked.
    Fitting both separates a magnification difference from a general geometric
    disagreement, and reporting only the one that happened to fit would be
    choosing the conclusion.
    """
    p = np.asarray(pts, dtype=np.float64)
    o = np.asarray(offs, dtype=np.float64)
    c = p.mean(axis=0)
    d = p - c

    num = float(np.sum(d * o))
    den = float(np.sum(d * d))
    k = num / den if den else 0.0
    t_iso = (o - k * d).mean(axis=0)
    resid_iso = o - (t_iso + k * d)

    A = np.hstack([d, np.ones((len(d), 1))])
    sol, *_ = np.linalg.lstsq(A, o, rcond=None)
    resid_aff = o - A @ sol
    return k, t_iso, resid_iso, sol[:2].T, sol[2], resid_aff


def main():
    ra, rb = sys.argv[1], sys.argv[2]
    pa, pb = os.path.join(OUT, ra + ".tiff"), os.path.join(OUT, rb + ".tiff")
    r16 = tifffile.imread(os.path.join(OUT, "n149a.tiff"))
    expo = 0.90 / max(float(np.percentile(r16.astype(np.float64) / 65535.0, 99.9)), 1e-9)
    del r16
    ga, gb = green(pa, expo), green(pb, expo)
    h, w = ga.shape
    print("%s vs %s   grid %dx%d sites of %d px\n" % (ra, rb, GRID_Y, GRID_X, SITE))

    ys = np.linspace(MARGIN, h - MARGIN - SITE, GRID_Y).astype(int)
    xs = np.linspace(MARGIN, w - MARGIN - SITE, GRID_X).astype(int)
    pts, offs, res = [], [], []
    for y in ys:
        for x in xs:
            o, e, edge = nscene.integer_align(
                ga[y:y + SITE, x:x + SITE],
                gb[y - PAD:y + SITE + PAD, x - PAD:x + SITE + PAD], PAD)
            if edge:
                print("  site (%5d,%5d) SATURATED at +-%d: %s" % (y, x, PAD, o))
                continue
            pts.append((y + SITE / 2, x + SITE / 2))
            offs.append(o)
            res.append(e)
    if len(pts) < 6:
        sys.exit("too few unsaturated sites to fit")

    o = np.array(offs, dtype=np.float64)
    print("  raw offsets: y %+d..%+d (span %d), x %+d..%+d (span %d), over %d sites"
          % (o[:, 0].min(), o[:, 0].max(), o[:, 0].max() - o[:, 0].min(),
             o[:, 1].min(), o[:, 1].max(), o[:, 1].max() - o[:, 1].min(), len(o)))
    print("  match residual %.2f..%.2f codes (a bad match would show here)"
          % (min(res), max(res)))

    k, t, r, M, t_aff, r_aff = fit(pts, offs)
    rms_raw = float(np.sqrt(np.mean((o - o.mean(axis=0)) ** 2)))
    rms_iso = float(np.sqrt(np.mean(r ** 2)))
    rms_aff = float(np.sqrt(np.mean(r_aff ** 2)))
    print("\n  rms of the offset field about its own mean: %.2f px"
          "   <- what a single translation leaves behind" % rms_raw)
    print("  isotropic  s-1 = %+.5f (%.3f%%), t = (%+.1f,%+.1f):  rms %.2f px, "
          "absorbs %2.0f%%" % (k, 100 * k, t[0], t[1], rms_iso,
                               100 * (1 - rms_iso / rms_raw) if rms_raw else 0))
    print("  affine     M = [[%+.5f %+.5f] [%+.5f %+.5f]], t = (%+.1f,%+.1f):  "
          "rms %.2f px, absorbs %2.0f%%"
          % (M[0, 0], M[0, 1], M[1, 0], M[1, 1], t_aff[0], t_aff[1], rms_aff,
             100 * (1 - rms_aff / rms_raw) if rms_raw else 0))
    diag = np.hypot(h, w)
    print("  displacement implied across the %d px diagonal: isotropic %.1f px, "
          "affine %.1f px" % (int(diag), abs(k) * diag,
                              float(np.linalg.norm(M, 2)) * diag))
    if rms_aff < 0.35 * rms_raw:
        verdict = ("an AFFINE geometric disagreement -- the two renders are not on the "
                   "same grid and no single integer shift puts them there")
    elif rms_iso < 0.5 * rms_raw:
        verdict = "a residual SCALE, not a translation"
    else:
        verdict = ("NOT captured by an affine model either: the disagreement has "
                   "structure finer than a global warp")
    print("\n  verdict: %s" % verdict)
    print("  whatever its form, a difference statistic between these two renders "
          "carries a\n  displacement field of rms %.1f px that no global registration "
          "removes." % rms_raw)


if __name__ == "__main__":
    main()
