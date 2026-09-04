#!/usr/bin/env python3
"""Fail-closed consumer-boundary evidence gate for M165 common TIFFs.

The gate intentionally separates three independently computed statements:

* the converter manifest's hashes;
* the consumer-side receipt producer's hashes; and
* this gate's hashes.

Every JSON artifact and TIFF is read into memory at most once per invocation.
TIFF parsing and both hashes operate on that same immutable byte string.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from typing import Any, Iterable


CAMPAIGN_SCHEMA = "m165-common-input-campaign-v1"
CONSUMER_REGISTRY_SCHEMA = "m165-common-input-consumer-registry-v1"
INPUT_MANIFEST_SCHEMA = "m165-common-input-manifest-v3"
RECEIPT_SCHEMA = "m165-common-input-consumer-boundary-receipt-v1"
GATE_SCHEMA = "m165-common-input-consumer-gate-v1"
FREEZE_SCHEMA = "m165-common-input-consumer-gate-freeze-v1"
STANDARD_ATTESTATION_SCHEMA = "m165-consumer-input-attestation-v1"
STREHL_ATTESTATION_SCHEMA = "m165-strehl-common-input-identity-v1"

HASH_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

TIFF_TAGS = {
    "width": 256,
    "height": 257,
    "bits": 258,
    "compression": 259,
    "photometric": 262,
    "description": 270,
    "strip_offsets": 273,
    "samples_per_pixel": 277,
    "rows_per_strip": 278,
    "strip_byte_counts": 279,
    "planar": 284,
    "sample_format": 339,
    "icc": 34675,
}
TIFF_ALLOWED_TAGS = frozenset(TIFF_TAGS.values())
TIFF_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 7: 1}

PAIR_OUTCOMES = ("PASS", "FAIL", "MISSING", "BLOCKED", "OPTIONAL_ABSENT")
INPUT_OUTCOMES = ("PASS", "FAIL", "MISSING", "BLOCKED")


class GateFailure(RuntimeError):
    def __init__(self, failure_class: str, message: str):
        super().__init__(message)
        self.failure_class = failure_class


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def hash_bytes(value: bytes | bytearray | memoryview) -> str:
    return hashlib.sha256(value).hexdigest()


def check_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
        raise GateFailure("HASH_INVALID", f"{label} must be lowercase SHA-256")
    return value


def check_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or ID_RE.fullmatch(value) is None:
        raise GateFailure(
            "IDENTIFIER_INVALID",
            f"{label} must match {ID_RE.pattern!r}",
        )
    return value


def require(condition: bool, failure_class: str, message: str) -> None:
    if not condition:
        raise GateFailure(failure_class, message)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


@dataclass(frozen=True)
class Artifact:
    path: Path
    data: bytes
    sha256: str


class ArtifactCache:
    """One-read cache used by the complete verification invocation."""

    def __init__(self) -> None:
        self._artifacts: dict[Path, Artifact] = {}
        self._read_counts: Counter[str] = Counter()

    def read(self, path: Path, label: str) -> Artifact:
        resolved = path.resolve()
        if resolved in self._artifacts:
            return self._artifacts[resolved]
        try:
            data = resolved.read_bytes()
        except OSError as exc:
            raise GateFailure(
                "ARTIFACT_READ_FAILED", f"cannot read {label} {resolved}: {exc}"
            ) from exc
        artifact = Artifact(resolved, data, hash_bytes(data))
        self._artifacts[resolved] = artifact
        self._read_counts[str(resolved)] += 1
        return artifact

    def read_json(self, path: Path, label: str) -> tuple[Artifact, dict[str, Any]]:
        artifact = self.read(path, label)
        try:
            value = json.loads(artifact.data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GateFailure(
                "JSON_INVALID", f"{label} {artifact.path} is not valid UTF-8 JSON: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise GateFailure("JSON_INVALID", f"{label} must be a JSON object")
        return artifact, value

    def audit(self) -> dict[str, Any]:
        counts = dict(sorted(self._read_counts.items()))
        return {
            "unique_artifacts_read": len(counts),
            "maximum_reads_per_artifact": max(counts.values(), default=0),
            "all_artifacts_read_at_most_once": all(value == 1 for value in counts.values()),
            "read_counts": counts,
        }


def resolve_artifact(owner: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise GateFailure("PATH_INVALID", f"{label} must be a non-empty path")
    path = Path(value)
    if not path.is_absolute():
        path = owner.parent / path
    return path.resolve()


def _require_range(data: bytes, offset: int, length: int, label: str) -> None:
    if offset < 0 or length < 0 or offset > len(data) or length > len(data) - offset:
        raise GateFailure(
            "TIFF_RANGE_INVALID",
            f"{label} [{offset},{offset + length}) exceeds {len(data)} bytes",
        )


def _u16(data: bytes, offset: int, label: str) -> int:
    _require_range(data, offset, 2, label)
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int, label: str) -> int:
    _require_range(data, offset, 4, label)
    return struct.unpack_from("<I", data, offset)[0]


@dataclass(frozen=True)
class TiffEntry:
    tag: int
    kind: int
    count: int
    value_or_offset: bytes


def _entry_data(data: bytes, entry: TiffEntry) -> bytes:
    unit = TIFF_TYPE_SIZES.get(entry.kind)
    if unit is None:
        raise GateFailure(
            "TIFF_TYPE_REJECTED",
            f"tag {entry.tag} uses unsupported TIFF type {entry.kind}",
        )
    total = unit * entry.count
    if total <= 4:
        return entry.value_or_offset[:total]
    offset = struct.unpack("<I", entry.value_or_offset)[0]
    _require_range(data, offset, total, f"tag {entry.tag}")
    return data[offset : offset + total]


def _numeric_values(data: bytes, entry: TiffEntry) -> list[int]:
    raw = _entry_data(data, entry)
    if entry.kind == 3:
        return list(struct.unpack("<" + "H" * entry.count, raw))
    if entry.kind == 4:
        return list(struct.unpack("<" + "I" * entry.count, raw))
    raise GateFailure(
        "TIFF_TYPE_REJECTED",
        f"tag {entry.tag} is not a SHORT or LONG numeric field",
    )


def _scalar(data: bytes, entry: TiffEntry, label: str) -> int:
    values = _numeric_values(data, entry)
    if len(values) != 1:
        raise GateFailure("TIFF_FIELD_INVALID", f"{label} must contain one value")
    return values[0]


def inspect_tiff_bytes(data: bytes) -> dict[str, Any]:
    """Hash and parse one immutable TIFF byte string."""

    require(
        len(data) >= 8 and data[:2] == b"II" and _u16(data, 2, "TIFF magic") == 42,
        "TIFF_HEADER_REJECTED",
        "input is not a little-endian classic TIFF",
    )
    ifd = _u32(data, 4, "IFD offset")
    count = _u16(data, ifd, "IFD entry count")
    table_start = ifd + 2
    _require_range(data, table_start, count * 12 + 4, "IFD table")
    require(
        _u32(data, table_start + count * 12, "next IFD") == 0,
        "TIFF_MULTI_IMAGE_REJECTED",
        "multi-image TIFF is forbidden",
    )

    entries: dict[int, TiffEntry] = {}
    for index in range(count):
        at = table_start + index * 12
        entry = TiffEntry(
            tag=_u16(data, at, "IFD tag"),
            kind=_u16(data, at + 2, "IFD type"),
            count=_u32(data, at + 4, "IFD count"),
            value_or_offset=data[at + 8 : at + 12],
        )
        require(
            entry.tag in TIFF_ALLOWED_TAGS,
            "TIFF_TAG_REJECTED",
            f"TIFF tag {entry.tag} is outside the common-input allowlist",
        )
        require(
            entry.tag not in entries,
            "TIFF_TAG_DUPLICATE",
            f"duplicate TIFF tag {entry.tag}",
        )
        entries[entry.tag] = entry

    missing = sorted(TIFF_ALLOWED_TAGS.difference(entries))
    require(not missing, "TIFF_TAG_MISSING", f"required TIFF tags are absent: {missing}")

    def entry(name: str) -> TiffEntry:
        return entries[TIFF_TAGS[name]]

    width = _scalar(data, entry("width"), "ImageWidth")
    height = _scalar(data, entry("height"), "ImageLength")
    require(width > 0 and height > 0, "TIFF_DIMENSIONS_INVALID", "zero TIFF dimension")
    require(
        _numeric_values(data, entry("bits")) == [16, 16, 16],
        "TIFF_BITS_INVALID",
        "BitsPerSample must be [16,16,16]",
    )
    require(
        _scalar(data, entry("compression"), "Compression") == 1,
        "TIFF_COMPRESSION_INVALID",
        "Compression must be 1",
    )
    require(
        _scalar(data, entry("photometric"), "PhotometricInterpretation") == 2,
        "TIFF_PHOTOMETRIC_INVALID",
        "PhotometricInterpretation must be RGB",
    )
    require(
        _scalar(data, entry("samples_per_pixel"), "SamplesPerPixel") == 3,
        "TIFF_SAMPLES_INVALID",
        "SamplesPerPixel must be 3",
    )
    require(
        _scalar(data, entry("planar"), "PlanarConfiguration") == 1,
        "TIFF_PLANAR_INVALID",
        "PlanarConfiguration must be contiguous",
    )
    require(
        _numeric_values(data, entry("sample_format")) == [1, 1, 1],
        "TIFF_SAMPLE_FORMAT_INVALID",
        "SampleFormat must be unsigned integer [1,1,1]",
    )

    rows_per_strip = _scalar(data, entry("rows_per_strip"), "RowsPerStrip")
    require(rows_per_strip > 0, "TIFF_STRIP_INVALID", "RowsPerStrip must be positive")
    offsets = _numeric_values(data, entry("strip_offsets"))
    byte_counts = _numeric_values(data, entry("strip_byte_counts"))
    expected_strips = (height + rows_per_strip - 1) // rows_per_strip
    require(
        len(offsets) == expected_strips and len(byte_counts) == expected_strips,
        "TIFF_STRIP_INVALID",
        f"strip tables have {len(offsets)}/{len(byte_counts)} entries, expected "
        f"{expected_strips}",
    )

    row_bytes = width * 6
    expected_payload = row_bytes * height
    payload_digest = hashlib.sha256()
    payload_bytes = 0
    ranges: list[dict[str, int]] = []
    occupied: list[tuple[int, int]] = []
    for index, (offset, byte_count) in enumerate(zip(offsets, byte_counts, strict=True)):
        first_row = index * rows_per_strip
        rows = min(rows_per_strip, height - first_row)
        expected_count = rows * row_bytes
        require(
            byte_count == expected_count,
            "TIFF_STRIP_INVALID",
            f"strip {index} has {byte_count} bytes, expected {expected_count}",
        )
        _require_range(data, offset, byte_count, f"pixel strip {index}")
        start, end = offset, offset + byte_count
        for prior_start, prior_end in occupied:
            require(
                end <= prior_start or start >= prior_end,
                "TIFF_STRIP_OVERLAP",
                f"pixel strip {index} overlaps [{prior_start},{prior_end})",
            )
        occupied.append((start, end))
        payload_digest.update(data[start:end])
        payload_bytes += byte_count
        ranges.append({"start": start, "end_exclusive": end})
    require(
        payload_bytes == expected_payload,
        "TIFF_PAYLOAD_SIZE_INVALID",
        f"pixel payload has {payload_bytes} bytes, expected {expected_payload}",
    )

    description_entry = entry("description")
    require(
        description_entry.kind == 2,
        "TIFF_PROVENANCE_INVALID",
        "ImageDescription must be TIFF ASCII",
    )
    description = _entry_data(data, description_entry)
    require(
        description.endswith(b"\0"),
        "TIFF_PROVENANCE_INVALID",
        "ImageDescription must be NUL terminated",
    )
    try:
        provenance = json.loads(description[:-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateFailure(
            "TIFF_PROVENANCE_INVALID", f"ImageDescription is not UTF-8 JSON: {exc}"
        ) from exc
    require(
        isinstance(provenance, dict),
        "TIFF_PROVENANCE_INVALID",
        "ImageDescription provenance must be an object",
    )

    icc_entry = entry("icc")
    require(
        icc_entry.kind in {1, 7},
        "TIFF_ICC_INVALID",
        "ICC tag must use BYTE or UNDEFINED",
    )
    icc = _entry_data(data, icc_entry)
    require(
        len(icc) >= 128 and icc[36:40] == b"acsp",
        "TIFF_ICC_INVALID",
        "embedded ICC profile is absent or malformed",
    )

    return {
        "width": width,
        "height": height,
        "file_bytes": len(data),
        "file_sha256": hash_bytes(data),
        "whole_file_hash": {
            "algorithm": "sha256",
            "ranges": [{"start": 0, "end_exclusive": len(data)}],
        },
        "pixel_payload_bytes": payload_bytes,
        "pixel_payload_sha256": payload_digest.hexdigest(),
        "pixel_payload_hash": {
            "algorithm": "sha256-concatenated-ranges-in-listed-order",
            "ranges": ranges,
        },
        "icc_sha256": hash_bytes(icc),
        "provenance": provenance,
        "parse_contract": {
            "artifact_read_count": 1,
            "hash_and_parse_same_memory": True,
        },
    }


def build_freeze() -> dict[str, Any]:
    script = Path(__file__).resolve()
    python = Path(sys.executable).resolve()
    script_bytes = script.read_bytes()
    python_bytes = python.read_bytes()
    members = {
        "consumer_gate_script_sha256": hash_bytes(script_bytes),
        "python_executable_sha256": hash_bytes(python_bytes),
        "python_version": sys.version,
        "schemas": {
            "campaign": CAMPAIGN_SCHEMA,
            "registry": CONSUMER_REGISTRY_SCHEMA,
            "receipt": RECEIPT_SCHEMA,
            "gate": GATE_SCHEMA,
        },
    }
    return {
        "schema": FREEZE_SCHEMA,
        "status": "FROZEN",
        "consumer_gate_bundle_sha256": hash_bytes(canonical_json(members)),
        "bundle_members": members,
        "artifacts": {
            "consumer_gate_script": {
                "path": str(script),
                "bytes": len(script_bytes),
                "sha256": members["consumer_gate_script_sha256"],
            },
            "python_executable": {
                "path": str(python),
                "bytes": len(python_bytes),
                "sha256": members["python_executable_sha256"],
            },
        },
    }


def verify_freeze(cache: ArtifactCache, path: Path) -> tuple[Artifact, dict[str, Any]]:
    artifact, freeze = cache.read_json(path, "consumer gate freeze")
    require(
        freeze.get("schema") == FREEZE_SCHEMA and freeze.get("status") == "FROZEN",
        "GATE_FREEZE_INVALID",
        "consumer gate freeze is absent or not FROZEN",
    )
    script_artifact = cache.read(Path(__file__).resolve(), "consumer gate script")
    python_artifact = cache.read(Path(sys.executable).resolve(), "Python executable")
    members = {
        "consumer_gate_script_sha256": script_artifact.sha256,
        "python_executable_sha256": python_artifact.sha256,
        "python_version": sys.version,
        "schemas": {
            "campaign": CAMPAIGN_SCHEMA,
            "registry": CONSUMER_REGISTRY_SCHEMA,
            "receipt": RECEIPT_SCHEMA,
            "gate": GATE_SCHEMA,
        },
    }
    actual_bundle = hash_bytes(canonical_json(members))
    expected_bundle = check_hash(
        freeze.get("consumer_gate_bundle_sha256"), "consumer gate bundle"
    )
    require(
        actual_bundle == expected_bundle and freeze.get("bundle_members") == members,
        "GATE_FREEZE_MISMATCH",
        f"current gate bundle {actual_bundle} differs from frozen {expected_bundle}",
    )
    return artifact, freeze


def _bundle_member(
    cache: ArtifactCache, registry_path: Path, member: Any, consumer_id: str
) -> dict[str, Any]:
    require(
        isinstance(member, dict),
        "CONSUMER_BUNDLE_INVALID",
        f"{consumer_id}: bundle member must be an object",
    )
    label = check_id(member.get("label"), f"{consumer_id} bundle label")
    path = resolve_artifact(
        registry_path, member.get("path"), f"{consumer_id} bundle member {label}"
    )
    artifact = cache.read(path, f"{consumer_id} bundle member {label}")
    expected_sha = check_hash(member.get("sha256"), f"{consumer_id} bundle member {label}")
    require(
        artifact.sha256 == expected_sha,
        "CONSUMER_BUNDLE_HASH_MISMATCH",
        f"{consumer_id}: {label} hash is {artifact.sha256}, expected {expected_sha}",
    )
    require(
        member.get("bytes") == len(artifact.data),
        "CONSUMER_BUNDLE_SIZE_MISMATCH",
        f"{consumer_id}: {label} byte count differs",
    )
    return {
        "label": label,
        "path": str(path),
        "bytes": len(artifact.data),
        "sha256": artifact.sha256,
    }


def validate_registry(
    cache: ArtifactCache, path: Path
) -> tuple[Artifact, dict[str, Any], list[dict[str, Any]]]:
    artifact, registry = cache.read_json(path, "consumer registry")
    require(
        registry.get("schema") == CONSUMER_REGISTRY_SCHEMA,
        "CONSUMER_REGISTRY_SCHEMA_MISMATCH",
        f"consumer registry schema must be {CONSUMER_REGISTRY_SCHEMA}",
    )
    require(
        registry.get("status") in {"FROZEN", "BLOCKED"},
        "CONSUMER_REGISTRY_STATUS_INVALID",
        "consumer registry status must be FROZEN or BLOCKED",
    )
    require(
        registry.get("track") == "common-merge",
        "CONSUMER_REGISTRY_TRACK_MISMATCH",
        "consumer registry must name the common-merge track",
    )
    check_id(registry.get("registry_id"), "registry_id")
    require(
        isinstance(registry.get("version"), str) and registry["version"],
        "CONSUMER_REGISTRY_INVALID",
        "registry version must be a non-empty string",
    )
    consumers = registry.get("consumers")
    require(
        isinstance(consumers, list) and consumers,
        "CONSUMER_REGISTRY_EMPTY",
        "consumer registry must contain consumers",
    )

    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, consumer in enumerate(consumers):
        require(
            isinstance(consumer, dict),
            "CONSUMER_REGISTRY_INVALID",
            f"consumer {index} is not an object",
        )
        consumer_id = check_id(consumer.get("consumer_id"), f"consumer {index} id")
        require(
            consumer_id not in seen,
            "CONSUMER_REGISTRY_DUPLICATE",
            f"duplicate consumer_id {consumer_id}",
        )
        seen.add(consumer_id)
        required = consumer.get("required")
        require(
            isinstance(required, bool),
            "CONSUMER_REGISTRY_INVALID",
            f"{consumer_id}: required must be boolean",
        )
        role = consumer.get("role")
        require(
            isinstance(role, str) and role,
            "CONSUMER_REGISTRY_INVALID",
            f"{consumer_id}: role is absent",
        )
        status = consumer.get("status")
        if status != "FROZEN":
            blocker = consumer.get("blocker")
            require(
                isinstance(blocker, str) and blocker,
                "CONSUMER_BLOCKER_ABSENT",
                f"{consumer_id}: non-frozen consumer needs a precise blocker",
            )
            normalized.append(
                {
                    "consumer_id": consumer_id,
                    "role": role,
                    "required": required,
                    "status": status,
                    "blocker": blocker,
                    "attestation_schemas": consumer.get("attestation_schemas", []),
                }
            )
            continue

        executable = resolve_artifact(
            path, consumer.get("executable_path"), f"{consumer_id} executable"
        )
        executable_artifact = cache.read(executable, f"{consumer_id} executable")
        executable_sha = check_hash(
            consumer.get("executable_sha256"), f"{consumer_id} executable"
        )
        require(
            executable_artifact.sha256 == executable_sha,
            "CONSUMER_EXECUTABLE_HASH_MISMATCH",
            f"{consumer_id}: executable hash is {executable_artifact.sha256}, "
            f"expected {executable_sha}",
        )
        require(
            consumer.get("executable_bytes") == len(executable_artifact.data),
            "CONSUMER_EXECUTABLE_SIZE_MISMATCH",
            f"{consumer_id}: executable byte count differs",
        )

        bundle = consumer.get("executable_bundle")
        require(
            isinstance(bundle, list) and bundle,
            "CONSUMER_BUNDLE_REQUIRED",
            f"{consumer_id}: executable_bundle must enumerate every runtime artifact",
        )
        members = [_bundle_member(cache, path, item, consumer_id) for item in bundle]
        labels = [item["label"] for item in members]
        require(
            len(labels) == len(set(labels)),
            "CONSUMER_BUNDLE_INVALID",
            f"{consumer_id}: duplicate executable bundle label",
        )
        portable_members = [
            {"label": item["label"], "bytes": item["bytes"], "sha256": item["sha256"]}
            for item in members
        ]
        bundle_sha = hash_bytes(canonical_json(portable_members))
        expected_bundle_sha = check_hash(
            consumer.get("executable_bundle_sha256"),
            f"{consumer_id} executable bundle",
        )
        require(
            bundle_sha == expected_bundle_sha,
            "CONSUMER_BUNDLE_HASH_MISMATCH",
            f"{consumer_id}: executable bundle hash is {bundle_sha}, "
            f"expected {expected_bundle_sha}",
        )

        settings = consumer.get("settings")
        require(
            isinstance(settings, dict),
            "CONSUMER_SETTINGS_INVALID",
            f"{consumer_id}: settings must be an object",
        )
        settings_sha = hash_bytes(canonical_json(settings))
        require(
            settings_sha
            == check_hash(consumer.get("settings_sha256"), f"{consumer_id} settings"),
            "CONSUMER_SETTINGS_HASH_MISMATCH",
            f"{consumer_id}: settings hash differs",
        )
        invocation = consumer.get("invocation_template")
        require(
            isinstance(invocation, list)
            and invocation
            and all(isinstance(value, str) for value in invocation)
            and any("{input_tiff}" in value for value in invocation),
            "CONSUMER_INVOCATION_INVALID",
            f"{consumer_id}: invocation_template must contain {{input_tiff}}",
        )
        expected_input_contract = {
            "kind": "exact-common-tiff-bytes",
            "file_sha256_from": "input_manifest.output.file_sha256",
            "pixel_sha256_from": "input_manifest.output.pixel_payload_sha256",
        }
        require(
            consumer.get("input_contract") == expected_input_contract,
            "CONSUMER_INPUT_CONTRACT_MISMATCH",
            f"{consumer_id}: input contract differs from the exact-byte contract",
        )
        schemas = consumer.get("attestation_schemas")
        require(
            isinstance(schemas, list)
            and schemas
            and all(isinstance(value, str) and value for value in schemas),
            "CONSUMER_ATTESTATION_SCHEMA_INVALID",
            f"{consumer_id}: attestation_schemas must be non-empty",
        )
        normalized.append(
            {
                "consumer_id": consumer_id,
                "role": role,
                "required": required,
                "status": "FROZEN",
                "version": consumer.get("version"),
                "implementation_kind": consumer.get("implementation_kind"),
                "executable_path": str(executable),
                "executable_bytes": len(executable_artifact.data),
                "executable_sha256": executable_sha,
                "executable_bundle": members,
                "executable_bundle_sha256": bundle_sha,
                "settings": settings,
                "settings_sha256": settings_sha,
                "invocation_template": invocation,
                "input_contract": expected_input_contract,
                "attestation_schemas": schemas,
            }
        )

    required_consumers = [value for value in normalized if value["required"]]
    require(
        required_consumers,
        "CONSUMER_REGISTRY_NO_REQUIRED_CONSUMERS",
        "consumer registry has no required consumers",
    )
    all_required_frozen = all(value["status"] == "FROZEN" for value in required_consumers)
    require(
        (registry["status"] == "FROZEN") == all_required_frozen,
        "CONSUMER_REGISTRY_STATUS_INCONSISTENT",
        "registry status does not match required-consumer readiness",
    )
    return artifact, registry, normalized


def validate_campaign(
    cache: ArtifactCache,
    path: Path,
    freeze: dict[str, Any],
) -> tuple[Artifact, dict[str, Any], list[dict[str, Any]]]:
    artifact, campaign = cache.read_json(path, "consumer campaign")
    require(
        campaign.get("schema") == CAMPAIGN_SCHEMA,
        "CAMPAIGN_SCHEMA_MISMATCH",
        f"campaign schema must be {CAMPAIGN_SCHEMA}",
    )
    require(
        campaign.get("status") == "FROZEN",
        "CAMPAIGN_NOT_FROZEN",
        "consumer campaign must be FROZEN",
    )
    require(
        campaign.get("track") == "common-merge",
        "CAMPAIGN_TRACK_MISMATCH",
        "consumer campaign must name common-merge",
    )
    check_id(campaign.get("campaign_id"), "campaign_id")
    require(
        campaign.get("consumer_gate_bundle_sha256")
        == freeze["consumer_gate_bundle_sha256"],
        "CAMPAIGN_GATE_FREEZE_MISMATCH",
        "campaign does not bind the active consumer gate bundle",
    )
    check_hash(campaign.get("consumer_registry_sha256"), "campaign consumer registry")
    inputs = campaign.get("inputs")
    require(
        isinstance(inputs, list) and inputs,
        "CAMPAIGN_EMPTY",
        "campaign must contain at least one input",
    )
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(inputs):
        require(
            isinstance(item, dict),
            "CAMPAIGN_INPUT_INVALID",
            f"campaign input {index} is not an object",
        )
        input_id = check_id(item.get("input_id"), f"campaign input {index} id")
        require(
            input_id not in seen,
            "CAMPAIGN_INPUT_DUPLICATE",
            f"duplicate input_id {input_id}",
        )
        seen.add(input_id)
        manifest_path = resolve_artifact(
            path, item.get("manifest_path"), f"{input_id} manifest"
        )
        manifest_sha = check_hash(item.get("manifest_sha256"), f"{input_id} manifest")
        normalized.append(
            {
                "input_id": input_id,
                "manifest_path": manifest_path,
                "manifest_sha256": manifest_sha,
            }
        )
    return artifact, campaign, normalized


def validate_input(
    cache: ArtifactCache,
    item: dict[str, Any],
    registry_sha256: str,
) -> dict[str, Any]:
    manifest_artifact, manifest = cache.read_json(
        item["manifest_path"], f"{item['input_id']} input manifest"
    )
    require(
        manifest_artifact.sha256 == item["manifest_sha256"],
        "INPUT_MANIFEST_HASH_MISMATCH",
        f"{item['input_id']}: manifest hash is {manifest_artifact.sha256}, "
        f"expected {item['manifest_sha256']}",
    )
    require(
        manifest.get("schema") == INPUT_MANIFEST_SCHEMA
        and manifest.get("status") == "RENDERED"
        and manifest.get("track") == "common-merge",
        "INPUT_MANIFEST_INVALID",
        f"{item['input_id']}: manifest is not a rendered common-merge v3 input",
    )
    consumer_registry = manifest.get("consumer_registry")
    require(
        isinstance(consumer_registry, dict)
        and consumer_registry.get("sha256") == registry_sha256,
        "INPUT_REGISTRY_MISMATCH",
        f"{item['input_id']}: input manifest does not bind this consumer registry",
    )
    output = manifest.get("output")
    require(
        isinstance(output, dict),
        "INPUT_MANIFEST_INVALID",
        f"{item['input_id']}: output object is absent",
    )
    tiff_path = resolve_artifact(
        item["manifest_path"], output.get("path"), f"{item['input_id']} TIFF"
    )
    tiff_artifact = cache.read(tiff_path, f"{item['input_id']} TIFF")
    snapshot = inspect_tiff_bytes(tiff_artifact.data)
    require(
        snapshot["file_sha256"]
        == check_hash(output.get("file_sha256"), f"{item['input_id']} TIFF file"),
        "INPUT_FILE_HASH_MISMATCH",
        f"{item['input_id']}: TIFF whole-file hash differs from converter manifest",
    )
    require(
        snapshot["pixel_payload_sha256"]
        == check_hash(
            output.get("pixel_payload_sha256"), f"{item['input_id']} TIFF pixels"
        ),
        "INPUT_PIXEL_HASH_MISMATCH",
        f"{item['input_id']}: TIFF pixel hash differs from converter manifest",
    )
    require(
        snapshot["icc_sha256"]
        == check_hash(output.get("icc_sha256"), f"{item['input_id']} TIFF ICC"),
        "INPUT_ICC_HASH_MISMATCH",
        f"{item['input_id']}: TIFF ICC hash differs from converter manifest",
    )
    require(
        output.get("width") == snapshot["width"]
        and output.get("height") == snapshot["height"],
        "INPUT_DIMENSIONS_MISMATCH",
        f"{item['input_id']}: TIFF dimensions differ from converter manifest",
    )

    provenance = snapshot["provenance"]
    source = manifest.get("source")
    converter = manifest.get("converter")
    pattern_map = manifest.get("pattern_map")
    require(
        provenance.get("schema") == "m165-common-input-provenance-v1",
        "INPUT_PROVENANCE_MISMATCH",
        f"{item['input_id']}: TIFF provenance schema differs",
    )
    require(
        isinstance(source, dict),
        "INPUT_PROVENANCE_MISMATCH",
        f"{item['input_id']}: source provenance is absent",
    )
    source_sha = check_hash(source.get("sha256"), f"{item['input_id']} source")
    require(
        isinstance(converter, dict),
        "INPUT_PROVENANCE_MISMATCH",
        f"{item['input_id']}: converter provenance is absent",
    )
    converter_sha = check_hash(
        converter.get("executable_sha256"), f"{item['input_id']} converter"
    )
    settings_sha = check_hash(
        converter.get("settings_sha256"), f"{item['input_id']} converter settings"
    )
    require(
        isinstance(pattern_map, dict),
        "INPUT_PROVENANCE_MISMATCH",
        f"{item['input_id']}: pattern-map provenance is absent",
    )
    map_sha = check_hash(pattern_map.get("sha256"), f"{item['input_id']} pattern map")
    map_manifest_sha = check_hash(
        pattern_map.get("manifest_sha256"),
        f"{item['input_id']} pattern-map manifest",
    )
    require(
        provenance.get("source_sha256") == source_sha,
        "INPUT_PROVENANCE_MISMATCH",
        f"{item['input_id']}: source provenance differs",
    )
    require(
        provenance.get("converter_executable_sha256") == converter_sha
        and provenance.get("settings_sha256") == settings_sha,
        "INPUT_PROVENANCE_MISMATCH",
        f"{item['input_id']}: converter provenance differs",
    )
    require(
        provenance.get("pattern_map_sha256") == map_sha
        and provenance.get("pattern_manifest_sha256") == map_manifest_sha,
        "INPUT_PROVENANCE_MISMATCH",
        f"{item['input_id']}: pattern-map provenance differs",
    )
    require(
        provenance.get("icc_sha256") == snapshot["icc_sha256"],
        "INPUT_PROVENANCE_MISMATCH",
        f"{item['input_id']}: ICC provenance differs",
    )
    return {
        **item,
        "manifest": manifest,
        "manifest_sha256": manifest_artifact.sha256,
        "tiff_path": tiff_path,
        "snapshot": snapshot,
    }


def _attestation_hashes(attestation: dict[str, Any]) -> tuple[str, str]:
    schema = attestation.get("schema")
    if schema == STREHL_ATTESTATION_SCHEMA:
        require(
            attestation.get("status") == "PASS"
            and attestation.get("core_merge_exercised") is True,
            "ATTESTATION_FAILED",
            "Strehl attestation did not pass the real merge-core exercise",
        )
        file_sha = check_hash(attestation.get("file_sha256"), "Strehl input file")
        pixel_sha = check_hash(
            attestation.get("pixel_payload_sha256"), "Strehl input pixels"
        )
        require(
            attestation.get("internal_premerge_sha256") == pixel_sha
            and attestation.get("merge_sample_sha256") == pixel_sha,
            "ATTESTATION_IDENTITY_MISMATCH",
            "Strehl internal or merge-facing samples differ from TIFF pixels",
        )
        return file_sha, pixel_sha
    if schema == STANDARD_ATTESTATION_SCHEMA:
        require(
            attestation.get("status") == "PASS",
            "ATTESTATION_FAILED",
            "consumer attestation status is not PASS",
        )
        read_contract = attestation.get("read_contract")
        require(
            read_contract
            == {
                "artifact_read_count": 1,
                "hash_and_parse_same_memory": True,
            },
            "ATTESTATION_READ_CONTRACT_INVALID",
            "consumer attestation did not hash and parse one in-memory read",
        )
        return (
            check_hash(attestation.get("input_file_sha256"), "attested input file"),
            check_hash(
                attestation.get("input_pixel_payload_sha256"),
                "attested input pixels",
            ),
        )
    raise GateFailure(
        "ATTESTATION_SCHEMA_UNSUPPORTED",
        f"unsupported consumer attestation schema {schema!r}",
    )


def validate_complete_invocation(
    template: list[str],
    complete: list[str],
    consumer: dict[str, Any],
    input_record: dict[str, Any],
    attestation_path: Path,
    output_paths: list[Path],
) -> None:
    require(
        len(template) == len(complete),
        "RECEIPT_INVOCATION_MISMATCH",
        f"complete invocation has {len(complete)} tokens, expected {len(template)}",
    )
    snapshot = input_record["snapshot"]
    provenance = snapshot["provenance"]
    replacements = {
        "consumer_id": consumer["consumer_id"],
        "input_tiff": str(input_record["tiff_path"]),
        "attestation_path": str(attestation_path),
        "output_path": str(output_paths[0]) if output_paths else "",
        "file_sha256": snapshot["file_sha256"],
        "pixel_payload_sha256": snapshot["pixel_payload_sha256"],
        "icc_sha256": snapshot["icc_sha256"],
        "source_sha256": str(provenance.get("source_sha256", "")),
        "converter_sha256": str(
            provenance.get("converter_executable_sha256", "")
        ),
        "settings_sha256": str(provenance.get("settings_sha256", "")),
        "pattern_map_sha256": str(provenance.get("pattern_map_sha256", "")),
        "pattern_manifest_sha256": str(
            provenance.get("pattern_manifest_sha256", "")
        ),
    }
    placeholder = re.compile(r"\{([A-Za-z0-9_]+)\}")
    for index, (expected_token, actual_token) in enumerate(
        zip(template, complete, strict=True)
    ):
        cursor = 0
        parts: list[str] = []
        for match in placeholder.finditer(expected_token):
            parts.append(re.escape(expected_token[cursor : match.start()]))
            name = match.group(1)
            parts.append(
                re.escape(replacements[name]) if name in replacements else r".+"
            )
            cursor = match.end()
        parts.append(re.escape(expected_token[cursor:]))
        pattern = "".join(parts)
        require(
            re.fullmatch(pattern, actual_token) is not None,
            "RECEIPT_INVOCATION_MISMATCH",
            f"invocation token {index} does not match frozen template",
        )


def validate_receipt(
    cache: ArtifactCache,
    receipt_path: Path,
    receipt: dict[str, Any],
    campaign_sha256: str,
    registry_sha256: str,
    freeze: dict[str, Any],
    consumer: dict[str, Any],
    input_record: dict[str, Any],
) -> dict[str, Any]:
    require(
        receipt.get("schema") == RECEIPT_SCHEMA and receipt.get("status") == "PASS",
        "RECEIPT_INVALID",
        "receipt is not a passing consumer-boundary receipt",
    )
    require(
        receipt.get("consumer_gate_bundle_sha256")
        == freeze["consumer_gate_bundle_sha256"],
        "RECEIPT_GATE_FREEZE_MISMATCH",
        "receipt was not produced by the frozen gate bundle",
    )
    require(
        receipt.get("campaign_manifest_sha256") == campaign_sha256,
        "RECEIPT_CAMPAIGN_MISMATCH",
        "receipt campaign hash differs",
    )
    require(
        receipt.get("consumer_registry_sha256") == registry_sha256,
        "RECEIPT_REGISTRY_MISMATCH",
        "receipt registry hash differs",
    )
    require(
        receipt.get("consumer_id") == consumer["consumer_id"],
        "RECEIPT_CONSUMER_MISMATCH",
        "receipt consumer_id differs",
    )
    require(
        receipt.get("consumer_executable_sha256") == consumer["executable_sha256"]
        and receipt.get("consumer_executable_bundle_sha256")
        == consumer["executable_bundle_sha256"]
        and receipt.get("consumer_settings_sha256") == consumer["settings_sha256"],
        "RECEIPT_CONSUMER_IDENTITY_MISMATCH",
        "receipt consumer binary bundle or settings differs",
    )
    require(
        receipt.get("input_id") == input_record["input_id"]
        and receipt.get("input_manifest_sha256") == input_record["manifest_sha256"],
        "RECEIPT_INPUT_MISMATCH",
        "receipt input identity differs",
    )
    snapshot = input_record["snapshot"]
    require(
        receipt.get("input_file_sha256") == snapshot["file_sha256"]
        and receipt.get("input_pixel_payload_sha256")
        == snapshot["pixel_payload_sha256"],
        "RECEIPT_INPUT_HASH_MISMATCH",
        "receipt hashes differ from independently read TIFF bytes",
    )
    require(
        receipt.get("whole_file_hash") == snapshot["whole_file_hash"]
        and receipt.get("pixel_payload_hash") == snapshot["pixel_payload_hash"],
        "RECEIPT_BYTE_RANGE_MISMATCH",
        "receipt hash byte ranges differ from the independently parsed TIFF",
    )
    require(
        receipt.get("read_contract")
        == {
            "artifact_read_count": 1,
            "hash_and_parse_same_memory": True,
        },
        "RECEIPT_READ_CONTRACT_INVALID",
        "receipt did not assert the one-read same-memory contract",
    )
    require(
        receipt.get("exit_code") == 0,
        "RECEIPT_CONSUMER_FAILED",
        "consumer exit code is not zero",
    )
    invocation = receipt.get("complete_invocation")
    require(
        isinstance(invocation, list)
        and invocation
        and all(isinstance(value, str) for value in invocation),
        "RECEIPT_INVOCATION_INVALID",
        "receipt complete_invocation is absent",
    )

    attestation_info = receipt.get("consumer_attestation")
    require(
        isinstance(attestation_info, dict),
        "RECEIPT_ATTESTATION_INVALID",
        "receipt consumer_attestation is absent",
    )
    attestation_path = resolve_artifact(
        receipt_path,
        attestation_info.get("path"),
        f"{consumer['consumer_id']} attestation",
    )
    attestation_artifact, attestation = cache.read_json(
        attestation_path, f"{consumer['consumer_id']} attestation"
    )
    require(
        attestation_artifact.sha256
        == check_hash(attestation_info.get("sha256"), "consumer attestation"),
        "ATTESTATION_HASH_MISMATCH",
        "consumer attestation hash differs",
    )
    require(
        attestation_info.get("schema") == attestation.get("schema"),
        "ATTESTATION_SCHEMA_MISMATCH",
        "receipt and consumer attestation name different schemas",
    )
    require(
        attestation.get("schema") in consumer["attestation_schemas"],
        "ATTESTATION_SCHEMA_UNREGISTERED",
        "consumer attestation schema was not frozen in the registry",
    )
    if attestation.get("schema") == STANDARD_ATTESTATION_SCHEMA:
        require(
            attestation.get("consumer_id") == consumer["consumer_id"],
            "ATTESTATION_CONSUMER_MISMATCH",
            "consumer attestation belongs to a different consumer",
        )
        attested_input_path = resolve_artifact(
            attestation_path,
            attestation.get("input_path"),
            f"{consumer['consumer_id']} attested input",
        )
        require(
            attested_input_path == input_record["tiff_path"],
            "ATTESTATION_INPUT_PATH_MISMATCH",
            "consumer attestation names a different input path",
        )
        require(
            attestation.get("complete_invocation") == invocation,
            "ATTESTATION_INVOCATION_MISMATCH",
            "consumer attestation and receipt name different invocations",
        )
        require(
            attestation.get("exit_code") == 0,
            "ATTESTATION_FAILED",
            "consumer attestation exit code is not zero",
        )
    elif attestation.get("schema") == STREHL_ATTESTATION_SCHEMA:
        attested_input_path = resolve_artifact(
            attestation_path,
            attestation.get("tiff"),
            "Strehl attested input",
        )
        require(
            attested_input_path == input_record["tiff_path"],
            "ATTESTATION_INPUT_PATH_MISMATCH",
            "Strehl attestation names a different input path",
        )
    attested_file, attested_pixels = _attestation_hashes(attestation)
    require(
        attested_file == snapshot["file_sha256"]
        and attested_pixels == snapshot["pixel_payload_sha256"],
        "ATTESTATION_INPUT_HASH_MISMATCH",
        "consumer-side hashes differ from independently read TIFF bytes",
    )

    outputs = receipt.get("outputs")
    require(
        isinstance(outputs, list) and outputs,
        "RECEIPT_OUTPUT_ABSENT",
        "receipt must bind at least one consumer output or report",
    )
    normalized_outputs: list[dict[str, Any]] = []
    normalized_output_paths: list[Path] = []
    for index, output in enumerate(outputs):
        require(
            isinstance(output, dict),
            "RECEIPT_OUTPUT_INVALID",
            f"receipt output {index} is not an object",
        )
        output_path = resolve_artifact(
            receipt_path, output.get("path"), f"consumer output {index}"
        )
        require(
            output_path != input_record["tiff_path"],
            "RECEIPT_OUTPUT_INVALID",
            "consumer output may not alias its input TIFF",
        )
        output_artifact = cache.read(output_path, f"consumer output {index}")
        require(
            output_artifact.sha256
            == check_hash(output.get("sha256"), f"consumer output {index}"),
            "RECEIPT_OUTPUT_HASH_MISMATCH",
            f"consumer output {index} hash differs",
        )
        require(
            output.get("bytes") == len(output_artifact.data),
            "RECEIPT_OUTPUT_SIZE_MISMATCH",
            f"consumer output {index} byte count differs",
        )
        normalized_outputs.append(
            {
                "path": str(output_path),
                "bytes": len(output_artifact.data),
                "sha256": output_artifact.sha256,
            }
        )
        normalized_output_paths.append(output_path)
    if attestation.get("schema") == STANDARD_ATTESTATION_SCHEMA:
        attested_outputs = attestation.get("outputs")
        require(
            isinstance(attested_outputs, list) and attested_outputs,
            "ATTESTATION_OUTPUT_INVALID",
            "consumer attestation must bind at least one output",
        )
        receipt_outputs = {
            (item["path"], item["bytes"], item["sha256"])
            for item in normalized_outputs
        }
        seen_attested_outputs: set[tuple[str, int, str]] = set()
        for index, output in enumerate(attested_outputs):
            require(
                isinstance(output, dict),
                "ATTESTATION_OUTPUT_INVALID",
                f"consumer attestation output {index} is not an object",
            )
            output_path = resolve_artifact(
                attestation_path,
                output.get("path"),
                f"consumer attestation output {index}",
            )
            output_bytes = output.get("bytes")
            require(
                isinstance(output_bytes, int) and output_bytes >= 0,
                "ATTESTATION_OUTPUT_INVALID",
                f"consumer attestation output {index} byte count is invalid",
            )
            output_sha = check_hash(
                output.get("sha256"), f"consumer attestation output {index}"
            )
            identity = (str(output_path), output_bytes, output_sha)
            require(
                identity not in seen_attested_outputs,
                "ATTESTATION_OUTPUT_INVALID",
                f"consumer attestation output {index} is duplicated",
            )
            seen_attested_outputs.add(identity)
            require(
                identity in receipt_outputs,
                "ATTESTATION_OUTPUT_MISMATCH",
                f"consumer attestation output {index} is not bound by the receipt",
            )
    validate_complete_invocation(
        consumer["invocation_template"],
        invocation,
        consumer,
        input_record,
        attestation_path,
        normalized_output_paths,
    )
    return {
        "receipt_path": str(receipt_path.resolve()),
        "attestation_path": str(attestation_path),
        "attestation_schema": attestation.get("schema"),
        "file_sha256": snapshot["file_sha256"],
        "pixel_payload_sha256": snapshot["pixel_payload_sha256"],
        "outputs": normalized_outputs,
    }


def _count_partition(values: Iterable[str], outcomes: tuple[str, ...]) -> dict[str, Any]:
    values_list = list(values)
    counts = {name: values_list.count(name) for name in outcomes}
    return {
        "total_examined": len(values_list),
        "counts": counts,
        "counted_sum": sum(counts.values()),
        "partition_balanced": sum(counts.values()) == len(values_list),
    }


def verify_campaign(
    campaign_path: Path,
    registry_path: Path,
    freeze_path: Path,
    receipts_dir: Path,
) -> dict[str, Any]:
    cache = ArtifactCache()
    freeze_artifact, freeze = verify_freeze(cache, freeze_path)
    campaign_artifact, campaign, input_items = validate_campaign(
        cache, campaign_path, freeze
    )
    registry_artifact, registry, consumers = validate_registry(cache, registry_path)
    require(
        registry_artifact.sha256 == campaign["consumer_registry_sha256"],
        "CAMPAIGN_REGISTRY_HASH_MISMATCH",
        f"registry hash is {registry_artifact.sha256}, expected "
        f"{campaign['consumer_registry_sha256']}",
    )

    input_records: dict[str, dict[str, Any]] = {}
    input_errors: dict[str, dict[str, str]] = {}
    for item in input_items:
        try:
            input_records[item["input_id"]] = validate_input(
                cache, item, registry_artifact.sha256
            )
        except GateFailure as exc:
            input_errors[item["input_id"]] = {
                "failure_class": exc.failure_class,
                "reason": str(exc),
            }
        except BaseException as exc:
            input_errors[item["input_id"]] = {
                "failure_class": "UNEXPECTED_EXCEPTION",
                "reason": str(exc),
            }

    pairs: list[dict[str, Any]] = []
    for item in input_items:
        input_id = item["input_id"]
        for consumer in consumers:
            detail: dict[str, Any] = {
                "input_id": input_id,
                "consumer_id": consumer["consumer_id"],
                "required": consumer["required"],
            }
            if input_id in input_errors:
                detail.update({"outcome": "FAIL", **input_errors[input_id]})
            elif consumer["status"] != "FROZEN":
                detail.update(
                    {
                        "outcome": (
                            "BLOCKED" if consumer["required"] else "OPTIONAL_ABSENT"
                        ),
                        "failure_class": "CONSUMER_NOT_FROZEN",
                        "reason": consumer["blocker"],
                    }
                )
            else:
                receipt_path = (
                    receipts_dir.resolve() / consumer["consumer_id"] / f"{input_id}.json"
                )
                if not receipt_path.is_file():
                    detail.update(
                        {
                            "outcome": "MISSING",
                            "failure_class": "RECEIPT_ABSENT",
                            "reason": f"consumer receipt does not exist: {receipt_path}",
                        }
                    )
                else:
                    try:
                        _, receipt = cache.read_json(
                            receipt_path,
                            f"{consumer['consumer_id']}/{input_id} receipt",
                        )
                        evidence = validate_receipt(
                            cache,
                            receipt_path,
                            receipt,
                            campaign_artifact.sha256,
                            registry_artifact.sha256,
                            freeze,
                            consumer,
                            input_records[input_id],
                        )
                        detail.update({"outcome": "PASS", "evidence": evidence})
                    except GateFailure as exc:
                        detail.update(
                            {
                                "outcome": "FAIL",
                                "failure_class": exc.failure_class,
                                "reason": str(exc),
                            }
                        )
                    except BaseException as exc:
                        detail.update(
                            {
                                "outcome": "FAIL",
                                "failure_class": "UNEXPECTED_EXCEPTION",
                                "reason": str(exc),
                            }
                        )
            pairs.append(detail)

    input_details: list[dict[str, Any]] = []
    for item in input_items:
        required_outcomes = [
            pair["outcome"]
            for pair in pairs
            if pair["input_id"] == item["input_id"] and pair["required"]
        ]
        if "FAIL" in required_outcomes:
            outcome = "FAIL"
        elif "BLOCKED" in required_outcomes:
            outcome = "BLOCKED"
        elif "MISSING" in required_outcomes:
            outcome = "MISSING"
        elif required_outcomes and all(value == "PASS" for value in required_outcomes):
            outcome = "PASS"
        else:
            outcome = "FAIL"
        input_details.append(
            {
                "input_id": item["input_id"],
                "outcome": outcome,
                "required_pair_outcomes": dict(Counter(required_outcomes)),
            }
        )

    required_pairs = [pair for pair in pairs if pair["required"]]
    optional_pairs = [pair for pair in pairs if not pair["required"]]
    input_partition = _count_partition(
        [item["outcome"] for item in input_details], INPUT_OUTCOMES
    )
    required_partition = _count_partition(
        [item["outcome"] for item in required_pairs], PAIR_OUTCOMES
    )
    optional_partition = _count_partition(
        [item["outcome"] for item in optional_pairs], PAIR_OUTCOMES
    )
    all_partition = _count_partition(
        [item["outcome"] for item in pairs], PAIR_OUTCOMES
    )
    reads = cache.audit()
    partitions_balanced = all(
        partition["partition_balanced"]
        for partition in (
            input_partition,
            required_partition,
            optional_partition,
            all_partition,
        )
    )
    passed = (
        input_partition["counts"]["PASS"] == input_partition["total_examined"]
        and partitions_balanced
        and reads["all_artifacts_read_at_most_once"]
    )
    return {
        "schema": GATE_SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "track": "common-merge",
        "hash_contract": {
            "algorithm": "SHA-256",
            "whole_file_bytes": "[0,file_size)",
            "pixel_payload_bytes": (
                "concatenation of TIFF strip byte ranges in scan order"
            ),
            "same_memory_rule": (
                "each artifact is read once; hashes and parsing consume that "
                "same cached byte string"
            ),
        },
        "campaign": {
            "path": str(campaign_artifact.path),
            "sha256": campaign_artifact.sha256,
            "campaign_id": campaign["campaign_id"],
        },
        "consumer_registry": {
            "path": str(registry_artifact.path),
            "sha256": registry_artifact.sha256,
            "status": registry["status"],
            "consumer_count": len(consumers),
            "required_consumer_count": sum(
                1 for consumer in consumers if consumer["required"]
            ),
        },
        "gate_freeze": {
            "path": str(freeze_artifact.path),
            "sha256": freeze_artifact.sha256,
            "bundle_sha256": freeze["consumer_gate_bundle_sha256"],
        },
        "summary": {
            "inputs": input_partition,
            "required_consumer_input_pairs": required_partition,
            "optional_consumer_input_pairs": optional_partition,
            "all_consumer_input_pairs": all_partition,
            "all_partitions_balanced": partitions_balanced,
        },
        "inputs": input_details,
        "pairs": pairs,
        "artifact_read_audit": reads,
    }


def make_receipt(
    campaign_path: Path,
    registry_path: Path,
    freeze_path: Path,
    consumer_id: str,
    input_id: str,
    attestation_path: Path,
    complete_invocation: list[str],
    output_paths: list[Path],
) -> dict[str, Any]:
    cache = ArtifactCache()
    _, freeze = verify_freeze(cache, freeze_path)
    campaign_artifact, campaign, input_items = validate_campaign(
        cache, campaign_path, freeze
    )
    registry_artifact, _, consumers = validate_registry(cache, registry_path)
    require(
        registry_artifact.sha256 == campaign["consumer_registry_sha256"],
        "CAMPAIGN_REGISTRY_HASH_MISMATCH",
        "campaign registry hash differs",
    )
    consumer = next(
        (value for value in consumers if value["consumer_id"] == consumer_id), None
    )
    require(
        consumer is not None and consumer["status"] == "FROZEN",
        "CONSUMER_NOT_FROZEN",
        f"consumer {consumer_id!r} is absent or not frozen",
    )
    item = next((value for value in input_items if value["input_id"] == input_id), None)
    require(item is not None, "CAMPAIGN_INPUT_ABSENT", f"input {input_id!r} is absent")
    input_record = validate_input(cache, item, registry_artifact.sha256)

    attestation_artifact, attestation = cache.read_json(
        attestation_path, f"{consumer_id} attestation"
    )
    require(
        attestation.get("schema") in consumer["attestation_schemas"],
        "ATTESTATION_SCHEMA_UNREGISTERED",
        "attestation schema was not frozen for this consumer",
    )
    attested_file, attested_pixels = _attestation_hashes(attestation)
    snapshot = input_record["snapshot"]
    require(
        attested_file == snapshot["file_sha256"]
        and attested_pixels == snapshot["pixel_payload_sha256"],
        "ATTESTATION_INPUT_HASH_MISMATCH",
        "consumer-side hashes differ from the converter input",
    )
    require(
        complete_invocation
        and all(isinstance(value, str) and value for value in complete_invocation),
        "RECEIPT_INVOCATION_INVALID",
        "complete invocation must be a non-empty string array",
    )
    require(output_paths, "RECEIPT_OUTPUT_ABSENT", "at least one output is required")
    outputs: list[dict[str, Any]] = []
    for index, output_path in enumerate(output_paths):
        output = cache.read(output_path, f"consumer output {index}")
        outputs.append(
            {
                "path": str(output.path),
                "bytes": len(output.data),
                "sha256": output.sha256,
            }
        )
    validate_complete_invocation(
        consumer["invocation_template"],
        complete_invocation,
        consumer,
        input_record,
        attestation_artifact.path,
        [Path(value["path"]) for value in outputs],
    )

    return {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "consumer_gate_bundle_sha256": freeze["consumer_gate_bundle_sha256"],
        "campaign_manifest_sha256": campaign_artifact.sha256,
        "consumer_registry_sha256": registry_artifact.sha256,
        "consumer_id": consumer_id,
        "consumer_executable_sha256": consumer["executable_sha256"],
        "consumer_executable_bundle_sha256": consumer[
            "executable_bundle_sha256"
        ],
        "consumer_settings_sha256": consumer["settings_sha256"],
        "input_id": input_id,
        "input_manifest_sha256": input_record["manifest_sha256"],
        "input_file_sha256": snapshot["file_sha256"],
        "input_pixel_payload_sha256": snapshot["pixel_payload_sha256"],
        "whole_file_hash": snapshot["whole_file_hash"],
        "pixel_payload_hash": snapshot["pixel_payload_hash"],
        "read_contract": {
            "artifact_read_count": 1,
            "hash_and_parse_same_memory": True,
        },
        "consumer_attestation": {
            "path": str(attestation_artifact.path),
            "sha256": attestation_artifact.sha256,
            "schema": attestation["schema"],
        },
        "complete_invocation": complete_invocation,
        "exit_code": 0,
        "outputs": outputs,
    }


def failure_record(exc: BaseException, schema: str = GATE_SCHEMA) -> dict[str, Any]:
    return {
        "schema": schema,
        "status": "FAIL",
        "failure_class": (
            exc.failure_class if isinstance(exc, GateFailure) else "UNEXPECTED_EXCEPTION"
        ),
        "reason": str(exc),
        "summary": {
            "inputs": _count_partition([], INPUT_OUTCOMES),
            "required_consumer_input_pairs": _count_partition([], PAIR_OUTCOMES),
            "optional_consumer_input_pairs": _count_partition([], PAIR_OUTCOMES),
            "all_consumer_input_pairs": _count_partition([], PAIR_OUTCOMES),
            "all_partitions_balanced": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--out", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--campaign", required=True)
    verify.add_argument("--registry", required=True)
    verify.add_argument("--freeze", required=True)
    verify.add_argument("--receipts", required=True)
    verify.add_argument("--out", required=True)

    record = subparsers.add_parser("record")
    record.add_argument("--campaign", required=True)
    record.add_argument("--registry", required=True)
    record.add_argument("--freeze", required=True)
    record.add_argument("--consumer-id", required=True)
    record.add_argument("--input-id", required=True)
    record.add_argument("--attestation", required=True)
    record.add_argument("--invocation-json", required=True)
    record.add_argument("--output", action="append", required=True)
    record.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out)
    try:
        if args.command == "freeze":
            result = build_freeze()
        elif args.command == "verify":
            result = verify_campaign(
                Path(args.campaign),
                Path(args.registry),
                Path(args.freeze),
                Path(args.receipts),
            )
        elif args.command == "record":
            invocation_artifact = ArtifactCache().read(
                Path(args.invocation_json), "complete invocation"
            )
            try:
                invocation = json.loads(invocation_artifact.data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise GateFailure(
                    "RECEIPT_INVOCATION_INVALID",
                    f"invocation JSON is invalid: {exc}",
                ) from exc
            require(
                isinstance(invocation, list),
                "RECEIPT_INVOCATION_INVALID",
                "invocation JSON must be an array",
            )
            result = make_receipt(
                Path(args.campaign),
                Path(args.registry),
                Path(args.freeze),
                args.consumer_id,
                args.input_id,
                Path(args.attestation),
                invocation,
                [Path(value) for value in args.output],
            )
        else:
            raise GateFailure("COMMAND_INVALID", str(args.command))
        write_json(out_path, result)
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("status") in {"PASS", "FROZEN"} else 1
    except BaseException as exc:
        schema = FREEZE_SCHEMA if args.command == "freeze" else GATE_SCHEMA
        result = failure_record(exc, schema)
        try:
            write_json(out_path, result)
        except BaseException as write_exc:
            print(
                json.dumps(
                    failure_record(
                        GateFailure(
                            "REPORT_WRITE_FAILED",
                            f"{exc}; additionally could not write report: {write_exc}",
                        ),
                        schema,
                    ),
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            return 1
        print(json.dumps(result, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
