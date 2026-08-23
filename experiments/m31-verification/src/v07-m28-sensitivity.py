"""V07 -- independent re-implementation of M28 S3/S4 sensitivity, plus the
honest-FPR and threshold-free (AUC) versions the milestone did not report."""
import os
import numpy as np
CACHE=r"C:\dev\blog\death-of-software\projects\strehl\experiments\m28-robustness-scale\out\cache"
raw=np.load(os.path.join(CACHE,"109MSDCF.npy")).astype(np.float64)
n=len(raw); ISO=160.0; g_dn=ISO/436.8; rn2=(4.20*g_dn)**2
gg=raw.reshape(n,-1).mean(axis=1); gg/=np.median(gg); raw=raw/gg[:,None,None]
H=raw.shape[1]; k0=n//2; W=128; SH=[0,1,2,4,8,16,32]
def area_mean(a,d):
    N,h,w=a.shape; h2,w2=(h//d)*d,(w//d)*d
    return a[:,:h2,:w2].reshape(N,h2//d,d,w2//d,d).mean(axis=(2,4))
def nz(a,d):
    r=(a[:-2]+a[2:])/2.
    s=np.sqrt(np.maximum(g_dn*np.maximum(r,0)+rn2,1e-6))/d
    return np.abs(a[1:-1]-r)/(s*np.sqrt(1.5))
org=[(iy*W,ix*W) for iy in range(H//W) for ix in range(H//W)
     if iy*W+W+max(SH)<=H and ix*W+W<=H]
print(f"{len(org)} tiles, plant frame {k0}")
def auc(pos,neg):
    from scipy.stats import rankdata
    r=rankdata(np.concatenate([pos,neg]))
    return (r[:len(pos)].sum()-len(pos)*(len(pos)+1)/2)/(len(pos)*len(neg))

for d in (4,8,16):
    tb=W//d
    bz=nz(area_mean(raw,d),d); kk=k0-1
    tm=lambda z,k:np.array([np.median(z[k,y//d:y//d+tb,x//d:x//d+tb]) for (y,x) in org])
    null=tm(bz,kk)
    others=np.concatenate([tm(bz,k) for k in range(bz.shape[0]) if k!=kk])
    thr_o={p:np.percentile(others,100-p) for p in (5.,1.,0.1)}
    thr_n={p:np.percentile(null,100-p) for p in (5.,1.,0.1)}
    print(f"\n=== d={d}  tile {tb}x{tb} ===")
    print(f"  thresholds from OTHER frames (as published): "+"  ".join(f"{p}%={v:.3f}" for p,v in thr_o.items()))
    print(f"  thresholds from the TESTED frame's own null : "+"  ".join(f"{p}%={v:.3f}" for p,v in thr_n.items()))
    print(f"  null median {np.median(null):.4f}   others median {np.median(others):.4f}"
          f"   others p99/p95 tail ratio {thr_o[1.]/thr_o[5.]:.2f} vs null {thr_n[1.]/thr_n[5.]:.2f}")
    print(f"  {'s':>3s}{'med|z|':>9s}"
          +"".join(f"{('pub@'+str(p)):>10s}" for p in (5.,1.,0.1))
          +"".join(f"{('own@'+str(p)):>10s}" for p in (5.,1.,0.1))+f"{'AUC':>8s}")
    for s in SH:
        pl=raw.copy()
        for (y,x) in org: pl[k0,y:y+W,x:x+W]=raw[k0,y+s:y+s+W,x:x+W]
        t=tm(nz(area_mean(pl,d),d),kk)
        print(f"  {s:3d}{np.median(t):9.3f}"
              +"".join(f"{100*(t>thr_o[p]).mean():9.1f}%" for p in (5.,1.,0.1))
              +"".join(f"{100*(t>thr_n[p]).mean():9.1f}%" for p in (5.,1.,0.1))
              +f"{auc(t,null):8.3f}")
        del pl
