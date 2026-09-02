"""
Commissioning for refit_width.py.

WHY THIS EXISTS
---------------
refit_width.py reproduced the razor-verifier's w to 0.1 um on both estimators
on its first run. Under house rule 9 that is worth nothing on its own: a fit
rigged to always answer "width-dominated" would have produced exactly the same
agreement. The question a first-run agreement cannot answer is whether the
instrument is capable of returning the OTHER verdict.

So the load-bearing control here is C1, a planted SHARP EDGE. If the fit still
says width-dominated when handed rises that grow in exact proportion to
f-number, then the M128 verdict is an artefact of the estimator and must be
withdrawn.

Per the standing lesson that a defect-only commissioning is blind to a metric
that scores an IMPROVEMENT better, the plants below deliberately span both
directions: C1 and C4 plant the opposite conclusion, C2 and C3 plant the
expected one at known strength.

CONTROLS
--------
  C1  PLANTED SHARP EDGE. rise = k*N exactly, k = 1.8 um/f#, real sigmas.
      MUST return k > 0, w at or near 0, and MUST NOT exclude w = 0.
      This is the positive control for the opposite verdict.

  C2  PLANTED PURE WIDTH. rise identical at all three apertures.
      MUST recover that width and k = 0. (Recovery only -- see the disclosed
      error below for why no significance bar is asserted here.)

  C2b DERIVED SIGNIFICANCE. The significance of the C2 flat plant MUST match a
      CLOSED-FORM weighted-least-squares derivation of the same quantity, to
      within 0.05 sigma. This replaces a guessed bar with a derived one: the
      grid search and the algebra must independently agree.

  C3  PLANTED MIXTURE at known w and k. MUST recover both inside the 68%
      interval. Tests that the estimator is not saturated at one extreme.

  C4  SIGMA RESPONSIVENESS. Real data with sigmas inflated 3x.
      Significance MUST fall materially. If it does not, the quoted
      uncertainties are not entering the inference at all and every sigma
      this lane reports is decorative.

  C5  NULL. Real data, unmodified. MUST reproduce the committed refit.json
      exactly. Guards against the commissioning harness perturbing shared state.

MY OWN ERROR IN THIS FILE, DISCLOSED
------------------------------------
Run 1 of C2 asserted that a flat 18 um plant must exclude w = 0 at MORE than
2 sigma. It came back at 1.47 sigma and I recorded a MISS. The instrument was
right and the bar was mine: closed-form weighted least squares gives 1.4681
sigma for that plant, agreeing with the grid to four decimals.

The bar was not lowered to make the control pass. It was replaced by C2b, which
derives the number a second way instead of guessing it -- a control that agrees
with a guess tests the guess, while a control that agrees with an independent
derivation tests the instrument.

The error was also informative, and the finding is reported in the amendment. A
FLAT rise excludes the sharp model at only 1.47 sigma, whereas the real,
DECREASING rise excludes it at 2.53 sigma. The M128 verdict therefore does not
rest on the rise merely failing to grow. It rests on the rise falling where the
sharp model requires it to nearly double, and that is the stronger statement.

Every control states its pass condition BEFORE the run, in this docstring.
"""

import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
N = [5.6, 8.0, 11.0]

REAL = {
    "isotonic": {"rise": [20.86, 19.91, 16.50], "sd": [5.6, 5.3, 5.4]},
    "erf":      {"rise": [18.42, 16.29, 16.62], "sd": [3.4, 4.7, 3.9]},
}

K_GRID = [ki * 0.005 for ki in range(0, 801)]
W_GRID = [i * 0.05 for i in range(0, 1201)]


def chi2(w, k, rise, sd):
    s = 0.0
    for n, r, e in zip(N, rise, sd):
        pred = math.sqrt(w * w + (k * n) ** 2)
        s += ((r - pred) / e) ** 2
    return s


def fit(rise, sd, wfix=None):
    best = (1e18, None, None)
    ws = [wfix] if wfix is not None else W_GRID
    for w in ws:
        for k in K_GRID:
            v = chi2(w, k, rise, sd)
            if v < best[0]:
                best = (v, w, k)
    return best


def analyse(rise, sd):
    chi_free, w_hat, k_hat = fit(rise, sd)
    chi_null, _, _ = fit(rise, sd, wfix=0.0)
    dchi = chi_null - chi_free
    prof = [(w, fit(rise, sd, wfix=w)[0]) for w in W_GRID]
    lo68 = min((w for w, c in prof if c - chi_free <= 1.0), default=float("nan"))
    hi68 = max((w for w, c in prof if c - chi_free <= 1.0), default=float("nan"))
    return {"w": w_hat, "k": k_hat, "dchi2": dchi,
            "sigma": math.sqrt(dchi) if dchi > 0 else 0.0,
            "w68": [lo68, hi68]}


rows = []
verdicts = []


def report(cid, desc, expect, got, ok, detail):
    verdicts.append(ok)
    tag = "CAUGHT" if ok else "*** MISSED ***"
    rows.append({"id": cid, "desc": desc, "expect": expect, "got": got, "ok": ok})
    print("%-4s %-38s %s" % (cid, desc, tag))
    print("      expected: %s" % expect)
    print("      observed: %s" % detail)
    print()


print("COMMISSIONING refit_width.py")
print("=" * 74)
print()

# ---------------------------------------------------------------- C1
k_true = 1.8
sharp = [k_true * n for n in N]
r = analyse(sharp, REAL["isotonic"]["sd"])
ok = (r["k"] > 1.0) and (r["w"] < 5.0) and (r["sigma"] < 1.0)
report("C1", "planted SHARP EDGE (rise = 1.8*N)",
       "k>1.0, w<5um, w=0 NOT excluded (sigma<1)",
       r, ok,
       "w=%.2f um  k=%.3f um/f#  w=0 excluded at %.2f sigma" % (r["w"], r["k"], r["sigma"]))

