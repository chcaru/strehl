#!/usr/bin/env python3
"""Print QA: 100% crops at chosen sites, tiled with labels, no resampling.

A contact sheet clears nothing (see contact.py).  This is the instrument that
looks at delivered pixels at 1:1, which is the only scale at which the
question "is this print-worthy" means anything.

Design rules this obeys:

  * NO RESAMPLING of the crop.  A crop is lifted at 1:1 and pasted at 1:1.
    Any scaling would be the instrument inventing or destroying the very
    sharpness under review.
  * Sites are chosen by a stated rule and the rule is printed, so a reader can
    disbelieve the selection.  Selecting crops by output sharpness would
    guarantee a flattering result; these are selected on gradient percentile
    bands, which picks a HIGH-detail site, a TRANSITION site and a FLAT site.
  * Every crop carries its own label and its measured local statistics, so a
    number and the pixels it describes cannot be separated later.

Usage:
    python printqa.py <img> <out.jpg> [--crop N] [--sites a,b,c]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None


def load_rgb(path: str) -> tuple[np.ndarray, float, int]:
    """Pixels, the QUANTISATION STEP they carry, and their distinct-value count.

    The step travels with the pixels because the branch below is chosen by
    FILE EXTENSION, and the number this script stamps looks identical either
    way.  `grad=0.00044` is 29 quantisation steps read from a 16-bit master
    and 0.11 of one level read from an 8-bit preview -- the same five decimal
    places, one of them meaningless, and nothing in the digits says which.

    The distinct-value count is ORCH's provenance-free audit: a correctly read
    16-bit master holds thousands, an 8-bit read holds at most 256.  It needs
    no reference image and no knowledge of what the value should be, which is
    why it is preferred here over trusting this function's own branch.
    """
    if path.lower().endswith((".tif", ".tiff")):
        import tifffile
        a = tifffile.imread(path)
        assert a.dtype == np.uint16, f"expected uint16 TIFF, got {a.dtype}"
        return a.astype(np.float32) / 65535.0, 1.0 / 65535.0, len(np.unique(a))
    im = Image.open(path).convert("RGB")
    a = np.asarray(im)
    return a.astype(np.float32) / 255.0, 1.0 / 255.0, len(np.unique(a))


def grad_map(g: np.ndarray, block: int) -> np.ndarray:
    gy = np.abs(np.diff(g, axis=0))[:, :-1]
    gx = np.abs(np.diff(g, axis=1))[:-1, :]
    m = gy + gx
    h, w = m.shape
    bh, bw = h // block, w // block
    m = m[: bh * block, : bw * block].reshape(bh, block, bw, block)
    return m.mean(axis=(1, 3))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("img")
    ap.add_argument("out")
    ap.add_argument("--crop", type=int, default=520)
    args = ap.parse_args()

    rgb, qstep, nuniq = load_rgb(args.img)
    h, w, _ = rgb.shape
    g = rgb.mean(axis=2)
    c = args.crop

    bm = grad_map(g, c)
    # Guard: ignore blocks that touch the border, where a crop cannot be lifted.
    bm[0, :] = -1
    bm[-1, :] = -1
    bm[:, 0] = -1
    bm[:, -1] = -1
    valid = bm[bm >= 0]
    if valid.size == 0:
        print("image too small for this crop size", file=sys.stderr)
        return 1

    # Site rule, stated: the highest-gradient block (DETAIL), the block nearest
    # the 60th percentile (TRANSITION), and the lowest non-border block (FLAT).
    def pick(target: float) -> tuple[int, int]:
        d = np.where(bm >= 0, np.abs(bm - target), np.inf)
        i = int(np.argmin(d))
        return divmod(i, bm.shape[1])

    sites = [
        ("DETAIL  (max gradient)", pick(valid.max())),
        ("TRANSITION (p60)", pick(float(np.percentile(valid, 60)))),
        ("FLAT   (min gradient)", pick(valid.min())),
    ]

    pad, lab = 8, 22
    sheet = Image.new("RGB", (len(sites) * (c + pad) + pad, c + lab + 2 * pad), (18, 18, 18))
    dr = ImageDraw.Draw(sheet)
    name = os.path.splitext(os.path.basename(args.img))[0]

    print(f"{name}  {w}x{h}  crop={c}px at 1:1, no resampling")
    print(f"  source: {nuniq} distinct values, quantisation step {qstep:.3e}"
          f"{'   <== 8-BIT PATH: re-run from a 16-bit master, do NOT rescale'
             if nuniq <= 256 else ''}")
    for i, (label, (by, bx)) in enumerate(sites):
        y0, x0 = by * c, bx * c
        tile = rgb[y0:y0 + c, x0:x0 + c]
        # Local statistics reported with the pixels they describe.
        tg = tile.mean(axis=2)
        loc_grad = float(np.abs(np.diff(tg, axis=0)).mean() + np.abs(np.diff(tg, axis=1)).mean())
        loc_p50 = float(np.median(tg))
        loc_rng = float(np.ptp(tg))
        # A statistic near its own quantisation floor must say so.  The FLAT
        # site is where this bites: bee-3-cpl reads grad=0.00044, which is 29
        # steps of a 16-bit master and 0.11 of one level of an 8-bit preview.
        steps = loc_grad / qstep
        warn = "  BELOW QUANTISATION FLOOR" if steps < 3.0 else ""
        px = i * (c + pad) + pad
        sheet.paste(Image.fromarray((np.clip(tile, 0, 1) * 255).astype(np.uint8)), (px, pad + lab))
        dr.text((px, pad + 4), f"{label} @({x0},{y0})", fill=(255, 210, 60))
        dr.text((px, pad + lab + c - 14),
                f"grad={loc_grad:.5f} ({steps:.0f}q) p50={loc_p50:.3f} "
                f"range={loc_rng:.3f}", fill=(255, 90, 90) if warn else (120, 255, 160))
        print(f"  {label:<24s} @({x0:5d},{y0:5d})  grad={loc_grad:.5f} "
              f"({steps:.0f} quantisation steps) p50={loc_p50:.3f} "
              f"range={loc_rng:.3f}{warn}")

    sheet.save(args.out, quality=96, subsampling=0)
    print(f"  -> {args.out}  ({sheet.size[0]}x{sheet.size[1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
