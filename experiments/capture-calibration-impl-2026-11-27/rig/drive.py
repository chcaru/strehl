"""Live rig run of the calibration pass (spec S1/S2 rig gates).

  python drive.py setup      camera and light on, connect, lens near the subject
  python drive.py open       open Capture in the controlled desktop
  python drive.py calibrate  start the pass
  python drive.py watch      print the pass's state every 5 s until it ends
  python drive.py snap       one snapshot of capture.tools
  python drive.py restore    camera and light off (manage power stays on)
"""
import json
import subprocess
import sys
import time

sys.path.insert(0, 'C:/dev/blog/death-of-software/projects/strehl/outputs/shelly-power-2026-11-18')
import bench  # noqa: E402

REPO = 'C:/dev/blog/death-of-software/projects/strehl'
EXE = 'C:/Users/chris/AppData/Local/Programs/Strehl/Strehl.exe'
SESSION = 'C:/strehl-scratch/rig-1/ready.json'
LOG = 'C:/strehl-scratch/rig-1/watch.jsonl'


def control(args, stdin=None):
    p = subprocess.run(['python', f'{REPO}/scripts/strehl-control.py', '--exe', EXE, '--session-file', SESSION]
                       + args, input=stdin, capture_output=True, text=True, cwd=REPO)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {'error': p.stdout + p.stderr}


def snapshot():
    return control(['snapshot'])


def call(command):
    rev = snapshot()['data']['revision']
    req = json.dumps({'expected_revision': rev, 'command': command})
    return control(['call', '--request', '-'], stdin=req)


def tools(s):
    d = (s.get('data') or {}).get('result') or {}
    cap = (d.get('capture') or {})
    return cap.get('tools') or {}


def main():
    what = sys.argv[1]
    if what == 'setup':
        s = bench.state()
        if not (s['power']['camera'] or {}).get('on'):
            bench.cmd('power', device='camera', on=True)
            time.sleep(3)
            # Switching the camera on starts its connection: wait it out.
            bench.wait(lambda a: not a['busy'], 120)
        if not (s['power']['light'] or {}).get('on'):
            bench.cmd('power', device='light', on=True)
        bench.wait(lambda a: not a['busy'], 60)
        s = bench.state()
        if not s['connected']:
            bench.cmd('connect')
            s = bench.wait(lambda a: a['connected'] and not a['busy'], 90)
        print('connected', s['connected'], 'position', s['position'], 'exposure', s.get('exposure', {}).get('shutter'),
              'shots', s.get('shots_per_plane'), 'light', s['power']['light']['on'])
    elif what == 'focus':
        target = int(sys.argv[2])
        bench.ready()
        bench.cmd('focus', target=target)
        s = bench.wait(lambda a: not a['busy'] and a.get('position') == target, 60)
        print('lens at', s['position'])
    elif what == 'open':
        print(call({'operation': 'open_capture'}))
    elif what == 'calibrate':
        print(call({'operation': 'calibrate'}))
    elif what == 'stop':
        print(call({'operation': 'stop_calibration'}))
    elif what == 'snap':
        print(json.dumps(tools(snapshot()).get('calibration'), indent=1)[:4000])
    elif what == 'watch':
        t0 = time.time()
        last = None
        with open(LOG, 'a') as log:
            while True:
                c = tools(snapshot()).get('calibration') or {}
                p = c.get('pass') or {}
                row = {'t': round(time.time() - t0, 1), 'stage': p.get('stage'), 'calib': c.get('stage'),
                       'light_on': c.get('light_on_seconds'), 'secs': p.get('seconds'), 'sweep': p.get('sweep'), 'busiest': p.get('busiest'),
                       'test_top': p.get('test_top'), 'shutters': p.get('shutters'), 'error': p.get('error')}
                log.write(json.dumps(row) + '\n')
                log.flush()
                key = (row['stage'], row['calib'])
                if key != last:
                    print(json.dumps(row), flush=True)
                    last = key
                if row['stage'] in ('done', 'failed', 'idle') and row['t'] > 5:
                    print(json.dumps(c.get('pass'), indent=1)[:6000])
                    break
                time.sleep(5)
    elif what == 'restore':
        bench.ready()
        bench.cmd('power', device='light', on=False)
        time.sleep(1)
        # The host cuts the camera's power only while connected (it
        # confirms standby first).
        s = bench.state()
        if not s['connected']:
            bench.cmd('connect')
            bench.wait(lambda a: a['connected'] and not a['busy'], 120)
        bench.cmd('power', device='camera', on=False)
        s = bench.wait(lambda a: not a['busy'] and not a['power']['camera']['on'], 120)
        print('light', s['power']['light']['on'], 'camera', s['power']['camera']['on'], 'manage', s['power']['manage_stack'])


if __name__ == '__main__':
    main()
