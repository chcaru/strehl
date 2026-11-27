"""Native crops through focus at chosen tiles, one row a tile, one column a plane, one display
transform for a row (so brightness can be compared along it). Crops are the green site plane:
1 px = 2 sensor px, shown unresampled.

  python witness.py <planes folder> <truth folder> <out png> [--tiles y,x;y,x...] [--planes a,b,c]

Without --tiles: the earliest and latest resolved tiles, a typical one, a tile rising to the last
plane, a tile rising to the first plane, and a flat one (64 px tiles of truth.py).
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw

src, truth, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
args = sys.argv[4:]
z = np.load(truth / 'tiles-64.npz')
kind, foc, inside, peak = z['kind'], z['focus'], z['inside'], z['peak']
index = json.loads((src / 'index.json').read_text())
base = sorted([r for r in index if r['tier'] == 'base'], key=lambda r: r['plane'])
focus = np.array([r['focus'] for r in base])
CROP = 160                     # green-plane px: 320 sensor px
picks = []
if '--tiles' in args:
    for item in args[args.index('--tiles') + 1].split(';'):
        y, x = (int(v) for v in item.split(','))
        picks.append(('tile %d,%d' % (y, x), y, x))
else:
    res = (kind == 1) & inside
    ys, xs = np.nonzero(res)
    order = np.argsort(foc[res])
    for label, i in (('earliest resolved', order[0]), ('early (0.5 %)', order[len(order) // 200]),
                     ('median', order[len(order) // 2]), ('late (99.5 %)', order[-len(order) // 200]),
                     ('latest resolved', order[-1])):
        picks.append((label, ys[i], xs[i]))
    for label, code in (('rising to the last plane', 3), ('rising to the first plane', 2), ('flat', 0)):
        sel = np.nonzero((kind == code) & inside)
        if len(sel[0]):
            j = np.argmax(peak[sel]) if code != 0 else len(sel[0]) // 2
            picks.append((label, sel[0][j], sel[1][j]))
if '--planes' in args:
    cols = [int(v) for v in args[args.index('--planes') + 1].split(',')]
else:
    cols = None
rows = []
for label, ty, tx in picks:
    cy, cx = ty * 32 + 16, tx * 32 + 16          # tile centre, green-plane px
    f = foc[ty, tx]
    if cols is None:
        best = int(np.argmin(np.abs(focus - f))) if np.isfinite(f) else len(focus) // 2
        planes = [0, 20, 42, max(best - 6, 0), best, min(best + 6, len(focus) - 1), 125, 150]
    else:
        planes = cols
    crops = []
    for p in planes:
        zf = np.load(src / ('base-%04d.npz' % p))
        g = zf['g']
        y0 = int(np.clip(cy - CROP // 2, 0, g.shape[0] - CROP)); x0 = int(np.clip(cx - CROP // 2, 0, g.shape[1] - CROP))
        crops.append(g[y0:y0 + CROP, x0:x0 + CROP].astype(np.float32) - 512.0)
    hi = max(np.percentile(c, 99.5) for c in crops)
    hi = max(hi, 64.0)
    rows.append((label, ty, tx, f, planes, [np.clip(c / hi, 0, 1) ** (1 / 2.2) for c in crops], hi))
pad, head = 4, 30
W = max(len(r[4]) for r in rows) * (CROP + pad) + pad
H = len(rows) * (CROP + head + pad) + pad
img = Image.new('RGB', (W, H), (20, 20, 20))
d = ImageDraw.Draw(img)
for i, (label, ty, tx, f, planes, crops, hi) in enumerate(rows):
    y = pad + i * (CROP + head + pad)
    d.text((pad, y), '%s  tile (%d,%d)  centre sensor px (%d,%d)  focus %s  white at %d DN' % (label, ty, tx, tx * 64 + 32, ty * 64 + 32, 'none' if not np.isfinite(f) else '%.0f' % f, hi), fill=(230, 230, 230))
    for j, (p, c) in enumerate(zip(planes, crops)):
        x = pad + j * (CROP + pad)
        img.paste(Image.fromarray((c * 255).astype(np.uint8)), (x, y + head))
        d.text((x + 3, y + 15), 'plane %d · %d' % (p + 1, focus[p]), fill=(150, 200, 255))
img.save(out)
print(out, img.size)
for r in rows:
    print(r[0], 'tile', r[1], r[2], 'focus', r[3], 'planes', r[4])
