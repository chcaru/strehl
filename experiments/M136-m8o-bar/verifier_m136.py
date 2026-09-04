#!/usr/bin/env python3
"""Independent evidence verifier for the preregistered M136 M8-O census.

This file deliberately does not import checker_m136.py or any Strehl sampler,
hull, crop, or warp implementation.  It parses trace-v3 blocks, warp maps, and
the final TIFF directly and recomputes the certificate.

Production verification consumes one JSON manifest with schema
``m136-verifier-input-v1`` and protocol ``M136 independent verifier v1``.  It
freezes the preregistration, both commissioning suites, fixture, source
snapshot/patch, pre-target instrument freeze, candidate binary, and four
instrument files.  Each capture supplies ``input_dir``, before/after input
fingerprints, ``warpmap``, separate ``trace_state`` and ``checker_state``,
``output_tiff``, render provenance, and every labeled ``checker_artifacts``
entry named by ``REQUIRED_CHECKER_ARTIFACTS`` below.  All paths are absolute
and every frozen-file object contains ``path`` and uppercase ``sha256``.

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
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import tifffile


PROTOCOL = "M136 clamped-Catmull-Rom representable-domain M8-O v1"
PREREG_CANONICAL_SHA256 = (
    "97E4B3FF9F1AFAE98E416C92E3D62CCD7F5C5A2C79D45C51343B2A5D96AD770D"
)
INTERPRETATION_COMMIT = "746cc38a"
INTERPRETATION_CANONICAL_SHA256 = (
    "DBCCCF505D91FB86385D44BE3293A280A54ACE4C0C416945F23CFDFE355A203C"
)
MANIFEST_SCHEMA = "m136-verifier-input-v1"
SOURCE_MANIFEST_SCHEMA = "m136-source-snapshot-v1"
M130_SOURCE_COMMIT = "248178b921f98ec1f13ea4c07d30fa68ace787a0"
M130_SOURCE_TREE = {
    "files": 9292,
    "bytes": 325020512,
    "manifest_sha256": "0F0EFD13D5EC0BB8825EBFEE40F7DCD93D7C99B804582A142F59685288CBF625",
}
APPROVED_CANDIDATE_SOURCE_TREE = {
    "files": 9293,
    "bytes": 325053057,
    "manifest_sha256": "CE83FD38466856BF0C526AF9137AEEE8C7670E3D886A13A8D896155D32E92E12",
}
BUILD_OUTPUT_DIRECTORIES = {"target-m136", "target-m136-tests"}
SOURCE_MANIFEST_FIELDS = {
    "schema",
    "schema_version",
    "source_commit",
    "source_root",
    "file_count",
    "total_bytes",
    "tree_sha256",
    "files",
}
SOURCE_PATCH_FIELDS = {
    "schema",
    "schema_version",
    "protocol",
    "source_commit",
    "source_root",
    "repository",
    "source",
    "destination",
    "manifest_algorithm",
    "source_tree",
    "patched_tree",
    "frozen_before_sha256",
    "after_sha256",
    "changed_files",
    "changed_paths",
    "trace_hook",
    "patch_script",
    "candidate_divergences",
    "trace_scope",
}
APPROVED_SOURCE_PATCH_PATHS = {
    "crates/strehl-core/src/align.rs",
    "crates/strehl-core/src/restore.rs",
    "crates/strehl-core/src/warpmap.rs",
    "crates/strehl-cli/src/align_cmd.rs",
    "crates/strehl-cli/src/image_out.rs",
    "crates/strehl-cli/src/m8_trace_v3.rs",
    "crates/strehl-cli/src/main.rs",
    "crates/strehl-cli/src/merge_cmd.rs",
}
VERIFIER_PROTOCOL = "M136 independent verifier v1"
TRACE_MAGIC = b"M8SITE03"
TRACE_VERSION = 3
ARITHMETIC_CONTRACT = 1
COMMISSION_FREEZE_SHA256 = "00" * 32
TRACE_HEADER = struct.Struct("<8s15I6d4f32s32sI")
TRACE_NAME = re.compile(
    r"^m8-trace-v3-p1-f(?P<frame>\d{8})-"
    r"(?P<path_hash>[0-9a-f]{64})-s(?P<sx>[01])(?P<sy>[01])-"
    r"(?P<content_hash>[0-9a-f]{64})\.m8site$"
)
MAX_PATH_BYTES = 1 << 20
U16_MAX = 65535
FINAL_Q = 1.0 / 131070.0
COVER_MARGIN = 3.0
CHANNEL_NAMES = ("R", "G", "B")
SITE_CHANNEL = {(0, 0): 0, (1, 0): 1, (0, 1): 1, (1, 1): 2}
SITE_NAMES = {(0, 0): "R", (1, 0): "G1", (0, 1): "G2", (1, 1): "B"}
SITE_BY_NAME = {name: site for site, name in SITE_NAMES.items()}
GREEN_SITES = ((1, 0), (0, 1))
GREEN_RULE = "same-frame-before-reduction"
GREEN_RULE_STATUS = "ADOPTED_PROSPECTIVELY_AT_746cc38a"
FIXTURE_REPRESENTATION = (
    "fixture-only identity: P_fixture(z)=z; F_fixture(z)=clamp(z,0,1)"
)
CHECKER_PROTOCOL = "M136 independent checker"
CHECKER_VERSION = 1
BUILD_ENVIRONMENT_KEYS = {
    "CARGO_BUILD_JOBS",
    "CARGO_INCREMENTAL",
    "RUSTC",
    "RUSTFLAGS",
    "SOURCE_DATE_EPOCH",
    "STREHL_BUILD_ID",
}
BUILD_RECEIPT_FIELDS = {
    "schema",
    "schema_version",
    "protocol",
    "source_commit",
    "source_root",
    "source_manifest",
    "source_patch",
    "candidate_binary",
    "cargo",
    "rustc",
    "build_log",
    "environment",
    "command",
    "started_utc",
    "completed_utc",
    "exit_code",
    "cargo_version",
    "rustc_version",
}
REQUIRED_INSTRUMENTS = {"checker", "fixture", "hook", "runner"}
VERIFIER_MANIFEST_FIELDS = {
    "schema",
    "protocol",
    "created_utc",
    "preregistration",
    "commission_report",
    "source_root",
    "source_commit",
    "source_manifest",
    "source_patch",
    "build_receipt",
    "binary",
    "instruments",
    "checker_fixture_manifest",
    "checker_commission_artifacts",
    "instrument_freeze",
    "captures",
}
CAPTURE_MANIFEST_FIELDS = {
    "name",
    "input_dir",
    "input_fingerprint_before",
    "input_fingerprint_after",
    "warpmap",
    "trace_state",
    "checker_state",
    "output_tiff",
    "render_provenance",
    "checker_artifacts",
}


def measurement_description(instrument_freeze_sha256: str) -> str:
    return (
        "Linear camera-native RGB. This is the measurement output. "
        "M136 instrument freeze sha256: "
        f"{instrument_freeze_sha256.upper()}."
    )


INSTRUMENT_NAMES = {
    "checker": "checker_m136.py",
    "fixture": "fixture_m136.py",
    "hook": "m8_trace_v3.rs",
    "runner": "run-clamped-m8o.ps1",
}
REQUIRED_CHECKER_ARTIFACTS = {
    "meta",
    "m8_r",
    "m8_r_block_manifest",
    "m8_r_violations",
    "pre_lower",
    "pre_upper",
    "projected_lower",
    "projected_upper",
    "valid_contributors",
    "lower_frame_witness",
    "upper_frame_witness",
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
    instrument_freeze_sha256: str
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


def sha256_canonical_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return sha256_bytes(text.encode("utf-8"))


def m136_build_id(source_commit: str, source_manifest_sha256: str) -> str:
    return f"m136-{source_commit[:12]}-{source_manifest_sha256[:12].lower()}"


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(path.name + ".new")
    staging.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(staging, path)


def require_absolute_existing_file(raw: str, label: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        raise Unmeasured(f"{label} path is not absolute: {raw}")
    if not path.is_file():
        raise Unmeasured(f"{label} file is absent: {path}")
    if path.is_symlink():
        raise Unmeasured(f"{label} must not be a symlink: {path}")
    return path.resolve()


def require_absolute_existing_dir(raw: str, label: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        raise Unmeasured(f"{label} path is not absolute: {raw}")
    if not path.is_dir():
        raise Unmeasured(f"{label} directory is absent: {path}")
    return path.resolve()


def require_under(path: Path, root: Path, label: str) -> None:
    try:
        common = os.path.commonpath(
            [os.path.normcase(str(root)), os.path.normcase(str(path))]
        )
    except ValueError as error:
        raise Unmeasured(f"{label} is outside the required output volume") from error
    if os.path.normcase(common) != os.path.normcase(str(root)):
        raise Unmeasured(f"{label} must remain below {root}")


def path_is_within(path: Path, root: Path) -> bool:
    try:
        common = os.path.commonpath(
            [os.path.normcase(str(root)), os.path.normcase(str(path))]
        )
    except ValueError:
        return False
    return os.path.normcase(common) == os.path.normcase(str(root))


def frozen_file(raw: Mapping[str, Any], label: str) -> FrozenFile:
    if not isinstance(raw, Mapping):
        raise Unmeasured(f"{label} must be an object containing path and sha256")
    path = require_absolute_existing_file(str(raw.get("path", "")), label)
    expected = str(raw.get("sha256", "")).upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected):
        raise Unmeasured(f"{label}.sha256 is not a 64-digit hexadecimal digest")
    observed = sha256_file(path)
    if observed != expected:
        raise Unmeasured(
            f"{label} hash mismatch: expected {expected}, observed {observed}"
        )
    return FrozenFile(path=path, sha256=observed)


def assert_still_frozen(file: FrozenFile, label: str) -> None:
    observed = sha256_file(file.path)
    if observed != file.sha256:
        raise Unmeasured(
            f"{label} changed while being verified: "
            f"expected {file.sha256}, observed {observed}"
        )


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
            instrument_freeze_sha,
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
        if path_bytes == 0 or path_bytes > MAX_PATH_BYTES:
            raise Unmeasured(f"{path.name}: frame-path byte count is invalid")
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
        raise Unmeasured(
            f"{path.name}: source frame is absent or not absolute: {frame_path}"
        )
    frame_path = frame_path.resolve()
    observed_source_hash = source_hash_cache.get(frame_path)
    if observed_source_hash is None:
        observed_source_hash = sha256_file(frame_path)
        source_hash_cache[frame_path] = observed_source_hash
    if observed_source_hash != source_sha.hex().upper():
        raise Unmeasured(f"{path.name}: source frame SHA-256 mismatch")
    if (
        min(
            source_width,
            source_height,
            full_width,
            full_height,
            compact_width,
            compact_height,
        )
        <= 0
    ):
        raise Unmeasured(f"{path.name}: dimensions must be positive")
    if crop_x + compact_width > full_width or crop_y + compact_height > full_height:
        raise Unmeasured(f"{path.name}: crop rectangle exceeds full plane")
    scalars = (
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
    )
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
        instrument_freeze_sha256=instrument_freeze_sha.hex().upper(),
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
                    raise Unmeasured(
                        f"{path}: non-finite placement at frame {frame_order}"
                    )
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


def source_interval(
    lo: np.ndarray, hi: np.ndarray, tau: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
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
        block.source_width,
        block.source_height,
        block.full_width,
        block.full_height,
        block.compact_width,
        block.compact_height,
        block.crop_x,
        block.crop_y,
        block.cx,
        block.cy,
        block.arithmetic_contract,
        block.instrument_freeze_sha256,
    )


def validate_block_set(
    blocks: Sequence[TraceBlock],
    warpmap: WarpMap,
    input_dir: Path,
) -> dict[int, dict[tuple[int, int], TraceBlock]]:
    placed_orders = {
        index for index, placement in warpmap.placements.items() if placement.placed
    }
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
    keys = [(block.frame_order, block.site) for block in blocks]
    seen: set[tuple[int, tuple[int, int]]] = set()
    for key in keys:
        if key in seen:
            raise Unmeasured(f"duplicate trace-v3 frame/site {key}")
        seen.add(key)
    if seen != expected:
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        raise Unmeasured(
            f"incomplete trace set: missing={missing[:8]}, extra={extra[:8]}"
        )
    for block in blocks:
        if block.frame_order not in placed_orders:
            raise Unmeasured(f"trace exists for unplaced frame {block.frame_order}")
        try:
            common = os.path.commonpath(
                [
                    os.path.normcase(str(input_dir)),
                    os.path.normcase(str(block.frame_path)),
                ]
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
    first = blocks[0]
    geometry = block_geometry_key(first)
    for block in blocks[1:]:
        if block_geometry_key(block) != geometry:
            raise Unmeasured(
                "trace-v3 blocks disagree on geometry or arithmetic contract"
            )
    if first.full_width != warpmap.width or first.full_height != warpmap.height:
        raise Unmeasured("trace full-plane dimensions disagree with warpmap")
    for block in blocks:
        if (
            block.source_width != 2 * block.full_width
            or block.source_height != 2 * block.full_height
        ):
            raise Unmeasured(
                f"{block.path.name}: trace source is not the required "
                "full-resolution 2x gather plane"
            )
    if not same_f64(first.cx, first.full_width * 0.5) or not same_f64(
        first.cy, first.full_height * 0.5
    ):
        raise Unmeasured("trace transform centre differs from full-plane centre")
    for frame_order, sites in grouped.items():
        frame_blocks = list(sites.values())
        reference = frame_blocks[0]
        for block in frame_blocks[1:]:
            if block.frame_path != reference.frame_path:
                raise Unmeasured(
                    f"frame {frame_order}: CFA sites name different source files"
                )
            if block.frame_source_sha256 != reference.frame_source_sha256:
                raise Unmeasured(
                    f"frame {frame_order}: CFA sites disagree on source SHA-256"
                )
            if not same_f32(block.black_level, reference.black_level):
                raise Unmeasured(
                    f"frame {frame_order}: CFA sites disagree on black level"
                )
            if not same_f32(block.sensor_range, reference.sensor_range):
                raise Unmeasured(
                    f"frame {frame_order}: CFA sites disagree on sensor range"
                )
        g1 = sites[GREEN_SITES[0]]
        g2 = sites[GREEN_SITES[1]]
        if not same_f32(g1.output_gain, g2.output_gain):
            raise Unmeasured(f"frame {frame_order}: G1/G2 output gains differ")
    return grouped


def load_tiff(
    path: Path,
    expected_height: int,
    expected_width: int,
    expected_instrument_freeze_sha256: str | None = None,
) -> np.ndarray:
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
        if expected_instrument_freeze_sha256 is not None:
            freeze_marker = (
                "M136 instrument freeze sha256: "
                f"{expected_instrument_freeze_sha256.upper()}."
            )
            if description.count(freeze_marker) != 1:
                raise Unmeasured(
                    f"{path}: TIFF is not bound to the frozen M136 instrument"
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


def verify_m8r_block(
    block: TraceBlock, chunk_rows: int
) -> tuple[dict[str, Any], list[np.ndarray]]:
    source = block.source()
    gathered = block.gathered()
    if not np.all(np.isfinite(source)):
        yy, xx = np.argwhere(~np.isfinite(source))[0]
        raise Unmeasured(
            f"{block.path.name}: non-finite source at ({int(xx)},{int(yy)})"
        )
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
    max_excess = 0.0
    for rows in parts:
        excess = np.where(
            rows["direction"] > 0,
            rows["signed_excess"] - rows["tau"],
            -rows["signed_excess"] - rows["tau"],
        )
        max_excess = max(max_excess, float(np.max(excess, initial=0.0)))
    del source, gathered
    return (
        {
            "frame_order": block.frame_order,
            "site": SITE_NAMES[block.site],
            "eligible_samples": denominator,
            "lower_violation_rows": lower_count,
            "upper_violation_rows": upper_count,
            "violation_rows": lower_count + upper_count,
            "max_excess_over_tolerance": max_excess,
            "trace": block.path.name,
            "trace_sha256": block.file_sha256,
            "source_path": str(block.frame_path),
            "source_sha256": block.frame_source_sha256,
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


def create_array(
    path: Path, dtype: str, shape: tuple[int, ...], fill: float | int
) -> np.memmap:
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
            raise Unmeasured(
                "a coordinate is simultaneously below and above its interval"
            )
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
    rows = np.concatenate(parts) if parts else np.empty(0, dtype=M8O_VIOLATION_DTYPE)
    violations = lower_count + upper_count
    per_channel: dict[str, dict[str, int]] = {}
    for channel in CHANNEL_NAMES:
        selected = rows["channel"] == channel
        per_channel[channel] = {
            "lower_violations": int(
                np.count_nonzero(selected & (rows["direction"] < 0))
            ),
            "upper_violations": int(
                np.count_nonzero(selected & (rows["direction"] > 0))
            ),
            "violations": int(np.count_nonzero(selected)),
        }
    signed = np.asarray(rows["signed_excess"], dtype=np.float64)
    positive = signed[signed > 0.0]
    negative = signed[signed < 0.0]
    max_positive = float(np.max(positive)) if positive.size else 0.0
    min_negative = float(np.min(negative)) if negative.size else 0.0
    max_absolute = float(np.max(np.abs(signed))) if signed.size else 0.0
    return rows, {
        "denominator": int(height * width * 3),
        "lower_violations": lower_count,
        "upper_violations": upper_count,
        "violations": violations,
        "fraction_exact": f"{violations}/{height * width * 3}",
        "fraction": violations / float(height * width * 3),
        "percent": 100.0 * violations / float(height * width * 3),
        "maximum_positive_signed_excess": max_positive,
        "minimum_negative_signed_excess": min_negative,
        "maximum_absolute_signed_excess": max_absolute,
        "maximum_positive_signed_excess_lsb": max_positive * U16_MAX,
        "minimum_negative_signed_excess_lsb": min_negative * U16_MAX,
        "maximum_absolute_signed_excess_lsb": max_absolute * U16_MAX,
        "per_channel": per_channel,
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
            "at_full_rail": int(
                np.count_nonzero((lower_violation | upper_violation) & full)
            ),
            "at_zero_rail": int(
                np.count_nonzero((lower_violation | upper_violation) & zero)
            ),
            "off_rail": int(
                np.count_nonzero((lower_violation | upper_violation) & ~full & ~zero)
            ),
        },
    }


def load_checker_array(
    file: FrozenFile, label: str, shape: tuple[int, ...]
) -> np.ndarray:
    try:
        array = np.load(file.path, mmap_mode="r", allow_pickle=False)
    except Exception as error:
        raise Unmeasured(
            f"{label}: could not open NumPy artifact {file.path}"
        ) from error
    if array.shape == shape:
        return array
    channel_last = (shape[1], shape[2], shape[0])
    if array.shape == channel_last:
        return np.moveaxis(array, -1, 0)
    raise Disagreement(
        f"{label}: checker shape {array.shape} != verifier shape {shape}"
    )


def arrays_equal(a: np.ndarray, b: np.ndarray) -> bool:
    if a.dtype.kind == "f" or b.dtype.kind == "f":
        return bool(np.array_equal(a, b, equal_nan=True))
    return bool(np.array_equal(a, b))


def numpy_dtype_metadata(array: np.ndarray) -> Any:
    if array.dtype.names:
        return json.loads(json.dumps(array.dtype.descr))
    return array.dtype.str


def checker_json(files: Mapping[str, FrozenFile], label: str) -> Mapping[str, Any]:
    try:
        document = json.loads(files[label].path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(
            f"{label}: invalid JSON artifact {files[label].path}"
        ) from error
    if not isinstance(document, Mapping):
        raise Unmeasured(f"{label}: JSON root must be an object")
    return document


def require_checker_identity(
    document: Mapping[str, Any], schema: str, label: str
) -> None:
    if document.get("schema") != schema or document.get("schema_version") != 1:
        raise Unmeasured(f"{label}: unsupported checker schema/version")


def require_frozen_reference(raw: Any, expected: FrozenFile, label: str) -> None:
    if not isinstance(raw, Mapping):
        raise Unmeasured(f"{label}: expected a path/hash object")
    try:
        actual_path = Path(str(raw["path"])).resolve(strict=True)
    except Exception as error:
        raise Unmeasured(f"{label}: referenced path is absent") from error
    if actual_path != expected.path or raw.get("sha256") != expected.sha256:
        raise Disagreement(f"{label}: path/hash does not identify frozen evidence")


def parse_checker_command(
    raw: Any,
    *,
    checker: FrozenFile,
    capture: str,
    input_dir: Path,
    trace_state: Path,
    warpmap: FrozenFile,
    output_tiff: FrozenFile,
    checker_state: Path,
    preregistration: FrozenFile,
    checker_commission: FrozenFile,
    instrument_freeze: FrozenFile,
    source_commit: str,
    candidate_binary: FrozenFile,
) -> dict[str, str]:
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise Unmeasured("provenance.command must be a string array")
    try:
        verb = raw.index("adjudicate")
    except ValueError as error:
        raise Unmeasured("provenance.command does not invoke adjudicate") from error
    if verb < 1 or Path(raw[verb - 1]).resolve(strict=True) != checker.path:
        raise Disagreement("provenance.command does not execute the frozen checker")
    tail = raw[verb + 1 :]
    if len(tail) % 2 != 0:
        raise Unmeasured("provenance.command has an unpaired option")
    parsed: dict[str, str] = {}
    for index in range(0, len(tail), 2):
        flag, value = tail[index : index + 2]
        if not flag.startswith("--") or flag in parsed:
            raise Unmeasured("provenance.command has an invalid or duplicate option")
        parsed[flag] = value
    expected_paths = {
        "--input-dir": input_dir,
        "--trace-state": trace_state,
        "--warpmap": warpmap.path,
        "--tiff": output_tiff.path,
        "--output": checker_state,
        "--preregistration": preregistration.path,
        "--commissioning-report": checker_commission.path,
        "--instrument-freeze": instrument_freeze.path,
        "--candidate-binary": candidate_binary.path,
    }
    for flag, path in expected_paths.items():
        try:
            actual = Path(parsed.get(flag, "")).resolve(strict=True)
        except Exception as error:
            raise Unmeasured(f"provenance.command {flag} path is absent") from error
        if actual != path.resolve(strict=True):
            raise Disagreement(f"provenance.command {flag} path mismatch")
    expected_text = {
        "--capture": capture,
        "--source-commit": source_commit,
        "--green-rule": GREEN_RULE,
    }
    for flag, value in expected_text.items():
        if parsed.get(flag) != value:
            raise Disagreement(f"provenance.command {flag} mismatch")
    try:
        if int(parsed["--chunk-rows"]) <= 0:
            raise ValueError
    except (KeyError, ValueError) as error:
        raise Unmeasured("provenance.command --chunk-rows must be positive") from error
    if set(parsed) != set(expected_paths) | set(expected_text) | {"--chunk-rows"}:
        raise Unmeasured("provenance.command contains an unexpected or missing option")
    return parsed


def compare_checker_artifacts(
    files: Mapping[str, FrozenFile],
    result: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray],
    m8r_violations: np.ndarray,
    violations: np.ndarray,
    rails: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    compared: dict[str, Any] = {}
    checker_meta = checker_json(files, "meta")
    checker_m8r = checker_json(files, "m8_r")
    checker_m8r_blocks = checker_json(files, "m8_r_block_manifest")
    checker_m8o = checker_json(files, "m8_o")
    checker_rails_doc = checker_json(files, "rail_disclosure")
    provenance = checker_json(files, "provenance")
    require_checker_identity(checker_meta, "m136-checker-target", "meta")
    require_checker_identity(checker_m8r, "m136-m8-r", "m8_r")
    require_checker_identity(
        checker_m8r_blocks, "m136-m8-r-block-manifest", "m8_r_block_manifest"
    )
    require_checker_identity(checker_m8o, "m136-m8-o", "m8_o")
    require_checker_identity(
        checker_rails_doc, "m136-rail-disclosure", "rail_disclosure"
    )
    require_checker_identity(provenance, "m136-checker-provenance", "provenance")

    for key in ("denominator", "lower_violations", "upper_violations", "violations"):
        if checker_m8r.get(key) != result["m8_r"][key]:
            raise Disagreement(f"checker/verifier M8-R {key} mismatch")
        if checker_m8o.get(key) != result["m8_o"][key]:
            raise Disagreement(f"checker/verifier M8-O {key} mismatch")
    if checker_m8r.get("block_count") != result["trace_blocks"]:
        raise Disagreement("checker/verifier M8-R block-count mismatch")
    block_manifest_relative = (
        files["m8_r_block_manifest"]
        .path.relative_to(context["checker_state"])
        .as_posix()
    )
    if checker_m8r.get("block_manifest") != block_manifest_relative:
        raise Unmeasured("M8-R JSON does not name the frozen block manifest")
    if checker_m8r.get("violation_array") != files["m8_r_violations"].path.name:
        raise Unmeasured("M8-R JSON does not name the frozen violation array")
    block_entries = checker_m8r_blocks.get("blocks")
    if (
        not isinstance(block_entries, list)
        or len(block_entries) != result["trace_blocks"]
    ):
        raise Unmeasured("checker M8-R per-block manifest is incomplete")
    expected_block_summaries = {
        (item["frame_order"], item["site"]): item for item in result["m8_r"]["blocks"]
    }
    block_row_parts: list[np.ndarray] = []
    block_artifact_paths: list[Path] = []
    seen_block_keys: set[tuple[Any, Any]] = set()
    for entry in block_entries:
        if not isinstance(entry, Mapping):
            raise Unmeasured("checker M8-R block entry is not an object")
        key = (entry.get("frame_order"), entry.get("site"))
        expected_summary = expected_block_summaries.get(key)
        if expected_summary is None or key in seen_block_keys:
            raise Disagreement("checker M8-R block identifies an unexpected frame/site")
        seen_block_keys.add(key)
        for name, value in expected_summary.items():
            if entry.get(name) != value:
                raise Disagreement(
                    f"checker/verifier M8-R block field mismatch: {key}.{name}"
                )
        artifact = entry.get("violation_array")
        if not isinstance(artifact, Mapping):
            raise Unmeasured("checker M8-R block omits violation-array evidence")
        try:
            artifact_path = (context["checker_state"] / str(artifact["path"])).resolve(
                strict=True
            )
            artifact_path.relative_to(context["checker_state"])
        except Exception as error:
            raise Unmeasured(
                "checker M8-R block artifact escapes or is absent"
            ) from error
        if artifact.get("bytes") != artifact_path.stat().st_size or artifact.get(
            "sha256"
        ) != sha256_file(artifact_path):
            raise Disagreement("checker M8-R block artifact hash/size mismatch")
        block_rows = np.load(artifact_path, allow_pickle=False)
        if (
            artifact.get("shape") != list(block_rows.shape)
            or artifact.get("dtype") != numpy_dtype_metadata(block_rows)
            or len(block_rows) != expected_summary["violation_rows"]
        ):
            raise Disagreement("checker M8-R block artifact metadata mismatch")
        block_row_parts.append(np.asarray(block_rows))
        block_artifact_paths.append(artifact_path)
    if seen_block_keys != set(expected_block_summaries):
        raise Disagreement("checker M8-R block manifest omits a frame/site")
    if checker_m8o.get("capture") != result["capture"]:
        raise Disagreement("checker/verifier M8-O capture mismatch")
    if checker_m8o.get("fraction") != result["m8_o"]["fraction"]:
        raise Disagreement("checker/verifier M8-O fraction mismatch")
    if checker_m8o.get("q") != FINAL_Q:
        raise Disagreement("checker M8-O uses a different final tolerance")
    if checker_m8o.get("green_rule") != GREEN_RULE:
        raise Disagreement("checker M8-O uses a different green rule")
    if checker_m8o.get("green_rule_status") != GREEN_RULE_STATUS:
        raise Unmeasured("checker M8-O green rule is not prospectively adopted")
    if checker_m8o.get("violation_array") != files["violations"].path.name:
        raise Unmeasured("M8-O JSON does not name the frozen violation array")
    expected_m8o_status = "PASS" if result["m8_o"]["violations"] == 0 else "FAIL"
    if checker_m8o.get("status") != expected_m8o_status:
        raise Disagreement(
            f"checker declares {checker_m8o.get('status')!r} but raw evidence is "
            f"{expected_m8o_status}"
        )
    expected_max_excess = (
        float(
            np.max(
                np.where(
                    violations["direction"] > 0,
                    violations["signed_excess"] - FINAL_Q,
                    -violations["signed_excess"] - FINAL_Q,
                ),
                initial=0.0,
            )
        )
        if len(violations)
        else 0.0
    )
    if checker_m8o.get("max_excess_over_tolerance") != expected_max_excess:
        raise Disagreement("checker/verifier M8-O maximum excess mismatch")

    expected_overall = (
        "PASS"
        if result["m8_r"]["violations"] == 0 and result["m8_o"]["violations"] == 0
        else "FAIL"
    )
    placed_frame_orders = sorted(
        {block["frame_order"] for block in result["m8_r"]["blocks"]}
    )
    expected_frame_sites = [
        f"{frame_order:08d}:{SITE_NAMES[site]}"
        for frame_order in placed_frame_orders
        for site in SITE_NAMES
    ]
    expected_frame_site_manifest = []
    for block in result["m8_r"]["blocks"]:
        site = SITE_BY_NAME[block["site"]]
        expected_frame_site_manifest.append(
            {
                "frame_order": block["frame_order"],
                "site": block["site"],
                "site_x": site[0],
                "site_y": site[1],
                "channel": CHANNEL_NAMES[SITE_CHANNEL[site]],
                "frame_path": block["source_path"],
                "source_sha256": block["source_sha256"],
                "trace": block["trace"],
                "trace_sha256": block["trace_sha256"],
            }
        )
    expected_meta = {
        "protocol": CHECKER_PROTOCOL,
        "checker_version": CHECKER_VERSION,
        "status": expected_overall,
        "capture": result["capture"],
        "green_rule": GREEN_RULE,
        "green_rule_status": GREEN_RULE_STATUS,
        "instrument_freeze_sha256": context["instrument_freeze"].sha256,
        "arithmetic_contract": ARITHMETIC_CONTRACT,
        "crop": {
            **result["crop"],
            "cover_margin": COVER_MARGIN,
            "bisection_steps": 60,
            "rounding": "inward",
        },
        "full_plane": result["full_plane"],
        "placed_frames": result["frames"],
        "trace_block_count": result["trace_blocks"],
        "complete_frame_site_set": True,
        "expected_frame_sites": expected_frame_sites,
        "consumed_frame_sites": [
            f"{block['frame_order']:08d}:{block['site']}"
            for block in result["m8_r"]["blocks"]
        ],
        "frame_site_manifest": expected_frame_site_manifest,
        "m8_r_status": ("PASS" if result["m8_r"]["violations"] == 0 else "FAIL"),
        "m8_o_status": expected_m8o_status,
    }
    for key, value in expected_meta.items():
        if checker_meta.get(key) != value:
            raise Disagreement(f"checker/verifier meta field mismatch: {key}")
    if (
        "provisional" in json.dumps(checker_meta).lower()
        or "pending" in json.dumps(checker_meta).lower()
    ):
        raise Unmeasured("checker metadata still carries a provisional ruling")
    kernel = checker_meta.get("kernel")
    if (
        not isinstance(kernel, Mapping)
        or kernel.get("id") != 2
        or kernel.get("name") != "clamped-catmull"
    ):
        raise Disagreement("checker metadata does not identify clamped Catmull-Rom")

    checker_m8r_violations = np.load(files["m8_r_violations"].path, allow_pickle=False)
    block_rows_all = (
        np.concatenate(block_row_parts)
        if block_row_parts
        else np.empty(0, dtype=M8R_VIOLATION_DTYPE)
    )
    if not arrays_equal(np.asarray(block_rows_all), np.asarray(checker_m8r_violations)):
        raise Disagreement("checker M8-R block arrays do not reproduce aggregate array")
    required_m8r_fields = set(M8R_VIOLATION_DTYPE.names or ())
    if checker_m8r_violations.dtype.names is None or not required_m8r_fields.issubset(
        checker_m8r_violations.dtype.names
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
            raise Disagreement(
                f"checker/verifier M8-R violation field mismatch: {field}"
            )
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
        ("lower_frame_witness", "lower_frame_witness"),
        ("upper_frame_witness", "upper_frame_witness"),
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
    checker_order = np.lexsort(
        tuple(checker_violations[name] for name in reversed(order_fields))
    )
    verifier_order = np.lexsort(
        tuple(violations[name] for name in reversed(order_fields))
    )
    for field in required_fields:
        left = checker_violations[field][checker_order]
        right = violations[field][verifier_order]
        if not arrays_equal(np.asarray(left), np.asarray(right)):
            raise Disagreement(f"checker/verifier violation field mismatch: {field}")
    compared["violations"] = {"equal": True, "sha256": files["violations"].sha256}

    if (
        checker_rails_doc.get("capture") != result["capture"]
        or checker_rails_doc.get("rail_disclosure") != rails
    ):
        raise Disagreement("checker/verifier rail disclosure mismatch")
    compared["rail_disclosure"] = {
        "equal": True,
        "sha256": files["rail_disclosure"].sha256,
    }

    require_frozen_reference(
        provenance.get("candidate_binary"),
        context["candidate_binary"],
        "provenance.candidate_binary",
    )
    require_frozen_reference(
        provenance.get("checker"), context["checker"], "provenance.checker"
    )
    require_frozen_reference(
        provenance.get("preregistration"),
        context["preregistration"],
        "provenance.preregistration",
    )
    provenance_commissioning = provenance.get("commissioning")
    require_frozen_reference(
        provenance_commissioning,
        context["checker_commission"],
        "provenance.commissioning",
    )
    if (
        not isinstance(provenance_commissioning, Mapping)
        or provenance_commissioning.get("fixture_manifest_sha256")
        != context["fixture_manifest"].sha256
    ):
        raise Disagreement("checker provenance fixture-manifest hash mismatch")
    require_frozen_reference(
        provenance.get("warpmap"), context["warpmap"], "provenance.warpmap"
    )
    require_frozen_reference(
        provenance.get("output_tiff"),
        context["output_tiff"],
        "provenance.output_tiff",
    )
    require_frozen_reference(
        provenance.get("instrument_freeze"),
        context["instrument_freeze"],
        "provenance.instrument_freeze",
    )
    if (
        provenance.get("protocol") != CHECKER_PROTOCOL
        or provenance.get("capture") != result["capture"]
        or provenance.get("source_commit") != context["source_commit"]
        or provenance.get("green_rule") != GREEN_RULE
        or provenance.get("green_rule_status") != GREEN_RULE_STATUS
        or provenance.get("instrument_freeze_sha256")
        != context["instrument_freeze"].sha256
    ):
        raise Disagreement("checker provenance governing identity mismatch")
    if provenance.get("trace_sha256") != result["evidence"]["trace_sha256"]:
        raise Disagreement("checker provenance trace inventory mismatch")
    if provenance.get("source_sha256") != result["evidence"]["source_sha256"]:
        raise Disagreement("checker provenance RAW-source inventory mismatch")

    expected_environment = dict(context["environment"])
    if provenance.get("environment") != expected_environment:
        raise Disagreement("checker provenance environment mismatch")
    versions = provenance.get("versions")
    if (
        not isinstance(versions, Mapping)
        or set(versions) != {"python", "numpy", "tifffile"}
        or not all(isinstance(value, str) and value for value in versions.values())
    ):
        raise Unmeasured("checker provenance software versions are incomplete")
    parse_checker_command(
        provenance.get("command"),
        checker=context["checker"],
        capture=result["capture"],
        input_dir=context["input_dir"],
        trace_state=context["trace_state"],
        warpmap=context["warpmap"],
        output_tiff=context["output_tiff"],
        checker_state=context["checker_state"],
        preregistration=context["preregistration"],
        checker_commission=context["checker_commission"],
        instrument_freeze=context["instrument_freeze"],
        source_commit=context["source_commit"],
        candidate_binary=context["candidate_binary"],
    )

    expected_artifacts = {
        file.path.relative_to(context["checker_state"]).as_posix(): file
        for label, file in files.items()
        if label != "provenance"
    }
    artifact_inventory = provenance.get("artifacts")
    if not isinstance(artifact_inventory, Mapping) or set(artifact_inventory) != set(
        expected_artifacts
    ):
        raise Unmeasured("checker provenance artifact inventory is incomplete")
    for name, expected in expected_artifacts.items():
        metadata = artifact_inventory[name]
        if (
            not isinstance(metadata, Mapping)
            or metadata.get("path") != name
            or metadata.get("bytes") != expected.path.stat().st_size
            or metadata.get("sha256") != expected.sha256
        ):
            raise Disagreement(f"checker provenance artifact metadata mismatch: {name}")
        if expected.path.suffix == ".npy":
            array = np.load(expected.path, mmap_mode="r", allow_pickle=False)
            if metadata.get("shape") != list(array.shape) or metadata.get(
                "dtype"
            ) != numpy_dtype_metadata(array):
                raise Disagreement(
                    f"checker provenance array metadata mismatch: {name}"
                )
    expected_state_files = (
        set(expected_artifacts)
        | {"provenance.json"}
        | {
            path.relative_to(context["checker_state"]).as_posix()
            for path in block_artifact_paths
        }
    )
    observed_state_files = {
        path.relative_to(context["checker_state"]).as_posix()
        for path in context["checker_state"].rglob("*")
        if path.is_file()
    }
    if observed_state_files != expected_state_files:
        raise Unmeasured(
            "checker output contains missing or unaccounted files: "
            f"missing={sorted(expected_state_files - observed_state_files)[:8]}, "
            f"extra={sorted(observed_state_files - expected_state_files)[:8]}"
        )
    compared["meta"] = {"equal": True, "sha256": files["meta"].sha256}
    compared["m8_r"] = {"equal": True, "sha256": files["m8_r"].sha256}
    compared["m8_r_block_manifest"] = {
        "equal": True,
        "sha256": files["m8_r_block_manifest"].sha256,
    }
    compared["m8_o"] = {"equal": True, "sha256": files["m8_o"].sha256}
    compared["provenance"] = {
        "equal": True,
        "sha256": files["provenance"].sha256,
    }
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
    checker_context: Mapping[str, Any] | None = None,
    expected_freeze_sha256: str | None = None,
) -> dict[str, Any]:
    warpmap = parse_warpmap(warpmap_file.path)
    if warpmap.resampler != "clamped-catmull":
        raise Unmeasured(f"{capture}: warpmap resampler is {warpmap.resampler!r}")
    crop_x, crop_y, compact_width, compact_height, cover_scale = reconstruct_crop(
        warpmap
    )

    claims = state_dir / "claims"
    staging = state_dir / "staging"
    for directory, label in ((claims, "claim"), (staging, "staging")):
        if directory.exists() and any(directory.iterdir()):
            raise Unmeasured(
                f"{capture}: unresolved trace {label} files exist in {directory}"
            )
    block_dir = state_dir / "blocks"
    if not block_dir.is_dir():
        raise Unmeasured(f"{capture}: trace blocks directory is absent: {block_dir}")
    unexpected = [
        path.name
        for path in block_dir.iterdir()
        if not path.is_file()
        or path.is_symlink()
        or not TRACE_NAME.fullmatch(path.name)
    ]
    if unexpected:
        raise Unmeasured(
            f"{capture}: unexpected entries in trace blocks: {unexpected[:8]}"
        )
    block_paths = sorted(block_dir.glob("*.m8site"))
    if not block_paths:
        raise Unmeasured(f"{capture}: no trace-v3 blocks")
    source_hash_cache: dict[Path, str] = {}
    blocks = [parse_trace(path, source_hash_cache) for path in block_paths]
    expected_trace_files = {block.path.resolve() for block in blocks}
    observed_trace_files = {
        path.resolve() for path in state_dir.rglob("*") if path.is_file()
    }
    ignored_producer_files = {
        path
        for path in observed_trace_files
        if path.name
        in {"producer-supplied-hull.npy", "producer-supplied-contributor-mask.npy"}
    }
    unexpected_trace_files = (
        observed_trace_files - expected_trace_files - ignored_producer_files
    )
    if expected_trace_files - observed_trace_files or unexpected_trace_files:
        raise Unmeasured(
            f"{capture}: trace state contains unaccounted files: "
            f"missing={sorted(str(path) for path in expected_trace_files - observed_trace_files)[:8]}, "
            f"extra={sorted(str(path) for path in unexpected_trace_files)[:8]}"
        )
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
    if expected_freeze_sha256 is not None and any(
        block.instrument_freeze_sha256 != expected_freeze_sha256 for block in blocks
    ):
        raise Unmeasured(
            f"{capture}: trace blocks are not bound to the frozen instrument"
        )

    image = load_tiff(
        output_file.path,
        compact_height,
        compact_width,
        expected_freeze_sha256,
    )
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
            f"contributors={int(valid_contributors[channel, y, x])}, expected={placed_count}"
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
    rail_fractions = {
        category: {
            key: value / float(m8o["denominator"]) for key, value in counts.items()
        }
        for category, counts in rails.items()
    }
    m8r = {
        "denominator": sum(item["eligible_samples"] for item in m8r_summaries),
        "lower_violations": sum(item["lower_violation_rows"] for item in m8r_summaries),
        "upper_violations": sum(item["upper_violation_rows"] for item in m8r_summaries),
        "violations": sum(item["violation_rows"] for item in m8r_summaries),
        "max_excess_over_tolerance": max(
            (item["max_excess_over_tolerance"] for item in m8r_summaries),
            default=0.0,
        ),
        "blocks": m8r_summaries,
    }
    m8r_signed = np.asarray(m8r_violations["signed_excess"], dtype=np.float64)
    m8r_positive = m8r_signed[m8r_signed > 0.0]
    m8r_negative = m8r_signed[m8r_signed < 0.0]
    m8r["maximum_positive_signed_excess"] = (
        float(np.max(m8r_positive)) if m8r_positive.size else 0.0
    )
    m8r["minimum_negative_signed_excess"] = (
        float(np.min(m8r_negative)) if m8r_negative.size else 0.0
    )
    m8r["maximum_absolute_signed_excess"] = (
        float(np.max(np.abs(m8r_signed))) if m8r_signed.size else 0.0
    )
    if m8r["denominator"] <= 0:
        raise Unmeasured(f"{capture}: M8-R denominator is empty")
    m8r["fraction_exact"] = f"{m8r['violations']}/{m8r['denominator']}"
    m8r["fraction"] = m8r["violations"] / float(m8r["denominator"])
    result: dict[str, Any] = {
        "capture": capture,
        "crop": {
            "x": crop_x,
            "y": crop_y,
            "width": compact_width,
            "height": compact_height,
            "cover_scale": cover_scale,
        },
        "full_plane": {
            "width": blocks[0].full_width,
            "height": blocks[0].full_height,
        },
        "frames": placed_count,
        "trace_blocks": len(blocks),
        "m8_r": m8r,
        "m8_o": m8o,
        "rail_disclosure": rails,
        "rail_disclosure_fractions": rail_fractions,
        "evidence": {
            "warpmap": {"path": str(warpmap_file.path), "sha256": warpmap_file.sha256},
            "output_tiff": {
                "path": str(output_file.path),
                "sha256": output_file.sha256,
            },
            "trace_sha256": {block.path.name: block.file_sha256 for block in blocks},
            "source_sha256": {
                str(path): digest
                for path, digest in sorted(
                    source_hash_cache.items(), key=lambda x: str(x[0])
                )
            },
            "ignored_producer_derived_artifacts": {
                str(path): sha256_file(path)
                for path in sorted(ignored_producer_files, key=lambda item: str(item))
            },
        },
    }
    arrays = {
        "pre_lower": pre_lower,
        "pre_upper": pre_upper,
        "projected_lower": projected_lower,
        "projected_upper": projected_upper,
        "valid_contributors": valid_contributors,
        "lower_frame_witness": low_frames,
        "upper_frame_witness": high_frames,
    }
    if checker_artifacts is not None:
        if checker_context is None:
            raise Unmeasured("checker artifacts require strict comparison context")
        result["checker_comparison"] = compare_checker_artifacts(
            checker_artifacts,
            result,
            arrays,
            m8r_violations,
            violations,
            rails,
            checker_context,
        )
    assert_still_frozen(warpmap_file, f"{capture} warpmap")
    assert_still_frozen(output_file, f"{capture} output TIFF")
    for label, file in (checker_artifacts or {}).items():
        assert_still_frozen(file, f"{capture} checker artifact {label}")
    for block in blocks:
        if sha256_file(block.path) != block.file_sha256:
            raise Unmeasured(
                f"{capture}: trace changed during verification: {block.path}"
            )
    for source_path, expected_hash in source_hash_cache.items():
        if sha256_file(source_path) != expected_hash:
            raise Unmeasured(
                f"{capture}: source changed during verification: {source_path}"
            )
    for ignored_path in ignored_producer_files:
        expected_hash = result["evidence"]["ignored_producer_derived_artifacts"][
            str(ignored_path)
        ]
        if sha256_file(ignored_path) != expected_hash:
            raise Unmeasured(
                f"{capture}: ignored producer artifact changed: {ignored_path}"
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
    files = {
        name: frozen_file(value, f"instrument {name}") for name, value in raw.items()
    }
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
        if "checker_m136" in name or name.startswith("strehl") or ".strehl" in name
    ]
    if forbidden:
        raise Unmeasured(f"verifier has forbidden imports: {forbidden}")
    return {"imports": sorted(imports), "forbidden_imports": forbidden}


def validate_commission_report(
    file: FrozenFile,
    prereg_canonical_hash: str,
    interpretation_canonical_hash: str,
    verifier_canonical_hash: str,
) -> dict[str, Any]:
    try:
        report = json.loads(file.path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(
            f"invalid verifier commissioning report {file.path}"
        ) from error
    if report.get("protocol") != VERIFIER_PROTOCOL or report.get("status") != "PASS":
        raise Unmeasured(
            "verifier commissioning report is not a PASS for this protocol"
        )
    if (
        report.get("preregistration", {}).get("canonical_sha256")
        != prereg_canonical_hash
    ):
        raise Unmeasured("verifier commissioning used a different preregistration")
    if (
        report.get("prospective_interpretation", {}).get("canonical_sha256")
        != interpretation_canonical_hash
    ):
        raise Unmeasured("verifier commissioning used a different interpretation")
    if report.get("verifier", {}).get("canonical_sha256") != verifier_canonical_hash:
        raise Unmeasured(
            "verifier commissioning was produced by different verifier bytes"
        )
    defect = report.get("degradation_plant", {})
    improvement = report.get("improvement_plant", {})
    defect_landed = defect.get("landed", {})
    improvement_landed = improvement.get("landed", {})

    def validate_landed_pair(value: Any, label: str) -> None:
        if not isinstance(value, Mapping) or set(value) != {"lower", "upper"}:
            raise Unmeasured(f"commissioned {label} does not contain both directions")
        for direction, plant in value.items():
            if not isinstance(plant, Mapping) or plant.get("occurrences") != 1:
                raise Unmeasured(
                    f"commissioned {label} {direction} plant was not uniquely anchored"
                )
            before = str(plant.get("sha256_before", ""))
            after = str(plant.get("sha256_after", ""))
            if (
                before == after
                or not re.fullmatch(r"[0-9A-F]{64}", before)
                or not re.fullmatch(r"[0-9A-F]{64}", after)
            ):
                raise Unmeasured(
                    f"commissioned {label} {direction} plant has no valid changed hash"
                )

    validate_landed_pair(defect_landed, "degradation")
    expected_lines = {
        ("degradation", "lower"): (
            '  "encoded_r": 65535,',
            '  "encoded_r": 65534,',
        ),
        ("degradation", "upper"): (
            '  "encoded_b": 0,',
            '  "encoded_b": 1,',
        ),
        ("improvement", "lower"): (
            '  "encoded_r": 65534,',
            '  "encoded_r": 65535,',
        ),
        ("improvement", "upper"): (
            '  "encoded_b": 1,',
            '  "encoded_b": 0,',
        ),
    }
    for direction, plant in defect_landed.items():
        old, new = expected_lines[("degradation", direction)]
        if plant.get("old_line") != old or plant.get("new_line") != new:
            raise Unmeasured(f"commissioned degradation {direction} line is wrong")
    if defect.get("result", {}).get("m8_o_violations") != 2:
        raise Unmeasured(
            "commissioned degradations did not produce exactly two violations"
        )
    if defect.get("result", {}).get("status") != "FAIL":
        raise Unmeasured("commissioned degradation was not reported FAIL")
    if defect.get("result", {}).get("violations") != [
        {"x": 2, "y": 3, "channel": "R", "direction": -1, "encoded": 65534},
        {"x": 3, "y": 4, "channel": "B", "direction": 1, "encoded": 1},
    ]:
        raise Unmeasured("commissioned degradation rows or signs are wrong")
    validate_landed_pair(improvement_landed, "improvement")
    for direction, plant in improvement_landed.items():
        old, new = expected_lines[("improvement", direction)]
        if plant.get("old_line") != old or plant.get("new_line") != new:
            raise Unmeasured(f"commissioned improvement {direction} line is wrong")
    if not (
        defect_landed["lower"]["sha256_after"]
        == defect_landed["upper"]["sha256_before"]
        and defect_landed["upper"]["sha256_after"]
        == improvement_landed["lower"]["sha256_before"]
        and improvement_landed["lower"]["sha256_after"]
        == improvement_landed["upper"]["sha256_before"]
        and improvement_landed["upper"]["sha256_after"]
        == defect_landed["lower"]["sha256_before"]
    ):
        raise Unmeasured("commissioning plant hash chain is not reversible")
    if improvement.get("result", {}).get("m8_o_violations") != 0:
        raise Unmeasured("commissioned improvement did not remove the violation")
    if improvement.get("result", {}).get("status") != "PASS":
        raise Unmeasured("commissioned improvement was not reported PASS")
    if improvement.get("result", {}).get("violations") != []:
        raise Unmeasured("commissioned improvement retained violation rows")
    baseline = report.get("baseline_green", {})
    if (
        baseline.get("status") != "PASS"
        or baseline.get("m8_r_violations") != 0
        or baseline.get("m8_o_violations") != 0
        or baseline.get("violations") != []
    ):
        raise Unmeasured("commissioned baseline is not a zero-violation PASS")
    if defect.get("result", {}).get("output_sha256") == improvement.get(
        "result", {}
    ).get("output_sha256"):
        raise Unmeasured(
            "commissioned defect and improvement TIFF hashes are identical"
        )
    numeric_cases = report.get("numeric_cases")
    expected_numeric_names = {
        "convex_bilinear_green",
        "copy_green",
        "in_range_high_red",
        "in_range_low_red",
        "unrepresentable_high_at_rail_green",
        "unrepresentable_high_off_rail_red",
        "unrepresentable_low_at_rail_green",
        "unrepresentable_low_off_rail_red",
    }
    if (
        not isinstance(numeric_cases, Mapping)
        or set(numeric_cases) != expected_numeric_names
    ):
        raise Unmeasured(
            "commissioning report does not contain all eight numeric cases"
        )
    if any(not isinstance(case, Mapping) for case in numeric_cases.values()):
        raise Unmeasured("a numeric commissioning case is malformed")
    if any(
        case.get("observed_violations") != case.get("expected_violations")
        for case in numeric_cases.values()
    ):
        raise Unmeasured("a numeric commissioning case did not match its expectation")
    if report.get("interval_containment", {}).get("misses") != 0:
        raise Unmeasured("outward interval commissioning found a containment miss")
    source_inventory = report.get("source_inventory_case", {})
    if (
        source_inventory.get("status") != "PASS"
        or "crates/app/src/target/mod.rs"
        not in source_inventory.get("required_present", [])
        or "outside-path-dependency/src/lib.rs"
        not in source_inventory.get("required_present", [])
        or "target-m136/release/strehl.exe"
        not in source_inventory.get("top_level_target_excluded", [])
        or "target-m136-tests/debug/probe.exe"
        not in source_inventory.get("top_level_target_excluded", [])
        or any(
            path.startswith("target-m136")
            for path in source_inventory.get("observed", [])
        )
        or source_inventory.get("build_id") != "m136-248178b921f9-aaaaaaaaaaaa"
    ):
        raise Unmeasured("source-inventory commissioning is incomplete or wrong")
    quantizer = report.get("quantizer_case", {})
    if (
        quantizer.get("intermediate_u16") != 1013
        or quantizer.get("green_violation") is not False
        or quantizer.get("red_violation") is not True
    ):
        raise Unmeasured("intermediate-u16 commissioning is incomplete or wrong")
    crop_case = report.get("crop_origin_case", {})
    if (
        crop_case.get("correct_origin_violations") != 0
        or crop_case.get("wrong_origin_violations") != 6
        or crop_case.get("expected_wrong_origin_violations") != 6
    ):
        raise Unmeasured("crop-origin commissioning is incomplete or wrong")
    kernel_cases = report.get("m8_r_kernel_cases", {})
    arms = kernel_cases.get("arms", {})
    expected_exact = kernel_cases.get("expected_exact", {})
    required_exact = {
        "catmull_hard_step": {
            "denominator": 252,
            "lower_violations": 14,
            "upper_violations": 14,
            "violations": 28,
        },
        "clamped_hard_step": {
            "denominator": 252,
            "lower_violations": 0,
            "upper_violations": 0,
            "violations": 0,
        },
        "widened_clamp_sabotage": {
            "denominator": 252,
            "lower_violations": 14,
            "upper_violations": 14,
            "violations": 28,
        },
        "explicit_high_low": {
            "denominator": 252,
            "lower_violations": 1,
            "upper_violations": 1,
            "violations": 2,
        },
    }
    if expected_exact != required_exact or any(
        arms.get(name) != counts for name, counts in required_exact.items()
    ):
        raise Unmeasured("M8-R exact-count commissioning is incomplete or wrong")
    if (
        any(
            arms.get(name, {}).get("violations") != 0
            for name in ("copy_null", "clamped_copy_null", "convex_bilinear_null")
        )
        or kernel_cases.get("clamped_copy_bit_exact") is not True
    ):
        raise Unmeasured("M8-R null commissioning is incomplete or wrong")
    inverse_gain = report.get("inverse_gain_order_case", {})
    production_inverse_gain = inverse_gain.get("production_path", {})
    if (
        inverse_gain.get("actual_intermediate_u16") != 1
        or inverse_gain.get("direct_division_intermediate_u16") != 2
        or inverse_gain.get("distinguishes_operation_order") is not True
        or production_inverse_gain.get("intermediate_interval_u16") != [17268, 17269]
        or production_inverse_gain.get("direct_division_interval_u16") != [17269, 17269]
        or production_inverse_gain.get("distinguishes_operation_order") is not True
    ):
        raise Unmeasured("inverse-gain operation-order commissioning is incomplete")
    production_controls = report.get("production_path_controls", {})
    production_m8r = production_controls.get("m8_r", {})
    production_m8r_defect = production_m8r.get("defect", {})
    production_m8r_improvement = production_m8r.get("improvement", {})
    if (
        production_m8r_defect.get("m8_r")
        != {
            "denominator": 784,
            "lower_violations": 1,
            "upper_violations": 1,
            "violations": 2,
        }
        or production_m8r_defect.get("m8_o_violations") != 0
        or production_m8r_defect.get("violation_directions") != [-1, 1]
        or production_m8r_improvement.get("m8_r")
        != {
            "denominator": 784,
            "lower_violations": 0,
            "upper_violations": 0,
            "violations": 0,
        }
        or production_m8r_improvement.get("m8_o_violations") != 0
        or production_m8r_defect.get("recipe_sha256")
        == production_m8r_improvement.get("recipe_sha256")
        or production_controls.get("inverse_gain") != production_inverse_gain
        or set(production_m8r.get("improvement_landed", {})) != {"lower", "upper"}
        or any(
            plant.get("occurrences") != 1
            or plant.get("sha256_before") == plant.get("sha256_after")
            for plant in production_m8r.get("improvement_landed", {}).values()
        )
    ):
        raise Unmeasured("production-path commissioning is incomplete or wrong")
    production_green = production_controls.get("green_pairing", {})
    production_green_defect = production_green.get("defect", {})
    production_green_improvement = production_green.get("improvement", {})
    green_improvement_landed = production_green.get("improvement_landed", {})
    if (
        production_green_defect.get("m8_r_violations") != 0
        or production_green_defect.get("m8_o")
        != {
            "denominator": 243,
            "lower_violations": 81,
            "upper_violations": 0,
            "violations": 81,
        }
        or production_green_defect.get("violation_channels") != ["G"]
        or production_green_defect.get("violation_directions") != [-1]
        or production_green_improvement.get("m8_r_violations") != 0
        or production_green_improvement.get("m8_o")
        != {
            "denominator": 243,
            "lower_violations": 0,
            "upper_violations": 0,
            "violations": 0,
        }
        or production_green_defect.get("recipe_sha256")
        == production_green_improvement.get("recipe_sha256")
        or green_improvement_landed.get("occurrences") != 1
        or green_improvement_landed.get("sha256_before")
        == green_improvement_landed.get("sha256_after")
    ):
        raise Unmeasured("production-path green commissioning is incomplete or wrong")
    production_reciprocal = production_controls.get("reciprocal_order", {})
    production_reciprocal_defect = production_reciprocal.get("defect", {})
    production_reciprocal_improvement = production_reciprocal.get("improvement", {})
    reciprocal_improvement_landed = production_reciprocal.get("improvement_landed", {})
    if (
        production_reciprocal_defect.get("m8_r_violations") != 0
        or production_reciprocal_defect.get("m8_o")
        != {
            "denominator": 243,
            "lower_violations": 81,
            "upper_violations": 0,
            "violations": 81,
        }
        or production_reciprocal_defect.get("violation_channels") != ["R"]
        or production_reciprocal_defect.get("violation_directions") != [-1]
        or production_reciprocal_improvement.get("m8_r_violations") != 0
        or production_reciprocal_improvement.get("m8_o")
        != {
            "denominator": 243,
            "lower_violations": 0,
            "upper_violations": 0,
            "violations": 0,
        }
        or production_reciprocal_defect.get("recipe_sha256")
        == production_reciprocal_improvement.get("recipe_sha256")
        or reciprocal_improvement_landed.get("occurrences") != 1
        or reciprocal_improvement_landed.get("sha256_before")
        == reciprocal_improvement_landed.get("sha256_after")
    ):
        raise Unmeasured(
            "production-path reciprocal-order commissioning is incomplete or wrong"
        )
    pairing = report.get("green_pairing_case", {})
    if (
        pairing.get("same_frame_violation") is not True
        or pairing.get("independent_site_violation") is not False
    ):
        raise Unmeasured("green-pairing commissioning does not distinguish the rules")
    fail_closed = report.get("fail_closed", {})
    tiff_binding = fail_closed.get("wrong_tiff_freeze_binding", {})
    if (
        not fail_closed.get("missing_frame_site")
        or not fail_closed.get("duplicate_frame_site")
        or fail_closed.get("trace_v2_rejected") is not True
        or fail_closed.get("trace_v2_reason") != "requires trace-v3"
        or not fail_closed.get("wrong_crop_origin")
        or not fail_closed.get("wrong_freeze_binding")
        or tiff_binding.get("rejected") is not True
        or tiff_binding.get("reason")
        != "TIFF is not bound to the frozen M136 instrument"
        or tiff_binding.get("defect_tiff_sha256")
        == tiff_binding.get("improved_tiff_sha256")
        or any(
            tiff_binding.get(name, {}).get("occurrences") != 1
            or tiff_binding.get(name, {}).get("sha256_before")
            == tiff_binding.get(name, {}).get("sha256_after")
            for name in ("defect_landed", "improvement_landed")
        )
        or fail_closed.get("producer_supplied_hull_ignored") is not True
    ):
        raise Unmeasured("fail-closed commissioning evidence is incomplete")
    return {
        "path": str(file.path),
        "sha256": file.sha256,
        "degradation": "planted lower and upper violations caught",
        "improvement": "both planted violations reversed to PASS",
    }


def validate_checker_fixture(
    manifest_file: FrozenFile,
    preregistration: FrozenFile,
    prereg: Mapping[str, Any],
) -> dict[str, Any]:
    fixture_dir = manifest_file.path.parent
    try:
        document = json.loads(manifest_file.path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(
            f"invalid checker fixture manifest {manifest_file.path}"
        ) from error
    if (
        not isinstance(document, Mapping)
        or document.get("schema") != "m136-commissioning-fixture-manifest"
        or document.get("schema_version") != 1
    ):
        raise Unmeasured("checker fixture manifest has an unsupported schema")
    prereg_ref = document.get("preregistration")
    if (
        not isinstance(prereg_ref, Mapping)
        or Path(str(prereg_ref.get("path", ""))).resolve(strict=True)
        != preregistration.path
        or prereg_ref.get("sha256") != preregistration.sha256
        or prereg_ref.get("protocol") != PROTOCOL
        or prereg_ref.get("status") != prereg.get("status")
        or prereg_ref.get("result") != prereg.get("result")
    ):
        raise Disagreement("checker fixture identifies a different preregistration")
    semantics = document.get("fixture_semantics")
    if (
        not isinstance(semantics, Mapping)
        or semantics.get("numeric_cases") != FIXTURE_REPRESENTATION
    ):
        raise Unmeasured("checker fixture has not adopted the numeric identity ruling")

    inventory = document.get("artifacts")
    if not isinstance(inventory, list):
        raise Unmeasured("checker fixture manifest omits its artifact inventory")
    declared: dict[str, Mapping[str, Any]] = {}
    for entry in inventory:
        if not isinstance(entry, Mapping):
            raise Unmeasured("checker fixture inventory entry is not an object")
        name = str(entry.get("path", ""))
        if not name or Path(name).name != name or name in declared:
            raise Unmeasured("checker fixture inventory has an invalid path")
        declared[name] = entry
    observed = {
        path.name
        for path in fixture_dir.iterdir()
        if path.is_file() and path.name != manifest_file.path.name
    }
    if set(declared) != observed:
        raise Unmeasured("checker fixture inventory does not match its directory")
    for name, metadata in declared.items():
        path = fixture_dir / name
        if metadata.get("bytes") != path.stat().st_size or metadata.get(
            "sha256"
        ) != sha256_file(path):
            raise Disagreement(f"checker fixture artifact changed: {name}")

    numeric_path = fixture_dir / "m8-o-numeric-cases.json"
    intermediate_path = fixture_dir / "intermediate-quantizer-case.json"
    crop_path = fixture_dir / "crop-origin-case.json"
    try:
        numeric = json.loads(numeric_path.read_text(encoding="utf-8"))
        intermediate = json.loads(intermediate_path.read_text(encoding="utf-8"))
        crop = json.loads(crop_path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured("checker fixture JSON is unreadable") from error
    frozen_commissioning = prereg.get("commissioning", {})
    expected_numeric = frozen_commissioning.get("m8_o_numeric_cases", {})
    numeric_cases = numeric.get("cases") if isinstance(numeric, Mapping) else None
    if (
        numeric.get("schema_version") != 1
        or numeric.get("case_count") != 8
        or not isinstance(numeric_cases, Mapping)
        or set(numeric_cases) != set(expected_numeric)
    ):
        raise Unmeasured("checker numeric fixture is incomplete")
    for name, expected in expected_numeric.items():
        actual = numeric_cases[name]
        if (
            not isinstance(actual, Mapping)
            or actual.get("representation_map") != FIXTURE_REPRESENTATION
            or {
                key: actual.get(key)
                for key in ("lo", "hi", "tau", "encoded", "expected_violations")
            }
            != {
                key: expected.get(key)
                for key in ("lo", "hi", "tau", "encoded", "expected_violations")
            }
        ):
            raise Disagreement(f"checker numeric fixture differs at {name}")
    expected_intermediate = frozen_commissioning.get("intermediate_quantizer_case", {})
    if (
        intermediate.get("schema_version") != 1
        or intermediate.get("case") != expected_intermediate
    ):
        raise Disagreement("checker intermediate-quantizer fixture differs")
    expected_crop = frozen_commissioning.get("crop_origin_case", {})
    if crop.get("schema_version") != 1 or crop.get("case") != expected_crop:
        raise Disagreement("checker crop-origin fixture differs")

    source = np.load(fixture_dir / "crop-origin-source.npy", allow_pickle=False)
    correct = tifffile.imread(fixture_dir / "crop-origin-correct.tiff")
    wrong = tifffile.imread(fixture_dir / "crop-origin-wrong.tiff")
    if source.shape != (8, 8) or source.dtype != np.float64:
        raise Unmeasured("checker crop-origin source grid has wrong shape/dtype")
    expected_source = np.asarray(
        100 * np.indices((8, 8), dtype=np.float64)[0]
        + np.indices((8, 8), dtype=np.float64)[1],
        dtype=np.float64,
    )
    if not np.array_equal(source, expected_source):
        raise Disagreement("checker crop-origin source grid has wrong values")
    origin_x = int(expected_crop["origin_x"])
    origin_y = int(expected_crop["origin_y"])
    height = int(expected_crop["compact_height"])
    width = int(expected_crop["compact_width"])
    divisor_match = re.fullmatch(
        r"F\(z\)=z/(\d+) before final-u16 serialization",
        str(expected_crop["normalization"]),
    )
    if divisor_match is None:
        raise Unmeasured("unsupported frozen crop-origin normalization")
    divisor = float(divisor_match.group(1))

    def encode(values: np.ndarray) -> np.ndarray:
        return np.asarray(
            np.floor(np.clip(values / divisor, 0.0, 1.0) * U16_MAX + 0.5),
            dtype=np.uint16,
        )

    expected_correct = encode(
        source[origin_y : origin_y + height, origin_x : origin_x + width]
    )
    expected_wrong = encode(source[:height, :width])
    if not np.array_equal(correct, expected_correct) or not np.array_equal(
        wrong, expected_wrong
    ):
        raise Disagreement("checker crop-origin TIFF fixture has wrong pixels")
    if int(np.count_nonzero(correct != wrong)) != int(
        expected_crop["expected_wrong_origin_violations"]
    ):
        raise Disagreement("checker crop-origin fixture does not plant six defects")
    return {
        "manifest": {
            "path": str(manifest_file.path),
            "sha256": manifest_file.sha256,
        },
        "directory": str(fixture_dir),
        "artifacts": len(declared),
        "numeric_representation": FIXTURE_REPRESENTATION,
        "crop_defects_landed": int(np.count_nonzero(correct != wrong)),
    }


def validate_checker_commission_artifacts(
    report_file: FrozenFile,
    evidence_file: FrozenFile,
    *,
    checker: FrozenFile,
    fixture_manifest: FrozenFile,
    preregistration: FrozenFile,
) -> dict[str, Any]:
    try:
        report = json.loads(report_file.path.read_text(encoding="utf-8"))
        evidence = json.loads(evidence_file.path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured("checker commissioning artifacts are unreadable") from error
    if (
        report.get("schema") != "m136-checker-commissioning"
        or report.get("schema_version") != 1
        or report.get("protocol") != CHECKER_PROTOCOL
        or report.get("checker_version") != CHECKER_VERSION
        or report.get("status") != "PASS"
        or report.get("numeric_representation") != FIXTURE_REPRESENTATION
    ):
        raise Unmeasured("checker commissioning report is not an adopted PASS")
    require_frozen_reference(
        report.get("preregistration"),
        preregistration,
        "checker commission preregistration",
    )
    require_frozen_reference(
        report.get("checker"), checker, "checker commission checker"
    )
    fixture = report.get("fixture")
    if (
        not isinstance(fixture, Mapping)
        or Path(str(fixture.get("path", ""))).resolve(strict=True)
        != fixture_manifest.path.parent
        or Path(str(fixture.get("manifest", ""))).resolve(strict=True)
        != fixture_manifest.path
        or fixture.get("manifest_sha256") != fixture_manifest.sha256
        or fixture.get("artifacts_validated")
        != len(
            [
                path
                for path in fixture_manifest.path.parent.iterdir()
                if path.is_file() and path != fixture_manifest.path
            ]
        )
    ):
        raise Disagreement("checker commissioning report identifies another fixture")
    numeric = report.get("numeric_cases")
    expected_numeric_names = {
        "convex_bilinear_green",
        "copy_green",
        "in_range_high_red",
        "in_range_low_red",
        "unrepresentable_high_at_rail_green",
        "unrepresentable_high_off_rail_red",
        "unrepresentable_low_at_rail_green",
        "unrepresentable_low_off_rail_red",
    }
    if (
        not isinstance(numeric, Mapping)
        or set(numeric) != expected_numeric_names
        or any(
            not isinstance(case, Mapping)
            or case.get("status") != "PASS"
            or case.get("observed_violations") != case.get("expected_violations")
            or case.get("observed_direction") != case.get("expected_direction")
            or case.get("representation_map") != FIXTURE_REPRESENTATION
            for case in numeric.values()
        )
    ):
        raise Unmeasured("checker numeric commissioning controls are incomplete")
    quantizer = report.get("intermediate_quantizer_case", {})
    if (
        quantizer.get("status") != "PASS"
        or quantizer.get("native_expectations_match") is not True
        or quantizer.get("green", {}).get("observed_violations") != 0
        or quantizer.get("red", {}).get("observed_violations") != 1
    ):
        raise Unmeasured("checker native-quantizer commissioning is incomplete")
    crop = report.get("crop_origin_case", {})
    if (
        crop.get("correct", {}).get("status") != "PASS"
        or crop.get("correct", {}).get("observed_violations") != 0
        or crop.get("wrong", {}).get("status") != "PASS"
        or crop.get("wrong", {}).get("observed_violations") != 6
    ):
        raise Unmeasured("checker crop-origin commissioning is incomplete")
    green_names = {
        "convex_bilinear_green",
        "copy_green",
        "unrepresentable_high_at_rail_green",
        "unrepresentable_low_at_rail_green",
        "intermediate_quantizer_green",
        "crop_origin_correct",
    }
    red_names = {
        "in_range_high_red",
        "in_range_low_red",
        "unrepresentable_high_off_rail_red",
        "unrepresentable_low_off_rail_red",
        "intermediate_quantizer_red",
        "crop_origin_wrong",
    }
    directions = report.get("direction_controls", {})
    for label, names in (("green", green_names), ("red", red_names)):
        control = directions.get(label, {})
        if (
            control.get("expected") != len(names)
            or control.get("passed") != len(names)
            or set(control.get("controls", [])) != names
        ):
            raise Unmeasured(f"checker {label} direction commissioning is incomplete")
    counts = report.get("violation_count_controls", {})
    if counts.get("expected") != {"zero": 6, "one": 5, "six": 1} or counts.get(
        "observed"
    ) != {"zero": 6, "one": 5, "six": 1}:
        raise Unmeasured("checker violation-count commissioning is incomplete")
    m8r = report.get("m8_r_kernel_cases", {})
    required_m8r = {
        "catmull_hard_step": {
            "denominator": 252,
            "lower_violations": 14,
            "upper_violations": 14,
            "violations": 28,
        },
        "clamped_hard_step": {
            "denominator": 252,
            "lower_violations": 0,
            "upper_violations": 0,
            "violations": 0,
        },
        "widened_clamp_sabotage": {
            "denominator": 252,
            "lower_violations": 14,
            "upper_violations": 14,
            "violations": 28,
        },
        "explicit_high_low": {
            "denominator": 252,
            "lower_violations": 1,
            "upper_violations": 1,
            "violations": 2,
        },
    }
    if any(
        m8r.get("arms", {}).get(name) != expected
        for name, expected in required_m8r.items()
    ) or any(
        m8r.get("arms", {}).get(name, {}).get("violations") != 0
        for name in ("copy_null", "clamped_copy_null", "convex_bilinear_null")
    ):
        raise Unmeasured("checker M8-R commissioning is incomplete")
    if report.get("violation_evidence") != evidence_file.path.name:
        raise Unmeasured("checker report does not name the frozen violation evidence")
    if (
        evidence.get("schema") != "m136-checker-commissioning-violation-evidence"
        or evidence.get("schema_version") != 1
        or not isinstance(evidence.get("rows"), list)
        or evidence.get("row_count") != len(evidence["rows"])
        or evidence["row_count"]
        != sum(
            counts.get("observed", {}).get(key, 0) * n
            for key, n in (("one", 1), ("six", 6))
        )
    ):
        raise Unmeasured("checker commissioning violation evidence is incomplete")
    for row in evidence["rows"]:
        if (
            not isinstance(row, Mapping)
            or row.get("direction") not in (-1, 1)
            or row.get("q") != FINAL_Q
        ):
            raise Unmeasured("checker commissioning violation row is malformed")
    return {
        "report": {"path": str(report_file.path), "sha256": report_file.sha256},
        "violation_evidence": {
            "path": str(evidence_file.path),
            "sha256": evidence_file.sha256,
            "rows": evidence["row_count"],
        },
        "green_controls": 6,
        "red_controls": 6,
        "crop_correct_origin_violations": 0,
    }


def fresh_checker_commission(
    checker: FrozenFile,
    fixture_manifest: FrozenFile,
    report_file: FrozenFile,
    evidence_file: FrozenFile,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise Unmeasured(f"checker commission recheck output exists: {output_dir}")
    command = [
        sys.executable,
        str(checker.path),
        "commission",
        "--fixtures",
        str(fixture_manifest.path.parent),
        "--output",
        str(output_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=checker.path.parent,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise Unmeasured(
            "fresh checker commissioning failed: "
            f"exit={completed.returncode}; stderr={completed.stderr[-2000:]}"
        )
    fresh_report = output_dir / report_file.path.name
    fresh_evidence = output_dir / evidence_file.path.name
    if not fresh_report.is_file() or not fresh_evidence.is_file():
        raise Unmeasured("fresh checker commissioning omitted required artifacts")
    if fresh_report.read_bytes() != report_file.path.read_bytes():
        raise Disagreement(
            "fresh checker commissioning report differs from frozen report"
        )
    if fresh_evidence.read_bytes() != evidence_file.path.read_bytes():
        raise Disagreement(
            "fresh checker commissioning evidence differs from frozen evidence"
        )
    return {
        "command": command,
        "output": str(output_dir.resolve()),
        "report_sha256": sha256_file(fresh_report),
        "evidence_sha256": sha256_file(fresh_evidence),
        "byte_identical": True,
    }


def fresh_checker_fixture(
    fixture_tool: FrozenFile,
    preregistration: FrozenFile,
    fixture_manifest: FrozenFile,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise Unmeasured(f"checker fixture recheck output exists: {output_dir}")
    command = [
        sys.executable,
        str(fixture_tool.path),
        "commission",
        "--preregistration",
        str(preregistration.path),
        "--output",
        str(output_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=fixture_tool.path.parent,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise Unmeasured(
            "fresh checker fixture generation failed: "
            f"exit={completed.returncode}; stderr={completed.stderr[-2000:]}"
        )
    expected_dir = fixture_manifest.path.parent
    expected_files = {
        path.relative_to(expected_dir).as_posix(): path
        for path in expected_dir.rglob("*")
        if path.is_file()
    }
    fresh_files = {
        path.relative_to(output_dir).as_posix(): path
        for path in output_dir.rglob("*")
        if path.is_file()
    }
    if set(expected_files) != set(fresh_files):
        raise Disagreement(
            "fresh checker fixture inventory differs from frozen fixture"
        )
    for name, expected in expected_files.items():
        if expected.read_bytes() != fresh_files[name].read_bytes():
            raise Disagreement(f"fresh checker fixture differs at {name}")
    return {
        "command": command,
        "output": str(output_dir.resolve()),
        "files": len(expected_files),
        "byte_identical": True,
    }


def build_relevant_source_files(source_root: Path) -> set[str]:
    if (
        not (source_root / "Cargo.toml").is_file()
        or not (source_root / "crates").is_dir()
    ):
        raise Unmeasured(f"{source_root}: source snapshot lacks Cargo.toml or crates/")
    paths: set[str] = set()
    for top_level in source_root.iterdir():
        if top_level.name.lower() in BUILD_OUTPUT_DIRECTORIES:
            continue
        candidates = [top_level]
        if top_level.is_dir() and not top_level.is_symlink():
            candidates.extend(top_level.rglob("*"))
        for path in candidates:
            relative = path.relative_to(source_root)
            if path.is_symlink():
                raise Unmeasured(f"source snapshot contains a symlink: {relative}")
            if path.is_file():
                paths.add(relative.as_posix())
    return paths


def git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def committed_source_blobs(repository: Path, commit: str) -> dict[str, str]:
    command = [
        "git",
        "-C",
        str(repository),
        "ls-tree",
        "-r",
        "-z",
        commit,
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise Unmeasured(
            "source commit cannot be enumerated: "
            + completed.stderr.decode("utf-8", "replace")[-2000:]
        )
    blobs: dict[str, str] = {}
    for record in completed.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, object_id = metadata.decode("ascii").split(" ")
            relative = raw_path.decode("utf-8")
        except Exception as error:
            raise Unmeasured(
                "git ls-tree returned malformed source evidence"
            ) from error
        if kind != "blob" or mode == "120000":
            raise Unmeasured(f"unsupported build-source tree entry: {relative}")
        blobs[relative] = object_id.lower()
    return blobs


def git_blob_sha256(repository: Path, object_id: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository), "cat-file", "blob", object_id],
        check=False,
        capture_output=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise Unmeasured(f"cannot read source-commit blob {object_id}")
    return hashlib.sha256(completed.stdout).hexdigest().upper()


def verify_source_patch(
    file: FrozenFile,
    source_root: Path,
    source_commit: str,
    source_hashes: Mapping[str, str],
    source_tree_summary: Mapping[str, Any],
    hook: FrozenFile,
) -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[2]
    try:
        resolved_commit = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "rev-parse",
                "--verify",
                f"{source_commit}^{{commit}}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except OSError as error:
        raise Unmeasured("git is unavailable for source-patch verification") from error
    if (
        resolved_commit.returncode != 0
        or resolved_commit.stdout.strip().lower() != source_commit.lower()
    ):
        raise Unmeasured(
            "registered source commit is not an immutable repository commit"
        )
    committed = committed_source_blobs(repository, source_commit)
    snapshot_paths = set(source_hashes)
    missing = sorted(set(committed) - snapshot_paths)
    if missing:
        raise Unmeasured(
            f"source snapshot deleted build-relevant commit files: {missing[:8]}"
        )
    changed: dict[str, dict[str, Any]] = {}
    for relative in sorted(snapshot_paths):
        payload = (source_root / Path(relative)).read_bytes()
        after_blob = git_blob_sha1(payload)
        before_blob = committed.get(relative)
        if before_blob == after_blob:
            continue
        changed[relative] = {
            "path": relative,
            "kind": "added" if before_blob is None else "modified",
            "base_git_blob_sha1": before_blob,
            "base_sha256": (
                None
                if before_blob is None
                else git_blob_sha256(repository, before_blob)
            ),
            "snapshot_git_blob_sha1": after_blob,
            "snapshot_sha256": source_hashes[relative],
        }
    try:
        document = json.loads(file.path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(f"invalid source patch manifest {file.path}") from error
    if (
        not isinstance(document, Mapping)
        or document.get("schema") != "m136-source-patch-v1"
        or document.get("schema_version") != 1
        or document.get("protocol") != PROTOCOL
        or set(document) != SOURCE_PATCH_FIELDS
        or document.get("source_commit", "").lower() != source_commit.lower()
        or Path(str(document.get("source_root", ""))).resolve(strict=True)
        != source_root
        or Path(str(document.get("destination", ""))).resolve(strict=True)
        != source_root
        or Path(str(document.get("repository", ""))).resolve(strict=True) != repository
    ):
        raise Unmeasured("source patch manifest identity is invalid")
    rows = document.get("changed_files")
    if not isinstance(rows, list):
        raise Unmeasured("source patch manifest changed_files is absent")
    declared: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise Unmeasured("source patch row is not an object")
        relative = str(row.get("path", "")).replace("\\", "/")
        if not relative or relative in declared:
            raise Unmeasured("source patch path is empty or duplicated")
        declared[relative] = row
    if declared != changed:
        raise Disagreement(
            "source patch manifest does not match immutable git evidence"
        )
    if set(changed) != APPROVED_SOURCE_PATCH_PATHS:
        missing = sorted(APPROVED_SOURCE_PATCH_PATHS - set(changed))
        extra = sorted(set(changed) - APPROVED_SOURCE_PATCH_PATHS)
        raise Disagreement(
            f"source patch differs from the preregistered candidate arm: "
            f"missing={missing}, extra={extra}"
        )
    expected_changed_paths = sorted(changed)
    expected_after = {
        relative: row["snapshot_sha256"] for relative, row in sorted(changed.items())
    }
    expected_before = {
        relative: row["base_sha256"]
        for relative, row in sorted(changed.items())
        if row["base_sha256"] is not None
    }
    expected_patched_tree = {
        "files": source_tree_summary["files"],
        "bytes": source_tree_summary["bytes"],
        "manifest_sha256": source_tree_summary["tree_sha256"],
    }
    if (
        document.get("changed_paths") != expected_changed_paths
        or document.get("after_sha256") != expected_after
        or document.get("frozen_before_sha256") != expected_before
        or document.get("source_tree") != M130_SOURCE_TREE
        or document.get("patched_tree") != expected_patched_tree
        or document.get("manifest_algorithm")
        != "SHA-256 over sorted UTF-8 JSON lines [relative_posix_path,bytes,file_sha256]"
    ):
        raise Disagreement("source patch summary does not match the frozen source tree")
    trace_hook = document.get("trace_hook")
    if (
        not isinstance(trace_hook, Mapping)
        or Path(str(trace_hook.get("source", ""))).resolve(strict=True) != hook.path
        or str(trace_hook.get("sha256", "")).upper() != hook.sha256
    ):
        raise Disagreement("source patch trace hook differs from the frozen instrument")
    return {
        "path": str(file.path),
        "sha256": file.sha256,
        "repository": str(repository),
        "source_commit": source_commit,
        "changed_files": list(changed.values()),
        "patched_tree": expected_patched_tree,
    }


def verify_reproducible_build(
    receipt_file: FrozenFile,
    *,
    source_root: Path,
    source_commit: str,
    source_manifest: FrozenFile,
    source_patch: FrozenFile,
    candidate_binary: FrozenFile,
    rebuild_target: Path,
) -> dict[str, Any]:
    try:
        receipt = json.loads(receipt_file.path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(f"invalid build receipt {receipt_file.path}") from error
    if (
        not isinstance(receipt, Mapping)
        or receipt.get("schema") != "m136-build-receipt-v1"
        or receipt.get("schema_version") != 1
        or receipt.get("protocol") != PROTOCOL
        or set(receipt) != BUILD_RECEIPT_FIELDS
        or receipt.get("source_commit", "").lower() != source_commit.lower()
        or receipt.get("exit_code") != 0
    ):
        raise Unmeasured("candidate build receipt identity is invalid")
    try:
        receipt_source_root = Path(str(receipt.get("source_root", ""))).resolve(
            strict=True
        )
    except Exception as error:
        raise Unmeasured("candidate build receipt source root is absent") from error
    if receipt_source_root != source_root:
        raise Disagreement("candidate build receipt names another source root")
    require_frozen_reference(
        receipt.get("source_manifest"),
        source_manifest,
        "candidate build source manifest",
    )
    require_frozen_reference(
        receipt.get("source_patch"), source_patch, "candidate build source patch"
    )
    require_frozen_reference(
        receipt.get("candidate_binary"),
        candidate_binary,
        "candidate build binary",
    )
    cargo = frozen_file(receipt.get("cargo", {}), "candidate build cargo")
    rustc = frozen_file(receipt.get("rustc", {}), "candidate build rustc")
    build_log = frozen_file(receipt.get("build_log", {}), "candidate build log")
    if build_log.path.stat().st_size == 0:
        raise Unmeasured("candidate build log is empty")
    environment = receipt.get("environment")
    repository = Path(__file__).resolve().parents[2]
    try:
        commit_epoch_result = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "show",
                "-s",
                "--format=%ct",
                source_commit,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except OSError as error:
        raise Unmeasured("git is unavailable for build-receipt verification") from error
    commit_epoch = commit_epoch_result.stdout.strip()
    expected_build_id = m136_build_id(source_commit, source_manifest.sha256)
    if (
        not isinstance(environment, Mapping)
        or set(environment) != BUILD_ENVIRONMENT_KEYS
        or environment.get("CARGO_BUILD_JOBS") != "4"
        or environment.get("CARGO_INCREMENTAL") != "0"
        or environment.get("RUSTC") != str(rustc.path)
        or environment.get("RUSTFLAGS") != ""
        or environment.get("STREHL_BUILD_ID") != expected_build_id
        or not all(isinstance(value, str) for value in environment.values())
        or commit_epoch_result.returncode != 0
        or re.fullmatch(r"\d+", commit_epoch) is None
        or environment.get("SOURCE_DATE_EPOCH") != commit_epoch
    ):
        raise Unmeasured("candidate build environment is incomplete or unexpected")
    original_target = candidate_binary.path.parent.parent
    expected_command = [
        str(cargo.path),
        "build",
        "--release",
        "--locked",
        "--offline",
        "-p",
        "strehl-cli",
        "-j",
        "4",
        "--manifest-path",
        str(source_root / "Cargo.toml"),
        "--target-dir",
        str(original_target),
    ]
    if receipt.get("command") != expected_command:
        raise Disagreement("candidate build command is not the frozen command")
    for field in ("started_utc", "completed_utc"):
        if not isinstance(receipt.get(field), str) or not receipt[field]:
            raise Unmeasured(f"candidate build receipt omits {field}")
    version_commands = {
        "cargo_version": [str(cargo.path), "--version", "--verbose"],
        "rustc_version": [str(rustc.path), "-vV"],
    }
    for field, command in version_commands.items():
        completed = subprocess.run(
            command,
            cwd=source_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        observed = completed.stdout.strip()
        if completed.returncode != 0 or receipt.get(field) != observed:
            raise Unmeasured(f"candidate build {field} does not reproduce")
    if rebuild_target.exists():
        raise Unmeasured(f"independent rebuild target already exists: {rebuild_target}")
    rebuild_target.parent.mkdir(parents=True, exist_ok=True)
    rebuild_command = [
        str(cargo.path),
        *expected_command[1:-1],
        str(rebuild_target),
    ]
    environment_for_build = os.environ.copy()
    for key in list(environment_for_build):
        upper = key.upper()
        if (
            upper.startswith("CARGO")
            or upper.startswith("RUST")
            or upper.startswith("STREHL_")
        ):
            environment_for_build.pop(key)
    environment_for_build.update(
        {str(key): str(value) for key, value in environment.items()}
    )
    completed = subprocess.run(
        rebuild_command,
        cwd=source_root,
        env=environment_for_build,
        check=False,
        capture_output=True,
        timeout=3600,
    )
    rebuild_log = rebuild_target.with_name(rebuild_target.name + "-build.log")
    rebuild_log.write_bytes(completed.stdout + completed.stderr)
    if completed.returncode != 0:
        raise Unmeasured(
            f"independent candidate rebuild failed with exit {completed.returncode}"
        )
    rebuilt_binary = rebuild_target / "release" / candidate_binary.path.name
    if not rebuilt_binary.is_file():
        raise Unmeasured(f"independent rebuild omitted binary: {rebuilt_binary}")
    rebuilt_hash = sha256_file(rebuilt_binary)
    if rebuilt_hash != candidate_binary.sha256:
        raise Disagreement(
            "candidate binary is not reproducible from the frozen source snapshot"
        )
    assert_still_frozen(cargo, "cargo executable")
    assert_still_frozen(rustc, "rustc executable")
    assert_still_frozen(build_log, "candidate build log")
    return {
        "receipt": {"path": str(receipt_file.path), "sha256": receipt_file.sha256},
        "cargo": {"path": str(cargo.path), "sha256": cargo.sha256},
        "rustc": {"path": str(rustc.path), "sha256": rustc.sha256},
        "original_build_log": {
            "path": str(build_log.path),
            "sha256": build_log.sha256,
        },
        "environment": dict(environment),
        "source_commit_epoch": commit_epoch,
        "rebuild_command": rebuild_command,
        "rebuild_log": {
            "path": str(rebuild_log.resolve()),
            "sha256": sha256_file(rebuild_log),
        },
        "rebuilt_binary": {
            "path": str(rebuilt_binary.resolve()),
            "sha256": rebuilt_hash,
        },
        "matches_candidate": True,
    }


def verify_instrument_freeze(
    file: FrozenFile,
    *,
    source_commit: str,
    preregistration: FrozenFile,
    source_root: Path,
    source_manifest: FrozenFile,
    source_patch: FrozenFile,
    build_receipt: FrozenFile,
    binary: FrozenFile,
    instruments: Mapping[str, FrozenFile],
    verifier: FrozenFile,
    verifier_commission: FrozenFile,
    fixture_manifest: FrozenFile,
    checker_commission_report: FrozenFile,
    checker_commission_evidence: FrozenFile,
) -> dict[str, Any]:
    try:
        document = json.loads(file.path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(f"invalid instrument freeze {file.path}") from error
    if (
        not isinstance(document, Mapping)
        or document.get("schema") != "m136-instrument-freeze-v1"
        or document.get("schema_version") != 1
        or document.get("protocol") != PROTOCOL
        or document.get("status") != "FROZEN_PRE_TARGET"
        or document.get("source_commit", "").lower() != source_commit.lower()
    ):
        raise Unmeasured("instrument freeze identity is invalid")
    if not isinstance(document.get("created_utc"), str) or not document["created_utc"]:
        raise Unmeasured("instrument freeze omits its creation timestamp")
    require_frozen_reference(
        document.get("preregistration"),
        preregistration,
        "instrument freeze preregistration",
    )
    snapshot = document.get("source_snapshot")
    if (
        not isinstance(snapshot, Mapping)
        or Path(str(snapshot.get("root", ""))).resolve(strict=True) != source_root
    ):
        raise Disagreement("instrument freeze source root mismatch")
    require_frozen_reference(
        snapshot.get("manifest"), source_manifest, "instrument freeze source manifest"
    )
    require_frozen_reference(
        snapshot.get("patch"), source_patch, "instrument freeze source patch"
    )
    require_frozen_reference(
        document.get("build_receipt"),
        build_receipt,
        "instrument freeze build receipt",
    )
    require_frozen_reference(
        document.get("candidate_binary"), binary, "instrument freeze binary"
    )
    frozen_instruments = document.get("instruments")
    if not isinstance(frozen_instruments, Mapping) or set(frozen_instruments) != (
        set(instruments) | {"verifier"}
    ):
        raise Unmeasured("instrument freeze instrument inventory is incomplete")
    for name, expected in {**instruments, "verifier": verifier}.items():
        require_frozen_reference(
            frozen_instruments.get(name),
            expected,
            f"instrument freeze {name}",
        )
    commissioning = document.get("commissioning")
    if not isinstance(commissioning, Mapping) or set(commissioning) != {
        "verifier_report",
        "fixture_manifest",
        "checker_report",
        "checker_violation_evidence",
    }:
        raise Unmeasured("instrument freeze commissioning inventory is incomplete")
    for name, expected in {
        "verifier_report": verifier_commission,
        "fixture_manifest": fixture_manifest,
        "checker_report": checker_commission_report,
        "checker_violation_evidence": checker_commission_evidence,
    }.items():
        require_frozen_reference(
            commissioning.get(name),
            expected,
            f"instrument freeze commissioning {name}",
        )
    versions = document.get("versions")
    if (
        not isinstance(versions, Mapping)
        or not versions
        or any(not isinstance(value, str) or not value for value in versions.values())
    ):
        raise Unmeasured("instrument freeze tool versions are absent")
    return {
        "path": str(file.path),
        "sha256": file.sha256,
        "status": "FROZEN_PRE_TARGET",
        "created_utc": document["created_utc"],
        "versions": dict(versions),
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
    if (
        document.get("schema") != SOURCE_MANIFEST_SCHEMA
        or document.get("schema_version") != 1
        or set(document) != SOURCE_MANIFEST_FIELDS
    ):
        raise Unmeasured(f"source manifest schema must be {SOURCE_MANIFEST_SCHEMA!r}")
    if str(document.get("source_commit", "")).lower() != expected_commit.lower():
        raise Unmeasured("source manifest commit differs from registered source commit")
    try:
        declared_root = Path(str(document.get("source_root", ""))).resolve(strict=True)
    except Exception as error:
        raise Unmeasured("source manifest root is absent") from error
    if declared_root != source_root:
        raise Disagreement("source manifest names another source snapshot")
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
    total_bytes = 0
    tree_digest = hashlib.sha256()
    for relative, raw in sorted(declared.items()):
        path = (source_root / Path(relative)).resolve()
        try:
            common = os.path.commonpath(
                [os.path.normcase(str(source_root)), os.path.normcase(str(path))]
            )
        except ValueError as error:
            raise Unmeasured(
                f"source manifest path escapes root: {relative}"
            ) from error
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
        total_bytes += expected_bytes
        tree_digest.update(
            (
                json.dumps(
                    [relative, expected_bytes, actual_hash],
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            ).encode("utf-8")
        )
    observed_tree_hash = tree_digest.hexdigest().upper()
    if (
        document.get("file_count") != len(observed)
        or document.get("total_bytes") != total_bytes
        or str(document.get("tree_sha256", "")).upper() != observed_tree_hash
    ):
        raise Unmeasured("source snapshot manifest totals or tree digest are wrong")
    observed_tree = {
        "files": len(observed),
        "bytes": total_bytes,
        "manifest_sha256": observed_tree_hash,
    }
    if observed_tree != APPROVED_CANDIDATE_SOURCE_TREE:
        raise Disagreement(
            "source snapshot is not the prospectively approved candidate tree"
        )
    compiled_hook_path = "crates/strehl-cli/src/m8_trace_v3.rs"
    if observed.get(compiled_hook_path) != hook_hash:
        raise Unmeasured(
            "compiled source snapshot hook does not match the registered "
            "experiments/M136-m8o-bar/m8_trace_v3.rs"
        )
    return {
        "path": str(file.path),
        "sha256": file.sha256,
        "source_commit": expected_commit,
        "files": len(observed),
        "bytes": total_bytes,
        "tree_sha256": observed_tree_hash,
        "file_sha256": observed,
        "compiled_hook_path": compiled_hook_path,
    }


def validate_input_fingerprint(
    before: FrozenFile,
    after: FrozenFile,
    input_dir: Path,
) -> dict[str, Any]:
    documents: list[Mapping[str, Any]] = []
    for label, frozen, phase in (
        ("before", before, "before-render"),
        ("after", after, "after-census"),
    ):
        try:
            document = json.loads(frozen.path.read_text(encoding="utf-8"))
        except Exception as error:
            raise Unmeasured(f"{label} input fingerprint is unreadable") from error
        if (
            not isinstance(document, Mapping)
            or document.get("schema") != "m136-input-fingerprint-v1"
            or document.get("schema_version") != 1
            or document.get("phase") != phase
        ):
            raise Unmeasured(f"{label} input fingerprint has an unsupported schema")
        try:
            recorded_root = Path(str(document.get("root", ""))).resolve(strict=True)
        except Exception as error:
            raise Unmeasured(f"{label} input fingerprint root is absent") from error
        if recorded_root != input_dir:
            raise Disagreement(f"{label} input fingerprint names another root")
        documents.append(document)

    def indexed(
        document: Mapping[str, Any], label: str
    ) -> dict[str, Mapping[str, Any]]:
        rows = document.get("files")
        if not isinstance(rows, list):
            raise Unmeasured(f"{label} input fingerprint files are absent")
        result: dict[str, Mapping[str, Any]] = {}
        total = 0
        for row in rows:
            if not isinstance(row, Mapping):
                raise Unmeasured(f"{label} input fingerprint row is malformed")
            relative = str(row.get("path", "")).replace("\\", "/")
            path = Path(relative)
            if (
                not relative
                or path.is_absolute()
                or ".." in path.parts
                or relative in result
            ):
                raise Unmeasured(f"{label} input fingerprint path is invalid")
            size = row.get("bytes")
            ticks = row.get("last_write_utc_ticks")
            digest = str(row.get("sha256", "")).upper()
            if (
                not isinstance(size, int)
                or isinstance(size, bool)
                or size < 0
                or not isinstance(ticks, int)
                or isinstance(ticks, bool)
                or ticks < 0
                or re.fullmatch(r"[0-9A-F]{64}", digest) is None
            ):
                raise Unmeasured(f"{label} input fingerprint metadata is invalid")
            result[relative] = {
                "path": relative,
                "bytes": size,
                "last_write_utc_ticks": ticks,
                "sha256": digest,
            }
            total += size
        if (
            document.get("file_count") != len(result)
            or document.get("total_bytes") != total
        ):
            raise Unmeasured(f"{label} input fingerprint totals are wrong")
        return result

    before_rows = indexed(documents[0], "before")
    after_rows = indexed(documents[1], "after")
    if before_rows != after_rows:
        raise Disagreement("input fingerprint changed between render boundaries")
    current_paths = {
        path.relative_to(input_dir).as_posix(): path
        for path in input_dir.rglob("*")
        if path.is_file()
    }
    if set(current_paths) != set(before_rows):
        raise Disagreement("current input inventory differs from frozen fingerprints")
    for relative, path in current_paths.items():
        if path.is_symlink():
            raise Unmeasured(f"input fingerprint refuses symlink: {relative}")
        expected = before_rows[relative]
        current_ticks = path.stat().st_mtime_ns // 100 + 621355968000000000
        if (
            path.stat().st_size != expected["bytes"]
            or current_ticks != expected["last_write_utc_ticks"]
            or sha256_file(path) != expected["sha256"]
        ):
            raise Disagreement(f"current input file changed: {relative}")
    return {
        "before": {"path": str(before.path), "sha256": before.sha256},
        "after": {"path": str(after.path), "sha256": after.sha256},
        "files": len(before_rows),
        "bytes": sum(row["bytes"] for row in before_rows.values()),
        "unchanged": True,
    }


def validate_render_provenance(
    file: FrozenFile,
    *,
    capture: str,
    source_commit: str,
    binary: FrozenFile,
    input_dir: Path,
    output_tiff: FrozenFile,
    warpmap: FrozenFile,
    trace_state: Path,
    environment: Mapping[str, str],
    input_fingerprint_before: FrozenFile,
    instrument_freeze: FrozenFile,
) -> dict[str, Any]:
    try:
        document = json.loads(file.path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(f"{capture}: render provenance is unreadable") from error
    if (
        not isinstance(document, Mapping)
        or document.get("schema") != "m136-render-provenance-v1"
        or document.get("schema_version") != 1
        or document.get("protocol") != PROTOCOL
        or document.get("capture") != capture
        or document.get("source_commit") != source_commit.lower()
        or document.get("exit_code") != 0
    ):
        raise Unmeasured(f"{capture}: render provenance identity is invalid")
    require_frozen_reference(
        document.get("candidate_binary"), binary, f"{capture} render binary"
    )
    require_frozen_reference(
        document.get("warpmap"), warpmap, f"{capture} render warpmap"
    )
    require_frozen_reference(
        document.get("output_tiff"), output_tiff, f"{capture} render output"
    )
    require_frozen_reference(
        document.get("input_fingerprint_before"),
        input_fingerprint_before,
        f"{capture} render input fingerprint",
    )
    require_frozen_reference(
        document.get("instrument_freeze"),
        instrument_freeze,
        f"{capture} render instrument freeze",
    )
    if instrument_freeze.path.stat().st_mtime_ns > output_tiff.path.stat().st_mtime_ns:
        raise Unmeasured(f"{capture}: instrument freeze postdates target TIFF")
    try:
        recorded_input = Path(str(document.get("input_dir", ""))).resolve(strict=True)
        recorded_trace = Path(str(document.get("trace_state", ""))).resolve(strict=True)
    except Exception as error:
        raise Unmeasured(f"{capture}: render provenance path is absent") from error
    if recorded_input != input_dir or recorded_trace != trace_state:
        raise Disagreement(f"{capture}: render provenance path mismatch")
    if document.get("environment") != dict(environment):
        raise Disagreement(f"{capture}: render environment mismatch")
    expected_command = [
        str(binary.path),
        "stack",
        str(input_dir),
        "--out",
        str(output_tiff.path),
        "--merge",
        "pyramid",
        "--cover",
        "crop",
        "--resampler",
        "clamped-catmull",
        "--fix-ca",
        "off",
    ]
    if document.get("command") != expected_command:
        raise Disagreement(f"{capture}: render command differs from preregistration")
    for field in ("started_utc", "completed_utc"):
        if not isinstance(document.get(field), str) or not document[field]:
            raise Unmeasured(f"{capture}: render provenance omits {field}")
    return {
        "path": str(file.path),
        "sha256": file.sha256,
        "command": expected_command,
        "environment": dict(environment),
        "exit_code": 0,
    }


def verify_manifest(
    manifest_path: Path, report_path: Path, chunk_rows: int
) -> tuple[int, dict[str, Any]]:
    repository = Path(__file__).resolve().parents[2]
    allowed_output_roots = (
        Path(__file__).with_name("out").resolve(),
        (repository / "experiments" / "M142-m8o-execute" / "out").resolve(),
    )
    matching_roots = [
        root
        for root in allowed_output_roots
        if path_is_within(manifest_path, root) and path_is_within(report_path, root)
    ]
    if len(matching_roots) != 1:
        raise Unmeasured(
            "verifier manifest and report must share an approved M136/M142 output root"
        )
    output_root = matching_roots[0]
    require_under(manifest_path, output_root, "verifier manifest")
    require_under(report_path, output_root, "verifier report")
    manifest_file_hash = sha256_file(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Unmeasured(f"invalid verifier manifest {manifest_path}") from error
    if (
        not isinstance(manifest, Mapping)
        or manifest.get("schema") != MANIFEST_SCHEMA
        or manifest.get("protocol") != VERIFIER_PROTOCOL
        or set(manifest) != VERIFIER_MANIFEST_FIELDS
    ):
        raise Unmeasured(
            f"manifest must use schema {MANIFEST_SCHEMA!r} and exact frozen fields"
        )
    if not isinstance(manifest.get("created_utc"), str) or not manifest["created_utc"]:
        raise Unmeasured("verifier manifest omits its creation timestamp")

    prereg_file = require_absolute_existing_file(
        str(manifest.get("preregistration", "")), "preregistration"
    )
    prereg_hash = sha256_file(prereg_file)
    prereg_canonical_hash = sha256_canonical_text(prereg_file)
    frozen_prereg = (
        Path(__file__).with_name("clamped-m8o-preregistration.json").resolve()
    )
    if prereg_file != frozen_prereg:
        raise Unmeasured(
            f"preregistration must be the frozen repository file {frozen_prereg}"
        )
    if prereg_canonical_hash != PREREG_CANONICAL_SHA256:
        raise Unmeasured(
            "frozen preregistration canonical hash mismatch: expected "
            f"{PREREG_CANONICAL_SHA256}, observed {prereg_canonical_hash}"
        )
    prereg = json.loads(prereg_file.read_text(encoding="utf-8"))
    if prereg.get("protocol") != PROTOCOL:
        raise Unmeasured("preregistration protocol mismatch")
    decision = prereg.get("decision", {})
    if decision.get("example_40") != "V=40 is FAIL." or "V=0" not in str(
        decision.get("m8_o_pass", "")
    ):
        raise Unmeasured(
            "preregistration decision rule is not the frozen exact-zero rule"
        )
    interpretation_path = (
        Path(__file__).with_name("prospective-interpretations.md").resolve()
    )
    if not interpretation_path.is_file():
        raise Unmeasured(f"prospective interpretation is absent: {interpretation_path}")
    interpretation_hash = sha256_file(interpretation_path)
    interpretation_canonical_hash = sha256_canonical_text(interpretation_path)
    if interpretation_canonical_hash != INTERPRETATION_CANONICAL_SHA256:
        raise Unmeasured(
            "prospective interpretation bytes differ from the pre-target ruling"
        )
    verifier_path = Path(__file__).resolve()
    verifier_hash = sha256_file(verifier_path)
    verifier_canonical_hash = sha256_canonical_text(verifier_path)
    commission_file = frozen_file(
        manifest.get("commission_report", {}), "verifier commissioning report"
    )
    expected_commission_path = verifier_path.with_name("verifier-commission.json")
    if commission_file.path != expected_commission_path:
        raise Unmeasured(
            f"commission report must be the frozen repository artifact "
            f"{expected_commission_path}"
        )
    commission_evidence = validate_commission_report(
        commission_file,
        prereg_canonical_hash,
        interpretation_canonical_hash,
        verifier_canonical_hash,
    )
    recheck_path = report_path.with_name(report_path.stem + "-commission-recheck.json")
    if recheck_path.exists():
        raise Unmeasured(f"commission recheck output already exists: {recheck_path}")
    recheck_work = output_root / "v"
    recheck = commission(prereg_file, recheck_path, recheck_work)
    frozen_commission = json.loads(commission_file.path.read_text(encoding="utf-8"))
    if recheck != frozen_commission:
        raise Unmeasured(
            "fresh commissioning does not reproduce the frozen commissioning report"
        )
    commission_evidence["fresh_recheck"] = {
        "path": str(recheck_path.resolve()),
        "sha256": sha256_file(recheck_path),
        "byte_identical": recheck_path.read_bytes()
        == commission_file.path.read_bytes(),
    }
    if not commission_evidence["fresh_recheck"]["byte_identical"]:
        raise Unmeasured(
            "fresh commissioning report is not byte-identical to frozen report"
        )

    source_root = require_absolute_existing_dir(
        str(manifest.get("source_root", "")), "source_root"
    )
    expected_commit = str(manifest.get("source_commit", ""))
    if expected_commit != M130_SOURCE_COMMIT:
        raise Unmeasured(
            "source_commit is not the preregistered post-M130 commit "
            f"{M130_SOURCE_COMMIT}"
        )
    binary = frozen_file(manifest.get("binary", {}), "candidate binary")
    instruments = parse_instruments(manifest.get("instruments"))
    fixture_manifest = frozen_file(
        manifest.get("checker_fixture_manifest", {}),
        "checker fixture manifest",
    )
    checker_commission_raw = manifest.get("checker_commission_artifacts")
    if not isinstance(checker_commission_raw, Mapping) or set(
        checker_commission_raw
    ) != {"report", "violation_evidence"}:
        raise Unmeasured(
            "checker_commission_artifacts must contain report and violation_evidence"
        )
    checker_commission_report = frozen_file(
        checker_commission_raw["report"], "checker commissioning report"
    )
    checker_commission_violation_evidence = frozen_file(
        checker_commission_raw["violation_evidence"],
        "checker commissioning violation evidence",
    )
    if (
        checker_commission_report.path.name != "commissioning.json"
        or checker_commission_violation_evidence.path.name != "violation-evidence.json"
        or checker_commission_report.path.parent
        != checker_commission_violation_evidence.path.parent
    ):
        raise Unmeasured("checker commissioning artifact paths are not canonical")
    checker_fixture_evidence = validate_checker_fixture(
        fixture_manifest,
        FrozenFile(prereg_file, prereg_hash),
        prereg,
    )
    checker_commission_evidence = validate_checker_commission_artifacts(
        checker_commission_report,
        checker_commission_violation_evidence,
        checker=instruments["checker"],
        fixture_manifest=fixture_manifest,
        preregistration=FrozenFile(prereg_file, prereg_hash),
    )
    checker_fixture_recheck_dir = report_path.with_name(
        report_path.stem + "-checker-fixture-recheck"
    )
    checker_fixture_evidence["fresh_recheck"] = fresh_checker_fixture(
        instruments["fixture"],
        FrozenFile(prereg_file, prereg_hash),
        fixture_manifest,
        checker_fixture_recheck_dir,
    )
    checker_recheck_dir = report_path.with_name(
        report_path.stem + "-checker-commission-recheck"
    )
    checker_commission_evidence["fresh_recheck"] = fresh_checker_commission(
        instruments["checker"],
        fixture_manifest,
        checker_commission_report,
        checker_commission_violation_evidence,
        checker_recheck_dir,
    )
    source_manifest = frozen_file(
        manifest.get("source_manifest", {}), "source snapshot manifest"
    )
    source_evidence = verify_source_manifest(
        source_manifest, source_root, expected_commit, instruments["hook"].sha256
    )
    source_patch = frozen_file(
        manifest.get("source_patch", {}), "source patch manifest"
    )
    source_patch_evidence = verify_source_patch(
        source_patch,
        source_root,
        expected_commit,
        source_evidence["file_sha256"],
        source_evidence,
        instruments["hook"],
    )
    try:
        binary_common = os.path.commonpath(
            [os.path.normcase(str(source_root)), os.path.normcase(str(binary.path))]
        )
    except ValueError as error:
        raise Unmeasured(
            "candidate binary is outside the source snapshot volume"
        ) from error
    if os.path.normcase(binary_common) != os.path.normcase(str(source_root)):
        raise Unmeasured("candidate binary is outside the source snapshot")
    binary_relative = binary.path.relative_to(source_root)
    if (
        len(binary_relative.parts) != 3
        or binary_relative.parts[0].lower() != "target-m136"
        or binary_relative.parts[1].lower() != "release"
    ):
        raise Unmeasured(
            "candidate binary must be source_root\\target-m136\\release\\<binary>"
        )
    build_receipt = frozen_file(
        manifest.get("build_receipt", {}), "candidate build receipt"
    )
    instrument_freeze_file = frozen_file(
        manifest.get("instrument_freeze", {}), "instrument freeze"
    )
    instrument_freeze_evidence = verify_instrument_freeze(
        instrument_freeze_file,
        source_commit=expected_commit,
        preregistration=FrozenFile(prereg_file, prereg_hash),
        source_root=source_root,
        source_manifest=source_manifest,
        source_patch=source_patch,
        build_receipt=build_receipt,
        binary=binary,
        instruments=instruments,
        verifier=FrozenFile(verifier_path, verifier_hash),
        verifier_commission=commission_file,
        fixture_manifest=fixture_manifest,
        checker_commission_report=checker_commission_report,
        checker_commission_evidence=checker_commission_violation_evidence,
    )
    rebuild_target = report_path.with_name(report_path.stem + "-rebuild")
    build_evidence = verify_reproducible_build(
        build_receipt,
        source_root=source_root,
        source_commit=expected_commit,
        source_manifest=source_manifest,
        source_patch=source_patch,
        candidate_binary=binary,
        rebuild_target=rebuild_target,
    )
    if not (
        source_manifest.path.stat().st_mtime_ns <= build_receipt.path.stat().st_mtime_ns
        and source_patch.path.stat().st_mtime_ns
        <= build_receipt.path.stat().st_mtime_ns
        and binary.path.stat().st_mtime_ns
        <= build_receipt.path.stat().st_mtime_ns
        <= instrument_freeze_file.path.stat().st_mtime_ns
    ):
        raise Unmeasured("source/build/freeze timestamps are out of order")
    for label, path in (
        ("source root", source_root),
        ("source manifest", source_manifest.path),
        ("source patch", source_patch.path),
        ("build receipt", build_receipt.path),
        ("original build log", Path(build_evidence["original_build_log"]["path"])),
        ("candidate binary", binary.path),
        ("checker fixture", fixture_manifest.path),
        ("checker commission report", checker_commission_report.path),
        (
            "checker commission violation evidence",
            checker_commission_violation_evidence.path,
        ),
        ("instrument freeze", instrument_freeze_file.path),
    ):
        require_under(path, output_root, label)

    prereg_captures = {
        item["name"]: item for item in prereg.get("scope", {}).get("captures", [])
    }
    raw_captures = manifest.get("captures")
    if not isinstance(raw_captures, list) or not raw_captures:
        raise Unmeasured("manifest captures must be a non-empty list")
    if len(raw_captures) != len(prereg_captures) or {
        item.get("name") for item in raw_captures
    } != set(prereg_captures):
        raise Unmeasured("manifest capture set differs from preregistration")

    capture_results: list[dict[str, Any]] = []
    postflight_files: list[tuple[str, FrozenFile]] = []
    postflight_inputs: list[
        tuple[str, FrozenFile, FrozenFile, Path, dict[str, Any]]
    ] = []
    artifact_root = report_path.parent / (report_path.stem + "-artifacts")
    if artifact_root.exists():
        raise Unmeasured(f"verifier output directory already exists: {artifact_root}")
    artifact_root.mkdir(parents=True)
    for item in raw_captures:
        if not isinstance(item, Mapping) or set(item) != CAPTURE_MANIFEST_FIELDS:
            raise Unmeasured("capture entry must contain the exact frozen fields")
        name = str(item["name"])
        registered = prereg_captures[name]
        input_dir = require_absolute_existing_dir(
            str(item.get("input_dir", "")), f"{name} input"
        )
        if os.path.normcase(str(input_dir)) != os.path.normcase(
            str(Path(registered["input"]).resolve())
        ):
            raise Unmeasured(f"{name}: input directory differs from preregistration")
        warpmap_file = frozen_file(item.get("warpmap", {}), f"{name} warpmap")
        if warpmap_file.sha256 != str(registered["map_sha256"]).upper():
            raise Unmeasured(f"{name}: warpmap hash differs from preregistration")
        trace_state = require_absolute_existing_dir(
            str(item.get("trace_state", "")), f"{name} trace state"
        )
        checker_state = require_absolute_existing_dir(
            str(item.get("checker_state", "")), f"{name} checker state"
        )
        input_fingerprint_before = frozen_file(
            item.get("input_fingerprint_before", {}),
            f"{name} before-render input fingerprint",
        )
        input_fingerprint_after = frozen_file(
            item.get("input_fingerprint_after", {}),
            f"{name} after-census input fingerprint",
        )
        input_fingerprint_evidence = validate_input_fingerprint(
            input_fingerprint_before,
            input_fingerprint_after,
            input_dir,
        )
        output_file = frozen_file(item.get("output_tiff", {}), f"{name} output TIFF")
        raw_checker_artifacts = item.get("checker_artifacts")
        if (
            not isinstance(raw_checker_artifacts, Mapping)
            or set(raw_checker_artifacts) != REQUIRED_CHECKER_ARTIFACTS
        ):
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
            "lower_frame_witness",
            "upper_frame_witness",
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
                    [
                        os.path.normcase(str(checker_state)),
                        os.path.normcase(str(file.path)),
                    ]
                )
            except ValueError as error:
                raise Unmeasured(
                    f"{name}: checker artifact {label} is outside the state volume"
                ) from error
            if os.path.normcase(common) != os.path.normcase(str(checker_state)):
                raise Unmeasured(
                    f"{name}: checker artifact {label} is outside checker state directory"
                )
        required_environment = prereg.get("scope", {}).get("required_environment", {})
        if not isinstance(required_environment, Mapping):
            raise Unmeasured("preregistration required_environment is malformed")
        environment = {
            str(key): str(value) for key, value in required_environment.items()
        }
        substitutions = {
            "STREHL_M8_CAPTURE": name,
            "STREHL_M8_CHECKER": str(instruments["checker"].path),
            "STREHL_M8_FREEZE_SHA256": instrument_freeze_file.sha256,
            "STREHL_M8_TRACE_DIR": str(trace_state),
            "STREHL_WARPMAP": str(warpmap_file.path),
        }
        environment.update(substitutions)
        render_provenance_file = frozen_file(
            item.get("render_provenance", {}), f"{name} render provenance"
        )
        for label, path in (
            ("warpmap", warpmap_file.path),
            ("trace state", trace_state),
            ("checker state", checker_state),
            ("output TIFF", output_file.path),
            ("before input fingerprint", input_fingerprint_before.path),
            ("after input fingerprint", input_fingerprint_after.path),
            ("render provenance", render_provenance_file.path),
        ):
            require_under(path, output_root, f"{name} {label}")
        render_provenance_evidence = validate_render_provenance(
            render_provenance_file,
            capture=name,
            source_commit=expected_commit,
            binary=binary,
            input_dir=input_dir,
            output_tiff=output_file,
            warpmap=warpmap_file,
            trace_state=trace_state,
            environment=environment,
            input_fingerprint_before=input_fingerprint_before,
            instrument_freeze=instrument_freeze_file,
        )
        if not (
            instrument_freeze_file.path.stat().st_mtime_ns
            <= input_fingerprint_before.path.stat().st_mtime_ns
            <= output_file.path.stat().st_mtime_ns
            <= render_provenance_file.path.stat().st_mtime_ns
            <= input_fingerprint_after.path.stat().st_mtime_ns
        ):
            raise Unmeasured(
                f"{name}: freeze/fingerprint/render timestamps are out of order"
            )
        if any(
            file.path.stat().st_mtime_ns
            > input_fingerprint_after.path.stat().st_mtime_ns
            for file in checker_artifacts.values()
        ):
            raise Unmeasured(
                f"{name}: after-census fingerprint predates checker artifacts"
            )
        checker_context = {
            "candidate_binary": binary,
            "checker": instruments["checker"],
            "preregistration": FrozenFile(prereg_file, prereg_hash),
            "checker_commission": checker_commission_report,
            "fixture_manifest": fixture_manifest,
            "instrument_freeze": instrument_freeze_file,
            "warpmap": warpmap_file,
            "output_tiff": output_file,
            "source_commit": expected_commit,
            "environment": environment,
            "input_dir": input_dir,
            "trace_state": trace_state,
            "checker_state": checker_state,
        }
        capture_result = verify_capture(
            name,
            input_dir,
            warpmap_file,
            trace_state,
            output_file,
            artifact_root / name,
            chunk_rows,
            checker_artifacts,
            checker_context,
            instrument_freeze_file.sha256,
        )
        post_verification_fingerprint = validate_input_fingerprint(
            input_fingerprint_before,
            input_fingerprint_after,
            input_dir,
        )
        if post_verification_fingerprint != input_fingerprint_evidence:
            raise Disagreement(f"{name}: input fingerprint changed during verification")
        capture_result["input_fingerprint"] = input_fingerprint_evidence
        capture_result["render_provenance"] = render_provenance_evidence
        capture_results.append(capture_result)
        postflight_files.extend(
            [
                (f"{name} warpmap", warpmap_file),
                (f"{name} output TIFF", output_file),
                (f"{name} before input fingerprint", input_fingerprint_before),
                (f"{name} after input fingerprint", input_fingerprint_after),
                (f"{name} render provenance", render_provenance_file),
                *[
                    (f"{name} checker artifact {label}", file)
                    for label, file in checker_artifacts.items()
                ],
            ]
        )
        postflight_files.extend(
            (
                f"{name} trace {trace_name}",
                FrozenFile(trace_state / "blocks" / trace_name, digest),
            )
            for trace_name, digest in capture_result["evidence"]["trace_sha256"].items()
        )
        postflight_files.extend(
            (
                f"{name} source {source_path}",
                FrozenFile(Path(source_path), digest),
            )
            for source_path, digest in capture_result["evidence"][
                "source_sha256"
            ].items()
        )
        postflight_files.extend(
            (
                f"{name} ignored producer artifact {producer_path}",
                FrozenFile(Path(producer_path), digest),
            )
            for producer_path, digest in capture_result["evidence"][
                "ignored_producer_derived_artifacts"
            ].items()
        )
        postflight_inputs.append(
            (
                name,
                input_fingerprint_before,
                input_fingerprint_after,
                input_dir,
                input_fingerprint_evidence,
            )
        )

    aggregate_r_denominator = sum(
        item["m8_r"]["denominator"] for item in capture_results
    )
    aggregate_r_lower = sum(
        item["m8_r"]["lower_violations"] for item in capture_results
    )
    aggregate_r_upper = sum(
        item["m8_r"]["upper_violations"] for item in capture_results
    )
    aggregate_r_violations = sum(item["m8_r"]["violations"] for item in capture_results)
    aggregate_o_denominator = sum(
        item["m8_o"]["denominator"] for item in capture_results
    )
    aggregate_o_lower = sum(
        item["m8_o"]["lower_violations"] for item in capture_results
    )
    aggregate_o_upper = sum(
        item["m8_o"]["upper_violations"] for item in capture_results
    )
    aggregate_o_violations = sum(item["m8_o"]["violations"] for item in capture_results)
    aggregate_per_channel = {
        channel: {
            key: sum(
                item["m8_o"]["per_channel"][channel][key] for item in capture_results
            )
            for key in ("lower_violations", "upper_violations", "violations")
        }
        for channel in CHANNEL_NAMES
    }
    aggregate_max_positive = max(
        item["m8_o"]["maximum_positive_signed_excess"] for item in capture_results
    )
    aggregate_min_negative = min(
        item["m8_o"]["minimum_negative_signed_excess"] for item in capture_results
    )
    aggregate_max_absolute = max(
        item["m8_o"]["maximum_absolute_signed_excess"] for item in capture_results
    )
    evidence_verdict = (
        "PASS"
        if aggregate_r_violations == 0 and aggregate_o_violations == 0
        else "FAIL"
    )
    for label, file in (
        ("verifier manifest", FrozenFile(manifest_path, manifest_file_hash)),
        ("preregistration", FrozenFile(prereg_file, prereg_hash)),
        (
            "prospective interpretation",
            FrozenFile(interpretation_path, interpretation_hash),
        ),
        ("verifier", FrozenFile(verifier_path, verifier_hash)),
        ("verifier commissioning", commission_file),
        ("source manifest", source_manifest),
        ("source patch", source_patch),
        ("build receipt", build_receipt),
        ("candidate binary", binary),
        ("checker fixture manifest", fixture_manifest),
        ("checker commissioning report", checker_commission_report),
        (
            "checker commissioning violation evidence",
            checker_commission_violation_evidence,
        ),
        ("instrument freeze", instrument_freeze_file),
        *tuple((f"instrument {name}", file) for name, file in instruments.items()),
        (
            "cargo executable",
            FrozenFile(
                Path(build_evidence["cargo"]["path"]),
                build_evidence["cargo"]["sha256"],
            ),
        ),
        (
            "rustc executable",
            FrozenFile(
                Path(build_evidence["rustc"]["path"]),
                build_evidence["rustc"]["sha256"],
            ),
        ),
        (
            "candidate build log",
            FrozenFile(
                Path(build_evidence["original_build_log"]["path"]),
                build_evidence["original_build_log"]["sha256"],
            ),
        ),
    ):
        assert_still_frozen(file, label)
    source_evidence_after = verify_source_manifest(
        source_manifest, source_root, expected_commit, instruments["hook"].sha256
    )
    if source_evidence_after != source_evidence:
        raise Disagreement("source snapshot changed during target verification")
    for label, file in postflight_files:
        assert_still_frozen(file, label)
    for name, before, after, input_dir, expected in postflight_inputs:
        if validate_input_fingerprint(before, after, input_dir) != expected:
            raise Disagreement(f"{name}: final input fingerprint changed")
    result = {
        "protocol": VERIFIER_PROTOCOL,
        "status": evidence_verdict,
        "decision_rule": (
            "PASS iff aggregate M8-R V=0, the commissioned crop/reference "
            "identity V=0, and every capture and aggregate M8-O V=0"
        ),
        "manifest": {"path": str(manifest_path), "sha256": manifest_file_hash},
        "preregistration": {
            "path": str(prereg_file),
            "sha256": prereg_hash,
            "canonical_sha256": prereg_canonical_hash,
        },
        "prospective_interpretation": {
            "path": str(interpretation_path),
            "sha256": interpretation_hash,
            "canonical_sha256": interpretation_canonical_hash,
            "commit": INTERPRETATION_COMMIT,
        },
        "commissioning": commission_evidence,
        "checker_fixture": checker_fixture_evidence,
        "checker_commissioning": checker_commission_evidence,
        "crop_reference_identity": {
            "verifier_correct_origin_violations": frozen_commission["crop_origin_case"][
                "correct_origin_violations"
            ],
            "checker_correct_origin_violations": checker_commission_evidence[
                "crop_correct_origin_violations"
            ],
            "violations": 0,
        },
        "verifier": {
            "path": str(verifier_path),
            "sha256": verifier_hash,
            "canonical_sha256": verifier_canonical_hash,
        },
        "source_commit": expected_commit,
        "source_snapshot": source_evidence,
        "source_patch": source_patch_evidence,
        "reproducible_build": build_evidence,
        "instrument_freeze": instrument_freeze_evidence,
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
                "lower_violations": aggregate_r_lower,
                "upper_violations": aggregate_r_upper,
                "violations": aggregate_r_violations,
                "fraction_exact": (
                    f"{aggregate_r_violations}/{aggregate_r_denominator}"
                ),
                "fraction": aggregate_r_violations / float(aggregate_r_denominator),
                "max_excess_over_tolerance": max(
                    item["m8_r"]["max_excess_over_tolerance"]
                    for item in capture_results
                ),
                "maximum_positive_signed_excess": max(
                    item["m8_r"]["maximum_positive_signed_excess"]
                    for item in capture_results
                ),
                "minimum_negative_signed_excess": min(
                    item["m8_r"]["minimum_negative_signed_excess"]
                    for item in capture_results
                ),
                "maximum_absolute_signed_excess": max(
                    item["m8_r"]["maximum_absolute_signed_excess"]
                    for item in capture_results
                ),
            },
            "m8_o": {
                "denominator": aggregate_o_denominator,
                "lower_violations": aggregate_o_lower,
                "upper_violations": aggregate_o_upper,
                "violations": aggregate_o_violations,
                "fraction_exact": (
                    f"{aggregate_o_violations}/{aggregate_o_denominator}"
                ),
                "fraction": aggregate_o_violations / float(aggregate_o_denominator),
                "percent": 100.0
                * aggregate_o_violations
                / float(aggregate_o_denominator),
                "maximum_positive_signed_excess": aggregate_max_positive,
                "minimum_negative_signed_excess": aggregate_min_negative,
                "maximum_absolute_signed_excess": aggregate_max_absolute,
                "maximum_positive_signed_excess_lsb": (
                    aggregate_max_positive * U16_MAX
                ),
                "minimum_negative_signed_excess_lsb": (
                    aggregate_min_negative * U16_MAX
                ),
                "maximum_absolute_signed_excess_lsb": (
                    aggregate_max_absolute * U16_MAX
                ),
                "per_channel": aggregate_per_channel,
            },
        },
    }
    json_dump(report_path, result)
    return (0 if evidence_verdict == "PASS" else 1), result


def bits_f64(value: float) -> str:
    return struct.pack(">d", value).hex()


def write_synthetic_warpmap(path: Path, frames: int = 1) -> None:
    one = bits_f64(1.0)
    zero = bits_f64(0.0)
    placements = [
        f"{frame_order} placed {one} {zero} {zero} {zero}"
        for frame_order in range(frames)
    ]
    path.write_text(
        "\n".join(
            [
                "strehl-warpmap 1",
                "stack-name verifier-synthetic",
                "stack-digest 0000000000000000",
                f"frames {frames}",
                "plane 16x16",
                "reference 0",
                "strategy verifier",
                "resampler clamped-catmull",
                *placements,
                f"end {frames}",
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
    gathered_plants: Mapping[tuple[int, int], np.float32] | None = None,
    frame_order: int = 0,
    source_value_override: float | None = None,
    black_level: float = 0.0,
    sensor_range: float = 1000.0,
    site_gain: float = 1.0,
    output_gain: float = 1.0,
) -> Path:
    source_width = source_height = 32
    full_width = full_height = 16
    crop_x, crop_y, compact_width, compact_height = crop_override or crop
    channel = SITE_CHANNEL[(site_x, site_y)]
    source_value = np.float32(
        source_value_override
        if source_value_override is not None
        else (0.0 if channel == 2 else 2000.0)
    )
    source = np.full((source_height, source_width), source_value, dtype="<f4")
    valid = synthetic_validity(
        full_width, full_height, site_x, site_y, source_width, source_height
    )
    gathered = np.full((full_height, full_width), np.float32(np.nan), dtype="<f4")
    gathered[valid] = source_value
    for (y, x), value in (gathered_plants or {}).items():
        if not valid[y, x]:
            raise RuntimeError("M8-R commissioning plant targets an ineligible sample")
        gathered[y, x] = np.float32(value)
    frame_bytes = str(frame_path.resolve()).encode("utf-8")
    source_sha = bytes.fromhex(sha256_file(frame_path))
    header = TRACE_HEADER.pack(
        TRACE_MAGIC,
        TRACE_VERSION,
        2,
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
        ARITHMETIC_CONTRACT,
        1.0,
        0.0,
        0.0,
        0.0,
        8.0,
        8.0,
        black_level,
        sensor_range,
        site_gain,
        output_gain,
        bytes.fromhex(COMMISSION_FREEZE_SHA256),
        source_sha,
        len(frame_bytes),
    )
    payload = header + frame_bytes + source.tobytes() + gathered.tobytes()
    path_hash = hashlib.sha256(frame_bytes).hexdigest()
    content_hash = hashlib.sha256(payload).hexdigest()
    filename = (
        f"m8-trace-v3-p1-f{frame_order:08d}-{path_hash}"
        f"-s{site_x}{site_y}-{content_hash}.m8site"
    )
    path = block_dir / filename
    path.write_bytes(payload)
    return path


def write_synthetic_evidence(
    root: Path,
    encoded_r: int,
    encoded_b: int = 0,
    crop_override: tuple[int, int, int, int] | None = None,
    m8r_values: tuple[float, float] | None = None,
) -> tuple[Path, Path, Path, Path]:
    input_dir = root / "i"
    state = root / "s"
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
        plants = None
        if m8r_values is not None and site == (0, 0):
            plants = {
                (1, 1): np.float32(m8r_values[0]),
                (1, 2): np.float32(m8r_values[1]),
            }
        write_synthetic_trace(
            blocks,
            frame,
            *site,
            crop,
            crop_override,
            plants,
        )
    image = np.full((height, width, 3), U16_MAX, dtype=np.uint16)
    image[3, 2, 0] = encoded_r
    image[:, :, 2] = 0
    image[4, 3, 2] = encoded_b
    output = root / "o.tif"
    tifffile.imwrite(
        output,
        image,
        photometric="rgb",
        description=measurement_description(COMMISSION_FREEZE_SHA256),
    )
    return input_dir, state, warpmap, output


def write_green_pairing_evidence(
    root: Path, encoded_green: int
) -> tuple[Path, Path, Path, Path]:
    input_dir = root / "i"
    state = root / "s"
    blocks = state / "blocks"
    input_dir.mkdir(parents=True, exist_ok=True)
    blocks.mkdir(parents=True, exist_ok=True)
    warpmap = root / "m.txt"
    write_synthetic_warpmap(warpmap, frames=2)
    crop = reconstruct_crop(parse_warpmap(warpmap))[:4]
    green_values = {
        0: {(1, 0): 100.0, (0, 1): 900.0},
        1: {(1, 0): 900.0, (0, 1): 100.0},
    }
    for frame_order in range(2):
        frame = input_dir / f"frame{frame_order:03d}.ARW"
        frame.write_bytes(f"M136 green pairing frame {frame_order}\n".encode("ascii"))
        for site, channel in SITE_CHANNEL.items():
            if channel == 0:
                source_value = 2000.0
            elif channel == 2:
                source_value = 0.0
            else:
                source_value = green_values[frame_order][site]
            write_synthetic_trace(
                blocks,
                frame,
                *site,
                crop,
                frame_order=frame_order,
                source_value_override=source_value,
            )
    _, _, width, height = crop
    image = np.empty((height, width, 3), dtype=np.uint16)
    image[:, :, 0] = U16_MAX
    image[:, :, 1] = encoded_green
    image[:, :, 2] = 0
    output = root / "o.tif"
    tifffile.imwrite(
        output,
        image,
        photometric="rgb",
        description=measurement_description(COMMISSION_FREEZE_SHA256),
    )
    return input_dir, state, warpmap, output


def write_reciprocal_order_evidence(
    root: Path, encoded_red: int
) -> tuple[Path, Path, Path, Path]:
    input_dir = root / "i"
    state = root / "s"
    blocks = state / "blocks"
    input_dir.mkdir(parents=True, exist_ok=True)
    blocks.mkdir(parents=True, exist_ok=True)
    frame = input_dir / "frame000.ARW"
    frame.write_bytes(b"M136 reciprocal-order synthetic source\n")
    warpmap = root / "m.txt"
    write_synthetic_warpmap(warpmap)
    crop = reconstruct_crop(parse_warpmap(warpmap))[:4]
    special_source = np.array([0x471BCAC5], dtype=np.uint32).view(np.float32)[0]
    special_gain = np.array([0x3F3B4F55], dtype=np.uint32).view(np.float32)[0]
    black = np.array([0x0368236A], dtype=np.uint32).view(np.float32)[0]
    for site, channel in SITE_CHANNEL.items():
        source_value = (
            float(special_source) if channel == 0 else (0.0 if channel == 2 else 2000.0)
        )
        write_synthetic_trace(
            blocks,
            frame,
            *site,
            crop,
            source_value_override=source_value,
            black_level=float(black),
            sensor_range=float(U16_MAX),
            site_gain=float(special_gain) if channel == 0 else 1.0,
        )
    _, _, width, height = crop
    image = np.empty((height, width, 3), dtype=np.uint16)
    image[:, :, 0] = encoded_red
    image[:, :, 1] = 2000
    image[:, :, 2] = 0
    output = root / "o.tif"
    tifffile.imwrite(
        output,
        image,
        photometric="rgb",
        description=measurement_description(COMMISSION_FREEZE_SHA256),
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
        raise RuntimeError(
            "green-pairing control does not distinguish the two reductions"
        )
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


def crop_origin_control(prereg: Mapping[str, Any]) -> dict[str, Any]:
    case = prereg["commissioning"]["crop_origin_case"]
    full_height = int(case["full_height"])
    full_width = int(case["full_width"])
    compact_height = int(case["compact_height"])
    compact_width = int(case["compact_width"])
    origin_x = int(case["origin_x"])
    origin_y = int(case["origin_y"])
    yy, xx = np.indices((full_height, full_width), dtype=np.float64)
    source = 100.0 * yy + xx
    correct = (
        source[
            origin_y : origin_y + compact_height,
            origin_x : origin_x + compact_width,
        ]
        / 1000.0
    )
    wrong = source[:compact_height, :compact_width] / 1000.0

    def encode(values: np.ndarray) -> np.ndarray:
        return np.asarray(
            np.floor(np.clip(values, 0.0, 1.0) * U16_MAX + 0.5), dtype=np.uint16
        )

    correct_encoded = encode(correct)
    wrong_encoded = encode(wrong)
    correct_decoded = correct_encoded.astype(np.float64) / U16_MAX
    wrong_decoded = wrong_encoded.astype(np.float64) / U16_MAX
    correct_violations = (correct_decoded < correct - FINAL_Q) | (
        correct_decoded > correct + FINAL_Q
    )
    wrong_origin_violations = (wrong_decoded < correct - FINAL_Q) | (
        wrong_decoded > correct + FINAL_Q
    )
    expected_wrong = int(case["expected_wrong_origin_violations"])
    observed_correct = int(np.count_nonzero(correct_violations))
    observed_wrong = int(np.count_nonzero(wrong_origin_violations))
    if observed_correct != 0 or observed_wrong != expected_wrong:
        raise RuntimeError(
            f"crop-origin control observed correct={observed_correct}, "
            f"wrong={observed_wrong}, expected wrong={expected_wrong}"
        )
    return {
        "full_shape": [full_height, full_width],
        "compact_shape": [compact_height, compact_width],
        "origin": [origin_x, origin_y],
        "correct_origin_violations": observed_correct,
        "wrong_origin_violations": observed_wrong,
        "expected_wrong_origin_violations": expected_wrong,
    }


def catmull_weights(t: float) -> tuple[float, float, float, float]:
    t2 = t * t
    t3 = t2 * t
    return (
        -0.5 * t + t2 - 0.5 * t3,
        1.0 - 2.5 * t2 + 1.5 * t3,
        0.5 * t + 2.0 * t2 - 1.5 * t3,
        -0.5 * t2 + 0.5 * t3,
    )


def m8r_kernel_controls() -> dict[str, Any]:
    source_width, source_height = 40, 32
    output_width, output_height = 20, 16
    step = np.zeros((source_height, source_width), dtype=np.float32)
    step[:, 18:] = np.float32(1.0)

    def catmull_sample(source: np.ndarray, sx: float, sy: float) -> np.float32:
        ix = math.floor(sx)
        iy = math.floor(sy)
        wx = catmull_weights(sx - ix)
        wy = catmull_weights(sy - iy)
        total = 0.0
        for row, dy in enumerate((-1, 0, 1, 2)):
            for column, dx in enumerate((-1, 0, 1, 2)):
                total += wy[row] * wx[column] * float(source[iy + dy, ix + dx])
        return np.float32(total)

    def catmull_fixture(
        source: np.ndarray,
        offset_x: float,
        offset_y: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        values: list[np.float32] = []
        lowers: list[np.float32] = []
        uppers: list[np.float32] = []
        coordinates: list[tuple[int, int]] = []
        for y in range(output_height):
            for x in range(output_width):
                sx = 2.0 * (x + offset_x)
                sy = 2.0 * (y + offset_y)
                if not (
                    1.5 <= sx <= source_width - 2.5 and 1.5 <= sy <= source_height - 2.5
                ):
                    continue
                ix, iy = math.floor(sx), math.floor(sy)
                support = source[iy - 1 : iy + 3, ix - 1 : ix + 3]
                values.append(catmull_sample(source, sx, sy))
                lowers.append(np.min(support))
                uppers.append(np.max(support))
                coordinates.append((x, y))
        return (
            np.asarray(values, dtype=np.float32),
            np.asarray(lowers, dtype=np.float32),
            np.asarray(uppers, dtype=np.float32),
            np.asarray(coordinates, dtype=np.int32),
        )

    def census(
        values: np.ndarray, lower: np.ndarray, upper: np.ndarray
    ) -> dict[str, int]:
        tolerance = tau_r(lower, upper)
        low = values < np.asarray(lower - tolerance, dtype=np.float32)
        high = values > np.asarray(upper + tolerance, dtype=np.float32)
        return {
            "denominator": int(values.size),
            "lower_violations": int(np.count_nonzero(low)),
            "upper_violations": int(np.count_nonzero(high)),
            "violations": int(np.count_nonzero(low | high)),
        }

    raw, lower, upper, coordinates = catmull_fixture(step, 0.25, 0.0)
    catmull = census(raw, lower, upper)
    clamped_values = np.clip(raw, lower, upper).astype(np.float32)
    clamped = census(clamped_values, lower, upper)
    tolerance = tau_r(lower, upper)
    widened_values = np.minimum(
        np.maximum(raw, lower - np.float32(32.0) * tolerance),
        upper + np.float32(32.0) * tolerance,
    ).astype(np.float32)
    widened = census(widened_values, lower, upper)

    texture = np.fromfunction(
        lambda y, x: (17 * x + 29 * y + 7 * ((x * y) % 19)) / 4096.0,
        (source_height, source_width),
        dtype=np.float64,
    ).astype(np.float32)
    copy_values, copy_lower, copy_upper, _ = catmull_fixture(texture, 0.0, 0.0)
    copy_null = census(copy_values, copy_lower, copy_upper)
    clamped_copy = census(
        np.clip(copy_values, copy_lower, copy_upper).astype(np.float32),
        copy_lower,
        copy_upper,
    )
    clamped_copy_exact = bool(
        np.array_equal(
            copy_values.view(np.uint32),
            np.clip(copy_values, copy_lower, copy_upper)
            .astype(np.float32)
            .view(np.uint32),
        )
    )

    bilinear_values: list[np.float32] = []
    bilinear_lower: list[np.float32] = []
    bilinear_upper: list[np.float32] = []
    for y in range(output_height):
        for x in range(output_width):
            sx = 2.0 * (x + 0.25)
            sy = 2.0 * (y + 0.125)
            if not (
                0.5 <= sx <= source_width - 1.5 and 0.5 <= sy <= source_height - 1.5
            ):
                continue
            ix, iy = math.floor(sx), math.floor(sy)
            tx, ty = sx - ix, sy - iy
            support = texture[iy : iy + 2, ix : ix + 2]
            value = (1.0 - ty) * (
                (1.0 - tx) * support[0, 0] + tx * support[0, 1]
            ) + ty * ((1.0 - tx) * support[1, 0] + tx * support[1, 1])
            bilinear_values.append(np.float32(value))
            bilinear_lower.append(np.min(support))
            bilinear_upper.append(np.max(support))
    bilinear_null = census(
        np.asarray(bilinear_values, dtype=np.float32),
        np.asarray(bilinear_lower, dtype=np.float32),
        np.asarray(bilinear_upper, dtype=np.float32),
    )

    constant = np.ones((source_height, source_width), dtype=np.float32)
    plant_values, plant_lower, plant_upper, plant_coordinates = catmull_fixture(
        constant, 0.0, 0.0
    )
    plant_tau = tau_r(plant_lower, plant_upper)
    high_index = int(
        np.flatnonzero((plant_coordinates[:, 0] == 5) & (plant_coordinates[:, 1] == 5))[
            0
        ]
    )
    low_index = int(
        np.flatnonzero((plant_coordinates[:, 0] == 6) & (plant_coordinates[:, 1] == 5))[
            0
        ]
    )
    plant_values[high_index] = np.float32(
        plant_values[high_index] + np.float32(32.0) * plant_tau[high_index]
    )
    plant_values[low_index] = np.float32(
        plant_values[low_index] - np.float32(32.0) * plant_tau[low_index]
    )
    explicit = census(plant_values, plant_lower, plant_upper)

    expected = {
        "catmull_hard_step": {
            "denominator": 252,
            "lower_violations": 14,
            "upper_violations": 14,
            "violations": 28,
        },
        "clamped_hard_step": {
            "denominator": 252,
            "lower_violations": 0,
            "upper_violations": 0,
            "violations": 0,
        },
        "widened_clamp_sabotage": {
            "denominator": 252,
            "lower_violations": 14,
            "upper_violations": 14,
            "violations": 28,
        },
        "explicit_high_low": {
            "denominator": 252,
            "lower_violations": 1,
            "upper_violations": 1,
            "violations": 2,
        },
    }
    observed = {
        "catmull_hard_step": catmull,
        "clamped_hard_step": clamped,
        "widened_clamp_sabotage": widened,
        "copy_null": copy_null,
        "clamped_copy_null": clamped_copy,
        "convex_bilinear_null": bilinear_null,
        "explicit_high_low": explicit,
    }
    for name, counts in expected.items():
        if observed[name] != counts:
            raise RuntimeError(
                f"M8-R {name} commissioning observed {observed[name]}, "
                f"expected {counts}"
            )
    for name in ("copy_null", "clamped_copy_null", "convex_bilinear_null"):
        if observed[name]["violations"] != 0:
            raise RuntimeError(f"M8-R {name} commissioning was not green")
    if not clamped_copy_exact:
        raise RuntimeError("M8-R clamped copy control is not bit-exact")
    return {
        "arms": observed,
        "expected_exact": expected,
        "clamped_copy_bit_exact": clamped_copy_exact,
    }


def inverse_gain_order_control() -> dict[str, Any]:
    site_gain = np.float32(1.1)
    source_value = np.float32(1.649999976158142)
    inverse_gain = np.float32(np.float32(1.0) / site_gain)
    actual_scaled = np.float32(source_value * inverse_gain)
    direct_division = np.float32(source_value / site_gain)
    actual_code = int(
        np.clip(
            math.floor(float(actual_scaled) + 0.5),
            0,
            U16_MAX,
        )
    )
    direct_code = int(math.floor(float(direct_division) + 0.5))
    if actual_code != 1 or direct_code != 2:
        raise RuntimeError(
            "inverse-gain operation-order control did not separate multiply from divide"
        )
    production_gain = np.array([0x3F167791], dtype=np.uint32).view(np.float32)[0]
    production_source = np.array([0x461BB3F3], dtype=np.uint32).view(np.float32)[0]
    production_black = np.array([0x439D30BE], dtype=np.uint32).view(np.float32)[0]
    _, _, production_lo, production_hi = intermediate_interval(
        np.array([[production_source]], dtype=np.float32),
        np.array([[production_source]], dtype=np.float32),
        production_gain,
        production_black,
    )
    direct_lo = f32_down(
        np.array([[production_source]], dtype=np.float32).astype(np.float64)
        / float(production_gain)
    )
    direct_hi = f32_up(
        np.array([[production_source]], dtype=np.float32).astype(np.float64)
        / float(production_gain)
    )
    direct_lo = f32_down(direct_lo.astype(np.float64) + float(production_black))
    direct_hi = f32_up(direct_hi.astype(np.float64) + float(production_black))
    direct_u_lo = np.clip(round_ties_away(direct_lo), 0, U16_MAX).astype(np.uint16)
    direct_u_hi = np.clip(round_ties_away(direct_hi), 0, U16_MAX).astype(np.uint16)
    production_interval = [
        int(production_lo[0, 0]),
        int(production_hi[0, 0]),
    ]
    direct_interval = [int(direct_u_lo[0, 0]), int(direct_u_hi[0, 0])]
    if production_interval != [17268, 17269] or direct_interval != [17269, 17269]:
        raise RuntimeError(
            "production reciprocal-order discriminator no longer reaches the "
            "expected intermediate_interval branch"
        )
    return {
        "source_f32_bits": f"0x{int(source_value.view(np.uint32)):08x}",
        "site_gain_f32": float(site_gain),
        "actual_contract": "f32 inv=1/g; f32 z*inv",
        "actual_scaled_f32": float(actual_scaled),
        "direct_division_f32": float(direct_division),
        "actual_intermediate_u16": actual_code,
        "direct_division_intermediate_u16": direct_code,
        "distinguishes_operation_order": True,
        "production_path": {
            "source_f32_bits": "0x461bb3f3",
            "site_gain_f32_bits": "0x3f167791",
            "black_f32_bits": "0x439d30be",
            "intermediate_interval_u16": production_interval,
            "direct_division_interval_u16": direct_interval,
            "distinguishes_operation_order": True,
        },
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
        black_lo, black_hi, _, _ = intermediate_interval(lo, hi, site_gain, black)
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
                    f"{projected_lo[0, 0]} <= {projected} <= {projected_hi[0, 0]}"
                )
            samples += 1
    return {
        "seed": 136,
        "cases": cases,
        "scalar_samples": samples,
        "misses": 0,
    }


def source_inventory_control(work_dir: Path) -> dict[str, Any]:
    root = work_dir / "source-inventory"
    (root / "crates" / "app" / "src" / "target").mkdir(parents=True)
    (root / "outside-path-dependency" / "src").mkdir(parents=True)
    (root / "target-m136" / "release").mkdir(parents=True)
    (root / "target-m136-tests" / "debug").mkdir(parents=True)
    (root / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
    (root / "crates" / "app" / "src" / "target" / "mod.rs").write_text(
        "pub const COMPILED: bool = true;\n", encoding="utf-8"
    )
    (root / "outside-path-dependency" / "src" / "lib.rs").write_text(
        "pub fn dependency() {}\n", encoding="utf-8"
    )
    (root / "target-m136" / "release" / "strehl.exe").write_bytes(
        b"synthetic build output\n"
    )
    (root / "target-m136-tests" / "debug" / "probe.exe").write_bytes(
        b"synthetic test output\n"
    )
    observed = build_relevant_source_files(root)
    required = {
        "Cargo.toml",
        "crates/app/src/target/mod.rs",
        "outside-path-dependency/src/lib.rs",
    }
    excluded = {
        "target-m136/release/strehl.exe",
        "target-m136-tests/debug/probe.exe",
    }
    if not required.issubset(observed) or not excluded.isdisjoint(observed):
        raise RuntimeError(
            "source inventory is not closed over non-target source files"
        )
    return {
        "required_present": sorted(required),
        "top_level_target_excluded": sorted(excluded),
        "observed": sorted(observed),
        "build_id": m136_build_id(M130_SOURCE_COMMIT, "A" * 64),
        "status": "PASS",
    }


def commission(prereg_path: Path, report_path: Path, work_dir: Path) -> dict[str, Any]:
    if report_path.exists():
        raise RuntimeError(f"refusing to overwrite commissioning report: {report_path}")
    if work_dir.exists():
        raise RuntimeError(
            f"refusing to reuse commissioning work directory: {work_dir}"
        )
    work_dir.mkdir(parents=True)
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if sha256_canonical_text(prereg_path) != PREREG_CANONICAL_SHA256:
        raise RuntimeError(
            "commissioning preregistration differs from the frozen bytes"
        )
    interpretation_path = Path(__file__).with_name("prospective-interpretations.md")
    if sha256_canonical_text(interpretation_path) != INTERPRETATION_CANONICAL_SHA256:
        raise RuntimeError(
            "commissioning interpretation differs from the pre-target ruling"
        )
    report: dict[str, Any] = {
        "protocol": VERIFIER_PROTOCOL,
        "commissioning": "both directions",
        "verifier": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
            "canonical_sha256": sha256_canonical_text(Path(__file__).resolve()),
        },
        "preregistration": {
            "path": str(prereg_path.resolve()),
            "sha256": sha256_file(prereg_path),
            "canonical_sha256": sha256_canonical_text(prereg_path),
        },
        "prospective_interpretation": {
            "path": str(interpretation_path.resolve()),
            "sha256": sha256_file(interpretation_path),
            "canonical_sha256": sha256_canonical_text(interpretation_path),
            "commit": INTERPRETATION_COMMIT,
        },
        "independence": verify_independence(Path(__file__).resolve()),
        "numeric_cases": direct_numeric_controls(prereg),
        "quantizer_case": quantizer_control(prereg),
        "green_pairing_case": green_pairing_control(),
        "crop_origin_case": crop_origin_control(prereg),
        "m8_r_kernel_cases": m8r_kernel_controls(),
        "inverse_gain_order_case": inverse_gain_order_control(),
        "interval_containment": interval_containment_control(),
    }
    try:
        report["source_inventory_case"] = source_inventory_control(work_dir)
        recipe = work_dir / "recipe.json"
        recipe.write_text(
            "{\n"
            '  "encoded_r": 65535,\n'
            '  "encoded_b": 0,\n'
            '  "plant_x": 2,\n'
            '  "plant_y": 3\n'
            "}\n",
            encoding="utf-8",
        )
        input_dir, state, warpmap, output = write_synthetic_evidence(work_dir, U16_MAX)

        def run_case(name: str, encoded_r: int, encoded_b: int) -> dict[str, Any]:
            image = tifffile.imread(output)
            image[3, 2, 0] = encoded_r
            image[4, 3, 2] = encoded_b
            tifffile.imwrite(
                output,
                image,
                photometric="rgb",
                description=measurement_description(COMMISSION_FREEZE_SHA256),
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
                None,
                "00" * 32,
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

        baseline = run_case("baseline", U16_MAX, 0)
        if baseline["status"] != "PASS":
            raise RuntimeError("synthetic high-rail baseline did not pass")

        defect_low_plant = replace_unique_line(
            recipe, '  "encoded_r": 65535,', '  "encoded_r": 65534,'
        )
        defect_high_plant = replace_unique_line(
            recipe, '  "encoded_b": 0,', '  "encoded_b": 1,'
        )
        defect_recipe = json.loads(recipe.read_text(encoding="utf-8"))
        defect = run_case(
            "defect",
            int(defect_recipe["encoded_r"]),
            int(defect_recipe["encoded_b"]),
        )
        if defect["status"] != "FAIL" or defect["m8_o_violations"] != 2:
            raise RuntimeError("planted degradations were not charged exactly twice")
        if defect["violations"] != [
            {"x": 2, "y": 3, "channel": "R", "direction": -1, "encoded": 65534},
            {"x": 3, "y": 4, "channel": "B", "direction": 1, "encoded": 1},
        ]:
            raise RuntimeError(
                f"planted degradation landed at wrong verdict row: {defect}"
            )

        improvement_low_plant = replace_unique_line(
            recipe, '  "encoded_r": 65534,', '  "encoded_r": 65535,'
        )
        improvement_high_plant = replace_unique_line(
            recipe, '  "encoded_b": 1,', '  "encoded_b": 0,'
        )
        improvement_recipe = json.loads(recipe.read_text(encoding="utf-8"))
        improvement = run_case(
            "improvement",
            int(improvement_recipe["encoded_r"]),
            int(improvement_recipe["encoded_b"]),
        )
        if improvement["status"] != "PASS" or improvement["m8_o_violations"] != 0:
            raise RuntimeError("planted improvement was misreported")
        if baseline["output_sha256"] == defect["output_sha256"]:
            raise RuntimeError("degradation plant did not change the TIFF hash")
        if defect["output_sha256"] == improvement["output_sha256"]:
            raise RuntimeError("improvement plant did not change the TIFF hash")

        m8r_recipe = work_dir / "m8r-recipe.json"
        m8r_recipe.write_text(
            '{\n  "low_gather": 1999.0,\n  "high_gather": 2001.0\n}\n',
            encoding="utf-8",
        )

        def run_m8r_production_path(name: str) -> dict[str, Any]:
            values = json.loads(m8r_recipe.read_text(encoding="utf-8"))
            root = work_dir / f"r{name[0]}"
            m8r_input, m8r_state, m8r_map, m8r_output = write_synthetic_evidence(
                root,
                U16_MAX,
                0,
                m8r_values=(
                    float(values["low_gather"]),
                    float(values["high_gather"]),
                ),
            )
            result = verify_capture(
                f"commission-m8r-{name}",
                m8r_input.resolve(),
                FrozenFile(m8r_map.resolve(), sha256_file(m8r_map)),
                m8r_state.resolve(),
                FrozenFile(m8r_output.resolve(), sha256_file(m8r_output)),
                work_dir / f"vr{name[0]}",
                4,
                None,
                None,
                "00" * 32,
            )
            rows = np.load(
                work_dir / f"vr{name[0]}" / "m8-r-violations.npy",
                allow_pickle=False,
            )
            return {
                "m8_r": {
                    key: result["m8_r"][key]
                    for key in (
                        "denominator",
                        "lower_violations",
                        "upper_violations",
                        "violations",
                    )
                },
                "m8_o_violations": result["m8_o"]["violations"],
                "violation_directions": sorted(
                    int(value) for value in rows["direction"]
                ),
                "recipe_sha256": sha256_file(m8r_recipe),
            }

        m8r_defect = run_m8r_production_path("defect")
        if (
            m8r_defect["m8_r"]["lower_violations"] != 1
            or m8r_defect["m8_r"]["upper_violations"] != 1
            or m8r_defect["m8_r"]["violations"] != 2
            or m8r_defect["m8_o_violations"] != 0
            or m8r_defect["violation_directions"] != [-1, 1]
        ):
            raise RuntimeError(
                f"production-path M8-R defect was not charged exactly: {m8r_defect}"
            )
        m8r_low_improvement = replace_unique_line(
            m8r_recipe, '  "low_gather": 1999.0,', '  "low_gather": 2000.0,'
        )
        m8r_high_improvement = replace_unique_line(
            m8r_recipe, '  "high_gather": 2001.0', '  "high_gather": 2000.0'
        )
        m8r_improvement = run_m8r_production_path("improvement")
        if (
            m8r_improvement["m8_r"]["violations"] != 0
            or m8r_improvement["m8_o_violations"] != 0
        ):
            raise RuntimeError("production-path M8-R improvement was misreported")
        if m8r_defect["recipe_sha256"] == m8r_improvement["recipe_sha256"]:
            raise RuntimeError("production-path M8-R improvement did not land")

        green_recipe = work_dir / "green-recipe.json"
        green_recipe.write_text(
            '{\n  "encoded_green": 26214\n}\n',
            encoding="utf-8",
        )

        def run_green_production_path(name: str) -> dict[str, Any]:
            encoded_green = int(
                json.loads(green_recipe.read_text(encoding="utf-8"))["encoded_green"]
            )
            root = work_dir / f"g{name[0]}"
            green_input, green_state, green_map, green_output = (
                write_green_pairing_evidence(root, encoded_green)
            )
            result = verify_capture(
                f"commission-green-{name}",
                green_input.resolve(),
                FrozenFile(green_map.resolve(), sha256_file(green_map)),
                green_state.resolve(),
                FrozenFile(green_output.resolve(), sha256_file(green_output)),
                work_dir / f"vg{name[0]}",
                4,
                None,
                None,
                "00" * 32,
            )
            rows = np.load(
                work_dir / f"vg{name[0]}" / "m8-o-violations.npy",
                allow_pickle=False,
            )
            return {
                "encoded_green": encoded_green,
                "m8_r_violations": result["m8_r"]["violations"],
                "m8_o": {
                    key: result["m8_o"][key]
                    for key in (
                        "denominator",
                        "lower_violations",
                        "upper_violations",
                        "violations",
                    )
                },
                "violation_channels": sorted({str(value) for value in rows["channel"]}),
                "violation_directions": sorted(
                    {int(value) for value in rows["direction"]}
                ),
                "recipe_sha256": sha256_file(green_recipe),
            }

        green_defect = run_green_production_path("defect")
        if (
            green_defect["m8_r_violations"] != 0
            or green_defect["m8_o"]["denominator"] != 243
            or green_defect["m8_o"]["lower_violations"] != 81
            or green_defect["m8_o"]["upper_violations"] != 0
            or green_defect["m8_o"]["violations"] != 81
            or green_defect["violation_channels"] != ["G"]
            or green_defect["violation_directions"] != [-1]
        ):
            raise RuntimeError(
                "same-frame green production-path defect was not charged exactly: "
                f"{green_defect}"
            )
        green_improvement_plant = replace_unique_line(
            green_recipe,
            '  "encoded_green": 26214',
            '  "encoded_green": 32768',
        )
        green_improvement = run_green_production_path("improvement")
        if green_improvement["m8_r_violations"] != 0 or green_improvement["m8_o"] != {
            "denominator": 243,
            "lower_violations": 0,
            "upper_violations": 0,
            "violations": 0,
        }:
            raise RuntimeError(
                "same-frame green production-path improvement was misreported"
            )
        if green_defect["recipe_sha256"] == green_improvement["recipe_sha256"]:
            raise RuntimeError("same-frame green improvement did not land")

        reciprocal_recipe = work_dir / "reciprocal-recipe.json"
        reciprocal_recipe.write_text(
            '{\n  "encoded_red": 54508\n}\n',
            encoding="utf-8",
        )

        def run_reciprocal_production_path(name: str) -> dict[str, Any]:
            encoded_red = int(
                json.loads(reciprocal_recipe.read_text(encoding="utf-8"))["encoded_red"]
            )
            root = work_dir / f"x{name[0]}"
            reciprocal_input, reciprocal_state, reciprocal_map, reciprocal_output = (
                write_reciprocal_order_evidence(root, encoded_red)
            )
            result = verify_capture(
                f"commission-reciprocal-{name}",
                reciprocal_input.resolve(),
                FrozenFile(reciprocal_map.resolve(), sha256_file(reciprocal_map)),
                reciprocal_state.resolve(),
                FrozenFile(reciprocal_output.resolve(), sha256_file(reciprocal_output)),
                work_dir / f"vx{name[0]}",
                4,
                None,
                None,
                "00" * 32,
            )
            rows = np.load(
                work_dir / f"vx{name[0]}" / "m8-o-violations.npy",
                allow_pickle=False,
            )
            return {
                "encoded_red": encoded_red,
                "m8_r_violations": result["m8_r"]["violations"],
                "m8_o": {
                    key: result["m8_o"][key]
                    for key in (
                        "denominator",
                        "lower_violations",
                        "upper_violations",
                        "violations",
                    )
                },
                "violation_channels": sorted({str(value) for value in rows["channel"]}),
                "violation_directions": sorted(
                    {int(value) for value in rows["direction"]}
                ),
                "recipe_sha256": sha256_file(reciprocal_recipe),
            }

        reciprocal_defect = run_reciprocal_production_path("defect")
        if (
            reciprocal_defect["m8_r_violations"] != 0
            or reciprocal_defect["m8_o"]["denominator"] != 243
            or reciprocal_defect["m8_o"]["lower_violations"] != 81
            or reciprocal_defect["m8_o"]["upper_violations"] != 0
            or reciprocal_defect["m8_o"]["violations"] != 81
            or reciprocal_defect["violation_channels"] != ["R"]
            or reciprocal_defect["violation_directions"] != [-1]
        ):
            raise RuntimeError(
                "reciprocal-multiply production-path defect was not charged exactly: "
                f"{reciprocal_defect}"
            )
        reciprocal_improvement_plant = replace_unique_line(
            reciprocal_recipe,
            '  "encoded_red": 54508',
            '  "encoded_red": 54509',
        )
        reciprocal_improvement = run_reciprocal_production_path("improvement")
        if reciprocal_improvement["m8_r_violations"] != 0 or reciprocal_improvement[
            "m8_o"
        ] != {
            "denominator": 243,
            "lower_violations": 0,
            "upper_violations": 0,
            "violations": 0,
        }:
            raise RuntimeError(
                "reciprocal-multiply production-path improvement was misreported"
            )
        if (
            reciprocal_defect["recipe_sha256"]
            == reciprocal_improvement["recipe_sha256"]
        ):
            raise RuntimeError("reciprocal-multiply improvement did not land")

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
            raise RuntimeError(
                "duplicate frame/site evidence did not report UNMEASURED"
            )

        producer_hull = state / "producer-supplied-hull.npy"
        producer_mask = state / "producer-supplied-contributor-mask.npy"
        np.save(producer_hull, np.asarray([[-12345.0]], dtype=np.float32))
        np.save(producer_mask, np.asarray([[0]], dtype=np.uint8))
        ignored_hull = run_case("producer-hull-ignored", U16_MAX, 0)
        producer_hull.unlink()
        producer_mask.unlink()
        if ignored_hull["status"] != "PASS":
            raise RuntimeError("producer-supplied hull contaminated independent result")

        wrong_crop_root = work_dir / "c"
        wrong_input, wrong_state, wrong_map, wrong_output = write_synthetic_evidence(
            wrong_crop_root, U16_MAX, 0, crop_override=(0, 0, 9, 9)
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

        freeze_message = ""
        try:
            verify_capture(
                "commission-freeze",
                input_dir.resolve(),
                FrozenFile(warpmap.resolve(), sha256_file(warpmap)),
                state.resolve(),
                FrozenFile(output.resolve(), sha256_file(output)),
                work_dir / "verified-wrong-freeze",
                4,
                None,
                None,
                "11" * 32,
            )
        except Unmeasured as error:
            freeze_message = str(error)
        if "not bound to the frozen instrument" not in freeze_message:
            raise RuntimeError("wrong freeze binding did not report UNMEASURED")

        tiff_binding_recipe = work_dir / "tiff-binding-recipe.json"
        tiff_binding_recipe.write_text(
            f'{{\n  "freeze_sha256": "{COMMISSION_FREEZE_SHA256}"\n}}\n',
            encoding="utf-8",
        )
        wrong_tiff_binding_plant = replace_unique_line(
            tiff_binding_recipe,
            f'  "freeze_sha256": "{COMMISSION_FREEZE_SHA256}"',
            f'  "freeze_sha256": "{"11" * 32}"',
        )
        image = tifffile.imread(output)
        tifffile.imwrite(
            output,
            image,
            photometric="rgb",
            description=measurement_description(
                json.loads(tiff_binding_recipe.read_text(encoding="utf-8"))[
                    "freeze_sha256"
                ]
            ),
        )
        wrong_tiff_hash = sha256_file(output)
        tiff_binding_message = ""
        try:
            verify_capture(
                "commission-tiff-binding",
                input_dir.resolve(),
                FrozenFile(warpmap.resolve(), sha256_file(warpmap)),
                state.resolve(),
                FrozenFile(output.resolve(), wrong_tiff_hash),
                work_dir / "verified-wrong-tiff-binding",
                4,
                None,
                None,
                COMMISSION_FREEZE_SHA256,
            )
        except Unmeasured as error:
            tiff_binding_message = str(error)
        if (
            "TIFF is not bound to the frozen M136 instrument"
            not in tiff_binding_message
        ):
            raise RuntimeError("wrong TIFF freeze binding did not report UNMEASURED")
        restored_tiff_binding_plant = replace_unique_line(
            tiff_binding_recipe,
            f'  "freeze_sha256": "{"11" * 32}"',
            f'  "freeze_sha256": "{COMMISSION_FREEZE_SHA256}"',
        )
        tifffile.imwrite(
            output,
            image,
            photometric="rgb",
            description=measurement_description(COMMISSION_FREEZE_SHA256),
        )
        restored_tiff_hash = sha256_file(output)
        restored_tiff_binding = verify_capture(
            "commission-tiff-binding-restored",
            input_dir.resolve(),
            FrozenFile(warpmap.resolve(), sha256_file(warpmap)),
            state.resolve(),
            FrozenFile(output.resolve(), restored_tiff_hash),
            work_dir / "verified-restored-tiff-binding",
            4,
            None,
            None,
            COMMISSION_FREEZE_SHA256,
        )
        if (
            restored_tiff_binding["m8_r"]["violations"] != 0
            or restored_tiff_binding["m8_o"]["violations"] != 0
            or wrong_tiff_hash == restored_tiff_hash
        ):
            raise RuntimeError("restored TIFF freeze binding was misreported")

        report.update(
            {
                "baseline_green": baseline,
                "degradation_plant": {
                    "landed": {
                        "lower": defect_low_plant,
                        "upper": defect_high_plant,
                    },
                    "result": defect,
                },
                "improvement_plant": {
                    "landed": {
                        "lower": improvement_low_plant,
                        "upper": improvement_high_plant,
                    },
                    "result": improvement,
                },
                "production_path_controls": {
                    "m8_r": {
                        "defect": m8r_defect,
                        "improvement": m8r_improvement,
                        "improvement_landed": {
                            "lower": m8r_low_improvement,
                            "upper": m8r_high_improvement,
                        },
                    },
                    "green_pairing": {
                        "defect": green_defect,
                        "improvement": green_improvement,
                        "improvement_landed": green_improvement_plant,
                    },
                    "reciprocal_order": {
                        "defect": reciprocal_defect,
                        "improvement": reciprocal_improvement,
                        "improvement_landed": reciprocal_improvement_plant,
                    },
                    "inverse_gain": report["inverse_gain_order_case"][
                        "production_path"
                    ],
                },
                "fail_closed": {
                    "missing_frame_site": missing_message,
                    "duplicate_frame_site": duplicate_message,
                    "trace_v2_rejected": True,
                    "trace_v2_reason": "requires trace-v3",
                    "wrong_crop_origin": crop_message,
                    "wrong_freeze_binding": freeze_message,
                    "wrong_tiff_freeze_binding": {
                        "rejected": True,
                        "reason": "TIFF is not bound to the frozen M136 instrument",
                        "defect_landed": wrong_tiff_binding_plant,
                        "improvement_landed": restored_tiff_binding_plant,
                        "defect_tiff_sha256": wrong_tiff_hash,
                        "improved_tiff_sha256": restored_tiff_hash,
                    },
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
    report_output = args.report.resolve() if hasattr(args, "report") else None
    try:
        if args.command == "commission":
            report = commission(
                args.preregistration.resolve(),
                args.report.resolve(),
                args.work_dir.resolve(),
            )
            print(
                json.dumps(
                    {"status": report["status"], "report": str(args.report.resolve())}
                )
            )
            return 0
        if args.chunk_rows <= 0:
            raise Unmeasured("--chunk-rows must be positive")
        if report_output is not None and report_output.exists():
            raise Unmeasured(f"refusing to overwrite verifier report: {report_output}")
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
        if report_output is not None and not report_output.exists():
            json_dump(report_output, failure)
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        return 3
    except (
        Unmeasured,
        OSError,
        ValueError,
        KeyError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        failure = {
            "protocol": VERIFIER_PROTOCOL,
            "status": "UNMEASURED",
            "error": str(error),
        }
        if report_output is not None and not report_output.exists():
            json_dump(report_output, failure)
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
