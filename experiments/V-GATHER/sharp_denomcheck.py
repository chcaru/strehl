"""Commission MY OWN denominator. Which frame does the envelope select?

If a per-patch "best frame" envelope selects the LAST frame of a focus stack
at most patches, it is not selecting the sharpest frame -- it is selecting the
most defocused one, because a ratio statistic HI/LO is maximised when defocus
collapses LO and leaves read noise in HI.
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_diag as SD

for subj in ("coffee-bubbles",):
    r = SD.cached(subj)
    A, C = r["A"], r["C"]
    nf = A.shape[0]
    nreg = np.isfinite(A).sum(axis=0)
    sel = nreg >= 3
    Af = np.where(np.isfinite(A), A, -np.inf)
    bestk = np.argmax(Af, axis=0)[sel]
    print("=== %s : which frame does argmax(HI/LO) pick? (%d frames) ===" % (subj, nf))
    print("%6s %8s %8s   %s" % ("frame", "n picked", "share", "median corr of that frame"))
    for k in range(nf):
        n = int((bestk == k).sum())
        if n:
            print("%6d %8d %7.1f%%   %.3f" % (k, n, 100.0*n/bestk.size, float(np.median(C[k]))))
    ends = int(((bestk <= 1) | (bestk >= nf - 2)).sum())
    print("\npicked at a STACK END (first 2 or last 2 frames): %d/%d = %.1f%%"
          % (ends, bestk.size, 100.0*ends/bestk.size))
    print("a focus stack's in-focus frame is interior at most sites; an envelope")
    print("that piles up at the ends is selecting defocus, not focus.")
