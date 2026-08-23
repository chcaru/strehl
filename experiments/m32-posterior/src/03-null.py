"""M32 step 3: the no-information null curve, and the readout that survives it.

Step 2 falsified its own P1.  The no-information fixed point of a softmax
posterior is NOT H/log n = 1, even with a perfectly calibrated temperature: the
maximum of n noise draws sits ~3 sd above the others, so softmax at T = 1 sd
concentrates.  The scene-free placebo landed at 0.874 (n=53) drifting to 0.811
(n=9).  Any threshold on entropy therefore has to be referenced to that
n-dependent null rather than to log n.

That null is a pure function of n and of the distribution of the focus response
under noise, so it can be simulated once and stored.  This script does that, then
re-expresses every step-2 number as an excess over it -- and switches the readout
from entropy to PERPLEXITY, exp(H) in nats, which is the effective number of
frames the posterior cannot separate.  Perplexity is the same quantity M27 called
n_eff, so the posterior's width and the coverage criterion become one number.

PRE-REGISTERED:
  P5  the simulated null at n=53 reproduces step 2's scene-free placebo (0.874)
      to within 0.02.  If it does not, the null is not a pure function of n and
      the calibration proposed here is unavailable.
  P6  null perplexity is a large fraction of n (>= 0.4 n) at every n tested.
  P7  the textured population's perplexity is < 1.05 at EVERY point of the SNR
      sweep including s=16, i.e. the calibrated posterior is near-degenerate on
      this sensor even at SNR ~8.  This is the falsifying prediction for the
      review's proposal that confidence should be read off posterior entropy.
"""
import numpy as np, os, json
from scipy.ndimage import sobel, uniform_filter

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")
G, RN_E, R = 50 / 436.8, 4.20, 2
rng = np.random.default_rng(20260810)
DECIM = [1, 2, 3, 4, 6]
TRIALS = 200000


def ent_perp(f, T):
    z = (f - f.max(0)) / np.maximum(T, 1e-12)[None, :]
    p = np.exp(np.clip(z, -700, 0))
    p /= p.sum(0)
    h = -(p * np.log(np.maximum(p, 1e-300))).sum(0)
    return h / np.log(f.shape[0]), np.exp(h)


res = {"null": {}, "texture_sweep": {}, "note": {}}

# --- the null: softmax over n iid unit-variance draws -----------------------
for d in DECIM:
    n = len(range(0, 53, d))
    f = rng.standard_normal((n, TRIALS))
    e, pp = ent_perp(f, np.ones(TRIALS))
    res["null"][f"n{n}"] = dict(
        n=n,
        entropy_median=float(np.median(e)), entropy_p05=float(np.percentile(e, 5)),
        perplexity_median=float(np.median(pp)), perplexity_over_n=float(np.median(pp) / n),
    )
print("null:", json.dumps(res["null"], indent=2))

# --- texture sweep: is the response graded, or binary? ----------------------
raw = np.load(os.path.join(CACHE, "raw.npy"))
sigma = np.sqrt(G * np.clip(raw, 0, None) + (RN_E * G) ** 2).astype(np.float32)


def focus(cube):
    gx = sobel(cube, axis=2, mode="nearest")
    gy = sobel(cube, axis=1, mode="nearest")
    return uniform_filter(np.hypot(gx, gy), size=(1, 2 * R + 1, 2 * R + 1), mode="nearest")


f_all = focus(raw)
mean_img = raw.mean(0)
lv = uniform_filter(mean_img ** 2, 2 * R + 1) - uniform_filter(mean_img, 2 * R + 1) ** 2
tex = np.sqrt(np.maximum(lv, 0))
b = 8
inner = np.zeros(tex.shape, bool); inner[b:-b, b:-b] = True
edges = np.percentile(tex[inner], [0, 20, 40, 60, 80, 95, 100])

MC, NP = 12, 6000
for i in range(len(edges) - 1):
    m = inner & (tex >= edges[i]) & (tex < edges[i + 1] + (1e9 if i == len(edges) - 2 else 0))
    yy, xx = np.nonzero(m)
    k = rng.choice(yy.size, min(NP, yy.size), replace=False)
    idx = (yy[k], xx[k])
    s1 = np.zeros((raw.shape[0], idx[0].size)); s2 = np.zeros_like(s1)
    for _ in range(MC):
        fz = focus(raw + rng.standard_normal(raw.shape, np.float32) * sigma)[:, idx[0], idx[1]]
        s1 += fz; s2 += fz.astype(np.float64) ** 2
    T = np.sqrt(np.maximum(s2 / MC - (s1 / MC) ** 2, 0)).mean(0)
    f = f_all[:, idx[0], idx[1]].astype(np.float64)
    e, pp = ent_perp(f, T)
    eS, ppS = ent_perp(f, f.std(0))
    res["texture_sweep"][f"bin{i}"] = dict(
        texture_dn=float(np.median(tex[idx])), signal_dn=float(np.median(mean_img[idx])),
        peak_over_noise=float(np.median((f.max(0) - np.median(f, 0)) / T)),
        arm_N_entropy=float(np.median(e)), arm_N_perplexity=float(np.median(pp)),
        arm_S_entropy=float(np.median(eS)), arm_S_perplexity=float(np.median(ppS)),
        frac_perplexity_under_1p05=float((pp < 1.05).mean()),
    )
    print(f"bin{i}: {json.dumps(res['texture_sweep'][f'bin{i}'])}")

with open(os.path.join(OUT, "03-null.json"), "w") as fh:
    json.dump(res, fh, indent=2)
