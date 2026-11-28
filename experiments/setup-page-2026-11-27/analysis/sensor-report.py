"""Reads setup-sensor's JSON: the gain fits, variance over signal by level, the
top of the data, and the exposure-ratio linearity."""
import json
import sys

d = json.load(open(sys.argv[1]))
NAMES = ['R', 'G1', 'G2', 'B']
print('series:')
for s in d['series']:
    tops = ' '.join('%s %d x%d (+%d under)' % (t['channel'], t['code'], t['on_it'], t['within_16_under']) for t in s['top'])
    print('  %-28s %5.2f s iso %s frames %d black %.0f declared white %.0f drift %s | top: %s' % (
        s['name'][-25:], s['seconds'], s['iso'], s['frames'], s['black'], s['declared_white'],
        ['%.4f' % (v if v is not None else float('nan')) for v in s['drift_rel_sd']], tops))
print('gain fits (DN/e-), by upper fit limit:')
for f in d['fits']:
    print('  to %5.0f DN: ' % f['to_dn'] + '  '.join(
        '%s %.4f (r2 %+.2f, %d pts)' % (c, v['gain'], v['intercept'], v['points']) for c, v in f['fit'].items()))
print('variance over signal by level (G1), pooled over series:')
levels = {}
for s in d['series']:
    for m, v, n in s['bins'][1]:
        k = int(m // 1000)
        a = levels.setdefault(k, [0.0, 0.0, 0.0])
        a[0] += m * n
        a[1] += v * n
        a[2] += n
read2 = float(sys.argv[2]) ** 2 if len(sys.argv) > 2 else 1.78
for k in sorted(levels):
    a = levels[k]
    m, v = a[0] / a[2], a[1] / a[2]
    print('  %6.0f DN  var %9.1f  (var - read^2)/S %.4f  n %d' % (m, v, (v - read2) / m, a[2]))
print('exposure ratio by level of the longer burst (G1):')
for p in d['pairs']:
    rows = p['ratio'][1]
    if not rows:
        continue
    mid = sorted(r[1] for r in rows if 1500 <= r[0] <= 6000) or sorted(r[1] for r in rows)
    flat = mid[len(mid) // 2]
    print('  %.2f s over %.2f s (times %.3f): flat ratio %.4f' % (p['long'], p['short'], p['times'], flat))
    step = max(1, len(rows) // 24)
    line = []
    for r in rows[::step]:
        line.append('%5.0f:%+.2f%%' % (r[0], 100 * (r[1] / flat - 1)))
    print('     ' + '  '.join(line))
    limit = None
    for i, r in enumerate(rows):
        if r[0] > 6000 and all(abs(q[1] / flat - 1) > 0.01 for q in rows[i:i + 3]):
            limit = r[0]
            break
    print('     departs 1 %% from flat at: %s DN above black' % (None if limit is None else round(limit)))
