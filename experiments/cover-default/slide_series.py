"""Independent geometry adjudicator for the COVER calibration-slide series.

This program reads WarpMap sidecars and source-file metadata.  It does not
import the earlier ``audit.py``, invoke strehl, decode captures, fit placements,
or write files.  All results, including refusals, are emitted as deterministic
JSON on stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import stat
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


WIDTH = 3516
HEIGHT = 2344
MARGIN_PX = 3.0
SNR_K_SPAN_LIMIT = 0.0010
SNR_EDGE_SPAN_LIMIT_PX = 2
SUBSET_K_SPAN_LIMIT = 0.0010
ACTUAL_PRODUCT_DIAGNOSTIC = "ACTUAL_PRODUCT_DIAGNOSTIC"
IDENTITY_BITS = (
    "3ff0000000000000",
    "0000000000000000",
    "0000000000000000",
    "0000000000000000",
)
F64_BITS_RE = re.compile(r"[0-9a-fA-F]{16}\Z")
U64_BITS_RE = re.compile(r"[0-9a-fA-F]{16}\Z")
INTEGER_RE = re.compile(r"[0-9]+\Z")
PLANE_RE = re.compile(r"([0-9]+)x([0-9]+)\Z")


class AdjudicationError(ValueError):
    """A sidecar or invocation failed a frozen gate."""


class CommissionError(RuntimeError):
    """An in-memory commissioning truth was not recovered."""


@dataclass(frozen=True)
class StackSpec:
    name: str
    stack_name: str
    frames: int
    reference: int


STACK_SPECS = (
    StackSpec("flat-1s", "flat-et1s-sw4-cpl", 60, 30),
    StackSpec("flat-2p5s", "flat-et2.5s-sw4-cpl", 61, 30),
    StackSpec("flat-6s", "flat-et6s-sw4-cpl", 65, 32),
    StackSpec("tilted-sw10", "tilted-sw10-cpl", 92, 46),
    StackSpec("tilted-sw4", "tilted-sw4-cpl", 182, 91),
    StackSpec("all-axis-sw10", "very-tilted-all-axis-sw10-cpl", 197, 98),
)
SPECS_BY_NAME = {spec.name: spec for spec in STACK_SPECS}


@dataclass(frozen=True)
class SourceIdentity:
    """Full sorted source inventory used to validate one sidecar."""

    directory: Path
    entries: tuple[tuple[str, int], ...]
    digest: str
    inventory_sha256: str
    total_bytes: int


@dataclass(frozen=True)
class Placement:
    """One serialized reference-to-frame similarity."""

    bits: tuple[str, str, str, str]
    a: complex
    b: complex


@dataclass(frozen=True)
class RefusedPlacement:
    reason: str


FrameRecord = Placement | RefusedPlacement


@dataclass(frozen=True)
class SerializedOptionalF64:
    bits: str | None
    value: float | None


@dataclass(frozen=True)
class WarpMap:
    stack_name: str
    stack_digest: str
    frames: int
    width: int
    height: int
    reference: int
    strategy: str
    resampler: str
    heldout_px: SerializedOptionalF64
    cycle_floor_px: SerializedOptionalF64
    note: str
    records: tuple[FrameRecord, ...]


FNV1A64_OFFSET = 0xCBF29CE484222325
FNV1A64_PRIME = 0x00000100000001B3
U64_MASK = 0xFFFFFFFFFFFFFFFF


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CommissionError(message)


def _parse_uint(raw: str, key: str) -> int:
    if not INTEGER_RE.fullmatch(raw):
        raise AdjudicationError(
            f"{key}: expected an unsigned decimal integer, got {raw!r}"
        )
    return int(raw)


def _f64_from_bits(raw: str, key: str) -> tuple[str, float]:
    if not F64_BITS_RE.fullmatch(raw):
        raise AdjudicationError(
            f"{key}: expected exactly 16 hexadecimal f64 bits, got {raw!r}"
        )
    bits = raw.lower()
    value = struct.unpack(">d", int(bits, 16).to_bytes(8, "big"))[0]
    return bits, value


def _f64_to_bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def _unescape(raw: str) -> str:
    """Mirror WarpMap's line-format unescape operation."""

    output: list[str] = []
    index = 0
    while index < len(raw):
        char = raw[index]
        if char != "\\":
            output.append(char)
            index += 1
            continue
        index += 1
        if index == len(raw):
            output.append("\\")
            break
        escaped = raw[index]
        output.append("\n" if escaped == "n" else "\r" if escaped == "r" else escaped)
        index += 1
    return "".join(output)


def _stack_identity_bytes(entries: Sequence[tuple[str, int]]) -> bytes:
    encoded = bytearray()
    for name, size in entries:
        if size < 0 or size > U64_MASK:
            raise AdjudicationError(
                f"source entry {name!r} has size outside unsigned 64-bit range: {size}"
            )
        try:
            encoded.extend(name.encode("utf-8"))
        except UnicodeEncodeError as error:
            raise AdjudicationError(
                f"source entry name is not UTF-8 encodable: {name!r}"
            ) from error
        encoded.append(0)
        encoded.extend(size.to_bytes(8, "little"))
        encoded.append(0)
    return bytes(encoded)


def stack_digest(entries: Sequence[tuple[str, int]]) -> str:
    """Mirror ``StackIdentity::from_entries`` over an ordered inventory."""

    digest = FNV1A64_OFFSET
    for byte in _stack_identity_bytes(entries):
        digest = ((digest ^ byte) * FNV1A64_PRIME) & U64_MASK
    return f"{digest:016x}"


def _source_identity_from_entries(
    directory: Path, entries: Sequence[tuple[str, int]]
) -> SourceIdentity:
    fixed = tuple(entries)
    identity_bytes = _stack_identity_bytes(fixed)
    return SourceIdentity(
        directory=directory,
        entries=fixed,
        digest=stack_digest(fixed),
        inventory_sha256=hashlib.sha256(identity_bytes).hexdigest().upper(),
        total_bytes=sum(size for _, size in fixed),
    )


def _ascii_lower(value: str) -> str:
    return "".join(
        chr(ord(char) + 32) if "A" <= char <= "Z" else char for char in value
    )


