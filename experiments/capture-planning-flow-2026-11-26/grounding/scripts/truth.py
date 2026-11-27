"""Where the subject is in focus, tile by tile, from every plane of a capture; and what simpler
rules would have said.

A tile's curve is `strehl focus-step`'s measure (the green Laplacian's energy) against focus. A
tile is RESOLVED when its curve has a real peak inside the run: at least PEAK_OVER_FLOOR times its
own 10th percentile, both half-height crossings inside the run. Its focus is the centroid of the
curve above half height. Everything else is UNRESOLVED and is sorted by why: flat (no peak),
rising to the first plane, rising to the last plane.

Reported for tiles of 64, 32 and 16 sensor pixels, and for subsets of the planes (a survey).

  python truth.py <curves folder> <capture folder> <out folder>
"""
import json
import pathlib
import sys

import numpy as np
from matplotlib.path import Path as MplPath

PEAK_OVER_FLOOR = 6.0
src, run, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
focus = np.load(src / 'focus.npy').astype(np.float64)
lap_blocks = np.load(src / 'lap2.npy', mmap_mode='r')
rings = json.loads((run / 'manifest.json').read_text())['plan']['subject']['rings']


def tiles(a, t):
    p, h, w = a.shape
    h, w = h // t * t, w // t * t
    return np.asarray(a[:, :h, :w]).reshape(p, h // t, t, w // t, t).sum(axis=(2, 4))


def inside_mask(h, w):
    yy, xx = np.mgrid[0:h, 0:w]
    pts = np.column_stack([(xx.ravel() + 0.5) / w, (yy.ravel() + 0.5) / h])
    m = np.zeros(h * w, bool)
    for ring in rings:
        m |= MplPath(np.array(ring)).contains_points(pts)
    return m.reshape(h, w)


def resolve(cube, pos):
    """Per tile: kind (0 flat, 1 resolved, 2 rising to first, 3 rising to last), focus, width, peak."""
    p = cube.shape[0]
    c = cube.reshape(p, -1)
    floor = np.percentile(c, 10, axis=0)
    k = c.argmax(0)
    peak = c[k, np.arange(c.shape[1])]
    real = peak >= PEAK_OVER_FLOOR * np.maximum(floor, 1e-9)
    half = floor + (peak - floor) / 2
    above = c > half
    kind = np.zeros(c.shape[1], np.int8)
    foc = np.full(c.shape[1], np.nan)
    wid = np.full(c.shape[1], np.nan)
    idx = np.nonzero(real)[0]
    for i in idx:
        a = b = k[i]
        while a > 0 and above[a - 1, i]:
            a -= 1
        while b < p - 1 and above[b + 1, i]:
            b += 1
        if a == 0:
            kind[i] = 2
            continue
        if b == p - 1:
            kind[i] = 3
            continue
        kind[i] = 1
        seg = c[a:b + 1, i] - half[i]
        foc[i] = (seg * pos[a:b + 1]).sum() / seg.sum()
        lo = pos[a - 1] + (pos[a] - pos[a - 1]) * (half[i] - c[a - 1, i]) / (c[a, i] - c[a - 1, i])
        hi = pos[b] + (pos[b + 1] - pos[b]) * (c[b, i] - half[i]) / (c[b, i] - c[b + 1, i])
        wid[i] = hi - lo
    shape = cube.shape[1:]
    return kind.reshape(shape), foc.reshape(shape), wid.reshape(shape), peak.reshape(shape), floor.reshape(shape)


report = {}
for sensor_px, t in ((64, 4), (32, 2), (16, 1)):
    cube = tiles(lap_blocks, t)
    h, w = cube.shape[1:]
    inside = inside_mask(h, w)
    kind, foc, wid, peak, floor = resolve(cube, focus)
    sub = inside
    n = int(sub.sum())
    res = (kind == 1) & sub
    f = foc[res]
    row = {
        'tile_px': sensor_px, 'subject_tiles': n,
        'resolved': int(res.sum()), 'flat': int(((kind == 0) & sub).sum()),
        'rising_to_first': int(((kind == 2) & sub).sum()), 'rising_to_last': int(((kind == 3) & sub).sum()),
        'focus_min': float(f.min()), 'focus_p0.5': float(np.percentile(f, 0.5)), 'focus_p50': float(np.median(f)),
        'focus_p99.5': float(np.percentile(f, 99.5)), 'focus_max': float(f.max()),
        'width_p10': float(np.nanpercentile(wid[res], 10)), 'width_p50': float(np.nanmedian(wid[res])),
        'width_p90': float(np.nanpercentile(wid[res], 90)),
        'outside_resolved': int(((kind == 1) & ~sub).sum()), 'outside_tiles': int((~sub).sum()),
    }
    # the unresolved tiles that rise to an end: how strong are they against the resolved peaks?
    med_peak = float(np.median(peak[res]))
    for name, code in (('first', 2), ('last', 3)):
        sel = (kind == code) & sub
        if sel.any():
            row['rising_to_%s_peak_over_resolved_median' % name] = float(np.median(peak[sel]) / med_peak)
    report[sensor_px] = row
    np.savez(out / ('tiles-%d.npz' % sensor_px), kind=kind, focus=foc, width=wid, peak=peak, floor=floor, inside=inside)
    print(json.dumps(row))

# The engine's rule on the same data: a tile "in focus" at the plane of its largest energy, whatever
# the curve; depth = first and last such plane (full), or the central 99 % (core).
cube = tiles(lap_blocks, 4)
inside = inside_mask(*cube.shape[1:])
z = np.load(out / 'tiles-64.npz')
for label, sel in (('all 151 planes', np.arange(len(focus))), ('13 planes spread', np.round(np.linspace(0, len(focus) - 1, 13)).astype(int)),
                   ('25 planes spread', np.round(np.linspace(0, len(focus) - 1, 25)).astype(int))):
    c = cube[sel][:, inside]
    k = c.argmax(0)
    floor = np.percentile(c, 10, axis=0)
    peak = c.max(0)
    real = peak >= PEAK_OVER_FLOOR * np.maximum(floor, 1e-9)
    pos = focus[sel]
    edge = (k == 0) | (k == len(sel) - 1)
    interior = real & ~edge
    print('%-18s argmax rule: full %d to %d; central 99 %% of tiles %d to %d; tiles peaking at an end plane %d of %d; '
          'with a real interior peak %d: %d to %d (0.5 to 99.5 %%: %d to %d)'
          % (label, pos[k].min(), pos[k].max(), np.percentile(pos[k], 0.5), np.percentile(pos[k], 99.5), edge.sum(), len(k),
             interior.sum(), pos[k[interior]].min(), pos[k[interior]].max(),
             np.percentile(pos[k[interior]], 0.5), np.percentile(pos[k[interior]], 99.5)))
(out / 'truth.json').write_text(json.dumps(report, indent=1))
