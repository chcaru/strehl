import glob, os, numpy as np, tifffile, rawpy
m = tifffile.imread(r"C:\dev\strehl-out\acceptance\SHIP-V4\coffee-bubbles--SHIP-V4.tiff")
print("SHIP-V4 master        :", m.shape, m.dtype)
o = tifffile.imread(r"C:\dev\strehl-out\V-GATHER\onlyframe\cb-f09.tiff")
print("ONLY_FRAME=9 render   :", o.shape, o.dtype)
arw = sorted(glob.glob(r"D:\personal\macro\coffee-bubbles\*.ARW"))
print("frames on disk        :", len(arw))
with rawpy.imread(arw[9]) as r:
    s = r.postprocess(gamma=(2.222,4.5), no_auto_bright=True, use_camera_wb=True, output_bps=16)
print("rawpy postprocess     :", s.shape, s.dtype)
cov = 0.9887
print()
print("master magnification vs sensor grid : %.4f  (1/%.4f)" % (1.0/cov, cov))
print("corner displacement from scale alone over a 560 px crop at radius 3000 px:")
print("   %.1f px   -- SEARCH is 48 px" % (3000*(1.0/cov-1.0)))
