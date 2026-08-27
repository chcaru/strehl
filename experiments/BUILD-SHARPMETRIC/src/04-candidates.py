"""Candidate repairs, commissioned against a battery the original never had.

WHAT THE FIRST THREE SCRIPTS ESTABLISHED

  01  The RECONSTRUCT arm is not a ceiling. Master held byte-identical at
      perfect, the arm moves 1.0000 .. 20.2615 purely by changing the SOURCES.
  02  The ratio is EXACTLY linear in master gain (x1.20 -> 1.2000, x1.50 ->
      1.5000, mathematically, not approximately), and PERVERSE to noise:
      adding N(0,1500) to a master that merely SELECTS reads 3.4855, which
      reproduces the published "perfect reconstruction" ceiling to 0.03%.
  03  On real data the master is rendered 1.854x brighter (median level) and
      2.348x higher contrast (std) than the rawpy-rendered sources, over 21
      sites and 8 subjects. That is a photometric scale difference, and by 02
      it multiplies the reported sharpness directly.

THE REPAIR UNDER TEST

The defect is that `mean|grad(y)|` is a MAGNITUDE with physical units. Any
transform that scales the image scales the statistic. The fix is to make the
statistic DIMENSIONLESS by dividing one band of the same image by another:

    S1(y) = fine(y) / coarse(y)

`detail()` already returns both bands -- the original `patch_gain` computes
`coarse` and then throws it away, using only `fine`. Under y -> a*y + b both
bands scale by a and the constant b is annihilated by the gradient, so S1 is
invariant to any global affine photometric transform BY CONSTRUCTION rather
than by calibration. Blur, meanwhile, attenuates the fine band far more than
the coarse one, so S1 remains sensitive to the thing it is supposed to measure.

THE BATTERY

Commissioning that only ever plants degradations cannot tell a BLIND metric
from a PERVERSE one -- the halosens lesson. So the battery has three kinds of
arm and a candidate must satisfy all three:

    DEGRADE   the number must FALL      (blur, noise, ringing)
    IMPROVE   the number must RISE      (a genuinely better reconstruction)
    NEUTRAL   the number must NOT MOVE  (gain, offset, contrast: zero new detail)

and the IMPROVE arm is additionally required to be MONOTONIC across a sweep,
because a metric that rises once but not consistently is not measuring a
quantity, it is reacting.

A candidate is COMMISSIONED only if it passes every arm. Partial credit is
recorded, not awarded.
"""
import numpy as np

CROP = 560
PATCH = 70
PATCH_FLOOR = 50.0


def bands(y):
    """(fine, coarse) exactly as orch_sharp1to1.detail()."""
    f = np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])
    k = y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2]
    c = np.abs(np.diff(k, axis=1)[:-1, :]) + np.abs(np.diff(k, axis=0)[:, :-1])
    return float(np.mean(f)), float(np.mean(c) / 4.0)


def S0(y):
    """The SHIPPED statistic: fine band only. Has units. Scales with gain."""
    return bands(y)[0]


def S1(y):
    """Band ratio: dimensionless, invariant to y -> a*y + b."""
    f, c = bands(y)
    return f / c if c > 0 else float("nan")


def blur(a, k):
    if k <= 1:
        return a.copy()
    c = np.cumsum(np.pad(a, ((0, 0), (k, k)), mode="edge"), axis=1)
    h = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
    c = np.cumsum(np.pad(h, ((k, k), (0, 0)), mode="edge"), axis=0)
    return (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)


def usm(a, amount, k=3):
    return a + amount * (a - blur(a, k))


def ratio_of(stat, ref, srcs, patch=PATCH):
    """Per-patch median of stat(master)/max_src stat(source)."""
    n = ref.shape[0] // patch
    out = []
    for py in range(n):
        for px in range(n):
            sl = (slice(py * patch, (py + 1) * patch),
                  slice(px * patch, (px + 1) * patch))
            mf = bands(ref[sl])[0]
            sfmax = max(bands(c[sl])[0] for c in srcs)
            if mf < PATCH_FLOOR and sfmax < PATCH_FLOOR:
                continue
            m = stat(ref[sl])
            s = max(stat(c[sl]) for c in srcs)
            if np.isfinite(m) and np.isfinite(s) and s > 0:
                out.append(m / s)
    a = np.array(out)
    a = a[np.isfinite(a)]
    return float(np.median(a)) if a.size else float("nan")


