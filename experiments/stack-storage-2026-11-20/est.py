"""The study's code-length estimator: what an adaptive arithmetic coder would spend.

Two parts, both decodable (they use only data a decoder already has, plus counted side
information):

1. `predict`: a least-squares linear predictor fitted per tile and per CFA site over a list
   of taps. A tap is (source, dy, dx) in full-mosaic coordinates; source 0 is the frame being
   coded (taps must then be causal in raster order), other sources are frames the decoder
   already holds (any offset). The weights are side information: 16 bits per weight per tile
   and site are charged.
2. `cost`: an adaptive context model over the residuals, in raster order per site plane.
   Contexts: energy of the already-coded neighbours' residuals (8 bins), local gradient of
   already-coded same-site neighbours (8 bins), level (4 bins). Each context tracks the
   residual's variance relative to the noise model's variance at the predicted level, its
   bias, and the weights of a mixture of an integer-binned Gaussian, logistic and Laplace of
   that variance. The cost of a sample is -log2 of the mixture's probability of the integer
   actually seen: the ideal code length, which an arithmetic or ANS coder reaches within
   about 1 %.
"""
import math

import numba as nb
import numpy as np

BLACK, GAIN, READ = 512.0, 0.4040, 1.334
PAD = 8


def sigma_raw(p):
    """The product's noise sigma (DN) at raw level `p` (ISO 100 A7CR)."""
    return np.sqrt(GAIN * np.maximum(p - BLACK, 0.0) + READ * READ).astype(np.float32)


def padded(a):
    return np.pad(a.astype(np.float32), PAD, mode='edge')


def predict(sources, taps, tile=512, sigma=sigma_raw, ridge=1e-7, shifts=None):
    """Tile-wise weighted least-squares prediction of sources[0] (float32, PADded by `padded`).

    `shifts`: {source index: int array (tiles_y, tiles_x, 2) of (dy, dx)} moves that source's
    taps per tile (motion compensation; |shift| + tap offset must stay within PAD; 8 bits
    per tile are charged for each).

    Returns (prediction for the unpadded frame, bits of side information).
    """
    cur = sources[0]
    H, W = cur.shape[0] - 2 * PAD, cur.shape[1] - 2 * PAD
    out = np.empty((H, W), dtype=np.float32)
    k = len(taps) + 1
    side = 0
    shifts = shifts or {}
    for ty in range(0, H, tile):
        for tx in range(0, W, tile):
            side += 8 * len(shifts)
            for py in (0, 1):
                for px in (0, 1):
                    ys = slice(PAD + ty + ((py - ty) % 2), PAD + min(ty + tile, H), 2)
                    xs = slice(PAD + tx + ((px - tx) % 2), PAD + min(tx + tile, W), 2)
                    t = cur[ys, xs]
                    shape = t.shape
                    n = t.size
                    R = np.empty((n, k), dtype=np.float32)
                    R[:, 0] = 1.0
                    for i, (s, dy, dx) in enumerate(taps):
                        src = sources[s]
                        if s in shifts:
                            sy, sx = shifts[s][ty // tile, tx // tile]
                            dy, dx = dy + int(sy), dx + int(sx)
                        R[:, i + 1] = src[ys.start + dy:ys.stop + dy:2, xs.start + dx:xs.stop + dx:2].reshape(-1)
                    tv = t.reshape(-1)
                    mu = float(tv.mean())
                    w = (1.0 / np.square(sigma(tv))).astype(np.float32)
                    Rc = R.copy()
                    Rc[:, 1:] -= mu
                    Rw = Rc * w[:, None]
                    A = (Rw.T.astype(np.float64) @ Rc.astype(np.float64))
                    b = Rw.T.astype(np.float64) @ (tv.astype(np.float64) - mu)
                    A[np.diag_indices(k)] += ridge * np.trace(A) / k
                    beta = np.linalg.solve(A, b)
                    # weights as stored: 16 bits each (1/4096 steps), intercept in 1/16 DN
                    beta[1:] = np.round(beta[1:] * 4096) / 4096
                    beta[0] = np.round(beta[0] * 16) / 16
                    p = Rc.astype(np.float64) @ beta + mu
                    out[ys.start - PAD:ys.stop - PAD:2, xs.start - PAD:xs.stop - PAD:2] = p.reshape(shape).astype(np.float32)
                    side += 16 * k
    return out, side


def fixed4(cur):
    """Format 1/2's predictor: the floor mean of the four causal same-site neighbours."""
    H, W = cur.shape[0] - 2 * PAD, cur.shape[1] - 2 * PAD
    s = (cur[PAD:PAD + H, PAD - 2:PAD - 2 + W] + cur[PAD - 2:PAD - 2 + H, PAD:PAD + W]
         + cur[PAD - 2:PAD - 2 + H, PAD - 2:PAD - 2 + W] + cur[PAD - 2:PAD - 2 + H, PAD + 2:PAD + 2 + W])
    return np.floor(s / 4).astype(np.float32)


SAME = [(0, 0, -2), (0, 0, -4), (0, -2, -2), (0, -2, 0), (0, -2, 2), (0, -4, 0), (0, -2, -4), (0, -2, 4), (0, -4, -2), (0, -4, 2)]
CROSS = ([(0, 0, d) for d in (-1, -2, -3, -4)] + [(0, -1, d) for d in range(-3, 4)] + [(0, -2, d) for d in range(-3, 4)]
         + [(0, -3, d) for d in (-1, 0, 1)] + [(0, -4, 0)])


def window(src, radius=2):
    return [(src, dy, dx) for dy in range(-radius, radius + 1) for dx in range(-radius, radius + 1)]


@nb.njit(cache=True)
def _sf_logistic(t, s):
    z = t / s
    if z > 40.0:
        return math.exp(-z)
    if z < -40.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(z))


