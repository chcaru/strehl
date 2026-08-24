import numpy as np, tifffile, math, sys
sys.path.insert(0,r"C:\dev\strehl-out\VERIFY-M104c")
from mtf import mtf_from_roi
d=r"C:\dev\strehl-out\VERIFY-M104c"
G={k:tifffile.imread(d+"\\fr-%s.tif"%k)[:,:,1].astype(np.float64) for k in ("NOALIGN","REAL","ZOOM")}
base=G["NOALIGN"]; H,W=base.shape
RH,RW=256,160
cands=[]
for y in range(400, H-RH-400, 256):
    for x in range(400, W-RW-400, 160):
        r=base[y:y+RH, x:x+RW]
        left=r[:, :RW//3].mean(); right=r[:, -RW//3:].mean()
        contrast=abs(right-left)
        mid=r[:, RW//3:-RW//3]
        if contrast < 2000: continue
        cands.append((contrast, y, x))
cands.sort(reverse=True)
print("candidate ROIs with contrast > 2000 DN:", len(cands))
accepted=[]
for contrast,y,x in cands[:60]:
    try: r=mtf_from_roi(base[y:y+RH, x:x+RW])
    except Exception: continue
    ang=abs(r["angle"])
    if not (2.0 <= ang <= 12.0): continue
    if not np.isfinite(r["mtf50"]): continue
    accepted.append((y,x,contrast,r["angle"],r["mtf50"]))
print("accepted (angle 2-12 deg, finite MTF50):", len(accepted))
for y,x,c,a,m in accepted[:8]:
    print("   y=%5d x=%5d contrast=%7.0f angle=%+6.2f deg MTF50=%.4f c/px" % (y,x,c,a,m))
if not accepted:
    print("NO USABLE EDGE FOUND -> flat-on-ruler-cpl does not support a slanted-edge MTF at this ROI size")
    sys.exit(0)
print("")
print("=== MTF50 per arm on the SAME ROI (top 5 accepted edges) ===")
print("%-22s %8s %8s %8s   %8s %8s" % ("ROI","NOALIGN","REAL","ZOOM","ang_REAL","ang_NOAL"))
rows=[]
for y,x,c,a,m in accepted[:5]:
    vals={}
    for k in ("NOALIGN","REAL","ZOOM"):
        rr=mtf_from_roi(G[k][y:y+RH, x:x+RW]); vals[k]=(rr["mtf50"], rr["angle"], rr["mtf_nyq"])
    rows.append((y,x,vals))
    print("y=%5d x=%5d      %8.4f %8.4f %8.4f   %+8.2f %+8.2f" %
          (y,x,vals["NOALIGN"][0],vals["REAL"][0],vals["ZOOM"][0],vals["REAL"][1],vals["NOALIGN"][1]))
med=lambda k: float(np.median([v[k][0] for _,_,v in rows]))
n,r_,z_=med("NOALIGN"),med("REAL"),med("ZOOM")
K=0.9935   # FOV scale applied to REAL and ZOOM only; NOALIGN is unzoomed
print("")
print("median MTF50  NOALIGN=%.5f  REAL=%.5f  ZOOM=%.5f  (cycles/px, raw)" % (n,r_,z_))
print("magnification correction: REAL/ZOOM are zoomed by 1/%.4f, so compare against NOALIGN*%.4f = %.5f" % (K,K,n*K))
print("")
print("registration gain  REAL vs ZOOM   = %+.2f%%   (same FOV, no correction needed)" % (100*(r_-z_)/z_))
print("resample+FOV cost  ZOOM vs NOALIGN= %+.2f%%   (magnification-corrected)" % (100*(z_-n*K)/(n*K)))
print("net                REAL vs NOALIGN= %+.2f%%   (magnification-corrected)" % (100*(r_-n*K)/(n*K)))
print("median MTF@Nyquist NOALIGN=%.4f REAL=%.4f ZOOM=%.4f" %
      (np.median([v["NOALIGN"][2] for _,_,v in rows]), np.median([v["REAL"][2] for _,_,v in rows]), np.median([v["ZOOM"][2] for _,_,v in rows])))
