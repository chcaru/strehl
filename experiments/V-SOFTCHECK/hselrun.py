"""hselrun.py -- commission the contrast-stratified separator, then run it."""
import os, sys, json, numpy as np, softcheck as S, hcoh as HC, hsel as HS

T=HC.T; P=HC.PRIMARY; E=HC.E; NB=HC.NB; MASK=HC.MASK

def gam(FA,FB,m):
    X=(FA*np.conj(FB))[m].sum()
    return float(np.abs(X)/np.sqrt((np.abs(FA)**2)[m].sum()*(np.abs(FB)**2)[m].sum()))

def commission(A,B,oy,ox,cw,rng):
    """Two plants, opposite in kind.  The bound must respond to one and reject the other."""
    top=np.argsort(cw)[-len(cw)//10:]          # highest-contrast decile
    bot=np.argsort(cw)[:len(cw)//10]           # lowest-contrast decile
    sd=float(A[::8,::8].std())
    QS=[0.0,0.10,0.25,0.50,1.00]; SS=[0.005,0.02,0.05]
    fq={q:{"top":[],"bot":[]} for q in QS}; fs={s:{"top":[],"bot":[]} for s in SS}
    for grp,idx in (("top",top),("bot",bot)):
        for k in idx:
            y,x=oy[k],ox[k]
            a=A[y:y+T,x:x+T].astype(np.float32); b=B[y:y+T,x:x+T].astype(np.float32)
            FA=HC._ft(a); FB=HC._ft(b); FB,_,_=HC._subpix(FA,FB)
            m=MASK[P]
            for q in QS:
                FM=(1.0-q)*FA+q*FB
                fq[q][grp].append(1.0-gam(FA,FM,m))
            for s in SS:
                # BOTH arms are the SAME scene (a), so selection incoherence is ZERO
                # by construction and anything measured here is pure noise.
                an=a+rng.standard_normal(a.shape).astype(np.float32)*sd*s
                bn=a+rng.standard_normal(a.shape).astype(np.float32)*sd*s
                FAn=HC._ft(an); FBn=HC._ft(bn); FBn,_,_=HC._subpix(FAn,FBn)
                fs[s][grp].append(1.0-gam(FAn,FBn,m))
    out={"q":{q:{g:float(np.median(v)) for g,v in d.items()} for q,d in fq.items()},
         "s":{s:{g:float(np.median(v)) for g,v in d.items()} for s,d in fs.items()}}
    q_top=[out["q"][q]["top"] for q in QS]
    s_top=[out["s"][s]["top"] for s in SS]; s_bot=[out["s"][s]["bot"] for s in SS]
    ok_struct = all(q_top[i]<q_top[i+1] for i in range(len(QS)-1))
    ok_zero   = q_top[0] < 0.02
    ok_noise_rejected = max(s_top) < 0.10
    ok_noise_visible  = s_bot[-1] > 3*s_top[-1] and s_bot[0]<s_bot[1]<s_bot[2]
    out["gates"]={"STRUCTURED_monotone":ok_struct,"ZERO_arm_reads_zero":ok_zero,
                  "NOISE_rejected_at_top":ok_noise_rejected,"NOISE_visible_at_bottom":ok_noise_visible}
    out["ok"]=bool(ok_struct and ok_zero and ok_noise_rejected and ok_noise_visible)
    out["QS"]=QS; out["SS"]=SS
    return out

def run(subj,n):
    A,B=HS.load_pair(subj,n)
    oy,ox=HS.all_tiles(A.shape)
    sy,sx,m=HS.align(A,B,oy,ox)
    oy,ox=oy[m],ox[m]
    cw=HS.contrast(A,oy,ox)
    rng=np.random.default_rng(11)
    print("\n%s  N=%d  halves %d+%d   global shift (%d,%d)   tiles %d"%(subj,n,n//2,n//2,sy,sx,len(oy)))
    com=commission(A,B,oy,ox,cw,rng)
    print("  COMMISSIONING (top decile = the bound; bottom decile = the noise-sensitive end)")
    print("    STRUCTURED plant, q = fraction of the real A-B difference injected:")
    print("      q      " + "".join("%9.2f"%q for q in com["QS"]))
    print("      top    " + "".join("%9.4f"%com["q"][q]["top"] for q in com["QS"]))
    print("      bottom " + "".join("%9.4f"%com["q"][q]["bot"] for q in com["QS"]))
    print("    NOISE plant, identical scene in both arms so TRUE selection incoherence = 0:")
    print("      amp    " + "".join("%9.3f"%s for s in com["SS"]))
    print("      top    " + "".join("%9.4f"%com["s"][s]["top"] for s in com["SS"]))
    print("      bottom " + "".join("%9.4f"%com["s"][s]["bot"] for s in com["SS"]))
    for k,v in com["gates"].items(): print("      %-26s %s"%(k,v))
    if not com["ok"]:
        print("  VOID: commissioning failed, no bound reported for %s"%subj); return None
    f,rows=HS.stratified(A,B,oy,ox,cw)
    print("  f at %.2f-%.2f by CONTRAST DECILE (stratifier is 0.02-0.05, disjoint):"%(E[P],E[P+1]))
    print("    decile   n    contrast      p10     median      p90")
    for r in rows:
        print("      %d    %4d   %10.3e   %7.4f  %7.4f  %7.4f"%(r["decile"],r["n"],r["contrast"],r["p10"],r["med"],r["p90"]))
    top=rows[-1]
    # border vs interior: a defect at the borders is invisible to a median over all
    H,W=A.shape[:2]
    bord=(oy<T)|(ox<T)|(oy+2*T>H)|(ox+2*T>W)
    print("    border tiles %d  median f %.4f   |   interior %d  median f %.4f"%(
        bord.sum(),float(np.median(f[bord,P])),(~bord).sum(),float(np.median(f[~bord,P]))))
    print("  ==> UPPER BOUND on selection incoherence (top contrast decile) = %.4f"%top["med"])
    print("      raw f over all tiles                                       = %.4f"%float(np.median(f[:,P])))
    return dict(subject=subj,N=n,bound=top["med"],raw=float(np.median(f[:,P])),
                deciles=[r["med"] for r in rows], contrast=[r["contrast"] for r in rows],
                perband_top=rows[-1]["perband"], perband_bot=rows[0]["perband"],
                border=float(np.median(f[bord,P])), interior=float(np.median(f[~bord,P])),
                commissioning=com)

if __name__=="__main__":
    res=[]
    for spec in sys.argv[1:]:
        s,n=spec.split(":"); r=run(s,int(n))
        if r: res.append(r)
    p=os.path.join(HS.ROOT,"hsel.json"); json.dump(res,open(p,"w"),indent=1,default=float)
    print("\n  machine-readable: %s"%p)
