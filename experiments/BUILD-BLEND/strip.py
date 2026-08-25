"""Lay N parameter arms out in one strip, at 1:1 and at full frame.

For choosing a parameter, not for judging quality. Every arm goes through the
identical conversion, and the crop window is the SAME rectangle for every arm --
chosen once, from the first arm, so a parameter cannot flatter itself by moving
the window.

    python strip.py <out.jpg> <x> <y> <side> <label=path> [label=path ...]

Pass `-1 -1` for x y to centre the window.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

BAR = 40
GUTTER = 12
BG = (24, 24, 24)
FG = (240, 240, 240)


def read16(path: Path) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{path} has shape {a.shape}"
    return a


def panel(arr: np.ndarray, text: str, long_edge: int | None) -> Image.Image:
    im = Image.fromarray((arr >> 8).astype(np.uint8), mode="RGB")
    if long_edge:
        im.thumbnail((long_edge, long_edge), Image.LANCZOS)
    out = Image.new("RGB", (im.width, im.height + BAR), BG)
    out.paste(im, (0, BAR))
    ImageDraw.Draw(out).text((8, BAR // 2), text, fill=FG, anchor="lm")
    return out


def main() -> int:
    out_p = Path(sys.argv[1])
    x, y, side = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    arms = [a.split("=", 1) for a in sys.argv[5:]]
    assert arms, "need at least one label=path"

    panels = []
    for i, (label, p) in enumerate(arms):
        a = read16(Path(p))
        if i == 0 and x < 0:
            x, y = (a.shape[1] - side) // 2, (a.shape[0] - side) // 2
        crop = a[y:y + side, x:x + side]
        panels.append(panel(crop, label, None))

    w = sum(p.width for p in panels) + GUTTER * (len(panels) - 1)
    h = max(p.height for p in panels)
    strip = Image.new("RGB", (w, h + BAR), BG)
    ImageDraw.Draw(strip).text(
        (8, BAR // 2), f"1:1 at ({x}, {y}), {side}px -- identical window for every arm",
        fill=FG, anchor="lm",
    )
    cx = 0
    for p in panels:
        strip.paste(p, (cx, BAR))
        cx += p.width + GUTTER
    strip.save(out_p, quality=95, subsampling=0, optimize=True)
    print(f"{out_p.name}  {strip.size[0]}x{strip.size[1]}  window=({x},{y},{side})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
