"""E1: darks with the light off and no lens cap. ISO 100 at three shutters (a leak
shows as a level that grows with time), then a short ISO ladder at 1/100 s."""
import rig

for label, iso, shutter in [
    ('dark-nocap-iso100-1/8000', 100, 73536),
    ('dark-nocap-iso100-0.6s', 100, 393226),
    ('dark-nocap-iso100-2.5s', 100, 1638410),
    ('dark-nocap-iso100-1/100', 100, 65636),
    ('dark-nocap-iso320-1/100', 320, 65636),
    ('dark-nocap-iso400-1/100', 400, 65636),
    ('dark-nocap-iso3200-1/100', 3200, 65636),
]:
    rig.burst(label, 8, iso, shutter)
rig.exposure(100, 851978)
print('done')
