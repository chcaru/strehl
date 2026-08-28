"""hwarpmix.py -- can the fall-ratio statistic tell FRAME CHOICE from MISREGISTRATION?

WHY THIS EXISTS.  hmixrun.py returned a "selection share" of 0.85 on bee-1-cpl
(N=298) and 0.00 on 119MSDCF (N=32).  The statistic separates incoherence that is
INDEPENDENT of scene content (additive noise -> f falls steeply as tile contrast
rises) from incoherence PROPORTIONAL to scene content (f flat across contrast).
Frame choice is contrast-proportional.  So is a registration error: two arms offset
by a shift differ by roughly the local gradient times the shift, which scales with
scene content exactly the way a defocus difference does.

hwarp.py then measured the residual per-tile shift field between the two half
merges, AFTER the global integer shift and AFTER pair_stats removes each tile's own
constant shift as an exact phase ramp:

    bee-1-cpl N=298   median 8.885 px   p90 34.6   max 97.2   field spread 14.5
                      median |tile - mean of 8 neighbours| = 1.354 px  -> SMOOTH
    119MSDCF N=32     median 0.823 px   p90  1.27  max  1.82  field spread 0.35
                      median |tile - mean of 8 neighbours| = 0.161 px

A smooth field is real warp, not per-tile fitting noise.  What survives pair_stats
is the WITHIN-tile variation of that field, of order the neighbour deviation: about
1.35 px on bee against 0.16 px on 119.  So the subject that read 0.85 is also the
subject with 8x more residual within-tile warp.  These are confounded and I will not
report the 0.85 as a selection number until I know whether the statistic can even
separate them.

PRE-REGISTERED DISCRIMINATOR -- written before the warp arm was run.

Measure three PURE plants, each bisected to the SAME anchor-decile f as the real
pair, and read their fall ratios:  fall_noise (steep), fall_select, fall_warp.
Let D = fall_noise - fall_select, the calibration's own dynamic range.

  SEPARABLE          |fall_warp - fall_select| > 0.50 * D
                     warp sits at least halfway back toward the noise end, so a
                     measured fall can be attributed between the two.
  INDISTINGUISHABLE  |fall_warp - fall_select| <= 0.25 * D
                     the two mechanisms land on top of each other; the 0.85 must be
                     renamed a CONTRAST-PROPORTIONAL share and cannot name a cause.
  AMBIGUOUS          anything between; report as such, claim neither.

MY PREDICTION, recorded before running: INDISTINGUISHABLE.  A shifted edge and a
defocused edge both differ from the reference by something proportional to the local
gradient.  I expect fall_warp to land within a few percent of fall_select.  If it
instead lands near fall_noise I will have been wrong and the 0.85 survives as a
selection number.

THE PLANT IS INTEGER-ONLY AND CARRIES NO RESAMPLING BLUR.  Sub-pixel resampling adds
blur to the very quantity under measurement, so the plant never interpolates.  A
fraction q of 64 px blocks -- a quarter of the 256 px measurement tile, so the shift
varies WITHIN every tile, which is the component pair_stats cannot remove -- is moved
by an exact integer number of pixels m in a random direction.  Amplitude is one
continuous knob u: m = ceil(u), q = u/m.  u = 0.5 moves half the blocks 1 px, u = 3.0
moves every block 3 px.  Monotone in u, exact at every rung.

FIRST RUN CAPPED OUT AND THAT IS WHY u EXISTS.  The plant was originally fixed at a
1 px displacement with q the only knob.  On 119MSDCF q = 1.00 reached anchor
f = 0.3875 against a target of 0.8810: the plant could not be amplitude-matched at
all, so its fall ratio would have been read off an arm carrying a quarter of the
incoherence of the others and the comparison would have been meaningless.  The
bisection now REFUSES an arm it cannot match rather than reporting the ceiling as a
result.

KNOWN LIMITATION, stated because it cuts against my own prediction.  Displacing a
block by m px leaves a discontinuity at the block boundary that real warp would not
have.  That injects extra high-frequency difference, so the plant reaches a given
anchor f at a smaller displacement than true warp would need.  The discontinuity is
itself a copy of scene content, so it is contrast-proportional and should not move
the SHAPE the statistic reads -- but it makes the warp arm easier to match, which
biases toward finding warp indistinguishable from selection, i.e. toward my own
predicted answer.  Read the verdict with that in mind.

COMMISSIONING, both directions, run before any result is read:
  DEGRADE   u = UMAX must give f far above u = 0.
  IMPROVE   f must fall monotonically as u falls -- the plant must be free to make
            the image BETTER, not only worse.
  LANDED    at u > 0 the displaced array must differ from the source.  A plant that
            silently fails to apply is the inert-control failure this project has
            now seen three times.
  CEILING   the u = UMAX value is printed so a plant that cannot reach the target is
            visible before the ladder is read, not after.
"""
import os, sys, json, math, numpy as np, softcheck as S, hcoh as HC, hsel as HS, ncurve as NC, hshape as X

