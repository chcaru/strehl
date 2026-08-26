"""Did the HEAD fix RESTORE the shadow detail, or just move it off zero?
Compare, at the exact sites the old build clamped, what each build reads.
"""
import numpy as np, tifffile
L = r"C:\dev\strehl-out\V-BLEND\lin"
s = "flower-bud-alone-cpl"
old = tifffile.imread(f"{L}\\{s}-after.tiff")[:, :, 2].astype(np.float32)
new = tifffile.imread(f"{L}\\{s}-after-275fbd1.tiff")[:, :, 2].astype(np.float32)
bef = tifffile.imread(f"{L}\\{s}-before.tiff")[:, :, 2].astype(np.float32)
z = (old == 0)
n = int(z.sum())
print(f"sites the 0d9fd28 build clamped to exactly 0 (blue): {n:,}\n")
print(f"  {'arm':<28} {'median':>10} {'p10':>10} {'p90':>10} {'% at 0':>9}")
for lbl, a in (("0d9fd28 AFTER (clamped)", old), ("275fbd1 AFTER (hull fix)", new),
               ("BEFORE (ship path)", bef)):
    v = a[z]
    print(f"  {lbl:<28} {np.median(v):10.0f} {np.percentile(v,10):10.0f} "
          f"{np.percentile(v,90):10.0f} {100.0*(v==0).mean():8.3f}%")
d = new[z]-bef[z]
print(f"\n  275fbd1 minus BEFORE at those sites: median {np.median(d):+.0f} DN, "
      f"p10 {np.percentile(d,10):+.0f}, p90 {np.percentile(d,90):+.0f}")
print(f"  fraction where 275fbd1 now reads within +/-30% of BEFORE: "
      f"{100.0*np.mean(np.abs(d) <= 0.30*np.maximum(bef[z],1)):.1f}%")
print(f"\n  whole-frame minimum, 275fbd1: R/G/B ->", end=" ")
im = tifffile.imread(f"{L}\\{s}-after-275fbd1.tiff")
print(", ".join(str(int(im[:, :, c].min())) for c in range(3)))
