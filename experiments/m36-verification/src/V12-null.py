import numpy as np, json, os
OUT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\m36-verification\out"
def ent_perp(f, T):
    z = (f - f.max(0)) / np.maximum(T, 1e-12)[None, :]
    p = np.exp(np.clip(z, -700, 0)); p /= p.sum(0)
    h = -(p*np.log(np.maximum(p, 1e-300))).sum(0)
    return h/np.log(f.shape[0]), np.exp(h)
res={}
print("independent Gaussian-softmax null, T=1, 200000 trials, 5 seeds")
for n in (53,27,18,14,9):
    es=[];ps=[]
    for s in (101,202,303,404,505):
        r=np.random.default_rng(s)
        f=r.standard_normal((n,200000))
        e,pp=ent_perp(f,np.ones(200000))
        es.append(float(np.median(e))); ps.append(float(np.median(pp)/n))
    res[f"n{n}"]=dict(entropy_median=float(np.mean(es)), entropy_sd=float(np.std(es)),
                      perp_over_n=float(np.mean(ps)))
    print(f"  n={n:3d}  H/log n = {np.mean(es):.6f} +- {np.std(es):.6f}   perp/n = {np.mean(ps):.4f}")
# n=9 sub-sampled from 53 the way DECIM does it -- does using a SUBSET of a 53-draw matter?
r=np.random.default_rng(9999)
f53=r.standard_normal((53,200000))
for d in (1,2,3,4,6):
    idx=list(range(0,53,d)); f=f53[idx]
    e,pp=ent_perp(f,np.ones(200000))
    print(f"  subset d={d} n={len(idx):3d}  H/log n = {float(np.median(e)):.6f}")
json.dump(res, open(os.path.join(OUT,"V12-null.json"),"w"), indent=1)
