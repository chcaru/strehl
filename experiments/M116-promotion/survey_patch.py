"""survey_patch.py — LOOK at the whole frame before measuring any of it.

Campaign 5's registered metric failed its own plant (G1), and the crop showed
why: the ROI selector picked a region where the shipped arm is already smooth.
Before proposing any replacement metric I need to know WHERE on the shipped
render the patchwork actually is. This does no scoring. It writes:

  1. a downsampled, hard-stretched view of the whole A0 frame
  2. the same for M0 (where the artefact is known-present) and A2
  3. a view of the election index map, where polygons are directly visible

Stretch is common across arms so a step is never manufactured by autoscaling.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(r"C:\dev\strehl-out\M116")
OUT = ROOT / "images-patch"
OUT.mkdir(parents=True, exist_ok=True)

S = sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"
LONG = 1400


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def shrink(x, long_edge):
    h, w = x.shape
    f = max(1, int(round(max(h, w) / long_edge)))
    h2, w2 = (h // f) * f, (w // f) * f
    return x[:h2, :w2].reshape(h2 // f, f, w2 // f, f).mean(axis=(1, 3)), f


for arm in ("A0", "M0", "A2"):
    p = ROOT / "measure" / f"{S}__{arm}.tif"
    g = luma(tifffile.imread(p).astype(np.float32))
    sm, f = shrink(g, LONG)
    # gamma for looking only; stated in the filename
    v = np.clip(sm / 65535.0, 0, 1) ** (1 / 2.2)
    lo, hi = np.percentile(v, 0.5), np.percentile(v, 99.5)
    u8 = np.clip((v - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
    Image.fromarray(u8).save(OUT / f"{S}__full-{arm}-gamma22.png")
    print(f"{arm}: {g.shape} -> {sm.shape} (bin {f})")

ix = ROOT / "maps" / f"{S}__A0-index.tif"
if ix.exists():
    m = tifffile.imread(ix)
    m = m[..., 0] if m.ndim == 3 else m
    m = m.astype(np.float32)
    sm, f = shrink(m, LONG)
    lo, hi = float(m.min()), float(m.max())
    u8 = np.clip((sm - lo) / max(hi - lo, 1e-9) * 255, 0, 255).astype(np.uint8)
    Image.fromarray(u8).save(OUT / f"{S}__election-index.png")
    print(f"index map: {m.shape} range [{lo:.0f}, {hi:.0f}] (bin {f})")
else:
    print(f"NO index map at {ix}")
