"""The calibrated tier against its placebo.

  python compare-placebo.py <folder with lossless.tif, k1.tif, placebo.tif>

k1.tif is the render from samples requantised at one noise sigma; placebo.tif the render from
samples given independent random noise of the same size at every level (s9). If quantising
behaves like noise of its size, the two renders must stand at the same distance from the
lossless render, in flat tiles and in detail tiles alike, and at about sqrt(2) of that
distance from each other.
"""
import pathlib
import sys

import cv2
import numpy as np
import tifffile

src = pathlib.Path(sys.argv[1])
img = {n: tifffile.imread(str(src / (n + '.tif')))[..., 1].astype(np.float32) for n in ('lossless', 'k1', 'placebo')}
T = 128
a = img['lossless']
h, w = a.shape
th, tw = h // T, w // T


def tiles(e):
    return e[:th * T, :tw * T].reshape(th, T, tw, T).mean(axis=(1, 3))


s = cv2.GaussianBlur(a, (0, 0), 1.5)
ref = tiles(cv2.Sobel(s, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(s, cv2.CV_32F, 0, 1) ** 2)
inner = np.zeros((th, tw), bool)
inner[2:-2, 2:-2] = True
order = np.sort(ref[inner])
flat = inner & (ref <= order[int(0.2 * len(order))])
detail = inner & (ref >= order[int(0.9 * len(order))])
hp = a - cv2.GaussianBlur(a, (0, 0), 2.0)
own = np.sqrt(tiles(hp * hp))
print('the lossless render\'s own high-pass rms: flat tiles %.2f, detail tiles %.2f (detail there is signal, not noise)' % (
    np.median(own[flat]), np.median(own[detail])))
print('\npair                    rms difference: flat tiles (median)   detail tiles (median)   detail tiles (90th percentile)   whole frame')
for x, y in (('k1', 'lossless'), ('placebo', 'lossless'), ('k1', 'placebo')):
    d = img[x] - img[y]
    t = np.sqrt(tiles(d * d))
    print('%-8s vs %-9s   %8.3f   %8.3f   %8.3f   %8.3f' % (x, y, np.median(t[flat]), np.median(t[detail]), np.percentile(t[detail], 90), float(np.sqrt(np.mean(d * d)))))
print('\ngradient energy relative to the lossless render (blur 1.0 px), median over tiles: flat, detail')
ea = tiles(cv2.Sobel(cv2.GaussianBlur(a, (0, 0), 1.0), cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(cv2.GaussianBlur(a, (0, 0), 1.0), cv2.CV_32F, 0, 1) ** 2)
for x in ('k1', 'placebo'):
    b = cv2.GaussianBlur(img[x], (0, 0), 1.0)
    eb = tiles(cv2.Sobel(b, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(b, cv2.CV_32F, 0, 1) ** 2)
    print('   %-8s %.4f, %.4f' % (x, np.median(eb[flat] / ea[flat]), np.median(eb[detail] / ea[detail])))
print('\nlevels (green mean): lossless %.3f, k1 %+.4f, placebo %+.4f' % (
    float(a.mean()), float(img['k1'].mean() - a.mean()), float(img['placebo'].mean() - a.mean())))
