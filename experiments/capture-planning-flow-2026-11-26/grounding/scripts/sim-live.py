"""A live sweep simulated from a stack: every k-th plane reduced to the preview's size (1024 x 680),
the per-tile curve's PEAK located, compared with the RAW focus (general.npz). Shows whether the
live sweep's peak positions carry the subject's depth on subjects other than the one on the rig.

  python sim-live.py <stack scratch folder> [--positions N] [--tone linear|bright]
"""
import pathlib
import sys

import cv2
import numpy as np
from scipy import ndimage

folder = pathlib.Path(sys.argv[1])
args = sys.argv[2:]
N = int(args[args.index('--positions') + 1]) if '--positions' in args else 33
TONE = args[args.index('--tone') + 1] if '--tone' in args else 'bright'
TILE = 32
g = np.load(folder / 'general.npz')
tf, coherent, inside, pos_all, order = g['focus'], g['coherent'], g['inside'], g['pos'], g['order']
files = sorted((folder / 'planes').glob('base-*.npz'))
sel = np.unique(np.round(np.linspace(0, len(pos_all) - 1, N)).astype(int))
frames = []
scale = None
for i in sel:
    m = np.load(files[order[i]])['mean8'].astype(np.float32)
    lum = cv2.resize(0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2], (1024, 680), interpolation=cv2.INTER_AREA)
    frames.append(lum)
frames = np.stack(frames)
if TONE == 'bright':                       # as a camera preview: the subject's bulk mid-grey, highlights clipped
    k = np.percentile(frames[len(frames) // 2], 90)
    frames = np.clip(frames / (2.5 * max(k, 1.0)), 0, 1) ** (1 / 2.2)
else:
    frames = frames / 15871.0
pos = pos_all[sel].astype(float)
P, H, W = frames.shape
th, tw = H // TILE, W // TILE
sm = ndimage.gaussian_filter(frames, (0, 1.0, 1.0))
gy, gx = np.gradient(sm, axis=1), np.gradient(sm, axis=2)
ts = lambda a: a[:, :th * TILE, :tw * TILE].reshape(P, th, TILE, tw, TILE).mean(axis=(2, 4))
E, L = ts(gx * gx + gy * gy), ts(sm)
M = E / (L ** 2 + 0.03 ** 2)
spacing = float(np.median(np.diff(pos)))
c = ndimage.gaussian_filter1d(M, max(40.0 / spacing, 0.7), axis=0, mode='nearest')
k = c.argmax(0)
floor, peak = np.percentile(c, 15, axis=0), c.max(0)
real = (peak > 3 * np.maximum(floor, 1e-12)) & (k > 0) & (k < P - 1)
k0 = np.clip(k, 1, P - 2)
ii, jj = np.indices(k.shape)
y0, y1, y2 = c[k0 - 1, ii, jj], c[k0, ii, jj], c[k0 + 1, ii, jj]
d = y0 - 2 * y1 + y2
est = np.where(real, pos[k0] + np.where(np.abs(d) > 1e-15, 0.5 * (y0 - y2) / np.where(np.abs(d) > 1e-15, d, 1), 0) * spacing, np.nan)
at_end = (k == 0) | (k == P - 1)
ky, kx = tf.shape[0] / th, tf.shape[1] / tw
truth = np.full((th, tw), np.nan)
sub = np.zeros((th, tw), bool)
for i in range(th):
    for j in range(tw):
        sl = (slice(int(i * ky), int((i + 1) * ky) + 1), slice(int(j * kx), int((j + 1) * kx) + 1))
        sub[i, j] = inside[sl].mean() > 0.5
        ok = coherent[sl]
        if ok.sum() >= 4 and ok.mean() > 0.5:
            truth[i, j] = np.median(tf[sl][ok])
neigh = ndimage.generic_filter(est, np.nanmedian, size=3, mode='constant', cval=np.nan)
W_ = float(np.nanmedian(g['width'][inside]))
coh = np.isfinite(est) & (np.abs(est - neigh) <= 2 * W_)
both = coh & sub & np.isfinite(truth)
err = est[both] - truth[both]
off = float(np.median(err))
print('%s | %d positions %g apart, sharp depth %.0f | offset of the coarse peak %+.0f units (%+.2f widths) | after it: half the tiles within %.0f, 90 %% within %.0f (%d tiles)'
      % (folder.name[-22:], P, spacing, W_, off, off / W_, np.median(np.abs(err - off)), np.percentile(np.abs(err - off), 90), both.sum()))
v = est[coh & sub] - off
print('      range from the sweep %d to %d | RAW truth %d to %d | subject tiles peaking at an end position: %d of %d'
      % (v.min(), v.max(), tf[coherent].min(), tf[coherent].max(), (at_end & sub).sum(), sub.sum()))
