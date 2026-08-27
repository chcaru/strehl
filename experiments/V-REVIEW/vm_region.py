"""Where are the frames NATIVELY registered, with no warp at all?
Focus breathing is a scale change, so displacement grows with radius from its
centre.  Find the radius where the WHOLE stack agrees to under ~1 px unwarped.
Inside that radius the envelope needs no warp and carries no warp risk."""
import os, glob
import numpy as np, cv2, tifffile
import vm_warp as VW

ROOT = r"C:\dev\strehl-out\V-REVIEW\merge"
m = tifffile.imread(os.path.join(ROOT, "master.tiff"))
H, W = m.shape[:2]
cy, cx = H // 2, W // 2
NF = 19

def load(k):
    return tifffile.imread(os.path.join(ROOT, "frames", "frame%02d.tiff" % k))[:, :, 1].astype(np.float32)

f0, f9, f18 = load(0), load(9), load(18)
print("== native registration vs block half-size (no warp) ==")
print("%10s %12s %12s %12s" % ("half-size", "0 vs 9", "9 vs 18", "0 vs 18"))
ok = None
for hs in (128, 192, 256, 384, 512, 640, 768, 1024):
    r = []
    for (a, b) in ((f0, f9), (f9, f18), (f0, f18)):
        A = a[cy - hs:cy + hs, cx - hs:cx + hs].astype(np.float64)
        B = b[cy - hs:cy + hs, cx - hs:cx + hs].astype(np.float64)
        s, _ = cv2.phaseCorrelate(A, B)
        r.append(float(np.hypot(*s)))
    print("%10d %12.3f %12.3f %12.3f" % (hs, r[0], r[1], r[2]))
    if max(r) < 1.0:
        ok = hs
print("")
print("largest half-size with every pair under 1.0 px:", ok)

# Confirm across ALL frames, not just three.
if ok:
    hs = ok
    ref = f9[cy - hs:cy + hs, cx - hs:cx + hs].astype(np.float64)
    worst, worstk = 0.0, None
    for k in range(NF):
        g = load(k)[cy - hs:cy + hs, cx - hs:cx + hs].astype(np.float64)
        s, _ = cv2.phaseCorrelate(ref, g)
        d = float(np.hypot(*s))
        if d > worst:
            worst, worstk = d, k
    print("ALL %d frames vs reference at half-size %d: worst %.3f px (frame %d)"
          % (NF, hs, worst, worstk))
    print("photometric check, median level per frame in region:")
    lv = [float(np.median(load(k)[cy - hs:cy + hs, cx - hs:cx + hs])) for k in range(NF)]
    print("   min %.0f  max %.0f  spread %.2f%%  master %.0f"
          % (min(lv), max(lv), 100.0 * (max(lv) - min(lv)) / max(np.mean(lv), 1e-9),
             float(np.median(m[cy - hs:cy + hs, cx - hs:cx + hs, 1]))))
