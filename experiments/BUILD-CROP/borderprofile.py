"""Edge profile: mean level of the outermost rows/columns against the interior.

Usage:
    python borderprofile.py <img.tiff> [n]

Black fill from outside the covered region can be dragged inward by a merge
whose support is wider than a pixel -- the pyramid's coarse bands especially.
If the crop rectangle is drawn tightly enough to keep that fill out of the
picture, the outermost columns look like the interior; if it is not, they ramp
down towards the edge. This prints the ramp so the question is answered by a
number instead of by an argument about kernel support.
"""

import sys

import numpy as np
import tifffile


def main() -> int:
    p = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    a = np.asarray(tifffile.imread(p)).astype(np.float64)
    g = a[..., 1]
    h, w = g.shape
    # Interior reference: the middle half of the frame, well away from any edge.
    interior = g[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4].mean()
    print(f"{p}  {w}x{h}  interior mean (middle half) = {interior:.2f} DN")
    cols = g.mean(axis=0)
    rows = g.mean(axis=1)
    print("  col idx :   left mean   (frac of interior) |  right idx :  right mean")
    for i in list(range(0, 6)) + [8, 12, 16, 24, 40]:
        if i >= n and i > 16:
            pass
        j = w - 1 - i
        print(
            f"   {i:5d}  : {cols[i]:10.2f}   {cols[i] / interior:6.4f}          "
            f"{j:6d}  : {cols[j]:10.2f}   {cols[j] / interior:6.4f}"
        )
    print("  row idx :    top mean   (frac of interior) |    bot idx :    bot mean")
    for i in list(range(0, 6)) + [8, 12, 16, 24, 40]:
        j = h - 1 - i
        print(
            f"   {i:5d}  : {rows[i]:10.2f}   {rows[i] / interior:6.4f}          "
            f"{j:6d}  : {rows[j]:10.2f}   {rows[j] / interior:6.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
