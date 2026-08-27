"""Is the RECONSTRUCT arm a CEILING, or just one point on a slope?

ORCH-veiling.md sec 105.3 records the open problem: the commission's
"perfect reconstruction" arm reads 3.4867 and five of nine real subjects read
ABOVE it. A real photograph cannot out-reconstruct the latent image the
commission defined as perfection, so either the subjects are inflated or the
arm is not a ceiling. The orchestrator's instruction was to CHECK THE ARM
FIRST, because a ceiling arm that is not a ceiling is the cheapest explanation
and sec 105 never tested it.

THE HYPOTHESIS THIS SCRIPT TESTS
--------------------------------
`commission()` builds a latent `lat`, blurs it to make four sources at
k = 2,3,4,5, and calls `lat` itself the RECONSTRUCT arm. The reported ratio is

    detail(lat) / max_k detail(blur(lat, k))
  = detail(lat) / detail(blur(lat, 2))          <- the SHARPEST source wins

so the number is not "how good a perfect reconstruction is". It is "how much a
k=2 box blur attenuates the mean absolute gradient of THIS latent". k=2 is an
arbitrary choice made when the arm was written.

If that is right, then re-running the identical arm with a different sharpest
source must MOVE the so-called ceiling. A ceiling that moves when you change
something other than the master is not a ceiling.

WHAT WOULD FALSIFY IT
---------------------
If the RECONSTRUCT arm reads ~3.4867 regardless of the source blur, the number
is a property of perfect reconstruction after all, the hypothesis is dead, and
the inflation must be in the subjects. That is a real possible outcome of this
script and it is why the sweep is run rather than argued.

This script imports NOTHING from the orchestrator's file. The statistic is
re-implemented here, byte-for-byte from the original, so that a divergence
between my copy and theirs shows up as a disagreement in arm 1 rather than
hiding. Arm 1 (k=2) must reproduce 3.4867 or this script is not measuring the
thing sec 105 measured.
"""
import numpy as np

CROP = 560
PATCH = 70
PATCH_FLOOR = 50.0


def detail(y):
    """Mean absolute gradient at two scales. Copied verbatim from
    orch_sharp1to1.py so that any difference is visible as a number, not
    hidden in an import."""
    f = np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])
    k = y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2]
    c = np.abs(np.diff(k, axis=1)[:-1, :]) + np.abs(np.diff(k, axis=0)[:, :-1])
    return float(np.mean(f)), float(np.mean(c) / 4.0)


def blur(a, k):
    """Verbatim from orch_sharp1to1.commission()."""
    if k <= 1:
        return a.copy()
    c = np.cumsum(np.pad(a, ((0, 0), (k, k)), mode="edge"), axis=1)
    h = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
    c = np.cumsum(np.pad(h, ((k, k), (0, 0)), mode="edge"), axis=0)
    return (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)


def patch_gain(ref, reg, patch=PATCH):
    """Verbatim from orch_sharp1to1.py."""
    n = ref.shape[0] // patch
    gains, skipped = [], 0
    for py in range(n):
        for px in range(n):
            sl = (slice(py * patch, (py + 1) * patch),
                  slice(px * patch, (px + 1) * patch))
            mf, _ = detail(ref[sl])
            sf = max((detail(c[sl])[0] for _, c in reg), default=0.0)
            if mf < PATCH_FLOOR and sf < PATCH_FLOOR:
                skipped += 1
                continue
            gains.append(mf / sf if sf > 0 else float("inf"))
    return gains, skipped


def latent(seed=7):
    """Verbatim construction from orch_sharp1to1.commission()."""
    rng = np.random.default_rng(seed)
    lat = rng.normal(8000, 1500, (CROP, CROP))
    lat = np.clip(lat + 4000 * np.sin(np.arange(CROP) / 3.0)[None, :], 0, 65535)
    return lat


def med(gains):
    g = np.array(gains)
    g = g[np.isfinite(g)]
    return float(np.median(g)) if g.size else float("nan")


