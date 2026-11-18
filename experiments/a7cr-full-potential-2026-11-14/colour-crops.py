"""Native crops of shipped renders side by side, one display transform.

  python -X utf8 colour-crops.py OUT.png SIZE ZOOM A.tif,B.tif,... X,Y [X,Y ...]

Same geometry in every column (renders of one run by one binary differ only
in colour handling). Display: one gain from the first column's 99.7th
percentile green in that crop, then a 1/2.2 power; ZOOM repeats pixels
(nearest neighbour) for the eye only. Columns in argument order.
"""
import sys
import numpy as np
import tifffile
from PIL import Image

out, size, zoom = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
imgs = [tifffile.memmap(f) for f in sys.argv[4].split(',')]
rows = []
for o in sys.argv[5:]:
    x0, y0 = (int(v) for v in o.split(','))
    crops = [np.asarray(im[y0:y0 + size, x0:x0 + size]).astype(np.float32) for im in imgs]
    g = 0.9 / max(1.0, float(np.percentile(crops[0][..., 1], 99.7)))
    tiles = []
    for c in crops:
        v = (np.clip(c * g, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)
        tiles.append(np.pad(v.repeat(zoom, 0).repeat(zoom, 1), ((3, 3), (3, 3), (0, 0)), constant_values=255))
    rows.append(np.concatenate(tiles, 1))
    print(f'crop origin ({x0}, {y0}) size {size} zoom {zoom}')
Image.fromarray(np.concatenate(rows, 0)).save(out)
