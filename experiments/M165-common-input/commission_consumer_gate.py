#!/usr/bin/env python3
"""Commission the M165 consumer-boundary evidence gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

import consumer_gate
import converter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", required=True)
    parser.add_argument("--fixture-consumer", required=True)
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--icc", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def bundle_member(label: str, path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "label": label,
        "path": str(path.resolve()),
        "bytes": len(data),
        "sha256": consumer_gate.hash_bytes(data),
    }


def bundle_hash(members: list[dict[str, object]]) -> str:
    portable = [
        {
            "label": member["label"],
            "bytes": member["bytes"],
            "sha256": member["sha256"],
        }
        for member in members
    ]
    return consumer_gate.hash_bytes(consumer_gate.canonical_json(portable))


def frozen_consumer(
    consumer_id: str,
    role: str,
    executable: Path,
    members: list[dict[str, object]],
    settings: dict[str, object],
    invocation: list[str],
    attestation_schemas: list[str],
) -> dict[str, object]:
    executable_bytes = executable.read_bytes()
    return {
        "consumer_id": consumer_id,
        "role": role,
        "required": True,
        "status": "FROZEN",
        "implementation_kind": "script-runtime-bundle",
        "version": "commission-v1",
        "executable_path": str(executable.resolve()),
        "executable_bytes": len(executable_bytes),
        "executable_sha256": consumer_gate.hash_bytes(executable_bytes),
        "executable_bundle": members,
        "executable_bundle_sha256": bundle_hash(members),
        "source_revision": None,
        "build_manifest_path": None,
        "build_manifest_sha256": None,
        "settings": settings,
        "settings_sha256": consumer_gate.hash_bytes(
            consumer_gate.canonical_json(settings)
        ),
        "invocation_template": invocation,
        "input_contract": {
            "kind": "exact-common-tiff-bytes",
            "file_sha256_from": "input_manifest.output.file_sha256",
            "pixel_sha256_from": "input_manifest.output.pixel_payload_sha256",
        },
        "attestation_schemas": attestation_schemas,
    }


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def replace_unique_full_line(path: Path, target: str, replacement: str) -> bytes:
    original = path.read_bytes()
    text = original.decode("utf-8")
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line == target]
    if len(matches) != 1:
        raise RuntimeError(
            f"mutation anchor must match one full line, matched {len(matches)}: {target!r}"
        )
    lines[matches[0]] = replacement
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return original


def build_input(
    out: Path,
    input_id: str,
    width: int,
    height: int,
    registry_sha256: str,
    icc: bytes,
) -> tuple[Path, dict[str, str]]:
    yy, xx = np.mgrid[0:height, 0:width]
    seed = sum(input_id.encode("ascii"))
    rgb = np.stack(
        [
            1000 + seed + 17 * xx + 7 * yy,
            2000 + seed + 13 * xx + 11 * yy,
            3000 + seed + 19 * xx + 5 * yy,
        ],
        axis=2,
    ).astype(np.uint16)
    source_sha = consumer_gate.hash_bytes(f"{input_id}:source".encode("ascii"))
    converter_sha = consumer_gate.hash_bytes(b"commissioning converter bundle")
    settings_sha = consumer_gate.hash_bytes(b"commissioning converter settings")
    map_sha = consumer_gate.hash_bytes(f"{input_id}:map".encode("ascii"))
    pattern_manifest_sha = consumer_gate.hash_bytes(
        f"{input_id}:pattern-manifest".encode("ascii")
    )
    provenance = {
        "schema": "m165-common-input-provenance-v1",
        "source_sha256": source_sha,
        "converter_executable_sha256": converter_sha,
        "settings_sha256": settings_sha,
        "icc_sha256": consumer_gate.hash_bytes(icc),
        "pattern_map_sha256": map_sha,
        "pattern_manifest_sha256": pattern_manifest_sha,
    }
    tiff_path = out / "inputs" / f"{input_id}.tiff"
    layout = converter.write_common_tiff(tiff_path, rgb, icc, provenance)
    manifest = {
        "schema": consumer_gate.INPUT_MANIFEST_SCHEMA,
        "status": "RENDERED",
        "track": "common-merge",
        "source": {"sha256": source_sha},
        "converter": {
            "executable_sha256": converter_sha,
            "settings_sha256": settings_sha,
        },
        "pattern_map": {
            "sha256": map_sha,
            "manifest_sha256": pattern_manifest_sha,
        },
        "consumer_registry": {"sha256": registry_sha256},
        "output": {
            "path": str(tiff_path.resolve()),
            "width": layout["width"],
            "height": layout["height"],
            "file_sha256": layout["file_sha256"],
            "pixel_payload_sha256": layout["pixel_payload_sha256"],
            "icc_sha256": layout["icc_sha256"],
        },
    }
    manifest_path = out / "inputs" / f"{input_id}.manifest.json"
    consumer_gate.write_json(manifest_path, manifest)
    return manifest_path, provenance


def main() -> int:
    args = parse_args()
    gate_path = Path(args.gate).resolve()
    fixture_path = Path(args.fixture_consumer).resolve()
    verifier = Path(args.verifier).resolve()
    freeze_path = Path(args.freeze).resolve()
    icc_path = Path(args.icc).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    receipts = out / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)

    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    python = Path(sys.executable).resolve()
    synthetic_members = [
        bundle_member("python-executable", python),
        bundle_member("consumer-fixture-script", fixture_path),
        bundle_member("consumer-gate-script", gate_path),
    ]
    strehl_members = [bundle_member("strehl-common-input", verifier)]
    synthetic_invocation = [
        str(python),
        str(fixture_path),
        "--consumer-id",
        "{consumer_id}",
        "--input",
        "{input_tiff}",
        "--output",
        "{output_path}",
        "--attestation",
        "{attestation_path}",
    ]
    strehl_invocation = [
        str(verifier),
        "--tiff",
        "{input_tiff}",
        "--report",
        "{attestation_path}",
        "--file-sha256",
        "{file_sha256}",
        "--pixel-sha256",
        "{pixel_payload_sha256}",
        "--icc-sha256",
        "{icc_sha256}",
        "--source-sha256",
        "{source_sha256}",
        "--converter-sha256",
        "{converter_sha256}",
        "--settings-sha256",
        "{settings_sha256}",
        "--pattern-map-sha256",
        "{pattern_map_sha256}",
        "--pattern-manifest-sha256",
        "{pattern_manifest_sha256}",
        "--exercise-core-merge",
    ]
    consumers = [
        frozen_consumer(
            "strehl",
            "candidate",
            verifier,
            strehl_members,
            {"mode": "common-input-identity", "core_merge": True},
            strehl_invocation,
            [consumer_gate.STREHL_ATTESTATION_SCHEMA],
        )
    ]
    for consumer_id, mode in (
        ("zerene-pmax-fixture", "PMax"),
        ("zerene-dmap-fixture", "DMap"),
        ("fork-fixture", "best-known-source"),
    ):
        consumers.append(
            frozen_consumer(
                consumer_id,
                "comparator",
                python,
                synthetic_members,
                {"commissioning_only": True, "mode": mode},
                synthetic_invocation,
                [consumer_gate.STANDARD_ATTESTATION_SCHEMA],
            )
        )
    consumers.append(
        {
            "consumer_id": "helicon-optional-fixture",
            "role": "optional-comparator",
            "required": False,
            "status": "BLOCKED_NOT_INSTALLED",
            "implementation_kind": "installed-binary",
            "version": None,
            "executable_path": None,
            "executable_bytes": None,
            "executable_sha256": None,
            "executable_bundle": [],
            "executable_bundle_sha256": None,
            "settings": {},
            "settings_sha256": None,
            "invocation_template": [],
            "input_contract": {
                "kind": "exact-common-tiff-bytes",
                "file_sha256_from": "input_manifest.output.file_sha256",
                "pixel_sha256_from": "input_manifest.output.pixel_payload_sha256",
            },
            "attestation_schemas": [],
            "blocker": (
                "Optional Helicon is deliberately absent in this commissioning "
                "fixture; optional absence must be counted without failing required inputs."
            ),
        }
    )
    registry = {
        "schema": consumer_gate.CONSUMER_REGISTRY_SCHEMA,
        "status": "FROZEN",
        "track": "common-merge",
        "registry_id": "m165-consumer-gate-commission",
        "version": "1",
        "consumers": consumers,
    }
    registry_path = out / "consumer-registry.json"
    consumer_gate.write_json(registry_path, registry)
    registry_sha = consumer_gate.hash_bytes(registry_path.read_bytes())

    icc = icc_path.read_bytes()
    input_specs = [("input-a", 7, 5), ("input-b", 9, 6)]
    manifest_paths: dict[str, Path] = {}
    provenances: dict[str, dict[str, str]] = {}
    campaign_inputs: list[dict[str, str]] = []
    for input_id, width, height in input_specs:
        manifest_path, provenance = build_input(
            out, input_id, width, height, registry_sha, icc
        )
        manifest_paths[input_id] = manifest_path
        provenances[input_id] = provenance
        campaign_inputs.append(
            {
                "input_id": input_id,
                "manifest_path": str(manifest_path.resolve()),
                "manifest_sha256": consumer_gate.hash_bytes(manifest_path.read_bytes()),
            }
        )

    campaign = {
        "schema": consumer_gate.CAMPAIGN_SCHEMA,
        "status": "FROZEN",
        "track": "common-merge",
        "campaign_id": "m165-consumer-gate-commission",
        "consumer_gate_bundle_sha256": freeze["consumer_gate_bundle_sha256"],
        "consumer_registry_sha256": registry_sha,
        "inputs": campaign_inputs,
    }
    campaign_path = out / "campaign.json"
    consumer_gate.write_json(campaign_path, campaign)

    runs: list[dict[str, object]] = []
    for input_id, _, _ in input_specs:
        manifest = json.loads(manifest_paths[input_id].read_text(encoding="utf-8"))
        tiff_path = Path(manifest["output"]["path"])
        provenance = provenances[input_id]

        strehl_dir = receipts / "strehl"
        strehl_dir.mkdir(parents=True, exist_ok=True)
        strehl_attestation = out / "attestations" / "strehl" / f"{input_id}.json"
        strehl_command = [
            str(verifier),
            "--tiff",
            str(tiff_path),
            "--report",
            str(strehl_attestation),
            "--file-sha256",
            manifest["output"]["file_sha256"],
            "--pixel-sha256",
            manifest["output"]["pixel_payload_sha256"],
            "--icc-sha256",
            manifest["output"]["icc_sha256"],
            "--source-sha256",
            provenance["source_sha256"],
            "--converter-sha256",
            provenance["converter_executable_sha256"],
            "--settings-sha256",
            provenance["settings_sha256"],
            "--pattern-map-sha256",
            provenance["pattern_map_sha256"],
            "--pattern-manifest-sha256",
            provenance["pattern_manifest_sha256"],
            "--exercise-core-merge",
        ]
        strehl_attestation.parent.mkdir(parents=True, exist_ok=True)
        completed = run(strehl_command)
        if completed.returncode != 0:
            raise RuntimeError(
                f"Strehl fixture failed for {input_id}: {completed.stderr}"
            )
        strehl_receipt = consumer_gate.make_receipt(
            campaign_path,
            registry_path,
            freeze_path,
            "strehl",
            input_id,
            strehl_attestation,
            strehl_command,
            [strehl_attestation],
        )
        consumer_gate.write_json(strehl_dir / f"{input_id}.json", strehl_receipt)
        runs.append(
            {
                "consumer_id": "strehl",
                "input_id": input_id,
                "exit_code": completed.returncode,
                "attestation_sha256": consumer_gate.hash_bytes(
                    strehl_attestation.read_bytes()
                ),
            }
        )

        for consumer_id in (
            "zerene-pmax-fixture",
            "zerene-dmap-fixture",
            "fork-fixture",
        ):
            consumer_dir = receipts / consumer_id
            consumer_dir.mkdir(parents=True, exist_ok=True)
            output_path = out / "outputs" / consumer_id / f"{input_id}.json"
            attestation_path = (
                out / "attestations" / consumer_id / f"{input_id}.json"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            attestation_path.parent.mkdir(parents=True, exist_ok=True)
            command = [
                str(python),
                str(fixture_path),
                "--consumer-id",
                consumer_id,
                "--input",
                str(tiff_path),
                "--output",
                str(output_path),
                "--attestation",
                str(attestation_path),
            ]
            completed = run(command)
            if completed.returncode != 0:
                raise RuntimeError(
                    f"{consumer_id} fixture failed for {input_id}: {completed.stderr}"
                )
            receipt = consumer_gate.make_receipt(
                campaign_path,
                registry_path,
                freeze_path,
                consumer_id,
                input_id,
                attestation_path,
                command,
                [output_path, attestation_path],
            )
            consumer_gate.write_json(consumer_dir / f"{input_id}.json", receipt)
            runs.append(
                {
                    "consumer_id": consumer_id,
                    "input_id": input_id,
                    "exit_code": completed.returncode,
                    "attestation_sha256": consumer_gate.hash_bytes(
                        attestation_path.read_bytes()
                    ),
                }
            )

    record_source = receipts / "zerene-pmax-fixture" / "input-a.json"
    record_source_value = json.loads(record_source.read_text(encoding="utf-8"))
    record_invocation_path = out / "record-cli-invocation.json"
    consumer_gate.write_json(
        record_invocation_path, record_source_value["complete_invocation"]
    )
    record_cli_path = out / "record-cli-receipt.json"
    record_command = [
        str(python),
        str(gate_path),
        "record",
        "--campaign",
        str(campaign_path),
        "--registry",
        str(registry_path),
        "--freeze",
        str(freeze_path),
        "--consumer-id",
        "zerene-pmax-fixture",
        "--input-id",
        "input-a",
        "--attestation",
        str(out / "attestations" / "zerene-pmax-fixture" / "input-a.json"),
        "--invocation-json",
        str(record_invocation_path),
        "--output",
        str(out / "outputs" / "zerene-pmax-fixture" / "input-a.json"),
        "--output",
        str(out / "attestations" / "zerene-pmax-fixture" / "input-a.json"),
        "--out",
        str(record_cli_path),
    ]
    record_completed = run(record_command)
    record_cli_matches_library = (
        record_completed.returncode == 0
        and record_cli_path.read_bytes() == record_source.read_bytes()
    )

    baseline = consumer_gate.verify_campaign(
        campaign_path, registry_path, freeze_path, receipts
    )
    baseline_path = out / "baseline-gate.json"
    consumer_gate.write_json(baseline_path, baseline)

    cross_consumer_receipt = receipts / "zerene-dmap-fixture" / "input-a.json"
    cross_consumer_original = cross_consumer_receipt.read_bytes()
    cross_consumer_value = json.loads(cross_consumer_original)
    wrong_attestation = (
        out / "attestations" / "zerene-pmax-fixture" / "input-a.json"
    )
    cross_consumer_value["consumer_attestation"] = {
        "path": str(wrong_attestation),
        "sha256": consumer_gate.hash_bytes(wrong_attestation.read_bytes()),
        "schema": consumer_gate.STANDARD_ATTESTATION_SCHEMA,
    }
    consumer_gate.write_json(cross_consumer_receipt, cross_consumer_value)
    cross_consumer = consumer_gate.verify_campaign(
        campaign_path, registry_path, freeze_path, receipts
    )
    cross_consumer_path = out / "cross-consumer-gate.json"
    consumer_gate.write_json(cross_consumer_path, cross_consumer)
    cross_consumer_receipt.write_bytes(cross_consumer_original)
    cross_consumer_failure = next(
        pair
        for pair in cross_consumer["pairs"]
        if pair["consumer_id"] == "zerene-dmap-fixture"
        and pair["input_id"] == "input-a"
    )

    blocked_registry = json.loads(json.dumps(registry))
    blocked_registry["status"] = "BLOCKED"
    for consumer in blocked_registry["consumers"]:
        if consumer["required"]:
            consumer["status"] = "BLOCKED_COMMISSION_PROBE"
            consumer["blocker"] = (
                "Commissioning probe: required consumer deliberately unavailable."
            )
    blocked_registry_path = out / "blocked-registry.json"
    consumer_gate.write_json(blocked_registry_path, blocked_registry)
    blocked_registry_sha = consumer_gate.hash_bytes(blocked_registry_path.read_bytes())
    blocked_inputs: list[dict[str, str]] = []
    for input_id, _, _ in input_specs:
        blocked_manifest = json.loads(
            manifest_paths[input_id].read_text(encoding="utf-8")
        )
        blocked_manifest["consumer_registry"]["sha256"] = blocked_registry_sha
        blocked_manifest_path = out / "blocked-inputs" / f"{input_id}.manifest.json"
        consumer_gate.write_json(blocked_manifest_path, blocked_manifest)
        blocked_inputs.append(
            {
                "input_id": input_id,
                "manifest_path": str(blocked_manifest_path.resolve()),
                "manifest_sha256": consumer_gate.hash_bytes(
                    blocked_manifest_path.read_bytes()
                ),
            }
        )
    blocked_campaign = {
        **campaign,
        "campaign_id": "m165-consumer-gate-blocked-probe",
        "consumer_registry_sha256": blocked_registry_sha,
        "inputs": blocked_inputs,
    }
    blocked_campaign_path = out / "blocked-campaign.json"
    consumer_gate.write_json(blocked_campaign_path, blocked_campaign)
    blocked_receipts = out / "blocked-receipts"
    blocked_receipts.mkdir(parents=True, exist_ok=True)
    blocked = consumer_gate.verify_campaign(
        blocked_campaign_path,
        blocked_registry_path,
        freeze_path,
        blocked_receipts,
    )
    blocked_path = out / "blocked-gate.json"
    consumer_gate.write_json(blocked_path, blocked)

    mutation_receipt = receipts / "zerene-pmax-fixture" / "input-a.json"
    input_a_manifest = json.loads(
        manifest_paths["input-a"].read_text(encoding="utf-8")
    )
    input_a_sha = input_a_manifest["output"]["file_sha256"]
    target_line = f'  "input_file_sha256": "{input_a_sha}",'
    replacement_line = f'  "input_file_sha256": "{"0" * 64}",'
    missing_anchor_hard_error = False
    try:
        replace_unique_full_line(
            mutation_receipt,
            '  "input_file_sha256": "this-line-does-not-exist",',
            replacement_line,
        )
    except RuntimeError:
        missing_anchor_hard_error = True
    original_receipt = replace_unique_full_line(
        mutation_receipt, target_line, replacement_line
    )
    mutated = consumer_gate.verify_campaign(
        campaign_path, registry_path, freeze_path, receipts
    )
    mutated_path = out / "mutated-gate.json"
    consumer_gate.write_json(mutated_path, mutated)
    mutation_receipt.write_bytes(original_receipt)

    repaired = consumer_gate.verify_campaign(
        campaign_path, registry_path, freeze_path, receipts
    )
    repaired_path = out / "repaired-gate.json"
    consumer_gate.write_json(repaired_path, repaired)

    missing_receipt = receipts / "fork-fixture" / "input-b.json"
    missing_bytes = missing_receipt.read_bytes()
    missing_receipt.unlink()
    missing = consumer_gate.verify_campaign(
        campaign_path, registry_path, freeze_path, receipts
    )
    missing_path = out / "missing-gate.json"
    consumer_gate.write_json(missing_path, missing)
    missing_receipt.write_bytes(missing_bytes)

    malformed_campaign = out / "malformed-campaign.json.invalid"
    malformed_campaign.write_text("{", encoding="utf-8", newline="\n")
    malformed_report = out / "malformed-gate.json"
    malformed_command = [
        str(python),
        str(gate_path),
        "verify",
        "--campaign",
        str(malformed_campaign),
        "--registry",
        str(registry_path),
        "--freeze",
        str(freeze_path),
        "--receipts",
        str(receipts),
        "--out",
        str(malformed_report),
    ]
    malformed_completed = run(malformed_command)
    malformed = json.loads(malformed_report.read_text(encoding="utf-8"))

    baseline_required = baseline["summary"]["required_consumer_input_pairs"]
    baseline_optional = baseline["summary"]["optional_consumer_input_pairs"]
    cross_consumer_required = cross_consumer["summary"][
        "required_consumer_input_pairs"
    ]
    mutated_required = mutated["summary"]["required_consumer_input_pairs"]
    missing_required = missing["summary"]["required_consumer_input_pairs"]
    blocked_required = blocked["summary"]["required_consumer_input_pairs"]
    checks = {
        "baseline_passes": baseline["status"] == "PASS",
        "baseline_partitions_two_inputs": baseline["summary"]["inputs"]
        == {
            "total_examined": 2,
            "counts": {"PASS": 2, "FAIL": 0, "MISSING": 0, "BLOCKED": 0},
            "counted_sum": 2,
            "partition_balanced": True,
        },
        "baseline_partitions_eight_required_pairs": baseline_required[
            "total_examined"
        ]
        == 8
        and baseline_required["counts"]["PASS"] == 8
        and baseline_required["partition_balanced"],
        "optional_absence_counted_not_skipped": baseline_optional["total_examined"]
        == 2
        and baseline_optional["counts"]["OPTIONAL_ABSENT"] == 2
        and baseline_optional["partition_balanced"],
        "required_blockers_are_counted": blocked["status"] == "FAIL"
        and blocked["summary"]["inputs"]["counts"]["BLOCKED"] == 2
        and blocked_required["counts"]["BLOCKED"] == 8
        and blocked_required["partition_balanced"],
        "all_artifacts_read_at_most_once": baseline["artifact_read_audit"][
            "all_artifacts_read_at_most_once"
        ],
        "cross_consumer_attestation_rejected": cross_consumer["status"] == "FAIL"
        and cross_consumer_failure.get("failure_class")
        == "ATTESTATION_CONSUMER_MISMATCH"
        and cross_consumer_required["counts"]["FAIL"] == 1
        and cross_consumer_required["counts"]["PASS"] == 7
        and cross_consumer_required["partition_balanced"],
        "missing_mutation_anchor_hard_errors": missing_anchor_hard_error,
        "unique_full_line_hash_mutation_goes_red": mutated["status"] == "FAIL"
        and mutated_required["counts"]["FAIL"] == 1
        and mutated_required["counts"]["PASS"] == 7
        and mutated_required["partition_balanced"],
        "repair_goes_green": repaired["status"] == "PASS",
        "missing_receipt_is_counted": missing["status"] == "FAIL"
        and missing_required["counts"]["MISSING"] == 1
        and missing_required["counts"]["PASS"] == 7
        and missing_required["partition_balanced"],
        "record_cli_matches_library_byte_for_byte": record_cli_matches_library,
        "malformed_input_persists_fail": malformed_completed.returncode != 0
        and malformed.get("status") == "FAIL"
        and malformed_report.is_file(),
    }
    report = {
        "schema": "m165-common-input-consumer-gate-commission-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "hash_contract": baseline["hash_contract"],
        "gate_freeze": {
            "path": str(freeze_path),
            "sha256": consumer_gate.hash_bytes(freeze_path.read_bytes()),
            "bundle_sha256": freeze["consumer_gate_bundle_sha256"],
        },
        "registry": {
            "path": str(registry_path),
            "sha256": registry_sha,
            "required_consumers": 4,
            "optional_consumers": 1,
        },
        "campaign": {
            "path": str(campaign_path),
            "sha256": consumer_gate.hash_bytes(campaign_path.read_bytes()),
            "inputs": 2,
        },
        "runs": runs,
        "record_cli_probe": {
            "exit_code": record_completed.returncode,
            "receipt_path": str(record_cli_path),
            "receipt_sha256": consumer_gate.hash_bytes(record_cli_path.read_bytes()),
            "library_receipt_path": str(record_source),
            "library_receipt_sha256": consumer_gate.hash_bytes(
                record_source.read_bytes()
            ),
            "byte_identical": record_cli_matches_library,
        },
        "required_blocker_probe": {
            "path": str(blocked_path),
            "sha256": consumer_gate.hash_bytes(blocked_path.read_bytes()),
            "summary": blocked["summary"],
        },
        "baseline": {
            "path": str(baseline_path),
            "sha256": consumer_gate.hash_bytes(baseline_path.read_bytes()),
            "summary": baseline["summary"],
        },
        "cross_consumer_attestation_probe": {
            "failure_class": cross_consumer_failure.get("failure_class"),
            "path": str(cross_consumer_path),
            "sha256": consumer_gate.hash_bytes(cross_consumer_path.read_bytes()),
            "summary": cross_consumer["summary"],
        },
        "planted_degradation": {
            "mutation": {
                "path": str(mutation_receipt),
                "unique_full_line_before": target_line,
                "unique_full_line_after": replacement_line,
            },
            "path": str(mutated_path),
            "sha256": consumer_gate.hash_bytes(mutated_path.read_bytes()),
            "summary": mutated["summary"],
        },
        "planted_improvement": {
            "action": "restore the exact original receipt bytes",
            "path": str(repaired_path),
            "sha256": consumer_gate.hash_bytes(repaired_path.read_bytes()),
            "summary": repaired["summary"],
        },
        "missing_receipt_probe": {
            "path": str(missing_path),
            "sha256": consumer_gate.hash_bytes(missing_path.read_bytes()),
            "summary": missing["summary"],
        },
        "malformed_input_probe": {
            "exit_code": malformed_completed.returncode,
            "path": str(malformed_report),
            "sha256": consumer_gate.hash_bytes(malformed_report.read_bytes()),
            "failure_class": malformed.get("failure_class"),
        },
    }
    consumer_gate.write_json(out / "commission.json", report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
