"""Find the halo contour by measurement, then profile across it.

Guessing crop coordinates by eye is what produced fact 1250's retraction and
discipline 610. So: detect candidate decision boundaries automatically as
curvilinear ridges of |grad| inside the smooth background, then measure the
profile perpendicular to each one.

A piecewise-constant winner field produces long, thin, connected contours
with a genuine discontinuity across them. A defocused optical veil produces
a smooth ramp with no such structure.
"""
import os
import numpy as np
import tifffile
import cv2

SRC = r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"
OUT = r"C:\dev\strehl-out\ORCH-diagnose"
a = tifffile.imread(SRC).astype(np.float32).mean(axis=2)
H, W = a.shape
print("render %dx%d" % (W, H))

# 1. Background mask: bright, and locally smooth over a wide window, so the
#    subject and its hairs are excluded along with any fine detail.
K = 65
mu = cv2.blur(a, (K, K))
mu2 = cv2.blur(a * a, (K, K))
sd = np.sqrt(np.maximum(mu2 - mu * mu, 0.0))
bg = (mu > np.percentile(mu, 60)) & (sd < np.percentile(sd, 25))
# Erode so we never touch the subject silhouette itself.
bg = cv2.erode(bg.astype(np.uint8), np.ones((41, 41), np.uint8)).astype(bool)
print("background mask: %.1f%% of frame" % (100.0 * bg.mean()))

# 2. High-pass: remove any smooth optical falloff, keep discontinuities.
lp = cv2.blur(a, (41, 41))
hp = a - lp
# 3. Gradient of the high-passed field.
gx = cv2.Sobel(hp, cv2.CV_32F, 1, 0, ksize=3)
gy = cv2.Sobel(hp, cv2.CV_32F, 0, 1, ksize=3)
gm = np.sqrt(gx * gx + gy * gy)

inbg = gm[bg]
p50, p999 = np.percentile(inbg, 50), np.percentile(inbg, 99.9)
print("background |grad(hp)|: median %.3f  p99.9 %.3f  ratio %.1fx"
      % (p50, p999, p999 / max(p50, 1e-9)))

# 4. Ridges: pixels well above the background's own gradient distribution.
thr = np.percentile(inbg, 99.5)
ridge = (gm > thr) & bg
n, lab, stats, _ = cv2.connectedComponentsWithStats(
    ridge.astype(np.uint8), connectivity=8)
areas = stats[1:, cv2.CC_STAT_AREA]
boxes = stats[1:, :4]
long_thin = []
for i in range(len(areas)):
    x, y, w, h = boxes[i]
    ext = max(w, h)
    if areas[i] >= 200 and ext >= 150 and areas[i] < 0.35 * w * h:
        long_thin.append((areas[i], ext, x, y, w, h, i + 1))
long_thin.sort(reverse=True)
print("ridge components in background: %d total, %d long-and-thin (>=200 px, "
      "extent >=150 px, fill <35%%)" % (n - 1, len(long_thin)))
for r in long_thin[:8]:
    print("   area %6d extent %5d  bbox x=%d y=%d w=%d h=%d" % r[:6])

if not long_thin:
    print("\nVERDICT: no curvilinear discontinuities in the background. "
          "The halo is a smooth optical veil, not a decision boundary.")
    raise SystemExit(0)

# 5. Profile perpendicular to the largest ridge, averaged along it.
_, _, bx, by, bw, bh, lb = long_thin[0]
ys, xs = np.nonzero(lab == lb)
# Principal direction of the ridge.
pts = np.stack([xs - xs.mean(), ys - ys.mean()])
u, s, _ = np.linalg.svd(pts @ pts.T / pts.shape[1])
tang = u[:, 0]
norm = np.array([-tang[1], tang[0]])
print("\nlargest ridge: %d px, tangent (%.3f, %.3f)" % (len(xs), tang[0], tang[1]))

R = 24
prof = np.zeros(2 * R + 1)
cnt = 0
sel = np.linspace(0, len(xs) - 1, min(len(xs), 4000)).astype(int)
for j in sel:
    cx, cy = xs[j], ys[j]
    px = np.rint(cx + norm[0] * np.arange(-R, R + 1)).astype(int)
    py = np.rint(cy + norm[1] * np.arange(-R, R + 1)).astype(int)
    if px.min() < 0 or py.min() < 0 or px.max() >= W or py.max() >= H:
        continue
    prof += a[py, px]
    cnt += 1
prof /= max(cnt, 1)
d = np.abs(np.diff(prof))
print("averaged over %d perpendicular cuts" % cnt)
print("profile (DN): " + " ".join("%.1f" % v for v in prof))
print("max |step| %.2f DN at offset %+d ; median |step| %.2f DN ; ratio %.1fx"
      % (d.max(), int(np.argmax(d)) - R, np.median(d), d.max() / max(np.median(d), 1e-9)))

edge = d.max()
smooth = np.median(d)
print()
if edge > 5.0 * smooth:
    print("VERDICT: STEP. A %.1f DN discontinuity over one pixel, %.1fx the "
          "local ramp. This is a piecewise-constant admission boundary."
          % (edge, edge / max(smooth, 1e-9)))
else:
    print("VERDICT: RAMP. No discontinuity above the local gradient.")

vis = np.clip((a - np.percentile(a, 1)) /
              (np.percentile(a, 99) - np.percentile(a, 1)), 0, 1)
vis = (vis * 255).astype(np.uint8)
vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)
vis[ridge] = (0, 0, 255)
cv2.imwrite(os.path.join(OUT, "ridges.png"), vis[::4, ::4])
print("wrote ridges.png (detected boundaries in red)")
