"""113MSDCF on the SHIPPING GRID: their focus construction AND the merge
deficit, same subject their R=2.419 was measured on.

Registration is derived from the half-res fit rather than refitted, which is
exact rather than approximate.  The affine model is
    dy = a0 + a1*y + a2*x
On the full-res grid y'=2y, x'=2x, and the true displacement doubles, so
    dy' = 2*dy = 2*a0 + a1*(2y) + a2*(2x) = (2*a0) + a1*y' + a2*x'
i.e. ONLY the constant term scales; the linear terms are dimensionless
gradients and are unchanged.  The script checks this empirically: with correct
registration the reference is STRONGER and the ratio must come out LOWER than
with zero displacement (established earlier: misregistration weakens the
denominator and inflates the ratio).  If the scaled-coef ratio is not below
the literal-coordinate ratio, the derivation is wrong and the run aborts.
"""
import os, sys, numpy as np, softcheck as S
T=256; subj="113MSDCF"; NT=300; OFF=20
EDGES=np.array([0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50])
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
z=np.load(os.path.join(S.ROOT,"cache",f"{subj}--lin--T128.npz"))
coefs=z["coefs"].copy(); N=int(z["N"])
sel=np.argsort(z["m_lo"])[::-1][:NT]
oy=(z["oy"][sel]*2).astype(int); ox=(z["ox"][sel]*2).astype(int)
coefs[:,0,:]*=2.0
d=os.path.join(S.ROOT,"srgb",subj)
def rings(img,yy,xx):
    H,W=img.shape; yy=np.clip(yy,0,H-T); xx=np.clip(xx,0,W-T)
    tl=np.stack([img[y:y+T,x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
    tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
    P=np.abs(np.fft.fft2(tl))**2
    return np.stack([P[:,m].mean(1) for m in masks],axis=1)
M=S.load_luma(os.path.join(d,"master.tiff"),"srgb")
assert M.shape==(4688,7032), M.shape
Mr=rings(M,oy,ox)
Fr=np.zeros((N,NT,len(masks))); Fl=np.zeros_like(Fr)
for k in range(N):
    F=S.load_luma(os.path.join(d,f"f{k:03d}.tiff"),"srgb")
    dy,dx=S.disp_at(coefs[k],oy.astype(float),ox.astype(float)).T
    Fr[k]=rings(F,np.round(oy+dy).astype(int),np.round(ox+dx).astype(int))
    Fl[k]=rings(F,oy,ox); del F
n_arw=len([f for f in os.listdir(rf"D:\personal\macro\{subj}") if f.lower().endswith(".arw")])
assert N==n_arw, f"COMPLETE-BRACKET CHECK FAILED {N} vs {n_arw}"
b=3
reg=np.median(Mr[:,b]/np.maximum(Fr[:,:,b].max(0),1e-30))
lit=np.median(Mr[:,b]/np.maximum(Fl[:,:,b].max(0),1e-30))
print(f"{subj}: complete bracket N={N}=={n_arw} RAW, shipping grid {M.shape}")
print(f"  registration self-check: scaled-coef ratio {reg:.4f} vs literal-coord {lit:.4f}")
if not reg < lit:
    sys.exit(f"ABORT: scaled coefficients did not improve the reference ({reg:.4f} !< {lit:.4f})")
print(f"  PASS: scaled coefficients strengthen the reference, derivation confirmed\n")
Pn=np.median(Fr[:,:,-1],axis=0)
rng=np.random.default_rng(31)
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
def boot(v,B=2000,seed=13):
    r=np.random.default_rng(seed); n=len(v)
    return np.percentile([np.median(v[r.integers(0,n,n)]) for _ in range(B)],[2.5,97.5])
print("MERGE DEFICIT, shipping grid, each band charged its own null:")
for i in range(len(masks)):
    dfl=Mr[:,i]/np.maximum(Fr[:,:,i].max(0),1e-30)
    nul=np.median(Nr[0,:,i]/np.maximum(Nr[1:,:,i].max(0),1e-30))
    ch=dfl/nul; ci=boot(ch)
    star=" *" if i==b else "  "
    v="SOFT" if ci[1]<1 else ("SHARP" if ci[0]>1 else "parity")
    print(f" {star}{EDGES[i]:.2f}-{EDGES[i+1]:.2f} cyc/px  null {nul:.4f}  charged "
          f"{np.median(ch):.4f} [{ci[0]:.4f},{ci[1]:.4f}]  {v}")
sb=[0,1,2]
selp=Fr[:,:,sb].mean(2); repp=Fr[:,:,b]
best=selp.argmax(0); off=np.where(best+OFF<N,best+OFF,best-OFF)
ok=(off>=0)&(off<N); idx=np.arange(NT)[ok]
r=repp[best[ok],idx]/np.maximum(repp[off[ok],idx],1e-30)
ci=boot(r,seed=17)
wf=int(np.bincount(best).argmax()); wo=wf+OFF if wf+OFF<N else wf-OFF
rw=np.median(repp[wf]/np.maximum(repp[wo],1e-30))
print(f"\nTHEIR FOCUS CONSTRUCTION on their own subject, shipping grid:")
print(f"  select 0.05-0.20 cyc/px, report 0.20-0.25 cyc/px (disjoint), fixed {OFF}-step offset")
print(f"  PER-TILE  R = {np.median(r):.3f}  CI [{ci[0]:.3f}, {ci[1]:.3f}]   n={len(r)} tiles"
      f"   {100*(r>1).mean():.0f}% of tiles R>1")
print(f"  WHOLE-FRAME R = {rw:.3f}  -> suppression {np.median(r)/rw:.2f}x")
print(f"  their reported value: R = 2.419  CI [1.961, 3.063]")
