#!/usr/bin/env python3
"""Deterministic per-capture consumer checker for the M135 certificate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / "comparison-contract.json"
BINDING_PATH = HERE / "comparison-binding.json"
INSTRUMENT_PATH = HERE / "instrument.py"
EXPECTED_CONTRACT_SHA256 = (
    "247abd2024307aa43e7ab62edd7da23b8042ca98dedf6ca1a8eaac2d1510c249"
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")


class InvalidInstrument(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise InvalidInstrument(f"{path.name} must contain a JSON object")
    return value


def canonical_json_sha256(value: dict[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def exact_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_contract(contract: dict[str, Any]) -> None:
    if canonical_json_sha256(contract) != EXPECTED_CONTRACT_SHA256:
        raise InvalidInstrument("comparison contract hash drift")
    if contract.get("schema") != "m135-detail-comparison-contract-v1":
        raise InvalidInstrument("unsupported comparison contract schema")
    if contract.get("rule_id") != "m135-detail-pass-v1":
        raise InvalidInstrument("comparison rule identifier changed")
    if contract.get("status") != "PHYSICAL_UNBOUND":
        raise InvalidInstrument("comparison contract status changed")
    scope = contract.get("scope", {})
    if scope.get("decision_unit") != "one registered capture":
        raise InvalidInstrument("decision unit changed")
    if scope.get("cross_capture_averaging") is not False:
        raise InvalidInstrument("cross-capture averaging was enabled")
    if int(scope.get("minimum_sites", -1)) != 64:
        raise InvalidInstrument("minimum site count changed")
    bootstrap = contract.get("bootstrap", {})
    expected_bootstrap = {
        "replicates": 10000,
        "seed": 20260902,
        "paired_site_resampling": True,
        "capture_count": 1,
        "lower_quantile": 0.05,
        "upper_quantile": 0.95,
        "quantile_method": "linear",
    }
    if bootstrap != expected_bootstrap:
        raise InvalidInstrument("bootstrap contract changed")
    gates = contract.get("hard_gates", {})
    if gates != {
        "minimum_information_ratio_lower95": 0.98,
        "minimum_transfer_ratio_lower95_per_cell": 0.98,
        "maximum_unexplained_fraction_difference_upper95": 0.02,
    }:
        raise InvalidInstrument("hard comparison gates changed")
    if normalized_text_sha256(INSTRUMENT_PATH) != contract.get(
        "current_estimator_normalized_sha256"
    ):
        raise InvalidInstrument("bound estimator source hash drift")


def decision(
    contract: dict[str, Any],
    status: str,
    capture_id: str | None,
    *,
    reason: str | None = None,
    gates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    values = contract["detail_pass_values"]
    output = {
        "schema": "m135-detail-comparison-decision-v1",
        "rule_id": contract["rule_id"],
        "contract_sha256": EXPECTED_CONTRACT_SHA256,
        "checker_sha256": sha256(Path(__file__)),
        "capture_id": capture_id,
        "status": status,
        "detail_pass": values[status],
    }
    if reason is not None:
        output["reason"] = reason
    if gates is not None:
        output["gates"] = gates
    return output


def validate_binding_structure(
    binding: dict[str, Any], contract: dict[str, Any]
) -> str | None:
    if binding.get("schema") != "m135-detail-binding-v1":
        raise InvalidInstrument("unsupported binding schema")
    state = binding.get("state")
    if state == "UNBOUND":
        return state
    if state != "PHYSICAL_BOUND":
        raise InvalidInstrument("binding state is neither UNBOUND nor PHYSICAL_BOUND")
    if binding.get("physical_commissioning_status") != "PASS":
        raise InvalidInstrument("physical commissioning is not PASS")
    for field in contract["required_binding_hashes"]:
        if not valid_sha256(binding.get(field)):
            raise InvalidInstrument(f"binding lacks valid {field}")
    if binding["instrument_normalized_sha256"] != contract[
        "current_estimator_normalized_sha256"
    ]:
        raise InvalidInstrument("binding identifies a different estimator")
    captures = binding.get("applicable_captures")
    if not isinstance(captures, dict) or not captures:
        raise InvalidInstrument("physical binding has no applicable captures")
    for capture_id, row in captures.items():
        if not isinstance(capture_id, str) or not capture_id:
            raise InvalidInstrument("binding contains an invalid capture ID")
        if not isinstance(row, dict):
            raise InvalidInstrument(f"capture binding {capture_id} is not an object")
        site_count = row.get("site_count")
        if not exact_int(site_count) or site_count < int(
            contract["scope"]["minimum_sites"]
        ):
            raise InvalidInstrument(f"capture binding {capture_id} has too few sites")
        for field in contract["required_capture_hashes"]:
            if not valid_sha256(row.get(field)):
                raise InvalidInstrument(f"capture binding {capture_id} lacks {field}")
    return state


def validate_lineage(
    payload: dict[str, Any],
    binding: dict[str, Any],
    capture_id: str,
    contract: dict[str, Any],
) -> None:
    lineage = payload.get("lineage")
    if not isinstance(lineage, dict):
        raise InvalidInstrument("payload lacks lineage")
    for field in contract["required_binding_hashes"]:
        if lineage.get(field) != binding.get(field):
            raise InvalidInstrument(f"payload binding mismatch: {field}")
    expected_capture = binding["applicable_captures"][capture_id]
    for field in contract["required_capture_hashes"]:
        if lineage.get(field) != expected_capture.get(field):
            raise InvalidInstrument(f"payload capture mismatch: {field}")
    site_count = payload.get("site_count")
    if not exact_int(site_count) or site_count != expected_capture["site_count"]:
        raise InvalidInstrument("payload site count differs from bound capture")


def finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def validate_mode(
    mode: Any, label: str, contract: dict[str, Any]
) -> dict[str, float]:
    if not isinstance(mode, dict):
        raise InvalidInstrument(f"{label} mode record is missing")
    if mode.get("status") != contract["required_mode_status"]:
        raise InvalidInstrument(f"{label} mode is not eligible")
    information = mode.get("information_bits_per_site")
    if not finite_number(information) or float(information) < 0.10:
        raise InvalidInstrument(f"{label} information score is invalid")
    flat = mode.get("flat_control")
    if not isinstance(flat, dict):
        raise InvalidInstrument(f"{label} flat control is missing")
    if flat.get("status") != contract["flat_control"]["required_status"]:
        raise InvalidInstrument(f"{label} flat control does not report NO_DETAIL")
    fields = {
        "information_ratio": (
            "flat_to_detail_information_ratio",
            "maximum_information_ratio",
        ),
        "reference_repeatable_power_ratio": (
            "flat_to_detail_reference_repeatable_power_ratio",
            "maximum_reference_repeatable_power_ratio",
        ),
        "output_repeatable_power_ratio": (
            "flat_to_detail_output_repeatable_power_ratio",
            "maximum_output_repeatable_power_ratio",
        ),
    }
    values: dict[str, float] = {}
    for output_name, (payload_name, bar_name) in fields.items():
        value = flat.get(payload_name)
        if not finite_number(value) or float(value) < 0.0:
            raise InvalidInstrument(f"{label} flat {output_name} is invalid")
        numeric = float(value)
        values[output_name] = numeric
        if numeric > float(contract["flat_control"][bar_name]):
            raise InvalidInstrument(f"{label} flat {output_name} exceeds its bar")
    return values


def numeric_vector(value: Any, length: int, label: str) -> np.ndarray:
    if (
        not isinstance(value, list)
        or len(value) != length
        or any(not finite_number(item) for item in value)
    ):
        raise InvalidInstrument(f"{label} must contain {length} JSON numbers")
    array = np.asarray(value, dtype=float)
    return array


def validate_bootstrap(
    payload: dict[str, Any], contract: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    bootstrap = payload.get("bootstrap")
    if not isinstance(bootstrap, dict):
        raise InvalidInstrument("bootstrap record is missing")
    frozen = contract["bootstrap"]
    for field in ("replicates", "seed", "capture_count"):
        value = bootstrap.get(field)
        if not exact_int(value) or value != frozen[field]:
            raise InvalidInstrument(f"bootstrap {field} differs from the rule")
    if bootstrap.get("paired_site_resampling") is not True:
        raise InvalidInstrument("bootstrap paired_site_resampling differs from the rule")
    replicates = int(frozen["replicates"])
    information = numeric_vector(
        bootstrap.get("information_ratio"),
        replicates,
        "information_ratio",
    )
    unexplained = numeric_vector(
        bootstrap.get("unexplained_fraction_difference"),
        replicates,
        "unexplained_fraction_difference",
    )
    transfer_value = bootstrap.get("transfer_ratio_by_cell")
    cells = len(contract["scope"]["frequencies_cyc_per_native_px"])
    if (
        not isinstance(transfer_value, list)
        or len(transfer_value) != cells
        or any(
            not isinstance(row, list)
            or len(row) != replicates
            or any(not finite_number(item) for item in row)
            for row in transfer_value
        )
    ):
        raise InvalidInstrument(
            f"transfer_ratio_by_cell must contain ({cells}, {replicates}) JSON numbers"
        )
    transfer = np.asarray(transfer_value, dtype=float)
    if np.any(information <= 0.0) or np.any(transfer <= 0.0):
        raise InvalidInstrument("information and transfer ratios must be positive")
    if np.any(unexplained < -1.0) or np.any(unexplained > 1.0):
        raise InvalidInstrument("unexplained-fraction differences exceed [-1,1]")
    return information, transfer, unexplained


def adjudicate(
    payload: dict[str, Any],
    binding: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    capture_id = payload.get("capture_id")
    if not isinstance(capture_id, str) or not capture_id:
        capture_id = None
    try:
        validate_contract(contract)
        if payload.get("schema") != "m135-detail-comparison-payload-v1":
            raise InvalidInstrument("unsupported payload schema")
        if "detail_pass" in payload:
            raise InvalidInstrument("producer-supplied detail_pass is forbidden")
        if capture_id is None:
            raise InvalidInstrument("payload lacks a capture ID")
        state = validate_binding_structure(binding, contract)
        if state == "UNBOUND":
            return decision(
                contract,
                contract["decision_statuses"]["instrument_unbound"],
                capture_id,
                reason="physical M135 binding is UNBOUND",
            )
        if capture_id not in binding["applicable_captures"]:
            return decision(
                contract,
                contract["decision_statuses"]["not_applicable"],
                capture_id,
                reason="capture is absent from the frozen M135 detail ledger",
            )

        validate_lineage(payload, binding, capture_id, contract)
        if payload["site_count"] < int(contract["scope"]["minimum_sites"]):
            raise InvalidInstrument("payload has too few sites")
        if payload.get("frequencies_cyc_per_native_px") != contract["scope"].get(
            "frequencies_cyc_per_native_px"
        ):
            raise InvalidInstrument("registered frequencies differ from the rule")
        if payload.get("angles_deg") != contract["scope"].get("angles_deg"):
            raise InvalidInstrument("registered angles differ from the rule")

        modes = payload.get("modes")
        if not isinstance(modes, dict) or set(modes) != {"candidate", "legacy"}:
            raise InvalidInstrument("payload must contain candidate and legacy modes")
        candidate_flat = validate_mode(modes["candidate"], "candidate", contract)
        legacy_flat = validate_mode(modes["legacy"], "legacy", contract)
        information, transfer, unexplained = validate_bootstrap(payload, contract)

        method = str(contract["bootstrap"]["quantile_method"])
        lower_q = float(contract["bootstrap"]["lower_quantile"])
        upper_q = float(contract["bootstrap"]["upper_quantile"])
        information_lower = float(np.quantile(information, lower_q, method=method))
        transfer_lower = np.quantile(transfer, lower_q, axis=1, method=method)
        unexplained_upper = float(np.quantile(unexplained, upper_q, method=method))
        bars = contract["hard_gates"]
        gate_values = {
            "information_ratio_lower95": information_lower,
            "transfer_ratio_lower95_by_cell": transfer_lower.tolist(),
            "minimum_transfer_ratio_lower95": float(np.min(transfer_lower)),
            "unexplained_fraction_difference_upper95": unexplained_upper,
            "candidate_flat": candidate_flat,
            "legacy_flat": legacy_flat,
        }
        gate_passes = {
            "information_noninferiority": information_lower
            >= float(bars["minimum_information_ratio_lower95"]),
            "transfer_noninferiority_all_cells": bool(
                np.all(
                    transfer_lower
                    >= float(bars["minimum_transfer_ratio_lower95_per_cell"])
                )
            ),
            "unexplained_repeatability": unexplained_upper
            <= float(bars["maximum_unexplained_fraction_difference_upper95"]),
        }
        gate_values["passes"] = gate_passes
        status = (
            contract["decision_statuses"]["pass"]
            if all(gate_passes.values())
            else contract["decision_statuses"]["fail"]
        )
        return decision(contract, status, capture_id, gates=gate_values)
    except (InvalidInstrument, TypeError, ValueError) as error:
        return decision(
            contract,
            contract["decision_statuses"]["instrument_invalid"],
            capture_id,
            reason=str(error),
        )


def synthetic_binding(contract: dict[str, Any]) -> dict[str, Any]:
    common = {
        field: (index + 1) * "a"
        for index, field in enumerate(contract["required_binding_hashes"])
    }
    common["instrument_normalized_sha256"] = contract[
        "current_estimator_normalized_sha256"
    ]
    capture_hashes = {
        field: (index + 5) * "b"
        for index, field in enumerate(contract["required_capture_hashes"])
    }
    # Normalize the test-only repeated characters to valid 64-digit hashes.
    common = {key: (value[0] * 64) for key, value in common.items()}
    common["instrument_normalized_sha256"] = contract[
        "current_estimator_normalized_sha256"
    ]
    capture_hashes = {key: (value[0] * 64) for key, value in capture_hashes.items()}
    return {
        "schema": "m135-detail-binding-v1",
        "state": "PHYSICAL_BOUND",
        "physical_commissioning_status": "PASS",
        **common,
        "applicable_captures": {
            "capture-applicable": {
                "site_count": 64,
                **capture_hashes,
            }
        },
    }


def synthetic_payload(
    contract: dict[str, Any],
    binding: dict[str, Any],
    *,
    information: float = 1.0,
    transfer: float = 1.0,
    unexplained: float = 0.0,
) -> dict[str, Any]:
    capture_id = "capture-applicable"
    replicates = int(contract["bootstrap"]["replicates"])
    capture_binding = binding["applicable_captures"][capture_id]
    lineage = {
        field: binding[field] for field in contract["required_binding_hashes"]
    }
    lineage.update(
        {
            field: capture_binding[field]
            for field in contract["required_capture_hashes"]
        }
    )
    flat = {
        "status": "NO_DETAIL",
        "flat_to_detail_information_ratio": 0.0,
        "flat_to_detail_reference_repeatable_power_ratio": 0.01,
        "flat_to_detail_output_repeatable_power_ratio": 0.02,
    }
    return {
        "schema": "m135-detail-comparison-payload-v1",
        "capture_id": capture_id,
        "site_count": capture_binding["site_count"],
        "frequencies_cyc_per_native_px": contract["scope"][
            "frequencies_cyc_per_native_px"
        ],
        "angles_deg": contract["scope"]["angles_deg"],
        "lineage": lineage,
        "modes": {
            "candidate": {
                "status": "OK",
                "information_bits_per_site": 1.5 * information,
                "flat_control": copy.deepcopy(flat),
            },
            "legacy": {
                "status": "OK",
                "information_bits_per_site": 1.5,
                "flat_control": copy.deepcopy(flat),
            },
        },
        "bootstrap": {
            "replicates": replicates,
            "seed": contract["bootstrap"]["seed"],
            "paired_site_resampling": True,
            "capture_count": 1,
            "information_ratio": [information] * replicates,
            "transfer_ratio_by_cell": [
                [transfer] * replicates
                for _ in contract["scope"]["frequencies_cyc_per_native_px"]
            ],
            "unexplained_fraction_difference": [unexplained] * replicates,
        },
    }


def run_self_test(
    contract: dict[str, Any], unbound_binding: dict[str, Any]
) -> dict[str, Any]:
    bound = synthetic_binding(contract)
    baseline = synthetic_payload(contract, bound)
    checks: dict[str, bool] = {}

    checks["unbound_blocks"] = (
        adjudicate(baseline, unbound_binding, contract)["status"]
        == "INSTRUMENT_UNBOUND"
    )
    not_applicable = copy.deepcopy(baseline)
    not_applicable["capture_id"] = "capture-not-registered"
    checks["unregistered_capture_is_not_applicable"] = (
        adjudicate(not_applicable, bound, contract)["status"] == "NOT_APPLICABLE"
    )
    checks["exact_null_passes"] = (
        adjudicate(baseline, bound, contract)["status"] == "DETAIL_PASS"
    )
    improvement = synthetic_payload(
        contract, bound, information=1.20, transfer=1.10, unexplained=-0.05
    )
    checks["improvement_passes"] = (
        adjudicate(improvement, bound, contract)["status"] == "DETAIL_PASS"
    )
    checks["information_defect_fails"] = (
        adjudicate(
            synthetic_payload(contract, bound, information=0.70),
            bound,
            contract,
        )["status"]
        == "DETAIL_FAIL"
    )
    transfer_defect = synthetic_payload(contract, bound)
    transfer_defect["bootstrap"]["transfer_ratio_by_cell"][7] = [0.70] * int(
        contract["bootstrap"]["replicates"]
    )
    checks["one_cell_transfer_defect_fails"] = (
        adjudicate(transfer_defect, bound, contract)["status"] == "DETAIL_FAIL"
    )
    checks["unexplained_defect_fails"] = (
        adjudicate(
            synthetic_payload(contract, bound, unexplained=0.20),
            bound,
            contract,
        )["status"]
        == "DETAIL_FAIL"
    )

    candidate_flat = copy.deepcopy(baseline)
    candidate_flat["modes"]["candidate"]["flat_control"][
        "flat_to_detail_information_ratio"
    ] = 0.11
    checks["candidate_flat_failure_invalidates"] = (
        adjudicate(candidate_flat, bound, contract)["status"]
        == "INSTRUMENT_INVALID"
    )
    legacy_flat = copy.deepcopy(baseline)
    legacy_flat["modes"]["legacy"]["flat_control"][
        "flat_to_detail_output_repeatable_power_ratio"
    ] = 0.11
    checks["legacy_flat_failure_invalidates"] = (
        adjudicate(legacy_flat, bound, contract)["status"] == "INSTRUMENT_INVALID"
    )

    malformed_cases: dict[str, dict[str, Any]] = {}
    missing = copy.deepcopy(baseline)
    del missing["bootstrap"]
    malformed_cases["missing_bootstrap"] = missing
    short = copy.deepcopy(baseline)
    short["site_count"] = 63
    malformed_cases["short_capture"] = short
    nonfinite = copy.deepcopy(baseline)
    nonfinite["bootstrap"]["information_ratio"][0] = math.nan
    malformed_cases["nonfinite"] = nonfinite
    wrong_seed = copy.deepcopy(baseline)
    wrong_seed["bootstrap"]["seed"] += 1
    malformed_cases["wrong_seed"] = wrong_seed
    unpaired = copy.deepcopy(baseline)
    unpaired["bootstrap"]["paired_site_resampling"] = False
    malformed_cases["unpaired"] = unpaired
    wrong_frequency = copy.deepcopy(baseline)
    wrong_frequency["frequencies_cyc_per_native_px"][-1] = 0.26
    malformed_cases["wrong_frequency"] = wrong_frequency
    wrong_angle = copy.deepcopy(baseline)
    wrong_angle["angles_deg"][-1] = 90.0
    malformed_cases["wrong_angle"] = wrong_angle
    wrong_hash = copy.deepcopy(baseline)
    wrong_hash["lineage"]["site_manifest_sha256"] = "f" * 64
    malformed_cases["wrong_hash"] = wrong_hash
    supplied_boolean = copy.deepcopy(baseline)
    supplied_boolean["detail_pass"] = True
    malformed_cases["producer_boolean"] = supplied_boolean
    boolean_draw = copy.deepcopy(baseline)
    boolean_draw["bootstrap"]["information_ratio"][0] = True
    malformed_cases["boolean_draw"] = boolean_draw
    string_draw = copy.deepcopy(baseline)
    string_draw["bootstrap"]["information_ratio"][0] = "1.0"
    malformed_cases["numeric_string_draw"] = string_draw
    boolean_count = copy.deepcopy(baseline)
    boolean_count["bootstrap"]["capture_count"] = True
    malformed_cases["boolean_capture_count"] = boolean_count
    checks["malformed_payloads_invalidate"] = all(
        adjudicate(payload, bound, contract)["status"] == "INSTRUMENT_INVALID"
        for payload in malformed_cases.values()
    )

    info_boundary = synthetic_payload(contract, bound, information=0.98)
    transfer_boundary = synthetic_payload(contract, bound, transfer=0.98)
    unexplained_boundary = synthetic_payload(contract, bound, unexplained=0.02)
    checks["inclusive_boundaries_pass"] = all(
        adjudicate(payload, bound, contract)["status"] == "DETAIL_PASS"
        for payload in (info_boundary, transfer_boundary, unexplained_boundary)
    )
    info_below = synthetic_payload(
        contract,
        bound,
        information=float(np.nextafter(0.98, 0.0)),
    )
    transfer_below = synthetic_payload(
        contract,
        bound,
        transfer=float(np.nextafter(0.98, 0.0)),
    )
    unexplained_above = synthetic_payload(
        contract,
        bound,
        unexplained=float(np.nextafter(0.02, math.inf)),
    )
    checks["one_step_beyond_boundaries_fails"] = all(
        adjudicate(payload, bound, contract)["status"] == "DETAIL_FAIL"
        for payload in (info_below, transfer_below, unexplained_above)
    )

    sample = adjudicate(baseline, bound, contract)
    checks["decision_exposes_rule_hashes"] = bool(
        sample["contract_sha256"] == EXPECTED_CONTRACT_SHA256
        and valid_sha256(sample["checker_sha256"])
    )
    checks["nondecisions_never_emit_boolean"] = all(
        adjudicate(payload, binding, contract)["detail_pass"] is None
        for payload, binding in (
            (baseline, unbound_binding),
            (not_applicable, bound),
            (candidate_flat, bound),
        )
    )

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "sample_decisions": {
            "null": sample,
            "improvement": adjudicate(improvement, bound, contract),
            "information_defect": adjudicate(
                synthetic_payload(contract, bound, information=0.70),
                bound,
                contract,
            ),
            "not_applicable": adjudicate(not_applicable, bound, contract),
            "unbound": adjudicate(baseline, unbound_binding, contract),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--binding", type=Path, default=BINDING_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--describe", action="store_true")
    args = parser.parse_args()

    contract = load_json(CONTRACT_PATH)
    binding = load_json(args.binding)
    if args.describe:
        validate_contract(contract)
        output = {
            "rule_id": contract["rule_id"],
            "contract_sha256": EXPECTED_CONTRACT_SHA256,
            "checker_sha256": sha256(Path(__file__)),
            "binding_state": binding.get("state"),
            "decision_statuses": contract["decision_statuses"],
        }
    elif args.self_test:
        output = run_self_test(contract, binding)
    elif args.payload is not None:
        output = adjudicate(load_json(args.payload), binding, contract)
    else:
        parser.error("choose --describe, --self-test, or --payload")

    text = json.dumps(output, indent=2, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if output.get("status") == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
