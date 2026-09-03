"""Commission the independent C2 corpus-audit checker before RAW replay."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.ndimage import sobel


HERE = Path(__file__).resolve().parent
LANE = HERE.parent
FIXTURES = LANE / "fixtures"
OUT = LANE / "out"
CHANNELS = ("R", "G1", "G2", "B")


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def peak(curve: np.ndarray, *, sign: float = 1.0, scale: float = 1.0) -> float:
    values = np.asarray(curve, dtype=np.float64)
    centre = int(np.argmax(values))
    if centre == 0 or centre == values.size - 1:
        raise ValueError("fixed curve peak is not interior")
    before, middle, after = values[centre - 1 : centre + 2]
    denominator = before - 2.0 * middle + after
    if denominator >= 0.0:
        raise ValueError("fixed curve peak is not concave")
    offset = sign * 0.5 * (before - after) / denominator
    return scale * (centre + offset)


def interpolate(curve: np.ndarray, coordinate: float) -> float:
    values = np.asarray(curve, dtype=np.float64)
    clipped = float(np.clip(coordinate, 0.0, values.size - 1.001))
    lower = int(np.floor(clipped))
    fraction = clipped - lower
    return float(
        values[lower] * (1.0 - fraction) + values[lower + 1] * fraction
    )


def reading(
    responses: dict[str, list[float]],
    *,
    sign: float = 1.0,
    scale: float = 1.0,
    swap_rb: bool = False,
    green_mode: str = "mean",
    loss_sign: float = 1.0,
) -> dict:
    curves = {
        channel: np.asarray(responses[channel], dtype=np.float64)
        for channel in CHANNELS
    }
    if swap_rb:
        curves["R"], curves["B"] = curves["B"], curves["R"]
    peaks = {
        channel: peak(curve, sign=sign, scale=scale)
        for channel, curve in curves.items()
    }
    green = (
        peaks["G1"]
        if green_mode == "g1"
        else 0.5 * (peaks["G1"] + peaks["G2"])
    )
    offsets = {
        "delta_r": peaks["R"] - green,
        "delta_b": peaks["B"] - green,
        "delta_null": peaks["G1"] - peaks["G2"],
    }
    forfeit = {}
    for channel in ("R", "B", "G1"):
        own = interpolate(curves[channel], peaks[channel] / scale)
        at_green = interpolate(curves[channel], green / scale)
        forfeit[channel] = loss_sign * (1.0 - at_green / own)
    return {"peaks": peaks, "offsets": offsets, "forfeit": forfeit}


def predicate_pass(actual: dict, predicate: dict) -> bool:
    tolerance = float(predicate["absolute_tolerance"])
    errors = []
    for section in ("peaks", "offsets", "forfeit"):
        for name, expected in predicate[section].items():
            errors.append(abs(float(actual[section][name]) - float(expected)))
    return bool(errors) and max(errors) <= tolerance


def normalised_focus(image: np.ndarray) -> float:
    values = np.asarray(image, dtype=np.float64)
    gx = sobel(values, axis=1, mode="nearest")
    gy = sobel(values, axis=0, mode="nearest")
    energy = float(np.mean(gx * gx + gy * gy))
    variance = float(np.var(values))
    return energy / max(variance, 1.0e-12)


def main() -> int:
    fixed_input = read_json(FIXTURES / "c2-audit-gain-input.json")
    predicate = read_json(FIXTURES / "c2-audit-gain-predicate.json")
    responses = fixed_input["responses"]
    actual = reading(responses)
    mutations = [
        ("P1_invert_vertex_sign", reading(responses, sign=-1.0)),
        ("P2_double_frame_scale", reading(responses, scale=2.0)),
        ("P3_swap_red_and_blue", reading(responses, swap_rb=True)),
        ("P4_use_G1_only", reading(responses, green_mode="g1")),
        ("P5_invert_loss_sign", reading(responses, loss_sign=-1.0)),
    ]
    external = {
        "name": "C1_fixed_external_peak_offset_and_loss",
        "green": predicate_pass(actual, predicate),
        "reading": actual,
        "plants": [
            {
                "name": name,
                "red": not predicate_pass(mutated, predicate),
                "reading": mutated,
            }
            for name, mutated in mutations
        ],
    }

    y, x = np.mgrid[:96, :112]
    texture = (
        700.0
        + 0.9 * x
        + 0.4 * y
        + 80.0 * np.sin(0.17 * x + 0.11 * y)
        + 45.0 * np.cos(0.07 * x - 0.19 * y)
    )
    base = normalised_focus(texture)
    affine = normalised_focus(1.7 * texture + 231.0)
    raw_energy_base = float(
        np.mean(
            sobel(texture, axis=1) ** 2 + sobel(texture, axis=0) ** 2
        )
    )
    transformed = 1.7 * texture + 231.0
    raw_energy_affine = float(
        np.mean(
            sobel(transformed, axis=1) ** 2
            + sobel(transformed, axis=0) ** 2
        )
    )
    relative_error = abs(affine / base - 1.0)
    sabotage_change = abs(raw_energy_affine / raw_energy_base - 1.0)
    affine_control = {
        "name": "C2_affine_normalised_focus",
        "green": relative_error < 1.0e-12,
        "reading": {
            "base": base,
            "affine": affine,
            "relative_error": relative_error,
        },
        "plants": [
            {
                "name": "P6_omit_variance_normalisation",
                "red": sabotage_change > 1.0,
                "reading": {"relative_change": sabotage_change},
            }
        ],
    }

    controls = [external, affine_control]
    plants = [
        plant for control in controls for plant in control["plants"]
    ]
    green = sum(bool(control["green"]) for control in controls)
    red = sum(bool(plant["red"]) for plant in plants)
    passed = green == len(controls) and red == len(plants)
    result = {
        "schema": 1,
        "purpose": "commission independent C2 corpus-audit checker",
        "summary": {
            "controls_green": green,
            "controls_total": len(controls),
            "plants_red": red,
            "plants_total": len(plants),
            "all_passed": passed,
        },
        "controls": controls,
    }
    write_json(OUT / "c2-audit-commission.json", result)
    print(
        f"C2 audit commission: {green}/{len(controls)} GREEN; "
        f"{red}/{len(plants)} plants RED"
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
