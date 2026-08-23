"""V02 -- Is M28 S1's 1.13->12.30 separation curve a geometric-warp signature,
or an artefact of the per-frame gain estimator that M28 S6 calls a confound?"""
import os
import numpy as np
CACHE = r"C:\dev\blog\death-of-software\projects\strehl\experiments\m28-robustness-scale\out\cache"
a_raw = np.load(os.path.join(CACHE, "109MSDCF.npy")).astype(np.float64)
n = len(a_raw)
ISO=160.0; g_dn=ISO/436.8; rn2=(4.20*g_dn)**2

def area_mean(a,d):
    N,h,w=a.shape; h2,w2=(h//d)*d,(w//d)*d
    return a[:,:h2,:w2].reshape(N,h2//d,d,w2//d,d).mean(axis=(2,4))

flat = a_raw.reshape(n,-1)
gains = {
 "median (script 02 uses this)": np.median(flat,axis=1),
 "mean   (scripts 03/04/05)":    flat.mean(axis=1),
 "none":                         np.ones(n),
}
print("gain estimator p-p:")
for k,v in gains.items():
    gg=v/np.median(v); print(f"  {k:32s} p-p {100*(gg.max()-gg.min()):6.2f}%")

print("\npairwise median |z| at d=8 vs frame separation, by gain estimator")
print(f"{'estimator':34s}" + "".join(f"{('dk='+str(k)):>9s}" for k in (1,2,4,8,16)) + "   last/first")
for k,v in gains.items():
    gg=v/np.median(v)
    a8=area_mean(a_raw/gg[:,None,None],8)
    ref=np.median(a8,axis=0)
    sig=np.sqrt(np.maximum(g_dn*np.maximum(ref,0)+rn2,1e-6))/8.0
    row=[float(np.median(np.abs(a8[dk:]-a8[:-dk])/(sig*np.sqrt(2.0)))) for dk in (1,2,4,8,16)]
    print(f"{k:34s}" + "".join(f"{x:9.3f}" for x in row) + f"   {row[-1]/row[0]:8.2f}x")

# --- decisive test: remove a per-PAIR scalar gain, then re-measure -----------
# If the deterministic term is geometric (breathing), a scalar cannot remove it.
# If it is photometric, a single scalar per pair removes most of it.
print("\nafter removing a per-PAIR least-squares scalar gain (a[k+dk] ~ c*a[k]):")
gg = np.median(flat,axis=1); gg/=np.median(gg)
a8 = area_mean(a_raw/gg[:,None,None],8)
ref=np.median(a8,axis=0)
sig=np.sqrt(np.maximum(g_dn*np.maximum(ref,0)+rn2,1e-6))/8.0
print(f"{'':34s}" + "".join(f"{('dk='+str(k)):>9s}" for k in (1,2,4,8,16)))
row_raw=[];row_fit=[];cs=[]
for dk in (1,2,4,8,16):
    A=a8[:-dk]; B=a8[dk:]
    c=(A*B).sum(axis=(1,2))/(A*A).sum(axis=(1,2))
    row_raw.append(float(np.median(np.abs(B-A)/(sig*np.sqrt(2.0)))))
    row_fit.append(float(np.median(np.abs(B-c[:,None,None]*A)/(sig*np.sqrt(2.0)))))
    cs.append((float(c.min()),float(c.max())))
print(f"{'raw pairwise |z|':34s}" + "".join(f"{x:9.3f}" for x in row_raw))
print(f"{'after per-pair scalar gain':34s}" + "".join(f"{x:9.3f}" for x in row_fit))
print(f"{'fitted c range':34s}" + "".join(f"{(b-1)*100:9.3f}" for _,b in cs) + "  (max %% dev)")
print(f"{'reduction':34s}" + "".join(f"{100*(1-f/r):8.1f}%" for r,f in zip(row_raw,row_fit)))

# same, but starting from the MEAN-gain normalised data
print("\nsame test starting from mean-gain normalisation:")
gg = flat.mean(axis=1); gg/=np.median(gg)
a8 = area_mean(a_raw/gg[:,None,None],8)
ref=np.median(a8,axis=0)
sig=np.sqrt(np.maximum(g_dn*np.maximum(ref,0)+rn2,1e-6))/8.0
row_raw=[];row_fit=[]
for dk in (1,2,4,8,16):
    A=a8[:-dk]; B=a8[dk:]
    c=(A*B).sum(axis=(1,2))/(A*A).sum(axis=(1,2))
    row_raw.append(float(np.median(np.abs(B-A)/(sig*np.sqrt(2.0)))))
    row_fit.append(float(np.median(np.abs(B-c[:,None,None]*A)/(sig*np.sqrt(2.0)))))
print(f"{'raw pairwise |z|':34s}" + "".join(f"{x:9.3f}" for x in row_raw))
print(f"{'after per-pair scalar gain':34s}" + "".join(f"{x:9.3f}" for x in row_fit))
print(f"{'reduction':34s}" + "".join(f"{100*(1-f/r):8.1f}%" for r,f in zip(row_raw,row_fit)))
