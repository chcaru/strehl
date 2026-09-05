"""Pinned rho convention and C1 verdict read for M183.

This script intentionally consumes the accepted fitted scene parameters from
M-PHASE0-RHO. It does not decode RAW files and does not refit a spectrum.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Callable, Iterable

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STREHL = ROOT.parent.parent
OUT = ROOT / "out"
SCENE_ESTIMATES = (
    STREHL / "experiments" / "M-PHASE0-RHO" / "out" / "scene-estimates.json"
)
PHASE_BAR = (
    STREHL / "experiments" / "M-PHASE0-PHASE" / "out" / "p1_bar.json"
)
COMMISSION = OUT / "commission.json"
RESULT = OUT / "result.json"

GRID = 8
BOUNDARY = "average"
FREQUENCY_SCALE = 1.0
POWER_R0 = 0.02
BOOTSTRAPS = 10_000
BOOTSTRAP_SEED = 20260902

G_SHIFT = np.array([0.5, 0.5], dtype=float)
ORDINARY_SCENES = (
    "bee-1-cpl",
    "dry-erase-marker-head-cpl",
    "flower-inner-edge-cpl",
    "pencil-steep-angle-cpl",
    "wrapped-text-1",
)
ACCURACY = (
    ("field centre", 0.0801),
    ("inner annulus", 0.1168),
    ("corner", 0.2256),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wrap_sensor_band(frequency: np.ndarray) -> np.ndarray:
    """Wrap normalized sensor frequency into the half-open Nyquist square."""
    value = np.asarray(frequency, dtype=float)
    return np.mod(value + 0.5, 1.0) - 0.5


def point_key(frequency: np.ndarray) -> tuple[int, int]:
    value = np.asarray(frequency, dtype=float)
    return tuple(int(round(float(x) * 1_000_000_000)) for x in value)


def group_key(
    points: Iterable[np.ndarray],
) -> tuple[tuple[int, int], ...]:
    return tuple(sorted(point_key(point) for point in points))


def in_green_base(frequency: np.ndarray, tolerance: float = 1e-12) -> bool:
    return bool(np.abs(np.asarray(frequency, dtype=float)).sum() <= 0.5 + tolerance)


def alias_groups(grid: int | None = None) -> list[dict]:
    """Enumerate unique green one-times alias pairs on the pinned grid."""
    use_grid = GRID if grid is None else int(grid)
    if use_grid <= 0:
        raise ValueError("grid must be positive")
    coords = -0.5 + (np.arange(use_grid, dtype=float) + 0.5) / use_grid
    seen: dict[tuple[tuple[int, int], ...], dict] = {}
    for fy in coords:
        for fx in coords:
            frequency = np.array([fx, fy], dtype=float)
            points = [frequency, wrap_sensor_band(frequency + G_SHIFT)]
            key = group_key(points)
            if key in seen:
                continue
            candidates = [point for point in points if in_green_base(point)]
            if not candidates:
                raise ValueError(f"green group has no base representative: {points!r}")
            candidates = sorted(
                (np.asarray(point, dtype=float) for point in candidates),
                key=lambda point: (
                    round(float(np.linalg.norm(point)), 14),
                    point_key(point),
                ),
            )
            seen[key] = {
                "points": [np.asarray(point, dtype=float) for point in points],
                "base_candidates": candidates,
                "boundary_ambiguous": len(candidates) > 1,
            }
    return [seen[key] for key in sorted(seen)]


def physical_frequency(frequency: np.ndarray) -> np.ndarray:
    """Convert normalized coordinates to the pinned physical frequency unit."""
    return FREQUENCY_SCALE * np.asarray(frequency, dtype=float)


def angular_log_factor(
    frequency: np.ndarray,
    angular: tuple[float, float, float, float],
) -> np.ndarray:
    value = physical_frequency(frequency)
    theta = np.arctan2(value[..., 1], value[..., 0])
    c2, s2, c4, s4 = angular
    return (
        c2 * np.cos(2.0 * theta)
        + s2 * np.sin(2.0 * theta)
        + c4 * np.cos(4.0 * theta)
        + s4 * np.sin(4.0 * theta)
    )


def model_power(
    frequency: np.ndarray,
    beta: float,
    angular: tuple[float, float, float, float],
) -> float:
    value = physical_frequency(frequency)
    radius = max(float(np.linalg.norm(value)), POWER_R0)
    return float(
        radius ** (-float(beta))
        * np.exp(angular_log_factor(frequency, angular))
    )


def rho_from_power(
    power: Callable[[np.ndarray], float],
    *,
    grid: int | None = None,
    boundary: str | None = None,
) -> float:
    """Reduce sampled component powers to the A2.2 common scalar."""
    use_boundary = BOUNDARY if boundary is None else boundary
    if use_boundary not in ("primary", "swap", "average", "exclude"):
        raise ValueError(f"unknown boundary convention {use_boundary!r}")
    base_total = 0.0
    alias_total = 0.0
    alias_assignments = 0.0
    groups_used = 0
    for group in alias_groups(grid):
        candidates = group["base_candidates"]
        if use_boundary == "exclude" and len(candidates) > 1:
            continue
        if use_boundary == "average" and len(candidates) > 1:
            assignments = candidates
        elif use_boundary == "swap" and len(candidates) > 1:
            assignments = [candidates[-1]]
        else:
            assignments = [candidates[0]]
        weight = 1.0 / len(assignments)
        for chosen in assignments:
            base_total += weight * float(power(chosen))
            for frequency in group["points"]:
                if point_key(frequency) == point_key(chosen):
                    continue
                alias_total += weight * float(power(frequency))
                alias_assignments += weight
        groups_used += 1
    if groups_used == 0 or base_total <= 0.0:
        raise ValueError("rho reduction has no positive base power")
    aliases_per_group = alias_assignments / groups_used
    return alias_total / (aliases_per_group * base_total)


def rho_from_model(
    beta: float,
    angular: tuple[float, float, float, float],
    *,
    grid: int | None = None,
    boundary: str | None = None,
) -> float:
    return rho_from_power(
        lambda frequency: model_power(frequency, beta, angular),
        grid=grid,
        boundary=boundary,
    )


def primary_fit(record: dict) -> dict:
    fit = record["fits"][record.get("primary_fit_key", "full_a")]
    if fit.get("status") != "PASS":
        raise ValueError("a PASS record has a non-PASS primary fit")
    return fit


def selected_scene_rows(records: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for scene in ORDINARY_SCENES:
        rows = [
            record
            for record in records
            if record.get("arm") == "ordinary-census"
            and record.get("scene") == scene
            and record.get("status") == "PASS"
        ]
        if not rows:
            raise ValueError(f"no accepted records for required scene {scene}")
        groups[scene] = rows
    repeat = [
        record
        for record in records
        if record.get("arm") == "repeat-primary"
        and record.get("scene") == "bee"
        and record.get("status") == "PASS"
    ]
    if not repeat:
        raise ValueError("no accepted bee repeat records")
    groups["bee-repeat"] = repeat
    return groups


def scene_values(
    records: list[dict],
    boundary: str | None = None,
    grid: int | None = None,
) -> tuple[dict, dict]:
    groups = selected_scene_rows(records)
    values: dict[str, float] = {}
    counts: dict[str, int] = {}
    for scene, rows in groups.items():
        record_values = []
        for record in rows:
            fit = primary_fit(record)
            record_values.append(
                rho_from_model(
                    float(fit["beta"]),
                    tuple(float(value) for value in fit["angular"]),
                    grid=grid,
                    boundary=boundary,
                )
            )
        values[scene] = float(np.median(np.asarray(record_values, dtype=float)))
        counts[scene] = len(record_values)
    return values, counts


def bootstrap_scene_median(
    values: Iterable[float],
    *,
    seed: int = BOOTSTRAP_SEED,
    draws: int = BOOTSTRAPS,
) -> dict:
    sample = np.asarray(list(values), dtype=float)
    if sample.ndim != 1 or sample.size == 0 or np.any(sample <= 0.0):
        raise ValueError("bootstrap requires positive one-dimensional scene values")
    generator = np.random.default_rng(seed)
    boot = np.median(
        generator.choice(sample, size=(draws, sample.size), replace=True),
        axis=1,
    )
    return {
        "n_scenes": int(sample.size),
        "draws": int(draws),
        "seed": int(seed),
        "median": float(np.median(sample)),
        "interval_95": [
            float(np.percentile(boot, 2.5)),
            float(np.percentile(boot, 97.5)),
        ],
    }


def stored_reproduction(records: list[dict]) -> dict:
    """Cross-check the independent implementation against stored per-fit values."""
    primary_errors = []
    average_errors = []
    checked = 0
    for rows in selected_scene_rows(records).values():
        for record in rows:
            fit = primary_fit(record)
            beta = float(fit["beta"])
            angular = tuple(float(value) for value in fit["angular"])
            got_primary = rho_from_model(beta, angular, boundary="primary")
            got_average = rho_from_model(beta, angular, boundary="average")
            expected_primary = float(fit["rho_g"])
            expected_average = float(fit["rho_g_boundary_average"])
            primary_errors.append(
                abs(got_primary - expected_primary) / expected_primary
            )
            average_errors.append(
                abs(got_average - expected_average) / expected_average
            )
            checked += 1
    return {
        "records": checked,
        "primary_max_relative_error": float(max(primary_errors)),
        "average_max_relative_error": float(max(average_errors)),
    }


@dataclass(frozen=True)
class BarCurve:
    metadata: tuple
    rhos: np.ndarray
    bars: np.ndarray


def load_phase_curves(payload: dict) -> list[BarCurve]:
    selected = [
        row
        for row in payload["rows"]
        if row["target"] == "G-1x"
        and str(row["snr"]) == "inf"
        and row["gauge"] == "zero_mean"
        and row["bar_unit"] is not None
    ]
    rhos = sorted({float(row["rho"]) for row in selected})
    by_rho = {
        rho: [row for row in selected if float(row["rho"]) == rho]
        for rho in rhos
    }
    counts = {rho: len(rows) for rho, rows in by_rho.items()}
    if len(set(counts.values())) != 1:
        raise ValueError(f"PHASE rho rungs have unequal counts: {counts}")
    count = next(iter(counts.values()))
    curves = []
    for index in range(count):
        rows = [by_rho[rho][index] for rho in rhos]
        metadata = tuple(
            rows[0][key] for key in ("target", "N", "M", "kappa", "nu_abs", "snr", "gauge")
        )
        for row in rows[1:]:
            got = tuple(
                row[key]
                for key in ("target", "N", "M", "kappa", "nu_abs", "snr", "gauge")
            )
            if got != metadata:
                raise ValueError("PHASE rows cannot be paired across rho")
        bars = np.asarray([float(row["bar_unit"]) for row in rows], dtype=float)
        if np.any(bars <= 0.0):
            raise ValueError("noiseless PHASE curve has a nonpositive bar")
        if np.any(np.diff(bars) < -1e-12):
            raise ValueError("noiseless PHASE curve is nonmonotone in rho")
        curves.append(
            BarCurve(
                metadata=metadata,
                rhos=np.asarray(rhos, dtype=float),
                bars=bars,
            )
        )
    return curves


def interpolate_bar(curve: BarCurve, rho: float) -> float:
    if not (curve.rhos[0] <= rho <= curve.rhos[-1]):
        raise ValueError(f"rho {rho} lies outside PHASE ladder")
    return float(
        math.exp(
            np.interp(
                math.log(rho),
                np.log(curve.rhos),
                np.log(curve.bars),
            )
        )
    )


def classify_fraction(fraction: float) -> str:
    if fraction >= 0.60:
        return "SURVIVE"
    if fraction >= 0.25:
        return "NARROWED"
    return "KILL"


def verdict_at_rho(curves: list[BarCurve], rho: float) -> dict:
    bars = np.asarray([interpolate_bar(curve, rho) for curve in curves])
    result = {}
    for label, accuracy in ACCURACY:
        fraction = float(np.mean(bars > accuracy))
        result[label] = {
            "accuracy_px": accuracy,
            "winnable_fraction": fraction,
            "verdict": classify_fraction(fraction),
        }
    return result


def transition_rho(
    curves: list[BarCurve],
    accuracy: float,
    target_fraction: float,
    low: float,
    high: float,
) -> float | None:
    def fraction(rho: float) -> float:
        bars = np.asarray([interpolate_bar(curve, rho) for curve in curves])
        return float(np.mean(bars > accuracy))

    if fraction(low) >= target_fraction or fraction(high) < target_fraction:
        return None
    lo = math.log(low)
    hi = math.log(high)
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if fraction(math.exp(mid)) >= target_fraction:
            hi = mid
        else:
            lo = mid
    return float(math.exp(hi))


def assert_commissioned() -> dict:
    if not COMMISSION.exists():
        raise RuntimeError("commission.json is absent; run commission.py first")
    payload = json.loads(COMMISSION.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise RuntimeError("commissioning did not pass")
    expected = payload["input_sha256"]
    actual = {
        "scene-estimates.json": sha256_file(SCENE_ESTIMATES),
        "p1_bar.json": sha256_file(PHASE_BAR),
    }
    if actual != expected:
        raise RuntimeError(
            f"commissioned input hashes changed: expected {expected}, got {actual}"
        )
    instrument_hash = sha256_file(Path(__file__))
    if instrument_hash != payload["instrument_sha256"]:
        raise RuntimeError(
            "instrument changed after commissioning: "
            f"expected {payload['instrument_sha256']}, got {instrument_hash}"
        )
    return payload


def main() -> int:
    commission = assert_commissioned()
    records = json.loads(SCENE_ESTIMATES.read_text(encoding="utf-8"))
    values, counts = scene_values(records)
    sampling = bootstrap_scene_median(values.values())
    reproduction = stored_reproduction(records)
    if reproduction["primary_max_relative_error"] > 1e-12:
        raise RuntimeError(f"primary stored-value reproduction failed: {reproduction}")
    if reproduction["average_max_relative_error"] > 1e-12:
        raise RuntimeError(f"average stored-value reproduction failed: {reproduction}")

    phase_payload = json.loads(PHASE_BAR.read_text(encoding="utf-8"))
    curves = load_phase_curves(phase_payload)
    low, high = sampling["interval_95"]
    points = {
        "interval_low": verdict_at_rho(curves, low),
        "median": verdict_at_rho(curves, sampling["median"]),
        "interval_high": verdict_at_rho(curves, high),
    }
    flips = any(
        points["interval_low"][label]["verdict"]
        != points["interval_high"][label]["verdict"]
        for label, _ in ACCURACY
    )
    transitions = {}
    for label, accuracy in ACCURACY:
        transitions[label] = {
            "kill_to_narrowed_rho": transition_rho(
                curves, accuracy, 0.25, low, high
            ),
            "narrowed_to_survive_rho": transition_rho(
                curves, accuracy, 0.60, low, high
            ),
        }

    groups = alias_groups()
    grid_crux = {}
    for grid in (8, 16, 32):
        grid_values, _ = scene_values(records, grid=grid)
        grid_groups = alias_groups(grid)
        base_radii = [
            float(np.linalg.norm(candidate))
            for group in grid_groups
            for candidate in group["base_candidates"]
        ]
        grid_crux[str(grid)] = {
            "scene_median": float(np.median(list(grid_values.values()))),
            "minimum_base_radius": min(base_radii),
            "unique_groups": len(grid_groups),
            "ambiguous_groups": sum(
                1 for group in grid_groups if group["boundary_ambiguous"]
            ),
        }
    grid_crux["factor_8_to_32"] = (
        grid_crux["8"]["scene_median"] / grid_crux["32"]["scene_median"]
    )

    boundary_sensitivity = {}
    for boundary in ("primary", "swap", "average", "exclude"):
        boundary_values, _ = scene_values(records, boundary=boundary)
        boundary_sensitivity[boundary] = bootstrap_scene_median(
            boundary_values.values()
        )

    payload = {
        "status": "PASS",
        "answer": "STILL_FLIPS" if flips else "STABLE",
        "convention": {
            "frequency_unit": "cycles per full-resolution sensor pixel",
            "grid": GRID,
            "grid_sampling": "cell-centred over [-0.5,0.5)^2",
            "alias_pairs_deduplicated": True,
            "boundary": BOUNDARY,
            "spatial_boundary": (
                "stored commissioned fits: in-bounds square GQ patches, "
                "256-square 50%-overlap periodic-Hann Welch, no padding"
            ),
            "unique_groups": len(groups),
            "ambiguous_groups": sum(
                1 for group in groups if group["boundary_ambiguous"]
            ),
        },
        "grid_crux": grid_crux,
        "boundary_sensitivity": boundary_sensitivity,
        "rho": {
            **sampling,
            "scene_values": values,
            "accepted_record_counts": counts,
            "population": "five f/5.6 ordinary scenes plus independent bee repeat",
            "scope": (
                "scene-cluster sampling interval only; model/grid/sensor "
                "systematics are not included"
            ),
        },
        "c1": {
            "phase_curves": len(curves),
            "gauge": "zero_mean",
            "snr": "inf",
            "interpolation": "linear log(bar) in log(rho)",
            "points": points,
            "transitions_within_interval": transitions,
            "verdict_flips_across_interval": flips,
            "additional_decision_required": (
                "Preregister the target scene population and product risk "
                "functional (which scene/quantile must pass), then run the "
                "owed per-site joint scene-frequency census; the corpus "
                "contains neither a licensed population weighting nor that census."
                if flips
                else None
            ),
        },
        "stored_value_reproduction": reproduction,
        "input_sha256": commission["input_sha256"],
        "instrument_sha256": sha256_file(Path(__file__)),
        "preregistration_commit": "014063e498a2f0a1faf627b7bb7534e3163e76cd",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        "rho %.9g, 95%% %.9g to %.9g; C1 %s"
        % (
            sampling["median"],
            low,
            high,
            payload["answer"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
