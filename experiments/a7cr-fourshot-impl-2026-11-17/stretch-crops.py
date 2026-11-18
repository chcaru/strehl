"""Side-by-side native crops of smooth bright areas, contrast stretched about
each crop's own mean with one transform for every image (proposal item 1's
eye check: grain from the sensor pattern shows as a fixed mottle).

  python -X utf8 stretch-crops.py OUT.png SIZE STRETCH CHOOSER.tif IMG.tif [IMG.tif ...]

CHOOSER.tif picks the crops and is not shown: the three smoothest 256 px
tiles among the brightest fifth (green, local high-pass energy over level
squared). Each row is one crop, each column one image; every crop is
green - mean, times STRETCH, plus mid-grey, per channel, no resampling.
"""
import sys

import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import gaussian_filter, uniform_filter


def main():
    out, size, stretch = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
    chooser = tifffile.imread(sys.argv[4]).astype(np.float32)
    imgs = [tifffile.imread(f).astype(np.float32) for f in sys.argv[5:]]
    g = chooser[..., 1]
    lvl = gaussian_filter(g, 4.0)
    hp = uniform_filter((g - gaussian_filter(g, 2.0)) ** 2, 32) / np.maximum(lvl, 50.0) ** 2
    h, w = g.shape
    cands = []
    for y in range(256, h - 256 - size, 128):
        for x in range(256, w - 256 - size, 128):
            cands.append((float(lvl[y + size // 2, x + size // 2]), float(hp[y + size // 2, x + size // 2]), y, x))
    bright = np.percentile([c[0] for c in cands], 80)
    pick = sorted([c for c in cands if c[0] >= bright], key=lambda c: c[1])
    chosen = []
    for c in pick:
        if all(abs(c[2] - d[2]) > size or abs(c[3] - d[3]) > size for d in chosen):
            chosen.append(c)
        if len(chosen) == 3:
            break
    rows = []
    for _, _, y, x in chosen:
        tiles = []
        for im in imgs:
            # Grain only: each channel relative to its own 6 px local mean
            # (out-of-focus shading would otherwise saturate the stretch).
            t = im[y - 32:y + size + 32, x - 32:x + size + 32]
            mean = np.stack([gaussian_filter(t[..., c], 6.0) for c in range(3)], -1)
            d = ((t - mean) / np.maximum(mean, 50.0) * stretch + 0.5)[32:-32, 32:-32]
            tiles.append(np.clip(d * 255, 0, 255).astype(np.uint8))
            tiles.append(np.full((size, 8, 3), 255, np.uint8))
        rows.append(np.concatenate(tiles[:-1], 1))
        rows.append(np.full((8, rows[-1].shape[1], 3), 255, np.uint8))
        print(f'crop origin (x {x}, y {y}), {size} px, level {lvl[y + size // 2, x + size // 2]:.0f}')
    Image.fromarray(np.concatenate(rows[:-1], 0)).save(out)


if __name__ == '__main__':
    main()
