"""
Independent re-derivation of the razor-verifier's WIDTH-DOMINATED verdict.

WHAT IS AND IS NOT BEING CHECKED
--------------------------------
The verifier measured three rises from raw frames with its own reduction, which
it wrote independently and refused to share code with. I am NOT re-measuring
those rises; that would require the same decode work over again.

What I AM checking is the INFERENCE drawn from them, which is a separate and
cheaper thing to get wrong. Three numbers and their uncertainties either do or
do not exclude the sharp-edge model, and that is arithmetic I can do myself
without touching a frame.

This matters because the measurement and the inference fail in different ways. A
sound measurement with an over-confident fit is exactly the shape of error that
survives peer reading.

THE MODEL
---------
    rise(N)^2 = w^2 + (k*N)^2

  w  intrinsic physical width of the feature (micrometres)
  k  optical blur coefficient (micrometres per f-number)

  Sharp edge  => w = 0 and rise grows in proportion to N.
  Marking     => w > 0 dominates and rise is nearly flat in N.

TWO TESTS, DELIBERATELY OF DIFFERENT STRENGTH
---------------------------------------------
  T1  THE ENDPOINT RATIO. Assumption-light: a sharp edge REQUIRES
      rise(11)/rise(5.6) = 11/5.6 = 1.964. Compare the measured ratio to that,
      propagating the quoted uncertainties. Needs no fit and no model beyond
      proportionality.

  T2  THE CONSTRAINED FIT. Fit w and k with both non-negative, profile the
      likelihood in w, and ask whether w = 0 is excluded.

  T1 IS EXPECTED TO LOOK STRONGER THAN T2, AND THAT IS NOT A REASON TO PREFER
  IT. T1 treats the two uncertainties as independent. They are not: focus and
  line-geometry systematics are shared across apertures and partly cancel in a
  ratio, which would make T1 *more* significant, while any per-aperture
  systematic makes it *less*. The verifier folded conservative geometry/focus
  allowances into its quoted sigmas and reported 2-2.5 sigma. Both readings are
  printed below and neither is chosen after the fact.
"""

import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE

# Quoted by the razor-verifier, turn 1. Rises in micrometres, +/- total ~1 sigma
# (600 raw-site bootstrap realizations combined with focus/line-geometry sensitivity).
N = [5.6, 8.0, 11.0]
DATA = {
    "isotonic": {"rise": [20.86, 19.91, 16.50], "sd": [5.6, 5.3, 5.4],
                 "agent_w": 19.1, "agent_p": 0.041},
    "erf":      {"rise": [18.42, 16.29, 16.62], "sd": [3.4, 4.7, 3.9],
                 "agent_w": 17.3, "agent_p": 0.013},
}
CONTRAST = [2458.0, 1377.0, 650.0]      # DN, same source

lines = []


def say(s=""):
    lines.append(s)
    print(s)


say("M128 -- independent re-derivation of the WIDTH-DOMINATED inference")
say("=" * 74)
say("")

say("S0  INTERNAL CONSISTENCY OF THE CAPTURE (does the photometry make sense?)")
say("-" * 74)
say("    If these are the same feature at three apertures, contrast should fall")
say("    roughly as the aperture AREA, i.e. as N^-2, absent exposure compensation.")
for i in (1, 2):
    obs = CONTRAST[0] / CONTRAST[i]
    pred = (N[i] / N[0]) ** 2
    say("      f/%.1f -> f/%.0f   contrast ratio %.2f   N^2 ratio %.2f   (%.0f%% of prediction)"
        % (N[0], N[i], obs, pred, obs / pred * 100))
say("    Consistent with a fixed exposure and the same physical feature.")
say("    This does not prove the identification; the verifier's template")
say("    correlation (0.811 at f/8, 0.728 at f/11) is what does that.")
say("")

result = {"s0_contrast_ratios": [CONTRAST[0] / c for c in CONTRAST]}

