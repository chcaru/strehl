"""Detect merge artifacts as TEXTURE CLIFFS: places where local detail changes
abruptly without a matching change in intensity.

Motivation. On the correctly-exposed render, a flat grey patch with a hard
angular boundary sits on the lower part of the bee's compound eye: inside it
the ommatidia texture is gone. That is the merge electing a defocused frame
for a region, and its boundary is a discontinuity.

Two earlier attempts failed and are kept in the tree as step.py and ridge.py.
step.py's verdict came from a band that crossed the subject; ridge.py masked
to the bright background, which is where this artifact is NOT, and further
excluded locally-varying regions -- which is what a step is.

The discriminator here: a real object boundary changes intensity AND texture
together. A merge artifact changes texture while intensity stays nearly
continuous, because both candidate frames saw the same scene radiance and
differ only in focus. So look for large gradients in log-texture that
coincide with small gradients in intensity.
"""
import os
import numpy as np
import tifffile
import cv2

SRC = r"C:\dev\strehl-out\ORCH-exposure\bee-3-exposed.tif"
OUT = r"C:\dev\strehl-out\ORCH-diagnose"
a = tifffile.imread(SRC).astype(np.float32).mean(axis=2) / 65535.0
H, W = a.shape
print("render %dx%d" % (W, H))

# Local texture: high-frequency energy in a small window.
lp = cv2.blur(a, (9, 9))
hf = a - lp
tex = cv2.blur(hf * hf, (33, 33))
lt = np.log10(tex + 1e-8)

# Gradients of log-texture and of intensity, at the same scale.
def grad(img, k=9):
    s = cv2.blur(img, (k, k))
    gx = cv2.Sobel(s, cv2.CV_32F, 1, 0, ksize=5)
    gy = cv2.Sobel(s, cv2.CV_32F, 0, 1, ksize=5)
    return np.sqrt(gx * gx + gy * gy)


gt = grad(lt)
gi = grad(a)

# Normalise each to its own distribution so the comparison is scale-free.
gt_n = gt / (np.percentile(gt, 99) + 1e-9)
gi_n = gi / (np.percentile(gi, 99) + 1e-9)

# Artifact score: strong texture cliff, weak intensity edge.
score = gt_n * np.maximum(0.0, 1.0 - 4.0 * gi_n)
thr = float(np.percentile(score, 99.9))
cand = score > thr
print("texture-cliff candidates: %.4f%% of frame (threshold %.4f)"
      % (100 * cand.mean(), thr))

cand_u8 = cv2.morphologyEx(cand.astype(np.uint8), cv2.MORPH_CLOSE,
                           np.ones((5, 5), np.uint8))
n, lab, stats, cent = cv2.connectedComponentsWithStats(cand_u8, connectivity=8)
rows = []
for i in range(1, n):
    x, y, w, h, area = stats[i]
    if area < 400:
        continue
    ext = max(w, h)
    if ext < 120:
        continue
    rows.append((area, ext, int(x), int(y), int(w), int(h), i))
rows.sort(reverse=True)
print("%d large texture-cliff structures (area>=400, extent>=120)" % len(rows))
for r in rows[:10]:
    print("   area %6d extent %5d  bbox x=%d y=%d w=%d h=%d" % r[:6])

if not rows:
    print("\nVERDICT: no texture cliffs. No visible-scale merge artifact found.")
    raise SystemExit(0)

# Measure the biggest one: is intensity really continuous across it while
# texture is not? That is the signature; report both.
area, ext, x, y, w, h, lb = rows[0]
ys, xs = np.nonzero(lab == lb)
pts = np.stack([xs - xs.mean(), ys - ys.mean()]).astype(np.float64)
u, _, _ = np.linalg.svd(pts @ pts.T / pts.shape[1])
tang = u[:, 0]
norm = np.array([-tang[1], tang[0]])

R = 30
pi_ = np.zeros(2 * R + 1)
pt_ = np.zeros(2 * R + 1)
cnt = 0
sel = np.linspace(0, len(xs) - 1, min(len(xs), 3000)).astype(int)
for j in sel:
    px = np.rint(xs[j] + norm[0] * np.arange(-R, R + 1)).astype(int)
    py = np.rint(ys[j] + norm[1] * np.arange(-R, R + 1)).astype(int)
    if px.min() < 0 or py.min() < 0 or px.max() >= W or py.max() >= H:
        continue
    pi_ += a[py, px]
    pt_ += lt[py, px]
    cnt += 1
pi_ /= max(cnt, 1); pt_ /= max(cnt, 1)

print("\nlargest structure: %d px, %d perpendicular cuts averaged" % (len(xs), cnt))
print("intensity across it   : %s" % " ".join("%.4f" % v for v in pi_[::5]))
print("log10 texture across  : %s" % " ".join("%.3f" % v for v in pt_[::5]))
di = float(np.abs(np.diff(pi_)).max())
dt = float(np.abs(np.diff(pt_)).max())
print("max step: intensity %.5f (%.2f%% of range)   log-texture %.4f (%.2fx in energy)"
      % (di, 100 * di, dt, 10 ** dt))
print()
if dt > 0.25 and di < 0.02:
    print("VERDICT: TEXTURE CLIFF with continuous intensity -- a merge election "
          "boundary, not an object edge. Detail changes %.2fx across it while "
          "brightness changes %.2f%%." % (10 ** dt, 100 * di))
else:
    print("VERDICT: not separable from an ordinary object edge.")

vis = cv2.cvtColor((np.clip(a, 0, 1) * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
vis[cand_u8.astype(bool)] = (0, 0, 255)
cv2.imwrite(os.path.join(OUT, "texture-cliffs.png"), vis[::4, ::4])
print("wrote texture-cliffs.png")
