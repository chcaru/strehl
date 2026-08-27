"""Parse the warp sidecar and VERIFY the transform direction before trusting it.
If reference->frame is inverted, registration error doubles the drift and every
edge in the image grows a false rim.  Measure it; do not assume it."""
import sys, os, struct, glob
import numpy as np, cv2, tifffile

ROOT = r"C:\dev\strehl-out\V-REVIEW\merge"


def parse_warp(path):
    a, b, meta = {}, {}, {}
    for ln in open(path, "r", encoding="utf-8"):
        ln = ln.rstrip("\n")
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        if p[0].isdigit() and len(p) >= 6 and p[1] == "placed":
            i = int(p[0])
            v = [struct.unpack(">d", bytes.fromhex(x))[0] for x in p[2:6]]
            a[i] = complex(v[0], v[1]); b[i] = complex(v[2], v[3])
        elif len(p) >= 2:
            meta[p[0]] = " ".join(p[1:])
    return a, b, meta


wp = glob.glob(os.path.join(ROOT, "cache", "*.warpmap.txt"))[0]
A, B, META = parse_warp(wp)
print("sidecar:", os.path.basename(wp))
for k in ("frames", "plane", "reference", "resampler", "cycle-floor-px", "strategy"):
    print("   %-15s %s" % (k, META.get(k)))
print("   parsed placements:", len(A))

master = tifffile.imread(os.path.join(ROOT, "master.tiff"))
H, W = master.shape[:2]
print("   master %dx%d" % (W, H))

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
z = xx + 1j * yy


def warp_frame(k, img):
    c = A[k] * z + B[k]
    return cv2.remap(img, np.real(c).astype(np.float32), np.imag(c).astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def gray(a):
    return a[:, :, 1].astype(np.float32)


mg = gray(master)
cy, cx = H // 2, W // 2
win = 512
mc = mg[cy - win:cy + win, cx - win:cx + win].copy()
print("")
print("== warp direction check: residual shift of warped frame vs master ==")
print("%5s %14s %16s %16s" % ("frame", "declared drift", "resid AS-GIVEN", "resid INVERTED"))
for k in (0, len(A) // 2, len(A) - 1):
    img = tifffile.imread(os.path.join(ROOT, "frames", "frame%02d.tiff" % k))
    g = gray(img)
    fwd = warp_frame(k, g)
    ci = 1.0 / A[k]
    cinv = ci * z - ci * B[k]
    inv = cv2.remap(g, np.real(cinv).astype(np.float32), np.imag(cinv).astype(np.float32),
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    d_decl = abs(A[k] * complex(W, H) + B[k] - complex(W, H))
    s1, _ = cv2.phaseCorrelate(mc.astype(np.float64),
                               fwd[cy - win:cy + win, cx - win:cx + win].astype(np.float64))
    s2, _ = cv2.phaseCorrelate(mc.astype(np.float64),
                               inv[cy - win:cy + win, cx - win:cx + win].astype(np.float64))
    print("%5d %14.3f %16.3f %16.3f"
          % (k, d_decl, float(np.hypot(*s1)), float(np.hypot(*s2))))
print("")
print("The correct direction is the one with residual near 0 at EVERY frame.")
