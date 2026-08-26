"""True per-pixel out-of-hull rate, not the exact-zero proxy.

Where the clamp bound from BELOW, the clamped output value IS the hull floor
min_k. So {clamped - unclamped >= tol} is exactly the set of pixels where the
unclamped reconstruction emitted a value BELOW the minimum any input frame
observed. Likewise {unclamped - clamped >= tol} is the above-hull set.
Green plane, linear camera-native DN. tol = 8 DN (~1/8000 of full scale)."""
import sys, json
import numpy as np, tifffile
def g(p):
    a=tifffile.imread(p); assert a.dtype==np.uint16; return a[:,:,1].astype(np.float32)
print("%-22s %10s %10s %10s %12s %12s" % ("subject","below%","above%","total%","exact0(G)","worst_below"))
for i in range(1,len(sys.argv),3):
    t,cp,up = sys.argv[i],sys.argv[i+1],sys.argv[i+2]
    c,u = g(cp),g(up); n=c.size
    below = (c-u)>=8; above=(u-c)>=8
    print("%-22s %9.2f%% %9.2f%% %9.2f%% %12d %11.0f DN" % (
        t, 100*below.sum()/n, 100*above.sum()/n, 100*(below.sum()+above.sum())/n,
        int((u==0).sum()), float((c-u).max())))
