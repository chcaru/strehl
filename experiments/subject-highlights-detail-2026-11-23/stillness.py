"""Stillness test at one focus position (no lens move between frames). Prints no keys.

1. Magnified live view (the camera's largest magnifier ratio) fetched as fast as the host
   serves it for LIVE_SECONDS: a time series of where the picture sits.
2. A burst of single-shot RAWs at one focus position, short shutter.
3. The live series again.

"Manage power" is switched off for the series and back on afterwards; ISO, shutter, shot count
and the magnifier are put back; camera and light off at the end.

  python stillness.py <position> <out folder> [burst frames] [live seconds]
"""
import hashlib
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import URL, client, cmd, state, wait  # noqa: E402

POSITION = int(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
BURST = int(sys.argv[3]) if len(sys.argv) > 3 else 30
LIVE_SECONDS = float(sys.argv[4]) if len(sys.argv) > 4 else 60
OUT.mkdir(parents=True, exist_ok=True)
T0 = time.time()
record = {'position': POSITION, 'live': [], 'burst': None}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def idle(timeout=120):
    return wait(lambda a: not a['busy'], timeout=timeout)


def seconds(code):
    n, d = code >> 16, code & 0xffff
    return n / d if d else None


def set_exposure(iso, shutter):
    s = idle()
    e = s['exposure']
    if e.get('iso') == iso and e.get('shutter') == shutter:
        return
    cmd('exposure', iso=iso, shutter=shutter)
    wait(lambda a: not a['busy'] and (a.get('exposure') or {}).get('shutter') == shutter, timeout=30)


def live_series(label):
    folder = OUT / label
    folder.mkdir(exist_ok=True)
    frames, last = [], None
    end = time.time() + LIVE_SECONDS
    while time.time() < end:
        t = time.time()
        try:
            r = client.get(URL + '/api/preview', timeout=5)
            r.raise_for_status()
        except Exception as ex:  # a missed frame is not worth stopping for
            time.sleep(0.05)
            continue
        h = hashlib.md5(r.content).hexdigest()
        if h == last:
            time.sleep(0.02)
            continue
        last = h
        name = '%05d.jpg' % len(frames)
        (folder / name).write_bytes(r.content)
        frames.append({'t': round(t - T0, 3), 'name': name})
    record['live'].append({'label': label, 'frames': frames})
    span = frames[-1]['t'] - frames[0]['t'] if len(frames) > 1 else 0
    log('live series %s: %d distinct frames in %.1f s (%.1f a second)' % (label, len(frames), span, len(frames) / max(span, 1e-6)))


before = state()
log('before | phase', before['phase'], 'connected', before['connected'], 'manage power', before['power']['manage_stack'], 'plan', json.dumps(before.get('plan')))
s = before
if not s['connected']:
    if not s['power']['camera']['on']:
        cmd('power', device='camera', on=True)
    s = wait(lambda a: not a['busy'] and a['connected'], timeout=150)
if not s['power']['light']['on']:
    cmd('power', device='light', on=True)
    s = wait(lambda a: not a['busy'] and a['power']['light']['on'], timeout=60)
    log('light on; warming 150 s')
    time.sleep(150)
s = idle()
MANAGED = s['power']['manage_stack']
if MANAGED:
    cmd('power_plan', enabled=False)
    s = wait(lambda a: not a['busy'] and not a['power']['manage_stack'])
e = s['exposure']
ISO, SHUTTER, SHOTS = e['iso'], e['shutter'], s['shots_per_plane']
MAG0 = s.get('magnifier_current')
ratios = s.get('magnifier_ratios') or []
log('connected | iso', ISO, 'shutter %.4f s' % seconds(SHUTTER), 'shots', SHOTS, 'position', s.get('position'), 'magnifier', MAG0, 'of', ratios)
record.update(iso=ISO, shutter=SHUTTER, shots=SHOTS, magnifier_before=MAG0, magnifier_ratios=ratios)
try:
    cmd('focus', target=POSITION)
    wait(lambda a: not a['busy'] and a.get('position') == POSITION, timeout=60)
    time.sleep(3)
    big = max(ratios) if ratios else 0
    if big:
        idle()
        cmd('magnify', ratio=big, x=320, y=240)
        wait(lambda a: not a['busy'] and a.get('magnifier_current') == big, timeout=30)
        time.sleep(1.5)
        record['magnifier_used'] = big
        live_series('live-a')
        idle()
        cmd('magnify', ratio=0, x=320, y=240)
        wait(lambda a: not a['busy'] and (a.get('magnifier_current') or 0) == 0, timeout=30)
    # the RAW burst: single shots, 1/8 s, no lens move between them
    short = min((c for c in e['shutter_options'] if seconds(c)), key=lambda c: abs(seconds(c) / 0.125 - 1))
    set_exposure(ISO, short)
    idle()
    cmd('pixel_shift', shots=1)
    wait(lambda a: not a['busy'] and a.get('shots_per_plane') == 1, timeout=60)
    s = idle()
    seq = s['sequence_id'] + 1
    t = time.time()
    cmd('capture_positions', positions=[POSITION] * BURST, keep_power_on=True)
    wait(lambda a: a['sequence_id'] == seq and a['phase'] == 'capturing', timeout=90)
    s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected') and not a['busy']
             and not (a.get('storage') or {}).get('pending_frames'), timeout=120 + 20 * BURST)
    folder = str(pathlib.Path(s['storage']['receipt']['path'].replace('\\\\?\\', '')).parent)
    record['burst'] = {'folder': folder, 'frames': BURST, 'seconds': seconds(short), 'phase': s['phase'], 'wall': round(time.time() - t, 1), 'started': round(t - T0, 1)}
    log('burst: %d single shots at %.4f s in %.1f s, phase %s, %s' % (BURST, seconds(short), time.time() - t, s['phase'], pathlib.Path(folder).name))
    idle()
    cmd('pixel_shift', shots=SHOTS)
    wait(lambda a: not a['busy'] and a.get('shots_per_plane') == SHOTS, timeout=60)
    set_exposure(ISO, SHUTTER)
    if big:
        idle()
        cmd('magnify', ratio=big, x=320, y=240)
        wait(lambda a: not a['busy'] and a.get('magnifier_current') == big, timeout=30)
        time.sleep(1.5)
        live_series('live-b')
