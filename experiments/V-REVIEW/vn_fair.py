"""ORCH item 5 done properly: were the comparators fed the same bytes?

DISCLOSURE 2. vn_boot.py computed `100 * a.max() / full` on a numpy uint16
scalar. `100 * 65535` overflows uint16 and the line printed "65535 = 1.0% of
range" for a full-range image. The conclusion I drew from it happened to be
correct, but it was NOT supported by the number I printed -- an argued
conclusion wearing a measured number's clothes. Cast to float here.
"""
import os, glob, hashlib, json
import numpy as np, tifffile

V = r"C:\dev\strehl-out\V-LINEAR2"
print("=" * 78)
print("WHAT EACH ARM WAS FED")
print("=" * 78)
for d in ("aligned", "pilot", "out", "fs15"):
    p = os.path.join(V, d)
    if not os.path.isdir(p): continue
    fs = sorted(glob.glob(os.path.join(p, "*.tif*")))
    print("  %-9s %4d tif  %s" % (d, len(fs),
          os.path.basename(fs[0]) if fs else ""))
al = sorted(glob.glob(os.path.join(V, "aligned", "*.tif*")))
print()
if al:
    print("  aligned/ frame count %d" % len(al))
    a = tifffile.imread(al[0])
    full = 255.0 if a.dtype == np.uint8 else 65535.0
    print("  aligned/ frame 0  %s shape %s dtype %s  max %d = %.1f%% of range"
          % (os.path.basename(al[0]), a.shape, a.dtype, int(a.max()),
             100.0 * float(a.max()) / full))
    del a

print()
print("=" * 78)
print("BYTE-IDENTITY  the property that makes the comparison worth anything")
print("=" * 78)
logs = sorted(glob.glob(os.path.join(V, "logs", "*")))
print("  logs/ entries: %d" % len(logs))
for lg in logs[:20]:
    print("    %s (%d bytes)" % (os.path.basename(lg), os.path.getsize(lg)))
cm = os.path.join(V, "commitmsg.txt")
if os.path.isfile(cm):
    print()
    print("  commitmsg.txt says:")
    for ln in open(cm, encoding="utf-8", errors="replace").read().splitlines()[:40]:
        print("    | " + ln)

print()
print("=" * 78)
print("RANGE FAIRNESS, corrected arithmetic")
print("=" * 78)
ARM = {
 "strehl-A": r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff",
 "strehl-B": r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff",
 "enfuse-A": r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif",
 "enfuse-B": r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-B.tif",
 "fs15-A": r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif",
 "fs15-B": r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-B.tif",
}
print("  %-10s %-8s %2s %8s %8s %8s %9s"
      % ("arm", "dtype", "pl", "max", "%range", "mean", "p99.9"))
for k, p in ARM.items():
    a = tifffile.imread(p)
    full = 255.0 if a.dtype == np.uint8 else 65535.0
    b = a[:, :, :3].astype(np.float64)
    print("  %-10s %-8s %2d %8d %7.1f%% %8.4f %9.4f"
          % (k, a.dtype, a.shape[2], int(a.max()), 100.0 * float(a.max()) / full,
             b.mean() / full, np.percentile(b, 99.9) / full))
    del a, b
print()
print("  All six reach 100.0%% of their container's range, so no arm is clipped")
print("  low or floored high by the harness. focus-stack's container is 8-bit,")
print("  which is a property of the TOOL -- it emits uint8 -- not of the")
print("  harness, and it is the reason a quantisation penalty must be removed")
print("  before its ratios can be read as an algorithm comparison.")

print()
print("=" * 78)
print("THE 8-BIT PENALTY  as stated vs as applied in M127")
print("=" * 78)
raw = {"Y": 1.269, "R-Y": 2.211, "B-Y": 2.530}
cor = {"Y": 1.161, "R-Y": 2.028, "B-Y": 2.237}
sta = {"Y": 1.124, "R-Y": 1.333, "B-Y": 1.548}
mine = {"Y": 1.167, "R-Y": 1.390, "B-Y": 1.596}
myraw = {"Y": 1.270, "R-Y": 2.256, "B-Y": 2.596}
print("  %-5s %8s %8s %11s %10s %10s %11s"
      % ("chan", "M127raw", "M127cor", "implied", "stated", "mine", "mine->cor"))
for ch in ("Y", "R-Y", "B-Y"):
    print("  %-5s %8.3f %8.3f %11.3f %10.3f %10.3f %11.3f"
          % (ch, raw[ch], cor[ch], raw[ch] / cor[ch], sta[ch], mine[ch],
             myraw[ch] / mine[ch]))
print()
print("  'implied' is the factor M127's own corrected column actually divides")
print("  by. 'stated' is the QUANT8 penalty M127's control table reports")
print("  measuring. On chroma they disagree by a wide margin -- 1.090 applied")
print("  against 1.333 measured, and 1.131 applied against 1.548 measured.")
print("  M127 UNDER-APPLIES the penalty it measured, and under-applying it")
print("  overstates focus-stack's chroma disadvantage. Direction of the error")
print("  is in strehl's favour.")
