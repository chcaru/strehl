"""Prospective M193 consumer: input-derived authority, bounded path registration.

This module preserves successful v1 manifest bytes. It does not authenticate an
adapter's claimed output map or make the v1 single-reference method cover RAW.
TrustedInputBinding is an in-process registrar capability, not a Python sandbox.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import struct
import sys
import tempfile
from dataclasses import dataclass
from functools import cmp_to_key
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "m193b_frozen_reference", HERE.parent / "M193-cover-overlap" / "reference.py"
)
assert _spec is not None and _spec.loader is not None
v1 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = v1
_spec.loader.exec_module(v1)

ContractError = v1.ContractError
extract_features = v1.extract_features
register_to_reference = v1.register_to_reference
CHUNK_BYTES = 1024 * 1024
DENOMINATOR_ERROR = "UNMEASURED_DENOMINATOR_UNDEFINED"
INPUT_ERROR = "UNMEASURED_INPUT_CONTRACT_INVALID"
GRID_ERROR = "UNMEASURED_OUTPUT_GRID_UNDEFINED"
_BINDING_SEAL = object()


def _require(condition: bool, message: str, code: str = DENOMINATOR_ERROR) -> None:
    if not condition:
        raise ContractError(code, message)


def _json_value(value: Any, code: str) -> None:
    """Accept ordinary JSON values only; no objects with conversion hooks."""
    if type(value) is dict:
        _require(all(type(k) is str for k in value), "non-string object key", code)
        for child in value.values():
            _json_value(child, code)
    elif type(value) is list:
        for child in value:
            _json_value(child, code)
    else:
        _require(type(value) in (str, int, bool, type(None)),
                 "noncanonical JSON value (floats are not admitted)", code)


def _canonical(value: Any, code: str = DENOMINATOR_ERROR) -> bytes:
    _json_value(value, code)
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def strict_json_loads(text: str | bytes) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            _require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise ContractError(DENOMINATOR_ERROR, f"nonfinite JSON number: {value}")

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, TypeError, UnicodeError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError(DENOMINATOR_ERROR, f"invalid JSON: {exc}") from exc
    _require(type(value) is dict, "expected a JSON object")
    _json_value(value, DENOMINATOR_ERROR)
    return value


@dataclass(frozen=True, init=False, slots=True)
class TrustedInputBinding:
    """Minted only by construct_overlap_paths after input registration succeeds.

    No public constructor imports authority from a candidate digest/manifest.
    Treat this object as trusted runner state; never deserialize candidate data
    into it. Arbitrary code in this process can defeat any Python capability.
    """
    _manifest_bytes: bytes
    _seal: object

    def __init__(self) -> None:
        raise TypeError("TrustedInputBinding is created by construct_overlap_paths")

    @property
    def manifest_sha256(self) -> str:
        return json.loads(self._manifest_bytes)["manifest_sha256"]

    @property
    def input_bundle_sha256(self) -> str:
        return json.loads(self._manifest_bytes)["input_bundle_sha256"]


@dataclass(frozen=True)
class _InputFile:
    path: Path
    digest: bytes
    length: int


def _scan(path: Path) -> _InputFile:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as stream:
        while block := stream.read(CHUNK_BYTES):
            digest.update(block)
            length += len(block)
    _require(0 < length < 1 << 64, "input byte length is invalid", INPUT_ERROR)
    return _InputFile(path, digest.digest(), length)


def _copy_checked(item: _InputFile, sink: Any) -> None:
    digest = hashlib.sha256()
    length = 0
    with item.path.open("rb") as stream:
        while block := stream.read(CHUNK_BYTES):
            digest.update(block)
            sink(block)
            length += len(block)
    _require(length == item.length and digest.digest() == item.digest,
             f"input changed during construction: {item.path}", INPUT_ERROR)


def _compare_files(left: _InputFile, right: _InputFile) -> int:
    first = (left.digest, left.length)
    second = (right.digest, right.length)
    if first != second:
        return -1 if first < second else 1
    # Exact-byte comparison preserves v1 deduplication and its collision tiebreak.
    # Only equal digest+length pairs need this additional bounded streaming read.
    with left.path.open("rb") as a, right.path.open("rb") as b:
        while True:
            aa, bb = a.read(CHUNK_BYTES), b.read(CHUNK_BYTES)
            if aa != bb:
                return -1 if aa < bb else 1
            if not aa:
                return 0


def decode_input_path(path: Path, expected_sha256: str, expected_length: int) -> np.ndarray:
    """Decode exactly one verified file snapshot; never retain all source bytes."""
    item = _InputFile(Path(path), bytes.fromhex(expected_sha256), expected_length)
    # File-backed, not SpooledTemporaryFile: compressed bytes never accumulate in
    # Python memory. The TIFF sees the exact snapshot that passed the rehash.
    with tempfile.TemporaryFile(mode="w+b", dir=HERE) as snapshot:
        _copy_checked(item, snapshot.write)
        snapshot.seek(0)
        try:
            with tifffile.TiffFile(snapshot) as image:
                _require(len(image.pages) == 1, "TIFF must have one page", INPUT_ERROR)
                page = image.pages[0]
                _require(int(page.compression) == 1, "TIFF must be uncompressed", INPUT_ERROR)
                orientation = page.tags.get("Orientation")
                _require(orientation is None or int(orientation.value) == 1,
                         "TIFF orientation must be 1", INPUT_ERROR)
                pixels = page.asarray()
        except ContractError:
            raise
        except Exception as exc:
            raise ContractError(INPUT_ERROR, f"TIFF decode failed: {exc}") from exc
    _require(pixels.ndim == 3 and pixels.shape[2] == 3 and pixels.dtype == np.uint16,
             f"expected HxWx3 uint16, found {pixels.shape} {pixels.dtype}", INPUT_ERROR)
    return np.asarray(pixels)


_REFERENCE_RULE = "minimum (sha256_digest_bytes, byte_length, exact_bytes)"
_SUPPORT_RULE = (
    "active pixel-cell footprint eroded by 0.5 px to the valid-centre domain, "
    "plus held-out max residual rounded up to 1/256 source px and one 1/256-px coordinate quantum"
)
_INTERSECTION_RULE = "exact Q32 inverse-support inequalities at integer reference centres"
_TIE_BREAK = ["maximum area", "minimum y", "minimum x", "maximum height", "maximum width"]
_REFERENCE_REGISTRATION = {
    "reference": True, "heldout_rms_reference_px": "0.000000000",
    "heldout_max_source_px_ceil_q8": 0, "coordinate_quantization_guard_q8": 0,
    "valid_support_continuous_margin_q8": 128,
}


def construct_overlap_paths(paths: Sequence[Path]) -> tuple[dict[str, Any], TrustedInputBinding]:
    """O(N) metadata, O(one decoded frame + two bounded feature sets) image storage.

    Successful manifests use the unchanged v1 schema/ordering. Invalid input
    refusal precedence can differ because decode and registration are streamed.
    """
    _require(len(paths) > 0, "capture has no common-input TIFFs", INPUT_ERROR)
    items = sorted((_scan(Path(path)) for path in paths), key=cmp_to_key(_compare_files))
    bundle = hashlib.sha256(b"M193-INPUT-BUNDLE-V1\x00")
    unique: list[tuple[_InputFile, int]] = []
    for item in items:
        bundle.update(struct.pack(">Q", item.length))
        _copy_checked(item, bundle.update)
        if unique and _compare_files(unique[-1][0], item) == 0:
            unique[-1] = (unique[-1][0], unique[-1][1] + 1)
        else:
            unique.append((item, 1))

    supports = []
    sources = []
    reference_features = None
    for index, (item, multiplicity) in enumerate(unique):
        image = decode_input_path(item.path, item.digest.hex(), item.length)
        if index == 0:
            height, width = image.shape[:2]
            if len(unique) > 1:
                reference_features = extract_features(image)
            transform, registration, guard = v1.IDENTITY_Q32, dict(_REFERENCE_REGISTRATION), 0
        else:
            _require(image.shape[:2] == (height, width),
                     "all common inputs must have identical native dimensions", INPUT_ERROR)
            features = extract_features(image)
            transform, registration, guard = register_to_reference(reference_features, features)
            registration["reference"] = False
            del features
        del image
        supports.append((transform, width, height, guard))
        sources.append({
            "source_sha256": item.digest.hex(), "byte_length": item.length,
            "multiplicity": multiplicity, "reference": index == 0,
            "source_to_reference_q32": transform.as_dict(),
            "valid_center_guard_q8": guard, "registration": registration,
        })
    del reference_features
    manifest = {
        "schema": v1.SCHEMA, "status": "DEFINED_INPUT_ONLY",
        "input_bundle_sha256": bundle.hexdigest(), "input_count": len(items),
        "unique_input_count": len(unique), "reference_rule": _REFERENCE_RULE,
        "reference_source_sha256": unique[0][0].digest.hex(),
        "native_width": width, "native_height": height,
        "valid_support_rule": _SUPPORT_RULE, "intersection_rule": _INTERSECTION_RULE,
        "maximal_rectangle_tie_break": list(_TIE_BREAK), "sources": sources,
        "common_overlap": v1.maximal_rectangle(v1.common_row_intervals(width, height, supports)),
    }
    manifest["manifest_sha256"] = v1.manifest_digest(manifest)
    _validate_manifest_structure(manifest)
    binding = object.__new__(TrustedInputBinding)
    object.__setattr__(binding, "_manifest_bytes", _canonical(manifest))
    object.__setattr__(binding, "_seal", _BINDING_SEAL)
    return manifest, binding


def _keys(value: Any, expected: set[str], label: str, code: str = DENOMINATOR_ERROR) -> None:
    _require(type(value) is dict and set(value) == expected, f"{label} fields missing/unknown", code)


def _integer(value: Any, label: str, minimum: int | None = None, code: str = DENOMINATOR_ERROR) -> int:
    _require(type(value) is int and (minimum is None or value >= minimum),
             f"{label} must be an integer" + (f" >= {minimum}" if minimum is not None else ""), code)
    return value


def _hash(value: Any, label: str, code: str = DENOMINATOR_ERROR) -> None:
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None,
             f"{label} must be a lowercase SHA-256 hex digest", code)


def _transform(value: Any, code: str = DENOMINATOR_ERROR) -> Any:
    _keys(value, {"a", "b", "tx", "ty"}, "Q32 similarity", code)
    for name, integer in value.items():
        _integer(integer, name, code=code)
    transform = v1.SimilarityQ32(**value)
    _require(transform.a * transform.a + transform.b * transform.b > 0,
             "singular Q32 similarity", code)
    return transform


_MANIFEST_KEYS = {
    "schema", "status", "input_bundle_sha256", "input_count", "unique_input_count",
    "reference_rule", "reference_source_sha256", "native_width", "native_height",
    "valid_support_rule", "intersection_rule", "maximal_rectangle_tie_break",
    "sources", "common_overlap", "manifest_sha256",
}
_SOURCE_KEYS = {"source_sha256", "byte_length", "multiplicity", "reference",
                "source_to_reference_q32", "valid_center_guard_q8", "registration"}
_COUNT_KEYS = {"mutual_match_count", "calibration_count", "calibration_inlier_count",
               "holdout_count", "holdout_inlier_count"}


def _validate_manifest_structure(manifest: dict[str, Any]) -> None:
    _keys(manifest, _MANIFEST_KEYS, "overlap manifest")
    _canonical(manifest)
    _require(manifest["schema"] == v1.SCHEMA and manifest["status"] == "DEFINED_INPUT_ONLY",
             "unknown overlap schema or status")
    _require(manifest["reference_rule"] == _REFERENCE_RULE
             and manifest["valid_support_rule"] == _SUPPORT_RULE
             and manifest["intersection_rule"] == _INTERSECTION_RULE
             and manifest["maximal_rectangle_tie_break"] == _TIE_BREAK,
             "overlap construction rules differ from v1")
    for name in ("manifest_sha256", "input_bundle_sha256", "reference_source_sha256"):
        _hash(manifest[name], name)
    _require(v1.manifest_digest(manifest) == manifest["manifest_sha256"], "manifest self-hash is stale")
    width = _integer(manifest["native_width"], "native_width", 1)
    height = _integer(manifest["native_height"], "native_height", 1)
    total = _integer(manifest["input_count"], "input_count", 1)
    count = _integer(manifest["unique_input_count"], "unique_input_count", 1)
    sources = manifest["sources"]
    _require(type(sources) is list and len(sources) == count <= total, "source count mismatch")
    supports = []
    seen_total = 0
    order = []
    for index, source in enumerate(sources):
        _keys(source, _SOURCE_KEYS, "source")
        _hash(source["source_sha256"], "source_sha256")
        length = _integer(source["byte_length"], "byte_length", 1)
        _require(length < 1 << 64, "source byte length exceeds bundle encoding")
        seen_total += _integer(source["multiplicity"], "multiplicity", 1)
        order.append((source["source_sha256"], length))
        reference = index == 0
        _require(source["reference"] is reference, "reference must be first and unique")
        transform = _transform(source["source_to_reference_q32"])
        guard = _integer(source["valid_center_guard_q8"], "valid_center_guard_q8", 0)
        _require(2 * guard <= (min(width, height) - 1) * 256, "guard consumes source support")
        registration = source["registration"]
        keys = set(_REFERENCE_REGISTRATION) | (set() if reference else _COUNT_KEYS)
        _keys(registration, keys, "registration")
        _require(registration["reference"] is reference, "registration reference mismatch")
        maximum = _integer(registration["heldout_max_source_px_ceil_q8"], "heldout maximum", 0)
        quantum = _integer(registration["coordinate_quantization_guard_q8"], "coordinate quantum", 0)
        margin = _integer(registration["valid_support_continuous_margin_q8"], "continuous margin", 0)
        rms = registration["heldout_rms_reference_px"]
        _require(type(rms) is str and re.fullmatch(r"(?:0\.\d{9}|1\.000000000)", rms) is not None,
                 "heldout RMS must be fixed-nine-decimal and within the v1 bar")
        if reference:
            _require(transform == v1.IDENTITY_Q32 and guard == 0
                     and registration == _REFERENCE_REGISTRATION,
                     "reference geometry/uncertainty is not identity")
        else:
            counts = {name: _integer(registration[name], name, 0) for name in _COUNT_KEYS}
            matches, calibration, holdout = (counts["mutual_match_count"], counts["calibration_count"], counts["holdout_count"])
            _require(24 <= matches <= v1.MAX_MATCHES and calibration == (matches + 1) // 2
                     and holdout == matches // 2, "registration split is inconsistent")
            for prefix, population in (("calibration", calibration), ("holdout", holdout)):
                inliers = counts[prefix + "_inlier_count"]
                _require(12 <= inliers <= population and 2 * inliers >= population,
                         "registration lacks admitted consensus")
            _require(quantum == 1 and guard == maximum + quantum and margin == 128 + guard,
                     "registration uncertainty does not determine support guard")
            # Rounded RMS cannot exceed the source maximum converted to the
            # reference gauge. Half a printed decimal unit allows v1 rounding.
            rms_units = int(rms.replace(".", ""))
            lower_twice = max(0, 2 * rms_units - 1)
            determinant = transform.a ** 2 + transform.b ** 2
            _require(lower_twice ** 2 * (256 * v1.Q32) ** 2
                     <= 4 * 10 ** 18 * maximum ** 2 * determinant,
                     "RMS exceeds the source maximum after gauge conversion")
        supports.append((transform, width, height, guard))
    _require(seen_total == total and order == sorted(order), "input multiplicity/order mismatch")
    _require(sources[0]["source_sha256"] == manifest["reference_source_sha256"], "reference hash mismatch")
    rectangle = manifest["common_overlap"]
    _keys(rectangle, {"x", "y", "width", "height", "area_pixels"}, "common overlap")
    for name in ("x", "y", "width", "height", "area_pixels"):
        _integer(rectangle[name], name, 0 if name in ("x", "y") else 1)
    _require(rectangle["x"] + rectangle["width"] <= width
             and rectangle["y"] + rectangle["height"] <= height
             and rectangle["area_pixels"] == rectangle["width"] * rectangle["height"],
             "common overlap bounds/area are inconsistent")
    replay = v1.maximal_rectangle(v1.common_row_intervals(width, height, supports))
    _require(rectangle == replay, "common overlap differs from maximal input-support rectangle")


def validate_overlap(manifest: dict[str, Any], binding: TrustedInputBinding) -> dict[str, Any]:
    """Validate external binding before expensive geometry; return private snapshot."""
    _require(type(binding) is TrustedInputBinding and getattr(binding, "_seal", None) is _BINDING_SEAL,
             "trusted input binding is absent")
    candidate = _canonical(manifest)
    _require(candidate == binding._manifest_bytes, "manifest differs from trusted input registration")
    snapshot = strict_json_loads(candidate)
    _validate_manifest_structure(snapshot)
    return snapshot


def _validate_grid(descriptor: dict[str, Any], overlap: dict[str, Any]) -> Any:
    _keys(descriptor, v1.OUTPUT_GRID_KEYS, "output grid", GRID_ERROR)
    _canonical(descriptor, GRID_ERROR)
    for name in ("schema", "arm_id", "derivation_kind"):
        _require(type(descriptor[name]) is str and bool(descriptor[name]),
                 f"{name} must be a nonempty string", GRID_ERROR)
    for name in ("overlap_manifest_sha256", "input_bundle_sha256", "adapter_sha256", "settings_sha256"):
        _hash(descriptor[name], name, GRID_ERROR)
    for name in ("expected_width", "expected_height", "valid_center_guard_q8",
                 "input_only_landmark_residual_micropixel_ceil"):
        _integer(descriptor[name], name, 1 if name.startswith("expected_") else 0, GRID_ERROR)
    _transform(descriptor["common_to_output_q32"], GRID_ERROR)
    guard = descriptor["valid_center_guard_q8"]
    _require(2 * guard <= (min(descriptor["expected_width"], descriptor["expected_height"]) - 1) * 256,
             "guard consumes declared output grid", GRID_ERROR)
    return v1.validate_output_grid(descriptor, overlap)


def validate_output_grid(descriptor: dict[str, Any], manifest: dict[str, Any],
                         binding: TrustedInputBinding) -> Any:
    overlap = validate_overlap(manifest, binding)
    snapshot = strict_json_loads(_canonical(descriptor, GRID_ERROR))
    return _validate_grid(snapshot, overlap)


def output_retention(manifest: dict[str, Any], descriptor: dict[str, Any],
                     binding: TrustedInputBinding) -> dict[str, Any]:
    overlap = validate_overlap(manifest, binding)
    snapshot = strict_json_loads(_canonical(descriptor, GRID_ERROR))
    _validate_grid(snapshot, overlap)
    # v1 gets only detached, fully validated snapshots. Candidate mutation after
    # validation cannot change the denominator or mapping used for counting.
    return v1.output_retention(overlap, snapshot)
