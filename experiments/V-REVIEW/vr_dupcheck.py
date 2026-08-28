"""Are the two foam renders the same image? Compare DECODED ARRAYS.

A file hash cannot answer this: TIFF ImageDescription records the tool's own
parameters, so two byte-different files can hold identical pixels.  That trap
already produced one false acquittal in this lane.
"""
import numpy as np, tifffile, os
A = r"C:\dev\strehl-out\V-REVIEW\foam--f0050.tiff"
B = r"C:\dev\strehl-out\V-REVIEW\foam--f050.tiff"
for p in (A, B):
    print(f"{os.path.basename(p):22} {os.path.getsize(p):,} bytes")
a, b = tifffile.imread(A), tifffile.imread(B)
print(f"shapes {a.shape} {b.shape}  dtypes {a.dtype} {b.dtype}")
if a.shape != b.shape:
    print("VERDICT: different shape -> NOT duplicates"); raise SystemExit
same = np.array_equal(a, b)
print(f"np.array_equal on decoded pixels : {same}")
if not same:
    d = np.abs(a.astype(np.int64) - b.astype(np.int64))
    print(f"  differing pixels {int((d>0).sum()):,} of {d.size:,}  max |diff| {int(d.max())}")
print("VERDICT:", "DUPLICATE renders, one is redundant" if same else "genuinely different renders")
