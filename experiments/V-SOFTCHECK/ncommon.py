"""Separate the two things the halved-N run confounded.

ntest.py gave each arm its own reference: arm A a max over 63 frames, arm B a
max over 32.  A max over fewer draws is SMALLER, which inflates arm B's ratio on
its own -- trap 2, the subsampled reference.  So that run cannot tell "the merge
got better" from "the denominator got weaker".

Here BOTH masters are divided by the SAME denominator: the per-site max over all
63 frames.  The denominator is then literally identical between arms and every
difference is the merge.  This is CONSERVATIVE against the finding, because arm
B is charged against sharp frames its merge was never given.

Also reported: the N-driven inflation of the DENOMINATOR alone (max over 63 vs
max over 32 of the same frames), which is the order statistic itself, measured
rather than assumed.
"""
import os, sys, numpy as np, softcheck as S
T=256; NT=300
EDGES=np.array([0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40])
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
z=np.load(os.path.join(S.ROOT,"cache","113MSDCF--lin--T128.npz"))
coefs=z["coefs"].copy(); coefs[:,0,:]*=2.0
sel=np.argsort(z["m_lo"])[::-1][:NT]
oy=(z["oy"][sel]*2).astype(int); ox=(z["ox"][sel]*2).astype(int)
A=os.path.join(S.ROOT,"srgb","113MSDCF")
B=os.path.join(S.ROOT,"srgb-stride","113MSDCF-s2")
def rings(img,yy,xx):
    H,W=img.shape; yy=np.clip(yy,0,H-T); xx=np.clip(xx,0,W-T)
    tl=np.stack([img[y:y+T,x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
    tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
    P=np.abs(np.fft.fft2(tl))**2
    return np.stack([P[:,m].mean(1) for m in masks],axis=1)
def boot(v,B_=1500,seed=17):
    r=np.random.default_rng(seed); n=len(v)
    return np.percentile([np.median(v[r.integers(0,n,n)]) for _ in range(B_)],[2.5,97.5])
MA=S.load_luma(os.path.join(A,"master.tiff"),"srgb")
MB=S.load_luma(os.path.join(B,"master.tiff"),"srgb")
MAr=rings(MA,oy,ox); MBr=rings(MB,oy,ox)   # ntest measured 0,0 offset between arms
Fr=np.zeros((63,NT,len(masks)))
for k in range(63):
    F=S.load_luma(os.path.join(A,f"f{k:03d}.tiff"),"srgb")
    dy,dx=S.disp_at(coefs[k],oy.astype(float),ox.astype(float)).T
    Fr[k]=rings(F,np.round(oy+dy).astype(int),np.round(ox+dx).astype(int)); del F
ev=list(range(0,63,2))
den63=np.maximum(Fr.max(0),1e-30); den32=np.maximum(Fr[ev].max(0),1e-30)
print("113MSDCF  pin 9b05d0b7 / 44C2F2CD2E5B2894   COMMON denominator = max over all 63\n")
print(f"  {'band':>11s} {'A: merge63/max63':>21s} {'B: merge32/max63':>21s} {'B-A':>8s}  {'max63/max32':>11s}")
for bnd in range(len(masks)):
    ra=MAr[:,bnd]/den63[:,bnd]; rb=MBr[:,bnd]/den63[:,bnd]
    ca=boot(ra); cb=boot(rb)
    ordstat=np.median(den63[:,bnd]/den32[:,bnd])
    d=np.median(rb)-np.median(ra)
    sig="  SIG" if (cb[0]>ca[1] or ca[0]>cb[1]) else "  ns"
    print(f"   {EDGES[bnd]:.2f}-{EDGES[bnd+1]:.2f} {np.median(ra):8.4f} [{ca[0]:.4f},{ca[1]:.4f}]"
          f" {np.median(rb):8.4f} [{cb[0]:.4f},{cb[1]:.4f}] {d:+8.4f} {ordstat:11.4f}{sig}")
print("\n  max63/max32 is the order statistic itself: how much the denominator alone")
print("  grows when the reference doubles in density.  Anything above that column is")
print("  a real difference between the two merges, not a sampling artifact.")
