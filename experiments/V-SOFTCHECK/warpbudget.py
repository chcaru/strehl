"""warpbudget.py -- how much of the observed half-stack incoherence can the
MEASURED residual warp actually account for?

WHY THIS REPLACES A CALIBRATED WARP ARM.  hwarpmix.py tried to put warp on the same
amplitude-matched ladder as noise and selection, by bisecting a displacement until
its anchor-decile f matched the real pair.  IT FAILED ITS OWN COMMISSIONING, twice,
and the second failure is a property of the statistic rather than of my plant:

    u=0.00  0 px  f = -0.0000
    u=0.50  1 px  f =  0.1910
    u=1.00  1 px  f =  0.3875
    u=2.00  2 px  f =  0.8522
    u=3.00  3 px  f =  0.7840     <-- DOWN
    u=4.00  4 px  f =  0.9240

f is not monotone in displacement.  It cannot be: coherence in a band centred on
0.225 cyc/px is set by the phase 2*pi*f*s, which WRAPS, so decorrelation oscillates
with shift instead of growing with it.  A bisection assumes monotonicity and would
have converged on whichever of several roots it met first.  I am not tuning the
plant until it passes; I am reporting that a shift plant is not bisectable on a
band-limited coherence statistic and using a test that needs no calibration.

THE TEST.  Apply exactly the amount of within-tile warp that hwarp.py MEASURED
between the two arms, to a clean pair, and read the incoherence it produces.  No
bisection, no monotonicity requirement, no matching.  The ratio

    f(planted at the measured warp)  /  f(real pair)

is the fraction of the real effect that the real warp can account for, measured
rather than inferred.  Over-drive rungs at 2x and 4x the measured warp show the
sensitivity, so a near-miss cannot be mistaken for a null.

WHY THIS IS CONSERVATIVE IN FAVOUR OF THE WARP HYPOTHESIS -- stated because it is
the direction that could make me wrong.  Three separate over-statements:
  1. The plant varies at 64 px, the measurement tile is 256 px, and the real field
     was measured between tile centres 256 px apart.  A field varying 4x faster at
     the same amplitude destroys more within-tile coherence, not less.
  2. Every displaced block leaves a hard discontinuity at its boundary that real
     warp does not have, adding difference the real field would not produce.
  3. pair_stats removes each tile's own constant shift exactly, and it removes some
     of the plant's tile-mean shift too, but the plant's random directions leave the
     tile mean near zero, so almost all of the planted displacement survives as the
     within-tile component -- the worst case for the merge.
If a plant this generous still cannot reproduce the observed incoherence, warp is
not the explanation.

COMMISSIONING, both directions.
  ZERO      d = 0 must be an exact no-op, arms bit-identical, f = 0.
  LANDED    d > 0 must actually change the array -- an inert plant is the failure
            this project has now seen three times.
  DEGRADE   f must rise from d = 0 to d = 1 px.
  IMPROVE   f must fall again when d falls -- the plant must be free to make the
            image better, not only worse.  Checked on the 0.25/0.50/1.00 rungs,
            which share m = 1 px and so are monotone in the fraction moved.
"""
import os, sys, json, math, numpy as np, softcheck as S, hcoh as HC, hsel as HS, hshape as X

T=HC.T; P=HC.PRIMARY; SAT=0.90; BLK=T//4

# Residual WITHIN-tile warp measured by hwarp.py this session: median |tile shift -
# mean of its 8 neighbours| in px, after the global integer shift.  This is the
# component pair_stats cannot remove as a per-tile phase ramp.
MEASURED_WARP_PX={"119MSDCF":0.161,"bee-1-cpl":1.354}

def make_warp(A,d,rng):
    """Displace blocks so the MEAN displacement is exactly d px. Integer only, no
    interpolation: m = ceil(d) px applied to a fraction d/m of blocks."""
    H,W=A.shape; out=A.copy()
    if d<=0: return A.astype(np.float32),out.astype(np.float32),0,0
    m=int(math.ceil(d)); q=d/m
    ny=H//BLK; nx=W//BLK
    sel=rng.random((ny,nx))<q
    dirs=rng.integers(0,4,size=(ny,nx))
    DY=[1,-1,0,0]; DX=[0,0,1,-1]
    moved=0
    for by in range(ny):
        for bx in range(nx):
            if not sel[by,bx]: continue
            dy=DY[dirs[by,bx]]*m; dx=DX[dirs[by,bx]]*m
            y0=by*BLK; x0=bx*BLK
            sy0=min(max(y0+dy,0),H-BLK); sx0=min(max(x0+dx,0),W-BLK)
            out[y0:y0+BLK,x0:x0+BLK]=A[sy0:sy0+BLK,sx0:sx0+BLK]
            moved+=1
    return A.astype(np.float32),out.astype(np.float32),moved,m

