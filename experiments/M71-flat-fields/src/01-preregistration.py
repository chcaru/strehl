"""M71 pre-registration. Committed BEFORE any pixel of the delivered data is read.

Rule 20 / discipline 250: for every gate below, the input that would make it
FAIL is written down, and such an input is confirmed to be reachable. Rule 22:
every criterion names the statistic, the threshold, and the consequence of
failure. M65 voided its own headline when a pre-registered criterion failed and
M68 withdrew a number for the same reason; that is the standard this file is
written to.

This script reads NOTHING. It emits `data/01-preregistration.json` so that the
later scripts consume the thresholds rather than restating them, which is the
only mechanism that stops a threshold being edited to fit a result.

Provenance of the numbers this file is scored against, all read from the
repository at the time of writing and not re-derived here:

  crates/strehl-core/src/profile.rs  A7C2: gain_divisor = 436.8,
                                     base_iso = 100.0, read_noise_e_low = 4.20
  => at the ISO 100 of this capture, g = 100/436.8 = 0.2289377 DN/e-,
     sigma(0) = 4.20 * g = 0.961538 DN, floor variance = 0.924556 DN^2
  crates/strehl-core/src/noise.rs    sigma^2(S) = g*S + (RN_e*g)^2, no PRNU term
  AGENTS.md reference rig            black 512, white 15360, active 7032x4688
  fact 585                           a measured PTC at ISO 160 gave 0.3273
                                     against the relation's 0.3663, -10.7%,
                                     and that discrepancy was licensed to stand
  fact 230 (M29, amended M31-V)      PRNU bounded at <= 0.26% by a different route
  M68                                G2/G1 alpha ratio null 0.99937 +- 0.00511
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "data" / "01-preregistration.json"

GAIN_DIVISOR = 436.8
ISO = 100.0
G_DN_PER_E = ISO / GAIN_DIVISOR          # 0.2289377
READ_NOISE_E = 4.20
BLACK = 512
WHITE = 15360                            # AGENTS.md rig section, not 16383
MIDTONE = 8000.0                         # captures-needed.md sec 4: "mid-tone 8,000-12,000 DN"

# Materiality: kappa enters the model iff it inflates SIGMA by >= 5% at the
# mid-tone the corpus's own dust spec names. sigma inflation of 5% is 10.25% in
# variance, so the threshold on kappa is sqrt(0.1025 * g / S).
SIGMA_INFLATION_GATE = 0.05
KAPPA_MATERIAL = ((1.0 + SIGMA_INFLATION_GATE) ** 2 - 1.0) * G_DN_PER_E / MIDTONE
KAPPA_MATERIAL = KAPPA_MATERIAL ** 0.5

CRITERIA = [
    {
        "id": "PR-1a",
        "name": "CPL split from capture time",
        "claim": "Within each of the 9 shutter-speed groups, ordered by "
                 "SubSecDateTimeOriginal, there is exactly one interior gap "
                 "greater than 10x the group median gap, and it falls after "
                 "index 19 -- i.e. 20 frames, an intermission, 20 frames.",
        "statistic": "max interior inter-frame gap / median inter-frame gap, "
                     "and the index it falls after",
        "threshold": "ratio >= 10 and index == 19, in all 9 of 9 groups",
        "fail_input_exists": "A group shot straight through would give ratio "
                             "~1. A 25/15 split would give index 24. Both are "
                             "inside the estimator's range.",
        "consequence": "If it fails in any group the split is not recoverable "
                       "from time alone and the milestone STOPS and reports.",
        "status_at_write_time": "ALREADY RUN on metadata only, in 00-exif-census.py. "
                                "MET 9/9: gaps 277.4-284.5 s against medians "
                                "1.003-1.061 s (ratio 262-283x), index 19 every time.",
    },
    {
        "id": "PR-1b",
        "name": "CPL split cross-checked against signal level",
        "claim": "The first 20 frames of every group are the CPL-on half, so "
                 "they are darker than the last 20 at matched shutter speed by "
                 "the 1.5-2 stops a circular polariser costs.",
        "statistic": "R_k = mean(black-subtracted G1 spatial mean, frames 0..19) "
                     "/ mean(same, frames 20..39), per exposure group k",
        "threshold": "R_k < 1 in ALL 9 groups without exception, and "
                     "0.20 <= R_k <= 0.45 (1.15 to 2.32 stops) in every group "
                     "where neither half has a clipped pixel fraction > 0.01%",
        "fail_input_exists": "If the owner shot no-CPL first, R_k > 1. If the "
                             "level difference were illumination drift rather "
                             "than the filter, R_k would be within a few "
                             "percent of 1. Both are reachable numbers.",
        "consequence": "Brief instruction is explicit: if time-ordering and "
                       "signal level disagree, STOP AND REPORT. No CPL-split "
                       "analysis is run.",
    },
    {
        "id": "PR-2a",
        "name": "Focus state of the 360 flats",
        "claim": "EXIF says FocusDistance2 = inf and FocusPosition2 = 255 for "
                 "all 360 flats, against 0.2707-0.2771 m and 56-58 for the two "
                 "sweeps. PREDICTION, registered before pixels: the flats were "
                 "shot racked to infinity with the paper at 0.28 m, so their "
                 "resolved paper texture is BELOW the least-focused frame of "
                 "either sweep.",
        "statistic": "X(frame) = cov(r_G1, r_G2) on a single frame, where "
                     "r_P = P / gaussian_blur(P, sigma_s) - 1. Shot noise and "
                     "PRNU are independent between G1 and G2, so X estimates "
                     "the COMMON optical structure alone.",
        "threshold": "X(flats, 1/5 s) < min over the 62 frames of BOTH sweeps",
        "fail_input_exists": "If the flats were in focus, X(flat) would land at "
                             "or near the sweep maximum. If FocusPosition2=255 "
                             "were a meaningless sentinel and focus was "
                             "unchanged, X(flat) would land inside the sweep range.",
        "consequence": "If it fails, the paper-texture confound is live in the "
                       "flats and every kappa from them is reported as an UPPER "
                       "BOUND, explicitly labelled, not as a measurement.",
    },
    {
        "id": "PR-2b",
        "name": "The defocus lever has range",
        "claim": "The sweeps genuinely span focus, so they can calibrate how "
                 "much paper texture defocus removes.",
        "statistic": "max(X) / min(X) over the 62 frames of a sweep",
        "threshold": ">= 10x",
        "fail_input_exists": "A sweep that never reached focus would give ~1x.",
        "consequence": "If it fails the defocus lever is dead and the spectral "
                       "lever must carry the separation alone; say so.",
    },
    {
        "id": "PR-3a",
        "name": "PTC reproduces the shipped gain",
        "claim": "A temporal photon-transfer curve on 9 levels spanning 50x at "
                 "fixed ISO 100 reproduces profile.rs's g = 0.2289377 DN/e-.",
        "statistic": "slope a of a weighted least-squares fit of "
                     "V(S) = a*S + b, where V is the mean over unmasked pixels "
                     "of the per-pixel temporal variance across the 20 frames "
                     "of a group, each frame first divided by its own spatial "
                     "mean (mandatory drift normalisation), and S is the "
                     "black-subtracted spatial mean of the temporal mean map",
        "threshold": "|a / 0.2289377 - 1| <= 0.10 for the claim 'this PTC "
                     "reproduces the shipped model' to be made at all. 10% is "
                     "the corpus's own tolerance: fact 585 licensed a -10.7% "
                     "PTC-vs-relation discrepancy at ISO 160 to stand.",
        "fail_input_exists": "Fact 585's own -10.7% is outside this band, so a "
                             "failing value is not merely reachable, it has "
                             "already been observed once on this camera.",
        "consequence": "Failure is REPORTED AS A CONTRADICTION with the "
                       "profile, not reinterpreted. No reproduction is claimed.",
    },
    {
        "id": "PR-3b",
        "name": "Two-greens null on the PTC",
        "claim": "G1 and G2 are two independent photosite populations under the "
                 "same optical field, so their fitted gains must agree.",
        "statistic": "a(G2) / a(G1), with its standard error from the fit",
        "threshold": "within 3 standard errors of 1.000. M68's precedent value "
                     "for the analogous null is 0.99937 +- 0.00511.",
        "fail_input_exists": "A plane-indexing bug, a CFA phase error, or a "
                             "row/column artefact would all move this off 1.",
        "consequence": "If it fails the estimator is broken, not the sensor. "
                       "Everything downstream of it is withdrawn.",
    },
    {
        "id": "PR-3c",
        "name": "The temporal PTC must NOT be quadratic",
        "claim": "Per-pixel TEMPORAL variance cannot contain PRNU or paper "
                 "texture, because both are fixed across the 20 frames. So a "
                 "quadratic term in the temporal PTC is not PRNU -- it is "
                 "residual illumination instability, and it contaminates a.",
        "statistic": "c from V = a*S + b + c*S^2, and sqrt(c) as an equivalent "
                     "relative sigma",
        "threshold": "sqrt(c) consistent with zero at 3 sigma. If not, report "
                     "sqrt(c) as the residual drift amplitude and refit a with "
                     "the quadratic term present.",
        "fail_input_exists": "9 minutes of Seattle overcast with moving cloud "
                             "is exactly the condition that produces c > 0; the "
                             "owner flagged it himself.",
        "consequence": "Reported either way. A clean null is a stated result.",
    },
    {
        "id": "PR-4a",
        "name": "kappa is multiplicative",
        "claim": "PRNU is a gain non-uniformity, so the ABSOLUTE fixed-pattern "
                 "sd must scale linearly with signal. This is the defining "
                 "signature and it separates PRNU from additive offset FPN.",
        "statistic": "exponent q of a power-law fit sd_fixed(S) = A * S^q over "
                     "the exposure levels of one CPL state",
        "threshold": "q = 1.00 +- 0.05",
        "fail_input_exists": "Offset FPN gives q = 0. A mixture gives q "
                             "between. Both reachable.",
        "consequence": "If q is not 1, (kappa*S)^2 is the WRONG FUNCTIONAL FORM "
                       "and the ruling says so rather than reporting a kappa.",
    },
    {
        "id": "PR-4b",
        "name": "kappa is sensor-fixed and repeats",
        "claim": "The PRNU map recovered from the CPL-on half must reproduce "
                 "the map from the CPL-off half: different time, different "
                 "filter, same sensor.",
        "statistic": "Pearson rho between the two recovered per-pixel PRNU maps, "
                     "computed on the highest unclipped common exposure",
        "threshold": "rho >= 0.5",
        "fail_input_exists": "A pattern that is really paper texture would still "
                             "repeat (the paper did not move), so this is a "
                             "NECESSARY not sufficient test and is labelled so. "
                             "A pattern that is really residual noise would give "
                             "rho ~ 0, which is reachable at these amplitudes.",
        "consequence": "If it fails there is no fixed pattern to model and "
                       "kappa is reported as an upper bound at the noise floor.",
    },
    {
        "id": "PR-4c",
        "name": "kappa is invariant under defocus -- THE DECISIVE ONE",
        "claim": "Defocus destroys paper texture and leaves sensor PRNU "
                 "untouched. So the cross-plane-separated PRNU must be the SAME "
                 "at the sweep's in-focus frames and at its most defocused "
                 "frames, while the common optical term C moves by >= 10x.",
        "statistic": "P = var(r_G1) - cov(r_G1, r_G2) - noise, per sweep frame; "
                     "and C = cov(r_G1, r_G2), per sweep frame",
        "threshold": "max(C)/min(C) >= 10 across the sweep AND "
                     "P at the sharpest frame within +-25% of P at the "
                     "most defocused frame",
        "fail_input_exists": "If the estimator were actually measuring paper, P "
                             "would track C and fall by the same 10x through "
                             "defocus. That is the outcome this gate is built "
                             "to catch and it is entirely reachable.",
        "consequence": "If P tracks C, the separation has failed, kappa is an "
                       "upper bound only, and the ruling says the data cannot "
                       "answer the question.",
    },
    {
        "id": "PR-4d",
        "name": "Placebo and negative control for the separator",
        "claim": "cov(r_G1, r_G2) measures common structure and nothing else.",
        "statistic": "(i) POSITIVE: split one group's 20 frames into two "
                     "disjoint 10-frame halves, both on G1; cov between the two "
                     "half-mean residuals must recover the full fixed-pattern "
                     "variance of G1, since the fixed pattern IS common there. "
                     "(ii) NEGATIVE: roll r_G2 by an even offset (discipline "
                     "397 -- even, to preserve CFA phase) and recompute cov; it "
                     "must collapse.",
        "threshold": "(i) recovered within +-20% of var(r_G1) - noise. "
                     "(ii) |cov_rolled| <= 3 standard errors of zero.",
        "fail_input_exists": "A covariance estimator with a normalisation bug "
                             "fails (i). A shared low-frequency residual from "
                             "an under-aggressive smooth surface fails (ii).",
        "consequence": "Either failure withdraws the whole separation.",
    },
    {
        "id": "PR-5",
        "name": "MATERIALITY -- does kappa enter sigma^2(S)?",
        "claim": "kappa enters the model iff it inflates the predicted SIGMA by "
                 "at least 5% at the mid-tone the corpus's own dust spec names, "
                 "S = 8000 DN.",
        "statistic": "sqrt(g*S + (RN*g)^2 + (kappa*S)^2) / sqrt(g*S + (RN*g)^2) "
                     "at S = 8000 DN",
        "threshold": f"kappa >= {KAPPA_MATERIAL:.6f} "
                     f"({KAPPA_MATERIAL * 100:.4f}%) enters; below that it does not",
        "fail_input_exists": "Fact 230's independent bound is <= 0.26%, which is "
                             "ABOVE this threshold, so 'it enters' is reachable "
                             "from the corpus's own prior. A kappa at the "
                             "0.05% level is equally reachable. The gate "
                             "genuinely discriminates.",
        "consequence": "Binding. 'It is negligible and must not be added' is a "
                       "successful outcome and will be reported as the ruling "
                       "if the number lands below the line.",
    },
    {
        "id": "PR-6",
        "name": "Is the CPL spatially flat?",
        "claim": "The circular polariser introduces no spatial non-uniformity "
                 "of its own.",
        "statistic": "Q = (mu_on / mean mu_on) / (mu_off / mean mu_off), "
                     "smoothed; its peak-to-peak and its best-fit radial "
                     "edge-to-centre gradient",
        "threshold": "FLAT iff smoothed peak-to-peak < 1% AND radial gradient "
                     "< 0.5%",
        "fail_input_exists": "A tilted or stress-birefringent filter, or simple "
                             "angle-of-incidence dependence of polariser "
                             "efficiency across a wide cone, all produce a "
                             "radial term well above 0.5%.",
        "consequence": "If not flat, this is a per-stack systematic on the "
                       "seven CPL-on corpus stacks (fact 925 authoritative) "
                       "that nobody has accounted for, and it is reported as "
                       "such.",
        "mandatory_placebo": "The SAME statistic between two SAME-STATE groups "
                             "at different times is the illumination-drift null. "
                             "The CPL claim requires the cross-state Q to exceed "
                             "the same-state placebo by >= 3x its scatter. "
                             "Without the placebo the number means nothing, "
                             "because a moving cloud edge also makes Q non-flat.",
    },
    {
        "id": "PR-7",
        "name": "Dust map",
        "claim": "Dust shadows are fixed in SENSOR coordinates and visible in "
                 "every plane and both CPL states.",
        "statistic": "Connected components of pixels where the plane-averaged "
                     "residual r < -3%, required to be < -1.5% independently in "
                     "BOTH CPL states and in >= 3 of the 4 planes",
        "threshold": "report count, area fraction, size distribution, deepest "
                     "shadow. M29's fact 232 recorded real dust at 1-15% depth.",
        "fail_input_exists": "A clean sensor gives zero components, which is a "
                             "perfectly good result.",
        "consequence": "Reported as a map; no gate hangs on it.",
        "negative_control": "The same detector on a copy rolled by an even "
                            "offset must find ~0 components (discipline 397).",
    },
    {
        "id": "PR-8",
        "name": "Did the illumination drift carry SPATIAL structure?",
        "claim": "Global illumination drift is a per-frame scalar and divides "
                 "out under per-frame mean normalisation. Residual excess "
                 "temporal variance after that normalisation is evidence the "
                 "drift carried spatial structure.",
        "statistic": "ratio of the mean per-pixel temporal variance AFTER "
                     "normalisation to the noise model's prediction, and the "
                     "same ratio computed on a heavily blurred version of each "
                     "frame's residual (which suppresses white noise by the "
                     "kernel's area and so isolates low-frequency drift)",
        "threshold": "no threshold -- REPORTED EITHER WAY. A clean null is "
                     "worth stating and will be stated.",
        "fail_input_exists": "n/a, this is a measurement not a gate",
        "consequence": "A finding rather than a nuisance, per the brief.",
    },
]

NOT_PREREGISTERED = (
    "Anything not in this list that appears in the report is POST-HOC and will "
    "be labelled post-hoc in the report, per M68's form."
)


def main() -> None:
    doc = {
        "milestone": "M71",
        "written_before_reading_pixels": True,
        "constants": {
            "iso": ISO,
            "gain_divisor": GAIN_DIVISOR,
            "g_dn_per_e": G_DN_PER_E,
            "read_noise_e": READ_NOISE_E,
            "sigma_floor_dn": READ_NOISE_E * G_DN_PER_E,
            "black": BLACK,
            "white": WHITE,
            "midtone_dn": MIDTONE,
            "sigma_inflation_gate": SIGMA_INFLATION_GATE,
            "kappa_material_threshold": KAPPA_MATERIAL,
        },
        "criteria": CRITERIA,
        "note": NOT_PREREGISTERED,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    print(f"g  = {G_DN_PER_E:.7f} DN/e-   sigma(0) = {READ_NOISE_E * G_DN_PER_E:.6f} DN")
    print(f"kappa materiality threshold (>=5% sigma inflation at S={MIDTONE:.0f} DN): "
          f"{KAPPA_MATERIAL:.6f} = {KAPPA_MATERIAL * 100:.4f}%")
    print(f"  for reference, at S = {WHITE} DN the same 5% gate would be "
          f"{(((1.05 ** 2 - 1) * G_DN_PER_E / WHITE) ** 0.5) * 100:.4f}%")
    print(f"  fact 230's independent bound is <= 0.26%, i.e. "
          f"{0.0026 / KAPPA_MATERIAL:.2f}x the threshold\n")
    for c in CRITERIA:
        print(f"{c['id']:6s} {c['name']}")
        print(f"       threshold: {c['threshold']}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
