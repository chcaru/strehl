"""Side-by-side crops: strehl merged render vs a single middle frame.

The point is to SEE the defect the owner is complaining about ("those stacks
don't look too good yet"), not to score it. `defect_audit.py` already tried
scoring and its own control killed 3 of its 5 findings, so this script
deliberately produces no numbers - it produces pictures, at matched crops and
matched stretch, with a single-frame LibRaw control beside every crop.

Crops are placed on a fixed fractional grid across the frame, chosen before
looking, so this cannot become a cherry-picking instrument.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

OUT = r"C:\dev\strehl-out\ORCH-thennow"

PAIRS = [
    ("marker",
     os.path.join(OUT, "marker-HEAD-8f46f04.tif"),
     os.path.join(OUT, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif")),
    ("lavendar",
     os.path.join(OUT, "lavendar-HEAD-8f46f04.tif"),
     os.path.join(OUT, "CONTROL-singleframe-lavendar-cpl.tif")),
]

CROPS = [
    ("centre", 0.50, 0.50),
    ("upper-left", 0.32, 0.32),
    ("lower-right", 0.68, 0.68),
    ("upper-right", 0.70, 0.30),
]
BOX = 400
ZOOM = 3


def to8(a, lo, hi):
    a = a.astype(np.float32)
    a = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)
    return (a ** (1 / 2.2) * 255).astype(np.uint8)


def label(img, text):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 24], fill=(0, 0, 0))
    d.text((6, 6), text, fill=(255, 255, 0))
    return img


def main():
    for name, merged_p, ctrl_p in PAIRS:
        if not (os.path.exists(merged_p) and os.path.exists(ctrl_p)):
            print(f"SKIP {name}: missing input")
            continue
        m = tifffile.imread(merged_p)
        c = tifffile.imread(ctrl_p)
        print(f"{name}: merged {m.shape} {m.dtype}   control {c.shape} {c.dtype}")
        h = min(m.shape[0], c.shape[0])
        w = min(m.shape[1], c.shape[1])
        if m.shape[:2] != c.shape[:2]:
            print(f"  NOTE shape mismatch -> common crop {h}x{w}")
        m, c = m[:h, :w], c[:h, :w]

        # One shared stretch for BOTH arms, from the merged frame, so a
        # brightness difference cannot masquerade as a structural one.
        s = m.astype(np.float32)
        lo, hi = float(np.percentile(s, 0.5)), float(np.percentile(s, 99.5))
        print(f"  shared stretch lo={lo:.1f} hi={hi:.1f}")

        tiles = []
        for cname, fx, fy in CROPS:
            y = max(0, min(h - BOX, int(fy * h) - BOX // 2))
            x = max(0, min(w - BOX, int(fx * w) - BOX // 2))
            mim = Image.fromarray(to8(m[y:y + BOX, x:x + BOX], lo, hi))
            cim = Image.fromarray(to8(c[y:y + BOX, x:x + BOX], lo, hi))
            mim = mim.resize((BOX * ZOOM, BOX * ZOOM), Image.NEAREST)
            cim = cim.resize((BOX * ZOOM, BOX * ZOOM), Image.NEAREST)
            label(mim, f"STREHL merged   {cname} @({x},{y})")
            label(cim, f"single frame    {cname} @({x},{y})")
            row = Image.new("RGB", (BOX * ZOOM * 2 + 8, BOX * ZOOM), (40, 40, 40))
            row.paste(mim, (0, 0))
            row.paste(cim, (BOX * ZOOM + 8, 0))
            tiles.append(row)

        sheet = Image.new("RGB", (tiles[0].width, sum(t.height + 8 for t in tiles)), (40, 40, 40))
        yy = 0
        for t in tiles:
            sheet.paste(t, (0, yy))
            yy += t.height + 8
        sheet.thumbnail((1400, 4000), Image.LANCZOS)
        dst = os.path.join(OUT, f"_LOOK-{name}.png")
        sheet.save(dst)
        print(f"  wrote {dst}  {sheet.size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