def anchor_of(pr):
    for i,v in enumerate(pr):
        if v<SAT: return i
    return None

def anchor_f(A,d,oy,ox,order,a_i,seed=707):
    a,b,moved,m=make_warp(A,d,np.random.default_rng(seed))
    if d>0 and np.array_equal(a,b):
        raise SystemExit("COMMISSION FAIL: d=%.3f moved %d blocks but arms identical -- INERT"%(d,moved))
    if d==0 and not np.array_equal(a,b):
        raise SystemExit("COMMISSION FAIL: d=0 is not a no-op")
    di=np.array_split(order,10)[a_i]
    f,_=HC.pair_stats(a,b,oy[di],ox[di],oy[di],ox[di])
    return float(np.median(f[:,P])),moved,m

def run(subj,n):
    if subj not in MEASURED_WARP_PX:
        print("\n%s: REFUSED -- no hwarp.py residual-warp measurement for this subject"%subj)
        return dict(subject=subj,N=n,verdict="REFUSED_NO_WARP_MEASUREMENT")
    A,B=HS.load_pair(subj,n)
    oy,ox=HS.all_tiles(A.shape); sy,sx,mm=HS.align(A,B,oy,ox); oy,ox=oy[mm],ox[mm]
    cw=HS.contrast(A,oy,ox); order=np.argsort(cw)
    pr,_=X.prof(A,B,oy,ox,order)
    print("\n%s N=%d  shift(%d,%d)  tiles %d"%(subj,n,sy,sx,len(oy)))
    print("  REAL profile " + "".join("%8.4f"%v for v in pr))
    a_i=anchor_of(pr)
    if a_i is None or a_i>6:
        print("  REFUSED: no contrast decile below the %.2f saturation limit"%SAT)
        return dict(subject=subj,N=n,verdict="REFUSED_SATURATED",real=pr)
    real=pr[a_i]
    print("  anchor decile %d   REAL f = %.4f"%(a_i,real))

    print("  COMMISSIONING")
    c={}
    for d in [0.0,0.25,0.50,1.00]:
        v,moved,m=anchor_f(A,d,oy,ox,order,a_i); c[d]=v
        print("    d=%.2f px  shift %d px  blocks %6d  f = %.4f"%(d,m,moved,v))
    if not (c[0.0]<c[0.25]<c[0.50]<c[1.00]):
        raise SystemExit("  COMMISSION FAIL: not monotone on the m=1 rungs %s"%c)
    if abs(c[0.0])>1e-6:
        raise SystemExit("  COMMISSION FAIL: d=0 gave f=%.6f, expected exactly 0"%c[0.0])
    print("    ZERO ok (exactly %.6f)  LANDED ok  DEGRADE ok (%.4f -> %.4f)  IMPROVE ok (monotone down)"%(
          c[0.0],c[0.0],c[1.00]))

    have=MEASURED_WARP_PX[subj]
    rows=[]
    for mult in [1.0,2.0,4.0]:
        d=have*mult
        v,moved,m=anchor_f(A,d,oy,ox,order,a_i)
        share=v/real if real>0 else float("nan")
        rows.append(dict(mult=mult,d=float(d),f=float(v),share=float(share),m=int(m)))
        print("  warp at %.0fx measured (%.3f px, %d px steps): f = %.4f  = %.1f%% of the real %.4f"%(
              mult,d,m,v,100*share,real))
    s1=rows[0]["share"]
    if s1>=0.80:   verdict="WARP_SUFFICIENT"
    elif s1>=0.35: verdict="WARP_PARTIAL"
    else:          verdict="WARP_INSUFFICIENT"
    print("  ==> %s : the measured residual warp accounts for %.1f%% of the observed incoherence"%(
          verdict,100*s1))
    return dict(subject=subj,N=n,verdict=verdict,anchor=a_i,real_f=float(real),
                warp_px_measured=have,rungs=rows,share_at_measured=float(s1),
                commission={str(k):float(v) for k,v in c.items()},real=pr)

if __name__=="__main__":
    res=[]
    for spec in sys.argv[1:]:
        s,n=spec.split(":"); res.append(run(s,int(n)))
    p=os.path.join(HS.ROOT,"warpbudget.json"); json.dump(res,open(p,"w"),indent=1,default=float)
    print("\n  attempted %d = %s"%(len(res),", ".join(r["verdict"] for r in res)))
    print("  machine-readable: %s"%p)
