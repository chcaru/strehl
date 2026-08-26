"""RIM / HALO instrument, v3.  Two prior versions FAILED and are kept on record.

  v1 normalised by end plateaus with no step test -> +428% on a clean image.
     Broken: it was measuring its own denominator on thin lines.
  v2 added a step test but took the rim OF THE MEDIAN PROFILE.  Edges differ in
     sub-pixel phase and sharpness, so the median smears any rim away: a real
     Lightroom USM(40, r=1.0) moved it by +0.02%.  NO POWER -> inadmissible.

  v3 measures the rim PER EDGE in the plateau shoulders and takes the median of
     that, which is where a rim actually lives:
        lo = mean(p[t=-12..-9]),  hi = mean(p[t=+9..+12]),  step = hi - lo
        q  = (p - lo)/step
        bright rim = max(q[t=+2..+7]) - 1        dark rim = -min(q[t=-7..-2])
     A monotone edge scores 0 by construction; only an over/undershoot scores.

FOOLING DIRECTIONS.  (a) Noise inflates a max-based excursion, and PRIOR is the
noisier arm, so this biases TOWARD finding rims in prior -- the median over many
edges plus the plateau-flatness test is the mitigation, and the residual bias is
stated in the report.  (b) A clipped plateau cannot overshoot; prior's
background is 32% blown, so clipped ROIs are dropped.  (c) Ramps have no power;
edges are drawn from detail ROIs by gradient percentile.

RULE 20 -- the input that makes this FAIL: prior + USM(40, r=1.0) must score
clearly above prior.  If it does not, v3 joins v1 and v2 as inadmissible.
"""
import numpy as np, arms, h2h, json
from scipy import ndimage
R = 12

def rim_stats(g, clip, rois, T, nmax_per_roi=300, seed=11):
    rng = np.random.default_rng(seed); tt = np.arange(-R, R+1)
    iB = np.where((tt >= 2) & (tt <= 7))[0]; iD = np.where((tt >= -7) & (tt <= -2))[0]
    ov, un, profs = [], [], []
    for (y, x) in rois:
        t = g[y:y+T, x:x+T]
        if clip[y:y+T, x:x+T].any(): continue
        sm = ndimage.uniform_filter(t, 3); gy, gx = np.gradient(sm); mag = np.hypot(gx, gy)
        ys, xs = np.nonzero(mag > np.percentile(mag, 99.0))
        keep = (ys > R+2) & (ys < T-R-2) & (xs > R+2) & (xs < T-R-2)
        ys, xs = ys[keep], xs[keep]
        if len(ys) == 0: continue
        if len(ys) > nmax_per_roi:
            i = rng.choice(len(ys), nmax_per_roi, replace=False); ys, xs = ys[i], xs[i]
        for yy, xx in zip(ys, xs):
            d = np.array([gx[yy, xx], gy[yy, xx]]); n = np.hypot(*d)
            if n < 1e-12: continue
            d /= n
            p = t[np.round(yy+d[1]*tt).astype(int), np.round(xx+d[0]*tt).astype(int)]
            lo, hi = p[:4].mean(), p[-4:].mean(); step = hi - lo
            if step <= 0: continue
            if p[:4].std() > 0.20*step or p[-4:].std() > 0.20*step: continue
            q = (p - lo)/step
            if abs(q[R]-0.5) > 0.35: continue        # the transition is centred
            ov.append(q[iB].max()-1.0); un.append(-q[iD].min()); profs.append(q)
    if not ov: return None
    return (np.median(ov), np.median(un), len(ov),
            np.median(np.array(profs), axis=0),
            np.percentile(ov, 90), np.percentile(un, 90))

def rep(name, s):
    if s is None: print(f"  {name:<42} NONE"); return None
    print(f"  {name:<42} n={s[2]:>6}  bright rim {s[0]*100:+6.2f}% (p90 {s[4]*100:+6.2f}%)"
          f"   dark rim {s[1]*100:+6.2f}% (p90 {s[5]*100:+6.2f}%)")
    return dict(n=int(s[2]), bright=float(s[0]), dark=float(s[1]),
                bright_p90=float(s[4]), dark_p90=float(s[5]))

if __name__ == "__main__":
    import shapegrid
    T = 256; P = arms.prior_arm(); rois = shapegrid.grid_rois(P, T); out = {}
    print(f"detail ROIs: {len(rois)}\n=== NULL CONTROL ===")
    a = rim_stats(P.g, P.clip, rois, T); b = rim_stats(arms.clone_arm(P).g, P.clip, rois, T)
    out["null_a"] = rep("prior", a); out["null_b"] = rep("clone of prior", b)
    print(f"  identical: bright {a[0]==b[0]}  dark {a[1]==b[1]}  n {a[2]==b[2]}\n")
    print("=== POSITIVE CONTROL (rule 20): Lightroom-default USM amount 40 radius 1.0 ===")
    usm = np.clip(P.g + 0.40*(P.g - ndimage.gaussian_filter(P.g, 1.0)), 0, None).astype(np.float32)
    c = rim_stats(usm, P.clip, rois, T); out["pos_usm"] = rep("prior + USM(40, r=1.0)", c); del usm
    print("\n=== POSITIVE CONTROL 2: a strong halo, USM amount 100 radius 2.0 ===")
    usm2 = np.clip(P.g + 1.00*(P.g - ndimage.gaussian_filter(P.g, 2.0)), 0, None).astype(np.float32)
    c2 = rim_stats(usm2, P.clip, rois, T); out["pos_usm2"] = rep("prior + USM(100, r=2.0)", c2); del usm2
    print("\n=== SCALE-CONFOUND CONTROL ===")
    RS = arms.rescale_arm(P, h2h.SCALE); d = rim_stats(RS.g, RS.clip, rois, T)
    out["scale"] = rep("prior crop+Catmull-Rom upscale", d); del RS
    print("\n=== REAL ===")
    S = arms.strehl_arm(); Ts = int(round(T*h2h.SCALE)); sr = []
    for (y, x) in rois:
        sx, sy = h2h.prior_to_strehl(x+T/2.0, y+T/2.0)
        yy, xx = int(round(sy-Ts/2)), int(round(sx-Ts/2))
        if yy >= 0 and xx >= 0 and yy+Ts <= S.g.shape[0] and xx+Ts <= S.g.shape[1]: sr.append((yy, xx))
    e = rim_stats(S.g, S.clip, sr, Ts)
    out["real_prior"] = rep("PRIOR  (focus-stack fork, Lightroom TIFFs)", a)
    out["real_strehl"] = rep("STREHL (SHIP-V2, from ARW)", e)
    print("\n  median normalised step profile, t = -8..+8")
    for nm, s in (("prior ", a), ("strehl", e), ("usm40 ", c), ("usm100", c2), ("rescal", d)):
        print(f"   {nm}:", " ".join(f"{v:+.3f}" for v in s[3][R-8:R+9]))
    json.dump(out, open("rim_results.json", "w"), indent=1)
