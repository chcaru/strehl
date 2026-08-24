"""ORCH gallery3 contact sheet + true 100% crops.

Two figures, deliberately separate:

  CONTACT-SHEET.png  downscaled to fit, Lanczos. For "did the stack work at all".
                     Downscaling hides softness, so it must NOT be used to judge
                     sharpness -- that is what the crops are for.

  CROPS-100.png      pure pixel copies at 1:1 from the rendered TIFF. No resize,
                     no sharpening, no tone adjustment of any kind. This is the
                     only honest view of what the tool actually produced.

Nothing here post-processes the render. The TIFFs come from `strehl stack
--srgb --auto-exposure`, which is one multiply in linear light before the
transfer curve; everything below is crop and paste.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

SRC = Path(r"C:\dev\strehl-out\ORCH-gallery3")
STACKS = [
    "bee-3-cpl",
    "leaf-2-cpl",
    "dry-erase-marker-head-cpl",
    "lavendar-cpl",
    "tweezers-cpl",
]

THUMB_W = 620
CROP = 520


def load8(p: Path) -> np.ndarray:
    a = tifffile.imread(p)
    if a.dtype == np.uint16:
        return (a >> 8).astype(np.uint8)
    return a.astype(np.uint8)


def sharpest_crop(img: np.ndarray, size: int) -> tuple[int, int]:
    """Pick the crop with the most local detail, so the figure shows the
    subject rather than whatever happens to sit at the geometric centre.

    This selects WHERE to look, not what the pixels are. It is a framing
    decision, and it is applied identically to every stack.
    """
    h, w, _ = img.shape
    g = img[:, :, 1].astype(np.float32)
    best, bxy = -1.0, (h // 2 - size // 2, w // 2 - size // 2)
    step = size // 2
    for y in range(0, h - size, step):
        for x in range(0, w - size, step):
            t = g[y:y + size:4, x:x + size:4]
            v = float(np.var(np.abs(np.diff(t, axis=0))) + np.var(np.abs(np.diff(t, axis=1))))
            if v > best:
                best, bxy = v, (y, x)
    return bxy


def main() -> int:
    imgs = {}
    for s in STACKS:
        p = SRC / f"{s}.tif"
        if not p.exists():
            print(f"MISSING {p}")
            return 1
        imgs[s] = load8(p)
        print(f"{s:<30} {imgs[s].shape}")

    # ---- contact sheet -----------------------------------------------------
    thumbs = []
    for s in STACKS:
        a = imgs[s]
        im = Image.fromarray(a)
        th = im.resize((THUMB_W, int(THUMB_W * a.shape[0] / a.shape[1])), Image.LANCZOS)
        thumbs.append((s, th))

    cols, pad, lab = 3, 14, 26
    tw, thh = THUMB_W, thumbs[0][1].height
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * pad,
                              rows * (thh + lab) + (rows + 1) * pad + 34), (20, 20, 22))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 10), "strehl -- ORCH gallery3    stack --srgb --auto-exposure, "
                      "isolated sidecar per rule 45    DOWNSCALED: do not judge sharpness here",
           fill=(215, 215, 220))
    for i, (s, th) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = 34 + pad + r * (thh + lab + pad)
        sheet.paste(th, (x, y))
        n = imgs[s].shape
        d.text((x, y + thh + 6), f"{s}   {n[1]} x {n[0]}", fill=(190, 190, 200))
    sheet.save(SRC / "CONTACT-SHEET.png")
    print(f"wrote {SRC / 'CONTACT-SHEET.png'}")

    # ---- true 100% crops ---------------------------------------------------
    cols2 = 3
    rows2 = (len(STACKS) + cols2 - 1) // cols2
    crops = Image.new("RGB", (cols2 * CROP + (cols2 + 1) * pad,
                              rows2 * (CROP + lab) + (rows2 + 1) * pad + 34), (20, 20, 22))
    d2 = ImageDraw.Draw(crops)
    d2.text((pad, 10), "strehl -- ORCH gallery3    TRUE 100% CROPS, 1:1 pixels, "
                       "no resize / no sharpening / no tone adjustment",
            fill=(215, 215, 220))
    for i, s in enumerate(STACKS):
        a = imgs[s]
        y0, x0 = sharpest_crop(a, CROP)
        c = a[y0:y0 + CROP, x0:x0 + CROP]
        r, cc = divmod(i, cols2)
        x = pad + cc * (CROP + pad)
        y = 34 + pad + r * (CROP + lab + pad)
        crops.paste(Image.fromarray(c), (x, y))
        d2.text((x, y + CROP + 6), f"{s}   @ ({x0},{y0})", fill=(190, 190, 200))
    crops.save(SRC / "CROPS-100.png")
    print(f"wrote {SRC / 'CROPS-100.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
