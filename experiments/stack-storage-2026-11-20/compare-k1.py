"""What does the calibrated (k = 1) tier do to a finished render?

  python compare-k1.py <folder with lossless.tif and k1.tif> <crops out folder>

Both files are the product's linear float render of the first 24 scarab planes: one from the
lossless archives, one from the copies whose CFA samples were requantised with a step of one
noise sigma (quant.py, s7). Order of evidence:
  1. flat tiles first: gradient energy there is noise, so its ratio is the noise change
     (prediction: variance up by at most k^2/12 = 8.3 %, amplitude 4.1 %);
  2. levels: mean of each channel (a quantiser bias would show as an offset);
  3. detail tiles (top tenth by gradient energy), floor removed: the ratio should stay 1;
  4. the difference image itself: its size against the render's own noise, and whether it
     carries the picture (correlation of the difference with the image's local contrast);
  5. crops at 200 %: lossless, k = 1, and their difference amplified 16x about mid grey.
"""
import pathlib
import sys

import cv2
import numpy as np
import tifffile

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
a = tifffile.imread(str(src / 'lossless.tif'))[..., :3].astype(np.float32)
b = tifffile.imread(str(src / 'k1.tif'))[..., :3].astype(np.float32)
T = 128
h, w = a.shape[:2]
th, tw = h // T, w // T


def tiles(e):
    return e[:th * T, :tw * T].reshape(th, T, tw, T).mean(axis=(1, 3))


def grad(img, s):
    g = cv2.GaussianBlur(img, (0, 0), s) if s > 0 else img
    return cv2.Sobel(g, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(g, cv2.CV_32F, 0, 1) ** 2


ga, gb = a[..., 1], b[..., 1]
inner = np.zeros((th, tw), bool)
inner[2:-2, 2:-2] = True
ref = tiles(grad(ga, 1.5))
order = np.sort(ref[inner])
flat = inner & (ref <= order[int(0.2 * len(order))])
detail = inner & (ref >= order[int(0.9 * len(order))])
level_a, level_b = tiles(ga), tiles(gb)
print('render %dx%d; %d flat tiles, %d detail tiles of %d px' % (w, h, flat.sum(), detail.sum(), T))

print('\n1. flat tiles: gradient energy of the k = 1 render over the lossless render (noise change)')
for s in (0.0, 0.5, 1.0, 1.5, 2.5):
    ea, eb = tiles(grad(ga, s)), tiles(grad(gb, s))
    r = eb[flat] / ea[flat]
    print('   blur %.1f px: median %.4f (amplitude %.4f), 10th-90th percentile %.4f-%.4f' % (
        s, np.median(r), np.sqrt(np.median(r)), np.percentile(r, 10), np.percentile(r, 90)))

print('\n2. levels: channel means, k = 1 minus lossless')
for c, name in enumerate('RGB'):
    ma, mb = float(a[..., c].mean()), float(b[..., c].mean())
    print('   %s: lossless %.3f, k = 1 %.3f, difference %+.4f (%+.2e of the level)' % (name, ma, mb, mb - ma, (mb - ma) / ma))

print('\n3. detail tiles: gradient energy over the lossless render, each render\'s own flat-tile floor removed')
for s in (0.5, 1.0, 1.5, 2.5):
    ea, eb = tiles(grad(ga, s)), tiles(grad(gb, s))
    fa = np.maximum(np.polyval(np.polyfit(level_a[flat], ea[flat], 1), level_a[detail]), 0)
    fb = np.maximum(np.polyval(np.polyfit(level_b[flat], eb[flat], 1), level_b[detail]), 0)
    r = (eb[detail] - fb) / np.maximum(ea[detail] - fa, 1e-30)
    print('   blur %.1f px: median %.4f, 10th percentile %.4f, 1st percentile %.4f (signal/floor %.0fx)' % (
        s, np.median(r), np.percentile(r, 10), np.percentile(r, 1), np.median(ea[detail] / np.maximum(fa, 1e-30))))

print('\n4. the difference image (green)')
d = gb - ga
# the render's own noise: high-pass residual of the lossless render in flat tiles
hp = ga - cv2.GaussianBlur(ga, (0, 0), 2.0)
noise_tiles = np.sqrt(tiles(hp * hp))
diff_tiles = np.sqrt(tiles(d * d))
print('   rms difference %.3f; lossless render\'s own high-pass rms in flat tiles %.3f; ratio in flat tiles: median %.3f' % (
    float(np.sqrt(np.mean(d * d))), float(np.median(noise_tiles[flat])), float(np.median(diff_tiles[flat] / noise_tiles[flat]))))
print('   rms difference in detail tiles over flat tiles at the same brightness: %.3f (1 = no extra error where there is detail)' % (
    float(np.median(diff_tiles[detail]) / np.median(np.polyval(np.polyfit(level_a[flat], diff_tiles[flat], 1), level_a[detail])))))
contrast = np.sqrt(grad(ga, 1.0))
dd = np.abs(d)
cc = np.corrcoef(contrast[::7, ::7].ravel(), dd[::7, ::7].ravel())[0, 1]
lv = np.corrcoef(ga[::7, ::7].ravel(), dd[::7, ::7].ravel())[0, 1]
print('   correlation of |difference| with local contrast %.3f, with brightness %.3f (noise grows with brightness; contrast should add nothing)' % (cc, lv))
print('   largest |difference| %.1f against a white level of %.0f' % (float(dd.max()), float(ga.max())))


def show(img, scale):
    v = np.clip(img * scale, 0, 1) ** (1 / 2.2)
    return (v[..., ::-1] * 255 + 0.5).astype(np.uint8)


print('\n5. crops, 200 % nearest neighbour: lossless | k = 1 | difference x16 about mid grey')
picks = []
e1 = tiles(grad(ga, 1.0))
for i in np.argsort(-np.where(inner, e1, 0).ravel()):
    ty, tx = divmod(int(i), tw)
    if all(abs(ty - py) > 6 or abs(tx - px) > 6 for py, px in picks):
        picks.append((ty, tx))
    if len(picks) == 3:
        break
fy, fx = np.argwhere(flat & (level_a > np.median(level_a[flat])))[0]
picks.append((int(fy), int(fx)))
C = 160
for k, (ty, tx) in enumerate(picks):
    y0, x0 = ty * T, tx * T
    ca, cb = a[y0:y0 + C, x0:x0 + C], b[y0:y0 + C, x0:x0 + C]
    scale = 0.9 / max(1e-9, float(np.percentile(ca, 99.5)))
    diff = np.clip(0.5 + 16 * (cb - ca) * scale, 0, 1)
    panels = [show(ca, scale), show(cb, scale), (diff[..., ::-1] * 255 + 0.5).astype(np.uint8)]
    strip = np.concatenate([cv2.resize(p, (2 * C, 2 * C), interpolation=cv2.INTER_NEAREST) for p in panels], axis=1)
    name = 'k1-%d-%s-y%d-x%d.png' % (k, 'flat' if k == len(picks) - 1 else 'edge', y0, x0)
    cv2.imwrite(str(out / name), strip)
    print('   %s: origin y=%d x=%d, %d px square' % (name, y0, x0, C))
