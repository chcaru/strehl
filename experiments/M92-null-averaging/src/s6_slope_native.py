"""M92 S6 -- resolving the pre-registered sensitivity clause, arithmetically.

PREREGISTRATION section 4 named the slope-domain estimator as the mandatory
sensitivity variant and said that a disagreement on the verdict forces NOT
ESTABLISHED.  Section 10 registered, in advance, the prediction that the two
would differ: the primary averages `px = sign(b)*sqrt(|b|)`, the variant
averages `b` and then takes a square root, so near a zero truth the variant's
exponent must be HALF the primary's by construction, not because the per-ROI
estimates are coupled.

DERIVED, and testable: if the per-ROI slopes `b_i` are independent and mean
zero, then RMS(bbar) falls as N^(-1/2); the variant reports sqrt of that, so its
px exponent is 1/4; and the primary, whose summands are already in px and are
themselves independent and mean zero, keeps 1/2.

This script measures the SLOPE-NATIVE exponent `alpha_b` -- the exponent of
RMS(bbar) in slope units, where both estimators live in the same coordinate --
directly from the cached draw matrices.  If `alpha_b` is near 0.5 the two
estimators agree about independence and the difference in their px exponents is
arithmetic.  If `alpha_b` is near 0.25 the disagreement is real and the
pre-registered NOT ESTABLISHED stands.

Nothing here is re-run: it reads the matrices S2 and S3 already wrote.
"""
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m92lib as M92  # noqa: E402


def ladder_rms(v, index):
    fin = np.isfinite(v)
    return {N: dict(rms=M92._rms_for(v, fin, idx, True)[0])
            for N, idx in index.items()}


