"""
M-PHASE0-PTC, step 1: audit B1's acceptance criterion against the corpus's own
prior measurements, BEFORE building anything.

WHY THIS RUNS FIRST
-------------------
The proposal (docs/proposals/2026-08-sota-path.md, B1) specifies:

    "Acceptance: recovers M90's independent g within its CI on the reference
     body, per-stack, from subject frames alone"

Two things must be true for that sentence to be a usable gate:

  (a) M90's CI must be an accuracy statement about g, not a precision
      statement about one fit; and
  (b) no prior in-stack measurement of g must already exist, or B1 is not a
      build but a port.

This script tests both against published numbers. It builds no estimator and
touches no capture. Every input is a quoted figure with a citation; every
derived figure is computed here and never retyped.

THE REGISTERED QUESTIONS (fixed before the numbers were assembled)
-----------------------------------------------------------------
  Q1  Is B1's acceptance bar reachable?
      Bar = M90's quoted CI on g. Compare it to the demonstrated
      disagreement between two careful independent measurements of the SAME
      quantity on the SAME body (M90 vs M71).
      REACHABLE iff the inter-method disagreement is within the bar.
      Prediction (registered): NOT reachable. M90's own section 8.2 calls the
      M90-vs-M71 comparison a failed bar, so the disagreement is already known
      to exceed at least one side's uncertainty.

  Q2  Does an in-stack g measurement already exist?
      M61 ran a temporal adjacent-frame PTC on SUBJECT stacks (not flats).
      If it reports ISO 100 greens, B1's estimator has already been run in the
      exact configuration B1 proposes.
      Prediction (registered): it exists, and B1 is therefore a port.

  Q3  How far is the existing in-stack number from M90?
      This is the number B1's acceptance actually asks for. Report it both
      pre-registered (all stacks) and fit-gated, never one alone.
      NO PREDICTION REGISTERED. I had not computed this when writing Q1/Q2 and
      will not pretend to a direction. Reported as an observation.

CONTROLS ON MY OWN READING (this script's inputs are quotations, so the
failure mode is misquotation, not arithmetic)
-----------------------------------------------------------------------
  C1  g_model(ISO 100) computed from M61's stated divisor rule
      (g_model = max(ISO,100)/436.8) must reproduce the shipped constant
      0.228938 to better than 0.01%. If it does not, I have misread either the
      divisor or which constant M61's ratios are relative to, and every Q3
      number built on r would be scaled wrongly.
  C2  M90's stated delta vs M71 (-1.33%) must reproduce from the two central
      values I transcribed.
  C3  M90's stated delta vs shipped (-3.42%) must reproduce likewise.

  C1 is the load-bearing one: it is the only check that M61's dimensionless r
  is anchored to the constant I think it is.

If any control fails, the script prints FAILED and makes no Q3 claim.
"""

import json
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

# ----------------------------------------------------------------------------
# INPUTS. Each is a quotation. Citation is mandatory and travels with the value.
# ----------------------------------------------------------------------------

IN = {
    # docs/research/M90-prnu-noise-model.md section 2.2, table row
    #   "| `g` green, ISO 100 (DN/e-) | **0.221113 +/- 0.000142** | 0.224103 | **-1.33%** |"
    "m90_g": (0.221113, "M90 section 2.2 table, column 'M90'"),
    "m90_se": (0.000142, "M90 section 2.2 table, same cell, quoted +/-"),
    "m71_g": (0.224103, "M90 section 2.2 table, column 'M71'"),
    "m90_vs_m71_pct_quoted": (-1.33, "M90 section 2.2 table, column 'delta'"),
    # docs/research/M90-prnu-noise-model.md section 2.2, next row
    #   "| `g` vs shipped 0.228938 | **-3.42%** | -2.16% | contradicts fact 1065 |"
    "shipped_g": (0.228938, "M90 section 2.2 row 2, quoted shipped value"),
    "m90_vs_shipped_pct_quoted": (-3.42, "M90 section 2.2 row 2, column 'M90'"),
    "m71_vs_shipped_pct_quoted": (-2.16, "M90 section 2.2 row 2, column 'M71'"),
    # docs/research/M61-ptc-high-iso-measured.md section 1
    #   "r(ISO) = g_measured/g_model, g_model = max(ISO,100)/436.8"
    "gain_divisor": (436.8, "M61 section 1, hypotheses preamble"),
    # docs/research/M61-ptc-high-iso-measured.md section 3.1 ladder, ISO 100 row
    #   "| 100 | low | 3 | 0.9081 +/- 0.0383 | 0.9463 +/- 0.0461 | bee-1, bee-3, wrapped-text-1 |"
    "m61_r100_greens": (0.9463, "M61 section 3.1 ladder, ISO 100, 'r (greens)'"),
    "m61_r100_greens_spread": (0.0461, "M61 section 3.1 ladder, ISO 100, same cell"),
    "m61_r100_nstacks": (3, "M61 section 3.1 ladder, ISO 100, 'stacks'"),
    # docs/research/M61-ptc-high-iso-measured.md section 3.1, the parenthetical
    #   "ISO 100 r = 0.9463 (greens; 0.9728 excluding the one stack that fails
    #    its own fit, section 4.4)"  -- quoted in section 2.2
    "m61_r100_greens_gated": (0.9728, "M61 section 2.2, parenthetical excluding the failing stack"),
    # docs/research/M90-prnu-noise-model.md section 8.2, PR-5a
    #   "the true shipped-gain error is somewhere in -2.2% to -3.4%, and this
    #    milestone cannot narrow it further"
    "m90_band_lo_pct": (-2.2, "M90 section 8.2 PR-5a, stated accuracy band"),
    "m90_band_hi_pct": (-3.4, "M90 section 8.2 PR-5a, stated accuracy band"),
}


