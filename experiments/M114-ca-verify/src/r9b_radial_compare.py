"""M114 R9b -- why is 109MSDCF's improvement smaller?  Two candidate causes:
(a) benign: its edges sit nearer the optical centre, where a radial correction
    is correctly near zero; (b) alarming: the correction transfers badly off
    the fit stack.  Distinguish them by comparing the RADIAL distribution of
    near-edge pixels, and the per-annulus change, between the two stacks.
"""
import numpy as np
import tifffile
from scipy import ndimage

PAIRS = {
    "bee-3-cpl  (fit stack, f/5.6)": (
        r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif",
        r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"),
    "109MSDCF   (held out, f/11)": (
        r"C:\dev\strehl-out\M114-ca-verify\r9\off.tif",
        r"C:\dev\strehl-out\M114-ca-verify\r9\on.tif"),
}
EDGES = [0.0, 0.2, 0.4, 0.6, 0.788, 1.05]

for tag, (p0, p1) in PAIRS.items():
    a0 = tifffile.imread(p0).astype(np.float32) / np.float32(65535.0)
    a1 = tifffile.imread(p1).astype(np.float32) / np.float32(65535.0)
    H, W, _ = a0.shape
    y0 = 0.2126 * a0[..., 0] + 0.7152 * a0[..., 1] + 0.0722 * a0[..., 2]
    y1 = 0.2126 * a1[..., 0] + 0.7152 * a1[..., 1] + 0.0722 * a1[..., 2]
    gy, gx = np.gradient(y0)
    mag = np.hypot(gx, gy)
    near = ndimage.distance_transform_edt(~(mag >= np.quantile(mag, 0.99))) <= 3
    cy, cx = H * 0.5, W * 0.5
    yy, xx = np.mgrid[0:H, 0:W]
    rad = (np.hypot(xx - cx, yy - cy) / np.hypot(cx, cy)).astype(np.float32)
    del yy, xx

    def hp(x):
        return x - ndimage.uniform_filter(x, 31, mode="nearest")

    d0 = np.abs(hp(a0[..., 0] - y0))[near].astype(np.float64)
    d1 = np.abs(hp(a1[..., 0] - y1))[near].astype(np.float64)
    rn = rad[near].astype(np.float64)
    print("%s   mean r of near-edge px = %.3f   median = %.3f"
          % (tag, rn.mean(), np.median(rn)))
    for i in range(len(EDGES) - 1):
        m = (rn >= EDGES[i]) & (rn < EDGES[i + 1])
        if m.sum() < 500:
            print("      r %.2f-%.2f  n=%d (too few)" % (EDGES[i], EDGES[i + 1], m.sum()))
            continue
        print("      r %.2f-%.2f  n=%8d  share=%5.1f%%  hp|R-Y| %.5f -> %.5f  %+.2f%%"
              % (EDGES[i], EDGES[i + 1], m.sum(), 100 * m.mean(),
                 d0[m].mean(), d1[m].mean(),
                 100 * (d1[m].mean() - d0[m].mean()) / d0[m].mean()))
    del a0, a1, y0, y1, rad
    print()
