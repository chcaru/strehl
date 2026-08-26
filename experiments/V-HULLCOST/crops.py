"""1:1 crops of both arms at the site where the loss statistic is largest.

No resampling. IDENTICAL display transform on both arms (fixed gain taken once
from the CLAMPED arm, then gamma 2.2) -- a monotone curve, used ONLY for
looking, never for a number.
"""
import sys, json
import numpy as np, tifffile
from PIL import Image
from scipy.ndimage import gaussian_filter

def hp_rms(x, s=1.0):
    return float(np.sqrt(np.mean((x - gaussian_filter(x, s, mode="reflect"))**2)))

subj, cpath, upath, S = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
C = tifffile.imread(cpath); U = tifffile.imread(upath)
assert C.dtype == np.uint16 and U.dtype == np.uint16
gc = C[:,:,1].astype(np.float32); gu = U[:,:,1].astype(np.float32)
H, W = gc.shape

# locate the tile with the largest ABSOLUTE hp drop (worst case for the clamp)
best = None
for y in range(0, H-S, S//2):
    for x in range(0, W-S, S//2):
        ru = hp_rms(gu[y:y+S, x:x+S])
        if ru < 1e-6: continue
        drop = ru - hp_rms(gc[y:y+S, x:x+S])
        if best is None or drop > best[0]:
            best = (drop, y, x, ru)
drop, Y, X, ru = best
rep = {"subject": subj, "crop": [X, Y, S, S], "hp_unclamped_DN": ru,
       "hp_clamped_DN": ru-drop, "tile_retention_pct": 100.0*(ru-drop)/ru,
       "tile_max_abs_diff_DN": float(np.abs(gu[Y:Y+S,X:X+S]-gc[Y:Y+S,X:X+S]).max())}

# fixed display transform from the CLAMPED arm, applied identically to both
k = 1.0/max(float(np.percentile(C[Y:Y+S,X:X+S].astype(np.float32), 99.5)), 1.0)
rep["display_gain"] = k*65535.0
def show(A):
    v = np.clip(A[Y:Y+S, X:X+S].astype(np.float32)*k, 0, 1)**(1/2.2)
    return Image.fromarray((v*255+0.5).astype(np.uint8), "RGB")
a, b = show(C), show(U)
a.save(r"C:\dev\strehl-out\V-HULLCOST\crops\%s-clamped.png" % subj)
b.save(r"C:\dev\strehl-out\V-HULLCOST\crops\%s-unclamped.png" % subj)
# side by side with a 8px divider
sbs = Image.new("RGB", (S*2+8, S), (255,0,0)); sbs.paste(a,(0,0)); sbs.paste(b,(S+8,0))
sbs.save(r"C:\dev\strehl-out\V-HULLCOST\crops\%s-SBS.png" % subj)
# amplified difference map (x8, mid-grey = 0)
d = (gu[Y:Y+S,X:X+S]-gc[Y:Y+S,X:X+S])
dv = np.clip(128 + d*8.0/256.0, 0, 255).astype(np.uint8)
Image.fromarray(dv, "L").save(r"C:\dev\strehl-out\V-HULLCOST\crops\%s-DIFFx8.png" % subj)
print(json.dumps(rep, indent=1))
