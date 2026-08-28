r"""WHOLE-IMAGE OVERSHOOT CENSUS -- the rim axis without its validity domain.

WHY. rimv6 can only speak to edges that PLATEAU within +/-7 px; the rest are
excluded by construction and the excluded share is large on some subjects. If
the orchestrator's veins are not isolated at that scale, the rim axis is silent
about them and a null there is not evidence. This counts over- and undershoot
at EVERY pixel instead, with no isolation test.

STATISTIC. base = gaussian(g, 2.0); lo/hi = 7-px local min/max of base.
excess = max(0, g - hi) + max(0, lo - g), i.e. how far each pixel sticks out
beyond the range its own smoothed neighbourhood spans. Reported as a fraction
of the median level. Per-tile, bootstrapped over tiles.

STATED FOOLING DIRECTION, and it is the important one: THIS FALLS UNDER A BLUR
as well as under a halo fix. It is admissible as evidence of less halo ONLY
beside a measured edge width that did not increase. That pairing is why
edgewidth.py exists and both are reported together.
"""
import argparse
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402
import rimab                                                       # noqa: E402

TILE = 256


def excess(g, blur=2.0, size=7):
    base = ndimage.gaussian_filter(g, blur)
    hi = ndimage.maximum_filter(base, size)
    lo = ndimage.minimum_filter(base, size)
    return np.clip(g - hi, 0, None) + np.clip(lo - g, 0, None)


def tiles(x, cm):
    y0, x0, ty, tx = bm.tile_grid(x.shape)
    sub = x[y0:y0 + ty * TILE, x0:x0 + tx * TILE]
    c = cm[y0:y0 + ty * TILE, x0:x0 + tx * TILE]
    m = sub.reshape(ty, TILE, tx, TILE).mean(axis=(1, 3))
    k = c.reshape(ty, TILE, tx, TILE).max(axis=(1, 3))
    return m[k == 0]


def score(gA, gB, cm):
    lvl = 0.5 * (float(np.median(gA)) + float(np.median(gB)))
    a = tiles(excess(gA), cm) / lvl
    b = tiles(excess(gB), cm) / lvl
    r = b / np.maximum(a, 1e-12)
    rng = np.random.default_rng(91)
    idx = rng.integers(0, len(r), size=(4000, len(r)))
    m = np.median(r[idx], axis=1)
    return (float(np.median(a)), float(np.median(b)),
            100 * (float(np.median(r)) - 1),
            100 * (float(np.percentile(m, 2.5)) - 1),
            100 * (float(np.percentile(m, 97.5)) - 1), len(a))


def show(tag, s):
    print("  %-34s A %.6f  B %.6f   B-A %+7.3f%% [%+7.3f%%, %+7.3f%%]  n=%d"
          % (tag, s[0], s[1], s[2], s[3], s[4], s[5]))


def commission(path):
    print("COMMISSIONING the overshoot census on real pixels: %s" % path)
    g, cm, clipf = bm.load(path)
    print("  whole-image clip fraction %.4f%%" % (100 * clipf))
    rows = []
    for name, arm, sgn in (
            ("NULL     identical", g.copy(), 0),
            ("DEFECT   USM 0.5 r=2.0 -> must RISE", rimab.usm(g, 0.5, 2.0), +1),
            ("DEFECT   USM 0.2 r=2.0 -> must RISE", rimab.usm(g, 0.2, 2.0), +1),
            ("IMPROVE  overshoot clamp -> must FALL", rimab.clamp(g), -1),
            ("CONFOUND blur 0.8 -> ALSO falls, by design",
             ndimage.gaussian_filter(g, 0.8), -1)):
        s = score(g, arm, cm)
        show(name, s)
        ok = ((sgn > 0 and s[3] > 0) or (sgn < 0 and s[4] < 0) or
              (sgn == 0 and s[2] == 0.0))
        rows.append((name, ok))
        print("      ---> %s" % ("PASS" if ok else "FAIL"))
    bad = [r for r in rows if not r[1]]
    print("\n  COMMISSIONED %d/%d arms" % (len(rows) - len(bad), len(rows)))
    for n, _ in bad:
        print("    NOT COMMISSIONED: %s" % n)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", metavar="TIFF")
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    if args.commission:
        return commission(args.commission)
    gA, cmA, clipA = bm.load(args.a)
    gB, cmB, clipB = bm.load(args.b)
    print("%s   A clip %.4f%%  B clip %.4f%%" % (args.tag, 100 * clipA, 100 * clipB))
    show("overshoot", score(gA, gB, cmA | cmB))
    return 0


if __name__ == "__main__":
    sys.exit(main())
