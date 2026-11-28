"""E3: the light's warm-up from cold. Lens to the subject (from below), light on,
then one burst of single-shot frames at the plan's exposure."""
import sys
import time

import rig

P = int(sys.argv[1]) if len(sys.argv) > 1 else 32750
N = int(sys.argv[2]) if len(sys.argv) > 2 else 70
rig.exposure(100, 851978)
rig.focus(P - 128)
rig.focus(P)
rig.settled()
rig.light(True)
t = time.time()
rig.burst('warm-from-cold-1.3s', N, 100, 851978)
print('burst began', time.time() - t)
