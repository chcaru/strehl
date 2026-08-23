"""M36 V09: M32's three headline numbers, independently.

  A. the no-information fixed point 0.888 (n=53) -> 0.850 (n=9), NOT H/log n = 1
  B. arm S: 0.6480 -> 0.6482 across a 6.1x evidence range, non-monotone
  C. the 142-991 sigma peak.  The orchestrator's worry: is the sigma in the
     denominator the noise on a SINGLE focus-response sample, or on something
     already averaged?  Two independent checks:
       (c1) POSITIVE CONTROL for the roughness estimator -- plant a known sigma
            on the real curve shapes and see whether it comes back.
       (c2) a fully ANALYTIC sigma_f: propagate the M4 per-pixel noise through
            sobel + 5x5 box by the delta method.  No Monte Carlo, no roughness.
"""
import numpy as np, os, json, time
from scipy.ndimage import sobel, uniform_filter, correlate

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
OUT = os.path.join(ROOT, "m36-verification", "out")
G, RN_E, R = 50/436.8, 4.20, 2
res = {}
rng = np.random.default_rng(3690)

def norm_entropy(f, T):
    z = (f - f.max(0))/np.maximum(T, 1e-12)[None, :]
    p = np.exp(np.clip(z, -700, 0)); p /= p.sum(0)
    h = -(p*np.log(np.maximum(p, 1e-300))).sum(0)
    return h/np.log(f.shape[0]), np.exp(h)

# ------------------------------------------------------------------- A: null
print("A. no-information null, softmax over n iid draws, 200k trials each")
nl = {}
for n in (53, 27, 18, 14, 9):
    for dist, draw in (("gaussian", lambda: rng.standard_normal((n, 200000))),
                       ("rayleigh", lambda: rng.rayleigh(1.0, (n, 200000)))):
        f = draw(); T = np.full(200000, f.std(0).mean())
        e, pp = norm_entropy(f, T)
        nl[f"n{n}_{dist}"] = dict(entropy=float(np.median(e)), perplexity=float(np.median(pp)),
                                  perp_over_n=float(np.median(pp)/n))
    print(f"   n={n:2d}: gaussian H/logn {nl[f'n{n}_gaussian']['entropy']:.4f}"
          f"  perp {nl[f'n{n}_gaussian']['perplexity']:.3f}"
          f"  perp/n {nl[f'n{n}_gaussian']['perp_over_n']:.3f}"
          f"   | rayleigh H/logn {nl[f'n{n}_rayleigh']['entropy']:.4f}")
res["null"] = nl

# ----------------------------------------------------------------- data load
raw = np.asarray(np.load(os.path.join(ROOT, "m32-posterior", "out", "cache", "raw.npy"),
                         mmap_mode="r"), np.float32)
n_all, HH, WW = raw.shape
foc = np.asarray(np.load(os.path.join(ROOT, "m33-subframe-offset", "out", "cache",
                                      "dense_focus.npy"), mmap_mode="r"), np.float32)[::2]
foc = np.ascontiguousarray(foc)
mean_img = raw.mean(0)
lv = uniform_filter(mean_img**2, 2*R+1) - uniform_filter(mean_img, 2*R+1)**2
tex = np.sqrt(np.maximum(lv, 0))
b = 8
inner = np.zeros(tex.shape, bool); inner[b:-b, b:-b] = True
edges = np.percentile(tex[inner], [0, 20, 40, 60, 80, 95])
bins = []
for i, e0 in enumerate(edges):
    e1 = edges[i+1] if i+1 < len(edges) else tex.max()+1
    bins.append(inner & (tex >= e0) & (tex < e1))
print(f"\n   texture bin medians (DN): " + " ".join(f"{np.median(tex[m]):.1f}" for m in bins))