def battery(stat, name):
    rng = np.random.default_rng(7)
    lat = rng.normal(8000, 1500, (CROP, CROP))
    lat = np.clip(lat + 4000 * np.sin(np.arange(CROP) / 3.0)[None, :], 0, 65535)
    srcs = [blur(lat, k) for k in (2, 3, 4, 5)]
    sharp = blur(lat, 2)

    base = ratio_of(stat, sharp, srcs)
    perfect = ratio_of(stat, lat, srcs)

    print("=" * 96)
    print("CANDIDATE %s" % name)
    print("=" * 96)
    print("  SELECTION anchor %.4f   RECONSTRUCT(perfect) %.4f" % (base, perfect))
    print()

    arms = []
    arms.append(("DEGRADE", "master blurred to k=8", ratio_of(stat, blur(lat, 8), srcs)))
    arms.append(("DEGRADE", "master blurred to k=3", ratio_of(stat, blur(lat, 3), srcs)))
    for sd in (200, 600, 1500):
        arms.append(("DEGRADE", "master + N(0,%d) noise" % sd,
                     ratio_of(stat, sharp + rng.normal(0, sd, (CROP, CROP)), srcs)))
    for amt in (0.5, 1.5, 3.0):
        arms.append(("DEGRADE", "master USM x%.1f (rings)" % amt,
                     ratio_of(stat, usm(sharp, amt), srcs)))
    arms.append(("NEUTRAL", "master x1.20 gain", ratio_of(stat, 1.20 * sharp, srcs)))
    arms.append(("NEUTRAL", "master x1.50 gain", ratio_of(stat, 1.50 * sharp, srcs)))
    arms.append(("NEUTRAL", "master x1.85 gain (measured med_x, script 03)",
                 ratio_of(stat, 1.854 * sharp, srcs)))
    arms.append(("NEUTRAL", "master +3000 offset", ratio_of(stat, sharp + 3000.0, srcs)))
    arms.append(("NEUTRAL", "master contrast x1.3 about mean",
                 ratio_of(stat, (sharp - 8000) * 1.3 + 8000, srcs)))
    arms.append(("IMPROVE", "half-deblurred (t=0.50)",
                 ratio_of(stat, 0.5 * sharp + 0.5 * lat, srcs)))

    print("  %-9s %-46s %10s  %s" % ("kind", "arm", "value", "verdict"))
    print("  " + "-" * 90)
    nbad = 0
    for kind, label, val in arms:
        if kind == "DEGRADE":
            good = val < base * 0.98
            v = "PASS" if good else "PERVERSE  (rose on a degradation)"
        elif kind == "NEUTRAL":
            good = abs(val - base) / base < 0.02 if base else False
            v = "PASS" if good else "INFLATED  (%.3fx on zero new detail)" % (val / base)
        else:
            good = base * 1.02 < val < perfect * 1.02
            v = "PASS" if good else "FAIL"
        nbad += 0 if good else 1
        print("  %-9s %-46s %10.4f  %s" % (kind, label, val, v))

    print()
    print("  IMPROVEMENT SWEEP -- must be monotonic")
    print("  %-8s %12s %14s" % ("t", "value", "monotonic?"))
    print("  " + "-" * 36)
    prev, mono = None, True
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        r = ratio_of(stat, (1 - t) * sharp + t * lat, srcs)
        tag = "-" if prev is None else ("yes" if r > prev else "NO -- FELL")
        if prev is not None and r <= prev:
            mono = False
        print("  %-8.2f %12.4f %14s" % (t, r, tag))
        prev = r
    if not mono:
        nbad += 1
    print("  monotonic: %s" % ("YES" if mono else "NO"))
    print()
    print("  RESULT: %d arm(s) failed. %s"
          % (nbad, "COMMISSIONED" if nbad == 0 else "NOT COMMISSIONED"))
    print()
    return nbad


def main():
    b0 = battery(S0, "S0 = fine band only  (THE SHIPPED STATISTIC)")
    b1 = battery(S1, "S1 = fine/coarse band ratio  (dimensionless)")
    print("=" * 96)
    print("SUMMARY   S0 failed %d arms.   S1 failed %d arms." % (b0, b1))
    print("=" * 96)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
