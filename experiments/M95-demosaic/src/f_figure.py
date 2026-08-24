"""Arm 6 deliverable: the eye-check on B1.

B1 says top-octave power does not rank demosaic quality, because NEAREST reads
+0.58 dex LOUDER than MHC while carrying less real detail. That is a claim about
what a photograph looks like, and this project has already had a metric outrank
the eye once tonight and be wrong (M87's halo correction reported +72.9% while
erasing the bee's abdomen hairs).

So the claim is put in front of the eye. Four panels, identical crop, identical
display transform, at 100% with no resampling:

    TRUTH     the known answer -- the ceiling no demosaic can beat
    MHC       what strehl ships
    BILINEAR  the quiet-and-soft failure mode
    NEAREST   the LOUD failure mode, the one the power metric prefers

If NEAREST does not look worse than MHC, B1's interpretation is wrong however
the numbers read.

NO sharpness number appears on any panel. The numbers in the report were
measured over 400 tiles pooled, not on this crop, and labelling this crop with
them would be attributing a measurement to an axis it was not made on.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import m95dem  # noqa: E402

SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M95-demosaic\scratch")
OUTDIR = pathlib.Path(r"C:\dev\strehl-out\M95-demosaic")

CROP = 320
GAP = 14
LABEL_H = 34
FOOT_H = 46
EXPOSURE = 3.2      # linear gain, identical on every panel


def srgb(x):
    x = np.clip(x * EXPOSURE, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def to_u8(rgb):
    return (srgb(rgb) * 255.0 + 0.5).astype(np.uint8)


def font(sz):
    for n in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    T = np.load(SCRATCH / "truth_AHD.npy")
    M = m95dem.mosaic_rggb(T)

    # Pick the crop on the TRUTH's own in-band energy, never on any arm's, so
    # the crop cannot be chosen to flatter or damn a particular demosaic.
    tiles = m95dem.pick_tiles(T, CROP, 24, 0.30, 0.48, margin=CROP)
    y, x = tiles[3]
    print(f"crop at ({x}, {y}) size {CROP}")

    arms = [("TRUTH  (known answer)", T),
            ("MHC  (what strehl ships)", m95dem.demosaic_mhc(M)),
            ("BILINEAR  (quiet failure)", m95dem.demosaic_bilinear(M)),
            ("NEAREST  (loud failure)", m95dem.demosaic_nearest(M))]

    n = len(arms)
    W = n * CROP + (n + 1) * GAP
    H = LABEL_H + CROP + GAP + FOOT_H
    canvas = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(canvas)
    f_lab, f_foot = font(15), font(13)

    for i, (name, img) in enumerate(arms):
        px = GAP + i * (CROP + GAP)
        tile = to_u8(img[y:y + CROP, x:x + CROP])
        canvas.paste(Image.fromarray(tile), (px, LABEL_H))
        d.text((px, 9), name, font=f_lab, fill=(236, 236, 240))

    foot = ("Identical crop, identical exposure and transfer curve, 100% -- no panel is resampled.   "
            "The mosaic fed to all three demosaics is TRUTH sampled RGGB, so the left panel is the exact answer.   "
            "NEAREST emits the MOST top-octave power of the four.")
    d.text((GAP, LABEL_H + CROP + GAP + 6), foot, font=f_foot, fill=(158, 158, 166))
    d.text((GAP, LABEL_H + CROP + GAP + 25),
           "No sharpness number is printed on a panel: the report's numbers were pooled over 400 tiles, not measured on this crop.",
           font=f_foot, fill=(158, 158, 166))

    p = OUTDIR / "M95-demosaic-ladder.png"
    canvas.save(p)
    print("wrote", p, canvas.size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
