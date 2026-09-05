"""Independent-output checks for M183-rho-convention.

This checker reads stored per-fit rho values rather than importing analyze.py's
frequency enumerator or scalar reducer.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STREHL = ROOT.parent.parent
OUT = ROOT / "out"
PREREG_COMMIT = "014063e498a2f0a1faf627b7bb7534e3163e76cd"
SCENES = (
    "bee-1-cpl",
    "dry-erase-marker-head-cpl",
    "flower-inner-edge-cpl",
    "pencil-steep-angle-cpl",
    "wrapped-text-1",
)
ACCURACY = (0.0801, 0.1168, 0.2256)


def check(name: str, passed: bool, **details) -> dict:
    return {"name": name, "status": "PASS" if passed else "FAIL", **details}


def fit(record: dict) -> dict:
    return record["fits"][record.get("primary_fit_key", "full_a")]


def groups(records: list[dict]) -> dict[str, list[dict]]:
    result = {
        scene: [
            row
            for row in records
            if row.get("arm") == "ordinary-census"
            and row.get("scene") == scene
            and row.get("status") == "PASS"
        ]
        for scene in SCENES
    }
    result["bee-repeat"] = [
        row
        for row in records
        if row.get("arm") == "repeat-primary"
        and row.get("scene") == "bee"
        and row.get("status") == "PASS"
    ]
    if any(not rows for rows in result.values()):
        raise ValueError("verification population is incomplete")
    return result


def aggregate_field(records: list[dict], field: str) -> tuple[dict, dict]:
    values = {
        scene: float(np.median([float(fit(row)[field]) for row in rows]))
        for scene, rows in groups(records).items()
    }
    sample = np.asarray(list(values.values()), dtype=float)
    generator = np.random.default_rng(20260902)
    boot = np.median(
        generator.choice(sample, size=(10_000, sample.size), replace=True),
        axis=1,
    )
    summary = {
        "median": float(np.median(sample)),
        "interval_95": [
            float(np.percentile(boot, 2.5)),
            float(np.percentile(boot, 97.5)),
        ],
    }
    return values, summary


def phase_curves(payload: dict) -> list[tuple[np.ndarray, np.ndarray]]:
    rows = [
        row
        for row in payload["rows"]
        if row["target"] == "G-1x"
        and str(row["snr"]) == "inf"
        and row["gauge"] == "zero_mean"
        and row["bar_unit"] is not None
    ]
    rhos = sorted({float(row["rho"]) for row in rows})
    rungs = {
        rho: [row for row in rows if float(row["rho"]) == rho]
        for rho in rhos
    }
    if len({len(value) for value in rungs.values()}) != 1:
        raise ValueError("unequal PHASE rungs")
    curves = []
    for index in range(len(next(iter(rungs.values())))):
        bars = np.asarray(
            [float(rungs[rho][index]["bar_unit"]) for rho in rhos],
            dtype=float,
        )
        curves.append((np.asarray(rhos, dtype=float), bars))
    return curves


def phase_read(
    curves: list[tuple[np.ndarray, np.ndarray]], rho: float
) -> list[dict]:
    bars = []
    for rhos, values in curves:
        bars.append(
            math.exp(
                np.interp(math.log(rho), np.log(rhos), np.log(values))
            )
        )
    value = np.asarray(bars, dtype=float)
    result = []
    for accuracy in ACCURACY:
        fraction = float(np.mean(value > accuracy))
        verdict = (
            "SURVIVE"
            if fraction >= 0.60
            else "NARROWED"
            if fraction >= 0.25
            else "KILL"
        )
        result.append({"fraction": fraction, "verdict": verdict})
    return result


def prereg_commit_paths() -> list[str]:
    process = subprocess.run(
        [
            "git",
            "-C",
            str(STREHL),
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            PREREG_COMMIT,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in process.stdout.splitlines() if line]


def main() -> int:
    result = json.loads((OUT / "result.json").read_text(encoding="utf-8"))
    commission = json.loads((OUT / "commission.json").read_text(encoding="utf-8"))
    records = json.loads(
        (
            STREHL
            / "experiments"
            / "M-PHASE0-RHO"
            / "out"
            / "scene-estimates.json"
        ).read_text(encoding="utf-8")
    )
    phase = json.loads(
        (
            STREHL
            / "experiments"
            / "M-PHASE0-PHASE"
            / "out"
            / "p1_bar.json"
        ).read_text(encoding="utf-8")
    )

    scene_values, rho = aggregate_field(records, "rho_g_boundary_average")
    grid8 = aggregate_field(records, "rho_g")[1]["median"]
    grid16 = aggregate_field(records, "rho_g_grid16")[1]["median"]
    grid32 = aggregate_field(records, "rho_g_grid32")[1]["median"]
    curves = phase_curves(phase)
    reads = {
        "interval_low": phase_read(curves, rho["interval_95"][0]),
        "median": phase_read(curves, rho["median"]),
        "interval_high": phase_read(curves, rho["interval_95"][1]),
    }
    result_reads = {}
    labels = ("field centre", "inner annulus", "corner")
    for point in reads:
        result_reads[point] = [
            {
                "fraction": result["c1"]["points"][point][label][
                    "winnable_fraction"
                ],
                "verdict": result["c1"]["points"][point][label]["verdict"],
            }
            for label in labels
        ]

    paths = prereg_commit_paths()
    checks = [
        check(
            "V1 preregistration commit is isolated",
            paths == ["experiments/M183-rho-convention/PREREGISTRATION.md"],
            paths=paths,
        ),
        check(
            "V2 commissioning green without exception catches",
            commission["status"] == "PASS"
            and commission["known_answer_tally"] == {"pass": 10, "fail": 0}
            and commission["mutation_tally"] == {"caught": 4, "missed": 0}
            and all("exception" not in row for row in commission["mutants"]),
        ),
        check(
            "V3 stored boundary-average aggregation",
            list(scene_values) == list(result["rho"]["scene_values"])
            and np.allclose(
                list(scene_values.values()),
                list(result["rho"]["scene_values"].values()),
                rtol=1e-12,
                atol=0.0,
            )
            and np.allclose(
                [rho["median"], *rho["interval_95"]],
                [
                    result["rho"]["median"],
                    *result["rho"]["interval_95"],
                ],
                rtol=1e-12,
                atol=0.0,
            ),
            independently_aggregated=rho,
        ),
        check(
            "V4 stored grid ladder",
            np.allclose(
                [grid8, grid16, grid32, grid8 / grid32],
                [
                    result["grid_crux"]["8"]["scene_median"],
                    result["grid_crux"]["16"]["scene_median"],
                    result["grid_crux"]["32"]["scene_median"],
                    result["grid_crux"]["factor_8_to_32"],
                ],
                rtol=1e-12,
                atol=0.0,
            ),
            independently_aggregated={
                "8": grid8,
                "16": grid16,
                "32": grid32,
                "factor": grid8 / grid32,
            },
        ),
        check(
            "V5 independent PHASE endpoint reads",
            reads == result_reads,
            independently_computed=reads,
        ),
        check(
            "V6 filed answer follows endpoint classes",
            result["answer"] == "STILL_FLIPS"
            and reads["interval_low"][0]["verdict"] == "KILL"
            and reads["interval_high"][0]["verdict"] == "NARROWED",
        ),
    ]
    failed = [row for row in checks if row["status"] != "PASS"]
    payload = {
        "status": "PASS" if not failed else "FAIL",
        "tally": {"pass": len(checks) - len(failed), "fail": len(failed)},
        "checks": checks,
    }
    (OUT / "verify.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    summary = f"verification: PASS {len(checks) - len(failed)} / FAIL {len(failed)}\n"
    (OUT / "verify.txt").write_text(summary, encoding="utf-8")
    print(summary, end="")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
