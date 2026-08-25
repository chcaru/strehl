"""deliver_patch.py — the crops the owner and ORCH actually look at.

Everything here is FOR LOOKING, not for measuring: it applies a gamma 2.2
encode and a percentile stretch, both of which are non-linear and both of which
are disclosed in the filename. Every number in the report comes from the linear
renders instead.

The one discipline preserved from the measurement side: the OFF and ON panels
share ONE stretch, computed from the OFF panel. Per-panel autoscaling would
manufacture or hide a brightness step, which is the entire artefact under
discussion.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(r"C:\dev\strehl-out\M116")
MEAS = ROOT / "measure"
OUT = ROOT
SCALE = 2  # 1:1 pixels shown at 2x so a step is visible on a normal screen

JOBS = [
    ("SOFTGATE-1-background-OFF-vs-ON", "bee-3-cpl", 256, 768, 384,
     "defocused wing, out of focus in every frame"),
    ("SOFTGATE-2-detail-OFF-vs-ON", "bee-3-cpl", 1152, 2432, 384,
     "antenna and hairs, the detail the soft gate could damage"),
    ("SOFTGATE-3-plant-gate0-vs-shipped-vs-ON", "bee-3-cpl", 256, 768, 384,
     "same region, gate 0 plant included"),
]
ARMSETS = {
    "SOFTGATE-1-background-OFF-vs-ON": [("A0", "OFF (shipped)"),
                                        ("A2", "ON (soft gate)")],
    "SOFTGATE-2-detail-OFF-vs-ON": [("A0", "OFF (shipped)"),
                                    ("A2", "ON (soft gate)")],
    "SOFTGATE-3-plant-gate0-vs-shipped-vs-ON": [
        ("M0", "gate 0 (plant)"), ("A0", "OFF (shipped)"),
        ("A2", "ON (soft gate)")],
}


def rgb(a):
    return a[..., :3].astype(np.float32)


for tag, S, Y, X, R, caption in JOBS:
    arms = ARMSETS[tag]
    panels, lo, hi = [], None, None
    for a, _lab in arms:
        img = rgb(tifffile.imread(MEAS / f"{S}__{a}.tif"))
        roi = img[Y:Y + R, X:X + R, :]
        v = np.clip(roi / 65535.0, 0, 1) ** (1 / 2.2)
        if lo is None:
            ref = arms[0][0]
            lo, hi = np.percentile(v, 0.5), np.percentile(v, 99.5)
            print(f"{tag}: common stretch from {ref} = [{lo:.4f}, {hi:.4f}]")
        u8 = np.clip((v - lo) / max(hi - lo, 1e-9) * 255, 0, 255).astype(np.uint8)
        p = Image.fromarray(u8).resize((R * SCALE, R * SCALE), Image.NEAREST)
        panels.append(p)

    gap, bar = 12, 34
    W = len(panels) * R * SCALE + (len(panels) - 1) * gap
    sheet = Image.new("RGB", (W, R * SCALE + bar + 26), "white")
    d = ImageDraw.Draw(sheet)
    for i, (p, (a, lab)) in enumerate(zip(panels, arms)):
        x0 = i * (R * SCALE + gap)
        sheet.paste(p, (x0, bar))
        d.text((x0 + 6, 10), f"{a}  {lab}", fill="black")
    d.text((6, R * SCALE + bar + 6),
           f"{S}  y={Y} x={X} {R}x{R} px shown at {SCALE}x  |  {caption}  |  "
           f"gamma 2.2 + shared stretch, FOR LOOKING ONLY", fill="black")
    name = OUT / f"{tag}.png"
    sheet.save(name)
    print(f"wrote {name}")