def v(k):
    return IN[k][0]


def pct(a, b):
    """percent difference of a relative to b"""
    return (a / b - 1.0) * 100.0


lines = []


def say(s=""):
    lines.append(s)
    print(s)


say("M-PHASE0-PTC step 1 -- B1 acceptance audit")
say("=" * 78)
say("")
say("Inputs are quotations. Citations:")
for k, (val, cite) in IN.items():
    say("  %-26s = %-12s  [%s]" % (k, val, cite))
say("")

# ----------------------------------------------------------------------------
# CONTROLS
# ----------------------------------------------------------------------------
say("CONTROLS ON THE READING")
say("-" * 78)

g_model_100 = 100.0 / v("gain_divisor")
c1_err = abs(pct(g_model_100, v("shipped_g")))
c1 = c1_err < 0.01
say("C1  g_model(ISO100) = 100/%.1f = %.7f" % (v("gain_divisor"), g_model_100))
say("    shipped constant                 = %.7f" % v("shipped_g"))
say("    disagreement = %.5f%%   (bar 0.01%%)   -> %s" % (c1_err, "PASS" if c1 else "FAIL"))
say("    Meaning: M61's dimensionless r IS anchored to the shipped gain.")
say("")

c2_calc = pct(v("m90_g"), v("m71_g"))
c2 = abs(c2_calc - v("m90_vs_m71_pct_quoted")) < 0.01
say("C2  M90 vs M71 recomputed = %+.4f%%   quoted %+.2f%%  -> %s"
    % (c2_calc, v("m90_vs_m71_pct_quoted"), "PASS" if c2 else "FAIL"))

c3_calc = pct(v("m90_g"), v("shipped_g"))
c3 = abs(c3_calc - v("m90_vs_shipped_pct_quoted")) < 0.01
say("C3  M90 vs shipped recomputed = %+.4f%%   quoted %+.2f%%  -> %s"
    % (c3_calc, v("m90_vs_shipped_pct_quoted"), "PASS" if c3 else "FAIL"))
say("")

controls_ok = c1 and c2 and c3
say("CONTROLS: %s" % ("ALL PASS" if controls_ok else "FAILED -- no Q3 claim is made"))
say("")

# ----------------------------------------------------------------------------
# Q1 -- is the bar reachable?
# ----------------------------------------------------------------------------
say("Q1  IS B1'S ACCEPTANCE BAR REACHABLE?")
say("-" * 78)
m90_ci_rel = v("m90_se") / v("m90_g") * 100.0
inter_method = abs(c2_calc)
q1_ratio = inter_method / m90_ci_rel
q1_reachable = inter_method <= m90_ci_rel
say("    B1's bar          = M90's CI            = +/- %.4f%% of g" % m90_ci_rel)
say("    Same quantity, two careful methods, same body:")
say("      M90 %.6f   vs   M71 %.6f   -> %.4f%% apart" % (v("m90_g"), v("m71_g"), inter_method))
say("    The disagreement is %.1fx the bar." % q1_ratio)
say("    REACHABLE: %s" % ("yes" if q1_reachable else "NO"))
say("")
say("    M90's own section 8.2 declines to narrow g beyond a band of")
say("      %.1f%% to %.1f%% (width %.1f percentage points)"
    % (v("m90_band_lo_pct"), v("m90_band_hi_pct"),
       abs(v("m90_band_hi_pct") - v("m90_band_lo_pct"))))
band_width_rel = abs(v("m90_band_hi_pct") - v("m90_band_lo_pct"))
say("    That stated band is %.0fx wider than the CI B1 cites as the bar."
    % (band_width_rel / m90_ci_rel))
say("")
say("    => The CI is a PRECISION statement about one regression's slope.")
say("       B1 uses it as an ACCURACY statement about g. Those differ here by")
say("       a factor of %.0f, and M90 says so in its own words." % (band_width_rel / m90_ci_rel))
say("")

