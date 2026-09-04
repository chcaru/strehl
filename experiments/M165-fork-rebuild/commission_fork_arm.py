#!/usr/bin/env python3
"""Commission the rebuilt focus-stack arm against the Stage 0C boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
COMMON = HERE.parent / "M165-common-input"
sys.path.insert(0, str(COMMON))

import consumer_gate  # noqa: E402
import converter  # noqa: E402


COMMISSION_SCHEMA = "m165-fork-consumer-commission-v1"
FORK_COMMIT = "4bc7f95e448cf20ee2bdd758403ec43e2612a1c6"


class CommissionFailure(RuntimeError):
    def __init__(self, failure_class: str, message: str):
        super().__init__(message)
        self.failure_class = failure_class


def require(condition: bool, failure_class: str, message: str) -> None:
    if not condition:
        raise CommissionFailure(failure_class, message)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "JSON_INVALID", f"{path} is not an object")
    return value


def file_record(label: str, path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "label": label,
        "path": str(path.resolve()),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def bundle_hash(members: list[dict[str, Any]]) -> str:
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
    *,
    consumer_id: str,
    role: str,
    executable: Path,
    members: list[dict[str, Any]],
    version: str,
    implementation_kind: str,
    settings: dict[str, Any],
    invocation_template: list[str],
    attestation_schemas: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    executable_record = file_record("primary executable", executable)
    value: dict[str, Any] = {
        "consumer_id": consumer_id,
        "role": role,
        "required": True,
        "status": "FROZEN",
        "implementation_kind": implementation_kind,
        "version": version,
        "executable_path": executable_record["path"],
        "executable_bytes": executable_record["bytes"],
        "executable_sha256": executable_record["sha256"],
        "executable_bundle": members,
        "executable_bundle_sha256": bundle_hash(members),
        "settings": settings,
        "settings_sha256": consumer_gate.hash_bytes(
            consumer_gate.canonical_json(settings)
        ),
        "invocation_template": invocation_template,
        "input_contract": {
            "kind": "exact-common-tiff-bytes",
            "file_sha256_from": "input_manifest.output.file_sha256",
            "pixel_sha256_from": "input_manifest.output.pixel_payload_sha256",
        },
        "attestation_schemas": attestation_schemas,
    }
    if extra:
        value.update(extra)
    return value


def blocked_consumer(consumer_id: str, mode: str) -> dict[str, Any]:
    return {
        "consumer_id": consumer_id,
        "role": "comparator",
        "required": True,
        "status": "BLOCKED_LICENSE_EXPIRED",
        "implementation_kind": "installed-binary",
        "version": "1.04T2026-05-04-0750",
        "attestation_schemas": [],
        "blocker": (
            f"Licensed Zerene {mode} is required. The installed trial expired "
            "2026-06-06, so it cannot emit an admissible consumer receipt."
        ),
    }


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def replace_unique_full_line(path: Path, target: str, replacement: str) -> bytes:
    original = path.read_bytes()
    lines = original.decode("utf-8").splitlines()
    matches = [index for index, line in enumerate(lines) if line == target]
    if len(matches) != 1:
        raise CommissionFailure(
            "MUTATION_ANCHOR_INVALID",
            f"mutation anchor matched {len(matches)} full lines: {target!r}",
        )
    lines[matches[0]] = replacement
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return original


def write_fixture_files(out: Path) -> dict[str, str]:
    source = {
        "schema": "m165-fork-development-source-v1",
        "status": "DEVELOPMENT_ONLY_SYNTHETIC",
        "purpose": "consumer admission, not quality measurement",
        "dimensions": [128, 96],
    }
    source_path = out / "fixture" / "source.json"
    consumer_gate.write_json(source_path, source)
    map_path = out / "fixture" / "pattern-map.bin"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_bytes(bytes((index * 29 + 7) & 0xFF for index in range(256)))
    map_manifest = {
        "schema": "m165-fork-development-pattern-map-v1",
        "status": "DEVELOPMENT_ONLY_SYNTHETIC",
        "map_sha256": consumer_gate.hash_bytes(map_path.read_bytes()),
        "eligibility": "never score",
    }
    map_manifest_path = out / "fixture" / "pattern-map.json"
    consumer_gate.write_json(map_manifest_path, map_manifest)
    return {
        "source_sha256": consumer_gate.hash_bytes(source_path.read_bytes()),
        "pattern_map_sha256": consumer_gate.hash_bytes(map_path.read_bytes()),
        "pattern_manifest_sha256": consumer_gate.hash_bytes(
            map_manifest_path.read_bytes()
        ),
    }


def write_input(
    *,
    out: Path,
    registry_sha256: str,
    converter_freeze: dict[str, Any],
    icc: bytes,
    fixture_hashes: dict[str, str],
    tiff_path: Path | None = None,
    manifest_name: str,
) -> tuple[Path, dict[str, Any]]:
    height, width = 96, 128
    yy, xx = np.mgrid[0:height, 0:width]
    rgb = np.stack(
        [
            (4000 + 30000 * ((xx // 8 + yy // 8) % 2) + xx * 83 + yy * 31)
            % 65536,
            (8000 + 25000 * ((xx // 16) % 2) + xx * 47 + yy * 97) % 65536,
            (12000 + 20000 * ((yy // 12) % 2) + xx * 113 + yy * 43) % 65536,
        ],
        axis=2,
    ).astype(np.uint16)
    converter_sha = converter_freeze["converter"]["executable_bundle_sha256"]
    settings_sha = converter_freeze["converter"]["bundle_members"]["settings_sha256"]
    provenance = {
        "schema": "m165-common-input-provenance-v1",
        "source_sha256": fixture_hashes["source_sha256"],
        "converter_executable_sha256": converter_sha,
        "settings_sha256": settings_sha,
        "icc_sha256": consumer_gate.hash_bytes(icc),
        "pattern_map_sha256": fixture_hashes["pattern_map_sha256"],
        "pattern_manifest_sha256": fixture_hashes["pattern_manifest_sha256"],
    }
    if tiff_path is None:
        tiff_path = out / "input" / "development-common.tiff"
        layout = converter.write_common_tiff(tiff_path, rgb, icc, provenance)
    else:
        layout = consumer_gate.inspect_tiff_bytes(tiff_path.read_bytes())
    manifest = {
        "schema": consumer_gate.INPUT_MANIFEST_SCHEMA,
        "status": "RENDERED",
        "track": "common-merge",
        "eligibility": "DEVELOPMENT_ONLY_SYNTHETIC_NEVER_SCORE",
        "source": {"sha256": fixture_hashes["source_sha256"]},
        "converter": {
            "executable_sha256": converter_sha,
            "settings_sha256": settings_sha,
        },
        "pattern_map": {
            "sha256": fixture_hashes["pattern_map_sha256"],
            "manifest_sha256": fixture_hashes["pattern_manifest_sha256"],
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
    manifest_path = out / "input" / manifest_name
    consumer_gate.write_json(manifest_path, manifest)
    return manifest_path, provenance


def write_campaign(
    *,
    path: Path,
    campaign_id: str,
    gate_freeze: dict[str, Any],
    registry_sha256: str,
    manifest_path: Path,
) -> None:
    consumer_gate.write_json(
        path,
        {
            "schema": consumer_gate.CAMPAIGN_SCHEMA,
            "status": "FROZEN",
            "track": "common-merge",
            "campaign_id": campaign_id,
            "consumer_gate_bundle_sha256": gate_freeze[
                "consumer_gate_bundle_sha256"
            ],
            "consumer_registry_sha256": registry_sha256,
            "inputs": [
                {
                    "input_id": "development-common",
                    "manifest_path": str(manifest_path.resolve()),
                    "manifest_sha256": consumer_gate.hash_bytes(
                        manifest_path.read_bytes()
                    ),
                }
            ],
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", required=True)
    parser.add_argument("--gate-freeze", required=True)
    parser.add_argument("--converter-freeze", required=True)
    parser.add_argument("--strehl-verifier", required=True)
    parser.add_argument("--fork-adapter", required=True)
    parser.add_argument("--fork-build-freeze", required=True)
    parser.add_argument("--source-pin", required=True)
    parser.add_argument("--icc", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def commission(args: argparse.Namespace) -> dict[str, Any]:
    gate_path = Path(args.gate).resolve()
    gate_freeze_path = Path(args.gate_freeze).resolve()
    converter_freeze_path = Path(args.converter_freeze).resolve()
    strehl_source = Path(args.strehl_verifier).resolve()
    adapter = Path(args.fork_adapter).resolve()
    build_freeze_path = Path(args.fork_build_freeze).resolve()
    source_pin_path = Path(args.source_pin).resolve()
    icc_path = Path(args.icc).resolve()
    out = Path(args.out).resolve()
    require(
        HERE in out.parents,
        "OUTPUT_SCOPE_INVALID",
        "commissioning output must remain under experiments/M165-fork-rebuild",
    )
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    strehl = HERE / "bin" / "strehl-common-input.exe"
    strehl.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(strehl_source, strehl)

    gate_freeze = read_json(gate_freeze_path)
    converter_freeze = read_json(converter_freeze_path)
    build_freeze = read_json(build_freeze_path)
    source_pin = read_json(source_pin_path)
    require(
        gate_path == Path(consumer_gate.__file__).resolve(),
        "GATE_PATH_MISMATCH",
        "--gate does not name the imported Stage 0C implementation",
    )
    require(
        build_freeze.get("status") == "FROZEN"
        and build_freeze.get("source", {}).get("commit_sha1") == FORK_COMMIT
        and build_freeze.get("reproducibility", {}).get("byte_identical") is True,
        "FORK_BUILD_NOT_FROZEN",
        "fork build freeze is absent, wrong-revision, or not byte-reproducible",
    )
    require(
        build_freeze.get("freeze_order", {}).get(
            "executable_hash_recorded_before_rendering"
        )
        is True,
        "FORK_FREEZE_ORDER_INVALID",
        "fork executable was not frozen before rendering",
    )
    require(
        source_pin.get("status") == "FROZEN"
        and source_pin.get("commit", {}).get("resolved") == FORK_COMMIT,
        "FORK_SOURCE_NOT_FROZEN",
        "fork source pin is absent or names the wrong revision",
    )

    python = Path(sys.executable).resolve()
    fork_executable = Path(build_freeze["frozen_executable"]["path"]).resolve()
    fork_sha = build_freeze["frozen_executable"]["sha256"]
    require(
        file_record("focus-stack.exe", fork_executable)["sha256"] == fork_sha,
        "FORK_EXECUTABLE_HASH_MISMATCH",
        "current fork executable differs from the pre-render freeze",
    )

    strehl_members = [file_record("strehl-common-input.exe", strehl)]
    strehl_settings = {"mode": "common-input-identity", "core_merge": True}
    strehl_template = [
        str(strehl),
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
    strehl_consumer = frozen_consumer(
        consumer_id="strehl",
        role="candidate",
        executable=strehl,
        members=strehl_members,
        version="development-build",
        implementation_kind="native-executable",
        settings=strehl_settings,
        invocation_template=strehl_template,
        attestation_schemas=[consumer_gate.STREHL_ATTESTATION_SCHEMA],
    )

    fork_members = [
        file_record(item["label"], Path(item["path"]))
        for item in build_freeze["dependencies"]["runtime_bundle"]
    ]
    fork_members.extend(
        [
            file_record("python-executable", python),
            file_record("fork-consumer-adapter", adapter),
            file_record("fork-build-freeze", build_freeze_path),
            file_record("fork-source-pin", source_pin_path),
        ]
    )
    fork_settings = {
        "development_only": True,
        "quality_comparison": False,
        "input_path_occurrences": 2,
        "input_colorspace": "none",
        "output_colorspace": "srgb",
        "output_bitdepth": 16,
        "threads": 1,
        "batchsize": 2,
        "opencl": False,
        "alignment": "none",
        "whitebalance_matching": False,
        "contrast_matching": False,
        "consistency": 0,
        "denoise": 0,
        "known_color_limitation": (
            "Pinned source has no ProPhoto input mode. Integer TIFFs bypass its "
            "input color conversion, and the embedded ICC is not interpreted."
        ),
    }
    fork_template = [
        str(python),
        str(adapter),
        "--consumer-id",
        "focus-stack-fork",
        "--executable",
        str(fork_executable),
        "--executable-sha256",
        fork_sha,
        "--input",
        "{input_tiff}",
        "--output",
        "{output_path}",
        "--attestation",
        "{attestation_path}",
    ]
    fork_consumer = frozen_consumer(
        consumer_id="focus-stack-fork",
        role="comparator",
        executable=fork_executable,
        members=fork_members,
        version=FORK_COMMIT,
        implementation_kind="reproducible-source-build-with-locked-adapter",
        settings=fork_settings,
        invocation_template=fork_template,
        attestation_schemas=[consumer_gate.STANDARD_ATTESTATION_SCHEMA],
        extra={
            "source_revision": FORK_COMMIT,
            "source_tree_sha1": build_freeze["source"]["tree_sha1"],
            "source_manifest_sha256": build_freeze["source"]["manifest_sha256"],
            "build_manifest_path": str(build_freeze_path),
            "build_manifest_sha256": consumer_gate.hash_bytes(
                build_freeze_path.read_bytes()
            ),
        },
    )

    full_registry = {
        "schema": consumer_gate.CONSUMER_REGISTRY_SCHEMA,
        "status": "BLOCKED",
        "track": "common-merge",
        "registry_id": "m165-real-consumer-roster-development",
        "version": "1",
        "consumers": [
            strehl_consumer,
            blocked_consumer("zerene-pmax", "PMax"),
            blocked_consumer("zerene-dmap", "DMap"),
            fork_consumer,
            {
                "consumer_id": "helicon-focus",
                "role": "optional-comparator",
                "required": False,
                "status": "OPTIONAL_ABSENT",
                "implementation_kind": "installed-binary",
                "version": None,
                "attestation_schemas": [],
                "blocker": (
                    "No local Helicon installation is present. The live scorecard "
                    "counts this as optional absence."
                ),
            },
        ],
    }
    full_registry_path = out / "full" / "consumer-registry.json"
    consumer_gate.write_json(full_registry_path, full_registry)
    full_registry_sha = consumer_gate.hash_bytes(full_registry_path.read_bytes())

    arm_registry = {
        "schema": consumer_gate.CONSUMER_REGISTRY_SCHEMA,
        "status": "FROZEN",
        "track": "common-merge",
        "registry_id": "m165-fork-arm-commission",
        "version": "1",
        "commissioning_scope": "focus-stack-fork only; never a scorecard roster",
        "consumers": [fork_consumer],
    }
    arm_registry_path = out / "fork-arm" / "consumer-registry.json"
    consumer_gate.write_json(arm_registry_path, arm_registry)
    arm_registry_sha = consumer_gate.hash_bytes(arm_registry_path.read_bytes())

    fixture_hashes = write_fixture_files(out)
    icc = icc_path.read_bytes()
    full_manifest_path, provenance = write_input(
        out=out / "full",
        registry_sha256=full_registry_sha,
        converter_freeze=converter_freeze,
        icc=icc,
        fixture_hashes=fixture_hashes,
        manifest_name="development-common.manifest.json",
    )
    full_manifest = read_json(full_manifest_path)
    tiff_path = Path(full_manifest["output"]["path"])
    arm_manifest_path, _ = write_input(
        out=out / "fork-arm",
        registry_sha256=arm_registry_sha,
        converter_freeze=converter_freeze,
        icc=icc,
        fixture_hashes=fixture_hashes,
        tiff_path=tiff_path,
        manifest_name="development-common.manifest.json",
    )

    full_campaign_path = out / "full" / "campaign.json"
    write_campaign(
        path=full_campaign_path,
        campaign_id="m165-real-consumer-roster-development",
        gate_freeze=gate_freeze,
        registry_sha256=full_registry_sha,
        manifest_path=full_manifest_path,
    )
    arm_campaign_path = out / "fork-arm" / "campaign.json"
    write_campaign(
        path=arm_campaign_path,
        campaign_id="m165-fork-arm-commission",
        gate_freeze=gate_freeze,
        registry_sha256=arm_registry_sha,
        manifest_path=arm_manifest_path,
    )

    full_receipts = out / "full" / "receipts"
    strehl_attestation = out / "full" / "attestations" / "strehl.json"
    strehl_attestation.parent.mkdir(parents=True, exist_ok=True)
    strehl_command = [
        str(strehl),
        "--tiff",
        str(tiff_path),
        "--report",
        str(strehl_attestation),
        "--file-sha256",
        full_manifest["output"]["file_sha256"],
        "--pixel-sha256",
        full_manifest["output"]["pixel_payload_sha256"],
        "--icc-sha256",
        full_manifest["output"]["icc_sha256"],
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
    strehl_run = run(strehl_command)
    require(
        strehl_run.returncode == 0,
        "STREHL_CONSUMER_FAILED",
        f"Strehl identity verifier failed: {strehl_run.stderr[-1000:]}",
    )
    strehl_receipt = consumer_gate.make_receipt(
        full_campaign_path,
        full_registry_path,
        gate_freeze_path,
        "strehl",
        "development-common",
        strehl_attestation,
        strehl_command,
        [strehl_attestation],
    )
    strehl_receipt_path = full_receipts / "strehl" / "development-common.json"
    consumer_gate.write_json(strehl_receipt_path, strehl_receipt)

    fork_attestation = out / "full" / "attestations" / "focus-stack-fork.json"
    fork_output = out / "full" / "outputs" / "focus-stack-fork.tiff"
    fork_command = [
        str(python),
        str(adapter),
        "--consumer-id",
        "focus-stack-fork",
        "--executable",
        str(fork_executable),
        "--executable-sha256",
        fork_sha,
        "--input",
        str(tiff_path),
        "--output",
        str(fork_output),
        "--attestation",
        str(fork_attestation),
    ]
    fork_run = run(fork_command)
    require(
        fork_run.returncode == 0,
        "FORK_CONSUMER_FAILED",
        f"fork adapter failed: {fork_run.stdout[-1000:]} {fork_run.stderr[-1000:]}",
    )
    fork_attestation_value = read_json(fork_attestation)
    wrong_hash_attestation = (
        out / "failure-probes" / "wrong-executable-hash.json"
    )
    wrong_hash_output = out / "failure-probes" / "wrong-executable-hash.tiff"
    wrong_hash_command = [
        str(python),
        str(adapter),
        "--consumer-id",
        "focus-stack-fork",
        "--executable",
        str(fork_executable),
        "--executable-sha256",
        "0" * 64,
        "--input",
        str(tiff_path),
        "--output",
        str(wrong_hash_output),
        "--attestation",
        str(wrong_hash_attestation),
    ]
    wrong_hash_run = run(wrong_hash_command)
    wrong_hash_value = read_json(wrong_hash_attestation)
    fork_receipt = consumer_gate.make_receipt(
        full_campaign_path,
        full_registry_path,
        gate_freeze_path,
        "focus-stack-fork",
        "development-common",
        fork_attestation,
        fork_command,
        [fork_output],
    )
    fork_receipt_path = (
        full_receipts / "focus-stack-fork" / "development-common.json"
    )
    consumer_gate.write_json(fork_receipt_path, fork_receipt)

    full_gate = consumer_gate.verify_campaign(
        full_campaign_path, full_registry_path, gate_freeze_path, full_receipts
    )
    full_gate_path = out / "full" / "gate.json"
    consumer_gate.write_json(full_gate_path, full_gate)

    arm_receipts = out / "fork-arm" / "receipts"
    arm_receipt = consumer_gate.make_receipt(
        arm_campaign_path,
        arm_registry_path,
        gate_freeze_path,
        "focus-stack-fork",
        "development-common",
        fork_attestation,
        fork_command,
        [fork_output],
    )
    arm_receipt_path = (
        arm_receipts / "focus-stack-fork" / "development-common.json"
    )
    consumer_gate.write_json(arm_receipt_path, arm_receipt)
    baseline = consumer_gate.verify_campaign(
        arm_campaign_path, arm_registry_path, gate_freeze_path, arm_receipts
    )
    baseline_path = out / "fork-arm" / "baseline-gate.json"
    consumer_gate.write_json(baseline_path, baseline)

    input_sha = full_manifest["output"]["file_sha256"]
    target_line = f'  "input_file_sha256": "{input_sha}",'
    replacement_line = f'  "input_file_sha256": "{"0" * 64}",'
    missing_anchor_hard_error = False
    try:
        replace_unique_full_line(
            arm_receipt_path,
            '  "input_file_sha256": "missing-unique-line-anchor",',
            replacement_line,
        )
    except CommissionFailure as exc:
        missing_anchor_hard_error = exc.failure_class == "MUTATION_ANCHOR_INVALID"
    original_receipt = replace_unique_full_line(
        arm_receipt_path, target_line, replacement_line
    )
    degraded = consumer_gate.verify_campaign(
        arm_campaign_path, arm_registry_path, gate_freeze_path, arm_receipts
    )
    degraded_path = out / "fork-arm" / "degraded-gate.json"
    consumer_gate.write_json(degraded_path, degraded)
    arm_receipt_path.write_bytes(original_receipt)
    repaired = consumer_gate.verify_campaign(
        arm_campaign_path, arm_registry_path, gate_freeze_path, arm_receipts
    )
    repaired_path = out / "fork-arm" / "repaired-gate.json"
    consumer_gate.write_json(repaired_path, repaired)

    fork_pair = next(
        pair
        for pair in full_gate["pairs"]
        if pair["consumer_id"] == "focus-stack-fork"
    )
    degraded_pair = degraded["pairs"][0]
    required = full_gate["summary"]["required_consumer_input_pairs"]
    optional = full_gate["summary"]["optional_consumer_input_pairs"]
    inputs = full_gate["summary"]["inputs"]
    baseline_pairs = baseline["summary"]["required_consumer_input_pairs"]
    degraded_pairs = degraded["summary"]["required_consumer_input_pairs"]
    repaired_pairs = repaired["summary"]["required_consumer_input_pairs"]
    hashes_agree = (
        full_manifest["output"]["file_sha256"]
        == fork_attestation_value["input_file_sha256"]
        == fork_pair["evidence"]["file_sha256"]
        and full_manifest["output"]["pixel_payload_sha256"]
        == fork_attestation_value["input_pixel_payload_sha256"]
        == fork_pair["evidence"]["pixel_payload_sha256"]
    )
    checks = {
        "source_and_executable_frozen_before_render": True,
        "two_clean_builds_are_byte_identical": build_freeze["reproducibility"][
            "byte_identical"
        ]
        is True
        and build_freeze["reproducibility"]["differing_bytes"] == 0,
        "fork_process_completed_and_emitted_output": fork_run.returncode == 0
        and fork_output.is_file()
        and fork_output.stat().st_size > 0,
        "adapter_failure_persists_fail_record": wrong_hash_run.returncode != 0
        and wrong_hash_value.get("status") == "FAIL"
        and wrong_hash_value.get("failure_class") == "EXECUTABLE_HASH_MISMATCH"
        and not wrong_hash_output.exists(),
        "fork_received_input_path_twice": fork_attestation_value[
            "input_path_occurrences_in_consumer_invocation"
        ]
        == 2,
        "locked_handoff_metadata_stable": fork_attestation_value["locked_handoff"][
            "metadata_unchanged"
        ]
        is True,
        "fork_one_read_hash_and_parse": fork_attestation_value["read_contract"]
        == {
            "artifact_read_count": 1,
            "hash_and_parse_same_memory": True,
        },
        "converter_adapter_gate_hashes_agree": hashes_agree,
        "fork_pair_passes_in_truthful_roster": fork_pair["outcome"] == "PASS",
        "truthful_roster_partition_balanced": full_gate["status"] == "FAIL"
        and required["total_examined"] == 4
        and required["counts"]["PASS"] == 2
        and required["counts"]["BLOCKED"] == 2
        and required["partition_balanced"]
        and inputs["total_examined"] == 1
        and inputs["counts"]["BLOCKED"] == 1
        and inputs["partition_balanced"]
        and optional["total_examined"] == 1
        and optional["counts"]["OPTIONAL_ABSENT"] == 1
        and optional["partition_balanced"],
        "fork_arm_baseline_passes": baseline["status"] == "PASS"
        and baseline_pairs["total_examined"] == 1
        and baseline_pairs["counts"]["PASS"] == 1
        and baseline_pairs["partition_balanced"],
        "missing_mutation_anchor_hard_errors": missing_anchor_hard_error,
        "unique_full_line_mutation_goes_red": degraded["status"] == "FAIL"
        and degraded_pair.get("failure_class") == "RECEIPT_INPUT_HASH_MISMATCH"
        and degraded_pairs["counts"]["FAIL"] == 1
        and degraded_pairs["partition_balanced"],
        "exact_receipt_restore_recovers_pass": repaired["status"] == "PASS"
        and repaired_pairs["counts"]["PASS"] == 1
        and repaired_pairs["partition_balanced"],
        "all_gate_artifacts_one_read": full_gate["artifact_read_audit"][
            "all_artifacts_read_at_most_once"
        ]
        and baseline["artifact_read_audit"]["all_artifacts_read_at_most_once"],
    }
    require(
        all(checks.values()),
        "COMMISSION_CHECK_FAILED",
        "one or more fork-arm commissioning checks failed",
    )

    return {
        "schema": COMMISSION_SCHEMA,
        "status": "PASS",
        "eligibility": "DEVELOPMENT_ONLY; NOT A QUALITY SCORE",
        "measurement_class": "deterministic correctness; no wall-clock result",
        "checks": checks,
        "source": {
            "revision": FORK_COMMIT,
            "tree_sha1": build_freeze["source"]["tree_sha1"],
            "manifest_sha256": build_freeze["source"]["manifest_sha256"],
            "source_pin_sha256": consumer_gate.hash_bytes(
                source_pin_path.read_bytes()
            ),
        },
        "frozen_executable": build_freeze["frozen_executable"],
        "reproducibility": build_freeze["reproducibility"],
        "input_identity": {
            "hash_algorithm": "SHA-256",
            "whole_file_range": "[0,file_size)",
            "pixel_payload_range": (
                "concatenation of TIFF strip ranges in scan order"
            ),
            "converter_manifest": {
                "file_sha256": full_manifest["output"]["file_sha256"],
                "pixel_payload_sha256": full_manifest["output"][
                    "pixel_payload_sha256"
                ],
            },
            "fork_locked_adapter": {
                "file_sha256": fork_attestation_value["input_file_sha256"],
                "pixel_payload_sha256": fork_attestation_value[
                    "input_pixel_payload_sha256"
                ],
                "whole_file_hash": fork_attestation_value["whole_file_hash"],
                "pixel_payload_hash": fork_attestation_value["pixel_payload_hash"],
            },
            "stage0c_gate": {
                "file_sha256": fork_pair["evidence"]["file_sha256"],
                "pixel_payload_sha256": fork_pair["evidence"][
                    "pixel_payload_sha256"
                ],
            },
            "all_three_agree": hashes_agree,
        },
        "fork_run": {
            "adapter_exit_code": fork_run.returncode,
            "attestation": file_record("fork attestation", fork_attestation),
            "output": file_record("fork output", fork_output),
            "locked_handoff": fork_attestation_value["locked_handoff"],
            "consumer_invocation": fork_attestation_value["consumer_invocation"],
        },
        "fail_closed_probe": {
            "exit_code": wrong_hash_run.returncode,
            "attestation": file_record(
                "wrong executable hash attestation", wrong_hash_attestation
            ),
            "failure_class": wrong_hash_value.get("failure_class"),
            "output_created": wrong_hash_output.exists(),
        },
        "truthful_full_roster": {
            "status": full_gate["status"],
            "gate": file_record("full roster gate", full_gate_path),
            "summary": full_gate["summary"],
            "fork_pair": fork_pair,
        },
        "commissioned_fork_arm": {
            "baseline": {
                "gate": file_record("fork arm baseline", baseline_path),
                "summary": baseline["summary"],
            },
            "planted_degradation": {
                "mutation": {
                    "path": str(arm_receipt_path),
                    "unique_full_line_before": target_line,
                    "unique_full_line_after": replacement_line,
                    "missing_anchor_hard_error": missing_anchor_hard_error,
                },
                "gate": file_record("fork arm degraded", degraded_path),
                "failure_class": degraded_pair.get("failure_class"),
                "summary": degraded["summary"],
            },
            "planted_improvement": {
                "action": "restore exact original receipt bytes",
                "gate": file_record("fork arm repaired", repaired_path),
                "summary": repaired["summary"],
            },
        },
        "known_limitations": [
            (
                "The development input is synthetic and cannot produce a quality "
                "score or qualify a real campaign."
            ),
            (
                "The pinned fork has no ProPhoto D50 input mode. Its 16-bit input "
                "path bypasses input-color conversion and does not interpret the "
                "embedded ICC, so exact-byte admission is proven but color-semantic "
                "equivalence is not."
            ),
            (
                "The adapter proves the locked file bytes supplied at the consumer "
                "boundary. The opaque executable does not expose an internal sample "
                "hash."
            ),
            (
                "The complete Stage 0C roster remains blocked by expired Zerene "
                "PMax and DMap licences and by missing eligible campaign captures."
            ),
        ],
    }


def main() -> int:
    output: Path | None = None
    try:
        args = parse_args()
        output = Path(args.out).resolve() / "commission.json"
        report = commission(args)
        consumer_gate.write_json(output, report)
        print(json.dumps(report, sort_keys=True))
        return 0
    except BaseException as exc:
        failure_class = (
            exc.failure_class
            if isinstance(exc, CommissionFailure)
            else getattr(exc, "failure_class", type(exc).__name__.upper())
        )
        report = {
            "schema": COMMISSION_SCHEMA,
            "status": "FAIL",
            "failure_class": failure_class,
            "reason": str(exc),
        }
        if output is not None:
            try:
                consumer_gate.write_json(output, report)
            except BaseException:
                pass
        print(json.dumps(report, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
