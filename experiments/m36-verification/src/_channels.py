# shared helpers for M36 verification scripts (channels / worst / Jaccard)
import numpy as np
from scipy.ndimage import sobel, uniform_filter
_G, _RN, _R = 50/436.8, 4.20, 2

def channels(cube):
    cube = np.asarray(cube, np.float32)
    nn, HH, WW = cube.shape
    foc = np.empty_like(cube)
    for i in range(nn):
        gx = sobel(cube[i], axis=1, mode="nearest"); gy = sobel(cube[i], axis=0, mode="nearest")
        foc[i] = uniform_filter(np.hypot(gx, gy), size=2*_R+1, mode="nearest")
    yy, xx = np.mgrid[0:HH, 0:WW]
    tail = np.concatenate([foc[:6], foc[-6:]], 0)
    d2 = tail[2:] - 2*tail[1:-1] + tail[:-2]
    sf = np.sqrt(np.maximum(d2.var(0), 1e-12)/6.0).astype(np.float32)
    fmax, kmx = foc.max(0), foc.argmax(0)
    d = (fmax[None]-foc)/np.maximum(sf, 1e-6)[None]
    lp = -0.5*d.astype(np.float64)**2; lp -= lp.max(0)
    p = np.exp(lp); p /= p.sum(0)
    c2 = np.exp(-(p*np.log(np.maximum(p, 1e-300))).sum(0)).astype(np.float32)
    del d, lp, p
    acc = (fmax[None]-foc) <= sf[None]
    na = acc.sum(0).astype(np.float32)
    vk = _G*np.clip(cube, 0, None) + (_RN*_G)**2
    c1 = (np.sqrt((vk*acc).sum(0))/np.maximum(na, 1)) / \
         np.maximum((cube*acc).sum(0)/np.maximum(na, 1), 1e-3)
    base = foc.min(0); km = np.clip(kmx, 1, nn-2)
    a0  = np.log(np.maximum(foc[km,   yy, xx]-base, 1e-6))
    am_ = np.log(np.maximum(foc[km-1, yy, xx]-base, 1e-6))
    ap  = np.log(np.maximum(foc[km+1, yy, xx]-base, 1e-6))
    den = am_-2*a0+ap; ok = den < -1e-9
    xs = np.clip(np.where(ok, 0.5*(am_-ap)/np.where(ok, den, 1.0), 0.0), -1, 1)
    pk = a0 + 0.25*(ap-am_)*xs
    c3 = np.clip(1.0-np.exp(np.minimum(a0-pk, 0.0)), 0, 1).astype(np.float32)
    c3[~ok] = 0.0
    return c1.ravel(), c2.ravel(), c3.ravel()

def worst(v, seed=7, frac=0.05):
    r = np.random.default_rng(seed)
    k = int(round(frac*v.size))
    key = v.astype(np.float64) + r.uniform(0, 1e-12, v.size)*(np.ptp(v.astype(np.float64))+1e-12)
    return set(np.argpartition(key, -k)[-k:].tolist())

def J(a, b):
    return len(a & b)/len(a | b)
