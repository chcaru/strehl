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

# V-ANTI section 4.1: planted dose-response ladder on the odd field.
print("   %6s %12s %10s" % ("t", "mean|R-Y| DN", "vs off %"))
for t in [-3,-2.5,-2,-1.75,-1.5,-1.25,-1.0,-0.75,-0.5,-0.25,0,0.25,0.5,1.0,1.5,2.0,3.0]:
    v = np.abs(cu + t*O)[edge].mean()
    print("   %6.2f %12.2f %9.3f%%" % (t, v, 100*(v-Mu)/Mu))
ts = np.arange(-2.0, 0.01, 0.02)
vs = np.array([np.abs(cu + t*O)[edge].mean() for t in ts])
print("   minimum at t = %+.2f (shipped is -1.00), %.2f DN (%+.3f%%)"
      % (ts[vs.argmin()], vs.min(), 100*(vs.min()-Mu)/Mu))
