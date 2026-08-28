import numpy as np, sys
sys.path.insert(0,r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-KILLB0")
import bandprobe as bp, edgewidth as ew
la = bp.channels(bp.load(r"C:\dev\strehl-out\V-KILLB0\default\112MSDCF.tiff"))["L"]
sites = ew.find_edges(la)
n_none=n_prof=0; r2s=[]; steps=[]; sigs=[]
for (y,x) in sites:
    f = ew.fit(la[y-ew.HALF:y+ew.HALF, x-ew.HALF:x+ew.HALF])
    if f is None:
        n_none+=1; continue
    r2s.append(f["r2"]); steps.append(f["step"]); sigs.append(f["sig"])
r2s=np.array(r2s); steps=np.array(steps); sigs=np.array(sigs)
print("candidates",len(sites),"fit-None",n_none,"fitted",len(r2s))
for q in (10,25,50,75,90):
    print(f"  p{q}: r2={np.percentile(r2s,q):.4f} step={np.percentile(steps,q):.0f} sigma={np.percentile(sigs,q):.3f}")
print("count r2>=0.985:",(r2s>=0.985).sum()," r2>=0.95:",(r2s>=0.95).sum()," r2>=0.90:",(r2s>=0.90).sum())
print("count step>=1000:",(steps>=1000).sum()," step>=500:",(steps>=500).sum())
print("both r2>=0.95 & step>=800:", ((r2s>=0.95)&(steps>=800)).sum())
print("both r2>=0.98 & step>=800:", ((r2s>=0.98)&(steps>=800)).sum())
print("sigma of those:", np.median(sigs[(r2s>=0.95)&(steps>=800)]) if ((r2s>=0.95)&(steps>=800)).sum() else None)
