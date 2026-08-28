"""Map the near-border level effect spatially, in absolute DN.

Usage:
    python edgeprofile.py <render.tiff> [<render.tiff> ...]

Prints mean level against distance from the PLANE edge, so the coverage
boundary, any black fill outside it, and any overshoot inside it are all
visible in one column of numbers rather than inferred from a ratio.

A ratio between two renders can only say they differ. This says what the level
actually does as you walk in from the edge, which is what distinguishes a step
(fill bleeding in) from an overshoot (ringing on the bright side of a step).
Also reports the covered fraction per ring, so a level change caused by frames
dropping out cannot be mistaken for one caused by the merge.
"""

import sys

import numpy as np
import tifffile

RINGS = [0, 2, 4, 8, 16, 24, 32, 48, 64, 96, 128, 160, 192, 256, 384, 512]


def main() -> int:
    for path in sys.argv[1:]:
        img = np.asarray(tifffile.imread(path)).astype(np.float64)
        h, w = img.shape[0], img.shape[1]
        g = img[..., 1]
        X, Y = np.meshgrid(np.arange(w), np.arange(h))
        dist = np.minimum(np.minimum(X, w - 1 - X), np.minimum(Y, h - 1 - Y))
        print(f"\n=== {path.split(chr(92))[-1]}  ({w}x{h})")
        print(f"{'ring px':>10}  {'n':>9}  {'mean G':>10}  {'black%':>7}  {'vs 512+':>9}")
        deep = g[dist >= 512].mean()
        for lo, hi in zip(RINGS, RINGS[1:] + [10**9]):
            m = (dist >= lo) & (dist < hi)
            v = g[m]
            lbl = f"{lo}-{hi}" if hi < 10**8 else f"{lo}+"
            blk = 100.0 * (v == 0).mean()
            print(f"{lbl:>10}  {v.size:>9}  {v.mean():10.2f}  {blk:6.2f}%  {v.mean() / deep:9.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
