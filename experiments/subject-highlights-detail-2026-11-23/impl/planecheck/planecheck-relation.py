"""Plan Q5: how the old and the new plane check relate to the offset between the four shots.

Reads `strehl pixel-shift --all-groups --json` reports written by the Q5 build (each group
carries `gate`: the stack's own verdict, and `tile_local_px`: the new per-tile measure).

  python planecheck-relation.py <label> <report.json> [<label> <report.json> ...]

Offset between shots: the largest component of the raw (uncompensated) witness pair shift,
as `checker-relation.py` defines it. Old rule: tile ratio p99/median z^2 >= 2.5. New rule:
`gate.reason` (local p99 in px against LOCAL_TOLERANCE_PX, after the pair's whole-group
shift is taken out; parity slips; compensated misregistration).
"""
import json
import sys

import numpy as np

BINS = ((0, 0.15), (0.15, 0.25), (0.25, 0.40), (0.40, 1.0))


def kind(reason):
    if not reason:
        return 'pass'
    for key, name in (('CFA parities', 'slip/pattern'), ('tiles disagree', 'local'),
                      ('misregistered', 'misregistered'), ('structure', 'structure'),
                      ('sensor buffer', 'edge'), ('level', 'levels')):
        if key in reason:
            return name
    return 'other'


args = sys.argv[1:]
for i in range(0, len(args), 2):
    label, path = args[i], args[i + 1]
    doc = json.load(open(path))
    rows, kinds = [], {}
    for g in doc['groups']:
        gate = g.get('gate')
        if gate is None:
            continue
        k = kind(gate.get('reason'))
        kinds[k] = kinds.get(k, 0) + 1
        s, z = g.get('witness_pair_shift_px'), g.get('tile_z2') or {}
        if s is None or not z:
            continue
        off = float(np.max(np.abs(np.array(s, dtype=float))))
        ratio = z['p99'] / z['p50']
        local = gate.get('local_px')
        rows.append((g['plane'], g['group_id'], off, ratio, np.nan if local is None else local, k))
    print('== %s: %d groups checked; new verdicts %s' % (label, sum(kinds.values()), kinds))
    tol = doc['groups'][0]['gate']['local_tolerance_px'] if doc['groups'] and 'gate' in doc['groups'][0] else float('nan')
    r = np.array([(o, q, l) for _, _, o, q, l, _ in rows])
    old_fail = r[:, 1] >= 2.5
    new_local_fail = np.array([k == 'local' for *_, k in rows])
    print('   groups with a witness: %d; offset median %.3f px, 90th %.3f, largest %.3f' % (
        len(r), np.median(r[:, 0]), np.percentile(r[:, 0], 90), r[:, 0].max()))
    print('   old tile rule fails %d; new local rule fails %d (local tolerance %.3f px)' % (
        old_fail.sum(), new_local_fail.sum(), tol))
    for lo, hi in BINS:
        m = (r[:, 0] >= lo) & (r[:, 0] < hi)
        if m.sum():
            print('   offset %.2f-%.2f px: %3d groups | old ratio median %.2f, largest %.2f, fails %d | local p99 median %.3f px, largest %.3f, fails %d' % (
                lo, hi, m.sum(), np.median(r[m, 1]), r[m, 1].max(), old_fail[m].sum(),
                np.nanmedian(r[m, 2]), np.nanmax(r[m, 2]), new_local_fail[m].sum()))
    ok = np.isfinite(r[:, 2])
    if ok.sum() > 2:
        slope, icept = np.polyfit(r[ok, 0], r[ok, 2], 1)
        print('   fit: local p99 = %.3f + %.3f x offset (px); correlation %.2f' % (
            icept, slope, np.corrcoef(r[ok, 0], r[ok, 2])[0, 1]))
    worst = sorted(rows, key=lambda t: -(t[4] if np.isfinite(t[4]) else -1))[:6]
    print('   largest local p99: ' + '; '.join('plane %d %s %.3f px (offset %.2f, ratio %.2f, %s)' % (
        p, gid, l, o, q, k) for p, gid, o, q, l, k in worst))
