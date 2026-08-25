"""M113-ca C15 -- does my own 'the radial shape is flat' conclusion survive the
CORRECTED error bars?

C13 found the published +/- column was produced by a broken bootstrap that
resampled numerator and denominator independently, inflating the sd by 1.5-3.3x
depending on the ring's relative radius spread (C14, rho +0.93/+0.82). The point
estimates are untouched -- only the bars move, and they move DOWN.

Smaller bars make a flatness claim HARDER to sustain, not easier. My report says
eps(r) is "flat across the entire field" for couch-fibers. That was asserted
against the inflated bars. It has to be re-tested against the correct ones, and
if it fails I have to say so.

TEST. Fit a constant eps by inverse-variance weighting and compute chi2/dof
against each of the three bar choices. A constant radial scale -- which is what
the shipped model IS -- predicts chi2/dof ~ 1. Report the peak-to-peak variation
as a fraction of the mean alongside it, because a statistically resolved
departure can still be physically small and the two must not be conflated.

FALSIFIER for my own published wording: if chi2/dof against the corrected bars
is >> 1, "flat across the entire field" is too strong and must be replaced with
a quantified statement of the residual curvature.
"""
import json, os
import numpy as np

OUT = r"C:\dev\strehl-out\M113-ca"

def chi2(vals, sds):
    v = np.asarray(vals, float); s = np.asarray(sds, float)
    w = 1.0 / s ** 2
    mu = float(np.sum(w * v) / np.sum(w))
    c = float(np.sum(w * (v - mu) ** 2))
    dof = len(v) - 1
    return mu, c, dof, c / dof

def main():
    d = json.load(open(os.path.join(OUT, "c13_bootaudit.json")))
    print("=" * 94)
    print("Does 'eps(r) is flat' survive the corrected bars?  chi2/dof for a CONSTANT eps")
    print("=" * 94)
    res = {}
    for name in ("couch-fibers-cpl", "bee-3-cpl"):
        if name not in d:
            continue
        rows = d[name]["rows"]
        eps = [r["eps"] * 1e6 for r in rows]
        print("\n%s   %d rings" % (name, len(rows)))
        print("  r_bar   " + " ".join("%8.3f" % r["rbar"] for r in rows))
        print("  eps ppm " + " ".join("%8.1f" % e for e in eps))
        cell = {}
        for lab, key in (("broken (published)", "sd_broken"),
                         ("paired (correct)", "sd_paired"),
                         ("block (correct+corr)", "sd_block")):
            sds = [r[key] * 1e6 for r in rows]
            mu, c, dof, red = chi2(eps, sds)
            print("  sd %-21s" % lab + " ".join("%8.1f" % s for s in sds))
            print("      -> weighted mean %+.1f ppm   chi2 %.2f / %d dof = %.2f   %s"
                  % (mu, c, dof, red, "FLAT is supported" if red < 2.0
                     else "FLAT is NOT supported"))
            cell[key] = dict(mu=mu, chi2=c, dof=dof, red=red)
        ptp = max(eps) - min(eps)
        mean = float(np.mean(eps))
        print("  peak-to-peak %.1f ppm on a mean of %.1f ppm = %.1f %% of the scale"
              % (ptp, abs(mean), 100.0 * ptp / abs(mean)))
        cell["ptp_ppm"] = ptp; cell["ptp_frac"] = ptp / abs(mean)
        res[name] = cell
    print("\n" + "=" * 94)
    print("READING. The published bars were too LARGE, so any flatness claim made")
    print("against them was made too easily. Whether it survives is decided above.")
    with open(os.path.join(OUT, "c15_flatness.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print("wrote c15_flatness.json")

if __name__ == "__main__":
    main()