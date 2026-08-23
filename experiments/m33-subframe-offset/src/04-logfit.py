"""M33 step 4: why three-point parabolic peak interpolation is blind, and the fix.

Step 3 found the parabola predictor's estimated deficit pinned near 1.5% while
the true deficit ran 2.75% -> 9.74% -> 19.60% across x2/x4/x6. It is nearly blind
to the quantity it is asked to report. Three-point parabolic peak interpolation
is standard in essentially every focus stacker, so if this is a real mechanism
rather than a property of coffee-bean it matters beyond this project.

MECHANISM (to be tested, not assumed): a parabola through three samples of a
peaked curve assumes the curve IS a parabola. Real through-focus responses have
heavier shoulders, so a fit through widely spaced samples is too FLAT near the
peak and under-states how much higher the true peak is -- and the wider the
spacing, the flatter the fit. The resulting relative deficit depends only on the
SHAPE of the three samples, which is scale-free, so it barely moves with spacing.
That would make it another self-normalised shape statistic in the sense of
discipline 120, in a third independent guise.

THE FIX: if the response is approximately Gaussian in defocus, then log f is
exactly a parabola and the three-point fit in the LOG domain is exact at every
spacing. That is a one-line change wherever the interpolation is done. Real
curves sit on a baseline (the focus measure does not reach zero when defocused),
and log is not shift-invariant, so a baseline-subtracted variant is measured too.

PRE-REGISTERED:
  P9   on a synthetic Gaussian the parabola predictor's relative deficit varies
       by less than 2x across spacings where the TRUE deficit varies by more than
       5x -- reproducing the real-data pattern from first principles.
  P10  on the same synthetic, the log-domain fit recovers the true deficit to
       within 10% at every spacing.
  P11  on real coffee-bean data at x2, the log-domain fit beats the parabola on
       both calibration measures: median predicted/true ratio nearer 1.0, and a
       larger fraction of pixels within a factor 2.
  PLACEBO  on a synthetic curve that is genuinely a PARABOLA, the parabola fit
       must be exact and the log fit must be WORSE. Without this, "the log fit
       wins" is unfalsifiable and could just mean log helps everywhere.
"""
import numpy as np, os, json

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")
rng = np.random.default_rng(20260813)
NPIX = 40000
res = {"synthetic": {}, "real": {}}


def three_point(am_, a0, ap):
    """parabola vertex offset and value from three equally spaced samples"""
    dn = am_ - 2 * a0 + ap
    ok = dn < -1e-12
    sh = np.where(ok, -0.5 * (ap - am_) / np.where(ok, dn, 1), 0.0)
    return ok, sh, np.where(ok, a0 + 0.25 * (ap - am_) * sh, a0)


def predict(am_, a0, ap, mode, base=0.0):
    if mode == "parabola":
        ok, _, pk = three_point(am_, a0, ap)
        return ok, 1 - a0 / np.maximum(pk, 1e-12)
    lo = 1e-9
    x = np.maximum(am_ - base, lo), np.maximum(a0 - base, lo), np.maximum(ap - base, lo)
    ok, _, pk = three_point(np.log(x[0]), np.log(x[1]), np.log(x[2]))
    return ok, 1 - x[1] / np.maximum(np.exp(pk), 1e-12)


# ---------------- synthetic: shape known exactly ---------------------------
N = 200000
for shape in ("gaussian", "parabola"):
    row = {}
    for h in (2.0, 4.0, 6.0):
        sig = 2.0
        d = rng.uniform(-h / 2, h / 2, N)            # offset of nearest sample from peak
        xs = np.stack([d - h, d, d + h])
        if shape == "gaussian":
            f = np.exp(-xs ** 2 / (2 * sig ** 2))
        else:
            f = np.maximum(1 - xs ** 2 / (2 * sig ** 2), 1e-6)
        j = f.argmax(0)
        a0 = f[j, np.arange(N)]
        jm, jp = np.clip(j - 1, 0, 2), np.clip(j + 1, 0, 2)
        am_, ap = f[jm, np.arange(N)], f[jp, np.arange(N)]
        inner = j == 1                                # only the centre sample has both sides
        true_def = 1 - a0
        ok_p, pd_p = predict(am_, a0, ap, "parabola")
        ok_l, pd_l = predict(am_, a0, ap, "log")
        gp, gl = inner & ok_p, inner & ok_l
        row[f"h{h:g}"] = dict(
            true_deficit_median_pct=float(100 * np.median(true_def[inner])),
            parabola_pred_pct=float(100 * np.median(pd_p[gp])),
            parabola_ratio=float(np.median(pd_p[gp] / true_def[gp])),
            log_pred_pct=float(100 * np.median(pd_l[gl])),
            log_ratio=float(np.median(pd_l[gl] / true_def[gl])),
        )
    res["synthetic"][shape] = row
    print(f"{shape}: {json.dumps(row, indent=1)}")

# ---------------- real data ------------------------------------------------
V = np.load(os.path.join(CACHE, "dense_focus.npy"))
n_dense = V.shape[0]
b = 8
r2 = np.random.default_rng(20260812)                 # same pixels as steps 2-3
idx = (r2.integers(b, V.shape[1] - b, NPIX), r2.integers(b, V.shape[2] - b, NPIX))
D = V[:, idx[0], idx[1]].astype(np.float64)
f_dense_max = D.max(0)
k_dense = D.argmax(0)
interior = (k_dense >= 2) & (k_dense <= n_dense - 3)
ar = np.arange(NPIX)

for label, step in (("x2even", 2), ("x4", 4), ("x6", 6)):
    S = D[list(range(0, n_dense, step))]
    m = S.shape[0]
    j = S.argmax(0)
    f_max = S.max(0)
    true_def = 1 - f_max / f_dense_max
    jj = np.clip(j, 1, m - 2)
    a0, am_, ap = S[jj, ar], S[jj - 1, ar], S[jj + 1, ar]
    base = np.percentile(S, 5, axis=0)
    row = {}
    for mode, bs in (("parabola", 0.0), ("log", 0.0), ("log_baseline", base)):
        ok, pd = predict(am_, a0, ap, "parabola" if mode == "parabola" else "log", bs)
        g = interior & ok & (j >= 1) & (j <= m - 2) & (true_def > 1e-12)
        ratio = pd[g] / true_def[g]
        row[mode] = dict(
            pred_deficit_median_pct=float(100 * np.median(pd[g])),
            calib_ratio_median=float(np.median(ratio)),
            calib_frac_within_2x=float(((ratio > 0.5) & (ratio < 2.0)).mean()),
        )
    row["true_deficit_median_pct"] = float(100 * np.median(true_def[interior & (true_def > 1e-12)]))
    res["real"][label] = row
    print(f"{label}: {json.dumps(row)}")

with open(os.path.join(OUT, "04-logfit.json"), "w") as fh:
    json.dump(res, fh, indent=2)
