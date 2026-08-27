"""Focus response measured PER TILE, at each tile's own in-focus frame.

A fixed k is only meaningful for tiles that are actually in focus at k; on a
205-frame stack each tile focuses at its own depth, so a fixed-k median is
diluted by tiles that were never in focus there.  So for each tile take its
own peak frame k_t and compare with k_t +- off.

Caveat stated up front: k_t is the argmax of the statistic under test, so the
ratio is >= 1 BY CONSTRUCTION.  This arm therefore cannot test the SIGN of
the response -- only its MAGNITUDE.  A statistic blind to focus would still
be pinned at ~1.0 here, which is exactly the failure mode being looked for,
so the magnitude is the informative quantity.  Tiles are still selected by
E_lo, the focus-insensitive coarse band.
"""
import os, sys, numpy as np, softcheck as S
from analyze import load
subj = sys.argv[1]; OFFS=[int(x) for x in sys.argv[2].split(",")]
T, GAU = 128, "lin"
c = load(subj, GAU, T); lo=np.asarray(c["m_lo"]); F=np.asarray(c["f_mid_none"]); N=int(c["N"])
top = np.argsort(lo)[::-1][:200]
kt = F[:, top].argmax(0)
print(f"{subj}: N={N}, {len(top)} tiles by E_lo; their own focus frames span {kt.min()}..{kt.max()}"
      f" (median {int(np.median(kt))})")
print(f"  {'offset':>8s} {'n usable':>9s} {'median ratio':>13s} {'p10':>8s} {'p90':>8s} {'min':>8s}")
for o in OFFS:
    r=[]
    for j,tt in enumerate(top):
        k=kt[j]
        for kk in (k-o, k+o):
            if 0 <= kk < N: r.append(F[k,tt]/F[kk,tt])
    r=np.array(r)
    print(f"  {'+-'+str(o):>8s} {len(r):9d} {np.median(r):13.2f} {np.percentile(r,10):8.2f}"
          f" {np.percentile(r,90):8.2f} {r.min():8.2f}")
