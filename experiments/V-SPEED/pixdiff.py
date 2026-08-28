"""Do two masters differ in PIXELS, or only in metadata?

A byte hash over a TIFF answers the wrong question when the writer stamps a
version string into the header: the inertness check compared file hashes and
read FAIL, but the two binaries report different git hashes (649e35620f02 vs
6341a7a4b7e9), so a metadata-only difference would produce exactly that
result. Reporting "the change alters output" on a file hash, when 0 samples
actually differ, is the same defect ORCH described clearing an --exposure
issue on a file hash.

So: compare the arrays, and if they differ, say by how much and where.
"""

import pathlib
import sys

import numpy as np
import tifffile

A, B = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
a, b = tifffile.imread(str(A)), tifffile.imread(str(B))

print(f"A {A.name}  shape {a.shape} dtype {a.dtype}")
print(f"B {B.name}  shape {b.shape} dtype {b.dtype}")

if a.shape != b.shape or a.dtype != b.dtype:
    print("\nVERDICT: shape/dtype differ -- a real difference")
    sys.exit(1)

same = np.array_equal(a, b)
d = a.astype(np.int64) - b.astype(np.int64)
n = int((d != 0).sum())
print(f"\nsamples total     {a.size:,}")
print(f"samples differing {n:,}  ({100.0 * n / a.size:.6f}%)")
if n:
    print(f"max |difference|  {int(np.abs(d).max())} DN")
    print(f"mean |difference| {float(np.abs(d).mean()):.6f} DN")

# File-level bytes, for the contrast that makes the point.
ha = A.read_bytes()
hb = B.read_bytes()
print(f"\nfile sizes        {len(ha):,} vs {len(hb):,}")
first = next((i for i, (x, y) in enumerate(zip(ha, hb)) if x != y), None)
print(f"first byte differs at offset {first}" if first is not None
      else "files are byte-identical")

if same:
    print("\nVERDICT: PIXEL-IDENTICAL. The file hashes differ only in metadata,")
    print("so the code change is INERT on output. A byte hash would have")
    print("reported a regression that does not exist.")
    sys.exit(0)
print("\nVERDICT: pixels genuinely differ.")
sys.exit(1)
