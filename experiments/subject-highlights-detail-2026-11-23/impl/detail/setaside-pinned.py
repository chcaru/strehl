"""The subject's diffuse top with pinned quads set aside as well (shd-d-detail, choosing the rule).

  python setaside-pinned.py <linear master> <subject json> <pinned value>

As setaside-local.py with the shipped local rule (16-quad blocks, 75th percentile, 2 x, 3 x 3),
plus quads whose brightest colour is at or above a fraction of `pinned value` (a pinned
sample's developed level on that master, read off its p99.9: 1.0689 on the A7CR scarab),
dilated by 0, 4 or 16 quads. The master has no raw values, so this stands in for the engine's
test on the camera colours against the saturation ceiling. Output: setaside.txt.
"""
import json
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy import ndimage

master, subj, pin = sys.argv[1], sys.argv[2], float(sys.argv[3])
a = tifffile.imread(master).astype(np.float32)
h, w = a.shape[:2]
q = a[:h // 2 * 2, :w // 2 * 2].reshape(h // 2, 2, w // 2, 2, 3).mean((1, 3))
qh, qw = q.shape[:2]
m = np.zeros((qh, qw), bool)
for r in json.load(open(subj))['rings']:
    im = Image.new('L', (qw, qh), 0)
    ImageDraw.Draw(im).polygon([(x * qw, y * qh) for x, y in r], fill=255)
    m ^= np.array(im) > 0
b = q.max(-1)
block = 16
bh, bw = -(-qh // block), -(-qw // block)
lev = np.full((bh, bw), np.nan, np.float32)
for by in range(bh):
    for bx in range(bw):
        sl = (slice(by * block, (by + 1) * block), slice(bx * block, (bx + 1) * block))
        v = b[sl][m[sl]]
        if v.size * 4 >= block * block:
            lev[by, bx] = np.percentile(v, 75)
pad = np.pad(lev, 1, constant_values=np.nan)
loc = np.full_like(lev, np.nan)
for dy in range(3):
    for dx in range(3):
        loc = np.fmax(loc, pad[dy:dy + bh, dx:dx + bw])
L = np.kron(loc, np.ones((block, block)))[:qh, :qw]
local = m & (b > 2 * np.nan_to_num(L, nan=np.inf))
for frac in (0.95, 0.80, 0.60):
    for dil in (0, 4, 16):
        pinned = b >= frac * pin
        if dil:
            pinned = ndimage.binary_dilation(pinned, iterations=dil)
        hi = m & (local | pinned)
        keep = m & ~hi
        print('pinned at %.2f of the pin, dilated %2d quads: pinned share %.3f %%, set aside %.3f %%, diffuse top %.4f' % (
            frac, dil, 100 * (m & pinned).sum() / m.sum(), 100 * hi.sum() / m.sum(), np.percentile(b[keep], 99.9)))
