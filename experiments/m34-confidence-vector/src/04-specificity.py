"""M34 step 4: specificity. Orthogonal is not the same as useful.

Step 3 established that the three real-valued channels flag almost perfectly
disjoint pixel sets (14.28% union against a 15% disjoint ceiling) while each is
70-76% self-reproducible under an independent noise draw.  That justifies a
vector over a scalar.  It does NOT establish that any channel is right about
anything -- three orthogonal noise sources would score identically.

So test one channel against real ground truth.  M33's dense 105-frame grid gives
the TRUE sub-frame deficit for every pixel: the fraction of its focus response
lost by sampling at x2 instead of x1.  C3 is built to estimate exactly that.  If
the vector is meaningful then:

  - C3 must predict the true deficit substantially better than C1 or C2 do
    (specificity: the right channel wins on its own target), and
  - C1 and C2 must not be merely weaker versions of C3 (if they tracked it at,
    say, 0.8 of C3's correlation, the vector would be redundant after all and
    step 3's disjoint sets would be a thresholding artifact).

Ground-truth caveat carried forward from M33: the dense grid misses its own peaks
by 0.711% against the x2 grid's 2.753%, so it is honest ground truth for the x2
question by a factor of 3.87 and no more.

PRE-REGISTERED before running:
  P6  Spearman(C3, true deficit) > 0.45.
  P7  Both |Spearman(C1, true)| and |Spearman(C2, true)| < 0.5 * Spearman(C3, true).
  P8  Among the pixels C3 flags worst-5%, mean true deficit > 3x the global mean.
"""
import numpy as np, os, json
from scipy.stats import spearmanr

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "out")
CACHE = os.path.join(OUT, "cache")
M33 = os.path.join(HERE, "..", "..", "m33-subframe-offset", "out", "cache", "dense_focus.npy")

dense = np.asarray(np.load(M33, mmap_mode="r"), np.float32)
nd = dense.shape[0]
coarse = dense[::2]

true_peak = dense.max(0)                       # best the dense grid can see
coarse_peak = coarse.max(0)                    # best the operational grid sees
base = dense.min(0)
tp = np.maximum(true_peak - base, 1e-6)
cp = np.maximum(coarse_peak - base, 1e-6)
true_def = np.clip(1.0 - cp / tp, 0, 1).ravel()
print(f"true deficit  mean {true_def.mean():.5f}  median {np.median(true_def):.5f}"
      f"  p95 {np.percentile(true_def,95):.5f}  exactly_zero {float((true_def==0).mean()):.4%}")
print("  (M33 fact 270 reported mean 2.753% for this quantity)")

C1 = np.load(os.path.join(CACHE, "C1.npy")).ravel()
C2 = np.load(os.path.join(CACHE, "C2.npy")).ravel()
C3 = np.load(os.path.join(CACHE, "C3_fixed.npy")).ravel()
rng = np.random.default_rng(344)
sub = rng.choice(true_def.size, 300_000, replace=False)

r = {}
for nm, v in [("C1_sigma", C1), ("C2_perplexity", C2), ("C3_deficit", C3)]:
    r[nm] = float(spearmanr(v[sub], true_def[sub]).statistic)
    print(f"spearman({nm:15s}, true deficit) = {r[nm]:+.4f}")

# a channel built from pure noise, as the floor
noise_ch = rng.standard_normal(true_def.size)
r["noise_floor"] = float(spearmanr(noise_ch[sub], true_def[sub]).statistic)
print(f"spearman({'random':15s}, true deficit) = {r['noise_floor']:+.4f}   <- floor")

def worst_mean(v, frac=0.05):
    k = int(round(frac * v.size))
    idx = np.argpartition(v + rng.uniform(0, 1e-12, v.size) * (np.ptp(v) + 1e-12), -k)[-k:]
    return float(true_def[idx].mean())

g = float(true_def.mean())
lift = {}
for nm, v in [("C1_sigma", C1), ("C2_perplexity", C2), ("C3_deficit", C3)]:
    wm = worst_mean(v)
    lift[nm] = wm / g
    print(f"mean TRUE deficit among {nm:15s} worst-5%: {wm:.5f}  = {wm/g:.2f}x global mean")

p6 = r["C3_deficit"] > 0.45
p7 = abs(r["C1_sigma"]) < 0.5 * r["C3_deficit"] and abs(r["C2_perplexity"]) < 0.5 * r["C3_deficit"]
p8 = lift["C3_deficit"] > 3.0
print(f"\nP6 spearman(C3,true) > 0.45      : {p6}")
print(f"P7 C1,C2 below half of C3        : {p7}")
print(f"P8 C3 worst-5% lift > 3x         : {p8}")

json.dump(dict(
    true_deficit=dict(mean=g, median=float(np.median(true_def)),
                      p95=float(np.percentile(true_def, 95)),
                      exactly_zero=float((true_def == 0).mean())),
    spearman_vs_true=r, worst5_lift=lift, global_mean=g,
    P6=bool(p6), P7=bool(p7), P8=bool(p8),
), open(os.path.join(OUT, "04-specificity.json"), "w"), indent=1)
print("wrote 04-specificity.json")
