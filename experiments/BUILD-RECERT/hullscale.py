"""Is the frame basis photometrically comparable to the merge?

The hull is a claim about VALUES: "the output holds a sample outside the range
of the aligned inputs at that sample". That claim is only meaningful if the
frames and the merge are on the same scale. strehl normalises tone from the
image's own statistics (p99.9 -> 0.90), so a single-frame render normalises on
THAT FRAME and a 19-frame merge normalises on the MERGE. If those gains differ,
every violation the instrument reports is a gain mismatch wearing a hull's
clothes.

This measures the ratio rather than assuming it either way.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile

H = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\hull")

m = tifffile.imread(H / "merged-default.tiff").astype(np.float64)
print(f"merge  shape={m.shape} p50={np.percentile(m, 50):9.1f} "
      f"p99.9={np.percentile(m, 99.9):9.1f} max={m.max():7.0f}")

ratios = []
for k in range(19):
    f = tifffile.imread(H / "frames" / f"f{k:04d}.tiff").astype(np.float64)
    if f.shape != m.shape:
        print(f"frame {k:2d}: SHAPE {f.shape} != merge {m.shape}")
        continue
    # Compare on the same pixels, high signal only, to avoid dividing by noise.
    mask = m[..., 1] > np.percentile(m[..., 1], 80)
    r = float(np.median(f[..., 1][mask] / np.maximum(m[..., 1][mask], 1.0)))
    ratios.append(r)
    if k < 6 or k == 18:
        print(f"frame {k:2d}: p50={np.percentile(f, 50):9.1f} "
              f"p99.9={np.percentile(f, 99.9):9.1f} max={f.max():7.0f}  "
              f"median(frame/merge) on bright pixels = {r:.4f}")

r = np.array(ratios)
print(f"\nframe/merge gain ratio over {len(r)} frames: "
      f"min={r.min():.4f} median={np.median(r):.4f} max={r.max():.4f} "
      f"spread={(r.max() - r.min()):.4f}")
if r.max() - r.min() > 0.02 or abs(np.median(r) - 1.0) > 0.02:
    print("VERDICT: the frame basis is NOT photometrically matched to the merge.")
    print("Any hull violation measured against it is uninterpretable.")
else:
    print("VERDICT: frames and merge share one scale; the hull is admissible.")
