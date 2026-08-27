"""Price the plane-Nyquist wall: the SAME pin, the SAME bracket, the SAME
registration, with the gather as the ONLY variable.

STREHL_FULLRES_GATHER=0 is the per-phase-plane gather that BUILD-SHARP:4665-4669
describes, which band-limits every CFA phase to 0.25 cyc/output px before the
election.  Unset is the shipping default, which gathers every output pixel from
a full-resolution demosaic of the frame.

Both arms are re-rendered end to end -- master AND all 33 single-frame
references -- because the single-frame path also runs warp_frame_in_place and
is NOT invariant under the flag (verified by hash: DDF3AD2E vs 3BEA3CD9).
Comparing a gather-off master against gather-on references would be a
mismatched gauge, which is the trap that killed this project's previous
sharpness metric.
"""
import os, numpy as np, softcheck as S
T=256; subj="119MSDCF"
EDGES=np.array([0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50])
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
zc=np.load(os.path.join(S.ROOT,"cache",f"{subj}--srgb--T256.npz"))
coefs=zc["coefs"]; N=int(zc["N"])
sel=np.argsort(zc["m_lo"])[::-1][:300]
oy=zc["oy"][sel].astype(int); ox=zc["ox"][sel].astype(int)
def rings(img,yy,xx):
    H,W=img.shape; yy=np.clip(yy,0,H-T); xx=np.clip(xx,0,W-T)
    tl=np.stack([img[y:y+T,x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
    tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
    P=np.abs(np.fft.fft2(tl))**2
    return np.stack([P[:,m].mean(1) for m in masks],axis=1)
def boot(v,B=1500,seed=9):
    r=np.random.default_rng(seed); n=len(v)
    return np.percentile([np.median(v[r.integers(0,n,n)]) for _ in range(B)],[2.5,97.5])
arms={}
for name,d in [("FULLRES (shipping default)",os.path.join(S.ROOT,"srgb",subj)),
               ("PLANE gather (=0, the wall)",os.path.join(S.ROOT,"srgb-gatheroff",subj))]:
    M=S.load_luma(os.path.join(d,"master.tiff"),"srgb")
    Mr=rings(M,oy,ox); Fr=np.zeros((N,300,len(masks)))
    for k in range(N):
        F=S.load_luma(os.path.join(d,f"f{k:03d}.tiff"),"srgb")
        dy,dx=S.disp_at(coefs[k],oy.astype(float),ox.astype(float)).T
        Fr[k]=rings(F,np.round(oy+dy).astype(int),np.round(ox+dx).astype(int)); del F
    Pn=np.median(Fr[:,:,-1],axis=0)
    rng=np.random.default_rng(53)
    probe=rng.standard_normal((64,T,T)).astype(np.float32)*WIN
    scale=float((np.abs(np.fft.fft2(probe))**2)[:,masks[-1]].mean())
    sig=np.sqrt(np.maximum(Pn,0)/scale)
    Nr=np.zeros((N+1,300,len(masks)))
    for k in range(N+1):
        tl=np.empty((300,T,T),np.float32)
        for j,(y,x) in enumerate(zip(oy,ox)):
            tl[j]=M[y:y+T,x:x+T]+sig[j]*rng.standard_normal((T,T)).astype(np.float32)
        tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
        P=np.abs(np.fft.fft2(tl))**2
        Nr[k]=np.stack([P[:,m].mean(1) for m in masks],axis=1)
    arms[name]=(Mr,Fr,Nr)
print(f"{subj}: charged deficit, shipping grid, gather is the only variable\n")
print(f"  {'band cyc/px':>12s} {'PLANE (wall)':>22s} {'FULLRES (shipped)':>22s} {'gain':>7s}")
for b in range(len(masks)):
    row=[]
    for name in ["PLANE gather (=0, the wall)","FULLRES (shipping default)"]:
        Mr,Fr,Nr=arms[name]
        dfl=Mr[:,b]/np.maximum(Fr[:,:,b].max(0),1e-30)
        nul=np.median(Nr[0,:,b]/np.maximum(Nr[1:,:,b].max(0),1e-30))
        ch=dfl/nul; row.append((np.median(ch),boot(ch)))
    star=" *" if abs(EDGES[b]-0.20)<1e-9 else "  "
    print(f" {star}{EDGES[b]:.2f}-{EDGES[b+1]:.2f} {row[0][0]:9.4f} [{row[0][1][0]:.4f},{row[0][1][1]:.4f}]"
          f" {row[1][0]:9.4f} [{row[1][1][0]:.4f},{row[1][1][1]:.4f}] {row[1][0]/row[0][0]:7.3f}x")
