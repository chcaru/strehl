"""Does restoring the shrink reintroduce the halo? Measure the aura directly.

The parent render IS the shrink-restored state, so the two pinned renders
answer the revert-risk question without building anything further.

A veiling halo is elevated BACKGROUND luminance hugging the silhouette and
decaying outward. Segment subject from background, distance-transform into
the background, and read mean luminance against distance for both arms.
"""
import sys
import numpy as np, tifffile
from pathlib import Path
from scipy.ndimage import distance_transform_edt, binary_opening, uniform_filter

OUT = Path(r"C:\dev\strehl-out\V-softness")
SUBJ = sys.argv[1] if len(sys.argv) > 1 else "bee-1-cpl"

def load(sha):
    a = tifffile.imread(OUT / f"{SUBJ}-{sha}.tif")
    assert a.dtype == np.uint16
    return a.astype(np.float64).mean(2)

yp, yc = load("526c727"), load("57e4554")

# background = bright side of an Otsu-ish split on a smoothed frame
s = uniform_filter((yp + yc) / 2.0, 15)
lo, hi = np.percentile(s, [2, 98])
bins = np.linspace(lo, hi, 256)
h, _ = np.histogram(s, bins=bins)
p = h / h.sum(); c = np.cumsum(p); mids = 0.5 * (bins[:-1] + bins[1:])
mu = np.cumsum(p * mids); mut = mu[-1]
with np.errstate(invalid="ignore", divide="ignore"):
    var = (mut * c - mu) ** 2 / (c * (1 - c))
thr = mids[int(np.nanargmax(var))]
bg = binary_opening(s > thr, np.ones((9, 9)))
subj = binary_opening(s <= thr, np.ones((9, 9)))
print(f"{SUBJ}: threshold {thr:.0f} DN   subject {100*subj.mean():.1f}%   background {100*bg.mean():.1f}%")

dist = distance_transform_edt(~subj)
print("\n dist from silhouette | parent(shrink ON)   child(shrink OFF)   child-parent")
print(" " + "-" * 70)
far = bg & (dist > 150)
fp, fc = yp[far].mean(), yc[far].mean()
print(f" far field >150 px     {fp:14.1f} {fc:18.1f} {fc-fp:+14.1f}   (reference level)")
for a, b in [(2,6),(6,12),(12,20),(20,32),(32,50),(50,80),(80,120)]:
    sel = bg & (dist >= a) & (dist < b)
    if sel.sum() < 500: continue
    mp, mc = yp[sel].mean(), yc[sel].mean()
    print(f" {a:3d}-{b:3d} px  n={int(sel.sum()):8d} {mp:10.1f} {mc:18.1f} {mc-mp:+14.1f}")

print("\n excess over far field (the halo itself):")
print(" dist        parent excess    child excess    child better by")
print(" " + "-" * 62)
for a, b in [(2,6),(6,12),(12,20),(20,32),(32,50),(50,80)]:
    sel = bg & (dist >= a) & (dist < b)
    if sel.sum() < 500: continue
    ep, ec = yp[sel].mean() - fp, yc[sel].mean() - fc
    print(f" {a:3d}-{b:3d} px {ep:14.1f} {ec:15.1f} {ep-ec:+18.1f}")
print("\n POSITIVE 'child better by' = deleting the shrink REDUCED the halo,")
print(" i.e. restoring it would reintroduce that much aura. Negative = no halo cost.")
