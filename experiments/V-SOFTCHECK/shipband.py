"""The deficit ON THE SHIPPING GRID, in the units the band map is written in.

Established structurally, not inferred: SHIP-V4 masters are 7032x4688, the
full sensor photosite count, so on the shipped product 1 output pixel is
1 photosite and "cyc/px" is unambiguous.  My primary gauge (lin) is strehl's
half-size linear output, where the same physical frequency reads 2x higher.
This script therefore re-measures on the FULL-RESOLUTION srgb gauge, whose
pixel grid IS the shipped product's, so every band label below can be read
directly against the band map.

Both sides of every ratio come from the same renderer, the same pin, the same
flags and the same code path; only STREHL_ONLY_FRAME differs.  Each band is
charged its OWN order-statistic null.
"""
import os, sys, numpy as np, softcheck as S
T = 256
subj = sys.argv[1] if len(sys.argv) > 1 else "119MSDCF"
NT = 300
EDGES = np.array([0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50])
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
z=np.load(os.path.join(S.ROOT,"cache",f"{subj}--srgb--T256.npz"))
oy,ox,coefs,m_lo,N = z["oy"],z["ox"],z["coefs"],z["m_lo"],int(z["N"])
sel=np.argsort(m_lo)[::-1][:NT]; oy,ox=oy[sel].astype(int),ox[sel].astype(int)
d=os.path.join(S.ROOT,"srgb",subj)
def rings(img,yy,xx,H,W):
    yy=np.clip(yy,0,H-T); xx=np.clip(xx,0,W-T)
    tl=np.stack([img[y:y+T,x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
    tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
    P=np.abs(np.fft.fft2(tl))**2
    return np.stack([P[:,m].mean(1) for m in masks],axis=1)
M=S.load_luma(os.path.join(d,"master.tiff"),"srgb"); H,W=M.shape
assert (H,W)==(4688,7032), f"not the shipping grid: {(H,W)}"
Mr=rings(M,oy,ox,H,W)
Fr=np.zeros((N,NT,len(masks)))
for k in range(N):
    F=S.load_luma(os.path.join(d,f"f{k:03d}.tiff"),"srgb")
    dy,dx=S.disp_at(coefs[k],oy.astype(float),ox.astype(float)).T
    Fr[k]=rings(F,np.round(oy+dy).astype(int),np.round(ox+dx).astype(int),H,W)
    del F
n_arw=len([f for f in os.listdir(rf"D:\personal\macro\{subj}") if f.lower().endswith(".arw")])
assert N==n_arw, f"COMPLETE-BRACKET CHECK FAILED {N} vs {n_arw}"
print(f"complete bracket confirmed: N={N} renders == {n_arw} RAW frames")
Pn=np.median(Fr[:,:,-1],axis=0)
rng=np.random.default_rng(23)
probe=rng.standard_normal((64,T,T)).astype(np.float32)*WIN
scale=float((np.abs(np.fft.fft2(probe))**2)[:,masks[-1]].mean())
sig=np.sqrt(np.maximum(Pn,0)/scale)
Nr=np.zeros((N+1,NT,len(masks)))
for k in range(N+1):
    tl=np.empty((NT,T,T),np.float32)
    for j,(y,x) in enumerate(zip(oy,ox)):
        tl[j]=M[y:y+T,x:x+T]+sig[j]*rng.standard_normal((T,T)).astype(np.float32)
    tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
    P=np.abs(np.fft.fft2(tl))**2
    Nr[k]=np.stack([P[:,m].mean(1) for m in masks],axis=1)
def boot(v,B=1500,seed=7):
    r=np.random.default_rng(seed); n=len(v)
    m=[np.median(v[r.integers(0,n,n)]) for _ in range(B)]
    return np.percentile(m,2.5),np.percentile(m,97.5)
print(f"\n{subj}  SHIPPING GRID 7032x4688, bands in cyc/px = cyc/photosite\n")
print(f"  {'band cyc/px':>12s} {'raw deficit':>21s} {'own null':>9s} {'CHARGED deficit':>22s}  verdict")
for b in range(len(masks)):
    dfl=Mr[:,b]/np.maximum(Fr[:,:,b].max(0),1e-30)
    nul=Nr[0,:,b]/np.maximum(Nr[1:,:,b].max(0),1e-30)
    nm=np.median(nul); ch=dfl/nm; cc=boot(ch); dc=boot(dfl)
    v="SOFT" if cc[1]<1 else ("SHARP" if cc[0]>1 else "parity")
    flag="  <-- promotable band" if abs(EDGES[b]-0.20)<1e-9 else ""
    print(f"  {EDGES[b]:.2f}-{EDGES[b+1]:.2f} {np.median(dfl):8.4f} [{dc[0]:.4f},{dc[1]:.4f}]"
          f" {nm:9.4f} {np.median(ch):8.4f} [{cc[0]:.4f},{cc[1]:.4f}] {v:>7s}{flag}")
np.savez_compressed(os.path.join(S.ROOT,"cache",f"{subj}--shipring.npz"),
                    Mr=Mr,Fr=Fr,Nr=Nr,EDGES=EDGES,oy=oy,ox=ox,N=N)
