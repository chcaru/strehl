"""Commission statistic D, then answer: restored or created?"""
from __future__ import annotations
import sys, numpy as np
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from chroma import (malvar, sample_cr, make_T, gather_old, gather_new,
                    stats, hp, radial_spectrum, M)

H = W = 384
LEVEL, SIGMA = 2000.0, 40.0

def mosaic(seed, sigma=SIGMA, level=LEVEL):
    rg = np.random.default_rng(seed)
    return level + sigma*rg.standard_normal((H, W))

print("=" * 78)
print("COMMISSIONING statistic D = rms of the 7x7-box high-pass of (R-B)")
print("=" * 78)

mos = mosaic(1)
r, g, b = malvar(mos)

flat = np.full((H, W), 1234.5)
fr, fg, fb = malvar(flat)
print(f"C1 DC-preservation      : malvar(const) max |err| = "
      f"{max(np.abs(x-1234.5).max() for x in (fr,fg,fb)):.3e}   "
      f"{'PASS' if max(np.abs(x-1234.5).max() for x in (fr,fg,fb)) < 1e-9 else 'FAIL'}")

e = max(np.abs(r[0::2,0::2]-mos[0::2,0::2]).max(),
        np.abs(b[1::2,1::2]-mos[1::2,1::2]).max(),
        np.abs(g[0::2,1::2]-mos[0::2,1::2]).max(),
        np.abs(g[1::2,0::2]-mos[1::2,0::2]).max())
print(f"C2 interpolating        : demosaic returns the MEASURED value at its own "
      f"site, max |err| = {e:.3e}   {'PASS' if e == 0.0 else 'FAIL'}")

Tid = make_T(0.0, 1.0, 0.0, 0.0, W/4, H/4)
o_id, n_id = gather_old(mos, Tid), gather_new(mos, Tid)
d_o = np.abs(o_id - mos)[M:-M, M:-M].max()
d_n = np.abs(n_id - mos)[M:-M, M:-M].max()
print(f"C3 NULL (identity warp) : OLD max|d| = {d_o:.3e}   NEW max|d| = {d_n:.3e}")
print(f"   -> the DOUBLE DEMOSAIC alone is a {'no-op' if d_n < 1e-9 else 'CHANGE'}; "
      f"{'PASS' if d_o < 1e-9 and d_n < 1e-9 else 'FAIL'}")

s1 = stats(*malvar(mosaic(1, sigma=SIGMA)))[1]
s2 = stats(*malvar(mosaic(1, sigma=2*SIGMA)))[1]
print(f"C4 amplitude response   : sigma x2 -> statistic x{s2/s1:.4f}   "
      f"(statistic B was x1.000000)   {'PASS' if abs(s2/s1-2) < 0.02 else 'FAIL'}")

base_l, base_c, base_sc = stats(r, g, b)
kk = np.zeros((H, W))
yy, xx = np.mgrid[0:H, 0:W]
kk = 12.0*np.cos(np.pi*(xx+yy)/2.0)                      # maze: diagonal Nyquist
dr, db = r + kk, b - kk
_, maze_c, maze_sc = stats(dr, g, db)
print(f"C5 PLANTED DEFECT (maze): {base_c:.4f} -> {maze_c:.4f}  "
      f"(x{maze_c/base_c:.3f})   {'PASS - rises' if maze_c > base_c else 'FAIL'}")

from chroma import boxblur
sr, sb = boxblur(r, 1), boxblur(b, 1)
_, smooth_c, _ = stats(sr, g, sb)
print(f"C6 PLANTED IMPROVEMENT  : chroma denoise 3x3 -> {base_c:.4f} -> {smooth_c:.4f}  "
      f"(x{smooth_c/base_c:.3f})   {'PASS - falls' if smooth_c < base_c else 'FAIL'}")
print(f"   (statistic B ROSE under blur; D must fall, and does)")

