"""Second look at the coarser-step renders, separating detail from selection noise.

  python compare-step-renders-2.py <folder with full.tif, s2.tif, s4.tif> <crops out folder>

The first comparison found the unblurred fine-band energy falling by the same factor in flat
tiles and in detail tiles, which is what noise does (a selecting merge picks the largest of N
noisy coefficients, so fewer planes means less selected noise), not what defocus does. Here
gradient energy is taken after Gaussian blurs of 0.5, 0.7, 1.0, 1.5 and 2.5 px, and a scale
is only read where the detail tiles' energy is at least ten times the flat tiles' at the same
brightness (signal-dominated). Crops are taken at the strongest edges and shown at 200 %
(nearest neighbour), one display transform for all three renders.
"""
import pathlib
import sys

import cv2
import numpy as np
import tifffile

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
names = sys.argv[3].split(',') if len(sys.argv) > 3 else ['full', 's2', 's4']
T = 128
SCALES = [0.5, 0.7, 1.0, 1.5, 2.5]
img, level, energy = {}, {}, {}
for n in names:
    a = tifffile.imread(str(src / (n + '.tif')))[..., :3].astype(np.float32)
    img[n] = a
    g = a[..., 1]
    h, w = g.shape
    th, tw = h // T, w // T

    def tiles(e):
        return e[:th * T, :tw * T].reshape(th, T, tw, T).mean(axis=(1, 3))
    level[n] = tiles(g)
    for s in SCALES:
        b = cv2.GaussianBlur(g, (0, 0), s)
        gx = cv2.Sobel(b, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(b, cv2.CV_32F, 0, 1)
        energy[(n, s)] = tiles(gx * gx + gy * gy)
inner = np.zeros((th, tw), bool)
inner[2:-2, 2:-2] = True
ref = energy[('full', 1.5)]
order = np.sort(ref[inner])
flat = inner & (ref <= order[int(0.2 * len(order))])
detail = inner & (ref >= order[int(0.9 * len(order))])
print('%d flat tiles, %d detail tiles (the full render\'s top tenth by 1.5 px gradient energy)' % (flat.sum(), detail.sum()))
print('\nscale   signal/noise in detail tiles (full)   flat-tile energy vs full: s2, s4   detail energy vs full (floor removed): s2 median [p10], s4 median [p10]   amplitude s2, s4')
for s in SCALES:
    floors = {}
    for n in names:
        k = np.polyfit(level[n][flat], energy[(n, s)][flat], 1)
        floors[n] = np.maximum(np.polyval(k, level[n][detail]), 0)
    snr = np.median(energy[('full', s)][detail] / np.maximum(floors['full'], 1e-30))
    row = []
    for n in names[1:]:
        r = (energy[(n, s)][detail] - floors[n]) / np.maximum(energy[('full', s)][detail] - floors['full'], 1e-30)
        row.append((np.median(r), np.percentile(r, 10)))
    fl = [np.median(energy[(n, s)][flat] / energy[('full', s)][flat]) for n in names[1:]]
    print('%.1f px   %6.1fx%s   ' % (s, snr, '' if snr >= 10 else ' (noise-limited: do not read)') + '   '.join('%s: flat %.3f detail %.3f [p10 %.3f] amplitude %.3f' % (n, f, r[0], r[1], np.sqrt(r[0])) for n, f, r in zip(names[1:], fl, row)))


def show(a, scale):
    v = np.clip(a * scale, 0, 1) ** (1 / 2.2)
    return (v[..., ::-1] * 255 + 0.5).astype(np.uint8)


print('\ncrops at the strongest edges, 200 % nearest neighbour (left to right: full, every 2nd plane, every 4th plane)')
picks = []
for i in np.argsort(-np.where(inner, energy[('full', 1.0)], 0).ravel()):
    ty, tx = divmod(int(i), tw)
    if all(abs(ty - py) > 6 or abs(tx - px) > 6 for py, px in picks):
        picks.append((ty, tx))
    if len(picks) == 4:
        break
C = 160
for k, (ty, tx) in enumerate(picks):
    # centre the crop on the strongest gradient inside the tile
    g = img['full'][ty * T:(ty + 1) * T, tx * T:(tx + 1) * T, 1]
    b = cv2.GaussianBlur(g, (0, 0), 1.0)
    e = cv2.Sobel(b, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(b, cv2.CV_32F, 0, 1) ** 2
    cy, cx = np.unravel_index(np.argmax(cv2.GaussianBlur(e, (0, 0), 8)), e.shape)
    y0 = int(np.clip(ty * T + cy - C // 2, 0, img['full'].shape[0] - C))
    x0 = int(np.clip(tx * T + cx - C // 2, 0, img['full'].shape[1] - C))
    crop = {n: img[n][y0:y0 + C, x0:x0 + C] for n in names}
    scale = 0.9 / max(1e-9, float(np.percentile(crop['full'], 99.5)))
    strip = np.concatenate([cv2.resize(show(crop[n], scale), (2 * C, 2 * C), interpolation=cv2.INTER_NEAREST) for n in names], axis=1)
    path = out / ('edge-%d-y%d-x%d.png' % (k, y0, x0))
    cv2.imwrite(str(path), strip)
    print('   %s: origin y=%d x=%d, %d px square each, shown at 200 %%' % (path.name, y0, x0, C))
