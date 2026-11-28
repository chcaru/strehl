"""E2 probe: one frame at several defocus offsets, to choose the white ladder's position.
Also switches managed power off (so no capture toggles the light) and notes it."""
import json
import sys
import time

import rig
from rig import bench

s = rig.settled()
if s['power'].get('manage_stack'):
    bench.cmd('power_plan', enabled=False)
    s = rig.settled()
    rig.note({'label': 'power_plan', 'enabled': False})
print('manage_stack', s['power'].get('manage_stack'), 'light', s['power']['light'])
positions = [int(a) for a in sys.argv[2:]]
shutter = int(sys.argv[1])
rig.exposure(100, shutter)
rig.focus(positions[0] - 128)
s = rig.settled()
expected = s['sequence_id'] + 1
bench.cmd('capture_positions', positions=positions, keep_power_on=True)
s = bench.wait(lambda a: a['sequence_id'] == expected and a['phase'] in ('complete', 'fault', 'stopped')
               and not a['busy'], 600)
assert s['phase'] == 'complete', s['message']
bench.wait(lambda a: (a['storage'] or {}).get('pending_frames', 0) == 0, 300)
s = bench.state()
path = s['storage']['receipt']['path']
folder = path.replace(chr(92) * 2 + '?' + chr(92), '').rsplit(chr(92), 1)[0]
rig.note({'label': 'defocus-probe', 'folder': folder, 'positions': positions, 'shutter': shutter})
print(folder, 'light', s['power']['light'])
