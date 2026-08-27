"""ARM G3 redone: commission ground_iqr against a plant of KNOWN amplitude.
The first attempt blurred white noise at sigma 60 without renormalising, which
collapses its sd ~200x -- the plant was ~254 DN, not 18000 DN.  Normalise."""
import numpy as np, cv2, sys
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW")
from vg_geom import geom

H, W = 2344, 3520
rng = np.random.default_rng(0)
yy, xx = np.mgrid[0:H, 0:W]
disc = ((yy-H//2)**2/(0.30*H)**2 + (xx-W//2)**2/(0.30*H)**2) < 1.0
GND = 40000.0

print("ARM G3  ground texture -> ground_iqr  (dark_ratio must stay ~5)")
print("%10s %12s %12s %12s" % ("plant sd", "as %% of gnd", "ground_iqr", "dark_ratio"))
for rel in (0.0, 0.02, 0.05, 0.10, 0.20, 0.35):
    t = cv2.GaussianBlur(rng.normal(0, 1, (H,W)).astype(np.float32), (0,0), 60)
    t = t/ (t.std() + 1e-12) * (rel*GND)                 # normalise to a KNOWN sd
    L = np.full((H,W), GND, np.float32) + t
    L[disc] = 8000.0
    L += rng.normal(0, 150, (H,W)).astype(np.float32)
    g = geom(np.clip(L, 1, None), scale=1.0)
    if g is None or g.get("bad"):
        print("%10.0f %11.0f%% %12s %12s  REFUSED (%s)" % (rel*GND, 100*rel, "-","-",(g or {}).get("bad","no subject")))
    else:
        print("%10.0f %11.0f%% %12.3f %12.2f" % (rel*GND, 100*rel, g["iqr"], g["dark_ratio"]))
print()
print("reference readings on real masters:  flower-bud-alone-cpl 0.03   lead-1-cpl 0.11")
