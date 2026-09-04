"""Audit the scoped GX claim against the governing SOTA documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PLAN = ROOT / "docs" / "proposals" / "2026-08-sota-path.md"
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
REPORT = ROOT / "docs" / "research" / "M164-gx-sota-claim.md"
OUTPUT = HERE / "audit.json"

PLAN_DEFINITION = (
    "SOTA = a pre-registered scorecard, versus named comparators, "
    "on axes with commissioned instruments."
)
PUBLICATION_GATES = ["M1", "M2", "M3", "M8", "M9", "M10", "M11"]
EXPLICIT_D = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
SEMANTIC_COMPARATOR = [
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "M7",
    "M11",
]
CLAIM = (
    "On the preregistered macro-subject population and licensed "
    "frequency-orientation cells for which the independent reference arm "
    "passed REFERENCE_INFORMATION_DOMINANCE, Strehl resolved more "
    "scene-linked detail, measured as greater recoverable covariance "
    "information about GX—the scene structure transmitted through the "
    "measured non-null passband common to the registered Sony FE 100mm F2.8 "
    "Macro GM OSS optical paths—than licensed Zerene Stacker PMax, licensed "
    "Zerene Stacker DMap, and the commit-pinned best-known-source fork and, "
    "when obtainable under the preregistration, licensed Helicon Focus "
    "methods A/B/C on identical inputs, without worse reference-relative "
    "attenuation, "
    "overshoot, phase error, or unexplained repeatable structure; this is a "
    "comparative claim about that camera, optic, reference path and licensed "
    "band, not a claim to recover absolute object detail removed by or "
    "artifacts shared through G, and not a claim about other optical "
    "configurations."
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def normalize(text: str) -> str:
    return " ".join(text.split())


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


def readiness_rows(scorecard: str) -> dict[str, dict[str, str]]:
    block = section(scorecard, "### 3.1 ", "### 3.2 ")
    rows: dict[str, dict[str, str]] = {}
    for line in block.splitlines():
        if not re.match(r"^\| M(?:[1-9]|1[0-2]) \|", line):
            continue
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(columns) != 3:
            raise ValueError(f"unexpected readiness row: {line}")
        rows[columns[0]] = {
            "class": columns[1],
            "description": columns[2],
        }
    return rows


def reported_claim(report: str) -> str:
    start = report.index("> **On the preregistered")
    lines: list[str] = []
    for line in report[start:].splitlines():
        if not line.startswith(">"):
            break
        lines.append(line.removeprefix("> ").strip())
    return normalize(" ".join(lines)).removeprefix("**").removesuffix("**")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--plant-defect", choices=("drop-m7",))
    arguments = parser.parse_args(argv)

    plan = PLAN.read_text(encoding="utf-8")
    scorecard = SCORECARD.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    if arguments.plant_defect == "drop-m7":
        scorecard = scorecard.replace(
            "| M7 | **(b)(c)(d)** |",
            "| M7 | **(b)(c)** |",
            1,
        )
    rows = readiness_rows(scorecard)
    explicit_d = [
        axis for axis, row in rows.items() if "(d)" in row["class"]
    ]
    semantic_comparator = list(explicit_d)
    if "required common-input comparator outputs" in rows["M11"][
        "description"
    ]:
        semantic_comparator.append("M11")

    normalized_plan = normalize(plan)
    normalized_scorecard = normalize(scorecard)
    checks = {
        "C1_plan_definition_is_present": PLAN_DEFINITION
        in normalized_plan,
        "C2_plan_end_state_requires_resolved_detail": (
            "resolves detail at or beyond the best shipping comparator"
            in normalized_plan
        ),
        "C3_scorecard_publication_gate_set_is_exact": (
            "The publication gates are exactly `M1`, `M2`, `M3`, `M8`, "
            "`M9`, `M10`, and `M11`"
            in normalized_scorecard
        ),
        "C4_exactly_seven_rows_explicitly_carry_d": len(explicit_d) == 7,
        "C5_explicit_d_rows_are_M1_through_M7": explicit_d == EXPLICIT_D,
        "C6_M11_has_untagged_semantic_comparator_dependency": (
            semantic_comparator == SEMANTIC_COMPARATOR
            and "M11" not in explicit_d
            and "required common-input comparator outputs"
            in rows["M11"]["description"]
        ),
        "C7_plan_reconciles_semantic_d_count_as_eight": (
            "`(d)` **8**" in normalized_plan
        ),
        "C8_GX_scope_removes_no_explicit_d_dependency": (
            explicit_d == EXPLICIT_D
        ),
        "C9_claim_names_required_comparators": all(
            text in CLAIM
            for text in (
                "licensed Zerene Stacker PMax",
                "licensed Zerene Stacker DMap",
                "commit-pinned best-known-source fork",
                "licensed Helicon Focus methods A/B/C",
            )
        ),
        "C10_claim_defines_GX_scope": all(
            text in CLAIM
            for text in (
                "recoverable covariance information about GX",
                "measured non-null passband common",
                "registered Sony FE 100mm F2.8 Macro GM OSS",
            )
        ),
        "C11_claim_disclaims_absolute_X": (
            "not a claim to recover absolute object detail" in CLAIM
            and "artifacts shared through G" in CLAIM
        ),
        "C12_report_contains_literal_claim": reported_claim(report) == CLAIM,
    }
    result: dict[str, Any] = {
        "schema": "m164-gx-sota-claim-audit-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "planted_defect": arguments.plant_defect,
        "claim": CLAIM,
        "plan_definition": PLAN_DEFINITION,
        "plan_publication_gates": PUBLICATION_GATES,
        "scorecard_section_3_1": {
            "explicit_blocker_d_axes": explicit_d,
            "explicit_blocker_d_count": len(explicit_d),
            "semantic_comparator_axes": semantic_comparator,
            "gx_removed_explicit_blocker_d_axes": [],
            "note": (
                "M11 is an additional semantic comparator dependency even "
                "though its class cell omits the literal (d) marker."
            ),
        },
        "competitor_claim_scope": {
            "finding": (
                "No named comparator or benchmark source in the verified "
                "evidence base validates absolute physical object truth X."
            ),
            "zerene": {
                "source": "https://zerenesystems.com/cms/stacker",
                "published_language": (
                    "Highest quality output images; preserves low contrast "
                    "detail and avoids stacking mush."
                ),
                "absolute_X_validation": False,
            },
            "helicon": {
                "source": (
                    "https://www.heliconsoft.com/focus/help/english/"
                    "HeliconFocus.html"
                ),
                "published_language": (
                    "Fully focused image by combining the sharpest areas."
                ),
                "absolute_X_validation": False,
            },
            "araujo_2023": {
                "source": "https://arxiv.org/abs/2311.17846",
                "published_language": (
                    "Uses pseudo ground truth computed with commercial "
                    "software and reports qualitative parity."
                ),
                "absolute_X_validation": False,
            },
            "mfifb_2020": {
                "source": "https://arxiv.org/abs/2005.01116",
                "published_language": (
                    "Benchmarks 30 algorithms on 105 image pairs with 20 "
                    "metrics."
                ),
                "absolute_X_validation": False,
            },
        },
        "checks": checks,
        "source": {
            "audit_py_sha256": digest(Path(__file__)),
            "plan_sha256": digest(PLAN),
            "scorecard_sha256": digest(SCORECARD),
            "report_sha256": digest(REPORT),
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    passed = sum(checks.values())
    print(
        f"{result['status']}: {passed}/{len(checks)} checks; "
        f"explicit_d={len(explicit_d)} "
        f"({','.join(explicit_d)}); "
        f"semantic_comparator={','.join(semantic_comparator)}; "
        "gx_removed=0"
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
