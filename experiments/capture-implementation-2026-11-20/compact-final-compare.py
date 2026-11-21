"""Viewable copies of the two final images from compare-compact.ps1, and how far apart they are.

  python compact-final-compare.py <folder with lossless.tiff and compacted.tiff>

Writes, next to them: lossless.jpg and compacted.jpg (full size, quality 95), side-by-side
crops at 200 % nearest neighbour (lossless | compacted | difference x16 about mid grey) at the
strongest detail and in a flat area, and the difference statistics in 8-bit display steps.
"""
import pathlib
import sys

import cv2
import numpy as np
import tifffile

d = pathlib.Path(sys.argv[1])
a = tifffile.imread(str(d / 'lossless.tiff'))[..., :3]
b = tifffile.imread(str(d / 'compacted.tiff'))[..., :3]
assert a.shape == b.shape and a.dtype == b.dtype, (a.shape, b.shape, a.dtype, b.dtype)
full = 65535.0 if a.dtype == np.uint16 else 255.0
lines = ['%dx%d, %s' % (a.shape[1], a.shape[0], a.dtype)]
diff = (a.astype(np.float32) - b.astype(np.float32)) * (255.0 / full)
ad = np.abs(diff)
lines.append('difference in 8-bit display steps (0-255): mean %.3f, 99th percentile %.2f, 99.99th %.2f, max %.1f' % (
    ad.mean(), np.percentile(ad, 99), np.percentile(ad, 99.99), ad.max()))
lines.append('pixels differing by 1 step or more: %.2f %%; by 3 or more: %.4f %%' % (100 * (ad.max(axis=2) >= 1).mean(), 100 * (ad.max(axis=2) >= 3).mean()))
a8 = np.clip(a.astype(np.float32) * (255.0 / full) + 0.5, 0, 255).astype(np.uint8)
b8 = np.clip(b.astype(np.float32) * (255.0 / full) + 0.5, 0, 255).astype(np.uint8)
lines.append('8-bit images identical at %.2f %% of pixels' % (100 * (a8 == b8).all(axis=2).mean()))
cv2.imwrite(str(d / 'lossless.jpg'), a8[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 95])
cv2.imwrite(str(d / 'compacted.jpg'), b8[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 95])

g = a8[..., 1].astype(np.float32)
T = 128
h, w = g.shape
s = cv2.GaussianBlur(g, (0, 0), 1.0)
e = cv2.Sobel(s, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(s, cv2.CV_32F, 0, 1) ** 2
et = e[:h // T * T, :w // T * T].reshape(h // T, T, w // T, T).mean(axis=(1, 3))
inner = np.zeros_like(et, bool)
inner[2:-2, 2:-2] = True
picks = []
for i in np.argsort(-np.where(inner, et, 0).ravel()):
    ty, tx = divmod(int(i), et.shape[1])
    if all(abs(ty - py) > 8 or abs(tx - px) > 8 for _, py, px in picks):
        picks.append(('detail', ty, tx))
    if len(picks) == 3:
        break
lt = g[:h // T * T, :w // T * T].reshape(h // T, T, w // T, T).mean(axis=(1, 3))
flat = np.where(inner & (lt > 40), et, np.inf)
ty, tx = divmod(int(np.argmin(flat)), et.shape[1])
picks.append(('flat', ty, tx))
C = 256
lines.append('crops, %d px square at 200 %% nearest neighbour: lossless | compacted | difference x16 about mid grey' % C)
for k, (kind, ty, tx) in enumerate(picks):
    y0 = int(np.clip(ty * T + T // 2 - C // 2, 0, h - C))
    x0 = int(np.clip(tx * T + T // 2 - C // 2, 0, w - C))
    ca, cb = a8[y0:y0 + C, x0:x0 + C], b8[y0:y0 + C, x0:x0 + C]
    cd = np.clip(128 + 16 * diff[y0:y0 + C, x0:x0 + C], 0, 255).astype(np.uint8)
    panels = []
    for name, p in (('lossless', ca), ('compacted', cb), ('difference x16', cd)):
        v = cv2.resize(p[..., ::-1], (2 * C, 2 * C), interpolation=cv2.INTER_NEAREST)
        v = cv2.copyMakeBorder(v, 30, 0, 0, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(v, name, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1, cv2.LINE_AA)
        panels.append(v)
    name = 'crop-%d-%s-y%d-x%d.png' % (k, kind, y0, x0)
    cv2.imwrite(str(d / name), np.concatenate(panels, axis=1))
    lines.append('   %s: origin y=%d x=%d' % (name, y0, x0))
(d / 'compare.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
