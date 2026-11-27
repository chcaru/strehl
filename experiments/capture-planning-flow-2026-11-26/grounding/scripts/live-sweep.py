"""What a live-view sweep can know of the subject's range, measured on real preview frames.

The frames are rig-series.py's: the camera's 1024 x 680 preview after each lens move. Compared:

  host      the host's own measure and rule, re-implemented from `strehl-capture/src/bounds.rs`
            (6 x 4 tiles of the subject box, smoothed gradient energy over the tile's mean level
            squared, half-height spans widened by two positions)
  peaks     small tiles (TILE preview px); each tile's curve is located by its PEAK (a parabola
            through the three highest samples of the smoothed curve), not by its half-height span
  contrast  the same tiles with the level taken from the neighbourhood and a floor

Truth is the RAW stack's per-tile focus (general.npz: narrow fine-band peaks), resampled to the
preview's tiles. Reported: each rule's range against the truth's, and the per-tile error of the
peak positions.

  python live-sweep.py <series folder> <sweep name> <stack scratch folder with general.npz> [--every N]
"""
import json
import pathlib
import sys

import cv2
import numpy as np
from scipy import ndimage

series, name, stack = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
args = sys.argv[4:]
EVERY = int(args[args.index('--every') + 1]) if '--every' in args else 1
TILE = 32
rec = json.loads((series / 'record.json').read_text())
rows = rec['sweeps'][name]['rows'][::EVERY]
pos = np.array([r['position'] for r in rows], float)


def luma(path):
    im = cv2.imread(str(path)).astype(np.float32) / 255.0          # BGR
    return 0.0722 * im[..., 0] + 0.7152 * im[..., 1] + 0.2126 * im[..., 2]


frames = np.stack([np.mean([luma(series / name / f) for f in r['frames']], axis=0) for r in rows])
P, H, W = frames.shape
print('%s: %d positions %d to %d, spacing %g, preview %d x %d' % (name, P, pos[0], pos[-1], np.median(np.diff(pos)), W, H))


# ---- the host's measure and rule
def host_scores(img, roi=(0.1, 0.1, 0.8, 0.8)):
    sm = (img * 4 + np.roll(img, 1, 1) + np.roll(img, -1, 1) + np.roll(img, 1, 0) + np.roll(img, -1, 0)) / 8
    gx = np.roll(sm, -2, 1) - np.roll(sm, 2, 1)
    gy = np.roll(sm, -2, 0) - np.roll(sm, 2, 0)
    e = gx * gx + gy * gy
    ok = (sm >= 0.02) & (sm < 0.97)
    out = []
    x0, y0, w, h = roi
    for ty in range(4):
        for tx in range(6):
            l, r = int((x0 + w * tx / 6) * W), int((x0 + w * (tx + 1) / 6) * W)
            t, b = int((y0 + h * ty / 4) * H), int((y0 + h * (ty + 1) / 4) * H)
            sl = (slice(max(t, 3), min(b, H - 4), 3), slice(max(l, 3), min(r, W - 4), 3))
            m = ok[sl]
            n = int(m.sum())
            out.append(0.0 if n < 16 else float(e[sl][m].sum() / n / max((sm[sl][m].sum() / n) ** 2, 0.01)))
    return out


