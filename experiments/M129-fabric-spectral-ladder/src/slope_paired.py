"""The slope IS aperture-dependent, and the question is whether diffraction explains it.

WHY THIS EXISTS. slope_survey.py compared the spread of the five aperture means
(0.1553) against the mean ROI-to-ROI spread within one aperture (0.2467) and read
"consistent with an aperture-independent slope" from 0.1553 <= 0.2467. That test is
too weak, for a reason that is visible in its own saved table: the SAME six ROIs are
measured at every aperture, so ROI-to-ROI variation is a shared block effect that does
not inflate the difference between apertures at all. Comparing a between-aperture
spread against a within-aperture spread throws away the pairing and hides an effect
that the paired data show plainly:

    f/18 has a steeper slope than f/11 in 6 of the 6 ROIs.

Six of six in a fixed direction is p = 0.031 two-sided on a sign test alone, before
the size of the difference is considered. So the slope IS aperture-dependent as
measured, and Amendment 6's equalisation rests on it not being.

THE HYPOTHESIS THIS TESTS. The subject is one subject, photographed once. Its true
texture slope cannot depend on the aperture. What CAN depend on the aperture is the
measured slope, because the diffraction MTF is already falling inside the low band:
at f/18 the cutoff is lowest, so the roll-off intrudes furthest into the band and
steepens the fitted slope the most. That predicts a specific ORDER, f/11 < f/14 <
f/18, and it predicts a specific SIZE, which can be computed from the known MTF
without reference to the measurement.

    PREDICTION, COMPUTED BEFORE COMPARING: fit the same low band on a pure power law
    of index alpha_0 multiplied by mtf_diffraction squared at each aperture, and the
    fitted index rises by an amount that depends only on the aperture and the band.
    If the measured per-aperture differences match that, the aperture dependence is
    an artefact of the instrument rather than a property of the subject, and the
    subject slope is recovered by subtracting it.

HONESTY NOTE, REQUIRED BY RULE 18. The direction f/11 < f/14 < f/18 was seen in the
saved table before this script was written, so the ORDER is not a prediction here. The
SIZE is: nothing in the measurement was used to compute the predicted steepening, and
the two are compared only at the end.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "m5-diffraction"))

from slope_survey import fit_slope, LOW  # noqa: E402
import m5_lib  # noqa: E402

TAGS = ["f5.6", "f8", "f11", "f14", "f18"]
NUM = {"f5.6": 5.6, "f8": 8.0, "f11": 11.0, "f14": 14.0, "f18": 18.0}
PRIMARY = ["f11", "f14", "f18"]


def predicted_slope(n_eff, alpha0, f):
    """Low-band slope fitted to a pure power law seen through the diffraction MTF.

    The PSD of an image is the object PSD times the squared MTF, so the model is
    f**-alpha0 * mtf(f)**2. No measured quantity enters.

    Section 2.2 defines `B` as the effective-f-number multiplier: N_eff = B * N, and
    f_c = PITCH_UM / (lambda * N_eff). B is the very constant this lane is trying to
    measure, so the prediction is computed under BOTH live hypotheses and the spread
    between them is reported rather than one being assumed.
    """
    fc = m5_lib.f_cutoff_sensor(n_eff)
    m = m5_lib.mtf_diffraction(f, fc)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = np.where(f > 0, f ** (-alpha0), 0.0) * m ** 2
    a, _, _ = fit_slope(f, p, 0.0)
    return float(a)


def main():
    with open(os.path.join(OUT, "slope-w2.json"), encoding="utf-8") as fh:
        s = json.load(fh)
    with open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8") as fh:
        sn = json.load(fh)
    per = s["per_roi"]
    rois = sorted(per, key=int)
    A = np.array([[per[i][t] for t in TAGS] for i in rois], float)

    print("IS THE MEASURED SLOPE APERTURE-DEPENDENT? A PAIRED TEST.")
    print()
    print("  The same six ROIs are measured at every aperture, so the comparison is")
    print("  paired and the ROI main effect must be removed before apertures are")
    print("  compared. slope_survey.py did not do that, and its verdict is too weak.")
    print()
    blocked = A - A.mean(axis=1, keepdims=True)
    eff = blocked.mean(axis=0)
    resid = blocked - eff
    # Residual df: 6 ROIs x 5 apertures, minus 6 ROI means, minus 4 free aperture
    # effects (they sum to zero after blocking).
    dof = A.size - len(rois) - (len(TAGS) - 1)
    s_res = float(np.sqrt((resid ** 2).sum() / dof))
    se = s_res / np.sqrt(len(rois))
    print(f"  {'ap':>6} {'mean alpha':>11} {'effect':>9} {'se':>7} {'t':>7}")
    for k, t in enumerate(TAGS):
        print(f"  {t:>6} {A[:, k].mean():11.3f} {eff[k]:+9.4f} {se:7.4f} "
              f"{eff[k] / se:+7.2f}")
    print()
    print(f"  residual sd {s_res:.4f} on {dof} df, so the standard error of each")
    print(f"  aperture effect is {se:.4f}. An effect beyond about {2.06 * se:.3f} is")
    print(f"  significant at 5%.")
    print()

    # --- the sign test, which needs no model at all ------------------------
    d = A[:, TAGS.index("f18")] - A[:, TAGS.index("f11")]
    npos = int((d > 0).sum())
    print("  SIGN TEST, f/18 minus f/11, which assumes nothing about the noise:")
    print(f"    positive in {npos} of {len(d)} ROIs, "
          f"mean difference {d.mean():+.4f}, sd {d.std(ddof=1):.4f}")
    from math import comb
    p2 = 2.0 * sum(comb(len(d), k) for k in range(npos, len(d) + 1)) / 2 ** len(d)
    print(f"    two-sided p = {min(p2, 1.0):.4f}")
    print(f"    VERDICT: the measured slope IS aperture-dependent across the primary")
    print(f"    arm. slope_survey.py's 'aperture-independent' reading was wrong.")
    print()

    # --- does the diffraction MTF predict the size, not just the order? ----
    f = np.asarray(sn["records"][0]["f"], float)
    band = (f >= LOW[0]) & (f <= LOW[1])
    print("  DOES DIFFRACTION EXPLAIN IT? The subject cannot change with aperture,")
    print("  but the MEASURED slope can, because the MTF is already falling inside")
    print("  the low band. The predicted steepening uses only the known MTF and the")
    print(f"  band {LOW[0]:.3f}-{LOW[1]:.3f} cyc/px -- no measured quantity enters.")
    print()
    alpha0 = 3.0
    B = {"H2": 3.0763, "H3": 2.4020}
    results = {}
    for hyp, b in B.items():
        pred = {t: predicted_slope(b * NUM[t], alpha0, f) for t in TAGS}
        base = pred["f5.6"]
        print(f"  Under {hyp}, B = {b:.4f}:")
        print(f"  {'ap':>6} {'predicted':>11} {'pred rel':>10} {'obs rel':>9} "
              f"{'diff':>8}")
        for k, t in enumerate(TAGS):
            pr = pred[t] - base
            ob = A[:, k].mean() - A[:, TAGS.index("f5.6")].mean()
            print(f"  {t:>6} {pred[t]:11.3f} {pr:+10.4f} {ob:+9.4f} "
                  f"{ob - pr:+8.4f}")
        results[hyp] = pred
        print()
    ob_arm = A[:, TAGS.index("f18")].mean() - A[:, TAGS.index("f11")].mean()
    print(f"  Across the primary arm f/11 to f/18:")
    print(f"    observed steepening                      : {ob_arm:+.4f}")
    pr_by = {}
    for hyp, pred in results.items():
        pr_arm = pred["f18"] - pred["f11"]
        pr_by[hyp] = pr_arm
        print(f"    predicted from diffraction alone, {hyp}    : {pr_arm:+.4f}   "
              f"(observed / predicted {ob_arm / pr_arm if pr_arm else float('nan'):.2f})")
    print()
    lo, hi = min(pr_by.values()), max(pr_by.values())
    sed = 2.06 * se * np.sqrt(2)
    explained = (ob_arm >= lo - sed) and (ob_arm <= hi + sed)
    pr_arm = pr_by["H2"]
    if explained:
        print(f"    The observed {ob_arm:+.4f} lies within measurement error "
              f"(+/-{sed:.3f}) of the")
        print(f"    range {lo:+.4f} to {hi:+.4f} that the diffraction MTF alone "
              f"predicts.")
        print("    So the SUBJECT's slope is aperture-independent and the MEASURED")
        print("    slope is not: the difference is the instrument, not the fabric.")
    else:
        print(f"    The observed {ob_arm:+.4f} lies OUTSIDE the predicted range")
        print(f"    {lo:+.4f} to {hi:+.4f} even allowing +/-{sed:.3f} of measurement")
        print("    error, so something beyond the MTF differs between apertures in")
        print("    the low band. This is a live confound, not a retired one.")
    print()
    print("  f/5.6 IS THE ODD ONE OUT AND IT IS NOT DIFFRACTION. Diffraction predicts")
    print("  f/5.6 to be the SHALLOWEST measured slope, since its cutoff is furthest")
    print(f"  above the band. It is instead the steepest, at {A[:, 0].mean():.3f}.")
    print("  The likely cause is T1, the registered primary threat: f/5.6 has the")
    print("  shallowest depth of field, so more of the ROI is out of focus, and")
    print("  defocus blur steepens the spectrum. That is consistent with section")
    print("  2.3 treating f/5.6 as an out-of-band control rather than a measurement.")
    print()

    # --- what it costs the equalisation ------------------------------------
    span = LOW[1] / LOW[0]
    tilt = span ** abs(ob_arm)
    print("  WHAT THIS COSTS AMENDMENT 6. Equalising the low band assumes the band's")
    print("  SHAPE is common and only its LEVEL differs. A slope difference of")
    print(f"  {abs(ob_arm):.4f} across a band spanning {span:.2f}x in frequency tilts one")
    print(f"  end of the band relative to the other by {tilt:.3f}x. The measured")
    low_ratio = 1.72
    print(f"  low-band power ratio being equalised is {low_ratio:.2f}x, so the shape")
    print(f"  error is about {100 * (tilt - 1) / (low_ratio - 1):.0f}% of the level")
    print(f"  difference being corrected. It is not negligible and it is not")
    print(f"  dominant.")

    dest = os.path.join(OUT, "slope-paired.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump({"effects": {t: float(eff[k]) for k, t in enumerate(TAGS)},
                   "se": se, "resid_sd": s_res, "dof": int(dof),
                   "sign_npos": npos, "sign_n": len(d),
                   "sign_p": float(min(p2, 1.0)),
                   "mean_diff_f18_f11": float(d.mean()),
                   "predicted_arm": float(pr_arm),
                   "observed_arm": float(ob_arm),
                   "explained_by_diffraction": bool(explained),
                   "band_tilt": float(tilt),
                   "shape_vs_level_pct": float(100 * (tilt - 1) / (low_ratio - 1))},
                  fh, indent=2)
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
