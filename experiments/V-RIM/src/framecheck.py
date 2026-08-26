"""Are single-frame renders in the same geometry as the merge?

If the diagnostic single-frame path skips alignment, merge pixel (y,x) and frame
pixel (y,x) are not the same scene point, and any pixel-paired comparison is
measuring registration error rather than the merge. Segment each image on its
own terms and print where the subject actually sits.

Also reports clipping, because a frame whose backdrop is pinned at 65535 cannot
show a ring of any size and would read as a clean negative.
"""
import glob, gc
from pathlib import Path
import numpy as np
from scipy import ndimage
import sys
sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum, segment

files = [("MERGE", r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif")]
for p in sorted(glob.glob(r"C:\dev\strehl-out\V-RIM\cb-frame*-lin.tif")):
    if Path(p).stat().st_size > 1_000_000:
        files.append((Path(p).stem.replace("cb-", "").replace("-lin", "").upper(), p))

print("image        subj%    cy      cx    y0    y1    x0    x1   subjDN   backDN"
      "   clip%   p99.9")
rows = {}
for lab, path in files:
    shape, lum = load_lum(Path(path), "G")
    subject, backdrop, diag = segment(lum)
    ys, xs = np.nonzero(subject)
    cy, cx = ys.mean(), xs.mean()
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    sdn = float(np.median(lum[subject])); bdn = float(np.median(lum[backdrop]))
    clip = float((lum >= 65535).mean() * 100)
    p999 = float(np.percentile(lum, 99.9))
    print(f"{lab:11s} {diag['subject_frac']*100:6.2f} {cy:7.0f} {cx:7.0f} "
          f"{y0:5d} {y1:5d} {x0:5d} {x1:5d} {sdn:8.0f} {bdn:8.0f} {clip:7.3f} {p999:7.0f}")
    rows[lab] = subject
    del lum, backdrop; gc.collect()

print()
print("mask agreement with MERGE (IoU) and best integer shift found by")
print("maximising overlap over a +-160 px search on a 4x-downsampled mask:")
m = rows["MERGE"][::4, ::4]
for lab in rows:
    if lab == "MERGE":
        continue
    f = rows[lab][::4, ::4]
    inter = (m & f).sum(); union = (m | f).sum()
    best = (-1, 0, 0)
    for dy in range(-40, 41, 2):
        for dx in range(-40, 41, 2):
            fs = np.roll(np.roll(f, dy, axis=0), dx, axis=1)
            o = int((m & fs).sum())
            if o > best[0]:
                best = (o, dy, dx)
    print(f"  {lab:9s} IoU={inter/union:6.4f}   best shift (4x px) dy={best[1]:+4d} "
          f"dx={best[2]:+4d} -> full-res dy={best[1]*4:+5d} dx={best[2]*4:+5d}  "
          f"overlap gain={best[0]/max(inter,1):.4f}x")
