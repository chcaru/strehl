"""Fine focus sweep and revisits (brief Q6, Q7).

Sweep: four-shot groups 2 focus units apart around one plane. For the sharpest 512 px tiles,
signal power per frequency band against focus (noise taken from the two green samples of each
site, which see the same light), the width of each band's focus curve, and what a plane lying
half a capture step (3.5 units) from a tile's best focus keeps.

Revisits: groups taken at one position after separate approaches. Shift between them (phase
correlation with a parabolic peak) and the focus difference implied by their fine-band power.

  python sweep.py <index.json> <out folder>
"""
import json
import pathlib
import sys

import numpy as np

import rigdata

rows = json.loads(pathlib.Path(sys.argv[1]).read_text())
out = pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
BANDS = [(0.05, 0.10), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.50)]
T = 512
lines = []


def say(*a):
    s = ' '.join(str(v) for v in a)
    print(s, flush=True)
    lines.append(s)


def greens(folder):
    """Mean of the two green samples per site, and half their difference (noise and member motion only)."""
    ms = rigdata.members(folder)
    img0 = ms[0][0]
    h, w = img0.shape
    yy, xx = np.mgrid[2:h - 2, 2:w - 2]
    vals = []
    for (img, b, wl, cfa), (dx, dy) in zip(ms, rigdata.OFFSETS):
        sy, sx = yy + dy, xx + dx
        vals.append(np.where(cfa[sy % 2, sx % 2] == 'G', img[sy, sx].astype(np.float32) - b, np.nan))
    st = np.stack(vals)
    order = np.argsort(np.isnan(st), axis=0)[:2]         # the two members that are green at each site
    a = np.take_along_axis(st, order[:1], 0)[0]
    b_ = np.take_along_axis(st, order[1:2], 0)[0]
    return 0.5 * (a + b_), 0.5 * (a - b_)


fy = np.fft.fftfreq(T)[:, None]
fx = np.fft.rfftfreq(T)[None, :]
FR = np.hypot(fy, fx)
WIN = np.hanning(T)[:, None] * np.hanning(T)[None, :]


def band_power(tile):
    f = np.abs(np.fft.rfft2((tile - tile.mean()) * WIN)) ** 2
    return np.array([f[(FR >= lo) & (FR < hi)].mean() for lo, hi in BANDS])


