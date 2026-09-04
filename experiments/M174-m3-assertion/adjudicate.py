"""Independently adjudicate M161's M3 improvement-arm assertion.

The script reads the frozen M161/M169 artifacts, opens no RAW or product pixels,
and writes only beneath the M174 experiment directory.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
M152 = ROOT / "experiments" / "M152-site-census"
M161 = ROOT / "experiments" / "M161-m3-ratification"
M169 = ROOT / "experiments" / "M169-m3-veil"
OUT = HERE / "out" / "adjudication.json"
OUT_SHA = HERE / "out" / "adjudication.sha256"
ORACLE = HERE / "oracle-template.json"
RATIFICATION_COMMIT = "47d67a9f"
EXPECTED_M161_SHA256 = {
    "commission_m3_v2.py": (
        "342ea2d9064130117f9173ff2311a47465760519251f2c473f3a8ea8d34952da"
    ),
    "m3_checker_v2.py": (
        "05d291c8c24712d46666e9ed398f39cb982fa3b4c918a7e0cfcdee200dec2eda"
    ),
    "m3-checker-definition-v2.json": (
        "578022e6eeefecce60a00191024e9ffd4dc3c621410b398709b3f92b987b67ca"
    ),
}
EXPECTED_M152_COMMISSION_SHA256 = (
    "cd997c28a6e0532c48858350f0f3c0c0434285ede91413ce43952a6880b36ad6"
)
CURVE_AMPLITUDES = [index * 0.0005 for index in range(13)]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def exact_float_match(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def replace_unique_full_line(text: str, anchor: str, replacement: str) -> str:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line == anchor]
    if len(matches) != 1:
        raise RuntimeError(
            f"full-line anchor count must be exactly one, got {len(matches)}: "
            f"{anchor!r}"
        )
    lines[matches[0]] = replacement
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def find_arm(document: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [arm for arm in document["arms"] if arm["name"] == name]
    if len(matches) != 1:
        raise RuntimeError(f"expected one arm named {name}, got {len(matches)}")
    return matches[0]


def main() -> int:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, evidence: Any) -> None:
        checks.append(
            {
                "name": name,
                "outcome": "PASS" if passed else "FAIL",
                "evidence": evidence,
            }
        )

    current_hashes = {
        name: sha256_file(M161 / name) for name in EXPECTED_M161_SHA256
    }
    for name, expected in EXPECTED_M161_SHA256.items():
        check(
            f"m161_hash_{name}",
            current_hashes[name] == expected,
            {"expected": expected, "actual": current_hashes[name]},
        )

    frozen_paths = [
        "experiments/M161-m3-ratification/commission_m3_v2.py",
        "experiments/M161-m3-ratification/m3_checker_v2.py",
        "experiments/M161-m3-ratification/m3-checker-definition-v2.json",
        "experiments/M161-m3-ratification/preregistration.json",
    ]
    diff = subprocess.run(
        ["git", "diff", "--quiet", RATIFICATION_COMMIT, "--", *frozen_paths],
        cwd=ROOT,
        check=False,
    )
    check(
        "m161_worktree_matches_ratification_commit",
        diff.returncode == 0,
        {"commit": RATIFICATION_COMMIT, "git_diff_exit": diff.returncode},
    )

    check(
        "m169_checker_matches_m161",
        sha256_file(M169 / "m3_checker_v2.py")
        == current_hashes["m3_checker_v2.py"],
        {
            "m161": current_hashes["m3_checker_v2.py"],
            "m169": sha256_file(M169 / "m3_checker_v2.py"),
        },
    )
    check(
        "m169_definition_matches_m161",
        sha256_file(M169 / "m3-checker-definition-v2.json")
        == current_hashes["m3-checker-definition-v2.json"],
        {
            "m161": current_hashes["m3-checker-definition-v2.json"],
            "m169": sha256_file(M169 / "m3-checker-definition-v2.json"),
        },
    )

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(M161))
    checker = importlib.import_module("m3_checker_v2")
    commission = importlib.import_module("commission_m3_v2")
    definition, definition_sha = checker.load_checker_definition()
    check(
        "loaded_definition_hash_matches",
        definition_sha == EXPECTED_M161_SHA256["m3-checker-definition-v2.json"],
        {
            "expected": EXPECTED_M161_SHA256[
                "m3-checker-definition-v2.json"
            ],
            "actual": definition_sha,
        },
    )

    identity: Callable[[np.ndarray, np.ndarray, float], np.ndarray] = (
        lambda output, offsets, step: output.copy()
    )
    identity_patch: Callable[[np.ndarray, float], np.ndarray] = (
        lambda patch, step: patch.copy()
    )
    improved = (
        lambda output, offsets, step: output
        + commission.rim_delta(offsets, step, 0.005)
        + commission.two_sided_veil_delta(offsets, step, 0.005)
    )
    improved_patch = lambda patch, step: commission.patch_delta(
        patch, step, rim=0.005, veil=0.005
    )

    clean_summary, clean_rows = commission.arm_summary(
        "clean_noise_null",
        identity,
        identity_patch,
        definition,
        0.0,
    )
    improved_summary, improved_rows = commission.arm_summary(
        "planted_improvement_0_5pct_rim_and_veil",
        improved,
        improved_patch,
        definition,
        0.005,
    )
    del clean_rows, improved_rows

    m169_bytes = (M169 / "out" / "commission-v2.json").read_bytes()
    m169_commission = json.loads(m169_bytes)
    m169_clean = find_arm(m169_commission, "clean_noise_null")
    m169_improved = find_arm(
        m169_commission, "planted_improvement_0_5pct_rim_and_veil"
    )
    compared_fields = [
        "median_h_e",
        "median_v_e",
        "p99_h_e",
        "p99_v_e",
        "maximum_max_h_v",
        "median_edge_width_ratio",
        "median_rho_edge",
    ]
    for label, source, reported in [
        ("clean", clean_summary, m169_clean),
        ("improved", improved_summary, m169_improved),
    ]:
        differences = {
            field: float(source[field]) - float(reported[field])
            for field in compared_fields
        }
        check(
            f"m169_{label}_numbers_reproduce",
            all(exact_float_match(source[field], reported[field]) for field in compared_fields),
            differences,
        )

    clean_failed_gates = sorted(
        name for name, passed in clean_summary["checks"].items() if not passed
    )
    improved_failed_gates = sorted(
        name for name, passed in improved_summary["checks"].items() if not passed
    )
    check(
        "clean_null_passes_all_gates",
        clean_summary["verdict"] == "PASS" and not clean_failed_gates,
        {
            "median_h_e": clean_summary["median_h_e"],
            "failed_gates": clean_failed_gates,
        },
    )
    check(
        "improved_arm_fails_only_median_h_e",
        improved_summary["verdict"] == "FAIL"
        and improved_failed_gates == ["median_h_e"],
        {
            "median_h_e": improved_summary["median_h_e"],
            "failed_gates": improved_failed_gates,
        },
    )

    sites: list[Any] = []
    planted_steps: list[float] = []

    def capture_identity(
        output: np.ndarray, offsets: np.ndarray, step: float
    ) -> np.ndarray:
        planted_steps.append(float(step))
        return output.copy()

    def capture_site(site: Any, ignored_definition: dict[str, Any]) -> dict[str, Any]:
        del ignored_definition
        sites.append(site)
        return {"capture_id": site.capture_id}

    original_score_site = commission.score_site
    commission.score_site = capture_site
    try:
        commission.synthetic_population(
            capture_identity, identity_patch, definition
        )
    finally:
        commission.score_site = original_score_site
    check(
        "frozen_population_captured_completely",
        len(sites) == commission.SITE_COUNT
        and len(planted_steps) == commission.SITE_COUNT,
        {
            "expected": commission.SITE_COUNT,
            "sites": len(sites),
            "steps": len(planted_steps),
        },
    )

    def response(amplitude: float, plant: str = "combined") -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for site, step in zip(sites, planted_steps, strict=True):
            if plant == "clean":
                delta = np.zeros_like(site.output_profile)
            elif plant == "rim":
                delta = commission.rim_delta(
                    site.offsets_native_px, step, amplitude
                )
            elif plant == "veil":
                delta = commission.two_sided_veil_delta(
                    site.offsets_native_px, step, amplitude
                )
            elif plant == "combined":
                delta = commission.rim_delta(
                    site.offsets_native_px, step, amplitude
                ) + commission.two_sided_veil_delta(
                    site.offsets_native_px, step, amplitude
                )
            else:
                raise ValueError(f"unknown plant: {plant}")
            probe = dataclasses.replace(
                site,
                output_profile=site.output_profile + delta,
                output_patch=None,
                sharp_source_patch=None,
            )
            rows.append(checker.score_site(probe, definition))
        h_values = [row["h_e"] for row in rows]
        v_values = [row["v_e"] for row in rows]
        maximum = max(max(row["h_e"], row["v_e"]) for row in rows)
        median_h = checker.nearest_rank(h_values, 0.50)
        median_v = checker.nearest_rank(v_values, 0.50)
        return {
            "plant": plant,
            "component_amplitude_fraction_of_step": amplitude,
            "component_amplitude_percent": 100.0 * amplitude,
            "median_h_e": median_h,
            "median_v_e": median_v,
            "p99_h_e": checker.nearest_rank(h_values, 0.99),
            "p99_v_e": checker.nearest_rank(v_values, 0.99),
            "maximum_max_h_v": maximum,
            "median_h_e_gate": "PASS"
            if median_h <= float(definition["bars"]["median_h_e_max"])
            else "FAIL",
        }

    response_curve = [response(amplitude) for amplitude in CURVE_AMPLITUDES]
    curve_counts = Counter(row["median_h_e_gate"] for row in response_curve)
    curve_partition = {
        "total": len(response_curve),
        "pass": curve_counts["PASS"],
        "fail": curve_counts["FAIL"],
    }
    check(
        "response_curve_partition_is_complete",
        curve_partition["pass"] + curve_partition["fail"]
        == curve_partition["total"],
        curve_partition,
    )

    clean_profile_response = response(0.0)
    improved_profile_response = response(0.005)
    check(
        "profile_curve_matches_full_clean_run",
        exact_float_match(
            clean_profile_response["median_h_e"],
            clean_summary["median_h_e"],
        )
        and exact_float_match(
            clean_profile_response["median_v_e"],
            clean_summary["median_v_e"],
        ),
        {
            "curve_h": clean_profile_response["median_h_e"],
            "full_h": clean_summary["median_h_e"],
            "curve_v": clean_profile_response["median_v_e"],
            "full_v": clean_summary["median_v_e"],
        },
    )
    check(
        "profile_curve_matches_full_improved_run",
        exact_float_match(
            improved_profile_response["median_h_e"],
            improved_summary["median_h_e"],
        )
        and exact_float_match(
            improved_profile_response["median_v_e"],
            improved_summary["median_v_e"],
        ),
        {
            "curve_h": improved_profile_response["median_h_e"],
            "full_h": improved_summary["median_h_e"],
            "curve_v": improved_profile_response["median_v_e"],
            "full_v": improved_summary["median_v_e"],
        },
    )

    median_h_gate = float(definition["bars"]["median_h_e_max"])
    lower = 0.0
    upper = 0.006
    for _ in range(48):
        midpoint = 0.5 * (lower + upper)
        if response(midpoint)["median_h_e"] <= median_h_gate:
            lower = midpoint
        else:
            upper = midpoint
    crossing = {
        "largest_passing_component_amplitude_fraction": lower,
        "smallest_failing_component_amplitude_fraction": upper,
        "component_amplitude_percent_approx": 100.0 * upper,
        "combined_noiseless_peak_percent_approx": 200.0 * upper,
        "median_h_e_at_largest_pass": response(lower)["median_h_e"],
        "median_h_e_at_smallest_fail": response(upper)["median_h_e"],
    }

    component_responses = {
        plant: response(0.005, plant)
        for plant in ["clean", "rim", "veil", "combined"]
    }
    check(
        "individual_half_percent_components_pass_but_combination_fails",
        component_responses["rim"]["median_h_e_gate"] == "PASS"
        and component_responses["veil"]["median_h_e_gate"] == "PASS"
        and component_responses["combined"]["median_h_e_gate"] == "FAIL",
        {
            name: {
                "median_h_e": values["median_h_e"],
                "gate": values["median_h_e_gate"],
            }
            for name, values in component_responses.items()
        },
    )

    offsets = np.arange(-400.0, 401.0, 1.0)
    rim = commission.rim_delta(offsets, 1.0, 0.005)
    veil = commission.two_sided_veil_delta(offsets, 1.0, 0.005)
    combined = rim + veil
    halo_low, halo_high = definition["halo"]["support_abs_native_px"]
    halo_mask = (np.abs(offsets) >= float(halo_low)) & (
        np.abs(offsets) <= float(halo_high)
    )
    negative_veil = (offsets >= -200.0) & (offsets <= -16.0)
    positive_veil = (offsets >= 16.0) & (offsets <= 200.0)
    deterministic = {
        "rim_component_fraction": 0.005,
        "veil_component_fraction": 0.005,
        "maximum_absolute_combined_delta_in_h_support": float(
            np.max(np.abs(combined[halo_mask]))
        ),
        "median_h_e_gate": median_h_gate,
        "positive_overlap_offsets": [
            int(value)
            for value in offsets[
                halo_mask & np.isclose(combined, 0.010, rtol=0.0, atol=1e-15)
            ]
        ],
        "noiseless_v_e_negative_side": float(
            np.mean(np.abs(combined[negative_veil]))
        ),
        "noiseless_v_e_positive_side": float(
            np.mean(np.abs(combined[positive_veil]))
        ),
    }
    check(
        "design_places_combined_plant_at_median_h_gate",
        exact_float_match(
            deterministic["maximum_absolute_combined_delta_in_h_support"],
            median_h_gate,
            tolerance=1e-15,
        )
        and deterministic["positive_overlap_offsets"]
        == list(range(16, 25)),
        deterministic,
    )

    m152_path = M152 / "out" / "m3-commission.json"
    m152_bytes = m152_path.read_bytes()
    m152_commission = json.loads(m152_bytes)
    m152_improved = find_arm(
        m152_commission, "planted_improvement_0_5pct_rim_and_veil"
    )
    m152_assertions = set(m152_commission["assertions"])
    m152_lineage = {
        "artifact_sha256": sha256_bytes(m152_bytes),
        "median_h_e": m152_improved["median_h_e"],
        "p99_h_e": m152_improved["p99_h_e"],
        "median_gate_margin": median_h_gate - m152_improved["median_h_e"],
        "p99_to_median_gate_margin": median_h_gate - m152_improved["p99_h_e"],
        "assertion_names": sorted(m152_assertions),
    }
    check(
        "m152_artifact_hash_matches_report",
        m152_lineage["artifact_sha256"]
        == EXPECTED_M152_COMMISSION_SHA256,
        {
            "expected": EXPECTED_M152_COMMISSION_SHA256,
            "actual": m152_lineage["artifact_sha256"],
        },
    )
    check(
        "m152_registered_movement_not_whole_arm_pass",
        "improvement_reduces_h_by_at_least_5pp" in m152_assertions
        and "improvement_reduces_v_by_at_least_5pp" in m152_assertions
        and "improved_arm_passes" not in m152_assertions,
        m152_lineage,
    )

    preregistration_text = (
        M161 / "preregistration.json"
    ).read_text(encoding="utf-8")
    registered_pass_line = '        "improved arm passes"'
    check(
        "m161_pass_expectation_is_unique_full_line",
        preregistration_text.splitlines().count(registered_pass_line) == 1,
        {
            "anchor": registered_pass_line,
            "count": preregistration_text.splitlines().count(
                registered_pass_line
            ),
        },
    )

    oracle_text = ORACLE.read_text(encoding="utf-8")
    oracle_line = '  "registered_expectation": "FAIL_MEDIAN_H_E",'
    defective_line = '  "registered_expectation": "PASS_ALL_GATES",'

    def oracle_is_consistent(text: str) -> bool:
        value = json.loads(text)
        amplitude = float(value["component_amplitude_fraction_of_step"])
        measured = response(amplitude)
        expectation = value["registered_expectation"]
        if expectation == "FAIL_MEDIAN_H_E":
            return measured["median_h_e_gate"] == "FAIL"
        if expectation == "PASS_ALL_GATES":
            return measured["median_h_e_gate"] == "PASS"
        raise RuntimeError(f"unknown oracle expectation: {expectation}")

    check(
        "corrected_oracle_accepts",
        oracle_is_consistent(oracle_text),
        {"anchor": oracle_line},
    )
    defective_oracle = replace_unique_full_line(
        oracle_text, oracle_line, defective_line
    )
    check(
        "planted_pass_assertion_defect_is_rejected",
        not oracle_is_consistent(defective_oracle),
        {"planted_line": defective_line},
    )
    missing_anchor_hard_error = False
    try:
        replace_unique_full_line(
            oracle_text,
            '  "registered_expectation": "MISSING_ANCHOR",',
            defective_line,
        )
    except RuntimeError:
        missing_anchor_hard_error = True
    check(
        "missing_anchor_hard_errors",
        missing_anchor_hard_error,
        {"expected": "RuntimeError"},
    )

    clean_headroom_ratio = median_h_gate / float(clean_summary["median_h_e"])
    rationale = {
        "verdict": "B_ASSERTION_DEFECT",
        "clean_null_median_h_e": clean_summary["median_h_e"],
        "clean_null_headroom_ratio_to_gate": clean_headroom_ratio,
        "improvement_median_h_e": improved_summary["median_h_e"],
        "improvement_excess_over_gate": float(improved_summary["median_h_e"])
        - median_h_gate,
        "pre_registration_derivation": [
            "The frozen rim contributes +0.005 on offsets +12..+24.",
            "The frozen two-sided veil contributes +0.005 on offsets +16..+200.",
            "Their overlap at +16..+24 is nine samples inside h_e support and sums to +0.010 before noise.",
            "The frozen median h_e gate is 0.010, so this is a boundary challenge, not a green cleanliness arm.",
            "M152 had already measured the same nominal arm at median 0.0098849484 and p99 0.0099980927 with no noisy source/output null, and asserted only downward movement.",
            "M161 retained the amplitude, added independent sigma=0.002 source/output noise, then added the inconsistent whole-arm PASS assertion.",
        ],
        "correct_registration": {
            "arm_role": "planted boundary improvement that remains red",
            "required_expectation": "FAIL_MEDIAN_H_E",
            "retain_existing_movement_assertions": [
                "improvement_reduces_h_by_at_least_5pp",
                "improvement_reduces_v_by_at_least_5pp",
            ],
            "unchanged": [
                "0.005 rim plant",
                "0.005 veil plant",
                "0.01 median h_e gate",
                "0.01 median v_e gate",
                "0.05 headline maximum gate",
                "all other M3 gates",
                "checker source",
                "seed",
                "population",
            ],
        },
    }

    outcomes = Counter(item["outcome"] for item in checks)
    check_partition = {
        "total": len(checks),
        "pass": outcomes["PASS"],
        "fail": outcomes["FAIL"],
        "error": outcomes["ERROR"],
    }
    if (
        check_partition["pass"]
        + check_partition["fail"]
        + check_partition["error"]
        != check_partition["total"]
    ):
        raise RuntimeError("check outcomes do not partition the examined total")

    result = {
        "schema": "m174-m3-improvement-assertion-adjudication-v1",
        "verdict": "B_ASSERTION_DEFECT",
        "candidate_outputs_opened": 0,
        "comparator_outputs_opened": 0,
        "capture_pixels_opened": 0,
        "protected_holdout_opened": 0,
        "source_hashes": {
            "m161": current_hashes,
            "m169_commission_artifact": sha256_bytes(m169_bytes),
            "m152_commission_artifact": sha256_bytes(m152_bytes),
            "oracle_template": sha256_file(ORACLE),
            "adjudicator": sha256_file(Path(__file__)),
        },
        "clean_null": clean_summary,
        "improvement": improved_summary,
        "deterministic_design": deterministic,
        "component_responses_at_0_5pct": component_responses,
        "response_curve": response_curve,
        "response_curve_partition": curve_partition,
        "median_h_e_crossing": crossing,
        "m152_lineage": m152_lineage,
        "rationale": rationale,
        "checks": checks,
        "check_partition": check_partition,
    }
    write_json(OUT, result)
    OUT_SHA.write_text(sha256_file(OUT) + "\n", encoding="ascii")

    print("VERDICT B_ASSERTION_DEFECT")
    print(
        "clean_null median_h_e=%.15f gate=%.15f headroom=%.9fx"
        % (clean_summary["median_h_e"], median_h_gate, clean_headroom_ratio)
    )
    print(
        "improvement median_h_e=%.15f failed=%s"
        % (improved_summary["median_h_e"], ",".join(improved_failed_gates))
    )
    print(
        "crossing component_amplitude=%.9f%% combined_peak=%.9f%%"
        % (
            crossing["component_amplitude_percent_approx"],
            crossing["combined_noiseless_peak_percent_approx"],
        )
    )
    print(
        "response_curve total=%d pass=%d fail=%d"
        % (
            curve_partition["total"],
            curve_partition["pass"],
            curve_partition["fail"],
        )
    )
    print(
        "checks total=%d pass=%d fail=%d error=%d"
        % (
            check_partition["total"],
            check_partition["pass"],
            check_partition["fail"],
            check_partition["error"],
        )
    )
    return 0 if check_partition["fail"] == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
