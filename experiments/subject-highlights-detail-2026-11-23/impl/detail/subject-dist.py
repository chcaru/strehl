"""The subject's brightest-colour and luminance distribution on a linear master (shd-d-detail).

  python subject-dist.py <linear master> <subject json>

Percentiles of the brightest colour and BT.709 luminance inside the outline (rasterised at
1/8 scale with PIL, even-odd by xor), the frame's luminance percentiles beside them, and the
median saturation (max - min over max) of the subject's brightest 1 % against its middle 20 %
(speculars carry the light's colour: a glossy beetle's sheen is paler than its body).
Output: subject-dist.txt.
"""
import json
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

master, subj = sys.argv[1], sys.argv[2]
a = tifffile.imread(master).astype(np.float32)
h, w = a.shape[:2]
m = np.zeros((h // 8, w // 8), bool)
for r in json.load(open(subj))['rings']:
    im = Image.new('L', (w // 8, h // 8), 0)
    ImageDraw.Draw(im).polygon([(x * w / 8, y * h / 8) for x, y in r], fill=255)
    m ^= np.array(im) > 0
mask = np.zeros((h, w), bool)
big = np.kron(m, np.ones((8, 8), bool))
mask[:big.shape[0], :big.shape[1]] = big[:h, :w]
b = a.max(-1)
lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
sb, sl = b[mask], lum[mask]
print('subject share %.3f' % mask.mean())
for p in (50, 75, 90, 95, 98, 99, 99.5, 99.9, 99.99):
    print('p%-6s bright %.4f lum %.4f | frame lum %.4f' % (p, np.percentile(sb, p), np.percentile(sl, p),
                                                          np.percentile(lum, p)))
top = sb >= np.percentile(sb, 99)
rgb = a[mask][top]
sat = (rgb.max(-1) - rgb.min(-1)) / np.maximum(rgb.max(-1), 1e-6)
mid = (sb >= np.percentile(sb, 40)) & (sb <= np.percentile(sb, 60))
rgbm = a[mask][mid]
satm = (rgbm.max(-1) - rgbm.min(-1)) / np.maximum(rgbm.max(-1), 1e-6)
print('saturation of the brightest 1 %%: median %.3f; of the middle 20 %%: median %.3f' % (np.median(sat), np.median(satm)))
