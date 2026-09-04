"""Derive the holdout register and 603-frame gap audit from the M141 manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "capture-manifest.json"

GRID = (
    r"requests\30-calibration-grid\calibration-grid-1-sw1-cpl",
    r"requests\30-calibration-grid\calibration-grid-1-sw4-cpl",
    r"requests\30-calibration-grid\calibration-grid-2-sw4-cpl",
    r"requests\30-calibration-grid\calibration-grid-1-sw10-cpl",
    r"requests\30-calibration-grid\calibration-grid-2-sw10-cpl",
)
SLIDE = (
    r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
    r"\flat-sw4-cpl\flat-et6s-sw4-cpl",
    r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
    r"\flat-sw4-cpl\flat-et2.5s-sw4-cpl",
    r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
    r"\flat-sw4-cpl\flat-et1s-sw4-cpl",
    r"requests\misc-diagnostic\high-res-calibration-slide-cpl\tilted-sw4-cpl",
    r"requests\misc-diagnostic\high-res-calibration-slide-cpl\tilted-sw10-cpl",
    r"requests\misc-diagnostic\high-res-calibration-slide-cpl"
    r"\very-tilted-all-axis-sw10-cpl",
)
REGISTERED_HOLDOUTS = {
    r"requests\7-aperture-pairs\fabric-weave-f5.6-sw5-cpl": "HOLDOUT — QUALITY",
    r"requests\7-aperture-pairs\fabric-weave-f8-sw5-cpl": "HOLDOUT — QUALITY",
    r"requests\7-aperture-pairs\fabric-weave-f11-sw5-cpl": "HOLDOUT — QUALITY",
    r"requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f5.6-sw7-cpl": "HOLDOUT — QUALITY",
    r"requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f8-sw7-cpl": "HOLDOUT — QUALITY",
    r"requests\8-tilted-planar\ruler-incline-ang10.26deg-inches-f11-sw7-cpl": "HOLDOUT — QUALITY",
    r"requests\12-bee-iso-var-no-bracket-32-repeat-diff-light": "HOLDOUT — QUALITY",
    r"duck-tape-side-layers-cpl": "HOLDOUT — QUALITY",
    r"chia-seeds-cpl": "HOLDOUT — QUALITY",
    r"flower-bud-with-background-fern-cpl": "HOLDOUT — QUALITY",
    r"medication-pill-cpl": "HOLDOUT — QUALITY",
    r"foam": "HOLDOUT — QUALITY",
    r"requests\misc-diagnostic\flat-round-3V-battery-cpl"
    r"\flat-round-3V-battery-iso100-sw4-cpl": "HOLDOUT — QUALITY",
    r"maldon-sea-salt-cpl": "HOLDOUT — QUALITY",
    r"highly-angled-ruler-mm-cpl": "HOLDOUT — QUALITY",
    r"bee-1-cpl": "HOLDOUT — PERFORMANCE",
}
REGISTERED_NOT_HOLDOUT = {
    r"requests\10-paper-iso-var": "CONTROL — NOT HOLDOUT",
    r"requests\6-11-extended-dark-frames": "CONTROL — NOT HOLDOUT",
    r"requests\19-razor-edge\horizontal-flat"
    r"\razor-edge-horizontal-flat-sw4-f5.6-cpl": "CONTROL — NOT HOLDOUT",
    r"coffee-bubbles": "DEVELOPMENT — NOT HOLDOUT",
    r"coffee-bean": "FIXED HISTORICAL BENCHMARK — NOT HOLDOUT",
    r"113MSDCF": "HISTORICAL CONTROL — NOT HOLDOUT",
}


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def unit_record(
    by_id: dict[str, dict[str, Any]],
    *,
    unit_id: str,
    members: tuple[str, ...],
    ruling: str,
    ruling_status: str,
    sources: list[str],
    note: str,
) -> dict[str, Any]:
    rows = [by_id[member] for member in members]
    return {
        "unit_id": unit_id,
        "members": list(members),
        "frame_count": sum(row["frame_count"] for row in rows),
        "first_capture_at": min(row["first_capture_at"] for row in rows),
        "last_capture_at": max(row["last_capture_at"] for row in rows),
        "ruling": ruling,
        "ruling_status": ruling_status,
        "numeric_status": "VERIFIED",
        "sources": sources,
        "note": note,
    }


def make_holdout_register(manifest: dict[str, Any]) -> dict[str, Any]:
    by_id = {row["stack_id"]: row for row in manifest["stacks"]}
    known = set(GRID) | set(SLIDE) | set(REGISTERED_HOLDOUTS) | set(
        REGISTERED_NOT_HOLDOUT
    )
    missing = sorted(known - set(by_id))
    if missing:
        raise RuntimeError(f"classified paths missing from manifest: {missing}")
    clean = []
    for stack_id, evidence_class in REGISTERED_HOLDOUTS.items():
        row = by_id[stack_id]
        clean.append(
            {
                "stack_id": stack_id,
                "frame_count": row["frame_count"],
                "first_capture_at": row["first_capture_at"],
                "last_capture_at": row["last_capture_at"],
                "ruling": "CLEAN REGISTERED HOLDOUT",
                "evidence_class": evidence_class,
                "numeric_status": "VERIFIED",
                "ruling_status": "INHERITED",
                "source": r"docs\proposals\2026-09-sota-scorecard.md:315-334",
                "caveat": (
                    "This is the current scorecard label; same-subject/session "
                    "partners not explicitly listed are not promoted by inference."
                ),
            }
        )
    not_holdout = []
    for stack_id, evidence_class in REGISTERED_NOT_HOLDOUT.items():
        row = by_id[stack_id]
        not_holdout.append(
            {
                "stack_id": stack_id,
                "frame_count": row["frame_count"],
                "ruling": "NOT HOLDOUT",
                "evidence_class": evidence_class,
                "numeric_status": "VERIFIED",
                "ruling_status": "INHERITED",
                "source": r"docs\proposals\2026-09-sota-scorecard.md:321-336",
            }
        )
    return {
        "schema": "M141-holdout-register-v1",
        "rule": {
            "text": (
                "The holdout unit is subject plus uninterrupted capture session. "
                "Rendering, tuning, or reading an outcome on any member burns "
                "every member."
            ),
            "status": "INHERITED",
            "source": r"docs\proposals\2026-09-sota-scorecard.md:343-348",
        },
        "burned_or_spent_units": [
            unit_record(
                by_id,
                unit_id="calibration-grid-2026-09-01",
                members=GRID,
                ruling="BURNED — QUARANTINED DEVELOPMENT ONLY",
                ruling_status="INHERITED",
                sources=[
                    r"docs\proposals\2026-09-sota-scorecard.md:304-308",
                    r"docs\proposals\2026-09-sota-scorecard.md:345-360",
                    r"experiments\PHASE1-DESIGN\quarantine"
                    r"\f5658e5d-grid-sw4-exposed\ACCESS.md:6-18",
                ],
                note=(
                    "The sw4 outcome leak burns all five same-subject/session "
                    "members, including stacks W1 did not itself score."
                ),
            ),
            unit_record(
                by_id,
                unit_id="high-res-calibration-slide-2026-09-02",
                members=SLIDE,
                ruling="BURNED — DELIBERATELY SPENT DEVELOPMENT, NOT HOLDOUT",
                ruling_status="INHERITED",
                sources=[
                    r"docs\proposals\2026-09-sota-scorecard.md:36-41",
                    r"docs\proposals\2026-09-sota-scorecard.md:363-379",
                    r"docs\STATUS.md:2535-2547",
                    r"experiments\cover-default\slide-series-preregistration.md:9-15",
                ],
                note=(
                    "Conservative unit boundary: all six stacks are one physical "
                    "slide/session. Geometry outcomes have been read, so this unit "
                    "cannot be recovered as holdout evidence."
                ),
            ),
        ],
        "clean_registered_holdout_rows": clean,
        "explicit_not_holdout_rows": not_holdout,
        "unclassified_stack_ids": [
            {
                "stack_id": stack_id,
                "ruling": "INDETERMINATE — DO NOT ASSUME CLEAN",
                "ruling_status": "INHERITED",
                "basis": (
                    "No row for this stack in the scorecard's explicit evidence "
                    "table; the scorecard says only rows beginning HOLDOUT are "
                    "holdout."
                ),
                "source": r"docs\proposals\2026-09-sota-scorecard.md:299-303",
            }
            for stack_id in sorted(set(by_id) - known)
        ],
        "error_direction": (
            "restrictive: ambiguous or unlisted material is not treated as a "
            "clean holdout, and the whole six-stack slide sitting is treated as "
            "spent rather than split into narrower units"
        ),
    }


def block(
    name: str,
    frames: int,
    request_line: int,
    reason: str,
    analogues: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "block": name,
        "requested_frames": frames,
        "status": "NOT SATISFIED",
        "eligible_existing_frames": 0,
        "remaining_frames": frames,
        "requested_frames_status": "INHERITED",
        "eligible_existing_frames_status": "VERIFIED",
        "remaining_frames_status": "VERIFIED",
        "request_source": (
            rf"docs\capture-requests\2026-09-319-frame-session.md:{request_line}"
        ),
        "reason": reason,
        "existing_analogues_not_creditable": analogues or [],
    }


def make_gap_analysis(manifest: dict[str, Any]) -> dict[str, Any]:
    by_id = {row["stack_id"]: row for row in manifest["stacks"]}
    all_ibis_on = all(
        {
            item["value"]
            for item in row["settings"]["image_stabilization"]
        }
        == {"On"}
        for row in manifest["stacks"]
    )
    if not all_ibis_on:
        raise RuntimeError("expected every inventoried ARW stack to report IBIS on")

    reason_session = (
        "No existing frame can enter this block: the request requires one fresh, "
        "sealed, uninterrupted HOLDOUT session, while all inventoried ARWs report "
        "ImageStabilization On and the request requires body SteadyShot and lens "
        "OSS off."
    )
    reason_witness = (
        reason_session
        + " No existing capture implements this named fixed-focus witness at the "
        "required point in the A/B reset sequence."
    )
    reason_sw4 = (
        reason_session
        + " Existing sw4 ladders are burned/development-only, and no eligible "
        "pair supplies two identical 55-frame passes at one geometry."
    )
    reason_sw10 = (
        reason_session
        + " Existing sw10 ladders are burned/development-only; the two new sw10 "
        "views have different geometry and are not repeats."
    )
    reason_sw1 = (
        reason_session
        + " The exact 91-frame old sw1 grid is burned; the new dense slide is "
        "sw4 and development-only."
    )
    reason_flat = (
        reason_session
        + " Existing flat material is not two independent, same-session, "
        "same-exposure 32-frame diffuser groups assigned separately to A and B."
    )
    reason_dark = (
        reason_session
        + " The existing dark campaign has only one 22-frame ISO-100/1-s group "
        "and was not warmed in this claim session; it cannot supply either "
        "32-frame A/B master."
    )
    reason_reference_scene = (
        reason_session
        + " No existing capture is a 32-frame fixed-focus view of this same "
        "physical patch at the required >=2x sampling ratio."
    )
    reason_reference_flat = (
        reason_session
        + " No existing flat group is an independently repositioned, "
        "reference-only 32-frame master from the high-magnification block."
    )
    reason_reference_dark = (
        reason_session
        + " No existing dark group is a warmed, matching 32-frame reference "
        "dark from the high-magnification block."
    )
    sw4_analogues = [
        GRID[1],
        GRID[2],
        SLIDE[3],
    ]
    sw10_analogues = [
        GRID[3],
        GRID[4],
        SLIDE[4],
        SLIDE[5],
    ]
    witness_names = (
        ("reset pre-flight P0", 228),
        ("reset pre-flight P1", 229),
        ("start sw4-A", 230),
        ("end sw4-A", 232),
        ("start sw4-B", 233),
        ("end sw4-B", 235),
        ("start sw10-A", 236),
        ("end sw10-A", 238),
        ("start sw10-B", 239),
        ("end sw10-B", 241),
    )
    blocks = [
        block(name, 6, line, reason_witness) for name, line in witness_names
    ]
    blocks.extend(
        [
            block("sw4-A", 55, 231, reason_sw4, sw4_analogues),
            block("sw4-B", 55, 234, reason_sw4, sw4_analogues),
            block("sw10-A", 27, 237, reason_sw10, sw10_analogues),
            block("sw10-B", 27, 240, reason_sw10, sw10_analogues),
            block("sw1 checker-only", 91, 242, reason_sw1, [GRID[0], SLIDE[3]]),
            block(
                "flats A",
                32,
                243,
                reason_flat,
                [
                    r"flat-fields\flat-fields",
                    SLIDE[0],
                    SLIDE[1],
                    SLIDE[2],
                ],
            ),
            block(
                "flats B",
                32,
                244,
                reason_flat,
                [
                    r"flat-fields\flat-fields",
                    SLIDE[0],
                    SLIDE[1],
                    SLIDE[2],
                ],
            ),
            block(
                "darks A",
                32,
                245,
                reason_dark,
                [r"requests\6-11-extended-dark-frames"],
            ),
            block(
                "darks B",
                32,
                246,
                reason_dark,
                [r"requests\6-11-extended-dark-frames"],
            ),
            block("reference near", 32, 249, reason_reference_scene),
            block("reference middle", 32, 250, reason_reference_scene),
            block("reference far", 32, 251, reason_reference_scene),
            block(
                "reference flats",
                32,
                252,
                reason_reference_flat,
                [r"flat-fields\flat-fields"],
            ),
            block(
                "reference darks",
                32,
                253,
                reason_reference_dark,
                [r"requests\6-11-extended-dark-frames"],
            ),
        ]
    )
    requested = sum(item["requested_frames"] for item in blocks)
    remaining = sum(item["remaining_frames"] for item in blocks)
    if requested != 603 or remaining != 603 or len(blocks) != 24:
        raise RuntimeError(
            f"gap arithmetic failed: blocks={len(blocks)} "
            f"requested={requested} remaining={remaining}"
        )
    missing_analogues = sorted(
        {
            analogue
            for item in blocks
            for analogue in item["existing_analogues_not_creditable"]
            if analogue not in by_id
        }
    )
    if missing_analogues:
        raise RuntimeError(f"analogue paths missing from manifest: {missing_analogues}")
    return {
        "schema": "M141-capture-gap-analysis-v1",
        "ruling": {
            "requested_session_frames": 603,
            "requested_session_frames_status": "INHERITED",
            "eligible_existing_frames": 0,
            "eligible_existing_frames_status": "VERIFIED",
            "remaining_session_frames": 603,
            "remaining_session_frames_status": "VERIFIED",
            "throwaway_histogram_exposure_outside_603": 1,
            "throwaway_histogram_exposure_status": "INHERITED",
            "remaining_session_shutter_releases_including_throwaway": 604,
            "remaining_session_shutter_releases_status": "VERIFIED",
            "sources": [
                r"docs\capture-requests\2026-09-319-frame-session.md:127-137",
                r"docs\capture-requests\2026-09-319-frame-session.md:228-255",
                r"docs\capture-requests\2026-09-319-frame-session.md:566-577",
            ],
            "note": (
                "The two unresolved pre-shoot items require one development dry "
                "run whose frame count is not specified in the request; it is "
                "additional to the frozen 603-frame holdout session."
            ),
        },
        "cross_cutting_disqualifiers": [
            {
                "fact": "All 10,509 inventoried ARWs report ImageStabilization On.",
                "status": "VERIFIED",
                "source": str(MANIFEST),
            },
            {
                "fact": (
                    "The frozen session requires body SteadyShot OFF and lens "
                    "OSS OFF."
                ),
                "status": "INHERITED",
                "source": (
                    r"docs\capture-requests\2026-09-319-frame-session.md:497-500"
                ),
            },
            {
                "fact": (
                    "The scored value must come from this new sealed HOLDOUT "
                    "session; existing development captures only commission."
                ),
                "status": "INHERITED",
                "source": (
                    r"docs\capture-requests\2026-09-319-frame-session.md:169-179"
                ),
            },
        ],
        "pre_shoot_items": [
            {
                "item": 1,
                "status": "NOT SATISFIED",
                "numeric_status": "INHERITED",
                "reason": (
                    "No metadata-only evidence establishes 1.30x reproduction, "
                    "gap-free coverage, or 64 interior sites; the request "
                    "explicitly requires image-data verification."
                ),
                "source": (
                    r"docs\capture-requests\2026-09-319-frame-session.md:27"
                ),
            },
            {
                "item": 2,
                "status": "NOT SATISFIED",
                "numeric_status": "INHERITED",
                "reason": (
                    "The new slide has no required fixed-focus G2 burst pairs or "
                    "matched A/B ladders for G3 at the exact configuration."
                ),
                "source": (
                    r"docs\capture-requests\2026-09-319-frame-session.md:28"
                ),
            },
            {
                "item": 3,
                "status": "ALREADY SATISFIED",
                "numeric_status": "INHERITED",
                "reason": "Converter identity is closed by owner testimony.",
                "source": (
                    r"docs\capture-requests\2026-09-319-frame-session.md:29-32"
                ),
            },
        ],
        "blocks": sorted(
            blocks,
            key=lambda item: int(item["request_source"].rsplit(":", 1)[1]),
        ),
        "block_count": 24,
        "block_status_counts": {
            "already_satisfied": 0,
            "partially_satisfied": 0,
            "not_satisfied": 24,
            "numeric_status": "VERIFIED",
        },
    }


def main() -> int:
    manifest = load_manifest()
    holdouts = make_holdout_register(manifest)
    gaps = make_gap_analysis(manifest)
    (HERE / "holdout-register.json").write_text(
        json.dumps(holdouts, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (HERE / "capture-gap-analysis.json").write_text(
        json.dumps(gaps, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "burned_or_spent_units": len(
                    holdouts["burned_or_spent_units"]
                ),
                "clean_registered_holdout_rows": len(
                    holdouts["clean_registered_holdout_rows"]
                ),
                "unclassified_stack_ids": len(
                    holdouts["unclassified_stack_ids"]
                ),
                "gap_blocks": gaps["block_count"],
                "remaining_frames": gaps["ruling"]["remaining_session_frames"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
