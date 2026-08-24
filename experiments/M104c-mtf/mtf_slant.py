import numpy as np, tifffile, math, sys
sys.path.insert(0,r"C:\dev\strehl-out\VERIFY-M104c")
from mtf import mtf_from_roi
d=r"C:\dev\strehl-out\VERIFY-M104c"
G={k:tifffile.imread(d+"\\fr-%s.tif"%k)[:,:,1].astype(np.float64) for k in ("NOALIGN","REAL","ZOOM")}
base=G["NOALIGN"]; H,W=base.shape; RH,RW=256,160
slant=[]
for y in range(400,H-RH-400,256):
    for x in range(400,W-RW-400,160):
        r=base[y:y+RH,x:x+RW]
        c=abs(r[:,-RW//3:].mean()-r[:,:RW//3].mean())
        if c<2000: continue
        try: rr=mtf_from_roi(r)
        except Exception: continue
        if 2.0<=abs(rr["angle"])<=12.0: slant.append((y,x,c,rr["angle"],rr["mtf50"],rr["mtf_nyq"]))
print("slanted candidates (|angle| 2-12 deg, contrast>2000):", len(slant))
for y,x,c,a,m,nq in slant:
    print("  y=%5d x=%5d contrast=%7.0f angle=%+6.2f MTF50=%.4f MTF@Nyq=%.4f" % (y,x,c,a,m,nq))
print("")
print("plausibility gate: a real edge on this rig should give MTF50 roughly 0.05-0.35 c/px.")
print("Anything at ~0.01 c/px is the 0-degree aliasing artifact, not a measurement.")
good=[s for s in slant if 0.05<=s[4]<=0.35]
print("slanted candidates that are also plausible:", len(good))
if good:
    print("")
    print("=== per-arm MTF50 on plausible slanted edges ===")
    for y,x,c,a,m,nq in good:
        line="y=%5d x=%5d ang=%+5.2f : " % (y,x,a)
        for k in ("NOALIGN","REAL","ZOOM"):
            rr=mtf_from_roi(G[k][y:y+RH,x:x+RW]); line+="%s=%.4f(ang%+5.2f) " % (k,rr["mtf50"],rr["angle"])
        print("  "+line)
else:
    print("")
    print("VERDICT: flat-on-ruler-cpl does NOT support a slanted-edge MTF.")
print("")
print("=== contrast context: dynamic range actually present ===")
print("  green channel p1=%.0f p50=%.0f p99=%.0f max=%.0f (16-bit)" %
      tuple(np.percentile(base,[1,50,99]).tolist()+[base.max()]))
print("  best edge contrast found = 4555 DN = %.1f%% of the p1-p99 range" % (100*4555/(np.percentile(base,99)-np.percentile(base,1))))
