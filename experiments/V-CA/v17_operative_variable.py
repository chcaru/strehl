import numpy as np, tifffile
D = r"C:\dev\strehl-out\M110-sheet\bee-3-cpl"
def rd(p):
    a = tifffile.imread(p); assert a.dtype == np.uint16, a.dtype; return a
off, on = rd(D+r"\default.tif").astype(np.float64), rd(D+r"\ca.tif").astype(np.float64)
g = off[...,1]; grad = np.abs(np.diff(g,axis=1,prepend=g[:,:1]))+np.abs(np.diff(g,axis=0,prepend=g[:1,:]))
edge = grad >= np.percentile(grad,90)
Y = lambda a: 0.2126*a[...,0]+0.7152*a[...,1]+0.0722*a[...,2]
ry = np.abs(off[...,0]-Y(off))[edge]
dR = np.abs(on[...,0]-off[...,0]); dG = np.abs(on[...,1]-off[...,1])
print("THE OPERATIVE VARIABLE: q/P, not the form of the statistic\n")
for bits in [12,10,8,6]:
    q = (2.0**(16-bits))**2/12.0
    print("  %2d-bit: quantisation power q = step^2/12 = %10.1f DN^2" % (bits,q))
    for lab,P,N in [("edge |R-Y| (my headline)", ry.var(), ry.size),
                    ("per-px |dR| (%px changed)", (dR**2).mean(), 1),
                    ("per-px |dG| (the D=10.8 numerator)", (dG**2).mean(), 1)]:
        print("      %-36s P=%12.1f  q/P=%9.5f  N=%d" % (lab,P,q/P,N))
    print()
print("Effective cancellation: zero-mean error over N samples falls as 1/sqrt(N).")
print("  my headline averages N = %d edge pixels -> 1/sqrt(N) = %.2e" % (ry.size, 1/np.sqrt(ry.size)))
print("  M111's tiles average N ~ a small window over 1547 tiles.")
print("\nM115's asymptote needs q >~ P_noise. At 8-bit, q/P for my headline = %.5f" %
      ((2.0**8)**2/12.0/ry.var()))
print("  -> the perturbation lands 5 orders of magnitude below the measured power.")
