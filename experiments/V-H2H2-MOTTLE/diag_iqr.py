"""Does the per-site contrast guard have any power to detect a gain?

The guard exists to refuse two arms that differ in exposure, because a gain g on
one arm puts (1-g)*S into the half-difference and every number downstream is then
wrong. It tests the interquartile range, which a gain multiplies and an additive
offset leaves alone -- that part was measured and is right.

But it is called PER SITE, on a 384 px crop, on the RAW pixels. Two objections:

  1. A gain is a property of the RENDER, not of a site. Measuring a global
     property locally throws away almost all the data.
  2. The raw IQR of a small crop is dominated by the low-frequency scene
     structure inside that crop. The two arms are known to differ by more than a
     translation, so a fixed window sees slightly different content in each --
     which moves the raw IQR for reasons that have nothing to do with gain.

If objection 2 bites, the local test has a false-positive rate set by content and
no power. This measures that directly: the spread of the local IQR ratio across
many sites, against the global ratio, on a pair of arms that CANNOT differ in
gain (--linear-srgb, no --exposure, so there is no tone stage to differ in).

A guard whose noise exceeds the effect it must catch is not a guard.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402
import decomplib  # noqa: E402

OUT = r"C:\dev\strehl-out\V-H2H2\ladder\out"
SITE = 384
MARGIN = 600


def iqr(x):
    return float(np.subtract(*np.percentile(x, [75, 25])))


def main():
    a16 = tifffile.imread(os.path.join(OUT, "n149a.tiff"))
    expo = 0.90 / max(float(np.percentile(a16.astype(np.float64) / 65535.0, 99.9)), 1e-9)
    ga = bandlib.display(a16[..., 1].astype(np.float64), expo)
    del a16
    gb = bandlib.display(tifffile.imread(os.path.join(OUT, "n149b.tiff"))[..., 1]
                         .astype(np.float64), expo)

    print("global IQR ratio a/b : %.5f  (%.2f%%)" % (iqr(ga) / iqr(gb),
                                                     100 * (iqr(ga) / iqr(gb) - 1)))
    print("global mean ratio a/b: %.5f\n" % (float(np.mean(ga)) / float(np.mean(gb))))

    h, w = ga.shape
    rng = np.random.default_rng(7)
    ys = rng.integers(MARGIN, h - MARGIN - SITE, 40)
    xs = rng.integers(MARGIN, w - MARGIN - SITE, 40)
    r = []
    for y, x in zip(ys, xs):
        ca = ga[y:y + SITE, x:x + SITE]
        cb = gb[y:y + SITE, x:x + SITE]
        if iqr(ca) <= 0 or iqr(cb) <= 0:
            continue
        r.append(iqr(ca) / iqr(cb))
    r = np.array(r)
    print("local IQR ratio over %d sites of %d px, arms that CANNOT differ in gain:" % (len(r), SITE))
    print("  median %.5f   sd %.5f   min %.5f   max %.5f"
          % (np.median(r), np.std(r, ddof=1), r.min(), r.max()))
    print("  spread as percent: sd %.2f%%   full range %.2f%%"
          % (100 * np.std(r, ddof=1), 100 * (r.max() - r.min())))
    tol = decomplib.LEVEL_TOL
    trips = int(np.sum(np.abs(r - 1.0) > tol))
    print("  sites that would TRIP the %.0f%% guard: %d of %d (%.0f%%)"
          % (100 * tol, trips, len(r), 100 * trips / len(r)))
    print("\n  A gain of exactly the tolerance, %.0f%%, is what the guard must catch."
          % (100 * tol))
    print("  Content alone moves this statistic by up to %.2f%% between sites."
          % (100 * max(abs(r.max() - 1), abs(r.min() - 1))))
    verdict = ("the local test's noise EXCEEDS the effect it must detect: it has no power"
               if 100 * np.std(r, ddof=1) > 100 * tol / 2 else "the local test retains power")
    print("  -> %s" % verdict)

    print("\nIs a gain visible globally, where content averages out?")
    for g in (1.005, 1.02, 1.04):
        print("  arm b x%.3f  ->  global IQR ratio %.5f  (guard %s)"
              % (g, iqr(ga) / iqr(gb * g),
                 "TRIPS" if abs(iqr(ga) / iqr(gb * g) - 1) > tol else "passes"))


if __name__ == "__main__":
    main()
