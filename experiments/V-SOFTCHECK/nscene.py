"""SCENE / NOISE DECOMPOSITION DOWN THE DEPTH LADDER.

Question: the tone lane found scene ratio collapsing to 0.060-0.180 on bee against
external comparators.  Does scene detail fall MONOTONICALLY with N on ONE subject at
matched focus range?  If yes the N-dilution mechanism is demonstrated; if it peaks
and declines it is a two-limb coverage/dilution trade and the collapse needs another
cause.

MATCHED BANDWIDTH THROUGHOUT.  Every term below is the mean power in the SAME radial
ring of the SAME Hann-windowed T=256 tile FFT.  Nothing mixes a band-limited
statistic with a full-band one -- that is the mistake that made the tone lane's
decomposition degenerate on 3 of 3 arms.

TWO NOISE ESTIMATORS ARE BUILT, AND ESTIMATOR A IS EXPECTED TO FAIL.
  A  flat-ROI:  noise = ring power on low-contrast tiles.
  B  HF-corner: noise = ring power at 0.45-0.50 cyc/px on the SAME detail tiles,
                extrapolated flat.  Level-matched by construction because it is the
                same pixels.

A is not asserted to be noise, it is TESTED, by two facts that noise must satisfy:
  A1 the flat tiles must sit at the same signal level as the detail tiles, because
     shot noise scales with level;
  A2 the term must not RISE with N.  Averaging more frames cannot manufacture noise.
     If it rises, and if it correlates with the scene term, it is scene.
B's load-bearing assumption is that merge/demosaic noise is WHITE from 0.20 to 0.50,
so that one ring predicts another.  That is also tested, not asserted, on the ring
shape at 0.30-0.50 where scene is weakest.  A verdict is printed only for the
estimators that survive.
"""
import os, sys, numpy as np, softcheck as S
from ncurve import align_int, T, NT
ROOT=r"C:\dev\strehl-out\V-SOFTCHECK\ncurve"
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
E=[0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50]
MASK=[(R>=E[i])&(R<E[i+1]) for i in range(len(E)-1)]
LO=(R>=0.02)&(R<0.05); NB=len(MASK); HF=NB-1     # HF ring = 0.45-0.50
def prof(img,ys,xs):
    out=np.empty((len(ys),NB),np.float64)
    for k,(y,x) in enumerate(zip(ys,xs)):
        t=img[y:y+T,x:x+T].astype(np.float32)
        P=np.abs(np.fft.fft2((t-t.mean())*WIN))**2
        for b in range(NB): out[k,b]=P[MASK[b]].mean()
    return out
subj=sys.argv[1]; d=os.path.join(ROOT,subj)
fs=sorted(f for f in os.listdir(d) if f.startswith("master-N") and f.endswith(".tiff"))
ns=[int(f[8:11]) for f in fs]; Nx=max(ns)
B=S.load_luma(os.path.join(d,f"master-N{Nx:03d}.tiff"),"srgb"); H,W=B.shape
gy=[];gx=[];en=[];lv=[]
MG=64                                   # shift headroom, applied ONCE so the
for y in range(MG,H-T-MG,T):            # tile set is identical across every arm
    for x in range(MG,W-T-MG,T):
        t=B[y:y+T,x:x+T].astype(np.float32); m=t.mean()
        gy.append(y);gx.append(x);lv.append(m)
        en.append((np.abs(np.fft.fft2((t-m)*WIN))**2)[LO].mean())
gy=np.array(gy);gx=np.array(gx);en=np.array(en);lv=np.array(lv)
o=np.argsort(en)[::-1]; dy,dx=gy[o[:NT]],gx[o[:NT]]
tgt=np.median(lv[o[:NT]])
c=o[int(0.80*len(o)):]; c=c[np.argsort(np.abs(lv[c]-tgt))]
fy,fx=gy[c[:NT]],gx[c[:NT]]
print(f"{subj}  scene/noise vs depth   pin 9b05d0b7   matched bandwidth, T={T}\n")
mm=abs(np.median(lv[c[:NT]])-tgt)/max(tgt,1e-9)
print(f"  detail tiles {len(dy)}  level {tgt:8.1f}")
print(f"  flat   tiles {len(fy)}  level {np.median(lv[c[:NT]]):8.1f}   level mismatch {mm*100:5.1f}%")
tot={};flt={}
for f,n in zip(fs,ns):
    M=S.load_luma(os.path.join(d,f),"srgb"); sy,sx=align_int(B,M)
    assert max(abs(sy),abs(sx))<=MG, f"shift {sy},{sx} exceeds margin {MG}"
    tot[n]=prof(M,dy+sy,dx+sx); flt[n]=prof(M,fy+sy,fx+sx); del M
T_=lambda n,b: np.median(tot[n][:,b]); F_=lambda n,b: np.median(flt[n][:,b])
print("\n  COMMISSIONING ESTIMATOR A (flat-ROI)")
okA=True
if mm>0.15:
    print(f"    A1 level match  FAIL  {mm*100:.1f}% > 15%; shot noise scales with level"); okA=False
