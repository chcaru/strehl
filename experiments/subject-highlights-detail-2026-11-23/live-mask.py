"""The subject mask from live-view frames alone (brief Q9): no RAW is taken.

Same evidence as subject-mask.py on the camera's 1024 px preview JPEGs of a focus sweep:
fine energy of luma per 4x4 px block, normalised by the frame's own quiet level, registered
by one magnification rate, the largest value over the sweep, thresholded against the quiet
population, grown by hysteresis.

  python live-mask.py <folder of live-NNNNN.jpg> <out prefix> [--every K]
"""
import glob
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

folder, prefix = sys.argv[1], sys.argv[2]
every = int(sys.argv[sys.argv.index('--every') + 1]) if '--every' in sys.argv else 1
files = sorted(glob.glob(str(pathlib.Path(folder) / 'live-*.jpg')))[::every]
B = 4
frames, energy = [], []
for f in files:
    im = np.asarray(Image.open(f).convert('RGB'), np.float32) / 255
    lin = np.where(im <= 0.04045, im / 12.92, ((im + 0.055) / 1.055) ** 2.4)
    y = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    # JPEG blocks are 8 px: a 3x3 Laplacian of a lightly smoothed image keeps block edges out
    lap = ndimage.laplace(ndimage.gaussian_filter(y, 0.7))
    h, w = y.shape[0] // B * B, y.shape[1] // B * B
    e = (lap[:h, :w] ** 2).reshape(h // B, B, w // B, B).mean((1, 3))
    frames.append(y[:h, :w].reshape(h // B, B, w // B, B).mean((1, 3)))
    energy.append(e)
mean = np.stack(frames)
fine = np.stack(energy)
n, h, w = fine.shape
print('frames', n, 'grid', h, 'x', w)


def rescale(img, s):
    cy, cx = (h - 1) / 2, (w - 1) / 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return ndimage.map_coordinates(img, [cy + (yy - cy) / s, cx + (xx - cx) / s], order=1, mode='nearest')


i, j = n // 4, 3 * n // 4
ref, mov = ndimage.gaussian_filter(mean[i], 2), ndimage.gaussian_filter(mean[j], 2)
best = max(((np.corrcoef(ref[8:-8, 8:-8].ravel(), rescale(mov, s)[8:-8, 8:-8].ravel())[0, 1], s) for s in np.linspace(0.96, 1.04, 81)))
rate = np.log(best[1]) / (j - i)
print('registration: frame %d onto %d needs scale %.4f (corr %.4f)' % (j, i, best[1], best[0]))
for k in range(n):
    s = float(np.exp(-rate * (k - n // 2)))
    fine[k] = rescale(fine[k], s)
    mean[k] = rescale(mean[k], s)
# quiet level per frame: the median energy of the darkest-energy third of blocks
z = np.stack([ndimage.uniform_filter(f / max(np.median(f[f <= np.percentile(f, 33)]), 1e-12), 3) for f in fine])
zs = ndimage.uniform_filter1d(z, 3, axis=0, mode='nearest') if n >= 3 else z
focus = zs.max(0)
lf = np.log(np.maximum(focus, 1e-3))
low = lf[lf <= np.percentile(lf, 60)]
hist, edges = np.histogram(low, bins=120)
hist = ndimage.uniform_filter1d(hist.astype(np.float64), 5)
mode = 0.5 * (edges[hist.argmax()] + edges[hist.argmax() + 1])
spread = max(mode - np.percentile(lf[lf < mode], 16), 0.02)
cut = np.exp(mode + 6 * spread)
level = np.median(mean, 0)
quiet = focus < np.exp(mode + 3 * spread)
b_med = np.median(level[quiet])
b_mad = 1.4826 * np.median(np.abs(level[quiet] - b_med)) + 1e-6
differs = np.abs(level - b_med) / b_mad
raw = (focus >= cut) | ((differs >= 36) & (level > b_med + 0.002))
weak = (focus >= np.exp(mode + 3 * spread)) | (differs >= 12)
wl, _ = ndimage.label(weak | raw)
raw = np.isin(wl, np.unique(wl[raw])) & (wl > 0)
m = ndimage.binary_closing(raw, iterations=2)
holes = ndimage.binary_fill_holes(m) & ~m
hl, hk = ndimage.label(holes)
if hk:
    hs = ndimage.sum(holes, hl, range(1, hk + 1))
    m |= np.isin(hl, [q + 1 for q, s in enumerate(hs) if s < 0.0005 * h * w])
lab, k = ndimage.label(m)
sizes = ndimage.sum(m, lab, range(1, k + 1))
m = np.isin(lab, [q + 1 for q, s in enumerate(sizes) if s >= 0.002 * h * w])
m = ndimage.binary_dilation(m, iterations=1)
print('quiet mode %.2f, threshold %.2f; mask %.2f %% of the frame' % (np.exp(mode), cut, 100 * m.mean()))
np.savez_compressed(prefix + '.npz', mask=m, focus=focus.astype(np.float32))
g = np.clip(np.sqrt(level / max(np.percentile(level, 99.5), 1e-6)), 0, 1)
rgb = np.stack([g, g, g], -1)
rgb[m & ~ndimage.binary_erosion(m)] = [1.0, 0.85, 0.1]
rgb[~m] *= 0.45
Image.fromarray((rgb * 255).astype(np.uint8)).resize((w * 4, h * 4), Image.NEAREST).save(prefix + '.png')
