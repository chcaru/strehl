"""Fail-closed M164 production-manifest and evidence reader."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
import sys
import types
from pathlib import Path
from typing import Any

import numpy as np


LAUNCHER_CHECKS = {
    "CHECKER_CORE_SHA256",
    "CHECKER_CORE_UNRESOLVABLE",
    "EVIDENCE_UNRESOLVABLE",
    "FREEZE_RECORD_JSON",
    "FREEZE_RECORD_SCHEMA",
    "INPUT_UNRESOLVABLE",
    "LAUNCHER_SHA256",
    "MANIFEST_PATH_BINDING",
    "MANIFEST_SHA256",
}

CORE_CHECKS = {
    "ARTIFACT_PATH_SAFE",
    "ARTIFACT_RESOLVABLE",
    "ARTIFACT_SHA256",
    "CELL_IDS_UNIQUE",
    "CELL_MARGINS_POSITIVE",
    "CLAIM_SCOPE",
    "DIMENSIONS_NONEMPTY",
    "DIMENSION_MEMBER_VALID",
    "DOMINANCE_COMMON_MODE",
    "DOMINANCE_FAMILY",
    "DOMINANCE_POWER",
    "EVIDENCE_CELL_FAMILY",
    "EVIDENCE_CONTROL_CLASSES",
    "EVIDENCE_DESIGN_CONDITION",
    "EVIDENCE_DESIGN_RANK",
    "EVIDENCE_FINITE_VALUES",
    "EVIDENCE_FRAME_COUNTS",
    "EVIDENCE_FRAME_DISJOINT",
    "EVIDENCE_JSON",
    "EVIDENCE_MANIFEST_BINDING",
    "EVIDENCE_MATRIX_SHAPE",
    "EVIDENCE_REDUCTION_BINDING",
    "EVIDENCE_REQUIRED",
    "EVIDENCE_SCHEMA",
    "EVIDENCE_SITE_COUNT",
    "EPSILON_COMMON_RANGE",
    "FAMILY_CARTESIAN",
    "HASH_GROUPS_COMPLETE",
    "INFERENCE_SETTINGS",
    "MANIFEST_JSON",
    "MANIFEST_SCHEMA",
    "MANIFEST_STATUS",
    "POWER_FLOORS_POSITIVE",
    "RANK_CONDITION_BARS",
    "REDUCTION_SPEC",
    "UNRESOLVED_FIELDS",
}

ALL_CHECKS = LAUNCHER_CHECKS | CORE_CHECKS

REQUIRED_HASH_GROUPS = (
    "calibration",
    "target",
    "resampler",
    "geometry",
    "software",
    "seed",
    "checker",
)

DIMENSION_KEYS = (
    "reference_strips",
    "scored_modes",
    "channels",
    "frequencies",
    "orientations",
    "field_partitions",
)

CELL_KEYS = (
    "reference_strip",
    "scored_mode",
    "channel",
    "frequency",
    "orientation",
    "field_partition",
)

TOKEN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reason(
    reasons: list[dict[str, str]],
    code: str,
    pointer: str,
    detail: str,
) -> None:
    reasons.append({"code": code, "pointer": pointer, "detail": detail})


def _json_from_bytes(
    data: bytes,
    *,
    code: str,
    pointer: str,
    reasons: list[dict[str, str]],
) -> Any | None:
    def object_without_duplicates(
        pairs: list[tuple[str, Any]],
    ) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate object key {key!r}")
            value[key] = item
        return value

    try:
        text = data.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=object_without_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard constant {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        _reason(reasons, code, pointer, str(error))
        return None


def _is_real_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _canonical_cell_id(values: tuple[str, ...]) -> str:
    return "__".join(values)


def _base_result(
    *,
    manifest_path: str,
    manifest_sha256: str,
    evidence_path: str | None,
    evidence_sha256: str | None,
) -> dict[str, Any]:
    return {
        "schema": "m164-dominance-verdict/v1",
        "status": "UNMEASURED",
        "claim": "M164_REFERENCE_INFORMATION_DOMINANCE_GX",
        "manifest": {
            "path": manifest_path,
            "sha256": manifest_sha256,
            "verified_bytes_consumed": True,
        },
        "evidence": {
            "path": evidence_path,
            "sha256": evidence_sha256,
            "verified_bytes_consumed": evidence_sha256 is not None,
        },
        "reasons": [],
        "family_result": None,
    }


def _validate_manifest(
    manifest: Any,
    *,
    repository_root: Path,
    runtime_hashes: dict[str, str],
    reasons: list[dict[str, str]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, bytes],
    dict[str, str],
]:
    cells: list[dict[str, Any]] = []
    context: dict[str, Any] = {}
    artifact_bytes: dict[str, bytes] = {}
    artifact_hashes: dict[str, str] = {}

    if not isinstance(manifest, dict):
        _reason(reasons, "MANIFEST_SCHEMA", "$", "manifest must be an object")
        return cells, context, artifact_bytes, artifact_hashes

    if (
        manifest.get("schema") != "m164-dominance-manifest/v1"
        or manifest.get("version") != 1
    ):
        _reason(
            reasons,
            "MANIFEST_SCHEMA",
            "$.schema",
            "schema and version must be m164-dominance-manifest/v1 and 1",
        )

    if manifest.get("status") != "FROZEN":
        _reason(
            reasons,
            "MANIFEST_STATUS",
            "$.status",
            "only FROZEN manifests are executable",
        )

    if manifest.get("claim_scope") != "GX":
        _reason(
            reasons,
            "CLAIM_SCOPE",
            "$.claim_scope",
            "the M164 reader is licensed only for the GX scoped claim",
        )

    dimensions = manifest.get("dimensions")
    valid_dimensions = isinstance(dimensions, dict)
    if not valid_dimensions:
        _reason(
            reasons,
            "DIMENSIONS_NONEMPTY",
            "$.dimensions",
            "dimensions must be an object",
        )
        dimensions = {}

    dimension_values: list[list[str]] = []
    members_valid = True
    for key in DIMENSION_KEYS:
        value = dimensions.get(key)
        if not isinstance(value, list) or not value:
            _reason(
                reasons,
                "DIMENSIONS_NONEMPTY",
                f"$.dimensions.{key}",
                "dimension must be a nonempty list",
            )
            dimension_values.append([])
            members_valid = False
            continue
        if (
            any(not isinstance(item, str) or not TOKEN_RE.fullmatch(item) for item in value)
            or len(set(value)) != len(value)
        ):
            _reason(
                reasons,
                "DIMENSION_MEMBER_VALID",
                f"$.dimensions.{key}",
                "members must be unique lower-case tokens",
            )
            members_valid = False
        dimension_values.append(value)

    raw_cells = manifest.get("cells")
    if not isinstance(raw_cells, list):
        _reason(
            reasons,
            "FAMILY_CARTESIAN",
            "$.cells",
            "cells must be a list",
        )
        raw_cells = []
    elif not raw_cells:
        _reason(
            reasons,
            "FAMILY_CARTESIAN",
            "$.cells",
            "the licensed cell family may not be empty",
        )

    cell_ids: list[str] = []
    cell_tuples: list[tuple[str, ...]] = []
    for index, cell in enumerate(raw_cells):
        pointer = f"$.cells[{index}]"
        if not isinstance(cell, dict):
            _reason(
                reasons,
                "FAMILY_CARTESIAN",
                pointer,
                "cell must be an object",
            )
            continue
        values = tuple(cell.get(key) for key in CELL_KEYS)
        if any(not isinstance(value, str) for value in values):
            _reason(
                reasons,
                "FAMILY_CARTESIAN",
                pointer,
                "cell dimension values must be strings",
            )
            continue
        expected_id = _canonical_cell_id(values)
        cell_id = cell.get("id")
        if not isinstance(cell_id, str):
            _reason(
                reasons,
                "FAMILY_CARTESIAN",
                f"{pointer}.id",
                "cell id must be a string",
            )
            continue
        if cell_id != expected_id:
            _reason(
                reasons,
                "FAMILY_CARTESIAN",
                f"{pointer}.id",
                f"cell id must be {expected_id}",
            )
        cell_ids.append(cell_id)
        cell_tuples.append(values)
        delta_information = cell.get("delta_information")
        delta_transfer = cell.get("delta_transfer")
        if (
            not _is_real_number(delta_information)
            or float(delta_information) <= 0.0
            or not _is_real_number(delta_transfer)
            or float(delta_transfer) <= 0.0
        ):
            _reason(
                reasons,
                "CELL_MARGINS_POSITIVE",
                pointer,
                "both cell margins must be finite and strictly positive",
            )
        cells.append(cell)

    if len(cell_ids) != len(set(cell_ids)):
        _reason(
            reasons,
            "CELL_IDS_UNIQUE",
            "$.cells",
            "cell ids must be unique",
        )

    if members_valid and all(dimension_values):
        expected_tuples = list(itertools.product(*dimension_values))
        if (
            len(cell_tuples) != len(expected_tuples)
            or set(cell_tuples) != set(expected_tuples)
        ):
            _reason(
                reasons,
                "FAMILY_CARTESIAN",
                "$.cells",
                "cells must equal the complete dimension Cartesian product",
            )
        expected_order = {
            values: index for index, values in enumerate(expected_tuples)
        }
        cells.sort(
            key=lambda cell: expected_order.get(
                tuple(cell.get(key) for key in CELL_KEYS),
                len(expected_order),
            )
        )

    thresholds = manifest.get("thresholds")
    if not isinstance(thresholds, dict):
        thresholds = {}

    epsilon_common = thresholds.get("epsilon_common")
    if (
        not _is_real_number(epsilon_common)
        or not 0.0 < float(epsilon_common) < 1.0
    ):
        _reason(
            reasons,
            "EPSILON_COMMON_RANGE",
            "$.thresholds.epsilon_common",
            "epsilon_common must be finite and lie in (0, 1)",
        )

    minimum_signal_power = thresholds.get("minimum_signal_power")
    minimum_noise_power = thresholds.get("minimum_noise_power")
    if (
        not _is_real_number(minimum_signal_power)
        or float(minimum_signal_power) <= 0.0
        or not _is_real_number(minimum_noise_power)
        or float(minimum_noise_power) <= 0.0
    ):
        _reason(
            reasons,
            "POWER_FLOORS_POSITIVE",
            "$.thresholds",
            "signal and noise floors must be finite and strictly positive",
        )

    minimum_rank = thresholds.get("minimum_rank")
    maximum_condition_number = thresholds.get("maximum_condition_number")
    if (
        not isinstance(minimum_rank, int)
        or isinstance(minimum_rank, bool)
        or minimum_rank < 1
        or not _is_real_number(maximum_condition_number)
        or float(maximum_condition_number) < 1.0
    ):
        _reason(
            reasons,
            "RANK_CONDITION_BARS",
            "$.thresholds",
            "minimum_rank must be positive and condition bar at least one",
        )

    minimum_sites = thresholds.get("minimum_sites_per_cell")
    minimum_control_sites = thresholds.get("minimum_control_sites_per_class")
    control_classes = thresholds.get("common_mode_control_classes")
    if (
        not isinstance(minimum_sites, int)
        or isinstance(minimum_sites, bool)
        or minimum_sites < 64
        or not isinstance(minimum_control_sites, int)
        or isinstance(minimum_control_sites, bool)
        or minimum_control_sites < 8
    ):
        _reason(
            reasons,
            "POWER_FLOORS_POSITIVE",
            "$.thresholds",
            "site floors must be integers with at least 64 witness and 8 control sites",
        )
    if (
        not isinstance(control_classes, list)
        or not control_classes
        or any(
            not isinstance(value, str) or not TOKEN_RE.fullmatch(value)
            for value in control_classes
        )
        or len(set(control_classes)) != len(control_classes)
    ):
        _reason(
            reasons,
            "EPSILON_COMMON_RANGE",
            "$.thresholds.common_mode_control_classes",
            "common-mode control classes must be a nonempty unique token list",
        )

    inference = manifest.get("inference")
    if not isinstance(inference, dict):
        inference = {}
    dominance_alpha = inference.get("dominance_alpha")
    common_mode_alpha = inference.get("common_mode_alpha")
    bootstrap_draws = inference.get("bootstrap_draws")
    dominance_seed = inference.get("dominance_seed")
    common_mode_seed = inference.get("common_mode_seed")
    if (
        inference.get("method") != "paired-site-one-sided-max-t"
        or inference.get("quantile_method") != "higher"
        or not _is_real_number(dominance_alpha)
        or not 0.0 < float(dominance_alpha) < 0.5
        or not _is_real_number(common_mode_alpha)
        or not 0.0 < float(common_mode_alpha) < 0.5
        or not isinstance(bootstrap_draws, int)
        or isinstance(bootstrap_draws, bool)
        or bootstrap_draws < 10_000
        or not isinstance(dominance_seed, int)
        or isinstance(dominance_seed, bool)
        or dominance_seed < 0
        or not isinstance(common_mode_seed, int)
        or isinstance(common_mode_seed, bool)
        or common_mode_seed < 0
        or dominance_seed == common_mode_seed
    ):
        _reason(
            reasons,
            "INFERENCE_SETTINGS",
            "$.inference",
            "the frozen max-t method, finite alphas, >=10000 draws, and distinct nonnegative seeds are required",
        )

    reduction = manifest.get("reduction")
    reduction_valid = isinstance(reduction, dict)
    if not reduction_valid:
        reduction = {}
    frame_counts = reduction.get("frame_counts")
    scored_modes = dimensions.get("scored_modes", [])
    scored_counts = (
        frame_counts.get("scored_per_mode_per_repeat")
        if isinstance(frame_counts, dict)
        else None
    )
    if (
        reduction.get("kind") != "scalar-linear-sufficient"
        or not isinstance(reduction.get("artifact_id"), str)
        or not isinstance(frame_counts, dict)
        or not isinstance(
            frame_counts.get("reference_per_strip_per_repeat"), int
        )
        or isinstance(
            frame_counts.get("reference_per_strip_per_repeat"), bool
        )
        or frame_counts.get("reference_per_strip_per_repeat", 0) < 1
        or not isinstance(scored_counts, dict)
        or set(scored_counts) != set(scored_modes)
        or any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
            for value in (scored_counts or {}).values()
        )
    ):
        _reason(
            reasons,
            "REDUCTION_SPEC",
            "$.reduction",
            "a complete scalar-linear-sufficient reduction and exact frame counts are required",
        )

    artifact_groups = manifest.get("artifact_hashes")
    artifact_records: dict[str, dict[str, Any]] = {}
    hashes_structurally_valid = isinstance(artifact_groups, dict)
    if not hashes_structurally_valid:
        artifact_groups = {}
    for group in REQUIRED_HASH_GROUPS:
        records = artifact_groups.get(group)
        if not isinstance(records, list) or not records:
            _reason(
                reasons,
                "HASH_GROUPS_COMPLETE",
                f"$.artifact_hashes.{group}",
                "required hash group must be nonempty",
            )
            continue
        for index, record in enumerate(records):
            pointer = f"$.artifact_hashes.{group}[{index}]"
            if not isinstance(record, dict):
                _reason(
                    reasons,
                    "HASH_GROUPS_COMPLETE",
                    pointer,
                    "artifact record must be an object",
                )
                continue
            artifact_id = record.get("id")
            path_text = record.get("path")
            expected_sha = record.get("sha256")
            if (
                not isinstance(artifact_id, str)
                or not TOKEN_RE.fullmatch(artifact_id)
                or artifact_id in artifact_records
                or not isinstance(path_text, str)
                or not isinstance(expected_sha, str)
                or not SHA256_RE.fullmatch(expected_sha)
            ):
                _reason(
                    reasons,
                    "HASH_GROUPS_COMPLETE",
                    pointer,
                    "artifact ids must be unique tokens with path and lowercase SHA-256",
                )
                continue
            artifact_records[artifact_id] = record

    required_ids = {"dominance-core", "reader-core", "reader-launcher"}
    if not required_ids.issubset(artifact_records):
        _reason(
            reasons,
            "HASH_GROUPS_COMPLETE",
            "$.artifact_hashes",
            "dominance-core, reader-core, and reader-launcher hashes are required",
        )
    if (
        isinstance(reduction.get("artifact_id"), str)
        and reduction.get("artifact_id") not in artifact_records
    ):
        _reason(
            reasons,
            "REDUCTION_SPEC",
            "$.reduction.artifact_id",
            "reduction artifact id must resolve in artifact_hashes",
        )

    for artifact_id, record in artifact_records.items():
        path_text = record["path"]
        relative = Path(path_text)
        if relative.is_absolute() or ".." in relative.parts or relative.drive:
            _reason(
                reasons,
                "ARTIFACT_PATH_SAFE",
                f"$.artifact_hashes[{artifact_id}]",
                "artifact path must be a repository-relative path without parent traversal",
            )
            continue
        try:
            resolved = (repository_root / relative).resolve(strict=True)
            resolved.relative_to(repository_root)
        except (FileNotFoundError, OSError):
            _reason(
                reasons,
                "ARTIFACT_RESOLVABLE",
                f"$.artifact_hashes[{artifact_id}]",
                f"artifact cannot be resolved: {path_text}",
            )
            continue
        except ValueError:
            _reason(
                reasons,
                "ARTIFACT_PATH_SAFE",
                f"$.artifact_hashes[{artifact_id}]",
                "artifact resolves outside the repository",
            )
            continue

        if artifact_id in runtime_hashes:
            actual_sha = runtime_hashes[artifact_id]
            data = b""
        else:
            try:
                data = resolved.read_bytes()
            except OSError as error:
                _reason(
                    reasons,
                    "ARTIFACT_RESOLVABLE",
                    f"$.artifact_hashes[{artifact_id}]",
                    str(error),
                )
                continue
            actual_sha = _sha256(data)
        if actual_sha != record["sha256"]:
            _reason(
                reasons,
                "ARTIFACT_SHA256",
                f"$.artifact_hashes[{artifact_id}]",
                f"expected {record['sha256']}, consumed {actual_sha}",
            )
            continue
        artifact_bytes[artifact_id] = data
        artifact_hashes[artifact_id] = actual_sha

    unresolved = manifest.get("unresolved")
    if not isinstance(unresolved, list):
        _reason(
            reasons,
            "UNRESOLVED_FIELDS",
            "$.unresolved",
            "unresolved must be an empty list",
        )
    elif unresolved:
        for index, item in enumerate(unresolved):
            detail = (
                json.dumps(item, sort_keys=True)
                if isinstance(item, (dict, list))
                else str(item)
            )
            _reason(
                reasons,
                "UNRESOLVED_FIELDS",
                f"$.unresolved[{index}]",
                detail,
            )

    context.update(
        {
            "dimensions": dimensions,
            "thresholds": thresholds,
            "inference": inference,
            "reduction": reduction,
            "artifact_records": artifact_records,
            "artifact_hashes": artifact_hashes,
            "control_classes": control_classes,
        }
    )
    return cells, context, artifact_bytes, artifact_hashes


def _complex_vector(
    value: Any,
    *,
    pointer: str,
    reasons: list[dict[str, str]],
) -> np.ndarray | None:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        _reason(
            reasons,
            "EVIDENCE_MATRIX_SHAPE",
            pointer,
            "complex vector must be encoded as [[real, imag], ...]",
        )
        return None
    if array.ndim != 2 or array.shape[1] != 2:
        _reason(
            reasons,
            "EVIDENCE_MATRIX_SHAPE",
            pointer,
            "complex vector must have shape [sites, 2]",
        )
        return None
    if not np.all(np.isfinite(array)):
        _reason(
            reasons,
            "EVIDENCE_FINITE_VALUES",
            pointer,
            "complex vector contains a non-finite value",
        )
        return None
    return array[:, 0] + 1j * array[:, 1]


def _matrix_from_cell_map(
    value: Any,
    *,
    cell_ids: list[str],
    pointer: str,
    reasons: list[dict[str, str]],
) -> np.ndarray | None:
    if not isinstance(value, dict) or set(value) != set(cell_ids):
        _reason(
            reasons,
            "EVIDENCE_CELL_FAMILY",
            pointer,
            "cell-keyed matrix must contain exactly the licensed cell ids",
        )
        return None
    vectors: list[np.ndarray] = []
    for cell_id in cell_ids:
        vector = _complex_vector(
            value[cell_id],
            pointer=f"{pointer}.{cell_id}",
            reasons=reasons,
        )
        if vector is None:
            return None
        vectors.append(vector)
    lengths = {len(vector) for vector in vectors}
    if len(lengths) != 1:
        _reason(
            reasons,
            "EVIDENCE_MATRIX_SHAPE",
            pointer,
            "all cells must have the same number of physical sites",
        )
        return None
    return np.column_stack(vectors)


def _validate_lineage(
    lineage: Any,
    *,
    dimensions: dict[str, Any],
    reduction: dict[str, Any],
    reasons: list[dict[str, str]],
) -> None:
    if not isinstance(lineage, dict):
        _reason(
            reasons,
            "EVIDENCE_FRAME_COUNTS",
            "$.lineage",
            "lineage must be an object",
        )
        return
    reference = lineage.get("reference")
    scored = lineage.get("scored")
    candidate_inputs = lineage.get("candidate_inputs")
    if (
        not isinstance(reference, dict)
        or not isinstance(scored, dict)
        or not isinstance(candidate_inputs, list)
    ):
        _reason(
            reasons,
            "EVIDENCE_FRAME_COUNTS",
            "$.lineage",
            "reference, scored, and candidate_inputs lineage are required",
        )
        return

    counts = reduction["frame_counts"]
    expected_ref = counts["reference_per_strip_per_repeat"]
    expected_scored = counts["scored_per_mode_per_repeat"]
    all_a: list[str] = []
    all_b: list[str] = []
    count_failure = False

    if set(reference) != set(dimensions["reference_strips"]):
        count_failure = True
    else:
        for strip in dimensions["reference_strips"]:
            passes = reference.get(strip)
            if not isinstance(passes, dict) or set(passes) != {"A", "B"}:
                count_failure = True
                continue
            for label, sink in (("A", all_a), ("B", all_b)):
                frame_ids = passes[label]
                if (
                    not isinstance(frame_ids, list)
                    or len(frame_ids) != expected_ref
                    or any(
                        not isinstance(frame_id, str) or not frame_id
                        for frame_id in frame_ids
                    )
                    or len(set(frame_ids)) != len(frame_ids)
                ):
                    count_failure = True
                    continue
                sink.extend(frame_ids)

    if set(scored) != set(dimensions["scored_modes"]):
        count_failure = True
    else:
        for mode in dimensions["scored_modes"]:
            passes = scored.get(mode)
            if not isinstance(passes, dict) or set(passes) != {"A", "B"}:
                count_failure = True
                continue
            expected = expected_scored[mode]
            for label, sink in (("A", all_a), ("B", all_b)):
                frame_ids = passes[label]
                if (
                    not isinstance(frame_ids, list)
                    or len(frame_ids) != expected
                    or any(
                        not isinstance(frame_id, str) or not frame_id
                        for frame_id in frame_ids
                    )
                    or len(set(frame_ids)) != len(frame_ids)
                ):
                    count_failure = True
                    continue
                sink.extend(frame_ids)

    if count_failure:
        _reason(
            reasons,
            "EVIDENCE_FRAME_COUNTS",
            "$.lineage",
            "every strip/mode A/B frame list must match the frozen complete-input count",
        )
        return

    candidate_valid = all(
        isinstance(frame_id, str) and frame_id for frame_id in candidate_inputs
    )
    if (
        not candidate_valid
        or set(all_a) & set(all_b)
        or set(all_a + all_b) & set(candidate_inputs)
    ):
        _reason(
            reasons,
            "EVIDENCE_FRAME_DISJOINT",
            "$.lineage",
            "A/B sources must be disjoint and S witness frames must not contact candidate inputs",
        )


def _validate_evidence(
    evidence: Any,
    *,
    manifest_sha256: str,
    cells: list[dict[str, Any]],
    context: dict[str, Any],
    reasons: list[dict[str, str]],
) -> dict[str, Any]:
    prepared: dict[str, Any] = {}
    if not isinstance(evidence, dict):
        _reason(
            reasons,
            "EVIDENCE_SCHEMA",
            "$",
            "evidence must be an object",
        )
        return prepared

    if evidence.get("schema") != "m164-dominance-evidence/v1":
        _reason(
            reasons,
            "EVIDENCE_SCHEMA",
            "$.schema",
            "schema must be m164-dominance-evidence/v1",
        )
    if evidence.get("manifest_sha256") != manifest_sha256:
        _reason(
            reasons,
            "EVIDENCE_MANIFEST_BINDING",
            "$.manifest_sha256",
            "evidence is not bound to the consumed manifest bytes",
        )

    reduction_artifact_id = context["reduction"].get("artifact_id")
    expected_reduction_sha = context["artifact_hashes"].get(
        reduction_artifact_id
    )
    if evidence.get("reduction_artifact_sha256") != expected_reduction_sha:
        _reason(
            reasons,
            "EVIDENCE_REDUCTION_BINDING",
            "$.reduction_artifact_sha256",
            "evidence does not name the frozen reduction artifact hash",
        )

    cell_ids = [cell["id"] for cell in cells]
    if evidence.get("cell_ids") != cell_ids:
        _reason(
            reasons,
            "EVIDENCE_CELL_FAMILY",
            "$.cell_ids",
            "evidence cell ids and order must exactly equal the manifest family",
        )

    witness = evidence.get("witness")
    witness_matrices: dict[str, np.ndarray] = {}
    if not isinstance(witness, dict):
        _reason(
            reasons,
            "EVIDENCE_MATRIX_SHAPE",
            "$.witness",
            "witness must be an object",
        )
    else:
        required = ("reference_1", "reference_2", "scored_1", "scored_2")
        if set(witness) != set(required):
            _reason(
                reasons,
                "EVIDENCE_MATRIX_SHAPE",
                "$.witness",
                "four and only four witness matrices are required",
            )
        for name in required:
            if name in witness:
                matrix = _matrix_from_cell_map(
                    witness[name],
                    cell_ids=cell_ids,
                    pointer=f"$.witness.{name}",
                    reasons=reasons,
                )
                if matrix is not None:
                    witness_matrices[name] = matrix

    if len(witness_matrices) == 4:
        shapes = {matrix.shape for matrix in witness_matrices.values()}
        if len(shapes) != 1:
            _reason(
                reasons,
                "EVIDENCE_MATRIX_SHAPE",
                "$.witness",
                "all witness matrices must have identical shape",
            )
        else:
            sites = next(iter(shapes))[0]
            if sites < context["thresholds"]["minimum_sites_per_cell"]:
                _reason(
                    reasons,
                    "EVIDENCE_SITE_COUNT",
                    "$.witness",
                    "witness has fewer physical sites than the frozen floor",
                )

    design = evidence.get("design")
    design_vectors: dict[str, np.ndarray] = {}
    if not isinstance(design, dict) or set(design) != set(cell_ids):
        _reason(
            reasons,
            "EVIDENCE_CELL_FAMILY",
            "$.design",
            "design must contain exactly the licensed cell ids",
        )
    else:
        for cell_id in cell_ids:
            vector = _complex_vector(
                design[cell_id],
                pointer=f"$.design.{cell_id}",
                reasons=reasons,
            )
            if vector is not None:
                design_vectors[cell_id] = vector

    if len(design_vectors) == len(cell_ids):
        expected_sites = (
            next(iter(witness_matrices.values())).shape[0]
            if witness_matrices
            else None
        )
        for cell_id, vector in design_vectors.items():
            if expected_sites is not None and len(vector) != expected_sites:
                _reason(
                    reasons,
                    "EVIDENCE_MATRIX_SHAPE",
                    f"$.design.{cell_id}",
                    "design and witness site counts differ",
                )
                continue
            real_design = np.column_stack((vector.real, vector.imag))
            real_design -= np.mean(real_design, axis=0, keepdims=True)
            rank = int(np.linalg.matrix_rank(real_design))
            if rank < context["thresholds"]["minimum_rank"]:
                _reason(
                    reasons,
                    "EVIDENCE_DESIGN_RANK",
                    f"$.design.{cell_id}",
                    f"observed rank {rank} is below the frozen bar",
                )
                continue
            condition = float(np.linalg.cond(real_design))
            if (
                not math.isfinite(condition)
                or condition
                > context["thresholds"]["maximum_condition_number"]
            ):
                _reason(
                    reasons,
                    "EVIDENCE_DESIGN_CONDITION",
                    f"$.design.{cell_id}",
                    f"observed condition {condition} exceeds the frozen bar",
                )

    controls = evidence.get("controls")
    control_matrices: dict[str, dict[str, np.ndarray]] = {}
    expected_classes = context["control_classes"]
    if (
        not isinstance(controls, dict)
        or not isinstance(expected_classes, list)
        or set(controls) != set(expected_classes)
    ):
        _reason(
            reasons,
            "EVIDENCE_CONTROL_CLASSES",
            "$.controls",
            "control classes must exactly equal the frozen family",
        )
    else:
        required = ("reference_1", "reference_2", "scored_1", "scored_2")
        for class_name in expected_classes:
            class_value = controls[class_name]
            if not isinstance(class_value, dict) or set(class_value) != set(
                required
            ):
                _reason(
                    reasons,
                    "EVIDENCE_CONTROL_CLASSES",
                    f"$.controls.{class_name}",
                    "each class needs four and only four path/repeat matrices",
                )
                continue
            matrices: dict[str, np.ndarray] = {}
            for name in required:
                matrix = _matrix_from_cell_map(
                    class_value[name],
                    cell_ids=cell_ids,
                    pointer=f"$.controls.{class_name}.{name}",
                    reasons=reasons,
                )
                if matrix is not None:
                    matrices[name] = matrix
            if len(matrices) == 4:
                shapes = {matrix.shape for matrix in matrices.values()}
                if len(shapes) != 1:
                    _reason(
                        reasons,
                        "EVIDENCE_MATRIX_SHAPE",
                        f"$.controls.{class_name}",
                        "control matrices in a class must share shape",
                    )
                elif (
                    next(iter(shapes))[0]
                    < context["thresholds"][
                        "minimum_control_sites_per_class"
                    ]
                ):
                    _reason(
                        reasons,
                        "EVIDENCE_SITE_COUNT",
                        f"$.controls.{class_name}",
                        "control class has fewer sites than the frozen floor",
                    )
                else:
                    control_matrices[class_name] = matrices

    _validate_lineage(
        evidence.get("lineage"),
        dimensions=context["dimensions"],
        reduction=context["reduction"],
        reasons=reasons,
    )

    prepared.update(
        {
            "cell_ids": cell_ids,
            "witness": witness_matrices,
            "controls": control_matrices,
        }
    )
    return prepared


def _load_dominance_module(source: bytes) -> dict[str, Any]:
    module_name = "m164_verified_dominance"
    module = types.ModuleType(module_name)
    module.__file__ = "<verified-dominance-bytes>"
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        exec(
            compile(source, "<verified-dominance-bytes>", "exec"),
            module.__dict__,
        )
    finally:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
    return module.__dict__


def _evaluate(
    *,
    cells: list[dict[str, Any]],
    context: dict[str, Any],
    prepared: dict[str, Any],
    dominance_source: bytes,
) -> tuple[dict[str, Any], str | None]:
    module = _load_dominance_module(dominance_source)
    inference = context["inference"]
    thresholds = context["thresholds"]
    controls = prepared["controls"]
    cell_count = len(cells)
    reference_bounds: list[np.ndarray] = []
    scored_bounds: list[np.ndarray] = []
    control_results: dict[str, Any] = {}
    class_alpha = float(inference["common_mode_alpha"]) / len(controls)

    for class_index, class_name in enumerate(context["control_classes"]):
        matrices = controls[class_name]
        result = module["estimate_common_mode_bounds"](
            matrices["reference_1"],
            matrices["reference_2"],
            matrices["scored_1"],
            matrices["scored_2"],
            alpha=class_alpha,
            bootstrap_draws=inference["bootstrap_draws"],
            bootstrap_seed=inference["common_mode_seed"] + class_index,
            minimum_power=max(
                float(thresholds["minimum_signal_power"]),
                float(thresholds["minimum_noise_power"]),
            ),
        )
        control_results[class_name] = result
        reference_bounds.append(np.asarray(result["reference_ucb"]))
        scored_bounds.append(np.asarray(result["scored_ucb"]))

    reference_common = np.max(np.vstack(reference_bounds), axis=0)
    scored_common = np.max(np.vstack(scored_bounds), axis=0)
    if reference_common.shape != (cell_count,) or scored_common.shape != (
        cell_count,
    ):
        raise ValueError("common-mode family size differs from cell family")

    config = module["GateConfig"](
        delta_information=np.asarray(
            [cell["delta_information"] for cell in cells], dtype=np.float64
        ),
        delta_transfer=np.asarray(
            [cell["delta_transfer"] for cell in cells], dtype=np.float64
        ),
        bootstrap_draws=inference["bootstrap_draws"],
        bootstrap_seed=inference["dominance_seed"],
        dominance_alpha=inference["dominance_alpha"],
        minimum_power=max(
            float(thresholds["minimum_signal_power"]),
            float(thresholds["minimum_noise_power"]),
        ),
        maximum_common_fraction=thresholds["epsilon_common"],
    )
    witness = prepared["witness"]
    family_result = module["evaluate_dominance"](
        witness["reference_1"],
        witness["reference_2"],
        witness["scored_1"],
        witness["scored_2"],
        reference_common,
        scored_common,
        config,
    )
    output = {
        "cell_ids": prepared["cell_ids"],
        "common_mode": {
            "classes": control_results,
            "reference_family_ucb": [
                float(value) for value in reference_common
            ],
            "scored_family_ucb": [float(value) for value in scored_common],
            "family_alpha": inference["common_mode_alpha"],
            "class_alpha": class_alpha,
        },
        "dominance": family_result,
    }
    return output, family_result.get("failure")


def run(
    *,
    repository_root: str,
    manifest_path: str,
    manifest_bytes: bytes,
    manifest_sha256: str,
    evidence_path: str | None,
    evidence_bytes: bytes | None,
    runtime_hashes: dict[str, str],
) -> dict[str, Any]:
    """Consume already captured bytes and return a persistent family verdict."""

    evidence_sha256 = (
        _sha256(evidence_bytes) if evidence_bytes is not None else None
    )
    output = _base_result(
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
        evidence_path=evidence_path,
        evidence_sha256=evidence_sha256,
    )
    reasons: list[dict[str, str]] = output["reasons"]
    manifest = _json_from_bytes(
        manifest_bytes,
        code="MANIFEST_JSON",
        pointer="$manifest",
        reasons=reasons,
    )
    if manifest is None:
        return output

    cells, context, artifact_bytes, _ = _validate_manifest(
        manifest,
        repository_root=Path(repository_root).resolve(strict=True),
        runtime_hashes=runtime_hashes,
        reasons=reasons,
    )
    if reasons:
        return output

    if evidence_bytes is None:
        _reason(
            reasons,
            "EVIDENCE_REQUIRED",
            "$evidence",
            "a frozen manifest requires an evidence payload",
        )
        return output

    evidence = _json_from_bytes(
        evidence_bytes,
        code="EVIDENCE_JSON",
        pointer="$evidence",
        reasons=reasons,
    )
    if evidence is None:
        return output
    prepared = _validate_evidence(
        evidence,
        manifest_sha256=manifest_sha256,
        cells=cells,
        context=context,
        reasons=reasons,
    )
    if reasons:
        return output

    try:
        family_result, failure = _evaluate(
            cells=cells,
            context=context,
            prepared=prepared,
            dominance_source=artifact_bytes["dominance-core"],
        )
    except (KeyError, TypeError, ValueError, FloatingPointError) as error:
        _reason(
            reasons,
            "DOMINANCE_FAMILY",
            "$evidence",
            f"verified dominance core refused: {error}",
        )
        return output

    output["family_result"] = family_result
    if family_result["dominance"]["status"] == "PASS":
        output["status"] = "PASS"
        return output

    if failure == "NONPOSITIVE_POWER_OR_NOISE":
        code = "DOMINANCE_POWER"
    elif failure == "COMMON_MODE_BOUND":
        code = "DOMINANCE_COMMON_MODE"
    else:
        code = "DOMINANCE_FAMILY"
    _reason(
        reasons,
        code,
        "$evidence",
        f"M164 family refusal: {failure}",
    )
    return output