def rough_sigma(f):
    d = f[:-2]-2*f[1:-1]+f[2:]
    lvl = f[1:-1]
    thr = np.percentile(lvl, 33, axis=0)[None, :]
    m = lvl <= thr
    dd = np.where(m, d, np.nan)
    mad = np.nanmedian(np.abs(dd - np.nanmedian(dd, 0)[None, :]), 0)
    return 1.4826*mad/np.sqrt(6.0)

# --------------------------------------------------- B: arm S, all pixels/bin
print("\nB. arm S (self-normalised) and arm N, per texture bin, ALL pixels in bin")
armrows = {}
for i, m in enumerate(bins):
    yy, xx = np.nonzero(m)
    k = rng.choice(yy.size, min(20000, yy.size), replace=False)
    idx = (yy[k], xx[k])
    f = foc[:, idx[0], idx[1]].astype(np.float64)
    eS, ppS = norm_entropy(f, f.std(0))
    Trg = rough_sigma(f)
    peak = f.max(0)-np.median(f, 0)
    eN, ppN = norm_entropy(f, Trg)
    armrows[f"bin{i}"] = dict(texture_dn=float(np.median(tex[idx])),
                              arm_S_entropy=float(np.median(eS)),
                              arm_S_perplexity=float(np.median(ppS)),
                              arm_N_rough_entropy=float(np.median(eN)),
                              T_roughness=float(np.median(Trg)),
                              peak_over_T_roughness=float(np.median(peak/Trg)))
    r_ = armrows[f"bin{i}"]
    print(f"   bin{i} tex {r_['texture_dn']:6.1f}  armS H {r_['arm_S_entropy']:.4f}"
          f"  perp {r_['arm_S_perplexity']:6.2f}   T_rough {r_['T_roughness']:6.2f}"
          f"  peak/T {r_['peak_over_T_roughness']:8.1f}")
res["arms"] = armrows
sv = [armrows[f"bin{i}"]["arm_S_entropy"] for i in range(6)]
print(f"   arm S across bins: min {min(sv):.4f} max {max(sv):.4f}"
      f"  monotone: {sv == sorted(sv) or sv == sorted(sv, reverse=True)}")
res["armS_monotone"] = bool(sv == sorted(sv) or sv == sorted(sv, reverse=True))

# ------------------------------------- C1: positive control for rough_sigma
print("\nC1. positive control: plant a known sigma on the real curve shapes")
sm = np.apply_along_axis(lambda a: np.convolve(a, np.ones(5)/5, mode="same"), 0,
                         foc[:, ::16, ::16].astype(np.float64).reshape(n_all, -1))
pc = {}
for s_true in (5.0, 20.0, 80.0):
    fsyn = sm + rng.standard_normal(sm.shape)*s_true
    got = float(np.median(rough_sigma(fsyn)))
    pc[f"sigma{s_true:g}"] = dict(planted=s_true, recovered=got, ratio=got/s_true)
    print(f"   planted {s_true:6.1f} -> recovered {got:7.2f}  ratio {got/s_true:.4f}")
res["rough_sigma_positive_control"] = pc

# ----------------------------------------- C2: analytic sigma_f, delta method
print("\nC2. analytic sigma_f by the delta method (no Monte Carlo)")
Kx = np.outer([1., 2., 1.], [-1., 0., 1.])
Ky = np.outer([-1., 0., 1.], [1., 2., 1.])
DE = [(dy, dx) for dy in range(-3, 4) for dx in range(-3, 4)]
HX, HY = {}, {}
for dy, dx in DE:
    hx = np.zeros((5, 5)); hy = np.zeros((5, 5))
    for ey in range(-2, 3):
        for ex in range(-2, 3):
            ay, ax = dy-ey, dx-ex
            if abs(ay) <= 1 and abs(ax) <= 1:
                hx[ey+2, ex+2] = Kx[ay+1, ax+1]; hy[ey+2, ex+2] = Ky[ay+1, ax+1]
    HX[(dy, dx)], HY[(dy, dx)] = hx, hy

