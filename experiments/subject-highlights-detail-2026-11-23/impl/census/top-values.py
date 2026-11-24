"""Where does a long frame's top end sit? Counts of raw values near white.

  python top-values.py <archive tool> <.ARW.straw> <scratch dir>
"""
import pathlib
import subprocess
import sys

import numpy as np
import rawpy

tool, src, work = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
work.mkdir(parents=True, exist_ok=True)
subprocess.run([tool, 'restore', str(src), '--output-dir', str(work)], check=True, capture_output=True)
name = src.name[:-len('.straw')]
with rawpy.imread(str(work / name)) as raw:
    img = raw.raw_image_visible.copy()
    white = raw.white_level
    black = raw.black_level_per_channel
(work / name).unlink()
print('white_level', white, 'black', black, 'max', int(img.max()))
vals, counts = np.unique(img[img >= 14000], return_counts=True)
top = sorted(zip(counts, vals), reverse=True)[:12]
print('most common values >= 14000:', [(int(v), int(c)) for c, v in top])
for lo in (14000, 15000, 15200, 15300, 15340, 15358, 15360, 16000, 16380):
    print('>= %5d: %d' % (lo, int((img >= lo).sum())))
