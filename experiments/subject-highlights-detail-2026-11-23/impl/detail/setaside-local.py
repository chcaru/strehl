"""The subject's diffuse top under local set-aside rules (shd-d-detail, choosing the rule).

  python setaside-local.py <linear master> <subject json>

A Python approximation of image_out/tone-subject.rs: 2 x 2 quads by their mean (the engine
takes the native-site triple), developed linear from the master, the brightest colour; the
outline rasterised with PIL (even-odd by xor). For block sizes, block percentiles, ratios and
neighbourhoods: the share of the subject set aside as brighter than ratio x the local level,
and the p99.9 of the rest; then a desaturation rule. Output: setaside.txt.
"""
import json
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

master, subj = sys.argv[1], sys.argv[2]
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
sat = (q.max(-1) - q.min(-1)) / np.maximum(q.max(-1), 1e-9)


def run(block, pct, ratio, nb):
    bh, bw = -(-qh // block), -(-qw // block)
    lev = np.full((bh, bw), np.nan, np.float32)
    for by in range(bh):
        for bx in range(bw):
            sl = (slice(by * block, (by + 1) * block), slice(bx * block, (bx + 1) * block))
            v = b[sl][m[sl]]
            if v.size * 4 >= block * block:
                lev[by, bx] = np.percentile(v, pct)
    pad = np.pad(lev, nb, constant_values=np.nan)
    loc = np.full_like(lev, np.nan)
    for dy in range(2 * nb + 1):
        for dx in range(2 * nb + 1):
            loc = np.fmax(loc, pad[dy:dy + bh, dx:dx + bw])
    L = np.kron(loc, np.ones((block, block)))[:qh, :qw]
    hi = m & (b > ratio * np.nan_to_num(L, nan=np.inf))
    keep = m & ~hi
    top = np.percentile(b[keep], 99.9)
    return hi.sum() / m.sum(), top


print('subject p99.9 all: %.4f' % np.percentile(b[m], 99.9))
for block, pct, ratio, nb in [(16, 75, 2, 1), (32, 75, 2, 1), (64, 75, 2, 1), (64, 50, 2, 1), (64, 50, 2, 2), (32, 50, 2, 1), (128, 50, 2, 1), (64, 50, 3, 1)]:
    share, top = run(block, pct, ratio, nb)
    print('block %3d pct %d ratio %.1f nb %d: set aside %.3f %%, diffuse top %.4f' % (block, pct, ratio, nb, 100 * share, top))
# desaturation rule: bright and less saturated than half the subject's median saturation
ms = np.median(sat[m])
for k in (2.0, 4.0):
    hi = m & (b > k * np.percentile(b[m], 90)) & (sat < 0.5 * ms)
    keep = m & ~hi
    print('desaturated above %.0f x p90 (sat < %.2f): set aside %.3f %%, top %.4f' % (k, 0.5 * ms, 100 * hi.mean() / m.mean(), np.percentile(b[keep], 99.9)))
