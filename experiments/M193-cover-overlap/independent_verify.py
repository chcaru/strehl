from __future__ import annotations

import hashlib
import math
import struct
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np

from reference import (
    Q32,
    XY_Q,
    encode_tiff,
    load_json,
    synthetic_rgb,
    warp_synthetic,
)


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS {message}")


def exact_inverse_valid(
    x: int,
    y: int,
    support: dict[str, object],
) -> bool:
    transform = support["transform"]
    a = int(transform["a"])
    b = int(transform["b"])
    tx = int(transform["tx"])
    ty = int(transform["ty"])
    determinant = a * a + b * b
    u = Q32 * x - tx
    v = Q32 * y - ty
    source_x = Fraction(a * u + b * v, determinant)
    source_y = Fraction(-b * u + a * v, determinant)
    guard = Fraction(int(support["guard_q8"]), XY_Q)
    return (
        guard
        <= source_x
        <= int(support["source_width"]) - 1 - guard
        and guard
        <= source_y
        <= int(support["source_height"]) - 1 - guard
    )


def brute_mask(
    width: int,
    height: int,
    supports: list[dict[str, object]],
) -> np.ndarray:
    mask = np.zeros((height, width), dtype=bool)
    for y in range(height):
        for x in range(width):
            mask[y, x] = all(
                exact_inverse_valid(x, y, support) for support in supports
            )
    return mask


def histogram_maximal_rectangle(mask: np.ndarray) -> dict[str, int]:
    heights = np.zeros(mask.shape[1], dtype=np.int64)
    best_key: tuple[int, int, int, int, int] | None = None
    best: dict[str, int] | None = None
    for y in range(mask.shape[0]):
        heights = np.where(mask[y], heights + 1, 0)
        stack: list[int] = []
        for x in range(mask.shape[1] + 1):
            current = int(heights[x]) if x < mask.shape[1] else 0
            while stack and int(heights[stack[-1]]) > current:
                index = stack.pop()
                height = int(heights[index])
                left = stack[-1] + 1 if stack else 0
                width = x - left
                top = y - height + 1
                area = width * height
                key = (-area, top, left, -height, -width)
                if best_key is None or key < best_key:
                    best_key = key
                    best = {
                        "x": left,
                        "y": top,
                        "width": width,
                        "height": height,
                        "area_pixels": area,
                    }
            stack.append(x)
    assert best is not None
    return best


def affine_matrix(
    width: int,
    height: int,
    scale: float,
    rotation_degrees: float,
    tx: float,
    ty: float,
) -> np.ndarray:
    matrix = cv2.getRotationMatrix2D(
        ((width - 1) / 2.0, (height - 1) / 2.0),
        rotation_degrees,
        scale,
    ).astype(np.float64)
    matrix[:, 2] += np.asarray([tx, ty], dtype=np.float64)
    return np.vstack([matrix, np.asarray([0.0, 0.0, 1.0])])


