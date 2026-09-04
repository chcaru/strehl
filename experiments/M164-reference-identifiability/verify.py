"""Independently re-derive and verify the M164 reference witness."""

from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
WITNESS = HERE / "witness.py"
COMMITTED = HERE / "results.json"
REGENERATED = HERE / ".verify-regenerated.json"
RED_ARTIFACT = HERE / ".verify-red.json"
PROPOSAL = (
    HERE.parents[1]
    / "docs"
    / "proposals"
    / "2026-09-truth-referenced-detail.md"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def covariance(first: np.ndarray, second: np.ndarray) -> float:
    first = first - np.mean(first)
    second = second - np.mean(second)
    return float(np.mean(first * second))


def run_generator(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(WITNESS), *arguments],
        cwd=HERE.parents[1],
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    categories: dict[str, dict[str, bool]] = {
        "RE-DERIVATION": {},
        "ARTIFACT CONSISTENCY": {},
        "RED CANARY": {},
    }
    try:
        x = np.asarray([1.0, 0.8, 0.6, 0.4])
        h_s = np.diag([0.90, 0.70, 0.50, 0.30])
        k = np.diag([1.0, 1.0, 1.20, 1.0])
        h_r = np.diag([0.95, 0.80, 0.60, 0.40])
        x_prime = k @ x
        h_r_prime = h_r @ np.linalg.inv(k)
        categories["RE-DERIVATION"]["unknown_transfer_gauge"] = bool(
            np.array_equal(k @ h_s @ x, h_s @ x_prime)
            and np.array_equal(h_r @ x, h_r_prime @ x_prime)
        )

        k_null = np.diag([1.0, 1.0, 1.0, 2.0])
        h_r_null = np.diag([0.95, 0.80, 0.60, 0.0])
        categories["RE-DERIVATION"]["fixed_reference_nullspace"] = bool(
            np.array_equal(k_null @ h_s @ x, h_s @ k_null @ x)
            and np.array_equal(h_r_null @ x, h_r_null @ k_null @ x)
            and not np.array_equal(k_null, np.eye(len(x)))
        )

        near_delta = float(
            np.max(
                np.abs(
                    np.diag([0.95, 0.80, 0.60, 1.0e-4]) @ x
                    - np.diag([0.95, 0.80, 0.60, 1.0e-4])
                    @ k_null
                    @ x
                )
            )
        )
        informative_delta = float(
            np.max(
                np.abs(
                    np.diag([0.95, 0.80, 0.60, 0.20]) @ x
                    - np.diag([0.95, 0.80, 0.60, 0.20])
                    @ k_null
                    @ x
                )
            )
        )
        categories["RE-DERIVATION"]["near_null_and_movable_probe"] = (
            0.0 < near_delta < 1.0e-3 < informative_delta
        )

        def information(transfer: float) -> float:
            return 0.5 * float(np.log2(1.0 + transfer**2 / 0.01))

        categories["RE-DERIVATION"]["information_dominance_moves"] = bool(
            0.0 < information(0.20) < information(0.30) < information(0.50)
        )

        rows = np.asarray(list(itertools.product((-1.0, 1.0), repeat=4)))
        signal = rows[:, 0]
        common = 0.2 * rows[:, 1]
        noise_1 = 0.1 * rows[:, 2]
        noise_2 = 0.1 * rows[:, 3]
        total = covariance(
            signal + common + noise_1,
            signal + common + noise_2,
        )
        conditional = covariance(noise_1, noise_2)
        conditional_means = covariance(signal + common, signal + common)
        categories["RE-DERIVATION"]["law_of_total_covariance"] = bool(
            conditional == 0.0
            and np.isclose(
                total,
                conditional + conditional_means,
                rtol=0.0,
                atol=1.0e-15,
            )
            and covariance(common + noise_1, common + noise_2) > 0.0
        )

        ratio = 2.7015 / 1.33
        categories["RE-DERIVATION"]["sampling_not_information"] = bool(
            ratio > 2.0
            and np.array_equal(h_r_null @ x, h_r_null @ k_null @ x)
        )

        generated = run_generator("--output", str(REGENERATED))
        categories["ARTIFACT CONSISTENCY"]["generator_passes"] = (
            generated.returncode == 0
            and generated.stdout.startswith("PASS: 11/11 checks")
        )
        categories["ARTIFACT CONSISTENCY"]["byte_identical"] = (
            REGENERATED.exists()
            and COMMITTED.exists()
            and REGENERATED.read_bytes() == COMMITTED.read_bytes()
        )
        artifact = json.loads(COMMITTED.read_text(encoding="utf-8"))
        categories["ARTIFACT CONSISTENCY"]["witness_hash"] = (
            artifact["source"]["witness_py_sha256"] == digest(WITNESS)
        )
        categories["ARTIFACT CONSISTENCY"]["proposal_hash"] = (
            artifact["source"]["proposal_file_sha256"] == digest(PROPOSAL)
        )

        red = run_generator(
            "--plant-defect",
            "informative-reference-collapse",
            "--output",
            str(RED_ARTIFACT),
        )
        categories["RED CANARY"]["nonzero_exit"] = (
            red.returncode == 1
            and red.stdout.startswith("FAIL: 10/11 checks")
        )
        red_result = json.loads(RED_ARTIFACT.read_text(encoding="utf-8"))
        failed_checks = [
            name
            for name, passed in red_result["checks"].items()
            if not passed
        ]
        categories["RED CANARY"]["targeted_failure"] = failed_checks == [
            "C5_informative_reference_exposes_same_change"
        ]
    finally:
        REGENERATED.unlink(missing_ok=True)
        RED_ARTIFACT.unlink(missing_ok=True)

    passed = sum(
        passed
        for checks in categories.values()
        for passed in checks.values()
    )
    total = sum(len(checks) for checks in categories.values())
    for category, checks in categories.items():
        category_passed = sum(checks.values())
        label = "PASS" if category_passed == len(checks) else "RED"
        print(
            f"{category}: {label} {category_passed}/{len(checks)} passed"
        )
        for name, result in checks.items():
            if not result:
                print(f"  FAIL: {name}")
    failed = total - passed
    label = "PASS" if failed == 0 else "RED"
    print(
        f"TOTAL: {label} {passed}/{total} passed; "
        f"{failed} failed; 0 skipped"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
