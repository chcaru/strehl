"""Width of the smallest glints in an unclipped short exposure (brief Q7).

A glint is a reflection of the light in a curved facet: its image is the lens's point spread
widened by the facet's own size, so the narrowest glints bound the point spread from above.
Each isolated, unpinned local maximum of the assembled green plane gets a 2-D Gaussian fit
(with background and orientation) on a 9x9 window.

  python glint-psf.py <short four-shot folder> <mask npz> [cutoff cycles/px]
"""
import sys

import numpy as np
from scipy import ndimage, optimize

import rigdata

folder, mask8 = sys.argv[1], np.load(sys.argv[2])['mask']
cutoff = float(sys.argv[3]) if len(sys.argv) > 3 else 0.768
rgb, pinned, _ = rigdata.assemble(rigdata.members(folder))
g = rgb[..., 1]
h, w = g.shape
big = np.kron(mask8, np.ones((8, 8), bool))[2:, 2:]
m = np.zeros((h, w), bool)
m[:min(h, big.shape[0]), :min(w, big.shape[1])] = big[:h, :w]
bg = ndimage.median_filter(g[::4, ::4], 9)
bg = np.kron(bg, np.ones((4, 4), np.float32))[:h, :w]
peak = (g == ndimage.maximum_filter(g, 13)) & m & (g > 8 * np.maximum(bg, 20)) & (g > 300) & ~ndimage.maximum_filter(pinned.any(-1), 9)
ys, xs = np.nonzero(peak)
print('%d isolated unpinned maxima at least 8x their surround' % len(ys))
yy, xx = np.mgrid[-4:5, -4:5].astype(np.float64)


def model(p):
    a, x0, y0, sx, sy, th, b = p
    c, s = np.cos(th), np.sin(th)
    u = c * (xx - x0) + s * (yy - y0)
    v = -s * (xx - x0) + c * (yy - y0)
    return a * np.exp(-0.5 * (u / sx) ** 2 - 0.5 * (v / sy) ** 2) + b


rows = []
for y, x in zip(ys, xs):
    if y < 6 or x < 6 or y > h - 7 or x > w - 7:
        continue
    win = g[y - 4:y + 5, x - 4:x + 5].astype(np.float64)
    p0 = [win.max() - np.median(win), 0, 0, 0.8, 0.8, 0, np.median(win)]
    try:
        r = optimize.least_squares(lambda p: (model(p) - win).ravel(), p0, bounds=([0, -2, -2, 0.3, 0.3, -np.pi, -1e4], [1e6, 2, 2, 4, 4, np.pi, 1e5]))
    except Exception:
        continue
    a, x0, y0, sx, sy, th, b = r.x
    resid = np.sqrt(np.mean(r.fun ** 2)) / max(a, 1e-6)
    if resid > 0.06 or a < 6 * max(b, 20):
        continue
    major, minor = max(sx, sy), min(sx, sy)
    ang = (np.degrees(th) + (90 if sy > sx else 0)) % 180
    rows.append((2.3548 * minor, 2.3548 * major, ang, a, resid))
r = np.array(rows)
print('%d clean fits (residual under 6 %% of the peak)' % len(r))
if len(r):
    geo = np.sqrt(r[:, 0] * r[:, 1])
    for name, v in (('narrow axis', r[:, 0]), ('wide axis', r[:, 1]), ('geometric mean', geo)):
        print('FWHM %-15s px: p5 %.2f  p10 %.2f  p25 %.2f  median %.2f  p75 %.2f' % (name, *np.percentile(v, [5, 10, 25, 50, 75])))
    tight = r[geo <= np.percentile(geo, 25)]
    print('the tightest quarter: axis ratio median %.2f; wide-axis direction histogram (30 deg bins from the x axis): %s' % (
        np.median(tight[:, 1] / tight[:, 0]), np.histogram(tight[:, 2], bins=6, range=(0, 180))[0].tolist()))
lam_n = 1 / cutoff
sig = np.hypot(0.42 * lam_n, np.sqrt(1 / 12))
print('diffraction at cutoff %.3f cycles/px: Airy FWHM %.2f px; with a 1 px photosite about %.2f px' % (cutoff, 1.029 * lam_n, 2.3548 * sig))
