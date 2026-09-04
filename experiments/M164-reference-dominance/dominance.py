"""Reference-information-dominance gate for paired physical witnesses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class GateConfig:
    delta_information: np.ndarray
    delta_transfer: np.ndarray
    bootstrap_draws: int = 10_000
    bootstrap_seed: int = 164_176
    dominance_alpha: float = 0.025
    minimum_power: float = 1.0e-10
    maximum_common_fraction: float = 0.05


def _as_complex_matrix(name: str, value: np.ndarray) -> np.ndarray:
    matrix = np.asarray(value, dtype=np.complex128)
    if matrix.ndim != 2:
        raise ValueError(f"{name} must have shape [sites, cells]")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} contains non-finite values")
    return matrix


def _as_cell_vector(
    name: str,
    value: np.ndarray,
    cells: int,
) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float64)
    if vector.shape != (cells,):
        raise ValueError(f"{name} must have shape [{cells}]")
    if not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} contains non-finite values")
    return vector


def _cross_power(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    return np.real(_cross_covariance(first, second))


def _cross_covariance(
    first: np.ndarray,
    second: np.ndarray,
) -> np.ndarray:
    first_centered = first - np.mean(first, axis=0, keepdims=True)
    second_centered = second - np.mean(second, axis=0, keepdims=True)
    return (
        np.sum(first_centered * np.conj(second_centered), axis=0)
        / (first.shape[0] - 1)
    )


def _mean_noise_power(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    difference = first - second
    difference -= np.mean(difference, axis=0, keepdims=True)
    # The admitted path estimate is the average of the two supplied
    # replicates. Under conditional independence, one quarter of their
    # difference power is the temporal-noise power in that average.
    return 0.25 * np.sum(np.abs(difference) ** 2, axis=0) / (
        first.shape[0] - 1
    )


def _statistics(
    reference_1: np.ndarray,
    reference_2: np.ndarray,
    scored_1: np.ndarray,
    scored_2: np.ndarray,
    reference_common_bound: np.ndarray,
    scored_common_bound: np.ndarray,
    minimum_power: float,
) -> dict[str, np.ndarray] | None:
    reference_cross = _cross_power(reference_1, reference_2)
    scored_cross = _cross_power(scored_1, scored_2)
    reference_difference_noise = _mean_noise_power(
        reference_1,
        reference_2,
    )
    scored_difference_noise = _mean_noise_power(scored_1, scored_2)

    reference_signal = reference_cross - reference_common_bound
    scored_signal = scored_cross + scored_common_bound
    reference_noise = reference_difference_noise + reference_common_bound
    scored_noise = scored_difference_noise - scored_common_bound
    valid = (
        np.all(reference_signal > minimum_power)
        and np.all(scored_signal > minimum_power)
        and np.all(reference_noise > minimum_power)
        and np.all(scored_noise > minimum_power)
    )
    if not valid:
        return None

    reference_information = 0.5 * np.log2(
        1.0 + reference_signal / reference_noise
    )
    scored_information = 0.5 * np.log2(
        1.0 + scored_signal / scored_noise
    )
    transfer_ratio = np.sqrt(reference_signal / scored_signal)
    return {
        "reference_cross_power": reference_cross,
        "scored_cross_power": scored_cross,
        "reference_signal_power": reference_signal,
        "scored_signal_power": scored_signal,
        "reference_difference_noise_power": reference_difference_noise,
        "scored_difference_noise_power": scored_difference_noise,
        "reference_noise_power": reference_noise,
        "scored_noise_power": scored_noise,
        "reference_information": reference_information,
        "scored_information": scored_information,
        "information_ratio": reference_information / scored_information,
        "transfer_ratio": transfer_ratio,
    }


def _serialise(vector: np.ndarray) -> list[float]:
    return [float(value) for value in vector]


def estimate_common_mode_bounds(
    reference_control_1: np.ndarray,
    reference_control_2: np.ndarray,
    scored_control_1: np.ndarray,
    scored_control_2: np.ndarray,
    *,
    alpha: float = 0.025,
    bootstrap_draws: int = 10_000,
    bootstrap_seed: int = 164_175,
    minimum_power: float = 1.0e-10,
) -> dict[str, Any]:
    """Return simultaneous UCBs for repeatable non-scene covariance."""

    reference_control_1 = _as_complex_matrix(
        "reference_control_1",
        reference_control_1,
    )
    reference_control_2 = _as_complex_matrix(
        "reference_control_2",
        reference_control_2,
    )
    scored_control_1 = _as_complex_matrix(
        "scored_control_1",
        scored_control_1,
    )
    scored_control_2 = _as_complex_matrix(
        "scored_control_2",
        scored_control_2,
    )
    if reference_control_1.shape != reference_control_2.shape:
        raise ValueError("reference controls must have matching shapes")
    if scored_control_1.shape != scored_control_2.shape:
        raise ValueError("scored controls must have matching shapes")
    if reference_control_1.shape[1] != scored_control_1.shape[1]:
        raise ValueError("reference and scored controls need equal cells")
    if reference_control_1.shape[0] < 8 or scored_control_1.shape[0] < 8:
        raise ValueError("at least eight control sites per path are required")
    if not 0.0 < alpha < 0.5:
        raise ValueError("alpha must lie in (0, 0.5)")

    reference_point = np.abs(
        _cross_covariance(reference_control_1, reference_control_2)
    )
    scored_point = np.abs(
        _cross_covariance(scored_control_1, scored_control_2)
    )
    point = np.concatenate([reference_point, scored_point])
    cells = reference_control_1.shape[1]
    bootstrap = np.empty((bootstrap_draws, 2 * cells), dtype=np.float64)
    rng = np.random.default_rng(bootstrap_seed)
    for draw in range(bootstrap_draws):
        reference_indices = rng.integers(
            0,
            reference_control_1.shape[0],
            size=reference_control_1.shape[0],
        )
        scored_indices = rng.integers(
            0,
            scored_control_1.shape[0],
            size=scored_control_1.shape[0],
        )
        bootstrap[draw, :cells] = np.abs(
            _cross_covariance(
                reference_control_1[reference_indices],
                reference_control_2[reference_indices],
            )
        )
        bootstrap[draw, cells:] = np.abs(
            _cross_covariance(
                scored_control_1[scored_indices],
                scored_control_2[scored_indices],
            )
        )

    standard_error = np.std(bootstrap, axis=0, ddof=1)
    if np.any(standard_error <= minimum_power):
        raise ValueError("common-mode bootstrap is degenerate")
    studentized_error = (
        bootstrap - point[np.newaxis, :]
    ) / standard_error[np.newaxis, :]
    maximum_error = np.max(studentized_error, axis=1)
    critical = float(
        np.quantile(maximum_error, 1.0 - alpha, method="higher")
    )
    upper = point + critical * standard_error
    return {
        "family": {
            "members": 2 * cells,
            "contents": (
                "absolute repeatable control covariance for both paths "
                "and every frozen cell"
            ),
            "method": "one-sided max-t cluster bootstrap",
            "alpha": alpha,
            "draws": bootstrap_draws,
            "seed": bootstrap_seed,
        },
        "reference_point": _serialise(reference_point),
        "scored_point": _serialise(scored_point),
        "reference_ucb": _serialise(upper[:cells]),
        "scored_ucb": _serialise(upper[cells:]),
        "critical_value": critical,
    }


def evaluate_dominance(
    reference_1: np.ndarray,
    reference_2: np.ndarray,
    scored_1: np.ndarray,
    scored_2: np.ndarray,
    reference_common_bound: np.ndarray,
    scored_common_bound: np.ndarray,
    config: GateConfig,
    *,
    known_latent_power: np.ndarray | None = None,
) -> dict[str, Any]:
    """Evaluate strict per-cell reference dominance.

    The common-mode bounds are simultaneous upper confidence bounds obtained
    from independent controls.  This function spends ``dominance_alpha`` on a
    paired-site max-t lower confidence family over both information and
    transfer margins.
    """

    reference_1 = _as_complex_matrix("reference_1", reference_1)
    reference_2 = _as_complex_matrix("reference_2", reference_2)
    scored_1 = _as_complex_matrix("scored_1", scored_1)
    scored_2 = _as_complex_matrix("scored_2", scored_2)
    shapes = {
        reference_1.shape,
        reference_2.shape,
        scored_1.shape,
        scored_2.shape,
    }
    if len(shapes) != 1:
        raise ValueError("all witness matrices must have the same shape")
    sites, cells = reference_1.shape
    if sites < 8:
        raise ValueError("at least eight paired physical sites are required")

    reference_common_bound = _as_cell_vector(
        "reference_common_bound",
        reference_common_bound,
        cells,
    )
    scored_common_bound = _as_cell_vector(
        "scored_common_bound",
        scored_common_bound,
        cells,
    )
    if np.any(reference_common_bound < 0.0) or np.any(
        scored_common_bound < 0.0
    ):
        raise ValueError("common-mode bounds must be nonnegative")
    delta_information = _as_cell_vector(
        "delta_information",
        config.delta_information,
        cells,
    )
    delta_transfer = _as_cell_vector(
        "delta_transfer",
        config.delta_transfer,
        cells,
    )
    if np.any(delta_information <= 0.0) or np.any(delta_transfer <= 0.0):
        raise ValueError("dominance margins must be strictly positive")
    if not 0.0 < config.dominance_alpha < 0.5:
        raise ValueError("dominance_alpha must lie in (0, 0.5)")

    point = _statistics(
        reference_1,
        reference_2,
        scored_1,
        scored_2,
        reference_common_bound,
        scored_common_bound,
        config.minimum_power,
    )
    raw_reference_cross = _cross_power(reference_1, reference_2)
    raw_scored_cross = _cross_power(scored_1, scored_2)
    reference_common_fraction = np.divide(
        reference_common_bound,
        np.maximum(np.abs(raw_reference_cross), config.minimum_power),
    )
    scored_common_fraction = np.divide(
        scored_common_bound,
        np.maximum(np.abs(raw_scored_cross), config.minimum_power),
    )
    common_mode_pass = bool(
        np.all(reference_common_fraction <= config.maximum_common_fraction)
        and np.all(scored_common_fraction <= config.maximum_common_fraction)
    )

    result: dict[str, Any] = {
        "status": "UNMEASURED",
        "sites": sites,
        "cells": cells,
        "family": {
            "members": 2 * cells,
            "contents": (
                "log information-ratio and log transfer-ratio margins for "
                "every frozen cell"
            ),
            "method": "paired-site one-sided max-t cluster bootstrap",
            "alpha": config.dominance_alpha,
            "draws": config.bootstrap_draws,
            "seed": config.bootstrap_seed,
        },
        "delta_information": _serialise(delta_information),
        "delta_transfer": _serialise(delta_transfer),
        "reference_common_bound": _serialise(reference_common_bound),
        "scored_common_bound": _serialise(scored_common_bound),
        "reference_common_fraction": _serialise(reference_common_fraction),
        "scored_common_fraction": _serialise(scored_common_fraction),
        "common_mode_pass": common_mode_pass,
        "absolute_transfer_status": (
            "KNOWN_INPUT"
            if known_latent_power is not None
            else "ABSOLUTE_TRANSFER_UNIDENTIFIED"
        ),
        "failed_cells": [],
    }
    if point is None:
        result["failure"] = "NONPOSITIVE_POWER_OR_NOISE"
        result["failed_cells"] = list(range(cells))
        return result

    information_margin = np.log(point["information_ratio"]) - np.log1p(
        delta_information
    )
    transfer_margin = np.log(point["transfer_ratio"]) - np.log1p(
        delta_transfer
    )
    point_margin = np.concatenate([information_margin, transfer_margin])

    rng = np.random.default_rng(config.bootstrap_seed)
    bootstrap_margin = np.empty(
        (config.bootstrap_draws, 2 * cells),
        dtype=np.float64,
    )
    valid_draws = np.ones(config.bootstrap_draws, dtype=bool)
    for draw in range(config.bootstrap_draws):
        indices = rng.integers(0, sites, size=sites)
        draw_stats = _statistics(
            reference_1[indices],
            reference_2[indices],
            scored_1[indices],
            scored_2[indices],
            reference_common_bound,
            scored_common_bound,
            config.minimum_power,
        )
        if draw_stats is None:
            valid_draws[draw] = False
            bootstrap_margin[draw] = np.nan
            continue
        draw_information_margin = np.log(
            draw_stats["information_ratio"]
        ) - np.log1p(delta_information)
        draw_transfer_margin = np.log(
            draw_stats["transfer_ratio"]
        ) - np.log1p(delta_transfer)
        bootstrap_margin[draw] = np.concatenate(
            [draw_information_margin, draw_transfer_margin]
        )

    result["valid_bootstrap_draws"] = int(np.sum(valid_draws))
    if not np.all(valid_draws):
        result["failure"] = "INVALID_BOOTSTRAP_DRAW"
        result["failed_cells"] = list(range(cells))
        return result

    standard_error = np.std(bootstrap_margin, axis=0, ddof=1)
    if np.any(standard_error <= config.minimum_power):
        result["failure"] = "DEGENERATE_BOOTSTRAP"
        result["failed_cells"] = list(range(cells))
        return result
    studentized_error = (
        bootstrap_margin - point_margin[np.newaxis, :]
    ) / standard_error[np.newaxis, :]
    maximum_error = np.max(studentized_error, axis=1)
    critical = float(
        np.quantile(
            maximum_error,
            1.0 - config.dominance_alpha,
            method="higher",
        )
    )
    simultaneous_lcb = point_margin - critical * standard_error
    information_lcb = simultaneous_lcb[:cells]
    transfer_lcb = simultaneous_lcb[cells:]

    information_pass = information_lcb > 0.0
    transfer_pass = transfer_lcb > 0.0
    cell_pass = information_pass & transfer_pass
    result.update(
        {
            "critical_value": critical,
            "point": {
                name: _serialise(value) for name, value in point.items()
            },
            "information_log_margin": _serialise(information_margin),
            "transfer_log_margin": _serialise(transfer_margin),
            "information_simultaneous_lcb": _serialise(information_lcb),
            "transfer_simultaneous_lcb": _serialise(transfer_lcb),
            "information_pass": [bool(value) for value in information_pass],
            "transfer_pass": [bool(value) for value in transfer_pass],
            "cell_pass": [bool(value) for value in cell_pass],
        }
    )

    if known_latent_power is not None:
        latent_power = _as_cell_vector(
            "known_latent_power",
            known_latent_power,
            cells,
        )
        if np.any(latent_power <= config.minimum_power):
            result["failure"] = "INVALID_KNOWN_INPUT_POWER"
            result["failed_cells"] = list(range(cells))
            return result
        if np.any(
            point["reference_cross_power"] <= config.minimum_power
        ) or np.any(point["scored_cross_power"] <= config.minimum_power):
            result["failure"] = "NONPOSITIVE_ABSOLUTE_TRANSFER_POWER"
            result["failed_cells"] = list(range(cells))
            return result
        result["absolute_transfer"] = {
            "reference_point": _serialise(
                np.sqrt(point["reference_cross_power"] / latent_power)
            ),
            "scored_point": _serialise(
                np.sqrt(point["scored_cross_power"] / latent_power)
            ),
            "reference_charged_lower": _serialise(
                np.sqrt(point["reference_signal_power"] / latent_power)
            ),
            "scored_charged_upper": _serialise(
                np.sqrt(point["scored_signal_power"] / latent_power)
            ),
        }

    failed_cells = np.flatnonzero(~cell_pass).tolist()
    if not common_mode_pass:
        failed_cells = sorted(
            set(failed_cells)
            | set(
                np.flatnonzero(
                    (
                        reference_common_fraction
                        > config.maximum_common_fraction
                    )
                    | (
                        scored_common_fraction
                        > config.maximum_common_fraction
                    )
                ).tolist()
            )
        )
    result["failed_cells"] = failed_cells
    if failed_cells:
        result["failure"] = (
            "COMMON_MODE_BOUND"
            if not common_mode_pass
            else "DOMINANCE_NOT_ESTABLISHED"
        )
        return result

    result["status"] = "PASS"
    result["failure"] = None
    return result
