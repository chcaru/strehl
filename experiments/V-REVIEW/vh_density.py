"""Set the cell-pinch threshold from all 26 subjects, not from the two that
showed the artifact.

Band populations are not comparable directly: the NEAR bands are 4,6,8,12,18,30
and 40 px wide, so a wider band holds more pixels for the same geometry.  What
is comparable is DENSITY per unit distance.  For a well-formed cell it is flat
or slowly falling (perimeter grows with distance, offsetting the cell
narrowing).  When the dominant part's cell pinches off, density collapses and
the surviving pixels are a directional sliver whose median is not the
background level at that distance.
"""
import glob, os, sys
import numpy as np
from scipy.ndimage import distance_transform_edt, label

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H
CACHE = r"D:\strehl-out\V-REVIEW\halo\cache"

print("per-unit-width band density, normalised to the innermost band (=1.00)")
print("%-38s %s  %8s" % ("subject", "  ".join("%6s" % ("%d-%d" % b) for b in H.NEAR), "min/first"))
print("-" * 128)
rows = []
for f in sorted(glob.glob(os.path.join(CACHE, "*.npy"))):
    stem = os.path.basename(f)[:-4].replace(".tiff", "")
    y = np.load(f)[::2, ::2]
    t, subj = H.segment(y)
    lab, nlab = label(subj)
    if nlab < 1:
        continue
    sizes = np.bincount(lab.ravel())[1:]
    dom = int(np.argmax(sizes)) + 1
    d, ind = distance_transform_edt(~subj, return_indices=True)
    d *= 4
    own = (lab[ind[0], ind[1]] == dom) & (~subj)
    dens = []
    for lo, hi in H.NEAR:
        n = int((own & (d >= lo) & (d < hi)).sum())
        dens.append(n / float(hi - lo))
    if dens[0] <= 0:
        continue
    r = [x / dens[0] for x in dens]
    rows.append((stem, r))
    print("%-38s %s  %8.3f"
          % (stem, "  ".join("%6.2f" % x for x in r), min(r)))

print("-" * 128)
print("A pinching cell shows a steep monotone collapse; a well-formed one stays")
print("near 1.  The two subjects whose profile spiked (leaf-2-cpl, lead-1-cpl)")
print("are the two lowest, and the separation from the rest is what sets the bar.")
srt = sorted(rows, key=lambda r: min(r[1]))
print("\nranked by min density ratio:")
for stem, r in srt[:8]:
    print("  %-38s %.3f" % (stem, min(r)))
print("  ...")
for stem, r in srt[-3:]:
    print("  %-38s %.3f" % (stem, min(r)))
