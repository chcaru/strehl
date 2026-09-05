"""Strict, fail-closed evaluator for the frozen M171 admission experiment.

This module consumes synthetic commissioning evidence only.  It never opens a
capture and it never computes a candidate score.

Evidence JSON schema (``m171-reference-admission-evidence-v1``)
================================================================

JSON numbers below are finite real numbers (JSON booleans are not numbers).
``complex[N,D]`` means an array with shape ``[N, D, 2]`` whose last axis is
``[real, imag]``. ``matrix[N,P,D,D]`` adds a final ``[real, imag]`` axis.
All arrays are ordered by the top-level ``sites`` array.

::

  {
    "schema": "m171-reference-admission-evidence-v1",
    "claim_scope": "GX_REFERENCE_CONDITIONAL" | "DIGITAL_K",
    "sites": [
      {"site_id": str, "session_id": str, "burst_id": str}, ... 64
    ],
    "lineage": {
      "evidence_generation_sha256": sha256,
      "claim_scope_sha256": sha256,
      "sampling_sha256": sha256,
      "focus_known_input_sha256": sha256,
      "raw_response_known_input_sha256": sha256,
      "split_sha256": sha256,
      "geometry_sha256": sha256,
      "resampler_sha256": sha256,
      "nonperiodic_sha256": sha256,
      "featureless_control_sha256": sha256,
      "flat_control_sha256": sha256,
      "dark_control_sha256": sha256,
      "R1_source_sha256": sha256, "R2_source_sha256": sha256,
      "S1_source_sha256": sha256, "S2_source_sha256": sha256,
      "R1_calibration_sha256": sha256, "R2_calibration_sha256": sha256,
      "S1_calibration_sha256": sha256, "S2_calibration_sha256": sha256
    },
    "reductions": {
      "S1": {
        "complete": true, "candidate_blind": true, "linear": true,
        "source_sha256": sha256, "calibration_sha256": sha256,
        "reduction_sha256": sha256
      },
      "S2": { ... same fields ... }
    },
    "sampling": {
      "input_only": bool,
      "reference_magnification": real[64],
      "scored_magnification": real[64]
    },
    "cells": [
      {
        "id": str, "frequency": real, "orientation": real, "dimension": 1|2,
        "coefficients": {
          "R1": complex[64,D], "R2": complex[64,D],
          "S1": complex[64,D], "S2": complex[64,D]
        },
        "controls": {
          "featureless": {"R1": complex[64,D], "R2": complex[64,D],
                          "S1": complex[64,D], "S2": complex[64,D]},
          "flat":        { ... }, "dark": { ... }
        },
        "focus": {
          "known_input": bool,
          "positions": real[5],
          "transfer": matrix[64,5,D,D],
          "cross_cell_leakage": real[64]
        },
        "split_pairs": {
          "odd_even": {
            "first": complex[64,D], "second": complex[64,D],
            "controls": {
              "featureless": {"first": complex[64,D],
                              "second": complex[64,D]},
              "flat": { ... }, "dark": { ... }
            }
          },
          "contiguous_halves": { ... },
          "alternating_four_frame_blocks": { ... }
        },
        "resampler": {
          "kernel_a": complex[64,D], "kernel_b": complex[64,D]
        }
      }, ... exactly the 16 frozen contract cells
    ],
    "raw_response": {
      "known_input": bool,
      "input_levels": real[33], "output_levels": real[33],
      "low_rail_hits": nonnegative integer,
      "high_rail_hits": nonnegative integer
    },
    "geometry": {
      "input_only": bool, "scored_pixels_native": bool,
      "reference_only_resampling": bool,
      "scale_disagreement_percent": real[64],
      "rotation_disagreement_deg": real[64],
      "nontranslation_rms_native_px": real[64],
      "planted_transform_sign": (-1|1)[64],
      "estimated_transform_sign": (-1|1)[64]
    },
    "nonperiodic": {
      "concealed": bool,
      "lineage_sha256": sha256,
      "site_ids": str[64]
    },
    "q_baseline": {                         # optional; never sufficient for DIGITAL_K
      "schema": "m171-q-baseline-v1",
      "payload": {
        "cell_ids": str[16],
        "q": {cell_id: complex[D,D], ...}
      },
      "payload_sha256": sha256               # canonical JSON payload hash
    }
  }

Every acquisition and calibration hash is required.  Gate G5, rather than the
schema validator, decides whether those hashes establish disjoint lineages.
The S1/S2 declarations are required to be complete, candidate-blind, and
linear; a false declaration is valid evidence but cannot pass G8.

Production calibration
======================

``profile="production"`` requires a *separate* sealed
``m171-reference-admission-production-calibration-v1`` object.  Callers should
load it with :func:`load_sealed_json`, or pass its canonical SHA-256 through
``calibration_manifest_sha256``.  Its ``production_thresholds`` object must
contain every name in ``contract["production_thresholds_required"]``:

* ``licensed_cells``: the exact 16 cell ids;
* ``sampling_optical_systematic``: ``artifact_sha256``,
  ``sampling_ratio_lcb_min``, ``optical_systematic_ratio_bound``,
  ``scale_disagreement_percent_max``, ``rotation_disagreement_deg_max``, and
  ``nontranslation_rms_native_px_max``;
* ``reference_snr_floor`` and ``focus_transfer_floor``: positive numbers;
* ``focus_conditioning_ceiling``: ``condition_number_max`` and
  ``cross_cell_leakage_max``;
* ``raw_response_calibration``: ``artifact_sha256`` and
  ``max_normalized_residual``;
* ``split_agreement_tolerances``: ``magnitude_relative_max`` and
  ``phase_rad_max``;
* ``common_mode_allowance`` and ``resampler_allowance``: nonnegative numbers;
* ``nonperiodic_power_floor``: ``power_lcb_min`` and
  ``duplicate_site_correlation_max``;
* ``delta_information_by_cell`` and ``delta_transfer_by_cell``: complete maps;
* ``reduction_sufficiency``: an ``artifact_sha256`` and
  ``complete_candidate_blind_linear: true``; and
* ``noise_estimand_convention``: ``difference_factor: 0.5`` and the literal
  ``"half_split_difference_variance"``.

An absent, unsealed, or incomplete production manifest yields eight evaluated
``UNMEASURED`` records.  Synthetic thresholds are never substituted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


FROZEN_CONTRACT_SHA256 = (
    "3530035E986B35118731FB2249EB95C32DEC372AA36AFD4F3B1B989F743D1DEF"
)
_FROZEN_CONTRACT_CANONICAL_SHA256 = (
    "E88658E39E8E48514666300E1E64C42B258EF540828EB71FEA0BE0AA66AC7F5F"
)
_CONTRACT_SCHEMA = "m171-reference-admission-contract-v4"
_EVIDENCE_SCHEMA = "m171-reference-admission-evidence-v1"
_RESULT_SCHEMA = "m171-reference-admission-result-v4"
_PRODUCTION_SCHEMA = "m171-reference-admission-production-calibration-v1"
_Q_SCHEMA = "m171-q-baseline-v1"
_LOWER_BOUND_QUANTILE = 0.975
_PATHS = ("R1", "R2", "S1", "S2")
_CONTROLS = ("featureless", "flat", "dark")
_SPLITS = ("odd_even", "contiguous_halves", "alternating_four_frame_blocks")
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class HarnessError(RuntimeError):
    """Malformed or unbound input; the CLI maps this exception to exit code 2."""


class _SealedJSON(dict):
    """A mapping carrying immutable metadata for the exact bytes it parsed."""

    __slots__ = ("_sealed_bytes", "_sealed_sha256")

    def __init__(
        self, value: Mapping[str, Any], digest: str, payload: bytes
    ) -> None:
        super().__init__(value)
        object.__setattr__(self, "_sealed_sha256", digest.upper())
        object.__setattr__(self, "_sealed_bytes", payload)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("sealed JSON metadata is immutable")

    @property
    def sealed_sha256(self) -> str:
        """SHA-256 of :attr:`sealed_bytes`."""

        return self._sealed_sha256

    @property
    def sealed_bytes(self) -> bytes:
        """The exact immutable byte payload read, hashed, and parsed once."""

        return self._sealed_bytes


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HarnessError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise HarnessError(f"non-finite JSON number: {value}")


def _load_sealed_json(path: os.PathLike[str] | str, expected_sha256: str) -> _SealedJSON:
    if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(
        expected_sha256
    ):
        raise HarnessError("expected_sha256 must be 64 hexadecimal characters")
    try:
        with open(os.fspath(path), "rb") as stream:
            payload = stream.read()
    except (OSError, TypeError) as exc:
        raise HarnessError(f"cannot read sealed JSON: {exc}") from exc

    actual = hashlib.sha256(payload).hexdigest().upper()
    if actual != expected_sha256.upper():
        raise HarnessError(
            f"sealed JSON SHA-256 mismatch: expected {expected_sha256.upper()}, "
            f"got {actual}"
        )

    try:
        decoded = payload.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_json_constant,
        )
    except HarnessError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessError(f"invalid sealed JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise HarnessError("sealed JSON root must be an object")
    return _SealedJSON(value, actual, payload)


def load_sealed_json(
    path: os.PathLike[str] | str, expected_sha256: str
) -> _SealedJSON:
    """Read/hash/parse once and retain the exact immutable sealed bytes."""

    return _load_sealed_json(path, expected_sha256)


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HarnessError(f"value is not canonical finite JSON: {exc}") from exc


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().upper()


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise HarnessError(f"{path} must be an object")
    return value


def _keys(
    value: Any,
    path: str,
    required: Sequence[str],
    optional: Sequence[str] = (),
) -> Mapping[str, Any]:
    obj = _mapping(value, path)
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(obj))
    unknown = sorted(set(obj) - allowed)
    if missing:
        raise HarnessError(f"{path} missing required member(s): {', '.join(missing)}")
    if unknown:
        raise HarnessError(f"{path} has unknown member(s): {', '.join(unknown)}")
    return obj


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise HarnessError(f"{path} must be a nonempty string")
    return value


def _boolean(value: Any, path: str) -> bool:
    if type(value) is not bool:
        raise HarnessError(f"{path} must be a JSON boolean")
    return value


def _number(value: Any, path: str) -> float:
    if type(value) not in (int, float):
        raise HarnessError(f"{path} must be a JSON number (not boolean)")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise HarnessError(f"{path} is not a finite number") from exc
    if not math.isfinite(result):
        raise HarnessError(f"{path} must be finite")
    return result


def _integer(value: Any, path: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise HarnessError(f"{path} must be a JSON integer (not boolean)")
    if minimum is not None and value < minimum:
        raise HarnessError(f"{path} must be at least {minimum}")
    return value


def _sha256(value: Any, path: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise HarnessError(f"{path} must be a 64-character SHA-256")
    return value.upper()


def _object_array(value: Any, shape: tuple[int, ...], path: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=object)
    except (TypeError, ValueError) as exc:
        raise HarnessError(f"{path} is not a rectangular array") from exc
    if array.shape != shape:
        raise HarnessError(f"{path} has shape {array.shape}; expected {shape}")
    return array


def _real_array(value: Any, shape: tuple[int, ...], path: str) -> np.ndarray:
    source = _object_array(value, shape, path)
    result = np.empty(shape, dtype=np.float64)
    for index, item in np.ndenumerate(source):
        result[index] = _number(item, f"{path}{index}")
    return result


def _complex_array(
    value: Any, shape: tuple[int, ...], path: str
) -> np.ndarray:
    encoded = _real_array(value, shape + (2,), path)
    return encoded[..., 0] + 1j * encoded[..., 1]


def _string_array(value: Any, length: int, path: str) -> list[str]:
    source = _object_array(value, (length,), path)
    return [_string(item, f"{path}[{index}]") for index, item in enumerate(source)]


def _validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, Mapping):
        raise HarnessError("contract must be an object")
    digest = _canonical_sha256(dict(contract))
    if digest != _FROZEN_CONTRACT_CANONICAL_SHA256:
        raise HarnessError(
            "contract is not the frozen M171 contract "
            f"(canonical SHA-256 {digest})"
        )
    if contract.get("schema") != _CONTRACT_SCHEMA:
        raise HarnessError("contract schema is not the frozen M171 v4 schema")
    schemas = contract.get("schemas")
    if not isinstance(schemas, Mapping) or (
        schemas.get("evidence") != _EVIDENCE_SCHEMA
        or schemas.get("result") != _RESULT_SCHEMA
        or schemas.get("commission")
        != "m171-reference-admission-commission-v4"
        or schemas.get("verification")
        != "m171-reference-admission-verification-v4"
    ):
        raise HarnessError("contract artifact schema bindings are not M171 v4")
    inference = contract.get("inference_contract")
    if not isinstance(inference, Mapping) or (
        inference.get("max_t_studentized_numerator")
        != "bootstrap_minus_observed"
        or inference.get("lower_bound")
        != "observed_minus_critical_times_standard_error"
        or inference.get("upper_max_t_studentized_numerator")
        != "observed_minus_bootstrap"
        or inference.get("upper_bound")
        != "observed_plus_critical_times_standard_error"
        or inference.get("g2_coordinate") != "natural_log_reference_snr"
        or inference.get("g2_reported_bound")
        != "exp_coordinate_lower_bound"
    ):
        raise HarnessError("contract inference bindings are not M171 v4")
    digital_k = contract.get("digital_k_policy")
    if not isinstance(digital_k, Mapping) or (
        digital_k.get("status") != "UNMEASURED"
        or digital_k.get("reason")
        != "DIGITAL_K_IDENTIFICATION_NOT_COMMISSIONED"
    ):
        raise HarnessError("contract DIGITAL_K refusal is not frozen")
    return dict(contract)


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


def _validate_lineage(value: Any) -> dict[str, str]:
    obj = _keys(value, "evidence.lineage", _LINEAGE_FIELDS)
    return {
        name: _sha256(obj[name], f"evidence.lineage.{name}")
        for name in _LINEAGE_FIELDS
    }


def _validate_reductions(
    value: Any, lineage: Mapping[str, str]
) -> tuple[dict[str, Any], bool]:
    obj = _keys(value, "evidence.reductions", ("S1", "S2"))
    result: dict[str, Any] = {}
    sufficient = True
    for path_name in ("S1", "S2"):
        item = _keys(
            obj[path_name],
            f"evidence.reductions.{path_name}",
            (
                "complete",
                "candidate_blind",
                "linear",
                "source_sha256",
                "calibration_sha256",
                "reduction_sha256",
            ),
        )
        parsed = {
            "complete": _boolean(
                item["complete"], f"evidence.reductions.{path_name}.complete"
            ),
            "candidate_blind": _boolean(
                item["candidate_blind"],
                f"evidence.reductions.{path_name}.candidate_blind",
            ),
            "linear": _boolean(
                item["linear"], f"evidence.reductions.{path_name}.linear"
            ),
            "source_sha256": _sha256(
                item["source_sha256"],
                f"evidence.reductions.{path_name}.source_sha256",
            ),
            "calibration_sha256": _sha256(
                item["calibration_sha256"],
                f"evidence.reductions.{path_name}.calibration_sha256",
            ),
            "reduction_sha256": _sha256(
                item["reduction_sha256"],
                f"evidence.reductions.{path_name}.reduction_sha256",
            ),
        }
        if parsed["source_sha256"] != lineage[f"{path_name}_source_sha256"]:
            raise HarnessError(
                f"evidence.reductions.{path_name}.source_sha256 does not "
                "match lineage"
            )
        if (
            parsed["calibration_sha256"]
            != lineage[f"{path_name}_calibration_sha256"]
        ):
            raise HarnessError(
                f"evidence.reductions.{path_name}.calibration_sha256 does not "
                "match lineage"
            )
        sufficient &= bool(
            parsed["complete"] and parsed["candidate_blind"] and parsed["linear"]
        )
        result[path_name] = parsed
    return result, sufficient


def _validate_sites(
    value: Any, contract: Mapping[str, Any]
) -> tuple[list[dict[str, str]], list[list[np.ndarray]]]:
    expected_count = int(contract["sample_contract"]["site_count"])
    source = _object_array(value, (expected_count,), "evidence.sites")
    sites: list[dict[str, str]] = []
    site_ids: set[str] = set()
    burst_to_session: dict[str, str] = {}
    grouped: dict[str, dict[str, list[int]]] = {}

    for index, raw in enumerate(source):
        item = _keys(
            raw,
            f"evidence.sites[{index}]",
            ("site_id", "session_id", "burst_id"),
        )
        site_id = _string(item["site_id"], f"evidence.sites[{index}].site_id")
        session_id = _string(
            item["session_id"], f"evidence.sites[{index}].session_id"
        )
        burst_id = _string(item["burst_id"], f"evidence.sites[{index}].burst_id")
        if site_id in site_ids:
            raise HarnessError(f"duplicate site_id: {site_id}")
        site_ids.add(site_id)
        prior_session = burst_to_session.setdefault(burst_id, session_id)
        if prior_session != session_id:
            raise HarnessError(f"burst_id {burst_id} occurs in multiple sessions")
        grouped.setdefault(session_id, {}).setdefault(burst_id, []).append(index)
        sites.append(
            {
                "site_id": site_id,
                "session_id": session_id,
                "burst_id": burst_id,
            }
        )

    expected_sessions = int(contract["sample_contract"]["session_count"])
    expected_bursts = int(contract["sample_contract"]["bursts_per_session"])
    expected_sites = int(contract["sample_contract"]["sites_per_burst"])
    if len(grouped) != expected_sessions:
        raise HarnessError(
            f"evidence.sites has {len(grouped)} sessions; expected "
            f"{expected_sessions}"
        )

    hierarchy: list[list[np.ndarray]] = []
    for session_id in sorted(grouped):
        bursts = grouped[session_id]
        if len(bursts) != expected_bursts:
            raise HarnessError(
                f"session {session_id} has {len(bursts)} bursts; expected "
                f"{expected_bursts}"
            )
        session_groups: list[np.ndarray] = []
        for burst_id in sorted(bursts):
            indices = bursts[burst_id]
            if len(indices) != expected_sites:
                raise HarnessError(
                    f"burst {burst_id} has {len(indices)} sites; expected "
                    f"{expected_sites}"
                )
            session_groups.append(np.asarray(indices, dtype=np.intp))
        hierarchy.append(session_groups)
    return sites, hierarchy


def _validate_control_paths(
    value: Any, path: str, site_count: int, dimension: int
) -> dict[str, np.ndarray]:
    obj = _keys(value, path, _PATHS)
    return {
        name: _complex_array(
            obj[name], (site_count, dimension), f"{path}.{name}"
        )
        for name in _PATHS
    }


def _validate_split_pair(
    value: Any, path: str, site_count: int, dimension: int
) -> dict[str, Any]:
    obj = _keys(value, path, ("first", "second", "controls"))
    controls_obj = _keys(obj["controls"], f"{path}.controls", _CONTROLS)
    controls: dict[str, dict[str, np.ndarray]] = {}
    for control_name in _CONTROLS:
        pair = _keys(
            controls_obj[control_name],
            f"{path}.controls.{control_name}",
            ("first", "second"),
        )
        controls[control_name] = {
            arm: _complex_array(
                pair[arm],
                (site_count, dimension),
                f"{path}.controls.{control_name}.{arm}",
            )
            for arm in ("first", "second")
        }
    return {
        "first": _complex_array(
            obj["first"], (site_count, dimension), f"{path}.first"
        ),
        "second": _complex_array(
            obj["second"], (site_count, dimension), f"{path}.second"
        ),
        "controls": controls,
    }


def _validate_cell(
    value: Any,
    index: int,
    expected: Mapping[str, Any],
    site_count: int,
) -> dict[str, Any]:
    path = f"evidence.cells[{index}]"
    obj = _keys(
        value,
        path,
        (
            "id",
            "frequency",
            "orientation",
            "dimension",
            "coefficients",
            "controls",
            "focus",
            "split_pairs",
            "resampler",
        ),
    )
    cell_id = _string(obj["id"], f"{path}.id")
    frequency = _number(obj["frequency"], f"{path}.frequency")
    orientation = _number(obj["orientation"], f"{path}.orientation")
    dimension = _integer(obj["dimension"], f"{path}.dimension", minimum=1)
    if cell_id != expected["id"]:
        raise HarnessError(
            f"{path}.id is {cell_id}; expected frozen cell {expected['id']}"
        )
    if frequency != float(expected["frequency"]):
        raise HarnessError(f"{path}.frequency does not match frozen contract")
    if orientation != float(expected["orientation"]):
        raise HarnessError(f"{path}.orientation does not match frozen contract")
    if dimension != int(expected["dimension"]):
        raise HarnessError(f"{path}.dimension does not match frozen contract")

    coefficients_obj = _keys(obj["coefficients"], f"{path}.coefficients", _PATHS)
    coefficients = {
        name: _complex_array(
            coefficients_obj[name],
            (site_count, dimension),
            f"{path}.coefficients.{name}",
        )
        for name in _PATHS
    }

    controls_obj = _keys(obj["controls"], f"{path}.controls", _CONTROLS)
    controls = {
        name: _validate_control_paths(
            controls_obj[name],
            f"{path}.controls.{name}",
            site_count,
            dimension,
        )
        for name in _CONTROLS
    }

    focus_obj = _keys(
        obj["focus"],
        f"{path}.focus",
        ("known_input", "positions", "transfer", "cross_cell_leakage"),
    )
    positions = _real_array(
        focus_obj["positions"], (5,), f"{path}.focus.positions"
    )
    if not np.all(np.diff(positions) > 0.0):
        raise HarnessError(f"{path}.focus.positions must be strictly increasing")
    focus = {
        "known_input": _boolean(
            focus_obj["known_input"], f"{path}.focus.known_input"
        ),
        "positions": positions,
        "transfer": _complex_array(
            focus_obj["transfer"],
            (site_count, 5, dimension, dimension),
            f"{path}.focus.transfer",
        ),
        "cross_cell_leakage": _real_array(
            focus_obj["cross_cell_leakage"],
            (site_count,),
            f"{path}.focus.cross_cell_leakage",
        ),
    }
    if np.any(focus["cross_cell_leakage"] < 0.0):
        raise HarnessError(f"{path}.focus.cross_cell_leakage must be nonnegative")

    split_obj = _keys(obj["split_pairs"], f"{path}.split_pairs", _SPLITS)
    split_pairs = {
        name: _validate_split_pair(
            split_obj[name],
            f"{path}.split_pairs.{name}",
            site_count,
            dimension,
        )
        for name in _SPLITS
    }

    resampler_obj = _keys(
        obj["resampler"], f"{path}.resampler", ("kernel_a", "kernel_b")
    )
    resampler = {
        name: _complex_array(
            resampler_obj[name],
            (site_count, dimension),
            f"{path}.resampler.{name}",
        )
        for name in ("kernel_a", "kernel_b")
    }
    return {
        "id": cell_id,
        "frequency": frequency,
        "orientation": orientation,
        "dimension": dimension,
        "coefficients": coefficients,
        "controls": controls,
        "focus": focus,
        "split_pairs": split_pairs,
        "resampler": resampler,
    }


def _validate_q_baseline(
    value: Any, contract_cells: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    obj = _keys(
        value, "evidence.q_baseline", ("schema", "payload", "payload_sha256")
    )
    if obj["schema"] != _Q_SCHEMA:
        raise HarnessError("evidence.q_baseline.schema is not supported")
    payload = _keys(
        obj["payload"], "evidence.q_baseline.payload", ("cell_ids", "q")
    )
    expected_ids = [str(cell["id"]) for cell in contract_cells]
    cell_ids = _string_array(
        payload["cell_ids"], len(expected_ids), "evidence.q_baseline.payload.cell_ids"
    )
    if cell_ids != expected_ids or len(set(cell_ids)) != len(cell_ids):
        raise HarnessError(
            "evidence.q_baseline.payload.cell_ids must be the frozen cell order"
        )
    q_obj = _keys(payload["q"], "evidence.q_baseline.payload.q", expected_ids)
    q: dict[str, np.ndarray] = {}
    for cell in contract_cells:
        cell_id = str(cell["id"])
        dimension = int(cell["dimension"])
        q[cell_id] = _complex_array(
            q_obj[cell_id],
            (dimension, dimension),
            f"evidence.q_baseline.payload.q.{cell_id}",
        )
    expected_digest = _sha256(
        obj["payload_sha256"], "evidence.q_baseline.payload_sha256"
    )
    actual_digest = _canonical_sha256(dict(payload))
    if expected_digest != actual_digest:
        raise HarnessError(
            "evidence.q_baseline payload SHA-256 mismatch: "
            f"expected {expected_digest}, got {actual_digest}"
        )
    return {
        "schema": _Q_SCHEMA,
        "payload_sha256": expected_digest,
        "cell_ids": cell_ids,
        "q": q,
    }


def _validate_evidence(
    evidence: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    obj = _keys(
        evidence,
        "evidence",
        (
            "schema",
            "claim_scope",
            "sites",
            "lineage",
            "reductions",
            "sampling",
            "cells",
            "raw_response",
            "geometry",
            "nonperiodic",
        ),
        ("q_baseline",),
    )
    if obj["schema"] != _EVIDENCE_SCHEMA:
        raise HarnessError(f"unsupported evidence schema: {obj['schema']!r}")
    claim_scope = _string(obj["claim_scope"], "evidence.claim_scope")
    if claim_scope not in ("GX_REFERENCE_CONDITIONAL", "DIGITAL_K"):
        raise HarnessError(f"unsupported claim_scope: {claim_scope}")

    sites, hierarchy = _validate_sites(obj["sites"], contract)
    site_count = len(sites)
    lineage = _validate_lineage(obj["lineage"])
    reductions, reduction_sufficient = _validate_reductions(
        obj["reductions"], lineage
    )

    sampling_obj = _keys(
        obj["sampling"],
        "evidence.sampling",
        ("input_only", "reference_magnification", "scored_magnification"),
    )
    sampling = {
        "input_only": _boolean(
            sampling_obj["input_only"], "evidence.sampling.input_only"
        ),
        "reference_magnification": _real_array(
            sampling_obj["reference_magnification"],
            (site_count,),
            "evidence.sampling.reference_magnification",
        ),
        "scored_magnification": _real_array(
            sampling_obj["scored_magnification"],
            (site_count,),
            "evidence.sampling.scored_magnification",
        ),
    }
    if np.any(sampling["reference_magnification"] <= 0.0) or np.any(
        sampling["scored_magnification"] <= 0.0
    ):
        raise HarnessError("sampling magnifications must be strictly positive")

    contract_cells = list(contract["cells"])
    raw_cells = _object_array(
        obj["cells"], (len(contract_cells),), "evidence.cells"
    )
    raw_ids: list[str] = []
    for index, raw in enumerate(raw_cells):
        raw_obj = _mapping(raw, f"evidence.cells[{index}]")
        if "id" not in raw_obj:
            raise HarnessError(f"evidence.cells[{index}] missing required member: id")
        raw_ids.append(_string(raw_obj["id"], f"evidence.cells[{index}].id"))
    if len(set(raw_ids)) != len(raw_ids):
        duplicates = sorted({value for value in raw_ids if raw_ids.count(value) > 1})
        raise HarnessError(f"duplicate cell id(s): {', '.join(duplicates)}")
    expected_ids = [str(cell["id"]) for cell in contract_cells]
    if set(raw_ids) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(raw_ids))
        extra = sorted(set(raw_ids) - set(expected_ids))
        raise HarnessError(
            f"evidence.cells does not match frozen family; missing={missing}, "
            f"extra={extra}"
        )
    by_id = {str(_mapping(raw, "cell")["id"]): raw for raw in raw_cells}
    cells = [
        _validate_cell(by_id[str(expected["id"])], index, expected, site_count)
        for index, expected in enumerate(contract_cells)
    ]

    response_obj = _keys(
        obj["raw_response"],
        "evidence.raw_response",
        (
            "known_input",
            "input_levels",
            "output_levels",
            "low_rail_hits",
            "high_rail_hits",
        ),
    )
    raw_response = {
        "known_input": _boolean(
            response_obj["known_input"], "evidence.raw_response.known_input"
        ),
        "input_levels": _real_array(
            response_obj["input_levels"], (33,), "evidence.raw_response.input_levels"
        ),
        "output_levels": _real_array(
            response_obj["output_levels"],
            (33,),
            "evidence.raw_response.output_levels",
        ),
        "low_rail_hits": _integer(
            response_obj["low_rail_hits"],
            "evidence.raw_response.low_rail_hits",
            minimum=0,
        ),
        "high_rail_hits": _integer(
            response_obj["high_rail_hits"],
            "evidence.raw_response.high_rail_hits",
            minimum=0,
        ),
    }
    if not np.all(np.diff(raw_response["input_levels"]) > 0.0):
        raise HarnessError("raw_response.input_levels must be strictly increasing")

    geometry_obj = _keys(
        obj["geometry"],
        "evidence.geometry",
        (
            "input_only",
            "scored_pixels_native",
            "reference_only_resampling",
            "scale_disagreement_percent",
            "rotation_disagreement_deg",
            "nontranslation_rms_native_px",
            "planted_transform_sign",
            "estimated_transform_sign",
        ),
    )
    geometry: dict[str, Any] = {
        name: _boolean(geometry_obj[name], f"evidence.geometry.{name}")
        for name in (
            "input_only",
            "scored_pixels_native",
            "reference_only_resampling",
        )
    }
    for name in (
        "scale_disagreement_percent",
        "rotation_disagreement_deg",
        "nontranslation_rms_native_px",
    ):
        geometry[name] = _real_array(
            geometry_obj[name], (site_count,), f"evidence.geometry.{name}"
        )
    for name in ("planted_transform_sign", "estimated_transform_sign"):
        signs_source = _object_array(
            geometry_obj[name], (site_count,), f"evidence.geometry.{name}"
        )
        signs = np.empty(site_count, dtype=np.int8)
        for index, item in enumerate(signs_source):
            parsed = _integer(item, f"evidence.geometry.{name}[{index}]")
            if parsed not in (-1, 1):
                raise HarnessError(
                    f"evidence.geometry.{name}[{index}] must be -1 or 1"
                )
            signs[index] = parsed
        geometry[name] = signs
    if np.any(geometry["nontranslation_rms_native_px"] < 0.0):
        raise HarnessError(
            "geometry.nontranslation_rms_native_px must be nonnegative"
        )

    nonperiodic_obj = _keys(
        obj["nonperiodic"],
        "evidence.nonperiodic",
        ("concealed", "lineage_sha256", "site_ids"),
    )
    nonperiodic_site_ids = _string_array(
        nonperiodic_obj["site_ids"], site_count, "evidence.nonperiodic.site_ids"
    )
    expected_site_ids = [site["site_id"] for site in sites]
    if nonperiodic_site_ids != expected_site_ids:
        raise HarnessError(
            "evidence.nonperiodic.site_ids must exactly match evidence.sites order"
        )
    if len(set(nonperiodic_site_ids)) != site_count:
        raise HarnessError("evidence.nonperiodic.site_ids contains duplicates")
    nonperiodic = {
        "concealed": _boolean(
            nonperiodic_obj["concealed"], "evidence.nonperiodic.concealed"
        ),
        "lineage_sha256": _sha256(
            nonperiodic_obj["lineage_sha256"],
            "evidence.nonperiodic.lineage_sha256",
        ),
        "site_ids": nonperiodic_site_ids,
    }
    if nonperiodic["lineage_sha256"] != lineage["nonperiodic_sha256"]:
        raise HarnessError("nonperiodic lineage hash does not match lineage record")

    q_baseline = (
        _validate_q_baseline(obj["q_baseline"], contract_cells)
        if "q_baseline" in obj
        else None
    )
    q_baseline_independent = bool(
        q_baseline is not None
        and q_baseline["payload_sha256"] not in set(lineage.values())
    )
    return {
        "schema": _EVIDENCE_SCHEMA,
        "claim_scope": claim_scope,
        "sites": sites,
        "hierarchy": hierarchy,
        "lineage": lineage,
        "reductions": reductions,
        "reduction_sufficient": reduction_sufficient,
        "sampling": sampling,
        "cells": cells,
        "raw_response": raw_response,
        "geometry": geometry,
        "nonperiodic": nonperiodic,
        "q_baseline": q_baseline,
        "q_baseline_independent": q_baseline_independent,
        "fixture_stats": {},
    }


_BOOTSTRAP_INDEX_CACHE: dict[tuple[Any, ...], np.ndarray] = {}


def _bootstrap_indices(
    hierarchy: Sequence[Sequence[np.ndarray]], draws: int, seed: int
) -> np.ndarray:
    signature = tuple(
        tuple(tuple(int(index) for index in burst) for burst in session)
        for session in hierarchy
    )
    key = (signature, draws, seed)
    cached = _BOOTSTRAP_INDEX_CACHE.get(key)
    if cached is not None:
        return cached

    rng = np.random.default_rng(seed)
    session_count = len(hierarchy)
    bursts_per_session = len(hierarchy[0])
    sites_per_burst = len(hierarchy[0][0])
    result = np.empty(
        (draws, session_count * bursts_per_session * sites_per_burst),
        dtype=np.intp,
    )
    for draw in range(draws):
        cursor = 0
        sampled_sessions = rng.integers(0, session_count, size=session_count)
        for session_index in sampled_sessions:
            session = hierarchy[int(session_index)]
            sampled_bursts = rng.integers(
                0, len(session), size=bursts_per_session
            )
            for burst_index in sampled_bursts:
                burst = session[int(burst_index)]
                sampled_sites = rng.integers(
                    0, len(burst), size=sites_per_burst
                )
                result[draw, cursor : cursor + sites_per_burst] = burst[
                    sampled_sites
                ]
                cursor += sites_per_burst
    result.setflags(write=False)
    _BOOTSTRAP_INDEX_CACHE[key] = result
    return result


def _hermitian_cross_covariance(
    first: np.ndarray, second: np.ndarray, indices: np.ndarray | None = None
) -> np.ndarray:
    if indices is None:
        x = first[np.newaxis, ...]
        y = second[np.newaxis, ...]
    else:
        x = first[indices]
        y = second[indices]
    x = x - np.mean(x, axis=1, keepdims=True)
    y = y - np.mean(y, axis=1, keepdims=True)
    covariance = np.einsum(
        "bni,bnj->bij", x.conj(), y, optimize=True
    ) / x.shape[1]
    return 0.5 * (covariance + np.swapaxes(covariance.conj(), -1, -2))


def _noise_covariance(
    first: np.ndarray,
    second: np.ndarray,
    difference_factor: float,
    indices: np.ndarray | None = None,
) -> np.ndarray:
    if indices is None:
        difference = (first - second)[np.newaxis, ...]
    else:
        difference = first[indices] - second[indices]
    difference = difference - np.mean(difference, axis=1, keepdims=True)
    covariance = difference_factor * np.einsum(
        "bni,bnj->bij", difference.conj(), difference, optimize=True
    ) / difference.shape[1]
    return 0.5 * (covariance + np.swapaxes(covariance.conj(), -1, -2))


def _path_stats(
    cell: Mapping[str, Any],
    path_prefix: str,
    difference_factor: float,
    indices: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    coefficients = cell["coefficients"]
    return (
        _hermitian_cross_covariance(
            coefficients[f"{path_prefix}1"],
            coefficients[f"{path_prefix}2"],
            indices,
        ),
        _noise_covariance(
            coefficients[f"{path_prefix}1"],
            coefficients[f"{path_prefix}2"],
            difference_factor,
            indices,
        ),
    )


def _matrix_abs_size(matrices: np.ndarray) -> np.ndarray:
    eigenvalues = np.linalg.eigvalsh(matrices)
    return np.max(np.abs(eigenvalues), axis=-1)


def _control_sizes(
    cell: Mapping[str, Any], path_prefix: str, indices: np.ndarray | None
) -> np.ndarray:
    sizes = []
    for control_name in _CONTROLS:
        control = cell["controls"][control_name]
        covariance = _hermitian_cross_covariance(
            control[f"{path_prefix}1"],
            control[f"{path_prefix}2"],
            indices,
        )
        sizes.append(_matrix_abs_size(covariance))
    return np.max(np.stack(sizes, axis=-1), axis=-1)


def _higher_quantile(values: np.ndarray, probability: float) -> float:
    return float(np.quantile(values, probability, method="higher"))


def _simultaneous_lcb(
    observed: np.ndarray, bootstrap: np.ndarray
) -> tuple[np.ndarray | None, dict[str, Any]]:
    observed = np.asarray(observed, dtype=np.float64)
    bootstrap = np.asarray(bootstrap, dtype=np.float64)
    if (
        bootstrap.ndim != 2
        or observed.ndim != 1
        or bootstrap.shape[1] != observed.size
        or not np.all(np.isfinite(observed))
        or not np.all(np.isfinite(bootstrap))
    ):
        return None, {"valid": False, "failure": "NONFINITE_OR_SHAPE"}
    standard_error = np.std(bootstrap, axis=0, ddof=1)
    if np.any(~np.isfinite(standard_error)) or np.any(standard_error <= 0.0):
        return None, {
            "valid": False,
            "failure": "ZERO_OR_NONFINITE_STANDARD_ERROR",
            "standard_error": [_finite_or_none(value) for value in standard_error],
        }
    studentized = (bootstrap - observed[np.newaxis, :]) / standard_error
    maximum = np.max(studentized, axis=1)
    critical = _higher_quantile(maximum, _LOWER_BOUND_QUANTILE)
    lower = observed - critical * standard_error
    return lower, {
        "valid": True,
        "critical_value": critical,
        "standard_error": [float(value) for value in standard_error],
        "studentized_numerator": "bootstrap_minus_observed",
        "quantile_probability": _LOWER_BOUND_QUANTILE,
        "quantile_method": "higher",
    }


def _simultaneous_upper(
    observed: np.ndarray, bootstrap: np.ndarray, alpha: float
) -> tuple[np.ndarray | None, dict[str, Any]]:
    observed = np.asarray(observed, dtype=np.float64)
    bootstrap = np.asarray(bootstrap, dtype=np.float64)
    if (
        bootstrap.ndim != 2
        or observed.ndim != 1
        or bootstrap.shape[1] != observed.size
        or not np.all(np.isfinite(observed))
        or not np.all(np.isfinite(bootstrap))
    ):
        return None, {"valid": False, "failure": "NONFINITE_OR_SHAPE"}
    standard_error = np.std(bootstrap, axis=0, ddof=1)
    if np.any(~np.isfinite(standard_error)) or np.any(standard_error <= 0.0):
        return None, {
            "valid": False,
            "failure": "ZERO_OR_NONFINITE_STANDARD_ERROR",
            "standard_error": [_finite_or_none(value) for value in standard_error],
        }
    studentized = (observed[np.newaxis, :] - bootstrap) / standard_error
    maximum = np.max(studentized, axis=1)
    critical = _higher_quantile(maximum, 1.0 - alpha)
    upper = observed + critical * standard_error
    return upper, {
        "valid": True,
        "critical_value": critical,
        "standard_error": [float(value) for value in standard_error],
        "studentized_numerator": "observed_minus_bootstrap",
        "upper_bound": "observed_plus_critical_times_standard_error",
        "quantile_probability": 1.0 - alpha,
        "quantile_method": "higher",
    }


def _finite_or_none(value: Any) -> float | None:
    try:
        converted = float(np.real(value))
    except (TypeError, ValueError, OverflowError):
        return None
    return converted if math.isfinite(converted) else None


def _eigen_summary(matrix: np.ndarray) -> dict[str, Any]:
    eigenvalues = np.linalg.eigvalsh(matrix)
    minimum = float(eigenvalues[0])
    maximum = float(eigenvalues[-1])
    condition = None if minimum <= 0.0 else maximum / minimum
    return {
        "eigenvalues": [float(value) for value in eigenvalues],
        "minimum_eigenvalue": minimum,
        "condition_number": _finite_or_none(condition),
    }


def _spd_batch(
    matrices: np.ndarray, condition_ceiling: float
) -> tuple[bool, np.ndarray, np.ndarray]:
    eigenvalues = np.linalg.eigvalsh(matrices)
    minimum = eigenvalues[..., 0]
    maximum = eigenvalues[..., -1]
    with np.errstate(divide="ignore", invalid="ignore"):
        condition = maximum / minimum
    valid = bool(
        np.all(np.isfinite(eigenvalues))
        and np.all(minimum > 0.0)
        and np.all(np.isfinite(condition))
        and np.all(condition <= condition_ceiling)
    )
    return valid, minimum, condition


def _inverse_sqrt_hermitian(matrices: np.ndarray) -> np.ndarray:
    eigenvalues, eigenvectors = np.linalg.eigh(matrices)
    scales = 1.0 / np.sqrt(eigenvalues)
    return (eigenvectors * scales[..., np.newaxis, :]) @ np.swapaxes(
        eigenvectors.conj(), -1, -2
    )


def _information_operator(signal: np.ndarray, noise: np.ndarray) -> np.ndarray:
    inverse_sqrt = _inverse_sqrt_hermitian(noise)
    whitened = inverse_sqrt @ signal @ inverse_sqrt
    whitened = 0.5 * (whitened + np.swapaxes(whitened.conj(), -1, -2))
    eigenvalues, eigenvectors = np.linalg.eigh(whitened)
    information_eigenvalues = 0.5 * np.log2(1.0 + eigenvalues)
    return (eigenvectors * information_eigenvalues[..., np.newaxis, :]) @ np.swapaxes(
        eigenvectors.conj(), -1, -2
    )


def _smallest_generalized_eigenvalue(
    numerator: np.ndarray, denominator: np.ndarray
) -> np.ndarray:
    denominator_inverse_sqrt = _inverse_sqrt_hermitian(denominator)
    whitened = denominator_inverse_sqrt @ numerator @ denominator_inverse_sqrt
    whitened = 0.5 * (whitened + np.swapaxes(whitened.conj(), -1, -2))
    return np.linalg.eigvalsh(whitened)[..., 0]


def _common_mode_bounds(
    context: Mapping[str, Any],
    contract: Mapping[str, Any],
    bootstrap_indices: np.ndarray,
) -> tuple[dict[tuple[str, str], float] | None, dict[str, Any]]:
    observed_values: list[float] = []
    bootstrap_columns: list[np.ndarray] = []
    labels: list[tuple[str, str]] = []
    for cell in context["cells"]:
        for path_prefix in ("R", "S"):
            observed = _control_sizes(cell, path_prefix, None)[0]
            bootstrap = _control_sizes(cell, path_prefix, bootstrap_indices)
            observed_values.append(float(observed))
            bootstrap_columns.append(np.asarray(bootstrap, dtype=np.float64))
            labels.append((cell["id"], path_prefix))
    observed_array = np.asarray(observed_values, dtype=np.float64)
    bootstrap_array = np.stack(bootstrap_columns, axis=1)
    upper, max_t = _simultaneous_upper(
        observed_array,
        bootstrap_array,
        float(contract["bootstrap"]["common_mode_family_alpha"]),
    )
    diagnostics = {
        "family_alpha": float(contract["bootstrap"]["common_mode_family_alpha"]),
        "draws": int(contract["bootstrap"]["draws"]),
        "max_t": max_t,
        "point_estimates": {
            f"{cell_id}:{path_prefix}": float(value)
            for (cell_id, path_prefix), value in zip(labels, observed_array)
        },
    }
    if upper is None:
        diagnostics["upper_bounds"] = None
        return None, diagnostics
    bounds = {
        label: float(value) for label, value in zip(labels, np.asarray(upper))
    }
    diagnostics["upper_bounds"] = {
        f"{cell_id}:{path_prefix}": value
        for (cell_id, path_prefix), value in bounds.items()
    }
    return bounds, diagnostics


def _gate_record(
    gate_id: str,
    name: str,
    reasons: Sequence[str],
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    unique_reasons = list(dict.fromkeys(reasons))
    passed = not unique_reasons
    return {
        "id": gate_id,
        "name": name,
        "status": "PASS" if passed else "UNMEASURED",
        "evaluated": True,
        "reason_codes": [] if passed else unique_reasons,
        "claim_value": "ESTABLISHED" if passed else None,
        "diagnostics": dict(diagnostics),
    }


def _gate_g1(
    context: Mapping[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    bootstrap_indices: np.ndarray,
) -> dict[str, Any]:
    sampling = context["sampling"]
    ratio = (
        sampling["reference_magnification"] / sampling["scored_magnification"]
    )
    observed = np.asarray([float(np.mean(ratio))])
    bootstrap = np.mean(ratio[bootstrap_indices], axis=1)[:, np.newaxis]
    lower, max_t = _simultaneous_lcb(
        observed,
        bootstrap,
    )
    reasons: list[str] = []
    if not sampling["input_only"]:
        reasons.append("INPUT_ONLY_SAMPLING_NOT_ESTABLISHED")
    if lower is None:
        reasons.append("SAMPLING_BOOTSTRAP_INVALID")
        lower_value = None
    else:
        lower_value = float(lower[0])
        adjusted_lower = lower_value - float(
            thresholds["sampling_optical_systematic_bound"]
        )
        if adjusted_lower < float(thresholds["sampling_ratio_lcb_min"]):
            reasons.append("SAMPLING_RATIO_NOT_ESTABLISHED")
    if lower is None:
        adjusted_lower = None
    diagnostics = {
        "ratio_mean": float(observed[0]),
        "ratio_minimum": float(np.min(ratio)),
        "simultaneous_lcb": lower_value,
        "optical_systematic_ratio_bound": float(
            thresholds["sampling_optical_systematic_bound"]
        ),
        "systematic_adjusted_lcb": adjusted_lower,
        "threshold": float(thresholds["sampling_ratio_lcb_min"]),
        "max_t": max_t,
    }
    return _gate_record("G1", "SUBJECT_SAMPLING_RATIO", reasons, diagnostics)


def _reference_fixture_stats(
    context: dict[str, Any],
    cell: Mapping[str, Any],
    contract: Mapping[str, Any],
    bootstrap_indices: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    cell_id = str(cell["id"])
    cached = context["fixture_stats"].get(cell_id)
    if cached is not None:
        return cached
    difference_factor = float(contract["source_authority"]["noise_difference_factor"])
    point_signal, point_noise = _path_stats(
        cell, "R", difference_factor, None
    )
    draw_signal, draw_noise = _path_stats(
        cell, "R", difference_factor, bootstrap_indices
    )
    result = (point_signal, point_noise, draw_signal, draw_noise)
    context["fixture_stats"][cell_id] = result
    return result


def _gate_g2(
    context: dict[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    bootstrap_indices: np.ndarray,
    common_bounds: Mapping[tuple[str, str], float] | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    inference = contract["inference_contract"]
    diagnostics: dict[str, Any] = {
        "inference_coordinate": str(inference["g2_coordinate"]),
        "reported_bound": str(inference["g2_reported_bound"]),
        "cells": {},
    }
    if common_bounds is None:
        return _gate_record(
            "G2",
            "SPLIT_REFERENCE_SNR",
            ["COMMON_MODE_BOUND_INVALID"],
            diagnostics,
        )
    observed: list[float] = []
    draws: list[np.ndarray] = []
    invalid = False
    condition_ceiling = float(thresholds["condition_number_max"])
    for cell in context["cells"]:
        point_signal, point_noise, draw_signal, draw_noise = _reference_fixture_stats(
            context, cell, contract, bootstrap_indices
        )
        dimension = int(cell["dimension"])
        identity = np.eye(dimension, dtype=np.complex128)
        common = float(common_bounds[(cell["id"], "R")])
        charged_signal = point_signal - common * identity
        charged_noise = point_noise + common * identity
        draw_charged_signal = draw_signal - common * identity
        draw_charged_noise = draw_noise + common * identity
        valid_point_signal, _, _ = _spd_batch(charged_signal, condition_ceiling)
        valid_point_noise, _, _ = _spd_batch(charged_noise, condition_ceiling)
        valid_draw_signal, _, _ = _spd_batch(draw_charged_signal, condition_ceiling)
        valid_draw_noise, _, _ = _spd_batch(draw_charged_noise, condition_ceiling)
        cell_diag = {
            "signal": _eigen_summary(point_signal[0]),
            "noise": _eigen_summary(point_noise[0]),
            "common_mode_upper": common,
            "charged_signal": _eigen_summary(charged_signal[0]),
            "charged_noise": _eigen_summary(charged_noise[0]),
        }
        if not (
            valid_point_signal
            and valid_point_noise
            and valid_draw_signal
            and valid_draw_noise
        ):
            invalid = True
            cell_diag["snr"] = None
            cell_diag["log_snr"] = None
            cell_diag["log_snr_lcb"] = None
            cell_diag["snr_lcb"] = None
        else:
            point_ratio = _smallest_generalized_eigenvalue(
                charged_signal, charged_noise
            )
            draw_ratio = _smallest_generalized_eigenvalue(
                draw_charged_signal, draw_charged_noise
            )
            ratios_valid = bool(
                np.all(np.isfinite(point_ratio))
                and np.all(point_ratio > 0.0)
                and np.all(np.isfinite(draw_ratio))
                and np.all(draw_ratio > 0.0)
            )
            if not ratios_valid:
                invalid = True
                cell_diag["snr"] = None
                cell_diag["log_snr"] = None
                cell_diag["log_snr_lcb"] = None
                cell_diag["snr_lcb"] = None
            else:
                point_log_snr = np.log(point_ratio)
                draw_log_snr = np.log(draw_ratio)
                observed.append(float(point_log_snr[0]))
                draws.append(np.asarray(draw_log_snr, dtype=np.float64))
                cell_diag["snr"] = float(point_ratio[0])
                cell_diag["log_snr"] = float(point_log_snr[0])
        diagnostics["cells"][cell["id"]] = cell_diag
    if invalid:
        reasons.append("REFERENCE_SNR_NONPOSITIVE_OR_ILL_CONDITIONED")
        reasons.append("REFERENCE_SNR_INSUFFICIENT")
    else:
        lower, max_t = _simultaneous_lcb(
            np.asarray(observed),
            np.stack(draws, axis=1),
        )
        diagnostics["max_t"] = max_t
        if lower is None:
            reasons.append("REFERENCE_SNR_BOOTSTRAP_INVALID")
        else:
            with np.errstate(over="ignore", invalid="ignore"):
                snr_lower = np.exp(lower)
            if not np.all(np.isfinite(snr_lower)):
                reasons.append("REFERENCE_SNR_BOOTSTRAP_INVALID")
            else:
                for cell, log_value, snr_value in zip(
                    context["cells"], lower, snr_lower
                ):
                    diagnostics["cells"][cell["id"]][
                        "log_snr_lcb"
                    ] = float(log_value)
                    diagnostics["cells"][cell["id"]][
                        "snr_lcb"
                    ] = float(snr_value)
            if np.any(
                snr_lower <= float(thresholds["reference_snr_lcb_min"])
            ):
                reasons.append("REFERENCE_SNR_INSUFFICIENT")
    diagnostics["threshold"] = float(thresholds["reference_snr_lcb_min"])
    return _gate_record("G2", "SPLIT_REFERENCE_SNR", reasons, diagnostics)


def _gate_g3(
    context: Mapping[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    bootstrap_indices: np.ndarray,
) -> dict[str, Any]:
    reasons: list[str] = []
    diagnostics: dict[str, Any] = {"cells": {}}
    observed: list[float] = []
    draws: list[np.ndarray] = []
    invalid_bootstrap = False
    for cell in context["cells"]:
        focus = cell["focus"]
        mean_transfer = np.mean(focus["transfer"], axis=0)
        response = np.linalg.norm(mean_transfer, axis=(-2, -1))
        peak = int(np.argmax(response))
        maximum = float(response[peak])
        unique = int(np.count_nonzero(response == maximum)) == 1
        interior = 0 < peak < len(response) - 1
        peak_transfer = mean_transfer[peak]
        singular_values = np.linalg.svd(peak_transfer, compute_uv=False)
        smallest = float(singular_values[-1])
        condition = (
            None
            if smallest <= 0.0
            else float(singular_values[0] / singular_values[-1])
        )
        leakage = float(np.max(focus["cross_cell_leakage"]))
        cell_diag = {
            "known_input": bool(focus["known_input"]),
            "response_by_position": [float(value) for value in response],
            "peak_index": peak,
            "peak_unique": unique,
            "peak_interior": interior,
            "smallest_singular_value": smallest,
            "condition_number": condition,
            "cross_cell_leakage": leakage,
        }
        if not focus["known_input"]:
            reasons.append("FOCUS_KNOWN_INPUT_PROVENANCE_MISSING")
        if not unique or not interior:
            reasons.append("FOCUS_PEAK_NOT_INTERIOR")
        if condition is None or condition > float(thresholds["condition_number_max"]):
            reasons.append("FOCUS_TRANSFER_ILL_CONDITIONED")
        if leakage > float(thresholds["cross_cell_leakage_max"]):
            reasons.append("CROSS_CELL_LEAKAGE_EXCESS")
        sampled = np.mean(focus["transfer"][bootstrap_indices, peak], axis=1)
        sampled_smallest = np.linalg.svd(sampled, compute_uv=False)[..., -1]
        if not np.all(np.isfinite(sampled_smallest)):
            invalid_bootstrap = True
        observed.append(smallest)
        draws.append(np.asarray(sampled_smallest, dtype=np.float64))
        diagnostics["cells"][cell["id"]] = cell_diag
    if invalid_bootstrap:
        lower = None
        diagnostics["max_t"] = {"valid": False, "failure": "NONFINITE_DRAW"}
    else:
        lower, max_t = _simultaneous_lcb(
            np.asarray(observed),
            np.stack(draws, axis=1),
        )
        diagnostics["max_t"] = max_t
    if lower is None:
        reasons.append("FOCUS_TRANSFER_BOOTSTRAP_INVALID")
    else:
        for cell, value in zip(context["cells"], lower):
            diagnostics["cells"][cell["id"]]["smallest_singular_value_lcb"] = float(
                value
            )
        if np.any(
            lower <= float(thresholds["focus_transfer_singular_value_lcb_min"])
        ):
            reasons.append("FOCUS_TRANSFER_INSUFFICIENT")
    diagnostics["thresholds"] = {
        "smallest_singular_value_lcb_min": float(
            thresholds["focus_transfer_singular_value_lcb_min"]
        ),
        "condition_number_max": float(thresholds["condition_number_max"]),
        "cross_cell_leakage_max": float(thresholds["cross_cell_leakage_max"]),
    }
    return _gate_record(
        "G3",
        "REFERENCE_FOCUS_TRANSFER_SUFFICIENCY",
        reasons,
        diagnostics,
    )


def _gate_g4(
    context: Mapping[str, Any], thresholds: Mapping[str, Any]
) -> dict[str, Any]:
    response = context["raw_response"]
    reasons: list[str] = []
    if not response["known_input"]:
        reasons.append("RAW_KNOWN_INPUT_PROVENANCE_MISSING")
    if response["low_rail_hits"] or response["high_rail_hits"]:
        reasons.append("RAW_CLIPPING_DETECTED")
    x = response["input_levels"]
    y = response["output_levels"]
    even = np.arange(0, 33, 2)
    odd = np.arange(1, 33, 2)
    design = np.column_stack((x[even], np.ones(even.size)))
    coefficients, _, rank, _ = np.linalg.lstsq(design, y[even], rcond=None)
    slope = float(coefficients[0])
    intercept = float(coefficients[1])
    dynamic_range = float(np.max(y) - np.min(y))
    if rank != 2 or slope <= 0.0 or dynamic_range <= 0.0:
        normalized_residual = None
        reasons.append("RAW_POSITIVE_AFFINE_FIT_NOT_ESTABLISHED")
    else:
        prediction = slope * x[odd] + intercept
        normalized_residual = float(
            np.max(np.abs(y[odd] - prediction)) / dynamic_range
        )
        if normalized_residual > float(
            thresholds["raw_response_max_normalized_residual"]
        ):
            reasons.append("RAW_NONLINEARITY_DETECTED")
    diagnostics = {
        "low_rail_hits": int(response["low_rail_hits"]),
        "high_rail_hits": int(response["high_rail_hits"]),
        "fit_level_indices": [int(value) for value in even],
        "held_out_level_indices": [int(value) for value in odd],
        "slope": slope,
        "intercept": intercept,
        "held_out_max_normalized_residual": normalized_residual,
        "threshold": float(thresholds["raw_response_max_normalized_residual"]),
    }
    return _gate_record("G4", "LINEAR_UNCLIPPED_RAW", reasons, diagnostics)


def _split_metrics(pair: Mapping[str, Any]) -> dict[str, Any]:
    first = pair["first"]
    second = pair["second"]
    first_rms = float(np.sqrt(np.mean(np.sum(np.abs(first) ** 2, axis=1))))
    second_rms = float(np.sqrt(np.mean(np.sum(np.abs(second) ** 2, axis=1))))
    magnitude_denominator = 0.5 * (first_rms + second_rms)
    magnitude_disagreement = (
        None
        if magnitude_denominator <= 0.0
        else abs(first_rms - second_rms) / magnitude_denominator
    )
    cross = np.vdot(first.reshape(-1), second.reshape(-1))
    phase_disagreement = None if abs(cross) == 0.0 else abs(float(np.angle(cross)))
    signal_matrix = _hermitian_cross_covariance(first, second)[0]
    signal_minimum = float(np.linalg.eigvalsh(signal_matrix)[0])
    controls = []
    for control_name in _CONTROLS:
        control = pair["controls"][control_name]
        covariance = _hermitian_cross_covariance(
            control["first"], control["second"]
        )
        controls.append(float(_matrix_abs_size(covariance)[0]))
    common_mode = max(controls)
    common_fraction = (
        None if signal_minimum <= 0.0 else common_mode / signal_minimum
    )
    return {
        "first_rms": first_rms,
        "second_rms": second_rms,
        "relative_magnitude_disagreement": _finite_or_none(
            magnitude_disagreement
        ),
        "phase_disagreement_rad": _finite_or_none(phase_disagreement),
        "repeatable_signal_minimum_eigenvalue": signal_minimum,
        "control_repeatable_covariance": {
            name: value for name, value in zip(_CONTROLS, controls)
        },
        "common_mode_fraction": _finite_or_none(common_fraction),
    }


def _gate_g5(
    context: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    diagnostics: dict[str, Any] = {"cells": {}}
    lineage = context["lineage"]
    acquisition_hashes = [
        lineage[f"{name}_{kind}_sha256"]
        for name in _PATHS
        for kind in ("source", "calibration")
    ]
    lineage_disjoint = len(set(acquisition_hashes)) == len(acquisition_hashes)
    if not lineage_disjoint:
        reasons.append("LINEAGE_NOT_DISJOINT")
    for cell in context["cells"]:
        cell_diagnostics: dict[str, Any] = {}
        for split_name in _SPLITS:
            metrics = _split_metrics(cell["split_pairs"][split_name])
            cell_diagnostics[split_name] = metrics
            magnitude = metrics["relative_magnitude_disagreement"]
            phase = metrics["phase_disagreement_rad"]
            common_fraction = metrics["common_mode_fraction"]
            if magnitude is None or phase is None or common_fraction is None:
                reasons.append("REFERENCE_HALF_AGREEMENT_UNIDENTIFIED")
                continue
            if magnitude > float(thresholds["split_magnitude_disagreement_max"]):
                reasons.append("REFERENCE_HALF_MAGNITUDE_DISAGREEMENT")
            if phase > float(thresholds["split_phase_disagreement_rad_max"]):
                reasons.append("REFERENCE_HALF_PHASE_DISAGREEMENT")
            if common_fraction > float(thresholds["common_mode_fraction_max"]):
                reasons.append("LAGGED_COMMON_MODE_EXCESS")
        diagnostics["cells"][cell["id"]] = cell_diagnostics
    diagnostics["lineage_disjoint"] = lineage_disjoint
    diagnostics["thresholds"] = {
        "magnitude_relative_max": float(
            thresholds["split_magnitude_disagreement_max"]
        ),
        "phase_rad_max": float(thresholds["split_phase_disagreement_rad_max"]),
        "common_mode_fraction_max": float(thresholds["common_mode_fraction_max"]),
    }
    return _gate_record(
        "G5", "REFERENCE_HALF_AGREEMENT", reasons, diagnostics
    )


def _gate_g6(
    context: Mapping[str, Any], thresholds: Mapping[str, Any]
) -> dict[str, Any]:
    geometry = context["geometry"]
    reasons: list[str] = []
    if not geometry["input_only"]:
        reasons.append("INPUT_ONLY_GEOMETRY_NOT_ESTABLISHED")
    if not geometry["scored_pixels_native"]:
        reasons.append("SCORED_PIXELS_NOT_NATIVE")
    if not geometry["reference_only_resampling"]:
        reasons.append("REFERENCE_ONLY_RESAMPLING_NOT_ESTABLISHED")
    max_scale = float(np.max(np.abs(geometry["scale_disagreement_percent"])))
    max_rotation = float(
        np.max(np.abs(geometry["rotation_disagreement_deg"]))
    )
    max_nontranslation = float(
        np.max(geometry["nontranslation_rms_native_px"])
    )
    signs_match = bool(
        np.array_equal(
            geometry["planted_transform_sign"],
            geometry["estimated_transform_sign"],
        )
    )
    if max_scale > float(thresholds["scale_disagreement_percent_max"]):
        reasons.append("SCALE_GEOMETRY_DISAGREEMENT")
    if max_rotation > float(thresholds["rotation_disagreement_deg_max"]):
        reasons.append("ROTATION_GEOMETRY_DISAGREEMENT")
    if max_nontranslation > float(
        thresholds["nontranslation_rms_native_px_max"]
    ):
        reasons.append("NONTRANSLATION_RESIDUAL_EXCESS")
    if not signs_match:
        reasons.append("WRONG_SIGN_GEOMETRY")

    resampler_changes: dict[str, float | None] = {}
    for cell in context["cells"]:
        first = cell["resampler"]["kernel_a"]
        second = cell["resampler"]["kernel_b"]
        denominator = float(np.sqrt(np.mean(np.sum(np.abs(first) ** 2, axis=1))))
        if denominator <= 0.0:
            relative_change = None
            reasons.append("RESAMPLER_SENSITIVITY_UNIDENTIFIED")
        else:
            relative_change = float(
                np.sqrt(np.mean(np.sum(np.abs(second - first) ** 2, axis=1)))
                / denominator
            )
            if relative_change > float(
                thresholds["resampler_relative_change_max"]
            ):
                reasons.append("RESAMPLER_SENSITIVITY_EXCESS")
        resampler_changes[cell["id"]] = relative_change
    diagnostics = {
        "max_scale_disagreement_percent": max_scale,
        "max_rotation_disagreement_deg": max_rotation,
        "max_nontranslation_rms_native_px": max_nontranslation,
        "planted_transform_sign_matches": signs_match,
        "resampler_relative_change_by_cell": resampler_changes,
        "thresholds": {
            "scale_disagreement_percent_max": float(
                thresholds["scale_disagreement_percent_max"]
            ),
            "rotation_disagreement_deg_max": float(
                thresholds["rotation_disagreement_deg_max"]
            ),
            "nontranslation_rms_native_px_max": float(
                thresholds["nontranslation_rms_native_px_max"]
            ),
            "resampler_relative_change_max": float(
                thresholds["resampler_relative_change_max"]
            ),
        },
    }
    return _gate_record(
        "G6", "GEOMETRY_RESAMPLER_SENSITIVITY", reasons, diagnostics
    )


def _maximum_duplicate_correlation(
    cells: Sequence[Mapping[str, Any]]
) -> float | None:
    features: list[np.ndarray] = []
    for cell in cells:
        for path_name in ("R1", "R2"):
            values = cell["coefficients"][path_name]
            features.extend((values.real, values.imag))
    matrix = np.concatenate(features, axis=1)
    matrix = matrix - np.mean(matrix, axis=1, keepdims=True)
    norms = np.linalg.norm(matrix, axis=1)
    if np.any(norms <= 0.0):
        return None
    normalized = matrix / norms[:, np.newaxis]
    correlation = np.abs(normalized @ normalized.T)
    np.fill_diagonal(correlation, -np.inf)
    return float(np.max(correlation))


def _gate_g7(
    context: dict[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    bootstrap_indices: np.ndarray,
    common_bounds: Mapping[tuple[str, str], float] | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    diagnostics: dict[str, Any] = {"cells": {}}
    if not context["nonperiodic"]["concealed"]:
        reasons.append("NONPERIODIC_LINEAGE_NOT_CONCEALED")
    duplicate_correlation = _maximum_duplicate_correlation(context["cells"])
    if duplicate_correlation is None:
        reasons.append("DUPLICATE_SITE_CORRELATION_UNIDENTIFIED")
    elif duplicate_correlation >= float(
        thresholds["duplicate_site_correlation_max"]
    ):
        reasons.append("DUPLICATE_SITE_CORRELATION_EXCESS")
    diagnostics["maximum_duplicate_site_correlation"] = duplicate_correlation
    diagnostics["duplicate_site_correlation_threshold"] = float(
        thresholds["duplicate_site_correlation_max"]
    )
    if common_bounds is None:
        return _gate_record(
            "G7",
            "NONPERIODIC_REFERENCE_POWER",
            reasons + ["COMMON_MODE_BOUND_INVALID"],
            diagnostics,
        )

    observed: list[float] = []
    draws: list[np.ndarray] = []
    invalid = False
    condition_ceiling = float(thresholds["condition_number_max"])
    for cell in context["cells"]:
        point_signal, _, draw_signal, _ = _reference_fixture_stats(
            context, cell, contract, bootstrap_indices
        )
        dimension = int(cell["dimension"])
        common = float(common_bounds[(cell["id"], "R")])
        identity = np.eye(dimension, dtype=np.complex128)
        charged = point_signal - common * identity
        draw_charged = draw_signal - common * identity
        valid_point, point_minimum, point_condition = _spd_batch(
            charged, condition_ceiling
        )
        valid_draws, draw_minimum, _ = _spd_batch(
            draw_charged, condition_ceiling
        )
        cell_diag = {
            "signal": _eigen_summary(point_signal[0]),
            "common_mode_upper": common,
            "charged_signal": _eigen_summary(charged[0]),
            "point_power": float(point_minimum[0]),
            "condition_number": _finite_or_none(point_condition[0]),
        }
        if not valid_point or not valid_draws:
            invalid = True
            cell_diag["lcb"] = None
        else:
            observed.append(float(point_minimum[0]))
            draws.append(np.asarray(draw_minimum, dtype=np.float64))
        diagnostics["cells"][cell["id"]] = cell_diag
    if invalid:
        reasons.append("REFERENCE_POWER_NONPOSITIVE_OR_ILL_CONDITIONED")
        reasons.append("REFERENCE_POWER_FLOOR")
    else:
        lower, max_t = _simultaneous_lcb(
            np.asarray(observed),
            np.stack(draws, axis=1),
        )
        diagnostics["max_t"] = max_t
        if lower is None:
            reasons.append("REFERENCE_POWER_BOOTSTRAP_INVALID")
        else:
            for cell, value in zip(context["cells"], lower):
                diagnostics["cells"][cell["id"]]["lcb"] = float(value)
            if np.any(lower <= float(thresholds["reference_power_lcb_min"])):
                reasons.append("REFERENCE_POWER_FLOOR")
    diagnostics["thresholds"] = {
        "reference_power_lcb_min": float(
            thresholds["reference_power_lcb_min"]
        ),
        "condition_number_max": float(thresholds["condition_number_max"]),
    }
    return _gate_record(
        "G7", "NONPERIODIC_REFERENCE_POWER", reasons, diagnostics
    )


def _dominance_point_and_draws(
    cell: Mapping[str, Any],
    difference_factor: float,
    bootstrap_indices: np.ndarray,
    common_r: float,
    common_s: float,
    delta_information: float,
    delta_transfer: float,
    condition_ceiling: float,
) -> tuple[dict[str, Any], np.ndarray | None, list[str]]:
    point_r_signal, point_r_noise = _path_stats(
        cell, "R", difference_factor, None
    )
    point_s_signal, point_s_noise = _path_stats(
        cell, "S", difference_factor, None
    )
    draw_r_signal, draw_r_noise = _path_stats(
        cell, "R", difference_factor, bootstrap_indices
    )
    draw_s_signal, draw_s_noise = _path_stats(
        cell, "S", difference_factor, bootstrap_indices
    )
    dimension = int(cell["dimension"])
    identity = np.eye(dimension, dtype=np.complex128)

    charged_point = {
        "signal_R": point_r_signal - common_r * identity,
        "noise_R": point_r_noise + common_r * identity,
        "signal_S": point_s_signal + common_s * identity,
        "noise_S": point_s_noise - common_s * identity,
    }
    charged_draw = {
        "signal_R": draw_r_signal - common_r * identity,
        "noise_R": draw_r_noise + common_r * identity,
        "signal_S": draw_s_signal + common_s * identity,
        "noise_S": draw_s_noise - common_s * identity,
    }
    raw_point = {
        "signal_R": point_r_signal,
        "noise_R": point_r_noise,
        "signal_S": point_s_signal,
        "noise_S": point_s_noise,
    }
    diagnostics: dict[str, Any] = {
        "common_mode_upper_R": common_r,
        "common_mode_upper_S": common_s,
        "raw": {
            name: _eigen_summary(matrix[0]) for name, matrix in raw_point.items()
        },
        "charged": {
            name: _eigen_summary(matrix[0])
            for name, matrix in charged_point.items()
        },
    }
    reasons: list[str] = []

    raw_signal_r_min = float(np.linalg.eigvalsh(point_r_signal[0])[0])
    raw_signal_s_min = float(np.linalg.eigvalsh(point_s_signal[0])[0])
    fraction_r = (
        None if raw_signal_r_min <= 0.0 else common_r / raw_signal_r_min
    )
    fraction_s = (
        None if raw_signal_s_min <= 0.0 else common_s / raw_signal_s_min
    )
    diagnostics["common_mode_fraction_R"] = _finite_or_none(fraction_r)
    diagnostics["common_mode_fraction_S"] = _finite_or_none(fraction_s)

    point_valid = True
    draw_valid = True
    for name in ("signal_R", "noise_R", "signal_S", "noise_S"):
        valid_point, _, _ = _spd_batch(
            charged_point[name], condition_ceiling
        )
        valid_draw, _, _ = _spd_batch(charged_draw[name], condition_ceiling)
        point_valid &= valid_point
        draw_valid &= valid_draw
    if not point_valid:
        reasons.append("NONPOSITIVE_HOSTILE_CHARGE")
    if not draw_valid:
        reasons.append("DOMINANCE_INVALID_BOOTSTRAP_DRAW")
    if not point_valid or not draw_valid:
        diagnostics["information_margin"] = None
        diagnostics["transfer_margin"] = None
        return diagnostics, None, reasons

    information_r_point = _information_operator(
        charged_point["signal_R"], charged_point["noise_R"]
    )
    information_s_point = _information_operator(
        charged_point["signal_S"], charged_point["noise_S"]
    )
    information_ratio_point = _smallest_generalized_eigenvalue(
        information_r_point, information_s_point
    )
    transfer_ratio_squared_point = _smallest_generalized_eigenvalue(
        charged_point["signal_R"], charged_point["signal_S"]
    )
    information_margin_point = np.log(information_ratio_point) - math.log1p(
        delta_information
    )
    transfer_margin_point = (
        0.5 * np.log(transfer_ratio_squared_point) - math.log1p(delta_transfer)
    )

    information_r_draw = _information_operator(
        charged_draw["signal_R"], charged_draw["noise_R"]
    )
    information_s_draw = _information_operator(
        charged_draw["signal_S"], charged_draw["noise_S"]
    )
    information_ratio_draw = _smallest_generalized_eigenvalue(
        information_r_draw, information_s_draw
    )
    transfer_ratio_squared_draw = _smallest_generalized_eigenvalue(
        charged_draw["signal_R"], charged_draw["signal_S"]
    )
    if (
        np.any(information_ratio_draw <= 0.0)
        or np.any(transfer_ratio_squared_draw <= 0.0)
        or not np.all(np.isfinite(information_ratio_draw))
        or not np.all(np.isfinite(transfer_ratio_squared_draw))
    ):
        reasons.append("DOMINANCE_INVALID_BOOTSTRAP_DRAW")
        diagnostics["information_margin"] = float(information_margin_point[0])
        diagnostics["transfer_margin"] = float(transfer_margin_point[0])
        return diagnostics, None, reasons
    information_margin_draw = np.log(information_ratio_draw) - math.log1p(
        delta_information
    )
    transfer_margin_draw = (
        0.5 * np.log(transfer_ratio_squared_draw) - math.log1p(delta_transfer)
    )
    diagnostics.update(
        {
            "information_generalized_eigenvalue": float(
                information_ratio_point[0]
            ),
            "transfer_generalized_eigenvalue": float(
                transfer_ratio_squared_point[0]
            ),
            "transfer_ratio": float(np.sqrt(transfer_ratio_squared_point[0])),
            "information_margin": float(information_margin_point[0]),
            "transfer_margin": float(transfer_margin_point[0]),
        }
    )
    if dimension > 1:
        diagnostics["vector_rule"] = "SMALLEST_GENERALIZED_EIGENVALUE"
    observed = np.asarray(
        [information_margin_point[0], transfer_margin_point[0]],
        dtype=np.float64,
    )
    bootstrap = np.stack(
        (information_margin_draw, transfer_margin_draw), axis=1
    )
    return diagnostics, np.vstack((observed, bootstrap)), reasons


def _gate_g8(
    context: Mapping[str, Any],
    contract: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    bootstrap_indices: np.ndarray,
    common_bounds: Mapping[tuple[str, str], float] | None,
    common_diagnostics: Mapping[str, Any],
    support_gate_passed: bool,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "noise_difference_factor": float(
            contract["source_authority"]["noise_difference_factor"]
        ),
        "bootstrap_draws": int(contract["bootstrap"]["draws"]),
        "bootstrap_seed": int(contract["bootstrap"]["dominance_seed"]),
        "quantile_method": str(contract["bootstrap"]["quantile_method"]),
        "common_mode_family": dict(common_diagnostics),
        "cells": {},
    }
    if context["claim_scope"] == "DIGITAL_K":
        digital_k_policy = contract["digital_k_policy"]
        diagnostics["digital_k_policy"] = {
            "status": str(digital_k_policy["status"]),
            "reason": str(digital_k_policy["reason"]),
            "q_payload_present": context["q_baseline"] is not None,
            "q_matrix_alone_sufficient": False,
        }
        return _gate_record(
            "G8",
            "REFERENCE_INFORMATION_DOMINANCE",
            [str(digital_k_policy["reason"])],
            diagnostics,
        )
    if not context["reduction_sufficient"]:
        return _gate_record(
            "G8",
            "REFERENCE_INFORMATION_DOMINANCE",
            ["REDUCTION_SUFFICIENCY_NOT_ESTABLISHED"],
            diagnostics,
        )
    if common_bounds is None:
        return _gate_record(
            "G8",
            "REFERENCE_INFORMATION_DOMINANCE",
            ["COMMON_MODE_BOUND_INVALID"],
            diagnostics,
        )

    reasons: list[str] = []
    if not support_gate_passed:
        reasons.append("SUPPORT_FLOOR_NOT_ESTABLISHED")
    observed: list[float] = []
    bootstrap_columns: list[np.ndarray] = []
    labels: list[tuple[str, str]] = []
    difference_factor = float(
        contract["source_authority"]["noise_difference_factor"]
    )
    condition_ceiling = float(thresholds["condition_number_max"])
    common_allowance = float(thresholds["common_mode_fraction_max"])
    for cell in context["cells"]:
        cell_id = str(cell["id"])
        delta_i = float(thresholds["delta_information_by_cell"][cell_id])
        delta_h = float(thresholds["delta_transfer_by_cell"][cell_id])
        cell_diagnostics, packed, cell_reasons = _dominance_point_and_draws(
            cell,
            difference_factor,
            bootstrap_indices,
            float(common_bounds[(cell_id, "R")]),
            float(common_bounds[(cell_id, "S")]),
            delta_i,
            delta_h,
            condition_ceiling,
        )
        cell_diagnostics["delta_information"] = delta_i
        cell_diagnostics["delta_transfer"] = delta_h
        diagnostics["cells"][cell_id] = cell_diagnostics
        reasons.extend(cell_reasons)
        fraction_r = cell_diagnostics["common_mode_fraction_R"]
        fraction_s = cell_diagnostics["common_mode_fraction_S"]
        if (
            fraction_r is None
            or fraction_s is None
            or fraction_r > common_allowance
            or fraction_s > common_allowance
        ):
            reasons.append("COMMON_MODE_FRACTION_EXCESS")
        if packed is not None:
            observed.extend(float(value) for value in packed[0])
            bootstrap_columns.extend(
                (packed[1:, 0].copy(), packed[1:, 1].copy())
            )
            labels.extend(((cell_id, "information"), (cell_id, "transfer")))

    if reasons:
        diagnostics["dominance_max_t"] = None
        return _gate_record(
            "G8", "REFERENCE_INFORMATION_DOMINANCE", reasons, diagnostics
        )

    lower, max_t = _simultaneous_lcb(
        np.asarray(observed, dtype=np.float64),
        np.stack(bootstrap_columns, axis=1),
    )
    diagnostics["dominance_max_t"] = max_t
    diagnostics["dominance_family_alpha"] = float(
        contract["bootstrap"]["dominance_family_alpha"]
    )
    if lower is None:
        reasons.append("DOMINANCE_BOOTSTRAP_INVALID")
    else:
        for (cell_id, kind), value in zip(labels, lower):
            diagnostics["cells"][cell_id][f"{kind}_margin_lcb"] = float(value)
        information_lower = np.asarray(
            [
                value
                for (label, value) in zip(labels, lower)
                if label[1] == "information"
            ]
        )
        transfer_lower = np.asarray(
            [
                value
                for (label, value) in zip(labels, lower)
                if label[1] == "transfer"
            ]
        )
        if np.any(information_lower <= 0.0):
            reasons.append("INFORMATION_NOT_DOMINANT")
        if np.any(transfer_lower <= 0.0):
            reasons.append("TRANSFER_NOT_DOMINANT")
    diagnostics["common_mode_fraction_threshold"] = common_allowance
    return _gate_record(
        "G8", "REFERENCE_INFORMATION_DOMINANCE", reasons, diagnostics
    )


def _synthetic_thresholds(contract: Mapping[str, Any]) -> dict[str, Any]:
    source = dict(contract["synthetic_thresholds"])
    source["sampling_optical_systematic_bound"] = 0.0
    cell_ids = [str(cell["id"]) for cell in contract["cells"]]
    source["delta_information_by_cell"] = {
        cell_id: float(source["delta_information"]) for cell_id in cell_ids
    }
    source["delta_transfer_by_cell"] = {
        cell_id: float(source["delta_transfer"]) for cell_id in cell_ids
    }
    return source


class _IncompleteManifest(ValueError):
    pass


def _manifest_number(
    value: Any, path: str, *, positive: bool = False
) -> float:
    try:
        parsed = _number(value, path)
    except HarnessError as exc:
        raise _IncompleteManifest(str(exc)) from exc
    if parsed < 0.0 or (positive and parsed <= 0.0):
        comparison = "positive" if positive else "nonnegative"
        raise _IncompleteManifest(f"{path} must be {comparison}")
    return parsed


def _manifest_object(
    value: Any, path: str, required: Sequence[str]
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _IncompleteManifest(f"{path} must be an object")
    missing = sorted(set(required) - set(value))
    if missing:
        raise _IncompleteManifest(f"{path} missing {', '.join(missing)}")
    return value


def _production_thresholds(
    manifest: Mapping[str, Any] | None,
    manifest_expected_sha256: str | None,
    contract: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    if manifest is None:
        return None, "PRODUCTION_CALIBRATION_MANIFEST_ABSENT"

    if isinstance(manifest, _SealedJSON):
        manifest_digest = manifest.sealed_sha256
    elif manifest_expected_sha256 is None:
        return None, "PRODUCTION_CALIBRATION_MANIFEST_NOT_HASH_BOUND"
    else:
        expected = _sha256(
            manifest_expected_sha256, "calibration_manifest_sha256"
        )
        actual = _canonical_sha256(dict(manifest))
        if actual != expected:
            raise HarnessError(
                "production calibration manifest SHA-256 mismatch: "
                f"expected {expected}, got {actual}"
            )
        manifest_digest = actual

    try:
        root = _manifest_object(
            manifest,
            "production calibration manifest",
            ("schema", "contract_sha256", "production_thresholds"),
        )
        if root["schema"] != _PRODUCTION_SCHEMA:
            raise _IncompleteManifest("production calibration schema is unsupported")
        contract_digest = root["contract_sha256"]
        if not isinstance(contract_digest, str) or not _SHA256_RE.fullmatch(
            contract_digest
        ):
            raise _IncompleteManifest("contract_sha256 is missing or invalid")
        if contract_digest.upper() != FROZEN_CONTRACT_SHA256:
            raise HarnessError(
                "production calibration is bound to a different contract"
            )
        required = tuple(contract["production_thresholds_required"])
        production = _manifest_object(
            root["production_thresholds"], "production_thresholds", required
        )
        if any(name not in production or production[name] is None for name in required):
            raise _IncompleteManifest(
                "production_thresholds does not contain every required field"
            )

        cell_ids = [str(cell["id"]) for cell in contract["cells"]]
        licensed = production["licensed_cells"]
        if not isinstance(licensed, list) or licensed != cell_ids:
            raise _IncompleteManifest(
                "licensed_cells must be the complete frozen cell order"
            )

        sampling = _manifest_object(
            production["sampling_optical_systematic"],
            "sampling_optical_systematic",
            (
                "artifact_sha256",
                "sampling_ratio_lcb_min",
                "optical_systematic_ratio_bound",
                "scale_disagreement_percent_max",
                "rotation_disagreement_deg_max",
                "nontranslation_rms_native_px_max",
            ),
        )
        _sha256(
            sampling["artifact_sha256"],
            "sampling_optical_systematic.artifact_sha256",
        )
        conditioning = _manifest_object(
            production["focus_conditioning_ceiling"],
            "focus_conditioning_ceiling",
            ("condition_number_max", "cross_cell_leakage_max"),
        )
        raw = _manifest_object(
            production["raw_response_calibration"],
            "raw_response_calibration",
            ("artifact_sha256", "max_normalized_residual"),
        )
        _sha256(raw["artifact_sha256"], "raw_response_calibration.artifact_sha256")
        split = _manifest_object(
            production["split_agreement_tolerances"],
            "split_agreement_tolerances",
            ("magnitude_relative_max", "phase_rad_max"),
        )
        power = _manifest_object(
            production["nonperiodic_power_floor"],
            "nonperiodic_power_floor",
            ("power_lcb_min", "duplicate_site_correlation_max"),
        )
        reduction = _manifest_object(
            production["reduction_sufficiency"],
            "reduction_sufficiency",
            ("artifact_sha256", "complete_candidate_blind_linear"),
        )
        _sha256(
            reduction["artifact_sha256"], "reduction_sufficiency.artifact_sha256"
        )
        if reduction["complete_candidate_blind_linear"] is not True:
            raise _IncompleteManifest(
                "reduction_sufficiency is not complete/candidate-blind/linear"
            )
        convention = _manifest_object(
            production["noise_estimand_convention"],
            "noise_estimand_convention",
            ("difference_factor", "estimand"),
        )
        if (
            _manifest_number(
                convention["difference_factor"],
                "noise_estimand_convention.difference_factor",
                positive=True,
            )
            != float(contract["source_authority"]["noise_difference_factor"])
            or convention["estimand"] != "half_split_difference_variance"
        ):
            raise _IncompleteManifest(
                "noise_estimand_convention does not ratify the frozen 0.5 estimand"
            )

        delta_i_obj = _manifest_object(
            production["delta_information_by_cell"],
            "delta_information_by_cell",
            cell_ids,
        )
        delta_h_obj = _manifest_object(
            production["delta_transfer_by_cell"],
            "delta_transfer_by_cell",
            cell_ids,
        )
        delta_i = {
            cell_id: _manifest_number(
                delta_i_obj[cell_id],
                f"delta_information_by_cell.{cell_id}",
            )
            for cell_id in cell_ids
        }
        delta_h = {
            cell_id: _manifest_number(
                delta_h_obj[cell_id], f"delta_transfer_by_cell.{cell_id}"
            )
            for cell_id in cell_ids
        }
        thresholds = {
            "sampling_ratio_lcb_min": _manifest_number(
                sampling["sampling_ratio_lcb_min"],
                "sampling_optical_systematic.sampling_ratio_lcb_min",
                positive=True,
            ),
            "sampling_optical_systematic_bound": _manifest_number(
                sampling["optical_systematic_ratio_bound"],
                "sampling_optical_systematic.optical_systematic_ratio_bound",
            ),
            "reference_snr_lcb_min": _manifest_number(
                production["reference_snr_floor"],
                "reference_snr_floor",
                positive=True,
            ),
            "focus_transfer_singular_value_lcb_min": _manifest_number(
                production["focus_transfer_floor"],
                "focus_transfer_floor",
                positive=True,
            ),
            "condition_number_max": _manifest_number(
                conditioning["condition_number_max"],
                "focus_conditioning_ceiling.condition_number_max",
                positive=True,
            ),
            "cross_cell_leakage_max": _manifest_number(
                conditioning["cross_cell_leakage_max"],
                "focus_conditioning_ceiling.cross_cell_leakage_max",
            ),
            "raw_response_max_normalized_residual": _manifest_number(
                raw["max_normalized_residual"],
                "raw_response_calibration.max_normalized_residual",
            ),
            "split_magnitude_disagreement_max": _manifest_number(
                split["magnitude_relative_max"],
                "split_agreement_tolerances.magnitude_relative_max",
            ),
            "split_phase_disagreement_rad_max": _manifest_number(
                split["phase_rad_max"],
                "split_agreement_tolerances.phase_rad_max",
            ),
            "common_mode_fraction_max": _manifest_number(
                production["common_mode_allowance"],
                "common_mode_allowance",
            ),
            "scale_disagreement_percent_max": _manifest_number(
                sampling["scale_disagreement_percent_max"],
                "sampling_optical_systematic.scale_disagreement_percent_max",
            ),
            "rotation_disagreement_deg_max": _manifest_number(
                sampling["rotation_disagreement_deg_max"],
                "sampling_optical_systematic.rotation_disagreement_deg_max",
            ),
            "nontranslation_rms_native_px_max": _manifest_number(
                sampling["nontranslation_rms_native_px_max"],
                "sampling_optical_systematic.nontranslation_rms_native_px_max",
            ),
            "resampler_relative_change_max": _manifest_number(
                production["resampler_allowance"], "resampler_allowance"
            ),
            "duplicate_site_correlation_max": _manifest_number(
                power["duplicate_site_correlation_max"],
                "nonperiodic_power_floor.duplicate_site_correlation_max",
            ),
            "reference_power_lcb_min": _manifest_number(
                power["power_lcb_min"],
                "nonperiodic_power_floor.power_lcb_min",
                positive=True,
            ),
            "delta_information_by_cell": delta_i,
            "delta_transfer_by_cell": delta_h,
            "manifest_sha256": manifest_digest,
        }
        return thresholds, None
    except _IncompleteManifest:
        return None, "PRODUCTION_CALIBRATION_MANIFEST_INCOMPLETE"
    except HarnessError as exc:
        if "SHA-256" in str(exc) and "must be" in str(exc):
            return None, "PRODUCTION_CALIBRATION_MANIFEST_INCOMPLETE"
        raise


def _production_unmeasured_result(
    context: Mapping[str, Any],
    contract: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    gates = []
    for definition in contract["gate_definitions"]:
        reasons = [reason, str(definition["production_missing_reason"])]
        diagnostics: dict[str, Any] = {
            "profile": "production",
            "synthetic_defaults_used": False,
        }
        if (
            context["claim_scope"] == "DIGITAL_K"
            and definition["id"] == "G8"
        ):
            digital_k_policy = contract["digital_k_policy"]
            reasons.append(str(digital_k_policy["reason"]))
            diagnostics["digital_k_policy"] = {
                "status": str(digital_k_policy["status"]),
                "reason": str(digital_k_policy["reason"]),
                "q_payload_present": context["q_baseline"] is not None,
                "q_matrix_alone_sufficient": False,
                "production_manifest_failure_additional_reason": reason,
            }
        gates.append(
            _gate_record(
                str(definition["id"]),
                str(definition["name"]),
                reasons,
                diagnostics,
            )
        )
    return _result("production", context["claim_scope"], gates)


def _result(
    profile: str, claim_scope: str, gates: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if len(gates) != 8:
        raise HarnessError(f"internal gate partition has {len(gates)} records")
    pass_count = sum(gate["status"] == "PASS" for gate in gates)
    unmeasured_count = sum(gate["status"] == "UNMEASURED" for gate in gates)
    if pass_count + unmeasured_count != 8:
        raise HarnessError("internal gate partition is not PASS + UNMEASURED == 8")
    for gate in gates:
        if gate["evaluated"] is not True:
            raise HarnessError("internal gate record was not evaluated")
        reasons = gate["reason_codes"]
        if (gate["status"] == "PASS") != (reasons == []):
            raise HarnessError("internal gate reason/status invariant violated")
        if gate["status"] == "UNMEASURED" and gate["claim_value"] is not None:
            raise HarnessError("UNMEASURED gate carried a claim value")
        if isinstance(gate["claim_value"], (int, float)):
            raise HarnessError("numeric gate claim values are forbidden")
    return {
        "schema": _RESULT_SCHEMA,
        "profile": profile,
        "claim_scope": claim_scope,
        "gates": [dict(gate) for gate in gates],
        "counts": {
            "PASS": pass_count,
            "UNMEASURED": unmeasured_count,
            "total": 8,
        },
        "all_gates_pass": pass_count == 8,
    }


def evaluate_evidence(
    evidence: Mapping[str, Any],
    contract: Mapping[str, Any],
    profile: str = "synthetic_commission",
    *,
    calibration_manifest: Mapping[str, Any] | None = None,
    calibration_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate evidence and evaluate all eight frozen gates.

    A malformed input raises :class:`HarnessError`.  Scientific inability to
    establish a gate produces an evaluated ``UNMEASURED`` record instead.
    """

    frozen_contract = _validate_contract(contract)
    context = _validate_evidence(evidence, frozen_contract)
    if profile not in ("synthetic_commission", "production"):
        raise HarnessError(f"unsupported profile: {profile!r}")

    if profile == "synthetic_commission":
        if calibration_manifest is not None or calibration_manifest_sha256 is not None:
            raise HarnessError(
                "synthetic_commission must not consume a production manifest"
            )
        thresholds = _synthetic_thresholds(frozen_contract)
    else:
        thresholds, production_reason = _production_thresholds(
            calibration_manifest,
            calibration_manifest_sha256,
            frozen_contract,
        )
        if thresholds is None:
            assert production_reason is not None
            return _production_unmeasured_result(
                context, frozen_contract, production_reason
            )

    draws = int(frozen_contract["bootstrap"]["draws"])
    fixture_indices = _bootstrap_indices(
        context["hierarchy"],
        draws,
        int(frozen_contract["bootstrap"]["fixture_seed"]),
    )
    dominance_indices = _bootstrap_indices(
        context["hierarchy"],
        draws,
        int(frozen_contract["bootstrap"]["dominance_seed"]),
    )
    common_bounds, common_diagnostics = _common_mode_bounds(
        context, frozen_contract, dominance_indices
    )
    gate_g1 = _gate_g1(context, frozen_contract, thresholds, fixture_indices)
    gate_g2 = _gate_g2(
        context,
        frozen_contract,
        thresholds,
        fixture_indices,
        common_bounds,
    )
    gate_g3 = _gate_g3(context, frozen_contract, thresholds, fixture_indices)
    gate_g4 = _gate_g4(context, thresholds)
    gate_g5 = _gate_g5(context, thresholds)
    gate_g6 = _gate_g6(context, thresholds)
    gate_g7 = _gate_g7(
        context,
        frozen_contract,
        thresholds,
        fixture_indices,
        common_bounds,
    )
    gate_g8 = _gate_g8(
        context,
        frozen_contract,
        thresholds,
        dominance_indices,
        common_bounds,
        common_diagnostics,
        gate_g7["status"] == "PASS",
    )
    gates = [
        gate_g1,
        gate_g2,
        gate_g3,
        gate_g4,
        gate_g5,
        gate_g6,
        gate_g7,
        gate_g8,
    ]
    return _result(profile, context["claim_scope"], gates)


