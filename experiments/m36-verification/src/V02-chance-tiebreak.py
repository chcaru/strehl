"""M36 V02: M34's chance level, its tie-breaking, and the union -- recomputed
independently of the author's scripts.

Attacks:
  A. the analytic chance Jaccard 0.05*0.05/(0.10-0.0025) = 0.0256
  B. the tie-break perturbation  U(0,1e-12)*ptp(v).  Different channels have
     wildly different ptp.  Does the perturbation reorder NON-TIED values?
  C. the union 14.278% and the pairwise Jaccards, recomputed with my own code
     and my own seeds, and with the tie-break removed entirely.
  D. the shuffle null: is 0.53x-1.35x of chance actually "at chance"?  Measure
     the null's spread instead of asserting it.
"""
import numpy as np, os, json, itertools
from scipy.stats import spearmanr

ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
C = os.path.join(ROOT, "m34-confidence-vector", "out", "cache")
OUT = os.path.join(ROOT, "m36-verification", "out")
res = {}

ch = {n: np.load(os.path.join(C, f"{n}.npy")).ravel()
      for n in ("C1", "C2", "C3_fixed", "C4")}
N = ch["C1"].size
print(f"N = {N}")

# ---------------------------------------------------------------- A: chance
# Two independent uniformly-random subsets of size pN each.
p = 0.05
analytic = p*p/(2*p - p*p)
print(f"\nA. analytic chance = p^2/(2p-p^2) = {analytic:.10f}; author wrote "
      f"0.05*0.05/(0.10-0.0025) = {0.05*0.05/(0.10-0.0025):.10f}")
# brute-force Monte Carlo of the same quantity, no formula involved
rng = np.random.default_rng(3601)
mc = []
for _ in range(200):
    k = int(round(p*N))
    a = rng.choice(N, k, replace=False); b = rng.choice(N, k, replace=False)
    inter = np.intersect1d(a, b, assume_unique=True).size
    mc.append(inter/(2*k - inter))
mc = np.array(mc)
print(f"   MC over 200 independent pairs: mean {mc.mean():.6f}  sd {mc.std(ddof=1):.6f}"
      f"  [min {mc.min():.6f}, max {mc.max():.6f}]")
res["chance"] = dict(analytic=float(analytic), mc_mean=float(mc.mean()),
                     mc_sd=float(mc.std(ddof=1)), mc_min=float(mc.min()), mc_max=float(mc.max()))

# ------------------------------------------------------------- B: tie-break
print("\nB. tie-break audit")
tb = {}
for n, v in ch.items():
    v64 = v.astype(np.float64)
    ptp = float(np.ptp(v64))
    eps = 1e-12*ptp                       # max size of the author's perturbation
    thr = float(np.percentile(v64, 95))
    n_exact_tie = int((v64 == thr).sum())
    # how many values sit within the perturbation of the threshold, i.e. how many
    # NON-TIED pixels the perturbation could move across the boundary
    n_movable = int((np.abs(v64 - thr) <= eps).sum()) - n_exact_tie
    # float32 spacing at the threshold: perturbation matters only if eps >= spacing
    spacing = float(np.spacing(np.float32(thr)))
    tb[n] = dict(ptp=ptp, eps=eps, thr=thr, float32_spacing_at_thr=spacing,
                 eps_over_spacing=eps/spacing if spacing else None,
                 n_exact_at_thr=n_exact_tie, n_nontied_within_eps=n_movable,
                 frac_exact_at_thr=n_exact_tie/N)
    print(f"   {n:9s} ptp {ptp:12.5g}  eps {eps:10.4g}  p95 {thr:12.6g}"
          f"  f32-spacing {spacing:10.4g}  eps/spacing {eps/spacing:8.3g}"
          f"  exact-ties-at-p95 {n_exact_tie:8d} ({n_exact_tie/N:.4%})"
          f"  non-tied-within-eps {n_movable}")
res["tiebreak"] = tb

# ---------------------------------------------------- C: sets, union, jaccard
def worst_eps(v, r, frac=0.05, mult=1e-12):
    k = int(round(frac*v.size))
    key = v.astype(np.float64) + r.uniform(0, mult, v.size)*(np.ptp(v.astype(np.float64))+mult)
    return np.argpartition(key, -k)[-k:]

