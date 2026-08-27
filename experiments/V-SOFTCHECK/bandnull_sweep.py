"""How much would my band null have to be WRONG to erase the deficit?

bandnull.py estimates the per-tile noise level from the frames' top ring and
assumes that noise is white.  The printed PSD is NOT flat, so that assumption
is not exactly right.  Rather than argue about the true noise shape, bound it:
re-run the identical null with the assumed noise scaled 1x, 2x, 4x, 8x and see
at what point the null's inflation swallows the measured deficit.

An 8x noise amplitude is 64x the noise POWER.  If the deficit still survives
there, the noise-shape question cannot decide this measurement.
"""
import os, sys, numpy as np, softcheck as S
T, GAU = 128, "lin"
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
BAND=(0.20,0.25)
for subj in sys.argv[1:]:
    z=np.load(os.path.join(S.ROOT,"cache",f"{subj}--ring.npz"))
    Mr,Fr,E,oy,ox=z["Mr"],z["Fr"],z["EDGES"],z["oy"],z["ox"]
    N,nt,nb=Fr.shape
    b=int(np.argmin(np.abs(E[:-1]-BAND[0])))
    masks=[(R>=a)&(R<c) for a,c in zip(E[:-1],E[1:])]
    d=os.path.join(S.ROOT,GAU,subj); M=S.load_luma(os.path.join(d,"master.tiff"),GAU)
    Pn=np.median(Fr[:,:,-1],axis=0)
    rng=np.random.default_rng(19)
    probe=rng.standard_normal((nt,T,T)).astype(np.float32)*WIN
    scale=float((np.abs(np.fft.fft2(probe))**2)[:,masks[-1]].mean())
    sig0=np.sqrt(np.maximum(Pn,0)/scale)
    yy=oy.astype(int); xx=ox.astype(int)
    dfl=np.median(Mr[:,b]/np.maximum(Fr[:,:,b].max(0),1e-30))
    print(f"\n=== {subj}  band {E[b]:.2f}-{E[b+1]:.2f} c/opx   raw deficit {dfl:.4f}")
    for mult in (1,2,4,8):
        Nr=np.zeros((N+1,nt))
        for k in range(N+1):
            tl=np.empty((nt,T,T),np.float32)
            for j,(y,x) in enumerate(zip(yy,xx)):
                tl[j]=M[y:y+T,x:x+T]+mult*sig0[j]*rng.standard_normal((T,T)).astype(np.float32)
            tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
            Nr[k]=(np.abs(np.fft.fft2(tl))**2)[:,masks[b]].mean(1)
        nul=np.median(Nr[0]/np.maximum(Nr[1:].max(0),1e-30))
        ch=dfl/nul
        print(f"   noise x{mult}  ({mult*mult:2d}x power)  null {nul:.4f}   charged deficit {ch:.4f}"
              f"   {'SOFT' if ch<1 else 'NOT SOFT'}")
