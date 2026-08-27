import numpy as np, tifffile, warnings
from PIL import Image
from scipy.ndimage import uniform_filter
warnings.simplefilter("ignore")
P = r"C:\dev\strehl-out\V-HIGHLIGHT\u-bee-3-cpl.tiff"
N, OY, OX = 1024, 800, 1200
clean = tifffile.imread(P)[OY:OY+N, OX:OX+N, 1].astype(np.float64)
pil   = np.array(Image.open(P))[OY:OY+N, OX:OX+N, 1].astype(np.float64) * 256.0
assert clean.shape == (N,N) and pil.shape == (N,N), "crop ran off frame"
if len(np.unique(clean)) < 1000 or len(np.unique(pil)) > 300:
    raise SystemExit("ANCHOR FAIL: identity case does not show the gap; test void")

hp = lambda a, r: a - uniform_filter(a, r)
ops = [("identity",           lambda a: a),
       ("/65535 -> float",    lambda a: a/65535.0),
       ("3x3 box mean",       lambda a: uniform_filter(a,3)),
       ("downsample 2x mean", lambda a: a.reshape(N//2,2,N//2,2).mean(axis=(1,3))),
       ("high-pass r=201",    lambda a: hp(a,201))]
print("crop %dx%d at (%d,%d)   ORCH's rule: 'thousands' => clean" % (N,N,OY,OX))
print("%-20s %12s %12s   %s" % ("operation applied","clean uq","PIL-x256 uq","verdict on DAMAGED array"))
for nm, f in ops:
    cu, pu = len(np.unique(f(clean))), len(np.unique(f(pil)))
    v = "CAUGHT" if pu <= 300 else ("*** PASSES AS CLEAN ***" if pu >= 1000 else "ambiguous")
    print("%-20s %12d %12d   %s" % (nm, cu, pu, v))

c, p = hp(clean,201), hp(pil,201)
rms = np.sqrt(((p-c)**2).mean())
print("\n--- is the information back after the op that restored the count? ---")
print("clean high-pass sd    : %8.2f DN" % c.std())
print("damaged high-pass sd  : %8.2f DN" % p.std())
print("RMS(damaged - clean)  : %8.2f DN   (quantisation step 256 DN)" % rms)
print("corr(damaged, clean)  : %8.4f" % np.corrcoef(c.ravel(), p.ravel())[0,1])
print("\nORCH's dust: 'a few levels below background', crop spans 12 8-bit levels")
print("  a 3 DN dust feature against %.1f DN injected error -> SNR %.3f  (needs >~3 to see)" % (rms, 3/rms))
