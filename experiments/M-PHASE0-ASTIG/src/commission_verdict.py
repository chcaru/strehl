"""Commission the preregistered verdict stop-gate evaluator on literal fixtures."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import verdict as V


HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def passing_fixtures() -> tuple[dict, dict, dict, dict]:
    commission = {
        "tally": {
            "controls": 8,
            "clean_pass": 8,
            "clean_fail": 0,
            "plants": 8,
            "red": 8,
            "missed": 0,
        }
    }
    loader = {
        "rawpy": {"status": "PASS"},
        "rawler": {"status": "PASS"},
        "padded_shape_plant": {"status": "RED"},
        "tally": {
            "known_answer_pass": 2,
            "known_answer_total": 2,
            "plants_red": 1,
            "plants_total": 1,
        },
    }
    inventory = {"capture_snapshot_unchanged": True}

    def setup(name: str) -> dict:
        return {
            "stack": {"name": name},
            "radii": [{"radius": 0.90, "valid_sector_count": 4}],
            "centre_null": {
                "estimate": {
                    "bootstrap": {
                        "delta": {"lo95": -0.25, "hi95": 0.25}
                    }
                }
            },
        }

    primary = {
        "records": [
            setup("grid1-sw4"),
            setup("grid2-sw4"),
            {
                "stack": {"name": "razor-flat-f8"},
                "flat_control_refused": True,
            },
        ]
    }
    return commission, loader, inventory, primary


def gate_ids(fixtures: tuple[dict, dict, dict, dict], defect=None) -> set[str]:
    return {
        row["id"]
        for row in V.stop_gates(*fixtures, defect=defect)
    }


def run_control(
    control_id: str,
    mutation,
    defect: str,
) -> dict:
    fixtures = passing_fixtures()
    baseline_ids = gate_ids(fixtures)
    mutated = copy.deepcopy(fixtures)
    mutation(mutated)
    detected_ids = gate_ids(mutated)
    planted_ids = gate_ids(mutated, defect=defect)
    clean_pass = not baseline_ids and control_id in detected_ids
    plant_red = control_id not in planted_ids
    return {
        "id": control_id,
        "plant": defect,
        "clean_status": "PASS" if clean_pass else "FAIL",
        "plant_status": "RED" if plant_red else "MISSED",
        "baseline_failures": sorted(baseline_ids),
        "invalid_fixture_failures": sorted(detected_ids),
        "defective_evaluator_failures": sorted(planted_ids),
    }


def main() -> None:
    controls = [
        run_control(
            "commissioning",
            lambda f: f[0]["tally"].update(clean_pass=7, clean_fail=1),
            "ignore-commission",
        ),
        run_control(
            "loader",
            lambda f: f[1]["rawpy"].update(status="FAIL"),
            "ignore-loader",
        ),
        run_control(
            "capture-snapshot",
            lambda f: f[2].update(capture_snapshot_unchanged=False),
            "ignore-inventory",
        ),
        run_control(
            "flat-refusal",
            lambda f: f[3]["records"][2].update(flat_control_refused=False),
            "ignore-flat",
        ),
        run_control(
            "centre-null",
            lambda f: [
                record["centre_null"]["estimate"]["bootstrap"]["delta"].update(
                    lo95=1.10, hi95=1.40
                )
                for record in f[3]["records"][:2]
            ],
            "ignore-centre",
        ),
        run_control(
            "primary-outer-sectors",
            lambda f: f[3]["records"][0]["radii"][0].update(
                valid_sector_count=2
            ),
            "ignore-sectors",
        ),
    ]
    clean_pass = sum(row["clean_status"] == "PASS" for row in controls)
    red = sum(row["plant_status"] == "RED" for row in controls)
    result = {
        "schema_version": 1,
        "role": "commissioning before trusting the real-data verdict",
        "fixture": (
            "literal dictionaries independent of real_measure.py and "
            "reduce_real.py"
        ),
        "tally": {
            "controls": len(controls),
            "clean_pass": clean_pass,
            "clean_fail": len(controls) - clean_pass,
            "plants": len(controls),
            "red": red,
            "missed": len(controls) - red,
        },
        "records": controls,
        "provenance": {
            "invocation": (
                "PYTHONIOENCODING=utf-8; "
                "PYTHONPATH=<repo>\\experiments\\M-PHASE0-ASTIG\\src; "
                "python experiments\\M-PHASE0-ASTIG\\src\\commission_verdict.py"
            ),
            "source_sha256": {
                "commission_verdict.py": sha256(Path(__file__)),
                "verdict.py": sha256(HERE / "verdict.py"),
            },
        },
    }
    target = OUT / "verdict-commission.json"
    target.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"verdict commissioning: {clean_pass}/{len(controls)} PASS, "
        f"{red}/{len(controls)} RED"
    )
    print(f"wrote {target}")
    if clean_pass != len(controls) or red != len(controls):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
