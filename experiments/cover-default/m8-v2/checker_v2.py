"""Independent M8 source-hull adjudicator.

The trace producer supplies source-plane f32 values, gathered f32 values and
effective transform metadata.  This module reconstructs geometry, Catmull-Rom
support, source intervals, tolerances, output intervals and witnesses without
importing producer or product code.
"""

from __future__ import annotations

import argparse
import ast
import gc
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

# These are set before NumPy is imported.  A caller may ask for fewer workers,
# but never more for this audit.
THREAD_ENV = (
    "CARGO_BUILD_JOBS",
    "RAYON_NUM_THREADS",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
)
for _name in THREAD_ENV:
    try:
        _requested = int(os.environ.get(_name, "8"))
    except ValueError:
        _requested = 8
    os.environ[_name] = str(max(1, min(8, _requested)))

import numpy as np
import tifffile


BLOCK_MAGIC = b"M8SITE01"
# "block-v1" names the fixed byte layout.  Historical fixtures use embedded
# producer protocol 2; protocol 1 used the same fields and is accepted.
BLOCK_PROTOCOLS = frozenset((1, 2))
BLOCK_HEADER = struct.Struct("<8s9I6d2fI")
WRAPPER_SCHEMAS = frozenset(
    (
        "m8-trace-metadata",
        "strehl-m8-trace",
        "strehl-m8-trace-metadata",
    )
)
WRAPPER_VERSION = 1
RESULT_SCHEMA = "strehl-m8-adjudication"
RESULT_VERSION = 2
INDEX_SCHEMA = "strehl-m8-evidence-index"
INDEX_VERSION = 2
KERNEL_NAMES = {0: "catmull-rom", 1: "bilinear"}
SITE_NAMES = ("R", "G1", "G2", "B")
SITE_COORDS = ((0, 0), (1, 0), (0, 1), (1, 1))
SITE_CHANNELS = (0, 1, 1, 2)
CHANNEL_NAMES = ("R", "G", "B")
CHUNK_ROWS = 32
U16_QUANT_TOLERANCE = 0.5 / 65535.0
SHA256_CHARS = frozenset("0123456789ABCDEF")
NO_FRAME_U16 = np.uint16(np.iinfo(np.uint16).max)

R_ROWS_DTYPE = np.dtype(
    [
        ("full_x", "<u4"),
        ("full_y", "<u4"),
        ("crop_local_x", "<i4"),
        ("crop_local_y", "<i4"),
        ("gathered", "<f4"),
        ("lo", "<f4"),
        ("hi", "<f4"),
        ("tau", "<f4"),
        ("direction", "i1"),
        ("signed_excess", "<f4"),
        ("excess_over_tolerance", "<f4"),
    ],
    align=False,
)

O_ROWS_DTYPE = np.dtype(
    [
        ("local_x", "<u4"),
        ("local_y", "<u4"),
        ("full_x", "<u4"),
        ("full_y", "<u4"),
        ("channel", "u1"),
        ("encoded", "<u2"),
        ("normalized", "<f8"),
        ("lo", "<f8"),
        ("hi", "<f8"),
        ("tau", "<f8"),
        ("tolerance", "<f8"),
        ("direction", "i1"),
        ("signed_excess", "<f8"),
        ("excess_over_tolerance", "<f8"),
        ("lo_frame_a", "<i4"),
        ("lo_site_a", "i1"),
        ("lo_frame_b", "<i4"),
        ("lo_site_b", "i1"),
        ("hi_frame_a", "<i4"),
        ("hi_site_a", "i1"),
        ("hi_frame_b", "<i4"),
        ("hi_site_b", "i1"),
        ("tau_frame", "<i4"),
        ("tau_site", "i1"),
    ],
    align=False,
)


class Refusal(RuntimeError):
    """The arm cannot be adjudicated without weakening a frozen control."""


@dataclass(frozen=True)
class CropRect:
    x: int
    y: int
    width: int
    height: int

    def validate_inside(self, full_width: int, full_height: int) -> None:
        if min(self.x, self.y) < 0 or min(self.width, self.height) <= 0:
            raise Refusal(f"invalid Crop rectangle {self}")
        if self.x + self.width > full_width or self.y + self.height > full_height:
            raise Refusal(
                f"Crop rectangle {self} does not fit {full_width}x{full_height}"
            )


@dataclass(frozen=True)
class SourceEntry:
    frame_index: int
    name: str
    path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class SourceInventory:
    path: Path
    sha256: str
    entries: tuple[SourceEntry, ...]


@dataclass(frozen=True)
class Block:
    path: Path
    payload_sha256: str
    protocol: int
    kernel: int
    src_width: int
    src_height: int
    dst_width: int
    dst_height: int
    site_x: int
    site_y: int
    channel: int
    a_re: float
    a_im: float
    b_re: float
    b_im: float
    cx: float
    cy: float
    value_range: np.float32
    site_gain: np.float32
    frame_path: str
    source_offset: int
    gathered_offset: int

    @property
    def site_index(self) -> int:
        return SITE_COORDS.index((self.site_x, self.site_y))

    @property
    def site(self) -> str:
        return SITE_NAMES[self.site_index]


@dataclass(frozen=True)
class TraceRecord:
    block: Block
    source: SourceEntry

    @property
    def frame_index(self) -> int:
        return self.source.frame_index


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for part in iter(lambda: stream.read(1 << 20), b""):
                digest.update(part)
    except OSError as error:
        raise Refusal(f"cannot hash {path}: {error}") from error
    return digest.hexdigest().upper()


def _normalise_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise Refusal(f"{label}: SHA-256 must be a string")
    digest = value.strip().upper()
    if len(digest) != 64 or any(char not in SHA256_CHARS for char in digest):
        raise Refusal(f"{label}: invalid SHA-256 {value!r}")
    return digest


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Refusal(f"cannot read JSON {path}: {error}") from error


