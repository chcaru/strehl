"""1:1 crops from BUILD-HULL's own 4688x7032 pair at the worst band-limited
loss site. ONE shared display curve, derived once from the CLAMPED arm and
applied identically to both (the per-arm-curve mistake ORCH logged)."""
import sys, json
import numpy as np, tifffile
from PIL import Image
from scipy.ndimage import gaussian_filter
def hp_rms(x,s=1.0): return float(np.sqrt(np.mean((x-gaussian_filter(x,s,mode="reflect"))**2)))
subj, cp, up, S = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
C = tifffile.imread(cp); U = tifffile.imread(up)
assert C.dtype==np.uint16 and U.dtype==np.uint16
gc = C[:,:,1].astype(np.float32); gu = U[:,:,1].astype(np.float32)
H,W = gc.shape
best=None
for y in range(0,H-S,S):
    for x in range(0,W-S,S):
        ru=hp_rms(gu[y:y+S,x:x+S])
        if ru<1e-6: continue
        drop=ru-hp_rms(gc[y:y+S,x:x+S])
        if best is None or drop>best[0]: best=(drop,y,x,ru)
drop,Y,X,ru=best
print(json.dumps({"subject":subj,"crop":[X,Y,S,S],"hp_unclamped_DN":ru,
  "hp_clamped_DN":ru-drop,"tile_retention_pct":100*(ru-drop)/ru,
  "max_abs_diff_DN":float(np.abs(gu[Y:Y+S,X:X+S]-gc[Y:Y+S,X:X+S]).max()),
  "mean_signed_D_DN":float((gu[Y:Y+S,X:X+S]-gc[Y:Y+S,X:X+S]).mean())}, indent=1))
k = 1.0/max(float(np.percentile(C[Y:Y+S,X:X+S].astype(np.float32),99.5)),1.0)
def show(A):
    v=np.clip(A[Y:Y+S,X:X+S].astype(np.float32)*k,0,1)**(1/2.2)
    return Image.fromarray((v*255+0.5).astype(np.uint8),"RGB")
a,b=show(C),show(U)
sbs=Image.new("RGB",(S*2+8,S),(255,0,0)); sbs.paste(a,(0,0)); sbs.paste(b,(S+8,0))
sbs.save(r"C:\dev\strehl-out\V-HULLCOST\crops\%s-BH-SBS.png"%subj)
