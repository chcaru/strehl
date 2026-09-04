"""Registered M130 border-profile and retained-area instrument.

The real score compares the seven-band Crop render against the two-band Crop
control on the emitted green plane.  It deliberately has no dependency on
strehl's Rust implementation.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import tifffile

import artifact_io


THRESHOLD = 0.001
DEEP_START = 768
PROFILE_EDGES = (
    0,
    2,
    4,
    8,
    16,
    32,
    64,
    96,
    128,
    160,
    192,
    256,
    320,
    384,
    448,
    512,
    640,
    768,
)
MIN_CANDIDATE = 8
FULL_WIDTH = 3516
FULL_HEIGHT = 2344
RETENTION_GATE = 0.80
HERE = Path(__file__).resolve().parent
DEFAULT_RESULTS_ARTIFACT = HERE / "results.json"


def sha256(path: Path) -> str:
    return artifact_io.sha256_file(path)


def emit(result: dict[str, Any], output: Path | None) -> dict[str, Any]:
    if output is not None:
        result = artifact_io.write_artifact(output, result)
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return result


def per_distance(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sum one HxW plane by integer distance from its emitted boundary."""

    if image.ndim != 2:
        raise ValueError(f"expected a two-dimensional plane, got {image.shape}")
    height, width = image.shape
    max_distance = (min(height, width) - 1) // 2
    sums = np.zeros(max_distance + 1, dtype=np.float64)
    counts = np.zeros(max_distance + 1, dtype=np.int64)
    horizontal = np.minimum(np.arange(width), np.arange(width)[::-1])
    for y in range(height):
        distance = np.minimum(horizontal, min(y, height - 1 - y))
        sums += np.bincount(
            distance,
            weights=np.asarray(image[y], dtype=np.float64),
            minlength=sums.size,
        )[: sums.size]
        counts += np.bincount(distance, minlength=counts.size)[: counts.size]
    if int(counts.sum()) != height * width:
        raise AssertionError("distance partition did not cover every pixel")
    return sums, counts


def fixed_profile(
    candidate_sums: np.ndarray,
    reference_sums: np.ndarray,
    counts: np.ndarray,
    *,
    threshold: float = THRESHOLD,
    deep_start: int = DEEP_START,
    edges: Sequence[int] = PROFILE_EDGES,
) -> dict[str, Any]:
    """Apply the pre-registered M-COVER-BORDER annular statistic."""

    n = min(candidate_sums.size, reference_sums.size, counts.size)
    if deep_start >= n or int(counts[deep_start:].sum()) == 0:
        raise ValueError(f"deep start {deep_start} exceeds maximum distance {n - 1}")
    deep_reference = float(reference_sums[deep_start:].sum(dtype=np.float64))
    if deep_reference <= 0.0:
        raise ValueError("the deep reference level is not positive")
    deep_ratio = float(
        candidate_sums[deep_start:].sum(dtype=np.float64) / deep_reference
    )
    boundaries = sorted(
        {
            int(edge)
            for edge in edges
            if type(edge) is int and 0 <= int(edge) < n
        }
    )
    if not boundaries or boundaries[0] != 0 or deep_start not in boundaries:
        raise ValueError("fixed profile edges must begin at zero and include deep start")

    rows: list[dict[str, Any]] = []
    for position, lo in enumerate(boundaries):
        hi = boundaries[position + 1] if position + 1 < len(boundaries) else n
        count = int(counts[lo:hi].sum())
        if count == 0:
            continue
        candidate_mean = float(candidate_sums[lo:hi].sum(dtype=np.float64) / count)
        reference_mean = float(reference_sums[lo:hi].sum(dtype=np.float64) / count)
        if reference_mean <= 0.0:
            raise ValueError(f"non-positive reference annulus at [{lo}, {hi})")
        rows.append(
            {
                "lo": lo,
                "hi": hi,
                "samples": count,
                "candidate_mean": candidate_mean,
                "reference_mean": reference_mean,
                "ratio": candidate_mean / reference_mean,
                "normalised_effect": candidate_mean
                / reference_mean
                / deep_ratio
                - 1.0,
            }
        )

    safe = None
    for row_index, row in enumerate(rows):
        candidate = int(row["lo"])
        if candidate < MIN_CANDIDATE:
            continue
        if all(
            abs(float(tail["normalised_effect"])) <= threshold
            for tail in rows[row_index:]
        ):
            safe = candidate
            break
    return {
        "threshold": threshold,
        "deep_start_px": deep_start,
        "deep_ratio": deep_ratio,
        "safe_inset_px": safe,
        "censored_at_deep_start": safe == deep_start,
        "rows": rows,
    }


