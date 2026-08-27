"""Print real edge profiles as numbers.  If the master's edges are 8-20 px soft,
that is a headline fact and must be seen, not inferred from a summary."""
import sys, os
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_lib as H

subject = sys.argv[1]
R = float(sys.argv[2]) if len(sys.argv) > 2 else 24.0
rgb = H.read_master(subject)
lm = H.lum(rgb).astype(np.float32)
g = cv2.GaussianBlur(lm, (0, 0), 2.0)
gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=5)
gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=5)
mag = cv2.magnitude(gx, gy)
h, w = lm.shape
idx = np.argsort(mag.ravel())[::-1]
shown = 0
seen = []
for j in idx:
    y, x = divmod(int(j), w)
    if y < 200 or x < 200 or y > h - 200 or x > w - 200:
        continue
    if any(abs(y - a) < 300 and abs(x - b) < 300 for a, b in seen):
        continue
    seen.append((y, x))
    nx, ny = float(gx[y, x]), float(gy[y, x]); n = np.hypot(nx, ny)
    nx, ny = nx / n, ny / n
    us, p = H.profile_at(lm, y, x, nx, ny, R, 40.0)
    if p[-1] < p[0]:
        nx, ny = -nx, -ny
        us, p = H.profile_at(lm, y, x, nx, ny, R, 40.0)
    sel = np.arange(0, len(us), 4)          # 1 px spacing
    print("site (%4d,%4d)  normal (%+.2f,%+.2f)  grad %.0f" % (y, x, nx, ny, mag[y, x]))
    print("   u:  " + " ".join("%6.0f" % v for v in us[sel]))
    print("   p:  " + " ".join("%6.0f" % v for v in p[sel]))
    r = H.analyse(us, p)
    print("   analyse: %s" % ("REJECTED" if r is None else
          "step %.0f w %.2f over %.2f under %.2f floor %.2f"
          % (r["step"], r["w"], r["overshoot_dn"], r["undershoot_dn"], r["null_mean"])))
    print("")
    shown += 1
    if shown >= 5:
        break