def evaluate_sealed(
    path: os.PathLike[str] | str,
    expected_sha256: str,
    contract: Mapping[str, Any],
    profile: str = "synthetic_commission",
    *,
    calibration_manifest_path: os.PathLike[str] | str | None = None,
    calibration_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Load one sealed evidence artifact and evaluate it without reopening it."""

    evidence = _load_sealed_json(path, expected_sha256)
    manifest: Mapping[str, Any] | None = None
    if (calibration_manifest_path is None) != (calibration_manifest_sha256 is None):
        raise HarnessError(
            "production calibration path and expected SHA-256 must be supplied together"
        )
    if calibration_manifest_path is not None:
        assert calibration_manifest_sha256 is not None
        manifest = _load_sealed_json(
            calibration_manifest_path, calibration_manifest_sha256
        )
    result = evaluate_evidence(
        evidence,
        contract,
        profile,
        calibration_manifest=manifest,
    )
    result["evidence_sha256"] = expected_sha256.upper()
    return result


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("evidence", help="sealed evidence JSON path")
    parser.add_argument("expected_sha256", help="expected evidence SHA-256")
    parser.add_argument(
        "--contract",
        default=os.path.join(os.path.dirname(__file__), "contract.json"),
        help="frozen contract JSON path",
    )
    parser.add_argument(
        "--profile",
        choices=("synthetic_commission", "production"),
        default="synthetic_commission",
    )
    parser.add_argument("--calibration-manifest")
    parser.add_argument("--calibration-sha256")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)
    try:
        contract = load_sealed_json(args.contract, FROZEN_CONTRACT_SHA256)
        result = evaluate_sealed(
            args.evidence,
            args.expected_sha256,
            contract,
            args.profile,
            calibration_manifest_path=args.calibration_manifest,
            calibration_manifest_sha256=args.calibration_sha256,
        )
    except HarnessError as exc:
        failure = {
            "schema": _RESULT_SCHEMA,
            "status": "HARNESS_ERROR",
            "error": str(exc),
        }
        print(json.dumps(failure, sort_keys=True, allow_nan=False))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
