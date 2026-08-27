"""A registration-free cross-check.

The per-site ratio depends on my affine fit.  This one does not: for each
frame, sort its 1440 tile band-energies; do the same for the master; then
compare RANK BY RANK.  A few px of displacement barely changes a frame's own
distribution over 1440 tiles, so this statistic is insensitive to my fit
error.  It is weaker than the per-site ratio (it cannot tell whether the
master won at the SAME place), but it is a genuine bound: if the master's
j-th sharpest site is below the best j-th sharpest site any frame has, the
master is not carrying the bracket's peak sharpness anywhere in its
distribution.
"""
import numpy as np
from analyze import load
CN = 0.185088
print(f"{'subject':22s} {'N':>4s}  {'rank-free NOSUB':>16s} {'rank-free SUB':>14s}   {'per-site NOSUB':>14s}")
for subj in ("119MSDCF","coffee-bubbles","109MSDCF","flower-bud-alone-cpl"):
    c = load(subj,"lin",128); N=int(c["N"])
    M = np.asarray(c["m_mid_none"]); Mh=np.asarray(c["m_hi_none"])
    F = np.asarray(c["f_mid_none"]); Fh=np.asarray(c["f_hi_none"])
    lo = np.asarray(c["m_lo"]); sel = lo>=np.median(lo)
    ms = np.sort(M[sel]); fs = np.sort(F[:,sel],axis=1).max(0)
    msS= np.sort((M-CN*Mh)[sel]); fsS=np.sort((F-CN*Fh)[:,sel],axis=1).max(0)
    hi = slice(len(ms)//2, None)     # the sharp half of the ranks
    r1 = np.median(ms[hi]/fs[hi]); r2 = np.median(msS[hi]/fsS[hi])
    ps = np.median(M[sel]/F[:,sel].max(0))
    print(f"{subj:22s} {N:4d}  {r1:16.4f} {r2:14.4f}   {ps:14.4f}")
