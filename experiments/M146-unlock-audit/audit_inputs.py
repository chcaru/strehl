from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "experiments" / "M141-capture-inventory" / "capture-manifest.json"
REGISTER_PATH = ROOT / "experiments" / "M141-capture-inventory" / "holdout-register.json"
OUTPUT_PATH = Path(__file__).with_name("capture-map.json")
SOURCE_PATHS = [
    ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md",
    ROOT / "docs" / "capture-requests" / "2026-09-319-frame-session.md",
    ROOT / "docs" / "research" / "M-PHASE0-SPLIT2.md",
    ROOT / "docs" / "research" / "M133-blocker-audit.md",
    ROOT / "docs" / "research" / "M140-readiness.md",
    ROOT / "docs" / "research" / "M141-capture-inventory.md",
    ROOT / "docs" / "research" / "M144-reference-uncertainty.md",
    MANIFEST_PATH,
    REGISTER_PATH,
]


AXIS_INPUTS = {
    "M2": [
        {
            "stack_id": "requests\\12-bee-iso-var-no-bracket-32-repeat-diff-light",
            "role": "two score-bearing ISO-100 fixed-focus 32-frame light blocks",
            "segment_filter": {"iso": 100},
        },
        {
            "stack_id": "requests\\10-paper-iso-var",
            "role": "ISO-100 paper transfer/control block",
            "segment_filter": {"iso": 100},
        },
        {
            "stack_id": "requests\\6-11-extended-dark-frames",
            "role": "dark/FPN control",
            "segment_filter": {"iso": 100},
        },
        {
            "stack_id": (
                "requests\\misc-diagnostic\\high-res-calibration-slide-cpl\\"
                "flat-sw4-cpl\\flat-et6s-sw4-cpl"
            ),
            "role": "burned SNR-ladder commissioning source; not a matched repeat",
        },
        {
            "stack_id": (
                "requests\\misc-diagnostic\\high-res-calibration-slide-cpl\\"
                "flat-sw4-cpl\\flat-et2.5s-sw4-cpl"
            ),
            "role": "burned SNR-ladder commissioning source; not a matched repeat",
        },
        {
            "stack_id": (
                "requests\\misc-diagnostic\\high-res-calibration-slide-cpl\\"
                "flat-sw4-cpl\\flat-et1s-sw4-cpl"
            ),
            "role": "burned SNR-ladder commissioning source; not a matched repeat",
        },
    ],
    "M3": [
        {
            "stack_id": "duck-tape-side-layers-cpl",
            "role": "score-bearing fibre/occlusion boundaries",
        },
        {
            "stack_id": "chia-seeds-cpl",
            "role": "score-bearing broad-veil crevices",
        },
        {
            "stack_id": "flower-bud-with-background-fern-cpl",
            "role": "score-bearing multilayer boundaries",
        },
        {
            "stack_id": (
                "requests\\19-razor-edge\\horizontal-flat\\"
                "razor-edge-horizontal-flat-sw4-f5.6-cpl"
            ),
            "role": "isolated-boundary control",
        },
    ],
    "M4": [
        {
            "stack_id": "medication-pill-cpl",
            "role": "named input-flat commissioning source",
        },
        {
            "stack_id": "bee-1-cpl",
            "role": "possible referent of ambiguous 'bee background'",
        },
        {
            "stack_id": "bee-2-cpl",
            "role": "possible referent of ambiguous 'bee background'",
        },
        {
            "stack_id": "bee-3-cpl",
            "role": "possible referent of ambiguous 'bee background'",
        },
        {
            "stack_id": "requests\\12-bee-iso-var-no-bracket-32-repeat-diff-light",
            "role": "possible referent of ambiguous 'bee background'",
        },
        {
            "stack_id": "foam",
            "role": "named input-flat commissioning source",
        },
        {
            "stack_id": "coffee-bubbles",
            "role": "named input-flat commissioning source",
        },
        {
            "stack_id": (
                "requests\\misc-diagnostic\\high-res-calibration-slide-cpl\\"
                "flat-sw4-cpl\\flat-et6s-sw4-cpl"
            ),
            "role": "burned flat-path commissioning source; cannot score",
        },
        {
            "stack_id": (
                "requests\\misc-diagnostic\\high-res-calibration-slide-cpl\\"
                "flat-sw4-cpl\\flat-et2.5s-sw4-cpl"
            ),
            "role": "burned flat-path commissioning source; cannot score",
        },
        {
            "stack_id": (
                "requests\\misc-diagnostic\\high-res-calibration-slide-cpl\\"
                "flat-sw4-cpl\\flat-et1s-sw4-cpl"
            ),
            "role": "burned flat-path commissioning source; cannot score",
        },
        {
            "stack_id": "requests\\7-aperture-pairs\\fabric-weave-f5.6-sw5-cpl",
            "role": "score-bearing structured-edge fabric source",
        },
        {
            "stack_id": "requests\\7-aperture-pairs\\fabric-weave-f8-sw5-cpl",
            "role": "score-bearing structured-edge fabric source",
        },
        {
            "stack_id": "requests\\7-aperture-pairs\\fabric-weave-f11-sw5-cpl",
            "role": "score-bearing structured-edge fabric source",
        },
        {
            "stack_id": "duck-tape-side-layers-cpl",
            "role": "score-bearing structured-edge source",
        },
        {
            "stack_id": "flower-bud-with-background-fern-cpl",
            "role": "score-bearing structured-edge source",
        },
        {
            "stack_id": "requests\\30-calibration-grid\\calibration-grid-1-sw1-cpl",
            "role": "burned detector-commissioning source",
        },
        {
            "stack_id": "requests\\30-calibration-grid\\calibration-grid-1-sw4-cpl",
            "role": "burned detector-commissioning source",
        },
        {
            "stack_id": "requests\\30-calibration-grid\\calibration-grid-2-sw4-cpl",
            "role": "burned detector-commissioning source",
        },
        {
            "stack_id": "requests\\30-calibration-grid\\calibration-grid-1-sw10-cpl",
            "role": "burned detector-commissioning source",
        },
        {
            "stack_id": "requests\\30-calibration-grid\\calibration-grid-2-sw10-cpl",
            "role": "burned detector-commissioning source",
        },
    ],
    "M11": [
        {
            "stack_id": "bee-1-cpl",
            "role": "N=299, first N=33/100, and N=96/97/98/99 prefixes",
        },
        {
            "stack_id": "coffee-bean",
            "role": "N=105",
        },
    ],
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def setting_counts(stack: dict, key: str) -> list[dict]:
    return [
        {"value": item["value"], "frames": item["frame_count"]}
        for item in stack.get("settings", {}).get(key, [])
    ]


def build_rulings(register: dict) -> dict[str, dict]:
    rulings: dict[str, dict] = {}
    for unit in register["burned_or_spent_units"]:
        for stack_id in unit["members"]:
            rulings[stack_id] = {
                "ruling": unit["ruling"],
                "evidence_class": unit["ruling"],
                "source": unit["sources"],
                "unit_id": unit["unit_id"],
            }
    for row in register["clean_registered_holdout_rows"]:
        rulings[row["stack_id"]] = {
            "ruling": row["ruling"],
            "evidence_class": row["evidence_class"],
            "source": row["source"],
        }
    for row in register["explicit_not_holdout_rows"]:
        rulings[row["stack_id"]] = {
            "ruling": row["ruling"],
            "evidence_class": row["evidence_class"],
            "source": row["source"],
        }
    for row in register["unclassified_stack_ids"]:
        rulings[row["stack_id"]] = {
            "ruling": row["ruling"],
            "evidence_class": row["ruling"],
            "source": row["source"],
        }
    return rulings


def main() -> None:
    manifest = load_json(MANIFEST_PATH)
    register = load_json(REGISTER_PATH)
    stacks = {stack["stack_id"]: stack for stack in manifest["stacks"]}
    segments_by_stack: dict[str, list[dict]] = {}
    for segment in manifest["setting_segments"]:
        segments_by_stack.setdefault(segment["stack_id"], []).append(segment)
    rulings = build_rulings(register)

    axes: dict[str, list[dict]] = {}
    for axis, requested in AXIS_INPUTS.items():
        rows = []
        for item in requested:
            stack_id = item["stack_id"]
            if stack_id not in stacks:
                raise KeyError(f"missing stack in manifest: {stack_id}")
            if stack_id not in rulings:
                raise KeyError(f"missing evidence ruling: {stack_id}")
            stack = stacks[stack_id]
            relevant_segments = segments_by_stack.get(stack_id, [])
            for key, value in item.get("segment_filter", {}).items():
                relevant_segments = [
                    segment
                    for segment in relevant_segments
                    if segment.get(key) == value
                ]
            relevant_segments = [
                {
                    key: segment[key]
                    for key in (
                        "segment_index",
                        "frame_count",
                        "first_file",
                        "last_file",
                        "iso",
                        "exposure_seconds",
                        "aperture",
                        "image_stabilization",
                    )
                }
                for segment in relevant_segments
            ]
            rows.append(
                {
                    "stack_id": stack_id,
                    "path": stack["path"],
                    "role": item["role"],
                    "frame_count": stack["frame_count"],
                    "first_file": stack["first_file"],
                    "last_file": stack["last_file"],
                    "capture_contiguous": stack["capture_contiguous"],
                    "settings": {
                        "iso": setting_counts(stack, "iso"),
                        "exposure_seconds": setting_counts(
                            stack, "exposure_seconds"
                        ),
                        "aperture": setting_counts(stack, "aperture"),
                        "image_stabilization": setting_counts(
                            stack, "image_stabilization"
                        ),
                        "release_mode": setting_counts(stack, "release_mode"),
                    },
                    "magnification_status": stack["magnification"]["status"],
                    "relevant_segments": relevant_segments,
                    **rulings[stack_id],
                }
            )
        axes[axis] = rows

    output = {
        "schema": "M146-capture-map-v1",
        "method": (
            "Metadata-only join of the M141 capture manifest and holdout register; "
            "no image pixels or score outcomes read."
        ),
        "sources": {
            str(path.relative_to(ROOT)): sha256(path) for path in SOURCE_PATHS
        },
        "manifest_summary": manifest["summary"],
        "axes": axes,
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
