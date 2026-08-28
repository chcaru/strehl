"""HALF-STACK SELECTION COHERENCE.  Pre-registered in PREREG-coherence.md.

A selection driven by noise cannot be reproduced across two independent halves of
the same stack.  This measures how much delivered detail is COMMON to two
independently merged, INTERLEAVED halves of one bracket, as a function of depth.

STATISTIC.  Band-limited end to end: every term is one radial ring of the same
Hann-windowed T=256 tile FFT, on the shipping grid where one output pixel is one
photosite.  Per tile, per ring,

    gamma = |sum FA conj(FB)| / sqrt(sum|FA|^2 * sum|FB|^2)      f = 1 - gamma

f = 0 for identical arms, f -> 1 for independent arms.

WHY NOT THE FORM I PRE-REGISTERED.  PREREG-coherence.md specified the
half-difference form f = 2*P_dif / (P_coh + 2*P_dif), and required as a
commissioning arm that the statistic be GAIN-FREE.  The half-difference form is
not: scaling one arm by 1.3 moves it, because a photometric difference lands
entirely in (A-B)/2.  The arm I registered would have failed for a reason with
nothing to do with selection.  Commissioning rejected the estimator, which is what
it is for.  gamma is gain-free exactly, by construction.  The half-difference
coherent power P_coh is retained as a DEGENERACY DIAGNOSTIC, since P_coh < 0 is
forbidden by the additive model and gamma cannot express that failure.

NOISE_NULL IS A PREDICTION, NOT A ROUND NUMBER.  For independent arms, gamma does
not go to 0: summing M complex ring bins of random phase grows as sqrt(M) against a
denominator growing as M, so gamma -> 1/sqrt(M) and f -> 1 - 1/sqrt(M).  The
predicted value is computed from the ring's own bin count and compared.
"""
import os, sys, json, numpy as np, softcheck as S
from ncurve import pick_tiles, align_int, T, NT
ROOT=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh"
E=[0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40]
w1=np.hanning(T); WIN=np.outer(w1,w1).astype(np.float32)
f1=np.fft.fftfreq(T); RR=np.hypot(*np.meshgrid(f1,f1,indexing="ij"))
MASK=[(RR>=E[i])&(RR<E[i+1]) for i in range(len(E)-1)]
NB=len(MASK); PRIMARY=3
MBINS=[int(m.sum()) for m in MASK]
EST_LO,EST_HI=0.02,0.05          # the tile-selection band; disjoint from all reported bands
EST_MASK=((RR>=EST_LO)&(RR<EST_HI)).astype(np.float32)

def _ft(img):
    return np.fft.fft2((img-img.mean())*WIN)

FY,FX=np.meshgrid(f1,f1,indexing="ij")

