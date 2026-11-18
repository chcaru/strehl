"""Side-by-side native crops of detailed areas, one display transform for
every image (orientation for the final renders, not a measurement).

  python -X utf8 detail-crops.py OUT.png SIZE CHOOSER.tif IMG.tif [IMG.tif ...]

CHOOSER.tif picks the crops: the three tiles with the most green high-pass
energy among those under 0.5 % near clipping, at least 2 SIZE apart. Each row
is one crop, each column one image; display is linear / the chooser's 99.9th
percentile, then a 2.2 gamma, no resampling. Prints the crop origins.
"""
import sys

import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import gaussian_filter


def main():
    out, size = sys.argv[1], int(sys.argv[2])
    chooser = tifffile.imread(sys.argv[3]).astype(np.float32)
    imgs = [tifffile.imread(f).astype(np.float32) for f in sys.argv[4:]]
    g = chooser[..., 1]
    hp = gaussian_filter((g - gaussian_filter(g, 1.5)) ** 2, 16.0)
    top = float(np.percentile(chooser, 99.9))
    clip = 0.95 * float(chooser.max())
    h, w = g.shape
    cands = []
    for y in range(0, h - size, size // 2):
        for x in range(0, w - size, size // 2):
            if (chooser[y:y + size, x:x + size] > clip).mean() > 0.005:
                continue
            cands.append((float(hp[y:y + size, x:x + size].mean()), y, x))
    cands.sort(reverse=True)
    picks = []
    for _, y, x in cands:
        if all(abs(y - py) >= 2 * size or abs(x - px) >= 2 * size for py, px in picks):
            picks.append((y, x))
        if len(picks) == 3:
            break
    rows = []
    for y, x in picks:
        print(f'crop origin (x {x}, y {y}), {size} px')
        cols = [np.clip(im[y:y + size, x:x + size] / top, 0, 1) ** (1 / 2.2) for im in imgs]
        rows.append(np.concatenate([np.pad(c, ((4, 4), (4, 4), (0, 0)), constant_values=1) for c in cols], axis=1))
    Image.fromarray((np.concatenate(rows, axis=0) * 255 + 0.5).astype(np.uint8)).save(out)


if __name__ == '__main__':
    main()
