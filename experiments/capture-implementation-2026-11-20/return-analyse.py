"""Decision D5: is a plane revisited later the same plane?

  python -X faulthandler return-analyse.py <folder of NAME-M.ARW from l11-return>

Exposure 1 of each group, green, on the frame's most detailed 1536 px window:
  - a1 against a2 (taken twice at A without a move): what the measures read for the same plane;
  - a1 against c1r, c2r, c3r (A again after three planes forward and the approach back): the
    question;
  - a1 against c1f1 (8 units on): what one plane away reads, for scale.
Measures: phase-correlation shift (px) and the ratio of gradient energy (sharpness) after a
1 px blur. Control first: a planted 0.3 px shift of a2 must read 0.3 px.
"""
import pathlib
import sys

import cv2
import numpy as np
import rawpy

folder = pathlib.Path(sys.argv[1])
SIZE = 1536


def green(path):
    with rawpy.imread(str(path)) as raw:
        img = raw.raw_image_visible.copy()  # copy inside the context
        black = float(np.mean(raw.black_level_per_channel))
    return cv2.cvtColor(img, cv2.COLOR_BAYER_RG2GRAY).astype(np.float32) - black


frames = {p.stem.rsplit('-', 1)[0]: green(p) for p in sorted(folder.glob('*-1.ARW'))}
ref = frames['a1']
h, w = ref.shape
small = cv2.resize(ref, (w // 16, h // 16), interpolation=cv2.INTER_AREA)
e = cv2.boxFilter(cv2.Sobel(small, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(small, cv2.CV_32F, 0, 1) ** 2, -1, (SIZE // 16, SIZE // 16), normalize=True, anchor=(0, 0))
valid = np.zeros_like(e, bool)
valid[:(h - SIZE) // 16, :(w - SIZE) // 16] = True
iy, ix = np.unravel_index(np.argmax(np.where(valid, e, -1)), e.shape)
y0, x0 = int(iy) * 16, int(ix) * 16
hann = cv2.createHanningWindow((SIZE, SIZE), cv2.CV_64F)


def win(img):
    return img[y0:y0 + SIZE, x0:x0 + SIZE].astype(np.float64)


def sharp(img):
    b = cv2.GaussianBlur(win(img), (0, 0), 1.0)
    return float(np.mean(cv2.Sobel(b, cv2.CV_64F, 1, 0) ** 2 + cv2.Sobel(b, cv2.CV_64F, 0, 1) ** 2))


def compare(a, b):
    (sx, sy), resp = cv2.phaseCorrelate(win(a), win(b), hann)
    return float(np.hypot(sx, sy)), sx, sy, sharp(b) / sharp(a), resp


print('window y=%d x=%d, %d px square (most detailed part of a1)' % (y0, x0, SIZE))
m = np.float32([[1, 0, 0.3], [0, 1, 0.0]])
planted = cv2.warpAffine(frames['a2'], m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
d, sx, sy, s, _ = compare(frames['a2'], planted)
print('control: a2 against a2 shifted 0.300 px reads %.3f px (%+.3f, %+.3f)' % (d, sx, sy))
print('pair            shift px  (dx, dy)            sharpness ratio')
for name in ['a2', 'c1r', 'c2r', 'c3r', 'c1f1', 'c1f3']:
    if name not in frames:
        continue
    d, sx, sy, s, resp = compare(ref, frames[name])
    label = {'a2': 'same plane, no move', 'c1f1': 'one plane on (8 units)', 'c1f3': 'three planes on'}.get(name, 'revisited')
    print('a1 vs %-5s %8.3f   (%+.3f, %+.3f)   %.4f   %s' % (name, d, sx, sy, s, label))
