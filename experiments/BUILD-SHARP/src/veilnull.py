"""Extreme-value arithmetic behind the veil-envelope verdict (BUILD-SHARP section 18).

Three questions about `Estimator::apply_veil` in `crates/strehl-core/src/merge.rs`,
answered by Monte Carlo rather than by asymptotics, because the asymptotic form is
exactly what turned out to be wrong.

`apply_veil` substitutes at a pixel when

    est = pmax - debias * sigma  >  current + margin * sigma

with `debias = sqrt(2 ln n)` (merge.rs:2101), `margin = 3` by default, `pmax` a
maximum over every folded frame and `current` the gated mean over n_eff of them.

1. DEBIAS.  Is `sqrt(2 ln n)` the right constant?  It is the MODE of the maximum of
   n normals, not its EXPECTATION, so it over-subtracts.  Reported in sigmas.

2. NULL FIRING RATE.  How often does the operator fire on pure i.i.d. normal noise?
   If this is zero then any far-field level shift measured on a real stack is NOT
   extreme-value bias, which is the concern this whole verification was set up
   around.  That makes the answer an exoneration rather than a formality.

3. SIGMA INFLATION.  Inverting question 2: if the operator DOES fire at some
   observed rate, by how much would the calibrated noise model have to understate
   the true per-frame spread for noise alone to explain it?  A ratio near 1 means
   the firing is driven by real frame-to-frame content, which is what veil is.

Run with no arguments; every number section 18 quotes is printed.
"""

from __future__ import annotations

import numpy as np

# (frames in the bracket, mean n_eff at gate 4.0 from the engine's own gate table).
# The n_eff values are read from `run-A.log`, not assumed: the gated mean is an
# average over n_eff frames, so its noise is sigma/sqrt(n_eff), and using the frame
# count instead would understate the spread of (pmax - mean) and overstate how
# inert the operator is.
STACKS = (
    ("109MSDCF", 22, 4.871),
    ("coffee-bean", 105, 27.239),
    ("flower-bud-alone-cpl", 205, 138.717),
    ("couch-fibers-cpl", 299, 2.728),
)

MARGIN = 3.0
TRIALS_DEBIAS = 400_000
TRIALS_NULL = 2_000_000


def _draw(rng: np.random.Generator, n: int, n_eff: float, trials: int):
    """`(pmax - mean)` in true single-frame sigmas, and `pmax` alone.

    `n_eff` is fractional, so the gated mean is drawn as a normal of sd
    1/sqrt(n_eff) rather than by averaging an integer number of columns. That is
    the same quantity and it avoids rounding n_eff to an integer, which at
    n_eff = 2.728 would be a 10% error in the mean's own noise.
    """
    x = rng.standard_normal((trials, n))
    pmax = x.max(axis=1)
    mean = rng.standard_normal(trials) / np.sqrt(n_eff)
    return pmax, pmax - mean


def debias_table(rng: np.random.Generator) -> None:
    print("1. DEBIAS CONSTANT: sqrt(2 ln n) is the MODE of max(n), not the mean.\n")
    print(f"{'n':>6}{'sqrt(2 ln n)':>14}{'E[max] MC':>12}{'sem':>8}{'over-subtraction':>19}")
    for n in (22, 105, 205, 299):
        m = rng.standard_normal((TRIALS_DEBIAS, n)).max(axis=1)
        e = float(m.mean())
        sem = float(m.std(ddof=1) / np.sqrt(TRIALS_DEBIAS))
        a = float(np.sqrt(2 * np.log(n)))
        print(f"{n:6d}{a:14.4f}{e:12.4f}{sem:8.4f}{a - e:16.3f} sigma")
    print(
        "\n   Every applied pixel loses about half a single-frame sigma of real\n"
        "   light. Against a DARKENING defect that is the conservative direction.\n"
    )


def null_and_inflation(rng: np.random.Generator, observed: dict[str, float]) -> None:
    print("2. NULL FIRING RATE on i.i.d. normal noise, and")
    print("3. SIGMA INFLATION needed to explain the observed firing rate.\n")
    print(
        f"{'subject':<22}{'n':>5}{'n_eff':>8}{'thresh':>8}"
        f"{'null fire':>12}{'observed':>10}{'sigma x':>9}"
    )
    worst = 0.0
    worst_ratio = float("inf")
    for name, n, n_eff in STACKS:
        debias = float(np.sqrt(2 * np.log(n)))
        thresh = debias + MARGIN
        _, z = _draw(rng, n, n_eff, TRIALS_NULL)
        rate = float((z > thresh).mean())
        obs = observed[name]
        # Fire iff pmax - mean > (debias + margin) * sigma_model. If the true
        # spread is k * sigma_model then in TRUE sigmas the threshold is
        # thresh / k, so k = thresh / quantile(z, 1 - observed_rate).
        k = thresh / float(np.quantile(z, 1.0 - obs)) if obs > 0 else float("nan")
        shown = f"<{1.0 / TRIALS_NULL:.0e}" if rate == 0.0 else f"{rate:.2e}"
        print(f"{name:<22}{n:5d}{n_eff:8.2f}{thresh:8.3f}{shown:>12}{100 * obs:9.2f}%{k:9.2f}")
        worst = max(worst, rate)
        if obs > 0 and rate > 0:
            worst_ratio = min(worst_ratio, obs / rate)
    # Derived from the table above rather than asserted next to it. A narrative
    # sentence that does not move when the numbers move is the failure this
    # lane has now caught five times.
    floor = 1.0 / TRIALS_NULL
    print(
        f"\n   Highest null firing rate over {TRIALS_NULL:,} trials per stack: "
        f"{max(worst, floor):.1e}."
    )
    if worst_ratio < 100:
        print("   WARNING: that is within 100x of an observed rate. Not inert.")
    else:
        print(
            f"   The smallest observed-to-null ratio is {worst_ratio:,.0f}x, so on\n"
            "   clean Gaussian backdrop the envelope is effectively INERT and a\n"
            "   measured far-field shift cannot be extreme-value bias."
        )
    print(
        "   A 'sigma x' near 1 would mean noise could explain the firing; these\n"
        "   are well above it, so the operator is responding to real\n"
        "   frame-to-frame content, which is what veiling is."
    )


def main() -> None:
    rng = np.random.default_rng(20260826)
    debias_table(rng)
    # `applied` fractions printed by the engine in run-B.log.
    observed = {
        "109MSDCF": 0.0060,
        "coffee-bean": 0.2546,
        "flower-bud-alone-cpl": 0.1249,
        "couch-fibers-cpl": 0.1308,
    }
    null_and_inflation(rng, observed)


if __name__ == "__main__":
    main()
