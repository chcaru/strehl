import numpy as np, tifffile, sys
d = r"C:\dev\strehl-out\BUILD-PYRNOISE\renders\109MSDCF"
a = tifffile.imread(d + r"\pyr_default.tif")
b = tifffile.imread(d + r"\_cactl_pyr_nocia.tif")
print("shapes", a.shape, b.shape)
for i, nm in enumerate("RGB"):
    d_ = a[:, :, i].astype(np.int64) - b[:, :, i].astype(np.int64)
    print(f"  plane {nm}: max|d| = {np.abs(d_).max():6d} DN   nonzero = {np.count_nonzero(d_)/d_.size:8.4%}")
