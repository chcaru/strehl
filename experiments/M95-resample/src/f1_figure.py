"""M95 arm 4 deliverable figure.

Row 1 - THE LOSS, on real data:
    B0  strehl single frame, NO resample          (what the sensor delivered)
    B1  same frame, ONE Catmull-Rom gather        (what one resample costs)
    C   the shipped 299-frame gate-0 merge        (what actually ships)

Row 2 - THE CAUSE, same frame, same binary, only the sidecar's resampler changed:
    nearest / catmull-rom / bilinear

Every panel is labelled with the number measured on EXACTLY this axis (mean
log10 high/low band power, 0.30-0.48 vs 0.02-0.10 cyc/px, scene-frequency matched)
by x2_pairs.py and x4_endtoend.py. No number appears on a panel that was not
measured on that panel's own axis.

The crop is chosen BLIND to the effect: the sharpest tile by gradient energy on B0
alone. Display magnification is NEAREST so that no display filter can add or remove
the very detail the figure is about.
"""

import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import x2_pairs as X

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
DEST = r"C:\dev\strehl-out\M95-resample"
CROP = 300
ZOOM = 2
PAD = 12
LABEL_H = 54

X.IMAGES["Bnear"] = dict(path=os.path.join(DEST, "single-nearest.tif"), k=0.9974, what="nearest")
X.IMAGES["Bbilin"] = dict(path=os.path.join(DEST, "single-bilinear.tif"), k=0.9974, what="bilinear")


def font(sz):
    for f in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def stretch(a, lo, hi):
    """One shared linear stretch for every panel, computed on B0 alone. A per-panel
    stretch would change local contrast and could manufacture the difference."""
    return np.clip((a.astype(np.float64) - lo) / max(hi - lo, 1e-9), 0, 1)


def main():
    b0 = X.load_luma(X.IMAGES["B0"]["path"])
    tiles = X.pick_tiles(b0)
    y, x = tiles[0]
    y += (X.TILE - CROP) // 2
    x += (X.TILE - CROP) // 2
    print(f"crop chosen blind (sharpest gradient tile on B0): y={y} x={x} size={CROP}")

    ref = b0[y : y + CROP, x : x + CROP]
    lo, hi = float(np.percentile(ref, 0.5)), float(np.percentile(ref, 99.5))
    print(f"shared stretch from B0 only: [{lo:.0f}, {hi:.0f}] DN")

    d2 = json.load(open(os.path.join(OUT, "x2_pairs.json")))
    d4 = json.load(open(os.path.join(OUT, "x4_endtoend.json")))

    rows = [
        [
            ("B0", "single frame, NO resample", d2["per_image"]["B0"]["mean"]),
            ("B1", "same frame, ONE Catmull-Rom gather", d2["per_image"]["B1"]["mean"]),
            ("C", "shipped merge, 299 frames, gate 0", d2["per_image"]["C"]["mean"]),
        ],
        [
            ("Bnear", "gather = nearest (a permutation)", d2["per_image"]["B0"]["mean"] + d4["results"]["nearest"]["delta"]),
            ("B1", "gather = catmull-rom  (SHIPS)", d2["per_image"]["B0"]["mean"] + d4["results"]["catmull-rom"]["delta"]),
            ("Bbilin", "gather = bilinear", d2["per_image"]["B0"]["mean"] + d4["results"]["bilinear"]["delta"]),
        ],
    ]

    cw = CROP * ZOOM
    W = PAD + 3 * (cw + PAD)
    H = 96 + 2 * (LABEL_H + cw + PAD) + 84
    canvas = Image.new("RGB", (W, H), (16, 16, 18))
    dr = ImageDraw.Draw(canvas)
    f_title, f_lab, f_num, f_cap = font(26), font(17), font(15), font(14)

    dr.text((PAD, 16), "M95 - what one resampling step costs", font=f_title, fill=(245, 245, 245))
    dr.text(
        (PAD, 50),
        "D:\\personal\\macro\\bee-3-cpl - 100% crop, 2x nearest-neighbour magnification, identical linear stretch on every panel",
        font=f_cap,
        fill=(150, 150, 156),
    )

    yy = 96
    for ri, row in enumerate(rows):
        for ci, (name, label, val) in enumerate(row):
            img = X.load_luma(X.IMAGES[name]["path"])
            k = X.IMAGES[name]["k"]
            if name == "B0":
                oy, ox = y, x
                cc = 1.0
            else:
                r = X.register(b0, img, y - (X.TILE - CROP) // 2, x - (X.TILE - CROP) // 2, k)
                cc, oy, ox = r[0], r[1] + (X.TILE - CROP) // 2, r[2] + (X.TILE - CROP) // 2
            t = img[oy : oy + CROP, ox : ox + CROP]
            del img
            arr = (stretch(t, lo, hi) * 255).astype(np.uint8)
            pan = Image.fromarray(arr, "L").convert("RGB").resize((cw, cw), Image.NEAREST)
            px = PAD + ci * (cw + PAD)
            dr.text((px, yy), label, font=f_lab, fill=(240, 240, 240))
            dr.text(
                (px, yy + 24),
                f"log10(hi/lo) = {val:+.4f} dex     registration cc {cc:.3f}",
                font=f_num,
                fill=(130, 190, 255) if ri == 0 else (200, 170, 120),
            )
            canvas.paste(pan, (px, yy + LABEL_H))
            print(f"  row{ri} {name:6s} cc={cc:.4f} at ({oy},{ox})  label {val:+.4f}")
        yy += LABEL_H + cw + PAD

    dr.text(
        (PAD, yy + 4),
        "Number is the mean over 40 in-focus tiles of log10(power 0.30-0.48 cyc/px / power 0.02-0.10 cyc/px), each image integrated over its own",
        font=f_cap,
        fill=(150, 150, 156),
    )
    dr.text(
        (PAD, yy + 24),
        "coverage-scaled band so all terms cover the same SCENE frequencies. Higher is sharper. It is measured on exactly the axis each panel sits on.",
        font=f_cap,
        fill=(150, 150, 156),
    )
    dr.text(
        (PAD, yy + 48),
        "Row 2 differs ONLY in the resampler recorded in the warp sidecar. Same binary, same frame, same demosaic, same output path.",
        font=f_cap,
        fill=(150, 150, 156),
    )

    p = os.path.join(DEST, "M95-resample-kernel.png")
    canvas.save(p)
    print(f"\nwrote {p}  ({W}x{H})")


if __name__ == "__main__":
    main()
