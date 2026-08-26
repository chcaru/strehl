"""CA-vs-clipping discriminator, v2.

LaCA: per-channel radial magnification error. Hue fringe SIGN FLIPS with the sign
of the radial luminance gradient, magnitude GROWS with radius, vanishes at centre.
Clipping asymmetry: a LEVEL effect. One-signed regardless of edge direction, no
radial dependence.
"""
import sys, numpy as np, tifffile
from scipy.ndimage import maximum_filter, gaussian_filter

path, label = sys.argv[1], sys.argv[2]
a = tifffile.imread(path).astype(np.float32)
H, W = a.shape[:2]
R, G, B = a[:,:,0], a[:,:,1], a[:,:,2]
L = 0.2126*R + 0.7152*G + 0.0722*B
mg = ((R - G) + (B - G)) / 2.0

cx, cy = W/2.0, H/2.0
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
dx, dy = xx - cx, yy - cy
r = np.hypot(dx, dy); r[r < 1] = 1
ux, uy = dx/r, dy/r

Ls = gaussian_filter(L, 1.5)
gy, gx = np.gradient(Ls)
dLdr = gx*ux + gy*uy

nearbright = maximum_filter(L, size=15) > 0.90*L.max()   # within 7px of a near-white field
gmag = np.hypot(gx, gy)
sel = nearbright & (gmag > np.percentile(gmag[nearbright], 90))
print("=== %s ===" % label)
print("frame %dx%d  centre (%.0f,%.0f)  Lmax %.0f" % (W, H, cx, cy, L.max()))
print("edge pixels beside a near-white field: %d (%.4f%% of frame)" % (sel.sum(), 100.0*sel.mean()))

rr, mm, dd = r[sel], mg[sel], dLdr[sel]
out, inw = dd > 0, dd < 0
print("\n[TEST 1 ANTISYMMETRY]  CA flips with the radial gradient; clipping does not.")
print("  brightening OUTWARD (n=%7d): mean mg %+8.1f  median %+8.1f" % (out.sum(), mm[out].mean(), np.median(mm[out])))
print("  brightening INWARD  (n=%7d): mean mg %+8.1f  median %+8.1f" % (inw.sum(), mm[inw].mean(), np.median(mm[inw])))
sep = mm[out].mean() - mm[inw].mean()
print("  separation %+.1f DN   spread of the two means about their mid: %.1f DN" % (sep, abs(sep)/2))

print("\n[TEST 2 RADIAL]  CA grows with radius; clipping does not.")
print("   radius       n      mean mg    outward    inward   antisym(out-in)")
edges = np.linspace(rr.min(), rr.max(), 8)
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (rr >= lo) & (rr < hi)
    if m.sum() < 200: continue
    o, i = m & out, m & inw
    mo = mm[o].mean() if o.sum() > 30 else np.nan
    mi = mm[i].mean() if i.sum() > 30 else np.nan
    print("  %4.0f-%4.0f %8d   %+8.1f   %+8.1f  %+8.1f   %+8.1f" % (lo, hi, m.sum(), mm[m].mean(), mo, mi, mo-mi))

print("\n[TEST 3 LEVEL]  clipping asymmetry tracks proximity to the ceiling.")
lv = a.max(axis=2)[sel]
print("   level band          n      mean mg    frac mg>0")
qs = [0, 50, 75, 90, 97, 99.5, 100]
for lo, hi in zip(qs[:-1], qs[1:]):
    a1, a2 = np.percentile(lv, lo), np.percentile(lv, hi)
    m = (lv >= a1) & (lv <= a2)
    if m.sum() < 100: continue
    print("  %6.0f-%6.0f %8d   %+8.1f     %6.2f%%" % (a1, a2, m.sum(), mm[m].mean(), 100.0*(mm[m] > 0).mean()))
print("\nframe-wide: %.4f%% of pixels have ANY channel at 65535; %.4f%% have ALL three"
      % (100.0*(a >= 65535).any(axis=2).mean(), 100.0*(a >= 65535).all(axis=2).mean()))
