import numpy as np, rawpy, glob, os
from scipy.ndimage import uniform_filter, sobel
BLACK=512
def ff(g,R):
    gx=sobel(g,axis=1,mode='reflect')/8.0; gy=sobel(g,axis=0,mode='reflect')/8.0
    return uniform_filter(np.sqrt(gx*gx+gy*gy), 2*R+1)
def planes(stack,crop):
    fs=sorted(glob.glob(os.path.join(stack,"*.ARW")))
    out=[]
    for f in fs:
        with rawpy.imread(f) as rr:
            g=rr.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
        out.append(g[crop[0]:crop[1],crop[2]:crop[3]])
    return np.stack(out)
def multipeak(V,thr=0.04):
    Vs=np.copy(V); Vs[1:-1]=(V[:-2]+2*V[1:-1]+V[2:])/4.0
    mx=Vs.max(0); mn=Vs.min(0); rng=np.maximum(mx-mn,1e-6)
    ispk=np.zeros_like(Vs,bool)
    ispk[1:-1]=(Vs[1:-1]>Vs[:-2]+thr*rng)&(Vs[1:-1]>Vs[2:]+thr*rng)
    return ispk.sum(0), (mx-mn)/np.maximum(mx,1e-6), np.argmax(Vs,0)
CROP=(600,1624,900,1924)
print("=== Does the 27x27 window destroy the bimodality signal? Sweep the focus radius. ===")
print("    NULL = coffee-bubbles (no focus change at all): any multi-peak rate there is NOISE.")
print(f"{'stack':>16} {'R':>3} | {'multi-peak %':>12} {'NULL %':>8} {'excess pp':>10} | {'enrich @ depth step':>20}")
G={}
for name,path in (("109MSDCF",r"C:\dev\macro\test\109MSDCF"),
                  ("coffee-bean",r"C:\dev\macro\test\coffee-bean"),
                  ("NULL-bubbles",r"D:\personal\macro\coffee-bubbles")):
    fs=sorted(glob.glob(os.path.join(path,"*.ARW")))
    if name=="coffee-bean": fs=fs[::5]        # 105 -> 21 frames, keep the sweep, cut the cost
    out=[]
    for f in fs:
        with rawpy.imread(f) as rr:
            g=rr.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
        out.append(g[CROP[0]:CROP[1],CROP[2]:CROP[3]])
    G[name]=np.stack(out)
    print(f"  loaded {name}: {G[name].shape}")
print()
for R in (2,5,13):
    nullrate=None
    for name in ("NULL-bubbles","109MSDCF","coffee-bean"):
        V=np.stack([ff(g,R) for g in G[name]])
        npk,contrast,am=multipeak(V)
        strong=contrast>0.10
        rate=(npk>=2)[strong].mean()*100
        if name=="NULL-bubbles": nullrate=rate; continue
        amf=uniform_filter(am.astype(np.float32),9)
        step=np.abs(np.gradient(amf)[0])+np.abs(np.gradient(amf)[1])
        hi=step>np.percentile(step[strong],90); lo=step<np.percentile(step[strong],50)
        a=(npk>=2)[strong&hi].mean()*100; b=(npk>=2)[strong&lo].mean()*100
        print(f"{name:>16} {R:>3} | {rate:>11.1f}% {nullrate:>7.1f}% {rate-nullrate:>9.1f} | "
              f"{a:>6.1f}% vs {b:>5.1f}% = {a/max(b,1e-6):>4.2f}x")
    print()
