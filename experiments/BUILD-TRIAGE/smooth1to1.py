"""The three genuinely smooth FLAT tiles, both arms, at 1:1.

The corpus-wide sheet showed most FLAT tiles saturated at +/-40 DN because they
carry subject structure -- `argmin(high-frequency energy)` picks the block with
least FINE detail, which is routinely a large defocused shape, not a flat
field.  Three tiles are the exception and land in the regime ORCH described:
a few tens of DN of excursion on smooth tone.

Those three are the only crops in my lane that can speak to smooth-tone
defects at all.  This renders them big, both arms, so the question "is this in
the optics or in the merge" is answered by looking rather than by a ratio:
dust in the optical path is in EVERY frame and must appear in BOTH arms.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402
from smoothlook import detrend  # noqa: E402

TILES = os.path.join(tri.OUT, "tiles")
OUT = os.path.join(tri.OUT, "smooth")
SUBS = ["highly-angled-ruler-mm-cpl", "pencil-steep-angle-cpl",
        "pencil-flatter-angle-cpl"]
SHOW_DN = 25.0


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    cell, pad, hdr, lab = 512, 8, 46, 30
    W = 2 * (cell + pad) + pad
    H = hdr + len(SUBS) * (cell + pad + lab) + pad
    sheet = Image.new("RGB", (W, H), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 8), "smooth FLAT tiles at 1:1, camera-linear, background "
            f"removed at sigma=64 px", fill=(235, 235, 235))
    dr.text((pad, 24), f"full swing = +/-{SHOW_DN:g} DN of 65535 "
            f"(x{65535 / (2 * SHOW_DN):.0f}).  LEFT = merge, RIGHT = best "
            f"single source frame.", fill=(190, 190, 190))
    for i, sub in enumerate(SUBS):
        z = np.load(os.path.join(TILES, f"{sub}.FLAT.npz"))
        y = hdr + i * (cell + pad + lab)
        for j, arm in enumerate(("merge", "frame")):
            d = detrend(z[arm].astype(np.float32))
            v = np.clip(d / SHOW_DN * 127.0 + 128.0, 0, 255).astype(np.uint8)
            sheet.paste(Image.fromarray(v), (pad + j * (cell + pad), y))
        dr.text((pad, y + cell + 4),
                f"{sub}    merge sd {detrend(z['merge'].astype(np.float32)).std():.2f} DN"
                f"    frame sd {detrend(z['frame'].astype(np.float32)).std():.2f} DN",
                fill=(225, 225, 225))
    p = os.path.join(OUT, "smooth-1to1.png")
    sheet.save(p)
    print(f"wrote {p} ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
