"""How far apart are the two masks, in pixels, and why does that matter?

ORCH thresholds at 0.5*(p5+p95) of the RGB mean and keeps the largest connected
component. I use Otsu on green with the backdrop identified from the border.
The two disagree on subject area by 7.7 points of frame on coffee-bean. This
measures the disagreement where it matters: the signed distance from every
point of ORCH's boundary to my boundary.

The answer is expected to be tens of pixels, because the MERGED silhouette is
about 120 px wide from 10 to 90 percent. On an edge that soft, "the silhouette"
is not a well defined location and any mask-derived zero point is arbitrary to
a few tens of pixels. That is the root cause of both the annulus method's
smearing and the disagreement between the two masks.
"""
import gc, sys
from pathlib import Path
import numpy as np
from scipy import ndimage
import tifffile

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum, segment

SRC = r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif"

a = tifffile.imread(SRC)
assert a.dtype == np.uint16, a.dtype
mean_ch = a.astype(np.float32).mean(axis=2)
del a; gc.collect()

lo, hi = np.percentile(mean_ch, 5), np.percentile(mean_ch, 95)
thr = 0.5 * (lo + hi)
dark = mean_ch < thr
lab, n = ndimage.label(dark)
sizes = ndimage.sum(dark, lab, range(1, n + 1))
orch = lab == (int(np.argmax(sizes)) + 1)
del lab, dark; gc.collect()
print(f"ORCH rule: p5={lo:.0f} p95={hi:.0f} thr={thr:.0f}  "
      f"largest dark component = {orch.mean()*100:.2f}% of frame  ({n} components)")

shape, lum = load_lum(Path(SRC), "G")
mine, backdrop, diag = segment(lum)
print(f"V-RIM rule: Otsu on green, backdrop from border  subject = "
      f"{diag['subject_frac']*100:.2f}% of frame")

sd_mine = (ndimage.distance_transform_edt(~mine)
           - ndimage.distance_transform_edt(mine)).astype(np.float32)
er = ndimage.binary_erosion(orch, iterations=1, border_value=1)
ob = orch & ~er
ys, xs = np.nonzero(ob)
h, w = mine.shape
k = (ys > 350) & (ys < h - 350) & (xs > 350) & (xs < w - 350)
d = sd_mine[ys[k], xs[k]]
print(f"\nsigned distance from ORCH's boundary to MY boundary, over {d.size} points")
print("  (positive = ORCH's boundary lies OUTSIDE my subject, in the backdrop)")
for p in (5, 25, 50, 75, 95):
    print(f"    p{p:<3d} {np.percentile(d, p):+8.1f} px")
print(f"    mean {d.mean():+.1f} px   |median| {abs(np.median(d)):.1f} px")

print("\nluminance at each boundary, green channel")
print(f"  at ORCH's boundary : median {np.median(lum[ys[k], xs[k]]):8.0f} DN")
er2 = ndimage.binary_erosion(mine, iterations=1, border_value=1)
mb = mine & ~er2
ys2, xs2 = np.nonzero(mb)
k2 = (ys2 > 350) & (ys2 < h - 350) & (xs2 > 350) & (xs2 < w - 350)
print(f"  at MY boundary     : median {np.median(lum[ys2[k2], xs2[k2]]):8.0f} DN")
print(f"  subject interior   : median {np.median(lum[mine]):8.0f} DN")
print(f"  backdrop far field : median {np.median(lum[backdrop]):8.0f} DN")

inter = (orch & mine).sum(); union = (orch | mine).sum()
print(f"\nIoU of the two masks: {inter/union:.4f}")
print(f"area disagreement   : {abs(orch.mean()-mine.mean())*100:.2f} points of frame")
