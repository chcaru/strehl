"""Is the edge-shaped difference between the lossless and compacted renders a placement shift?
Phase correlation of the two renders' green channel in 1024 px windows over the frame.
  python compact-shift.py <folder with lossless.tiff and compacted.tiff>"""
import pathlib
import sys

import cv2
import numpy as np
import tifffile

d = pathlib.Path(sys.argv[1])
a = tifffile.imread(str(d / 'lossless.tiff'))[..., 1].astype(np.float32)
b = tifffile.imread(str(d / 'compacted.tiff'))[..., 1].astype(np.float32)
W = 1024
win = cv2.createHanningWindow((W, W), cv2.CV_32F)
rows = []
for y in range(256, a.shape[0] - W - 255, W):
    for x in range(256, a.shape[1] - W - 255, W):
        (dx, dy), r = cv2.phaseCorrelate(a[y:y + W, x:x + W], b[y:y + W, x:x + W], win)
        rows.append((y, x, dx, dy, r))
r = np.array(rows)
good = r[:, 4] > 0.3
print('%d windows of %d px, %d with a clear peak' % (len(r), W, good.sum()))
print('shift compacted vs lossless (px): dx median %.4f (range %.4f..%.4f), dy median %.4f (range %.4f..%.4f)' % (
    np.median(r[good, 2]), r[good, 2].min(), r[good, 2].max(), np.median(r[good, 3]), r[good, 3].min(), r[good, 3].max()))
for y, x, dx, dy, q in rows:
    print('   y %5d x %5d  dx %+.4f dy %+.4f  peak %.2f' % (y, x, dx, dy, q))
