"""Does `--linear-srgb` put single-frame renders on the merge's own scale?

The bare default does not: measured over 19 frames of coffee-bubbles the
frame/merge gain ran min 0.8168, median 0.8503, max 0.9459 -- a 12.9% spread,
because strehl normalises tone from each image's OWN p99.9. A hull taken across
that is measuring the normaliser, not the merge.

`image_out.rs` carries a unit test literally named
`tone_rides_with_the_viewing_render_and_never_with_a_measurement`, and
`--linear-srgb`'s help says "THIS IS THE MODE TO MEASURE IN". This checks
whether that is true of the SCALE, which is the property the hull needs, rather
than assuming it from the name.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile

T = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\hull\lintest")

m = tifffile.imread(T / "merged-lin.tiff").astype(np.float64)
print(f"merge --linear-srgb: shape={m.shape} p50={np.percentile(m, 50):8.1f} "
      f"p99.9={np.percentile(m, 99.9):8.1f}")

mask = m[..., 1] > np.percentile(m[..., 1], 80)
rs = []
for k in (0, 1, 4):
    f = tifffile.imread(T / f"f{k:04d}-lin.tiff").astype(np.float64)
    r = float(np.median(f[..., 1][mask] / np.maximum(m[..., 1][mask], 1.0)))
    rs.append(r)
    print(f"frame {k}: p99.9={np.percentile(f, 99.9):8.1f}  "
          f"median(frame/merge) on bright pixels = {r:.4f}")

r = np.array(rs)
spread = float(r.max() - r.min())
print(f"\nspread across frames = {spread:.4f}   median offset from 1.0 = "
      f"{abs(np.median(r) - 1.0):.4f}")
print("bare-default comparison: spread 0.1291, median offset 0.1497")
if spread < 0.02 and abs(np.median(r) - 1.0) < 0.02:
    print("VERDICT: --linear-srgb shares one scale. The hull is admissible here.")
else:
    print("VERDICT: --linear-srgb does NOT fix the scale. The hull cannot be")
    print("measured on this path without a photometric correction, and applying")
    print("one would be fitting away the very excursions the hull exists to find.")
