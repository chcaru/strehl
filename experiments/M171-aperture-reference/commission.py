#!/usr/bin/env python3
"""Commission the M171 physics preflight with anchored RED mutations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


SCHEMA = "M171-aperture-reference-commission-v1"
SOURCE = Path(__file__).with_name("audit.py")

MUTATIONS = [
    (
        "stack_member_missing",
        '        for index in range(int(expected["count"])):',
        '        for index in range(int(expected["count"]) - 1):',
    ),
    (
        "metadata_directory_outside_root",
        '                    "Directory": str(root / Path(stack)),',
        '                    "Directory": r"C:\\outside",',
    ),
    (
        "camera_model_wrong",
        '                    "Model": "ILCE-7CM2",',
        '                    "Model": "WRONG-CAMERA",',
    ),
    (
        "lens_model_wrong",
        '                        "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"',
        '                        "WRONG LENS"',
    ),
    (
        "lens_type_wrong",
        '                    "LensType3": 33094,',
        '                    "LensType3": 1,',
    ),
    (
        "f_number_wrong",
        '                    "FNumber": float(expected["f_number"]),',
        '                    "FNumber": 99.0,',
    ),
    (
        "sensor_pitch_wrong",
        "SENSOR_WIDTH_MM = 35.9",
        "SENSOR_WIDTH_MM = 36.0",
    ),
    (
        "focal_length_check_wrong",
        "EXPECTED_FOCAL_LENGTH_MM = 200.0",
        "EXPECTED_FOCAL_LENGTH_MM = 100.0",
    ),
    (
        "tc_correction_check_wrong",
        "EXPECTED_MAX_APERTURE = 5.6",
        "EXPECTED_MAX_APERTURE = 2.8",
    ),
    (
        "focal_length_35mm_wrong",
        '                    "FocalLengthIn35mmFormat": 200.0,',
        '                    "FocalLengthIn35mmFormat": 100.0,',
    ),
    (
        "iso_wrong",
        '                    "ISO": 100,',
        '                    "ISO": 200,',
    ),
    (
        "exposure_wrong",
        '                    "ExposureTime": float(expected["exposure_s"]),',
        '                    "ExposureTime": 99.0,',
    ),
    (
        "focus_position_non_numeric",
        '                    "FocusPosition2": 58 + index % 4,',
        '                    "FocusPosition2": None,',
    ),
    (
        "capture_time_missing",
        '                    "DateTimeOriginal": (',
        '                    "DateTimeOriginal_WRONG": (',
    ),
    (
        "airy_radius_substituted_for_diameter",
        "AIRY_DIAMETER_FACTOR = 2.44",
        "AIRY_DIAMETER_FACTOR = 1.22",
    ),
    (
        "mtf_normalization_halved",
        "MTF_SCALE = 2.0 / math.pi",
        "MTF_SCALE = 1.0 / math.pi",
    ),
    (
        "planted_improvement_blinded",
        "DIRECTIONAL_IMPROVEMENT_N = 5.6",
        "DIRECTIONAL_IMPROVEMENT_N = 8.0",
    ),
    (
        "planted_degradation_blinded",
        "DIRECTIONAL_DEGRADATION_N = 11.0",
        "DIRECTIONAL_DEGRADATION_N = 8.0",
    ),
    (
        "aberration_reversal_erased",
        "COUNTEREXAMPLE_W040_WAVES = 0.60",
        "COUNTEREXAMPLE_W040_WAVES = 0.00",
    ),
    (
        "counterexample_ignored",
        "    verdict = counterexample_verdict(counterexample)",
        '    verdict = "FORCED"',
    ),
]


class CommissionError(RuntimeError):
    """Hard commissioning failure."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def numerical_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "BLIS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        env[name] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_self_test(source: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(source), "--self-test"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=numerical_env(),
    )


def mutate_unique(text: str, anchor: str, replacement: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise CommissionError(
            f"ANCHOR ERROR: expected exactly one {anchor!r}, found {count}"
        )
    return text.replace(anchor, replacement, 1)


def concise_output(completed: subprocess.CompletedProcess[str]) -> str:
    combined = (completed.stdout + completed.stderr).strip().splitlines()
    return combined[-1] if combined else "<no output>"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.resolve()
    if resolved.drive.lower() == "d:":
        raise CommissionError(
            f"refusing to write under read-only D: tree: {resolved}"
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    original = SOURCE.read_text(encoding="utf-8")
    source_before = sha256(SOURCE)
    baseline = run_self_test(SOURCE)
    baseline_passed = baseline.returncode == 0
    print(
        f"GREEN baseline: {'PASS' if baseline_passed else 'FAIL'} "
        f"({concise_output(baseline)})"
    )

    mutation_results = []
    with tempfile.TemporaryDirectory(prefix="m171-commission-") as temporary:
        temporary_path = Path(temporary)
        for name, anchor, replacement in MUTATIONS:
            mutated_text = mutate_unique(original, anchor, replacement)
            mutated_source = temporary_path / f"{name}.py"
            mutated_source.write_text(mutated_text, encoding="utf-8")
            completed = run_self_test(mutated_source)
            caught = completed.returncode != 0
            line = concise_output(completed)
            print(f"RED {name}: {'CAUGHT' if caught else 'MISSED'} ({line})")
            mutation_results.append(
                {
                    "name": name,
                    "anchor": anchor,
                    "replacement": replacement,
                    "returncode": completed.returncode,
                    "red_caught": caught,
                    "output": line,
                }
            )

    missing_anchor_hard_error = False
    missing_anchor_message = ""
    try:
        mutate_unique(
            original,
            "THIS UNIQUE FULL-LINE ANCHOR DOES NOT EXIST",
            "replacement",
        )
    except CommissionError as exc:
        missing_anchor_hard_error = True
        missing_anchor_message = str(exc)
    print(
        "RED missing_anchor: "
        f"{'HARD_ERROR' if missing_anchor_hard_error else 'MISSED'} "
        f"({missing_anchor_message})"
    )

    source_after = sha256(SOURCE)
    source_unchanged = source_before == source_after
    all_caught = all(item["red_caught"] for item in mutation_results)
    commissioned = (
        baseline_passed
        and all_caught
        and missing_anchor_hard_error
        and source_unchanged
    )
    payload = {
        "schema": SCHEMA,
        "status": "COMMISSIONED" if commissioned else "NOT_COMMISSIONED",
        "baseline": {
            "passed": baseline_passed,
            "returncode": baseline.returncode,
            "output": concise_output(baseline),
        },
        "mutations": mutation_results,
        "mutation_count": len(mutation_results),
        "caught_count": sum(
            int(item["red_caught"]) for item in mutation_results
        ),
        "missing_anchor_hard_error": {
            "passed": missing_anchor_hard_error,
            "message": missing_anchor_message,
        },
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "source_unchanged": source_unchanged,
        "planted_improvement_commissioned": any(
            item["name"] == "planted_improvement_blinded"
            and item["red_caught"]
            for item in mutation_results
        ),
        "planted_degradation_present_in_green": (
            "planted_degradation" in baseline.stdout
        ),
    }
    write_json(args.output, payload)
    print(f"STATUS: {payload['status']}")
    return 0 if commissioned else 1


if __name__ == "__main__":
    raise SystemExit(main())
