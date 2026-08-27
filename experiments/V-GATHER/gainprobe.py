"""How much does a PURE EXPOSURE GAIN move orch_sharp1to1's statistic on real
pixels? The masters carry an auto-exposure gain of 0.79x to 13.6x that the
rawpy denominator never sees, and the tool's own provenance says the file is
"sRGB, TONE CURVE APPLIED -- DO NOT MEASURE NUMERICALLY".
"""
import os, sys, glob, numpy as np, rawpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import orig_detail

def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1/2.4) - 0.055)

arw = sorted(glob.glob(r"D:\personal\macro\coffee-bubbles\*.ARW"))
with rawpy.imread(arw[9]) as r:
    lin = r.postprocess(gamma=(1,1), no_auto_bright=True, use_camera_wb=True,
                        output_bps=16).astype(np.float64) / 65535.0
y = 0.2126*lin[...,0] + 0.7152*lin[...,1] + 0.0722*lin[...,2]
c = y[2000:2560, 3000:3560]
print("one real crop, camera-linear, then ONE multiply in linear light before the sRGB curve")
print("%10s %8s %14s %10s" % ("stops", "gain", "orig detail", "vs +0.00"))
b = None
for st in (-0.34, 0.0, 0.5, 1.0, 1.5, 1.95, 2.27, 2.60, 3.19, 3.76):
    g = 2.0 ** st
    d = orig_detail(srgb(c * g) * 65535.0)
    if st == 0.0: b = d
    print("%10.2f %8.3f %14.2f %10s" % (st, g, d, "-" if b is None else "%.3fx" % (d/b)))
print()
print("the corpus spans -0.34 to +3.76 stops and the source frames get NONE of it")
