"""Independently check report claims against pre-verdict measurement outputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
REPO = ROOT.parents[1]
REPORT = REPO / "docs" / "research" / "M-PHASE0-ASTIG.md"
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def record_named(reduction: dict, name: str) -> dict:
    rows = [
        row
        for row in reduction["records"]
        if row["stack"]["name"] == name
    ]
    if len(rows) != 1:
        raise ValueError(f"expected exactly one {name} record")
    return rows[0]


def outer(record: dict) -> dict:
    rows = [row for row in record["radii"] if row["radius"] == 0.90]
    if len(rows) != 1:
        raise ValueError("expected exactly one outer-radius row")
    return rows[0]


def claim_section(text: str, claim: str) -> str:
    marker = f"<!-- claim:{claim} -->"
    start = text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    next_marker = text.find("<!-- claim:", start)
    return text[start:] if next_marker < 0 else text[start:next_marker]


def expected_values() -> dict:
    primary = load(OUT / "real-primary.json")
    commission = load(OUT / "commission.json")
    verdict_commission = load(OUT / "verdict-commission.json")
    loader = load(OUT / "loader-check.json")
    inventory = load(OUT / "capture-inventory.json")
    setup1 = record_named(primary, "grid1-sw4")
    setup2 = record_named(primary, "grid2-sw4")
    outer1 = outer(setup1)
    outer2 = outer(setup2)
    invalid_widths = []
    for tile in setup1["tiles"]:
        if (
            tile["radius"] == 0.90
            and tile["sector"] != "centre"
            and not tile["valid_for_map"]
        ):
            interval = tile["estimate"]["bootstrap"]
            invalid_widths.append(
                max(interval["zx"]["width95"], interval["zy"]["width95"])
            )
    p1 = next(
        row for row in commission["records"] if row["id"] == "P1-known-split"
    )
    p7 = next(
        row
        for row in commission["records"]
        if row["id"] == "P7-external-predicate"
    )
    sensitivity_paths = [
        OUT / f"sensitivity-{name}.json" for name in SENSITIVITIES
    ]
    sensitivity_data = {
        name: load(OUT / f"sensitivity-{name}.json")
        for name in ("tile256", "xminus2")
    }
    capture_counts = {"grid": 0, "aperture": 0, "flat-control": 0}
    for row in inventory["records"]:
        capture_counts[row["stack"]["role"]] += len(row["inventory"]["files"])

    sampling = {}
    for setup in ("grid1", "grid2"):
        fine = record_named(primary, f"{setup}-sw4")
        coarse = record_named(primary, f"{setup}-sw10")
        fine_slope = fine["field_geometry"]["plane"][
            "slope_magnitude_frames_per_field"
        ]
        coarse_slope = coarse["field_geometry"]["plane"][
            "slope_magnitude_frames_per_field"
        ]
        ratio = fine_slope / coarse_slope
        sampling[setup] = {
            "ratio": ratio,
            "equivalent_outer": outer(coarse)["delta"] * ratio,
        }

    sensitivity_pairs = {}
    for name, reduction in sensitivity_data.items():
        pair = reduction["primary_pair"]
        sensitivity_pairs[name] = {
            "D4": pair["D4_abs_frames"],
            "lo": pair["signed_bootstrap"]["lo95"],
            "hi": pair["signed_bootstrap"]["hi95"],
        }
    return {
        "verdict": (
            "NOT ROBUST"
            if min(outer1["valid_sector_count"], outer2["valid_sector_count"]) < 3
            else None
        ),
        "primary_pair_invalid": primary["primary_pair"]["valid"] is False,
        "setup1_count": outer1["valid_sector_count"],
        "setup2_count": outer2["valid_sector_count"],
        "invalid_widths": invalid_widths,
        "grid2_delta": outer2["delta"],
        "grid2_lo": outer2["bootstrap"]["lo95"],
        "grid2_hi": outer2["bootstrap"]["hi95"],
        "estimator_tally": commission["tally"],
        "full_effect": p1["clean"]["estimator_full_effect_mean"],
        "external_split": p7["clean"]["split"],
        "loader_tally": loader["tally"],
        "verdict_tally": verdict_commission["tally"],
        "sensitivity_count": sum(path.exists() for path in sensitivity_paths),
        "sensitivity_total": len(sensitivity_paths),
        "sensitivity_pairs": sensitivity_pairs,
        "sampling": sampling,
        "capture_snapshot_unchanged": inventory["capture_snapshot_unchanged"],
        "capture_counts": capture_counts,
    }


def check_report(text: str, expected: dict) -> list[dict]:
    def squash(value: str) -> str:
        return " ".join(value.split())

    verdict = squash(claim_section(text, "verdict"))
    decisive = squash(claim_section(text, "decisive-gate"))
    commission = squash(claim_section(text, "commission"))
    captures = squash(claim_section(text, "capture-accounting"))
    grid2 = squash(claim_section(text, "grid2-diagnostic"))
    sensitivities = squash(claim_section(text, "sensitivities"))
    rust = squash(claim_section(text, "rust"))

    estimator = expected["estimator_tally"]
    loader = expected["loader_tally"]
    verdict_tally = expected["verdict_tally"]
    checks = [
        (
            "verdict",
            expected["verdict"] is not None
            and f"**{expected['verdict']}.**" in verdict,
            "verdict claim must follow the raw sector count and fixed threshold",
        ),
        (
            "decisive-counts",
            (
                f"**{expected['setup1_count']} valid outer sectors out of 4 "
                "in `grid1-sw4`**"
            )
            in decisive
            and f"`grid2-sw4` has {expected['setup2_count']}." in decisive
            and "minimum is **3 valid sectors in each primary setup**" in decisive
            and expected["primary_pair_invalid"]
            and "`D4` is therefore **not estimable**" in decisive,
            "primary sector counts and D4 refusal must match raw reduction",
        ),
        (
            "arm-widths",
            all(f"**{value:.6f}" in decisive for value in expected["invalid_widths"]),
            "rejected arm interval widths must match raw reduction",
        ),
        (
            "capture-accounting",
            expected["capture_snapshot_unchanged"]
            and (
                f"{sum(expected['capture_counts'].values())} registered ARWs "
                f"({expected['capture_counts']['grid']} grid, "
                f"{expected['capture_counts']['aperture']} fabric, and "
                f"{expected['capture_counts']['flat-control']} razor control)"
            )
            in captures
            and "before/after capture inventory was unchanged" in captures,
            "capture counts and read-only snapshot must match extraction inventory",
        ),
        (
            "grid2-diagnostic",
            f"**{expected['grid2_delta']:+.6f} frames**" in grid2
            and (
                f"**[{expected['grid2_lo']:+.6f}, "
                f"{expected['grid2_hi']:+.6f}]**"
            )
            in grid2,
            "non-decisive grid2 point and interval must match raw reduction",
        ),
        (
            "estimator-commissioning",
            f"**{estimator['clean_pass']} of {estimator['controls']} controls**"
            in commission
            and f"**{estimator['red']} of {estimator['plants']} named plants went RED**"
            in commission
            and f"**{expected['full_effect']:.6f} frames**" in commission
            and f"**{expected['external_split']:.6f}**" in commission,
            "estimator control tally and fixed readings must match commission.json",
        ),
        (
            "auxiliary-commissioning",
            loader["known_answer_pass"] == loader["known_answer_total"] == 2
            and loader["plants_red"] == loader["plants_total"] == 1
            and "reproduced 2/2 contracts" in commission
            and "padded-shape plant went RED" in commission
            and (
                f"**{verdict_tally['clean_pass']} of "
                f"{verdict_tally['controls']} gate controls passed and "
                f"{verdict_tally['red']} of {verdict_tally['plants']} "
                "disabling plants went RED**"
            )
            in commission,
            "loader and verdict-gate commissioning must match their outputs",
        ),
        (
            "sensitivities",
            expected["sensitivity_count"] == expected["sensitivity_total"] == 14
            and "**14 of 14 registered sensitivities**" in sensitivities,
            "all fourteen registered sensitivity outputs must exist and be reported",
        ),
        (
            "sensitivity-diagnostics",
            all(
                f"{row['D4']:.6f} frames" in sensitivities
                and (
                    f"[{row['lo']:+.6f}, {row['hi']:+.6f}]"
                    in sensitivities
                )
                for row in expected["sensitivity_pairs"].values()
            ),
            "valid sensitivity D4 diagnostics must match their raw reductions",
        ),
        (
            "sampling-diagnostics",
            (
                f"{expected['sampling']['grid1']['ratio']:.4f} and "
                f"{expected['sampling']['grid2']['ratio']:.4f}"
            )
            in sensitivities
            and (
                f"{expected['sampling']['grid1']['equivalent_outer']:.4f} and "
                f"{expected['sampling']['grid2']['equivalent_outer']:.4f}"
            )
            in sensitivities,
            "empirical slope ratios and rescaled coarse points must match primary data",
        ),
        (
            "rust-consequence",
            "**No Rust source changes.**" in rust
            and "`crates/strehl-core/src/focus.rs`" in rust
            and "`crates/strehl-core/src/pyramid.rs`" in rust
            and "`crates/strehl-cli/src/merge_cmd.rs`" in rust,
            "NOT ROBUST consequence must explicitly leave all three modules unchanged",
        ),
    ]
    return [
        {"id": check_id, "passed": bool(passed), "criterion": criterion}
        for check_id, passed, criterion in checks
    ]


def commission_checker(text: str, expected: dict) -> list[dict]:
    plants = (
        ("verdict", f"**{expected['verdict']}.**", "**KILL.**"),
        (
            "decisive-counts",
            f"**{expected['setup1_count']} valid outer sectors out of 4",
            "**4 valid outer sectors out of 4",
        ),
        (
            "arm-widths",
            f"**{expected['invalid_widths'][0]:.6f}",
            "**1.000000",
        ),
        (
            "capture-accounting",
            f"{sum(expected['capture_counts'].values())} registered ARWs",
            "999 registered ARWs",
        ),
        (
            "grid2-diagnostic",
            f"**{expected['grid2_delta']:+.6f} frames**",
            "**-1.051409 frames**",
        ),
        (
            "estimator-commissioning",
            (
                f"**{expected['estimator_tally']['clean_pass']} of "
                f"{expected['estimator_tally']['controls']} controls**"
            ),
            "**7 of 8 controls**",
        ),
        (
            "auxiliary-commissioning",
            "reproduced 2/2 contracts",
            "reproduced 1/2 contracts",
        ),
        (
            "sensitivities",
            "**14 of 14 registered sensitivities**",
            "**13 of 14 registered sensitivities**",
        ),
        (
            "sensitivity-diagnostics",
            (
                f"{expected['sensitivity_pairs']['tile256']['D4']:.6f} "
                "frames"
            ),
            "0.999999 frames",
        ),
        (
            "sampling-diagnostics",
            (
                f"{expected['sampling']['grid1']['ratio']:.4f} and "
                f"{expected['sampling']['grid2']['ratio']:.4f}"
            ),
            "9.9999 and 9.9999",
        ),
        (
            "rust-consequence",
            "**No Rust source changes.**",
            "**Rust source changes required.**",
        ),
    )
    records = []
    for check_id, old, new in plants:
        if text.count(old) != 1:
            raise ValueError(
                f"commissioning plant token for {check_id} occurs "
                f"{text.count(old)} times"
            )
        planted = text.replace(old, new, 1)
        rows = {row["id"]: row for row in check_report(planted, expected)}
        went_red = not rows[check_id]["passed"]
        records.append(
            {
                "id": check_id,
                "plant": f"replace {old!r} with {new!r}",
                "status": "RED" if went_red else "MISSED",
            }
        )
    return records


def main() -> None:
    text = REPORT.read_text(encoding="utf-8")
    expected = expected_values()
    plants = commission_checker(text, expected)
    checks = check_report(text, expected)
    passed = sum(row["passed"] for row in checks)
    red = sum(row["status"] == "RED" for row in plants)
    result = {
        "schema_version": 1,
        "role": "independent report-number checker and commissioning",
        "independence": (
            "recomputes claims from real-primary.json, commission.json, "
            "loader-check.json, verdict-commission.json, capture-inventory.json, "
            "selected sensitivity reductions, and all sensitivity-file existence; "
            "does not read verdict.json or import verdict.py"
        ),
        "actual_report": {
            "checks": len(checks),
            "passed": passed,
            "failed": len(checks) - passed,
            "records": checks,
        },
        "commissioning": {
            "plants": len(plants),
            "red": red,
            "missed": len(plants) - red,
            "records": plants,
        },
        "provenance": {
            "invocation": (
                "PYTHONIOENCODING=utf-8; "
                "python experiments\\M-PHASE0-ASTIG\\src\\report_check.py"
            ),
            "report_sha256": sha256(REPORT),
            "source_sha256": sha256(Path(__file__)),
            "input_sha256": {
                name: sha256(OUT / name)
                for name in (
                    "real-primary.json",
                    "commission.json",
                    "loader-check.json",
                    "verdict-commission.json",
                    "capture-inventory.json",
                )
            }
            | {
                f"sensitivity-{name}.json": sha256(
                    OUT / f"sensitivity-{name}.json"
                )
                for name in SENSITIVITIES
            },
        },
    }
    target = OUT / "report-check.json"
    target.write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"report: {passed}/{len(checks)} PASS; "
        f"checker plants: {red}/{len(plants)} RED"
    )
    print(f"wrote {target}")
    if passed != len(checks) or red != len(plants):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
