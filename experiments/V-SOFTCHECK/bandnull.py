"""BAND-LIMITED null.  A band-limited statistic needs a band-limited control.

My earlier null (N+1 iid noised masters) was evaluated on the AGGREGATE DoG
statistic and produced a single inflation figure, 0.6-0.9%.  That figure
cannot license a per-band claim: the order-statistic inflation of a per-site
max over N frames depends on the per-tile SNR, and SNR varies strongly with
frequency.  So run the identical null THROUGH THE RING INSTRUMENT and report
the inflation SEPARATELY IN EVERY BAND, then charge each band its own.

Noise level is estimated from the frames themselves, per tile, as the median
over frames of the power in the TOP ring (0.45-0.50 c/opx), where the band
map says most content is not scene.  Because those tiles are content-rich,
that estimate INCLUDES some real content and therefore OVERSTATES the noise,
which inflates the null and makes the charged deficit conservative.

The white-noise assumption is checked, not assumed: the flatness of the
frames' PSD across the top three rings is printed.
"""
import os, sys, numpy as np, softcheck as S
T, GAU = 128, "lin"
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
def boot(v,B=1500,seed=5):
    rng=np.random.default_rng(seed); n=len(v)
    m=[np.median(v[rng.integers(0,n,n)]) for _ in range(B)]
    return np.percentile(m,2.5), np.percentile(m,97.5)
for subj in sys.argv[1:]:
    z=np.load(os.path.join(S.ROOT,"cache",f"{subj}--ring.npz"))
    Mr,Fr,E,oy,ox = z["Mr"],z["Fr"],z["EDGES"],z["oy"],z["ox"]
    N,nt,nb = Fr.shape
    masks=[(R>=a)&(R<b) for a,b in zip(E[:-1],E[1:])]
    d=os.path.join(S.ROOT,GAU,subj); M=S.load_luma(os.path.join(d,"master.tiff"),GAU); H,W=M.shape
    flat = Fr[:,:,-3:].mean(0)
    print(f"\n=== {subj}  N={N}, {nt} tiles")
    print(f"  frames' PSD across top three rings (flat => white): "
          f"{flat[:,0].mean():.4g} {flat[:,1].mean():.4g} {flat[:,2].mean():.4g}"
          f"   ratio hi/lo {flat[:,2].mean()/flat[:,0].mean():.3f}")
    Pn = np.median(Fr[:,:,-1], axis=0)                    # per-tile noise PSD estimate
    rng=np.random.default_rng(19)
    probe=(rng.standard_normal((nt,T,T)).astype(np.float32))*WIN
    scale=float(np.abs(np.fft.fft2(probe))[:, masks[-1]].__pow__(2).mean())
    sig=np.sqrt(np.maximum(Pn,0)/scale)
    def ringstack(img, yy, xx):
        tl=np.stack([img[y:y+T,x:x+T] for y,x in zip(yy,xx)]).astype(np.float32)
        tl=(tl-tl.mean(axis=(1,2),keepdims=True))*WIN
        P=np.abs(np.fft.fft2(tl))**2
        return np.stack([P[:,m].mean(1) for m in masks],axis=1)
    yy=oy.astype(int); xx=ox.astype(int)
    Nr=np.zeros((N+1,nt,nb))
    for k in range(N+1):
        noisy=M.copy()
        for j,(y,x) in enumerate(zip(yy,xx)):
            noisy[y:y+T,x:x+T]=M[y:y+T,x:x+T]+sig[j]*rng.standard_normal((T,T)).astype(np.float32)
        Nr[k]=ringstack(noisy,yy,xx)
    print(f"  {'band c/opx':>12s} {'deficit raw':>22s} {'band null':>20s} {'CHARGED':>20s} {'verdict':>9s}")
    for b in range(nb):
        dfl=Mr[:,b]/np.maximum(Fr[:,:,b].max(0),1e-30)
        nul=Nr[0,:,b]/np.maximum(Nr[1:,:,b].max(0),1e-30)
        ch=dfl/np.median(nul)
        dc=boot(dfl); cc=boot(ch); nm=np.median(nul)
        v="SOFT" if cc[1]<1.0 else ("SHARP" if cc[0]>1.0 else "parity")
        print(f"  {E[b]:.2f}-{E[b+1]:.2f} {np.median(dfl):9.4f} [{dc[0]:.4f},{dc[1]:.4f}]"
              f" {nm:9.4f} {np.median(ch):9.4f} [{cc[0]:.4f},{cc[1]:.4f}] {v:>9s}")
