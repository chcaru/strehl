"""Independently verify the frozen M171 synthetic commission artifact."""

from __future__ import annotations

import argparse
import ast
import base64
import copy
import hashlib
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np


FROZEN_CONTRACT_SHA256 = (
    "3530035E986B35118731FB2249EB95C32DEC372AA36AFD4F3B1B989F743D1DEF"
)
FROZEN_ADMISSION_SOURCE_SHA256 = (
    "4DD848C833E537A6A15DBD20D68E792C63C0A11D857B7D68E55BF4B92D387C78"
)
FROZEN_COMMISSION_SOURCE_SHA256 = (
    "D3A65FC2C8F5E0CFE27F80A012B46DEA8C505F382B7D45C76316B2237E151E90"
)
FROZEN_SYNTHETIC_SOURCE_SHA256 = (
    "7C886E09E1041BD7EBA2C80223CF82D58C954834E6EBDAD70489D6E4F54B767F"
)
INITIAL_PREREGISTRATION_COMMIT = "15f5a84e"
INITIAL_PREREGISTRATION_COMMIT_FULL = (
    "15f5a84ea348f36698209383c6dccbc0a9da95d3"
)
AMENDMENT_ONE_COMMIT = "2adf1a8a"
AMENDMENT_ONE_COMMIT_FULL = "2adf1a8a26bd31927084cf2344ede1c34c514ed1"
AMENDMENT_TWO_COMMIT = "e13e2274"
AMENDMENT_TWO_COMMIT_FULL = "e13e2274be5ff997ea46cc75c840a47f961e9061"
AMENDMENT_THREE_COMMIT = "75259ef0"
AMENDMENT_THREE_COMMIT_FULL = (
    "75259ef0084d3c36d44861b50c0b6b387db502b8"
)
VERIFICATION_SCHEMA = "m171-reference-admission-verification-v4"
EMBEDDED_EVIDENCE_SCHEMA = "m171-reference-admission-embedded-evidence-v1"
HERE = pathlib.Path(__file__).resolve().parent
REL_TOL = 1.0e-12
ABS_TOL = 1.0e-12
SHA256_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
SCIENTIFIC_STATUSES = ("PASS", "UNMEASURED")
PATHS = ("R1", "R2", "S1", "S2")
SPLITS = (
    "odd_even",
    "contiguous_halves",
    "alternating_four_frame_blocks",
)
CONTROLS = ("featureless", "flat", "dark")
GZIP_COMPRESSION_LEVEL = 9
MAX_EMBEDDED_EVIDENCE_BYTES = 64 * 1024 * 1024
LOWER_BOUND_QUANTILE = 0.975
LINE_ENDING_POLICY = "LF"
EXPERIMENT_PREFIX = "experiments/M171-reference-admission"
ATTRIBUTE_PATHS = (
    f"{EXPERIMENT_PREFIX}/.gitattributes",
    f"{EXPERIMENT_PREFIX}/PREREGISTRATION.md",
    f"{EXPERIMENT_PREFIX}/admission.py",
    f"{EXPERIMENT_PREFIX}/commission.py",
    f"{EXPERIMENT_PREFIX}/synthetic.py",
    f"{EXPERIMENT_PREFIX}/test_admission.py",
    f"{EXPERIMENT_PREFIX}/verify.py",
    f"{EXPERIMENT_PREFIX}/contract.json",
    f"{EXPERIMENT_PREFIX}/out/commission.json",
    f"{EXPERIMENT_PREFIX}/out/verification.json",
)
_PROTECTED_OUTPUT_RELATIVE_PATHS = (
    ".gitattributes",
    "PREREGISTRATION.md",
    "contract.json",
    "admission.py",
    "synthetic.py",
    "commission.py",
    "test_admission.py",
    "verify.py",
    "out/commission.json",
)


class HarnessError(RuntimeError):
    """An input could not be safely sealed, parsed, or written."""


class VerificationError(ValueError):
    """A check could not interpret the retained verification evidence."""


@dataclass
class CheckContext:
    errors: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def expect(self, condition: bool, message: str) -> None:
        if not condition and len(self.errors) < 100:
            self.errors.append(message)

    def equal(self, actual: Any, expected: Any, path: str) -> None:
        self.expect(actual == expected, f"{path}: expected {expected!r}, got {actual!r}")

    def close(self, actual: Any, expected: Any, path: str) -> None:
        observed = _number(actual, path)
        target = _number(expected, f"{path} expected")
        self.expect(
            math.isclose(observed, target, rel_tol=REL_TOL, abs_tol=ABS_TOL),
            f"{path}: expected {target:.17g}, got {observed:.17g}",
        )


class CheckRegistry:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self._ids: set[str] = set()

    def run(
        self,
        check_id: str,
        summary: str,
        function: Callable[[CheckContext], None],
    ) -> CheckContext:
        if check_id in self._ids:
            raise HarnessError(f"duplicate verification check id: {check_id}")
        self._ids.add(check_id)
        context = CheckContext()
        try:
            function(context)
        except (
            VerificationError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
            IndexError,
        ) as exc:
            context.errors.append(f"uncheckable retained evidence: {exc}")
        record: dict[str, Any] = {
            "id": check_id,
            "status": "PASS" if not context.errors else "FAIL",
            "summary": summary,
        }
        if context.evidence:
            record["evidence"] = context.evidence
        if context.errors:
            record["errors"] = context.errors
        self.records.append(record)
        return context

    def partition(self) -> dict[str, int]:
        passed = sum(record["status"] == "PASS" for record in self.records)
        failed = sum(record["status"] == "FAIL" for record in self.records)
        total = len(self.records)
        return {
            "PASS": passed,
            "FAIL": failed,
            "PASS_plus_FAIL": passed + failed,
            "total": total,
            "skipped": 0,
        }


def _strip_windows_extended_prefix(value: str) -> str:
    if os.name != "nt":
        return value
    normalized = value.replace("/", "\\")
    folded = normalized.casefold()
    if folded.startswith("\\\\?\\unc\\"):
        return "\\\\" + normalized[8:]
    if folded.startswith("\\\\?\\"):
        return normalized[4:]
    return normalized


def _path_key(path: os.PathLike[str] | str) -> str:
    value = _strip_windows_extended_prefix(os.fspath(path))
    normalized = os.path.normpath(value)
    if os.name == "nt":
        return os.path.normcase(normalized).casefold()
    return normalized


