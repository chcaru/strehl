"""Faithful 16-bit master -> 8-bit viewable, with NO grade applied.

This is the input `grade.py` needs (it reads 8-bit through PIL by design) and it
is also useful on its own: it is what the master actually looks like, at a size
a browser will open, with nothing done to it but a bit-depth reduction and a
resize.

WHAT IS AND IS NOT DONE HERE
----------------------------
Masters are written --srgb, so they already carry the sRGB transfer curve. This
step therefore applies NO curve, NO black point, NO saturation: it takes the
high byte of the existing encoding and resizes. The result is faithful in the
sense that matters -- the only losses are quantisation and scale.

Read with tifffile and asserted uint16. PIL.Image.open silently downconverts
16-bit RGB to 8 bits, which has corrupted results in this project before, and
the failure is invisible because the image still looks right.

The rounding is explicit: (x + 128) >> 8 rounds to nearest rather than
truncating, so the downconvert does not introduce a systematic downward bias of
half a code across the whole frame.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


def to_viewable(src: Path, dst: Path, maxw: int, quality: int) -> tuple[int, int]:
    a = tifffile.imread(str(src))
    if a.dtype != np.uint16:
        raise SystemExit(f"{src}: dtype {a.dtype}, expected uint16 "
                         "(a 16-bit master read as 8-bit is silently wrong)")
    if a.ndim != 3 or a.shape[2] != 3:
        raise SystemExit(f"{src}: expected HxWx3, got {a.shape}")

    eight = ((a.astype(np.uint32) + 128) >> 8).clip(0, 255).astype(np.uint8)
    im = Image.fromarray(eight, mode="RGB")
    if maxw and im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.suffix.lower() in (".jpg", ".jpeg"):
        im.save(dst, quality=quality, subsampling=0)
    else:
        im.save(dst)
    return im.width, im.height


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--maxw", type=int, default=1400,
                    help="0 keeps full resolution")
    ap.add_argument("--quality", type=int, default=95,
                    help="4:4:4 always; chroma subsampling is disabled because "
                         "it destroys exactly the fine colour detail under review")
    args = ap.parse_args()

    if not args.src.exists():
        raise SystemExit(f"missing {args.src}")
    w, h = to_viewable(args.src, args.dst, args.maxw, args.quality)
    print(f"{args.src.name} -> {args.dst.name}  {w}x{h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
