"""Is the shipping-grid deficit an artefact of the srgb tone curve?

The srgb gauge carries a tone curve whose provenance says DO NOT MEASURE
NUMERICALLY.  Both sides of my ratio get the SAME curve from the SAME binary,
so to first order the local slope cancels -- but "to first order" is an
argument, not a measurement.  Measure it: restrict to tiles whose mean level
sits in a narrow mid-tone window, where the curve's slope is near-constant and
therefore cannot differentially shape master vs frames.  If the deficit at
0.20-0.25 cyc/px survives on mid-tone-only tiles, the curve did not make it.

Also reports the half-res(lin) vs full-res(srgb) comparison at MATCHED
PHYSICAL FREQUENCY, which is the real reason the two gauges disagree.
"""
import os, numpy as np, softcheck as S
subj="119MSDCF"
z=np.load(os.path.join(S.ROOT,"cache",f"{subj}--shipring.npz"))
Mr,Fr,Nr,E=z["Mr"],z["Fr"],z["Nr"],z["EDGES"]
zc=np.load(os.path.join(S.ROOT,"cache",f"{subj}--srgb--T256.npz"))
sel=np.argsort(zc["m_lo"])[::-1][:300]; lv=zc["m_lv"][sel]
def boot(v,B=1500,seed=11):
    r=np.random.default_rng(seed); n=len(v)
    return np.percentile([np.median(v[r.integers(0,n,n)]) for _ in range(B)],[2.5,97.5])
b=3
nul=np.median(Nr[0,:,b]/np.maximum(Nr[1:,:,b].max(0),1e-30))
dfl=Mr[:,b]/np.maximum(Fr[:,:,b].max(0),1e-30)
lo,hi=np.percentile(lv,[30,70])
mid=(lv>=lo)&(lv<=hi)
print(f"tile level range {lv.min():.0f}-{lv.max():.0f}, mid-tone window [{lo:.0f},{hi:.0f}] -> {mid.sum()} tiles\n")
for name,m in [("ALL tiles      ",np.ones(len(lv),bool)),("MID-TONE only  ",mid),
               ("DARK third     ",lv<lo),("BRIGHT third   ",lv>hi)]:
    v=dfl[m]/nul; ci=boot(v)
    print(f"  {name} n={m.sum():3d}  charged deficit at 0.20-0.25 cyc/px = "
          f"{np.median(v):.4f} [{ci[0]:.4f},{ci[1]:.4f}]")
print("\nWHY THE TWO GAUGES DISAGREE -- same physical frequency, both charged by own null:")
zl=np.load(os.path.join(S.ROOT,"cache",f"{subj}--ring.npz"))
Ml,Fl,El=zl["Mr"],zl["Fr"],zl["EDGES"]
print(f"  {'physical cyc/px':>16s} {'half-res lin gauge':>22s} {'full-res srgb gauge':>22s}")
for bl in range(len(El)-1):
    p0,p1=El[bl]/2,El[bl+1]/2
    dl=np.median(Ml[:,bl]/np.maximum(Fl[:,:,bl].max(0),1e-30))
    hit=[bs for bs in range(len(E)-1) if E[bs]<p1-1e-9 and E[bs+1]>p0+1e-9]
    if hit:
        ds=np.median([np.median(Mr[:,bs]/np.maximum(Fr[:,:,bs].max(0),1e-30)) for bs in hit])
        frac=p1/0.25
        print(f"  {p0:.3f}-{p1:.3f}    {dl:8.4f}  ({frac*100:5.1f}% of its Nyquist) {ds:8.4f}")
