import numpy as np, tifffile, os
OUT = os.environ.get("VANTI_DIR", r"C:\dev\strehl-out\V-CA-anti")
def rd(n):
    a = tifffile.imread(os.path.join(OUT, n + ".tif"))
    assert a.dtype == np.uint16, ("EXPECTED uint16 GOT", a.dtype)   # no fallback, by rule
    return a.astype(np.float64)
u, c, a = rd("unset"), rd("correct"), rd("anti")
g = u[..., 1]
grad = np.abs(np.diff(g, axis=1, prepend=g[:, :1])) + np.abs(np.diff(g, axis=0, prepend=g[:1, :]))
edge = grad >= np.percentile(grad, 90)          # registered stencil, computed on unset only
Y = lambda x: 0.2126*x[...,0] + 0.7152*x[...,1] + 0.0722*x[...,2]
cu, cc, ca = u[...,0]-Y(u), c[...,0]-Y(c), a[...,0]-Y(a)
O = (ca - cc) / 2.0                              # odd-in-eps part of the FIELD
E = ((ca - cu) + (cc - cu)) / 2.0                # even-in-eps part of the FIELD
h, w = g.shape
yy, xx = np.mgrid[0:h, 0:w]
r = np.hypot(yy - h/2, xx - w/2); r /= r.max()
th = np.degrees(np.arctan2(yy - h/2, xx - w/2))
Mu = np.abs(cu)[edge].mean()
pc = lambda v, m=edge: 100*(np.abs(v)[m].mean() - np.abs(cu)[m].mean()) / np.abs(cu)[m].mean()

# V-ANTI sections 4.2 / 4.3: is the harm radial, or azimuthal?
print("per-annulus, raw statistic beside every percentage:")
for lo in np.arange(0.0, 0.9, 0.1):
    m = edge & (r >= lo) & (r < lo+0.1)
    if m.sum() < 500: continue
    b = np.abs(cu)[m].mean()
    print("  r %.1f-%.1f n=%7d raw %7.1f DN  correct %+7.2f%% (%+8.1f DN)  zero-blur %+7.2f%%  sign-rev %5.1f%%  levels %5d"
          % (lo, lo+0.1, m.sum(), b, pc(cc,m), np.abs(cc)[m].mean()-b, pc(cu-O,m),
             100*np.mean(np.sign(cu[m]) != np.sign(cc[m])), len(np.unique(u[...,0][m]))))
print("\nstencil sensitivity of the r<0.40 sign:")
for q in (80, 90, 95, 99):
    e2 = grad >= np.percentile(grad, q); m = e2 & (r < 0.40)
    print("  green-grad top %2d%%  n=%8d raw %7.1f DN  correct %+7.2f%%  zero-blur %+7.2f%%"
          % (100-q, m.sum(), np.abs(cu)[m].mean(), pc(cc,m), pc(cu-O,m)))
m = (r < 0.40)
print("  ALL pixels, no stencil n=%8d raw %7.1f DN  correct %+7.2f%%  zero-blur %+7.2f%%"
      % (m.sum(), np.abs(cu)[m].mean(), pc(cc,m), pc(cu-O,m)))
print("\nradius vs azimuth inside r<0.45 -- same pixels, two binnings:")
m = edge & (r < 0.45)
for lab, coord, ed in (("radius", r, np.linspace(0,0.45,10)), ("azimuth", th, np.linspace(-180,180,10))):
    vals = [pc(cc, m & (coord>=ed[i]) & (coord<ed[i+1]))
            for i in range(9) if (m & (coord>=ed[i]) & (coord<ed[i+1])).sum() >= 500]
    print("  by %-8s : %+7.2f%% .. %+7.2f%%   range %6.2f pp, sd %5.2f"
          % (lab, min(vals), max(vals), max(vals)-min(vals), np.std(vals)))
print("\nr 0.2-0.3 (V-CA's claim-(b) annulus) by 12 azimuthal sectors:")
m0 = edge & (r >= 0.2) & (r < 0.3)
for k in range(12):
    lo = -180 + k*30; mm = m0 & (th >= lo) & (th < lo+30)
    if mm.sum() < 200: continue
    print("  %+5d..%+5d n=%7d raw %7.1f DN  correct %+8.2f%%  zero-blur %+8.2f%%"
          % (lo, lo+30, mm.sum(), np.abs(cu)[mm].mean(), pc(cc,mm), pc(cu-O,mm)))
print("\nsection 6, the number that does not fit:")
m56 = edge & (r >= 0.5) & (r < 0.6); keep = edge & ~m56
print("  r0.5-0.6 is %.1f%% of the edge population" % (100*m56.sum()/edge.sum()))
print("  headline with it %+.3f%% ; excluding it %+.3f%%" % (pc(cc), pc(cc, keep)))
