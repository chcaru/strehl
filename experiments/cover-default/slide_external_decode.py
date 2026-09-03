"""Independent LibRaw identity checker for the COVER slide-series control.

This module deliberately shares no decoder, geometry parser, or candidate
implementation with the Rust render path.  It emits JSON to stdout and never
writes a result file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np


BLACK_DN = np.float32(512.0)
USABLE_WHITE_DN = np.float32(15360.0)
LINEAR_RANGE_DN = np.float32(USABLE_WHITE_DN - BLACK_DN)
U16_MAX = np.float32(65535.0)
ZERO = np.float32(0.0)
HALF = np.float32(0.5)
ONE = np.float32(1.0)

EXPECTED_RAW_SHAPE = (4688, 7028)
EXPECTED_PLANE_SHAPE = (2344, 3516)
EXPECTED_PATTERN = ((0, 1), (3, 2))
EXPECTED_COLOR_DESC = b"RGBG"
EXPECTED_CONTAINER_WHITE = 16383
EXPECTED_BLACK_LEVELS = (512.0, 512.0, 512.0, 512.0)
COVER_MARGIN_PX = 3.0
CHANNELS = ("R", "G", "B")
DIFFERENCE_FIELDS = (
    "differing",
    "fraction_differing",
    "max_abs_dn",
    "rms_dn",
    "mean_abs_dn",
)
IDENTITY_BITS = (0x3FF0000000000000, 0, 0, 0)
STRICT_PREREGISTERED_STATUS = "UNMEASURABLE_REFERENCE_NOT_BIT_IDENTITY"
PRODUCT_DIAGNOSTIC_LABEL = "ACTUAL_PRODUCT_DIAGNOSTIC"
F64_HEX = re.compile(r"^[0-9a-f]{16}$")
U64_HEX = re.compile(r"^[0-9a-f]{16}$")
CAPTURE_ROOT = os.path.normcase(os.path.abspath(r"D:\personal\macro"))


@dataclass(frozen=True)
class CaseExpectation:
    name: str
    stack_name: str
    frames: int
    reference: int
    reference_filename: str


EXPECTED_CASES = (
    CaseExpectation(
        "flat-1s",
        "flat-et1s-sw4-cpl",
        60,
        30,
        "DSC00046.ARW",
    ),
    CaseExpectation(
        "flat-2p5s",
        "flat-et2.5s-sw4-cpl",
        61,
        30,
        "DSC00050.ARW",
    ),
    CaseExpectation(
        "flat-6s",
        "flat-et6s-sw4-cpl",
        65,
        32,
        "DSC00047.ARW",
    ),
)
EXPECTED_BY_NAME = {case.name: case for case in EXPECTED_CASES}


@dataclass(frozen=True)
class CaseSpec:
    expected: CaseExpectation
    raw: Path
    sidecar: Path
    crop: Path
    scale: Path

    def inputs(self) -> tuple[tuple[str, Path], ...]:
        return (
            ("reference_raw", self.raw),
            ("full_stack_sidecar", self.sidecar),
            ("crop_tiff", self.crop),
            ("scale_tiff", self.scale),
        )


@dataclass(frozen=True)
class DiffStats:
    samples: int
    differing: int
    fraction_differing: float
    max_abs_dn: int
    rms_dn: float
    mean_abs_dn: float


@dataclass(frozen=True)
class Placement:
    bits: tuple[int, int, int, int]
    values: tuple[float, float, float, float]


@dataclass(frozen=True)
class SidecarGeometry:
    frames: int
    width: int
    height: int
    reference: int
    stack_name: str
    stack_digest: str
    strategy: str
    resampler: str
    heldout_px: float | None
    heldout_bits: str | None
    cycle_floor_px: float | None
    cycle_floor_bits: str | None
    placements: tuple[Placement, ...]
    refused: int


@dataclass(frozen=True)
class RawSnapshot:
    mosaic: np.ndarray
    pattern: np.ndarray
    color_desc: bytes
    black_levels: np.ndarray
    container_white: int
    white_balance: np.ndarray


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return hashlib.sha256(memoryview(contiguous)).hexdigest().upper()


def _absolute(path: str) -> Path:
    return Path(os.path.abspath(os.path.expanduser(path)))


def _refuse_capture_tree(path: Path) -> None:
    candidate = os.path.normcase(os.path.abspath(os.fspath(path)))
    try:
        inside = os.path.commonpath((candidate, CAPTURE_ROOT)) == CAPTURE_ROOT
    except ValueError:
        inside = False
    if inside:
        raise ValueError(
            f"{path}: direct access beneath D:\\personal\\macro is forbidden; "
            "use a frozen private copy"
        )


def parse_case_specs(rows: Sequence[Sequence[str]]) -> tuple[CaseSpec, ...]:
    if len(rows) != len(EXPECTED_CASES):
        raise ValueError(f"measure requires exactly three --case specifications, got {len(rows)}")

    supplied: dict[str, CaseSpec] = {}
    for row in rows:
        if len(row) != 5:
            raise ValueError("each --case needs NAME RAW SIDECAR CROP_TIFF SCALE_TIFF")
        name, raw, sidecar, crop, scale = row
        if name not in EXPECTED_BY_NAME:
            raise ValueError(
                f"unsupported case {name!r}; expected "
                + ", ".join(case.name for case in EXPECTED_CASES)
            )
        if name in supplied:
            raise ValueError(f"duplicate case {name!r}")
        expected = EXPECTED_BY_NAME[name]
        spec = CaseSpec(
            expected=expected,
            raw=_absolute(raw),
            sidecar=_absolute(sidecar),
            crop=_absolute(crop),
            scale=_absolute(scale),
        )
        if spec.raw.name != expected.reference_filename:
            raise ValueError(
                f"{name}: reference RAW is {spec.raw.name!r}, "
                f"expected {expected.reference_filename!r}"
            )
        for _, path in spec.inputs():
            _refuse_capture_tree(path)
        supplied[name] = spec

    want = set(EXPECTED_BY_NAME)
    got = set(supplied)
    if got != want:
        raise ValueError(f"case names are {sorted(got)}, expected {sorted(want)}")

    ordered = tuple(supplied[case.name] for case in EXPECTED_CASES)
    all_paths = [os.path.normcase(os.path.abspath(os.fspath(path))) for case in ordered for _, path in case.inputs()]
    if len(set(all_paths)) != len(all_paths):
        raise ValueError("the twelve frozen case inputs must be distinct files")
    return ordered


def freeze_inputs(cases: Sequence[CaseSpec]) -> dict[str, dict[str, dict[str, str]]]:
    frozen: dict[str, dict[str, dict[str, str]]] = {}
    for case in cases:
        row: dict[str, dict[str, str]] = {}
        for role, path in case.inputs():
            if not path.is_file():
                raise FileNotFoundError(f"{case.expected.name} {role}: {path}")
            row[role] = {
                "path": str(path),
                "sha256": file_sha256(path),
            }
        frozen[case.expected.name] = row
    return frozen


def verify_inputs_unchanged(
    cases: Sequence[CaseSpec],
    frozen: dict[str, dict[str, dict[str, str]]],
) -> None:
    for case in cases:
        for role, path in case.inputs():
            before = frozen[case.expected.name][role]["sha256"]
            after = file_sha256(path)
            if after != before:
                raise RuntimeError(
                    f"{case.expected.name} {role} changed during measurement: "
                    f"{before} -> {after}"
                )


def _require_rgb16(array: np.ndarray, label: str) -> None:
    if (
        not isinstance(array, np.ndarray)
        or array.dtype != np.dtype(np.uint16)
        or array.ndim != 3
        or array.shape[2] != 3
        or array.shape[0] <= 0
        or array.shape[1] <= 0
    ):
        shape = getattr(array, "shape", None)
        dtype = getattr(array, "dtype", None)
        raise ValueError(f"{label}: expected non-empty native uint16 HxWx3, got {shape} {dtype}")


def _diff_stats(reference: np.ndarray, candidate: np.ndarray) -> DiffStats:
    if reference.shape != candidate.shape:
        raise ValueError(f"shape mismatch: {reference.shape} != {candidate.shape}")
    delta = candidate.astype(np.int64) - reference.astype(np.int64)
    absolute = np.abs(delta)
    differing = int(np.count_nonzero(delta))
    return DiffStats(
        samples=int(delta.size),
        differing=differing,
        fraction_differing=float(differing / delta.size),
        max_abs_dn=int(absolute.max(initial=0)),
        rms_dn=float(np.sqrt(np.mean(delta.astype(np.float64) ** 2))),
        mean_abs_dn=float(np.mean(absolute, dtype=np.float64)),
    )


def compare_rgb16(reference: np.ndarray, candidate: np.ndarray) -> dict[str, dict[str, Any]]:
    _require_rgb16(reference, "reference")
    _require_rgb16(candidate, "candidate")
    if reference.shape != candidate.shape:
        raise ValueError(f"shape mismatch: {reference.shape} != {candidate.shape}")
    result = {"overall": asdict(_diff_stats(reference, candidate))}
    for channel, name in enumerate(CHANNELS):
        result[name] = asdict(_diff_stats(reference[..., channel], candidate[..., channel]))
    return result


def _stats_exact(stats: dict[str, dict[str, Any]]) -> bool:
    return all(
        row["differing"] == 0
        and row["fraction_differing"] == 0.0
        and row["max_abs_dn"] == 0
        and row["rms_dn"] == 0.0
        and row["mean_abs_dn"] == 0.0
        for row in stats.values()
    )


def encode_planes(
    red: np.ndarray,
    green: np.ndarray,
    blue: np.ndarray,
    gains: np.ndarray,
) -> np.ndarray:
    encoded: list[np.ndarray] = []
    for source, gain in zip((red, green, blue), gains, strict=True):
        value = np.multiply(source, np.float32(gain), dtype=np.float32)
        value = np.divide(value, LINEAR_RANGE_DN, dtype=np.float32)
        value = np.minimum(value, ONE)
        value = np.multiply(value, U16_MAX, dtype=np.float32)
        value = np.add(value, HALF, dtype=np.float32)
        encoded.append(value.astype(np.uint16))
    return np.stack(encoded, axis=-1)


def encode_quad(
    raw_quad: tuple[int, int, int, int],
    gains: tuple[float, float, float],
) -> tuple[int, int, int]:
    red, green1, green2, blue = (np.float32(value) for value in raw_quad)
    red = np.maximum(np.subtract(red, BLACK_DN, dtype=np.float32), ZERO)
    green1 = np.maximum(np.subtract(green1, BLACK_DN, dtype=np.float32), ZERO)
    green2 = np.maximum(np.subtract(green2, BLACK_DN, dtype=np.float32), ZERO)
    blue = np.maximum(np.subtract(blue, BLACK_DN, dtype=np.float32), ZERO)
    green = np.multiply(
        np.add(green1, green2, dtype=np.float32),
        HALF,
        dtype=np.float32,
    )
    encoded = encode_planes(
        np.asarray([red], dtype=np.float32),
        np.asarray([green], dtype=np.float32),
        np.asarray([blue], dtype=np.float32),
        np.asarray(gains, dtype=np.float32),
    )
    return tuple(int(value) for value in encoded[0])


def _preblack_gain_plant(
    raw_quad: tuple[int, int, int, int],
    gains: tuple[float, float, float],
) -> tuple[int, int, int]:
    red, green1, green2, blue = (np.float32(value) for value in raw_quad)
    gain_r, gain_g, gain_b = (np.float32(value) for value in gains)
    red = np.maximum(
        np.subtract(np.multiply(red, gain_r, dtype=np.float32), BLACK_DN, dtype=np.float32),
        ZERO,
    )
    green_raw = np.multiply(
        np.add(green1, green2, dtype=np.float32),
        HALF,
        dtype=np.float32,
    )
    green = np.maximum(
        np.subtract(
            np.multiply(green_raw, gain_g, dtype=np.float32),
            BLACK_DN,
            dtype=np.float32,
        ),
        ZERO,
    )
    blue = np.maximum(
        np.subtract(np.multiply(blue, gain_b, dtype=np.float32), BLACK_DN, dtype=np.float32),
        ZERO,
    )
    encoded = encode_planes(
        np.asarray([red], dtype=np.float32),
        np.asarray([green], dtype=np.float32),
        np.asarray([blue], dtype=np.float32),
        np.ones(3, dtype=np.float32),
    )
    return tuple(int(value) for value in encoded[0])


def commission_encoder() -> dict[str, Any]:
    fixtures = (
        ((4224, 4224, 11648, 15360), (2.0, 1.0, 0.5), (32768, 32768, 32768)),
        ((7936, 512, 512, 15360), (2.0, 1.0, 0.5), (65535, 0, 32768)),
        ((16383, 15360, 15360, 16383), (1.0, 1.0, 1.0), (65535, 65535, 65535)),
    )
    rows = []
    for raw_quad, gains, expected in fixtures:
        got = encode_quad(raw_quad, gains)
        if got != expected:
            raise AssertionError(f"literal encoder fixture {raw_quad}: got {got}, expected {expected}")
        rows.append(
            {
                "raw_r_g1_g2_b": raw_quad,
                "gains_r_g_b": gains,
                "expected_rgb16": expected,
                "got_rgb16": got,
            }
        )

    raw_quad, gains, expected = fixtures[1]
    channel_order_plant = encode_quad(
        (raw_quad[3], raw_quad[1], raw_quad[2], raw_quad[0]),
        gains,
    )
    if channel_order_plant == expected:
        raise AssertionError("R/B channel-order plant did not move the fixed fixture")
    preblack_plant = _preblack_gain_plant(fixtures[0][0], fixtures[0][1])
    if preblack_plant == fixtures[0][2]:
        raise AssertionError("pre-black gain plant did not move the fixed fixture")
    return {
        "fixtures": rows,
        "channel_order_plant_rgb16": channel_order_plant,
        "preblack_gain_plant_rgb16": preblack_plant,
    }


def candidate_mutation_controls(candidate: np.ndarray) -> dict[str, Any]:
    _require_rgb16(candidate, "candidate mutation control")
    y = candidate.shape[0] // 2
    x = candidate.shape[1] // 2
    channel = 1

    probe = candidate.copy()
    probe[y, x, channel] ^= np.uint16(0x8000)
    known = compare_rgb16(candidate, probe)
    row = known["overall"]
    if not (
        row["differing"] == 1
        and row["max_abs_dn"] == 32768
        and row["fraction_differing"] == 1.0 / candidate.size
    ):
        raise AssertionError(f"candidate XOR 0x8000 plant was not detected exactly: {row}")

    improved_probe = candidate.copy()
    improved_probe[y, x, channel] ^= np.uint16(0x0001)
    improved = compare_rgb16(candidate, improved_probe)
    if not (
        improved["overall"]["differing"] == 1
        and improved["overall"]["max_abs_dn"] == 1
        and improved["overall"]["max_abs_dn"] < row["max_abs_dn"]
        and improved["overall"]["rms_dn"] < row["rms_dn"]
    ):
        raise AssertionError(f"candidate XOR 1 improvement was not detected: {improved['overall']}")

    probe[y, x, channel] ^= np.uint16(0x8000)
    restored = compare_rgb16(candidate, probe)
    if not _stats_exact(restored):
        raise AssertionError(f"candidate restoration was not exact: {restored}")
    return {
        "sample_y_x_channel": [y, x, "G"],
        "xor_0x8000": known,
        "xor_0x0001": improved,
        "restored": restored,
    }


def external_prediction(
    mosaic: np.ndarray,
    site_black: tuple[np.float32, np.float32, np.float32, np.float32],
    gains: np.ndarray,
    origin: tuple[int, int],
    width: int,
    height: int,
) -> np.ndarray:
    if mosaic.dtype != np.dtype(np.uint16) or mosaic.ndim != 2:
        raise ValueError(f"prediction expects a uint16 2-D mosaic, got {mosaic.shape} {mosaic.dtype}")
    ox, oy = origin
    if width <= 0 or height <= 0 or ox < 0 or oy < 0:
        raise ValueError(f"invalid quad rectangle origin={origin} size={width}x{height}")
    if 2 * (ox + width) > mosaic.shape[1] or 2 * (oy + height) > mosaic.shape[0]:
        raise ValueError(
            f"quad rectangle origin={origin} size={width}x{height} "
            f"exceeds mosaic {mosaic.shape}"
        )

    sensor = mosaic[2 * oy : 2 * (oy + height), 2 * ox : 2 * (ox + width)]
    red = sensor[0::2, 0::2].astype(np.float32)
    green1 = sensor[0::2, 1::2].astype(np.float32)
    green2 = sensor[1::2, 0::2].astype(np.float32)
    blue = sensor[1::2, 1::2].astype(np.float32)
    if any(plane.shape != (height, width) for plane in (red, green1, green2, blue)):
        raise ValueError("RGGB site extraction did not produce the requested rectangle")

    red = np.maximum(np.subtract(red, site_black[0], dtype=np.float32), ZERO)
    green1 = np.maximum(np.subtract(green1, site_black[1], dtype=np.float32), ZERO)
    green2 = np.maximum(np.subtract(green2, site_black[2], dtype=np.float32), ZERO)
    blue = np.maximum(np.subtract(blue, site_black[3], dtype=np.float32), ZERO)
    green = np.multiply(
        np.add(green1, green2, dtype=np.float32),
        HALF,
        dtype=np.float32,
    )
    return encode_planes(red, green, blue, gains)


def _commission_origin_control() -> dict[str, Any]:
    plane_height, plane_width = 32, 40
    mosaic = np.empty((2 * plane_height, 2 * plane_width), dtype=np.uint16)
    yy, xx = np.indices((plane_height, plane_width), dtype=np.uint16)
    mosaic[0::2, 0::2] = 1000 + 13 * xx + 17 * yy
    mosaic[0::2, 1::2] = 2000 + 19 * xx + 23 * yy
    mosaic[1::2, 0::2] = 3000 + 29 * xx + 31 * yy
    mosaic[1::2, 1::2] = 4000 + 37 * xx + 41 * yy
    black = (BLACK_DN, BLACK_DN, BLACK_DN, BLACK_DN)
    gains = np.ones(3, dtype=np.float32)
    origin = (5, 4)
    width, height = 24, 20
    candidate = external_prediction(mosaic, black, gains, origin, width, height)
    wrong = external_prediction(mosaic, black, gains, (origin[0] + 1, origin[1]), width, height)
    wrong_stats = compare_rgb16(wrong, candidate)
    corrected_stats = compare_rgb16(candidate.copy(), candidate)
    if wrong_stats["overall"]["fraction_differing"] <= 0.01:
        raise AssertionError(f"one-quad origin plant changed <=1%: {wrong_stats['overall']}")
    for scope in ("overall", *CHANNELS):
        for field in DIFFERENCE_FIELDS:
            if not corrected_stats[scope][field] < wrong_stats[scope][field]:
                raise AssertionError(
                    f"correct origin did not improve {scope}.{field}: "
                    f"{corrected_stats[scope][field]} vs {wrong_stats[scope][field]}"
                )
    return {
        "correct_origin_xy": list(origin),
        "wrong_origin_xy": [origin[0] + 1, origin[1]],
        "wrong": wrong_stats,
        "corrected": corrected_stats,
    }


def _commission_contract_refusals() -> dict[str, str]:
    candidate = np.arange(8 * 10 * 3, dtype=np.uint16).reshape(8, 10, 3)
    messages: dict[str, str] = {}
    try:
        compare_rgb16(candidate, candidate[:, :-1, :])
    except ValueError as error:
        messages["shape_mismatch"] = str(error)
    else:
        raise AssertionError("shape mismatch was accepted")

    four_channel = np.concatenate((candidate, candidate[..., :1]), axis=2)
    try:
        compare_rgb16(candidate, four_channel)
    except ValueError as error:
        messages["channel_mismatch"] = str(error)
    else:
        raise AssertionError("channel mismatch was accepted")
    return messages


def _synthetic_sidecar(
    expected: CaseExpectation,
    reference_bits: tuple[int, int, int, int] = IDENTITY_BITS,
) -> str:
    identity = " ".join(f"{bits:016x}" for bits in IDENTITY_BITS)
    lines = [
        "strehl-warpmap 1",
        f"stack-name {expected.stack_name}",
        "stack-digest 0123456789abcdef",
        f"frames {expected.frames}",
        f"plane {EXPECTED_PLANE_SHAPE[1]}x{EXPECTED_PLANE_SHAPE[0]}",
        f"reference {expected.reference}",
        "strategy synthetic-commission",
        "resampler catmull-rom",
        "heldout-px none",
        "cycle-floor-px none",
    ]
    reference = " ".join(f"{bits:016x}" for bits in reference_bits)
    lines.extend(
        f"{index} placed {reference if index == expected.reference else identity}"
        for index in range(expected.frames)
    )
    lines.append(f"end {expected.frames}")
    return "\n".join(lines) + "\n"


def _reference_gauge(geometry: SidecarGeometry) -> dict[str, Any]:
    placement = geometry.placements[geometry.reference]
    a_re, a_im, b_re, b_im = placement.values
    scale_minus_one = a_re - 1.0
    cx = float(geometry.width) * 0.5
    cy = float(geometry.height) * 0.5
    centered_corners = (
        (-cx, -cy),
        (cx, -cy),
        (-cx, cy),
        (cx, cy),
    )
    displacements = tuple(
        math.hypot(
            scale_minus_one * x - a_im * y + b_re,
            scale_minus_one * y + a_im * x + b_im,
        )
        for x, y in centered_corners
    )
    return {
        "reference_transform_f64_bits": [
            f"{bits:016x}" for bits in placement.bits
        ],
        "exact_identity": placement.bits == IDENTITY_BITS,
        "max_centered_corner_displacement_px": max(displacements),
        "displacement_expression": "|((a - 1) * z + b)|",
    }


def _commission_reference_gauge() -> dict[str, Any]:
    expected = EXPECTED_CASES[0]
    observed_bits = tuple(
        int(token, 16)
        for token in (
            "3fefffffffffffff",
            "3be0000000000000",
            "bc80000000000000",
            "3cb0000000000000",
        )
    )
    source = "<synthetic-product-reference>"
    text = _synthetic_sidecar(expected, observed_bits)

    try:
        _parse_sidecar_text(
            text,
            source,
            expected,
            require_exact_reference=True,
        )
    except ValueError as error:
        strict_refusal = str(error)
    else:
        raise AssertionError("strict sidecar gate accepted a non-bit-identity reference")
    if "not exact serialized f64 identity" not in strict_refusal:
        raise AssertionError(f"strict sidecar gate refused for the wrong reason: {strict_refusal}")

    product = _parse_sidecar_text(
        text,
        source,
        expected,
        require_exact_reference=False,
    )
    gauge = _reference_gauge(product)
    expected_displacement_hex = "0x1.08457c7bf0f44p-42"
    if product.placements[product.reference].bits != observed_bits:
        raise AssertionError("product sidecar gate canonicalized the reference bits")
    if gauge["exact_identity"]:
        raise AssertionError("product reference gauge reported exact identity")
    if float(gauge["max_centered_corner_displacement_px"]).hex() != expected_displacement_hex:
        raise AssertionError(
            "cancellation-resistant reference displacement changed: "
            f"{gauge['max_centered_corner_displacement_px']!r}"
        )

    return {
        "strict_nonidentity_rejected": True,
        "strict_refusal": strict_refusal,
        "product_nonidentity_accepted": True,
        "product_reference_preserved": (
            product.placements[product.reference].bits == observed_bits
        ),
        "expected_max_centered_corner_displacement_f64_hex": expected_displacement_hex,
        "product_reference_gauge": gauge,
    }


def commission() -> dict[str, Any]:
    synthetic = np.arange(18 * 24 * 3, dtype=np.uint16).reshape(18, 24, 3)
    return {
        "status": "COMMISSIONED",
        "input_mode": "IN_MEMORY_ONLY",
        "literal_encoder": commission_encoder(),
        "candidate_comparator": candidate_mutation_controls(synthetic),
        "crop_origin_control": _commission_origin_control(),
        "contract_refusals": _commission_contract_refusals(),
        "reference_gauge": _commission_reference_gauge(),
    }


def _unescape_sidecar(value: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\" or index + 1 == len(value):
            output.append(char)
            index += 1
            continue
        escaped = value[index + 1]
        output.append({"n": "\n", "r": "\r", "\\": "\\"}.get(escaped, escaped))
        index += 2
    return "".join(output)


def _f64_from_hex(token: str, label: str) -> tuple[int, float]:
    if not F64_HEX.fullmatch(token):
        raise ValueError(f"{label}: expected 16 lowercase serialized f64 hex digits, got {token!r}")
    bits = int(token, 16)
    value = struct.unpack(">d", struct.pack(">Q", bits))[0]
    if not math.isfinite(value):
        raise ValueError(f"{label}: placement value is not finite")
    return bits, value


def _sidecar_metric(raw: str, label: str) -> tuple[float | None, str | None]:
    token = raw.split("#", 1)[0].strip()
    if token == "none":
        return None, None
    _, value = _f64_from_hex(token, label)
    return value, token


def _parse_sidecar_text(
    text: str,
    source: str,
    expected: CaseExpectation,
    *,
    require_exact_reference: bool,
) -> SidecarGeometry:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "strehl-warpmap 1":
        found = lines[0].strip() if lines else "<empty>"
        raise ValueError(f"{source}: expected 'strehl-warpmap 1', got {found!r}")

    headers: dict[str, str] = {}
    records: dict[int, Placement | None] = {}
    end_count: int | None = None
    ended = False
    for line_number, raw in enumerate(lines[1:], start=2):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ended:
            raise ValueError(f"{source}:{line_number}: data after end record")
        head, separator, rest = line.partition(" ")
        rest = rest.strip() if separator else ""
        if head == "end":
            fields = line.split("#", 1)[0].split()
            if len(fields) != 2:
                raise ValueError(f"{source}:{line_number}: malformed end record")
            end_count = int(fields[1])
            ended = True
            continue
        if head.isdecimal():
            body = line.split("#", 1)[0].split()
            index = int(head)
            if index in records:
                raise ValueError(f"{source}:{line_number}: duplicate frame {index}")
            if len(body) >= 2 and body[1] == "refused":
                records[index] = None
                continue
            if len(body) != 6 or body[1] != "placed":
                raise ValueError(f"{source}:{line_number}: malformed placement record")
            parsed = tuple(
                _f64_from_hex(token, f"{source}:{line_number} field {field}")
                for field, token in enumerate(body[2:], start=1)
            )
            records[index] = Placement(
                bits=tuple(item[0] for item in parsed),
                values=tuple(item[1] for item in parsed),
            )
            continue
        if head in headers:
            raise ValueError(f"{source}:{line_number}: duplicate header {head!r}")
        headers[head] = rest

    required = {
        "stack-name",
        "stack-digest",
        "frames",
        "plane",
        "reference",
        "strategy",
        "resampler",
        "heldout-px",
        "cycle-floor-px",
    }
    missing = sorted(required - set(headers))
    if missing:
        raise ValueError(f"{source}: missing sidecar headers {missing}")

    frames = int(headers["frames"])
    if frames != expected.frames or frames != 2 * expected.reference + frames % 2:
        raise ValueError(
            f"{expected.name}: sidecar frames/reference rule is {frames}/{expected.reference}, "
            f"expected N={expected.frames} and reference=floor(N/2)"
        )
    if end_count != frames or set(records) != set(range(frames)):
        raise ValueError(
            f"{source}: truncated or non-contiguous records: frames={frames}, "
            f"records={len(records)}, end={end_count}"
        )

    reference = int(headers["reference"])
    if reference != expected.reference or reference != frames // 2:
        raise ValueError(
            f"{expected.name}: reference {reference}, expected {expected.reference}=floor({frames}/2)"
        )
    stack_name = _unescape_sidecar(headers["stack-name"])
    if stack_name != expected.stack_name:
        raise ValueError(
            f"{expected.name}: sidecar stack-name {stack_name!r}, expected {expected.stack_name!r}"
        )
    digest = headers["stack-digest"].strip()
    if not U64_HEX.fullmatch(digest):
        raise ValueError(f"{source}: invalid stack-digest {digest!r}")
    if not headers["strategy"]:
        raise ValueError(f"{source}: empty alignment strategy")
    if headers["resampler"] != "catmull-rom":
        raise ValueError(
            f"{source}: resampler {headers['resampler']!r}, expected 'catmull-rom'"
        )

    plane = headers["plane"].split("x")
    if len(plane) != 2:
        raise ValueError(f"{source}: malformed plane {headers['plane']!r}")
    width, height = (int(value) for value in plane)
    if (height, width) != EXPECTED_PLANE_SHAPE:
        raise ValueError(
            f"{source}: plane {width}x{height}, "
            f"expected {EXPECTED_PLANE_SHAPE[1]}x{EXPECTED_PLANE_SHAPE[0]}"
        )

    refused = sum(value is None for value in records.values())
    if refused:
        raise ValueError(
            f"{source}: expected {frames} placed / 0 refused, "
            f"got {frames-refused}/{refused}"
        )
    placements = tuple(records[index] for index in range(frames))
    if any(value is None for value in placements):
        raise AssertionError("refused placement survived the refusal gate")
    placed = tuple(value for value in placements if value is not None)
    if require_exact_reference and placed[reference].bits != IDENTITY_BITS:
        got = tuple(f"{bits:016x}" for bits in placed[reference].bits)
        raise ValueError(
            f"{source}: reference placement is not exact serialized f64 identity: {got}"
        )

    heldout_px, heldout_bits = _sidecar_metric(headers["heldout-px"], "heldout-px")
    cycle_floor_px, cycle_floor_bits = _sidecar_metric(
        headers["cycle-floor-px"],
        "cycle-floor-px",
    )
    return SidecarGeometry(
        frames=frames,
        width=width,
        height=height,
        reference=reference,
        stack_name=stack_name,
        stack_digest=digest,
        strategy=_unescape_sidecar(headers["strategy"]),
        resampler=headers["resampler"],
        heldout_px=heldout_px,
        heldout_bits=heldout_bits,
        cycle_floor_px=cycle_floor_px,
        cycle_floor_bits=cycle_floor_bits,
        placements=placed,
        refused=refused,
    )


def parse_sidecar(
    path: Path,
    expected: CaseExpectation,
    *,
    require_exact_reference: bool = True,
) -> SidecarGeometry:
    text = path.read_bytes().decode("utf-8", errors="strict")
    return _parse_sidecar_text(
        text,
        str(path),
        expected,
        require_exact_reference=require_exact_reference,
    )


def _corners_are_covered(geometry: SidecarGeometry, k: float) -> bool:
    width = float(geometry.width)
    height = float(geometry.height)
    cx = width * 0.5
    cy = height * 0.5
    corners = (
        (0.0, 0.0),
        (width - 1.0, 0.0),
        (0.0, height - 1.0),
        (width - 1.0, height - 1.0),
    )
    for placement in geometry.placements:
        a_re, a_im, b_re, b_im = placement.values
        scaled_a_re = k * a_re - 0.0 * a_im
        scaled_a_im = k * a_im + 0.0 * a_re
        for x, y in corners:
            dx = x - cx
            dy = y - cy
            sx = scaled_a_re * dx - scaled_a_im * dy + b_re + cx
            sy = scaled_a_re * dy + scaled_a_im * dx + b_im + cy
            if not (
                sx >= COVER_MARGIN_PX
                and sy >= COVER_MARGIN_PX
                and sx <= width - 1.0 - COVER_MARGIN_PX
                and sy <= height - 1.0 - COVER_MARGIN_PX
            ):
                return False
    return True


def cover_scale(geometry: SidecarGeometry) -> float:
    if _corners_are_covered(geometry, 1.0):
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _corners_are_covered(geometry, mid):
            lo = mid
        else:
            hi = mid
    if lo <= 0.0:
        raise ValueError("no positive 3px-margin cover scale exists")
    return lo


def cover_rect(width: int, height: int, k: float) -> tuple[int, int, int, int]:
    def axis(size: int) -> tuple[int, int]:
        extent = float(size)
        low = 0.5 * extent * (1.0 - k)
        high = low + k * (extent - 1.0)
        first = max(0, math.ceil(low))
        last = max(first, min(size - 1, math.floor(high)))
        return first, last - first + 1

    x, crop_width = axis(width)
    y, crop_height = axis(height)
    return x, y, crop_width, crop_height


def read_rgb16_tiff(path: Path) -> np.ndarray:
    import tifffile

    array = np.asarray(tifffile.imread(path))
    _require_rgb16(array, str(path))
    return array


def decode_rawpy(path: Path) -> RawSnapshot:
    import rawpy

    with rawpy.imread(str(path)) as raw:
        mosaic = np.array(raw.raw_image_visible, copy=True)
        pattern = np.array(raw.raw_pattern, copy=True)
        color_desc = bytes(raw.color_desc)
        black_levels = np.array(raw.black_level_per_channel, copy=True)
        container_white = int(raw.white_level)
        white_balance = np.array(raw.camera_whitebalance, copy=True)
    return RawSnapshot(
        mosaic=mosaic,
        pattern=pattern,
        color_desc=color_desc,
        black_levels=black_levels,
        container_white=container_white,
        white_balance=white_balance,
    )


def _feed_array(digest: Any, name: str, array: np.ndarray) -> None:
    digest.update(name.encode("ascii"))
    digest.update(b"\0")
    digest.update(array.dtype.str.encode("ascii"))
    digest.update(b"\0")
    digest.update(struct.pack(">I", array.ndim))
    for size in array.shape:
        digest.update(struct.pack(">Q", size))
    digest.update(memoryview(np.ascontiguousarray(array)))


def raw_metadata_sha256(snapshot: RawSnapshot) -> str:
    digest = hashlib.sha256()
    digest.update(str(snapshot.mosaic.shape).encode("ascii"))
    digest.update(b"\0")
    digest.update(snapshot.mosaic.dtype.str.encode("ascii"))
    _feed_array(digest, "pattern", snapshot.pattern)
    digest.update(b"color-desc\0")
    digest.update(snapshot.color_desc)
    _feed_array(digest, "black-levels", snapshot.black_levels)
    digest.update(b"container-white\0")
    digest.update(struct.pack(">q", snapshot.container_white))
    _feed_array(digest, "white-balance", snapshot.white_balance)
    return digest.hexdigest().upper()


def raw_metadata_equal(first: RawSnapshot, second: RawSnapshot) -> bool:
    arrays_equal = all(
        left.shape == right.shape
        and left.dtype == right.dtype
        and np.ascontiguousarray(left).tobytes() == np.ascontiguousarray(right).tobytes()
        for left, right in (
            (first.pattern, second.pattern),
            (first.black_levels, second.black_levels),
            (first.white_balance, second.white_balance),
        )
    )
    return (
        first.mosaic.shape == second.mosaic.shape
        and first.mosaic.dtype == second.mosaic.dtype
        and first.color_desc == second.color_desc
        and first.container_white == second.container_white
        and arrays_equal
    )


def validate_raw_loader(
    snapshot: RawSnapshot,
) -> tuple[np.ndarray, tuple[np.float32, np.float32, np.float32, np.float32]]:
    if snapshot.mosaic.shape != EXPECTED_RAW_SHAPE:
        raise ValueError(
            f"rawpy visible mosaic {snapshot.mosaic.shape}, expected {EXPECTED_RAW_SHAPE}"
        )
    if snapshot.mosaic.dtype != np.dtype(np.uint16) or snapshot.mosaic.ndim != 2:
        raise ValueError(
            f"rawpy visible mosaic must be native uint16 2-D, "
            f"got {snapshot.mosaic.shape} {snapshot.mosaic.dtype}"
        )
    pattern = tuple(tuple(int(value) for value in row) for row in snapshot.pattern.tolist())
    if pattern != EXPECTED_PATTERN:
        raise ValueError(f"rawpy pattern {pattern}, expected {EXPECTED_PATTERN}")
    if snapshot.color_desc.rstrip(b"\0") != EXPECTED_COLOR_DESC:
        raise ValueError(
            f"rawpy color_desc {snapshot.color_desc!r}, expected {EXPECTED_COLOR_DESC!r}"
        )

    black = np.asarray(snapshot.black_levels)
    if (
        black.shape != (4,)
        or not np.issubdtype(black.dtype, np.number)
        or tuple(float(value) for value in black) != EXPECTED_BLACK_LEVELS
    ):
        raise ValueError(
            f"rawpy black levels {black.tolist()} {black.dtype}, "
            f"expected four levels of 512"
        )
    if snapshot.container_white != EXPECTED_CONTAINER_WHITE:
        raise ValueError(
            f"rawpy container white {snapshot.container_white}, "
            f"expected {EXPECTED_CONTAINER_WHITE}"
        )

    wb = np.asarray(snapshot.white_balance)
    if wb.ndim != 1 or wb.size < 3 or not np.issubdtype(wb.dtype, np.number):
        raise ValueError(f"rawpy camera white balance has unsupported contract: {wb.shape} {wb.dtype}")
    first_three = np.asarray(wb[:3], dtype=np.float64)
    if not np.all(np.isfinite(first_three)) or np.any(first_three <= 0.0):
        raise ValueError(f"rawpy R/G/B white balance is not finite and positive: {first_three.tolist()}")
    wb32 = np.asarray(wb[:3], dtype=np.float32)
    gains = np.asarray(
        [
            np.divide(wb32[0], wb32[1], dtype=np.float32),
            ONE,
            np.divide(wb32[2], wb32[1], dtype=np.float32),
        ],
        dtype=np.float32,
    )
    if not np.all(np.isfinite(gains)) or np.any(gains <= ZERO):
        raise ValueError(f"normalised f32 white balance is unusable: {gains.tolist()}")

    pattern_array = np.asarray(pattern, dtype=np.int64)
    site_black = (
        np.float32(black[pattern_array[0, 0]]),
        np.float32(black[pattern_array[0, 1]]),
        np.float32(black[pattern_array[1, 0]]),
        np.float32(black[pattern_array[1, 1]]),
    )
    return gains, site_black


def _json_float(value: Any) -> float | None:
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _f32_bits(value: np.float32) -> str:
    bits = struct.unpack(">I", struct.pack(">f", float(value)))[0]
    return f"{bits:08x}"


def raw_metadata_report(snapshot: RawSnapshot) -> dict[str, Any]:
    return {
        "visible_mosaic_shape": list(snapshot.mosaic.shape),
        "visible_mosaic_dtype": str(snapshot.mosaic.dtype),
        "raw_pattern": snapshot.pattern.tolist(),
        "color_desc": snapshot.color_desc.rstrip(b"\0").decode("ascii", errors="strict"),
        "black_levels": [float(value) for value in snapshot.black_levels],
        "container_white": snapshot.container_white,
        "camera_whitebalance": [_json_float(value) for value in snapshot.white_balance],
    }


def _origin_control(
    mosaic: np.ndarray,
    site_black: tuple[np.float32, np.float32, np.float32, np.float32],
    gains: np.ndarray,
    crop: np.ndarray,
    rectangle: tuple[int, int, int, int],
) -> tuple[dict[str, Any], np.ndarray, dict[str, dict[str, Any]]]:
    x, y, width, height = rectangle
    correct = external_prediction(mosaic, site_black, gains, (x, y), width, height)
    wrong = external_prediction(mosaic, site_black, gains, (x + 1, y), width, height)
    wrong_stats = compare_rgb16(wrong, crop)
    if wrong_stats["overall"]["fraction_differing"] <= 0.01:
        raise AssertionError(
            f"actual Crop one-quad origin plant changed <=1%: {wrong_stats['overall']}"
        )
    correct_stats = compare_rgb16(correct, crop)
    for scope in ("overall", *CHANNELS):
        for field in DIFFERENCE_FIELDS:
            if not correct_stats[scope][field] < wrong_stats[scope][field]:
                raise AssertionError(
                    f"actual Crop correct origin did not improve {scope}.{field}: "
                    f"{correct_stats[scope][field]} vs {wrong_stats[scope][field]}"
                )
    return (
        {
            "wrong_origin_xy": [x + 1, y],
            "wrong": wrong_stats,
            "correct_origin_xy": [x, y],
            "corrected": correct_stats,
        },
        correct,
        correct_stats,
    )


def measure_case(
    case: CaseSpec,
    frozen: dict[str, dict[str, str]],
    *,
    require_exact_reference: bool = True,
) -> dict[str, Any]:
    geometry = parse_sidecar(
        case.sidecar,
        case.expected,
        require_exact_reference=require_exact_reference,
    )
    reference_gauge = _reference_gauge(geometry)
    k = cover_scale(geometry)
    rectangle = cover_rect(geometry.width, geometry.height, k)
    x, y, crop_width, crop_height = rectangle

    crop = read_rgb16_tiff(case.crop)
    scale = read_rgb16_tiff(case.scale)
    expected_crop_shape = (crop_height, crop_width, 3)
    expected_scale_shape = (geometry.height, geometry.width, 3)
    if crop.shape != expected_crop_shape:
        raise ValueError(
            f"{case.expected.name}: Crop candidate shape {crop.shape}, "
            f"expected sidecar-derived {expected_crop_shape}"
        )
    if scale.shape != expected_scale_shape:
        raise ValueError(
            f"{case.expected.name}: Scale candidate shape {scale.shape}, "
            f"expected full-plane {expected_scale_shape}"
        )

    # Candidate-side controls run before any external comparison is interpreted.
    mutation_controls = candidate_mutation_controls(crop)

    first = decode_rawpy(case.raw)
    second = decode_rawpy(case.raw)
    first_mosaic_hash = array_sha256(first.mosaic)
    second_mosaic_hash = array_sha256(second.mosaic)
    first_metadata_hash = raw_metadata_sha256(first)
    second_metadata_hash = raw_metadata_sha256(second)
    if (
        first_mosaic_hash != second_mosaic_hash
        or first_metadata_hash != second_metadata_hash
        or not raw_metadata_equal(first, second)
    ):
        raise AssertionError(
            f"{case.expected.name}: independent rawpy contexts disagreed: "
            f"mosaics={first_mosaic_hash}/{second_mosaic_hash}, "
            f"metadata={first_metadata_hash}/{second_metadata_hash}"
        )
    gains, site_black = validate_raw_loader(first)

    overlap_height = first.mosaic.shape[0] // 2
    overlap_width = first.mosaic.shape[1] // 2
    if overlap_height != geometry.height or overlap_width > geometry.width:
        raise ValueError(
            f"{case.expected.name}: rawpy overlap {overlap_width}x{overlap_height} "
            f"is incompatible with sidecar plane {geometry.width}x{geometry.height}"
        )
    if x < 0 or y < 0 or x + crop_width > overlap_width or y + crop_height > overlap_height:
        raise ValueError(
            f"{case.expected.name}: sidecar-derived Crop rectangle {rectangle} "
            f"is outside rawpy overlap {overlap_width}x{overlap_height}"
        )
    if x + 1 + crop_width > overlap_width:
        raise ValueError(
            f"{case.expected.name}: one-quad origin control is outside rawpy overlap"
        )

    # The candidate already applied the serialized reference placement.  This
    # independent arm stays a direct sensor Crop so any candidate pixel change
    # remains an exactness failure instead of being canonicalized away here.
    origin_control, crop_prediction, crop_stats = _origin_control(
        first.mosaic,
        site_black,
        gains,
        crop,
        rectangle,
    )
    full_prediction = external_prediction(
        first.mosaic,
        site_black,
        gains,
        (0, 0),
        overlap_width,
        overlap_height,
    )
    scale_overlap = scale[:overlap_height, :overlap_width, :]
    if scale_overlap.shape != full_prediction.shape:
        raise ValueError(
            f"{case.expected.name}: prescribed Scale overlap has {scale_overlap.shape}, "
            f"expected {full_prediction.shape}"
        )
    scale_stats = compare_rgb16(full_prediction, scale_overlap)

    crop_exact = _stats_exact(crop_stats)
    scale_changed = scale_stats["overall"]["fraction_differing"] > 0.01
    passed = crop_exact and scale_changed
    categorical = "CROP_EXACT_SCALE_CHANGED" if passed else (
        "CROP_NOT_EXACT" if not crop_exact else "SCALE_NOT_CHANGED_ABOVE_ONE_PERCENT"
    )

    return {
        "case": case.expected.name,
        "status": "PASS" if passed else "FAIL",
        "categorical_result": categorical,
        "frozen_inputs": frozen,
        "sidecar": {
            "stack_name": geometry.stack_name,
            "stack_digest": geometry.stack_digest,
            "frames": geometry.frames,
            "placed": len(geometry.placements),
            "refused": geometry.refused,
            "reference": geometry.reference,
            "reference_filename": case.expected.reference_filename,
            "reference_transform_f64_bits": reference_gauge[
                "reference_transform_f64_bits"
            ],
            "reference_gauge": reference_gauge,
            "plane_width_height": [geometry.width, geometry.height],
            "strategy": geometry.strategy,
            "resampler": geometry.resampler,
            "heldout_px": geometry.heldout_px,
            "heldout_px_f64_bits": geometry.heldout_bits,
            "cycle_floor_px": geometry.cycle_floor_px,
            "cycle_floor_px_f64_bits": geometry.cycle_floor_bits,
        },
        "geometry": {
            "support_margin_plane_px": COVER_MARGIN_PX,
            "k": k,
            "crop_rect_xywh": list(rectangle),
            "rawpy_full_overlap_xywh": [0, 0, overlap_width, overlap_height],
        },
        "external_loader": {
            "metadata": raw_metadata_report(first),
            "metadata_sha256_first": first_metadata_hash,
            "metadata_sha256_second": second_metadata_hash,
            "mosaic_sha256_first": first_mosaic_hash,
            "mosaic_sha256_second": second_mosaic_hash,
            "normalised_wb_gains_f32": [float(value) for value in gains],
            "normalised_wb_gains_f32_bits": [_f32_bits(value) for value in gains],
        },
        "hashes": {
            "crop_candidate_array_sha256": array_sha256(crop),
            "scale_candidate_array_sha256": array_sha256(scale),
            "crop_prediction_array_sha256": array_sha256(crop_prediction),
            "full_overlap_prediction_array_sha256": array_sha256(full_prediction),
        },
        "candidate_mutation_controls": mutation_controls,
        "crop_origin_control": origin_control,
        "comparisons": {
            "external_vs_crop_full_extent": crop_stats,
            "external_unscaled_full_rawpy_overlap_vs_scale": scale_stats,
        },
        "predicates": {
            "crop_exact_overall_and_r_g_b": crop_exact,
            "scale_fraction_differing_above_one_percent": scale_changed,
        },
    }


def _measure(
    rows: Sequence[Sequence[str]],
    *,
    require_exact_reference: bool,
) -> tuple[dict[str, Any], bool]:
    commissioning = commission()
    cases = parse_case_specs(rows)
    frozen = freeze_inputs(cases)
    results = [
        measure_case(
            case,
            frozen[case.expected.name],
            require_exact_reference=require_exact_reference,
        )
        for case in cases
    ]
    verify_inputs_unchanged(cases, frozen)

    passed = all(row["status"] == "PASS" for row in results)
    verdict = (
        "CROP_EXACT_SCALE_CHANGED_AT_ALL_THREE_EXPOSURES"
        if passed
        else "NOT_CROP_EXACT_SCALE_CHANGED_AT_ALL_THREE_EXPOSURES"
    )
    payload = {
        "status": "PASS" if passed else "FAIL",
        "commissioning": commissioning,
        "cases": results,
        "aggregate": {
            "case_order": [case.name for case in EXPECTED_CASES],
            "categorical_results": {
                row["case"]: row["categorical_result"] for row in results
            },
            "snr_invariance_verdict": verdict,
        },
    }
    return payload, passed


def measure(rows: Sequence[Sequence[str]]) -> tuple[dict[str, Any], bool]:
    return _measure(rows, require_exact_reference=True)


def measure_product(rows: Sequence[Sequence[str]]) -> tuple[dict[str, Any], bool]:
    payload, passed = _measure(rows, require_exact_reference=False)
    payload["result_label"] = PRODUCT_DIAGNOSTIC_LABEL
    payload["strict_preregistered_status"] = STRICT_PREREGISTERED_STATUS
    return payload, passed


def _add_measure_cases(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--case",
        action="append",
        nargs=5,
        required=True,
        metavar=("NAME", "RAW", "SIDECAR", "CROP_TIFF", "SCALE_TIFF"),
        help="repeat exactly three times, once for each registered flat exposure",
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("commission")
    measure_parser = commands.add_parser("measure")
    _add_measure_cases(measure_parser)
    product_parser = commands.add_parser("measure-product")
    _add_measure_cases(product_parser)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "commission":
            payload = commission()
            exit_code = 0
        elif args.command == "measure-product":
            payload, passed = measure_product(args.case)
            exit_code = 0 if passed else 1
        else:
            payload, passed = measure(args.case)
            exit_code = 0 if passed else 1
    except Exception as error:
        payload = {
            "status": "ERROR",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        exit_code = 2
    print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
