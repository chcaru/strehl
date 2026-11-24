"""A subject JSON over a rectangle of backdrop: the corner region farthest from the found
subject's rings (no highlights expected there).

  python backdrop-subject.py <survey json> <out json>
"""
import json
import sys

s = json.load(open(sys.argv[1]))['subject']
pts = [p for r in s['rings'] for p in r]
xs, ys = [p[0] for p in pts], [p[1] for p in pts]
print('subject bbox x %.3f..%.3f y %.3f..%.3f' % (min(xs), max(xs), min(ys), max(ys)))
# Candidate 0.15 x 0.15 squares in the four corners; keep the one with no ring point inside
# a 0.05 margin around it.
best = None
for (x0, y0) in [(0.03, 0.03), (0.82, 0.03), (0.03, 0.82), (0.82, 0.82)]:
    x1, y1 = x0 + 0.15, y0 + 0.15
    inside = sum(1 for x, y in pts if x0 - 0.05 <= x <= x1 + 0.05 and y0 - 0.05 <= y <= y1 + 0.05)
    print('corner', x0, y0, 'ring points near', inside)
    if inside == 0 and best is None:
        best = (x0, y0, x1, y1)
x0, y0, x1, y1 = best
out = {'rings': [[[x0, y0], [x1, y0], [x1, y1], [x0, y1]]], 'reference_focus': s['reference_focus'],
       'ppm_per_unit': s['ppm_per_unit'], 'provenance': {'kind': 'box', 'note': 'backdrop corner, shd-census no-highlight control'}}
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print('box', best)
