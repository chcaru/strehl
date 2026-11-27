"""Three checks over every measured stack, from general.npz and the curves:

  A. Sensitivity. The contrast rule's range with its parameters moved (the share of the subject's
     own reference that counts as in focus; how many tiles make a plane count). A rule that only
     works at one setting is fitted, not found.
  B. The in-flight stop. Walking the planes in capture order with only what has been seen so far:
     the reference is seeded from the plane nearest the subject's median focus (the proof plane),
     a plane is "live" when enough tiles pass; the flight would stop one and a half sharp depths
     after the last live plane. Where is that, against the truth and the captured end?
  C. The sharp depth from a short dense cluster: 9, 13, 17 and 25 planes at the stack's own spacing
     around the plane with most tiles in focus, against the whole stack's figure.

  python robust.py <stack scratch folder> [...]
"""
import json
import pathlib
import sys

import numpy as np

PEAK_OVER_FLOOR = 6.0


def half_width_median(cube, pos):
    p = cube.shape[0]
    c = cube.reshape(p, -1)
    floor = np.percentile(c, 10, axis=0)
    k = c.argmax(0)
    peak = c[k, np.arange(c.shape[1])]
    real = (peak >= PEAK_OVER_FLOOR * np.maximum(floor, 1e-9)) & (k > 0) & (k < p - 1)
    half = floor + (peak - floor) / 2
    out = []
    for i in np.nonzero(real)[0]:
        a = b = k[i]
        while a > 0 and c[a - 1, i] > half[i]:
            a -= 1
        while b < p - 1 and c[b + 1, i] > half[i]:
            b += 1
        if a == 0 or b == p - 1:
            continue
        lo = pos[a - 1] + (pos[a] - pos[a - 1]) * (half[i] - c[a - 1, i]) / (c[a, i] - c[a - 1, i])
        hi = pos[b] + (pos[b + 1] - pos[b]) * (c[b, i] - half[i]) / (c[b, i] - c[b + 1, i])
        out.append(hi - lo)
    return (float(np.median(out)) if len(out) >= 30 else float('nan')), len(out)


for arg in sys.argv[1:]:
    folder = pathlib.Path(arg)
    g = np.load(folder / 'general.npz')
    meta = json.loads((folder / 'general.json').read_text())
    pos, order, inside, f, coherent = g['pos'], g['order'], g['inside'], g['focus'], g['coherent']
    cb = g['contrast'].astype(np.float32)
    sub = cb[:, inside]
    W = meta['width_64']['p50']
    truth = meta['truth']
    P = len(pos)
    step = float(np.median(np.diff(pos)))
    print('\n== %s | captured %d to %d | truth %d to %d | sharp depth %.0f' % (meta['run'][-22:], pos[0], pos[-1], *truth, W))
    # A
    best = sub.max(0)
    ref = float(np.percentile(best, 90))
    line = []
    for share in (0.1, 0.2, 0.3, 0.4):
        for need in (0.0005, 0.002):
            counts = (sub >= share * ref).sum(1)
            live = counts >= max(3, need * sub.shape[1])
            line.append('share %.1f, %.2f %% of tiles: %d to %d (ends %d, %d)' % (share, 100 * need, pos[live].min(), pos[live].max(), counts[0], counts[-1]))
    print('   A ' + '\n     '.join(line))
    # B
    seed = int(np.argmin(np.abs(pos - np.nanmedian(f[coherent]))))
    ref_seed = float(np.percentile(sub[seed], 90))             # the proof plane's own tiles
    thr = 0.2 * max(ref_seed, 1e-9)
    counts = (sub >= thr).sum(1)
    live = counts >= max(3, 0.0005 * sub.shape[1])
    last_live, stop = None, None
    for i in range(P):
        if live[i]:
            last_live = i
        if last_live is not None and stop is None and pos[i] - pos[last_live] >= 1.5 * W:
            stop = i
    first_live = int(np.argmax(live))
    print('   B seeded from the plane at %d (reference %.3f against the whole stack\'s %.3f): first live plane %d, last live %d; the flight would stop at %s; truth end %d; captured end %d; planes saved at the far end %s'
          % (pos[seed], ref_seed, ref, pos[first_live], pos[last_live], 'the end of the run (still live)' if stop is None else '%d' % pos[stop],
             truth[1], pos[-1], '0' if stop is None else '%d' % (P - 1 - stop)))
    # C
    lap = np.load(folder / 'curves' / 'lap2.npy', mmap_mode='r')
    T = 4
    h, w = lap.shape[1] // T * T, lap.shape[2] // T * T
    centre = int(np.argmax(g['truth_count']))
    parts = []
    for n in (9, 13, 17, 25):
        a = max(0, min(centre - n // 2, P - n))
        idx = np.arange(a, a + n)
        cube = np.stack([np.asarray(lap[order[i], :h, :w]).reshape(h // T, T, w // T, T).sum(axis=(1, 3)) for i in idx])[:, inside]
        wd, tiles = half_width_median(cube, pos[idx])
        parts.append('%d planes (%d units): %.0f on %d tiles' % (n, (n - 1) * step, wd, tiles))
    print('   C cluster at %d, spacing %g: %s; whole stack %.0f' % (pos[centre], step, '; '.join(parts), W))
