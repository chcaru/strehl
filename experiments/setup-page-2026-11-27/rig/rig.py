"""Rig measurements for the Setup page spec (experiments/setup-page-2026-11-27).

  python rig.py up        camera on (light untouched), connect, single-shot, error correction off
  python rig.py info      exposure options and state
  python rig.py burst LABEL FRAMES ISO SHUTTER [POSITION]
  python rig.py light on|off
  python rig.py focus TARGET
  python rig.py down      restore exposure, four-shot, error correction; camera and light off
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, 'C:/dev/blog/death-of-software/projects/strehl/outputs/shelly-power-2026-11-18')
import bench  # noqa: E402

OUT = pathlib.Path('C:/strehl-scratch/calib-page')
LOG = OUT / 'series.jsonl'


def settled(timeout=90):
    return bench.wait(lambda s: s['editable'] and not s['busy'], timeout)


def shutter_seconds(v):
    return (v >> 16) / (v & 0xffff)


def note(rec):
    rec['unix'] = time.time()
    with LOG.open('a') as f:
        f.write(json.dumps(rec) + '\n')


def up():
    s = bench.state()
    if not (s['power']['camera'] or {}).get('on'):
        bench.cmd('power', device='camera', on=True)
        time.sleep(3)
        bench.wait(lambda a: not a['busy'], 150)
    s = bench.state()
    if not s['connected']:
        bench.cmd('connect')
        s = bench.wait(lambda a: a['connected'] and not a['busy'], 120)
    s = settled()
    before = {k: s.get(k) for k in ('position', 'shots_per_plane', 'error_correction', 'plan')}
    before['exposure'] = {k: (s.get('exposure') or {}).get(k) for k in ('iso', 'shutter')}
    p = OUT / 'before.json'
    if not p.exists():
        p.write_text(json.dumps(before, indent=1))
    if s['shots_per_plane'] != 1:
        bench.cmd('pixel_shift', shots=1)
        s = settled()
    if s.get('error_correction'):
        bench.cmd('error_correction', enabled=False, max_retakes=(s.get('retakes') or {}).get('max', 2))
        s = settled()
    print('connected', s['connected'], 'position', s['position'], 'shots', s['shots_per_plane'],
          'exposure', s['exposure'].get('iso'), s['exposure'].get('shutter'),
          'ec', s.get('error_correction'), 'light', s['power']['light']['on'], 'usb', s.get('usb_speed_mbps'))


def info():
    s = bench.state()
    ex = s.get('exposure') or {}
    print('iso', ex.get('iso'), 'shutter', ex.get('shutter'), 'f', ex.get('f_number'))
    print('iso options', ex.get('iso_options'))
    so = ex.get('shutter_options') or []
    print('shutter options', [(v, round(shutter_seconds(v), 6)) for v in so])
    print({k: s.get(k) for k in ('phase', 'busy', 'connected', 'position', 'shots_per_plane', 'error_correction', 'message')})
    print('power', s['power']['camera'], s['power']['light'], 'magnifier', s.get('magnifier_ratios'), s.get('magnifier'))


def exposure(iso, shutter):
    s = settled()
    ex = s['exposure']
    if (ex.get('iso'), ex.get('shutter')) != (iso, shutter):
        bench.cmd('exposure', iso=iso, shutter=shutter)
        s = settled()
        ex = s['exposure']
        assert (ex.get('iso'), ex.get('shutter')) == (iso, shutter), ex
    return s


def focus(target):
    settled()
    bench.cmd('focus', target=target)
    return bench.wait(lambda a: not a['busy'] and a.get('position') == target, 60)


def burst(label, frames, iso, shutter, position=None):
    s = exposure(iso, shutter)
    if position is not None and s['position'] != position:
        focus(position)
        s = settled()
    position = s['position']
    expected = s['sequence_id'] + 1
    began = time.time()
    bench.cmd('capture_positions', positions=[position] * frames, keep_power_on=True)
    s = bench.wait(lambda a: a['sequence_id'] == expected and a['phase'] in ('complete', 'fault', 'stopped')
                   and not a['busy'], frames * (shutter_seconds(shutter) + 12) + 240)
    assert s['phase'] == 'complete', s['message']
    bench.wait(lambda a: (a['storage'] or {}).get('pending_frames', 0) == 0, 300)
    s = bench.state()
    path = s['storage']['receipt']['path']
    folder = path.replace(chr(92) * 2 + '?' + chr(92), '').rsplit(chr(92), 1)[0]
    rec = {'label': label, 'folder': folder, 'frames': frames, 'iso': iso, 'shutter': shutter,
           'seconds': shutter_seconds(shutter), 'position': position, 'began_unix': began,
           'wall_seconds': time.time() - began, 'light': s['power']['light']}
    note(rec)
    print(json.dumps(rec), flush=True)
    return rec


def light(on):
    s = bench.state()
    if bool((s['power']['light'] or {}).get('on')) != on:
        t = time.time()
        bench.cmd('power', device='light', on=on)
        bench.wait(lambda a: not a['busy'], 60)
        note({'label': 'light', 'on': on, 'commanded_unix': t})
        print('light', on, 'at', t)
    else:
        print('light already', on)


def down():
    before = json.loads((OUT / 'before.json').read_text())
    s = bench.state()
    if s['connected']:
        s = settled()
        ex = before['exposure']
        if ex.get('iso') and ex.get('shutter'):
            exposure(ex['iso'], ex['shutter'])
        if before.get('shots_per_plane') and bench.state()['shots_per_plane'] != before['shots_per_plane']:
            bench.cmd('pixel_shift', shots=before['shots_per_plane'])
            settled()
        if before.get('error_correction') and not bench.state().get('error_correction'):
            bench.cmd('error_correction', enabled=True, max_retakes=(bench.state().get('retakes') or {}).get('max', 2))
            settled()
    s = bench.state()
    if (s['power']['light'] or {}).get('on'):
        bench.cmd('power', device='light', on=False)
        bench.wait(lambda a: not a['busy'], 60)
    s = bench.state()
    if (s['power']['camera'] or {}).get('on'):
        bench.cmd('power', device='camera', on=False)
        time.sleep(2)
        bench.wait(lambda a: not a['busy'], 120)
    s = bench.state()
    print('down: connected', s['connected'], 'camera', s['power']['camera'], 'light', s['power']['light'],
          'shots', s['shots_per_plane'], 'ec', s.get('error_correction'), 'message', s['message'])


if __name__ == '__main__':
    what = sys.argv[1]
    if what == 'up':
        up()
    elif what == 'info':
        info()
    elif what == 'burst':
        a = sys.argv
        burst(a[2], int(a[3]), int(a[4]), int(a[5]), int(a[6]) if len(a) > 6 else None)
    elif what == 'light':
        light(sys.argv[2] == 'on')
    elif what == 'focus':
        print(focus(int(sys.argv[2]))['position'])
    elif what == 'down':
        down()
