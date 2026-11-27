"""Rig series for the grounding experiments. Prints no keys. Everything it changes is put back.

  python rig-series.py <out folder> [--proof-position P] [--skip-proofs] [--skip-sweeps]

A. Cold start. Camera on, "manage power" off for the series, lens to the proof position, then the
   light on (t = 0) and PROOF PLANES at set times after it: a four-shot group at the base shutter
   and one at the highlight shutter, each its own test run (a test run is one position; the
   owner's desktop does not follow, stack or list test runs).
B. Live-view sweeps with the light warm: every distinct preview after each move, saved as JPEG.
   Dense (the stack's range and a margin, 20 units apart), then wide and coarse (33 positions).
C. A last proof plane, then: lens back, approach, exposure, four-shot, "manage power", light and
   camera as found.
"""
import hashlib
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(r'C:\dev\blog\death-of-software\projects\strehl')
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import URL, client, cmd, state, wait  # noqa: E402

OUT = pathlib.Path(sys.argv[1])
ARGS = sys.argv[2:]
PROOF = int(ARGS[ARGS.index('--proof-position') + 1]) if '--proof-position' in ARGS else 32734
BASE, SHORT, ISO = 851978, 65576, 100            # 1.3 s, 1/40 s: the owner's stack
PROOF_AT = [0, 30, 60, 100, 140, 190, 250, 320, 400, 500, 620, 760]   # seconds after the light
DENSE = list(range(31900, 33421, 20))
WIDE = [29500 + i * 190 for i in range(33)]
OUT.mkdir(parents=True, exist_ok=True)
record = {'proof_position': PROOF, 'proofs': [], 'sweeps': {}, 'notes': []}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def save():
    (OUT / 'record.json').write_text(json.dumps(record, indent=1))


def idle(timeout=120):
    return wait(lambda a: not a['busy'], timeout=timeout)


def focus(target, timeout=40):
    idle()
    cmd('focus', target=target)
    return wait(lambda a: not a['busy'] and a.get('position') == target, timeout=timeout)


def set_exposure(iso, shutter):
    s = idle()
    e = s['exposure']
    if e.get('iso') == iso and e.get('shutter') == shutter:
        return
    cmd('exposure', iso=iso, shutter=shutter)
    wait(lambda a: not a['busy'] and (a.get('exposure') or {}).get('shutter') == shutter
         and (a.get('exposure') or {}).get('iso') == iso, timeout=30)


def test_run(position, shutter=None):
    """One test run (one four-shot group). Returns its folder and timings."""
    s = idle()
    assert s['connected'] and not s['failure'], s['message']
    seq = s['sequence_id'] + 1
    t = time.time()
    extra = {'shutters': [shutter]} if shutter else {}
    cmd('capture_positions', positions=[position], keep_power_on=True, kind='test', **extra)
    wait(lambda a: a['sequence_id'] == seq and a['phase'] == 'capturing', timeout=60)
    s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected')
             and not a['busy'] and not (a.get('storage') or {}).get('pending_frames'), timeout=240)
    assert s['phase'] == 'complete', (s['phase'], s['message'])
    folder = str(pathlib.Path(s['storage']['receipt']['path'].replace('\\\\?\\', '')).parent)
    return {'folder': folder, 'started_unix': t, 'wall_s': round(time.time() - t, 2)}


def proof(label, t_light):
    a = test_run(PROOF)
    b = test_run(PROOF, SHORT)
    row = {'label': label, 'after_light_s': round(a['started_unix'] - t_light, 1), 'base': a, 'highlight': b,
           'light_watts': state()['power']['light']['watts']}
    record['proofs'].append(row)
    save()
    log('proof %-6s at %5.0f s after the light: base %.1f s, highlight %.1f s, light %.1f W'
        % (label, row['after_light_s'], a['wall_s'], b['wall_s'], row['light_watts']))


def sweep(name, positions):
    folder = OUT / name
    folder.mkdir(exist_ok=True)
    rows = []
    focus(positions[0] - 128)                       # always arrive from below
    t_start = time.time()
    for p in positions:
        t0 = time.time()
        before = hashlib.md5(client.get(URL + '/api/preview', timeout=7).content).hexdigest()
        focus(p)
        t_move = time.time() - t0
        seen, kept, last = 0, [], before
        end = time.time() + 6
        while len(kept) < 2 and time.time() < end:
            r = client.get(URL + '/api/preview', timeout=7)
            h = hashlib.md5(r.content).hexdigest()
            if h != last and h != before:
                last = h
                seen += 1
                if seen >= 2:                       # the first changed frame may straddle the move
                    fname = '%05d-%d.jpg' % (p, len(kept))
                    (folder / fname).write_bytes(r.content)
                    kept.append(fname)
            time.sleep(0.03)
        rows.append({'position': p, 'move_s': round(t_move, 3), 'total_s': round(time.time() - t0, 3), 'frames': kept})
    record['sweeps'][name] = {'positions': len(positions), 'seconds': round(time.time() - t_start, 1), 'rows': rows}
    save()
    log('sweep %s: %d positions in %.1f s (%.2f s a position; the move %.2f s)'
        % (name, len(positions), time.time() - t_start, (time.time() - t_start) / len(positions),
           sum(r['move_s'] for r in rows) / len(rows)))


