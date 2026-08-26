"""The deficit in absolute DN and its full distribution, not a mean.

A mean hides the localised failure this milestone was sent to look for, so every
number here is a percentile over tiles and the absolute DN shortfall is reported
next to the ratio.
"""
import numpy as np
from curve import arms

GATE = 0.80
PC = [5, 10, 25, 50, 75, 90, 95]
for subj in ("bee-1-cpl", "flowers-cpl"):
    for g, tag in ((0.0, "ungated"), (GATE, f"gate {GATE}")):
        a = arms(subj, peak_min=g)
        real = a["snr"] >= 3.0
        r = a["ratio"][real]
        fd = np.sqrt(a["Sft"][real]); md = np.sqrt(a["Smt"][real])
        deficit = fd - md                       # DN of fine-band amplitude
        print(f"\n{subj}  [{tag}]  {int(real.sum())} of 352 tiles hold frame detail "
              f"(SNR>=3); {2*a['na']} of {a['nd']} frames read")
        print(f"  merge <  best frame : {100*np.mean(r < 1.0):5.1f}% of them "
              f"({int(np.sum(r < 1.0))} tiles)")
        print(f"  merge >= best frame : {100*np.mean(r >= 1.0):5.1f}% "
              f"({int(np.sum(r >= 1.0))} tiles)")
        print("  " + "ratio        " + "  ".join(f"p{q:02d} {np.percentile(r,q):7.3f}" for q in PC))
        print("  " + "deficit DN   " + "  ".join(f"p{q:02d} {np.percentile(deficit,q):+7.1f}" for q in PC))
        sub = deficit[r < 1.0]
        if sub.size:
            print(f"  among the {sub.size} tiles where the merge is behind, shortfall DN: "
                  f"med {np.median(sub):.1f}  p90 {np.percentile(sub,90):.1f}  max {sub.max():.1f}"
                  f"   (frame detail there med {np.median(fd[r<1.0]):.1f} DN)")
        worst = np.argsort(r)[:3]
        ij = np.argwhere(real)
        print("  worst three: " + " | ".join(
            f"({ij[w][0]},{ij[w][1]}) ratio {r[w]:.3f} frame {fd[w]:.0f} merge {md[w]:.0f} DN"
            for w in worst))