pb, cb, dgb, axb = radial_spectrum(base_sc)
pm, cm, dgm, axm = radial_spectrum(maze_sc)
print(f"C7 spectrum potency     : diagonal-corner power  clean {dgb:.3e} -> maze "
      f"{dgm:.3e}  (x{dgm/dgb:.1f})   {'PASS' if dgm/dgb > 5 else 'FAIL'}")
print(f"   flatness (diag/axis)  clean {dgb/axb:.3f} -> maze {dgm/axm:.3f}")

print()
print("=" * 78)
print("MEASUREMENT  (n seeds x n transforms; NOGATHER = restoration CEILING)")
print("=" * 78)

TRANSFORMS = [
    ("pure shift .5,.5",  dict(theta=0.0,     scale=1.0,    tx=0.5,  ty=0.5)),
    ("pure shift .27,.61", dict(theta=0.0,    scale=1.0,    tx=0.27, ty=0.61)),
    ("rot 0.05deg",       dict(theta=8.73e-4, scale=1.0,    tx=0.13, ty=-0.41)),
    ("rot 0.15deg+scale", dict(theta=2.62e-3, scale=1.0003, tx=-0.72, ty=0.33)),
]
SEEDS = [11, 12, 13, 14, 15, 16]

print(f"{'transform':22s} {'lumaHP ng':>9s} {'lumaHP old':>10s} {'lumaHP new':>10s} "
      f"{'new/old':>8s} {'new/ng':>7s} | {'chrHP ng':>9s} {'chr old':>9s} {'chr new':>9s} "
      f"{'new/old':>8s} {'new/ng':>7s}")
agg = {}
for name, kw in TRANSFORMS:
    T = make_T(cx=W/4, cy=H/4, **kw)
    acc = np.zeros((3, 2))
    for s in SEEDS:
        mos = mosaic(s)
        for i, arm in enumerate((mos, gather_old(mos, T), gather_new(mos, T))):
            l, c, _ = stats(*malvar(arm))
            acc[i, 0] += l*l; acc[i, 1] += c*c
    acc = np.sqrt(acc/len(SEEDS))
    ng, ol, nw = acc
    agg[name] = acc
    print(f"{name:22s} {ng[0]:9.3f} {ol[0]:10.3f} {nw[0]:10.3f} {nw[0]/ol[0]:8.3f} "
          f"{nw[0]/ng[0]:7.3f} | {ng[1]:9.3f} {ol[1]:9.3f} {nw[1]:9.3f} "
          f"{nw[1]/ol[1]:8.3f} {nw[1]/ng[1]:7.3f}", flush=True)

print()
print("SPECTRUM of the (R-B) high-pass residual, transform = rot 0.05deg, seed 11")
T = make_T(cx=W/4, cy=H/4, theta=8.73e-4, scale=1.0, tx=0.13, ty=-0.41)
mos = mosaic(11)
specs = {}
for nm, arm in (("NOGATHER", mos), ("OLD plane", gather_old(mos, T)),
                ("NEW fullres", gather_new(mos, T))):
    _, _, sc = stats(*malvar(arm))
    prof, ctr, dg, ax = radial_spectrum(sc)
    specs[nm] = (prof, ctr, dg, ax)
    print(f"  {nm:12s} diag-corner {dg:.4e}  axis {ax:.4e}  diag/axis {dg/ax:6.3f}")
print()
print(f"  {'radial f (cyc/px)':22s}" + "".join(f"{n:>14s}" for n in specs))
ctr = specs['NOGATHER'][1]
for i in range(0, 32, 2):
    row = f"  {ctr[i]:<22.4f}"
    for n in specs:
        row += f"{specs[n][0][i]:14.4e}"
    print(row)
print()
print("  ratio NEW/NOGATHER by radial band:")
for i in range(0, 32, 2):
    a, b_ = specs['NEW fullres'][0][i], specs['NOGATHER'][0][i]
    o = specs['OLD plane'][0][i]
    print(f"    f={ctr[i]:.4f}  OLD/NG {o/b_:7.3f}   NEW/NG {a/b_:7.3f}   NEW/OLD {a/o:7.3f}")
