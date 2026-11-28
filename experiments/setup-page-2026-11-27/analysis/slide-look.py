"""Restore one frame of a run, write a small PNG overview and keep the green plane as .npy."""
import pathlib
import subprocess
import sys

import numpy as np
import rawpy
from PIL import Image

TOOL = r'C:\dev\blog\death-of-software\projects\strehl\target\release\strehl-raw-archive.exe'
run = pathlib.Path(sys.argv[1])
name = sys.argv[2]
out = pathlib.Path(sys.argv[3])
work = pathlib.Path(r'C:\strehl-scratch\calib-page\tmp-raw') / 'look'
work.mkdir(parents=True, exist_ok=True)
subprocess.run([TOOL, 'restore', str(run / (name + '.straw')), '--output-dir', str(work)], check=True, capture_output=True)
with rawpy.imread(str(work / name)) as raw:
    img = raw.raw_image_visible.copy()
    black = float(np.mean(raw.black_level_per_channel))
(work / name).unlink()
g = (img[0::2, 1::2].astype(np.float32) + img[1::2, 0::2].astype(np.float32)) / 2 - black
np.save(out.with_suffix('.npy'), g)
h, w = g.shape
small = g[:h // 4 * 4, :w // 4 * 4].reshape(h // 4, 4, w // 4, 4).mean((1, 3))
top = np.percentile(small, 99.5)
im = (np.clip(small / top, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
Image.fromarray(im).save(out.with_suffix('.png'))
print('green plane', g.shape, 'p50', float(np.median(g)), 'p99.5', float(top), '->', out.with_suffix('.png'))
