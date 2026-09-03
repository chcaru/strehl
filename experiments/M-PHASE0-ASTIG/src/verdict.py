"""Apply the preregistered stop gates and file the M-PHASE0-ASTIG verdict."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
REPO = ROOT.parents[1]

PRIMARY_SETUPS = ("grid1-sw4", "grid2-sw4")
SENSITIVITIES = (
    "tile128",
    "tile256",
    "g1",
    "g2",
    "block3",
    "block5",
    "xminus2",
    "xplus2",
    "linear",
    "log-no-baseline",
    "omit-left",
    "omit-right",
    "omit-top",
    "omit-bottom",
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def record_named(reduction: dict, name: str) -> dict:
    matches = [
        record
        for record in reduction["records"]
        if record["stack"]["name"] == name
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one {name} record, found {len(matches)}")
    return matches[0]


def outer_row(record: dict) -> dict:
    matches = [row for row in record["radii"] if row["radius"] == 0.90]
    if len(matches) != 1:
        raise ValueError(
            f"expected one radius-0.90 row for {record['stack']['name']}"
        )
    return matches[0]


def centre_beyond_one(record: dict) -> bool:
    interval = record["centre_null"]["estimate"]["bootstrap"]["delta"]
    return interval["lo95"] > 1.0 or interval["hi95"] < -1.0


def stop_gates(
    commission: dict,
    loader: dict,
    inventory: dict,
    primary: dict,
    *,
    defect: str | None = None,
) -> list[dict]:
    """Return failures in the order fixed in preregistration section 9."""
    failures = []
    tally = commission["tally"]
    commission_ok = (
        tally["controls"] == 8
        and tally["clean_pass"] == 8
        and tally["clean_fail"] == 0
        and tally["plants"] == 8
        and tally["red"] == 8
        and tally["missed"] == 0
    )
    if defect != "ignore-commission" and not commission_ok:
        failures.append(
            {
                "id": "commissioning",
                "reason": "estimator commissioning tally is not 8 PASS / 8 RED",
            }
        )

    loader_tally = loader["tally"]
    loader_ok = (
        loader["rawpy"]["status"] == "PASS"
        and loader["rawler"]["status"] == "PASS"
        and loader_tally["known_answer_pass"] == loader_tally["known_answer_total"]
        and loader_tally["plants_red"] == loader_tally["plants_total"]
        and loader["padded_shape_plant"]["status"] == "RED"
    )
    if defect != "ignore-loader" and not loader_ok:
        failures.append(
            {
                "id": "loader",
                "reason": "decoder contract or padded-shape plant failed",
            }
        )

    if (
        defect != "ignore-inventory"
        and not inventory.get("capture_snapshot_unchanged", False)
    ):
        failures.append(
            {
                "id": "capture-snapshot",
                "reason": "read-only capture snapshot changed during extraction",
            }
        )

    flat = record_named(primary, "razor-flat-f8")
    if defect != "ignore-flat" and flat["flat_control_refused"] is not True:
        failures.append(
            {
                "id": "flat-refusal",
                "reason": "texture-poor razor tile did not refuse a focus split",
            }
        )

    setups = [record_named(primary, name) for name in PRIMARY_SETUPS]
    centre_flags = [centre_beyond_one(record) for record in setups]
    if defect != "ignore-centre" and all(centre_flags):
        failures.append(
            {
                "id": "centre-null",
                "reason": "both setup centre intervals lie wholly beyond one frame",
                "setup_flags": dict(zip(PRIMARY_SETUPS, centre_flags)),
            }
        )

    counts = {
        record["stack"]["name"]: outer_row(record)["valid_sector_count"]
        for record in setups
    }
    if defect != "ignore-sectors" and min(counts.values()) < 3:
        failures.append(
            {
                "id": "primary-outer-sectors",
                "reason": "a primary setup has fewer than three valid outer sectors",
                "counts": counts,
                "required_each": 3,
            }
        )
    return failures


def tile_gate_detail(record: dict) -> list[dict]:
    details = []
    for tile in record["tiles"]:
        if tile["radius"] != 0.90 or tile["sector"] == "centre":
            continue
        estimate = tile["estimate"]
        details.append(
            {
                "sector": tile["sector"],
                "valid_for_map": tile["valid_for_map"],
                "delta": estimate.get("delta"),
                "uncertainty_rejection": estimate.get("uncertainty_rejection"),
                "x_width95": (
                    estimate.get("bootstrap", {}).get("zx", {}).get("width95")
                ),
                "y_width95": (
                    estimate.get("bootstrap", {}).get("zy", {}).get("width95")
                ),
            }
        )
    return details


def reduction_digest(reduction: dict) -> dict:
    pair = reduction.get("primary_pair")
    setups = {}
    for name in PRIMARY_SETUPS:
        record = record_named(reduction, name)
        outer = outer_row(record)
        centre_interval = record["centre_null"]["estimate"]["bootstrap"]["delta"]
        setups[name] = {
            "outer": outer,
            "outer_tile_gates": tile_gate_detail(record),
            "centre_delta": record["centre_null"]["estimate"]["delta"],
            "centre_delta_interval": centre_interval,
        }
    return {
        "variant": reduction["variant"],
        "primary_pair": pair,
        "setups": setups,
    }


def main() -> None:
    input_paths = {
        "commission": OUT / "commission.json",
        "verdict_commission": OUT / "verdict-commission.json",
        "loader": OUT / "loader-check.json",
        "inventory": OUT / "capture-inventory.json",
        "primary": OUT / "real-primary.json",
    }
    inputs = {name: load_json(path) for name, path in input_paths.items()}
    verdict_tally = inputs["verdict_commission"]["tally"]
    if not (
        verdict_tally["controls"] == verdict_tally["clean_pass"] == 6
        and verdict_tally["clean_fail"] == 0
        and verdict_tally["plants"] == verdict_tally["red"] == 6
        and verdict_tally["missed"] == 0
    ):
        raise RuntimeError("verdict stop-gate evaluator is not commissioned")
    failures = stop_gates(
        inputs["commission"],
        inputs["loader"],
        inputs["inventory"],
        inputs["primary"],
    )
    if not failures:
        raise RuntimeError(
            "no stop gate fired; simultaneous-inference classification is not "
            "implemented because this lane preregistered stopping first"
        )

    sensitivity_paths = {
        name: OUT / f"sensitivity-{name}.json" for name in SENSITIVITIES
    }
    missing = [name for name, path in sensitivity_paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing sensitivities: {', '.join(missing)}")
    sensitivities = {
        name: reduction_digest(load_json(path))
        for name, path in sensitivity_paths.items()
    }

    setup_counts = {
        name: outer_row(record_named(inputs["primary"], name))[
            "valid_sector_count"
        ]
        for name in PRIMARY_SETUPS
    }
    result = {
        "schema_version": 1,
        "claim": "C7 astigmatism",
        "verdict": "NOT ROBUST",
        "decision_stage": "preregistered section-9 stop gate",
        "decisive_quantity": {
            "name": "minimum valid outer sectors across primary setups",
            "value": min(setup_counts.values()) if setup_counts else None,
            "required_each": 3,
            "sampling_uncertainty": (
                "not applicable to the deterministic validity count; each "
                "tile gate uses a 2,000-draw 95% bootstrap interval"
            ),
            "D4_abs_frames": None,
            "D4_reason": inputs["primary"]["primary_pair"]["reason"],
        },
        "stop_failures": failures,
        "controls": {
            "estimator": inputs["commission"]["tally"],
            "verdict_evaluator": verdict_tally,
            "loader": inputs["loader"]["tally"],
            "flat_refused": record_named(
                inputs["primary"], "razor-flat-f8"
            )["flat_control_refused"],
        },
        "primary": reduction_digest(inputs["primary"]),
        "sensitivities": sensitivities,
        "post_stop_inference": {
            "status": "NOT PERFORMED",
            "reason": (
                "Preregistration section 9 says to stop rather than interpret "
                "numbers when a primary setup has fewer than three valid outer "
                "sectors. D4, multiplicity-controlled bounds, empirical "
                "step-width rescaling, and ladder classifications therefore "
                "cannot establish a claim verdict."
            ),
        },
        "rust_consequence": {
            "change": "none",
            "reason": (
                "A NOT ROBUST verdict preregistered no Rust change until a "
                "repeat controlled chart resolves the failed primary gate."
            ),
            "deferred_modules": [
                "crates/strehl-core/src/focus.rs",
                "crates/strehl-core/src/pyramid.rs",
                "crates/strehl-cli/src/merge_cmd.rs",
            ],
        },
        "provenance": {
            "git_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
            ).strip(),
            "invocation": (
                "PYTHONIOENCODING=utf-8; "
                "python experiments\\M-PHASE0-ASTIG\\src\\verdict.py"
            ),
            "input_sha256": {
                name: file_sha256(path) for name, path in input_paths.items()
            }
            | {
                f"sensitivity-{name}": file_sha256(path)
                for name, path in sensitivity_paths.items()
            },
            "source_sha256": file_sha256(Path(__file__)),
        },
    }
    target = OUT / "verdict.json"
    target.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"{result['verdict']}: "
        f"{result['decisive_quantity']['value']}/"
        f"{result['decisive_quantity']['required_each']} valid outer sectors"
    )
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
