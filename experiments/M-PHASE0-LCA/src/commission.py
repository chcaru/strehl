"""Commission the M-PHASE0-LCA instrument before real focus measurement.

Every control has an explicit mutation.  Success requires the untreated arm to
go green and every mutation to go red.  The fixed response table and predicate
are committed data that this estimator never generated.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from lca_lib import (
    CHANNELS,
    FIXTURES,
    LANE,
    OUT,
    REPO,
    SITE,
    array_sha256,
    decode_visible,
    environment_record,
    file_sha256,
    offset_values,
    peak_fit,
    phase_shift,
    read_json,
    split_cfa,
    write_json,
)


GRID = Path(
    r"D:\personal\macro\requests\30-calibration-grid"
    r"\calibration-grid-1-sw4-cpl"
)


def fixture_fits(
    fixture: dict,
    *,
    mode: str = "log",
    vertex_sign: float = 1.0,
    coordinate_scale: float = 1.0,
) -> dict:
    return {
        channel: peak_fit(
            np.asarray(fixture["responses"][channel], dtype=np.float64),
            baseline_override=float(fixture["baselines"][channel]),
            mode=mode,
            vertex_sign=vertex_sign,
            coordinate_scale=coordinate_scale,
        )
        for channel in CHANNELS
    }


def fixture_reading(fits: dict) -> dict:
    delta_r, delta_b, delta_null = offset_values(fits)
    return {
        "peaks": {
            channel: float(fits[channel].peak[0]) for channel in CHANNELS
        },
        "valid": {
            channel: bool(fits[channel].valid[0]) for channel in CHANNELS
        },
        "offsets": {
            "delta_r": float(delta_r[0]),
            "delta_b": float(delta_b[0]),
            "delta_null": float(delta_null[0]),
        },
    }


def predicate_pass(reading: dict, predicate: dict) -> bool:
    tolerance = float(predicate["absolute_tolerance_frames"])
    fields = [
        abs(reading["peaks"][channel] - predicate["peaks"][channel])
        for channel in CHANNELS
    ]
    fields += [
        abs(reading["offsets"][name] - predicate["offsets"][name])
        for name in ("delta_r", "delta_b", "delta_null")
    ]
    return (
        all(reading["valid"].values())
        and all(np.isfinite(fields))
        and max(fields) <= tolerance
    )


def record_control(
    name: str,
    green: bool,
    reading: dict,
    plants: list[tuple[str, bool, dict]],
) -> dict:
    return {
        "name": name,
        "green": bool(green),
        "reading": reading,
        "plants": [
            {"name": plant_name, "red": bool(red), "reading": plant_reading}
            for plant_name, red, plant_reading in plants
        ],
    }


def fixed_controls() -> list[dict]:
    fixture = read_json(FIXTURES / "fixed-curves.json")
    predicate = read_json(FIXTURES / "fixed-predicate.json")
    actual = fixture_reading(fixture_fits(fixture))

    linear = fixture_reading(fixture_fits(fixture, mode="linear"))
    control_external = record_control(
        "C1_fixed_external_peak_predicate",
        predicate_pass(actual, predicate),
        actual,
        [
            (
                "P1_linear_domain_instead_of_log",
                not predicate_pass(linear, predicate),
                linear,
            )
        ],
    )

    reversed_vertex = fixture_reading(
        fixture_fits(fixture, vertex_sign=-1.0)
    )
    doubled_units = fixture_reading(
        fixture_fits(fixture, coordinate_scale=2.0)
    )
    control_sign = record_control(
        "C2_signed_offsets_and_frame_units",
        predicate_pass(actual, predicate),
        actual,
        [
            (
                "P2_inverted_vertex_sign",
                not predicate_pass(reversed_vertex, predicate),
                reversed_vertex,
            ),
            (
                "P3_doubled_frame_coordinate",
                not predicate_pass(doubled_units, predicate),
                doubled_units,
            ),
        ],
    )

    null_green = abs(actual["offsets"]["delta_null"]) < 0.01
    shifted = dict(fixture)
    shifted["responses"] = dict(fixture["responses"])
    g2 = np.asarray(fixture["responses"]["G2"], dtype=np.float64)
    base = float(fixture["baselines"]["G2"])
    shifted["responses"]["G2"] = np.r_[base, g2[:-1]].tolist()
    shifted_reading = fixture_reading(fixture_fits(shifted))
    null_plant_red = abs(shifted_reading["offsets"]["delta_null"]) >= 0.01
    control_null = record_control(
        "C5_green_pair_null_sensitivity",
        null_green,
        {"delta_null": actual["offsets"]["delta_null"]},
        [
            (
                "P6_shift_G2_by_one_frame",
                null_plant_red,
                {"delta_null": shifted_reading["offsets"]["delta_null"]},
            )
        ],
    )

    offset_input = read_json(FIXTURES / "fixed-offset-input.json")
    offset_predicate = read_json(FIXTURES / "fixed-offset-predicate.json")
    fixed_peaks = {
        channel: np.asarray([offset_input["peaks"][channel]], dtype=np.float64)
        for channel in CHANNELS
    }

    class FixedFit:
        def __init__(self, peak: np.ndarray) -> None:
            self.peak = peak

    fixed_fits = {
        channel: FixedFit(peak) for channel, peak in fixed_peaks.items()
    }
    delta_r, delta_b, delta_null = offset_values(fixed_fits)
    averaged_reading = {
        "delta_r": float(delta_r[0]),
        "delta_b": float(delta_b[0]),
        "delta_null": float(delta_null[0]),
    }
    expected_offsets = offset_predicate["offsets"]
    offset_tolerance = float(
        offset_predicate["absolute_tolerance_frames"]
    )

    def offset_pass(reading: dict) -> bool:
        return max(
            abs(float(reading[name]) - float(expected_offsets[name]))
            for name in ("delta_r", "delta_b", "delta_null")
        ) <= offset_tolerance

    # Exact planted defect: use G1 alone rather than the two-site mean.  The
    # fixed input deliberately gives G1 and G2 different peaks, so this cannot
    # cancel as it did in the symmetric peak-fit fixture.
    g1 = float(fixed_peaks["G1"][0])
    g1_only_reading = {
        "delta_r": float(fixed_peaks["R"][0]) - g1,
        "delta_b": float(fixed_peaks["B"][0]) - g1,
        "delta_null": g1 - float(fixed_peaks["G2"][0]),
    }
    control_green_reference = record_control(
        "C2b_fixed_external_green_reference",
        offset_pass(averaged_reading),
        averaged_reading,
        [
            (
                "P9_use_G1_instead_of_two_site_mean",
                not offset_pass(g1_only_reading),
                g1_only_reading,
            )
        ],
    )
    return [
        control_external,
        control_sign,
        control_null,
        control_green_reference,
    ]


def cfa_control() -> dict:
    # Explicit RGGB table; it is not generated through SITE.
    mosaic = np.tile(
        np.array([[101, 202], [303, 404]], dtype=np.uint16), (4, 4)
    )
    expected = {"R": 101.0, "G1": 202.0, "G2": 303.0, "B": 404.0}

    def read(mapping: dict[str, tuple[int, int]]) -> dict:
        return {
            channel: float(np.median(plane))
            for channel, plane in split_cfa(mosaic, sites=mapping).items()
        }

    actual = read(SITE)
    swapped = dict(SITE)
    swapped["G2"], swapped["B"] = swapped["B"], swapped["G2"]
    planted = read(swapped)
    return record_control(
        "C3_fixed_CFA_layout",
        actual == expected,
        actual,
        [("P4_swap_G2_and_B_sites", planted != expected, planted)],
    )


def registration_control() -> dict:
    rng = np.random.default_rng(41831)
    y, x = np.mgrid[:128, :128]
    texture = (
        rng.normal(0.0, 1.0, (128, 128))
        + 0.7 * np.sin(0.17 * x + 0.09 * y)
        + 0.4 * np.cos(0.07 * x - 0.13 * y)
    )
    rows = []
    planted_rows = []
    green = True
    all_red = True
    for dy, dx in ((0, 0), (3, -5), (-7, 4), (11, 9), (-13, -8)):
        moved = np.roll(np.roll(texture, dy, axis=0), dx, axis=1)
        got_y, got_x, peak = phase_shift(texture, moved)
        ok = round(got_y) == dy and round(got_x) == dx
        plant_y, plant_x = -got_y, -got_x
        plant_ok = round(plant_y) == dy and round(plant_x) == dx
        rows.append(
            {
                "expected": [dy, dx],
                "recovered": [got_y, got_x],
                "correlation_peak": peak,
                "green": ok,
            }
        )
        planted_rows.append(
            {
                "expected": [dy, dx],
                "recovered": [plant_y, plant_x],
                "would_pass": plant_ok,
            }
        )
        green &= ok
        if (dy, dx) != (0, 0):
            all_red &= not plant_ok
    return record_control(
        "C4_registration_roll_convention",
        green,
        {"rows": rows},
        [("P5_invert_registration_sign", all_red, {"rows": planted_rows})],
    )


def dose_control() -> dict:
    k = np.arange(13, dtype=np.float64)
    doses = np.array([0.0, 0.25, 0.5, 1.0, 2.0])
    readings = []
    for dose in doses:
        base = 35.0
        green_curve = base + np.exp(5.0 - 0.22 * (k - 6.0) ** 2)
        red_curve = base + np.exp(5.0 - 0.22 * (k - (6.0 - dose)) ** 2)
        red = peak_fit(red_curve, baseline_override=base)
        green = peak_fit(green_curve, baseline_override=base)
        readings.append(float(red.peak[0] - green.peak[0]))
    observed = np.abs(np.asarray(readings))
    slope = float(np.polyfit(doses[doses <= 1.0], observed[doses <= 1.0], 1)[0])
    monotone = bool(np.all(np.diff(observed) >= -1.0e-9))
    green = monotone and 0.9 <= slope <= 1.1

    clamped = np.minimum(observed, 0.25)
    planted_slope = float(
        np.polyfit(doses[doses <= 1.0], clamped[doses <= 1.0], 1)[0]
    )
    planted_pass = bool(
        np.all(np.diff(clamped) >= -1.0e-9) and 0.9 <= planted_slope <= 1.1
    )
    reading = {
        "doses_frames": doses.tolist(),
        "estimator_delta_r_frames": readings,
        "absolute_response": observed.tolist(),
        "slope_through_one_frame": slope,
        "fully_present_one_frame_reading": float(observed[doses == 1.0][0]),
    }
    planted = {
        "absolute_response": clamped.tolist(),
        "slope_through_one_frame": planted_slope,
    }
    return record_control(
        "C6_dose_response_and_ceiling",
        green,
        reading,
        [("P7_clamp_recovered_effect_at_quarter_frame", not planted_pass, planted)],
    )


def decoder_control() -> dict:
    files = sorted(GRID.glob("*.ARW"), key=lambda path: path.name.lower())
    if not files:
        raise RuntimeError(f"no ARW files under {GRID}")
    first = files[0]
    mosaic_a, metadata_a = decode_visible(first)
    mosaic_b, metadata_b = decode_visible(first)
    planes = split_cfa(mosaic_a, metadata_a["black_levels"])
    plane_summary = {
        channel: {
            "median_black_subtracted": float(np.median(plane)),
            "p01": float(np.percentile(plane, 1)),
            "p99": float(np.percentile(plane, 99)),
        }
        for channel, plane in planes.items()
    }

    command = [
        str(REPO / "target" / "release" / "strehl.exe"),
        "probe",
        str(GRID),
        "--limit",
        "1",
    ]
    completed = subprocess.run(
        command,
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = completed.stdout
    contract = (
        metadata_a == metadata_b
        and metadata_a["shape"] == [4688, 7028]
        and metadata_a["pattern"] == [[0, 1], [3, 2]]
        and metadata_a["color_desc"] == "RGBG"
        and metadata_a["black_levels"] == [512.0, 512.0, 512.0, 512.0]
        and array_sha256(mosaic_a) == array_sha256(mosaic_b)
        and completed.returncode == 0
        and "camera          : ILCE-7CM2" in stdout
        and "iso             : 100" in stdout
        and "active area     : 7032 x 4688" in stdout
        and "levels          : black 512, white 15360" in stdout
    )
    padded_metadata = dict(metadata_a)
    padded_metadata["shape"] = [5120, 7168]
    planted_pass = padded_metadata["shape"] == [4688, 7028]
    reading = {
        "file": str(first),
        "rawpy_metadata": metadata_a,
        "rawpy_pixel_sha256_first": array_sha256(mosaic_a),
        "rawpy_pixel_sha256_second": array_sha256(mosaic_b),
        "plane_summary": plane_summary,
        "rust_probe": {
            "command": command,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": completed.stderr,
        },
        "width_difference_explained": (
            "rawpy/LibRaw exposes 7028 visible columns; strehl/rawler reports "
            "7032 active columns. Verdict path uses only rawpy's copied 7028."
        ),
    }
    return record_control(
        "C7_independent_decoder_contract",
        contract,
        reading,
        [
            (
                "P8_treat_padded_buffer_as_active",
                not planted_pass,
                {"planted_metadata": padded_metadata},
            )
        ],
    )


def main() -> int:
    controls = []
    controls.extend(fixed_controls())
    controls.append(cfa_control())
    controls.append(registration_control())
    controls.append(dose_control())
    controls.append(decoder_control())

    green_count = sum(control["green"] for control in controls)
    plants = [
        plant
        for control in controls
        for plant in control["plants"]
    ]
    red_count = sum(plant["red"] for plant in plants)
    passed = green_count == len(controls) and red_count == len(plants)
    input_paths = [
        Path(__file__).resolve(),
        Path(__file__).with_name("lca_lib.py").resolve(),
        *sorted(FIXTURES.glob("*.json")),
    ]
    result = {
        "schema": 1,
        "purpose": "M-PHASE0-LCA pre-measurement commissioning",
        "environment": environment_record(),
        "input_sha256": {
            path.relative_to(LANE).as_posix(): file_sha256(path)
            for path in input_paths
        },
        "summary": {
            "controls_green": green_count,
            "controls_total": len(controls),
            "plants_red": red_count,
            "plants_total": len(plants),
            "all_passed": passed,
        },
        "controls": controls,
    }
    write_json(OUT / "commission.json", result)

    print(
        f"commission: controls {green_count}/{len(controls)} GREEN; "
        f"plants {red_count}/{len(plants)} RED"
    )
    for control in controls:
        plant_text = ", ".join(
            f"{plant['name']}={'RED' if plant['red'] else 'FAILED'}"
            for plant in control["plants"]
        )
        print(
            f"  {control['name']}: "
            f"{'GREEN' if control['green'] else 'FAILED'}; {plant_text}"
        )
    print(f"wrote {OUT / 'commission.json'}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
