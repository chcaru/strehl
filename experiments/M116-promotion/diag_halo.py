"""Diagnostic: what does the registered halo index actually see?

Prints the radial background profile L(d)/L_far - 1 for the H0 and H1 arms, the
band populations, and where the treated pixels fall relative to the
fine-structure window. Read before interpreting any dHALO% number.
"""

import json
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

import score as S
import score_halo as H

HALO = Path(r"C:\dev\strehl-out\M116\halo")
SUBJ = "bee-3-cpl"

sc = json.loads((HALO / "scores-halo.json").read_text())
rec = sc["subjects"][SUBJ]

print("mask:", rec["mask"])
for a in ["H0", "H1"]:
    h = rec["arms"][a]["halo"]
    print(f"{a}: H={h['H']:+.5f}  L_far={h['L_far']:.1f} "
          f"near_px={h['near_px']:,} far_px={h['far_px']:,}")

print("\n  d   H0 profile   H1 profile      delta      band px")
p0 = {r: (v, n) for r, v, n in rec["arms"]["H0"]["profile"]}
p1 = {r: (v, n) for r, v, n in rec["arms"]["H1"]["profile"]}
for r in sorted(p0):
    v0, n0 = p0[r]
    v1, _ = p1.get(r, (float("nan"), 0))
    print(f"{r:3d}   {v0:+10.5f}   {v1:+10.5f}   {v1 - v0:+10.5f}   {n0:9,}")

# Where does the correction actually act, and does the fine window see it?
g0 = S.green(HALO / "measure" / f"{SUBJ}__H0.tif")
fg, _ = H.foreground_mask(g0)
a0 = tifffile.imread(HALO / "measure" / f"{SUBJ}__H0.tif")
a1 = tifffile.imread(HALO / "measure" / f"{SUBJ}__H1.tif")
diff = np.any(a0 != a1, axis=2)
print(f"\nchanged pixels: {diff.sum():,} ({100.0 * diff.mean():.3f}%)")

d = ndimage.distance_transform_edt(~fg)
print(f"changed & in foreground : {int((diff & fg).sum()):,}")
print(f"changed & d>40          : {int((diff & (d > 40)).sum()):,}")

fw = rec["fine_window"]
y, x, c = fw["y"], fw["x"], fw["size"]
sub = diff[y:y + c, x:x + c]
print(f"\nfine-structure window at (y={y}, x={x}) size {c}")
print(f"  treated pixels inside it: {int(sub.sum()):,} "
      f"({100.0 * sub.mean():.4f}% of the window)")
print(f"  foreground fraction     : {100.0 * fg[y:y + c, x:x + c].mean():.2f}%")
print("  -> a window with no treated pixels CANNOT express softening;")
print("     any dQ it reports is structurally pinned to zero.")
