"""V15 -- M29 sec 4.  (1) independently reproduce script 05's n-sweep.
(2) Ask whether Q10's discriminator had any POWER: how big could the exponent
have been under the pure-shot-noise alternative, given the measured scene/noise
split?  (3) Re-price the flat-field budget with a PRNU term at the bound V14
measured.  (4) Sensitivity of the D=0.999 refutation to displacement error."""
import glob, os
import numpy as np, rawpy
from scipy.ndimage import gaussian_filter
BLACK,SIG=512.0,24.0
ISO,RN_E=160.0,4.20
def hp(m): return m-gaussian_filter(m,SIG)
fs=sorted(glob.glob(r"D:\personal\macro\109MSDCF\*.ARW"))[:16]
rs=[];gs=[]
for f in fs:
    with rawpy.imread(f) as r: g=r.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
    rs.append(g/np.maximum(gaussian_filter(g,SIG),1.0))
    gs.append(g)
print("=== (1) independent n-sweep, 109MSDCF ===")
print(f"{'n':>4s}{'map rms (mine)':>16s}{'script05':>10s}{'pair-diff':>12s}{'script05':>10s}")
pub_r=[0.14412132,0.14545469,0.14841214,0.15342528,0.15447406]
pub_p=[float('nan'),0.01608641,0.01519320,0.02200266,0.02951171]
mine=[]
for i,n in enumerate((1,2,4,8,16)):
    m=hp(np.mean(rs[:n],axis=0)-1.0); rm=float(m.std())
    if n>=2:
        a=hp(np.mean(rs[:n//2],axis=0)-1.0); b=hp(np.mean(rs[n//2:n],axis=0)-1.0)
        pd=float(((a-b)/2.0).std())
    else: pd=float('nan')
    mine.append((rm,pd))
    print(f"{n:4d}{rm:16.5f}{pub_r[i]:10.5f}{pd:12.5f}{pub_p[i]:10.5f}")
r1,rN=mine[0][0],mine[-1][0]
print(f"  exponent {np.log(rN/r1)/np.log(16):+.4f}  (script 05: +0.0250)")
pe=[m[1] for m in mine[1:]]
print(f"  pair exponent {np.log(pe[-1]/pe[0])/np.log(8):+.4f}  (script 05: +0.2918)")

print("\n=== (2) did Q10's discriminator have any POWER? ===")
g_dn=ISO/436.8
g0=gs[0]; lo=np.maximum(gaussian_filter(g0,SIG),1.0)
sig=np.sqrt(np.maximum(g_dn*g0,0)+ (RN_E*g_dn)**2)
frac=sig/np.maximum(g0,1.0)
# model-predicted rms of the photon term in a ONE-frame map (highpass ~ unity gain
# on white noise); weight by the same pixels the map covers
pred=float(np.sqrt(np.mean(frac[g0>50]**2)))
pdn=mine[1][1]*np.sqrt(2)           # measured single-frame map noise, from pair-diff
print(f"  median green signal            {np.median(g0):8.1f} DN")
print(f"  model photon term in a 1-frame map    {100*pred:6.3f}%")
print(f"  measured (sqrt2 x n=2 pair-diff)      {100*pdn:6.3f}%")
print(f"  measured n=1 map rms                  {100*r1:6.3f}%")
for nm,sn in (("model",pred),("measured",pdn)):
    sc2=max(r1**2-sn**2,0.0)
    pr16=np.sqrt(sc2+sn**2/16)
    print(f"  under PURE SHOT NOISE ({nm}): rms(16) would be {100*pr16:6.3f}%"
          f"  -> exponent {np.log(pr16/r1)/np.log(16):+.4f}")
print("  ...vs the pure-scene alternative exponent 0.0000, and the measured +0.0250.")

print("\n=== (3) flat-field budget re-priced with a PRNU term ===")
print(f"{'ISO':>4s}{'S':>7s}{'per-frame':>11s}{'n=20 photon':>13s}"
      f"{'+PRNU 0.26%':>13s}{'5% dust: doc':>14s}{'with PRNU':>11s}{'n=64 doc':>10s}{'n=64+PRNU':>11s}")
for iso in (100.0,160.0):
    gd=iso/436.8
    for S in (8000.0,12000.0):
        per=np.sqrt(gd*S+(RN_E*gd)**2)/S
        f20=per/np.sqrt(20); f64=per/np.sqrt(64)
        for P in (0.0026,):
            t20=np.sqrt(f20**2+P**2); t64=np.sqrt(f64**2+P**2)
            print(f"{iso:4.0f}{S:7.0f}{100*per:10.3f}%{100*f20:12.3f}%"
                  f"{100*t20:12.3f}%{0.05/f20:13.0f}s{0.05/t20:10.0f}s"
                  f"{0.05/f64:9.0f}s{0.05/t64:10.0f}s")

print("\n=== (4) how wrong would the displacement have to be to save the claim? ===")
print(f"{'d (green px)':>13s}{'D n=3 sd=5':>12s}{'D n=3 sd=10':>13s}{'D n=3 sd=20':>13s}")
for d in (0.07,0.22,0.44,1.0,2.0,3.0,5.0,5.47,8.0):
    row=""
    for sd in (5.0,10.0,20.0):
        offs=np.array([-d,0.0,d])
        row+=f"{float(np.mean(np.exp(-(offs**2)/(2*sd**2)))):12.4f} " if sd==5.0 else \
             f"{float(np.mean(np.exp(-(offs**2)/(2*sd**2)))):12.4f} "
    print(f"{d:13.2f}{row}")
print("  D<0.7 at n=3 requires d = 5.47 px (sigma_d=5); measured 0.07-0.22, "
      "peak-lock-corrected 0.15-0.43.")
