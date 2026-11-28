"""Level and picture position of every frame of a fixed-focus single-shot burst.

  python series-an.py <run folder> <out.json> [workers] [crop x0 y0 side]

Level: mean above black of each colour over photosites that are mid-tone (5 % to 50 % of the
range) in the first frame. Position: a 2x2-binned luminance crop registered against the first
frame's (Lucas-Kanade with a gain and an offset, to 0.01 px of a binned pixel; reported in
sensor pixels).
"""
import concurrent.futures as cf
import json
import pathlib
import subprocess
import sys

import numpy as np
import rawpy
from scipy import ndimage

TOOL = r'C:\dev\blog\death-of-software\projects\strehl\target\release\strehl-raw-archive.exe'
SCRATCH = pathlib.Path(r'C:\strehl-scratch\calib-page\tmp-raw')
run = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
crop = [int(v) for v in sys.argv[4:7]] if len(sys.argv) > 6 else None


def read(name):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    work = SCRATCH / ('%s-%s' % (run.name, name))
    work.mkdir(exist_ok=True)
    raw_name = name[:-len('.straw')]
    subprocess.run([TOOL, 'restore', str(run / name), '--output-dir', str(work)], check=True, capture_output=True)
    with rawpy.imread(str(work / raw_name)) as raw:
        img = raw.raw_image_visible.copy()
        black = float(np.mean(raw.black_level_per_channel))
    (work / raw_name).unlink()
    work.rmdir()
    return img, black


def luma(img, black, x0, y0, side):
    a = img[y0:y0 + 2 * side, x0:x0 + 2 * side].astype(np.float32) - black
    return a[0::2, 0::2] + a[0::2, 1::2] + a[1::2, 0::2] + a[1::2, 1::2]


def register(ref, mov):
    """(dx, dy) in binned pixels such that mov(x + d) matches ref."""
    r = ndimage.gaussian_filter(ref, 1.0)
    m0 = ndimage.gaussian_filter(mov, 1.0)
    d = np.zeros(2)
    core = (slice(16, -16), slice(16, -16))
    for _ in range(8):
        m = ndimage.shift(m0, (-d[1], -d[0]), order=3, mode='nearest') if d.any() else m0
        gy, gx = np.gradient(m)
        A = np.stack([gx[core].ravel(), gy[core].ravel(), m[core].ravel(), np.ones(m[core].size, np.float32)], 1)
        b = r[core].ravel()
        # r = g (m + gx dx + gy dy) + o, linearised about g = 1
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        g = sol[2]
        step = np.array([sol[0], sol[1]]) / max(g, 1e-6)
        d += step
        if np.abs(step).max() < 0.002:
            break
    return float(d[0]), float(d[1])


def times():
    t = {}
    for line in open(run / 'events.jsonl', encoding='utf-8'):
        e = json.loads(line)
        if e['event'] in ('capture_complete', 'capture_buffered'):
            for f in e['data']['response'].get('files', []):
                t[f['name']] = e['unix_ms'] / 1000
    return t


names = sorted(p.name for p in run.glob('*.ARW.straw'))
img0, black0 = read(names[0])
H, W = img0.shape
side = 768
if crop:
    x0, y0, side = crop
else:
    x0, y0 = (W // 2 - side) & ~1, (H // 2 - side) & ~1
ref = luma(img0, black0, x0, y0, side)
rng = 16383.0 - black0
masks = []
for (py, px) in [(0, 0), (0, 1), (1, 0), (1, 1)]:
    p = img0[py::2, px::2].astype(np.float32) - black0
    masks.append((p > 0.05 * rng) & (p < 0.5 * rng))


def one(name):
    img, black = read(name)
    level = [float((img[py::2, px::2][m].astype(np.float64) - black).mean())
             for (py, px), m in zip([(0, 0), (0, 1), (1, 0), (1, 1)], masks)]
    dx, dy = register(ref, luma(img, black, x0, y0, side))
    return {'name': name, 'level': level, 'dx': 2 * dx, 'dy': 2 * dy}


t = times()
with cf.ThreadPoolExecutor(workers) as ex:
    rows = list(ex.map(one, names))
for r in rows:
    r['unix'] = t.get(r['name'][:-len('.straw')])
out.write_text(json.dumps({'run': str(run), 'crop': [x0, y0, side], 'mask_counts': [int(m.sum()) for m in masks], 'rows': rows}, indent=1))
print('wrote', out, len(rows), 'frames; mask', [int(m.sum()) for m in masks])
