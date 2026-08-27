"""Cut a 1:1 crop out of a master and write it as PNG, with NO resampling.

Every instrument in this directory looks at a crop some statistic chose, and the
presentation JPEGs are downsampled to 1400 px, which is roughly a 5x reduction on
a 33 MP master. Neither shows what a print shows. This does: one rectangle of
output pixels, copied, at native scale.

Deliberately dumb. It selects nothing, scores nothing and stretches nothing, so
there is no statistic here that can pick a flattering site or a flattering tone.
Give it coordinates or a named fraction of the frame and look at the result.

`--grid` writes an NxN array of crops tiled at 1:1 with hairlines between them,
which is how to survey a frame for halos without choosing where to look.

Usage:
  orch_crop.py <master.tiff> <out.png> [--cx FRAC --cy FRAC] [--size N]
  orch_crop.py <master.tiff> <out.png> --grid N [--size N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile


def to8(a: np.ndarray) -> np.ndarray:
    """16-bit -> 8-bit with NO tone map.

    These masters are written by `--srgb`, which has ALREADY applied the camera
    matrix and the sRGB transfer curve. Applying another curve here is a defect
    this project raised once and retracted within the hour. The divisor is
    65535/255 = 257.0 exactly, so this is a pure requantisation.
    """
    return np.clip(a.astype(np.float64) / 257.0, 0, 255).astype(np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("master")
    ap.add_argument("out")
    ap.add_argument("--cx", type=float, default=0.5)
    ap.add_argument("--cy", type=float, default=0.5)
    ap.add_argument("--size", type=int, default=900)
    ap.add_argument("--grid", type=int, default=0)
    a = ap.parse_args()

    src = Path(a.master)
    if not src.exists():
        sys.exit(f"no such master: {src}")
    img = tifffile.imread(str(src))
    if img.dtype != np.uint16:
        # Refuse rather than guess: a float or 8-bit master reaching here means
        # something upstream changed and the /257.0 above would be wrong.
        sys.exit(f"expected uint16 master, got {img.dtype} -- refusing to guess")
    if img.ndim != 3 or img.shape[2] != 3:
        sys.exit(f"expected HxWx3, got {img.shape}")
    h, w, _ = img.shape
    s = a.size
    if s > h or s > w:
        sys.exit(f"crop {s} does not fit in {w}x{h}")

    if a.grid:
        n = a.grid
        # Interior grid: centres at (i+1)/(n+1) so no cell hangs off the edge,
        # where the coverage warp leaves pixels no frame covers.
        gap = 6
        out = np.full((n * s + (n - 1) * gap, n * s + (n - 1) * gap, 3), 255, np.uint8)
        for gy in range(n):
            for gx in range(n):
                cx = int((gx + 1) / (n + 1) * w)
                cy = int((gy + 1) / (n + 1) * h)
                x0 = max(0, min(w - s, cx - s // 2))
                y0 = max(0, min(h - s, cy - s // 2))
                tile = to8(img[y0:y0 + s, x0:x0 + s])
                out[gy * (s + gap):gy * (s + gap) + s,
                    gx * (s + gap):gx * (s + gap) + s] = tile
        label = f"{n}x{n} grid of {s}px 1:1 crops"
    else:
        x0 = max(0, min(w - s, int(a.cx * w) - s // 2))
        y0 = max(0, min(h - s, int(a.cy * h) - s // 2))
        out = to8(img[y0:y0 + s, x0:x0 + s])
        label = f"{s}px 1:1 crop at ({x0},{y0})"

    dst = Path(a.out)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(str(dst.with_suffix(".tmp.tif")), out)
    try:
        import PIL.Image  # noqa: PLC0415
        # PIL mis-reads THIS TOOL's masters, which is why tifffile reads the
        # input above. Writing an ordinary 8-bit PNG from an in-memory array is
        # a different operation and is safe.
        PIL.Image.fromarray(out).save(str(dst))
    finally:
        dst.with_suffix(".tmp.tif").unlink(missing_ok=True)
    print(f"{src.name}: {w}x{h} -> {label} -> {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
