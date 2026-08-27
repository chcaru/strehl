"""Convention test done where the signal is: CORNERS.
Focus breathing is a scale change about some centre, so it produces ~zero
displacement at that centre and maximum at the corners.  A centre crop cannot
discriminate any convention.  Declared drift is CORNER drift."""
import os, glob
import numpy as np, cv2, tifffile
import vm_warp as VW

ROOT = r"C:\dev\strehl-out\V-REVIEW\merge"
A, B, META = VW.parse_warp(glob.glob(os.path.join(ROOT, "cache", "*.warpmap.txt"))[0])
m = tifffile.imread(os.path.join(ROOT, "master.tiff"))
H, W = m.shape[:2]
S = 384
CORNERS = {"TL": (S, S), "TR": (S, W - S), "BL": (H - S, S), "BR": (H - S, W - S)}
ctr_c = complex((W - 1) / 2.0, (H - 1) / 2.0)

def load(k):
    return tifffile.imread(os.path.join(ROOT, "frames", "frame%02d.tiff" % k))[:, :, 1].astype(np.float32)

def maps(cy, cx):
    ys, xs = np.mgrid[cy - S:cy + S, cx - S:cx + S].astype(np.float32)
    return xs + 1j * ys

CONV = {
    "none":            lambda k, z: z,
    "a*z+b":           lambda k, z: A[k] * z + B[k],
    "(z-b)/a":         lambda k, z: (z - B[k]) / A[k],
    "a*(z-c)+b+c":     lambda k, z: A[k] * (z - ctr_c) + B[k] + ctr_c,
    "(z-c-b)/a+c":     lambda k, z: (z - ctr_c - B[k]) / A[k] + ctr_c,
}
PAIRS = [(0, 9), (9, 18), (0, 18)]
frames = {k: load(k) for k in (0, 9, 18)}
print("%-16s %25s %10s" % ("convention", "worst corner/pair resid px", "mean"))
res_all = {}
for name, fn in CONV.items():
    rr = []
    for cn, (cy, cx) in CORNERS.items():
        z = maps(cy, cx)
        for (i, j) in PAIRS:
            wi = cv2.remap(frames[i], np.real(fn(i, z)).astype(np.float32),
                           np.imag(fn(i, z)).astype(np.float32), cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)
            wj = cv2.remap(frames[j], np.real(fn(j, z)).astype(np.float32),
                           np.imag(fn(j, z)).astype(np.float32), cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_REPLICATE)
            s, _ = cv2.phaseCorrelate(wi.astype(np.float64), wj.astype(np.float64))
            rr.append(float(np.hypot(*s)))
    res_all[name] = rr
    print("%-16s %25.3f %10.3f" % (name, float(np.max(rr)), float(np.mean(rr))))
print("")
b = min(res_all, key=lambda n: np.mean(res_all[n]))
print("BEST: %s   mean %.3f px  worst %.3f px   (cycle floor 0.333 px)"
      % (b, float(np.mean(res_all[b])), float(np.max(res_all[b]))))
print("unwarped mean for contrast: %.3f px" % float(np.mean(res_all["none"])))
