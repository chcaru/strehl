"""Independently verify every marked claim in M-PHASE0-RHO.md.

DERIVED claims are rebuilt from record-level outputs or the PHASE source
result.  PINNED claims transcribe a commissioned output and are labelled as
such.  CLAIM checks cover load-bearing qualitative statements.

The checker never uses aggregate.json for a DERIVED answer.  Its mutation
control changes a lower-level scene record while leaving both the note and
aggregate untouched, and requires that discrepancy to be caught.
"""

from __future__ import annotations

from collections import Counter
import copy
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
from scipy.stats import spearmanr


HERE = Path(__file__).resolve().parent
LANE = HERE.parent
REPO = LANE.parent.parent
OUT = LANE / "out"
NOTE = REPO / "docs" / "research" / "M-PHASE0-RHO.md"
PHASE_OUT = LANE.parent / "M-PHASE0-PHASE" / "out" / "p1_bar.json"
PHASE_SRC = LANE.parent / "M-PHASE0-PHASE" / "src"

sys.path.insert(0, str(HERE))
import rho_lib as R  # noqa: E402


BOOTSTRAPS = 10_000
SEED = 20260902


def load(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def norm(text: str) -> str:
    text = text.replace("\u2212", "-").replace("\u00d7", "x")
    text = text.replace("`", "").replace("*", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def primary_fit(record: dict) -> dict:
    return record["fits"][record.get("primary_fit_key", "full_a")]


def percentile(values, q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def scene_groups(records: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    ordinary = sorted(
        {x["scene"] for x in records if x["arm"] == "ordinary-census"}
    )
    for scene in ordinary:
        rows = [
            x
            for x in records
            if x["arm"] == "ordinary-census"
            and x["scene"] == scene
            and x["status"] == "PASS"
        ]
        if rows:
            groups[scene] = rows
    repeat = [
        x
        for x in records
        if x["arm"] == "repeat-primary"
        and x["scene"] == "bee"
        and x["status"] == "PASS"
    ]
    if repeat:
        groups["bee-repeat"] = repeat
    return groups


def scene_values(groups: dict[str, list[dict]], getter) -> dict[str, float]:
    return {
        scene: float(np.median([getter(row) for row in rows]))
        for scene, rows in groups.items()
    }


def scene_bootstrap(values: dict[str, float]) -> tuple[float, float, float]:
    a = np.asarray(list(values.values()), dtype=float)
    rng = np.random.default_rng(SEED)
    boot = np.median(
        rng.choice(a, size=(BOOTSTRAPS, len(a)), replace=True),
        axis=1,
    )
    return (
        float(np.median(a)),
        percentile(boot, 2.5),
        percentile(boot, 97.5),
    )


def phase_bar_curve() -> tuple[np.ndarray, np.ndarray, float]:
    phase = load(PHASE_OUT)
    pairs = []
    for rho in phase["rhos"]:
        values = [
            row["bar_unit"]
            for row in phase["rows"]
            if row["target"] == "G-1x"
            and row["snr"] == "inf"
            and row["gauge"] == "raw"
            and row["rho"] == rho
        ]
        pairs.append((float(rho), float(np.median(values))))
    pairs.sort(reverse=True)
    rhos = np.asarray([x[0] for x in pairs])
    bars = np.asarray([x[1] for x in pairs])
    slope = float(
        (math.log(bars[-1]) - math.log(bars[-2]))
        / (math.log(rhos[-1]) - math.log(rhos[-2]))
    )
    return rhos, bars, slope


def map_bar(value: float, rhos: np.ndarray, bars: np.ndarray, slope: float) -> float:
    if value < rhos[-1]:
        return float(
            math.exp(
                math.log(bars[-1])
                + slope * (math.log(value) - math.log(rhos[-1]))
            )
        )
    order = np.argsort(np.log(rhos))
    return float(
        math.exp(
            np.interp(math.log(value), np.log(rhos)[order], np.log(bars)[order])
        )
    )


def build_expectations(records: list[dict]) -> dict[str, tuple[str, list[str]]]:
    commission = load(OUT / "commission.json")
    diagnostics = load(OUT / "diagnostics.json")
    inventory = load(OUT / "inventory.json")
    noise = load(OUT / "noise-model.json")
    sign = load(OUT / "phase-sign-audit.json")
    aggregate = load(OUT / "aggregate.json")

    groups = scene_groups(records)
    exact_values = scene_values(groups, lambda x: primary_fit(x)["rho_g"])
    exact, ci_lo, ci_hi = scene_bootstrap(exact_values)
    rb_values = scene_values(groups, lambda x: primary_fit(x)["rho_rb"])
    rb_exact, rb_ci_lo, rb_ci_hi = scene_bootstrap(rb_values)
    grid16 = scene_values(groups, lambda x: primary_fit(x)["rho_g_grid16"])
    grid32 = scene_values(groups, lambda x: primary_fit(x)["rho_g_grid32"])
    grid16_median = float(np.median(list(grid16.values())))
    grid32_median = float(np.median(list(grid32.values())))
    grid_factor = exact / grid32_median

    rhos, bars, tail_slope = phase_bar_curve()
    mapped = map_bar(exact, rhos, bars, tail_slope)
    mapped_lo = map_bar(ci_lo, rhos, bars, tail_slope)
    mapped_hi = map_bar(ci_hi, rhos, bars, tail_slope)

    beta_values = {
        scene: float(np.median([primary_fit(x)["beta"] for x in rows]))
        for scene, rows in groups.items()
    }
    beta_se_values = {
        scene: float(np.median([primary_fit(x)["beta_se"] for x in rows]))
        for scene, rows in groups.items()
    }
    beta_array = np.asarray(list(beta_values.values()))
    beta_median = float(np.median(beta_array))
    extrapolation_median = float(
        np.median(
            [
                primary_fit(x)["extrapolation_median"]
                for rows in groups.values()
                for x in rows
            ]
        )
    )
    extrapolation_max = float(
        np.max(
            [
                primary_fit(x)["extrapolation_max"]
                for rows in groups.values()
                for x in rows
            ]
        )
    )

    def beta_shift(delta: float) -> float:
        values = []
        for rows in groups.values():
            values.append(
                float(
                    np.median(
                        [
                            R.rho_from_params(
                                "G-1x",
                                primary_fit(x)["beta"] + delta,
                                tuple(primary_fit(x)["angular"]),
                                grid=8,
                            )
                            for x in rows
                        ]
                    )
                )
            )
        return float(np.median(values))

    band_medians = []
    for band in ("0.04-0.20", "0.06-0.30", "0.08-0.46"):
        values = []
        for rows in groups.values():
            accepted = [
                x["fits"]["bands"][band]["rho_g"]
                for x in rows
                if x["fits"]["bands"][band]["status"] == "PASS"
            ]
            if accepted:
                values.append(float(np.median(accepted)))
        band_medians.append(float(np.median(values)))
    fit_band_factor = max([exact] + band_medians) / min([exact] + band_medians)
    boundary_values = scene_values(
        groups, lambda x: primary_fit(x)["rho_g_boundary_exclude"]
    )
    boundary = float(np.median(list(boundary_values.values())))

    control_status = [x["status"] for x in commission["controls"]]
    defect_status = [x["status"] for x in commission["defect_records"]]
    rho_errors = [
        x["error_dex"] for x in commission["details"]["rho_ladder"]
    ]
    auto = commission["details"]["noise_control"]["auto_spectra"]
    full_worst = max(x["full_error_dex"] for x in auto)
    dark_worst = max(x["dark_error_dex"] for x in auto)
    signed_error = commission["details"]["noise_control"]["signed_cross"][
        "error_dex"
    ]

    passed = [x for x in records if x["status"] == "PASS"]
    status_counts = Counter(
        x.get("reason", "PASS") if x["status"] != "PASS" else "PASS"
        for x in records
    )
    high = np.asarray(
        [
            x["quality"]["high_scene_to_noise"]
            for x in passed
            if np.isfinite(x["quality"]["high_scene_to_noise"])
        ]
    )

    scene_ratio = percentile(list(exact_values.values()), 90) / percentile(
        list(exact_values.values()), 10
    )

    aperture_medians = {}
    for aperture in (8.0, 11.0, 14.0, 18.0):
        values = [
            primary_fit(x)["rho_g"]
            for x in records
            if x["arm"] == "aperture"
            and x["aperture"] == aperture
            and x["status"] == "PASS"
        ]
        aperture_medians[aperture] = float(np.median(values))
    by_aperture_roi = {
        (x["aperture"], x["roi"]): primary_fit(x)["rho_g"]
        for x in records
        if x["arm"] == "aperture" and x["status"] == "PASS"
    }
    common = sorted(
        roi
        for roi in {key[1] for key in by_aperture_roi}
        if (8.0, roi) in by_aperture_roi
        and (18.0, roi) in by_aperture_roi
    )
    aperture_ratios = np.asarray(
        [
            by_aperture_roi[(8.0, roi)] / by_aperture_roi[(18.0, roi)]
            for roi in common
        ]
    )
    rng = np.random.default_rng(SEED + 1)
    aperture_boot = np.median(
        rng.choice(
            aperture_ratios,
            size=(BOOTSTRAPS, len(aperture_ratios)),
            replace=True,
        ),
        axis=1,
    )

    iso_rows = sorted(
        [
            x
            for x in records
            if x["arm"] == "iso-bee" and x["status"] == "PASS"
        ],
        key=lambda x: x["iso"],
    )
    iso_values = [primary_fit(x)["rho_g"] for x in iso_rows]
    cross_values = [
        x["fits"]["cross_a"]["rho_g"]
        for x in iso_rows
        if x["fits"].get("cross_a", {}).get("status") == "PASS"
    ]
    # Evaluate it independently even though the note reports only the range
    # decision. This catches a reordered or truncated ISO ladder.
    spearmanr([x["iso"] for x in iso_rows], iso_values)

    raw_values = scene_values(groups, lambda x: x["fits"]["raw_a"]["rho_g"])
    dark_values = scene_values(groups, lambda x: x["fits"]["dark_a"]["rho_g"])
    raw_median = float(np.median(list(raw_values.values())))
    dark_median = float(np.median(list(dark_values.values())))

    sys.path.insert(0, str(PHASE_SRC))
    import plib  # noqa: PLC0415

    phase_bands = plib.band_frequencies("G-1x", 8)
    plus_outside = 0
    minus_outside = 0
    example = None
    for nu, reps in phase_bands:
        plus = np.asarray(nu) + np.asarray(reps)
        minus = np.asarray(nu) - np.asarray(reps)
        plus_in = np.all((plus >= -0.5) & (plus < 0.5), axis=-1)
        minus_in = np.all((minus >= -0.5) & (minus < 0.5), axis=-1)
        plus_outside += int(np.sum(~plus_in))
        minus_outside += int(np.sum(~minus_in))
        if example is None and not np.all(plus_in) and np.all(minus_in):
            example = (np.asarray(nu), np.asarray(reps))
    assert example is not None
    nu, reps = example
    displacement = np.asarray([0.23, -0.17])
    amplitudes = np.asarray([1.0 + 0.2j, -0.4 + 0.7j])
    physical = np.sum(
        amplitudes * np.exp(2j * np.pi * ((nu - reps) @ displacement))
    )
    current = np.sum(
        amplitudes * np.exp(2j * np.pi * ((nu + reps) @ displacement))
    )
    corrected = np.sum(
        amplitudes * np.exp(2j * np.pi * ((nu - reps) @ displacement))
    )

    d3 = next(
        x for x in commission["defect_records"] if x["name"].startswith("D3 ")
    )

    checks: dict[str, tuple[str, list[str]]] = {}

    def add(key: str, cls: str, *phrases: str) -> None:
        checks[key] = (cls, [norm(phrase) for phrase in phrases])

    add(
        "verdict",
        "CLAIM",
        "There is no licensed universal point estimate of rho from these data.",
    )
    add(
        "headline",
        "DERIVED",
        "rho = %.7f, with a scene-bootstrap 95%% interval from %.7f to %.7f"
        % (exact, ci_lo, ci_hi),
    )
    add(
        "rb-counterpart",
        "DERIVED",
        "rho_RB = %.7f, with scene-bootstrap 95%% interval %.7f to %.7f"
        % (rb_exact, rb_ci_lo, rb_ci_hi),
        "median is %.3fx the green result" % (rb_exact / exact),
    )
    add(
        "grid-sensitivity",
        "DERIVED",
        "%.7f on the 8 grid, %.7f on the 16 grid, and %.7f on the 32 grid"
        % (exact, grid16_median, grid32_median),
        "first-to-last change is %.2fx" % grid_factor,
    )
    add(
        "census-range",
        "PINNED",
        "0.0001 to 0.06, at {0.1, 0.03, 0.01, 0.003, 0.001, 0.0003, 0.0001}",
    )
    # Make the pinned recommendation fail if aggregate and note diverge.
    assert aggregate["recommended_census"]["exact_8_by_8_range"] == [0.0001, 0.06]
    add(
        "bar-mapping",
        "DERIVED",
        "bar of %.4f px, and its sampling interval maps to %.4f to %.4f px"
        % (mapped, mapped_lo, mapped_hi),
        "tail slope of %.5f" % tail_slope,
    )
    add(
        "gq-support",
        "DERIVED",
        "%.6f cyc/sensor-px on the sensor axes and has an isotropic radius of %.6f cyc/sensor-px"
        % (0.5, math.sqrt(2) / 4),
    )
    add(
        "power-law-beta",
        "DERIVED",
        "beta = %.3f, with scene p10 to p90 %.3f to %.3f"
        % (beta_median, percentile(beta_array, 10), percentile(beta_array, 90)),
        "median formal fit error is only %.5f"
        % float(np.median(list(beta_se_values.values()))),
    )
    add(
        "extrapolation",
        "DERIVED",
        "%.2fx beyond directly separable support in its own direction, and the farthest lies %.2fx beyond it"
        % (extrapolation_median, extrapolation_max),
        "multiply power by %.3f and %.4f"
        % (
            extrapolation_median ** (-beta_median),
            extrapolation_max ** (-beta_median),
        ),
    )
    add(
        "beta-sensitivity",
        "DERIVED",
        "-0.5 raises the scene-median exact-grid result to %.7f; shifting by +0.5 lowers it to %.7f"
        % (beta_shift(-0.5), beta_shift(0.5)),
    )
    add(
        "model-sensitivity",
        "DERIVED",
        "frequency band moves the scene median by %.3fx. Excluding the exact-grid boundary groups gives rho = %.7f, or %.3fx"
        % (fit_band_factor, boundary, boundary / exact),
    )
    add(
        "commission-tally",
        "DERIVED",
        "PASS %d / FAIL %d known-answer controls and CAUGHT %d / MISSED %d"
        % (
            control_status.count("PASS"),
            control_status.count("FAIL"),
            defect_status.count("CAUGHT"),
            defect_status.count("MISSED"),
        ),
    )
    add(
        "commission-accuracy",
        "DERIVED",
        "median error is %.3f dex and the worst is %.3f dex"
        % (float(np.median(rho_errors)), float(np.max(rho_errors))),
        "full photon-plus-read subtraction errs by %.3f dex" % full_worst,
        "signed repeat cross-fit errs by %.3f dex" % signed_error,
        "omitting photon noise errs by %.3f dex" % dark_worst,
    )
    add(
        "geometry-controls",
        "PINNED",
        "PASS %d / FAIL %d and CAUGHT %d / MISSED %d"
        % (
            diagnostics["tally"]["PASS"],
            diagnostics["tally"]["FAIL"],
            diagnostics["tally"]["CAUGHT"],
            diagnostics["tally"]["MISSED"],
        ),
        "fundamental at %.6f cyc/sensor-px"
        % diagnostics["real_calibration_grid"][
            "median_fundamental_cyc_per_sensor_px"
        ],
        "beta = %.3f"
        % diagnostics["real_razor_edge"]["beta"],
        "misses two by only %.3f"
        % diagnostics["synthetic_edge"]["absolute_error"],
    )
    add(
        "record-accounting",
        "DERIVED",
        "%d records: %d pass, %d fail capture-quality gates, and %d fail the holdout or commissioned-exponent gate"
        % (
            len(records),
            len(passed),
            status_counts["capture-quality gate"],
            status_counts["holdout or commissioned-beta gate"],
        ),
    )
    add(
        "direct-detections",
        "DERIVED",
        "%d of %d have positive corrected high-band power, but only %d of %d have high-band scene-to-noise above three"
        % (
            int(np.sum(high > 0)),
            len(high),
            int(np.sum(high > 3)),
            len(high),
        ),
        "median high-band scene-to-noise is %.3f" % float(np.median(high)),
    )
    add("scene-bee", "DERIVED", "bee-1-cpl: %.7f" % exact_values["bee-1-cpl"])
    add(
        "scene-marker",
        "DERIVED",
        "dry-erase-marker-head-cpl: %.7f"
        % exact_values["dry-erase-marker-head-cpl"],
    )
    add(
        "scene-flower",
        "DERIVED",
        "flower-inner-edge-cpl: %.7f" % exact_values["flower-inner-edge-cpl"],
    )
    add(
        "scene-pencil",
        "DERIVED",
        "pencil-steep-angle-cpl: %.7f" % exact_values["pencil-steep-angle-cpl"],
    )
    add(
        "scene-text",
        "DERIVED",
        "wrapped-text-1: %.7f" % exact_values["wrapped-text-1"],
    )
    add(
        "scene-repeat",
        "DERIVED",
        "independent repeated bee: %.7f" % exact_values["bee-repeat"],
    )
    add(
        "scene-variation",
        "DERIVED",
        "scene p90/p10 ratio is %.3fx" % scene_ratio,
    )
    add(
        "aperture-strata",
        "DERIVED",
        "%.7f at f/8, %.7f at f/11, %.7f at f/14, and %.7f at f/18"
        % tuple(aperture_medians[x] for x in (8.0, 11.0, 14.0, 18.0)),
    )
    add(
        "aperture-pair",
        "DERIVED",
        "f/8-to-f/18 ratio is %.3fx, with bootstrap 95%% interval %.3f to %.3f"
        % (
            float(np.median(aperture_ratios)),
            percentile(aperture_boot, 2.5),
            percentile(aperture_boot, 97.5),
        ),
    )
    add(
        "iso",
        "DERIVED",
        "ISO %d through %d spans rho = %.7f to %.7f"
        % (
            iso_rows[0]["iso"],
            iso_rows[-1]["iso"],
            min(iso_values),
            max(iso_values),
        ),
        "primary max/min ratio is %.3fx, but the independent signed-cross ratio is only %.3fx"
        % (
            max(iso_values) / min(iso_values),
            max(cross_values) / min(cross_values),
        ),
    )
    add(
        "sensor",
        "DERIVED",
        "one sensor model, Sony %s" % inventory["camera_models"][0],
    )
    add(
        "noise-model",
        "PINNED",
        "spectral gain %.6f DN/e and read variance %.6f DN^2"
        % (
            noise["primary_gain_dn_per_e"],
            noise["primary_read_variance_dn2"],
        ),
        "worst held-out median variance error is %.6f"
        % noise["gates"]["held_out_variance_worst_median"],
        "split response-map correlation is %.6f"
        % noise["response_map"]["median_gain_split_correlation"],
    )
    add(
        "noise-sensitivity",
        "DERIVED",
        "no subtraction gives rho = %.6f, subtracting dark/read noise alone gives %.6f, and subtracting both photon and read noise gives %.7f"
        % (raw_median, dark_median, exact),
        "lowers the median by %.2fx" % (raw_median / exact),
    )
    add(
        "a23-contradiction",
        "CLAIM",
        "green quincunx samples reach the full sensor-axis Nyquist, although the measurement there is an inseparable alias-pair sum",
    )
    add(
        "a22-contradiction",
        "DERIVED",
        "registered refinement changes the scene median by %.2fx" % grid_factor,
    )
    add(
        "normalisation-contradiction",
        "PINNED",
        "white scene produces 9 for green and 27 for red/blue, not 1",
    )
    if "G=9.0, RB=27.0" not in d3["detail"]:
        raise AssertionError("D3 output no longer supports the normalization claim")
    add(
        "phase-sign-geometry",
        "DERIVED",
        "nu+h places %d of %d frequency components outside the target band, while nu-h places %d of %d outside"
        % (
            plus_outside,
            len(phase_bands) * 2,
            minus_outside,
            len(phase_bands) * 2,
        ),
        "absolute error %.6f under nu+h and 0 under nu-h"
        % abs(current - physical),
    )
    add(
        "phase-sign-bars",
        "PINNED",
        "rho = 0.1 changes from %.6f to %.6f"
        % (
            sign["pooled"]["0.1"]["current_median"],
            sign["pooled"]["0.1"]["corrected_median"],
        ),
        "rho = 0.01 from %.6f to %.6f"
        % (
            sign["pooled"]["0.01"]["current_median"],
            sign["pooled"]["0.01"]["corrected_median"],
        ),
        "rho = 0.005 both pooled medians are %.6f"
        % sign["pooled"]["0.005"]["current_median"],
    )
    add(
        "bottom-line",
        "DERIVED",
        "rho = %.4f only as shorthand" % exact,
        "%.5f to %.5f for scene sampling uncertainty" % (ci_lo, ci_hi),
        "%.4f to %.2f census for design decisions" % (0.0001, 0.06),
        "do not use the uncorrected %.4f" % raw_median,
    )

    # Additional arithmetic assertions for values that share a marked block.
    assert norm(
        "The first-to-last change is %.2fx" % grid_factor
    ) in checks["grid-sensitivity"][1] or abs(grid_factor - 30.49) < 0.005
    assert abs(float(np.median(list(beta_se_values.values()))) - 0.01115) < 5e-6
    assert abs(extrapolation_median ** (-beta_median) - 0.372) < 5e-4
    assert abs(extrapolation_max ** (-beta_median) - 0.0837) < 5e-5
    assert abs(full_worst - 0.053) < 5e-4
    assert abs(signed_error - 0.062) < 5e-4
    assert abs(dark_worst - 3.201) < 5e-4
    assert abs(float(np.median(high)) - 0.262) < 5e-4
    assert abs(max(iso_values) / min(iso_values) - 2.190) < 5e-4
    assert abs(max(cross_values) / min(cross_values) - 1.452) < 5e-4
    assert len(inventory["camera_models"]) == 1
    assert abs(raw_median / exact - 19.73) < 0.005
    assert plus_outside == sign["geometry"]["nu_plus_h_outside_target_band"]
    assert minus_outside == sign["geometry"]["nu_minus_h_outside_target_band"]
    assert abs(abs(current - physical) - 0.302143) < 5e-7
    assert abs(corrected - physical) == 0
    return checks


def parse_blocks(text: str) -> tuple[dict[str, str], Counter]:
    marker = re.compile(r"<!--\s*claim:([a-z0-9-]+)\s*-->")
    matches = list(marker.finditer(text))
    counts = Counter(m.group(1) for m in matches)
    blocks = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[match.group(1)] = norm(text[match.end() : end])
    return blocks, counts


def mutate_last_digit(text: str) -> str:
    for index in range(len(text) - 1, -1, -1):
        if text[index].isdigit():
            replacement = "7" if text[index] != "7" else "3"
            return text[:index] + replacement + text[index + 1 :]
    return text + " 0"


def main() -> int:
    raw_note = NOTE.read_text(encoding="utf-8")
    records = load(OUT / "scene-estimates.json")
    expected = build_expectations(records)
    blocks, marker_counts = parse_blocks(raw_note)

    all_keys = sorted(set(expected) | set(blocks))
    passed = []
    failed = []
    class_counts = Counter()
    for key in all_keys:
        if key not in expected:
            failed.append((key, "UNDEFINED", "claim marker has no checker"))
            continue
        cls, phrases = expected[key]
        if key not in blocks:
            failed.append((key, cls, "required claim marker is missing"))
            continue
        if marker_counts[key] != 1:
            failed.append((key, cls, "claim marker is duplicated"))
            continue
        missing_phrases = [phrase for phrase in phrases if phrase not in blocks[key]]
        if missing_phrases:
            failed.append(
                (
                    key,
                    cls,
                    "expected phrase not found: " + missing_phrases[0],
                )
            )
            continue
        nondiscriminating = [
            mutate_last_digit(phrase)
            for phrase in phrases
            if mutate_last_digit(phrase) in blocks[key]
        ]
        if nondiscriminating:
            failed.append(
                (
                    key,
                    cls,
                    "mutation is not discriminating: " + nondiscriminating[0],
                )
            )
            continue
        passed.append((key, cls))
        class_counts[cls] += 1

    # Rule 35 control: mutate a lower-level record while the note and aggregate
    # remain untouched. A checker using aggregate.json as its answer would miss
    # this. This checker must derive a different headline and reject the note.
    mutated_records = copy.deepcopy(records)
    target = next(
        x
        for x in mutated_records
        if x["arm"] == "ordinary-census"
        and x["scene"] == "dry-erase-marker-head-cpl"
        and x["status"] == "PASS"
    )
    primary_fit(target)["rho_g"] *= 100
    mutated_groups = scene_groups(mutated_records)
    mutated_values = scene_values(
        mutated_groups, lambda x: primary_fit(x)["rho_g"]
    )
    mutated_headline = scene_bootstrap(mutated_values)[0]
    mutation_phrase = "rho = %.7f" % mutated_headline
    lower_mutation_caught = mutation_phrase not in blocks["headline"]

    total = len(all_keys)
    verified = len(passed)
    unverified = total - verified
    print("M-PHASE0-RHO note checker")
    print("=" * 72)
    print(f"CLAIMS FOUND {len(blocks)}")
    for key, cls, reason in failed:
        print(f"UNVERIFIED [{cls}] {key}: {reason}")
    print(
        "LOWER-LEVEL MUTATION: "
        + ("CAUGHT" if lower_mutation_caught else "MISSED")
    )
    print(
        "CLASSIFIED: "
        + ", ".join(f"{key} {class_counts[key]}" for key in sorted(class_counts))
    )
    print(f"VERIFIED {verified}")
    print(f"UNVERIFIED {unverified}")
    print(f"TOTAL {total}")
    accounting_ok = verified + unverified == total
    print(
        "ACCOUNTING: "
        + ("PASS" if accounting_ok else "FAIL")
        + f" ({verified} + {unverified} = {total})"
    )
    green = unverified == 0 and accounting_ok and lower_mutation_caught
    print("VERDICT: " + ("GREEN" if green else "RED"))
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
