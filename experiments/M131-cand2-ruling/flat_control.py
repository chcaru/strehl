from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CAND2_SRC = REPO / "experiments" / "M-CAND2" / "src"
sys.path.insert(0, str(CAND2_SRC))

import cand2 as core  # noqa: E402


NULL_REPEATS = 16
POWER_REPEATS = 4
BLOCKS = 5
SITES = 96


def flat_backgrounds() -> np.ndarray:
    data = np.empty(
        (BLOCKS, SITES, core.CHANNELS, core.PLANE_SIDE, core.PLANE_SIDE),
        dtype=np.float64,
    )
    channel_offsets = np.asarray([0.015, 0.005, -0.004, -0.012])
    for block in range(BLOCKS):
        for site in range(SITES):
            level = 0.29 + 0.012 * math.sin(0.19 * site + 0.7 * block)
            for channel in range(core.CHANNELS):
                data[block, site, channel] = level + channel_offsets[channel]
    return data


def no_target_observations(
    backgrounds: np.ndarray,
    seed: int,
) -> core.ObservationSet:
    covariance = []
    derivative_plus = [[] for _ in range(core.TEMPLATE_COUNT)]
    derivative_minus = [[] for _ in range(core.TEMPLATE_COUNT)]
    test_plus = [[] for _ in range(core.TEMPLATE_COUNT)]
    test_minus = [[] for _ in range(core.TEMPLATE_COUNT)]
    blocks = []
    macros = []
    noise_family = f"M131-flat-null-{seed}"
    for block in range(BLOCKS):
        for macro in range(SITES):
            background = backgrounds[block, macro]
            covariance.append(
                core._observation(
                    background,
                    None,
                    0,
                    seed,
                    noise_family,
                    block,
                    macro,
                    "covariance",
                    None,
                )
            )
            for template in range(core.TEMPLATE_COUNT):
                derivative_plus[template].append(
                    core._observation(
                        background,
                        None,
                        1,
                        seed,
                        noise_family,
                        block,
                        macro,
                        "derivative",
                        template,
                    )
                )
                derivative_minus[template].append(
                    core._observation(
                        background,
                        None,
                        -1,
                        seed,
                        noise_family,
                        block,
                        macro,
                        "derivative",
                        template,
                    )
                )
                test_plus[template].append(
                    core._observation(
                        background,
                        None,
                        1,
                        seed,
                        noise_family,
                        block,
                        macro,
                        "test",
                        template,
                    )
                )
                test_minus[template].append(
                    core._observation(
                        background,
                        None,
                        -1,
                        seed,
                        noise_family,
                        block,
                        macro,
                        "test",
                        template,
                    )
                )
            blocks.append(block)
            macros.append(macro)
    return core.ObservationSet(
        covariance=np.asarray(covariance, dtype=np.float64),
        derivative_plus=np.asarray(derivative_plus, dtype=np.float64),
        derivative_minus=np.asarray(derivative_minus, dtype=np.float64),
        test_plus=np.asarray(test_plus, dtype=np.float64),
        test_minus=np.asarray(test_minus, dtype=np.float64),
        blocks=np.asarray(blocks, dtype=np.int64),
        macros=np.asarray(macros, dtype=np.int64),
    )


def result_row(result: core.HotellingResult, seed: int) -> dict:
    conditions = [model.condition_number for model in result.models]
    return {
        "seed": seed,
        "status": result.status,
        "d2": result.d2,
        "accuracy": result.accuracy,
        "refusal": result.refusal,
        "condition_number_max": max(conditions) if conditions else None,
    }


def summary(values: list[float]) -> dict:
    array = np.asarray(values, dtype=np.float64)
    return {
        "n": len(array),
        "mean": float(array.mean()),
        "standard_deviation": float(array.std(ddof=1)),
        "standard_error": float(array.std(ddof=1) / math.sqrt(len(array))),
        "minimum": float(array.min()),
        "maximum": float(array.max()),
    }


def lawful_flat_gate(row: dict) -> bool:
    return row["status"] not in ("NUMERIC", "Ok")


def run(output: Path) -> int:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    core.configure_threads()
    backgrounds = flat_backgrounds()

    null_rows = []
    for index in range(NULL_REPEATS):
        seed = core.stable_seed("M131", "flat-null", index)
        result = core.crossfit(
            no_target_observations(backgrounds, seed),
            f"M131-flat-null-{index}",
        )
        null_rows.append(result_row(result, seed))

    power_rows = []
    for index in range(POWER_REPEATS):
        seed = core.stable_seed("M131", "flat-power", index)
        result = core.crossfit(
            core.make_observations(backgrounds, seed, "base"),
            f"M131-flat-power-{index}",
        )
        power_rows.append(result_row(result, seed))

    numeric_null = [
        float(row["d2"])
        for row in null_rows
        if row["status"] == "NUMERIC" and row["d2"] is not None
    ]
    numeric_power = [
        float(row["d2"])
        for row in power_rows
        if row["status"] == "NUMERIC" and row["d2"] is not None
    ]
    null_summary = summary(numeric_null) if numeric_null else None
    power_summary = summary(numeric_power) if numeric_power else None
    power_control = bool(
        len(numeric_power) == POWER_REPEATS
        and len(numeric_null) == NULL_REPEATS
        and min(numeric_power) > max(numeric_null)
    )

    real_gate_accepts = [lawful_flat_gate(row) for row in null_rows]
    mutant_gate_accepts = [
        row["status"] == "NUMERIC" and row["d2"] is not None for row in null_rows
    ]
    mutation_caught = bool(
        all(not accepted for accepted in real_gate_accepts) and all(mutant_gate_accepts)
    )
    flat_pass = bool(all(real_gate_accepts))

    record = {
        "protocol": "M131-flat-control-v1",
        "input": {
            "spatial_content": "constant per channel and site",
            "target_amplitude": 0.0,
            "blocks": BLOCKS,
            "sites_per_block": SITES,
            "dimension": core.DIMENSION,
            "templates": core.TEMPLATE_COUNT,
            "independent_streams": [
                "covariance",
                "derivative-plus",
                "derivative-minus",
                "test-plus",
                "test-minus",
            ],
        },
        "flat_gate": {
            "required": "typed non-numeric NO_TARGET refusal",
            "passed": flat_pass,
            "numeric_rows": len(numeric_null),
            "null_d2": null_summary,
            "null_accuracy": summary([float(row["accuracy"]) for row in null_rows]),
        },
        "power_control": {
            "registered_target_amplitude": core.SIGNAL_AMPLITUDE,
            "passed": power_control,
            "d2": power_summary,
            "all_power_above_all_null": power_control,
        },
        "planted_wrong_answer": {
            "mutation": "accept every finite NUMERIC zero-target result",
            "caught": mutation_caught,
        },
        "null_rows": null_rows,
        "power_rows": power_rows,
        "verdict": "PASS" if flat_pass and power_control else "FAIL",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"flat={record['flat_gate']['passed']} "
        f"numeric={len(numeric_null)}/{NULL_REPEATS} "
        f"null_mean={null_summary['mean'] if null_summary else None} "
        f"null_se={null_summary['standard_error'] if null_summary else None} "
        f"power={power_control} mutation_caught={mutation_caught}"
    )
    return 0 if record["verdict"] == "PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "flat-control.json",
    )
    args = parser.parse_args()
    return run(args.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
