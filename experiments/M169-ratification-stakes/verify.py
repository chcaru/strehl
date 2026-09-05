#!/usr/bin/env python3
"""Verify the M169 ratification-stakes audit using text only."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = Path(__file__).with_name("audit.json")
REPORT_PATH = ROOT / "docs/research/M169-ratification-stakes.md"

SOURCE_PATHS = {
    "plan": ROOT / "docs/proposals/2026-08-sota-path.md",
    "scorecard": ROOT / "docs/proposals/2026-09-sota-scorecard.md",
    "m139_m12_campaign": ROOT / "docs/research/M139-m12-campaign.md",
    "m158_drift_audit": ROOT / "docs/research/M158-scorecard-drift.md",
    "m161_m3_ratification": ROOT / "docs/research/M161-m3-ratification.md",
    "m166_bar_definitions": ROOT / "docs/research/M166-bar-definition-repairs.md",
    "m169_comparator_audit": ROOT
    / "docs/research/M169-comparator-requirement-audit.md",
    "m169_m3_commissioning": ROOT / "docs/research/M169-m3-veil.md",
    "m175_fork_arm": ROOT / "docs/research/M175-fork-arm.md",
}

PINNED_GIT_SOURCES = {
    "m139_m12_campaign": "2ba256aa8c511ec83b4c0a99c5b988ad0752afc1",
}

EXPECTED_SOURCES = {
    "plan": (
        "72f8257918e929acb3f50c4606a4a7a73a44594492f040b4fcf196072e6a0b94",
        2780,
    ),
    "scorecard": (
        "405f3749f097104778ec11404eb432e53869ee9cfa6ef13bab4bc2cdbda7a696",
        2240,
    ),
    "m139_m12_campaign": (
        "9cff5b17c0129d8246b859689b30bf20747f67bae68b0217a9f3641378af0df7",
        268,
    ),
    "m158_drift_audit": (
        "129546e240072d79be665618b356f8a5ac3b93e5046182c47c97d09e23175ee2",
        800,
    ),
    "m161_m3_ratification": (
        "3da41f80a05a9d1f91b35f03aa72ef1dece1d7252d21da8cc0ce5313d725b58e",
        229,
    ),
    "m166_bar_definitions": (
        "b66bd24d9fad69c7e9629ac0dbb187e4c08b981e2479104220671eb06fea1cfd",
        587,
    ),
    "m169_comparator_audit": (
        "71f08bf819e74d0bf5f69a3957028d36c525ddb694d6f7cdb0b9de0e973a7b38",
        395,
    ),
    "m169_m3_commissioning": (
        "d83eab7a42670eef54554e0638eb3cc27df48445cd34fb93f4f51e01d3869cb1",
        403,
    ),
    "m175_fork_arm": (
        "a6b86e660f8cef2e46af5864f7236fdf3e58237a9a9679d4cc85444efbb9c61c",
        341,
    ),
}

PLAN_ANCHORS = (
    "SOTA = a pre-registered scorecard, versus named comparators, on axes with "
    "commissioned instruments.",
    "| Noise, flat/defocused ground | **Ahead, measured.**",
    "| Nothing — quotable now |",
    "| Highlight retention | **Ahead vs fork",
    "| Wire the census; B2 below |",
    "| Occlusion veil / aura |",
    "≥400 px clear-background captures; A2/C3 below",
    "| Fine detail ≥ 0.15 cyc/px |",
    "§30/§32/§33 captures; a licensed comparator; the D1 instrument.",
    "| Depth output | Absent from the field; unbuilt here",
    "| A5/C5 below |",
    "| Speed / memory | **Ahead, measured.**",
    "Hold the line (D5; D9 buys back the worker-cap tax first)",
    "licensed Zerene (PMax *and* DMap",
    "DMap has never rendered here and is A5's true comparator",
    "the fork rebuilt at its best-known build",
    "An open-source stacker is a useful foreign arm and repairs a real "
    "provenance defect, but it clears **no** blocker.",
    "DMap has never even rendered here (licence), which D1 must fix — it is this "
    "item's true comparator, not PMax.",
    "Bytes are then invariant to worker count *by construction*",
    "comparators re-timed under the identical protocol at matched output",
)

SCORECARD_ANCHORS = (
    "The publication gates are exactly `M1`, `M2`, `M3`, `M8`, `M9`, `M10`, "
    "and `M11`",
    "`M4`, `M5`, `M6`, `M7`, and `M12` are mandatory disclosures",
    "**SCORECARD ADDITION — UNRATIFIED. This rule is authored here and is not "
    "traceable to the owner's plan.**",
    "**SCORECARD ADDITION — UNRATIFIED. The universal conjunction in the "
    "preceding paragraph is authored here and is not traceable to the owner's plan.**",
    "The build must also pass the independently commissioned M1 gate.",
    "p99(a_e)` no worse than the M1-qualified comparator envelope in every scope",
    "A comparator mode qualifies only when one binary/settings fingerprint passes "
    "the common-input transfer/geometry contract, M1, M2, M3, M8, and the retained M4",
    "For the owner's overall gate, the same output must pass the retained M4 component",
    "Common-merge track — sole publication track.",
    "they cannot establish a competitive detail, noise, clipping, or colour win",
    "M178 adjudicated the scorecard's reverse M11 dependency an unratified addition",
    "M12 | Memory / determinism / scaling invariance | **FAIL**",
    "Blocker `(b)`, the scorecard native-scale geometry gate, is now **CLEARED**.",
    "rebuild prerequisite is now **closed**",
    "the fresh hash-bound fork, frozen modes, timing harness",
    "`M9` and `M10` are strehl output obligations, not comparator capabilities.",
)

M158_ANCHORS = (
    "Status: **COMPLETE — 58 gate-bearing blocks examined; 14 distinct drift findings**",
    "Decision rule 4 makes replacement M1 a prerequisite",
    "Competitive quality is restricted to one already-demosaiced RGB-TIFF boundary",
    "M12-S's 16-worker output must pass **all of M11**",
    "A SOTA verdict requires all 12 primary axes",
)

M139_ANCHORS = (
    "**Absolute memory: FAIL.** The bar is 6 GiB.",
    "`scored:N105:W16:R2`: sampled private commit",
    "`32.6777 GiB`, Job Object peak `33.4283 GiB`",
    "N=33 has five distinct TIFF hashes",
    "N=105 independently has five of each",
    "**Formal M12 verdict: FAIL.** M12 is conjunctive.",
)

EXPECTED_AXES = [f"M{i}" for i in range(1, 13)]
EXPECTED_LITERAL_D = [f"M{i}" for i in range(1, 8)]
EXPECTED_LOSES_D = [f"M{i}" for i in range(2, 8)]
EXPECTED_ATOMIC_EXTRA = [f"M{i}" for i in range(2, 8)] + ["M11"]
EXPECTED_REGISTER_IDS = [f"R{i}" for i in range(1, 10)]
EXPECTED_AXIS_FINGERPRINTS = {
    "M1": "e4135fbe316a76b7a9ec6f6deafadf540c0fcdb2bbc1ecb87bd8aa223fcc97e3",
    "M2": "58e8383e3dfd636169d3b1fef329e24d443176dc8ee225ad68de835fcb7d0af2",
    "M3": "cb5cc708ff17ddb24037daec22bfaced5887f0c8c1399382e3851ac7a8e0a81a",
    "M4": "1504b3187ddc9cf7a8b0b8cec98ad5acc13a94b5ddd582346f799237a4f8db13",
    "M5": "49b75b31252402b9376715f1d89e1ff5183aa18acc17e1e934ede96f40a15383",
    "M6": "1e41668d9c74d99663f3062ff01fecf867707064263f68ac0632401989389dad",
    "M7": "2eff9cdd3ca6a652cf45e9c3bc29c74fd00f82567601ed33ba9d8e626e08ffbd",
    "M8": "e2a12054c7744064951aa066822593464ae74122e1f8c62df4ca5c6255462c0b",
    "M9": "f28fcc2e979480e5ed50678b2c6b4a84684e9ac99c340436b75efcf228395d76",
    "M10": "8894a3af05307c7a3d4204e2f9716fe8e1fa97c612c674ec8c66cb04c7c5a112",
    "M11": "e6db50f49a6794bd4b60e8b4c9e5fb29abdcf555069d5c9edaa9409d0f7fe076",
    "M12": "09430c4e6768e2a058c5beb71479e18487e7f7deeffa93842a8af61e1be06035",
}
EXPECTED_REGISTER_FINGERPRINTS = {
    "R1": "886d290e960bf8ba6a1dfe952f743ce77d1c585a38c4806b26e74316c0421dbd",
    "R2": "35116db14becfc8fdc047f4a14a798852c4f0c2db5628b431a2365c1826f5ab1",
    "R3": "3a02f75efc973c26943b72b1b5a8948ab520f4c3c0f3ebf95cbba5b6b703108b",
    "R4": "cae59835a243ed10770bea64c0ca4027c41a234c9b5272bdc3f2ba21c644b2a3",
    "R5": "c99ca968c3e00fccec2c224167cce0da37c83f1867fbf256866091dbee7bd660",
    "R6": "62419d819983fbe6c1b09308380b46139de02a0f8d4d1bde55145a29f505f661",
    "R7": "231eb99269db332cd370f655b5107ee88d3390609860866ac5b10ed783365df7",
    "R8": "bef8617f03406a7f799f32aa86eb9063f6d78f04d085d0d89aa90fcda76986d0",
    "R9": "4532c49531d7db38779bfdf4827322a31160a697cbf5f40fac11aa48775fb149",
}
EXPECTED_OBJECT_FINGERPRINTS = {
    "headline": "6afa18fa7df29c242a07db723efb50331c1f774fbc8a861e874c3db5355add09",
    "m175_effect": "7b15c62d2a7def33ebe45e71353e923d54937fdd4a6b84d98ebdbd31da2a044a",
    "ratification_totals": "049f9080f2a30cf10649fd52189d66db3650ac8e09e59f6360d143b439c6fe83",
    "m158_disposition": "3006773287e75f982a74b5894baaa7eac9397d1d2e23bb15f9e0ecd4cc54ffbb",
    "document_consistency_defects": "214335b20769183abe7e0727149bedbb8fcd7456fc7a1763129c7f0a54a4fe17",
    "m12_disposition": "df7cb9fc90af31e044b46ad2b95acfc061c372f5894bd04fd21f1acc6c34fca1",
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


def normalize(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("> "):
            line = stripped[2:]
        lines.append(line)
    return " ".join("\n".join(lines).split())


def source_bytes(key: str, path: Path) -> bytes:
    if key not in PINNED_GIT_SOURCES:
        return path.read_bytes()
    revision = PINNED_GIT_SOURCES[key]
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.check_output(
        ["git", "show", f"{revision}:{relative}"],
        cwd=ROOT,
    )


def source_text(key: str, path: Path) -> str:
    return source_bytes(key, path).decode("utf-8")


def semantic_fingerprint(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def source_line_count(key: str, path: Path) -> int:
    return len(source_text(key, path).splitlines())


def readiness_rows(scorecard: str) -> dict[str, str]:
    start = scorecard.index("### 3.1 Measurement readiness as of v1.10")
    end = scorecard.index("### 3.2 Closed program decision gates", start)
    rows: dict[str, str] = {}
    for line in scorecard[start:end].splitlines():
        if not line.startswith("| M"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(r"M(?:[1-9]|1[0-2])", cells[0]):
            rows[cells[0]] = line
    return rows


def validate(
    texts: dict[str, str],
    audit: dict[str, Any],
    report: str,
    *,
    check_disk: bool,
) -> int:
    checks = Checks()

    checks.require(audit["schema_version"] == 1, "unexpected audit schema")
    checks.require(audit["pixel_files_opened"] == 0, "pixel-free boundary changed")
    checks.require(audit["score_authorized"] is False, "audit cannot authorize a score")

    checks.require(set(SOURCE_PATHS) == set(EXPECTED_SOURCES), "source allowlist drift")
    checks.require(
        set(audit["source_snapshot"]) == set(SOURCE_PATHS),
        "JSON source snapshot allowlist drift",
    )
    for key, path in SOURCE_PATHS.items():
        checks.require(path.suffix == ".md", f"non-Markdown source admitted: {path}")
        checks.require(
            "7-aperture-pairs" not in str(path).lower(),
            f"forbidden holdout path admitted: {path}",
        )
        expected_hash, expected_lines = EXPECTED_SOURCES[key]
        snapshot = audit["source_snapshot"][key]
        checks.require(
            snapshot["path"] == path.relative_to(ROOT).as_posix(),
            f"{key} JSON path drift",
        )
        checks.require(snapshot["sha256"] == expected_hash, f"{key} JSON hash drift")
        checks.require(snapshot["lines"] == expected_lines, f"{key} JSON line drift")
        if key in PINNED_GIT_SOURCES:
            checks.require(
                snapshot["revision"] == PINNED_GIT_SOURCES[key],
                f"{key} JSON revision drift",
            )
        else:
            checks.require("revision" not in snapshot, f"{key} unexpected revision pin")
        if check_disk:
            checks.require(
                hashlib.sha256(source_bytes(key, path)).hexdigest() == expected_hash,
                f"{key} source hash drift",
            )
            checks.require(
                source_line_count(key, path) == expected_lines,
                f"{key} source line drift",
            )

    plan = normalize(texts["plan"])
    scorecard = normalize(texts["scorecard"])
    m139 = normalize(texts["m139_m12_campaign"])
    m158 = normalize(texts["m158_drift_audit"])
    m161 = normalize(texts["m161_m3_ratification"])
    m166 = normalize(texts["m166_bar_definitions"])
    m169_comparator = normalize(texts["m169_comparator_audit"])
    m169_m3 = normalize(texts["m169_m3_commissioning"])
    m175 = normalize(texts["m175_fork_arm"])

    for anchor in PLAN_ANCHORS:
        checks.require(normalize(anchor) in plan, f"missing plan anchor: {anchor}")
    for anchor in SCORECARD_ANCHORS:
        checks.require(
            normalize(anchor) in scorecard,
            f"missing scorecard anchor: {anchor}",
        )
    for anchor in M158_ANCHORS:
        checks.require(normalize(anchor) in m158, f"missing M158 anchor: {anchor}")
    for anchor in M139_ANCHORS:
        checks.require(normalize(anchor) in m139, f"missing M139 anchor: {anchor}")

    checks.require(
        "The p99, rate, Wilson, comparator, width, and coherence summaries remain "
        "reported." in m161,
        "M161 addition provenance missing",
    )
    checks.require(
        "**Status:** proposal for lane M160 to apply; not a scorecard edit and not "
        "a measurement result." in m166,
        "M166 proposal status missing",
    )
    checks.require(
        "SCORECARD EXCEEDS PLAN: it made PMax, DMap, and the fork an axis-blind "
        "all-or-nothing gate." in m169_comparator,
        "prior M169 ruling missing",
    )
    checks.require(
        "**Instrument verdict: BATTERY COMMISSIONED.**" in m169_m3,
        "M169 M3 commissioning anchor missing",
    )
    checks.require(
        "This is a development admission of the fork rebuild/transfer sub-arm, not "
        "a scored quality result" in m175,
        "M175 scope anchor missing",
    )
    checks.require("No scorecard axis changes status." in m175, "M175 axis ruling missing")
    for value in (
        "1.0000000000000002",
        "-6.6597626500634704e-18",
        "2.220446049250313e-16",
        "691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac",
    ):
        checks.require(value in m175, f"M175 result anchor missing: {value}")

    rows = readiness_rows(texts["scorecard"])
    checks.require(list(rows) == EXPECTED_AXES, "§3.1 must contain ordered M1-M12")
    literal_d = [
        axis for axis, row in rows.items() if "(d)" in row.split("|")[2]
    ]
    checks.require(literal_d == EXPECTED_LITERAL_D, f"literal (d) set drifted: {literal_d}")
    checks.require(
        "required common-input comparator outputs" in rows["M11"],
        "M11 semantic comparator dependency missing",
    )
    checks.require("(d)" not in rows["M9"], "M9 cannot be counted as direct (d)")

    axis_rows = audit["axis_ledger"]
    checks.require(len(axis_rows) == 12, "axis ledger length changed")
    axes = [row["axis"] for row in axis_rows]
    checks.require(axes == EXPECTED_AXES, "axis ledger order/completeness changed")
    by_axis = {row["axis"]: row for row in axis_rows}
    for axis, row in by_axis.items():
        checks.require(
            semantic_fingerprint(row) == EXPECTED_AXIS_FINGERPRINTS[axis],
            f"{axis} complete ledger row drift",
        )
    loses_d = [row["axis"] for row in axis_rows if row["loses_d"]]
    checks.require(loses_d == EXPECTED_LOSES_D, f"counterfactual loses-(d) set: {loses_d}")
    checks.require(
        all(not by_axis[axis]["scoreable_now"] for axis in EXPECTED_LOSES_D),
        "an axis was falsely promoted to scoreable",
    )
    checks.require(
        by_axis["M1"]["plan_required_arms"] == ["Zerene PMax", "Zerene DMap"],
        "M1 plan arm map drift",
    )
    checks.require(
        by_axis["M11"]["plan_required_arms"] == ["fresh best-known-source fork"],
        "M11 plan arm map drift",
    )
    checks.require(
        by_axis["M10"]["plan_required_arms"] == [],
        "DMap was incorrectly made an M10 score input",
    )
    checks.require(
        by_axis["M9"]["current_comparator_dependency"]
        == "TRANSITIVE_THROUGH_M1_TRUTH",
        "M9 direct/transitive distinction drift",
    )
    checks.require(by_axis["M12"]["scoreable_now"] is True, "M12 read status drift")
    checks.require(by_axis["M12"]["remaining_blockers"] == [], "M12 has stale blockers")

    headline = audit["headline"]
    checks.require(
        semantic_fingerprint(headline) == EXPECTED_OBJECT_FINGERPRINTS["headline"],
        "complete headline ledger drift",
    )
    checks.require(headline["axes_losing_d"] == EXPECTED_LOSES_D, "headline freed set drift")
    checks.require(headline["axes_losing_d_count"] == 6, "freed count must be six")
    checks.require(headline["newly_scoreable"] == [], "newly scoreable set must be empty")
    checks.require(headline["newly_scoreable_count"] == 0, "scoreable count must be zero")
    checks.require(headline["axis_status_changes"] == [], "axis status cannot move")
    checks.require(
        headline["owner_plan_paid_license_direct_axes"] == ["M1"],
        "owner-plan paid-licence count drift",
    )
    checks.require(
        headline["unratified_atomic_rule_added_paid_license_direct_axes"]
        == EXPECTED_ATOMIC_EXTRA,
        "unratified paid-licence propagation drift",
    )
    checks.require(headline["m9_is_transitive_not_direct"] is True, "M9 tally drift")

    m175_effect = audit["m175_effect"]
    checks.require(
        semantic_fingerprint(m175_effect)
        == EXPECTED_OBJECT_FINGERPRINTS["m175_effect"],
        "complete M175 effect ledger drift",
    )
    checks.require(m175_effect["axis_status_moved"] is False, "M175 falsely moved an axis")
    checks.require(
        "scored common-input fork outputs" in m175_effect["not_closed"],
        "M175 scope overclaim",
    )
    checks.require(
        "D9 worker-independent reduction" in m175_effect["not_closed"],
        "D9 was falsely closed",
    )

    register = audit["ratification_register"]
    checks.require(len(register) == 9, "ratification register length changed")
    checks.require(
        [row["id"] for row in register] == EXPECTED_REGISTER_IDS,
        "ratification register IDs drift",
    )
    for row in register:
        checks.require(
            semantic_fingerprint(row) == EXPECTED_REGISTER_FINGERPRINTS[row["id"]],
            f"{row['id']} complete register row drift",
        )
    checks.require(
        [row["known"] for row in register].count(True) == 2,
        "known-addition count drift",
    )
    checks.require(
        [row["known"] for row in register].count(False) == 7,
        "new-addition count drift",
    )
    checks.require(
        next(row for row in register if row["id"] == "R9")["status"]
        == "WITHDRAWN_SCORECARD_V1_11",
        "withdrawn reverse M12 dependency was reactivated",
    )
    totals = audit["ratification_totals"]
    checks.require(
        semantic_fingerprint(totals)
        == EXPECTED_OBJECT_FINGERPRINTS["ratification_totals"],
        "complete ratification totals drift",
    )
    checks.require(
        totals["historical_material_governance_families"] == 9,
        "historical family count drift",
    )
    checks.require(
        totals["active_material_governance_families"] == 8,
        "active family count drift",
    )
    checks.require(totals["previously_known"] == 2, "known family count drift")
    checks.require(totals["additional_found"] == 7, "new family count drift")
    checks.require(totals["active_additional_found"] == 6, "active new family count drift")
    checks.require(totals["withdrawn"] == 1, "withdrawn family count drift")
    checks.require(totals["m158_findings_dispositioned"] == 14, "M158 count drift")
    checks.require(
        set(audit["m158_disposition"]) == {str(i) for i in range(1, 15)},
        "M158 disposition incomplete",
    )
    checks.require(
        semantic_fingerprint(audit["m158_disposition"])
        == EXPECTED_OBJECT_FINGERPRINTS["m158_disposition"],
        "complete M158 disposition drift",
    )
    checks.require(
        len(audit["document_consistency_defects"]) == 3,
        "consistency-defect count drift",
    )
    checks.require(
        semantic_fingerprint(audit["document_consistency_defects"])
        == EXPECTED_OBJECT_FINGERPRINTS["document_consistency_defects"],
        "complete consistency-defect ledger drift",
    )
    checks.require(
        semantic_fingerprint(audit["m12_disposition"])
        == EXPECTED_OBJECT_FINGERPRINTS["m12_disposition"],
        "complete M12 disposition drift",
    )
    m12 = audit["m12_disposition"]
    checks.require(m12["overall"] == "FAIL", "M12 overall status drift")
    checks.require(m12["m12_d"] == "PASS", "M12-D status drift")
    checks.require(m12["m12_s_cross_worker"] == "FAIL", "M12-S status drift")
    checks.require(m12["absolute_memory"] == "FAIL", "M12 memory status drift")
    checks.require(m12["n_mod_4"] == "FAIL", "M12 modulo status drift")
    checks.require(
        m12["peak_ratio"] == "UNMEASURED_SAMPLING_COVERAGE",
        "M12 ratio status drift",
    )

    lead = "**AXES FREED: 6 of which 0 become scoreable.**"
    checks.require(lead in report, "report lead missing")
    for heading in (
        "## 1. Which axes lose blocker `(d)`",
        "## 2. Why none of the six becomes scoreable",
        "## 3. What M175 moved",
        "## 4. The honest total",
        "## 5. M10 and M12 boundary rulings",
        "## 6. Full scorecard provenance sweep",
        "## 7. Text routed to the scorecard owner",
        "## 8. Boundaries and unresolved document defects",
    ):
        checks.require(heading in report, f"missing report section: {heading}")
    checks.require("**VERIFIED BY RUNNING" in report, "running-evidence label missing")
    checks.require("**INFERRED BY READING" in report, "reading-evidence label missing")
    checks.require("**NO SCORE**" in report, "no-score boundary missing")
    checks.require(
        "one direct\nowner-plan paid-licence axis" in report,
        "honest total missing",
    )
    for register_id in EXPECTED_REGISTER_IDS:
        checks.require(f"**{register_id}" in report, f"report missing {register_id}")
    checks.require(
        "ordinary scorecard-owned numeric completion" in report,
        "numeric-completion exclusion missing",
    )
    checks.require(
        "The scoreboard remains `0 of 12` PASS." in report,
        "scoreboard boundary missing",
    )
    checks.require(
        "FAIL:                M8 M12" in report,
        "corrected M12 status block missing",
    )
    checks.require(
        "| `docs/research/M139-m12-campaign.md@"
        "2ba256aa8c511ec83b4c0a99c5b988ad0752afc1` | 268 | "
        "`9cff5b17c0129d8246b859689b30bf20747f67bae68b0217a9f3641378af0df7` |"
        in report,
        "M139 report snapshot row drift",
    )
    for value in (
        "33.4283",
        "2ba256aa8c511ec83b4c0a99c5b988ad0752afc1",
        "M12-D passes all 15",
        "UNMEASURED_SAMPLING_COVERAGE",
    ):
        checks.require(value in report, f"M12 report value missing: {value}")
    checks.require(
        "**R9 — new; withdrawn in v1.11**" in report,
        "withdrawn R9 report row missing",
    )
    checks.require(
        "leaving eight\n  active families total and six active additions beyond R1/R2"
        in report,
        "active governance count prose drift",
    )
    checks.require(
        "`M12` awaits its registered run" not in report,
        "stale M12 pending-run prose remains",
    )
    checks.require(
        "reverse dependency remains R9" not in report,
        "stale active R9 prose remains",
    )

    return checks.count


def expect_rejected(
    name: str,
    texts: dict[str, str],
    audit: dict[str, Any],
    report: str,
) -> None:
    try:
        validate(texts, audit, report, check_disk=False)
    except (AuditFailure, KeyError, ValueError, TypeError):
        return
    raise AuditFailure(f"negative control was not rejected: {name}")


def main() -> int:
    texts = {
        key: source_text(key, path) for key, path in SOURCE_PATHS.items()
    }
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    report = REPORT_PATH.read_text(encoding="utf-8")

    positive = validate(texts, audit, report, check_disk=True)

    bad_plan = dict(texts)
    bad_plan["plan"] = texts["plan"].replace(
        "§30/§32/§33 captures; a licensed comparator; the D1 instrument.",
        "§30/§32/§33 captures; the D1 instrument.",
        1,
    )
    expect_rejected("M1 licence authority removed", bad_plan, audit, report)

    bad_scorecard = dict(texts)
    bad_scorecard["scorecard"] = texts["scorecard"].replace(
        "| M7 | **(b)(c)(d)** |",
        "| M7 | **(b)(c)** |",
        1,
    )
    expect_rejected("literal (d) set drift", bad_scorecard, audit, report)

    false_scoreable = copy.deepcopy(audit)
    false_scoreable["headline"]["newly_scoreable"] = ["M3"]
    false_scoreable["headline"]["newly_scoreable_count"] = 1
    next(row for row in false_scoreable["axis_ledger"] if row["axis"] == "M3")[
        "scoreable_now"
    ] = True
    expect_rejected("false scoreability promotion", texts, false_scoreable, report)

    false_m175 = copy.deepcopy(audit)
    false_m175["m175_effect"]["axis_status_moved"] = True
    expect_rejected("false M175 axis movement", texts, false_m175, report)

    truncated_register = copy.deepcopy(audit)
    truncated_register["ratification_register"] = truncated_register[
        "ratification_register"
    ][:-1]
    expect_rejected("ratification register truncation", texts, truncated_register, report)

    false_m10 = copy.deepcopy(audit)
    next(row for row in false_m10["axis_ledger"] if row["axis"] == "M10")[
        "plan_required_arms"
    ] = ["Zerene DMap"]
    expect_rejected("DMap promoted into M10 gate", texts, false_m10, report)

    reactivated_m12 = copy.deepcopy(audit)
    next(
        row
        for row in reactivated_m12["ratification_register"]
        if row["id"] == "R9"
    )["status"] = "UNLABELED_UNRATIFIED_IN_FORCE"
    expect_rejected("reverse M12 clause reactivated", texts, reactivated_m12, report)

    false_m12 = copy.deepcopy(audit)
    false_m12["m12_disposition"]["overall"] = "UNMEASURED"
    expect_rejected("false M12 overall status", texts, false_m12, report)

    false_report_peak = report.replace("33.4283", "3.34283", 1)
    expect_rejected(
        "false M12 report peak",
        texts,
        audit,
        false_report_peak,
    )

    reactivated_report_r9 = report.replace(
        "**R9 — new; withdrawn in v1.11**",
        "**R9 — new; active**",
        1,
    )
    expect_rejected(
        "reactivated R9 report row",
        texts,
        audit,
        reactivated_report_r9,
    )

    stale_snapshot = copy.deepcopy(audit)
    stale_snapshot["source_snapshot"]["scorecard"]["sha256"] = "0" * 64
    expect_rejected("stale scorecard snapshot", texts, stale_snapshot, report)

    false_path = copy.deepcopy(audit)
    false_path["source_snapshot"]["plan"]["path"] = "docs/research/not-the-plan.md"
    expect_rejected("false source path", texts, false_path, report)

    missing_blocker = copy.deepcopy(audit)
    next(row for row in missing_blocker["axis_ledger"] if row["axis"] == "M2")[
        "remaining_blockers"
    ] = []
    expect_rejected("axis blocker deletion", texts, missing_blocker, report)

    corrupt_register = copy.deepcopy(audit)
    next(row for row in corrupt_register["ratification_register"] if row["id"] == "R3")[
        "title"
    ] = "ordinary numeric completion"
    expect_rejected("ratification family corruption", texts, corrupt_register, report)

    corrupt_disposition = copy.deepcopy(audit)
    corrupt_disposition["m158_disposition"]["1"] = "OPEN_R9"
    expect_rejected("M158 disposition corruption", texts, corrupt_disposition, report)

    false_m175_close = copy.deepcopy(audit)
    false_m175_close["m175_effect"]["closed"].append("M11 verdict")
    false_m175_close["m175_effect"]["not_closed"].remove("M11 verdict")
    expect_rejected("false M175 closure", texts, false_m175_close, report)

    extra_source = copy.deepcopy(audit)
    extra_source["source_snapshot"]["unexpected"] = {
        "path": "experiments/M175-fork-arm/code.py",
        "sha256": "0" * 64,
        "lines": 1,
    }
    expect_rejected("unexpected source snapshot entry", texts, extra_source, report)

    print(f"PASS: {positive}/{positive} positive assertions")
    print("PASS: 17/17 negative controls rejected")
    print("PASS: text-only audit; opened 0 pixel files")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditFailure, KeyError, ValueError, TypeError, FileNotFoundError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
