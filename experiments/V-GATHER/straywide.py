r"""Widen the stray-equivalence test to more subjects, against the shipped
masters themselves rather than a re-render of the reference.

Scope note that limits every number below: three probes have now shown that the
two SEALED pins produce bit-identical masters on all 26 subjects, so this
comparison has no demonstrated power to separate two strehl builds. What it CAN
do is separate two pipelines -- the gather flag moves 99.8% of pixels through the
same comparison. So a zero here means "indistinguishable by an instrument known
to respond to a real pipeline change", which is weaker than "identical builds"
and is the strongest thing the assets support.
"""
import os
import numpy as np
import tifffile

D = r"C:\dev\strehl-out\V-GATHER\strayprobe"
V4 = r"C:\dev\strehl-out\acceptance\SHIP-V4"
PAIRS = [("wrapped-text-1", os.path.join(D, "STRAY.tiff")),
         ("foam", os.path.join(D, "foam--STRAY.tiff")),
         ("coffee-bean", os.path.join(D, "coffee-bean--STRAY.tiff"))]

print("%-18s %14s %8s %s" % ("subject", "differing px", "max DN", "verdict"))
print("-" * 62)
same = diff = skip = 0
for s, p in PAIRS:
    m = os.path.join(V4, "%s--SHIP-V4.tiff" % s)
    if not (os.path.exists(p) and os.path.exists(m)):
        print("%-18s %14s %8s %s" % (s, "-", "-", "SKIP missing")); skip += 1; continue
    a = tifffile.imread(p)[..., :3].astype(np.int32)
    b = tifffile.imread(m)[..., :3].astype(np.int32)
    if a.shape != b.shape:
        print("%-18s %14s %8s %s" % (s, "-", "-", "SKIP shape")); skip += 1; continue
    d = np.abs(a - b)
    n = int((d > 0).sum())
    if n:
        diff += 1
    else:
        same += 1
    print("%-18s %14d %8d %s" % (s, n, d.max(), "identical" if n == 0 else "DIFFERS"))

print("\nPARTITION  identical %d + differing %d + skipped %d = %d of %d"
      % (same, diff, skip, same + diff + skip, len(PAIRS)))
print("UNMEASURED: %d of the 26 sealed subjects were not rendered with the stray."
      % (26 - same - diff))
