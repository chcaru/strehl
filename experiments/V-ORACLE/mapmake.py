#!/usr/bin/env python3
"""Render the per-tile oracle map for a subject as a viewable PNG.

Three panels, all on the same tile grid:
  1. the delivered master, downscaled, for orientation;
  2. SOURCE-BEST resolvable structure per tile (stage A through-focus contrast);
  3. the merge/source comparison per tile (stage B), where stage B has run.

A map is the deliverable here, not a scalar: the question is WHERE the merge
loses, and a corpus mean cannot say where.

Usage:  python mapmake.py <subject> [--band 2]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

CELL = 22


def colourise(v, lo, hi, bad=None):
    """Blue (low) -> grey -> yellow (high) on a log-ish scale."""
    t = np.clip((np.log10(np.maximum(v, 1e-6)) - np.log10(max(lo, 1e-6)))
                / max(np.log10(max(hi, 1e-6)) - np.log10(max(lo, 1e-6)), 1e-9), 0, 1)
    r = (40 + 215 * t)
    g = (60 + 195 * t)
    b = (150 - 130 * t)
    out = np.stack([r, g, b], -1).astype(np.uint8)
    if bad is not None:
        out[bad] = np.array([120, 30, 30], np.uint8)
    return out


def grid_img(arr, lo, hi, bad=None):
    c = colourise(arr, lo, hi, bad)
    return np.kron(c, np.ones((CELL, CELL, 1), np.uint8))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--band", type=int, default=2)
    args = ap.parse_args()
    b = args.band
    A = np.load(os.path.join(ora.OUT, "stageA", args.subject + ".npz"))
    nr, nc, ts = int(A["nr"]), int(A["nc"]), int(A["tile"])
    con, lo_ = A["contrast"][b], A["lo"][b]
    rel = con / np.maximum(lo_, 1e-9)

    a = tifffile.imread(os.path.join(ora.MASTERS, args.subject + ".tiff"))
    lum = (0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1]
           + 0.0722 * a[:, :, 2]).astype(np.float32)
    thumb = lum[::4, ::4]
    p2, p98 = np.percentile(thumb, [2, 98])
    im = Image.fromarray(
        (np.clip((thumb - p2) / max(p98 - p2, 1), 0, 1) ** (1 / 1.6)
         * 255).astype(np.uint8)
    ).resize((nc * CELL, nr * CELL), Image.BILINEAR).convert("RGB")

    det = con >= np.nanquantile(con, 0.90)
    panels = [np.asarray(im),
              grid_img(rel, np.quantile(rel, 0.05), np.quantile(rel, 0.98))]
    labels = [f"1. delivered master ({args.subject})",
              f"2. SOURCE-BEST resolvable structure, band {b} "
              f"(yellow = some frame resolved detail here, blue = none did)"]

    pB = os.path.join(ora.OUT, "stageB", args.subject + ".npz")
    if os.path.exists(pB):
        B = np.load(pB)
        src = B["src_sig"][b]
        for mode in [str(m) for m in B["modes"]]:
            mrg = B[f"{mode}_sig"][b]
            with np.errstate(invalid="ignore", divide="ignore"):
                ratio = src / np.maximum(mrg, 1e-9)
            bad = (~np.isfinite(ratio)) | (~det)
            # Tiles below the detail threshold are painted flat dark, not
            # coloured: the ratio there is a ratio of two noise estimates and
            # colouring it would invite reading grain as a merge defect --
            # which is exactly how V-bestframe's first statistic went wrong.
            panels.append(grid_img(np.where(bad, 1.0, ratio), 0.4, 2.5, bad))
            labels.append(
                f"{len(panels)}. best-source / merge at DETAIL tiles, "
                f"noise-corrected [{mode}] -- yellow = source beats merge, "
                f"blue = merge wins, dark = no detail available")

    gap = 26
    W = nc * CELL
    H = len(panels) * (nr * CELL + gap) + gap
    sheet = np.full((H, W, 3), 18, np.uint8)
    for i, p in enumerate(panels):
        y = gap + i * (nr * CELL + gap)
        sheet[y:y + nr * CELL, :W] = p[:, :W]
    img = Image.fromarray(sheet)
    d = ImageDraw.Draw(img)
    for i, t in enumerate(labels):
        d.text((6, i * (nr * CELL + gap) + 8), t, fill=(255, 235, 120))
    # The six 1:1 crop sites, drawn on every panel, so the eye's observation
    # and the measurement can be read against each other tile by tile.
    if args.subject == "flowers-cpl":
        try:
            from sites import FLOWERS_SITES, CROP
        except Exception:
            FLOWERS_SITES = []
        for i, (my, mx, note) in enumerate(FLOWERS_SITES):
            col = (255, 60, 60) if "BLURRED" in note else (60, 255, 120)
            x0 = mx / 2.0 / int(A["tile"]) * CELL
            y0 = my / 2.0 / int(A["tile"]) * CELL
            w = CROP / 2.0 / int(A["tile"]) * CELL
            for p in range(len(panels)):
                oy = gap + p * (nr * CELL + gap)
                d.rectangle([x0, oy + y0, x0 + w, oy + y0 + w],
                            outline=col, width=2)
                d.text((x0 + 3, oy + y0 + 2), str(i), fill=col)
    out = os.path.join(ora.OUT, "maps", f"{args.subject}-b{b}.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print(f"wrote {out}  ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