def shift(a, b):
    fa, fb = np.fft.rfft2((a - a.mean()) * WIN), np.fft.rfft2((b - b.mean()) * WIN)
    cross = fa * np.conj(fb)
    lowpass = np.exp(-(FR / 0.25) ** 2)
    corr = np.fft.irfft2(cross / (np.abs(cross) + 1e-3 * np.abs(cross).max()) * lowpass, s=a.shape)
    py, px = np.unravel_index(corr.argmax(), corr.shape)

    def sub(c_m, c_0, c_p):
        d = c_m - 2 * c_0 + c_p
        return 0.0 if d == 0 else 0.5 * (c_m - c_p) / d
    dy = sub(corr[(py - 1) % T, px], corr[py, px], corr[(py + 1) % T, px])
    dx = sub(corr[py, (px - 1) % T], corr[py, px], corr[py, (px + 1) % T])
    return ((px + T // 2) % T - T // 2 + dx, (py + T // 2) % T - T // 2 + dy)


sweep = sorted([r for r in rows if r.get('series') == 'sweep'], key=lambda r: (r['position'], r['started']))
centre = [r for r in sweep if r.get('note') == 'centre again'][0]['position']
ref_row = [r for r in sweep if r['position'] == centre and not r.get('note')][0]
g_ref, n_ref = greens(ref_row['folder'])
h, w = g_ref.shape
# the sharpest tiles at the centre
cands = []
for y0 in range(256, h - T - 256, T):
    for x0 in range(256, w - T - 256, T):
        t = g_ref[y0:y0 + T, x0:x0 + T]
        if t.mean() < 150:
            continue
        p = band_power(t) - band_power(n_ref[y0:y0 + T, x0:x0 + T])
        cands.append((p[3], y0, x0))
cands.sort(reverse=True)
tiles = [(y0, x0) for _, y0, x0 in cands[:24]]
say('sweep: %d groups, centre %d, %d tiles (the sharpest in the 0.3-0.4 cycles/px band at the centre)' % (len(sweep), centre, len(tiles)))

curve = {}   # position -> [tile][band] signal power
shifts = {}
for r in sweep:
    g, nz = greens(r['folder'])
    key = (r['position'], r.get('note') or '')
    curve[key] = np.array([band_power(g[y0:y0 + T, x0:x0 + T]) - band_power(nz[y0:y0 + T, x0:x0 + T]) for y0, x0 in tiles])
    shifts[key] = np.array([shift(g_ref[y0:y0 + T, x0:x0 + T], g[y0:y0 + T, x0:x0 + T]) for y0, x0 in tiles[:8]])
    del g, nz
pos = sorted({k[0] for k in curve})
arr = np.array([curve[(p, '')] for p in pos])      # [position, tile, band]
say('\nband (cycles/px) | focus-curve width at half height, units (median over tiles; p10-p90) | kept 3.5 units from best focus | kept 7 units away | best-focus spread over tiles (units)')
for bi, (lo, hi) in enumerate(BANDS):
    widths, keep35, keep7, best = [], [], [], []
    for ti in range(len(tiles)):
        c = np.maximum(arr[:, ti, bi], 0)
        fine = np.linspace(pos[0], pos[-1], 20 * (len(pos) - 1) + 1)
        ci = np.interp(fine, pos, c)
        k = ci.argmax()
        if k < 40 or k > len(fine) - 40:
            continue
        half = ci >= 0.5 * ci[k]
        left = k - np.argmin(half[:k][::-1]) if not half[:k].all() else 0
        right = k + np.argmin(half[k:]) if not half[k:].all() else len(fine) - 1
        if left > 0 and right < len(fine) - 1:
            widths.append(fine[right] - fine[left])
        keep35.append(min(np.interp(fine[k] - 3.5, fine, ci), np.interp(fine[k] + 3.5, fine, ci)) / ci[k])
        keep7.append(min(np.interp(fine[k] - 7, fine, ci), np.interp(fine[k] + 7, fine, ci)) / ci[k])
        best.append(fine[k])
    if keep35:
        say('%.2f-%.2f        | %s | %.3f (worst tile %.3f) | %.3f | %.1f' % (
            lo, hi, ('%.1f (%.1f-%.1f) on %d tiles' % (np.median(widths), np.percentile(widths, 10), np.percentile(widths, 90), len(widths))) if widths else 'wider than the sweep',
            np.median(keep35), np.min(keep35), np.median(keep7), np.std(best)))
np.savez(out / 'sweep-curves.npz', positions=np.array(pos), power=arr, tiles=np.array(tiles))

say('\nshift of each sweep group against the centre group (median over 8 tiles, px):')
for p in pos:
    s = shifts[(p, '')]
    say('   %d: %+.3f, %+.3f (tile spread %.3f)' % (p, np.median(s[:, 0]), np.median(s[:, 1]), s.std(0).max()))

# revisits
say('\nrevisits of position %d:' % centre)
again = [(r, 'sweep centre again') for r in sweep if r.get('note') == 'centre again']
again += [(r, r['note']) for r in rows if r.get('series') == 'repeat']
again += [(r, 'ladder ' + (r.get('note') or '')) for r in rows if r.get('series') == 'ladder' and r['position'] == centre and abs(r['seconds'] - ref_row['seconds']) < 1e-6]
mid = arr[pos.index(centre)]
slope_note = 'fine-band power of the same tiles in the sweep at -2 / +2 units: %.3f / %.3f of the centre' % (
    np.median(arr[pos.index(centre - 2), :, 3] / mid[:, 3]), np.median(arr[pos.index(centre + 2), :, 3] / mid[:, 3]))
say('   (%s)' % slope_note)
for r, label in again:
    g, nz = greens(r['folder'])
    s = np.array([shift(g_ref[y0:y0 + T, x0:x0 + T], g[y0:y0 + T, x0:x0 + T]) for y0, x0 in tiles[:8]])
    p = np.array([band_power(g[y0:y0 + T, x0:x0 + T]) - band_power(nz[y0:y0 + T, x0:x0 + T]) for y0, x0 in tiles])
    say('   %-28s %6.1f s after the reference: shift %+.3f, %+.3f px (tile spread %.3f); 0.3-0.4 band power %.3f of the reference (tile spread %.3f)' % (
        label, r['started'] - ref_row['started'], np.median(s[:, 0]), np.median(s[:, 1]), s.std(0).max(), np.median(p[:, 3] / mid[:, 3]), np.std(p[:, 3] / mid[:, 3])))
    del g, nz
(out / 'sweep.txt').write_text('\n'.join(lines) + '\n')
