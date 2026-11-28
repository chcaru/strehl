"""Creep after a long move: the lens position read from each live frame for 12 s after a
5000-unit move from each side (the fingerprint of e4-an.py, with a gain per frame).

  python e6-an.py <folder>
"""
import io
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

folder = pathlib.Path(sys.argv[1])
meta = json.loads((folder / 'log.json').read_text())
P = meta['P']
T = 32


def luma(path):
    return np.asarray(Image.open(io.BytesIO(path.read_bytes())).convert('L'), np.float32)


def contrast(l):
    h, w = l.shape
    hp = l - ndimage.gaussian_filter(l, 1.5)
    e = hp * hp
    ny, nx = h // T, w // T
    e = e[:ny * T, :nx * T].reshape(ny, T, nx, T).mean((1, 3))
    m = l[:ny * T, :nx * T].reshape(ny, T, nx, T).mean((1, 3))
    return (e / (m * m + 16.0 ** 2)).ravel()


positions = list(range(P - 64, P + 65, 4))
S = {p: [contrast(luma(folder / ('s1-%05d-%d.jpg' % (p, k)))) for k in (0, 1)] for p in positions}
F = np.array([np.mean(S[p], 0) for p in positions])
pairs = np.array([S[p][0] - S[p][1] for p in positions])
noise = np.sqrt((pairs ** 2).mean(0) / 2) + 1e-9
good = (F.max(0) - F.min(0)) > 6 * noise
w = np.where(good, 1.0 / (noise ** 2 + (0.03 * F.mean(0)) ** 2), 0.0)
grid = np.arange(positions[0], positions[-1] + 0.01, 0.25)
C = np.array([np.interp(grid, positions, F[:, i]) for i in range(F.shape[1])]).T


def locate(c):
    g = (C * c[None, :] * w[None, :]).sum(1) / ((C * C) * w[None, :]).sum(1)
    r = ((g[:, None] * C - c[None, :]) ** 2 * w[None, :]).sum(1)
    i = int(r.argmin())
    d = 0.0
    if 0 < i < len(grid) - 1:
        a, b, cc = r[i - 1], r[i], r[i + 1]
        if a - 2 * b + cc != 0:
            d = 0.5 * (a - cc) / (a - 2 * b + cc)
    return grid[i] + 0.25 * d


print('tiles used', int(good.sum()))
bins = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 6), (6, 8), (8, 10), (10, 12.5)]
out = {}
for e in meta['log']:
    rows = [(f['t'], locate(contrast(luma(folder / f['name']))) - P) for f in e['frames']]
    out.setdefault(e['kind'], []).append(rows)
    line = []
    for lo, hi in bins:
        v = [p for t, p in rows if lo <= t < hi]
        if v:
            line.append('%g-%g s: %+.1f' % (lo, hi, float(np.median(v))))
    print('%-9s rep %d (%d frames, first at %.2f s): %s' % (e['kind'], e['rep'], len(rows), rows[0][0], '  '.join(line)))
for kind, reps in out.items():
    line = []
    for lo, hi in bins:
        v = [p for rows in reps for t, p in rows if lo <= t < hi]
        if v:
            line.append('%g-%g s: %+.1f (sd %.1f)' % (lo, hi, float(np.mean(v)), float(np.std(v))))
    print('%-9s all: %s' % (kind, '  '.join(line)))
(folder / 'creep.json').write_text(json.dumps({k: v for k, v in out.items()}, indent=0))