T=HC.T; P=HC.PRIMARY; E=HC.E
SIG=1.5; SCALE=40; SAT=0.90; BLK=T//4; UMAX=4.0
# Residual WITHIN-tile warp actually measured by hwarp.py: median |tile shift -
# mean of its 8 neighbours|, in px, after the global integer shift.  This is the
# component pair_stats cannot remove, and it is what the warp plant must be
# compared against.  Source: hwarp.py output, this session.
MEASURED_WARP_PX={"119MSDCF":0.161,"bee-1-cpl":1.354,"113MSDCF":None}

def make_warp(A,u,rng):
    """Arm A untouched, arm B block-displaced by an exact integer shift. No interpolation."""
    H,W=A.shape; out=A.copy()
    if u<=0: return A.astype(np.float32),out.astype(np.float32),0,0
    m=int(math.ceil(u)); q=u/m
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

def fall(pr,a): return pr[a]/pr[-1] if pr[-1]>0 else float("inf")

def commission(A,oy,ox,order,a_i):
    print("  COMMISSIONING the warp plant (both directions)")
    di=np.array_split(order,10)[a_i]
    vals=[]
    for u in [0.0,0.5,1.0,2.0,3.0,UMAX]:
        a,b,moved,m=make_warp(A,u,np.random.default_rng(707))
        if u>0 and np.array_equal(a,b):
            raise SystemExit("  COMMISSION FAIL: u=%.2f moved %d blocks but arms are identical -- INERT PLANT"%(u,moved))
        if u==0.0 and not np.array_equal(a,b):
            raise SystemExit("  COMMISSION FAIL: u=0 must be a no-op and is not")
        f,_=HC.pair_stats(a,b,oy[di],ox[di],oy[di],ox[di])
        v=float(np.median(f[:,P])); vals.append(v)
        print("    u=%.2f  shift %d px  blocks moved %6d  anchor f = %.4f"%(u,m,moved,v))
    if not all(vals[i]<vals[i+1] for i in range(len(vals)-1)):
        raise SystemExit("  COMMISSION FAIL: f is not monotone in u -- plant not calibratable")
    if vals[-1]<=vals[0]+0.05:
        raise SystemExit("  COMMISSION FAIL: u=UMAX barely above u=0 (%.4f vs %.4f)"%(vals[-1],vals[0]))
    print("    DEGRADE ok (%.4f -> %.4f)   IMPROVE ok (monotone)   LANDED ok   CEILING %.4f"%(
          vals[0],vals[-1],vals[-1]))
    return vals[-1]

def warp_verdict(subj,u_req,ceil_f,target):
    """The sharpest statement the warp arm can make: how much displacement the plant
    NEEDED to reproduce the observed incoherence, against how much displacement the
    two arms actually carry.  Ratio >> 1 means warp cannot account for the effect at
    the amount of warp that is really present, whatever the fall ratio says."""
    have=MEASURED_WARP_PX.get(subj)
    if have is None:
        return None,"no hwarp.py measurement for this subject"
    r=u_req/have
    if r<=1.5:  tag="WARP SUFFICIENT -- the measured residual warp is enough on its own"
    elif r<=4.0: tag="WARP PARTIAL -- measured warp accounts for a fraction, not all"
    else:        tag="WARP INSUFFICIENT -- measured warp is far too small to explain it"
    return r,tag

def bisect_to(target,A,oy,ox,order,a_i,kind,extra=None):
    di=np.array_split(order,10)[a_i]
    lo,hi=(0.0,0.30) if kind=="noise" else (0.0,UMAX)
    mid=0.0; v=None
    sd=float(A[::8,::8].std())
    for _ in range(12):
        mid=0.5*(lo+hi)
        if kind=="noise":
            r1=np.random.default_rng(303); r2=np.random.default_rng(404)
            a=extra[0]+r1.standard_normal(A.shape).astype(np.float32)*sd*mid
            b=extra[1]+r2.standard_normal(A.shape).astype(np.float32)*sd*mid
        else:
            a,b,_,_=make_warp(A,mid,np.random.default_rng(707))
        f,_=HC.pair_stats(a,b,oy[di],ox[di],oy[di],ox[di])
        v=float(np.median(f[:,P]))
        if abs(v-target)<0.006: break
        if v<target: lo=mid
        else: hi=mid
    return mid,v

