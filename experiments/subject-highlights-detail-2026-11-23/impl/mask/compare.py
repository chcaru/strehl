"""Compare a product subject mask (strehl subject --mask-png/--dump-evidence) with a
prototype mask (subject-mask.py .npz) at the product's cell grid.

The product grid covers the decoder's active area (9504 x 6336 on the A7CR); the
prototype's covers rawpy's visible area (9564 x 6376). The offset between the two
origins is found by correlating the two level maps over even sensor-pixel shifts,
then the prototype mask is sampled (nearest cell) at the product cells' centres.

  python compare.py <product prefix> <prototype npz> [--offset ox,oy]
"""
import json
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

prefix, proto = sys.argv[1], sys.argv[2]
meta = json.load(open(prefix + '.json'))
cols, rows = meta['grid']
mask = np.asarray(Image.open(prefix + '.png')) > 127
assert mask.shape == (rows, cols), mask.shape
p = np.load(proto)
pm = p['mask']
plevel = p['level'].astype(np.float32)
ph, pw = pm.shape


def sample(img, ox, oy, order):
    yy, xx = np.mgrid[0:rows, 0:cols].astype(np.float64)
    # product cell centre in active px -> visible px -> prototype cell coords
    py = (8 * yy + 4 + oy) / 8 - 0.5
    px = (8 * xx + 4 + ox) / 8 - 0.5
    return ndimage.map_coordinates(img.astype(np.float32), [py, px], order=order, mode='nearest')


off = None
if '--offset' in sys.argv:
    off = tuple(int(v) for v in sys.argv[sys.argv.index('--offset') + 1].split(','))
else:
    raw = np.fromfile(prefix + '.bin', dtype='<f4', count=2 * rows * cols)
    level = raw[rows * cols:].reshape(rows, cols)
    a = ndimage.gaussian_filter(level, 1.0)[20:-20, 20:-20].ravel()
    best = None
    for oy in range(0, 2 * (ph * 8 - rows * 8) // 2 + 1, 2):
        for ox in range(0, 2 * (pw * 8 - cols * 8) // 2 + 1, 2):
            b = ndimage.gaussian_filter(sample(plevel, ox, oy, 1), 1.0)[20:-20, 20:-20].ravel()
            c = np.corrcoef(a, b)[0, 1]
            if best is None or c > best[0]:
                best = (c, ox, oy)
    print('level-map offset (active origin in visible px): x %d, y %d (correlation %.5f)' % (best[1], best[2], best[0]))
    off = best[1:]
ref = sample(pm, off[0], off[1], 0) > 0.5
inter = (mask & ref).sum()
union = (mask | ref).sum()
edge = mask & ~ndimage.binary_erosion(mask)
dist = ndimage.distance_transform_edt(~(ref & ~ndimage.binary_erosion(ref)))
print('product %.4f of the grid, prototype %.4f; IoU %.4f; product outline from the prototype outline: median %.1f, p95 %.1f cells' % (
    mask.mean(), ref.mean(), inter / max(union, 1), np.median(dist[edge]) if edge.any() else float('nan'),
    np.percentile(dist[edge], 95) if edge.any() else float('nan')))
print('only product %.4f, only prototype %.4f of the grid' % ((mask & ~ref).mean(), (ref & ~mask).mean()))
