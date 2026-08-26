#!/usr/bin/env python3
"""Convert 16-bit sRGB TIFFs to JPEG so display-space instruments can read them.

Why this exists as its own file rather than a line inside another instrument:
scripts/tone_profile.py reads JPEGs only, and the shipped renderer writes TIFF.
Without a converter the shipped path cannot be measured by the project's own
display-space instrument at all -- which is exactly the measurement that matters,
because the gallery I delivered came from the blend-render example binary and
therefore never went through the shipped exposure policy.

The conversion is deliberately dumb. It rescales nothing, chooses nothing, and
applies no curve. 16-bit sRGB in, 8-bit sRGB out, by a right shift. Any tone
difference the instrument then reports is a difference in the RENDERER, not in
this file. A converter that "helped" would make the comparison meaningless.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: tiffjpg.py <dir> [outdir]", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src
    dst.mkdir(parents=True, exist_ok=True)

    tiffs = sorted(p for p in src.glob("*.tif*"))
    if not tiffs:
        print(f"no TIFFs in {src}", file=sys.stderr)
        return 2

    for p in tiffs:
        a = tifffile.imread(str(p))
        if a.dtype == np.uint16:
            a8 = (a >> 8).astype(np.uint8)
        elif a.dtype == np.uint8:
            a8 = a
        else:
            # float path: the renderer emits 0..1 in sRGB display space
            a8 = np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)
        if a8.ndim == 3 and a8.shape[2] > 3:
            a8 = a8[:, :, :3]
        out = dst / (p.stem + ".jpg")
        Image.fromarray(a8).save(out, quality=95, subsampling=0)
        print(f"{p.name:44s} {a.dtype} {a.shape} -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
