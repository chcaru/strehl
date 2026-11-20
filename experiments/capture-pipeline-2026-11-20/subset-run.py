"""A copy of a four-shot capture run holding every STRIDE-th plane, as a run folder the engine
reads (for testing a coarser focus step on a stack that was captured finely).

  subset-run.py <run> <dest> <stride> <offset> [--link-from <other dest>]

The source run is only read. Archives are copied (or, with --link-from, hard-linked from a
previous subset on the same volume). Planes are renumbered consecutively; events.jsonl keeps
the selected planes' capture events, transfer-receipts.jsonl their receipts, and manifest.json
the selected focus positions.
"""
import json
import os
import pathlib
import shutil
import sys

src, dest, stride, offset = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
link_from = pathlib.Path(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[5] == '--link-from' else None
dest.mkdir(parents=True, exist_ok=False)
events = [json.loads(l) for l in open(src / 'events.jsonl', encoding='utf-8') if l.strip()]
captures = [e for e in events if e.get('event') in ('capture_buffered', 'capture_complete')]
planes = sorted({f['plane'] for e in captures for f in e['data']['response']['files']})
chosen = planes[offset::stride]
renumber = {p: planes[0] + i for i, p in enumerate(chosen)}
ordinals = sorted({e['data']['ordinal'] for e in captures})
names, out_events, positions = set(), [], []
for e in events:
    kind = e.get('event')
    if kind in ('capture_buffered', 'capture_complete'):
        files = e['data']['response']['files']
        if files[0]['plane'] not in renumber:
            continue
        e = json.loads(json.dumps(e))
        for f in e['data']['response']['files']:
            f['plane'] = renumber[f['plane']]
            names.add(f['name'])
        e['data']['ordinal'] = renumber[files[0]['plane']] - planes[0] + ordinals[0]
        positions.append(e['data'].get('target'))
        out_events.append(e)
    elif kind in ('created', 'finished'):
        out_events.append(e)
for i, e in enumerate(out_events):
    e['sequence'] = i + 1
(dest / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in out_events), encoding='utf-8')
receipts = [json.loads(l) for l in open(src / 'transfer-receipts.jsonl', encoding='utf-8') if l.strip()]
kept = [r for r in receipts if r.get('logical_name') in names]
(dest / 'transfer-receipts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in kept), encoding='utf-8')
m = json.loads((src / 'manifest.json').read_text(encoding='utf-8'))
m['focus_positions'] = positions
m['planned_planes'] = len(chosen)
m['planned_raws'] = len(names)
(dest / 'manifest.json').write_text(json.dumps(m, indent=1) + '\n', encoding='utf-8')
if (src / 'result.json').exists():
    r = json.loads((src / 'result.json').read_text(encoding='utf-8'))
    if 'completed' in r:
        r['completed'] = len(chosen)
    (dest / 'result.json').write_text(json.dumps(r) + '\n', encoding='utf-8')
size = 0
for name in sorted(names):
    for candidate in (name + '.straw', name):
        if (src / candidate).exists():
            if link_from is not None:
                os.link(link_from / candidate, dest / candidate)
            else:
                shutil.copyfile(src / candidate, dest / candidate)
            size += (dest / candidate).stat().st_size
            break
print('%d of %d planes (stride %d, offset %d; original planes %d..%d), %d files, %.1f GB -> %s' % (
    len(chosen), len(planes), stride, offset, chosen[0], chosen[-1], len(names), size / 1e9, dest))
