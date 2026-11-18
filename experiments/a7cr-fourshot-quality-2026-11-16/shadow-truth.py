"""Q4: which merge has the right shadow level? Each arm against one in-focus
frame.

  python -X utf8 shadow-truth.py OUT.json FRAME.tif MASK.tif ARM.tif [ARM.tif ...]

FRAME.tif: one frame of the stack rendered alone (no cross-frame averaging:
its shadows hold only that frame's own optical spill). MASK.tif: a merge
that does not contain the scored noise (the other half-stack), used for the
pixel classes. ARM.tif: merges that include FRAME's focus position.

Region: dark pixels whose bright surroundings are in focus in FRAME (a dark
pixel has no focus evidence of its own): FRAME's local fine energy (green,
|x - gauss 2 px|^2 smoothed at 12 px) at least 0.7 of the mask merge's on at
least 85 % of the bright pixels within a 20 px Gaussian. Classes from the mask (green, 2 px): bright above 50 % of the
99.5th percentile, dark below 12 %, binned by distance to the nearest
bright pixel. Per arm and bin: mean(arm) / mean(FRAME) over dark in-focus
pixels. One means the merge's shadows are as dark as the in-focus frame's.

Control: a neighbouring single frame scored the same way (it differs from
FRAME only by noise, exposure drift and one focus step).
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, gaussian_filter

out = Path(sys.argv[1])
frame = tifffile.imread(sys.argv[2]).astype(np.float32)
mask_img = tifffile.imread(sys.argv[3]).astype(np.float32)


def energy(g):
    return gaussian_filter((g - gaussian_filter(g, 2.0)) ** 2, 12.0)


sharp = energy(frame[..., 1]) >= 0.7 * energy(mask_img[..., 1])
g = gaussian_filter(mask_img[..., 1], 2.0)
top = np.percentile(g, 99.5)
dark, bright = g < 0.12 * top, g > 0.50 * top
# A dark pixel carries no focus evidence of its own. It counts as in focus
# when the bright pixels around it (Gaussian 20 px) are sharp in FRAME: at
# least 85 % of them, and enough of them to judge.
near_bright = gaussian_filter(bright.astype(np.float32), 20.0)
near_sharp = gaussian_filter((bright & sharp).astype(np.float32), 20.0)
infocus = (near_bright > 0.05) & (near_sharp >= 0.85 * near_bright)
dist = distance_transform_edt(~bright)
edges = [3, 6, 12, 20, 30, 50]
bins = [dark & infocus & (dist >= lo) & (dist < hi) for lo, hi in zip(edges[:-1], edges[1:])]
labels = [f'{lo}-{hi if hi < 100000 else "inf"}' for lo, hi in zip(edges[:-1], edges[1:])]
print(f'in-focus fraction {infocus.mean():.3f}; dark in-focus px per bin: ' + ', '.join(f'{l}: {int(b.sum())}' for l, b in zip(labels, bins)))
bright_in = bright & infocus
del mask_img


def stats(img):
    return np.array([[float(img[..., c][b].mean()) if b.sum() > 500 else np.nan for b in bins] for c in range(3)]), \
        np.array([float(img[..., c][bright_in].mean()) for c in range(3)])


base, bb = stats(frame)
report = {'frame': sys.argv[2], 'bins_px': labels, 'frame_dark_pct_of_bright': (100 * base / bb[:, None]).tolist(), 'arms': {}}
print('frame dark level, % of bright (G): ' + ' '.join(f'{v:.2f}' for v in 100 * base[1] / bb[1]))
print('distance (px):                  ' + ' '.join(f'{l:>7s}' for l in labels))
for p in sys.argv[4:]:
    a, ab = stats(tifffile.imread(p).astype(np.float32))
    name = Path(p).name
    report['arms'][name] = {'ratio': (a / base).tolist(), 'bright_ratio': (ab / bb).tolist()}
    print(f'{name[:30]:30s} G ' + ' '.join(f'{v:7.3f}' for v in a[1] / base[1]) + f'   bright {ab[1] / bb[1]:.4f}')
out.write_text(json.dumps(report, indent=1) + '\n')
