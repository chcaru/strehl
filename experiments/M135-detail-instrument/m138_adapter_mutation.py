#!/usr/bin/env python3
"""Mutation-commission the M138 adapter's formerly uncovered predicates."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ADAPTER_PATH = HERE / "m138_adapter.py"


@dataclass(frozen=True)
class Mutation:
    mutation_id: str
    expected_failed_check: str
    old: str
    new: str


MUTATIONS = (
    Mutation(
        "nested-supplied-decision",
        "guard_nested_supplied_decision",
        "            if key in forbidden:\n",
        "            if False and key in forbidden:\n",
    ),
    Mutation(
        "environment-equality",
        "guard_environment_equality",
        (
            "def environment_matches(\n"
            "    manifest: dict[str, Any], expected: dict[str, Any]\n"
            ") -> bool:\n"
            "    return manifest == expected\n"
        ),
        (
            "def environment_matches(\n"
            "    manifest: dict[str, Any], expected: dict[str, Any]\n"
            ") -> bool:\n"
            "    return True\n"
        ),
    ),
    Mutation(
        "common-binding-hash",
        "guard_common_binding_hash",
        (
            "def common_binding_hash_matches(observed: str, expected: str) -> bool:\n"
            "    return observed == expected\n"
        ),
        (
            "def common_binding_hash_matches(observed: str, expected: str) -> bool:\n"
            "    return True\n"
        ),
    ),
    Mutation(
        "physical-binding-hash",
        "guard_physical_binding_hash",
        (
            "def physical_binding_hash_matches(observed: str, expected: str) -> bool:\n"
            "    return observed == expected\n"
        ),
        (
            "def physical_binding_hash_matches(observed: str, expected: str) -> bool:\n"
            "    return True\n"
        ),
    ),
    Mutation(
        "canonical-terminal-newline",
        "guard_canonical_terminal_newline",
        "    return canonical_json_bytes(value) + b\"\\n\"\n",
        "    return canonical_json_bytes(value) + b\"\"\n",
    ),
    Mutation(
        "commission-null-invalid-status",
        "guard_commission_null_invalid_status",
        (
            "def null_decision_requires_refusal(\n"
            "    status: Any, invalid_statuses: set[str]\n"
            ") -> bool:\n"
            "    return status in invalid_statuses\n"
        ),
        (
            "def null_decision_requires_refusal(\n"
            "    status: Any, invalid_statuses: set[str]\n"
            ") -> bool:\n"
            "    return False\n"
        ),
    ),
    Mutation(
        "commission-blur-invalid-status",
        "guard_commission_blur_invalid_status",
        (
            "def blur_decision_requires_refusal(\n"
            "    status: Any, invalid_statuses: set[str]\n"
            ") -> bool:\n"
            "    return status in invalid_statuses\n"
        ),
        (
            "def blur_decision_requires_refusal(\n"
            "    status: Any, invalid_statuses: set[str]\n"
            ") -> bool:\n"
            "    return False\n"
        ),
    ),
    Mutation(
        "commission-improvement-invalid-status",
        "guard_commission_improvement_invalid_status",
        (
            "def improvement_decision_requires_refusal(\n"
            "    status: Any, invalid_statuses: set[str]\n"
            ") -> bool:\n"
            "    return status in invalid_statuses\n"
        ),
        (
            "def improvement_decision_requires_refusal(\n"
            "    status: Any, invalid_statuses: set[str]\n"
            ") -> bool:\n"
            "    return False\n"
        ),
    ),
    Mutation(
        "commission-missing-not-applicable",
        "guard_commission_missing_not_applicable",
        (
            "def missing_decision_requires_refusal(status: Any) -> bool:\n"
            "    return status == \"NOT_APPLICABLE\"\n"
        ),
        (
            "def missing_decision_requires_refusal(status: Any) -> bool:\n"
            "    return False\n"
        ),
    ),
    Mutation(
        "commission-mutated-sha-format",
        "guard_commission_mutated_sha_format",
        (
            "def mutation_digest_is_invalid(value: Any) -> bool:\n"
            "    return not valid_sha256(value)\n"
        ),
        (
            "def mutation_digest_is_invalid(value: Any) -> bool:\n"
            "    return False\n"
        ),
    ),
    Mutation(
        "commission-output-set",
        "guard_commission_output_set",
        (
            "def commissioning_control_set_matches(\n"
            "    controls: dict[str, bool], expected: set[str]\n"
            ") -> bool:\n"
            "    return set(controls) == expected\n"
        ),
        (
            "def commissioning_control_set_matches(\n"
            "    controls: dict[str, bool], expected: set[str]\n"
            ") -> bool:\n"
            "    return True\n"
        ),
    ),
    Mutation(
        "commission-hash-requires-error",
        "guard_commission_hash_requires_error",
        (
            "def hash_mutation_control_passes(\n"
            "    error: AdapterRefusal | None,\n"
            "    first_snapshot: FileSnapshot,\n"
            "    second_snapshot: FileSnapshot,\n"
            ") -> bool:\n"
            "    return bool(\n"
            "        error is not None\n"
            "        and \"SHA-256 mismatch\" in error.reason\n"
            "        and first_snapshot == second_snapshot\n"
            "    )\n"
        ),
        (
            "def hash_mutation_control_passes(\n"
            "    error: AdapterRefusal | None,\n"
            "    first_snapshot: FileSnapshot,\n"
            "    second_snapshot: FileSnapshot,\n"
            ") -> bool:\n"
            "    return bool(\n"
            "        (error is None or \"SHA-256 mismatch\" in error.reason)\n"
            "        and first_snapshot == second_snapshot\n"
            "    )\n"
        ),
    ),
    Mutation(
        "commission-hash-requires-mismatch-reason",
        "guard_commission_hash_requires_mismatch_reason",
        "        and \"SHA-256 mismatch\" in error.reason\n",
        "        and True\n",
    ),
    Mutation(
        "commission-hash-requires-same-snapshot",
        "guard_commission_hash_requires_same_snapshot",
        "        and first_snapshot == second_snapshot\n",
        "        and True\n",
    ),
    Mutation(
        "commission-null-status",
        "guard_commission_null_status",
        (
            "        status == \"DETAIL_PASS\"\n"
            "        and q05 >= low\n"
        ),
        (
            "        True\n"
            "        and q05 >= low\n"
        ),
    ),
    Mutation(
        "commission-null-q05-lower",
        "guard_commission_null_q05_lower",
        "        and q05 >= low\n",
        "        and True\n",
    ),
    Mutation(
        "commission-null-q05-upper",
        "guard_commission_null_q05_upper",
        "        and q05 <= 1.0\n",
        "        and True\n",
    ),
    Mutation(
        "commission-null-q95-lower",
        "guard_commission_null_q95_lower",
        "        and q95 >= 1.0\n",
        "        and True\n",
    ),
    Mutation(
        "commission-null-q95-upper",
        "guard_commission_null_q95_upper",
        "        and q95 <= high\n",
        "        and True\n",
    ),
    Mutation(
        "commission-blur-status",
        "guard_commission_blur_status",
        (
            "def blur_control_passes(status: Any, q95: float, bar: float) -> bool:\n"
            "    return bool(status == \"DETAIL_FAIL\" and q95 < bar)\n"
        ),
        (
            "def blur_control_passes(status: Any, q95: float, bar: float) -> bool:\n"
            "    return bool(True and q95 < bar)\n"
        ),
    ),
    Mutation(
        "commission-blur-q95",
        "guard_commission_blur_q95",
        "    return bool(status == \"DETAIL_FAIL\" and q95 < bar)\n",
        "    return bool(status == \"DETAIL_FAIL\" and True)\n",
    ),
    Mutation(
        "commission-blur-contract-threshold",
        "guard_commission_blur_contract_threshold",
        '        config["pre_noise_blur_information_ratio_q95_strictly_below"]\n',
        (
            '        config[\n'
            '            "pre_noise_optical_improvement_information_ratio_q05_strictly_above"\n'
            '        ]\n'
        ),
    ),
    Mutation(
        "commission-improvement-status",
        "guard_commission_improvement_status",
        (
            "def improvement_control_passes(status: Any, q05: float, bar: float) -> bool:\n"
            "    return bool(status == \"DETAIL_PASS\" and q05 > bar)\n"
        ),
        (
            "def improvement_control_passes(status: Any, q05: float, bar: float) -> bool:\n"
            "    return bool(True and q05 > bar)\n"
        ),
    ),
    Mutation(
        "commission-improvement-q05",
        "guard_commission_improvement_q05",
        "    return bool(status == \"DETAIL_PASS\" and q05 > bar)\n",
        "    return bool(status == \"DETAIL_PASS\" and True)\n",
    ),
    Mutation(
        "commission-improvement-contract-threshold",
        "guard_commission_improvement_contract_threshold",
        (
            '        config[\n'
            '            "pre_noise_optical_improvement_information_ratio_q05_strictly_above"\n'
            '        ]\n'
        ),
        '        config["pre_noise_blur_information_ratio_q95_strictly_below"]\n',
    ),
    Mutation(
        "commission-missing-status",
        "guard_commission_missing_status",
        (
            "        status == \"INSTRUMENT_INVALID\"\n"
            "        and \"flat control is missing\" in reason\n"
        ),
        (
            "        True\n"
            "        and \"flat control is missing\" in reason\n"
        ),
    ),
    Mutation(
        "commission-missing-reason",
        "guard_commission_missing_reason",
        "        and \"flat control is missing\" in reason\n",
        "        and True\n",
    ),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def load_module(source: bytes, name: str) -> Any:
    module = types.ModuleType(name)
    module.__file__ = str(ADAPTER_PATH)
    module.__package__ = ""
    sys.modules[name] = module
    try:
        exec(
            compile(source, str(ADAPTER_PATH), "exec", dont_inherit=True),
            module.__dict__,
        )
    finally:
        sys.modules.pop(name, None)
    return module


def apply_mutation(source: str, mutation: Mutation) -> bytes:
    count = source.count(mutation.old)
    if count != 1:
        raise RuntimeError(
            f"{mutation.mutation_id}: expected one source anchor, found {count}"
        )
    return source.replace(mutation.old, mutation.new, 1).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if sys.flags.isolated != 1:
        raise SystemExit("invoke through python -I")

    source_bytes = ADAPTER_PATH.read_bytes()
    source = (
        source_bytes.decode("utf-8")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    base = load_module(source_bytes, "m138_adapter_mutation_base")
    base_checks = base.mutation_probe_checks()
    expected_names = {mutation.expected_failed_check for mutation in MUTATIONS}
    base_ok = (
        set(base_checks) == expected_names
        and all(value is True for value in base_checks.values())
    )

    outcomes: list[dict[str, Any]] = []
    for index, mutation in enumerate(MUTATIONS):
        mutated = apply_mutation(source, mutation)
        module = load_module(mutated, f"m138_adapter_mutant_{index}")
        checks = module.mutation_probe_checks()
        failed = sorted(name for name, value in checks.items() if not value)
        outcomes.append(
            {
                "mutation_id": mutation.mutation_id,
                "expected_failed_check": mutation.expected_failed_check,
                "mutated_adapter_sha256": sha256_bytes(mutated),
                "failed_checks": failed,
                "killed": mutation.expected_failed_check in failed,
            }
        )

    inert_old = "Hash-bound M138 adapter for the frozen M135 per-capture checker."
    inert_new = (
        "Hash-bound M138 adapter for the frozen M135 per-capture checker. "
        "Inert mutation."
    )
    if source.count(inert_old) != 1:
        raise RuntimeError("inert mutation source anchor is not unique")
    inert_source = source.replace(inert_old, inert_new, 1).encode("utf-8")
    inert = load_module(inert_source, "m138_adapter_mutation_inert")
    inert_checks = inert.mutation_probe_checks()
    inert_survived = (
        set(inert_checks) == expected_names
        and all(value is True for value in inert_checks.values())
    )

    killed = sum(1 for outcome in outcomes if outcome["killed"])
    result = {
        "schema": "m135-m138-adapter-mutation-coverage/v1",
        "adapter_sha256": sha256_bytes(source_bytes),
        "status": (
            "PASS"
            if base_ok and killed == len(MUTATIONS) and inert_survived
            else "FAIL"
        ),
        "base_probe_count": len(base_checks),
        "base_probe_passed_count": sum(
            1 for value in base_checks.values() if value
        ),
        "substantive_mutation_count": len(MUTATIONS),
        "killed_mutation_count": killed,
        "inert_mutation_survived": inert_survived,
        "mutations": outcomes,
    }
    encoded = canonical_json_bytes(result) + b"\n"
    if args.output is None:
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(encoded)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
