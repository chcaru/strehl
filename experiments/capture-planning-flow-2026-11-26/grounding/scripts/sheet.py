"""Native crops of chosen tiles at chosen planes of an extracted stack (green plane, 1 px = 2 sensor px).

  python sheet.py <stack scratch folder> <out png> <tiles "y,x;y,x"> <plane indices in focus order "a,b,c">
"""
import json, pathlib, sys
import numpy as np
from PIL import Image, ImageDraw
folder, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
tiles = [tuple(int(v) for v in t.split(',')) for t in sys.argv[3].split(';')]
g = np.load(folder / 'general.npz')
pos, order = g['pos'], g['order']
planes = [int(v) for v in sys.argv[4].split(',')]
files = sorted((folder / 'planes').glob('base-*.npz'))
CROP, pad, head = 160, 4, 30
img = Image.new('RGB', (len(planes) * (CROP + pad) + pad, len(tiles) * (CROP + head + pad) + pad), (20, 20, 20))
d = ImageDraw.Draw(img)
cache = {}
for i, (ty, tx) in enumerate(tiles):
    crops = []
    for p in planes:
        if p not in cache:
            cache[p] = np.load(files[order[p]])['g']
        a = cache[p]
        y0 = int(np.clip(ty * 32 + 16 - CROP // 2, 0, a.shape[0] - CROP)); x0 = int(np.clip(tx * 32 + 16 - CROP // 2, 0, a.shape[1] - CROP))
        crops.append(a[y0:y0 + CROP, x0:x0 + CROP].astype(np.float32) - 512.0)
    hi = max(max(np.percentile(c, 99.5) for c in crops), 64.0)
    y = pad + i * (CROP + head + pad)
    f = g['focus'][ty, tx]
    d.text((pad, y), 'tile (%d,%d) sensor px (%d,%d) narrow-peak focus %s white %d DN' % (ty, tx, tx * 64 + 32, ty * 64 + 32, 'none' if not np.isfinite(f) else '%.0f' % f, hi), fill=(230, 230, 230))
    for j, (p, c) in enumerate(zip(planes, crops)):
        x = pad + j * (CROP + pad)
        img.paste(Image.fromarray((np.clip(c / hi, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)), (x, y + head))
        d.text((x + 3, y + 15), 'plane %d · %d' % (p + 1, pos[p]), fill=(150, 200, 255))
img.save(out); print(out, img.size)
