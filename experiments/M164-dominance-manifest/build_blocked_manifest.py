"""Serialize the current fail-closed production-manifest state."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MANIFEST_RELATIVE = (
    Path("experiments")
    / "M164-dominance-manifest"
    / "production-manifest-v1.json"
)
FREEZE_RELATIVE = (
    Path("experiments")
    / "M164-dominance-manifest"
    / "production-manifest-v1.freeze.json"
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _encode(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _artifact(artifact_id: str, relative: str) -> dict[str, str]:
    path = ROOT / relative
    return {
        "id": artifact_id,
        "path": str(Path(relative)),
        "sha256": _sha256(path.read_bytes()),
    }


def build() -> tuple[str, str]:
    manifest = {
        "schema": "m164-dominance-manifest/v1",
        "version": 1,
        "status": "BLOCKED",
        "claim_scope": "GX",
        "dimensions": {
            "reference_strips": [
                "strip-1",
                "strip-2",
                "strip-3",
                "strip-4",
            ],
            "scored_modes": ["sw4", "sw10"],
            "channels": None,
            "frequencies": ["f0100", "f0150", "f0200", "f0250"],
            "orientations": ["o0000", "o0225", "o0450", "o0675"],
            "field_partitions": None,
        },
        "cells": [],
        "thresholds": {
            "epsilon_common": None,
            "minimum_signal_power": None,
            "minimum_noise_power": None,
            "minimum_rank": None,
            "maximum_condition_number": None,
            "minimum_sites_per_cell": 64,
            "minimum_control_sites_per_class": None,
            "common_mode_control_classes": None,
        },
        "inference": {
            "method": "paired-site-one-sided-max-t",
            "quantile_method": "higher",
            "dominance_alpha": 0.025,
            "common_mode_alpha": 0.025,
            "bootstrap_draws": 10000,
            "dominance_seed": 164176,
            "common_mode_seed": 164175,
        },
        "reduction": None,
        "artifact_hashes": {
            "calibration": [
                _artifact(
                    "m165-pattern-map-settings",
                    "experiments\\M165-common-input\\pattern-map-settings-v1.json",
                ),
                _artifact(
                    "m165-pattern-map-estimator-freeze",
                    "experiments\\M165-common-input\\pattern-map-estimator-freeze-v1.json",
                ),
            ],
            "target": [
                _artifact(
                    "m135-comparison-contract",
                    "experiments\\M135-detail-instrument\\comparison-contract.json",
                ),
                _artifact(
                    "m135-comparison-binding",
                    "experiments\\M135-detail-instrument\\comparison-binding.json",
                ),
            ],
            "resampler": [
                _artifact(
                    "m135-comparison-rule",
                    "experiments\\M135-detail-instrument\\comparison-rule-manifest.json",
                )
            ],
            "geometry": [
                _artifact(
                    "m147-preflight-core",
                    "experiments\\M147-preflight\\preflight.py",
                )
            ],
            "software": [
                _artifact(
                    "dominance-core",
                    "experiments\\M164-reference-dominance\\dominance.py",
                ),
                _artifact(
                    "manifest-builder",
                    "experiments\\M164-dominance-manifest\\build_blocked_manifest.py",
                ),
            ],
            "seed": [],
            "checker": [
                _artifact(
                    "reader-core",
                    "experiments\\M164-dominance-manifest\\reader_core.py",
                ),
                _artifact(
                    "reader-launcher",
                    "experiments\\M164-dominance-manifest\\reader.py",
                ),
            ],
        },
        "unresolved": [
            {
                "id": "production-cell-family",
                "missing": (
                    "registered channels, frozen subject-region/field "
                    "partitions, and their exact Cartesian expansion"
                ),
                "producer": "M164 registrar with the M135 target owner",
            },
            {
                "id": "production-numerical-bars",
                "missing": (
                    "positive per-cell information and transfer margins, "
                    "epsilon_common, signal/noise floors, rank bar, "
                    "conditioning bar, and control-site floor"
                ),
                "producer": (
                    "M164 calibration owner using two disjoint known-ratio "
                    "development partitions"
                ),
            },
            {
                "id": "complete-s-reduction",
                "missing": (
                    "candidate-blind scalar sufficiency proof and exact "
                    "55/27-frame reduction artifact"
                ),
                "producer": "M164 complete-input reduction owner",
            },
            {
                "id": "physical-target-geometry",
                "missing": (
                    "final target artwork, native-output resampler, accepted "
                    "M147 scale/field result, and production geometry binding"
                ),
                "producer": (
                    "M135 target and M147 geometry owners after the allowed "
                    "two-frame M147 preflight"
                ),
            },
            {
                "id": "production-software",
                "missing": (
                    "the Strehl candidate plus licensed Zerene PMax/DMap "
                    "and registered fork binaries, versions, settings, "
                    "native-output adapters, non-secret licence/edition "
                    "authorisation receipt, reduction/extraction software, "
                    "and environment freeze required by the exact rehearsal"
                ),
                "producer": (
                    "M164 registrar with the Strehl and comparator execution "
                    "owners; the owner must purchase the admitted Zerene tier"
                ),
            },
            {
                "id": "production-seed",
                "missing": (
                    "target-code, randomization, and checker seed artifact"
                ),
                "producer": "M164 registrar before any registered exposure",
            },
        ],
    }
    manifest_bytes = _encode(manifest)
    manifest_path = ROOT / MANIFEST_RELATIVE
    manifest_path.write_bytes(manifest_bytes)
    manifest_sha = _sha256(manifest_bytes)

    core_relative = (
        Path("experiments")
        / "M164-dominance-manifest"
        / "reader_core.py"
    )
    launcher_relative = (
        Path("experiments") / "M164-dominance-manifest" / "reader.py"
    )
    freeze = {
        "schema": "m164-dominance-freeze/v1",
        "manifest_path": str(MANIFEST_RELATIVE),
        "manifest_sha256": manifest_sha,
        "checker_core_path": str(core_relative),
        "checker_core_sha256": _sha256((ROOT / core_relative).read_bytes()),
        "launcher_path": str(launcher_relative),
        "launcher_sha256": _sha256(
            (ROOT / launcher_relative).read_bytes()
        ),
    }
    freeze_path = ROOT / FREEZE_RELATIVE
    freeze_path.write_bytes(_encode(freeze))
    return manifest_sha, _sha256(freeze_path.read_bytes())


def main() -> int:
    manifest_sha, freeze_sha = build()
    print(f"manifest_sha256={manifest_sha}")
    print(f"freeze_sha256={freeze_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
