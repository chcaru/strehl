"""M113 K14 - THE CONFOUND-FREE MEASUREMENT OF RINGING AT n_eff = 1.

K13's merged numbers are contaminated and the contamination is visible in K13's
own table: merged CATMULL-ROM overshoots the nearest arm's envelope by 26.71%
while a single coherent catmull-rom resample of the same content overshoots by
12.83%. Same kernel. A kernel cannot ring twice as hard as itself, so most of
that excursion is NOT ringing -- it is the three arms ELECTING DIFFERENT FRAMES
(8.084% of quads, fact 1467) and the excursion beyond nearest's envelope picking
up a different photograph rather than a different interpolation.

The fix is to remove the confound rather than model it. Restrict to quads where

    idx_cr == idx_l3 == idx_nn   AND   n_eff == 1 in all three arms

There, every arm folded exactly one frame, and it was the SAME frame, with the
SAME warp. The only surviving difference between the three outputs is the
resampling kernel. Nearest is monotone and cannot overshoot, so it is a valid
envelope. This is the exact condition the orchestrator asked about -- no
averaging to hide behind -- and it is a pure kernel comparison.

Registered before looking: if ringing at n_eff = 1 is as bad as a single frame,
the ratio here should approach the 1.79x that M95's corrected P95 and my own
K12 stage A both measure. If the election's SPATIAL phase diversity is doing the
work instead of temporal averaging, it should come in below that even here.
"""
import json
import os

import numpy as np
import tifffile
from scipy import ndimage

from k12_neff_ringing import NB, cr_w, l3_w, luma, shift

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
R = r"C:\dev\strehl-out\M113\render3"


def main():
    nn = luma(os.path.join(R, "lin-nn.tif"))
    cr = luma(os.path.join(R, "lin-cr.tif"))
    l3 = luma(os.path.join(R, "lin-l3.tif"))
    idx = {k: tifffile.imread(os.path.join(R, f"idx-{k}.tif")).astype(np.int32)
           for k in ("cr", "l3", "nn")}
    ne = {k: tifffile.imread(os.path.join(R, f"neff-{k}.tif")).astype(np.int32)
          for k in ("cr", "l3", "nn")}

    same = (idx["cr"] == idx["l3"]) & (idx["cr"] == idx["nn"])
    one = (ne["cr"] == 1) & (ne["l3"] == 1) & (ne["nn"] == 1)
    pure = same & one
    print(f"quads total                      : {same.size}")
    print(f"  same elected frame in all 3    : {100*same.mean():6.2f}%")
    print(f"  n_eff == 1 in all 3            : {100*one.mean():6.2f}%")
    print(f"  BOTH (the clean stratum)       : {100*pure.mean():6.2f}%  "
          f"({int(pure.sum())} quads)")

    emax = ndimage.maximum_filter(nn, footprint=NB)
    emin = ndimage.minimum_filter(nn, footprint=NB)
    rng = np.maximum(emax - emin, 1e-9)
    g = np.hypot(*np.gradient(nn))
    gthr = float(np.percentile(g, 90.0))

    def over(v):
        return np.maximum(np.maximum(v - emax, emin - v), 0.0) / rng

    o_cr, o_l3 = over(cr), over(l3)
    res = {}
    print(f"\n{'population':38s} {'n':>9s} {'cr p99.9':>10s} {'l3 p99.9':>10s} {'ratio':>7s}")
    for nm, m in (("clean stratum, ALL pixels", pure),
                  ("clean stratum, EDGE pixels only", pure & (g >= gthr)),
                  ("clean stratum, top 1% gradient", pure & (g >= np.percentile(g, 99.0)))):
        if m.sum() < 500:
            print(f"{nm:38s} {int(m.sum()):9d}   too few, NO READING")
            continue
        a, b = np.percentile(o_cr[m], 99.9), np.percentile(o_l3[m], 99.9)
        res[nm] = dict(n=int(m.sum()), cr=a, l3=b, ratio=b / a if a > 0 else float("nan"))
        print(f"{nm:38s} {int(m.sum()):9d} {100*a:9.2f}% {100*b:9.2f}% "
              f"{b/a if a>0 else float('nan'):7.3f}")

    # ---- the ceiling, measured the same way on the same pixels ----
    print("\nCEILING on the SAME pixels: nearest arm resampled ONCE, coherently,")
    print("averaged over 7 sub-pixel phases (not just the worst-case 0.5).")
    m = pure & (g >= gthr)
    acc = {}
    for nm, wf in (("cr", cr_w), ("l3", l3_w)):
        vals = [np.percentile(over(shift(nn, p / 8.0, wf))[m], 99.9) for p in range(1, 8)]
        acc[nm] = float(np.mean(vals))
        print(f"  {nm} phase-averaged p99.9 : {100*np.mean(vals):6.2f}%  "
              f"(range {100*min(vals):.2f}-{100*max(vals):.2f}%)")
    ceil_ratio = acc["l3"] / acc["cr"]
    edge = res["clean stratum, EDGE pixels only"]
    print(f"  CEILING ratio l3/cr          : {ceil_ratio:.3f}")
    print(f"  MEASURED ratio l3/cr at n_eff=1: {edge['ratio']:.3f}")
    surv = (edge["l3"] - edge["cr"]) / (acc["l3"] - acc["cr"])
    print(f"\n  survival of the l3-cr excess at n_eff == 1, same frame: {100*surv:.1f}%")
    res["ceiling"] = dict(cr=acc["cr"], l3=acc["l3"], ratio=ceil_ratio)
    res["survival_at_neff1"] = float(surv)

    # ---- mechanism: is the ELECTION spatially diverse even at n_eff == 1? ----
    print("\nMECHANISM CHECK. If temporal averaging cannot be doing the work at")
    print("n_eff == 1, what is? Spatial diversity of the election: neighbouring")
    print("quads folding DIFFERENT frames, hence different sub-pixel phases, so")
    print("ringing lobes never line up into a coherent fringe.")
    i = idx["cr"]
    dif_r = (i[:, 1:] != i[:, :-1])
    sub = pure[:, 1:] & pure[:, :-1]
    frac = float(dif_r[sub].mean())
    d = np.abs(i[:, 1:].astype(np.int64) - i[:, :-1].astype(np.int64))
    print(f"  within the clean n_eff==1 stratum, horizontally adjacent quads elect")
    print(f"  a DIFFERENT frame {100*frac:.2f}% of the time; median |delta index| "
          f"among those = {np.median(d[sub & dif_r]):.0f}")
    res["election_spatial_diversity_pct"] = 100 * frac

    json.dump(res, open(os.path.join(OUT, "k14_pure.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k14_pure.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())