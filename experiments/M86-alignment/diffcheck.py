import sys, numpy as np, tifffile
a = tifffile.imread(r"C:\dev\strehl-out\M86-align\bee3-aligned-cov.tif")
b = tifffile.imread(r"C:\dev\strehl-out\M86-align\bee3-zoomnull.tif")
u = tifffile.imread(r"C:\dev\strehl-out\M86-align\bee-3-UNALIGNED.tif")
print("shapes", a.shape, b.shape, u.shape)
for name, x, y in (("aligned vs zoomnull", a, b), ("aligned vs unaligned", a, u), ("zoomnull vs unaligned", b, u)):
    d = np.abs(x.astype(np.int32) - y.astype(np.int32))
    print(f"{name:24s} differing px {100.0*(d>0).mean():7.3f}%  mean|d| {d.mean():9.2f}  max {d.max()}")
