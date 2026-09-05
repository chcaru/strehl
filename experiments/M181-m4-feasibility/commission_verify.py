from __future__ import annotations

import copy
import json
from typing import Any, Callable

from verify import VerificationError, load_values, verify_values


Mutation = Callable[
    [dict[str, Any], dict[str, Any], dict[str, Any]], None
]


def exactly_one(rows: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any]:
    matches = [row for row in rows if row.get(key) == value]
    if len(matches) != 1:
        raise RuntimeError(
            f"mutation anchor {key}={value!r} occurs {len(matches)} times, not once"
        )
    return matches[0]


def mutate_source_freeze(
    _: dict[str, Any], probe: dict[str, Any], __: dict[str, Any]
) -> None:
    old = probe["frozen_dependencies"]["census_common.py"]
    if old.count("3") < 1:
        raise RuntimeError("source-freeze mutation anchor absent")
    probe["frozen_dependencies"]["census_common.py"] = "0" + old[1:]


def mutate_prohibited_path(
    inventory: dict[str, Any], _: dict[str, Any], __: dict[str, Any]
) -> None:
    row = exactly_one(inventory["stacks"], "stack_id", "medication-pill-cpl")
    row["path"] = (
        r"D:\personal\macro\requests\7-aperture-pairs\forbidden-sentinel"
    )


def mutate_inventory_denominator(
    inventory: dict[str, Any], _: dict[str, Any], __: dict[str, Any]
) -> None:
    inventory["arw_frame_count_excluding_prohibited"] += 1


def mutate_rig_audit(
    _: dict[str, Any], __: dict[str, Any], rig: dict[str, Any]
) -> None:
    row = exactly_one(rig["settings"]["FocalLength"], "value", 200)
    row["value"] = 100


def mutate_probe_partition(
    _: dict[str, Any], probe: dict[str, Any], __: dict[str, Any]
) -> None:
    row = exactly_one(probe["probes"], "unit_id", "score-medication-pill")
    labels = list(row["first_failure_counts"])
    if not labels:
        raise RuntimeError("probe partition mutation has no failure label")
    row["first_failure_counts"][labels[0]] += 1


def mutate_verdict(
    _: dict[str, Any], probe: dict[str, Any], __: dict[str, Any]
) -> None:
    old = probe["summary"]["capture_verdict"]
    probe["summary"]["capture_verdict"] = (
        "CAPTURE_READY"
        if old == "M4_RETAINED_BLOCKED_CAPTURE"
        else "M4_RETAINED_BLOCKED_CAPTURE"
    )


def mutate_inert(
    inventory: dict[str, Any],
    probe: dict[str, Any],
    rig: dict[str, Any],
) -> None:
    inventory["commissioning_inert_note"] = "unconsumed"
    probe["commissioning_inert_note"] = "unconsumed"
    rig["commissioning_inert_note"] = "unconsumed"


def main() -> int:
    baseline_inventory, baseline_probe, baseline_rig = load_values()
    baseline = verify_values(baseline_inventory, baseline_probe, baseline_rig)
    arms: list[tuple[str, Mutation, bool]] = [
        ("source-freeze", mutate_source_freeze, True),
        ("prohibited-path", mutate_prohibited_path, True),
        ("inventory-integrity", mutate_inventory_denominator, True),
        ("rig-audit", mutate_rig_audit, True),
        ("probe-accounting", mutate_probe_partition, True),
        ("verdict-reduction", mutate_verdict, True),
        ("inert", mutate_inert, False),
    ]
    killed = 0
    missed = 0
    inert_green = 0
    rows = []
    for name, mutate, should_fail in arms:
        inventory = copy.deepcopy(baseline_inventory)
        probe = copy.deepcopy(baseline_probe)
        rig = copy.deepcopy(baseline_rig)
        mutate(inventory, probe, rig)
        failed = False
        reason = None
        try:
            verify_values(inventory, probe, rig)
        except VerificationError as error:
            failed = True
            reason = str(error)
        if should_fail and failed:
            killed += 1
            status = "KILLED"
        elif should_fail:
            missed += 1
            status = "MISSED"
        elif failed:
            missed += 1
            status = "INERT_RED"
        else:
            inert_green += 1
            status = "INERT_GREEN"
        rows.append({"arm": name, "status": status, "reason": reason})
        print(f"{name}: {status}" + (f" ({reason})" if reason else ""))
    artifact = {
        "schema": "m181-verifier-commission-v1",
        "baseline_checks": baseline,
        "arms": rows,
        "mutation_arms_planted": 6,
        "mutation_arms_killed": killed,
        "mutation_arms_missed": missed,
        "inert_arms_run": 1,
        "inert_arms_green": inert_green,
        "accounted": killed + missed + inert_green,
        "expected_total": len(arms),
        "verdict": (
            "COMMISSIONED"
            if killed == 6
            and missed == 0
            and inert_green == 1
            and killed + missed + inert_green == len(arms)
            else "NOT_COMMISSIONED"
        ),
    }
    from probe_flats import OUT, write_json

    write_json(OUT / "commission.json", artifact)
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0 if artifact["verdict"] == "COMMISSIONED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
