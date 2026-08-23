import numpy as np, rawpy, glob, os
from scipy.ndimage import uniform_filter, sobel, median_filter
BLACK=512
def ff(g,R):
    gx=sobel(g,axis=1,mode='reflect')/8.0; gy=sobel(g,axis=0,mode='reflect')/8.0
    return uniform_filter(np.sqrt(gx*gx+gy*gy), 2*R+1)
def mp_am(V,thr=0.04):
    Vs=np.copy(V); Vs[1:-1]=(V[:-2]+2*V[1:-1]+V[2:])/4.0
    mx=Vs.max(0); mn=Vs.min(0); rng=np.maximum(mx-mn,1e-6)
    p=np.zeros_like(Vs,bool)
    p[1:-1]=(Vs[1:-1]>Vs[:-2]+thr*rng)&(Vs[1:-1]>Vs[2:]+thr*rng)
    return p.sum(0)>=2, np.argmax(Vs,0)
CROP=(600,1624,900,1924)
print("=== ATTACK: is coffee-bean's 4.38x a DEPTH effect or an INTENSITY-EDGE effect? ===\n")
fs_all=sorted(glob.glob(os.path.join(r"C:\dev\macro\test\coffee-bean","*.ARW")))
for off in (0,2):
    fs=fs_all[off::5]
    G=[]
    for f in fs:
        with rawpy.imread(f) as rr:
            g=rr.raw_image_visible[0::2,1::2].astype(np.float32)-BLACK
        G.append(g[CROP[0]:CROP[1],CROP[2]:CROP[3]])
    G=np.stack(G)
    V2=np.stack([ff(g,2) for g in G]); V13=np.stack([ff(g,13) for g in G])
    mp,_=mp_am(V2); _,am13=mp_am(V13)
    amr=median_filter(am13.astype(np.float32),5)
    step=np.abs(np.gradient(amr)[0])+np.abs(np.gradient(amr)[1])
    # all-in-focus composite by per-pixel argmax -> its own intensity gradient
    comp=np.take_along_axis(G,am13[None],0)[0]
    gx=sobel(comp,axis=1,mode='reflect')/8.0; gy=sobel(comp,axis=0,mode='reflect')/8.0
    ig=uniform_filter(np.sqrt(gx*gx+gy*gy),5)
    hi=step>=1.0; lo=step<0.25
    print(f"--- subsample offset {off} ({len(fs)} frames) ---")
    print(f"  UNSTRATIFIED: {mp[hi].mean()*100:5.1f}% vs {mp[lo].mean()*100:5.1f}% = {mp[hi].mean()/mp[lo].mean():5.2f}x")
    # does binning on INTENSITY edges alone reproduce it?
    q=np.percentile(ig,[90]); ihi=ig>=q[0]; ilo=ig<np.percentile(ig,50)
    print(f"  intensity-edge binning alone: {mp[ihi].mean()*100:5.1f}% vs {mp[ilo].mean()*100:5.1f}%"
          f" = {mp[ihi].mean()/max(mp[ilo].mean(),1e-9):5.2f}x")
    # STRATIFY: within quintiles of intensity gradient, compare depth-step vs smooth
    edges=np.percentile(ig,[0,20,40,60,80,100]); rs=[]
    print("   stratified by intensity-gradient quintile:")
    for i in range(5):
        m=(ig>=edges[i])&(ig<=edges[i+1])
        h=m&hi; l=m&lo
        if h.sum()<300 or l.sum()<300:
            print(f"     Q{i+1}: bins too small ({h.sum()}/{l.sum()})"); continue
        r=mp[h].mean()/max(mp[l].mean(),1e-9); rs.append(r)
        print(f"     Q{i+1}: {mp[h].mean()*100:5.1f}% vs {mp[l].mean()*100:5.1f}% = {r:5.2f}x  (n={h.sum()}/{l.sum()})")
    if rs: print(f"   POOLED within-stratum enrichment (geometric mean): {np.exp(np.mean(np.log(rs))):5.2f}x")
    print()
