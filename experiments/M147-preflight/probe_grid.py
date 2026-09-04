"""Small read-only RAW preview helper used while designing M147."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    with rawpy.imread(str(args.raw)) as raw:
        mosaic = np.array(raw.raw_image_visible, dtype=np.float32, copy=True)
        pattern = np.array(raw.raw_pattern, copy=True)
        black = np.array(raw.black_level_per_channel, dtype=np.float32)
        white = int(raw.white_level)
        sizes = str(raw.sizes)

    height = mosaic.shape[0] // 2 * 2
    width = mosaic.shape[1] // 2 * 2
    blocks = mosaic[:height, :width].reshape(height // 2, 2, width // 2, 2)
    plane_black = black[pattern]
    image = np.mean(blocks - plane_black[np.newaxis, :, np.newaxis, :], axis=(1, 3))
    low, high = np.percentile(image, [0.5, 99.5])
    image = np.clip((image - low) / (high - low), 0.0, 1.0)
    rendered = Image.fromarray(np.uint8(np.round(image * 255.0)), mode="L")
    rendered.thumbnail((1600, 1200), Image.Resampling.LANCZOS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered.save(args.output)

    print(f"path={args.raw.resolve()}")
    print(f"visible_shape={mosaic.shape}")
    print(f"raw_pattern={pattern.tolist()}")
    print(f"black={black.tolist()} white={white}")
    print(f"sizes={sizes}")
    print(f"percentiles={low:.3f},{high:.3f}")
    print(f"preview={args.output.resolve()}")


if __name__ == "__main__":
    main()
