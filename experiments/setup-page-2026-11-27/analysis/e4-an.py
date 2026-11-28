"""Analyse e4-return.py's recording.

Fingerprint: per 32 px tile of the magnified live frame, contrast against lens position from
sweep 1 (fine detail energy over brightness squared). A frame's position is the one whose
interpolated fingerprint it matches best (weighted least squares over tiles). The instrument's
own precision is read from sweep 1's second frame of each position and from leaving one
position out; the drift during the test from sweep 2.

  python e4-an.py <folder>
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
    im = Image.open(io.BytesIO(path.read_bytes())).convert('L')
    return np.asarray(im, np.float32)


def contrast(l):
    h, w = l.shape
    hp = l - ndimage.gaussian_filter(l, 1.5)
    e = hp * hp
    ny, nx = h // T, w // T
    e = e[:ny * T, :nx * T].reshape(ny, T, nx, T).mean((1, 3))
    m = l[:ny * T, :nx * T].reshape(ny, T, nx, T).mean((1, 3))
    return (e / (m * m + 16.0 ** 2)).ravel()


def load(prefix):
    out = {}
    for p in sorted(folder.glob(prefix + '-*.jpg')):
        stem = p.stem
        key, k = stem.rsplit('-', 1)
        out.setdefault(key, []).append(contrast(luma(p)))
    return out


s1 = load('s1')
s2 = load('s2')
positions = sorted(int(k.split('-')[1]) for k in s1)
first = luma(sorted(folder.glob('s1-*.jpg'))[0])
print('live frame', first.shape, 'tiles', (first.shape[0] // T) * (first.shape[1] // T), 'positions', positions[0], positions[-1], len(positions))
F = np.array([np.mean(s1['s1-%05d' % p], 0) for p in positions])          # positions x tiles
# Per-tile noise from the two frames of each position.
pairs = np.array([s1['s1-%05d' % p][0] - s1['s1-%05d' % p][1] for p in positions if len(s1['s1-%05d' % p]) > 1])
noise = np.sqrt((pairs ** 2).mean(0) / 2) + 1e-9
swing = F.max(0) - F.min(0)
good = swing > 6 * noise
print('tiles with a swing over 6 x noise:', int(good.sum()), 'of', good.size)
w = np.where(good, 1.0 / (noise ** 2 + (0.03 * F.mean(0)) ** 2), 0.0)
grid = np.arange(positions[0], positions[-1] + 0.01, 0.25)


def curves(Fm, pos):
    return np.array([np.interp(grid, pos, Fm[:, i]) for i in range(Fm.shape[1])]).T   # grid x tiles


C = curves(F, positions)


def locate(c, Cm=C):
    # A gain per frame: live view's brightness changes from frame to frame.
    g = (Cm * c[None, :] * w[None, :]).sum(1) / ((Cm * Cm) * w[None, :]).sum(1)
    r = ((g[:, None] * Cm - c[None, :]) ** 2 * w[None, :]).sum(1)
    i = int(r.argmin())
    if 0 < i < len(grid) - 1:
        a, b, cc = r[i - 1], r[i], r[i + 1]
        d = 0.5 * (a - cc) / (a - 2 * b + cc) if (a - 2 * b + cc) != 0 else 0.0
    else:
        d = 0.0
    return grid[i] + 0.25 * d


# Instrument precision 1: each single frame of sweep 1 against the mean fingerprint.
err = []
for p in positions:
    for c in s1['s1-%05d' % p]:
        err.append(locate(c) - p)
err = np.array(err)
print('sweep 1 single frames against their own fingerprint: bias %+.2f, rms %.2f units' % (err.mean(), err.std()))
# Precision 2: leave one position out.
loo = []
for j, p in enumerate(positions[1:-1], 1):
    keep = [i for i in range(len(positions)) if i != j]
    Cm = curves(F[keep], [positions[i] for i in keep])
    for c in s1['s1-%05d' % p]:
        loo.append(locate(c, Cm) - p)
loo = np.array(loo)
print('leave one position out: bias %+.2f, rms %.2f, worst %.2f units' % (loo.mean(), loo.std(), np.abs(loo).max()))
# Drift: sweep 2 against sweep 1's fingerprint.
d2 = np.array([locate(c) - int(k.split('-')[1]) for k, v in sorted(s2.items()) for c in v])
inner = np.array([abs(int(k.split('-')[1]) - P) <= 48 for k, v in sorted(s2.items()) for c in v])
print('sweep 2 read against sweep 1: mean %+.2f, rms about it %.2f units (inner positions: %+.2f)' % (
    d2.mean(), d2.std(), d2[inner].mean()))

t = load('t')
kinds = {}
for key, frames in t.items():
    _, kind, rep = key.split('-', 2) if key.count('-') == 2 else (None, None, None)
    if kind is None:
        parts = key.split('-')
        kind, rep = '-'.join(parts[1:-1]), parts[-1]
    for c in frames:
        kinds.setdefault(kind, []).append((int(rep), locate(c) - P))
times = {(e['kind'], e['rep']): e['unix'] for e in meta['log'] if e['what'] == 'approach'}
span = meta['ended'] - meta['began']
print('approaches to P = %d (read position minus P, units; two frames each):' % P)
out = {}
for kind in sorted(kinds):
    v = np.array([x[1] for x in kinds[kind]])
    per_rep = {}
    for rep, x in kinds[kind]:
        per_rep.setdefault(rep, []).append(x)
    reps = np.array([np.mean(per_rep[r]) for r in sorted(per_rep)])
    out[kind] = {'mean': float(reps.mean()), 'sd': float(reps.std(ddof=1)) if len(reps) > 1 else None,
                 'reps': [float(x) for x in reps]}
    print('  %-14s mean %+6.2f  sd %5.2f  reps %s' % (kind, reps.mean(), reps.std(ddof=1) if len(reps) > 1 else 0,
                                                        ' '.join('%+.1f' % x for x in reps)))
(folder / 'approach.json').write_text(json.dumps({'P': P, 'instrument': {'single_rms': float(err.std()), 'loo_rms': float(loo.std()),
                                                  'sweep2_mean': float(d2.mean())}, 'kinds': out}, indent=1))
