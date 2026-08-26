"""Does rimprofile.py's mask have holes, and do those holes put bean-interior
pixels into the 'backdrop profile'?

Reproduces the instrument's OWN mask rule verbatim, then asks one question:
what fraction of the pixels it profiles at each distance actually lie inside
the subject's outer silhouette? Any answer above zero means the profile is a
mixture of backdrop and subject interior.
"""
import sys
import numpy as np
import tifffile
from scipy import ndimage

SRC = sys.argv[1]
LABEL = sys.argv[2]

img = tifffile.imread(SRC)
assert img.dtype == np.uint16
a = img.astype(np.float32)
lum = a.mean(axis=2)          # ORCH's channel
del img, a

lo, hi = np.percentile(lum, [5, 95])
thr = 0.5 * (lo + hi)
subject = lum < thr
print(f"{LABEL}: ORCH rule  p5={lo:.0f} p95={hi:.0f} thr={thr:.0f}")
print(f"  raw dark fraction            {subject.mean()*100:.2f}%")
lab, n = ndimage.label(subject)
sizes = ndimage.sum(subject, lab, range(1, n + 1))
orch = lab == (1 + int(np.argmax(sizes)))
print(f"  largest of {n} components     {orch.mean()*100:.2f}%   <-- ORCH's mask")

filled = ndimage.binary_fill_holes(orch)
print(f"  same mask with holes filled  {filled.mean()*100:.2f}%")
holes = filled & ~orch
print(f"  HOLE AREA inside silhouette  {holes.mean()*100:.2f}% of frame "
      f"= {holes.sum()} px")
hl, hn = ndimage.label(holes)
if hn:
    hs = ndimage.sum(holes, hl, range(1, hn + 1))
    print(f"  number of holes              {hn}, largest {int(hs.max())} px, "
          f"holes over 1000 px: {int((hs>1000).sum())}")

d_out = ndimage.distance_transform_edt(~orch)
d_in = ndimage.distance_transform_edt(orch)
signed = d_out - d_in
print()
print("  ORCH bin      n px      % of those px INSIDE the outer silhouette")
edges = [0, 4, 8, 12, 16, 20, 25, 30, 40, 50, 65, 80, 100, 125, 150,
         200, 250, 300, 400, 500, 600]
for i in range(len(edges) - 1):
    m = (signed >= edges[i]) & (signed < edges[i + 1])
    c = int(m.sum())
    if c < 500:
        continue
    inside = int((m & filled).sum())
    v_all = float(np.median(lum[m]))
    mo = m & ~filled
    v_out = float(np.median(lum[mo])) if int(mo.sum()) > 100 else float("nan")
    mi = m & filled
    v_in = float(np.median(lum[mi])) if int(mi.sum()) > 100 else float("nan")
    print(f"  {edges[i]:4d}-{edges[i+1]:<4d} {c:9d}   {inside/c*100:6.2f}%   "
          f"median all={v_all:8.0f}  backdrop-only={v_out:8.0f}  "
          f"inside-only={v_in:8.0f}")

far = (signed > 600) & (signed < 1400)
ref = float(np.median(lum[far]))
farc = far & ~filled
refc = float(np.median(lum[farc]))
print()
print(f"  far-field 600-1400 as ORCH computes it        {ref:8.0f}")
print(f"  far-field 600-1400 restricted to real backdrop {refc:8.0f}")
print(f"  fraction of that band inside the silhouette   "
      f"{(far & filled).sum()/far.sum()*100:.2f}%")
