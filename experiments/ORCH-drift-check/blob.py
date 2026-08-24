"""Look hard at the polygonal grey region in bee-3-cpl's defocused background.

A defocused background is a smooth field. It cannot contain straight edges or
polygonal boundaries: those are not something an out-of-focus lens can produce.
If the boundary is hard and piecewise-linear, it was made by the merge, and the
signature would be the winner field showing through -- adjacent tiles electing
frames whose background brightness differs slightly.

This does not diagnose the cause, it only establishes whether the artifact is
real and what shape it has. Rendering it large, with a strong contrast stretch
applied ONLY to this diagnostic view (never to a delivered render), because the
step is a few DN and invisible at normal display gamma.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

SRC = Path(r"C:\dev\strehl-out\ORCH-gallery3\bee-3-cpl.tif")
OUT = Path(r"C:\dev\strehl-out\ORCH-gallery3\BLOB.png")

# Region around the suspect area, from the CROPS-100 figure: that crop was
# anchored at (780, 3120) and the polygon sat low-centre within its 520 px.
X0, Y0, W, H = 700, 3150, 1100, 900


def main() -> int:
    a = tifffile.imread(SRC)
    print(f"render {a.shape} {a.dtype}")
    r = a[Y0:Y0 + H, X0:X0 + W].astype(np.float32)

    g = r[:, :, 1]
    lo, hi = float(np.percentile(g, 1)), float(np.percentile(g, 99))
    print(f"green in region: p1 {lo:.0f}  p99 {hi:.0f}  span {hi - lo:.0f} DN of 65535")

    # Normal view, just scaled to 8-bit.
    normal = np.clip(r / 257.0, 0, 255).astype(np.uint8)

    # Hard stretch of the green plane about its own median, to make a few-DN
    # step visible. Diagnostic only.
    med = float(np.median(g))
    span = max(hi - lo, 1.0) * 0.35
    stretched = np.clip((g - med) / span * 127.0 + 127.0, 0, 255).astype(np.uint8)
    stretched = np.dstack([stretched] * 3)

    pad, lab = 14, 24
    sheet = Image.new("RGB", (2 * W + 3 * pad, H + 2 * pad + lab + 34), (20, 20, 22))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 10), "bee-3-cpl -- defocused background at 100%.  "
                      "A lens cannot put a straight edge in an out-of-focus field.",
           fill=(215, 215, 220))
    sheet.paste(Image.fromarray(normal), (pad, 34 + pad))
    sheet.paste(Image.fromarray(stretched), (2 * pad + W, 34 + pad))
    d.text((pad, 34 + pad + H + 4), f"as rendered  @ ({X0},{Y0}) {W}x{H}", fill=(190, 190, 200))
    d.text((2 * pad + W, 34 + pad + H + 4),
           f"green plane, contrast x{65535 / span:.0f} about median -- DIAGNOSTIC ONLY",
           fill=(190, 190, 200))
    sheet.save(OUT)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
