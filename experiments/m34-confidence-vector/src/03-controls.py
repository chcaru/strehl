"""M34 step 3: the two controls that decide whether step 2 means anything.

Step 2 found every cross-channel Jaccard within 0.53x-1.35x of chance.  Two
things could produce that without the channels being genuinely complementary,
and both are checked here.

CONTROL A -- C4 is a degenerate row and must be removed from the union.
  C4 is a binary flag firing on 0.053% of pixels.  Asking for its "worst 5%"
  therefore returns 0.053% real flags and 4.947% random tie-breaks, so its
  overlap with anything lands at chance BY CONSTRUCTION.  That makes C4's row a
  second, independent confirmation of the chance level -- it measured 0.0250,
  0.0297, 0.0268 against an analytic 0.0256 -- but it also means C4 contributed
  ~5% of near-random pixels to step 2's 18.52% union.  Recompute the union over
  the three real-valued channels, and separately with C4 as its ACTUAL flag set.

CONTROL B -- the reliability ceiling.
  Low overlap proves the channels disagree.  It does not prove they disagree
  ABOUT SOMETHING REAL: two pure noise channels also disagree.  So re-realise
  the measurement.  Add an independent draw of sensor noise (M4 model, at the
  data's own level) to the raw cube, rebuild the focus volume, recompute each
  channel, and measure each channel against ITSELF across two such draws.  That
  self-overlap is the ceiling any cross-channel number should be read against.

  This is deliberately CONSERVATIVE.  Both arms carry the original noise plus an
  independent synthetic draw, so each arm has ~sqrt(2)x the real noise and the
  two arms share only the original component.  The measured self-overlap is
  therefore a LOWER BOUND on the true reliability, not an estimate of it.

P3 (pre-registered in script 01): self-overlap > 0.60 Jaccard for C1 and C3.
"""
import numpy as np, os, json
from scipy.ndimage import sobel, uniform_filter

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "out")
CACHE = os.path.join(OUT, "cache")
M32 = os.path.join(HERE, "..", "..", "m32-posterior", "out", "cache", "raw.npy")

ISO, G, RN_E, R = 50, 50 / 436.8, 4.20, 2
rng = np.random.default_rng(3434)

# ------------------------------------------------------------------ control A
C1 = np.load(os.path.join(CACHE, "C1.npy")).ravel()
C2 = np.load(os.path.join(CACHE, "C2.npy")).ravel()
C3 = np.load(os.path.join(CACHE, "C3_fixed.npy")).ravel()
C4 = np.load(os.path.join(CACHE, "C4.npy")).ravel()
N = C1.size

def worst(v, frac=0.05, r=None):
    r = r or rng
    k = int(round(frac * v.size))
    key = v + r.uniform(0, 1e-12, v.size) * (np.ptp(v) + 1e-12)
    return set(np.argpartition(key, -k)[-k:].tolist())

s1, s2, s3 = worst(C1), worst(C2), worst(C3)
u3 = s1 | s2 | s3
u3_c4 = u3 | set(np.flatnonzero(C4 > 0).tolist())
print(f"union of C1,C2,C3 worst-5% : {len(u3)/N:.4%}   (5% identical, 15% disjoint)")
print(f"   fraction of the disjoint ceiling reached: {len(u3)/N/0.15:.4f}")
print(f"union + C4's ACTUAL flags  : {len(u3_c4)/N:.4%}  (C4 adds {(len(u3_c4)-len(u3))/N:.4%})")
print(f"step 2 reported 18.5244% because C4's worst-5% was 4.947% random tie-breaks")

# ------------------------------------------------------------------ control B
raw = np.asarray(np.load(M32, mmap_mode="r"), np.float32)
n = raw.shape[0]
sig = np.clip(raw, 0, None)
noise_sd = np.sqrt(G * sig + (RN_E * G) ** 2).astype(np.float32)
print(f"\nsynthetic noise sd: median {np.median(noise_sd):.3f} DN"
      f"  (data median signal {np.median(raw):.0f} DN)")