def _json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_bytes(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_child(root: Path, relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise Refusal(f"{label}: path must be a non-empty string")
    candidate = (root / relative).resolve()
    if not _is_relative_to(candidate, root.resolve()):
        raise Refusal(f"{label}: path escapes its root: {relative!r}")
    return candidate


def _float32_bits(value: np.float32) -> bytes:
    return np.asarray(value, dtype="<f4").tobytes()


def _same_f32(left: np.float32, right: np.float32) -> bool:
    return _float32_bits(left) == _float32_bits(right)


def read_source_inventory(path: Path) -> SourceInventory:
    """Read and independently hash an explicit, already sorted inventory."""

    path = path.resolve()
    raw = _read_json(path)
    if isinstance(raw, list):
        rows = raw
        directory = path.parent
    elif isinstance(raw, dict):
        rows = raw.get("sources", raw.get("entries"))
        directory_raw = raw.get("directory")
        directory = (
            Path(directory_raw).resolve()
            if isinstance(directory_raw, str)
            else path.parent
        )
    else:
        raise Refusal(f"{path}: source inventory must be an array or object")
    if not isinstance(rows, list) or not rows:
        raise Refusal(f"{path}: source inventory has no ordered entries")

    entries: list[SourceEntry] = []
    for frame_index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise Refusal(f"{path}: source entry {frame_index} is not an object")
        raw_path = row.get("path")
        raw_name = row.get("name")
        if isinstance(raw_path, str):
            source_path = Path(raw_path)
            if not source_path.is_absolute():
                source_path = directory / source_path
        elif isinstance(raw_name, str):
            source_path = directory / raw_name
        else:
            raise Refusal(
                f"{path}: source entry {frame_index} needs path or name"
            )
        source_path = source_path.resolve()
        name = (
            raw_name
            if isinstance(raw_name, str)
            else source_path.name
        )
        if name != source_path.name or not name:
            raise Refusal(
                f"{path}: source entry {frame_index} name/path disagree"
            )
        expected_hash = _normalise_sha256(
            row.get("sha256"), f"{path}: source {name}"
        )
        try:
            stat = source_path.stat()
        except OSError as error:
            raise Refusal(f"{path}: cannot stat source {source_path}: {error}") from error
        if not source_path.is_file():
            raise Refusal(f"{path}: source is not a file: {source_path}")
        if "size" in row:
            try:
                expected_size = int(row["size"])
            except (TypeError, ValueError) as error:
                raise Refusal(f"{path}: invalid size for {name}") from error
            if expected_size != stat.st_size:
                raise Refusal(
                    f"{path}: {name} has {stat.st_size} bytes, inventory says "
                    f"{expected_size}"
                )
        actual_hash = sha256_file(source_path)
        if actual_hash != expected_hash:
            raise Refusal(
                f"{path}: source hash mismatch for {name}: "
                f"{actual_hash} != {expected_hash}"
            )
        entries.append(
            SourceEntry(frame_index, name, source_path, stat.st_size, actual_hash)
        )

    names = [entry.name for entry in entries]
    if len(entries) >= int(NO_FRAME_U16):
        raise Refusal(
            f"{path}: {len(entries)} sources exceed the uint16 witness range"
        )
    if names != sorted(names):
        raise Refusal(
            f"{path}: source entries are not in exact lexical frame order"
        )
    if len(names) != len(set(names)):
        raise Refusal(f"{path}: duplicate source names")
    return SourceInventory(path, sha256_file(path), tuple(entries))


def read_block(path: Path) -> Block:
    path = path.resolve()
    try:
        size = path.stat().st_size
        with path.open("rb") as stream:
            raw = stream.read(BLOCK_HEADER.size)
            if len(raw) != BLOCK_HEADER.size:
                raise Refusal(f"{path}: truncated block-v1 header")
            fields = BLOCK_HEADER.unpack(raw)
            (
                magic,
                protocol,
                kernel,
                src_width,
                src_height,
                dst_width,
                dst_height,
                site_x,
                site_y,
                channel,
                a_re,
                a_im,
                b_re,
                b_im,
                cx,
                cy,
                value_range,
                site_gain,
                frame_len,
            ) = fields
            if magic != BLOCK_MAGIC or protocol not in BLOCK_PROTOCOLS:
                raise Refusal(
                    f"{path}: unsupported block protocol {magic!r} v{protocol}"
                )
            if kernel not in KERNEL_NAMES:
                raise Refusal(f"{path}: unknown kernel id {kernel}")
            if min(src_width, src_height, dst_width, dst_height) <= 0:
                raise Refusal(f"{path}: zero image dimension")
            if src_width != 2 * dst_width or src_height != 2 * dst_height:
                raise Refusal(
                    f"{path}: full-resolution source {src_width}x{src_height} "
                    f"is not 2x destination {dst_width}x{dst_height}"
                )
            if (site_x, site_y) not in SITE_COORDS:
                raise Refusal(f"{path}: invalid CFA site {(site_x, site_y)}")
            site_index = SITE_COORDS.index((site_x, site_y))
            if channel != SITE_CHANNELS[site_index]:
                raise Refusal(
                    f"{path}: site {SITE_NAMES[site_index]} declares channel "
                    f"{channel}, expected {SITE_CHANNELS[site_index]}"
                )
            numeric = (a_re, a_im, b_re, b_im, cx, cy, value_range, site_gain)
            if not all(math.isfinite(float(value)) for value in numeric):
                raise Refusal(f"{path}: non-finite block metadata")
            if value_range <= 0.0 or site_gain <= 0.0:
                raise Refusal(f"{path}: range and site gain must be positive")
            if cx != 0.5 * dst_width or cy != 0.5 * dst_height:
                raise Refusal(
                    f"{path}: centre {(cx, cy)} != destination centre "
                    f"{(0.5 * dst_width, 0.5 * dst_height)}"
                )
            if frame_len <= 0 or frame_len > (1 << 20):
                raise Refusal(f"{path}: invalid frame-path length {frame_len}")
            frame_bytes = stream.read(frame_len)
            if len(frame_bytes) != frame_len:
                raise Refusal(f"{path}: truncated frame path")
            try:
                frame_path = frame_bytes.decode("utf-8")
            except UnicodeDecodeError as error:
                raise Refusal(f"{path}: frame path is not UTF-8") from error
    except OSError as error:
        raise Refusal(f"cannot read block {path}: {error}") from error

    source_offset = BLOCK_HEADER.size + frame_len
    gathered_offset = source_offset + 4 * src_width * src_height
    expected_size = gathered_offset + 4 * dst_width * dst_height
    if size != expected_size:
        raise Refusal(f"{path}: expected {expected_size} bytes, found {size}")
    return Block(
        path=path,
        payload_sha256=sha256_file(path),
        protocol=protocol,
        kernel=kernel,
        src_width=src_width,
        src_height=src_height,
        dst_width=dst_width,
        dst_height=dst_height,
        site_x=site_x,
        site_y=site_y,
        channel=channel,
        a_re=a_re,
        a_im=a_im,
        b_re=b_re,
        b_im=b_im,
        cx=cx,
        cy=cy,
        value_range=np.float32(value_range),
        site_gain=np.float32(site_gain),
        frame_path=frame_path,
        source_offset=source_offset,
        gathered_offset=gathered_offset,
    )


def _read_wrapper(path: Path, trace_root: Path) -> tuple[list[Path], dict[str, Any]]:
    raw = _read_json(path)
    if not isinstance(raw, dict) or raw.get("schema") not in WRAPPER_SCHEMAS:
        raise Refusal(f"{path}: unrecognised trace metadata wrapper")
    if raw.get("version") != WRAPPER_VERSION:
        raise Refusal(f"{path}: wrapper version must be {WRAPPER_VERSION}")
    layout = raw.get("payload_layout", "block-v1")
    if layout != "block-v1":
        raise Refusal(f"{path}: unsupported payload layout {layout!r}")
    rows = raw.get("blocks")
    if not isinstance(rows, list) or not rows:
        raise Refusal(f"{path}: wrapper contains no blocks")
    paths: list[Path] = []
    for index, row in enumerate(rows):
        if isinstance(row, str):
            relative = row
            expected_hash = None
        elif isinstance(row, dict):
            relative = row.get("path", row.get("payload"))
            expected_hash = row.get("sha256")
        else:
            raise Refusal(f"{path}: block wrapper row {index} is invalid")
        payload = _safe_child(trace_root, relative, f"{path}: block {index}")
        if payload.suffix.lower() != ".m8site" or not payload.is_file():
            raise Refusal(f"{path}: block payload is not an .m8site file: {payload}")
        if expected_hash is not None:
            expected = _normalise_sha256(
                expected_hash, f"{path}: block {index}"
            )
            actual = sha256_file(payload)
            if actual != expected:
                raise Refusal(
                    f"{path}: wrapped block hash mismatch: {actual} != {expected}"
                )
        paths.append(payload)
    if len(paths) != len(set(paths)):
        raise Refusal(f"{path}: duplicate block payload in wrapper")
    # Producer-computed support, hull, validity and tolerances are intentionally
    # neither parsed nor used.  The raw wrapper is retained only as provenance.
    return paths, {
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
        "schema": raw["schema"],
        "version": raw["version"],
        "payload_layout": layout,
    }


def discover_blocks(trace_dir: Path) -> tuple[list[Path], dict[str, Any] | None]:
    root = trace_dir.resolve()
    if not root.is_dir():
        raise Refusal(f"trace directory does not exist: {root}")
    wrapper_paths: list[Path] = []
    for candidate in (
        root / "trace-index.json",
        root / "trace-metadata.json",
        root / "metadata.json",
    ):
        if candidate.is_file():
            raw = _read_json(candidate)
            if isinstance(raw, dict) and raw.get("schema") in WRAPPER_SCHEMAS:
                wrapper_paths.append(candidate)
    wrapper_paths.extend(sorted(root.glob("*.m8meta.json")))
    wrapper_paths = list(dict.fromkeys(path.resolve() for path in wrapper_paths))
    if len(wrapper_paths) > 1:
        raise Refusal(f"{root}: multiple trace metadata wrappers")
    actual = sorted(path.resolve() for path in root.rglob("*.m8site"))
    if wrapper_paths:
        listed, provenance = _read_wrapper(wrapper_paths[0], root)
        if set(listed) != set(actual):
            missing = sorted(str(path) for path in set(actual) - set(listed))
            absent = sorted(str(path) for path in set(listed) - set(actual))
            raise Refusal(
                f"{wrapper_paths[0]}: wrapper/payload set mismatch; "
                f"unlisted={missing}, absent={absent}"
            )
        return listed, provenance
    if not actual:
        raise Refusal(f"{root}: no .m8site blocks")
    return actual, None


def coordinates(block: Block, y0: int, y1: int) -> tuple[np.ndarray, np.ndarray]:
    """Reconstruct full-resolution source coordinates from effective f64 bits."""

    if not (0 <= y0 <= y1 <= block.dst_height):
        raise Refusal(f"invalid destination row range {y0}:{y1}")
    ox = 0.5 * block.site_x
    oy = 0.5 * block.site_y
    x = np.arange(block.dst_width, dtype=np.float64)[None, :] + ox
    y = np.arange(y0, y1, dtype=np.float64)[:, None] + oy
    xr = x - block.cx
    yr = y - block.cy
    sx_plane = block.a_re * xr - block.a_im * yr + block.b_re + block.cx
    sy_plane = block.a_re * yr + block.a_im * xr + block.b_im + block.cy
    return 2.0 * sx_plane, 2.0 * sy_plane


def support_bounds(
    source: np.ndarray,
    block: Block,
    sx: np.ndarray,
    sy: np.ndarray,
    *,
    kernel: str = "catmull-rom",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return independently valid mask and exact discrete support interval."""

    if kernel == "catmull-rom":
        support = 2.0
        offsets = (-1, 0, 1, 2)
        low_index = 1
        high_x = block.src_width - 3
        high_y = block.src_height - 3
    elif kernel == "bilinear":
        support = 1.0
        offsets = (0, 1)
        low_index = 0
        high_x = block.src_width - 2
        high_y = block.src_height - 2
    else:
        raise Refusal(f"unsupported independent support kernel {kernel!r}")
    if source.shape != (block.src_height, block.src_width):
        raise Refusal(
            f"{block.path}: source shape {source.shape} does not match block"
        )
    valid = (
        (sx >= support - 0.5)
        & (sy >= support - 0.5)
        & (sx <= block.src_width - 0.5 - support)
        & (sy <= block.src_height - 0.5 - support)
    )
    # Production clamps before floor.  Valid coordinates are already inside the
    # legal interval; clipping the floor reproduces the endpoint behaviour and
    # also avoids invalid coordinates becoming unsafe indices.
    clamped_x = np.clip(sx, low_index, high_x)
    clamped_y = np.clip(sy, low_index, high_y)
    ix = np.floor(clamped_x).astype(np.intp)
    iy = np.floor(clamped_y).astype(np.intp)
    lo = np.full(sx.shape, np.float32(np.inf), dtype=np.float32)
    hi = np.full(sx.shape, np.float32(-np.inf), dtype=np.float32)
    for dy in offsets:
        for dx in offsets:
            values = np.asarray(source[iy + dy, ix + dx], dtype=np.float32)
            np.minimum(lo, values, out=lo)
            np.maximum(hi, values, out=hi)
    return valid, lo, hi


def tau_r(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Compute 8*ULP_f32(max(1, |lo|, |hi|)) entirely in binary32."""

    lo32 = np.asarray(lo, dtype=np.float32)
    hi32 = np.asarray(hi, dtype=np.float32)
    magnitude = np.maximum(
        np.float32(1.0), np.maximum(np.abs(lo32), np.abs(hi32))
    )
    magnitude = np.asarray(magnitude, dtype=np.float32)
    next_value = np.nextafter(
        magnitude, np.float32(np.inf), dtype=np.float32
    )
    ulp = np.subtract(next_value, magnitude, dtype=np.float32)
    return np.multiply(np.float32(8.0), ulp, dtype=np.float32)


def _f32_threshold_masks(
    gathered: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    tau: np.ndarray,
    valid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    lower_limit = np.subtract(lo, tau, dtype=np.float32)
    upper_limit = np.add(hi, tau, dtype=np.float32)
    return valid & (gathered < lower_limit), valid & (gathered > upper_limit)


def _output_threshold_masks(
    encoded: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    tau: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact serialized comparison, exposed for fixed commissioning predicates."""

    normalized = np.asarray(encoded, dtype=np.float64) / 65535.0
    tolerance = np.asarray(tau, dtype=np.float64) + U16_QUANT_TOLERANCE
    lower = normalized < np.asarray(lo, dtype=np.float64) - tolerance
    upper = normalized > np.asarray(hi, dtype=np.float64) + tolerance
    return lower, upper, normalized, tolerance


def refuse_unsafe_producer_state(
    *,
    expected_blocks: int,
    observed_blocks: int,
    duplicate_blocks: int,
    concurrent_writers: int,
    transparency_hashes: Sequence[str],
) -> None:
    """Strict gate for producer/runner state that value payloads cannot prove."""

    if observed_blocks != expected_blocks:
        raise Refusal(
            f"missing trace blocks: expected {expected_blocks}, "
            f"observed {observed_blocks}"
        )
    if duplicate_blocks != 0:
        raise Refusal(f"producer reported {duplicate_blocks} duplicate trace blocks")
    if concurrent_writers != 1:
        raise Refusal(
            f"trace state had {concurrent_writers} concurrent writers; exactly 1 required"
        )
    hashes = tuple(
        _normalise_sha256(value, "output-transparency hash")
        for value in transparency_hashes
    )
    if len(hashes) != 3 or len(set(hashes)) != 1:
        raise Refusal(
            "uninstrumented, tracing-off and tracing-on TIFF hashes must be identical"
        )


def _validate_trace_set(
    block_paths: Sequence[Path], inventory: SourceInventory
) -> tuple[list[TraceRecord], int, int, np.float32, np.ndarray]:
    blocks = [read_block(path) for path in block_paths]
    by_path = {entry.path: entry for entry in inventory.entries}
    expected_blocks = 4 * len(inventory.entries)
    if len(blocks) != expected_blocks:
        raise Refusal(
            f"trace set has {len(blocks)} blocks; complete inventory requires "
            f"{expected_blocks}"
        )
    records: list[TraceRecord] = []
    keys: set[tuple[int, int]] = set()
    first = blocks[0]
    for block in blocks:
        if block.kernel != 0:
            raise Refusal(
                f"{block.path}: M8 adjudication requires Catmull-Rom, got "
                f"{KERNEL_NAMES[block.kernel]}"
            )
        raw_frame_path = Path(block.frame_path)
        if not raw_frame_path.is_absolute():
            raise Refusal(
                f"{block.path}: emitted frame path is not absolute: "
                f"{block.frame_path!r}"
            )
        try:
            frame_path = raw_frame_path.resolve(strict=True)
        except OSError as error:
            raise Refusal(
                f"{block.path}: cannot resolve emitted frame path "
                f"{block.frame_path!r}: {error}"
            ) from error
        source = by_path.get(frame_path)
        if source is None:
            raise Refusal(
                f"{block.path}: emitted frame path {frame_path} is absent from "
                "the source inventory"
            )
        key = (source.frame_index, block.site_index)
        if key in keys:
            raise Refusal(
                f"duplicate trace for frame {source.frame_index} site {block.site}"
            )
        keys.add(key)
        if (block.dst_width, block.dst_height) != (
            first.dst_width,
            first.dst_height,
        ):
            raise Refusal(f"{block.path}: destination geometry disagrees")
        if (block.src_width, block.src_height) != (
            first.src_width,
            first.src_height,
        ):
            raise Refusal(f"{block.path}: source geometry disagrees")
        if not _same_f32(block.value_range, first.value_range):
            raise Refusal(f"{block.path}: sensor range differs from first block")
        records.append(TraceRecord(block, source))
    required = {
        (frame_index, site_index)
        for frame_index in range(len(inventory.entries))
        for site_index in range(4)
    }
    missing = sorted(required - keys)
    if missing:
        raise Refusal(f"trace set is missing frame/site records: {missing[:8]}")
    records.sort(key=lambda row: (row.frame_index, row.block.site_index))
    for frame_index in range(len(inventory.entries)):
        g1 = records[4 * frame_index + 1].block.site_gain
        g2 = records[4 * frame_index + 2].block.site_gain
        if not _same_f32(g1, g2):
            raise Refusal(f"frame {frame_index}: G1/G2 site gains differ")
    output_gains = np.asarray(
        [
            records[0].block.site_gain,
            records[1].block.site_gain,
            records[3].block.site_gain,
        ],
        dtype=np.float32,
    )
    return (
        records,
        first.dst_width,
        first.dst_height,
        first.value_range,
        output_gains,
    )


def _validate_tiff(
    path: Path, expected_width: int, expected_height: int
) -> tuple[np.ndarray, str]:
    path = path.resolve()
    try:
        with tifffile.TiffFile(path) as tif:
            if len(tif.series) != 1 or len(tif.pages) != 1:
                raise Refusal(f"{path}: expected one TIFF image/page")
            series = tif.series[0]
            expected = (expected_height, expected_width, 3)
            if series.shape != expected or series.dtype != np.dtype(np.uint16):
                raise Refusal(
                    f"{path}: expected RGB16 shape {expected}, got "
                    f"{series.dtype} {series.shape}"
                )
            page = tif.pages[0]
            if int(page.samplesperpixel) != 3 or int(page.photometric) != 2:
                raise Refusal(f"{path}: TIFF is not three-sample RGB")
            image = np.asarray(series.asarray())
    except Refusal:
        raise
    except (OSError, ValueError, tifffile.TiffFileError) as error:
        raise Refusal(f"cannot read TIFF {path}: {error}") from error
    return image, sha256_file(path)


def _delivery_coordinates(
    mode: str,
    crop: CropRect | None,
    y0: int,
    y1: int,
    width: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xx = np.broadcast_to(
        np.arange(width, dtype=np.int64)[None, :], (y1 - y0, width)
    )
    yy = np.broadcast_to(
        np.arange(y0, y1, dtype=np.int64)[:, None], (y1 - y0, width)
    )
    if mode == "scale":
        return (
            np.ones((y1 - y0, width), dtype=bool),
            xx.astype(np.int32),
            yy.astype(np.int32),
        )
    assert crop is not None
    delivered = (
        (xx >= crop.x)
        & (xx < crop.x + crop.width)
        & (yy >= crop.y)
        & (yy < crop.y + crop.height)
    )
    local_x = np.where(delivered, xx - crop.x, -1).astype(np.int32)
    local_y = np.where(delivered, yy - crop.y, -1).astype(np.int32)
    return delivered, local_x, local_y


def _r_violation_rows(
    y0: int,
    gathered: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    tau: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    local_x: np.ndarray,
    local_y: np.ndarray,
) -> np.ndarray:
    mask = lower | upper
    yy, xx = np.nonzero(mask)
    out = np.empty(xx.size, dtype=R_ROWS_DTYPE)
    selected = mask
    direction = np.where(upper[selected], 1, -1).astype(np.int8)
    values = gathered[selected]
    lows = lo[selected]
    highs = hi[selected]
    tolerances = tau[selected]
    signed = np.where(direction > 0, values - highs, values - lows).astype(
        np.float32
    )
    excess = np.where(direction > 0, signed - tolerances, -signed - tolerances)
    out["full_x"] = xx
    out["full_y"] = yy + y0
    out["crop_local_x"] = local_x[selected]
    out["crop_local_y"] = local_y[selected]
    out["gathered"] = values
    out["lo"] = lows
    out["hi"] = highs
    out["tau"] = tolerances
    out["direction"] = direction
    out["signed_excess"] = signed
    out["excess_over_tolerance"] = np.asarray(excess, dtype=np.float32)
    return out


def _artifact(
    root: Path,
    path: Path,
    *,
    kind: str,
    rows: int | None = None,
    array: np.ndarray | None = None,
) -> dict[str, Any]:
    stat = path.stat()
    result: dict[str, Any] = {
        "kind": kind,
        "path": path.relative_to(root).as_posix(),
        "bytes": stat.st_size,
        "sha256": sha256_file(path),
    }
    if rows is not None:
        result["rows"] = rows
    if array is not None:
        result["shape"] = list(array.shape)
        result["dtype"] = array.dtype.str
    return result


def _save_rows(path: Path, rows: Sequence[np.ndarray], dtype: np.dtype) -> np.ndarray:
    if rows:
        array = np.concatenate(rows)
    else:
        array = np.empty(0, dtype=dtype)
    np.save(path, array, allow_pickle=False)
    return array


def _close_memmap(array: np.ndarray | None) -> None:
    """Flush and close a NumPy mapping so Windows can rename its directory."""

    if array is None:
        return
    array.flush()
    mapping = getattr(array, "_mmap", None)
    if mapping is not None:
        mapping.close()


def _update_endpoint_maps(
    values_map: np.ndarray,
    witness_map: np.ndarray,
    site_index: int,
    frame_index: int,
    y0: int,
    valid: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    tau: np.ndarray,
    factor: np.float32,
) -> None:
    transformed_lo = np.multiply(lo, factor, dtype=np.float32)
    transformed_hi = np.multiply(hi, factor, dtype=np.float32)
    transformed_tau = np.multiply(tau, factor, dtype=np.float32)
    for component, candidate, better in (
        (0, transformed_lo, np.less),
        (1, transformed_hi, np.greater),
        (2, transformed_tau, np.greater),
    ):
        current = values_map[
            site_index, y0 : y0 + valid.shape[0], :, component
        ]
        current_witness = witness_map[
            site_index, y0 : y0 + valid.shape[0], :, component
        ]
        replace = valid & better(candidate, current)
        # Exact ties retain the lowest sorted frame index.  Records are sorted,
        # but the explicit comparison makes this invariant recoverable even if
        # this helper is called independently.
        replace |= (
            valid
            & (candidate == current)
            & (np.uint16(frame_index) < current_witness)
        )
        current[replace] = candidate[replace]
        current_witness[replace] = np.uint16(frame_index)


def _site_output_interval(
    values: np.ndarray,
    witnesses: np.ndarray,
    channel: int,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    tuple[np.ndarray, int, np.ndarray, int],
    tuple[np.ndarray, int, np.ndarray, int],
    tuple[np.ndarray, np.ndarray],
]:
    if channel == 0:
        site = 0
        return (
            values[site, ..., 0].astype(np.float64),
            values[site, ..., 1].astype(np.float64),
            values[site, ..., 2].astype(np.float64),
            (witnesses[site, ..., 0], site, None, -1),
            (witnesses[site, ..., 1], site, None, -1),
            (witnesses[site, ..., 2], np.full(values.shape[1:3], site)),
        )
    if channel == 2:
        site = 3
        return (
            values[site, ..., 0].astype(np.float64),
            values[site, ..., 1].astype(np.float64),
            values[site, ..., 2].astype(np.float64),
            (witnesses[site, ..., 0], site, None, -1),
            (witnesses[site, ..., 1], site, None, -1),
            (witnesses[site, ..., 2], np.full(values.shape[1:3], site)),
        )

    lo = 0.5 * (
        values[1, ..., 0].astype(np.float64)
        + values[2, ..., 0].astype(np.float64)
    )
    hi = 0.5 * (
        values[1, ..., 1].astype(np.float64)
        + values[2, ..., 1].astype(np.float64)
    )
    tau1 = values[1, ..., 2]
    tau2 = values[2, ..., 2]
    frame1 = witnesses[1, ..., 2]
    frame2 = witnesses[2, ..., 2]
    choose1 = (tau1 > tau2) | (
        (tau1 == tau2)
        & ((frame1 < frame2) | ((frame1 == frame2) & (1 < 2)))
    )
    tau = np.maximum(tau1, tau2).astype(np.float64)
    tau_frame = np.where(choose1, frame1, frame2)
    tau_site = np.where(choose1, 1, 2)
    return (
        lo,
        hi,
        tau,
        (witnesses[1, ..., 0], 1, witnesses[2, ..., 0], 2),
        (witnesses[1, ..., 1], 1, witnesses[2, ..., 1], 2),
        (tau_frame, tau_site),
    )


def _o_violation_rows(
    channel: int,
    local_y0: int,
    full_x0: int,
    full_y0: int,
    encoded: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    tau: np.ndarray,
    lo_witness: tuple[np.ndarray, int, np.ndarray | None, int],
    hi_witness: tuple[np.ndarray, int, np.ndarray | None, int],
    tau_witness: tuple[np.ndarray, np.ndarray],
) -> np.ndarray:
    lower, upper, normalized, tolerance = _output_threshold_masks(
        encoded, lo, hi, tau
    )
    mask = lower | upper
    yy, xx = np.nonzero(mask)
    out = np.empty(xx.size, dtype=O_ROWS_DTYPE)
    direction = np.where(upper[mask], 1, -1).astype(np.int8)
    signed = np.where(
        direction > 0,
        normalized[mask] - hi[mask],
        normalized[mask] - lo[mask],
    )
    excess = np.where(
        direction > 0,
        signed - tolerance[mask],
        -signed - tolerance[mask],
    )
    out["local_x"] = xx
    out["local_y"] = yy + local_y0
    out["full_x"] = xx + full_x0
    out["full_y"] = yy + local_y0 + full_y0
    out["channel"] = channel
    out["encoded"] = encoded[mask]
    out["normalized"] = normalized[mask]
    out["lo"] = lo[mask]
    out["hi"] = hi[mask]
    out["tau"] = tau[mask]
    out["tolerance"] = tolerance[mask]
    out["direction"] = direction
    out["signed_excess"] = signed
    out["excess_over_tolerance"] = excess
    lo_a, lo_site_a, lo_b, lo_site_b = lo_witness
    hi_a, hi_site_a, hi_b, hi_site_b = hi_witness
    out["lo_frame_a"] = lo_a[mask].astype(np.int64)
    out["lo_site_a"] = lo_site_a
    out["lo_frame_b"] = -1 if lo_b is None else lo_b[mask].astype(np.int64)
    out["lo_site_b"] = lo_site_b
    out["hi_frame_a"] = hi_a[mask].astype(np.int64)
    out["hi_site_a"] = hi_site_a
    out["hi_frame_b"] = -1 if hi_b is None else hi_b[mask].astype(np.int64)
    out["hi_site_b"] = hi_site_b
    out["tau_frame"] = tau_witness[0][mask].astype(np.int64)
    out["tau_site"] = tau_witness[1][mask].astype(np.int8)
    return out


def adjudicate_arm(
    *,
    capture: str,
    trace_dir: Path,
    tiff_path: Path,
    source_inventory_path: Path,
    sidecar_sha256: str,
    mode: str,
    crop: CropRect | None,
    output_dir: Path,
) -> dict[str, Any]:
    """Adjudicate one complete arm and publish it by one directory rename."""

    if not capture or not capture.strip():
        raise Refusal("capture must be a non-empty identifier")
    capture = capture.strip()
    sidecar_hash = _normalise_sha256(sidecar_sha256, "sidecar")
    mode = mode.strip().lower()
    if mode not in ("scale", "crop"):
        raise Refusal(f"mode must be scale or crop, got {mode!r}")
    if mode == "crop" and crop is None:
        raise Refusal("Crop mode requires explicit x,y,w,h")
    if mode == "scale" and crop is not None:
        raise Refusal("Scale mode refuses a Crop rectangle")

    inventory = read_source_inventory(source_inventory_path)
    block_paths, wrapper = discover_blocks(trace_dir)
    records, full_width, full_height, value_range, output_gains = (
        _validate_trace_set(block_paths, inventory)
    )
    if mode == "crop":
        assert crop is not None
        crop.validate_inside(full_width, full_height)
        output_width, output_height = crop.width, crop.height
    else:
        output_width, output_height = full_width, full_height
    image, tiff_hash = _validate_tiff(tiff_path, output_width, output_height)

    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise Refusal(f"output directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = output_dir.with_name(output_dir.name + f".staging-{os.getpid()}")
    if staging.exists():
        raise Refusal(f"staging directory already exists: {staging}")

    artifacts: list[dict[str, Any]] = []
    r_files: list[dict[str, Any]] = []
    r_full_denominator = 0
    r_delivered_denominator = 0
    r_full_lower = 0
    r_full_upper = 0
    r_delivered_lower = 0
    r_delivered_upper = 0
    r_max_excess = 0.0
    values_map: np.ndarray | None = None
    witness_map: np.ndarray | None = None
    try:
        evidence_dir = staging / "m8-r"
        evidence_dir.mkdir(parents=True)
        values_path = staging / "endpoint-values.npy"
        witness_path = staging / "endpoint-witness-frames.npy"
        values_map = np.lib.format.open_memmap(
            values_path,
            mode="w+",
            dtype="<f4",
            shape=(4, full_height, full_width, 3),
        )
        values_map[..., 0] = np.float32(np.inf)
        values_map[..., 1] = np.float32(-np.inf)
        values_map[..., 2] = np.float32(0.0)
        witness_map = np.lib.format.open_memmap(
            witness_path,
            mode="w+",
            dtype="<u2",
            shape=(4, full_height, full_width, 3),
        )
        witness_map[:] = NO_FRAME_U16

        for record in records:
            block = record.block
            source = np.memmap(
                block.path,
                mode="r",
                dtype="<f4",
                offset=block.source_offset,
                shape=(block.src_height, block.src_width),
            )
            gathered_all = np.memmap(
                block.path,
                mode="r",
                dtype="<f4",
                offset=block.gathered_offset,
                shape=(block.dst_height, block.dst_width),
            )
            if not np.all(np.isfinite(source)):
                first_bad = np.argwhere(~np.isfinite(source))[0]
                raise Refusal(
                    f"{block.path}: source plane has non-finite value at "
                    f"({int(first_bad[1])},{int(first_bad[0])})"
                )
            rows: list[np.ndarray] = []
            full_denominator = delivered_denominator = 0
            lower_count = upper_count = 0
            delivered_lower = delivered_upper = 0
            max_excess = 0.0
            factor = np.float32(
                np.float32(output_gains[block.channel] / block.site_gain)
                / value_range
            )
            if not np.isfinite(factor) or factor <= 0:
                raise Refusal(f"{block.path}: invalid transformed interval factor")
            for y0 in range(0, full_height, CHUNK_ROWS):
                y1 = min(full_height, y0 + CHUNK_ROWS)
                sx, sy = coordinates(block, y0, y1)
                valid, lo, hi = support_bounds(
                    source, block, sx, sy, kernel="catmull-rom"
                )
                gathered = np.asarray(gathered_all[y0:y1], dtype=np.float32)
                finite = np.isfinite(gathered)
                mismatch = finite ^ valid
                if np.any(mismatch):
                    yy, xx = np.argwhere(mismatch)[0]
                    raise Refusal(
                        f"{block.path}: gathered finite/NaN pattern disagrees "
                        f"with independent validity at ({int(xx)},{int(yy + y0)})"
                    )
                tau = tau_r(lo, hi)
                lower, upper = _f32_threshold_masks(
                    gathered, lo, hi, tau, valid
                )
                delivered, local_x, local_y = _delivery_coordinates(
                    mode, crop, y0, y1, full_width
                )
                full_denominator += int(np.count_nonzero(valid))
                delivered_denominator += int(np.count_nonzero(valid & delivered))
                lower_count += int(np.count_nonzero(lower))
                upper_count += int(np.count_nonzero(upper))
                delivered_lower += int(np.count_nonzero(lower & delivered))
                delivered_upper += int(np.count_nonzero(upper & delivered))
                if np.any(lower | upper):
                    part = _r_violation_rows(
                        y0,
                        gathered,
                        lo,
                        hi,
                        tau,
                        lower,
                        upper,
                        local_x,
                        local_y,
                    )
                    rows.append(part)
                    max_excess = max(
                        max_excess,
                        float(
                            np.max(
                                part["excess_over_tolerance"],
                                initial=np.float32(0.0),
                            )
                        ),
                    )
                _update_endpoint_maps(
                    values_map,
                    witness_map,
                    block.site_index,
                    record.frame_index,
                    y0,
                    valid,
                    lo,
                    hi,
                    tau,
                    factor,
                )

            row_path = evidence_dir / (
                f"frame-{record.frame_index:05d}-{block.site}.npy"
            )
            saved = _save_rows(row_path, rows, R_ROWS_DTYPE)
            artifact = _artifact(
                staging,
                row_path,
                kind="m8-r-violations",
                rows=len(saved),
                array=saved,
            )
            artifacts.append(artifact)
            entry = {
                **artifact,
                "capture": capture,
                "mode": mode,
                "sidecar_sha256": sidecar_hash,
                "frame_index": record.frame_index,
                "frame_name": record.source.name,
                "frame_path": str(record.source.path),
                "source_sha256": record.source.sha256,
                "trace_payload": str(block.path),
                "trace_payload_sha256": block.payload_sha256,
                "site": block.site,
                "site_index": block.site_index,
                "channel": CHANNEL_NAMES[block.channel],
                "full_denominator": full_denominator,
                "delivered_denominator": delivered_denominator,
                "lower_violations": lower_count,
                "upper_violations": upper_count,
                "delivered_lower_violations": delivered_lower,
                "delivered_upper_violations": delivered_upper,
                "max_excess_over_tolerance": max_excess,
            }
            r_files.append(entry)
            r_full_denominator += full_denominator
            r_delivered_denominator += delivered_denominator
            r_full_lower += lower_count
            r_full_upper += upper_count
            r_delivered_lower += delivered_lower
            r_delivered_upper += delivered_upper
            r_max_excess = max(r_max_excess, max_excess)
            del source, gathered_all, saved

        values_map.flush()
        witness_map.flush()
        # Every delivered output sample needs both green-site intervals and its
        # channel interval.  Refuse rather than silently shrinking M8-O.
        x0 = crop.x if crop is not None else 0
        y0 = crop.y if crop is not None else 0
        delivered_values = values_map[
            :, y0 : y0 + output_height, x0 : x0 + output_width, :
        ]
        delivered_witnesses = witness_map[
            :, y0 : y0 + output_height, x0 : x0 + output_width, :
        ]
        bracketed = (
            np.isfinite(delivered_values[..., 0])
            & np.isfinite(delivered_values[..., 1])
            & (delivered_witnesses[..., 0] != NO_FRAME_U16)
            & (delivered_witnesses[..., 1] != NO_FRAME_U16)
            & (delivered_witnesses[..., 2] != NO_FRAME_U16)
        )
        if not np.all(bracketed):
            site, yy, xx = np.argwhere(~bracketed)[0]
            raise Refusal(
                f"M8-O has no complete source interval at delivered "
                f"({int(xx)},{int(yy)}) site {SITE_NAMES[int(site)]}"
            )

        o_parts: list[np.ndarray] = []
        o_lower = o_upper = 0
        o_max_excess = 0.0
        for channel in range(3):
            for local_y0 in range(0, output_height, CHUNK_ROWS):
                local_y1 = min(output_height, local_y0 + CHUNK_ROWS)
                value_chunk = delivered_values[
                    :, local_y0:local_y1, :, :
                ]
                witness_chunk = delivered_witnesses[
                    :, local_y0:local_y1, :, :
                ]
                (
                    lo,
                    hi,
                    tau,
                    lo_witness,
                    hi_witness,
                    tau_witness,
                ) = _site_output_interval(value_chunk, witness_chunk, channel)
                encoded = image[local_y0:local_y1, :, channel]
                part = _o_violation_rows(
                    channel,
                    local_y0,
                    x0,
                    y0,
                    encoded,
                    lo,
                    hi,
                    tau,
                    lo_witness,
                    hi_witness,
                    tau_witness,
                )
                if len(part):
                    o_parts.append(part)
                    o_lower += int(np.count_nonzero(part["direction"] < 0))
                    o_upper += int(np.count_nonzero(part["direction"] > 0))
                    o_max_excess = max(
                        o_max_excess,
                        float(
                            np.max(
                                part["excess_over_tolerance"], initial=0.0
                            )
                        ),
                    )
        o_path = staging / "m8-o-violations.npy"
        o_rows = _save_rows(o_path, o_parts, O_ROWS_DTYPE)
        o_artifact = _artifact(
            staging,
            o_path,
            kind="m8-o-violations",
            rows=len(o_rows),
            array=o_rows,
        )
        artifacts.append(o_artifact)
        del o_rows

        values_map.flush()
        witness_map.flush()
        value_artifact = _artifact(
            staging,
            values_path,
            kind="endpoint-values",
            array=values_map,
        )
        witness_artifact = _artifact(
            staging,
            witness_path,
            kind="endpoint-witness-frames",
            array=witness_map,
        )
        artifacts.extend((value_artifact, witness_artifact))

        r_violations = r_full_lower + r_full_upper
        r_delivered_violations = r_delivered_lower + r_delivered_upper
        o_violations = o_lower + o_upper
        r_summary = {
            "primary_full": {
                "denominator": r_full_denominator,
                "violations": r_violations,
                "lower_violations": r_full_lower,
                "upper_violations": r_full_upper,
                "fraction": r_violations / r_full_denominator,
                "max_excess_over_tolerance": r_max_excess,
            },
            "delivered_subset": {
                "denominator": r_delivered_denominator,
                "violations": r_delivered_violations,
                "lower_violations": r_delivered_lower,
                "upper_violations": r_delivered_upper,
                "fraction": r_delivered_violations / r_delivered_denominator,
            },
        }
        if mode == "scale" and r_summary["primary_full"] != {
            **r_summary["delivered_subset"],
            "max_excess_over_tolerance": r_max_excess,
        }:
            # Compare the actual census fields without relying on dictionary
            # layout or fraction formatting.
            if (
                r_full_denominator != r_delivered_denominator
                or r_full_lower != r_delivered_lower
                or r_full_upper != r_delivered_upper
            ):
                raise Refusal("Scale full and delivered M8-R domains diverged")
        o_denominator = output_width * output_height * 3
        o_summary = {
            "denominator": o_denominator,
            "violations": o_violations,
            "lower_violations": o_lower,
            "upper_violations": o_upper,
            "fraction": o_violations / o_denominator,
            "max_excess_over_tolerance": o_max_excess,
            "quantization_tolerance": U16_QUANT_TOLERANCE,
            "clamping_caveat": (
                "Final clamping can erase M8-O evidence; M8-O cannot acquit M8-R."
            ),
        }
        crop_payload = (
            {
                "x": crop.x,
                "y": crop.y,
                "width": crop.width,
                "height": crop.height,
            }
            if crop is not None
            else None
        )
        index_payload = {
            "schema": INDEX_SCHEMA,
            "version": INDEX_VERSION,
            "capture": capture,
            "mode": mode,
            "sidecar_sha256": sidecar_hash,
            "full_geometry": {"width": full_width, "height": full_height},
            "crop": crop_payload,
            "source_inventory": {
                "path": str(inventory.path),
                "sha256": inventory.sha256,
                "entries": [
                    {
                        "frame_index": entry.frame_index,
                        "name": entry.name,
                        "path": str(entry.path),
                        "bytes": entry.size,
                        "sha256": entry.sha256,
                    }
                    for entry in inventory.entries
                ],
            },
            "trace_wrapper": wrapper,
            "m8_r": {"summary": r_summary, "files": r_files},
            "m8_o": {
                "summary": o_summary,
                "violations_file": o_artifact,
                "endpoint_values": value_artifact,
                "endpoint_witness_frames": witness_artifact,
                "site_axis": list(SITE_NAMES),
                "component_axis": ["lo", "hi", "tau"],
                "green_rule": (
                    "lo=.5*(min G1 lo+min G2 lo); "
                    "hi=.5*(max G1 hi+max G2 hi); tau=max(G1,G2)"
                ),
            },
            "artifacts": artifacts,
        }
        index_bytes = _json_bytes(index_payload)
        index_hash = _sha256_bytes(index_bytes)
        index_name = f"evidence-index-{index_hash.lower()}.json"
        _write_bytes(staging / index_name, index_bytes)
        result_payload = {
            "schema": RESULT_SCHEMA,
            "version": RESULT_VERSION,
            "capture": capture,
            "mode": mode,
            "sidecar_sha256": sidecar_hash,
            "tiff": {
                "path": str(Path(tiff_path).resolve()),
                "bytes": Path(tiff_path).resolve().stat().st_size,
                "sha256": tiff_hash,
                "width": output_width,
                "height": output_height,
                "dtype": "uint16",
                "channels": list(CHANNEL_NAMES),
            },
            "source_inventory": {
                "path": str(inventory.path),
                "sha256": inventory.sha256,
            },
            "crop": crop_payload,
            "m8_r": r_summary,
            "m8_o": o_summary,
            "evidence_index": {
                "path": index_name,
                "bytes": len(index_bytes),
                "sha256": index_hash,
            },
        }
        _write_bytes(staging / "result.json", _json_bytes(result_payload))
        # Close mappings before Windows renames the directory.  CPython keeps
        # the last loop's slice locals alive until function return, so merely
        # deleting the two owning names is insufficient on Windows.
        del delivered_values, delivered_witnesses
        _close_memmap(values_map)
        _close_memmap(witness_map)
        del values_map, witness_map
        values_map = witness_map = None
        gc.collect()
        os.replace(staging, output_dir)
        return result_payload
    except Exception:
        try:
            _close_memmap(values_map)
        except Exception:
            pass
        try:
            _close_memmap(witness_map)
        except Exception:
            pass
        del values_map, witness_map
        gc.collect()
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _verify_artifact(root: Path, row: dict[str, Any]) -> None:
    path = _safe_child(root, row.get("path"), "artifact")
    if not path.is_file():
        raise Refusal(f"missing artifact {path}")
    actual_bytes = path.stat().st_size
    if actual_bytes != row.get("bytes"):
        raise Refusal(
            f"{path}: byte count {actual_bytes} != index {row.get('bytes')}"
        )
    actual_hash = sha256_file(path)
    expected_hash = _normalise_sha256(row.get("sha256"), f"{path}")
    if actual_hash != expected_hash:
        raise Refusal(f"{path}: SHA-256 {actual_hash} != {expected_hash}")
    if path.suffix == ".npy":
        try:
            array = np.load(path, mmap_mode="r", allow_pickle=False)
        except (OSError, ValueError) as error:
            raise Refusal(f"{path}: invalid NumPy artifact: {error}") from error
        if "rows" in row and (array.ndim != 1 or len(array) != row["rows"]):
            raise Refusal(
                f"{path}: row count/shape {array.shape} != {row['rows']}"
            )
        if "shape" in row and list(array.shape) != row["shape"]:
            raise Refusal(
                f"{path}: array shape {list(array.shape)} != {row['shape']}"
            )
        if "dtype" in row and array.dtype.str != row["dtype"]:
            raise Refusal(
                f"{path}: array dtype {array.dtype.str} != {row['dtype']}"
            )
        kind = row.get("kind")
        expected_dtype = {
            "m8-r-violations": R_ROWS_DTYPE,
            "m8-o-violations": O_ROWS_DTYPE,
            "endpoint-values": np.dtype("<f4"),
            "endpoint-witness-frames": np.dtype("<u2"),
        }.get(kind)
        if expected_dtype is None:
            raise Refusal(f"{path}: unknown artifact kind {kind!r}")
        if array.dtype != expected_dtype:
            raise Refusal(
                f"{path}: {kind} dtype {array.dtype!r} != {expected_dtype!r}"
            )
        del array


def _same_artifact(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = ("kind", "path", "bytes", "sha256", "rows", "shape", "dtype")
    return all(left.get(key) == right.get(key) for key in keys)


def _verify_fraction(summary: dict[str, Any], label: str) -> None:
    try:
        denominator = int(summary["denominator"])
        violations = int(summary["violations"])
        lower = int(summary["lower_violations"])
        upper = int(summary["upper_violations"])
        fraction = float(summary["fraction"])
    except (KeyError, TypeError, ValueError) as error:
        raise Refusal(f"{label}: malformed census summary") from error
    if denominator <= 0 or min(violations, lower, upper) < 0:
        raise Refusal(f"{label}: invalid census counts")
    if violations != lower + upper:
        raise Refusal(f"{label}: violation count does not equal lower+upper")
    if fraction != violations / denominator:
        raise Refusal(f"{label}: fraction does not reproduce integer counts")


def verify_result(result_path: Path) -> dict[str, Any]:
    """Verify the content-addressed index and every indexed artifact."""

    result_path = result_path.resolve()
    result = _read_json(result_path)
    if (
        not isinstance(result, dict)
        or result.get("schema") != RESULT_SCHEMA
        or result.get("version") != RESULT_VERSION
    ):
        raise Refusal(f"{result_path}: unsupported adjudication result")
    index_record = result.get("evidence_index")
    if not isinstance(index_record, dict):
        raise Refusal(f"{result_path}: missing evidence index record")
    root = result_path.parent
    index_path = _safe_child(root, index_record.get("path"), "evidence index")
    if not index_path.is_file():
        raise Refusal(f"missing evidence index {index_path}")
    index_bytes = index_path.read_bytes()
    index_hash = _sha256_bytes(index_bytes)
    expected_hash = _normalise_sha256(
        index_record.get("sha256"), "evidence index"
    )
    if index_hash != expected_hash:
        raise Refusal(
            f"{index_path}: SHA-256 {index_hash} != result {expected_hash}"
        )
    if index_path.name != f"evidence-index-{index_hash.lower()}.json":
        raise Refusal(f"{index_path}: filename is not its content address")
    if len(index_bytes) != index_record.get("bytes"):
        raise Refusal(f"{index_path}: indexed byte count is wrong")
    try:
        index = json.loads(index_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise Refusal(f"{index_path}: invalid index JSON: {error}") from error
    if (
        not isinstance(index, dict)
        or index.get("schema") != INDEX_SCHEMA
        or index.get("version") != INDEX_VERSION
    ):
        raise Refusal(f"{index_path}: unsupported evidence index")
    for key in ("capture", "mode", "sidecar_sha256"):
        if index.get(key) != result.get(key):
            raise Refusal(f"{index_path}: {key} disagrees with result")
    if index.get("m8_r", {}).get("summary") != result.get("m8_r"):
        raise Refusal(f"{index_path}: M8-R summary disagrees with result")
    if index.get("m8_o", {}).get("summary") != result.get("m8_o"):
        raise Refusal(f"{index_path}: M8-O summary disagrees with result")
    artifacts = index.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise Refusal(f"{index_path}: no artifacts")
    paths = [row.get("path") for row in artifacts if isinstance(row, dict)]
    if len(paths) != len(artifacts) or len(paths) != len(set(paths)):
        raise Refusal(f"{index_path}: invalid or duplicate artifact paths")
    for row in artifacts:
        _verify_artifact(root, row)
    artifact_by_path = {row["path"]: row for row in artifacts}

    source_rows = index.get("source_inventory", {}).get("entries")
    if not isinstance(source_rows, list) or not source_rows:
        raise Refusal(f"{index_path}: no ordered source identities")
    for frame_index, source in enumerate(source_rows):
        if not isinstance(source, dict) or source.get("frame_index") != frame_index:
            raise Refusal(f"{index_path}: source frame indices are not contiguous")
        if not isinstance(source.get("name"), str) or not source["name"]:
            raise Refusal(f"{index_path}: source {frame_index} has no name")
        if Path(source.get("path", "")).name != source["name"]:
            raise Refusal(f"{index_path}: source {frame_index} name/path disagree")
        _normalise_sha256(source.get("sha256"), f"source {frame_index}")
        if not isinstance(source.get("bytes"), int) or source["bytes"] < 0:
            raise Refusal(f"{index_path}: source {frame_index} byte count is invalid")
    source_names = [source["name"] for source in source_rows]
    if source_names != sorted(source_names) or len(source_names) != len(
        set(source_names)
    ):
        raise Refusal(f"{index_path}: source identities are not unique/sorted")
    retained_inventory_record = result.get("source_inventory")
    indexed_inventory_record = index.get("source_inventory")
    if not isinstance(retained_inventory_record, dict) or not isinstance(
        indexed_inventory_record, dict
    ):
        raise Refusal(f"{index_path}: missing retained source inventory identity")
    retained_inventory = read_source_inventory(
        Path(retained_inventory_record.get("path", ""))
    )
    if (
        indexed_inventory_record.get("path") != str(retained_inventory.path)
        or indexed_inventory_record.get("sha256") != retained_inventory.sha256
        or retained_inventory_record.get("sha256") != retained_inventory.sha256
    ):
        raise Refusal(f"{index_path}: retained source inventory identity disagrees")
    retained_source_rows = [
        {
            "frame_index": entry.frame_index,
            "name": entry.name,
            "path": str(entry.path),
            "bytes": entry.size,
            "sha256": entry.sha256,
        }
        for entry in retained_inventory.entries
    ]
    if source_rows != retained_source_rows:
        raise Refusal(
            f"{index_path}: indexed sources do not reproduce retained inventory"
        )

    r_files = index.get("m8_r", {}).get("files")
    if not isinstance(r_files, list) or len(r_files) != len(source_rows) * 4:
        raise Refusal(f"{index_path}: incomplete M8-R file index")
    expected_keys = {
        (frame_index, site_index)
        for frame_index in range(len(source_rows))
        for site_index in range(4)
    }
    observed_keys: set[tuple[int, int]] = set()
    for row in r_files:
        if not isinstance(row, dict):
            raise Refusal(f"{index_path}: malformed M8-R file record")
        key = (row.get("frame_index"), row.get("site_index"))
        if key in observed_keys:
            raise Refusal(f"{index_path}: duplicate M8-R frame/site {key}")
        observed_keys.add(key)
        if key not in expected_keys:
            raise Refusal(f"{index_path}: invalid M8-R frame/site {key}")
        frame_index, site_index = key
        source = source_rows[frame_index]
        expected_context = {
            "capture": result["capture"],
            "mode": result["mode"],
            "sidecar_sha256": result["sidecar_sha256"],
            "frame_name": source["name"],
            "frame_path": source["path"],
            "source_sha256": source["sha256"],
            "site": SITE_NAMES[site_index],
            "channel": CHANNEL_NAMES[SITE_CHANNELS[site_index]],
        }
        if any(row.get(key) != value for key, value in expected_context.items()):
            raise Refusal(
                f"{index_path}: M8-R context mismatch at frame/site "
                f"{(frame_index, site_index)}"
            )
        artifact = artifact_by_path.get(row.get("path"))
        if artifact is None or not _same_artifact(row, artifact):
            raise Refusal(
                f"{index_path}: M8-R artifact mismatch at frame/site "
                f"{(frame_index, site_index)}"
            )
        if row.get("kind") != "m8-r-violations":
            raise Refusal(f"{index_path}: M8-R record has wrong artifact kind")
        if row.get("rows") != row.get("lower_violations", -1) + row.get(
            "upper_violations", -1
        ):
            raise Refusal(f"{index_path}: M8-R row/violation count mismatch")
        if row.get("delivered_lower_violations", -1) < 0 or row.get(
            "delivered_upper_violations", -1
        ) < 0:
            raise Refusal(f"{index_path}: negative delivered M8-R count")
        if row.get("delivered_denominator", -1) > row.get(
            "full_denominator", -1
        ):
            raise Refusal(f"{index_path}: delivered M8-R denominator exceeds full")
    if observed_keys != expected_keys:
        raise Refusal(f"{index_path}: incomplete M8-R frame/site Cartesian set")

    r_summary = index["m8_r"]["summary"]
    primary = r_summary.get("primary_full")
    delivered = r_summary.get("delivered_subset")
    if not isinstance(primary, dict) or not isinstance(delivered, dict):
        raise Refusal(f"{index_path}: malformed M8-R summaries")
    _verify_fraction(primary, "M8-R primary")
    _verify_fraction(delivered, "M8-R delivered")
    expected_primary = {
        "denominator": sum(row["full_denominator"] for row in r_files),
        "lower_violations": sum(row["lower_violations"] for row in r_files),
        "upper_violations": sum(row["upper_violations"] for row in r_files),
    }
    expected_delivered = {
        "denominator": sum(row["delivered_denominator"] for row in r_files),
        "lower_violations": sum(
            row["delivered_lower_violations"] for row in r_files
        ),
        "upper_violations": sum(
            row["delivered_upper_violations"] for row in r_files
        ),
    }
    for key, value in expected_primary.items():
        if primary.get(key) != value:
            raise Refusal(f"{index_path}: M8-R primary {key} does not aggregate")
    for key, value in expected_delivered.items():
        if delivered.get(key) != value:
            raise Refusal(f"{index_path}: M8-R delivered {key} does not aggregate")
    if result["mode"] == "scale" and any(
        primary[key] != delivered[key]
        for key in ("denominator", "violations", "lower_violations", "upper_violations")
    ):
        raise Refusal(f"{index_path}: Scale M8-R domains do not coincide")

    m8_o = index.get("m8_o")
    if not isinstance(m8_o, dict):
        raise Refusal(f"{index_path}: missing M8-O evidence")
    required_o = {
        "violations_file": "m8-o-violations",
        "endpoint_values": "endpoint-values",
        "endpoint_witness_frames": "endpoint-witness-frames",
    }
    named_o_paths: set[str] = set()
    for key, kind in required_o.items():
        row = m8_o.get(key)
        if not isinstance(row, dict) or row.get("kind") != kind:
            raise Refusal(f"{index_path}: missing or invalid M8-O {key}")
        artifact = artifact_by_path.get(row.get("path"))
        if artifact is None or not _same_artifact(row, artifact):
            raise Refusal(f"{index_path}: M8-O {key} artifact mismatch")
        named_o_paths.add(row["path"])
    full_geometry = index.get("full_geometry")
    if not isinstance(full_geometry, dict):
        raise Refusal(f"{index_path}: missing full geometry")
    expected_map_shape = [
        4,
        full_geometry.get("height"),
        full_geometry.get("width"),
        3,
    ]
    for key in ("endpoint_values", "endpoint_witness_frames"):
        if m8_o[key].get("shape") != expected_map_shape:
            raise Refusal(f"{index_path}: {key} does not cover the full grid")
    o_summary = m8_o.get("summary")
    if not isinstance(o_summary, dict):
        raise Refusal(f"{index_path}: malformed M8-O summary")
    _verify_fraction(o_summary, "M8-O")
    if m8_o["violations_file"].get("rows") != o_summary["violations"]:
        raise Refusal(f"{index_path}: M8-O row/violation count mismatch")
    if index.get("mode") == "crop":
        crop = index.get("crop")
        if not isinstance(crop, dict):
            raise Refusal(f"{index_path}: Crop result has no explicit rectangle")
        output_width, output_height = crop.get("width"), crop.get("height")
    else:
        if index.get("crop") is not None:
            raise Refusal(f"{index_path}: Scale result carries a Crop rectangle")
        output_width = full_geometry.get("width")
        output_height = full_geometry.get("height")
    if o_summary["denominator"] != output_width * output_height * 3:
        raise Refusal(f"{index_path}: M8-O denominator does not match output grid")

    required_artifact_paths = {row["path"] for row in r_files} | named_o_paths
    if set(paths) != required_artifact_paths:
        raise Refusal(f"{index_path}: artifact set has missing or extra records")

    for external_key in ("tiff", "source_inventory"):
        external = result.get(external_key)
        if not isinstance(external, dict):
            raise Refusal(f"{result_path}: missing {external_key} identity")
        path = Path(external.get("path", "")).resolve()
        if not path.is_file():
            raise Refusal(f"{result_path}: missing external input {path}")
        if sha256_file(path) != _normalise_sha256(
            external.get("sha256"), external_key
        ):
            raise Refusal(f"{result_path}: external {external_key} hash changed")
    return {
        "verified": True,
        "result": str(result_path),
        "evidence_index": str(index_path),
        "evidence_index_sha256": index_hash,
        "artifacts": len(artifacts),
    }


def independence_report() -> dict[str, Any]:
    path = Path(__file__).resolve()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    forbidden = sorted(name for name in imports if name.lower().startswith("strehl"))
    return {
        "checker": str(path),
        "sha256": sha256_file(path),
        "imports": sorted(imports),
        "forbidden_imports": forbidden,
        "independent": not forbidden,
    }


def _parse_crop(raw: str) -> CropRect:
    fields = raw.split(",")
    if len(fields) != 4:
        raise argparse.ArgumentTypeError("Crop must be x,y,w,h")
    try:
        x, y, width, height = (int(field) for field in fields)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Crop fields must be integers") from error
    return CropRect(x, y, width, height)


def _run_commissioning() -> int:
    test_path = Path(__file__).with_name("test_checker_v2.py")
    if not test_path.is_file():
        raise Refusal(f"commissioning test is missing: {test_path}")
    command = [sys.executable, "-B", str(test_path), "-v"]
    completed = subprocess.run(command, check=False, env=os.environ.copy())
    return int(completed.returncode)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "commission",
        help="run only fixed synthetic commissioning predicates",
    )
    adjudicate = commands.add_parser(
        "adjudicate", help="adjudicate one complete M8 arm"
    )
    adjudicate.add_argument("--capture", required=True)
    adjudicate.add_argument("--trace-dir", type=Path, required=True)
    adjudicate.add_argument("--tiff", type=Path, required=True)
    adjudicate.add_argument("--source-inventory", type=Path, required=True)
    adjudicate.add_argument("--sidecar-sha256", required=True)
    adjudicate.add_argument("--mode", choices=("scale", "crop"), required=True)
    adjudicate.add_argument(
        "--crop",
        type=_parse_crop,
        help="required explicit full-grid x,y,w,h in Crop mode",
    )
    adjudicate.add_argument("--output-dir", type=Path, required=True)
    verify = commands.add_parser(
        "verify", help="verify result, index and artifact hashes"
    )
    verify.add_argument("--result", type=Path, required=True)
    commands.add_parser("independence", help="print the import audit")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "commission":
            return _run_commissioning()
        if args.command == "adjudicate":
            payload = adjudicate_arm(
                capture=args.capture,
                trace_dir=args.trace_dir,
                tiff_path=args.tiff,
                source_inventory_path=args.source_inventory,
                sidecar_sha256=args.sidecar_sha256,
                mode=args.mode,
                crop=args.crop,
                output_dir=args.output_dir,
            )
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        if args.command == "verify":
            print(json.dumps(verify_result(args.result), indent=2, sort_keys=True))
            return 0
        if args.command == "independence":
            payload = independence_report()
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload["independent"] else 1
    except Refusal as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
