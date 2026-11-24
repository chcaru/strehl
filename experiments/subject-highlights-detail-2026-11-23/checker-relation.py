"""How the plane check's tile ratio relates to the offset between the four shots, by exposure.
Reads the JSON reports of `strehl pixel-shift --json` for two captures of one framing.

  python checker-relation.py <label> <report.json> [<label> <report.json> ...]
"""
import json
import sys

import numpy as np

args = sys.argv[1:]
for i in range(0, len(args), 2):
    label, path = args[i], args[i + 1]
    rows, verdicts = [], {}
    for g in json.load(open(path))['groups']:
        verdicts[g.get('verdict')] = verdicts.get(g.get('verdict'), 0) + 1
        s, z = g.get('witness_pair_shift_px'), g.get('tile_z2') or {}
        if s is None or not z:
            continue
        rows.append((float(np.max(np.abs(np.array(s, dtype=float)))), z['p99'] / z['p50']))
    r = np.array(rows)
    k = float(np.sum((r[:, 1] - 1) * r[:, 0] ** 2) / np.sum(r[:, 0] ** 4))
    print('%s: %d groups with a measured offset; verdicts without compensation: %s' % (label, len(r), verdicts))
    print('   largest offset between two of the four shots, px: median %.3f, 75th percentile %.3f, 90th %.3f, largest %.3f; at or above 0.2 px: %d' % (
        np.median(r[:, 0]), np.percentile(r[:, 0], 75), np.percentile(r[:, 0], 90), r[:, 0].max(), int((r[:, 0] >= 0.2).sum())))
    for lo, hi in ((0, 0.15), (0.15, 0.25), (0.25, 0.4), (0.4, 1.0)):
        m = (r[:, 0] >= lo) & (r[:, 0] < hi)
        if m.sum():
            print('   offset %.2f-%.2f px: %3d groups, tile ratio (p99 / median z^2) median %.2f, largest %.2f' % (lo, hi, m.sum(), np.median(r[m, 1]), r[m, 1].max()))
    print('   fit: tile ratio - 1 = %.1f x offset^2, so the 2.5 threshold is reached at %.2f px' % (k, np.sqrt(1.5 / k)))