def _ordered_source_entries(
    entries: Iterable[tuple[str, int]],
) -> tuple[tuple[str, int], ...]:
    # Python's WindowsPath ordering is case-folded, unlike Rust's PathBuf Ord.
    # For the UTF-8-encodable names admitted by _stack_identity_bytes, lexical
    # Unicode order is also WTF-8 byte order, which is Rust's Windows OsStr Ord.
    return tuple(sorted(entries, key=lambda entry: entry[0]))


def _read_source_identity(spec: StackSpec, directory: Path) -> SourceIdentity:
    try:
        children = tuple(directory.iterdir())
    except OSError as error:
        raise AdjudicationError(
            f"{spec.name}: cannot list source directory {directory}: {error}"
        ) from error

    entries: list[tuple[str, int]] = []
    for child in children:
        if _ascii_lower(child.suffix) != ".arw":
            continue
        try:
            # DirEntry::file_type().is_file() in the frozen Rust reference
            # renderer does not follow symlinks.
            metadata = child.lstat()
        except OSError as error:
            raise AdjudicationError(
                f"{spec.name}: cannot stat source entry {child}: {error}"
            ) from error
        if stat.S_ISREG(metadata.st_mode):
            entries.append((child.name, metadata.st_size))
    if not entries:
        raise AdjudicationError(f"{spec.name}: no .ARW source files in {directory}")
    return _source_identity_from_entries(directory, _ordered_source_entries(entries))


def _optional_f64(raw: str | None, key: str) -> SerializedOptionalF64:
    if raw is None:
        return SerializedOptionalF64(None, None)
    value_part = raw.split("#", 1)[0].strip()
    fields = value_part.split()
    if fields == ["none"]:
        return SerializedOptionalF64(None, None)
    if len(fields) != 1:
        raise AdjudicationError(f"{key}: expected one f64 bit field or 'none'")
    bits, value = _f64_from_bits(fields[0], key)
    if not math.isfinite(value):
        raise AdjudicationError(f"{key}: provenance value is not finite")
    return SerializedOptionalF64(bits, value)


def parse_warpmap_text(text: str, source: str = "<memory>") -> WarpMap:
    """Parse WarpMap v1 while retaining every authoritative f64 bit pattern."""

    headers: dict[str, str] = {}
    records: dict[int, FrameRecord] = {}
    end_count: int | None = None
    saw_magic = False
    saw_end = False
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

    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split(maxsplit=1)
        head = fields[0]
        rest = fields[1].strip() if len(fields) == 2 else ""

        if not saw_magic:
            if head != "strehl-warpmap" or rest != "1":
                raise AdjudicationError(
                    f"{source}:{line_number}: expected first record 'strehl-warpmap 1'"
                )
            saw_magic = True
            continue

        if saw_end:
            raise AdjudicationError(
                f"{source}:{line_number}: record follows the end marker"
            )

        if head == "end":
            end_count = _parse_uint(rest, f"{source}:{line_number}: end")
            saw_end = True
            continue

        if INTEGER_RE.fullmatch(head):
            index = int(head)
            if index in records:
                raise AdjudicationError(
                    f"{source}:{line_number}: duplicate frame record {index}"
                )
            state_fields = rest.split(maxsplit=1)
            if not state_fields:
                raise AdjudicationError(
                    f"{source}:{line_number}: frame {index} has no state"
                )
            state = state_fields[0]
            tail = state_fields[1] if len(state_fields) == 2 else ""
            if state == "refused":
                records[index] = RefusedPlacement(_unescape(tail))
                continue
            if state != "placed":
                raise AdjudicationError(
                    f"{source}:{line_number}: unknown frame state {state!r}"
                )
            bit_fields = tail.split("#", 1)[0].split()
            if len(bit_fields) != 4:
                raise AdjudicationError(
                    f"{source}:{line_number}: placed frame needs exactly four f64 fields"
                )
            decoded = [
                _f64_from_bits(value, f"{source}:{line_number}: placement")[0:2]
                for value in bit_fields
            ]
            bits = tuple(item[0] for item in decoded)
            values = tuple(item[1] for item in decoded)
            records[index] = Placement(
                bits=(bits[0], bits[1], bits[2], bits[3]),
                a=complex(values[0], values[1]),
                b=complex(values[2], values[3]),
            )
            continue

        if head == "strehl-warpmap":
            raise AdjudicationError(f"{source}:{line_number}: duplicate magic record")
        if head not in known_headers:
            raise AdjudicationError(f"{source}:{line_number}: unknown header {head!r}")
        if not rest:
            raise AdjudicationError(f"{source}:{line_number}: empty header {head!r}")
        if head in headers:
            raise AdjudicationError(
                f"{source}:{line_number}: duplicate header {head!r}"
            )
        headers[head] = rest

    if not saw_magic:
        raise AdjudicationError(f"{source}: no WarpMap magic record")
    if not saw_end or end_count is None:
        raise AdjudicationError(f"{source}: missing end marker")

    required = (
        "stack-name",
        "stack-digest",
        "frames",
        "plane",
        "reference",
        "strategy",
        "resampler",
    )
    missing = [key for key in required if key not in headers]
    if missing:
        raise AdjudicationError(f"{source}: missing header(s): {', '.join(missing)}")

    frames = _parse_uint(headers["frames"], f"{source}: frames")
    reference = _parse_uint(headers["reference"], f"{source}: reference")
    plane_match = PLANE_RE.fullmatch(headers["plane"])
    if plane_match is None:
        raise AdjudicationError(f"{source}: malformed plane {headers['plane']!r}")
    width, height = (int(value) for value in plane_match.groups())
    digest = headers["stack-digest"]
    if not U64_BITS_RE.fullmatch(digest):
        raise AdjudicationError(f"{source}: stack-digest is not 16 hexadecimal digits")
    if end_count != frames:
        raise AdjudicationError(
            f"{source}: end count {end_count} does not equal declared frame count {frames}"
        )
    expected_indices = set(range(frames))
    actual_indices = set(records)
    if actual_indices != expected_indices:
        missing_indices = sorted(expected_indices - actual_indices)
        extra_indices = sorted(actual_indices - expected_indices)
        raise AdjudicationError(
            f"{source}: frame records disagree with frames={frames}; "
            f"missing={missing_indices}, extra={extra_indices}"
        )

    ordered_records = tuple(records[index] for index in range(frames))
    return WarpMap(
        stack_name=_unescape(headers["stack-name"]),
        stack_digest=digest.lower(),
        frames=frames,
        width=width,
        height=height,
        reference=reference,
        strategy=_unescape(headers["strategy"]),
        resampler=headers["resampler"],
        heldout_px=_optional_f64(headers.get("heldout-px"), f"{source}: heldout-px"),
        cycle_floor_px=_optional_f64(
            headers.get("cycle-floor-px"), f"{source}: cycle-floor-px"
        ),
        note=_unescape(headers.get("note", "")),
        records=ordered_records,
    )


