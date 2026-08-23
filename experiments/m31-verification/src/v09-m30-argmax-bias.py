"""V09 -- M30 fact 242 uses an UNREGULARISED argmax (rule 4 forbids this for
output).  At a clipped pixel the neighbourhood is flat, so Sobel magnitude is
~0 and the argmax FLEES the clipped frame.  Does the 0.075% survive a
regularised index?  Also: min S over the FULL green plane, not the centre crop."""
import os, glob
import numpy as np, rawpy
from scipy.ndimage import uniform_filter, sobel, median_filter
CACHE=r"C:\dev\blog\death-of-software\projects\strehl\experiments\m30-hdr-cobracket\out\cache"
BLACK,WHITE=512.0,15360.0
cube=np.load(os.path.join(CACHE,"cube-coffee-bean.npy"))
n=cube.shape[0]; sig=cube-BLACK
foc=np.empty(sig.shape,np.float32)
for k in range(n):
    foc[k]=uniform_filter(np.hypot(sobel(sig[k],0),sobel(sig[k],1)),5)
cl=cube>=WHITE
yy,xx=np.mgrid[0:1500,0:1500]
ever=cl.any(0)
print(f"coffee-bean {n} frames, clip-prone px {ever.sum()} ({100*ever.mean():.4f}%)")
print(f"{'best-frame rule':38s}{'clip @ gathered':>16s}{'clip|clip-prone':>17s}{'idx speckle':>13s}")
def speckle(b):
    return float((b[1:,:]!=b[:-1,:]).mean())
rows=[]
b=np.argmax(foc,0)
rows.append(("raw argmax (as published)",b))
for R in (7,15,31,61):
    fs=np.empty_like(foc)
    for k in range(n): fs[k]=uniform_filter(foc[k],R)
    rows.append((f"argmax of focus box-smoothed R={R}",np.argmax(fs,0)))
    del fs
for R in (9,25):
    rows.append((f"median-filtered argmax map {R}x{R}",median_filter(b,size=R)))
for lab,bb in rows:
    g=cl[bb,yy,xx]
    print(f"{lab:38s}{100*g.mean():15.4f}%{100*g[ever].mean():16.2f}%{100*speckle(bb):12.2f}%")
print(f"{'uniform random frame':38s}"
      f"{100*cl[np.random.default_rng(11).integers(0,n,size=b.shape),yy,xx].mean():15.4f}%"
      f"{100*np.mean(cl.sum(0)[ever]/n):16.2f}%{'':13s}")

print("\n--- does the focus measure flee clipped frames? ---")
fl=foc.reshape(n,-1)[:,ever.ravel()]; cc=cl.reshape(n,-1)[:,ever.ravel()]
print(f"  median focus value at clip-prone px, IN clipped frames   : {np.median(fl[cc]):8.2f}")
print(f"  median focus value at clip-prone px, in unclipped frames : {np.median(fl[~cc]):8.2f}")
print(f"  fraction of clip-prone px whose max-focus frame is clipped: "
      f"{100*cc[np.argmax(fl,0),np.arange(fl.shape[1])].mean():.2f}%")

print("\n--- min S over the FULL green plane (not the 1500^2 centre crop) ---")
for name,iso,folder,step in (("coffee-bean",50.,r"D:\personal\macro\coffee-bean",2),
                             ("112MSDCF",500.,r"D:\personal\macro\112MSDCF",1),
                             ("109MSDCF",160.,r"D:\personal\macro\109MSDCF",1)):
    fs=sorted(glob.glob(os.path.join(folder,"*.ARW")))[::step]
    g=iso/436.8; rn=4.20 if iso<400 else 1.47; bnd=rn*rn*g
    mn=1e9; below=0; tot=0
    for f in fs[::max(len(fs)//6,1)]:
        with rawpy.imread(f) as r:
            a=r.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
        mn=min(mn,float(a.min())); below+=int((a<bnd).sum()); tot+=a.size
    print(f"  {name:13s} boundary {bnd:6.3f} DN   min S full plane {mn:8.1f}   "
          f"% below boundary {100*below/tot:.6f}%")
