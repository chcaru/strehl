import sys, time, numpy as np, tifffile
sys.path.insert(0, r"C:\dev\strehl-out\BUILD-RESAMP")
import slanted_edge as se
g = tifffile.imread(sys.argv[1])[:,:,1].astype(np.float64)
t=time.time()
s = se.find_edges(g, stride=int(sys.argv[2]) if len(sys.argv)>2 else 96, border=128)
print("sites", len(s), f"in {time.time()-t:.0f} s")
print("STATS", se.STATS)
if se.ANGLES:
    print("fitted angle deg pct", np.round(np.percentile(se.ANGLES,[1,5,25,50,75,95,99]),3))
if s:
    for k in ("mtf50","angle","contrast","rough"):
        v = np.array([x[k] for x in s])
        print(f"  {k:9s}", np.round(np.percentile(v,[5,25,50,75,95]),4))
    print("  horizontal-edge sites:", sum(1 for x in s if x["t"]))
