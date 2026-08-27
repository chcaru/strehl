"""10-90% edge RISE DISTANCE on the MEDIAN step-normalised profile.

Why this and not band power: the median over hundreds of edge profiles averages
noise out, so a shorter rise distance cannot be manufactured by adding noise.
It is therefore a resolution measure that is robust to the signal/noise question
band power cannot settle.

Sites are chosen ONCE on the mean of the two arms, so both arms are profiled at
identical pixels.  Profiles are sampled along the local gradient normal at 1 px
spacing (ds=1) and the 10% / 90% crossings are found by linear interpolation.

Controls
  NULL     : the alignment-REFUSED subject (arms byte-identical) must give
             ratio exactly 1.000.
  POSITIVE : blur one arm by a known Gaussian and confirm the rise distance
             lengthens by the predicted amount (quadrature).
  SHUFFLE  : profiles at random positions/orientations must give a degenerate
             (much longer / undefined) rise.
"""
import os, sys, glob, json
import numpy as np, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from instr import step_overshoot, luma, boxblur, downsample

OUT=r"C:\dev\strehl-out\V-GATHER"
HALF, BLUR = 24, 5

def rise1090(prof, half=HALF):
    """distance in px between the 10% and 90% crossings around the centre."""
    if prof is None: return float("nan")
    t=np.arange(-half, half+1, dtype=float)
    def cross(level):
        # walk out from centre to the left for the LOW crossing, right for HIGH
        idx=np.arange(len(prof))
        s=np.sign(prof-level)
        k=np.nonzero(np.diff(s)!=0)[0]
        if k.size==0: return None
        # take the crossing nearest the centre
        c=len(prof)//2
        j=k[np.argmin(np.abs(k-c))]
        y0,y1=prof[j],prof[j+1]
        if y1==y0: return t[j]
        return t[j]+(level-y0)/(y1-y0)
    a=cross(0.10); b=cross(0.90)
    if a is None or b is None: return float("nan")
    return float(b-a)

def gauss_blur(img, sigma):
    r=int(np.ceil(3*sigma)); x=np.arange(-r,r+1,dtype=float)
    k=np.exp(-x*x/(2*sigma*sigma)); k/=k.sum()
    o=np.apply_along_axis(lambda m: np.convolve(m,k,mode="same"),0,img)
    return np.apply_along_axis(lambda m: np.convolve(m,k,mode="same"),1,o)

def sites(mean_img):
    d=step_overshoot(mean_img, half=HALF, band=(1,4), ds=1, blur=BLUR, seed=0)
    # recover the exact site list by re-running the selection deterministically
    img=downsample(np.asarray(mean_img,np.float64),1)
    b=boxblur(img,BLUR)
    gy=np.zeros_like(b); gx=np.zeros_like(b)
    gy[1:-1,:]=(b[2:,:]-b[:-2,:])*0.5; gx[:,1:-1]=(b[:,2:]-b[:,:-2])*0.5
    mag=np.hypot(gy,gx)
    m=np.zeros(mag.shape,bool); m[HALF+2:-HALF-2, HALF+2:-HALF-2]=True
    thr=float(np.percentile(mag[m],99.5))
    ys,xs=np.nonzero((mag>=thr)&m)
    rng=np.random.default_rng(0)
    if ys.size>4000:
        k=rng.choice(ys.size,4000,replace=False); ys,xs=ys[k],xs[k]
    return (ys,xs)

subs=sorted({os.path.basename(f)[:-len("-q-g0.tiff")]
             for f in glob.glob(os.path.join(OUT,"*-q-g0.tiff"))})
print(f"{'subject':30s}{'rise g0':>9s}{'rise g1':>9s}{'ratio':>8s}{'n g0':>7s}{'n g1':>7s}")
rows=[]
for s in subs:
    a=luma(tifffile.imread(os.path.join(OUT,f"{s}-q-g0.tiff"))[:,:,:3].astype(np.float64))
    b=luma(tifffile.imread(os.path.join(OUT,f"{s}-q-g1.tiff"))[:,:,:3].astype(np.float64))
    pts=sites((a+b)/2.0)
    d0=step_overshoot(a,half=HALF,band=(1,4),ds=1,blur=BLUR,pts_override=pts)
    d1=step_overshoot(b,half=HALF,band=(1,4),ds=1,blur=BLUR,pts_override=pts)
    r0,r1=rise1090(d0["prof"]), rise1090(d1["prof"])
    rows.append((s,r0,r1,r1/r0 if r0==r0 and r0 else float("nan"),d0["n"],d1["n"]))
    print(f"{s:30s}{r0:9.3f}{r1:9.3f}{(r1/r0):8.3f}{d0['n']:7d}{d1['n']:7d}",flush=True)
    if s=="foam":
        keep=(a,b,pts)
    del a,b
print()
a,b,pts=keep
print("POSITIVE CONTROL on foam g0: blur by a known Gaussian, rise must lengthen")
base=rise1090(step_overshoot(a,half=HALF,band=(1,4),ds=1,blur=BLUR,pts_override=pts)["prof"])
for sg in (0.5,1.0,2.0):
    ab_=gauss_blur(a,sg)
    r=rise1090(step_overshoot(ab_,half=HALF,band=(1,4),ds=1,blur=BLUR,pts_override=pts)["prof"])
    pred=np.sqrt(base**2+(2.563*sg)**2)   # 10-90 of a gaussian = 2.563 sigma
    print(f"  sigma={sg:4.1f}  rise {base:6.3f} -> {r:6.3f}   quadrature prediction {pred:6.3f}",flush=True)
print()
print("SHUFFLE CONTROL on foam g0 (random positions/orientations):")
sh=step_overshoot(a,half=HALF,band=(1,4),ds=1,blur=BLUR,seed=11,shuffle=True)
print(f"  n={sh['n']}  rise={rise1090(sh['prof']):.3f}   (real edges gave {base:.3f})")
json.dump(rows,open(os.path.join(OUT,"rise.json"),"w"),indent=1)
