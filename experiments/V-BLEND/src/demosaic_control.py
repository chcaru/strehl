"""Two controls for the rho finding.

C1 (causal): does the DEMOSAIC manufacture the correlation? Measure rho on the
    SAME frame rendered BINNED -- one RGB sample per real 2x2 sensor quad, no
    interpolation at all. If binned reads ~0 and demosaiced reads +0.35, the
    correlation is made by the interpolator, not by the scene.

C2 (reproducibility): how much of a single frame's backdrop residual is
    REPRODUCIBLE scene/fixed pattern rather than temporal noise? Correlate two
    adjacent frames' residuals at the same tiles. Noise is independent between
    exposures; scene and fixed pattern are not.
"""
import numpy as np, tifffile
from noisefloor import tiles, sigma_std, immerkaer
from whiteness import resid, rho_lag1, hf_fraction

def green(p):
    a = tifffile.imread(p); assert a.dtype == np.uint16
    return a[:, :, 1].astype(np.float32)

def coarse(t, ds=8):
    n = t.shape[0]; b = t.shape[1]//ds
    return sigma_std(t.reshape(n, b, ds, b, ds).mean(axis=(2, 4)).astype(np.float32))

def backdrop(t, K=10.0):
    m = t.mean(axis=(1, 2)); c = coarse(t)
    idx = np.where((m >= 16000) & (m < 32000))[0]
    return idx[c[idx] <= np.percentile(c[idx], K)]

L = r"C:\dev\strehl-out\V-BLEND\lin"
print("=== C1: is the +0.35 correlation made by the demosaic? ===")
for lbl, p in (("frame 102 DEMOSAICED (Malvar-He-Cutler)", f"{L}\\flower-bud-alone-cpl-FRAME102.tiff"),
               ("frame 102 BINNED (no interpolation)",     f"{L}\\fb-FRAME102-BINNED.tiff")):
    t = tiles(green(p)); k = backdrop(t); tt = t[k].astype(np.float32)
    print(f"  {lbl:<42} tiles {k.size:5d}  sigma {float(np.median(sigma_std(tt))):8.3f} "
          f" rho {float(np.median(rho_lag1(tt))):8.4f}  HF frac {float(np.median(hf_fraction(tt))):7.4f}")
print("  -> binned is REAL sensor noise with no interpolator between it and the file.")

print()
print("=== C2: how much of the backdrop residual reproduces between exposures? ===")
a = tiles(green(f"{L}\\flower-bud-alone-cpl-FRAME102.tiff"))
b = tiles(green(f"{L}\\fb-FRAME103.tiff"))
k = backdrop(a)
ra, rb = resid(a[k].astype(np.float32)), resid(b[k].astype(np.float32))
ra = ra - ra.mean(axis=(1, 2), keepdims=True); rb = rb - rb.mean(axis=(1, 2), keepdims=True)
num = (ra*rb).mean(axis=(1, 2))
den = np.sqrt((ra*ra).mean(axis=(1, 2))*(rb*rb).mean(axis=(1, 2)))
r = num/np.maximum(den, 1e-12)
print(f"  corr(frame102 residual, frame103 residual) over {k.size} backdrop tiles:")
print(f"    median {float(np.median(r)):+.4f}   p10 {float(np.percentile(r,10)):+.4f}   "
      f"p90 {float(np.percentile(r,90)):+.4f}")
print("  Two adjacent exposures of the SAME defocused backdrop. A residual that is")
print("  scene or fixed pattern reproduces; temporal noise does not.")
