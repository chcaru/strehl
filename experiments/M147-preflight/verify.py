"""Independent checks for M147 artifacts.

This script deliberately does not import preflight.py or commission.py.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import rawpy
from scipy import ndimage


HERE = Path(__file__).resolve().parent
NULL_ARTIFACT = HERE / "out" / "null.json"
COMMISSION_ARTIFACT = HERE / "out" / "commission.json"
OUTPUT = HERE / "out" / "verification.json"
REQUIRED_NONCOVERAGE_ARMS = {
    "alias",
    "alias-weak",
    "alias-third",
    "alias-third-weak",
    "anisotropic",
    "perspective",
    "blur-mild",
    "blur-severe",
    "partial-grid",
    "no-grid",
    "real-null",
    "single-site-defect",
    "rotation-mapping",
    "scale-low",
    "scale-nominal",
    "scale-inside",
    "scale-outside",
    "scale-large",
}
EXPECTED_COVERAGE_ARMS = {f"coverage-{index:02d}" for index in range(20)}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def decode_visible_and_green(path: Path) -> tuple[str, np.ndarray]:
    with rawpy.imread(str(path)) as raw:
        mosaic = np.array(raw.raw_image_visible, dtype=np.uint16, copy=True)
        pattern = np.array(raw.raw_pattern, dtype=np.int16, copy=True)
        black = np.array(raw.black_level_per_channel, dtype=np.float32, copy=True)
        color_desc = bytes(raw.color_desc)
    green_indices = [
        index for index, value in enumerate(color_desc) if value == ord("G")
    ]
    positions = np.argwhere(np.isin(pattern, green_indices))
    planes = [
        mosaic[row::2, column::2].astype(np.float32)
        - black[int(pattern[row, column])]
        for row, column in positions
    ]
    decoded_hash = hashlib.sha256(memoryview(np.ascontiguousarray(mosaic))).hexdigest()
    return decoded_hash, np.mean(planes, axis=0)


def parabolic_offset(a: float, b: float, c: float) -> float:
    denominator = a - 2.0 * b + c
    if denominator >= -1e-12:
        return 0.0
    return float(np.clip(0.5 * (a - c) / denominator, -0.5, 0.5))


def autocorrelation_period(image: np.ndarray) -> dict[str, Any]:
    # Fixed lower-right ROI: a large uniform dot-grid region in the burned
    # slide.  This is independent verification only, not the field estimator.
    roi = image[1200:2200, 1800:3300].astype(np.float64)
    roi -= np.mean(roi)
    window_y = np.hanning(roi.shape[0])
    window_x = np.hanning(roi.shape[1])
    spectrum = np.fft.fft2(roi * window_y[:, None] * window_x[None, :])
    correlation = np.fft.fftshift(np.fft.ifft2(np.abs(spectrum) ** 2).real)
    center = np.asarray(correlation.shape) // 2
    y, x = np.indices(correlation.shape)
    radius = np.hypot(y - center[0], x - center[1])
    search = (radius >= 45.0) & (radius <= 80.0)
    local = correlation == ndimage.maximum_filter(correlation, size=9, mode="constant")
    peaks = np.argwhere(search & local)
    peaks = sorted(
        peaks,
        key=lambda rc: float(correlation[int(rc[0]), int(rc[1])]),
        reverse=True,
    )[:8]
    if len(peaks) < 4:
        raise AssertionError("independent autocorrelation found too few grid peaks")
    radii = []
    for row, column in peaks[:4]:
        dy = int(row - center[0])
        dx = int(column - center[1])
        row_offset = parabolic_offset(
            correlation[row - 1, column],
            correlation[row, column],
            correlation[row + 1, column],
        )
        column_offset = parabolic_offset(
            correlation[row, column - 1],
            correlation[row, column],
            correlation[row, column + 1],
        )
        radii.append(math.hypot(dy + row_offset, dx + column_offset))
    return {
        "method": "fixed-ROI two-dimensional spatial autocorrelation",
        "roi_green_px": [1200, 2200, 1800, 3300],
        "peak_radii_green_px": [float(value) for value in radii],
        "period_green_px": float(np.median(radii)),
    }


def main() -> None:
    null = json.loads(NULL_ARTIFACT.read_text(encoding="utf-8"))
    commission = json.loads(COMMISSION_ARTIFACT.read_text(encoding="utf-8"))
    checks: dict[str, Any] = {}

    checks["artifact_schemas_are_current"] = (
        null["schema"] == "m147-preflight-result-v2"
        and commission["schema"] == "m147-commission-v2"
        and null["parameters"]["schema"] == "m147-preflight-parameters-v2"
        and commission["rules"]["schema"] == "m147-commission-rules-v2"
    )
    checks["parameter_hash_matches_null"] = (
        canonical_hash(null["parameters"]) == null["parameters_sha256"]
    )
    checks["parameter_hash_matches_commission"] = (
        null["parameters_sha256"] == commission["preflight_parameters_sha256"]
    )
    checks["preflight_source_hash_matches"] = (
        sha256_file(HERE / "preflight.py")
        == commission["source_sha256"]["preflight.py"]
        == null["tool"]["source_sha256"]
    )
    checks["commission_source_hash_matches"] = (
        sha256_file(HERE / "commission.py")
        == commission["source_sha256"]["commission.py"]
    )
    checks["commission_rules_hash_matches"] = (
        canonical_hash(commission["rules"]) == commission["rules_sha256"]
    )

    independent = {}
    for role in ("reference", "scored"):
        record = null["inputs"][role]
        path = Path(record["path"])
        checks[f"{role}_file_hash_matches"] = sha256_file(path) == record["sha256"]
        decoded_hash, green = decode_visible_and_green(path)
        checks[f"{role}_decoded_hash_matches"] = (
            decoded_hash == record["decoded_visible_sha256"]
        )
        independent[role] = autocorrelation_period(green)
    independent_ratio = (
        independent["reference"]["period_green_px"]
        / independent["scored"]["period_green_px"]
    )
    independent["ratio"] = independent_ratio
    checks["independent_null_within_0_25_percent"] = (
        abs(independent_ratio - 1.0) <= 0.0025
    )
    null_decision = null["decision"]
    checks["recorded_null_covers_truth_and_fails"] = (
        null["status"] == "OK"
        and abs(float(null_decision["sampling_ratio"]) - 1.0) <= 0.0025
        and float(null_decision["interval"]["lower"]) <= 1.0
        <= float(null_decision["interval"]["upper"])
        and null_decision["verdict"] == "FAIL"
    )

    arms = commission["arms"]
    arm_names = set(arms)
    coverage_names = {name for name in arm_names if name.startswith("coverage-")}
    noncoverage_names = arm_names - coverage_names
    checks["exact_commission_arm_set_present"] = (
        coverage_names == EXPECTED_COVERAGE_ARMS
        and noncoverage_names == REQUIRED_NONCOVERAGE_ARMS
        and set(commission["required_noncov_arms"]) == REQUIRED_NONCOVERAGE_ARMS
        and set(commission["expected_coverage_arms"]) == EXPECTED_COVERAGE_ARMS
    )
    recomputed_all_pass = all(arm.get("pass") is True for arm in arms.values())
    checks["all_recorded_commission_arms_pass"] = (
        recomputed_all_pass
        and commission["all_recorded_arms_pass"] is True
    )
    covered_trials = sum(
        arms.get(name, {}).get("covered") is True
        for name in EXPECTED_COVERAGE_ARMS
    )
    checks["coverage_is_20_of_20"] = (
        covered_trials == 20
        and commission["coverage"]["covered_trials"] == covered_trials
        and commission["coverage"]["recorded_trials"] == 20
    )
    recomputed_synthetic_pass = (
        noncoverage_names == REQUIRED_NONCOVERAGE_ARMS
        and all(arms[name].get("pass") is True for name in REQUIRED_NONCOVERAGE_ARMS)
        and 18 <= covered_trials <= 20
    )
    checks["synthetic_commission_passes"] = (
        recomputed_synthetic_pass
        and commission["synthetic_commission"]["pass"] is True
    )
    false_passes = 0
    above_threshold = 0
    above_threshold_passes = 0
    gate_invariants_hold = True
    for name, arm in arms.items():
        if arm.get("measurement_status") == "OK":
            decision = arm["decision"]
            expected_verdict = (
                "PASS" if float(decision["interval"]["lower"]) >= 2.0 else "FAIL"
            )
            gate_invariants_hold &= decision["verdict"] == expected_verdict
        if name not in EXPECTED_COVERAGE_ARMS:
            continue
        if (
            float(arm["truth_ratio"]) <= 2.0
            and arm["decision"]["verdict"] == "PASS"
        ):
            false_passes += 1
        if float(arm["truth_ratio"]) > 2.0:
            above_threshold += 1
            if arm["decision"]["verdict"] == "PASS":
                above_threshold_passes += 1
    checks["all_numeric_gate_invariants_hold"] = gate_invariants_hold
    checks["no_below_threshold_coverage_passes"] = false_passes == 0
    checks["all_above_threshold_coverage_trials_pass"] = (
        above_threshold == 6 and above_threshold_passes == 6
    )
    checks["alias_regressions_refuse"] = all(
        name in arms
        and arms[name].get("measurement_status") == "REFUSED"
        and arms[name].get("reason_code") == "AMBIGUOUS_HARMONIC"
        for name in ("alias", "alias-weak", "alias-third", "alias-third-weak")
    )
    checks["mapping_regressions_fail"] = all(
        name in arms
        and arms[name].get("measurement_status") == "OK"
        and arms[name]["decision"]["verdict"] == "FAIL"
        and math.isclose(
            float(
                arms[name]["decision"]["interval"][
                    "local_spatial_ratio_envelope"
                ][0]
            ),
            1.99,
            abs_tol=1e-12,
        )
        for name in ("single-site-defect", "rotation-mapping")
    )
    checks["field_commission_remains_blocked"] = (
        commission["field_commission"]["status"] == "BLOCKED"
    )

    mutation = json.loads(json.dumps(null["parameters"]))
    mutation["decision"]["minimum_sampling_ratio"] = 1.99
    checks["parameter_mutation_changes_hash"] = (
        canonical_hash(mutation) != null["parameters_sha256"]
    )

    output = {
        "schema": "m147-independent-verification-v2",
        "verifier_source_sha256": sha256_file(Path(__file__).resolve()),
        "imports_production_modules": False,
        "checks": checks,
        "independent_period_check": independent,
        "pass": all(checks.values()),
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True, allow_nan=False))
    if not output["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
