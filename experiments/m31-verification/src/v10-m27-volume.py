"""V10 -- build an INDEPENDENT focus volume for coffee-bean from D:\personal,
compare to the committed cb_vol.npy, and reproduce M27 S1/S3/S4 tables."""
import os, glob, time
import numpy as np, rawpy
from scipy.ndimage import sobel, uniform_filter
OUT=r"C:\dev\blog\death-of-software\projects\strehl\experiments\m31-verification\out"
mine=os.path.join(OUT,"cb_vol_mine.npy")
if not os.path.exists(mine):
    fs=sorted(glob.glob(r"D:\personal\macro\coffee-bean\*.ARW"))[::2]
    t0=time.time(); v=[]
    for f in fs:
        with rawpy.imread(f) as r:
            a=r.raw_image_visible[0::2,1::2][1172-750:1172+750,1757-750:1757+750].astype(np.float32)
        v.append(uniform_filter(np.hypot(sobel(a,1,mode="nearest"),sobel(a,0,mode="nearest")),
                                size=5,mode="nearest"))
    v=np.stack(v); np.save(mine,v); print(f"built {v.shape} in {time.time()-t0:.0f}s")
vol=np.load(mine)
ref=np.load(r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files\cb_vol.npy")
print(f"mine {vol.shape}  committed-input {ref.shape}  max|diff| {np.abs(vol-ref).max():.6g}")
n=vol.shape[0]

def stats(v):
    k=v.argmax(0); fk=np.take_along_axis(v,k[None],0)[0]; fmin=v.min(0)
    km1,kp1=np.clip(k-1,0,v.shape[0]-1),np.clip(k+1,0,v.shape[0]-1)
    fm=np.take_along_axis(v,km1[None],0)[0]; fp=np.take_along_axis(v,kp1[None],0)[0]
    den=fm-2*fk+fp; ok=np.abs(den)>1e-6
    delta=np.clip(np.where(ok,0.5*(fm-fp)/np.where(ok,den,1),0.0),-0.5,0.5)
    curv=(2*fk-fm-fp)/np.maximum(fk-fmin,1e-6)
    half=fmin+0.5*(fk-fmin); nwide=(v>=half[None]).sum(0).astype(np.float32)
    return k,delta,curv,fk,nwide
k_full,_,_,fk_full,_=stats(vol)
fmin_full=vol.min(0)
c_full=(fk_full-fmin_full)/np.maximum(fk_full,1e-6)
rel=(c_full>0.6)&(k_full>2)&(k_full<n-3)&(fk_full>np.percentile(fk_full,50))
K0=12; CTL=(rel)&(k_full>=26)&(k_full<34)
print(f"\nreliable {int(rel.sum()):,}  fixed control band {int(CTL.sum()):,} px")
print(f"{'gap':>4}{'pos n':>10}{'curv ratio':>12}{'curv null':>11}{'excess':>9}"
      f"{'|d| ratio':>11}{'|d| null':>10}{'excess':>9}")
for gw in (1,2,4,6,8,12):
    pos=rel&(k_full>=K0)&(k_full<K0+gw)
    keep=np.ones(n,bool); keep[K0:K0+gw]=False
    _,dg,cg=stats(vol[keep])[:3]
    kn=np.ones(n,bool); kn[n-gw:]=False
    _,d0,c0=stats(vol[kn])[:3]
    m=lambda a,q: float(np.median(a[q]))
    cr=m(cg,pos)/m(cg,CTL); cn=m(c0,pos)/m(c0,CTL)
    dr=m(np.abs(dg),pos)/m(np.abs(dg),CTL); dn=m(np.abs(d0),pos)/m(np.abs(d0),CTL)
    print(f"{gw:>4}{int(pos.sum()):>10,}{cr:>12.3f}{cn:>11.3f}{cr-cn:>+9.3f}"
          f"{dr:>11.3f}{dn:>10.3f}{dr-dn:>+9.3f}")

print("\n--- S3 uniform decimation ---")
print(f"{'step':>5}{'frames':>8}{'med curv':>11}{'med |d|':>10}{'med nwide':>11}"
      f"{'med own-min':>13}{'min/full':>10}{'nwide FULLmin':>15}{'<=1 sample':>12}")
for s in (1,2,3,4,6):
    sub=vol[::s]; _,d,cv,fk,nw=stats(sub)
    om=sub.min(0)
    nwfix=(sub>=(fmin_full+0.5*(fk-fmin_full))[None]).sum(0)
    print(f"{s:>5}{sub.shape[0]:>8}{float(np.median(cv[rel])):>11.4f}"
          f"{float(np.median(np.abs(d[rel]))):>10.4f}{float(np.median(nw[rel])):>11.2f}"
          f"{float(np.median(om[rel])):>13.2f}"
          f"{float(np.median(om[rel]))/float(np.median(fmin_full[rel])):>10.4f}"
          f"{float(np.median(nwfix[rel])):>15.2f}{100*float((nwfix[rel]<=1).mean()):>11.2f}%")
