"""M36 V08: M33 findings 2 and 3 -- the parabola's peak-HEIGHT anti-correlation,
the log-domain fix, and the position scope limit.  Re-implemented from the
formulas, own RNG, own seeds.
"""
import numpy as np, os, json
ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
OUT = os.path.join(ROOT, "m36-verification", "out")
res = {"synthetic": {}, "real": {}, "position": {}}
rng = np.random.default_rng(3680)

def vertex(am_, a0, ap):
    dn = am_-2*a0+ap
    ok = dn < -1e-12
    xs = np.where(ok, -0.5*(ap-am_)/np.where(ok, dn, 1.0), 0.0)
    return ok, xs, np.where(ok, a0+0.25*(ap-am_)*xs, a0)

def pred(am_, a0, ap, mode, base=0.0):
    if mode == "parabola":
        ok, xs, pk = vertex(am_, a0, ap)
        return ok, xs, 1-a0/np.maximum(pk, 1e-12)
    lo = 1e-9
    x0, x1, x2 = (np.maximum(am_-base, lo), np.maximum(a0-base, lo), np.maximum(ap-base, lo))
    ok, xs, pk = vertex(np.log(x0), np.log(x1), np.log(x2))
    return ok, xs, 1-x1/np.maximum(np.exp(pk), 1e-12)

# ------------------------------------------------------------- synthetic
N, sg = 200000, 2.0
for shape in ("gaussian", "parabola"):
    row = {}
    for h in (2.0, 4.0, 6.0):
        d = rng.uniform(-h/2, h/2, N)
        xs_ = np.stack([d-h, d, d+h])
        f = np.exp(-xs_**2/(2*sg**2)) if shape == "gaussian" \
            else np.maximum(1-xs_**2/(2*sg**2), 1e-6)
        a0 = f[1]; am_ = f[0]; ap = f[2]
        clamped = float((f <= 1e-6+1e-12).any(0).mean())
        td = 1-a0
        okp, _, pdp = pred(am_, a0, ap, "parabola")
        okl, _, pdl = pred(am_, a0, ap, "log")
        row[f"h{h:g}"] = dict(true_pct=float(100*np.median(td)),
                              parab_pct=float(100*np.median(pdp[okp])),
                              parab_ratio=float(np.median(pdp[okp]/td[okp])),
                              log_pct=float(100*np.median(pdl[okl])),
                              log_ratio=float(np.median(pdl[okl]/td[okl])),
                              frac_outer_sample_clamped=clamped)
        print(f"  {shape:9s} h={h:g}: true {100*np.median(td):7.3f}%  parab "
              f"{100*np.median(pdp[okp]):7.3f}% (r {np.median(pdp[okp]/td[okp]):.4f})"
              f"  log {100*np.median(pdl[okl]):7.3f}% (r {np.median(pdl[okl]/td[okl]):.4f})"
              f"  clamped {clamped:.1%}")
    res["synthetic"][shape] = row
g = res["synthetic"]["gaussian"]
print(f"  parabola prediction falls {g['h2']['parab_pct']/g['h6']['parab_pct']:.1f}x"
      f" while truth rises {g['h6']['true_pct']/g['h2']['true_pct']:.1f}x")
res["synthetic"]["parabola_fall_x"] = float(g['h2']['parab_pct']/g['h6']['parab_pct'])
res["synthetic"]["truth_rise_x"] = float(g['h6']['true_pct']/g['h2']['true_pct'])

# ------------------------------------------------------------------- real
V = np.asarray(np.load(os.path.join(ROOT, "m33-subframe-offset", "out", "cache",
                                    "dense_focus.npy"), mmap_mode="r"), np.float32)
nd, HH, WW = V.shape
# ALL pixels, not a 40k sample
D = V.reshape(nd, -1).astype(np.float64)
NP = D.shape[1]
ar = np.arange(NP)
fdm = D.max(0); kd = D.argmax(0)
interior = (kd >= 2) & (kd <= nd-3)
kk = np.clip(kd, 1, nd-2)
_, sh_t, _ = vertex(D[kk-1, ar], D[kk, ar], D[kk+1, ar])
tau = kk + np.clip(sh_t, -1, 1)

for label, step in (("x2even", 2), ("x4", 4), ("x6", 6)):
    sel = np.arange(0, nd, step)
    S = D[sel]; m = S.shape[0]
    j = S.argmax(0); fm = S.max(0)
    td = 1-fm/fdm
    jj = np.clip(j, 1, m-2)
    a0, am_, ap = S[jj, ar], S[jj-1, ar], S[jj+1, ar]
    bp5 = np.percentile(S, 5, axis=0)
    row = {}
    for mode, bs in (("parabola", 0.0), ("log", 0.0), ("log_baseline", bp5)):
        ok, shp, pd = pred(am_, a0, ap, "parabola" if mode == "parabola" else "log", bs)
        gsel = interior & ok & (j >= 1) & (j <= m-2) & (td > 1e-12)
        r = pd[gsel]/td[gsel]
        row[mode] = dict(pred_median_pct=float(100*np.median(pd[gsel])),
                         calib_ratio_median=float(np.median(r)),
                         frac_within_2x=float(((r > 0.5) & (r < 2.0)).mean()))
        print(f"  real {label} {mode:13s} pred {100*np.median(pd[gsel]):6.3f}%"
              f"  ratio {np.median(r):.4f}  within2x {((r>0.5)&(r<2.0)).mean():.4f}")
    row["true_median_pct"] = float(100*np.median(td[interior & (td > 1e-12)]))
    res["real"][label] = row

    # ---- position
    k_samp = sel[jj].astype(np.float64)
    okp, shp, _ = pred(am_, a0, ap, "parabola")
    okl, shl, _ = pred(am_, a0, ap, "log", bp5)
    gp = interior & okp & okl & (j >= 1) & (j <= m-2)
    en = np.abs(k_samp-tau); ep = np.abs(k_samp+shp*step-tau); el = np.abs(k_samp+shl*step-tau)
    res["position"][label] = dict(null=float(np.median(en[gp])), parabola=float(np.median(ep[gp])),
                                  log=float(np.median(el[gp])),
                                  parab_gain=float(np.median(en[gp])/np.median(ep[gp])),
                                  log_gain=float(np.median(en[gp])/np.median(el[gp])),
                                  log_over_parab=float(1-np.median(el[gp])/np.median(ep[gp])))
    print(f"  posn {label}: null {np.median(en[gp]):.4f}  parab {np.median(ep[gp]):.4f}"
          f"  log {np.median(el[gp]):.4f}   parab gain {np.median(en[gp])/np.median(ep[gp]):.3f}x"
          f"  log better by {100*(1-np.median(el[gp])/np.median(ep[gp])):.1f}%")

json.dump(res, open(os.path.join(OUT, "V08-m33-estimators.json"), "w"), indent=1)
print("wrote V08-m33-estimators.json")
