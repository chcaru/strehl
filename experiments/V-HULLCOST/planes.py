"""Retention per output plane. G = 0.5*(G1+G2) (averaged pair, no resample);
R and B are SINGLE CFA planes (cosite-resampled by a fixed subpixel shift that
is identical in both arms). Bounds the worry that averaging G1/G2 understates
the clamp's per-plane cost. Both arms from ONE binary, so R/B are comparable."""
import sys
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter
def hp(x,s=1.0): return float(np.sqrt(np.mean((x-gaussian_filter(x,s,mode="reflect"))**2)))
print("%-22s %10s %10s %10s" % ("subject","R ret%","G ret%","B ret%"))
for i in range(1,len(sys.argv),3):
    t,cp,up=sys.argv[i],sys.argv[i+1],sys.argv[i+2]
    C=tifffile.imread(cp); U=tifffile.imread(up)
    assert C.dtype==np.uint16 and U.dtype==np.uint16
    r=[]
    for k in range(3):
        c=C[:,:,k].astype(np.float32); u=U[:,:,k].astype(np.float32)
        r.append(100.0*hp(c)/hp(u))
    print("%-22s %9.2f%% %9.2f%% %9.2f%%" % (t,r[0],r[1],r[2]))
