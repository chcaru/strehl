"""M33 step 2: does the sub-frame peak offset matter, and can it be estimated?

Fact 263 argued that the defect in selection is not a noise problem -- a
142-sigma peak cannot be SNR-limited -- so M2's argmax defect and M27's
under-resolved pixels must be SAMPLING failures: the true through-focus peak
lies BETWEEN frames and no estimator in the project has a term for it. Question
65 names that offset as the load-bearing confidence candidate. This is its cheap
falsifiable form, on real data rather than synthetic cells.

Ground truth is the 105-frame dense grid. The operational stack is a x2
decimation of it, so every claim here is about what an operational stack loses
relative to a focus axis sampled twice as finely, measured from real samples
only -- retention = f(best sampled frame) / f(best dense frame), no interpolation
anywhere in the truth.

The predictor is free and available at inference time: a parabola through the
three decimated samples around the argmax extrapolates the peak the grid missed,
so predicted retention = f_sampled_max / f_parabola_peak.

PRE-REGISTERED, with effect sizes (discipline 142):
  P1  median retention at x2 is below 1 by more than 1%, and falls monotonically
      at x4 and x6.  Anchored estimate: if the through-focus curve is roughly
      Gaussian with sigma ~1.3 dense frames (M27's n_eff ~ 3), a median offset of
      0.5 dense frames costs exp(-0.25/3.38) = 0.93, i.e. a ~7% deficit at x2.
  P2  the predictor tracks the truth at Spearman rho > 0.5 at x2.
  P3  the two x2 phases (even and odd frames) agree in median retention to
      within 0.005.  This is the replication null: both are legitimate
      operational stacks and nothing should distinguish them.
  P4  FLOOR BIAS.  The parabola predicts a peak above the sampled maximum even
      when the grid is dense, so run it at x1 where the true deficit is ZERO by
      construction.  The hallucinated deficit at x1 must be smaller than the true
      deficit at x2, or the predictor cannot tell a sampling gap from its own
      extrapolation and is useless as confidence.
"""
import numpy as np, os, json
from scipy.stats import spearmanr

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")
rng = np.random.default_rng(20260812)
NPIX = 40000

V = np.load(os.path.join(CACHE, "dense_focus.npy"))
n_dense = V.shape[0]

# sample pixels once; every arm is scored on the same ones
b = 8
idx = (rng.integers(b, V.shape[1] - b, NPIX), rng.integers(b, V.shape[2] - b, NPIX))
D = V[:, idx[0], idx[1]].astype(np.float64)          # (105, NPIX)
f_dense_max = D.max(0)
k_dense = D.argmax(0)

# interpolated dense peak, used ONLY to report the offset -- never in retention
kk = np.clip(k_dense, 1, n_dense - 2)
c0, cm, cp = D[kk, np.arange(NPIX)], D[kk - 1, np.arange(NPIX)], D[kk + 1, np.arange(NPIX)]
den = cm - 2 * c0 + cp
tau = kk + np.where(np.abs(den) > 1e-12, -0.5 * (cp - cm) / np.where(np.abs(den) > 1e-12, den, 1), 0.0)
interior = (k_dense >= 2) & (k_dense <= n_dense - 3)

res = {"n_pixels": int(NPIX), "frac_interior": float(interior.mean()), "arms": {}}


def arm(sel, label):
    S = D[sel]                                        # (m, NPIX)
    m = S.shape[0]
    j = S.argmax(0)
    f_max = S.max(0)
    retention = f_max / f_dense_max                   # truth, samples only
    offset_dense = np.abs(tau - np.asarray(sel)[j])   # in dense-frame units

    # inference-time predictor: parabola through the 3 decimated samples
    jj = np.clip(j, 1, m - 2)
    a0, am_, ap = S[jj, np.arange(NPIX)], S[jj - 1, np.arange(NPIX)], S[jj + 1, np.arange(NPIX)]
    dn = am_ - 2 * a0 + ap
    ok = (dn < -1e-12) & (j >= 1) & (j <= m - 2)
    shift = np.where(ok, -0.5 * (ap - am_) / np.where(ok, dn, 1), 0.0)
    peak = np.where(ok, a0 - 0.25 * (ap - am_) * shift, a0)
    pred_retention = np.where(ok, f_max / np.maximum(peak, 1e-12), 1.0)

    g = interior & ok
    rho = float(spearmanr(pred_retention[g], retention[g]).statistic)
    return dict(
        n_frames=int(m), frac_usable=float(g.mean()),
        retention_median=float(np.median(retention[g])),
        retention_p05=float(np.percentile(retention[g], 5)),
        retention_p25=float(np.percentile(retention[g], 25)),
        deficit_median_pct=float(100 * (1 - np.median(retention[g]))),
        offset_dense_median=float(np.median(offset_dense[g])),
        offset_dense_p95=float(np.percentile(offset_dense[g], 95)),
        pred_deficit_median_pct=float(100 * (1 - np.median(pred_retention[g]))),
        spearman_pred_vs_true=rho,
    ), label


for sel, label in [
    (list(range(0, n_dense, 1)), "x1 (floor-bias control, true deficit = 0)"),
    (list(range(0, n_dense, 2)), "x2 phase even (operational)"),
    (list(range(1, n_dense, 2)), "x2 phase odd  (replication null)"),
    (list(range(0, n_dense, 4)), "x4"),
    (list(range(0, n_dense, 6)), "x6"),
]:
    row, lab = arm(sel, label)
    res["arms"][lab] = row
    print(f"{lab:42s} {json.dumps(row)}")

e = res["arms"]["x2 phase even (operational)"]
o = res["arms"]["x2 phase odd  (replication null)"]
f = res["arms"]["x1 (floor-bias control, true deficit = 0)"]
res["verdict"] = dict(
    P1_deficit_x2_pct=e["deficit_median_pct"],
    P1_monotone=bool(res["arms"]["x6"]["deficit_median_pct"]
                     > res["arms"]["x4"]["deficit_median_pct"] > e["deficit_median_pct"]),
    P2_spearman=e["spearman_pred_vs_true"],
    P3_phase_gap=abs(e["retention_median"] - o["retention_median"]),
    P4_floor_bias_pct=f["pred_deficit_median_pct"],
    P4_true_deficit_x2_pct=e["deficit_median_pct"],
    P4_separable=bool(f["pred_deficit_median_pct"] < e["deficit_median_pct"]),
)
print("verdict:", json.dumps(res["verdict"], indent=2))
with open(os.path.join(OUT, "02-offset.json"), "w") as fh:
    json.dump(res, fh, indent=2)
