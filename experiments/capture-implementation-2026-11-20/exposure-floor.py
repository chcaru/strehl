"""Decision D6a: where does the capture stop getting faster as the exposure shortens?

  python exposure-floor.py <start> <planes> <out.txt>

For each exposure (ISO raised to keep the brightness of 0.6 s at ISO 100, so the files
compress no better than at 0.6 s: the uplink's own worst case), four-shot and single-shot
runs of <planes> planes 8 units apart, error correction off. Reports the plane period
(capture intents), the camera's own capture time, the RAWs' lag to the PC, the upload queue's
peak, and the model `timing::initial_plane`'s prediction. Restores the exposure and
pixel-shift mode it found. Deletes nothing (the caller deletes the runs it names).
"""
import json
import pathlib
import statistics as st
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import cmd, state, wait  # noqa: E402

start, planes, out = int(sys.argv[1]), int(sys.argv[2]), pathlib.Path(sys.argv[3])
s = wait(lambda a: not a['busy'], timeout=60)
orig_iso, orig_shutter = s['exposure']['iso'], s['exposure']['shutter']
orig_shots = s['shots_per_plane']
options = set(s['exposure']['shutter_options'])
isos = set(s['exposure']['iso_options'])


def shutter(num, den):
    return (num << 16) | den


plan = [(shutter(6, 10), 100), (shutter(3, 10), 200), (shutter(1, 6), 400), (shutter(1, 10), 640), (shutter(1, 25), 1600)]
lines = []


def run(shots, sh, iso):
    s = wait(lambda a: not a['busy'], timeout=60)
    if s['shots_per_plane'] != shots:
        cmd('pixel_shift', shots=shots)
        s = wait(lambda a: not a['busy'] and a['shots_per_plane'] == shots, timeout=60)
    if (s['exposure']['shutter'], s['exposure']['iso']) != (sh, iso):
        cmd('exposure', iso=iso, shutter=sh)
        s = wait(lambda a: not a['busy'] and a['exposure']['shutter'] == sh and a['exposure']['iso'] == iso, timeout=60)
    seq = s['sequence_id'] + 1
    cmd('capture_positions', positions=[start + 8 * i for i in range(planes)])
    wait(lambda a: a['sequence_id'] == seq and a['phase'] == 'capturing', timeout=60)
    s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected') and not a['busy'], timeout=1200)
    folder = pathlib.Path(s['storage']['receipt']['path'].replace('\\\\?\\', '')).parent
    events = [json.loads(l) for l in open(folder / 'events.jsonl', encoding='utf-8')]
    intents = [e['unix_ms'] for e in events if e['event'] == 'capture_intent']
    period = st.median([(b - a) / 1000 for a, b in zip(intents, intents[1:])])
    cams = [e['data']['response']['camera_seconds'] for e in events if e['event'] == 'capture_buffered']
    receipts = {r['logical_name']: r for r in (json.loads(l) for l in open(folder / 'transfer-receipts.jsonl', encoding='utf-8')) if 'wire_bytes' in r}
    lags = []
    for e in events:
        if e['event'] != 'capture_buffered':
            continue
        r0 = e['unix_ms'] - 1000 * e['data']['response']['camera_seconds']
        for f, cf in zip(e['data']['response']['files'], e['data']['response']['camera_reply']['files']):
            rec = receipts.get(f['name'])
            if rec:
                lags.append((rec['saved_unix_ms'] - (r0 + 1000 * cf['seconds'])) / 1000)
    wire = st.median([r['wire_bytes'] for r in receipts.values()]) / 1e6
    seconds = (sh >> 16) / (sh & 0xffff)
    model = (seconds + 0.55) * shots + 1.0
    line = '%s %5.3f s ISO %4d: plane period %.2f s (model %.2f), capture() %.2f s, wire %.1f MB a RAW, lag to PC median %.2f s max %.2f s, queue peak %s, %s' % (
        'four-shot' if shots == 4 else 'single   ', seconds, iso, period, model, st.median(cams), wire, st.median(lags), max(lags),
        s['storage'].get('queue_peak'), folder.name)
    print(line, flush=True)
    lines.append(line)


try:
    for sh, iso in plan:
        if sh not in options or iso not in isos:
            lines.append('skipped %s ISO %s: not offered' % (sh, iso))
            continue
        for shots in (4, 1):
            run(shots, sh, iso)
finally:
    s = wait(lambda a: not a['busy'], timeout=120)
    cmd('exposure', iso=orig_iso, shutter=orig_shutter)
    s = wait(lambda a: not a['busy'] and a['exposure']['shutter'] == orig_shutter, timeout=60)
    if s['shots_per_plane'] != orig_shots:
        cmd('pixel_shift', shots=orig_shots)
        wait(lambda a: not a['busy'] and a['shots_per_plane'] == orig_shots, timeout=60)
    out.write_text('\n'.join(lines) + '\n')
