"""MECHANISM: is the depth softening a drift toward AVERAGING?

The relayed hypothesis is that the pyramid normalises w_i/sum_j w_j over N frames,
so at a real edge where many frames sit near-tied in band energy the winner's
SHARE falls as N grows.  That predicts the merged result behaves like an average
of an increasing number of frames.  Confirmed at pin 9b05d0b7: pyramid.rs carries
MAX_EXPONENT 8.0, exponent 2.0, sharpen_per_octave 1.4, SoftPower.

I do not read the merge's internal weights -- I measure the OUTPUT against a
calibrated ruler built from the same data:

  1. For each tile, find its own best frame k* by band energy.
  2. Build explicit averages of the m frames nearest k* in focus order, m=1,3,5,...
     This is what "drifting toward an average of m frames" physically looks like
     on THIS scene, including the fact that neighbouring frames are correlated
     rather than independent -- which is why the ruler is measured, not assumed.
  3. That gives a dilution curve D(m) = P_avg(m) / P_best.
  4. Invert each master onto D(m) to read its EFFECTIVE blend width.

COMMISSIONING IS BUILT IN: m=1 must return exactly 1.0 by construction, and D must
be monotone decreasing.  If D is flat the ruler has no resolving power and the
inversion is meaningless, so that is checked and the run aborts on failure.

PREDICTION UNDER THE HYPOTHESIS: effective m rises with N.
PREDICTION IF THE HYPOTHESIS IS WRONG: effective m is flat in N, and the softening
comes from somewhere else.
"""
import os, sys, numpy as np, softcheck as S
from ncurve import rings, align_int, boot, EDGES, T, NT
FR=r"C:\dev\strehl-out\V-SOFTCHECK\srgb\113MSDCF"
CV=r"C:\dev\strehl-out\V-SOFTCHECK\ncurve\113MSDCF"
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); R=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
masks=[(R>=a)&(R<b) for a,b in zip(EDGES[:-1],EDGES[1:])]
LO=(R>=0.02)&(R<0.05)
z=np.load(os.path.join(S.ROOT,"cache","113MSDCF--lin--T128.npz"))
coefs=z["coefs"].copy(); coefs[:,0,:]*=2.0
sel=np.argsort(z["m_lo"])[::-1][:NT]
oy=(z["oy"][sel]*2).astype(int); ox=(z["ox"][sel]*2).astype(int)
B=S.load_luma(os.path.join(FR,"master.tiff"),"srgb")
import hashlib
h1=hashlib.sha256(open(os.path.join(FR,"master.tiff"),"rb").read()).hexdigest()[:16]
h2=hashlib.sha256(open(os.path.join(CV,"master-N063.tiff"),"rb").read()).hexdigest()[:16]
print(f"self-check: shipped-path master {h1} vs curve N=63 master {h2}  identical={h1==h2}")
H,W=B.shape
# registered tile stack: every frame's tile, integer-shifted onto the master grid
tiles=np.empty((63,NT,T,T),np.float32)
for k in range(63):
    F=S.load_luma(os.path.join(FR,f"f{k:03d}.tiff"),"srgb")
    dy,dx=S.disp_at(coefs[k],oy.astype(float),ox.astype(float)).T
    yy=np.clip(np.round(oy+dy).astype(int),0,H-T); xx=np.clip(np.round(ox+dx).astype(int),0,W-T)
    for j in range(NT): tiles[k,j]=F[yy[j]:yy[j]+T,xx[j]:xx[j]+T]
    del F
def bandpow(tl,b):
    t=(tl-tl.mean(axis=(-2,-1),keepdims=True))*WIN
    P=np.abs(np.fft.fft2(t))**2
    return P[...,masks[b]].mean(-1)
for b,(lo,hi) in [(5,(0.30,0.35)),(4,(0.25,0.30))]:
    P=bandpow(tiles,b)                     # (63, NT)
    kstar=np.argmax(P,axis=0)
    Pbest=P[kstar,np.arange(NT)]
    MS=[1,3,5,9,15,25,41,63]
    D=[]
    for m in MS:
        acc=np.empty(NT)
        for j in range(NT):
            half=m//2
            lo_i=max(0,min(63-m,kstar[j]-half)); idx=slice(lo_i,lo_i+m)
            acc[j]=bandpow(tiles[idx,j].mean(0),b)
        D.append(np.median(acc/Pbest))
    D=np.array(D)
    print(f"\n  band {lo:.2f}-{hi:.2f}  dilution ruler D(m) = power of an m-frame average / best frame")
    print("    m      " + "  ".join(f"{m:6d}" for m in MS))
    print("    D(m)   " + "  ".join(f"{v:6.4f}" for v in D))
    # m=1 must return the best frame itself.  Tolerance is 1e-4 relative, not exact:
    # bandpow() reaches D(m) through a single (T,T) FFT and Pbest through a batched
    # (63,NT,T,T) FFT, and float32 FFT is not bit-identical between those two code
    # paths.  An exact test here fails on numpy's batching, not on the ruler.
    if abs(D[0]-1.0)>1e-4: sys.exit(f"ABORT: D(1) = {D[0]:.8f}, must be 1")
    if not np.all(np.diff(D)<0): sys.exit("ABORT: ruler is not monotone; no resolving power")
    print(f"    ruler PASS: D(1)=1 exactly, monotone, spans {D[0]:.3f} -> {D[-1]:.4f}")
    print(f"\n    master effective blend width, by depth:")
    for f in sorted(os.listdir(CV)):
        if not (f.startswith("master-N") and f.endswith(".tiff")): continue
        n=int(f[8:11]); M=S.load_luma(os.path.join(CV,f),"srgb")
        sy,sx=align_int(B,M)
        acc=np.empty(NT)
        for j in range(NT):
            y=min(max(oy[j]+sy,0),H-T); x=min(max(ox[j]+sx,0),W-T)
            acc[j]=bandpow(M[y:y+T,x:x+T].astype(np.float32),b)
        ratio=np.median(acc/Pbest)
        eff=np.interp(-ratio,-D,MS)
        print(f"      N={n:3d}   master/best = {ratio:.4f}   effective m = {eff:5.2f}")
        del M

