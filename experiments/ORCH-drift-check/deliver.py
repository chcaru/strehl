"""Turn the gallery TIFFs into something a human can actually open.

A 189 MB 16-bit TIFF is a deliverable for a printer, not for looking at.  This
writes, per subject:

    <name>.jpg          full resolution, quality 95 -- the viewable stack
    <name>--sheet.jpg   full frame + a UNIFORM 3x3 grid of 100% crops

The grid is uniform on purpose.  Crops chosen by a feature score are blind to
any defect that lacks that feature -- selecting by edge density hid a black
crush over a large contiguous region earlier in this project, and selecting by
flatness would hide the opposite.  A fixed grid cannot flatter the result.

Usage:
    python deliver.py <dir-of-tiffs> <outdir>
"""

import sys
import os
import glob
import numpy as np
import tifffile
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(src, "*.tif*")))
    if not paths:
        raise SystemExit(f"no tiffs in {src}")

    print(f"{'subject':<40} {'MP':>6} {'jpg MB':>8} {'p50':>7} {'clip%':>7}")
    for p in paths:
        name = os.path.splitext(os.path.basename(p))[0]
        a = tifffile.imread(p)
        assert a.dtype == np.uint16, f"{p}: expected uint16, got {a.dtype}"
        h, w = a.shape[:2]

        lum = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
        clip = 100.0 * float(np.count_nonzero(a >= 65535)) / a.size

        eight = (a >> 8).astype(np.uint8)
        im = Image.fromarray(eight)
        dst = os.path.join(out, f"{name}.jpg")
        im.save(dst, quality=95, subsampling=0, optimize=True)
        mb = os.path.getsize(dst) / 1e6

        # review sheet: full frame over a uniform 3x3 of 100% crops
        s = 560
        fit = im.copy()
        fit.thumbnail((3 * s + 2 * 8, 1200), Image.LANCZOS)
        ys = [int(h * f) - s // 2 for f in (0.25, 0.50, 0.75)]
        xs = [int(w * f) - s // 2 for f in (0.25, 0.50, 0.75)]
        cells = []
        for gy in ys:
            row = []
            for gx in xs:
                gy2 = max(0, min(h - s, gy))
                gx2 = max(0, min(w - s, gx))
                c = Image.fromarray(eight[gy2:gy2 + s, gx2:gx2 + s]).copy()
                d = ImageDraw.Draw(c)
                d.rectangle([0, 0, 190, 13], fill=(0, 0, 0))
                d.text((3, 2), f"100%  y{gy2} x{gx2}", fill=(255, 210, 60))
                row.append(c)
            cells.append(row)

        gw = 3 * s + 2 * 8
        sheet = Image.new("RGB", (gw, fit.height + 12 + 3 * s + 2 * 8), (16, 16, 16))
        sheet.paste(fit, ((gw - fit.width) // 2, 0))
        for r, row in enumerate(cells):
            for c2, cell in enumerate(row):
                sheet.paste(cell, (c2 * (s + 8), fit.height + 12 + r * (s + 8)))
        d = ImageDraw.Draw(sheet)
        d.rectangle([0, 0, 560, 15], fill=(0, 0, 0))
        d.text((4, 2), f"{name}   {w}x{h}   p50={int(np.median(lum))}   clip={clip:.3f}%",
               fill=(120, 255, 140))
        sheet.save(os.path.join(out, f"{name}--sheet.jpg"), quality=92, optimize=True)

        print(f"{name:<40} {w*h/1e6:>6.1f} {mb:>8.1f} {int(np.median(lum)):>7} {clip:>7.3f}")
    print(f"\n  {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
