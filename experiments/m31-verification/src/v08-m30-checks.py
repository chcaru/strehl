"""V08 -- M30: (a) read-noise boundary as DOCUMENTED vs as IMPLEMENTED,
(b) Monte-Carlo test of the fixed-light neutrality identity (not a re-evaluation
of the same closed form), (c) clipping-at-gathered-frame against a random-frame
null and a test of the 'highlights are out of focus' mechanism."""
import os, glob
import numpy as np, rawpy
from scipy.ndimage import uniform_filter, sobel
CACHE=r"C:\dev\blog\death-of-software\projects\strehl\experiments\m30-hdr-cobracket\out\cache"
BLACK, WHITE = 512.0, 15360.0
ST=[("coffee-bean",50.0,r"D:\personal\macro\coffee-bean",2),
    ("112MSDCF",500.0,r"D:\personal\macro\112MSDCF",1),
    ("109MSDCF",160.0,r"D:\personal\macro\109MSDCF",1)]

print("=== 0. cube integrity: independent decode of frame 0 ===")
for name,iso,folder,step in ST:
    c=np.load(os.path.join(CACHE,f"cube-{name}.npy"),mmap_mode="r")
    f=sorted(glob.glob(os.path.join(folder,"*.ARW")))[::step][0]
    with rawpy.imread(f) as r:
        g=r.raw_image_visible[0::2,1::2].astype(np.float32)
    h,w=g.shape; y,x=(h-1500)//2,(w-1500)//2
    mine=g[y:y+1500,x:x+1500]
    print(f"  {name:13s} cube{c.shape} maxabsdiff {np.abs(mine-np.asarray(c[0])).max():.6g}")

print("\n=== 1. read-noise-limited fraction: documented vs implemented boundary ===")
print(f"{'stack':13s}{'doc RN^2*g':>11s}{'impl RN^2':>11s}{'min S best':>12s}{'min S cube':>12s}"
      f"{'% < doc (best)':>15s}{'% < doc (all frames)':>22s}")
best={}
for name,iso,folder,step in ST:
    cube=np.load(os.path.join(CACHE,f"cube-{name}.npy"))
    n=cube.shape[0]; sig=cube-BLACK
    rn=4.20 if iso<400 else 1.47; g=iso/436.8
    bf=np.full(sig.shape[1:],-1.,np.float32); bi=np.zeros(sig.shape[1:],np.int64)
    for k in range(n):
        f=uniform_filter(np.hypot(sobel(sig[k],0),sobel(sig[k],1)),5).astype(np.float32)
        m=f>bf; bf[m],bi[m]=f[m],k
    yy,xx=np.mgrid[0:1500,0:1500]
    S=sig[bi,yy,xx]
    best[name]=(cube,sig,bi,S,iso,rn,g)
    print(f"{name:13s}{rn*rn*g:11.3f}{rn*rn:11.3f}{S.min():12.2f}{sig.min():12.2f}"
          f"{100*(S<rn*rn*g).mean():14.4f}%{100*(sig<rn*rn*g).mean():21.4f}%")

print("\n=== 2. Monte-Carlo test of the neutrality identity (5m base vs m base+m@+2EV) ===")
rng=np.random.default_rng(3)
for L,iso in ((2000.,160.),(300.,500.),(50.,50.),(10.,160.)):
    g=iso/436.8; rn=4.20 if iso<400 else 1.47; R2=(rn*g)**2
    m=200; N=400000
    # all-base: 5m frames of mean L
    e=L/g
    base=(rng.poisson(e,size=(N,5*m))*g+rng.normal(0,np.sqrt(R2),size=(N,5*m)))
    est_all=base.mean(1)
    b2=(rng.poisson(e,size=(N,m))*g+rng.normal(0,np.sqrt(R2),size=(N,m)))
    p2=(rng.poisson(4*e,size=(N,m))*g+rng.normal(0,np.sqrt(R2),size=(N,m)))/4.
    vb=g*L+R2; vp=(g*4*L+R2)/16.
    wb, wp = 1/vb, 1/vp
    est_hdr=(b2.mean(1)*m*wb+p2.mean(1)*m*wp)/(m*wb+m*wp)
    r_sim=est_all.std()/est_hdr.std()
    r_theory=np.sqrt((vb/(5*m))/(1/(m/vb+m/vp)))
    print(f"  L={L:7.1f} DN ISO {iso:5.0f}: sd ratio all/hdr  simulated {r_sim:.5f}   "
          f"closed form {r_theory:.5f}   (1.0 = exact neutrality)")

print("\n=== 3. clipping: gathered vs random-frame null vs union ===")
print(f"{'stack':13s}{'gathered':>10s}{'mean/frame':>12s}{'random null':>13s}{'union(any)':>12s}"
      f"{'shuffled bi':>13s}")
for name,(cube,sig,bi,S,iso,rn,g) in best.items():
    n=cube.shape[0]; yy,xx=np.mgrid[0:1500,0:1500]
    cl=cube>=WHITE
    gathered=cl[bi,yy,xx].mean()
    meanframe=cl.mean()
    ridx=np.random.default_rng(11).integers(0,n,size=bi.shape)
    randnull=cl[ridx,yy,xx].mean()
    union=cl.any(0).mean()
    sh=bi.copy().ravel(); np.random.default_rng(5).shuffle(sh); sh=sh.reshape(bi.shape)
    shuffled=cl[sh,yy,xx].mean()
    print(f"{name:13s}{100*gathered:9.4f}%{100*meanframe:11.4f}%{100*randnull:12.4f}%"
          f"{100*union:11.4f}%{100*shuffled:12.4f}%")

print("\n=== 4. mechanism: is the focus measure AVOIDING clipped frames? ===")
name="coffee-bean"; cube,sig,bi,S,iso,rn,g=best[name]
n=cube.shape[0]
cl=cube>=WHITE
ever=cl.any(0)
print(f"  {name}: {ever.sum()} px clip in >=1 frame ({100*ever.mean():.4f}%)")
nclip=cl.sum(0)[ever]
print(f"  of those, median #frames clipped {np.median(nclip):.0f} of {n}; "
      f"expected clipped-if-random-choice {100*np.mean(nclip/n):.2f}%")
yy,xx=np.mgrid[0:1500,0:1500]
print(f"  actually clipped at the argmax frame: {100*cl[bi,yy,xx][ever].mean():.2f}%")
print(f"  best-frame index at clip-prone px: median {np.median(bi[ever]):.1f}  "
      f"IQR {np.percentile(bi[ever],25):.0f}-{np.percentile(bi[ever],75):.0f}   "
      f"| all px: median {np.median(bi):.1f} IQR {np.percentile(bi,25):.0f}-{np.percentile(bi,75):.0f}"
      f"   (n={n} frames; 'depth extremes' would be near 0 or {n-1})")
