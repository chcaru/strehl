import numpy as np, rawpy, glob, os
from scipy.ndimage import median_filter
S=r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
BLACK=512; count=np.load(os.path.join(S,"hotcount.npy")); stable=count>=6
rng=np.random.default_rng(3); ctrl=np.zeros_like(stable)
ctrl.ravel()[rng.choice(stable.size, stable.sum()*10, replace=False)]=True; ctrl&=~stable
print("=== R11 step 4: the fair test -- stratify by local signal level ===")
print("    A hot pixel is invisible on a bright subject and obvious in a shadow.")
print("    Noise model at ISO 160: sigma = sqrt(g*S + (RN*g)^2), g = 160/436.8 = 0.3663 DN/e-, RN 4.20 e-\n")
g=160/436.8; RN=4.20
HS={};CS={};LV={}
for f in sorted(glob.glob(os.path.join(r"C:\dev\macro\test\109MSDCF","*.ARW")))[:6]:
    with rawpy.imread(f) as rr: a=rr.raw_image_visible.astype(np.float32)-BLACK
    e=np.zeros_like(a); lv=np.zeros_like(a)
    for (dy,dx) in ((0,0),(0,1),(1,0),(1,1)):
        pl=a[dy::2,dx::2]; mf=median_filter(pl,3); e[dy::2,dx::2]=pl-mf; lv[dy::2,dx::2]=mf
    for nm,sel,D in (("h",stable,HS),("c",ctrl,CS)):
        D.setdefault('e',[]).append(e[sel]); D.setdefault('l',[]).append(lv[sel])
he=np.concatenate(HS['e']); hl=np.concatenate(HS['l'])
ce=np.concatenate(CS['e']); cl=np.concatenate(CS['l'])
bins=[(-1e9,50),(50,200),(200,1000),(1000,4000),(4000,1e9)]
names=["deep shadow (<50 DN)","shadow (50-200)","midtone (200-1k)","upper mid (1k-4k)","highlight (>4k)"]
print(f"  {'signal band':>22} {'n_hot':>8} {'hot mean':>9} {'ctrl mean':>10} {'EXCESS':>8} {'sigma(S)':>9} {'excess/sigma':>13}")
for (lo,hi),nm in zip(bins,names):
    mh=(hl>=lo)&(hl<hi); mc=(cl>=lo)&(cl<hi)
    if mh.sum()<200: print(f"  {nm:>22} {mh.sum():>8}  -- too few"); continue
    Smid=np.median(hl[mh]); sig=np.sqrt(max(g*Smid,0)+(RN*g)**2)
    ex=he[mh].mean()-ce[mc].mean()
    print(f"  {nm:>22} {mh.sum():>8} {he[mh].mean():>+9.2f} {ce[mc].mean():>+10.2f} {ex:>+8.2f} {sig:>9.2f} {ex/sig:>13.2f}")
print("\n  A defect only matters if EXCESS/sigma is an appreciable fraction of 1.")
