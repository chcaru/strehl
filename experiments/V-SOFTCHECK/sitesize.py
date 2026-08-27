"""Site-size sensitivity, computed EXACTLY from the T=128 cache.

The band energy of a 256-px tile is the mean of the band energies of its four
non-overlapping 128-px quarters, and the grid step is 64, so those quarters are
present in the cache at index offsets of 2 rows / 2 cols.  The reference is
therefore max_k (mean of quarters) -- a real per-site max at the larger site,
not a max of maxes.
"""
import sys, numpy as np, softcheck as S
from analyze import load, ratio

subj = sys.argv[1]; gauge = sys.argv[2] if len(sys.argv)>2 else "lin"
c = load(subj, gauge, 128); sh = tuple(c["shape"]); nt = len(c["m_lo"]); cn = float(c["c_noise"])
idx = np.arange(nt).reshape(sh)
print(f"=== {subj}/{gauge} site-size sensitivity  (grid {sh})")
for name, quarters in (("T=128 (headline)", [(0,0)]),
                       ("T=256", [(0,0),(2,0),(0,2),(2,2)]),
                       ("T=384", [(r,c2) for r in (0,2,4) for c2 in (0,2,4)])):
    R = max(q[0] for q in quarters); C = max(q[1] for q in quarters)
    core = idx[:sh[0]-R, :sh[1]-C].ravel()
    def agg(a):
        return np.mean([a[..., idx[q[0]:sh[0]-R+q[0], q[1]:sh[1]-C+q[1]].ravel()]
                        for q in quarters], axis=0)
    m_mid = agg(c["m_mid_none"]); m_hi = agg(c["m_hi_none"])
    f_mid = agg(c["f_mid_none"]); f_hi = agg(c["f_hi_none"])
    lo = agg(c["m_lo"]); sel = lo >= np.quantile(lo, 0.50)
    n2 = len(core); sh2 = (sh[0]-R, sh[1]-C)
    a = ratio(m_mid, f_mid.max(0), sel, sh2, n2, True)
    b = ratio(m_mid-cn*m_hi, (f_mid-cn*f_hi).max(0), sel, sh2, n2, True)
    print(f"  {name:18s} NOSUB {a['median']:.4f} [{a['ci'][0]:.4f},{a['ci'][1]:.4f}]"
          f"   SUB {b['median']:.4f} [{b['ci'][0]:.4f},{b['ci'][1]:.4f}]   n={a['n']}")