def _stat_exists(path: pathlib.Path, purpose: str) -> bool:
    try:
        os.stat(path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as exc:
        raise HarnessError(
            f"cannot establish {purpose} filesystem identity"
        ) from exc
    return True


def _paths_identical(
    candidate: os.PathLike[str] | str,
    protected: os.PathLike[str] | str,
) -> bool:
    try:
        candidate_path = pathlib.Path(candidate).expanduser().resolve(
            strict=False
        )
        protected_path = pathlib.Path(protected).expanduser().resolve(
            strict=False
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise HarnessError(
            "cannot resolve verification output identity"
        ) from exc
    candidate_key = _path_key(candidate_path)
    protected_key = _path_key(protected_path)
    candidate_exists = _stat_exists(
        candidate_path, "verification output path"
    )
    protected_exists = _stat_exists(
        protected_path, "protected output target"
    )
    if candidate_exists and protected_exists:
        try:
            same_file = os.path.samefile(
                candidate_path, protected_path
            )
        except (OSError, ValueError) as exc:
            if candidate_key == protected_key:
                return True
            raise HarnessError(
                "cannot establish verification output filesystem identity"
            ) from exc
        return same_file or candidate_key == protected_key
    return candidate_key == protected_key


def _reject_d_drive(value: os.PathLike[str] | str, purpose: str) -> pathlib.Path:
    raw = os.fspath(value)
    drive, _ = os.path.splitdrive(_strip_windows_extended_prefix(raw))
    if drive.casefold() == "d:":
        raise HarnessError(f"{purpose} must not use the prohibited D: drive")
    try:
        resolved = pathlib.Path(raw).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise HarnessError(f"cannot resolve {purpose}: {exc}") from exc
    resolved_drive, _ = os.path.splitdrive(
        _strip_windows_extended_prefix(os.fspath(resolved))
    )
    if resolved_drive.casefold() == "d:":
        raise HarnessError(f"{purpose} must not resolve to the prohibited D: drive")
    return resolved


def _protected_output_paths(
    contract_path: pathlib.Path,
    commission_path: pathlib.Path,
) -> list[tuple[pathlib.Path, str]]:
    protected = [
        (contract_path, "contract input"),
        (commission_path, "commission input"),
    ]
    protected.extend(
        (
            (HERE / relative).resolve(strict=False),
            relative,
        )
        for relative in _PROTECTED_OUTPUT_RELATIVE_PATHS
    )
    return protected


def _safe_verification_output(
    output: os.PathLike[str] | str,
    contract_path: pathlib.Path,
    commission_path: pathlib.Path,
) -> pathlib.Path:
    resolved = _reject_d_drive(output, "verification output path")
    for protected_path, label in _protected_output_paths(
        contract_path, commission_path
    ):
        if _paths_identical(resolved, protected_path):
            raise HarnessError(
                "verification output must not overwrite protected input "
                f"{label}"
            )
    return resolved


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HarnessError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise HarnessError(f"non-finite JSON number: {value}")


def _reject_nonfinite_tree(value: Any, path: str = "$") -> None:
    if type(value) is float and not math.isfinite(value):
        raise HarnessError(f"non-finite JSON number at {path}")
    if isinstance(value, Mapping):
        for key, member in value.items():
            _reject_nonfinite_tree(member, f"{path}.{key}")
    elif isinstance(value, list):
        for index, member in enumerate(value):
            _reject_nonfinite_tree(member, f"{path}[{index}]")


def _read_sealed_json_once(
    path: pathlib.Path,
    expected_sha256: str,
    purpose: str,
) -> tuple[dict[str, Any], bytes, str]:
    if not isinstance(expected_sha256, str) or not SHA256_RE.fullmatch(
        expected_sha256
    ):
        raise HarnessError(f"{purpose} expected SHA-256 is not 64 hexadecimal digits")
    try:
        with path.open("rb") as stream:
            payload = stream.read()
    except OSError as exc:
        raise HarnessError(f"cannot read {purpose}: {exc}") from exc
    actual_sha256 = _sha256(payload)
    if actual_sha256 != expected_sha256.upper():
        raise HarnessError(
            f"{purpose} SHA-256 mismatch: expected {expected_sha256.upper()}, "
            f"got {actual_sha256}"
        )
    if payload.startswith(b"\xef\xbb\xbf"):
        raise HarnessError(f"{purpose} must not contain a UTF-8 BOM")
    if b"\r" in payload:
        raise HarnessError(
            f"{purpose} must use LF line endings without carriage returns"
        )
    try:
        decoded = payload.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_json_constant,
        )
    except HarnessError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessError(f"invalid {purpose} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise HarnessError(f"{purpose} JSON root must be an object")
    _reject_nonfinite_tree(value)
    return value, payload, actual_sha256


def _read_bytes_once(path: pathlib.Path, purpose: str) -> bytes:
    try:
        with path.open("rb") as stream:
            return stream.read()
    except OSError as exc:
        raise HarnessError(f"cannot read {purpose}: {exc}") from exc


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationError(f"{path} must be an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise VerificationError(f"{path} must be an array")
    return value


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise VerificationError(f"{path} must be a nonempty string")
    return value


def _boolean(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise VerificationError(f"{path} must be a JSON boolean")
    return value


def _number(value: Any, path: str) -> float:
    if type(value) not in (int, float):
        raise VerificationError(f"{path} must be a JSON number, not boolean")
    result = float(value)
    if not math.isfinite(result):
        raise VerificationError(f"{path} must be finite")
    return result


def _optional_number(value: Any, path: str) -> float | None:
    if value is None:
        return None
    return _number(value, path)


def _integer(value: Any, path: str) -> int:
    if type(value) is not int:
        raise VerificationError(f"{path} must be a JSON integer, not boolean")
    return value


def _hash(value: Any, path: str) -> str:
    text = _string(value, path)
    if not SHA256_RE.fullmatch(text):
        raise VerificationError(f"{path} must be a 64-character SHA-256")
    return text.upper()


def _expect_keys(
    context: CheckContext,
    value: Mapping[str, Any],
    expected: Sequence[str] | set[str],
    path: str,
) -> None:
    actual = set(value)
    wanted = set(expected)
    context.expect(
        actual == wanted,
        f"{path} members differ: missing={sorted(wanted - actual)}, "
        f"unknown={sorted(actual - wanted)}",
    )


def _require_keys(
    value: Any,
    expected: Sequence[str] | set[str],
    path: str,
    optional: Sequence[str] | set[str] = (),
) -> Mapping[str, Any]:
    obj = _mapping(value, path)
    required = set(expected)
    allowed = required | set(optional)
    missing = sorted(required - set(obj))
    unknown = sorted(set(obj) - allowed)
    if missing or unknown:
        raise VerificationError(
            f"{path} members differ: missing={missing}, unknown={unknown}"
        )
    return obj


def _parse_embedded_json(payload: bytes, purpose: str) -> dict[str, Any]:
    try:
        decoded = payload.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_json_constant,
        )
    except HarnessError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessError(f"invalid {purpose} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise HarnessError(f"{purpose} JSON root must be an object")
    _reject_nonfinite_tree(value)
    return value


def _gunzip_embedded(
    compressed: bytes,
    expected_length: int,
    case_name: str,
) -> bytes:
    if expected_length < 1 or expected_length > MAX_EMBEDDED_EVIDENCE_BYTES:
        raise HarnessError(
            f"{case_name} embedded evidence uncompressed length is out of range"
        )
    if (
        len(compressed) < 18
        or compressed[:3] != b"\x1f\x8b\x08"
        or compressed[3] != 0
        or compressed[4:8] != b"\x00\x00\x00\x00"
    ):
        raise HarnessError(
            f"{case_name} embedded evidence is not one deterministic gzip stream"
        )
    try:
        inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
        payload = inflater.decompress(compressed, expected_length + 1)
        payload += inflater.flush()
    except zlib.error as exc:
        raise HarnessError(
            f"{case_name} embedded evidence gzip is invalid: {exc}"
        ) from exc
    if (
        not inflater.eof
        or inflater.unused_data
        or inflater.unconsumed_tail
        or len(payload) != expected_length
    ):
        raise HarnessError(
            f"{case_name} embedded evidence gzip length or stream boundary is invalid"
        )
    return payload


def _decode_embedded_evidence(
    case: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    case_name = _string(case["case"], "commission case name")
    envelope = _require_keys(
        case["embedded_evidence"],
        (
            "schema",
            "encoding",
            "compression",
            "compression_level",
            "gzip_mtime",
            "identity",
            "uncompressed_length_bytes",
            "uncompressed_sha256",
            "compressed_length_bytes",
            "compressed_sha256",
            "payload",
        ),
        f"{case_name}.embedded_evidence",
    )
    if envelope["schema"] != EMBEDDED_EVIDENCE_SCHEMA:
        raise HarnessError(f"{case_name} embedded evidence schema is unsupported")
    if envelope["encoding"] != "base64":
        raise HarnessError(f"{case_name} embedded evidence encoding is unsupported")
    if envelope["compression"] != "gzip":
        raise HarnessError(
            f"{case_name} embedded evidence compression is unsupported"
        )
    if (
        _integer(
            envelope["compression_level"],
            f"{case_name}.embedded_evidence.compression_level",
        )
        != GZIP_COMPRESSION_LEVEL
        or _integer(
            envelope["gzip_mtime"],
            f"{case_name}.embedded_evidence.gzip_mtime",
        )
        != 0
    ):
        raise HarnessError(
            f"{case_name} embedded evidence gzip parameters are not deterministic"
        )
    identity = _require_keys(
        envelope["identity"],
        ("case", "evidence_schema", "claim_scope"),
        f"{case_name}.embedded_evidence.identity",
    )
    expected_evidence_schema = _string(
        _mapping(contract["schemas"], "contract.schemas")["evidence"],
        "contract.schemas.evidence",
    )
    expected_claim_scope = _string(contract["claim_scope"], "contract.claim_scope")
    if (
        identity["case"] != case_name
        or identity["evidence_schema"] != expected_evidence_schema
        or identity["claim_scope"] != expected_claim_scope
        or case["claim_scope"] != expected_claim_scope
    ):
        raise HarnessError(f"{case_name} embedded evidence identity is not bound")

    encoded = _string(
        envelope["payload"], f"{case_name}.embedded_evidence.payload"
    )
    try:
        encoded_bytes = encoded.encode("ascii")
        compressed = base64.b64decode(encoded_bytes, validate=True)
    except (UnicodeEncodeError, ValueError) as exc:
        raise HarnessError(
            f"{case_name} embedded evidence base64 is invalid"
        ) from exc
    if base64.b64encode(compressed) != encoded_bytes:
        raise HarnessError(
            f"{case_name} embedded evidence base64 is not canonical"
        )
    compressed_length = _integer(
        envelope["compressed_length_bytes"],
        f"{case_name}.embedded_evidence.compressed_length_bytes",
    )
    if compressed_length != len(compressed):
        raise HarnessError(
            f"{case_name} embedded evidence compressed length mismatch"
        )
    compressed_sha256 = _hash(
        envelope["compressed_sha256"],
        f"{case_name}.embedded_evidence.compressed_sha256",
    )
    actual_compressed_sha256 = _sha256(compressed)
    if compressed_sha256 != actual_compressed_sha256:
        raise HarnessError(
            f"{case_name} embedded evidence compressed SHA-256 mismatch"
        )
    uncompressed_length = _integer(
        envelope["uncompressed_length_bytes"],
        f"{case_name}.embedded_evidence.uncompressed_length_bytes",
    )
    payload = _gunzip_embedded(compressed, uncompressed_length, case_name)
    uncompressed_sha256 = _hash(
        envelope["uncompressed_sha256"],
        f"{case_name}.embedded_evidence.uncompressed_sha256",
    )
    evidence_sha256 = _hash(
        case["evidence_sha256"], f"{case_name}.evidence_sha256"
    )
    actual_uncompressed_sha256 = _sha256(payload)
    if not (
        uncompressed_sha256
        == evidence_sha256
        == actual_uncompressed_sha256
    ):
        raise HarnessError(
            f"{case_name} embedded evidence uncompressed SHA-256 mismatch"
        )
    evidence = _parse_embedded_json(payload, f"{case_name} embedded evidence")
    if (
        evidence.get("schema") != expected_evidence_schema
        or evidence.get("claim_scope") != expected_claim_scope
    ):
        raise HarnessError(
            f"{case_name} embedded evidence payload identity is wrong"
        )
    metadata = {
        "case": case_name,
        "compressed_length_bytes": compressed_length,
        "compressed_sha256": compressed_sha256,
        "uncompressed_length_bytes": uncompressed_length,
        "uncompressed_sha256": uncompressed_sha256,
        "encoding": "base64+gzip(mtime=0)",
    }
    return evidence, payload, metadata


def _object_array(value: Any, shape: tuple[int, ...], path: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=object)
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"{path} is not a rectangular array") from exc
    if array.shape != shape:
        raise VerificationError(
            f"{path} has shape {array.shape}; expected {shape}"
        )
    return array


def _real_array(value: Any, shape: tuple[int, ...], path: str) -> np.ndarray:
    source = _object_array(value, shape, path)
    result = np.empty(shape, dtype=np.float64)
    for index, item in np.ndenumerate(source):
        result[index] = _number(item, f"{path}{index}")
    return result


def _complex_array(
    value: Any,
    shape: tuple[int, ...],
    path: str,
) -> np.ndarray:
    encoded = _real_array(value, shape + (2,), path)
    return encoded[..., 0] + 1j * encoded[..., 1]


def _string_array(value: Any, length: int, path: str) -> list[str]:
    source = _object_array(value, (length,), path)
    return [_string(item, f"{path}[{index}]") for index, item in enumerate(source)]


LINEAGE_FIELDS = (
    "evidence_generation_sha256",
    "claim_scope_sha256",
    "sampling_sha256",
    "focus_known_input_sha256",
    "raw_response_known_input_sha256",
    "split_sha256",
    "geometry_sha256",
    "resampler_sha256",
    "nonperiodic_sha256",
    "featureless_control_sha256",
    "flat_control_sha256",
    "dark_control_sha256",
    "R1_source_sha256",
    "R2_source_sha256",
    "S1_source_sha256",
    "S2_source_sha256",
    "R1_calibration_sha256",
    "R2_calibration_sha256",
    "S1_calibration_sha256",
    "S2_calibration_sha256",
)


def _prepare_sites(
    value: Any,
    contract: Mapping[str, Any],
) -> tuple[list[dict[str, str]], list[list[np.ndarray]]]:
    sample = _mapping(contract["sample_contract"], "contract.sample_contract")
    expected_count = _integer(sample["site_count"], "contract site count")
    source = _object_array(value, (expected_count,), "evidence.sites")
    sites: list[dict[str, str]] = []
    site_ids: set[str] = set()
    burst_sessions: dict[str, str] = {}
    grouped: dict[str, dict[str, list[int]]] = {}
    for index, raw in enumerate(source):
        site = _require_keys(
            raw,
            ("site_id", "session_id", "burst_id"),
            f"evidence.sites[{index}]",
        )
        site_id = _string(site["site_id"], f"evidence.sites[{index}].site_id")
        session_id = _string(
            site["session_id"], f"evidence.sites[{index}].session_id"
        )
        burst_id = _string(
            site["burst_id"], f"evidence.sites[{index}].burst_id"
        )
        if site_id in site_ids:
            raise VerificationError(f"duplicate evidence site id {site_id}")
        site_ids.add(site_id)
        prior = burst_sessions.setdefault(burst_id, session_id)
        if prior != session_id:
            raise VerificationError(
                f"evidence burst {burst_id} occurs in multiple sessions"
            )
        grouped.setdefault(session_id, {}).setdefault(burst_id, []).append(index)
        sites.append(
            {
                "site_id": site_id,
                "session_id": session_id,
                "burst_id": burst_id,
            }
        )
    session_count = _integer(sample["session_count"], "contract session count")
    burst_count = _integer(
        sample["bursts_per_session"], "contract bursts per session"
    )
    sites_per_burst = _integer(
        sample["sites_per_burst"], "contract sites per burst"
    )
    if len(grouped) != session_count:
        raise VerificationError("evidence session hierarchy count is wrong")
    hierarchy: list[list[np.ndarray]] = []
    for session_id in sorted(grouped):
        bursts = grouped[session_id]
        if len(bursts) != burst_count:
            raise VerificationError(
                f"evidence session {session_id} has the wrong burst count"
            )
        session_groups: list[np.ndarray] = []
        for burst_id in sorted(bursts):
            indices = bursts[burst_id]
            if len(indices) != sites_per_burst:
                raise VerificationError(
                    f"evidence burst {burst_id} has the wrong site count"
                )
            session_groups.append(np.asarray(indices, dtype=np.intp))
        hierarchy.append(session_groups)
    return sites, hierarchy


def _prepare_control_paths(
    value: Any,
    path: str,
    site_count: int,
    dimension: int,
) -> dict[str, np.ndarray]:
    obj = _require_keys(value, PATHS, path)
    return {
        name: _complex_array(
            obj[name], (site_count, dimension), f"{path}.{name}"
        )
        for name in PATHS
    }


def _prepare_split_pair(
    value: Any,
    path: str,
    site_count: int,
    dimension: int,
) -> dict[str, Any]:
    obj = _require_keys(value, ("first", "second", "controls"), path)
    controls_obj = _require_keys(
        obj["controls"], CONTROLS, f"{path}.controls"
    )
    controls: dict[str, dict[str, np.ndarray]] = {}
    for control_name in CONTROLS:
        pair = _require_keys(
            controls_obj[control_name],
            ("first", "second"),
            f"{path}.controls.{control_name}",
        )
        controls[control_name] = {
            arm: _complex_array(
                pair[arm],
                (site_count, dimension),
                f"{path}.controls.{control_name}.{arm}",
            )
            for arm in ("first", "second")
        }
    return {
        "first": _complex_array(
            obj["first"], (site_count, dimension), f"{path}.first"
        ),
        "second": _complex_array(
            obj["second"], (site_count, dimension), f"{path}.second"
        ),
        "controls": controls,
    }


def _prepare_cell(
    value: Any,
    index: int,
    expected: Mapping[str, Any],
    site_count: int,
) -> dict[str, Any]:
    path = f"evidence.cells[{index}]"
    obj = _require_keys(
        value,
        (
            "id",
            "frequency",
            "orientation",
            "dimension",
            "coefficients",
            "controls",
            "focus",
            "split_pairs",
            "resampler",
        ),
        path,
    )
    cell_id = _string(obj["id"], f"{path}.id")
    frequency = _number(obj["frequency"], f"{path}.frequency")
    orientation = _number(obj["orientation"], f"{path}.orientation")
    dimension = _integer(obj["dimension"], f"{path}.dimension")
    if (
        cell_id != expected["id"]
        or frequency != float(expected["frequency"])
        or orientation != float(expected["orientation"])
        or dimension != int(expected["dimension"])
    ):
        raise VerificationError(f"{path} does not match the frozen cell")
    coefficients_obj = _require_keys(
        obj["coefficients"], PATHS, f"{path}.coefficients"
    )
    coefficients = {
        name: _complex_array(
            coefficients_obj[name],
            (site_count, dimension),
            f"{path}.coefficients.{name}",
        )
        for name in PATHS
    }
    controls_obj = _require_keys(
        obj["controls"], CONTROLS, f"{path}.controls"
    )
    controls = {
        name: _prepare_control_paths(
            controls_obj[name],
            f"{path}.controls.{name}",
            site_count,
            dimension,
        )
        for name in CONTROLS
    }
    focus_obj = _require_keys(
        obj["focus"],
        ("known_input", "positions", "transfer", "cross_cell_leakage"),
        f"{path}.focus",
    )
    positions = _real_array(
        focus_obj["positions"], (5,), f"{path}.focus.positions"
    )
    leakage = _real_array(
        focus_obj["cross_cell_leakage"],
        (site_count,),
        f"{path}.focus.cross_cell_leakage",
    )
    if not np.all(np.diff(positions) > 0.0) or np.any(leakage < 0.0):
        raise VerificationError(f"{path}.focus has an invalid domain")
    focus = {
        "known_input": _boolean(
            focus_obj["known_input"], f"{path}.focus.known_input"
        ),
        "positions": positions,
        "transfer": _complex_array(
            focus_obj["transfer"],
            (site_count, 5, dimension, dimension),
            f"{path}.focus.transfer",
        ),
        "cross_cell_leakage": leakage,
    }
    splits_obj = _require_keys(
        obj["split_pairs"], SPLITS, f"{path}.split_pairs"
    )
    split_pairs = {
        name: _prepare_split_pair(
            splits_obj[name],
            f"{path}.split_pairs.{name}",
            site_count,
            dimension,
        )
        for name in SPLITS
    }
    resampler_obj = _require_keys(
        obj["resampler"],
        ("kernel_a", "kernel_b"),
        f"{path}.resampler",
    )
    resampler = {
        name: _complex_array(
            resampler_obj[name],
            (site_count, dimension),
            f"{path}.resampler.{name}",
        )
        for name in ("kernel_a", "kernel_b")
    }
    return {
        "id": cell_id,
        "frequency": frequency,
        "orientation": orientation,
        "dimension": dimension,
        "coefficients": coefficients,
        "controls": controls,
        "focus": focus,
        "split_pairs": split_pairs,
        "resampler": resampler,
    }


def _canonical_sha256(value: Any) -> str:
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"value is not canonical finite JSON: {exc}") from exc
    return _sha256(payload)


def _prepare_q_baseline(
    value: Any,
    contract_cells: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    obj = _require_keys(
        value,
        ("schema", "payload", "payload_sha256"),
        "evidence.q_baseline",
    )
    if obj["schema"] != "m171-q-baseline-v1":
        raise VerificationError("evidence q baseline schema is wrong")
    payload = _require_keys(
        obj["payload"],
        ("cell_ids", "q"),
        "evidence.q_baseline.payload",
    )
    expected_ids = [str(cell["id"]) for cell in contract_cells]
    cell_ids = _string_array(
        payload["cell_ids"],
        len(expected_ids),
        "evidence.q_baseline.payload.cell_ids",
    )
    if cell_ids != expected_ids or len(set(cell_ids)) != len(cell_ids):
        raise VerificationError(
            "evidence q baseline cell order is not the frozen family"
        )
    q_obj = _require_keys(
        payload["q"],
        expected_ids,
        "evidence.q_baseline.payload.q",
    )
    q = {
        cell_id: _complex_array(
            q_obj[cell_id],
            (int(cell["dimension"]), int(cell["dimension"])),
            f"evidence.q_baseline.payload.q.{cell_id}",
        )
        for cell, cell_id in zip(contract_cells, expected_ids)
    }
    expected_q_hash = _hash(
        obj["payload_sha256"], "evidence.q_baseline.payload_sha256"
    )
    if _canonical_sha256(dict(payload)) != expected_q_hash:
        raise VerificationError("evidence q baseline payload hash is wrong")
    return {
        "schema": "m171-q-baseline-v1",
        "payload_sha256": expected_q_hash,
        "cell_ids": cell_ids,
        "q": q,
    }


def _prepare_evidence(
    evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    obj = _require_keys(
        evidence,
        (
            "schema",
            "claim_scope",
            "sites",
            "lineage",
            "reductions",
            "sampling",
            "cells",
            "raw_response",
            "geometry",
            "nonperiodic",
        ),
        "evidence",
        ("q_baseline",),
    )
    if obj["schema"] != contract["schemas"]["evidence"]:
        raise VerificationError("embedded evidence schema is unsupported")
    claim_scope = _string(obj["claim_scope"], "evidence.claim_scope")
    if claim_scope not in ("GX_REFERENCE_CONDITIONAL", "DIGITAL_K"):
        raise VerificationError("embedded evidence claim scope is wrong")
    sites, hierarchy = _prepare_sites(obj["sites"], contract)
    site_count = len(sites)
    lineage_obj = _require_keys(
        obj["lineage"], LINEAGE_FIELDS, "evidence.lineage"
    )
    lineage = {
        name: _hash(lineage_obj[name], f"evidence.lineage.{name}")
        for name in LINEAGE_FIELDS
    }
    reductions_obj = _require_keys(
        obj["reductions"], ("S1", "S2"), "evidence.reductions"
    )
    reductions: dict[str, Any] = {}
    reduction_sufficient = True
    for path_name in ("S1", "S2"):
        item = _require_keys(
            reductions_obj[path_name],
            (
                "complete",
                "candidate_blind",
                "linear",
                "source_sha256",
                "calibration_sha256",
                "reduction_sha256",
            ),
            f"evidence.reductions.{path_name}",
        )
        parsed = {
            "complete": _boolean(
                item["complete"], f"evidence.reductions.{path_name}.complete"
            ),
            "candidate_blind": _boolean(
                item["candidate_blind"],
                f"evidence.reductions.{path_name}.candidate_blind",
            ),
            "linear": _boolean(
                item["linear"], f"evidence.reductions.{path_name}.linear"
            ),
            "source_sha256": _hash(
                item["source_sha256"],
                f"evidence.reductions.{path_name}.source_sha256",
            ),
            "calibration_sha256": _hash(
                item["calibration_sha256"],
                f"evidence.reductions.{path_name}.calibration_sha256",
            ),
            "reduction_sha256": _hash(
                item["reduction_sha256"],
                f"evidence.reductions.{path_name}.reduction_sha256",
            ),
        }
        if (
            parsed["source_sha256"] != lineage[f"{path_name}_source_sha256"]
            or parsed["calibration_sha256"]
            != lineage[f"{path_name}_calibration_sha256"]
        ):
            raise VerificationError(
                f"evidence reduction {path_name} is not lineage-bound"
            )
        reduction_sufficient &= bool(
            parsed["complete"]
            and parsed["candidate_blind"]
            and parsed["linear"]
        )
        reductions[path_name] = parsed
    sampling_obj = _require_keys(
        obj["sampling"],
        ("input_only", "reference_magnification", "scored_magnification"),
        "evidence.sampling",
    )
    sampling = {
        "input_only": _boolean(
            sampling_obj["input_only"], "evidence.sampling.input_only"
        ),
        "reference_magnification": _real_array(
            sampling_obj["reference_magnification"],
            (site_count,),
            "evidence.sampling.reference_magnification",
        ),
        "scored_magnification": _real_array(
            sampling_obj["scored_magnification"],
            (site_count,),
            "evidence.sampling.scored_magnification",
        ),
    }
    if np.any(sampling["reference_magnification"] <= 0.0) or np.any(
        sampling["scored_magnification"] <= 0.0
    ):
        raise VerificationError("evidence sampling magnifications are not positive")
    contract_cells = _list(contract["cells"], "contract.cells")
    raw_cells = _list(obj["cells"], "evidence.cells")
    if len(raw_cells) != len(contract_cells):
        raise VerificationError("evidence cell count is wrong")
    raw_ids = [
        _string(_mapping(cell, "evidence cell").get("id"), "evidence cell id")
        for cell in raw_cells
    ]
    expected_ids = [str(cell["id"]) for cell in contract_cells]
    if len(set(raw_ids)) != len(raw_ids) or set(raw_ids) != set(expected_ids):
        raise VerificationError("evidence cell identity family is wrong")
    by_id = {str(cell["id"]): cell for cell in raw_cells}
    cells = [
        _prepare_cell(by_id[str(expected["id"])], index, expected, site_count)
        for index, expected in enumerate(contract_cells)
    ]
    response_obj = _require_keys(
        obj["raw_response"],
        (
            "known_input",
            "input_levels",
            "output_levels",
            "low_rail_hits",
            "high_rail_hits",
        ),
        "evidence.raw_response",
    )
    response = {
        "known_input": _boolean(
            response_obj["known_input"], "evidence.raw_response.known_input"
        ),
        "input_levels": _real_array(
            response_obj["input_levels"],
            (33,),
            "evidence.raw_response.input_levels",
        ),
        "output_levels": _real_array(
            response_obj["output_levels"],
            (33,),
            "evidence.raw_response.output_levels",
        ),
        "low_rail_hits": _integer(
            response_obj["low_rail_hits"],
            "evidence.raw_response.low_rail_hits",
        ),
        "high_rail_hits": _integer(
            response_obj["high_rail_hits"],
            "evidence.raw_response.high_rail_hits",
        ),
    }
    if (
        response["low_rail_hits"] < 0
        or response["high_rail_hits"] < 0
        or not np.all(np.diff(response["input_levels"]) > 0.0)
    ):
        raise VerificationError("evidence raw response domain is invalid")
    geometry_obj = _require_keys(
        obj["geometry"],
        (
            "input_only",
            "scored_pixels_native",
            "reference_only_resampling",
            "scale_disagreement_percent",
            "rotation_disagreement_deg",
            "nontranslation_rms_native_px",
            "planted_transform_sign",
            "estimated_transform_sign",
        ),
        "evidence.geometry",
    )
    geometry: dict[str, Any] = {
        name: _boolean(geometry_obj[name], f"evidence.geometry.{name}")
        for name in (
            "input_only",
            "scored_pixels_native",
            "reference_only_resampling",
        )
    }
    for name in (
        "scale_disagreement_percent",
        "rotation_disagreement_deg",
        "nontranslation_rms_native_px",
    ):
        geometry[name] = _real_array(
            geometry_obj[name], (site_count,), f"evidence.geometry.{name}"
        )
    for name in ("planted_transform_sign", "estimated_transform_sign"):
        source = _object_array(
            geometry_obj[name], (site_count,), f"evidence.geometry.{name}"
        )
        signs = np.empty(site_count, dtype=np.int8)
        for index, item in enumerate(source):
            sign = _integer(item, f"evidence.geometry.{name}[{index}]")
            if sign not in (-1, 1):
                raise VerificationError(
                    f"evidence.geometry.{name}[{index}] is not a sign"
                )
            signs[index] = sign
        geometry[name] = signs
    if np.any(geometry["nontranslation_rms_native_px"] < 0.0):
        raise VerificationError("evidence geometry RMS is negative")
    nonperiodic_obj = _require_keys(
        obj["nonperiodic"],
        ("concealed", "lineage_sha256", "site_ids"),
        "evidence.nonperiodic",
    )
    nonperiodic_ids = _string_array(
        nonperiodic_obj["site_ids"],
        site_count,
        "evidence.nonperiodic.site_ids",
    )
    if (
        nonperiodic_ids != [site["site_id"] for site in sites]
        or len(set(nonperiodic_ids)) != site_count
    ):
        raise VerificationError("evidence nonperiodic site identity is wrong")
    nonperiodic_hash = _hash(
        nonperiodic_obj["lineage_sha256"],
        "evidence.nonperiodic.lineage_sha256",
    )
    if nonperiodic_hash != lineage["nonperiodic_sha256"]:
        raise VerificationError("evidence nonperiodic lineage hash is wrong")
    q_baseline = (
        _prepare_q_baseline(obj["q_baseline"], contract_cells)
        if "q_baseline" in obj
        else None
    )
    return {
        "claim_scope": claim_scope,
        "sites": sites,
        "hierarchy": hierarchy,
        "lineage": lineage,
        "reductions": reductions,
        "reduction_sufficient": reduction_sufficient,
        "sampling": sampling,
        "cells": cells,
        "raw_response": response,
        "geometry": geometry,
        "nonperiodic": {
            "concealed": _boolean(
                nonperiodic_obj["concealed"], "evidence.nonperiodic.concealed"
            ),
            "lineage_sha256": nonperiodic_hash,
            "site_ids": nonperiodic_ids,
        },
        "q_baseline": q_baseline,
        "fixture_stats": {},
    }


def _case_map(commission: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    cases = _list(commission["cases"], "commission.cases")
    result: dict[str, Mapping[str, Any]] = {}
    for index, raw_case in enumerate(cases):
        case = _mapping(raw_case, f"commission.cases[{index}]")
        name = _string(case["case"], f"commission.cases[{index}].case")
        if name in result:
            raise VerificationError(f"duplicate commission case {name}")
        result[name] = case
    return result


def _gate(case: Mapping[str, Any], gate_id: str) -> Mapping[str, Any]:
    gates = _list(case["gates"], f"{case.get('case', '?')}.gates")
    matches = [
        _mapping(gate, f"{case.get('case', '?')}.{gate_id}")
        for gate in gates
        if isinstance(gate, Mapping) and gate.get("id") == gate_id
    ]
    if len(matches) != 1:
        raise VerificationError(
            f"{case.get('case', '?')} must contain exactly one {gate_id}"
        )
    return matches[0]


def _reason_codes(gate: Mapping[str, Any], path: str) -> list[str]:
    raw = _list(gate["reason_codes"], f"{path}.reason_codes")
    result = [_string(value, f"{path}.reason_codes") for value in raw]
    if len(result) != len(set(result)):
        raise VerificationError(f"{path}.reason_codes contains duplicates")
    return result


def _eigen_summary(
    context: CheckContext,
    value: Any,
    dimension: int,
    path: str,
) -> list[float]:
    summary = _mapping(value, path)
    _expect_keys(
        context,
        summary,
        ("condition_number", "eigenvalues", "minimum_eigenvalue"),
        path,
    )
    raw_values = _list(summary["eigenvalues"], f"{path}.eigenvalues")
    context.equal(len(raw_values), dimension, f"{path}.eigenvalues length")
    eigenvalues = [
        _number(item, f"{path}.eigenvalues[{index}]")
        for index, item in enumerate(raw_values)
    ]
    context.expect(
        eigenvalues == sorted(eigenvalues),
        f"{path}.eigenvalues are not ascending",
    )
    context.close(
        summary["minimum_eigenvalue"],
        eigenvalues[0],
        f"{path}.minimum_eigenvalue",
    )
    condition = _optional_number(
        summary["condition_number"], f"{path}.condition_number"
    )
    expected_condition = (
        None if eigenvalues[0] <= 0.0 else eigenvalues[-1] / eigenvalues[0]
    )
    if expected_condition is None:
        context.equal(condition, None, f"{path}.condition_number")
    else:
        context.close(condition, expected_condition, f"{path}.condition_number")
    return eigenvalues


def _max_t(
    context: CheckContext,
    value: Any,
    expected_length: int,
    path: str,
    expected_probability: float = LOWER_BOUND_QUANTILE,
    expected_numerator: str = "bootstrap_minus_observed",
    expected_upper_bound: str | None = None,
) -> tuple[float, list[float]]:
    max_t = _mapping(value, path)
    expected_keys = {
        "critical_value",
        "quantile_method",
        "quantile_probability",
        "standard_error",
        "studentized_numerator",
        "valid",
    }
    if expected_upper_bound is not None:
        expected_keys.add("upper_bound")
    _expect_keys(
        context,
        max_t,
        expected_keys,
        path,
    )
    context.equal(_boolean(max_t["valid"], f"{path}.valid"), True, f"{path}.valid")
    critical = _number(max_t["critical_value"], f"{path}.critical_value")
    context.expect(critical > 0.0, f"{path}.critical_value must be positive")
    raw_errors = _list(max_t["standard_error"], f"{path}.standard_error")
    context.equal(
        len(raw_errors),
        expected_length,
        f"{path}.standard_error length",
    )
    errors = [
        _number(item, f"{path}.standard_error[{index}]")
        for index, item in enumerate(raw_errors)
    ]
    context.expect(
        all(value > 0.0 for value in errors),
        f"{path}.standard_error must be strictly positive",
    )
    context.equal(
        max_t["studentized_numerator"],
        expected_numerator,
        f"{path}.studentized_numerator",
    )
    if expected_upper_bound is not None:
        context.equal(
            max_t["upper_bound"],
            expected_upper_bound,
            f"{path}.upper_bound",
        )
    context.close(
        max_t["quantile_probability"],
        expected_probability,
        f"{path}.quantile_probability",
    )
    context.equal(
        max_t["quantile_method"],
        "higher",
        f"{path}.quantile_method",
    )
    return critical, errors


_RAW_BOOTSTRAP_CACHE: dict[tuple[Any, ...], np.ndarray] = {}


def _raw_bootstrap_indices(
    hierarchy: Sequence[Sequence[np.ndarray]],
    draws: int,
    seed: int,
) -> np.ndarray:
    signature = tuple(
        tuple(tuple(int(index) for index in burst) for burst in session)
        for session in hierarchy
    )
    key = (signature, draws, seed)
    cached = _RAW_BOOTSTRAP_CACHE.get(key)
    if cached is not None:
        return cached
    rng = np.random.default_rng(seed)
    session_count = len(hierarchy)
    bursts_per_session = len(hierarchy[0])
    sites_per_burst = len(hierarchy[0][0])
    indices = np.empty(
        (
            draws,
            session_count * bursts_per_session * sites_per_burst,
        ),
        dtype=np.intp,
    )
    for draw in range(draws):
        cursor = 0
        sessions = rng.integers(0, session_count, size=session_count)
        for session_index in sessions:
            session = hierarchy[int(session_index)]
            bursts = rng.integers(
                0, len(session), size=bursts_per_session
            )
            for burst_index in bursts:
                burst = session[int(burst_index)]
                sites = rng.integers(
                    0, len(burst), size=sites_per_burst
                )
                indices[draw, cursor : cursor + sites_per_burst] = burst[sites]
                cursor += sites_per_burst
    indices.setflags(write=False)
    _RAW_BOOTSTRAP_CACHE[key] = indices
    return indices


def _raw_cross_covariance(
    first: np.ndarray,
    second: np.ndarray,
    indices: np.ndarray | None = None,
) -> np.ndarray:
    if indices is None:
        x = first[np.newaxis, ...]
        y = second[np.newaxis, ...]
    else:
        x = first[indices]
        y = second[indices]
    x = x - np.mean(x, axis=1, keepdims=True)
    y = y - np.mean(y, axis=1, keepdims=True)
    covariance = (
        np.einsum("bni,bnj->bij", x.conj(), y, optimize=True) / x.shape[1]
    )
    return 0.5 * (
        covariance + np.swapaxes(covariance.conj(), -1, -2)
    )


def _raw_noise_covariance(
    first: np.ndarray,
    second: np.ndarray,
    difference_factor: float,
    indices: np.ndarray | None = None,
) -> np.ndarray:
    if indices is None:
        difference = (first - second)[np.newaxis, ...]
    else:
        difference = first[indices] - second[indices]
    difference = difference - np.mean(difference, axis=1, keepdims=True)
    covariance = (
        difference_factor
        * np.einsum(
            "bni,bnj->bij",
            difference.conj(),
            difference,
            optimize=True,
        )
        / difference.shape[1]
    )
    return 0.5 * (
        covariance + np.swapaxes(covariance.conj(), -1, -2)
    )


def _raw_path_stats(
    cell: Mapping[str, Any],
    prefix: str,
    difference_factor: float,
    indices: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    coefficients = cell["coefficients"]
    return (
        _raw_cross_covariance(
            coefficients[f"{prefix}1"],
            coefficients[f"{prefix}2"],
            indices,
        ),
        _raw_noise_covariance(
            coefficients[f"{prefix}1"],
            coefficients[f"{prefix}2"],
            difference_factor,
            indices,
        ),
    )


def _raw_matrix_size(matrices: np.ndarray) -> np.ndarray:
    eigenvalues = np.linalg.eigvalsh(matrices)
    return np.max(np.abs(eigenvalues), axis=-1)


def _raw_control_sizes(
    cell: Mapping[str, Any],
    prefix: str,
    indices: np.ndarray | None,
) -> np.ndarray:
    sizes: list[np.ndarray] = []
    for control_name in CONTROLS:
        control = cell["controls"][control_name]
        covariance = _raw_cross_covariance(
            control[f"{prefix}1"],
            control[f"{prefix}2"],
            indices,
        )
        sizes.append(_raw_matrix_size(covariance))
    return np.max(np.stack(sizes, axis=-1), axis=-1)


def _raw_finite(value: Any) -> float | None:
    try:
        converted = float(np.real(value))
    except (TypeError, ValueError, OverflowError):
        return None
    return converted if math.isfinite(converted) else None


def _raw_simultaneous_lcb(
    observed: np.ndarray,
    bootstrap: np.ndarray,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    point = np.asarray(observed, dtype=np.float64)
    draws = np.asarray(bootstrap, dtype=np.float64)
    if (
        draws.ndim != 2
        or point.ndim != 1
        or draws.shape[1] != point.size
        or not np.all(np.isfinite(point))
        or not np.all(np.isfinite(draws))
    ):
        return None, {"valid": False, "failure": "NONFINITE_OR_SHAPE"}
    standard_error = np.std(draws, axis=0, ddof=1)
    if np.any(~np.isfinite(standard_error)) or np.any(
        standard_error <= 0.0
    ):
        return None, {
            "valid": False,
            "failure": "ZERO_OR_NONFINITE_STANDARD_ERROR",
            "standard_error": [
                _raw_finite(value) for value in standard_error
            ],
        }
    studentized = (draws - point[np.newaxis, :]) / standard_error
    maximum = np.max(studentized, axis=1)
    critical = float(
        np.quantile(maximum, LOWER_BOUND_QUANTILE, method="higher")
    )
    return point - critical * standard_error, {
        "valid": True,
        "critical_value": critical,
        "standard_error": [float(value) for value in standard_error],
        "studentized_numerator": "bootstrap_minus_observed",
        "quantile_probability": LOWER_BOUND_QUANTILE,
        "quantile_method": "higher",
    }


def _raw_simultaneous_upper(
    observed: np.ndarray,
    bootstrap: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    point = np.asarray(observed, dtype=np.float64)
    draws = np.asarray(bootstrap, dtype=np.float64)
    if (
        draws.ndim != 2
        or point.ndim != 1
        or draws.shape[1] != point.size
        or not np.all(np.isfinite(point))
        or not np.all(np.isfinite(draws))
    ):
        return None, {"valid": False, "failure": "NONFINITE_OR_SHAPE"}
    standard_error = np.std(draws, axis=0, ddof=1)
    if np.any(~np.isfinite(standard_error)) or np.any(
        standard_error <= 0.0
    ):
        return None, {
            "valid": False,
            "failure": "ZERO_OR_NONFINITE_STANDARD_ERROR",
            "standard_error": [
                _raw_finite(value) for value in standard_error
            ],
        }
    studentized = (point[np.newaxis, :] - draws) / standard_error
    maximum = np.max(studentized, axis=1)
    critical = float(
        np.quantile(maximum, 1.0 - alpha, method="higher")
    )
    return point + critical * standard_error, {
        "valid": True,
        "critical_value": critical,
        "standard_error": [float(value) for value in standard_error],
        "studentized_numerator": "observed_minus_bootstrap",
        "upper_bound": "observed_plus_critical_times_standard_error",
        "quantile_probability": 1.0 - alpha,
        "quantile_method": "higher",
    }


def _raw_eigen_summary(matrix: np.ndarray) -> dict[str, Any]:
    eigenvalues = np.linalg.eigvalsh(matrix)
    minimum = float(eigenvalues[0])
    maximum = float(eigenvalues[-1])
    condition = None if minimum <= 0.0 else maximum / minimum
    return {
        "eigenvalues": [float(value) for value in eigenvalues],
        "minimum_eigenvalue": minimum,
        "condition_number": _raw_finite(condition),
    }


def _raw_spd_batch(
    matrices: np.ndarray,
    condition_ceiling: float,
) -> tuple[bool, np.ndarray, np.ndarray]:
    eigenvalues = np.linalg.eigvalsh(matrices)
    minimum = eigenvalues[..., 0]
    maximum = eigenvalues[..., -1]
    with np.errstate(divide="ignore", invalid="ignore"):
        condition = maximum / minimum
    valid = bool(
        np.all(np.isfinite(eigenvalues))
        and np.all(minimum > 0.0)
        and np.all(np.isfinite(condition))
        and np.all(condition <= condition_ceiling)
    )
    return valid, minimum, condition


def _raw_inverse_sqrt(matrices: np.ndarray) -> np.ndarray:
    eigenvalues, eigenvectors = np.linalg.eigh(matrices)
    scales = 1.0 / np.sqrt(eigenvalues)
    return (eigenvectors * scales[..., np.newaxis, :]) @ np.swapaxes(
        eigenvectors.conj(), -1, -2
    )


def _raw_information_operator(
    signal: np.ndarray,
    noise: np.ndarray,
) -> np.ndarray:
    inverse_sqrt = _raw_inverse_sqrt(noise)
    whitened = inverse_sqrt @ signal @ inverse_sqrt
    whitened = 0.5 * (
        whitened + np.swapaxes(whitened.conj(), -1, -2)
    )
    eigenvalues, eigenvectors = np.linalg.eigh(whitened)
    information = 0.5 * np.log2(1.0 + eigenvalues)
    return (eigenvectors * information[..., np.newaxis, :]) @ np.swapaxes(
        eigenvectors.conj(), -1, -2
    )


def _raw_smallest_generalized(
    numerator: np.ndarray,
    denominator: np.ndarray,
) -> np.ndarray:
    inverse_sqrt = _raw_inverse_sqrt(denominator)
    whitened = inverse_sqrt @ numerator @ inverse_sqrt
    whitened = 0.5 * (
        whitened + np.swapaxes(whitened.conj(), -1, -2)
    )
    return np.linalg.eigvalsh(whitened)[..., 0]


def _complex_vector_json(vector: np.ndarray) -> list[list[float]]:
    return [
        [float(np.real(value)), float(np.imag(value))]
        for value in np.asarray(vector)
    ]


def _raw_generalized_eigensystem_audit(
    numerator: np.ndarray,
    denominator: np.ndarray,
) -> dict[str, Any]:
    inverse_sqrt = _raw_inverse_sqrt(denominator)
    whitened = inverse_sqrt @ numerator @ inverse_sqrt
    whitened = 0.5 * (
        whitened + np.swapaxes(whitened.conj(), -1, -2)
    )
    eigenvalues, whitened_vectors = np.linalg.eigh(whitened)
    vectors = inverse_sqrt @ whitened_vectors
    residual = numerator @ vectors - (
        denominator
        @ vectors
        @ np.apply_along_axis(np.diag, -1, eigenvalues)
    )
    numerator_scale = np.linalg.norm(numerator, axis=(-2, -1))
    denominator_scale = np.linalg.norm(denominator, axis=(-2, -1))
    vector_scale = np.linalg.norm(vectors, axis=(-2, -1))
    eigenvalue_scale = np.max(np.abs(eigenvalues), axis=-1)
    scale = (
        numerator_scale
        + denominator_scale * eigenvalue_scale
    ) * vector_scale
    with np.errstate(divide="ignore", invalid="ignore"):
        relative_residual = np.linalg.norm(
            residual, axis=(-2, -1)
        ) / scale
    metric_gram = (
        np.swapaxes(vectors.conj(), -1, -2)
        @ denominator
        @ vectors
    )
    identity = np.eye(numerator.shape[-1], dtype=np.complex128)
    orthonormality = np.linalg.norm(
        metric_gram - identity,
        axis=(-2, -1),
    )
    point_values = eigenvalues[0]
    point_vectors = vectors[0]
    return {
        "point_eigenvalues": [float(value) for value in point_values],
        "weakest_point_direction": _complex_vector_json(
            point_vectors[:, 0]
        ),
        "maximum_relative_residual": float(
            np.nanmax(relative_residual)
        ),
        "maximum_metric_orthonormality_error": float(
            np.max(orthonormality)
        ),
        "draw_count": int(numerator.shape[0] - 1),
    }


def _raw_common_mode_bounds(
    evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
    indices: np.ndarray,
) -> tuple[
    dict[tuple[str, str], float] | None,
    dict[str, Any],
]:
    observed: list[float] = []
    bootstrap_columns: list[np.ndarray] = []
    labels: list[tuple[str, str]] = []
    for cell in evidence["cells"]:
        for prefix in ("R", "S"):
            point = _raw_control_sizes(cell, prefix, None)[0]
            draws = _raw_control_sizes(cell, prefix, indices)
            observed.append(float(point))
            bootstrap_columns.append(np.asarray(draws, dtype=np.float64))
            labels.append((cell["id"], prefix))
    point_array = np.asarray(observed, dtype=np.float64)
    draw_array = np.stack(bootstrap_columns, axis=1)
    upper, max_t = _raw_simultaneous_upper(
        point_array,
        draw_array,
        float(contract["bootstrap"]["common_mode_family_alpha"]),
    )
    diagnostics = {
        "family_alpha": float(
            contract["bootstrap"]["common_mode_family_alpha"]
        ),
        "draws": int(contract["bootstrap"]["draws"]),
        "max_t": max_t,
        "point_estimates": {
            f"{cell_id}:{prefix}": float(value)
            for (cell_id, prefix), value in zip(labels, point_array)
        },
    }
    if upper is None:
        diagnostics["upper_bounds"] = None
        return None, diagnostics
    bounds = {
        label: float(value)
        for label, value in zip(labels, np.asarray(upper))
    }
    diagnostics["upper_bounds"] = {
        f"{cell_id}:{prefix}": value
        for (cell_id, prefix), value in bounds.items()
    }
    return bounds, diagnostics


def _raw_gate_record(
    gate_id: str,
    name: str,
    reasons: Sequence[str],
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    unique_reasons = list(dict.fromkeys(reasons))
    passed = not unique_reasons
    return {
        "id": gate_id,
        "name": name,
        "status": "PASS" if passed else "UNMEASURED",
        "evaluated": True,
        "reason_codes": [] if passed else unique_reasons,
        "claim_value": "ESTABLISHED" if passed else None,
        "diagnostics": dict(diagnostics),
    }


def _raw_thresholds(contract: Mapping[str, Any]) -> dict[str, Any]:
    thresholds = dict(contract["synthetic_thresholds"])
    thresholds["sampling_optical_systematic_bound"] = 0.0
    cell_ids = [str(cell["id"]) for cell in contract["cells"]]
    thresholds["delta_information_by_cell"] = {
        cell_id: float(thresholds["delta_information"])
        for cell_id in cell_ids
    }
    thresholds["delta_transfer_by_cell"] = {
        cell_id: float(thresholds["delta_transfer"])
        for cell_id in cell_ids
    }
    return thresholds


def _compare_rederived_tree(
    context: CheckContext,
    actual: Any,
    expected: Any,
    path: str,
) -> None:
    if isinstance(expected, Mapping):
        actual_mapping = _mapping(actual, path)
        _expect_keys(context, actual_mapping, set(expected), path)
        for key, value in expected.items():
            if key in actual_mapping:
                _compare_rederived_tree(
                    context,
                    actual_mapping[key],
                    value,
                    f"{path}.{key}",
                )
        return
    if isinstance(expected, list):
        actual_list = _list(actual, path)
        context.equal(len(actual_list), len(expected), f"{path} length")
        for index, value in enumerate(expected):
            if index < len(actual_list):
                _compare_rederived_tree(
                    context,
                    actual_list[index],
                    value,
                    f"{path}[{index}]",
                )
        return
    if type(expected) is float:
        context.close(actual, expected, path)
    else:
        context.equal(actual, expected, path)


def _raw_fixture_stats(
    evidence: dict[str, Any],
    cell: Mapping[str, Any],
    contract: Mapping[str, Any],
    indices: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    cell_id = str(cell["id"])
    cached = evidence["fixture_stats"].get(cell_id)
    if cached is not None:
        return cached
    difference_factor = float(
        contract["source_authority"]["noise_difference_factor"]
    )
    point_signal, point_noise = _raw_path_stats(
        cell, "R", difference_factor, None
    )
    draw_signal, draw_noise = _raw_path_stats(
        cell, "R", difference_factor, indices
    )
    result = (point_signal, point_noise, draw_signal, draw_noise)
    evidence["fixture_stats"][cell_id] = result
    return result


def _raw_gate_g1(
    evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    indices: np.ndarray,
) -> dict[str, Any]:
    sampling = evidence["sampling"]
    ratio = (
        sampling["reference_magnification"]
        / sampling["scored_magnification"]
    )
    observed = np.asarray([float(np.mean(ratio))])
    bootstrap = np.mean(ratio[indices], axis=1)[:, np.newaxis]
    lower, max_t = _raw_simultaneous_lcb(
        observed,
        bootstrap,
    )
    reasons: list[str] = []
    if not sampling["input_only"]:
        reasons.append("INPUT_ONLY_SAMPLING_NOT_ESTABLISHED")
    if lower is None:
        reasons.append("SAMPLING_BOOTSTRAP_INVALID")
        lower_value = None
        adjusted = None
    else:
        lower_value = float(lower[0])
        adjusted = lower_value - float(
            thresholds["sampling_optical_systematic_bound"]
        )
        if adjusted < float(thresholds["sampling_ratio_lcb_min"]):
            reasons.append("SAMPLING_RATIO_NOT_ESTABLISHED")
    diagnostics = {
        "ratio_mean": float(observed[0]),
        "ratio_minimum": float(np.min(ratio)),
        "simultaneous_lcb": lower_value,
        "optical_systematic_ratio_bound": float(
            thresholds["sampling_optical_systematic_bound"]
        ),
        "systematic_adjusted_lcb": adjusted,
        "threshold": float(thresholds["sampling_ratio_lcb_min"]),
        "max_t": max_t,
    }
    return _raw_gate_record(
        "G1", "SUBJECT_SAMPLING_RATIO", reasons, diagnostics
    )


def _raw_gate_g2(
    evidence: dict[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    indices: np.ndarray,
    common_bounds: Mapping[tuple[str, str], float] | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    diagnostics: dict[str, Any] = {
        "inference_coordinate": "natural_log_reference_snr",
        "reported_bound": "exp_coordinate_lower_bound",
        "cells": {},
    }
    if common_bounds is None:
        return _raw_gate_record(
            "G2",
            "SPLIT_REFERENCE_SNR",
            ["COMMON_MODE_BOUND_INVALID"],
            diagnostics,
        )
    observed: list[float] = []
    draws: list[np.ndarray] = []
    invalid = False
    condition_ceiling = float(thresholds["condition_number_max"])
    for cell in evidence["cells"]:
        (
            point_signal,
            point_noise,
            draw_signal,
            draw_noise,
        ) = _raw_fixture_stats(evidence, cell, contract, indices)
        dimension = int(cell["dimension"])
        identity = np.eye(dimension, dtype=np.complex128)
        common = float(common_bounds[(cell["id"], "R")])
        charged_signal = point_signal - common * identity
        charged_noise = point_noise + common * identity
        draw_charged_signal = draw_signal - common * identity
        draw_charged_noise = draw_noise + common * identity
        valid_point_signal, _, _ = _raw_spd_batch(
            charged_signal, condition_ceiling
        )
        valid_point_noise, _, _ = _raw_spd_batch(
            charged_noise, condition_ceiling
        )
        valid_draw_signal, _, _ = _raw_spd_batch(
            draw_charged_signal, condition_ceiling
        )
        valid_draw_noise, _, _ = _raw_spd_batch(
            draw_charged_noise, condition_ceiling
        )
        cell_diagnostics: dict[str, Any] = {
            "signal": _raw_eigen_summary(point_signal[0]),
            "noise": _raw_eigen_summary(point_noise[0]),
            "common_mode_upper": common,
            "charged_signal": _raw_eigen_summary(charged_signal[0]),
            "charged_noise": _raw_eigen_summary(charged_noise[0]),
        }
        if not (
            valid_point_signal
            and valid_point_noise
            and valid_draw_signal
            and valid_draw_noise
        ):
            invalid = True
            cell_diagnostics["snr"] = None
            cell_diagnostics["log_snr"] = None
            cell_diagnostics["log_snr_lcb"] = None
            cell_diagnostics["snr_lcb"] = None
        else:
            point_ratio = _raw_smallest_generalized(
                charged_signal, charged_noise
            )
            draw_ratio = _raw_smallest_generalized(
                draw_charged_signal, draw_charged_noise
            )
            ratios_valid = (
                np.all(np.isfinite(point_ratio))
                and np.all(point_ratio > 0.0)
                and np.all(np.isfinite(draw_ratio))
                and np.all(draw_ratio > 0.0)
            )
            if not ratios_valid:
                invalid = True
                cell_diagnostics["snr"] = None
                cell_diagnostics["log_snr"] = None
                cell_diagnostics["log_snr_lcb"] = None
                cell_diagnostics["snr_lcb"] = None
            else:
                point_log_snr = np.log(point_ratio)
                draw_log_snr = np.log(draw_ratio)
                observed.append(float(point_log_snr[0]))
                draws.append(np.asarray(draw_log_snr, dtype=np.float64))
                cell_diagnostics["snr"] = float(point_ratio[0])
                cell_diagnostics["log_snr"] = float(point_log_snr[0])
        diagnostics["cells"][cell["id"]] = cell_diagnostics
    if invalid:
        reasons.extend(
            [
                "REFERENCE_SNR_NONPOSITIVE_OR_ILL_CONDITIONED",
                "REFERENCE_SNR_INSUFFICIENT",
            ]
        )
    else:
        lower, max_t = _raw_simultaneous_lcb(
            np.asarray(observed),
            np.stack(draws, axis=1),
        )
        diagnostics["max_t"] = max_t
        if lower is None:
            reasons.append("REFERENCE_SNR_BOOTSTRAP_INVALID")
        else:
            with np.errstate(over="ignore", invalid="ignore"):
                snr_lower = np.exp(lower)
            for cell, log_value, snr_value in zip(
                evidence["cells"], lower, snr_lower
            ):
                diagnostics["cells"][cell["id"]][
                    "log_snr_lcb"
                ] = float(log_value)
                diagnostics["cells"][cell["id"]][
                    "snr_lcb"
                ] = _raw_finite(snr_value)
            if np.any(~np.isfinite(snr_lower)):
                reasons.append("REFERENCE_SNR_BOOTSTRAP_INVALID")
            if np.any(
                snr_lower <= float(thresholds["reference_snr_lcb_min"])
            ):
                reasons.append("REFERENCE_SNR_INSUFFICIENT")
    diagnostics["threshold"] = float(thresholds["reference_snr_lcb_min"])
    return _raw_gate_record(
        "G2", "SPLIT_REFERENCE_SNR", reasons, diagnostics
    )


def _raw_gate_g3(
    evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    indices: np.ndarray,
) -> dict[str, Any]:
    reasons: list[str] = []
    diagnostics: dict[str, Any] = {"cells": {}}
    observed: list[float] = []
    draws: list[np.ndarray] = []
    invalid_bootstrap = False
    for cell in evidence["cells"]:
        focus = cell["focus"]
        mean_transfer = np.mean(focus["transfer"], axis=0)
        response = np.linalg.norm(mean_transfer, axis=(-2, -1))
        peak = int(np.argmax(response))
        maximum = float(response[peak])
        unique = int(np.count_nonzero(response == maximum)) == 1
        interior = 0 < peak < len(response) - 1
        singular_values = np.linalg.svd(
            mean_transfer[peak], compute_uv=False
        )
        smallest = float(singular_values[-1])
        condition = (
            None
            if smallest <= 0.0
            else float(singular_values[0] / singular_values[-1])
        )
        leakage = float(np.max(focus["cross_cell_leakage"]))
        cell_diagnostics = {
            "known_input": bool(focus["known_input"]),
            "response_by_position": [float(value) for value in response],
            "peak_index": peak,
            "peak_unique": unique,
            "peak_interior": interior,
            "smallest_singular_value": smallest,
            "condition_number": condition,
            "cross_cell_leakage": leakage,
        }
        if not focus["known_input"]:
            reasons.append("FOCUS_KNOWN_INPUT_PROVENANCE_MISSING")
        if not unique or not interior:
            reasons.append("FOCUS_PEAK_NOT_INTERIOR")
        if condition is None or condition > float(
            thresholds["condition_number_max"]
        ):
            reasons.append("FOCUS_TRANSFER_ILL_CONDITIONED")
        if leakage > float(thresholds["cross_cell_leakage_max"]):
            reasons.append("CROSS_CELL_LEAKAGE_EXCESS")
        sampled = np.mean(
            focus["transfer"][indices, peak], axis=1
        )
        sampled_smallest = np.linalg.svd(
            sampled, compute_uv=False
        )[..., -1]
        if not np.all(np.isfinite(sampled_smallest)):
            invalid_bootstrap = True
        observed.append(smallest)
        draws.append(np.asarray(sampled_smallest, dtype=np.float64))
        diagnostics["cells"][cell["id"]] = cell_diagnostics
    if invalid_bootstrap:
        lower = None
        diagnostics["max_t"] = {
            "valid": False,
            "failure": "NONFINITE_DRAW",
        }
    else:
        lower, max_t = _raw_simultaneous_lcb(
            np.asarray(observed),
            np.stack(draws, axis=1),
        )
        diagnostics["max_t"] = max_t
    if lower is None:
        reasons.append("FOCUS_TRANSFER_BOOTSTRAP_INVALID")
    else:
        for cell, value in zip(evidence["cells"], lower):
            diagnostics["cells"][cell["id"]][
                "smallest_singular_value_lcb"
            ] = float(value)
        if np.any(
            lower
            <= float(
                thresholds["focus_transfer_singular_value_lcb_min"]
            )
        ):
            reasons.append("FOCUS_TRANSFER_INSUFFICIENT")
    diagnostics["thresholds"] = {
        "smallest_singular_value_lcb_min": float(
            thresholds["focus_transfer_singular_value_lcb_min"]
        ),
        "condition_number_max": float(thresholds["condition_number_max"]),
        "cross_cell_leakage_max": float(
            thresholds["cross_cell_leakage_max"]
        ),
    }
    return _raw_gate_record(
        "G3",
        "REFERENCE_FOCUS_TRANSFER_SUFFICIENCY",
        reasons,
        diagnostics,
    )


def _raw_gate_g4(
    evidence: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    response = evidence["raw_response"]
    reasons: list[str] = []
    if not response["known_input"]:
        reasons.append("RAW_KNOWN_INPUT_PROVENANCE_MISSING")
    if response["low_rail_hits"] or response["high_rail_hits"]:
        reasons.append("RAW_CLIPPING_DETECTED")
    x = response["input_levels"]
    y = response["output_levels"]
    even = np.arange(0, 33, 2)
    odd = np.arange(1, 33, 2)
    design = np.column_stack((x[even], np.ones(even.size)))
    coefficients, _, rank, _ = np.linalg.lstsq(
        design, y[even], rcond=None
    )
    slope = float(coefficients[0])
    intercept = float(coefficients[1])
    dynamic_range = float(np.max(y) - np.min(y))
    if rank != 2 or slope <= 0.0 or dynamic_range <= 0.0:
        residual = None
        reasons.append("RAW_POSITIVE_AFFINE_FIT_NOT_ESTABLISHED")
    else:
        prediction = slope * x[odd] + intercept
        residual = float(
            np.max(np.abs(y[odd] - prediction)) / dynamic_range
        )
        if residual > float(
            thresholds["raw_response_max_normalized_residual"]
        ):
            reasons.append("RAW_NONLINEARITY_DETECTED")
    diagnostics = {
        "low_rail_hits": int(response["low_rail_hits"]),
        "high_rail_hits": int(response["high_rail_hits"]),
        "fit_level_indices": [int(value) for value in even],
        "held_out_level_indices": [int(value) for value in odd],
        "slope": slope,
        "intercept": intercept,
        "held_out_max_normalized_residual": residual,
        "threshold": float(
            thresholds["raw_response_max_normalized_residual"]
        ),
    }
    return _raw_gate_record(
        "G4", "LINEAR_UNCLIPPED_RAW", reasons, diagnostics
    )


def _raw_split_metrics(pair: Mapping[str, Any]) -> dict[str, Any]:
    first = pair["first"]
    second = pair["second"]
    first_rms = float(
        np.sqrt(np.mean(np.sum(np.abs(first) ** 2, axis=1)))
    )
    second_rms = float(
        np.sqrt(np.mean(np.sum(np.abs(second) ** 2, axis=1)))
    )
    denominator = 0.5 * (first_rms + second_rms)
    magnitude = (
        None
        if denominator <= 0.0
        else abs(first_rms - second_rms) / denominator
    )
    cross = np.vdot(first.reshape(-1), second.reshape(-1))
    phase = None if abs(cross) == 0.0 else abs(float(np.angle(cross)))
    signal = _raw_cross_covariance(first, second)[0]
    signal_minimum = float(np.linalg.eigvalsh(signal)[0])
    control_values: list[float] = []
    for control_name in CONTROLS:
        control = pair["controls"][control_name]
        covariance = _raw_cross_covariance(
            control["first"], control["second"]
        )
        control_values.append(float(_raw_matrix_size(covariance)[0]))
    common = max(control_values)
    common_fraction = (
        None if signal_minimum <= 0.0 else common / signal_minimum
    )
    return {
        "first_rms": first_rms,
        "second_rms": second_rms,
        "relative_magnitude_disagreement": _raw_finite(magnitude),
        "phase_disagreement_rad": _raw_finite(phase),
        "repeatable_signal_minimum_eigenvalue": signal_minimum,
        "control_repeatable_covariance": {
            name: value
            for name, value in zip(CONTROLS, control_values)
        },
        "common_mode_fraction": _raw_finite(common_fraction),
    }


def _raw_gate_g5(
    evidence: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    diagnostics: dict[str, Any] = {"cells": {}}
    lineage = evidence["lineage"]
    acquisition_hashes = [
        lineage[f"{name}_{kind}_sha256"]
        for name in PATHS
        for kind in ("source", "calibration")
    ]
    lineage_disjoint = len(set(acquisition_hashes)) == len(
        acquisition_hashes
    )
    if not lineage_disjoint:
        reasons.append("LINEAGE_NOT_DISJOINT")
    for cell in evidence["cells"]:
        cell_diagnostics: dict[str, Any] = {}
        for split_name in SPLITS:
            metrics = _raw_split_metrics(
                cell["split_pairs"][split_name]
            )
            cell_diagnostics[split_name] = metrics
            magnitude = metrics["relative_magnitude_disagreement"]
            phase = metrics["phase_disagreement_rad"]
            common = metrics["common_mode_fraction"]
            if magnitude is None or phase is None or common is None:
                reasons.append("REFERENCE_HALF_AGREEMENT_UNIDENTIFIED")
                continue
            if magnitude > float(
                thresholds["split_magnitude_disagreement_max"]
            ):
                reasons.append("REFERENCE_HALF_MAGNITUDE_DISAGREEMENT")
            if phase > float(
                thresholds["split_phase_disagreement_rad_max"]
            ):
                reasons.append("REFERENCE_HALF_PHASE_DISAGREEMENT")
            if common > float(thresholds["common_mode_fraction_max"]):
                reasons.append("LAGGED_COMMON_MODE_EXCESS")
        diagnostics["cells"][cell["id"]] = cell_diagnostics
    diagnostics["lineage_disjoint"] = lineage_disjoint
    diagnostics["thresholds"] = {
        "magnitude_relative_max": float(
            thresholds["split_magnitude_disagreement_max"]
        ),
        "phase_rad_max": float(
            thresholds["split_phase_disagreement_rad_max"]
        ),
        "common_mode_fraction_max": float(
            thresholds["common_mode_fraction_max"]
        ),
    }
    return _raw_gate_record(
        "G5", "REFERENCE_HALF_AGREEMENT", reasons, diagnostics
    )


def _raw_gate_g6(
    evidence: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    geometry = evidence["geometry"]
    reasons: list[str] = []
    if not geometry["input_only"]:
        reasons.append("INPUT_ONLY_GEOMETRY_NOT_ESTABLISHED")
    if not geometry["scored_pixels_native"]:
        reasons.append("SCORED_PIXELS_NOT_NATIVE")
    if not geometry["reference_only_resampling"]:
        reasons.append("REFERENCE_ONLY_RESAMPLING_NOT_ESTABLISHED")
    max_scale = float(
        np.max(np.abs(geometry["scale_disagreement_percent"]))
    )
    max_rotation = float(
        np.max(np.abs(geometry["rotation_disagreement_deg"]))
    )
    max_nontranslation = float(
        np.max(geometry["nontranslation_rms_native_px"])
    )
    signs_match = bool(
        np.array_equal(
            geometry["planted_transform_sign"],
            geometry["estimated_transform_sign"],
        )
    )
    if max_scale > float(
        thresholds["scale_disagreement_percent_max"]
    ):
        reasons.append("SCALE_GEOMETRY_DISAGREEMENT")
    if max_rotation > float(
        thresholds["rotation_disagreement_deg_max"]
    ):
        reasons.append("ROTATION_GEOMETRY_DISAGREEMENT")
    if max_nontranslation > float(
        thresholds["nontranslation_rms_native_px_max"]
    ):
        reasons.append("NONTRANSLATION_RESIDUAL_EXCESS")
    if not signs_match:
        reasons.append("WRONG_SIGN_GEOMETRY")
    changes: dict[str, float | None] = {}
    for cell in evidence["cells"]:
        first = cell["resampler"]["kernel_a"]
        second = cell["resampler"]["kernel_b"]
        denominator = float(
            np.sqrt(np.mean(np.sum(np.abs(first) ** 2, axis=1)))
        )
        if denominator <= 0.0:
            relative = None
            reasons.append("RESAMPLER_SENSITIVITY_UNIDENTIFIED")
        else:
            relative = float(
                np.sqrt(
                    np.mean(
                        np.sum(np.abs(second - first) ** 2, axis=1)
                    )
                )
                / denominator
            )
            if relative > float(
                thresholds["resampler_relative_change_max"]
            ):
                reasons.append("RESAMPLER_SENSITIVITY_EXCESS")
        changes[cell["id"]] = relative
    diagnostics = {
        "max_scale_disagreement_percent": max_scale,
        "max_rotation_disagreement_deg": max_rotation,
        "max_nontranslation_rms_native_px": max_nontranslation,
        "planted_transform_sign_matches": signs_match,
        "resampler_relative_change_by_cell": changes,
        "thresholds": {
            "scale_disagreement_percent_max": float(
                thresholds["scale_disagreement_percent_max"]
            ),
            "rotation_disagreement_deg_max": float(
                thresholds["rotation_disagreement_deg_max"]
            ),
            "nontranslation_rms_native_px_max": float(
                thresholds["nontranslation_rms_native_px_max"]
            ),
            "resampler_relative_change_max": float(
                thresholds["resampler_relative_change_max"]
            ),
        },
    }
    return _raw_gate_record(
        "G6", "GEOMETRY_RESAMPLER_SENSITIVITY", reasons, diagnostics
    )


def _raw_duplicate_correlation(
    cells: Sequence[Mapping[str, Any]],
) -> float | None:
    features: list[np.ndarray] = []
    for cell in cells:
        for path_name in ("R1", "R2"):
            values = cell["coefficients"][path_name]
            features.extend((values.real, values.imag))
    matrix = np.concatenate(features, axis=1)
    matrix = matrix - np.mean(matrix, axis=1, keepdims=True)
    norms = np.linalg.norm(matrix, axis=1)
    if np.any(norms <= 0.0):
        return None
    normalized = matrix / norms[:, np.newaxis]
    correlation = np.abs(normalized @ normalized.T)
    np.fill_diagonal(correlation, -np.inf)
    return float(np.max(correlation))


def _raw_gate_g7(
    evidence: dict[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    indices: np.ndarray,
    common_bounds: Mapping[tuple[str, str], float] | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    diagnostics: dict[str, Any] = {"cells": {}}
    if not evidence["nonperiodic"]["concealed"]:
        reasons.append("NONPERIODIC_LINEAGE_NOT_CONCEALED")
    duplicate = _raw_duplicate_correlation(evidence["cells"])
    if duplicate is None:
        reasons.append("DUPLICATE_SITE_CORRELATION_UNIDENTIFIED")
    elif duplicate >= float(
        thresholds["duplicate_site_correlation_max"]
    ):
        reasons.append("DUPLICATE_SITE_CORRELATION_EXCESS")
    diagnostics["maximum_duplicate_site_correlation"] = duplicate
    diagnostics["duplicate_site_correlation_threshold"] = float(
        thresholds["duplicate_site_correlation_max"]
    )
    if common_bounds is None:
        return _raw_gate_record(
            "G7",
            "NONPERIODIC_REFERENCE_POWER",
            reasons + ["COMMON_MODE_BOUND_INVALID"],
            diagnostics,
        )
    observed: list[float] = []
    draws: list[np.ndarray] = []
    invalid = False
    condition_ceiling = float(thresholds["condition_number_max"])
    for cell in evidence["cells"]:
        point_signal, _, draw_signal, _ = _raw_fixture_stats(
            evidence, cell, contract, indices
        )
        dimension = int(cell["dimension"])
        common = float(common_bounds[(cell["id"], "R")])
        identity = np.eye(dimension, dtype=np.complex128)
        charged = point_signal - common * identity
        draw_charged = draw_signal - common * identity
        valid_point, point_minimum, point_condition = _raw_spd_batch(
            charged, condition_ceiling
        )
        valid_draw, draw_minimum, _ = _raw_spd_batch(
            draw_charged, condition_ceiling
        )
        cell_diagnostics = {
            "signal": _raw_eigen_summary(point_signal[0]),
            "common_mode_upper": common,
            "charged_signal": _raw_eigen_summary(charged[0]),
            "point_power": float(point_minimum[0]),
            "condition_number": _raw_finite(point_condition[0]),
        }
        if not valid_point or not valid_draw:
            invalid = True
            cell_diagnostics["lcb"] = None
        else:
            observed.append(float(point_minimum[0]))
            draws.append(np.asarray(draw_minimum, dtype=np.float64))
        diagnostics["cells"][cell["id"]] = cell_diagnostics
    if invalid:
        reasons.extend(
            [
                "REFERENCE_POWER_NONPOSITIVE_OR_ILL_CONDITIONED",
                "REFERENCE_POWER_FLOOR",
            ]
        )
    else:
        lower, max_t = _raw_simultaneous_lcb(
            np.asarray(observed),
            np.stack(draws, axis=1),
        )
        diagnostics["max_t"] = max_t
        if lower is None:
            reasons.append("REFERENCE_POWER_BOOTSTRAP_INVALID")
        else:
            for cell, value in zip(evidence["cells"], lower):
                diagnostics["cells"][cell["id"]]["lcb"] = float(value)
            if np.any(
                lower <= float(thresholds["reference_power_lcb_min"])
            ):
                reasons.append("REFERENCE_POWER_FLOOR")
    diagnostics["thresholds"] = {
        "reference_power_lcb_min": float(
            thresholds["reference_power_lcb_min"]
        ),
        "condition_number_max": float(thresholds["condition_number_max"]),
    }
    return _raw_gate_record(
        "G7", "NONPERIODIC_REFERENCE_POWER", reasons, diagnostics
    )


def _complex_matrix_json(matrix: np.ndarray) -> list[list[list[float]]]:
    return [
        [
            [float(np.real(value)), float(np.imag(value))]
            for value in row
        ]
        for row in np.asarray(matrix)
    ]


def _raw_dominance_cell(
    cell: Mapping[str, Any],
    difference_factor: float,
    indices: np.ndarray,
    common_r: float,
    common_s: float,
    delta_information: float,
    delta_transfer: float,
    condition_ceiling: float,
) -> tuple[
    dict[str, Any],
    np.ndarray | None,
    list[str],
    dict[str, Any] | None,
]:
    point_r_signal, point_r_noise = _raw_path_stats(
        cell, "R", difference_factor, None
    )
    point_s_signal, point_s_noise = _raw_path_stats(
        cell, "S", difference_factor, None
    )
    draw_r_signal, draw_r_noise = _raw_path_stats(
        cell, "R", difference_factor, indices
    )
    draw_s_signal, draw_s_noise = _raw_path_stats(
        cell, "S", difference_factor, indices
    )
    dimension = int(cell["dimension"])
    identity = np.eye(dimension, dtype=np.complex128)
    charged_point = {
        "signal_R": point_r_signal - common_r * identity,
        "noise_R": point_r_noise + common_r * identity,
        "signal_S": point_s_signal + common_s * identity,
        "noise_S": point_s_noise - common_s * identity,
    }
    charged_draw = {
        "signal_R": draw_r_signal - common_r * identity,
        "noise_R": draw_r_noise + common_r * identity,
        "signal_S": draw_s_signal + common_s * identity,
        "noise_S": draw_s_noise - common_s * identity,
    }
    raw_point = {
        "signal_R": point_r_signal,
        "noise_R": point_r_noise,
        "signal_S": point_s_signal,
        "noise_S": point_s_noise,
    }
    diagnostics: dict[str, Any] = {
        "common_mode_upper_R": common_r,
        "common_mode_upper_S": common_s,
        "raw": {
            name: _raw_eigen_summary(matrix[0])
            for name, matrix in raw_point.items()
        },
        "charged": {
            name: _raw_eigen_summary(matrix[0])
            for name, matrix in charged_point.items()
        },
    }
    reasons: list[str] = []
    raw_signal_r_minimum = float(
        np.linalg.eigvalsh(point_r_signal[0])[0]
    )
    raw_signal_s_minimum = float(
        np.linalg.eigvalsh(point_s_signal[0])[0]
    )
    fraction_r = (
        None
        if raw_signal_r_minimum <= 0.0
        else common_r / raw_signal_r_minimum
    )
    fraction_s = (
        None
        if raw_signal_s_minimum <= 0.0
        else common_s / raw_signal_s_minimum
    )
    diagnostics["common_mode_fraction_R"] = _raw_finite(fraction_r)
    diagnostics["common_mode_fraction_S"] = _raw_finite(fraction_s)
    point_valid = True
    draw_valid = True
    for name in ("signal_R", "noise_R", "signal_S", "noise_S"):
        valid_point, _, _ = _raw_spd_batch(
            charged_point[name], condition_ceiling
        )
        valid_draw, _, _ = _raw_spd_batch(
            charged_draw[name], condition_ceiling
        )
        point_valid &= valid_point
        draw_valid &= valid_draw
    vector_audit: dict[str, Any] | None = None
    if dimension > 1:
        vector_audit = {
            "charged_point_matrices": {
                name: _complex_matrix_json(matrix[0])
                for name, matrix in charged_point.items()
            },
            "raw_point_matrices": {
                name: _complex_matrix_json(matrix[0])
                for name, matrix in raw_point.items()
            },
            "point_positive_definite": point_valid,
            "all_bootstrap_draws_positive_definite": draw_valid,
            "bootstrap_draw_count": int(indices.shape[0]),
            "favorable_average_transfer_ratio": float(
                np.sqrt(
                    np.real(np.trace(point_r_signal[0]))
                    / np.real(np.trace(point_s_signal[0]))
                )
            ),
        }
    if not point_valid:
        reasons.append("NONPOSITIVE_HOSTILE_CHARGE")
    if not draw_valid:
        reasons.append("DOMINANCE_INVALID_BOOTSTRAP_DRAW")
    if not point_valid or not draw_valid:
        diagnostics["information_margin"] = None
        diagnostics["transfer_margin"] = None
        return diagnostics, None, reasons, vector_audit
    information_r_point = _raw_information_operator(
        charged_point["signal_R"], charged_point["noise_R"]
    )
    information_s_point = _raw_information_operator(
        charged_point["signal_S"], charged_point["noise_S"]
    )
    information_ratio_point = _raw_smallest_generalized(
        information_r_point, information_s_point
    )
    transfer_squared_point = _raw_smallest_generalized(
        charged_point["signal_R"], charged_point["signal_S"]
    )
    information_margin_point = np.log(
        information_ratio_point
    ) - math.log1p(delta_information)
    transfer_margin_point = (
        0.5 * np.log(transfer_squared_point)
        - math.log1p(delta_transfer)
    )
    information_r_draw = _raw_information_operator(
        charged_draw["signal_R"], charged_draw["noise_R"]
    )
    information_s_draw = _raw_information_operator(
        charged_draw["signal_S"], charged_draw["noise_S"]
    )
    information_ratio_draw = _raw_smallest_generalized(
        information_r_draw, information_s_draw
    )
    transfer_squared_draw = _raw_smallest_generalized(
        charged_draw["signal_R"], charged_draw["signal_S"]
    )
    if (
        np.any(information_ratio_draw <= 0.0)
        or np.any(transfer_squared_draw <= 0.0)
        or not np.all(np.isfinite(information_ratio_draw))
        or not np.all(np.isfinite(transfer_squared_draw))
    ):
        reasons.append("DOMINANCE_INVALID_BOOTSTRAP_DRAW")
        diagnostics["information_margin"] = float(
            information_margin_point[0]
        )
        diagnostics["transfer_margin"] = float(transfer_margin_point[0])
        return diagnostics, None, reasons, vector_audit
    information_margin_draw = np.log(
        information_ratio_draw
    ) - math.log1p(delta_information)
    transfer_margin_draw = (
        0.5 * np.log(transfer_squared_draw)
        - math.log1p(delta_transfer)
    )
    diagnostics.update(
        {
            "information_generalized_eigenvalue": float(
                information_ratio_point[0]
            ),
            "transfer_generalized_eigenvalue": float(
                transfer_squared_point[0]
            ),
            "transfer_ratio": float(
                np.sqrt(transfer_squared_point[0])
            ),
            "information_margin": float(information_margin_point[0]),
            "transfer_margin": float(transfer_margin_point[0]),
        }
    )
    if dimension > 1:
        diagnostics["vector_rule"] = "SMALLEST_GENERALIZED_EIGENVALUE"
        assert vector_audit is not None
        information_numerator = np.concatenate(
            (information_r_point, information_r_draw), axis=0
        )
        information_denominator = np.concatenate(
            (information_s_point, information_s_draw), axis=0
        )
        transfer_numerator = np.concatenate(
            (charged_point["signal_R"], charged_draw["signal_R"]),
            axis=0,
        )
        transfer_denominator = np.concatenate(
            (charged_point["signal_S"], charged_draw["signal_S"]),
            axis=0,
        )
        vector_audit.update(
            {
                "information_point_matrices": {
                    "reference": _complex_matrix_json(
                        information_r_point[0]
                    ),
                    "scored": _complex_matrix_json(
                        information_s_point[0]
                    ),
                },
                "information_generalized_eigensystem": (
                    _raw_generalized_eigensystem_audit(
                        information_numerator,
                        information_denominator,
                    )
                ),
                "transfer_generalized_eigensystem": (
                    _raw_generalized_eigensystem_audit(
                        transfer_numerator,
                        transfer_denominator,
                    )
                ),
            }
        )
    observed = np.asarray(
        [information_margin_point[0], transfer_margin_point[0]],
        dtype=np.float64,
    )
    bootstrap = np.stack(
        (information_margin_draw, transfer_margin_draw),
        axis=1,
    )
    return (
        diagnostics,
        np.vstack((observed, bootstrap)),
        reasons,
        vector_audit,
    )


def _raw_gate_g8(
    evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    indices: np.ndarray,
    common_bounds: Mapping[tuple[str, str], float] | None,
    common_diagnostics: Mapping[str, Any],
    support_gate_passed: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    diagnostics: dict[str, Any] = {
        "noise_difference_factor": float(
            contract["source_authority"]["noise_difference_factor"]
        ),
        "bootstrap_draws": int(contract["bootstrap"]["draws"]),
        "bootstrap_seed": int(
            contract["bootstrap"]["dominance_seed"]
        ),
        "quantile_method": str(
            contract["bootstrap"]["quantile_method"]
        ),
        "common_mode_family": dict(common_diagnostics),
        "cells": {},
    }
    audits: dict[str, Any] = {"vector_cells": {}}
    if evidence["claim_scope"] == "DIGITAL_K":
        digital_k_policy = contract["digital_k_policy"]
        diagnostics["digital_k_policy"] = {
            "status": str(digital_k_policy["status"]),
            "reason": str(digital_k_policy["reason"]),
            "q_payload_present": evidence["q_baseline"] is not None,
            "q_matrix_alone_sufficient": False,
        }
        return (
            _raw_gate_record(
                "G8",
                "REFERENCE_INFORMATION_DOMINANCE",
                [str(digital_k_policy["reason"])],
                diagnostics,
            ),
            audits,
        )
    if not evidence["reduction_sufficient"]:
        return (
            _raw_gate_record(
                "G8",
                "REFERENCE_INFORMATION_DOMINANCE",
                ["REDUCTION_SUFFICIENCY_NOT_ESTABLISHED"],
                diagnostics,
            ),
            audits,
        )
    if common_bounds is None:
        return (
            _raw_gate_record(
                "G8",
                "REFERENCE_INFORMATION_DOMINANCE",
                ["COMMON_MODE_BOUND_INVALID"],
                diagnostics,
            ),
            audits,
        )
    reasons: list[str] = []
    if not support_gate_passed:
        reasons.append("SUPPORT_FLOOR_NOT_ESTABLISHED")
    observed: list[float] = []
    bootstrap_columns: list[np.ndarray] = []
    labels: list[tuple[str, str]] = []
    difference_factor = float(
        contract["source_authority"]["noise_difference_factor"]
    )
    condition_ceiling = float(thresholds["condition_number_max"])
    common_allowance = float(thresholds["common_mode_fraction_max"])
    for cell in evidence["cells"]:
        cell_id = str(cell["id"])
        delta_information = float(
            thresholds["delta_information_by_cell"][cell_id]
        )
        delta_transfer = float(
            thresholds["delta_transfer_by_cell"][cell_id]
        )
        (
            cell_diagnostics,
            packed,
            cell_reasons,
            vector_audit,
        ) = _raw_dominance_cell(
            cell,
            difference_factor,
            indices,
            float(common_bounds[(cell_id, "R")]),
            float(common_bounds[(cell_id, "S")]),
            delta_information,
            delta_transfer,
            condition_ceiling,
        )
        cell_diagnostics["delta_information"] = delta_information
        cell_diagnostics["delta_transfer"] = delta_transfer
        diagnostics["cells"][cell_id] = cell_diagnostics
        if vector_audit is not None:
            audits["vector_cells"][cell_id] = vector_audit
        reasons.extend(cell_reasons)
        fraction_r = cell_diagnostics["common_mode_fraction_R"]
        fraction_s = cell_diagnostics["common_mode_fraction_S"]
        if (
            fraction_r is None
            or fraction_s is None
            or fraction_r > common_allowance
            or fraction_s > common_allowance
        ):
            reasons.append("COMMON_MODE_FRACTION_EXCESS")
        if packed is not None:
            observed.extend(float(value) for value in packed[0])
            bootstrap_columns.extend(
                (packed[1:, 0].copy(), packed[1:, 1].copy())
            )
            labels.extend(
                ((cell_id, "information"), (cell_id, "transfer"))
            )
    if reasons:
        diagnostics["dominance_max_t"] = None
        return (
            _raw_gate_record(
                "G8",
                "REFERENCE_INFORMATION_DOMINANCE",
                reasons,
                diagnostics,
            ),
            audits,
        )
    lower, max_t = _raw_simultaneous_lcb(
        np.asarray(observed, dtype=np.float64),
        np.stack(bootstrap_columns, axis=1),
    )
    diagnostics["dominance_max_t"] = max_t
    diagnostics["dominance_family_alpha"] = float(
        contract["bootstrap"]["dominance_family_alpha"]
    )
    if lower is None:
        reasons.append("DOMINANCE_BOOTSTRAP_INVALID")
    else:
        for (cell_id, kind), value in zip(labels, lower):
            diagnostics["cells"][cell_id][
                f"{kind}_margin_lcb"
            ] = float(value)
        information_lower = np.asarray(
            [
                value
                for (label, value) in zip(labels, lower)
                if label[1] == "information"
            ]
        )
        transfer_lower = np.asarray(
            [
                value
                for (label, value) in zip(labels, lower)
                if label[1] == "transfer"
            ]
        )
        if np.any(information_lower <= 0.0):
            reasons.append("INFORMATION_NOT_DOMINANT")
        if np.any(transfer_lower <= 0.0):
            reasons.append("TRANSFER_NOT_DOMINANT")
    diagnostics["common_mode_fraction_threshold"] = common_allowance
    return (
        _raw_gate_record(
            "G8",
            "REFERENCE_INFORMATION_DOMINANCE",
            reasons,
            diagnostics,
        ),
        audits,
    )


def _raw_rederive_case(
    evidence: dict[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    thresholds = _raw_thresholds(contract)
    draws = int(contract["bootstrap"]["draws"])
    fixture_indices = _raw_bootstrap_indices(
        evidence["hierarchy"],
        draws,
        int(contract["bootstrap"]["fixture_seed"]),
    )
    dominance_indices = _raw_bootstrap_indices(
        evidence["hierarchy"],
        draws,
        int(contract["bootstrap"]["dominance_seed"]),
    )
    common_bounds, common_diagnostics = _raw_common_mode_bounds(
        evidence, contract, dominance_indices
    )
    gates = [
        _raw_gate_g1(
            evidence,
            contract,
            thresholds,
            fixture_indices,
        ),
        _raw_gate_g2(
            evidence,
            contract,
            thresholds,
            fixture_indices,
            common_bounds,
        ),
        _raw_gate_g3(
            evidence,
            contract,
            thresholds,
            fixture_indices,
        ),
        _raw_gate_g4(evidence, thresholds),
        _raw_gate_g5(evidence, thresholds),
        _raw_gate_g6(evidence, thresholds),
    ]
    gate_g7 = _raw_gate_g7(
        evidence,
        contract,
        thresholds,
        fixture_indices,
        common_bounds,
    )
    gates.append(gate_g7)
    gate_g8, g8_audit = _raw_gate_g8(
        evidence,
        contract,
        thresholds,
        dominance_indices,
        common_bounds,
        common_diagnostics,
        gate_g7["status"] == "PASS",
    )
    gates.append(gate_g8)
    pass_count = sum(gate["status"] == "PASS" for gate in gates)
    unmeasured_count = sum(
        gate["status"] == "UNMEASURED" for gate in gates
    )
    return {
        "claim_scope": evidence["claim_scope"],
        "gates": {str(gate["id"]): gate for gate in gates},
        "counts": {
            "PASS": pass_count,
            "UNMEASURED": unmeasured_count,
            "total": 8,
        },
        "all_gates_pass": pass_count == 8,
        "audits": {
            "G8": g8_audit,
            "fixture_bootstrap_draws": int(fixture_indices.shape[0]),
            "dominance_bootstrap_draws": int(
                dominance_indices.shape[0]
            ),
            "hierarchy_shape": [
                len(evidence["hierarchy"]),
                len(evidence["hierarchy"][0]),
                len(evidence["hierarchy"][0][0]),
            ],
        },
    }


def _rederive_campaign(
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    rederived: dict[str, dict[str, Any]] = {}
    metadata: list[dict[str, Any]] = []
    raw_evidence_by_case: dict[str, dict[str, Any]] = {}
    for raw_case in _list(commission["cases"], "commission.cases"):
        case = _mapping(raw_case, "commission case")
        case_name = _string(case["case"], "commission case name")
        try:
            raw_evidence, payload, envelope_metadata = (
                _decode_embedded_evidence(case, contract)
            )
            prepared = _prepare_evidence(raw_evidence, contract)
            result = _raw_rederive_case(prepared, contract)
        except (VerificationError, KeyError, TypeError, ValueError) as exc:
            raise HarnessError(
                f"{case_name} embedded evidence cannot be independently "
                f"rederived: {exc}"
            ) from exc
        result["evidence_sha256"] = _sha256(payload)
        rederived[case_name] = result
        metadata.append(envelope_metadata)
        raw_evidence_by_case[case_name] = raw_evidence
    if len(rederived) != len(commission["cases"]):
        raise HarnessError("embedded evidence case identities are not unique")
    return rederived, metadata, raw_evidence_by_case


def _normalized_line(line: str) -> str:
    return line.strip(" \t\r\n")


def _anchor_count(source: str, anchor: str) -> int:
    return sum(_normalized_line(line) == anchor for line in source.splitlines())


def _replace_unique_full_line(source: str, anchor: str, replacement: str) -> str:
    for value, name in ((anchor, "anchor"), (replacement, "replacement")):
        if (
            not value
            or value != value.strip()
            or "\r" in value
            or "\n" in value
        ):
            raise HarnessError(f"mutation {name} must be one normalized full line")
    lines = source.splitlines(keepends=True)
    matches = [
        index for index, line in enumerate(lines) if _normalized_line(line) == anchor
    ]
    if len(matches) != 1:
        raise HarnessError(
            "mutation anchor must occur as one complete normalized line; "
            f"found {len(matches)} for {anchor!r}"
        )
    index = matches[0]
    original = lines[index]
    if original.endswith("\r\n"):
        ending = "\r\n"
        body = original[:-2]
    elif original.endswith(("\n", "\r")):
        ending = original[-1]
        body = original[:-1]
    else:
        ending = ""
        body = original
    leading = body[: len(body) - len(body.lstrip(" \t"))]
    trailing = body[len(body.rstrip(" \t")) :]
    lines[index] = f"{leading}{replacement}{trailing}{ending}"
    mutated = "".join(lines)
    if mutated == source:
        raise HarnessError("mutation did not alter synthetic source")
    if _anchor_count(mutated, anchor) != 0:
        raise HarnessError("mutation anchor remained after replacement")
    if _anchor_count(mutated, replacement) != 1:
        raise HarnessError("mutation replacement is not a unique normalized line")
    return mutated


def _git_output(
    repository: pathlib.Path,
    arguments: Sequence[str],
    purpose: str,
    input_payload: bytes | None = None,
) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", os.fspath(repository), *arguments],
            stdin=(
                subprocess.DEVNULL
                if input_payload is None
                else None
            ),
            input=input_payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise VerificationError(f"cannot run git for {purpose}: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise VerificationError(
            f"git failed for {purpose} with exit {completed.returncode}: {detail}"
        )
    return completed.stdout


def _lf_text(payload: bytes, purpose: str) -> str:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise VerificationError(f"{purpose} contains a UTF-8 BOM")
    if b"\r" in payload:
        raise VerificationError(f"{purpose} contains a carriage return")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError(f"{purpose} is not UTF-8: {exc}") from exc


def _line_ending_attribute_check(
    context: CheckContext,
    repository: pathlib.Path,
) -> None:
    output = _git_output(
        repository,
        ("check-attr", "-z", "text", "eol", "--", *ATTRIBUTE_PATHS),
        "M171 line-ending attributes",
    )
    fields = output.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 3:
        raise VerificationError("git check-attr returned malformed -z output")
    observed: dict[str, dict[str, str]] = {}
    for index in range(0, len(fields), 3):
        try:
            path = fields[index].decode("utf-8")
            attribute = fields[index + 1].decode("ascii")
            value = fields[index + 2].decode("ascii")
        except UnicodeDecodeError as exc:
            raise VerificationError(
                f"git check-attr returned undecodable output: {exc}"
            ) from exc
        observed.setdefault(path, {})[attribute] = value
    context.equal(set(observed), set(ATTRIBUTE_PATHS), "attribute path set")
    for path in ATTRIBUTE_PATHS:
        context.equal(
            observed.get(path),
            {"text": "set", "eol": "lf"},
            f"{path} attributes",
        )
    context.evidence.update(
        {
            "policy": LINE_ENDING_POLICY,
            "paths_checked": len(ATTRIBUTE_PATHS),
            "required_attributes": {"text": "set", "eol": "lf"},
        }
    )


def _checkout_representation_check(
    context: CheckContext,
    repository: pathlib.Path,
    payloads_by_path: Mapping[str, bytes],
    expected_sha256_by_path: Mapping[str, str],
) -> None:
    context.equal(
        set(expected_sha256_by_path).issubset(payloads_by_path),
        True,
        "hash-bound checkout path set",
    )
    records: dict[str, dict[str, Any]] = {}
    for path, payload in payloads_by_path.items():
        _lf_text(payload, path)
        raw_object = (
            _git_output(
                repository,
                ("hash-object", "--no-filters", "--stdin"),
                f"raw Git object identity for {path}",
                payload,
            )
            .decode("ascii")
            .strip()
        )
        clean_object = (
            _git_output(
                repository,
                ("hash-object", f"--path={path}", "--stdin"),
                f"clean Git object identity for {path}",
                payload,
            )
            .decode("ascii")
            .strip()
        )
        context.equal(
            clean_object,
            raw_object,
            f"{path} raw bytes equal Git-clean bytes",
        )
        digest = _sha256(payload)
        expected = expected_sha256_by_path.get(path)
        if expected is not None:
            context.equal(digest, expected, f"{path} LF-byte SHA-256")
        records[path] = {
            "raw_sha256": digest,
            "raw_git_object": raw_object,
            "clean_git_object": clean_object,
            "raw_equals_git_clean": raw_object == clean_object,
            "hash_bound": expected is not None,
        }
    context.evidence.update(
        {
            "policy": LINE_ENDING_POLICY,
            "utf8_bom_forbidden": True,
            "carriage_return_forbidden": True,
            "paths": records,
        }
    )


def _upper_tail_formula_check(context: CheckContext) -> None:
    point = np.asarray([10.0, 20.0], dtype=np.float64)
    draws = np.asarray(
        [
            [0.0, 19.0],
            [8.0, 19.5],
            [9.0, 19.8],
            [9.5, 20.1],
            [10.1, 20.2],
        ],
        dtype=np.float64,
    )
    upper, diagnostics = _raw_simultaneous_upper(point, draws, 0.025)
    if upper is None:
        raise VerificationError("asymmetric upper-tail fixture was invalid")
    standard_error = np.std(draws, axis=0, ddof=1)
    correct_root = (
        point[np.newaxis, :] - draws
    ) / standard_error
    inverted_root = (
        draws - point[np.newaxis, :]
    ) / standard_error
    probability = 0.975
    critical = float(
        np.quantile(
            np.max(correct_root, axis=1),
            probability,
            method="higher",
        )
    )
    inverted_critical = float(
        np.quantile(
            np.max(inverted_root, axis=1),
            probability,
            method="higher",
        )
    )
    expected = point + critical * standard_error
    inverted = point + inverted_critical * standard_error
    for index in range(point.size):
        context.close(
            float(upper[index]),
            float(expected[index]),
            f"asymmetric upper[{index}]",
        )
    context.equal(
        diagnostics["studentized_numerator"],
        "observed_minus_bootstrap",
        "asymmetric upper studentized numerator",
    )
    context.equal(
        diagnostics["upper_bound"],
        "observed_plus_critical_times_standard_error",
        "asymmetric upper bound formula",
    )
    context.close(
        diagnostics["quantile_probability"],
        probability,
        "asymmetric upper quantile probability",
    )
    context.equal(
        diagnostics["quantile_method"],
        "higher",
        "asymmetric upper quantile method",
    )
    context.close(
        diagnostics["critical_value"],
        critical,
        "asymmetric upper critical value",
    )
    context.expect(
        critical > inverted_critical + 1.0,
        "asymmetric fixture does not strongly separate the two roots",
    )
    context.expect(
        upper[0] > inverted[0] + 5.0,
        "left-skewed nonnegative fixture understates the hostile UCB",
    )
    context.expect(
        upper[0] >= point[0],
        "hostile UCB fell below its observed common-mode point",
    )
    context.evidence.update(
        {
            "studentized_numerator": diagnostics[
                "studentized_numerator"
            ],
            "upper_bound": diagnostics["upper_bound"],
            "quantile_probability": probability,
            "quantile_method": diagnostics["quantile_method"],
            "correct_critical_value": critical,
            "inverted_critical_value": inverted_critical,
            "left_skewed_nonnegative_point": float(point[0]),
            "left_skewed_nonnegative_ucb": float(upper[0]),
            "inverted_path_ucb": float(inverted[0]),
        }
    )


def _ast_qualified_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _ast_qualified_name(node.value)
        if prefix is not None:
            return f"{prefix}.{node.attr}"
    return None


def _ast_function(
    tree: ast.Module,
    name: str,
    purpose: str,
) -> ast.FunctionDef:
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise VerificationError(
            f"{purpose} must define exactly one {name}"
        )
    return matches[0]


def _ast_literal_assignment(
    tree: ast.Module,
    name: str,
    purpose: str,
) -> Any:
    matches: list[ast.expr] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            matches.append(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and node.value is not None
        ):
            matches.append(node.value)
    if len(matches) != 1:
        raise VerificationError(
            f"{purpose} must assign exactly one {name}"
        )
    try:
        return ast.literal_eval(matches[0])
    except (ValueError, TypeError, SyntaxError) as exc:
        raise VerificationError(
            f"{purpose}.{name} is not a literal"
        ) from exc


def _source_output_safety_audit(
    context: CheckContext,
    source_payloads: Mapping[str, bytes],
) -> None:
    frozen_and_source = {
        ".gitattributes",
        "PREREGISTRATION.md",
        "contract.json",
        "admission.py",
        "synthetic.py",
        "commission.py",
        "test_admission.py",
        "verify.py",
    }
    specifications = {
        "synthetic": {
            "safe_function": "_safe_evidence_output",
            "protected": frozen_and_source
            | {"out/commission.json", "out/verification.json"},
        },
        "commission": {
            "safe_function": "_safe_commission_output",
            "protected": frozen_and_source | {"out/verification.json"},
        },
        "verify": {
            "safe_function": "_safe_verification_output",
            "protected": frozen_and_source | {"out/commission.json"},
        },
    }
    context.equal(
        set(source_payloads),
        set(specifications),
        "output-safety source set",
    )
    records: dict[str, Any] = {}
    for source_name, specification in specifications.items():
        payload = source_payloads[source_name]
        source = _lf_text(payload, f"{source_name} source")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise VerificationError(
                f"{source_name} source cannot be parsed: {exc}"
            ) from exc
        protected = _ast_literal_assignment(
            tree,
            "_PROTECTED_OUTPUT_RELATIVE_PATHS",
            source_name,
        )
        context.expect(
            isinstance(protected, tuple),
            f"{source_name} protected paths must be a tuple",
        )
        protected_values = tuple(str(value) for value in protected)
        context.equal(
            len(protected_values),
            len(set(protected_values)),
            f"{source_name} protected paths are unique",
        )
        context.equal(
            set(protected_values),
            specification["protected"],
            f"{source_name} protected path coverage",
        )

        prefix_function = _ast_function(
            tree,
            "_strip_windows_extended_prefix",
            source_name,
        )
        prefix_literals = {
            node.value.casefold()
            for node in ast.walk(prefix_function)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
        }
        context.expect(
            "\\\\?\\unc\\" in prefix_literals,
            f"{source_name} omits extended UNC prefix normalization",
        )
        context.expect(
            "\\\\?\\" in prefix_literals,
            f"{source_name} omits extended drive prefix normalization",
        )

        key_function = _ast_function(tree, "_path_key", source_name)
        key_calls = {
            _ast_qualified_name(node.func)
            for node in ast.walk(key_function)
            if isinstance(node, ast.Call)
        }
        for required_call in (
            "_strip_windows_extended_prefix",
            "os.path.normpath",
            "os.path.normcase",
        ):
            context.expect(
                required_call in key_calls,
                f"{source_name} path fallback omits {required_call}",
            )
        context.expect(
            any(
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "casefold"
                for node in ast.walk(key_function)
                if isinstance(node, ast.Call)
            ),
            f"{source_name} path fallback omits case folding",
        )

        identity_function = _ast_function(
            tree, "_paths_identical", source_name
        )
        identity_calls = [
            node
            for node in ast.walk(identity_function)
            if isinstance(node, ast.Call)
        ]
        identity_call_names = {
            _ast_qualified_name(node.func) for node in identity_calls
        }
        context.expect(
            "os.path.samefile" in identity_call_names,
            f"{source_name} identity predicate omits os.path.samefile",
        )
        context.expect(
            "_path_key" in identity_call_names,
            f"{source_name} identity predicate omits fallback keys",
        )
        strict_false_resolves = sum(
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "resolve"
            and any(
                keyword.arg == "strict"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is False
                for keyword in call.keywords
            )
            for call in identity_calls
        )
        context.expect(
            strict_false_resolves >= 2,
            f"{source_name} identity predicate must resolve both paths "
            "with strict=False",
        )

        safe_function = _ast_function(
            tree,
            str(specification["safe_function"]),
            source_name,
        )
        safe_calls = {
            _ast_qualified_name(node.func)
            for node in ast.walk(safe_function)
            if isinstance(node, ast.Call)
        }
        context.expect(
            "_paths_identical" in safe_calls,
            f"{source_name} safe output guard bypasses identity predicate",
        )
        if source_name == "synthetic":
            safe_names = {
                node.id
                for node in ast.walk(safe_function)
                if isinstance(node, ast.Name)
            }
            context.expect(
                {"contract", "source_directory"}.issubset(safe_names),
                "synthetic output protection is not anchored to both "
                "contract and executing-source directories",
            )
        records[source_name] = {
            "protected_relative_paths": list(protected_values),
            "samefile_required": True,
            "strict_false_resolves": strict_false_resolves,
            "extended_drive_prefix_normalized": True,
            "extended_unc_prefix_normalized": True,
            "normalized_casefolded_fallback": True,
        }

    verifier_tree = ast.parse(
        _lf_text(source_payloads["verify"], "verify source")
    )
    forbidden_imports: set[str] = set()
    for node in ast.walk(verifier_tree):
        if isinstance(node, ast.Import):
            forbidden_imports.update(
                alias.name.split(".", 1)[0]
                for alias in node.names
                if alias.name.split(".", 1)[0]
                in {"admission", "commission", "synthetic"}
            )
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.split(".", 1)[0]
            in {"admission", "commission", "synthetic"}
        ):
            forbidden_imports.add(node.module.split(".", 1)[0])
    context.equal(
        forbidden_imports,
        set(),
        "independent verifier local-module imports",
    )
    context.evidence["source_audit"] = records


def _output_protection_check(
    context: CheckContext,
    contract_path: pathlib.Path,
    commission_path: pathlib.Path,
    output_path: pathlib.Path,
    source_payloads: Mapping[str, bytes],
) -> None:
    _source_output_safety_audit(context, source_payloads)
    protected = _protected_output_paths(contract_path, commission_path)
    required_by_key = {
        _path_key(path): path
        for path in (
            contract_path,
            commission_path,
            *(
                (HERE / relative).resolve(strict=False)
                for relative in _PROTECTED_OUTPUT_RELATIVE_PATHS
            ),
        )
    }
    protected_keys = {
        _path_key(path) for path, _ in protected
    }
    context.equal(
        protected_keys,
        set(required_by_key),
        "verification protected output path set",
    )
    refused = 0
    for path_key, protected_path in sorted(required_by_key.items()):
        try:
            _safe_verification_output(
                protected_path,
                contract_path,
                commission_path,
            )
        except HarnessError:
            refused += 1
        else:
            context.errors.append(
                f"protected verification output was accepted: {path_key}"
            )
    relative_alias = HERE / "out" / ".." / "admission.py"
    try:
        _safe_verification_output(
            relative_alias,
            contract_path,
            commission_path,
        )
    except HarnessError:
        relative_alias_refused = True
    else:
        relative_alias_refused = False
    context.equal(
        relative_alias_refused,
        True,
        "relative protected-output alias refusal",
    )
    case_alias_refused = None
    extended_alias_refused = None
    if os.name == "nt":
        case_alias = pathlib.Path(
            os.fspath(HERE / "admission.py").swapcase()
        )
        try:
            _safe_verification_output(
                case_alias,
                contract_path,
                commission_path,
            )
        except HarnessError:
            case_alias_refused = True
        else:
            case_alias_refused = False
        context.equal(
            case_alias_refused,
            True,
            "case-insensitive protected-output alias refusal",
        )
        extended_alias = pathlib.Path(
            "\\\\?\\" + os.fspath(HERE / "admission.py")
        )
        try:
            _safe_verification_output(
                extended_alias,
                contract_path,
                commission_path,
            )
        except HarnessError:
            extended_alias_refused = True
        else:
            extended_alias_refused = False
        context.equal(
            extended_alias_refused,
            True,
            "extended-length protected-output alias refusal",
        )
        context.equal(
            _path_key(
                r"\\?\UNC\server\share\folder\..\protected.json"
            ),
            _path_key(r"\\server\share\protected.json"),
            "extended UNC fallback normalization",
        )

    protected_probe = HERE / "admission.py"
    protected_before = _sha256(_read_bytes_once(
        protected_probe, "samefile output-protection probe"
    ))
    with tempfile.TemporaryDirectory(
        prefix="m171-output-identity-"
    ) as temporary:
        alias = pathlib.Path(temporary) / "admission-hardlink.py"
        try:
            os.link(protected_probe, alias)
        except OSError as exc:
            raise VerificationError(
                f"cannot create samefile identity probe: {exc}"
            ) from exc
        try:
            _safe_verification_output(
                alias,
                contract_path,
                commission_path,
            )
        except HarnessError:
            samefile_alias_refused = True
        else:
            samefile_alias_refused = False
        context.equal(
            samefile_alias_refused,
            True,
            "samefile hardlink protected-output alias refusal",
        )
    context.equal(
        _sha256(_read_bytes_once(
            protected_probe, "samefile output-protection probe"
        )),
        protected_before,
        "samefile probe protected bytes",
    )
    active_output = (HERE / "out" / "verification.json").resolve(
        strict=False
    )
    context.equal(
        _safe_verification_output(
            active_output,
            contract_path,
            commission_path,
        ),
        active_output,
        "active verification output remains permitted",
    )
    context.equal(
        _safe_verification_output(
            output_path,
            contract_path,
            commission_path,
        ),
        output_path,
        "requested verification output remains permitted",
    )
    external_probe = (
        output_path.parent / "m171-external-verification-probe.json"
    ).resolve(strict=False)
    context.equal(
        _safe_verification_output(
            external_probe,
            contract_path,
            commission_path,
        ),
        external_probe,
        "external verification output remains permitted",
    )
    context.evidence.update(
        {
            "identity_rule": (
                "os.path.samefile for existing paths; prefix-normalized, "
                "normalized case-folded fallback keys"
            ),
            "protected_path_count": len(required_by_key),
            "protected_paths_refused": refused,
            "relative_alias_refused": relative_alias_refused,
            "case_alias_refused": case_alias_refused,
            "extended_alias_refused": extended_alias_refused,
            "extended_unc_fallback_normalized": os.name == "nt",
            "samefile_hardlink_alias_refused": samefile_alias_refused,
            "active_commission_artifact_protected": True,
            "active_output_permitted": True,
            "external_output_permitted": True,
        }
    )


def _contract_definition_check(
    context: CheckContext,
    contract: Mapping[str, Any],
) -> None:
    expected_root = {
        "schema",
        "frozen_at",
        "amended_at",
        "amendment",
        "integrity_amendment",
        "statistical_amendment",
        "claim_scope",
        "capture_ruling",
        "source_authority",
        "schemas",
        "statuses",
        "sample_contract",
        "cells",
        "bootstrap",
        "inference_contract",
        "digital_k_policy",
        "synthetic_thresholds",
        "production_thresholds_required",
        "gate_definitions",
        "synthetic_fixture",
        "mutations",
        "additional_cases",
        "campaign_counts",
    }
    _expect_keys(context, contract, expected_root, "contract")
    context.equal(
        contract["schema"],
        "m171-reference-admission-contract-v4",
        "contract.schema",
    )
    context.equal(contract["claim_scope"], "GX_REFERENCE_CONDITIONAL", "claim scope")
    context.equal(contract["capture_ruling"], "ANALYSIS_ONLY", "capture ruling")
    schemas = _mapping(contract["schemas"], "contract.schemas")
    context.equal(schemas["evidence"], "m171-reference-admission-evidence-v1", "evidence schema")
    context.equal(schemas["result"], "m171-reference-admission-result-v4", "result schema")
    context.equal(
        schemas["commission"],
        "m171-reference-admission-commission-v4",
        "commission schema",
    )
    context.equal(schemas["verification"], VERIFICATION_SCHEMA, "verification schema")
    inference = _mapping(
        contract["inference_contract"], "contract.inference_contract"
    )
    context.equal(
        inference["max_t_studentized_numerator"],
        "bootstrap_minus_observed",
        "max-t studentized numerator",
    )
    context.equal(
        inference["lower_bound"],
        "observed_minus_critical_times_standard_error",
        "max-t lower bound",
    )
    context.equal(
        inference["upper_max_t_studentized_numerator"],
        "observed_minus_bootstrap",
        "upper max-t studentized numerator",
    )
    context.equal(
        inference["upper_bound"],
        "observed_plus_critical_times_standard_error",
        "max-t upper bound",
    )
    context.equal(
        inference["g2_coordinate"],
        "natural_log_reference_snr",
        "G2 inference coordinate",
    )
    context.equal(
        inference["g2_reported_bound"],
        "exp_coordinate_lower_bound",
        "G2 reported bound",
    )
    digital_k = _mapping(
        contract["digital_k_policy"], "contract.digital_k_policy"
    )
    context.equal(digital_k["status"], "UNMEASURED", "DIGITAL_K status")
    context.equal(
        digital_k["reason"],
        "DIGITAL_K_IDENTIFICATION_NOT_COMMISSIONED",
        "DIGITAL_K reason",
    )
    statuses = _mapping(contract["statuses"], "contract.statuses")
    context.equal(statuses["scientific"], list(SCIENTIFIC_STATUSES), "scientific statuses")
    context.equal(statuses["forbidden"], ["SKIPPED"], "forbidden statuses")
    context.equal(statuses["gate_count"], 8, "gate count")

    cells = _list(contract["cells"], "contract.cells")
    context.equal(len(cells), 16, "contract cell count")
    cell_ids = [_string(_mapping(cell, "contract cell")["id"], "cell id") for cell in cells]
    context.equal(len(set(cell_ids)), 16, "unique contract cell ids")
    context.equal(
        [int(_number(_mapping(cell, "contract cell")["dimension"], "dimension")) for cell in cells],
        [1] * 15 + [2],
        "contract cell dimensions",
    )
    sample = _mapping(contract["sample_contract"], "contract.sample_contract")
    context.equal(sample["site_count"], 64, "site count")
    context.equal(sample["session_count"], 4, "session count")
    context.equal(sample["bursts_per_session"], 2, "bursts per session")
    context.equal(sample["sites_per_burst"], 8, "sites per burst")
    context.equal(sample["native_scored_pixels"], True, "native scored pixels")
    context.equal(sample["reference_only_resampling"], True, "reference-only resampling")

    definitions = _list(contract["gate_definitions"], "contract.gate_definitions")
    expected_gates = [
        ("G1", "SUBJECT_SAMPLING_RATIO"),
        ("G2", "SPLIT_REFERENCE_SNR"),
        ("G3", "REFERENCE_FOCUS_TRANSFER_SUFFICIENCY"),
        ("G4", "LINEAR_UNCLIPPED_RAW"),
        ("G5", "REFERENCE_HALF_AGREEMENT"),
        ("G6", "GEOMETRY_RESAMPLER_SENSITIVITY"),
        ("G7", "NONPERIODIC_REFERENCE_POWER"),
        ("G8", "REFERENCE_INFORMATION_DOMINANCE"),
    ]
    context.equal(
        [(item["id"], item["name"]) for item in definitions],
        expected_gates,
        "ordered gate definitions",
    )
    context.equal(len(_list(contract["mutations"], "contract.mutations")), 8, "mutation count")
    counts = _mapping(contract["campaign_counts"], "contract.campaign_counts")
    context.equal(counts["scientific_cases"], 11, "scientific case count")
    context.equal(counts["gate_evaluations"], 88, "gate evaluation count")
    context.equal(counts["targeted_red_cases"], 9, "targeted RED count")
    context.equal(counts["expected_green_cases"], 2, "expected GREEN count")
    context.equal(counts["capture_reads"], 0, "capture read count")
    context.evidence.update(
        {
            "cell_count": len(cells),
            "gate_ids": [gate_id for gate_id, _ in expected_gates],
            "scientific_cases": counts["scientific_cases"],
            "gate_evaluations": counts["gate_evaluations"],
        }
    )


def _authority_boundary_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    preregistration: str,
) -> None:
    authority = _mapping(contract["source_authority"], "contract.source_authority")
    context.close(authority["noise_difference_factor"], 0.5, "noise difference factor")
    context.close(authority["later_average_noise_factor"], 0.25, "later average factor")
    context.equal(
        authority["production_convention_status"],
        "UNRESOLVED",
        "production convention status",
    )
    required = _list(
        contract["production_thresholds_required"],
        "contract.production_thresholds_required",
    )
    context.expect(
        len(required) >= 14 and len(required) == len(set(required)),
        "production thresholds must be an explicit unique list",
    )
    normalized_preregistration = " ".join(preregistration.split())
    for phrase in (
        "Production admission remains `UNMEASURED`",
        "synthetic commissioning values only",
        "digital `K`",
        "q_k = H_S,k/H_R,k",
        "fixed-exposure subject capture cannot establish arbitrary RAW",
    ):
        context.expect(
            phrase in normalized_preregistration,
            f"preregistration omits {phrase!r}",
        )
    context.evidence.update(
        {
            "noise_difference_factor": 0.5,
            "later_average_noise_factor": 0.25,
            "production_convention_status": "UNRESOLVED",
            "production_threshold_field_count": len(required),
            "production_admission": "UNMEASURED",
        }
    )


def _commission_structure_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
) -> None:
    _expect_keys(
        context,
        commission,
        {
            "schema",
            "status",
            "invalidation_history",
            "cases",
            "policy_probes",
            "partitions",
            "checks",
            "comparisons",
            "mutation_validation",
            "hashes",
            "canaries",
        },
        "commission",
    )
    context.equal(commission["schema"], contract["schemas"]["commission"], "commission.schema")
    context.expect(
        commission["status"] in ("COMMISSIONED", "NOT_COMMISSIONED"),
        "commission.status is outside the v4 outcome vocabulary",
    )
    history = _mapping(
        commission["invalidation_history"], "commission.invalidation_history"
    )
    amendment = _mapping(contract["amendment"], "contract.amendment")
    integrity_amendment = _mapping(
        contract["integrity_amendment"],
        "contract.integrity_amendment",
    )
    statistical_amendment = _mapping(
        contract["statistical_amendment"],
        "contract.statistical_amendment",
    )
    context.equal(
        dict(history),
        {
            "v1": {
                "status": "INVALIDATED",
                "amendment": 1,
                "commission_sha256": amendment[
                    "invalidated_commission_sha256"
                ],
                "verification_sha256": amendment[
                    "invalidated_verification_sha256"
                ],
            },
            "v2": {
                "status": "INVALIDATED",
                "amendment": 2,
                "commission_sha256": integrity_amendment[
                    "invalidated_commission_sha256"
                ],
                "verification_sha256": integrity_amendment[
                    "invalidated_verification_sha256"
                ],
            },
            "v3": {
                "status": "INVALIDATED",
                "amendment": 3,
                "commission_sha256": statistical_amendment[
                    "invalidated_commission_sha256"
                ],
                "verification_sha256": statistical_amendment[
                    "invalidated_verification_sha256"
                ],
            },
        },
        "v1, v2, and v3 artifact invalidation history",
    )
    mutations = _list(contract["mutations"], "contract.mutations")
    expected_names = [
        "baseline",
        *[mutation["case"] for mutation in mutations],
        "planted_improvement",
        "common_mode_false_improvement",
    ]
    cases = _list(commission["cases"], "commission.cases")
    context.equal(len(cases), 11, "commission case count")
    context.equal([case["case"] for case in cases], expected_names, "commission case order")
    definitions = _list(contract["gate_definitions"], "contract.gate_definitions")
    expected_gates = [(gate["id"], gate["name"]) for gate in definitions]
    base_keys = {
        "case",
        "kind",
        "generator_source_sha256",
        "evidence_sha256",
        "embedded_evidence",
        "capture_reads",
        "result_schema",
        "profile",
        "claim_scope",
        "counts",
        "all_gates_pass",
        "gates",
        "expected",
        "expectation_met",
        "outcome",
    }
    for index, raw_case in enumerate(cases):
        case = _mapping(raw_case, f"commission.cases[{index}]")
        expected_keys = set(base_keys)
        if case["kind"] == "source_mutation":
            expected_keys.add("mutation")
        if case["kind"] in ("planted_improvement", "common_mode_false_improvement"):
            expected_keys.add("comparison")
        _expect_keys(context, case, expected_keys, f"case {case['case']}")
        context.equal(case["result_schema"], contract["schemas"]["result"], f"{case['case']} schema")
        context.equal(case["profile"], "synthetic_commission", f"{case['case']} profile")
        context.equal(case["claim_scope"], contract["claim_scope"], f"{case['case']} scope")
        _hash(case["generator_source_sha256"], f"{case['case']}.generator_source_sha256")
        _hash(case["evidence_sha256"], f"{case['case']}.evidence_sha256")
        gates = _list(case["gates"], f"{case['case']}.gates")
        context.equal(len(gates), 8, f"{case['case']} gate count")
        context.equal(
            [(gate["id"], gate["name"]) for gate in gates],
            expected_gates,
            f"{case['case']} ordered gates",
        )
        for gate in gates:
            _expect_keys(
                context,
                _mapping(gate, f"{case['case']}.{gate['id']}"),
                (
                    "id",
                    "name",
                    "status",
                    "evaluated",
                    "reason_codes",
                    "claim_value",
                    "diagnostics",
                ),
                f"{case['case']}.{gate['id']}",
            )
    context.evidence["ordered_cases"] = expected_names


def _status_semantics_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
) -> None:
    allowed = set(contract["statuses"]["scientific"])
    forbidden = set(contract["statuses"]["forbidden"])
    for raw_case in _list(commission["cases"], "commission.cases"):
        case = _mapping(raw_case, "commission case")
        statuses: list[str] = []
        for gate in _list(case["gates"], f"{case['case']}.gates"):
            status = _string(gate["status"], f"{case['case']}.{gate['id']}.status")
            statuses.append(status)
            context.expect(status in allowed, f"{case['case']}.{gate['id']} has invalid status")
            context.expect(status not in forbidden, f"{case['case']}.{gate['id']} is forbidden")
            context.equal(gate["evaluated"], True, f"{case['case']}.{gate['id']}.evaluated")
            reasons = _reason_codes(gate, f"{case['case']}.{gate['id']}")
            if status == "PASS":
                context.equal(reasons, [], f"{case['case']}.{gate['id']} PASS reasons")
                context.equal(
                    gate["claim_value"],
                    "ESTABLISHED",
                    f"{case['case']}.{gate['id']} PASS claim",
                )
            elif status == "UNMEASURED":
                context.expect(bool(reasons), f"{case['case']}.{gate['id']} needs a reason")
                context.equal(
                    gate["claim_value"],
                    None,
                    f"{case['case']}.{gate['id']} UNMEASURED claim",
                )
        counts = _mapping(case["counts"], f"{case['case']}.counts")
        _expect_keys(context, counts, ("PASS", "UNMEASURED", "total"), f"{case['case']}.counts")
        context.equal(counts["PASS"], statuses.count("PASS"), f"{case['case']} PASS count")
        context.equal(
            counts["UNMEASURED"],
            statuses.count("UNMEASURED"),
            f"{case['case']} UNMEASURED count",
        )
        context.equal(counts["total"], 8, f"{case['case']} total")
        context.equal(
            counts["PASS"] + counts["UNMEASURED"],
            8,
            f"{case['case']} exact partition",
        )
        context.equal(
            case["all_gates_pass"],
            statuses == ["PASS"] * 8,
            f"{case['case']} all_gates_pass",
        )
    context.evidence.update(
        {
            "allowed_statuses": sorted(allowed),
            "forbidden_statuses_observed": 0,
            "evaluated_gates": 88,
        }
    )


def _campaign_partition_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
) -> None:
    cases = _list(commission["cases"], "commission.cases")
    statuses = [gate["status"] for case in cases for gate in case["gates"]]
    recomputed = {
        "scientific_cases": len(cases),
        "gate_evaluations": len(statuses),
        "PASS": statuses.count("PASS"),
        "UNMEASURED": statuses.count("UNMEASURED"),
        "PASS_plus_UNMEASURED": statuses.count("PASS")
        + statuses.count("UNMEASURED"),
        "targeted_red_cases": sum(case["outcome"] == "RED_CAUGHT" for case in cases),
        "expected_green_cases": sum(case["outcome"] == "GREEN" for case in cases),
        "skipped": sum(status not in SCIENTIFIC_STATUSES for status in statuses),
        "capture_reads": sum(_integer(case["capture_reads"], "capture_reads") for case in cases),
    }
    partitions = _mapping(commission["partitions"], "commission.partitions")
    _expect_keys(context, partitions, recomputed.keys(), "commission.partitions")
    for name, expected in recomputed.items():
        context.equal(partitions[name], expected, f"commission.partitions.{name}")
    expected_counts = _mapping(contract["campaign_counts"], "contract.campaign_counts")
    for name in (
        "scientific_cases",
        "gate_evaluations",
        "targeted_red_cases",
        "expected_green_cases",
        "capture_reads",
    ):
        context.equal(recomputed[name], expected_counts[name], f"campaign {name}")
    context.equal(recomputed["PASS_plus_UNMEASURED"], 88, "complete 88-gate partition")
    context.equal(recomputed["skipped"], 0, "skipped gates")
    context.evidence.update(recomputed)


def _evidence_hash_check(
    context: CheckContext,
    commission: Mapping[str, Any],
    rederived: Mapping[str, Mapping[str, Any]],
    embedded_metadata: Sequence[Mapping[str, Any]],
) -> None:
    hashes = _mapping(commission["hashes"], "commission.hashes")
    _expect_keys(
        context,
        hashes,
        (
            "contract_sha256",
            "source_line_ending_policy",
            "admission_source_before_sha256",
            "admission_source_after_sha256",
            "admission_source_unchanged",
            "commission_source_before_sha256",
            "commission_source_after_sha256",
            "commission_source_unchanged",
            "synthetic_source_before_sha256",
            "synthetic_source_after_sha256",
            "synthetic_source_unchanged",
            "evidence_sha256_by_case",
        ),
        "commission.hashes",
    )
    context.equal(
        _hash(hashes["contract_sha256"], "commission.hashes.contract_sha256"),
        FROZEN_CONTRACT_SHA256,
        "commission contract binding",
    )
    context.equal(
        hashes["source_line_ending_policy"],
        LINE_ENDING_POLICY,
        "commission source line-ending policy",
    )
    evidence_hashes = _mapping(
        hashes["evidence_sha256_by_case"],
        "commission.hashes.evidence_sha256_by_case",
    )
    cases = _list(commission["cases"], "commission.cases")
    context.equal(set(evidence_hashes), {case["case"] for case in cases}, "evidence hash cases")
    for case in cases:
        case_name = _string(case["case"], "commission case name")
        context.equal(
            _hash(evidence_hashes[case_name], f"{case_name} evidence map hash"),
            _hash(case["evidence_sha256"], f"{case_name} evidence hash"),
            f"{case_name} evidence hash binding",
        )
        context.equal(
            rederived[case_name]["evidence_sha256"],
            _hash(case["evidence_sha256"], f"{case_name} evidence hash"),
            f"{case_name} exact decompressed evidence hash",
        )
        context.equal(
            rederived[case_name]["counts"],
            case["counts"],
            f"{case_name} raw-evidence gate counts",
        )
        context.equal(
            rederived[case_name]["all_gates_pass"],
            case["all_gates_pass"],
            f"{case_name} raw-evidence all-gates outcome",
        )
    context.equal(
        len(embedded_metadata),
        len(cases),
        "embedded evidence metadata count",
    )
    context.evidence.update(
        {
            "bound_evidence_hashes": len(evidence_hashes),
            "embedded_evidence_cases": len(embedded_metadata),
            "encoding": "base64+gzip(mtime=0)",
            "compressed_length_bytes": sum(
                int(item["compressed_length_bytes"])
                for item in embedded_metadata
            ),
            "uncompressed_length_bytes": sum(
                int(item["uncompressed_length_bytes"])
                for item in embedded_metadata
            ),
            "exact_decompressed_payload_hashes_verified": len(cases),
        }
    )


def _source_mutation_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    admission_source_payload: bytes,
    commission_source_payload: bytes,
    synthetic_source_payload: bytes,
) -> None:
    try:
        source = synthetic_source_payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError(f"synthetic source is not UTF-8: {exc}") from exc
    source_payloads = {
        "admission": admission_source_payload,
        "commission": commission_source_payload,
        "synthetic": synthetic_source_payload,
    }
    source_hashes = {
        name: _sha256(payload)
        for name, payload in source_payloads.items()
    }
    expected_source_hashes = {
        "admission": FROZEN_ADMISSION_SOURCE_SHA256,
        "commission": FROZEN_COMMISSION_SOURCE_SHA256,
        "synthetic": FROZEN_SYNTHETIC_SOURCE_SHA256,
    }
    for name, payload in source_payloads.items():
        context.expect(
            not payload.startswith(b"\xef\xbb\xbf"),
            f"{name} source contains a UTF-8 BOM",
        )
        context.expect(
            b"\r" not in payload,
            f"{name} source contains a carriage return",
        )
        context.equal(
            source_hashes[name],
            expected_source_hashes[name],
            f"frozen {name} source SHA-256",
        )
    source_sha256 = source_hashes["synthetic"]
    hashes = _mapping(commission["hashes"], "commission.hashes")
    context.equal(
        hashes["source_line_ending_policy"],
        LINE_ENDING_POLICY,
        "source binding line-ending policy",
    )
    for name, actual_sha256 in source_hashes.items():
        context.equal(
            _hash(
                hashes[f"{name}_source_before_sha256"],
                f"{name} source before hash",
            ),
            actual_sha256,
            f"{name} source before",
        )
        context.equal(
            _hash(
                hashes[f"{name}_source_after_sha256"],
                f"{name} source after hash",
            ),
            actual_sha256,
            f"{name} source after",
        )
        context.equal(
            hashes[f"{name}_source_unchanged"],
            True,
            f"{name} source unchanged flag",
        )
    context.equal(
        commission["checks"]["source_unchanged"],
        True,
        "aggregate source unchanged check",
    )

    cases = _case_map(commission)
    for name in ("baseline", "planted_improvement", "common_mode_false_improvement"):
        context.equal(
            _hash(cases[name]["generator_source_sha256"], f"{name} generator hash"),
            source_sha256,
            f"{name} unmutated source hash",
        )
    validations = _list(commission["mutation_validation"], "mutation_validation")
    mutations = _list(contract["mutations"], "contract.mutations")
    context.equal(len(validations), 8, "mutation validation count")
    context.equal(len(mutations), 8, "contract mutation count")
    records: list[dict[str, Any]] = []
    for index, mutation in enumerate(mutations):
        _expect_keys(
            context,
            _mapping(mutation, f"contract.mutations[{index}]"),
            ("case", "anchor", "replacement", "target_gate", "reason"),
            f"contract.mutations[{index}]",
        )
        validation = _mapping(validations[index], f"mutation_validation[{index}]")
        _expect_keys(
            context,
            validation,
            (
                "case",
                "anchor",
                "replacement",
                "target_gate",
                "reason",
                "anchor_count",
                "mutation_applied",
                "mutated_source_sha256",
            ),
            f"mutation_validation[{index}]",
        )
        for field_name in ("case", "anchor", "replacement", "target_gate", "reason"):
            context.equal(
                validation[field_name],
                mutation[field_name],
                f"mutation_validation[{index}].{field_name}",
            )
        anchor = _string(mutation["anchor"], f"mutation[{index}].anchor")
        replacement = _string(mutation["replacement"], f"mutation[{index}].replacement")
        context.equal(_anchor_count(source, anchor), 1, f"{mutation['case']} anchor count")
        mutated = _replace_unique_full_line(source, anchor, replacement).encode("utf-8")
        mutated_sha256 = _sha256(mutated)
        context.equal(validation["anchor_count"], 1, f"{mutation['case']} recorded anchor count")
        context.equal(validation["mutation_applied"], True, f"{mutation['case']} applied")
        context.equal(
            _hash(validation["mutated_source_sha256"], f"{mutation['case']} mutation hash"),
            mutated_sha256,
            f"{mutation['case']} independently mutated hash",
        )
        case = cases[_string(mutation["case"], f"mutation[{index}].case")]
        context.equal(
            _hash(case["generator_source_sha256"], f"{mutation['case']} case source hash"),
            mutated_sha256,
            f"{mutation['case']} generator source hash",
        )
        records.append(
            {
                "case": mutation["case"],
                "mutated_source_sha256": mutated_sha256,
                "reason": mutation["reason"],
                "target_gate": mutation["target_gate"],
            }
        )
    context.evidence.update(
        {
            "implementation_source_sha256": source_hashes,
            "synthetic_source_sha256": source_sha256,
            "mutation_count": len(records),
            "mutations": records,
        }
    )


def _mutation_mapping_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
) -> None:
    cases = _case_map(commission)
    evidence: list[dict[str, Any]] = []
    for index, mutation in enumerate(_list(contract["mutations"], "contract.mutations")):
        case_name = mutation["case"]
        case = cases[case_name]
        context.equal(case["kind"], "source_mutation", f"{case_name} kind")
        recorded = _mapping(case["mutation"], f"{case_name}.mutation")
        expected_record = {
            "anchor": mutation["anchor"],
            "replacement": mutation["replacement"],
            "target_gate": mutation["target_gate"],
            "reason": mutation["reason"],
            "applied": True,
        }
        context.equal(dict(recorded), expected_record, f"{case_name} mutation mapping")
        context.equal(
            case["expected"],
            {
                "gate": mutation["target_gate"],
                "status": "UNMEASURED",
                "reason": mutation["reason"],
            },
            f"{case_name} expected result",
        )
        target = _gate(case, mutation["target_gate"])
        reasons = _reason_codes(target, f"{case_name}.{mutation['target_gate']}")
        context.equal(target["status"], "UNMEASURED", f"{case_name} target status")
        context.expect(mutation["reason"] in reasons, f"{case_name} target reason missing")
        context.equal(case["expectation_met"], True, f"{case_name} expectation")
        context.equal(case["outcome"], "RED_CAUGHT", f"{case_name} outcome")
        evidence.append(
            {
                "case": case_name,
                "target_gate": mutation["target_gate"],
                "required_reason": mutation["reason"],
                "observed_unmeasured_gates": [
                    gate["id"] for gate in case["gates"] if gate["status"] == "UNMEASURED"
                ],
            }
        )
    context.evidence["targeted_mutations"] = evidence


def _canary_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    source_payload: bytes,
    kind: str,
) -> None:
    source = source_payload.decode("utf-8")
    mutation = _mapping(contract["mutations"][0], "contract.mutations[0]")
    anchor = mutation["anchor"]
    replacement = mutation["replacement"]
    if kind == "missing_full_line_anchor":
        modified = "".join(
            line
            for line in source.splitlines(keepends=True)
            if _normalized_line(line) != anchor
        )
        expected_count = 0
    elif kind == "duplicate_full_line_anchor":
        separator = "" if source.endswith(("\r", "\n")) else "\n"
        modified = f"{source}{separator}{anchor}\n"
        expected_count = 2
    else:
        raise VerificationError(f"unknown canary kind {kind}")
    observed_count = _anchor_count(modified, anchor)
    try:
        _replace_unique_full_line(modified, anchor, replacement)
    except HarnessError as exc:
        error = str(exc)
        hard_error = True
    else:
        error = None
        hard_error = False
    expected_error = (
        "mutation anchor must occur as one complete normalized line; "
        f"found {expected_count} for {anchor!r}"
    )
    recorded = _mapping(commission["canaries"][kind], f"commission.canaries.{kind}")
    context.equal(observed_count, expected_count, f"{kind} independent anchor count")
    context.equal(hard_error, True, f"{kind} independent hard error")
    context.equal(error, expected_error, f"{kind} independent error")
    context.equal(recorded["status"], "PASS", f"{kind} recorded status")
    context.equal(recorded["hard_error"], True, f"{kind} recorded hard error")
    context.equal(recorded["mapped_exit_code"], 2, f"{kind} mapped exit code")
    context.equal(recorded["observed_anchor_count"], expected_count, f"{kind} recorded count")
    context.equal(recorded["expected_anchor_count"], expected_count, f"{kind} expected count")
    context.equal(recorded["error"], expected_error, f"{kind} recorded error")
    context.evidence.update(
        {
            "anchor": anchor,
            "anchor_count": expected_count,
            "hard_error": hard_error,
            "mapped_exit_code": 2,
        }
    )


def _g1_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    threshold = _number(contract["synthetic_thresholds"]["sampling_ratio_lcb_min"], "G1 threshold")
    values: dict[str, float] = {}
    for case in commission["cases"]:
        gate = _gate(case, "G1")
        _compare_rederived_tree(
            context,
            gate,
            rederived[case["case"]]["gates"]["G1"],
            f"{case['case']}.G1 exact raw-evidence rederivation",
        )
        diagnostics = _mapping(gate["diagnostics"], f"{case['case']}.G1.diagnostics")
        _expect_keys(
            context,
            diagnostics,
            (
                "ratio_mean",
                "ratio_minimum",
                "simultaneous_lcb",
                "optical_systematic_ratio_bound",
                "systematic_adjusted_lcb",
                "threshold",
                "max_t",
            ),
            f"{case['case']}.G1.diagnostics",
        )
        mean = _number(diagnostics["ratio_mean"], f"{case['case']}.G1.ratio_mean")
        minimum = _number(diagnostics["ratio_minimum"], f"{case['case']}.G1.ratio_minimum")
        lcb = _number(diagnostics["simultaneous_lcb"], f"{case['case']}.G1.lcb")
        systematic = _number(
            diagnostics["optical_systematic_ratio_bound"],
            f"{case['case']}.G1.systematic",
        )
        adjusted = _number(
            diagnostics["systematic_adjusted_lcb"],
            f"{case['case']}.G1.adjusted_lcb",
        )
        critical, errors = _max_t(context, diagnostics["max_t"], 1, f"{case['case']}.G1.max_t")
        context.close(lcb, mean - critical * errors[0], f"{case['case']}.G1 LCB relation")
        context.close(adjusted, lcb - systematic, f"{case['case']}.G1 systematic charge")
        context.close(diagnostics["threshold"], threshold, f"{case['case']}.G1 threshold")
        context.expect(minimum <= mean, f"{case['case']}.G1 minimum exceeds mean")
        expected_reasons = (
            ["SAMPLING_RATIO_NOT_ESTABLISHED"] if adjusted < threshold else []
        )
        context.equal(
            _reason_codes(gate, f"{case['case']}.G1"),
            expected_reasons,
            f"{case['case']}.G1 directional reasons",
        )
        context.equal(
            gate["status"],
            "PASS" if not expected_reasons else "UNMEASURED",
            f"{case['case']}.G1 directional status",
        )
        values[case["case"]] = adjusted
    context.evidence.update(
        {
            "threshold": threshold,
            "baseline_systematic_adjusted_lcb": values["baseline"],
            "low_sampling_systematic_adjusted_lcb": values["g1_low_sampling"],
            "exact_raw_evidence_cases": len(rederived),
            "bootstrap_indices_and_draws_regenerated": True,
        }
    )


def _g2_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    cell_dimensions: Mapping[str, int],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    threshold = _number(contract["synthetic_thresholds"]["reference_snr_lcb_min"], "G2 threshold")
    condition_ceiling = _number(
        contract["synthetic_thresholds"]["condition_number_max"],
        "G2 condition ceiling",
    )
    minima: dict[str, float | None] = {}
    for case in commission["cases"]:
        gate = _gate(case, "G2")
        _compare_rederived_tree(
            context,
            gate,
            rederived[case["case"]]["gates"]["G2"],
            f"{case['case']}.G2 exact raw-evidence rederivation",
        )
        diagnostics = _mapping(gate["diagnostics"], f"{case['case']}.G2.diagnostics")
        context.equal(
            diagnostics["inference_coordinate"],
            "natural_log_reference_snr",
            f"{case['case']}.G2 inference coordinate",
        )
        context.equal(
            diagnostics["reported_bound"],
            "exp_coordinate_lower_bound",
            f"{case['case']}.G2 reported bound",
        )
        cells = _mapping(diagnostics["cells"], f"{case['case']}.G2.cells")
        context.equal(set(cells), set(cell_dimensions), f"{case['case']}.G2 cells")
        invalid = False
        snrs: list[float] = []
        cell_records: list[tuple[str, Mapping[str, Any]]] = []
        g8_cells = _mapping(
            _gate(case, "G8")["diagnostics"]["cells"],
            f"{case['case']}.G8.cells",
        )
        for cell_id, dimension in cell_dimensions.items():
            cell = _mapping(cells[cell_id], f"{case['case']}.G2.{cell_id}")
            signal = _eigen_summary(context, cell["signal"], dimension, f"{case['case']}.G2.{cell_id}.signal")
            noise = _eigen_summary(context, cell["noise"], dimension, f"{case['case']}.G2.{cell_id}.noise")
            charged_signal = _eigen_summary(
                context,
                cell["charged_signal"],
                dimension,
                f"{case['case']}.G2.{cell_id}.charged_signal",
            )
            charged_noise = _eigen_summary(
                context,
                cell["charged_noise"],
                dimension,
                f"{case['case']}.G2.{cell_id}.charged_noise",
            )
            common = _number(cell["common_mode_upper"], f"{case['case']}.G2.{cell_id}.common")
            for index in range(dimension):
                context.close(
                    charged_signal[index],
                    signal[index] - common,
                    f"{case['case']}.G2.{cell_id}.signal charge[{index}]",
                )
                context.close(
                    charged_noise[index],
                    noise[index] + common,
                    f"{case['case']}.G2.{cell_id}.noise charge[{index}]",
                )
            context.close(
                common,
                g8_cells[cell_id]["common_mode_upper_R"],
                f"{case['case']}.G2.{cell_id} common bound binding",
            )
            cell_valid = (
                charged_signal[0] > 0.0
                and charged_noise[0] > 0.0
                and charged_signal[-1] / charged_signal[0] <= condition_ceiling
                and charged_noise[-1] / charged_noise[0] <= condition_ceiling
            )
            invalid |= not cell_valid
            if cell_valid:
                snr = _number(cell["snr"], f"{case['case']}.G2.{cell_id}.snr")
                lower_bound = charged_signal[0] / charged_noise[-1]
                upper_bound = charged_signal[-1] / charged_noise[0]
                context.expect(
                    lower_bound - ABS_TOL <= snr <= upper_bound + ABS_TOL,
                    f"{case['case']}.G2.{cell_id}.snr violates eigenvalue bounds",
                )
                if dimension == 1:
                    context.close(
                        snr,
                        charged_signal[0] / charged_noise[0],
                        f"{case['case']}.G2.{cell_id}.scalar snr",
                    )
                context.close(
                    cell["log_snr"],
                    math.log(snr),
                    f"{case['case']}.G2.{cell_id}.log SNR",
                )
                snrs.append(snr)
                cell_records.append((cell_id, cell))
        reasons = _reason_codes(gate, f"{case['case']}.G2")
        if invalid:
            expected_reasons = [
                "REFERENCE_SNR_NONPOSITIVE_OR_ILL_CONDITIONED",
                "REFERENCE_SNR_INSUFFICIENT",
            ]
            context.equal(reasons, expected_reasons, f"{case['case']}.G2 invalid reasons")
            context.equal(gate["status"], "UNMEASURED", f"{case['case']}.G2 invalid status")
            minima[case["case"]] = None
        else:
            critical, errors = _max_t(
                context,
                diagnostics["max_t"],
                len(cell_dimensions),
                f"{case['case']}.G2.max_t",
            )
            lcbs: list[float] = []
            for index, (cell_id, cell) in enumerate(cell_records):
                log_snr = _number(
                    cell["log_snr"],
                    f"{case['case']}.G2.{cell_id}.log_snr",
                )
                log_lcb = _number(
                    cell["log_snr_lcb"],
                    f"{case['case']}.G2.{cell_id}.log_snr_lcb",
                )
                context.close(
                    log_lcb,
                    log_snr - critical * errors[index],
                    f"{case['case']}.G2.{cell_id}.log LCB relation",
                )
                snr_lcb = _number(
                    cell["snr_lcb"],
                    f"{case['case']}.G2.{cell_id}.snr_lcb",
                )
                context.close(
                    snr_lcb,
                    math.exp(log_lcb),
                    f"{case['case']}.G2.{cell_id}.exp LCB relation",
                )
                lcbs.append(snr_lcb)
            expected_reasons = (
                ["REFERENCE_SNR_INSUFFICIENT"]
                if any(value <= threshold for value in lcbs)
                else []
            )
            context.equal(reasons, expected_reasons, f"{case['case']}.G2 threshold reasons")
            context.equal(
                gate["status"],
                "PASS" if not expected_reasons else "UNMEASURED",
                f"{case['case']}.G2 threshold status",
            )
            minima[case["case"]] = min(lcbs)
        context.close(diagnostics["threshold"], threshold, f"{case['case']}.G2 threshold")
    context.evidence.update(
        {
            "threshold": threshold,
            "coordinate": "natural_log_reference_snr",
            "reported_bound": "exp_coordinate_lower_bound",
            "max_t_studentized_numerator": "bootstrap_minus_observed",
            "baseline_minimum_snr_lcb": minima["baseline"],
            "high_noise_minimum_snr_lcb": minima["g2_high_reference_noise"],
            "all_cells_checked_per_valid_case": len(cell_dimensions),
            "vector_snr_check": (
                "EXACT_GENERALIZED_EIGENVALUE_FROM_RECONSTRUCTED_MATRICES"
            ),
            "exact_raw_evidence_cases": len(rederived),
            "bootstrap_indices_and_draws_regenerated": True,
        }
    )


def _g3_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    cell_dimensions: Mapping[str, int],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    thresholds = contract["synthetic_thresholds"]
    transfer_floor = _number(
        thresholds["focus_transfer_singular_value_lcb_min"],
        "G3 transfer floor",
    )
    condition_ceiling = _number(thresholds["condition_number_max"], "G3 condition")
    leakage_ceiling = _number(thresholds["cross_cell_leakage_max"], "G3 leakage")
    decisive: dict[str, Any] = {}
    for case in commission["cases"]:
        gate = _gate(case, "G3")
        _compare_rederived_tree(
            context,
            gate,
            rederived[case["case"]]["gates"]["G3"],
            f"{case['case']}.G3 exact raw-evidence rederivation",
        )
        diagnostics = _mapping(gate["diagnostics"], f"{case['case']}.G3.diagnostics")
        cells = _mapping(diagnostics["cells"], f"{case['case']}.G3.cells")
        context.equal(set(cells), set(cell_dimensions), f"{case['case']}.G3 cells")
        critical, errors = _max_t(
            context,
            diagnostics["max_t"],
            len(cell_dimensions),
            f"{case['case']}.G3.max_t",
        )
        expected_reasons: list[str] = []
        lcbs: list[float] = []
        peaks: list[int] = []
        for index, cell_id in enumerate(cell_dimensions):
            cell = _mapping(cells[cell_id], f"{case['case']}.G3.{cell_id}")
            response = [
                _number(value, f"{case['case']}.G3.{cell_id}.response")
                for value in _list(cell["response_by_position"], "G3 response")
            ]
            context.equal(len(response), 5, f"{case['case']}.G3.{cell_id} response length")
            peak = response.index(max(response))
            unique = response.count(max(response)) == 1
            interior = 0 < peak < len(response) - 1
            context.equal(cell["peak_index"], peak, f"{case['case']}.G3.{cell_id} peak")
            context.equal(cell["peak_unique"], unique, f"{case['case']}.G3.{cell_id} unique")
            context.equal(cell["peak_interior"], interior, f"{case['case']}.G3.{cell_id} interior")
            context.equal(cell["known_input"], True, f"{case['case']}.G3.{cell_id} known input")
            smallest = _number(
                cell["smallest_singular_value"],
                f"{case['case']}.G3.{cell_id}.smallest",
            )
            condition = _optional_number(
                cell["condition_number"],
                f"{case['case']}.G3.{cell_id}.condition",
            )
            leakage = _number(
                cell["cross_cell_leakage"],
                f"{case['case']}.G3.{cell_id}.leakage",
            )
            lcb = _number(
                cell["smallest_singular_value_lcb"],
                f"{case['case']}.G3.{cell_id}.lcb",
            )
            context.close(
                lcb,
                smallest - critical * errors[index],
                f"{case['case']}.G3.{cell_id}.LCB relation",
            )
            if not unique or not interior:
                expected_reasons.append("FOCUS_PEAK_NOT_INTERIOR")
            if condition is None or condition > condition_ceiling:
                expected_reasons.append("FOCUS_TRANSFER_ILL_CONDITIONED")
            if leakage > leakage_ceiling:
                expected_reasons.append("CROSS_CELL_LEAKAGE_EXCESS")
            lcbs.append(lcb)
            peaks.append(peak)
        if any(value <= transfer_floor for value in lcbs):
            expected_reasons.append("FOCUS_TRANSFER_INSUFFICIENT")
        expected_reasons = list(dict.fromkeys(expected_reasons))
        context.equal(
            _reason_codes(gate, f"{case['case']}.G3"),
            expected_reasons,
            f"{case['case']}.G3 directional reasons",
        )
        context.equal(
            gate["status"],
            "PASS" if not expected_reasons else "UNMEASURED",
            f"{case['case']}.G3 directional status",
        )
        if case["case"] in ("baseline", "g3_endpoint_focus"):
            decisive[case["case"]] = {
                "minimum_transfer_lcb": min(lcbs),
                "peak_indices": sorted(set(peaks)),
            }
    context.evidence.update(
        {
            "transfer_lcb_floor": transfer_floor,
            "condition_ceiling": condition_ceiling,
            "leakage_ceiling": leakage_ceiling,
            "decisive_cases": decisive,
            "exact_raw_evidence_cases": len(rederived),
            "bootstrap_indices_and_draws_regenerated": True,
        }
    )


def _g4_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    threshold = _number(
        contract["synthetic_thresholds"]["raw_response_max_normalized_residual"],
        "G4 threshold",
    )
    decisive: dict[str, float] = {}
    for case in commission["cases"]:
        gate = _gate(case, "G4")
        _compare_rederived_tree(
            context,
            gate,
            rederived[case["case"]]["gates"]["G4"],
            f"{case['case']}.G4 exact raw-evidence rederivation",
        )
        diagnostics = _mapping(gate["diagnostics"], f"{case['case']}.G4.diagnostics")
        context.equal(diagnostics["fit_level_indices"], list(range(0, 33, 2)), f"{case['case']}.G4 fit indices")
        context.equal(
            diagnostics["held_out_level_indices"],
            list(range(1, 33, 2)),
            f"{case['case']}.G4 held-out indices",
        )
        low = _integer(diagnostics["low_rail_hits"], f"{case['case']}.G4 low rails")
        high = _integer(diagnostics["high_rail_hits"], f"{case['case']}.G4 high rails")
        slope = _number(diagnostics["slope"], f"{case['case']}.G4 slope")
        _number(diagnostics["intercept"], f"{case['case']}.G4 intercept")
        residual = _optional_number(
            diagnostics["held_out_max_normalized_residual"],
            f"{case['case']}.G4 residual",
        )
        context.close(diagnostics["threshold"], threshold, f"{case['case']}.G4 threshold")
        reasons: list[str] = []
        if low or high:
            reasons.append("RAW_CLIPPING_DETECTED")
        if slope <= 0.0 or residual is None:
            reasons.append("RAW_POSITIVE_AFFINE_FIT_NOT_ESTABLISHED")
        elif residual > threshold:
            reasons.append("RAW_NONLINEARITY_DETECTED")
        context.equal(_reason_codes(gate, f"{case['case']}.G4"), reasons, f"{case['case']}.G4 reasons")
        context.equal(
            gate["status"],
            "PASS" if not reasons else "UNMEASURED",
            f"{case['case']}.G4 status",
        )
        if case["case"] in ("baseline", "g4_gamma_response"):
            decisive[case["case"]] = residual
    context.evidence.update(
        {
            "held_out_residual_threshold": threshold,
            "rail_hits_required": 0,
            "decisive_residuals": decisive,
            "exact_raw_evidence_cases": len(rederived),
        }
    )


def _g5_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    cell_dimensions: Mapping[str, int],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    thresholds = contract["synthetic_thresholds"]
    magnitude_limit = _number(thresholds["split_magnitude_disagreement_max"], "G5 magnitude")
    phase_limit = _number(thresholds["split_phase_disagreement_rad_max"], "G5 phase")
    common_limit = _number(thresholds["common_mode_fraction_max"], "G5 common")
    decisive: dict[str, Any] = {}
    for case in commission["cases"]:
        gate = _gate(case, "G5")
        _compare_rederived_tree(
            context,
            gate,
            rederived[case["case"]]["gates"]["G5"],
            f"{case['case']}.G5 exact raw-evidence rederivation",
        )
        diagnostics = _mapping(gate["diagnostics"], f"{case['case']}.G5.diagnostics")
        cells = _mapping(diagnostics["cells"], f"{case['case']}.G5.cells")
        context.equal(set(cells), set(cell_dimensions), f"{case['case']}.G5 cells")
        reasons: list[str] = []
        lineage_disjoint = _boolean(
            diagnostics["lineage_disjoint"],
            f"{case['case']}.G5.lineage_disjoint",
        )
        if not lineage_disjoint:
            reasons.append("LINEAGE_NOT_DISJOINT")
        maxima = {split: {"magnitude": 0.0, "phase": 0.0, "common": 0.0} for split in SPLITS}
        for cell_id in cell_dimensions:
            cell = _mapping(cells[cell_id], f"{case['case']}.G5.{cell_id}")
            context.equal(set(cell), set(SPLITS), f"{case['case']}.G5.{cell_id} splits")
            for split in SPLITS:
                metrics = _mapping(cell[split], f"{case['case']}.G5.{cell_id}.{split}")
                first = _number(metrics["first_rms"], f"{case['case']}.G5 first RMS")
                second = _number(metrics["second_rms"], f"{case['case']}.G5 second RMS")
                magnitude = _optional_number(
                    metrics["relative_magnitude_disagreement"],
                    f"{case['case']}.G5 magnitude",
                )
                phase = _optional_number(
                    metrics["phase_disagreement_rad"],
                    f"{case['case']}.G5 phase",
                )
                signal = _number(
                    metrics["repeatable_signal_minimum_eigenvalue"],
                    f"{case['case']}.G5 signal",
                )
                controls = _mapping(
                    metrics["control_repeatable_covariance"],
                    f"{case['case']}.G5 controls",
                )
                context.equal(set(controls), set(CONTROLS), f"{case['case']}.G5 controls")
                control_values = [
                    _number(controls[name], f"{case['case']}.G5 control {name}")
                    for name in CONTROLS
                ]
                common = _optional_number(
                    metrics["common_mode_fraction"],
                    f"{case['case']}.G5 common fraction",
                )
                denominator = 0.5 * (first + second)
                if denominator > 0.0:
                    context.close(
                        magnitude,
                        abs(first - second) / denominator,
                        f"{case['case']}.G5.{cell_id}.{split} magnitude formula",
                    )
                else:
                    context.equal(magnitude, None, f"{case['case']}.G5 magnitude null")
                if signal > 0.0:
                    context.close(
                        common,
                        max(control_values) / signal,
                        f"{case['case']}.G5.{cell_id}.{split} common formula",
                    )
                else:
                    context.equal(common, None, f"{case['case']}.G5 common null")
                if magnitude is None or phase is None or common is None:
                    reasons.append("REFERENCE_HALF_AGREEMENT_UNIDENTIFIED")
                    continue
                if magnitude > magnitude_limit:
                    reasons.append("REFERENCE_HALF_MAGNITUDE_DISAGREEMENT")
                if phase > phase_limit:
                    reasons.append("REFERENCE_HALF_PHASE_DISAGREEMENT")
                if common > common_limit:
                    reasons.append("LAGGED_COMMON_MODE_EXCESS")
                maxima[split]["magnitude"] = max(maxima[split]["magnitude"], magnitude)
                maxima[split]["phase"] = max(maxima[split]["phase"], phase)
                maxima[split]["common"] = max(maxima[split]["common"], common)
        reasons = list(dict.fromkeys(reasons))
        context.equal(_reason_codes(gate, f"{case['case']}.G5"), reasons, f"{case['case']}.G5 reasons")
        context.equal(
            gate["status"],
            "PASS" if not reasons else "UNMEASURED",
            f"{case['case']}.G5 status",
        )
        recorded_thresholds = _mapping(diagnostics["thresholds"], "G5 thresholds")
        context.close(recorded_thresholds["magnitude_relative_max"], magnitude_limit, "G5 magnitude threshold")
        context.close(recorded_thresholds["phase_rad_max"], phase_limit, "G5 phase threshold")
        context.close(recorded_thresholds["common_mode_fraction_max"], common_limit, "G5 common threshold")
        if case["case"] in ("baseline", "g5_lagged_drift"):
            decisive[case["case"]] = maxima
    context.evidence.update(
        {
            "split_names": list(SPLITS),
            "common_mode_fraction_limit": common_limit,
            "decisive_cases": decisive,
            "exact_raw_evidence_cases": len(rederived),
        }
    )


def _g6_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    cell_dimensions: Mapping[str, int],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    thresholds = contract["synthetic_thresholds"]
    scale_limit = _number(thresholds["scale_disagreement_percent_max"], "G6 scale")
    rotation_limit = _number(thresholds["rotation_disagreement_deg_max"], "G6 rotation")
    residual_limit = _number(thresholds["nontranslation_rms_native_px_max"], "G6 residual")
    resampler_limit = _number(thresholds["resampler_relative_change_max"], "G6 resampler")
    decisive: dict[str, Any] = {}
    for case in commission["cases"]:
        gate = _gate(case, "G6")
        _compare_rederived_tree(
            context,
            gate,
            rederived[case["case"]]["gates"]["G6"],
            f"{case['case']}.G6 exact raw-evidence rederivation",
        )
        diagnostics = _mapping(gate["diagnostics"], f"{case['case']}.G6.diagnostics")
        scale = _number(diagnostics["max_scale_disagreement_percent"], f"{case['case']}.G6 scale")
        rotation = _number(diagnostics["max_rotation_disagreement_deg"], f"{case['case']}.G6 rotation")
        residual = _number(diagnostics["max_nontranslation_rms_native_px"], f"{case['case']}.G6 residual")
        sign_match = _boolean(
            diagnostics["planted_transform_sign_matches"],
            f"{case['case']}.G6 sign",
        )
        changes = _mapping(
            diagnostics["resampler_relative_change_by_cell"],
            f"{case['case']}.G6 resampler changes",
        )
        context.equal(set(changes), set(cell_dimensions), f"{case['case']}.G6 resampler cells")
        values = [
            _optional_number(changes[cell_id], f"{case['case']}.G6.{cell_id} resampler")
            for cell_id in cell_dimensions
        ]
        reasons: list[str] = []
        if scale > scale_limit:
            reasons.append("SCALE_GEOMETRY_DISAGREEMENT")
        if rotation > rotation_limit:
            reasons.append("ROTATION_GEOMETRY_DISAGREEMENT")
        if residual > residual_limit:
            reasons.append("NONTRANSLATION_RESIDUAL_EXCESS")
        if not sign_match:
            reasons.append("WRONG_SIGN_GEOMETRY")
        if any(value is None for value in values):
            reasons.append("RESAMPLER_SENSITIVITY_UNIDENTIFIED")
        elif any(value > resampler_limit for value in values if value is not None):
            reasons.append("RESAMPLER_SENSITIVITY_EXCESS")
        context.equal(_reason_codes(gate, f"{case['case']}.G6"), reasons, f"{case['case']}.G6 reasons")
        context.equal(
            gate["status"],
            "PASS" if not reasons else "UNMEASURED",
            f"{case['case']}.G6 status",
        )
        recorded = _mapping(diagnostics["thresholds"], "G6 thresholds")
        context.close(recorded["scale_disagreement_percent_max"], scale_limit, "G6 scale threshold")
        context.close(recorded["rotation_disagreement_deg_max"], rotation_limit, "G6 rotation threshold")
        context.close(recorded["nontranslation_rms_native_px_max"], residual_limit, "G6 residual threshold")
        context.close(recorded["resampler_relative_change_max"], resampler_limit, "G6 resampler threshold")
        if case["case"] in ("baseline", "g6_wrong_sign_rotation"):
            decisive[case["case"]] = {
                "max_scale_disagreement_percent": scale,
                "max_rotation_disagreement_deg": rotation,
                "max_nontranslation_rms_native_px": residual,
                "sign_match": sign_match,
                "max_resampler_relative_change": max(
                    value for value in values if value is not None
                ),
            }
    context.evidence.update(
        {
            "thresholds": {
                "scale_disagreement_percent_max": scale_limit,
                "rotation_disagreement_deg_max": rotation_limit,
                "nontranslation_rms_native_px_max": residual_limit,
                "resampler_relative_change_max": resampler_limit,
            },
            "decisive_cases": decisive,
            "exact_raw_evidence_cases": len(rederived),
        }
    )


def _g7_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    cell_dimensions: Mapping[str, int],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    thresholds = contract["synthetic_thresholds"]
    duplicate_limit = _number(thresholds["duplicate_site_correlation_max"], "G7 duplicate")
    power_floor = _number(thresholds["reference_power_lcb_min"], "G7 power")
    condition_ceiling = _number(thresholds["condition_number_max"], "G7 condition")
    decisive: dict[str, Any] = {}
    for case in commission["cases"]:
        gate = _gate(case, "G7")
        _compare_rederived_tree(
            context,
            gate,
            rederived[case["case"]]["gates"]["G7"],
            f"{case['case']}.G7 exact raw-evidence rederivation",
        )
        diagnostics = _mapping(gate["diagnostics"], f"{case['case']}.G7.diagnostics")
        duplicate = _optional_number(
            diagnostics["maximum_duplicate_site_correlation"],
            f"{case['case']}.G7 duplicate correlation",
        )
        context.close(
            diagnostics["duplicate_site_correlation_threshold"],
            duplicate_limit,
            f"{case['case']}.G7 duplicate threshold",
        )
        cells = _mapping(diagnostics["cells"], f"{case['case']}.G7.cells")
        context.equal(set(cells), set(cell_dimensions), f"{case['case']}.G7 cells")
        invalid = False
        points: list[float] = []
        records: list[tuple[str, Mapping[str, Any]]] = []
        g8_cells = _mapping(_gate(case, "G8")["diagnostics"]["cells"], f"{case['case']}.G8.cells")
        for cell_id, dimension in cell_dimensions.items():
            cell = _mapping(cells[cell_id], f"{case['case']}.G7.{cell_id}")
            signal = _eigen_summary(context, cell["signal"], dimension, f"{case['case']}.G7.{cell_id}.signal")
            charged = _eigen_summary(
                context,
                cell["charged_signal"],
                dimension,
                f"{case['case']}.G7.{cell_id}.charged",
            )
            common = _number(cell["common_mode_upper"], f"{case['case']}.G7.{cell_id}.common")
            for index in range(dimension):
                context.close(
                    charged[index],
                    signal[index] - common,
                    f"{case['case']}.G7.{cell_id}.charge[{index}]",
                )
            context.close(
                common,
                g8_cells[cell_id]["common_mode_upper_R"],
                f"{case['case']}.G7.{cell_id} common binding",
            )
            point = _number(cell["point_power"], f"{case['case']}.G7.{cell_id}.point")
            context.close(point, charged[0], f"{case['case']}.G7.{cell_id}.point power")
            condition = _optional_number(
                cell["condition_number"],
                f"{case['case']}.G7.{cell_id}.condition",
            )
            expected_condition = (
                None if charged[0] == 0.0 else charged[-1] / charged[0]
            )
            if expected_condition is None:
                context.equal(condition, None, f"{case['case']}.G7.{cell_id} condition")
            else:
                context.close(condition, expected_condition, f"{case['case']}.G7.{cell_id} condition")
            cell_invalid = (
                charged[0] <= 0.0
                or expected_condition is None
                or expected_condition > condition_ceiling
            )
            invalid |= cell_invalid
            points.append(point)
            records.append((cell_id, cell))
        reasons: list[str] = []
        if duplicate is None:
            reasons.append("DUPLICATE_SITE_CORRELATION_UNIDENTIFIED")
        elif duplicate >= duplicate_limit:
            reasons.append("DUPLICATE_SITE_CORRELATION_EXCESS")
        lcbs: list[float] = []
        if invalid:
            reasons.extend(
                [
                    "REFERENCE_POWER_NONPOSITIVE_OR_ILL_CONDITIONED",
                    "REFERENCE_POWER_FLOOR",
                ]
            )
        else:
            critical, errors = _max_t(
                context,
                diagnostics["max_t"],
                len(cell_dimensions),
                f"{case['case']}.G7.max_t",
            )
            for index, (cell_id, cell) in enumerate(records):
                lcb = _number(cell["lcb"], f"{case['case']}.G7.{cell_id}.lcb")
                context.close(
                    lcb,
                    points[index] - critical * errors[index],
                    f"{case['case']}.G7.{cell_id}.LCB relation",
                )
                lcbs.append(lcb)
            if any(value <= power_floor for value in lcbs):
                reasons.append("REFERENCE_POWER_FLOOR")
        context.equal(_reason_codes(gate, f"{case['case']}.G7"), reasons, f"{case['case']}.G7 reasons")
        context.equal(
            gate["status"],
            "PASS" if not reasons else "UNMEASURED",
            f"{case['case']}.G7 status",
        )
        if case["case"] in ("baseline", "g7_zero_power", "common_mode_false_improvement"):
            decisive[case["case"]] = {
                "maximum_duplicate_site_correlation": duplicate,
                "minimum_point_power": min(points),
                "minimum_lcb": min(lcbs) if lcbs else None,
            }
    context.evidence.update(
        {
            "duplicate_correlation_limit": duplicate_limit,
            "power_lcb_floor": power_floor,
            "condition_ceiling": condition_ceiling,
            "decisive_cases": decisive,
            "exact_raw_evidence_cases": len(rederived),
            "bootstrap_indices_and_draws_regenerated": True,
        }
    )


def _scalar_naive_metrics(cell: Mapping[str, Any], path: str) -> dict[str, float]:
    raw = _mapping(cell["raw"], f"{path}.raw")
    values: dict[str, list[float]] = {}
    for name in ("signal_R", "noise_R", "signal_S", "noise_S"):
        summary = _mapping(raw[name], f"{path}.raw.{name}")
        values[name] = [
            _number(value, f"{path}.raw.{name}.eigenvalues")
            for value in _list(summary["eigenvalues"], f"{path}.raw.{name}.eigenvalues")
        ]
    lengths = {len(value) for value in values.values()}
    if lengths != {len(values["signal_R"])} or not values["signal_R"]:
        raise VerificationError(f"{path} naive spectra have incompatible lengths")
    if any(value <= 0.0 for spectrum in values.values() for value in spectrum):
        raise VerificationError(f"{path} naive spectra are nonpositive")
    information_r = [
        0.5 * math.log2(1.0 + signal / noise)
        for signal, noise in zip(values["signal_R"], values["noise_R"])
    ]
    information_s = [
        0.5 * math.log2(1.0 + signal / noise)
        for signal, noise in zip(values["signal_S"], values["noise_S"])
    ]
    return {
        "reference_information": min(information_r),
        "information_ratio": min(
            reference / scored
            for reference, scored in zip(information_r, information_s)
        ),
        "transfer_ratio": math.sqrt(
            min(
                reference / scored
                for reference, scored in zip(
                    values["signal_R"], values["signal_S"]
                )
            )
        ),
    }


def _g8_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
    cell_dimensions: Mapping[str, int],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    thresholds = contract["synthetic_thresholds"]
    common_limit = _number(thresholds["common_mode_fraction_max"], "G8 common")
    condition_ceiling = _number(thresholds["condition_number_max"], "G8 condition")
    delta_information = _number(thresholds["delta_information"], "G8 delta information")
    delta_transfer = _number(thresholds["delta_transfer"], "G8 delta transfer")
    bootstrap = _mapping(contract["bootstrap"], "contract.bootstrap")
    decisive: dict[str, Any] = {}

    for case in commission["cases"]:
        case_name = case["case"]
        gate = _gate(case, "G8")
        _compare_rederived_tree(
            context,
            gate,
            rederived[case_name]["gates"]["G8"],
            f"{case_name}.G8 exact raw-evidence rederivation",
        )
        diagnostics = _mapping(gate["diagnostics"], f"{case_name}.G8.diagnostics")
        context.close(diagnostics["noise_difference_factor"], 0.5, f"{case_name}.G8 noise factor")
        context.equal(diagnostics["bootstrap_draws"], bootstrap["draws"], f"{case_name}.G8 draws")
        context.equal(diagnostics["bootstrap_seed"], bootstrap["dominance_seed"], f"{case_name}.G8 seed")
        context.equal(
            diagnostics["quantile_method"],
            bootstrap["quantile_method"],
            f"{case_name}.G8 quantile",
        )
        common_family = _mapping(
            diagnostics["common_mode_family"],
            f"{case_name}.G8.common_mode_family",
        )
        context.close(
            common_family["family_alpha"],
            bootstrap["common_mode_family_alpha"],
            f"{case_name}.G8 common family alpha",
        )
        context.equal(common_family["draws"], bootstrap["draws"], f"{case_name}.G8 common draws")
        point_estimates = _mapping(common_family["point_estimates"], f"{case_name}.G8 common points")
        upper_bounds = _mapping(common_family["upper_bounds"], f"{case_name}.G8 common upper")
        labels = [
            f"{cell_id}:{path_name}"
            for cell_id in cell_dimensions
            for path_name in ("R", "S")
        ]
        context.equal(set(point_estimates), set(labels), f"{case_name}.G8 common point labels")
        context.equal(set(upper_bounds), set(labels), f"{case_name}.G8 common upper labels")
        common_critical, common_errors = _max_t(
            context,
            common_family["max_t"],
            len(labels),
            f"{case_name}.G8 common max_t",
            1.0 - float(bootstrap["common_mode_family_alpha"]),
            "observed_minus_bootstrap",
            "observed_plus_critical_times_standard_error",
        )
        for index, label in enumerate(labels):
            context.close(
                upper_bounds[label],
                _number(point_estimates[label], f"{case_name}.{label} common point")
                + common_critical * common_errors[index],
                f"{case_name}.G8 {label} simultaneous upper relation",
            )

        cells = _mapping(diagnostics["cells"], f"{case_name}.G8.cells")
        context.equal(set(cells), set(cell_dimensions), f"{case_name}.G8 cells")
        observed: list[float] = []
        observed_labels: list[tuple[str, str]] = []
        common_excess = False
        point_invalid = False
        all_cell_data: dict[str, dict[str, Any]] = {}
        for cell_id, dimension in cell_dimensions.items():
            cell = _mapping(cells[cell_id], f"{case_name}.G8.{cell_id}")
            raw = _mapping(cell["raw"], f"{case_name}.G8.{cell_id}.raw")
            charged = _mapping(cell["charged"], f"{case_name}.G8.{cell_id}.charged")
            spectra: dict[str, list[float]] = {}
            charged_spectra: dict[str, list[float]] = {}
            for name in ("signal_R", "noise_R", "signal_S", "noise_S"):
                spectra[name] = _eigen_summary(
                    context,
                    raw[name],
                    dimension,
                    f"{case_name}.G8.{cell_id}.raw.{name}",
                )
                charged_spectra[name] = _eigen_summary(
                    context,
                    charged[name],
                    dimension,
                    f"{case_name}.G8.{cell_id}.charged.{name}",
                )
            common_r = _number(cell["common_mode_upper_R"], f"{case_name}.G8.{cell_id}.common R")
            common_s = _number(cell["common_mode_upper_S"], f"{case_name}.G8.{cell_id}.common S")
            context.close(common_r, upper_bounds[f"{cell_id}:R"], f"{case_name}.G8.{cell_id} common R binding")
            context.close(common_s, upper_bounds[f"{cell_id}:S"], f"{case_name}.G8.{cell_id} common S binding")
            charge_signs = {
                "signal_R": -common_r,
                "noise_R": common_r,
                "signal_S": common_s,
                "noise_S": -common_s,
            }
            for name, charge in charge_signs.items():
                for index in range(dimension):
                    context.close(
                        charged_spectra[name][index],
                        spectra[name][index] + charge,
                        f"{case_name}.G8.{cell_id}.{name} hostile charge[{index}]",
                    )
            fraction_r = _optional_number(
                cell["common_mode_fraction_R"],
                f"{case_name}.G8.{cell_id}.common fraction R",
            )
            fraction_s = _optional_number(
                cell["common_mode_fraction_S"],
                f"{case_name}.G8.{cell_id}.common fraction S",
            )
            expected_fraction_r = (
                None if spectra["signal_R"][0] <= 0.0 else common_r / spectra["signal_R"][0]
            )
            expected_fraction_s = (
                None if spectra["signal_S"][0] <= 0.0 else common_s / spectra["signal_S"][0]
            )
            if expected_fraction_r is None:
                context.equal(fraction_r, None, f"{case_name}.G8.{cell_id} fraction R")
            else:
                context.close(fraction_r, expected_fraction_r, f"{case_name}.G8.{cell_id} fraction R")
            if expected_fraction_s is None:
                context.equal(fraction_s, None, f"{case_name}.G8.{cell_id} fraction S")
            else:
                context.close(fraction_s, expected_fraction_s, f"{case_name}.G8.{cell_id} fraction S")
            if (
                fraction_r is None
                or fraction_s is None
                or fraction_r > common_limit
                or fraction_s > common_limit
            ):
                common_excess = True
            context.close(cell["delta_information"], delta_information, f"{case_name}.G8.{cell_id} delta I")
            context.close(cell["delta_transfer"], delta_transfer, f"{case_name}.G8.{cell_id} delta H")

            valid = True
            for spectrum in charged_spectra.values():
                valid &= (
                    spectrum[0] > 0.0
                    and spectrum[-1] / spectrum[0] <= condition_ceiling
                )
            point_invalid |= not valid
            if not valid:
                context.equal(cell.get("information_margin"), None, f"{case_name}.G8.{cell_id} invalid I margin")
                context.equal(cell.get("transfer_margin"), None, f"{case_name}.G8.{cell_id} invalid H margin")
                continue

            information_generalized = _number(
                cell["information_generalized_eigenvalue"],
                f"{case_name}.G8.{cell_id}.information generalized eigenvalue",
            )
            transfer_generalized = _number(
                cell["transfer_generalized_eigenvalue"],
                f"{case_name}.G8.{cell_id}.transfer generalized eigenvalue",
            )
            transfer_ratio = _number(
                cell["transfer_ratio"],
                f"{case_name}.G8.{cell_id}.transfer ratio",
            )
            information_margin = _number(
                cell["information_margin"],
                f"{case_name}.G8.{cell_id}.information margin",
            )
            transfer_margin = _number(
                cell["transfer_margin"],
                f"{case_name}.G8.{cell_id}.transfer margin",
            )
            context.close(
                information_margin,
                math.log(information_generalized) - math.log1p(delta_information),
                f"{case_name}.G8.{cell_id} information margin formula",
            )
            context.close(
                transfer_ratio,
                math.sqrt(transfer_generalized),
                f"{case_name}.G8.{cell_id} transfer ratio formula",
            )
            context.close(
                transfer_margin,
                0.5 * math.log(transfer_generalized) - math.log1p(delta_transfer),
                f"{case_name}.G8.{cell_id} transfer margin formula",
            )
            if dimension == 1:
                information_r = 0.5 * math.log2(
                    1.0 + charged_spectra["signal_R"][0] / charged_spectra["noise_R"][0]
                )
                information_s = 0.5 * math.log2(
                    1.0 + charged_spectra["signal_S"][0] / charged_spectra["noise_S"][0]
                )
                context.close(
                    information_generalized,
                    information_r / information_s,
                    f"{case_name}.G8.{cell_id} scalar information formula",
                )
                context.close(
                    transfer_generalized,
                    charged_spectra["signal_R"][0] / charged_spectra["signal_S"][0],
                    f"{case_name}.G8.{cell_id} scalar transfer formula",
                )
            else:
                context.equal(
                    cell.get("vector_rule"),
                    "SMALLEST_GENERALIZED_EIGENVALUE",
                    f"{case_name}.G8.{cell_id} vector rule",
                )
                r_info_low = 0.5 * math.log2(
                    1.0
                    + charged_spectra["signal_R"][0]
                    / charged_spectra["noise_R"][-1]
                )
                r_info_high = 0.5 * math.log2(
                    1.0
                    + charged_spectra["signal_R"][-1]
                    / charged_spectra["noise_R"][0]
                )
                s_info_low = 0.5 * math.log2(
                    1.0
                    + charged_spectra["signal_S"][0]
                    / charged_spectra["noise_S"][-1]
                )
                s_info_high = 0.5 * math.log2(
                    1.0
                    + charged_spectra["signal_S"][-1]
                    / charged_spectra["noise_S"][0]
                )
                context.expect(
                    r_info_low / s_info_high - ABS_TOL
                    <= information_generalized
                    <= r_info_high / s_info_low + ABS_TOL,
                    f"{case_name}.G8.{cell_id} vector information violates spectral bounds",
                )
                context.expect(
                    charged_spectra["signal_R"][0]
                    / charged_spectra["signal_S"][-1]
                    - ABS_TOL
                    <= transfer_generalized
                    <= charged_spectra["signal_R"][-1]
                    / charged_spectra["signal_S"][0]
                    + ABS_TOL,
                    f"{case_name}.G8.{cell_id} vector transfer violates spectral bounds",
                )
            observed.extend((information_margin, transfer_margin))
            observed_labels.extend(((cell_id, "information"), (cell_id, "transfer")))
            all_cell_data[cell_id] = {
                "information_margin": information_margin,
                "transfer_margin": transfer_margin,
                "information_generalized_eigenvalue": information_generalized,
                "transfer_ratio": transfer_ratio,
                "fraction_R": fraction_r,
                "fraction_S": fraction_s,
                "charged_signal_R": charged_spectra["signal_R"],
                "charged_signal_S": charged_spectra["signal_S"],
            }

        reasons = _reason_codes(gate, f"{case_name}.G8")
        core_reasons: list[str] = []
        if _gate(case, "G7")["status"] != "PASS":
            core_reasons.append("SUPPORT_FLOOR_NOT_ESTABLISHED")
        if point_invalid:
            core_reasons.append("NONPOSITIVE_HOSTILE_CHARGE")
        if common_excess:
            core_reasons.append("COMMON_MODE_FRACTION_EXCESS")
        for reason in core_reasons:
            context.expect(reason in reasons, f"{case_name}.G8 missing {reason}")

        if core_reasons:
            context.equal(
                diagnostics.get("dominance_max_t"),
                None,
                f"{case_name}.G8 preconditioned dominance max_t",
            )
            context.equal(gate["status"], "UNMEASURED", f"{case_name}.G8 precondition status")
        else:
            context.close(
                diagnostics["dominance_family_alpha"],
                bootstrap["dominance_family_alpha"],
                f"{case_name}.G8 dominance alpha",
            )
            critical, errors = _max_t(
                context,
                diagnostics["dominance_max_t"],
                len(observed),
                f"{case_name}.G8 dominance max_t",
            )
            lcbs: dict[str, dict[str, float]] = {}
            for index, (cell_id, kind) in enumerate(observed_labels):
                lcb = _number(
                    cells[cell_id][f"{kind}_margin_lcb"],
                    f"{case_name}.G8.{cell_id}.{kind} LCB",
                )
                context.close(
                    lcb,
                    observed[index] - critical * errors[index],
                    f"{case_name}.G8.{cell_id}.{kind} simultaneous LCB",
                )
                lcbs.setdefault(cell_id, {})[kind] = lcb
            expected_reasons: list[str] = []
            if any(values["information"] <= 0.0 for values in lcbs.values()):
                expected_reasons.append("INFORMATION_NOT_DOMINANT")
            if any(values["transfer"] <= 0.0 for values in lcbs.values()):
                expected_reasons.append("TRANSFER_NOT_DOMINANT")
            context.equal(reasons, expected_reasons, f"{case_name}.G8 LCB reasons")
            context.equal(
                gate["status"],
                "PASS" if not expected_reasons else "UNMEASURED",
                f"{case_name}.G8 LCB status",
            )
            if case_name in ("baseline", "g8_inferior_direction", "planted_improvement"):
                decisive[case_name] = {
                    "minimum_information_margin_lcb": min(
                        values["information"] for values in lcbs.values()
                    ),
                    "minimum_transfer_margin_lcb": min(
                        values["transfer"] for values in lcbs.values()
                    ),
                    "vector": all_cell_data["green-f025-o675"],
                    "vector_lcbs": lcbs["green-f025-o675"],
                }
        if case_name == "common_mode_false_improvement":
            decisive[case_name] = {
                "maximum_common_mode_fraction": max(
                    max(
                        value["fraction_R"] if value["fraction_R"] is not None else math.inf,
                        value["fraction_S"] if value["fraction_S"] is not None else math.inf,
                    )
                    for value in all_cell_data.values()
                ),
                "violating_cells": sum(
                    value["fraction_R"] is None
                    or value["fraction_S"] is None
                    or value["fraction_R"] > common_limit
                    or value["fraction_S"] > common_limit
                    for value in all_cell_data.values()
                ),
            }
        if core_reasons:
            context.expect(
                "common_mode_fraction_threshold" not in diagnostics,
                f"{case_name}.G8 unexpectedly retained a post-decision threshold",
            )
        else:
            context.close(
                diagnostics["common_mode_fraction_threshold"],
                common_limit,
                f"{case_name}.G8 common threshold",
            )
    vector_cell_id = next(
        cell_id
        for cell_id, dimension in cell_dimensions.items()
        if dimension > 1
    )
    vector_audits: dict[str, Any] = {}
    for case_name, result in rederived.items():
        audit = result["audits"]["G8"]["vector_cells"][vector_cell_id]
        vector_audits[case_name] = audit
        context.equal(
            audit["bootstrap_draw_count"],
            bootstrap["draws"],
            f"{case_name}.G8 vector bootstrap eigensystem draws",
        )
        if audit["point_positive_definite"] and audit[
            "all_bootstrap_draws_positive_definite"
        ]:
            for family in (
                "information_generalized_eigensystem",
                "transfer_generalized_eigensystem",
            ):
                eigensystem = audit[family]
                context.expect(
                    eigensystem["maximum_relative_residual"] <= 1.0e-10,
                    f"{case_name}.G8 {family} residual is not tight",
                )
                context.expect(
                    eigensystem[
                        "maximum_metric_orthonormality_error"
                    ]
                    <= 1.0e-10,
                    f"{case_name}.G8 {family} eigenspace is not normalized",
                )
                context.equal(
                    eigensystem["draw_count"],
                    bootstrap["draws"],
                    f"{case_name}.G8 {family} draw count",
                )
            stored_vector = rederived[case_name]["gates"]["G8"][
                "diagnostics"
            ]["cells"][vector_cell_id]
            context.close(
                audit["information_generalized_eigensystem"][
                    "point_eigenvalues"
                ][0],
                stored_vector["information_generalized_eigenvalue"],
                f"{case_name}.G8 vector exact information eigenvalue",
            )
            context.close(
                audit["transfer_generalized_eigensystem"][
                    "point_eigenvalues"
                ][0],
                stored_vector["transfer_generalized_eigenvalue"],
                f"{case_name}.G8 vector exact transfer eigenvalue",
            )
    context.evidence.update(
        {
            "noise_difference_factor": 0.5,
            "common_mode_fraction_limit": common_limit,
            "delta_information": delta_information,
            "delta_transfer": delta_transfer,
            "decisive_cases": decisive,
            "vector_exact_recomputation": (
                "HERMITIAN_MATRICES_GENERALIZED_EIGENVALUES_AND_EIGENSPACES"
            ),
            "vector_cell_id": vector_cell_id,
            "vector_audits": vector_audits,
            "all_cells_exactly_recomputed_per_case": len(cell_dimensions),
            "exact_raw_evidence_cases": len(rederived),
            "common_mode_and_dominance_bootstraps_regenerated": True,
        }
    )


def _baseline_control_check(
    context: CheckContext,
    commission: Mapping[str, Any],
) -> None:
    baseline = _case_map(commission)["baseline"]
    statuses = {gate["id"]: gate["status"] for gate in baseline["gates"]}
    context.equal(statuses, {f"G{index}": "PASS" for index in range(1, 9)}, "baseline gates")
    context.equal(baseline["counts"], {"PASS": 8, "UNMEASURED": 0, "total": 8}, "baseline counts")
    context.equal(baseline["all_gates_pass"], True, "baseline all_gates_pass")
    context.equal(baseline["expectation_met"], True, "baseline expectation")
    context.equal(baseline["outcome"], "GREEN", "baseline outcome")
    context.evidence["gate_partition"] = "8/8 PASS"


def _planted_improvement_check(
    context: CheckContext,
    commission: Mapping[str, Any],
    cell_ids: Sequence[str],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    cases = _case_map(commission)
    weak = _mapping(
        rederived["g8_inferior_direction"]["gates"]["G8"][
            "diagnostics"
        ]["cells"],
        "raw-evidence weak cells",
    )
    improved_case = cases["planted_improvement"]
    improved_gate = _gate(improved_case, "G8")
    improved = _mapping(
        rederived["planted_improvement"]["gates"]["G8"][
            "diagnostics"
        ]["cells"],
        "raw-evidence improved cells",
    )
    context.equal(set(weak), set(cell_ids), "weak G8 cells")
    context.equal(set(improved), set(cell_ids), "improved G8 cells")
    point_increases = 0
    lcb_increases = 0
    for cell_id in cell_ids:
        for kind in ("information", "transfer"):
            before = _number(weak[cell_id][f"{kind}_margin"], f"weak {cell_id} {kind}")
            after = _number(improved[cell_id][f"{kind}_margin"], f"improved {cell_id} {kind}")
            context.expect(after > before, f"{cell_id} {kind} point margin did not increase")
            point_increases += after > before
            before_lcb = _number(weak[cell_id][f"{kind}_margin_lcb"], f"weak {cell_id} {kind} LCB")
            after_lcb = _number(improved[cell_id][f"{kind}_margin_lcb"], f"improved {cell_id} {kind} LCB")
            context.expect(after_lcb > before_lcb, f"{cell_id} {kind} LCB did not increase")
            lcb_increases += after_lcb > before_lcb
    context.equal(improved_gate["status"], "PASS", "planted improvement G8")
    context.equal(improved_case["all_gates_pass"], True, "planted improvement all gates")
    comparison = _mapping(commission["comparisons"]["planted_improvement"], "planted comparison")
    context.equal(comparison, improved_case["comparison"], "planted comparison copies")
    context.equal(comparison["control_case"], "g8_inferior_direction", "planted control case")
    context.equal(
        comparison["every_information_and_transfer_margin_increased"],
        True,
        "recorded point-margin comparison",
    )
    context.equal(comparison["g8_pass"], True, "recorded planted G8 pass")
    context.equal(comparison["all_gates_pass"], True, "recorded planted all-gate pass")
    context.equal(comparison["passed"], True, "recorded planted comparison")
    for cell_id in cell_ids:
        record = _mapping(comparison["cells"][cell_id], f"planted comparison {cell_id}")
        context.close(
            record["information_margin_before"],
            weak[cell_id]["information_margin"],
            f"{cell_id} recorded information before",
        )
        context.close(
            record["information_margin_after"],
            improved[cell_id]["information_margin"],
            f"{cell_id} recorded information after",
        )
        context.close(
            record["transfer_margin_before"],
            weak[cell_id]["transfer_margin"],
            f"{cell_id} recorded transfer before",
        )
        context.close(
            record["transfer_margin_after"],
            improved[cell_id]["transfer_margin"],
            f"{cell_id} recorded transfer after",
        )
        context.equal(record["information_margin_increased"], True, f"{cell_id} recorded information increase")
        context.equal(record["transfer_margin_increased"], True, f"{cell_id} recorded transfer increase")
    context.evidence.update(
        {
            "point_margin_increases": point_increases,
            "simultaneous_lcb_increases": lcb_increases,
            "required_each": 2 * len(cell_ids),
            "gate_partition": "8/8 PASS",
            "comparison_source": "EXACT_EMBEDDED_RAW_EVIDENCE",
        }
    )


def _common_mode_control_check(
    context: CheckContext,
    commission: Mapping[str, Any],
    cell_ids: Sequence[str],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    cases = _case_map(commission)
    baseline_cells = _mapping(
        rederived["baseline"]["gates"]["G8"]["diagnostics"]["cells"],
        "raw-evidence baseline G8 cells",
    )
    common_case = cases["common_mode_false_improvement"]
    common_gate = _gate(common_case, "G8")
    common_cells = _mapping(
        rederived["common_mode_false_improvement"]["gates"]["G8"][
            "diagnostics"
        ]["cells"],
        "raw-evidence common G8 cells",
    )
    increases = 0
    minimum_increases = {
        "reference_information": math.inf,
        "information_ratio": math.inf,
        "transfer_ratio": math.inf,
    }
    for cell_id in cell_ids:
        before = _scalar_naive_metrics(baseline_cells[cell_id], f"baseline.{cell_id}")
        after = _scalar_naive_metrics(common_cells[cell_id], f"common.{cell_id}")
        for name in minimum_increases:
            difference = after[name] - before[name]
            minimum_increases[name] = min(minimum_increases[name], difference)
        increased = (
            after["reference_information"] > before["reference_information"]
            and after["information_ratio"] > before["information_ratio"]
            and after["transfer_ratio"] > before["transfer_ratio"]
        )
        context.expect(increased, f"{cell_id} naive common-mode readings did not all rise")
        increases += increased
    reasons = _reason_codes(common_gate, "common_mode_false_improvement.G8")
    context.equal(common_gate["status"], "UNMEASURED", "common-mode G8 status")
    context.expect("COMMON_MODE_FRACTION_EXCESS" in reasons, "common-mode G8 reason missing")
    comparison = _mapping(commission["comparisons"]["common_mode_false_improvement"], "common comparison")
    context.equal(comparison, common_case["comparison"], "common comparison copies")
    context.equal(
        comparison["every_naive_uncharged_information_and_transfer_metric_increased"],
        True,
        "recorded naive comparison",
    )
    context.equal(comparison["g8_status"], "UNMEASURED", "recorded common G8 status")
    context.equal(comparison["required_reason"], "COMMON_MODE_FRACTION_EXCESS", "recorded common reason")
    context.equal(comparison["required_reason_present"], True, "recorded common reason presence")
    context.equal(comparison["passed"], True, "recorded common comparison")
    for cell_id in cell_ids:
        record = _mapping(comparison["cells"][cell_id], f"common comparison {cell_id}")
        before = _scalar_naive_metrics(baseline_cells[cell_id], f"baseline.{cell_id}")
        after = _scalar_naive_metrics(common_cells[cell_id], f"common.{cell_id}")
        for name, value in before.items():
            context.close(record["baseline"][name], value, f"{cell_id} recorded baseline {name}")
        for name, value in after.items():
            context.close(record["common_mode"][name], value, f"{cell_id} recorded common {name}")
        context.equal(record["reference_information_increased"], True, f"{cell_id} recorded information increase")
        context.equal(record["transfer_increased"], True, f"{cell_id} recorded transfer increase")
    context.evidence.update(
        {
            "cells_with_all_naive_readings_increased": increases,
            "required_cells": len(cell_ids),
            "minimum_naive_increases": minimum_increases,
            "g8_status": common_gate["status"],
            "required_reason": "COMMON_MODE_FRACTION_EXCESS",
            "comparison_source": "RECONSTRUCTED_RAW_HERMITIAN_MATRICES",
        }
    )


def _weak_vector_control_check(
    context: CheckContext,
    commission: Mapping[str, Any],
    rederived: Mapping[str, Mapping[str, Any]],
) -> None:
    case = _case_map(commission)["g8_inferior_direction"]
    for gate_id in (f"G{index}" for index in range(1, 8)):
        context.equal(_gate(case, gate_id)["status"], "PASS", f"weak vector {gate_id}")
    gate = _gate(case, "G8")
    context.equal(gate["status"], "UNMEASURED", "weak vector G8")
    context.expect(
        "TRANSFER_NOT_DOMINANT" in _reason_codes(gate, "weak vector G8"),
        "weak vector transfer reason missing",
    )
    vector = _mapping(
        gate["diagnostics"]["cells"]["green-f025-o675"],
        "weak vector diagnostics",
    )
    context.equal(vector["vector_rule"], "SMALLEST_GENERALIZED_EIGENVALUE", "weak vector rule")
    vector_audit = rederived["g8_inferior_direction"]["audits"]["G8"][
        "vector_cells"
    ]["green-f025-o675"]
    favorable_mean_ratio = _number(
        vector_audit["favorable_average_transfer_ratio"],
        "weak vector matrix-derived favorable average",
    )
    required_ratio = 1.0 + _number(vector["delta_transfer"], "weak vector delta")
    transfer_ratio = math.sqrt(
        _number(
            vector_audit["transfer_generalized_eigensystem"][
                "point_eigenvalues"
            ][0],
            "weak vector exact matrix generalized eigenvalue",
        )
    )
    transfer_lcb = _number(vector["transfer_margin_lcb"], "weak vector transfer LCB")
    context.close(
        transfer_ratio,
        vector["transfer_ratio"],
        "weak vector matrix-derived transfer ratio",
    )
    context.expect(favorable_mean_ratio > required_ratio, "weak vector mean witness is not favorable")
    context.expect(transfer_ratio < required_ratio, "weakest vector direction is not inferior")
    context.expect(transfer_lcb <= 0.0, "weak vector simultaneous transfer LCB is not nonpositive")
    context.evidence.update(
        {
            "original_gate_partition": "G1-G7 PASS",
            "g8_status": "UNMEASURED",
            "favorable_mean_transfer_ratio": favorable_mean_ratio,
            "required_point_transfer_ratio": required_ratio,
            "smallest_direction_transfer_ratio": transfer_ratio,
            "smallest_direction_transfer_margin_lcb": transfer_lcb,
            "direction_source": (
                "RECONSTRUCTED_HERMITIAN_GENERALIZED_EIGENSPACE"
            ),
            "weakest_transfer_direction": (
                vector_audit["transfer_generalized_eigensystem"][
                    "weakest_point_direction"
                ]
            ),
        }
    )


def _top_level_checks_check(
    context: CheckContext,
    commission: Mapping[str, Any],
) -> None:
    checks = _mapping(commission["checks"], "commission.checks")
    expected_names = {
        "all_case_expectations",
        "complete_gate_partition",
        "duplicate_anchor_canary",
        "expected_green_cases",
        "gate_evaluations",
        "missing_anchor_canary",
        "production_digital_k_refusal",
        "scientific_cases",
        "source_unchanged",
        "targeted_red_cases",
        "zero_capture_reads",
        "zero_skipped",
    }
    context.equal(set(checks), expected_names, "commission check names")
    context.expect(
        all(_boolean(value, f"commission.checks.{name}") for name, value in checks.items()),
        "one or more commission summary checks are false",
    )
    cases = _list(commission["cases"], "commission.cases")
    context.expect(
        all(case["expectation_met"] is True for case in cases),
        "not every case expectation is met",
    )
    context.evidence["producer_checks_cross_checked"] = len(checks)


def _production_digital_k_probe_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
) -> None:
    probes = _require_keys(
        commission["policy_probes"],
        ("production_missing_manifest_digital_k",),
        "commission.policy_probes",
    )
    probe = _require_keys(
        probes["production_missing_manifest_digital_k"],
        (
            "source_case",
            "evidence_origin",
            "calibration_manifest_present",
            "result_schema",
            "profile",
            "claim_scope",
            "counts",
            "all_gates_pass",
            "gates",
        ),
        "production_missing_manifest_digital_k",
    )
    context.equal(probe["source_case"], "baseline", "policy probe source case")
    context.equal(
        probe["evidence_origin"],
        "BASELINE_IN_MEMORY_AFTER_SINGLE_READ",
        "policy probe evidence origin",
    )
    context.equal(
        probe["calibration_manifest_present"],
        False,
        "policy probe manifest presence",
    )
    context.equal(
        probe["result_schema"],
        contract["schemas"]["result"],
        "policy probe result schema",
    )
    context.equal(probe["profile"], "production", "policy probe profile")
    context.equal(
        probe["claim_scope"],
        "DIGITAL_K",
        "policy probe claim scope",
    )
    context.equal(
        probe["counts"],
        {"PASS": 0, "UNMEASURED": 8, "total": 8},
        "policy probe gate counts",
    )
    context.equal(
        probe["all_gates_pass"],
        False,
        "policy probe all-gates outcome",
    )

    definitions = _list(
        contract["gate_definitions"],
        "contract.gate_definitions",
    )
    gates = _list(probe["gates"], "policy probe gates")
    context.equal(len(gates), 8, "policy probe gate count")
    context.equal(
        [(gate["id"], gate["name"]) for gate in gates],
        [
            (definition["id"], definition["name"])
            for definition in definitions
        ],
        "policy probe ordered gates",
    )
    manifest_reason = "PRODUCTION_CALIBRATION_MANIFEST_ABSENT"
    policy = _mapping(contract["digital_k_policy"], "digital_k_policy")
    policy_reason = _string(policy["reason"], "digital_k_policy.reason")
    observed_reasons: dict[str, list[str]] = {}
    for definition, raw_gate in zip(definitions, gates):
        gate_id = str(definition["id"])
        gate = _require_keys(
            raw_gate,
            (
                "id",
                "name",
                "status",
                "evaluated",
                "reason_codes",
                "claim_value",
                "diagnostics",
            ),
            f"policy probe {gate_id}",
        )
        expected_reasons = [
            manifest_reason,
            str(definition["production_missing_reason"]),
        ]
        if gate_id == "G8":
            expected_reasons.append(policy_reason)
        reasons = _reason_codes(gate, f"policy probe {gate_id}")
        observed_reasons[gate_id] = reasons
        context.equal(
            gate["status"],
            policy["status"],
            f"policy probe {gate_id} status",
        )
        context.equal(
            gate["evaluated"],
            True,
            f"policy probe {gate_id} evaluated",
        )
        context.equal(
            gate["claim_value"],
            None,
            f"policy probe {gate_id} claim value",
        )
        context.equal(
            reasons,
            expected_reasons,
            f"policy probe {gate_id} reasons",
        )
        diagnostics = _mapping(
            gate["diagnostics"],
            f"policy probe {gate_id} diagnostics",
        )
        expected_diagnostic_keys = {
            "profile",
            "synthetic_defaults_used",
        }
        if gate_id == "G8":
            expected_diagnostic_keys.add("digital_k_policy")
        _expect_keys(
            context,
            diagnostics,
            expected_diagnostic_keys,
            f"policy probe {gate_id} diagnostics",
        )
        context.equal(
            diagnostics["profile"],
            "production",
            f"policy probe {gate_id} diagnostic profile",
        )
        context.equal(
            diagnostics["synthetic_defaults_used"],
            False,
            f"policy probe {gate_id} synthetic defaults",
        )

    g8 = _mapping(gates[-1], "policy probe G8")
    digital_k_diagnostics = _require_keys(
        _mapping(g8["diagnostics"], "policy probe G8 diagnostics")[
            "digital_k_policy"
        ],
        (
            "status",
            "reason",
            "q_payload_present",
            "q_matrix_alone_sufficient",
            "production_manifest_failure_additional_reason",
        ),
        "policy probe G8 digital_k_policy",
    )
    context.equal(
        digital_k_diagnostics["status"],
        policy["status"],
        "policy probe policy status",
    )
    context.equal(
        digital_k_diagnostics["reason"],
        policy_reason,
        "policy probe frozen reason",
    )
    context.equal(
        digital_k_diagnostics["q_payload_present"],
        False,
        "policy probe q presence",
    )
    context.equal(
        digital_k_diagnostics["q_matrix_alone_sufficient"],
        False,
        "policy probe q sufficiency",
    )
    context.equal(
        digital_k_diagnostics[
            "production_manifest_failure_additional_reason"
        ],
        manifest_reason,
        "policy probe additional manifest reason",
    )
    context.equal(
        commission["checks"]["production_digital_k_refusal"],
        True,
        "producer production DIGITAL_K refusal check",
    )
    context.evidence.update(
        {
            "source_case": probe["source_case"],
            "evidence_origin": probe["evidence_origin"],
            "profile": probe["profile"],
            "claim_scope": probe["claim_scope"],
            "g8_status": g8["status"],
            "g8_reason_codes": observed_reasons["G8"],
            "g8_claim_value": g8["claim_value"],
            "all_gates_pass": probe["all_gates_pass"],
            "q_payload_present": False,
            "q_matrix_alone_sufficient": False,
        }
    )


def _digital_k_refusal_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    baseline_raw_evidence: Mapping[str, Any],
) -> None:
    policy = _mapping(contract["digital_k_policy"], "digital_k_policy")
    expected_reason = _string(
        policy["reason"], "digital_k_policy.reason"
    )
    variants: list[tuple[str, dict[str, Any]]] = []
    absent = copy.deepcopy(dict(baseline_raw_evidence))
    absent["claim_scope"] = "DIGITAL_K"
    absent.pop("q_baseline", None)
    variants.append(("absent_q", absent))
    for name, fill in (("identity_q", "identity"), ("all_zero_q", "zero")):
        evidence = copy.deepcopy(dict(baseline_raw_evidence))
        evidence["claim_scope"] = "DIGITAL_K"
        q_payload = {
            "cell_ids": [
                str(cell["id"]) for cell in contract["cells"]
            ],
            "q": {},
        }
        for cell in contract["cells"]:
            cell_id = str(cell["id"])
            dimension = int(cell["dimension"])
            matrix = (
                np.eye(dimension, dtype=np.complex128)
                if fill == "identity"
                else np.zeros(
                    (dimension, dimension), dtype=np.complex128
                )
            )
            q_payload["q"][cell_id] = _complex_matrix_json(matrix)
        evidence["q_baseline"] = {
            "schema": "m171-q-baseline-v1",
            "payload": q_payload,
            "payload_sha256": _canonical_sha256(q_payload),
        }
        variants.append((name, evidence))

    records: list[dict[str, Any]] = []
    for name, raw_evidence in variants:
        prepared = _prepare_evidence(raw_evidence, contract)
        rederived = _raw_rederive_case(prepared, contract)
        gate = rederived["gates"]["G8"]
        context.equal(gate["status"], "UNMEASURED", f"{name} G8 status")
        context.equal(
            gate["reason_codes"],
            [expected_reason],
            f"{name} frozen refusal reason",
        )
        context.equal(gate["claim_value"], None, f"{name} claim value")
        context.equal(
            rederived["all_gates_pass"],
            False,
            f"{name} all-gates outcome",
        )
        digital_k_diagnostics = _mapping(
            gate["diagnostics"]["digital_k_policy"],
            f"{name}.G8.digital_k_policy",
        )
        context.equal(
            digital_k_diagnostics["status"],
            policy["status"],
            f"{name} policy status",
        )
        context.equal(
            digital_k_diagnostics["reason"],
            expected_reason,
            f"{name} policy reason",
        )
        context.equal(
            digital_k_diagnostics["q_payload_present"],
            name != "absent_q",
            f"{name} q presence",
        )
        context.equal(
            digital_k_diagnostics["q_matrix_alone_sufficient"],
            False,
            f"{name} q sufficiency",
        )
        records.append(
            {
                "variant": name,
                "g8_status": gate["status"],
                "reason": expected_reason,
                "q_payload_present": name != "absent_q",
                "all_gates_pass": rederived["all_gates_pass"],
            }
        )
    context.evidence.update(
        {
            "policy_status": policy["status"],
            "frozen_reason": expected_reason,
            "q_matrix_alone_sufficient": False,
            "variants": records,
        }
    )


def _no_capture_access_check(
    context: CheckContext,
    contract: Mapping[str, Any],
    commission: Mapping[str, Any],
) -> None:
    cases = _list(commission["cases"], "commission.cases")
    recorded = [_integer(case["capture_reads"], f"{case['case']}.capture_reads") for case in cases]
    context.expect(all(value == 0 for value in recorded), "a case reports capture reads")
    context.equal(sum(recorded), 0, "summed capture reads")
    context.equal(commission["partitions"]["capture_reads"], 0, "partition capture reads")
    context.equal(contract["campaign_counts"]["capture_reads"], 0, "contract capture reads")
    context.evidence.update(
        {
            "commission_reported_capture_reads": 0,
            "verifier_capture_reads": 0,
            "cases_checked": len(recorded),
        }
    )


def _provenance_check(
    context: CheckContext,
    repository: pathlib.Path,
    contract: Mapping[str, Any],
    contract_payload: bytes,
    preregistration_payload: bytes,
    gitattributes_payload: bytes,
) -> None:
    initial_resolved = (
        _git_output(
            repository,
            (
                "rev-parse",
                "--verify",
                f"{INITIAL_PREREGISTRATION_COMMIT}^{{commit}}",
            ),
            "initial preregistration commit",
        )
        .decode("ascii")
        .strip()
    )
    amendment_one_resolved = (
        _git_output(
            repository,
            (
                "rev-parse",
                "--verify",
                f"{AMENDMENT_ONE_COMMIT}^{{commit}}",
            ),
            "Amendment 1 commit",
        )
        .decode("ascii")
        .strip()
    )
    amendment_two_resolved = (
        _git_output(
            repository,
            (
                "rev-parse",
                "--verify",
                f"{AMENDMENT_TWO_COMMIT}^{{commit}}",
            ),
            "Amendment 2 commit",
        )
        .decode("ascii")
        .strip()
    )
    amendment_three_resolved = (
        _git_output(
            repository,
            (
                "rev-parse",
                "--verify",
                f"{AMENDMENT_THREE_COMMIT}^{{commit}}",
            ),
            "Amendment 3 commit",
        )
        .decode("ascii")
        .strip()
    )
    context.equal(
        initial_resolved,
        INITIAL_PREREGISTRATION_COMMIT_FULL,
        "initial preregistration commit",
    )
    context.equal(
        amendment_one_resolved,
        AMENDMENT_ONE_COMMIT_FULL,
        "Amendment 1 commit",
    )
    context.equal(
        amendment_two_resolved,
        AMENDMENT_TWO_COMMIT_FULL,
        "Amendment 2 commit",
    )
    context.equal(
        amendment_three_resolved,
        AMENDMENT_THREE_COMMIT_FULL,
        "Amendment 3 commit",
    )
    _git_output(
        repository,
        (
            "merge-base",
            "--is-ancestor",
            initial_resolved,
            amendment_one_resolved,
        ),
        "initial-to-Amendment-1 ancestry",
    )
    _git_output(
        repository,
        (
            "merge-base",
            "--is-ancestor",
            amendment_one_resolved,
            amendment_two_resolved,
        ),
        "Amendment-1-to-Amendment-2 ancestry",
    )
    _git_output(
        repository,
        (
            "merge-base",
            "--is-ancestor",
            amendment_two_resolved,
            amendment_three_resolved,
        ),
        "Amendment-2-to-Amendment-3 ancestry",
    )
    historical_contract = _git_output(
        repository,
        (
            "show",
            f"{amendment_three_resolved}:{EXPERIMENT_PREFIX}/contract.json",
        ),
        "Amendment 3 contract blob",
    )
    historical_preregistration = _git_output(
        repository,
        (
            "show",
            f"{amendment_three_resolved}:{EXPERIMENT_PREFIX}/PREREGISTRATION.md",
        ),
        "Amendment 3 preregistration blob",
    )
    historical_gitattributes = _git_output(
        repository,
        (
            "show",
            f"{amendment_three_resolved}:{EXPERIMENT_PREFIX}/.gitattributes",
        ),
        "Amendment 3 attributes blob",
    )
    initial_preregistration = _git_output(
        repository,
        (
            "show",
            f"{initial_resolved}:{EXPERIMENT_PREFIX}/PREREGISTRATION.md",
        ),
        "initial preregistration blob",
    )
    _lf_text(contract_payload, "contract")
    _lf_text(preregistration_payload, "preregistration")
    _lf_text(gitattributes_payload, ".gitattributes")
    context.expect(
        historical_contract == contract_payload,
        "contract worktree bytes differ from the frozen Amendment 3 blob",
    )
    context.expect(
        historical_preregistration == preregistration_payload,
        "preregistration worktree bytes differ from the frozen Amendment 3 blob",
    )
    context.expect(
        historical_gitattributes == gitattributes_payload,
        ".gitattributes worktree bytes differ from the frozen Amendment 3 blob",
    )
    context.equal(
        gitattributes_payload,
        b"* text eol=lf\n",
        "lane-local .gitattributes bytes",
    )
    context.equal(
        contract["amendment"]["amends_preregistration_commit"],
        initial_resolved,
        "contract Amendment 1 initial-commit binding",
    )
    context.expect(
        b"## 8. Amendment 1 - max-t direction and DIGITAL_K refusal"
        in preregistration_payload,
        "amended preregistration omits the frozen Amendment 1 section",
    )
    context.expect(
        b"## 9. Amendment 2 - checkout-stable seals"
        in preregistration_payload,
        "amended preregistration omits the frozen Amendment 2 section",
    )
    context.expect(
        b"## 10. Amendment 3 - common-mode upper tail and protected outputs"
        in preregistration_payload,
        "amended preregistration omits the frozen Amendment 3 section",
    )
    context.expect(
        b"The frozen `contract.json` SHA-256 is"
        in initial_preregistration,
        "initial preregistration blob omits its original contract binding",
    )
    integrity_amendment = _mapping(
        contract["integrity_amendment"],
        "contract.integrity_amendment",
    )
    context.equal(
        integrity_amendment["amendment"],
        2,
        "contract integrity amendment number",
    )
    context.equal(
        integrity_amendment["line_ending_policy"],
        LINE_ENDING_POLICY,
        "contract line-ending policy",
    )
    context.equal(
        integrity_amendment["gitattributes"],
        f"{EXPERIMENT_PREFIX}/.gitattributes",
        "contract .gitattributes path",
    )
    amendment = _mapping(contract["amendment"], "contract.amendment")
    context.equal(
        amendment["invalidated_commission_sha256"],
        "2B9A6A2DD1D1321C63F202FA8615BB466CD255D3BC52BAD2140ACBD71A24132E",
        "v1 invalidated commission SHA-256",
    )
    context.equal(
        amendment["invalidated_verification_sha256"],
        "7627BDC0D42E3DDD011DEE2EF06CDD6BDA72471630919F02ABE96F282D0F68FE",
        "v1 invalidated verification SHA-256",
    )
    context.equal(
        integrity_amendment["invalidated_commission_sha256"],
        "D1C862E12BCD967D9B3FB29BECA48CEB4939233B0758B84D725E4341AB1B78B1",
        "v2 invalidated commission SHA-256",
    )
    context.equal(
        integrity_amendment["invalidated_verification_sha256"],
        "2773F392B7C51A4930300DFE7777D8ABF328CF6AED583245FACFC2A5A0A81449",
        "v2 invalidated verification SHA-256",
    )
    statistical_amendment = _mapping(
        contract["statistical_amendment"],
        "contract.statistical_amendment",
    )
    context.equal(
        statistical_amendment["amendment"],
        3,
        "contract statistical amendment number",
    )
    context.equal(
        statistical_amendment["invalidated_commission_sha256"],
        "C79C7E79B872EF7E6DA03778B8E158A4FFE7F93EDAFA08D5306C00DD7DAF97DF",
        "v3 invalidated commission SHA-256",
    )
    context.equal(
        statistical_amendment["invalidated_verification_sha256"],
        "4F987DDFDEBC0FF3DBFFA90DBCAE4CDAFF83B95C757C62A326289DDF6C49EDA1",
        "v3 invalidated verification SHA-256",
    )
    context.equal(
        statistical_amendment["output_protection"],
        "All CLIs refuse outputs that resolve to frozen inputs or lane source files.",
        "contract Amendment 3 output protection",
    )
    context.evidence.update(
        {
            "initial_preregistration_commit": INITIAL_PREREGISTRATION_COMMIT,
            "initial_resolved_commit": initial_resolved,
            "amendment_one_commit": AMENDMENT_ONE_COMMIT,
            "amendment_one_resolved_commit": amendment_one_resolved,
            "amendment_two_commit": AMENDMENT_TWO_COMMIT,
            "amendment_two_resolved_commit": amendment_two_resolved,
            "amendment_three_commit": AMENDMENT_THREE_COMMIT,
            "amendment_three_resolved_commit": amendment_three_resolved,
            "preregistration_sha256": _sha256(preregistration_payload),
            "initial_preregistration_git_blob_sha256": _sha256(
                initial_preregistration
            ),
            "contract_git_blob_sha256": _sha256(historical_contract),
            "preregistration_git_blob_sha256": _sha256(
                historical_preregistration
            ),
            "gitattributes_git_blob_sha256": _sha256(
                historical_gitattributes
            ),
            "line_ending_policy": LINE_ENDING_POLICY,
            "checkout_representation": "EXACT_LF_WORKTREE_EQUALS_FROZEN_GIT_BLOB",
            "contract_content_matches_commit": (
                historical_contract == contract_payload
            ),
            "preregistration_content_matches_commit": (
                historical_preregistration == preregistration_payload
            ),
            "gitattributes_content_matches_commit": (
                historical_gitattributes == gitattributes_payload
            ),
        }
    )


def _write_json(path: pathlib.Path, value: Mapping[str, Any]) -> None:
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise HarnessError(f"verification result is not finite JSON: {exc}") from exc
    payload = (rendered + "\n").encode("utf-8")
    try:
        with path.open("wb") as stream:
            stream.write(payload)
    except OSError as exc:
        raise HarnessError(f"cannot write verification output: {exc}") from exc


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--commission", required=True)
    parser.add_argument("--expected-commission-sha256", required=True)
    parser.add_argument("--output", required=True)
    return parser


def verify(
    *,
    contract_path: pathlib.Path,
    commission_path: pathlib.Path,
    expected_commission_sha256: str,
    output_path: pathlib.Path,
) -> dict[str, Any]:
    contract, contract_payload, contract_sha256 = _read_sealed_json_once(
        contract_path,
        FROZEN_CONTRACT_SHA256,
        "contract",
    )
    commission, commission_payload, commission_sha256 = _read_sealed_json_once(
        commission_path,
        expected_commission_sha256,
        "commission",
    )
    base = contract_path.parent
    admission_path = _reject_d_drive(
        base / "admission.py",
        "admission source",
    )
    commission_source_path = _reject_d_drive(
        base / "commission.py",
        "commission source",
    )
    synthetic_path = _reject_d_drive(base / "synthetic.py", "synthetic source")
    preregistration_path = _reject_d_drive(
        base / "PREREGISTRATION.md",
        "preregistration",
    )
    gitattributes_path = _reject_d_drive(
        base / ".gitattributes",
        "lane-local attributes",
    )
    test_source_path = _reject_d_drive(
        base / "test_admission.py",
        "test source",
    )
    verifier_source_path = _reject_d_drive(
        base / "verify.py",
        "verifier source",
    )
    repository = _reject_d_drive(base.parent.parent, "Strehl repository")
    admission_payload = _read_bytes_once(
        admission_path,
        "admission source",
    )
    commission_source_payload = _read_bytes_once(
        commission_source_path,
        "commission source",
    )
    synthetic_payload = _read_bytes_once(synthetic_path, "synthetic source")
    preregistration_payload = _read_bytes_once(
        preregistration_path,
        "preregistration",
    )
    gitattributes_payload = _read_bytes_once(
        gitattributes_path,
        "lane-local attributes",
    )
    test_source_payload = _read_bytes_once(
        test_source_path,
        "test source",
    )
    verifier_source_payload = _read_bytes_once(
        verifier_source_path,
        "verifier source",
    )
    try:
        preregistration_text = preregistration_payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HarnessError(f"preregistration is not UTF-8: {exc}") from exc
    rederived, embedded_metadata, raw_evidence_by_case = (
        _rederive_campaign(contract, commission)
    )

    cells = _list(contract["cells"], "contract.cells")
    cell_dimensions = {
        _string(cell["id"], "contract cell id"): int(
            _number(cell["dimension"], "contract cell dimension")
        )
        for cell in cells
    }
    cell_ids = list(cell_dimensions)
    checks = CheckRegistry()
    checks.run(
        "seal.contract",
        "The exact contract bytes match the frozen SHA-256.",
        lambda context: context.evidence.update({"sha256": contract_sha256}),
    )
    checks.run(
        "seal.commission",
        "The exact commission bytes match the caller-supplied SHA-256.",
        lambda context: context.evidence.update({"sha256": commission_sha256}),
    )
    checks.run(
        "numeric.upper-tail-formula",
        "An asymmetric raw fixture independently proves the common-mode UCB root and addition.",
        _upper_tail_formula_check,
    )
    checks.run(
        "provenance.output-protections",
        "Filesystem-identical contract, artifact, frozen, and source outputs are refused before writing.",
        lambda context: _output_protection_check(
            context,
            contract_path,
            commission_path,
            output_path,
            {
                "synthetic": synthetic_payload,
                "commission": commission_source_payload,
                "verify": verifier_source_payload,
            },
        ),
    )
    attribute_context = checks.run(
        "provenance.line-ending-attributes",
        "Every M171 source, frozen input, and output artifact has text=set and eol=lf.",
        lambda context: _line_ending_attribute_check(context, repository),
    )
    checkout_payloads = {
        f"{EXPERIMENT_PREFIX}/.gitattributes": gitattributes_payload,
        f"{EXPERIMENT_PREFIX}/PREREGISTRATION.md": (
            preregistration_payload
        ),
        f"{EXPERIMENT_PREFIX}/admission.py": admission_payload,
        f"{EXPERIMENT_PREFIX}/commission.py": commission_source_payload,
        f"{EXPERIMENT_PREFIX}/synthetic.py": synthetic_payload,
        f"{EXPERIMENT_PREFIX}/test_admission.py": test_source_payload,
        f"{EXPERIMENT_PREFIX}/verify.py": verifier_source_payload,
        f"{EXPERIMENT_PREFIX}/contract.json": contract_payload,
        f"{EXPERIMENT_PREFIX}/out/commission.json": commission_payload,
    }
    checkout_context = checks.run(
        "provenance.checkout-stable-LF",
        "Raw UTF-8 LF bytes equal Git-clean bytes and all active input seals bind those exact bytes.",
        lambda context: _checkout_representation_check(
            context,
            repository,
            checkout_payloads,
            {
                f"{EXPERIMENT_PREFIX}/admission.py": (
                    FROZEN_ADMISSION_SOURCE_SHA256
                ),
                f"{EXPERIMENT_PREFIX}/commission.py": (
                    FROZEN_COMMISSION_SOURCE_SHA256
                ),
                f"{EXPERIMENT_PREFIX}/synthetic.py": (
                    FROZEN_SYNTHETIC_SOURCE_SHA256
                ),
                f"{EXPERIMENT_PREFIX}/contract.json": (
                    FROZEN_CONTRACT_SHA256
                ),
                f"{EXPERIMENT_PREFIX}/out/commission.json": (
                    commission_sha256
                ),
            },
        ),
    )
    checks.run(
        "provenance.preregistration",
        "All three amendments resolve, and frozen v4 inputs exactly match commit 75259ef0.",
        lambda context: _provenance_check(
            context,
            repository,
            contract,
            contract_payload,
            preregistration_payload,
            gitattributes_payload,
        ),
    )
    checks.run(
        "contract.definition",
        "The frozen contract has the exact M171 scope, cells, gates, and campaign counts.",
        lambda context: _contract_definition_check(context, contract),
    )
    checks.run(
        "contract.authority-boundaries",
        "Noise conventions, production refusal, and DIGITAL_K boundaries remain explicit.",
        lambda context: _authority_boundary_check(
            context,
            contract,
            preregistration_text,
        ),
    )
    checks.run(
        "commission.structure",
        "The commission and every retained result have the exact expected schema.",
        lambda context: _commission_structure_check(context, contract, commission),
    )
    checks.run(
        "commission.status-semantics",
        "Every gate is evaluated PASS or UNMEASURED with fail-closed claim semantics.",
        lambda context: _status_semantics_check(context, contract, commission),
    )
    campaign_context = checks.run(
        "commission.partitions",
        "The independently counted 11-case, 88-gate partitions are complete.",
        lambda context: _campaign_partition_check(context, contract, commission),
    )
    checks.run(
        "commission.evidence-hash-bindings",
        "Every embedded exact evidence payload passes both seals and its raw gate partition rederives.",
        lambda context: _evidence_hash_check(
            context,
            commission,
            rederived,
            embedded_metadata,
        ),
    )
    checks.run(
        "commission.summary-booleans",
        "Producer summary booleans agree with independently reconstructed outcomes.",
        lambda context: _top_level_checks_check(context, commission),
    )
    digital_k_context = checks.run(
        "policy.DIGITAL_K-refusal",
        "Absent, valid identity, and all-zero q payloads all refuse DIGITAL_K for the frozen reason.",
        lambda context: _digital_k_refusal_check(
            context,
            contract,
            raw_evidence_by_case["baseline"],
        ),
    )
    production_digital_k_context = checks.run(
        "policy.production-missing-manifest-DIGITAL_K",
        "The commissioned production early-refusal probe preserves both manifest reasons and the frozen DIGITAL_K refusal.",
        lambda context: _production_digital_k_probe_check(
            context,
            contract,
            commission,
        ),
    )
    checks.run(
        "scope.zero-capture-reads",
        "The contract, every case, and the campaign partition report zero capture reads.",
        lambda context: _no_capture_access_check(context, contract, commission),
    )
    source_context = checks.run(
        "mutations.source-hashes",
        "Admission, commission, and synthetic sources are unchanged, and all eight mutations reproduce their sealed hashes.",
        lambda context: _source_mutation_check(
            context,
            contract,
            commission,
            admission_payload,
            commission_source_payload,
            synthetic_payload,
        ),
    )
    mutation_context = checks.run(
        "mutations.target-mapping",
        "All eight contract-derived target gate and reason mappings are caught.",
        lambda context: _mutation_mapping_check(context, contract, commission),
    )
    checks.run(
        "canary.missing-anchor",
        "A missing full-line mutation anchor independently hard-errors.",
        lambda context: _canary_check(
            context,
            contract,
            commission,
            synthetic_payload,
            "missing_full_line_anchor",
        ),
    )
    checks.run(
        "canary.duplicate-anchor",
        "A duplicate full-line mutation anchor independently hard-errors.",
        lambda context: _canary_check(
            context,
            contract,
            commission,
            synthetic_payload,
            "duplicate_full_line_anchor",
        ),
    )
    gate_contexts = {
        "G1": checks.run(
            "numeric.G1",
            "G1 raw hierarchy, draws, max-t LCB, systematic charge, and outcome independently rederive.",
            lambda context: _g1_check(
                context,
                contract,
                commission,
                rederived,
            ),
        ),
        "G2": checks.run(
            "numeric.G2",
            "G2 hostile charge, per-draw log-SNR max-t, exponentiated LCB, and all-cell directions recompute.",
            lambda context: _g2_check(
                context,
                contract,
                commission,
                cell_dimensions,
                rederived,
            ),
        ),
        "G3": checks.run(
            "numeric.G3",
            "G3 focus interiority, transfer LCB, conditioning, and leakage directions recompute.",
            lambda context: _g3_check(
                context,
                contract,
                commission,
                cell_dimensions,
                rederived,
            ),
        ),
        "G4": checks.run(
            "numeric.G4",
            "G4 even/odd affine holdout, clipping, slope, and residual directions recompute.",
            lambda context: _g4_check(
                context,
                contract,
                commission,
                rederived,
            ),
        ),
        "G5": checks.run(
            "numeric.G5",
            "G5 odd/even, contiguous, lagged, and common-mode formulas recompute.",
            lambda context: _g5_check(
                context,
                contract,
                commission,
                cell_dimensions,
                rederived,
            ),
        ),
        "G6": checks.run(
            "numeric.G6",
            "G6 sign, geometry tolerances, and every kernel-relative-change direction recompute.",
            lambda context: _g6_check(
                context,
                contract,
                commission,
                cell_dimensions,
                rederived,
            ),
        ),
        "G7": checks.run(
            "numeric.G7",
            "G7 hostile power charge, conditioning, uniqueness, and all-cell LCB directions recompute.",
            lambda context: _g7_check(
                context,
                contract,
                commission,
                cell_dimensions,
                rederived,
            ),
        ),
        "G8": checks.run(
            "numeric.G8",
            "G8 hostile charges, margins, common mode, LCBs, vector rule, and no-compensation recompute.",
            lambda context: _g8_check(
                context,
                contract,
                commission,
                cell_dimensions,
                rederived,
            ),
        ),
    }
    checks.run(
        "control.baseline",
        "The baseline is exactly 8/8 PASS.",
        lambda context: _baseline_control_check(context, commission),
    )
    checks.run(
        "control.planted-improvement",
        "The planted improvement passes and raises every point margin and simultaneous LCB.",
        lambda context: _planted_improvement_check(
            context,
            commission,
            cell_ids,
            rederived,
        ),
    )
    checks.run(
        "control.common-mode-false-improvement",
        "Naive readings rise in every cell while charged G8 refuses common mode.",
        lambda context: _common_mode_control_check(
            context,
            commission,
            cell_ids,
            rederived,
        ),
    )
    checks.run(
        "control.weak-vector-direction",
        "G1-G7 pass while the favorable-average vector is refused in its weakest direction.",
        lambda context: _weak_vector_control_check(
            context,
            commission,
            rederived,
        ),
    )

    partition = checks.partition()
    all_pass = partition["FAIL"] == 0 and partition["PASS_plus_FAIL"] == partition["total"]
    result = {
        "schema": VERIFICATION_SCHEMA,
        "status": "PASS" if all_pass else "FAIL",
        "verdict": (
            "INDEPENDENT_EXACT_EVIDENCE_REDERIVATION_PASS"
            if all_pass
            else "INDEPENDENT_EXACT_EVIDENCE_REDERIVATION_FAIL"
        ),
        "scope": {
            "capture_ruling": "ANALYSIS_ONLY",
            "claim_scope": contract["claim_scope"],
            "evidence": "EMBEDDED_EXACT_SEALED_SYNTHETIC_BYTES",
            "production_admission": "UNMEASURED",
            "real_capture_confidence_interval": "NO_CI",
            "coverage": (
                "EXACT_RAW_EVIDENCE_G1_G8_AND_BOOTSTRAP_REDERIVATION"
            ),
            "verifier_capture_reads": 0,
        },
        "inputs": {
            "contract": {
                "path": contract_path.relative_to(repository).as_posix(),
                "sha256": contract_sha256,
            },
            "commission": {
                "path": commission_path.relative_to(repository).as_posix(),
                "sha256": commission_sha256,
            },
            "preregistration": {
                "path": preregistration_path.relative_to(repository).as_posix(),
                "initial_commit": INITIAL_PREREGISTRATION_COMMIT,
                "amendment_one_commit": AMENDMENT_ONE_COMMIT,
                "amendment_two_commit": AMENDMENT_TWO_COMMIT,
                "amendment_three_commit": AMENDMENT_THREE_COMMIT,
                "sha256": _sha256(preregistration_payload),
            },
            "gitattributes": {
                "path": gitattributes_path.relative_to(
                    repository
                ).as_posix(),
                "sha256": _sha256(gitattributes_payload),
            },
            "admission_source": {
                "path": admission_path.relative_to(repository).as_posix(),
                "sha256": _sha256(admission_payload),
            },
            "commission_source": {
                "path": commission_source_path.relative_to(
                    repository
                ).as_posix(),
                "sha256": _sha256(commission_source_payload),
            },
            "synthetic_source": {
                "path": synthetic_path.relative_to(repository).as_posix(),
                "sha256": _sha256(synthetic_payload),
            },
            "test_source": {
                "path": test_source_path.relative_to(repository).as_posix(),
                "sha256": _sha256(test_source_payload),
            },
            "verifier_source": {
                "path": verifier_source_path.relative_to(
                    repository
                ).as_posix(),
                "sha256": _sha256(verifier_source_payload),
            },
        },
        "line_endings": {
            "attributes": attribute_context.evidence,
            "checkout_representation": checkout_context.evidence,
        },
        "campaign": campaign_context.evidence,
        "digital_k_policy": digital_k_context.evidence,
        "production_digital_k_policy_probe": (
            production_digital_k_context.evidence
        ),
        "mutation_evidence": {
            "source": source_context.evidence,
            "targets": mutation_context.evidence,
        },
        "gate_evidence": {
            gate_id: context.evidence for gate_id, context in gate_contexts.items()
        },
        "verification_partitions": partition,
        "checks": checks.records,
        "limitations": [
            "The zero-capture-read result is cross-checked across sealed commission fields; no external filesystem trace is retained in the artifact.",
            "The canary exit code is a recorded mapping from an independently reproduced hard error, not a separately observed subprocess exit.",
            "This verifier establishes synthetic commissioning consistency only; it does not license production thresholds, real data, M1 admission, or global object truth.",
        ],
        "implementation_commit": "PENDING",
    }
    for key in _walk_keys(result):
        lowered = key.casefold()
        if lowered in {"time", "elapsed", "duration"} or lowered.endswith(
            ("_time", "_elapsed", "_duration")
        ):
            raise HarnessError(f"forbidden timing field in verification output: {key}")
    return result


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, Mapping):
        for key, member in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(member))
    elif isinstance(value, list):
        for member in value:
            keys.extend(_walk_keys(member))
    return keys


def main(argv: Sequence[str] | None = None) -> int:
    parser = _argument_parser()
    args = parser.parse_args(argv)
    try:
        contract_path = _reject_d_drive(args.contract, "contract path")
        commission_path = _reject_d_drive(args.commission, "commission path")
        expected_contract_path = (HERE / "contract.json").resolve(strict=False)
        expected_commission_path = (HERE / "out" / "commission.json").resolve(
            strict=False
        )
        if not _paths_identical(contract_path, expected_contract_path):
            raise HarnessError("contract path must name the M171 frozen contract")
        if not _paths_identical(
            commission_path, expected_commission_path
        ):
            raise HarnessError("commission path must name the M171 frozen commission")
        output_path = _safe_verification_output(
            args.output,
            contract_path,
            commission_path,
        )
        if not output_path.parent.is_dir():
            raise HarnessError("verification output parent directory does not exist")
        result = verify(
            contract_path=contract_path,
            commission_path=commission_path,
            expected_commission_sha256=args.expected_commission_sha256,
            output_path=output_path,
        )
        _write_json(output_path, result)
    except HarnessError as exc:
        failure = {
            "schema": VERIFICATION_SCHEMA,
            "status": "HARNESS_ERROR",
            "error": str(exc),
        }
        print(
            json.dumps(failure, sort_keys=True, ensure_ascii=True, allow_nan=False),
            file=sys.stderr,
        )
        return 2
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
