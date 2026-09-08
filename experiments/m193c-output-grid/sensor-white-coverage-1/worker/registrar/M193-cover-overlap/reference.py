from __future__ import annotations

import hashlib
import io
import json
import math
import struct
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence

import cv2
import numpy as np
import tifffile


SCHEMA = "strehl.m193-cover-overlap.v1"
OUTPUT_GRID_SCHEMA = "strehl.m193-output-grid.v1"
Q32 = 1 << 32
XY_Q = 256
LUMA_NUMERATORS = (2_880_402, 7_118_741, 857)
LUMA_DENOMINATOR = 10_000_000
MAX_FEATURES = 1024
MAX_MATCHES = 256
MIN_FIT_MATCHES = 12
MIN_HOLDOUT_MATCHES = 12
RATIO_NUMERATOR = 64
RATIO_DENOMINATOR = 100
INLIER_RADIUS_PX = 2
MAX_HELDOUT_RMS_PX = 1.0
MAX_OUTPUT_SCALE_DISAGREEMENT = 0.001
MAX_OUTPUT_ROTATION_DEGREES = 0.02
MAX_OUTPUT_RESIDUAL_MICROPIXEL = 100_000
ROTATION_TAN_Q62_FLOOR = 1_609_782_167_177_275


class ContractError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ContractError(code, message)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def checked_lowerhex(value: object, label: str) -> str:
    require(
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value),
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        f"{label} must be 64 lowercase hexadecimal characters",
    )
    return value


def round_fraction_ties_even(value: Fraction) -> int:
    numerator = value.numerator
    denominator = value.denominator
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    twice = remainder * 2
    if twice > denominator or (twice == denominator and quotient & 1):
        quotient += 1
    return sign * quotient


