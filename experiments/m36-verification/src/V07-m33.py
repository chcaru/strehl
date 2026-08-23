"""M36 V07: M33's headline numbers, recomputed from the dense volume with my own
code, on ALL 1,048,576 pixels rather than the author's 40,000-pixel sample.

Targets:
  1. "48.7% of pixels miss their peak"  (report prose) vs the JSON field
     frac_peak_sampled_exactly = 0.4869.  One of the two is inverted.
  2. conditional median 4.64%, p90 10.74%, p99 17.34%, all-pixel mean 2.753%.
  3. the M33 (2.753%) vs M34 (2.876%) ground-truth gap: decompose it exactly
     into (a) baseline subtraction and (b) pixel population.
  4. P7 GROUND-TRUTH ADEQUACY.  The dense grid's own deficit (0.711%) was
     estimated with the PARABOLA -- the very estimator this milestone proves
     under-predicts the deficit by ~2x at x2 and 14x at x4.  Re-estimate it with
     the log+baseline fit and recompute the 3.87x adequacy ratio.
  5. parabola vs log fit, synthetic and real, re-implemented.
  6. peak POSITION: null 0.517, parabola 0.128, log 0.116.
"""
import numpy as np, os, json
from scipy.stats import spearmanr

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
OUT = os.path.join(ROOT, "m36-verification", "out")
V = np.asarray(np.load(os.path.join(ROOT, "m33-subframe-offset", "out", "cache",
                                    "dense_focus.npy"), mmap_mode="r"), np.float32)
nd, HH, WW = V.shape
res = {}

def vertex(am_, a0, ap):
    """x* and vertex VALUE for samples at -1,0,1.  b=(ap-am)/2, c=(ap-2a0+am)/2,
    x* = -b/2c, value = a0 - b^2/4c = a0 + 0.25*(ap-am)*x*."""
    dn = am_ - 2*a0 + ap
    ok = dn < -1e-12
    xs = np.where(ok, -0.5*(ap-am_)/np.where(ok, dn, 1.0), 0.0)
    return ok, xs, np.where(ok, a0 + 0.25*(ap-am_)*xs, a0)

# --- algebraic check of the vertex formula against a brute-force fit --------
rr = np.random.default_rng(3700)
A = rr.normal(size=(5, 20000)); a0 = np.abs(A[0])+2; am_ = a0-np.abs(A[1]); ap = a0-np.abs(A[2])
ok, xs, pk = vertex(am_, a0, ap)
co = np.polyfit([-1.0, 0.0, 1.0], np.stack([am_, a0, ap]), 2)
xs_ref = -co[1]/(2*co[0]); pk_ref = np.polyval(co, xs_ref)[np.arange(20000), np.arange(20000)] \
    if False else (co[0]*xs_ref**2 + co[1]*xs_ref + co[2])
print(f"vertex formula vs polyfit: max|dx*| {np.abs(xs-xs_ref).max():.3g}"
      f"  max|dvalue| {np.abs(pk-pk_ref).max():.3g}")
res["vertex_formula_check"] = dict(max_dx=float(np.abs(xs-xs_ref).max()),
                                   max_dvalue=float(np.abs(pk-pk_ref).max()))
# and the SIGN-FLIPPED form script 01/M33-02 used, to show it is not the vertex
pk_bad = np.where(ok, a0 - 0.25*(ap-am_)*xs, a0)
print(f"   sign-flipped form: it is BELOW the sampled max for "
      f"{float((pk_bad < a0).mean()):.2%} of cases (a true vertex is never below)")
res["signflip_below_max_frac"] = float((pk_bad < a0).mean())

# --------------------------------------------------------- 1-3: the deficits
f_dense_max = V.max(0)
k_dense = V.argmax(0)
base_min = V.min(0)
r2 = np.random.default_rng(20260812)            # M33's pixel sample, reproduced
b = 8
idx = (r2.integers(b, HH-b, 40000), r2.integers(b, WW-b, 40000))
interior_full = (k_dense >= 2) & (k_dense <= nd-3)

def arms_stats(step, phase=0, pix=None, baseline=False):
    sel = np.arange(phase, nd, step)
    if pix is None:
        S = V[sel]; fdm = f_dense_max; bs = base_min; inter = interior_full
    else:
        S = V[sel][:, pix[0], pix[1]]; fdm = f_dense_max[pix]; bs = base_min[pix]
        inter = interior_full[pix]
    fm = S.max(0)
    if baseline:
        ret = np.maximum(fm-bs, 1e-6)/np.maximum(fdm-bs, 1e-6)
    else:
        ret = fm/fdm
    td = np.clip(1-ret, 0, 1)
    exact = ret >= 1.0-1e-12
    g = inter
    return dict(frac_exact=float(exact[g].mean()), frac_miss=float((~exact[g]).mean()),
                mean_all_pct=float(100*td[g].mean()),
                cond_median_pct=float(100*np.percentile(td[g & ~exact], 50)),
                cond_p90_pct=float(100*np.percentile(td[g & ~exact], 90)),
                cond_p99_pct=float(100*np.percentile(td[g & ~exact], 99)))

