"""Q4: the fusion's dark lift, against distance from bright pixels, with the
mask taken from an independent render.

  python -X utf8 halo-distance.py OUT.json MASK.tif BASE.tif ARM.tif [ARM.tif ...]

MASK.tif defines the pixel classes and is NOT one of the scored renders
(use the other half-stack of the base arm: its noise is independent of every
scored image, so choosing dark pixels by threshold cannot bias the scored
means; halo.py took the mask from the base arm itself). Green, smoothed at
2 px: bright above 50 % of the 99.5th percentile, dark below 12 %. Dark
pixels are binned by their distance to the nearest bright pixel.

Per arm, channel and distance bin: mean of the arm over the bin divided by
the base's mean (ratio), and the difference as a percentage of the bright
level (absolute lift). A lift that falls with distance is light spread from
bright neighbours; one that is flat out to 100+ px is a loss of
low-frequency contrast or a global effect.

Control: the base arm's own other half, scored like an arm, must read 1.00.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, gaussian_filter

out = Path(sys.argv[1])
mask_img = tifffile.imread(sys.argv[2]).astype(np.float32)
g = gaussian_filter(mask_img[..., 1], 2.0)
top = np.percentile(g, 99.5)
dark, bright = g < 0.12 * top, g > 0.50 * top
dist = distance_transform_edt(~bright)
edges = [3, 6, 12, 20, 30, 50, 100, 200, 100000]
bins = [dark & (dist >= lo) & (dist < hi) for lo, hi in zip(edges[:-1], edges[1:])]
labels = [f'{lo}-{hi if hi < 100000 else "inf"}' for lo, hi in zip(edges[:-1], edges[1:])]
print('dark px per distance bin: ' + ', '.join(f'{l}: {int(b.sum())}' for l, b in zip(labels, bins)))
del mask_img


def stats(path):
    img = tifffile.imread(path).astype(np.float32)
    return np.array([[float(img[..., c][b].mean()) if b.any() else np.nan for b in bins] for c in range(3)]), \
        np.array([float(img[..., c][bright].mean()) for c in range(3)])


base, base_bright = stats(sys.argv[3])
report = {'mask': sys.argv[2], 'base': sys.argv[3], 'bins_px': labels, 'dark_level_pct_of_bright': (100 * base / base_bright[:, None]).tolist(), 'arms': {}}
print('base dark level, % of bright (G): ' + ' '.join(f'{v:.2f}' for v in 100 * base[1] / base_bright[1]))
print('distance (px):                 ' + ' '.join(f'{l:>8s}' for l in labels))
for p in sys.argv[4:]:
    a, ab = stats(p)
    name = Path(p).name
    report['arms'][name] = {'ratio': (a / base).tolist(), 'lift_pct_of_bright': (100 * (a - base) / base_bright[:, None]).tolist(),
                            'bright_ratio': (ab / base_bright).tolist()}
    print(f'{name[:30]:30s} G ratio ' + ' '.join(f'{v:8.3f}' for v in a[1] / base[1]) + f'   bright {ab[1] / base_bright[1]:.4f}')
    print(f'{"":30s} G lift, % of bright ' + ' '.join(f'{v:+7.3f}' for v in 100 * (a[1] - base[1]) / base_bright[1]))
out.write_text(json.dumps(report, indent=1) + '\n')
