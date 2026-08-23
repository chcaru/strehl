import numpy as np, os, json
ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
OUT = os.path.join(ROOT,"m36-verification","out"); CACHE=os.path.join(OUT,"cache")
out={}
for tag in ("119MSDCF","112MSDCF"):
    foc = np.asarray(np.load(os.path.join(CACHE,f"{tag}_foc.npy"), mmap_mode="r"), np.float32)
    raw = np.asarray(np.load(os.path.join(CACHE,f"{tag}_raw.npy"), mmap_mode="r"), np.float32)
    nd = foc.shape[0]; c = foc[::2]; n=c.shape[0]
    am = c.argmax(0)
    bnd = float(((am<=1)|(am>=n-2)).mean())
    out[tag]=dict(n_dense=nd,n_coarse=n,argmax_p05=int(np.percentile(am,5)),argmax_median=int(np.median(am)),
        argmax_p95=int(np.percentile(am,95)),frac_boundary=bnd,
        median_signal=float(np.median(raw.mean(0))),
        frames_holding_1pct=int((np.bincount(am.ravel(),minlength=n)>0.01*am.size).sum()))
    print(tag, json.dumps(out[tag]))
# coffee-bean for comparison
dense = np.asarray(np.load(os.path.join(ROOT,"m33-subframe-offset","out","cache","dense_focus.npy"), mmap_mode="r"), np.float32)
c = dense[::2]; n=c.shape[0]; am=c.argmax(0)
out["coffee-bean"]=dict(n_dense=105,n_coarse=n,argmax_p05=int(np.percentile(am,5)),argmax_median=int(np.median(am)),
    argmax_p95=int(np.percentile(am,95)),frac_boundary=float(((am<=1)|(am>=n-2)).mean()),
    frames_holding_1pct=int((np.bincount(am.ravel(),minlength=n)>0.01*am.size).sum()))
print("coffee-bean", json.dumps(out["coffee-bean"]))
json.dump(out, open(os.path.join(OUT,"V06b-stack-diagnostics.json"),"w"), indent=1)
