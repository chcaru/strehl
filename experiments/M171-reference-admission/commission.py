"""Commission the frozen M171 admission gates with source-level mutations."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from typing import Any

import admission


_SEAL_SCHEMA = "m171-reference-admission-evidence-seal-v1"
_EMBEDDED_EVIDENCE_SCHEMA = "m171-reference-admission-embedded-evidence-v1"
_COMMISSION_SCHEMA = "m171-reference-admission-commission-v4"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_COMMON_MODE_REASON = "COMMON_MODE_FRACTION_EXCESS"
_GZIP_COMPRESSION_LEVEL = 9
HERE = pathlib.Path(__file__).resolve().parent
_PROTECTED_OUTPUT_RELATIVE_PATHS = (
    ".gitattributes",
    "PREREGISTRATION.md",
    "contract.json",
    "admission.py",
    "synthetic.py",
    "commission.py",
    "test_admission.py",
    "verify.py",
    "out/verification.json",
)


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
        raise admission.HarnessError(
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
        raise admission.HarnessError(
            "cannot resolve commission output identity"
        ) from exc
    candidate_key = _path_key(candidate_path)
    protected_key = _path_key(protected_path)
    candidate_exists = _stat_exists(
        candidate_path, "commission output path"
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
            raise admission.HarnessError(
                "cannot establish commission output filesystem identity"
            ) from exc
        return same_file or candidate_key == protected_key
    return candidate_key == protected_key


def _reject_d_drive(path: os.PathLike[str] | str, purpose: str) -> pathlib.Path:
    raw = os.fspath(path)
    drive, _ = os.path.splitdrive(_strip_windows_extended_prefix(raw))
    if drive.casefold() == "d:":
        raise admission.HarnessError(
            f"{purpose} must not use the prohibited drive"
        )
    try:
        resolved = pathlib.Path(raw).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise admission.HarnessError(f"cannot resolve {purpose}") from exc
    resolved_drive, _ = os.path.splitdrive(
        _strip_windows_extended_prefix(os.fspath(resolved))
    )
    if resolved_drive.casefold() == "d:":
        raise admission.HarnessError(
            f"{purpose} must not use the prohibited drive"
        )
    return resolved


def _safe_commission_output(
    output: os.PathLike[str] | str,
    contract_path: os.PathLike[str] | str,
) -> pathlib.Path:
    resolved = _reject_d_drive(output, "commission output path")
    contract = _reject_d_drive(contract_path, "contract path")
    protected = [
        (contract, "loaded contract"),
        *[
            (
                (HERE / relative).resolve(strict=False),
                relative,
            )
            for relative in _PROTECTED_OUTPUT_RELATIVE_PATHS
        ],
    ]
    for protected_path, label in protected:
        if _paths_identical(resolved, protected_path):
            raise admission.HarnessError(
                "commission output must not overwrite protected input "
                f"{label}"
            )
    return resolved


def _source_bytes(path: pathlib.Path, purpose: str) -> bytes:
    try:
        with path.open("rb") as stream:
            payload = stream.read()
    except OSError as exc:
        raise admission.HarnessError(f"cannot read {purpose}") from exc
    if payload.startswith(b"\xef\xbb\xbf"):
        raise admission.HarnessError(f"{purpose} must not contain a UTF-8 BOM")
    if b"\r" in payload:
        raise admission.HarnessError(
            f"{purpose} must use LF line endings without carriage returns"
        )
    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise admission.HarnessError(f"{purpose} must be UTF-8") from exc
    return payload


def _decode_source(payload: bytes) -> str:
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise admission.HarnessError(
            "synthetic source must be UTF-8"
        ) from exc


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _deterministic_gzip(payload: bytes) -> bytes:
    target = io.BytesIO()
    with gzip.GzipFile(
        filename="",
        mode="wb",
        compresslevel=_GZIP_COMPRESSION_LEVEL,
        fileobj=target,
        mtime=0,
    ) as stream:
        stream.write(payload)
    return target.getvalue()


def _embedded_evidence_record(
    case: str,
    evidence: admission._SealedJSON,
) -> dict[str, Any]:
    payload = evidence.sealed_bytes
    digest = evidence.sealed_sha256
    if type(payload) is not bytes or _sha256(payload) != digest:
        raise admission.HarnessError(
            f"retained sealed evidence bytes drifted for {case}"
        )
    evidence_schema = evidence.get("schema")
    claim_scope = evidence.get("claim_scope")
    if not isinstance(evidence_schema, str) or not isinstance(
        claim_scope, str
    ):
        raise admission.HarnessError(
            f"sealed evidence identity is malformed for {case}"
        )
    compressed = _deterministic_gzip(payload)
    return {
        "schema": _EMBEDDED_EVIDENCE_SCHEMA,
        "encoding": "base64",
        "compression": "gzip",
        "compression_level": _GZIP_COMPRESSION_LEVEL,
        "gzip_mtime": 0,
        "identity": {
            "case": case,
            "evidence_schema": evidence_schema,
            "claim_scope": claim_scope,
        },
        "uncompressed_length_bytes": len(payload),
        "uncompressed_sha256": digest,
        "compressed_length_bytes": len(compressed),
        "compressed_sha256": _sha256(compressed),
        "payload": base64.b64encode(compressed).decode("ascii"),
    }


def _load_evaluate_and_embed(
    *,
    evidence_path: pathlib.Path,
    expected_sha256: str,
    contract: Mapping[str, Any],
    case: str,
    production_digital_k_probe: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    """Load once, evaluate that object, and embed its exact retained bytes."""

    evidence = admission.load_sealed_json(evidence_path, expected_sha256)
    result = admission.evaluate_evidence(
        evidence,
        contract,
        profile="synthetic_commission",
    )
    policy_probe = None
    if production_digital_k_probe:
        if case != "baseline":
            raise admission.HarnessError(
                "production DIGITAL_K probe must derive from baseline"
            )
        # Keep the once-read sealed baseline alive and change only the claim
        # scope in memory.  No evidence path is reopened for this policy probe.
        policy_evidence = dict(evidence)
        policy_evidence["claim_scope"] = "DIGITAL_K"
        policy_probe = admission.evaluate_evidence(
            policy_evidence,
            contract,
            profile="production",
        )
    if evidence.sealed_sha256 != expected_sha256.upper():
        raise admission.HarnessError(
            f"loaded evidence digest drifted for {case}"
        )
    result["evidence_sha256"] = evidence.sealed_sha256
    return result, _embedded_evidence_record(case, evidence), policy_probe


def _normalized_line(line: str) -> str:
    return line.strip(" \t\r\n")


def _anchor_count(source: str, anchor: str) -> int:
    return sum(
        _normalized_line(line) == anchor for line in source.splitlines()
    )


def _validate_anchor_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise admission.HarnessError(f"{path} must be a nonempty string")
    if "\n" in value or "\r" in value or value != value.strip():
        raise admission.HarnessError(
            f"{path} must be one normalized complete line"
        )
    return value


def _replace_unique_full_line(
    source: str, anchor: str, replacement: str
) -> str:
    """Replace one normalized full line or raise a hard harness error."""

    anchor = _validate_anchor_text(anchor, "mutation anchor")
    replacement = _validate_anchor_text(replacement, "mutation replacement")
    lines = source.splitlines(keepends=True)
    matches = [
        index
        for index, line in enumerate(lines)
        if _normalized_line(line) == anchor
    ]
    if len(matches) != 1:
        raise admission.HarnessError(
            "mutation anchor must occur as one complete normalized line; "
            f"found {len(matches)} for {anchor!r}"
        )
    index = matches[0]
    original = lines[index]
    if original.endswith("\r\n"):
        ending = "\r\n"
        body = original[:-2]
    elif original.endswith("\n") or original.endswith("\r"):
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
        raise admission.HarnessError("mutation did not alter synthetic source")
    if _anchor_count(mutated, anchor) != 0:
        raise admission.HarnessError("mutation anchor remained after replacement")
    if _anchor_count(mutated, replacement) != 1:
        raise admission.HarnessError(
            "mutation replacement is not a unique complete normalized line"
        )
    return mutated


def _mutation_list(contract: Mapping[str, Any]) -> list[dict[str, str]]:
    raw = contract.get("mutations")
    if not isinstance(raw, list) or len(raw) != 8:
        raise admission.HarnessError(
            "frozen contract must contain exactly eight mutations"
        )
    required = {
        "case",
        "anchor",
        "replacement",
        "target_gate",
        "reason",
    }
    result: list[dict[str, str]] = []
    cases: set[str] = set()
    anchors: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping) or set(item) != required:
            raise admission.HarnessError(
                f"contract.mutations[{index}] has the wrong members"
            )
        parsed = {
            name: _validate_anchor_text(
                item[name], f"contract.mutations[{index}].{name}"
            )
            if name in ("anchor", "replacement")
            else str(item[name])
            for name in required
        }
        if not all(parsed.values()):
            raise admission.HarnessError(
                f"contract.mutations[{index}] contains an empty value"
            )
        if parsed["case"] in cases:
            raise admission.HarnessError("mutation case names must be unique")
        if parsed["anchor"] in anchors:
            raise admission.HarnessError("mutation anchors must be unique")
        cases.add(parsed["case"])
        anchors.add(parsed["anchor"])
        result.append(parsed)
    return result


def _without_anchor(source: str, anchor: str) -> str:
    return "".join(
        line
        for line in source.splitlines(keepends=True)
        if _normalized_line(line) != anchor
    )


def _with_duplicate_anchor(source: str, anchor: str) -> str:
    separator = "" if source.endswith(("\n", "\r")) else "\n"
    return f"{source}{separator}{anchor}\n"


def _expect_anchor_error(
    source: str, anchor: str, replacement: str, expected_count: int
) -> dict[str, Any]:
    observed_count = _anchor_count(source, anchor)
    try:
        _replace_unique_full_line(source, anchor, replacement)
    except admission.HarnessError as exc:
        caught = True
        error = str(exc)
    else:
        caught = False
        error = None
    passed = caught and observed_count == expected_count
    return {
        "status": "PASS" if passed else "FAIL",
        "hard_error": caught,
        "mapped_exit_code": 2 if caught else None,
        "observed_anchor_count": observed_count,
        "expected_anchor_count": expected_count,
        "error": error,
    }


def validate_mutations(
    source: str, contract: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Validate all anchors plus missing/duplicate hard-error canaries."""

    mutations = _mutation_list(contract)
    validations: list[dict[str, Any]] = []
    for mutation in mutations:
        count = _anchor_count(source, mutation["anchor"])
        if count != 1:
            raise admission.HarnessError(
                "mutation anchor must occur as one complete normalized line; "
                f"found {count} for {mutation['anchor']!r}"
            )
        mutated = _replace_unique_full_line(
            source, mutation["anchor"], mutation["replacement"]
        )
        validations.append(
            {
                "case": mutation["case"],
                "anchor": mutation["anchor"],
                "replacement": mutation["replacement"],
                "target_gate": mutation["target_gate"],
                "reason": mutation["reason"],
                "anchor_count": count,
                "mutation_applied": mutated != source,
                "mutated_source_sha256": _sha256(mutated.encode("utf-8")),
            }
        )

    canary_mutation = mutations[0]
    missing = _expect_anchor_error(
        _without_anchor(source, canary_mutation["anchor"]),
        canary_mutation["anchor"],
        canary_mutation["replacement"],
        0,
    )
    duplicate = _expect_anchor_error(
        _with_duplicate_anchor(source, canary_mutation["anchor"]),
        canary_mutation["anchor"],
        canary_mutation["replacement"],
        2,
    )
    canaries = {
        "missing_full_line_anchor": missing,
        "duplicate_full_line_anchor": duplicate,
    }
    if any(canary["status"] != "PASS" for canary in canaries.values()):
        raise admission.HarnessError("anchor hard-error canary failed")
    return validations, canaries


