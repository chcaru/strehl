"""Focus by the lens's own through-focus signature: a NARROW peak of the fine band.

A point in focus gives the fine-band energy a peak about one sharp depth wide. Out-of-focus
highlights (bokeh discs with hard rims, clipped blobs) give humps several times wider, or energy
that keeps rising to the ends of the run. So each tile's curve is high-passed (a running median
over MEDIAN_SPAN sharp depths is subtracted) and matched against a Gaussian of the sharp depth's
width; a peak counts when it stands SIGNIFICANT robust deviations above the curve's own scatter.
Up to two peaks a tile (two surfaces can share a tile on a transparent subject).

  python narrow.py <curves folder> <capture folder> <out folder> [--width W] [--measure lap2|lap2m]

Writes narrow-<tile>.npz (first and second peak's focus and score, the engine-style argmax) and
prints the depth range by several rules.
"""
import json
import pathlib
import sys

import numpy as np
from matplotlib.path import Path as MplPath
from scipy import ndimage

MEDIAN_SPAN = 3.5          # the running median's window, sharp depths
SIGNIFICANT = 8.0
args = sys.argv[4:]
WIDTH = float(args[args.index('--width') + 1]) if '--width' in args else 45.0
MEASURE = args[args.index('--measure') + 1] if '--measure' in args else 'lap2'
src, run, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
focus = np.load(src / 'focus.npy').astype(np.float64)
step = float(np.median(np.diff(focus)))
rings = json.loads((run / 'manifest.json').read_text())['plan']['subject']['rings']


def tiles(name, t):
    a = np.load(src / (name + '.npy'), mmap_mode='r')
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


def narrow_peaks(cube, positions, width):
    """(focus1, score1, focus2, score2) per tile, NaN where there is none."""
    spacing = float(np.median(np.diff(positions)))
    p = cube.shape[0]
    c = cube.reshape(p, -1).astype(np.float64)
    span = int(round(MEDIAN_SPAN * width / spacing)) | 1
    base = ndimage.median_filter(c, size=(span, 1), mode='nearest')
    r = c - base
    sigma = width / 2.3548 / spacing
    matched = ndimage.gaussian_filter1d(r, sigma, axis=0, mode='nearest')
    # the scatter of the matched curve itself, robustly: what a peak must beat
    med = np.median(matched, axis=0)
    scat = 1.4826 * np.median(np.abs(matched - med), axis=0) + 1e-12
    score = (matched - med) / scat
    n = c.shape[1]
    out = np.full((4, n), np.nan)
    cols = np.arange(n)
    for which in (0, 1):
        k = score.argmax(0)
        s = score[k, cols]
        ok = (s >= SIGNIFICANT) & (k > 0) & (k < p - 1)
        k0 = np.clip(k, 1, p - 2)
        a, b, cc = matched[k0 - 1, cols], matched[k0, cols], matched[k0 + 1, cols]
        denom = a - 2 * b + cc
        shift = np.where(np.abs(denom) > 1e-12, 0.5 * (a - cc) / denom, 0.0)
        pos = positions[k0] + np.clip(shift, -1, 1) * spacing
        out[2 * which, ok] = pos[ok]
        out[2 * which + 1, ok] = s[ok]
        # blank the neighbourhood of this peak before looking for a second one
        reach = int(round(1.5 * width / spacing))
        idx = np.arange(p)[:, None]
        score = np.where(np.abs(idx - k[None, :]) <= reach, -np.inf, score)
    return out.reshape((4,) + cube.shape[1:])


for sensor_px, t in ((64, 4), (32, 2)):
    cube = tiles(MEASURE, t)
    if MEASURE == 'lap2m':
        cube = cube / np.maximum(tiles('nm', t), 1.0) * (t * 8) ** 2
    h, w = cube.shape[1:]
    inside = inside_mask(h, w)
    f1, s1, f2, s2 = narrow_peaks(cube, focus, WIDTH)
    argmax = focus[cube.argmax(0)]
    np.savez(out / ('narrow-%s-%d.npz' % (MEASURE, sensor_px)), f1=f1, s1=s1, f2=f2, s2=s2, argmax=argmax, inside=inside)
    have = np.isfinite(f1) & inside
    two = np.isfinite(f2) & inside
    allf = np.concatenate([f1[have], f2[two]])
    # spatial coherence: a peak whose focus is far from its 5 x 5 neighbourhood's median is an outlier
    filled = np.where(np.isfinite(f1), f1, np.nan)
    neigh = ndimage.generic_filter(filled, np.nanmedian, size=5, mode='constant', cval=np.nan)
    lonely = have & (np.abs(f1 - neigh) > 2 * WIDTH)
    coherent = have & ~lonely
    print('tile %d px, measure %s, width %.0f: subject tiles %d; with a narrow peak %d (%.1f %%); with two %d; '
          'outside the outline with a peak %d of %d'
          % (sensor_px, MEASURE, WIDTH, inside.sum(), have.sum(), 100 * have.sum() / inside.sum(), two.sum(),
             (np.isfinite(f1) & ~inside).sum(), (~inside).sum()))
    print('   first peaks: min %.0f, 0.1 %% %.0f, 0.5 %% %.0f, median %.0f, 99.5 %% %.0f, 99.9 %% %.0f, max %.0f'
          % (f1[have].min(), np.percentile(f1[have], 0.1), np.percentile(f1[have], 0.5), np.median(f1[have]),
             np.percentile(f1[have], 99.5), np.percentile(f1[have], 99.9), f1[have].max()))
    print('   all peaks (first and second): min %.0f, 0.5 %% %.0f, 99.5 %% %.0f, max %.0f; coherent first peaks %d: min %.0f max %.0f; lonely %d'
          % (allf.min(), np.percentile(allf, 0.5), np.percentile(allf, 99.5), allf.max(), coherent.sum(),
             f1[coherent].min(), f1[coherent].max(), lonely.sum()))
    am = argmax[inside]
    wrong = have & (np.abs(argmax - f1) > WIDTH)
    print('   engine-style argmax over all planes: min %.0f max %.0f; differs from the narrow peak by more than one width on %d tiles (%.1f %%); '
          'at an end plane on %d' % (am.min(), am.max(), wrong.sum(), 100 * wrong.sum() / have.sum(),
                                    ((argmax == focus[0]) | (argmax == focus[-1]))[inside].sum()))
    hist, edges = np.histogram(f1[have], bins=np.arange(focus[0], focus[-1] + 50, 50))
    print('   first peaks per 50 units from %d:' % focus[0], hist.tolist())
