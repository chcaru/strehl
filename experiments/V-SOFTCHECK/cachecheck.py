"""Is every cached frame row actually a DIFFERENT frame, and does the argmax
really move across the bracket?  A density sweep that does not move would be
explained either by real data or by a cache that stored one frame N times."""
import sys, numpy as np
from analyze import load
for subj, N in (("119MSDCF",33), ("coffee-bubbles",19), ("109MSDCF",22)):
    c = load(subj, "lin", 128); F = np.asarray(c["f_mid_none"]); lo = np.asarray(c["m_lo"])
    sel = lo >= np.quantile(lo, 0.50)
    u = np.unique(F, axis=0)
    am = F[:, sel].argmax(0)
    win, cnt = np.unique(am, return_counts=True)
    print(f"{subj}: rows {F.shape} distinct_rows={len(u)}  winners_used={len(win)}/{N}")
    print(f"   argmax histogram: " + " ".join(f"{w}:{n}" for w, n in zip(win, cnt)))
    for n in (3,5,9,17,N):
        idx = np.unique(np.round(np.linspace(0,N-1,n)).astype(int))
        r = np.median(np.asarray(c["m_mid_none"])[sel]/F[idx][:,sel].max(0))
        print(f"   n={len(idx):3d} idx={list(idx)} -> {r:.6f}")