def _parse_generator_seal(stdout: str, case: str) -> dict[str, Any]:
    try:
        seal = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise admission.HarnessError(
            f"synthetic generator returned invalid seal JSON for {case}"
        ) from exc
    required = {
        "schema",
        "case",
        "contract_sha256",
        "evidence_sha256",
        "capture_reads",
    }
    if not isinstance(seal, dict) or set(seal) != required:
        raise admission.HarnessError(
            f"synthetic generator returned malformed seal for {case}"
        )
    if seal["schema"] != _SEAL_SCHEMA or seal["case"] != case:
        raise admission.HarnessError(
            f"synthetic generator returned the wrong seal identity for {case}"
        )
    if (
        seal["contract_sha256"].upper()
        != admission.FROZEN_CONTRACT_SHA256
    ):
        raise admission.HarnessError(
            f"synthetic generator used the wrong contract for {case}"
        )
    digest = seal["evidence_sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise admission.HarnessError(
            f"synthetic generator returned an invalid evidence SHA-256 for {case}"
        )
    if type(seal["capture_reads"]) is not int or seal["capture_reads"] != 0:
        raise admission.HarnessError(
            f"synthetic generator reported capture access for {case}"
        )
    seal["evidence_sha256"] = digest.upper()
    return seal


def _run_case(
    *,
    index: int,
    case: str,
    kind: str,
    source_payload: bytes,
    contract_path: pathlib.Path,
    contract: Mapping[str, Any],
    temporary_root: pathlib.Path,
    mutation: Mapping[str, str] | None = None,
    production_digital_k_probe: bool = False,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    case_directory = temporary_root / f"{index:02d}"
    script_path = case_directory / "synthetic.py"
    evidence_path = case_directory / "evidence.json"
    _reject_d_drive(script_path, "temporary generator path")
    _reject_d_drive(evidence_path, "temporary evidence path")
    try:
        case_directory.mkdir(parents=True, exist_ok=False)
        with script_path.open("wb") as stream:
            stream.write(source_payload)
    except OSError as exc:
        raise admission.HarnessError(
            f"cannot prepare temporary generator for {case}"
        ) from exc

    environment = dict(os.environ)
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            os.fspath(script_path),
            "--contract",
            os.fspath(contract_path),
            "--case",
            case,
            "--output",
            os.fspath(evidence_path),
        ],
        cwd=case_directory,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stdout.strip() or completed.stderr.strip()
        raise admission.HarnessError(
            f"synthetic generator failed for {case} with exit "
            f"{completed.returncode}: {detail}"
        )
    seal = _parse_generator_seal(completed.stdout.strip(), case)

    # This public load is the only read of the evidence file.  Evaluation and
    # retention both consume the same object and its exact immutable bytes.
    result, embedded_evidence, policy_probe = _load_evaluate_and_embed(
        evidence_path=evidence_path,
        expected_sha256=seal["evidence_sha256"],
        contract=contract,
        case=case,
        production_digital_k_probe=production_digital_k_probe,
    )
    if result.get("evidence_sha256") != seal["evidence_sha256"]:
        raise admission.HarnessError(
            f"evidence digest was not propagated for {case}"
        )
    statuses = [gate.get("status") for gate in result.get("gates", [])]
    if len(statuses) != 8 or any(
        status not in ("PASS", "UNMEASURED") for status in statuses
    ):
        raise admission.HarnessError(
            f"invalid scientific gate partition for {case}"
        )
    if (
        result["counts"]["PASS"] + result["counts"]["UNMEASURED"] != 8
        or result["counts"]["total"] != 8
    ):
        raise admission.HarnessError(
            f"incomplete scientific gate partition for {case}"
        )

    record: dict[str, Any] = {
        "case": case,
        "kind": kind,
        "generator_source_sha256": _sha256(source_payload),
        "evidence_sha256": seal["evidence_sha256"],
        "embedded_evidence": embedded_evidence,
        "capture_reads": seal["capture_reads"],
        "result_schema": result["schema"],
        "profile": result["profile"],
        "claim_scope": result["claim_scope"],
        "counts": result["counts"],
        "all_gates_pass": result["all_gates_pass"],
        "gates": result["gates"],
    }
    if mutation is not None:
        record["mutation"] = {
            "anchor": mutation["anchor"],
            "replacement": mutation["replacement"],
            "target_gate": mutation["target_gate"],
            "reason": mutation["reason"],
            "applied": True,
        }
    return record, policy_probe


