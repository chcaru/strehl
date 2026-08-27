"""How far is the unsealed stray F663B703 from the shipping pin 9b05d0b7?

Twelve scripts in this lane rendered through the stray. Both arms of every A/B
came from it, so those comparisons remain valid arm-versus-arm -- that was the
design requirement and it held. The question here is narrower and it decides how
hard the rescope has to be: is the stray a cosmetically different build of the
same pipeline, or a materially different one?

Same subject, same binary invocation, same pinned exposure, same flags, fresh
cache on the stray side so the whole pipeline runs rather than replaying a solve.
"""
import numpy as np
import tifffile

A = r"C:\dev\strehl-out\acceptance\SHIP-V4\wrapped-text-1--SHIP-V4.tiff"
B = r"C:\dev\strehl-out\V-GATHER\strayprobe\STRAY.tiff"

a = tifffile.imread(A)[..., :3]
b = tifffile.imread(B)[..., :3]
print("shipping 9b05d0b7 %s %s" % (a.shape, a.dtype))
print("stray    F663B703 %s %s" % (b.shape, b.dtype))
if a.shape != b.shape:
    raise SystemExit("different output dimensions -- materially different build")
d = np.abs(a.astype(np.int32) - b.astype(np.int32))
tot = d.size
print("\ndiffering pixels %d of %d  (%.2f%%)" % (int((d > 0).sum()), tot, 100.0 * (d > 0).mean()))
print("max |diff|   %d DN of 65535  (%.3f%% of full scale)" % (d.max(), 100.0 * d.max() / 65535))
print("mean |diff|  %.2f DN" % d.mean())
for p in (50, 90, 99, 99.9):
    print("  p%-5s %6.1f DN" % (p, np.percentile(d, p)))
big = int((d > 655).sum())
print("\npixels differing by more than 1%% of full scale: %d (%.4f%%)"
      % (big, 100.0 * big / tot))
