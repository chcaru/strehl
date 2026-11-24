"""Build a synthetic Calibrate survey (plan X1) from single-plane test runs.

  python make-fixture.py <out folder> <spec.json>

spec.json: {"source_manifest": <run folder>, "shots": [{"run": <folder>, "shutter": <code>,
"position": <focus>}, ...], "shuffle": <seed or null>, "link_from": <folder or null>}

Member 1 of each run's group is copied (or hard-linked from `link_from`, which must hold
the same files) as frame-NNNNNN.ARW.straw. The journal carries the plan X3 format:
capture_intent and capture_buffered with "tier": "base" and "exposure": {"iso", "shutter"};
receipts are durable with the original SHA-256. The originals are only read.
"""
import json
import os
import pathlib
import random
import shutil
import sys

out = pathlib.Path(sys.argv[1])
spec = json.loads(pathlib.Path(sys.argv[2]).read_text())
out.mkdir(parents=True, exist_ok=False)


def jsonl(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


manifest = json.loads((pathlib.Path(spec['source_manifest']) / 'manifest.json').read_text())
manifest['capture_kind'] = 'positions'
manifest['focus_positions'] = [s['position'] for s in spec['shots']]
manifest['planned_planes'] = len(spec['shots'])
manifest['planned_raws'] = len(spec['shots'])
manifest['pixel_shift_shots'] = 1
manifest['fixture_note'] = 'Synthetic survey assembled from test runs for strehl survey (shd-census); member 1 of each source group.'
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2))

groups = []
for k, s in enumerate(spec['shots']):
    run = pathlib.Path(s['run'])
    events = jsonl(run / 'events.jsonl')
    bufs = [e for e in events if e['event'] == 'capture_buffered']
    if 'plane' in s:
        bufs = [e for e in bufs if e['data']['response']['files'][0]['plane'] == s['plane']
                and e['data']['response'].get('group_complete')]
    buf = bufs[-1]
    member = [f for f in buf['data']['response']['files'] if f['member_index'] == 1][0]
    assert buf['data']['target'] == s['position'], (run, buf['data']['target'], s['position'])
    intent = [e for e in events if e['event'] == 'capture_intent'][-1]
    shutter_status = intent['data']['camera_status']['properties']['ShutterSpeed']['value']
    assert shutter_status == s['shutter'], (run, shutter_status, s['shutter'])
    iso = intent['data']['camera_status']['properties']['IsoSensitivity']['value']
    name = 'frame-%06d.ARW' % (k + 1)
    src = run / (member['name'] + '.straw')
    dst = out / (name + '.straw')
    if spec.get('link_from'):
        os.link(pathlib.Path(spec['link_from']) / (name + '.straw'), dst)
    else:
        shutil.copyfile(src, dst)
    groups.append({
        'ordinal': k, 'plane': k + 1, 'target': s['position'], 'name': name,
        'sha256': member['sha256'], 'bytes': member['bytes'], 'group_id': 'fixture-%d' % (k + 1),
        'iso': iso, 'shutter': s['shutter'], 'storage_bytes': dst.stat().st_size,
        'source': str(run),
    })

order = list(range(len(groups)))
if spec.get('shuffle') is not None:
    random.Random(spec['shuffle']).shuffle(order)

seq = 1
lines = [{'data': {}, 'event': 'created', 'sequence': seq, 'unix_ms': 0}]
receipts = []
for i in order:
    g = groups[i]
    exposure = {'iso': g['iso'], 'shutter': g['shutter']}
    seq += 1
    lines.append({'data': {'ordinal': g['ordinal'], 'target': g['target'], 'tier': 'base', 'exposure': exposure},
                  'event': 'capture_intent', 'sequence': seq, 'unix_ms': seq})
    seq += 1
    f = {'bytes': g['bytes'], 'durable': False, 'group_id': g['group_id'], 'member_index': 1, 'members': 1,
         'name': g['name'], 'plane': g['plane'], 'sha256': g['sha256'], 'tier': 'base'}
    lines.append({'data': {'ordinal': g['ordinal'], 'target': g['target'], 'tier': 'base', 'exposure': exposure,
                           'response': {'files': [f], 'group_complete': True, 'pixel_shift_shots': 1}},
                  'event': 'capture_buffered', 'sequence': seq, 'unix_ms': seq})
    receipts.append({'bytes': g['bytes'], 'durable': True, 'encoding': 'strehl-raw-v1', 'logical_name': g['name'],
                     'ok': True, 'path': str(out / (g['name'] + '.straw')), 'sha256': g['sha256'],
                     'storage_bytes': g['storage_bytes']})
seq += 1
lines.append({'data': {'completed': len(groups), 'outcome': 'complete'}, 'event': 'finished', 'sequence': seq, 'unix_ms': seq})
(out / 'events.jsonl').write_text(''.join(json.dumps(l) + '\n' for l in lines))
(out / 'transfer-receipts.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in receipts))
(out / 'fixture-sources.json').write_text(json.dumps(groups, indent=1))
print('wrote', out, len(groups), 'shots, order', 'shuffled' if spec.get('shuffle') is not None else 'as listed')
