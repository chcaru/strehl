import numpy as np, tifffile
p = r"C:\dev\strehl-out\GALLERY-NOW\flower-bud-alone-cpl.tif"
a = tifffile.imread(p)
print("shape", a.shape, a.dtype)
H, W = a.shape[:2]
print("frame %dx%d  centre (%d,%d)" % (W, H, W//2, H//2))
x0, y0 = 3200, 800
c = a[y0:y0+800, x0:x0+800].astype(np.float32)
R, G, B = c[:,:,0], c[:,:,1], c[:,:,2]
lvl = c.max(axis=2)
# magenta = R and B both above G
mg = ((R - G) + (B - G)) / 2.0
print("\ncrop x=%d..%d y=%d..%d" % (x0, x0+800, y0, y0+800))
print("level: min %d median %d max %d ; frac at 65535 (any ch) %.3f%%" % (
    lvl.min(), np.median(lvl), lvl.max(), 100.0*(c>=65535).any(axis=2).mean()))
print("magenta index (R-G + B-G)/2: p99 %.0f  max %.0f" % (np.percentile(mg,99), mg.max()))
# Where are the most magenta pixels in the crop?
th = np.percentile(mg, 99.5)
ys, xs = np.where(mg >= th)
print("top-0.5%% magenta pixels: n=%d  centroid crop(x=%.0f,y=%.0f) full(x=%.0f,y=%.0f)" % (
    len(xs), xs.mean(), ys.mean(), x0+xs.mean(), y0+ys.mean()))
print("  their level: median %.0f   their mg: median %.0f" % (np.median(lvl[ys,xs]), np.median(mg[ys,xs])))
# bounding box of the magenta cluster
print("  bbox crop x %d..%d  y %d..%d" % (xs.min(), xs.max(), ys.min(), ys.max()))
