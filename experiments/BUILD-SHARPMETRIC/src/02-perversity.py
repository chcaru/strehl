"""What else does this statistic respond to? Perversity, gain, noise -- and an
IMPROVEMENT arm, which is the arm that catches a metric that is merely blind.

Script 01 established that the RECONSTRUCT arm is not a ceiling: with the
master held byte-identical at perfect, the arm moves 1.0000 .. 20.2615 purely
because the sources changed. That makes a real subject reading 4.767x LEGAL.
It does not make it CORRECT. This script asks the second question: does the
ratio respond to anything other than sharpness?

The statistic is

    ratio = mean|grad(master_patch)| / max_over_sources mean|grad(source_patch)|

`mean|grad|` is a MAGNITUDE. It is bounded below by zero and unbounded above.
That is the same shape as the halosens defect recorded in
experiments/BUILD-TRIAGE/halosens.py -- `tri.edge_slope` is a magnitude and
`tri.blur_equiv` returns 0.0 for any ratio >= 1.0, so the sign of the error is
bounded below by zero and no input can make it charge for a halo. The lesson
recorded there is the one this script is built around:

    "Every defect I ever planted made the image worse and I checked the number
     went down. A defect that makes the number go UP passes every such test
     trivially."

So every arm below is labelled with what a CORRECT instrument must do, and the
arms are deliberately mixed: degradations that must lower it, an improvement
that must raise it, and neutral transforms that must leave it ALONE. An arm
that must leave the number alone is the one the original commission never had,
and it is where a magnitude statistic fails.

VERDICTS
    PASS      the metric moved the way a sharpness metric must
    PERVERSE  the metric moved the WRONG WAY -- it rewarded a degradation
    INFLATED  the metric moved on a transform that adds no detail at all
    BLIND     the metric did not move when it should have
"""
import numpy as np

CROP = 560
PATCH = 70
PATCH_FLOOR = 50.0


def detail(y):
    f = np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])
    k = y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2]
    c = np.abs(np.diff(k, axis=1)[:-1, :]) + np.abs(np.diff(k, axis=0)[:, :-1])
    return float(np.mean(f)), float(np.mean(c) / 4.0)


def blur(a, k):
    if k <= 1:
        return a.copy()
    c = np.cumsum(np.pad(a, ((0, 0), (k, k)), mode="edge"), axis=1)
    h = (c[:, 2 * k:] - c[:, :-2 * k]) / (2 * k)
    c = np.cumsum(np.pad(h, ((k, k), (0, 0)), mode="edge"), axis=0)
    return (c[2 * k:, :] - c[:-2 * k, :]) / (2 * k)


def patch_gain(ref, reg, patch=PATCH):
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


def med(ref, srcs):
    g = np.array(patch_gain(ref, srcs)[0])
    g = g[np.isfinite(g)]
    return float(np.median(g)) if g.size else float("nan")


def usm(a, amount, k=3):
    return a + amount * (a - blur(a, k))


def main():
    rng = np.random.default_rng(7)
    lat = rng.normal(8000, 1500, (CROP, CROP))
    lat = np.clip(lat + 4000 * np.sin(np.arange(CROP) / 3.0)[None, :], 0, 65535)
    srcs = [("k%d" % k, blur(lat, k)) for k in (2, 3, 4, 5)]

    base = med(blur(lat, 2), srcs)          # SELECTION anchor == 1.0
    perfect = med(lat, srcs)                # the published "ceiling"
    print("anchors:  SELECTION %.4f   RECONSTRUCT(published ceiling) %.4f\n"
          % (base, perfect))

    rows = []

    # ---- degradations: the number MUST fall ------------------------------
    rows.append(("DEGRADE  blur master to k=8 (published DEFECT arm)",
                 med(blur(lat, 8), srcs), "must FALL", "fall"))
    rows.append(("DEGRADE  blur master slightly (k=3)",
                 med(blur(lat, 3), srcs), "must FALL", "fall"))

    # ---- the improvement arm. The arm the original commission LACKED. ----
    # A partial deblur: strictly better than the sharpest source, strictly
    # worse than the latent. A correct metric must place it BETWEEN them and
    # must rise monotonically as the reconstruction improves.
    print("IMPROVEMENT ARM -- a reconstruction that gets genuinely better.")
    print("Each row mixes the sharpest source toward the true latent. t=0 is")
    print("the source itself (must read 1.0), t=1 is the latent (must read the")
    print("RECONSTRUCT value). A correct metric must be MONOTONIC in t.")
    print("  %-8s %12s %12s" % ("t", "ratio", "monotonic?"))
    print("  " + "-" * 36)
    prev, mono = None, True
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        mix = (1 - t) * blur(lat, 2) + t * lat
        r = med(mix, srcs)
        ok = "-" if prev is None else ("yes" if r > prev else "NO -- FELL")
        if prev is not None and r <= prev:
            mono = False
        print("  %-8.2f %12.4f %12s" % (t, r, ok))
        prev = r
    print("  improvement arm monotonic: %s\n" % ("YES  PASS" if mono else "NO  FAIL"))
    rows.append(("IMPROVE  half-deblurred master (t=0.5)",
                 med(0.5 * blur(lat, 2) + 0.5 * lat, srcs), "must RISE", "rise"))

    # ---- neutral transforms: the number MUST NOT MOVE --------------------
    # These add no detail whatsoever. Any movement is inflation.
    rows.append(("NEUTRAL  master x1.20 gain (pure exposure)",
                 med(1.20 * blur(lat, 2), srcs), "must HOLD", "hold"))
    rows.append(("NEUTRAL  master x1.50 gain (pure exposure)",
                 med(1.50 * blur(lat, 2), srcs), "must HOLD", "hold"))
    rows.append(("NEUTRAL  master contrast about its mean (x1.3)",
                 med((blur(lat, 2) - 8000) * 1.3 + 8000, srcs), "must HOLD", "hold"))

    # ---- noise: adding noise is a DEGRADATION, not detail ----------------
    for sd in (200, 600, 1500):
        n = blur(lat, 2) + rng.normal(0, sd, (CROP, CROP))
        rows.append(("DEGRADE  master + N(0,%4d) sensor-like noise" % sd,
                     med(n, srcs), "must FALL", "fall"))

    # ---- sharpening: manufactures gradient, adds no information ----------
    for amt in (0.5, 1.5, 3.0):
        rows.append(("DEGRADE  master unsharp-masked x%.1f (rings)" % amt,
                     med(usm(blur(lat, 2), amt), srcs), "must FALL", "fall"))

    print("%-52s %10s %11s  %s" % ("arm", "ratio", "required", "verdict"))
    print("-" * 92)
    nbad = 0
    for label, val, req, kind in rows:
        if kind == "fall":
            good = val < base * 0.98
            verdict = "PASS" if good else "PERVERSE (rose on a degradation)"
        elif kind == "rise":
            good = base * 1.02 < val < perfect
            verdict = "PASS" if good else "FAIL"
        else:
            good = abs(val - base) / base < 0.02
            verdict = "PASS" if good else "INFLATED (moved on zero new detail)"
        if not good:
            nbad += 1
        print("%-52s %10.4f %11s  %s" % (label, val, req, verdict))

    print()
    print("=" * 92)
    print("%d of %d arms failed." % (nbad, len(rows)))
    print()
    print("Read the NEUTRAL rows first. mean|grad(a*y)| == a*mean|grad(y)|")
    print("exactly, so the ratio is LINEAR in any gain applied to the master.")
    print("A master rendered 20%% brighter than its sources scores 20%% 'sharper'")
    print("while containing not one extra photon of detail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
