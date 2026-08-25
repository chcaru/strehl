"""M116-promotion — the images.

Writes, to C:\\dev\\strehl-out\\M116\\images\\:

  <subject>__<arm>__full.png     the whole render, downscaled to view
  <subject>__<arm>__detail.png   a 1:1 (100%) crop, IDENTICAL pixel region
  <subject>__<arm>__flat.png     a 1:1 (100%) crop, IDENTICAL pixel region
  <subject>__contact-detail.png  every arm side by side at 1:1
  <subject>__contact-flat.png    every arm side by side at 1:1

The two crop windows are located on the M0 arm (`--gate 0`), which is not one of
the compared arms, so the choice of what to look at is not made by an arm under
test. Coordinates come from scores.json and are doubled, because the viewing
render is `--srgb` and therefore full sensor resolution while the crop windows
were found on the half-resolution plane grid.

Every panel is labelled with its arm, the pinned commit and its metric values,
so that a sheet cannot be separated from the run that produced it.
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

ROOT = Path(r"C:\dev\strehl-out\M116")
VIEW = ROOT / "view"
OUT = ROOT / "images"
SHA = "4beac73"

SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
# M0 is pure selection -- what every other stacker does -- and B0 is the
# sharpest single source frame. Both are shown because both are the things the
# default path has to beat.
ARMS = ["B0", "M0", "A0", "A1", "A2", "A3", "A4"]
LABEL = {
    "B0": "B0 sharpest single frame",
    "M0": "M0 gate 0 = pure selection",
    "A0": "A0 DEFAULT (shipped)",
    "A1": "A1 +photometric",
    "A2": "A2 +softgate gaussian",
    "A3": "A3 +softgate exponential",
    "A4": "A4 +photometric +softgate",
}
CROP = 512          # on the plane grid
CROP_VIEW = 1024    # on the --srgb full-resolution grid
BAR = 34


def to_u8(a: np.ndarray) -> np.ndarray:
    if a.dtype == np.uint16:
        return (a >> 8).astype(np.uint8)
    return a.astype(np.uint8)


def labelled(img: Image.Image, text: str, sub: str) -> Image.Image:
    out = Image.new("RGB", (img.width, img.height + BAR), (16, 16, 16))
    out.paste(img, (0, BAR))
    d = ImageDraw.Draw(out)
    d.text((6, 4), text, fill=(255, 255, 255))
    d.text((6, 18), sub, fill=(170, 170, 170))
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    scores = json.loads((ROOT / "scores.json").read_text())

    for s in SUBJECTS:
        al = scores[s]["aligned"]
        if not al:
            print(f"{s}: no scores, skipping")
            continue
        windows = {
            "detail": al["crop_detail_plane_xy"],
            "flat": al["crop_flat_plane_xy"],
        }
        panels = {"detail": [], "flat": []}

        for arm in ARMS:
            tif = VIEW / f"{s}__{arm}.tif"
            if not tif.exists():
                print(f"  {tif.name} missing")
                continue
            a = to_u8(tifffile.imread(tif))
            img = Image.fromarray(a)

            full = img.copy()
            full.thumbnail((1400, 1400))
            full.save(OUT / f"{s}__{arm}__full.png")

            st = al["arms"].get(arm, {})
            ref = al["arms"].get("A0", {})
            if st and ref:
                sub = (f"N {st['N']:.4f}  D {st['D']:.4f}  Q {st['Q']:.4f}   "
                       f"dQ {st['Q'] - ref['Q']:+.5f}  dD {st['D'] - ref['D']:+.5f}")
            else:
                sub = "not scored on this grid"

            for kind, (px, py) in windows.items():
                x, y = 2 * px, 2 * py
                x = max(0, min(x, img.width - CROP_VIEW))
                y = max(0, min(y, img.height - CROP_VIEW))
                crop = img.crop((x, y, x + CROP_VIEW, y + CROP_VIEW))
                crop.save(OUT / f"{s}__{arm}__{kind}.png")
                panels[kind].append(
                    labelled(crop, f"{LABEL[arm]}   [{SHA}]", sub))

        for kind, ps in panels.items():
            if not ps:
                continue
            cols = len(ps)
            w = sum(p.width for p in ps) + 8 * (cols + 1)
            h = max(p.height for p in ps) + 40
            sheet = Image.new("RGB", (w, h), (28, 28, 28))
            x = 8
            for p in ps:
                sheet.paste(p, (x, 32))
                x += p.width + 8
            d = ImageDraw.Draw(sheet)
            d.text((8, 10),
                   f"M116  {s}  1:1 {kind.upper()} crop at plane "
                   f"{windows[kind]}  commit {SHA}  gate 4  limit 100"
                   f"   -- crop window located on M0, not on any compared arm",
                   fill=(255, 255, 255))
            sheet.save(OUT / f"{s}__contact-{kind}.png")
            print(f"  wrote {s}__contact-{kind}.png  ({cols} arms)")

    print(f"\nimages in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