# ---------------------------------------------------------------- C2
w_true = 18.0
pure = [w_true, w_true, w_true]
r = analyse(pure, REAL["isotonic"]["sd"])
ok = (abs(r["w"] - w_true) < 1.0) and (r["k"] < 0.3)
report("C2", "planted PURE WIDTH (rise flat at 18um)",
       "w~18um, k~0  (recovery only; see C2b)",
       r, ok,
       "w=%.2f um  k=%.3f um/f#  w=0 excluded at %.2f sigma" % (r["w"], r["k"], r["sigma"]))


# ---------------------------------------------------------------- C2b
def closed_form_sigma(rise, sd):
    """Weighted least squares for the w=0 null, done algebraically not on a grid.

    Under w=0 the model is rise = k*N, linear in k through the origin, so the
    optimum has a closed form. For a plant whose free-model residual is exactly
    zero, chi2_null IS delta-chi2 and sigma = sqrt(chi2_null).
    """
    num = sum(ri * ni / si ** 2 for ri, ni, si in zip(rise, N, sd))
    den = sum(ni ** 2 / si ** 2 for ni, si in zip(N, sd))
    k = num / den
    chi = sum(((ri - k * ni) / si) ** 2 for ri, ni, si in zip(rise, N, sd))
    return k, chi, math.sqrt(chi)


k_cf, chi_cf, sig_cf = closed_form_sigma(pure, REAL["isotonic"]["sd"])
grid_sig = r["sigma"]
ok = abs(grid_sig - sig_cf) < 0.05
report("C2b", "DERIVED significance (grid vs algebra)",
       "grid sigma matches closed-form WLS to within 0.05",
       {"grid": grid_sig, "closed_form": sig_cf},
       ok,
       "grid %.4f sigma vs closed-form %.4f sigma  (k*=%.4f, diff %.4f)"
       % (grid_sig, sig_cf, k_cf, abs(grid_sig - sig_cf)))

# ---------------------------------------------------------------- C3
w_mix, k_mix = 14.0, 1.2
mix = [math.sqrt(w_mix ** 2 + (k_mix * n) ** 2) for n in N]
r = analyse(mix, REAL["isotonic"]["sd"])
ok = (r["w68"][0] <= w_mix <= r["w68"][1])
report("C3", "planted MIXTURE (w=14um, k=1.2)",
       "true w inside the 68%% interval",
       r, ok,
       "w=%.2f um  68%% interval %.1f-%.1f um  contains 14.0: %s"
       % (r["w"], r["w68"][0], r["w68"][1], ok))

# ---------------------------------------------------------------- C4
base = analyse(REAL["erf"]["rise"], REAL["erf"]["sd"])
infl = analyse(REAL["erf"]["rise"], [s * 3.0 for s in REAL["erf"]["sd"]])
ok = infl["sigma"] < base["sigma"] * 0.6
report("C4", "SIGMA RESPONSIVENESS (erf sigmas x3)",
       "significance falls below 60%% of baseline",
       infl, ok,
       "baseline %.2f sigma -> inflated %.2f sigma  (%.0f%% of baseline)"
       % (base["sigma"], infl["sigma"], infl["sigma"] / base["sigma"] * 100))

# ---------------------------------------------------------------- C5
print("C5   NULL: re-running the real script unmodified")
proc = subprocess.run([sys.executable, os.path.join(HERE, "refit_width.py")],
                      capture_output=True, text=True, cwd=HERE)
with open(os.path.join(HERE, "refit.json"), encoding="utf-8") as f:
    got = json.load(f)
null_ok = (proc.returncode == 0
           and abs(got["t2"]["isotonic"]["w"] - 19.05) < 0.01
           and abs(got["t2"]["erf"]["w"] - 17.35) < 0.01)
verdicts.append(null_ok)
print("     %s  rc=%d  w_iso=%.2f  w_erf=%.2f"
      % ("GREEN" if null_ok else "*** RED ***", proc.returncode,
         got["t2"]["isotonic"]["w"], got["t2"]["erf"]["w"]))
print()

caught = sum(1 for v in verdicts if v)
total = len(verdicts)
print("=" * 74)

# Derived finding that fell out of the C2 error -- reported, not asserted as a control.
_, _, sig_flat = closed_form_sigma(pure, REAL["isotonic"]["sd"])
_, _, sig_real = closed_form_sigma(REAL["erf"]["rise"], REAL["erf"]["sd"])
print("FINDING (from the disclosed C2 error):")
print("  a FLAT rise excludes the sharp model at only %.2f sigma;" % sig_flat)
print("  the real DECREASING rise excludes it at %.2f sigma." % sig_real)
print("  The verdict rests on the rise FALLING, not merely on it not growing.")
print()

print("plants+null: %d    caught/green: %d    missed: %d" % (total, caught, total - caught))
print("STATUS: %s" % ("COMMISSIONED" if caught == total else "NOT COMMISSIONED"))

with open(os.path.join(HERE, "commission.json"), "w", encoding="utf-8") as f:
    json.dump({"rows": rows, "null_ok": null_ok,
               "total": total, "caught": caught,
               "sigma_flat_plant": sig_flat, "sigma_real": sig_real,
               "status": "COMMISSIONED" if caught == total else "NOT COMMISSIONED"},
              f, indent=2)
sys.exit(0 if caught == total else 1)
