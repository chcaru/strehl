"""Manifest-only preflight for a formal real-data M1 run.

No capture, TIFF, NPY or RAW pixel path is opened.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATHS = {
    "input": Path("experiments/SCORECARD-BASELINE/out/INPUT-MANIFEST.json"),
    "sites": Path("experiments/SCORECARD-BASELINE/out/SITE-MANIFEST.json"),
    "geometry": Path("experiments/SCORECARD-BASELINE/out/GEOMETRY-AUDIT.json"),
    "repeat_alignment": Path(
        "experiments/M-PHASE0-SPLIT2/out/alignment-gate.json"
    ),
}


def read_json(relative: Path) -> tuple[dict, str]:
    data = (ROOT / relative).read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def main() -> int:
    documents = {}
    hashes = {}
    for name, relative in PATHS.items():
        documents[name], hashes[name] = read_json(relative)

    input_manifest = documents["input"]
    site_manifest = documents["sites"]
    geometry = documents["geometry"]
    repeat_alignment = documents["repeat_alignment"]

    floor = input_manifest["m1_floor_preflight"]
    colour = input_manifest["colour_space_conflict"]
    render = input_manifest["decoder"]["settings"]
    repeat_rows = repeat_alignment["runs"]
    failed_repeat = [
        row for row in repeat_rows
        if not row["passes_translation_only_gate"]
    ]

    blockers = {
        "matching_dark_count_zero": floor["matching_dark_count"] == 0,
        "matching_flat_count_zero": floor["matching_flat_count"] == 0,
        "defocused_source_undefined": (
            "defocused source" in site_manifest["m1"]["formal_status"]
        ),
        "colour_space_conflict": (
            colour["common_contract"]
            != colour["coefficient_identity"]
        ),
        "render_not_common_prophoto": (
            render["output_color"] != "linear ProPhoto RGB D50"
        ),
        "baseline_geometry_invalid": bool(
            geometry["all_scale_invalid"]
        ),
        "independent_repeat_alignment_failed": bool(failed_repeat),
    }
    result = {
        "schema": 1,
        "status": (
            "FORMAL_REAL_M1_BLOCKED"
            if any(blockers.values())
            else "FORMAL_REAL_M1_PREFLIGHT_GREEN"
        ),
        "blockers": blockers,
        "details": {
            "matching_dark_count": floor["matching_dark_count"],
            "matching_flat_count": floor["matching_flat_count"],
            "site_manifest_status": site_manifest["m1"]["formal_status"],
            "common_colour_contract": colour["common_contract"],
            "coefficient_identity": colour["coefficient_identity"],
            "render_output_color": render["output_color"],
            "all_scale_invalid": geometry["all_scale_invalid"],
            "failed_repeat_max_residual_native_px": [
                row["maximum_nontranslation_residual_rms_native_pixels"]
                for row in failed_repeat
            ],
        },
        "manifest_sha256": hashes,
        "pixel_files_opened": 0,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "FORMAL_REAL_M1_BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
