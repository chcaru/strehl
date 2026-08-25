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

# V-ANTI section 3.2: the controls V-CA did not build.
print("channel deltas vs unset (proves only R moves):")
for nm, x in (("correct", c), ("anti", a)):
    print("  %-8s R=%9d G=%9d B=%9d" % (nm,
        int(np.count_nonzero(x[...,0] != u[...,0])),
        int(np.count_nonzero(x[...,1] != u[...,1])),
        int(np.count_nonzero(x[...,2] != u[...,2]))))
print("\nrms(O)=%.2f DN  rms(E)=%.2f DN  E/O=%.4f" % (
    np.sqrt((O[edge]**2).mean()), np.sqrt((E[edge]**2).mean()),
    np.sqrt((E[edge]**2).mean())/np.sqrt((O[edge]**2).mean())))
rows = (("correct  (cu-O+E) observed", cc), ("anti     (cu+O+E) observed", ca),
        ("correction, blur deleted  ", cu-O), ("anti,       blur deleted  ", cu+O),
        ("blur alone, no correction ", cu+E))
print()
for nm, v in rows:
    print("  %-28s %+8.3f %%   (%8.2f DN)" % (nm, pc(v), np.abs(v)[edge].mean()))
Eobs, Erect = (pc(ca)+pc(cc))/2, (pc(cu+O)+pc(cu-O))/2
print("\n  metric EVEN observed                       = %+8.3f pp" % Eobs)
print("  metric EVEN from a PERFECTLY ODD FIELD     = %+8.3f pp" % Erect)
print("  rectification share of V-CA's 'interpolation' = %.0f %%" % (100*Erect/Eobs))
print("  genuine even-field contribution            = %+8.3f pp" % (Eobs - Erect))
print("  realised distinct R levels in the window   = %d" % len(np.unique(u[...,0][edge])))