before = state()
log('before | phase', before['phase'], 'connected', before['connected'], 'camera', before['power']['camera']['on'],
    'light', before['power']['light']['on'], 'manage power', before['power']['manage_stack'])
record['before'] = {k: before.get(k) for k in ('phase', 'connected', 'position', 'shots_per_plane', 'start_set', 'end_set')}
record['before']['power'] = before['power']
CAMERA0, LIGHT0, MANAGED0 = before['power']['camera']['on'], before['power']['light']['on'], before['power']['manage_stack']
s = before
PLAN0 = POS0 = ISO0 = SHUTTER0 = SHOTS0 = None
try:
    if not s['connected']:
        if not s['power']['camera']['on']:
            cmd('power', device='camera', on=True)
        s = wait(lambda a: not a['busy'] and a['connected'], timeout=150)
    s = idle()
    if s['power']['manage_stack']:
        cmd('power_plan', enabled=False)
        s = wait(lambda a: not a['busy'] and not a['power']['manage_stack'])
    e = s['exposure']
    ISO0, SHUTTER0, SHOTS0, PLAN0, POS0 = e['iso'], e['shutter'], s['shots_per_plane'], s['plan'], s.get('position')
    record['connected'] = {'iso': ISO0, 'shutter': SHUTTER0, 'shots': SHOTS0, 'position': POS0, 'usb': s.get('usb_speed_mbps'),
                           'battery': s.get('battery'), 'plan': {k: PLAN0[k] for k in ('start', 'end', 'step', 'settle_ms', 'approach', 'capture_timeout_s')}}
    log('connected | usb', s.get('usb_speed_mbps'), '| iso', ISO0, 'shutter code', SHUTTER0, 'shots', SHOTS0, '| position', POS0, '| battery', s.get('battery'))
    set_exposure(ISO, BASE)
    if SHOTS0 != 4:
        cmd('pixel_shift', shots=4)
        idle()
    cmd('settings', step=PLAN0['step'], settle_ms=PLAN0['settle_ms'], approach=1, capture_timeout_s=PLAN0['capture_timeout_s'])
    idle()
    focus(PROOF - 128)
    focus(PROOF)
    save()
    if '--skip-proofs' not in ARGS:
        if state()['power']['light']['on']:
            record['notes'].append('the light was already on: no cold start')
            t_light = time.time()
        else:
            cmd('power', device='light', on=True)
            wait(lambda a: not a['busy'] and a['power']['light']['on'], timeout=60)
            t_light = time.time()
        record['light_on_unix'] = t_light
        log('light on')
        for i, at in enumerate(PROOF_AT):
            while time.time() - t_light < at:
                time.sleep(0.2)
            proof('p%02d' % i, t_light)
    else:
        if not state()['power']['light']['on']:
            cmd('power', device='light', on=True)
            wait(lambda a: not a['busy'] and a['power']['light']['on'], timeout=60)
        t_light = time.time()
    if '--skip-sweeps' not in ARGS:
        sweep('dense', DENSE)
        sweep('wide', WIDE)
        focus(PROOF - 128)
        focus(PROOF)
        proof('last', t_light)
finally:
    try:
        s = idle()
        if s['connected'] and PLAN0 is not None:
            cmd('settings', step=PLAN0['step'], settle_ms=PLAN0['settle_ms'], approach=PLAN0['approach'], capture_timeout_s=PLAN0['capture_timeout_s'])
            idle()
            set_exposure(ISO0, SHUTTER0)
            if state()['shots_per_plane'] != SHOTS0:
                cmd('pixel_shift', shots=SHOTS0)
                idle()
            if POS0 is not None:
                focus(POS0)
        s = idle()
        if not LIGHT0 and s['power']['light']['on']:
            cmd('power', device='light', on=False)
            s = wait(lambda a: not a['busy'] and not a['power']['light']['on'], timeout=60)
        if MANAGED0 and s['connected'] and not s['power']['manage_stack']:
            cmd('power_plan', enabled=True)
            s = wait(lambda a: not a['busy'] and a['power']['manage_stack'])
        if not CAMERA0 and (s['power']['camera']['on'] or s['connected']):
            cmd('power', device='camera', on=False)
            s = wait(lambda a: not a['busy'] and not a['power']['camera']['on'], timeout=150)
        s = state()
        record['after'] = {'phase': s['phase'], 'connected': s['connected'], 'power': s['power'], 'position': s.get('position'),
                           'exposure': {k: (s.get('exposure') or {}).get(k) for k in ('iso', 'shutter')}, 'shots': s.get('shots_per_plane'),
                           'approach': s['plan'].get('approach')}
        save()
        log('after | phase', s['phase'], 'connected', s['connected'], 'camera', s['power']['camera']['on'], 'light',
            s['power']['light']['on'], 'manage power', s['power']['manage_stack'], '| approach', s['plan'].get('approach'))
    except Exception as err:                         # say so loudly: the rig may not be as found
        log('RESTORE FAILED:', repr(err))
        raise