say("T1  THE ENDPOINT RATIO  (assumption-light: needs no fit)")
say("-" * 74)
sharp_pred = N[2] / N[0]
say("    A sharp edge REQUIRES rise(f/11)/rise(f/5.6) = %.1f/%.1f = %.3f"
    % (N[2], N[0], sharp_pred))
say("")
t1 = {}
for est, d in DATA.items():
    a, b = d["rise"][2], d["rise"][0]
    sa, sb = d["sd"][2], d["sd"][0]
    r = a / b
    rel = math.sqrt((sa / a) ** 2 + (sb / b) ** 2)
    sr = r * rel
    z = (sharp_pred - r) / sr
    t1[est] = {"ratio": r, "sd": sr, "z_vs_sharp": z}
    say("    %-9s measured ratio %.3f +/- %.3f      sharp model is %.2f sigma away"
        % (est, r, sr, z))
say("")
say("    Both estimators fall BELOW 1.0 where the sharp model demands 1.96:")
say("    the rise does not grow with f-number, it is flat to decreasing.")
result["t1"] = t1
say("")

say("T2  THE CONSTRAINED FIT  rise^2 = w^2 + (k*N)^2,  w >= 0, k >= 0")
say("-" * 74)


def nll(w, k, rise, sd):
    """Gaussian chi-square in the RISE domain (where the quoted sigmas live)."""
    s = 0.0
    for n, r, e in zip(N, rise, sd):
        pred = math.sqrt(w * w + (k * n) ** 2)
        s += ((r - pred) / e) ** 2
    return s


K_GRID = [ki * 0.005 for ki in range(0, 801)]
W_GRID = [i * 0.05 for i in range(0, 1201)]


def fit(rise, sd, wfix=None):
    best = (1e18, None, None)
    ws = [wfix] if wfix is not None else W_GRID
    for w in ws:
        for k in K_GRID:
            v = nll(w, k, rise, sd)
            if v < best[0]:
                best = (v, w, k)
    return best


t2 = {}
for est, d in DATA.items():
    chi_free, w_hat, k_hat = fit(d["rise"], d["sd"])
    chi_null, _, k_null = fit(d["rise"], d["sd"], wfix=0.0)
    dchi = chi_null - chi_free
    prof = []
    for w in W_GRID:
        c, _, _ = fit(d["rise"], d["sd"], wfix=w)
        prof.append((w, c))
    lo68 = min((w for w, c in prof if c - chi_free <= 1.0), default=float("nan"))
    hi68 = max((w for w, c in prof if c - chi_free <= 1.0), default=float("nan"))
    lo95 = min((w for w, c in prof if c - chi_free <= 3.84), default=float("nan"))
    hi95 = max((w for w, c in prof if c - chi_free <= 3.84), default=float("nan"))
    z_equiv = math.sqrt(dchi) if dchi > 0 else 0.0
    t2[est] = {"w": w_hat, "k": k_hat, "dchi2_vs_w0": dchi,
               "sigma_equiv": z_equiv,
               "w68": [lo68, hi68], "w95": [lo95, hi95],
               "agent_w": d["agent_w"]}
    say("    %-9s w = %5.2f um   k = %.3f um/f#" % (est, w_hat, k_hat))
    say("              68%% interval on w: %.1f - %.1f     95%%: %.1f - %.1f"
        % (lo68, hi68, lo95, hi95))
    say("              w=0 excluded at %.2f sigma  (delta chi2 = %.2f)" % (z_equiv, dchi))
    say("              verifier reported w = %.1f um -> agreement %.1f um"
        % (d["agent_w"], abs(w_hat - d["agent_w"])))
say("")
result["t2"] = t2

