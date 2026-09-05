from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from reference import (
    SYNTH_FOCUS_STEP_UM,
    SYNTH_FRAME_STEPS,
    SYNTH_HEIGHT,
    SYNTH_INSTANCE_COUNT,
    SYNTH_TARGETS_PER_CLASS,
    SYNTH_TARGETS_PER_INSTANCE,
    SYNTH_WIDTH,
    development_summary,
    load_json_strict,
    make_fixtures,
    make_sample_manifest,
    seed_commitment,
    sha256_lower,
    validate_manifest_dict,
)


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS {message}")


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def verify_contract(contract: dict[str, Any], allow_pending_seed: bool) -> None:
    require(
        contract["schema"] == "strehl.m10-definition-freeze.v1",
        "contract schema identifier",
    )
    contracts = contract["contracts"]
    require(
        set(contracts)
        == {
            "quota_selection",
            "origin_fit",
            "depth_product",
            "synthetic_instrument",
        },
        "exactly four frozen contracts",
    )

    quota = contracts["quota_selection"]
    require(quota["digest"] == "SHA-256", "quota digest algorithm")
    require(
        quota["unsigned_interpretation"] == "big-endian",
        "quota digest byte order",
    )
    require(
        quota["sort_key"]
        == ["digest_bytes_lexicographic", "y", "x", "cell_id_utf8_bytes"],
        "quota total ordering",
    )

    origin = contracts["origin_fit"]
    require(
        origin["N"]
        == "count(candidate_valid && truth_target) in the full unresampled capture population",
        "origin divisor definition",
    )
    require(
        origin["zero_case"] == "candidate-worst for every origin-dependent metric",
        "origin zero-denominator handling",
    )

    product = contracts["depth_product"]
    require(
        product["manifest_schema"] == "depth-manifest.schema.json",
        "manifest schema binding",
    )
    require(
        product["hash_contract"] == "sha256-raw-bytes-lowerhex-v1",
        "product hash algorithm and encoding",
    )
    require(
        product["invalid_float32_bits"] == "7fc00000",
        "invalid float sentinel",
    )

    synthetic = contracts["synthetic_instrument"]
    require(synthetic["width"] == SYNTH_WIDTH, "synthetic width")
    require(synthetic["height"] == SYNTH_HEIGHT, "synthetic height")
    require(
        synthetic["instance_count"] == SYNTH_INSTANCE_COUNT,
        "synthetic instance count",
    )
    require(
        synthetic["targets_per_instance"] == SYNTH_TARGETS_PER_INSTANCE,
        "synthetic targets per instance",
    )
    require(
        synthetic["targets_per_class"] == SYNTH_TARGETS_PER_CLASS,
        "synthetic targets per class",
    )
    require(
        synthetic["focus_step_um"] == SYNTH_FOCUS_STEP_UM,
        "synthetic focus step",
    )
    require(
        synthetic["frame_steps"] == [min(SYNTH_FRAME_STEPS), max(SYNTH_FRAME_STEPS)],
        "synthetic frame-step range",
    )
    require(
        synthetic["sensor_noise"] == "none",
        "synthetic scored arm has no invented sensor-noise model",
    )
    commitment = synthetic["scored_seed_commitment_sha256"]
    if commitment is None:
        require(allow_pending_seed, "pending seed allowed only for algorithm precommit")
    else:
        require(
            isinstance(commitment, str)
            and len(commitment) == 64
            and all(char in "0123456789abcdef" for char in commitment),
            "scored seed commitment syntax",
        )

    failure = contract["failure_mapping"]
    require(
        failure["stage_order"]
        == [
            "checker_contract",
            "truth_preflight",
            "product_availability",
            "candidate_product_contract",
            "metric_decision",
        ],
        "failure stage order",
    )
    codes = [entry["code"] for entry in failure["known_failures"]]
    require(len(codes) == len(set(codes)), "failure codes are unique")
    allowed_outcomes = {
        "CANDIDATE_FAIL",
        "PRODUCT_UNMEASURED",
        "TRUTH_UNMEASURED",
        "CHECKER_ERROR",
    }
    require(
        all(entry["record_outcome"] in allowed_outcomes for entry in failure["known_failures"]),
        "every known failure has one record outcome",
    )
    require(
        failure["unknown_failure"]["record_outcome"] == "CHECKER_ERROR",
        "unknown failures fail closed",
    )
    require(
        failure["summary_equation"]
        == "total_examined = PASS + CANDIDATE_FAIL + PRODUCT_UNMEASURED + TRUTH_UNMEASURED + CHECKER_ERROR",
        "failure summary is a complete partition",
    )


