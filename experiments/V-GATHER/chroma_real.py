"""Statistic D on real renders: is the chroma excess NOISE (white, flatness-
independent) or DETAIL (shrinks as tiles get flatter, follows the subject)?

Renders are --linear-srgb --demosaic, NO --auto-exposure: no per-image gain,
no tone-scaling stage, so absolute rms is comparable between the two arms.
"""
from __future__ import annotations
import os, sys, json
import numpy as np, tifffile
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from chroma import boxblur, hp, radial_spectrum

OUT = r"C:\dev\strehl-out\V-GATHER"
T = 128
QS = [0.02, 0.05, 0.10, 0.25, 0.50]

def load(s, a):
    im = tifffile.imread(os.path.join(OUT, f"{s}-q-g{a}.tiff"))[:, :, :3].astype(np.float64)
    return im

def planes(im):
    return (0.2126*im[:,:,0] + 0.7152*im[:,:,1] + 0.0722*im[:,:,2], im[:,:,0] - im[:,:,2])

def tiled(y, t=T):
    h = (y.shape[0]//t)*t; w = (y.shape[1]//t)*t
    return y[:h, :w].reshape(h//t, t, w//t, t)

def measure(im0, im1, q):
    l0, c0 = planes(im0); l1, c1 = planes(im1)
    h = (min(l0.shape[0], l1.shape[0])//T)*T; w = (min(l0.shape[1], l1.shape[1])//T)*T
    l0, c0, l1, c1 = l0[:h,:w], c0[:h,:w], l1[:h,:w], c1[:h,:w]
    st = tiled((l0+l1)/2).std(axis=(1,3))
    sel = st <= np.quantile(st, q)
    out = []
    for y in (l0, l1, c0, c1):
        e = tiled(hp(y)); v = (e**2).mean(axis=(1,3))
        out.append(float(np.sqrt(v[sel].mean())))
    return out + [int(sel.sum()), float(np.quantile(st, q))]

SUBJ = ["foam", "couch-fibers-cpl", "lavendar-cpl", "flower-bud-alone-cpl",
        "coffee-bubbles", "bee-1-cpl", "tweezers-cpl", "wrapped-text-1",
        "wrapped-text-2", "flat-on-ruler-cpl"]
NULLS = ["highly-angled-ruler-mm-cpl"]

print("="*100)
print("COMMISSIONING statistic D on REAL renders")
print("="*100)
n = NULLS[0]
a0, a1 = load(n, "0"), load(n, "1")
print(f"N1 byte-identical null ({n}, alignment REFUSED): "
      f"max |g1-g0| = {np.abs(a1-a0).max():.6f} DN")
for q in (0.05, 0.25):
    L0,L1,C0,C1,ntile,_ = measure(a0, a1, q)
    print(f"   q={q:<5} luma ratio {L1/L0:.6f}   chroma ratio {C1/C0:.6f}   "
          f"{'PASS' if abs(L1/L0-1)<1e-9 and abs(C1/C0-1)<1e-9 else 'FAIL'}")

s = "foam"
b0, b1 = load(s, "0"), load(s, "1")
base = measure(b0, b1, 0.10)
print(f"\nP0 baseline ({s}, q=0.10): luma {base[0]:.3f} -> {base[1]:.3f} (x{base[1]/base[0]:.4f}) "
      f"| chroma {base[2]:.3f} -> {base[3]:.3f} (x{base[3]/base[2]:.4f})")

yy, xx = np.mgrid[0:b1.shape[0], 0:b1.shape[1]]
maze = (10.0*(-1.0)**(xx+yy)).astype(np.float64)
d1 = b1.copy(); d1[:,:,0] += maze; d1[:,:,2] -= maze
m = measure(b0, d1, 0.10)
print(f"P1 PLANTED DEFECT  (diag-Nyquist chroma maze, +/-10 DN): chroma x{m[3]/m[2]:.4f}  "
      f"{'PASS - rises' if m[3]/m[2] > base[3]/base[2] else 'FAIL'}")

i1 = b1.copy(); i1[:,:,0] = boxblur(b1[:,:,0],1); i1[:,:,2] = boxblur(b1[:,:,2],1)
m = measure(b0, i1, 0.10)
print(f"P2 PLANTED IMPROVEMENT (chroma denoise 3x3):            chroma x{m[3]/m[2]:.4f}  "
      f"{'PASS - falls' if m[3]/m[2] < base[3]/base[2] else 'FAIL'}")

s1 = b1.copy(); mn = b1.reshape(-1,3).mean(axis=0)
s1 = (b1 - mn)*2.0 + mn
m = measure(b0, s1, 0.10)
print(f"P3 AMPLITUDE x2 (statistic B was x1.000000):            chroma x{m[3]/m[2]/(base[3]/base[2]):.4f} "
      f"relative  {'PASS' if abs(m[3]/m[2]/(base[3]/base[2])-2)<0.03 else 'FAIL'}")
del b0, b1, d1, i1, s1, a0, a1

print()
print("="*100)
print("FLATNESS SWEEP -- if the chroma excess is DETAIL it shrinks toward 1.0 as tiles flatten")
print("="*100)
hdr = f"{'subject':24s}" + "".join(f"{('q='+str(q)):>16s}" for q in QS)
print("LUMA  ratio g1/g0"); print(hdr)
res = {}
for s in SUBJ:
    try:
        i0, i1 = load(s, "0"), load(s, "1")
    except Exception as e:
        print(f"{s:24s} SKIP {e}"); continue
    row = []
    for q in QS:
        row.append(measure(i0, i1, q))
    res[s] = row
    print(f"{s:24s}" + "".join(f"{r[1]/r[0]:16.4f}" for r in row), flush=True)
    del i0, i1
print("\nCHROMA (R-B) ratio g1/g0"); print(hdr)
for s, row in res.items():
    print(f"{s:24s}" + "".join(f"{r[3]/r[2]:16.4f}" for r in row))
print("\nn tiles admitted"); print(hdr)
for s, row in res.items():
    print(f"{s:24s}" + "".join(f"{r[4]:16d}" for r in row))
json.dump({s: [list(r) for r in row] for s, row in res.items()},
          open(os.path.join(OUT, "chroma_real.json"), "w"), indent=1)