def _validate_warpmap(
    warpmap: WarpMap,
    spec: StackSpec,
    source: str,
    *,
    require_exact_reference: bool,
) -> None:
    """Apply the common frozen gates and the requested reference-gauge gate."""

    if warpmap.stack_name != spec.stack_name:
        raise AdjudicationError(
            f"{source}: stack-name {warpmap.stack_name!r}, expected {spec.stack_name!r}"
        )
    if warpmap.frames != spec.frames:
        raise AdjudicationError(
            f"{source}: frames={warpmap.frames}, expected {spec.frames} for {spec.name}"
        )
    if warpmap.reference != spec.reference:
        raise AdjudicationError(
            f"{source}: reference={warpmap.reference}, expected {spec.reference} for {spec.name}"
        )
    if (warpmap.width, warpmap.height) != (WIDTH, HEIGHT):
        raise AdjudicationError(
            f"{source}: plane={warpmap.width}x{warpmap.height}, expected {WIDTH}x{HEIGHT}"
        )
    if warpmap.resampler != "catmull-rom":
        raise AdjudicationError(
            f"{source}: resampler={warpmap.resampler!r}, expected 'catmull-rom'"
        )

    placed = sum(isinstance(record, Placement) for record in warpmap.records)
    refused = warpmap.frames - placed
    if refused:
        raise AdjudicationError(
            f"{source}: {placed} placed and {refused} refused; all {warpmap.frames} must be placed"
        )
    if placed != spec.frames:
        raise AdjudicationError(
            f"{source}: placed count {placed}, expected {spec.frames}"
        )

    for index, record in enumerate(warpmap.records):
        if not isinstance(record, Placement):
            raise AdjudicationError(f"{source}: frame {index} was refused")
        values = (record.a.real, record.a.imag, record.b.real, record.b.imag)
        if not all(math.isfinite(value) for value in values):
            raise AdjudicationError(
                f"{source}: frame {index} has a non-finite placement"
            )

    reference = warpmap.records[spec.reference]
    if require_exact_reference and (
        not isinstance(reference, Placement) or reference.bits != IDENTITY_BITS
    ):
        got = reference.bits if isinstance(reference, Placement) else "refused"
        raise AdjudicationError(
            f"{source}: reference transform is not exact f64 identity; got {got}"
        )


def validate_warpmap(
    warpmap: WarpMap, spec: StackSpec, source: str = "<memory>"
) -> None:
    """Apply every frozen strict pre-measurement gate."""

    _validate_warpmap(
        warpmap,
        spec,
        source,
        require_exact_reference=True,
    )


def validate_product_warpmap(
    warpmap: WarpMap, spec: StackSpec, source: str = "<memory>"
) -> None:
    """Apply every frozen gate except strict reference bit identity."""

    _validate_warpmap(
        warpmap,
        spec,
        source,
        require_exact_reference=False,
    )


def validate_source_identity(
    warpmap: WarpMap,
    spec: StackSpec,
    identity: SourceIdentity,
    source: str = "<memory>",
) -> None:
    """Refuse unless source names/sizes/count reproduce the sidecar identity."""

    if identity.directory.name != spec.stack_name:
        raise AdjudicationError(
            f"{source}: source directory name {identity.directory.name!r}, "
            f"expected {spec.stack_name!r}"
        )
    if len(identity.entries) != spec.frames:
        raise AdjudicationError(
            f"{source}: source inventory has {len(identity.entries)} .ARW files, "
            f"expected {spec.frames} for {spec.name}"
        )
    if identity.digest != warpmap.stack_digest:
        raise AdjudicationError(
            f"{source}: source stack digest {identity.digest}, "
            f"sidecar declares {warpmap.stack_digest}"
        )


def _reference_transform_report(warpmap: WarpMap, spec: StackSpec) -> dict[str, Any]:
    reference = warpmap.records[spec.reference]
    if not isinstance(reference, Placement):
        raise AdjudicationError(
            f"{spec.name}: reference frame {spec.reference} was refused"
        )
    half_width = warpmap.width * 0.5
    half_height = warpmap.height * 0.5
    delta_a = reference.a - 1.0
    maximum_displacement = max(
        abs(delta_a * complex(x, y) + reference.b)
        for x in (-half_width, half_width)
        for y in (-half_height, half_height)
    )
    return {
        "f64_bits": list(reference.bits),
        "exact_identity": reference.bits == IDENTITY_BITS,
        "max_centered_corner_displacement_px": maximum_displacement,
    }


def _placements(warpmap: WarpMap) -> tuple[Placement, ...]:
    placed = tuple(
        record for record in warpmap.records if isinstance(record, Placement)
    )
    if not placed:
        raise AdjudicationError("cover geometry requires at least one placement")
    return placed


def _corners(width: int, height: int) -> tuple[tuple[float, float], ...]:
    return (
        (0.0, 0.0),
        (width - 1.0, 0.0),
        (0.0, height - 1.0),
        (width - 1.0, height - 1.0),
    )


def _mapped_corners(
    placement: Placement, width: int, height: int, k: float
) -> tuple[tuple[float, float], ...]:
    cx, cy = width * 0.5, height * 0.5
    mapped: list[tuple[float, float]] = []
    for x, y in _corners(width, height):
        source = placement.a * (k * complex(x - cx, y - cy)) + placement.b
        mapped.append((source.real + cx, source.imag + cy))
    return tuple(mapped)


