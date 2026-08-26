"""ORCH presentation probe -- is part of "these look horrible" a GRADING problem?

NOT A MEASUREMENT TOOL. Everything here is a monotone tone curve plus a
saturation change, i.e. exactly the transformation this project forbids
measuring across. Nothing produced by this script may be fed to any gate,
acceptance test, or numeric comparison. It exists to answer one question that
is about perception, not physics:

    the shipped renders are faithful (linear -> sRGB, one gain, no curve).
    Does a photographer looking at them call them "horrible" because they are
    SOFT, or because they are FLAT?

Those two have completely different fixes and the project has been assuming the
first without testing the second.

Usage:
    python grade.py <in.jpg> <out_sidebyside.jpg> [--label NAME]
"""
import argparse
import sys

import numpy as np
from PIL import Image


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    a = 0.055
    return np.where(x <= 0.04045, x / 12.92, ((x + a) / (1 + a)) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    a = 0.055
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, (1 + a) * x ** (1 / 2.4) - a)


def grade(img: np.ndarray) -> np.ndarray:
    """A conservative, entirely conventional photographic rendering.

    Deliberately boring: a percentile black/white point, a mild filmic S-curve,
    and a modest saturation lift. Nothing here is clever or bespoke -- the point
    is to apply what ANY raw developer would apply by default, so that if the
    result transforms the impression, the deficit was never sharpness.
    """
    lin = srgb_to_linear(img)

    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    # Black point: the 0.1th percentile, so a genuinely black background lands
    # at black instead of at a washed-out dark grey.
    blk = np.percentile(lum, 0.1)
    wht = np.percentile(lum, 99.8)
    if not np.isfinite(blk) or not np.isfinite(wht) or wht <= blk:
        blk, wht = 0.0, 1.0
    lin = (lin - blk) / (wht - blk)
    lin = np.clip(lin, 0.0, None)

    out = linear_to_srgb(lin)

    # Filmic-ish S-curve in display space. Contrast where the midtones are,
    # shoulders that do not clip.
    c = 0.42
    out = np.clip(out, 0.0, 1.0)
    out = out + c * out * (1.0 - out) * (2.0 * out - 1.0) * -1.0
    out = np.clip(out, 0.0, 1.0)

    # Modest saturation. Macro subjects carry real colour that a faithful
    # render leaves on the table.
    g = out @ np.array([0.2126, 0.7152, 0.0722])
    out = np.clip(g[..., None] + (out - g[..., None]) * 1.18, 0.0, 1.0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--label", default="")
    ap.add_argument("--maxw", type=int, default=1400)
    ap.add_argument(
        "--single",
        action="store_true",
        help="write the graded image alone, with no side-by-side and no caption",
    )
    args = ap.parse_args()

    im = Image.open(args.src).convert("RGB")
    if im.width > args.maxw:
        h = round(im.height * args.maxw / im.width)
        im = im.resize((args.maxw, h), Image.LANCZOS)

    a = np.asarray(im).astype(np.float64) / 255.0
    b = grade(a)

    left = (a * 255.0 + 0.5).astype(np.uint8)
    right = (b * 255.0 + 0.5).astype(np.uint8)

    if args.single:
        Image.fromarray(right).save(args.dst, quality=93)
        print(f"  -> {args.dst}  (graded, {right.shape[1]}x{right.shape[0]})")
        return 0

    pad = 8
    h, w, _ = left.shape
    canvas = np.zeros((h + 26, w * 2 + pad, 3), dtype=np.uint8)
    canvas[26:, :w] = left
    canvas[26:, w + pad:] = right

    out = Image.fromarray(canvas)
    from PIL import ImageDraw

    d = ImageDraw.Draw(out)
    tag = f"  {args.label}" if args.label else ""
    d.text((6, 7), f"SHIPPED (faithful, no curve){tag}", fill=(255, 210, 90))
    d.text((w + pad + 6, 7), "SAME FILE, conventional grade  [PRESENTATION ONLY]", fill=(120, 235, 140))
    out.save(args.dst, quality=92)
    print(f"  -> {args.dst}  ({out.width}x{out.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
