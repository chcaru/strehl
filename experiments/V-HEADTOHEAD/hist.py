import numpy as np, tifffile
PRIOR = r"C:\dev\macro\out\coffee-bean\stack.tif"
STREHL = r"C:\dev\strehl-out\SHIP-V2\coffee-bean--SHIP-V2.tiff"
a = tifffile.memmap(PRIOR, mode="r")
sub = np.asarray(a[::7, ::7, :]).astype(np.float32)
print("prior subsample", sub.shape)
for i, ch in enumerate("RGB"):
    v = sub[:, :, i].ravel()
    q = np.percentile(v, [0, 0.1, 1, 5, 25, 50, 75, 95, 99, 99.9, 100])
    print(f" prior {ch}: " + " ".join(f"{x:.4f}" for x in q), " frac==1.0:", float((v >= 1.0).mean()))
del a, sub
b = tifffile.memmap(STREHL, mode="r")
sub2 = np.asarray(b[::7, ::7, :]).astype(np.float32) / 65535.0
print("strehl subsample", sub2.shape)
for i, ch in enumerate("RGB"):
    v = sub2[:, :, i].ravel()
    q = np.percentile(v, [0, 0.1, 1, 5, 25, 50, 75, 95, 99, 99.9, 100])
    print(f" strehl {ch}: " + " ".join(f"{x:.4f}" for x in q), " frac==1.0:", float((v >= 1.0).mean()))
