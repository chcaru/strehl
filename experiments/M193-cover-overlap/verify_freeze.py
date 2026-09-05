from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import tifffile

from reference import (
    MAX_OUTPUT_RESIDUAL_MICROPIXEL,
    OUTPUT_GRID_SCHEMA,
    ROTATION_TAN_Q62_FLOOR,
    SCHEMA,
    canonical_json_bytes,
    load_json,
    make_fixtures,
    manifest_digest,
)


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS {message}")


def verify_contract(contract: dict[str, object]) -> None:
    require(
        contract["schema"] == "strehl.m193-cover-overlap-contract.v1",
        "contract schema",
    )
    scope = contract["scope"]
    require(
        scope["constructor_inputs"]
        == "the multiset of exact common-input TIFF byte strings for one capture",
        "constructor is byte-only",
    )
    forbidden = set(scope["forbidden_inputs"])
    require(
        {
            "candidate output bytes",
            "comparator output bytes",
            "stacker alignment or crop results",
        }
        <= forbidden,
        "stacker outputs are forbidden constructor inputs",
    )
    require(
        contract["registration"]["reference_key"]
        == ["SHA-256 digest bytes", "byte length", "exact TIFF bytes"],
        "reference selection has a total byte key",
    )
    require(
        contract["overlap"]["tie_break"]
        == [
            "maximum area",
            "minimum y",
            "minimum x",
            "maximum height",
            "maximum width",
        ],
        "maximal rectangle has a total tie-break",
    )
    unchanged = contract["unchanged_scorecard_thresholds"]
    require(
        unchanged
        == {
            "retained_field_of_view_percent_minimum": 99.0,
            "output_scale_disagreement_percent_maximum": 0.1,
            "output_rotation_disagreement_degrees_maximum": 0.02,
            "output_nontranslation_residual_rms_px_maximum": 0.1,
            "identical_site_survival_percent_minimum": 80.0,
            "differential_site_attrition_percentage_points_maximum": 2.0,
        },
        "scorecard thresholds are unchanged",
    )
    verdicts = [entry["verdict"] for entry in contract["failure_mapping"]]
    require(len(verdicts) == len(set(verdicts)), "failure verdicts are unique")
    require(
        "UNMEASURED_DENOMINATOR_UNDEFINED" in verdicts
        and "UNMEASURED_OUTPUT_GRID_UNDEFINED" in verdicts
        and "UNMEASURED_CHECKER_ERROR" in verdicts,
        "fail-closed denominator, mapping, and checker outcomes exist",
    )


def verify_environment(contract: dict[str, object]) -> None:
    expected = contract["reference_environment"]
    require(sys.version.split()[0] == expected["python"], "Python version")
    require(np.__version__ == expected["numpy"], "NumPy version")
    require(cv2.__version__ == expected["opencv"], "OpenCV version")
    require(tifffile.__version__ == expected["tifffile"], "tifffile version")
    build_hash = hashlib.sha256(cv2.getBuildInformation().encode("utf-8")).hexdigest()
    require(
        build_hash == expected["opencv_build_information_sha256"],
        "OpenCV build fingerprint",
    )


def verify_fixture_shape(fixtures: dict[str, object]) -> None:
    overlap = fixtures["synthetic_overlap"]
    require(overlap["schema"] == SCHEMA, "overlap manifest schema")
    require(
        overlap["manifest_sha256"] == manifest_digest(overlap),
        "overlap manifest self-hash",
    )
    rectangle = overlap["common_overlap"]
    require(
        rectangle["area_pixels"] == rectangle["width"] * rectangle["height"],
        "overlap denominator is rectangle area",
    )
    tie = fixtures["tie_break"]["expected"]
    require(
        tie["x"] == 0 and tie["y"] == 0 and tie["width"] == 2 and tie["height"] == 2,
        "top-left tie-break fixture",
    )
    retention = fixtures["output_retention"]
    require(
        retention["identity"]["field_of_view_verdict"] == "PASS"
        and retention["identity"]["retained_pixels"]
        == retention["identity"]["denominator_pixels"],
        "identity output retains the whole denominator",
    )
    require(
        retention["cropped"]["field_of_view_verdict"]
        == "FAIL_GEOMETRY_FIELD_OF_VIEW",
        "cropped output can fail the unchanged 99% bar",
    )
    require(
        OUTPUT_GRID_SCHEMA == "strehl.m193-output-grid.v1"
        and MAX_OUTPUT_RESIDUAL_MICROPIXEL == 100_000,
        "output-grid contract constants",
    )
    require(
        ROTATION_TAN_Q62_FLOOR == 1_609_782_167_177_275,
        "exact rotation gate constant",
    )


def main() -> None:
    contract = load_json(ROOT / "contract-v1.json")
    expected = load_json(ROOT / "fixtures.json")
    verify_contract(contract)
    verify_environment(contract)
    observed = make_fixtures()
    require(observed == expected, "all deterministic fixtures round-trip")
    verify_fixture_shape(observed)
    print(
        "CONTRACT_SHA256",
        hashlib.sha256(canonical_json_bytes(contract)).hexdigest(),
    )
    print(
        "FIXTURES_SHA256",
        hashlib.sha256((ROOT / "fixtures.json").read_bytes()).hexdigest(),
    )
    print("VERDICT GREEN")


if __name__ == "__main__":
    main()
