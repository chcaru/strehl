"""Shared input-only primitives for the M152 M3/M4 site census.

This module never opens a candidate or comparator output.  Its only image
decoder accepts Sony ARW inputs under the two registered read-only roots.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import rawpy
from scipy import fft, ndimage


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
DEFINITION_PATH = HERE / "census-definition.json"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_definition() -> tuple[dict[str, Any], str]:
    raw = DEFINITION_PATH.read_bytes()
    definition = json.loads(raw)
    if definition.get("schema") != "m152-input-only-site-census-definition-v1":
        raise RuntimeError("unexpected M152 census definition schema")
    return definition, sha256_bytes(raw)


def nearest_rank(values: Iterable[float] | np.ndarray, q: float) -> float:
    array = np.asarray(list(values) if not isinstance(values, np.ndarray) else values)
    if array.size == 0:
        raise ValueError("nearest-rank percentile is undefined for an empty population")
    if not 0.0 < q <= 1.0:
        raise ValueError("q must be in (0, 1]")
    ordered = np.sort(array.astype(np.float64, copy=False), axis=None)
    rank = int(math.ceil(q * ordered.size))
    return float(ordered[rank - 1])


def deterministic_frame_indices(frame_count: int, requested: int) -> list[int]:
    if frame_count <= 0 or requested <= 0:
        raise ValueError("frame counts must be positive")
    if frame_count <= requested:
        return list(range(frame_count))
    denominator = requested - 1
    return [
        (index * (frame_count - 1) + denominator // 2) // denominator
        for index in range(requested)
    ]


def path_is_under(path: Path, roots: Iterable[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


@dataclass(frozen=True)
class DecodedGreen:
    path: Path
    green_luma_dn: np.ndarray
    visible_shape_native_px: tuple[int, int]
    decoded_green_sha256: str
    raw_pattern: list[list[int]]
    color_desc: str
    black_levels_dn: list[float]
    white_level_dn: int
    usable_range_dn: float
    iso: float
    low_rail_fraction: float
    high_rail_fraction: float

    def input_record(self) -> dict[str, Any]:
        stat = self.path.stat()
        return {
            "file": self.path.name,
            "size_bytes": stat.st_size,
            "decoded_green_sha256": self.decoded_green_sha256,
            "visible_shape_native_px": list(self.visible_shape_native_px),
            "iso": self.iso,
            "black_levels_dn": self.black_levels_dn,
            "white_level_dn": self.white_level_dn,
            "low_rail_fraction": self.low_rail_fraction,
            "high_rail_fraction": self.high_rail_fraction,
        }


def decode_green(
    path: Path, allowed_roots: Iterable[Path], registered_iso: float
) -> DecodedGreen:
    path = path.resolve()
    if not path_is_under(path, allowed_roots):
        raise RuntimeError(f"refusing RAW outside registered read roots: {path}")
    if path.suffix.lower() != ".arw" or not path.is_file():
        raise RuntimeError(f"expected an existing Sony ARW input: {path}")

    # raw_image_visible is a LibRaw-owned view.  Every array needed after the
    # context exits is copied while the context is alive (AGENTS.md rule 32).
    with rawpy.imread(str(path)) as raw:
        mosaic = np.array(raw.raw_image_visible, dtype=np.uint16, copy=True)
        pattern = np.array(raw.raw_pattern, dtype=np.int16, copy=True)
        black = np.array(raw.black_level_per_channel, dtype=np.float64, copy=True)
        color_desc_bytes = bytes(raw.color_desc)
        white = int(raw.white_level)
        pixel_aspect = float(raw.sizes.pixel_aspect)

    if pattern.shape != (2, 2):
        raise RuntimeError(f"{path.name}: expected a 2x2 Bayer CFA, got {pattern.shape}")
    if not math.isclose(pixel_aspect, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError(f"{path.name}: non-square decoded pixels ({pixel_aspect})")

    green_channels = [
        index for index, value in enumerate(color_desc_bytes) if value == ord("G")
    ]
    green_positions = np.argwhere(np.isin(pattern, green_channels))
    if len(green_positions) != 2:
        raise RuntimeError(f"{path.name}: expected two Bayer green positions")

    planes: list[np.ndarray] = []
    low_count = 0
    high_count = 0
    sample_count = 0
    used_black: list[float] = []
    for row, column in green_positions:
        channel = int(pattern[row, column])
        raw_plane = mosaic[row::2, column::2]
        planes.append(raw_plane.astype(np.float32) - np.float32(black[channel]))
        low_count += int(np.count_nonzero(raw_plane <= black[channel]))
        high_count += int(np.count_nonzero(raw_plane >= white - 1))
        sample_count += int(raw_plane.size)
        used_black.append(float(black[channel]))

    green = np.float32(0.5) * (planes[0] + planes[1])
    green = np.ascontiguousarray(green, dtype=np.float32)
    decoded_hash = sha256_bytes(memoryview(green).tobytes())
    usable = float(white - np.mean(used_black))
    return DecodedGreen(
        path=path,
        green_luma_dn=green,
        visible_shape_native_px=(int(mosaic.shape[0]), int(mosaic.shape[1])),
        decoded_green_sha256=decoded_hash,
        raw_pattern=pattern.tolist(),
        color_desc=color_desc_bytes.decode("ascii", errors="replace"),
        black_levels_dn=[float(value) for value in black],
        white_level_dn=white,
        usable_range_dn=usable,
        iso=float(registered_iso),
        low_rail_fraction=low_count / sample_count,
        high_rail_fraction=high_count / sample_count,
    )


def temporal_sigma_green_luma_dn(
    signal_dn: float | np.ndarray, iso: float, model: dict[str, Any]
) -> float | np.ndarray:
    signal = np.maximum(np.asarray(signal_dn, dtype=np.float64), 0.0)
    effective_iso = max(float(iso), float(model["base_iso"]))
    measured_gain = effective_iso / float(model["measured_green_gain_divisor"])
    shipped_gain = effective_iso / float(
        model["shipped_gain_divisor_for_measured_dark_floor"]
    )
    read_noise = (
        float(model["read_noise_e_high"])
        if iso >= float(model["second_base_iso"])
        else float(model["read_noise_e_low"])
    )
    photosite_variance = measured_gain * signal + (read_noise * shipped_gain) ** 2
    answer = np.sqrt(photosite_variance / 2.0)
    if np.ndim(answer) == 0:
        return float(answer)
    return answer


def band_window(size: int) -> np.ndarray:
    one = np.hanning(size).astype(np.float32)
    window = np.outer(one, one).astype(np.float32)
    mean_square = float(np.mean(window * window))
    if mean_square <= 0.0:
        raise ValueError("invalid band window")
    return window / np.float32(math.sqrt(mean_square))


def band_mask_rfft(
    size: int, sample_pitch_native_px: float, low: float, high: float
) -> tuple[np.ndarray, np.ndarray]:
    fy = fft.fftfreq(size, d=sample_pitch_native_px)
    fx = fft.rfftfreq(size, d=sample_pitch_native_px)
    radial = np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    mask = (radial >= low) & (radial <= high)
    weights = np.ones_like(radial, dtype=np.float32)
    if size % 2 == 0:
        weights[:, 1:-1] = 2.0
    else:
        weights[:, 1:] = 2.0
    return mask, weights


def band_rms_tiles(
    tiles: np.ndarray,
    sample_pitch_native_px: float,
    low: float,
    high: float,
) -> np.ndarray:
    if tiles.ndim != 3 or tiles.shape[1] != tiles.shape[2]:
        raise ValueError("tiles must have shape (N, size, size)")
    size = int(tiles.shape[1])
    centred = tiles.astype(np.float32, copy=False) - np.mean(
        tiles, axis=(1, 2), keepdims=True, dtype=np.float64
    ).astype(np.float32)
    tapered = centred * band_window(size)[None, :, :]
    spectrum = fft.rfft2(tapered, axes=(-2, -1), norm="ortho", workers=1)
    mask, weights = band_mask_rfft(size, sample_pitch_native_px, low, high)
    energy = np.abs(spectrum) ** 2
    selected = np.sum(
        energy[:, mask] * weights[mask][None, :], axis=1, dtype=np.float64
    )
    return np.sqrt(selected / float(size * size))


def image_blocks(image: np.ndarray, size: int) -> tuple[np.ndarray, int, int]:
    height = (image.shape[0] // size) * size
    width = (image.shape[1] // size) * size
    cropped = image[:height, :width]
    ny = height // size
    nx = width // size
    blocks = (
        cropped.reshape(ny, size, nx, size)
        .transpose(0, 2, 1, 3)
        .reshape(ny * nx, size, size)
    )
    return blocks, ny, nx


def bilinear_profile(
    image: np.ndarray,
    y_green: float,
    x_green: float,
    normal_y: float,
    normal_x: float,
    reach_native_px: int,
) -> tuple[np.ndarray, np.ndarray]:
    offsets_native = np.arange(
        -reach_native_px, reach_native_px + 1, 2, dtype=np.float64
    )
    offsets_green = offsets_native / 2.0
    ys = y_green + offsets_green * normal_y
    xs = x_green + offsets_green * normal_x
    if (
        np.min(ys) < 0.0
        or np.max(ys) > image.shape[0] - 1
        or np.min(xs) < 0.0
        or np.max(xs) > image.shape[1] - 1
    ):
        raise ValueError("profile footprint leaves the decoded input")
    values = ndimage.map_coordinates(
        image, [ys, xs], order=1, mode="nearest", prefilter=False
    )
    return offsets_native, values.astype(np.float64, copy=False)


def tree_summary(root: Path) -> dict[str, Any]:
    file_count = 0
    total_bytes = 0
    extension_counts: dict[str, int] = {}
    metadata_rows: list[tuple[str, int, int]] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    stat = entry.stat(follow_symlinks=False)
                    file_count += 1
                    total_bytes += stat.st_size
                    suffix = Path(entry.name).suffix.lower() or "<none>"
                    extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
                    relative = str(Path(entry.path).relative_to(root)).replace("\\", "/")
                    metadata_rows.append((relative, stat.st_size, stat.st_mtime_ns))
    metadata_digest = hashlib.sha256()
    for relative, size, modified in sorted(metadata_rows):
        metadata_digest.update(relative.encode("utf-8"))
        metadata_digest.update(b"\0")
        metadata_digest.update(str(size).encode("ascii"))
        metadata_digest.update(b"\0")
        metadata_digest.update(str(modified).encode("ascii"))
        metadata_digest.update(b"\n")
    return {
        "path": str(root),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "extension_counts": dict(sorted(extension_counts.items())),
        "path_size_mtime_sha256": metadata_digest.hexdigest(),
        "enumeration": "recursive os.scandir including hidden/system entries",
    }
