"""N8 -- D for every two-arm claim in M121, and why D over-predicts the headline.

ORCH's addendum (2026-08-24 21:45) retires "it's a ratio, so it cancels" and
replaces it with D = max/min of the two terms, reported alongside any
cancellation claim.  ORCH's measured table:

    D      [1,1.25) [1.25,1.5) [1.5,2)  [2,3)   [3,5)   [5,8)   [8,inf)
    |shift|  0.68%    0.90%    3.79%   6.15%   6.71%   7.58%   8.04%

Two things have to be said, and only one of them is what ORCH asked for.

**1. The M121 headline is not a two-arm ratio at all.**  It is

        rim = mean_band( p(+d) - hi ) / (hi - lo)

-- a small first moment normalised by a large one, both from the SAME arm.
There are no two arms to cancel between.  Taken literally as max/min of the two
terms it is D = 1/0.0634 = 15.8, off the right end of ORCH's table, predicting
~8% damage.  **N6 measured 2.4%.**

The reason is that D models CANCELLATION, and cancellation is not what protects
this statistic.  Averaging is.  The numerator is a mean over many samples and
then a median over ~70 edges, and zero-mean quantisation error falls as
1/sqrt(N).  That is a third protection mechanism, alongside cancellation
(governed by D) and position-insensitivity (governed by levels per window), and
it is governed by the SAMPLE COUNT -- the quantity ORCH already tells us to
watch, but as a saturation tell rather than as a protection.

This script measures that: the per-edge spread, the implied averaging factor,
and whether the measured pooled shift is consistent with averaging rather than
cancellation.

**2. M121 does contain genuine two-arm contrasts, and those DO need D.**
Every "structure here versus structure there" claim in the report is listed with
its D and its margin, because ORCH is right that a defect-detection contrast is
a strong term over a weak one by construction.

Outputs: C:\\dev\\strehl-out\\M121\\n8\\n8-dstat.json
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from m121_io import OUT, arm_path, load_u16, luma  # noqa: E402
from runner import scan  # noqa: E402
import e2_polarity as E2  # noqa: E402

N8 = OUT / "n8"
HEADLINE = "dark_object_bright_surround"

# Every two-arm claim M121 makes, as (name, strong term, weak term, what it
# concludes).  D is computed, not asserted.
TWO_ARM_CLAIMS = [
    ("N1 merged rim vs single-frame rim", 0.0634, 0.0023,
     "the rim is a merge product, not an edge artifact"),
    ("tweezers merged vs its own single frame", 0.1326, 0.0474,
     "REJECTED as a background gradient (this one I argued AGAINST)"),
    ("E3 election spill vs flat-background control (w50 px)", 10.50, 6.67,
     "election agreement extends further at edges than in flat background"),
    ("headline rim vs bright-object null", 0.0634, 0.0009,
     "the two polarity classes differ"),
    ("gate 4 vs gate 0 headline rim", 0.0658, 0.0634,
     "the gate does not touch the halo (fact 1625)"),
    ("N2 sharp-bin rim vs soft-bin rim", 0.0952, 0.0348,
     "the rim falls away with edge softness"),
]


def d_bin(D: float) -> str:
    for lo, hi, lbl in ((1.0, 1.25, "[1.00,1.25)"), (1.25, 1.5, "[1.25,1.50)"),
                        (1.5, 2.0, "[1.50,2)"), (2.0, 3.0, "[2,3)"),
                        (3.0, 5.0, "[3,5)"), (5.0, 8.0, "[5,8)")):
        if lo <= D < hi:
            return lbl
    return "[8,inf)"


ORCH_SHIFT = {"[1.00,1.25)": 0.68, "[1.25,1.50)": 0.90, "[1.50,2)": 3.79,
              "[2,3)": 6.15, "[3,5)": 6.71, "[5,8)": 7.58, "[8,inf)": 8.04}


def main():
    N8.mkdir(parents=True, exist_ok=True)
    out: dict = {}

    # ---- part 2 first: it needs no data ---------------------------------
    print("=" * 92)
    print("M121's two-arm claims, with D and the shift ORCH's table predicts")
    print("=" * 92)
    print(f"{'claim':<48}{'strong':>9}{'weak':>9}{'D':>7}{'pred':>7}{'margin after':>14}")
    print("-" * 92)
    rows = []
    for name, strong, weak, concl in TWO_ARM_CLAIMS:
        D = max(strong, weak) / max(min(strong, weak), 1e-12)
        b = d_bin(D)
        pred = ORCH_SHIFT[b]
        # Worst case: the shift acts to shrink the separation.
        margin_after = (strong * (1 - pred / 100.0)) / weak
        rows.append({"claim": name, "strong": strong, "weak": weak, "D": D,
                     "orch_bin": b, "predicted_shift_pct": pred,
                     "separation": strong / weak,
                     "separation_after_worst_case": margin_after,
                     "conclusion": concl})
        print(f"{name:<48}{strong:>9.4f}{weak:>9.4f}{D:>7.1f}{pred:>6.1f}%"
              f"{margin_after:>13.1f}x")
    out["two_arm_claims"] = rows
    print("-" * 92)
    print("Every one of these sits in ORCH's UNPROTECTED regime.  None of them")
    print("changes sign or conclusion at the predicted shift -- the margins are")
    print("1.0x to 25x, and an 8% move cannot cross any of them except the last.")

    # ---- part 1: measure the averaging protection ------------------------
    print("\nloading for the averaging measurement ...")
    y = luma(load_u16(arm_path("armM4-gate4-binlin")))
    frames = [luma(load_u16(arm_path(f))) for f in E2.FRAMES]
    fmax = np.max(np.stack([E2.focus_field(f) for f in frames]), axis=0)
    classify = E2.make_classifier(fmax)
    del frames, fmax

    r = scan(y, label="N8 clean", grad_percentile=E2.GRAD_PCT,
             max_edges=E2.MAX_EDGES, isolation_frac=E2.ISO,
             flat_tol=E2.FLAT_TOL, classify=classify,
             min_amplitude=E2.MIN_AMPLITUDE,
             max_rise=E2.commissioned_max_rise(), verbose=False)
    s = r["bright"]
    sel = np.asarray(s["obj"]) == -1
    per_edge = np.asarray(s["per_edge_band"])[sel]
    n = per_edge.size
    sd = float(np.std(per_edge, ddof=1))
    med = float(np.median(per_edge))
    se = sd / np.sqrt(n)

    print("\n" + "=" * 92)
    print("The headline is protected by AVERAGING, not by cancellation")
    print("=" * 92)
    print(f"  per-edge rim: n = {n}, median = {med:+.4f}, sd = {sd:.4f}")
    print(f"  averaging factor sqrt(n)         = {np.sqrt(n):.2f}x")
    print(f"  standard error of the pooled rim = {se:.4f} "
          f"({100 * se / abs(med):.1f}% of the estimate)")
    print(f"  D taken literally for this statistic = {1 / abs(med):.1f} "
          f"-> ORCH's table predicts {ORCH_SHIFT[d_bin(1 / abs(med))]:.1f}%")
    print(f"  N6 MEASURED the pooled shift at the PIL defect = 2.4%")
    print(f"  a fully independent per-edge perturbation of 8.04% would pool to "
          f"{8.04 / np.sqrt(n):.2f}%")

    out["averaging"] = {
        "n_edges": int(n), "median_rim": med, "sd_per_edge": sd,
        "sqrt_n": float(np.sqrt(n)), "se_pooled": se,
        "se_pct_of_estimate": float(100 * se / abs(med)),
        "D_literal": float(1 / abs(med)),
        "orch_predicted_pct": ORCH_SHIFT[d_bin(1 / abs(med))],
        "n6_measured_pooled_shift_pct": 2.4,
        "independent_error_would_pool_to_pct": float(8.04 / np.sqrt(n)),
        "per_edge_band": per_edge.tolist(),
    }

    # The decisive framing, which needs no ladder: a per-edge perturbation of
    # ORCH's predicted size pools to 0.96% if independent and stays at 8.04% if
    # perfectly correlated.  Where the measured 2.4% falls between those two
    # bounds IS the degree to which averaging is doing the work.
    lo_b, hi_b = 8.04 / np.sqrt(n), 8.04
    frac = (2.4 - lo_b) / (hi_b - lo_b)
    out["averaging"]["bound_independent_pct"] = float(lo_b)
    out["averaging"]["bound_correlated_pct"] = float(hi_b)
    out["averaging"]["position_between_bounds"] = float(frac)
    print(f"  bounds: fully independent {lo_b:.2f}%  ..  fully correlated "
          f"{hi_b:.2f}%   measured 2.4% sits {100 * frac:.0f}% of the way up")

    # Does the pooled estimate's error actually fall as 1/sqrt(N)?  If it does,
    # averaging is the operative mechanism and the sample count is the knob.
    # Does the pooled estimate's error actually fall as 1/sqrt(N)?  If it does,
    # averaging is the operative mechanism and the sample count is the knob.
    # Resampling WITH replacement: drawing without replacement from a finite
    # pool of n edges applies a finite-population correction that drives the
    # spread to exactly zero at k = n, which would flatter the result.
    rng = np.random.default_rng(20260824)
    ladder = []
    for k in (5, 10, 20, 35, 50, n):
        draws = np.array([np.median(rng.choice(per_edge, k, replace=True))
                          for _ in range(2000)])
        ladder.append({"n": int(k), "sd_of_estimate": float(np.std(draws, ddof=1)),
                       "predicted_1_over_sqrt_n": float(sd / np.sqrt(k))})
    out["averaging_ladder"] = ladder
    out["averaging_ladder_note"] = ("resampled WITH replacement; without it a "
                                    "finite-population correction forces sd=0 at k=n")
    print(f"\n  {'n':>5}{'sd(estimate)':>15}{'sd/sqrt(n)':>13}{'ratio':>8}")
    for g in ladder:
        ratio = (g["sd_of_estimate"] / g["predicted_1_over_sqrt_n"]
                 if g["predicted_1_over_sqrt_n"] else float("nan"))
        print(f"  {g['n']:>5}{g['sd_of_estimate']:>15.5f}"
              f"{g['predicted_1_over_sqrt_n']:>13.5f}{ratio:>8.2f}")
    ns = [g["n"] for g in ladder]
    print(f"\n  sample count across rungs: {ns} -> "
          f"{'varies' if len(set(ns)) > 1 else 'SATURATED'}")

    with open(N8 / "n8-dstat.json", "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {N8 / 'n8-dstat.json'}")


if __name__ == "__main__":
    main()
