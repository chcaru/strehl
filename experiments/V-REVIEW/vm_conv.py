"""Which coordinate convention does the sidecar use?  Test empirically.
Metric: residual between ADJACENT frames after warping into reference coords.
Adjacent frames share focus, so registration between them is measurable;
frame-0-vs-master is not, because their focus differs.
The correct convention is the one that beats the unwarped baseline."""
import os, struct, glob
import numpy as np, cv2, tifffile

ROOT = r"C:\dev\strehl-out\V-REVIEW\merge"
import vm_warp as VW

A, B, META = VW.parse_warp(glob.glob(os.path.join(ROOT, "cache", "*.warpmap.txt"))[0])
m = tifffile.imread(os.path.join(ROOT, "master.tiff"))
H, W = m.shape[:2]
ctr = complex(W / 2.0, H / 2.0)
CROP = 640
cy, cx = H // 2, W // 2
ys, xs = np.mgrid[cy - CROP:cy + CROP, cx - CROP:cx + CROP].astype(np.float32)
zc = xs + 1j * ys

CONV = {
    "a*z+b (as given)":        lambda k: A[k] * zc + B[k],
    "inverse (z-b)/a":         lambda k: (zc - B[k]) / A[k],
    "centred a*(z-c)+b+c":     lambda k: A[k] * (zc - ctr) + B[k] + ctr,
    "centred inverse":         lambda k: (zc - ctr - B[k]) / A[k] + ctr,
    "none (unwarped)":         lambda k: zc,
}

cache = {}
def g(k):
    if k not in cache:
        if len(cache) > 3:
            cache.pop(next(iter(cache)))
        cache[k] = tifffile.imread(os.path.join(ROOT, "frames",
                                                "frame%02d.tiff" % k))[:, :, 1].astype(np.float32)
    return cache[k]

PAIRS = [(0, 1), (3, 4), (7, 8), (11, 12), (15, 16), (17, 18)]
print("%-24s %10s %10s" % ("convention", "mean resid", "max resid"))
for name, fn in CONV.items():
    res = []
    for (i, j) in PAIRS:
        c1, c2 = fn(i), fn(j)
        w1 = cv2.remap(g(i), np.real(c1).astype(np.float32), np.imag(c1).astype(np.float32),
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        w2 = cv2.remap(g(j), np.real(c2).astype(np.float32), np.imag(c2).astype(np.float32),
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        s, _ = cv2.phaseCorrelate(w1.astype(np.float64), w2.astype(np.float64))
        res.append(float(np.hypot(*s)))
    print("%-24s %10.3f %10.3f" % (name, float(np.mean(res)), float(np.max(res))))
