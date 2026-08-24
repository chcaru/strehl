"""M104 C0 -- geometry probe.  How many ROIs actually carry a comb?

INERT is a registered bar (>= 8 live ROIs).  The first configuration returned
7 and went red.  Rather than lower the bar -- which would be the exact move
this project punishes -- this probe searches the ROI geometry for a
configuration that clears it, on the CONTROL image only, with no baseline
number in sight.  Tuning an instrument against planted ground truth before
looking at the data is the right way round; tuning it against the data is not.

Reported for each candidate: live ROI count, whether the ROIs overlap (they
must not, or the across-ROI SE is inflated by shared pixels), and the FFT bin
size against the +/- 0.004 bar.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m104lib as L

BASE = Path(L.RENDERS) / "flat-on-ruler-cpl-PRE-A0-g0.tif"

CANDIDATES = [
    (768, 5, 4), (768, 6, 4), (640, 6, 4), (640, 7, 5),
    (512, 6, 4), (512, 7, 5), (512, 8, 5), (384, 8, 6),
]


def main() -> None:
    a = L.green(BASE)
    h, w = a.shape
    print(f"base {w} x {h}   {BASE.name}")
    print(f"{'ROI':>5} {'cols':>5} {'rows':>5} {'tot':>5} {'live':>5} "
          f"{'overlap':>8} {'bin':>9} {'medS/B':>8}")
    for n, c, r in CANDIDATES:
        L.ROI = n
        ov = (c * n > w) or (r * n > h)
        seed = L.seed_combs(a, cols=c, rows=r)
        sb = sorted(s["sb"] for s in seed.values())
        med = sb[len(sb) // 2] if sb else 0.0
        f0 = sorted(s["f0"] for s in seed.values())
        f0m = f0[len(f0) // 2] if f0 else 0.0
        # relative frequency resolution of one raw FFT bin at the comb
        rel = (1.0 / n) / f0m if f0m else float("inf")
        print(f"{n:5d} {c:5d} {r:5d} {c*r:5d} {len(seed):5d} "
              f"{'YES' if ov else 'no':>8} {rel:9.4f} {med:8.2f}")


if __name__ == "__main__":
    main()