def _gate(case_record: Mapping[str, Any], gate_id: str) -> Mapping[str, Any]:
    matches = [
        gate for gate in case_record["gates"] if gate.get("id") == gate_id
    ]
    if len(matches) != 1:
        raise admission.HarnessError(
            f"case {case_record['case']} does not contain one {gate_id} record"
        )
    return matches[0]


def _production_digital_k_probe_record(
    result: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> tuple[dict[str, Any], bool]:
    gates = result.get("gates")
    if not isinstance(gates, list) or len(gates) != 8:
        raise admission.HarnessError(
            "production DIGITAL_K probe does not contain eight gates"
        )
    definitions = {
        str(definition["id"]): definition
        for definition in contract["gate_definitions"]
    }
    expected_gate_order = list(definitions)
    if [gate.get("id") for gate in gates] != expected_gate_order:
        raise admission.HarnessError(
            "production DIGITAL_K probe gate order drifted"
        )
    manifest_reason = "PRODUCTION_CALIBRATION_MANIFEST_ABSENT"
    policy = contract["digital_k_policy"]
    policy_reason = str(policy["reason"])
    reasons_match = True
    semantics_match = True
    for gate in gates:
        gate_id = str(gate["id"])
        expected_reasons = [
            manifest_reason,
            str(definitions[gate_id]["production_missing_reason"]),
        ]
        if gate_id == "G8":
            expected_reasons.append(policy_reason)
        reasons = gate.get("reason_codes")
        reasons_match &= (
            reasons == expected_reasons
            and isinstance(reasons, list)
            and len(reasons) == len(set(reasons))
        )
        semantics_match &= (
            gate.get("status") == "UNMEASURED"
            and gate.get("evaluated") is True
            and gate.get("claim_value") is None
        )

    g8 = next(gate for gate in gates if gate["id"] == "G8")
    diagnostics = g8.get("diagnostics")
    digital_k_diagnostics = (
        diagnostics.get("digital_k_policy")
        if isinstance(diagnostics, Mapping)
        else None
    )
    diagnostics_match = isinstance(
        digital_k_diagnostics, Mapping
    ) and dict(digital_k_diagnostics) == {
        "status": str(policy["status"]),
        "reason": policy_reason,
        "q_payload_present": False,
        "q_matrix_alone_sufficient": False,
        "production_manifest_failure_additional_reason": manifest_reason,
    }
    counts_match = result.get("counts") == {
        "PASS": 0,
        "UNMEASURED": 8,
        "total": 8,
    }
    passed = (
        result.get("schema") == contract["schemas"]["result"]
        and result.get("profile") == "production"
        and result.get("claim_scope") == "DIGITAL_K"
        and result.get("all_gates_pass") is False
        and counts_match
        and reasons_match
        and semantics_match
        and diagnostics_match
    )
    record = {
        "source_case": "baseline",
        "evidence_origin": "BASELINE_IN_MEMORY_AFTER_SINGLE_READ",
        "calibration_manifest_present": False,
        "result_schema": result["schema"],
        "profile": result["profile"],
        "claim_scope": result["claim_scope"],
        "counts": dict(result["counts"]),
        "all_gates_pass": result["all_gates_pass"],
        "gates": [dict(gate) for gate in gates],
    }
    return record, passed


def _numeric(value: Any, path: str) -> float:
    if type(value) not in (int, float):
        raise admission.HarnessError(f"{path} is not numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise admission.HarnessError(f"{path} is not finite")
    return converted


def _compare_improvement(
    weak_case: Mapping[str, Any],
    improved_case: Mapping[str, Any],
) -> dict[str, Any]:
    weak_cells = _gate(weak_case, "G8")["diagnostics"]["cells"]
    improved_gate = _gate(improved_case, "G8")
    improved_cells = improved_gate["diagnostics"]["cells"]
    if set(weak_cells) != set(improved_cells):
        raise admission.HarnessError(
            "weak and improved G8 cell families differ"
        )
    comparisons: dict[str, Any] = {}
    every_margin_increased = True
    for cell_id in weak_cells:
        weak = weak_cells[cell_id]
        improved = improved_cells[cell_id]
        information_before = _numeric(
            weak.get("information_margin"),
            f"{weak_case['case']}.{cell_id}.information_margin",
        )
        information_after = _numeric(
            improved.get("information_margin"),
            f"{improved_case['case']}.{cell_id}.information_margin",
        )
        transfer_before = _numeric(
            weak.get("transfer_margin"),
            f"{weak_case['case']}.{cell_id}.transfer_margin",
        )
        transfer_after = _numeric(
            improved.get("transfer_margin"),
            f"{improved_case['case']}.{cell_id}.transfer_margin",
        )
        information_increased = information_after > information_before
        transfer_increased = transfer_after > transfer_before
        every_margin_increased &= information_increased and transfer_increased
        comparisons[cell_id] = {
            "information_margin_before": information_before,
            "information_margin_after": information_after,
            "information_margin_increased": information_increased,
            "transfer_margin_before": transfer_before,
            "transfer_margin_after": transfer_after,
            "transfer_margin_increased": transfer_increased,
        }
    passed = (
        every_margin_increased
        and improved_gate["status"] == "PASS"
        and bool(improved_case["all_gates_pass"])
    )
    return {
        "control_case": weak_case["case"],
        "every_information_and_transfer_margin_increased": (
            every_margin_increased
        ),
        "g8_pass": improved_gate["status"] == "PASS",
        "all_gates_pass": bool(improved_case["all_gates_pass"]),
        "cells": comparisons,
        "passed": passed,
    }


def _naive_uncharged_metrics(
    cell: Mapping[str, Any], path: str
) -> dict[str, float]:
    raw = cell["raw"]
    signal_r = [
        _numeric(value, f"{path}.raw.signal_R.eigenvalues")
        for value in raw["signal_R"]["eigenvalues"]
    ]
    noise_r = [
        _numeric(value, f"{path}.raw.noise_R.eigenvalues")
        for value in raw["noise_R"]["eigenvalues"]
    ]
    signal_s = [
        _numeric(value, f"{path}.raw.signal_S.eigenvalues")
        for value in raw["signal_S"]["eigenvalues"]
    ]
    noise_s = [
        _numeric(value, f"{path}.raw.noise_S.eigenvalues")
        for value in raw["noise_S"]["eigenvalues"]
    ]
    if not (
        len(signal_r)
        == len(noise_r)
        == len(signal_s)
        == len(noise_s)
        and signal_r
    ):
        raise admission.HarnessError(f"{path} has incompatible eigenvalues")
    if any(
        value <= 0.0
        for values in (signal_r, noise_r, signal_s, noise_s)
        for value in values
    ):
        raise admission.HarnessError(
            f"{path} has nonpositive naive uncharged inputs"
        )
    information_r = [
        0.5 * math.log2(1.0 + signal / noise)
        for signal, noise in zip(signal_r, noise_r)
    ]
    information_s = [
        0.5 * math.log2(1.0 + signal / noise)
        for signal, noise in zip(signal_s, noise_s)
    ]
    information_ratio = min(
        reference / scored
        for reference, scored in zip(information_r, information_s)
    )
    transfer_ratio = math.sqrt(
        min(
            reference / scored
            for reference, scored in zip(signal_r, signal_s)
        )
    )
    return {
        "reference_information": min(information_r),
        "information_ratio": information_ratio,
        "transfer_ratio": transfer_ratio,
    }


def _compare_common_mode(
    baseline_case: Mapping[str, Any],
    common_case: Mapping[str, Any],
) -> dict[str, Any]:
    baseline_cells = _gate(baseline_case, "G8")["diagnostics"]["cells"]
    common_gate = _gate(common_case, "G8")
    common_cells = common_gate["diagnostics"]["cells"]
    if set(baseline_cells) != set(common_cells):
        raise admission.HarnessError(
            "baseline and common-mode G8 cell families differ"
        )
    comparisons: dict[str, Any] = {}
    every_naive_metric_increased = True
    for cell_id in baseline_cells:
        before = _naive_uncharged_metrics(
            baseline_cells[cell_id], f"baseline.{cell_id}"
        )
        after = _naive_uncharged_metrics(
            common_cells[cell_id], f"common_mode.{cell_id}"
        )
        information_increased = (
            after["reference_information"]
            > before["reference_information"]
            and after["information_ratio"] > before["information_ratio"]
        )
        transfer_increased = (
            after["transfer_ratio"] > before["transfer_ratio"]
        )
        every_naive_metric_increased &= (
            information_increased and transfer_increased
        )
        comparisons[cell_id] = {
            "baseline": before,
            "common_mode": after,
            "reference_information_increased": information_increased,
            "transfer_increased": transfer_increased,
        }
    reason_present = _COMMON_MODE_REASON in common_gate["reason_codes"]
    passed = (
        every_naive_metric_increased
        and common_gate["status"] == "UNMEASURED"
        and reason_present
    )
    return {
        "every_naive_uncharged_information_and_transfer_metric_increased": (
            every_naive_metric_increased
        ),
        "g8_status": common_gate["status"],
        "required_reason": _COMMON_MODE_REASON,
        "required_reason_present": reason_present,
        "cells": comparisons,
        "passed": passed,
    }


def _mark_expectations(
    cases: list[dict[str, Any]],
    mutations: Sequence[Mapping[str, str]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_name = {case["case"]: case for case in cases}
    baseline = by_name["baseline"]
    baseline_met = bool(baseline["all_gates_pass"])
    baseline["expected"] = "ALL_PASS"
    baseline["expectation_met"] = baseline_met
    baseline["outcome"] = "GREEN" if baseline_met else "UNEXPECTED"

    for mutation in mutations:
        record = by_name[mutation["case"]]
        target = _gate(record, mutation["target_gate"])
        caught = (
            record["mutation"]["applied"]
            and target["status"] == "UNMEASURED"
            and mutation["reason"] in target["reason_codes"]
        )
        record["expected"] = {
            "gate": mutation["target_gate"],
            "status": "UNMEASURED",
            "reason": mutation["reason"],
        }
        record["expectation_met"] = caught
        record["outcome"] = "RED_CAUGHT" if caught else "RED_MISSED"

    weak = by_name["g8_inferior_direction"]
    improved = by_name["planted_improvement"]
    improvement = _compare_improvement(weak, improved)
    improved["expected"] = "ALL_PASS_AND_G8_MARGINS_INCREASE"
    improved["comparison"] = improvement
    improved["expectation_met"] = improvement["passed"]
    improved["outcome"] = (
        "GREEN" if improvement["passed"] else "UNEXPECTED"
    )

    common = by_name["common_mode_false_improvement"]
    common_mode = _compare_common_mode(baseline, common)
    common["expected"] = "G8_UNMEASURED_COMMON_MODE_BOUND"
    common["comparison"] = common_mode
    common["expectation_met"] = common_mode["passed"]
    common["outcome"] = (
        "RED_CAUGHT" if common_mode["passed"] else "RED_MISSED"
    )
    return improvement, common_mode


def _partition(
    cases: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> tuple[dict[str, int], dict[str, bool]]:
    statuses = [
        gate["status"] for case in cases for gate in case["gates"]
    ]
    partition = {
        "scientific_cases": len(cases),
        "gate_evaluations": len(statuses),
        "PASS": statuses.count("PASS"),
        "UNMEASURED": statuses.count("UNMEASURED"),
        "PASS_plus_UNMEASURED": (
            statuses.count("PASS") + statuses.count("UNMEASURED")
        ),
        "targeted_red_cases": sum(
            case.get("outcome") == "RED_CAUGHT" for case in cases
        ),
        "expected_green_cases": sum(
            case.get("outcome") == "GREEN" for case in cases
        ),
        "skipped": sum(status not in ("PASS", "UNMEASURED") for status in statuses),
        "capture_reads": sum(int(case["capture_reads"]) for case in cases),
    }
    expected = contract["campaign_counts"]
    checks = {
        "scientific_cases": (
            partition["scientific_cases"] == int(expected["scientific_cases"])
        ),
        "gate_evaluations": (
            partition["gate_evaluations"] == int(expected["gate_evaluations"])
        ),
        "complete_gate_partition": (
            partition["PASS_plus_UNMEASURED"]
            == int(expected["gate_evaluations"])
        ),
        "targeted_red_cases": (
            partition["targeted_red_cases"]
            == int(expected["targeted_red_cases"])
        ),
        "expected_green_cases": (
            partition["expected_green_cases"]
            == int(expected["expected_green_cases"])
        ),
        "zero_skipped": partition["skipped"] == 0,
        "zero_capture_reads": (
            partition["capture_reads"] == int(expected["capture_reads"])
        ),
        "all_case_expectations": all(
            bool(case.get("expectation_met")) for case in cases
        ),
    }
    return partition, checks


def _validation_report(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    source_before: bytes,
    source_after: bytes,
    validations: Sequence[Mapping[str, Any]],
    canaries: Mapping[str, Any],
) -> dict[str, Any]:
    unchanged = source_before == source_after
    if not unchanged:
        raise admission.HarnessError(
            "synthetic source changed during mutation validation"
        )
    return {
        "schema": contract["schemas"]["commission"],
        "mode": "VALIDATE_MUTATIONS_ONLY",
        "status": "MUTATIONS_VALIDATED",
        "mutations": [dict(value) for value in validations],
        "canaries": dict(canaries),
        "hashes": {
            "contract_sha256": contract_sha256,
            "source_line_ending_policy": "LF",
            "synthetic_source_before_sha256": _sha256(source_before),
            "synthetic_source_after_sha256": _sha256(source_after),
            "synthetic_source_unchanged": unchanged,
        },
    }


def commission(
    *,
    contract_path: pathlib.Path,
    source_path: pathlib.Path,
) -> dict[str, Any]:
    contract = admission.load_sealed_json(
        contract_path, admission.FROZEN_CONTRACT_SHA256
    )
    contract_sha256 = getattr(
        contract, "sealed_sha256", admission.FROZEN_CONTRACT_SHA256
    )
    source_paths = {
        "admission": _reject_d_drive(
            source_path.with_name("admission.py"),
            "admission source path",
        ),
        "commission": _reject_d_drive(
            pathlib.Path(__file__),
            "commission source path",
        ),
        "synthetic": _reject_d_drive(
            source_path,
            "synthetic source path",
        ),
    }
    source_before = {
        name: _source_bytes(path, f"{name} source")
        for name, path in source_paths.items()
    }
    source = _decode_source(source_before["synthetic"])
    validations, canaries = validate_mutations(source, contract)
    mutations = _mutation_list(contract)
    validation_by_case = {
        validation["case"]: validation for validation in validations
    }

    cases: list[dict[str, Any]] = []
    production_probe_result: dict[str, Any] | None = None
    with tempfile.TemporaryDirectory(
        prefix="m171-reference-admission-"
    ) as temporary:
        temporary_root = _reject_d_drive(
            temporary, "temporary evidence directory"
        )
        baseline_case, production_probe_result = _run_case(
            index=0,
            case="baseline",
            kind="baseline",
            source_payload=source_before["synthetic"],
            contract_path=contract_path,
            contract=contract,
            temporary_root=temporary_root,
            production_digital_k_probe=True,
        )
        cases.append(baseline_case)
        for index, mutation in enumerate(mutations, start=1):
            mutated_source = _replace_unique_full_line(
                source, mutation["anchor"], mutation["replacement"]
            )
            mutated_payload = mutated_source.encode("utf-8")
            if (
                _sha256(mutated_payload)
                != validation_by_case[mutation["case"]][
                    "mutated_source_sha256"
                ]
            ):
                raise admission.HarnessError(
                    f"mutation validation drifted for {mutation['case']}"
                )
            mutation_case, unexpected_probe = _run_case(
                index=index,
                case=mutation["case"],
                kind="source_mutation",
                source_payload=mutated_payload,
                contract_path=contract_path,
                contract=contract,
                temporary_root=temporary_root,
                mutation=mutation,
            )
            if unexpected_probe is not None:
                raise admission.HarnessError(
                    "mutation case unexpectedly emitted a policy probe"
                )
            cases.append(mutation_case)
        improvement_case, unexpected_probe = _run_case(
            index=9,
            case="planted_improvement",
            kind="planted_improvement",
            source_payload=source_before["synthetic"],
            contract_path=contract_path,
            contract=contract,
            temporary_root=temporary_root,
        )
        if unexpected_probe is not None:
            raise admission.HarnessError(
                "planted improvement unexpectedly emitted a policy probe"
            )
        cases.append(improvement_case)
        common_mode_case, unexpected_probe = _run_case(
            index=10,
            case="common_mode_false_improvement",
            kind="common_mode_false_improvement",
            source_payload=source_before["synthetic"],
            contract_path=contract_path,
            contract=contract,
            temporary_root=temporary_root,
        )
        if unexpected_probe is not None:
            raise admission.HarnessError(
                "common-mode case unexpectedly emitted a policy probe"
            )
        cases.append(common_mode_case)

    if production_probe_result is None:
        raise admission.HarnessError(
            "baseline did not emit the production DIGITAL_K policy probe"
        )
    policy_probe, production_digital_k_refusal = (
        _production_digital_k_probe_record(
            production_probe_result,
            contract,
        )
    )
    improvement, common_mode = _mark_expectations(cases, mutations)
    partition, checks = _partition(cases, contract)
    source_after = {
        name: _source_bytes(path, f"{name} source")
        for name, path in source_paths.items()
    }
    source_unchanged_by_name = {
        name: source_before[name] == source_after[name]
        for name in source_paths
    }
    source_unchanged = all(source_unchanged_by_name.values())
    if not source_unchanged:
        changed = sorted(
            name
            for name, unchanged in source_unchanged_by_name.items()
            if not unchanged
        )
        raise admission.HarnessError(
            "implementation source changed during commission: "
            + ", ".join(changed)
        )
    checks["source_unchanged"] = source_unchanged
    checks["production_digital_k_refusal"] = (
        production_digital_k_refusal
    )
    checks["missing_anchor_canary"] = (
        canaries["missing_full_line_anchor"]["status"] == "PASS"
    )
    checks["duplicate_anchor_canary"] = (
        canaries["duplicate_full_line_anchor"]["status"] == "PASS"
    )
    complete = all(checks.values())
    amendment = contract["amendment"]
    integrity_amendment = contract["integrity_amendment"]
    statistical_amendment = contract["statistical_amendment"]
    return {
        "schema": contract["schemas"]["commission"],
        "status": "COMMISSIONED" if complete else "NOT_COMMISSIONED",
        "invalidation_history": {
            "v1": {
                "status": "INVALIDATED",
                "amendment": 1,
                "commission_sha256": str(
                    amendment["invalidated_commission_sha256"]
                ),
                "verification_sha256": str(
                    amendment["invalidated_verification_sha256"]
                ),
            },
            "v2": {
                "status": "INVALIDATED",
                "amendment": 2,
                "commission_sha256": str(
                    integrity_amendment["invalidated_commission_sha256"]
                ),
                "verification_sha256": str(
                    integrity_amendment["invalidated_verification_sha256"]
                ),
            },
            "v3": {
                "status": "INVALIDATED",
                "amendment": 3,
                "commission_sha256": str(
                    statistical_amendment[
                        "invalidated_commission_sha256"
                    ]
                ),
                "verification_sha256": str(
                    statistical_amendment[
                        "invalidated_verification_sha256"
                    ]
                ),
            },
        },
        "cases": cases,
        "policy_probes": {
            "production_missing_manifest_digital_k": policy_probe,
        },
        "partitions": partition,
        "checks": checks,
        "comparisons": {
            "planted_improvement": improvement,
            "common_mode_false_improvement": common_mode,
        },
        "mutation_validation": validations,
        "hashes": {
            "contract_sha256": contract_sha256,
            "source_line_ending_policy": "LF",
            "admission_source_before_sha256": _sha256(
                source_before["admission"]
            ),
            "admission_source_after_sha256": _sha256(
                source_after["admission"]
            ),
            "admission_source_unchanged": source_unchanged_by_name[
                "admission"
            ],
            "commission_source_before_sha256": _sha256(
                source_before["commission"]
            ),
            "commission_source_after_sha256": _sha256(
                source_after["commission"]
            ),
            "commission_source_unchanged": source_unchanged_by_name[
                "commission"
            ],
            "synthetic_source_before_sha256": _sha256(
                source_before["synthetic"]
            ),
            "synthetic_source_after_sha256": _sha256(
                source_after["synthetic"]
            ),
            "synthetic_source_unchanged": source_unchanged_by_name[
                "synthetic"
            ],
            "evidence_sha256_by_case": {
                case["case"]: case["evidence_sha256"] for case in cases
            },
        },
        "canaries": canaries,
    }


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise admission.HarnessError(
            "commission result is not finite JSON"
        ) from exc
    return (rendered + "\n").encode("utf-8")


def _write_output(path: pathlib.Path, value: Mapping[str, Any]) -> None:
    payload = _json_bytes(value)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as stream:
            stream.write(payload)
    except OSError as exc:
        raise admission.HarnessError(
            "cannot write commission output"
        ) from exc


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output")
    parser.add_argument("--validate-mutations-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)
    source_path = pathlib.Path(__file__).resolve().with_name("synthetic.py")
    try:
        contract_path = _reject_d_drive(args.contract, "contract path")
        source_path = _reject_d_drive(source_path, "synthetic source path")
        output_path = (
            _safe_commission_output(args.output, contract_path)
            if args.output is not None
            else None
        )
        if args.validate_mutations_only:
            contract = admission.load_sealed_json(
                contract_path, admission.FROZEN_CONTRACT_SHA256
            )
            contract_sha256 = getattr(
                contract,
                "sealed_sha256",
                admission.FROZEN_CONTRACT_SHA256,
            )
            source_before = _source_bytes(source_path, "synthetic source")
            validations, canaries = validate_mutations(
                _decode_source(source_before), contract
            )
            source_after = _source_bytes(source_path, "synthetic source")
            result = _validation_report(
                contract=contract,
                contract_sha256=contract_sha256,
                source_before=source_before,
                source_after=source_after,
                validations=validations,
                canaries=canaries,
            )
        else:
            if output_path is None:
                raise admission.HarnessError(
                    "--output is required for a normal commission"
                )
            result = commission(
                contract_path=contract_path,
                source_path=source_path,
            )
        if output_path is None:
            sys.stdout.buffer.write(_json_bytes(result))
        else:
            _write_output(output_path, result)
    except admission.HarnessError as exc:
        failure = {
            "schema": _COMMISSION_SCHEMA,
            "status": "HARNESS_ERROR",
            "error": str(exc),
        }
        print(json.dumps(failure, sort_keys=True, allow_nan=False))
        return 2
    if args.validate_mutations_only:
        return 0
    return 0 if result["status"] == "COMMISSIONED" else 1


if __name__ == "__main__":
    sys.exit(main())
