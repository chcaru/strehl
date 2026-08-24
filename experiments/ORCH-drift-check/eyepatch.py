"""Characterise the grey patch on the bee's eye.

HONESTY NOTE: I located this artifact BY EYE on the correctly-exposed 100%
crop. cliff.py tried to find it with an unbiased detector and failed -- its
top hits were ordinary object edges. So this is a characterisation of a
known-visible defect, not a survey, and nothing here may be read as a
frequency or a rate. The detector is the missing instrument.

What to establish: inside the patch, is the ommatidia texture actually gone
(the merge elected a defocused frame), and is its boundary a step?
"""
import os
import numpy as np
import tifffile
import cv2
from PIL import Image

SRC = r"C:\dev\strehl-out\ORCH-exposure\bee-3-exposed.tif"
OUT = r"C:\dev\strehl-out\ORCH-diagnose"
a = tifffile.imread(SRC).astype(np.float32).mean(axis=2) / 65535.0
H, W = a.shape

# The 100% crop that showed it was at x=0.52*W, y=0.62*H, 1100 px, and the
# patch sat near its bottom-centre.
X0, Y0, N = int(W * 0.52), int(H * 0.62), 1100
eye = a[Y0:Y0 + N, X0:X0 + N]

lp = cv2.blur(eye, (9, 9))
hf = eye - lp
tex = cv2.blur(hf * hf, (25, 25))
lt = np.log10(tex + 1e-9)

# Restrict to the eye itself: dark, and textured somewhere nearby.
dark = eye < np.percentile(eye, 45)
print("dark (eye) fraction of crop: %.1f%%" % (100 * dark.mean()))
inside = lt[dark]
print("log10 texture inside the eye: p5 %.3f  p50 %.3f  p95 %.3f"
      % tuple(float(np.percentile(inside, q)) for q in (5, 50, 95)))

# The patch is the low-texture part of the eye. Threshold well below the
# eye's own median texture.
cut = float(np.percentile(inside, 50)) - 0.45
patch = dark & (lt < cut)
patch = cv2.morphologyEx(patch.astype(np.uint8), cv2.MORPH_OPEN,
                         np.ones((9, 9), np.uint8))
n, lab, stats, _ = cv2.connectedComponentsWithStats(patch, connectivity=8)
blobs = sorted(((stats[i, cv2.CC_STAT_AREA], i) for i in range(1, n)),
               reverse=True)
print("low-texture blobs inside the eye: %d; largest %d px"
      % (len(blobs), blobs[0][0] if blobs else 0))

if not blobs or blobs[0][0] < 2000:
    print("VERDICT: no large smooth region inside the eye. Patch not confirmed.")
    raise SystemExit(0)

area, lb = blobs[0]
m = (lab == lb)
ys, xs = np.nonzero(m)
print("largest smooth blob: %d px, bbox x=%d..%d y=%d..%d (crop coords)"
      % (area, xs.min(), xs.max(), ys.min(), ys.max()))

# Texture inside the blob vs the eye immediately around it.
ring = cv2.dilate(m.astype(np.uint8), np.ones((61, 61), np.uint8)).astype(bool)
ring &= dark & ~cv2.dilate(m.astype(np.uint8),
                           np.ones((21, 21), np.uint8)).astype(bool)
t_in = float(np.median(tex[m]))
t_out = float(np.median(tex[ring]))
i_in = float(np.median(eye[m]))
i_out = float(np.median(eye[ring]))
print()
print("texture   inside %.3e   surrounding eye %.3e   ratio %.2fx"
      % (t_in, t_out, t_out / max(t_in, 1e-12)))
print("intensity inside %.4f      surrounding eye %.4f      difference %.4f (%.2f%%)"
      % (i_in, i_out, i_in - i_out, 100 * (i_in - i_out)))

# How sharp is the boundary? Distance-transform profile of texture.
d_out = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
d_in = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
sd = np.where(m, -d_in, d_out)
prof = []
for r in range(-14, 15):
    sel = dark & (np.abs(sd - r) < 0.5)
    prof.append(float(np.median(tex[sel])) if sel.sum() > 50 else np.nan)
prof = np.array(prof)
print()
print("texture vs signed distance from the blob edge (-in .. +out):")
print("  " + " ".join("%.2e" % v for v in prof[::2]))
valid = ~np.isnan(prof)
if valid.sum() > 6:
    lg = np.log10(prof[valid] + 1e-12)
    steps = np.abs(np.diff(lg))
    print("  largest single-pixel change in log texture: %.3f (%.2fx energy)"
          % (steps.max(), 10 ** steps.max()))

print()
if t_out / max(t_in, 1e-12) > 3.0:
    print("VERDICT: CONFIRMED. A %d px region of the eye carries %.1fx less "
          "detail than the eye around it, while sitting %.2f%% different in "
          "brightness. The scene has no such structure: this is the merge "
          "electing a defocused frame for a region."
          % (area, t_out / max(t_in, 1e-12), 100 * abs(i_in - i_out)))
else:
    print("VERDICT: texture difference too small to call it an artifact.")

vis = np.stack([eye] * 3, axis=-1)
vis[m] = np.array([1.0, 0.15, 0.15])
Image.fromarray((np.clip(vis, 0, 1) * 255).astype(np.uint8)).save(
    os.path.join(OUT, "eye-patch.png"))
n01 = (lt - lt.min()) / max(lt.max() - lt.min(), 1e-9)
Image.fromarray((n01 * 255).astype(np.uint8)).save(
    os.path.join(OUT, "eye-texture.png"))
print("wrote eye-patch.png (blob in red) and eye-texture.png")
