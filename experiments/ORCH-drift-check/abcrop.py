#!/usr/bin/env python3
"""A/B two renders at 1:1 on the same crop, with a chroma-edge readout.

The point of this instrument is that a colour-fringe change is easy to SEE and
easy to fake.  So it does two things at once and prints both:

  * it lifts the SAME rectangle from both arms at 1:1, no resampling, and tiles
    them so the eye can adjudicate;
  * it measures sigma of the channel differences on the crop's edge pixels,
    which is the quantity a lateral-CA correction is supposed to move, and on
    the crop's FLAT pixels, which is the built-in placebo -- a radial channel
    warp must be a near-no-op where there is no edge.

If the flat placebo moves, the comparison is measuring something other than
fringe removal and the numbers should not be believed.

Usage:
    python abcrop.py <A.tiff> <B.tiff> <out.jpg> --x X --y Y [--crop N]
                     [--labels "A,B"]
"""
from __future__ import annotations

import argparse

import numpy as np
import tifffile
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None


def load(path: str) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16 TIFF, got {a.dtype} for {path}"
    return a.astype(np.float32) / 65535.0


def chroma_stats(t: np.ndarray) -> dict[str, float]:
    g = t.mean(axis=2)
    gy = np.zeros_like(g)
    gx = np.zeros_like(g)
    gy[:-1, :] = np.abs(np.diff(g, axis=0))
    gx[:, :-1] = np.abs(np.diff(g, axis=1))
    mag = gy + gx
    hi = mag >= np.percentile(mag, 99.0)
    lo = mag <= np.percentile(mag, 50.0)
    r, gg, b = t[..., 0], t[..., 1], t[..., 2]
    out = {}
    for nm, d in (("R-G", r - gg), ("R-B", r - b), ("B-G", b - gg)):
        out[f"edge {nm}"] = float(d[hi].std())
        out[f"flat {nm}"] = float(d[lo].std())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("out")
    ap.add_argument("--x", type=int, required=True)
    ap.add_argument("--y", type=int, required=True)
    ap.add_argument("--crop", type=int, default=520)
    ap.add_argument("--labels", default="A,B")
    args = ap.parse_args()

    la, lb = args.labels.split(",")
    A, B = load(args.a), load(args.b)
    assert A.shape == B.shape, f"shape mismatch {A.shape} vs {B.shape}"
    c, x, y = args.crop, args.x, args.y
    ta, tb = A[y:y + c, x:x + c], B[y:y + c, x:x + c]

    sa, sb = chroma_stats(ta), chroma_stats(tb)
    print(f"crop {c}x{c} at ({x},{y}), 1:1, no resampling")
    print(f"{'metric':<12s} {la:>12s} {lb:>12s} {'ratio B/A':>11s}")
    print("-" * 50)
    for k in sa:
        ratio = sb[k] / sa[k] if sa[k] else float("nan")
        tag = "  <- placebo" if k.startswith("flat") else ""
        print(f"{k:<12s} {sa[k]:12.5f} {sb[k]:12.5f} {ratio:11.4f}{tag}")

    pad, lab = 8, 20
    sheet = Image.new("RGB", (2 * (c + pad) + pad, c + lab + 2 * pad), (18, 18, 18))
    dr = ImageDraw.Draw(sheet)
    for i, (t, nm) in enumerate(((ta, la), (tb, lb))):
        px = i * (c + pad) + pad
        sheet.paste(Image.fromarray((np.clip(t, 0, 1) * 255).astype(np.uint8)), (px, pad + lab))
        dr.text((px, pad + 4), nm, fill=(255, 210, 60))
    sheet.save(args.out, quality=97, subsampling=0)
    print(f"-> {args.out}  ({sheet.size[0]}x{sheet.size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