def retained_area(
    width: int,
    height: int,
    safe_inset: int | None,
    *,
    full_width: int = FULL_WIDTH,
    full_height: int = FULL_HEIGHT,
) -> dict[str, Any]:
    if safe_inset is None:
        retained_width = retained_height = retained_pixels = 0
    else:
        retained_width = max(0, width - 2 * safe_inset)
        retained_height = max(0, height - 2 * safe_inset)
        retained_pixels = retained_width * retained_height
    original_pixels = full_width * full_height
    fraction = retained_pixels / original_pixels
    return {
        "crop_width": width,
        "crop_height": height,
        "full_width": full_width,
        "full_height": full_height,
        "safe_inset_px_per_side": safe_inset,
        "retained_width": retained_width,
        "retained_height": retained_height,
        "retained_pixels": retained_pixels,
        "original_pixels": original_pixels,
        "retained_fraction": fraction,
        "retained_percent": 100.0 * fraction,
        "gate_fraction": RETENTION_GATE,
        "gate_pass": fraction >= RETENTION_GATE,
    }


def synthetic_profile(poison_reach: int) -> dict[str, Any]:
    """A full registered-geometry field with a controlled boundary defect."""

    height, width = 2312, 3470
    yy, xx = np.mgrid[:height, :width]
    reference = 8000.0 + 0.0625 * xx + 0.03125 * yy
    candidate = 1.1 * reference
    distance = np.minimum.reduce(
        (
            yy,
            xx,
            height - 1 - yy,
            width - 1 - xx,
        )
    )
    if poison_reach:
        candidate[distance < poison_reach] *= 1.02
    candidate_sums = np.bincount(
        distance.ravel(),
        weights=candidate.ravel(),
    )
    reference_sums = np.bincount(
        distance.ravel(),
        weights=reference.ravel(),
    )
    counts = np.bincount(distance.ravel())
    profile = fixed_profile(candidate_sums, reference_sums, counts)
    return {
        "poison_reach_px": poison_reach,
        "profile": profile,
        "retention": retained_area(width, height, profile["safe_inset_px"]),
    }


def command_commission(_: argparse.Namespace) -> int:
    null = synthetic_profile(0)
    defect = synthetic_profile(256)
    repaired = synthetic_profile(8)
    checks = {
        "null_safe_is_floor": null["profile"]["safe_inset_px"] == 8,
        "defect_safe_is_256": defect["profile"]["safe_inset_px"] == 256,
        "defect_makes_gate_red": defect["retention"]["gate_pass"] is False,
        "repaired_safe_is_floor": repaired["profile"]["safe_inset_px"] == 8,
        "repaired_makes_gate_green": repaired["retention"]["gate_pass"] is True,
        "old_fraction_reproduced": abs(
            defect["retention"]["retained_fraction"] - 0.6460471292618435
        )
        < 1e-15,
        "predicted_fraction_reproduced": abs(
            repaired["retention"]["retained_fraction"] - 0.9622496
        )
        < 5e-8,
    }
    result = {
        "schema": "m130-crop-early-profile-commission-v1",
        "milestone": "M130",
        "command": "commission",
        "instrument": {
            "threshold": THRESHOLD,
            "deep_start_px": DEEP_START,
            "edges": list(PROFILE_EDGES),
            "minimum_candidate_px": MIN_CANDIDATE,
            "retention_gate": RETENTION_GATE,
        },
        "checks": checks,
        "null": null,
        "planted_boundary_poison": defect,
        "repaired_control": repaired,
        "pass": all(checks.values()),
    }
    emit(result, getattr(_, "output", None))
    return 0 if result["pass"] else 1


