from __future__ import annotations

import argparse
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REPORT = REPO / "docs" / "research" / "M131-cand2-ruling.md"
OPENING = "**VERDICT: Candidate 2 DOES NOT CLEAR blocker (a).**"
HEADINGS = (
    "## Rule-40 prior-art search",
    "## Killer 1 — synthetic, signal-linear optical arms",
    "## Killer 2 — can Hotelling \\(d'^2\\) license comparative detail?",
    "## Killer 3 — confirmation-pair confounds",
    "## Flat-ROI control",
    "## Candidate 2 against the M55 acceptance battery",
    "## What I did not establish",
)


def read_json(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def check(output: Path) -> int:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    report = REPORT.read_text(encoding="utf-8")
    flat = read_json("flat-control.json")
    m55 = read_json("m55-audit.json")
    synthetic = read_json("synthetic-choice-audit.json")
    null = read_json("null-rechoice.json")
    metadata = read_json("capture-metadata-audit.json")
    focus = read_json("focus-coverage-audit.json")
    capture = read_json("capture-admissibility.json")
    before = read_json("input-inventory-before.json")
    after = read_json("input-inventory-after.json")

    checks = []

    def add(name: str, passed: bool, detail=None) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add("exact opening verdict", report.startswith(OPENING + "\n"))
    positions = [report.find(heading) for heading in HEADINGS]
    add(
        "required headings present and ordered",
        all(position >= 0 for position in positions) and positions == sorted(positions),
        positions,
    )
    add(
        "what-I-did-not-establish is final H2",
        positions[-1] == report.rfind("\n## ") + 1,
    )
    add("flat control fails", flat["verdict"] == "FAIL")
    add(
        "flat control numeric 16 of 16",
        flat["flat_gate"]["numeric_rows"] == 16
        and flat["flat_gate"]["null_d2"]["n"] == 16,
    )
    add("flat power control passes", flat["power_control"]["passed"])
    add(
        "flat wrong-answer mutation caught",
        flat["planted_wrong_answer"]["caught"],
    )
    add(
        "M55 B0 fails all ten fields",
        not m55["candidate_2_interface"]["m55_b0"]["passed"]
        and len(m55["candidate_2_interface"]["m55_b0"]["missing"]) == 10,
    )
    add(
        "M55 class swap exact",
        m55["class_swap_test"]["exact_at_float_precision"],
    )
    add(
        "M55 power and passability demonstrated",
        m55["m55_power"]["pr27_passability_met"]
        and m55["m55_power"]["pr28_known_bad_power_met"]
        and m55["m55_power"]["all_property_tests_passed"],
    )
    add(
        "synthetic direction robust",
        synthetic["all_registered_choice_directions_pass"],
    )
    add(
        "synthetic failure self-test passes",
        synthetic["planted_failure_self_test"]["passed"],
    )
    add("balanced null includes unity", null["unity_in_ci95"])
    add(
        "capture counts and EXIF histograms match",
        metadata["checks"]["all_six_counts_match"]
        and metadata["checks"]["all_three_focus_histograms_match"],
    )
    add(
        "all slide stacks have IBIS on",
        metadata["checks"]["all_six_stacks_ibis_on"],
    )
    add(
        "focus coverage is exactly 63 of 64",
        capture["gates"]["image_coverage"][
            "qualifying_sites_in_both_stacks_and_metrics_at_1p05"
        ]
        == 63,
    )
    add(
        "no measured tail peaks",
        all(
            focus["stacks"][stack][metric]["peaks_in_tail_bucket"] == 0
            for stack in ("tilted-sw4", "tilted-sw10")
            for metric in ("tenengrad", "laplacian")
        ),
    )
    add(
        "task and geometry gates fail",
        not capture["gates"]["task_and_streams"]["passed"]
        and not capture["gates"]["ibis_and_geometry"]["passed"],
    )
    add(
        "capture trees unchanged",
        before["roots"] == after["roots"],
    )

    required_strings = (
        "0.2779204536",
        "2.4627494970",
        "0.0030320 +/- 0.0005553 SE",
        "0.1108` to `9.0270",
        "63 of 64",
        "8.6621 px",
        "12.0952 px",
        "candidate_status: DEAD",
    )
    missing_strings = [value for value in required_strings if value not in report]
    add("report contains deciding values", not missing_strings, missing_strings)

    failures = [row for row in checks if not row["passed"]]
    record = {
        "protocol": "M131-final-check-v1",
        "checks": checks,
        "passed": not failures,
        "failures": failures,
    }
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"checks={len(checks)} failures={len(failures)}")
    for failure in failures:
        print(f"FAIL: {failure['name']} {failure['detail']}")
    return 0 if not failures else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "check-result.json",
    )
    args = parser.parse_args()
    return check(args.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
