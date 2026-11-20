"""S4: lossless intra-frame candidates on the same frames.

  python s4-intra.py RUN FRAME [RUN FRAME ...]

Per frame (whole 9600 x 6376 strip): the oracle floor (noise model), format 2 as packed today,
JPEG-LS (CharLS) and JPEG XL lossless (libjxl) on the four site planes through imagecodecs
(black boxes; one thread, timed), and this study's estimator with progressively better
predictors:

  E0  format 2's predictor (mean of four same-site causal neighbours) + adaptive contexts
  E1  least squares over 10 same-site causal taps, one set of weights per site per frame
  E2  least squares over 22 causal taps of every site (cross-colour), per frame
  E3  E2 with weights per 512 px tile
  E4  E2 with weights per 256 px tile
"""
import math
import os
import subprocess
import sys
import time

import cv2
import imagecodecs
import numpy as np

import common as c
import est

c.below_normal()
pairs = [(sys.argv[i], int(sys.argv[i + 1])) for i in range(1, len(sys.argv) - 1, 2)]
RATIO = [0.95, 0.95, 0.95, 0.90]


def floor_bits(cfa):
    tot = 0.0
    for i, (dy, dx) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
        p = cfa[dy::2, dx::2].astype(np.float32)
        lv = cv2.blur(p, (5, 5), borderType=cv2.BORDER_REFLECT)
        var = (est.GAIN * np.maximum(lv - est.BLACK, 0) + est.READ ** 2).astype(np.float64) * RATIO[i]
        tot += float((0.5 * np.log2(2 * math.pi * math.e * (var + 1 / 12))).sum())
    return tot


def timed(f, *a, **k):
    t = time.perf_counter()
    r = f(*a, **k)
    return r, time.perf_counter() - t


for run, frame in pairs:
    arw = c.restore(run, frame)
    cfa = c.cfa_of(run, frame)
    H, W = cfa.shape
    px = H * W
    other = os.path.getsize(arw) - 2 * px
    print('== %s frame %d (%d x %d = %.2f MP; %d non-strip bytes)' % (run, frame, W, H, px / 1e6, other), flush=True)

    def line(name, bits, note=''):
        print('   %-46s %6.3f bits/px  %6.2f MB CFA  %s' % (name, bits / px, bits / 8e6, note), flush=True)

    line('oracle floor (noise model x measured ratio)', floor_bits(cfa))
    out2 = c.SCRATCH / ('s4-%s-%06d.ARW.straw' % (run, frame))
    if out2.exists():
        out2.unlink()
    r = subprocess.run([str(c.EXE), 'pack', str(arw), str(out2)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    f2 = os.path.getsize(out2)
    out2.unlink()
    line('format 2 as packed (strip share)', 8.0 * (f2 - other), 'whole archive %.2f MB; upper bound for the strip: non-strip bytes counted raw' % (f2 / 1e6))
    planes = [np.ascontiguousarray(cfa[dy::2, dx::2]) for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))]
    for name, enc, dec in (
        ('JPEG-LS (CharLS) per site plane', lambda a: imagecodecs.jpegls_encode(a), imagecodecs.jpegls_decode),
        ('JPEG XL lossless effort 3 per site plane', lambda a: imagecodecs.jpegxl_encode(a, lossless=True, effort=3, numthreads=1), lambda b: imagecodecs.jpegxl_decode(b, numthreads=1)),
        ('JPEG XL lossless effort 7 per site plane', lambda a: imagecodecs.jpegxl_encode(a, lossless=True, effort=7, numthreads=1), lambda b: imagecodecs.jpegxl_decode(b, numthreads=1)),
    ):
        try:
            size = 0
            te = td = 0.0
            for a in planes:
                b, t1 = timed(enc, a)
                d, t2 = timed(dec, b)
                assert np.array_equal(d, a)
                size += len(b)
                te += t1
                td += t2
            line(name, 8.0 * size, 'encode %.0f MP/s, decode %.0f MP/s (one thread)' % (px / 1e6 / te, px / 1e6 / td))
        except Exception as e:  # noqa: BLE001
            print('   %-46s failed: %s' % (name, str(e)[:120]), flush=True)
    cur = est.padded(cfa)
    x = cfa.astype(np.int32)
    p0 = est.fixed4(cur)
    res = x - p0.astype(np.int32)
    line('format 2 predictor, static entropy of residuals', sum(est.entropy0(res[dy::2, dx::2]) for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))) * px / 4,
         'one ideal static code per site per frame')
    b, t = timed(est.cost, x, p0)
    line('E0 format 2 predictor + adaptive contexts', b.sum(), 'per site %s; %.0f s' % (np.round(b / (px / 4), 3), t))
    for name, taps, tile in (('E1 LS 10 same-site taps, per frame', est.SAME, 1 << 20), ('E2 LS 22 cross-colour taps, per frame', est.CROSS, 1 << 20),
                             ('E3 LS 22 cross-colour taps, 512 px tiles', est.CROSS, 512), ('E4 LS 22 cross-colour taps, 256 px tiles', est.CROSS, 256)):
        (p, side), t1 = timed(est.predict, [cur], taps, tile)
        b, t2 = timed(est.cost, x, p)
        line(name, b.sum() + side, 'per site %s; side info %.1f kB; fit %.0f s, model %.0f s' % (np.round(b / (px / 4), 3), side / 8e3, t1, t2))
