"""What is the smallest gain the pair-level guard can actually detect?

The guard's tolerance has to be set from its measured noise, not chosen. Two
things must both hold:

  * a real pair, which CANNOT differ in gain, must certify with margin;
  * a gain the guard is meant to catch must trip it.

and the second is tighter than it looks. The real pair's global IQR ratio is
1.00195, so a plant of x1.02 lands at 1.00195/1.02 = 0.9823, i.e. 1.77% -- a
tolerance of 2% would MISS a 2% gain. The tolerance must sit below the effect,
and the guard's own noise must sit below the tolerance.

This measures the noise as a function of block count, which is the free
parameter: more blocks means a better-determined standard error, and using more
of the data is not the same as loosening a threshold.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402

OUT = r"C:\dev\strehl-out\V-H2H2\ladder\out"


def iqr(x):
    return float(np.subtract(*np.percentile(x, [75, 25])))


def scatter(a, b, k):
    h, w = a.shape
    bh, bw = h // k, w // k
    r = []
    for i in range(k):
        for j in range(k):
            ra = iqr(a[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw])
            rb = iqr(b[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw])
            if ra > 0 and rb > 0:
                r.append(ra / rb)
    r = np.array(r)
    return len(r), float(np.std(r, ddof=1)), float(np.std(r, ddof=1)) / np.sqrt(len(r))


def jack(a, b, k):
    """Standard error of the POOLED ratio sum(qa)/sum(qb), by delete-one jackknife.

    Averaging per-block RATIOS is the wrong estimator and the table above shows
    why: a block on flat content has qb near zero, its ratio explodes, and the
    scatter grows with block count instead of shrinking. The pooled ratio weights
    each block by its own contrast automatically, and the jackknife gives the
    error of that estimator rather than of a different one.
    """
    h, w = a.shape
    bh, bw = h // k, w // k
    qa, qb = [], []
    for i in range(k):
        for j in range(k):
            qa.append(iqr(a[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]))
            qb.append(iqr(b[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]))
    qa, qb = np.array(qa), np.array(qb)
    n = len(qa)
    th = np.array([(qa.sum() - qa[i]) / (qb.sum() - qb[i]) for i in range(n)])
    se = np.sqrt((n - 1) / n * float(np.sum((th - th.mean()) ** 2)))
    return n, qa.sum() / qb.sum(), float(se)


def main():
    a16 = tifffile.imread(os.path.join(OUT, "n149a.tiff"))
    expo = 0.90 / max(float(np.percentile(a16.astype(np.float64) / 65535.0, 99.9)), 1e-9)
    ga = bandlib.display(a16[..., 1].astype(np.float64), expo)
    del a16
    gb = bandlib.display(tifffile.imread(os.path.join(OUT, "n149b.tiff"))[..., 1]
                         .astype(np.float64), expo)
    rel = iqr(ga) / iqr(gb) - 1.0
    print("real pair, global IQR ratio %+.3f%%  (a gain is impossible here: "
          "--linear-srgb, no --exposure)\n" % (100 * rel))

    print("  %4s %7s %9s %9s %11s %11s" % ("k", "blocks", "blk px", "blk sd",
                                           "se", "detect@Z=4"))
    for k in (4, 8, 16, 24, 32):
        n, sd, se = scatter(ga, gb, k)
        print("  %4d %7d %9d %8.2f%% %10.3f%% %10.3f%%"
              % (k, n, (ga.shape[0] // k) * (ga.shape[1] // k), 100 * sd,
                 100 * se, 400 * se))

    print("\n  pooled ratio sum(qa)/sum(qb) with a delete-one jackknife:")
    print("  %4s %7s %11s %11s %11s %s" % ("k", "blocks", "pooled", "se",
                                           "detect@Z=4", "and a planted x1.02"))
    for k in (8, 16, 24, 32):
        n, pooled, se = jack(ga, gb, k)
        n2, pooled2, se2 = jack(ga, gb * 1.02, k)
        print("  %4d %7d %10.4f %10.3f%% %10.3f%%   pooled %.4f -> %s"
              % (k, n, pooled, 100 * se, 400 * se, pooled2,
                 "CAUGHT" if abs(pooled2 - 1) > 400 * se / 100 else "MISSED"))

    print("\n  synthetic 512x512 pairs (what commissioning runs on):")
    rng = np.random.default_rng(1)
    y, x = np.mgrid[0:512, 0:512].astype(np.float64)
    S = 40 * np.sin(x / 7) * np.cos(y / 11) + 25 * np.sin((x + y) / 31) \
        + 30 * ((x // 37 + y // 41) % 2) + 128.0
    for name, pa, pb in (("scene + noise", S + rng.normal(0, 3, S.shape),
                          S + rng.normal(0, 3, S.shape)),
                         ("flat + noise", 128 + rng.normal(0, 3, S.shape),
                          128 + rng.normal(0, 3, S.shape))):
        line = "    %-14s" % name
        for k in (8, 16, 24):
            n, sd, se = scatter(pa, pb, k)
            line += "  k=%d detect %.3f%%" % (k, 400 * se)
        print(line + "   rel %+.3f%%" % (100 * (iqr(pa) / iqr(pb) - 1)))


if __name__ == "__main__":
    main()
