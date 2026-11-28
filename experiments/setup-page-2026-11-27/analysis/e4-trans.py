"""Transients of e4-return.py: the lens position read from each live frame (the same
fingerprint as e4-an.py) and the picture's shift against the transient's last frames,
against time since the move was commanded. Also the two frames of each far approach.

  python e4-trans.py <folder>
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


def register(ref, mov):
    r = ndimage.gaussian_filter(ref, 1.0)
    m0 = ndimage.gaussian_filter(mov, 1.0)
    d = np.zeros(2)
    core = (slice(16, -16), slice(16, -16))
    for _ in range(6):
        m = ndimage.shift(m0, (-d[1], -d[0]), order=3, mode='nearest') if d.any() else m0
        gy, gx = np.gradient(m)
        A = np.stack([gx[core].ravel(), gy[core].ravel(), m[core].ravel(), np.ones(m[core].size, np.float32)], 1)
        sol, *_ = np.linalg.lstsq(A, r[core].ravel(), rcond=None)
        step = np.array([sol[0], sol[1]]) / max(sol[2], 1e-6)
        d += step
        if np.abs(step).max() < 0.002:
            break
    return d


print('far approaches, first and second live frame (read position minus P):')
for kind in ['farbelow', 'farabove', 'farbelow+128', 'farabove+128', 'below128', 'above128']:
    rows = []
    for rep in range(6):
        a = folder / ('t-%s-%d-0.jpg' % (kind, rep))
        b = folder / ('t-%s-%d-1.jpg' % (kind, rep))
        if a.exists() and b.exists():
            rows.append('%+.1f/%+.1f' % (locate(contrast(luma(a))) - P, locate(contrast(luma(b))) - P))
    print('  %-14s %s' % (kind, '  '.join(rows)))

SENSOR_PER_LIVE = 9504 / 1024
print('transients (t s after the command: read position minus P, picture shift in sensor px against the last 5 frames):')
summary = {}
for e in meta['log']:
    if e['what'] != 'transient':
        continue
    frames = e['frames']
    lum = [luma(folder / f['name']) for f in frames]
    ref = np.mean(lum[-5:], 0)
    rows = []
    for f, l in zip(frames, lum):
        d = register(ref, l) * SENSOR_PER_LIVE
        rows.append((f['t'], locate(contrast(l)) - P, float(d[0]), float(d[1])))
    summary.setdefault(e['kind'], []).append(rows)
    if e['rep'] < 2:
        print('  %s rep %d, command posted in %.2f s, %d frames:' % (e['kind'], e['rep'], e['posted_after'], len(frames)))
        print('     ' + '  '.join('%.2f:%+.1f(%+.1f,%+.1f)' % r for r in rows[:14]))
        print('     ' + '  '.join('%.2f:%+.1f(%+.1f,%+.1f)' % r for r in rows[-4:]))
print('by kind, mean over repeats in time bins (s): position minus final, |shift| px')
for kind, reps in summary.items():
    line = []
    for lo, hi in [(0, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 4.6)]:
        pos, sh = [], []
        for rows in reps:
            final = np.mean([r[1] for r in rows[-5:]])
            for t, p, dx, dy in rows:
                if lo <= t < hi:
                    pos.append(p - final)
                    sh.append(np.hypot(dx, dy))
        if pos:
            line.append('%.2f-%.2f: %+.1f u, %.1f px (n %d)' % (lo, hi, np.mean(pos), np.mean(sh), len(pos)))
    print('  %-5s %s' % (kind, ' | '.join(line)))
    print('        first frame arrives %.2f s after the command (mean); %.1f frames/s' % (
        np.mean([rows[0][0] for rows in reps]), np.mean([(len(rows) - 1) / (rows[-1][0] - rows[0][0]) for rows in reps])))
