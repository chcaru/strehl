"""V-KILLB0 band-resolved coherence + contiguity.

Two questions at once.

1. MECHANISM AUDIT.  Reading gatefloor.rs/pyramid.rs, scaling beta[0] can only
   move the band-0 gate; the per-level hull loop indexes beta[k.min(len-2)] for
   k in 1.., so beta[0] never reaches the hull, and bands 1..6 should therefore
   be identical.  If coarse bands are NOT identical, the orchestrator's account
   of what the knob does is incomplete.  Coherent gain per band answers this
   with a number instead of an argument.

2. IS THE "STRUCTURE" REAL?  leaf-2-cpl reads rho=0.47 at its top structure
   decile, which would be a serious loss -- unless that decile is scattered
   noise clumps rather than contiguous structure.  Contiguity separates the
   two: real structure (veins, hairs, edges) forms large connected components;
   noise clumps do not.  Reported as the fraction of top-decile pixels living
   in components of >= 200 px, measured identically on every subject so the
   subjects can be compared to each other.
"""
import sys

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.ndimage import label as cclabel

import bandprobe as bp

BANDS = [("0.02-0.05", 8.0, 16.0), ("0.05-0.17", 2.0, 8.0),
         ("0.17-0.25", 1.2732, 2.0), ("0.25-0.50", 0.0, 1.2732)]


def bandpass(x, lo, hi):
    a = gaussian_filter(x, hi) if hi > 0 else x
    b = gaussian_filter(x, lo) if lo > 0 else x
    return (b - a) if hi > 0 else x - gaussian_filter(x, 0.6366)


def cg(a, b):
    a = a.astype(np.float64); b = b.astype(np.float64)
    a = a - a.mean(); b = b - b.mean()
    ea = np.sqrt((a * a).mean()); eb = np.sqrt((b * b).mean())
    return (a * b).mean() / (ea * eb), (a * b).mean() / (a * a).mean(), eb / ea


def main():
    A, B, label = sys.argv[1], sys.argv[2], sys.argv[3]
    la = bp.channels(bp.load(A))["L"]; lb = bp.channels(bp.load(B))["L"]
    h, w = la.shape
    sel = gaussian_filter(np.abs(gaussian_filter(la, 1.5) - gaussian_filter(la, 4.0)), 2.0)
    top = sel >= np.percentile(sel, 90)
    lab, n = cclabel(top)
    if n:
        sizes = np.bincount(lab.ravel())[1:]
        big = float(sizes[sizes >= 200].sum()) / float(sizes.sum())
    else:
        big = 0.0
    print(f"== BANDCOH {label}   medianA={np.median(la):.0f} "
          f"clip%={100*(la>=65000).mean():.3f} black%={100*(la<=200).mean():.3f}")
    print(f"  top-decile contiguity (frac of px in components >=200px): {big:.4f}"
          f"   [high = real extended structure, low = scattered speckle]")
    print(f"  {'band':<10} {'ALL rho':>9} {'ALL g':>8} {'ALL rms':>8} "
          f"{'TOP rho':>9} {'TOP g':>8} {'TOP rms':>8}")
    for nm, lo, hi in BANDS:
        pa = bandpass(la, lo, hi); pb = bandpass(lb, lo, hi)
        r1, g1, x1 = cg(pa, pb)
        r2, g2, x2 = cg(pa[top], pb[top])
        print(f"  {nm:<10} {r1:9.4f} {g1:8.4f} {x1:8.4f} {r2:9.4f} {g2:8.4f} {x2:8.4f}")


if __name__ == "__main__":
    main()