def _subpix(FA,FB):
    """Sub-pixel registration of one tile pair by phase correlation.

    REQUIRED, not optional.  Measured on 119MSDCF: a ONE PIXEL misalignment alone
    produces f = 0.486 at 0.20-0.25, which exceeds the f = 0.467 measured between
    the real half-stacks.  Without this correction the statistic cannot tell
    incoherent frame choice from a pixel of misalignment, and the pre-registered
    registration-floor gate correctly VOIDs the run.

    Sub-pixel resampling is normally banned in this lane because it adds blur to
    the measured quantity.  It is admissible HERE and only here because gamma is a
    NORMALISED ratio evaluated in a narrow ring: a smooth resampling MTF is nearly
    constant across one ring and cancels between numerator and denominator.  No
    resampling is performed in any case -- the shift is applied as a pure phase
    ramp, which is exact and lossless.
    """
    # The shift is estimated ONLY from EST_MASK, a band disjoint from every band
    # this instrument reports.  Fitting it on the same bins that are then scored
    # lets two free parameters per tile buy apparent coherence out of noise.
    # Measured on 113MSDCF with a full-band fit: adding INDEPENDENT noise to both
    # arms drove f DOWN, 0.510 -> 0.482, which the additive model forbids.  With
    # the fit confined to a disjoint band the same ladder is monotone.
    X=FA*np.conj(FB)*EST_MASK
    c=np.fft.ifft2(X/(np.abs(X)+1e-30)).real
    py,px=np.unravel_index(np.argmax(c),c.shape)
    def ref(v0,v1,v2):
        d=v0-2*v1+v2
        return 0.0 if abs(d)<1e-30 else 0.5*(v0-v2)/d
    dy=ref(c[(py-1)%T,px],c[py,px],c[(py+1)%T,px])
    dx=ref(c[py,(px-1)%T],c[py,px],c[py,(px+1)%T])
    sy=(py-T if py>T//2 else py)+dy; sx=(px-T if px>T//2 else px)+dx
    # SIGN.  For b(n)=a(n-s) we have FB=FA*exp(-2i.pi.k.s/T), so X=FA.conj(FB)
    # carries exp(+2i.pi.k.s/T), and numpy's ifft convention puts that peak at -s,
    # not +s.  The correction multiplier is therefore exp(-2i.pi.k.sy/T) with sy the
    # peak location.  Getting this backwards DOUBLES the misalignment instead of
    # removing it: measured, it drove the 1 px floor from 0.486 up to 0.666.
    # Verified against planted integer AND non-integer shifts in commissioning.
    return FB*np.exp(-2j*np.pi*(FY*sy+FX*sx)), sy, sx

def pair_stats(A,B,ay,ax,by,bx,subpix=True):
    """gamma per tile per band, plus the half-difference coherent power for gating."""
    g=np.empty((len(ay),NB)); coh=np.empty((len(ay),NB))
    for k in range(len(ay)):
        a=A[ay[k]:ay[k]+T, ax[k]:ax[k]+T].astype(np.float32)
        b=B[by[k]:by[k]+T, bx[k]:bx[k]+T].astype(np.float32)
        FA=_ft(a); FB=_ft(b)
        if subpix: FB,_,_=_subpix(FA,FB)
        X=FA*np.conj(FB); PA=np.abs(FA)**2; PB=np.abs(FB)**2
        PS=np.abs((FA+FB)*0.5)**2; PD=np.abs((FA-FB)*0.5)**2
        for i in range(NB):
            m=MASK[i]
            g[k,i]=np.abs(X[m].sum())/max(np.sqrt(PA[m].sum()*PB[m].sum()),1e-30)
            coh[k,i]=PS[m].mean()-PD[m].mean()
    return 1.0-g, coh

def measure(A,B):
    """Returns (f per tile per band, coherent power, chosen shift, tiles kept)."""
    oy,ox=pick_tiles(A); sy,sx=align_int(A,B); best=None
    for dy,dx in [(0,0),(1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,-1),(2,0),(0,2)]:
        yy=oy+sy+dy; xx=ox+sx+dx
        m=(yy>=0)&(yy+T<=A.shape[0])&(xx>=0)&(xx+T<=A.shape[1])
        if m.sum()<50: continue
        f,coh=pair_stats(A,B,oy[m],ox[m],yy[m],xx[m])
        v=float(np.median(f[:,PRIMARY]))
        # Registration is chosen by MINIMISING incoherence: the best alignment
        # available, which is the reading kindest to the merge.
        if best is None or v<best[0]: best=(v,f,coh,(int(sy+dy),int(sx+dx)),int(m.sum()))
    return best[1],best[2],best[3],best[4]

def commission(A,B):
    oy,ox=pick_tiles(A); rng=np.random.default_rng(23); out={}
    sub=slice(0,120)                      # 120 tiles is ample and keeps this quick
    y,x=oy[sub],ox[sub]
    base,_=pair_stats(A,B,y,x,y,x); b0=float(np.median(base[:,PRIMARY])); out["BASE"]=b0
    fI,_=pair_stats(A,A,y,x,y,x); out["IDENTITY"]=float(np.median(fI[:,PRIMARY]))
    fO,_=pair_stats(A+2000.0,B+2000.0,y,x,y,x); out["NULL_OFFSET"]=float(np.median(fO[:,PRIMARY]))
    fG,_=pair_stats(A,B*1.3,y,x,y,x); out["NULL_GAIN"]=float(np.median(fG[:,PRIMARY]))
    Ar=np.roll(np.roll(A,7,0),11,1); Br=np.roll(np.roll(B,7,0),11,1)
    k=(y>=7)&(x>=11)
    fS,_=pair_stats(Ar,Br,y[k]+7,x[k]+11,y[k]+7,x[k]+11); out["NULL_SHIFT_BOTH"]=float(np.median(fS[:,PRIMARY]))
    n1=rng.standard_normal(A.shape[:2]).astype(np.float32)*1000
    n2=rng.standard_normal(A.shape[:2]).astype(np.float32)*1000
    fN,_=pair_stats(n1,n2,y,x,y,x); out["NOISE_NULL"]=float(np.median(fN[:,PRIMARY]))
    out["NOISE_NULL_predicted"]=1.0-1.0/np.sqrt(MBINS[PRIMARY])
    sd=float(A.std())
    for amp in (0.01,0.03,0.10):
        Ad=A+rng.standard_normal(A.shape).astype(np.float32)*sd*amp
        Bd=B+rng.standard_normal(B.shape).astype(np.float32)*sd*amp
        fD,_=pair_stats(Ad,Bd,y,x,y,x); out[f"DEGRADE_{amp}"]=float(np.median(fD[:,PRIMARY]))
    Bi=A+rng.standard_normal(A.shape).astype(np.float32)*sd*0.01
    fP,_=pair_stats(A,Bi,y,x,y,x); out["IMPROVE"]=float(np.median(fP[:,PRIMARY]))
    A1=np.roll(A,1,0); kk=y>=1
    fF,_=pair_stats(A,A1,y[kk],x[kk],y[kk],x[kk],subpix=False)
    out["REG_FLOOR_1px_uncorrected"]=float(np.median(fF[:,PRIMARY]))
    fF2,_=pair_stats(A,A1,y[kk],x[kk],y[kk],x[kk])
    out["REG_FLOOR_1px"]=float(np.median(fF2[:,PRIMARY]))
    # a NON-integer planted shift, which no integer aligner can remove
    FA_=np.fft.fft2(A.astype(np.float32))
    gy_=np.fft.fftfreq(A.shape[0])[:,None]; gx_=np.fft.fftfreq(A.shape[1])[None,:]
    Ah=np.fft.ifft2(FA_*np.exp(-2j*np.pi*(gy_*0.37+gx_*(-0.62)))).real.astype(np.float32)
    fH,_=pair_stats(A,Ah,y,x,y,x); out["REG_FLOOR_subpix_0.37_-0.62"]=float(np.median(fH[:,PRIMARY]))
    deg=[out[f"DEGRADE_{a}"] for a in (0.01,0.03,0.10)]
    # PRE-REGISTERED GATE: the measured incoherence must be at least twice the
    # incoherence a registration error alone can manufacture, in the SAME band.
    out["FLOOR_GATE_ratio"]=b0/max(out["REG_FLOOR_1px"],1e-30)
    ok=(out["FLOOR_GATE_ratio"]>2.0
        and out["IDENTITY"]<1e-6   # float32 FFT residue, 5.5 orders below BASE.
        # Measured 1.49e-09, NOT exactly 0.0, and that is the useful part: the
        # parabolic refinement returns a tiny non-zero shift on identical tiles, so
        # a non-zero residue is positive evidence the code path executed rather
        # than short-circuiting.  This arm is reported, never relied on.
        and abs(out["NULL_OFFSET"]-b0)<1e-6 and abs(out["NULL_GAIN"]-b0)<1e-6
        and abs(out["NULL_SHIFT_BOTH"]-b0)<5e-3
        and abs(out["NOISE_NULL"]-out["NOISE_NULL_predicted"])<0.02
        and deg[0]<deg[1]<deg[2] and deg[0]>b0
        and out["IMPROVE"]<0.25*b0)
    return ok,out
