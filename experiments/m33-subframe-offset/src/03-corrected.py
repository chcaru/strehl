"""M33 step 3: corrected predictor, and the summary the distribution actually admits.

Two defects in step 2, both left in place per rule 15 and both disclosed here.

DEFECT 1 -- sign error in the parabola vertex VALUE. For samples (am, a0, ap)
with dn = am - 2*a0 + ap < 0, the vertex sits at x* = -0.5*(ap-am)/dn and its
value is a0 - 0.125*(ap-am)^2/dn, i.e. a0 + 0.25*(ap-am)*x*. Step 2 wrote
a0 - 0.25*(ap-am)*x*, which puts the predicted peak BELOW the sampled maximum
and makes every predicted deficit negative. The Spearman figures in step 2 are
still readable -- the two forms are monotone decreasing functions of each other,
so the reported -0.58 corresponds to +0.58 -- but that is an argument, and this
script measures it instead.

DEFECT 2 -- the MEDIAN is the wrong summary. A x2 grid contains half the dense
frames, so a pixel whose dense argmax happens to land on a sampled frame has
retention EXACTLY 1. The distribution is a mixture: a point mass at 1.0 holding
about half the pixels, plus a spread. The median therefore sits on the boundary
of the point mass and reports 1.0 for one phase and 0.9977 for the other, which
is an artefact of which side of 50% the mass falls on and not a measurement of
anything. The quantity with meaning is the deficit CONDITIONAL ON MISSING.

PRE-REGISTERED (the step-2 predictions that survive, plus their repairs):
  P5  with the sign corrected, Spearman rho > 0.5 at x2, matching the magnitude
      step 2 reported with the opposite sign.
  P6  conditional on missing, the median deficit at x2 is between 2% and 10%
      (step 2's p25 of the full distribution, 4.8%, is the same quantity read
      off the mixture, so this is a consistency check rather than a discovery).
  P7  GROUND-TRUTH ADEQUACY, and this one can invalidate the milestone. The x1
      arm's predicted deficit estimates how much the DENSE grid itself misses.
      If that is comparable to the true x2 deficit, the ground truth is not
      finer than the effect and nothing in M33 is readable. It must be at least
      3x smaller.
  P8  CALIBRATION, which rank correlation does not test. For a confidence output
      the predicted magnitude has to be right, not merely ordered: the median
      ratio of predicted to true deficit among missing pixels must lie in
      [0.5, 2.0], and more than half of those pixels must be within a factor 2.
"""
import numpy as np, os, json
from scipy.stats import spearmanr

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")
rng = np.random.default_rng(20260812)          # same seed as step 2: same pixels
NPIX = 40000

V = np.load(os.path.join(CACHE, "dense_focus.npy"))
n_dense = V.shape[0]
b = 8
idx = (rng.integers(b, V.shape[1] - b, NPIX), rng.integers(b, V.shape[2] - b, NPIX))
D = V[:, idx[0], idx[1]].astype(np.float64)
f_dense_max = D.max(0)
k_dense = D.argmax(0)
ar = np.arange(NPIX)

kk = np.clip(k_dense, 1, n_dense - 2)
den = D[kk - 1, ar] - 2 * D[kk, ar] + D[kk + 1, ar]
sh = np.where(np.abs(den) > 1e-12, -0.5 * (D[kk + 1, ar] - D[kk - 1, ar]) / np.where(np.abs(den) > 1e-12, den, 1), 0.0)
tau = kk + np.clip(sh, -1, 1)
interior = (k_dense >= 2) & (k_dense <= n_dense - 3)

res = {"n_pixels": int(NPIX), "arms": {}}


def arm(sel):
    S = D[sel]
    m = S.shape[0]
    j = S.argmax(0)
    f_max = S.max(0)
    retention = f_max / f_dense_max
    offset = np.abs(tau - np.asarray(sel)[j])

    jj = np.clip(j, 1, m - 2)
    a0, am_, ap = S[jj, ar], S[jj - 1, ar], S[jj + 1, ar]
    dn = am_ - 2 * a0 + ap
    ok = (dn < -1e-12) & (j >= 1) & (j <= m - 2)
    shift = np.where(ok, -0.5 * (ap - am_) / np.where(ok, dn, 1), 0.0)
    peak = np.where(ok, a0 + 0.25 * (ap - am_) * shift, a0)       # CORRECTED SIGN
    pred_ret = np.where(ok, f_max / np.maximum(peak, 1e-12), 1.0)

    g = interior & ok
    exact = retention >= 1.0 - 1e-12
    miss = g & ~exact
    td, pd = 1 - retention, 1 - pred_ret
    nm = int(miss.sum())
    ratio = pd[miss] / np.maximum(td[miss], 1e-9) if nm else np.array([np.nan])
    q = (lambda a, p: float(100 * np.percentile(td[miss], p))) if nm else (lambda a, p: None)
    return dict(
        n_frames=int(m), frac_usable=float(g.mean()), n_missing=nm,
        frac_peak_sampled_exactly=float(exact[g].mean()),
        deficit_all_mean_pct=float(100 * td[g].mean()),
        deficit_cond_median_pct=q(td, 50),
        deficit_cond_p90_pct=q(td, 90),
        deficit_cond_p99_pct=q(td, 99),
        offset_median=float(np.median(offset[g])),
        pred_deficit_all_mean_pct=float(100 * pd[g].mean()),
        pred_deficit_cond_median_pct=float(100 * np.median(pd[miss])) if nm else None,
        spearman=float(spearmanr(pd[g], td[g]).statistic),
        calib_ratio_median=float(np.median(ratio)) if nm else None,
        calib_frac_within_2x=float(((ratio > 0.5) & (ratio < 2.0)).mean()) if nm else None,
    )


ARMS = [("x1", 1), ("x2even", 2), ("x2odd", -2), ("x4", 4), ("x6", 6)]
for label, d in ARMS:
    sel = list(range(1, n_dense, 2)) if d < 0 else list(range(0, n_dense, d))
    res["arms"][label] = arm(sel)
    print(f"{label:8s} {json.dumps(res['arms'][label])}")

# effective through-focus width implied by the decimation ladder (Gaussian read)
w = {}
for label in ("x2even", "x4", "x6"):
    a = res["arms"][label]
    dfc = a["deficit_cond_median_pct"] / 100
    off = a["offset_median"]
    if 0 < dfc < 1:
        w[label] = float(off / np.sqrt(-2 * np.log(1 - dfc)))
res["implied_gaussian_sigma_dense_frames"] = w

e, one = res["arms"]["x2even"], res["arms"]["x1"]
res["verdict"] = dict(
    P5_spearman_x2=e["spearman"],
    P6_cond_deficit_x2_pct=e["deficit_cond_median_pct"],
    P7_dense_grid_own_deficit_pct=one["pred_deficit_all_mean_pct"],
    P7_ratio_x2_true_to_dense_own=(e["deficit_all_mean_pct"] / one["pred_deficit_all_mean_pct"]
                                   if one["pred_deficit_all_mean_pct"] > 0 else None),
    P8_calib_ratio_median=e["calib_ratio_median"],
    P8_frac_within_2x=e["calib_frac_within_2x"],
)
print("verdict:", json.dumps(res["verdict"], indent=2))
print("implied sigma:", json.dumps(w, indent=2))
with open(os.path.join(OUT, "03-corrected.json"), "w") as fh:
    json.dump(res, fh, indent=2)
