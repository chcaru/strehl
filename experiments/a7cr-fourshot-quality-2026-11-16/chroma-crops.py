"""Q1/Q8: native crops with the colour difference from green exaggerated, to
see whether fine colour structure repeats between independent half-stacks.

  python -X utf8 chroma-crops.py OUT.png SIZE ZOOM BOOST A.tif,B.tif,... X,Y [X,Y ...]

Per crop and column: linear camera RGB; a neutral balance from the crop's own
channel means (first column's, applied to all); chroma = value minus the
pixel's mean of R, G, B, multiplied by BOOST (1 = as is); one gain from the
first column's 99.7th percentile; 1/2.2 power; ZOOM repeats pixels (nearest
neighbour, for the eye only). Columns in argument order. A colour speckle
that sits at the same place in an odd-frame and an even-frame half-stack is
not random noise.
"""
import sys

import numpy as np
import tifffile
from PIL import Image

out, size, zoom, boost = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
imgs = [tifffile.memmap(f) for f in sys.argv[5].split(',')]
rows = []
for o in sys.argv[6:]:
    x0, y0 = (int(v) for v in o.split(','))
    crops = [np.asarray(im[y0:y0 + size, x0:x0 + size]).astype(np.float32) for im in imgs]
    bal = crops[0].reshape(-1, 3).mean(0)
    bal = bal.mean() / bal
    g = 0.9 / max(1.0, float(np.percentile((crops[0] * bal).mean(-1), 99.7)))
    tiles = []
    for c in crops:
        c = c * bal
        luma = c.mean(-1, keepdims=True)
        v = luma + boost * (c - luma)
        v = (np.clip(v * g, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)
        tiles.append(np.pad(v.repeat(zoom, 0).repeat(zoom, 1), ((3, 3), (3, 3), (0, 0)), constant_values=255))
    rows.append(np.concatenate(tiles, 1))
    print(f'crop origin ({x0}, {y0}) size {size} zoom {zoom} chroma x{boost}')
Image.fromarray(np.concatenate(rows, 0)).save(out)
