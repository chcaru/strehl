"""POSITIVE CONTROL for the microcontrast instrument.

(a) Confirm the metric moves hard when a known-potent softening is planted.
(b) Translate the measured retention into photographic units: what Gaussian
    blur sigma, applied to the UNCLAMPED arm, reproduces the same retention?
"""
import sys, json
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter
def hp_rms(x,s=1.0): return float(np.sqrt(np.mean((x-gaussian_filter(x,s,mode="reflect"))**2)))
p=sys.argv[1]; target=float(sys.argv[2])
a=tifffile.imread(p); assert a.dtype==np.uint16
g=a[:,:,1].astype(np.float32)[600:1800, 900:2500]   # central 1200x1600 block
base=hp_rms(g)
print("unclamped hp1 RMS = %.2f DN (control block)" % base)
prev=None
for s in (0.05,0.10,0.15,0.20,0.25,0.30,0.40,0.50,0.75,1.00):
    r=100.0*hp_rms(gaussian_filter(g,s,mode="reflect"))/base
    mark=""
    if prev is not None and prev>=target>=r: mark="   <== measured clamp cost lands here"
    print("  blur sigma %.2f px -> retention %6.2f%%%s" % (s,r,mark))
    prev=r
