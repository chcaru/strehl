import numpy as np, tifffile, glob, os
rows=[]
for p in sorted(glob.glob(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB\*.tiff")):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16
    s = a[::8, ::8, :].astype(np.float32)/65535.0
    lum = s @ np.array([0.2126,0.7152,0.0722], np.float32)
    gy, gx = np.gradient(lum)
    g = np.hypot(gx, gy)
    thr = np.percentile(g, 99)
    rows.append((os.path.basename(p)[:-5], lum.mean(), np.median(lum), lum.std(),
                 float(np.mean(lum > 0.5)), float(np.percentile(g,99.9))))
    del a, s, lum, g
print("%-38s %7s %7s %7s %9s %9s" % ("subject","mean","median","sd","frac>0.5","g99.9"))
for r in sorted(rows, key=lambda r: r[1]):
    print("%-38s %7.4f %7.4f %7.4f %8.1f%% %9.5f" % (r[0], r[1], r[2], r[3], 100*r[4], r[5]))
