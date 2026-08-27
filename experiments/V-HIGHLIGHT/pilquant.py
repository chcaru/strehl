import numpy as np, tifffile, warnings
from PIL import Image
warnings.simplefilter("ignore")
P = r"C:\dev\strehl-out\V-HIGHLIGHT\u-bee-3-cpl.tiff"

clean = tifffile.imread(P)
pil   = np.array(Image.open(P))
if clean.dtype != np.uint16: raise SystemExit("ANCHOR FAIL: tifffile did not give uint16")
if pil.dtype   != np.uint8:  raise SystemExit("ANCHOR FAIL: PIL did not give uint8 -- hazard absent, test void")
x256  = pil.astype(np.float64) * 256.0

print("file            :", P.split("\\")[-1], clean.shape)
print("%-10s %8s %10s %8s %8s" % ("reader","dtype","distinct","min","max"))
for nm, a in (("tifffile", clean), ("PIL", pil), ("PIL x256", x256)):
    print("%-10s %8s %10d %8.0f %8.0f" % (nm, str(a.dtype), len(np.unique(a)), a.min(), a.max()))

print()
print("--- ORCH's two sub-claims, checked ---")
se = abs(x256.max() - clean.max()) / clean.max() * 100
print("scale restored to        : %.2f%% of true max   (ORCH: 'within 0.7%%')" % se)
print("distinct preserved by x256: %s  (%d -> %d)" % (len(np.unique(x256)) == len(np.unique(pil)), len(np.unique(pil)), len(np.unique(x256))))
print("every x256 value mult of 256: %s" % bool(np.all(np.mod(x256, 256) == 0)))
print("floor destroyed          : clean min %d -> PIL min %d" % (clean.min(), pil.min()))
u = np.unique(x256)
print("quantisation step        : %.0f DN  => true DN known only to +/-%.0f" % (np.diff(u).min(), np.diff(u).min()/2))
print("tonal resolution lost    : %.0fx" % (len(np.unique(clean)) / len(np.unique(pil))))
