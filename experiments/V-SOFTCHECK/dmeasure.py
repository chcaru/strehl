"""dmeasure.py -- does the N-softening track FRAME COUNT or FOCUS STEP?

Executes PREREG-dilution.md, committed at 8982657d before any statistic was formed.

Four merges of bee-1-cpl at the SHIP-V4 pin, all --srgb --exposure 1.50:
  S = R075x2      N= 75  step 2  range 0-148
  P = R150x1      N=150  step 1  range 0-149
  Q = master-N149 N=149  step 2  range 0-298
  R = master-N299 N=299  step 1  range 0-298

  A1  S -> P   range held, N doubles, step halves      model: P softer
  A1' Q -> R   range held, N doubles, step halves      model: R softer
  A2  P -> R   STEP held, N doubles, range doubles     model: EQUAL
  A3  P -> Q   N held, step doubles, range doubles     model: Q sharper

A1' vs A2 is the discriminator: same endpoint, same +150 frames, opposite predictions.

THE REGISTERED THREAT.  Every range-varying arm is confounded IN FAVOUR of the model,
because the arm with fewer frames is also the arm missing half the depth, and its
never-in-focus sites drag it down for reasons that have nothing to do with dilution.
The NEAR mask removes this: comparisons that vary range are read only at tiles whose
focus peak lies inside the shared range, determined from STREHL_ONLY_FRAME probes
that are not an arm of any comparison.
"""
import os, sys, json, numpy as np, softcheck as S, hcoh as HC, hsel as HS, ncurve as NC

T=HC.T; WIN=HC.WIN; MASK=HC.MASK; NB=HC.NB; E=HC.E
B_MAIN=5      # 0.30-0.35 cyc/output-px, where the standing 0.114 result lives
B_PROM=3      # 0.20-0.25 cyc/output-px, the promotable band
DIL=r"C:\dev\strehl-out\V-SOFTCHECK\dilut\bee-1-cpl"
NCV=r"C:\dev\strehl-out\V-SOFTCHECK\ncurve\bee-1-cpl"
# All four arms are re-rendered by drender.py rather than inherited.  ncurve's
# master-N299.tiff.log is ZERO BYTES, so that arm's development gain could not be
# verified, and it is the shared endpoint of both discriminator comparisons.  After
# re-rendering, both inherited arms proved BYTE-IDENTICAL to mine
# (master-N149 / R149x2 sha256 EAE7539A..., master-N299 / R299x1 sha256 CC410176...),
# so the empty log was a logging failure and not a gain difference -- but that could
# only be established by re-rendering, not by assuming.
ARMS={"S":(os.path.join(DIL,"R075x2.tiff"),75,2,"0-148"),
      "P":(os.path.join(DIL,"R150x1.tiff"),150,1,"0-149"),
      "Q":(os.path.join(DIL,"R149x2.tiff"),149,2,"0-298"),
      "R":(os.path.join(DIL,"R299x1.tiff"),299,1,"0-298")}
PROBES=[0,25,50,75,100,125,150,175,200,225,250,275,298]
NEAR_MAX_PROBE=100     # peak at probe index <= this; 125/150 left as an exclusion margin
# A probe whose global registration exceeds HALF A TILE cannot be trusted to sample
# the same scene content as the merge it is being compared against: the correction is
# no longer a small one and phase correlation on a heavily defocused single frame is
# where it fails.  Measured on bee: probes 0-200 register within 60 px and drift
# smoothly with bracket index (real focus breathing), while probes 225,250,275,298
# jump to 250-330 px as a block.  The threshold is T/2 and is not tuned to that gap.
MAX_PROBE_SHIFT=T//2
PEAK_RATIO=1.5         # a tile with no focus peak this strong has no depth to assign
FLAT_FRAC=0.15         # fraction of lowest-content tiles used as the noise sample

