"""DIAGNOSTIC for the pre-registered clip guard, which rejected 110 of 110
tiles on its first run.

This exists because the guard in PREREGISTRATION.md sec.2 item 4 was written
for a display-referred image and these are LINEAR renders.  In linear light
most of a frame sits near zero -- that is what linear means -- so a
"min <= 0.02 anywhere in the tile" test is not a clipping test, it is a test of
whether the scene contains shadow.  Before changing anything I want the
numbers, so the deviation can be argued from measurement rather than from
convenience.

INVOCATION (rule 47).  Reads the same three arms and census.npz.  Prints only.

    python clipdiag.py
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from noisefree import Arm, LIN, CACHE, CLIP_HI, CLIP_LO, FREE   # noqa: E402


def main():
    z = np.load(CACHE)
    cells = [tuple(c) for c in z["cells"][z["flat"]]]
    arms = {"strehl": Arm(rf"{LIN}\113-full-g1.tiff", 1.0, 16, "")}
    for tag in ("enfuse", "fs15"):
        cfg = FREE[tag]
        arms[tag] = Arm(cfg["path"], cfg["scale"], cfg["bits"], cfg["label"])

    print(f"{len(cells)} FLAT tiles.  Per-tile extremes, over all three arms:")
    lo_any, hi_any, means = [], [], []
    for (y, x) in cells:
        mn, mx, mu = 1.0, 0.0, []
        for a in arms.values():
            b = a.rgb(y, x)
            if b is None:
                mn, mx = 0.0, 1.0
                break
            mn = min(mn, float(b.min()))
            mx = max(mx, float(b.max()))
            mu.append(float(b.mean()))
        lo_any.append(mn)
        hi_any.append(mx)
        means.append(np.mean(mu))
    lo_any = np.array(lo_any)
    hi_any = np.array(hi_any)
    means = np.array(means)

    qs = [0, 5, 25, 50, 75, 95, 100]
    print("\n  tile MIN percentiles: " +
          "  ".join(f"p{q}={v:.4f}" for q, v in
                    zip(qs, np.percentile(lo_any, qs))))
    print("  tile MAX percentiles: " +
          "  ".join(f"p{q}={v:.4f}" for q, v in
                    zip(qs, np.percentile(hi_any, qs))))
    print("  tile MEAN percentiles: " +
          "  ".join(f"p{q}={v:.4f}" for q, v in
                    zip(qs, np.percentile(means, qs))))

    print(f"\n  fails min<= {CLIP_LO}:  {int((lo_any <= CLIP_LO).sum())} "
          f"of {len(cells)}")
    print(f"  fails max>= {CLIP_HI}:  {int((hi_any >= CLIP_HI).sum())} "
          f"of {len(cells)}")
    print(f"  fails BOTH:          "
          f"{int(((lo_any <= CLIP_LO) & (hi_any >= CLIP_HI)).sum())}")

    print("\n  If the guard is restated as a FRACTION of the tile rather than")
    print("  its single most extreme sample, survivors at various tolerances:")
    for frac in (0.0, 0.001, 0.01, 0.05):
        n = 0
        for (y, x) in cells:
            bad = False
            for a in arms.values():
                b = a.rgb(y, x)
                if b is None:
                    bad = True
                    break
                if ((b >= CLIP_HI).mean() > frac
                        or (b <= 1e-9).mean() > frac):
                    bad = True
                    break
            n += (not bad)
        print(f"    hard-clip fraction tolerance {frac:<6}: {n} tiles survive")

    # WHICH arm clips matters for the direction of any bias introduced by
    # dropping the affected tiles, so it is measured rather than assumed.
    print("\n  Hard black clipping (samples at exactly 0), per arm:")
    for k, a in arms.items():
        ntile, frac_max, tot = 0, 0.0, 0.0
        for (y, x) in cells:
            b = a.rgb(y, x)
            if b is None:
                continue
            f = float((b <= 1e-9).mean())
            ntile += f > 0
            frac_max = max(frac_max, f)
            tot += f
        print(f"    {k:8s} {ntile:3d}/{len(cells)} tiles contain a zero; "
              f"worst tile {frac_max * 100:6.3f}% of samples; "
              f"mean over tiles {tot / len(cells) * 100:6.4f}%")

    print("\n  Level context: these FLAT tiles are also the DARK tiles.")
    print("  8-bit quantiser step 1/255 = 0.00392 against a median tile mean")
    print(f"  of {np.median(means):.4f} -- i.e. "
          f"{0.00392 / float(np.median(means)) * 100:.1f}% of the tile level.")
    print("  That is why the QUANT8 commissioning arm exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
