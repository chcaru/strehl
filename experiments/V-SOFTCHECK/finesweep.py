"""Cliff or smooth? Fine-band deficit sweep against an independently
re-implemented gather MTF.  Discriminator fixed in PREREG-nyquist.md.

gather_mtf is re-derived here from the KERNEL DEFINITION only (restore.rs tap()),
not imported, and is validated against the four values the shipping tests pin
before it is used for anything.
"""
import os, sys, numpy as np, softcheck as S
T=256
def tap(a):
    a=abs(a)
    if a<1.0:  return 1.5*a**3-2.5*a**2+1.0
    if a<2.0:  return -0.5*a**3+2.5*a**2-4.0*a+2.0
    return 0.0
def gather_mtf(f,phases=64):
    acc=0.0
    for p in range(phases):
        phi=(p+0.5)/phases
        ds=[n-phi for n in range(-1,3)]
        w=[tap(d) for d in ds]; s=sum(w)
        if abs(s)<1e-12: continue
        re=sum(v/s*np.cos(2*np.pi*f*d) for d,v in zip(ds,w))
        im=sum(v/s*np.sin(2*np.pi*f*d) for d,v in zip(ds,w))
        acc+=np.hypot(re,im)
    return acc/phases
print("validating my gather_mtf against the four values shipping tests pin:")
bad=0
for f,want in [(0.25,0.9402),(0.35,0.8211),(0.40,0.7425),(0.50,0.6251)]:
    got=gather_mtf(f); ok=abs(got-want)<5e-4
    bad+= (not ok)
    print(f"   MTF({f:.2f} cyc/plane-sample) = {got:.5f}  pinned {want}  {'OK' if ok else 'MISMATCH'}")
if bad: sys.exit("my re-implementation disagrees with the shipping pin; refusing to measure")
print("   validated -- my implementation reproduces the shipping kernel\n")
EDGES=np.round(np.arange(0.05,0.5001,0.01),4)
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
nb=len(masks)
for subj in sys.argv[1:]:
    zc=np.load(os.path.join(S.ROOT,"cache",f"{subj}--lin--T128.npz"))
    coefs=zc["coefs"].copy(); N=int(zc["N"]); coefs[:,0,:]*=2.0
    sel=np.argsort(zc["m_lo"])[::-1][:300]
    oy=(zc["oy"][sel]*2).astype(int); ox=(zc["ox"][sel]*2).astype(int)
    d=os.path.join(S.ROOT,"srgb",subj)
    def rings(img,yy,xx):
        H,W=img.shape; yy=np.clip(yy,0,H-T); xx=np.clip(xx,0,W-T)
        tl=np.stack([img[y:y+T,x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
        tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
        P=np.abs(np.fft.fft2(tl))**2
        return np.stack([P[:,m].mean(1) for m in masks],axis=1)
    M=S.load_luma(os.path.join(d,"master.tiff"),"srgb")
    Mr=rings(M,oy,ox); Fr=np.zeros((N,300,nb))
    for k in range(N):
        F=S.load_luma(os.path.join(d,f"f{k:03d}.tiff"),"srgb")
        dy,dx=S.disp_at(coefs[k],oy.astype(float),ox.astype(float)).T
        Fr[k]=rings(F,np.round(oy+dy).astype(int),np.round(ox+dx).astype(int)); del F
    Pn=np.median(Fr[:,:,-1],axis=0)
    rng=np.random.default_rng(41)
    probe=rng.standard_normal((64,T,T)).astype(np.float32)*WIN
    scale=float((np.abs(np.fft.fft2(probe))**2)[:,masks[-1]].mean())
    sig=np.sqrt(np.maximum(Pn,0)/scale)
    Nr=np.zeros((N+1,300,nb))
    for k in range(N+1):
        tl=np.empty((300,T,T),np.float32)
        for j,(y,x) in enumerate(zip(oy,ox)):
            tl[j]=M[y:y+T,x:x+T]+sig[j]*rng.standard_normal((T,T)).astype(np.float32)
        tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
        P=np.abs(np.fft.fft2(tl))**2
        Nr[k]=np.stack([P[:,m].mean(1) for m in masks],axis=1)
    Dfine=np.array([np.median(Mr[:,b]/np.maximum(Fr[:,:,b].max(0),1e-30))
                    / np.median(Nr[0,:,b]/np.maximum(Nr[1:,:,b].max(0),1e-30)) for b in range(nb)])
    np.savez_compressed(os.path.join(S.ROOT,"cache",f"{subj}--fine.npz"),
                        Mr=Mr,Fr=Fr,Nr=Nr,EDGES=EDGES,D=Dfine,oy=oy,ox=ox,N=N)
    ctr=(EDGES[:-1]+EDGES[1:])/2
    def D_at(f):
        return Dfine[int(np.argmin(np.abs(ctr-f)))]
    drop=D_at(0.11)-D_at(0.39); win=D_at(0.23)-D_at(0.27)
    frac=win/drop if abs(drop)>1e-9 else float("nan")
    print(f"=== {subj}  N={N}  shipping grid, charged, 0.01-wide bands")
    print(f"  {'f_out':>7s} {'f_plane':>8s} {'D measured':>11s} {'gatherMTF^2':>12s} {'D/D(0.11)':>10s} {'pred/pred':>10s}")
    for f in np.arange(0.11,0.401,0.02):
        pm=gather_mtf(2*f)**2
        p0=gather_mtf(2*0.11)**2
        star=" *" if abs(f-0.25)<0.011 else "  "
        print(f" {star}{f:6.3f} {2*f:8.3f} {D_at(f):11.4f} {pm:12.4f} "
              f"{D_at(f)/D_at(0.11):10.4f} {pm/p0:10.4f}")
    print(f"\n  PRE-REGISTERED DISCRIMINATOR")
    print(f"    total decline D(0.11)-D(0.39) = {drop:+.4f}")
    print(f"    window decline D(0.23)-D(0.27) = {win:+.4f}")
    print(f"    W/D_drop = {frac:.3f}   (uniform expectation 0.143)")
    v = "CLIFF" if frac>0.40 else ("SMOOTH" if frac<0.20 else "AMBIGUOUS")
    print(f"    VERDICT: {v}")
