"""Deliberately commit the tone-curve error, to see if it reproduces 84.6%.

The clamp acts almost entirely in the darkest decile. The sRGB transfer curve
has slope ~12x linear near black. If BUILD-HULL's statistic was taken across a
curve (or on a --srgb render), a shadow-localised difference would be inflated
several-fold. Same pixels, same arms, same band -- only the curve differs.
"""
import sys, json
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter
def hp(x,s=1.0): return float(np.sqrt(np.mean((x-gaussian_filter(x,s,mode="reflect"))**2)))
def srgb(v):
    v=np.clip(v,0,1)
    return np.where(v<=0.0031308, v*12.92, 1.055*np.power(v,1/2.4)-0.055)
def G(p):
    a=tifffile.imread(p); assert a.dtype==np.uint16; return a[:,:,1].astype(np.float32)/65535.0
for tag,cp,up in [(sys.argv[i],sys.argv[i+1],sys.argv[i+2]) for i in range(1,len(sys.argv),3)]:
    c,u=G(cp),G(up)
    lin=100.0*hp(c)/hp(u)
    s=100.0*hp(srgb(c))/hp(srgb(u))
    # gamma 2.2 variant, and a p95-gradient variant
    g22=100.0*hp(np.power(c,1/2.2))/hp(np.power(u,1/2.2))
    def p95grad(x):
        gy,gx=np.gradient(x); return float(np.percentile(np.sqrt(gy*gy+gx*gx),95))
    pg_lin=100.0*p95grad(c)/p95grad(u)
    pg_srgb=100.0*p95grad(srgb(c))/p95grad(srgb(u))
    print("%-22s  LINEAR(correct)=%6.2f%%   sRGB-curve=%6.2f%%   gamma2.2=%6.2f%%   p95grad-lin=%6.2f%%   p95grad-sRGB=%6.2f%%"
          % (tag,lin,s,g22,pg_lin,pg_srgb))