def q32_matrix(record: dict[str, object]) -> np.ndarray:
    transform = record["source_to_reference_q32"]
    return np.asarray(
        [
            [
                int(transform["a"]) / Q32,
                -int(transform["b"]) / Q32,
                int(transform["tx"]) / Q32,
            ],
            [
                int(transform["b"]) / Q32,
                int(transform["a"]) / Q32,
                int(transform["ty"]) / Q32,
            ],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def maximum_corner_error(
    observed: np.ndarray,
    expected: np.ndarray,
    width: int,
    height: int,
) -> float:
    corners = np.asarray(
        [[0.0, 0.0, 1.0], [width - 1.0, 0.0, 1.0],
         [0.0, height - 1.0, 1.0], [width - 1.0, height - 1.0, 1.0]]
    ).T
    delta = observed @ corners - expected @ corners
    return float(np.max(np.sqrt(np.sum(delta[:2] * delta[:2], axis=0))))


def direct_output_retention(
    rectangle: dict[str, int],
    output_width: int,
    output_height: int,
) -> int:
    retained = 0
    for y in range(rectangle["y"], rectangle["y"] + rectangle["height"]):
        for x in range(rectangle["x"], rectangle["x"] + rectangle["width"]):
            retained += int(0 <= x < output_width and 0 <= y < output_height)
    return retained


def main() -> None:
    fixtures = load_json(ROOT / "fixtures.json")
    geometry = fixtures["geometry"]
    mask = brute_mask(
        int(geometry["width"]),
        int(geometry["height"]),
        geometry["supports"],
    )
    rows = []
    for row in mask:
        indices = np.flatnonzero(row)
        rows.append(
            None if len(indices) == 0 else [int(indices[0]), int(indices[-1])]
        )
    require(rows == geometry["row_intervals"], "independent exact row intersection")
    require(
        histogram_maximal_rectangle(mask) == geometry["maximal_rectangle"],
        "independent histogram maximal rectangle",
    )

    overlap = fixtures["synthetic_overlap"]
    synthetic_supports = [
        {
            "transform": source["source_to_reference_q32"],
            "source_width": overlap["native_width"],
            "source_height": overlap["native_height"],
            "guard_q8": source["valid_center_guard_q8"],
        }
        for source in overlap["sources"]
    ]
    synthetic_mask = brute_mask(
        int(overlap["native_width"]),
        int(overlap["native_height"]),
        synthetic_supports,
    )
    require(
        histogram_maximal_rectangle(synthetic_mask) == overlap["common_overlap"],
        "independent full synthetic overlap rectangle",
    )

    base = synthetic_rgb()
    blobs = [
        encode_tiff(base),
        encode_tiff(
            warp_synthetic(
                base,
                scale=0.985,
                rotation_degrees=0.35,
                tx=3.25,
                ty=-2.5,
            )
        ),
        encode_tiff(
            warp_synthetic(
                base,
                scale=1.018,
                rotation_degrees=-0.25,
                tx=-4.0,
                ty=3.0,
            )
        ),
    ]
    digest = hashlib.sha256()
    digest.update(b"M193-INPUT-BUNDLE-V1\x00")
    for blob in sorted(
        blobs,
        key=lambda value: (hashlib.sha256(value).digest(), len(value), value),
    ):
        digest.update(struct.pack(">Q", len(blob)))
        digest.update(blob)
    require(
        digest.hexdigest()
        == fixtures["synthetic_inputs"]["order_invariant_bundle_sha256"],
        "independent byte-bundle hash",
    )

    width = int(overlap["native_width"])
    height = int(overlap["native_height"])
    first_matrix = affine_matrix(width, height, 0.985, 0.35, 3.25, -2.5)
    second_matrix = affine_matrix(width, height, 1.018, -0.25, -4.0, 3.0)
    expected_by_hash = {
        hashlib.sha256(blobs[0]).hexdigest(): first_matrix,
        hashlib.sha256(blobs[1]).hexdigest(): np.eye(3),
        hashlib.sha256(blobs[2]).hexdigest(): first_matrix @ np.linalg.inv(second_matrix),
    }
    errors = []
    for source in overlap["sources"]:
        observed = q32_matrix(source)
        expected = expected_by_hash[source["source_sha256"]]
        errors.append(maximum_corner_error(observed, expected, width, height))
    require(max(errors) <= 0.75, "registration recovers planted corner geometry")

    rectangle = overlap["common_overlap"]
    identity_expected = direct_output_retention(rectangle, width, height)
    crop_expected = direct_output_retention(rectangle, width - 12, height - 10)
    require(
        identity_expected
        == fixtures["output_retention"]["identity"]["retained_pixels"],
        "independent identity-grid retention",
    )
    require(
        crop_expected == fixtures["output_retention"]["cropped"]["retained_pixels"],
        "independent cropped-grid retention",
    )
    require(
        crop_expected * 1000 < rectangle["area_pixels"] * 990,
        "independent cropped-grid 99-percent failure",
    )
    print(f"MAX_PLANTED_CORNER_ERROR_PX {max(errors):.9f}")
    print("VERDICT GREEN")


if __name__ == "__main__":
    main()
