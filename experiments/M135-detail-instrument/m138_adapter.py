#!/usr/bin/env python3
"""Hash-bound M138 adapter for the frozen M135 per-capture checker."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import types
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

HERE = Path(__file__).resolve().parent
ADAPTER_CONTRACT_PATH = HERE / "m138-adapter-contract.json"
CORE_CONTRACT_PATH = HERE / "comparison-contract.json"
CORE_BINDING_PATH = HERE / "comparison-binding.json"
BUNDLE_PATH = HERE / "m138-checker-bundle.json"
ENVIRONMENT_PATH = HERE / "m138-adapter-environment.json"
PREREGISTRATION_PATH = HERE / "M138-ADAPTER-PREREGISTRATION.md"
EXPECTED_ADAPTER_CONTRACT_SHA256 = (
    "30453f8901c0b121a48771d35c9cf735da88358bb441794b918de77b267903e2"
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
REQUEST_REFUSAL_EXIT_CODE = 2
UNEXPECTED_ERROR_EXIT_CODE = 3
BUNDLE_SOURCE_NAMES = (
    "M138-ADAPTER-PREREGISTRATION.md",
    "M138-ADAPTER-AMENDMENT-1.md",
    "M138-ADAPTER-AMENDMENT-2.md",
    "M138-ADAPTER-AMENDMENT-3.md",
    "M138-ADAPTER-AMENDMENT-4.md",
    "M138-ADAPTER-AMENDMENT-5.md",
    "M138-ADAPTER-AMENDMENT-6.md",
    "M138-ADAPTER-AMENDMENT-7.md",
    "M138-ADAPTER-AMENDMENT-8.md",
    "M138-ADAPTER-AMENDMENT-9.md",
    "comparison-binding.json",
    "comparison-contract.json",
    "comparison_checker.py",
    "instrument.py",
    "m138-adapter-contract.json",
    "m138-adapter-environment.json",
    "m138_adapter.py",
)


_core: Any | None = None
_core_sha256: str | None = None


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    data: bytes
    sha256: str


@dataclass(frozen=True)
class BundleSnapshot:
    manifest: FileSnapshot
    files: dict[str, FileSnapshot]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_text_sha256_bytes(data: bytes) -> str:
    text = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return sha256_bytes(text.encode("utf-8"))


def install_core_module(bundle: BundleSnapshot) -> Any:
    global _core, _core_sha256
    source = bundle.files["comparison_checker.py"]
    if _core is not None:
        if _core_sha256 != source.sha256:
            raise RuntimeError("comparison checker source changed within one process")
        return _core
    try:
        code = compile(source.data, str(source.path), "exec", dont_inherit=True)
        module = types.ModuleType("m135_comparison_checker")
        module.__file__ = str(source.path)
        module.__package__ = ""
        exec(code, module.__dict__)

        snapshots_by_path = {
            snapshot.path.resolve(): snapshot for snapshot in bundle.files.values()
        }

        def verified_sha256(path: Path) -> str:
            resolved = Path(path).resolve()
            snapshot = snapshots_by_path.get(resolved)
            if snapshot is None:
                raise RuntimeError(
                    f"core attempted an unverified source read: {resolved}"
                )
            return snapshot.sha256

        def verified_normalized_text_sha256(path: Path) -> str:
            resolved = Path(path).resolve()
            snapshot = snapshots_by_path.get(resolved)
            if snapshot is None:
                raise RuntimeError(
                    f"core attempted an unverified text read: {resolved}"
                )
            return normalized_text_sha256_bytes(snapshot.data)

        def verified_load_json(path: Path) -> dict[str, Any]:
            resolved = Path(path).resolve()
            snapshot = snapshots_by_path.get(resolved)
            if snapshot is None:
                raise RuntimeError(
                    f"core attempted an unverified JSON read: {resolved}"
                )
            return json_object_from_bytes(snapshot.data, snapshot.path.name)

        module.sha256 = verified_sha256
        module.normalized_text_sha256 = verified_normalized_text_sha256
        module.load_json = verified_load_json
    except Exception as error:
        raise RuntimeError(
            f"could not execute frozen comparison checker: {error}"
        ) from error
    _core = module
    _core_sha256 = source.sha256
    return _core


def require_core_module() -> Any:
    if _core is None:
        raise RuntimeError("frozen comparison checker was not installed")
    return _core


class AdapterRefusal(ValueError):
    def __init__(self, status: str, reason: str) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason


@dataclass(frozen=True)
class Runtime:
    adapter_contract: dict[str, Any]
    core_contract: dict[str, Any]
    binding: dict[str, Any]
    binding_state: str
    checker_sha256: str
    bundle_sha256: str
    environment_sha256: str
    comparison_rule_sha256: str


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_file_once(path: Path, label: str) -> FileSnapshot:
    resolved = path.resolve()
    try:
        data = resolved.read_bytes()
    except OSError as error:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", f"{label} could not be read: {error}"
        ) from error
    return FileSnapshot(path=resolved, data=data, sha256=sha256_bytes(data))


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def canonical_json_line(value: Any) -> bytes:
    return canonical_json_bytes(value) + b"\n"


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = child
    return value


def json_object_from_bytes(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", f"{label} is not strict JSON: {error}"
        ) from error
    if not isinstance(value, dict):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", f"{label} must contain one JSON object"
        )
    return value


def snapshot_json_object(snapshot: FileSnapshot, label: str) -> dict[str, Any]:
    return json_object_from_bytes(snapshot.data, label)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_line(value))


def emit_json(value: Any, output: Path | None) -> None:
    encoded = canonical_json_line(value)
    if output is None:
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AdapterRefusal("INSTRUMENT_INVALID", f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"{label} fields differ: missing={missing}, extra={extra}",
        )
    return value


def reject_supplied_decisions(value: Any, path: str = "$") -> None:
    forbidden = {
        "detail_pass",
        "detail_pass_by_capture",
        "detail_state_by_capture",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            if key in forbidden:
                raise AdapterRefusal(
                    "INSTRUMENT_INVALID",
                    f"{path}.{key}: producer-supplied detail decision is forbidden",
                )
            reject_supplied_decisions(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_supplied_decisions(child, f"{path}[{index}]")


def parse_relative_posix_path(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", f"{label}.path must be a nonempty string"
        )
    if "\\" in value or ":" in value or value.startswith("/"):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"{label}.path must use relative POSIX syntax",
        )
    raw_parts = value.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"{label}.path contains an empty or traversal component",
        )
    path = PurePosixPath(value)
    if path.is_absolute() or tuple(path.parts) != tuple(raw_parts):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", f"{label}.path is not a canonical relative path"
        )
    return tuple(raw_parts)


def verify_artifact_ref(
    ref: Any,
    *,
    base: Path,
    root: Path,
    label: str,
) -> FileSnapshot:
    row = require_exact_keys(ref, {"path", "sha256"}, label)
    parts = parse_relative_posix_path(row["path"], label)
    if not valid_sha256(row["sha256"]):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"{label}.sha256 must be 64 lowercase hexadecimal digits",
        )
    target = (base / Path(*parts)).resolve()
    root_resolved = root.resolve()
    try:
        target.relative_to(root_resolved)
    except ValueError as error:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", f"{label}.path escapes its evidence root"
        ) from error
    snapshot = read_file_once(target, label)
    if snapshot.sha256 != row["sha256"]:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"{label} SHA-256 mismatch: expected {row['sha256']}, "
            f"observed {snapshot.sha256}",
        )
    return snapshot


def ref_key(ref: Any, label: str) -> tuple[str, str]:
    row = require_exact_keys(ref, {"path", "sha256"}, label)
    parse_relative_posix_path(row["path"], label)
    if not valid_sha256(row["sha256"]):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", f"{label}.sha256 is not a valid SHA-256"
        )
    return row["path"], row["sha256"]


def verify_declared_artifacts(
    request: dict[str, Any], request_path: Path
) -> dict[tuple[str, str], FileSnapshot]:
    refs = request.get("artifacts")
    if not isinstance(refs, list) or not refs:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", "request.artifacts must be a nonempty list"
        )
    verified: dict[tuple[str, str], FileSnapshot] = {}
    seen_paths: set[str] = set()
    for index, ref in enumerate(refs):
        label = f"request.artifacts[{index}]"
        key = ref_key(ref, label)
        if key[0] in seen_paths:
            raise AdapterRefusal(
                "INSTRUMENT_INVALID", f"duplicate declared artifact path: {key[0]}"
            )
        seen_paths.add(key[0])
        verified[key] = verify_artifact_ref(
            ref,
            base=request_path.parent,
            root=request_path.parent,
            label=label,
        )
    return verified


def declared_artifact_snapshot(
    ref: Any,
    verified: dict[tuple[str, str], FileSnapshot],
    label: str,
) -> FileSnapshot:
    key = ref_key(ref, label)
    if key not in verified:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"{label} is absent from the top-level artifacts ledger",
        )
    return verified[key]


def current_environment() -> dict[str, Any]:
    return {
        "schema": "m135-checker-environment/v1",
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "numpy_version": importlib.metadata.version("numpy"),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "isolated_python_required": True,
    }


def environment_matches(
    manifest: dict[str, Any], expected: dict[str, Any]
) -> bool:
    return manifest == expected


def validate_environment(snapshot: FileSnapshot) -> str:
    manifest = snapshot_json_object(snapshot, "environment manifest")
    expected = current_environment()
    if not environment_matches(manifest, expected):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"runtime environment differs from manifest: expected={manifest}, "
            f"observed={expected}",
        )
    if sys.flags.isolated != 1:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", "checker must be invoked through python -I"
        )
    return snapshot.sha256


def validate_bundle() -> BundleSnapshot:
    manifest_snapshot = read_file_once(BUNDLE_PATH, "checker bundle manifest")
    bundle = snapshot_json_object(manifest_snapshot, "checker bundle manifest")
    require_exact_keys(bundle, {"schema", "rule_id", "files"}, "checker bundle")
    if bundle["schema"] != "m135-checker-bundle/v1":
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", "unsupported checker bundle schema"
        )
    if bundle["rule_id"] != "m135-m138-adapter-v1":
        raise AdapterRefusal("INSTRUMENT_INVALID", "checker bundle rule ID changed")
    refs = bundle["files"]
    if not isinstance(refs, list) or not refs:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", "checker bundle files must be a nonempty list"
        )
    observed_names: set[str] = set()
    files: dict[str, FileSnapshot] = {}
    for index, ref in enumerate(refs):
        label = f"checker bundle files[{index}]"
        key = ref_key(ref, label)
        if key[0] in observed_names:
            raise AdapterRefusal(
                "INSTRUMENT_INVALID", f"duplicate checker bundle path: {key[0]}"
            )
        observed_names.add(key[0])
        files[key[0]] = verify_artifact_ref(
            ref, base=HERE, root=HERE, label=label
        )
    missing = sorted(set(BUNDLE_SOURCE_NAMES) - observed_names)
    if missing:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"checker bundle omits required transitive files: {missing}",
        )
    return BundleSnapshot(manifest=manifest_snapshot, files=files)


def bundle_file(bundle: BundleSnapshot, name: str) -> FileSnapshot:
    try:
        return bundle.files[name]
    except KeyError as error:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"checker bundle omits required transitive file: {name}",
        ) from error


def load_runtime() -> Runtime:
    bundle = validate_bundle()
    adapter_contract = snapshot_json_object(
        bundle_file(bundle, ADAPTER_CONTRACT_PATH.name),
        "M138 adapter contract",
    )
    if canonical_json_sha256(adapter_contract) != EXPECTED_ADAPTER_CONTRACT_SHA256:
        raise AdapterRefusal("INSTRUMENT_INVALID", "adapter contract hash drift")
    if adapter_contract.get("schema") != "m135-m138-adapter-contract-v1":
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", "unsupported adapter contract schema"
        )
    environment_sha256 = validate_environment(
        bundle_file(bundle, ENVIRONMENT_PATH.name)
    )
    try:
        module = install_core_module(bundle)
        core_contract = module.load_json(CORE_CONTRACT_PATH)
        module.validate_contract(core_contract)
        binding = module.load_json(CORE_BINDING_PATH)
        state = module.validate_binding_structure(binding, core_contract)
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", f"frozen core validation failed: {error}"
        ) from error
    return Runtime(
        adapter_contract=adapter_contract,
        core_contract=core_contract,
        binding=binding,
        binding_state=str(state),
        checker_sha256=bundle_file(
            bundle, Path(__file__).name
        ).sha256,
        bundle_sha256=bundle.manifest.sha256,
        environment_sha256=environment_sha256,
        comparison_rule_sha256=bundle_file(
            bundle, CORE_CONTRACT_PATH.name
        ).sha256,
    )


def common_binding_hash_matches(observed: str, expected: str) -> bool:
    return observed == expected


def physical_binding_hash_matches(observed: str, expected: str) -> bool:
    return observed == expected


def validate_binding_hashes(request: dict[str, Any], runtime: Runtime) -> None:
    expected_fields = set(runtime.adapter_contract["binding_hash_fields"])
    hashes = require_exact_keys(
        request.get("binding_hashes"), expected_fields, "request.binding_hashes"
    )
    for field in expected_fields:
        if not valid_sha256(hashes[field]):
            raise AdapterRefusal(
                "INSTRUMENT_INVALID",
                f"request.binding_hashes.{field} is not a valid SHA-256",
            )
    expected = {
        "checker_bundle_manifest_sha256": runtime.bundle_sha256,
        "environment_manifest_sha256": runtime.environment_sha256,
        "comparison_rule_sha256": runtime.comparison_rule_sha256,
    }
    for field, value in expected.items():
        if not common_binding_hash_matches(hashes[field], value):
            raise AdapterRefusal(
                "INSTRUMENT_INVALID",
                f"request binding hash mismatch for {field}",
            )
    if runtime.binding_state == "UNBOUND":
        raise AdapterRefusal(
            "INSTRUMENT_UNBOUND", "physical M135 comparison binding is UNBOUND"
        )
    physical_hash = runtime.binding.get("physical_preregistration_sha256")
    if not physical_binding_hash_matches(
        hashes["physical_preregistration_sha256"], physical_hash
    ):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            "request binding hash mismatch for physical_preregistration_sha256",
        )


def common_output(request_sha256: str, runtime: Runtime) -> dict[str, Any]:
    hashes = {
        "checker_bundle_manifest_sha256": runtime.bundle_sha256,
        "environment_manifest_sha256": runtime.environment_sha256,
        "physical_preregistration_sha256": runtime.binding[
            "physical_preregistration_sha256"
        ],
        "comparison_rule_sha256": runtime.comparison_rule_sha256,
    }
    return {
        "schema": runtime.adapter_contract["interface_schema"],
        "checker_sha256": runtime.checker_sha256,
        **hashes,
        "request_sha256": request_sha256,
    }


def load_core_payload(
    ref: Any,
    *,
    verified: dict[tuple[str, str], FileSnapshot],
    label: str,
) -> dict[str, Any]:
    snapshot = declared_artifact_snapshot(ref, verified, label)
    payload = snapshot_json_object(snapshot, label)
    reject_supplied_decisions(payload, label)
    return payload


def core_decision(payload: dict[str, Any], runtime: Runtime) -> dict[str, Any]:
    module = require_core_module()
    decision = module.adjudicate(payload, runtime.binding, runtime.core_contract)
    status = decision.get("status")
    if status == runtime.adapter_contract["evaluation"]["unbound_core_status"]:
        raise AdapterRefusal(
            "INSTRUMENT_UNBOUND",
            str(decision.get("reason", "physical M135 binding is UNBOUND")),
        )
    return decision


def process_evaluate(
    request_path: Path,
    request_sha256: str,
    request: dict[str, Any],
    runtime: Runtime,
) -> dict[str, Any]:
    require_exact_keys(
        request,
        {"schema", "capture_ids", "artifacts", "binding_hashes", "comparisons"},
        "evaluation request",
    )
    if request["schema"] != runtime.adapter_contract["evaluate_request_schema"]:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", "unsupported M138 evaluation request schema"
        )
    reject_supplied_decisions(request)
    verified = verify_declared_artifacts(request, request_path)
    validate_binding_hashes(request, runtime)

    capture_ids = request["capture_ids"]
    if (
        not isinstance(capture_ids, list)
        or not capture_ids
        or any(not isinstance(value, str) or not value for value in capture_ids)
        or len(set(capture_ids)) != len(capture_ids)
    ):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            "capture_ids must be a nonempty list of unique nonempty strings",
        )
    comparisons = request["comparisons"]
    if not isinstance(comparisons, list) or len(comparisons) != len(capture_ids):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            "comparisons must contain exactly one row per capture",
        )

    accepted = runtime.adapter_contract["evaluation"]["accepted_core_statuses"]
    invalid_statuses = set(
        runtime.adapter_contract["evaluation"]["invalid_core_statuses"]
    )
    invalid_output = runtime.adapter_contract["evaluation"]["invalid_output_state"]
    states: dict[str, str] = {}
    passes: dict[str, bool] = {}
    for index, (capture_id, raw_row) in enumerate(zip(capture_ids, comparisons)):
        row = require_exact_keys(
            raw_row, {"capture_id", "payload"}, f"comparisons[{index}]"
        )
        if row["capture_id"] != capture_id:
            raise AdapterRefusal(
                "INSTRUMENT_INVALID",
                f"comparisons[{index}] is out of capture_ids order",
            )
        payload = load_core_payload(
            row["payload"],
            verified=verified,
            label=f"comparisons[{index}].payload",
        )
        if payload.get("capture_id") != capture_id:
            raise AdapterRefusal(
                "INSTRUMENT_INVALID",
                f"comparisons[{index}] payload capture ID mismatch",
            )
        decision = core_decision(payload, runtime)
        status = decision.get("status")
        if status in accepted:
            states[capture_id] = str(status)
            passes[capture_id] = bool(accepted[status])
        elif status in invalid_statuses:
            states[capture_id] = str(invalid_output)
        else:
            raise AdapterRefusal(
                "INSTRUMENT_INVALID",
                f"core returned unsupported decision status for {capture_id}: {status}",
            )

    return {
        **common_output(request_sha256, runtime),
        runtime.adapter_contract["evaluation"]["decision_state_field"]: states,
        runtime.adapter_contract["evaluation"]["boolean_field"]: passes,
    }


def information_quantiles(
    payload: dict[str, Any], runtime: Runtime
) -> tuple[float, float]:
    module = require_core_module()
    values = module.np.asarray(
        payload["bootstrap"]["information_ratio"], dtype=module.np.float64
    )
    method = runtime.adapter_contract["commissioning"]["quantile_method"]
    return (
        float(module.np.quantile(values, 0.05, method=method)),
        float(module.np.quantile(values, 0.95, method=method)),
    )


def commission_payload(
    raw_control: Any,
    *,
    verified: dict[tuple[str, str], FileSnapshot],
    label: str,
    runtime: Runtime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    control = require_exact_keys(raw_control, {"payload"}, label)
    payload = load_core_payload(
        control["payload"], verified=verified, label=f"{label}.payload"
    )
    return payload, core_decision(payload, runtime)


def null_decision_requires_refusal(
    status: Any, invalid_statuses: set[str]
) -> bool:
    return status in invalid_statuses


def blur_decision_requires_refusal(
    status: Any, invalid_statuses: set[str]
) -> bool:
    return status in invalid_statuses


def improvement_decision_requires_refusal(
    status: Any, invalid_statuses: set[str]
) -> bool:
    return status in invalid_statuses


def missing_decision_requires_refusal(status: Any) -> bool:
    return status == "NOT_APPLICABLE"


def mutation_digest_is_invalid(value: Any) -> bool:
    return not valid_sha256(value)


def physical_null_control_passes(
    status: Any,
    q05: float,
    q95: float,
    low: float,
    high: float,
) -> bool:
    return bool(
        status == "DETAIL_PASS"
        and q05 >= low
        and q05 <= 1.0
        and q95 >= 1.0
        and q95 <= high
    )


def commissioning_blur_information_bar(config: dict[str, Any]) -> float:
    return float(
        config["pre_noise_blur_information_ratio_q95_strictly_below"]
    )


def commissioning_improvement_information_bar(
    config: dict[str, Any],
) -> float:
    return float(
        config[
            "pre_noise_optical_improvement_information_ratio_q05_strictly_above"
        ]
    )


def blur_control_passes(
    status: Any, q95: float, config: dict[str, Any]
) -> bool:
    return bool(
        status == "DETAIL_FAIL"
        and q95 < commissioning_blur_information_bar(config)
    )


def improvement_control_passes(
    status: Any, q05: float, config: dict[str, Any]
) -> bool:
    return bool(
        status == "DETAIL_PASS"
        and q05 > commissioning_improvement_information_bar(config)
    )


def missing_flat_control_passes(status: Any, reason: str) -> bool:
    return bool(
        status == "INSTRUMENT_INVALID"
        and "flat control is missing" in reason
    )


def hash_mutation_control_passes(
    error: AdapterRefusal | None,
    first_snapshot: FileSnapshot,
    second_snapshot: FileSnapshot,
) -> bool:
    return bool(
        error is not None
        and "SHA-256 mismatch" in error.reason
        and first_snapshot == second_snapshot
    )


def commissioning_control_set_matches(
    controls: dict[str, bool], expected: set[str]
) -> bool:
    return set(controls) == expected


def verify_snapshot_digest(
    snapshot: FileSnapshot, expected_sha256: str, label: str
) -> None:
    if snapshot.sha256 != expected_sha256:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"{label} SHA-256 mismatch: expected {expected_sha256}, "
            f"observed {snapshot.sha256}",
        )


def process_commission(
    request_path: Path,
    request_sha256: str,
    request: dict[str, Any],
    runtime: Runtime,
) -> dict[str, Any]:
    require_exact_keys(
        request,
        {"schema", "artifacts", "binding_hashes", "controls"},
        "commissioning request",
    )
    if request["schema"] != runtime.adapter_contract["commission_request_schema"]:
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", "unsupported M138 commissioning request schema"
        )
    reject_supplied_decisions(request)
    verified = verify_declared_artifacts(request, request_path)
    validate_binding_hashes(request, runtime)

    expected_inputs = set(
        runtime.adapter_contract["commissioning"]["required_input_controls"]
    )
    controls_in = require_exact_keys(
        request["controls"], expected_inputs, "commissioning request.controls"
    )
    invalid_statuses = set(
        runtime.adapter_contract["evaluation"]["invalid_core_statuses"]
    )

    null_payload, null_decision = commission_payload(
        controls_in["physical_null"],
        verified=verified,
        label="controls.physical_null",
        runtime=runtime,
    )
    if null_decision_requires_refusal(
        null_decision.get("status"), invalid_statuses
    ):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"physical null could not be adjudicated: {null_decision.get('reason')}",
        )
    null_q05, null_q95 = information_quantiles(null_payload, runtime)
    null_low, null_high = runtime.adapter_contract["commissioning"][
        "physical_null_information_ratio_interval"
    ]

    blur_payload, blur_decision = commission_payload(
        controls_in["pre_noise_blur"],
        verified=verified,
        label="controls.pre_noise_blur",
        runtime=runtime,
    )
    if blur_decision_requires_refusal(
        blur_decision.get("status"), invalid_statuses
    ):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"blur control could not be adjudicated: {blur_decision.get('reason')}",
        )
    _, blur_q95 = information_quantiles(blur_payload, runtime)

    improvement_payload, improvement_decision = commission_payload(
        controls_in["pre_noise_optical_improvement"],
        verified=verified,
        label="controls.pre_noise_optical_improvement",
        runtime=runtime,
    )
    if improvement_decision_requires_refusal(
        improvement_decision.get("status"), invalid_statuses
    ):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            "optical-improvement control could not be adjudicated: "
            f"{improvement_decision.get('reason')}",
        )
    improvement_q05, _ = information_quantiles(improvement_payload, runtime)

    missing_payload, missing_decision = commission_payload(
        controls_in["missing_flat_control"],
        verified=verified,
        label="controls.missing_flat_control",
        runtime=runtime,
    )
    _ = missing_payload
    missing_status = missing_decision.get("status")
    missing_reason = str(missing_decision.get("reason", "")).lower()
    if missing_decision_requires_refusal(missing_status):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            "missing-flat control capture is absent from the physical binding",
        )

    mutation = require_exact_keys(
        controls_in["hash_mutation"],
        {"artifact", "mutated_sha256"},
        "controls.hash_mutation",
    )
    first_snapshot = declared_artifact_snapshot(
        mutation["artifact"], verified, "controls.hash_mutation.artifact"
    )
    if mutation_digest_is_invalid(mutation["mutated_sha256"]):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID",
            "controls.hash_mutation.mutated_sha256 is not a valid SHA-256",
        )
    mutation_ref = {
        "path": mutation["artifact"]["path"],
        "sha256": mutation["mutated_sha256"],
    }
    hash_mutation_error: AdapterRefusal | None = None
    try:
        verify_snapshot_digest(
            first_snapshot,
            mutation_ref["sha256"],
            "controls.hash_mutation.probe",
        )
    except AdapterRefusal as error:
        hash_mutation_error = error
    second_snapshot = declared_artifact_snapshot(
        mutation["artifact"],
        verified,
        "controls.hash_mutation.artifact",
    )
    hash_mutation_refused = hash_mutation_control_passes(
        hash_mutation_error,
        first_snapshot,
        second_snapshot,
    )

    commission_cfg = runtime.adapter_contract["commissioning"]
    controls_out = {
        "physical_null_stays_null": physical_null_control_passes(
            null_decision.get("status"),
            null_q05,
            null_q95,
            float(null_low),
            float(null_high),
        ),
        "pre_noise_blur_lowers_information": blur_control_passes(
            blur_decision.get("status"),
            blur_q95,
            commission_cfg,
        ),
        "pre_noise_optical_improvement_raises_information": (
            improvement_control_passes(
                improvement_decision.get("status"),
                improvement_q05,
                commission_cfg,
            )
        ),
        "missing_flat_control_refuses": missing_flat_control_passes(
            missing_status, missing_reason
        ),
        "artifact_hash_mutation_refuses": hash_mutation_refused,
    }
    expected_outputs = set(commission_cfg["required_output_controls"])
    if not commissioning_control_set_matches(controls_out, expected_outputs):
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", "internal commissioning control set drift"
        )
    return {**common_output(request_sha256, runtime), "controls": controls_out}


def make_ref(path: Path, base: Path) -> dict[str, str]:
    relative = path.resolve().relative_to(base.resolve()).as_posix()
    return {"path": relative, "sha256": file_sha256(path)}


def write_bundle_manifest(root: Path) -> Path:
    manifest = {
        "schema": "m135-checker-bundle/v1",
        "rule_id": "m135-m138-adapter-v1",
        "files": [make_ref(root / name, root) for name in BUNDLE_SOURCE_NAMES],
    }
    path = root / BUNDLE_PATH.name
    write_json(path, manifest)
    return path


def mutation_probe_checks() -> dict[str, bool]:
    checks: dict[str, bool] = {}

    try:
        reject_supplied_decisions({"outer": {"detail_pass": True}})
    except AdapterRefusal:
        checks["guard_nested_supplied_decision"] = True
    else:
        checks["guard_nested_supplied_decision"] = False

    observed_environment = current_environment()
    changed_environment = dict(observed_environment)
    changed_environment["python_version"] = "mutation-probe"
    checks["guard_environment_equality"] = not environment_matches(
        changed_environment, observed_environment
    )
    checks["guard_common_binding_hash"] = not common_binding_hash_matches(
        "0" * 64, "1" * 64
    )
    checks["guard_physical_binding_hash"] = not physical_binding_hash_matches(
        "0" * 64, "1" * 64
    )
    checks["guard_canonical_terminal_newline"] = canonical_json_line(
        {"probe": True}
    ).endswith(b"\n")

    invalid_statuses = {"INSTRUMENT_INVALID", "NOT_APPLICABLE"}
    checks["guard_commission_null_invalid_status"] = (
        null_decision_requires_refusal("INSTRUMENT_INVALID", invalid_statuses)
    )
    checks["guard_commission_blur_invalid_status"] = (
        blur_decision_requires_refusal("INSTRUMENT_INVALID", invalid_statuses)
    )
    checks["guard_commission_improvement_invalid_status"] = (
        improvement_decision_requires_refusal(
            "INSTRUMENT_INVALID", invalid_statuses
        )
    )
    checks["guard_commission_missing_not_applicable"] = (
        missing_decision_requires_refusal("NOT_APPLICABLE")
    )
    checks["guard_commission_mutated_sha_format"] = mutation_digest_is_invalid(
        "g" * 64
    )
    checks["guard_commission_output_set"] = not commissioning_control_set_matches(
        {"unexpected": False}, {"expected"}
    )

    snapshot_a = FileSnapshot(Path("a.json"), b"a", sha256_bytes(b"a"))
    snapshot_b = FileSnapshot(Path("a.json"), b"b", sha256_bytes(b"b"))
    mismatch = AdapterRefusal(
        "INSTRUMENT_INVALID",
        "probe SHA-256 mismatch: expected 0, observed 1",
    )
    wrong_reason = AdapterRefusal("INSTRUMENT_INVALID", "different refusal")
    checks["guard_commission_hash_requires_error"] = (
        not hash_mutation_control_passes(None, snapshot_a, snapshot_a)
    )
    checks["guard_commission_hash_requires_mismatch_reason"] = (
        not hash_mutation_control_passes(
            wrong_reason, snapshot_a, snapshot_a
        )
    )
    checks["guard_commission_hash_requires_same_snapshot"] = (
        not hash_mutation_control_passes(mismatch, snapshot_a, snapshot_b)
    )

    checks["guard_commission_null_status"] = not physical_null_control_passes(
        "DETAIL_FAIL", 1.0, 1.0, 0.95, 1.05
    )
    checks["guard_commission_null_q05_lower"] = (
        not physical_null_control_passes(
            "DETAIL_PASS", 0.94, 1.0, 0.95, 1.05
        )
    )
    checks["guard_commission_null_q05_upper"] = (
        not physical_null_control_passes(
            "DETAIL_PASS", 1.01, 1.01, 0.95, 1.05
        )
    )
    checks["guard_commission_null_q95_lower"] = (
        not physical_null_control_passes(
            "DETAIL_PASS", 0.99, 0.99, 0.95, 1.05
        )
    )
    checks["guard_commission_null_q95_upper"] = (
        not physical_null_control_passes(
            "DETAIL_PASS", 1.0, 1.06, 0.95, 1.05
        )
    )
    threshold_config = {
        "pre_noise_blur_information_ratio_q95_strictly_below": 0.90,
        "pre_noise_optical_improvement_information_ratio_q05_strictly_above": 1.10,
    }
    checks["guard_commission_blur_status"] = not blur_control_passes(
        "DETAIL_PASS", 0.80, threshold_config
    )
    checks["guard_commission_blur_q95"] = not blur_control_passes(
        "DETAIL_FAIL", 0.90, threshold_config
    )
    checks["guard_commission_improvement_status"] = (
        not improvement_control_passes(
            "DETAIL_FAIL", 1.20, threshold_config
        )
    )
    checks["guard_commission_improvement_q05"] = (
        not improvement_control_passes(
            "DETAIL_PASS", 1.10, threshold_config
        )
    )
    checks["guard_commission_blur_contract_threshold"] = (
        commissioning_blur_information_bar(threshold_config) == 0.90
    )
    checks["guard_commission_improvement_contract_threshold"] = (
        commissioning_improvement_information_bar(threshold_config) == 1.10
    )
    alternate_threshold_config = {
        "pre_noise_blur_information_ratio_q95_strictly_below": 0.70,
        "pre_noise_optical_improvement_information_ratio_q05_strictly_above": 1.30,
    }
    checks["guard_commission_blur_uses_config"] = (
        not blur_control_passes(
            "DETAIL_FAIL", 0.80, alternate_threshold_config
        )
    )
    checks["guard_commission_improvement_uses_config"] = (
        not improvement_control_passes(
            "DETAIL_PASS", 1.20, alternate_threshold_config
        )
    )
    checks["guard_commission_missing_status"] = (
        not missing_flat_control_passes(
            "DETAIL_FAIL", "flat control is missing"
        )
    )
    checks["guard_commission_missing_reason"] = (
        not missing_flat_control_passes(
            "INSTRUMENT_INVALID", "different refusal"
        )
    )
    return checks


def copy_self_test_runtime(
    root: Path, binding: dict[str, Any], name: str = "runtime"
) -> Path:
    runtime = root / name
    runtime.mkdir(parents=True, exist_ok=False)
    for name in BUNDLE_SOURCE_NAMES:
        if name == CORE_BINDING_PATH.name:
            continue
        shutil.copy2(HERE / name, runtime / name)
    write_json(runtime / CORE_BINDING_PATH.name, binding)
    write_bundle_manifest(runtime)
    return runtime


def add_synthetic_capture(
    binding: dict[str, Any],
    contract: dict[str, Any],
    capture_id: str,
) -> None:
    binding["applicable_captures"][capture_id] = {
        "site_count": 64,
        **{
            field: hashlib.sha256(f"{capture_id}:{field}".encode("utf-8")).hexdigest()
            for field in contract["required_capture_hashes"]
        },
    }


def synthetic_payload_for(
    contract: dict[str, Any],
    binding: dict[str, Any],
    capture_id: str,
    *,
    information: float = 1.0,
    transfer: float = 1.0,
    unexplained: float = 0.0,
) -> dict[str, Any]:
    module = require_core_module()
    payload = module.synthetic_payload(
        contract,
        binding,
        information=information,
        transfer=transfer,
        unexplained=unexplained,
    )
    payload["capture_id"] = capture_id
    capture_binding = binding["applicable_captures"][capture_id]
    for field in contract["required_capture_hashes"]:
        payload["lineage"][field] = capture_binding[field]
    return payload


def self_test_binding_hashes(
    runtime: Path, binding: dict[str, Any]
) -> dict[str, str]:
    return {
        "checker_bundle_manifest_sha256": file_sha256(
            runtime / BUNDLE_PATH.name
        ),
        "environment_manifest_sha256": file_sha256(
            runtime / ENVIRONMENT_PATH.name
        ),
        "physical_preregistration_sha256": (
            binding.get("physical_preregistration_sha256")
            if valid_sha256(binding.get("physical_preregistration_sha256"))
            else "f" * 64
        ),
        "comparison_rule_sha256": file_sha256(
            runtime / CORE_CONTRACT_PATH.name
        ),
    }


def invoke_self_test_adapter(
    runtime: Path, mode: str, request_path: Path
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(runtime / Path(__file__).name),
            f"--m138-{mode}",
            str(request_path),
        ],
        cwd=runtime,
        check=False,
        capture_output=True,
        timeout=120,
    )


def invoke_self_test_description(
    runtime: Path,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(runtime / Path(__file__).name),
            "--describe",
        ],
        cwd=runtime,
        check=False,
        capture_output=True,
        timeout=120,
    )


def parsed_stdout(completed: subprocess.CompletedProcess[bytes]) -> dict[str, Any]:
    try:
        value = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"subprocess stdout is not JSON: {error}") from error
    if not isinstance(value, dict):
        raise AssertionError("subprocess stdout is not a JSON object")
    return value


def parsed_stderr(completed: subprocess.CompletedProcess[bytes]) -> dict[str, Any]:
    try:
        value = json.loads(completed.stderr.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"subprocess stderr is not JSON: {error}") from error
    if not isinstance(value, dict):
        raise AssertionError("subprocess stderr is not a JSON object")
    return value


def run_self_test(runtime_state: Runtime) -> dict[str, Any]:
    scratch = HERE / f".m138-adapter-selftest-{os.getpid()}"
    if scratch.exists():
        raise AdapterRefusal(
            "INSTRUMENT_INVALID", f"self-test scratch already exists: {scratch.name}"
        )
    checks: dict[str, bool] = {}
    try:
        scratch.mkdir()
        checks.update(mutation_probe_checks())
        module = require_core_module()
        contract = copy.deepcopy(runtime_state.core_contract)
        bound = module.synthetic_binding(contract)
        capture_ids = (
            "capture-pass",
            "capture-fail",
            "capture-null",
            "capture-blur",
            "capture-improvement",
            "capture-missing-flat",
            "capture-flat-roi",
            "capture-blur-threshold",
            "capture-improvement-threshold",
        )
        for capture_id in capture_ids:
            add_synthetic_capture(bound, contract, capture_id)
        runtime = copy_self_test_runtime(scratch, bound)
        evidence = scratch / "evidence"
        payload_dir = evidence / "payloads"
        payload_dir.mkdir(parents=True)

        payloads = {
            "pass": synthetic_payload_for(
                contract, bound, "capture-pass", information=1.0
            ),
            "fail": synthetic_payload_for(
                contract, bound, "capture-fail", information=0.70
            ),
            "null": synthetic_payload_for(
                contract, bound, "capture-null", information=1.0
            ),
            "blur": synthetic_payload_for(
                contract, bound, "capture-blur", information=0.70
            ),
            "improvement": synthetic_payload_for(
                contract,
                bound,
                "capture-improvement",
                information=1.20,
                transfer=1.10,
                unexplained=-0.05,
            ),
            "missing-flat": synthetic_payload_for(
                contract, bound, "capture-missing-flat"
            ),
            "flat-roi": synthetic_payload_for(
                contract, bound, "capture-flat-roi"
            ),
            "blur-threshold": synthetic_payload_for(
                contract, bound, "capture-blur-threshold", information=0.95
            ),
            "improvement-threshold": synthetic_payload_for(
                contract,
                bound,
                "capture-improvement-threshold",
                information=1.00,
            ),
        }
        del payloads["missing-flat"]["modes"]["candidate"]["flat_control"]
        payloads["flat-roi"]["modes"]["candidate"]["status"] = "NO_DETAIL"
        not_applicable = copy.deepcopy(payloads["pass"])
        not_applicable["capture_id"] = "capture-not-applicable"
        payloads["not-applicable"] = not_applicable

        refs: dict[str, dict[str, str]] = {}
        for name, payload in payloads.items():
            path = payload_dir / f"{name}.json"
            write_json(path, payload)
            refs[name] = make_ref(path, evidence)

        binding_hashes = self_test_binding_hashes(runtime, bound)

        valid_request = {
            "schema": "m135-m138-evaluate-request/v1",
            "capture_ids": ["capture-pass", "capture-fail"],
            "artifacts": [refs["pass"], refs["fail"]],
            "binding_hashes": binding_hashes,
            "comparisons": [
                {"capture_id": "capture-pass", "payload": refs["pass"]},
                {"capture_id": "capture-fail", "payload": refs["fail"]},
            ],
        }
        valid_path = evidence / "valid-evaluate.json"
        write_json(valid_path, valid_request)
        valid_run = invoke_self_test_adapter(runtime, "evaluate", valid_path)
        valid_repeat = invoke_self_test_adapter(runtime, "evaluate", valid_path)
        valid_output = parsed_stdout(valid_run)
        checks["valid_verdict_exit_zero"] = valid_run.returncode == 0
        checks["valid_state_map_complete"] = valid_output.get(
            "detail_state_by_capture"
        ) == {
            "capture-pass": "DETAIL_PASS",
            "capture-fail": "DETAIL_FAIL",
        }
        checks["valid_boolean_map_pass_and_fail"] = valid_output.get(
            "detail_pass_by_capture"
        ) == {"capture-pass": True, "capture-fail": False}
        checks["valid_output_hashes_bound"] = all(
            valid_output.get(field) == expected
            for field, expected in {
                "checker_sha256": file_sha256(runtime / Path(__file__).name),
                **binding_hashes,
                "request_sha256": file_sha256(valid_path),
            }.items()
        )
        checks["repeat_output_byte_stable"] = (
            valid_repeat.returncode == 0
            and valid_repeat.stdout == valid_run.stdout
            and valid_repeat.stderr == valid_run.stderr
        )

        invalid_request = {
            "schema": "m135-m138-evaluate-request/v1",
            "capture_ids": [
                "capture-pass",
                "capture-flat-roi",
                "capture-missing-flat",
            ],
            "artifacts": [
                refs["pass"],
                refs["flat-roi"],
                refs["missing-flat"],
            ],
            "binding_hashes": binding_hashes,
            "comparisons": [
                {"capture_id": "capture-pass", "payload": refs["pass"]},
                {"capture_id": "capture-flat-roi", "payload": refs["flat-roi"]},
                {
                    "capture_id": "capture-missing-flat",
                    "payload": refs["missing-flat"],
                },
            ],
        }
        invalid_path = evidence / "invalid-evaluate.json"
        write_json(invalid_path, invalid_request)
        invalid_run = invoke_self_test_adapter(runtime, "evaluate", invalid_path)
        invalid_output = parsed_stdout(invalid_run)
        checks["internal_invalid_exit_zero"] = invalid_run.returncode == 0
        checks["flat_roi_has_invalid_state"] = invalid_output.get(
            "detail_state_by_capture", {}
        ).get("capture-flat-roi") == "INSTRUMENT_INVALID"
        checks["missing_flat_has_invalid_state"] = invalid_output.get(
            "detail_state_by_capture", {}
        ).get("capture-missing-flat") == "INSTRUMENT_INVALID"
        checks["invalid_states_have_no_boolean"] = set(
            invalid_output.get("detail_pass_by_capture", {})
        ) == {"capture-pass"}

        not_applicable_request = {
            "schema": "m135-m138-evaluate-request/v1",
            "capture_ids": ["capture-not-applicable"],
            "artifacts": [refs["not-applicable"]],
            "binding_hashes": binding_hashes,
            "comparisons": [
                {
                    "capture_id": "capture-not-applicable",
                    "payload": refs["not-applicable"],
                }
            ],
        }
        not_applicable_path = evidence / "not-applicable-evaluate.json"
        write_json(not_applicable_path, not_applicable_request)
        not_applicable_run = invoke_self_test_adapter(
            runtime, "evaluate", not_applicable_path
        )
        not_applicable_output = parsed_stdout(not_applicable_run)
        checks["not_applicable_is_invalid_without_boolean"] = bool(
            not_applicable_run.returncode == 0
            and not_applicable_output.get("detail_state_by_capture")
            == {"capture-not-applicable": "INSTRUMENT_INVALID"}
            and not_applicable_output.get("detail_pass_by_capture") == {}
        )

        mutated = ("0" if refs["null"]["sha256"][0] != "0" else "1") + refs[
            "null"
        ]["sha256"][1:]
        commission_request = {
            "schema": "m135-m138-commission-request/v1",
            "artifacts": [
                refs["null"],
                refs["blur"],
                refs["improvement"],
                refs["missing-flat"],
            ],
            "binding_hashes": binding_hashes,
            "controls": {
                "physical_null": {"payload": refs["null"]},
                "pre_noise_blur": {"payload": refs["blur"]},
                "pre_noise_optical_improvement": {
                    "payload": refs["improvement"]
                },
                "missing_flat_control": {"payload": refs["missing-flat"]},
                "hash_mutation": {
                    "artifact": refs["null"],
                    "mutated_sha256": mutated,
                },
            },
        }
        commission_path = evidence / "commission.json"
        write_json(commission_path, commission_request)
        commission_run = invoke_self_test_adapter(
            runtime, "commission", commission_path
        )
        commission_repeat = invoke_self_test_adapter(
            runtime, "commission", commission_path
        )
        commission_output = parsed_stdout(commission_run)
        checks["commission_exit_zero"] = commission_run.returncode == 0
        for control in (
            "physical_null_stays_null",
            "pre_noise_blur_lowers_information",
            "pre_noise_optical_improvement_raises_information",
            "missing_flat_control_refuses",
            "artifact_hash_mutation_refuses",
        ):
            checks[f"commission_{control}"] = (
                commission_output.get("controls", {}).get(control) is True
            )
        checks["commission_output_byte_stable"] = (
            commission_repeat.returncode == 0
            and commission_repeat.stdout == commission_run.stdout
            and commission_repeat.stderr == commission_run.stderr
        )

        all_negative_request = {
            "schema": "m135-m138-commission-request/v1",
            "artifacts": [refs["fail"], refs["pass"]],
            "binding_hashes": binding_hashes,
            "controls": {
                "physical_null": {"payload": refs["fail"]},
                "pre_noise_blur": {"payload": refs["pass"]},
                "pre_noise_optical_improvement": {"payload": refs["fail"]},
                "missing_flat_control": {"payload": refs["pass"]},
                "hash_mutation": {
                    "artifact": refs["pass"],
                    "mutated_sha256": refs["pass"]["sha256"],
                },
            },
        }
        all_negative_path = evidence / "commission-all-negative.json"
        write_json(all_negative_path, all_negative_request)
        all_negative_run = invoke_self_test_adapter(
            runtime, "commission", all_negative_path
        )
        all_negative_output = parsed_stdout(all_negative_run)
        checks["commission_all_negative_controls_reachable"] = bool(
            all_negative_run.returncode == 0
            and all_negative_output.get("controls")
            == {
                "physical_null_stays_null": False,
                "pre_noise_blur_lowers_information": False,
                "pre_noise_optical_improvement_raises_information": False,
                "missing_flat_control_refuses": False,
                "artifact_hash_mutation_refuses": False,
            }
        )

        threshold_request = copy.deepcopy(commission_request)
        threshold_request["artifacts"] = [
            refs["null"],
            refs["blur-threshold"],
            refs["improvement-threshold"],
            refs["missing-flat"],
        ]
        threshold_request["controls"]["pre_noise_blur"] = {
            "payload": refs["blur-threshold"]
        }
        threshold_request["controls"]["pre_noise_optical_improvement"] = {
            "payload": refs["improvement-threshold"]
        }
        threshold_path = evidence / "commission-threshold-discrimination.json"
        write_json(threshold_path, threshold_request)
        threshold_run = invoke_self_test_adapter(
            runtime, "commission", threshold_path
        )
        threshold_output = parsed_stdout(threshold_run)
        checks["commission_blur_threshold_rejects_marginal_control"] = bool(
            threshold_run.returncode == 0
            and threshold_output.get("controls", {}).get(
                "pre_noise_blur_lowers_information"
            )
            is False
        )
        checks[
            "commission_improvement_threshold_rejects_marginal_control"
        ] = bool(
            threshold_run.returncode == 0
            and threshold_output.get("controls", {}).get(
                "pre_noise_optical_improvement_raises_information"
            )
            is False
        )

        bad_hash_request = copy.deepcopy(valid_request)
        wrong_hash = (
            ("0" if refs["pass"]["sha256"][0] != "0" else "1")
            + refs["pass"]["sha256"][1:]
        )
        bad_hash_request["artifacts"][0]["sha256"] = wrong_hash
        bad_hash_request["comparisons"][0]["payload"]["sha256"] = wrong_hash
        bad_hash_path = evidence / "bad-hash-evaluate.json"
        write_json(bad_hash_path, bad_hash_request)
        bad_hash_run = invoke_self_test_adapter(runtime, "evaluate", bad_hash_path)
        bad_hash_error = parsed_stderr(bad_hash_run)
        checks["bad_artifact_hash_exits_nonzero"] = bad_hash_run.returncode != 0
        checks["bad_artifact_hash_has_no_stdout"] = bad_hash_run.stdout == b""
        checks["bad_artifact_hash_is_machine_readable"] = (
            bad_hash_error.get("status") == "INSTRUMENT_INVALID"
            and "SHA-256 mismatch" in str(bad_hash_error.get("reason"))
        )

        supplied_request = copy.deepcopy(valid_request)
        supplied_request["detail_pass_by_capture"] = {"capture-pass": True}
        supplied_path = evidence / "supplied-decision-evaluate.json"
        write_json(supplied_path, supplied_request)
        supplied_run = invoke_self_test_adapter(runtime, "evaluate", supplied_path)
        checks["supplied_boolean_refuses"] = bool(
            supplied_run.returncode != 0
            and supplied_run.stdout == b""
            and parsed_stderr(supplied_run).get("status") == "INSTRUMENT_INVALID"
        )

        duplicate_request = copy.deepcopy(valid_request)
        duplicate_request["capture_ids"] = ["capture-pass", "capture-pass"]
        duplicate_request["comparisons"][1]["capture_id"] = "capture-pass"
        duplicate_request["comparisons"][1]["payload"] = refs["pass"]
        duplicate_path = evidence / "duplicate-capture-evaluate.json"
        write_json(duplicate_path, duplicate_request)
        duplicate_run = invoke_self_test_adapter(
            runtime, "evaluate", duplicate_path
        )
        checks["duplicate_capture_refuses"] = bool(
            duplicate_run.returncode != 0
            and duplicate_run.stdout == b""
            and parsed_stderr(duplicate_run).get("status") == "INSTRUMENT_INVALID"
        )

        tampered_runtime = copy_self_test_runtime(
            scratch, bound, name="bundle-tamper-runtime"
        )
        tampered_member = tampered_runtime / "M138-ADAPTER-AMENDMENT-9.md"
        tampered_member.write_bytes(
            tampered_member.read_bytes() + b"\nM138 bundle mutation probe\n"
        )
        tampered_bundle_run = invoke_self_test_description(tampered_runtime)
        tampered_bundle_error = (
            parsed_stderr(tampered_bundle_run)
            if tampered_bundle_run.stderr
            else {}
        )
        checks["bundle_member_hash_refuses"] = bool(
            tampered_bundle_run.returncode != 0
            and tampered_bundle_run.stdout == b""
            and tampered_bundle_error.get("status") == "INSTRUMENT_INVALID"
            and "SHA-256 mismatch"
            in str(tampered_bundle_error.get("reason"))
        )

        unbound = copy.deepcopy(runtime_state.binding)
        write_json(runtime / CORE_BINDING_PATH.name, unbound)
        write_bundle_manifest(runtime)
        unbound_request = copy.deepcopy(valid_request)
        unbound_request["binding_hashes"] = self_test_binding_hashes(
            runtime, unbound
        )
        unbound_path = evidence / "unbound-evaluate.json"
        write_json(unbound_path, unbound_request)
        unbound_run = invoke_self_test_adapter(runtime, "evaluate", unbound_path)
        unbound_error = parsed_stderr(unbound_run)
        checks["unbound_exits_nonzero"] = unbound_run.returncode != 0
        checks["unbound_has_no_stdout"] = unbound_run.stdout == b""
        checks["unbound_status_is_explicit"] = (
            unbound_error.get("status") == "INSTRUMENT_UNBOUND"
        )
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)

    passed = sum(1 for value in checks.values() if value)
    return {
        "schema": "m135-m138-adapter-self-test-v1",
        "rule_id": "m135-m138-adapter-v1",
        "adapter_sha256": runtime_state.checker_sha256,
        "adapter_contract_canonical_sha256": EXPECTED_ADAPTER_CONTRACT_SHA256,
        "status": "PASS" if passed == len(checks) else "FAIL",
        "check_count": len(checks),
        "passed_check_count": passed,
        "checks": checks,
        "scope": "synthetic interface commissioning only; physical binding remains UNBOUND",
    }


def describe(runtime: Runtime) -> dict[str, Any]:
    return {
        "schema": "m135-m138-adapter-description-v1",
        "rule_id": runtime.adapter_contract["rule_id"],
        "interface_schema": runtime.adapter_contract["interface_schema"],
        "binding_state": runtime.binding_state,
        "checker_sha256": runtime.checker_sha256,
        "checker_bundle_manifest_sha256": runtime.bundle_sha256,
        "environment_manifest_sha256": runtime.environment_sha256,
        "comparison_rule_sha256": runtime.comparison_rule_sha256,
        "adapter_contract_canonical_sha256": EXPECTED_ADAPTER_CONTRACT_SHA256,
    }


def refusal_object(
    error: AdapterRefusal, request_sha256: str | None
) -> dict[str, Any]:
    return {
        "schema": "m135-m138-refusal/v1",
        "status": error.status,
        "reason": error.reason,
        "request_sha256": request_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--m138-evaluate", type=Path, metavar="REQUEST")
    mode.add_argument("--m138-commission", type=Path, metavar="REQUEST")
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--describe", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    request_path = args.m138_evaluate or args.m138_commission
    request_snapshot: FileSnapshot | None = None
    try:
        if sys.flags.isolated != 1:
            raise AdapterRefusal(
                "INSTRUMENT_INVALID", "checker must be invoked through python -I"
            )
        if args.self_test:
            runtime = load_runtime()
            result = run_self_test(runtime)
            emit_json(result, args.output)
            return 0 if result["status"] == "PASS" else 1
        runtime = load_runtime()
        if args.describe:
            emit_json(describe(runtime), args.output)
            return 0
        assert request_path is not None
        request_path = request_path.resolve()
        request_snapshot = read_file_once(request_path, "M138 request")
        request = snapshot_json_object(request_snapshot, "M138 request")
        if args.m138_evaluate is not None:
            result = process_evaluate(
                request_path, request_snapshot.sha256, request, runtime
            )
        else:
            result = process_commission(
                request_path, request_snapshot.sha256, request, runtime
            )
        emit_json(result, args.output)
        return 0
    except AdapterRefusal as error:
        request_sha256 = (
            request_snapshot.sha256 if request_snapshot is not None else None
        )
        sys.stderr.buffer.write(
            canonical_json_line(refusal_object(error, request_sha256))
        )
        sys.stderr.buffer.flush()
        return REQUEST_REFUSAL_EXIT_CODE
    except Exception as error:
        wrapped = AdapterRefusal(
            "INSTRUMENT_INVALID",
            f"unexpected adapter failure: {type(error).__name__}: {error}",
        )
        sys.stderr.buffer.write(
            canonical_json_line(
                refusal_object(
                    wrapped,
                    request_snapshot.sha256
                    if request_snapshot is not None
                    else None,
                )
            )
        )
        sys.stderr.buffer.flush()
        return UNEXPECTED_ERROR_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
