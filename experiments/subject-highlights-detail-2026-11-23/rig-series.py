"""Rig series for the subject/highlights/detail brief (Q3, Q5, Q6, Q7, Q9). Prints no keys.

Every RAW capture is a single-plane run of capture_kind "test": the open desktop does not
follow, stack or list those. ISO, shutter, pixel-shift count and power are restored at the end
whatever happens (camera and light off, "manage power" left on). "Manage power" is switched off
for the series, because with it on every run waits the light warm-up again (60 s on this rig).

  python rig-series.py <index.json> <live-view folder> [series ...]

Series (default: all, in this order):
  ladder    four-shot groups at three in-focus positions over a shutter ladder, the owner's
            shutter first and again last
  repeat    six groups at one position, each after its own approach
  sweep     a fine focus sweep (step 2, +-24 units) around that position
  single    one single-shot group at a short shutter, with the pixel-shift switch timed
  live      live-view JPEGs across the owner's focus range (no RAW)
"""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import URL, client, cmd, state, wait  # noqa: E402

INDEX = pathlib.Path(sys.argv[1])
LIVE = pathlib.Path(sys.argv[2])
SERIES = sys.argv[3:] or ['ladder', 'repeat', 'sweep', 'single', 'live']
POSITIONS = [24972, 25182, 25462]      # planes 70, 100, 140 of stack-1795460665629-8651
CENTRE = 25182
LADDER = [1.3, 1 / 15, 1 / 60, 1 / 250, 1 / 1000]   # seconds; the owner's shutter brackets them
rows = json.loads(INDEX.read_text()) if INDEX.exists() else []
T0 = time.time()


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def save():
    INDEX.write_text(json.dumps(rows, indent=1))


def idle(timeout=90):
    return wait(lambda a: not a['busy'], timeout=timeout)


def seconds(code):
    n, d = code >> 16, code & 0xffff
    return n / d if d else None


def nearest(options, want):
    best = min((c for c in options if seconds(c)), key=lambda c: abs(seconds(c) / want - 1))
    return best


def set_exposure(iso, shutter):
    s = idle()
    e = s['exposure']
    if e.get('iso') == iso and e.get('shutter') == shutter:
        return 0.0
    t = time.time()
    cmd('exposure', iso=iso, shutter=shutter)
    wait(lambda a: not a['busy'] and (a.get('exposure') or {}).get('shutter') == shutter and (a.get('exposure') or {}).get('iso') == iso, timeout=30)
    return time.time() - t


def shoot(series, position, note=None):
    want = seconds(idle()['exposure']['shutter'])
    for r in rows:
        if series == 'ladder' and r.get('series') == series and r.get('position') == position and r.get('note') == note \
                and abs(r.get('seconds', 0) / want - 1) < 0.01:
            log('kept', series, position, note or '')
            return r
    s = idle()
    assert s['connected'] and not s['failure'], s['message']
    seq = s['sequence_id'] + 1
    e = s['exposure']
    t = time.time()
    cmd('capture_positions', positions=[position], keep_power_on=True, kind='test')
    wait(lambda a: a['sequence_id'] == seq and a['phase'] == 'capturing', timeout=60)
    s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected') and not a['busy']
             and not (a.get('storage') or {}).get('pending_frames'), timeout=240)
    assert s['phase'] == 'complete', (s['phase'], s['message'])
    folder = str(pathlib.Path(s['storage']['receipt']['path'].replace('\\\\?\\', '')).parent)
    row = {'series': series, 'position': position, 'iso': e['iso'], 'shutter': e['shutter'], 'seconds': seconds(e['shutter']),
           'shots': s.get('shots_per_plane'), 'folder': folder, 'wall_seconds': round(time.time() - t, 2),
           'started': round(t - T0, 1), 'note': note}
    rows.append(row)
    save()
    log(series, 'pos', position, 'shutter %.5f s' % row['seconds'], 'shots', row['shots'], '%.1f s' % row['wall_seconds'], pathlib.Path(folder).name, note or '')
    return row


def power_on():
    s = state()
    if not s['connected']:
        if not s['power']['camera']['on']:
            cmd('power', device='camera', on=True)
        s = wait(lambda a: not a['busy'] and a['connected'], timeout=150)
    if not s['power']['light']['on']:
        cmd('power', device='light', on=True)
        s = wait(lambda a: not a['busy'] and a['power']['light']['on'], timeout=60)
        log('light on; warming 100 s (it dims about 9 % in its first minute)')
        time.sleep(100)
    s = idle(150)
    if s['power']['manage_stack']:
        cmd('power_plan', enabled=False)
        s = wait(lambda a: not a['busy'] and not a['power']['manage_stack'])
        log('manage power off for the series (it waits the light warm-up before every run); restored at the end')
    return idle()


