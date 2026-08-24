import numpy as np, tifffile, math, sys
sys.path.insert(0,r"C:\dev\strehl-out\VERIFY-M104c")
from mtf import mtf_from_roi
d=r"C:\dev\strehl-out\VERIFY-M104c"
base=tifffile.imread(d+"\\fr-NOALIGN.tif")[:,:,1].astype(np.float64)
H,W=base.shape
RH,RW=256,160
def scan(img,tag):
    h,w=img.shape; out=[]
    for y in range(400, h-RH-400, 256):
        for x in range(400, w-RW-400, 160):
            r=img[y:y+RH, x:x+RW]
            c=abs(r[:,-RW//3:].mean()-r[:,:RW//3].mean())
            if c<2000: continue
            try: rr=mtf_from_roi(r)
            except Exception: continue
            out.append((c,y,x,rr["angle"],rr["mtf50"]))
    out.sort(reverse=True)
    print("[%s] candidates=%d" % (tag,len(out)))
    angs=np.array([o[3] for o in out])
    if len(angs):
        print("    fitted angle: min=%+.2f max=%+.2f median=%+.2f  |ang|<1deg: %d/%d  |ang| in 2-12: %d"
              % (angs.min(),angs.max(),np.median(angs),(np.abs(angs)<1).sum(),len(angs),((np.abs(angs)>=2)&(np.abs(angs)<=12)).sum()))
        print("    top 10 by contrast:")
        for c,y,x,a,m in out[:10]:
            print("      y=%5d x=%5d contrast=%7.0f angle=%+7.3f MTF50=%.4f" % (y,x,c,a,m))
    return out
print("=== A. as-rendered (near-VERTICAL edges) ===")
scan(base,"vertical")
print("")
print("=== B. TRANSPOSED (catches near-HORIZONTAL edges) ===")
scan(np.ascontiguousarray(base.T),"horizontal")
print("")
print("=== C. instrument liveness on THIS data path: synthetic edge pasted into a real crop ===")
sys.path.insert(0,d); from mtf import synth_edge
sy=synth_edge(256,160,1.2,angle_deg=5.0,lo=3000,hi=30000)
r=mtf_from_roi(sy)
print("    synthetic sigma=1.2 in real DN range: angle=%+.2f MTF50=%.4f (analytic %.4f)"
      % (r["angle"], r["mtf50"], math.sqrt(math.log(2)/(2*math.pi**2))/1.2))
