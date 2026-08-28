"""hmixrun.py -- calibrated UPPER BOUND on the selection share of half-stack incoherence.

Supersedes hselrun.py, which FAILED ITS OWN COMMISSIONING, and hshaperun.py, which
could compare shapes but not bound a share.

THE STATISTIC.  fall = f(anchor contrast decile) / f(top contrast decile), a ratio
of two f values on the same image, so a common amplitude cancels.

  additive noise   Nz independent of scene power S  ->  fall LARGE
  frame choice     difference proportional to S     ->  fall ~ 1 (flat)

THE CALIBRATION.  For selection share lambda I apply the blob-mask selection plant
at mix lambda, then BISECT a white-noise amplitude until the anchor decile matches
the real pair.  Every rung carries the same incoherence at the anchor and differs
only in how much of it is contrast-proportional.  lambda = 0 and lambda = 1 are both
reachable, so the instrument is free to answer either way.

SATURATION GATE, forced by a measurement.  NOISE_NULL puts the independent limit at
0.985.  A decile sitting at 0.98 is saturated: every plant matches it trivially and
the match then OVER-DRIVES the plant.  On bee-1-cpl, whose bottom decile is 0.9822,
all five rungs converged on the bisection's FIRST midpoint, amp 0.1500 -- which is
how a saturated anchor looks from outside.  The anchor is therefore the first decile
below SAT, and if none exists the subject is REFUSED.

SPREAD GATE.  If the pure-noise and pure-selection rungs are less than 1.30 apart
the calibration cannot separate them and no share is reported.
"""
import os, sys, json, numpy as np, softcheck as S, hcoh as HC, hsel as HS, ncurve as NC, hshape as X

T=HC.T; P=HC.PRIMARY; E=HC.E
SIG=1.5; SCALE=40
LAM=[0.0,0.25,0.50,0.75,1.00]
SAT=0.90

def anchor_of(pr):
    for i,v in enumerate(pr):
        if v<SAT: return i
    return None

def fall(pr,a): return pr[a]/pr[-1] if pr[-1]>0 else float("inf")

def run(subj,n):
    A,B=HS.load_pair(subj,n)
    oy,ox=HS.all_tiles(A.shape); sy,sx,m=HS.align(A,B,oy,ox); oy,ox=oy[m],ox[m]
    cw=HS.contrast(A,oy,ox); order=np.argsort(cw)
    pr,_=X.prof(A,B,oy,ox,order)
    print("\n%s N=%d halves %d+%d  shift(%d,%d)  tiles %d"%(subj,n,n//2,n//2,sy,sx,len(oy)))
    print("  REAL profile " + "".join("%8.4f"%v for v in pr))
    a_i=anchor_of(pr)
    if a_i is None or a_i>6:
        print("  REFUSED: no contrast decile below the %.2f saturation limit (independent limit 0.985)"%SAT)
        return dict(subject=subj,N=n,verdict="REFUSED_SATURATED",real=pr)
    target=pr[a_i]; real_fall=fall(pr,a_i)
    print("  anchor decile %d (first below %.2f), anchor f = %.4f"%(a_i,SAT,target))
    print("  REAL fall ratio (anchor/top) = %.3f"%real_fall)
    Ab=NC.gauss(A,SIG); sd=float(A[::8,::8].std())
    rows=[]
    for lam in LAM:
        if lam>0: asl,bsl=X.make_select(A,Ab,lam,SCALE,np.random.default_rng(202))
        else:     asl,bsl=A.astype(np.float32),A.astype(np.float32)
        lo,hi,mid,v=0.0,0.30,0.0,None
        for _ in range(11):
            mid=0.5*(lo+hi)
            r1=np.random.default_rng(303); r2=np.random.default_rng(404)
            a=asl+r1.standard_normal(A.shape).astype(np.float32)*sd*mid
            b=bsl+r2.standard_normal(A.shape).astype(np.float32)*sd*mid
            # evaluate ONLY the anchor decile during bisection: same value, 10x cheaper
            di=np.array_split(order,10)[a_i]
            fv,_=HC.pair_stats(a,b,oy[di],ox[di],oy[di],ox[di])
            v=float(np.median(fv[:,P]))
            if abs(v-target)<0.004: break
            if v<target: lo=mid
            else: hi=mid
        r1=np.random.default_rng(303); r2=np.random.default_rng(404)
        a=asl+r1.standard_normal(A.shape).astype(np.float32)*sd*mid
        b=bsl+r2.standard_normal(A.shape).astype(np.float32)*sd*mid
        pp,_=X.prof(a,b,oy,ox,order)
        rows.append((lam,mid,pp,fall(pp,a_i)))
        print("   lambda %.2f  noise amp %.4f  anchor %.4f  top %.4f  fall %.3f"%(lam,mid,pp[a_i],pp[-1],fall(pp,a_i)))
    falls=[r[3] for r in rows]
    amps=[r[1] for r in rows]
    if len(set("%.4f"%x for x in amps))==1:
        print("  REFUSED: every rung took the same noise amplitude %.4f -- the anchor is not"%amps[0])
        print("           constraining the match, so the rungs are not amplitude-matched.")
        return dict(subject=subj,N=n,verdict="REFUSED_ANCHOR_INERT",amps=amps,real=pr)
    mono=all(falls[i]>falls[i+1] for i in range(len(falls)-1))
    spread=falls[0]/falls[-1] if falls[-1]>0 else 0.0
    print("  calibration %s  monotone=%s  spread=%.3f"%(["%.3f"%f for f in falls],mono,spread))
    if not mono:
        print("  REFUSED: calibration not monotone in lambda."); 
        return dict(subject=subj,N=n,verdict="REFUSED_NONMONOTONE",falls=falls,real=pr)
    if spread<1.30:
        print("  REFUSED: calibration spans only %.3f, too little to bound a share."%spread)
        return dict(subject=subj,N=n,verdict="REFUSED_FLAT_CALIBRATION",spread=spread,falls=falls,real=pr)
    if real_fall>=falls[0]:
        bound=0.0; note="real fall EXCEEDS the pure-noise rung; no contrast-proportional component fits"
    else:
        bound=float(np.interp(-real_fall,[-f for f in falls],LAM)); note="interpolated on the calibration"
    print("  ==> real fall %.3f vs pure-noise rung %.3f -> SELECTION SHARE BOUND = %.2f (%s)"%(
        real_fall,falls[0],bound,note))
    return dict(subject=subj,N=n,verdict="MEASURED",anchor=a_i,real_fall=float(real_fall),
                falls=[float(f) for f in falls],amps=[float(x) for x in amps],lam=LAM,
                bound=float(bound),spread=float(spread),real=pr,
                rungs=[[r[0],r[1],r[2]] for r in rows])

if __name__=="__main__":
    res=[]
    for spec in sys.argv[1:]:
        s,n=spec.split(":"); res.append(run(s,int(n)))
    p=os.path.join(HS.ROOT,"hmix.json"); json.dump(res,open(p,"w"),indent=1,default=float)
    print("\n  attempted %d = measured %d + refused %d"%(len(res),
          sum(1 for r in res if r["verdict"]=="MEASURED"),
          sum(1 for r in res if r["verdict"].startswith("REFUSED"))))
    print("  machine-readable: %s"%p)