def check_exposure():
    """Both sides of every ratio must be developed identically. This is the trap that
    produced a sign flip on this project: a numerator with a tone curve against a
    denominator without one. Hard-error rather than warn."""
    print("EXPOSURE AUDIT -- every arm must carry the same gain or no ratio is valid")
    seen={}
    for k,(p,_,_,_) in ARMS.items():
        lg=p+".log"
        if not os.path.exists(lg): sys.exit("ABORT: no log for arm %s at %s"%(k,lg))
        line=[l.strip() for l in open(lg,encoding="utf-8",errors="replace") if l.startswith("exposure")]
        if not line: sys.exit("ABORT: arm %s log has no exposure line"%k)
        print("  %s  %s"%(k,line[0])); seen[k]=line[0]
    if len(set(seen.values()))!=1:
        sys.exit("ABORT: arms developed at DIFFERENT gain: %s"%seen)
    print("  all four arms identical -- ratios are gain-free\n")

def bandpow(img,oy,ox):
    """Per-tile band power and per-tile mean level, on the OUTPUT pixel grid.

    Tiles that fall outside the image after the arm's global shift return NaN and are
    intersected away later.  The first version indexed them anyway and numpy silently
    produced an empty slice, which is how a tile that was never measured would have
    entered a median as a value."""
    H,W=img.shape[:2]
    out=np.full((len(oy),NB),np.nan); mu=np.full(len(oy),np.nan)
    for i in range(len(oy)):
        y=int(oy[i]); x=int(ox[i])
        if y<0 or x<0 or y+T>H or x+T>W: continue
        t=img[y:y+T,x:x+T]
        m=float(t.mean()); mu[i]=m
        F=np.fft.fft2((t-m)*WIN); P=F.real**2+F.imag**2
        for b in range(NB): out[i,b]=P[MASK[b]].sum()/MASK[b].sum()
    return out,mu

def noise_model(pw,mu,content):
    """Fit noise power = a + b*mean on the flattest tiles, per band.

    Read noise is a constant term and photon noise scales with level, so a
    two-parameter fit spans both. The flattest tiles are the sample because they
    carry the least scene; they are not scene-free, so this OVERSTATES noise and
    therefore UNDERSTATES scene power. That bias is common to every arm."""
    fin=np.isfinite(mu)&np.isfinite(content)&np.isfinite(pw).all(1)
    order=np.argsort(np.where(fin,content,np.inf))
    k=max(12,int(FLAT_FRAC*int(fin.sum())))
    idx=order[:k]
    if not np.isfinite(pw[idx]).all() or k<12:
        sys.exit("ABORT: noise sample has %d usable tiles / non-finite entries"%k)
    coef=[]
    for b in range(NB):
        A=np.stack([np.ones(len(idx)),mu[idx]],1)
        c,_,_,_=np.linalg.lstsq(A,pw[idx,b],rcond=None)
        coef.append(c)
    return np.array(coef)          # (NB,2)

def scene(pw,mu,coef):
    est=coef[:,0][None,:]+np.outer(mu,coef[:,1])
    return np.maximum(pw-est,0.0),est

def load(path):
    return S.load_luma(path,"srgb")

def tiles_for(ref,img,oy,ox):
    sy,sx,m=HS.align(ref,img,oy,ox)
    return sy,sx,m

def commission(img,oy,ox):
    """Both directions plus a null, on the same pixels, before any arm is read.
      NULL     added noise must raise total power and leave SCENE power alone
      DEGRADE  a blur must lower scene power
      IMPROVE  an unsharp mask must RAISE scene power -- the estimator must be free
               to score an image as better, not only as worse."""
    print("COMMISSIONING the scene/noise separation")
    sd=float(img[::8,::8].std())
    base,mu=bandpow(img,oy,ox); c0=base[:,B_MAIN]
    coef=noise_model(base,mu,c0); sc0,_=scene(base,mu,coef)
    rng=np.random.default_rng(9001)
    res={}
    for tag,arr in [("NULL_noise",img+rng.standard_normal(img.shape).astype(np.float32)*sd*0.05),
                    ("DEGRADE_blur",NC.gauss(img,1.0)),
                    ("IMPROVE_sharp",(img+0.7*(img-NC.gauss(img,1.0))).astype(np.float32))]:
        if np.array_equal(arr,img): sys.exit("  COMMISSION FAIL: %s is an INERT plant"%tag)
        pw,mu2=bandpow(arr,oy,ox)
        cf=noise_model(pw,mu2,c0); sc,_=scene(pw,mu2,cf)
        rt=float(np.median(pw[:,B_MAIN]/base[:,B_MAIN]))
        rs=float(np.median(sc[:,B_MAIN]/np.maximum(sc0[:,B_MAIN],1e-12)))
        res[tag]=(rt,rs)
        print("    %-14s total x%.3f   scene x%.3f"%(tag,rt,rs))
    ok=True
    if not (res["NULL_noise"][0]>1.15):
        print("    FAIL: planted noise did not raise total power"); ok=False
    if not (0.85<res["NULL_noise"][1]<1.15):
        print("    FAIL: planted noise moved SCENE power to x%.3f -- not separated"%res["NULL_noise"][1]); ok=False
    if not (res["DEGRADE_blur"][1]<0.70):
        print("    FAIL: blur did not lower scene power enough (x%.3f)"%res["DEGRADE_blur"][1]); ok=False
    if not (res["IMPROVE_sharp"][1]>1.10):
        print("    FAIL: sharpening did not RAISE scene power (x%.3f) -- estimator is"%res["IMPROVE_sharp"][1])
        print("          not free to score an improvement, so a deficit means nothing"); ok=False
    print("    => scene estimator %s\n"%("COMMISSIONED" if ok else "REFUSED"))
    return ok,res

