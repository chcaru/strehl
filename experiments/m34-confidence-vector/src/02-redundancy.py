"""M34 step 2: correct C3, then measure whether the channels are redundant.

TWO DEFECTS IN SCRIPT 01, both left in place per rule 15 and corrected here.

  (1) SIGN ERROR in the vertex value, identical to the one M33 script 02 already
      contained.  For samples at x = -1,0,1 with b = (ap-am)/2 and c = (ap-2a0+am)/2,
      the vertex sits at x* = -b/2c and its value is a0 - b^2/4c = a0 + 0.5*b*x*
      = a0 + 0.25*(ap-am)*x*.  Script 01 wrote a MINUS.  I found this exact error
      once already and reintroduced it by retyping the formula instead of importing
      the corrected one.

  (2) THE CLAMP HID IT.  `1 - exp(min(a0 - peak, 0))` was written so a numerically
      impossible positive value could not produce a negative deficit.  With the sign
      flipped, a0 - peak is positive for EVERY pixel, so the clamp fired everywhere
      and C3 came out exactly 0.00000 at the median, the mean and p95.  A guard
      meant to catch an impossible case silently absorbed a real one.  An assert
      would have failed on pixel one.

Script 02 recomputes C3 correctly and CHECKS it against M33 rather than trusting
it: M33 measured a true mean deficit of 2.75% at x2 sampling and a calibration
ratio of 0.710 for this estimator, so the corrected channel should average near
0.710 * 2.75% = 1.95%.  If it does not, the estimator is not the one M33 scored.

Then the actual question: do the four channels rank pixels the same way?

  - Spearman rank correlation between every pair.
  - Jaccard overlap of the worst-5% sets, which is what a user-facing mask
    actually is.  Chance level for two independent 5% sets is
    0.05*0.05 / (0.10 - 0.0025) = 0.0256.
  - A label-shuffle null: permute one channel's pixels and re-measure, which must
    land at chance.  This confirms the overlap statistic is reading structure and
    not arithmetic.

P1 (pre-registered in script 01): C1 vs C3 Jaccard < 0.15.
"""
import numpy as np, os, json, itertools
from scipy.stats import spearmanr

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "out")
CACHE = os.path.join(OUT, "cache")
M33 = os.path.join(HERE, "..", "..", "m33-subframe-offset", "out", "cache", "dense_focus.npy")

dense = np.load(M33, mmap_mode="r")
foc = np.ascontiguousarray(dense[::2])
n, HH, WW = foc.shape
yy, xx = np.mgrid[0:HH, 0:WW]
kmax = np.load(os.path.join(CACHE, "kmax.npy")).astype(np.int64)

base = foc.min(0)
km = np.clip(kmax, 1, n - 2)
a0 = np.log(np.maximum(foc[km, yy, xx] - base, 1e-6))
am_ = np.log(np.maximum(foc[km - 1, yy, xx] - base, 1e-6))
ap = np.log(np.maximum(foc[km + 1, yy, xx] - base, 1e-6))
denom = am_ - 2 * a0 + ap
ok = denom < -1e-9                                   # a real maximum, not a flat/degenerate cell
xstar = np.where(ok, 0.5 * (am_ - ap) / np.where(ok, denom, 1.0), 0.0)
xstar = np.clip(xstar, -1, 1)

peak_bad = a0 - 0.25 * (ap - am_) * xstar            # script 01, wrong sign
peak_good = a0 + 0.25 * (ap - am_) * xstar           # corrected

C3_bad = np.clip(1.0 - np.exp(np.minimum(a0 - peak_bad, 0.0)), 0, 1)
C3 = np.clip(1.0 - np.exp(np.minimum(a0 - peak_good, 0.0)), 0, 1).astype(np.float32)
C3[~ok] = 0.0

print(f"C3 as script 01 computed it : mean {C3_bad.mean():.6f}  p95 {np.percentile(C3_bad,95):.6f}"
      f"  exactly_zero {float((C3_bad==0).mean()):.4%}")
