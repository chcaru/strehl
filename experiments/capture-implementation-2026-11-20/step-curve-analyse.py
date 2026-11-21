"""Detail and noise against the focus step, from step-curve.ps1's renders.

  python step-curve-analyse.py <render folder> <step of the capture> <sharp width> <crops out> <out.json>

Each render sK.tif used every K-th plane (step K x the capture's step). Against s1 (every
plane), as in compare-step-renders-2.py: gradient energy after Gaussian blurs, in 128 px
tiles; detail tiles = s1's top tenth, flat tiles = its bottom fifth; each render's flat
floor (fit against brightness) is removed from its detail energy, and a scale is read only
where s1's detail is at least ten times its floor. Detail: median, 10th and 1st percentile
over detail tiles (the low percentiles are the points that fell between planes). Noise:
flat-tile energy over s1's. Crops at s1's strongest edges, one display transform, 200 %.
"""
import json
import pathlib
import re
import sys

import cv2
import numpy as np
import tifffile

src, base_step, width = pathlib.Path(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
crops_out, out_json = pathlib.Path(sys.argv[4]), pathlib.Path(sys.argv[5])
crops_out.mkdir(parents=True, exist_ok=True)
ks = sorted(int(re.match(r's(\d+)\.tif$', p.name).group(1)) for p in src.glob('s*.tif') if re.match(r's\d+\.tif$', p.name))
T = 128
SCALES = [0.7, 1.0, 1.5, 2.5]
level, energy, imgs = {}, {}, {}
for k in ks:
    a = tifffile.imread(str(src / ('s%d.tif' % k)))[..., :3].astype(np.float32)
    g = a[..., 1]
    h, w = g.shape
    th, tw = h // T, w // T

    def tiles(e):
        return e[:th * T, :tw * T].reshape(th, T, tw, T).mean(axis=(1, 3))
    level[k] = tiles(g)
    for s in SCALES:
        b = cv2.GaussianBlur(g, (0, 0), s)
        energy[(k, s)] = tiles(cv2.Sobel(b, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(b, cv2.CV_32F, 0, 1) ** 2)
    if k == 1:
        imgs[1] = a
    del a, g
inner = np.zeros((th, tw), bool)
inner[2:-2, 2:-2] = True
ref = energy[(1, 1.5)]
order = np.sort(ref[inner])
flat = inner & (ref <= order[int(0.2 * len(order))])
detail = inner & (ref >= order[int(0.9 * len(order))])
lines = ['%s: capture step %d, sharp width %.0f; %d flat tiles, %d detail tiles of %d px' % (src.name, base_step, width, flat.sum(), detail.sum(), T)]
lines.append('every  step  width/step   scale   s1 signal/floor   detail median [p10, p1]   flat (noise) energy')
data = {'base_step': base_step, 'width': width, 'rows': []}
for k in ks:
    row = {'every': k, 'step': k * base_step, 'width_over_step': width / (k * base_step), 'scales': {}}
    for s in SCALES:
        floors = {}
        for n in (1, k):
            fit = np.polyfit(level[n][flat], energy[(n, s)][flat], 1)
            floors[n] = np.maximum(np.polyval(fit, level[n][detail]), 0)
        snr = float(np.median(energy[(1, s)][detail] / np.maximum(floors[1], 1e-30)))
        r = (energy[(k, s)][detail] - floors[k]) / np.maximum(energy[(1, s)][detail] - floors[1], 1e-30)
        fl = float(np.median(energy[(k, s)][flat] / energy[(1, s)][flat]))
        row['scales'][str(s)] = dict(snr=snr, median=float(np.median(r)), p10=float(np.percentile(r, 10)), p1=float(np.percentile(r, 1)), flat=fl)
        lines.append('%5d %5d %10.1f   %4.1f px   %8.1fx%s   %.3f [%.3f, %.3f]   %.3f' % (
            k, k * base_step, width / (k * base_step), s, snr, '' if snr >= 10 else ' (noise-limited)', np.median(r),
            np.percentile(r, 10), np.percentile(r, 1), fl))
    data['rows'].append(row)
print('\n'.join(lines), flush=True)


def show(a, scale):
    v = np.clip(a * scale, 0, 1) ** (1 / 2.2)
    return (v[..., ::-1] * 255 + 0.5).astype(np.uint8)


picks = []
e1 = energy[(1, 1.0)]
for i in np.argsort(-np.where(inner, e1, 0).ravel()):
    ty, tx = divmod(int(i), tw)
    if all(abs(ty - py) > 6 or abs(tx - px) > 6 for py, px in picks):
        picks.append((ty, tx))
    if len(picks) == 3:
        break
C = 160
lines.append('crops at s1\'s strongest edges, %d px square, 200 %% nearest neighbour, left to right: every %s plane(s)' % (C, ', '.join(map(str, ks))))
boxes = []
for ty, tx in picks:
    g = imgs[1][ty * T:(ty + 1) * T, tx * T:(tx + 1) * T, 1]
    b = cv2.GaussianBlur(g, (0, 0), 1.0)
    e = cv2.Sobel(b, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(b, cv2.CV_32F, 0, 1) ** 2
    cy, cx = np.unravel_index(np.argmax(cv2.GaussianBlur(e, (0, 0), 8)), e.shape)
    y0 = int(np.clip(ty * T + cy - C // 2, 0, imgs[1].shape[0] - C))
    x0 = int(np.clip(tx * T + cx - C // 2, 0, imgs[1].shape[1] - C))
    scale = 0.9 / max(1e-9, float(np.percentile(imgs[1][y0:y0 + C, x0:x0 + C], 99.5)))
    boxes.append((y0, x0, scale, []))
del imgs
for k in ks:
    a = tifffile.imread(str(src / ('s%d.tif' % k)))[..., :3]
    for y0, x0, scale, panels in boxes:
        v = cv2.resize(show(a[y0:y0 + C, x0:x0 + C].astype(np.float32), scale), (2 * C, 2 * C), interpolation=cv2.INTER_NEAREST)
        v = cv2.copyMakeBorder(v, 28, 0, 0, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(v, 'step %d' % (k * base_step), (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        panels.append(v)
    del a
for j, (y0, x0, scale, panels) in enumerate(boxes):
    path = crops_out / ('step-%s-edge-%d-y%d-x%d.png' % (src.name, j, y0, x0))
    cv2.imwrite(str(path), np.concatenate(panels, axis=1))
    lines.append('   %s: origin y=%d x=%d' % (path.name, y0, x0))
out_json.write_text(json.dumps(data, indent=1) + '\n')
pathlib.Path(str(out_json).replace('.json', '.txt')).write_text('\n'.join(lines) + '\n')
print('\n'.join(lines[-4:]))
