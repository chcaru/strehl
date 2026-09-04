"""Development-only scale-plant probe."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy import ndimage

from preflight import decode_arw, estimate_planes, evaluate_measurements


def scale_plane(image: np.ndarray, scale: float) -> np.ndarray:
    center = (np.asarray(image.shape, dtype=np.float64) - 1.0) / 2.0
    matrix = np.eye(2) / scale
    offset = center - matrix @ center
    return ndimage.affine_transform(
        image,
        matrix=matrix,
        offset=offset,
        order=3,
        mode="reflect",
        prefilter=True,
    ).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("ratio", type=float)
    args = parser.parse_args()
    decoded = decode_arw(args.raw.resolve())
    reference = estimate_planes(decoded.green_planes, "reference")
    scored_planes = tuple(
        scale_plane(plane, 1.0 / args.ratio) for plane in decoded.green_planes
    )
    scored = estimate_planes(scored_planes, "TC0")
    print(f"reference={reference['period_green_px']:.8f}")
    print(f"scored={scored['period_green_px']:.8f}")
    print(evaluate_measurements(reference, scored))


if __name__ == "__main__":
    main()