def analytic_var(v, s2):
    gx = sobel(v, axis=1, mode="nearest"); gy = sobel(v, axis=0, mode="nearest")
    M = np.maximum(np.hypot(gx, gy), 1e-6)
    u, w = gx/M, gy/M
    var = np.zeros_like(v, np.float64)
    for d_ in DE:
        c = (correlate(u, HX[d_], mode="nearest") + correlate(w, HY[d_], mode="nearest"))/25.0
        var += np.roll(np.roll(s2, -d_[0], 0), -d_[1], 1)*c*c
    return var

# numerical validation of the Jacobian on a small patch
vp = np.asarray(raw[26, 400:440, 400:440], np.float64)
s2p = np.ones_like(vp)
def fx(a):
    gx = sobel(a, axis=1, mode="nearest"); gy = sobel(a, axis=0, mode="nearest")
    return uniform_filter(np.hypot(gx, gy), size=5, mode="nearest")
t = (20, 20); eps = 1e-3
num = np.zeros((7, 7))
for i, (dy, dx) in enumerate(DE):
    p = vp.copy(); p[t[0]+dy, t[1]+dx] += eps
    num[dy+3, dx+3] = (fx(p)[t]-fx(vp)[t])/eps
gx = sobel(vp, axis=1, mode="nearest"); gy = sobel(vp, axis=0, mode="nearest")
M = np.maximum(np.hypot(gx, gy), 1e-6); u, w = gx/M, gy/M
ana = np.zeros((7, 7))
for dy, dx in DE:
    c = (correlate(u, HX[(dy, dx)], mode="nearest") + correlate(w, HY[(dy, dx)], mode="nearest"))/25.0
    ana[dy+3, dx+3] = c[t]
print(f"   Jacobian check: max|analytic - finite difference| = {np.abs(ana-num).max():.3e}"
      f"   (typical |c| {np.abs(ana).mean():.3e})")
res["jacobian_check"] = float(np.abs(ana-num).max())

t0 = time.time()
acc = np.zeros((HH, WW), np.float64)
for k in range(n_all):
    v = np.asarray(raw[k], np.float64)
    s2 = G*np.clip(v, 0, None) + (RN_E*G)**2
    acc += np.sqrt(np.maximum(analytic_var(v, s2), 0))
T_ana = (acc/n_all).astype(np.float32)
print(f"   analytic sigma_f computed over {n_all} frames in {time.time()-t0:.0f}s")

rows = {}
for i, m in enumerate(bins):
    yy, xx = np.nonzero(m)
    k = np.random.default_rng(3691).choice(yy.size, min(20000, yy.size), replace=False)
    idx = (yy[k], xx[k])
    f = foc[:, idx[0], idx[1]].astype(np.float64)
    peak = f.max(0)-np.median(f, 0)
    Ta = T_ana[idx]; Tr = rough_sigma(f)
    rows[f"bin{i}"] = dict(texture_dn=float(np.median(tex[idx])),
                           T_analytic=float(np.median(Ta)), T_roughness=float(np.median(Tr)),
                           ratio_rough_over_analytic=float(np.median(Tr/Ta)),
                           peak_over_T_analytic=float(np.median(peak/Ta)),
                           peak_over_T_roughness=float(np.median(peak/Tr)))
    r_ = rows[f"bin{i}"]
    print(f"   bin{i} tex {r_['texture_dn']:6.1f}  T_ana {r_['T_analytic']:7.2f}"
          f"  T_rough {r_['T_roughness']:7.2f}  ratio {r_['ratio_rough_over_analytic']:.3f}"
          f"   peak/T_ana {r_['peak_over_T_analytic']:8.1f}"
          f"   peak/T_rough {r_['peak_over_T_roughness']:8.1f}")
res["sigma_f_comparison"] = rows

json.dump(res, open(os.path.join(OUT, "V09-m32.json"), "w"), indent=1)
print("\nwrote V09-m32.json")
