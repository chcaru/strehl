import numpy as np, rawpy, glob, os
from scipy.ndimage import uniform_filter, sobel, median_filter
BLACK=512
def ff(g,R):
    gx=sobel(g,axis=1,mode='reflect')/8.0; gy=sobel(g,axis=0,mode='reflect')/8.0
    return uniform_filter(np.sqrt(gx*gx+gy*gy), 2*R+1)
def multipeak(V,thr=0.04):
    Vs=np.copy(V); Vs[1:-1]=(V[:-2]+2*V[1:-1]+V[2:])/4.0
    mx=Vs.max(0); mn=Vs.min(0); rng=np.maximum(mx-mn,1e-6)
    ispk=np.zeros_like(Vs,bool)
    ispk[1:-1]=(Vs[1:-1]>Vs[:-2]+thr*rng)&(Vs[1:-1]>Vs[2:]+thr*rng)
    return ispk.sum(0)>=2, (mx-mn)/np.maximum(mx,1e-6), np.argmax(Vs,0)
CROP=(600,1624,900,1924)
STACKS=(("109MSDCF",r"C:\dev\macro\test\109MSDCF",1),
        ("119MSDCF",r"C:\dev\macro\test\119MSDCF",1),
        ("coffee-bean",r"C:\dev\macro\test\coffee-bean",5))
print("=== R2 occlusion bimodality, with the circularity broken ===")
print(" - bimodality measured at R=2 (fine, so a two-layer edge is not smeared)")
print(" - depth steps measured from the R=13 argmax, median-filtered 5x5 (independent scale,")
print("   robust to the single-pixel argmax flips that a bimodal pixel itself produces)")
print(" - PLACEBO: permute the frame order. Noise statistics are preserved EXACTLY;")
print("   genuine focus structure is destroyed. Real enrichment must collapse to ~1.0x.\n")
rng0=np.random.default_rng(20260808)
for name,path,sub in STACKS:
    fs=sorted(glob.glob(os.path.join(path,"*.ARW")))[::sub]
    G=[]
    for f in fs:
        with rawpy.imread(f) as rr:
            g=rr.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
        G.append(g[CROP[0]:CROP[1],CROP[2]:CROP[3]])
    G=np.stack(G)
    V2=np.stack([ff(g,2) for g in G]); V13=np.stack([ff(g,13) for g in G])
    _,c13,am13=multipeak(V13)
    amr=median_filter(am13.astype(np.float32),5)
    step=np.abs(np.gradient(amr)[0])+np.abs(np.gradient(amr)[1])
    strong=c13>0.10
    print(f"{name}: {len(fs)} frames   strong pixels {strong.mean()*100:.1f}%   "
          f"depth-step map: {(strong&(step>=1.0)).sum()} at step>=1, {(strong&(step<0.25)).sum()} at step<0.25")
    for label,order in (("REAL      ", np.arange(len(fs))), ("PERMUTED  ", rng0.permutation(len(fs)))):
        mp,_,_=multipeak(V2[order])
        hi=strong&(step>=1.0); lo=strong&(step<0.25)
        if hi.sum()<500 or lo.sum()<500:
            print(f"   {label} bins too small ({hi.sum()}/{lo.sum()}) -- NOT DECIDABLE"); continue
        a=mp[hi].mean()*100; b=mp[lo].mean()*100
        print(f"   {label} multi-peak: {a:5.1f}% at depth steps vs {b:5.1f}% on smooth depth"
              f"   = {a/max(b,1e-9):5.2f}x   (overall {mp[strong].mean()*100:.1f}%)")
    print()
