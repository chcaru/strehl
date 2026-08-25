import numpy as np, tifffile
D = r"C:\dev\strehl-out\M110-sheet\bee-3-cpl"
def rd(p):
    a = tifffile.imread(p); assert a.dtype == np.uint16, a.dtype; return a
off16, on16 = rd(D+r"\default.tif"), rd(D+r"\ca.tif")
def narrow(a, bits):
    if bits >= 16: return a.astype(np.float64)
    s = 16 - bits
    return ((a >> s) << s).astype(np.float64)
# edge stencil once, from the UNNARROWED off arm (same population every dose)
g = off16[..., 1].astype(np.float64)
gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1])); gy = np.abs(np.diff(g, axis=0, prepend=g[:1, :]))
grad = gx + gy
edge = grad >= np.percentile(grad, 90)
print("edge px = %d (%.1f%% of frame)\n" % (edge.sum(), 100*edge.mean()))
def Y(a): return 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2]
hdr = "%5s %8s %12s %12s %12s %12s" % ("bits","levels","fall_edge%","|dG|/|dR|","%px R chg","var-ratio")
print(hdr); print("-"*len(hdr))
base = {}
for bits in [16,14,12,11,10,9,8,7,6]:
    o, n = narrow(off16,bits), narrow(on16,bits)
    ro, rn = np.abs(o[...,0]-Y(o))[edge], np.abs(n[...,0]-Y(n))[edge]
    fall = 100*(rn.mean()-ro.mean())/ro.mean()
    dR = np.abs(n[...,0]-o[...,0]); dG = np.abs(n[...,1]-o[...,1])
    ratio = dG.mean()/dR.mean() if dR.mean() else float("nan")
    pct = 100*np.mean(n[...,0] != o[...,0])
    vr  = rn.var()/ro.var()
    lv = len(np.unique(o[...,0][edge]))
    if bits==16: base = dict(fall=fall, ratio=ratio, pct=pct, vr=vr)
    print("%5d %8d %12.3f %12.4f %12.3f %12.4f" % (bits, lv, fall, ratio, pct, vr))
print("\nERROR vs true 16-bit value (%):")
print("%5s %12s %12s %12s %12s" % ("bits","fall_edge","|dG|/|dR|","%px R chg","var-ratio"))
for bits in [12,10,8,6]:
    o, n = narrow(off16,bits), narrow(on16,bits)
    ro, rn = np.abs(o[...,0]-Y(o))[edge], np.abs(n[...,0]-Y(n))[edge]
    fall = 100*(rn.mean()-ro.mean())/ro.mean()
    dR = np.abs(n[...,0]-o[...,0]); dG = np.abs(n[...,1]-o[...,1])
    ratio = dG.mean()/dR.mean(); pct = 100*np.mean(n[...,0]!=o[...,0]); vr = rn.var()/ro.var()
    f = lambda x,b: 100*(x-b)/abs(b)
    print("%5d %11.1f%% %11.1f%% %11.1f%% %11.1f%%" %
          (bits, f(fall,base["fall"]), f(ratio,base["ratio"]), f(pct,base["pct"]), f(vr,base["vr"])))
# M111 term disparity of MY ratio
o, n = narrow(off16,16), narrow(on16,16)
dR = np.abs(n[...,0]-o[...,0]).mean(); dG = np.abs(n[...,1]-o[...,1]).mean()
print("\nM111 term disparity D of my |dG|/|dR| ratio = max/min = %.2f" % (max(dR,dG)/min(dR,dG)))
