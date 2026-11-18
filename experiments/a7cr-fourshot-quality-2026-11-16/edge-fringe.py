"""Q8: colour fringe at bright-on-dark edges, as channel ratios against
distance from the edge.

  python -X utf8 edge-fringe.py OUT.json MASK.tif ARM.tif [ARM.tif ...]

Classes from MASK (green, 2 px): bright above 50 % of the 99.5th percentile,
not bright below that. For every pixel the signed distance to the bright
boundary (positive outside, into the dark). Per arm and distance bin: mean
R, G, B, then R/G and B/G normalised by the arm's own ratio deep inside the
bright class (10-20 px in), so a neutral, fringe-free edge reads 1.00 where
the dark side has the bright side's colour. The dark side's own colour
shows at large distance; a fringe is the excursion between.

Only pixels whose nearest bright boundary is sharp are useful; this takes
all of them, so the figures understate the fringe on in-focus edges and
should be read arm against arm.
"""
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, gaussian_filter

out = Path(sys.argv[1])
m = tifffile.imread(sys.argv[2]).astype(np.float32)
g = gaussian_filter(m[..., 1], 2.0)
bright = g > 0.50 * np.percentile(g, 99.5)
del m, g
d_out = distance_transform_edt(~bright)
d_in = distance_transform_edt(bright)
edges_out = [0.5, 1.5, 2.5, 3.5, 4.5, 6.5, 9.5, 14.5, 24.5]
bins = [(f'+{(lo + hi) / 2:.0f}', (d_out > lo) & (d_out <= hi)) for lo, hi in zip(edges_out[:-1], edges_out[1:])]
bins = [(f'-{(lo + hi) / 2:.0f}', (d_in > lo) & (d_in <= hi)) for lo, hi in ((0.5, 1.5), (1.5, 2.5), (2.5, 4.5))][::-1] + bins
ref = (d_in > 10) & (d_in <= 20)
report = {'bins': [b[0] for b in bins], 'arms': {}}
print('distance from the bright boundary, px (negative inside): ' + ' '.join(f'{b[0]:>6s}' for b in bins))
for p in sys.argv[3:]:
    img = tifffile.imread(p).astype(np.float32)
    r0 = [float(img[..., c][ref].mean()) for c in range(3)]
    rows = []
    for _, msk in bins:
        v = [float(img[..., c][msk].mean()) for c in range(3)]
        rows.append([(v[0] / v[1]) / (r0[0] / r0[1]), (v[2] / v[1]) / (r0[2] / r0[1]), v[1] / r0[1]])
    rows = np.array(rows)
    report['arms'][Path(p).name] = rows.tolist()
    print(f'{Path(p).name[:28]:28s} R/G ' + ' '.join(f'{v:6.3f}' for v in rows[:, 0]))
    print(f'{"":28s} B/G ' + ' '.join(f'{v:6.3f}' for v in rows[:, 1]))
    print(f'{"":28s} G   ' + ' '.join(f'{v:6.3f}' for v in rows[:, 2]))
out.write_text(json.dumps(report, indent=1) + '\n')