print("\n1-2. x2 even, no baseline, M33's 40k interior sample:")
a = arms_stats(2, 0, idx, False); print("   ", json.dumps(a, indent=None))
res["m33_repro_40k"] = a
print("    x2 even, no baseline, ALL 1,048,576 pixels:")
a2 = arms_stats(2, 0, None, False); print("   ", json.dumps(a2, indent=None))
res["m33_all_pixels"] = a2
print("    x2 odd:")
res["m33_odd_40k"] = arms_stats(2, 1, idx, False); print("   ", json.dumps(res["m33_odd_40k"]))
for st in (4, 6):
    res[f"m33_x{st}_40k"] = arms_stats(st, 0, idx, False)
    print(f"    x{st}: {json.dumps(res[f'm33_x{st}_40k'])}")

print("\n3. M33 (2.753%) vs M34 (2.876%) -- decomposition")
grid = {}
for pop, pix in (("40k_interior_sample", idx), ("all_pixels", None)):
    for bl in (False, True):
        s = arms_stats(2, 0, pix, bl)
        grid[f"{pop}|baseline={bl}"] = s["mean_all_pct"]
        print(f"    {pop:20s} baseline={str(bl):5s} -> mean {s['mean_all_pct']:.4f}%"
              f"   exact {s['frac_exact']:.4%}")
# M34's exact form: ALL pixels, baseline, NO interior restriction
tp = np.maximum(V.max(0)-base_min, 1e-6); cp = np.maximum(V[::2].max(0)-base_min, 1e-6)
tdm34 = np.clip(1-cp/tp, 0, 1)
grid["M34_exact_form_no_interior"] = float(100*tdm34.mean())
print(f"    M34's exact form (all px, baseline, no interior cut) -> "
      f"{100*tdm34.mean():.4f}%   exactly_zero {float((tdm34==0).mean()):.4%}")
res["reconciliation"] = grid

# ------------------------------------------------ 4: P7 ground-truth adequacy
print("\n4. P7 adequacy: the dense grid's own deficit, parabola vs log+baseline")
D = V[:, idx[0], idx[1]].astype(np.float64)
ar = np.arange(40000)
def own_deficit(S, base=None):
    m = S.shape[0]
    j = S.argmax(0); jj = np.clip(j, 1, m-2)
    a0_, am2, ap2 = S[jj, ar], S[jj-1, ar], S[jj+1, ar]
    if base is None:
        ok, _, pk = vertex(am2, a0_, ap2)
        return ok & (j >= 1) & (j <= m-2), 1 - a0_/np.maximum(pk, 1e-12)
    lo = 1e-9
    x0, x1, x2 = (np.maximum(am2-base, lo), np.maximum(a0_-base, lo), np.maximum(ap2-base, lo))
    ok, _, pk = vertex(np.log(x0), np.log(x1), np.log(x2))
    return ok & (j >= 1) & (j <= m-2), 1 - x1/np.maximum(np.exp(pk), 1e-12)
p7 = {}
for lab, S in (("x1_dense", D), ("x2even", D[::2])):
    bp5 = np.percentile(S, 5, axis=0)
    for mode, bs in (("parabola", None), ("log_baseline", bp5), ("log_min", S.min(0))):
        ok, pd = own_deficit(S, bs)
        g = interior_full[idx] & ok
        p7[f"{lab}|{mode}"] = float(100*pd[g].mean())
        print(f"    {lab:9s} {mode:13s} predicted mean deficit {100*pd[g].mean():.4f}%")
true_x2 = res["m33_repro_40k"]["mean_all_pct"]
for mode in ("parabola", "log_baseline", "log_min"):
    r_ = true_x2/p7[f"x1_dense|{mode}"]
    p7[f"adequacy_ratio_{mode}"] = float(r_)
    print(f"    adequacy ratio using {mode:13s}: {true_x2:.3f}% / {p7[f'x1_dense|{mode}']:.3f}%"
          f" = {r_:.2f}x   (P7 threshold 3x: {'PASS' if r_>=3 else 'FAIL'})")
res["P7"] = p7

json.dump(res, open(os.path.join(OUT, "V07-m33.json"), "w"), indent=1)
print("\nwrote V07-m33.json")