print(f"C3 corrected                : mean {C3.mean():.6f}  p95 {np.percentile(C3,95):.6f}"
      f"  exactly_zero {float((C3==0).mean()):.4%}")
print(f"   degenerate cells (denom>=0): {float((~ok).mean()):.4%}")

M33_TRUE_MEAN, M33_RATIO = 0.02753, 0.710
expect = M33_TRUE_MEAN * M33_RATIO
print(f"   M33 cross-check: expect mean ~{expect:.5f}, got {C3.mean():.5f}"
      f"  (ratio {C3.mean()/expect:.3f})")
np.save(os.path.join(CACHE, "C3_fixed.npy"), C3)

# ---------------------------------------------------------------- redundancy
C = {
    "C1_sigma": np.load(os.path.join(CACHE, "C1.npy")).ravel(),
    "C2_perplexity": np.load(os.path.join(CACHE, "C2.npy")).ravel(),
    "C3_deficit": C3.ravel(),
    "C4_flags": np.load(os.path.join(CACHE, "C4.npy")).ravel(),
}
names = list(C)
N = C["C1_sigma"].size
rng = np.random.default_rng(34)
sub = rng.choice(N, 200_000, replace=False)          # spearman on 1.05e6 pts is slow

def worst(v, frac=0.05):
    """Indices of the `frac` least-trustworthy pixels. Ties broken randomly, so a
    channel that is constant over a large set cannot win the overlap by ordering."""
    k = int(round(frac * v.size))
    key = v + rng.uniform(0, 1e-12, v.size) * (np.ptp(v) + 1e-12)
    return np.argpartition(key, -k)[-k:]

sets = {k: set(worst(v).tolist()) for k, v in C.items()}
for k, s in sets.items():
    print(f"  worst-5% set {k}: {len(s)} px")

rho, jac = {}, {}
for a, b in itertools.combinations(names, 2):
    r = spearmanr(C[a][sub], C[b][sub]).statistic
    inter = len(sets[a] & sets[b])
    union = len(sets[a] | sets[b])
    rho[f"{a}|{b}"] = float(r)
    jac[f"{a}|{b}"] = float(inter / union)
    print(f"{a:15s} vs {b:15s}  spearman {r:+.4f}   jaccard {inter/union:.4f}"
          f"   ({inter} shared)")

# null: shuffle one channel's pixel labels -> must land at chance
shuf = C["C3_deficit"].copy()
rng.shuffle(shuf)
s_shuf = set(worst(shuf).tolist())
null_j = len(sets["C1_sigma"] & s_shuf) / len(sets["C1_sigma"] | s_shuf)
print(f"\nNULL  C1 vs shuffled C3 jaccard {null_j:.4f}  (analytic chance 0.0256)")

union_all = set().union(*sets.values())
print(f"UNION of all four worst-5% sets: {len(union_all)/N:.4%} of pixels"
      f"   (5% if identical, 20% if disjoint)")

json.dump(dict(
    c3_bad=dict(mean=float(C3_bad.mean()), exactly_zero=float((C3_bad == 0).mean())),
    c3_fixed=dict(mean=float(C3.mean()), p95=float(np.percentile(C3, 95)),
                  exactly_zero=float((C3 == 0).mean()), degenerate=float((~ok).mean())),
    m33_crosscheck=dict(expected=float(expect), got=float(C3.mean()),
                        ratio=float(C3.mean() / expect)),
    spearman=rho, jaccard=jac, null_jaccard=float(null_j),
    analytic_chance=0.05 * 0.05 / (0.10 - 0.0025),
    union_fraction=float(len(union_all) / N),
    P1_c1_vs_c3_under_015=bool(jac["C1_sigma|C3_deficit"] < 0.15),
    P4_union_over_12pct=bool(len(union_all) / N > 0.12),
), open(os.path.join(OUT, "02-redundancy.json"), "w"), indent=1)
print("wrote 02-redundancy.json")
