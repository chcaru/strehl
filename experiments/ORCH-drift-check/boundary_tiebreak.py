"""Is the frame-0 pile-up depth, or is it the argmax defect breaking ties low?

boundary_where.py found that 29.81% of flowers-cpl pixels elect frame 0 while
only 0.18% elect frame 175 -- a 165x asymmetry -- and that they are spread
evenly across the frame (centre 30.79%, outer ring 27.53%) rather than
concentrated anywhere. Neither hypothesis in captures-needed.md section 23
predicts that.

A third hypothesis does. `argmax-baseline` is the NAIVE per-pixel argmax that
this project exists to demonstrate is defective. In a region with no focus
signal the response is flat to within noise, and if ties resolve toward the
lowest index then every such pixel reports frame 0 -- uniformly, everywhere
there is no texture, which on a white flower is most of the frame.

DISCRIMINATOR: depth is a property of position; tie-breaking is a property of
local contrast. So split pixels by local contrast and compare.

  If frame-0 election is concentrated in LOW-CONTRAST pixels, it is the argmax
  defect and the boundary statistic is contaminated by it.

  If frame-0 election is independent of contrast, it is depth and section 23's
  hypothesis (1) survives.

PRE-REGISTERED BAR: the ratio of frame-0 rate in the lowest contrast decile to
that in the highest decile. Above 3x reads as contamination; below 1.5x reads
as depth; between is unresolved and will be reported as unresolved.

NULL CONTROL: the same split applied to a SHUFFLED contrast map must show a
ratio of ~1.0, or the split itself is manufacturing the effect.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\ORCH-flowers")
IDX = OUT / "argmax-index.tif"
LIN = OUT / "linear.tif"   # written by flowers_blame.py, same binned grid


def main():
    for p in (IDX, LIN):
        if not p.exists():
            print(f"missing {p} -- run boundary_where.py and flowers_blame.py first")
            return 1

    idx = tifffile.imread(IDX)
    lin = tifffile.imread(LIN).astype(np.float64)
    if lin.ndim == 3:
        lin = lin.mean(axis=2)
    lin /= lin.max() if lin.max() > 0 else 1.0

    print(f"index {idx.shape}  linear {lin.shape}")
    if idx.shape != lin.shape:
        h = min(idx.shape[0], lin.shape[0])
        w = min(idx.shape[1], lin.shape[1])
        print(f"  cropping both to {h} x {w}")
        idx, lin = idx[:h, :w], lin[:h, :w]

    hi = int(idx.max())
    is0 = idx == 0

    # Local contrast: std over a 15x15 window, via integral images so it is
    # cheap on 8 Mpx. Computed on the MERGED render, which is the only
    # texture reference available that is not itself one elected frame.
    r = 7
    pad = np.pad(lin, r, mode="edge")
    c1 = pad.cumsum(0).cumsum(1)
    c2 = (pad * pad).cumsum(0).cumsum(1)

    def boxsum(c):
        return (c[2 * r:, 2 * r:] - c[:-2 * r, 2 * r:]
                - c[2 * r:, :-2 * r] + c[:-2 * r, :-2 * r])

    n = (2 * r) ** 2
    s1, s2 = boxsum(c1), boxsum(c2)
    var = np.maximum(s2 / n - (s1 / n) ** 2, 0.0)
    contrast = np.sqrt(var)[:idx.shape[0], :idx.shape[1]]

    def decile_ratio(cmap, tag):
        lo_t = np.quantile(cmap, 0.10)
        hi_t = np.quantile(cmap, 0.90)
        lo = cmap <= lo_t
        hi_m = cmap >= hi_t
        r_lo = float(is0[lo].mean())
        r_hi = float(is0[hi_m].mean())
        ratio = r_lo / r_hi if r_hi > 0 else float("inf")
        print(f"  {tag:<22} frame-0 rate  low-contrast {100*r_lo:6.2f}%   "
              f"high-contrast {100*r_hi:6.2f}%   ratio {ratio:7.2f}x")
        return ratio

    print()
    print("=" * 78)
    real = decile_ratio(contrast, "real contrast map")

    rng = np.random.default_rng(20260824)
    flat = contrast.ravel().copy()
    rng.shuffle(flat)
    null = decile_ratio(flat.reshape(contrast.shape), "NULL shuffled map")

    print()
    print(f"overall frame-0 rate: {100 * float(is0.mean()):.2f}%   "
          f"frame-{hi} rate: {100 * float((idx == hi).mean()):.2f}%")
    print()
    assert 0.7 < null < 1.4, (
        f"NULL CONTROL FAILED: shuffled map gave {null:.2f}x, not ~1.0 -- "
        "the decile split itself is manufacturing the effect")
    print(f"NULL CONTROL PASSED: shuffled map {null:.2f}x, effect is not an artifact of the split")
    print()
    if real > 3.0:
        print(f"VERDICT: CONTAMINATION ({real:.2f}x > 3x bar).")
        print("  The frame-0 pile-up tracks LOW LOCAL CONTRAST, not position.")
        print("  It is the argmax defect resolving ties toward the lowest index,")
        print("  and the boundary statistic inherits it.")
    elif real < 1.5:
        print(f"VERDICT: DEPTH ({real:.2f}x < 1.5x bar).")
        print("  Frame-0 election is independent of contrast, so it reflects")
        print("  scene geometry and section 23 hypothesis (1) survives.")
    else:
        print(f"VERDICT: UNRESOLVED ({real:.2f}x, between the 1.5x and 3x bars).")
        print("  Report as unresolved. Do not guess.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
