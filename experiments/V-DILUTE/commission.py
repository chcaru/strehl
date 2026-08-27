"""V-DILUTE commissioning: null arm and potency arm, on DECODED ARRAYS.

Rule 5: a file hash is not a pixel gauge. Everything here compares numpy arrays.
"""
import sys
import numpy as np
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-DILUTE")
import vd_metrics as vd

R = r"C:\dev\strehl-out\V-DILUTE\runs"

a = vd.read_rgb(rf"{R}\A_n22_default.tif")
b = vd.read_rgb(rf"{R}\X_n22_default_rep.tif")
c = vd.read_rgb(rf"{R}\X_n22_e4.tif")

print(f"shapes: {a.shape} {b.shape} {c.shape}")
print()
print("NULL ARM  identical flags twice, decoded arrays:")
print(f"  array_equal            : {np.array_equal(a, b)}")
print(f"  samples differing      : {int((a != b).sum())} of {a.size}")
print(f"  max |delta|            : {int(np.abs(a.astype(np.int64) - b.astype(np.int64)).max())}")
print()
d = (a != c)
print("POTENCY ARM  --pyramid-exponent 4.0 vs default (ORCH: expect 90.98% moved):")
print(f"  samples differing      : {int(d.sum())} of {a.size} = {100.0*d.mean():.2f}%")
print(f"  max |delta| (DN)       : {int(np.abs(a.astype(np.int64) - c.astype(np.int64)).max())}")
print()

# The analytic N-dependent bias of the rank statistic, pre-registered.
print("ANALYTIC NULL of the confidence rank (a merge that averages IDENTICALLY):")
for n in (22, 33, 63, 105, 150, 299):
    print(f"  N={n:3d}  E[v] = {vd.null_confidence(n):7.1f} milli-units")
