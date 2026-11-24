"""Plan X7 gates on a fused render against its base-only render (same engine,
STREHL_HIGHLIGHT_FUSION=off), from their sensor masters (`--sensor-master`: the merged
RGGB mosaic, FP32, black-subtracted DN, before any display step).

1. Unpinned areas equal: outside the neighbourhood of the base-only render's bright
   photosites (at or above `--bright` of the raw pin above black), the two renders
   agree. Reported for several neighbourhood radii, in DN.
2. Where the base-only render is at or above the pin, what the fused render holds:
   how many of those photosites remain at or below the pin level, and the fused peak.

  python compare-masters.py <fused master.tif> <base master.tif> [--black 512] [--pin 16383]
"""
import argparse
import json

import numpy as np
import tifffile
from scipy import ndimage

ap = argparse.ArgumentParser()
ap.add_argument('fused')
ap.add_argument('base')
ap.add_argument('--black', type=float, default=512.0)
ap.add_argument('--pin', type=float, default=16383.0)
ap.add_argument('--bright', type=float, default=0.70)
a = ap.parse_args()

f = tifffile.imread(a.fused).astype(np.float32)
b = tifffile.imread(a.base).astype(np.float32)
assert f.shape == b.shape and f.ndim == 2, (f.shape, b.shape)
full = a.pin - a.black
print(f'mosaic {f.shape}; base-only max {b.max():.1f} DN ({b.max() / full:.3f} of the pin above black), '
      f'fused max {f.max():.1f} ({f.max() / full:.2f})')
bright = b >= a.bright * full
print(f'bright photosites in the base-only render (>= {a.bright} of the pin): {int(bright.sum())} '
      f'({100 * bright.mean():.4f} %)')
d = np.abs(f - b)
out = {'radii': []}
for r in (0, 8, 32, 64, 128, 256, 512, 1024):
    near = ndimage.binary_dilation(bright, iterations=r) if r else bright
    far = ~near
    dd = d[far]
    row = {
        'radius_px': r,
        'far_fraction': float(far.mean()),
        'max_abs_dn': float(dd.max()),
        'p99_99_abs_dn': float(np.percentile(dd, 99.99)),
        'p99_abs_dn': float(np.percentile(dd, 99)),
        'exact_fraction': float((dd == 0).mean()),
        'within_0_5_dn_fraction': float((dd <= 0.5).mean()),
    }
    out['radii'].append(row)
    print('outside %3d px of bright: %.4f of the mosaic; |diff| max %.3f DN, p99.99 %.4f, p99 %.5f; exact %.4f, '
          '<=0.5 DN %.6f' % (r, row['far_fraction'], row['max_abs_dn'], row['p99_99_abs_dn'], row['p99_abs_dn'],
                              row['exact_fraction'], row['within_0_5_dn_fraction']))
# Where the base-only stack reaches the pin (a pinned frame's value survived the merge).
for k, name in enumerate(['R', 'G1', 'G2', 'B']):
    dy, dx = divmod(k, 2)
    bp, fp = b[dy::2, dx::2], f[dy::2, dx::2]
    pinned = bp >= 0.98 * full
    n = int(pinned.sum())
    if n == 0:
        print(f'{name}: no base-only photosite at the pin')
        continue
    recovered = fp[pinned] > 1.02 * full
    print(f'{name}: base-only photosites at >= 0.98 of the pin: {n}; fused above 1.02 of the pin there: '
          f'{int(recovered.sum())} ({100 * recovered.mean():.1f} %); fused median {np.median(fp[pinned]) / full:.2f}, '
          f'max {fp[pinned].max() / full:.2f} of the pin')
    out[name] = {'pinned': n, 'fused_above': int(recovered.sum())}
json.dump(out, open(a.fused + '.compare.json', 'w'), indent=1)
