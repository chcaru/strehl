"""M36 V13: does M32's arm-S / arm-N conclusion survive on the focus measure the
rest of the project uses?  M32 used a frame-smoothed volume (V11).  Recompute
both arms on both volumes with my own pixel sample and my own seeds."""
import numpy as np, os, json, time
from scipy.ndimage import sobel, uniform_filter
ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
OUT = os.path.join(ROOT, "m36-verification", "out")
G, RN_E, R = 50/436.8, 4.20, 2
rng = np.random.default_rng(511)

def ent_perp(f, T):
    z = (f-f.max(0))/np.maximum(T, 1e-12)[None, :]
    p = np.exp(np.clip(z, -700, 0)); p /= p.sum(0)
    h = -(p*np.log(np.maximum(p, 1e-300))).sum(0)
    return h/np.log(f.shape[0]), np.exp(h)

raw = np.asarray(np.load(os.path.join(ROOT,"m32-posterior","out","cache","raw.npy"), mmap_mode="r"), np.float32)
sigma = np.sqrt(G*np.clip(raw,0,None)+(RN_E*G)**2).astype(np.float32)
def f3(c):
    gx=sobel(c,axis=2,mode="nearest"); gy=sobel(c,axis=1,mode="nearest")
    return uniform_filter(np.hypot(gx,gy), size=(1,5,5), mode="nearest")
def f2(c):
    o=np.empty_like(c)
    for i in range(c.shape[0]):
        gx=sobel(c[i],axis=1,mode="nearest"); gy=sobel(c[i],axis=0,mode="nearest")
        o[i]=uniform_filter(np.hypot(gx,gy), size=5, mode="nearest")
    return o
mean_img = raw.mean(0)
lv = uniform_filter(mean_img**2,5)-uniform_filter(mean_img,5)**2
tex = np.sqrt(np.maximum(lv,0)); b=8
inner=np.zeros(tex.shape,bool); inner[b:-b,b:-b]=True
edges=np.percentile(tex[inner],[0,20,40,60,80,95])
idxs=[]
for i,e0 in enumerate(edges):
    e1 = edges[i+1] if i+1<len(edges) else tex.max()+1
    yy,xx=np.nonzero(inner&(tex>=e0)&(tex<e1))
    k=rng.choice(yy.size,6000,replace=False); idxs.append((yy[k],xx[k]))
MC=12; res={}
for tag,ff in (("focus3d_M32_as_run",f3),("focus2d_M27_M33_M34",f2)):
    t0=time.time(); F=ff(raw)
    s1=[np.zeros((53,6000)) for _ in idxs]; s2=[np.zeros((53,6000)) for _ in idxs]
    for _ in range(MC):
        Fz=ff(raw+rng.standard_normal(raw.shape,np.float32)*sigma)
        for j,ix in enumerate(idxs):
            z=Fz[:,ix[0],ix[1]].astype(np.float64); s1[j]+=z; s2[j]+=z*z
    rows={}
    for j,ix in enumerate(idxs):
        T=np.sqrt(np.maximum(s2[j]/MC-(s1[j]/MC)**2,0)).mean(0)
        f=F[:,ix[0],ix[1]].astype(np.float64)
        eN,ppN=ent_perp(f,T); eS,ppS=ent_perp(f,f.std(0))
        rows[f"bin{j}"]=dict(texture_dn=float(np.median(tex[ix])), signal_dn=float(np.median(mean_img[ix])),
            peak_over_T_mc=float(np.median((f.max(0)-np.median(f,0))/T)),
            arm_N_entropy=float(np.median(eN)), arm_N_perplexity=float(np.median(ppN)),
            arm_S_entropy=float(np.median(eS)), arm_S_perplexity=float(np.median(ppS)),
            frac_perp_under_1p05=float((ppN<1.05).mean()))
        r=rows[f"bin{j}"]
        print(f"  {tag:20s} bin{j} tex {r['texture_dn']:6.1f} sig {r['signal_dn']:7.0f}"
              f"  peak/T {r['peak_over_T_mc']:7.1f}  armN_perp {r['arm_N_perplexity']:.6f}"
              f"  armS_H {r['arm_S_entropy']:.4f}  frac<1.05 {r['frac_perp_under_1p05']:.4f}")
    res[tag]=rows; print(f"    [{time.time()-t0:.0f}s]")
for tag in res:
    v=[res[tag][f"bin{j}"]["arm_S_entropy"] for j in range(6)]
    ev=[res[tag][f"bin{j}"]["signal_dn"] for j in range(6)]
    print(f"\n  {tag}: arm S {v[0]:.4f} -> {v[-1]:.4f} (min {min(v):.4f} at bin{v.index(min(v))}),"
          f" span {max(v)-min(v):.4f}, signal range {max(ev)/min(ev):.2f}x, monotone={v==sorted(v) or v==sorted(v,reverse=True)}")
json.dump(res, open(os.path.join(OUT,"V13-arms.json"),"w"), indent=1)
print("wrote V13-arms.json")
