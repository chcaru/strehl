"""crops_patch.py — look at the background ROI directly.

The prereg says the images adjudicate, not the number, so this runs before any
interpretation of K. Writes 8-bit PNGs of the ROI for each arm, plus a
Laplacian view that makes step edges visible, plus a hard-stretched view
because the patchwork is a LOW-CONTRAST artefact and an unstretched crop can
hide it entirely.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(r"C:\dev\strehl-out\M116")
MEAS = ROOT / "measure"
OUT = ROOT / "images-patch"
OUT.mkdir(parents=True, exist_ok=True)

S = sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"
Y = int(sys.argv[2]); X = int(sys.argv[3]); R = int(sys.argv[4])
ARMS = sys.argv[5].split(",") if len(sys.argv) > 5 else ["A0", "A1", "A2", "M0"]
TAG = sys.argv[6] if len(sys.argv) > 6 else "roi"


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def to8(x, lo, hi):
    return np.clip((x - lo) / max(hi - lo, 1e-9) * 255.0, 0, 255).astype(np.uint8)


panels, laps = [], []
ref_lo = ref_hi = None
for a in ARMS:
    g = luma(tifffile.imread(MEAS / f"{S}__{a}.tif").astype(np.float32))
    roi = g[Y:Y + R, X:X + R]
    # A hard, COMMON stretch: +/- 3 sd about the first arm's mean, so every
    # panel shares one mapping and a brightness step is not manufactured by
    # per-panel autoscaling.
    if ref_lo is None:
        m, s = roi.mean(), roi.std()
        ref_lo, ref_hi = m - 3 * s, m + 3 * s
        print(f"common stretch from {ARMS[0]}: [{ref_lo:.1f}, {ref_hi:.1f}] "
              f"(mean {m:.1f}, sd {s:.1f})")
    panels.append(to8(roi, ref_lo, ref_hi))
    lap = ndimage.laplace(roi.astype(np.float64))
    laps.append(to8(np.abs(lap), 0, np.percentile(np.abs(lap), 99.5)))
    print(f"  {a}: roi mean {roi.mean():.1f} sd {roi.std():.2f} "
          f"lap|.|p99.5 {np.percentile(np.abs(lap), 99.5):.1f}")

gap = 8
W = R * len(panels) + gap * (len(panels) - 1)
sheet = np.full((R * 2 + gap, W), 255, np.uint8)
for i, (p, l) in enumerate(zip(panels, laps)):
    x0 = i * (R + gap)
    sheet[0:R, x0:x0 + R] = p
    sheet[R + gap:R * 2 + gap, x0:x0 + R] = 255 - l
name = OUT / f"{S}__{TAG}__{'-'.join(ARMS)}.png"
Image.fromarray(sheet).save(name)
print(f"wrote {name}  (top: common hard stretch, bottom: |Laplacian| inverted)")
