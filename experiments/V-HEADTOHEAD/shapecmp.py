"""SHAPE-NORMALISED SPECTRUM -- the sharpness statistic.

grade.py MEASURED that the prior arm renders 1.281x more local contrast than
strehl at the tones the bean occupies (local slope / level ratio, 16x box coarse
scale).  That alone predicts a contrast-variance ratio of 1/1.281^2 = 0.610, and
the measured whole-spectrum ratio is 0.556 -- i.e. THE CONTRAST GAP IS A GRADE.
A naive microcontrast comparison would report it as "prior is sharper", which is
exactly the failure this project keeps hitting.

So the sharpness statistic is each arm's spectrum normalised BY ITS OWN
low-frequency band.  Any scalar contrast factor cancels exactly.  What survives
is the SHAPE of the spectrum -- resolution.

Read against: the scale-confound control (strehl's own 3.5% crop+upsample costs
real high-frequency power and must be discounted), and the flat-ROI noise floor.
"""
import numpy as np, arms, spec, json

REF = (0.02, 0.05)

def shape(arm, rois, T=384):
    per = []
    for (y, x) in rois:
        v, c, _ = spec.band_variance(arm, y, x, T)
        if v is None or c > 0: continue
        per.append([v[k] for k in spec.BANDS])
    return np.array(per)

def shape_ratio(A, B, rois, label, na, nb, T=384):
    a = shape(A, rois, T); b = shape(B, rois, T)
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    iref = spec.BANDS.index(REF)
    print(f"\n===== {label}  ({n} ROIs) =====")
    print(f"{'band':<12}{na+' shape':>14}{nb+' shape':>14}{'shape ratio':>13}{'   95% CI':>20}")
    rng = np.random.default_rng(17); out = {}
    for j, k in enumerate(spec.BANDS):
        sa = a[:, j].sum() / a[:, iref].sum(); sb = b[:, j].sum() / b[:, iref].sum()
        idx = rng.integers(0, n, (4000, n))
        bsa = a[idx, j].sum(1) / a[idx, iref].sum(1)
        bsb = b[idx, j].sum(1) / b[idx, iref].sum(1)
        r = bsb / bsa
        lo, hi = np.percentile(r, [2.5, 97.5])
        print(f"{k[0]:.2f}-{k[1]:.2f}   {sa:>14.5f}{sb:>14.5f}{sb/sa:>13.3f}   [{lo:.3f}, {hi:.3f}]")
        out[f"{k[0]:.2f}-{k[1]:.2f}"] = [float(sa), float(sb), float(sb/sa), float(lo), float(hi)]
    return out

if __name__ == "__main__":
    P = arms.prior_arm()
    res = {}
    res["null"] = shape_ratio(P, arms.clone_arm(P), spec.DETAIL_ROIS,
        "NULL CONTROL (shape): prior vs prior", "prior", "clone")
    res["pos"] = shape_ratio(P, arms.blur_arm(P, 0.8), spec.DETAIL_ROIS,
        "POSITIVE CONTROL (shape): prior vs prior blurred 0.8 px", "prior", "blur")
    RS = arms.rescale_arm(P, arms.h2h.SCALE)
    res["scale"] = shape_ratio(P, RS, spec.DETAIL_ROIS,
        "SCALE-CONFOUND CONTROL (shape): the cost of strehl's own 3.5% crop+upsample", "prior", "rescaled")
    del RS
    S = arms.strehl_arm()
    res["real"] = shape_ratio(P, S, spec.DETAIL_ROIS,
        "REAL (shape): prior vs strehl SHIP-V2 -- SHARPNESS, grade removed", "prior", "strehl")
    print("\n===== strehl shape ratio CORRECTED for its own rescale cost =====")
    print(f"{'band':<12}{'raw':>9}{'confound':>11}{'corrected':>12}")
    for k in res["real"]:
        r = res["real"][k][2]; c = res["scale"][k][2]
        print(f"{k:<12}{r:>9.3f}{c:>11.3f}{r/c:>12.3f}")
    json.dump(res, open("shape_results.json", "w"), indent=1)
