"""Compare single-group.rs's three arms (demosaic1, demosaic4, shift).

  python -X utf8 compare-single-group.py OUT_DIR

Per crop: one display transform for all arms (gain from demosaic1's luma
p99.5 in that crop, then a 1/2.2 power), native pixels, plus a 3x
nearest-neighbour zoom of the crop's central 128 px for the eye (zooms are
labelled as such; the native strip is the evidence).

Metrics per arm over all crops: high-passed chroma (R-G, B-G minus their 5x5
box mean) RMS on edge pixels (luma gradient top 20%) and on flat pixels
(bottom 50%), normalised by the crop's mean green so crops of different
brightness weigh alike. Edge chroma = false colour + colour fringes (lateral
CA is common to all arms) + noise; flat chroma is mostly noise.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import uniform_filter

out = Path(sys.argv[1])
meta = json.loads((out / 'crops.json').read_text())
C = meta['crop']
ARMS = ['demosaic1', 'demosaic4', 'shift']


def load(i, a):
    return np.fromfile(out / f'crop{i}-{a}.f32', '<f4').reshape(C, C, 3)


def luma(x):
    return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]


rows, zooms, acc = [], [], {a: {'edge': [], 'flat': []} for a in ARMS}
for i, origin in enumerate(meta['origins']):
    im = {a: load(i, a) for a in ARMS}
    assert all(np.isfinite(v).all() for v in im.values())
    L1 = luma(im['demosaic1'])
    gain = 1.0 / max(1e-6, float(np.percentile(L1, 99.5)))
    # Edge/flat masks from demosaic4 (low noise, same geometry as both others).
    l4 = uniform_filter(luma(im['demosaic4']), 3)
    gy, gx = np.gradient(l4)
    grad = np.hypot(gx, gy)[4:-4, 4:-4]
    edge, flat = grad >= np.percentile(grad, 80), grad <= np.percentile(grad, 50)
    norm = float(im['demosaic4'][..., 1].mean())
    for a in ARMS:
        x = im[a]
        cr, cb = x[..., 0] - x[..., 1], x[..., 2] - x[..., 1]
        h = np.sqrt((cr - uniform_filter(cr, 5)) ** 2 + (cb - uniform_filter(cb, 5)) ** 2)[4:-4, 4:-4] / norm
        acc[a]['edge'].append(float(np.sqrt((h[edge] ** 2).mean())))
        acc[a]['flat'].append(float(np.sqrt((h[flat] ** 2).mean())))

    def disp(x):
        return (np.clip(np.clip(x * gain, 0, 1) ** (1 / 2.2) * 255 + 0.5, 0, 255)).astype(np.uint8)

    rows.append(np.concatenate([np.pad(disp(im[a]), ((4, 4), (4, 4), (0, 0)), constant_values=255) for a in ARMS], 1))
    c0 = C // 2 - 64
    zooms.append(np.concatenate([np.pad(disp(im[a][c0:c0 + 128, c0:c0 + 128]).repeat(3, 0).repeat(3, 1),
                                        ((4, 4), (4, 4), (0, 0)), constant_values=255) for a in ARMS], 1))
    print(f'crop {i}: origin {origin} size {C}; zoom: central 128 px at 3x nearest')
Image.fromarray(np.concatenate(rows, 0)).save(out / 'native.png')
Image.fromarray(np.concatenate(zooms[:3], 0)).save(out / 'zoom3x-a.png')
Image.fromarray(np.concatenate(zooms[3:], 0)).save(out / 'zoom3x-b.png')
summary = {a: {k: {'per_crop': v, 'mean': float(np.mean(v))} for k, v in d.items()} for a, d in acc.items()}
(out / 'metrics.json').write_text(json.dumps(summary, indent=1) + '\n')
for a in ARMS:
    print(f"{a:10s} edge chroma {summary[a]['edge']['mean']:.4f}  flat chroma {summary[a]['flat']['mean']:.4f}  "
          f"edge per crop {[round(v, 4) for v in acc[a]['edge']]}")
print('columns:', ARMS)
