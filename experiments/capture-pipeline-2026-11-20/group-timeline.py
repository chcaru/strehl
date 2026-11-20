"""Read-only: inside-the-group timeline of a run (camera progress states and RAW completions),
and the gaps between journal events around each plane."""
import json
import sys

run = sys.argv[1]
which = [int(a) for a in sys.argv[2:]] or [0, 1]
events = [json.loads(l) for l in open(run + '/events.jsonl', encoding='utf-8') if l.strip()]
manifest = json.load(open(run + '/manifest.json', encoding='utf-8'))
cam = None
for e in events:
    if e.get('event') == 'capture_intent':
        cam = e['data'].get('camera_status', {}).get('properties', {})
        break
if cam:
    print('camera:', {k: v.get('value') for k, v in cam.items()})
print('manifest keys:', sorted(manifest.keys()))
for k in ('settle_ms', 'shutter', 'iso', 'exposure', 'plan', 'capture', 'settings'):
    if k in manifest:
        print(' ', k, '=', json.dumps(manifest[k])[:600])
caps = [e for e in events if e.get('event') == 'capture_buffered']
for n in which:
    if n >= len(caps):
        continue
    c = caps[n]
    r = c['data']['response']
    reply = r.get('camera_reply') or {}
    print('--- group', n, 'capture() seconds', reply.get('seconds'), 'camera_seconds', r.get('camera_seconds'))
    rows = [(p['seconds'], 'state  active=%s member=%s buffer=0x%04x' % (p['active'], p['member'], p['buffer'])) for p in reply.get('progress', [])]
    rows += [(f['seconds'], 'RAW %d complete on the Pi (%d bytes)' % (f['member_index'], f['bytes'])) for f in reply.get('files', [])]
    for t, text in sorted(rows):
        print('   %7.3f  %s' % (t, text))
    for f in r.get('files', [])[:1]:
        print('   queue entry keys:', sorted(f.keys()))
print('--- journal gaps (s)')
prev = None
for e in events:
    if prev is not None:
        print('   %-18s -> %-18s %6.3f' % (prev['event'], e['event'], (e['unix_ms'] - prev['unix_ms']) / 1000))
    prev = e
    if e.get('event') == 'capture_buffered' and e['data'].get('ordinal', 0) >= 2:
        break