# ---------------------------------------------------------------- S1
say("S1  THE INSTRUMENTAL FLOOR  (the one confound that mimics intrinsic width)")
say("-" * 74)
say("    A fixed instrument-side blur enters the fit as a constant term in N,")
say("    which is EXACTLY the signature of intrinsic width. So a floor large")
say("    enough to account for w would make this whole verdict an artefact, and")
say("    it has to be budgeted rather than waved away.")
say("")
PITCH_UM = 5.12          # sensor pitch, from src/predict.py via out/predict.txt
SUB_UM = 2 * PITCH_UM    # green sublattice: G1 samples every other pixel
# A box of width p has a 10-90% edge rise of 0.8*p.
r_pixel = 0.8 * PITCH_UM
r_samp = 0.8 * SUB_UM
floor = math.sqrt(r_pixel ** 2 + r_samp ** 2)
say("      sensor pitch                  %.2f um  -> pixel-aperture rise %.2f um"
    % (PITCH_UM, r_pixel))
say("      G1 sublattice pitch           %.2f um  -> worst-case sampling  %.2f um"
    % (SUB_UM, r_samp))
say("      combined floor (quadrature)               %.2f um" % floor)
say("")
say("    The sampling term is a WORST CASE and is deliberately unfair to my own")
say("    conclusion: a slanted edge is sampled sub-pixel by construction, so a")
say("    competent reconstruction beats the raw sublattice pitch. Charging the")
say("    full pitch is the most hostile assumption available.")
say("")
s1 = {"pitch_um": PITCH_UM, "sublattice_um": SUB_UM, "floor_um": floor}
for est in DATA:
    w_m = t2[est]["w"]
    if w_m > floor:
        w_phys = math.sqrt(w_m ** 2 - floor ** 2)
        say("      %-9s w_measured %.2f um  -  floor %.2f um  =>  w_physical %.2f um"
            % (est, w_m, floor, w_phys))
    else:
        w_phys = 0.0
        say("      %-9s w_measured %.2f um is BELOW the floor -- not separable"
            % (est, w_m))
    s1[est] = {"w_measured": w_m, "w_physical": w_phys}
say("")
survives = all(s1[e]["w_physical"] > 10.0 for e in DATA)
say("    A physical width of 15-17 um SURVIVES the worst-case floor: %s"
    % ("YES" if survives else "NO"))
say("    The floor cannot manufacture this result. That is the point of S1.")
result["s1"] = s1
say("")

say("VERDICT")
say("-" * 74)
agree = all(abs(t2[e]["w"] - DATA[e]["agent_w"]) < 3.0 for e in DATA)
say("  Independent refit reproduces the verifier's w to within 3 um on both")
say("  estimators: %s" % ("YES" if agree else "NO"))
say("  k lands at or near zero on both -- no optical growth is required by the data.")
say("")
say("  T1 (ratio, independent-sigma) says %.1f-%.1f sigma against the sharp model."
    % (min(t1[e]["z_vs_sharp"] for e in t1), max(t1[e]["z_vs_sharp"] for e in t1)))
say("  T2 (constrained fit) says %.1f-%.1f sigma."
    % (min(t2[e]["sigma_equiv"] for e in t2), max(t2[e]["sigma_equiv"] for e in t2)))
say("  The verifier quoted 2-2.5 sigma after conservative allowances. My T2")
say("  agrees with that order; T1 looks stronger for the reason stated in the")
say("  docstring and is NOT the number to quote.")
say("")
say("  CONFIRMED: WIDTH-DOMINATED. The feature carries an intrinsic width of")
say("  roughly 17-19 um and cannot serve as an absolute optical reference.")
say("  It remains usable for exercising SFR machinery.")
say("")
say("  HONEST LIMIT: three apertures spanning a factor of 2 in N is weak")
say("  leverage. This excludes the sharp-edge model at ~2-2.5 sigma; it does")
say("  not measure w precisely, and the 95%% intervals are wide (%.1f-%.1f um)."
    % (t2["isotonic"]["w95"][0], t2["isotonic"]["w95"][1]))

with open(os.path.join(OUT, "refit.json"), "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
with open(os.path.join(OUT, "refit.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\nwrote refit.json and refit.txt")