@nb.njit(cache=True)
def _probs(d, sd):
    """P(integer bin at distance d from the centre) under Gaussian, logistic, Laplace of sd."""
    a = abs(d)
    lo, hi = a - 0.5, a + 0.5
    r2 = sd * 1.4142135623730951
    if lo > 0:
        pg = 0.5 * (math.erfc(lo / r2) - math.erfc(hi / r2))
    else:
        pg = 0.5 * (math.erf(hi / r2) + math.erf(-lo / r2))
    s = sd * 0.5513288954217921
    pl = _sf_logistic(lo, s) - _sf_logistic(hi, s)
    b = sd * 0.7071067811865476
    if lo >= 0:
        pp = 0.5 * (math.exp(-lo / b) - math.exp(-hi / b))
    else:
        pp = 1.0 - 0.5 * (math.exp(lo / b) + math.exp(-hi / b))
    return pg, pl, pp


@nb.njit(cache=True)
def _cost_plane(x, p, sm):
    h, w = x.shape
    NA, NG, NL = 8, 8, 4
    nctx = NA * NG * NL
    s2 = np.full(nctx, 1.3 * 4.0)
    n = np.full(nctx, 4.0)
    bs = np.zeros(nctx)
    bn = np.full(nctx, 4.0)
    wt = np.full((nctx, 3), 1.0 / 3.0)
    e = np.zeros((h, w), dtype=np.float32)
    ta = np.array([0.35, 0.6, 0.85, 1.15, 1.6, 2.6, 6.0])
    tg = np.array([0.55, 0.8, 1.05, 1.35, 1.8, 2.8, 6.0])
    tl = np.array([3.0, 12.0, 30.0])
    total = 0.0
    for y in range(h):
        for xx in range(w):
            sg = sm[y, xx]
            act = 0.0
            cnt = 0.0
            g = 0.0
            if xx >= 1:
                act += e[y, xx - 1] ** 2
                cnt += 1.0
            if xx >= 2:
                act += 0.5 * e[y, xx - 2] ** 2
                cnt += 0.5
            if y >= 1:
                act += e[y - 1, xx] ** 2
                cnt += 1.0
                if xx >= 1:
                    act += e[y - 1, xx - 1] ** 2
                    cnt += 1.0
                if xx + 1 < w:
                    act += e[y - 1, xx + 1] ** 2
                    cnt += 1.0
            if y >= 2:
                act += 0.5 * e[y - 2, xx] ** 2
                cnt += 0.5
            if cnt > 0:
                act /= cnt
            else:
                act = 1.0
            if y >= 1 and xx >= 2 and xx + 1 < w:
                g = (abs(x[y, xx - 1] - x[y - 1, xx - 1]) + abs(x[y - 1, xx] - x[y - 1, xx - 1])
                     + abs(x[y - 1, xx] - x[y - 1, xx + 1]) + abs(x[y, xx - 1] - x[y, xx - 2])) / (4.0 * sg)
            else:
                g = 1.0
            ia = 0
            while ia < 7 and act > ta[ia]:
                ia += 1
            ig = 0
            while ig < 7 and g > tg[ig]:
                ig += 1
            il = 0
            while il < 3 and sg > tl[il]:
                il += 1
            c = (ia * NG + ig) * NL + il
            sd = sg * math.sqrt(s2[c] / n[c])
            if sd < 0.05:
                sd = 0.05
            bias = sg * bs[c] / bn[c]
            raw = x[y, xx] - p[y, xx]
            d = raw - bias
            pg, pl, pp = _probs(d, sd)
            pm = wt[c, 0] * pg + wt[c, 1] * pl + wt[c, 2] * pp
            if pm < 1e-9:
                pm = 1e-9  # an escape: 30 bits
                total += 30.0
            else:
                total -= math.log2(pm)
                w0 = wt[c, 0] * pg / pm
                w1 = wt[c, 1] * pl / pm
                w2 = wt[c, 2] * pp / pm
                wt[c, 0] = 0.998 * w0 + 0.002 / 3
                wt[c, 1] = 0.998 * w1 + 0.002 / 3
                wt[c, 2] = 0.998 * w2 + 0.002 / 3
            en = raw / sg
            dn = d / sg
            q = dn * dn
            if q > 400.0:
                q = 400.0
            s2[c] += q
            n[c] += 1.0
            if n[c] > 2048.0:
                s2[c] *= 0.5
                n[c] *= 0.5
            if en > 20.0:
                en = 20.0
            if en < -20.0:
                en = -20.0
            bs[c] += en
            bn[c] += 1.0
            if bn[c] > 2048.0:
                bs[c] *= 0.5
                bn[c] *= 0.5
            e[y, xx] = dn
    return total


@nb.njit(parallel=True, cache=True)
def _cost4(x, p, sm):
    out = np.zeros(4)
    for i in nb.prange(4):
        py, px = i // 2, i % 2
        out[i] = _cost_plane(np.ascontiguousarray(x[py::2, px::2]), np.ascontiguousarray(p[py::2, px::2]),
                             np.ascontiguousarray(sm[py::2, px::2]))
    return out


def cost(x, p, sigma=sigma_raw):
    """Bits per site plane (R, G1, G2, B order of the 2x2 cell) to code integer frame `x` given prediction `p`."""
    return _cost4(x.astype(np.float32), p.astype(np.float32), sigma(p))


def entropy0(res):
    """Zeroth-order empirical entropy (bits/sample) of integer residuals: what a static code per frame reaches."""
    r = np.asarray(res).astype(np.int64).ravel()
    r -= r.min()
    h = np.bincount(r)
    h = h[h > 0] / r.size
    return float(-(h * np.log2(h)).sum())
