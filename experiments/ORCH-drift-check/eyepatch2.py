"""Measure the eye patch, with no brightness gate.

eyepatch.py masked to `eye < p45` and missed the artifact, because the patch
is LIGHTER than the eye around it. That is the third time tonight a mask has
excluded the very thing being looked for -- step.py's band crossed the
subject, ridge.py excluded locally-varying regions, and this one excluded by
brightness. The discipline that falls out: after building a mask, verify the
mask contains the thing you are looking for, before trusting any statistic
computed through it.

Here the region is selected from the TEXTURE map -- a measurement -- rather
than from my reading of the photograph.
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
X0, Y0, N = int(W * 0.52), int(H * 0.62), 1100
eye = a[Y0:Y0 + N, X0:X0 + N]

lp = cv2.blur(eye, (9, 9))
tex = cv2.blur((eye - lp) ** 2, (25, 25))
lt = np.log10(tex + 1e-12)

# MASK SELF-CHECK: the visible patch is near (x 350-620, y 975-1100). Confirm
# whatever mask we build actually covers it before using any number from it.
PROBE = (slice(1000, 1080), slice(380, 580))
print("probe region texture: median %.3e (log10 %.3f)"
      % (float(np.median(tex[PROBE])), float(np.median(lt[PROBE]))))
print("whole-crop texture  : median %.3e (log10 %.3f)"
      % (float(np.median(tex)), float(np.median(lt))))

cut = float(np.log10(np.median(tex) / 3.0))
smooth = (lt < cut).astype(np.uint8)
smooth = cv2.morphologyEx(smooth, cv2.MORPH_OPEN, np.ones((11, 11), np.uint8))
cover = float(smooth[PROBE].mean())
print("mask covers %.1f%% of the probe region (cut = log10 %.3f)"
      % (100 * cover, cut))
assert cover > 0.5, ("MASK DOES NOT CONTAIN THE ARTIFACT -- do not trust any "
                     "statistic computed through it")

n, lab, stats, _ = cv2.connectedComponentsWithStats(smooth, connectivity=8)
plab = lab[PROBE]
plab = plab[plab > 0]
assert plab.size, "no labelled component inside the probe region"
lb = int(np.bincount(plab.ravel()).argmax())
area = int(stats[lb, cv2.CC_STAT_AREA])
m = (lab == lb)
ys, xs = np.nonzero(m)
print("\npatch: %d px, bbox x=%d..%d y=%d..%d (crop coords), %.3f%% of the crop"
      % (area, xs.min(), xs.max(), ys.min(), ys.max(), 100 * m.mean()))

ring = cv2.dilate(m.astype(np.uint8), np.ones((81, 81), np.uint8)).astype(bool)
ring &= ~cv2.dilate(m.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool)
t_in, t_out = float(np.median(tex[m])), float(np.median(tex[ring]))
i_in, i_out = float(np.median(eye[m])), float(np.median(eye[ring]))
print("texture   inside %.3e   surrounding %.3e   ratio %.2fx"
      % (t_in, t_out, t_out / max(t_in, 1e-15)))
print("intensity inside %.4f      surrounding %.4f      difference %+.4f (%+.2f%%)"
      % (i_in, i_out, i_in - i_out, 100 * (i_in - i_out)))

d_out = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
d_in = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
sd = np.where(m, -d_in, d_out)
prof, xs_ = [], []
for r in range(-20, 21):
    sel = np.abs(sd - r) < 0.5
    if sel.sum() > 80:
        prof.append(float(np.median(tex[sel]))); xs_.append(r)
prof = np.array(prof)
print("\ntexture vs signed distance from the patch edge (-in .. +out):")
print("  offsets: " + " ".join("%+d" % v for v in xs_[::4]))
print("  texture: " + " ".join("%.2e" % v for v in prof[::4]))
lg = np.log10(prof + 1e-15)
st = np.abs(np.diff(lg))
print("  largest single-pixel change: %.3f in log10 (%.2fx energy)"
      % (st.max(), 10 ** st.max()))
w = float(np.sum(prof < 0.5 * (prof.min() + prof.max())))
print("  transition width at half-max: ~%d px" % w)

ratio = t_out / max(t_in, 1e-15)
print()
if ratio > 3.0:
    print("VERDICT: CONFIRMED. A %d px region carries %.1fx less detail than "
          "its surroundings while differing only %+.2f%% in brightness. The "
          "bee's eye has no such structure -- the merge elected a defocused "
          "frame there." % (area, ratio, 100 * (i_in - i_out)))
else:
    print("VERDICT: only %.2fx texture deficit. Not conclusive." % ratio)

vis = np.stack([eye] * 3, axis=-1)
edge = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT,
                        np.ones((5, 5), np.uint8)).astype(bool)
vis[edge] = np.array([1.0, 0.1, 0.1])
Image.fromarray((np.clip(vis, 0, 1) * 255).astype(np.uint8)).save(
    os.path.join(OUT, "eye-patch2.png"))
print("wrote eye-patch2.png (patch outlined)")