finally:
    (OUT / 'record.json').write_text(json.dumps(record, indent=1))
    s = idle(180)
    if s['connected']:
        if (s.get('magnifier_current') or 0) != 0:
            cmd('magnify', ratio=0, x=320, y=240)
            s = wait(lambda a: not a['busy'] and (a.get('magnifier_current') or 0) == 0, timeout=30)
        if s.get('shots_per_plane') != SHOTS:
            cmd('pixel_shift', shots=SHOTS)
            s = wait(lambda a: not a['busy'] and a.get('shots_per_plane') == SHOTS, timeout=60)
        set_exposure(ISO, SHUTTER)
        s = idle()
        chk = s['exposure']
        log('settings back | iso', chk.get('iso'), 'shutter %.4f s' % seconds(chk['shutter']), 'shots', s.get('shots_per_plane'), 'magnifier', s.get('magnifier_current'))
    if s['power']['light']['on']:
        cmd('power', device='light', on=False)
        s = wait(lambda a: not a['busy'] and not a['power']['light']['on'], timeout=60)
    if MANAGED and s['connected'] and not s['power']['manage_stack']:
        cmd('power_plan', enabled=True)
        s = wait(lambda a: not a['busy'] and a['power']['manage_stack'])
    if s['power']['camera']['on'] or s['connected']:
        cmd('power', device='camera', on=False)
        s = wait(lambda a: not a['busy'] and not a['power']['camera']['on'], timeout=150)
    p = s['power']
    log('off | camera', p['camera']['on'], 'light', p['light']['on'], 'manage power', p['manage_stack'], '| plan', json.dumps(s.get('plan')))
    log('done in %.0f s' % (time.time() - T0))
