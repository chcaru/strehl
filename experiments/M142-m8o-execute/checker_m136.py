#!/usr/bin/env python3
"""Independent commissioner and target adjudicator for M136.

The commissioning command consumes only the frozen fixture and
preregistration.  The adjudication command consumes value-only trace-v3
blocks, reconstructs every interval, and never accepts producer hulls, masks,
or verdicts.

Exit codes:
  0  measured PASS
  1  measured FAIL
  2  UNMEASURED / refused evidence
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


# Keep numerical libraries bounded before importing NumPy.
for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[_thread_variable] = "1"

import numpy as np
import tifffile


PROTOCOL = "M136 clamped-Catmull-Rom representable-domain M8-O v1"
CHECKER_PROTOCOL = "M136 independent checker"
CHECKER_VERSION = 1
COMMISSION_SCHEMA = "m136-checker-commissioning"
COMMISSION_VERSION = 1
FIXTURE_SCHEMA = "m136-commissioning-fixture-manifest"
FIXTURE_VERSION = 1
NUMERIC_REPRESENTATION = (
    "fixture-only identity: P_fixture(z)=z; F_fixture(z)=clamp(z,0,1)"
)
PREREG_SHA256 = "B656EFB9D2BFEA4B8CF5DD67BE63A9CD7D6930F6B302C7EF93E9E1DF7529BCEB"
INTERPRETATION_COMMIT = "746cc38a"
INTERPRETATION_CANONICAL_SHA256 = (
    "DBCCCF505D91FB86385D44BE3293A280A54ACE4C0C416945F23CFDFE355A203C"
)
M136_EVIDENCE_DIR = (
    Path(__file__).resolve().parent.parent / "M136-m8o-bar"
).resolve()
PREREGISTRATION_PATH = M136_EVIDENCE_DIR / "clamped-m8o-preregistration.json"
INTERPRETATION_PATH = M136_EVIDENCE_DIR / "prospective-interpretations.md"

TRACE_MAGIC = b"M8SITE03"
TRACE_VERSION = 3
TRACE_HEADER = struct.Struct("<8s15I6d4f32s32sI")
TRACE_NAME = re.compile(
    r"^m8-trace-v3-p1-f(?P<frame>\d{8})-"
    r"(?P<path_hash>[0-9a-f]{64})-s(?P<sx>[01])(?P<sy>[01])-"
    r"(?P<content_hash>[0-9a-f]{64})\.m8site$"
)
ARITHMETIC_CONTRACT = 1
TARGET_KERNEL = 2
GREEN_RULE = "same-frame-before-reduction"
GREEN_RULE_STATUS = "ADOPTED_PROSPECTIVELY_AT_746cc38a"

U16_MAX = 65535
FINAL_Q = 1.0 / 131070.0
COVER_MARGIN = 3.0
CHUNK_ROWS_DEFAULT = 32
MAX_PATH_BYTES = 1 << 20
CHANNEL_NAMES = ("R", "G", "B")
SITE_NAMES = {
    (0, 0): "R",
    (1, 0): "G1",
    (0, 1): "G2",
    (1, 1): "B",
}
SITE_CHANNEL = {(0, 0): 0, (1, 0): 1, (0, 1): 1, (1, 1): 2}
GREEN_SITES = ((1, 0), (0, 1))
SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
F64_BITS_RE = re.compile(r"^[0-9a-fA-F]{16}$")
U64_BITS_RE = re.compile(r"^[0-9a-fA-F]{16}$")
UINT_RE = re.compile(r"^(0|[1-9][0-9]*)$")
PLANE_RE = re.compile(r"^(0|[1-9][0-9]*)x(0|[1-9][0-9]*)$")
FNV1A64_OFFSET = 0xCBF29CE484222325
FNV1A64_PRIME = 0x100000001B3
U64_MASK = (1 << 64) - 1

NUMERIC_FIELDS = ("lo", "hi", "tau", "encoded", "expected_violations")
INTERMEDIATE_FIELDS = (
    "g",
    "b",
    "G",
    "R",
    "lo",
    "hi",
    "tau",
    "expected_intermediate_u16",
    "expected_pre_final",
    "green_encoded",
    "red_encoded",
)
CROP_FIELDS = (
    "channels",
    "compact_height",
    "compact_width",
    "expected_wrong_origin_violations",
    "full_height",
    "full_width",
    "normalization",
    "origin_x",
    "origin_y",
    "source_value",
    "transform",
)
FIXTURE_BASE_FILES = frozenset(
    (
        "m8-o-numeric-cases.json",
        "intermediate-quantizer-case.json",
        "crop-origin-source.npy",
        "crop-origin-correct.tiff",
        "crop-origin-wrong.tiff",
        "crop-origin-case.json",
        "fail-closed-cases.json",
    )
)
FAIL_CLOSED_CONTROLS = (
    "trace v2 without black level reports UNMEASURED",
    "missing crop origin reports UNMEASURED",
    "missing or duplicate frame/site trace reports UNMEASURED",
    "producer-supplied hull or contributor mask is ignored",
    "Catmull hard-step is red for M8-R",
    "clamped hard-step, copy, and convex-bilinear controls are green for M8-R",
    "widened-clamp sabotage is red for M8-R",
)
NUMERIC_DIRECTIONS = {
    "convex_bilinear_green": 0,
    "copy_green": 0,
    "in_range_high_red": 1,
    "in_range_low_red": -1,
    "unrepresentable_high_at_rail_green": 0,
    "unrepresentable_high_off_rail_red": -1,
    "unrepresentable_low_at_rail_green": 0,
    "unrepresentable_low_off_rail_red": 1,
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
    ],
    align=False,
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
    ],
    align=False,
)


class Refusal(RuntimeError):
    """The supplied evidence cannot support a measured result."""


@dataclass(frozen=True)
class Placement:
    frame_order: int
    bits: tuple[str, str, str, str]
    a_re: float
    a_im: float
    b_re: float
    b_im: float


@dataclass(frozen=True)
class WarpMap:
    path: Path
    sha256: str
    stack_name: str
    stack_digest: str
    frame_count: int
    width: int
    height: int
    reference: int
    resampler: str
    placements: Mapping[int, Placement | None]


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


class RowSink:
    """Bounded raw structured-row spool that is finalized as a NumPy array."""

    def __init__(self, path: Path, dtype: np.dtype):
        self.path = path
        self.dtype = dtype
        self.count = 0
        self._stream = path.open("xb")

    def append(self, rows: np.ndarray) -> None:
        fixed = np.asarray(rows, dtype=self.dtype)
        if fixed.ndim != 1:
            raise Refusal("violation rows must be one-dimensional")
        if fixed.size:
            self._stream.write(fixed.tobytes(order="C"))
            self.count += int(fixed.size)

    def finish(self, destination: Path, chunk_rows: int = 65536) -> np.ndarray:
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._stream.close()
        output = np.lib.format.open_memmap(
            destination, mode="w+", dtype=self.dtype, shape=(self.count,)
        )
        with self.path.open("rb") as source:
            offset = 0
            while offset < self.count:
                count = min(chunk_rows, self.count - offset)
                raw = source.read(count * self.dtype.itemsize)
                if len(raw) != count * self.dtype.itemsize:
                    raise Refusal(f"truncated violation spool {self.path}")
                output[offset : offset + count] = np.frombuffer(
                    raw, dtype=self.dtype, count=count
                )
                offset += count
            if source.read(1):
                raise Refusal(f"overlong violation spool {self.path}")
        output.flush()
        self.path.unlink()
        return output

    def abort(self) -> None:
        if not self._stream.closed:
            self._stream.close()
        self.path.unlink(missing_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
    except OSError as error:
        raise Refusal(f"cannot hash {path}: {error}") from error
    return digest.hexdigest().upper()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_canonical_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise Refusal(f"cannot read canonical text {path}: {error}") from error
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return sha256_bytes(canonical.encode("utf-8"))


def json_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise Refusal(f"cannot serialize JSON evidence: {error}") from error


def write_bytes(path: Path, payload: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        raise Refusal(f"cannot write {path}: {error}") from error


def write_json(path: Path, value: Any) -> None:
    write_bytes(path, json_bytes(value))


def read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise Refusal(f"{label}: cannot read JSON {path}: {error}") from error


def require_frozen_reference(
    raw: Any,
    path: Path,
    digest: str,
    label: str,
) -> None:
    reference = mapping(raw, label)
    try:
        actual_path = Path(str(reference["path"])).resolve(strict=True)
    except (KeyError, OSError, RuntimeError) as error:
        raise Refusal(f"{label}: referenced path is absent") from error
    if (
        os.path.normcase(str(actual_path))
        != os.path.normcase(str(path.resolve(strict=True)))
        or reference.get("sha256") != digest
    ):
        raise Refusal(f"{label}: path/hash differs from frozen evidence")


def validate_instrument_freeze(
    path: Path,
    *,
    source_commit: str,
    candidate_binary: Path,
    preregistration: Path,
    commissioning_report: Path,
) -> tuple[Path, str]:
    try:
        path = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise Refusal(f"instrument freeze is absent: {path}") from error
    if not path.is_file():
        raise Refusal(f"instrument freeze is not a file: {path}")
    digest = sha256_file(path)
    environment_digest = os.environ.get("STREHL_M8_FREEZE_SHA256", "").upper()
    if not SHA256_RE.fullmatch(environment_digest):
        raise Refusal("STREHL_M8_FREEZE_SHA256 is absent or invalid")
    if environment_digest != digest:
        raise Refusal(
            "instrument-freeze SHA-256 differs from "
            "STREHL_M8_FREEZE_SHA256"
        )
    document = mapping(read_json(path, "instrument freeze"), "instrument freeze")
    if (
        document.get("schema") != "m136-instrument-freeze-v1"
        or document.get("schema_version") != 1
        or document.get("protocol") != PROTOCOL
        or document.get("status") != "FROZEN_PRE_TARGET"
        or str(document.get("source_commit", "")).lower()
        != source_commit.lower()
    ):
        raise Refusal("instrument freeze identity is invalid")
    require_frozen_reference(
        document.get("preregistration"),
        preregistration,
        sha256_file(preregistration),
        "instrument freeze preregistration",
    )
    require_frozen_reference(
        document.get("candidate_binary"),
        candidate_binary,
        sha256_file(candidate_binary),
        "instrument freeze candidate binary",
    )
    instruments = mapping(
        document.get("instruments"), "instrument freeze instruments"
    )
    checker_path = Path(__file__).resolve()
    require_frozen_reference(
        instruments.get("checker"),
        checker_path,
        sha256_file(checker_path),
        "instrument freeze checker",
    )
    commissioning = mapping(
        document.get("commissioning"), "instrument freeze commissioning"
    )
    require_frozen_reference(
        commissioning.get("checker_report"),
        commissioning_report,
        sha256_file(commissioning_report),
        "instrument freeze checker commissioning",
    )
    return path, digest


def mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise Refusal(f"{label} must be a JSON object")
    return value


def exact_keys(value: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    expected_set = set(expected)
    actual = set(value)
    if actual != expected_set:
        raise Refusal(
            f"{label} keys differ: missing={sorted(expected_set - actual)}, "
            f"extra={sorted(actual - expected_set)}"
        )


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Refusal(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise Refusal(f"{label} must be finite")
    return result


def integer(value: Any, label: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise Refusal(f"{label} must be an integer")
    if not low <= value <= high:
        raise Refusal(f"{label} must be in [{low}, {high}]")
    return value


def digest_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise Refusal(f"{label} must be a SHA-256 string")
    normalized = value.upper()
    if SHA256_RE.fullmatch(normalized) is None:
        raise Refusal(f"{label} is not a 64-digit SHA-256")
    return normalized


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def fresh_staging(output: Path) -> Path:
    output = output.resolve()
    if os.path.lexists(output):
        raise Refusal(f"refusing to overwrite output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    leftovers = sorted(output.parent.glob(f".{output.name}.staging-*"))
    if leftovers:
        raise Refusal(f"stale output staging path exists: {leftovers[0]}")
    try:
        return Path(
            tempfile.mkdtemp(
                prefix=f".{output.name}.staging-", dir=output.parent
            )
        )
    except OSError as error:
        raise Refusal(f"cannot create output staging directory: {error}") from error


def publish_staging(staging: Path, output: Path) -> None:
    output = output.resolve()
    if os.path.lexists(output):
        raise Refusal(f"refusing to overwrite output: {output}")
    try:
        os.rename(staging, output)
    except OSError as error:
        raise Refusal(f"cannot atomically publish {output}: {error}") from error


def f32_bits(value: np.float32) -> bytes:
    return np.asarray(value, dtype="<f4").tobytes()


def same_f32(left: np.float32, right: np.float32) -> bool:
    return f32_bits(left) == f32_bits(right)


def same_f64(left: float, right: float) -> bool:
    return struct.pack("<d", left) == struct.pack("<d", right)


def f32_down(value: np.ndarray | float) -> np.ndarray:
    exact = np.asarray(value, dtype=np.float64)
    rounded = np.asarray(exact, dtype=np.float32)
    return np.where(
        rounded.astype(np.float64) > exact,
        np.nextafter(rounded, np.float32(-np.inf), dtype=np.float32),
        rounded,
    ).astype(np.float32)


def f32_up(value: np.ndarray | float) -> np.ndarray:
    exact = np.asarray(value, dtype=np.float64)
    rounded = np.asarray(exact, dtype=np.float32)
    return np.where(
        rounded.astype(np.float64) < exact,
        np.nextafter(rounded, np.float32(np.inf), dtype=np.float32),
        rounded,
    ).astype(np.float32)


def down_add(left: np.ndarray, right: np.ndarray | np.float32) -> np.ndarray:
    return f32_down(
        np.asarray(left, dtype=np.float32).astype(np.float64)
        + np.asarray(right, dtype=np.float32).astype(np.float64)
    )


def up_add(left: np.ndarray, right: np.ndarray | np.float32) -> np.ndarray:
    return f32_up(
        np.asarray(left, dtype=np.float32).astype(np.float64)
        + np.asarray(right, dtype=np.float32).astype(np.float64)
    )


def down_subtract(left: np.ndarray, right: np.ndarray | np.float32) -> np.ndarray:
    return f32_down(
        np.asarray(left, dtype=np.float32).astype(np.float64)
        - np.asarray(right, dtype=np.float32).astype(np.float64)
    )


def up_subtract(left: np.ndarray, right: np.ndarray | np.float32) -> np.ndarray:
    return f32_up(
        np.asarray(left, dtype=np.float32).astype(np.float64)
        - np.asarray(right, dtype=np.float32).astype(np.float64)
    )


def down_multiply(left: np.ndarray, right: np.ndarray | np.float32) -> np.ndarray:
    return f32_down(
        np.asarray(left, dtype=np.float32).astype(np.float64)
        * np.asarray(right, dtype=np.float32).astype(np.float64)
    )


def up_multiply(left: np.ndarray, right: np.ndarray | np.float32) -> np.ndarray:
    return f32_up(
        np.asarray(left, dtype=np.float32).astype(np.float64)
        * np.asarray(right, dtype=np.float32).astype(np.float64)
    )


def down_divide(left: np.ndarray, right: np.float32) -> np.ndarray:
    return f32_down(
        np.asarray(left, dtype=np.float32).astype(np.float64)
        / float(np.float32(right))
    )


def up_divide(left: np.ndarray, right: np.float32) -> np.ndarray:
    return f32_up(
        np.asarray(left, dtype=np.float32).astype(np.float64)
        / float(np.float32(right))
    )


def round_ties_away_u16(value: np.ndarray) -> np.ndarray:
    """Round binary32 values away from zero at ties, then clamp to u16."""

    values = np.asarray(value, dtype=np.float32)
    rounded = np.where(
        values >= np.float32(0.0),
        np.floor(values.astype(np.float64) + 0.5),
        np.ceil(values.astype(np.float64) - 0.5),
    )
    return np.asarray(np.clip(rounded, 0, U16_MAX), dtype=np.uint16)


def source_interval(
    lo: np.ndarray, hi: np.ndarray, tau: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    return down_subtract(lo, tau), up_add(hi, tau)


def intermediate_interval(
    lo: np.ndarray,
    hi: np.ndarray,
    site_gain: np.float32,
    black_level: np.float32,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Replay f32 inverse gain/multiply, pedestal, u16, and black removal."""

    inverse_gain = np.divide(
        np.float32(1.0), site_gain, dtype=np.float32
    )
    scaled_lo = down_multiply(lo, inverse_gain)
    scaled_hi = up_multiply(hi, inverse_gain)
    restored_lo = down_add(scaled_lo, black_level)
    restored_hi = up_add(scaled_hi, black_level)
    u_lo = round_ties_away_u16(restored_lo)
    u_hi = round_ties_away_u16(restored_hi)
    black_lo = down_subtract(u_lo.astype(np.float32), black_level)
    black_hi = up_subtract(u_hi.astype(np.float32), black_level)
    np.maximum(black_lo, np.float32(0.0), out=black_lo)
    np.maximum(black_hi, np.float32(0.0), out=black_hi)
    return black_lo, black_hi, u_lo, u_hi


