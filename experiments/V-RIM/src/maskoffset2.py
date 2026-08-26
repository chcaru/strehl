"""Outer-silhouette comparison only: fill both masks before comparing.

The first version measured every boundary pixel of ORCH's mask, and ORCH's mask
has about 3500 interior holes, so most of those points were hole rims a thousand
pixels inside the bean. Filling both masks first restricts the comparison to the
one boundary either method claims to be the silhouette.
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
orch_f = ndimage.binary_fill_holes(orch)
print(f"ORCH thr={thr:.0f}  raw largest component {orch.mean()*100:.2f}%  "
      f"holes filled {orch_f.mean()*100:.2f}%  (holes = {(orch_f & ~orch).sum()} px)")

shape, lum = load_lum(Path(SRC), "G")
mine, backdrop, diag = segment(lum)
print(f"V-RIM subject {diag['subject_frac']*100:.2f}%   "
      f"IoU(filled ORCH, mine) = {(orch_f & mine).sum()/(orch_f | mine).sum():.4f}")

sd = (ndimage.distance_transform_edt(~mine)
      - ndimage.distance_transform_edt(mine)).astype(np.float32)
ob = orch_f & ~ndimage.binary_erosion(orch_f, iterations=1, border_value=1)
ys, xs = np.nonzero(ob)
h, w = mine.shape
k = (ys > 350) & (ys < h - 350) & (xs > 350) & (xs < w - 350)
d = sd[ys[k], xs[k]]
print(f"\nsigned distance from ORCH's OUTER silhouette to mine, {d.size} points")
print("  positive = ORCH's silhouette lies outside my subject")
for p in (5, 25, 50, 75, 95):
    print(f"    p{p:<3d} {np.percentile(d, p):+8.1f} px")
print(f"    mean {d.mean():+.1f} px")
print(f"\n  luminance at ORCH's outer silhouette: median "
      f"{np.median(lum[ys[k], xs[k]]):.0f} DN  (its threshold, in mean ch, is {thr:.0f})")
mb = mine & ~ndimage.binary_erosion(mine, iterations=1, border_value=1)
ys2, xs2 = np.nonzero(mb)
k2 = (ys2 > 350) & (ys2 < h - 350) & (xs2 > 350) & (xs2 < w - 350)
print(f"  luminance at my silhouette          : median "
      f"{np.median(lum[ys2[k2], xs2[k2]]):.0f} DN")
print(f"\n  the merged 10-90 edge width measured by ray registration is 120.6 px,")
print(f"  so a disagreement of this size is what two different thresholds on a")
print(f"  120 px ramp are expected to produce.")