def load_green(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    image = tifffile.memmap(path)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"{path}: expected HxWx3 TIFF, got {image.shape}")
    if image.dtype != np.uint16:
        raise ValueError(f"{path}: expected uint16, got {image.dtype}")
    green = np.asarray(image[:, :, 1])
    return green, {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "shape": list(image.shape),
        "dtype": str(image.dtype),
        "bytes": path.stat().st_size,
    }


def profile_result(
    b2_path: Path,
    b7_path: Path,
    *,
    expected_b2_sha: str | None = None,
    expected_b7_sha: str | None = None,
    full_width: int = FULL_WIDTH,
    full_height: int = FULL_HEIGHT,
) -> dict[str, Any]:
    b2, b2_meta = load_green(b2_path)
    b7, b7_meta = load_green(b7_path)
    if b2.shape != b7.shape:
        raise ValueError(f"shape mismatch: b2 {b2.shape}, b7 {b7.shape}")
    if expected_b2_sha and b2_meta["sha256"] != expected_b2_sha.upper():
        raise ValueError("b2 SHA-256 does not match --expected-b2-sha")
    if expected_b7_sha and b7_meta["sha256"] != expected_b7_sha.upper():
        raise ValueError("b7 SHA-256 does not match --expected-b7-sha")

    b2_sums, counts = per_distance(b2)
    b7_sums, b7_counts = per_distance(b7)
    if not np.array_equal(counts, b7_counts):
        raise AssertionError("distance partitions differ")
    profile = fixed_profile(b7_sums, b2_sums, counts)
    height, width = b2.shape
    retention = retained_area(
        width,
        height,
        profile["safe_inset_px"],
        full_width=full_width,
        full_height=full_height,
    )
    result = {
        "schema": "m130-crop-early-profile-v1",
        "milestone": "M130",
        "command": "profile",
        "b2": b2_meta,
        "b7": b7_meta,
        "profile": profile,
        "retention": retention,
        "registered_prediction": {
            "safe_inset_px_at_most": 8,
            "retained_fraction": 0.9622496,
        },
        "safe_inset_prediction_pass": (
            profile["safe_inset_px"] is not None
            and profile["safe_inset_px"] <= 8
            and not profile["censored_at_deep_start"]
        ),
        "retention_gate_pass": retention["gate_pass"],
    }
    result["pass"] = (
        result["safe_inset_prediction_pass"] and result["retention_gate_pass"]
    )
    return result


def command_profile(args: argparse.Namespace) -> int:
    result = profile_result(
        args.b2,
        args.b7,
        expected_b2_sha=args.expected_b2_sha,
        expected_b7_sha=args.expected_b7_sha,
        full_width=args.full_width,
        full_height=args.full_height,
    )
    emit(result, args.output)
    return 0 if result["pass"] else 1


def decimal_ratio(numerator: int, denominator: int) -> str:
    with localcontext() as context:
        context.prec = 40
        return format(Decimal(numerator) / Decimal(denominator), "f")


def retention_evidence(
    profile: dict[str, Any],
    *,
    crop_x: int,
    crop_y: int,
) -> dict[str, Any]:
    retention = dict(profile["retention"])
    safe = retention["safe_inset_px_per_side"]
    if safe is None:
        raise ValueError("the registered profile did not produce a safe inset")
    numerator = int(retention["retained_pixels"])
    denominator = int(retention["original_pixels"])
    retention["retained_rectangle"] = {
        "x": crop_x + safe,
        "y": crop_y + safe,
        "width": int(retention["retained_width"]),
        "height": int(retention["retained_height"]),
    }
    retention["retained_fraction_exact"] = f"{numerator}/{denominator}"
    retention["retained_fraction_decimal"] = decimal_ratio(numerator, denominator)
    return {
        "b2": profile["b2"],
        "b7": profile["b7"],
        "profile": profile["profile"],
        "retention": retention,
        "registered_prediction_pass": profile["safe_inset_prediction_pass"],
        "pixel_area_gate_pass": profile["retention_gate_pass"],
    }


