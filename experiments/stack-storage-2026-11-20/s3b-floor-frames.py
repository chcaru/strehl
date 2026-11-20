"""S3b: (1) the repeated run again, restricted to FLAT pixels (the run turned out not to be
static: consecutive-difference correlations of -0.30 to +0.18 say the scene moved between
groups, so detail pixels carry motion in their temporal variance); (2) the oracle floor of
single frames of real stacks from the product's noise model.

Floor of a single frame: sum over pixels of the entropy of integer-binned Gaussian noise at
the model's sigma for that pixel's level. The level is the 5x5 same-colour box mean of the
frame itself (it enters only through log sigma^2, which is smooth in level: a level error of
10 % moves a pixel's floor by 0.07 bits, and the errors have both signs). The floor counts
NOTHING for scene detail or fixed pattern, so every real coder sits above it. A second
column scales the model variance by the temporal/model ratio measured on this body
(2026-11-16: 0.93-0.97 red and green, 0.86-0.95 blue at 2 plane px; mid values used).
"""
import math

import cv2
import numpy as np

import common as c

c.below_normal()
BLACK, GAIN, READ = 512.0, 0.4040, 1.334
CROP = (32, 20, 9504, 6336)
KAPPA = {'R': 0.0030, 'G1': 0.0035, 'G2': 0.0035, 'B': 0.0040}
RATIO = {'R': 0.95, 'G1': 0.95, 'G2': 0.95, 'B': 0.90}
NAMES = {(0, 0): 'R', (0, 1): 'G1', (1, 0): 'G2', (1, 1): 'B'}
x0, y0, cw, ch = CROP


def model_var(s):
    return GAIN * np.maximum(s, 0.0) + READ * READ


def bits(var):
    return 0.5 * np.log2(2 * math.pi * math.e * (var + 1.0 / 12.0))


print('== (1) repeated run %s, shift position 3 (frames 3, 7, ..., 23), flat pixels only' % c.REPEAT_A)
fs = [3 + 4 * g for g in range(6)]
stack = np.empty((6, ch, cw), dtype=np.float32)
for i, f in enumerate(fs):
    stack[i] = c.cfa_of(c.REPEAT_A, f)[y0:y0 + ch, x0:x0 + cw]
sig = stack - BLACK
level = sig.reshape(6, -1)[:, ::97].mean(axis=1)
sig /= (level / level.mean())[:, None, None].astype(np.float32)
mean = sig.mean(axis=0)
var = sig.var(axis=0, ddof=1)
edges = np.array([-50, 25, 50, 100, 200, 400, 800, 1600, 3200, 6400, 16000], dtype=np.float64)
for (dy, dx), name in NAMES.items():
    m = mean[dy::2, dx::2]
    v = var[dy::2, dx::2]
    sm = np.sqrt(model_var(m))
    dev = np.zeros_like(m)
    for sy, sx in ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        dev = np.maximum(dev, np.abs(np.roll(m, (sy, sx), axis=(0, 1)) - m))
    flat = dev < 1.0 * sm  # the mean of six has sigma/sqrt(6); a neighbour difference 0.58 sigma
    flat[:2] = flat[-2:] = False
    flat[:, :2] = flat[:, -2:] = False
    idx = np.clip(np.digitize(m, edges) - 1, 0, len(edges) - 2)
    row = []
    for b in range(len(edges) - 1):
        sel = (idx == b) & flat
        if sel.sum() < 5000:
            continue
        row.append('[%d,%d) n=%d ratio %.3f' % (edges[b], edges[b + 1], sel.sum(), v[sel].mean() / model_var(m[sel]).mean()))
    print('   %-2s flat %.1f %% of pixels | measured/model temporal variance: %s' % (name, 100 * flat.mean(), ' | '.join(row)))
del stack, sig, mean, var

print('== (2) oracle floor of single frames (active area), bits/px: model | model x measured ratio | + what the fixed pattern costs a coder without a gain map | level percentiles (DN above black) 5/50/95 %')
FRAMES = [(c.REPEAT_A, 1), (c.SCARAB, 1), (c.SCARAB, 201), (c.SCARAB, 401), (c.SCARAB, 601), (c.SCARAB, 781),
          (c.STACK107, 1), (c.STACK107, 201), (c.STACK107, 425)]
keep = {(c.REPEAT_A, 1), (c.SCARAB, 1), (c.SCARAB, 401)}
for run, frame in FRAMES:
    cfa = c.cfa_of(run, frame)[y0:y0 + ch, x0:x0 + cw].astype(np.float32) - BLACK
    tot = [0.0, 0.0, 0.0]
    per = []
    sat = float((cfa >= 16383 - BLACK).mean())
    for (dy, dx), name in NAMES.items():
        p = cfa[dy::2, dx::2]
        lv = cv2.blur(p, (5, 5), borderType=cv2.BORDER_REFLECT)
        mv = model_var(lv.astype(np.float64))
        a = float(bits(mv).mean())
        b = float(bits(mv * RATIO[name]).mean())
        fp = float((0.5 * np.log2(1 + (KAPPA[name] * np.maximum(lv, 0)) ** 2 / (mv * RATIO[name]))).mean())
        tot[0] += a / 4
        tot[1] += b / 4
        tot[2] += fp / 4
        per.append('%s %.3f' % (name, b))
    q = np.percentile(cfa[::8, ::8], [5, 50, 95])
    px = cw * ch
    print('   %s frame %4d: %.3f | %.3f | +%.4f | %5.0f %5.0f %5.0f | saturated %.3f %% | per site (ratio-scaled): %s | floor = %.1f MB for the active area'
          % (run[-10:], frame, tot[0], tot[1], tot[2], q[0], q[1], q[2], 100 * sat, ', '.join(per), tot[1] * px / 8e6))
    if (run, frame) not in keep:
        c.drop(run, frame)
