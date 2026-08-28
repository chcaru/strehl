"""Estimate the sub-pixel shift of each channel between two renders.

Usage:
    python subshift.py <base.tiff> <render.tiff> <x> <y>

The integer-offset scan already reported argmin (0,0) for the R/B null
failure, which only rules out shifts of a whole pixel or more. A chroma PHASE
error is a quarter of a pixel and is invisible to that test, so this solves for
translation directly.

Gradient (Lucas-Kanade) estimate: for a pure translation, the intensity
difference is d = -(gx*dx + gy*dy), so the least-squares solution over all
pixels recovers (dx, dy) to well under a pixel. Reported per channel, with the
residual before and after, because a shift model that does not reduce the
residual has not explained the difference.

Prediction under the co-siting hypothesis: green ~0, and R and B displaced in
OPPOSITE directions by about a quarter of a quad pixel.
"""

import sys

import numpy as np
import tifffile


def solve(a, b):
    """Least-squares translation taking `a` onto `b`, plus residuals."""
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    gy, gx = np.gradient(a)
    # Trim the border: gradients there are one-sided.
    s = (slice(8, -8), slice(8, -8))
    gx, gy, d = gx[s], gy[s], (b - a)[s]
    A = np.array([[(gx * gx).sum(), (gx * gy).sum()], [(gx * gy).sum(), (gy * gy).sum()]])
    rhs = np.array([-(gx * d).sum(), -(gy * d).sum()])
    dx, dy = np.linalg.solve(A, rhs)
    before = float(np.sqrt((d * d).mean()))
    after = float(np.sqrt(((d + gx * dx + gy * dy) ** 2).mean()))
    return dx, dy, before, after


def main() -> int:
    base = np.asarray(tifffile.imread(sys.argv[1]))
    rend = np.asarray(tifffile.imread(sys.argv[2]))
    x, y = int(sys.argv[3]), int(sys.argv[4])
    h, w = rend.shape[0], rend.shape[1]
    win = base[y : y + h, x : x + w]
    print(f"window {w}x{h} at ({x},{y})")
    print(f"{'ch':>3}  {'dx px':>9}  {'dy px':>9}  {'rms before':>11}  {'rms after':>10}  {'explained':>10}")
    for c, name in enumerate("RGB"):
        dx, dy, b0, b1 = solve(win[..., c], rend[..., c])
        expl = "n/a" if b0 == 0 else f"{100.0 * (1 - b1 / b0):9.2f}%"
        print(f"{name:>3}  {dx:9.4f}  {dy:9.4f}  {b0:11.3f}  {b1:10.3f}  {expl:>10}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
