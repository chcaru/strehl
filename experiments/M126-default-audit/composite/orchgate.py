"""M126: measure ORCH's own two ORCH-GATE artefacts with a strict reader.

ORCH reports for 109MSDCF gate 4.5 vs compiled default, same pinned binary:
  97.359% of samples differ, peak 21.1% of full scale, rms 0.41%.
My own linear binned renders of the same two configurations give
  87.813% differ, peak 1.386%, rms 0.0672%.
This script settles the discrepancy against the artefacts themselves.
Chunked so two ~198 MB frames never co-exist as float64.
"""
import numpy as np
import tifffile  # hard import -- no PIL fallback

A = r"C:\dev\strehl-out\ORCH-GATE\a-g45.tiff"
B = r"C:\dev\strehl-out\ORCH-GATE\b-default.tiff"
FS = 65535.0

ta, tb = tifffile.TiffFile(A), tifffile.TiffFile(B)
pa, pb = ta.pages[0], tb.pages[0]
print(f"a-g45     : shape={pa.shape} dtype={pa.dtype}")
print(f"b-default : shape={pb.shape} dtype={pb.dtype}")
assert pa.dtype == np.uint16 and pb.dtype == np.uint16, "expected uint16"
assert pa.shape == pb.shape

xa = ta.asarray()
xb = tb.asarray()
assert xa.dtype == np.uint16 and xb.dtype == np.uint16

n = 0
ndiff = 0
sse = 0.0
peak = 0
rows = xa.shape[0]
step = 256
for y in range(0, rows, step):
    ca = xa[y:y + step].astype(np.int32)
    cb = xb[y:y + step].astype(np.int32)
    d = ca - cb
    n += d.size
    ndiff += int((d != 0).sum())
    sse += float((d.astype(np.float64) ** 2).sum())
    peak = max(peak, int(np.abs(d).max()))

print()
print(f"samples        : {n}")
print(f"%% differing    : {ndiff / n * 100:.3f}   (ORCH: 97.359)")
print(f"rms %% of FS    : {np.sqrt(sse / n) / FS * 100:.4f}   (ORCH: 0.41)")
print(f"peak %% of FS   : {peak / FS * 100:.3f}   (ORCH: 21.1)")
