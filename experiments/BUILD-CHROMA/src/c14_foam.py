"""ORCH's foam ask: can my axial instrument add a fourth reading, and does my dB
radial term predict the edge colour they measured?

Three questions were asked and they get three separate answers, because two of
them can be answered even though the first one fails.

1. RUN MY INSTRUMENT ON foam. It declines. Reported here with the reason and
   with the comparison against the stacks where it worked, because "no result"
   and "the subject defeats the method" are different claims.

2. DOES MY dB RADIAL TERM PREDICT THEIR CORNER EDGE COLOUR? This is answerable
   from what I already measured, and it is the useful half. The chain is:
   radial component of dB -> fraction of one measured axial dose -> edge chroma,
   using the DOSE-RESPONSE I measured directly in section 5 rather than a
   blur-to-edge-colour formula I would have to invent.

   I ran the naive route too and it disagreed by two orders of magnitude. The
   naive route is wrong and the reason is worth recording: it assumes edge
   chroma is produced BY the channel blur, when section 5's forward arm measured
   that a full sigma=0.369 px blue blur moves the edge chroma statistic by only
   ~1.6%. Edge chroma is dominated by sources that are not axial CA. Any
   arithmetic that ignores that overestimates.

3. IS THERE A DULLER EXPLANATION IN MY OWN LANE? Yes, and it needs no axial term
   at all. eps_b is 4.04x smaller than eps_r by construction, so blue's
   correction is small at the corner and most of blue's native edge colour
   survives it. A radially elevated blue residual after correction is the
   EXPECTED result of the shipped profile, not evidence of anything new.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2_analyse as b2
from common import dump

# Section 5, table 5.2: the dose-response arms. bg_sd is the blue-green edge
# chroma amplitude, which is the closest statistic I have to ORCH's |B-G|.
BG_MERGE, BG_FWD1, BG_FWD10 = 0.0773, 0.0761, 0.0871

# Section 4.4: the radial component of dB, centre->corner, and the intercepts.
RADIAL_FRAMES = (0.25, 0.34)
INTERCEPTS = (0.48, 0.30)

# Shipped coefficients and the corner radius, in plane px.
EPS_R, EPS_B, CORNER_R = 704.5e-6, 174.4e-6, 2112.0

# ORCH's foam measurement, quoted for comparison only -- NOT re-derived.
ORCH_B_CENTRE, ORCH_B_CORNER = 0.0672, 0.1262
ORCH_B_CORNER_RATIO, ORCH_R_CORNER_RATIO = 0.988, 0.758


def q1_decline():
    print("=" * 94)
    print("Q1. CAN MY INSTRUMENT MEASURE foam?   -- NO, and the gate is the reason")
    print("=" * 94)
    print(f"{'stack':>18} {'tiles<=2px':>11} {'track_res med':>14} {'max':>7} {'confident pts':>14}")
    rows = []
    for s in ("foam", "lavendar-cpl", "coffee-bean", "bee-2-cpl", "couch-fibers-cpl"):
        z = b2.load(s)
        tr = z["track_res"]
        res, nt, npt = b2.peaks(z)
        conf = b2.gate(res, 1.5, np.repeat(tr <= 2.0, npt))
        rows.append({"stack": s, "tiles_ok": int((tr <= 2.0).sum()), "tiles": len(tr),
                     "med": float(np.median(tr)), "max": float(tr.max()),
                     "conf": int(conf.sum())})
        mark = "   <- DECLINED" if conf.sum() == 0 else ""
        print(f"{s:>18} {int((tr <= 2.0).sum()):5d}/{len(tr):<5d} "
              f"{np.median(tr):14.2f} {tr.max():7.2f} {int(conf.sum()):14d}{mark}")
    print()
    print("  Not drift. On coffee-bean the per-tile frame shifts are mostly exactly")
    print("  zero with rare outliers; on foam EVERY tile-frame shift is a large")
    print("  random value with no structure. Foam's self-similar bubble texture")
    print("  gives the per-tile matcher no unique correlation peak, so it locks a")
    print("  different match each frame.")
    print()
    print("  I did NOT loosen the gate to produce a number. A randomly-tracked tile")
    print("  still has a maximum along the frame axis, and a parabola fitted to it")
    print("  returns a confident-looking offset computed from different scene")
    print("  content in every frame. That is precisely the 'instrument reports a")
    print("  confident per-channel offset where there is none' failure the original")
    print("  brief made a mandatory negative control. The gate firing IS that")
    print("  control working.")
    return rows


def q2_magnitude():
    print()
    print("=" * 94)
    print("Q2. DOES MY dB RADIAL TERM PREDICT ORCH'S CORNER EDGE COLOUR?")
    print("=" * 94)
    # Dose-response measured in section 5: 1x -> 10x is nine further doses.
    per_dose = (BG_FWD10 - BG_FWD1) / BG_FWD1 / 9.0
    print(f"  section 5 dose-response, measured, not modelled:")
    print(f"    bg_sd  1x dose {BG_FWD1:.4f}   10x dose {BG_FWD10:.4f}")
    print(f"    -> one FULL dose of measured axial offset moves edge chroma by "
          f"{per_dose * 100:.2f}%")
    print()
    lo_f = RADIAL_FRAMES[0] / (INTERCEPTS[0] + RADIAL_FRAMES[0])
    hi_f = RADIAL_FRAMES[1] / (INTERCEPTS[1] + RADIAL_FRAMES[1])
    print(f"  section 4.4: the RADIAL part of dB is {RADIAL_FRAMES[0]}-{RADIAL_FRAMES[1]} frames "
          f"on intercepts of {INTERCEPTS[0]}/{INTERCEPTS[1]},")
    print(f"    so the radial part is {lo_f:.2f}-{hi_f:.2f} of one full dose.")
    print()
    pred_lo, pred_hi = lo_f * per_dose * 100, hi_f * per_dose * 100
    obs_rel = (ORCH_B_CORNER - ORCH_B_CENTRE) / ORCH_B_CENTRE * 100
    print(f"  PREDICTED centre->corner blue edge-colour elevation : "
          f"{pred_lo:.2f}% to {pred_hi:.2f}%")
    print(f"  ORCH OBSERVED                                       : {obs_rel:.1f}%  "
          f"({ORCH_B_CENTRE:.4f} -> {ORCH_B_CORNER:.4f})")
    print(f"  RATIO observed/predicted                            : "
          f"{obs_rel / pred_hi:.0f}x to {obs_rel / pred_lo:.0f}x")
    print()
    print("  My axial radial term is two orders of magnitude too small. It cannot")
    print("  be the mechanism behind their corner blue, and the agreement in")
    print("  DIRECTION carries no weight against a magnitude gap this size --")
    print("  a two-sided quantity agrees in direction half the time by chance.")
    return {"per_dose_pct": per_dose * 100, "pred_lo": pred_lo, "pred_hi": pred_hi,
            "observed_pct": obs_rel}


def q3_duller():
    print()
    print("=" * 94)
    print("Q3. THE DULLER EXPLANATION, ENTIRELY INSIDE MY OWN LANE")
    print("=" * 94)
    dr, db = EPS_R * CORNER_R, EPS_B * CORNER_R
    print(f"  corner displacement the correction applies:")
    print(f"    red  {EPS_R * 1e6:6.1f} ppm x {CORNER_R:.0f} px = {dr:.3f} px")
    print(f"    blue {EPS_B * 1e6:6.1f} ppm x {CORNER_R:.0f} px = {db:.3f} px")
    print(f"    red/blue = {dr / db:.2f}x")
    print()
    print(f"  ORCH observed at the corner: red {ORCH_R_CORNER_RATIO:.3f}x "
          f"({(1 - ORCH_R_CORNER_RATIO) * 100:.1f}% of edge colour removed),")
    print(f"                               blue {ORCH_B_CORNER_RATIO:.3f}x "
          f"({(1 - ORCH_B_CORNER_RATIO) * 100:.1f}% removed).")
    print()
    print("  Their observation 1 is not a puzzle and needs no axial explanation.")
    print("  Blue's correction is 4x smaller than red's BY CONSTRUCTION, because")
    print("  eps_b is 4x smaller. A correction that small removes little edge")
    print("  colour, so most of blue's native radial edge colour survives it --")
    print("  which is exactly their observation 2, a radially elevated blue")
    print("  residual AFTER correction, with no axial term anywhere in the story.")
    return {"corner_disp_r": dr, "corner_disp_b": db, "ratio": dr / db}


def main():
    rows = q1_decline()
    q2 = q2_magnitude()
    q3 = q3_duller()
    print()
    print("=" * 94)
    print("VERDICT: NOT CORROBORATING. Record it as retired, not as a fourth reading.")
    print("=" * 94)
    dump("c14_foam", {"decline": rows, "magnitude": q2, "lateral": q3})


if __name__ == "__main__":
    main()
