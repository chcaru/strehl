"""hshaperun.py -- run the contrast-profile discriminator."""
import os, sys, json, numpy as np, softcheck as S, hcoh as HC, hsel as HS, ncurve as NC, hshape as X

T=HC.T; P=HC.PRIMARY; E=HC.E
SIG=1.5; SCALE=40          # defocus step, and blob scale inside the convicted 20-60 px band

def match(fn, lo, hi, target, tol=0.01, iters=9):
    """Bisect a plant amplitude until its BOTTOM-decile f matches the real pair."""
    for _ in range(iters):
        mid=0.5*(lo+hi); v=fn(mid)
        if abs(v-target)<tol: return mid,v
        if v<target: lo=mid
        else: hi=mid
    return mid,v

def run(subj,n):
    A,B=HS.load_pair(subj,n)
    oy,ox=HS.all_tiles(A.shape); sy,sx,m=HS.align(A,B,oy,ox); oy,ox=oy[m],ox[m]
    cw=HS.contrast(A,oy,ox); order=np.argsort(cw)
    rng=np.random.default_rng(7)
    real_bot=X.bottom(A,B,oy,ox,order)
    print("\n%s N=%d halves %d+%d  shift(%d,%d)  tiles %d"%(subj,n,n//2,n//2,sy,sx,len(oy)))
    print("  real pair, BOTTOM contrast decile f = %.4f   <- both plants are matched to this"%real_bot)
    Ab=NC.gauss(A,SIG)
    def bn(s):
        a,b=X.make_noise(A,s,np.random.default_rng(101)); return X.bottom(a,b,oy,ox,order)
    def bs(c):
        a,b=X.make_select(A,Ab,c,SCALE,np.random.default_rng(202)); return X.bottom(a,b,oy,ox,order)
    s,vs=match(bn,0.0,0.20,real_bot); print("  NOISE plant matched at amp %.4f  (bottom %.4f)"%(s,vs))
    c,vc=match(bs,0.0,1.00,real_bot); print("  SELECT plant matched at mix %.4f  (bottom %.4f)"%(c,vc))
    an,bnn=X.make_noise(A,s,np.random.default_rng(101))
    asl,bsl=X.make_select(A,Ab,c,SCALE,np.random.default_rng(202))
    pr,_=X.prof(A,B,oy,ox,order); pn,_=X.prof(an,bnn,oy,ox,order); ps,_=X.prof(asl,bsl,oy,ox,order)
    print("  f at %.2f-%.2f by contrast decile (0 = lowest contrast, 9 = highest):"%(E[P],E[P+1]))
    print("    decile      " + "".join("%8d"%d for d in range(10)))
    print("    REAL        " + "".join("%8.4f"%v for v in pr))
    print("    noise plant " + "".join("%8.4f"%v for v in pn))
    print("    select plant" + "".join("%8.4f"%v for v in ps))
    tn,ts,tr=pn[-1],ps[-1],pr[-1]
    sep=abs(tn-ts)
    print("  TOP decile:  real %.4f | noise %.4f | select %.4f   separation %.4f"%(tr,tn,ts,sep))
    if sep<0.10:
        print("  REFUSED: the two plants are %.4f apart at the top decile, which is not"%sep)
        print("           enough to discriminate.  No mechanism attribution reported.")
        return dict(subject=subj,N=n,verdict="REFUSED",sep=sep,real=pr,noise=pn,select=ps)
    # which plant does the real profile sit nearer, at the discriminating end?
    pick = "NOISE" if abs(tr-tn)<abs(tr-ts) else "SELECTION"
    frac = (tr-tn)/(ts-tn) if (ts-tn)!=0 else float("nan")
    print("  ==> real top decile sits nearer the %s plant."%pick)
    print("      position between the two plants: %.3f  (0 = pure noise, 1 = pure selection)"%frac)
    return dict(subject=subj,N=n,verdict=pick,frac=float(frac),sep=float(sep),
                real=pr,noise=pn,select=ps,amp_noise=float(s),mix_select=float(c),
                sigma=SIG,scale=SCALE,real_bottom=float(real_bot))

if __name__=="__main__":
    res=[]
    for spec in sys.argv[1:]:
        s,n=spec.split(":"); res.append(run(s,int(n)))
    p=os.path.join(HS.ROOT,"hshape.json"); json.dump(res,open(p,"w"),indent=1,default=float)
    print("\n  machine-readable: %s"%p)
