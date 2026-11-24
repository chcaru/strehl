"""Rig helpers for the 2026-11-24 rig sessions (plan X3, X7, Q3, Q6, Q7, S2/S3). Prints no keys.

Every command goes through the Pi's own API with the bench helper (`outputs/shelly-power-
2026-11-18/bench.py` in the main checkout, which reads the pairing key without printing it).

  python rig.py scout <out folder>        camera and light on, a coarse live-view focus sweep,
                                          two test shots back to back (Q3), all off again
  python rig.py sweep <out> <lo> <hi> <n> a live-view sweep of n frames between lo and hi
  python rig.py ladder <out> <position> <seconds,...>   test shots at one focus over a
                                          shutter ladder; the owner's exposure restored
  python rig.py capture <out> <start> <end> <step> <base s> <highlight s> <every>
                                          a capture with highlight groups (plan X7); the
                                          owner's exposure and plan restored afterwards
  python rig.py still <out> <position> <seconds>   magnified live view at the camera's
                                          largest ratio, every frame saved with its time
                                          (the Q7 stillness check's input); magnifier put back
  python rig.py off                       light and camera off, "manage power" on

Whatever happens, `finish()` leaves the light and camera off and "manage power" on.
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, r'C:\dev\blog\death-of-software\projects\strehl\outputs\shelly-power-2026-11-18')
from bench import URL, client, cmd, state, wait  # noqa: E402

T0 = time.time()


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def idle(timeout=120):
    return wait(lambda a: not a['busy'], timeout=timeout)


def seconds(code):
    n, d = code >> 16, code & 0xffff
    return n / d if d else None


def camera_on():
    s = idle()
    if not s['connected']:
        cmd('connect', from_state=s)
        s = wait(lambda a: not a['busy'] and a['connected'] and a['phase'] == 'ready', timeout=150)
    if not s['power'].get('manage_stack'):
        cmd('power_plan', enabled=True)
        s = wait(lambda a: not a['busy'] and a['power'].get('manage_stack'), timeout=30)
    return s


def light(on):
    s = idle()
    if bool(s['power']['light']['on']) != on:
        cmd('power', device='light', on=on)
        s = wait(lambda a: not a['busy'] and bool(a['power']['light']['on']) == on, timeout=60)
    return s


def finish():
    """Light off, camera off, "manage power" on; never raises."""
    try:
        s = idle(300)
        if s['phase'] == 'fault':
            # Nothing was exposed (a focus or command fault): recover first.
            cmd('recover', from_state=s, acknowledge_uncertain=False)
            s = idle(120)
        if s['connected'] and not s['power'].get('manage_stack'):
            cmd('power_plan', enabled=True)
            s = wait(lambda a: not a['busy'] and a['power'].get('manage_stack'), timeout=30)
        if s['power']['light']['on']:
            light(False)
        s = idle()
        if s['power']['camera']['on'] or s['connected']:
            cmd('power', device='camera', on=False)
            s = wait(lambda a: not a['busy'] and not a['connected'] and not a['power']['camera']['on'], timeout=150)
        log('finished | light', s['power']['light']['on'], 'camera', s['power']['camera']['on'],
            'manage', s['power'].get('manage_stack'))
    except Exception as e:  # noqa: BLE001
        log('FINISH FAILED, check the rig by hand:', repr(e))


def focus(target):
    idle()
    cmd('focus', target=int(target))
    return wait(lambda a: not a['busy'] and a.get('position') == int(target), timeout=60)


def preview_jpeg():
    wait(lambda a: a['connected'] and a['preview']['fresh'], timeout=20)
    r = client.get(URL + '/api/preview', timeout=7)
    r.raise_for_status()
    return r.content


def sweep(out, lo, hi, n, settle=0.8):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    targets = sorted({round(lo + (hi - lo) * i / max(n - 1, 1)) for i in range(n)})
    for t in targets:
        focus(t)
        time.sleep(settle)
        (out / ('live-%05d.jpg' % t)).write_bytes(preview_jpeg())
    log('sweep', lo, hi, len(targets), 'frames ->', out)
    return targets


def test_shot(position):
    s = idle()
    seq = s['sequence_id'] + 1
    t = time.time()
    cmd('capture_positions', positions=[int(position)], keep_power_on=True, kind='test')
    wait(lambda a: a['sequence_id'] == seq and a['phase'] == 'capturing', timeout=60)
    s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected')
             and not a['busy'] and not (a.get('storage') or {}).get('pending_frames'), timeout=300)
    return {'phase': s['phase'], 'seconds': round(time.time() - t, 1), 'folder': receipt_folder(s)}


def nearest_shutter(options, want):
    return min((c for c in options if seconds(c)), key=lambda c: abs(seconds(c) / want - 1))


def set_exposure(iso, shutter):
    s = idle()
    e = s.get('exposure') or {}
    if e.get('iso') == iso and e.get('shutter') == shutter:
        return
    cmd('exposure', iso=iso, shutter=shutter)
    wait(lambda a: not a['busy'] and (a.get('exposure') or {}).get('shutter') == shutter, timeout=30)


def ladder(out, position, wants):
    s = idle()
    e = s['exposure']
    iso, owner = e['iso'], e['shutter']
    rows = []
    try:
        focus(position)
        for want in wants:
            code = nearest_shutter(e['shutter_options'], want)
            set_exposure(iso, code)
            row = test_shot(position)
            row['wall_seconds'] = row.pop('seconds')
            row.update(shutter=code, seconds=seconds(code), position=position)
            rows.append(row)
            log('ladder', position, '%.5f s' % seconds(code), 'took %.1f s' % row['wall_seconds'],
                pathlib.Path(row['folder']).name)
    finally:
        set_exposure(iso, owner)
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(out) / 'ladder.json').write_text(json.dumps(rows, indent=1))
    return rows


def mark(position, start):
    focus(position)
    cmd('mark', start=start)
    return idle()


def receipt_folder(s):
    return str(pathlib.Path(s['storage']['receipt']['path'].replace('\\\\?\\', '')).parent)


def capture(out, start, end, step, base_s, high_s, every):
    s = idle()
    e = s['exposure']
    iso, owner = e['iso'], e['shutter']
    plan = s['plan']
    try:
        base = nearest_shutter(e['shutter_options'], base_s)
        high = nearest_shutter(e['shutter_options'], high_s)
        set_exposure(iso, base)
        mark(start, True)
        mark(end, False)
        s = idle()
        cmd('settings', step=step, settle_ms=plan['settle_ms'], approach=plan['approach'],
            capture_timeout_s=max(plan['capture_timeout_s'], 30))
        s = idle()
        planes = s['planned']
        cmd('highlight', highlight={'shutter': high, 'every': every, 'first_plane': 1,
                                    'last_plane': planes, 'shots': s['shots_per_plane']})
        s = idle()
        seq = s['sequence_id'] + 1
        t = time.time()
        cmd('start')
        wait(lambda a: a['sequence_id'] == seq and a['phase'] == 'capturing', timeout=60)
        s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected')
                 and not a['busy'] and not (a.get('storage') or {}).get('pending_frames'), timeout=3600)
        row = {'phase': s['phase'], 'wall_seconds': round(time.time() - t, 1), 'folder': receipt_folder(s),
               'planes': planes, 'base': base, 'highlight': high, 'every': every, 'start': start, 'end': end,
               'step': step, 'message': s['message']}
        log('capture', json.dumps(row))
        pathlib.Path(out).mkdir(parents=True, exist_ok=True)
        with open(pathlib.Path(out) / 'captures.jsonl', 'a') as f:
            f.write(json.dumps(row) + '\n')
        return row
    finally:
        s = camera_on()
        cmd('new_plan')
        set_exposure(iso, owner)


def still(out, position, seconds_):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    s = idle()
    before = s.get('magnifier_current') or 0
    ratio = max(s.get('magnifier_ratios') or [0])
    focus(position)
    try:
        cmd('magnify', ratio=ratio, x=320, y=240)
        wait(lambda a: not a['busy'] and a.get('magnifier_current') == ratio, timeout=30)
        time.sleep(1.0)
        t0 = time.time()
        last, n = None, 0
        while time.time() - t0 < seconds_:
            st = state()
            g = st['preview'].get('generation')
            if g is not None and g != last and st['preview'].get('fresh'):
                r = client.get(URL + '/api/preview', timeout=7)
                r.raise_for_status()
                (out / ('still-%08.3f.jpg' % (time.time() - t0))).write_bytes(r.content)
                last, n = g, n + 1
            time.sleep(0.03)
        log('still', n, 'frames over', seconds_, 's at ratio', ratio, '->', out)
    finally:
        cmd('magnify', ratio=before, x=320, y=240)
        wait(lambda a: not a['busy'], timeout=30)
    return ratio


def settings():
    s = idle()
    e = s.get('exposure') or {}
    return {'iso': e.get('iso'), 'shutter': e.get('shutter'), 'seconds': seconds(e['shutter']) if e.get('shutter') else None,
            'shots': s.get('shots_per_plane'), 'position': s.get('position'), 'plan': s.get('plan'),
            'magnifier': s.get('magnifier_current'), 'warmup': s['power'].get('warmup_seconds'),
            'capabilities': sorted(k for k, v in (s.get('capabilities') or {}).items() if v)}


if __name__ == '__main__':
    what = sys.argv[1]
    try:
        if what == 'scout':
            out = pathlib.Path(sys.argv[2])
            out.mkdir(parents=True, exist_ok=True)
            s = camera_on()
            log('settings', json.dumps(settings()))
            light(True)
            log('light on (switched by the controller; Q3 counts from here)')
            time.sleep(5)
            sweep(out / 'coarse', 40000, 63000, 24)
            pos = idle()['position']
            shots = [test_shot(pos), test_shot(pos)]
            log('test shots (Q3: the second should not wait the warm-up):', json.dumps(shots))
            (out / 'scout.json').write_text(json.dumps({'settings': settings(), 'test_shots': shots}, indent=1))
        elif what == 'sweep':
            camera_on()
            light(True)
            time.sleep(3)
            sweep(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]))
        elif what == 'ladder':
            camera_on()
            light(True)
            log('settings', json.dumps(settings()))
            ladder(sys.argv[2], int(sys.argv[3]), [float(x) for x in sys.argv[4].split(',')])
        elif what == 'capture':
            camera_on()
            a = sys.argv
            capture(a[2], int(a[3]), int(a[4]), int(a[5]), float(a[6]), float(a[7]), int(a[8]))
        elif what == 'still':
            camera_on()
            light(True)
            time.sleep(3)
            r = still(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]))
            (pathlib.Path(sys.argv[2]) / 'still.json').write_text(json.dumps({'ratio': r}))
        elif what == 'off':
            pass
    finally:
        finish()
        log('done in %.0f s' % (time.time() - T0))
