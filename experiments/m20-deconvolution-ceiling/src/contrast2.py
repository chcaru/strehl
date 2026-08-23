import numpy as np, rawpy, glob, os, exifread
from scipy.ndimage import uniform_filter
W=9; BLACK=512
def lstd(a,w=W):
    m=uniform_filter(a,w); m2=uniform_filter(a*a,w)
    return np.sqrt(np.maximum(m2-m*m,0))
files=sorted(glob.glob(r"C:\dev\macro\test\109MSDCF\*.ARW"))
with open(files[0],'rb') as fh:
    tags=exifread.process_file(fh, details=False)
iso=None
for k in ('EXIF ISOSpeedRatings','Image ISOSpeedRatings'):
    if k in tags: iso=int(str(tags[k]).split(',')[0].strip('[] '))
print(f"ISO from EXIF: {iso}")
g=iso/436.8; RN_e=1.47 if iso>=400 else 4.20
print(f"noise model: g = ISO/436.8 = {g:.5f} DN/e-, RN = {RN_e} e-  -> sigma(S) = sqrt(g*S + (RN*g)^2)")
best=None
for i,f in enumerate(files):
    with rawpy.imread(f) as r:
        gp=r.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
    s=lstd(gp)
    sig_n=np.sqrt(np.maximum(g*np.maximum(uniform_filter(gp,W),0)+ (RN_e*g)**2, 1e-6))
    signal=np.sqrt(np.maximum(s*s-sig_n*sig_n,0.0))
    rel=sig_n/np.maximum(signal,1e-6)          # sigma_rel at this pixel in THIS frame
    best = rel if best is None else np.minimum(best,rel)   # best (lowest sigma_rel) over the stack
    if i==0: print(f"  plane {gp.shape}, per-pixel sigma ranges {sig_n.min():.1f}..{sig_n.max():.1f} DN")
    if (i+1)%7==0: print(f"  ...{i+1}/{len(files)} frames")
print()
print("=== sigma_rel = local noise sigma / local SIGNAL std, taking each pixel's BEST frame ===")
for p in (5,10,25,50,75,90):
    print(f"  p{p:<3}: {np.percentile(best,p):8.4f}")
CROSS=0.3440   # measured crossover: below this the deconvolution merge beats plain selection
for label,c in (("est-sel prior (implementable)",0.3440),("oracle prior (upper bound)",0.03/0.0872*(0.05/0.03))):
    frac=float(np.mean(best<c))
    print(f"  fraction of pixels below crossover {c:.4f} [{label}]: {frac*100:5.1f}%  -> deconvolution wins there")
np.save(r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files\best_rel.npy", best.astype(np.float32))
