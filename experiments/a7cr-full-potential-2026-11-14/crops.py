"""Native crops of the shipped stack beside prototype arms, one display
transform for every column.

  python -X utf8 crops.py WORK_DIR S0_DIR EVAL_DIR OUT.png ARM[,ARM...] X,Y [X,Y ...] [--size 384] [--zoom 1] [--s0 single]

Columns: S0 (the shipped stack named by --s0), then each arm's full result
(WORK_DIR/fused/ARM-all.npy). X,Y is the crop origin in the prototype's
geometry; the S0 crop is taken at the location evaluate.py fitted (rounded to
whole pixels; S0 is about 1 % magnified by its cover fit and is not
resampled). Prototype channels are scaled to S0 units with evaluate.py's
per-channel gains (the first listed arm's), then every column gets the same
gain (the S0 crop's 99.7th-percentile green to 0.9) and a 1/2.2 power.
--zoom N repeats pixels N times (nearest neighbour), for the eye only.
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


size, zoom, s0name = int(opt('--size', 384)), int(opt('--zoom', 1)), opt('--s0', 'single')
work, s0dir, evd, outp = Path(args[0]), Path(args[1]), Path(args[2]), Path(args[3])
arms = args[4].split(',')
origins = [tuple(int(v) for v in a.split(',')) for a in args[5:]]
ev = json.loads((evd / 'evaluate.json').read_text())
H, W = 6336, 9504
p = ev['s0_single_similarity'] if s0name == 'single' else ev['s0_member1_similarity']
gains = ev['gain_to_s0'][arms[0]] if arms[0] in ev.get('gain_to_s0', {}) else next(iter(ev['gain_to_s0'].values()))
s0 = tifffile.memmap(s0dir / f'{s0name}.tif')
imgs = [np.load(work / 'fused' / f'{a}-all.npy', mmap_mode='r') for a in arms]
rows = []
for x0, y0 in origins:
    cx, cy = (W - 1) / 2, (H - 1) / 2
    ux, uy = x0 + size / 2 - 0.5, y0 + size / 2 - 0.5
    sx = int(round(cx + p[0] * (ux - cx) + 8 * p[1] - size / 2 + 0.5))
    sy = int(round(cy + p[0] * (uy - cy) + 8 * p[2] - size / 2 + 0.5))
    ref = np.asarray(s0[sy:sy + size, sx:sx + size]).astype(np.float32)
    g = 0.9 / max(1.0, float(np.percentile(ref[..., 1], 99.7)))
    cols = [ref]
    for im in imgs:
        t = np.asarray(im[:, y0:y0 + size, x0:x0 + size]).astype(np.float32).transpose(1, 2, 0)
        cols.append(t * np.array(gains, dtype=np.float32))
    tiles = []
    for c in cols:
        v = (np.clip(c * g, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)
        if zoom > 1:
            v = v.repeat(zoom, 0).repeat(zoom, 1)
        tiles.append(np.pad(v, ((3, 3), (3, 3), (0, 0)), constant_values=255))
    rows.append(np.concatenate(tiles, 1))
    print(f'crop origin ({x0}, {y0}) size {size}; S0 {s0name} at ({sx}, {sy}); columns: S0, ' + ', '.join(arms))
Image.fromarray(np.concatenate(rows, 0)).save(outp)
