"""Tone-matched crop montages of the two patches the owner can see.

Every panel uses the SAME fixed tone transform (the one ORCH-rim/twoside.py used, with
its measured far-field reference hard-coded) so that panels from different renders are
comparable by eye. Nothing here autoscales per panel -- an autoscaled montage makes two
different images look alike and has already misled this project once.

Usage:  python crops.py <label>=<path.tif> [<label>=<path.tif> ...] --out <name.png>
"""
import argparse
import pathlib

import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# Far-field reference measured by ORCH-rim/twoside.py on this subject (its own log).
REF = np.array([18735.0, 19249.0, 18686.0], dtype=np.float32)

# Crop centres are twoside.py's, on the 4688x7040 full-resolution output grid.
CROPS = {
    "upper-lobe": (2112, 2464),
    "lower-lobe": (3168, 3872),
}
SIDE = 700


def rgb_of(p):
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a.astype(np.float32)


def tone(a):
    x = np.clip(a / (REF[None, None, :] / 0.92), 0.0, 1.0)
    return (np.clip(x ** (1 / 2.2), 0, 1) * 255).astype(np.uint8)


def crop_slice(shape, tag):
    h, w = shape[:2]
    cy, cx = CROPS[tag]
    y0 = int(np.clip(cy - SIDE // 2, 0, h - SIDE))
    x0 = int(np.clip(cx - SIDE // 2, 0, w - SIDE))
    return (slice(y0, y0 + SIDE), slice(x0, x0 + SIDE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arms", nargs="+", help="label=path.tif")
    ap.add_argument("--out", required=True, help="output png stem")
    ap.add_argument("--outdir", default=r"C:\dev\strehl-out\BUILD-ELECT\pics")
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    pairs = []
    for a in args.arms:
        label, _, path = a.partition("=")
        pairs.append((label, pathlib.Path(path)))

    for tag in CROPS:
        panels = []
        for label, path in pairs:
            img = rgb_of(path)
            sl = crop_slice(img.shape, tag)
            panels.append(tone(img[sl]))
            print(f"  {tag:<12} {label:<22} {path.name}  shape={img.shape}")
            del img
        montage = np.concatenate(panels, axis=1)
        dst = outdir / f"{args.out}-{tag}.png"
        Image.fromarray(montage).save(dst)
        print(f"wrote {dst}   panels: {' | '.join(l for l, _ in pairs)}")


if __name__ == "__main__":
    main()