def test_summary(output: str) -> dict[str, int]:
    matches = re.findall(
        r"test result: ok\. (?P<passed>\d+) passed; (?P<failed>\d+) failed; "
        r"(?P<ignored>\d+) ignored; (?P<measured>\d+) measured; "
        r"(?P<filtered>\d+) filtered out",
        output,
    )
    if not matches:
        raise ValueError("cargo test did not print a passing test summary")
    passed, failed, ignored, measured, filtered = (int(value) for value in matches[-1])
    return {
        "passed": passed,
        "failed": failed,
        "ignored": ignored,
        "measured": measured,
        "filtered_out": filtered,
    }


def clean_subprocess_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("STREHL_")
    }


def run_estimator_refusal(candidate: Path, stack: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="m130-estimator-refusal-") as temporary:
        output = Path(temporary) / "must-not-exist.tiff"
        command = [
            str(candidate.resolve()),
            "stack",
            str(stack.resolve()),
            "--merge",
            "estimator",
            "--cover",
            "crop",
            "--out",
            str(output),
        ]
        completed = subprocess.run(
            command,
            env=clean_subprocess_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        combined = completed.stdout + completed.stderr
        print(combined, file=sys.stderr, end="" if combined.endswith("\n") else "\n")
        refused = "REFUSING TO RENDER" in combined
        output_exists = output.exists()
        if completed.returncode != 1 or not refused or output_exists:
            raise RuntimeError(
                "Estimator Crop refusal control failed: "
                f"exit={completed.returncode}, refusal={refused}, "
                f"output_exists={output_exists}"
            )
        return {
            "source": "regenerated by measure.py record-results",
            "command": [
                *command[:-1],
                "<temporary-output>",
            ],
            "environment": "all inherited STREHL_* variables removed",
            "exit_code": completed.returncode,
            "refusal_text_observed": refused,
            "output_created": output_exists,
            "combined_output_sha256": artifact_io.sha256_text(combined),
        }


def run_cli_tests(repo: Path, cargo_target: Path) -> dict[str, Any]:
    if cargo_target.exists() and any(cargo_target.iterdir()):
        raise ValueError(
            f"--cargo-target must be absent or empty to prove compilation: {cargo_target}"
        )
    command = ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl"]
    environment = clean_subprocess_environment()
    environment["CARGO_TARGET_DIR"] = str(cargo_target.resolve())
    completed = subprocess.run(
        command,
        cwd=repo,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined = completed.stdout + completed.stderr
    print(combined, file=sys.stderr, end="" if combined.endswith("\n") else "\n")
    if completed.returncode != 0:
        raise RuntimeError(f"CLI unit tests exited {completed.returncode}")
    summary = test_summary(combined)
    compiled = "Compiling strehl-cli " in combined
    if not compiled:
        raise RuntimeError("fresh CLI unit-test run did not compile strehl-cli")
    return {
        "source": "regenerated by measure.py record-results",
        "command": command,
        "cwd": str(repo),
        "environment": {
            "CARGO_TARGET_DIR": str(cargo_target.resolve()),
            "inherited_strehl_variables": "removed",
        },
        "exit_code": completed.returncode,
        "compiled_strehl_cli": compiled,
        "summary": summary,
        "combined_output_sha256": artifact_io.sha256_text(combined),
    }


def rgb16_metadata(path: Path) -> dict[str, Any]:
    image = tifffile.memmap(path)
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint16:
        raise ValueError(f"{path}: expected uint16 HxWx3, got {image.shape} {image.dtype}")
    return {
        **artifact_io.file_record(path),
        "shape": list(image.shape),
        "dtype": str(image.dtype),
    }


def git_head(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


def normalise_diff(diff: dict[str, Any]) -> dict[str, Any]:
    return {
        "samples": int(diff["samples"]),
        "differing_samples": int(diff["differing"]),
        "fraction_differing": float(diff["fraction_differing"]),
        "max_dn": int(diff["max_abs_dn"]),
        "rms_dn": float(diff["rms_dn"]),
    }


def command_record_results(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    default_meta = rgb16_metadata(args.default_before)
    full_height, full_width, _ = default_meta["shape"]
    if [full_width, full_height] != [FULL_WIDTH, FULL_HEIGHT]:
        raise ValueError(
            f"default render is {full_width}x{full_height}, expected "
            f"{FULL_WIDTH}x{FULL_HEIGHT}"
        )

    old = profile_result(
        args.old_b2,
        args.old_b7,
        expected_b2_sha=args.expected_old_b2_sha,
        expected_b7_sha=args.expected_old_b7_sha,
        full_width=full_width,
        full_height=full_height,
    )
    new = profile_result(
        args.new_b2,
        args.new_b7,
        expected_b2_sha=args.expected_new_b2_sha,
        expected_b7_sha=args.expected_new_b7_sha,
        full_width=full_width,
        full_height=full_height,
    )
    crop_height, crop_width, _ = new["b2"]["shape"]
    if old["b2"]["shape"] != new["b2"]["shape"]:
        raise ValueError("old and new Crop renders have different dimensions")
    crop_x = (full_width - crop_width) // 2
    crop_y = (full_height - crop_height) // 2
    crop = {
        "x": crop_x,
        "y": crop_y,
        "width": crop_width,
        "height": crop_height,
    }
    if crop_x < 0 or crop_y < 0:
        raise ValueError("Crop dimensions exceed the full plane")

    exactness = artifact_io.read_verified_artifact(args.exactness_json.resolve())
    if exactness.get("schema") != "m130-crop-early-exactness-v1":
        raise ValueError("unexpected exactness artifact schema")
    if not exactness.get("pass"):
        raise ValueError("exactness artifact did not pass")
    comparisons = exactness["comparisons"]

    manifest = artifact_io.frame_manifest(
        args.full_stack,
        capture_identifier=args.full_stack_identifier,
        limit=args.full_stack_limit,
    )
    if manifest["frame_count"] != args.full_stack_limit:
        raise AssertionError("full-stack manifest count changed")

    refusal = run_estimator_refusal(args.candidate, args.estimator_stack)
    tests = run_cli_tests(repo, args.cargo_target)
    commission = {
        "null": synthetic_profile(0),
        "planted_boundary_poison": synthetic_profile(256),
        "repaired_control": synthetic_profile(8),
    }
    if (
        commission["planted_boundary_poison"]["profile"]["safe_inset_px"] != 256
        or commission["planted_boundary_poison"]["retention"]["gate_pass"]
        or commission["repaired_control"]["profile"]["safe_inset_px"] != 8
        or not commission["repaired_control"]["retention"]["gate_pass"]
    ):
        raise AssertionError("boundary-poison commission did not reproduce")

    old_evidence = retention_evidence(old, crop_x=crop_x, crop_y=crop_y)
    new_evidence = retention_evidence(new, crop_x=crop_x, crop_y=crop_y)
    crop_exactness = normalise_diff(comparisons["external_to_crop"])
    wrong_origin = normalise_diff(comparisons["wrong_origin_to_crop"])
    scale_control = normalise_diff(comparisons["external_to_scale_overlap"])
    pass_result = (
        old_evidence["retention"]["safe_inset_px_per_side"] == 256
        and not old_evidence["pixel_area_gate_pass"]
        and new_evidence["retention"]["safe_inset_px_per_side"] == 8
        and new_evidence["pixel_area_gate_pass"]
        and crop_exactness["differing_samples"] == 0
        and crop_exactness["max_dn"] == 0
        and crop_exactness["rms_dn"] == 0.0
        and refusal["exit_code"] == 1
        and tests["summary"]["passed"] == 121
        and tests["summary"]["failed"] == 0
    )
    if not pass_result:
        raise RuntimeError("one or more registered M130 result gates failed")

    artifact = {
        "schema": "m130-crop-early-results-v1",
        "milestone": "M130",
        "generation": {
            "source": "regenerated by measure.py record-results",
            "repository_head": git_head(repo),
            "render_production_status": (
                "manual command, not regenerated by record-results; exact commands "
                "and binary hashes are recorded in docs/research/M130-crop-early.md"
            ),
            "analysis_status": (
                "all profile, retention, exactness, refusal, test, file-hash, and "
                "capture-manifest values were regenerated by the named instruments"
            ),
        },
        "instruments": {
            "measure_py": artifact_io.file_record(Path(__file__)),
            "exactness_py": artifact_io.file_record(HERE / "exactness.py"),
            "artifact_io_py": artifact_io.file_record(HERE / "artifact_io.py"),
            "preregistration": artifact_io.file_record(HERE / "PREREGISTRATION.md"),
            "exactness_component": artifact_io.file_record(args.exactness_json),
        },
        "input_provenance": {
            "full_stack": manifest,
            "one_frame": {
                "capture_identifier": args.one_frame_identifier,
                **exactness["raw"],
            },
            "sidecars": {
                "full_stack": artifact_io.file_record(args.sidecar),
                "one_frame": artifact_io.file_record(args.one_sidecar),
            },
            "preserved_render_artifacts": {
                "default_before": default_meta,
                "old_b2": old["b2"],
                "old_b7": old["b7"],
                "new_b2": new["b2"],
                "new_b7": new["b7"],
                "direct": exactness["files"]["direct"],
                "crop": exactness["files"]["crop"],
                "scale": exactness["files"]["scale"],
            },
        },
        "geometry": {
            "units": "binned plane pixels",
            "full_plane": {
                "x": 0,
                "y": 0,
                "width": full_width,
                "height": full_height,
                "pixels": full_width * full_height,
            },
            "crop_rectangle": crop,
        },
        "border_profile": {
            "statistic": (
                "((mean green b7 / mean green b2) / deep ratio) - 1"
            ),
            "absolute_threshold": THRESHOLD,
            "deep_start_px": DEEP_START,
            "fixed_edges_px": list(PROFILE_EDGES),
            "late_crop_control": old_evidence,
            "m130_early_crop": new_evidence,
        },
        "crop_exactness": {
            "crop": crop_exactness,
            "direct_window": normalise_diff(comparisons["direct_window_to_crop"]),
            "controls": {
                "wrong_origin": wrong_origin,
                "scale": scale_control,
            },
            "crop_origin_plane_px": exactness["crop_origin_plane_px"],
        },
        "controls": {
            "boundary_poison_commission": commission,
            "estimator_crop_refusal": refusal,
            "cli_unit_tests": tests,
        },
        "registered_gate": {
            "estimand": "retained pixel area divided by original plane pixel area",
            "threshold_fraction": RETENTION_GATE,
            "late_crop_pass": old_evidence["pixel_area_gate_pass"],
            "m130_early_crop_pass": new_evidence["pixel_area_gate_pass"],
        },
        "verdict": {
            "safe_inset_prediction_pass": new_evidence[
                "registered_prediction_pass"
            ],
            "pixel_area_gate_pass": new_evidence["pixel_area_gate_pass"],
            "crop_exact": crop_exactness["differing_samples"] == 0,
            "estimator_crop_refuses": refusal["exit_code"] == 1,
            "cli_tests_pass": tests["summary"]["failed"] == 0,
            "pass": pass_result,
        },
    }
    sealed = artifact_io.write_artifact(args.output, artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output.resolve()),
                "self_sha256": sealed["integrity"]["self_sha256"],
                "safe_inset_px": new_evidence["retention"][
                    "safe_inset_px_per_side"
                ],
                "retained_fraction": new_evidence["retention"]["retained_fraction"],
                "crop_differing_samples": crop_exactness["differing_samples"],
                "estimator_exit_code": refusal["exit_code"],
                "tests_passed": tests["summary"]["passed"],
                "pass": sealed["verdict"]["pass"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_verify_results(args: argparse.Namespace) -> int:
    artifact = artifact_io.read_verified_artifact(args.input.resolve())
    artifact_io.require_keys(
        artifact,
        (
            "schema",
            "geometry",
            "border_profile",
            "crop_exactness",
            "controls",
            "verdict",
        ),
        where=str(args.input),
    )
    if artifact["schema"] != "m130-crop-early-results-v1":
        raise ValueError(f"{args.input}: unsupported schema {artifact['schema']!r}")
    old = artifact["border_profile"]["late_crop_control"]
    new = artifact["border_profile"]["m130_early_crop"]
    exact = artifact["crop_exactness"]["crop"]
    refusal = artifact["controls"]["estimator_crop_refusal"]
    tests = artifact["controls"]["cli_unit_tests"]["summary"]
    checks = {
        "old_safe_256": old["retention"]["safe_inset_px_per_side"] == 256,
        "old_gate_red": old["pixel_area_gate_pass"] is False,
        "new_safe_8": new["retention"]["safe_inset_px_per_side"] == 8,
        "new_gate_green": new["pixel_area_gate_pass"] is True,
        "crop_exact": exact["differing_samples"] == 0
        and exact["max_dn"] == 0
        and exact["rms_dn"] == 0.0,
        "estimator_refuses": refusal["exit_code"] == 1
        and refusal["output_created"] is False,
        "tests_pass": tests["passed"] == 121 and tests["failed"] == 0,
    }
    if not all(checks.values()):
        raise ValueError(f"{args.input}: result checks failed: {checks}")
    print(
        json.dumps(
            {
                "artifact": str(args.input.resolve()),
                "self_sha256": artifact["integrity"]["self_sha256"],
                "checks": checks,
                "pass": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    commands = p.add_subparsers(dest="command", required=True)
    commission = commands.add_parser("commission")
    commission.add_argument("--output", type=Path)
    commission.set_defaults(function=command_commission)
    profile = commands.add_parser("profile")
    profile.add_argument("--b2", type=Path, required=True)
    profile.add_argument("--b7", type=Path, required=True)
    profile.add_argument("--expected-b2-sha")
    profile.add_argument("--expected-b7-sha")
    profile.add_argument("--full-width", type=int, default=FULL_WIDTH)
    profile.add_argument("--full-height", type=int, default=FULL_HEIGHT)
    profile.add_argument("--output", type=Path)
    profile.set_defaults(function=command_profile)
    record = commands.add_parser("record-results")
    record.add_argument("--repo", type=Path, required=True)
    record.add_argument("--full-stack", type=Path, required=True)
    record.add_argument("--full-stack-identifier", required=True)
    record.add_argument("--full-stack-limit", type=int, required=True)
    record.add_argument("--sidecar", type=Path, required=True)
    record.add_argument("--one-sidecar", type=Path, required=True)
    record.add_argument("--one-frame-identifier", required=True)
    record.add_argument("--candidate", type=Path, required=True)
    record.add_argument("--estimator-stack", type=Path, required=True)
    record.add_argument("--cargo-target", type=Path, required=True)
    record.add_argument("--default-before", type=Path, required=True)
    record.add_argument("--old-b2", type=Path, required=True)
    record.add_argument("--old-b7", type=Path, required=True)
    record.add_argument("--new-b2", type=Path, required=True)
    record.add_argument("--new-b7", type=Path, required=True)
    record.add_argument("--expected-old-b2-sha", required=True)
    record.add_argument("--expected-old-b7-sha", required=True)
    record.add_argument("--expected-new-b2-sha", required=True)
    record.add_argument("--expected-new-b7-sha", required=True)
    record.add_argument("--exactness-json", type=Path, required=True)
    record.add_argument("--output", type=Path, default=DEFAULT_RESULTS_ARTIFACT)
    record.set_defaults(function=command_record_results)
    verify = commands.add_parser("verify-results")
    verify.add_argument("--input", type=Path, default=DEFAULT_RESULTS_ARTIFACT)
    verify.set_defaults(function=command_verify_results)
    return p


def main() -> int:
    args = parser().parse_args()
    return int(args.function(args))


if __name__ == "__main__":
    raise SystemExit(main())
