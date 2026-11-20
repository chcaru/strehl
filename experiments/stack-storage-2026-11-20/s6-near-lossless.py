"""S6: calibrated near-lossless storage. A per-sample companding quantiser with step k sigma
(quant.py), k = 0.25, 0.5, 1, 2.

  python s6-near-lossless.py bits RUN FRAME [RUN FRAME ...]   realised bits/px of the codes
  python s6-near-lossless.py stats                            error statistics, bias of a mean of repeats
  python s6-near-lossless.py theory                           the systematic bias of the quantiser against sigma / step

bits: the codes q are coded like raw values were in S4: JPEG-LS and JPEG XL (black boxes),
format 2's predictor with a static code, and the estimator with format 2's predictor (E0)
and with the 22-tap tile predictor (E3). Noise in code units is about 1 / k, plus 1/12 of
quantisation; the estimator's contexts learn the actual scale.

stats (run stack-1794687317465-11226, six repeats of shift position 3): per k, the error
against the original in units of the model sigma, the added variance against the predicted
(k sigma)^2 / 12, and D = mean of the six quantised frames - mean of the six originals: its
mean by level, its variance against prediction, and the correlation of D between two
disjoint halves of the repeats (a deterministic, signal-locked bias would correlate; an
independent error does not).
"""
import math
import sys
import time

import imagecodecs
import numpy as np

import common as c
import est
import quant

c.below_normal()
KS = (0.25, 0.5, 1.0, 2.0)
mode = sys.argv[1]

if mode == 'theory':
    print('systematic bias of a uniform quantiser of step D on a Gaussian of sigma s, as a mean over repeats sees it')
    print('(exact: E[Q(x)] - mu over all phases of mu within a step; in units of sigma)')
    for k in (0.25, 0.5, 1.0, 2.0, 3.0, 4.0):
        mus = np.linspace(0, k, 201)
        qs = np.arange(-60, 61) * k
        worst = 0.0
        rms = 0.0
        for mu in mus:
            lo = (qs - k / 2 - mu) / math.sqrt(2)
            hi = (qs + k / 2 - mu) / math.sqrt(2)
            p = 0.5 * (np.array([math.erf(h) for h in hi]) - np.array([math.erf(l) for l in lo]))
            b = float((p * qs).sum() - mu)
            worst = max(worst, abs(b))
            rms += b * b
        print('   k = step / sigma = %.2f: worst bias %.3e sigma, rms %.3e sigma; added noise sigma x %.4f (+%.2f %%)'
              % (k, worst, math.sqrt(rms / len(mus)), math.sqrt(1 + k * k / 12), 100 * (math.sqrt(1 + k * k / 12) - 1)))
    sys.exit()

