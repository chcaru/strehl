"""Is the chroma excess RESTORED (removing a low-pass) or CREATED (manufactured
by the double demosaic)?  Decide by SHAPE, not magnitude.

Restored noise has a predicted spectrum: for white sensor noise the per-band
amplitude ratio between the two gather orders is exactly
    gather_mtf(CR, f) / gather_mtf(CR, 2f)      (f in cyc/output px, f < 0.25)
because the old path resamples on the CFA-plane lattice (pitch 2) and the new
one on the full-res lattice (pitch 1).  That curve is the RESTORATION CEILING
and it is smooth and monotone.  Created noise has no reason to follow it, and a
maze/labyrinth artifact would appear as a PEAK -- typically near the diagonal
Nyquist -- rather than a smooth lift.
"""
from __future__ import annotations
import os, sys, math
import numpy as np, tifffile
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from chroma import hp, boxblur
from mtfsim2 import gather_mtf

OUT = r"C:\dev\strehl-out\V-GATHER"
T = 128
NB = 24

_win = np.hanning(T)[:, None] * np.hanning(T)[None, :]
_fy = np.fft.fftshift(np.fft.fftfreq(T))[:, None]
_fx = np.fft.fftshift(np.fft.fftfreq(T))[None, :]
_rad = np.sqrt(_fx**2 + _fy**2)
_edges = np.linspace(0.0, 0.5, NB + 1)
_masks = [(_rad >= _edges[i]) & (_rad < _edges[i+1]) for i in range(NB)]
_ctr = 0.5*(_edges[:-1] + _edges[1:])
_corner = (np.abs(_fx) > 0.38) & (np.abs(_fy) > 0.38)
_axes = ((np.abs(_fx) > 0.38) & (np.abs(_fy) < 0.08)) | ((np.abs(_fy) > 0.38) & (np.abs(_fx) < 0.08))

def load(s, a):
    return tifffile.imread(os.path.join(OUT, f"{s}-q-g{a}.tiff"))[:, :, :3].astype(np.float64)

def flat_tiles(l0, l1, q=0.05):
    h = (min(l0.shape[0], l1.shape[0])//T)*T; w = (min(l0.shape[1], l1.shape[1])//T)*T
    m = ((l0[:h,:w] + l1[:h,:w])/2).reshape(h//T, T, w//T, T)
    st = m.std(axis=(1,3))
    thr = np.quantile(st, q)
    return h, w, np.argwhere(st <= thr)

def band_power(img, h, w, idx):
    """Mean radial power spectrum of img over the listed tiles."""
    acc = np.zeros(NB); cor = 0.0; ax = 0.0; n = 0
    for (ty, tx) in idx:
        t = img[ty*T:(ty+1)*T, tx*T:(tx+1)*T]
        a = (t - t.mean())*_win
        P = np.abs(np.fft.fftshift(np.fft.fft2(a)))**2
        for i in range(NB):
            acc[i] += P[_masks[i]].mean()
        cor += P[_corner].mean(); ax += P[_axes].mean(); n += 1
    return acc/n, cor/n, ax/n

def chroma(im): return im[:,:,0] - im[:,:,2]
def luma(im):   return 0.2126*im[:,:,0] + 0.7152*im[:,:,1] + 0.0722*im[:,:,2]

def run(s, q=0.05, plant=None):
    i0, i1 = load(s, "0"), load(s, "1")
    if plant is not None: i1 = plant(i1)
    h, w, idx = flat_tiles(luma(i0), luma(i1), q)
    c0 = hp(chroma(i0))[:h,:w]; c1 = hp(chroma(i1))[:h,:w]
    p0, k0, a0 = band_power(c0, h, w, idx)
    p1, k1, a1 = band_power(c1, h, w, idx)
    del i0, i1, c0, c1
    return p0, p1, k0, k1, a0, a1, len(idx)

print("="*104)
print("COMMISSIONING the spectral instrument")
print("="*104)
p0, p1, k0, k1, a0, a1, n = run("highly-angled-ruler-mm-cpl", 0.05)
r = p1/p0
print(f"N1 null (byte-identical arms, {n} tiles): per-band ratio "
      f"min {r.min():.9f} max {r.max():.9f}  corner {k1/k0:.9f}   "
      f"{'PASS' if abs(r.max()-1) < 1e-12 and abs(r.min()-1) < 1e-12 else 'FAIL'}")

def maze(im):
    yy, xx = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    k = 10.0*((-1.0)**(xx+yy))          # TRUE diagonal Nyquist (0.5,0.5) cyc/px
    o = im.copy(); o[:,:,0] += k; o[:,:,2] -= k; return o
p0, p1, k0, k1, a0, a1, n = run("foam", 0.05, plant=maze)
print(f"P1 planted maze at diagonal Nyquist: corner power x{k1/k0:8.2f}   "
      f"axis power x{a1/a0:6.3f}   {'PASS - corner-selective' if k1/k0 > 20 and k1/k0 > 5*(a1/a0) else 'FAIL'}")

def denoise(im):
    o = im.copy(); o[:,:,0] = boxblur(im[:,:,0],1); o[:,:,2] = boxblur(im[:,:,2],1); return o
p0d, p1d, _, _, _, _, _ = run("foam", 0.05, plant=denoise)
rd = p1d/p0d
print(f"P2 planted improvement (chroma denoise): high-band ratio "
      f"{rd[NB//2:].mean():.4f} vs unplanted -- must FALL")

print()
print("="*104)
print("MEASURED per-band chroma (R-B) power ratio g1/g0 on FLAT tiles (q=0.05)")
print("   PRED = (gather_mtf(CR,f)/gather_mtf(CR,2f))^2, the white-noise restoration CEILING")
print("   | 0.25 cyc/output px = the OLD path's plane Nyquist; PRED undefined above it")
print("="*104)
SUBJ = ["foam", "couch-fibers-cpl", "lavendar-cpl", "flower-bud-alone-cpl", "coffee-bubbles"]
pred = []
for f in _ctr:
    pred.append((gather_mtf("catmull-rom", f)/gather_mtf("catmull-rom", 2*f))**2 if 2*f < 0.5 else float("nan"))
pred = np.array(pred)

res = {}
for s in SUBJ:
    p0, p1, k0, k1, a0, a1, n = run(s, 0.05)
    res[s] = (p0, p1, k0, k1, a0, a1, n)
    print(f"  {s}: {n} flat tiles", flush=True)

print()
print(f"{'f cyc/out px':>13s} {'PRED':>8s}" + "".join(f"{s[:11]:>13s}" for s in SUBJ))
for i in range(NB):
    mark = " |" if abs(_ctr[i]-0.25) < 0.011 else "  "
    pp = f"{pred[i]:8.3f}" if not math.isnan(pred[i]) else "     n/a"
    print(f"{_ctr[i]:13.4f}{mark}{pp}" + "".join(f"{res[s][1][i]/res[s][0][i]:13.3f}" for s in SUBJ))

print()
print("MAZE / LABYRINTH TEST -- diagonal-Nyquist corner vs on-axis high frequency")
print(f"{'subject':24s} {'corner g0':>12s} {'corner g1':>12s} {'x':>7s} {'axis g0':>12s} "
      f"{'axis g1':>12s} {'x':>7s} {'corner/axis g0':>15s} {'g1':>8s}")
for s in SUBJ:
    p0, p1, k0, k1, a0, a1, n = res[s]
    print(f"{s:24s} {k0:12.4e} {k1:12.4e} {k1/k0:7.3f} {a0:12.4e} {a1:12.4e} {a1/a0:7.3f} "
          f"{k0/a0:15.3f} {k1/a1:8.3f}")
