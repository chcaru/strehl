"""M72 step 5 -- audit of F1 and F2, declared and committed BEFORE running.

04 fired four checks.  Two are results (F3, F4).  Two are failures of my own
instrument gates (F1, F2) and I declared both fatal:

    F1 fail -> "the estimator is wrong and nothing here is reported"
    F2 fail -> "disagreement kills the field, not the criteria"

Both fired at both ISOs.  By the letter, the correlation field is discarded
and F3 and F4 go with it.  Before accepting that I am obliged to find out
whether the gates were mis-specified, the same way C0 was -- and obliged to
do it with tests that can fail rather than with an explanation.

WHAT I THINK WENT WRONG, WRITTEN BEFORE THE TEST RUNS

F1 asked for rho(0,0) = 1.000000.  It measured 1.11276 at ISO 100 and
1.00703 at ISO 1600.  But 04 applies Sheppard's correction to the
DENOMINATOR only, so at zero lag the estimator is

    rho(0,0) = S / (S - n (T-1)/12)  =  Vbar / (Vbar - 1/12)

where Vbar is the mask-weighted mean per-pixel temporal variance.  That is
GREATER than one by construction, and the amount is fixed by Vbar with
nothing free.  If that is what happened, F1 was a check on a quantity my own
correction guarantees is not 1, and its failure CONFIRMS Sheppard is applied
rather than showing the estimator is wrong.

F2 compared the field's G1->G2 entry (+0.09133) against 02-criteria's
rho(G1,G2) (+0.08261) and found +0.00872, over the 0.005 tolerance.  R->B
agreed at +0.00112.  The two numbers are computed over DIFFERENT PIXEL SETS:
02 uses the whole 2344x3514 plane, 04 uses a 2400x2400 central crop whose
median temporal variance is 0.787 DN^2 against the full plane's ~1.00.  The
centre of this sensor is quieter than its edges, which M68 already found for
a different statistic.  If rho varies across the sensor, the two numbers
SHOULD differ and my tolerance compared things that were never the same
quantity.

TESTS, with consequences, declared before running:

  A1  PARAMETER-FREE.  rho(0,0) must equal Vbar/(Vbar - 1/12) to within
      1e-4, at both ISOs, with Vbar taken from the same masked pixels.  Two
      predictions, nothing fitted.

  A2  CODE-PATH CROSS-VALIDATION, can fail.  Run 01's pooled_moments -- the
      function 02-criteria uses, unmodified -- on the IDENTICAL crop with an
      IDENTICAL mask, and compare with the field's own G1->G2 and R->B
      entries recomputed on a consistently-masked footing.
        A2a  the two code paths on a matched pixel set must agree to 0.002
        A2b  the residual gap to 04's published entry is the effect of 04's
             documented denominator approximation and must be <= 0.002

  A3  MEASUREMENT, not a gate.  rho(G1,G2) on the full plane against the
      same crop, with the variance ratio.  This quantifies how much of F2's
      gap is pixel set.  It is allowed to be large; if it is, that is a new
      finding and is reported as one.

  PRE-DECLARED CONSEQUENCES:
    - A1 and A2 both pass -> F1 and F2 are reported as FAILED AS WRITTEN
      with the mis-specification named, and F3 and F4 STAND.  They are
      internal comparisons within a single field over a single pixel set,
      so neither the zero-lag normalisation nor the pixel-set difference can
      touch them -- but that argument is only available if A1 and A2 hold.
    - EITHER fails -> F2's declared consequence is honoured in full: the
      correlation field is discarded, F3 and F4 are WITHDRAWN, and the
      report says the post-hoc measurement did not survive its own gates.

Also computed here, because C5 needs it and nothing else provides it: the
variance's own alpha/delta split per plane, so the covariance's upstream
fraction has something to be compared against.

Run: python 05-field-audit.py
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

spec4 = importlib.util.spec_from_file_location("m72f", HERE / "04-correlation-field.py")
m72f = importlib.util.module_from_spec(spec4)
spec4.loader.exec_module(m72f)

spec2 = importlib.util.spec_from_file_location("m72c", HERE / "02-criteria.py")
m72c = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(m72c)

A1_TOL = 1e-4
A2_TOL = 0.002


def main() -> int:
    field = json.loads((DATA / "04-correlation-field.json").read_text(encoding="utf-8"))
    sweep = json.loads((DATA / "01-green-correlation.json").read_text(encoding="utf-8"))
    by_group = {r["group"]: r for r in sweep["groups"]}
    t = sweep["t_frames"]
    fails = []

    for name, want_iso in m72f.GROUPS:
        print("=" * 78)
        print(f"{name}  ISO {want_iso}")
        print("=" * 78)
        iso, x = m72f.load_crop(m72.DARKS / name)
        x = x - x.mean(axis=0, keepdims=True)
        ss = np.einsum("tij,tij->ij", x, x)
        var = ss / (t - 1)
        med = float(np.median(var))
        good = var <= m72f.VAR_OUTLIER * med
        x *= good.astype(np.float32)

        # ---------------------------------------------------------- A1
        lo, hi = m72f.RAD, m72f.CROP - m72f.RAD
        gg = good[lo:hi, lo:hi]
        n = int(gg.sum())
        s = float((ss[lo:hi, lo:hi] * gg).sum())
        vbar = s / (n * (t - 1))
        predicted = vbar / (vbar - 1.0 / 12.0)
        measured = field[name]["grid"]["0,0"]
        print(f"\n  A1  Vbar over the masked window = {vbar:.6f} DN^2")
        print(f"      predicted rho(0,0) = Vbar/(Vbar - 1/12) = {predicted:.8f}")
        print(f"      measured  rho(0,0)                      = {measured:.8f}")
        print(f"      difference {measured - predicted:+.2e}   tol {A1_TOL}")
        ok = abs(measured - predicted) <= A1_TOL
        print(f"      A1: {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"A1@{name}")

        # ---------------------------------------------------------- A2
        g1 = np.ascontiguousarray(x[:, 0::2, 1::2])
        g2 = np.ascontiguousarray(x[:, 1::2, 0::2])
        r = np.ascontiguousarray(x[:, 0::2, 0::2])
        b = np.ascontiguousarray(x[:, 1::2, 1::2])
        m_g = good[0::2, 1::2] & good[1::2, 0::2]
        m_rb = good[0::2, 0::2] & good[1::2, 1::2]

        print("\n  A2  01's pooled_moments, unmodified, on the identical crop")
        rows = []
        for label, u, v, m, fkey, fphase in (
            ("G1-G2", g1, g2, m_g, "1,-1", "G1"),
            ("R-B", r, b, m_rb, "1,1", "R"),
        ):
            vxx, vyy, vxy, npair = m72.pooled_moments(u, v, m)
            rho_matched = m72.rho_from(vxx, vyy, vxy, True)
            rho_field = field[name]["by_phase"][fphase][fkey]
            rho_full = by_group[name]["arms"]["k6"]["pairs"][label]["rho_shep"]
            rows.append((label, rho_matched, rho_field, rho_full, npair))
            print(f"      {label:6s} matched-set {rho_matched:+.6f}   "
                  f"04 field {rho_field:+.6f}   diff {rho_field - rho_matched:+.6f}")
        worst = max(abs(f - m) for _, m, f, _, _ in rows)
        print(f"      worst |field - matched| {worst:.6f}   tol {A2_TOL}")
        ok = worst <= A2_TOL
        print(f"      A2: {'PASS' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"A2@{name}")

        # ---------------------------------------------------------- A3
        print("\n  A3  pixel set, a measurement rather than a gate")
        full_var = by_group[name]["arms"]["k6"]["pairs"]["G1-G2"]["var_a"]
        print(f"      mean temporal var: crop {vbar:.5f}   full plane {full_var:.5f}"
              f"   ratio {vbar / full_var:.5f}")
        for label, rho_matched, rho_field, rho_full, npair in rows:
            print(f"      {label:6s} crop {rho_matched:+.6f}   full plane {rho_full:+.6f}"
                  f"   crop/full {rho_matched / rho_full:.4f}   pairs {npair}")
        del x, g1, g2, r, b

    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("C5 support -- the VARIANCE's own alpha/delta split, per plane")
    print("=" * 78)
    groups = sorted(sweep["groups"], key=lambda q: q["iso"])
    isos = np.array([q["iso"] for q in groups], float)
    g = np.array([m72c.gain(i) for i in isos])
    md = np.array([m72c.mode(i) for i in isos])
    print("\n  var(ISO) = alpha G^2 + delta, same fit 02 applies to cov.")
    print(f"\n  {'plane':>6} {'alpha_low':>11} {'alpha_high':>11} {'delta':>11} "
          f"{'upstream frac':>14}")
    varfits = {}
    for plane, pair, which in (("R", "R-G1", "var_a"), ("G1", "G1-G2", "var_a"),
                               ("G2", "G1-G2", "var_b"), ("B", "R-B", "var_b")):
        y = np.array([q["arms"]["k6"]["pairs"][pair][which] for q in groups])
        fit = m72c.jackknife_fit(g, md, y)
        up = fit["alpha_low"] * m72c.gain(100.0) ** 2
        frac = up / (up + fit["delta"])
        varfits[plane] = (frac, fit)
        print(f"  {plane:>6} {fit['alpha_low']:11.5f} {fit['alpha_high']:11.5f} "
              f"{fit['delta']:11.6f} {frac:14.4f}")
        print(f"  {'':>6} {'+/-' + format(fit['alpha_low_se'], '.5f'):>11} "
              f"{'+/-' + format(fit['alpha_high_se'], '.5f'):>11} "
              f"{'+/-' + format(fit['delta_se'], '.6f'):>11}")
    covy = np.array([q["arms"]["k6"]["pairs"]["G1-G2"]["cov"] for q in groups])
    cfit = m72c.jackknife_fit(g, md, covy)
    cup = cfit["alpha_low"] * m72c.gain(100.0) ** 2
    cfrac = cup / (cup + cfit["delta"])
    print(f"  {'cov':>6} {cfit['alpha_low']:11.5f} {cfit['alpha_high']:11.5f} "
          f"{cfit['delta']:11.6f} {cfrac:14.4f}")
    gmean = 0.5 * (varfits["G1"][0] + varfits["G2"][0])
    ga = 0.5 * (varfits["G1"][1]["alpha_low"] + varfits["G2"][1]["alpha_low"])
    gd = 0.5 * (varfits["G1"][1]["delta"] + varfits["G2"][1]["delta"])
    print(f"""
  Green variance upstream fraction at base ISO {gmean:.4f}
  Green covariance upstream fraction at base ISO {cfrac:.4f}
  The covariance is {'MORE' if cfrac > gmean else 'LESS'} upstream-weighted than the variance.
  Falling rho with ISO therefore means the covariance is generated
  relatively further DOWN the chain than the noise it correlates.

  INCIDENTAL, not pre-registered, routed and not adjudicated here.
  M68 measured the B plane at 0.84x the greens' apparent conversion gain and
  could not tell a true gain difference from a pre-ADC scale.  A dark-frame
  variance fit splits into a term that scales with gain^2 and one that does
  not, so it carries information a PTC ratio cannot:
      alpha_B / alpha_green = {varfits['B'][1]['alpha_low'] / ga:.4f}
      delta_B / delta_green = {varfits['B'][1]['delta'] / gd:.4f}
  A single scale s applied to everything upstream of the ADC predicts
  alpha_B/alpha_green = s^2 = {0.8396 ** 2:.4f} and delta_B/delta_green = 1
  (quantisation is added after the scale and cannot be scaled by it).
  Neither prediction is met.  I am not adjudicating this; M71 owns the
  photon-transfer cross-check and this is its evidence, not mine.
""")

    print("=" * 78)
    if not fails:
        print("VERDICT: A1 and A2 PASS.")
        print("F1 and F2 are reported as FAILED AS WRITTEN, with the")
        print("mis-specification named in each case: F1 asked for a zero-lag")
        print("value that Sheppard's correction guarantees exceeds 1, and F2")
        print("compared two different pixel sets. F3 and F4 STAND.")
    else:
        print("VERDICT: F2's declared consequence is honoured in full.")
        print(f"Failed: {fails}.  The correlation field is DISCARDED and F3")
        print("and F4 are WITHDRAWN.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