def main():
    check_exposure()
    ref=load(ARMS["R"][0])
    oy,ox=HS.all_tiles(ref.shape)
    print("tiles on the output grid: %d of %dx%d at T=%d"%(len(oy),ref.shape[0],ref.shape[1],T))

    # ---- NEAR mask from single-frame probes (not an arm of any comparison) ----
    sharp=np.full((len(PROBES),len(oy)),np.nan)
    pshift=[]
    for i,k in enumerate(PROBES):
        pth=os.path.join(DIL,"probe","F%03d.tiff"%k)
        im=load(pth); sy,sx,m=tiles_for(ref,im,oy,ox)
        pw,_=bandpow(im,oy+sy,ox+sx)
        sharp[i]=pw[:,2]+pw[:,3]        # 0.15-0.25 cyc/px
        pshift.append((k,int(sy),int(sx)))
        print("  probe %3d  shift(%+4d,%+4d)  tiles in bounds %3d  median sharpness %.4g"%(
              k,sy,sx,int(np.isfinite(sharp[i]).sum()),np.nanmedian(sharp[i])))
        del im
    dy=[a[1] for a in pshift]; dx=[a[2] for a in pshift]
    print("  probe shift range: dy %+d..%+d  dx %+d..%+d"%(min(dy),max(dy),min(dx),max(dx)))
    print("  (a shift that varies smoothly with bracket index is focus breathing: the")
    print("   probes then sample slightly different scene points and the focus index is")
    print("   only as good as a global translation makes it. Spread is reported, not assumed.)")
    rel=np.array([abs(a[1])<=MAX_PROBE_SHIFT and abs(a[2])<=MAX_PROBE_SHIFT for a in pshift])
    print("  RELIABILITY GATE (|shift| <= %d px = T/2): %d of %d probes usable"%(
          MAX_PROBE_SHIFT,rel.sum(),len(PROBES)))
    print("    rejected: %s"%[a[0] for a,r in zip(pshift,rel) if not r])
    relk=np.array(PROBES)[rel]
    if not (relk<=NEAR_MAX_PROBE).any():
        sys.exit("REFUSED: no reliable probe inside the near range")
    if not (relk>NEAR_MAX_PROBE).any():
        sys.exit("REFUSED: no reliable probe beyond the near range -- 'near' has nothing to be near ABOUT")
    print("    focus index is decided on probes %s only"%list(relk))
    sr=sharp[rel]
    ok_all=np.isfinite(sr).all(0)
    print("  tiles in bounds for every RELIABLE probe: %d of %d"%(ok_all.sum(),len(oy)))
    with np.errstate(invalid="ignore"):
        pk=np.nanargmax(np.where(np.isfinite(sr),sr,-np.inf),0)
        pkv=np.nanmax(sr,0); mnv=np.nanmin(sr,0)
    has_peak=pkv>PEAK_RATIO*np.maximum(mnv,1e-12)
    # A tile is NEAR only if it is genuinely sharper in the near half than at the far
    # end of the reliable range.  Without this a tile whose true focus is in the
    # discarded far quarter could take its argmax at probe 0 by accident and be
    # admitted, which is the failure the reliability gate would otherwise create.
    far_ref=sr[-1]
    beats_far=pkv>PEAK_RATIO*np.maximum(far_ref,1e-12)
    near=(relk[pk]<=NEAR_MAX_PROBE)&has_peak&beats_far&ok_all
    print("  of in-bounds tiles: argmax near %d, of those with a peak %d, of those beating probe %d: %d"%(
          int(((relk[pk]<=NEAR_MAX_PROBE)&ok_all).sum()),
          int(((relk[pk]<=NEAR_MAX_PROBE)&has_peak&ok_all).sum()),
          relk[-1],int(near.sum())))
    print("\nNEAR mask: %d tiles of %d (peak probe <= %d, peak/min > %.1f)"%(
          near.sum(),len(oy),NEAR_MAX_PROBE,PEAK_RATIO))
    for r in (1.3,2.0):
        hp=pkv>r*np.maximum(mnv,1e-12)
        print("   sensitivity: peak/min > %.1f -> %d tiles"%(
              r,((relk[pk]<=NEAR_MAX_PROBE)&hp&(pkv>r*np.maximum(far_ref,1e-12))&ok_all).sum()))
    import collections
    print("   focus-peak histogram over in-bounds tiles: %s"%(
          sorted((int(a),int(b)) for a,b in collections.Counter(relk[pk][ok_all]).items())))
    if near.sum()<60: sys.exit("REFUSED: NEAR mask holds %d tiles, under the registered floor of 60"%near.sum())
    del sharp

    # ---- commissioning on one arm ----
    Pimg=load(ARMS["P"][0])
    sub=np.where(near)[0][:200]
    ok,cres=commission(Pimg,oy[sub],ox[sub])

    # ---- per-arm band power on the SAME tiles ----
    pw={}; mus={}; shifts={}
    for k,(p,n,st,rg) in ARMS.items():
        im=Pimg if k=="P" else load(p)
        sy,sx,m=tiles_for(ref,im,oy,ox); shifts[k]=(int(sy),int(sx))
        a,mu=bandpow(im,oy+sy,ox+sx); pw[k]=a; mus[k]=mu
        print("  arm %s  N=%3d step %d range %-6s shift(%+d,%+d)  in bounds %d"%(
              k,n,st,rg,sy,sx,int(np.isfinite(a[:,0]).sum())))
        if k!="P": del im
    del Pimg
    # A tile only counts if EVERY arm measured it. Otherwise a comparison silently
    # runs on a different tile set than its neighbour in the same table.
    armok=np.ones(len(oy),bool)
    for k in ARMS: armok&=np.isfinite(pw[k][:,0])
    near=near&armok
    print("  tiles measured by every arm: %d ; NEAR after intersection: %d"%(armok.sum(),near.sum()))
    if near.sum()<60: sys.exit("REFUSED: NEAR mask holds %d tiles after intersection, under the registered floor of 60"%near.sum())

    base_content=pw["R"][:,B_MAIN]
    sc={}; est={}
    for k in ARMS:
        cf=noise_model(pw[k],mus[k],base_content)
        sc[k],est[k]=scene(pw[k],mus[k],cf)

    def D(a,b,mask,band,which):
        """softening in dex going from arm a (fewer frames) to arm b (more frames)"""
        src=pw if which=="total" else sc
        x=src[a][mask,band]; y=src[b][mask,band]
        good=(x>0)&(y>0)&np.isfinite(x)&np.isfinite(y)
        return float(np.median(np.log10(x[good]/y[good]))),int(good.sum())

    allm=armok.copy()
    COMPS=[("A1","S","P",near,"range held 0-149, N 75->150"),
           ("A1p","Q","R",allm,"range held 0-298, N 149->299"),
           ("A2","P","R",near,"STEP held at 1, N 150->299"),
           ("A3","P","Q",near,"N held ~150, step 1->2")]
    out={}
    for band,bname in [(B_MAIN,"0.30-0.35"),(B_PROM,"0.20-0.25")]:
        print("\n=== band %s cyc/output-px ==="%bname)
        print("  %-4s %-30s %8s %8s %7s"%("id","holds","D_total","D_scene","tiles"))
        for cid,a,b,msk,desc in COMPS:
            dt,nt=D(a,b,msk,band,"total"); ds,ns=D(a,b,msk,band,"scene")
            out["%s|%s"%(bname,cid)]=dict(a=a,b=b,D_total=dt,D_scene=ds,tiles=nt,holds=desc)
            print("  %-4s %-30s %+8.4f %+8.4f %7d"%(cid,desc,dt,ds,nt))
        for src in (["total","scene"] if ok else ["total"]):
            d1=out["%s|A1p"%bname]["D_"+src]; d2=out["%s|A2"%bname]["D_"+src]
            print("  -- decision on D_%s:"%src)
            if d1<=0.02:
                print("     REFUSED: reference effect D(A1')=%+.4f dex is at or below the"%d1)
                print("              registered floor of 0.02; no ratio to a null denominator.")
                continue
            r=d2/d1
            v=("MODEL DIES" if r>=0.70 else "MODEL SURVIVES" if r<=0.35 else "INDETERMINATE")
            print("     D(A1')=%+.4f  D(A2)=%+.4f  ratio %.3f  ==> %s"%(d1,d2,r,v))
            out["%s|verdict_%s"%(bname,src)]=dict(D_A1p=d1,D_A2=d2,ratio=float(r),verdict=v)
    # ---- EXPLORATORY, NOT PRE-REGISTERED ----------------------------------
    # The two estimators disagree in sign, which the pre-registration says to refuse
    # rather than resolve by choosing.  This block does not resolve it and cannot
    # promote the refused verdict.  It asks a narrower question the noise model does
    # not have to be accurate to answer: restricted to tiles where the NOISIER arm's
    # own noise is a small fraction of its total band power, a difference in total
    # power cannot be manufactured by the noise reduction that adding frames buys.
    # At noise fraction f, halving the noise moves total power by at most f/2.
    print("\n--- EXPLORATORY (not pre-registered): high-SNR tiles only ---")
    print("    at noise fraction f, doubling N can move total power by at most f/2,")
    print("    so a |D| above that bound is not a noise artifact.")
    expl={}
    for band,bname in [(B_MAIN,"0.30-0.35"),(B_PROM,"0.20-0.25")]:
        for thr in (0.10,0.05,0.02):
            print("  band %s  noise-fraction cut %.2f  (bound on noise-driven |D|: %.4f dex)"%(
                  bname,thr,abs(np.log10(1-thr/2))))
            for cid,a,b,msk,desc in COMPS:
                with np.errstate(invalid="ignore",divide="ignore"):
                    frac=est[a][:,band]/np.maximum(pw[a][:,band],1e-30)
                hi=msk&np.isfinite(frac)&(frac<thr)
                if hi.sum()<30:
                    print("    %-4s only %d tiles clear the cut -- not reported"%(cid,int(hi.sum()))); continue
                dt,nt=D(a,b,hi,band,"total")
                mf=float(np.nanmedian(frac[hi]))
                bound=abs(np.log10(1-mf/2))
                flag="ABOVE noise bound" if abs(dt)>bound else "within noise bound"
                print("    %-4s %-30s D_total %+8.4f  tiles %4d  median f %.4f  %s"%(
                      cid,desc,dt,nt,mf,flag))
                expl["%s|%.2f|%s"%(bname,thr,cid)]=dict(D_total=dt,tiles=nt,frac=mf,bound=bound)
    out["exploratory_highSNR"]=expl
    out["commissioned"]=bool(ok); out["commission"]=cres
    out["shifts"]=shifts; out["near_tiles"]=int(near.sum())
    p=r"C:\dev\strehl-out\V-SOFTCHECK\dilut\dmeasure.json"
    json.dump(out,open(p,"w"),indent=1,default=float)
    np.savez_compressed(r"C:\dev\strehl-out\V-SOFTCHECK\dilut\dmeasure_tiles.npz",
                        near=near,armok=armok,**{"pw_"+k:pw[k] for k in ARMS},
                        **{"sc_"+k:sc[k] for k in ARMS},**{"est_"+k:est[k] for k in ARMS})
    print("\nmachine-readable: %s"%p)

if __name__=="__main__": main()
