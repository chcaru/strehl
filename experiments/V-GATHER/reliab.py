"""Split-half RELIABILITY of the high-frequency content, restricted to FLAT tiles.

Two disjoint 20-frame stacks per arm (even / odd frames).  In a flat tile the
true scene is smooth, so high-pass content is either (a) photon/read noise,
which is INDEPENDENT between the two halves, or (b) real fine detail, which is
IDENTICAL between them.  Pearson r of the high-pass fields therefore splits
high-pass variance into signal (r) and noise (1-r).

Controls:
  NULL      : a half against itself -> r must be 1.000
  POSITIVE  : inject independent white noise of known sd into each half ->
              r must fall by the predicted amount.
Registration is INTEGER ONLY.
"""
import json, os
import numpy as np, tifffile

OUT = r"C:\dev\strehl-out\V-GATHER"

def luma(im):
    return 0.2126*im[:, :, 0] + 0.7152*im[:, :, 1] + 0.0722*im[:, :, 2]

def load(subj, half, arm):
    im = tifffile.imread(os.path.join(OUT, f"sp-{subj}-{half}-g{arm}.tiff"))
    return luma(im[:, :, :3].astype(np.float64))

def centre(y, n):
    h, w = y.shape
    return y[h//2-n//2:h//2+n//2, w//2-n//2:w//2+n//2]

def int_shift(a, b, maxs=48):
    n = 1024
    A = centre(a, n); B = centre(b, n)
    A = A - A.mean(); B = B - B.mean()
    w = np.outer(np.hanning(n), np.hanning(n))
    R = np.fft.rfft2(A*w)*np.conj(np.fft.rfft2(B*w))
    m = np.abs(R); m[m == 0] = 1.0
    cc = np.fft.fftshift(np.fft.irfft2(R/m, s=(n, n)))
    k = n//2
    win = cc[k-maxs:k+maxs+1, k-maxs:k+maxs+1]
    iy, ix = np.unravel_index(np.argmax(win), win.shape)
    return iy-maxs, ix-maxs

def boxblur(y, r):
    k = 2*r+1
    c = np.cumsum(np.pad(y, ((r+1, r), (0, 0)), mode="edge"), axis=0)
    y1 = (c[k:] - c[:-k])/k
    c = np.cumsum(np.pad(y1, ((0, 0), (r+1, r)), mode="edge"), axis=1)
    return (c[:, k:] - c[:, :-k])/k

def hp(y, r=3):
    return y - boxblur(y, r)

def tiles(y, t=256):
    h, w = y.shape
    for r in range(0, h-t+1, t):
        for c in range(0, w-t+1, t):
            yield r, c

def report(subj, arm, rng=None, inject=0.0, verbose=True):
    e = load(subj, "even", arm)
    o = load(subj, "odd", arm)
    dy, dx = int_shift(e, o)
    o = np.roll(np.roll(o, dy, axis=0), dx, axis=1)
    n = 3072
    E = centre(e, n); O = centre(o, n)
    if inject:
        E = E + rng.normal(0, inject, E.shape)
        O = O + rng.normal(0, inject, O.shape)
    M = (E+O)/2.0
    # flat = lowest-quartile local std tiles, chosen ONCE on the mean of the two halves
    st = np.array([M[r:r+256, c:c+256].std() for r, c in tiles(M)])
    thr = np.quantile(st, 0.25)
    he, ho = hp(E), hp(O)
    xs, ys = [], []
    for (r, c), s in zip(tiles(M), st):
        if s <= thr:
            xs.append(he[r:r+256, c:c+256].ravel())
            ys.append(ho[r:r+256, c:c+256].ravel())
    x = np.concatenate(xs); y = np.concatenate(ys)
    x -= x.mean(); y -= y.mean()
    r_ = float((x*y).mean()/np.sqrt((x*x).mean()*(y*y).mean()))
    v = float(((x+y)/2).var())          # high-pass variance of the merged half-pair
    return {"arm": arm, "shift": [int(dy), int(dx)], "flat_tiles": len(xs),
            "std_thr": float(thr), "r": r_, "hp_var": v,
            "hp_rms": float(np.sqrt(v)),
            "sig_var": r_*v, "noise_var": (1-r_)*v}

if __name__ == "__main__":
    rng = np.random.default_rng(3)
    res = {}
    for subj in ("foam", "wrapped-text-1"):
        res[subj] = {}
        for arm in ("0", "1"):
            d = report(subj, arm)
            res[subj][arm] = d
            print(f"{subj:15s} g{arm} shift={d['shift']} tiles={d['flat_tiles']:4d} "
                  f"r={d['r']:.4f} hp_rms={d['hp_rms']:8.2f} "
                  f"sig_rms={np.sqrt(d['sig_var']):8.2f} noise_rms={np.sqrt(d['noise_var']):8.2f}",
                  flush=True)
    print()
    for subj in res:
        a0, a1 = res[subj]["0"], res[subj]["1"]
        print(f"{subj:15s} g1/g0   total_hp_rms x{np.sqrt(a1['hp_var']/a0['hp_var']):.3f}   "
              f"SIGNAL_rms x{np.sqrt(a1['sig_var']/a0['sig_var']):.3f}   "
              f"NOISE_rms x{np.sqrt(a1['noise_var']/a0['noise_var']):.3f}")
    print()
    # NULL: a half against itself
    e = load("foam", "even", "0"); E = centre(e, 3072); h = hp(E)
    x = h.ravel() - h.mean()
    print(f"NULL  r(self,self) = {float((x*x).mean()/(x*x).mean()):.6f}   (must be 1.000000)")
    # POSITIVE: independent noise injected into both halves
    for sd in (10.0, 30.0, 100.0):
        d = report("foam", "0", rng=rng, inject=sd)
        print(f"POSCTL foam g0 +indep white sd={sd:6.1f} -> r={d['r']:.4f} "
              f"hp_rms={d['hp_rms']:8.2f}  (r must FALL monotonically)", flush=True)
    with open(os.path.join(OUT, "reliab.json"), "w") as f:
        json.dump(res, f, indent=1)
