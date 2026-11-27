"""Can ONE frame tell a tile in focus from a tile of bright blur?

Truth: the narrow fine-band peak of narrow.py (first peak, at least GUARD widths from the run's
ends, score at least SCORE). For every such tile and every plane the candidate single-frame
measures are tabulated against the plane's distance from the tile's focus, in sharp depths:

  energy   the fine band's energy over its noise expectation (what the engine thresholds)
  ratio    fine energy / mid-band energy, both above their noise expectations
  ratio_m  the same with the fine band taken away from bright samples

The noise expectation of the fine band is fitted on (tile, plane) pairs more than FAR widths from
focus: lap2 per pixel = a + b * mean level (photon noise: linear in the level).

  python index.py <curves folder> <truth folder> <out json> [--width W]
"""
import json
import pathlib
import sys

import numpy as np

args = sys.argv[4:]
WIDTH = float(args[args.index('--width') + 1]) if '--width' in args else 45.0
GUARD, SCORE, FAR = 1.5, 20.0, 6.0
src, truth, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
focus = np.load(src / 'focus.npy').astype(np.float64)
T = 4


def tiles(name):
    a = np.load(src / (name + '.npy'), mmap_mode='r')
    p, h, w = a.shape
    h, w = h // T * T, w // T * T
    return np.asarray(a[:, :h, :w]).reshape(p, h // T, T, w // T, T).sum(axis=(2, 4))


px = (T * 8) ** 2
lap, mid, lapm, nm = tiles('lap2') / px, tiles('mid2') / px, tiles('lap2m'), tiles('nm')
mean, bright, pin = tiles('mean') / T ** 2, tiles('bright'), tiles('pin')
lapm = lapm / np.maximum(nm, 1)
z = np.load(truth / 'narrow-lap2-64.npz')
f1, s1, inside = z['f1'], z['s1'], z['inside']
good = inside & np.isfinite(f1) & (s1 >= SCORE) & (f1 > focus[0] + GUARD * WIDTH) & (f1 < focus[-1] - GUARD * WIDTH)
print('subject tiles', inside.sum(), 'with a trusted focus', good.sum(), 'range %.0f to %.0f' % (f1[good].min(), f1[good].max()))
dist = np.abs(focus[:, None, None] - f1[None]) / WIDTH            # (planes, h, w), in widths
far = (dist > FAR) & good[None] & (bright == 0)
# noise of the fine band against the level, from far-from-focus samples: the lower envelope
lv, e = mean[far], lap[far]
edges = np.percentile(lv, np.linspace(0, 100, 21))
cx, cy = [], []
for a, b in zip(edges[:-1], edges[1:]):
    s = (lv >= a) & (lv <= b)
    if s.sum() > 200:
        cx.append(np.median(lv[s])); cy.append(np.percentile(e[s], 10))
bfit, afit = np.polyfit(cx, cy, 1)
print('fine-band noise per pixel = %.1f + %.4f x level (DN; fitted on the 10th percentile of %d far samples)' % (afit, bfit, far.sum()))
noise_f = afit + bfit * np.maximum(mean, 0)
# mid band: its noise is the same variance through a far smaller kernel power (0.0159 against 20)
noise_m = noise_f * (0.01592 / 20.0)
energy = lap / noise_f
ratio = np.maximum(lap - noise_f, 0) / np.maximum(mid - noise_m, noise_m)
ratio_m = np.maximum(lapm - noise_f, 0) / np.maximum(mid - noise_m, noise_m)
measures = {'energy': energy, 'ratio': ratio, 'ratio_m': ratio_m}
bands = [(0, 0.25, 'in focus (within 1/4 width)'), (0.25, 0.6, '1/4 to 0.6'), (0.6, 1.0, '0.6 to 1'), (1.0, 2.0, '1 to 2'),
         (2.0, 4.0, '2 to 4'), (4.0, 8.0, '4 to 8'), (8.0, 99.0, 'over 8')]
report = {'noise': [float(afit), float(bfit)], 'tables': {}}
gsel = np.broadcast_to(good[None], dist.shape)
for name, m in measures.items():
    rows = []
    for a, b, label in bands:
        s = gsel & (dist >= a) & (dist < b)
        v = m[s]
        rows.append({'band': label, 'n': int(s.sum()), 'p5': float(np.percentile(v, 5)), 'p25': float(np.percentile(v, 25)),
                     'p50': float(np.median(v)), 'p75': float(np.percentile(v, 75)), 'p95': float(np.percentile(v, 95)),
                     'p99': float(np.percentile(v, 99)), 'p999': float(np.percentile(v, 99.9))})
    report['tables'][name] = rows
    print('\n%s by distance from focus (5 / 25 / 50 / 75 / 95 / 99 / 99.9 %%):' % name)
    for r in rows:
        print('  %-28s n %8d  %9.3g %9.3g %9.3g %9.3g %9.3g %9.3g %9.3g' % (r['band'], r['n'], r['p5'], r['p25'], r['p50'], r['p75'], r['p95'], r['p99'], r['p999']))
    # one threshold: keep 90 % of the in-focus samples; how many samples over 2 widths away pass it?
    infocus = m[gsel & (dist < 0.25)]
    thr = np.percentile(infocus, 10)
    for a, b, label in ((1.0, 2.0, '1 to 2 widths'), (2.0, 4.0, '2 to 4'), (4.0, 99.0, 'over 4')):
        s = gsel & (dist >= a) & (dist < b)
        print('  threshold %.3g (keeps 90 %% of in-focus): passes %.2f %% of samples %s away' % (thr, 100 * (m[s] >= thr).mean(), label))
    # tiles of the subject with no trusted focus, and the background
    for label, sel in (('subject tiles with no trusted focus', inside & ~good), ('outside the outline', ~inside)):
        v = m[:, sel]
        print('  %s: passes %.2f %% of samples; tiles ever passing %.1f %%' % (label, 100 * (v >= thr).mean(), 100 * (v >= thr).any(0).mean()))
    report['tables'][name + '_threshold'] = float(thr)
out.write_text(json.dumps(report, indent=1))
