"""M72 step 7 -- C6 re-examined against a comparator that has been refuted.

C6 was pre-registered with an EXTERNAL input:

    "PRE-DECLARED COMPARISON: M69 is finding FOCUS_NOISE_SD 19-21 % off on
     real texture.  If the worst-case sigma error over the operating range
     is below 1/4 of that, the item is reported as IMMATERIAL IN PRACTICE
     regardless of whether rho is real."

That input is now known to be false.  M69's report refutes it at the
headline: the 19-21 % is M66's, it reproduces only on M66's own plant, and
it does not generalise -- on three further real latents the same measurement
gives 0.8380, 1.0274 and 1.0246 and "the sign is not even consistent".
M69's own finding is that FOCUS_NOISE_SD's VALUE is nearly right --
per-stack response noise between 0.9285x and 1.1009x the shipped number,
median 1.0147x -- and it recommends against changing it.  What M69 refutes
is the constant's FORM.

I do not get to keep a verdict whose input has been withdrawn.  The formula
was pre-registered; the number I fed it was wrong; so I re-apply MY OWN
formula to the corrected input and report what it gives.

The apples-to-apples comparator for a multiplicative sigma error in
green_luma_sigma is FOCUS_NOISE_SD's SCALE error, not its form error.  A
4 % scale error is the same kind of object as a 1.5 % scale error and is not
the same kind of object as a 4.06x form error.  Both readings of the scale
error are computed below so the choice is visible rather than assumed:

    median across 12 stacks   1.47 %   ->  threshold 0.25 x 1.47 = 0.37 %
    worst single stack       10.09 %   ->  threshold 0.25 x 10.09 = 2.52 %

Also computed, because "does it matter" is a regime question and my own
discipline 494 says state the regime: the signal level at which the error
crosses the corrected threshold, per ISO.  A worst-case number taken at
S = 0 answers a question nobody asks; where the curve crosses is the
answer that can be acted on.

WHAT I AM NOT DOING HERE.  I am not re-opening C6's measurement.  Facts 16,
17 and 18 of the report are unchanged and are not in question: the sigma
error is over-confident everywhere, never changes sign, peaks at 4.038 %,
and decays with signal.  Those are measurements of my own data and M69 has
no bearing on them.  What is in question is only the adjective the
pre-registration attached to them.

Run: python 07-materiality-recheck.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

spec2 = importlib.util.spec_from_file_location("m72c", HERE / "02-criteria.py")
m72c = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(m72c)

# M69 headline, docs/research/M69-focus-noise-sd.md
M69_SCALE_MEDIAN = 0.0147            # median 1.0147x across all 12 stacks
M69_SCALE_WORST = 0.1009             # worst single stack 1.1009x
M72_PREREG_INPUT = 0.19              # what C6 was actually fed
FRACTION = 0.25                      # C6's pre-registered fraction


def sigma_error(cov: float, var: float, g: float, s: float) -> float:
    """Fractional error in sigma from ignoring cov, at signal s DN."""
    return np.sqrt(1.0 + cov / (var + s * g)) - 1.0


def crossover(cov: float, var: float, g: float, thresh: float) -> float:
    """Signal in DN at which the sigma error falls to thresh. NaN if never above."""
    if sigma_error(cov, var, g, 0.0) <= thresh:
        return float("nan")
    x = (1.0 + thresh) ** 2 - 1.0
    return (cov / x - var) / g


def main() -> int:
    sweep = json.loads((DATA / "01-green-correlation.json").read_text(encoding="utf-8"))
    groups = sorted(sweep["groups"], key=lambda q: q["iso"])

    print("=" * 78)
    print("M72 step 7 -- C6 against M69's corrected numbers")
    print("=" * 78)

    t_orig = FRACTION * M72_PREREG_INPUT
    t_med = FRACTION * M69_SCALE_MEDIAN
    t_worst = FRACTION * M69_SCALE_WORST
    worst_measured = 0.0

    print(f"""
  C6's formula, unchanged:  threshold = {FRACTION} x (FOCUS_NOISE_SD error)

    input as pre-registered   {M72_PREREG_INPUT * 100:6.2f} %  ->  threshold {t_orig * 100:5.3f} %   [REFUTED]
    M69 median scale error    {M69_SCALE_MEDIAN * 100:6.2f} %  ->  threshold {t_med * 100:5.3f} %
    M69 worst-stack scale     {M69_SCALE_WORST * 100:6.2f} %  ->  threshold {t_worst * 100:5.3f} %
""")

    print(f"  {'ISO':>6} {'cov DN^2':>10} {'var DN^2':>10} {'G':>8} "
          f"{'err@S=0':>9} {'S* median':>10} {'S* worst':>9}")
    rows = []
    for q in groups:
        iso = q["iso"]
        p = q["arms"]["k6"]["pairs"]["G1-G2"]
        cov = p["cov"]
        var = 0.5 * (p["var_a"] + p["var_b"])
        g = m72c.gain(float(iso))
        e0 = sigma_error(cov, var, g, 0.0)
        worst_measured = max(worst_measured, e0)
        sm = crossover(cov, var, g, t_med)
        sw = crossover(cov, var, g, t_worst)
        rows.append((iso, sm, sw))
        print(f"  {iso:>6} {cov:10.6f} {var:10.5f} {g:8.5f} "
              f"{e0 * 100:8.3f}% {sm:10.1f} {sw:9.1f}")

    sm_all = np.array([r[1] for r in rows])
    sw_all = np.array([r[2] for r in rows])
    print(f"""
  S* is the signal in DN above black at which the error falls BELOW the
  threshold.  Above S* the effect is immaterial on C6's own arithmetic;
  below it, it is not.

    against M69's median scale error   S* spans {sm_all.min():6.1f} to {sm_all.max():6.1f} DN
    against M69's worst-stack error    S* spans {sw_all.min():6.1f} to {sw_all.max():6.1f} DN
""")

    print("=" * 78)
    print(f"  worst measured sigma error {worst_measured * 100:.3f} %")
    print(f"    vs refuted threshold  {t_orig * 100:5.3f} %  -> "
          f"{'MET' if worst_measured < t_orig else 'NOT MET'}   [the verdict as published]")
    print(f"    vs median threshold   {t_med * 100:5.3f} %  -> "
          f"{'MET' if worst_measured < t_med else 'NOT MET'}")
    print(f"    vs worst-stack thresh {t_worst * 100:5.3f} %  -> "
          f"{'MET' if worst_measured < t_worst else 'NOT MET'}")
    both = worst_measured >= t_med and worst_measured >= t_worst
    print()
    if both:
        print("  C6's IMMATERIAL IN PRACTICE verdict is VOID.  Re-applying my own")
        print("  pre-registered formula to the corrected input gives NOT MET under")
        print("  BOTH readings of the comparator, so the outcome does not depend on")
        print("  which reading is chosen.  The adjective is withdrawn; the")
        print("  measurement it was attached to -- facts 16, 17, 18 -- is not.")
        print()
        print("  C6 also had a DEFECT I did not notice when I wrote it: only the")
        print("  favourable branch carried a consequence.  It said what to conclude")
        print("  if the error was small and said nothing about the other case.  That")
        print("  is discipline 496 in a second guise -- a criterion that can only")
        print("  confirm.  A criterion with one branch is not a criterion.")
    else:
        print("  C6's verdict survives the corrected input.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
