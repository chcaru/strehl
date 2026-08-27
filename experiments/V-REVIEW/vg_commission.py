"""Commission the geometry statistic in BOTH directions, on NON-degenerate input.
The first harness used flat two-valued fields; that is the one histogram Otsu
handles pathologically, so it tested the corner rather than the regime."""
import numpy as np, cv2, sys
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW")
from vg_geom import geom

H, W = 2344, 3520
rng = np.random.default_rng(0)
yy, xx = np.mgrid[0:H, 0:W]
disc = ((yy-H//2)**2/(0.30*H)**2 + (xx-W//2)**2/(0.30*H)**2) < 1.0

def field(ground, subject, texture=0.0):
    L = np.full((H,W), float(ground), np.float32)
    if texture:
        L += cv2.GaussianBlur(rng.normal(0, texture, (H,W)).astype(np.float32), (0,0), 60)*3.0
    L[disc] = subject
    return L + rng.normal(0, 150, (H,W)).astype(np.float32)   # sensor-like noise

def show(tag, L, expect):
    g = geom(L, scale=1.0)
    if g is None or g.get("bad"):
        print("%-36s  REFUSED (%s)   [expect %s]" % (tag, (g or {}).get("bad","no subject"), expect)); return None
    print("%-36s  dark_ratio %6.2f   ground_iqr %5.2f   subj %4.1f%%   [expect %s]"
          % (tag, g["dark_ratio"], g["iqr"], 100*g["frac"], expect))
    return g

print("== boundary ==")
L = np.full((H,W), 40000.0, np.float32); L[disc] = 8000.0        # exactly two values
show("G0 degenerate two-valued field", L, "dark_ratio 5.0")

print("\n== direction: must score HIGH ==")
show("G1 dark disc / flat bright ground", field(40000, 8000), "dark_ratio ~5")

print("\n== direction: must NOT score high ==")
show("G2 low-contrast subject", field(40000, 34000), "dark_ratio ~1.2")
show("G4 bright subj / dark ground (inv)", field(8000, 40000), "not dark-on-bright")
show("G5 flat field, no subject", field(30000, 30000), "REFUSE or subj~0")

print("\n== ground-coherence arm: iqr MUST rise, dark_ratio may not ==")
show("G3 dark disc / textured ground", field(40000, 8000, texture=18000), "iqr >> 0.03")

print("\n== DENOMINATOR arm: perturb the term the ratio divides BY ==")
for gnd in (20000, 30000, 40000, 50000):
    g = show("G6 ground %5d DN" % gnd, field(gnd, 8000), "ratio tracks ground/8000")
    if g: print("%-36s  predicted %.2f  measured %.2f  err %+.1f%%"
                % ("", gnd/8000.0, g["dark_ratio"], 100*(g["dark_ratio"]/(gnd/8000.0)-1)))
