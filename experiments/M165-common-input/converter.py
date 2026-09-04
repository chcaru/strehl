#!/usr/bin/env python3
"""Frozen LibRaw common-merge converter and strict TIFF inspector.

The renderer is deliberately fail-closed. It will not render without a frozen,
matching sensor-space pattern map made from non-empty independent dark and flat
source sets. It writes a deliberately small TIFF dialect that is independently
parsed by the Rust adapter in ``strehl-raw``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
from typing import Any, BinaryIO, Iterable

CONVERTER_ID = "m165-libraw-common-linear"
CONVERTER_VERSION = "1.1.0"
SETTINGS_SCHEMA = "m165-common-input-settings-v1"
FREEZE_SCHEMA = "m165-converter-freeze-v1"
PATTERN_SCHEMA = "m165-sensor-pattern-map-v1"
MANIFEST_SCHEMA = "m165-common-input-manifest-v2"
INSPECTION_SCHEMA = "m165-common-tiff-inspection-v1"
CONSUMER_REGISTRY_SCHEMA = "m165-common-input-consumer-registry-v1"
CONSUMER_RECEIPT_SCHEMA = "m165-common-input-consumer-receipt-v1"

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
ALLOWED_TIFF_TAGS = set(TIFF_TAGS.values())


class ContractFailure(RuntimeError):
    def __init__(self, failure_class: str, message: str):
        super().__init__(message)
        self.failure_class = failure_class


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("ascii")
        + b"\n"
    )
    os.replace(partial, path)


def hash_bytes(value: bytes | bytearray | memoryview) -> str:
    return hashlib.sha256(value).hexdigest()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def check_hash(value: str, label: str) -> str:
    value = value.strip().lower()
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ContractFailure("INVALID_HASH", f"{label} is not a SHA-256 hex digest")
    return value


def align4(value: int) -> int:
    return (value + 3) & ~3


def s15fixed16(value: float) -> bytes:
    scaled = round(value * 65536.0)
    if not -(1 << 31) <= scaled < (1 << 31):
        raise ValueError(f"ICC fixed-point value out of range: {value}")
    return struct.pack(">i", scaled)


def icc_xyz(x: float, y: float, z: float) -> bytes:
    return b"XYZ " + bytes(4) + b"".join(s15fixed16(v) for v in (x, y, z))


def icc_curve(gamma: float) -> bytes:
    encoded = round(gamma * 256.0)
    return b"curv" + bytes(4) + struct.pack(">I", 1) + struct.pack(">H", encoded) + bytes(2)


def icc_description(text: str) -> bytes:
    ascii_text = text.encode("ascii") + b"\0"
    # ICC v2 textDescription: ASCII, empty Unicode, empty ScriptCode.
    return (
        b"desc"
        + bytes(4)
        + struct.pack(">I", len(ascii_text))
        + ascii_text
        + bytes(4)
        + bytes(4)
        + bytes(2)
        + bytes(1)
        + bytes(67)
    )


def icc_text(text: str) -> bytes:
    return b"text" + bytes(4) + text.encode("ascii") + b"\0"


def build_linear_prophoto_icc() -> bytes:
    """Build a deterministic ICC v2 linear ROMM/ProPhoto RGB D50 profile."""
    tags = [
        (b"bTRC", icc_curve(1.0)),
        (b"bXYZ", icc_xyz(0.0313534, 0.0000857, 0.8252100)),
        (b"cprt", icc_text("CC0-1.0; generated deterministically by M165")),
        (b"desc", icc_description("M165 Linear ProPhoto RGB D50 v1")),
        (b"gTRC", icc_curve(1.0)),
        (b"gXYZ", icc_xyz(0.1351917, 0.7118741, 0.0000000)),
        (b"rTRC", icc_curve(1.0)),
        (b"rXYZ", icc_xyz(0.7976749, 0.2880402, 0.0000000)),
        (b"wtpt", icc_xyz(0.9642200, 1.0000000, 0.8252100)),
    ]
    tags.sort(key=lambda item: item[0])
    table_size = 4 + len(tags) * 12
    data_at = align4(128 + table_size)
    table = bytearray(struct.pack(">I", len(tags)))
    payload = bytearray()
    for signature, value in tags:
        offset = data_at + len(payload)
        table.extend(signature)
        table.extend(struct.pack(">II", offset, len(value)))
        payload.extend(value)
        payload.extend(bytes(align4(len(payload)) - len(payload)))

    size = data_at + len(payload)
    header = bytearray(128)
    header[0:4] = struct.pack(">I", size)
    header[4:8] = b"M165"
    header[8:12] = struct.pack(">I", 0x02100000)
    header[12:16] = b"mntr"
    header[16:20] = b"RGB "
    header[20:24] = b"XYZ "
    header[24:36] = struct.pack(">6H", 2026, 8, 1, 0, 0, 0)
    header[36:40] = b"acsp"
    header[64:68] = struct.pack(">I", 0)
    header[68:80] = b"".join(s15fixed16(v) for v in (0.9642, 1.0, 0.8249))
    header[80:84] = b"M165"
    return bytes(header + table + bytes(data_at - 128 - len(table)) + payload)


def inspect_linear_prophoto_icc(profile: bytes) -> dict[str, Any]:
    if len(profile) < 132 or profile[36:40] != b"acsp":
        raise ContractFailure("ICC_INVALID", "ICC header is absent or malformed")
    declared_size = struct.unpack(">I", profile[:4])[0]
    if declared_size != len(profile):
        raise ContractFailure(
            "ICC_INVALID", f"ICC declares {declared_size} bytes but has {len(profile)}"
        )
    tag_count = struct.unpack(">I", profile[128:132])[0]
    tags: dict[bytes, bytes] = {}
    for index in range(tag_count):
        at = 132 + index * 12
        if at + 12 > len(profile):
            raise ContractFailure("ICC_INVALID", "ICC tag table is truncated")
        signature = profile[at : at + 4]
        offset, size = struct.unpack(">II", profile[at + 4 : at + 12])
        if offset + size > len(profile):
            raise ContractFailure("ICC_INVALID", f"ICC tag {signature!r} is truncated")
        tags[signature] = profile[offset : offset + size]

    def fixed(raw: bytes) -> float:
        return struct.unpack(">i", raw)[0] / 65536.0

    def xyz(name: bytes) -> list[float]:
        value = tags.get(name, b"")
        if len(value) < 20 or value[:4] != b"XYZ ":
            raise ContractFailure("ICC_INVALID", f"ICC tag {name!r} is not XYZ")
        return [fixed(value[8 + 4 * i : 12 + 4 * i]) for i in range(3)]

    def gamma(name: bytes) -> float:
        value = tags.get(name, b"")
        if len(value) < 14 or value[:4] != b"curv":
            raise ContractFailure("ICC_INVALID", f"ICC tag {name!r} is not a curve")
        if struct.unpack(">I", value[8:12])[0] != 1:
            raise ContractFailure("ICC_INVALID", f"ICC tag {name!r} is not one gamma")
        return struct.unpack(">H", value[12:14])[0] / 256.0

    return {
        "profile_size": len(profile),
        "profile_version_hex": f"{struct.unpack('>I', profile[8:12])[0]:08x}",
        "device_class": profile[12:16].decode("ascii"),
        "data_color_space": profile[16:20].decode("ascii"),
        "pcs": profile[20:24].decode("ascii"),
        "header_d50_xyz": [fixed(profile[68 + 4 * i : 72 + 4 * i]) for i in range(3)],
        "media_white_xyz": xyz(b"wtpt"),
        "matrix_columns_xyz": {
            "red": xyz(b"rXYZ"),
            "green": xyz(b"gXYZ"),
            "blue": xyz(b"bXYZ"),
        },
        "trc_gamma": {
            "red": gamma(b"rTRC"),
            "green": gamma(b"gTRC"),
            "blue": gamma(b"bTRC"),
        },
    }


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractFailure("INVALID_JSON", f"cannot read {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractFailure("INVALID_JSON", f"{label} must be a JSON object")
    return value


def validate_settings(path: Path) -> dict[str, Any]:
    settings = load_json(path, "settings")
    if settings.get("schema") != SETTINGS_SCHEMA:
        raise ContractFailure(
            "SETTINGS_SCHEMA_MISMATCH",
            f"settings schema must be {SETTINGS_SCHEMA!r}",
        )
    converter = settings.get("converter", {})
    if converter.get("id") != CONVERTER_ID or converter.get("version") != CONVERTER_VERSION:
        raise ContractFailure(
            "SETTINGS_CONVERTER_MISMATCH",
            "settings do not name this converter and version",
        )
    expected = {
        "demosaic_algorithm": "AHD",
        "half_size": False,
        "four_color_rgb": False,
        "dcb_iterations": 0,
        "dcb_enhance": False,
        "fbdd_noise_reduction": "Off",
        "noise_thr": None,
        "median_filter_passes": 0,
        "use_camera_wb": True,
        "use_auto_wb": False,
        "user_wb": None,
        "output_color": "ProPhoto",
        "output_bps": 16,
        "user_flip": 0,
        "user_black": 0,
        "user_cblack": "LibRaw per-channel camera metadata",
        "user_sat": "LibRaw camera white level",
        "no_auto_bright": True,
        "auto_bright_thr": None,
        "adjust_maximum_thr": 0.0,
        "bright": 1.0,
        "highlight_mode": "Clip",
        "exp_shift": None,
        "exp_preserve_highlights": 0.0,
        "no_auto_scale": False,
        "gamma": [1.0, 1.0],
        "chromatic_aberration": None,
        "bad_pixels_path": None,
    }
    if settings.get("postprocess") != expected:
        raise ContractFailure(
            "SETTINGS_NOT_FROZEN",
            "postprocess settings differ from the converter's v1 contract",
        )
    return settings


def import_runtime() -> tuple[Any, Any]:
    try:
        import numpy as np
        import rawpy
    except Exception as exc:
        raise ContractFailure("RUNTIME_IMPORT_FAILED", str(exc)) from exc
    return np, rawpy


def runtime_artifacts(settings: Path, icc: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    np, rawpy = import_runtime()
    script = Path(__file__).resolve()
    python = Path(sys.executable).resolve()
    rawpy_module = Path(rawpy.__file__).resolve()
    rawpy_extension = Path(rawpy._rawpy.__file__).resolve()
    numpy_module = Path(np.__file__).resolve()
    numpy_extension = Path(np._core._multiarray_umath.__file__).resolve()
    exiftool_name = shutil.which("exiftool")
    if exiftool_name is None:
        raise ContractFailure(
            "EXIFTOOL_ABSENT", "ExifTool is required to bind camera make/model/ISO"
        )
    exiftool = Path(exiftool_name).resolve()
    try:
        exiftool_version = subprocess.run(
            [str(exiftool), "-ver"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ContractFailure("EXIFTOOL_FAILED", str(exc)) from exc
    members = {
        "converter_script_sha256": hash_file(script),
        "python_executable_sha256": hash_file(python),
        "rawpy_module_sha256": hash_file(rawpy_module),
        "rawpy_extension_sha256": hash_file(rawpy_extension),
        "numpy_module_sha256": hash_file(numpy_module),
        "numpy_extension_sha256": hash_file(numpy_extension),
        "exiftool_executable_sha256": hash_file(exiftool),
        "settings_sha256": hash_file(settings),
        "icc_sha256": hash_file(icc),
        "converter_id": CONVERTER_ID,
        "converter_version": CONVERTER_VERSION,
        "python_version": platform.python_version(),
        "rawpy_version": rawpy.__version__,
        "libraw_version": ".".join(str(v) for v in rawpy.libraw_version),
        "numpy_version": np.__version__,
        "exiftool_version": exiftool_version,
    }
    artifacts = {
        "converter_script": {
            "path": str(script),
            "sha256": members["converter_script_sha256"],
        },
        "python_executable": {
            "path": str(python),
            "sha256": members["python_executable_sha256"],
        },
        "rawpy_module": {
            "path": str(rawpy_module),
            "sha256": members["rawpy_module_sha256"],
        },
        "rawpy_extension": {
            "path": str(rawpy_extension),
            "sha256": members["rawpy_extension_sha256"],
        },
        "numpy_module": {
            "path": str(numpy_module),
            "sha256": members["numpy_module_sha256"],
        },
        "numpy_extension": {
            "path": str(numpy_extension),
            "sha256": members["numpy_extension_sha256"],
        },
        "exiftool_executable": {
            "path": str(exiftool),
            "sha256": members["exiftool_executable_sha256"],
            "version": exiftool_version,
        },
        "settings": {
            "path": str(settings.resolve()),
            "sha256": members["settings_sha256"],
        },
        "icc": {
            "path": str(icc.resolve()),
            "sha256": members["icc_sha256"],
        },
    }
    return members, artifacts


def build_freeze(settings: Path, icc: Path) -> dict[str, Any]:
    validate_settings(settings)
    generated_icc = build_linear_prophoto_icc()
    try:
        disk_icc = icc.read_bytes()
    except OSError as exc:
        raise ContractFailure("ICC_READ_FAILED", f"cannot read ICC {icc}: {exc}") from exc
    if disk_icc != generated_icc:
        raise ContractFailure(
            "ICC_NOT_CANONICAL",
            "ICC bytes differ from the converter's deterministic v1 profile",
        )
    members, artifacts = runtime_artifacts(settings, icc)
    return {
        "schema": FREEZE_SCHEMA,
        "status": "FROZEN",
        "converter": {
            "id": CONVERTER_ID,
            "version": CONVERTER_VERSION,
            "executable_bundle_sha256": hash_bytes(canonical_json(members)),
            "bundle_members": members,
        },
        "artifacts": artifacts,
        "icc_inspection": inspect_linear_prophoto_icc(disk_icc),
    }


def verify_freeze(path: Path, settings: Path, icc: Path) -> dict[str, Any]:
    freeze = load_json(path, "converter freeze")
    if freeze.get("schema") != FREEZE_SCHEMA or freeze.get("status") != "FROZEN":
        raise ContractFailure("FREEZE_INVALID", "converter freeze is absent or not FROZEN")
    members, _ = runtime_artifacts(settings, icc)
    converter = freeze.get("converter", {})
    expected = check_hash(
        str(converter.get("executable_bundle_sha256", "")), "frozen converter bundle"
    )
    actual = hash_bytes(canonical_json(members))
    if actual != expected or converter.get("bundle_members") != members:
        raise ContractFailure(
            "CONVERTER_FREEZE_MISMATCH",
            f"current converter bundle {actual} differs from frozen {expected}",
        )
    return freeze


def _registry_artifact_path(registry_path: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ContractFailure(
            "CONSUMER_REGISTRY_INVALID", f"{label} must be a non-empty path"
        )
    path = Path(value)
    if not path.is_absolute():
        path = registry_path.parent / path
    return path.resolve()


def validate_consumer_registry(path: Path) -> dict[str, Any]:
    """Validate an arbitrary-size consumer freeze and every frozen executable."""
    registry = load_json(path, "consumer registry")
    if registry.get("schema") != CONSUMER_REGISTRY_SCHEMA:
        raise ContractFailure(
            "CONSUMER_REGISTRY_SCHEMA_MISMATCH",
            f"consumer registry schema must be {CONSUMER_REGISTRY_SCHEMA!r}",
        )
    if registry.get("status") != "FROZEN":
        raise ContractFailure(
            "CONSUMER_REGISTRY_NOT_FROZEN",
            f"consumer registry status is {registry.get('status')!r}, not 'FROZEN'",
        )
    if registry.get("track") != "common-merge":
        raise ContractFailure(
            "CONSUMER_REGISTRY_TRACK_MISMATCH",
            "consumer registry must name the common-merge track",
        )
    if not isinstance(registry.get("registry_id"), str) or not registry["registry_id"]:
        raise ContractFailure(
            "CONSUMER_REGISTRY_INVALID", "registry_id must be a non-empty string"
        )
    if not isinstance(registry.get("version"), str) or not registry["version"]:
        raise ContractFailure(
            "CONSUMER_REGISTRY_INVALID", "registry version must be a non-empty string"
        )
    consumers = registry.get("consumers")
    if not isinstance(consumers, list) or not consumers:
        raise ContractFailure(
            "CONSUMER_REGISTRY_EMPTY", "consumer registry must contain at least one consumer"
        )

    ids: set[str] = set()
    frozen: list[dict[str, Any]] = []
    required_count = 0
    for index, consumer in enumerate(consumers):
        if not isinstance(consumer, dict):
            raise ContractFailure(
                "CONSUMER_REGISTRY_INVALID", f"consumer {index} is not an object"
            )
        consumer_id = consumer.get("consumer_id")
        if not isinstance(consumer_id, str) or not consumer_id:
            raise ContractFailure(
                "CONSUMER_REGISTRY_INVALID",
                f"consumer {index} has no non-empty consumer_id",
            )
        if consumer_id in ids:
            raise ContractFailure(
                "CONSUMER_REGISTRY_DUPLICATE", f"duplicate consumer_id {consumer_id!r}"
            )
        ids.add(consumer_id)
        if not isinstance(consumer.get("role"), str) or not consumer["role"]:
            raise ContractFailure(
                "CONSUMER_REGISTRY_INVALID", f"{consumer_id}: role is absent"
            )
        if not isinstance(consumer.get("required"), bool):
            raise ContractFailure(
                "CONSUMER_REGISTRY_INVALID", f"{consumer_id}: required must be boolean"
            )
        required_count += int(consumer["required"])
        if consumer.get("status") != "FROZEN":
            if consumer["required"]:
                raise ContractFailure(
                    "CONSUMER_REQUIRED_NOT_FROZEN",
                    f"required consumer {consumer_id!r} is {consumer.get('status')!r}",
                )
            frozen.append(
                {
                    "consumer_id": consumer_id,
                    "role": consumer["role"],
                    "required": False,
                    "status": consumer.get("status"),
                    "blocker": consumer.get("blocker"),
                }
            )
            continue

        kind = consumer.get("implementation_kind")
        if kind not in {"installed-binary", "source-build", "script-runtime-bundle"}:
            raise ContractFailure(
                "CONSUMER_REGISTRY_INVALID",
                f"{consumer_id}: unsupported implementation_kind {kind!r}",
            )
        executable = _registry_artifact_path(
            path, consumer.get("executable_path"), f"{consumer_id} executable_path"
        )
        if not executable.is_file():
            raise ContractFailure(
                "CONSUMER_EXECUTABLE_ABSENT",
                f"{consumer_id}: executable does not exist: {executable}",
            )
        executable_sha = check_hash(
            str(consumer.get("executable_sha256", "")),
            f"{consumer_id} executable",
        )
        actual_executable_sha = hash_file(executable)
        if actual_executable_sha != executable_sha:
            raise ContractFailure(
                "CONSUMER_EXECUTABLE_HASH_MISMATCH",
                f"{consumer_id}: executable hash is {actual_executable_sha}, "
                f"expected {executable_sha}",
            )
        executable_bytes = consumer.get("executable_bytes")
        if not isinstance(executable_bytes, int) or executable_bytes != executable.stat().st_size:
            raise ContractFailure(
                "CONSUMER_EXECUTABLE_SIZE_MISMATCH",
                f"{consumer_id}: executable_bytes does not match {executable}",
            )
        if not isinstance(consumer.get("version"), str) or not consumer["version"]:
            raise ContractFailure(
                "CONSUMER_REGISTRY_INVALID", f"{consumer_id}: version is absent"
            )

        settings = consumer.get("settings")
        if not isinstance(settings, dict):
            raise ContractFailure(
                "CONSUMER_REGISTRY_INVALID", f"{consumer_id}: settings must be an object"
            )
        settings_sha = check_hash(
            str(consumer.get("settings_sha256", "")), f"{consumer_id} settings"
        )
        actual_settings_sha = hash_bytes(canonical_json(settings))
        if actual_settings_sha != settings_sha:
            raise ContractFailure(
                "CONSUMER_SETTINGS_HASH_MISMATCH",
                f"{consumer_id}: settings hash is {actual_settings_sha}, expected {settings_sha}",
            )
        invocation = consumer.get("invocation_template")
        if (
            not isinstance(invocation, list)
            or not invocation
            or not all(isinstance(value, str) for value in invocation)
            or not any("{input_tiff}" in value for value in invocation)
        ):
            raise ContractFailure(
                "CONSUMER_INVOCATION_INVALID",
                f"{consumer_id}: invocation_template must contain {{input_tiff}}",
            )
        expected_input_contract = {
            "kind": "exact-common-tiff-bytes",
            "file_sha256_from": "input_manifest.output.file_sha256",
            "pixel_sha256_from": "input_manifest.output.pixel_payload_sha256",
        }
        if consumer.get("input_contract") != expected_input_contract:
            raise ContractFailure(
                "CONSUMER_INPUT_CONTRACT_MISMATCH",
                f"{consumer_id}: input contract is not the frozen exact-byte contract",
            )

        source_revision = consumer.get("source_revision")
        build_manifest_path: str | None = None
        build_manifest_sha: str | None = None
        if kind == "source-build":
            if (
                not isinstance(source_revision, str)
                or len(source_revision) != 40
                or any(ch not in "0123456789abcdefABCDEF" for ch in source_revision)
            ):
                raise ContractFailure(
                    "CONSUMER_SOURCE_PIN_INVALID",
                    f"{consumer_id}: source-build requires a full 40-hex source_revision",
                )
            build_manifest = _registry_artifact_path(
                path,
                consumer.get("build_manifest_path"),
                f"{consumer_id} build_manifest_path",
            )
            if not build_manifest.is_file():
                raise ContractFailure(
                    "CONSUMER_BUILD_MANIFEST_ABSENT",
                    f"{consumer_id}: build manifest does not exist: {build_manifest}",
                )
            build_manifest_sha = check_hash(
                str(consumer.get("build_manifest_sha256", "")),
                f"{consumer_id} build manifest",
            )
            actual_build_sha = hash_file(build_manifest)
            if actual_build_sha != build_manifest_sha:
                raise ContractFailure(
                    "CONSUMER_BUILD_MANIFEST_HASH_MISMATCH",
                    f"{consumer_id}: build manifest hash is {actual_build_sha}, "
                    f"expected {build_manifest_sha}",
                )
            build_manifest_path = str(build_manifest)
        elif source_revision is not None:
            if (
                not isinstance(source_revision, str)
                or len(source_revision) != 40
                or any(ch not in "0123456789abcdefABCDEF" for ch in source_revision)
            ):
                raise ContractFailure(
                    "CONSUMER_SOURCE_PIN_INVALID",
                    f"{consumer_id}: source_revision is not full 40-hex",
                )

        frozen.append(
            {
                "consumer_id": consumer_id,
                "role": consumer["role"],
                "required": consumer["required"],
                "status": "FROZEN",
                "implementation_kind": kind,
                "version": consumer["version"],
                "executable_path": str(executable),
                "executable_bytes": executable_bytes,
                "executable_sha256": executable_sha,
                "source_revision": (
                    source_revision.lower() if isinstance(source_revision, str) else None
                ),
                "build_manifest_path": build_manifest_path,
                "build_manifest_sha256": build_manifest_sha,
                "settings": settings,
                "settings_sha256": settings_sha,
                "invocation_template": invocation,
                "input_contract": expected_input_contract,
            }
        )

    if required_count == 0:
        raise ContractFailure(
            "CONSUMER_REGISTRY_NO_REQUIRED_CONSUMERS",
            "consumer registry must contain at least one required consumer",
        )

    return {
        "schema": CONSUMER_REGISTRY_SCHEMA,
        "status": "FROZEN",
        "track": "common-merge",
        "registry_id": registry["registry_id"],
        "version": registry["version"],
        "consumer_count": len(consumers),
        "required_consumer_count": required_count,
        "consumers": frozen,
    }


def _tiff_entry(tag: int, kind: int, count: int, value: int | bytes) -> bytes:
    if isinstance(value, int):
        raw = struct.pack("<I", value)
    else:
        if len(value) > 4:
            raise ValueError("inline TIFF value exceeds four bytes")
        raw = value + bytes(4 - len(value))
    return struct.pack("<HHI", tag, kind, count) + raw


def write_common_tiff(
    path: Path,
    rgb: Any,
    icc: bytes,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    np, _ = import_runtime()
    if not isinstance(rgb, np.ndarray) or rgb.dtype != np.uint16:
        raise ContractFailure("PIXEL_TYPE_INVALID", "TIFF pixels must be numpy uint16")
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ContractFailure("PIXEL_SHAPE_INVALID", "TIFF pixels must have shape HxWx3")
    if not rgb.flags.c_contiguous:
        rgb = np.ascontiguousarray(rgb)
    rgb = rgb.astype("<u2", copy=False)
    height, width, _ = rgb.shape
    pixel_bytes = int(rgb.nbytes)
    if width <= 0 or height <= 0 or pixel_bytes >= 2**32:
        raise ContractFailure("TIFF_SIZE_INVALID", "classic-TIFF dimensions are invalid")

    description = canonical_json(provenance) + b"\0"
    entry_count = 13
    ifd_end = 8 + 2 + entry_count * 12 + 4
    # Four unreferenced zero bytes are structural alignment padding. The
    # commissioning probe flips one to prove whole-file identity can move
    # without changing any pixel or semantic metadata.
    bits_at = align4(ifd_end) + 4
    sample_format_at = align4(bits_at + 6)
    description_at = align4(sample_format_at + 6)
    icc_at = align4(description_at + len(description))
    pixels_at = align4(icc_at + len(icc))
    if pixels_at + pixel_bytes >= 2**32:
        raise ContractFailure("TIFF_SIZE_INVALID", "classic TIFF exceeds 4 GiB")

    entries = [
        _tiff_entry(TIFF_TAGS["width"], 4, 1, width),
        _tiff_entry(TIFF_TAGS["height"], 4, 1, height),
        _tiff_entry(TIFF_TAGS["bits"], 3, 3, bits_at),
        _tiff_entry(TIFF_TAGS["compression"], 3, 1, struct.pack("<H", 1)),
        _tiff_entry(TIFF_TAGS["photometric"], 3, 1, struct.pack("<H", 2)),
        _tiff_entry(TIFF_TAGS["description"], 2, len(description), description_at),
        _tiff_entry(TIFF_TAGS["strip_offsets"], 4, 1, pixels_at),
        _tiff_entry(TIFF_TAGS["samples_per_pixel"], 3, 1, struct.pack("<H", 3)),
        _tiff_entry(TIFF_TAGS["rows_per_strip"], 4, 1, height),
        _tiff_entry(TIFF_TAGS["strip_byte_counts"], 4, 1, pixel_bytes),
        _tiff_entry(TIFF_TAGS["planar"], 3, 1, struct.pack("<H", 1)),
        _tiff_entry(TIFF_TAGS["sample_format"], 3, 3, sample_format_at),
        _tiff_entry(TIFF_TAGS["icc"], 7, len(icc), icc_at),
    ]
    entries.sort(key=lambda value: struct.unpack("<H", value[:2])[0])

    prefix = bytearray(pixels_at)
    prefix[0:8] = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)
    prefix[8:10] = struct.pack("<H", entry_count)
    at = 10
    for entry in entries:
        prefix[at : at + 12] = entry
        at += 12
    prefix[at : at + 4] = bytes(4)
    prefix[bits_at : bits_at + 6] = struct.pack("<3H", 16, 16, 16)
    prefix[sample_format_at : sample_format_at + 6] = struct.pack("<3H", 1, 1, 1)
    prefix[description_at : description_at + len(description)] = description
    prefix[icc_at : icc_at + len(icc)] = icc

    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    pixel_view = memoryview(rgb).cast("B")
    pixel_hash = hashlib.sha256()
    try:
        with partial.open("wb") as handle:
            handle.write(prefix)
            for start in range(0, len(pixel_view), 8 * 1024 * 1024):
                chunk = pixel_view[start : start + 8 * 1024 * 1024]
                pixel_hash.update(chunk)
                handle.write(chunk)
        os.replace(partial, path)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    return {
        "file_sha256": hash_file(path),
        "pixel_payload_sha256": pixel_hash.hexdigest(),
        "icc_sha256": hash_bytes(icc),
        "width": width,
        "height": height,
        "pixel_bytes": pixel_bytes,
        "strip_offset": pixels_at,
        "strip_byte_count": pixel_bytes,
        "inert_padding_offset": align4(ifd_end),
    }


def _read_at(data: bytes, at: int, size: int, label: str) -> bytes:
    if at < 0 or size < 0 or at + size > len(data):
        raise ContractFailure("TIFF_TRUNCATED", f"{label} exceeds TIFF bounds")
    return data[at : at + size]


def _entry_data(data: bytes, entry: tuple[int, int, int, bytes]) -> bytes:
    tag, kind, count, inline = entry
    sizes = {1: 1, 2: 1, 3: 2, 4: 4, 7: 1}
    if kind not in sizes:
        raise ContractFailure("TIFF_TYPE_REJECTED", f"tag {tag} has type {kind}")
    size = count * sizes[kind]
    if size <= 4:
        return inline[:size]
    offset = struct.unpack("<I", inline)[0]
    return _read_at(data, offset, size, f"tag {tag}")


def _unsigned_values(data: bytes, entry: tuple[int, int, int, bytes]) -> list[int]:
    _, kind, _, _ = entry
    value = _entry_data(data, entry)
    if kind == 3:
        return list(struct.unpack("<" + "H" * (len(value) // 2), value))
    if kind == 4:
        return list(struct.unpack("<" + "I" * (len(value) // 4), value))
    raise ContractFailure("TIFF_TYPE_REJECTED", "numeric TIFF field is not SHORT/LONG")


def inspect_common_tiff(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ContractFailure("TIFF_READ_FAILED", f"cannot read TIFF {path}: {exc}") from exc
    if len(data) < 8 or data[:2] != b"II" or struct.unpack("<H", data[2:4])[0] != 42:
        raise ContractFailure("TIFF_HEADER_REJECTED", "not a little-endian classic TIFF")
    ifd = struct.unpack("<I", data[4:8])[0]
    count = struct.unpack("<H", _read_at(data, ifd, 2, "IFD count"))[0]
    entries: dict[int, tuple[int, int, int, bytes]] = {}
    for index in range(count):
        raw = _read_at(data, ifd + 2 + index * 12, 12, "IFD entry")
        tag, kind, value_count = struct.unpack("<HHI", raw[:8])
        if tag not in ALLOWED_TIFF_TAGS:
            raise ContractFailure(
                "TIFF_TAG_REJECTED", f"tag {tag} is not structural, provenance, or ICC"
            )
        if tag in entries:
            raise ContractFailure("TIFF_TAG_DUPLICATE", f"duplicate tag {tag}")
        entries[tag] = (tag, kind, value_count, raw[8:12])
    next_ifd_at = ifd + 2 + count * 12
    if struct.unpack("<I", _read_at(data, next_ifd_at, 4, "next IFD"))[0] != 0:
        raise ContractFailure("TIFF_MULTI_IMAGE", "multiple TIFF images are forbidden")
    if set(entries) != ALLOWED_TIFF_TAGS:
        missing = sorted(ALLOWED_TIFF_TAGS - set(entries))
        raise ContractFailure("TIFF_TAG_MISSING", f"required tags absent: {missing}")

    scalar = lambda name: _unsigned_values(data, entries[TIFF_TAGS[name]])[0]
    width, height = scalar("width"), scalar("height")
    bits = _unsigned_values(data, entries[TIFF_TAGS["bits"]])
    sample_format = _unsigned_values(data, entries[TIFF_TAGS["sample_format"]])
    checks = [
        (bits == [16, 16, 16], f"BitsPerSample is {bits}"),
        (scalar("compression") == 1, f"Compression is {scalar('compression')}"),
        (scalar("photometric") == 2, f"Photometric is {scalar('photometric')}"),
        (scalar("samples_per_pixel") == 3, "SamplesPerPixel is not 3"),
        (scalar("planar") == 1, f"PlanarConfiguration is {scalar('planar')}"),
        (sample_format == [1, 1, 1], f"SampleFormat is {sample_format}"),
        (scalar("rows_per_strip") == height, "TIFF is not a single full-image strip"),
    ]
    for valid, message in checks:
        if not valid:
            raise ContractFailure("TIFF_CONTRACT_REJECTED", message)
    offsets = _unsigned_values(data, entries[TIFF_TAGS["strip_offsets"]])
    counts = _unsigned_values(data, entries[TIFF_TAGS["strip_byte_counts"]])
    if len(offsets) != 1 or len(counts) != 1 or counts[0] != width * height * 6:
        raise ContractFailure("TIFF_STRIP_REJECTED", "strip layout is not canonical RGB16")
    payload = _read_at(data, offsets[0], counts[0], "pixel payload")
    description = _entry_data(data, entries[TIFF_TAGS["description"]])
    if not description.endswith(b"\0"):
        raise ContractFailure("TIFF_PROVENANCE_REJECTED", "provenance is not NUL-terminated")
    try:
        provenance = json.loads(description[:-1].decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractFailure("TIFF_PROVENANCE_REJECTED", str(exc)) from exc
    icc = _entry_data(data, entries[TIFF_TAGS["icc"]])
    if len(icc) < 128 or icc[36:40] != b"acsp":
        raise ContractFailure("TIFF_ICC_REJECTED", "embedded ICC is malformed")
    return {
        "schema": INSPECTION_SCHEMA,
        "status": "PASS",
        "path": str(path.resolve()),
        "width": width,
        "height": height,
        "bits_per_sample": bits,
        "sample_format": sample_format,
        "compression": scalar("compression"),
        "photometric": scalar("photometric"),
        "planar_configuration": scalar("planar"),
        "rows_per_strip": scalar("rows_per_strip"),
        "strip_count": 1,
        "strip_offset": offsets[0],
        "strip_byte_count": counts[0],
        "pixel_payload_sha256": hash_bytes(payload),
        "file_sha256": hash_bytes(data),
        "icc_sha256": hash_bytes(icc),
        "provenance": provenance,
    }


def validate_pattern_manifest(
    manifest_path: Path,
    map_path: Path,
    raw: Any,
    camera_metadata: dict[str, Any],
    source_sha256: str,
    source_path: Path,
) -> tuple[dict[str, Any], Any, Any]:
    np, _ = import_runtime()
    manifest = load_json(manifest_path, "pattern-map manifest")
    if manifest.get("schema") != PATTERN_SCHEMA or manifest.get("status") != "FROZEN":
        raise ContractFailure(
            "PATTERN_MAP_NOT_FROZEN", "pattern-map manifest is absent or not FROZEN"
        )
    darks = manifest.get("independent_dark_source_sha256", [])
    flats = manifest.get("independent_flat_source_sha256", [])
    if not isinstance(darks, list) or not darks or not isinstance(flats, list) or not flats:
        raise ContractFailure(
            "PATTERN_MAP_SOURCES_ABSENT",
            "pattern map must bind non-empty independent dark and flat source sets",
        )
    for index, value in enumerate(darks):
        check_hash(str(value), f"dark source {index}")
    for index, value in enumerate(flats):
        check_hash(str(value), f"flat source {index}")
    dark_set = {str(value).lower() for value in darks}
    flat_set = {str(value).lower() for value in flats}
    if dark_set & flat_set or source_sha256 in dark_set | flat_set:
        raise ContractFailure(
            "PATTERN_MAP_SOURCES_NOT_INDEPENDENT",
            "dark, flat, and subject source sets must be disjoint",
        )
    estimator = manifest.get("estimator", {})
    if not estimator.get("id") or not estimator.get("version"):
        raise ContractFailure(
            "PATTERN_MAP_ESTIMATOR_ABSENT",
            "pattern map must name its estimator and version",
        )
    check_hash(
        str(estimator.get("executable_sha256", "")),
        "pattern-map estimator executable",
    )
    expected_map = check_hash(str(manifest.get("map_npz_sha256", "")), "pattern map")
    actual_map = hash_file(map_path)
    if actual_map != expected_map:
        raise ContractFailure(
            "PATTERN_MAP_HASH_MISMATCH",
            f"pattern map hash is {actual_map}, expected {expected_map}",
        )
    visible = raw.raw_image_visible
    if list(manifest.get("active_shape", [])) != list(visible.shape):
        raise ContractFailure(
            "PATTERN_MAP_SHAPE_MISMATCH",
            f"map shape {manifest.get('active_shape')} != RAW visible shape {list(visible.shape)}",
        )
    capture_match = manifest.get("capture_match", {})
    if capture_match != camera_metadata:
        raise ContractFailure(
            "PATTERN_MAP_CAMERA_MISMATCH",
            f"map capture match {capture_match!r} != source metadata "
            f"{camera_metadata!r} ({source_path})",
        )
    expected_sensor = sensor_fingerprint(raw)
    if manifest.get("sensor_fingerprint") != expected_sensor:
        raise ContractFailure(
            "PATTERN_MAP_SENSOR_MISMATCH",
            f"map sensor fingerprint differs from source: expected {expected_sensor!r}",
        )
    semantics = (
        "corrected = black + clip((raw - black - offset_dn) * gain, "
        "0, white - black)"
    )
    if manifest.get("semantics") != semantics:
        raise ContractFailure(
            "PATTERN_MAP_SEMANTICS_MISMATCH",
            "pattern-map correction semantics are not the frozen v1 formula",
        )
    shape = list(visible.shape)
    expected_arrays = {
        "gain": {"dtype": "float32", "shape": shape},
        "offset_dn": {"dtype": "float32", "shape": shape},
    }
    if manifest.get("arrays") != expected_arrays:
        raise ContractFailure(
            "PATTERN_MAP_ARRAY_DECLARATION_MISMATCH",
            f"array declaration must be {expected_arrays!r}",
        )
    try:
        with np.load(map_path, allow_pickle=False) as arrays:
            if set(arrays.files) != {"gain", "offset_dn"}:
                raise ContractFailure(
                    "PATTERN_MAP_ARRAYS_INVALID",
                    f"map arrays must be exactly gain and offset_dn, got {arrays.files}",
                )
            if arrays["gain"].dtype != np.dtype("float32") or arrays[
                "offset_dn"
            ].dtype != np.dtype("float32"):
                raise ContractFailure(
                    "PATTERN_MAP_ARRAYS_INVALID",
                    "gain and offset_dn arrays must be float32",
                )
            gain = np.asarray(arrays["gain"], dtype=np.float64)
            offset = np.asarray(arrays["offset_dn"], dtype=np.float64)
    except ContractFailure:
        raise
    except Exception as exc:
        raise ContractFailure("PATTERN_MAP_READ_FAILED", str(exc)) from exc
    if gain.shape != visible.shape or offset.shape != visible.shape:
        raise ContractFailure("PATTERN_MAP_SHAPE_MISMATCH", "map array shape mismatch")
    if not np.all(np.isfinite(gain)) or not np.all(gain > 0):
        raise ContractFailure("PATTERN_MAP_VALUES_INVALID", "all gains must be finite and > 0")
    if not np.all(np.isfinite(offset)):
        raise ContractFailure("PATTERN_MAP_VALUES_INVALID", "all offsets must be finite")
    return manifest, gain, offset


def apply_pattern_correction(
    raw_values: Any,
    color_indices: Any,
    black_levels: Iterable[float],
    white_levels: Iterable[float],
    gain: Any,
    offset_dn: Any,
) -> Any:
    np, _ = import_runtime()
    raw_values = np.asarray(raw_values)
    colors = np.asarray(color_indices)
    black = np.asarray(list(black_levels), dtype=np.float64)
    white = np.asarray(list(white_levels), dtype=np.float64)
    if raw_values.shape != colors.shape or raw_values.shape != gain.shape:
        raise ContractFailure("PATTERN_MAP_SHAPE_MISMATCH", "correction arrays differ in shape")
    if black.shape != (4,) or white.shape != (4,):
        raise ContractFailure("SENSOR_LEVELS_INVALID", "four black and white levels required")
    if np.any(colors < 0) or np.any(colors > 3):
        raise ContractFailure("CFA_INDEX_INVALID", "CFA color index is outside 0..3")
    black_at = black[colors]
    white_at = white[colors]
    if np.any(white_at <= black_at):
        raise ContractFailure("SENSOR_LEVELS_INVALID", "white must exceed black")
    corrected_signal = (raw_values.astype(np.float64) - black_at - offset_dn) * gain
    corrected = black_at + np.clip(corrected_signal, 0.0, white_at - black_at)
    return np.rint(corrected).astype(np.uint16)


def postprocess_kwargs(rawpy: Any, black_levels: list[int], white_level: int) -> dict[str, Any]:
    return {
        "demosaic_algorithm": rawpy.DemosaicAlgorithm.AHD,
        "half_size": False,
        "four_color_rgb": False,
        "dcb_iterations": 0,
        "dcb_enhance": False,
        "fbdd_noise_reduction": rawpy.FBDDNoiseReductionMode.Off,
        "noise_thr": None,
        "median_filter_passes": 0,
        "use_camera_wb": True,
        "use_auto_wb": False,
        "user_wb": None,
        "output_color": rawpy.ColorSpace.ProPhoto,
        "output_bps": 16,
        "user_flip": 0,
        "user_black": 0,
        "user_cblack": black_levels,
        "user_sat": white_level,
        "no_auto_bright": True,
        "auto_bright_thr": None,
        "adjust_maximum_thr": 0.0,
        "bright": 1.0,
        "highlight_mode": rawpy.HighlightMode.Clip,
        "exp_shift": None,
        "exp_preserve_highlights": 0.0,
        "no_auto_scale": False,
        "gamma": (1.0, 1.0),
        "chromatic_aberration": None,
        "bad_pixels_path": None,
    }


def read_camera_metadata(source_path: Path) -> dict[str, Any]:
    exiftool_name = shutil.which("exiftool")
    if exiftool_name is None:
        raise ContractFailure("EXIFTOOL_ABSENT", "ExifTool is required")
    command = [
        exiftool_name,
        "-j",
        "-n",
        "-Make",
        "-Model",
        "-ISO",
        "-SerialNumber",
        "-ExposureTime",
        "-FNumber",
        "-LensModel",
        "-FocalLength",
        "-FocusDistance",
        "-CameraTemperature",
        str(source_path),
    ]
    try:
        completed = subprocess.run(
            command, check=True, capture_output=True, text=True
        )
        records = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise ContractFailure("CAMERA_METADATA_FAILED", str(exc)) from exc
    if not isinstance(records, list) or len(records) != 1:
        raise ContractFailure("CAMERA_METADATA_FAILED", "ExifTool returned no unique record")
    record = records[0]
    required = ["Make", "Model", "ISO", "ExposureTime", "FNumber", "LensModel", "FocalLength"]
    if any(record.get(field) is None for field in required):
        raise ContractFailure(
            "CAMERA_METADATA_INCOMPLETE",
            f"required capture metadata is absent; required fields are {required}",
        )
    return {
        "make": str(record["Make"]),
        "model": str(record["Model"]),
        "iso_speed": float(record["ISO"]),
        "serial_number": (
            str(record["SerialNumber"]) if record.get("SerialNumber") is not None else None
        ),
        "exposure_time_s": float(record["ExposureTime"]),
        "f_number": float(record["FNumber"]),
        "lens_model": str(record["LensModel"]),
        "focal_length_mm": float(record["FocalLength"]),
        "focus_distance_m": (
            float(record["FocusDistance"])
            if record.get("FocusDistance") is not None
            else None
        ),
        "camera_temperature_c": (
            float(record["CameraTemperature"])
            if record.get("CameraTemperature") is not None
            else None
        ),
    }


def sensor_fingerprint(raw: Any) -> dict[str, Any]:
    pattern = raw.raw_pattern
    return {
        "active_shape": [int(v) for v in raw.raw_image_visible.shape],
        "raw_shape": [int(raw.sizes.raw_height), int(raw.sizes.raw_width)],
        "black_levels": [int(value) for value in raw.black_level_per_channel],
        "white_levels": [
            int(value)
            for value in (
                raw.camera_white_level_per_channel
                or [int(raw.white_level)] * 4
            )
        ],
        "raw_pattern": pattern.tolist() if pattern is not None else None,
        "color_description": bytes(raw.color_desc).rstrip(b"\0").decode("ascii"),
    }


def raw_metadata(raw: Any, camera_metadata: dict[str, Any]) -> dict[str, Any]:
    np, _ = import_runtime()
    camera_whitebalance = [float(value) for value in raw.camera_whitebalance]
    black = [int(value) for value in raw.black_level_per_channel]
    camera_whites = raw.camera_white_level_per_channel
    whites = [int(value) for value in camera_whites] if camera_whites else []
    if not whites or any(value <= 0 for value in whites):
        whites = [int(raw.white_level)] * 4
    matrix = np.asarray(raw.rgb_xyz_matrix, dtype=np.float64)
    return {
        "camera": camera_metadata,
        "sensor_fingerprint": sensor_fingerprint(raw),
        "active_width": int(raw.sizes.width),
        "active_height": int(raw.sizes.height),
        "raw_width": int(raw.sizes.raw_width),
        "raw_height": int(raw.sizes.raw_height),
        "top_margin": int(raw.sizes.top_margin),
        "left_margin": int(raw.sizes.left_margin),
        "black_levels": black,
        "white_levels": whites,
        "camera_whitebalance": camera_whitebalance,
        "rgb_xyz_matrix": matrix.tolist(),
    }


def render(args: argparse.Namespace) -> dict[str, Any]:
    settings_path = Path(args.settings)
    icc_path = Path(args.icc)
    freeze_path = Path(args.freeze)
    source_path = Path(args.input)
    output_path = Path(args.output)
    pattern_path = Path(args.pattern_map)
    pattern_manifest_path = Path(args.pattern_manifest)
    consumer_registry_path = Path(args.consumer_registry)
    settings = validate_settings(settings_path)
    freeze = verify_freeze(freeze_path, settings_path, icc_path)
    consumer_registry = validate_consumer_registry(consumer_registry_path)
    consumer_registry_sha = hash_file(consumer_registry_path)
    if not pattern_path.is_file() or not pattern_manifest_path.is_file():
        raise ContractFailure(
            "PATTERN_MAP_REQUIRED",
            "common-merge rendering is forbidden without a frozen matching dark/flat pattern map",
        )
    if not source_path.is_file():
        raise ContractFailure("SOURCE_ABSENT", f"RAW source does not exist: {source_path}")

    np, rawpy = import_runtime()
    source_sha = hash_file(source_path)
    camera_metadata = read_camera_metadata(source_path)
    with rawpy.imread(str(source_path)) as raw:
        metadata = raw_metadata(raw, camera_metadata)
        pattern, gain, offset = validate_pattern_manifest(
            pattern_manifest_path,
            pattern_path,
            raw,
            camera_metadata,
            source_sha,
            source_path,
        )
        black = metadata["black_levels"]
        whites = metadata["white_levels"]
        if len(set(whites)) != 1:
            raise ContractFailure(
                "PER_CHANNEL_WHITE_UNSUPPORTED",
                f"rawpy exposes only scalar user_sat; channel whites are {whites}",
            )
        corrected = apply_pattern_correction(
            raw.raw_image_visible,
            raw.raw_colors_visible,
            black,
            whites,
            gain,
            offset,
        )
        raw.raw_image_visible[:] = corrected
        rgb = raw.postprocess(**postprocess_kwargs(rawpy, black, whites[0]))
    if rgb.dtype != np.uint16:
        raise ContractFailure("LIBRAW_OUTPUT_TYPE", f"LibRaw returned {rgb.dtype}, not uint16")
    if list(rgb.shape) != [metadata["active_height"], metadata["active_width"], 3]:
        raise ContractFailure(
            "LIBRAW_OUTPUT_DIMENSIONS",
            f"LibRaw returned {list(rgb.shape)}, expected native active "
            f"[{metadata['active_height']},{metadata['active_width']},3]",
        )

    settings_sha = hash_file(settings_path)
    icc = icc_path.read_bytes()
    map_sha = hash_file(pattern_path)
    pattern_manifest_sha = hash_file(pattern_manifest_path)
    converter_sha = freeze["converter"]["executable_bundle_sha256"]
    provenance = {
        "schema": "m165-common-input-provenance-v1",
        "source_sha256": source_sha,
        "converter_executable_sha256": converter_sha,
        "settings_sha256": settings_sha,
        "icc_sha256": hash_bytes(icc),
        "pattern_map_sha256": map_sha,
        "pattern_manifest_sha256": pattern_manifest_sha,
    }
    written = write_common_tiff(output_path, rgb, icc, provenance)
    inspected = inspect_common_tiff(output_path)
    if (
        written["file_sha256"] != inspected["file_sha256"]
        or written["pixel_payload_sha256"] != inspected["pixel_payload_sha256"]
    ):
        output_path.unlink(missing_ok=True)
        raise ContractFailure(
            "TIFF_SELF_INSPECTION_MISMATCH", "written TIFF does not independently re-parse"
        )

    return {
        "schema": MANIFEST_SCHEMA,
        "status": "RENDERED",
        "track": "common-merge",
        "source": {
            "path": str(source_path.resolve()),
            "sha256": source_sha,
            "metadata": metadata,
        },
        "converter": {
            "id": CONVERTER_ID,
            "version": CONVERTER_VERSION,
            "executable_sha256": converter_sha,
            "freeze_path": str(freeze_path.resolve()),
            "freeze_sha256": hash_file(freeze_path),
            "settings": settings,
            "settings_sha256": settings_sha,
            "complete_invocation": [sys.executable, str(Path(__file__).resolve())] + sys.argv[1:],
            "working_directory": str(Path.cwd()),
        },
        "pattern_map": {
            "path": str(pattern_path.resolve()),
            "sha256": map_sha,
            "manifest_path": str(pattern_manifest_path.resolve()),
            "manifest_sha256": pattern_manifest_sha,
            "manifest": pattern,
        },
        # Consumer identity belongs in the manifest, not the TIFF. Keeping the
        # roster out of ImageDescription means adding a comparator cannot alter
        # the common bytes every consumer is required to receive.
        "consumer_registry": {
            "path": str(consumer_registry_path.resolve()),
            "sha256": consumer_registry_sha,
            **consumer_registry,
            "receipt_schema": CONSUMER_RECEIPT_SCHEMA,
        },
        "output": {
            "path": str(output_path.resolve()),
            "width": inspected["width"],
            "height": inspected["height"],
            "bits_per_sample": inspected["bits_per_sample"],
            "sample_format": inspected["sample_format"],
            "compression": inspected["compression"],
            "photometric": inspected["photometric"],
            "planar_configuration": inspected["planar_configuration"],
            "rows_per_strip": inspected["rows_per_strip"],
            "strip_count": inspected["strip_count"],
            "pixel_payload_sha256": inspected["pixel_payload_sha256"],
            "file_sha256": inspected["file_sha256"],
            "icc_sha256": inspected["icc_sha256"],
        },
    }


def failure_record(exc: BaseException, schema: str = MANIFEST_SCHEMA) -> dict[str, Any]:
    if isinstance(exc, ContractFailure):
        failure_class = exc.failure_class
    else:
        failure_class = "UNEXPECTED_EXCEPTION"
    return {
        "schema": schema,
        "status": "FAIL",
        "failure_class": failure_class,
        "reason": str(exc),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    icc = subparsers.add_parser("write-icc")
    icc.add_argument("--out", required=True)

    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--settings", required=True)
    freeze.add_argument("--icc", required=True)
    freeze.add_argument("--out", required=True)

    inspect = subparsers.add_parser("inspect-tiff")
    inspect.add_argument("--input", required=True)
    inspect.add_argument("--out", required=True)

    consumers = subparsers.add_parser("verify-consumers")
    consumers.add_argument("--registry", required=True)
    consumers.add_argument("--out", required=True)

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--input", required=True)
    render_parser.add_argument("--output", required=True)
    render_parser.add_argument("--manifest", required=True)
    render_parser.add_argument("--settings", required=True)
    render_parser.add_argument("--icc", required=True)
    render_parser.add_argument("--freeze", required=True)
    render_parser.add_argument("--pattern-map", required=True)
    render_parser.add_argument("--pattern-manifest", required=True)
    render_parser.add_argument("--consumer-registry", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path: Path | None = None
    try:
        if args.command == "write-icc":
            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(build_linear_prophoto_icc())
            result = {
                "status": "PASS",
                "path": str(path.resolve()),
                "sha256": hash_file(path),
                "bytes": path.stat().st_size,
            }
        elif args.command == "freeze":
            report_path = Path(args.out)
            result = build_freeze(Path(args.settings), Path(args.icc))
            result["complete_freeze_invocation"] = [
                sys.executable,
                str(Path(__file__).resolve()),
            ] + sys.argv[1:]
            result["working_directory"] = str(Path.cwd())
            write_json(report_path, result)
        elif args.command == "inspect-tiff":
            report_path = Path(args.out)
            result = inspect_common_tiff(Path(args.input))
            write_json(report_path, result)
        elif args.command == "verify-consumers":
            report_path = Path(args.out)
            registry_path = Path(args.registry)
            result = {
                **validate_consumer_registry(registry_path),
                "registry_path": str(registry_path.resolve()),
                "registry_sha256": hash_file(registry_path),
            }
            write_json(report_path, result)
        elif args.command == "render":
            report_path = Path(args.manifest)
            result = render(args)
            write_json(report_path, result)
        else:
            raise ContractFailure("COMMAND_INVALID", str(args.command))
        print(json.dumps(result, sort_keys=True))
        return 0
    except BaseException as exc:
        failure_schema = (
            CONSUMER_REGISTRY_SCHEMA
            if args.command == "verify-consumers"
            else MANIFEST_SCHEMA
        )
        result = failure_record(exc, failure_schema)
        if report_path is not None:
            try:
                write_json(report_path, result)
            except BaseException as write_exc:
                result["report_write_failure"] = str(write_exc)
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
