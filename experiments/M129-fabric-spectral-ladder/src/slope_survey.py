"""Measure the fabric's texture spectral slope, and test that it does not move with aperture.

TWO REASONS THIS IS NOT OPTIONAL.

First, A1' requires the commissioning battery to measure the crossing estimator's
bias "as a function of planted f_c, signal-to-noise ratio and texture spectral slope,
across the range this ladder actually uses". Every synthetic test written so far has
planted a slope of 2.2 because that is a common value for natural texture, not
because anything here was measured. If the fabric is far from 2.2 the commissioning
surface does not cover the real case and its bias correction is an extrapolation.

Second, Amendment 6 equalises the low-band SNR across apertures and argues that this
equalises the estimator's bias. That argument has a hidden premise: that BELOW the
cutoff the texture spectrum has the same shape at every aperture, differing only in
scale. If the low-band slope itself moved with aperture, matching one number would
not match the spectra, and the equalisation would be cosmetic. The premise is
physically reasonable -- below the cutoff the MTF is near 1 and the subject is the
same subject -- but it is a premise, and it is cheap to test.

WHAT IS FITTED. log P = a - alpha * log f, by least squares over the low band, which
Amendment 6 fixed at 0.040-0.090 sensor cyc/px because it lies below every candidate
cutoff at every aperture in the ladder. The noise floor is subtracted first: a floor
flattens the apparent slope, and at f/18 the floor is a larger fraction of the low
band than at f/11, which would manufacture exactly the aperture dependence this
script is looking for. Not subtracting it would be the same class of error as
Amendment 6's contaminated band.

Reads only out/snr-w2.json. No decode, no raw file, no cutoff estimated.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
LOW = (0.040, 0.090)


def fit_slope(f, p, floor, band=LOW, subtract_floor=True):
    """Least-squares power-law slope over `band`. Returns (alpha, rms of residual)."""
    f = np.asarray(f, float)
    p = np.asarray(p, float)
    sel = (f >= band[0]) & (f <= band[1]) & (f > 0)
    y = p[sel] - (floor if subtract_floor else 0.0)
    x = f[sel]
    good = y > 0
    if good.sum() < 4:
        return float("nan"), float("nan"), int(good.sum())
    lx, ly = np.log(x[good]), np.log(y[good])
    A = np.vstack([np.ones_like(lx), -lx]).T
    coef, *_ = np.linalg.lstsq(A, ly, rcond=None)
    resid = ly - A @ coef
    return float(coef[1]), float(np.sqrt(np.mean(resid ** 2))), int(good.sum())


def main():
    w = sys.argv[1] if len(sys.argv) > 1 else "2"
    with open(os.path.join(OUT, f"snr-w{w}.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    recs = d["records"]
    if "psd" not in recs[0]:
        raise SystemExit("snr-w*.json has no saved spectra; re-run snr_survey.py")
    tags = []
    for r in recs:
        if r["aperture"] not in tags:
            tags.append(r["aperture"])
    rois = sorted({r["roi"] for r in recs})

    print("TEXTURE SPECTRAL SLOPE of the fabric weave")
    print()
    print(f"Fitted as log P = a - alpha*log f over {LOW[0]:.3f}-{LOW[1]:.3f} sensor")
    print(f"cyc/px ({LOW[0] * 1000 / 5.12:.1f}-{LOW[1] * 1000 / 5.12:.1f} cy/mm), "
          f"floor subtracted first.")
    print()
    print(f"  {'ROI':>4} " + "".join(f"{t:>9}" for t in tags) + f"{'spread':>9}")
    tab = {}
    for i in rois:
        row = {}
        for t in tags:
            r = next(x for x in recs if x["roi"] == i and x["aperture"] == t)
            a, rms, nb = fit_slope(r["f"], r["psd"], r["floor"])
            row[t] = a
        tab[i] = row
        vals = [row[t] for t in tags if np.isfinite(row[t])]
        print(f"  {i:>4} " + "".join(f"{row[t]:9.3f}" for t in tags) +
              f"{max(vals) - min(vals):9.3f}")
    print()
    per_ap = {t: np.array([tab[i][t] for i in rois]) for t in tags}
    allv = np.concatenate([per_ap[t] for t in tags])
    print(f"  {'ap':>6} {'mean alpha':>11} {'sd over ROIs':>13}")
    for t in tags:
        print(f"  {t:>6} {per_ap[t].mean():11.3f} {per_ap[t].std():13.3f}")
    print()
    print(f"  overall mean alpha {allv.mean():.3f}, sd {allv.std():.3f}")
    print()

    # --- is the slope aperture-dependent? ---------------------------------
    # Between-aperture spread of the per-aperture means, against the within-
    # aperture spread across ROIs. If the subject is the same subject at every
    # aperture, the former should not exceed the latter.
    means = np.array([per_ap[t].mean() for t in tags])
    between = float(means.std())
    within = float(np.mean([per_ap[t].std() for t in tags]))
    print("  IS THE SLOPE APERTURE-DEPENDENT? Amendment 6's equalisation assumes not.")
    print(f"    spread of the five aperture means      {between:.4f}")
    print(f"    mean spread across ROIs within one ap  {within:.4f}")
    print(f"    ratio {between / within:.2f}")
    indep = between <= within
    print(f"    {'CONSISTENT with an aperture-independent slope' if indep else 'APERTURE DEPENDENCE PRESENT'}"
          f": the between-aperture spread is")
    print(f"    {'no larger' if indep else 'LARGER'} than the ROI-to-ROI spread of the same quantity.")
    print()

    # --- the control that proves the fit can see a difference at all -------
    # A fit that reported the same slope no matter what would pass the test above
    # trivially, so the test needs a positive control: a PLANTED aperture
    # dependence of known size, which the fit must recover.
    #
    # The first version of this control subtracted no floor, on the reasoning that
    # the floor is a larger fraction of the low band at f/18 than at f/11 and must
    # therefore flatten f/18 more. It moved the slopes by 0.003. That is not a
    # failed control, it is a measurement: in this band the signal sits 1000 to
    # 5000 times above the floor, so floor subtraction is irrelevant here and
    # cannot serve as a disturbance. Recorded because it also retires a worry --
    # the low band is nowhere near the noise.
    print("  POTENCY, by planting. A test that cannot respond to a real aperture")
    print("  dependence would pass the one above trivially. So each aperture's")
    print("  spectrum is tilted by a KNOWN per-aperture amount and the fit must")
    print("  recover it.")
    print()
    # The plant is specified by its STANDARD DEVIATION, not its range, because the
    # test it must trip compares standard deviations. A linear ramp's sd is only
    # 0.354 of its span over five points, so a ramp spanning 2*within has an sd of
    # 0.71*within and cannot trip a test set at within -- which is exactly how the
    # first version of this control failed: the fit recovered the plant perfectly
    # and the verdict still did not flip.
    ramp = np.array([k / (len(tags) - 1) - 0.5 for k in range(len(tags))])
    target_sd = 2.0 * within
    planted = {t: float(ramp[k] / ramp.std() * target_sd)
               for k, t in enumerate(tags)}
    print(f"  planted tilt has sd {target_sd:.4f} in alpha, twice the ROI-to-ROI")
    print(f"  spread, running {min(planted.values()):+.4f} to "
          f"{max(planted.values()):+.4f}")
    print()
    print(f"  {'ap':>6} {'planted':>9} {'recovered':>11} {'error':>9}")
    rec_means, errs = {}, []
    fref = np.sqrt(LOW[0] * LOW[1])
    for t in tags:
        vals = []
        for i in rois:
            r = next(x for x in recs if x["roi"] == i and x["aperture"] == t)
            f = np.asarray(r["f"], float)
            p = np.asarray(r["psd"], float)
            with np.errstate(divide="ignore", invalid="ignore"):
                tilt = np.where(f > 0, (f / fref) ** (-planted[t]), 1.0)
            a, _, _ = fit_slope(f, (p - r["floor"]) * tilt, 0.0)
            vals.append(a)
        rec_means[t] = float(np.mean(vals))
        got = rec_means[t] - per_ap[t].mean()
        errs.append(got - planted[t])
        print(f"  {t:>6} {planted[t]:+9.4f} {got:+11.4f} {got - planted[t]:+9.4f}")
    rec_between = float(np.array([rec_means[t] for t in tags]).std())
    plant_between = float(np.array(list(planted.values())).std())
    print()
    print(f"    between-aperture spread, planted {plant_between:.4f}, "
          f"recovered {rec_between:.4f}")
    print(f"    worst per-aperture error {max(abs(e) for e in errs):.4f}")
    recovered = abs(rec_between - plant_between) / plant_between < 0.15
    flagged = rec_between > within
    potent = recovered and flagged
    print(f"    the fit recovers the planted spread to 15%: "
          f"{'PASS' if recovered else 'FAIL'}")
    print(f"    and the aperture-independence test flips to DEPENDENT: "
          f"{'PASS' if flagged else 'FAIL'}")
    print(f"    potency {'PASS' if potent else 'FAIL'}. The corrected fit's failure to")
    print(f"    find an aperture dependence is therefore informative rather than blind.")

    dest = os.path.join(OUT, f"slope-w{w}.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump({"band": LOW, "per_roi": {str(k): v for k, v in tab.items()},
                   "per_aperture_mean": {t: float(per_ap[t].mean()) for t in tags},
                   "per_aperture_sd": {t: float(per_ap[t].std()) for t in tags},
                   "overall_mean": float(allv.mean()),
                   "overall_sd": float(allv.std()),
                   "between": between, "within": within,
                   "aperture_independent": bool(indep),
                   "planted_sd": target_sd,
                   "planted_between": plant_between,
                   "recovered_between": rec_between,
                   "worst_plant_error": float(max(abs(e) for e in errs)),
                   "potent": bool(potent)}, fh, indent=2)
    print()
    print(f"wrote {dest}")
    return 0 if potent else 1


if __name__ == "__main__":
    sys.exit(main())
