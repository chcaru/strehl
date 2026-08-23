"""M32 step 2: is posterior entropy admissible as confidence under discipline 120?

The review's second-ranked proposal is to carry a per-pixel posterior over
frame-of-best-focus and read CONFIDENCE off its entropy.  Discipline 120 (from
M27) says a self-normalised shape statistic measures goodness of fit and never
presence of evidence.  A softmax posterior needs a temperature, and the choice
of temperature is exactly the choice between those two things:

  arm N  T = the noise sd of the focus response, from the M4 model  (EXTERNAL)
  arm S  T = std_k(f_k), the spread of the observed curve itself    (SELF)

The test that matters is not discrimination -- arm S can discriminate, because a
peak and a noise curve genuinely have different shapes.  It is CALIBRATION:
whether a fixed threshold means the same thing twice.  So the headline is the
FIXED-POINT test: on information-free pixels, does the arm land on a stable
value that does not move when a nuisance variable moves?  The nuisance chosen is
n, the number of frames, because decimating a stack changes the curve's shape
without changing whether a pixel had any focus evidence to begin with.

PRE-REGISTERED, with effect sizes (discipline 142):
  P1  arm N, flat pixels: median H/log n >= 0.95, range over n <= 0.03
  P2  arm S, flat pixels: median H/log n <  0.95, range over n >  0.05
  P3  arm N, textured pixels: median H/log n < 0.70 (separation from flat > 0.25)
  P4  both arms rise under the SNR sweep; arm N reaches >= 0.95 by s = 8
  PLACEBO  a synthetic scene-free noise cube must give arm N H/log n ~ 1.0 at
           EVERY n.  If it does not, the instrument is broken and nothing else
           in this script is readable.

Note on the temperature estimate: the Monte Carlo uses the OBSERVED frames as a
proxy for the noise-free scene, so the gradients it perturbs already carry one
realisation of noise and T_N is biased HIGH.  A high T flattens the posterior and
raises entropy, i.e. the bias is toward claiming LESS information than is there.
That is the conservative direction for a confidence statistic.  The sigma/sqrt2
variant below bounds how much of any result is that bias.
"""
import numpy as np, os, json, time
from scipy.ndimage import sobel, uniform_filter

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")

G, RN_E, R = 50 / 436.8, 4.20, 2
MC = 32
NPIX = 20000
DECIM = [1, 2, 3, 4, 6]
SNR_SWEEP = [1, 2, 4, 8, 16]
rng = np.random.default_rng(20260809)


def focus(cube):
    gx = sobel(cube, axis=2, mode="nearest")
    gy = sobel(cube, axis=1, mode="nearest")
    return uniform_filter(np.hypot(gx, gy), size=(1, 2 * R + 1, 2 * R + 1), mode="nearest")


def norm_entropy(f, T):
    """f (n, P), T (P,) -> normalised entropy in [0, 1], 1 = no information."""
    z = (f - f.max(0)) / np.maximum(T, 1e-12)[None, :]
    p = np.exp(np.clip(z, -700, 0))
    p /= p.sum(0)
    h = -(p * np.log(np.maximum(p, 1e-300))).sum(0)
    return h / np.log(f.shape[0])


def temperature_mc(cube, sigma, idx, mc=MC, scale=1.0):
    """Monte Carlo sd of the focus response under model noise, per frame/pixel."""
    s1 = np.zeros((cube.shape[0], idx[0].size), np.float64)
    s2 = np.zeros_like(s1)
    for _ in range(mc):
        noisy = cube + rng.standard_normal(cube.shape, np.float32) * (sigma * scale)
        f = focus(noisy)[:, idx[0], idx[1]].astype(np.float64)
        s1 += f
        s2 += f * f
    v = np.maximum(s2 / mc - (s1 / mc) ** 2, 0.0)
    return np.sqrt(v).mean(0)          # average over frames -> (P,)


raw = np.load(os.path.join(CACHE, "raw.npy"))
n_all = raw.shape[0]
sigma = np.sqrt(G * np.clip(raw, 0, None) + (RN_E * G) ** 2).astype(np.float32)
f_all = focus(raw)