def corners_are_covered(
    placements: Iterable[Placement],
    width: int,
    height: int,
    margin: float,
    k: float,
) -> bool:
    """Test the four exact extreme points of every placed similarity."""

    for placement in placements:
        for source_x, source_y in _mapped_corners(placement, width, height, k):
            if not (
                source_x >= margin
                and source_y >= margin
                and source_x <= width - 1.0 - margin
                and source_y <= height - 1.0 - margin
            ):
                return False
    return True


def cover_scale(
    placements: Iterable[Placement],
    width: int = WIDTH,
    height: int = HEIGHT,
    margin: float = MARGIN_PX,
) -> float:
    """Return the largest commissioned ``k <= 1`` after 60 bisections."""

    fixed = tuple(placements)
    if not fixed:
        raise AdjudicationError("cover geometry requires at least one placement")
    if corners_are_covered(fixed, width, height, margin, 1.0):
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if corners_are_covered(fixed, width, height, margin, mid):
            lo = mid
        else:
            hi = mid
    if lo <= 0.0:
        raise AdjudicationError("no positive cover scale covers all four corners")
    return lo


def cover_rectangle(width: int, height: int, k: float) -> tuple[int, int, int, int]:
    def axis(size: int) -> tuple[int, int]:
        low = 0.5 * size * (1.0 - k)
        high = low + k * (size - 1.0)
        first = max(0, math.ceil(low))
        last = max(first, min(size - 1, math.floor(high)))
        return first, last - first + 1

    x, crop_width = axis(width)
    y, crop_height = axis(height)
    return x, y, crop_width, crop_height


def crop_edge_losses(
    width: int, height: int, rectangle: Sequence[int]
) -> dict[str, int]:
    x, y, crop_width, crop_height = rectangle
    return {
        "left": x,
        "right": width - x - crop_width,
        "top": y,
        "bottom": height - y - crop_height,
    }


