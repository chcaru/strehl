"""Fail-closed M3 score preflight under the current no-host-lock policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / "out" / "measurement-verdict.json"
FEASIBILITY = HERE / "out" / "capture-feasibility.json"
FULL_COMMISSION = HERE / "out" / "commission-v2.json"
ANCHORED_CONTROLS = HERE / "out" / "anchored-controls.json"
SCORECARD = REPO / "docs" / "proposals" / "2026-09-sota-scorecard.md"
REQUIRED_PACKAGES = {
    "common-input": HERE / "packages" / "INPUT-MANIFEST.json",
    "strehl": HERE / "packages" / "strehl" / "manifest.json",
    "fork": HERE / "packages" / "fork" / "manifest.json",
    "zerene-pmax": HERE / "packages" / "zerene-pmax" / "manifest.json",
    "zerene-dmap": HERE / "packages" / "zerene-dmap" / "manifest.json",
}
ABSOLUTE_LIMB_PACKAGES = {"common-input", "strehl"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    feasibility = read_json(FEASIBILITY)
    commission = read_json(FULL_COMMISSION)
    controls = read_json(ANCHORED_CONTROLS)
    scorecard = SCORECARD.read_text(encoding="utf-8")
    m1_dependency_anchor = (
        "M3 remains `UNMEASURED_COMPARATOR_QUALIFICATION` until M1 admits the"
    )
    absolute_anchor = (
        "The candidate must satisfy every bar both on each of the four "
        "capture populations and"
    )
    comparator_anchor = (
        "Strehl's value must be `<=` that reference in every scope."
    )
    for name, anchor in {
        "M1 dependency": m1_dependency_anchor,
        "absolute candidate": absolute_anchor,
        "comparator": comparator_anchor,
    }.items():
        if scorecard.count(anchor) != 1:
            raise RuntimeError(
                f"M3 scorecard {name} anchor did not occur exactly once"
            )

    prerequisites = {
        "capture_feasibility": feasibility["verdict"] == "PASS",
        "full_m161_v2_commissioning": commission["verdict"] == "PASS",
        "line_anchored_controls": controls["verdict"] == "PASS",
    }

    package_state = {
        name: {
            "path": str(path),
            "exists": path.is_file(),
            "required_for": (
                "absolute_candidate_limb"
                if name in ABSOLUTE_LIMB_PACKAGES
                else "full_axis_comparator_limb"
            ),
        }
        for name, path in REQUIRED_PACKAGES.items()
    }
    blockers: list[dict[str, Any]] = []
    if not prerequisites["capture_feasibility"]:
        blockers.append(
            {
                "code": "UNMEASURED_CAPTURE_INADEQUATE",
                "evidence": str(FEASIBILITY),
            }
        )
    if not prerequisites["full_m161_v2_commissioning"]:
        blockers.append(
            {
                "code": "NOT_ADMITTED_COMMISSIONING_FAILED",
                "failed_assertions": commission["failed_assertions"],
                "evidence": str(FULL_COMMISSION),
            }
        )
    if not prerequisites["line_anchored_controls"]:
        blockers.append(
            {
                "code": "REQUIRED_CONTROL_FAILED",
                "evidence": str(ANCHORED_CONTROLS),
            }
        )
    blockers.extend(
        [
        {
            "code": (
                "COMMON_INPUT_MANIFEST_ABSENT"
                if name == "common-input"
                else "REQUIRED_PRODUCT_PACKAGE_ABSENT"
            ),
            "product": name,
            "path": row["path"],
            "scope": row["required_for"],
        }
        for name, row in package_state.items()
        if not row["exists"]
        ]
    )
    blockers.append(
        {
            "code": "PROFILE_BUILDER_INPUT_ONLY_WARP_EVIDENCE_ABSENT",
            "scope": "absolute_candidate_limb",
            "evidence": (
                "docs/proposals/2026-09-sota-scorecard.md unique M3 "
                "Definition status anchor"
            ),
        }
    )
    blockers.append(
        {
            "code": "M1_QUALIFIED_COMPARATOR_ENVELOPE_ABSENT",
            "scope": "full_axis_comparator_limb",
            "evidence": (
                "docs/proposals/2026-09-sota-scorecard.md unique M3 "
                "comparator-clause anchor"
            ),
        }
    )
    subject_counts = feasibility["selected_site_counts"]
    result = {
        "schema": "m169-m3-measurement-verdict-v2",
        "axis_contract": {
            "kind": "CONJUNCTIVE_ABSOLUTE_AND_COMPARATIVE",
            "absolute_candidate_limb": (
                "all absolute bars pass per capture and pooled"
            ),
            "comparator_limb": (
                "strehl p99(a_e) is no worse than the required "
                "M1-qualified comparator envelope in every scope"
            ),
            "missing_comparator_effect": (
                "UNMEASURED_COMPARATOR_QUALIFICATION"
            ),
            "absolute_candidate_result_is_full_axis_score": False,
        },
        "bar": {
            "statistic": "maximum over frozen sites of max(h_e,v_e)",
            "maximum": 0.05,
            "changed": False,
        },
        "capture_feasibility": feasibility["verdict"],
        "recommissioning": {
            "full_m161_v2": commission["verdict"],
            "line_anchored_required_controls": controls["verdict"],
            "failed_assertions": commission["failed_assertions"],
        },
        "host_policy": {
            "exclusive_host_lock": False,
            "effect": "not a blocker; deterministic correctness work proceeded",
            "absolute_timing": "QUARANTINED_AND_NOT_REPORTED",
        },
        "denominator": int(feasibility["selected_site_count"]),
        "subjects": subject_counts,
        "required_packages": package_state,
        "blockers": blockers,
        "score_attempted": False,
        "score": None,
        "confidence_interval": "NO CI",
        "pixel_files_opened_by_m169": 0,
        "verdict": (
            "NOT_ADMITTED_COMMISSIONING_FAILED"
            if not prerequisites["full_m161_v2_commissioning"]
            else (
                "UNMEASURED_COMPARATOR_QUALIFICATION"
                if blockers
                else "READY_FOR_ONE_SHOT_SCORE"
            )
        ),
    }
    write_json(OUT, result)
    print(result["verdict"])
    print("denominator=%d" % result["denominator"])
    print(
        "subjects="
        + ",".join(
            f"{name}:{count}" for name, count in sorted(subject_counts.items())
        )
    )
    print("score=NO SCORE")
    print("confidence_interval=NO CI")
    for blocker in blockers:
        print("BLOCKER " + json.dumps(blocker, sort_keys=True))
    if result["verdict"] == "NOT_ADMITTED_COMMISSIONING_FAILED":
        return 5
    return 4 if blockers else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
