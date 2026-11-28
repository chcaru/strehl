"""The last rig block, chained so it runs unattended:

1. wait until the light has been off for the given minutes, switch it on and shoot the
   warm-up burst at once (single shot, 1.3 s, ISO 100, the subject in focus);
2. creep: a fingerprint sweep in live view, then every live frame for 12 s after a move
   of 5000 units from each side;
3. settle ladder: bursts of ten planes 8 units apart at 1/100 s, ISO 3200, with the plan's
   settle at 2000, 100, 250, 500 and 1000 ms, interleaved;
4. restore the plan's settings, the exposure, four-shot, error correction and managed power.

  python e-final.py <light-off unix> <minutes off> <P>
"""
import json
import pathlib
import sys
import time

import rig
from rig import bench

OUT = pathlib.Path('C:/strehl-scratch/calib-page')
off_at = float(sys.argv[1])
minutes = float(sys.argv[2])
P = int(sys.argv[3])
before = json.loads((OUT / 'before.json').read_text())
plan = before['plan']


def preview():
    r = bench.client.get(bench.URL + '/api/preview', timeout=7)
    if r.status_code != 200:
        return None, None
    return r.headers.get('x-preview-generation'), r.content


def focus(target):
    bench.wait(lambda a: a['editable'] and not a['busy'], 60)
    bench.cmd('focus', target=target)
    bench.wait(lambda a: not a['busy'] and a.get('position') == target, 60)


def fresh(folder, count, tag, skip=1, limit=8.0):
    last, _ = preview()
    seen = kept = 0
    end = time.time() + limit
    while kept < count and time.time() < end:
        g, b = preview()
        if b is not None and g != last:
            last = g
            seen += 1
            if seen > skip:
                (folder / ('%s-%d.jpg' % (tag, kept))).write_bytes(b)
                kept += 1
        time.sleep(0.02)


def settings(settle_ms):
    rig.settled()
    bench.cmd('settings', step=plan['step'], settle_ms=settle_ms, approach=plan['approach'],
              capture_timeout_s=plan['capture_timeout_s'])
    rig.settled()


def positions_burst(label, positions, iso, shutter):
    s = rig.exposure(iso, shutter)
    expected = s['sequence_id'] + 1
    began = time.time()
    bench.cmd('capture_positions', positions=positions, keep_power_on=True)
    s = bench.wait(lambda a: a['sequence_id'] == expected and a['phase'] in ('complete', 'fault', 'stopped')
                   and not a['busy'], 600)
    assert s['phase'] == 'complete', s['message']
    bench.wait(lambda a: (a['storage'] or {}).get('pending_frames', 0) == 0, 300)
    s = bench.state()
    path = s['storage']['receipt']['path']
    folder = path.replace(chr(92) * 2 + '?' + chr(92), '').rsplit(chr(92), 1)[0]
    rec = {'label': label, 'folder': folder, 'positions': positions, 'iso': iso, 'shutter': shutter,
           'began_unix': began, 'wall_seconds': time.time() - began}
    rig.note(rec)
    print(json.dumps(rec), flush=True)


try:
    # 1. warm-up from cold
    s = rig.settled()
    assert not s['power']['light']['on'], 'the light is on'
    assert not s['power'].get('manage_stack')
    rig.exposure(100, 851978)
    focus(P - 128)
    focus(P)
    rig.settled()
    wait = off_at + 60 * minutes - time.time()
    print('waiting %.0f s for the light to have been off %.0f min' % (max(wait, 0), minutes), flush=True)
    if wait > 0:
        time.sleep(wait)
    rig.light(True)
    rig.burst('warm-from-cold-1.3s-b', 70, 100, 851978)

    # 2. creep after a long move (live view)
    folder = OUT / 'e6'
    folder.mkdir(exist_ok=True)
    log = []
    focus(P - 64 - 128)
    for p in range(P - 64, P + 65, 4):
        focus(p)
        fresh(folder, 2, 's1-%05d' % p)
    for rep in range(3):
        for kind, start in [('farbelow', P - 5000), ('farabove', P + 5000)]:
            focus(start)
            time.sleep(3.0)
            last, _ = preview()
            bench.wait(lambda a: a['editable'] and not a['busy'], 60)
            t0 = time.time()
            bench.cmd('focus', target=P)
            rows = []
            n = 0
            while time.time() - t0 < 12.0:
                g, b = preview()
                t = time.time()
                if b is not None and g != last:
                    last = g
                    name = 'c-%s-%d-%03d.jpg' % (kind, rep, n)
                    (folder / name).write_bytes(b)
                    rows.append({'name': name, 't': t - t0})
                    n += 1
                time.sleep(0.015)
            log.append({'what': 'creep', 'kind': kind, 'rep': rep, 'frames': rows})
    (folder / 'log.json').write_text(json.dumps({'P': P, 'log': log}, indent=1))
    print('creep recorded', flush=True)

    # 3. settle ladder (RAW, 1/100 s, ISO 3200)
    focus(P - 128)
    focus(P)
    ladder = [P + 8 * k for k in range(10)]
    for settle in [2000, 100, 250, 500, 1000, 2000, 100, 250, 500, 1000, 2000]:
        settings(settle)
        positions_burst('settle-%d' % settle, ladder, 3200, 65636)
    print('settle ladder done', flush=True)
finally:
    s = bench.state()
    if s['connected']:
        try:
            settings(plan['settle_ms'])
            if not bench.state()['power'].get('manage_stack'):
                bench.cmd('power_plan', enabled=True)
                rig.settled()
                rig.note({'label': 'power_plan', 'enabled': True})
        except Exception as e:  # noqa: BLE001
            print('restore failed:', e, flush=True)
    rig.down()
