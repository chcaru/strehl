#!/usr/bin/env python3
"""Turn the 26 full-resolution 16-bit TIFF renders into something a human can look at.

The gallery ships as 7032x4688 16-bit RGB TIFFs, 188 MB each, 4.8 GB total.
That is the right deliverable for printing and the wrong one for answering "where
are some stacks I can view".  This writes three things:

  view/<name>.jpg    long edge 2400 px, quality 92 -- the browse copy
  full/<name>.jpg    full resolution, quality 95 -- the print/pixel-peep copy
  contact.jpg        every subject on one sheet, labelled

Rules this obeys, learned the hard way in this project:

  * 16-bit TIFFs are read with tifffile and asserted uint16.  PIL silently
    mangles them.
  * Downscaling for the browse copy uses PIL LANCZOS on the 8-bit conversion,
    which is a viewing operation.  Nothing here is ever used for measurement --
    the measurement instruments read the TIFFs directly.
  * The 16->8 bit conversion is a plain right shift by 8.  No tone curve, no
    autolevel, no per-image normalisation: the renders already carry
    --auto-exposure, and a second per-image gain here would make the sheet lie
    about what the tool produced.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None


def load8(path: str) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    return (a >> 8).astype(np.uint8)


def font(sz: int):
    for p in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=r"C:\dev\strehl-out\SHIP-V1")
    ap.add_argument("dst", nargs="?", default=r"C:\dev\strehl-out\SHIP-V1\viewable")
    ap.add_argument("--long-edge", type=int, default=2400)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--cell", type=int, default=560)
    ap.add_argument("--skip-full", action="store_true")
    args = ap.parse_args()

    vdir = os.path.join(args.dst, "view")
    fdir = os.path.join(args.dst, "full")
    os.makedirs(vdir, exist_ok=True)
    os.makedirs(fdir, exist_ok=True)

    names = sorted(n[:-5] for n in os.listdir(args.src) if n.endswith(".tiff"))
    print(f"{len(names)} subjects from {args.src}")

    thumbs: list[tuple[str, Image.Image]] = []
    for i, n in enumerate(names, 1):
        src = os.path.join(args.src, n + ".tiff")
        a = load8(src)
        im = Image.fromarray(a, "RGB")
        h, w = a.shape[:2]

        fp = os.path.join(fdir, n + ".jpg")
        if not args.skip_full and not os.path.exists(fp):
            im.save(fp, "JPEG", quality=95, subsampling=0, optimize=True)

        s = args.long_edge / max(w, h)
        vs = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        vp = os.path.join(vdir, n + ".jpg")
        vs.save(vp, "JPEG", quality=92, optimize=True)

        t = args.cell / max(w, h)
        thumbs.append((n, im.resize((max(1, int(w * t)), max(1, int(h * t))),
                                    Image.LANCZOS)))
        print(f"  [{i:2d}/{len(names)}] {n:<40s} {w}x{h} -> "
              f"{vs.size[0]}x{vs.size[1]}")

    cols = args.cols
    rows = (len(thumbs) + cols - 1) // cols
    cw = max(t.size[0] for _, t in thumbs)
    ch = max(t.size[1] for _, t in thumbs)
    pad, lab = 14, 30
    W = cols * (cw + pad) + pad
    H = rows * (ch + pad + lab) + pad + 56
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 16),
           f"strehl SHIP-V1  --  {len(thumbs)} subjects, pyramid merge, "
           f"lateral-CA correction on, full sensor resolution",
           font=font(22), fill=(235, 235, 240))

    for i, (n, t) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = 56 + pad + r * (ch + pad + lab)
        sheet.paste(t, (x + (cw - t.size[0]) // 2, y))
        d.text((x, y + ch + 6), n[:44], font=font(15), fill=(200, 200, 208))

    cp = os.path.join(args.dst, "contact.jpg")
    sheet.save(cp, "JPEG", quality=93, optimize=True)
    print(f"\ncontact sheet -> {cp}  ({sheet.size[0]}x{sheet.size[1]})")
    print(f"browse copies -> {vdir}")
    if not args.skip_full:
        print(f"full-res copies -> {fdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
