"""One reviewable contact sheet of the current gallery, so judging it is unambiguous.

The gallery directory contains BOTH a dark `-srgb.tif` and a well-exposed
`-exposed.tif` for every stack, which means I do not know which one the owner
was looking at when he said the stacks did not look good. That ambiguity has
already cost a night of misdirected attribution, so this emits exactly one
artefact per stack, from the exposed variant, as PNG that opens anywhere.

For each stack: the full frame downscaled so overall rendition is judgeable,
and a 100% crop of the most detailed region so sharpness and seams are
judgeable. Those are different questions and a single image cannot answer both.

The detail region is found on a downsampled copy by gradient energy, which is
the same device `gallery.py` uses, so crops are chosen by the picture rather
than by me picking flattering spots.

READ-ONLY on the renders. Everything goes to a REVIEW-*.png.
"""
import glob
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

OUT = r"C:\dev\strehl-out\ORCH-gallery"
CROP = 1000
THUMB = 760


def detail_peak(gray, box=CROP):
    s = 8
    g = gray[::s, ::s].astype(np.float32)
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    e = gx * gx + gy * gy
    r = max(box // (2 * s), 1)
    c = np.zeros((e.shape[0] + 1, e.shape[1] + 1))
    np.cumsum(np.cumsum(e.astype(np.float64), 0), 1, out=c[1:, 1:])
    H, W = e.shape
    y0, y1 = np.clip(np.arange(H) - r, 0, H), np.clip(np.arange(H) + r, 0, H)
    x0, x1 = np.clip(np.arange(W) - r, 0, W), np.clip(np.arange(W) + r, 0, W)
    tot = (c[np.ix_(y1, x1)] - c[np.ix_(y0, x1)]
           - c[np.ix_(y1, x0)] + c[np.ix_(y0, x0)])
    iy, ix = np.unravel_index(int(np.argmax(tot)), tot.shape)
    return iy * s, ix * s


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 26], fill=(0, 0, 0))
    d.text((8, 6), text, fill=(255, 235, 140))
    return im


def main():
    srcs = sorted(glob.glob(os.path.join(OUT, "*-exposed.tif")))
    # Windows globbing is case-insensitive, so my own -EXPOSED previews match
    # the pattern too. Keep only gallery.py's exposed renders, which apply their
    # gain in linear light before the clamp and are the better artefact.
    srcs = [p for p in srcs if not os.path.basename(p).endswith("-EXPOSED.tif")]
    if not srcs:
        sys.exit("no *-exposed.tif in the gallery")

    fulls, crops = [], []
    print(f"{'stack':<28} {'shape':<20} {'crop at':<16} {'mean':>7}")
    for p in srcs:
        name = os.path.basename(p).replace("-exposed.tif", "")
        a = tifffile.imread(p)
        g = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])
        cy, cx = detail_peak(g)
        cy = int(np.clip(cy, CROP // 2, a.shape[0] - CROP // 2))
        cx = int(np.clip(cx, CROP // 2, a.shape[1] - CROP // 2))
        print(f"{name:<28} {str(a.shape):<20} {f'({cy},{cx})':<16} "
              f"{g.mean() / 65535:>7.4f}")

        full = Image.fromarray((a >> 8).astype(np.uint8)).convert("RGB")
        full.thumbnail((THUMB, THUMB), Image.LANCZOS)
        fulls.append(label(full, name))

        c = a[cy - CROP // 2:cy + CROP // 2, cx - CROP // 2:cx + CROP // 2]
        crop = Image.fromarray((c >> 8).astype(np.uint8)).convert("RGB")
        crop.thumbnail((THUMB, THUMB), Image.LANCZOS)
        crops.append(label(crop, name))

    for tiles, fn, what in ((crops, "REVIEW-CROPS.png", f"{CROP}px detail region"),
                            (fulls, "REVIEW-FULL.png", "full frame")):
        cols = 3
        rowsn = (len(tiles) + cols - 1) // cols
        tw = max(t.width for t in tiles)
        th = max(t.height for t in tiles)
        sheet = Image.new("RGB", (cols * tw + (cols - 1) * 8,
                                  rowsn * th + (rowsn - 1) * 8), (18, 18, 18))
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % cols) * (tw + 8), (i // cols) * (th + 8)))
        p = os.path.join(OUT, fn)
        sheet.save(p)
        print(f"wrote {p}  ({sheet.width}x{sheet.height})  -- {what}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
