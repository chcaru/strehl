"""Capped darks, door closed (2026-11-27, second run): the spec's Dark shot list in full,
extra shutter speeds at ISO 100, a long exposure, and two bursts with the light on (a cap
in a lit room). Restores and powers down at the end.
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, 'C:/dev/blog/death-of-software/projects/strehl/.claude/worktrees/calibration-page-spec/experiments/setup-page-2026-11-27/rig')
import rig  # noqa: E402
from rig import bench  # noqa: E402

rig.OUT = pathlib.Path('C:/strehl-scratch/setup-polish')
rig.LOG = rig.OUT / 'series.jsonl'

T100, T25 = 65636, 1638410
try:
    rig.up()
    s = rig.settled()
    managed = bool(s['power'].get('manage_stack'))
    if managed:
        bench.cmd('power_plan', enabled=False)
        rig.settled()
    rig.light(False)
    assert not bench.state()['power']['light']['on']
    plan = [('capped-iso100-1/100', 100, T100, 8), ('capped-iso100-2.5s', 100, T25, 8)]
    plan += [('capped-iso%d-1/100' % iso, iso, T100, 8) for iso in (200, 400, 800, 1600, 3200)]
    plan += [('capped-iso%d-1/100' % iso, iso, T100, 8) for iso in (250, 320)]
    plan += [('capped-iso100-1/8000', 100, 73536, 8), ('capped-iso100-1/4000', 100, 69536, 8),
             ('capped-iso100-1/2000', 100, 67536, 8), ('capped-iso100-1/1000', 100, 66536, 8),
             ('capped-iso100-0.6s', 100, 393226, 8), ('capped-iso100-8s', 100, 5242890, 4)]
    for label, iso, shutter, frames in plan:
        r = rig.burst(label, frames, iso, shutter)
        assert not r['light']['on'], r['light']
    rig.light(True)
    time.sleep(5)
    for label, iso, shutter in [('capped-lit-iso100-1/100', 100, T100), ('capped-lit-iso100-2.5s', 100, T25)]:
        r = rig.burst(label, 8, iso, shutter)
        assert r['light']['on'], r['light']
    rig.light(False)
    print('bursts done', flush=True)
finally:
    s = bench.state()
    if s['connected']:
        try:
            rig.settled()
            if not bench.state()['power'].get('manage_stack'):
                bench.cmd('power_plan', enabled=True)
                rig.settled()
        except Exception as e:  # noqa: BLE001
            print('restore failed:', e, flush=True)
    rig.down()
