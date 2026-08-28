"""Drive the half-stack coherence measurement across depth and subject.
Pre-registered in PREREG-coherence.md.  P1 trend in N, P2 between subjects, P3 band shape."""
import os, sys, json, numpy as np, softcheck as S, hcoh as HC
ROOT=HC.ROOT; E=HC.E; PR=HC.PRIMARY
def run(subject):
    d=os.path.join(ROOT,subject)
    ns=sorted({int(f[1:4]) for f in os.listdir(d) if f.endswith("-A.tiff")})
    print(f"\n{subject}: incoherent fraction f between two INTERLEAVED half-stacks")
    print(f"  f = 1 - gamma, band-limited, sub-pixel phase corrected.  "
          f"0 = the two halves agree, 1 = independent.")
    A0=S.load_luma(os.path.join(d,f"N{ns[-1]:03d}-A.tiff"),"srgb")
    B0=S.load_luma(os.path.join(d,f"N{ns[-1]:03d}-B.tiff"),"srgb")
    ok,com=HC.commission(A0,B0); del A0,B0
    print(f"  commissioning on the deepest pair: {'PASSED' if ok else 'FAILED'}")
    for k in ("IDENTITY","NULL_GAIN","NOISE_NULL","NOISE_NULL_predicted","IMPROVE",
              "REG_FLOOR_1px_uncorrected","REG_FLOOR_1px","FLOOR_GATE_ratio"):
        print(f"    {k:28s} {com[k]:.6f}")
    if not ok: print("  VOID: commissioning failed, no numbers reported"); return None
    res={}; store={}
    hdr="   N  halves " + " ".join(f"{E[b]:.2f}-{E[b+1]:.2f}" for b in range(HC.NB))
    print("\n"+hdr)
    for n in ns:
        A=S.load_luma(os.path.join(d,f"N{n:03d}-A.tiff"),"srgb")
        B=S.load_luma(os.path.join(d,f"N{n:03d}-B.tiff"),"srgb")
        f,coh,sh,kept=HC.measure(A,B); del A,B
        neg=[b for b in range(HC.NB) if np.median(coh[:,b])<=0]
        res[n]=[float(np.median(f[:,b])) for b in range(HC.NB)]
        store[n]=f[:,PR].copy()
        row=" ".join(f"{res[n][b]:9.4f}" for b in range(HC.NB))
        print(f"  {n:3d}  {n//2:3d}+{n-n//2:<3d} {row}   shift{sh} tiles {kept}"
              + ("   DEGENERATE bands "+str(neg) if neg else ""))
    lo_n,hi_n=ns[0],ns[-1]
    r=np.random.default_rng(23); a=store[lo_n]; b=store[hi_n]
    bs=[np.median(b[r.integers(0,len(b),len(b))])/np.median(a[r.integers(0,len(a),len(a))])
        for _ in range(1500)]
    ci=np.percentile(bs,[2.5,97.5]); ratio=np.median(b)/np.median(a)
    trend="RISE" if ci[0]>1.0 else ("FALL" if ci[1]<1.0 else "INCONCLUSIVE")
    print(f"\n  P1  f(N={hi_n}) / f(N={lo_n}) at 0.20-0.25 = {ratio:.4f} "
          f"CI [{ci[0]:.4f},{ci[1]:.4f}]  -> {trend}")
    c0=res[hi_n][0]/res[lo_n][0]
    print(f"  P3  same ratio at 0.05-0.10 = {c0:.4f}   "
          f"(selection should move the fine band more than the coarse one)")
    return dict(subject=subject,ns=ns,f=res,p1_ratio=round(float(ratio),4),
                p1_ci=[round(float(ci[0]),4),round(float(ci[1]),4)],p1=trend,
                p3_coarse_ratio=round(float(c0),4),
                f_primary_by_n={str(k):round(v[PR],4) for k,v in res.items()},
                commissioning={k:round(float(v),6) for k,v in com.items()})
if __name__=="__main__":
    out=[run(s) for s in sys.argv[1:]]
    out=[o for o in out if o]
    if len(out)>1:
        print("\n  P2  between subjects at matched N:")
        common=set(out[0]["ns"])
        for o in out[1:]: common &= set(o["ns"])
        for n in sorted(common):
            vals=" ".join(f"{o['subject']}={o['f'][n][PR]:.4f}" for o in out)
            print(f"    N={n:3d}  {vals}")
    json.dump(out,open(os.path.join(ROOT,"hcoh.json"),"w"),indent=1)
    print(f"\n  machine-readable: {os.path.join(ROOT,'hcoh.json')}")