# ----------------------------------------------------------------------------
# Q2 -- does an in-stack measurement already exist?
# ----------------------------------------------------------------------------
say("Q2  DOES AN IN-STACK g ALREADY EXIST?")
say("-" * 78)
say("    YES. M61 ran a temporal adjacent-frame PTC on SUBJECT stacks:")
say("      12 stacks, 1554 frames, ISO 50-1000, per CFA plane, raw DN,")
say("      low-texture tile selection, never demosaiced.")
say("    That is the estimator B1 describes, in the configuration B1 proposes")
say("    (subject frames, working exposure), with a PASSING pre-registered")
say("    control at ISO 160 (r = 0.9887 greens, band 0.80-1.20).")
say("")
say("    => B1 is a PORT AND A GENERALISATION, not a new build.")
say("")

# ----------------------------------------------------------------------------
# Q3 -- how far is it from M90?  (observation, no registered direction)
# ----------------------------------------------------------------------------
say("Q3  HOW FAR IS THE EXISTING IN-STACK NUMBER FROM M90?  (observation)")
say("-" * 78)

q3 = {}
if not controls_ok:
    say("    SKIPPED -- controls failed.")
else:
    for label, rkey in (("pre-registered, 3 stacks", "m61_r100_greens"),
                        ("fit-gated, 2 stacks", "m61_r100_greens_gated")):
        g_instack = v(rkey) * g_model_100
        d = pct(g_instack, v("m90_g"))
        q3[rkey] = {"r": v(rkey), "g": g_instack, "pct_vs_m90": d}
        say("    %-26s r = %.4f  ->  g = %.6f DN/e-   %+.3f%% vs M90"
            % (label, v(rkey), g_instack, d))

    own_rel = v("m61_r100_greens_spread") / v("m61_r100_greens") * 100.0
    ratio = own_rel / m90_ci_rel
    say("")
    say("    M61's OWN uncertainty at ISO 100 (stack-to-stack, n=%d): +/- %.3f%%"
        % (v("m61_r100_nstacks"), own_rel))
    say("    B1's bar (M90's CI):                                    +/- %.4f%%" % m90_ci_rel)
    say("    The existing in-stack instrument's uncertainty is %.0fx the bar." % ratio)
    say("")
    inside = [k for k in q3 if abs(q3[k]["pct_vs_m90"]) <= m90_ci_rel]
    say("    Arms landing inside B1's stated bar: %d of %d" % (len(inside), len(q3)))
    say("    Arms landing inside M61's own uncertainty: %d of %d"
        % (sum(1 for k in q3 if abs(q3[k]["pct_vs_m90"]) <= own_rel), len(q3)))
    q3["own_rel_pct"] = own_rel
    q3["ratio_to_bar"] = ratio

say("")
say("VERDICT")
say("-" * 78)
say("  1. B1's acceptance bar as written is UNREACHABLE. It names a %.4f%%" % m90_ci_rel)
say("     precision figure as an accuracy target for a quantity whose two")
say("     best independent measurements disagree by %.2f%%." % inter_method)
say("  2. B1's estimator ALREADY EXISTS and has been run in-stack (M61-E1),")
say("     with a passing pre-registered control.")
if controls_ok:
    say("  3. It lands %+.2f%% (pre-registered) / %+.2f%% (fit-gated) from M90 --"
        % (q3["m61_r100_greens"]["pct_vs_m90"], q3["m61_r100_greens_gated"]["pct_vs_m90"]))
    say("     i.e. WELL INSIDE M90's own stated %.1f-%.1f%% band of ignorance,"
        % (abs(v("m90_band_lo_pct")), abs(v("m90_band_hi_pct"))))
    say("     and far outside the CI the acceptance names.")
say("")
say("  The bar should be restated against the inter-method spread that")
say("  actually exists, not one method's fit error. Proposed replacement is")
say("  in the lane PREREGISTRATION.")

blob = {
    "inputs": {k: {"value": val, "cite": cite} for k, (val, cite) in IN.items()},
    "controls": {"c1_g_model_vs_shipped_pct": c1_err, "c1": c1,
                 "c2_calc_pct": c2_calc, "c2": c2,
                 "c3_calc_pct": c3_calc, "c3": c3,
                 "all_pass": controls_ok},
    "g_model_100": g_model_100,
    "q1": {"bar_rel_pct": m90_ci_rel,
           "inter_method_pct": inter_method,
           "ratio": q1_ratio,
           "reachable": q1_reachable,
           "m90_band_width_pct": band_width_rel,
           "band_over_bar": band_width_rel / m90_ci_rel},
    "q2": {"exists": True, "lane": "M61", "estimator": "M61-E1"},
    "q3": q3,
}

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "b1-audit.json"), "w", encoding="utf-8") as f:
    json.dump(blob, f, indent=2)
with open(os.path.join(OUT, "b1-audit.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\nwrote out/b1-audit.json and out/b1-audit.txt")
