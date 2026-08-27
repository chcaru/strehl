"""Attribution: is the chroma excess made by the GATHER, or by the pyramid
merge's SOFT SELECTION (weight = band power ^ exponent, a noise-dependent
nonlinear operator that my linear restoration model does not contain)?

--gate 0 makes the estimator emit the ELECTED FRAME with no averaging and no
band-power weighting (BUILD-SHARP 1(a): byte-identical to the elected frame).
So a gate-0 render isolates the gather.  If the chroma excess collapses toward
the kernel-ratio prediction there, the merge made it, not the double demosaic.
"""
import sys, json
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from ab import render
for subj in ("foam", "couch-fibers-cpl"):
    for arm in ("1", "0"):
        d = render(subj, arm, 12, "gate0", extra=["--gate", "0"])
        print(f"{subj:20s} arm={arm} rc={d['rc']} workers={d['workers']} "
              f"wall={d['wall_s']:.1f}s", flush=True)
        if d["rc"] != 0:
            print(d.get("err", "")[-800:])
