"""Does the stack keep the fine detail of its own sharpest plane? (brief Q7, Q8)

Signal power per frequency band is the real part of a cross-spectrum between two renders that
share the scene and not the noise:
  - the stack: its odd and even half-stacks (same grid);
  - one plane: two separate four-shot groups taken at the same focus position (revisits),
    registered by a phase ramp.
Noise per band is the mean auto-spectrum minus that. Tiles are where the depth map says this
plane is the sharpest. Everything is measured on the linear masters (luminance), scaled to each
tile's own mean level. The stack's grid is the plane's magnified 1.6 % (coverage scale), which
moves its frequencies by 1.6 %: ignored.

  python stack-vs-plane.py <mask npz> <plane index> <half-stack odd master> <half-stack even master>
        <planes folder> <out txt> [extra master pairs: label=a.tiff,b.tiff ...]
"""
import json
import pathlib
import sys

import numpy as np
import tifffile

mask = np.load(sys.argv[1])
plane = int(sys.argv[2])
odd, even = sys.argv[3], sys.argv[4]
pdir = pathlib.Path(sys.argv[5])
out = pathlib.Path(sys.argv[6])
extra = [a.split('=') for a in sys.argv[7:]]
T = 256
BANDS = [(0.05, 0.10), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.50)]
SCALE = 0.984
fy = np.fft.fftfreq(T)[:, None]
fx = np.fft.rfftfreq(T)[None, :]
FR = np.hypot(fy, fx)
WIN = np.hanning(T)[:, None] * np.hanning(T)[None, :]
lines = []


def say(*a):
    s = ' '.join(str(v) for v in a)
    print(s, flush=True)
    lines.append(s)


def luma(path):
    a = tifffile.imread(path)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def spec(t):
    return np.fft.rfft2((t / max(t.mean(), 1e-9) - 1.0) * WIN)


