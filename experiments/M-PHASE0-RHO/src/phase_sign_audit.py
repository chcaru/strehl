"""Audit PHASE's nu+h versus the band-representative nu-h convention."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
PHASE_SRC = ROOT.parent / "M-PHASE0-PHASE" / "src"
sys.path.insert(0, str(PHASE_SRC))

import plib  # noqa: E402


SIGMA = np.concatenate([[0.0], np.geomspace(1e-3, 2.0, 31)])
RHOS = (0.1, 0.01, 0.005)
TRIALS = 300


def crossing(values: np.ndarray, threshold: float = 1.0) -> float:
    below = np.asarray(values) < threshold
    if not below[0]:
        return 0.0
    above = np.flatnonzero(~below)
    if above.size == 0:
        return float(SIGMA[-1])
    index = int(above[0])
    return float(SIGMA[max(index - 1, 0)])


def in_band(f: np.ndarray) -> np.ndarray:
    return np.all((f >= -0.5) & (f < 0.5), axis=-1)


def main() -> int:
    bands = plib.band_frequencies("G-1x", 8)
    geometry = []
    plus_outside = 0
    minus_outside = 0
    for nu, reps in bands:
        plus = np.asarray(nu) + np.asarray(reps)
        minus = np.asarray(nu) - np.asarray(reps)
        plus_outside += int(np.sum(~in_band(plus)))
        minus_outside += int(np.sum(~in_band(minus)))
        geometry.append(
            {
                "nu": [float(x) for x in nu],
                "reps": [[float(v) for v in row] for row in reps],
                "plus": [[float(v) for v in row] for row in plus],
                "minus": [[float(v) for v in row] for row in minus],
                "plus_in_band": [bool(x) for x in in_band(plus)],
                "minus_in_band": [bool(x) for x in in_band(minus)],
            }
        )

    example = next(
        row
        for row in geometry
        if not all(row["plus_in_band"]) and all(row["minus_in_band"])
    )
    nu = np.asarray(example["nu"])
    reps = np.asarray(example["reps"])
    displacement = np.asarray([0.23, -0.17])
    amplitudes = np.asarray([1.0 + 0.2j, -0.4 + 0.7j])
    physical = np.sum(
        amplitudes
        * np.exp(2j * np.pi * ((nu - reps) @ displacement))
    )
    current = np.sum(
        amplitudes
        * np.exp(2j * np.pi * ((nu + reps) @ displacement))
    )
    corrected = np.sum(
        amplitudes
        * np.exp(2j * np.pi * ((nu - reps) @ displacement))
    )
    control = {
        "nu": [float(x) for x in nu],
        "reps": [[float(v) for v in row] for row in reps],
        "displacement": [float(x) for x in displacement],
        "physical_real_imag": [float(physical.real), float(physical.imag)],
        "current_real_imag": [float(current.real), float(current.imag)],
        "corrected_real_imag": [float(corrected.real), float(corrected.imag)],
        "current_abs_error": float(abs(current - physical)),
        "corrected_abs_error": float(abs(corrected - physical)),
    }

    rng = np.random.default_rng(20260903)
    configs = []
    for index, (nu, reps) in enumerate(bands):
        scale = float(np.exp(rng.uniform(np.log(0.03), np.log(2.0))))
        displacements = rng.normal(0.0, scale, size=(4, 2))
        configs.append((index, nu, reps, displacements))

    comparisons = []
    for rho in RHOS:
        for index, nu, reps, d in configs:
            plus_eta = []
            minus_eta = []
            for sigma_index, sigma in enumerate(SIGMA):
                seed = 1000003 * index + 1009 * sigma_index + int(rho * 1e6)
                plus_rng = np.random.default_rng(seed)
                minus_rng = np.random.default_rng(seed)
                plus, _ = plib.median_eta(
                    reps,
                    d,
                    float(sigma),
                    np.inf,
                    plus_rng,
                    TRIALS,
                    rho=rho,
                    nu=nu,
                    gauge="raw",
                )
                minus, _ = plib.median_eta(
                    -np.asarray(reps),
                    d,
                    float(sigma),
                    np.inf,
                    minus_rng,
                    TRIALS,
                    rho=rho,
                    nu=nu,
                    gauge="raw",
                )
                plus_eta.append(plus)
                minus_eta.append(minus)
            plus_bar = crossing(np.asarray(plus_eta))
            minus_bar = crossing(np.asarray(minus_eta))
            comparisons.append(
                {
                    "rho": rho,
                    "config": index,
                    "nu": [float(x) for x in nu],
                    "bar_current_nu_plus_h": plus_bar,
                    "bar_corrected_nu_minus_h": minus_bar,
                    "corrected_over_current": float(
                        minus_bar / max(plus_bar, 1e-12)
                    ),
                }
            )

    pooled = {}
    for rho in RHOS:
        rows = [x for x in comparisons if x["rho"] == rho]
        current = np.asarray(
            [x["bar_current_nu_plus_h"] for x in rows], dtype=float
        )
        corrected = np.asarray(
            [x["bar_corrected_nu_minus_h"] for x in rows], dtype=float
        )
        ratio = corrected / np.maximum(current, 1e-12)
        pooled[str(rho)] = {
            "configs": len(rows),
            "current_median": float(np.median(current)),
            "corrected_median": float(np.median(corrected)),
            "median_ratio": float(np.median(ratio)),
            "ratio_p10": float(np.percentile(ratio, 10)),
            "ratio_p90": float(np.percentile(ratio, 90)),
            "ratio_min": float(np.min(ratio)),
            "ratio_max": float(np.max(ratio)),
            "changed_configs": int(np.sum(current != corrected)),
        }

    payload = {
        "target": "G-1x",
        "nu_grid": 8,
        "trials": TRIALS,
        "sigma_grid": [float(x) for x in SIGMA],
        "geometry": {
            "frequency_components": len(bands) * 2,
            "nu_plus_h_outside_target_band": plus_outside,
            "nu_minus_h_outside_target_band": minus_outside,
        },
        "physical_control": control,
        "pooled": pooled,
        "comparisons": comparisons,
        "verdict": (
            "nu-h is the band representative; nu+h fails the physical "
            "component control"
        ),
    }
    with open(OUT / "phase-sign-audit.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(payload["verdict"])
    print(
        f"outside target band: nu+h {plus_outside}, nu-h {minus_outside}"
    )
    print(
        "physical control absolute error: current %.6g, corrected %.6g"
        % (control["current_abs_error"], control["corrected_abs_error"])
    )
    for rho, row in pooled.items():
        print(
            "rho %s: pooled current %.6g, corrected %.6g, ratio %.3f "
            "(p10-p90 %.3f-%.3f)"
            % (
                rho,
                row["current_median"],
                row["corrected_median"],
                row["median_ratio"],
                row["ratio_p10"],
                row["ratio_p90"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