def channels(cube):
    """Rebuild C1,C2,C3 from a raw cube, exactly as scripts 01/02 do."""
    foc = np.empty_like(cube)
    for i in range(cube.shape[0]):
        gx = sobel(cube[i], axis=1, mode="nearest")
        gy = sobel(cube[i], axis=0, mode="nearest")
        foc[i] = uniform_filter(np.hypot(gx, gy), size=2 * R + 1, mode="nearest")
    nn, HH, WW = foc.shape
    yy, xx = np.mgrid[0:HH, 0:WW]
    tail = np.concatenate([foc[:6], foc[-6:]], 0)
    d2 = tail[2:] - 2 * tail[1:-1] + tail[:-2]
    sf = np.sqrt(np.maximum(d2.var(0), 1e-12) / 6.0).astype(np.float32)
    fmax, kmax = foc.max(0), foc.argmax(0)

    d = (fmax[None] - foc) / np.maximum(sf, 1e-6)[None]
    lp = -0.5 * d.astype(np.float64) ** 2
    lp -= lp.max(0)
    p = np.exp(lp); p /= p.sum(0)
    c2 = np.exp(-(p * np.log(np.maximum(p, 1e-300))).sum(0)).astype(np.float32)
    del d, lp, p

    acc = (fmax[None] - foc) <= sf[None]
    na = acc.sum(0).astype(np.float32)
    vk = G * np.clip(cube, 0, None) + (RN_E * G) ** 2
    c1 = (np.sqrt((vk * acc).sum(0)) / np.maximum(na, 1)) / \
         np.maximum((cube * acc).sum(0) / np.maximum(na, 1), 1e-3)

    base = foc.min(0)
    km = np.clip(kmax, 1, nn - 2)
    a0 = np.log(np.maximum(foc[km, yy, xx] - base, 1e-6))
    am_ = np.log(np.maximum(foc[km - 1, yy, xx] - base, 1e-6))
    ap = np.log(np.maximum(foc[km + 1, yy, xx] - base, 1e-6))
    den = am_ - 2 * a0 + ap
    ok = den < -1e-9
    xs = np.clip(np.where(ok, 0.5 * (am_ - ap) / np.where(ok, den, 1.0), 0.0), -1, 1)
    pk = a0 + 0.25 * (ap - am_) * xs
    c3 = np.clip(1.0 - np.exp(np.minimum(a0 - pk, 0.0)), 0, 1).astype(np.float32)
    c3[~ok] = 0.0
    return c1.ravel(), c2.ravel(), c3.ravel()

arms = []
for a in range(2):
    cube = raw + rng.standard_normal(raw.shape).astype(np.float32) * noise_sd
    arms.append(channels(cube))
    print(f"  arm {a} rebuilt")

r0 = np.random.default_rng(7)                      # SAME tie-break stream for both arms
ceil = {}
for i, nm in enumerate(["C1_sigma", "C2_perplexity", "C3_deficit"]):
    a = worst(arms[0][i], r=np.random.default_rng(7))
    b = worst(arms[1][i], r=np.random.default_rng(7))
    ceil[nm] = len(a & b) / len(a | b)
    print(f"  reliability ceiling {nm:15s} jaccard {ceil[nm]:.4f}")

cross = {"C1_sigma|C3_deficit": 0.0136, "C1_sigma|C2_perplexity": 0.0346,
         "C2_perplexity|C3_deficit": 0.0267}
print("\n  cross-channel overlap as a FRACTION of each pair's reliability ceiling:")
for k, v in cross.items():
    a, b = k.split("|")
    cl = min(ceil[a], ceil[b])
    print(f"    {k:28s} {v:.4f} / {cl:.4f} = {v/cl:.4f}   (chance/{cl:.4f} = {0.0256/cl:.4f})")

json.dump(dict(
    union_three_channels=float(len(u3) / N),
    fraction_of_disjoint_ceiling=float(len(u3) / N / 0.15),
    union_plus_real_c4_flags=float(len(u3_c4) / N),
    c4_worst5_is_random_tiebreak=True,
    reliability_ceiling=ceil,
    cross_over_ceiling={k: float(v / min(ceil[k.split("|")[0]], ceil[k.split("|")[1]]))
                        for k, v in cross.items()},
    P3_ceiling_over_060=bool(ceil["C1_sigma"] > 0.60 and ceil["C3_deficit"] > 0.60),
), open(os.path.join(OUT, "03-controls.json"), "w"), indent=1)
print("wrote 03-controls.json")