def pair(a, b):
    """signal and noise power per band from two noisy views of one scene (shift removed)."""
    fa, fb = spec(a), spec(b)
    cross = fa * np.conj(fb)
    corr = np.fft.irfft2(cross / (np.abs(cross) + 1e-3 * np.abs(cross).max()) * np.exp(-(FR / 0.2) ** 2), s=(T, T))
    py, px = np.unravel_index(corr.argmax(), corr.shape)

    def sub(m, c, p):
        d = m - 2 * c + p
        return 0.0 if d == 0 else 0.5 * (m - p) / d
    dy = (py + T // 2) % T - T // 2 + sub(corr[(py - 1) % T, px], corr[py, px], corr[(py + 1) % T, px])
    dx = (px + T // 2) % T - T // 2 + sub(corr[py, (px - 1) % T], corr[py, px], corr[py, (px + 1) % T])
    cross = cross * np.exp(2j * np.pi * (fy * dy + fx * dx))
    auto = 0.5 * (np.abs(fa) ** 2 + np.abs(fb) ** 2)
    sig = np.array([cross.real[(FR >= lo) & (FR < hi)].mean() for lo, hi in BANDS])
    tot = np.array([auto[(FR >= lo) & (FR < hi)].mean() for lo, hi in BANDS])
    return sig, tot - sig, (dx, dy)


# tiles (plane grid) where this plane is the sharpest: the depth map is 1/8 scale of the raw frame,
# whose visible area is 9564 x 6376 against the render's 9504 x 6336 (30, 20 px margins)
depth, focus, m = mask['depth'], mask['focus'], mask['mask']
tiles = []
for by in range(0, depth.shape[0] - 32, 8):
    for bx in range(0, depth.shape[1] - 32, 8):
        d = depth[by:by + 32, bx:bx + 32]
        share = float(((np.abs(d - plane) <= 3) & m[by:by + 32, bx:bx + 32]).mean())
        if share >= 0.35:
            tiles.append((by * 8 - 20, bx * 8 - 30, share))
tiles.sort(key=lambda t: -t[2])
kept = []
for t in tiles:                      # no two tiles overlapping by more than half
    if all(abs(t[0] - k[0]) >= T // 2 or abs(t[1] - k[1]) >= T // 2 for k in kept):
        kept.append(t)
tiles = kept[:40]
say('%d tiles of %d px where plane index %d is the sharpest (within 3 planes) over %.0f-%.0f %% of the tile; elsewhere in a tile the plane is out of focus, which favours the stack' % (
    len(tiles), T, plane, 100 * min(t[2] for t in tiles), 100 * max(t[2] for t in tiles)))

idx = json.loads((pdir / 'index.json').read_text())
revisits = [r for r in idx if r['series'] == 'repeat']
masters = {r['name']: luma(pdir / r['name'] / 'master.tiff') for r in revisits}
names = list(masters)
h, w = next(iter(masters.values())).shape
cy, cx = h / 2, w / 2
L_odd, L_even = luma(odd), luma(even)
others = {label: [luma(p) for p in paths.split(',')] for label, paths in extra}
long_rows = [r for r in idx if r['series'] == 'ladder' and r['seconds'] > 1.0]

res = {'plane': [], 'stack': []}
for k in others:
    res[k] = []
shifts = []
for (y0, x0, _) in tiles:
    if y0 < 0 or x0 < 0 or y0 + T > h or x0 + T > w:
        continue
    acc = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            s, n, sh = pair(masters[names[i]][y0:y0 + T, x0:x0 + T], masters[names[j]][y0:y0 + T, x0:x0 + T])
            acc.append((s, n))
            shifts.append(np.hypot(*sh))
    res['plane'].append((np.mean([a[0] for a in acc], 0), np.mean([a[1] for a in acc], 0)))
    ys = int(round((y0 + T / 2 - cy) / SCALE + cy - T / 2))
    xs = int(round((x0 + T / 2 - cx) / SCALE + cx - T / 2))
    if ys < 0 or xs < 0 or ys + T > h or xs + T > w:
        res['plane'].pop()
        continue
    s, n, _ = pair(L_odd[ys:ys + T, xs:xs + T], L_even[ys:ys + T, xs:xs + T])
    res['stack'].append((s, n))
    for k, (a, b) in others.items():
        s, n, _ = pair(a[ys:ys + T, xs:xs + T], b[ys:ys + T, xs:xs + T])
        res[k].append((s, n))
say('tiles used %d; shift between revisit pairs: median %.2f px, max %.2f px' % (len(res['plane']), np.median(shifts), np.max(shifts)))


def table(label, key, ref='plane'):
    s = np.array([a[0] for a in res[key]])
    n = np.array([a[1] for a in res[key]])
    rs = np.array([a[0] for a in res[ref]])
    rn = np.array([a[1] for a in res[ref]])
    say('\n%s against %s (median over tiles; noise is that of ONE of the two views compared)' % (label, ref))
    say('band (cycles/px) | signal power ratio | amplitude ratio | noise power ratio | signal/noise: %s -> %s' % (ref, label))
    for bi, (lo, hi) in enumerate(BANDS):
        say('%.2f-%.2f        | %.3f (p25 %.3f, p75 %.3f) | %.3f | %.3f | %.2f -> %.2f' % (
            lo, hi, np.median(s[:, bi] / rs[:, bi]), np.percentile(s[:, bi] / rs[:, bi], 25), np.percentile(s[:, bi] / rs[:, bi], 75),
            np.sqrt(max(np.median(s[:, bi] / rs[:, bi]), 0)), np.median(n[:, bi] / rn[:, bi]), np.median(rs[:, bi] / rn[:, bi]), np.median(s[:, bi] / n[:, bi])))


say('\none plane (a four-shot group, same engine, restoration off), signal and noise by band:')
s = np.array([a[0] for a in res['plane']])
n = np.array([a[1] for a in res['plane']])
for bi, (lo, hi) in enumerate(BANDS):
    say('   %.2f-%.2f: signal/noise power %.2f (tiles p25 %.2f, p75 %.2f)' % (lo, hi, np.median(s[:, bi] / n[:, bi]), np.percentile(s[:, bi] / n[:, bi], 25), np.percentile(s[:, bi] / n[:, bi], 75)))
table('half-stack (every second plane)', 'stack')
for k in others:
    table(k, k)
    table(k, k, ref='stack')
out.write_text('\n'.join(lines) + '\n')
