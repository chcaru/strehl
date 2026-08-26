import sys, numpy as np, tifffile
a = tifffile.imread(sys.argv[1]).astype(np.int64)
b = tifffile.imread(sys.argv[2]).astype(np.int64)
print("shapes", a.shape, b.shape, a.dtype, b.dtype)
d = b - a
moved = np.any(d != 0, axis=2)
print("pixels moved      : %d / %d = %.4f%%" % (moved.sum(), moved.size, 100.0*moved.sum()/moved.size))
for i,ch in enumerate("RGB"):
    di = d[:,:,i]
    print("  %s max|d| %6d  min %6d  max %6d  moved %.4f%%" % (
        ch, np.abs(di).max(), di.min(), di.max(), 100.0*(di!=0).mean()))
if moved.any():
    # level of the moved pixels, measured on the BEFORE image
    lv = a.max(axis=2)[moved]
    print("moved-pixel level on BEFORE (max over channels, 0-65535):")
    print("   min %d  p1 %d  median %d  max %d" % (lv.min(), np.percentile(lv,1), np.median(lv), lv.max()))
    unmoved_hi = a.max(axis=2)[~moved]
    print("unmoved max level : %d" % unmoved_hi.max())
