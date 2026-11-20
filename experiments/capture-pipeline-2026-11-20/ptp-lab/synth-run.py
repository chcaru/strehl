"""Turn the settle test's RAWs (pNN-sSSSS-M.ARW) into a run folder the engine's own
four-shot check can read:   synth-run.py <raw folder> <manifest to copy> <run folder>

The RAWs are moved (renamed), not copied. events.jsonl and transfer-receipts.jsonl carry
only what `strehl pixel-shift` reads: one capture_buffered event per group with each file's
name, plane, SHA-256, group id and member index, and one durable receipt per file.
Writes settle-map.json (plane -> settle ms) beside them.
"""
import hashlib
import json
import pathlib
import re
import sys

src, manifest, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
groups = {}
for f in sorted(src.glob('*.ARW')):
    m = re.match(r'p(\d+)-s(\d+)-(\d)\.ARW', f.name)
    groups.setdefault((int(m.group(1)), int(m.group(2))), {})[int(m.group(3))] = f
events, receipts, settle = [], [], {}
n = 0
for (plane, ms), members in sorted(groups.items()):
    files = []
    for member in (1, 2, 3, 4):
        n += 1
        name = 'frame-%06d.ARW' % n
        h = hashlib.sha256()
        with open(members[member], 'rb') as fh:
            while True:
                b = fh.read(1 << 24)
                if not b:
                    break
                h.update(b)
        members[member].rename(out / name)
        size = (out / name).stat().st_size
        files.append({'name': name, 'plane': plane, 'sha256': h.hexdigest(), 'group_id': 'lab-%02d' % plane,
                      'member_index': member, 'members': 4, 'bytes': size, 'durable': True})
        receipts.append({'logical_name': name, 'sha256': h.hexdigest(), 'durable': True, 'ok': True, 'bytes': size})
    events.append({'event': 'capture_buffered', 'sequence': len(events) + 1, 'unix_ms': 0,
                   'data': {'ordinal': plane, 'target': 40916 + 8 * plane,
                            'response': {'files': files, 'pixel_shift_shots': 4, 'group_complete': True}}})
    settle[plane] = ms
m = json.loads(manifest.read_text(encoding='utf-8'))
m['planned_planes'] = len(groups)
m['planned_raws'] = 4 * len(groups)
m['focus_positions'] = [40916 + 8 * p for p, _ in sorted(groups)]
(out / 'manifest.json').write_text(json.dumps(m, indent=1) + '\n', encoding='utf-8')
(out / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events), encoding='utf-8')
(out / 'transfer-receipts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in receipts), encoding='utf-8')
(out / 'settle-map.json').write_text(json.dumps(settle) + '\n', encoding='utf-8')
print(len(groups), 'groups,', n, 'files ->', out)
