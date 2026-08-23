"""M36 V05: attack fact 281 -- C1's worst-5% lift of 0.89x on the TRUE sub-frame
deficit, i.e. the claim that predicted sigma is ANTI-informative about C3's target.

This is the load-bearing claim of M34 (no monotone scalar summary is faithful),
so it gets the hardest test I can build:

  1. reproduce the true deficit and the lift with my own code;
  2. put an error bar on it -- the report gives none, and the pixels are
     spatially correlated so the naive s.e. is wrong.  Spatial block bootstrap;
  3. SHIFT CONTROL: roll C1 by a large spatial offset.  This destroys per-pixel
     correspondence while preserving every spatial statistic of C1.  Lift must
     go to 1.0.  (discipline 17)
  4. does the sign survive a DIFFERENT DEFINITION of C1?  The acceptance set has
     median size 1.0, so C1 may just be single-frame SNR.  Five alternatives.
  5. what actually drives it -- bin the true deficit against C1 and against the
     peak height, and look at the monotonicity.
"""
import numpy as np, os, json
from scipy.stats import spearmanr
from scipy.ndimage import sobel, uniform_filter

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
CACHE34 = os.path.join(ROOT, "m34-confidence-vector", "out", "cache")
OUT = os.path.join(ROOT, "m36-verification", "out")
G, RN_E, R = 50/436.8, 4.20, 2
res = {}

dense = np.asarray(np.load(os.path.join(ROOT, "m33-subframe-offset", "out", "cache",
                                        "dense_focus.npy"), mmap_mode="r"), np.float32)
raw = np.asarray(np.load(os.path.join(ROOT, "m32-posterior", "out", "cache", "raw.npy"),
                         mmap_mode="r"), np.float32)
foc = np.ascontiguousarray(dense[::2])
n, HH, WW = foc.shape
yy, xx = np.mgrid[0:HH, 0:WW]

# ---- true deficit, M34 script 04's definition, recomputed ------------------
base_d = dense.min(0)
tp = np.maximum(dense.max(0) - base_d, 1e-6)
cp = np.maximum(foc.max(0) - base_d, 1e-6)
true_def2d = np.clip(1.0 - cp/tp, 0, 1)
true_def = true_def2d.ravel()
gmean = float(true_def.mean())
print(f"true deficit (M34 defn): mean {gmean:.6f}  median {np.median(true_def):.6f}"
      f"  exactly_zero {float((true_def==0).mean()):.4%}")
res["true_deficit_M34"] = dict(mean=gmean, median=float(np.median(true_def)),
                               exactly_zero=float((true_def == 0).mean()))

# ---- channel bank ----------------------------------------------------------
tail = np.concatenate([foc[:6], foc[-6:]], 0)
d2 = tail[2:] - 2*tail[1:-1] + tail[:-2]
sf = np.sqrt(np.maximum(d2.var(0), 1e-12)/6.0).astype(np.float32)
fmax, kmx = foc.max(0), foc.argmax(0)
vk = G*np.clip(raw, 0, None) + (RN_E*G)**2

def sigma_over_S(acc):
    na = acc.sum(0).astype(np.float32)
    return ((np.sqrt((vk*acc).sum(0))/np.maximum(na, 1)) /
            np.maximum((raw*acc).sum(0)/np.maximum(na, 1), 1e-3)).ravel()

defs = {}
for g_ in (1.0, 2.0, 3.0):
    defs[f"C1_gate{g_:g}sig"] = sigma_over_S((fmax[None]-foc) <= g_*sf[None])
one = np.zeros(foc.shape, bool); one[kmx, yy, xx] = True
defs["C1_argmax_frame_only"] = sigma_over_S(one)
ordr = np.argsort(-foc, axis=0)
top3 = np.zeros(foc.shape, bool)
for t in range(3):
    top3[ordr[t], yy, xx] = True
defs["C1_fixed_top3"] = sigma_over_S(top3)
mimg = raw.mean(0)
defs["C1_inv_snr_meanimg"] = (np.sqrt(G*np.clip(mimg, 0, None) + (RN_E*G)**2)/np.maximum(mimg, 1e-3)).ravel()
defs["C1_cached"] = np.load(os.path.join(CACHE34, "C1.npy")).ravel()
defs["C3_cached"] = np.load(os.path.join(CACHE34, "C3_fixed.npy")).ravel()
defs["C2_cached"] = np.load(os.path.join(CACHE34, "C2.npy")).ravel()

rng = np.random.default_rng(3650)
sub = rng.choice(true_def.size, 300_000, replace=False)

