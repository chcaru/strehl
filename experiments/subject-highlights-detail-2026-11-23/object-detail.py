"""How fine is the detail on the subject? Two captures of the same pronotum at different
magnifications, compared in the subject's own units.

For each capture: signal power by frequency from the cross-spectrum of its odd and even
half-stacks (linear masters, restoration off, luminance), noise from the auto-spectrum minus
that, on the textured tiles of a region. Frequencies are converted to cycles per scale spacing
on the subject with the magnification ratio measured from the scale lattice itself. Reported:
the frequency at which signal falls to the noise of one half-stack, and the signal-to-noise
at fixed subject frequencies.

  python object-detail.py <label> <odd master> <even master> <cx> <cy> <half-size px> [<label> ...]
"""
import sys

import numpy as np
import tifffile

T = 512
fy = np.fft.fftfreq(T)[:, None]
fx = np.fft.rfftfreq(T)[None, :]
FR = np.hypot(fy, fx)
WIN = np.hanning(T)[:, None] * np.hanning(T)[None, :]
EDGES = np.linspace(0.0, 0.5, 41)


def luma(path):
    a = tifffile.imread(path)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def analyse(label, odd, even, cx, cy, half):
    a, b = luma(odd), luma(even)
    y0, y1, x0, x1 = cy - half, cy + half, cx - half, cx + half
    tiles = []
    for y in range(y0, y1 - T + 1, T // 2):
        for x in range(x0, x1 - T + 1, T // 2):
            ta, tb = a[y:y + T, x:x + T], b[y:y + T, x:x + T]
            if ta.mean() <= 0:
                continue
            fa = np.fft.rfft2((ta / ta.mean() - 1) * WIN)
            fb = np.fft.rfft2((tb / tb.mean() - 1) * WIN)
            cross = (fa * np.conj(fb)).real
            auto = 0.5 * (np.abs(fa) ** 2 + np.abs(fb) ** 2)
            s = np.array([cross[(FR >= lo) & (FR < hi)].mean() for lo, hi in zip(EDGES[:-1], EDGES[1:])])
            n = np.array([(auto - cross)[(FR >= lo) & (FR < hi)].mean() for lo, hi in zip(EDGES[:-1], EDGES[1:])])
            tiles.append((s[4:12].sum(), s, n))
    tiles.sort(key=lambda t: -t[0])
    keep = tiles[:max(4, len(tiles) // 3)]            # the most textured third: in focus, on the scales
    s = np.median([t[1] for t in keep], 0)
    n = np.median([t[2] for t in keep], 0)
    mid = 0.5 * (EDGES[:-1] + EDGES[1:])
    return {'label': label, 'mid': mid, 's': s, 'n': n, 'tiles': len(keep)}


args = sys.argv[1:]
spacings = {}
rest = []
for a in args:
    if a.startswith('--spacing='):
        k, v = a[len('--spacing='):].split(':')
        spacings[k] = float(v)
    else:
        rest.append(a)
res = [analyse(rest[i], rest[i + 1], rest[i + 2], int(rest[i + 3]), int(rest[i + 4]), int(rest[i + 5])) for i in range(0, len(rest), 6)]
for r in res:
    r['spacing'] = spacings[r['label']]
    snr = r['s'] / np.maximum(r['n'], 1e-30)
    below = np.nonzero((snr < 1.0) & (r['mid'] > 0.05))[0]
    limit = r['mid'][below[0]] if len(below) else 0.5
    r['limit'] = limit
    print('%s: %d tiles; scale spacing %.1f px; signal falls to one half-stack\'s noise at %.3f cycles/px = %.1f cycles per scale spacing' % (
        r['label'], r['tiles'], r['spacing'], limit, limit * r['spacing']))
    print('   signal/noise power at 0.1 / 0.2 / 0.3 / 0.4 cycles/px: %s' % ' / '.join('%.1f' % snr[np.argmin(np.abs(r['mid'] - f))] for f in (0.1, 0.2, 0.3, 0.4)))
if len(res) == 2:
    a, b = res
    print('magnification ratio from the scale spacing: %.2f' % (a['spacing'] / b['spacing']))
    print('detail limit in the subject\'s units, %s over %s: %.2f' % (a['label'], b['label'], (a['limit'] * a['spacing']) / (b['limit'] * b['spacing'])))
    print('signal/noise power at the same detail size on the subject (cycles per scale spacing):')
    for c in (1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20):
        row = []
        for r in res:
            f = c / r['spacing']
            if f >= 0.5:
                row.append('beyond its pixels')
            else:
                k = np.argmin(np.abs(r['mid'] - f))
                row.append('%.1f' % (r['s'][k] / max(r['n'][k], 1e-30)))
        print('   %2d: %s %s | %s %s' % (c, a['label'], row[0], b['label'], row[1]))
