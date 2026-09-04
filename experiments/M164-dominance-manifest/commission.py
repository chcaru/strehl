"""Commission every fail-closed M164 manifest-reader check."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = HERE / ".commission-work"
READER = HERE / "reader.py"
CORE = HERE / "reader_core.py"
DOMINANCE = ROOT / "experiments" / "M164-reference-dominance" / "dominance.py"
OUTPUT = HERE / "out" / "commission.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _encode(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _fragment(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def _complex_json(value: np.ndarray) -> list[list[float]]:
    return [
        [float(np.real(item)), float(np.imag(item))]
        for item in np.asarray(value)
    ]


def _cell_id(values: tuple[str, ...]) -> str:
    return "__".join(values)


def _artifact(artifact_id: str, path: Path) -> dict[str, str]:
    return {
        "id": artifact_id,
        "path": _relative(path),
        "sha256": _sha256(path.read_bytes()),
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_encode(value))


def _replace_exact(
    data: bytes,
    old: bytes,
    new: bytes,
    *,
    label: str,
) -> tuple[bytes, dict[str, Any]]:
    count = data.count(old)
    if count != 1:
        raise AssertionError(
            f"{label}: mutation anchor count is {count}, expected exactly one"
        )
    return (
        data.replace(old, new, 1),
        {
            "label": label,
            "anchor_count": count,
            "anchor_sha256": _sha256(old),
        },
    )


def _make_evidence(
    cell_ids: list[str],
    *,
    manifest_sha256: str,
    reduction_sha256: str,
) -> dict[str, Any]:
    rng = np.random.default_rng(164_901)
    sites = 64
    witness = {
        name: {}
        for name in ("reference_1", "reference_2", "scored_1", "scored_2")
    }
    design: dict[str, Any] = {}
    controls: dict[str, Any] = {}

    for cell_index, cell_id in enumerate(cell_ids):
        latent = (
            rng.normal(size=sites) + 1j * rng.normal(size=sites)
        ) / np.sqrt(2.0)
        latent += (0.07 + 0.01j) * cell_index
        reference_gain = 1.40 + 0.03 * cell_index
        scored_gain = 0.74 + 0.01 * cell_index
        reference_1 = reference_gain * latent + 0.07 * (
            rng.normal(size=sites) + 1j * rng.normal(size=sites)
        )
        reference_2 = reference_gain * latent + 0.07 * (
            rng.normal(size=sites) + 1j * rng.normal(size=sites)
        )
        scored_1 = scored_gain * latent + 0.18 * (
            rng.normal(size=sites) + 1j * rng.normal(size=sites)
        )
        scored_2 = scored_gain * latent + 0.18 * (
            rng.normal(size=sites) + 1j * rng.normal(size=sites)
        )
        design[cell_id] = _complex_json(latent)
        witness["reference_1"][cell_id] = _complex_json(reference_1)
        witness["reference_2"][cell_id] = _complex_json(reference_2)
        witness["scored_1"][cell_id] = _complex_json(scored_1)
        witness["scored_2"][cell_id] = _complex_json(scored_2)

    for class_name in ("featureless", "dark"):
        class_value = {
            name: {}
            for name in (
                "reference_1",
                "reference_2",
                "scored_1",
                "scored_2",
            )
        }
        for cell_id in cell_ids:
            for name in class_value:
                noise = 0.025 * (
                    rng.normal(size=sites) + 1j * rng.normal(size=sites)
                )
                class_value[name][cell_id] = _complex_json(noise)
        controls[class_name] = class_value

    return {
        "schema": "m164-dominance-evidence/v1",
        "manifest_sha256": manifest_sha256,
        "reduction_artifact_sha256": reduction_sha256,
        "cell_ids": cell_ids,
        "witness": witness,
        "design": design,
        "controls": controls,
        "lineage": {
            "reference": {
                "strip-a": {
                    "A": ["ref-a-001", "ref-a-002"],
                    "B": ["ref-b-001", "ref-b-002"],
                }
            },
            "scored": {
                "sw4": {
                    "A": ["sw4-a-001", "sw4-a-002", "sw4-a-003"],
                    "B": ["sw4-b-001", "sw4-b-002", "sw4-b-003"],
                }
            },
            "candidate_inputs": ["candidate-001", "candidate-002"],
        },
    }


@dataclass
class Case:
    case_id: str
    directory: Path
    manifest_path: Path
    freeze_path: Path
    evidence_path: Path
    output_path: Path
    manifest: dict[str, Any]
    evidence: dict[str, Any]
    artifacts: dict[str, Path]
    core_path: Path
    manifest_sha256: str
    mutations: list[dict[str, Any]] = field(default_factory=list)
    binding_updates: list[dict[str, Any]] = field(default_factory=list)

    def replace_file(
        self,
        path: Path,
        old: bytes,
        new: bytes,
        *,
        label: str,
        binding_update: bool = False,
    ) -> None:
        changed, record = _replace_exact(
            path.read_bytes(), old, new, label=label
        )
        path.write_bytes(changed)
        if binding_update:
            self.binding_updates.append(record)
        else:
            self.mutations.append(record)

    def replace_manifest_value(
        self,
        old: Any,
        new: Any,
        *,
        label: str,
    ) -> None:
        self.replace_file(
            self.manifest_path,
            _fragment(old),
            _fragment(new),
            label=label,
        )
        self.refresh_manifest_binding()

    def replace_evidence_value(
        self,
        old: Any,
        new: Any,
        *,
        label: str,
    ) -> None:
        self.replace_file(
            self.evidence_path,
            _fragment(old),
            _fragment(new),
            label=label,
        )

    def replace_freeze_value(
        self,
        old: Any,
        new: Any,
        *,
        label: str,
    ) -> None:
        self.replace_file(
            self.freeze_path,
            _fragment(old),
            _fragment(new),
            label=label,
        )

    def refresh_manifest_binding(self) -> None:
        new_sha = _sha256(self.manifest_path.read_bytes())
        self.replace_file(
            self.freeze_path,
            _fragment(self.manifest_sha256),
            _fragment(new_sha),
            label="refresh-manifest-sha256-binding",
            binding_update=True,
        )
        self.manifest_sha256 = new_sha


def _make_case(
    case_id: str,
    *,
    core_source: bytes | None = None,
) -> Case:
    directory = WORK / case_id
    directory.mkdir(parents=True, exist_ok=False)
    fixture_dir = directory / "fixtures"
    fixture_dir.mkdir()

    fixture_values = {
        "calibration": {
            "schema": "m164-commission-calibration/v1",
            "partition": "disjoint-known-ratio",
        },
        "target": {
            "schema": "m164-commission-target/v1",
            "sites": 64,
        },
        "resampler": {
            "schema": "m164-commission-resampler/v1",
            "kernel": "identity",
        },
        "geometry": {
            "schema": "m164-commission-geometry/v1",
            "field": "synthetic",
        },
        "environment": {
            "schema": "m164-commission-environment/v1",
            "numpy": np.__version__,
        },
        "seed": {
            "schema": "m164-commission-seeds/v1",
            "target_seed": 164901,
        },
        "reduction": {
            "schema": "m164-commission-reduction-proof/v1",
            "kind": "scalar-linear-sufficient",
            "scope": "synthetic-commissioning-only",
        },
    }
    artifacts: dict[str, Path] = {}
    for name, value in fixture_values.items():
        path = fixture_dir / f"{name}.json"
        _write_json(path, value)
        artifacts[name] = path

    if core_source is None:
        core_path = CORE
    else:
        core_path = directory / "reader_core_defect.py"
        core_path.write_bytes(core_source)

    dimensions = {
        "reference_strips": ["strip-a"],
        "scored_modes": ["sw4"],
        "channels": ["green"],
        "frequencies": ["f0100", "f0200"],
        "orientations": ["o0000", "o0450"],
        "field_partitions": ["field-all"],
    }
    dimension_order = [
        dimensions["reference_strips"],
        dimensions["scored_modes"],
        dimensions["channels"],
        dimensions["frequencies"],
        dimensions["orientations"],
        dimensions["field_partitions"],
    ]
    cells = []
    for index, values in enumerate(itertools.product(*dimension_order)):
        cells.append(
            {
                "id": _cell_id(values),
                "reference_strip": values[0],
                "scored_mode": values[1],
                "channel": values[2],
                "frequency": values[3],
                "orientation": values[4],
                "field_partition": values[5],
                "delta_information": 0.021 + 0.001 * index,
                "delta_transfer": 0.022 + 0.001 * index,
            }
        )
    manifest = {
        "schema": "m164-dominance-manifest/v1",
        "version": 1,
        "status": "FROZEN",
        "claim_scope": "GX",
        "dimensions": dimensions,
        "cells": cells,
        "thresholds": {
            "epsilon_common": 0.05,
            "minimum_signal_power": 1.0e-6,
            "minimum_noise_power": 2.0e-6,
            "minimum_rank": 2,
            "maximum_condition_number": 2.0,
            "minimum_sites_per_cell": 64,
            "minimum_control_sites_per_class": 16,
            "common_mode_control_classes": ["featureless", "dark"],
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
        "reduction": {
            "kind": "scalar-linear-sufficient",
            "artifact_id": "reduction-proof",
            "frame_counts": {
                "reference_per_strip_per_repeat": 2,
                "scored_per_mode_per_repeat": {"sw4": 3},
            },
        },
        "artifact_hashes": {
            "calibration": [
                _artifact("fixture-calibration", artifacts["calibration"])
            ],
            "target": [_artifact("fixture-target", artifacts["target"])],
            "resampler": [
                _artifact("fixture-resampler", artifacts["resampler"])
            ],
            "geometry": [
                _artifact("fixture-geometry", artifacts["geometry"])
            ],
            "software": [
                _artifact("dominance-core", DOMINANCE),
                _artifact("reduction-proof", artifacts["reduction"]),
                _artifact("fixture-environment", artifacts["environment"]),
            ],
            "seed": [_artifact("bootstrap-seeds", artifacts["seed"])],
            "checker": [
                _artifact("reader-core", core_path),
                _artifact("reader-launcher", READER),
            ],
        },
        "unresolved": [],
    }
    manifest_path = directory / "manifest.json"
    _write_json(manifest_path, manifest)
    manifest_sha = _sha256(manifest_path.read_bytes())
    evidence = _make_evidence(
        [cell["id"] for cell in cells],
        manifest_sha256=manifest_sha,
        reduction_sha256=_sha256(artifacts["reduction"].read_bytes()),
    )
    evidence_path = directory / "evidence.json"
    _write_json(evidence_path, evidence)
    freeze = {
        "schema": "m164-dominance-freeze/v1",
        "manifest_path": _relative(manifest_path),
        "manifest_sha256": manifest_sha,
        "checker_core_path": _relative(core_path),
        "checker_core_sha256": _sha256(core_path.read_bytes()),
        "launcher_path": _relative(READER),
        "launcher_sha256": _sha256(READER.read_bytes()),
    }
    freeze_path = directory / "freeze.json"
    _write_json(freeze_path, freeze)
    return Case(
        case_id=case_id,
        directory=directory,
        manifest_path=manifest_path,
        freeze_path=freeze_path,
        evidence_path=evidence_path,
        output_path=directory / "verdict.json",
        manifest=manifest,
        evidence=evidence,
        artifacts=artifacts,
        core_path=core_path,
        manifest_sha256=manifest_sha,
    )


def _replace_argument(
    arguments: list[str],
    old: str,
    new: str | None,
    *,
    label: str,
) -> dict[str, Any]:
    count = arguments.count(old)
    if count != 1:
        raise AssertionError(
            f"{label}: argument anchor count is {count}, expected exactly one"
        )
    index = arguments.index(old)
    if new is None:
        arguments.pop(index)
    else:
        arguments[index] = new
    return {
        "label": label,
        "anchor_count": count,
        "anchor_sha256": _sha256(old.encode("utf-8")),
    }


def _run_case(
    case: Case,
    target_check: str | None,
    *,
    mutate: Callable[[Case], None] | None = None,
    omit_evidence: bool = False,
    missing_evidence: bool = False,
    missing_freeze: bool = False,
) -> dict[str, Any]:
    if mutate is not None:
        mutate(case)
    arguments = [
        sys.executable,
        "-B",
        str(READER),
        "--repo-root",
        str(ROOT),
        "--freeze",
        str(case.freeze_path),
        "--manifest",
        str(case.manifest_path),
        "--evidence",
        str(case.evidence_path),
        "--output",
        str(case.output_path),
    ]
    if omit_evidence:
        evidence_index = arguments.index("--evidence")
        count = arguments.count("--evidence")
        if count != 1:
            raise AssertionError("omit-evidence anchor was not unique")
        removed = arguments[evidence_index : evidence_index + 2]
        del arguments[evidence_index : evidence_index + 2]
        case.mutations.append(
            {
                "label": "omit-evidence-argument",
                "anchor_count": count,
                "anchor_sha256": _sha256(
                    "\0".join(removed).encode("utf-8")
                ),
            }
        )
    if missing_evidence:
        case.mutations.append(
            _replace_argument(
                arguments,
                str(case.evidence_path),
                str(case.directory / "missing-evidence.json"),
                label="point-evidence-at-missing-file",
            )
        )
    if missing_freeze:
        case.mutations.append(
            _replace_argument(
                arguments,
                str(case.freeze_path),
                str(case.directory / "missing-freeze.json"),
                label="point-freeze-at-missing-file",
            )
        )

    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "BLIS_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
        }
    )
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if not case.output_path.exists():
        raise AssertionError(
            f"{case.case_id}: reader produced no persistent verdict; "
            f"stderr={completed.stderr}"
        )
    verdict = json.loads(case.output_path.read_text(encoding="utf-8"))
    observed = sorted(
        {
            reason["code"]
            for reason in verdict.get("reasons", [])
            if isinstance(reason, dict) and isinstance(reason.get("code"), str)
        }
    )
    if target_check is None:
        passed = completed.returncode == 0 and verdict.get("status") == "PASS"
    else:
        passed = (
            completed.returncode == 2
            and verdict.get("status") == "UNMEASURED"
            and target_check in observed
        )
    return {
        "id": case.case_id,
        "target_check": target_check,
        "status": verdict.get("status"),
        "returncode": completed.returncode,
        "observed_reason_codes": observed,
        "mutations": case.mutations,
        "binding_updates": case.binding_updates,
        "passed": passed,
    }


def _mutate_manifest_value(
    old_selector: Callable[[Case], Any],
    new_selector: Callable[[Case], Any] | Any,
    label: str,
) -> Callable[[Case], None]:
    def mutate(case: Case) -> None:
        old = old_selector(case)
        new = new_selector(case) if callable(new_selector) else new_selector
        case.replace_manifest_value(old, new, label=label)

    return mutate


def _mutate_evidence_value(
    old_selector: Callable[[Case], Any],
    new_selector: Callable[[Case], Any] | Any,
    label: str,
) -> Callable[[Case], None]:
    def mutate(case: Case) -> None:
        old = old_selector(case)
        new = new_selector(case) if callable(new_selector) else new_selector
        case.replace_evidence_value(old, new, label=label)

    return mutate


def _raw_metrics(evidence: dict[str, Any]) -> dict[str, list[float]]:
    cell_ids = evidence["cell_ids"]

    def matrix(name: str) -> np.ndarray:
        columns = []
        for cell_id in cell_ids:
            value = np.asarray(
                evidence["witness"][name][cell_id], dtype=np.float64
            )
            columns.append(value[:, 0] + 1j * value[:, 1])
        return np.column_stack(columns)

    def cross(first: np.ndarray, second: np.ndarray) -> np.ndarray:
        first = first - np.mean(first, axis=0, keepdims=True)
        second = second - np.mean(second, axis=0, keepdims=True)
        return np.real(
            np.sum(first * np.conj(second), axis=0) / (first.shape[0] - 1)
        )

    def noise(first: np.ndarray, second: np.ndarray) -> np.ndarray:
        difference = first - second
        difference -= np.mean(difference, axis=0, keepdims=True)
        return (
            0.25
            * np.sum(np.abs(difference) ** 2, axis=0)
            / (first.shape[0] - 1)
        )

    reference_1 = matrix("reference_1")
    reference_2 = matrix("reference_2")
    scored_1 = matrix("scored_1")
    scored_2 = matrix("scored_2")
    reference_signal = cross(reference_1, reference_2)
    scored_signal = cross(scored_1, scored_2)
    reference_information = 0.5 * np.log2(
        1.0 + reference_signal / noise(reference_1, reference_2)
    )
    scored_information = 0.5 * np.log2(
        1.0 + scored_signal / noise(scored_1, scored_2)
    )
    return {
        "information_ratio": [
            float(value)
            for value in reference_information / scored_information
        ],
        "transfer_ratio": [
            float(value)
            for value in np.sqrt(reference_signal / scored_signal)
        ],
    }


def _contaminated_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(evidence)
    rng = np.random.default_rng(164_902)
    sites = 64
    for cell_index, cell_id in enumerate(value["cell_ids"]):
        common = (0.70 + 0.04 * cell_index) * (
            rng.normal(size=sites) + 1j * rng.normal(size=sites)
        ) / np.sqrt(2.0)
        for name in ("reference_1", "reference_2"):
            matrix = np.asarray(
                value["witness"][name][cell_id], dtype=np.float64
            )
            complex_value = matrix[:, 0] + 1j * matrix[:, 1] + common
            value["witness"][name][cell_id] = _complex_json(complex_value)
        for name in ("reference_1", "reference_2"):
            matrix = np.asarray(
                value["controls"]["featureless"][name][cell_id],
                dtype=np.float64,
            )
            complex_value = matrix[:, 0] + 1j * matrix[:, 1] + common
            value["controls"]["featureless"][name][cell_id] = _complex_json(
                complex_value
            )
    return value


def _weak_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(evidence)
    cell_id = value["cell_ids"][0]
    latent_pairs = np.asarray(value["design"][cell_id], dtype=np.float64)
    latent = latent_pairs[:, 0] + 1j * latent_pairs[:, 1]
    rng = np.random.default_rng(164_903)
    for name in ("reference_1", "reference_2"):
        weak = 0.48 * latent + 0.18 * (
            rng.normal(size=len(latent)) + 1j * rng.normal(size=len(latent))
        )
        value["witness"][name][cell_id] = _complex_json(weak)
    return value


def _power_defect_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(evidence)
    cell_id = value["cell_ids"][0]
    zeros = [[0.0, 0.0] for _ in range(64)]
    for name in ("reference_1", "reference_2", "scored_1", "scored_2"):
        value["witness"][name][cell_id] = zeros
    return value


def _rank_defect_design(evidence: dict[str, Any]) -> dict[str, Any]:
    design = copy.deepcopy(evidence["design"])
    cell_id = evidence["cell_ids"][0]
    real = np.linspace(-1.0, 1.0, 64)
    design[cell_id] = [[float(value), float(2.0 * value)] for value in real]
    return design


def _condition_defect_design(evidence: dict[str, Any]) -> dict[str, Any]:
    design = copy.deepcopy(evidence["design"])
    cell_id = evidence["cell_ids"][0]
    real = np.linspace(-1.0, 1.0, 64)
    perturbation = np.sin(np.arange(64)) * 1.0e-3
    design[cell_id] = [
        [float(first), float(first + second)]
        for first, second in zip(real, perturbation)
    ]
    return design


def _run_all() -> dict[str, Any]:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    core_namespace: dict[str, Any] = {"__name__": "commission_core_catalog"}
    core_source = CORE.read_bytes()
    exec(compile(core_source, str(CORE), "exec"), core_namespace)
    required_checks = set(core_namespace["ALL_CHECKS"])
    results: list[dict[str, Any]] = []

    results.append(_run_case(_make_case("clean-pass"), None))

    results.append(
        _run_case(
            _make_case("missing-freeze"),
            "INPUT_UNRESOLVABLE",
            missing_freeze=True,
        )
    )
    results.append(
        _run_case(
            _make_case("freeze-json"),
            "FREEZE_RECORD_JSON",
            mutate=lambda case: case.replace_file(
                case.freeze_path,
                b'"schema":"m164-dominance-freeze/v1"',
                b'"schema":',
                label="malform-freeze-json",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("freeze-duplicate-key"),
            "FREEZE_RECORD_JSON",
            mutate=lambda case: case.replace_file(
                case.freeze_path,
                b'"schema":"m164-dominance-freeze/v1"',
                (
                    b'"schema":"m164-dominance-freeze/v1",'
                    b'"schema":"m164-dominance-freeze/v1"'
                ),
                label="duplicate-freeze-schema-key",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("freeze-schema"),
            "FREEZE_RECORD_SCHEMA",
            mutate=lambda case: case.replace_freeze_value(
                "m164-dominance-freeze/v1",
                "m164-dominance-freeze/v0",
                label="wrong-freeze-schema",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("manifest-path-binding"),
            "MANIFEST_PATH_BINDING",
            mutate=lambda case: case.replace_freeze_value(
                _relative(case.manifest_path),
                _relative(case.directory / "wrong-manifest.json"),
                label="wrong-manifest-path-binding",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("launcher-sha"),
            "LAUNCHER_SHA256",
            mutate=lambda case: case.replace_freeze_value(
                _sha256(READER.read_bytes()),
                "1" * 64,
                label="wrong-launcher-sha256",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("core-unresolvable"),
            "CHECKER_CORE_UNRESOLVABLE",
            mutate=lambda case: case.replace_freeze_value(
                _relative(case.core_path),
                _relative(case.directory / "missing-core.py"),
                label="missing-checker-core-path",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("core-sha"),
            "CHECKER_CORE_SHA256",
            mutate=lambda case: case.replace_freeze_value(
                _sha256(case.core_path.read_bytes()),
                "2" * 64,
                label="wrong-checker-core-sha256",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("manifest-sha"),
            "MANIFEST_SHA256",
            mutate=lambda case: case.replace_freeze_value(
                case.manifest_sha256,
                "3" * 64,
                label="wrong-manifest-sha256",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("manifest-json"),
            "MANIFEST_JSON",
            mutate=lambda case: (
                case.replace_file(
                    case.manifest_path,
                    b'"status":"FROZEN"',
                    b'"status":',
                    label="malform-manifest-json",
                ),
                case.refresh_manifest_binding(),
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("manifest-duplicate-key"),
            "MANIFEST_JSON",
            mutate=lambda case: (
                case.replace_file(
                    case.manifest_path,
                    b'"status":"FROZEN"',
                    b'"status":"FROZEN","status":"FROZEN"',
                    label="duplicate-manifest-status-key",
                ),
                case.refresh_manifest_binding(),
            ),
        )
    )

    manifest_cases = [
        (
            "manifest-schema",
            "MANIFEST_SCHEMA",
            lambda case: case.manifest["schema"],
            "m164-dominance-manifest/v0",
            "wrong-manifest-schema",
        ),
        (
            "manifest-status",
            "MANIFEST_STATUS",
            lambda case: case.manifest["status"],
            "DRAFT",
            "nonfrozen-manifest",
        ),
        (
            "claim-scope",
            "CLAIM_SCOPE",
            lambda case: case.manifest["claim_scope"],
            "X",
            "wrong-claim-scope",
        ),
        (
            "dimensions-empty",
            "DIMENSIONS_NONEMPTY",
            lambda case: case.manifest["dimensions"]["channels"],
            [],
            "empty-channel-dimension",
        ),
        (
            "dimension-member",
            "DIMENSION_MEMBER_VALID",
            lambda case: case.manifest["dimensions"]["frequencies"],
            ["f0100", "f0100"],
            "duplicate-frequency-member",
        ),
        (
            "epsilon-range",
            "EPSILON_COMMON_RANGE",
            lambda case: case.manifest["thresholds"]["epsilon_common"],
            1.0,
            "invalid-epsilon-common",
        ),
        (
            "power-floor",
            "POWER_FLOORS_POSITIVE",
            lambda case: case.manifest["thresholds"],
            lambda case: {
                **case.manifest["thresholds"],
                "minimum_signal_power": 0.0,
            },
            "zero-signal-power-floor",
        ),
        (
            "site-floor",
            "POWER_FLOORS_POSITIVE",
            lambda case: case.manifest["thresholds"],
            lambda case: {
                **case.manifest["thresholds"],
                "minimum_sites_per_cell": 63,
            },
            "sub64-site-floor",
        ),
        (
            "rank-bar",
            "RANK_CONDITION_BARS",
            lambda case: case.manifest["thresholds"],
            lambda case: {
                **case.manifest["thresholds"],
                "minimum_rank": 0,
            },
            "zero-rank-bar",
        ),
        (
            "condition-bar",
            "RANK_CONDITION_BARS",
            lambda case: case.manifest["thresholds"],
            lambda case: {
                **case.manifest["thresholds"],
                "maximum_condition_number": 0.9,
            },
            "subunit-condition-bar",
        ),
        (
            "control-class-list",
            "EPSILON_COMMON_RANGE",
            lambda case: case.manifest["thresholds"],
            lambda case: {
                **case.manifest["thresholds"],
                "common_mode_control_classes": [
                    "featureless",
                    "featureless",
                ],
            },
            "duplicate-control-class",
        ),
        (
            "inference",
            "INFERENCE_SETTINGS",
            lambda case: case.manifest["inference"],
            lambda case: {
                **case.manifest["inference"],
                "bootstrap_draws": 9999,
            },
            "underpowered-bootstrap",
        ),
        (
            "reduction-kind",
            "REDUCTION_SPEC",
            lambda case: case.manifest["reduction"],
            lambda case: {
                **case.manifest["reduction"],
                "kind": "post-hoc-average",
            },
            "unlicensed-reduction-kind",
        ),
        (
            "reduction-counts",
            "REDUCTION_SPEC",
            lambda case: case.manifest["reduction"],
            lambda case: {
                **case.manifest["reduction"],
                "frame_counts": {
                    "reference_per_strip_per_repeat": 2,
                    "scored_per_mode_per_repeat": {"sw10": 3},
                },
            },
            "wrong-reduction-mode-counts",
        ),
        (
            "hash-groups",
            "HASH_GROUPS_COMPLETE",
            lambda case: case.manifest["artifact_hashes"],
            lambda case: {
                **case.manifest["artifact_hashes"],
                "seed": [],
            },
            "empty-seed-hash-group",
        ),
        (
            "unresolved",
            "UNRESOLVED_FIELDS",
            lambda case: case.manifest["unresolved"],
            [{"id": "still-open", "producer": "commission"}],
            "plant-unresolved-field",
        ),
    ]
    for case_id, check, old, new, label in manifest_cases:
        results.append(
            _run_case(
                _make_case(case_id),
                check,
                mutate=_mutate_manifest_value(old, new, label),
            )
        )

    results.append(
        _run_case(
            _make_case("family-cartesian"),
            "FAMILY_CARTESIAN",
            mutate=_mutate_manifest_value(
                lambda case: case.manifest["cells"],
                lambda case: case.manifest["cells"][:-1],
                "delete-one-licensed-cell",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("cell-id-duplicate"),
            "CELL_IDS_UNIQUE",
            mutate=_mutate_manifest_value(
                lambda case: case.manifest["cells"][-1],
                lambda case: {
                    **case.manifest["cells"][-1],
                    "id": case.manifest["cells"][0]["id"],
                },
                "duplicate-cell-id",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("cell-margin"),
            "CELL_MARGINS_POSITIVE",
            mutate=_mutate_manifest_value(
                lambda case: case.manifest["cells"][0],
                lambda case: {
                    **case.manifest["cells"][0],
                    "delta_information": 0.0,
                },
                "zero-cell-information-margin",
            ),
        )
    )

    def unsafe_artifact(case: Case) -> None:
        record = case.manifest["artifact_hashes"]["target"][0]
        case.replace_manifest_value(
            record,
            {**record, "path": "..\\escape.json"},
            label="outside-root-artifact-path",
        )

    def missing_artifact(case: Case) -> None:
        record = case.manifest["artifact_hashes"]["target"][0]
        case.replace_manifest_value(
            record,
            {
                **record,
                "path": _relative(case.directory / "missing-target.json"),
            },
            label="unresolvable-artifact-path",
        )

    def wrong_artifact_hash(case: Case) -> None:
        target = case.artifacts["target"]
        case.replace_file(
            target,
            b'"sites":64',
            b'"sites":65',
            label="mutate-hash-bound-target",
        )

    results.append(
        _run_case(
            _make_case("artifact-path-safe"),
            "ARTIFACT_PATH_SAFE",
            mutate=unsafe_artifact,
        )
    )
    results.append(
        _run_case(
            _make_case("artifact-resolvable"),
            "ARTIFACT_RESOLVABLE",
            mutate=missing_artifact,
        )
    )
    results.append(
        _run_case(
            _make_case("artifact-sha"),
            "ARTIFACT_SHA256",
            mutate=wrong_artifact_hash,
        )
    )

    results.append(
        _run_case(
            _make_case("evidence-required"),
            "EVIDENCE_REQUIRED",
            omit_evidence=True,
        )
    )
    results.append(
        _run_case(
            _make_case("evidence-unresolvable"),
            "EVIDENCE_UNRESOLVABLE",
            missing_evidence=True,
        )
    )
    results.append(
        _run_case(
            _make_case("evidence-json"),
            "EVIDENCE_JSON",
            mutate=lambda case: case.replace_file(
                case.evidence_path,
                b'"schema":"m164-dominance-evidence/v1"',
                b'"schema":',
                label="malform-evidence-json",
            ),
        )
    )
    results.append(
        _run_case(
            _make_case("evidence-duplicate-key"),
            "EVIDENCE_JSON",
            mutate=lambda case: case.replace_file(
                case.evidence_path,
                b'"schema":"m164-dominance-evidence/v1"',
                (
                    b'"schema":"m164-dominance-evidence/v1",'
                    b'"schema":"m164-dominance-evidence/v1"'
                ),
                label="duplicate-evidence-schema-key",
            ),
        )
    )

    evidence_cases = [
        (
            "evidence-schema",
            "EVIDENCE_SCHEMA",
            lambda case: case.evidence["schema"],
            "m164-dominance-evidence/v0",
            "wrong-evidence-schema",
        ),
        (
            "evidence-manifest-binding",
            "EVIDENCE_MANIFEST_BINDING",
            lambda case: case.evidence["manifest_sha256"],
            "4" * 64,
            "wrong-evidence-manifest-sha256",
        ),
        (
            "evidence-reduction-binding",
            "EVIDENCE_REDUCTION_BINDING",
            lambda case: case.evidence["reduction_artifact_sha256"],
            "5" * 64,
            "wrong-evidence-reduction-sha256",
        ),
        (
            "evidence-cell-family",
            "EVIDENCE_CELL_FAMILY",
            lambda case: case.evidence["cell_ids"],
            lambda case: case.evidence["cell_ids"][:-1]
            + ["unlicensed-cell"],
            "replace-one-evidence-cell-id",
        ),
        (
            "evidence-control-classes",
            "EVIDENCE_CONTROL_CLASSES",
            lambda case: case.evidence["controls"],
            lambda case: {
                key: value
                for key, value in case.evidence["controls"].items()
                if key != "dark"
            },
            "remove-dark-control-class",
        ),
        (
            "evidence-design-rank",
            "EVIDENCE_DESIGN_RANK",
            lambda case: case.evidence["design"],
            lambda case: _rank_defect_design(case.evidence),
            "collapse-design-rank",
        ),
        (
            "evidence-design-condition",
            "EVIDENCE_DESIGN_CONDITION",
            lambda case: case.evidence["design"],
            lambda case: _condition_defect_design(case.evidence),
            "ill-condition-design",
        ),
    ]
    for case_id, check, old, new, label in evidence_cases:
        results.append(
            _run_case(
                _make_case(case_id),
                check,
                mutate=_mutate_evidence_value(old, new, label),
            )
        )

    def matrix_shape(case: Case) -> None:
        cell_id = case.evidence["cell_ids"][0]
        old = case.evidence["witness"]["reference_1"][cell_id]
        case.replace_evidence_value(
            old,
            old[:-1],
            label="shorten-one-witness-column",
        )

    def finite_value(case: Case) -> None:
        cell_id = case.evidence["cell_ids"][0]
        value = case.evidence["witness"]["reference_1"][cell_id][0][0]
        case.replace_file(
            case.evidence_path,
            _fragment(value),
            b"1e999",
            label="plant-nonfinite-witness-value",
        )

    def site_count(case: Case) -> None:
        witness = copy.deepcopy(case.evidence["witness"])
        design = copy.deepcopy(case.evidence["design"])
        for name in witness:
            for cell_id in case.evidence["cell_ids"]:
                witness[name][cell_id] = witness[name][cell_id][:-1]
        for cell_id in case.evidence["cell_ids"]:
            design[cell_id] = design[cell_id][:-1]
        case.replace_evidence_value(
            case.evidence["witness"],
            witness,
            label="truncate-all-witness-sites",
        )
        case.replace_evidence_value(
            case.evidence["design"],
            design,
            label="truncate-all-design-sites",
        )

    def control_site_count(case: Case) -> None:
        controls = copy.deepcopy(case.evidence["controls"])
        for name in controls["dark"]:
            for cell_id in case.evidence["cell_ids"]:
                controls["dark"][name][cell_id] = controls["dark"][name][
                    cell_id
                ][:7]
        case.replace_evidence_value(
            case.evidence["controls"],
            controls,
            label="truncate-dark-control-sites",
        )

    def frame_count(case: Case) -> None:
        old = case.evidence["lineage"]["scored"]["sw4"]["A"]
        case.replace_evidence_value(
            old,
            old[:-1],
            label="remove-one-complete-s-frame",
        )

    def frame_disjoint(case: Case) -> None:
        case.replace_evidence_value(
            "sw4-b-003",
            "sw4-a-003",
            label="overlap-a-b-source-frame",
        )

    results.append(
        _run_case(
            _make_case("evidence-matrix-shape"),
            "EVIDENCE_MATRIX_SHAPE",
            mutate=matrix_shape,
        )
    )
    results.append(
        _run_case(
            _make_case("evidence-finite"),
            "EVIDENCE_FINITE_VALUES",
            mutate=finite_value,
        )
    )
    results.append(
        _run_case(
            _make_case("evidence-site-count"),
            "EVIDENCE_SITE_COUNT",
            mutate=site_count,
        )
    )
    results.append(
        _run_case(
            _make_case("control-site-count"),
            "EVIDENCE_SITE_COUNT",
            mutate=control_site_count,
        )
    )
    results.append(
        _run_case(
            _make_case("evidence-frame-count"),
            "EVIDENCE_FRAME_COUNTS",
            mutate=frame_count,
        )
    )
    results.append(
        _run_case(
            _make_case("evidence-frame-disjoint"),
            "EVIDENCE_FRAME_DISJOINT",
            mutate=frame_disjoint,
        )
    )

    def power_defect(case: Case) -> None:
        defective = _power_defect_evidence(case.evidence)
        case.replace_evidence_value(
            case.evidence["witness"],
            defective["witness"],
            label="zero-one-cell-witness-power",
        )

    def weak_defect(case: Case) -> None:
        defective = _weak_evidence(case.evidence)
        case.replace_evidence_value(
            case.evidence["witness"],
            defective["witness"],
            label="weaken-one-reference-cell",
        )

    improvement_case = _make_case("improvement-contamination")
    clean_metrics = _raw_metrics(improvement_case.evidence)
    contaminated = _contaminated_evidence(improvement_case.evidence)
    contaminated_metrics = _raw_metrics(contaminated)

    def improvement_defect(case: Case) -> None:
        case.replace_evidence_value(
            case.evidence["witness"],
            contaminated["witness"],
            label="raise-reference-witness-by-repeatable-contamination",
        )
        case.replace_evidence_value(
            case.evidence["controls"],
            contaminated["controls"],
            label="expose-contamination-in-independent-controls",
        )

    results.append(
        _run_case(
            _make_case("dominance-power"),
            "DOMINANCE_POWER",
            mutate=power_defect,
        )
    )
    results.append(
        _run_case(
            _make_case("dominance-family"),
            "DOMINANCE_FAMILY",
            mutate=weak_defect,
        )
    )
    improvement_result = _run_case(
        improvement_case,
        "DOMINANCE_COMMON_MODE",
        mutate=improvement_defect,
    )
    improvement_result["directional_control"] = {
        "clean_min_information_ratio": min(
            clean_metrics["information_ratio"]
        ),
        "contaminated_min_information_ratio": min(
            contaminated_metrics["information_ratio"]
        ),
        "clean_min_transfer_ratio": min(clean_metrics["transfer_ratio"]),
        "contaminated_min_transfer_ratio": min(
            contaminated_metrics["transfer_ratio"]
        ),
        "both_metrics_rose": (
            min(contaminated_metrics["information_ratio"])
            > min(clean_metrics["information_ratio"])
            and min(contaminated_metrics["transfer_ratio"])
            > min(clean_metrics["transfer_ratio"])
        ),
    }
    improvement_result["passed"] = (
        improvement_result["passed"]
        and improvement_result["directional_control"]["both_metrics_rose"]
    )
    results.append(improvement_result)

    newline = b"\r\n" if b"\r\n" in core_source else b"\n"
    canary_old = newline.join(
        (
            b"    reference_common = np.max(np.vstack(reference_bounds), axis=0)",
            b"    scored_common = np.max(np.vstack(scored_bounds), axis=0)",
            b"",
        )
    )
    canary_new = newline.join(
        (
            b"    reference_common = np.zeros(cell_count, dtype=np.float64)",
            b"    scored_common = np.zeros(cell_count, dtype=np.float64)",
            b"",
        )
    )
    mutated_core, canary_anchor = _replace_exact(
        core_source,
        canary_old,
        canary_new,
        label="disable-common-mode-charge-and-fraction",
    )
    canary_case = _make_case(
        "red-canary-ignore-common-mode",
        core_source=mutated_core,
    )
    contaminated_canary = _contaminated_evidence(canary_case.evidence)
    canary_case.replace_evidence_value(
        canary_case.evidence["witness"],
        contaminated_canary["witness"],
        label="canary-repeatable-improvement-witness",
    )
    canary_case.replace_evidence_value(
        canary_case.evidence["controls"],
        contaminated_canary["controls"],
        label="canary-repeatable-improvement-controls",
    )
    canary_result = _run_case(
        canary_case,
        "DOMINANCE_COMMON_MODE",
    )
    red_canary = {
        "source_mutation": canary_anchor,
        "bad_checker_status": canary_result["status"],
        "bad_checker_reason_codes": canary_result[
            "observed_reason_codes"
        ],
        "commission_would_reject_bad_checker": not canary_result["passed"],
        "bad_checker_rewarded_contamination": (
            canary_result["status"] == "PASS"
        ),
    }

    observed_checks = {
        result["target_check"]
        for result in results
        if result["target_check"] is not None and result["passed"]
    }
    missing_checks = sorted(required_checks - observed_checks)
    failed_cases = sorted(
        result["id"] for result in results if not result["passed"]
    )
    all_mutations_anchored = all(
        bool(result["mutations"])
        and all(
            mutation.get("anchor_count") == 1
            for mutation in result["mutations"]
        )
        for result in results
        if result["target_check"] is not None
    )
    production_manifest = HERE / "production-manifest-v1.json"
    production_has_commission_default = b"0.08" in production_manifest.read_bytes()
    passed = (
        not missing_checks
        and not failed_cases
        and all_mutations_anchored
        and red_canary["commission_would_reject_bad_checker"]
        and red_canary["bad_checker_rewarded_contamination"]
        and not production_has_commission_default
    )
    return {
        "schema": "m164-dominance-manifest-commission/v1",
        "status": "PASS" if passed else "FAIL",
        "required_checks": sorted(required_checks),
        "observed_checks": sorted(observed_checks),
        "missing_checks": missing_checks,
        "failed_cases": failed_cases,
        "all_mutations_exactly_once_anchored": all_mutations_anchored,
        "production_manifest_contains_commissioning_default_0_08": (
            production_has_commission_default
        ),
        "red_canary": red_canary,
        "cases": results,
    }


def main() -> int:
    try:
        result = _run_all()
    except Exception as error:
        result = {
            "schema": "m164-dominance-manifest-commission/v1",
            "status": "FAIL",
            "harness_error": f"{type(error).__name__}: {error}",
        }
    finally:
        if WORK.exists():
            shutil.rmtree(WORK)
    _write_json(OUTPUT, result)
    if result["status"] != "PASS" and "cases" not in result:
        print(json.dumps(result, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": result["status"],
                "cases": len(result["cases"]),
                "checks": len(result["observed_checks"]),
                "missing_checks": result["missing_checks"],
                "failed_cases": result["failed_cases"],
                "red_canary": result["red_canary"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