def strict_order(points: Sequence[tuple[str, float]]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    adjacent: list[dict[str, Any]] = []
    for (left_name, left_k), (right_name, right_k) in zip(points, points[1:]):
        passed = left_k > right_k
        comparison = {
            "left": left_name,
            "left_k": left_k,
            "required_relation": ">",
            "right": right_name,
            "right_k": right_k,
            "pass": passed,
        }
        adjacent.append(comparison)
        if not passed:
            violations.append(
                {
                    **comparison,
                    "failure": "equality" if left_k == right_k else "reversal",
                }
            )
    return {
        "adjacent_comparisons": adjacent,
        "pass": not violations,
        "verdict": "ORDERED" if not violations else "NOT_ORDERED",
        "violations": violations,
    }


def _span(values: Iterable[float | int]) -> float | int:
    fixed = tuple(values)
    if not fixed:
        raise AdjudicationError("a span requires at least one value")
    return max(fixed) - min(fixed)


def _edge_spans(losses: Sequence[dict[str, int]]) -> dict[str, int]:
    return {
        edge: int(_span(row[edge] for row in losses))
        for edge in ("left", "right", "top", "bottom")
    }


def subset_indices() -> tuple[int, ...]:
    """Frozen N=182 to N=92 membership; no data-dependent selection."""

    return tuple(math.floor(i * 181 / 91 + 0.5) for i in range(92))


def _measurement_row(
    spec: StackSpec,
    path: Path,
    raw_bytes: bytes,
    warpmap: WarpMap,
    identity: SourceIdentity,
) -> dict[str, Any]:
    placements = _placements(warpmap)
    k = cover_scale(placements)
    rectangle = cover_rectangle(warpmap.width, warpmap.height, k)
    losses = crop_edge_losses(warpmap.width, warpmap.height, rectangle)
    return {
        "name": spec.name,
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(raw_bytes).hexdigest().upper(),
        "validation": "PASS",
        "source_identity": {
            "stack_name": warpmap.stack_name,
            "source_directory": str(identity.directory.resolve()),
            "sidecar_stack_digest": warpmap.stack_digest,
            "recomputed_stack_digest": identity.digest,
            "digest_basis": "sorted source file name and size entries",
            "validated": identity.digest == warpmap.stack_digest,
            "frames": len(identity.entries),
            "total_bytes": identity.total_bytes,
            "first_entry": {
                "name": identity.entries[0][0],
                "size": identity.entries[0][1],
            },
            "last_entry": {
                "name": identity.entries[-1][0],
                "size": identity.entries[-1][1],
            },
            "inventory_sha256": identity.inventory_sha256,
        },
        "frames": warpmap.frames,
        "reference": warpmap.reference,
        "plane": [warpmap.width, warpmap.height],
        "resampler": warpmap.resampler,
        "placed": len(placements),
        "refused": warpmap.frames - len(placements),
        "reference_identity_bits": list(IDENTITY_BITS),
        "reference_transform": _reference_transform_report(warpmap, spec),
        "strategy": warpmap.strategy,
        "note": warpmap.note,
        "heldout_px": warpmap.heldout_px.value,
        "heldout_px_bits": warpmap.heldout_px.bits,
        "cycle_floor_px": warpmap.cycle_floor_px.value,
        "cycle_floor_px_bits": warpmap.cycle_floor_px.bits,
        "margin_px": MARGIN_PX,
        "corner_count": 4,
        "k": k,
        "one_over_k_minus_one": 1.0 / k - 1.0,
        "crop_rect_xywh": list(rectangle),
        "crop_edge_loss_px": losses,
    }


def _read_sidecar(
    spec: StackSpec, path: Path, *, product_mode: bool = False
) -> tuple[bytes, WarpMap]:
    try:
        raw_bytes = path.read_bytes()
    except OSError as error:
        raise AdjudicationError(f"{spec.name}: cannot read {path}: {error}") from error
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AdjudicationError(
            f"{spec.name}: sidecar is not UTF-8: {error}"
        ) from error
    source = f"{spec.name}={path}"
    warpmap = parse_warpmap_text(text, source)
    if product_mode:
        validate_product_warpmap(warpmap, spec, source)
    else:
        validate_warpmap(warpmap, spec, source)
    return raw_bytes, warpmap


def _bindings(
    raw_bindings: Sequence[str], command_name: str, binding_kind: str
) -> dict[str, Path]:
    if len(raw_bindings) != len(STACK_SPECS):
        raise AdjudicationError(
            f"{command_name} requires exactly {len(STACK_SPECS)} "
            f"name=path {binding_kind}"
        )
    bindings: dict[str, Path] = {}
    for raw in raw_bindings:
        name, separator, path_text = raw.partition("=")
        if not separator or not name or not path_text:
            raise AdjudicationError(f"expected name=path, got {raw!r}")
        if name not in SPECS_BY_NAME:
            raise AdjudicationError(
                f"unknown sidecar name {name!r}; expected {sorted(SPECS_BY_NAME)}"
            )
        if name in bindings:
            raise AdjudicationError(f"duplicate {binding_kind} name {name!r}")
        bindings[name] = Path(path_text)
    missing = [spec.name for spec in STACK_SPECS if spec.name not in bindings]
    if missing:
        raise AdjudicationError(f"missing {binding_kind} name(s): {', '.join(missing)}")
    return bindings


def _command_measure(args: argparse.Namespace, *, product_mode: bool) -> dict[str, Any]:
    command_name = "measure-product" if product_mode else "measure"
    bindings = _bindings(args.sidecars, command_name, "sidecars")
    source_bindings = _bindings(args.sources, command_name, "source directories")
    rows: list[dict[str, Any]] = []
    warpmaps: dict[str, WarpMap] = {}
    for spec in STACK_SPECS:
        path = bindings[spec.name]
        identity = _read_source_identity(spec, source_bindings[spec.name])
        raw_bytes, warpmap = _read_sidecar(
            spec,
            path,
            product_mode=product_mode,
        )
        validate_source_identity(
            warpmap,
            spec,
            identity,
            f"{spec.name}={source_bindings[spec.name]}",
        )
        rows.append(_measurement_row(spec, path, raw_bytes, warpmap, identity))
        warpmaps[spec.name] = warpmap
    by_name = {row["name"]: row for row in rows}

    ordered_points = (
        ("source-anchor-n22", 0.9870),
        ("flat-1s-n60", by_name["flat-1s"]["k"]),
        ("flat-2p5s-n61", by_name["flat-2p5s"]["k"]),
        ("flat-6s-n65", by_name["flat-6s"]["k"]),
        ("tilted-sw10-n92", by_name["tilted-sw10"]["k"]),
        ("tilted-sw4-n182", by_name["tilted-sw4"]["k"]),
        ("all-axis-sw10-n197", by_name["all-axis-sw10"]["k"]),
        ("source-anchor-n299", 0.9321),
    )
    order = strict_order(ordered_points)
    order.update(
        {
            "chain": [name for name, _ in ordered_points],
            "source_anchor_assertions": {
                "n22": {"decimal": "0.9870", "k": 0.9870},
                "n299": {"decimal": "0.9321", "k": 0.9321},
            },
        }
    )

    flat_names = ("flat-1s", "flat-2p5s", "flat-6s")
    flat_rows = [by_name[name] for name in flat_names]
    k_span = float(_span(row["k"] for row in flat_rows))
    edge_spans = _edge_spans([row["crop_edge_loss_px"] for row in flat_rows])
    edge_pass = {
        edge: span <= SNR_EDGE_SPAN_LIMIT_PX for edge, span in edge_spans.items()
    }
    snr_pass = k_span <= SNR_K_SPAN_LIMIT and all(edge_pass.values())
    snr_control = {
        "names": list(flat_names),
        "k_span": k_span,
        "k_span_limit": SNR_K_SPAN_LIMIT,
        "k_span_pass": k_span <= SNR_K_SPAN_LIMIT,
        "crop_edge_loss_span_px": edge_spans,
        "crop_edge_loss_span_limit_px": SNR_EDGE_SPAN_LIMIT_PX,
        "crop_edge_pass": edge_pass,
        "pass": snr_pass,
        "verdict": (
            "ESSENTIALLY_UNCHANGED" if snr_pass else "EXPOSURE_SOLVE_SENSITIVE"
        ),
    }

    indices = subset_indices()
    tilted_full = _placements(warpmaps["tilted-sw4"])
    tilted_subset = tuple(tilted_full[index] for index in indices)
    subset_k = cover_scale(tilted_subset)
    full_k = by_name["tilted-sw4"]["k"]
    sparse_k = by_name["tilted-sw10"]["k"]
    removal_delta = subset_k - full_k
    cross_capture_delta = subset_k - sparse_k
    absolute_cross_capture_delta = abs(cross_capture_delta)
    removal_pass = subset_k >= full_k
    cross_capture_pass = absolute_cross_capture_delta <= SUBSET_K_SPAN_LIMIT
    step_width_control = {
        "membership_formula": "floor(i * 181 / 91 + 0.5), i=0..91",
        "source_indices": list(indices),
        "source_index_count": len(indices),
        "source_index_unique_count": len(set(indices)),
        "source_reference_index": 91,
        "subset_reference_position": indices.index(91),
        "full_n182_k": full_k,
        "tilted_sw10_n92_k": sparse_k,
        "subset_n182_to_n92_k": subset_k,
        "full_n92_minus_full_n182_delta_k": sparse_k - full_k,
        "removed_constraints_delta_k": removal_delta,
        "cross_capture_subset_minus_n92_delta_k": cross_capture_delta,
        "abs_subset_minus_n92_k": absolute_cross_capture_delta,
        "cross_capture_limit": SUBSET_K_SPAN_LIMIT,
        "removing_constraints_cannot_lower_k": removal_pass,
        "cross_capture_pass": cross_capture_pass,
        "pass": removal_pass and cross_capture_pass,
        "verdict": (
            "HARNESS_FAILURE"
            if not removal_pass
            else "DEPTH_DENSITY_SUPPORTED"
            if cross_capture_pass
            else "CAPTURE_STEP_WIDTH_SENSITIVE"
        ),
    }

    if product_mode:
        for control in (order, snr_control, step_width_control):
            control["diagnostic_label"] = ACTUAL_PRODUCT_DIAGNOSTIC

    payload = {
        "command": command_name,
        "status": "MEASURED",
        "method": {
            "serialized_values": "IEEE-754 binary64 decoded from exact 16-hex-digit fields",
            "geometry": "3 px margin; all four plane corners; 60 bisections",
            "membership": "all placed frames, except only the preregistered N182-to-N92 subset",
            "source_identity": "FNV-1a-64 over every sorted .ARW name, NUL, little-endian u64 size, NUL",
            "invokes_strehl": False,
            "writes_result_files": False,
        },
        "sidecars": rows,
        "strict_order": order,
        "snr_control": snr_control,
        "step_width_control": step_width_control,
    }
    if product_mode:
        nonexact_references = [
            row["name"]
            for row in rows
            if not row["reference_transform"]["exact_identity"]
        ]
        payload.update(
            {
                "diagnostic_label": ACTUAL_PRODUCT_DIAGNOSTIC,
                "strict_preregistered_status": (
                    "UNMEASURABLE_REFERENCE_NOT_BIT_IDENTITY"
                    if nonexact_references
                    else "MEASURABLE"
                ),
                "nonexact_reference_maps": nonexact_references,
            }
        )
    return payload


def command_measure(args: argparse.Namespace) -> dict[str, Any]:
    return _command_measure(args, product_mode=False)


def command_measure_product(args: argparse.Namespace) -> dict[str, Any]:
    return _command_measure(args, product_mode=True)


def _placement(
    a_re: float = 1.0,
    a_im: float = 0.0,
    b_re: float = 0.0,
    b_im: float = 0.0,
) -> Placement:
    values = (a_re, a_im, b_re, b_im)
    return Placement(
        bits=tuple(_f64_to_bits(value) for value in values),  # type: ignore[arg-type]
        a=complex(a_re, a_im),
        b=complex(b_re, b_im),
    )


def _synthetic_sidecar(spec: StackSpec, digest: str) -> str:
    identity = " ".join(IDENTITY_BITS)
    lines = [
        "strehl-warpmap 1",
        "stack-name " + spec.stack_name,
        "stack-digest " + digest,
        f"frames {spec.frames}",
        f"plane {WIDTH}x{HEIGHT}",
        f"reference {spec.reference}",
        "strategy synthetic-commission",
        "resampler catmull-rom",
        "heldout-px none",
        "cycle-floor-px none",
        "note in-memory only",
    ]
    lines.extend(f"{index} placed {identity}" for index in range(spec.frames))
    lines.append(f"end {spec.frames}")
    return "\n".join(lines) + "\n"


def _replace_line(text: str, prefix: str, replacement: str) -> str:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    _require(len(matches) == 1, f"commission mutation prefix {prefix!r} was ambiguous")
    lines[matches[0]] = replacement
    return "\n".join(lines) + "\n"


def _expect_refusal(text: str, spec: StackSpec) -> str:
    try:
        parsed = parse_warpmap_text(text)
        validate_warpmap(parsed, spec)
    except AdjudicationError as error:
        return str(error)
    raise CommissionError("a planted invalid sidecar was accepted")


def _expect_product_refusal(text: str, spec: StackSpec) -> str:
    try:
        parsed = parse_warpmap_text(text)
        validate_product_warpmap(parsed, spec)
    except AdjudicationError as error:
        return str(error)
    raise CommissionError("product mode accepted a planted invalid sidecar")


def _expect_source_refusal(
    warpmap: WarpMap, spec: StackSpec, identity: SourceIdentity
) -> str:
    try:
        validate_source_identity(warpmap, spec, identity)
    except AdjudicationError as error:
        return str(error)
    raise CommissionError("a planted source-identity mismatch was accepted")


def command_commission(_: argparse.Namespace) -> dict[str, Any]:
    identity = _placement()
    defect = _placement(b_re=16.0, b_im=-12.0)
    smaller = _placement(b_re=4.0, b_im=-3.0)
    baseline_k = cover_scale((identity,))
    defect_k = cover_scale((identity, defect))
    smaller_k = cover_scale((identity, smaller))
    restored_k = cover_scale((identity,))
    baseline_corners = _mapped_corners(identity, WIDTH, HEIGHT, 1.0)
    defect_corners = _mapped_corners(defect, WIDTH, HEIGHT, 1.0)
    corner_deltas = [
        math.hypot(got_x - want_x, got_y - want_y)
        for (want_x, want_y), (got_x, got_y) in zip(baseline_corners, defect_corners)
    ]
    _require(max(corner_deltas) > 0.0, "known transform defect was not detected")
    _require(
        defect_k < smaller_k < baseline_k, "smaller transform defect did not improve k"
    )
    _require(restored_k == baseline_k, "restored transform did not return exact k")
    _require(
        _mapped_corners(identity, WIDTH, HEIGHT, 1.0) == baseline_corners,
        "restored corners were not exact",
    )

    valid_points = (
        ("anchor22", 0.9870),
        ("k60", 0.9820),
        ("k61", 0.9770),
        ("k65", 0.9720),
        ("k92", 0.9660),
        ("k182", 0.9550),
        ("k197", 0.9440),
        ("anchor299", 0.9321),
    )
    valid_order = strict_order(valid_points)
    equality_points = list(valid_points)
    equality_points[2] = (equality_points[2][0], equality_points[1][1])
    equality_order = strict_order(equality_points)
    reversal_points = list(valid_points)
    reversal_points[3], reversal_points[4] = (
        reversal_points[4],
        reversal_points[3],
    )
    reversal_order = strict_order(reversal_points)
    _require(valid_order["pass"], "valid strict chain was rejected")
    _require(
        not equality_order["pass"]
        and any(row["failure"] == "equality" for row in equality_order["violations"]),
        "strict order accepted equality",
    )
    _require(
        not reversal_order["pass"]
        and any(row["failure"] == "reversal" for row in reversal_order["violations"]),
        "strict order accepted a reversal",
    )

    threshold_span = float(_span((0.0, SNR_K_SPAN_LIMIT)))
    above_threshold = math.nextafter(SNR_K_SPAN_LIMIT, math.inf)
    above_span = float(_span((0.0, above_threshold)))
    _require(threshold_span <= SNR_K_SPAN_LIMIT, "SNR threshold boundary was rejected")
    _require(above_span > SNR_K_SPAN_LIMIT, "SNR value above threshold was accepted")

    edge_boundary_rows = (
        {"left": 4, "right": 7, "top": 3, "bottom": 8},
        {"left": 6, "right": 5, "top": 4, "bottom": 6},
        {"left": 5, "right": 6, "top": 5, "bottom": 7},
    )
    edge_boundary_spans = _edge_spans(edge_boundary_rows)
    edge_outside_rows = list(edge_boundary_rows)
    edge_outside_rows[-1] = {**edge_outside_rows[-1], "left": 7}
    edge_outside_spans = _edge_spans(edge_outside_rows)
    _require(
        all(value <= SNR_EDGE_SPAN_LIMIT_PX for value in edge_boundary_spans.values())
        and edge_boundary_spans["left"] == SNR_EDGE_SPAN_LIMIT_PX,
        "crop-edge span boundary was rejected",
    )
    _require(
        edge_outside_spans["left"] > SNR_EDGE_SPAN_LIMIT_PX,
        "crop-edge span above the boundary was accepted",
    )

    indices = subset_indices()
    _require(len(indices) == 92, "subset formula did not return 92 indices")
    _require(len(set(indices)) == 92, "subset formula returned duplicate indices")
    _require(
        {0, 91, 181}.issubset(indices),
        "subset formula omitted an endpoint or the reference",
    )
    full_constraints = [identity] * 182
    full_constraints[1] = defect
    subset_constraints = tuple(full_constraints[index] for index in indices)
    full_k = cover_scale(full_constraints)
    subset_k = cover_scale(subset_constraints)
    _require(
        1 not in indices, "commission's planted removed constraint survived the subset"
    )
    _require(subset_k >= full_k, "removing constraints lowered k")

    fixed_digest_vector = (("a.ARW", 10), ("b.ARW", 20))
    fixed_digest = stack_digest(fixed_digest_vector)
    _require(
        fixed_digest == "9d06cf05b27f7b40",
        "FNV-1a implementation missed the fixed external digest oracle",
    )
    _require(
        stack_digest((("a.ARW", 11), ("b.ARW", 20))) != fixed_digest,
        "source-size mutation did not change the stack digest",
    )
    _require(
        stack_digest(fixed_digest_vector) == fixed_digest,
        "restored source inventory did not restore the digest exactly",
    )
    mixed_case_entries = _ordered_source_entries((("a.ARW", 10), ("B.ARW", 20)))
    _require(
        tuple(name for name, _ in mixed_case_entries) == ("B.ARW", "a.ARW"),
        "source inventory used case-folded Windows Path ordering",
    )
    _require(
        stat.S_ISREG(stat.S_IFREG | 0o644) and not stat.S_ISREG(stat.S_IFLNK | 0o777),
        "source file-type gate admitted a symbolic link",
    )

    spec = STACK_SPECS[0]
    synthetic_entries = tuple(
        (f"DSC{index:05d}.ARW", 1_000_000 + index) for index in range(spec.frames)
    )
    synthetic_identity = _source_identity_from_entries(
        Path(spec.stack_name), synthetic_entries
    )
    good_text = _synthetic_sidecar(spec, synthetic_identity.digest)
    good_map = parse_warpmap_text(good_text)
    validate_warpmap(good_map, spec)
    validate_source_identity(good_map, spec, synthetic_identity)
    wrong_digest_text = _replace_line(
        good_text,
        "stack-digest ",
        "stack-digest 0000000000000000",
    )
    wrong_digest_refusal = _expect_source_refusal(
        parse_warpmap_text(wrong_digest_text), spec, synthetic_identity
    )
    missing_entry_identity = _source_identity_from_entries(
        Path(spec.stack_name), synthetic_entries[:-1]
    )
    missing_entry_refusal = _expect_source_refusal(
        good_map, spec, missing_entry_identity
    )
    subtle_bits = _f64_to_bits(math.nextafter(1.0, math.inf))
    subtle_value = _f64_from_bits(subtle_bits, "commission subtle f64")[1]
    _require(
        _f64_to_bits(subtle_value) == subtle_bits,
        "serialized f64 bit pattern did not round-trip exactly",
    )

    reference_line = f"{spec.reference} placed " + " ".join(IDENTITY_BITS)
    nonidentity_bits = list(IDENTITY_BITS)
    nonidentity_bits[2] = _f64_to_bits(1.0)
    validation_refusals = {
        "wrong_reference_index": _expect_refusal(
            _replace_line(good_text, "reference ", f"reference {spec.reference - 1}"),
            spec,
        ),
        "nonidentity_reference_transform": _expect_refusal(
            _replace_line(
                good_text,
                f"{spec.reference} placed ",
                f"{spec.reference} placed " + " ".join(nonidentity_bits),
            ),
            spec,
        ),
        "refused_frame": _expect_refusal(
            _replace_line(good_text, "0 placed ", "0 refused planted-refusal"), spec
        ),
        "wrong_resampler": _expect_refusal(
            _replace_line(good_text, "resampler ", "resampler bilinear"), spec
        ),
        "wrong_dimensions": _expect_refusal(
            _replace_line(good_text, "plane ", f"plane {WIDTH - 1}x{HEIGHT}"), spec
        ),
        "wrong_frame_count": _expect_refusal(
            _replace_line(good_text, "frames ", f"frames {spec.frames - 1}"), spec
        ),
    }
    _require(
        reference_line in good_text, "synthetic reference line was not constructed"
    )

    material_placement = _placement(b_re=30.0, b_im=40.0)
    material_text = _replace_line(
        good_text,
        f"{spec.reference} placed ",
        f"{spec.reference} placed " + " ".join(material_placement.bits),
    )
    strict_reference_refusal = _expect_refusal(material_text, spec)
    _require(
        "reference transform is not exact f64 identity" in strict_reference_refusal,
        "strict mode did not reject the material nonidentity reference",
    )
    material_map = parse_warpmap_text(material_text)
    records_before = material_map.records
    reference_before = material_map.records[spec.reference]
    validate_product_warpmap(material_map, spec)
    material_row = _measurement_row(
        spec,
        Path("<commission-memory>"),
        material_text.encode("utf-8"),
        material_map,
        synthetic_identity,
    )
    reference_after = material_map.records[spec.reference]
    material_report = material_row["reference_transform"]
    transform_unchanged = (
        material_map.records is records_before
        and reference_after is reference_before
        and reference_after == material_placement
    )
    _require(transform_unchanged, "product mode mutated the reference transform")
    _require(
        material_report["f64_bits"] == list(material_placement.bits),
        "product mode did not report the serialized reference bits unchanged",
    )
    _require(
        not material_report["exact_identity"],
        "product mode incorrectly reported exact reference identity",
    )
    _require(
        material_report["max_centered_corner_displacement_px"] == 50.0,
        "reference displacement did not recover the exact 30-40-50 oracle",
    )
    _require(
        material_row["k"] < baseline_k,
        "product measurement did not retain the material reference transform",
    )
    product_common_gate_refusal = _expect_product_refusal(
        _replace_line(material_text, "resampler ", "resampler bilinear"),
        spec,
    )

    return {
        "command": "commission",
        "status": "COMMISSIONED",
        "geometry_defect": {
            "baseline_k": baseline_k,
            "known_defect_k": defect_k,
            "smaller_defect_k": smaller_k,
            "restored_k": restored_k,
            "known_defect_corner_delta_px": corner_deltas,
            "detected": max(corner_deltas) > 0.0 and defect_k < baseline_k,
            "smaller_defect_improves": defect_k < smaller_k < baseline_k,
            "restoration_exact": restored_k == baseline_k,
        },
        "strict_order": {
            "valid_chain": valid_order,
            "equality_plant": equality_order,
            "reversal_plant": reversal_order,
        },
        "snr_k_span_boundary": {
            "limit": SNR_K_SPAN_LIMIT,
            "at_limit": threshold_span,
            "at_limit_pass": threshold_span <= SNR_K_SPAN_LIMIT,
            "next_float_above_limit": above_span,
            "next_float_above_limit_pass": above_span <= SNR_K_SPAN_LIMIT,
        },
        "crop_edge_span_boundary": {
            "limit_px": SNR_EDGE_SPAN_LIMIT_PX,
            "at_limit_spans_px": edge_boundary_spans,
            "above_limit_spans_px": edge_outside_spans,
        },
        "subset": {
            "formula": "floor(i * 181 / 91 + 0.5), i=0..91",
            "indices": list(indices),
            "count": len(indices),
            "unique_count": len(set(indices)),
            "contains_0_91_181": {0, 91, 181}.issubset(indices),
            "full_k": full_k,
            "subset_k": subset_k,
            "removing_constraints_cannot_lower_k": subset_k >= full_k,
        },
        "warpmap_validation": {
            "valid_sidecar_accepted": True,
            "exact_f64_bits_round_trip": subtle_bits,
            "refusals": validation_refusals,
        },
        "source_identity": {
            "fixed_external_vector_entries": list(fixed_digest_vector),
            "fixed_external_vector_digest": fixed_digest,
            "mixed_case_sort_order": [name for name, _ in mixed_case_entries],
            "symbolic_link_is_regular_file": stat.S_ISREG(stat.S_IFLNK | 0o777),
            "source_size_mutation_detected": (
                stack_digest((("a.ARW", 11), ("b.ARW", 20))) != fixed_digest
            ),
            "restoration_exact": stack_digest(fixed_digest_vector) == fixed_digest,
            "valid_inventory_accepted": True,
            "wrong_digest_refusal": wrong_digest_refusal,
            "missing_entry_refusal": missing_entry_refusal,
        },
        "reference_gauge": {
            "strict_reference_refusal": strict_reference_refusal,
            "product_nonidentity_accepted": True,
            "product_common_gate_refusal": product_common_gate_refusal,
            "serialized_transform_unchanged": transform_unchanged,
            "reference_transform": material_report,
            "exact_displacement_oracle_px": 50.0,
            "admission_threshold_px": None,
            "material_nonidentity_reported_without_threshold": (
                material_report["max_centered_corner_displacement_px"] == 50.0
            ),
            "identity_baseline_k": baseline_k,
            "actual_product_k": material_row["k"],
        },
        "invokes_strehl": False,
        "writes_result_files": False,
    }


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise AdjudicationError(message)


def parser() -> argparse.ArgumentParser:
    result = JsonArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)

    commission = commands.add_parser("commission")
    commission.set_defaults(run=command_commission)

    measure = commands.add_parser("measure")
    measure.add_argument(
        "--source",
        dest="sources",
        action="append",
        required=True,
        metavar="NAME=DIR",
    )
    measure.add_argument("sidecars", nargs="+", metavar="NAME=PATH")
    measure.set_defaults(run=command_measure)

    measure_product = commands.add_parser("measure-product")
    measure_product.add_argument(
        "--source",
        dest="sources",
        action="append",
        required=True,
        metavar="NAME=DIR",
    )
    measure_product.add_argument("sidecars", nargs="+", metavar="NAME=PATH")
    measure_product.set_defaults(run=command_measure_product)
    return result


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))


def main(argv: Sequence[str] | None = None) -> int:
    actual_argv = list(sys.argv[1:] if argv is None else argv)
    command = actual_argv[0] if actual_argv else None
    try:
        args = parser().parse_args(actual_argv)
        payload = args.run(args)
    except (AdjudicationError, CommissionError) as error:
        _print_json(
            {
                "command": command,
                "error": str(error),
                "status": (
                    "UNMEASURABLE"
                    if command in {"measure", "measure-product"}
                    else "COMMISSION_FAILED"
                    if command == "commission"
                    else "REFUSED"
                ),
            }
        )
        return 2
    _print_json(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
