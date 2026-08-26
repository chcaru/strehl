import sys, numpy as np, tifffile
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-softness\src")
from vlib import grad_rms, grad_rms_norm, hf_fraction

def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: expected uint16, got {a.dtype}"
    return a.astype(np.float64).mean(2)

d = r"C:\dev\strehl-out\V-shrink\full"
print(f"{'subject':<38}{'grad_rms A':>12}{'grad_rms B':>12}{'B/A':>9}"
      f"{'normB/A':>10}{'hfA':>9}{'hfB':>9}{'hfB/A':>9}")
for s in ("bee-1-cpl", "coffee-bean", "flower-bud-with-background-fern-cpl", "109MSDCF"):
    a = load(f"{d}\\{s}-A.tif"); b = load(f"{d}\\{s}-B.tif")
    ga, gb = grad_rms(a), grad_rms(b)
    na, nb = grad_rms_norm(a), grad_rms_norm(b)
    h, w = a.shape
    y0, x0 = (h - 4096) // 2, (w - 4096) // 2
    ca = a[y0:y0+4096, x0:x0+4096]; cb = b[y0:y0+4096, x0:x0+4096]
    ha, hb = hf_fraction(ca), hf_fraction(cb)
    print(f"{s:<38}{ga:12.1f}{gb:12.1f}{gb/ga:9.4f}{nb/na:10.4f}"
          f"{ha:9.5f}{hb:9.5f}{hb/ha:9.4f}")
