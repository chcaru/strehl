"""Soft-proof pictures: what the press does to a master, at 1:1, side by side.

Scores are not a print verdict.  A subject can read 50% out of gamut and look
untouched, because the clipped colours sit in a region nobody looks at, and a
subject can read 3% and lose the one hue the picture is about.  So this emits
pictures at 1:1 and the numbers are only used to decide WHERE to look.

The crop is chosen by the instrument, not by hand: the 800 x 800 window whose
out-of-gamut density is highest.  That makes the choice reproducible and it
puts the crop where the damage is, which is the honest place to look rather
than the flattering one.  Coordinates are printed so a later run can be
compared against this one.

Panels, left to right:
  MASTER     the shipped file
  PRINTABLE  the same pixels after a round trip through the print profile
  LOST       where, and how much, chroma the press cannot reach

Written as PNG.  A 1:1 artifact crop is never JPEGed here; the compression
artifacts would be indistinguishable from the thing being judged.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw

from printqa import (
    SATURATED_CHROMA,
    SRGB_ICM,
    SWOP_ICM,
    printable_rgb8,
    read_master,
    rgb_to_lab,
)

CROP = 800


def densest_window(mask: np.ndarray, size: int) -> tuple[int, int, float]:
    """Top-left of the size x size window with the most flagged pixels."""
    step = max(size // 4, 1)
    h, w = mask.shape
    best, by, bx = -1.0, 0, 0
    integral = mask.cumsum(0).cumsum(1)
    integral = np.pad(integral, ((1, 0), (1, 0)))
    for y in range(0, max(h - size, 0) + 1, step):
        for x in range(0, max(w - size, 0) + 1, step):
            y2, x2 = y + size, x + size
            s = (
                integral[y2, x2]
                - integral[y, x2]
                - integral[y2, x]
                + integral[y, x]
            )
            if s > best:
                best, by, bx = float(s), y, x
    return by, bx, 100.0 * best / (size * size)


def label(img: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 22], fill=(0, 0, 0))
    d.text((6, 5), text, fill=(255, 255, 255))
    return img


def proof_one(path: Path, out_dir: Path, swop, srgb) -> dict:
    rgb16 = read_master(path)
    rgb8 = (rgb16 >> 8).astype(np.uint8)
    printable = printable_rgb8(rgb8, swop, srgb)

    lab_o = rgb_to_lab(rgb16 / 65535.0)
    lab_p = rgb_to_lab(printable / 255.0)
    c_o = np.hypot(lab_o[..., 1], lab_o[..., 2])
    lost = c_o - np.hypot(lab_p[..., 1], lab_p[..., 2])
    # Condition on there being saturation to lose. Selecting on `lost` alone
    # sent the flowers-cpl crop to featureless background bokeh -- a 90.5%
    # window in which MASTER and PRINTABLE are indistinguishable by eye,
    # because the loss was taken off a near-neutral. A crop that shows no
    # visible difference cannot support a print verdict either way, so the
    # window must land where real colour is being flattened.
    mask = ((lost > 2.0) & (c_o >= SATURATED_CHROMA)).astype(np.float32)
    if mask.sum() < CROP * CROP * 0.02:
        # Nothing saturated is being lost anywhere. Say so rather than falling
        # back to the old mask and presenting a near-neutral crop as evidence.
        print(f"  {path.stem}: no saturated loss to show (mask {100 * mask.mean():.3f}% of frame)")
        return None

    y, x, density = densest_window(mask, CROP)
    sl = (slice(y, y + CROP), slice(x, x + CROP))

    a = Image.fromarray(rgb8[sl], "RGB")
    b = Image.fromarray(printable[sl], "RGB")
    heat = np.clip(lost[sl] / 10.0, 0, 1)
    c = np.zeros((CROP, CROP, 3), np.uint8)
    c[..., 0] = (heat * 255).astype(np.uint8)
    c[..., 1] = ((1 - heat) * 60).astype(np.uint8)
    c[..., 2] = ((1 - heat) * 60).astype(np.uint8)

    name = path.name.replace("--SHIP-V2-ICC.tiff", "")
    sheet = Image.new("RGB", (CROP * 3 + 16, CROP + 26), (24, 24, 24))
    sheet.paste(label(a, f"MASTER  {name}  @ {x},{y}"), (0, 26))
    sheet.paste(label(b, "PRINTABLE  (SWOP, rel.col. + BPC)"), (CROP + 8, 26))
    sheet.paste(
        label(Image.fromarray(c, "RGB"), "LOST CHROMA  red = up to 10 Lab units"),
        (CROP * 2 + 16, 26),
    )
    d = ImageDraw.Draw(sheet)
    d.text(
        (6, 8),
        f"{name}   crop {CROP}x{CROP} at ({x},{y})   "
        f"window out-of-gamut {density:.1f}%   1:1, no resampling",
        fill=(230, 230, 230),
    )
    out = out_dir / f"{name}--softproof.png"
    sheet.save(out)
    return {"subject": name, "x": x, "y": y, "density": density, "path": out}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--root", type=Path, default=Path(r"C:\dev\strehl-out\SHIP-V2-ICC"))
    ap.add_argument(
        "--out", type=Path, default=Path(r"C:\dev\strehl-out\BUILD-RENDER-print")
    )
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    srgb = ImageCms.getOpenProfile(str(SRGB_ICM))
    swop = ImageCms.getOpenProfile(str(SWOP_ICM))

    made, missing = 0, []
    for s in args.subjects:
        hits = sorted(args.root.glob(f"{s}*.tiff"))
        if not hits:
            missing.append(s)
            continue
        r = proof_one(hits[0], args.out, swop, srgb)
        made += 1
        print(
            f"  {r['subject']:<38} crop at ({r['x']:>4},{r['y']:>4})  "
            f"window OOG {r['density']:5.1f}%  -> {r['path'].name}"
        )
    print(f"requested {len(args.subjects)}  written {made}  not found {len(missing)}")
    if missing:
        print(f"  NOT FOUND: {missing}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
