#!/usr/bin/env python3
"""Independent evidence verifier for the preregistered M136 M8-O census.

This file deliberately does not import checker_m136.py or any Strehl sampler,
hull, crop, or warp implementation.  It parses trace-v3 blocks, warp maps, and
the final TIFF directly and recomputes the certificate.

Production verification consumes one JSON manifest with schema
``m136-verifier-input-v1``.  It freezes the preregistration, commissioning
report, candidate source commit/source manifest/binary, four instrument files,
and all capture paths/hashes.  Each capture supplies ``input_dir``, ``warpmap``,
``state_dir``, ``output_tiff``, and the twelve labeled ``checker_artifacts``
named by ``REQUIRED_CHECKER_ARTIFACTS`` below.

Exit codes:
  0  independently verified PASS / commissioning passed
  1  independently verified FAIL
  2  UNMEASURED (missing, malformed, or irreconcilable evidence)
  3  checker/verifier disagreement
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import re
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import tifffile


PROTOCOL = "M136 clamped-Catmull-Rom representable-domain M8-O v1"
PREREG_SHA256 = "B656EFB9D2BFEA4B8CF5DD67BE63A9CD7D6930F6B302C7EF93E9E1DF7529BCEB"
INTERPRETATION_COMMIT = "746cc38a"
INTERPRETATION_SHA256 = "8F827FAD6C2A218B473FAFD9287F95E3321E880FF2B36E2D877DC64DC4783C12"
MANIFEST_SCHEMA = "m136-verifier-input-v1"
SOURCE_MANIFEST_SCHEMA = "m136-source-snapshot-v1"
VERIFIER_PROTOCOL = "M136 independent verifier v1"
TRACE_MAGIC = b"M8SITE03"
TRACE_VERSION = 3
ARITHMETIC_CONTRACT = 1
TRACE_HEADER = struct.Struct("<8s15I6d4f32sI")
TRACE_NAME = re.compile(
    r"^m8-trace-v3-p1-f(?P<frame>\d{8})-"
    r"(?P<path_hash>[0-9a-f]{64})-s(?P<sx>[01])(?P<sy>[01])-"
    r"(?P<content_hash>[0-9a-f]{64})\.m8site$"
)
U16_MAX = 65535
FINAL_Q = 1.0 / 131070.0
COVER_MARGIN = 3.0
CHANNEL_NAMES = ("R", "G", "B")
SITE_CHANNEL = {(0, 0): 0, (1, 0): 1, (0, 1): 1, (1, 1): 2}
GREEN_SITES = ((1, 0), (0, 1))
REQUIRED_INSTRUMENTS = {"checker", "fixture", "hook", "runner"}
INSTRUMENT_NAMES = {
    "checker": "checker_m136.py",
    "fixture": "fixture_m136.py",
    "hook": "m8_trace_v3.rs",
    "runner": "run-clamped-m8o.ps1",
}
REQUIRED_CHECKER_ARTIFACTS = {
    "meta",
    "m8_r",
    "m8_r_violations",
    "pre_lower",
    "pre_upper",
    "projected_lower",
    "projected_upper",
    "valid_contributors",
    "m8_o",
    "violations",
    "rail_disclosure",
    "provenance",
}
M8R_VIOLATION_DTYPE = np.dtype(
    [
        ("frame_order", "<u4"),
        ("site_x", "u1"),
        ("site_y", "u1"),
        ("x", "<u4"),
        ("y", "<u4"),
        ("direction", "i1"),
        ("value", "<f4"),
        ("lo", "<f4"),
        ("hi", "<f4"),
        ("tau", "<f4"),
        ("signed_excess", "<f4"),
    ]
)
M8O_VIOLATION_DTYPE = np.dtype(
    [
        ("capture", "U64"),
        ("x", "<u4"),
        ("y", "<u4"),
        ("channel", "U1"),
        ("direction", "i1"),
        ("encoded", "<u2"),
        ("L", "<f4"),
        ("H", "<f4"),
        ("q", "<f8"),
        ("signed_excess", "<f8"),
        ("lower_frame_order", "<i4"),
        ("upper_frame_order", "<i4"),
        ("extremising_frame_order", "<i4"),
    ]
)


class Unmeasured(RuntimeError):
    """The evidence cannot support either PASS or FAIL."""


class Disagreement(RuntimeError):
    """The independent result and checker artifacts disagree."""


@dataclass(frozen=True)
class FrozenFile:
    path: Path
    sha256: str


@dataclass(frozen=True)
class Placement:
    frame_order: int
    placed: bool
    a_re: float | None
    a_im: float | None
    b_re: float | None
    b_im: float | None


@dataclass(frozen=True)
class WarpMap:
    path: Path
    frame_count: int
    width: int
    height: int
    resampler: str
    placements: Mapping[int, Placement]


@dataclass(frozen=True)
class TraceBlock:
    path: Path
    file_sha256: str
    kernel: int
    frame_order: int
    source_width: int
    source_height: int
    full_width: int
    full_height: int
    compact_width: int
    compact_height: int
    crop_x: int
    crop_y: int
    site_x: int
    site_y: int
    channel: int
    arithmetic_contract: int
    a_re: float
    a_im: float
    b_re: float
    b_im: float
    cx: float
    cy: float
    black_level: np.float32
    sensor_range: np.float32
    site_gain: np.float32
    output_gain: np.float32
    frame_source_sha256: str
    frame_path: Path
    source_offset: int
    gathered_offset: int

    @property
    def site(self) -> tuple[int, int]:
        return (self.site_x, self.site_y)

    def source(self) -> np.memmap:
        return np.memmap(
            self.path,
            mode="r",
            dtype="<f4",
            offset=self.source_offset,
            shape=(self.source_height, self.source_width),
        )

    def gathered(self) -> np.memmap:
        return np.memmap(
            self.path,
            mode="r",
            dtype="<f4",
            offset=self.gathered_offset,
            shape=(self.full_height, self.full_width),
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(path.name + ".new")
    staging.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(staging, path)


def require_absolute_existing_file(raw: str, label: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        raise Unmeasured(f"{label} path is not absolute: {raw}")
    if not path.is_file():
        raise Unmeasured(f"{label} file is absent: {path}")
    return path.resolve()


def require_absolute_existing_dir(raw: str, label: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        raise Unmeasured(f"{label} path is not absolute: {raw}")
    if not path.is_dir():
        raise Unmeasured(f"{label} directory is absent: {path}")
    return path.resolve()


def frozen_file(raw: Mapping[str, Any], label: str) -> FrozenFile:
    if not isinstance(raw, Mapping):
        raise Unmeasured(f"{label} must be an object containing path and sha256")
    path = require_absolute_existing_file(str(raw.get("path", "")), label)
    expected = str(raw.get("sha256", "")).upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected):
        raise Unmeasured(f"{label}.sha256 is not a 64-digit hexadecimal digest")
    observed = sha256_file(path)
    if observed != expected:
        raise Unmeasured(f"{label} hash mismatch: expected {expected}, observed {observed}")
    return FrozenFile(path=path, sha256=observed)


def same_f32(a: np.float32, b: np.float32) -> bool:
    return np.asarray(a, dtype="<f4").tobytes() == np.asarray(b, dtype="<f4").tobytes()


def same_f64(a: float, b: float) -> bool:
    return struct.pack("<d", a) == struct.pack("<d", b)


def parse_trace(path: Path, source_hash_cache: dict[Path, str]) -> TraceBlock:
    match = TRACE_NAME.fullmatch(path.name)
    if match is None:
        raise Unmeasured(f"trace block has an invalid filename: {path.name}")
    file_sha = sha256_file(path)
    if file_sha.lower() != match.group("content_hash"):
        raise Unmeasured(
            f"{path.name}: content hash in filename does not match {file_sha}"
        )
    with path.open("rb") as handle:
        raw = handle.read(TRACE_HEADER.size)
        if len(raw) != TRACE_HEADER.size:
            raise Unmeasured(f"{path}: truncated trace-v3 header")
        (
            magic,
            version,
            kernel,
            frame_order,
            source_width,
            source_height,
            full_width,
            full_height,
            compact_width,
            compact_height,
            crop_x,
            crop_y,
            site_x,
            site_y,
            channel,
            arithmetic_contract,
            a_re,
            a_im,
            b_re,
            b_im,
            cx,
            cy,
            black_level,
            sensor_range,
            site_gain,
            output_gain,
            source_sha,
            path_bytes,
        ) = TRACE_HEADER.unpack(raw)
        if magic != TRACE_MAGIC or version != TRACE_VERSION:
            raise Unmeasured(
                f"{path.name}: requires trace-v3 {TRACE_MAGIC!r}, got magic={magic!r}, version={version}"
            )
        if kernel not in (0, 1, 2):
            raise Unmeasured(f"{path.name}: unknown kernel code {kernel}")
        if arithmetic_contract != ARITHMETIC_CONTRACT:
            raise Unmeasured(
                f"{path.name}: arithmetic contract {arithmetic_contract}, expected {ARITHMETIC_CONTRACT}"
            )
        encoded_path = handle.read(path_bytes)
        if len(encoded_path) != path_bytes:
            raise Unmeasured(f"{path.name}: truncated frame path")
        try:
            frame_path = Path(encoded_path.decode("utf-8"))
        except UnicodeDecodeError as error:
            raise Unmeasured(f"{path.name}: frame path is not UTF-8") from error
        source_offset = TRACE_HEADER.size + path_bytes
        gathered_offset = source_offset + source_width * source_height * 4
        expected_size = gathered_offset + full_width * full_height * 4
        handle.seek(0, os.SEEK_END)
        observed_size = handle.tell()
    if observed_size != expected_size:
        raise Unmeasured(
            f"{path.name}: size {observed_size} does not equal header-implied {expected_size}"
        )
    if frame_order != int(match.group("frame")):
        raise Unmeasured(f"{path.name}: frame order disagrees with filename")
    if (site_x, site_y) != (int(match.group("sx")), int(match.group("sy"))):
        raise Unmeasured(f"{path.name}: CFA site disagrees with filename")
    if SITE_CHANNEL.get((site_x, site_y)) != channel:
        raise Unmeasured(f"{path.name}: CFA site/channel pairing is invalid")
    if sha256_bytes(encoded_path).lower() != match.group("path_hash"):
        raise Unmeasured(f"{path.name}: frame-path hash disagrees with filename")
    if not frame_path.is_absolute() or not frame_path.is_file():
        raise Unmeasured(f"{path.name}: source frame is absent or not absolute: {frame_path}")
    frame_path = frame_path.resolve()
    observed_source_hash = source_hash_cache.get(frame_path)
    if observed_source_hash is None:
        observed_source_hash = sha256_file(frame_path)
        source_hash_cache[frame_path] = observed_source_hash
    if observed_source_hash != source_sha.hex().upper():
        raise Unmeasured(f"{path.name}: source frame SHA-256 mismatch")
    if min(source_width, source_height, full_width, full_height, compact_width, compact_height) <= 0:
        raise Unmeasured(f"{path.name}: dimensions must be positive")
    if crop_x + compact_width > full_width or crop_y + compact_height > full_height:
        raise Unmeasured(f"{path.name}: crop rectangle exceeds full plane")
    scalars = (a_re, a_im, b_re, b_im, cx, cy, black_level, sensor_range, site_gain, output_gain)
    if not all(math.isfinite(float(v)) for v in scalars):
        raise Unmeasured(f"{path.name}: non-finite transform or representation scalar")
    if sensor_range <= 0 or site_gain <= 0 or output_gain <= 0:
        raise Unmeasured(f"{path.name}: range and gains must be positive")
    return TraceBlock(
        path=path,
        file_sha256=file_sha,
        kernel=kernel,
        frame_order=frame_order,
        source_width=source_width,
        source_height=source_height,
        full_width=full_width,
        full_height=full_height,
        compact_width=compact_width,
        compact_height=compact_height,
        crop_x=crop_x,
        crop_y=crop_y,
        site_x=site_x,
        site_y=site_y,
        channel=channel,
        arithmetic_contract=arithmetic_contract,
        a_re=a_re,
        a_im=a_im,
        b_re=b_re,
        b_im=b_im,
        cx=cx,
        cy=cy,
        black_level=np.float32(black_level),
        sensor_range=np.float32(sensor_range),
        site_gain=np.float32(site_gain),
        output_gain=np.float32(output_gain),
        frame_source_sha256=source_sha.hex().upper(),
        frame_path=frame_path,
        source_offset=source_offset,
        gathered_offset=gathered_offset,
    )


def f64_from_hex(bits: str) -> float:
    if not re.fullmatch(r"[0-9a-fA-F]{16}", bits):
        raise Unmeasured(f"invalid f64 bit pattern {bits!r}")
    return struct.unpack(">d", bytes.fromhex(bits))[0]


def parse_warpmap(path: Path) -> WarpMap:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "strehl-warpmap 1":
        raise Unmeasured(f"{path}: not a strehl-warpmap 1 file")
    frame_count: int | None = None
    width: int | None = None
    height: int | None = None
    resampler: str | None = None
    placements: dict[int, Placement] = {}
    end_count: int | None = None
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("frames "):
            frame_count = int(line.split()[1])
        elif line.startswith("plane "):
            match = re.fullmatch(r"plane (\d+)x(\d+)", line)
            if match is None:
                raise Unmeasured(f"{path}: malformed plane line {line!r}")
            width, height = map(int, match.groups())
        elif line.startswith("resampler "):
            resampler = line.split(maxsplit=1)[1]
        elif line.startswith("end "):
            end_count = int(line.split()[1])
        elif line[0].isdigit():
            fields = line.split("#", maxsplit=1)[0].split()
            if len(fields) < 2:
                raise Unmeasured(f"{path}: malformed placement line {line!r}")
            frame_order = int(fields[0])
            if frame_order in placements:
                raise Unmeasured(f"{path}: duplicate placement index {frame_order}")
            if fields[1] == "placed":
                if len(fields) != 6:
                    raise Unmeasured(f"{path}: malformed placed line {line!r}")
                values = [f64_from_hex(value) for value in fields[2:]]
                if not all(math.isfinite(value) for value in values):
                    raise Unmeasured(f"{path}: non-finite placement at frame {frame_order}")
                placements[frame_order] = Placement(frame_order, True, *values)
            elif fields[1] == "refused":
                placements[frame_order] = Placement(
                    frame_order, False, None, None, None, None
                )
            else:
                raise Unmeasured(f"{path}: unknown placement state {fields[1]!r}")
    if frame_count is None or width is None or height is None or resampler is None:
        raise Unmeasured(f"{path}: missing frames, plane, or resampler header")
    if end_count != frame_count:
        raise Unmeasured(f"{path}: end count {end_count} != frame count {frame_count}")
    if set(placements) != set(range(frame_count)):
        raise Unmeasured(f"{path}: placement indices are incomplete")
    return WarpMap(path, frame_count, width, height, resampler, placements)


def apply_similarity(
    placement: Placement, x: float, y: float, cx: float, cy: float
) -> tuple[float, float]:
    assert placement.placed
    assert placement.a_re is not None
    assert placement.a_im is not None
    assert placement.b_re is not None
    assert placement.b_im is not None
    xr = x - cx
    yr = y - cy
    return (
        placement.a_re * xr - placement.a_im * yr + placement.b_re + cx,
        placement.a_re * yr + placement.a_im * xr + placement.b_im + cy,
    )


def reconstruct_crop(warpmap: WarpMap) -> tuple[int, int, int, int, float]:
    placed = [p for p in warpmap.placements.values() if p.placed]
    if not placed:
        raise Unmeasured(f"{warpmap.path}: no placed frames")
    width = float(warpmap.width)
    height = float(warpmap.height)
    cx = width * 0.5
    cy = height * 0.5
    corners = (
        (0.0, 0.0),
        (width - 1.0, 0.0),
        (0.0, height - 1.0),
        (width - 1.0, height - 1.0),
    )

    def covers(scale: float) -> bool:
        for placement in placed:
            assert placement.a_re is not None
            assert placement.a_im is not None
            assert placement.b_re is not None
            assert placement.b_im is not None
            composed_a_re = scale * placement.a_re - 0.0 * placement.a_im
            composed_a_im = scale * placement.a_im + 0.0 * placement.a_re
            composed = Placement(
                placement.frame_order,
                True,
                composed_a_re,
                composed_a_im,
                placement.b_re,
                placement.b_im,
            )
            for x, y in corners:
                sx, sy = apply_similarity(composed, x, y, cx, cy)
                if not (
                    sx >= COVER_MARGIN
                    and sy >= COVER_MARGIN
                    and sx <= width - 1.0 - COVER_MARGIN
                    and sy <= height - 1.0 - COVER_MARGIN
                ):
                    return False
        return True

    if covers(1.0):
        scale = 1.0
    else:
        lo = 0.0
        hi = 1.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if covers(mid):
                lo = mid
            else:
                hi = mid
        if lo <= 0.0:
            raise Unmeasured(f"{warpmap.path}: no positive common coverage scale")
        scale = lo

    def axis(n_int: int) -> tuple[int, int]:
        n = float(n_int)
        low = 0.5 * n * (1.0 - scale)
        high = low + scale * (n - 1.0)
        first = max(0, math.ceil(low))
        last = max(first, min(n_int - 1, math.floor(high)))
        return first, last - first + 1

    x, compact_width = axis(warpmap.width)
    y, compact_height = axis(warpmap.height)
    return x, y, compact_width, compact_height, scale


def f32_down(value: np.ndarray | float) -> np.ndarray:
    exact = np.asarray(value, dtype=np.float64)
    rounded = np.asarray(exact, dtype=np.float32)
    return np.where(
        rounded.astype(np.float64) > exact,
        np.nextafter(rounded, np.float32(-np.inf)),
        rounded,
    ).astype(np.float32)


def f32_up(value: np.ndarray | float) -> np.ndarray:
    exact = np.asarray(value, dtype=np.float64)
    rounded = np.asarray(exact, dtype=np.float32)
    return np.where(
        rounded.astype(np.float64) < exact,
        np.nextafter(rounded, np.float32(np.inf)),
        rounded,
    ).astype(np.float32)


def round_ties_away(value: np.ndarray) -> np.ndarray:
    value64 = np.asarray(value, dtype=np.float64)
    return np.where(
        value64 >= 0.0,
        np.floor(value64 + 0.5),
        np.ceil(value64 - 0.5),
    )


def tau_r(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    magnitude = np.maximum(
        np.float32(1.0),
        np.maximum(np.abs(lo, dtype=np.float32), np.abs(hi, dtype=np.float32)),
    )
    ulp = np.nextafter(magnitude, np.float32(np.inf)) - magnitude
    return np.asarray(np.float32(8.0) * ulp, dtype=np.float32)


def source_interval(lo: np.ndarray, hi: np.ndarray, tau: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return (
        f32_down(lo.astype(np.float64) - tau.astype(np.float64)),
        f32_up(hi.astype(np.float64) + tau.astype(np.float64)),
    )


def intermediate_interval(
    lo: np.ndarray,
    hi: np.ndarray,
    site_gain: np.float32,
    black: np.float32,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    inverse_gain = np.float32(np.float32(1.0) / site_gain)
    scaled_lo = f32_down(lo.astype(np.float64) * float(inverse_gain))
    scaled_hi = f32_up(hi.astype(np.float64) * float(inverse_gain))
    restored_lo = f32_down(scaled_lo.astype(np.float64) + float(black))
    restored_hi = f32_up(scaled_hi.astype(np.float64) + float(black))
    u_lo = np.clip(round_ties_away(restored_lo), 0, U16_MAX).astype(np.uint16)
    u_hi = np.clip(round_ties_away(restored_hi), 0, U16_MAX).astype(np.uint16)
    if np.any(u_lo > u_hi):
        raise Unmeasured("non-monotone intermediate-u16 interval")
    black_lo = np.maximum(
        f32_down(u_lo.astype(np.float64) - float(black)), np.float32(0.0)
    )
    black_hi = np.maximum(
        f32_up(u_hi.astype(np.float64) - float(black)), np.float32(0.0)
    )
    return black_lo, black_hi, u_lo, u_hi


def output_interval(
    lo: np.ndarray,
    hi: np.ndarray,
    output_gain: np.float32,
    sensor_range: np.float32,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    pre_lo = f32_down(lo.astype(np.float64) * float(output_gain))
    pre_lo = f32_down(pre_lo.astype(np.float64) / float(sensor_range))
    pre_hi = f32_up(hi.astype(np.float64) * float(output_gain))
    pre_hi = f32_up(pre_hi.astype(np.float64) / float(sensor_range))
    projected_lo = np.clip(pre_lo, np.float32(0.0), np.float32(1.0))
    projected_hi = np.clip(pre_hi, np.float32(0.0), np.float32(1.0))
    return pre_lo, pre_hi, projected_lo, projected_hi


def green_pair_interval(
    g1_lo: np.ndarray,
    g1_hi: np.ndarray,
    g2_lo: np.ndarray,
    g2_hi: np.ndarray,
    output_gain: np.float32,
    sensor_range: np.float32,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean_lo = f32_down(g1_lo.astype(np.float64) + g2_lo.astype(np.float64))
    mean_lo = f32_down(mean_lo.astype(np.float64) * 0.5)
    mean_hi = f32_up(g1_hi.astype(np.float64) + g2_hi.astype(np.float64))
    mean_hi = f32_up(mean_hi.astype(np.float64) * 0.5)
    mean_lo = np.maximum(mean_lo, np.float32(0.0))
    mean_hi = np.maximum(mean_hi, np.float32(0.0))
    return output_interval(mean_lo, mean_hi, output_gain, sensor_range)


def row_coordinates(
    block: TraceBlock, y0: int, y1: int, x0: int, x1: int
) -> tuple[np.ndarray, np.ndarray]:
    ox = 0.5 * block.site_x
    oy = 0.5 * block.site_y
    x = np.arange(x0, x1, dtype=np.float64)[None, :] + ox
    y = np.arange(y0, y1, dtype=np.float64)[:, None] + oy
    xr = x - block.cx
    yr = y - block.cy
    sx = 2.0 * (block.a_re * xr - block.a_im * yr + block.b_re + block.cx)
    sy = 2.0 * (block.a_re * yr + block.a_im * xr + block.b_im + block.cy)
    return sx, sy


def exact_support(
    source: np.ndarray, block: TraceBlock, sx: np.ndarray, sy: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if block.kernel in (0, 2):
        margin = 2.0
        offsets = (-1, 0, 1, 2)
        low_index = 1
        high_x = block.source_width - 3
        high_y = block.source_height - 3
    elif block.kernel == 1:
        margin = 1.0
        offsets = (0, 1)
        low_index = 0
        high_x = block.source_width - 2
        high_y = block.source_height - 2
    else:
        raise Unmeasured(f"unknown kernel code {block.kernel}")
    valid = (
        (sx >= margin - 0.5)
        & (sy >= margin - 0.5)
        & (sx <= block.source_width - 0.5 - margin)
        & (sy <= block.source_height - 0.5 - margin)
    )
    ix = np.floor(sx).astype(np.intp)
    iy = np.floor(sy).astype(np.intp)
    np.clip(ix, low_index, high_x, out=ix)
    np.clip(iy, low_index, high_y, out=iy)
    lo = np.full(sx.shape, np.float32(np.inf), dtype=np.float32)
    hi = np.full(sx.shape, np.float32(-np.inf), dtype=np.float32)
    for dy in offsets:
        for dx in offsets:
            values = np.asarray(source[iy + dy, ix + dx], dtype=np.float32)
            np.minimum(lo, values, out=lo)
            np.maximum(hi, values, out=hi)
    if np.any(valid & (~np.isfinite(lo) | ~np.isfinite(hi))):
        raise Unmeasured(f"{block.path.name}: non-finite source support")
    return valid, lo, hi


def block_geometry_key(block: TraceBlock) -> tuple[Any, ...]:
    return (
        block.kernel,
        block.full_width,
        block.full_height,
        block.compact_width,
        block.compact_height,
        block.crop_x,
        block.crop_y,
        block.cx,
        block.cy,
        block.arithmetic_contract,
    )


def validate_block_set(
    blocks: Sequence[TraceBlock],
    warpmap: WarpMap,
    input_dir: Path,
) -> dict[int, dict[tuple[int, int], TraceBlock]]:
    placed_orders = {index for index, placement in warpmap.placements.items() if placement.placed}
    raw_paths = sorted(
        (
            path.resolve()
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".arw"
        ),
        key=lambda path: str(path),
    )
    if len(raw_paths) != warpmap.frame_count:
        raise Unmeasured(
            f"registered input has {len(raw_paths)} .ARW files but warpmap has "
            f"{warpmap.frame_count} frames"
        )
    expected = {(frame, site) for frame in placed_orders for site in SITE_CHANNEL}
    grouped: dict[int, dict[tuple[int, int], TraceBlock]] = {}
    seen: set[tuple[int, tuple[int, int]]] = set()
    for block in blocks:
        key = (block.frame_order, block.site)
        if key in seen:
            raise Unmeasured(f"duplicate trace-v3 frame/site {key}")
        seen.add(key)
        if block.frame_order not in placed_orders:
            raise Unmeasured(f"trace exists for unplaced frame {block.frame_order}")
        try:
            common = os.path.commonpath(
                [os.path.normcase(str(input_dir)), os.path.normcase(str(block.frame_path))]
            )
        except ValueError as error:
            raise Unmeasured(
                f"frame {block.frame_path} is not on the registered input volume"
            ) from error
        if os.path.normcase(common) != os.path.normcase(str(input_dir)):
            raise Unmeasured(
                f"frame {block.frame_path} is outside registered input {input_dir}"
            )
        if block.frame_path != raw_paths[block.frame_order]:
            raise Unmeasured(
                f"frame {block.frame_order}: trace path {block.frame_path} differs from "
                f"sorted input {raw_paths[block.frame_order]}"
            )
        placement = warpmap.placements[block.frame_order]
        assert placement.placed
        for actual, expected_value, label in (
            (block.a_re, placement.a_re, "a.re"),
            (block.a_im, placement.a_im, "a.im"),
            (block.b_re, placement.b_re, "b.re"),
            (block.b_im, placement.b_im, "b.im"),
        ):
            assert expected_value is not None
            if not same_f64(actual, expected_value):
                raise Unmeasured(
                    f"frame {block.frame_order} site {block.site}: trace {label} differs from warpmap"
                )
        grouped.setdefault(block.frame_order, {})[block.site] = block
    if seen != expected:
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        raise Unmeasured(f"incomplete trace set: missing={missing[:8]}, extra={extra[:8]}")
    first = blocks[0]
    geometry = block_geometry_key(first)
    for block in blocks[1:]:
        if block_geometry_key(block) != geometry:
            raise Unmeasured("trace-v3 blocks disagree on geometry or arithmetic contract")
    if first.full_width != warpmap.width or first.full_height != warpmap.height:
        raise Unmeasured("trace full-plane dimensions disagree with warpmap")
    if first.source_width != 2 * first.full_width or first.source_height != 2 * first.full_height:
        raise Unmeasured("trace source is not the required full-resolution 2x gather plane")
    if not same_f64(first.cx, first.full_width * 0.5) or not same_f64(
        first.cy, first.full_height * 0.5
    ):
        raise Unmeasured("trace transform centre differs from full-plane centre")
    for frame_order, sites in grouped.items():
        frame_blocks = list(sites.values())
        reference = frame_blocks[0]
        for block in frame_blocks[1:]:
            if block.frame_path != reference.frame_path:
                raise Unmeasured(f"frame {frame_order}: CFA sites name different source files")
            if block.frame_source_sha256 != reference.frame_source_sha256:
                raise Unmeasured(f"frame {frame_order}: CFA sites disagree on source SHA-256")
            if not same_f32(block.black_level, reference.black_level):
                raise Unmeasured(f"frame {frame_order}: CFA sites disagree on black level")
            if not same_f32(block.sensor_range, reference.sensor_range):
                raise Unmeasured(f"frame {frame_order}: CFA sites disagree on sensor range")
        g1 = sites[GREEN_SITES[0]]
        g2 = sites[GREEN_SITES[1]]
        if not same_f32(g1.output_gain, g2.output_gain):
            raise Unmeasured(f"frame {frame_order}: G1/G2 output gains differ")
    return grouped


def load_tiff(path: Path, expected_height: int, expected_width: int) -> np.ndarray:
    with tifffile.TiffFile(path) as tif:
        if len(tif.pages) != 1:
            raise Unmeasured(f"{path}: expected one TIFF page, found {len(tif.pages)}")
        page = tif.pages[0]
        if int(page.photometric) != 2:
            raise Unmeasured(f"{path}: TIFF photometric is not RGB")
        if int(page.samplesperpixel) != 3:
            raise Unmeasured(
                f"{path}: TIFF has {page.samplesperpixel} samples per pixel, expected 3"
            )
        orientation = page.tags.get("Orientation")
        if orientation is not None and int(orientation.value) != 1:
            raise Unmeasured(f"{path}: TIFF orientation is not top-left")
        description = page.description or ""
        if "This is the measurement output." not in description:
            raise Unmeasured(
                f"{path}: TIFF does not identify the linear camera-native measurement path"
            )
        image = page.asarray()
    if image.dtype != np.uint16:
        raise Unmeasured(f"{path}: output TIFF dtype is {image.dtype}, expected uint16")
    if image.ndim != 3:
        raise Unmeasured(f"{path}: output TIFF shape {image.shape}, expected HxWx3")
    if image.shape == (expected_height, expected_width, 3):
        return np.asarray(image)
    if image.shape == (3, expected_height, expected_width):
        return np.moveaxis(np.asarray(image), 0, -1)
    raise Unmeasured(
        f"{path}: output TIFF shape {image.shape}, expected "
        f"({expected_height},{expected_width},3)"
    )


def m8r_rows(
    block: TraceBlock,
    y0: int,
    values: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    tau: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
) -> np.ndarray:
    mask = lower | upper
    yy, xx = np.nonzero(mask)
    rows = np.empty(len(xx), dtype=M8R_VIOLATION_DTYPE)
    rows["frame_order"] = block.frame_order
    rows["site_x"] = block.site_x
    rows["site_y"] = block.site_y
    rows["x"] = xx
    rows["y"] = yy + y0
    rows["direction"] = np.where(upper[mask], 1, -1)
    rows["value"] = values[mask]
    rows["lo"] = lo[mask]
    rows["hi"] = hi[mask]
    rows["tau"] = tau[mask]
    rows["signed_excess"] = np.where(
        upper[mask], values[mask] - hi[mask], values[mask] - lo[mask]
    )
    return rows


def verify_m8r_block(block: TraceBlock, chunk_rows: int) -> tuple[dict[str, Any], list[np.ndarray]]:
    source = block.source()
    gathered = block.gathered()
    denominator = 0
    lower_count = 0
    upper_count = 0
    parts: list[np.ndarray] = []
    for y0 in range(0, block.full_height, chunk_rows):
        y1 = min(block.full_height, y0 + chunk_rows)
        sx, sy = row_coordinates(block, y0, y1, 0, block.full_width)
        valid, lo, hi = exact_support(source, block, sx, sy)
        values = np.asarray(gathered[y0:y1], dtype=np.float32)
        finite = np.isfinite(values)
        if np.any(finite ^ valid):
            yy, xx = np.argwhere(finite ^ valid)[0]
            raise Unmeasured(
                f"{block.path.name}: trace/reconstructed coverage mismatch at "
                f"({int(xx)},{int(yy + y0)})"
            )
        tau = tau_r(lo, hi)
        lower = valid & (values < np.asarray(lo - tau, dtype=np.float32))
        upper = valid & (values > np.asarray(hi + tau, dtype=np.float32))
        denominator += int(np.count_nonzero(valid))
        lower_count += int(np.count_nonzero(lower))
        upper_count += int(np.count_nonzero(upper))
        if np.any(lower | upper):
            parts.append(m8r_rows(block, y0, values, lo, hi, tau, lower, upper))
    del source, gathered
    return (
        {
            "frame_order": block.frame_order,
            "site": [block.site_x, block.site_y],
            "denominator": denominator,
            "lower_violations": lower_count,
            "upper_violations": upper_count,
            "violations": lower_count + upper_count,
        },
        parts,
    )


def compact_site_intervals(
    block: TraceBlock,
    source: np.ndarray,
    y0: int,
    y1: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    full_y0 = block.crop_y + y0
    full_y1 = block.crop_y + y1
    full_x0 = block.crop_x
    full_x1 = block.crop_x + block.compact_width
    sx, sy = row_coordinates(block, full_y0, full_y1, full_x0, full_x1)
    valid, lo, hi = exact_support(source, block, sx, sy)
    tau = tau_r(lo, hi)
    interval_lo, interval_hi = source_interval(lo, hi, tau)
    black_lo, black_hi, _, _ = intermediate_interval(
        interval_lo, interval_hi, block.site_gain, block.black_level
    )
    return valid, black_lo, black_hi


def create_array(path: Path, dtype: str, shape: tuple[int, ...], fill: float | int) -> np.memmap:
    array = np.lib.format.open_memmap(path, mode="w+", dtype=dtype, shape=shape)
    array[...] = fill
    array.flush()
    return array


def update_aggregate(
    low_array: np.ndarray,
    high_array: np.ndarray,
    channel: int,
    y0: int,
    valid: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    frame_order: int,
    valid_array: np.ndarray | None = None,
    low_frame_array: np.ndarray | None = None,
    high_frame_array: np.ndarray | None = None,
) -> None:
    y1 = y0 + valid.shape[0]
    low_view = low_array[channel, y0:y1]
    high_view = high_array[channel, y0:y1]
    lower_update = valid & (low < low_view)
    upper_update = valid & (high > high_view)
    low_view[lower_update] = low[lower_update]
    high_view[upper_update] = high[upper_update]
    if valid_array is not None:
        valid_array[channel, y0:y1][valid] += 1
    if low_frame_array is not None:
        low_frame_array[channel, y0:y1][lower_update] = frame_order
    if high_frame_array is not None:
        high_frame_array[channel, y0:y1][upper_update] = frame_order


def build_m8o_rows(
    capture: str,
    image: np.ndarray,
    projected_lo: np.ndarray,
    projected_hi: np.ndarray,
    low_frames: np.ndarray,
    high_frames: np.ndarray,
    chunk_rows: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    parts: list[np.ndarray] = []
    lower_count = 0
    upper_count = 0
    height, width, _ = image.shape
    for y0 in range(0, height, chunk_rows):
        y1 = min(height, y0 + chunk_rows)
        encoded = np.moveaxis(image[y0:y1], -1, 0)
        value = encoded.astype(np.float64) / float(U16_MAX)
        lo = np.asarray(projected_lo[:, y0:y1], dtype=np.float32)
        hi = np.asarray(projected_hi[:, y0:y1], dtype=np.float32)
        lower = value < lo.astype(np.float64) - FINAL_Q
        upper = value > hi.astype(np.float64) + FINAL_Q
        if np.any(lower & upper):
            raise Unmeasured("a coordinate is simultaneously below and above its interval")
        lower_count += int(np.count_nonzero(lower))
        upper_count += int(np.count_nonzero(upper))
        mask = lower | upper
        if not np.any(mask):
            continue
        cc, yy, xx = np.nonzero(mask)
        rows = np.empty(len(xx), dtype=M8O_VIOLATION_DTYPE)
        rows["capture"] = capture
        rows["x"] = xx
        rows["y"] = yy + y0
        rows["channel"] = np.asarray(CHANNEL_NAMES)[cc]
        rows["direction"] = np.where(upper[mask], 1, -1)
        rows["encoded"] = encoded[mask]
        rows["L"] = lo[mask]
        rows["H"] = hi[mask]
        rows["q"] = FINAL_Q
        rows["signed_excess"] = np.where(
            upper[mask],
            value[mask] - hi[mask].astype(np.float64),
            value[mask] - lo[mask].astype(np.float64),
        )
        selected_low_frames = np.asarray(low_frames[:, y0:y1])[mask]
        selected_high_frames = np.asarray(high_frames[:, y0:y1])[mask]
        rows["lower_frame_order"] = selected_low_frames
        rows["upper_frame_order"] = selected_high_frames
        rows["extremising_frame_order"] = np.where(
            upper[mask], selected_high_frames, selected_low_frames
        )
        parts.append(rows)
    rows = (
        np.concatenate(parts)
        if parts
        else np.empty(0, dtype=M8O_VIOLATION_DTYPE)
    )
    return rows, {
        "denominator": int(height * width * 3),
        "lower_violations": lower_count,
        "upper_violations": upper_count,
        "violations": lower_count + upper_count,
        "fraction": (lower_count + upper_count) / float(height * width * 3),
    }


def rail_disclosure(
    image: np.ndarray,
    pre_lo: np.ndarray,
    pre_hi: np.ndarray,
    projected_lo: np.ndarray,
    projected_hi: np.ndarray,
) -> dict[str, Any]:
    encoded = np.moveaxis(image, -1, 0)
    value = encoded.astype(np.float64) / float(U16_MAX)
    lower_violation = value < projected_lo.astype(np.float64) - FINAL_Q
    upper_violation = value > projected_hi.astype(np.float64) + FINAL_Q
    high_beyond = pre_lo.astype(np.float64) - FINAL_Q > 1.0
    low_beyond = pre_hi.astype(np.float64) + FINAL_Q < 0.0
    full = encoded == U16_MAX
    zero = encoded == 0
    return {
        "source_interval_wholly_above_representable": {
            "coordinates": int(np.count_nonzero(high_beyond)),
            "full_rail": int(np.count_nonzero(high_beyond & full)),
            "off_rail": int(np.count_nonzero(high_beyond & ~full)),
        },
        "source_interval_wholly_below_representable": {
            "coordinates": int(np.count_nonzero(low_beyond)),
            "zero_rail": int(np.count_nonzero(low_beyond & zero)),
            "off_rail": int(np.count_nonzero(low_beyond & ~zero)),
        },
        "projected_violations": {
            "coordinates": int(np.count_nonzero(lower_violation | upper_violation)),
            "at_full_rail": int(np.count_nonzero((lower_violation | upper_violation) & full)),
            "at_zero_rail": int(np.count_nonzero((lower_violation | upper_violation) & zero)),
            "off_rail": int(
                np.count_nonzero((lower_violation | upper_violation) & ~full & ~zero)
            ),
        },
    }


def load_checker_array(file: FrozenFile, label: str, shape: tuple[int, ...]) -> np.ndarray:
    try:
        array = np.load(file.path, mmap_mode="r", allow_pickle=False)
    except Exception as error:
        raise Unmeasured(f"{label}: could not open NumPy artifact {file.path}") from error
    if array.shape == shape:
        return array
    channel_last = (shape[1], shape[2], shape[0])
    if array.shape == channel_last:
        return np.moveaxis(array, -1, 0)
    raise Disagreement(f"{label}: checker shape {array.shape} != verifier shape {shape}")


def arrays_equal(a: np.ndarray, b: np.ndarray) -> bool:
    if a.dtype.kind == "f" or b.dtype.kind == "f":
        return bool(np.array_equal(a, b, equal_nan=True))
    return bool(np.array_equal(a, b))


def metric_counts(document: Mapping[str, Any], metric: str) -> Mapping[str, Any]:
    candidates: list[Mapping[str, Any]] = []
    direct = document.get(metric)
    if isinstance(direct, Mapping):
        nested = direct.get("aggregate")
        if isinstance(nested, Mapping):
            candidates.append(nested)
        candidates.append(direct)
    aggregate = document.get("aggregate")
    if isinstance(aggregate, Mapping):
        nested = aggregate.get(metric)
        if isinstance(nested, Mapping):
            candidates.append(nested)
        candidates.append(aggregate)
    candidates.append(document)
    for candidate in candidates:
        denominator = candidate.get("denominator")
        violations = candidate.get("violations")
        if (
            isinstance(denominator, int)
            and not isinstance(denominator, bool)
            and isinstance(violations, int)
            and not isinstance(violations, bool)
        ):
            return candidate
    raise Unmeasured(
        f"checker JSON has no aggregate {metric} object with integer denominator/violations"
    )


def compare_checker_artifacts(
    files: Mapping[str, FrozenFile],
    result: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    m8r_violations: np.ndarray,
    violations: np.ndarray,
    rails: Mapping[str, Any],
) -> dict[str, Any]:
    compared: dict[str, Any] = {}
    for label in ("meta", "m8_r", "m8_o", "rail_disclosure", "provenance"):
        try:
            document = json.loads(files[label].path.read_text(encoding="utf-8"))
        except Exception as error:
            raise Unmeasured(f"{label}: invalid JSON artifact {files[label].path}") from error
        if not isinstance(document, Mapping):
            raise Unmeasured(f"{label}: JSON root must be an object")
        compared[label] = {"opened": True, "sha256": files[label].sha256}

    checker_m8r = json.loads(files["m8_r"].path.read_text(encoding="utf-8"))
    checker_m8o = json.loads(files["m8_o"].path.read_text(encoding="utf-8"))
    checker_m8r_counts = metric_counts(checker_m8r, "m8_r")
    checker_m8o_counts = metric_counts(checker_m8o, "m8_o")
    if checker_m8r_counts["denominator"] != result["m8_r"]["denominator"]:
        raise Disagreement("checker/verifier M8-R denominator mismatch")
    if checker_m8r_counts["violations"] != result["m8_r"]["violations"]:
        raise Disagreement("checker/verifier M8-R violation-count mismatch")
    if checker_m8o_counts["denominator"] != result["m8_o"]["denominator"]:
        raise Disagreement("checker/verifier M8-O denominator mismatch")
    if checker_m8o_counts["violations"] != result["m8_o"]["violations"]:
        raise Disagreement("checker/verifier M8-O violation-count mismatch")
    expected_m8o_status = "PASS" if result["m8_o"]["violations"] == 0 else "FAIL"
    for key in ("status", "verdict", "decision"):
        declared = checker_m8o.get(key)
        if isinstance(declared, str) and declared.upper() in {"PASS", "FAIL"}:
            if declared.upper() != expected_m8o_status:
                raise Disagreement(
                    f"checker declares {declared.upper()} but raw evidence is "
                    f"{expected_m8o_status}"
                )

    checker_m8r_violations = np.load(files["m8_r_violations"].path, allow_pickle=False)
    required_m8r_fields = set(M8R_VIOLATION_DTYPE.names or ())
    if (
        checker_m8r_violations.dtype.names is None
        or not required_m8r_fields.issubset(checker_m8r_violations.dtype.names)
    ):
        raise Disagreement("checker M8-R violation artifact omits required fields")
    if len(checker_m8r_violations) != len(m8r_violations):
        raise Disagreement("checker/verifier M8-R violation-row count mismatch")
    m8r_order_fields = ("frame_order", "site_x", "site_y", "y", "x", "direction")
    checker_m8r_order = np.lexsort(
        tuple(checker_m8r_violations[name] for name in reversed(m8r_order_fields))
    )
    verifier_m8r_order = np.lexsort(
        tuple(m8r_violations[name] for name in reversed(m8r_order_fields))
    )
    for field in required_m8r_fields:
        left = checker_m8r_violations[field][checker_m8r_order]
        right = m8r_violations[field][verifier_m8r_order]
        if not arrays_equal(np.asarray(left), np.asarray(right)):
            raise Disagreement(f"checker/verifier M8-R violation field mismatch: {field}")
    compared["m8_r_violations"] = {
        "equal": True,
        "sha256": files["m8_r_violations"].sha256,
    }

    for label, verifier_name in (
        ("pre_lower", "pre_lower"),
        ("pre_upper", "pre_upper"),
        ("projected_lower", "projected_lower"),
        ("projected_upper", "projected_upper"),
        ("valid_contributors", "valid_contributors"),
    ):
        checker = load_checker_array(files[label], label, arrays[verifier_name].shape)
        if not arrays_equal(np.asarray(checker), np.asarray(arrays[verifier_name])):
            raise Disagreement(f"checker/verifier array mismatch: {label}")
        compared[label] = {"equal": True, "sha256": files[label].sha256}

    checker_violations = np.load(files["violations"].path, allow_pickle=False)
    required_fields = {
        "capture",
        "x",
        "y",
        "channel",
        "direction",
        "encoded",
        "L",
        "H",
        "q",
        "signed_excess",
        "lower_frame_order",
        "upper_frame_order",
        "extremising_frame_order",
    }
    if checker_violations.dtype.names is None or not required_fields.issubset(
        checker_violations.dtype.names
    ):
        raise Disagreement("checker violation artifact omits required fields")
    if len(checker_violations) != len(violations):
        raise Disagreement("checker/verifier violation-row count mismatch")
    order_fields = ("capture", "y", "x", "channel", "direction")
    checker_order = np.lexsort(tuple(checker_violations[name] for name in reversed(order_fields)))
    verifier_order = np.lexsort(tuple(violations[name] for name in reversed(order_fields)))
    for field in required_fields:
        left = checker_violations[field][checker_order]
        right = violations[field][verifier_order]
        if not arrays_equal(np.asarray(left), np.asarray(right)):
            raise Disagreement(f"checker/verifier violation field mismatch: {field}")
    compared["violations"] = {"equal": True, "sha256": files["violations"].sha256}

    checker_rails_doc = json.loads(
        files["rail_disclosure"].path.read_text(encoding="utf-8")
    )
    checker_rails = checker_rails_doc.get("rail_disclosure", checker_rails_doc)
    if checker_rails != rails:
        raise Disagreement("checker/verifier rail disclosure mismatch")
    compared["rail_disclosure"]["equal"] = True
    return compared


def verify_capture(
    capture: str,
    input_dir: Path,
    warpmap_file: FrozenFile,
    state_dir: Path,
    output_file: FrozenFile,
    artifact_dir: Path,
    chunk_rows: int,
    checker_artifacts: Mapping[str, FrozenFile] | None,
) -> dict[str, Any]:
    warpmap = parse_warpmap(warpmap_file.path)
    if warpmap.resampler != "clamped-catmull":
        raise Unmeasured(f"{capture}: warpmap resampler is {warpmap.resampler!r}")
    crop_x, crop_y, compact_width, compact_height, cover_scale = reconstruct_crop(warpmap)

    claims = state_dir / "claims"
    staging = state_dir / "staging"
    for directory, label in ((claims, "claim"), (staging, "staging")):
        if directory.exists() and any(directory.iterdir()):
            raise Unmeasured(f"{capture}: unresolved trace {label} files exist in {directory}")
    block_dir = state_dir / "blocks"
    if not block_dir.is_dir():
        raise Unmeasured(f"{capture}: trace blocks directory is absent: {block_dir}")
    unexpected = [
        path.name
        for path in block_dir.iterdir()
        if not path.is_file() or not TRACE_NAME.fullmatch(path.name)
    ]
    if unexpected:
        raise Unmeasured(f"{capture}: unexpected entries in trace blocks: {unexpected[:8]}")
    block_paths = sorted(block_dir.glob("*.m8site"))
    if not block_paths:
        raise Unmeasured(f"{capture}: no trace-v3 blocks")
    source_hash_cache: dict[Path, str] = {}
    blocks = [parse_trace(path, source_hash_cache) for path in block_paths]
    grouped = validate_block_set(blocks, warpmap, input_dir)
    first = blocks[0]
    expected_crop = (crop_x, crop_y, compact_width, compact_height)
    trace_crop = (first.crop_x, first.crop_y, first.compact_width, first.compact_height)
    if trace_crop != expected_crop:
        raise Unmeasured(
            f"{capture}: trace crop {trace_crop} != independently reconstructed {expected_crop}"
        )
    if any(block.kernel != 2 for block in blocks):
        raise Unmeasured(f"{capture}: target contains a non-clamped-Catmull trace")

    image = load_tiff(output_file.path, compact_height, compact_width)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    shape = (3, compact_height, compact_width)
    pre_lower = create_array(artifact_dir / "pre-lower.npy", "<f4", shape, np.inf)
    pre_upper = create_array(artifact_dir / "pre-upper.npy", "<f4", shape, -np.inf)
    projected_lower = create_array(
        artifact_dir / "projected-lower.npy", "<f4", shape, np.inf
    )
    projected_upper = create_array(
        artifact_dir / "projected-upper.npy", "<f4", shape, -np.inf
    )
    valid_contributors = create_array(
        artifact_dir / "valid-contributors.npy", "<u2", shape, 0
    )
    low_frames = create_array(artifact_dir / "low-frames.npy", "<i4", shape, -1)
    high_frames = create_array(artifact_dir / "high-frames.npy", "<i4", shape, -1)

    m8r_summaries: list[dict[str, Any]] = []
    m8r_parts: list[np.ndarray] = []
    for block in blocks:
        summary, parts = verify_m8r_block(block, chunk_rows)
        m8r_summaries.append(summary)
        m8r_parts.extend(parts)
    m8r_violations = (
        np.concatenate(m8r_parts)
        if m8r_parts
        else np.empty(0, dtype=M8R_VIOLATION_DTYPE)
    )
    np.save(artifact_dir / "m8-r-violations.npy", m8r_violations, allow_pickle=False)

    for frame_order in sorted(grouped):
        sites = grouped[frame_order]
        red = sites[(0, 0)]
        g1 = sites[(1, 0)]
        blue = sites[(1, 1)]
        sources = {site: block.source() for site, block in sites.items()}
        try:
            for y0 in range(0, compact_height, chunk_rows):
                y1 = min(compact_height, y0 + chunk_rows)
                site_intervals: dict[
                    tuple[int, int], tuple[np.ndarray, np.ndarray, np.ndarray]
                ] = {}
                for site, block in sites.items():
                    site_intervals[site] = compact_site_intervals(
                        block, sources[site], y0, y1
                    )

                for channel, block in ((0, red), (2, blue)):
                    valid, black_lo, black_hi = site_intervals[block.site]
                    pre_lo, pre_hi, proj_lo, proj_hi = output_interval(
                        black_lo, black_hi, block.output_gain, block.sensor_range
                    )
                    update_aggregate(
                        pre_lower,
                        pre_upper,
                        channel,
                        y0,
                        valid,
                        pre_lo,
                        pre_hi,
                        frame_order,
                    )
                    update_aggregate(
                        projected_lower,
                        projected_upper,
                        channel,
                        y0,
                        valid,
                        proj_lo,
                        proj_hi,
                        frame_order,
                        valid_contributors,
                        low_frames,
                        high_frames,
                    )

                valid_g1, g1_lo, g1_hi = site_intervals[GREEN_SITES[0]]
                valid_g2, g2_lo, g2_hi = site_intervals[GREEN_SITES[1]]
                valid_green = valid_g1 & valid_g2
                if np.any(valid_g1 ^ valid_g2):
                    raise Unmeasured(
                        f"{capture}: frame {frame_order} green sites have unequal coverage"
                    )
                pre_lo, pre_hi, proj_lo, proj_hi = green_pair_interval(
                    g1_lo, g1_hi, g2_lo, g2_hi, g1.output_gain, g1.sensor_range
                )
                update_aggregate(
                    pre_lower,
                    pre_upper,
                    1,
                    y0,
                    valid_green,
                    pre_lo,
                    pre_hi,
                    frame_order,
                )
                update_aggregate(
                    projected_lower,
                    projected_upper,
                    1,
                    y0,
                    valid_green,
                    proj_lo,
                    proj_hi,
                    frame_order,
                    valid_contributors,
                    low_frames,
                    high_frames,
                )
        finally:
            sources.clear()

    for array in (
        pre_lower,
        pre_upper,
        projected_lower,
        projected_upper,
        valid_contributors,
        low_frames,
        high_frames,
    ):
        array.flush()

    placed_count = len(grouped)
    if np.any(valid_contributors != placed_count):
        channel, y, x = np.argwhere(valid_contributors != placed_count)[0]
        raise Unmeasured(
            f"{capture}: Crop is not covered by every frame/site at "
            f"({int(x)},{int(y)},{CHANNEL_NAMES[int(channel)]}); "
            f"contributors={int(valid_contributors[channel,y,x])}, expected={placed_count}"
        )
    if np.any(~np.isfinite(pre_lower)) or np.any(~np.isfinite(pre_upper)):
        raise Unmeasured(f"{capture}: aggregate interval contains non-finite values")
    if np.any(pre_lower > pre_upper) or np.any(projected_lower > projected_upper):
        raise Unmeasured(f"{capture}: aggregate interval is inverted")

    violations, m8o = build_m8o_rows(
        capture,
        image,
        projected_lower,
        projected_upper,
        low_frames,
        high_frames,
        chunk_rows,
    )
    np.save(artifact_dir / "m8-o-violations.npy", violations, allow_pickle=False)
    rails = rail_disclosure(
        image, pre_lower, pre_upper, projected_lower, projected_upper
    )
    m8r = {
        "denominator": sum(item["denominator"] for item in m8r_summaries),
        "lower_violations": sum(item["lower_violations"] for item in m8r_summaries),
        "upper_violations": sum(item["upper_violations"] for item in m8r_summaries),
        "violations": sum(item["violations"] for item in m8r_summaries),
        "blocks": m8r_summaries,
    }
    result: dict[str, Any] = {
        "capture": capture,
        "crop": {
            "x": crop_x,
            "y": crop_y,
            "width": compact_width,
            "height": compact_height,
            "cover_scale": cover_scale,
        },
        "frames": placed_count,
        "trace_blocks": len(blocks),
        "m8_r": m8r,
        "m8_o": m8o,
        "rail_disclosure": rails,
        "evidence": {
            "warpmap": {"path": str(warpmap_file.path), "sha256": warpmap_file.sha256},
            "output_tiff": {"path": str(output_file.path), "sha256": output_file.sha256},
            "trace_sha256": {block.path.name: block.file_sha256 for block in blocks},
            "source_sha256": {
                str(path): digest for path, digest in sorted(source_hash_cache.items(), key=lambda x: str(x[0]))
            },
        },
    }
    arrays = {
        "pre_lower": pre_lower,
        "pre_upper": pre_upper,
        "projected_lower": projected_lower,
        "projected_upper": projected_upper,
        "valid_contributors": valid_contributors,
    }
    if checker_artifacts is not None:
        result["checker_comparison"] = compare_checker_artifacts(
            checker_artifacts,
            result,
            arrays,
            m8r_violations,
            violations,
            rails,
        )
    result["independent_artifacts"] = {
        path.name: {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
        }
        for path in sorted(artifact_dir.glob("*.npy"))
    }
    json_dump(artifact_dir / "result.json", result)
    return result


def parse_instruments(raw: Any) -> dict[str, FrozenFile]:
    if not isinstance(raw, Mapping) or set(raw) != REQUIRED_INSTRUMENTS:
        raise Unmeasured(
            f"instruments must contain exactly {sorted(REQUIRED_INSTRUMENTS)}"
        )
    files = {name: frozen_file(value, f"instrument {name}") for name, value in raw.items()}
    for name, file in files.items():
        if file.path.name != INSTRUMENT_NAMES[name]:
            raise Unmeasured(
                f"instrument {name} must be named {INSTRUMENT_NAMES[name]}, got {file.path.name}"
            )
    if len({file.path for file in files.values()}) != len(files):
        raise Unmeasured("instrument paths must be distinct")
    return files


def verify_independence(verifier_path: Path) -> dict[str, Any]:
    source = verifier_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(verifier_path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = [
        name
        for name in imports
        if "checker_m136" in name
        or name.startswith("strehl")
        or ".strehl" in name
    ]
    if forbidden:
        raise Unmeasured(f"verifier has forbidden imports: {forbidden}")
    return {"imports": sorted(imports), "forbidden_imports": forbidden}


def validate_commission_report(
    file: FrozenFile,
    prereg_hash: str,
    interpretation_hash: str,
    verifier_hash: str,
) -> dict[str, Any]:
    try:
        report = json.loads(file.path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(f"invalid verifier commissioning report {file.path}") from error
    if report.get("protocol") != VERIFIER_PROTOCOL or report.get("status") != "PASS":
        raise Unmeasured("verifier commissioning report is not a PASS for this protocol")
    if report.get("preregistration", {}).get("sha256") != prereg_hash:
        raise Unmeasured("verifier commissioning used a different preregistration")
    if (
        report.get("prospective_interpretation", {}).get("sha256")
        != interpretation_hash
    ):
        raise Unmeasured("verifier commissioning used a different interpretation")
    if report.get("verifier", {}).get("sha256") != verifier_hash:
        raise Unmeasured("verifier commissioning was produced by different verifier bytes")
    defect = report.get("degradation_plant", {})
    improvement = report.get("improvement_plant", {})
    defect_landed = defect.get("landed", {})
    improvement_landed = improvement.get("landed", {})
    if defect_landed.get("occurrences") != 1:
        raise Unmeasured("commissioned degradation plant was not uniquely anchored")
    if (
        defect_landed.get("sha256_before") == defect_landed.get("sha256_after")
        or not re.fullmatch(r"[0-9A-F]{64}", str(defect_landed.get("sha256_before", "")))
        or not re.fullmatch(r"[0-9A-F]{64}", str(defect_landed.get("sha256_after", "")))
    ):
        raise Unmeasured("commissioned degradation plant has no valid changed hash")
    if defect.get("result", {}).get("m8_o_violations") != 1:
        raise Unmeasured("commissioned degradation did not produce exactly one violation")
    if defect.get("result", {}).get("status") != "FAIL":
        raise Unmeasured("commissioned degradation was not reported FAIL")
    if improvement_landed.get("occurrences") != 1:
        raise Unmeasured("commissioned improvement plant was not uniquely anchored")
    if (
        improvement_landed.get("sha256_before")
        == improvement_landed.get("sha256_after")
        or not re.fullmatch(
            r"[0-9A-F]{64}", str(improvement_landed.get("sha256_before", ""))
        )
        or not re.fullmatch(
            r"[0-9A-F]{64}", str(improvement_landed.get("sha256_after", ""))
        )
    ):
        raise Unmeasured("commissioned improvement plant has no valid changed hash")
    if improvement.get("result", {}).get("m8_o_violations") != 0:
        raise Unmeasured("commissioned improvement did not remove the violation")
    if improvement.get("result", {}).get("status") != "PASS":
        raise Unmeasured("commissioned improvement was not reported PASS")
    if (
        defect.get("result", {}).get("output_sha256")
        == improvement.get("result", {}).get("output_sha256")
    ):
        raise Unmeasured("commissioned defect and improvement TIFF hashes are identical")
    numeric_cases = report.get("numeric_cases")
    if not isinstance(numeric_cases, Mapping) or len(numeric_cases) != 8:
        raise Unmeasured("commissioning report does not contain all eight numeric cases")
    if any(not isinstance(case, Mapping) for case in numeric_cases.values()):
        raise Unmeasured("a numeric commissioning case is malformed")
    if any(
        case.get("observed_violations") != case.get("expected_violations")
        for case in numeric_cases.values()
    ):
        raise Unmeasured("a numeric commissioning case did not match its expectation")
    if report.get("interval_containment", {}).get("misses") != 0:
        raise Unmeasured("outward interval commissioning found a containment miss")
    pairing = report.get("green_pairing_case", {})
    if pairing.get("same_frame_violation") is not True or pairing.get(
        "independent_site_violation"
    ) is not False:
        raise Unmeasured("green-pairing commissioning does not distinguish the rules")
    fail_closed = report.get("fail_closed", {})
    if (
        not fail_closed.get("missing_frame_site")
        or not fail_closed.get("duplicate_frame_site")
        or not fail_closed.get("trace_v2")
        or not fail_closed.get("wrong_crop_origin")
        or fail_closed.get("producer_supplied_hull_ignored") is not True
    ):
        raise Unmeasured("fail-closed commissioning evidence is incomplete")
    return {
        "path": str(file.path),
        "sha256": file.sha256,
        "degradation": "one planted lower violation caught",
        "improvement": "the planted violation removed",
    }


def build_relevant_source_files(source_root: Path) -> set[str]:
    required_roots = (
        source_root / "Cargo.toml",
        source_root / "Cargo.lock",
        source_root / "rust-toolchain.toml",
    )
    paths = {path for path in required_roots if path.is_file()}
    for directory in (source_root / ".cargo", source_root / "crates"):
        if directory.is_dir():
            paths.update(path for path in directory.rglob("*") if path.is_file())
    hook = source_root / "experiments" / "M136-m8o-bar" / "m8_trace_v3.rs"
    if hook.is_file():
        paths.add(hook)
    if not (source_root / "Cargo.toml").is_file() or not (source_root / "crates").is_dir():
        raise Unmeasured(f"{source_root}: source snapshot lacks Cargo.toml or crates/")
    return {
        path.relative_to(source_root).as_posix()
        for path in paths
        if "target" not in path.relative_to(source_root).parts
    }


def verify_source_manifest(
    file: FrozenFile,
    source_root: Path,
    expected_commit: str,
    hook_hash: str,
) -> dict[str, Any]:
    try:
        document = json.loads(file.path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(f"invalid source snapshot manifest {file.path}") from error
    if document.get("schema") != SOURCE_MANIFEST_SCHEMA:
        raise Unmeasured(
            f"source manifest schema must be {SOURCE_MANIFEST_SCHEMA!r}"
        )
    if str(document.get("source_commit", "")).lower() != expected_commit.lower():
        raise Unmeasured("source manifest commit differs from registered source commit")
    raw_files = document.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise Unmeasured("source manifest files must be a non-empty list")
    declared: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(raw_files):
        if not isinstance(raw, Mapping):
            raise Unmeasured(f"source manifest file {index} is not an object")
        relative = str(raw.get("path", "")).replace("\\", "/")
        rel_path = Path(relative)
        if (
            not relative
            or rel_path.is_absolute()
            or ".." in rel_path.parts
            or relative in declared
        ):
            raise Unmeasured(f"invalid or duplicate source-manifest path {relative!r}")
        declared[relative] = raw
    relevant = build_relevant_source_files(source_root)
    if set(declared) != relevant:
        missing = sorted(relevant - set(declared))
        extra = sorted(set(declared) - relevant)
        raise Unmeasured(
            f"source manifest inventory mismatch: missing={missing[:8]}, extra={extra[:8]}"
        )
    observed: dict[str, str] = {}
    for relative, raw in declared.items():
        path = (source_root / Path(relative)).resolve()
        try:
            common = os.path.commonpath(
                [os.path.normcase(str(source_root)), os.path.normcase(str(path))]
            )
        except ValueError as error:
            raise Unmeasured(f"source manifest path escapes root: {relative}") from error
        if os.path.normcase(common) != os.path.normcase(str(source_root)):
            raise Unmeasured(f"source manifest path escapes root: {relative}")
        if not path.is_file() or path.is_symlink():
            raise Unmeasured(f"source manifest file is absent or a symlink: {relative}")
        expected_hash = str(raw.get("sha256", "")).upper()
        expected_bytes = raw.get("bytes")
        if not re.fullmatch(r"[0-9A-F]{64}", expected_hash):
            raise Unmeasured(f"source manifest hash is invalid: {relative}")
        if (
            not isinstance(expected_bytes, int)
            or isinstance(expected_bytes, bool)
            or expected_bytes < 0
        ):
            raise Unmeasured(f"source manifest byte count is invalid: {relative}")
        if path.stat().st_size != expected_bytes:
            raise Unmeasured(f"source snapshot byte count changed: {relative}")
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise Unmeasured(f"source snapshot hash changed: {relative}")
        observed[relative] = actual_hash
    hook_matches = [
        relative
        for relative, digest in observed.items()
        if Path(relative).name == "m8_trace_v3.rs" and digest == hook_hash
    ]
    if not hook_matches:
        raise Unmeasured(
            "source snapshot must contain an m8_trace_v3.rs "
            "matching the registered hook"
        )
    return {
        "path": str(file.path),
        "sha256": file.sha256,
        "source_commit": expected_commit,
        "files": len(observed),
        "matching_hook_paths": hook_matches,
    }


def verify_manifest(manifest_path: Path, report_path: Path, chunk_rows: int) -> tuple[int, dict[str, Any]]:
    manifest_file_hash = sha256_file(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(f"invalid verifier manifest {manifest_path}") from error
    if not isinstance(manifest, Mapping) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise Unmeasured(f"manifest schema must be {MANIFEST_SCHEMA!r}")

    prereg_file = require_absolute_existing_file(
        str(manifest.get("preregistration", "")), "preregistration"
    )
    prereg_hash = sha256_file(prereg_file)
    frozen_prereg = Path(__file__).with_name("clamped-m8o-preregistration.json").resolve()
    if prereg_file != frozen_prereg:
        raise Unmeasured(
            f"preregistration must be the frozen repository file {frozen_prereg}"
        )
    if prereg_hash != PREREG_SHA256:
        raise Unmeasured(
            f"frozen preregistration hash mismatch: expected {PREREG_SHA256}, observed {prereg_hash}"
        )
    prereg = json.loads(prereg_file.read_text(encoding="utf-8"))
    if prereg.get("protocol") != PROTOCOL:
        raise Unmeasured("preregistration protocol mismatch")
    decision = prereg.get("decision", {})
    if decision.get("example_40") != "V=40 is FAIL." or "V=0" not in str(
        decision.get("m8_o_pass", "")
    ):
        raise Unmeasured("preregistration decision rule is not the frozen exact-zero rule")
    interpretation_path = Path(__file__).with_name("prospective-interpretations.md").resolve()
    if not interpretation_path.is_file():
        raise Unmeasured(f"prospective interpretation is absent: {interpretation_path}")
    interpretation_hash = sha256_file(interpretation_path)
    if interpretation_hash != INTERPRETATION_SHA256:
        raise Unmeasured(
            "prospective interpretation bytes differ from the pre-target ruling"
        )
    verifier_path = Path(__file__).resolve()
    verifier_hash = sha256_file(verifier_path)
    commission_file = frozen_file(
        manifest.get("commission_report", {}), "verifier commissioning report"
    )
    commission_evidence = validate_commission_report(
        commission_file, prereg_hash, interpretation_hash, verifier_hash
    )

    source_root = require_absolute_existing_dir(
        str(manifest.get("source_root", "")), "source_root"
    )
    expected_commit = str(manifest.get("source_commit", ""))
    if not re.fullmatch(r"[0-9a-fA-F]{40}", expected_commit):
        raise Unmeasured("source_commit is not a full 40-digit commit")
    binary = frozen_file(manifest.get("binary", {}), "candidate binary")
    instruments = parse_instruments(manifest.get("instruments"))
    source_manifest = frozen_file(
        manifest.get("source_manifest", {}), "source snapshot manifest"
    )
    source_evidence = verify_source_manifest(
        source_manifest, source_root, expected_commit, instruments["hook"].sha256
    )
    try:
        binary_common = os.path.commonpath(
            [os.path.normcase(str(source_root)), os.path.normcase(str(binary.path))]
        )
    except ValueError as error:
        raise Unmeasured("candidate binary is outside the source snapshot volume") from error
    if os.path.normcase(binary_common) != os.path.normcase(str(source_root)):
        raise Unmeasured("candidate binary is outside the source snapshot")

    prereg_captures = {
        item["name"]: item for item in prereg.get("scope", {}).get("captures", [])
    }
    raw_captures = manifest.get("captures")
    if not isinstance(raw_captures, list) or not raw_captures:
        raise Unmeasured("manifest captures must be a non-empty list")
    if {item.get("name") for item in raw_captures} != set(prereg_captures):
        raise Unmeasured("manifest capture set differs from preregistration")

    capture_results: list[dict[str, Any]] = []
    artifact_root = report_path.parent / (report_path.stem + "-artifacts")
    if artifact_root.exists():
        raise Unmeasured(f"verifier output directory already exists: {artifact_root}")
    artifact_root.mkdir(parents=True)
    for item in raw_captures:
        if not isinstance(item, Mapping):
            raise Unmeasured("capture entry must be an object")
        name = str(item["name"])
        registered = prereg_captures[name]
        input_dir = require_absolute_existing_dir(str(item.get("input_dir", "")), f"{name} input")
        if os.path.normcase(str(input_dir)) != os.path.normcase(
            str(Path(registered["input"]).resolve())
        ):
            raise Unmeasured(f"{name}: input directory differs from preregistration")
        warpmap_file = frozen_file(item.get("warpmap", {}), f"{name} warpmap")
        if warpmap_file.sha256 != str(registered["map_sha256"]).upper():
            raise Unmeasured(f"{name}: warpmap hash differs from preregistration")
        state_dir = require_absolute_existing_dir(str(item.get("state_dir", "")), f"{name} state")
        output_file = frozen_file(item.get("output_tiff", {}), f"{name} output TIFF")
        raw_checker_artifacts = item.get("checker_artifacts")
        if not isinstance(raw_checker_artifacts, Mapping) or set(
            raw_checker_artifacts
        ) != REQUIRED_CHECKER_ARTIFACTS:
            raise Unmeasured(
                f"{name}: checker_artifacts must contain exactly "
                f"{sorted(REQUIRED_CHECKER_ARTIFACTS)}"
            )
        checker_artifacts = {
            label: frozen_file(value, f"{name} checker artifact {label}")
            for label, value in raw_checker_artifacts.items()
        }
        numpy_labels = {
            "m8_r_violations",
            "pre_lower",
            "pre_upper",
            "projected_lower",
            "projected_upper",
            "valid_contributors",
            "violations",
        }
        for label, file in checker_artifacts.items():
            expected_suffix = ".npy" if label in numpy_labels else ".json"
            if file.path.suffix.lower() != expected_suffix:
                raise Unmeasured(
                    f"{name}: checker artifact {label} must be {expected_suffix}"
                )
        if len({file.path for file in checker_artifacts.values()}) != len(
            checker_artifacts
        ):
            raise Unmeasured(f"{name}: checker artifact paths must be distinct")
        for label, file in checker_artifacts.items():
            try:
                common = os.path.commonpath(
                    [os.path.normcase(str(state_dir)), os.path.normcase(str(file.path))]
                )
            except ValueError as error:
                raise Unmeasured(
                    f"{name}: checker artifact {label} is outside the state volume"
                ) from error
            if os.path.normcase(common) != os.path.normcase(str(state_dir)):
                raise Unmeasured(
                    f"{name}: checker artifact {label} is outside state directory"
                )
        capture_results.append(
            verify_capture(
                name,
                input_dir,
                warpmap_file,
                state_dir,
                output_file,
                artifact_root / name,
                chunk_rows,
                checker_artifacts,
            )
        )

    aggregate_r_denominator = sum(item["m8_r"]["denominator"] for item in capture_results)
    aggregate_r_violations = sum(item["m8_r"]["violations"] for item in capture_results)
    aggregate_o_denominator = sum(item["m8_o"]["denominator"] for item in capture_results)
    aggregate_o_violations = sum(item["m8_o"]["violations"] for item in capture_results)
    evidence_verdict = (
        "PASS"
        if aggregate_r_violations == 0 and aggregate_o_violations == 0
        else "FAIL"
    )
    result = {
        "protocol": VERIFIER_PROTOCOL,
        "status": evidence_verdict,
        "decision_rule": "PASS iff aggregate M8-R V=0 and every capture and aggregate M8-O V=0",
        "manifest": {"path": str(manifest_path), "sha256": manifest_file_hash},
        "preregistration": {"path": str(prereg_file), "sha256": prereg_hash},
        "prospective_interpretation": {
            "path": str(interpretation_path),
            "sha256": interpretation_hash,
            "commit": INTERPRETATION_COMMIT,
        },
        "commissioning": commission_evidence,
        "verifier": {"path": str(verifier_path), "sha256": verifier_hash},
        "source_commit": expected_commit,
        "source_snapshot": source_evidence,
        "binary": {"path": str(binary.path), "sha256": binary.sha256},
        "instruments": {
            name: {"path": str(file.path), "sha256": file.sha256}
            for name, file in instruments.items()
        },
        "independence": verify_independence(Path(__file__).resolve()),
        "captures": capture_results,
        "aggregate": {
            "m8_r": {
                "denominator": aggregate_r_denominator,
                "violations": aggregate_r_violations,
            },
            "m8_o": {
                "denominator": aggregate_o_denominator,
                "violations": aggregate_o_violations,
            },
        },
    }
    json_dump(report_path, result)
    return (0 if evidence_verdict == "PASS" else 1), result


def bits_f64(value: float) -> str:
    return struct.pack(">d", value).hex()


def write_synthetic_warpmap(path: Path) -> None:
    one = bits_f64(1.0)
    zero = bits_f64(0.0)
    path.write_text(
        "\n".join(
            [
                "strehl-warpmap 1",
                "stack-name verifier-synthetic",
                "stack-digest 0000000000000000",
                "frames 1",
                "plane 16x16",
                "reference 0",
                "strategy verifier",
                "resampler clamped-catmull",
                f"0 placed {one} {zero} {zero} {zero}",
                "end 1",
                "",
            ]
        ),
        encoding="utf-8",
    )


def synthetic_validity(
    full_width: int,
    full_height: int,
    site_x: int,
    site_y: int,
    source_width: int,
    source_height: int,
) -> np.ndarray:
    x = np.arange(full_width, dtype=np.float64)[None, :] + 0.5 * site_x
    y = np.arange(full_height, dtype=np.float64)[:, None] + 0.5 * site_y
    sx = 2.0 * x
    sy = 2.0 * y
    return (
        (sx >= 1.5)
        & (sy >= 1.5)
        & (sx <= source_width - 2.5)
        & (sy <= source_height - 2.5)
    )


def write_synthetic_trace(
    block_dir: Path,
    frame_path: Path,
    site_x: int,
    site_y: int,
    crop: tuple[int, int, int, int],
    crop_override: tuple[int, int, int, int] | None = None,
) -> Path:
    source_width = source_height = 32
    full_width = full_height = 16
    crop_x, crop_y, compact_width, compact_height = crop_override or crop
    channel = SITE_CHANNEL[(site_x, site_y)]
    source = np.full((source_height, source_width), np.float32(2000.0), dtype="<f4")
    valid = synthetic_validity(
        full_width, full_height, site_x, site_y, source_width, source_height
    )
    gathered = np.full((full_height, full_width), np.float32(np.nan), dtype="<f4")
    gathered[valid] = np.float32(2000.0)
    frame_bytes = str(frame_path.resolve()).encode("utf-8")
    source_sha = bytes.fromhex(sha256_file(frame_path))
    header = TRACE_HEADER.pack(
        TRACE_MAGIC,
        TRACE_VERSION,
        2,
        0,
        source_width,
        source_height,
        full_width,
        full_height,
        compact_width,
        compact_height,
        crop_x,
        crop_y,
        site_x,
        site_y,
        channel,
        ARITHMETIC_CONTRACT,
        1.0,
        0.0,
        0.0,
        0.0,
        8.0,
        8.0,
        0.0,
        1000.0,
        1.0,
        1.0,
        source_sha,
        len(frame_bytes),
    )
    payload = header + frame_bytes + source.tobytes() + gathered.tobytes()
    path_hash = hashlib.sha256(frame_bytes).hexdigest()
    content_hash = hashlib.sha256(payload).hexdigest()
    filename = (
        f"m8-trace-v3-p1-f00000000-{path_hash}-s{site_x}{site_y}-"
        f"{content_hash}.m8site"
    )
    path = block_dir / filename
    path.write_bytes(payload)
    return path


def write_synthetic_evidence(
    root: Path,
    encoded_r: int,
    crop_override: tuple[int, int, int, int] | None = None,
) -> tuple[Path, Path, Path, Path]:
    input_dir = root / "i"
    state = root
    blocks = state / "blocks"
    input_dir.mkdir(parents=True, exist_ok=True)
    blocks.mkdir(parents=True, exist_ok=True)
    frame = input_dir / "frame000.ARW"
    frame.write_bytes(b"M136 independent verifier synthetic source\n")
    warpmap = root / "m.txt"
    write_synthetic_warpmap(warpmap)
    parsed = parse_warpmap(warpmap)
    crop_x, crop_y, width, height, _ = reconstruct_crop(parsed)
    crop = (crop_x, crop_y, width, height)
    for site in SITE_CHANNEL:
        write_synthetic_trace(blocks, frame, *site, crop, crop_override)
    image = np.full((height, width, 3), U16_MAX, dtype=np.uint16)
    image[3, 2, 0] = encoded_r
    output = root / "o.tif"
    tifffile.imwrite(
        output,
        image,
        photometric="rgb",
        description="Linear camera-native RGB. This is the measurement output.",
    )
    return input_dir, state, warpmap, output


def replace_unique_line(path: Path, old_line: str, new_line: str) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    count = sum(line == old_line for line in lines)
    if count != 1:
        raise RuntimeError(
            f"commissioning plant anchor must occur exactly once; "
            f"{old_line!r} occurred {count} times"
        )
    before = sha256_file(path)
    replaced = [new_line if line == old_line else line for line in lines]
    path.write_text("\n".join(replaced) + "\n", encoding="utf-8")
    after = sha256_file(path)
    if before == after or new_line not in replaced or old_line in replaced:
        raise RuntimeError("commissioning plant did not land")
    return {
        "old_line": old_line,
        "new_line": new_line,
        "occurrences": count,
        "sha256_before": before,
        "sha256_after": after,
    }


def direct_numeric_controls(prereg: Mapping[str, Any]) -> dict[str, Any]:
    cases = prereg["commissioning"]["m8_o_numeric_cases"]
    observed: dict[str, Any] = {}
    for name, case in cases.items():
        low = min(max(float(case["lo"]) - float(case["tau"]), 0.0), 1.0)
        high = min(max(float(case["hi"]) + float(case["tau"]), 0.0), 1.0)
        value = int(case["encoded"]) / float(U16_MAX)
        violation = value < low - FINAL_Q or value > high + FINAL_Q
        expected = int(case["expected_violations"])
        if int(violation) != expected:
            raise RuntimeError(
                f"numeric control {name} observed {int(violation)}, expected {expected}"
            )
        observed[name] = {
            "L": low,
            "H": high,
            "encoded": int(case["encoded"]),
            "observed_violations": int(violation),
            "expected_violations": expected,
        }
    return observed


def quantizer_control(prereg: Mapping[str, Any]) -> dict[str, Any]:
    case = prereg["commissioning"]["intermediate_quantizer_case"]
    z = np.asarray([[np.float32(case["lo"])]], dtype=np.float32)
    black_lo, black_hi, u_lo, u_hi = intermediate_interval(
        z, z, np.float32(case["g"]), np.float32(case["b"])
    )
    pre_lo, pre_hi, projected_lo, projected_hi = output_interval(
        black_lo, black_hi, np.float32(case["G"]), np.float32(case["R"])
    )
    if int(u_lo[0, 0]) != int(case["expected_intermediate_u16"]) or not np.array_equal(
        u_lo, u_hi
    ):
        raise RuntimeError("intermediate-u16 commissioning value disagrees")
    expected_pre = float(case["expected_pre_final"])
    if not (float(pre_lo[0, 0]) <= expected_pre <= float(pre_hi[0, 0])):
        raise RuntimeError("pre-final quantizer value is outside verifier interval")

    def violation(encoded: int) -> bool:
        value = encoded / float(U16_MAX)
        return bool(
            value < float(projected_lo[0, 0]) - FINAL_Q
            or value > float(projected_hi[0, 0]) + FINAL_Q
        )

    green = violation(int(case["green_encoded"]))
    red = violation(int(case["red_encoded"]))
    if green or not red:
        raise RuntimeError(
            f"quantizer boundary control failed: green={green}, red={red}"
        )
    return {
        "intermediate_u16": int(u_lo[0, 0]),
        "pre_final_interval": [float(pre_lo[0, 0]), float(pre_hi[0, 0])],
        "green_violation": green,
        "red_violation": red,
    }


def green_pairing_control() -> dict[str, Any]:
    zero = np.asarray([[np.float32(0.0)]])
    one = np.asarray([[np.float32(1.0)]])
    f0 = green_pair_interval(zero, zero, one, one, np.float32(1.0), np.float32(1.0))
    f1 = green_pair_interval(one, one, zero, zero, np.float32(1.0), np.float32(1.0))
    same_frame_lo = min(float(f0[2][0, 0]), float(f1[2][0, 0]))
    same_frame_hi = max(float(f0[3][0, 0]), float(f1[3][0, 0]))
    independently_reduced_lo = 0.5 * (min(0.0, 1.0) + min(1.0, 0.0))
    independently_reduced_hi = 0.5 * (max(0.0, 1.0) + max(1.0, 0.0))
    output = 0.0
    same_frame_violation = output < same_frame_lo - FINAL_Q
    wrong_rule_violation = output < independently_reduced_lo - FINAL_Q
    if not same_frame_violation or wrong_rule_violation:
        raise RuntimeError("green-pairing control does not distinguish the two reductions")
    return {
        "same_frame_interval": [same_frame_lo, same_frame_hi],
        "independent_site_interval": [
            independently_reduced_lo,
            independently_reduced_hi,
        ],
        "encoded_output": 0,
        "same_frame_violation": same_frame_violation,
        "independent_site_violation": wrong_rule_violation,
    }


def interval_containment_control() -> dict[str, Any]:
    rng = np.random.default_rng(136)
    cases = 4096
    samples = 0
    for index in range(cases):
        site_gain = np.float32(10.0 ** rng.uniform(-0.3, 0.3))
        black = np.float32(rng.uniform(0.0, 1024.0))
        output_gain = np.float32(10.0 ** rng.uniform(-0.3, 0.3))
        sensor_range = np.float32(rng.uniform(1000.0, 65000.0))
        center = np.float32(rng.uniform(-1000.0, 70000.0))
        span = np.float32(rng.uniform(0.0, 8.0))
        lo = np.asarray([[np.float32(center - span)]], dtype=np.float32)
        hi = np.asarray([[np.float32(center + span)]], dtype=np.float32)
        black_lo, black_hi, _, _ = intermediate_interval(
            lo, hi, site_gain, black
        )
        _, _, projected_lo, projected_hi = output_interval(
            black_lo, black_hi, output_gain, sensor_range
        )
        candidates = np.asarray(
            np.linspace(float(lo[0, 0]), float(hi[0, 0]), 17), dtype=np.float32
        )
        candidates = np.unique(
            np.concatenate(
                [
                    candidates,
                    np.asarray([lo[0, 0], hi[0, 0]], dtype=np.float32),
                ]
            )
        )
        inverse_gain = np.float32(np.float32(1.0) / site_gain)
        for z in candidates:
            restored = np.float32(np.float32(z * inverse_gain) + black)
            rounded = (
                math.floor(float(restored) + 0.5)
                if restored >= 0
                else math.ceil(float(restored) - 0.5)
            )
            encoded = np.uint16(min(max(rounded, 0), U16_MAX))
            black_removed = np.float32(
                max(np.float32(np.float32(encoded) - black), np.float32(0.0))
            )
            pre = np.float32(np.float32(black_removed * output_gain) / sensor_range)
            projected = np.float32(min(pre, np.float32(1.0)))
            if not (
                float(projected_lo[0, 0])
                <= float(projected)
                <= float(projected_hi[0, 0])
            ):
                raise RuntimeError(
                    f"outward interval missed scalar case {index}: "
                    f"{projected_lo[0,0]} <= {projected} <= {projected_hi[0,0]}"
                )
            samples += 1
    return {
        "seed": 136,
        "cases": cases,
        "scalar_samples": samples,
        "misses": 0,
    }


def commission(prereg_path: Path, report_path: Path, work_dir: Path) -> dict[str, Any]:
    if work_dir.exists():
        raise RuntimeError(f"refusing to reuse commissioning work directory: {work_dir}")
    work_dir.mkdir(parents=True)
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if sha256_file(prereg_path) != PREREG_SHA256:
        raise RuntimeError("commissioning preregistration differs from the frozen bytes")
    interpretation_path = Path(__file__).with_name("prospective-interpretations.md")
    if sha256_file(interpretation_path) != INTERPRETATION_SHA256:
        raise RuntimeError("commissioning interpretation differs from the pre-target ruling")
    report: dict[str, Any] = {
        "protocol": VERIFIER_PROTOCOL,
        "commissioning": "both directions",
        "verifier": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "preregistration": {
            "path": str(prereg_path.resolve()),
            "sha256": sha256_file(prereg_path),
        },
        "prospective_interpretation": {
            "path": str(interpretation_path.resolve()),
            "sha256": sha256_file(interpretation_path),
            "commit": INTERPRETATION_COMMIT,
        },
        "independence": verify_independence(Path(__file__).resolve()),
        "numeric_cases": direct_numeric_controls(prereg),
        "quantizer_case": quantizer_control(prereg),
        "green_pairing_case": green_pairing_control(),
        "interval_containment": interval_containment_control(),
    }
    try:
        recipe = work_dir / "recipe.json"
        recipe.write_text(
            "{\n"
            '  "encoded_r": 65535,\n'
            '  "plant_x": 2,\n'
            '  "plant_y": 3\n'
            "}\n",
            encoding="utf-8",
        )
        input_dir, state, warpmap, output = write_synthetic_evidence(work_dir, U16_MAX)

        def run_case(name: str, encoded: int) -> dict[str, Any]:
            image = tifffile.imread(output)
            image[3, 2, 0] = encoded
            tifffile.imwrite(
                output,
                image,
                photometric="rgb",
                description="Linear camera-native RGB. This is the measurement output.",
            )
            artifact_dir = work_dir / f"verified-{name}"
            result = verify_capture(
                "commission",
                input_dir.resolve(),
                FrozenFile(warpmap.resolve(), sha256_file(warpmap)),
                state.resolve(),
                FrozenFile(output.resolve(), sha256_file(output)),
                artifact_dir,
                4,
                None,
            )
            rows = np.load(artifact_dir / "m8-o-violations.npy", allow_pickle=False)
            return {
                "status": "PASS"
                if result["m8_r"]["violations"] == 0
                and result["m8_o"]["violations"] == 0
                else "FAIL",
                "m8_r_violations": result["m8_r"]["violations"],
                "m8_o_violations": result["m8_o"]["violations"],
                "violations": [
                    {
                        "x": int(row["x"]),
                        "y": int(row["y"]),
                        "channel": str(row["channel"]),
                        "direction": int(row["direction"]),
                        "encoded": int(row["encoded"]),
                    }
                    for row in rows
                ],
                "output_sha256": sha256_file(output),
            }

        baseline = run_case("baseline", U16_MAX)
        if baseline["status"] != "PASS":
            raise RuntimeError("synthetic high-rail baseline did not pass")

        defect_plant = replace_unique_line(
            recipe, '  "encoded_r": 65535,', '  "encoded_r": 65534,'
        )
        defect_recipe = json.loads(recipe.read_text(encoding="utf-8"))
        defect = run_case("defect", int(defect_recipe["encoded_r"]))
        if defect["status"] != "FAIL" or defect["m8_o_violations"] != 1:
            raise RuntimeError("planted degradation was not charged exactly once")
        if defect["violations"] != [
            {"x": 2, "y": 3, "channel": "R", "direction": -1, "encoded": 65534}
        ]:
            raise RuntimeError(f"planted degradation landed at wrong verdict row: {defect}")

        improvement_plant = replace_unique_line(
            recipe, '  "encoded_r": 65534,', '  "encoded_r": 65535,'
        )
        improvement_recipe = json.loads(recipe.read_text(encoding="utf-8"))
        improvement = run_case("improvement", int(improvement_recipe["encoded_r"]))
        if improvement["status"] != "PASS" or improvement["m8_o_violations"] != 0:
            raise RuntimeError("planted improvement was misreported")
        if baseline["output_sha256"] == defect["output_sha256"]:
            raise RuntimeError("degradation plant did not change the TIFF hash")
        if defect["output_sha256"] == improvement["output_sha256"]:
            raise RuntimeError("improvement plant did not change the TIFF hash")

        held = next((state / "blocks").glob("*.m8site"))
        absent = work_dir / "held.m8site"
        held.rename(absent)
        missing_message = ""
        try:
            verify_capture(
                "commission-missing",
                input_dir.resolve(),
                FrozenFile(warpmap.resolve(), sha256_file(warpmap)),
                state.resolve(),
                FrozenFile(output.resolve(), sha256_file(output)),
                work_dir / "verified-missing",
                4,
                None,
            )
        except Unmeasured as error:
            missing_message = str(error)
        finally:
            absent.rename(held)
        if "missing=" not in missing_message:
            raise RuntimeError("missing frame/site evidence did not report UNMEASURED")

        original = next((state / "blocks").glob("*.m8site"))
        original_match = TRACE_NAME.fullmatch(original.name)
        assert original_match is not None
        original_bytes = original.read_bytes()
        version_two = bytearray(original_bytes)
        version_two[8:12] = struct.pack("<I", 2)
        version_two_hash = hashlib.sha256(version_two).hexdigest()
        version_two_name = (
            original.name[: original_match.start("content_hash")]
            + version_two_hash
            + original.name[original_match.end("content_hash") :]
        )
        original_held = work_dir / "v3-held.m8site"
        original.rename(original_held)
        version_two_path = state / "blocks" / version_two_name
        version_two_path.write_bytes(version_two)
        version_message = ""
        try:
            verify_capture(
                "commission-v2",
                input_dir.resolve(),
                FrozenFile(warpmap.resolve(), sha256_file(warpmap)),
                state.resolve(),
                FrozenFile(output.resolve(), sha256_file(output)),
                work_dir / "verified-v2",
                4,
                None,
            )
        except Unmeasured as error:
            version_message = str(error)
        finally:
            version_two_path.unlink(missing_ok=True)
            original_held.rename(original)
        if "requires trace-v3" not in version_message:
            raise RuntimeError("trace-v2 evidence did not report UNMEASURED")

        alternate_frame = input_dir / "frame-alt.bin"
        alternate_frame.write_bytes(
            b"M136 independent verifier alternate synthetic source\n"
        )
        parsed_map = parse_warpmap(warpmap)
        duplicate_crop = reconstruct_crop(parsed_map)[:4]
        duplicate_path = write_synthetic_trace(
            state / "blocks",
            alternate_frame,
            0,
            0,
            duplicate_crop,
        )
        duplicate_message = ""
        try:
            verify_capture(
                "commission-duplicate",
                input_dir.resolve(),
                FrozenFile(warpmap.resolve(), sha256_file(warpmap)),
                state.resolve(),
                FrozenFile(output.resolve(), sha256_file(output)),
                work_dir / "verified-duplicate",
                4,
                None,
            )
        except Unmeasured as error:
            duplicate_message = str(error)
        finally:
            duplicate_path.unlink(missing_ok=True)
            alternate_frame.unlink(missing_ok=True)
        if "duplicate trace-v3 frame/site" not in duplicate_message:
            raise RuntimeError("duplicate frame/site evidence did not report UNMEASURED")

        producer_hull = state / "producer-supplied-hull.npy"
        np.save(producer_hull, np.asarray([[-12345.0]], dtype=np.float32))
        ignored_hull = run_case("producer-hull-ignored", U16_MAX)
        producer_hull.unlink()
        if ignored_hull["status"] != "PASS":
            raise RuntimeError("producer-supplied hull contaminated independent result")

        wrong_crop_root = work_dir / "c"
        wrong_input, wrong_state, wrong_map, wrong_output = write_synthetic_evidence(
            wrong_crop_root, U16_MAX, crop_override=(0, 0, 9, 9)
        )
        crop_message = ""
        try:
            verify_capture(
                "commission-crop",
                wrong_input.resolve(),
                FrozenFile(wrong_map.resolve(), sha256_file(wrong_map)),
                wrong_state.resolve(),
                FrozenFile(wrong_output.resolve(), sha256_file(wrong_output)),
                work_dir / "verified-wrong-crop",
                4,
                None,
            )
        except Unmeasured as error:
            crop_message = str(error)
        if "trace crop" not in crop_message:
            raise RuntimeError("wrong crop origin did not report UNMEASURED")

        report.update(
            {
                "baseline_green": baseline,
                "degradation_plant": {
                    "landed": defect_plant,
                    "result": defect,
                },
                "improvement_plant": {
                    "landed": improvement_plant,
                    "result": improvement,
                },
                "fail_closed": {
                    "missing_frame_site": missing_message,
                    "duplicate_frame_site": duplicate_message,
                    "trace_v2": version_message,
                    "wrong_crop_origin": crop_message,
                    "producer_supplied_hull_ignored": ignored_hull["status"] == "PASS",
                },
                "status": "PASS",
            }
        )
        json_dump(report_path, report)
        return report
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    commission_parser = subparsers.add_parser("commission")
    commission_parser.add_argument(
        "--preregistration",
        type=Path,
        default=Path(__file__).with_name("clamped-m8o-preregistration.json"),
    )
    commission_parser.add_argument(
        "--report",
        type=Path,
        default=Path(__file__).with_name("verifier-commission.json"),
    )
    commission_parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(__file__).with_name("w"),
    )

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser.add_argument("--report", type=Path, required=True)
    verify_parser.add_argument("--chunk-rows", type=int, default=64)

    args = parser.parse_args(argv)
    try:
        if args.command == "commission":
            report = commission(
                args.preregistration.resolve(),
                args.report.resolve(),
                args.work_dir.resolve(),
            )
            print(json.dumps({"status": report["status"], "report": str(args.report.resolve())}))
            return 0
        if args.chunk_rows <= 0:
            raise Unmeasured("--chunk-rows must be positive")
        code, result = verify_manifest(
            args.manifest.resolve(), args.report.resolve(), args.chunk_rows
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "m8_r_violations": result["aggregate"]["m8_r"]["violations"],
                    "m8_o_violations": result["aggregate"]["m8_o"]["violations"],
                    "report": str(args.report.resolve()),
                },
                sort_keys=True,
            )
        )
        return code
    except Disagreement as error:
        failure = {
            "protocol": VERIFIER_PROTOCOL,
            "status": "DISAGREEMENT",
            "error": str(error),
        }
        if hasattr(args, "report"):
            json_dump(args.report.resolve(), failure)
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        return 3
    except (Unmeasured, OSError, ValueError, KeyError, RuntimeError) as error:
        failure = {
            "protocol": VERIFIER_PROTOCOL,
            "status": "UNMEASURED",
            "error": str(error),
        }
        if hasattr(args, "report"):
            json_dump(args.report.resolve(), failure)
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
