"""Check a tiered capture's journal (plan X3): groups per plane and tier, the
plane numbers and focus of each highlight group against its base group,
the exposures, the shutter changes, and the seconds a plane took with and
without a highlight group.

  python tiers-check.py <capture folder>
"""
import collections
import json
import pathlib
import sys

folder = pathlib.Path(sys.argv[1])
events = [json.loads(l) for l in open(folder / 'events.jsonl', encoding='utf-8')]
manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
print('plan.highlight', json.dumps(manifest['plan'].get('highlight')))
groups = []
for e in events:
    if e['event'] in ('capture_buffered', 'capture_complete'):
        d = e['data']
        files = d['response']['files']
        groups.append({'tier': d.get('tier', 'base'), 'plane': files[0]['plane'], 'target': d['target'],
                       'shutter': d.get('exposure', {}).get('shutter'), 'files': len(files),
                       'file_tiers': sorted({f.get('tier') for f in files}), 'ms': e['unix_ms']})
by = collections.defaultdict(dict)
for g in groups:
    by[g['plane']][g['tier']] = g
bad = []
for plane, tiers in sorted(by.items()):
    if 'highlight' in tiers:
        b, h = tiers['base'], tiers['highlight']
        if b['target'] != h['target'] or b['shutter'] == h['shutter'] or h['file_tiers'] != ['highlight']:
            bad.append(plane)
counts = collections.Counter(g['tier'] for g in groups)
print('groups', dict(counts), 'planes', len(by), 'with highlight', sum('highlight' in t for t in by.values()))
print('mismatched highlight groups', bad)
shutters = collections.Counter((g['tier'], g['shutter']) for g in groups)
print('exposures', {f'{k[0]}:{k[1]}': v for k, v in shutters.items()})
changes = sum(1 for e in events if e['event'] == 'exposure_complete')
print('shutter changes', changes)
# Seconds a plane took: from one base group to the next base group.
bases = [g for g in groups if g['tier'] == 'base']
with_h, without = [], []
for a, b in zip(bases, bases[1:]):
    dt = (b['ms'] - a['ms']) / 1000
    (with_h if 'highlight' in by[a['plane']] else without).append(dt)
for name, v in (('with a highlight group', with_h), ('without', without)):
    if v:
        v = sorted(v)
        print('seconds a plane %s: median %.1f (%d planes)' % (name, v[len(v) // 2], len(v)))
