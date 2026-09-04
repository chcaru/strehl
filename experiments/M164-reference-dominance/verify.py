"""Independent verifier for the reference-dominance commission."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
COMMISSION = HERE / "commission.py"
DOMINANCE = HERE / "dominance.py"
COMMITTED = HERE / "commission.json"
REGENERATED = HERE / ".verify-regenerated.json"
RED = HERE / ".verify-red.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run_commission(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(COMMISSION), *arguments],
        cwd=HERE.parents[1],
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    checks: dict[str, bool] = {}
    try:
        shared = np.diag([1.0, 0.8, 0.5, 0.0])
        reference_specific = np.diag([1.4, 1.3, 1.2, 1.1])
        scored_specific = np.diag([1.0, 0.9, 0.8, 0.7])
        reference = reference_specific @ shared
        scored = scored_specific @ shared
        supported = np.diag(shared) > 0.0
        ratio = np.diag(reference)[supported] / np.diag(scored)[supported]
        checks["shared_objective_allows_strict_supported_dominance"] = bool(
            np.all(ratio > 1.0)
        )
        checks["shared_objective_null_is_common"] = bool(
            np.diag(reference)[-1] == 0.0
            and np.diag(scored)[-1] == 0.0
        )

        latent = np.asarray([1.0, 0.8, 0.6])
        transfer = np.asarray([0.9, 0.7, 0.5])
        scale = 1.25
        checks["absolute_transfer_scale_gauge"] = bool(
            np.allclose(
                transfer * latent,
                (transfer / scale) * (scale * latent),
                rtol=0.0,
                atol=1.0e-15,
            )
        )

        regenerated = run_commission("--output", str(REGENERATED))
        checks["generator_passes"] = (
            regenerated.returncode == 0
            and regenerated.stdout.startswith("PASS: 15/15 checks")
        )
        checks["artifact_is_byte_identical"] = (
            REGENERATED.exists()
            and COMMITTED.exists()
            and REGENERATED.read_bytes() == COMMITTED.read_bytes()
        )
        artifact = json.loads(COMMITTED.read_text(encoding="utf-8"))
        checks["source_hashes_match"] = (
            artifact["source"]["dominance_py_sha256"] == digest(DOMINANCE)
            and artifact["source"]["commission_py_sha256"]
            == digest(COMMISSION)
        )
        checks["legitimate_case_passes"] = (
            artifact["legitimate"]["status"] == "PASS"
            and all(artifact["legitimate"]["cell_pass"])
        )
        checks["unknown_input_refuses_absolute_labels"] = (
            artifact["legitimate_relative_only"]["status"] == "PASS"
            and artifact["legitimate_relative_only"][
                "absolute_transfer_status"
            ]
            == "ABSOLUTE_TRANSFER_UNIDENTIFIED"
            and "absolute_transfer"
            not in artifact["legitimate_relative_only"]
        )
        weak = artifact["single_cell_violation"]
        checks["single_cell_cannot_be_compensated"] = (
            weak["status"] == "UNMEASURED"
            and weak["cell_pass"] == [True, True, True, False]
            and float(np.mean(weak["point"]["transfer_ratio"])) > 1.08
        )
        improvement = artifact["improvement_shaped_common_mode"]
        checks["improvement_shape_raises_both_numbers"] = (
            improvement["contaminated_naive_min_information_ratio"]
            > improvement["clean_min_information_ratio"]
            and improvement["contaminated_naive_min_transfer_ratio"]
            > improvement["clean_min_transfer_ratio"]
        )
        checks["common_mode_charge_rejects_improvement_shape"] = (
            improvement["contaminated_naive"]["status"] == "PASS"
            and improvement["contaminated_charged"]["status"] == "UNMEASURED"
            and improvement["contaminated_charged"]["failure"]
            == "COMMON_MODE_BOUND"
        )

        red = run_commission(
            "--plant-defect",
            "ignore-common-mode",
            "--output",
            str(RED),
        )
        red_artifact = json.loads(RED.read_text(encoding="utf-8"))
        failed = [
            name
            for name, passed in red_artifact["checks"].items()
            if not passed
        ]
        checks["red_canary_has_nonzero_exit"] = (
            red.returncode == 1
            and red.stdout.startswith("FAIL: 13/15 checks")
        )
        checks["red_canary_is_targeted"] = failed == [
            "C13_charged_improvement_shaped_case_is_rejected",
            "C14_common_mode_gate_names_the_failure",
        ]
    finally:
        REGENERATED.unlink(missing_ok=True)
        RED.unlink(missing_ok=True)

    passed = sum(checks.values())
    total = len(checks)
    for name, result in checks.items():
        if not result:
            print(f"FAIL: {name}")
    label = "PASS" if passed == total else "RED"
    print(
        f"TOTAL: {label} {passed}/{total} passed; "
        f"{total - passed} failed; 0 skipped"
    )
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
