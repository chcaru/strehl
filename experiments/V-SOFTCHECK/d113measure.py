"""Does MY OWN standing depth-softening result survive a noise decomposition?

The 0.114 I reported -- 63 frames softer than 32 at matched range, 0.30-0.35
cyc/output-px -- came from 113MSDCF and from TOTAL band power.  More frames means
less output noise, less noise means less band power, and that alone reads as
softening.  This runs the same two arms through the scene/noise separation that was
commissioned in dmeasure.py, on the same pixels, in both bands.

Both arms span the full focus range by construction, so there is no range confound
and no focus mask is needed: this is the cleanest form of the comparison available.
"""
import os, sys, json, numpy as np, softcheck as S, hsel as HS
import dmeasure as DM

DIR=r"C:\dev\strehl-out\V-SOFTCHECK\dilut\113MSDCF"
ARMS={"N032":(os.path.join(DIR,"N032.tiff"),32,2),
      "N063":(os.path.join(DIR,"N063.tiff"),63,1)}

def main():
    print("EXPOSURE AUDIT")
    seen={}
    for k,(p,_,_) in ARMS.items():
        line=[l.strip() for l in open(p+".log",encoding="utf-8",errors="replace") if l.startswith("exposure")]
        if not line: sys.exit("ABORT: %s has no exposure line"%k)
        print("  %s  %s"%(k,line[0])); seen[k]=line[0]
    if len(set(seen.values()))!=1: sys.exit("ABORT: arms at different gain")
    print("  identical -- ratios are gain-free\n")

    ref=DM.load(ARMS["N063"][0])
    oy,ox=HS.all_tiles(ref.shape)
    print("tiles: %d"%len(oy))
    pw={}; mus={}; est={}; sc={}
    ref_img=ref
    for k,(p,n,st) in ARMS.items():
        im=ref_img if k=="N063" else DM.load(p)
        sy,sx,m=DM.tiles_for(ref,im,oy,ox)
        a,mu=DM.bandpow(im,oy+sy,ox+sx); pw[k]=a; mus[k]=mu
        print("  arm %s N=%2d step %d  shift(%+d,%+d)  in bounds %d"%(
              k,n,st,sy,sx,int(np.isfinite(a[:,0]).sum())))
        if k=="N032":
            ok,cres=DM.commission(im,oy[:200]+sy,ox[:200]+sx)
        if k!="N063": del im
    okm=np.isfinite(pw["N032"][:,0])&np.isfinite(pw["N063"][:,0])
    print("  tiles measured by both arms: %d"%okm.sum())
    base=pw["N063"][:,DM.B_MAIN]
    for k in ARMS:
        cf=DM.noise_model(pw[k],mus[k],base); sc[k],est[k]=DM.scene(pw[k],mus[k],cf)

    out={"commissioned":bool(ok),"commission":cres}
    for band,bname in [(DM.B_MAIN,"0.30-0.35"),(DM.B_PROM,"0.20-0.25")]:
        print("\n=== band %s cyc/output-px ==="%bname)
        for which,src in (("total",pw),("scene",sc)):
            x=src["N032"][okm,band]; y=src["N063"][okm,band]
            g=(x>0)&(y>0)&np.isfinite(x)&np.isfinite(y)
            d=float(np.median(np.log10(x[g]/y[g])))
            pct=100*(10**d-1)
            print("  D_%-5s = %+.4f dex  -> N=63 is %+.1f%% %s than N=32   (%d tiles)"%(
                  which,d,abs(pct),"SOFTER" if d>0 else "SHARPER",int(g.sum())))
            out["%s|%s"%(bname,which)]=dict(D=d,pct=pct,tiles=int(g.sum()))
        with np.errstate(invalid="ignore",divide="ignore"):
            frac=est["N032"][:,band]/np.maximum(pw["N032"][:,band],1e-30)
        for thr in (0.10,0.05,0.02):
            hi=okm&np.isfinite(frac)&(frac<thr)
            if hi.sum()<30:
                print("  high-SNR f<%.2f: only %d tiles, not reported"%(thr,int(hi.sum()))); continue
            x=pw["N032"][hi,band]; y=pw["N063"][hi,band]
            g=(x>0)&(y>0)
            d=float(np.median(np.log10(x[g]/y[g])))
            mf=float(np.nanmedian(frac[hi])); bound=abs(np.log10(1-mf/2))
            print("  high-SNR f<%.2f: D_total %+.4f dex  tiles %4d  median f %.4f  bound %.4f  %s"%(
                  thr,d,int(g.sum()),mf,bound,"ABOVE noise bound" if abs(d)>bound else "within noise bound"))
            out["%s|hi%.2f"%(bname,thr)]=dict(D=d,tiles=int(g.sum()),frac=mf,bound=bound)
    p=os.path.join(DIR,"d113measure.json"); json.dump(out,open(p,"w"),indent=1,default=float)
    print("\nmachine-readable: %s"%p)

if __name__=="__main__": main()
