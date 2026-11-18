"""R10: colour of the rim that bright detail leaves on dark ground, by channel
and distance.

  python -X utf8 rim-colour.py OUT.json MASK.tif IMG.tif [IMG.tif ...]

MASK.tif defines the classes and should not be one of the scored images
(halo-distance.py's rule). Green smoothed at 1 px: bright above 50 % of the
99.5th percentile, dark below 12 %. Dark pixels are binned by distance to
the nearest bright pixel.

Per scored image, channel and bin: the mean level of the dark pixels as a
percentage of that channel's bright level (the images are white-balanced, so
a neutral rim reads the same in all three). Reported: that percentage for
green, and red and blue as differences from green (percentage points of the
bright level): a purple rim is red and blue above green near the edge.

Also by side: dark pixels 3.5-10 px from bright detail, split by where
their nearest bright pixel lies (above, below, left, right). A channel
displaced against green makes the rim differ between opposite sides; a
channel that is only softer than green makes it the same on every side.

The far bin (100 px and beyond) is the ground's own colour; the rim's colour
is the excess over it.

Fooled by: a ground that is itself coloured near bright scales (shadowed
cuticle, translucent scale edges); the mask's threshold; a channel that is
softer everywhere (its rim is wider but neutral in sum).
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, gaussian_filter

out = Path(sys.argv[1])
g = gaussian_filter(tifffile.imread(sys.argv[2])[..., 1].astype(np.float32), 1.0)
top = np.percentile(g, 99.5)
dark, bright = g < 0.12 * top, g > 0.50 * top
dist, (iy, ix) = distance_transform_edt(~bright, return_indices=True)
edges = [1.5, 2.5, 3.5, 5, 7, 10, 15, 30, 100, 100000]
bins = [dark & (dist >= lo) & (dist < hi) for lo, hi in zip(edges[:-1], edges[1:])]
labels = [f'{lo:g}-{hi:g}' if hi < 100000 else f'{lo:g}+' for lo, hi in zip(edges[:-1], edges[1:])]
H, W = g.shape
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
rad = np.hypot(xx - (W - 1) / 2, yy - (H - 1) / 2) / np.hypot(W / 2, H / 2)
del yy, xx
ZONES = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
near = dark & (dist >= 3.5) & (dist < 10)
# direction from each dark pixel to its nearest bright pixel: a channel displaced against green makes the rim
# differ between opposite sides of bright detail; a channel that is only softer makes it the same on all sides
yy, xx = np.mgrid[0:H, 0:W].astype(np.int32)
dy, dx = (iy - yy).astype(np.float32), (ix - xx).astype(np.float32)
del yy, xx, iy, ix
SIDES = {'bright above': near & (dy < 0) & (np.abs(dy) > np.abs(dx)), 'bright below': near & (dy > 0) & (np.abs(dy) > np.abs(dx)),
         'bright left': near & (dx < 0) & (np.abs(dx) > np.abs(dy)), 'bright right': near & (dx > 0) & (np.abs(dx) > np.abs(dy))}
del dy, dx
far = dark & (dist >= 100)
print('dark px per bin: ' + ', '.join(f'{l}: {int(b.sum())}' for l, b in zip(labels, bins)))
report = {'mask': sys.argv[2], 'bins_px': labels, 'images': {}}
print(f'{"":34s}' + ' '.join(f'{l:>8s}' for l in labels))
for p in sys.argv[3:]:
    img = tifffile.imread(p)
    br = np.array([float(img[..., c][bright].mean()) for c in range(3)])
    lv = np.array([[float(img[..., c][b].mean()) for b in bins] for c in range(3)])
    pct = 100 * lv / br[:, None]
    name = Path(p).name[:30]
    rim = pct - pct[:, -1:]
    report['images'][Path(p).name] = {'bright': br.tolist(), 'dark_pct_of_bright': pct.tolist()}
    print(f'{name:30s} G % ' + ' '.join(f'{v:8.2f}' for v in pct[1]))
    print(f'{"":30s} R-G ' + ' '.join(f'{v:+8.2f}' for v in pct[0] - pct[1]))
    print(f'{"":30s} B-G ' + ' '.join(f'{v:+8.2f}' for v in pct[2] - pct[1]))
    print(f'{"":30s} rim excess over the far ground, R / G / B at the first three bins: '
          + '  '.join(f'{rim[0, i]:.2f}/{rim[1, i]:.2f}/{rim[2, i]:.2f}' for i in range(3)))
    # by radius zone (share of the half diagonal), dark pixels 3.5-10 px from bright: a rim made by lateral
    # colour inside a channel's passband grows with radius; one made by the optics' on-axis blur does not
    zrows = []
    for zlo, zhi in ZONES:
        zm = near & (rad >= zlo) & (rad < zhi)
        zb = bright & (rad >= zlo) & (rad < zhi)
        if zm.sum() < 2000 or zb.sum() < 2000:
            continue
        zbr = np.array([float(img[..., c][zb].mean()) for c in range(3)])
        zl = 100 * np.array([float(img[..., c][zm].mean()) for c in range(3)]) / zbr
        zf = far & (rad >= zlo) & (rad < zhi)
        zfar = 100 * np.array([float(img[..., c][zf].mean()) for c in range(3)]) / zbr if zf.sum() > 2000 else np.full(3, np.nan)
        zrows.append({'zone': [zlo, zhi], 'pixels': int(zm.sum()), 'near_pct': zl.tolist(), 'far_pct': zfar.tolist()})
        print(f'{"":30s} radius {zlo:.2f}-{zhi:.2f}: {int(zm.sum()):8d} px 3.5-10 px from bright: G {zl[1]:.2f} %, R-G {zl[0] - zl[1]:+.2f}, B-G {zl[2] - zl[1]:+.2f}'
              f'  (far ground R-G {zfar[0] - zfar[1]:+.2f}, B-G {zfar[2] - zfar[1]:+.2f})')
    report['images'][Path(p).name]['zones'] = zrows
    side = {}
    for sname, sm in SIDES.items():
        v = 100 * np.array([float(img[..., c][sm].mean()) for c in range(3)]) / br
        side[sname] = v.tolist()
    report['images'][Path(p).name]['sides'] = side
    print(f'{"":30s} by side, 3.5-10 px (R-G, B-G): ' + ';  '.join(f'{k}: {v[0] - v[1]:+.2f}, {v[2] - v[1]:+.2f}' for k, v in side.items()))
    print(f'{"":30s} opposite-side differences: R-G vertical {side["bright above"][0] - side["bright above"][1] - side["bright below"][0] + side["bright below"][1]:+.2f}, '
          f'horizontal {side["bright left"][0] - side["bright left"][1] - side["bright right"][0] + side["bright right"][1]:+.2f};  '
          f'B-G vertical {side["bright above"][2] - side["bright above"][1] - side["bright below"][2] + side["bright below"][1]:+.2f}, '
          f'horizontal {side["bright left"][2] - side["bright left"][1] - side["bright right"][2] + side["bright right"][1]:+.2f}')
    del img
out.write_text(json.dumps(report, indent=1) + '\n')