def verify_failure_partition(
    contract: dict[str, Any],
    fixtures: dict[str, Any],
) -> None:
    known = {
        entry["code"]: entry["record_outcome"]
        for entry in contract["failure_mapping"]["known_failures"]
    }
    unknown = contract["failure_mapping"]["unknown_failure"]["record_outcome"]
    records = fixtures["failure_partition"]["records"]
    outcomes = []
    for record in records:
        if record["code"] == "OK":
            derived = "PASS"
        else:
            derived = known.get(record["code"], unknown)
        require(derived == record["outcome"], f"failure mapping {record['code']}")
        outcomes.append(derived)
    counts = Counter(outcomes)
    observed = {
        "PASS": counts["PASS"],
        "CANDIDATE_FAIL": counts["CANDIDATE_FAIL"],
        "PRODUCT_UNMEASURED": counts["PRODUCT_UNMEASURED"],
        "TRUTH_UNMEASURED": counts["TRUTH_UNMEASURED"],
        "CHECKER_ERROR": counts["CHECKER_ERROR"],
        "total_examined": len(records),
    }
    require(
        observed == fixtures["failure_partition"]["expected_counts"],
        "failure records partition total examined",
    )


def verify_development_summary(
    expected: dict[str, Any],
    observed: dict[str, Any],
) -> None:
    require(observed == expected, "development synthetic summary round-trip")
    require(
        observed["total_target_count"] == 40000,
        "synthetic total target count",
    )
    require(
        observed["interior_target_count"] == 20000,
        "synthetic interior target count",
    )
    require(
        observed["boundary_target_count"] == 20000,
        "synthetic boundary target count",
    )
    require(
        observed["minimum_layer_separation_steps"] >= 8,
        "synthetic minimum layer separation",
    )
    require(
        observed["minimum_truth_depth_steps"] > min(SYNTH_FRAME_STEPS)
        and observed["maximum_truth_depth_steps"] < max(SYNTH_FRAME_STEPS),
        "synthetic truth lies strictly inside focus bracket",
    )
    require(
        all(
            item["certificate"]["triple_count"]
            >= item["certificate"]["required_triple_count"]
            and item["certificate"]["minimum_abs_second_difference_steps"] > 4
            for item in observed["instances"]
        ),
        "all affine certificates meet strict proof condition",
    )


def verify_scored_seed(contract: dict[str, Any]) -> None:
    seed_hex = os.environ.get("M190_SCORED_SEED_HEX")
    if seed_hex is None:
        return
    seed = bytes.fromhex(seed_hex)
    require(len(seed) == 32, "scored seed length")
    commitment = contract["contracts"]["synthetic_instrument"][
        "scored_seed_commitment_sha256"
    ]
    require(seed_commitment(seed) == commitment, "scored seed commitment")
    summary = development_summary(seed)
    require(
        len(summary["instances"]) == SYNTH_INSTANCE_COUNT,
        "scored seed instance generation",
    )
    require(
        all(
            item["certificate"]["triple_count"]
            == item["certificate"]["required_triple_count"]
            == 101
            for item in summary["instances"]
        ),
        "scored seed affine certificates 20/20",
    )
    require(
        summary["minimum_layer_separation_steps"] >= 8,
        "scored seed layer separation",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-pending-seed", action="store_true")
    args = parser.parse_args()

    contract = load_json_strict(ROOT / "contract-v1.json")
    schema = load_json_strict(ROOT / "depth-manifest.schema.json")
    fixtures = load_json_strict(ROOT / "fixtures.json")
    manifest = load_json_strict(ROOT / "sample-depth-manifest.json")
    development = load_json_strict(ROOT / "development-synthetic-summary.json")

    verify_contract(contract, args.allow_pending_seed)
    require(
        schema["$id"] == "https://carusos-conjecture.net/strehl/m10/depth-manifest-v1.schema.json",
        "JSON Schema identifier",
    )
    validate_manifest_dict(manifest)
    require(manifest == make_sample_manifest(), "manifest shape round-trip")
    require(fixtures == make_fixtures(), "all hashing and arithmetic fixtures round-trip")
    verify_failure_partition(contract, fixtures)
    verify_development_summary(
        development_summary(bytes(range(32))),
        development,
    )
    verify_scored_seed(contract)

    print(f"CONTRACT_SHA256 {sha256_lower((ROOT / 'contract-v1.json').read_bytes())}")
    print(f"SCHEMA_SHA256 {sha256_lower((ROOT / 'depth-manifest.schema.json').read_bytes())}")
    print(f"FIXTURES_SHA256 {sha256_lower((ROOT / 'fixtures.json').read_bytes())}")
    print("VERDICT GREEN")


if __name__ == "__main__":
    main()
