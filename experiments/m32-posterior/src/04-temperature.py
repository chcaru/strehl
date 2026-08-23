"""M32 step 4: validate the temperature model-free, then read the sweep as perplexity.

Everything in step 3 rests on T, the noise sd of the focus response, which came
from a Monte Carlo that uses the observed frames as a proxy for the noise-free
scene.  The load-bearing number -- a through-focus peak at 119-728 T -- is only
as good as T, so it needs an estimate that shares none of that machinery.

The independent estimate uses the focus curve's own along-k roughness.  For a
smooth curve plus iid noise, the second difference D_k = f_{k-1} - 2 f_k + f_{k+1}
has variance 6 sigma_f^2 plus a curvature term.  Evaluated on the DEFOCUSED tail
of the curve, where the through-focus response is flat, the curvature term is
negligible and a robust scale of D gives sigma_f directly from the data, with no
noise model, no Monte Carlo and no added noise.

PRE-REGISTERED:
  P8   T_mc and T_roughness agree within a factor of 2 (median ratio in
       [0.5, 2.0]).  A factor-2 disagreement would still leave the step-3
       conclusion intact -- 119 T becomes 60 T -- so the falsifying threshold
       here is deliberately loose and stated in advance: the claim dies only if
       they disagree by more than ~100x, which is the factor needed to bring the
       LEAST textured bin's peak down to the null.
  P9   the peak-over-noise ratio computed with T_roughness stays above 20 in
       every texture bin.
"""
import numpy as np, os, json
from scipy.ndimage import sobel, uniform_filter

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")
G, RN_E, R = 50 / 436.8, 4.20, 2
rng = np.random.default_rng(20260811)
MC, NP = 12, 6000

raw = np.load(os.path.join(CACHE, "raw.npy"))
n_all = raw.shape[0]
sigma = np.sqrt(G * np.clip(raw, 0, None) + (RN_E * G) ** 2).astype(np.float32)


def focus(cube):
    gx = sobel(cube, axis=2, mode="nearest")
    gy = sobel(cube, axis=1, mode="nearest")
    return uniform_filter(np.hypot(gx, gy), size=(1, 2 * R + 1, 2 * R + 1), mode="nearest")


def rough_sigma(f):
    """Model-free sigma of the focus response, from along-k second differences
    evaluated on the defocused tail of each pixel's curve."""
    d = f[:-2] - 2 * f[1:-1] + f[2:]                       # (n-2, P)
    lvl = f[1:-1]
    thr = np.percentile(lvl, 33, axis=0)[None, :]
    m = lvl <= thr                                          # defocused tail only
    dd = np.where(m, d, np.nan)
    mad = np.nanmedian(np.abs(dd - np.nanmedian(dd, 0)[None, :]), 0)
    return 1.4826 * mad / np.sqrt(6.0)


f_all = focus(raw)
mean_img = raw.mean(0)
lv = uniform_filter(mean_img ** 2, 2 * R + 1) - uniform_filter(mean_img, 2 * R + 1) ** 2
tex = np.sqrt(np.maximum(lv, 0))
b = 8
inner = np.zeros(tex.shape, bool); inner[b:-b, b:-b] = True
edges = np.percentile(tex[inner], [0, 20, 40, 60, 80, 95])

res = {"temperature": {}, "sweep_as_perplexity": {}}
for i, e0 in enumerate(edges):
    e1 = edges[i + 1] if i + 1 < len(edges) else tex.max() + 1
    yy, xx = np.nonzero(inner & (tex >= e0) & (tex < e1))
    k = rng.choice(yy.size, min(NP, yy.size), replace=False)
    idx = (yy[k], xx[k])
    s1 = np.zeros((n_all, idx[0].size)); s2 = np.zeros_like(s1)
    for _ in range(MC):
        fz = focus(raw + rng.standard_normal(raw.shape, np.float32) * sigma)[:, idx[0], idx[1]]
        s1 += fz; s2 += fz.astype(np.float64) ** 2
    T_mc = np.sqrt(np.maximum(s2 / MC - (s1 / MC) ** 2, 0)).mean(0)
    f = f_all[:, idx[0], idx[1]].astype(np.float64)
    T_rg = rough_sigma(f)
    peak = f.max(0) - np.median(f, 0)
    res["temperature"][f"bin{i}"] = dict(
        texture_dn=float(np.median(tex[idx])),
        T_mc=float(np.median(T_mc)), T_roughness=float(np.median(T_rg)),
        ratio_median=float(np.median(T_rg / T_mc)),
        peak_over_T_mc=float(np.median(peak / T_mc)),
        peak_over_T_roughness=float(np.median(peak / T_rg)),
    )
    print(f"bin{i}: {json.dumps(res['temperature'][f'bin{i}'])}")

# --- step 2's SNR sweep, re-expressed as perplexity against the null --------
NULL = {53: 33.966, 27: 17.864, 18: 12.220, 14: 9.681, 9: 6.477}
with open(os.path.join(OUT, "02-entropy.json")) as fh:
    st2 = json.load(fh)
ln = np.log(n_all)
for key, row in st2["snr_sweep"].items():
    res["sweep_as_perplexity"][key] = dict(
        arm_N_perplexity=float(np.exp(row["arm_N"] * ln)),
        arm_S_perplexity=float(np.exp(row["arm_S"] * ln)),
        null_perplexity=NULL[n_all],
    )
print("sweep:", json.dumps(res["sweep_as_perplexity"], indent=2))

with open(os.path.join(OUT, "04-temperature.json"), "w") as fh:
    json.dump(res, fh, indent=2)
