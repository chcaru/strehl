"""Fail-closed verification of M164 code, artifacts, and gate direction."""

from __future__ import annotations

import hashlib
import json
import math
import sys
import types
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.ndimage import gaussian_filter

import transfer_veto


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "verification.json"
Q = 1.0 / 65535.0
INSTRUMENT = HERE / "transfer_veto.py"
COMMISSIONING = HERE / "commissioning.json"
RUN1 = HERE / "commissioning-run1-pre-clipping-control.json"
REFINEMENT = HERE / "refinement.json"
FINAL_REFINEMENT = HERE / "final-refinement.json"
SOURCE_ANCHOR = "        fired = all(checks.values())\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.name} root is not an object")
    return value


def reliable_threshold(
    records: list[dict[str, Any]], key: str
) -> float | None:
    strengths = sorted({float(record[key]) for record in records})
    for index, strength in enumerate(strengths):
        tail = [
            record
            for record in records
            if float(record[key]) >= strength - 1.0e-15
        ]
        per_strength = {
            candidate: [
                record
                for record in tail
                if math.isclose(
                    float(record[key]), candidate, rel_tol=0.0, abs_tol=1.0e-12
                )
            ]
            for candidate in strengths[index:]
        }
        if all(
            group and all(bool(record["fired"]) for record in group)
            for group in per_strength.values()
        ):
            return strength
    return None


