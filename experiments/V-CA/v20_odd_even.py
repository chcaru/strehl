import numpy as np, tifffile, os
OUT = r"C:\dev\strehl-out\V-CA-anti"
def rd(p):
    a = tifffile.imread(p); assert a.dtype == np.uint16, a.dtype; return a.astype(np.float64)
u, c, a = rd(OUT+r"\unset.tif"), rd(OUT+r"\correct.tif"), rd(OUT+r"\anti.tif")
g = u[...,1]
grad = np.abs(np.diff(g,axis=1,prepend=g[:,:1])) + np.abs(np.diff(g,axis=0,prepend=g[:1,:]))
edge = grad >= np.percentile(grad,90)
Y = lambda x: 0.2126*x[...,0]+0.7152*x[...,1]+0.0722*x[...,2]
h,w = g.shape; yy,xx = np.mgrid[0:h,0:w]
r = np.hypot(yy-h/2, xx-w/2); r /= r.max()
print("DECOMPOSITION: correction is ODD in eps, resampling is EVEN in eps.")
print("  odd  = (anti - correct)/2   <- the real correction")
print("  even = (anti + correct)/2   <- interpolation, present in BOTH arms")
print()
print("  %-9s %8s %9s %9s %9s %9s %7s" % ("r","n","correct","anti","ODD","EVEN","%corr"))
print("  " + "-"*66)
for lo in np.arange(0.0,0.9,0.1):
    m = edge & (r>=lo) & (r<lo+0.1)
    if m.sum() < 500: continue
    b  = np.abs(u[...,0]-Y(u))[m].mean()
    cc = 100*(np.abs(c[...,0]-Y(c))[m].mean()-b)/b
    aa = 100*(np.abs(a[...,0]-Y(a))[m].mean()-b)/b
    odd, even = (aa-cc)/2, (aa+cc)/2
    frac = 100*abs(odd)/(abs(odd)+abs(even)) if (abs(odd)+abs(even)) else float('nan')
    print("  %.1f-%.1f  %8d %8.2f%% %8.2f%% %8.2f%% %8.2f%% %6.1f%%" % (lo,lo+0.1,m.sum(),cc,aa,odd,even,frac))
b  = np.abs(u[...,0]-Y(u))[edge].mean()
cc = 100*(np.abs(c[...,0]-Y(c))[edge].mean()-b)/b
aa = 100*(np.abs(a[...,0]-Y(a))[edge].mean()-b)/b
print("\n  WHOLE EDGE POPULATION: correct %+.2f%%  anti %+.2f%%  ODD %+.2f%%  EVEN %+.2f%%"
      % (cc,aa,(aa-cc)/2,(aa+cc)/2))
print("  -> of the %.2f%% headline, %.2f pp is correction and %.2f pp is interpolation"
      % (abs(cc), abs((aa-cc)/2), abs((aa+cc)/2)))
print("  -> INTERPOLATION SHARE OF THE ON-VS-OFF NUMBER: %.1f%%"
      % (100*abs((aa+cc)/2)/(abs((aa-cc)/2)+abs((aa+cc)/2))))
