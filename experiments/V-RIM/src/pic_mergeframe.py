"""Merge versus the in-focus frame, same crop, same linear stretch.

Both panels get IDENTICAL linear display limits and no gamma, because a tone
curve exaggerates edge artifacts and the point here is what is actually in the
linear data. The crop is centred on a straight section of silhouette chosen by
fringe index, not by eye, so the region is not cherry-picked for the artifact.
"""
import gc, sys
from pathlib import Path
import numpy as np
from scipy import ndimage
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum, segment
from vrim_rays import fringe_index

MERGE = r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif"
FRAME = r"C:\dev\strehl-out\V-RIM\cb-frame52-lin.tif"
VMIN, VMAX = 30000.0, 63000.0
HH, HW = 340, 560

shape, lum_m = load_lum(Path(MERGE), "G")
subject, backdrop, diag = segment(lum_m)
fi, bnd = fringe_index(subject)
h, w = subject.shape
ys, xs = np.nonzero(bnd)
keep = (ys > 700) & (ys < h - 700) & (xs > 700) & (xs < w - 700)
ys, xs = ys[keep], xs[keep]
fv = fi[ys, xs]

sd = (ndimage.distance_transform_edt(~subject)
      - ndimage.distance_transform_edt(subject)).astype(np.float32)
sm = ndimage.gaussian_filter(sd, 4.0)
gy, gx = np.gradient(sm)
n = np.sqrt(gy * gy + gx * gx) + 1e-6
gy /= n; gx /= n
del sm, n; gc.collect()

# straight section whose outward normal is close to horizontal, so the edge is
# vertical in the crop and the ring reads as a band rather than a curve
straight = fv <= np.percentile(fv, 5)
horiz = np.abs(gx[ys, xs]) > 0.97
cand = np.nonzero(straight & horiz)[0]
print(f"boundary points: {ys.size}   straight&horizontal candidates: {cand.size}")
i = cand[len(cand) // 2]
cy, cx = int(ys[i]), int(xs[i])
print(f"crop centre y={cy} x={cx}  fringe index={fv[i]:.3f}  normal=({gy[ys[i],xs[i]]:+.2f},{gx[ys[i],xs[i]]:+.2f})")

sl = (slice(cy - HH, cy + HH), slice(cx - HW, cx + HW))
crop_m = lum_m[sl].astype(np.float32)
del lum_m, subject, backdrop, fi, bnd, sd; gc.collect()
_, lum_f = load_lum(Path(FRAME), "G")
crop_f = lum_f[sl].astype(np.float32)
del lum_f; gc.collect()

def stretch(a):
    return np.clip((a - VMIN) / (VMAX - VMIN), 0, 1)

fig = plt.figure(figsize=(15.5, 9.2), dpi=110)
ax1 = fig.add_subplot(2, 2, 1); ax2 = fig.add_subplot(2, 2, 2)
ax3 = fig.add_subplot(2, 1, 2)
for ax, a, t in ((ax1, crop_m, "MERGED OUTPUT  (all 105 frames)"),
                 (ax2, crop_f, "SINGLE FRAME 52  (silhouette in focus)")):
    ax.imshow(stretch(a), cmap="gray", vmin=0, vmax=1, interpolation="nearest")
    ax.set_title(t, fontsize=12)
    ax.set_xticks([]); ax.set_yticks([])
ax1.text(0.02, 0.04, f"identical linear stretch {VMIN:.0f}-{VMAX:.0f} DN, no gamma",
         transform=ax1.transAxes, color="yellow", fontsize=9)

row = slice(HH - 60, HH + 60)
pm = np.median(crop_m[row], axis=0)
pf = np.median(crop_f[row], axis=0)
xax = np.arange(pm.size) - HW
ax3.plot(xax, pm, lw=1.6, label="merged output")
ax3.plot(xax, pf, lw=1.6, label="single frame 52 (in focus)")
ax3.set_xlabel("pixels across the silhouette (negative = inside the bean)")
ax3.set_ylabel("linear DN, green channel")
ax3.set_title("Median row profile through the same crop. The merged edge is soft and "
              "overshoots; the in-focus frame is monotone.", fontsize=11)
ax3.grid(alpha=0.3); ax3.legend(loc="lower right")
fig.tight_layout()
out = r"C:\dev\strehl-out\V-RIM\pics\merge-vs-frame52.png"
Path(out).parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out)
print("wrote", out)
