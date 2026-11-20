"""What does a coarser focus step cost in the finished photograph?

  python compare-step-renders.py <folder with full.tif, s2.tif, s4.tif> <crops out folder>

The three files are the product's linear float renders of the same capture from all planes,
every second and every fourth plane. Per 128 px tile the script takes two measures of detail
in the green channel (fine: unblurred 4-neighbour Laplacian energy; mid: gradient energy after
a 1.5 px blur) and reports each subset's measure relative to the full stack's.

Order of evidence: (1) flat tiles first: there the measures are noise, and a subset's ratio
says how the noise changed, not the detail; (2) detail tiles (the full render's top fifth by
fine energy, well above the flat level), with the flat-tile energy at the same brightness
subtracted; (3) the worst detail tiles, saved as crops at 100 % with one display transform for
all three renders. Gradient energy cannot by itself establish quality (noise and ringing
raise it): the crops are the check, the numbers say where to look.
"""
import pathlib
import sys

import cv2
import numpy as np
import tifffile

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
names = ['full', 's2', 's4']
T = 128
lap = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], np.float32)
img, fine, mid, level = {}, {}, {}, {}
for n in names:
    a = tifffile.imread(str(src / (n + '.tif')))
    if a.ndim == 3 and a.shape[0] in (3, 4) and a.shape[2] > 4:
        a = np.moveaxis(a, 0, 2)
    a = a[..., :3].astype(np.float32)
    img[n] = a
    g = a[..., 1]
    h, w = g.shape
    th, tw = h // T, w // T
    l = cv2.filter2D(g, cv2.CV_32F, lap)
    s = cv2.GaussianBlur(g, (0, 0), 1.5)
    gx = cv2.Sobel(s, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(s, cv2.CV_32F, 0, 1)

    def tiles(e):
        return e[:th * T, :tw * T].reshape(th, T, tw, T).mean(axis=(1, 3))
    fine[n], mid[n], level[n] = tiles(l * l), tiles(gx * gx + gy * gy), tiles(g)
    print('%s: %s %s, green mean %.5f, min %.5f, max %.5f' % (n, a.shape, a.dtype, g.mean(), g.min(), g.max()))
th, tw = fine['full'].shape
# keep away from the frame border, where coverage differs between solves
inner = np.zeros((th, tw), bool)
inner[2:-2, 2:-2] = True
f0 = fine['full']
order = np.sort(f0[inner])
flat_cut = order[int(0.2 * len(order))]
detail_cut = order[int(0.8 * len(order))]
flat = inner & (f0 <= flat_cut)
detail = inner & (f0 >= detail_cut)
print('\n%d x %d tiles of %d px; flat tiles: %d (fine energy <= %.3g), detail tiles: %d (>= %.3g, %.0fx the flat median)' % (
    tw, th, T, flat.sum(), flat_cut, detail.sum(), detail_cut, detail_cut / np.median(f0[flat])))

print('\n1. flat tiles (noise): energy relative to the full stack, median over tiles')
for n in names[1:]:
    print('   %s: fine %.3f, mid %.3f   (1.0 = the full stack\'s noise; sqrt of it is the amplitude ratio)' % (
        n, np.median(fine[n][flat] / fine['full'][flat]), np.median(mid[n][flat] / mid['full'][flat])))


def floor_fit(n, measure):
    # noise energy against brightness, from the flat tiles (a line through them)
    x, y = level[n][flat], measure[n][flat]
    k = np.polyfit(x, y, 1)
    return lambda lv: np.maximum(np.polyval(k, lv), 0)


print('\n2. detail tiles: detail energy (noise floor at the tile\'s brightness removed) relative to the full stack')
worst = {}
for n in names[1:]:
    for label, measure in (('fine', fine), ('mid', mid)):
        num = measure[n][detail] - floor_fit(n, measure)(level[n][detail])
        den = measure['full'][detail] - floor_fit('full', measure)(level['full'][detail])
        r = num / np.maximum(den, 1e-30)
        print('   %s %s: median %.3f, 10th percentile %.3f, 1st percentile %.3f, share of tiles below 0.90: %.1f %%  (amplitude = sqrt: median %.3f)' % (
            n, label, np.median(r), np.percentile(r, 10), np.percentile(r, 1), 100 * np.mean(r < 0.9), np.sqrt(np.median(r))))
        if label == 'fine':
            full = np.full((th, tw), np.inf)
            full[detail] = r
            worst[n] = full


def show(a, scale):
    v = np.clip(a * scale, 0, 1) ** (1 / 2.2)
    return (v[..., ::-1] * 255 + 0.5).astype(np.uint8)


print('\n3. crops (100 %, one display transform; left to right: full, every 2nd plane, every 4th plane)')
picks = []
flatidx = np.argsort(worst['s4'].ravel())
for i in flatidx:
    ty, tx = divmod(int(i), tw)
    if all(abs(ty - py) > 3 or abs(tx - px) > 3 for py, px, _ in picks):
        picks.append((ty, tx, 'worst-s4'))
    if len(picks) == 3:
        break
med = np.argsort(np.abs(worst['s4'].ravel() - np.median(worst['s4'][detail])))
for i in med:
    ty, tx = divmod(int(i), tw)
    if all(abs(ty - py) > 3 or abs(tx - px) > 3 for py, px, _ in picks):
        picks.append((ty, tx, 'median-s4'))
        break
fy, fx = np.argwhere(flat)[len(np.argwhere(flat)) // 2]
picks.append((int(fy), int(fx), 'flat'))
C = 320
for k, (ty, tx, why) in enumerate(picks):
    y0 = int(np.clip(ty * T + T // 2 - C // 2, 0, img['full'].shape[0] - C))
    x0 = int(np.clip(tx * T + T // 2 - C // 2, 0, img['full'].shape[1] - C))
    crop = {n: img[n][y0:y0 + C, x0:x0 + C] for n in names}
    scale = 0.9 / max(1e-9, float(np.percentile(crop['full'], 99.5)))
    strip = np.concatenate([show(crop[n], scale) for n in names], axis=1)
    path = out / ('crop-%d-%s-y%d-x%d.png' % (k, why, y0, x0))
    cv2.imwrite(str(path), strip)
    print('   %s: origin y=%d x=%d, %d px square each; fine ratio s2 %.3f, s4 %.3f' % (
        path.name, y0, x0, C, worst['s2'][ty, tx] if np.isfinite(worst['s2'][ty, tx]) else float('nan'),
        worst['s4'][ty, tx] if np.isfinite(worst['s4'][ty, tx]) else float('nan')))