def run(subj,n):
    A,B=HS.load_pair(subj,n)
    oy,ox=HS.all_tiles(A.shape); sy,sx,m=HS.align(A,B,oy,ox); oy,ox=oy[m],ox[m]
    cw=HS.contrast(A,oy,ox); order=np.argsort(cw)
    pr,_=X.prof(A,B,oy,ox,order)
    print("\n%s N=%d  shift(%d,%d)  tiles %d"%(subj,n,sy,sx,len(oy)))
    print("  REAL profile " + "".join("%8.4f"%v for v in pr))
    a_i=anchor_of(pr)
    if a_i is None or a_i>6:
        print("  REFUSED: no contrast decile below the %.2f saturation limit"%SAT)
        return dict(subject=subj,N=n,verdict="REFUSED_SATURATED",real=pr)
    target=pr[a_i]; real_fall=fall(pr,a_i)
    print("  anchor decile %d  f=%.4f   REAL fall = %.3f"%(a_i,target,real_fall))
    ceil_f=commission(A,oy,ox,order,a_i)
    Ab=NC.gauss(A,SIG); sd=float(A[::8,::8].std())
    out={}; unmatched=[]
    for kind in ["noise","select","warp"]:
        if kind=="noise":
            amp,v=bisect_to(target,A,oy,ox,order,a_i,"noise",extra=(A.astype(np.float32),A.astype(np.float32)))
            r1=np.random.default_rng(303); r2=np.random.default_rng(404)
            a=A+r1.standard_normal(A.shape).astype(np.float32)*sd*amp
            b=A+r2.standard_normal(A.shape).astype(np.float32)*sd*amp
        elif kind=="select":
            asl,bsl=X.make_select(A,Ab,1.0,SCALE,np.random.default_rng(202))
            amp,v=bisect_to(target,A,oy,ox,order,a_i,"noise",extra=(asl,bsl))
            r1=np.random.default_rng(303); r2=np.random.default_rng(404)
            a=asl+r1.standard_normal(A.shape).astype(np.float32)*sd*amp
            b=bsl+r2.standard_normal(A.shape).astype(np.float32)*sd*amp
        else:
            amp,v=bisect_to(target,A,oy,ox,order,a_i,"warp")
            a,b,_,_=make_warp(A,amp,np.random.default_rng(707))
        pp,_=X.prof(a,b,oy,ox,order)
        ok=abs(pp[a_i]-target)<0.02
        if not ok: unmatched.append(kind)
        out[kind]=dict(amp=float(amp),anchor=float(pp[a_i]),top=float(pp[-1]),
                       fall=float(fall(pp,a_i)),matched=bool(ok),prof=[float(x) for x in pp])
        print("  %-7s amp %.4f  anchor %.4f (target %.4f) %s  top %.4f  FALL %.3f"%(
              kind,amp,pp[a_i],target,"MATCHED" if ok else "*** UNMATCHED ***",pp[-1],fall(pp,a_i)))
    if unmatched:
        print("  REFUSED: arm(s) %s could not be amplitude-matched to the anchor; their fall"%",".join(unmatched))
        print("           ratios are read off a different amount of incoherence and mean nothing.")
        return dict(subject=subj,N=n,verdict="REFUSED_ARM_UNMATCHED",unmatched=unmatched,
                    ceiling=float(ceil_f),target=float(target),arms=out,real=pr,
                    real_fall=float(real_fall))
    u_req=out["warp"]["amp"]
    r,tag=warp_verdict(subj,u_req,ceil_f,target)
    if r is not None:
        print("  WARP BUDGET: plant needed %.2f px mean displacement; hwarp.py measured %.3f px"%(
              u_req,MEASURED_WARP_PX[subj]))
        print("               ratio %.2fx  ->  %s"%(r,tag))
    fn=out["noise"]["fall"]; fs=out["select"]["fall"]; fw=out["warp"]["fall"]
    D=fn-fs; gap=abs(fw-fs)
    if D<=0: verdict="REFUSED_NO_DYNAMIC_RANGE"
    elif gap>0.50*D: verdict="SEPARABLE"
    elif gap<=0.25*D: verdict="INDISTINGUISHABLE"
    else: verdict="AMBIGUOUS"
    print("  D = fall_noise - fall_select = %.3f ;  |fall_warp - fall_select| = %.3f = %.2f D"%(
          D,gap,gap/D if D>0 else float("nan")))
    print("  ==> %s"%verdict)
    return dict(subject=subj,N=n,verdict=verdict,anchor=a_i,real_fall=float(real_fall),
                D=float(D),gap=float(gap),ceiling=float(ceil_f),arms=out,real=pr,
                warp_px_required=float(u_req),warp_px_measured=MEASURED_WARP_PX.get(subj),
                warp_budget_ratio=(float(r) if r is not None else None),warp_budget=tag)

if __name__=="__main__":
    res=[]
    for spec in sys.argv[1:]:
        s,n=spec.split(":"); res.append(run(s,int(n)))
    p=os.path.join(HS.ROOT,"hwarpmix.json"); json.dump(res,open(p,"w"),indent=1,default=float)
    print("\n  attempted %d = %s"%(len(res),", ".join(r["verdict"] for r in res)))
    print("  machine-readable: %s"%p)