def main():
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log("=" * 78)
    log("M92 S6 -- slope-native exponent, from the matrices S2/S3 already wrote.")
    log("  alpha_px   : primary, mean of per-ROI px, RMS about 0")
    log("  alpha_b    : SLOPE-NATIVE, mean of per-ROI OLS slopes, RMS about 0")
    log("  alpha_sqrt : the pre-registered variant, sqrt(|mean slope|)")
    log("  DERIVED prediction under independence: alpha_b ~ 0.5,")
    log("  alpha_px ~ 0.5, alpha_sqrt ~ 0.25 = alpha_b / 2.")
    log("=" * 78)
    log(f"  {'matrix':>34} {'ROIs':>5} {'alpha_px':>9} {'alpha_b':>9}"
        f" {'alpha_sqrt':>11} {'a_b/2':>7} {'ratio':>7}")

    out = {}
    for f in sorted(glob.glob(os.path.join(M92.CACHE, "d*_*.npz"))):
        z = np.load(f)
        px, sl = z["px"], z["slope"]
        if px.shape[1] < 32:
            continue                      # leftover smoke matrix
        idx = M92.subset_index(px.shape[0], seed=92)
        a_px, _ = M92.exponent(ladder_rms(px, idx))
        a_b, _ = M92.exponent(ladder_rms(sl, idx))
        rv = {}
        for N, ix in idx.items():
            sub = sl[ix]
            ok = np.isfinite(sub).all(1)
            if not ok.any():
                continue
            bb = sub.mean(1)[ok]
            w = np.sign(bb) * np.sqrt(np.abs(bb))
            rv[N] = dict(rms=float(np.sqrt((w ** 2).mean())))
        a_sq, _ = M92.exponent(rv)
        name = re.sub(r"^d3?_", "", os.path.basename(f))[:-4]
        rat = a_sq / (a_b / 2) if a_b else np.nan
        cp = M92.pair_corr(px)
        cw = M92.pair_corr_pairwise(px)
        cb = M92.corr_boot(px, nboot=1000)
        log(f"  {name:>34} {px.shape[0]:>5} {a_px:>9.4f} {a_b:>9.4f}"
            f" {a_sq:>11.4f} {a_b/2:>7.4f} {rat:>7.3f}")
        out[name] = dict(n_roi=int(px.shape[0]), alpha_px=a_px, alpha_b=a_b,
                         alpha_sqrt=a_sq, ratio_to_half=float(rat),
                         rbar=cp["rbar"], rbar_pairwise=cw["rbar"],
                         rbar_pairs=cp["n_pair"],
                         rbar_pairwise_pairs=cw["n_pair"],
                         rbar_boot=cb, nan_frac=float(1 - np.isfinite(px).mean()))

    if out:
        ab = np.array([v["alpha_b"] for v in out.values()])
        ap = np.array([v["alpha_px"] for v in out.values()])
        rr = np.array([v["ratio_to_half"] for v in out.values()])
        log("")
        log(f"  across {len(out)} matrices:  alpha_b  median {np.median(ab):.4f}"
            f"  range {ab.min():.4f}..{ab.max():.4f}")
        log(f"                             alpha_px median {np.median(ap):.4f}"
            f"  range {ap.min():.4f}..{ap.max():.4f}")
        log(f"    alpha_sqrt / (alpha_b/2): median {np.median(rr):.4f}"
            f"  range {rr.min():.4f}..{rr.max():.4f}"
            f"   (1.000 = the variant is pure arithmetic)")

        log("")
        log("=" * 78)
        log("  CROSS-ROI CORRELATION, two estimators and a draw-level bootstrap.")
        log("  `all-finite` drops any ROI with a single NaN and so selects ROIs;")
        log("  `pairwise` keeps every ROI and uses joint-finite draws per pair.")
        log("  The interval is a 1000-sample bootstrap over DRAWS (pairs share")
        log("  ROIs, so an across-pair standard error would overstate precision).")
        log("=" * 78)
        log(f"  {'matrix':>34} {'NaN%':>6} {'r all-fin':>10} {'npair':>6}"
            f" {'r pairwise':>11} {'npair':>6} {'boot 95% CI':>22}")
        for name, v in out.items():
            b = v["rbar_boot"]
            log(f"  {name:>34} {100*v['nan_frac']:>6.1f} {v['rbar']:>+10.5f}"
                f" {v['rbar_pairs']:>6d} {v['rbar_pairwise']:>+11.5f}"
                f" {v['rbar_pairwise_pairs']:>6d}"
                f"  [{b['lo']:+8.5f},{b['hi']:+8.5f}]")
        rp = np.array([v["rbar_pairwise"] for v in out.values()])
        log("")
        log(f"  pairwise rbar across {len(out)} matrices: median "
            f"{np.median(rp):+.5f}, range {rp.min():+.5f}..{rp.max():+.5f}"
            f"   (material common mode is rbar >= 0.10)")

        log("")
        log("=" * 78)
        log("  WHAT IS THE COMMON MODE?  Removing the per-draw mean across ROIs.")
        log("  If the coupling is a single per-draw global scalar -- one noise")
        log("  realisation that is simply louder on some draws than others --")
        log("  then subtracting mean_j d[j,r] from every d[i,r] must restore")
        log("  alpha to ~0.5 and rbar to ~ -1/(m-1).  If a spatially structured")
        log("  component survives, alpha stays depressed and that structure is")
        log("  the real obstacle.")
        log("=" * 78)
        log(f"  {'matrix':>34} {'alpha':>8} {'a demean':>9} {'rbar':>9}"
            f" {'r demean':>9} {'-1/(m-1)':>9} {'global %':>9}")
        for f in sorted(glob.glob(os.path.join(M92.CACHE, "d*_*.npz"))):
            z = np.load(f)
            px = z["px"]
            if px.shape[1] < 32:
                continue
            name = re.sub(r"^d3?_", "", os.path.basename(f))[:-4]
            if name not in out:
                continue
            idx = M92.subset_index(px.shape[0], seed=92)
            with np.errstate(invalid="ignore"):
                gm = np.nanmean(px, axis=0, keepdims=True)
                dd = px - gm
            a_d, _ = M92.exponent(ladder_rms(dd, idx))
            c_d = M92.pair_corr_pairwise(dd)
            m = px.shape[0]
            vg = float(np.nanvar(gm))
            vt = float(np.nanmean(np.nanvar(px, axis=1)))
            log(f"  {name:>34} {out[name]['alpha_px']:>8.4f} {a_d:>9.4f}"
                f" {out[name]['rbar_pairwise']:>+9.5f} {c_d['rbar']:>+9.5f}"
                f" {-1.0/(m-1):>9.5f} {100*vg/vt:>9.2f}")
            out[name].update(alpha_demeaned=a_d, rbar_demeaned=c_d["rbar"],
                             neg_baseline=-1.0 / (m - 1),
                             global_var_frac=float(vg / vt))

    with open(os.path.join(M92.OUT, "s6_slope_native.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    with open(os.path.join(M92.OUT, "s6_slope_native.log"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\nwrote out/s6_slope_native.{json,log}")


if __name__ == "__main__":
    main()
