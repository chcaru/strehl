"""The pixel-exactness null, per channel, with a high-frequency reading.

Usage:
    python nullcheck.py <base.tiff> <x> <y> <label>=<render.tiff> ...

`base` is the directly-demosaiced input (STREHL_ALIGN=0, no warp at all).
Each `render` is a crop-mode render, compared against the window of `base` at
`(x, y)`. For every channel this prints the bit-exact fraction against the base
AND the laplacian energy of both, because "differs" and "is softer" are
different findings and only the second one is an acuity loss.

An identity placement should reproduce the base exactly. Where it does not,
the laplacian ratio says whether the placement is merely relocating values or
is band-limiting them.
"""

import sys

import numpy as np
import tifffile


def lap_energy(p):
    a = p.astype(np.float64)
    lap = 4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    return float((lap * lap).mean())


def main() -> int:
    base = np.asarray(tifffile.imread(sys.argv[1])).astype(np.int64)
    x, y = int(sys.argv[2]), int(sys.argv[3])
    for spec in sys.argv[4:]:
        label, path = spec.split("=", 1)
        r = np.asarray(tifffile.imread(path)).astype(np.int64)
        h, w = r.shape[0], r.shape[1]
        win = base[y : y + h, x : x + w]
        print(f"\n=== {label}  ({w}x{h} vs base window at ({x},{y}))")
        print(f"{'ch':>3}  {'bit-exact':>10}  {'max|d|':>8}  {'mean|d|':>9}  "
              f"{'lap base':>11}  {'lap render':>11}  {'ratio':>8}")
        for c, name in enumerate("RGB"):
            d = np.abs(win[..., c] - r[..., c])
            lb, lr = lap_energy(win[..., c]), lap_energy(r[..., c])
            print(f"{name:>3}  {100.0 * (d == 0).mean():9.4f}%  {int(d.max()):8d}  "
                  f"{d.mean():9.4f}  {lb:11.1f}  {lr:11.1f}  {lr / lb:8.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
