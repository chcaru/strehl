"""V11 -- adversarial probes of M27: (a) is the null stable to WHERE the null
block is removed, (b) is the detector blind (oracle grouping?), (c) does a
self-normalised shape statistic really NEVER carry presence-of-evidence
(discipline 120's 'never'), (d) is nwide floored at 1."""
import os
import numpy as np
vol=np.load(r"C:\dev\blog\death-of-software\projects\strehl\experiments\m31-verification\out\cb_vol_mine.npy")
n=vol.shape[0]
def stats(v):
    k=v.argmax(0); fk=np.take_along_axis(v,k[None],0)[0]; fmin=v.min(0)
    km1,kp1=np.clip(k-1,0,v.shape[0]-1),np.clip(k+1,0,v.shape[0]-1)
    fm=np.take_along_axis(v,km1[None],0)[0]; fp=np.take_along_axis(v,kp1[None],0)[0]
    den=fm-2*fk+fp; ok=np.abs(den)>1e-6
    delta=np.clip(np.where(ok,0.5*(fm-fp)/np.where(ok,den,1),0.0),-0.5,0.5)
    curv=(2*fk-fm-fp)/np.maximum(fk-fmin,1e-6)
    return k,delta,curv,fk,fmin
k_full,_,curv_full,fk_full,fmin_full=stats(vol)
c_full=(fk_full-fmin_full)/np.maximum(fk_full,1e-6)
rel=(c_full>0.6)&(k_full>2)&(k_full<n-3)&(fk_full>np.percentile(fk_full,50))
CTL=rel&(k_full>=26)&(k_full<34); K0=12
m=lambda a,q: float(np.median(a[q]))

print("=== (a) is the 1.40-1.43 null stable to WHERE the null block sits? ===")
print(f"{'gap':>4}" + "".join(f"{('null@'+str(s)):>11s}" for s in ("end",0,4,44,'rand')))
rng=np.random.default_rng(2)
for gw in (1,2,4,6,8,12):
    pos=rel&(k_full>=K0)&(k_full<K0+gw)
    row=[]
    for where in ("end",0,4,44,"rand"):
        kn=np.ones(n,bool)
        if where=="end": kn[n-gw:]=False
        elif where=="rand":
            idx=rng.choice(np.concatenate([np.arange(0,10),np.arange(40,n)]),gw,replace=False); kn[idx]=False
        else: kn[where:where+gw]=False
        _,_,c0,_,_=stats(vol[kn]); row.append(m(c0,pos)/m(c0,CTL))
    print(f"{gw:>4}"+"".join(f"{v:11.3f}" for v in row))

print("\n=== (b) BLIND grouping: bin by REDUCED-stack argmax, look for the band ===")
for gw in (1,4):
    keep=np.ones(n,bool); keep[K0:K0+gw]=False
    kg,dg,cg,_,_=stats(vol[keep])
    print(f"  gap {gw} frames removed at original index {K0}..{K0+gw-1} "
          f"(reduced index {K0}..): median curv by reduced argmax bin")
    prof=[]
    for kk in range(2,n-gw-2):
        mm=rel&(kg==kk)
        prof.append((kk,int(mm.sum()),float(np.median(cg[mm])) if mm.sum()>300 else np.nan))
    s="  "; 
    for kk,cnt,v in prof:
        s+=f"{kk}:{v:.2f} " if not np.isnan(v) else f"{kk}:--- "
    print("   "+s)
    vals=np.array([v for _,_,v in prof]); ks=np.array([k for k,_,_ in prof])
    good=~np.isnan(vals)
    top=ks[good][np.argsort(vals[good])[::-1][:5]]
    print(f"   -> top-5 bins by median curv: {list(top)}   (gap sits at reduced index "
          f"{max(K0-1,0)}..{K0})   argmax bin = {ks[good][np.nanargmax(vals[good])]}")

print("\n=== (c) discipline 120 says a self-normalised shape statistic NEVER carries")
print("        presence of evidence.  Does curv separate information-rich from")
print("        information-free pixels on the FULL 53-frame stack? ===")
lowc=(c_full<=0.6)
dim=(fk_full<=np.percentile(fk_full,10))
flat=(fk_full<=np.percentile(fk_full,2))
for lab,mask in (("reliable (info-rich)",rel),("low peak-contrast",lowc),
                 ("dimmest 10% peaks",dim),("dimmest 2% peaks",flat)):
    print(f"   {lab:24s} n={int(mask.sum()):>9,}  median curv {m(curv_full,mask):8.4f}"
          f"   median |delta| {m(np.abs(stats(vol)[1]),mask):.4f}")

print("\n=== (d) nwide floor: can it ever read below 1? ===")
for s in (1,2,3,4,6,9,13):
    sub=vol[::s]; fk=sub.max(0)
    nw=(sub>=(fmin_full+0.5*(fk-fmin_full))[None]).sum(0)
    print(f"   step {s:>2} ({sub.shape[0]:>2} frames): median nwide {float(np.median(nw[rel])):.2f}"
          f"   min {int(nw[rel].min())}   frac==0 {100*float((nw[rel]==0).mean()):.3f}%"
          f"   frac<=1 {100*float((nw[rel]<=1).mean()):.2f}%   mean {float(nw[rel].mean()):.3f}")
