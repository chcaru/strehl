#!/usr/bin/env python3
"""Verify the M169 comparator audit from text only.

This verifier deliberately opens no candidate, comparator, capture, or holdout
pixel. It checks frozen source hashes, quoted authority anchors, the §3.1 axis
count, the structured audit, and the report. Its negative controls prove that
missing authority text, axis drift, and a silently promoted candidate are all
rejected.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "docs/proposals/2026-08-sota-path.md"
SCORECARD_PATH = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
M157_PATH = ROOT / "docs/research/M157-comparator-viability.md"
M161_PATH = ROOT / "docs/research/M161-m3-ratification.md"
M164_PATH = ROOT / "docs/research/M164-gx-sota-claim.md"
M169_M3_PATH = ROOT / "docs/research/M169-m3-veil.md"
REPORT_PATH = ROOT / "docs/research/M169-comparator-requirement-audit.md"
AUDIT_PATH = Path(__file__).with_name("audit.json")

EXPECTED_HASHES = {
    "plan": "72f8257918e929acb3f50c4606a4a7a73a44594492f040b4fcf196072e6a0b94",
    "scorecard": "cf91ec9afcaa4487a7ad1718a6c1ff9b6d2843b5869861606aaad46ec99331f1",
    "m157_prior_audit": "14660adc46e1d253e7e9646245708e789cd1cb4e1ba96312b424db1742e08c7e",
    "m161_m3_ratification": "3da41f80a05a9d1f91b35f03aa72ef1dece1d7252d21da8cc0ce5313d725b58e",
    "m164_gx_ruling": "59d56ffeae5156d9afd046e864efacc8dba45ef455487bd5317000f2bca0fde8",
    "m169_m3_commissioning": "d83eab7a42670eef54554e0638eb3cc27df48445cd34fb93f4f51e01d3869cb1",
}

PLAN_ANCHORS = (
    "SOTA = a pre-registered scorecard, versus named comparators, on axes with\n"
    "commissioned instruments.",
    "licensed Zerene (PMax *and* DMap",
    "DMap has never rendered here and is A5's true comparator",
    "the fork rebuilt at its best-known build",
    "Helicon if obtainable",
    "no occlusion veil above [bar] (halo instrument at full reach)",
    "An open-source stacker is a useful foreign arm and repairs a real\n"
    "provenance defect, but it clears **no** blocker.",
)

SCORECARD_ANCHORS = (
    "The required set is exactly licensed Zerene Stacker PMax, licensed Zerene "
    "Stacker DMap, and a fresh fork rebuild",
    "If any required arm — Zerene PMax, Zerene DMap, or the fresh "
    "commit-pinned best-known-source fork rebuild — cannot produce a linear "
    "output that passes §1.3",
    "the named-comparator requirement is unmet and the dependent comparative "
    "axes remain `UNMEASURED`",
    "**SCORECARD ADDITION — UNRATIFIED. This rule is authored here and is not "
    "traceable to the owner's plan.**",
    "p99(a_e)` no worse than the M1-qualified comparator envelope in every scope",
)

EXPECTED_CANDIDATES = {
    "Enfuse / Hugin",
    "PetteriAimonen/focus-stack",
    "ImageJ/Fiji Extended Depth of Field",
    "ShineStacker",
    "OpenCV-based stackers as a class",
    "Stackaroni",
    "z-stackr",
    "PICOLAY",
    "CombineZP",
    "ChimpStackr",
}

EXPECTED_DIRECT_D = [f"M{i}" for i in range(1, 8)]
EXPECTED_SEMANTIC = [f"M{i}" for i in range(1, 8)] + ["M11"]
EXPECTED_MINIMUM = {
    "exact_hashed_common_input_tiff_bytes",
    "native_size_16_bit_linear_tiff_output",
    "section_1_3_33_step_ramp_pass",
    "zero_development_instructions_in_files_and_sidecars",
    "no_output_tone_sharpen_denoise_white_balance_or_resize",
    "native_scale_and_at_least_99_percent_common_overlap",
    "frequency_metrics_never_resample_output",
    "input_only_geometry_evidence_with_registered_residual_limits",
    "at_least_80_percent_and_metric_minimum_sites_survive_identically",
    "differential_site_attrition_at_most_2_percentage_points",
    "frozen_version_binary_hash_settings_and_output_hashes",
    "fixed_settings_without_per_subject_tuning",
}


class AuditFailure(RuntimeError):
    """A deterministic audit assertion failed."""


class Checks:
    def __init__(self) -> None:
        self.count = 0

    def require(self, condition: bool, message: str) -> None:
        self.count += 1
        if not condition:
            raise AuditFailure(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("> "):
            line = stripped[2:]
        lines.append(line)
    return " ".join("\n".join(lines).split())


def readiness_rows(scorecard: str) -> dict[str, str]:
    start = scorecard.index("### 3.1 Measurement readiness as of v1.10")
    end = scorecard.index("### 3.2 Closed program decision gates", start)
    rows: dict[str, str] = {}
    for line in scorecard[start:end].splitlines():
        if not line.startswith("| M"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0][1:].isdigit():
            rows[cells[0]] = line
    return rows


def validate(
    plan: str,
    scorecard: str,
    m161: str,
    m169_m3: str,
    audit: dict[str, Any],
    report: str,
    *,
    check_hashes: bool,
) -> int:
    checks = Checks()

    if check_hashes:
        source_paths = {
            "plan": PLAN_PATH,
            "scorecard": SCORECARD_PATH,
            "m157_prior_audit": M157_PATH,
            "m161_m3_ratification": M161_PATH,
            "m164_gx_ruling": M164_PATH,
            "m169_m3_commissioning": M169_M3_PATH,
        }
        for key, path in source_paths.items():
            actual = sha256(path)
            checks.require(actual == EXPECTED_HASHES[key], f"{key} hash drift: {actual}")
            checks.require(
                audit["source_snapshot"][key]["sha256"] == actual,
                f"audit.json has stale {key} hash",
            )

    normalized_plan = normalized(plan)
    normalized_scorecard = normalized(scorecard)
    for anchor in PLAN_ANCHORS:
        checks.require(normalized(anchor) in normalized_plan, f"missing plan anchor: {anchor}")
    for anchor in SCORECARD_ANCHORS:
        checks.require(
            normalized(anchor) in normalized_scorecard,
            f"missing scorecard anchor: {anchor}",
        )
    normalized_m161 = normalized(m161)
    checks.require(
        "`[bar] = 5%` of the independently selected local source step."
        in normalized_m161,
        "M161 5% ratification anchor missing",
    )
    checks.require(
        "The literal publication gate is `max_e max(h_e,v_e) <= 0.05`"
        in normalized_m161,
        "M161 literal-maximum anchor missing",
    )
    normalized_m169_m3 = normalized(m169_m3)
    checks.require(
        "**Instrument verdict: BATTERY COMMISSIONED.**" in normalized_m169_m3,
        "M169 commissioning verdict anchor missing",
    )
    checks.require(
        "All **21/21** v3 assertions are true" in normalized_m169_m3,
        "M169 21/21 anchor missing",
    )

    rows = readiness_rows(scorecard)
    checks.require(set(rows) == {f"M{i}" for i in range(1, 13)}, "§3.1 must contain M1-M12")
    direct_d = [axis for axis, row in rows.items() if "(d)" in row.split("|")[2]]
    checks.require(direct_d == EXPECTED_DIRECT_D, f"literal (d) axes drifted: {direct_d}")
    checks.require("(d)" not in rows["M9"], "M9 must not be counted as a literal (d) axis")
    checks.require(
        "required common-input comparator set" in rows["M3"],
        "M3 scorecard comparator blocker anchor missing",
    )
    checks.require(
        "required common-input comparator outputs" in rows["M11"],
        "M11 semantic comparator dependency missing",
    )

    checks.require(audit["schema_version"] == 1, "unexpected audit schema")
    checks.require(audit["pixel_files_opened"] == 0, "audit must remain pixel-free")
    ruling = audit["ruling"]
    checks.require(ruling["named_portfolio_traceable_to_plan"] is True, "portfolio ruling drift")
    checks.require(
        ruling["universal_all_three_conjunction_traceable_to_plan"] is False,
        "universal-conjunction ruling drift",
    )
    checks.require(
        ruling["m3_comparator_envelope_traceable_to_plan"] is False,
        "M3 authority ruling drift",
    )
    checks.require(ruling["m3_plan_bar_is_absolute"] is True, "M3 plan-bar ruling drift")
    checks.require(
        ruling["current_whole_product_sota_definition_is_comparative"] is True,
        "SOTA framing ruling drift",
    )
    checks.require(ruling["free_comparator_currently_admitted"] == [], "no free arm is admitted")

    checks.require(
        set(audit["technical_minimum"]) == EXPECTED_MINIMUM,
        "technical minimum changed",
    )
    candidates = {row["name"]: row for row in audit["candidates"]}
    checks.require(set(candidates) == EXPECTED_CANDIDATES, "candidate matrix incomplete")
    checks.require(
        candidates["Enfuse / Hugin"]["status"] == "TECHNICALLY_PLAUSIBLE_UNADMITTED",
        "Enfuse must not be silently promoted",
    )
    checks.require(
        all(row["status"] != "QUALIFIED" for row in candidates.values()),
        "a free comparator was marked QUALIFIED without a witness",
    )
    for name in ("PetteriAimonen/focus-stack", "Stackaroni", "z-stackr", "PICOLAY"):
        checks.require(
            candidates[name]["status"].startswith("DISQUALIFIED"),
            f"{name} must retain its linear-output disqualification",
        )

    ledger = audit["axis_ledger"]
    checks.require(ledger["literal_blocker_d"] == EXPECTED_DIRECT_D, "JSON literal axes drift")
    checks.require(
        ledger["direct_semantic_comparator_dependency"] == EXPECTED_SEMANTIC,
        "JSON semantic axes drift",
    )
    checks.require(
        ledger["m9"]
        == "CURRENT_ROUTE_TRANSITIVE_THROUGH_M1_TRUTH_NOT_INTRINSIC_COMPARATOR_DEPENDENCY",
        "M9 distinction drift",
    )
    checks.require(
        ledger["free_arm_axes_unblocked_under_current_plan"] == [],
        "plan says a free foreign arm clears no blocker",
    )
    checks.require(
        ledger["technical_limb_axes_if_owner_authorizes_substitution"] == EXPECTED_SEMANTIC,
        "substitution axis list drift",
    )

    lead = (
        "SCORECARD EXCEEDS PLAN: it made PMax, DMap, and the fork an axis-blind "
        "all-or-nothing gate."
    )
    checks.require(lead in report, "report lead line missing")
    for heading in (
        "## 1. What the plan requires",
        "## 2. The load-bearing comparator contract",
        "## 3. Free-stackers audit",
        "## 4. Axis consequences and admission cost",
        "## 5. What is and is not unique about Zerene",
        "## 6. Can reference truth replace comparison?",
    ):
        checks.require(heading in report, f"report section missing: {heading}")
    checks.require("INFERRED BY READING" in report, "evidence label missing")
    checks.require("VERIFIED BY RUNNING" in report, "execution label missing")
    checks.require("NO SCORE" in report, "report must preserve the no-score boundary")
    checks.require("0 of 7" in report and "0 of 8" in report, "M164 propagation quote missing")
    for name in EXPECTED_CANDIDATES:
        checks.require(name in report, f"candidate absent from report: {name}")

    return checks.count


def expect_rejected(
    name: str,
    plan: str,
    scorecard: str,
    m161: str,
    m169_m3: str,
    audit: dict[str, Any],
    report: str,
) -> None:
    try:
        validate(
            plan,
            scorecard,
            m161,
            m169_m3,
            audit,
            report,
            check_hashes=False,
        )
    except (AuditFailure, KeyError, ValueError):
        return
    raise AuditFailure(f"negative control was not rejected: {name}")


def main() -> int:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    scorecard = SCORECARD_PATH.read_text(encoding="utf-8")
    m161 = M161_PATH.read_text(encoding="utf-8")
    m169_m3 = M169_M3_PATH.read_text(encoding="utf-8")
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    report = REPORT_PATH.read_text(encoding="utf-8")

    count = validate(
        plan,
        scorecard,
        m161,
        m169_m3,
        audit,
        report,
        check_hashes=True,
    )

    bad_plan = plan.replace(
        "SOTA = a pre-registered scorecard",
        "SOTA = an unspecified scorecard",
        1,
    )
    expect_rejected(
        "missing plan authority",
        bad_plan,
        scorecard,
        m161,
        m169_m3,
        audit,
        report,
    )

    bad_scorecard = scorecard.replace(
        "| M7 | **(b)(c)(d)** |",
        "| M7 | **(b)(c)** |",
        1,
    )
    expect_rejected(
        "literal axis-count drift",
        plan,
        bad_scorecard,
        m161,
        m169_m3,
        audit,
        report,
    )

    promoted = copy.deepcopy(audit)
    next(row for row in promoted["candidates"] if row["name"] == "Enfuse / Hugin")[
        "status"
    ] = "QUALIFIED"
    expect_rejected(
        "unwitnessed comparator promotion",
        plan,
        scorecard,
        m161,
        m169_m3,
        promoted,
        report,
    )

    bad_axes = copy.deepcopy(audit)
    bad_axes["axis_ledger"]["literal_blocker_d"].append("M9")
    expect_rejected(
        "M9 direct/transitive collapse",
        plan,
        scorecard,
        m161,
        m169_m3,
        bad_axes,
        report,
    )

    missing_candidate = copy.deepcopy(audit)
    missing_candidate["candidates"] = missing_candidate["candidates"][:-1]
    expect_rejected(
        "candidate matrix truncation",
        plan,
        scorecard,
        m161,
        m169_m3,
        missing_candidate,
        report,
    )

    bad_m161 = m161.replace(
        "`[bar] = 5%` of the independently selected local source step.",
        "`[bar] = unspecified`.",
        1,
    )
    expect_rejected(
        "M3 ratification drift",
        plan,
        scorecard,
        bad_m161,
        m169_m3,
        audit,
        report,
    )

    print(f"PASS: {count}/{count} positive assertions")
    print("PASS: 6/6 negative controls rejected")
    print("PASS: text-only audit; opened 0 pixel files")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditFailure, KeyError, ValueError, FileNotFoundError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
