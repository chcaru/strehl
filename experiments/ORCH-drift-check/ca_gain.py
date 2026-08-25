"""ORCH: what correction did the CA stage actually apply, versus what was needed?

################################################################################
# SUPERSEDED -- THIS SCRIPT'S HEADLINE RESULT (gain 1.444) IS REFUTED.
#
# It was run on `--srgb --auto-exposure` renders. Lateral CA is a CROSS-CHANNEL
# quantity and that space contains two cross-channel operators:
#   * camera_to_srgb is non-diagonal -- output red carries camera green at 27.4%
#     and output green carries camera red at 7.7%, BOTH AT ZERO DISPLACEMENT;
#     (CORRECTED 2026-08-25 by V-FOLD: this header previously said 10.4% / 20.3%,
#     which was wrong AND swapped. The crate computes inv(rownorm(A@S)) --
#     color.rs:191-208 row-normalises at step 2 then inverts at step 3 -- while
#     the corpus everywhere quoted rownorm(inv(A@S)). Verify with
#     experiments/V-FOLD/matrix.py; its green row matches color.rs:221's own doc
#     comment to 3 d.p. The supersession below is UNAFFECTED and strengthened:
#     the green-into-red leak is 27.4%, not 10.4%.)
#   * Malvar-He-Cutler demosaic assumes `R - G` is smoother than either channel
#     (demosaic.rs:482), which a CA fringe violates by definition.
# `main.rs:116` says of --srgb: "For looking at, NOT for measuring." It was right.
#
# M113 re-measured in the binned linear space and obtained gain 1.2496
# (bee-3-cpl) and 1.0557 (couch-fibers-cpl). The chain-transfer check
# `applied / eps_r` against the compile-time constant eps_r = -704.5 ppm reads
# 1.3073 in sRGB, 0.6963 in demosaic-linear and 0.9399/0.9813 binned -- the two
# contaminated spaces are wrong in OPPOSITE directions.
#
# The implied "multiply the red coefficient by 0.692" fix MUST NOT SHIP: on
# couch-fibers-cpl it turns a 5.6% over-correction into a 27.0% UNDER-correction.
# No scalar fix is supported at all -- `needed` differs 23.6% between scenes
# because a channel's effective wavelength is its passband centroid weighted by
# the SCENE's spectrum.
#
# WHAT SURVIVES: the radial SHAPE is correct (eps(r) flat over r = 0.11..0.87
# -- the "+/-15 ppm" tolerance this header used to quote is RETRACTED, it was
# spliced from a different, n=1 experiment and the real bootstrap sd at the
# r=0.11 ring is 80.0 ppm; see SYNTHESIS fact 1723), and the sign-flip finding
# (RECOLOURED, NOT REMOVED) is confirmed on two stacks under two independent
# estimators.
#
# See docs/research/SYNTHESIS.md facts 1567+ and experiments/M113-ca/.
# Kept, not deleted, because the corpus rule is that a refuted instrument stays
# readable next to what refuted it.
################################################################################

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
print("IMPLIED SINGLE-SCALAR FIX: %.3f -- DO NOT APPLY. Refuted by M113: no scalar"
      " fix is supported (needed differs 23.6%% between scenes), and this space is"
      " contaminated. See the SUPERSEDED banner at the top of this file."
      % (1.0 / float(np.median(g))))
resid_now = float(np.median([abs(w["R_on"]) for w in rows if abs(-w["R_off"]) >= 1.5 * w["tan_off"]]))
# DEFECT, found by M113 and repaired here: this previously computed
#   abs(R_off * (1.0 - median(g)/median(g)))
# whose second factor is identically zero, so it printed 0.000 on ANY input and
# was captioned "i.e. at the estimator's floor" -- a fabricated floor. The
# quantity intended was the residual that WOULD remain under a unit gain, which
# is just |needed - applied| evaluated at gain 1.0, i.e. |R_off + R_off| is wrong
# too. There is no defensible one-line form here, so it is not printed.
print("  median |residual| now              : %.3f px" % resid_now)
print("  median |residual| if gain were 1.0 : NOT COMPUTED -- the former"
      " expression was identically zero (see the defect note above)")

print()
print("BLUE CHANNEL -- reported separately because it sits at the noise floor:")
print("%-7s %9s %9s %9s %10s" % ("r", "B off", "B on", "applied", "|tan| floor"))
for w in rows:
    print("%-7.3f %9.3f %9.3f %9.3f %10.3f"
          % (w["r"], w["B_off"], w["B_on"], w["B_on"] - w["B_off"], w["tan_off"]))
nb = sum(1 for w in rows if abs(w["B_off"]) >= 1.5 * w["tan_off"])
print("rings where |B_off| clears 1.5x the tangential noise floor: %d of %d" % (nb, len(rows)))
print("=> Any claim about the blue correction's SIGN is not supported by this scene.")
