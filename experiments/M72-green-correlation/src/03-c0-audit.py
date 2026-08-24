"""M72 step 3 -- C0 audit.  Declared and committed BEFORE it is run.

DISCLOSURE OF NON-BLINDNESS, written first because it matters.  When I wrote
this file the sweep had printed three of eleven groups.  I had seen that
rho(G1,G2) is roughly +0.083 / +0.068 / +0.054 at ISO 100 / 400 / 800 and
that the frame-permutation null read -0.00659 / -0.00301 / -0.00094 -- i.e.
that C0's |rho| <= 0.005 band is BREACHED at ISO 100.  I had not seen the
other eight groups, and the test declared below is parameter-free algebra
with no fitted quantity, so seeing three numbers cannot have shaped it.

-----------------------------------------------------------------------------
THE PROBLEM

C0 pre-registered: "real-data frame-permutation null |rho| <= 0.005", with
the consequence "no rho in this report stands".  At ISO 100 it reads
-0.00659.  By the letter of the pre-registration C0 is NOT MET and that is
how it will be reported.

THE DERIVATION -- why that band was mis-specified by me

The estimator removes each cell's own TEMPORAL mean before accumulating
cross-products.  Write x~_t = x_t - xbar.  If the underlying series are
correlated only at matched frames, cov(x_s, y_t) = c d_st, then after
centering

    cov(x~_s, y~_t) = c (d_st - 1/T)

because subtracting the sample mean couples every frame to every other.
For the MATCHED estimator,

    E[ sum_t x~_t y~_t ] = c sum_t (1 - 1/T) = c (T - 1)

and for a DERANGEMENT pi, where no frame keeps its partner so d_{t,pi(t)}=0
for every t,

    E[ sum_t x~_t y~_pi(t) ] = c sum_t (0 - 1/T) = -c

Therefore, with no free parameters at all,

    cov_perm / cov_matched  =  -1 / (T - 1)  =  -1/19  =  -0.052632

A frame-permutation null CANNOT be zero when a real correlation exists.  It
is forced to -rho/(T-1), which at rho = +0.083 is -0.0044 -- most of the
-0.0066 observed.  My C0 band was written as though the null could be zero
in the presence of a signal, and it cannot.  That is a defect in my
criterion, not in the instrument, and I am obliged to show it rather than
assert it.

WHY THIS IS NOT SIMPLY AN EXCUSE

M62 section 9.1 has precedent for reporting a tripped criterion as
mis-specified.  The reason that move is dangerous is that it is always
available after the fact.  What makes it checkable here is that the
replacement is a PARAMETER-FREE PREDICTION tested 66 times:

  T1  cov_perm / cov_matched = -1/(T-1) = -0.052632 for every pair at every
      ISO where the correlation is measurable.  Nothing is fitted.
  T2  The BIAS-CORRECTED null, rho_perm + rho_matched/(T-1), must satisfy
      the ORIGINAL C0 band |.| <= 0.005.  This is C0's actual intent and it
      can still fail.
  T3  The synthetic null, where the true rho is zero, must show NO such
      offset -- it read +0.00004 in the selftest, which is the control that
      makes T1 a statement about signal rather than about the estimator.

  PRE-DECLARED CONSEQUENCES:
    - If T1 holds (mean ratio within +/-0.010 of -0.052632 over the pairs
      with |rho| > 0.01) AND T2 holds AND T3 holds, C0 is reported as NOT
      MET BY THE LETTER, attributed to a mis-specified band, with the
      correction shown; the rho results stand and say so explicitly.
    - If ANY of T1, T2, T3 fails, C0's original consequence is honoured in
      full: no rho in this report stands, and the milestone reports that it
      could not measure the quantity it was commissioned to measure.

  There is no third branch and I am not going to invent one.
-----------------------------------------------------------------------------

Run: python 03-c0-audit.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

spec = importlib.util.spec_from_file_location("m72", HERE / "01-green-correlation.py")
m72 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m72)

T1_BAND = 0.010
T1_MIN_RHO = 0.01
T2_BAND = m72.C0_BAND
T3_BAND = m72.C0_BAND


def main() -> int:
    payload = json.loads((DATA / "01-green-correlation.json").read_text(encoding="utf-8"))
    groups = sorted(payload["groups"], key=lambda r: r["iso"])
    t = payload["t_frames"]
    predicted = -1.0 / (t - 1)

    print("M72 -- C0 audit.  Parameter-free prediction, declared before running.")
    print(f"T = {t} frames, so cov_perm/cov_matched must equal -1/(T-1) = {predicted:.6f}")

    print("\nT1 -- ratio cov_perm / cov, arm k6, all six pairs, all ISOs")
    print(f"  {'ISO':>5}  " + "  ".join(f"{a}-{b}".rjust(9) for a, b, _ in m72.PAIRS))
    ratios = []
    for r in groups:
        pr = r["arms"]["k6"]["pairs"]
        cells = []
        for a, b, _ in m72.PAIRS:
            e = pr[f"{a}-{b}"]
            if abs(e["rho_shep"]) > T1_MIN_RHO and e["cov"] != 0:
                q = e["cov_perm"] / e["cov"]
                ratios.append(q)
                cells.append(f"{q:+9.5f}")
            else:
                cells.append(f"{'--':>9}")
        print(f"  {r['iso']:5.0f}  " + "  ".join(cells))
    ratios = np.array(ratios)
    mean_ratio = float(ratios.mean()) if len(ratios) else float("nan")
    print(f"\n  n = {len(ratios)} pair-ISO cells with |rho| > {T1_MIN_RHO}")
    print(f"  mean ratio {mean_ratio:+.6f}   predicted {predicted:+.6f}   "
          f"difference {mean_ratio - predicted:+.6f}")
    print(f"  sd of ratios {ratios.std(ddof=1):.6f}   band +/-{T1_BAND}")
    t1 = abs(mean_ratio - predicted) <= T1_BAND
    print(f"  T1: {'PASS' if t1 else 'FAIL'}")

    print("\nT2 -- bias-corrected null, rho_perm + rho/(T-1), must meet C0's band")
    print(f"  {'ISO':>5}  " + "  ".join(f"{a}-{b}".rjust(9) for a, b, _ in m72.PAIRS))
    worst = 0.0
    for r in groups:
        pr = r["arms"]["k6"]["pairs"]
        cells = []
        for a, b, _ in m72.PAIRS:
            e = pr[f"{a}-{b}"]
            v = e["rho_perm"] + e["rho_shep"] / (t - 1)
            worst = max(worst, abs(v))
            cells.append(f"{v:+9.5f}")
        print(f"  {r['iso']:5.0f}  " + "  ".join(cells))
    print(f"\n  worst |corrected null| {worst:.6f}   band +/-{T2_BAND}")
    t2 = worst <= T2_BAND
    print(f"  T2: {'PASS' if t2 else 'FAIL'}")

    print("\nT3 -- synthetic null, true rho = 0, must show no such offset")
    s = payload["synthetic_null"]
    print(f"  rho_shep {s['rho_shep']:+.6f}   rho_perm {s['rho_perm']:+.6f}")
    print(f"  offset predicted for rho=0 is exactly 0; band +/-{T3_BAND}")
    t3 = abs(s["rho_perm"]) <= T3_BAND and abs(s["rho_shep"]) <= T3_BAND
    print(f"  T3: {'PASS' if t3 else 'FAIL'}")

    print("\n" + "=" * 78)
    if t1 and t2 and t3:
        print("VERDICT: C0 is NOT MET BY THE LETTER of the pre-registration.")
        print("The band was mis-specified by me: a frame-permutation null cannot")
        print("be zero when a real correlation exists, and is forced to")
        print(f"-rho/(T-1).  The parameter-free prediction {predicted:+.6f} is")
        print(f"confirmed at {mean_ratio:+.6f} over {len(ratios)} cells, the")
        print("bias-corrected null meets C0's original band, and the synthetic")
        print("control shows no offset.  Per the declared consequence the rho")
        print("results STAND, and C0 is reported as NOT MET throughout.")
    else:
        print("VERDICT: C0's ORIGINAL CONSEQUENCE IS HONOURED IN FULL.")
        print("No rho in this report stands.  The milestone reports that it")
        print("could not measure the quantity it was commissioned to measure.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
