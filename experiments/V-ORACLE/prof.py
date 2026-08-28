import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

fs = ora.frames_of("flowers-cpl")
t = time.time()
g1, g2 = ora.green_pair(fs[0])
print(f"decode      {time.time() - t:6.2f}s  shape={g1.shape}")
for s in ora.SIGMAS:
    t = time.time()
    ora._blur(g1, s)
    print(f"blur s={s:5.1f}  {time.time() - t:6.2f}s")
t = time.time()
ora.tile_stats(g1, g2, 128)
print(f"tile_stats  {time.time() - t:6.2f}s")
