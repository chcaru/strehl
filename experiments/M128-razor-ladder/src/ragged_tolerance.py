"""Measure the C2 pipeline's tolerance to locus raggedness.

This is synthetic-only. It preserves the original C2 random-walk plant and
compares straight-line registration with registration on each measured
per-column 50% crossing.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out" / "ragged-tolerance.json"

sys.path.insert(0, str(HERE))
import commission as C  # noqa: E402


PLANTED_FC_CYMM = 105.54
ANGLE_DEG = -0.68
BAR_PCT = 5.0
GEOMETRY_PLANTS = 64
NOISE_REALIZATIONS_PER_PLANT = 2
GEOMETRY_SEED_BASE = 81000
NOISE_SEED_BASE = 82000
BOOTSTRAP_SAMPLES = 10000
RMS_GRID_GREEN_PX = tuple(
    [round(i / 100.0, 2) for i in range(0, 11)]
    + [round(i / 10.0, 1) for i in range(2, 16)]
)
METHODS = {
    "straight_line": "inf",
    "measured_per_column": 1,
}

ORIGINAL_C2_FIXTURE_SHA256 = (
    "59dac301a0c07e8690b0994776bf33f8500e32019d9b95352b9558b4ad67128a"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def c2_unit_offsets(ncols: int, seed: int) -> np.ndarray:
    """Original C2 random-walk locus, normalized to 1 sensor-pixel RMS."""
    rng = np.random.default_rng(seed)
    walk = np.cumsum(rng.normal(0.0, 1.0, ncols))
    radius = 8
    kernel = np.ones(2 * radius + 1, dtype=float) / (2 * radius + 1)
    smooth = np.convolve(
        np.pad(walk, (radius, radius), mode="reflect"),
        kernel,
        mode="valid",
    )
    x = np.arange(ncols, dtype=float)
    smooth -= np.polyval(np.polyfit(x, smooth, 1), x)
    return smooth / np.sqrt(np.mean(smooth * smooth))


def offsets_at_rms(unit_offsets: np.ndarray, rms_green_px: float) -> np.ndarray:
    return unit_offsets * (2.0 * rms_green_px)


def bootstrap_median_ci(values: np.ndarray, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    indices = rng.integers(
        0, len(values), size=(BOOTSTRAP_SAMPLES, len(values))
    )
    medians = np.median(values[indices], axis=1)
    return [
        float(np.percentile(medians, 2.5)),
        float(np.percentile(medians, 97.5)),
    ]


def summarize_plants(
    plant_records: list[dict],
    method_index: int,
    rms_index: int,
) -> dict:
    valid = [p for p in plant_records if p["recovered_fc_cymm"] is not None]
    errors = np.asarray([p["error_pct"] for p in valid], dtype=float)
    recovered = np.asarray(
        [p["recovered_fc_cymm"] for p in valid], dtype=float
    )
    smears = np.asarray([p["residual_smear_um"] for p in valid], dtype=float)
    if len(valid) != GEOMETRY_PLANTS:
        return {
            "valid_plants": len(valid),
            "total_plants": GEOMETRY_PLANTS,
            "central_bar_pass": False,
            "plants": plant_records,
        }

    median_error = float(np.median(errors))
    first_half = float(np.median(errors[: GEOMETRY_PLANTS // 2]))
    second_half = float(np.median(errors[GEOMETRY_PLANTS // 2 :]))
    return {
        "valid_plants": len(valid),
        "total_plants": GEOMETRY_PLANTS,
        "noise_realizations_per_plant": NOISE_REALIZATIONS_PER_PLANT,
        "recovered_fc_cymm": float(np.median(recovered)),
        "error_pct": median_error,
        "abs_error_pct": abs(median_error),
        "error_mean_pct": float(np.mean(errors)),
        "error_sd_pct": float(np.std(errors, ddof=1)),
        "error_p16_pct": float(np.percentile(errors, 16.0)),
        "error_p84_pct": float(np.percentile(errors, 84.0)),
        "error_mad_pct": float(
            np.median(np.abs(errors - np.median(errors)))
        ),
        "median_error_bootstrap_95pct_ci": bootstrap_median_ci(
            errors,
            900000 + 1000 * method_index + rms_index,
        ),
        "plant_pass_count": int(np.sum(np.abs(errors) <= BAR_PCT)),
        "plant_pass_fraction": float(np.mean(np.abs(errors) <= BAR_PCT)),
        "plants_with_fit_fc_upper_boundary": int(
            sum(p["fit_fc_upper_boundary"] for p in valid)
        ),
        "residual_smear_um": float(np.median(smears)),
        "residual_smear_p16_um": float(np.percentile(smears, 16.0)),
        "residual_smear_p84_um": float(np.percentile(smears, 84.0)),
        "first_half_median_error_pct": first_half,
        "second_half_median_error_pct": second_half,
        "split_half_delta_pct_points": abs(first_half - second_half),
        "central_bar_pass": abs(median_error) <= BAR_PCT,
        "plants": plant_records,
    }


def crossing_summary(rows: list[dict]) -> dict:
    first_fail_index = None
    for index, row in enumerate(rows):
        if not row["central_bar_pass"]:
            first_fail_index = index
            break

    passing = [
        row["raggedness_rms_green_px"]
        for row in rows
        if row["central_bar_pass"]
    ]
    result = {
        "bar_definition": (
            "Absolute error of the median recovered fc across "
            f"{GEOMETRY_PLANTS} independent locus plants, each itself the "
            f"median of {NOISE_REALIZATIONS_PER_PLANT} noise realizations."
        ),
        "maximum_passing_sampled_rms_green_px_anywhere": (
            max(passing) if passing else None
        ),
        "passing_sampled_rms_green_px": passing,
    }
    if first_fail_index == 0:
        result.update(
            {
                "first_contiguous_failure": "already fails at zero raggedness",
                "maximum_contiguous_passing_rms_green_px": None,
                "first_crossing_bracket_green_px": [0.0, 0.0],
                "interpolated_first_crossing_green_px": 0.0,
            }
        )
        return result
    if first_fail_index is None:
        result.update(
            {
                "first_contiguous_failure": None,
                "maximum_contiguous_passing_rms_green_px": rows[-1][
                    "raggedness_rms_green_px"
                ],
                "first_crossing_bracket_green_px": None,
                "interpolated_first_crossing_green_px": None,
            }
        )
        return result

    lo = rows[first_fail_index - 1]
    hi = rows[first_fail_index]
    e0 = lo["abs_error_pct"]
    e1 = hi["abs_error_pct"]
    if e1 == e0:
        interpolated = hi["raggedness_rms_green_px"]
    else:
        interpolated = lo["raggedness_rms_green_px"] + (
            (BAR_PCT - e0)
            / (e1 - e0)
            * (
                hi["raggedness_rms_green_px"]
                - lo["raggedness_rms_green_px"]
            )
        )
    result.update(
        {
            "first_contiguous_failure": (
                f"passes at {lo['raggedness_rms_green_px']:.3f}, "
                f"fails at {hi['raggedness_rms_green_px']:.3f} green px"
            ),
            "maximum_contiguous_passing_rms_green_px": lo[
                "raggedness_rms_green_px"
            ],
            "first_crossing_bracket_green_px": [
                lo["raggedness_rms_green_px"],
                hi["raggedness_rms_green_px"],
            ],
            "interpolated_first_crossing_green_px": float(interpolated),
        }
    )
    return result


def fixture_validation(base: np.ndarray) -> dict:
    unit = c2_unit_offsets(C.FRAME_W, 21100)
    offsets = offsets_at_rms(unit, 1.23)
    silhouette, d_um = C.shifted_silhouette(base, ANGLE_DEG, offsets)
    image, levels = C.compose_subject(
        silhouette, d_um, bevel=True, glare=True
    )
    noisy = C.add_noise(image, 22100)
    actual_hash = C.array_sha256(noisy)
    fit = C.run_noisy(
        noisy,
        C.BASE_SETTINGS,
        locator="crossing",
        registration_w="inf",
    )
    return {
        "geometry_seed": 21100,
        "noise_seed": 22100,
        "expected_noisy_array_sha256": ORIGINAL_C2_FIXTURE_SHA256,
        "actual_noisy_array_sha256": actual_hash,
        "byte_exact_original_C2_plant": (
            actual_hash == ORIGINAL_C2_FIXTURE_SHA256
        ),
        "recovered_fc_cymm": fit["fc_cymm"],
        "error_pct": 100.0 * (fit["fc_cymm"] / PLANTED_FC_CYMM - 1.0),
        "levels_dn": levels,
    }


def main() -> None:
    base = C.subject_base(PLANTED_FC_CYMM, ANGLE_DEG)
    fixture = fixture_validation(base)
    if not fixture["byte_exact_original_C2_plant"]:
        raise RuntimeError("original C2 fixture hash did not reproduce")

    unit_offsets = [
        c2_unit_offsets(C.FRAME_W, GEOMETRY_SEED_BASE + index)
        for index in range(GEOMETRY_PLANTS)
    ]
    rows_by_method = {name: [] for name in METHODS}

    for rms_index, rms_green_px in enumerate(RMS_GRID_GREEN_PX):
        print(f"raggedness {rms_green_px:.3f} green px")
        plant_records_by_method = {name: [] for name in METHODS}
        for plant_index, unit in enumerate(unit_offsets):
            geometry_seed = GEOMETRY_SEED_BASE + plant_index
            offsets = offsets_at_rms(unit, rms_green_px)
            silhouette, d_um = C.shifted_silhouette(
                base, ANGLE_DEG, offsets
            )
            image, _ = C.compose_subject(
                silhouette, d_um, bevel=True, glare=True
            )
            noise_records = {name: [] for name in METHODS}
            for noise_index in range(NOISE_REALIZATIONS_PER_PLANT):
                noise_seed = (
                    NOISE_SEED_BASE + 100 * plant_index + noise_index
                )
                noisy = C.add_noise(image, noise_seed)
                for method_name, registration_w in METHODS.items():
                    try:
                        fit = C.run_noisy(
                            noisy,
                            C.BASE_SETTINGS,
                            locator="crossing",
                            registration_w=registration_w,
                        )
                        noise_records[method_name].append(
                            {
                                "noise_seed": noise_seed,
                                "fc_cymm": fit["fc_cymm"],
                                "error_pct": 100.0
                                * (
                                    fit["fc_cymm"] / PLANTED_FC_CYMM
                                    - 1.0
                                ),
                                "sigma_um": fit["sigma_um"],
                                "amp": fit["amp"],
                                "rms_resid": fit["rms_resid"],
                                "success": fit["success"],
                                "residual_smear_um": C.residual_smear_um(
                                    fit, ANGLE_DEG, offsets
                                ),
                            }
                        )
                    except C.L.EdgeFitError as exc:
                        noise_records[method_name].append(
                            {
                                "noise_seed": noise_seed,
                                "refused": str(exc),
                            }
                        )

            for method_name in METHODS:
                valid = [
                    record
                    for record in noise_records[method_name]
                    if "fc_cymm" in record
                ]
                if len(valid) == NOISE_REALIZATIONS_PER_PLANT:
                    recovered = float(
                        np.median([record["fc_cymm"] for record in valid])
                    )
                    smear = float(
                        np.median(
                            [record["residual_smear_um"] for record in valid]
                        )
                    )
                    fit_boundary = any(
                        record["fc_cymm"] >= 399.9 for record in valid
                    )
                    error = 100.0 * (
                        recovered / PLANTED_FC_CYMM - 1.0
                    )
                else:
                    recovered = smear = error = None
                    fit_boundary = False
                plant_records_by_method[method_name].append(
                    {
                        "plant_index": plant_index,
                        "geometry_seed": geometry_seed,
                        "recovered_fc_cymm": recovered,
                        "error_pct": error,
                        "residual_smear_um": smear,
                        "fit_fc_upper_boundary": fit_boundary,
                        "noise_runs": noise_records[method_name],
                    }
                )

        for method_index, method_name in enumerate(METHODS):
            summary = summarize_plants(
                plant_records_by_method[method_name],
                method_index,
                rms_index,
            )
            rows_by_method[method_name].append(
                {
                    "raggedness_rms_green_px": rms_green_px,
                    "raggedness_rms_um": rms_green_px
                    * 2.0
                    * C.L.PITCH_UM,
                    **summary,
                }
            )

    crossings = {
        method_name: crossing_summary(rows)
        for method_name, rows in rows_by_method.items()
    }
    straight_limit = crossings["straight_line"][
        "maximum_contiguous_passing_rms_green_px"
    ]
    per_column_limit = crossings["measured_per_column"][
        "maximum_contiguous_passing_rms_green_px"
    ]
    if per_column_limit is not None and (
        straight_limit is None or per_column_limit > straight_limit
    ):
        answer = (
            "The pipeline needed a better registration reference; measured "
            "per-column registration extends the contiguous 5% tolerance."
        )
    else:
        answer = (
            "The pipeline needs a straighter subject. Measured per-column "
            "self-registration does not extend the contiguous 5% tolerance."
        )

    straight_rows = rows_by_method["straight_line"]
    straight_at_001 = next(
        row for row in straight_rows if row["raggedness_rms_green_px"] == 0.01
    )
    straight_at_002 = next(
        row for row in straight_rows if row["raggedness_rms_green_px"] == 0.02
    )
    straight_at_003 = next(
        row for row in straight_rows if row["raggedness_rms_green_px"] == 0.03
    )
    straight_at_070 = next(
        row for row in straight_rows if row["raggedness_rms_green_px"] == 0.7
    )
    per_column_zero = rows_by_method["measured_per_column"][0]
    interpretation = {
        "requested_median_based_limit": (
            "0.02 green px is the largest contiguous sampled RMS that passes; "
            "the first crossing is bracketed by 0.02 and 0.03 green px. "
            "Linear interpolation gives "
            f"{crossings['straight_line']['interpolated_first_crossing_green_px']:.4f} "
            "green px and is not claimed more precisely than the bracket."
        ),
        "shape_scatter_warning": (
            f"RMS alone does not guarantee a result for an individual locus: "
            f"{straight_at_001['plant_pass_count']}/{GEOMETRY_PLANTS} plants "
            f"pass at 0.01, "
            f"{straight_at_002['plant_pass_count']}/{GEOMETRY_PLANTS} at "
            f"0.02, and "
            f"{straight_at_003['plant_pass_count']}/{GEOMETRY_PLANTS} at "
            f"0.03 green px."
        ),
        "isolated_reentry_warning": (
            "The apparent pass at 0.7 green px is not a tolerance extension. "
            f"It occurs after a long failing interval, only "
            f"{straight_at_070['plant_pass_count']}/{GEOMETRY_PLANTS} plants "
            f"pass, its "
            f"16th-84th error range is "
            f"{straight_at_070['error_p16_pct']:.2f}% to "
            f"{straight_at_070['error_p84_pct']:.2f}%, and it is bias "
            "cancellation between an initially high fitted cutoff and later "
            "raggedness smear."
        ),
        "per_column_result": (
            "Per-column registration fails before raggedness is introduced: "
            f"at 0.00 green px it leaves only "
            f"{per_column_zero['residual_smear_um']:.3f} um median residual "
            f"smear but biases fc by {per_column_zero['error_pct']:+.3f}%. "
            "The failure is self-registration sharpening, not untracked "
            "locus smear."
        ),
    }

    bracket_indices = set()
    for crossing in crossings.values():
        bracket = crossing["first_crossing_bracket_green_px"]
        if bracket:
            for value in bracket:
                bracket_indices.add(RMS_GRID_GREEN_PX.index(value))
    stability_rows = []
    for method_name, rows in rows_by_method.items():
        for index in sorted(bracket_indices):
            row = rows[index]
            stability_rows.append(
                {
                    "method": method_name,
                    "raggedness_rms_green_px": row[
                        "raggedness_rms_green_px"
                    ],
                    "split_half_delta_pct_points": row[
                        "split_half_delta_pct_points"
                    ],
                    "bootstrap_95pct_ci": row[
                        "median_error_bootstrap_95pct_ci"
                    ],
                }
            )

    payload = {
        "experiment": "M128-razor-ladder",
        "question": "Maximum C2 locus-raggedness tolerance",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Synthetic C2 plant only. C3-C9 were not run and no real frame "
            "was opened."
        ),
        "instrument": {
            "commission_path": str(HERE / "commission.py"),
            "commission_sha256": sha256_file(HERE / "commission.py"),
            "sfr_run_sha256": sha256_file(HERE / "sfr_run.py"),
            "m88lib_sha256": sha256_file(C.M88_LIB),
            "locator": "line_from_crossings",
            "fit_route": "m88lib.fit_fc with the driver/default fc_init=90",
        },
        "plant": {
            "planted_fc_cymm": PLANTED_FC_CYMM,
            "angle_deg": ANGLE_DEG,
            "settings": C.BASE_SETTINGS,
            "bevel_and_glare": {
                "ridge_peak_dn": C.RIDGE_PEAK_DN,
                "ridge_offset_um": C.RIDGE_OFFSET_UM,
                "ridge_sigma_um": C.RIDGE_SIGMA_UM,
                "glare_near_dn": C.GLARE_NEAR_DN,
                "glare_far_um": C.GLARE_FAR_UM,
                "glare_tau_um": C.GLARE_TAU_UM,
            },
            "raggedness_model": (
                "Original C2 model: Gaussian innovations -> cumulative "
                "random walk -> 17-sensor-column reflected moving average -> "
                "linear detrend -> exact RMS scaling."
            ),
            "fixture_validation": fixture,
        },
        "sampling": {
            "rms_grid_green_px": RMS_GRID_GREEN_PX,
            "geometry_plants_per_step": GEOMETRY_PLANTS,
            "noise_realizations_per_plant": (
                NOISE_REALIZATIONS_PER_PLANT
            ),
            "fits_per_method_per_step": (
                GEOMETRY_PLANTS * NOISE_REALIZATIONS_PER_PLANT
            ),
            "paired_design": (
                "At each RMS, each noisy array is shared by both methods. "
                "Across RMS values, the same normalized displacement shapes "
                "and RNG seeds are reused at the requested new amplitude."
            ),
            "geometry_seeds": [
                GEOMETRY_SEED_BASE + index
                for index in range(GEOMETRY_PLANTS)
            ],
            "noise_seed_formula": (
                f"{NOISE_SEED_BASE} + 100*plant_index + noise_index"
            ),
            "aggregation": (
                f"Median of {NOISE_REALIZATIONS_PER_PLANT} noise fits per "
                f"locus plant, then median across {GEOMETRY_PLANTS} "
                "independent locus plants."
            ),
            "scatter": (
                "16th-84th percentiles and sample SD across the independent "
                "plant medians; bootstrap 95% CI for the median; split-half "
                "delta."
            ),
        },
        "methods": {
            "straight_line": {
                "registration_W_green_columns": "inf",
                "description": (
                    "One robust line from line_from_crossings; planted locus "
                    "wander remains as ESF smear."
                ),
                "table": rows_by_method["straight_line"],
                "crossing": crossings["straight_line"],
            },
            "measured_per_column": {
                "registration_W_green_columns": 1,
                "description": (
                    "Each column is registered on its own measured 50% "
                    "crossing; residual smear is crossing-estimation error, "
                    "while same-column noise correlation can sharpen."
                ),
                "table": rows_by_method["measured_per_column"],
                "crossing": crossings["measured_per_column"],
            },
        },
        "stability_at_crossings": stability_rows,
        "interpretation": interpretation,
        "answer_c": answer,
        "reproduction_commands": [
            "$env:PYTHONIOENCODING='utf-8'",
            "$env:PYTHONDONTWRITEBYTECODE='1'",
            (
                "Set-Location "
                "'C:\\dev\\blog\\death-of-software\\projects\\strehl\\"
                "experiments\\M128-razor-ladder'"
            ),
            "python -m py_compile src\\ragged_tolerance.py",
            "python -B src\\ragged_tolerance.py",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            C.json_ready(payload),
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print("\nSTRAIGHT-LINE REGISTRATION")
    print(" RMS(gpx)   fc(cy/mm)    error%       p16       p84  pass")
    for row in rows_by_method["straight_line"]:
        print(
            f" {row['raggedness_rms_green_px']:8.3f}"
            f"  {row['recovered_fc_cymm']:10.3f}"
            f"  {row['error_pct']:8.3f}"
            f"  {row['error_p16_pct']:8.3f}"
            f"  {row['error_p84_pct']:8.3f}"
            f"  {str(row['central_bar_pass']):>5}"
        )
    print("\nMEASURED PER-COLUMN REGISTRATION")
    print(" RMS(gpx)   fc(cy/mm)    error%       p16       p84  pass")
    for row in rows_by_method["measured_per_column"]:
        print(
            f" {row['raggedness_rms_green_px']:8.3f}"
            f"  {row['recovered_fc_cymm']:10.3f}"
            f"  {row['error_pct']:8.3f}"
            f"  {row['error_p16_pct']:8.3f}"
            f"  {row['error_p84_pct']:8.3f}"
            f"  {str(row['central_bar_pass']):>5}"
        )
    print(f"\nstraight crossing: {crossings['straight_line']}")
    print(f"per-column crossing: {crossings['measured_per_column']}")
    print(f"ANSWER: {answer}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
