"""M36 V03: attack M34's reliability ceiling (C1 0.7642, C2 0.6948, C3 0.7352).

Three separate attacks.

  1. EXACTNESS.  Script 03 re-implements the channels from the raw cube.  Does
     channels(raw) reproduce the cached C1/C2/C3_fixed that the cross-channel
     numbers were computed from?  If not, the ceiling is a ceiling for a
     different statistic.
  2. SENSITIVITY.  The ceiling is measured at one arbitrary extra-noise level
     (1x).  Sweep it.  If the ceiling is a property of the channel it should not
     be a strong function of a knob the experimenter chose.
  3. THE "LOWER BOUND" ARGUMENT.  Both arms are raw + independent draw, so both
     arms SHARE the original noise realisation n0.  Shared noise makes the arms
     AGREE.  The report argues the sqrt(2)x noise makes the number a lower bound
     and does not consider the shared component at all.
     NULL CONTROL that decides it: a scene-free cube (constant level + M4 noise)
     has NO reproducible channel signal whatsoever, so its true reliability is
     chance (0.0256).  Run the author's protocol on it.  Whatever it returns
     above chance is pure shared-noise inflation.
     POSITIVE CONTROL: identical arms must return 1.0.
"""
import numpy as np, os, json, time
from scipy.ndimage import sobel, uniform_filter

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
CACHE34 = os.path.join(ROOT, "m34-confidence-vector", "out", "cache")
OUT = os.path.join(ROOT, "m36-verification", "out")
G, RN_E, R = 50/436.8, 4.20, 2
CHANCE = 0.05*0.05/(0.10-0.0025)
res = {}

def channels(cube):
    """C1, C2, C3 exactly as M34 defines them (script 01 + script 02's sign fix)."""
    cube = np.asarray(cube, np.float32)
    nn, HH, WW = cube.shape
    foc = np.empty_like(cube)
    for i in range(nn):
        gx = sobel(cube[i], axis=1, mode="nearest"); gy = sobel(cube[i], axis=0, mode="nearest")
        foc[i] = uniform_filter(np.hypot(gx, gy), size=2*R+1, mode="nearest")
    yy, xx = np.mgrid[0:HH, 0:WW]
    tail = np.concatenate([foc[:6], foc[-6:]], 0)
    d2 = tail[2:] - 2*tail[1:-1] + tail[:-2]
    sf = np.sqrt(np.maximum(d2.var(0), 1e-12)/6.0).astype(np.float32)
    fmax, kmax = foc.max(0), foc.argmax(0)
    d = (fmax[None]-foc)/np.maximum(sf, 1e-6)[None]
    lp = -0.5*d.astype(np.float64)**2; lp -= lp.max(0)
    p = np.exp(lp); p /= p.sum(0)
    c2 = np.exp(-(p*np.log(np.maximum(p, 1e-300))).sum(0)).astype(np.float32)
    del d, lp, p
    acc = (fmax[None]-foc) <= sf[None]
    na = acc.sum(0).astype(np.float32)
    vk = G*np.clip(cube, 0, None) + (RN_E*G)**2
    c1 = (np.sqrt((vk*acc).sum(0))/np.maximum(na, 1)) / \
         np.maximum((cube*acc).sum(0)/np.maximum(na, 1), 1e-3)
    base = foc.min(0); km = np.clip(kmax, 1, nn-2)
    a0  = np.log(np.maximum(foc[km,   yy, xx]-base, 1e-6))
    am_ = np.log(np.maximum(foc[km-1, yy, xx]-base, 1e-6))
    ap  = np.log(np.maximum(foc[km+1, yy, xx]-base, 1e-6))
    den = am_-2*a0+ap; ok = den < -1e-9
    xs = np.clip(np.where(ok, 0.5*(am_-ap)/np.where(ok, den, 1.0), 0.0), -1, 1)
    pk = a0 + 0.25*(ap-am_)*xs
    c3 = np.clip(1.0-np.exp(np.minimum(a0-pk, 0.0)), 0, 1).astype(np.float32)
    c3[~ok] = 0.0
    return c1.ravel(), c2.ravel(), c3.ravel()

def worst(v, seed=7, frac=0.05):
    r = np.random.default_rng(seed)
    k = int(round(frac*v.size))
    key = v.astype(np.float64) + r.uniform(0, 1e-12, v.size)*(np.ptp(v.astype(np.float64))+1e-12)
    return set(np.argpartition(key, -k)[-k:].tolist())

