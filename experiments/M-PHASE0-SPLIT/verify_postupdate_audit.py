"""Independently re-derive the post-update audit's load-bearing fields."""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
OUT = LANE / "out"


def expected() -> dict[str, object]:
    raw = json.loads(
        (OUT / "m115-rerun" / "s03_instrument.json").read_text(encoding="utf-8")
    )
    prototype = json.loads((OUT / "commission.json").read_text(encoding="utf-8"))
    m41 = (
        ROOT / "docs" / "research" / "M41-r3-kill-measured.md"
    ).read_text(encoding="utf-8")
    recoveries = [
        value
        for arm in ("MEAN", "FRAME*")
        for value in raw["C2"]["109MSDCF"]["res"][arm]["recovery"]
    ]
    common = re.search(
        r"low_band=([\d.]+)", prototype["readings"]["common_mode"]
    )
    if common is None:
        raise RuntimeError("missing common-mode reading")
    return {
        "numeric_passed": (
            round(min(recoveries), 4) == 0.9938
            and round(max(recoveries), 4) == 0.9974
        ),
        "null_failed_arms": sorted(
            name
            for name, row in raw["C1p"]["arms"].items()
            if float(row["mx"]) >= 0.25
        ),
        "common_mode_frc": float(common.group(1)),
        "withdrawal": (
            "32 settings, 0 of which are uncensored" in m41
            and "The FRC 1/7 crossing is withdrawn" in m41
        ),
    }


def mismatches(record: dict[str, object]) -> list[str]:
    want = expected()
    got_numeric = record["historical_numeric_reproduction"]
    got_transfer = record["transfer_and_meaning"]
    failures = []
    if got_numeric["passed"] != want["numeric_passed"]:
        failures.append("numeric_passed")
    if got_transfer["historical_null_failed_arms"] != want["null_failed_arms"]:
        failures.append("null_failed_arms")
    if abs(got_transfer["common_mode_adversary_low_band_frc"] - want["common_mode_frc"]) > 1e-12:
        failures.append("common_mode_frc")
    if got_transfer["later_frc_withdrawal_found"] != want["withdrawal"]:
        failures.append("withdrawal")
    expected_verdict = (
        "STOP_REMOVE_RUST"
        if (
            not got_transfer["historical_null_passed"]
            and got_transfer["common_mode_adversary_violates_null"]
            and got_transfer["power_identity_is_algebraic"]
            and not got_transfer["data_dependent_tuning_plant_present"]
            and got_transfer["later_frc_withdrawal_found"]
        )
        else "PASS_BUILD"
    )
    if record["verdict"] != expected_verdict:
        failures.append("verdict")
    return failures


def main() -> int:
    record = json.loads((OUT / "postupdate-audit.json").read_text(encoding="utf-8"))
    failures = mismatches(record)
    if failures:
        print(f"POST-UPDATE AUDIT CHECK RED: {failures}")
        return 1

    plants: dict[str, bool] = {}
    if "--commission" in sys.argv:
        mutations = {
            "numeric": ("historical_numeric_reproduction", "passed"),
            "null": ("transfer_and_meaning", "historical_null_failed_arms"),
            "withdrawal": ("transfer_and_meaning", "later_frc_withdrawal_found"),
            "verdict": ("verdict",),
        }
        for name, path in mutations.items():
            planted = copy.deepcopy(record)
            if name == "numeric":
                planted[path[0]][path[1]] = not planted[path[0]][path[1]]
            elif name == "null":
                planted[path[0]][path[1]] = []
            elif name == "withdrawal":
                planted[path[0]][path[1]] = False
            else:
                planted[path[0]] = "PASS_BUILD"
            plants[name] = bool(mismatches(planted))
        if not all(plants.values()):
            print(f"POST-UPDATE AUDIT CHECKER MISSED PLANT: {plants}")
            return 1

    result = {
        "status": "GREEN",
        "claims_checked": 5,
        "plants": plants,
        "all_plants_red": all(plants.values()) if plants else None,
    }
    (OUT / "postupdate-audit-check.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
