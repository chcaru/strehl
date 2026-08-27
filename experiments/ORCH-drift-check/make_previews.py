"""Make the corpus viewable: a full-resolution JPEG per master, plus a contact
sheet.

The masters are 7032x4688 16-bit TIFFs at roughly 190 MB each, which is not a
form anyone can actually look at. The owner has twice asked to see stacks and
twice been handed a directory of those. This produces the set he asked for.

The TIFFs are already sRGB-encoded (`--srgb`), so the 16 -> 8 bit reduction is
a plain divide by 257 and not a tone operation. Nothing here is a quality
instrument -- JPEG is lossy and these previews must never be measured. They are
for looking at.

Usage:
    python make_previews.py <arm-dir> [--quality 94] [--sheet-width 400]
"""
import argparse
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None


def to_u8(a):
    """16-bit sRGB to 8-bit. A divide, not a tone curve."""
    if a.dtype == np.uint16:
        return (a // 257).astype(np.uint8)
    if a.dtype == np.uint8:
        return a
    if np.issubdtype(a.dtype, np.floating):
        return (np.clip(a, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    raise SystemExit("unhandled dtype %s" % a.dtype)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm")
    ap.add_argument("--quality", type=int, default=94)
    ap.add_argument("--sheet-width", type=int, default=400)
    args = ap.parse_args()

    arm = os.path.abspath(args.arm)
    if not os.path.isdir(arm):
        raise SystemExit("no such directory: %s" % arm)

    out = os.path.join(arm, "preview")
    os.makedirs(out, exist_ok=True)

    tiffs = sorted(f for f in os.listdir(arm) if f.lower().endswith(".tiff"))
    if not tiffs:
        raise SystemExit("no .tiff in %s" % arm)

    thumbs = []
    for i, f in enumerate(tiffs, 1):
        src = os.path.join(arm, f)
        name = f[: -len(".tiff")]
        dst = os.path.join(out, name + ".jpg")
        a = tifffile.imread(src)
        if a.ndim == 2:
            a = np.dstack([a] * 3)
        if a.shape[2] > 3:
            a = a[:, :, :3]
        im = Image.fromarray(to_u8(a), "RGB")
        im.save(dst, "JPEG", quality=args.quality, subsampling=0, optimize=True)
        mb = os.path.getsize(dst) / 1e6
        print(
            "[%2d/%2d] %-40s %5dx%-5d -> %.1f MB"
            % (i, len(tiffs), name, im.width, im.height, mb),
            flush=True,
        )
        t = im.copy()
        t.thumbnail((args.sheet_width, args.sheet_width), Image.LANCZOS)
        thumbs.append((name, t))

    # Contact sheet. Labels drawn under each cell so a defect can be named
    # without counting rows.
    cols = 5
    pad, label_h = 8, 16
    cw = max(t.width for _, t in thumbs)
    ch = max(t.height for _, t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new(
        "RGB",
        (cols * (cw + pad) + pad, rows * (ch + label_h + pad) + pad),
        (24, 24, 24),
    )
    d = ImageDraw.Draw(sheet)
    for i, (name, t) in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = pad + r * (ch + label_h + pad)
        sheet.paste(t, (x + (cw - t.width) // 2, y))
        d.text((x, y + ch + 2), name[:38], fill=(210, 210, 210))
    sheet_path = os.path.join(out, "_contact-sheet.jpg")
    sheet.save(sheet_path, "JPEG", quality=90, optimize=True)
    print("contact sheet: %s (%dx%d)" % (sheet_path, sheet.width, sheet.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