def worst_plain(v, frac=0.05):
    """NO tie-break at all: argpartition on the raw values."""
    k = int(round(frac*v.size))
    return np.argpartition(v, -k)[-k:]

def jac(a, b):
    a, b = set(a.tolist()), set(b.tolist())
    return len(a & b)/len(a | b)

names3 = ["C1", "C2", "C3_fixed"]
variants = {}
for tag, mult, seed in (("eps1e-12", 1e-12, 3602), ("eps1e-6", 1e-6, 3603),
                        ("eps1e-18", 1e-18, 3604)):
    r = np.random.default_rng(seed)
    S = {n: worst_eps(ch[n], r, mult=mult) for n in ch}
    u3 = set(S["C1"].tolist()) | set(S["C2"].tolist()) | set(S["C3_fixed"].tolist())
    u4 = u3 | set(S["C4"].tolist())
    variants[tag] = dict(union3=len(u3)/N, union4=len(u4)/N,
                         jaccard={f"{a}|{b}": jac(S[a], S[b])
                                  for a, b in itertools.combinations(list(ch), 2)})
    print(f"\nC. tie-break x{mult:g}: union(C1,C2,C3) = {len(u3)/N:.4%}"
          f"  ceiling frac {len(u3)/N/0.15:.4f}   union+C4worst5 = {len(u4)/N:.4%}")
    for k_, v_ in variants[tag]["jaccard"].items():
        print(f"      {k_:22s} {v_:.4f}  ({v_/analytic:.2f}x chance)")

Sp = {n: worst_plain(ch[n]) for n in ch}
u3p = set(Sp["C1"].tolist()) | set(Sp["C2"].tolist()) | set(Sp["C3_fixed"].tolist())
variants["no_tiebreak"] = dict(union3=len(u3p)/N, union4=None,
                               jaccard={f"{a}|{b}": jac(Sp[a], Sp[b])
                                        for a, b in itertools.combinations(list(ch), 2)})
print(f"\nC. NO tie-break at all: union(C1,C2,C3) = {len(u3p)/N:.4%}")
for k_, v_ in variants["no_tiebreak"]["jaccard"].items():
    print(f"      {k_:22s} {v_:.4f}  ({v_/analytic:.2f}x chance)")
res["variants"] = variants

# --------------------------------------------------------------- D: the null
print("\nD. shuffle null -- 100 repeats, both directions")
r = np.random.default_rng(3605)
S = {n: worst_eps(ch[n], r) for n in ch}
null = {}
for pair in (("C1", "C3_fixed"), ("C1", "C2"), ("C2", "C3_fixed")):
    vals = []
    for _ in range(100):
        sh = ch[pair[1]].copy(); r.shuffle(sh)
        vals.append(jac(S[pair[0]], worst_eps(sh, r)))
    vals = np.array(vals)
    obs = jac(S[pair[0]], S[pair[1]])
    z = (obs - vals.mean())/vals.std(ddof=1)
    null[f"{pair[0]}|{pair[1]}"] = dict(observed=obs, null_mean=float(vals.mean()),
                                        null_sd=float(vals.std(ddof=1)), z=float(z))
    print(f"   {pair[0]:3s} vs {pair[1]:9s} observed {obs:.5f}  null {vals.mean():.5f}"
          f" +- {vals.std(ddof=1):.5f}   z = {z:+.1f}")
res["null"] = null

# spearman on the FULL image, not a 200k subsample
print("\n   spearman, full 1.05e6 pixels (author subsampled 200k):")
sp = {}
for a, b in itertools.combinations(names3, 2):
    sp[f"{a}|{b}"] = float(spearmanr(ch[a], ch[b]).statistic)
    print(f"      {a}|{b}: {sp[f'{a}|{b}']:+.4f}")
res["spearman_full"] = sp

json.dump(res, open(os.path.join(OUT, "V02-chance-tiebreak.json"), "w"), indent=1)
print("\nwrote V02-chance-tiebreak.json")
