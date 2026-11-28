"""E1b: darks with the light off (managed power off, so no capture wakes it) and no lens cap."""
import rig
from rig import bench

s = rig.settled()
assert not s['power'].get('manage_stack'), 'managed power is on'
rig.light(False)
s = bench.state()
assert not s['power']['light']['on'], s['power']['light']
for label, iso, shutter in [
    ('dark-off-iso100-1/8000', 100, 73536),
    ('dark-off-iso100-1/1000', 100, 66536),
    ('dark-off-iso100-1/100', 100, 65636),
    ('dark-off-iso100-0.6s', 100, 393226),
    ('dark-off-iso100-2.5s', 100, 1638410),
    ('dark-off-iso320-1/100', 320, 65636),
    ('dark-off-iso400-1/100', 400, 65636),
    ('dark-off-iso3200-1/100', 3200, 65636),
]:
    r = rig.burst(label, 8, iso, shutter)
    assert not r['light']['on'], r['light']
rig.exposure(100, 851978)
print('done')
