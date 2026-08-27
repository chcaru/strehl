"""Strong test of the convention: DISTANT pairs, where declared drift is ~34 px.
A correct warp must collapse that to the alignment floor.  Adjacent pairs cannot
discriminate because they only drift 0.45 px unwarped."""
import os, glob
import numpy as np, cv2, tifffile
import vm_warp as VW

ROOT = r"C:\dev\strehl-out\V-REVIEW\merge"
A, B, META = VW.parse_warp(glob.glob(os.path.join(ROOT, "cache", "*.warpmap.txt"))[0])
m = tifffile.imread(os.path.join(ROOT, "master.tiff"))
H, W = m.shape[:2]
CROP = 640
cy, cx = H // 2, W // 2
ys, xs = np.mgrid[cy - CROP:cy + CROP, cx - CROP:cx + CROP].astype(np.float32)
zc = xs + 1j * ys

def load(k):
    return tifffile.imread(os.path.join(ROOT, "frames", "frame%02d.tiff" % k))[:, :, 1].astype(np.float32)

def warp(k, img, ctr):
    c = A[k] * (zc - ctr) + B[k] + ctr
    return cv2.remap(img, np.real(c).astype(np.float32), np.imag(c).astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def crop(img):
    return img[cy - CROP:cy + CROP, cx - CROP:cx + CROP]

CTRS = {"W/2,H/2": complex(W / 2.0, H / 2.0),
        "(W-1)/2,(H-1)/2": complex((W - 1) / 2.0, (H - 1) / 2.0)}
PAIRS = [(0, 9), (9, 18), (0, 18), (2, 16), (4, 14)]
print("%-18s %8s %12s %12s" % ("centre", "pair", "unwarped", "warped"))
best = None
for cname, ctr in CTRS.items():
    tot = []
    for (i, j) in PAIRS:
        gi, gj = load(i), load(j)
        su, _ = cv2.phaseCorrelate(crop(gi).astype(np.float64), crop(gj).astype(np.float64))
        sw, _ = cv2.phaseCorrelate(warp(i, gi, ctr).astype(np.float64),
                                   warp(j, gj, ctr).astype(np.float64))
        u, w = float(np.hypot(*su)), float(np.hypot(*sw))
        tot.append(w)
        print("%-18s %8s %12.3f %12.3f" % (cname, "%d-%d" % (i, j), u, w))
    print("%-18s %8s %12s %12.3f" % (cname, "MEAN", "", float(np.mean(tot))))
    if best is None or np.mean(tot) < best[1]:
        best = (cname, float(np.mean(tot)))
print("")
print("BEST centre: %s  mean warped residual %.3f px  (sidecar cycle floor 0.333 px)" % best)
