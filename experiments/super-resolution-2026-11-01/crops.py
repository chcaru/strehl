"""Side-by-side native crops of saved arm images with one display transform.

Usage: crops.py <imgs.npy> <out.png> [labels...]
Each array is (arms, 3, h, w) linear WB'd camera RGB. Display: shared black/white
from the first arm's 0.5/99.7 percentiles, gamma 1/2.2, nearest-neighbour x3.
"""
import sys

import numpy as np
from PIL import Image, ImageDraw

a = np.load(sys.argv[1])
labels = sys.argv[3:] or [f"arm{i}" for i in range(len(a))]
b = 8
a = a[:, :, b:-b, b:-b]
lo = np.percentile(a[0], 0.5)
hi = np.percentile(a[0], 99.7)
tiles = []
for img in a:
    x = np.clip((img - lo) / (hi - lo), 0, 1) ** (1 / 2.2)
    x = (x.transpose(1, 2, 0) * 255).astype(np.uint8)
    x = np.kron(x, np.ones((3, 3, 1), np.uint8))
    tiles.append(x)
h, w, _ = tiles[0].shape
out = Image.new("RGB", (w * len(tiles) + 8 * (len(tiles) - 1), h + 20), (40, 40, 40))
d = ImageDraw.Draw(out)
for i, t in enumerate(tiles):
    out.paste(Image.fromarray(t), (i * (w + 8), 20))
    d.text((i * (w + 8) + 4, 4), labels[i] if i < len(labels) else "", fill=(255, 255, 255))
out.save(sys.argv[2])
print(sys.argv[2], out.size, "black", lo, "white", hi)
