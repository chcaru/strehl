"""Pick the most chroma-active tile in a render and emit 1:1 before/after crops.

The tile is CHOSEN BY THE DATA, not by eye: it is the one maximising
high-frequency energy in the colour-difference plane R-G, which is where a
chroma resample either helps or hurts. Choosing it from the BEFORE image only
means the choice cannot be tuned to flatter the AFTER one.

Both arms are linear renders, asserted. They are converted to 8-bit sRGB for
viewing only -- the sRGB curve is applied HERE, at the last step, and no DN in
any measurement script ever passes through it. PIL is used only to write the
8-bit PNG; every 16-bit read in this directory goes through tifffile.

Usage: python crops.py BEFORE.tif AFTER.tif OUTDIR [tile]
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

TILE = 480


def load(path: str) -> np.ndarray:
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        desc = page.tags["ImageDescription"].value
        arr = page.asarray()
    assert arr.dtype == np.uint16, f"{path}: dtype {arr.dtype}"
    # ASSERT THE COLOUR SPACE before any DN is touched.
    assert "no transfer curve" in desc.lower(), (
        f"{path}: expected a LINEAR render, got {desc[:80]!r}"
    )
    return arr


def srgb8(linear16: np.ndarray) -> np.ndarray:
    """Linear 16-bit -> 8-bit sRGB, for VIEWING ONLY."""
    v = linear16.astype(np.float64) / 65535.0
    v = np.clip(v, 0.0, 1.0)
    enc = np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(v, 1 / 2.4) - 0.055)
    return np.clip(enc * 255.0 + 0.5, 0, 255).astype(np.uint8)


def pick_tile(arr: np.ndarray, tile: int) -> tuple:
    """Tile with the most high-frequency energy in R-G."""
    chroma = arr[:, :, 0].astype(np.float64) - arr[:, :, 1].astype(np.float64)
    # High-pass by a 3x3 Laplacian, then integrate energy per tile.
    lap = np.abs(4.0 * chroma[1:-1, 1:-1] - chroma[:-2, 1:-1] - chroma[2:, 1:-1]
                 - chroma[1:-1, :-2] - chroma[1:-1, 2:])
    h, w = lap.shape
    ny, nx = h // tile, w // tile
    best, score = (0, 0), -1.0
    for iy in range(ny):
        for ix in range(nx):
            s = float(lap[iy * tile:(iy + 1) * tile, ix * tile:(ix + 1) * tile].sum())
            if s > score:
                score, best = s, (iy * tile, ix * tile)
    return best


def main() -> None:
    before_path, after_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    tile = int(sys.argv[4]) if len(sys.argv) > 4 else TILE
    before, after = load(before_path), load(after_path)
    assert before.shape == after.shape, "arms differ in shape"

    y, x = pick_tile(before, tile)
    print(f"tile chosen from BEFORE only: y={y} x={x} size={tile}")

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    crops = {}
    for name, arr in (("before", before), ("after", after)):
        c = srgb8(arr[y:y + tile, x:x + tile, :])
        crops[name] = c
        Image.fromarray(c).save(out / f"crop-{name}.png")
        print(f"  wrote {out / f'crop-{name}.png'}")

    pair = np.concatenate(
        [crops["before"], np.full((tile, 8, 3), 255, np.uint8), crops["after"]], axis=1
    )
    Image.fromarray(pair).save(out / "crop-pair.png")
    print(f"  wrote {out / 'crop-pair.png'}  (left = before, right = after, 1:1)")


if __name__ == "__main__":
    main()
