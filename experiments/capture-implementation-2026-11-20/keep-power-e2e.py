"""Rig check for the calibration hang (2026-11-20 evening): with "manage power" on, a
capture_positions request with keep_power_on leaves the camera connected afterwards (the
desktop's step calibration then sets four-shot again). Captures 2 single RAWs at the current
position, prints the folder (delete it with clean-runs.py) and the power state. Prints no keys.
  python keep-power-e2e.py"""
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'outputs/shelly-power-2026-11-18'))
from bench import cmd, state, wait  # noqa: E402

s = wait(lambda a: not a['busy'] and a['connected'] and a['editable'], timeout=60)
assert s['power']['manage_stack'], 'turn manage power on first'
shots = s['shots_per_plane']
if shots != 1:
    cmd('pixel_shift', shots=1)
    s = wait(lambda a: not a['busy'] and a['editable'] and a['shots_per_plane'] == 1, timeout=60)
seq = s['sequence_id'] + 1
pos = s['position']
t0 = time.time()
cmd('capture_positions', positions=[pos, pos], keep_power_on=True)
s = wait(lambda a: a['sequence_id'] == seq and a['phase'] in ('complete', 'stopped', 'fault', 'disconnected')
         and not a['busy'], timeout=180)
time.sleep(5)  # a power-off would have started by now
s = state()
rec = (s.get('storage') or {}).get('receipt') or {}
print(json.dumps({'phase': s['phase'], 'seconds': round(time.time() - t0, 1), 'connected': s['connected'],
                  'editable': s['editable'], 'camera_on': s['power']['camera']['on'],
                  'light_on': s['power']['light']['on'], 'manage': s['power']['manage_stack'],
                  'folder': str(pathlib.Path(rec['path']).parent) if rec.get('path') else None}))
if shots != 1:
    cmd('pixel_shift', shots=shots)
    wait(lambda a: not a['busy'] and a['shots_per_plane'] == shots, timeout=60)