if mode == 'stats':
    x0, y0, cw, ch = 32, 20, 9504, 6336
    fs = [3 + 4 * g for g in range(6)]
    orig = np.empty((6, ch, cw), dtype=np.uint16)
    for i, f in enumerate(fs):
        orig[i] = c.cfa_of(c.REPEAT_A, f)[y0:y0 + ch, x0:x0 + cw]
    m0 = orig.mean(axis=0, dtype=np.float64)
    sg = quant.sigma(m0)
    edges = np.array([0, 520, 540, 580, 650, 800, 1100, 1700, 3000, 6000, 16384])
    idx = np.digitize(m0, edges) - 1
    print('run %s frames %s (active area); sigma from the model at the six-frame mean' % (c.REPEAT_A, fs))
    for k in KS:
        code, rec, width = quant.tables(k)
        qd = rec[code[orig]]
        err = qd.astype(np.float32) - orig
        rel = err / sg[None].astype(np.float32)
        print('== k = %.2f: %d codes; error / sigma: mean %+.5f, rms %.4f (predicted k / sqrt(12) = %.4f), max |error| %.3f sigma = %.0f DN; rms error %.2f DN'
              % (k, int(code.max()) + 1, rel.mean(dtype=np.float64), math.sqrt(float((rel ** 2).mean(dtype=np.float64))), k / math.sqrt(12), np.abs(rel).max(), np.abs(err).max(), math.sqrt(float((err ** 2).mean(dtype=np.float64)))))
        D = qd.mean(axis=0, dtype=np.float64) - m0
        Da = qd[0::2].mean(axis=0, dtype=np.float64) - orig[0::2].mean(axis=0, dtype=np.float64)
        Db = qd[1::2].mean(axis=0, dtype=np.float64) - orig[1::2].mean(axis=0, dtype=np.float64)
        pred = (k * sg) ** 2 / 12 / 6
        wq = width[code[np.rint(m0).astype(np.int64)]].astype(np.float64)
        print('   bin width at the pixel means: mean %.2f DN = %.3f sigma (k %.2f); exact added variance (w^2 - 1) / 12 is %.4f of (k sigma)^2 / 12; stored exactly (width 1): %.2f %% of pixels'
              % (wq.mean(), (wq / sg).mean(), k, ((wq * wq - 1) / 12).mean() / ((k * sg) ** 2 / 12).mean(), 100 * (wq == 1).mean()))
        print('   D = mean6(quantised) - mean6(original): mean %+.5f DN, variance / predicted %.4f; correlation of D between halves (3 + 3 frames) %+.5f'
              % (D.mean(), (D ** 2).mean() / pred.mean(), np.corrcoef(Da.ravel()[::7], Db.ravel()[::7])[0, 1]))
        row = []
        for b in range(len(edges) - 1):
            sel = idx == b
            if sel.sum() < 20000:
                continue
            se = math.sqrt(float(pred[sel].mean()) / float(sel.sum()))
            row.append('[%d,%d) %+.4f DN (+-%.4f, %.1f se; %+.5f sigma)' % (edges[b], edges[b + 1], D[sel].mean(), se, D[sel].mean() / se, D[sel].mean() / sg[sel].mean()))
        print('   mean of D by raw level: ' + ' | '.join(row))
        del qd, err, rel, D, Da, Db
    sys.exit()

pairs = [(sys.argv[i], int(sys.argv[i + 1])) for i in range(2, len(sys.argv) - 1, 2)]
for run, frame in pairs:
    cfa = c.cfa_of(run, frame)
    H, W = cfa.shape
    px = H * W
    print('== %s frame %d' % (run, frame), flush=True)
    for k in KS:
        code, rec, width = quant.tables(k)
        q = code[cfa]
        s0 = math.sqrt(1.0 / (k * k) + 1.0 / 12.0)
        wmean = float(width[q[::4, ::4]].mean())

        def const(p, s0=s0):
            return np.full(np.shape(p), s0, dtype=np.float32)

        out = []
        planes = [np.ascontiguousarray(q[dy::2, dx::2]) for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))]
        for name, enc in (('JPEG-LS', lambda a: imagecodecs.jpegls_encode(a)),
                          ('JXL e3', lambda a: imagecodecs.jpegxl_encode(a, lossless=True, effort=3, numthreads=1)),
                          ('JXL e7', lambda a: imagecodecs.jpegxl_encode(a, lossless=True, effort=7, numthreads=1))):
            if name == 'JXL e7' and k not in (1.0,):
                continue
            try:
                out.append('%s %.3f' % (name, 8.0 * sum(len(enc(a)) for a in planes) / px))
            except Exception as e:  # noqa: BLE001
                out.append('%s failed (%s)' % (name, str(e)[:40]))
        cur = est.padded(q)
        x = q.astype(np.int32)
        p0 = est.fixed4(cur)
        res = x - p0.astype(np.int32)
        out.append('f2 predictor static %.3f' % (sum(est.entropy0(res[dy::2, dx::2]) for dy, dx in ((0, 0), (0, 1), (1, 0), (1, 1))) / 4))
        out.append('E0 %.3f' % (est.cost(x, p0, sigma=const).sum() / px))
        p, side = est.predict([cur], list(est.CROSS), 512, sigma=const)
        e3 = (est.cost(x, p, sigma=const).sum() + side) / px
        out.append('E3 %.3f' % e3)
        ideal = math.log2(s0 * math.sqrt(2 * math.pi * math.e))
        print('   k = %.2f (%4d codes, mean bin width %.1f DN): bits/px  %s | noise-only entropy of a code at the nominal step %.3f | E3 = %.2f MB for the strip'
              % (k, int(code.max()) + 1, wmean, ' | '.join(out), ideal, e3 * px / 8e6), flush=True)
