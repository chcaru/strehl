"""M36 V04: the control M34 section 1 does not have -- is the reliability
ceiling a LOWER bound, as the report claims, or an UPPER bound?

The report's argument: both arms carry the original noise plus an independent
draw, so each has ~sqrt(2)x the real noise, therefore the measured self-overlap
is a lower bound on true reliability.

The argument omits the other half: both arms also SHARE the original noise
realisation n0, and shared noise makes two arms agree.  Which effect wins is a
measurement, not an argument.  So build a cube whose noise-free truth I know,
and run both protocols on it:

    R_true(1)      = J( channels(S + n0), channels(S + n0') )      <- what we want
    R_true(sqrt2)  = J( channels(S + m0), channels(S + m0') ), m ~ sqrt(2)*sd
    R_share        = J( channels(S + n0 + n1), channels(S + n0 + n2) )  <- author's

    net bias      = R_share - R_true(1)
    sharing gain  = R_share - R_true(sqrt2)
    noise penalty = R_true(1) - R_true(sqrt2)

The synthetic stack is built from the real data so it can express the failure:
real all-in-focus texture, the real per-pixel depth map, a defocus sweep, and
M4-model noise at the real signal level.
"""
import numpy as np, os, json, time
from scipy.ndimage import sobel, uniform_filter, gaussian_filter

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
CACHE34 = os.path.join(ROOT, "m34-confidence-vector", "out", "cache")
OUT = os.path.join(ROOT, "m36-verification", "out")
G, RN_E, R = 50/436.8, 4.20, 2
res = {}

exec(open(os.path.join(ROOT, "m36-verification", "src", "_channels.py")).read())

raw = np.asarray(np.load(os.path.join(ROOT, "m32-posterior", "out", "cache", "raw.npy"),
                         mmap_mode="r"), np.float32)
n, HH, WW = raw.shape
kmax = np.load(os.path.join(CACHE34, "kmax.npy")).astype(np.float32)

# --- verify the kmax cache before using it ---------------------------------
dense = np.load(os.path.join(ROOT, "m33-subframe-offset", "out", "cache", "dense_focus.npy"),
                mmap_mode="r")
foc = np.ascontiguousarray(dense[::2])
print(f"kmax cache check: identical to argmax(dense[::2]) = "
      f"{np.array_equal(kmax.astype(np.int16), foc.argmax(0).astype(np.int16))}")
res["kmax_cache_ok"] = bool(np.array_equal(kmax.astype(np.int16), foc.argmax(0).astype(np.int16)))
del dense

# --- build the synthetic noise-free cube -----------------------------------
depth = gaussian_filter(kmax, 3.0)                       # smooth per-pixel depth
yy, xx = np.mgrid[0:HH, 0:WW]
S0 = raw[np.clip(np.rint(depth).astype(int), 0, n-1), yy, xx]   # all-in-focus composite
SIG0, SLOPE = 0.35, 1.0
levels = np.concatenate([[0.0], np.geomspace(0.25, 24.0, 19)]).astype(np.float32)
bank = np.stack([S0 if L == 0 else gaussian_filter(S0, L) for L in levels])
print(f"blur bank {bank.shape} built")

scene = np.empty((n, HH, WW), np.float32)
for k in range(n):
    sm = np.clip(SIG0 + SLOPE*np.abs(k - depth), levels[0], levels[-1])
    j = np.clip(np.searchsorted(levels, sm) - 1, 0, len(levels)-2)
    lo, hi = levels[j], levels[j+1]
    w = ((sm - lo)/(hi - lo)).astype(np.float32)
    scene[k] = bank[j, yy, xx]*(1-w) + bank[j+1, yy, xx]*w
del bank
sd = np.sqrt(G*np.clip(scene, 0, None) + (RN_E*G)**2).astype(np.float32)
print(f"synthetic scene: median {np.median(scene):.0f} DN, noise sd median {np.median(sd):.2f} DN")

# realism check: does the synthetic behave like the real stack?
c1r, c2r, c3r = channels(raw)
rng = np.random.default_rng(3640)
obs = scene + rng.standard_normal(scene.shape, np.float32)*sd          # the "capture"
c1s, c2s, c3s = channels(obs)
real_stats = dict(C1_median=float(np.median(c1r)), C2_median=float(np.median(c2r)),
                  C2_frac_deg=float((c2r < 1.01).mean()), C3_mean=float(c3r.mean()))
syn_stats = dict(C1_median=float(np.median(c1s)), C2_median=float(np.median(c2s)),
                 C2_frac_deg=float((c2s < 1.01).mean()), C3_mean=float(c3s.mean()))
print(f"  realism  real {real_stats}")
print(f"  realism  syn  {syn_stats}")
res["realism"] = dict(real=real_stats, synthetic=syn_stats)

def arms(a, b, tag):
    A, B = channels(a), channels(b)
    out = {nm: J(worst(A[i]), worst(B[i])) for i, nm in enumerate(["C1", "C2", "C3"])}
    print(f"  {tag:46s} C1 {out['C1']:.4f}  C2 {out['C2']:.4f}  C3 {out['C3']:.4f}")
    return out

t0 = time.time()
n0 = rng.standard_normal(scene.shape, np.float32)*sd
n0p = rng.standard_normal(scene.shape, np.float32)*sd
res["R_true_1x"] = arms(scene+n0, scene+n0p, "R_true(1x)   true retest, real noise level")
del n0p
m0 = rng.standard_normal(scene.shape, np.float32)*sd*np.sqrt(2.0)
m0p = rng.standard_normal(scene.shape, np.float32)*sd*np.sqrt(2.0)
res["R_true_sqrt2"] = arms(scene+m0, scene+m0p, "R_true(sqrt2) true retest, sqrt2 noise")
del m0, m0p
n1 = rng.standard_normal(scene.shape, np.float32)*sd
n2 = rng.standard_normal(scene.shape, np.float32)*sd
res["R_share"] = arms(scene+n0+n1, scene+n0+n2, "R_share      AUTHOR'S PROTOCOL")
del n1, n2, n0
print(f"  [{time.time()-t0:.0f}s]")

res["decomposition"] = {}
for nm in ("C1", "C2", "C3"):
    d = dict(net_bias=res["R_share"][nm]-res["R_true_1x"][nm],
             sharing_gain=res["R_share"][nm]-res["R_true_sqrt2"][nm],
             noise_penalty=res["R_true_1x"][nm]-res["R_true_sqrt2"][nm])
    res["decomposition"][nm] = {k: float(v) for k, v in d.items()}
    print(f"  {nm}: net bias {d['net_bias']:+.4f}   (sharing gain {d['sharing_gain']:+.4f},"
          f" noise penalty {d['noise_penalty']:+.4f})")

json.dump(res, open(os.path.join(OUT, "V04-ceiling-bias.json"), "w"), indent=1)
print("wrote V04-ceiling-bias.json")
