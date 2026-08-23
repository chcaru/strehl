"""V06 -- refine the direct noise-model check: fine bins, low-gradient
restriction (suppresses the defocus term), and a check of ISO / CFA phase."""
import os, glob
import numpy as np, rawpy, exifread
CACHE=r"C:\dev\blog\death-of-software\projects\strehl\experiments\m28-robustness-scale\out\cache"

f0=sorted(glob.glob(r"D:\personal\macro\109MSDCF\*.ARW"))[0]
with rawpy.imread(f0) as r:
    print("raw_pattern\n",r.raw_pattern)
    print("black_level_per_channel",r.black_level_per_channel,"white",r.white_level)
    v=r.raw_image_visible; print("visible",v.shape)
    rc=r.raw_colors_visible
    h,w=v.shape; y0=(h-3072)//2; x0=(w-3072)//2
    sub=rc[y0:y0+3072,x0:x0+3072]
    print("colour index at [0::2,1::2] (green expected =1):",np.unique(sub[0::2,1::2]))
    print("colour index at [0::2,0::2]:",np.unique(sub[0::2,0::2]),
          " [1::2,0::2]:",np.unique(sub[1::2,0::2])," [1::2,1::2]:",np.unique(sub[1::2,1::2]))
with open(f0,"rb") as fh:
    t=exifread.process_file(fh,details=False)
print("EXIF ISO:",t.get("EXIF ISOSpeedRatings"),"  Exposure:",t.get("EXIF ExposureTime"),
      "  FNumber:",t.get("EXIF FNumber"))

a=np.load(os.path.join(CACHE,"109MSDCF.npy")).astype(np.float64)
n=len(a); g_dn=160.0/436.8; rn2=(4.20*g_dn)**2
gg=a.reshape(n,-1).mean(axis=1); gg/=np.median(gg); a=a/gg[:,None,None]
ref=np.median(a,axis=0)
gy,gx=np.gradient(ref); grad=np.sqrt(gy**2+gx**2)
dif=(a[1:-1]-(a[:-2]+a[2:])/2.)/np.sqrt(1.5)
S=(a[:-2]+a[2:])/2.
gmask=np.broadcast_to(grad<np.percentile(grad,30),S.shape)

for label,mask in (("all pixels",None),("low-|grad| 30%",gmask)):
    print(f"\n--- {label} ---")
    edges=np.array([0,60,120,200,300,450,650,900,1200,1600,2100,2800,3600,5000,7000,10000])
    xs=[];ys=[];ws=[]
    print(f"{'S bin':>14s}{'n':>10s}{'sig_meas':>10s}{'sig_model':>10s}{'ratio':>8s}")
    for lo,hi in zip(edges[:-1],edges[1:]):
        m=(S>=lo)&(S<hi)
        if mask is not None: m&=mask
        if m.sum()<20000: continue
        v=dif[m]; sm=1.4826*np.median(np.abs(v-np.median(v)))
        sc=float(np.median(S[m])); mo=np.sqrt(g_dn*sc+rn2)
        xs.append(sc); ys.append(sm**2); ws.append(m.sum())
        print(f"{lo:6.0f}-{hi:<7.0f}{m.sum():10d}{sm:10.3f}{mo:10.3f}{sm/mo:8.4f}")
    xs=np.array(xs);ys=np.array(ys);ws=np.array(ws,float)
    A=np.vstack([xs,np.ones_like(xs)]).T
    sol,*_=np.linalg.lstsq(A*np.sqrt(ws)[:,None],ys*np.sqrt(ws),rcond=None)
    print(f"  weighted fit: g={sol[0]:.4f} (model {g_dn:.4f}, {100*(sol[0]/g_dn-1):+.1f}%)"
          f"   intercept={sol[1]:.2f} DN^2 (model {rn2:.2f}) -> RN_e={np.sqrt(max(sol[1],0))/sol[0]:.2f} e-")
    # gain-only fit with the model intercept pinned
    gonly=float(np.sum(ws*xs*(ys-rn2))/np.sum(ws*xs*xs))
    print(f"  intercept pinned to model: g={gonly:.4f}  ({100*(gonly/g_dn-1):+.1f}% vs model)")
    resid=np.sqrt(np.maximum(ys,0))/np.sqrt(g_dn*xs+rn2)
    print(f"  ratio meas/model across bins: min {resid.min():.3f} max {resid.max():.3f} "
          f"median {np.median(resid):.3f}")
