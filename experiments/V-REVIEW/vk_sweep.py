"""Two sweeps that decide the attribution.

SWEEP 1 -- ROUND TRIP vs k. What does a fit_to_cover round trip at each measured
k cost, in band-0 FLAT (the band BOTH lanes scored, 0.30-0.35 lies inside
0.25-0.50) and in band-1 EDGE (the only acuity bar)? The differential between
two arms is what could bias a comparison, not the absolute cost.

SWEEP 2 -- PURE MAGNIFICATION. A round trip is geometrically neutral. A genuine
magnification difference is not. Sweep it and find which magnification produces
the coarsest-EDGE null failures the two lanes' comparisons actually showed
(113MSDCF 0.9866, bee-3-cpl 1.0213), to test whether a scale difference can
explain them at all.
"""
import subprocess, sys, os, re
import numpy as np, tifffile
from scipy.ndimage import zoom

SRC = r"C:\dev\strehl-out\V-DILUTE\runs\A_n63_default.tif"
OUT = r"C:\dev\strehl-out\V-REVIEW\sweep"
MS  = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\contrast_ms.py"
os.makedirs(OUT, exist_ok=True)

a = tifffile.imread(SRC)
f = a.astype(np.float32)
G = re.compile(r"GRAIN WIN.*?:\s*([0-9.]+)")
A_ = re.compile(r"ACUITY COST.*?:\s*([0-9.]+)")
N_ = re.compile(r"INSTRUMENT NULL.*?:\s*([0-9.]+)")

def fit(x, shape):
    y = np.zeros(shape, dtype=x.dtype)
    h = min(x.shape[0], shape[0]); w = min(x.shape[1], shape[1])
    y[:h, :w] = x[:h, :w]
    return y

def score(arr, tag):
    p = os.path.join(OUT, tag + ".tif")
    tifffile.imwrite(p, fit(np.clip(arr, 0, 65535), a.shape).astype(np.uint16))
    r = subprocess.run([sys.executable, MS, SRC, p], capture_output=True, text=True)
    os.remove(p)
    t = r.stdout
    try:
        return float(G.search(t).group(1)), float(A_.search(t).group(1)), float(N_.search(t).group(1))
    except AttributeError:
        print(r.stdout[-400:], r.stderr[-400:]); raise

print("SWEEP 1 -- fit_to_cover round trip: downscale by k, upscale by 1/k")
print(f"{'k':>8} {'1/k upsample':>13} {'band0 FLAT':>11} {'band1 EDGE':>11} {'NULL':>8} {'null ok':>8}")
r1 = {}
for k in (0.9021, 0.9198, 0.9208, 0.9321, 0.9359, 0.9595, 0.9870):
    s = zoom(f, (k, k, 1), order=3)
    b = zoom(s, (a.shape[0] / s.shape[0], a.shape[1] / s.shape[1], 1), order=3)
    g, ac, nu = score(b, f"rt{int(k*10000)}")
    r1[k] = (g, ac, nu)
    print(f"{k:8.4f} {100*(1/k-1):12.2f}% {g:11.4f} {ac:11.4f} {nu:8.4f} "
          f"{'yes' if abs(nu-1) <= 0.005 else 'NO':>8}")

print()
print("  DIFFERENTIAL between the two arms each lane compared:")
print(f"    bee-3-cpl  N=33 k=0.9198 vs N=63 k=0.9208 ->"
      f"  band0 FLAT {abs(r1[0.9198][0]-r1[0.9208][0]):.4f}"
      f"   band1 EDGE {abs(r1[0.9198][1]-r1[0.9208][1]):.4f}")

print()
print("SWEEP 2 -- pure magnification (a real scale difference, not a round trip)")
print(f"{'mag':>8} {'band0 FLAT':>11} {'band1 EDGE':>11} {'NULL':>8} {'null ok':>8}")
for m in (1.0011, 1.005, 1.0134, 1.0213, 1.04):
    s = zoom(f, (m, m, 1), order=3)
    g, ac, nu = score(s, f"mag{int(m*10000)}")
    print(f"{m:8.4f} {g:11.4f} {ac:11.4f} {nu:8.4f} "
          f"{'yes' if abs(nu-1) <= 0.005 else 'NO':>8}")
