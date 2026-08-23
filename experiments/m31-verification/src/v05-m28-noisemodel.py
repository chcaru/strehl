"""V05 -- M28 S2 claims the M4 noise model predicts the clean adjacent-frame
tile residual to 9.9% with NO FREE PARAMETERS.  Test it three ways."""
import os
import numpy as np
CACHE=r"C:\dev\blog\death-of-software\projects\strehl\experiments\m28-robustness-scale\out\cache"
a_raw=np.load(os.path.join(CACHE,"109MSDCF.npy")).astype(np.float64)
n=len(a_raw); ISO=160.0; g_dn=ISO/436.8; rn2=(4.20*g_dn)**2
def area_mean(a,d):
    if d==1: return a
    N,h,w=a.shape; h2,w2=(h//d)*d,(w//d)*d
    return a[:,:h2,:w2].reshape(N,h2//d,d,w2//d,d).mean(axis=(2,4))
flat=a_raw.reshape(n,-1)
GAINS={"mean (as published)":flat.mean(axis=1),"median":np.median(flat,axis=1),"NONE":np.ones(n)}

def tile_med(z,tb):
    ny=z.shape[1]//tb; nx=z.shape[2]//tb
    return np.median(z[:,:ny*tb,:nx*tb].reshape(z.shape[0],ny,tb,nx,tb),axis=(2,4)).ravel()

print("=== A: is 1.099x robust to the per-frame gain fit (the 'free parameter')? ===")
print(f"{'gain':22s}{'d':>4s}{'2nd-diff tile|z|':>18s}{'/0.6745':>9s}{'1st-diff tile|z|':>18s}{'/0.6745':>9s}")
for gname,gv in GAINS.items():
    gg=gv/np.median(gv)
    for d in (8,):
        A=area_mean(a_raw/gg[:,None,None],d)
        R=(A[:-2]+A[2:])/2.; S=np.sqrt(np.maximum(g_dn*np.maximum(R,0)+rn2,1e-6))/d
        z2=np.abs(A[1:-1]-R)/(S*np.sqrt(1.5))
        R1=(A[:-1]+A[1:])/2.; S1=np.sqrt(np.maximum(g_dn*np.maximum(R1,0)+rn2,1e-6))/d
        z1=np.abs(A[1:]-A[:-1])/(S1*np.sqrt(2.))
        t2=np.median(tile_med(z2,128//d)); t1=np.median(tile_med(z1,128//d))
        print(f"{gname:22s}{d:4d}{t2:18.4f}{t2/0.6745:9.4f}{t1:18.4f}{t1/0.6745:9.4f}")

print("\n=== B: scale sweep of the same statistic (flat at 0.6745 iff pixels are")
print("       independent AND no deterministic term).  mean gain. ===")
gg=flat.mean(axis=1); gg/=np.median(gg)
print(f"{'d':>4s}{'2nd-diff med|z| (all px)':>26s}{'/0.6745':>9s}")
for d in (1,2,4,8,16,32):
    A=area_mean(a_raw/gg[:,None,None],d)
    R=(A[:-2]+A[2:])/2.; S=np.sqrt(np.maximum(g_dn*np.maximum(R,0)+rn2,1e-6))/d
    v=float(np.median(np.abs(A[1:-1]-R)/(S*np.sqrt(1.5))))
    print(f"{d:4d}{v:26.4f}{v/0.6745:9.4f}")

print("\n=== C: DIRECT model check at d=1 (no independence assumption).")
print("       Robust sigma of the 2nd difference, binned by signal level. ===")
A=a_raw/gg[:,None,None]
dif=(A[1:-1]-(A[:-2]+A[2:])/2.)/np.sqrt(1.5)
S=(A[:-2]+A[2:])/2.
edges=np.array([0,100,200,400,700,1000,1500,2000,3000,5000,8000,12000])
print(f"{'S bin DN':>14s}{'n':>10s}{'sigma_meas':>12s}{'sigma_model':>12s}{'meas/model':>12s}")
xs=[];ys=[];ws=[]
for lo,hi in zip(edges[:-1],edges[1:]):
    m=(S>=lo)&(S<hi)
    if m.sum()<5000: continue
    v=dif[m]
    smeas=1.4826*np.median(np.abs(v-np.median(v)))
    sc=float(np.median(S[m]))
    smod=np.sqrt(g_dn*sc+rn2)
    xs.append(sc); ys.append(smeas**2); ws.append(m.sum())
    print(f"{lo:6.0f}-{hi:<7.0f}{m.sum():10d}{smeas:12.4f}{smod:12.4f}{smeas/smod:12.4f}")
xs=np.array(xs); ys=np.array(ys); ws=np.array(ws,float)
Amat=np.vstack([xs,np.ones_like(xs)]).T
sol,*_=np.linalg.lstsq(Amat*np.sqrt(ws)[:,None],ys*np.sqrt(ws),rcond=None)
print(f"\n  free fit  sigma^2 = g*S + c :  g_fit = {sol[0]:.4f} DN/e-   "
      f"(model {g_dn:.4f}, ratio {sol[0]/g_dn:.4f})")
rn_fit=np.sqrt(max(sol[1],0))/sol[0] if sol[0]>0 else float('nan')
print(f"                                  c_fit = {sol[1]:.4f} DN^2 -> RN_e = {rn_fit:.3f} e- "
      f"(model {4.20:.2f})")

print("\n=== D: half-normal check.  Simulate pure Gaussian noise at the model sigma")
print("       through the identical pipeline. ===")
rng=np.random.default_rng(7)
Sref=np.median(a_raw,axis=0)
sigpx=np.sqrt(np.maximum(g_dn*np.maximum(Sref,0)+rn2,1e-6))
sim=Sref[None,:,:]+rng.normal(size=(n,)+Sref.shape)*sigpx[None,:,:]
for d in (1,8):
    Asim=area_mean(sim,d)
    R=(Asim[:-2]+Asim[2:])/2.; SS=np.sqrt(np.maximum(g_dn*np.maximum(R,0)+rn2,1e-6))/d
    z=np.abs(Asim[1:-1]-R)/(SS*np.sqrt(1.5))
    print(f"  simulated pure-Gaussian, d={d:2d}: median|z| {np.median(z):.4f} "
          f"tile|z| {np.median(tile_med(z,max(128//d,1))):.4f}  (expect 0.6745)")
# Poisson version
lam=np.maximum(Sref,0)/g_dn
simp=(rng.poisson(lam[None,:,:].repeat(n,0))*g_dn
      + rng.normal(size=(n,)+Sref.shape)*np.sqrt(rn2))
for d in (1,8):
    Asim=area_mean(simp,d)
    R=(Asim[:-2]+Asim[2:])/2.; SS=np.sqrt(np.maximum(g_dn*np.maximum(R,0)+rn2,1e-6))/d
    z=np.abs(Asim[1:-1]-R)/(SS*np.sqrt(1.5))
    print(f"  simulated Poisson+read,  d={d:2d}: median|z| {np.median(z):.4f} "
          f"tile|z| {np.median(tile_med(z,max(128//d,1))):.4f}  (expect 0.6745)")
