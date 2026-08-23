import numpy as np, os, json
from scipy.stats import spearmanr
ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
OUT = os.path.join(ROOT, "m36-verification", "out")
G, RN_E = 50/436.8, 4.20
dense = np.asarray(np.load(os.path.join(ROOT,"m33-subframe-offset","out","cache","dense_focus.npy"), mmap_mode="r"), np.float32)
raw = np.asarray(np.load(os.path.join(ROOT,"m32-posterior","out","cache","raw.npy"), mmap_mode="r"), np.float32)
foc = np.ascontiguousarray(dense[::2])
base_d = dense.min(0); tp = np.maximum(dense.max(0)-base_d,1e-6)
td = np.clip(1.0-np.maximum(foc.max(0)-base_d,1e-6)/tp,0,1).ravel(); gm=float(td.mean())
tail = np.concatenate([foc[:6],foc[-6:]],0); d2=tail[2:]-2*tail[1:-1]+tail[:-2]
sf = np.sqrt(np.maximum(d2.var(0),1e-12)/6.0).astype(np.float32)
fmax = foc.max(0)
nacc = ((fmax[None]-foc) <= sf[None]).sum(0).ravel()
print("mean TRUE deficit by acceptance-set size |A|:")
rows=[]
for a in (1,2,3,4,5):
    m = (nacc==a) if a<5 else (nacc>=5)
    lab = f"|A|={a}" if a<5 else "|A|>=5"
    rows.append(dict(A=lab, frac=float(m.mean()), mean_true_def=float(td[m].mean())))
    print(f"  {lab:7s} {m.mean():7.4%} of pixels   mean true deficit {td[m].mean():.5f}  ({td[m].mean()/gm:.2f}x global)")
print(f"  spearman(|A|, true deficit) = {spearmanr(nacc[::7], td[::7]).statistic:+.4f}")
k=int(round(0.05*nacc.size))
i=np.argpartition(nacc.astype(np.float64)+np.random.default_rng(1).uniform(0,1e-9,nacc.size),-k)[-k:]
print(f"  worst-5% lift of |A| itself = {td[i].mean()/gm:.3f}x")
json.dump(dict(rows=rows, spearman_A_vs_truedef=float(spearmanr(nacc[::7], td[::7]).statistic),
               liftA=float(td[i].mean()/gm)), open(os.path.join(OUT,"V05c-acceptance-mechanism.json"),"w"), indent=1)
