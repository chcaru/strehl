#!/usr/bin/env python3
"""Commission the M165 ProPhoto semantics gate in three counted arms."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.request

import numpy as np
import tifffile


HERE = Path(__file__).resolve().parent
STREHL_ROOT = HERE.parents[1]
REFERENCE = HERE / "reference.json"
WITNESSES = HERE / "witnesses.json"
GATE = HERE / "prophoto_gate.py"
RESULTS = HERE / "results"
OUT = HERE / "out"
FREEZE = HERE / "freeze-v1.json"
COMMISSION_SCHEMA = "m165-prophoto-semantics-commission-v1"
FREEZE_SCHEMA = "m165-prophoto-semantics-freeze-v1"
MUTATION_TARGET = b'    "linear_neutral_128_srgb8": 188,'
MUTATION_REPLACEMENT = b'    "linear_neutral_128_srgb8": 180,'
EXPECTED_PLANTED_FAILURE = "PROFILE_NUMERIC_NEUTRAL_MISMATCH"


class CommissionFailure(RuntimeError):
    def __init__(self, failure_class: str, message: str):
        super().__init__(message)
        self.failure_class = failure_class


def require(condition: bool, failure_class: str, message: str) -> None:
    if not condition:
        raise CommissionFailure(failure_class, message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(data)
    os.replace(partial, path)


def write_json(path: Path, value: Any) -> None:
    write_bytes(
        path,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True).encode("ascii")
        + b"\n",
    )


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(HERE)).replace("\\", "/"),
        "bytes": len(data),
        "sha256": sha256(data),
    }


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CommissionFailure("RESULT_READ_FAILED", f"{label}: {exc}") from exc
    if not isinstance(value, dict):
        raise CommissionFailure("RESULT_READ_FAILED", f"{label}: not an object")
    return value


def download_exact(source: dict[str, Any], destination: Path) -> None:
    request = urllib.request.Request(
        source["url"], headers={"User-Agent": "M165-prophoto-semantics/1"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = bytes(response.read())
    except (urllib.error.URLError, OSError) as exc:
        raise CommissionFailure(
            "EXTERNAL_SOURCE_DOWNLOAD_FAILED", f"{source['url']}: {exc}"
        ) from exc
    if "bytes" in source and "sha256" in source:
        require(
            len(data) == source["bytes"] and sha256(data) == source["sha256"],
            "EXTERNAL_SOURCE_IDENTITY_MISMATCH",
            f"{source['url']} returned {len(data)} bytes / {sha256(data)}",
        )
    else:
        require(
            bool(data) and source.get("identity_mode") == "live-content-anchor-gated",
            "EXTERNAL_SOURCE_IDENTITY_MISMATCH",
            f"{source['url']} returned no anchor-gated content",
        )
    write_bytes(destination, data)


def mutate_icc_gamma(profile: bytes, gamma: float) -> bytes:
    require(
        len(profile) >= 132 and profile[36:40] == b"acsp",
        "PROFILE_FIXTURE_INVALID",
        "source ICC is malformed",
    )
    encoded = round(gamma * 256.0)
    require(
        0 < encoded <= 0xFFFF,
        "PROFILE_FIXTURE_INVALID",
        "gamma is outside ICC u8Fixed8 range",
    )
    count = struct.unpack(">I", profile[128:132])[0]
    mutable = bytearray(profile)
    changed = 0
    for index in range(count):
        at = 132 + index * 12
        signature = profile[at : at + 4]
        offset, size = struct.unpack(">II", profile[at + 4 : at + 12])
        if signature not in {b"rTRC", b"gTRC", b"bTRC"}:
            continue
        require(
            offset + size <= len(profile)
            and size >= 14
            and profile[offset : offset + 4] == b"curv"
            and struct.unpack(">I", profile[offset + 8 : offset + 12])[0] == 1,
            "PROFILE_FIXTURE_INVALID",
            f"{signature!r} is not a one-value gamma curve",
        )
        mutable[offset + 12 : offset + 14] = struct.pack(">H", encoded)
        changed += 1
    require(
        changed == 3,
        "PROFILE_FIXTURE_INVALID",
        f"expected three TRCs, changed {changed}",
    )
    return bytes(mutable)


def fixture_pixels() -> np.ndarray:
    height, width = 96, 128
    y, x = np.indices((height, width), dtype=np.uint32)
    red = (x * 257 + y * 911 + ((x ^ y) * 37)) & 0xFFFF
    green = (x * 149 + y * 613 + ((x * y) % 4093) * 7) & 0xFFFF
    blue = (x * 997 + y * 83 + ((x + 3 * y) % 257) * 131) & 0xFFFF
    return np.stack((red, green, blue), axis=2).astype(np.uint16)


def write_tifffile_fixture(path: Path, pixels: np.ndarray, icc: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.unlink(missing_ok=True)
    tifffile.imwrite(
        partial,
        pixels,
        byteorder="<",
        photometric="rgb",
        planarconfig="contig",
        rowsperstrip=pixels.shape[0],
        compression=None,
        iccprofile=icc,
        metadata=None,
        software=False,
        datetime=False,
    )
    os.replace(partial, path)


def prepare_inputs(reference: dict[str, Any]) -> dict[str, Any]:
    sources_dir = OUT / "sources"
    external_paths = {
        "libraw_colorconst": sources_dir / "colorconst-0.22.1.cpp",
        "libraw_postprocessing": sources_dir
        / "postprocessing_utils_dcrdefs-0.22.1.cpp",
        "romm_registry": sources_dir / "romm-registry.html",
        "zerene_color_management": sources_dir / "zerene-color-management.html",
    }
    for source_id, destination in external_paths.items():
        download_exact(reference["external_sources"][source_id], destination)

    profile_path = STREHL_ROOT / reference["artifacts"]["linear_profile"]["path"]
    try:
        linear_profile = bytes(profile_path.read_bytes())
    except OSError as exc:
        raise CommissionFailure("PROFILE_FIXTURE_INVALID", str(exc)) from exc
    require(
        len(linear_profile) == reference["artifacts"]["linear_profile"]["bytes"]
        and sha256(linear_profile)
        == reference["artifacts"]["linear_profile"]["sha256"],
        "PROFILE_FIXTURE_INVALID",
        "source linear profile identity drifted",
    )
    gamma18_profile = mutate_icc_gamma(linear_profile, 1.8)
    pixels = fixture_pixels()
    shifted_pixels = pixels.copy()
    shifted_pixels[:, :, 0] ^= np.uint16(0x4000)
    fixture_dir = OUT / "fixtures"
    linear_input = fixture_dir / "fork-input-gamma1.tiff"
    gamma18_input = fixture_dir / "fork-input-gamma18.tiff"
    shifted_input = fixture_dir / "fork-input-pixel-shift.tiff"
    write_tifffile_fixture(linear_input, pixels, linear_profile)
    write_tifffile_fixture(gamma18_input, pixels, gamma18_profile)
    write_tifffile_fixture(shifted_input, shifted_pixels, linear_profile)

    development_tiff = (
        STREHL_ROOT
        / "experiments/M165-fork-rebuild/commissioning/full/input/development-common.tiff"
    )
    if development_tiff.is_file():
        audited_tiff = development_tiff
        tiff_origin = "development-common"
    else:
        audited_tiff = fixture_dir / "audited-common-fallback.tiff"
        write_tifffile_fixture(audited_tiff, pixels, linear_profile)
        tiff_origin = "tifffile-fixture"

    return {
        "external_paths": external_paths,
        "linear_input": linear_input,
        "gamma18_input": gamma18_input,
        "shifted_input": shifted_input,
        "audited_tiff": audited_tiff,
        "tiff_origin": tiff_origin,
        "linear_profile_sha256": sha256(linear_profile),
        "gamma18_profile_sha256": sha256(gamma18_profile),
        "pixel_sha256": sha256(np.ascontiguousarray(pixels).tobytes()),
        "shifted_pixel_sha256": sha256(
            np.ascontiguousarray(shifted_pixels).tobytes()
        ),
    }


def gate_command(
    reference_path: Path,
    result_path: Path,
    run_label: str,
    prepared: dict[str, Any],
) -> list[str]:
    external = prepared["external_paths"]
    return [
        sys.executable,
        str(GATE),
        "--reference",
        str(reference_path),
        "--witnesses",
        str(WITNESSES),
        "--output",
        str(result_path),
        "--run-label",
        run_label,
        "--libraw-source",
        str(external["libraw_postprocessing"]),
        "--libraw-colorconst",
        str(external["libraw_colorconst"]),
        "--romm-registry",
        str(external["romm_registry"]),
        "--zerene-doc",
        str(external["zerene_color_management"]),
        "--tiff",
        str(prepared["audited_tiff"]),
        "--tiff-origin",
        prepared["tiff_origin"],
        "--fork-input-linear",
        str(prepared["linear_input"]),
        "--fork-input-gamma18",
        str(prepared["gamma18_input"]),
        "--fork-input-shifted",
        str(prepared["shifted_input"]),
        "--out-root",
        str(OUT),
    ]


def run_gate(
    reference_path: Path,
    result_path: Path,
    run_label: str,
    prepared: dict[str, Any],
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any], list[str]]:
    command = gate_command(reference_path, result_path, run_label, prepared)
    result_path.unlink(missing_ok=True)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=HERE,
        )
    except OSError as exc:
        raise CommissionFailure("GATE_EXECUTION_FAILED", str(exc)) from exc
    require(
        result_path.is_file(),
        "GATE_RESULT_ABSENT",
        f"{run_label} gate did not write {result_path}",
    )
    return completed, read_json(result_path, run_label), command


def arm_record(result: dict[str, Any], arm: str) -> dict[str, Any]:
    matches = [
        record for record in result["arm_partition"] if record["arm"] == arm
    ]
    require(
        len(matches) == 1,
        "COMMISSION_PARTITION_INVALID",
        f"{result.get('run_label')}: arm {arm!r} count is {len(matches)}",
    )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    try:
        reference_bytes = bytes(REFERENCE.read_bytes())
        reference = json.loads(reference_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CommissionFailure("REFERENCE_READ_FAILED", str(exc)) from exc
    require(
        isinstance(reference, dict)
        and reference.get("schema") == "m165-prophoto-semantics-reference-v1",
        "REFERENCE_SCHEMA_MISMATCH",
        "reference schema is not pinned",
    )
    target_count = reference_bytes.splitlines().count(MUTATION_TARGET)
    require(
        target_count == 1,
        "MUTATION_TARGET_COUNT",
        f"planted full-line target count is {target_count}, expected 1",
    )
    require(
        reference_bytes.splitlines().count(MUTATION_REPLACEMENT) == 0,
        "MUTATION_REPLACEMENT_PREEXISTS",
        "planted replacement already exists in baseline reference",
    )

    prepared = prepare_inputs(reference)
    RESULTS.mkdir(parents=True, exist_ok=True)

    baseline_path = RESULTS / "baseline.json"
    baseline_run, baseline, baseline_command = run_gate(
        REFERENCE, baseline_path, "baseline", prepared
    )
    require(
        baseline_run.returncode == 0
        and baseline.get("status") == "PASS"
        and baseline.get("headline_verdict") == "PROPHOTO_DISPROVED"
        and baseline["check_partition"]["RED"] == 0,
        "BASELINE_GATE_FAILED",
        f"baseline exit {baseline_run.returncode}: "
        f"{baseline_run.stdout[-1000:]} {baseline_run.stderr[-1000:]}",
    )
    baseline_bytes = bytes(baseline_path.read_bytes())
    baseline_repeat_path = OUT / "baseline-repeat.json"
    baseline_repeat_run, baseline_repeat, _ = run_gate(
        REFERENCE, baseline_repeat_path, "baseline", prepared
    )
    baseline_repeat_bytes = bytes(baseline_repeat_path.read_bytes())
    require(
        baseline_repeat_run.returncode == 0
        and baseline_repeat.get("status") == "PASS"
        and baseline_repeat_bytes == baseline_bytes,
        "BASELINE_NOT_BYTE_DETERMINISTIC",
        "two same-input baseline executions did not produce byte-identical evidence",
    )

    mutated_reference = reference_bytes.replace(
        MUTATION_TARGET, MUTATION_REPLACEMENT
    )
    require(
        mutated_reference != reference_bytes
        and mutated_reference.splitlines().count(MUTATION_REPLACEMENT) == 1,
        "MUTATION_APPLICATION_FAILED",
        "planted mutation was not unique",
    )
    mutated_path = OUT / "mutated-reference.json"
    write_bytes(mutated_path, mutated_reference)
    degraded_path = RESULTS / "degraded.json"
    degraded_run, degraded, degraded_command = run_gate(
        mutated_path, degraded_path, "planted-degradation", prepared
    )
    degraded_red = [
        check for check in degraded["checks"] if check["status"] == "RED"
    ]
    require(
        degraded_run.returncode != 0
        and degraded.get("status") == "FAIL"
        and degraded.get("headline_verdict") == "INDETERMINATE"
        and len(degraded_red) == 1
        and degraded_red[0]["id"] == "PROFILE_NUMERIC_NEUTRAL"
        and degraded_red[0]["failure_class"] == EXPECTED_PLANTED_FAILURE
        and degraded.get("failure_classes") == [EXPECTED_PLANTED_FAILURE],
        "PLANTED_DEGRADATION_WRONG_FAILURE",
        f"degraded gate did not isolate {EXPECTED_PLANTED_FAILURE}",
    )
    degraded_tiff_arm = arm_record(degraded, "TIFF_STORAGE")
    require(
        degraded_tiff_arm["RED"] == 0 and degraded_tiff_arm["PASS"] == 1,
        "PLANTED_DEGRADATION_SPILLED",
        "unrelated TIFF_STORAGE arm did not stay green",
    )

    repaired_path = OUT / "repaired-reference.json"
    write_bytes(repaired_path, reference_bytes)
    repaired_bytes = bytes(repaired_path.read_bytes())
    baseline_reference_sha = sha256(reference_bytes)
    repaired_reference_sha = sha256(repaired_bytes)
    require(
        repaired_bytes == reference_bytes
        and repaired_reference_sha == baseline_reference_sha,
        "REPAIR_NOT_EXACT",
        "repaired reference bytes/hash do not reproduce baseline",
    )
    improvement_path = RESULTS / "improvement.json"
    improvement_run, improvement, improvement_command = run_gate(
        repaired_path, improvement_path, "planted-improvement", prepared
    )
    require(
        improvement_run.returncode == 0
        and improvement.get("status") == "PASS"
        and improvement.get("headline_verdict") == "PROPHOTO_DISPROVED"
        and improvement["check_partition"] == baseline["check_partition"],
        "PLANTED_IMPROVEMENT_FAILED",
        f"improvement exit {improvement_run.returncode}: "
        f"{improvement_run.stdout[-1000:]} {improvement_run.stderr[-1000:]}",
    )

    phase_counts = {
        "BASELINE_PASS": 1,
        "BASELINE_REPEAT_BYTE_IDENTICAL": 1,
        "PLANTED_DEGRADATION_RED": 1,
        "PLANTED_IMPROVEMENT_PASS": 1,
    }
    phase_total = sum(phase_counts.values())
    commission = {
        "schema": COMMISSION_SCHEMA,
        "status": "PASS",
        "headline_verdict": "PROPHOTO_DISPROVED",
        "scope": "input-contract-only-not-quality-comparison",
        "planted_failure_class": EXPECTED_PLANTED_FAILURE,
        "mutation": {
            "kind": "unique-full-line-reference-mutation",
            "target_count": target_count,
            "baseline_line": MUTATION_TARGET.decode("ascii"),
            "degraded_line": MUTATION_REPLACEMENT.decode("ascii"),
            "baseline_reference_sha256": baseline_reference_sha,
            "degraded_reference_sha256": sha256(mutated_reference),
            "repaired_reference_sha256": repaired_reference_sha,
            "repair_bytes_equal_baseline": repaired_bytes == reference_bytes,
            "label": "PLANTED_IMPROVEMENT",
        },
        "fixture": {
            "audited_tiff": str(prepared["audited_tiff"].resolve()),
            "audited_tiff_origin": prepared["tiff_origin"],
            "fork_input_linear": str(prepared["linear_input"].resolve()),
            "fork_input_gamma18": str(prepared["gamma18_input"].resolve()),
            "fork_input_shifted": str(prepared["shifted_input"].resolve()),
            "linear_profile_sha256": prepared["linear_profile_sha256"],
            "gamma18_profile_sha256": prepared["gamma18_profile_sha256"],
            "identical_input_pixel_sha256": prepared["pixel_sha256"],
            "shifted_input_pixel_sha256": prepared["shifted_pixel_sha256"],
        },
        "phase_partition": {
            "counts": phase_counts,
            "total": phase_total,
            "sum": phase_total,
            "sum_matches_total": True,
        },
        "runs": {
            "baseline": {
                "command": baseline_command,
                "exit_code": baseline_run.returncode,
                "result": str(baseline_path.resolve()),
                "check_partition": baseline["check_partition"],
                "arm_partition": baseline["arm_partition"],
            },
            "degraded": {
                "command": degraded_command,
                "exit_code": degraded_run.returncode,
                "result": str(degraded_path.resolve()),
                "check_partition": degraded["check_partition"],
                "arm_partition": degraded["arm_partition"],
                "red_checks": degraded_red,
                "unrelated_tiff_storage_arm": degraded_tiff_arm,
            },
            "improvement": {
                "command": improvement_command,
                "exit_code": improvement_run.returncode,
                "result": str(improvement_path.resolve()),
                "check_partition": improvement["check_partition"],
                "arm_partition": improvement["arm_partition"],
            },
        },
        "movement": {
            "baseline_to_degraded": {
                "pass_delta": degraded["check_partition"]["PASS"]
                - baseline["check_partition"]["PASS"],
                "red_delta": degraded["check_partition"]["RED"]
                - baseline["check_partition"]["RED"],
            },
            "degraded_to_planted_improvement": {
                "pass_delta": improvement["check_partition"]["PASS"]
                - degraded["check_partition"]["PASS"],
                "red_delta": improvement["check_partition"]["RED"]
                - degraded["check_partition"]["RED"],
                "returned_to_baseline_partition": improvement["check_partition"]
                == baseline["check_partition"],
            },
        },
        "determinism": {
            "same_input_baseline_run_count": 2,
            "byte_identical": baseline_repeat_bytes == baseline_bytes,
            "baseline_result_sha256": sha256(baseline_bytes),
            "repeat_result_sha256": sha256(baseline_repeat_bytes),
        },
        "consumer_partition": baseline["evidence"]["consumer_partition"],
    }
    write_json(RESULTS / "commission.json", commission)
    freeze = {
        "schema": FREEZE_SCHEMA,
        "status": "FROZEN",
        "scope": "input-contract-only-not-quality-comparison",
        "headline_verdict": "PROPHOTO_DISPROVED",
        "sources": [
            file_record(GATE),
            file_record(Path(__file__).resolve()),
            file_record(REFERENCE),
            file_record(WITNESSES),
        ],
        "results": [
            file_record(RESULTS / name)
            for name in (
                "baseline.json",
                "degraded.json",
                "improvement.json",
                "commission.json",
            )
        ],
    }
    write_json(FREEZE, freeze)
    print(
        json.dumps(
            {
                "status": "PASS",
                "headline_verdict": commission["headline_verdict"],
                "planted_failure_class": EXPECTED_PLANTED_FAILURE,
                "baseline_partition": baseline["check_partition"],
                "degraded_partition": degraded["check_partition"],
                "improvement_partition": improvement["check_partition"],
                "consumer_partition": commission["consumer_partition"]["counts"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
