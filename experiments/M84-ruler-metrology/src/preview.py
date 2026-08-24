"""Decode fixed ruler-stack frames to read-only green-luma previews."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image


def green_luma(path: Path) -> tuple[np.ndarray, int, int]:
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible.astype(np.float32)
        black = int(max(raw.black_level_per_channel))
        white = int(raw.white_level)
    height, width = visible.shape
    height -= height % 2
    width -= width % 2
    g1 = visible[:height:2, 1:width:2]
    g2 = visible[1:height:2, :width:2]
    return 0.5 * (g1 + g2) - black, black, white


def render(plane: np.ndarray, destination: Path, step: int = 2) -> None:
    small = plane[::step, ::step]
    lo, hi = np.percentile(small, [0.1, 99.9])
    scaled = np.clip((small - lo) / max(float(hi - lo), 1.0), 0.0, 1.0)
    Image.fromarray(np.round(255.0 * scaled).astype(np.uint8)).save(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stack", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--crop", help="green-plane x0,y0,x1,y1")
    parser.add_argument("--step", type=int, default=2)
    args = parser.parse_args()

    frames = sorted(args.stack.glob("*.ARW"))
    if not frames:
        raise RuntimeError(f"no ARWs in {args.stack}")
    args.output.mkdir(parents=True, exist_ok=True)
    indices = sorted({0, len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4, len(frames) - 1})
    for index in indices:
        plane, black, white = green_luma(frames[index])
        suffix = ""
        if args.crop:
            x0, y0, x1, y1 = (int(value) for value in args.crop.split(","))
            plane = plane[y0:y1, x0:x1]
            suffix = "-crop"
        destination = args.output / f"{args.stack.name}-f{index:03d}.png"
        if suffix:
            destination = destination.with_stem(destination.stem + suffix)
        render(plane, destination, step=args.step)
        print(
            f"{frames[index].name}\tindex={index}\tgreen={plane.shape[1]}x{plane.shape[0]}"
            f"\tblack={black}\twhite={white}\tp01={np.percentile(plane, 1):.3f}"
            f"\tp99={np.percentile(plane, 99):.3f}\toutput={destination}"
        )


if __name__ == "__main__":
    main()
