"""E2: the exposure ladder at far defocus, light warm. ISO 100 across the range and
past clipping, then other ISO settings for the gain's scaling."""
import sys

import rig

P = int(sys.argv[1]) if len(sys.argv) > 1 else 37750
rig.focus(P - 128)
rig.focus(P)
rig.settled()
for label, iso, shutter in [
    ('white-iso100-0.4s', 100, 262154),
    ('white-iso100-1.3s', 100, 851978),
    ('white-iso100-3.2s', 100, 2097162),
    ('white-iso100-5s', 100, 3276810),
    ('white-iso100-8s', 100, 5242890),
    ('white-iso400-1/3s', 400, 65539),
    ('white-iso400-0.8s', 400, 524298),
    ('white-iso400-1.3s', 400, 851978),
    ('white-iso400-2s', 400, 1310730),
    ('white-iso200-1.6s', 200, 1048586),
    ('white-iso320-1s', 320, 655370),
    ('white-iso800-0.4s', 800, 262154),
]:
    rig.burst(label, 8, iso, shutter)
rig.exposure(100, 851978)
print('done')
