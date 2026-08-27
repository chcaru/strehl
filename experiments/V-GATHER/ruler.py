"""Focused probe of flat-on-ruler-cpl, the only subject with a genuinely sharp
edge (10-90 rise ~5 px).  rise.py read the NEW arm as 12% SOFTER there.  Before
believing that, test the three ways it could be an artefact:
  (a) the min_step / plateau gates keep DIFFERENT profile subsets per arm
      (279 vs 253) -> force the INTERSECTION so both medians use identical edges;
  (b) too few profiles -> vary edge_pct to change n by ~10x;
  (c) no resolution estimate -> bootstrap the site list and get a spread.
Plus band power, which is an independent view of the same question.
"""
import os, sys, json
import numpy as np, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instr import luma, boxblur, downsample, bilinear

OUT=r"C:\dev\strehl-out\V-GATHER"
S="flat-on-ruler-cpl"
HALF, BLUR = 24, 5

def profiles(img, pts, half=HALF, blur=BLUR, min_step_frac=0.08, plateau_frac=0.18):
    """returns dict site_index -> normalised profile (only those passing gates)"""
    img=np.asarray(img,np.float64)
    b=boxblur(img,blur)
    gy=np.zeros_like(b); gx=np.zeros_like(b)
    gy[1:-1,:]=(b[2:,:]-b[:-2,:])*0.5; gx[:,1:-1]=(b[:,2:]-b[:,:-2])*0.5
    lo_p,hi_p=np.percentile(img,(1.0,99.0)); min_step=min_step_frac*(hi_p-lo_p)
    t=np.arange(-half,half+1,dtype=np.float64); nflat=max(3,half//7); q=max(4,half//5)
    out={}
    for i,(py,px) in enumerate(zip(*pts)):
        g=float(np.hypot(gy[py,px],gx[py,px]))
        if g<=0: continue
        ny,nx=gy[py,px]/g, gx[py,px]/g
        v=bilinear(img, py+t*ny, px+t*nx)
        lo=float(v[:nflat].mean()); hi=float(v[-nflat:].mean()); step=abs(hi-lo)
        if step<min_step: continue
        lf=abs(float(v[:q].mean())-float(v[q:2*q].mean()))
        rf=abs(float(v[-q:].mean())-float(v[-2*q:-q].mean()))
        if max(lf,rf)>plateau_frac*step: continue
        p=(v-lo)/(hi-lo)
        if hi<lo: p=p[::-1]
        out[i]=p
    return out

def rise1090(prof, half=HALF):
    if prof is None: return float("nan")
    t=np.arange(-half,half+1,dtype=float)
    def cross(level):
        s=np.sign(prof-level); k=np.nonzero(np.diff(s)!=0)[0]
        if k.size==0: return None
        c=len(prof)//2; j=k[np.argmin(np.abs(k-c))]
        y0,y1=prof[j],prof[j+1]
        return t[j] if y1==y0 else t[j]+(level-y0)/(y1-y0)
    a=cross(0.10); b=cross(0.90)
    return float("nan") if (a is None or b is None) else float(b-a)

def sitelist(mean_img, edge_pct, cap=20000, seed=0):
    b=boxblur(mean_img,BLUR)
    gy=np.zeros_like(b); gx=np.zeros_like(b)
    gy[1:-1,:]=(b[2:,:]-b[:-2,:])*0.5; gx[:,1:-1]=(b[:,2:]-b[:,:-2])*0.5
    mag=np.hypot(gy,gx)
    m=np.zeros(mag.shape,bool); m[HALF+2:-HALF-2, HALF+2:-HALF-2]=True
    thr=float(np.percentile(mag[m],edge_pct))
    ys,xs=np.nonzero((mag>=thr)&m)
    rng=np.random.default_rng(seed)
    if ys.size>cap:
        k=rng.choice(ys.size,cap,replace=False); ys,xs=ys[k],xs[k]
    return (ys,xs)

a=luma(tifffile.imread(os.path.join(OUT,f"{S}-q-g0.tiff"))[:,:,:3].astype(np.float64))
b=luma(tifffile.imread(os.path.join(OUT,f"{S}-q-g1.tiff"))[:,:,:3].astype(np.float64))
mean=(a+b)/2.0

print("(a)+(b) rise on the INTERSECTION of surviving profiles, at several edge_pct")
print(f"{'edge_pct':>9s}{'n_sites':>9s}{'n_common':>10s}{'rise g0':>9s}{'rise g1':>9s}{'ratio':>8s}")
res=[]
for ep in (99.9, 99.5, 99.0, 98.0, 95.0):
    pts=sitelist(mean, ep)
    p0=profiles(a,pts); p1=profiles(b,pts)
    common=sorted(set(p0)&set(p1))
    if not common: print(f"{ep:9.1f}  no common profiles"); continue
    m0=np.median(np.stack([p0[i] for i in common]),axis=0)
    m1=np.median(np.stack([p1[i] for i in common]),axis=0)
    r0,r1=rise1090(m0),rise1090(m1)
    res.append((ep,len(pts[0]),len(common),r0,r1,r1/r0))
    print(f"{ep:9.1f}{len(pts[0]):9d}{len(common):10d}{r0:9.3f}{r1:9.3f}{r1/r0:8.3f}",flush=True)

print()
print("(c) bootstrap resolution of the ratio at edge_pct=99.0 (resample common sites)")
pts=sitelist(mean,99.0); p0=profiles(a,pts); p1=profiles(b,pts)
common=sorted(set(p0)&set(p1))
A=np.stack([p0[i] for i in common]); B=np.stack([p1[i] for i in common])
rng=np.random.default_rng(1); rat=[]
for _ in range(40):
    k=rng.choice(len(common),len(common),replace=True)
    rat.append(rise1090(np.median(B[k],axis=0))/rise1090(np.median(A[k],axis=0)))
rat=np.array(rat)
print(f"  n_common={len(common)}  ratio mean={rat.mean():.4f} sd={rat.std():.4f} "
      f"min={rat.min():.4f} max={rat.max():.4f}")

print()
print("median profile around the edge (edge_pct=99.0, common sites)")
m0=np.median(A,axis=0); m1=np.median(B,axis=0)
for k in range(HALF-8, HALF+9):
    print(f"  t={k-HALF:+3d}  g0={m0[k]:8.4f}  g1={m1[k]:8.4f}  d={m1[k]-m0[k]:+8.4f}")

print()
print("independent view: radial band power ratio g1/g0, 2048 centred crop")
def bp(y,bands):
    n=2048; h,w=y.shape
    c=y[h//2-n//2:h//2+n//2, w//2-n//2:w//2+n//2]
    w2=np.outer(np.hanning(n),np.hanning(n))
    F=np.fft.fftshift(np.fft.fft2((c-c.mean())*w2)); P=(np.abs(F)**2)/(w2**2).sum()
    fy=np.fft.fftshift(np.fft.fftfreq(n))[:,None]; fx=np.fft.fftshift(np.fft.fftfreq(n))[None,:]
    rr=np.hypot(fy,fx)
    return [float(P[(rr>=lo)&(rr<hi)].mean()) for lo,hi in bands]
bands=[(0.05,0.15),(0.15,0.25),(0.25,0.35),(0.35,0.50)]
P0=bp(a,bands); P1=bp(b,bands)
for (lo,hi),x,y in zip(bands,P0,P1):
    print(f"  {lo:.2f}-{hi:.2f} cyc/px   g0={x:12.1f}  g1={y:12.1f}  x{y/x:6.3f}")
