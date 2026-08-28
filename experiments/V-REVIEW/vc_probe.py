import tifffile, numpy as np, os
old = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\dry-erase-marker-head-cpl.tiff"
a = tifffile.imread(old)
print("old shape", a.shape, a.dtype, "min", a.min(), "max", a.max())
v6 = r"C:\dev\strehl-out\DELIVER-V6\masters"
if os.path.isdir(v6):
    fs = sorted(os.listdir(v6))
    print("V6 files:", len(fs), fs[:4])
else:
    print("V6 masters dir absent; siblings:", os.listdir(r"C:\dev\strehl-out\DELIVER-V6"))
