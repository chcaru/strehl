"""Derive the holdout register and design-scoped gap audits from the manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "capture-manifest.json"
PROJECT_ROOT = HERE.parent.parent
TRUTH_PROPOSAL = (
    PROJECT_ROOT / "docs" / "proposals" / "2026-09-truth-referenced-detail.md"
)
TRUTH_PROPOSAL_SHA256 = (
    "4a8f470b31d7823a819b865084af29d4511b2a2df8317b2e71316a9ced076171"
)

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


def setting_values(row: dict[str, Any], key: str) -> list[Any]:
    return [item["value"] for item in row["settings"][key]]


def analogue(
    by_id: dict[str, dict[str, Any]],
    stack_id: str,
    why_not_creditable: str,
) -> dict[str, Any]:
    row = by_id[stack_id]
    return {
        "stack_id": stack_id,
        "frame_count": row["frame_count"],
        "iso_values": setting_values(row, "iso"),
        "exposure_seconds_values": setting_values(row, "exposure_seconds"),
        "aperture_values": setting_values(row, "aperture"),
        "focal_length_mm_values": setting_values(row, "focal_length_mm"),
        "image_stabilization_values": setting_values(
            row, "image_stabilization"
        ),
        "release_mode_values": setting_values(row, "release_mode"),
        "step_width": row["step_width"],
        "magnification": row["magnification"],
        "numeric_status": "VERIFIED",
        "why_not_creditable": why_not_creditable,
    }


def inverted_block(
    by_id: dict[str, dict[str, Any]],
    *,
    name: str,
    frames: int,
    proposal_line: int,
    requirement: dict[str, str],
    reason: str,
    analogues: list[tuple[str, str]] | None = None,
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
            rf"docs\proposals\2026-09-truth-referenced-detail.md:{proposal_line}"
        ),
        "requirement": requirement,
        "reason": reason,
        "closest_existing_analogues_not_creditable": [
            analogue(by_id, stack_id, why)
            for stack_id, why in (analogues or [])
        ],
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
        "design_scope": {
            "design_id": "committed-603-bench-sheet",
            "authority": "FROZEN COMMITTED CAPTURE REQUEST",
            "source": r"docs\capture-requests\2026-09-319-frame-session.md",
            "note": (
                "This artifact answers only the committed 603-frame design. "
                "See capture-design-coverage.json for the separate, "
                "non-arbitrating live 448-frame proposal snapshot."
            ),
        },
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


def make_design_coverage(
    manifest: dict[str, Any],
    committed_gap: dict[str, Any],
) -> dict[str, Any]:
    proposal_bytes = TRUTH_PROPOSAL.read_bytes()
    proposal_sha256 = hashlib.sha256(proposal_bytes).hexdigest()
    if proposal_sha256 != TRUTH_PROPOSAL_SHA256:
        raise RuntimeError(
            "live truth proposal changed; re-read and re-audit before "
            "regenerating M141 coverage: "
            f"{proposal_sha256} != {TRUTH_PROPOSAL_SHA256}"
        )

    by_id = {row["stack_id"]: row for row in manifest["stacks"]}
    all_focal_lengths = sorted(
        {
            value
            for row in manifest["stacks"]
            for value in setting_values(row, "focal_length_mm")
        }
    )
    all_stabilization = sorted(
        {
            value
            for row in manifest["stacks"]
            for value in setting_values(row, "image_stabilization")
        }
    )
    recovered_magnifications = sum(
        row["magnification"]["value"] is not None
        for row in manifest["stacks"]
    )
    if all_focal_lengths != [200]:
        raise RuntimeError(
            f"expected only 200 mm inventoried captures: {all_focal_lengths}"
        )
    if all_stabilization != ["On"]:
        raise RuntimeError(
            f"expected only stabilization-on captures: {all_stabilization}"
        )
    if recovered_magnifications != 0:
        raise RuntimeError(
            "expected no metadata-recoverable physical magnifications"
        )

    bee_repeat = r"requests\12-bee-iso-var-no-bracket-32-repeat-diff-light"
    flat_1s = SLIDE[2]
    dark_campaign = r"requests\6-11-extended-dark-frames"
    flat_campaign = r"flat-fields\flat-fields"
    required_analogues = {
        bee_repeat,
        flat_1s,
        dark_campaign,
        flat_campaign,
        *GRID,
        *SLIDE,
    }
    missing = sorted(required_analogues - set(by_id))
    if missing:
        raise RuntimeError(
            f"inverted-design analogues missing from manifest: {missing}"
        )

    reference_common = {
        "subject": (
            "same grid plus nonperiodic physical patch as the incoming "
            "converter-on session"
        ),
        "optical_state": (
            "converter on; untouched existing maximum-reproduction framing"
        ),
        "capture": (
            "32 fixed-focus lossless-compressed 14-bit RAW exposures at one "
            "of the near/middle/far focus intersections"
        ),
        "settings": (
            "same converter-on ISO, shutter and marked f-number; fixed white "
            "balance; IBIS and OSS off"
        ),
    }
    tc0_common = {
        "subject": (
            "same physical grid plus nonperiodic patch, retained across "
            "converter removal"
        ),
        "optical_state": (
            "bare lens, 1.32x target and measured reproduction no greater "
            "than 1.33x"
        ),
        "capture": "block-specific fixed-focus burst or automated bracket",
        "settings": (
            "ISO 100, 1 s, marked f/5.6, fixed white balance, EFCS, "
            "IBIS off, OSS off and crossed polarizers"
        ),
    }
    no_reference = (
        "No inventoried stack is a same-subject, same-framing member of the "
        "incoming converter-on session. Physical magnification is "
        "metadata-recoverable for zero stacks, and every inventoried ARW "
        "reports ImageStabilization On."
    )
    no_tc0 = (
        "No inventoried stack was captured in the required bare-lens TC0 "
        "state: every stack reports 200 mm with the 2x-converter protocol "
        "identity and ImageStabilization On, while physical reproduction "
        "ratio is not metadata-recoverable."
    )
    reference_analogues = [
        (
            bee_repeat,
            "Contains metadata-defined 32-frame fixed-focus repeat groups, "
            "but it is a different subject/session at 200 mm with "
            "stabilization on, not the required three maximum-reproduction "
            "near/middle/far bursts.",
        ),
        (
            flat_1s,
            "Has at least 32 ISO-100, 1-s, f/5.6 CPL frames, but it is a "
            "converter-on focus bracket of a flat development slide, not "
            "a fixed-focus same-subject reference burst; the entire slide "
            "session is burned development.",
        ),
    ]
    sw4_analogues = [
        (
            GRID[1],
            "Exact 55-frame sw4 count and matching ISO/exposure/aperture, "
            "but converter-on, stabilization-on and burned; no eligible "
            "bare-lens B repeat exists.",
        ),
        (
            GRID[2],
            "Same burned converter-on grid session, but only 46 frames and "
            "not an eligible independent TC0 repeat.",
        ),
        (
            SLIDE[3],
            "A 182-frame sw4-labelled development bracket at ISO 100, 1 s "
            "and f/5.6, but converter-on, stabilization-on, burned and not "
            "two 55-frame bare-lens A/B passes.",
        ),
    ]
    sw10_analogues = [
        (
            GRID[3],
            "Burned converter-on sw10 stack with only 23 frames.",
        ),
        (
            GRID[4],
            "Exact 27-frame sw10 count, but converter-on, "
            "stabilization-on and burned; no eligible TC0 partner exists.",
        ),
        (
            SLIDE[4],
            "A 92-frame sw10-labelled development bracket, but "
            "converter-on, stabilization-on, burned and not a 27-frame "
            "bare-lens repeat pair.",
        ),
        (
            SLIDE[5],
            "A 197-frame sw10-labelled all-axis development bracket with "
            "different geometry; converter-on, stabilization-on and burned.",
        ),
    ]
    flat_analogues = [
        (
            flat_campaign,
            "Existing flat material is converter-on and not one of two "
            "independently repositioned 32-frame TC0 A/B groups from the "
            "incoming session.",
        ),
        (
            flat_1s,
            "A 60-frame ISO-100, 1-s, f/5.6 converter-on focus bracket; "
            "not two independent bare-lens diffuser groups and burned "
            "development.",
        ),
    ]
    dark_analogues = [
        (
            dark_campaign,
            "The only ISO-100, 1-s segment has 22 frames; it is not a "
            "32-frame bare-lens, warmed, same-session TC0 A/B dark group.",
        )
    ]

    blocks: list[dict[str, Any]] = []
    for name, line, focus_position in (
        ("TR-REF-NEAR", 108, "near third"),
        ("TR-REF-MID", 109, "middle third"),
        ("TR-REF-FAR", 110, "far third"),
    ):
        requirement = dict(reference_common)
        requirement["focus_position"] = focus_position
        blocks.append(
            inverted_block(
                by_id,
                name=name,
                frames=32,
                proposal_line=line,
                requirement=requirement,
                reason=no_reference,
                analogues=reference_analogues,
            )
        )

    witness_requirements = {
        "TC0-P0": (
            111,
            "fixed-focus burst at the recorded bare-lens 1.32x near reset",
        ),
        "TC0-P1": (
            112,
            "paired fixed-focus reset burst after move-away and return",
        ),
        "TC0-S4-A": (113, "fixed-focus sentinel immediately before sw4 A"),
        "TC0-E4-A": (
            115,
            "fixed-focus sentinel at sw4 A's untouched endpoint",
        ),
        "TC0-S4-B": (
            116,
            "fixed-focus sentinel after the repeated sw4 reset",
        ),
        "TC0-E4-B": (
            118,
            "fixed-focus sentinel at sw4 B's untouched endpoint",
        ),
        "TC0-S10-A": (
            119,
            "fixed-focus sentinel immediately before sw10 A",
        ),
        "TC0-E10-A": (
            121,
            "fixed-focus sentinel at sw10 A's untouched endpoint",
        ),
        "TC0-S10-B": (
            122,
            "fixed-focus sentinel after the repeated sw10 reset",
        ),
        "TC0-E10-B": (
            124,
            "fixed-focus sentinel at sw10 B's untouched endpoint",
        ),
    }
    for name, (line, capture) in witness_requirements.items():
        requirement = dict(tc0_common)
        requirement["capture"] = f"6-frame {capture}"
        blocks.append(
            inverted_block(
                by_id,
                name=name,
                frames=6,
                proposal_line=line,
                requirement=requirement,
                reason=(
                    no_tc0
                    + " No existing capture implements this named six-frame "
                    "witness at the required point in the TC0 reset/pass "
                    "sequence."
                ),
            )
        )

    for name, line, frames, step_width, pass_name, analogues in (
        ("TC0-sw4-A", 114, 55, 4, "A", sw4_analogues),
        ("TC0-sw4-B", 117, 55, 4, "B", sw4_analogues),
        ("TC0-sw10-A", 120, 27, 10, "A", sw10_analogues),
        ("TC0-sw10-B", 123, 27, 10, "B", sw10_analogues),
    ):
        requirement = dict(tc0_common)
        requirement["capture"] = (
            f"{frames}-frame automated Focus Bracket, step width "
            f"{step_width}, independent pass {pass_name}"
        )
        blocks.append(
            inverted_block(
                by_id,
                name=name,
                frames=frames,
                proposal_line=line,
                requirement=requirement,
                reason=(
                    no_tc0
                    + f" No eligible pair supplies two identical {frames}-frame "
                    f"step-width-{step_width} bare-lens passes at one geometry."
                ),
                analogues=analogues,
            )
        )

    for name, line, kind, assignment, analogues in (
        ("TC0-FLAT-A", 125, "flat", "A", flat_analogues),
        ("TC0-FLAT-B", 126, "flat", "B", flat_analogues),
        ("TC0-DARK-A", 127, "dark", "A", dark_analogues),
        ("TC0-DARK-B", 128, "dark", "B", dark_analogues),
    ):
        requirement = dict(tc0_common)
        if kind == "flat":
            if assignment == "A":
                requirement["capture"] = (
                    "32-frame bare-lens A diffuser flat at the scored exposure"
                )
            else:
                requirement["capture"] = (
                    "32-frame bare-lens B diffuser flat at the scored exposure; "
                    "move or rotate the diffuser after A"
                )
        else:
            requirement["capture"] = (
                f"32-frame independent bare-lens {assignment} dark at the "
                "scored exposure"
            )
        blocks.append(
            inverted_block(
                by_id,
                name=name,
                frames=32,
                proposal_line=line,
                requirement=requirement,
                reason=(
                    no_tc0
                    + " Existing calibration material is not an independent "
                    "32-frame TC0 group assigned to this incoming-session "
                    "master."
                ),
                analogues=analogues,
            )
        )

    blocks.sort(
        key=lambda item: int(item["request_source"].rsplit(":", 1)[1])
    )
    requested = sum(item["requested_frames"] for item in blocks)
    remaining = sum(item["remaining_frames"] for item in blocks)
    if requested != 448 or remaining != 448 or len(blocks) != 21:
        raise RuntimeError(
            f"inverted-gap arithmetic failed: blocks={len(blocks)} "
            f"requested={requested} remaining={remaining}"
        )

    return {
        "schema": "M141-capture-design-coverage-v1",
        "non_arbitration": {
            "text": (
                "This artifact preserves separate block ledgers for both "
                "designs. It does not choose which design governs."
            ),
            "status": "INHERITED",
            "source": "orchestrator direction for M141 follow-up",
        },
        "inventory_facts": {
            "stack_directories": manifest["summary"]["stack_directory_count"],
            "arw_frames": manifest["summary"]["arw_frame_count"],
            "focal_length_mm_values": all_focal_lengths,
            "image_stabilization_values": all_stabilization,
            "metadata_recoverable_magnification_stack_count": (
                recovered_magnifications
            ),
            "numeric_status": "VERIFIED",
            "source": str(MANIFEST),
            "implication": (
                "No inventoried stack proves the candidate TC0 bare-lens "
                "optical state or either design's required stabilization-off "
                "state."
            ),
        },
        "designs": [
            {
                "design_id": "committed-603-bench-sheet",
                "authority": "FROZEN COMMITTED CAPTURE REQUEST",
                "source": (
                    r"docs\capture-requests"
                    r"\2026-09-319-frame-session.md"
                ),
                "requested_frames": 603,
                "requested_frames_status": "INHERITED",
                "block_count": len(committed_gap["blocks"]),
                "block_count_status": "VERIFIED",
                "eligible_existing_frames": 0,
                "eligible_existing_frames_status": "VERIFIED",
                "blocks": committed_gap["blocks"],
            },
            {
                "design_id": "live-448-inverted-block",
                "authority": (
                    "UNCOMMITTED LIVE PROPOSAL SNAPSHOT; ORCHESTRATOR "
                    "GOVERNANCE DECISION PENDING"
                ),
                "source_snapshot": {
                    "path": str(TRUTH_PROPOSAL.relative_to(PROJECT_ROOT)),
                    "sha256": proposal_sha256,
                    "sha256_status": "VERIFIED",
                    "working_tree_state_when_audited": "modified/uncommitted",
                    "working_tree_state_status": "VERIFIED",
                    "working_tree_state_method": (
                        "git status --short -- "
                        "docs/proposals/2026-09-truth-referenced-detail.md"
                    ),
                    "proposal_decision_source": (
                        r"docs\proposals"
                        r"\2026-09-truth-referenced-detail.md:5-6"
                    ),
                    "block_table_source": (
                        r"docs\proposals"
                        r"\2026-09-truth-referenced-detail.md:104-133"
                    ),
                },
                "requested_frames": 448,
                "requested_frames_status": "INHERITED",
                "block_count": len(blocks),
                "block_count_status": "VERIFIED",
                "eligible_existing_frames": 0,
                "eligible_existing_frames_status": "VERIFIED",
                "remaining_frames_within_this_block": remaining,
                "remaining_frames_status": "VERIFIED",
                "proposal_integration_statement": {
                    "text": (
                        "The proposal says to replace the committed design's "
                        "160-frame reference block with this 448-frame block, "
                        "making that proposal's combined total 891 frames."
                    ),
                    "status": "INHERITED",
                    "source": (
                        r"docs\proposals"
                        r"\2026-09-truth-referenced-detail.md:135-147"
                    ),
                    "governance_note": (
                        "M141 does not adopt or reject that integration; the "
                        "committed 603 ledger remains separate."
                    ),
                },
                "development_only_near_match": {
                    "text": (
                        "The burned high-resolution slide supplies sw4/sw10 "
                        "and flat-path commissioning analogues only. It is "
                        "explicitly barred from the scored value."
                    ),
                    "status": "INHERITED",
                    "sources": [
                        r"docs\proposals"
                        r"\2026-09-truth-referenced-detail.md:1011-1016",
                        r"docs\proposals"
                        r"\2026-09-truth-referenced-detail.md:1171-1179",
                    ],
                },
                "blocks": blocks,
            },
        ],
    }


def main() -> int:
    manifest = load_manifest()
    holdouts = make_holdout_register(manifest)
    gaps = make_gap_analysis(manifest)
    design_coverage = make_design_coverage(manifest, gaps)
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
    (HERE / "capture-design-coverage.json").write_text(
        json.dumps(design_coverage, indent=2) + "\n",
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
                "inverted_gap_blocks": design_coverage["designs"][1][
                    "block_count"
                ],
                "inverted_remaining_frames": design_coverage["designs"][1][
                    "remaining_frames_within_this_block"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