def lift(v, frac=0.05, r=None):
    r = r if r is not None else rng
    k = int(round(frac*v.size))
    key = v.astype(np.float64) + r.uniform(0, 1e-12, v.size)*(np.ptp(v.astype(np.float64))+1e-12)
    idx = np.argpartition(key, -k)[-k:]
    return float(true_def[idx].mean())/gmean

print("\n  channel                    spearman vs true   worst-5% lift   best-5% lift")
tbl = {}
for nm, v in defs.items():
    rho = float(spearmanr(v[sub], true_def[sub]).statistic)
    lo = lift(-v.astype(np.float64))
    tbl[nm] = dict(spearman=rho, worst5_lift=lift(v), best5_lift=lo)
    print(f"  {nm:26s} {rho:+.4f}        {tbl[nm]['worst5_lift']:.3f}x        {lo:.3f}x")
res["alternative_C1_definitions"] = tbl

# ---- error bar on the 0.89x, spatial block bootstrap -----------------------
print("\n  spatial block bootstrap on C1_cached's lift (64x64 blocks, 400 resamples)")
B = 64
nb = HH//B
c1_2d = defs["C1_cached"].reshape(HH, WW)
blocks_c1 = c1_2d.reshape(nb, B, nb, B).transpose(0, 2, 1, 3).reshape(nb*nb, B*B)
blocks_td = true_def2d.reshape(nb, B, nb, B).transpose(0, 2, 1, 3).reshape(nb*nb, B*B)
boot = []
rb = np.random.default_rng(3651)
for _ in range(400):
    sel = rb.integers(0, nb*nb, nb*nb)
    c = blocks_c1[sel].ravel(); t = blocks_td[sel].ravel()
    k = int(round(0.05*c.size))
    idx = np.argpartition(c + rb.uniform(0, 1e-12, c.size)*(np.ptp(c)+1e-12), -k)[-k:]
    boot.append(t[idx].mean()/t.mean())
boot = np.array(boot)
print(f"    lift = {tbl['C1_cached']['worst5_lift']:.4f}   bootstrap mean {boot.mean():.4f}"
      f"  sd {boot.std(ddof=1):.4f}  95% CI [{np.percentile(boot,2.5):.4f},"
      f" {np.percentile(boot,97.5):.4f}]  P(lift>=1) = {(boot>=1).mean():.4f}")
res["bootstrap_C1_lift"] = dict(point=tbl["C1_cached"]["worst5_lift"], mean=float(boot.mean()),
                                sd=float(boot.std(ddof=1)),
                                ci=[float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
                                p_ge_1=float((boot >= 1).mean()))

# ---- shift control ---------------------------------------------------------
sh = {}
for s in (128, 256, 512):
    v = np.roll(np.roll(c1_2d, s, 0), s, 1).ravel()
    sh[f"roll{s}"] = lift(v)
    print(f"  SHIFT CONTROL roll {s}px: lift {sh[f'roll{s}']:.3f}x  (must be ~1.0)")
res["shift_control"] = sh

# ---- what drives it: decile table -----------------------------------------
print("\n  decile of C1 (10 = worst) -> mean true deficit, mean peak height, mean signal")
q = np.quantile(defs["C1_cached"], np.linspace(0, 1, 11))
tab = []
for i in range(10):
    m = (defs["C1_cached"] >= q[i]) & (defs["C1_cached"] <= q[i+1] if i == 9 else defs["C1_cached"] < q[i+1])
    tab.append(dict(decile=i+1, mean_true_def=float(true_def[m].mean()),
                    mean_peak_over_base=float(tp.ravel()[m].mean()),
                    mean_signal=float(mimg.ravel()[m].mean()),
                    mean_C3=float(defs["C3_cached"][m].mean())))
    print(f"   {i+1:2d}  true_def {tab[-1]['mean_true_def']:.5f}  peak-base "
          f"{tab[-1]['mean_peak_over_base']:9.2f}  signal {tab[-1]['mean_signal']:8.1f}"
          f"  C3 {tab[-1]['mean_C3']:.5f}")
res["C1_deciles"] = tab
res["spearman_peakheight_vs_truedef"] = float(spearmanr(tp.ravel()[sub], true_def[sub]).statistic)
print(f"  spearman(peak-height, true deficit) = {res['spearman_peakheight_vs_truedef']:+.4f}")

json.dump(res, open(os.path.join(OUT, "V05-fact281.json"), "w"), indent=1)
print("wrote V05-fact281.json")
