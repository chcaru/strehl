"""Look at what the hull clamp actually removes.

Loads a matched clamped/unclamped pair (both from one binary, so cross-build
CA drift does not apply), finds the site where the clamp took the most
high-frequency energy, and writes 1:1 crops of both arms plus a difference map.

Numeric work is on the GREEN plane in linear DN. The tone curve is applied
only to the PNGs that get looked at, identically to both arms, and nothing
numeric is ever read back off them.

Usage: python hullcrop.py <clamped.tiff> <unclamped.tiff> <outdir> <tag>
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

CROP = 700          # 1:1 crop side, output pixels
TILE = 128          # search tile


def highpass_energy(g):
    """Energy above roughly a quarter of Nyquist: a 3x3 Laplacian residual."""
    lap = (
        4.0 * g[1:-1, 1:-1]
        - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    )
    return lap


def tone(rgb16, lo, hi):
    """Presentation only. The caller passes ONE lo/hi for BOTH arms.

    Deriving lo/hi per arm would give the two crops different curves and
    manufacture a brightness/contrast difference that is mine, not the
    product's. That is the same instrument-across-a-transformation defect
    this project has logged four times; do not reintroduce it.
    """
    x = rgb16.astype(np.float32) / 65535.0
    x = np.clip((x - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    x = np.power(x, 1.0 / 2.2)
    x = x * x * (3.0 - 2.0 * x)
    return (x * 255.0 + 0.5).astype(np.uint8)


def shift_between(a, b, radius=6):
    """Integer-only cross-correlation peak. Sub-pixel resampling would add
    blur to the very quantity being measured, so the search is integer."""
    a = a - a.mean()
    b = b - b.mean()
    best, bdy, bdx = -np.inf, 0, 0
    h, w = a.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            ay0, ay1 = max(0, dy), min(h, h + dy)
            ax0, ax1 = max(0, dx), min(w, w + dx)
            by0, by1 = max(0, -dy), min(h, h - dy)
            bx0, bx1 = max(0, -dx), min(w, w - dx)
            v = float((a[ay0:ay1, ax0:ax1] * b[by0:by1, bx0:bx1]).sum())
            if v > best:
                best, bdy, bdx = v, dy, dx
    return bdy, bdx


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    cl_p, un_p, outdir, tag = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4]
    outdir.mkdir(parents=True, exist_ok=True)

    cl = tifffile.imread(cl_p)
    un = tifffile.imread(un_p)
    assert cl.dtype == np.uint16, f"clamped is {cl.dtype}, expected uint16"
    assert un.dtype == np.uint16, f"unclamped is {un.dtype}, expected uint16"
    assert cl.shape == un.shape, f"shape mismatch {cl.shape} vs {un.shape}"
    print(f"{tag}: shape {cl.shape} dtype {cl.dtype}")

    gc = cl[:, :, 1].astype(np.float32)
    gu = un[:, :, 1].astype(np.float32)

    d = np.abs(gc - gu)
    print(f"{tag}: green |clamped-unclamped|  max {d.max():.1f} DN   "
          f"mean {d.mean():.4f} DN   nonzero {(d > 0).mean() * 100:.4f}%")
    if d.max() == 0:
        print(f"{tag}: ARMS ARE IDENTICAL ON GREEN -- nothing to look at")
        return 1

    hc = highpass_energy(gc)
    hu = highpass_energy(gu)

    # Where did the clamp remove the most high-frequency energy?
    loss = np.abs(hu) - np.abs(hc)
    h, w = loss.shape
    ny, nx = h // TILE, w // TILE
    blocks = loss[: ny * TILE, : nx * TILE].reshape(ny, TILE, nx, TILE)
    score = blocks.sum(axis=(1, 3))
    by, bx = np.unravel_index(np.argmax(score), score.shape)
    cy = int(by * TILE + TILE // 2)
    cx = int(bx * TILE + TILE // 2)
    y0 = max(0, min(cl.shape[0] - CROP, cy - CROP // 2))
    x0 = max(0, min(cl.shape[1] - CROP, cx - CROP // 2))
    print(f"{tag}: worst-loss site at y={y0} x={x0} (tile score {score.max():.3e})")

    # Honest global numbers on green, linear DN, same domain both arms.
    ec = float(np.sqrt((hc ** 2).mean()))
    eu = float(np.sqrt((hu ** 2).mean()))
    print(f"{tag}: GLOBAL highpass RMS  clamped {ec:.3f}  unclamped {eu:.3f}  "
          f"retained {100.0 * ec / eu:.2f}%")

    sc = gc[y0:y0 + CROP, x0:x0 + CROP]
    su = gu[y0:y0 + CROP, x0:x0 + CROP]
    hcc = highpass_energy(sc)
    huc = highpass_energy(su)
    print(f"{tag}: CROP   highpass RMS  clamped {np.sqrt((hcc**2).mean()):.3f}  "
          f"unclamped {np.sqrt((huc**2).mean()):.3f}  "
          f"retained {100.0 * np.sqrt((hcc**2).mean()) / np.sqrt((huc**2).mean()):.2f}%")

    ccl_raw = cl[y0:y0 + CROP, x0:x0 + CROP]
    cun_raw = un[y0:y0 + CROP, x0:x0 + CROP]

    # GEOMETRY CONTROL. If the two arms are not on the same grid, every
    # "texture" difference below is a registration artifact instead.
    dy, dx = shift_between(sc, su)
    print(f"{tag}: GEOMETRY integer shift between arms  dy={dy} dx={dx}  "
          f"(want 0 0; nonzero means the pair is not matched)")

    # ONE tone curve, derived from both arms together, applied to both.
    both = np.concatenate([ccl_raw.ravel(), cun_raw.ravel()]).astype(np.float32) / 65535.0
    lo = float(np.percentile(both, 0.5))
    hi = float(np.percentile(both, 99.7))
    print(f"{tag}: shared tone curve lo={lo:.5f} hi={hi:.5f} (both arms)")
    ccl = tone(ccl_raw, lo, hi)
    cun = tone(cun_raw, lo, hi)
    gap = np.full((CROP, 12, 3), 255, np.uint8)
    Image.fromarray(np.hstack([ccl, gap, cun])).save(
        outdir / f"{tag}--clamped_LEFT__unclamped_RIGHT.png")

    # Difference map, autoscaled, so "where" is visible even if "how much" is small.
    dc = d[y0:y0 + CROP, x0:x0 + CROP]
    m = dc.max()
    Image.fromarray((dc / max(m, 1e-6) * 255).astype(np.uint8)).save(
        outdir / f"{tag}--diff_green_max{m:.0f}DN.png")

    print(f"{tag}: wrote crops to {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
