"""Is the detail-shaped part of (k = 1 render minus lossless render) a registration difference?

  python shift-k1.py <folder with lossless.tif and k1.tif>

Phase correlation of the two renders' green channel in 512 px windows on the most detailed
parts of the frame gives their relative displacement; a displacement of s px leaves a
difference of about s times the local gradient, which is then compared with the difference
actually found there.
"""
import pathlib
import sys

import cv2
import numpy as np
import tifffile

src = pathlib.Path(sys.argv[1])
a = tifffile.imread(str(src / 'lossless.tif'))[..., 1].astype(np.float32)
b = tifffile.imread(str(src / 'k1.tif'))[..., 1].astype(np.float32)
W = 512
h, w = a.shape
hann = cv2.createHanningWindow((W, W), cv2.CV_32F)
s = cv2.GaussianBlur(a, (0, 0), 1.0)
gx, gy = cv2.Sobel(s, cv2.CV_32F, 1, 0), cv2.Sobel(s, cv2.CV_32F, 0, 1)
e = gx * gx + gy * gy
th, tw = h // W, w // W
tiles = e[:th * W, :tw * W].reshape(th, W, tw, W).mean(axis=(1, 3))
rows = []
for i in np.argsort(-tiles.ravel())[:24]:
    ty, tx = divmod(int(i), tw)
    y0, x0 = ty * W, tx * W
    pa, pb = a[y0:y0 + W, x0:x0 + W], b[y0:y0 + W, x0:x0 + W]
    (sx, sy), resp = cv2.phaseCorrelate(pa.astype(np.float64), pb.astype(np.float64), hann.astype(np.float64))
    d = pb - pa
    # what a pure displacement (sx, sy) would leave, to first order
    pred = -(sx * gx[y0:y0 + W, x0:x0 + W] / 8 + sy * gy[y0:y0 + W, x0:x0 + W] / 8)
    explained = 1 - float(np.mean((d - pred) ** 2)) / float(np.mean(d * d))
    rows.append((y0, x0, sx, sy, float(np.sqrt(np.mean(d * d))), explained))
print('window origin (y, x)   displacement k1 vs lossless (px)   rms difference   share of the difference a displacement explains')
for y0, x0, sx, sy, rms, ex in rows:
    print('   %5d %5d   (%+.4f, %+.4f)   %7.2f   %5.1f %%' % (y0, x0, sx, sy, rms, 100 * ex))
sx = np.array([r[2] for r in rows])
sy = np.array([r[3] for r in rows])
print('median displacement (%+.4f, %+.4f) px; largest %.4f px over %d windows' % (np.median(sx), np.median(sy), float(np.max(np.hypot(sx, sy))), len(rows)))
