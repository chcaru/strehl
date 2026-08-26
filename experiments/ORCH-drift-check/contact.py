"""Contact sheet: every gallery render at thumbnail size, one image.

Purpose is SURVEY, not judgement.  A thumbnail cannot show sharpness and must
never be used to claim any.  What it does show, and what this exists to catch,
is the class of defect that is GLOBAL: a halo tracing a silhouette, a crushed
region, a tone shift, a colour cast, a frame that failed outright.  Those are
exactly the defects that feature-selected 100% crops are blind to (SS28), and
the whole point of looking at all of them at once is that the eye finds an
outlier in a grid far faster than in a sequence.

Anything flagged here gets the full-resolution treatment.  Nothing is cleared
here.

Usage:
    python contact.py <dir-of-tiffs> <out.jpg> [cols]
"""

import sys
import os
import glob
import numpy as np
import tifffile
from PIL import Image, ImageDraw


def main():
    src, dst = sys.argv[1], sys.argv[2]
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    cell = 460

    paths = sorted(glob.glob(os.path.join(src, "*.tif*")))
    if not paths:
        raise SystemExit(f"no tiffs in {src}")
    print(f"{len(paths)} renders")

    tiles = []
    for p in paths:
        a = tifffile.imread(p)
        assert a.dtype == np.uint16, f"{p}: expected uint16, got {a.dtype}"
        h, w = a.shape[:2]
        k = max(1, int(min(h, w) // cell))
        a = a[::k, ::k]
        im = Image.fromarray((a >> 8).astype(np.uint8))
        im.thumbnail((cell, cell), Image.LANCZOS)
        canvas = Image.new("RGB", (cell, cell), (24, 24, 24))
        canvas.paste(im, ((cell - im.width) // 2, (cell - im.height) // 2))
        d = ImageDraw.Draw(canvas)
        name = os.path.splitext(os.path.basename(p))[0]
        # tone summary beside the name: a thumbnail hides crush, a number does not
        lum = (0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2])
        frac_dark = float(np.count_nonzero(lum < 500)) / lum.size
        label = f"{name}   p50={int(np.median(lum))}  dark<500={100*frac_dark:.2f}%"
        d.rectangle([0, 0, cell, 14], fill=(0, 0, 0))
        d.text((3, 2), label[:78], fill=(255, 210, 60))
        tiles.append(canvas)
        print(f"  {name:<38} p50={int(np.median(lum)):>6}  dark<500={100*frac_dark:6.2f}%")

    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (12, 12, 12))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * cell, (i // cols) * cell))
    sheet.save(dst, quality=92)
    print(f"\n  {dst}  ({sheet.width}x{sheet.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