def ceil_div(numerator: int, denominator: int) -> int:
    require(
        denominator != 0,
        "UNMEASURED_CHECKER_ERROR",
        "division by zero in exact interval construction",
    )
    return -((-numerator) // denominator)


def ceil_sqrt_ratio(numerator: int, denominator: int) -> int:
    require(
        numerator >= 0 and denominator > 0,
        "UNMEASURED_CHECKER_ERROR",
        "invalid exact square-root ratio",
    )
    if numerator == 0:
        return 0
    guess = math.isqrt((numerator + denominator - 1) // denominator)
    while guess * guess * denominator < numerator:
        guess += 1
    while guess > 0 and (guess - 1) * (guess - 1) * denominator >= numerator:
        guess -= 1
    return guess


def bundle_hash(blobs: Sequence[bytes]) -> str:
    digest = hashlib.sha256()
    digest.update(b"M193-INPUT-BUNDLE-V1\x00")
    for blob in sorted(blobs, key=byte_sort_key):
        digest.update(struct.pack(">Q", len(blob)))
        digest.update(blob)
    return digest.hexdigest()


def byte_sort_key(blob: bytes) -> tuple[bytes, int, bytes]:
    return hashlib.sha256(blob).digest(), len(blob), blob


def _round_nonnegative_array_ties_even(
    numerator: np.ndarray, denominator: int
) -> np.ndarray:
    quotient = numerator // denominator
    remainder = numerator - quotient * denominator
    increment = (remainder * 2 > denominator) | (
        (remainder * 2 == denominator) & ((quotient & 1) == 1)
    )
    return quotient + increment.astype(quotient.dtype)


def prophoto_luma_u16(rgb: np.ndarray) -> np.ndarray:
    require(
        rgb.ndim == 3 and rgb.shape[2] == 3 and rgb.dtype == np.uint16,
        "UNMEASURED_INPUT_CONTRACT_INVALID",
        "common input must decode as HxWx3 uint16",
    )
    values = rgb.astype(np.int64)
    numerator = (
        values[..., 0] * LUMA_NUMERATORS[0]
        + values[..., 1] * LUMA_NUMERATORS[1]
        + values[..., 2] * LUMA_NUMERATORS[2]
    )
    return _round_nonnegative_array_ties_even(
        numerator, LUMA_DENOMINATOR
    ).astype(np.uint16)


def nearest_rank(values: np.ndarray, numerator: int, denominator: int) -> int:
    require(
        values.size > 0 and 0 < numerator <= denominator,
        "UNMEASURED_INPUT_CONTRACT_INVALID",
        "invalid nearest-rank request",
    )
    rank = ceil_div(numerator * int(values.size), denominator)
    index = min(max(rank - 1, 0), int(values.size) - 1)
    return int(np.partition(values.reshape(-1), index)[index])


def registration_u8(rgb: np.ndarray) -> np.ndarray:
    luma = prophoto_luma_u16(rgb)
    low = nearest_rank(luma, 1, 100)
    high = nearest_rank(luma, 99, 100)
    require(
        high > low,
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        "input has no usable 1%-99% luminance span",
    )
    clipped = np.clip(luma.astype(np.int64), low, high) - low
    scaled = _round_nonnegative_array_ties_even(clipped * 255, high - low)
    return scaled.astype(np.uint8)


def decode_input_tiff(blob: bytes) -> np.ndarray:
    try:
        with tifffile.TiffFile(io.BytesIO(blob)) as image:
            require(
                len(image.pages) == 1,
                "UNMEASURED_INPUT_CONTRACT_INVALID",
                "common input TIFF must have exactly one page",
            )
            page = image.pages[0]
            require(
                int(page.compression) == 1,
                "UNMEASURED_INPUT_CONTRACT_INVALID",
                "common input TIFF must be uncompressed",
            )
            orientation = page.tags.get("Orientation")
            require(
                orientation is None or int(orientation.value) == 1,
                "UNMEASURED_INPUT_CONTRACT_INVALID",
                "common input TIFF orientation must be 1",
            )
            pixels = page.asarray()
    except ContractError:
        raise
    except Exception as exc:
        raise ContractError(
            "UNMEASURED_INPUT_CONTRACT_INVALID",
            f"TIFF decode failed: {exc}",
        ) from exc
    require(
        pixels.ndim == 3
        and pixels.shape[2] == 3
        and pixels.dtype == np.uint16,
        "UNMEASURED_INPUT_CONTRACT_INVALID",
        f"expected HxWx3 uint16, found {pixels.shape} {pixels.dtype}",
    )
    return np.asarray(pixels)


@dataclass(frozen=True)
class FeatureSet:
    coordinates_q8: np.ndarray
    descriptors: np.ndarray
    keys: tuple[tuple[Any, ...], ...]


def extract_features(rgb: np.ndarray) -> FeatureSet:
    cv2.setNumThreads(1)
    cv2.ocl.setUseOpenCL(False)
    image = registration_u8(rgb)
    detector = cv2.SIFT_create(
        nfeatures=2048,
        nOctaveLayers=3,
        contrastThreshold=0.01,
        edgeThreshold=12,
        sigma=1.6,
    )
    keypoints, descriptors = detector.detectAndCompute(image, None)
    require(
        descriptors is not None and len(keypoints) >= MIN_FIT_MATCHES * 2,
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        "too few SIFT landmarks",
    )
    records: list[tuple[tuple[Any, ...], tuple[int, int], bytes]] = []
    for keypoint, descriptor in zip(keypoints, descriptors, strict=True):
        require(
            math.isfinite(float(keypoint.response))
            and math.isfinite(float(keypoint.pt[0]))
            and math.isfinite(float(keypoint.pt[1])),
            "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
            "non-finite SIFT landmark",
        )
        x_q8 = int(np.rint(float(keypoint.pt[0]) * XY_Q))
        y_q8 = int(np.rint(float(keypoint.pt[1]) * XY_Q))
        descriptor_u8 = np.clip(np.rint(descriptor), 0, 255).astype(np.uint8)
        descriptor_bytes = descriptor_u8.tobytes()
        response_q = int(np.rint(float(keypoint.response) * 10**12))
        size_q = int(np.rint(float(keypoint.size) * XY_Q))
        angle_q = int(np.rint(float(keypoint.angle) * XY_Q))
        key = (
            -response_q,
            y_q8,
            x_q8,
            size_q,
            angle_q,
            int(keypoint.octave),
            int(keypoint.class_id),
            descriptor_bytes,
        )
        records.append((key, (x_q8, y_q8), descriptor_bytes))
    records.sort(key=lambda record: record[0])
    records = records[:MAX_FEATURES]
    coordinates = np.asarray([record[1] for record in records], dtype=np.int64)
    descriptor_matrix = np.vstack(
        [
            np.frombuffer(record[2], dtype=np.uint8).astype(np.int16)
            for record in records
        ]
    )
    return FeatureSet(
        coordinates_q8=coordinates,
        descriptors=descriptor_matrix,
        keys=tuple(record[0] for record in records),
    )


def nearest_two(
    descriptor: np.ndarray,
    candidates: np.ndarray,
    candidate_keys: Sequence[tuple[Any, ...]],
) -> tuple[int, int, int, int]:
    diff = candidates.astype(np.int32) - descriptor.astype(np.int32)
    distances = np.sum(diff * diff, axis=1, dtype=np.int64)
    first_distance = int(np.min(distances))
    first_candidates = np.flatnonzero(distances == first_distance)
    first = min((int(index) for index in first_candidates), key=candidate_keys.__getitem__)
    masked = distances.copy()
    masked[first] = np.iinfo(np.int64).max
    second_distance = int(np.min(masked))
    second_candidates = np.flatnonzero(masked == second_distance)
    second = min(
        (int(index) for index in second_candidates), key=candidate_keys.__getitem__
    )
    return first, first_distance, second, second_distance


@dataclass(frozen=True)
class Match:
    reference_x_q8: int
    reference_y_q8: int
    source_x_q8: int
    source_y_q8: int
    digest: bytes


def match_features(reference: FeatureSet, source: FeatureSet) -> list[Match]:
    forward = [
        nearest_two(row, source.descriptors, source.keys)
        for row in reference.descriptors
    ]
    reverse = [
        nearest_two(row, reference.descriptors, reference.keys)
        for row in source.descriptors
    ]
    matches: list[Match] = []
    for reference_index, (
        source_index,
        first_distance,
        _,
        second_distance,
    ) in enumerate(forward):
        if reverse[source_index][0] != reference_index:
            continue
        if second_distance <= 0:
            continue
        if (
            first_distance * RATIO_DENOMINATOR
            > second_distance * RATIO_NUMERATOR
        ):
            continue
        rx, ry = (int(value) for value in reference.coordinates_q8[reference_index])
        sx, sy = (int(value) for value in source.coordinates_q8[source_index])
        preimage = (
            b"M193-LANDMARK-SPLIT-V1\x00"
            + struct.pack(">iiii", rx, ry, sx, sy)
            + reference.descriptors[reference_index].astype(np.uint8).tobytes()
            + source.descriptors[source_index].astype(np.uint8).tobytes()
        )
        matches.append(Match(rx, ry, sx, sy, hashlib.sha256(preimage).digest()))
    matches.sort(
        key=lambda item: (
            item.digest,
            item.reference_y_q8,
            item.reference_x_q8,
            item.source_y_q8,
            item.source_x_q8,
        )
    )
    return matches[:MAX_MATCHES]


@dataclass(frozen=True)
class SimilarityQ32:
    a: int
    b: int
    tx: int
    ty: int

    def as_dict(self) -> dict[str, int]:
        return {"a": self.a, "b": self.b, "tx": self.tx, "ty": self.ty}


IDENTITY_Q32 = SimilarityQ32(Q32, 0, 0, 0)


def quantize_similarity(
    a: Fraction, b: Fraction, tx_pixels: Fraction, ty_pixels: Fraction
) -> SimilarityQ32:
    return SimilarityQ32(
        round_fraction_ties_even(a * Q32),
        round_fraction_ties_even(b * Q32),
        round_fraction_ties_even(tx_pixels * Q32),
        round_fraction_ties_even(ty_pixels * Q32),
    )


def pair_hypothesis(first: Match, second: Match) -> SimilarityQ32 | None:
    dsx = second.source_x_q8 - first.source_x_q8
    dsy = second.source_y_q8 - first.source_y_q8
    drx = second.reference_x_q8 - first.reference_x_q8
    dry = second.reference_y_q8 - first.reference_y_q8
    source_denominator = dsx * dsx + dsy * dsy
    reference_denominator = drx * drx + dry * dry
    if (
        source_denominator < (32 * XY_Q) ** 2
        or reference_denominator < (32 * XY_Q) ** 2
    ):
        return None
    a = Fraction(drx * dsx + dry * dsy, source_denominator)
    b = Fraction(dry * dsx - drx * dsy, source_denominator)
    if a * a + b * b < Fraction(1, 4) or a * a + b * b > 4:
        return None
    tx_q8 = Fraction(first.reference_x_q8) - a * first.source_x_q8 + b * first.source_y_q8
    ty_q8 = Fraction(first.reference_y_q8) - b * first.source_x_q8 - a * first.source_y_q8
    return quantize_similarity(a, b, tx_q8 / XY_Q, ty_q8 / XY_Q)


def exact_similarity_fit(matches: Sequence[Match]) -> SimilarityQ32:
    require(
        len(matches) >= 2,
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        "similarity fit needs at least two landmarks",
    )
    count = len(matches)
    sx = sum(item.source_x_q8 for item in matches)
    sy = sum(item.source_y_q8 for item in matches)
    rx = sum(item.reference_x_q8 for item in matches)
    ry = sum(item.reference_y_q8 for item in matches)
    source_energy = sum(
        item.source_x_q8 * item.source_x_q8
        + item.source_y_q8 * item.source_y_q8
        for item in matches
    )
    denominator = count * source_energy - sx * sx - sy * sy
    require(
        denominator > 0,
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        "landmark geometry is singular",
    )
    a_numerator = (
        count
        * sum(
            item.source_x_q8 * item.reference_x_q8
            + item.source_y_q8 * item.reference_y_q8
            for item in matches
        )
        - sx * rx
        - sy * ry
    )
    b_numerator = (
        count
        * sum(
            item.source_x_q8 * item.reference_y_q8
            - item.source_y_q8 * item.reference_x_q8
            for item in matches
        )
        - sx * ry
        + sy * rx
    )
    a = Fraction(a_numerator, denominator)
    b = Fraction(b_numerator, denominator)
    tx_q8 = Fraction(rx - a * sx + b * sy, count)
    ty_q8 = Fraction(ry - b * sx - a * sy, count)
    return quantize_similarity(a, b, tx_q8 / XY_Q, ty_q8 / XY_Q)


def residual_squared_q40(match: Match, transform: SimilarityQ32) -> int:
    predicted_x = (
        transform.a * match.source_x_q8
        - transform.b * match.source_y_q8
        + transform.tx * XY_Q
    )
    predicted_y = (
        transform.b * match.source_x_q8
        + transform.a * match.source_y_q8
        + transform.ty * XY_Q
    )
    residual_x = predicted_x - match.reference_x_q8 * Q32
    residual_y = predicted_y - match.reference_y_q8 * Q32
    return residual_x * residual_x + residual_y * residual_y


def inlier_threshold_squared() -> int:
    return (INLIER_RADIUS_PX * XY_Q * Q32) ** 2


def choose_similarity(matches: Sequence[Match]) -> tuple[SimilarityQ32, list[Match]]:
    require(
        len(matches) >= MIN_FIT_MATCHES,
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        "too few calibration landmarks",
    )
    threshold = inlier_threshold_squared()
    best_key: tuple[int, int, int, int] | None = None
    best_transform: SimilarityQ32 | None = None
    best_inliers: list[Match] = []
    for first_index in range(len(matches) - 1):
        for second_index in range(first_index + 1, len(matches)):
            transform = pair_hypothesis(matches[first_index], matches[second_index])
            if transform is None:
                continue
            residuals = [residual_squared_q40(item, transform) for item in matches]
            inliers = [
                item
                for item, residual in zip(matches, residuals, strict=True)
                if residual <= threshold
            ]
            key = (
                -len(inliers),
                sum(
                    residual
                    for residual in residuals
                    if residual <= threshold
                ),
                first_index,
                second_index,
            )
            if best_key is None or key < best_key:
                best_key = key
                best_transform = transform
                best_inliers = inliers
    require(
        best_transform is not None
        and len(best_inliers) >= MIN_FIT_MATCHES
        and len(best_inliers) * 2 >= len(matches),
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        "no majority landmark consensus",
    )
    seen: set[tuple[tuple[int, int, int, int], ...]] = set()
    current = best_inliers
    for _ in range(8):
        signature = tuple(
            (
                item.reference_x_q8,
                item.reference_y_q8,
                item.source_x_q8,
                item.source_y_q8,
            )
            for item in current
        )
        if signature in seen:
            break
        seen.add(signature)
        fitted = exact_similarity_fit(current)
        updated = [
            item
            for item in matches
            if residual_squared_q40(item, fitted) <= threshold
        ]
        if updated == current:
            return fitted, current
        current = updated
    fitted = exact_similarity_fit(current)
    return fitted, current


def register_to_reference(
    reference: FeatureSet, source: FeatureSet
) -> tuple[SimilarityQ32, dict[str, Any], int]:
    matches = match_features(reference, source)
    require(
        len(matches) >= MIN_FIT_MATCHES + MIN_HOLDOUT_MATCHES,
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        "too few total mutual landmarks",
    )
    calibration = matches[0::2]
    holdout = matches[1::2]
    transform, calibration_inliers = choose_similarity(calibration)
    threshold = inlier_threshold_squared()
    holdout_residuals = [
        (item, residual_squared_q40(item, transform)) for item in holdout
    ]
    holdout_inliers = [
        (item, residual)
        for item, residual in holdout_residuals
        if residual <= threshold
    ]
    require(
        len(holdout_inliers) >= MIN_HOLDOUT_MATCHES
        and len(holdout_inliers) * 2 >= len(holdout),
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        "held-out landmarks lack a majority consensus",
    )
    residual_sum = sum(residual for _, residual in holdout_inliers)
    rms = math.sqrt(residual_sum / len(holdout_inliers)) / (XY_Q * Q32)
    require(
        residual_sum
        <= len(holdout_inliers) * int(MAX_HELDOUT_RMS_PX * XY_Q * Q32) ** 2,
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        f"held-out residual RMS {rms:.9f} px exceeds {MAX_HELDOUT_RMS_PX:.1f}",
    )
    determinant = transform.a * transform.a + transform.b * transform.b
    max_residual = max(residual for _, residual in holdout_inliers)
    max_residual_source_q8 = ceil_sqrt_ratio(max_residual, determinant)
    guard_q8 = max_residual_source_q8 + 1
    metrics = {
        "mutual_match_count": len(matches),
        "calibration_count": len(calibration),
        "calibration_inlier_count": len(calibration_inliers),
        "holdout_count": len(holdout),
        "holdout_inlier_count": len(holdout_inliers),
        "heldout_rms_reference_px": f"{rms:.9f}",
        "heldout_max_source_px_ceil_q8": max_residual_source_q8,
        "coordinate_quantization_guard_q8": 1,
        "valid_support_continuous_margin_q8": XY_Q // 2 + guard_q8,
    }
    return transform, metrics, guard_q8


def linear_range_bounds(
    coefficient: int,
    constant: int,
    lower: int,
    upper: int,
    current_lower: int,
    current_upper: int,
) -> tuple[int, int] | None:
    require(
        lower <= upper,
        "UNMEASURED_CHECKER_ERROR",
        "reversed exact linear range",
    )
    lower_rhs = lower - constant
    upper_rhs = upper - constant
    if coefficient == 0:
        return (
            (current_lower, current_upper)
            if lower_rhs <= 0 <= upper_rhs
            else None
        )
    if coefficient > 0:
        current_lower = max(current_lower, ceil_div(lower_rhs, coefficient))
        current_upper = min(current_upper, upper_rhs // coefficient)
    else:
        current_upper = min(current_upper, lower_rhs // coefficient)
        current_lower = max(current_lower, ceil_div(upper_rhs, coefficient))
    if current_lower > current_upper:
        return None
    return current_lower, current_upper


def inverse_support_interval(
    y: int,
    transform: SimilarityQ32,
    source_width: int,
    source_height: int,
    guard_q8: int,
    current_lower: int,
    current_upper: int,
) -> tuple[int, int] | None:
    determinant = transform.a * transform.a + transform.b * transform.b
    require(
        determinant > 0,
        "UNMEASURED_INPUT_REGISTRATION_INADEQUATE",
        "singular input registration",
    )
    maximum_x_q8 = (source_width - 1) * XY_Q - guard_q8
    maximum_y_q8 = (source_height - 1) * XY_Q - guard_q8
    require(
        guard_q8 <= maximum_x_q8 and guard_q8 <= maximum_y_q8,
        "UNMEASURED_COMMON_OVERLAP_EMPTY",
        "valid-support margin consumes the source",
    )
    x_coefficient = XY_Q * transform.a * Q32
    x_constant = (
        XY_Q * transform.b * Q32 * y
        - XY_Q * (transform.a * transform.tx + transform.b * transform.ty)
    )
    bounds = linear_range_bounds(
        x_coefficient,
        x_constant,
        guard_q8 * determinant,
        maximum_x_q8 * determinant,
        current_lower,
        current_upper,
    )
    if bounds is None:
        return None
    y_coefficient = -XY_Q * transform.b * Q32
    y_constant = (
        XY_Q * transform.a * Q32 * y
        + XY_Q * (transform.b * transform.tx - transform.a * transform.ty)
    )
    return linear_range_bounds(
        y_coefficient,
        y_constant,
        guard_q8 * determinant,
        maximum_y_q8 * determinant,
        bounds[0],
        bounds[1],
    )


def common_row_intervals(
    reference_width: int,
    reference_height: int,
    supports: Sequence[tuple[SimilarityQ32, int, int, int]],
) -> list[tuple[int, int] | None]:
    rows: list[tuple[int, int] | None] = []
    for y in range(reference_height):
        bounds: tuple[int, int] | None = (0, reference_width - 1)
        for transform, width, height, guard_q8 in supports:
            if bounds is None:
                break
            bounds = inverse_support_interval(
                y,
                transform,
                width,
                height,
                guard_q8,
                bounds[0],
                bounds[1],
            )
        rows.append(bounds)
    return rows


def maximal_rectangle(
    rows: Sequence[tuple[int, int] | None],
) -> dict[str, int]:
    best_key: tuple[int, int, int, int, int] | None = None
    best: dict[str, int] | None = None
    for top in range(len(rows)):
        if rows[top] is None:
            continue
        left = rows[top][0]
        right = rows[top][1]
        for bottom in range(top, len(rows)):
            row = rows[bottom]
            if row is None:
                break
            left = max(left, row[0])
            right = min(right, row[1])
            if left > right:
                break
            width = right - left + 1
            height = bottom - top + 1
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
    require(
        best is not None and best["area_pixels"] > 0,
        "UNMEASURED_COMMON_OVERLAP_EMPTY",
        "input supports have no common integer rectangle",
    )
    return best


def manifest_digest(manifest: dict[str, Any]) -> str:
    body = dict(manifest)
    body.pop("manifest_sha256", None)
    return sha256_hex(canonical_json_bytes(body))


def construct_overlap(input_blobs: Sequence[bytes]) -> dict[str, Any]:
    require(
        len(input_blobs) > 0,
        "UNMEASURED_INPUT_CONTRACT_INVALID",
        "capture has no common-input TIFFs",
    )
    multiplicity: dict[bytes, int] = {}
    for blob in input_blobs:
        require(
            isinstance(blob, bytes),
            "UNMEASURED_INPUT_CONTRACT_INVALID",
            "constructor accepts exact TIFF bytes, not paths or decoded arrays",
        )
        multiplicity[blob] = multiplicity.get(blob, 0) + 1
    unique_blobs = sorted(multiplicity, key=byte_sort_key)
    decoded = [decode_input_tiff(blob) for blob in unique_blobs]
    height, width = decoded[0].shape[:2]
    require(
        all(image.shape[:2] == (height, width) for image in decoded),
        "UNMEASURED_INPUT_CONTRACT_INVALID",
        "all common inputs must have identical native dimensions",
    )
    reference_blob = unique_blobs[0]
    reference_features = extract_features(decoded[0]) if len(unique_blobs) > 1 else None
    supports: list[tuple[SimilarityQ32, int, int, int]] = []
    sources: list[dict[str, Any]] = []
    for index, (blob, image) in enumerate(zip(unique_blobs, decoded, strict=True)):
        digest = sha256_hex(blob)
        if index == 0:
            transform = IDENTITY_Q32
            guard_q8 = 0
            registration = {
                "reference": True,
                "heldout_rms_reference_px": "0.000000000",
                "heldout_max_source_px_ceil_q8": 0,
                "coordinate_quantization_guard_q8": 0,
                "valid_support_continuous_margin_q8": XY_Q // 2,
            }
        else:
            require(
                reference_features is not None,
                "UNMEASURED_CHECKER_ERROR",
                "reference features unexpectedly absent",
            )
            transform, registration, guard_q8 = register_to_reference(
                reference_features, extract_features(image)
            )
            registration["reference"] = False
        supports.append((transform, width, height, guard_q8))
        sources.append(
            {
                "source_sha256": digest,
                "byte_length": len(blob),
                "multiplicity": multiplicity[blob],
                "reference": blob == reference_blob,
                "source_to_reference_q32": transform.as_dict(),
                "valid_center_guard_q8": guard_q8,
                "registration": registration,
            }
        )
    rows = common_row_intervals(width, height, supports)
    rectangle = maximal_rectangle(rows)
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "DEFINED_INPUT_ONLY",
        "input_bundle_sha256": bundle_hash(list(input_blobs)),
        "input_count": len(input_blobs),
        "unique_input_count": len(unique_blobs),
        "reference_rule": "minimum (sha256_digest_bytes, byte_length, exact_bytes)",
        "reference_source_sha256": sha256_hex(reference_blob),
        "native_width": width,
        "native_height": height,
        "valid_support_rule": (
            "active pixel-cell footprint eroded by 0.5 px to the valid-centre "
            "domain, plus held-out max residual rounded up to 1/256 source px "
            "and one 1/256-px coordinate quantum"
        ),
        "intersection_rule": "exact Q32 inverse-support inequalities at integer reference centres",
        "maximal_rectangle_tie_break": [
            "maximum area",
            "minimum y",
            "minimum x",
            "maximum height",
            "maximum width",
        ],
        "sources": sources,
        "common_overlap": rectangle,
    }
    manifest["manifest_sha256"] = manifest_digest(manifest)
    return manifest


OUTPUT_GRID_KEYS = {
    "schema",
    "arm_id",
    "overlap_manifest_sha256",
    "input_bundle_sha256",
    "created_before_output",
    "uses_output_bytes",
    "derivation_kind",
    "adapter_sha256",
    "settings_sha256",
    "expected_width",
    "expected_height",
    "valid_center_guard_q8",
    "common_to_output_q32",
    "input_only_landmark_residual_micropixel_ceil",
}


def validate_output_grid(
    descriptor: dict[str, Any], overlap_manifest: dict[str, Any]
) -> SimilarityQ32:
    require(
        isinstance(descriptor, dict) and set(descriptor) == OUTPUT_GRID_KEYS,
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "output-grid descriptor fields are missing or unknown",
    )
    require(
        descriptor["schema"] == OUTPUT_GRID_SCHEMA,
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "output-grid schema is unknown",
    )
    require(
        isinstance(descriptor["arm_id"], str) and descriptor["arm_id"],
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "arm_id is absent",
    )
    require(
        descriptor["overlap_manifest_sha256"]
        == overlap_manifest["manifest_sha256"]
        and descriptor["input_bundle_sha256"]
        == overlap_manifest["input_bundle_sha256"],
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "output grid is not bound to this input-only overlap",
    )
    require(
        descriptor["created_before_output"] is True
        and descriptor["uses_output_bytes"] is False,
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "output-grid mapping must be frozen before and without output bytes",
    )
    require(
        descriptor["derivation_kind"]
        in {"identity_reference_grid", "predeclared_program_grid"},
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "output-grid derivation kind is not admitted",
    )
    checked_lowerhex(descriptor["adapter_sha256"], "adapter_sha256")
    checked_lowerhex(descriptor["settings_sha256"], "settings_sha256")
    width = descriptor["expected_width"]
    height = descriptor["expected_height"]
    guard_q8 = descriptor["valid_center_guard_q8"]
    require(
        isinstance(width, int)
        and isinstance(height, int)
        and width > 0
        and height > 0
        and isinstance(guard_q8, int)
        and guard_q8 >= 0,
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "invalid declared output dimensions or support guard",
    )
    mapping = descriptor["common_to_output_q32"]
    require(
        isinstance(mapping, dict)
        and set(mapping) == {"a", "b", "tx", "ty"}
        and all(isinstance(mapping[key], int) for key in mapping),
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "common-to-output Q32 similarity is malformed",
    )
    transform = SimilarityQ32(
        mapping["a"], mapping["b"], mapping["tx"], mapping["ty"]
    )
    determinant = transform.a * transform.a + transform.b * transform.b
    require(
        determinant > 0,
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "common-to-output mapping is singular",
    )
    residual = descriptor["input_only_landmark_residual_micropixel_ceil"]
    require(
        isinstance(residual, int) and residual >= 0,
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "input-only landmark residual is malformed",
    )
    scale_pass = (
        determinant * 1_000_000 >= Q32 * Q32 * 998_001
        and determinant * 1_000_000 <= Q32 * Q32 * 1_002_001
    )
    rotation_pass = (
        transform.a > 0
        and abs(transform.b) * (1 << 62)
        <= transform.a * ROTATION_TAN_Q62_FLOOR
    )
    if descriptor["derivation_kind"] == "identity_reference_grid":
        require(
            transform == IDENTITY_Q32,
            "UNMEASURED_OUTPUT_GRID_UNDEFINED",
            "identity-reference-grid descriptor must carry the exact identity map",
        )
    require(
        scale_pass
        and rotation_pass
        and residual <= MAX_OUTPUT_RESIDUAL_MICROPIXEL,
        "UNMEASURED_OUTPUT_WARP_INADEQUATE",
        "pre-output grid mapping misses an existing scorecard geometry bar",
    )
    return transform


def direct_support_interval(
    y: int,
    transform: SimilarityQ32,
    output_width: int,
    output_height: int,
    guard_q8: int,
    current_lower: int,
    current_upper: int,
) -> tuple[int, int] | None:
    maximum_x_q8 = (output_width - 1) * XY_Q - guard_q8
    maximum_y_q8 = (output_height - 1) * XY_Q - guard_q8
    require(
        guard_q8 <= maximum_x_q8 and guard_q8 <= maximum_y_q8,
        "UNMEASURED_OUTPUT_GRID_UNDEFINED",
        "output valid-support guard consumes the declared grid",
    )
    x_bounds = linear_range_bounds(
        XY_Q * transform.a,
        XY_Q * (-transform.b * y + transform.tx),
        guard_q8 * Q32,
        maximum_x_q8 * Q32,
        current_lower,
        current_upper,
    )
    if x_bounds is None:
        return None
    return linear_range_bounds(
        XY_Q * transform.b,
        XY_Q * (transform.a * y + transform.ty),
        guard_q8 * Q32,
        maximum_y_q8 * Q32,
        x_bounds[0],
        x_bounds[1],
    )


def output_retention(
    overlap_manifest: dict[str, Any], descriptor: dict[str, Any]
) -> dict[str, Any]:
    transform = validate_output_grid(descriptor, overlap_manifest)
    rectangle = overlap_manifest["common_overlap"]
    x0 = int(rectangle["x"])
    y0 = int(rectangle["y"])
    width = int(rectangle["width"])
    height = int(rectangle["height"])
    expected_width = int(descriptor["expected_width"])
    expected_height = int(descriptor["expected_height"])
    guard_q8 = int(descriptor["valid_center_guard_q8"])
    retained = 0
    for y in range(y0, y0 + height):
        interval = direct_support_interval(
            y,
            transform,
            expected_width,
            expected_height,
            guard_q8,
            x0,
            x0 + width - 1,
        )
        if interval is not None:
            retained += interval[1] - interval[0] + 1
    denominator = width * height
    fraction = Fraction(retained, denominator)
    return {
        "arm_id": descriptor["arm_id"],
        "retained_pixels": retained,
        "denominator_pixels": denominator,
        "retained_fraction_numerator": fraction.numerator,
        "retained_fraction_denominator": fraction.denominator,
        "retained_percent": f"{100.0 * retained / denominator:.9f}",
        "field_of_view_verdict": (
            "PASS"
            if retained * 1000 >= denominator * 990
            else "FAIL_GEOMETRY_FIELD_OF_VIEW"
        ),
    }


def map_point_q32(
    x: int, y: int, transform: SimilarityQ32
) -> tuple[int, int]:
    return (
        transform.a * x - transform.b * y + transform.tx,
        transform.b * x + transform.a * y + transform.ty,
    )


def make_output_grid(
    overlap_manifest: dict[str, Any],
    *,
    arm_id: str,
    expected_width: int,
    expected_height: int,
    transform: SimilarityQ32 = IDENTITY_Q32,
    guard_q8: int = 0,
    derivation_kind: str = "identity_reference_grid",
    residual_micropixel_ceil: int = 0,
) -> dict[str, Any]:
    return {
        "schema": OUTPUT_GRID_SCHEMA,
        "arm_id": arm_id,
        "overlap_manifest_sha256": overlap_manifest["manifest_sha256"],
        "input_bundle_sha256": overlap_manifest["input_bundle_sha256"],
        "created_before_output": True,
        "uses_output_bytes": False,
        "derivation_kind": derivation_kind,
        "adapter_sha256": sha256_hex(b"M193 fixture adapter"),
        "settings_sha256": sha256_hex(b"M193 fixture settings"),
        "expected_width": expected_width,
        "expected_height": expected_height,
        "valid_center_guard_q8": guard_q8,
        "common_to_output_q32": transform.as_dict(),
        "input_only_landmark_residual_micropixel_ceil": residual_micropixel_ceil,
    }


def encode_tiff(rgb: np.ndarray) -> bytes:
    output = io.BytesIO()
    tifffile.imwrite(
        output,
        rgb,
        photometric="rgb",
        compression=None,
        metadata=None,
        byteorder="<",
    )
    return output.getvalue()


def synthetic_rgb(width: int = 384, height: int = 288) -> np.ndarray:
    yy, xx = np.mgrid[0:height, 0:width]
    base = (
        ((xx * 257 + yy * 911) ^ (xx * yy * 17) ^ ((xx >> 2) * 1237))
        & 0xFFFF
    ).astype(np.uint16)
    image = np.empty((height, width, 3), dtype=np.uint16)
    image[..., 0] = (4096 + (base % 52000)).astype(np.uint16)
    image[..., 1] = (2048 + ((base * 3 + xx * 101) % 56000)).astype(np.uint16)
    image[..., 2] = (6144 + ((base * 5 + yy * 173) % 50000)).astype(np.uint16)
    for index in range(36):
        centre = (
            18 + (index * 83) % (width - 36),
            18 + (index * 47) % (height - 36),
        )
        radius = 4 + index % 11
        colour = (
            int(8000 + (index * 3001) % 50000),
            int(10000 + (index * 5003) % 48000),
            int(6000 + (index * 7001) % 52000),
        )
        cv2.circle(image, centre, radius, colour, thickness=-1, lineType=cv2.LINE_8)
    for index in range(18):
        start = (
            (index * 31) % width,
            (index * 59) % height,
        )
        end = (
            (start[0] + 90 + index * 7) % width,
            (start[1] + 50 + index * 11) % height,
        )
        cv2.line(
            image,
            start,
            end,
            (
                int(12000 + index * 1901),
                int(48000 - index * 1301),
                int(9000 + index * 1703),
            ),
            thickness=2 + index % 3,
            lineType=cv2.LINE_8,
        )
    return image


def warp_synthetic(
    reference: np.ndarray,
    *,
    scale: float,
    rotation_degrees: float,
    tx: float,
    ty: float,
) -> np.ndarray:
    height, width = reference.shape[:2]
    matrix = cv2.getRotationMatrix2D(
        ((width - 1) / 2.0, (height - 1) / 2.0),
        rotation_degrees,
        scale,
    )
    matrix[:, 2] += np.asarray([tx, ty])
    return cv2.warpAffine(
        reference,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )


def geometry_fixture() -> dict[str, Any]:
    width = 12
    height = 9
    supports = [
        (IDENTITY_Q32, width, height, 0),
        (
            SimilarityQ32(
                Q32,
                0,
                round_fraction_ties_even(Fraction(3, 4) * Q32),
                round_fraction_ties_even(Fraction(-1, 2) * Q32),
            ),
            width,
            height,
            128,
        ),
        (
            SimilarityQ32(
                Q32,
                0,
                round_fraction_ties_even(Fraction(-5, 4) * Q32),
                round_fraction_ties_even(Fraction(1, 2) * Q32),
            ),
            width,
            height,
            128,
        ),
    ]
    rows = common_row_intervals(width, height, supports)
    return {
        "width": width,
        "height": height,
        "supports": [
            {
                "transform": transform.as_dict(),
                "source_width": source_width,
                "source_height": source_height,
                "guard_q8": guard_q8,
            }
            for transform, source_width, source_height, guard_q8 in supports
        ],
        "row_intervals": [list(row) if row is not None else None for row in rows],
        "maximal_rectangle": maximal_rectangle(rows),
    }


def make_fixtures() -> dict[str, Any]:
    base = synthetic_rgb()
    first = warp_synthetic(
        base, scale=0.985, rotation_degrees=0.35, tx=3.25, ty=-2.5
    )
    second = warp_synthetic(
        base, scale=1.018, rotation_degrees=-0.25, tx=-4.0, ty=3.0
    )
    blobs = [encode_tiff(base), encode_tiff(first), encode_tiff(second)]
    overlap = construct_overlap(blobs)
    identity_grid = make_output_grid(
        overlap,
        arm_id="identity-grid",
        expected_width=overlap["native_width"],
        expected_height=overlap["native_height"],
    )
    crop_grid = make_output_grid(
        overlap,
        arm_id="cropped-grid",
        expected_width=overlap["native_width"] - 12,
        expected_height=overlap["native_height"] - 10,
        derivation_kind="predeclared_program_grid",
    )
    mapping = SimilarityQ32(
        Q32,
        0,
        round_fraction_ties_even(Fraction(5, 4) * Q32),
        round_fraction_ties_even(Fraction(-3, 4) * Q32),
    )
    point = map_point_q32(17, 23, mapping)
    tie_rows = [(0, 1), (0, 1), None, (4, 5), (4, 5)]
    return {
        "schema": "strehl.m193-fixtures.v1",
        "synthetic_inputs": {
            "file_sha256": [sha256_hex(blob) for blob in blobs],
            "byte_lengths": [len(blob) for blob in blobs],
            "order_invariant_bundle_sha256": bundle_hash(blobs),
        },
        "synthetic_overlap": overlap,
        "geometry": geometry_fixture(),
        "tie_break": {
            "rows": [list(row) if row is not None else None for row in tie_rows],
            "expected": maximal_rectangle(tie_rows),
        },
        "mapping_round_trip": {
            "input_xy": [17, 23],
            "transform_q32": mapping.as_dict(),
            "mapped_xy_q32": [point[0], point[1]],
        },
        "output_retention": {
            "identity": output_retention(overlap, identity_grid),
            "cropped": output_retention(overlap, crop_grid),
        },
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(
        (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    )
