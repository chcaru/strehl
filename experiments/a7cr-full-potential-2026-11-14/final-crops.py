"""Side-by-side crops from render.py's sRGB TIFFs (identical colour and tone
transform in every column).

  python -X utf8 final-crops.py FINAL_DIR EVAL_DIR WORK_DIR OUT.png ARM[,ARM...] X,Y [X,Y ...] [--size 400] [--zoom 1]

Columns: shipped, then each arm. X,Y is the crop origin in the prototype's
full-frame geometry; arm TIFFs are cropped to the common box (offset
subtracted here) and the shipped crop is taken where evaluate.py located it
(whole pixels; the shipped image is about 1 % magnified and not resampled).
--zoom N repeats pixels (nearest neighbour), for the eye only.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

args = sys.argv[1:]


def opt(name, default):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


size, zoom = int(opt('--size', 400)), int(opt('--zoom', 1))
final, evd, work, outp = Path(args[0]), Path(args[1]), Path(args[2]), Path(args[3])
arms = args[4].split(',')
origins = [tuple(int(v) for v in a.split(',')) for a in args[5:]]
ev = json.loads((evd / 'evaluate.json').read_text())
p = ev['s0_single_similarity']
box = json.loads((work / 'fused' / 'f2-box.json').read_text())['box']
H, W = 6336, 9504
shipped = tifffile.imread(final / 'shipped-srgb.tif')
imgs = [tifffile.imread(final / f'{a}-srgb.tif') for a in arms]
rows = []
for x0, y0 in origins:
    cx, cy = (W - 1) / 2, (H - 1) / 2
    ux, uy = x0 + size / 2 - 0.5, y0 + size / 2 - 0.5
    sx = int(round(cx + p[0] * (ux - cx) + 8 * p[1] - size / 2 + 0.5))
    sy = int(round(cy + p[0] * (uy - cy) + 8 * p[2] - size / 2 + 0.5))
    cols = [shipped[sy:sy + size, sx:sx + size]] + [im[y0 - box[2]:y0 - box[2] + size, x0 - box[0]:x0 - box[0] + size] for im in imgs]
    tiles = []
    for c in cols:
        v = (c >> 8).astype(np.uint8)
        if zoom > 1:
            v = v.repeat(zoom, 0).repeat(zoom, 1)
        tiles.append(np.pad(v, ((3, 3), (3, 3), (0, 0)), constant_values=255))
    rows.append(np.concatenate(tiles, 1))
    print(f'crop origin ({x0}, {y0}) size {size} zoom {zoom}; shipped at ({sx}, {sy}); columns: shipped, ' + ', '.join(arms))
Image.fromarray(np.concatenate(rows, 0)).save(outp)