else: print(f"    A1 level match  pass  {mm*100:.1f}%")
r=F_(Nx,3)/F_(min(ns),3); sc=[T_(n,3)-F_(n,3) for n in ns]
cc=np.corrcoef(sc,[F_(n,3) for n in ns])[0,1]
if r>1.2:
    print(f"    A2 not-rising   FAIL  flat term rises {r:.2f}x from N={min(ns)} to N={Nx}")
    print(f"                          and correlates {cc:.4f} with the scene term -> it is scene")
    okA=False
else: print(f"    A2 not-rising   pass  {r:.2f}x")
print(f"    ESTIMATOR A {'ACCEPTED' if okA else 'REFUSED -- no ratio will be printed from it'}")
print("\n  COMMISSIONING ESTIMATOR B (HF-corner, white extrapolation)")
sh=[F_(Nx,b) for b in range(5,NB)]
flat=max(sh)/min(sh)
print("    ring power on flat tiles, N=%d:  %s"%(Nx," ".join(
      f"{E[b]:.2f}-{E[b+1]:.2f}:{F_(Nx,b):.3e}" for b in range(5,NB))))
okB = flat<=2.0
print(f"    B1 whiteness 0.30-0.50  {'pass' if okB else 'FAIL'}  max/min {flat:.2f} (need <=2.0)")
neg=[(n,b) for n in ns for b in (3,4,5) if T_(n,b)-T_(n,HF)<=0]
print(f"    B2 non-degenerate       {'pass' if not neg else 'FAIL '+str(neg)}  scene>0 in all {len(ns)*3} arm-bands")
okB = okB and not neg
print(f"    ESTIMATOR B {'ACCEPTED' if okB else 'REFUSED'}")
if not okB:
    print("\n  A and B both refused. ESTIMATOR C: bound the noise floor instead of estimating it.")
    print("    C does not decompose. It asks whether a decomposition is NEEDED, by bounding")
    print("    how much of the detail-tile power could possibly be noise. Among tiles within")
    print("    +-15%% of the detail tiles' LEVEL (so shot noise is matched), the SMALLEST ring")
    print("    power is an upper bound on the noise floor at that level: any tile's power is")
    print("    scene + noise >= noise. This can only ever support 'noise is small'. It is")
    print("    incapable of supporting 'noise is large', and is not used for that.")
    sel=np.where(np.abs(lv-tgt)<=0.15*tgt)[0]
    print(f"\n    level-matched tiles: {len(sel)}  (level {tgt:.0f} +-15%%)")
    if len(sel)<30: sys.exit("\n  VOID: too few level-matched tiles to bound the floor.")
    py=gy[sel]; px=gx[sel]
    for b in (3,4,5):
        print(f"\n  band {E[b]:.2f}-{E[b+1]:.2f} cyc/output px")
        print(f"    {'N':>5s} {'total/total(Nmax)':>18s} {'noise floor <=':>15s} {'noise frac <=':>14s}")
        fr={}
        for n in ns:
            M=S.load_luma(os.path.join(d,f"master-N{n:03d}.tiff"),"srgb")
            sy,sx=align_int(B,M)
            k=(py+sy>=0)&(py+sy<H-T)&(px+sx>=0)&(px+sx<W-T)
            fl=np.percentile(prof(M,py[k]+sy,px[k]+sx)[:,b],1.0); del M
            fr[n]=fl/T_(n,b)
            print(f"    {n:5d} {T_(n,b)/T_(Nx,b):18.4f} {fl:15.3e} {fr[n]*100:13.1f}%")
        mx=max(fr.values())
        if mx<0.05:
            print(f"    noise <= {mx*100:.1f}%% of total in EVERY arm -> total is scene to within {mx*100:.1f}%%;")
            print(f"    the depth curve above IS the scene curve, no decomposition required.")
        else:
            print(f"    noise bound reaches {mx*100:.1f}%% -- too large to ignore, and neither A nor B")
            print(f"    can separate it. VOID for this band.")
    sys.exit(0)
print("\n  DECOMPOSITION (estimator B): P_scene = P_total - P_noise(0.45-0.50), same tiles")
for b in (3,4,5):
    s={n:T_(n,b)-T_(n,HF) for n in ns}; nz={n:T_(n,HF) for n in ns}
    print(f"\n  band {E[b]:.2f}-{E[b+1]:.2f} cyc/output px")
    print(f"    {'N':>5s} {'scene/scene(Nmax)':>18s} {'noise/noise(Nmax)':>18s} {'noise frac':>11s}")
    for n in ns:
        print(f"    {n:5d} {s[n]/s[Nx]:18.4f} {nz[n]/nz[Nx]:18.4f} {nz[n]/T_(n,b)*100:10.1f}%")
    pk=max(ns,key=lambda n:s[n]/s[Nx])
    mono=all(s[ns[i]]>=s[ns[i+1]] for i in range(len(ns)-1))
    print(f"    scene peaks at N={pk}    monotone-falling in N: {mono}"
          f"    deficit at Nmax vs peak: {s[pk]/s[Nx]:.4f}")
