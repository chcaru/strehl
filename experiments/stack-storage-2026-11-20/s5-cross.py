"""S5: cross-frame lossless prediction, with the SAME estimator as S4 (deltas are like for like).

  python s5-cross.py RUN FIRST_FRAME_OF_GROUP [--map MAP.npy]

The group is frames F..F+3 (one focus plane, four sensor positions); the plane before it is
F-4..F-1. Every variant uses S4's best intra predictor (22 causal cross-colour taps, weights
per 512 px tile and site) and ADDS taps from frames the decoder would already hold:

  I    intra only (S4's E3)
  G    + a 5x5 window (all sites) from each EARLIER shot of the same group
  P    + a 5x5 window from the same shot of the PREVIOUS plane, moved per tile by the even
       shift that best aligns the two frames (searched on 2x2-binned luma, +-6 px)
  GP   both
  M    intra with a per-photosite gain map divided out of every tap and multiplied back into
       the prediction (map given with --map: R, G1, G2, B planes of the active area,
       relative response - 1; tried at three shrink factors)

All side information (16 bits a weight, 8 bits a tile shift) is charged. The map's own
storage is NOT in the per-frame figure; it is reported separately.
"""
import sys
import time

import cv2
import numpy as np

import common as c
import est

c.below_normal()
run = sys.argv[1]
first = int(sys.argv[2])
mapfile = sys.argv[sys.argv.index('--map') + 1] if '--map' in sys.argv else None
only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
TILE = 512
CROP = (32, 20, 9504, 6336)


def luma(a):
    return (a[0::2, 0::2] + a[0::2, 1::2] + a[1::2, 0::2] + a[1::2, 1::2]).astype(np.float32)


def tile_shifts(cur, ref, tile=TILE, reach=3):
    """Per tile, the even (dy, dx) such that ref[y + dy, x + dx] best matches cur[y, x] (SAD on binned luma)."""
    a, b = luma(cur), luma(ref)
    a = cv2.GaussianBlur(a, (0, 0), 1.0)
    b = cv2.GaussianBlur(b, (0, 0), 1.0)
    H, W = cur.shape
    out = np.zeros(((H + tile - 1) // tile, (W + tile - 1) // tile, 2), dtype=np.int64)
    t2 = tile // 2
    for iy in range(out.shape[0]):
        for ix in range(out.shape[1]):
            y0, x0 = iy * t2, ix * t2
            y1, x1 = min(y0 + t2, a.shape[0]), min(x0 + t2, a.shape[1])
            best = None
            for dy in range(-reach, reach + 1):
                for dx in range(-reach, reach + 1):
                    ya, yb = max(y0, -dy, 0), min(y1, a.shape[0] - dy)
                    xa, xb = max(x0, -dx, 0), min(x1, a.shape[1] - dx)
                    if yb - ya < 8 or xb - xa < 8:
                        continue
                    sad = float(np.abs(a[ya:yb, xa:xb] - b[ya + dy:yb + dy, xa + dx:xb + dx]).mean())
                    if best is None or sad < best[0]:
                        best = (sad, dy, dx)
            out[iy, ix] = (2 * best[1], 2 * best[2])
    return out


frames = {f: c.cfa_of(run, f) for f in range(first - 4, first + 4)}
H, W = frames[first].shape
px = H * W
pads = {f: est.padded(a) for f, a in frames.items()}
print('== %s group %d..%d, previous plane %d..%d; tile %d' % (run, first, first + 3, first - 4, first - 1, TILE), flush=True)
totals = {}


def report(shot, name, bits, side, t, extra=''):
    totals.setdefault(name, []).append((bits.sum() + side) / px)
    print('   shot %d  %-34s %6.3f bits/px  %6.2f MB  side %.0f kB  %.0f s  %s'
          % (shot, name, (bits.sum() + side) / px, (bits.sum() + side) / 8e6, side / 8e3, t, extra), flush=True)


for j in range(4):
    f = first + j
    x = frames[f].astype(np.int32)
    cur = pads[f]
    variants = [('I intra', [cur], list(est.CROSS), None)]
    if j >= 1:
        srcs = [cur] + [pads[first + i] for i in range(j)]
        taps = list(est.CROSS)
        for i in range(j):
            taps += est.window(1 + i)
        variants.append(('G + earlier shots of the group', srcs, taps, None))
    sh = tile_shifts(frames[f], frames[f - 4])
    variants.append(('P0 + previous plane, no motion', [cur, pads[f - 4]], list(est.CROSS) + est.window(1), None))
    variants.append(('P + previous plane, tile motion', [cur, pads[f - 4]], list(est.CROSS) + est.window(1), {1: sh}))
    if j >= 1:
        srcs = [cur] + [pads[first + i] for i in range(j)] + [pads[f - 4]]
        taps = list(est.CROSS)
        for i in range(j):
            taps += est.window(1 + i)
        taps += est.window(j + 1)
        variants.append(('GP both', srcs, taps, {j + 1: sh}))
    for name, srcs, taps, shifts in variants:
        if only and name.split()[0] not in only:
            continue
        t = time.perf_counter()
        p, side = est.predict(srcs, taps, TILE, shifts=shifts)
        bits = est.cost(x, p)
        extra = ''
        if shifts:
            s = list(shifts.values())[0]
            extra = 'tile shifts dy [%d, %d] dx [%d, %d], nonzero in %.0f %% of tiles' % (s[..., 0].min(), s[..., 0].max(), s[..., 1].min(), s[..., 1].max(), 100 * (np.abs(s).sum(axis=2) > 0).mean())
        report(j, name, bits, side, time.perf_counter() - t, '%d taps %s' % (len(taps), extra))
    if mapfile and (not only or 'M' in only):
        m = np.load(mapfile, mmap_mode='r')
        x0, y0, cw, ch = CROP
        g = np.zeros((H, W), dtype=np.float32)
        for i, (dy, dx) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
            g[y0 + dy:y0 + ch:2, x0 + dx:x0 + cw:2] = np.asarray(m[i], dtype=np.float32)
        for shrink in (0.3, 0.6, 1.0):
            t = time.perf_counter()
            gg = 1.0 + shrink * g
            xd = est.BLACK + (frames[f].astype(np.float32) - est.BLACK) / gg
            pd, side = est.predict([est.padded(xd)], list(est.CROSS), TILE)
            p = est.BLACK + (pd - est.BLACK) * gg
            bits = est.cost(x, p)
            report(j, 'M intra + gain map x %.1f' % shrink, bits, side, time.perf_counter() - t)
print('== group mean (bits/px over the four shots; shot 0 has no earlier shot, so G and GP average its I or P in)')
base = np.array(totals['I intra'])
for name, v in totals.items():
    v = list(v)
    if name.startswith('G '):
        v = [totals['I intra'][0]] + v
    if name.startswith('GP'):
        v = [totals['P + previous plane, tile motion'][0]] + v
    v = np.array(v)
    if len(v) == 4:
        print('   %-34s %6.3f bits/px  (%+.2f %% against intra)  per shot %s' % (name, v.mean(), 100 * (v.mean() / base.mean() - 1), np.round(v, 3)))