def main():
    lat = latent()

    print("=" * 78)
    print("ARM 1 -- reproduce the published commission exactly (sources k=2,3,4,5)")
    print("=" * 78)
    srcs = [("k%d" % k, blur(lat, k)) for k in (2, 3, 4, 5)]
    sel = med(patch_gain(blur(lat, 2), srcs)[0])
    dfc = med(patch_gain(blur(lat, 8), srcs)[0])
    rec = med(patch_gain(lat, srcs)[0])
    print("  SELECTION   (master == sharpest source)  %10.4f   published 1.0000" % sel)
    print("  DEFECT      (master blurred past all)    %10.4f   published 0.1717" % dfc)
    print("  RECONSTRUCT (master == unblurred latent) %10.4f   published 3.4867" % rec)
    agree = abs(rec - 3.4867) < 0.01 and abs(sel - 1.0) < 0.01 and abs(dfc - 0.1717) < 0.01
    print("\n  reproduces the published arms: %s" % ("YES" % () if agree else "NO"))
    if not agree:
        print("  -> my copy of the statistic DIFFERS from the orchestrator's.")
        print("     Everything below is therefore about MY statistic, and the")
        print("     disagreement is the first thing to resolve.")
        return 1

    print()
    print("=" * 78)
    print("ARM 2 -- THE TEST: hold the master at PERFECT, move only the SOURCES")
    print("=" * 78)
    print("The master is `lat` in every row: a literally perfect reconstruction,")
    print("identical pixels, unchanged. ONLY the source blur changes. If 3.4867")
    print("is a ceiling on perfection, every row must read 3.4867.")
    print()
    print("  %-26s %12s %12s" % ("sources (box half-width)", "RECONSTRUCT", "vs 3.4867"))
    print("  " + "-" * 52)
    rows = []
    for ks in [(1, 2, 3, 4), (2, 3, 4, 5), (3, 4, 5, 6), (4, 5, 6, 7),
               (5, 6, 7, 8), (6, 7, 8, 9), (8, 9, 10, 11), (10, 11, 12, 13)]:
        s = [("k%d" % k, blur(lat, k)) for k in ks]
        r = med(patch_gain(lat, s)[0])
        rows.append((ks, r))
        print("  %-26s %12.4f %11.2fx" % (str(ks), r, r / 3.4867))
    lo, hi = min(r for _, r in rows), max(r for _, r in rows)
    print()
    print("  RECONSTRUCT ranges %.4f .. %.4f over an UNCHANGED, perfect master." % (lo, hi))
    print("  spread %.2fx" % (hi / lo))
    print()
    if hi / lo > 1.5:
        print("  VERDICT: 3.4867 is NOT A CEILING. The master is byte-identical in")
        print("  every row above -- it is the same perfect reconstruction -- and the")
        print("  number moves by %.2fx purely because the SOURCES changed. The arm" % (hi / lo))
        print("  measures how blurred the best source is, not how good the master is.")
        print("  A real subject scoring above 3.4867 is therefore NOT out-performing")
        print("  perfection; it has source frames blurred by more than a k=2 box.")
    else:
        print("  VERDICT: the arm held steady. Hypothesis REFUTED -- 3.4867 behaves")
        print("  like a real ceiling and the inflation must be sought in the subjects.")

    print()
    print("=" * 78)
    print("ARM 3 -- what does the published k=2 arm correspond to physically?")
    print("=" * 78)
    print("If the ceiling is set by the sharpest source's blur, then the published")
    print("3.4867 is the answer for ONE specific source blur. Invert it: for a")
    print("perfect master, what source blur does each observed subject ratio imply?")
    print()
    print("  %-12s %12s" % ("RECONSTRUCT", "implied sharpest-source box half-width"))
    print("  " + "-" * 52)
    for k in range(1, 14):
        s = [("k", blur(lat, k))]
        r = med(patch_gain(lat, s)[0])
        print("  k=%-10d %12.4f" % (k, r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