def host_suggest(scores):
    scores = np.array(scores)
    first, last, support, clipped = len(pos) - 1, 0, 0, False
    for tile in range(scores.shape[1]):
        c = scores[:, tile]
        floor = np.sort(c)[len(c) // 4]
        peak = int(c.argmax())
        prom = c[peak] - floor
        if prom < 0.00003 or prom < max(floor, 0.00001) * 0.6:
            continue
        thr = floor + prom * 0.5
        a = b = peak
        while a > 0 and c[a - 1] >= thr:
            a -= 1
        while b + 1 < len(c) and c[b + 1] >= thr:
            b += 1
        if b - a < 2:
            continue
        support += 1
        clipped |= a == 0 or b == len(c) - 1
        first, last = min(first, max(a - 2, 0)), max(last, min(b + 2, len(c) - 1))
    if clipped:
        first, last = 0, len(pos) - 1
    return pos[first], pos[last], support, clipped


hs = [host_scores(f) for f in frames]
a, b, support, clipped = host_suggest(hs)
print('host rule: %d to %d (%d tiles supported%s)' % (a, b, support, '; CLIPPED: the whole sweep is kept' if clipped else ''))

# ---- small tiles
th, tw = H // TILE, W // TILE
sm = ndimage.gaussian_filter(frames, (0, 1.0, 1.0))
gy, gx = np.gradient(sm, axis=1), np.gradient(sm, axis=2)
e = (gx * gx + gy * gy)


def tile_sum(a):
    return a[:, :th * TILE, :tw * TILE].reshape(P, th, TILE, tw, TILE).mean(axis=(2, 4))


E = tile_sum(e)
L = tile_sum(sm)
Lnear = ndimage.maximum_filter(L, size=(1, 3, 3), mode='nearest')
measures = {'energy / own level^2': E / np.maximum(L, 0.02) ** 2, 'energy / neighbourhood level^2': E / (Lnear ** 2 + 0.03 ** 2)}

# truth on the preview's tiles: the RAW stack's per-tile focus (64 px tiles of the 9564-wide frame)
g = np.load(stack / 'general.npz')
tf, coherent, inside = g['focus'], g['coherent'], g['inside']
ty = np.clip(((np.arange(th) + 0.5) / th * tf.shape[0]).astype(int), 0, tf.shape[0] - 1)
tx = np.clip(((np.arange(tw) + 0.5) / tw * tf.shape[1]).astype(int), 0, tf.shape[1] - 1)
# a preview tile covers about 4.7 x 4.7 truth tiles: the median of those with a trusted focus
truth = np.full((th, tw), np.nan)
share = np.zeros((th, tw))
ky, kx = tf.shape[0] / th, tf.shape[1] / tw
for i in range(th):
    for j in range(tw):
        blk = tf[int(i * ky):int((i + 1) * ky) + 1, int(j * kx):int((j + 1) * kx) + 1]
        ok = coherent[int(i * ky):int((i + 1) * ky) + 1, int(j * kx):int((j + 1) * kx) + 1]
        share[i, j] = ok.mean()
        if ok.sum() >= 4:
            truth[i, j] = np.median(blk[ok])
trusted = np.isfinite(truth) & (share > 0.5)
print('truth: %d preview tiles with a trusted focus; their range %d to %d; the stack\'s own %d to %d'
      % (trusted.sum(), np.nanmin(truth[trusted]), np.nanmax(truth[trusted]), g['focus'][coherent].min(), g['focus'][coherent].max()))

spacing = float(np.median(np.diff(pos)))
report = {'positions': P, 'spacing': spacing, 'host': {'start': float(a), 'end': float(b), 'supported': int(support), 'clipped': bool(clipped)}}
for label, M in measures.items():
    c = ndimage.gaussian_filter1d(M, max(40.0 / spacing, 0.7), axis=0, mode='nearest')      # smooth over 40 units
    k = c.argmax(0)
    floor = np.percentile(c, 15, axis=0)
    peak = c.max(0)
    real = (peak > 3 * np.maximum(floor, 1e-9)) & (k > 0) & (k < P - 1)
    k0 = np.clip(k, 1, P - 2)
    ii, jj = np.indices(k.shape)
    y0, y1, y2 = c[k0 - 1, ii, jj], c[k0, ii, jj], c[k0 + 1, ii, jj]
    d = y0 - 2 * y1 + y2
    est = pos[k0] + np.where(np.abs(d) > 1e-12, 0.5 * (y0 - y2) / np.where(np.abs(d) > 1e-12, d, 1), 0) * spacing
    est = np.where(real, est, np.nan)
    both = trusted & np.isfinite(est)
    err = est[both] - truth[both]
    lo, hi = np.nanpercentile(est[real], [1, 99]) if real.any() else (np.nan, np.nan)
    # half-height width of a typical curve: how blunt the live measure is
    widths = []
    for i, j in zip(*np.nonzero(both)):
        col = c[:, i, j]; half = floor[i, j] + (peak[i, j] - floor[i, j]) / 2
        above = np.nonzero(col >= half)[0]
        widths.append((above[-1] - above[0] + 1) * spacing)
    print('%-32s tiles with a peak %d (of them outside the subject %d); peak range 1-99 %%: %d to %d (min %d, max %d)'
          % (label, real.sum(), (real & ~np.isfinite(truth)).sum(), lo, hi, np.nanmin(est), np.nanmax(est)))
    print('%-32s against the RAW focus on %d tiles: median error %+.0f units, half the errors within %.0f, 90 %% within %.0f; curve width at half height, median %.0f units'
          % ('', both.sum(), np.median(err), np.median(np.abs(err - np.median(err))), np.percentile(np.abs(err - np.median(err)), 90), np.median(widths)))
    report[label] = {'tiles': int(real.sum()), 'p1': float(lo), 'p99': float(hi), 'min': float(np.nanmin(est)), 'max': float(np.nanmax(est)),
                     'median_error': float(np.median(err)), 'mad': float(np.median(np.abs(err - np.median(err)))),
                     'p90_abs': float(np.percentile(np.abs(err - np.median(err)), 90)), 'curve_width': float(np.median(widths))}
    np.save(series / ('live-%s-%s-est.npy' % (name, 'own' if 'own' in label else 'near')), est)
(series / ('live-%s%s.json' % (name, '' if EVERY == 1 else '-every%d' % EVERY))).write_text(json.dumps(report, indent=1))