# --- populations, selected on a texture measure EXTERNAL to the focus volume ---
mean_img = raw.mean(0)
loc_var = uniform_filter(mean_img ** 2, 2 * R + 1) - uniform_filter(mean_img, 2 * R + 1) ** 2
tex = np.sqrt(np.maximum(loc_var, 0))
b = 8                                   # keep boxes off the frame edge
inner = np.zeros(tex.shape, bool)
inner[b:-b, b:-b] = True
lo, hi = np.percentile(tex[inner], [5, 95])
pops = {}
for name, m in (("flat", inner & (tex <= lo)), ("textured", inner & (tex >= hi))):
    yy, xx = np.nonzero(m)
    k = rng.choice(yy.size, min(NPIX, yy.size), replace=False)
    pops[name] = (yy[k], xx[k])

res = {"populations": {}, "fixed_point": {}, "snr_sweep": {}, "placebo": {}}
for name, idx in pops.items():
    res["populations"][name] = dict(
        n=int(idx[0].size),
        texture_dn=float(np.median(tex[idx])),
        signal_dn=float(np.median(mean_img[idx])),
        snr=float(np.median(mean_img[idx] / np.sqrt(G * mean_img[idx] + (RN_E * G) ** 2))),
    )
print(json.dumps(res["populations"], indent=2))

# --- headline: fixed-point test over the decimation sweep -------------------
t0 = time.time()
for name, idx in pops.items():
    T_n = temperature_mc(raw, sigma, idx)
    T_half = temperature_mc(raw, sigma, idx, mc=8, scale=1 / np.sqrt(2))
    row = {}
    for d in DECIM:
        sel = np.arange(0, n_all, d)
        f = f_all[sel][:, idx[0], idx[1]].astype(np.float64)
        row[f"n{sel.size}"] = dict(
            arm_N=float(np.median(norm_entropy(f, T_n))),
            arm_S=float(np.median(norm_entropy(f, f.std(0)))),
            arm_N_half=float(np.median(norm_entropy(f, T_half))),
        )
    res["fixed_point"][name] = row
    print(f"{name}: {json.dumps(row)}   [{time.time()-t0:.0f}s]")

# --- SNR sweep on the textured population ----------------------------------
idx = pops["textured"]
for s in SNR_SWEEP:
    extra = sigma * np.sqrt(max(s * s - 1, 0))
    deg = raw + rng.standard_normal(raw.shape, np.float32) * extra
    f = focus(deg)[:, idx[0], idx[1]].astype(np.float64)
    T_n = temperature_mc(deg, sigma * s, idx, mc=8)
    res["snr_sweep"][f"s{s}"] = dict(
        arm_N=float(np.median(norm_entropy(f, T_n))),
        arm_S=float(np.median(norm_entropy(f, f.std(0)))),
    )
    print(f"snr/{s}: {json.dumps(res['snr_sweep'][f's{s}'])}")

# --- placebo: scene-free noise cube ----------------------------------------
lvl = float(np.median(mean_img))
sig_p = np.sqrt(G * lvl + (RN_E * G) ** 2)
noise_cube = (lvl + rng.standard_normal(raw.shape, np.float32) * sig_p).astype(np.float32)
idx_p = (rng.integers(b, raw.shape[1] - b, NPIX), rng.integers(b, raw.shape[2] - b, NPIX))
f_p_all = focus(noise_cube)
T_p = temperature_mc(noise_cube, np.float32(sig_p), idx_p, mc=8)
for d in DECIM:
    sel = np.arange(0, n_all, d)
    f = f_p_all[sel][:, idx_p[0], idx_p[1]].astype(np.float64)
    res["placebo"][f"n{sel.size}"] = dict(
        arm_N=float(np.median(norm_entropy(f, T_p))),
        arm_S=float(np.median(norm_entropy(f, f.std(0)))),
    )
print("placebo:", json.dumps(res["placebo"], indent=2))

with open(os.path.join(OUT, "02-entropy.json"), "w") as fh:
    json.dump(res, fh, indent=2)
