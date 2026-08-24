"""ORCH: what correction did the CA stage actually apply, versus what was needed?

Reads ca_shift.json (produced by ca_shift.py, whose estimator passed an integer-roll
positive control at 0.045 px accuracy over +/-2 px).

For each ring:
    needed  = -R_off          (the displacement that would have to be undone)
    applied =  R_on - R_off   (the displacement the correction actually introduced)
    gain    =  applied / needed

A correct correction has gain = 1.0 at every radius. A gain that is FLAT in radius but
not 1.0 is a scalar coefficient error. A gain that DRIFTS with radius -- particularly one
that departs beyond the fit's outer support at r = 0.788 -- is a radial-shape or
extrapolation error. These two diagnoses call for completely different fixes, which is
why the distinction is worth measuring rather than assuming.
"""

import json
import os

import numpy as np

OUT = r"C:\dev\strehl-out\ORCH-ca-radial"
SUPPORT_LO, SUPPORT_HI = 0.208, 0.788

with open(os.path.join(OUT, "ca_shift.json")) as fh:
    rows = json.load(fh)

print("=" * 86)
print("APPLIED vs NEEDED lateral-CA correction, red channel")
print("=" * 86)
print("%-7s %-8s %5s %9s %9s %9s %8s %10s"
      % ("r", "support", "n", "needed", "applied", "residual", "gain", "|tan| floor"))

gains, gains_in, gains_out = [], [], []
for w in rows:
    r = w["r"]
    off, on = w["R_off"], w["R_on"]
    needed = -off
    applied = on - off
    if abs(needed) < 1.5 * w["tan_off"]:
        note = "  (needed < 1.5x noise floor -- gain not reported)"
        print("%-7.3f %-8s %5d %9.3f %9.3f %9.3f %8s %10.3f%s"
              % (r, w["side"], w["n"], needed, applied, on, "--", w["tan_off"], note))
        continue
    g = applied / needed
    gains.append(g)
    (gains_in if r <= SUPPORT_HI else gains_out).append(g)
    print("%-7.3f %-8s %5d %9.3f %9.3f %9.3f %8.3f %10.3f"
          % (r, w["side"], w["n"], needed, applied, on, g, w["tan_off"]))

print("=" * 86)
g = np.array(gains)
print("gain over all rings with signal : median %.3f   mean %.3f   min %.3f   max %.3f   n=%d"
      % (np.median(g), g.mean(), g.min(), g.max(), g.size))
if gains_in and gains_out:
    gi, go = np.array(gains_in), np.array(gains_out)
    print("gain INSIDE  support (r<=%.3f) : median %.3f  (n=%d)" % (SUPPORT_HI, np.median(gi), gi.size))
    print("gain OUTSIDE support (r> %.3f) : median %.3f  (n=%d)" % (SUPPORT_HI, np.median(go), go.size))
    print()
    print("HYPOTHESIS UNDER TEST (SYNTHESIS fact 1501): the correction over-extrapolates")
    print("BEYOND its fit support, so the gain should be markedly worse outside r=%.3f." % SUPPORT_HI)
    delta = float(np.median(go) - np.median(gi))
    print("MEASURED: outside - inside = %+.3f in gain." % delta)
    if abs(delta) < 0.15:
        print("VERDICT : REFUTED. The gain error is FLAT in radius, so this is a scalar")
        print("          coefficient error, not an extrapolation error. Extending the fit's")
        print("          radial support would NOT fix it; rescaling the coefficient would.")
    else:
        print("VERDICT : consistent with a radius-dependent error; keep the hypothesis alive.")

print()
print("IMPLIED SINGLE-SCALAR FIX: multiply the red lateral-CA coefficient by %.3f"
      % (1.0 / float(np.median(g))))
resid_now = float(np.median([abs(w["R_on"]) for w in rows if abs(-w["R_off"]) >= 1.5 * w["tan_off"]]))
resid_pred = float(np.median([abs(w["R_off"] * (1.0 - np.median(g) / np.median(g)))
                              for w in rows if abs(-w["R_off"]) >= 1.5 * w["tan_off"]]))
print("  median |residual| now              : %.3f px" % resid_now)
print("  median |residual| if gain were 1.0 : %.3f px (i.e. at the estimator's floor)" % resid_pred)

print()
print("BLUE CHANNEL -- reported separately because it sits at the noise floor:")
print("%-7s %9s %9s %9s %10s" % ("r", "B off", "B on", "applied", "|tan| floor"))
for w in rows:
    print("%-7.3f %9.3f %9.3f %9.3f %10.3f"
          % (w["r"], w["B_off"], w["B_on"], w["B_on"] - w["B_off"], w["tan_off"]))
nb = sum(1 for w in rows if abs(w["B_off"]) >= 1.5 * w["tan_off"])
print("rings where |B_off| clears 1.5x the tangential noise floor: %d of %d" % (nb, len(rows)))
print("=> Any claim about the blue correction's SIGN is not supported by this scene.")
