"""M33 step 5: the same test for peak POSITION, which is what stackers actually use it for.

Step 4 measured the peak VALUE (the deficit). Three-point parabolic interpolation
is more commonly used for the peak POSITION -- the sub-frame depth estimate -- and
a claim about the value does not automatically transfer. This measures position
against the same dense-grid truth so the scope of step 4's finding is stated
correctly rather than assumed.

PRE-REGISTERED:
  P12  on a synthetic Gaussian, the parabola's position error grows with sample
       spacing (shrinkage toward the sampled maximum) while the log fit stays
       exact, mirroring step 4.
  P13  on real coffee-bean data at x2, the log-baseline fit reduces the median
       absolute position error relative to the parabola.
  NULL the trivial estimator "the sampled argmax itself" (offset 0) is scored
       alongside both. Any interpolator that does not beat it is worthless, and
       reporting it prevents a small improvement from looking like a large one.
"""
import numpy as np, os, json

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")
rng = np.random.default_rng(20260814)
NPIX = 40000
res = {"synthetic": {}, "real": {}}


def vertex_shift(am_, a0, ap):
    dn = am_ - 2 * a0 + ap
    ok = dn < -1e-12
    return ok, np.where(ok, -0.5 * (ap - am_) / np.where(ok, dn, 1), 0.0)


def shifts(am_, a0, ap, base=0.0):
    ok_p, sh_p = vertex_shift(am_, a0, ap)
    lo = 1e-9
    l = [np.log(np.maximum(v - base, lo)) for v in (am_, a0, ap)]
    ok_l, sh_l = vertex_shift(*l)
    return (ok_p, sh_p), (ok_l, sh_l)


# ---------------- synthetic ------------------------------------------------
N, sig = 200000, 2.0
row = {}
for h in (2.0, 4.0, 6.0):
    d = rng.uniform(-h / 2, h / 2, N)
    xs = np.stack([d - h, d, d + h])
    f = np.exp(-xs ** 2 / (2 * sig ** 2))
    j = f.argmax(0)
    inner = j == 1
    a0, am_, ap = f[1], f[0], f[2]
    (ok_p, sh_p), (ok_l, sh_l) = shifts(am_, a0, ap)
    # true peak offset from the centre sample, in sample units
    true_sh = -d / h
    g = inner & ok_p & ok_l
    row[f"h{h:g}"] = dict(
        null_abs_err_samples=float(np.median(np.abs(true_sh[g]))),
        parabola_abs_err_samples=float(np.median(np.abs(sh_p[g] - true_sh[g]))),
        log_abs_err_samples=float(np.median(np.abs(sh_l[g] - true_sh[g]))),
        parabola_shrinkage=float(np.median(sh_p[g] / np.where(np.abs(true_sh[g]) > 1e-6, true_sh[g], np.nan))),
        log_shrinkage=float(np.median(sh_l[g] / np.where(np.abs(true_sh[g]) > 1e-6, true_sh[g], np.nan))),
    )
res["synthetic"]["gaussian"] = row
print("synthetic:", json.dumps(row, indent=1))

# ---------------- real -----------------------------------------------------
V = np.load(os.path.join(CACHE, "dense_focus.npy"))
n_dense = V.shape[0]
b = 8
r2 = np.random.default_rng(20260812)
idx = (r2.integers(b, V.shape[1] - b, NPIX), r2.integers(b, V.shape[2] - b, NPIX))
D = V[:, idx[0], idx[1]].astype(np.float64)
k_dense = D.argmax(0)
ar = np.arange(NPIX)
kk = np.clip(k_dense, 1, n_dense - 2)
_, sh_t = vertex_shift(D[kk - 1, ar], D[kk, ar], D[kk + 1, ar])
tau = kk + np.clip(sh_t, -1, 1)                       # truth, in dense-frame units
interior = (k_dense >= 2) & (k_dense <= n_dense - 3)

for label, step in (("x2even", 2), ("x4", 4), ("x6", 6)):
    sel = np.arange(0, n_dense, step)
    S = D[sel]
    m = S.shape[0]
    j = S.argmax(0)
    jj = np.clip(j, 1, m - 2)
    a0, am_, ap = S[jj, ar], S[jj - 1, ar], S[jj + 1, ar]
    base = np.percentile(S, 5, axis=0)
    (ok_p, sh_p), (ok_l, sh_l) = shifts(am_, a0, ap, base)
    k_samp = sel[jj].astype(np.float64)
    g = interior & ok_p & ok_l & (j >= 1) & (j <= m - 2)
    err_null = np.abs(k_samp - tau)
    err_p = np.abs(k_samp + sh_p * step - tau)
    err_l = np.abs(k_samp + sh_l * step - tau)
    res["real"][label] = dict(
        null_abs_err_dense_frames=float(np.median(err_null[g])),
        parabola_abs_err_dense_frames=float(np.median(err_p[g])),
        log_baseline_abs_err_dense_frames=float(np.median(err_l[g])),
        parabola_gain_over_null=float(np.median(err_null[g]) / np.median(err_p[g])),
        log_gain_over_null=float(np.median(err_null[g]) / np.median(err_l[g])),
    )
    print(f"{label}: {json.dumps(res['real'][label])}")

with open(os.path.join(OUT, "05-position.json"), "w") as fh:
    json.dump(res, fh, indent=2)
