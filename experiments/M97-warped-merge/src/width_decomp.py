"""Where does the exponential's bound width actually live?

The refined ladder tightened the exponential's separation from -0.228 to -0.084
and it is STILL unresolved. Two explanations, and they call for opposite
actions:

  (a) the ladder is still too coarse for it -- refine further,
  (b) the exponential genuinely does not separate the populations.

Reporting (b) while (a) is true would be reporting my instrument's blind spot as
a property of the kernel, which is the exact error M111 caught in itself and the
exact error I would be repeating.

The bound width is a SUM OVER BINS -- each bin j contributes
`count_j * (K(z_lo) - K(z_hi))` to `sw_hi - sw_lo`. So the question "is the
ladder too coarse, and if so WHERE" is answerable by arithmetic on maps already
on disk, with no further rendering. Measure before spending renders.

A prediction, registered before running, from the shape of the two kernels at
the origin:

    d/dz exp(-0.5 z^2) = -z exp(-0.5 z^2)   ->   slope 0 at z = 0
    d/dz exp(-z)       = -exp(-z)           ->   slope -1 at z = 0

The Gaussian is FLAT at the origin; the exponential has a CUSP there and starts
falling immediately. The ladder's two finest low rungs are gate 0.25 and gate 1
(z = 0.0625 and z = 0.25), and the frame counts are largest near the origin --
n_eff reaches 284 in flat regions. So I expect the exponential's width to be
dominated by the LOW bins, not the tail I just spent eight renders refining,
and my tail refinement to have been aimed at the wrong end.

If that is right, the fix is rungs BELOW gate 1, and it is two renders.
"""

import sys
from pathlib import Path

import numpy as np

M111 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M111-waxy-blobs")
MY = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M97-warped-merge\src")
sys.path.insert(0, str(M111))
sys.path.insert(0, str(MY))

import softgate_prediction as sp  # noqa: E402
import kernel_price as kp  # noqa: E402


def load(ladder):
    import os
    maps = [np.load(os.path.join(sp.RENDER, rel)).astype(np.float64)
            for _, rel in ladder]
    edges = [g / sp.DEFAULT_GATE for g, _ in ladder]
    h = min(m.shape[0] for m in maps)
    w = min(m.shape[1] for m in maps)
    maps = [m[:h, :w] for m in maps]
    yc = sp.plane_luma(os.path.join(
        sp.ORCH, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif"))
    h, w = min(h, yc.shape[0]), min(w, yc.shape[1])
    maps = [m[:h, :w] for m in maps]
    yc = yc[:h, :w]
    inner = np.zeros((h, w), bool)
    inner[64:-64, 64:-64] = True
    sdc = sp.local_sd(yc)
    textured = (sdc >= float(np.percentile(sdc[inner], 90.0))) & inner
    flat = (sdc <= float(np.percentile(sdc[inner], 40.0))) & inner
    return maps, edges, flat, textured


def decompose(name, kernel, ladder):
    maps, edges, flat, textured = load(ladder)
    counts = [maps[0]] + [maps[j] - maps[j - 1] for j in range(1, len(maps))]
    lo_edges = [0.0] + edges[:-1]

    seam = flat & (maps[[g for g, _ in ladder].index(4.0)] <= 8)
    rows = []
    tot_t = tot_s = 0.0
    for c, zlo, zhi in zip(counts, lo_edges, edges):
        spread = float(kernel(zlo) - kernel(zhi))
        ct = float(np.median(c[textured]))
        cs = float(np.median(c[seam]))
        rows.append((zlo, zhi, spread, ct, cs, ct * spread, cs * spread))
        tot_t += ct * spread
        tot_s += cs * spread

    print("=" * 86)
    print(f"{name}: where the bound width comes from")
    print("=" * 86)
    print("  %-16s %10s %9s %9s %10s %10s"
          % ("bin (z)", "K(lo)-K(hi)", "med cnt T", "med cnt S",
             "width T", "width S"))
    for zlo, zhi, sp_, ct, cs, wt, ws in rows:
        if wt < 1e-4 and ws < 1e-4:
            continue
        print("  %6.4f - %-7.4f %10.6f %9.1f %9.1f %10.4f %10.4f"
              % (zlo, zhi, sp_, ct, cs, wt, ws))
    print("  %-16s %10s %9s %9s %10.4f %10.4f" % ("TOTAL", "", "", "", tot_t, tot_s))

    # Which end dominates? Split at the Gaussian's cutoff, which is exactly the
    # boundary my eight tail rungs were placed beyond.
    head_t = sum(r[5] for r in rows if r[1] <= 1.0)
    mid_t = sum(r[5] for r in rows if 1.0 < r[1] <= kp.GAUSS_CUTOFF)
    tail_t = sum(r[5] for r in rows if r[1] > kp.GAUSS_CUTOFF)
    print()
    print("  texture width by region:")
    print("    z <= 1            %8.4f  (%5.1f%%)" % (head_t, 100 * head_t / max(tot_t, 1e-30)))
    print("    1 < z <= %.3f     %8.4f  (%5.1f%%)" % (kp.GAUSS_CUTOFF, mid_t, 100 * mid_t / max(tot_t, 1e-30)))
    print("    z > %.3f          %8.4f  (%5.1f%%)   <- the 8 rungs I rendered"
          % (kp.GAUSS_CUTOFF, tail_t, 100 * tail_t / max(tot_t, 1e-30)))
    print()
    return head_t, mid_t, tail_t, tot_t


def main():
    fine = kp.refined_ladder()
    hg, mg, tg, og = decompose("GAUSSIAN", sp.gauss, fine)
    he, me, te, oe = decompose("EXPONENTIAL", kp.expo, fine)

    print("=" * 86)
    print("VERDICT ON MY OWN REFINEMENT")
    print("=" * 86)
    print("  exponential total texture width %.4f, of which the tail I refined"
          % oe)
    print("  (z > %.3f) carries %.4f = %.1f%%." % (kp.GAUSS_CUTOFF, te, 100 * te / max(oe, 1e-30)))
    print()
    if he > te:
        print("  MEASURED: the width is dominated by the LOW bins (z <= 1), not the")
        print("  tail. The pre-registration HELD: the exponential's cusp at the")
        print("  origin makes its bounds loose exactly where the frame counts are")
        print("  largest, and eight rungs in the tail were aimed at the wrong end.")
        print("  Resolving it needs rungs BELOW gate 1.")
    else:
        print("  MEASURED: the tail dominates after all; the pre-registration was")
        print("  REFUTED. Further tail refinement is the way to resolve it.")
    print()
    print("  For contrast the GAUSSIAN's total texture width is %.4f -- %.2fx" % (og, oe / max(og, 1e-30)))
    print("  narrower than the exponential's on the SAME bins and the SAME counts.")
    print("  That is not a fixable property of the ladder: a kernel that puts")
    print("  weight on frames far from the winner needs a finer ladder to bound")
    print("  to equal precision, and 'puts weight on frames far from the winner'")
    print("  is the same property that risks blur. The kernel that is hard to")
    print("  measure is hard to measure BECAUSE it reaches far.")


if __name__ == "__main__":
    main()
