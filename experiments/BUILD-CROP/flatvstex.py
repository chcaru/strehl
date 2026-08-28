"""Is the energy an identity placement removes from R and B detail, or noise?

Usage:
    python flatvstex.py <base.tiff> <render.tiff> <x> <y>

The base plane for R and B is one raw CFA sample per quad; the green plane is
the mean of two. So base R carries both real chroma detail AND the aliasing and
per-sample noise of a critically-sampled subgrid, and a laplacian-energy drop
alone cannot say which of those an identity placement removed.

This splits the frame by LOCAL STRUCTURE, using the GREEN plane -- which is
reproduced exactly by the placement and is therefore an unbiased referee that
cannot itself be moved by the effect under test. Flat cells are noise-dominated,
textured cells are detail-dominated. If the R/B loss is uniform across both, it
is noise and aliasing. If it concentrates in textured cells, it is detail.
"""

import sys

import numpy as np
import tifffile


def lap(a):
    """Squared laplacian, kept at the input's shape so cell grids line up."""
    a = a.astype(np.float64)
    out = np.zeros_like(a)
    out[1:-1, 1:-1] = (
        4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    )
    return out * out


def main() -> int:
    base = np.asarray(tifffile.imread(sys.argv[1]))
    rend = np.asarray(tifffile.imread(sys.argv[2]))
    x, y = int(sys.argv[3]), int(sys.argv[4])
    h, w = rend.shape[0], rend.shape[1]
    win = base[y : y + h, x : x + w]

    # Referee: green gradient magnitude, block-averaged into 32x32 cells.
    g = win[..., 1].astype(np.float64)
    gy, gx = np.gradient(g)
    gm = np.hypot(gx, gy)
    b = 32
    ch, cw = h // b, w // b
    cells = gm[: ch * b, : cw * b].reshape(ch, b, cw, b).mean(axis=(1, 3))
    q = np.percentile(cells, [25, 75])
    flat = cells <= q[0]
    tex = cells >= q[1]
    print(f"cells {cw}x{ch} of {b}px; green gradient p25={q[0]:.2f} p75={q[1]:.2f}")
    print(f"{'ch':>3}  {'partition':>10}  {'lap base':>12}  {'lap render':>12}  {'ratio':>8}")
    for c, name in enumerate("RGB"):
        lb = lap(win[..., c])
        lr = lap(rend[..., c])
        lb = lb[: ch * b, : cw * b].reshape(ch, b, cw, b).mean(axis=(1, 3))
        lr = lr[: ch * b, : cw * b].reshape(ch, b, cw, b).mean(axis=(1, 3))
        for label, m in (("flat", flat), ("textured", tex)):
            print(f"{name:>3}  {label:>10}  {lb[m].mean():12.1f}  {lr[m].mean():12.1f}  "
                  f"{lr[m].mean() / lb[m].mean():8.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
