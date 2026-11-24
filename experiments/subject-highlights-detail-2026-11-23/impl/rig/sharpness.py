"""Sharpness of live-view frames by focus position: the variance of the
Laplacian of luma over the central half and over the whole frame, and the
share of 32 px blocks whose Laplacian energy is near their own maximum over
the sweep (where something is in focus).

  python sharpness.py <folder of live-NNNNN.jpg>
"""
import pathlib
import sys

import numpy as np
from PIL import Image

folder = pathlib.Path(sys.argv[1])
frames = sorted(folder.glob('live-*.jpg'))
rows = []
blocks = []
for f in frames:
    pos = int(f.stem.split('-')[1])
    a = np.asarray(Image.open(f).convert('L'), dtype=np.float32)
    lap = 4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    h, w = lap.shape
    centre = lap[h // 4:3 * h // 4, w // 4:3 * w // 4]
    b = 32
    e = (lap[:h // b * b, :w // b * b] ** 2).reshape(h // b, b, w // b, b).mean(axis=(1, 3))
    blocks.append(e)
    rows.append((pos, float(centre.var()), float(lap.var()), float(a.mean())))
blocks = np.array(blocks)
peak = blocks.max(axis=0)
sharpest = blocks.argmax(axis=0)
busy = peak > np.percentile(peak, 50)
print('position  centre_var  frame_var  mean  blocks_sharpest_here')
for i, (pos, c, v, m) in enumerate(rows):
    print('%6d %10.1f %10.1f %6.1f %5d' % (pos, c, v, m, int(((sharpest == i) & busy).sum())))
