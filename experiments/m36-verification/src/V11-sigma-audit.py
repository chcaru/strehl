"""M36 V11: THE FOCUS MEASURE M32 ACTUALLY USED, and what it does to 142-991 sigma.

scipy.ndimage.sobel(cube, axis=2) applies the [-1,0,1] derivative along axis 2 and
the [1,2,1] SMOOTHING along EVERY OTHER AXIS -- including axis 0, the FRAME axis.
M32 scripts 02/03/04 call sobel on the whole (53,1024,1024) cube, so their focus
volume is smoothed along k with [1,2,1].  M27/M33/M34 call sobel per 2-D frame and
are not.  So:

  - M32's focus volume is NOT the M27 focus measure the report says it is;
  - its noise is correlated across k, which is exactly the assumption
    rough_sigma() relies on (var of the second difference = 6 sigma^2);
  - so peak / T_roughness may be referenced to the wrong sigma.

Measure it: Monte-Carlo the TRUE sd of each focus volume under the M4 noise model
and compare against rough_sigma on the same volume.
"""
import numpy as np, os, json, time
from scipy.ndimage import sobel, uniform_filter

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
OUT = os.path.join(ROOT, "m36-verification", "out")
G, RN_E, R = 50/436.8, 4.20, 2
rng = np.random.default_rng(3711)
res = {}

raw = np.asarray(np.load(os.path.join(ROOT, "m32-posterior", "out", "cache", "raw.npy"),
                         mmap_mode="r"), np.float32)
n_all, HH, WW = raw.shape
sigma = np.sqrt(G*np.clip(raw, 0, None) + (RN_E*G)**2).astype(np.float32)

def focus3d(cube):
    gx = sobel(cube, axis=2, mode="nearest"); gy = sobel(cube, axis=1, mode="nearest")
    return uniform_filter(np.hypot(gx, gy), size=(1, 2*R+1, 2*R+1), mode="nearest")

def focus2d_cube(cube):
    out = np.empty_like(cube)
    for i in range(cube.shape[0]):
        gx = sobel(cube[i], axis=1, mode="nearest"); gy = sobel(cube[i], axis=0, mode="nearest")
        out[i] = uniform_filter(np.hypot(gx, gy), size=2*R+1, mode="nearest")
    return out

def rough_sigma(f):
    d = f[:-2]-2*f[1:-1]+f[2:]
    lvl = f[1:-1]
    thr = np.percentile(lvl, 33, axis=0)[None, :]
    m = lvl <= thr
    dd = np.where(m, d, np.nan)
    mad = np.nanmedian(np.abs(dd-np.nanmedian(dd, 0)[None, :]), 0)
    return 1.4826*mad/np.sqrt(6.0)

mean_img = raw.mean(0)
lv = uniform_filter(mean_img**2, 2*R+1)-uniform_filter(mean_img, 2*R+1)**2
tex = np.sqrt(np.maximum(lv, 0))
b = 8
inner = np.zeros(tex.shape, bool); inner[b:-b, b:-b] = True
edges = np.percentile(tex[inner], [0, 20, 40, 60, 80, 95])
idxs = []
for i, e0 in enumerate(edges):
    e1 = edges[i+1] if i+1 < len(edges) else tex.max()+1
    yy, xx = np.nonzero(inner & (tex >= e0) & (tex < e1))
    k = rng.choice(yy.size, 6000, replace=False)
    idxs.append((yy[k], xx[k]))

MC = 16
out = {}
for tag, ff in (("focus3d_M32", focus3d), ("focus2d_M27_M33_M34", focus2d_cube)):
    t0 = time.time()
    F = ff(raw)
    s1 = [np.zeros((n_all, 6000)) for _ in idxs]
    s2 = [np.zeros((n_all, 6000)) for _ in idxs]
    for _ in range(MC):
        Fz = ff(raw + rng.standard_normal(raw.shape, np.float32)*sigma)
        for j, ix in enumerate(idxs):
            z = Fz[:, ix[0], ix[1]].astype(np.float64)
            s1[j] += z; s2[j] += z*z
    rows = {}
    for j, ix in enumerate(idxs):
        Tmc = np.sqrt(np.maximum(s2[j]/MC-(s1[j]/MC)**2, 0)).mean(0)
        f = F[:, ix[0], ix[1]].astype(np.float64)
        Trg = rough_sigma(f)
        peak = f.max(0)-np.median(f, 0)
        rows[f"bin{j}"] = dict(texture_dn=float(np.median(tex[ix])),
                               T_mc=float(np.median(Tmc)), T_roughness=float(np.median(Trg)),
                               rough_over_mc=float(np.median(Trg/Tmc)),
                               peak=float(np.median(peak)),
                               peak_over_T_mc=float(np.median(peak/Tmc)),
                               peak_over_T_roughness=float(np.median(peak/Trg)))
        r_ = rows[f"bin{j}"]
        print(f"  {tag:22s} bin{j} tex {r_['texture_dn']:6.1f}  T_mc {r_['T_mc']:8.2f}"
              f"  T_rough {r_['T_roughness']:8.2f}  rough/mc {r_['rough_over_mc']:.3f}"
              f"   peak/T_mc {r_['peak_over_T_mc']:8.1f}"
              f"   peak/T_rough {r_['peak_over_T_roughness']:8.1f}")
    out[tag] = rows
    print(f"    [{time.time()-t0:.0f}s]")
res["sigma_audit"] = out

lo3 = out["focus3d_M32"]["bin0"]; hi3 = out["focus3d_M32"]["bin5"]
lo2 = out["focus2d_M27_M33_M34"]["bin0"]; hi2 = out["focus2d_M27_M33_M34"]["bin5"]
res["summary"] = dict(
    M32_as_published_peak_over_rough=[lo3["peak_over_T_roughness"], hi3["peak_over_T_roughness"]],
    M32_volume_correct_sigma=[lo3["peak_over_T_mc"], hi3["peak_over_T_mc"]],
    M27_volume_correct_sigma=[lo2["peak_over_T_mc"], hi2["peak_over_T_mc"]],
    M27_volume_rough=[lo2["peak_over_T_roughness"], hi2["peak_over_T_roughness"]])
print("\n  SUMMARY of the '142-991 sigma' claim:")
for k, v in res["summary"].items():
    print(f"    {k:34s} {v[0]:8.1f} - {v[1]:8.1f}")

json.dump(res, open(os.path.join(OUT, "V11-sigma-audit.json"), "w"), indent=1)
print("wrote V11-sigma-audit.json")
