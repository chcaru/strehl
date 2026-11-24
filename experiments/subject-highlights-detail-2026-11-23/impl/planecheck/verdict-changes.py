"""Which groups' verdicts the Q5 check changes, from `strehl pixel-shift --json` reports of the Q5 build.

  python verdict-changes.py <label> <report.json> [...]

Old verdict, reconstructed: parity failure; else compensated pair misregistration (the new
report's gate reason when it says so, the rule is unchanged); else tile ratio p99/median z^2
>= 2.5 (from the report's pass-2 tile map, self-fitted noise model: a proxy for the gate's
injected-model ratio, checked against base-engine render logs on the 1 s capture). New verdict:
the report's `gate.reason`. Retake flags are the new ones.
"""
import json
import sys

args = sys.argv[1:]
for i in range(0, len(args), 2):
    label, path = args[i], args[i + 1]
    changed, slips_retake, total = [], 0, 0
    for g in json.load(open(path))['groups']:
        gate = g.get('gate')
        if gate is None:
            continue
        total += 1
        new = gate.get('reason') or 'pass'
        if 'CFA parities' in new:
            old = 'parity'
            slips_retake += bool(gate.get('retake'))
        elif 'misregistered' in new or 'structure' in new:
            old = new
        else:
            z = g.get('tile_z2') or {}
            ratio = z['p99'] / z['p50'] if z.get('p50') else float('nan')
            old = 'tiles (ratio %.2f)' % ratio if ratio >= 2.5 else 'pass'
        if (old == 'pass') != (new == 'pass'):
            changed.append('plane %d %s: %s -> %s' % (g['plane'], g['group_id'], old,
                                                      'pass' if new == 'pass' else new.split(':')[0] + ' (local %.2f px)' % (gate.get('local_px') or float('nan'))))
    print('== %s: %d groups; %d verdicts change; parity failures now asking a retake: %d' % (label, total, len(changed), slips_retake))
    for c in changed:
        print('   ' + c)
