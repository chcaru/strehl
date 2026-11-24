"""Where a group's high local-disagreement tiles sit: clustered (a real local event) or scattered.

  python tile-clusters.py <report.json> <limit_px> <plane:group_id> [...]

Prints, per group, the tiles at or above the limit: count, their bounding box in tiles, the
largest connected cluster (8-neighbour), and a coarse map ('#' over the limit, '+' over 0.7 of
it, '.' measured, ' ' unmeasured), downsampled to at most 75 columns.
"""
import json
import sys

import numpy as np

doc = json.load(open(sys.argv[1]))
limit = float(sys.argv[2])
want = set(sys.argv[3:])
for g in doc['groups']:
    key = '%d:%s' % (g['plane'], g['group_id'])
    if key not in want or 'tile_local_map' not in g:
        continue
    gw, gh = g['tile_grid']
    m = np.array([np.nan if v is None else v for v in g['tile_local_map']], dtype=float).reshape(gh, gw)
    over = np.nan_to_num(m, nan=0) >= limit
    ys, xs = np.nonzero(over)
    seen = np.zeros_like(over)
    best = 0
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        stack, n = [(y0, x0)], 0
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop()
            n += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < gh and 0 <= xx < gw and over[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        stack.append((yy, xx))
        best = max(best, n)
    measured = np.isfinite(m).sum()
    print('== plane %s: %d of %d measured tiles at or above %.2f px; largest cluster %d tiles; box x %s y %s; local p99 %s' % (
        key, over.sum(), measured, limit, best,
        (xs.min(), xs.max()) if len(xs) else '-', (ys.min(), ys.max()) if len(ys) else '-',
        g['gate'].get('local_px')))
    step = max(1, int(np.ceil(gw / 75)))
    for y in range(0, gh, step):
        row = ''
        for x in range(0, gw, step):
            b = m[y:y + step, x:x + step]
            if np.isfinite(b).any():
                v = np.nanmax(b)
                row += '#' if v >= limit else '+' if v >= 0.7 * limit else '.'
            else:
                row += ' '
        print('   ' + row)
