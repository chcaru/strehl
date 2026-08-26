"""Three-way 1:1 crops of the gate arms, sites chosen ONCE on the reference.

s31 standing rule: no arm may be judged by its statistic alone, and no arm may
choose its own crop sites. Sites come from the reference arm's gradient ranking
so that a change which invents texture cannot also select the place it is
displayed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

CROP = 400


def luma(a: np.ndarray) -> np.ndarray:
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def to8(t: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(t, 0.5), np.percentile(t, 99.5)
    return np.clip((t.astype(np.float64) - lo) / max(hi - lo, 1e-9) * 255, 0, 255).astype(np.uint8)


def main() -> int:
    out = Path(sys.argv[1])
    paths = [Path(p) for p in sys.argv[2:]]
    arms = [tifffile.imread(p) for p in paths]
    ref = luma(arms[0].astype(np.float64))
    h, w = ref.shape

    # Rank candidate sites on the reference only.
    best = []
    for y in range(CROP, h - 2 * CROP, CROP):
        for x in range(CROP, w - 2 * CROP, CROP):
            t = ref[y:y + CROP, x:x + CROP]
            gy, gx = np.gradient(t)
            best.append((np.hypot(gy, gx).mean(), y, x))
    best.sort(reverse=True)
    sites = [(y, x) for _, y, x in best[:3]]

    tiles = []
    for y, x in sites:
        row = [to8(a[y:y + CROP, x:x + CROP]) for a in arms]
        tiles.append(np.concatenate(row, axis=1))
    grid = np.concatenate(tiles, axis=0)
    Image.fromarray(grid).save(out)
    print(f"sites (from {paths[0].name}): {sites}")
    print("columns, left to right: " + ", ".join(p.name for p in paths))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
