"""
M-PHASE0-QUINCUNX step 2: an UNREGISTERED constraint on the bellows factor B.

STATUS: UNREGISTERED. I did not predict this before looking at the data. It fell
out of step 1's cutoff table once the empirical null was in place. It is written
as its own file, and labelled, so that it cannot be mistaken for one of the
lane's pre-registered results. Treat it as a lead with a number attached, not as
a settled measurement.

THE OPPORTUNITY
---------------
M129 has never settled the bellows factor B = N_eff/N. It carries three
hypotheses -- H1 3.732, H2 3.076, H3 2.402 -- and its own aperture trend remains
unexplained. Step 1 produced something M129 did not have: a per-aperture
statement of whether ANY scene energy reaches past 0.26 sensor cyc/px, scored
against a measured null rather than a chosen bar.

That is a cutoff detector. Diffraction transmits nothing above
f_c = PITCH_UM / (lambda * B * N). If energy is detected at one aperture and not
at the next, the cutoff crossed the band's lower edge between them, which
brackets B from BOTH sides:

    detected at f/14  =>  f_c(14.254) > 0.26  =>  B < PITCH/(lambda*14.254*0.26)
    absent   at f/18  =>  f_c(17.959) < 0.26  =>  B > PITCH/(lambda*17.959*0.26)

The bracket needs no fit, no model of the subject, and no assumption about MTF
shape below cutoff. It uses only the location of the cutoff itself.

WHAT WOULD MAKE THIS WRONG
--------------------------
  * A hard cutoff is an idealisation. A real MTF approaches zero smoothly, so
    "undetected" happens slightly BELOW the true cutoff, not exactly at it. This
    biases the upper bound on B downward and the lower bound downward too -- the
    bracket slides, it does not widen symmetrically. C8 states the direction.
  * Detection depends on SNR, and the noise floor moves 38x across this ladder.
    If f/18 were merely too noisy to detect a real signal, the lower bound would
    be wrong. C7 tests this directly: f/18 has the LOWEST floor of the five, so
    it is the most sensitive cell, not the least.
  * lambda carries a stated +-50 nm systematic in m5_lib. B scales as 1/lambda.
    C9 recomputes the bracket at both extremes and asks whether the exclusions
    survive.

CONTROLS
--------
  C6  The detection boundary is where step 1 says it is: f/14 detected, f/18 not,
      both judged against step 1's measured threshold. Re-read from the JSON, not
      restated here.
  C7  f/18 is not merely the noisiest cell. Its floor must be the LOWEST of the
      five apertures, so its null cannot be explained by lost sensitivity.
  C8  Direction of the idealisation bias, stated explicitly.
  C9  lambda sensitivity: recompute at 0.500 and 0.600 um and report which
      hypotheses survive at both extremes.
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")

PITCH_UM = 5.12
LAMBDA_UM = 0.550
EXACT_N = {"f5.6": 2 ** 2.5, "f8": 8.0, "f11": 2 ** 3.5,
           "f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}
B_HYP = {"H1": 3.732, "H2": 3.076, "H3": 2.402}

with open(os.path.join(OUT, "q1-band.json"), encoding="utf-8") as fh:
    S1 = json.load(fh)

lines = []
res = {}


def say(s=""):
    lines.append(s)
    print(s)


say("M-PHASE0-QUINCUNX step 2 -- UNREGISTERED constraint on B")
say("=" * 74)
say("reads out/q1-band.json; measures nothing new")
say("")

BAND_LO = 0.26
det = S1["detections"]
q2 = S1["q2"]

# ------------------------------------------------------------------------ C6
say("C6  the detection boundary, re-read from step 1's JSON")
say("-" * 74)
say("    threshold %.4f (|null mean| + 3 sd)" % S1["c5_null"]["threshold"])
for t in ["f5.6", "f8", "f11", "f14", "f18"]:
    say("      %-6s %d/%d detected   median %+.4f" %
        (t, det[t]["n_detected"], det[t]["n"], det[t]["median"]))
c6_ok = det["f14"]["n_detected"] > 0 and det["f18"]["n_detected"] == 0
say("    boundary sits between f/14 (detected) and f/18 (not): %s"
    % ("PASS" if c6_ok else "FAIL"))
say("")

# ------------------------------------------------------------------------ C7
say("C7  f/18's null is not a sensitivity failure")
say("-" * 74)
floors = {t: q2[t]["median_floor"] for t in q2}
lo_ap = min(floors, key=lambda k: floors[k])
c7_ok = lo_ap == "f18"
for t in ["f5.6", "f8", "f11", "f14", "f18"]:
    say("      %-6s median noise floor %10.1f" % (t, floors[t]))
say("    lowest floor is %s -> %s" % (lo_ap, "PASS" if c7_ok else "FAIL"))
say("    f/18 is the most sensitive cell in the ladder, so its null cannot be")
say("    explained by lost sensitivity. It is an absence of signal.")
say("")

# --------------------------------------------------------------- the bracket
say("THE BRACKET")
say("-" * 74)


def b_from(n, f_edge, lam):
    return PITCH_UM / (lam * n * f_edge)


def bracket(lam):
    hi = b_from(EXACT_N["f14"], BAND_LO, lam)   # detected  -> B below this
    lo = b_from(EXACT_N["f18"], BAND_LO, lam)   # absent    -> B above this
    return lo, hi


lo, hi = bracket(LAMBDA_UM)
say("    at lambda = %.3f um:  %.4f < B < %.4f" % (LAMBDA_UM, lo, hi))
say("")
say("    %-4s %8s   %s" % ("hyp", "B", "inside bracket?"))
inside = {}
for h, b in B_HYP.items():
    ok = lo < b < hi
    inside[h] = ok
    say("    %-4s %8.3f   %s" % (h, b, "YES" if ok else "no -- EXCLUDED"))
res["bracket"] = {"lambda": LAMBDA_UM, "lo": lo, "hi": hi, "inside": inside}
say("")

# ------------------------------------------------------------------------ C9
say("C9  lambda sensitivity (+-50 nm, per m5_lib)")
say("-" * 74)
surv = {h: [] for h in B_HYP}
per_lambda = {}
for lam in (0.500, 0.550, 0.600):
    l2, h2 = bracket(lam)
    tags = []
    for h, b in B_HYP.items():
        ok = l2 < b < h2
        surv[h].append(ok)
        if ok:
            tags.append(h)
    per_lambda["%.3f" % lam] = {"lo": l2, "hi": h2, "inside": tags}
    say("    lambda %.3f um -> %.4f < B < %.4f   inside: %s"
        % (lam, l2, h2, ", ".join(tags) if tags else "none"))
always = [h for h in B_HYP if all(surv[h])]
never = [h for h in B_HYP if not any(surv[h])]
say("")
say("    inside at EVERY lambda: %s" % (", ".join(always) if always else "none"))
say("    excluded at EVERY lambda: %s" % (", ".join(never) if never else "none"))
c9_ok = len(never) > 0
res["lambda_sensitivity"] = {"always_inside": always, "always_excluded": never,
                             "per_lambda": per_lambda}
say("")

# ------------------------------------------------------------------------ C8
say("C8  direction of the hard-cutoff idealisation, stated not assumed")
say("-" * 74)
say("    A real MTF decays to zero rather than stepping. Energy just below the")
say("    true cutoff is therefore attenuated and may go undetected, so the")
say("    aperture that reads null has a true cutoff slightly ABOVE the band")
say("    edge, not at it. f_c is proportional to 1/B, so the true B is slightly")
say("    SMALLER than the lower bound derived above. Both bounds move the same")
say("    way, and the effect pushes AWAY from H1 and H2, never toward them.")
say("    The exclusion is therefore conservative; the inclusion of H3 is not.")
say("")

# ----------------------------------------------------------------------- C10
say("C10  the single load-bearing point")
say("-" * 74)
say("    The UPPER bound on B comes entirely from f/14 being a detection. If")
say("    f/14 were actually null, only B > %.3f would survive and H1 and H2" % lo)
say("    would NOT be excluded. The whole exclusion rests on one aperture, so")
say("    it is worth stating how firm that one aperture is.")
say("")
nm, nsd = S1["c5_null"]["mean"], S1["c5_null"]["sd"]
z14 = (det["f14"]["median"] - nm) / nsd
c10_ok = z14 > 5.0
say("      f/14 median SNR      %+.4f" % det["f14"]["median"])
say("      f/18 null mean, sd   %+.4f, %.4f" % (nm, nsd))
say("      f/14 stands %.1f null sd above the null mean -> %s"
    % (z14, "PASS" if c10_ok else "FAIL"))
say("      its noise floor (%.1f) is within %.0f%% of f/18's (%.1f), so the null"
    % (floors["f14"], abs(floors["f14"] / floors["f18"] - 1) * 100, floors["f18"]))
say("      scale measured at f/18 is the right scale to judge f/14 by.")
res["c10_f14_z"] = z14
say("")

# --------------------------------------------------------------------- verdict
say("VERDICT (unregistered)")
say("-" * 74)
allc = c6_ok and c7_ok and c9_ok and c10_ok
say("  controls: C6 %s  C7 %s  C9 %s  C10 %s"
    % (*("PASS" if x else "FAIL" for x in (c6_ok, c7_ok, c9_ok, c10_ok)),))
say("")
say("  The super-plane-Nyquist detection boundary brackets B to")
say("  %.3f - %.3f at lambda %.3f um." % (lo, hi, LAMBDA_UM))
say("")
say("  ROBUST: H1 (%.3f) and H2 (%.3f) are excluded at every lambda across the"
    % (B_HYP["H1"], B_HYP["H2"]))
say("  stated +-50 nm systematic, and C8's idealisation bias pushes further")
say("  away from them rather than toward them.")
say("")
say("  NOT ROBUST: H3 (%.3f) is inside only for lambda up to about 0.57 um."
    % B_HYP["H3"])
say("  At 0.600 um the bracket is %.3f - %.3f and H3 sits just outside it."
    % bracket(0.600))
say("  So this evidence does NOT elect H3. It says B lies near 2.0-2.8, which")
say("  is H3's neighbourhood and nobody else's.")
say("")
say("  This is an independent line of evidence on a question M129 left open,")
say("  from data M129 itself produced. It is NOT a substitute for M129's own")
say("  ladder: it is one bracket from one subject, it assumes a hard cutoff,")
say("  it rests on a single aperture's detection, and it was found after the")
say("  fact. It should be pre-registered and re-run on a second subject before")
say("  it is allowed to settle anything.")
res["controls_all_pass"] = allc

with open(os.path.join(OUT, "q2-bhyp.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=2)
with open(os.path.join(OUT, "q2-bhyp.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("\nwrote out/q2-bhyp.json and out/q2-bhyp.txt")
sys.exit(0 if allc else 1)