def J(a, b):
    return len(a & b)/len(a | b)

raw = np.asarray(np.load(os.path.join(ROOT, "m32-posterior", "out", "cache", "raw.npy"),
                         mmap_mode="r"), np.float32)
noise_sd = np.sqrt(G*np.clip(raw, 0, None) + (RN_E*G)**2).astype(np.float32)
print(f"M4 noise sd on this cube: median {np.median(noise_sd):.4f} DN"
      f"  (median signal {np.median(raw):.1f} DN -> SNR {np.median(raw)/np.median(noise_sd):.1f})")
res["noise_sd_median_dn"] = float(np.median(noise_sd))
res["median_signal_dn"] = float(np.median(raw))

# ------------------------------------------------------------- 1. exactness
t0 = time.time()
c1, c2, c3 = channels(raw)
ref = {n: np.load(os.path.join(CACHE34, f"{n}.npy")).ravel()
       for n in ("C1", "C2", "C3_fixed")}
ex = {}
for nm, mine, r_ in (("C1", c1, ref["C1"]), ("C2", c2, ref["C2"]), ("C3", c3, ref["C3_fixed"])):
    ex[nm] = dict(max_abs=float(np.abs(mine-r_).max()),
                  identical=bool(np.array_equal(mine, r_)),
                  worst5_jaccard=J(worst(mine), worst(r_)))
    print(f"  channels(raw) {nm}: max|d| {np.abs(mine-r_).max():.6g}  identical "
          f"{np.array_equal(mine, r_)}  worst5 J vs cache {ex[nm]['worst5_jaccard']:.6f}")
res["exactness_vs_cache"] = ex
print(f"  [{time.time()-t0:.0f}s]")

# --------------------------------------------------- 2/3. ceiling protocols
def ceiling(cube_a_fn, cube_b_fn, tag):
    a = channels(cube_a_fn()); b = channels(cube_b_fn())
    out = {}
    for i, nm in enumerate(["C1", "C2", "C3"]):
        out[nm] = J(worst(a[i]), worst(b[i]))
    print(f"  {tag:44s} C1 {out['C1']:.4f}  C2 {out['C2']:.4f}  C3 {out['C3']:.4f}")
    return out

rng = np.random.default_rng(36036)
sweep = {}
for v in (0.25, 0.5, 1.0, 2.0):
    n1 = rng.standard_normal(raw.shape, np.float32)*noise_sd*v
    n2 = rng.standard_normal(raw.shape, np.float32)*noise_sd*v
    sweep[f"extra_noise_x{v}"] = ceiling(lambda: raw+n1, lambda: raw+n2,
                                         f"real cube, extra noise x{v}")
    del n1, n2
res["ceiling_sweep_real"] = sweep

# positive control: identical arms
res["positive_control_identical_arms"] = ceiling(lambda: raw, lambda: raw,
                                                 "POSITIVE CONTROL identical arms")

# NULL CONTROL: a scene-free cube.  True reliability of every channel = chance.
lvl = float(np.median(raw))
sd0 = float(np.sqrt(G*lvl + (RN_E*G)**2))
flat_true = np.full(raw.shape, lvl, np.float32)
flat_obs = flat_true + rng.standard_normal(raw.shape, np.float32)*sd0   # the "captured" cube
print(f"\n  scene-free cube: level {lvl:.1f} DN, sd {sd0:.3f} DN")
na = rng.standard_normal(raw.shape, np.float32)*sd0
nb = rng.standard_normal(raw.shape, np.float32)*sd0
res["null_authors_protocol_on_scene_free"] = ceiling(
    lambda: flat_obs+na, lambda: flat_obs+nb, "NULL author's protocol, scene-free cube")
del na, nb
ma = rng.standard_normal(raw.shape, np.float32)*sd0
mb = rng.standard_normal(raw.shape, np.float32)*sd0
res["null_true_retest_on_scene_free"] = ceiling(
    lambda: flat_true+ma, lambda: flat_true+mb, "NULL true retest, scene-free cube")
del ma, mb, flat_true, flat_obs
res["chance"] = CHANCE
print(f"  (chance level for reference: {CHANCE:.4f})")

json.dump(res, open(os.path.join(OUT, "V03-ceiling.json"), "w"), indent=1)
print("\nwrote V03-ceiling.json")
