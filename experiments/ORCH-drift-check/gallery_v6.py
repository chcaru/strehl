"""ORCH gallery for the DELIVER-V6 masters: something the owner can actually browse.

Distinct from `gallery.py`, which stacks from RAW and applies a global exposure gain
because fact 1257 found 19 of 23 captures under-exposed by a median +2.01 stops. That
script must not be used here: the V6 masters are rendered through the tone stage, which
fact 1925 records as SUPERSEDING `--auto-exposure` precisely because applying both
multiplies an already-normalised image by its own gain a second time -- MEASURED at
92.03 percent of pixels clipped versus 0.00 percent, blowing 11 of 18 masters to a
white median.

So the honest preview here is a straight 16-to-8 bit reduction: no stretch, no curve,
no saturation, no sharpening. What the file contains is what gets shown.

Two products per subject:
  * full-frame preview at 2400 px long edge, for composition and overall look
  * 1200 px 100 percent crop on the sharpest region, for detail judgement

READ-ONLY on the masters. All output goes to D:\\strehl-out\\ORCH-GALLERY.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

SRC = r"C:\dev\strehl-out\DELIVER-V6\masters"
OUT = r"D:\strehl-out\ORCH-GALLERY"
LONG_EDGE = 2400
CROP = 1200


def straight8(a16):
    """Faithful 16 -> 8 bit. No stretch, no gamma, no per-image adaptation."""
    return (a16 >> 8).astype(np.uint8)


def sharpest_site(luma, crop, margin=48):
    h, w = luma.shape
    step = max(crop // 2, 1)
    best, bxy = -1.0, (margin, margin)
    ylim = max(margin + 1, h - crop - margin)
    xlim = max(margin + 1, w - crop - margin)
    for y in range(margin, ylim, step):
        for x in range(margin, xlim, step):
            t = luma[y:y + crop:8, x:x + crop:8]
            if t.size == 0:
                continue
            e = float(np.mean(np.abs(np.diff(t, axis=0))) +
                      np.mean(np.abs(np.diff(t, axis=1))))
            if e > best:
                best, bxy = e, (y, x)
    return bxy, best


def main(argv):
    prev_dir = os.path.join(OUT, "preview")
    crop_dir = os.path.join(OUT, "crop-100pct")
    os.makedirs(prev_dir, exist_ok=True)
    os.makedirs(crop_dir, exist_ok=True)

    names = argv or sorted(
        os.path.splitext(f)[0] for f in os.listdir(SRC) if f.endswith(".tiff"))

    done = 0
    for name in names:
        path = os.path.join(SRC, name + ".tiff")
        if not os.path.exists(path):
            print(f"{name:44s} ABSENT")
            continue
        prev_p = os.path.join(prev_dir, name + ".jpg")
        if os.path.exists(prev_p):
            print(f"{name:44s} skip (already built)")
            done += 1
            continue
        try:
            img = tifffile.imread(path)
        except Exception as exc:                    # partial file, still rendering
            print(f"{name:44s} UNREADABLE ({type(exc).__name__}) - still rendering?")
            continue
        if img.ndim != 3 or img.shape[2] < 3:
            print(f"{name:44s} unexpected shape {img.shape}")
            continue

        h, w = img.shape[:2]
        rgb8 = straight8(img[..., :3])

        im = Image.fromarray(rgb8)
        scale = LONG_EDGE / float(max(w, h))
        im.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                  Image.LANCZOS).save(prev_p, quality=92, subsampling=0)

        (cy, cx), e = sharpest_site(img[..., 1].astype(np.float32), CROP)
        Image.fromarray(rgb8[cy:cy + CROP, cx:cx + CROP]).save(
            os.path.join(crop_dir, f"{name}@{cx}_{cy}.jpg"),
            quality=95, subsampling=0)

        print(f"{name:44s} {w}x{h} -> preview + crop @({cx},{cy}) grad {e:.0f}")
        done += 1

    print(f"\n{done} subject(s) in gallery")
    print(f"  previews : {prev_dir}")
    print(f"  crops    : {crop_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