def execute_mutant(source: str, name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(INSTRUMENT)
    module.__package__ = ""
    sys.modules[name] = module
    try:
        exec(compile(source, str(INSTRUMENT), "exec"), module.__dict__)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def analytic_scene() -> np.ndarray:
    y, x = np.mgrid[:256, :256]
    scene = (
        0.46
        + 0.13 * np.sin(x / 6.7)
        + 0.11 * np.cos(y / 10.3)
        + 0.06 * np.sin((x + y) / 3.9)
    )
    return np.rint(np.clip(scene, 0.08, 0.92) * 65535.0) / 65535.0


def main() -> int:
    report: dict[str, Any] = {
        "schema": 1,
        "passed": False,
        "checks": [],
        "errors": [],
    }

    def check(name: str, operation: Callable[[], Any]) -> None:
        try:
            detail = operation()
            report["checks"].append(
                {"name": name, "passed": True, "detail": detail}
            )
        except Exception as error:
            report["checks"].append(
                {
                    "name": name,
                    "passed": False,
                    "detail": f"{type(error).__name__}: {error}",
                }
            )
            report["errors"].append(
                {"check": name, "error": f"{type(error).__name__}: {error}"}
            )

    artifacts: dict[str, dict[str, Any]] = {}

    def read_artifacts() -> str:
        for name, path in (
            ("commissioning", COMMISSIONING),
            ("run1", RUN1),
            ("refinement", REFINEMENT),
            ("final", FINAL_REFINEMENT),
        ):
            artifacts[name] = load_json(path)
            require(
                not any(
                    key.endswith("_failed") and value
                    for key, value in artifacts[name].items()
                ),
                f"{path.name} is a failure artifact",
            )
        return "four JSON artifacts parsed without non-finite JSON tokens"

    check("artifact parse", read_artifacts)

    def check_hashes() -> str:
        commissioning = artifacts["commissioning"]
        refinement = artifacts["refinement"]
        final = artifacts["final"]
        instrument_hash = sha256_file(INSTRUMENT)
        require(
            commissioning["instrument"]["sha256"] == instrument_hash,
            "commissioning instrument hash does not bind current source",
        )
        require(
            refinement["instrument_sha256"] == instrument_hash,
            "refinement instrument hash does not bind current source",
        )
        require(
            final["instrument_sha256"] == instrument_hash,
            "final refinement instrument hash does not bind current source",
        )
        require(
            refinement["run1_sha256"] == sha256_file(RUN1),
            "refinement does not bind preserved run 1",
        )
        require(
            refinement["amendment_sha256"] == sha256_file(HERE / "AMENDMENT-2.md"),
            "refinement does not bind amendment 2",
        )
        require(
            final["amendment_sha256"] == sha256_file(HERE / "AMENDMENT-3.md"),
            "final refinement does not bind amendment 3",
        )
        for source in commissioning["inputs"]:
            path = Path(source["path"])
            require(path.stat().st_size == source["bytes"], f"size changed: {path}")
            require(sha256_file(path) == source["sha256"], f"hash changed: {path}")
        return "instrument, amendments, preserved run, and both source rasters match"

    check("hash binding", check_hashes)

    def check_aggregates() -> dict[str, Any]:
        commissioning = artifacts["commissioning"]
        refinement = artifacts["refinement"]
        final = artifacts["final"]

        identity = commissioning["identity"]["trials"]
        disturbance = commissioning["movable_null_disturbance"]["trials"]
        require(len(identity) == 12 and sum(r["fired"] for r in identity) == 0, "identity")
        require(
            len(disturbance) == 12 and sum(r["fired"] for r in disturbance) == 0,
            "disturbance false fire",
        )
        require(
            min(r["difference_rms_lsb"] for r in disturbance)
            > max(r["difference_rms_lsb"] for r in identity),
            "null probe did not move",
        )

        blur_threshold = reliable_threshold(
            refinement["gaussian_blur_combined"]["refinement_trials"]
            + commissioning["gaussian_blur"]["trials"],
            "sigma",
        )
        require(
            math.isclose(
                blur_threshold,
                refinement["gaussian_blur_combined"]["reliable_threshold"],
            ),
            "blur threshold aggregate mismatch",
        )
        gain_threshold = reliable_threshold(
            refinement["scalar_gain_combined"]["refinement_trials"]
            + commissioning["scalar_gain"]["trials"],
            "gain_delta",
        )
        require(
            math.isclose(
                gain_threshold,
                refinement["scalar_gain_combined"]["reliable_threshold"],
            ),
            "gain threshold aggregate mismatch",
        )
        usm_trials = (
            [
                record
                for record in commissioning["unsharp_mask"]["trials"]
                if float(record["amount"]) <= 0.20
            ]
            + final["original_contrast_unsharp_combined"]["refinement_trials"]
        )
        usm_threshold = reliable_threshold(usm_trials, "amount")
        require(
            math.isclose(
                usm_threshold,
                final["original_contrast_unsharp_combined"][
                    "reliable_threshold"
                ],
            ),
            "USM threshold aggregate mismatch",
        )

        shift_trials = (
            [
                record
                for record in commissioning["resampling"]["trials"]
                if record["kind"] == "bilinear-shift-roundtrip"
            ]
            + refinement["resampling_shift_combined"]["refinement_trials"]
            + final["resampling_shift_combined"]["refinement_trials"]
        )
        shift_threshold = reliable_threshold(shift_trials, "distance")
        require(
            math.isclose(
                shift_threshold,
                final["resampling_shift_combined"]["reliable_threshold"],
            ),
            "resampling threshold aggregate mismatch",
        )

        legitimate = [
            record
            for records in commissioning["legitimate_differences"]["trials"].values()
            for record in records
        ]
        false_positives = sum(record["fired"] for record in legitimate)
        require(len(legitimate) == 144, "legitimate battery count changed")
        require(false_positives == 0, "legitimate battery has a false fire")
        upper = 1.0 - 0.05 ** (1.0 / len(legitimate))
        recorded_upper = commissioning["legitimate_differences"]["overall"][
            "one_sided_clopper_pearson_95_upper"
        ]
        require(
            math.isclose(upper, recorded_upper, rel_tol=0.0, abs_tol=1.0e-15),
            "false-positive confidence bound mismatch",
        )

        common_improvement = commissioning["planted_improvement"][
            "truth_improving_common_usm"
        ]["trials"]
        require(
            len(common_improvement) == 12
            and all(record["truth_improved"] for record in common_improvement)
            and all(record["fired"] for record in common_improvement),
            "truth-improving common USM result changed",
        )
        optical = commissioning["planted_improvement"]["fresh_noise_optical"][
            "trials"
        ]
        require(
            len(optical) == 96
            and all(record["truth_improved"] for record in optical)
            and not any(record["fired"] for record in optical),
            "fresh-noise optical-improvement result changed",
        )
        require(
            commissioning["blur_plus_gain"]["summary"]["fires"] == 72,
            "blur-plus-gain count changed",
        )
        require(
            commissioning["resampling"]["by_kind"]["box-down-bilinear-up-2x"][
                "fires"
            ]
            == 12,
            "twofold resampling count changed",
        )
        return {
            "blur_sigma": blur_threshold,
            "usm_amount": usm_threshold,
            "gain_delta": gain_threshold,
            "resampling_displacement_px": shift_threshold,
            "false_positives": false_positives,
            "legitimate_trials": len(legitimate),
            "false_positive_upper_95": upper,
        }

    check("aggregate re-derivation", check_aggregates)

    def check_clipping() -> str:
        refinement = artifacts["refinement"]
        audit = refinement["original_unsharp_clipping_audit"]["by_amount"]
        for amount in ("0.001", "0.002", "0.005", "0.01", "0.02", "0.05", "0.1", "0.2"):
            require(audit[amount]["total_clipped_samples"] == 0, f"unexpected clip at {amount}")
        require(audit["0.5"]["total_clipped_samples"] > 0, "0.5 clipping not observed")
        require(audit["1"]["total_clipped_samples"] > 0, "1.0 clipping not observed")
        require(
            refinement["clipping_free_unsharp_mask"]["zero_clipped_samples"],
            "headroom USM arm clipped",
        )
        require(
            artifacts["final"]["original_contrast_unsharp_combined"][
                "zero_clipped_samples_in_refinement"
            ],
            "original-contrast refinement clipped",
        )
        return "original 0.5/1.0 failures are clipping-bound; repaired arms are linear"

    check("sharpening clipping audit", check_clipping)

    def check_scalar_algebra() -> dict[str, float]:
        image_a = analytic_scene()
        image_b = np.rint(image_a * 1.001 * 65535.0) / 65535.0
        x = image_a.ravel()
        y = (image_b - image_a).ravel()
        design = np.column_stack((np.ones(x.size), x))
        coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
        residual_lsb = float(
            np.sqrt(np.mean((y - design @ coefficients) ** 2)) / Q
        )
        result = transfer_veto.evaluate_transfer_veto(image_a, image_b, Q)
        require(result["fired"], "instrument did not fire on independent gain plant")
        require(residual_lsb < 0.5, "scalar algebra residual exceeds quantization")
        require(
            abs(float(coefficients[1]) - 0.001) < 5.0e-6,
            "independent gain estimate is wrong",
        )
        return {
            "fitted_gain_delta": float(coefficients[1]),
            "residual_rms_lsb": residual_lsb,
        }

    check("independent scalar algebra", check_scalar_algebra)

    def check_refusals() -> str:
        bad_a = np.ones((64, 64), dtype=np.float64)
        result = transfer_veto.evaluate_transfer_veto(bad_a, bad_a, Q)
        require(result["status"] == "INSTRUMENT_INVALID", "small input not refused")
        nonfinite = np.ones((256, 256), dtype=np.float64)
        nonfinite[0, 0] = np.nan
        result = transfer_veto.evaluate_transfer_veto(nonfinite, nonfinite, Q)
        require(result["status"] == "INSTRUMENT_INVALID", "NaN input not refused")
        return "small and non-finite inputs degrade to INSTRUMENT_INVALID"

    check("fail-closed refusals", check_refusals)

    def check_mutations() -> dict[str, Any]:
        source = INSTRUMENT.read_text(encoding="utf-8")
        require(
            source.count(SOURCE_ANCHOR) == 1,
            "mutation anchor is absent or non-unique",
        )
        image_a = analytic_scene()
        blurred = np.rint(
            gaussian_filter(image_a, sigma=0.60, mode="reflect", truncate=4.0)
            * 65535.0
        ) / 65535.0
        original_positive = transfer_veto.evaluate_transfer_veto(
            image_a, blurred, Q
        )
        require(original_positive["fired"], "positive mutation fixture is not live")

        false_source = source.replace(
            SOURCE_ANCHOR,
            "        fired = False and all(checks.values())\n",
        )
        require(false_source != source, "false mutation did not alter source")
        false_module = execute_mutant(false_source, "m164_mutant_false")
        try:
            killed_positive = false_module.evaluate_transfer_veto(
                image_a, blurred, Q
            )
        finally:
            sys.modules.pop("m164_mutant_false", None)
        require(
            not killed_positive["fired"],
            "always-false mutation did not kill positive control",
        )

        y, x = np.mgrid[:256, :256]
        disk = np.exp(
            -((y - 90.0) ** 2 + (x - 165.0) ** 2) / (2.0 * 18.0**2)
        )
        disturbed = np.rint(
            np.clip(image_a + 32.0 * Q * disk, 0.0, 1.0) * 65535.0
        ) / 65535.0
        original_negative = transfer_veto.evaluate_transfer_veto(
            image_a, disturbed, Q
        )
        require(
            not original_negative["fired"],
            "negative mutation fixture already fires",
        )
        true_source = source.replace(
            SOURCE_ANCHOR,
            "        fired = True or all(checks.values())\n",
        )
        require(true_source != source, "true mutation did not alter source")
        true_module = execute_mutant(true_source, "m164_mutant_true")
        try:
            corrupted_negative = true_module.evaluate_transfer_veto(
                image_a, disturbed, Q
            )
        finally:
            sys.modules.pop("m164_mutant_true", None)
        require(
            corrupted_negative["fired"],
            "always-true mutation did not corrupt negative control",
        )
        return {
            "anchor_count": 1,
            "positive_original": original_positive["status"],
            "positive_mutant": killed_positive["status"],
            "negative_original": original_negative["status"],
            "negative_mutant": corrupted_negative["status"],
        }

    check("bidirectional mutation controls", check_mutations)

    report["passed"] = not report["errors"]
    try:
        OUTPUT.write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except Exception as error:
        fallback = {
            "schema": 1,
            "passed": False,
            "checks": [],
            "errors": [
                {
                    "check": "verification serialization",
                    "error": f"{type(error).__name__}: {error}",
                }
            ],
        }
        OUTPUT.write_text(
            json.dumps(fallback, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("FAIL: verification serialization")
        return 1

    print("PASS" if report["passed"] else "FAIL")
    for item in report["checks"]:
        print(f"[{'PASS' if item['passed'] else 'FAIL'}] {item['name']}: {item['detail']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
