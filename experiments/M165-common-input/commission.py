#!/usr/bin/env python3
"""Commission the M165 converter, pattern probe, and Rust identity adapter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

import converter


def run_verifier(
    verifier: Path,
    tiff: Path,
    report: Path,
    expected: dict[str, str],
    exercise_core_merge: bool = False,
) -> dict[str, object]:
    command = [
        str(verifier),
        "--tiff",
        str(tiff),
        "--report",
        str(report),
        "--file-sha256",
        expected["file_sha256"],
        "--pixel-sha256",
        expected["pixel_payload_sha256"],
        "--icc-sha256",
        expected["icc_sha256"],
        "--source-sha256",
        expected["source_sha256"],
        "--converter-sha256",
        expected["converter_sha256"],
        "--settings-sha256",
        expected["settings_sha256"],
        "--pattern-map-sha256",
        expected["pattern_map_sha256"],
        "--pattern-manifest-sha256",
        expected["pattern_manifest_sha256"],
    ]
    if exercise_core_merge:
        command.append("--exercise-core-merge")
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    try:
        parsed = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parsed = {"status": "FAIL", "reason": f"unreadable verifier report: {exc}"}
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "report": parsed,
    }


def pattern_probe() -> dict[str, object]:
    yy, xx = np.mgrid[0:8, 0:10]
    colors = ((yy & 1) * 2 + (xx & 1)).astype(np.uint8)
    black = [512.0] * 4
    white = [15360.0] * 4
    truth_signal = 3000.0 + xx * 37.0 + yy * 19.0
    offset = ((xx % 3) - 1).astype(np.float64) * 5.0
    gain = 1.0 + ((yy % 4) - 1.5) * 0.002
    observed = 512.0 + truth_signal / gain + offset
    truth = np.rint(512.0 + truth_signal).astype(np.uint16)
    zeros = np.zeros_like(observed)
    ones = np.ones_like(observed)

    null = converter.apply_pattern_correction(observed, colors, black, white, ones, zeros)
    improved = converter.apply_pattern_correction(
        observed, colors, black, white, gain, offset
    )
    degraded = converter.apply_pattern_correction(
        observed, colors, black, white, 1.0 / gain, -offset
    )

    def mae(value: np.ndarray) -> float:
        return float(np.mean(np.abs(value.astype(np.float64) - truth.astype(np.float64))))

    null_mae = mae(null)
    improvement_mae = mae(improved)
    degradation_mae = mae(degraded)
    passed = (
        null_mae > 0.0
        and improvement_mae < null_mae
        and degradation_mae > null_mae
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "movable_null": {
            "undisturbed_mae_dn": 0.0,
            "disturbed_uncorrected_mae_dn": null_mae,
        },
        "planted_improvement": {
            "correct_map_mae_dn": improvement_mae,
            "direction_correct": improvement_mae < null_mae,
        },
        "planted_degradation": {
            "wrong_map_mae_dn": degradation_mae,
            "direction_correct": degradation_mae > null_mae,
        },
    }


def consumer_registry_probe(out: Path) -> dict[str, object]:
    fixture_dir = out / "consumer-fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    build_manifest = fixture_dir / "source-build-manifest.json"
    converter.write_json(
        build_manifest,
        {
            "schema": "m165-synthetic-consumer-build-v1",
            "source_revision": "0000000000000000000000000000000000000001",
            "command": ["synthetic-build"],
        },
    )
    input_contract = {
        "kind": "exact-common-tiff-bytes",
        "file_sha256_from": "input_manifest.output.file_sha256",
        "pixel_sha256_from": "input_manifest.output.pixel_payload_sha256",
    }
    binaries: list[Path] = []
    consumers: list[dict[str, object]] = []
    for index in range(4):
        binary = fixture_dir / f"consumer-{index + 1}.bin"
        binary.write_bytes(f"M165 synthetic consumer {index + 1}\n".encode("ascii"))
        binaries.append(binary)
        registry_binary_path = str(Path("consumer-fixtures") / binary.name)
        settings = {"mode": f"synthetic-{index + 1}", "workers": index + 1}
        consumer: dict[str, object] = {
            "consumer_id": f"synthetic-consumer-{index + 1}",
            "role": "candidate" if index == 0 else "comparator",
            "required": True,
            "status": "FROZEN",
            "implementation_kind": "source-build" if index == 3 else "installed-binary",
            "version": "commission-v1",
            "executable_path": registry_binary_path,
            "executable_bytes": binary.stat().st_size,
            "executable_sha256": converter.hash_file(binary),
            "source_revision": (
                "0000000000000000000000000000000000000001" if index == 3 else None
            ),
            "build_manifest_path": (
                str(Path("consumer-fixtures") / build_manifest.name)
                if index == 3
                else None
            ),
            "build_manifest_sha256": (
                converter.hash_file(build_manifest) if index == 3 else None
            ),
            "settings": settings,
            "settings_sha256": converter.hash_bytes(converter.canonical_json(settings)),
            "invocation_template": [registry_binary_path, "{input_tiff}"],
            "input_contract": input_contract,
        }
        consumers.append(consumer)

    four_path = out / "consumer-registry-four.json"
    four = {
        "schema": converter.CONSUMER_REGISTRY_SCHEMA,
        "status": "FROZEN",
        "track": "common-merge",
        "registry_id": "m165-synthetic-cardinality-probe",
        "version": "1",
        "consumers": consumers,
    }
    converter.write_json(four_path, four)
    four_summary = converter.validate_consumer_registry(four_path)
    four_sha = converter.hash_file(four_path)

    three_path = out / "consumer-registry-three.json"
    three = {
        **four,
        "consumers": consumers[:3],
    }
    converter.write_json(three_path, three)
    three_summary = converter.validate_consumer_registry(three_path)
    three_sha = converter.hash_file(three_path)

    no_required_path = out / "consumer-registry-no-required.json"
    no_required = {
        **three,
        "registry_id": "m165-synthetic-no-required-consumers",
        "consumers": [{**consumer, "required": False} for consumer in consumers[:3]],
    }
    converter.write_json(no_required_path, no_required)
    try:
        converter.validate_consumer_registry(no_required_path)
    except converter.ContractFailure as exc:
        no_required_result = {
            "status": "FAIL",
            "failure_class": exc.failure_class,
            "reason": str(exc),
        }
    else:
        no_required_result = {
            "status": "UNEXPECTED_PASS",
            "failure_class": None,
            "reason": None,
        }

    original = binaries[3].read_bytes()
    changed = bytearray(original)
    changed[0] ^= 0x01
    binaries[3].write_bytes(changed)
    try:
        converter.validate_consumer_registry(four_path)
    except converter.ContractFailure as exc:
        degradation = {
            "status": "FAIL",
            "failure_class": exc.failure_class,
            "reason": str(exc),
        }
    else:
        degradation = {
            "status": "UNEXPECTED_PASS",
            "failure_class": None,
            "reason": None,
        }
    finally:
        binaries[3].write_bytes(original)

    repaired_summary = converter.validate_consumer_registry(four_path)
    checks = {
        "three_consumers_pass": three_summary["consumer_count"] == 3,
        "four_consumers_pass": four_summary["consumer_count"] == 4,
        "fourth_consumer_moves_registry_hash": three_sha != four_sha,
        "no_required_consumers_fail": no_required_result["failure_class"]
        == "CONSUMER_REGISTRY_NO_REQUIRED_CONSUMERS",
        "binary_mutation_fails": degradation["failure_class"]
        == "CONSUMER_EXECUTABLE_HASH_MISMATCH",
        "binary_restoration_passes": repaired_summary["consumer_count"] == 4,
        "fourth_consumer_is_source_build": four_summary["consumers"][3][
            "implementation_kind"
        ]
        == "source-build",
        "fourth_consumer_has_first_class_executable_hash": len(
            str(four_summary["consumers"][3]["executable_sha256"])
        )
        == 64,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "three_consumer_registry": {
            "path": str(three_path.resolve()),
            "sha256": three_sha,
            "summary": three_summary,
        },
        "four_consumer_registry": {
            "path": str(four_path.resolve()),
            "sha256": four_sha,
            "summary": four_summary,
        },
        "no_required_consumers": no_required_result,
        "planted_degradation": degradation,
        "planted_improvement": {
            "status": "PASS",
            "summary": repaired_summary,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--icc", required=True)
    parser.add_argument("--freeze", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    verifier = Path(args.verifier).resolve()
    icc_path = Path(args.icc).resolve()
    source_sha = converter.hash_bytes(b"M165 deterministic synthetic source")
    freeze = converter.load_json(Path(args.freeze), "converter freeze")
    converter_sha = freeze["converter"]["executable_bundle_sha256"]
    provenance = {
        "schema": "m165-common-input-provenance-v1",
        "source_sha256": source_sha,
        "converter_executable_sha256": converter_sha,
        "settings_sha256": freeze["converter"]["bundle_members"]["settings_sha256"],
        "icc_sha256": converter.hash_file(icc_path),
        "pattern_map_sha256": converter.hash_bytes(b"synthetic pattern map"),
        "pattern_manifest_sha256": converter.hash_bytes(b"synthetic pattern manifest"),
    }
    yy, xx = np.mgrid[0:5, 0:7]
    rgb = np.stack(
        [
            1000 + 31 * xx + 7 * yy,
            2000 + 17 * xx + 11 * yy,
            3000 + 13 * xx + 19 * yy,
        ],
        axis=2,
    ).astype(np.uint16)
    baseline_path = out / "identity-baseline.tiff"
    layout = converter.write_common_tiff(
        baseline_path, rgb, icc_path.read_bytes(), provenance
    )
    expected = {
        "file_sha256": layout["file_sha256"],
        "pixel_payload_sha256": layout["pixel_payload_sha256"],
        "icc_sha256": layout["icc_sha256"],
        "source_sha256": source_sha,
        "converter_sha256": provenance["converter_executable_sha256"],
        "settings_sha256": provenance["settings_sha256"],
        "pattern_map_sha256": provenance["pattern_map_sha256"],
        "pattern_manifest_sha256": provenance["pattern_manifest_sha256"],
    }
    baseline = run_verifier(
        verifier,
        baseline_path,
        out / "identity-baseline.json",
        expected,
        exercise_core_merge=True,
    )

    bitflip_path = out / "identity-bitflip.tiff"
    shutil.copyfile(baseline_path, bitflip_path)
    bitflip = bytearray(bitflip_path.read_bytes())
    inert_at = int(layout["inert_padding_offset"])
    bitflip[inert_at] ^= 0x01
    bitflip_path.write_bytes(bitflip)
    bitflip_inspection = converter.inspect_common_tiff(bitflip_path)
    bitflip_result = run_verifier(
        verifier, bitflip_path, out / "identity-bitflip.json", expected
    )

    lsb_path = out / "identity-one-lsb.tiff"
    shutil.copyfile(baseline_path, lsb_path)
    lsb = bytearray(lsb_path.read_bytes())
    pixel_at = int(layout["strip_offset"])
    original = int.from_bytes(lsb[pixel_at : pixel_at + 2], "little")
    changed = original + 1 if original < 65535 else original - 1
    lsb[pixel_at : pixel_at + 2] = changed.to_bytes(2, "little")
    lsb_path.write_bytes(lsb)
    lsb_inspection = converter.inspect_common_tiff(lsb_path)
    lsb_result = run_verifier(verifier, lsb_path, out / "identity-one-lsb.json", expected)

    repaired_path = out / "identity-repaired.tiff"
    shutil.copyfile(baseline_path, repaired_path)
    repaired = run_verifier(
        verifier, repaired_path, out / "identity-repaired.json", expected
    )

    malformed_path = out / "identity-malformed.tiff"
    malformed_path.write_bytes(b"not a TIFF")
    malformed = run_verifier(
        verifier, malformed_path, out / "identity-malformed.json", expected
    )

    pattern = pattern_probe()
    consumers = consumer_registry_probe(out)
    checks = {
        "baseline_passes": baseline["exit_code"] == 0
        and baseline["report"].get("status") == "PASS",
        "actual_core_merge_exercised": baseline["report"].get("core_merge_exercised")
        is True,
        "metadata_bitflip_fails": bitflip_result["exit_code"] != 0
        and bitflip_result["report"].get("status") == "FAIL",
        "metadata_bitflip_preserves_pixel_hash": bitflip_inspection[
            "pixel_payload_sha256"
        ]
        == expected["pixel_payload_sha256"],
        "metadata_bitflip_moves_file_hash": bitflip_inspection["file_sha256"]
        != expected["file_sha256"],
        "one_lsb_fails": lsb_result["exit_code"] != 0
        and lsb_result["report"].get("status") == "FAIL",
        "one_lsb_moves_pixel_hash": lsb_inspection["pixel_payload_sha256"]
        != expected["pixel_payload_sha256"],
        "repaired_passes": repaired["exit_code"] == 0
        and repaired["report"].get("status") == "PASS",
        "malformed_degrades_to_fail": malformed["exit_code"] != 0
        and malformed["report"].get("status") == "FAIL",
        "pattern_probe_passes": pattern["status"] == "PASS",
        "consumer_registry_probe_passes": consumers["status"] == "PASS",
    }
    report = {
        "schema": "m165-common-input-commission-v2",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "working_directory": str(Path.cwd()),
        "complete_invocation": [
            sys.executable,
            str(Path(__file__).resolve()),
        ]
        + sys.argv[1:],
        "verifier": {
            "path": str(verifier),
            "sha256": converter.hash_file(verifier),
        },
        "checks": checks,
        "expected_identity": expected,
        "baseline": baseline,
        "metadata_bitflip": {
            "mutation": {
                "byte_offset": inert_at,
                "xor_mask": 1,
            },
            "file_sha256": bitflip_inspection["file_sha256"],
            "pixel_payload_sha256": bitflip_inspection["pixel_payload_sha256"],
            "verifier": bitflip_result,
        },
        "one_lsb": {
            "mutation": {
                "byte_offset": pixel_at,
                "sample_before": original,
                "sample_after": changed,
            },
            "file_sha256": lsb_inspection["file_sha256"],
            "pixel_payload_sha256": lsb_inspection["pixel_payload_sha256"],
            "verifier": lsb_result,
        },
        "repaired_improvement": repaired,
        "malformed_input": malformed,
        "pattern_correction_probe": pattern,
        "consumer_registry_probe": consumers,
    }
    converter.write_json(out / "commission.json", report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