def power_off(iso, shutter, shots):
    s = idle(120)
    try:
        if s['connected']:
            if s.get('shots_per_plane') != shots:
                cmd('pixel_shift', shots=shots)
                s = wait(lambda a: not a['busy'] and a.get('shots_per_plane') == shots, timeout=60)
            set_exposure(iso, shutter)
            s = idle()
    finally:
        if s['power']['light']['on']:
            cmd('power', device='light', on=False)
            s = wait(lambda a: not a['busy'] and not a['power']['light']['on'], timeout=60)
        if s['connected'] and not s['power']['manage_stack']:
            cmd('power_plan', enabled=True)
            s = wait(lambda a: not a['busy'] and a['power']['manage_stack'])
        if s['power']['camera']['on'] or s['connected']:
            cmd('power', device='camera', on=False)
            s = wait(lambda a: not a['busy'] and not a['power']['camera']['on'], timeout=150)
    p = s['power']
    log('restored | camera', p['camera']['on'], 'light', p['light']['on'], 'manage power', p['manage_stack'],
        '| plan', json.dumps(s.get('plan')), '(exposure and shot count are not reported with the camera off)')


before = state()
log('before | phase', before['phase'], 'connected', before['connected'], 'manage power', before['power']['manage_stack'],
    'plan', json.dumps(before.get('plan')), 'shots', before.get('shots_per_plane'))
s = power_on()
e = s['exposure']
ISO, SHUTTER, SHOTS = e['iso'], e['shutter'], s['shots_per_plane']
options = e['shutter_options']
log('connected | usb', s.get('usb_speed_mbps'), '| iso', ISO, 'shutter', SHUTTER, '= %.4f s' % seconds(SHUTTER), '| shots', SHOTS,
    '| position', s.get('position'), '|', len(options), 'shutter codes')
assert SHOTS == 4 and ISO == 100, (SHOTS, ISO)
try:
    if 'ladder' in SERIES:
        for p in POSITIONS:
            shoot('ladder', p, 'owner shutter, first')
        for want in LADDER:
            code = nearest(options, want)
            took = set_exposure(ISO, code)
            log('exposure change to %.5f s took %.2f s' % (seconds(code), took))
            rows.append({'series': 'exposure-change', 'seconds': seconds(code), 'took': round(took, 2)})
            for p in POSITIONS:
                shoot('ladder', p)
        took = set_exposure(ISO, SHUTTER)
        rows.append({'series': 'exposure-change', 'seconds': seconds(SHUTTER), 'took': round(took, 2)})
        for p in POSITIONS:
            shoot('ladder', p, 'owner shutter, last')
    if 'repeat' in SERIES:
        set_exposure(ISO, SHUTTER)
        for i in range(6):
            shoot('repeat', CENTRE, 'revisit %d' % i)
    if 'sweep' in SERIES:
        set_exposure(ISO, SHUTTER)
        for k in range(-12, 13):
            shoot('sweep', CENTRE + 2 * k)
        shoot('sweep', CENTRE, 'centre again')
    if 'single' in SERIES:
        code = nearest(options, 1 / 60)
        set_exposure(ISO, code)
        shoot('single-ref', CENTRE, 'four-shot at the short shutter')
        t = time.time()
        cmd('pixel_shift', shots=1)
        wait(lambda a: not a['busy'] and a.get('shots_per_plane') == 1, timeout=60)
        to_one = time.time() - t
        shoot('single', CENTRE, 'one shot at the short shutter')
        t = time.time()
        cmd('pixel_shift', shots=4)
        wait(lambda a: not a['busy'] and a.get('shots_per_plane') == 4, timeout=60)
        to_four = time.time() - t
        rows.append({'series': 'pixel-shift-switch', 'to_one': round(to_one, 2), 'to_four': round(to_four, 2)})
        save()
        log('pixel shift 4 -> 1 took %.2f s, 1 -> 4 took %.2f s' % (to_one, to_four))
        set_exposure(ISO, SHUTTER)
    if 'live' in SERIES:
        LIVE.mkdir(parents=True, exist_ok=True)
        set_exposure(ISO, SHUTTER)
        plan = idle()['plan']
        lo, hi = sorted((plan['start'], plan['end']))
        targets = [round(lo + (hi - lo) * i / 29) for i in range(30)]
        for t_ in targets:
            idle()
            cmd('focus', target=t_)
            wait(lambda a: not a['busy'] and a.get('position') == t_, timeout=40)
            time.sleep(0.8)
            wait(lambda a: a['connected'] and a['preview']['fresh'], timeout=20)
            r = client.get(URL + '/api/preview', timeout=7)
            r.raise_for_status()
            (LIVE / ('live-%05d.jpg' % t_)).write_bytes(r.content)
            rows.append({'series': 'live', 'position': t_, 'bytes': len(r.content)})
        save()
        log('live view:', len(targets), 'frames saved')
finally:
    save()
    power_off(ISO, SHUTTER, SHOTS)
    log('done in %.0f s' % (time.time() - T0))
