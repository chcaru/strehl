"""Generate deterministic sealed evidence for the M171 synthetic commission."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


FROZEN_CONTRACT_SHA256 = (
    "3530035E986B35118731FB2249EB95C32DEC372AA36AFD4F3B1B989F743D1DEF"
)
EVIDENCE_SCHEMA = "m171-reference-admission-evidence-v1"
SEAL_SCHEMA = "m171-reference-admission-evidence-seal-v1"
_PROTECTED_OUTPUT_RELATIVE_PATHS = (
    ".gitattributes",
    "PREREGISTRATION.md",
    "contract.json",
    "admission.py",
    "synthetic.py",
    "commission.py",
    "test_admission.py",
    "verify.py",
    "out/commission.json",
    "out/verification.json",
)

# These are executable commissioning controls.  The commissioner requires each
# assignment to remain a unique complete source line before applying a mutation.
SAMPLING_RATIO_MEAN = 2.08
REFERENCE_NOISE_SIGMA = 0.15
FOCUS_PEAK_INDEX = 2
RAW_RESPONSE_EXPONENT = 1.0
LAGGED_BLOCK_DRIFT = 0.0
ESTIMATED_ROTATION_DEG = 0.015
WEAK_CELL_POWER_MULTIPLIER = 1.0
VECTOR_REFERENCE_TRANSFER = (1.50, 1.50)

_PATHS = ("R1", "R2", "S1", "S2")
_CONTROLS = ("featureless", "flat", "dark")
_SPLITS = (
    "odd_even",
    "contiguous_halves",
    "alternating_four_frame_blocks",
)
_LINEAGE_FIELDS = (
    "evidence_generation_sha256",
    "claim_scope_sha256",
    "sampling_sha256",
    "focus_known_input_sha256",
    "raw_response_known_input_sha256",
    "split_sha256",
    "geometry_sha256",
    "resampler_sha256",
    "nonperiodic_sha256",
    "featureless_control_sha256",
    "flat_control_sha256",
    "dark_control_sha256",
    "R1_source_sha256",
    "R2_source_sha256",
    "S1_source_sha256",
    "S2_source_sha256",
    "R1_calibration_sha256",
    "R2_calibration_sha256",
    "S1_calibration_sha256",
    "S2_calibration_sha256",
)


class SyntheticError(RuntimeError):
    """The requested evidence artifact cannot be generated safely."""


def _strip_windows_extended_prefix(value: str) -> str:
    if os.name != "nt":
        return value
    normalized = value.replace("/", "\\")
    folded = normalized.casefold()
    if folded.startswith("\\\\?\\unc\\"):
        return "\\\\" + normalized[8:]
    if folded.startswith("\\\\?\\"):
        return normalized[4:]
    return normalized


def _path_key(path: os.PathLike[str] | str) -> str:
    value = _strip_windows_extended_prefix(os.fspath(path))
    normalized = os.path.normpath(value)
    if os.name == "nt":
        return os.path.normcase(normalized).casefold()
    return normalized


def _stat_exists(path: pathlib.Path, purpose: str) -> bool:
    try:
        os.stat(path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError as exc:
        raise SyntheticError(
            f"cannot establish {purpose} filesystem identity"
        ) from exc
    return True


def _paths_identical(
    candidate: os.PathLike[str] | str,
    protected: os.PathLike[str] | str,
) -> bool:
    try:
        candidate_path = pathlib.Path(candidate).expanduser().resolve(
            strict=False
        )
        protected_path = pathlib.Path(protected).expanduser().resolve(
            strict=False
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise SyntheticError(
            "cannot resolve evidence output identity"
        ) from exc
    candidate_key = _path_key(candidate_path)
    protected_key = _path_key(protected_path)
    candidate_exists = _stat_exists(
        candidate_path, "evidence output path"
    )
    protected_exists = _stat_exists(
        protected_path, "protected output target"
    )
    if candidate_exists and protected_exists:
        try:
            same_file = os.path.samefile(
                candidate_path, protected_path
            )
        except (OSError, ValueError) as exc:
            if candidate_key == protected_key:
                return True
            raise SyntheticError(
                "cannot establish evidence output filesystem identity"
            ) from exc
        return same_file or candidate_key == protected_key
    return candidate_key == protected_key


def _reject_d_drive(path: os.PathLike[str] | str, purpose: str) -> pathlib.Path:
    raw = os.fspath(path)
    drive, _ = os.path.splitdrive(_strip_windows_extended_prefix(raw))
    if drive.casefold() == "d:":
        raise SyntheticError(f"{purpose} must not use the prohibited drive")
    try:
        resolved = pathlib.Path(raw).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SyntheticError(f"cannot resolve {purpose}") from exc
    resolved_drive, _ = os.path.splitdrive(
        _strip_windows_extended_prefix(os.fspath(resolved))
    )
    if resolved_drive.casefold() == "d:":
        raise SyntheticError(f"{purpose} must not use the prohibited drive")
    return resolved


def _safe_evidence_output(
    output: os.PathLike[str] | str,
    contract_path: os.PathLike[str] | str,
) -> pathlib.Path:
    resolved = _reject_d_drive(output, "evidence output path")
    contract = _reject_d_drive(contract_path, "contract path")
    source_directory = pathlib.Path(__file__).resolve(strict=False).parent
    protected = [(contract, "loaded contract")]
    for directory, location in (
        (contract.parent, "frozen contract directory"),
        (source_directory, "executing source directory"),
    ):
        protected.extend(
            (
                (directory / relative).resolve(strict=False),
                f"{location} {relative}",
            )
            for relative in _PROTECTED_OUTPUT_RELATIVE_PATHS
        )
    for protected_path, label in protected:
        if _paths_identical(resolved, protected_path):
            raise SyntheticError(
                "evidence output must not overwrite protected input "
                f"{label}"
            )
    return resolved


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SyntheticError(f"duplicate JSON member in contract: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise SyntheticError(f"non-finite JSON number in contract: {value}")


def _load_contract(path: os.PathLike[str] | str) -> tuple[dict[str, Any], str]:
    resolved = _reject_d_drive(path, "contract path")
    try:
        with resolved.open("rb") as stream:
            payload = stream.read()
    except OSError as exc:
        raise SyntheticError("cannot read the frozen contract") from exc
    digest = hashlib.sha256(payload).hexdigest().upper()
    if digest != FROZEN_CONTRACT_SHA256:
        raise SyntheticError(
            "contract SHA-256 does not match the frozen M171 contract"
        )
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_json_constant,
        )
    except SyntheticError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SyntheticError("frozen contract is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise SyntheticError("frozen contract root must be an object")
    if value.get("schema") != "m171-reference-admission-contract-v4":
        raise SyntheticError("unsupported M171 contract schema")
    if value.get("schemas", {}).get("evidence") != EVIDENCE_SCHEMA:
        raise SyntheticError("contract names an unsupported evidence schema")
    return value, digest


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest().upper()


def _complex_json(values: np.ndarray) -> list[Any]:
    array = np.asarray(values, dtype=np.complex128)
    return np.stack((array.real, array.imag), axis=-1).tolist()


def _proper_complex_normal(
    rng: np.random.Generator,
    shape: tuple[int, ...],
    sigma: float = 1.0,
) -> np.ndarray:
    """Draw a circular/proper complex normal with E[|z|^2] = sigma^2."""

    return (
        sigma
        * (rng.normal(size=shape) + 1j * rng.normal(size=shape))
        / np.sqrt(2.0)
    )


def _sites(contract: Mapping[str, Any]) -> list[dict[str, str]]:
    sample = contract["sample_contract"]
    session_count = int(sample["session_count"])
    bursts_per_session = int(sample["bursts_per_session"])
    sites_per_burst = int(sample["sites_per_burst"])
    sites = [
        {
            "site_id": f"site-{session_index}-{burst_index}-{site_index}",
            "session_id": f"session-{session_index}",
            "burst_id": f"burst-{session_index}-{burst_index}",
        }
        for session_index in range(session_count)
        for burst_index in range(bursts_per_session)
        for site_index in range(sites_per_burst)
    ]
    if len(sites) != int(sample["site_count"]):
        raise SyntheticError("contract sample hierarchy does not equal site_count")
    return sites


def _allowed_cases(contract: Mapping[str, Any]) -> set[str]:
    mutation_cases = {
        str(mutation["case"]) for mutation in contract.get("mutations", [])
    }
    additional_cases = {
        str(case["case"]) for case in contract.get("additional_cases", [])
    }
    return mutation_cases | additional_cases


def _settings_fingerprint(case: str) -> str:
    settings = {
        "case": case,
        "sampling_ratio_mean": SAMPLING_RATIO_MEAN,
        "reference_noise_sigma": REFERENCE_NOISE_SIGMA,
        "focus_peak_index": FOCUS_PEAK_INDEX,
        "raw_response_exponent": RAW_RESPONSE_EXPONENT,
        "lagged_block_drift": LAGGED_BLOCK_DRIFT,
        "estimated_rotation_deg": ESTIMATED_ROTATION_DEG,
        "weak_cell_power_multiplier": WEAK_CELL_POWER_MULTIPLIER,
        "vector_reference_transfer": list(VECTOR_REFERENCE_TRANSFER),
    }
    encoded = json.dumps(
        settings,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def _lineage(case: str) -> dict[str, str]:
    settings_digest = _settings_fingerprint(case)
    return {
        name: _hash(f"m171:{settings_digest}:{name}") for name in _LINEAGE_FIELDS
    }


def _case_parameters(
    contract: Mapping[str, Any], case: str
) -> tuple[float, np.ndarray, float]:
    fixture = contract["synthetic_fixture"]
    scalar_reference_transfer = float(fixture["reference_transfer"])
    vector_reference_transfer = np.asarray(
        VECTOR_REFERENCE_TRANSFER, dtype=np.float64
    )
    common_mode_sigma = float(fixture["control_common_mode_sigma"])

    if case == "planted_improvement":
        improved = np.asarray(
            fixture["improved_vector_reference_transfer"], dtype=np.float64
        )
        scalar_reference_transfer = float(improved[0])
        vector_reference_transfer = improved
    elif case == "common_mode_false_improvement":
        common_mode_sigma = float(
            fixture["false_improvement_common_mode_sigma"]
        )

    if vector_reference_transfer.shape != (2,):
        raise SyntheticError("vector reference transfer must have dimension two")
    return (
        scalar_reference_transfer,
        vector_reference_transfer,
        common_mode_sigma,
    )


def _focus_transfer(
    rng: np.random.Generator, site_count: int, dimension: int
) -> np.ndarray:
    focus_axis = np.arange(5, dtype=np.float64)
    gains = 0.70 + 0.80 * np.exp(
        -0.5 * ((focus_axis - float(FOCUS_PEAK_INDEX)) / 0.65) ** 2
    )
    site_scale = 1.0 + rng.normal(0.0, 0.004, (site_count, 5))
    transfer = np.zeros(
        (site_count, 5, dimension, dimension), dtype=np.complex128
    )
    for diagonal in range(dimension):
        transfer[:, :, diagonal, diagonal] = gains[np.newaxis, :] * site_scale
    if dimension == 2:
        transfer[:, :, 0, 1] = _proper_complex_normal(
            rng, (site_count, 5), 0.001
        )
        transfer[:, :, 1, 0] = _proper_complex_normal(
            rng, (site_count, 5), 0.001
        )
    return transfer


def _coefficient_controls(
    rng: np.random.Generator,
    site_count: int,
    dimension: int,
    common_mode_sigma: float,
) -> dict[str, dict[str, list[Any]]]:
    controls: dict[str, dict[str, list[Any]]] = {}
    for control_name in _CONTROLS:
        shared = common_mode_sigma * _proper_complex_normal(
            rng, (site_count, dimension)
        )
        values = {
            "R1": shared
            + _proper_complex_normal(rng, (site_count, dimension), 0.01),
            "R2": shared
            + _proper_complex_normal(rng, (site_count, dimension), 0.01),
            "S1": _proper_complex_normal(rng, (site_count, dimension), 0.01),
            "S2": _proper_complex_normal(rng, (site_count, dimension), 0.01),
        }
        controls[control_name] = {
            path_name: _complex_json(values[path_name])
            for path_name in _PATHS
        }
    return controls


def _split_pairs(
    rng: np.random.Generator,
    latent: np.ndarray,
) -> dict[str, dict[str, Any]]:
    site_count, dimension = latent.shape
    pairs: dict[str, dict[str, Any]] = {}
    for split_name in _SPLITS:
        first = latent + _proper_complex_normal(rng, latent.shape, 0.01)
        second = (
            1.01 * np.exp(0.01j) * latent
            + _proper_complex_normal(rng, latent.shape, 0.01)
        )
        controls: dict[str, dict[str, list[Any]]] = {}
        for control_name in _CONTROLS:
            shared = _proper_complex_normal(rng, latent.shape)
            drift_scale = (
                LAGGED_BLOCK_DRIFT
                if split_name == "alternating_four_frame_blocks"
                else 0.0
            )
            shared *= drift_scale
            controls[control_name] = {
                "first": _complex_json(
                    shared
                    + _proper_complex_normal(
                        rng, (site_count, dimension), 0.01
                    )
                ),
                "second": _complex_json(
                    shared
                    + _proper_complex_normal(
                        rng, (site_count, dimension), 0.01
                    )
                ),
            }
        pairs[split_name] = {
            "first": _complex_json(first),
            "second": _complex_json(second),
            "controls": controls,
        }
    return pairs


def build_evidence(contract: Mapping[str, Any], case: str) -> dict[str, Any]:
    """Build one deterministic strict-schema evidence object."""

    if case not in _allowed_cases(contract):
        raise SyntheticError(f"case is not registered by the frozen contract: {case}")
    sample = contract["sample_contract"]
    site_count = int(sample["site_count"])
    sites = _sites(contract)
    fixture = contract["synthetic_fixture"]
    rng = np.random.default_rng(int(contract["bootstrap"]["fixture_seed"]))
    (
        scalar_reference_transfer,
        vector_reference_transfer,
        common_mode_sigma,
    ) = _case_parameters(contract, case)
    scored_transfer_value = float(fixture["scored_transfer"])
    scored_noise_sigma = float(fixture["scored_noise_sigma"])
    lineage = _lineage(case)

    cells: list[dict[str, Any]] = []
    for cell_index, definition in enumerate(contract["cells"]):
        dimension = int(definition["dimension"])
        shape = (site_count, dimension)
        # The vector canary deliberately weakens one transfer direction to
        # 0.70.  Extra latent support keeps that direction above G7's power
        # floor so G8, rather than its prerequisite, owns the intended RED.
        latent_sigma = 1.5 if dimension == 2 else 1.0
        latent = _proper_complex_normal(rng, shape, latent_sigma)
        power_multiplier = (
            WEAK_CELL_POWER_MULTIPLIER if cell_index == 0 else 1.0
        )
        reference_subject = power_multiplier * latent
        if dimension == 2:
            reference_transfer = vector_reference_transfer
        else:
            reference_transfer = np.full(
                dimension, scalar_reference_transfer, dtype=np.float64
            )
        scored_transfer = np.full(
            dimension, scored_transfer_value, dtype=np.float64
        )

        # The common-mode arm is deliberately improvement-shaped: it raises
        # raw R repeat covariance while its matched controls expose the charge.
        reference_common = common_mode_sigma * latent
        coefficients = {
            "R1": reference_subject * reference_transfer
            + reference_common
            + _proper_complex_normal(rng, shape, REFERENCE_NOISE_SIGMA),
            "R2": reference_subject * reference_transfer
            + reference_common
            + _proper_complex_normal(rng, shape, REFERENCE_NOISE_SIGMA),
            "S1": latent * scored_transfer
            + _proper_complex_normal(rng, shape, scored_noise_sigma),
            "S2": latent * scored_transfer
            + _proper_complex_normal(rng, shape, scored_noise_sigma),
        }
        controls = _coefficient_controls(
            rng, site_count, dimension, common_mode_sigma
        )
        transfer = _focus_transfer(rng, site_count, dimension)
        split_pairs = _split_pairs(rng, latent)
        kernel_a = latent + _proper_complex_normal(rng, shape, 0.01)

        cells.append(
            {
                "id": str(definition["id"]),
                "frequency": float(definition["frequency"]),
                "orientation": float(definition["orientation"]),
                "dimension": dimension,
                "coefficients": {
                    path_name: _complex_json(coefficients[path_name])
                    for path_name in _PATHS
                },
                "controls": controls,
                "focus": {
                    "known_input": True,
                    "positions": [-2.0, -1.0, 0.0, 1.0, 2.0],
                    "transfer": _complex_json(transfer),
                    "cross_cell_leakage": [0.01] * site_count,
                },
                "split_pairs": split_pairs,
                "resampler": {
                    "kernel_a": _complex_json(kernel_a),
                    "kernel_b": _complex_json(1.005 * kernel_a),
                },
            }
        )

    sampling_jitter = rng.normal(0.0, 0.006, site_count)
    sampling_jitter -= np.mean(sampling_jitter)
    input_levels = np.linspace(0.0, 1.0, 33)
    scale_error = rng.normal(0.0, 0.01, site_count)
    rotation_error = (
        ESTIMATED_ROTATION_DEG
        + rng.normal(0.0, 0.0005, site_count)
    )
    estimated_sign = 1 if ESTIMATED_ROTATION_DEG >= 0.0 else -1

    return {
        "schema": EVIDENCE_SCHEMA,
        "claim_scope": str(contract["claim_scope"]),
        "sites": sites,
        "lineage": lineage,
        "reductions": {
            path_name: {
                "complete": True,
                "candidate_blind": True,
                "linear": True,
                "source_sha256": lineage[f"{path_name}_source_sha256"],
                "calibration_sha256": lineage[
                    f"{path_name}_calibration_sha256"
                ],
                "reduction_sha256": _hash(
                    f"m171:{_settings_fingerprint(case)}:"
                    f"{path_name}:complete-linear-reduction"
                ),
            }
            for path_name in ("S1", "S2")
        },
        "sampling": {
            "input_only": True,
            "reference_magnification": (
                SAMPLING_RATIO_MEAN + sampling_jitter
            ).tolist(),
            "scored_magnification": [1.0] * site_count,
        },
        "cells": cells,
        "raw_response": {
            "known_input": True,
            "input_levels": input_levels.tolist(),
            "output_levels": (
                0.1 + 2.0 * np.power(input_levels, RAW_RESPONSE_EXPONENT)
            ).tolist(),
            "low_rail_hits": 0,
            "high_rail_hits": 0,
        },
        "geometry": {
            "input_only": True,
            "scored_pixels_native": bool(sample["native_scored_pixels"]),
            "reference_only_resampling": bool(
                sample["reference_only_resampling"]
            ),
            "scale_disagreement_percent": scale_error.tolist(),
            "rotation_disagreement_deg": rotation_error.tolist(),
            "nontranslation_rms_native_px": np.abs(
                rng.normal(0.03, 0.005, site_count)
            ).tolist(),
            "planted_transform_sign": [1] * site_count,
            "estimated_transform_sign": [estimated_sign] * site_count,
        },
        "nonperiodic": {
            "concealed": True,
            "lineage_sha256": lineage["nonperiodic_sha256"],
            "site_ids": [site["site_id"] for site in sites],
        },
    }


def _evidence_bytes(evidence: Mapping[str, Any]) -> bytes:
    try:
        text = json.dumps(
            evidence,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SyntheticError("evidence is not finite JSON") from exc
    return (text + "\n").encode("utf-8")


def write_sealed_evidence(
    output: os.PathLike[str] | str,
    evidence: Mapping[str, Any],
    *,
    contract_path: os.PathLike[str] | str,
) -> str:
    """Write prepared bytes once and return their digest without reopening."""

    resolved = _safe_evidence_output(output, contract_path)
    payload = _evidence_bytes(evidence)
    digest = hashlib.sha256(payload).hexdigest().upper()
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with resolved.open("wb") as stream:
            stream.write(payload)
    except OSError as exc:
        raise SyntheticError("cannot write evidence output") from exc
    return digest


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)
    try:
        contract, contract_sha256 = _load_contract(args.contract)
        output_path = _safe_evidence_output(args.output, args.contract)
        evidence = build_evidence(contract, args.case)
        evidence_sha256 = write_sealed_evidence(
            output_path,
            evidence,
            contract_path=args.contract,
        )
    except SyntheticError as exc:
        failure = {
            "schema": SEAL_SCHEMA,
            "status": "HARNESS_ERROR",
            "error": str(exc),
        }
        print(json.dumps(failure, sort_keys=True, allow_nan=False))
        return 2
    seal = {
        "schema": SEAL_SCHEMA,
        "case": args.case,
        "contract_sha256": contract_sha256,
        "evidence_sha256": evidence_sha256,
        "capture_reads": 0,
    }
    print(json.dumps(seal, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
