from __future__ import annotations

import copy
import json
from typing import Any, Callable

from verify import VerificationError, load_values, verify_values


Mutation = Callable[
    [
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
        dict[str, Any],
    ],
    None,
]


def exactly_one(rows: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any]:
    matches = [row for row in rows if row.get(key) == value]
    if len(matches) != 1:
        raise RuntimeError(
            f"mutation anchor {key}={value!r} occurs {len(matches)} times, not once"
        )
    return matches[0]


def unique_anchor(value: dict[str, Any], anchor: str) -> None:
    count = json.dumps(value, sort_keys=True).count(anchor)
    if count != 1:
        raise RuntimeError(f"mutation anchor {anchor!r} occurs {count} times, not once")


def mutate_source_freeze(
    _: dict[str, Any],
    probe: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
) -> None:
    old = probe["frozen_dependencies"]["census_common.py"]
    if old.count("3") < 1:
        raise RuntimeError("source-freeze mutation anchor absent")
    probe["frozen_dependencies"]["census_common.py"] = "0" + old[1:]


def mutate_prohibited_path(
    inventory: dict[str, Any],
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
) -> None:
    row = exactly_one(inventory["stacks"], "stack_id", "medication-pill-cpl")
    row["path"] = r"D:\personal\macro\requests\7-aperture-pairs\forbidden-sentinel"


def mutate_inventory_denominator(
    inventory: dict[str, Any],
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
) -> None:
    inventory["arw_frame_count_excluding_prohibited"] += 1


def mutate_rig_audit(
    _: dict[str, Any],
    __: dict[str, Any],
    rig: dict[str, Any],
    ___: dict[str, Any],
) -> None:
    row = exactly_one(rig["settings"]["FocalLength"], "value", 200)
    row["value"] = 100


def mutate_probe_partition(
    _: dict[str, Any],
    probe: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
) -> None:
    row = exactly_one(probe["probes"], "unit_id", "score-medication-pill")
    labels = list(row["first_failure_counts"])
    if not labels:
        raise RuntimeError("probe partition mutation has no failure label")
    row["first_failure_counts"][labels[0]] += 1


def mutate_verdict(
    _: dict[str, Any],
    probe: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
) -> None:
    old = probe["summary"]["capture_verdict"]
    probe["summary"]["capture_verdict"] = (
        "CAPTURE_READY"
        if old == "M4_RETAINED_BLOCKED_CAPTURE"
        else "M4_RETAINED_BLOCKED_CAPTURE"
    )


def mutate_development_source(
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
    development: dict[str, Any],
) -> None:
    digest = development["method"]["m152_source_sha256"]["census.py"]
    unique_anchor(development, digest)
    development["method"]["m152_source_sha256"]["census.py"] = "0" + digest[1:]


def mutate_development_identity(
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
    development: dict[str, Any],
) -> None:
    unique_anchor(development, r"D:\\personal\\macro\\coffee-bubbles")
    if development["m152_coffee_reference"]["same_capture"] is not False:
        raise RuntimeError("development identity mutation anchor is not false")
    development["m152_coffee_reference"]["same_capture"] = True


def mutate_development_band(
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
    development: dict[str, Any],
) -> None:
    unique_anchor(development, "max_over_frame_ratio_max")
    development["term_results"]["band_20_60_native_px_over_temporal_noise_p99"][
        "max_over_frame_ratio_max"
    ] = 1.0


def mutate_development_signal(
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
    development: dict[str, Any],
) -> None:
    unique_anchor(development, "minimum_over_frames_and_tiles_sigma")
    development["term_results"]["median_signal_over_temporal_sigma"][
        "minimum_over_frames_and_tiles_sigma"
    ] = 9.999


def mutate_development_low_rail(
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
    development: dict[str, Any],
) -> None:
    unique_anchor(development, '"low_rail_fraction"')
    development["term_results"]["low_rail_fraction"][
        "maximum_over_frames_and_tiles"
    ] = 0.010001


def mutate_development_high_rail(
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
    development: dict[str, Any],
) -> None:
    unique_anchor(development, '"high_rail_fraction"')
    development["term_results"]["high_rail_fraction"][
        "maximum_over_frames_and_tiles"
    ] = 0.001001


def mutate_development_joint(
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
    development: dict[str, Any],
) -> None:
    unique_anchor(development, "DEVELOPMENT_FLAT_ELIGIBLE")
    if int(development["eligible_tile_count"]) != 1768:
        raise RuntimeError("development joint mutation anchor differs")
    development["eligible_tile_count"] = 99


def mutate_development_prohibited(
    _: dict[str, Any],
    __: dict[str, Any],
    ___: dict[str, Any],
    development: dict[str, Any],
) -> None:
    unique_anchor(development, '"prohibited_root_opened"')
    if development["prohibited_root_opened"] is not False:
        raise RuntimeError("development prohibited mutation anchor is not false")
    development["prohibited_root_opened"] = True


def mutate_inert(
    inventory: dict[str, Any],
    probe: dict[str, Any],
    rig: dict[str, Any],
    development: dict[str, Any],
) -> None:
    inventory["commissioning_inert_note"] = "unconsumed"
    probe["commissioning_inert_note"] = "unconsumed"
    rig["commissioning_inert_note"] = "unconsumed"
    development["commissioning_inert_note"] = "unconsumed"


def main() -> int:
    (
        baseline_inventory,
        baseline_probe,
        baseline_rig,
        baseline_development,
    ) = load_values()
    baseline = verify_values(
        baseline_inventory,
        baseline_probe,
        baseline_rig,
        baseline_development,
    )
    arms: list[tuple[str, Mutation, bool]] = [
        ("source-freeze", mutate_source_freeze, True),
        ("prohibited-path", mutate_prohibited_path, True),
        ("inventory-integrity", mutate_inventory_denominator, True),
        ("rig-audit", mutate_rig_audit, True),
        ("probe-accounting", mutate_probe_partition, True),
        ("verdict-reduction", mutate_verdict, True),
        ("development-source", mutate_development_source, True),
        ("development-identity", mutate_development_identity, True),
        ("development-band", mutate_development_band, True),
        ("development-signal", mutate_development_signal, True),
        ("development-low-rail", mutate_development_low_rail, True),
        ("development-high-rail", mutate_development_high_rail, True),
        ("development-joint", mutate_development_joint, True),
        ("development-prohibited", mutate_development_prohibited, True),
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
        development = copy.deepcopy(baseline_development)
        mutate(inventory, probe, rig, development)
        failed = False
        reason = None
        try:
            verify_values(inventory, probe, rig, development)
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
        "mutation_arms_planted": 14,
        "mutation_arms_killed": killed,
        "mutation_arms_missed": missed,
        "inert_arms_run": 1,
        "inert_arms_green": inert_green,
        "accounted": killed + missed + inert_green,
        "expected_total": len(arms),
        "verdict": (
            "COMMISSIONED"
            if killed == 14
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
