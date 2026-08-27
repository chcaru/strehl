import numpy as np, sys
sys.path.insert(0, ".")
import banding as B
d = np.diff(B.LSTAR)
print("dL* per 8-bit sRGB code, over the whole scale:")
for lo, hi in ((1, 16), (16, 32), (32, 64), (64, 128), (128, 192), (192, 255)):
    seg = d[lo:hi]
    print(f"  codes {lo:>3}-{hi:<3}  min {seg.min():.3f}  med {np.median(seg):.3f}  max {seg.max():.3f}")
print(f"  GLOBAL codes 1-255: min {d[1:].min():.3f}  max {d[1:].max():.3f}")
print(f"  codes with dL* >= 0.50 : {int((d[1:] >= 0.50).sum())} of 254")
print(f"  codes with dL* >= 0.30 : {int((d[1:] >= 0.30).sum())} of 254")
print(f"  codes with dL* >= 0.25 : {int((d[1:] >= 0.25).sum())} of 254")
