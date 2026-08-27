"""N-invariance: how much sharpness does bracket DEPTH cost the merge?

WHY THIS NEEDS NO REFERENCE FRAMES.  The previous run divided both masters by the
same per-site max over all 63 frames.  A common denominator cancels in the ratio
between arms, so the depth effect is exactly a MASTER-TO-MASTER band power ratio.
That removes 299 single-frame renders and the whole registration prepass from the
critical path.  It also removes the order statistic entirely: there is no max over
N anywhere in this estimator, so trap 2 and trap 3 cannot apply to it.

WHAT IS HELD FIXED.  Focus RANGE (every subset keeps the first and last frame),
exposure (one explicit --exposure for every arm; the statistic is linear in gain
and auto-exposure would choose a different one per arm -- trap 1), pin, tile
coordinates, band edges, window.  Only DENSITY varies.

WHAT THIS CANNOT SEPARATE ON ITS OWN.  At small N the subset genuinely stops
covering every focus plane, so the master is soft because no input frame was sharp
there -- a real coverage limit, not a merge defect.  That confound falls with N and
the merge-dilution effect rises with it, so the curve is expected to RISE then FALL.
Only the falling limb is a merge defect.  Coverage is separated explicitly in
ncoverage.py, which does use the full per-site reference.
"""
import os, sys, numpy as np, softcheck as S
T=256; NT=300
EDGES=np.array([0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40])
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
LO=(R>=0.02)&(R<0.05)

def rings(img,yy,xx):
    H,W=img.shape; yy=np.clip(yy,0,H-T); xx=np.clip(xx,0,W-T)
    tl=np.stack([img[y:y+T,x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
    tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
    P=np.abs(np.fft.fft2(tl))**2
    return np.stack([P[:,m].mean(1) for m in masks],axis=1)

def pick_tiles(M):
    """Tiles chosen by LOW-band energy only (0.02-0.05 cyc/px).  Low frequencies
    survive defocus, so this cannot prefer tiles where any particular arm happens
    to be sharp -- the selecting band is disjoint from every reported band."""
    H,W=M.shape; step=T; ys=range(0,H-T,step); xs=range(0,W-T,step)
    oy=[];ox=[];sc=[]
    for y in ys:
        for x in xs:
            t=M[y:y+T,x:x+T].astype(np.float32); t=(t-t.mean())*WIN
            P=np.abs(np.fft.fft2(t))**2
            oy.append(y);ox.append(x);sc.append(P[LO].mean())
    o=np.argsort(sc)[::-1][:NT]
    return np.array(oy)[o],np.array(ox)[o]

def align_int(A,B):
    """Integer-only shift.  Sub-pixel resampling would add blur to the measured
    quantity, so the registration is deliberately coarse and lossless."""
    cy,cx=A.shape[0]//2,A.shape[1]//2; w=1024
    a=A[cy-w//2:cy+w//2,cx-w//2:cx+w//2].astype(np.float32); a-=a.mean()
    b=B[cy-w//2:cy+w//2,cx-w//2:cx+w//2].astype(np.float32); b-=b.mean()
    cc=np.fft.ifft2(np.fft.fft2(a)*np.conj(np.fft.fft2(b))).real
    sy,sx=np.unravel_index(np.argmax(cc),cc.shape)
    sy=int(sy)-w if sy>w//2 else int(sy); sx=int(sx)-w if sx>w//2 else int(sx)
    return sy,sx

def boot(v,B_=1500,seed=23):
    r=np.random.default_rng(seed); n=len(v)
    return np.percentile([np.median(v[r.integers(0,n,n)]) for _ in range(B_)],[2.5,97.5])

def gauss(img,sig):
    r=int(3*sig); k=np.exp(-0.5*(np.arange(-r,r+1)/sig)**2); k/=k.sum()
    o=np.apply_along_axis(lambda m:np.convolve(m,k,"same"),0,img.astype(np.float32))
    return np.apply_along_axis(lambda m:np.convolve(m,k,"same"),1,o)

if __name__=="__main__" and sys.argv[1]=="commission":
    M=S.load_luma(sys.argv[2],"srgb")
    oy,ox=pick_tiles(M); base=rings(M,oy,ox)
    print("COMMISSIONING the master-to-master depth statistic")
    print(f"  baseline {os.path.basename(sys.argv[2])}  {M.shape}  {NT} tiles, T={T}\n")
    print(f"  {'arm':<34s} {'0.20-0.25':>10s} {'0.30-0.35':>10s}  expected      result")
    arms=[("NULL  identical copy",       M.copy(),                 "no change"),
          ("DEGRADE  blur sigma 1.0",    gauss(M,1.0),             "must FALL"),
          ("IMPROVE  unsharp +0.8",      None,                     "must RISE"),
          ("REFPERT  baseline blurred",  None,                     "must move")]
    ok=True
    for name,img,exp in arms:
        if name.startswith("IMPROVE"):
            img=M.astype(np.float32)+0.8*(M.astype(np.float32)-gauss(M,1.2))
        if name.startswith("REFPERT"):
            r=rings(M,oy,ox)/np.maximum(rings(gauss(M,1.0),oy,ox),1e-30)
        else:
            r=rings(img,oy,ox)/np.maximum(base,1e-30)
        v3=np.median(r[:,3]); v5=np.median(r[:,5])
        if   name.startswith("NULL"):    good=abs(v3-1)<1e-9 and abs(v5-1)<1e-9
        elif name.startswith("DEGRADE"): good=v3<0.97 and v5<0.97
        elif name.startswith("IMPROVE"): good=v3>1.03 and v5>1.03
        else:                            good=abs(v3-1)>0.03
        ok&=good
        print(f"  {name:<34s} {v3:10.4f} {v5:10.4f}  {exp:<12s} {'PASS' if good else 'FAIL'}")
    print(f"\n  COMMISSIONING {'PASSED' if ok else 'FAILED'} -- the estimator moves in BOTH")
    print( "  directions and is inert under a null, so a fall it reports is a measurement.")
    sys.exit(0 if ok else 1)
