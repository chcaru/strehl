"""Probe the inputs. Independent of the V-NOISE lane's code -- tifffile only.
Establishes shape, dtype, range and file identity before any statistic exists.
"""
import os, hashlib
import numpy as np, tifffile

F = {
 "strehl-A":  r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff",
 "strehl-B":  r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff",
 "strehl-full": r"C:\dev\strehl-out\V-H2H2\lin\113-full-g1.tiff",
 "enfuse-A":  r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif",
 "enfuse-B":  r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-B.tif",
 "fs15-A":    r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif",
 "fs15-B":    r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-B.tif",
}
print("%-12s %-22s %-9s %12s %12s %10s" % ("arm", "shape", "dtype", "min", "max", "mean"))
for k, p in F.items():
    a = tifffile.imread(p)
    print("%-12s %-22s %-9s %12.5g %12.5g %10.5g"
          % (k, str(a.shape), a.dtype, a.min(), a.max(), a.mean()))
    del a

print()
print("census.npz contents (data, not code):")
z = np.load(r"C:\dev\strehl-out\V-NOISE\census.npz", allow_pickle=True)
for k in z.files:
    v = z[k]
    print("  %-16s %-16s %s" % (k, getattr(v, "shape", ""), str(v)[:110].replace("\n", " ")))
