"""Rig helper for the capture investigation. Prints no keys.

  rig.py on            camera on, wait until connected, print the USB link
  rig.py off           light off, camera off, manage power on (the owner's setting)
  rig.py light on|off
  rig.py plan on|off   manage power for stacks
  rig.py ec on|off     error correction
  rig.py show
  rig.py preview FILE  save the live preview JPEG
  rig.py stack N STEP [settle_ms]   capture N planes from the current position, STEP apart
  rig.py disconnect | connect
"""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import URL, client, cmd, state, wait, remote  # noqa: E402


def show(s=None, label=''):
    s = s or state()
    p = s['power']
    e = s.get('exposure') or {}
    print(time.strftime('%H:%M:%S'), label, '| phase', s['phase'], 'connected', s['connected'], 'busy', s['busy'],
          'editable', s['editable'], '| camera', p['camera']['on'], p['camera']['watts'], 'W light', p['light']['on'],
          p['light']['watts'], 'W plan', p['manage_stack'], '| usb', s.get('usb_speed_mbps'), 'ec', s.get('error_correction'),
          '| pos', s.get('position'), 'shots', s.get('shots_per_plane'), 'plan', json.dumps(s.get('plan')),
          '| exposure', json.dumps(e)[:200], '|', (s.get('message') or '')[:160], '| failure', s.get('failure'), flush=True)
    return s


def idle(timeout=60):
    return wait(lambda a: not a['busy'], timeout=timeout)


def main():
    op = sys.argv[1]
    if op == 'show':
        s = show()
        print('storage', json.dumps(s.get('storage'))[:600])
    elif op == 'on':
        s = state()
        if not s['connected']:
            if not s['power']['camera']['on']:
                cmd('power', device='camera', on=True)
            s = wait(lambda a: not a['busy'] and a['connected'], timeout=150)
        show(s, 'connected')
    elif op == 'off':
        s = idle()
        if s['power']['light']['on']:
            cmd('power', device='light', on=False)
            s = wait(lambda a: not a['busy'] and not a['power']['light']['on'], timeout=60)
        if s['connected'] and not s['power']['manage_stack']:
            cmd('power_plan', enabled=True)
            s = wait(lambda a: not a['busy'] and a['power']['manage_stack'])
        if s['power']['camera']['on'] or s['connected']:
            cmd('power', device='camera', on=False)
            s = wait(lambda a: not a['busy'] and not a['power']['camera']['on'], timeout=150)
        show(s, 'off')
    elif op == 'light':
        on = sys.argv[2] == 'on'
        cmd('power', device='light', on=on)
        s = wait(lambda a: not a['busy'] and a['power']['light']['on'] is on, timeout=60)
        show(s, 'light')
    elif op == 'plan':
        on = sys.argv[2] == 'on'
        cmd('power_plan', enabled=on)
        show(wait(lambda a: not a['busy'] and a['power']['manage_stack'] is on), 'plan')
    elif op == 'ec':
        on = sys.argv[2] == 'on'
        cmd('error_correction', enabled=on)
        show(wait(lambda a: not a['busy'] and a.get('error_correction') is on), 'ec')
    elif op == 'preview':
        s = wait(lambda a: a['connected'] and a['preview']['fresh'], timeout=20)
        r = client.get(URL + '/api/preview', timeout=7)
        r.raise_for_status()
        pathlib.Path(sys.argv[2]).write_bytes(r.content)
        print('saved', sys.argv[2], len(r.content), 'bytes')
    elif op in ('connect', 'disconnect'):
        cmd(op)
        show(wait(lambda a: not a['busy'] and a['connected'] is (op == 'connect'), timeout=90), op)
    elif op == 'stack':
        n, step = int(sys.argv[2]), int(sys.argv[3])
        s = idle()
        assert s['editable'] and not s['failure'], s['message']
        if len(sys.argv) > 4:
            p = s['plan']
            cmd('settings', step=p['step'], settle_ms=int(sys.argv[4]), approach=p['approach'], capture_timeout_s=p['capture_timeout_s'])
            s = idle()
        start = s['position']
        positions = [start + i * step for i in range(n)]
        if s['start_set'] and s['end_set'] and s['plan']['start'] > s['plan']['end']:
            positions = [start - i * step for i in range(n)]
        seq = s['sequence_id'] + 1
        t0 = time.time()
        cmd('capture_positions', positions=positions)
        wait(lambda a: a['sequence_id'] == seq and a['phase'] == 'capturing', timeout=60)
        s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected') and not a['busy'],
                 timeout=120 + 30 * n)
        show(s, 'stack done in %.1f s' % (time.time() - t0))
        st = s['storage']
        print('storage', json.dumps({k: st.get(k) for k in ('saved_frames', 'pending_frames', 'queue_peak', 'state')}))
        rec = st.get('receipt') or {}
        print('folder', str(pathlib.Path(rec['path']).parent) if rec.get('path') else None)
        print('last receipt', json.dumps({k: rec.get(k) for k in ('bytes', 'wire_bytes', 'upload_seconds', 'upload_MB_per_second', 'wire_MB_per_second', 'storage_bytes')}))
    else:
        raise SystemExit(__doc__)


main()