def output_interval(
    black_lo: np.ndarray,
    black_hi: np.ndarray,
    output_gain: np.float32,
    sensor_range: np.float32,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    multiplied_lo = down_multiply(black_lo, output_gain)
    multiplied_hi = up_multiply(black_hi, output_gain)
    pre_lo = down_divide(multiplied_lo, sensor_range)
    pre_hi = up_divide(multiplied_hi, sensor_range)
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
    lower_sum = down_add(g1_lo, g2_lo)
    upper_sum = up_add(g1_hi, g2_hi)
    lower_mean = down_multiply(lower_sum, np.float32(0.5))
    upper_mean = up_multiply(upper_sum, np.float32(0.5))
    np.maximum(lower_mean, np.float32(0.0), out=lower_mean)
    np.maximum(upper_mean, np.float32(0.0), out=upper_mean)
    return output_interval(lower_mean, upper_mean, output_gain, sensor_range)


def comparison(
    encoded: np.ndarray | int,
    lower: np.ndarray | float,
    upper: np.ndarray | float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    value = np.asarray(encoded, dtype=np.float64) / float(U16_MAX)
    lower64 = np.asarray(lower, dtype=np.float64)
    upper64 = np.asarray(upper, dtype=np.float64)
    return value < lower64 - FINAL_Q, value > upper64 + FINAL_Q, value


def validate_preregistration(path: Path) -> Mapping[str, Any]:
    frozen = PREREGISTRATION_PATH
    path = path.resolve()
    if path != frozen:
        raise Refusal(f"preregistration must be the frozen file {frozen}")
    if sha256_file(path) != PREREG_SHA256:
        raise Refusal(f"frozen preregistration hash differs from {PREREG_SHA256}")
    prereg = mapping(read_json(path, "preregistration"), "preregistration")
    if prereg.get("protocol") != PROTOCOL:
        raise Refusal("preregistration protocol mismatch")
    if prereg.get("status") != "PREREGISTERED_NOT_EXECUTED":
        raise Refusal("preregistration status is not frozen pre-execution state")
    commissioning = mapping(
        prereg.get("commissioning"), "preregistration.commissioning"
    )
    numeric = mapping(
        commissioning.get("m8_o_numeric_cases"),
        "preregistration commissioning numeric cases",
    )
    if set(numeric) != set(NUMERIC_DIRECTIONS):
        raise Refusal("preregistration numeric case names differ from the frozen eight")
    return prereg


def validate_fixture(fixtures: Path) -> dict[str, Any]:
    fixtures = fixtures.resolve()
    if not fixtures.is_dir():
        raise Refusal(f"fixture directory is absent: {fixtures}")
    manifest_path = fixtures / "manifest.json"
    manifest = mapping(read_json(manifest_path, "fixture manifest"), "fixture manifest")
    exact_keys(
        manifest,
        (
            "schema",
            "schema_version",
            "preregistration",
            "prospective_interpretation",
            "fixture_semantics",
            "expected_outcomes",
            "artifacts",
        ),
        "fixture manifest",
    )
    if (
        manifest["schema"] != FIXTURE_SCHEMA
        or manifest["schema_version"] != FIXTURE_VERSION
    ):
        raise Refusal("unsupported fixture manifest schema/version")

    prereg_entry = mapping(
        manifest["preregistration"], "fixture manifest preregistration"
    )
    exact_keys(
        prereg_entry,
        ("path", "sha256", "protocol", "status", "result"),
        "fixture manifest preregistration",
    )
    raw_prereg_path = prereg_entry["path"]
    if not isinstance(raw_prereg_path, str) or not raw_prereg_path:
        raise Refusal("fixture preregistration path is invalid")
    prereg_path = Path(raw_prereg_path)
    if not prereg_path.is_absolute():
        raise Refusal("fixture preregistration path must be absolute")
    prereg = validate_preregistration(prereg_path)
    prereg_hash = sha256_file(prereg_path)
    if digest_text(prereg_entry["sha256"], "fixture preregistration hash") != prereg_hash:
        raise Refusal("fixture preregistration hash mismatch")
    for key in ("protocol", "status", "result"):
        if prereg_entry[key] != prereg.get(key):
            raise Refusal(f"fixture preregistration {key} mismatch")

    interpretation_path = INTERPRETATION_PATH
    interpretation_entry = mapping(
        manifest["prospective_interpretation"],
        "fixture manifest prospective interpretation",
    )
    exact_keys(
        interpretation_entry,
        ("path", "sha256", "canonical_sha256", "commit"),
        "fixture manifest prospective interpretation",
    )
    if (
        Path(str(interpretation_entry["path"])).resolve() != interpretation_path
        or interpretation_entry["sha256"] != sha256_file(interpretation_path)
        or interpretation_entry["canonical_sha256"]
        != INTERPRETATION_CANONICAL_SHA256
        or interpretation_entry["commit"] != INTERPRETATION_COMMIT
        or sha256_canonical_text(interpretation_path)
        != INTERPRETATION_CANONICAL_SHA256
    ):
        raise Refusal("fixture prospective-interpretation identity mismatch")

    semantics = mapping(manifest["fixture_semantics"], "fixture semantics")
    if semantics.get("numeric_cases") != NUMERIC_REPRESENTATION:
        raise Refusal("fixture does not label the adopted fixture identity map")

    artifact_rows = manifest["artifacts"]
    if not isinstance(artifact_rows, list):
        raise Refusal("fixture artifacts must be an array")
    artifacts: dict[str, Path] = {}
    for index, raw_row in enumerate(artifact_rows):
        row = mapping(raw_row, f"fixture artifact {index}")
        exact_keys(row, ("path", "bytes", "sha256"), f"fixture artifact {index}")
        relative = row["path"]
        if (
            not isinstance(relative, str)
            or not relative
            or Path(relative).name != relative
        ):
            raise Refusal(f"fixture artifact {index} is not a direct child")
        path = (fixtures / relative).resolve()
        if not is_relative_to(path, fixtures) or not path.is_file():
            raise Refusal(f"fixture artifact is absent or escapes root: {relative!r}")
        if relative in artifacts:
            raise Refusal(f"duplicate fixture artifact: {relative}")
        expected_bytes = integer(
            row["bytes"], f"fixture artifact {relative} bytes", 0, 1 << 63
        )
        if path.stat().st_size != expected_bytes:
            raise Refusal(f"fixture artifact byte count mismatch: {relative}")
        expected_hash = digest_text(
            row["sha256"], f"fixture artifact {relative} hash"
        )
        observed_hash = sha256_file(path)
        if observed_hash != expected_hash:
            raise Refusal(
                f"fixture artifact hash mismatch: {relative}: "
                f"{observed_hash} != {expected_hash}"
            )
        artifacts[relative] = path
    if not FIXTURE_BASE_FILES.issubset(artifacts):
        raise Refusal(
            "fixture base artifact set differs: "
            f"missing={sorted(FIXTURE_BASE_FILES - set(artifacts))}"
        )

    fail_closed_document = mapping(
        read_json(artifacts["fail-closed-cases.json"], "fail-closed fixture"),
        "fail-closed fixture",
    )
    exact_keys(
        fail_closed_document,
        (
            "schema_version",
            "source",
            "preregistered_controls",
            "source_frame",
            "trace_rejection",
            "frame_site_set",
            "producer_fields",
            "m8_r",
        ),
        "fail-closed fixture",
    )
    if (
        fail_closed_document["schema_version"] != 1
        or fail_closed_document["source"] != "commissioning.fail_closed"
        or fail_closed_document["preregistered_controls"]
        != list(FAIL_CLOSED_CONTROLS)
    ):
        raise Refusal("fail-closed fixture header or frozen controls mismatch")

    source_frame = mapping(
        fail_closed_document["source_frame"], "fail-closed source frame"
    )
    exact_keys(source_frame, ("path", "sha256"), "fail-closed source frame")
    expected_source_frame = Path(__file__).with_name("fixture_m136.py").resolve()
    if (
        Path(str(source_frame["path"])).resolve() != expected_source_frame
        or digest_text(
            source_frame["sha256"], "fail-closed source-frame SHA-256"
        )
        != sha256_file(expected_source_frame)
    ):
        raise Refusal("fail-closed source-frame identity mismatch")

    trace_rejection = mapping(
        fail_closed_document["trace_rejection"], "fail-closed trace rejection"
    )
    exact_keys(
        trace_rejection,
        ("v2_without_black_level", "missing_crop_origin"),
        "fail-closed trace rejection",
    )
    declared_fail_artifacts: set[str] = set()

    def validate_trace_reference(
        raw: Any,
        label: str,
        *,
        extra_keys: Sequence[str] = (),
    ) -> Mapping[str, Any]:
        reference = mapping(raw, label)
        exact_keys(
            reference,
            ("artifact", "trace_name", *extra_keys),
            label,
        )
        artifact = str(reference["artifact"])
        trace_name = str(reference["trace_name"])
        if Path(artifact).name != artifact or TRACE_NAME.fullmatch(trace_name) is None:
            raise Refusal(f"{label}: malformed artifact or canonical trace name")
        declared_fail_artifacts.add(artifact)
        return reference

    for name in ("v2_without_black_level", "missing_crop_origin"):
        control = validate_trace_reference(
            trace_rejection[name],
            f"fail-closed {name}",
            extra_keys=("expected_status",),
        )
        if control["expected_status"] != "UNMEASURED":
            raise Refusal(f"fail-closed {name} expected status differs")

    frame_site_set = mapping(
        fail_closed_document["frame_site_set"], "fail-closed frame/site set"
    )
    exact_keys(
        frame_site_set,
        (
            "complete",
            "missing",
            "duplicate_extra",
            "expected_missing_status",
            "expected_duplicate_status",
        ),
        "fail-closed frame/site set",
    )
    complete = frame_site_set["complete"]
    missing = frame_site_set["missing"]
    if (
        not isinstance(complete, list)
        or len(complete) != 4
        or not isinstance(missing, list)
        or missing != complete[:-1]
        or frame_site_set["expected_missing_status"] != "UNMEASURED"
        or frame_site_set["expected_duplicate_status"] != "UNMEASURED"
    ):
        raise Refusal("fail-closed frame/site fixture is malformed")
    for index, reference in enumerate(complete):
        validate_trace_reference(
            reference, f"fail-closed complete trace {index}"
        )
    validate_trace_reference(
        frame_site_set["duplicate_extra"], "fail-closed duplicate trace"
    )

    producer_fields = mapping(
        fail_closed_document["producer_fields"], "fail-closed producer fields"
    )
    exact_keys(
        producer_fields,
        ("hull", "contributor_mask", "expected"),
        "fail-closed producer fields",
    )
    if producer_fields["expected"] != "ignored":
        raise Refusal("producer-field fixture does not require ignore semantics")
    declared_fail_artifacts.update(
        (str(producer_fields["hull"]), str(producer_fields["contributor_mask"]))
    )

    m8r_document = mapping(fail_closed_document["m8_r"], "fail-closed M8-R")
    exact_keys(m8r_document, ("controls",), "fail-closed M8-R")
    m8r_controls = mapping(
        m8r_document["controls"], "fail-closed M8-R controls"
    )
    expected_m8r = {
        "catmull_hard_step": "red",
        "clamped_hard_step": "green",
        "widened_clamp_sabotage": "red",
        "copy_null": "green",
        "clamped_copy_null": "green",
        "convex_bilinear_null": "green",
        "explicit_high_low": "red",
    }
    if set(m8r_controls) != set(expected_m8r):
        raise Refusal("fail-closed M8-R control names differ")
    for name, expected in expected_m8r.items():
        control = validate_trace_reference(
            m8r_controls[name],
            f"fail-closed M8-R {name}",
            extra_keys=("expected",),
        )
        if control["expected"] != expected:
            raise Refusal(f"fail-closed M8-R {name} expected class differs")

    expected_files = FIXTURE_BASE_FILES | declared_fail_artifacts
    if set(artifacts) != expected_files:
        raise Refusal(
            "fixture artifact set differs: "
            f"missing={sorted(expected_files - set(artifacts))}, "
            f"extra={sorted(set(artifacts) - expected_files)}"
        )
    for name in declared_fail_artifacts:
        if Path(name).name != name or name not in artifacts:
            raise Refusal(f"fail-closed artifact is absent/not direct: {name!r}")
    actual_files = {
        path.name
        for path in fixtures.iterdir()
        if path.is_file() and path.name != "manifest.json"
    }
    if actual_files != expected_files:
        raise Refusal(
            "fixture directory contains unmanifested or missing files: "
            f"missing={sorted(expected_files - actual_files)}, "
            f"extra={sorted(actual_files - expected_files)}"
        )

    commissioning = mapping(prereg["commissioning"], "preregistration commissioning")
    if commissioning.get("fail_closed") != list(FAIL_CLOSED_CONTROLS):
        raise Refusal("preregistration fail-closed controls differ from frozen seven")
    numeric_document = mapping(
        read_json(artifacts["m8-o-numeric-cases.json"], "numeric cases"),
        "numeric cases",
    )
    exact_keys(
        numeric_document,
        ("schema_version", "source", "case_count", "cases"),
        "numeric cases",
    )
    if (
        numeric_document["schema_version"] != 1
        or numeric_document["source"] != "commissioning.m8_o_numeric_cases"
        or numeric_document["case_count"] != 8
    ):
        raise Refusal("numeric fixture header mismatch")
    numeric_cases = mapping(numeric_document["cases"], "numeric fixture cases")
    if set(numeric_cases) != set(NUMERIC_DIRECTIONS):
        raise Refusal("numeric fixture does not contain the frozen eight cases")
    prereg_numeric = mapping(
        commissioning["m8_o_numeric_cases"], "preregistration numeric cases"
    )
    for name in NUMERIC_DIRECTIONS:
        case = mapping(numeric_cases[name], f"numeric case {name}")
        exact_keys(
            case,
            (*NUMERIC_FIELDS, "representation_map"),
            f"numeric case {name}",
        )
        if case["representation_map"] != NUMERIC_REPRESENTATION:
            raise Refusal(f"{name}: representation label mismatch")
        expected_case = mapping(prereg_numeric[name], f"preregistration case {name}")
        if {field: case[field] for field in NUMERIC_FIELDS} != {
            field: expected_case[field] for field in NUMERIC_FIELDS
        }:
            raise Refusal(f"{name}: fixture values differ from preregistration")

    intermediate_document = mapping(
        read_json(
            artifacts["intermediate-quantizer-case.json"],
            "intermediate quantizer fixture",
        ),
        "intermediate quantizer fixture",
    )
    exact_keys(
        intermediate_document,
        ("schema_version", "source", "case"),
        "intermediate quantizer fixture",
    )
    if (
        intermediate_document["schema_version"] != 1
        or intermediate_document["source"]
        != "commissioning.intermediate_quantizer_case"
    ):
        raise Refusal("intermediate quantizer fixture header mismatch")
    intermediate = mapping(
        intermediate_document["case"], "intermediate quantizer case"
    )
    exact_keys(intermediate, INTERMEDIATE_FIELDS, "intermediate quantizer case")
    prereg_intermediate = mapping(
        commissioning["intermediate_quantizer_case"],
        "preregistration intermediate case",
    )
    if dict(intermediate) != {
        field: prereg_intermediate[field] for field in INTERMEDIATE_FIELDS
    }:
        raise Refusal("intermediate fixture differs from preregistration")

    crop_document = mapping(
        read_json(artifacts["crop-origin-case.json"], "crop-origin fixture"),
        "crop-origin fixture",
    )
    exact_keys(
        crop_document,
        (
            "schema_version",
            "source",
            "case",
            "source_grid",
            "correct_origin_tiff",
            "wrong_origin_tiff",
            "serialization",
        ),
        "crop-origin fixture",
    )
    if (
        crop_document["schema_version"] != 1
        or crop_document["source"] != "commissioning.crop_origin_case"
    ):
        raise Refusal("crop-origin fixture header mismatch")
    crop = mapping(crop_document["case"], "crop-origin case")
    exact_keys(crop, CROP_FIELDS, "crop-origin case")
    prereg_crop = mapping(
        commissioning["crop_origin_case"], "preregistration crop-origin case"
    )
    if dict(crop) != {field: prereg_crop[field] for field in CROP_FIELDS}:
        raise Refusal("crop-origin fixture differs from preregistration")

    outcomes = mapping(manifest["expected_outcomes"], "fixture expected outcomes")
    exact_keys(
        outcomes,
        (
            "m8_o_numeric_cases",
            "intermediate_quantizer_case",
            "crop_origin_case",
            "fail_closed",
        ),
        "fixture expected outcomes",
    )
    if dict(mapping(outcomes["m8_o_numeric_cases"], "numeric outcomes")) != {
        name: prereg_numeric[name]["expected_violations"]
        for name in prereg_numeric
    }:
        raise Refusal("numeric manifest outcomes differ from preregistration")
    expected_intermediate_outcomes = {
        field: prereg_intermediate[field]
        for field in (
            "expected_intermediate_u16",
            "expected_pre_final",
            "green_encoded",
            "red_encoded",
        )
    }
    if (
        dict(mapping(outcomes["intermediate_quantizer_case"], "intermediate outcomes"))
        != expected_intermediate_outcomes
    ):
        raise Refusal("intermediate manifest outcomes differ from preregistration")
    expected_crop_outcome = {
        "expected_wrong_origin_violations": prereg_crop[
            "expected_wrong_origin_violations"
        ]
    }
    if dict(mapping(outcomes["crop_origin_case"], "crop outcomes")) != expected_crop_outcome:
        raise Refusal("crop manifest outcome differs from preregistration")
    if outcomes["fail_closed"] != list(FAIL_CLOSED_CONTROLS):
        raise Refusal("fail-closed manifest outcomes differ from preregistration")

    return {
        "fixtures": fixtures,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "manifest_sha256": sha256_file(manifest_path),
        "preregistration_path": prereg_path,
        "preregistration": prereg,
        "preregistration_sha256": prereg_hash,
        "interpretation_path": interpretation_path,
        "interpretation_sha256": sha256_file(interpretation_path),
        "interpretation_canonical_sha256": INTERPRETATION_CANONICAL_SHA256,
        "artifacts": artifacts,
        "numeric": numeric_cases,
        "intermediate": intermediate,
        "crop": crop,
        "fail_closed": fail_closed_document,
        "source_frame": expected_source_frame,
    }


def scalar_control(
    name: str,
    encoded: int,
    lower: float,
    upper: float,
    expected_count: int,
    expected_direction: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    low, high, value = comparison(encoded, lower, upper)
    is_low = bool(np.asarray(low))
    is_high = bool(np.asarray(high))
    observed_count = int(is_low) + int(is_high)
    direction = -1 if is_low else 1 if is_high else 0
    passed = (
        observed_count == expected_count and direction == expected_direction
    )
    evidence: list[dict[str, Any]] = []
    if direction:
        evidence.append(
            {
                "control": name,
                "direction": direction,
                "encoded": encoded,
                "decoded": float(value),
                "L": float(lower),
                "H": float(upper),
                "q": FINAL_Q,
                "signed_excess": (
                    float(value) - float(upper)
                    if direction > 0
                    else float(value) - float(lower)
                ),
            }
        )
    return (
        {
            "status": "PASS" if passed else "FAIL",
            "encoded": encoded,
            "decoded": float(value),
            "L": float(lower),
            "H": float(upper),
            "q": FINAL_Q,
            "expected_violations": expected_count,
            "observed_violations": observed_count,
            "expected_direction": expected_direction,
            "observed_direction": direction,
        },
        evidence,
    )


def load_gray_u16_tiff(path: Path, height: int, width: int) -> np.ndarray:
    try:
        with tifffile.TiffFile(path) as tiff:
            if len(tiff.series) != 1 or len(tiff.pages) != 1:
                raise Refusal(f"{path}: expected one TIFF image and page")
            series = tiff.series[0]
            if series.shape != (height, width) or series.dtype != np.dtype(np.uint16):
                raise Refusal(
                    f"{path}: expected uint16 {(height, width)}, "
                    f"got {series.dtype} {series.shape}"
                )
            page = tiff.pages[0]
            if int(page.samplesperpixel) != 1:
                raise Refusal(f"{path}: expected one grayscale sample per pixel")
            return np.asarray(series.asarray(), dtype=np.uint16)
    except Refusal:
        raise
    except (OSError, ValueError, tifffile.TiffFileError) as error:
        raise Refusal(f"cannot read TIFF {path}: {error}") from error


def score_fail_closed(data: Mapping[str, Any]) -> dict[str, Any]:
    fixture = mapping(data["fail_closed"], "fail-closed fixture")
    artifacts: Mapping[str, Path] = data["artifacts"]
    source_frame = Path(data["source_frame"])
    trace_rejection = mapping(
        fixture["trace_rejection"], "fail-closed trace rejection"
    )
    frame_site_set = mapping(
        fixture["frame_site_set"], "fail-closed frame/site set"
    )
    producer_fields = mapping(
        fixture["producer_fields"], "fail-closed producer fields"
    )
    m8r_controls = mapping(
        mapping(fixture["m8_r"], "fail-closed M8-R")["controls"],
        "fail-closed M8-R controls",
    )

    def expected_refusal(
        label: str,
        action: Any,
        required_text: str,
    ) -> dict[str, Any]:
        try:
            action()
        except Refusal as error:
            reason = str(error)
            passed = required_text in reason
            return {
                "status": "PASS" if passed else "FAIL",
                "expected": "UNMEASURED",
                "observed": "UNMEASURED",
                "reason": reason,
                "required_reason_fragment": required_text,
            }
        except Exception as error:
            return {
                "status": "FAIL",
                "expected": "UNMEASURED",
                "observed": type(error).__name__,
                "reason": str(error),
                "required_reason_fragment": required_text,
            }
        return {
            "status": "FAIL",
            "expected": "UNMEASURED",
            "observed": "ACCEPTED",
            "reason": f"{label} was incorrectly accepted",
            "required_reason_fragment": required_text,
        }

    v2_reference = mapping(
        trace_rejection["v2_without_black_level"], "v2 control"
    )
    missing_crop_reference = mapping(
        trace_rejection["missing_crop_origin"], "crop control"
    )

    placement = Placement(
        frame_order=0,
        bits=(
            "3ff0000000000000",
            "0000000000000000",
            "3fd0000000000000",
            "3fd0000000000000",
        ),
        a_re=1.0,
        a_im=0.0,
        b_re=0.25,
        b_im=0.25,
    )
    warpmap = WarpMap(
        path=Path(data["fixtures"]) / "fail-closed-cases.json",
        sha256=sha256_file(Path(data["fixtures"]) / "fail-closed-cases.json"),
        stack_name="m136-commission",
        stack_digest="0000000000000000",
        frame_count=1,
        width=20,
        height=16,
        reference=0,
        resampler="clamped-catmull",
        placements={0: placement},
    )

    complete_references = [
        mapping(reference, "complete trace reference")
        for reference in frame_site_set["complete"]
    ]
    missing_references = [
        mapping(reference, "missing trace reference")
        for reference in frame_site_set["missing"]
    ]
    duplicate_reference = mapping(
        frame_site_set["duplicate_extra"], "duplicate trace reference"
    )

    with tempfile.TemporaryDirectory(prefix="m136-fail-closed-") as temporary:
        root = Path(temporary)

        def materialize_trace(reference: Mapping[str, Any], directory: Path) -> Path:
            destination = directory / str(reference["trace_name"])
            shutil.copyfile(artifacts[str(reference["artifact"])], destination)
            return destination

        def make_state(
            name: str,
            references: Sequence[Mapping[str, Any]],
            *,
            include_producer_fields: bool = False,
        ) -> Path:
            state = root / name
            block_dir = state / "blocks"
            block_dir.mkdir(parents=True)
            for reference in references:
                materialize_trace(reference, block_dir)
            if include_producer_fields:
                for field in ("hull", "contributor_mask"):
                    artifact_name = str(producer_fields[field])
                    shutil.copyfile(
                        artifacts[artifact_name], state / artifact_name
                    )
            return state

        rejection_dir = root / "rejection"
        rejection_dir.mkdir()
        v2_path = materialize_trace(v2_reference, rejection_dir)
        missing_crop_path = materialize_trace(
            missing_crop_reference, rejection_dir
        )
        v2_result = expected_refusal(
            "trace v2 without black level",
            lambda: parse_trace(v2_path, {}),
            "requires b'M8SITE03' version 3",
        )
        missing_crop_result = expected_refusal(
            "trace without crop origin",
            lambda: parse_trace(missing_crop_path, {}),
            "truncated trace-v3 header",
        )

        missing_state = make_state("missing", missing_references)
        duplicate_state = make_state(
            "duplicate", [*complete_references, duplicate_reference]
        )
        ignored_state = make_state(
            "producer-fields",
            complete_references,
            include_producer_fields=True,
        )
        missing_result = expected_refusal(
            "missing frame/site",
            lambda: trace_blocks(missing_state, warpmap, [source_frame]),
            "incomplete trace set",
        )
        duplicate_result = expected_refusal(
            "duplicate frame/site",
            lambda: trace_blocks(duplicate_state, warpmap, [source_frame]),
            "duplicate frame/site trace",
        )
        try:
            parsed_blocks, _, _ = trace_blocks(
                ignored_state, warpmap, [source_frame]
            )
            producer_result = {
                "status": "PASS" if len(parsed_blocks) == 4 else "FAIL",
                "expected": "ignored",
                "observed_trace_blocks": len(parsed_blocks),
                "sentinel_artifacts": [
                    str(producer_fields["hull"]),
                    str(producer_fields["contributor_mask"]),
                ],
            }
        except Exception as error:
            producer_result = {
                "status": "FAIL",
                "expected": "ignored",
                "observed": type(error).__name__,
                "reason": str(error),
            }

        expected_m8r_counts = {
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
            "copy_null": {
                "denominator": 252,
                "lower_violations": 0,
                "upper_violations": 0,
                "violations": 0,
            },
            "clamped_copy_null": {
                "denominator": 252,
                "lower_violations": 0,
                "upper_violations": 0,
                "violations": 0,
            },
            "convex_bilinear_null": {
                "denominator": 252,
                "lower_violations": 0,
                "upper_violations": 0,
                "violations": 0,
            },
            "explicit_high_low": {
                "denominator": 252,
                "lower_violations": 1,
                "upper_violations": 1,
                "violations": 2,
            },
        }
        m8r_results: dict[str, Any] = {}
        for name in sorted(m8r_controls):
            control = mapping(m8r_controls[name], f"M8-R control {name}")
            expected = str(control["expected"])
            block_sink: RowSink | None = None
            aggregate_sink: RowSink | None = None
            arrays: list[np.ndarray] = []
            try:
                control_root = root / f"m8r-{name}"
                control_root.mkdir()
                trace_path = materialize_trace(control, control_root)
                block = parse_trace(trace_path, {})
                block_sink = RowSink(
                    control_root / "block.raw", M8R_VIOLATION_DTYPE
                )
                aggregate_sink = RowSink(
                    control_root / "aggregate.raw", M8R_VIOLATION_DTYPE
                )
                summary = verify_m8r_block(
                    block,
                    chunk_rows=2,
                    block_sink=block_sink,
                    aggregate_sink=aggregate_sink,
                )
                rows = block_sink.finish(control_root / "block.npy")
                arrays.append(rows)
                aggregate_rows = aggregate_sink.finish(
                    control_root / "aggregate.npy"
                )
                arrays.append(aggregate_rows)
                violations = int(summary["violation_rows"])
                directions = sorted(
                    int(direction) for direction in np.unique(rows["direction"])
                )
                observed_counts = {
                    "denominator": int(summary["eligible_samples"]),
                    "lower_violations": int(summary["lower_violation_rows"]),
                    "upper_violations": int(summary["upper_violation_rows"]),
                    "violations": violations,
                }
                expected_counts = expected_m8r_counts[name]
                expected_directions = (
                    []
                    if expected_counts["violations"] == 0
                    else [-1, 1]
                )
                passed = (
                    observed_counts == expected_counts
                    and directions == expected_directions
                    and (
                        (expected == "green" and violations == 0)
                        or (expected == "red" and violations > 0)
                    )
                )
                m8r_results[name] = {
                    "status": "PASS" if passed else "FAIL",
                    "expected": expected,
                    "expected_counts": expected_counts,
                    "eligible_samples": summary["eligible_samples"],
                    "lower_violations": summary["lower_violation_rows"],
                    "upper_violations": summary["upper_violation_rows"],
                    "observed_violations": violations,
                    "observed_directions": directions,
                    "gathered_sha256": hashlib.sha256(
                        np.asarray(block.gathered(), dtype="<f4").tobytes(
                            order="C"
                        )
                    ).hexdigest().upper(),
                    "max_excess_over_tolerance": summary[
                        "max_excess_over_tolerance"
                    ],
                }
            except Exception as error:
                m8r_results[name] = {
                    "status": "FAIL",
                    "expected": expected,
                    "observed": type(error).__name__,
                    "reason": str(error),
                }
            finally:
                if block_sink is not None:
                    block_sink.abort()
                if aggregate_sink is not None:
                    aggregate_sink.abort()
                for array in arrays:
                    close_memmap(array)

    grouped_controls = {
        FAIL_CLOSED_CONTROLS[0]: v2_result,
        FAIL_CLOSED_CONTROLS[1]: missing_crop_result,
        FAIL_CLOSED_CONTROLS[2]: {
            "status": (
                "PASS"
                if missing_result["status"] == "PASS"
                and duplicate_result["status"] == "PASS"
                else "FAIL"
            ),
            "missing": missing_result,
            "duplicate": duplicate_result,
        },
        FAIL_CLOSED_CONTROLS[3]: producer_result,
        FAIL_CLOSED_CONTROLS[4]: m8r_results["catmull_hard_step"],
        FAIL_CLOSED_CONTROLS[5]: {
            "status": (
                "PASS"
                if all(
                    m8r_results[name]["status"] == "PASS"
                    for name in (
                        "clamped_hard_step",
                        "copy_null",
                        "clamped_copy_null",
                        "convex_bilinear_null",
                    )
                )
                else "FAIL"
            ),
            "clamped_hard_step": m8r_results["clamped_hard_step"],
            "copy_null": m8r_results["copy_null"],
            "clamped_copy_null": m8r_results["clamped_copy_null"],
            "convex_bilinear_null": m8r_results["convex_bilinear_null"],
        },
        FAIL_CLOSED_CONTROLS[6]: {
            "status": (
                "PASS"
                if m8r_results["widened_clamp_sabotage"]["status"] == "PASS"
                and m8r_results["explicit_high_low"]["status"] == "PASS"
                else "FAIL"
            ),
            "widened_clamp_sabotage": m8r_results[
                "widened_clamp_sabotage"
            ],
            "explicit_high_low": m8r_results["explicit_high_low"],
        },
    }
    passed = sum(
        result["status"] == "PASS" for result in grouped_controls.values()
    )
    arms = {
        name: {
            "denominator": int(result.get("eligible_samples", -1)),
            "lower_violations": int(result.get("lower_violations", -1)),
            "upper_violations": int(result.get("upper_violations", -1)),
            "violations": int(result.get("observed_violations", -1)),
        }
        for name, result in m8r_results.items()
    }
    copy_hash = m8r_results["copy_null"].get("gathered_sha256")
    clamped_copy_hash = m8r_results["clamped_copy_null"].get(
        "gathered_sha256"
    )
    m8r_passed = (
        all(result["status"] == "PASS" for result in m8r_results.values())
        and copy_hash is not None
        and copy_hash == clamped_copy_hash
    )
    return {
        "status": "PASS" if passed == len(FAIL_CLOSED_CONTROLS) else "FAIL",
        "expected": len(FAIL_CLOSED_CONTROLS),
        "passed": passed,
        "controls": grouped_controls,
        "m8_r_kernel_cases": {
            "status": "PASS" if m8r_passed else "FAIL",
            "arms": arms,
            "clamped_copy_bit_exact": copy_hash == clamped_copy_hash,
        },
    }


def score_commission_fixture(data: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    numeric_results: dict[str, Any] = {}
    evidence_rows: list[dict[str, Any]] = []
    control_statuses: dict[str, str] = {}

    for name in sorted(NUMERIC_DIRECTIONS):
        case = data["numeric"][name]
        lo = finite_number(case["lo"], f"{name}.lo")
        hi = finite_number(case["hi"], f"{name}.hi")
        tau = finite_number(case["tau"], f"{name}.tau")
        if tau < 0.0 or lo > hi:
            raise Refusal(f"{name}: invalid source interval")
        lower = min(1.0, max(0.0, lo - tau))
        upper = min(1.0, max(0.0, hi + tau))
        result, rows = scalar_control(
            name,
            integer(case["encoded"], f"{name}.encoded", 0, U16_MAX),
            lower,
            upper,
            integer(
                case["expected_violations"],
                f"{name}.expected_violations",
                0,
                1,
            ),
            NUMERIC_DIRECTIONS[name],
        )
        result["representation_map"] = NUMERIC_REPRESENTATION
        numeric_results[name] = result
        control_statuses[name] = result["status"]
        evidence_rows.extend(rows)

    case = data["intermediate"]
    lo_value = np.float32(finite_number(case["lo"], "intermediate.lo"))
    hi_value = np.float32(finite_number(case["hi"], "intermediate.hi"))
    tau_value = np.float32(finite_number(case["tau"], "intermediate.tau"))
    if float(tau_value) < 0.0 or float(lo_value) > float(hi_value):
        raise Refusal("intermediate quantizer interval is invalid")
    source_lo, source_hi = source_interval(
        np.asarray([[lo_value]], dtype=np.float32),
        np.asarray([[hi_value]], dtype=np.float32),
        np.asarray([[tau_value]], dtype=np.float32),
    )
    black_lo, black_hi, u_lo, u_hi = intermediate_interval(
        source_lo,
        source_hi,
        np.float32(finite_number(case["g"], "intermediate.g")),
        np.float32(finite_number(case["b"], "intermediate.b")),
    )
    pre_lo, pre_hi, projected_lo, projected_hi = output_interval(
        black_lo,
        black_hi,
        np.float32(finite_number(case["G"], "intermediate.G")),
        np.float32(finite_number(case["R"], "intermediate.R")),
    )
    expected_u16 = integer(
        case["expected_intermediate_u16"],
        "intermediate.expected_intermediate_u16",
        0,
        U16_MAX,
    )
    expected_pre = np.float32(
        finite_number(case["expected_pre_final"], "intermediate.expected_pre_final")
    )
    native_exact = (
        int(u_lo[0, 0]) == expected_u16
        and int(u_hi[0, 0]) == expected_u16
        and float(pre_lo[0, 0]) <= float(expected_pre) <= float(pre_hi[0, 0])
    )
    green_result, green_rows = scalar_control(
        "intermediate_quantizer_green",
        integer(case["green_encoded"], "intermediate.green_encoded", 0, U16_MAX),
        float(projected_lo[0, 0]),
        float(projected_hi[0, 0]),
        0,
        0,
    )
    red_result, red_rows = scalar_control(
        "intermediate_quantizer_red",
        integer(case["red_encoded"], "intermediate.red_encoded", 0, U16_MAX),
        float(projected_lo[0, 0]),
        float(projected_hi[0, 0]),
        1,
        1,
    )
    intermediate_result = {
        "status": (
            "PASS"
            if native_exact
            and green_result["status"] == "PASS"
            and red_result["status"] == "PASS"
            else "FAIL"
        ),
        "arithmetic_contract": (
            "f32 reciprocal; f32 multiply; f32 add; ties-away round; u16 clamp; "
            "f32 subtract/max; f32 multiply; f32 divide; outward bounds"
        ),
        "observed_intermediate_u16": [
            int(u_lo[0, 0]),
            int(u_hi[0, 0]),
        ],
        "expected_intermediate_u16": expected_u16,
        "observed_pre_final_interval": [
            float(pre_lo[0, 0]),
            float(pre_hi[0, 0]),
        ],
        "expected_pre_final": float(expected_pre),
        "native_expectations_match": native_exact,
        "green": green_result,
        "red": red_result,
    }
    control_statuses["intermediate_quantizer_green"] = green_result["status"]
    control_statuses["intermediate_quantizer_red"] = red_result["status"]
    evidence_rows.extend(green_rows)
    evidence_rows.extend(red_rows)

    crop = data["crop"]
    full_height = integer(crop["full_height"], "crop.full_height", 1, 1 << 20)
    full_width = integer(crop["full_width"], "crop.full_width", 1, 1 << 20)
    compact_height = integer(
        crop["compact_height"], "crop.compact_height", 1, full_height
    )
    compact_width = integer(
        crop["compact_width"], "crop.compact_width", 1, full_width
    )
    origin_x = integer(crop["origin_x"], "crop.origin_x", 0, full_width - 1)
    origin_y = integer(crop["origin_y"], "crop.origin_y", 0, full_height - 1)
    if (
        origin_x + compact_width > full_width
        or origin_y + compact_height > full_height
        or crop["channels"] != 1
        or crop["transform"] != "integer identity"
    ):
        raise Refusal("crop-origin fixture geometry is invalid")
    normalization = re.fullmatch(
        r"F\(z\)=z/(\d+) before final-u16 serialization",
        str(crop["normalization"]),
    )
    source_formula = re.fullmatch(r"(\d+)\*y\+x", str(crop["source_value"]))
    if normalization is None or source_formula is None:
        raise Refusal("crop-origin fixture formula is unsupported")
    divisor = int(normalization.group(1))
    y_scale = int(source_formula.group(1))
    if divisor <= 0:
        raise Refusal("crop-origin divisor must be positive")
    try:
        source = np.load(
            data["artifacts"]["crop-origin-source.npy"], allow_pickle=False
        )
    except (OSError, ValueError) as error:
        raise Refusal(f"cannot load crop-origin source: {error}") from error
    if source.dtype != np.dtype("<f8") or source.shape != (full_height, full_width):
        raise Refusal(
            f"crop source expected float64 {(full_height, full_width)}, "
            f"got {source.dtype} {source.shape}"
        )
    yy, xx = np.indices((full_height, full_width), dtype=np.float64)
    declared_source = np.asarray(y_scale * yy + xx, dtype=np.float64)
    if not np.array_equal(source, declared_source):
        raise Refusal("crop source array disagrees with its preregistered formula")

    correct_image = load_gray_u16_tiff(
        data["artifacts"]["crop-origin-correct.tiff"],
        compact_height,
        compact_width,
    )
    wrong_image = load_gray_u16_tiff(
        data["artifacts"]["crop-origin-wrong.tiff"],
        compact_height,
        compact_width,
    )
    expected_values = source[
        origin_y : origin_y + compact_height,
        origin_x : origin_x + compact_width,
    ]
    normalized = np.clip(expected_values / float(divisor), 0.0, 1.0)
    expected_codes = np.asarray(
        np.floor(normalized * float(U16_MAX) + 0.5), dtype=np.uint16
    )

    def score_crop(name: str, image: np.ndarray, expected_count: int) -> dict[str, Any]:
        different = image != expected_codes
        count = int(np.count_nonzero(different))
        rows_y, rows_x = np.nonzero(different)
        directions = np.sign(
            image[different].astype(np.int64)
            - expected_codes[different].astype(np.int64)
        ).astype(np.int8)
        for local_y, local_x, direction in zip(rows_y, rows_x, directions):
            evidence_rows.append(
                {
                    "control": name,
                    "x": int(local_x),
                    "y": int(local_y),
                    "full_x": int(local_x + origin_x),
                    "full_y": int(local_y + origin_y),
                    "direction": int(direction),
                    "encoded": int(image[local_y, local_x]),
                    "expected_encoded": int(expected_codes[local_y, local_x]),
                    "q": FINAL_Q,
                }
            )
        expected_directions = {-1} if expected_count else set()
        observed_directions = {int(value) for value in directions}
        passed = (
            count == expected_count and observed_directions == expected_directions
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "full_plane_origin": [origin_x, origin_y],
            "expected_violations": expected_count,
            "observed_violations": count,
            "expected_directions": sorted(expected_directions),
            "observed_directions": sorted(observed_directions),
        }

    correct_result = score_crop("crop_origin_correct", correct_image, 0)
    wrong_expected = integer(
        crop["expected_wrong_origin_violations"],
        "crop.expected_wrong_origin_violations",
        0,
        compact_height * compact_width,
    )
    wrong_result = score_crop("crop_origin_wrong", wrong_image, wrong_expected)
    control_statuses["crop_origin_correct"] = correct_result["status"]
    control_statuses["crop_origin_wrong"] = wrong_result["status"]
    fail_closed_result = score_fail_closed(data)

    green_controls = (
        "convex_bilinear_green",
        "copy_green",
        "unrepresentable_high_at_rail_green",
        "unrepresentable_low_at_rail_green",
        "intermediate_quantizer_green",
        "crop_origin_correct",
    )
    red_controls = (
        "in_range_high_red",
        "in_range_low_red",
        "unrepresentable_high_off_rail_red",
        "unrepresentable_low_off_rail_red",
        "intermediate_quantizer_red",
        "crop_origin_wrong",
    )
    green_passed = sum(control_statuses[name] == "PASS" for name in green_controls)
    red_passed = sum(control_statuses[name] == "PASS" for name in red_controls)
    all_passed = (
        all(value["status"] == "PASS" for value in numeric_results.values())
        and intermediate_result["status"] == "PASS"
        and correct_result["status"] == "PASS"
        and wrong_result["status"] == "PASS"
        and fail_closed_result["status"] == "PASS"
        and green_passed == len(green_controls)
        and red_passed == len(red_controls)
    )
    observed_counts = [
        value["observed_violations"] for value in numeric_results.values()
    ] + [
        green_result["observed_violations"],
        red_result["observed_violations"],
        correct_result["observed_violations"],
        wrong_result["observed_violations"],
    ]
    count_distribution = {
        "zero": observed_counts.count(0),
        "one": observed_counts.count(1),
        "six": observed_counts.count(6),
    }
    expected_count_distribution = {"zero": 6, "one": 5, "six": 1}
    all_passed = all_passed and count_distribution == expected_count_distribution
    report = {
        "schema": COMMISSION_SCHEMA,
        "schema_version": COMMISSION_VERSION,
        "protocol": CHECKER_PROTOCOL,
        "checker_version": CHECKER_VERSION,
        "status": "PASS" if all_passed else "FAIL",
        "preregistration": {
            "path": str(data["preregistration_path"]),
            "sha256": data["preregistration_sha256"],
            "protocol": PROTOCOL,
        },
        "prospective_interpretation": {
            "path": str(data["interpretation_path"]),
            "sha256": data["interpretation_sha256"],
            "canonical_sha256": data[
                "interpretation_canonical_sha256"
            ],
            "commit": INTERPRETATION_COMMIT,
        },
        "fixture": {
            "path": str(data["fixtures"]),
            "manifest": str(data["manifest_path"]),
            "manifest_sha256": data["manifest_sha256"],
            "artifacts_validated": len(data["artifacts"]),
        },
        "checker": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "numeric_representation": NUMERIC_REPRESENTATION,
        "numeric_cases": numeric_results,
        "intermediate_quantizer_case": intermediate_result,
        "crop_origin_case": {
            "correct": correct_result,
            "wrong": wrong_result,
        },
        "m8_r_kernel_cases": fail_closed_result["m8_r_kernel_cases"],
        "fail_closed": fail_closed_result,
        "direction_controls": {
            "green": {
                "expected": len(green_controls),
                "passed": green_passed,
                "controls": list(green_controls),
            },
            "red": {
                "expected": len(red_controls),
                "passed": red_passed,
                "controls": list(red_controls),
            },
        },
        "violation_count_controls": {
            "expected": expected_count_distribution,
            "observed": count_distribution,
            "all_observed": observed_counts,
        },
        "violation_evidence": "violation-evidence.json",
    }
    evidence = {
        "schema": "m136-checker-commissioning-violation-evidence",
        "schema_version": 1,
        "rows": evidence_rows,
        "row_count": len(evidence_rows),
    }
    return report, evidence


def commission(fixtures: Path, output: Path) -> int:
    output = output.resolve()
    staging = fresh_staging(output)
    published = False
    try:
        try:
            data = validate_fixture(fixtures)
            report, evidence = score_commission_fixture(data)
            code = 0 if report["status"] == "PASS" else 1
        except Exception as error:
            report = {
                "schema": COMMISSION_SCHEMA,
                "schema_version": COMMISSION_VERSION,
                "protocol": CHECKER_PROTOCOL,
                "checker_version": CHECKER_VERSION,
                "status": "UNMEASURED",
                "reason": str(error),
                "checker": {
                    "path": str(Path(__file__).resolve()),
                    "sha256": sha256_file(Path(__file__).resolve()),
                },
            }
            evidence = {
                "schema": "m136-checker-commissioning-violation-evidence",
                "schema_version": 1,
                "rows": [],
                "row_count": 0,
                "unmeasured": str(error),
            }
            code = 2
        write_json(staging / "commissioning.json", report)
        write_json(staging / "violation-evidence.json", evidence)
        publish_staging(staging, output)
        published = True
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "output": str(output),
                    "green": report.get("direction_controls", {}).get("green"),
                    "red": report.get("direction_controls", {}).get("red"),
                    "fail_closed": report.get("fail_closed"),
                    "violation_counts": report.get("violation_count_controls"),
                },
                sort_keys=True,
            )
        )
        return code
    finally:
        if not published:
            shutil.rmtree(staging, ignore_errors=True)


def unescape_warp_text(raw: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(raw):
        if raw[index] != "\\":
            output.append(raw[index])
            index += 1
            continue
        index += 1
        if index == len(raw):
            output.append("\\")
            break
        output.append("\n" if raw[index] == "n" else "\r" if raw[index] == "r" else raw[index])
        index += 1
    return "".join(output)


def parse_f64_bits(raw: str, label: str) -> tuple[str, float]:
    if F64_BITS_RE.fullmatch(raw) is None:
        raise Refusal(f"{label}: expected 16 hexadecimal f64 bits")
    bits = raw.lower()
    value = struct.unpack(">d", bytes.fromhex(bits))[0]
    if not math.isfinite(value):
        raise Refusal(f"{label}: non-finite placement value")
    return bits, value


def parse_uint(raw: str, label: str) -> int:
    if UINT_RE.fullmatch(raw) is None:
        raise Refusal(f"{label}: expected an unsigned decimal integer")
    return int(raw)


def parse_warpmap(path: Path) -> WarpMap:
    path = path.resolve()
    try:
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    except (OSError, UnicodeError) as error:
        raise Refusal(f"cannot read warpmap {path}: {error}") from error
    headers: dict[str, str] = {}
    records: dict[int, Placement | None] = {}
    saw_magic = False
    saw_end = False
    end_count: int | None = None
    known_headers = {
        "stack-name",
        "stack-digest",
        "frames",
        "plane",
        "reference",
        "strategy",
        "resampler",
        "heldout-px",
        "cycle-floor-px",
        "note",
    }
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split(maxsplit=1)
        head = fields[0]
        rest = fields[1].strip() if len(fields) == 2 else ""
        label = f"{path}:{line_number}"
        if not saw_magic:
            if head != "strehl-warpmap" or rest != "1":
                raise Refusal(f"{label}: expected first record 'strehl-warpmap 1'")
            saw_magic = True
            continue
        if saw_end:
            raise Refusal(f"{label}: record follows end marker")
        if head == "end":
            end_count = parse_uint(rest, f"{label} end")
            saw_end = True
            continue
        if UINT_RE.fullmatch(head):
            frame_order = int(head)
            if frame_order in records:
                raise Refusal(f"{label}: duplicate frame {frame_order}")
            state_fields = rest.split(maxsplit=1)
            if not state_fields:
                raise Refusal(f"{label}: frame has no state")
            state = state_fields[0]
            tail = state_fields[1] if len(state_fields) == 2 else ""
            if state == "refused":
                records[frame_order] = None
                continue
            if state != "placed":
                raise Refusal(f"{label}: unknown frame state {state!r}")
            bit_fields = tail.split("#", 1)[0].split()
            if len(bit_fields) != 4:
                raise Refusal(f"{label}: placed frame needs four f64 fields")
            decoded = [
                parse_f64_bits(value, f"{label} placement") for value in bit_fields
            ]
            records[frame_order] = Placement(
                frame_order=frame_order,
                bits=tuple(item[0] for item in decoded),  # type: ignore[arg-type]
                a_re=decoded[0][1],
                a_im=decoded[1][1],
                b_re=decoded[2][1],
                b_im=decoded[3][1],
            )
            continue
        if head not in known_headers:
            raise Refusal(f"{label}: unknown warpmap header {head!r}")
        if not rest or head in headers:
            raise Refusal(f"{label}: empty or duplicate header {head!r}")
        headers[head] = rest
    if not saw_magic or not saw_end or end_count is None:
        raise Refusal(f"{path}: incomplete warpmap framing")
    required = (
        "stack-name",
        "stack-digest",
        "frames",
        "plane",
        "reference",
        "strategy",
        "resampler",
    )
    missing = [name for name in required if name not in headers]
    if missing:
        raise Refusal(f"{path}: missing warpmap headers {missing}")
    frame_count = parse_uint(headers["frames"], f"{path} frames")
    reference = parse_uint(headers["reference"], f"{path} reference")
    plane_match = PLANE_RE.fullmatch(headers["plane"])
    if plane_match is None:
        raise Refusal(f"{path}: malformed plane header")
    width, height = (int(value) for value in plane_match.groups())
    if min(width, height) <= 0:
        raise Refusal(f"{path}: zero plane dimension")
    stack_digest = headers["stack-digest"].lower()
    if U64_BITS_RE.fullmatch(stack_digest) is None:
        raise Refusal(f"{path}: invalid stack digest")
    expected_indices = set(range(frame_count))
    if (
        end_count != frame_count
        or set(records) != expected_indices
        or not 0 <= reference < frame_count
    ):
        raise Refusal(f"{path}: inconsistent frame records/reference/end marker")
    if not any(record is not None for record in records.values()):
        raise Refusal(f"{path}: no placed frames")
    return WarpMap(
        path=path,
        sha256=sha256_file(path),
        stack_name=unescape_warp_text(headers["stack-name"]),
        stack_digest=stack_digest,
        frame_count=frame_count,
        width=width,
        height=height,
        reference=reference,
        resampler=headers["resampler"],
        placements=records,
    )


def stack_digest(entries: Sequence[tuple[str, int]]) -> str:
    digest = FNV1A64_OFFSET
    for name, size in entries:
        try:
            encoded_name = name.encode("utf-8")
        except UnicodeEncodeError as error:
            raise Refusal(f"source filename is not UTF-8 encodable: {name!r}") from error
        payload = encoded_name + b"\0" + int(size).to_bytes(8, "little") + b"\0"
        for byte in payload:
            digest = ((digest ^ byte) * FNV1A64_PRIME) & U64_MASK
    return f"{digest:016x}"


def source_inventory(input_dir: Path, warpmap: WarpMap) -> tuple[Path, ...]:
    input_dir = input_dir.resolve()
    if not input_dir.is_dir():
        raise Refusal(f"input directory is absent: {input_dir}")
    if input_dir.name != warpmap.stack_name:
        raise Refusal(
            f"source directory name {input_dir.name!r} != "
            f"warpmap stack-name {warpmap.stack_name!r}"
        )
    paths: list[Path] = []
    try:
        for child in input_dir.iterdir():
            suffix = "".join(
                chr(ord(char) + 32) if "A" <= char <= "Z" else char
                for char in child.suffix
            )
            if suffix != ".arw":
                continue
            if child.is_symlink() or not child.is_file():
                raise Refusal(f"source entry is not a regular file: {child}")
            paths.append(child.resolve())
    except OSError as error:
        raise Refusal(f"cannot enumerate source directory {input_dir}: {error}") from error
    paths.sort(key=lambda item: item.name)
    if len(paths) != warpmap.frame_count:
        raise Refusal(
            f"source inventory has {len(paths)} .ARW files, "
            f"warpmap declares {warpmap.frame_count}"
        )
    entries = [(path.name, path.stat().st_size) for path in paths]
    observed_digest = stack_digest(entries)
    if observed_digest != warpmap.stack_digest:
        raise Refusal(
            f"source stack digest {observed_digest} != warpmap {warpmap.stack_digest}"
        )
    return tuple(paths)


def mapped_corners(
    placement: Placement, width: int, height: int, scale: float
) -> Iterable[tuple[float, float]]:
    cx, cy = width * 0.5, height * 0.5
    # Reproduce `Similarity::scale(scale).then(placement)` in the producer,
    # including its floating-point operation order.  Algebraically moving
    # `scale` onto each corner offset is equivalent over the reals but differs
    # by one binary64 ulp for the registered flat-et6s map.
    composed_a_re = scale * placement.a_re - 0.0 * placement.a_im
    composed_a_im = scale * placement.a_im + 0.0 * placement.a_re
    for x, y in (
        (0.0, 0.0),
        (width - 1.0, 0.0),
        (0.0, height - 1.0),
        (width - 1.0, height - 1.0),
    ):
        dx = x - cx
        dy = y - cy
        yield (
            composed_a_re * dx - composed_a_im * dy + placement.b_re + cx,
            composed_a_re * dy + composed_a_im * dx + placement.b_im + cy,
        )


def reconstruct_crop(warpmap: WarpMap) -> tuple[int, int, int, int, float]:
    placed = tuple(
        placement
        for placement in warpmap.placements.values()
        if placement is not None
    )

    def covered(scale: float) -> bool:
        for placement in placed:
            for x, y in mapped_corners(
                placement, warpmap.width, warpmap.height, scale
            ):
                if not (
                    x >= COVER_MARGIN
                    and y >= COVER_MARGIN
                    and x <= warpmap.width - 1.0 - COVER_MARGIN
                    and y <= warpmap.height - 1.0 - COVER_MARGIN
                ):
                    return False
        return True

    if covered(1.0):
        scale = 1.0
    else:
        low, high = 0.0, 1.0
        for _ in range(60):
            middle = 0.5 * (low + high)
            if covered(middle):
                low = middle
            else:
                high = middle
        if low <= 0.0:
            raise Refusal("no positive 3-pixel-margin cover scale")
        scale = low

    def axis(size: int) -> tuple[int, int]:
        lower = 0.5 * size * (1.0 - scale)
        upper = lower + scale * (size - 1.0)
        first = max(0, math.ceil(lower))
        last = max(first, min(size - 1, math.floor(upper)))
        return first, last - first + 1

    crop_x, compact_width = axis(warpmap.width)
    crop_y, compact_height = axis(warpmap.height)
    return crop_x, crop_y, compact_width, compact_height, scale


def parse_trace(
    path: Path,
    source_hash_cache: dict[Path, str],
    expected_instrument_freeze_sha256: str | None = None,
) -> TraceBlock:
    path = path.resolve()
    match = TRACE_NAME.fullmatch(path.name)
    if match is None:
        raise Refusal(f"trace block has invalid filename: {path.name}")
    file_hash = sha256_file(path)
    if file_hash.lower() != match.group("content_hash"):
        raise Refusal(f"{path.name}: content-addressed filename hash mismatch")
    try:
        size = path.stat().st_size
        with path.open("rb") as stream:
            raw_header = stream.read(TRACE_HEADER.size)
            if len(raw_header) != TRACE_HEADER.size:
                raise Refusal(f"{path.name}: truncated trace-v3 header")
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
            ) = TRACE_HEADER.unpack(raw_header)
            if magic != TRACE_MAGIC or version != TRACE_VERSION:
                raise Refusal(
                    f"{path.name}: requires {TRACE_MAGIC!r} version {TRACE_VERSION}"
                )
            if path_bytes <= 0 or path_bytes > MAX_PATH_BYTES:
                raise Refusal(f"{path.name}: invalid frame path length {path_bytes}")
            encoded_path = stream.read(path_bytes)
            if len(encoded_path) != path_bytes:
                raise Refusal(f"{path.name}: truncated frame path")
    except Refusal:
        raise
    except OSError as error:
        raise Refusal(f"cannot read trace {path}: {error}") from error
    try:
        frame_path = Path(encoded_path.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise Refusal(f"{path.name}: frame path is not UTF-8") from error
    if not frame_path.is_absolute() or not frame_path.is_file():
        raise Refusal(f"{path.name}: source frame is absent/not absolute: {frame_path}")
    frame_path = frame_path.resolve()
    source_offset = TRACE_HEADER.size + path_bytes
    source_bytes = source_width * source_height * 4
    gathered_offset = source_offset + source_bytes
    expected_size = gathered_offset + full_width * full_height * 4
    if size != expected_size:
        raise Refusal(
            f"{path.name}: size {size} != header-implied {expected_size}"
        )
    if (
        kernel != TARGET_KERNEL
        or arithmetic_contract != ARITHMETIC_CONTRACT
        or min(
            source_width,
            source_height,
            full_width,
            full_height,
            compact_width,
            compact_height,
        )
        <= 0
    ):
        raise Refusal(f"{path.name}: kernel, contract, or dimensions are invalid")
    if source_width != 2 * full_width or source_height != 2 * full_height:
        raise Refusal(f"{path.name}: source plane is not 2x the full output plane")
    if crop_x + compact_width > full_width or crop_y + compact_height > full_height:
        raise Refusal(f"{path.name}: compact crop exceeds full plane")
    if SITE_CHANNEL.get((site_x, site_y)) != channel:
        raise Refusal(f"{path.name}: invalid CFA site/channel pair")
    if frame_order != int(match.group("frame")):
        raise Refusal(f"{path.name}: frame order disagrees with filename")
    if (site_x, site_y) != (
        int(match.group("sx")),
        int(match.group("sy")),
    ):
        raise Refusal(f"{path.name}: CFA site disagrees with filename")
    if sha256_bytes(encoded_path).lower() != match.group("path_hash"):
        raise Refusal(f"{path.name}: frame path hash disagrees with filename")
    scalar_values = (
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
    if not all(math.isfinite(float(value)) for value in scalar_values):
        raise Refusal(f"{path.name}: non-finite geometry/representation scalar")
    if sensor_range <= 0 or site_gain <= 0 or output_gain <= 0 or black_level < 0:
        raise Refusal(f"{path.name}: invalid native representation scalar")
    source_hash = source_hash_cache.get(frame_path)
    if source_hash is None:
        source_hash = sha256_file(frame_path)
        source_hash_cache[frame_path] = source_hash
    if source_hash != source_sha.hex().upper():
        raise Refusal(f"{path.name}: source file SHA-256 mismatch")
    instrument_freeze_sha256 = instrument_freeze_sha.hex().upper()
    if (
        expected_instrument_freeze_sha256 is not None
        and instrument_freeze_sha256 != expected_instrument_freeze_sha256
    ):
        raise Refusal(
            f"{path.name}: instrument-freeze SHA-256 "
            f"{instrument_freeze_sha256} != "
            f"{expected_instrument_freeze_sha256}"
        )
    return TraceBlock(
        path=path,
        file_sha256=file_hash,
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
        instrument_freeze_sha256=instrument_freeze_sha256,
        frame_source_sha256=source_sha.hex().upper(),
        frame_path=frame_path,
        source_offset=source_offset,
        gathered_offset=gathered_offset,
    )


def trace_blocks(
    trace_state: Path,
    warpmap: WarpMap,
    inventory: Sequence[Path],
    expected_instrument_freeze_sha256: str | None = None,
) -> tuple[list[TraceBlock], dict[int, dict[tuple[int, int], TraceBlock]], dict[Path, str]]:
    trace_state = trace_state.resolve()
    if not trace_state.is_dir():
        raise Refusal(f"trace state directory is absent: {trace_state}")
    for name in ("claims", "staging"):
        directory = trace_state / name
        if directory.exists() and any(directory.iterdir()):
            raise Refusal(f"unresolved trace {name} leftovers exist in {directory}")
    block_dir = trace_state / "blocks"
    if not block_dir.is_dir():
        raise Refusal(f"trace blocks directory is absent: {block_dir}")
    entries = list(block_dir.iterdir())
    unexpected = [
        path.name
        for path in entries
        if path.is_symlink()
        or not path.is_file()
        or TRACE_NAME.fullmatch(path.name) is None
    ]
    if unexpected:
        raise Refusal(f"unexpected entries in trace blocks: {unexpected[:8]}")
    paths = sorted(path.resolve() for path in entries)
    if not paths:
        raise Refusal(f"no trace-v3 blocks in {block_dir}")
    source_hash_cache: dict[Path, str] = {}
    blocks = [
        parse_trace(
            path,
            source_hash_cache,
            expected_instrument_freeze_sha256,
        )
        for path in paths
    ]
    grouped: dict[int, dict[tuple[int, int], TraceBlock]] = {}
    for block in blocks:
        key = (block.frame_order, block.site)
        sites = grouped.setdefault(block.frame_order, {})
        if block.site in sites:
            raise Refusal(f"duplicate frame/site trace: {key}")
        sites[block.site] = block
    expected_frames = {
        frame_order
        for frame_order, placement in warpmap.placements.items()
        if placement is not None
    }
    expected_keys = {
        (frame_order, site)
        for frame_order in expected_frames
        for site in SITE_NAMES
    }
    actual_keys = {
        (frame_order, site)
        for frame_order, sites in grouped.items()
        for site in sites
    }
    if actual_keys != expected_keys:
        raise Refusal(
            "incomplete trace set: "
            f"missing={sorted(expected_keys - actual_keys)[:8]}, "
            f"extra={sorted(actual_keys - expected_keys)[:8]}"
        )
    first = blocks[0]
    geometry = (
        first.source_width,
        first.source_height,
        first.full_width,
        first.full_height,
        first.compact_width,
        first.compact_height,
        first.crop_x,
        first.crop_y,
    )
    for frame_order in sorted(grouped):
        placement = warpmap.placements[frame_order]
        assert placement is not None
        expected_source = inventory[frame_order]
        sites = grouped[frame_order]
        baseline = sites[(0, 0)]
        for site, block in sites.items():
            block_geometry = (
                block.source_width,
                block.source_height,
                block.full_width,
                block.full_height,
                block.compact_width,
                block.compact_height,
                block.crop_x,
                block.crop_y,
            )
            if block_geometry != geometry:
                raise Refusal(f"frame {frame_order} site {site}: geometry mismatch")
            if block.frame_path != expected_source:
                raise Refusal(
                    f"frame {frame_order}: trace source {block.frame_path} "
                    f"!= ordered input {expected_source}"
                )
            if not all(
                (
                    same_f64(block.a_re, placement.a_re),
                    same_f64(block.a_im, placement.a_im),
                    same_f64(block.b_re, placement.b_re),
                    same_f64(block.b_im, placement.b_im),
                    same_f64(block.cx, 0.5 * block.full_width),
                    same_f64(block.cy, 0.5 * block.full_height),
                )
            ):
                raise Refusal(
                    f"frame {frame_order} site {site}: trace/warp geometry mismatch"
                )
            if not (
                same_f32(block.black_level, baseline.black_level)
                and same_f32(block.sensor_range, baseline.sensor_range)
            ):
                raise Refusal(f"frame {frame_order}: site native scalars disagree")
        g1, g2 = sites[GREEN_SITES[0]], sites[GREEN_SITES[1]]
        if not (
            same_f32(g1.black_level, g2.black_level)
            and same_f32(g1.sensor_range, g2.sensor_range)
            and same_f32(g1.site_gain, g2.site_gain)
            and same_f32(g1.output_gain, g2.output_gain)
        ):
            raise Refusal(f"frame {frame_order}: paired green scalars disagree")
    output_gains: dict[int, np.float32] = {}
    for block in blocks:
        prior = output_gains.get(block.channel)
        if prior is None:
            output_gains[block.channel] = block.output_gain
        elif not same_f32(prior, block.output_gain):
            raise Refusal(
                f"channel {CHANNEL_NAMES[block.channel]}: "
                "final output gain changes across frames"
            )
    return blocks, grouped, source_hash_cache


def row_coordinates(
    block: TraceBlock,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
) -> tuple[np.ndarray, np.ndarray]:
    x = (
        np.arange(x0, x1, dtype=np.float64)[None, :]
        + 0.5 * block.site_x
    )
    y = (
        np.arange(y0, y1, dtype=np.float64)[:, None]
        + 0.5 * block.site_y
    )
    xr = x - block.cx
    yr = y - block.cy
    source_x = 2.0 * (
        block.a_re * xr - block.a_im * yr + block.b_re + block.cx
    )
    source_y = 2.0 * (
        block.a_re * yr + block.a_im * xr + block.b_im + block.cy
    )
    return source_x, source_y


def exact_support(
    source: np.ndarray,
    block: TraceBlock,
    source_x: np.ndarray,
    source_y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    valid = (
        (source_x >= 1.5)
        & (source_y >= 1.5)
        & (source_x <= block.source_width - 2.5)
        & (source_y <= block.source_height - 2.5)
    )
    clamped_x = np.clip(source_x, 1, block.source_width - 3)
    clamped_y = np.clip(source_y, 1, block.source_height - 3)
    ix = np.floor(clamped_x).astype(np.intp)
    iy = np.floor(clamped_y).astype(np.intp)
    lower = np.full(source_x.shape, np.float32(np.inf), dtype=np.float32)
    upper = np.full(source_x.shape, np.float32(-np.inf), dtype=np.float32)
    for dy in (-1, 0, 1, 2):
        for dx in (-1, 0, 1, 2):
            values = np.asarray(source[iy + dy, ix + dx], dtype=np.float32)
            np.minimum(lower, values, out=lower)
            np.maximum(upper, values, out=upper)
    return valid, lower, upper


def tau_r(lower: np.ndarray, upper: np.ndarray) -> np.ndarray:
    magnitude = np.maximum(
        np.float32(1.0),
        np.maximum(
            np.abs(np.asarray(lower, dtype=np.float32)),
            np.abs(np.asarray(upper, dtype=np.float32)),
        ),
    )
    magnitude = np.asarray(magnitude, dtype=np.float32)
    following = np.nextafter(
        magnitude, np.float32(np.inf), dtype=np.float32
    )
    ulp = np.subtract(following, magnitude, dtype=np.float32)
    return np.multiply(np.float32(8.0), ulp, dtype=np.float32)


def m8r_violation_rows(
    block: TraceBlock,
    y0: int,
    values: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    tau: np.ndarray,
    low_mask: np.ndarray,
    high_mask: np.ndarray,
) -> np.ndarray:
    mask = low_mask | high_mask
    yy, xx = np.nonzero(mask)
    rows = np.empty(len(xx), dtype=M8R_VIOLATION_DTYPE)
    rows["frame_order"] = block.frame_order
    rows["site_x"] = block.site_x
    rows["site_y"] = block.site_y
    rows["x"] = xx
    rows["y"] = yy + y0
    rows["direction"] = np.where(high_mask[mask], 1, -1)
    rows["value"] = values[mask]
    rows["lo"] = lower[mask]
    rows["hi"] = upper[mask]
    rows["tau"] = tau[mask]
    rows["signed_excess"] = np.where(
        high_mask[mask],
        values[mask] - upper[mask],
        values[mask] - lower[mask],
    )
    return rows


def verify_m8r_block(
    block: TraceBlock,
    chunk_rows: int,
    block_sink: RowSink,
    aggregate_sink: RowSink,
) -> dict[str, Any]:
    source = block.source()
    gathered = block.gathered()
    for source_y0 in range(0, block.source_height, chunk_rows):
        source_y1 = min(block.source_height, source_y0 + chunk_rows)
        if not np.all(np.isfinite(source[source_y0:source_y1])):
            yy, xx = np.argwhere(~np.isfinite(source[source_y0:source_y1]))[0]
            raise Refusal(
                f"{block.path.name}: non-finite source at "
                f"({int(xx)},{int(yy + source_y0)})"
            )
    denominator = lower_count = upper_count = 0
    max_excess = 0.0
    for y0 in range(0, block.full_height, chunk_rows):
        y1 = min(block.full_height, y0 + chunk_rows)
        source_x, source_y = row_coordinates(
            block, y0, y1, 0, block.full_width
        )
        valid, lower, upper = exact_support(source, block, source_x, source_y)
        values = np.asarray(gathered[y0:y1], dtype=np.float32)
        if np.any(np.isinf(values)):
            yy, xx = np.argwhere(np.isinf(values))[0]
            raise Refusal(
                f"{block.path.name}: infinite gathered value at "
                f"({int(xx)},{int(yy + y0)})"
            )
        if np.any(np.isfinite(values) ^ valid):
            yy, xx = np.argwhere(np.isfinite(values) ^ valid)[0]
            raise Refusal(
                f"{block.path.name}: gathered coverage mismatch at "
                f"({int(xx)},{int(yy + y0)})"
            )
        tau = tau_r(lower, upper)
        lower_limit = np.subtract(lower, tau, dtype=np.float32)
        upper_limit = np.add(upper, tau, dtype=np.float32)
        low_mask = valid & (values < lower_limit)
        high_mask = valid & (values > upper_limit)
        denominator += int(np.count_nonzero(valid))
        lower_count += int(np.count_nonzero(low_mask))
        upper_count += int(np.count_nonzero(high_mask))
        if np.any(low_mask | high_mask):
            rows = m8r_violation_rows(
                block,
                y0,
                values,
                lower,
                upper,
                tau,
                low_mask,
                high_mask,
            )
            block_sink.append(rows)
            aggregate_sink.append(rows)
            excess = np.where(
                rows["direction"] > 0,
                rows["signed_excess"] - rows["tau"],
                -rows["signed_excess"] - rows["tau"],
            )
            max_excess = max(max_excess, float(np.max(excess, initial=0.0)))
    del source, gathered
    return {
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
    }


def compact_native_interval(
    block: TraceBlock,
    y0: int,
    y1: int,
    crop_x: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    source = block.source()
    source_x, source_y = row_coordinates(
        block,
        block.crop_y + y0,
        block.crop_y + y1,
        crop_x,
        crop_x + block.compact_width,
    )
    valid, lower, upper = exact_support(source, block, source_x, source_y)
    tau = tau_r(lower, upper)
    interval_lo, interval_hi = source_interval(lower, upper, tau)
    black_lo, black_hi, _, _ = intermediate_interval(
        interval_lo, interval_hi, block.site_gain, block.black_level
    )
    del source
    return valid, black_lo, black_hi


def create_array(
    path: Path, dtype: str, shape: tuple[int, ...], fill: float | int
) -> np.memmap:
    array = np.lib.format.open_memmap(path, mode="w+", dtype=dtype, shape=shape)
    array[:] = fill
    array.flush()
    return array


def close_memmap(array: np.ndarray | None) -> None:
    if array is None:
        return
    if hasattr(array, "flush"):
        array.flush()
    mapping_handle = getattr(array, "_mmap", None)
    if mapping_handle is not None:
        mapping_handle.close()


def update_aggregate(
    lower_map: np.ndarray,
    upper_map: np.ndarray,
    channel: int,
    y0: int,
    valid: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    frame_order: int,
    contributors: np.ndarray | None = None,
    lower_frames: np.ndarray | None = None,
    upper_frames: np.ndarray | None = None,
) -> None:
    lower_view = lower_map[channel, y0 : y0 + valid.shape[0]]
    upper_view = upper_map[channel, y0 : y0 + valid.shape[0]]
    replace_lower = valid & (lower < lower_view)
    replace_upper = valid & (upper > upper_view)
    if lower_frames is not None:
        lower_witness = lower_frames[channel, y0 : y0 + valid.shape[0]]
        replace_lower |= valid & (lower == lower_view) & (frame_order < lower_witness)
        lower_witness[replace_lower] = frame_order
    if upper_frames is not None:
        upper_witness = upper_frames[channel, y0 : y0 + valid.shape[0]]
        replace_upper |= valid & (upper == upper_view) & (frame_order < upper_witness)
        upper_witness[replace_upper] = frame_order
    lower_view[replace_lower] = lower[replace_lower]
    upper_view[replace_upper] = upper[replace_upper]
    if contributors is not None:
        count_view = contributors[channel, y0 : y0 + valid.shape[0]]
        count_view[valid] += np.uint16(1)


def load_rgb16_tiff(
    path: Path,
    height: int,
    width: int,
    instrument_freeze_sha256: str,
) -> tuple[np.ndarray, str]:
    path = path.resolve()
    try:
        with tifffile.TiffFile(path) as tiff:
            if len(tiff.series) != 1 or len(tiff.pages) != 1:
                raise Refusal(f"{path}: expected one TIFF image and page")
            series = tiff.series[0]
            expected_shape = (height, width, 3)
            if (
                series.shape != expected_shape
                or series.dtype != np.dtype(np.uint16)
            ):
                raise Refusal(
                    f"{path}: expected RGB16 {expected_shape}, "
                    f"got {series.dtype} {series.shape}"
                )
            page = tiff.pages[0]
            if int(page.samplesperpixel) != 3 or int(page.photometric) != 2:
                raise Refusal(f"{path}: TIFF is not three-sample RGB")
            description = page.description or ""
            if "This is the measurement output." not in description:
                raise Refusal(
                    f"{path}: TIFF is not the linear camera-native measurement output"
                )
            freeze_marker = (
                "M136 instrument freeze sha256: "
                f"{instrument_freeze_sha256}."
            )
            if description.count(freeze_marker) != 1:
                raise Refusal(
                    f"{path}: TIFF is not bound to the frozen M136 instrument"
                )
            image = np.asarray(series.asarray(), dtype=np.uint16)
    except Refusal:
        raise
    except (OSError, ValueError, tifffile.TiffFileError) as error:
        raise Refusal(f"cannot read TIFF {path}: {error}") from error
    return image, sha256_file(path)


def build_m8o_rows(
    capture: str,
    image: np.ndarray,
    projected_lower: np.ndarray,
    projected_upper: np.ndarray,
    lower_frames: np.ndarray,
    upper_frames: np.ndarray,
    chunk_rows: int,
    sink: RowSink,
) -> dict[str, Any]:
    height, width, _ = image.shape
    lower_count = upper_count = 0
    max_excess = 0.0
    max_positive_signed = 0.0
    min_negative_signed = 0.0
    channel_counts = {
        name: {"lower_count": 0, "upper_count": 0, "violation_count": 0}
        for name in CHANNEL_NAMES
    }
    for y0 in range(0, height, chunk_rows):
        y1 = min(height, y0 + chunk_rows)
        encoded = np.moveaxis(image[y0:y1], -1, 0)
        values = encoded.astype(np.float64) / float(U16_MAX)
        lower = np.asarray(projected_lower[:, y0:y1], dtype=np.float32)
        upper = np.asarray(projected_upper[:, y0:y1], dtype=np.float32)
        low_mask = values < lower.astype(np.float64) - FINAL_Q
        high_mask = values > upper.astype(np.float64) + FINAL_Q
        lower_count += int(np.count_nonzero(low_mask))
        upper_count += int(np.count_nonzero(high_mask))
        mask = low_mask | high_mask
        if not np.any(mask):
            continue
        channel, yy, xx = np.nonzero(mask)
        rows = np.empty(len(xx), dtype=M8O_VIOLATION_DTYPE)
        directions = np.where(high_mask[mask], 1, -1)
        rows["capture"] = capture
        rows["x"] = xx
        rows["y"] = yy + y0
        rows["channel"] = np.asarray(CHANNEL_NAMES)[channel]
        rows["direction"] = directions
        rows["encoded"] = encoded[mask]
        rows["L"] = lower[mask]
        rows["H"] = upper[mask]
        rows["q"] = FINAL_Q
        rows["signed_excess"] = np.where(
            directions > 0,
            values[mask] - upper[mask].astype(np.float64),
            values[mask] - lower[mask].astype(np.float64),
        )
        selected_lower_frames = np.asarray(lower_frames[:, y0:y1])[mask]
        selected_upper_frames = np.asarray(upper_frames[:, y0:y1])[mask]
        rows["lower_frame_order"] = selected_lower_frames
        rows["upper_frame_order"] = selected_upper_frames
        rows["extremising_frame_order"] = np.where(
            directions > 0, selected_upper_frames, selected_lower_frames
        )
        sink.append(rows)
        for channel_index, channel_name in enumerate(CHANNEL_NAMES):
            channel_lower = int(np.count_nonzero(low_mask[channel_index]))
            channel_upper = int(np.count_nonzero(high_mask[channel_index]))
            channel_counts[channel_name]["lower_count"] += channel_lower
            channel_counts[channel_name]["upper_count"] += channel_upper
            channel_counts[channel_name]["violation_count"] += (
                channel_lower + channel_upper
            )
        if np.any(directions > 0):
            max_positive_signed = max(
                max_positive_signed,
                float(np.max(rows["signed_excess"][directions > 0], initial=0.0)),
            )
        if np.any(directions < 0):
            min_negative_signed = min(
                min_negative_signed,
                float(np.min(rows["signed_excess"][directions < 0], initial=0.0)),
            )
        excess = np.where(
            directions > 0,
            rows["signed_excess"] - FINAL_Q,
            -rows["signed_excess"] - FINAL_Q,
        )
        max_excess = max(max_excess, float(np.max(excess, initial=0.0)))
    violations = lower_count + upper_count
    denominator = height * width * 3
    maximum_absolute_signed = max(
        max_positive_signed, abs(min_negative_signed)
    )
    return {
        "denominator": denominator,
        "lower_violations": lower_count,
        "upper_violations": upper_count,
        "violations": violations,
        "fraction_exact": f"{violations}/{denominator}",
        "fraction": violations / float(denominator),
        "percent": 100.0 * violations / float(denominator),
        "maximum_positive_signed_excess_linear": max_positive_signed,
        "minimum_negative_signed_excess_linear": min_negative_signed,
        "maximum_absolute_signed_excess_linear": maximum_absolute_signed,
        "maximum_absolute_signed_excess_u16_lsb": (
            maximum_absolute_signed * float(U16_MAX)
        ),
        "max_excess_over_tolerance": max_excess,
        "per_channel": channel_counts,
        "q": FINAL_Q,
    }


def rail_disclosure(
    image: np.ndarray,
    pre_lower: np.ndarray,
    pre_upper: np.ndarray,
    projected_lower: np.ndarray,
    projected_upper: np.ndarray,
    chunk_rows: int,
) -> dict[str, Any]:
    counts = {
        "high_coordinates": 0,
        "high_full": 0,
        "high_off": 0,
        "low_coordinates": 0,
        "low_zero": 0,
        "low_off": 0,
        "violation_coordinates": 0,
        "violation_full": 0,
        "violation_zero": 0,
        "violation_off": 0,
    }
    height = image.shape[0]
    for y0 in range(0, height, chunk_rows):
        y1 = min(height, y0 + chunk_rows)
        encoded = np.moveaxis(image[y0:y1], -1, 0)
        values = encoded.astype(np.float64) / float(U16_MAX)
        lower_violation = (
            values
            < np.asarray(projected_lower[:, y0:y1], dtype=np.float64) - FINAL_Q
        )
        upper_violation = (
            values
            > np.asarray(projected_upper[:, y0:y1], dtype=np.float64) + FINAL_Q
        )
        high_beyond = (
            np.asarray(pre_lower[:, y0:y1], dtype=np.float64) - FINAL_Q > 1.0
        )
        low_beyond = (
            np.asarray(pre_upper[:, y0:y1], dtype=np.float64) + FINAL_Q < 0.0
        )
        full = encoded == U16_MAX
        zero = encoded == 0
        violation = lower_violation | upper_violation
        counts["high_coordinates"] += int(np.count_nonzero(high_beyond))
        counts["high_full"] += int(np.count_nonzero(high_beyond & full))
        counts["high_off"] += int(np.count_nonzero(high_beyond & ~full))
        counts["low_coordinates"] += int(np.count_nonzero(low_beyond))
        counts["low_zero"] += int(np.count_nonzero(low_beyond & zero))
        counts["low_off"] += int(np.count_nonzero(low_beyond & ~zero))
        counts["violation_coordinates"] += int(np.count_nonzero(violation))
        counts["violation_full"] += int(np.count_nonzero(violation & full))
        counts["violation_zero"] += int(np.count_nonzero(violation & zero))
        counts["violation_off"] += int(
            np.count_nonzero(violation & ~full & ~zero)
        )
    denominator = int(image.shape[0] * image.shape[1] * image.shape[2])
    count_result = {
        "source_interval_wholly_above_representable": {
            "coordinates": counts["high_coordinates"],
            "full_rail": counts["high_full"],
            "off_rail": counts["high_off"],
        },
        "source_interval_wholly_below_representable": {
            "coordinates": counts["low_coordinates"],
            "zero_rail": counts["low_zero"],
            "off_rail": counts["low_off"],
        },
        "projected_violations": {
            "coordinates": counts["violation_coordinates"],
            "at_full_rail": counts["violation_full"],
            "at_zero_rail": counts["violation_zero"],
            "off_rail": counts["violation_off"],
        },
    }
    return {
        "denominator": denominator,
        "counts": count_result,
        "fractions_over_denominator": {
            category: {
                name: count / float(denominator)
                for name, count in values.items()
            }
            for category, values in count_result.items()
        },
    }


def validate_commission_report(path: Path, prereg_hash: str) -> dict[str, Any]:
    path = path.resolve()
    report = mapping(read_json(path, "checker commissioning report"), "commission report")
    if (
        report.get("schema") != COMMISSION_SCHEMA
        or report.get("schema_version") != COMMISSION_VERSION
        or report.get("status") != "PASS"
    ):
        raise Refusal("checker commissioning report is not a versioned PASS")
    if report.get("preregistration", {}).get("sha256") != prereg_hash:
        raise Refusal("checker commissioning used another preregistration")
    interpretation_path = INTERPRETATION_PATH
    interpretation = mapping(
        report.get("prospective_interpretation"),
        "commission report prospective interpretation",
    )
    if (
        Path(str(interpretation.get("path", ""))).resolve()
        != interpretation_path
        or interpretation.get("sha256") != sha256_file(interpretation_path)
        or interpretation.get("canonical_sha256")
        != INTERPRETATION_CANONICAL_SHA256
        or interpretation.get("commit") != INTERPRETATION_COMMIT
        or sha256_canonical_text(interpretation_path)
        != INTERPRETATION_CANONICAL_SHA256
    ):
        raise Refusal(
            "checker commissioning used another prospective interpretation"
        )
    checker = mapping(report.get("checker"), "commission report checker")
    if checker.get("sha256") != sha256_file(Path(__file__).resolve()):
        raise Refusal("checker commissioning was produced by different checker bytes")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "fixture_manifest_sha256": report.get("fixture", {}).get("manifest_sha256"),
        "interpretation_sha256": interpretation["sha256"],
        "interpretation_canonical_sha256": INTERPRETATION_CANONICAL_SHA256,
        "interpretation_commit": INTERPRETATION_COMMIT,
    }


def artifact_metadata(root: Path, path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if path.suffix == ".npy":
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        result["shape"] = list(array.shape)
        result["dtype"] = array.dtype.descr if array.dtype.names else array.dtype.str
        del array
    return result


def adjudicate(
    *,
    capture: str,
    input_dir: Path,
    trace_state: Path,
    warpmap_path: Path,
    tiff_path: Path,
    output: Path,
    preregistration_path: Path,
    commissioning_report: Path,
    source_commit: str,
    candidate_binary: Path,
    instrument_freeze: Path,
    green_rule: str,
    chunk_rows: int,
) -> int:
    if not capture or len(capture) > 64:
        raise Refusal("capture must contain 1..64 characters")
    if green_rule != GREEN_RULE:
        raise Refusal(f"--green-rule must be explicitly {GREEN_RULE!r}")
    if chunk_rows <= 0 or chunk_rows > 1024:
        raise Refusal("--chunk-rows must be in [1, 1024]")
    if re.fullmatch(r"[0-9a-fA-F]{40}", source_commit) is None:
        raise Refusal("--source-commit must be a full 40-digit commit")
    candidate_binary = candidate_binary.resolve()
    if not candidate_binary.is_file():
        raise Refusal(f"candidate binary is absent: {candidate_binary}")

    prereg = validate_preregistration(preregistration_path)
    prereg_hash = sha256_file(preregistration_path.resolve())
    commission_evidence = validate_commission_report(
        commissioning_report, prereg_hash
    )
    instrument_freeze_path, instrument_freeze_sha256 = (
        validate_instrument_freeze(
            instrument_freeze,
            source_commit=source_commit,
            candidate_binary=candidate_binary,
            preregistration=preregistration_path.resolve(),
            commissioning_report=commissioning_report.resolve(),
        )
    )
    registered_captures = {
        str(item["name"]): item
        for item in prereg.get("scope", {}).get("captures", [])
        if isinstance(item, Mapping) and "name" in item
    }
    if capture not in registered_captures:
        raise Refusal(f"capture {capture!r} is not preregistered")
    registered = registered_captures[capture]
    input_dir = input_dir.resolve()
    if os.path.normcase(str(input_dir)) != os.path.normcase(
        str(Path(str(registered["input"])).resolve())
    ):
        raise Refusal(f"{capture}: input path differs from preregistration")
    warpmap = parse_warpmap(warpmap_path)
    if warpmap.sha256 != digest_text(
        registered["map_sha256"], f"{capture} preregistered warpmap hash"
    ):
        raise Refusal(f"{capture}: warpmap hash differs from preregistration")
    if warpmap.resampler != "clamped-catmull":
        raise Refusal(
            f"{capture}: target warpmap resampler is {warpmap.resampler!r}, "
            "expected 'clamped-catmull'"
        )
    inventory = source_inventory(input_dir, warpmap)
    blocks, grouped, source_hashes = trace_blocks(
        trace_state,
        warpmap,
        inventory,
        instrument_freeze_sha256,
    )
    crop_x, crop_y, compact_width, compact_height, cover_scale = reconstruct_crop(
        warpmap
    )
    first = blocks[0]
    trace_crop = (
        first.crop_x,
        first.crop_y,
        first.compact_width,
        first.compact_height,
    )
    reconstructed_crop = (crop_x, crop_y, compact_width, compact_height)
    if trace_crop != reconstructed_crop:
        raise Refusal(
            f"trace crop {trace_crop} != reconstructed Crop {reconstructed_crop}"
        )
    if (first.full_width, first.full_height) != (warpmap.width, warpmap.height):
        raise Refusal("trace full geometry differs from warpmap plane")
    image, tiff_hash = load_rgb16_tiff(
        tiff_path,
        compact_height,
        compact_width,
        instrument_freeze_sha256,
    )
    if len(grouped) > U16_MAX:
        raise Refusal("placed frame count exceeds uint16 contributor capacity")

    output = output.resolve()
    staging = fresh_staging(output)
    published = False
    arrays: list[np.ndarray] = []
    aggregate_sink: RowSink | None = None
    m8o_sink: RowSink | None = None
    try:
        shape = (3, compact_height, compact_width)
        pre_lower = create_array(
            staging / "pre-saturation-lower.npy", "<f4", shape, np.inf
        )
        pre_upper = create_array(
            staging / "pre-saturation-upper.npy", "<f4", shape, -np.inf
        )
        projected_lower = create_array(
            staging / "projected-lower.npy", "<f4", shape, np.inf
        )
        projected_upper = create_array(
            staging / "projected-upper.npy", "<f4", shape, -np.inf
        )
        contributors = create_array(
            staging / "valid-contributor-count.npy", "<u2", shape, 0
        )
        lower_frames = create_array(
            staging / "lower-frame-witness.npy", "<i4", shape, -1
        )
        upper_frames = create_array(
            staging / "upper-frame-witness.npy", "<i4", shape, -1
        )
        arrays.extend(
            (
                pre_lower,
                pre_upper,
                projected_lower,
                projected_upper,
                contributors,
                lower_frames,
                upper_frames,
            )
        )

        m8r_dir = staging / "m8-r-blocks"
        m8r_dir.mkdir()
        aggregate_sink = RowSink(staging / ".m8-r-all.raw", M8R_VIOLATION_DTYPE)
        block_summaries: list[dict[str, Any]] = []
        block_manifests: list[dict[str, Any]] = []
        for block in blocks:
            site_name = SITE_NAMES[block.site]
            destination = m8r_dir / (
                f"frame-{block.frame_order:08d}-s{block.site_x}{block.site_y}.npy"
            )
            block_sink = RowSink(
                m8r_dir
                / f".frame-{block.frame_order:08d}-s{block.site_x}{block.site_y}.raw",
                M8R_VIOLATION_DTYPE,
            )
            try:
                summary = verify_m8r_block(
                    block, chunk_rows, block_sink, aggregate_sink
                )
                saved = block_sink.finish(destination)
                close_memmap(saved)
            except Exception:
                block_sink.abort()
                raise
            block_summaries.append(summary)
            block_manifests.append(
                {
                    **summary,
                    "site_name": site_name,
                    "violation_array": artifact_metadata(staging, destination),
                }
            )
        all_m8r = aggregate_sink.finish(staging / "m8-r-violations.npy")
        close_memmap(all_m8r)
        aggregate_sink = None

        for frame_order in sorted(grouped):
            sites = grouped[frame_order]
            for y0 in range(0, compact_height, chunk_rows):
                y1 = min(compact_height, y0 + chunk_rows)
                native: dict[
                    tuple[int, int], tuple[np.ndarray, np.ndarray, np.ndarray]
                ] = {}
                for site, block in sites.items():
                    native[site] = compact_native_interval(
                        block, y0, y1, crop_x
                    )

                for channel, site in ((0, (0, 0)), (2, (1, 1))):
                    block = sites[site]
                    valid, black_lo, black_hi = native[site]
                    pre_lo, pre_hi, projected_lo, projected_hi = output_interval(
                        black_lo,
                        black_hi,
                        block.output_gain,
                        block.sensor_range,
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
                        projected_lo,
                        projected_hi,
                        frame_order,
                        contributors,
                        lower_frames,
                        upper_frames,
                    )

                valid_g1, g1_lo, g1_hi = native[GREEN_SITES[0]]
                valid_g2, g2_lo, g2_hi = native[GREEN_SITES[1]]
                if np.any(valid_g1 ^ valid_g2):
                    yy, xx = np.argwhere(valid_g1 ^ valid_g2)[0]
                    raise Refusal(
                        f"frame {frame_order}: G1/G2 coverage differs at "
                        f"({int(xx)},{int(yy + y0)})"
                    )
                g1 = sites[GREEN_SITES[0]]
                pre_lo, pre_hi, projected_lo, projected_hi = green_pair_interval(
                    g1_lo,
                    g1_hi,
                    g2_lo,
                    g2_hi,
                    g1.output_gain,
                    g1.sensor_range,
                )
                update_aggregate(
                    pre_lower,
                    pre_upper,
                    1,
                    y0,
                    valid_g1,
                    pre_lo,
                    pre_hi,
                    frame_order,
                )
                update_aggregate(
                    projected_lower,
                    projected_upper,
                    1,
                    y0,
                    valid_g1,
                    projected_lo,
                    projected_hi,
                    frame_order,
                    contributors,
                    lower_frames,
                    upper_frames,
                )

        for array in arrays:
            array.flush()
        expected_contributors = len(grouped)
        for y0 in range(0, compact_height, chunk_rows):
            y1 = min(compact_height, y0 + chunk_rows)
            count_chunk = np.asarray(contributors[:, y0:y1])
            if np.any(count_chunk != expected_contributors):
                channel, yy, xx = np.argwhere(
                    count_chunk != expected_contributors
                )[0]
                raise Refusal(
                    "unbracketed compact coordinate "
                    f"({int(xx)},{int(yy + y0)},{CHANNEL_NAMES[int(channel)]}): "
                    f"{int(count_chunk[channel, yy, xx])} contributors, "
                    f"expected {expected_contributors}"
                )
            for lower_map, upper_map, name in (
                (pre_lower, pre_upper, "pre-saturation"),
                (projected_lower, projected_upper, "projected"),
            ):
                lower_chunk = np.asarray(lower_map[:, y0:y1])
                upper_chunk = np.asarray(upper_map[:, y0:y1])
                if (
                    np.any(~np.isfinite(lower_chunk))
                    or np.any(~np.isfinite(upper_chunk))
                    or np.any(lower_chunk > upper_chunk)
                ):
                    raise Refusal(f"{name} aggregate interval is invalid")

        m8o_sink = RowSink(staging / ".m8-o.raw", M8O_VIOLATION_DTYPE)
        m8o = build_m8o_rows(
            capture,
            image,
            projected_lower,
            projected_upper,
            lower_frames,
            upper_frames,
            chunk_rows,
            m8o_sink,
        )
        all_m8o = m8o_sink.finish(staging / "m8-o-m136-violations.npy")
        close_memmap(all_m8o)
        m8o_sink = None

        rails = rail_disclosure(
            image,
            pre_lower,
            pre_upper,
            projected_lower,
            projected_upper,
            chunk_rows,
        )
        m8r_lower = sum(item["lower_violation_rows"] for item in block_summaries)
        m8r_upper = sum(item["upper_violation_rows"] for item in block_summaries)
        m8r_denominator = sum(
            item["eligible_samples"] for item in block_summaries
        )
        m8r_violations = m8r_lower + m8r_upper
        m8r = {
            "schema": "m136-m8-r",
            "schema_version": 1,
            "denominator": m8r_denominator,
            "lower_violations": m8r_lower,
            "upper_violations": m8r_upper,
            "violations": m8r_violations,
            "fraction_exact": f"{m8r_violations}/{m8r_denominator}",
            "fraction": m8r_violations / float(m8r_denominator),
            "percent": 100.0 * m8r_violations / float(m8r_denominator),
            "max_excess_over_tolerance": max(
                (
                    float(item["max_excess_over_tolerance"])
                    for item in block_summaries
                ),
                default=0.0,
            ),
            "block_count": len(block_summaries),
            "block_manifest": "m8-r-blocks/manifest.json",
            "violation_array": "m8-r-violations.npy",
        }
        write_json(
            m8r_dir / "manifest.json",
            {
                "schema": "m136-m8-r-block-manifest",
                "schema_version": 1,
                "blocks": block_manifests,
            },
        )
        write_json(staging / "m8-r.json", m8r)
        m8o_document = {
            "schema": "m136-m8-o",
            "schema_version": 1,
            "capture": capture,
            "status": "PASS" if m8o["violations"] == 0 else "FAIL",
            **m8o,
            "green_rule": GREEN_RULE,
            "green_rule_status": GREEN_RULE_STATUS,
            "violation_array": "m8-o-m136-violations.npy",
        }
        write_json(staging / "m8-o-m136.json", m8o_document)
        write_json(
            staging / "rail-disclosure.json",
            {
                "schema": "m136-rail-disclosure",
                "schema_version": 1,
                "capture": capture,
                "denominator": rails["denominator"],
                "rail_disclosure": rails["counts"],
                "fractions_over_denominator": rails[
                    "fractions_over_denominator"
                ],
            },
        )

        overall_status = (
            "PASS"
            if m8r["violations"] == 0 and m8o["violations"] == 0
            else "FAIL"
        )
        frame_site_manifest = [
            {
                "frame_order": block.frame_order,
                "site": SITE_NAMES[block.site],
                "site_x": block.site_x,
                "site_y": block.site_y,
                "channel": CHANNEL_NAMES[block.channel],
                "frame_path": str(block.frame_path),
                "source_sha256": block.frame_source_sha256,
                "trace": block.path.name,
                "trace_sha256": block.file_sha256,
            }
            for block in blocks
        ]
        expected_frame_sites = [
            f"{frame_order:08d}:{SITE_NAMES[site]}"
            for frame_order in sorted(grouped)
            for site in SITE_NAMES
        ]
        consumed_frame_sites = [
            f"{block.frame_order:08d}:{SITE_NAMES[block.site]}"
            for block in blocks
        ]
        meta = {
            "schema": "m136-checker-target",
            "schema_version": 1,
            "protocol": CHECKER_PROTOCOL,
            "checker_version": CHECKER_VERSION,
            "status": overall_status,
            "capture": capture,
            "green_rule": GREEN_RULE,
            "green_rule_status": GREEN_RULE_STATUS,
            "instrument_freeze_sha256": instrument_freeze_sha256,
            "kernel": {"id": TARGET_KERNEL, "name": "clamped-catmull"},
            "arithmetic_contract": ARITHMETIC_CONTRACT,
            "crop": {
                "x": crop_x,
                "y": crop_y,
                "width": compact_width,
                "height": compact_height,
                "cover_margin": COVER_MARGIN,
                "cover_scale": cover_scale,
                "bisection_steps": 60,
                "rounding": "inward",
            },
            "full_plane": {"width": first.full_width, "height": first.full_height},
            "placed_frames": len(grouped),
            "trace_block_count": len(blocks),
            "complete_frame_site_set": True,
            "expected_frame_sites": expected_frame_sites,
            "consumed_frame_sites": consumed_frame_sites,
            "frame_site_manifest": frame_site_manifest,
            "m8_r_status": "PASS" if m8r["violations"] == 0 else "FAIL",
            "m8_o_status": m8o_document["status"],
        }
        write_json(staging / "meta.json", meta)

        for array in arrays:
            close_memmap(array)
        arrays.clear()

        required_paths = (
            "meta.json",
            "m8-r.json",
            "m8-r-blocks/manifest.json",
            "m8-r-violations.npy",
            "pre-saturation-lower.npy",
            "pre-saturation-upper.npy",
            "projected-lower.npy",
            "projected-upper.npy",
            "valid-contributor-count.npy",
            "lower-frame-witness.npy",
            "upper-frame-witness.npy",
            "m8-o-m136.json",
            "m8-o-m136-violations.npy",
            "rail-disclosure.json",
        )
        provenance = {
            "schema": "m136-checker-provenance",
            "schema_version": 1,
            "protocol": CHECKER_PROTOCOL,
            "capture": capture,
            "command": [
                sys.executable,
                str(Path(__file__).resolve()),
                "adjudicate",
                "--capture",
                capture,
                "--input-dir",
                str(input_dir),
                "--trace-state",
                str(trace_state.resolve()),
                "--warpmap",
                str(warpmap.path),
                "--tiff",
                str(tiff_path.resolve()),
                "--output",
                str(output),
                "--preregistration",
                str(preregistration_path.resolve()),
                "--commissioning-report",
                str(commissioning_report.resolve()),
                "--source-commit",
                source_commit,
                "--candidate-binary",
                str(candidate_binary),
                "--instrument-freeze",
                str(instrument_freeze_path),
                "--green-rule",
                GREEN_RULE,
                "--chunk-rows",
                str(chunk_rows),
            ],
            "environment": {
                name: os.environ.get(name)
                for name in (
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "RAYON_NUM_THREADS",
                    "STREHL_DEFECT",
                    "STREHL_FULLRES_GATHER",
                    "STREHL_M8_CAPTURE",
                    "STREHL_M8_CHECKER",
                    "STREHL_M8_FREEZE_SHA256",
                    "STREHL_M8_TRACE_DIR",
                    "STREHL_PYRAMID_WORKERS",
                    "STREHL_WARPMAP",
                )
            },
            "versions": {
                "python": sys.version,
                "numpy": np.__version__,
                "tifffile": tifffile.__version__,
            },
            "source_commit": source_commit,
            "candidate_binary": {
                "path": str(candidate_binary),
                "sha256": sha256_file(candidate_binary),
            },
            "instrument_freeze": {
                "path": str(instrument_freeze_path),
                "sha256": instrument_freeze_sha256,
            },
            "instrument_freeze_sha256": instrument_freeze_sha256,
            "checker": {
                "path": str(Path(__file__).resolve()),
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "preregistration": {
                "path": str(preregistration_path.resolve()),
                "sha256": prereg_hash,
            },
            "prospective_interpretation": {
                "path": str(INTERPRETATION_PATH),
                "sha256": sha256_file(INTERPRETATION_PATH),
                "canonical_sha256": INTERPRETATION_CANONICAL_SHA256,
                "commit": INTERPRETATION_COMMIT,
            },
            "commissioning": commission_evidence,
            "warpmap": {
                "path": str(warpmap.path),
                "sha256": warpmap.sha256,
            },
            "output_tiff": {
                "path": str(tiff_path.resolve()),
                "sha256": tiff_hash,
            },
            "trace_sha256": {
                block.path.name: block.file_sha256 for block in blocks
            },
            "source_sha256": {
                str(path): digest
                for path, digest in sorted(
                    source_hashes.items(), key=lambda item: str(item[0])
                )
            },
            "green_rule": GREEN_RULE,
            "green_rule_status": GREEN_RULE_STATUS,
            "artifacts": {
                name: artifact_metadata(staging, staging / name)
                for name in required_paths
            },
        }
        write_json(staging / "provenance.json", provenance)
        publish_staging(staging, output)
        published = True
        print(
            json.dumps(
                {
                    "status": overall_status,
                    "capture": capture,
                    "m8_r_violations": m8r["violations"],
                    "m8_o_violations": m8o["violations"],
                    "green_rule": GREEN_RULE,
                    "green_rule_status": GREEN_RULE_STATUS,
                    "output": str(output),
                },
                sort_keys=True,
            )
        )
        return 0 if overall_status == "PASS" else 1
    finally:
        if aggregate_sink is not None:
            aggregate_sink.abort()
        if m8o_sink is not None:
            m8o_sink.abort()
        for array in arrays:
            close_memmap(array)
        if not published:
            shutil.rmtree(staging, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    commission_parser = subparsers.add_parser(
        "commission", help="score only the frozen commissioning fixture"
    )
    commission_parser.add_argument("--fixtures", type=Path, required=True)
    commission_parser.add_argument("--output", type=Path, required=True)

    adjudicate_parser = subparsers.add_parser(
        "adjudicate",
        help="adjudicate a registered target capture",
    )
    adjudicate_parser.add_argument("--capture", required=True)
    adjudicate_parser.add_argument("--input-dir", type=Path, required=True)
    adjudicate_parser.add_argument("--trace-state", type=Path, required=True)
    adjudicate_parser.add_argument("--warpmap", type=Path, required=True)
    adjudicate_parser.add_argument("--tiff", type=Path, required=True)
    adjudicate_parser.add_argument("--output", type=Path, required=True)
    adjudicate_parser.add_argument(
        "--preregistration",
        type=Path,
        default=PREREGISTRATION_PATH,
    )
    adjudicate_parser.add_argument(
        "--commissioning-report", type=Path, required=True
    )
    adjudicate_parser.add_argument("--source-commit", required=True)
    adjudicate_parser.add_argument("--candidate-binary", type=Path, required=True)
    adjudicate_parser.add_argument(
        "--instrument-freeze", type=Path, required=True
    )
    adjudicate_parser.add_argument(
        "--green-rule",
        choices=(GREEN_RULE,),
        required=True,
        help="prospectively adopted same-frame green pairing rule",
    )
    adjudicate_parser.add_argument(
        "--chunk-rows", type=int, default=CHUNK_ROWS_DEFAULT
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "commission":
            return commission(args.fixtures, args.output)
        return adjudicate(
            capture=args.capture,
            input_dir=args.input_dir,
            trace_state=args.trace_state,
            warpmap_path=args.warpmap,
            tiff_path=args.tiff,
            output=args.output,
            preregistration_path=args.preregistration,
            commissioning_report=args.commissioning_report,
            source_commit=args.source_commit,
            candidate_binary=args.candidate_binary,
            instrument_freeze=args.instrument_freeze,
            green_rule=args.green_rule,
            chunk_rows=args.chunk_rows,
        )
    except Refusal as error:
        print(
            json.dumps(
                {
                    "status": "UNMEASURED",
                    "error": str(error),
                    "command": args.command,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "UNMEASURED",
                    "error": f"{type(error).__name__}: {error}",
                    "command": args.command,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
