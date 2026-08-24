import glob
import os
import time

import numpy as np
import rawpy

DIR = r"D:\personal\macro\bee-3-cpl"
files = sorted(glob.glob(os.path.join(DIR, "*.ARW")))
t0 = time.time()
for f in files[:5]:
    with rawpy.imread(f) as r:
        raw = r.raw_image_visible
        h, w = raw.shape
        c = r.raw_colors_visible
        bl = r.black_level_per_channel
        wl = r.white_level
dt = (time.time() - t0) / 5
print("visible shape %dx%d  colors %s  black %s  white %s"
      % (w, h, c.shape, bl, wl))
print("mean decode %.3f s/frame -> %d frames = %.0f s single-threaded"
      % (dt, len(files), dt * len(files)))
print("cpu count", os.cpu_count())
