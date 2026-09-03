"""External LibRaw identity check for COVER Q1.

The expected pixels come from rawpy/LibRaw's copied visible mosaic.  No strehl
decoder or renderer is imported.  See external-decode-preregistration.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rawpy
import tifffile


OUT = Path(r"D:\strehl-out\cover-default")
RAW = OUT / "one-109-ref" / "DSC00020.ARW"
SIDECAR = OUT / "one-109-ref.warpmap.txt"
DIRECT = OUT / "q1-direct.tiff"
NOFIT = OUT / "q1-nofit.tiff"
CROP = OUT / "q1-crop.tiff"
SCALE = OUT / "q1-scale.tiff"

EXPECTED_HASHES = {
    RAW: "77AAEC0B9958B97E8B712332E2A3C67013373623B8BCF52CC5C88B912F0070CA",
    SIDECAR: "4C858562AF44E0646D9E45E445DEBAC17C6C9E4FEC28C325B9E653EB391E6C05",
    DIRECT: "447F1A6EF5212CECCE4890C0823C50E3D66DC65ED23733BC957F0217C31BFCF4",
    NOFIT: "5836AFBBE435760B366E042345D987F96C36CD31ACEE0C3C0AB18D5A2999E436",
    CROP: "9033579443C98A769770F71A239104E3529F53FB152308080A7EE4AC1C72C972",
    SCALE: "23A385AC2E5C0C70B1F436C3D9E5F3C13E905FB8DE9A177AA1D988DAFDBE2FC2",
}

BLACK = np.float32(512.0)
LINEAR_WHITE = np.float32(15360.0)
RANGE = np.float32(LINEAR_WHITE - BLACK)
U16_MAX = np.float32(65535.0)
CROP_ORIGIN = (5, 4)
CROP_SHAPE = (2337, 3506, 3)
RAW_SHAPE = (4688, 7028)
RAW_PATTERN = [[0, 1], [3, 2]]
RAW_COLOR_DESC = "RGBG"
CHANNELS = ("R", "G", "B")


@dataclass(frozen=True)
class DiffStats:
    samples: int
    differing: int
    fraction_differing: float
    max_abs_dn: int
    rms_dn: float
    mean_abs_dn: float


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(memoryview(np.ascontiguousarray(array))).hexdigest().upper()


def verify_frozen_inputs() -> dict[str, str]:
    got: dict[str, str] = {}
    for path, expected in EXPECTED_HASHES.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = file_sha256(path)
        if actual != expected:
            raise ValueError(f"{path}: SHA-256 {actual}, expected frozen {expected}")
        got[str(path)] = actual
    return got


def read_tiff(path: Path) -> np.ndarray:
    array = np.asarray(tifffile.imread(path))
    if array.ndim != 3 or array.shape[2] != 3 or array.dtype != np.uint16:
        raise ValueError(f"{path}: expected uint16 HxWx3, got {array.shape} {array.dtype}")
    return array


def diff_stats(reference: np.ndarray, candidate: np.ndarray) -> DiffStats:
    if reference.shape != candidate.shape:
        raise ValueError(f"shape mismatch: {reference.shape} != {candidate.shape}")
    delta = candidate.astype(np.int64) - reference.astype(np.int64)
    absolute = np.abs(delta)
    differing = int(np.count_nonzero(delta))
    return DiffStats(
        samples=delta.size,
        differing=differing,
        fraction_differing=differing / delta.size,
        max_abs_dn=int(absolute.max(initial=0)),
        rms_dn=float(np.sqrt(np.mean(delta.astype(np.float64) ** 2))),
        mean_abs_dn=float(np.mean(absolute)),
    )


def channel_stats(reference: np.ndarray, candidate: np.ndarray) -> dict[str, dict[str, Any]]:
    result = {"all": asdict(diff_stats(reference, candidate))}
    for index, name in enumerate(CHANNELS):
        result[name] = asdict(diff_stats(reference[..., index], candidate[..., index]))
    return result


def encode_planes(red: np.ndarray, green: np.ndarray, blue: np.ndarray, gains: np.ndarray) -> np.ndarray:
    encoded: list[np.ndarray] = []
    for source, gain in zip((red, green, blue), gains, strict=True):
        scaled = np.multiply(source, np.float32(gain), dtype=np.float32)
        scaled = np.divide(scaled, RANGE, dtype=np.float32)
        scaled = np.minimum(scaled, np.float32(1.0))
        scaled = np.multiply(scaled, U16_MAX, dtype=np.float32)
        scaled = np.add(scaled, np.float32(0.5), dtype=np.float32)
        encoded.append(scaled.astype(np.uint16))
    return np.stack(encoded, axis=-1)


def encode_quad(raw_quad: tuple[int, int, int, int], gains: tuple[float, float, float]) -> tuple[int, int, int]:
    r, g1, g2, b = (np.float32(value) for value in raw_quad)
    r = np.maximum(np.subtract(r, BLACK, dtype=np.float32), np.float32(0.0))
    g1 = np.maximum(np.subtract(g1, BLACK, dtype=np.float32), np.float32(0.0))
    g2 = np.maximum(np.subtract(g2, BLACK, dtype=np.float32), np.float32(0.0))
    b = np.maximum(np.subtract(b, BLACK, dtype=np.float32), np.float32(0.0))
    green = np.multiply(np.add(g1, g2, dtype=np.float32), np.float32(0.5), dtype=np.float32)
    got = encode_planes(
        np.asarray([r], dtype=np.float32),
        np.asarray([green], dtype=np.float32),
        np.asarray([b], dtype=np.float32),
        np.asarray(gains, dtype=np.float32),
    )
    return tuple(int(x) for x in got[0])


def preblack_gain_plant(
    raw_quad: tuple[int, int, int, int], gains: tuple[float, float, float]
) -> tuple[int, int, int]:
    r, g1, g2, b = (np.float32(value) for value in raw_quad)
    gr = np.float32(gains[0])
    gg = np.float32(gains[1])
    gb = np.float32(gains[2])
    red = np.maximum(np.subtract(np.multiply(r, gr), BLACK), np.float32(0.0))
    green_raw = np.multiply(np.add(g1, g2), np.float32(0.5))
    green = np.maximum(np.subtract(np.multiply(green_raw, gg), BLACK), np.float32(0.0))
    blue = np.maximum(np.subtract(np.multiply(b, gb), BLACK), np.float32(0.0))
    return tuple(
        int(x)
        for x in encode_planes(
            np.asarray([red]),
            np.asarray([green]),
            np.asarray([blue]),
            np.ones(3, dtype=np.float32),
        )[0]
    )


def commission_encoder() -> dict[str, Any]:
    fixtures = [
        ((4224, 4224, 11648, 15360), (2.0, 1.0, 0.5), (32768, 32768, 32768)),
        ((7936, 512, 512, 15360), (2.0, 1.0, 0.5), (65535, 0, 32768)),
        ((16383, 15360, 15360, 16383), (1.0, 1.0, 1.0), (65535, 65535, 65535)),
    ]
    rows = []
    for raw_quad, gains, expected in fixtures:
        got = encode_quad(raw_quad, gains)
        if got != expected:
            raise AssertionError(f"literal fixture {raw_quad}: {got}, expected {expected}")
        rows.append({"raw": raw_quad, "gains": gains, "expected": expected, "got": got})

    raw_quad, gains, expected = fixtures[1]
    swapped = encode_quad((raw_quad[3], raw_quad[1], raw_quad[2], raw_quad[0]), gains)
    if swapped == expected:
        raise AssertionError("R/B channel-order plant did not move the literal fixture")
    wrong_order = preblack_gain_plant(fixtures[0][0], fixtures[0][1])
    if wrong_order == fixtures[0][2]:
        raise AssertionError("pre-black gain plant did not move the literal fixture")
    return {
        "fixtures": rows,
        "channel_order_plant": swapped,
        "preblack_gain_plant": wrong_order,
    }


def commission_candidate_comparator(crop: np.ndarray) -> dict[str, Any]:
    y, x, c = crop.shape[0] // 2, crop.shape[1] // 2, 1
    bad = crop.copy()
    bad[y, x, c] ^= np.uint16(0x8000)
    bad_stats = diff_stats(crop, bad)
    if not (
        bad_stats.differing == 1
        and bad_stats.max_abs_dn == 32768
        and bad_stats.fraction_differing == 1.0 / crop.size
    ):
        raise AssertionError(f"candidate XOR 0x8000 plant missed: {bad_stats}")

    better = crop.copy()
    better[y, x, c] ^= np.uint16(0x0001)
    better_stats = diff_stats(crop, better)
    if not (
        better_stats.differing == 1
        and better_stats.max_abs_dn == 1
        and better_stats.rms_dn < bad_stats.rms_dn
    ):
        raise AssertionError(f"candidate XOR 1 improvement missed: {better_stats}")

    restored = diff_stats(crop, crop.copy())
    if restored.differing != 0 or restored.max_abs_dn != 0 or restored.rms_dn != 0.0:
        raise AssertionError(f"candidate restoration was not exact: {restored}")
    return {
        "sample_yxc": [y, x, c],
        "known_defect": asdict(bad_stats),
        "improvement": asdict(better_stats),
        "restored": asdict(restored),
    }


def commission() -> dict[str, Any]:
    hashes = verify_frozen_inputs()
    crop = read_tiff(CROP)
    if crop.shape != CROP_SHAPE:
        raise ValueError(f"{CROP}: shape {crop.shape}, expected {CROP_SHAPE}")
    return {
        "status": "COMMISSIONED",
        "frozen_hashes": hashes,
        "literal_encoder": commission_encoder(),
        "candidate_comparator": commission_candidate_comparator(crop),
    }


def decode_rawpy() -> tuple[np.ndarray, dict[str, Any]]:
    with rawpy.imread(str(RAW)) as raw:
        mosaic = np.array(raw.raw_image_visible, copy=True)
        pattern = np.array(raw.raw_pattern, copy=True).tolist()
        color_desc = bytes(raw.color_desc).decode("ascii", errors="replace").rstrip("\x00")
        metadata = {
            "shape": list(mosaic.shape),
            "dtype": str(mosaic.dtype),
            "raw_pattern": pattern,
            "color_desc": color_desc,
            "black_levels": [float(x) for x in raw.black_level_per_channel],
            "container_white": float(raw.white_level),
            "camera_whitebalance": [float(x) for x in raw.camera_whitebalance],
        }
    return mosaic, metadata


def validate_loader(metadata: dict[str, Any]) -> np.ndarray:
    if metadata["shape"] != list(RAW_SHAPE):
        raise ValueError(f"rawpy shape {metadata['shape']}, expected {list(RAW_SHAPE)}")
    if metadata["dtype"] != "uint16":
        raise ValueError(f"rawpy dtype {metadata['dtype']}, expected uint16")
    if metadata["raw_pattern"] != RAW_PATTERN:
        raise ValueError(f"rawpy pattern {metadata['raw_pattern']}, expected {RAW_PATTERN}")
    if metadata["color_desc"] != RAW_COLOR_DESC:
        raise ValueError(f"rawpy color_desc {metadata['color_desc']}, expected {RAW_COLOR_DESC}")
    if metadata["black_levels"] != [512.0, 512.0, 512.0, 512.0]:
        raise ValueError(f"rawpy black levels {metadata['black_levels']}, expected all 512")
    if metadata["container_white"] != 16383.0:
        raise ValueError(f"rawpy container white {metadata['container_white']}, expected 16383")
    wb = np.asarray(metadata["camera_whitebalance"], dtype=np.float32)
    if wb.size < 3 or not np.all(np.isfinite(wb[:3])) or np.any(wb[:3] <= 0):
        raise ValueError(f"unusable rawpy camera white balance {wb.tolist()}")
    return np.asarray([wb[0] / wb[1], np.float32(1.0), wb[2] / wb[1]], dtype=np.float32)


def external_prediction(
    mosaic: np.ndarray,
    gains: np.ndarray,
    origin: tuple[int, int],
    width: int,
    height: int,
) -> np.ndarray:
    ox, oy = origin
    if ox < 0 or oy < 0 or 2 * (ox + width) > mosaic.shape[1] or 2 * (oy + height) > mosaic.shape[0]:
        raise ValueError(
            f"quad rectangle origin={origin} size={width}x{height} exceeds mosaic {mosaic.shape}"
        )
    sensor = mosaic[2 * oy : 2 * (oy + height), 2 * ox : 2 * (ox + width)]
    red = sensor[0::2, 0::2].astype(np.float32)
    green1 = sensor[0::2, 1::2].astype(np.float32)
    green2 = sensor[1::2, 0::2].astype(np.float32)
    blue = sensor[1::2, 1::2].astype(np.float32)
    red = np.maximum(np.subtract(red, BLACK, dtype=np.float32), np.float32(0.0))
    green1 = np.maximum(np.subtract(green1, BLACK, dtype=np.float32), np.float32(0.0))
    green2 = np.maximum(np.subtract(green2, BLACK, dtype=np.float32), np.float32(0.0))
    blue = np.maximum(np.subtract(blue, BLACK, dtype=np.float32), np.float32(0.0))
    green = np.multiply(
        np.add(green1, green2, dtype=np.float32), np.float32(0.5), dtype=np.float32
    )
    return encode_planes(red, green, blue, gains)


def exact(stats: dict[str, dict[str, Any]]) -> bool:
    return all(
        row["differing"] == 0 and row["max_abs_dn"] == 0 and row["rms_dn"] == 0.0
        for row in stats.values()
    )


def measure() -> tuple[dict[str, Any], bool]:
    preflight = commission()
    first, metadata_first = decode_rawpy()
    second, metadata_second = decode_rawpy()
    hash_first = array_sha256(first)
    hash_second = array_sha256(second)
    if metadata_first != metadata_second or hash_first != hash_second:
        raise AssertionError(
            "two independent rawpy contexts disagreed: "
            f"metadata_equal={metadata_first == metadata_second}, "
            f"hashes={hash_first}/{hash_second}"
        )
    gains = validate_loader(metadata_first)

    crop = read_tiff(CROP)
    direct = read_tiff(DIRECT)
    nofit = read_tiff(NOFIT)
    scale = read_tiff(SCALE)
    expected_crop = external_prediction(first, gains, CROP_ORIGIN, crop.shape[1], crop.shape[0])
    expected_wrong = external_prediction(first, gains, (6, 4), crop.shape[1], crop.shape[0])
    expected_full = external_prediction(first, gains, (0, 0), first.shape[1] // 2, first.shape[0] // 2)

    wrong = channel_stats(expected_wrong, crop)
    right = channel_stats(expected_crop, crop)
    if wrong["all"]["fraction_differing"] <= 0.01:
        raise AssertionError(f"one-quad origin plant was not detected: {wrong['all']}")
    for key in ("fraction_differing", "max_abs_dn", "rms_dn"):
        if not right["all"][key] < wrong["all"][key]:
            raise AssertionError(
                f"correct origin did not improve {key}: right={right['all']}, wrong={wrong['all']}"
            )

    width = expected_full.shape[1]
    direct_overlap = direct[:, :width]
    scale_overlap = scale[:, :width]
    nofit_window = nofit[
        CROP_ORIGIN[1] : CROP_ORIGIN[1] + crop.shape[0],
        CROP_ORIGIN[0] : CROP_ORIGIN[0] + crop.shape[1],
    ]
    direct_stats = channel_stats(expected_full, direct_overlap)
    nofit_stats = channel_stats(expected_crop, nofit_window)
    scale_stats = channel_stats(expected_full, scale_overlap)
    scale_detected = scale_stats["all"]["fraction_differing"] > 0.01

    passed = exact(right) and exact(direct_stats) and exact(nofit_stats) and scale_detected
    payload = {
        "status": "PASS" if passed else "FAIL",
        "commissioning": preflight,
        "external_loader": {
            "metadata": metadata_first,
            "mosaic_sha256_first": hash_first,
            "mosaic_sha256_second": hash_second,
            "normalised_wb_gains_f32": [float(x) for x in gains],
            "full_overlap_shape": list(expected_full.shape),
            "full_overlap_sha256": array_sha256(expected_full),
            "crop_prediction_shape": list(expected_crop.shape),
            "crop_prediction_sha256": array_sha256(expected_crop),
        },
        "origin_control": {
            "wrong_origin_xy": [6, 4],
            "wrong": wrong,
            "correct_origin_xy": list(CROP_ORIGIN),
            "correct": right,
        },
        "comparisons": {
            "external_vs_crop": right,
            "external_vs_direct_overlap": direct_stats,
            "external_vs_nofit_crop_window": nofit_stats,
            "external_vs_scale_overlap": scale_stats,
        },
        "predicates": {
            "crop_exact": exact(right),
            "direct_overlap_exact": exact(direct_stats),
            "nofit_crop_window_exact": exact(nofit_stats),
            "scale_fraction_above_one_percent": scale_detected,
        },
    }
    return payload, passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("commission", "measure"))
    args = parser.parse_args()
    if args.command == "commission":
        print(json.dumps(commission(), indent=2, sort_keys=True))
        return 0
    payload, passed = measure()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
