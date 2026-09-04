from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
OUT = LANE / "out"
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
COVER_REPORT = ROOT / "docs" / "research" / "cover-default.md"

ORIGINAL_W, ORIGINAL_H = 3516, 2344
BARE_W, BARE_H = 3470, 2312
INSET_W, INSET_H = 2958, 1800


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def percent(numerator: int, denominator: int) -> float:
    return 100.0 * numerator / denominator


def numbered_occurrences(lines: list[str], pattern: str) -> list[dict[str, Any]]:
    expression = re.compile(pattern, re.IGNORECASE)
    return [
        {"line": index, "text": text}
        for index, text in enumerate(lines, start=1)
        if expression.search(text)
    ]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    scorecard_lines = SCORECARD.read_text(encoding="utf-8").splitlines()
    cover_text = COVER_REPORT.read_text(encoding="utf-8")

    require(
        scorecard_lines[224]
        == "- Outputs must retain native scale. Resize is a hard invalidation.",
        "scorecard line 225 moved",
    )
    require(
        scorecard_lines[225]
        == "- Crops are fixed from the common-input overlap before outputs exist. Retained field of",
        "scorecard line 226 moved",
    )
    require(
        scorecard_lines[226] == "  view must be `>=99.0%` of that overlap.",
        "scorecard line 227 moved",
    )
    require(
        "A 256 px inset reduces the 3470x2312 crop to 2958x1800"
        in cover_text.replace("\n", " "),
        "closed COVER dimension sentence moved",
    )
    require(
        "3516x2344 plane (66.3672% of the emitted crop)"
        in cover_text.replace("\n", " "),
        "closed COVER denominator sentence moved",
    )

    original_pixels = ORIGINAL_W * ORIGINAL_H
    bare_pixels = BARE_W * BARE_H
    inset_pixels = INSET_W * INSET_H
    bare_vs_original = percent(bare_pixels, original_pixels)
    inset_vs_original = percent(inset_pixels, original_pixels)
    inset_vs_bare = percent(inset_pixels, bare_pixels)

    require(round(inset_vs_original, 4) == 64.6047, "64.6047% did not reproduce")
    require(round(inset_vs_bare, 4) == 66.3672, "66.3672% did not reproduce")

    phrase = numbered_occurrences(scorecard_lines, r"common-input overlap")
    require(len(phrase) == 1 and phrase[0]["line"] == 226, "overlap phrase moved")

    result = {
        "status": "GRAMMATICAL_READING_A_OPERATIONALLY_UNMEASURED",
        "source_hashes": {
            "scorecard": sha256(SCORECARD),
            "cover_default_report": sha256(COVER_REPORT),
        },
        "scorecard_text": {
            "line_225": scorecard_lines[224],
            "line_226": scorecard_lines[225],
            "line_227": scorecard_lines[226],
            "common_input_passage_lines_149_171": scorecard_lines[148:171],
            "native_output_passage_lines_173_179": scorecard_lines[172:179],
            "geometry_passage_lines_223_235": scorecard_lines[222:235],
            "common_input_overlap_occurrences": phrase,
            "all_overlap_occurrences": numbered_occurrences(
                scorecard_lines, r"\boverlap\b"
            ),
        },
        "arithmetic_109msdcf": {
            "original_plane_wh": [ORIGINAL_W, ORIGINAL_H],
            "bare_crop_wh": [BARE_W, BARE_H],
            "inset_crop_wh": [INSET_W, INSET_H],
            "original_pixels": original_pixels,
            "bare_pixels": bare_pixels,
            "inset_pixels": inset_pixels,
            "bare_vs_original_percent": bare_vs_original,
            "inset_vs_original_percent": inset_vs_original,
            "inset_vs_bare_percent": inset_vs_bare,
            "conditional_reading_a_bare_vs_overlap_percent": 100.0,
            "conditional_reading_a_inset_vs_overlap_percent": inset_vs_bare,
            "reading_b_bare_vs_original_percent": bare_vs_original,
        },
        "representation": {
            "cover_output_is_binned": True,
            "reason": (
                "3516x2344 is exactly half of 7032x4688 and the recorded COVER "
                "commands omit --demosaic; STREHL_FULLRES_GATHER controls the warp "
                "source rather than the emitted sampling grid"
            ),
            "coverage_fraction_is_per_stack": True,
        },
        "adjudication": {
            "grammatical_denominator": "COMMON_INPUT_OVERLAP",
            "reading_a_grammatically_supported": True,
            "reading_b_grammatically_supported": False,
            "overlap_construction_defined_by_scorecard": False,
            "missing_definition": [
                "registration/reference gauge",
                "valid-support margin",
                "overlap/intersection algorithm",
                "cross-method scene-coordinate mapping",
            ],
            "formal_109_fov_status": "UNMEASURED_DENOMINATOR_UNDEFINED",
            "bare_crop_is_not_automatically_the_denominator": True,
            "scorecard_defect": (
                "The antecedent is clear, but the scorecard does not operationally "
                "define the common-input overlap rectangle."
            ),
        },
    }
    write_json(OUT / "SCORECARD-OVERLAP-ADJUDICATION.json", result)
    print(
        "109MSDCF arithmetic: "
        f"bare/original={bare_vs_original:.9f}%, "
        f"inset/original={inset_vs_original:.9f}%, "
        f"inset/bare={inset_vs_bare:.9f}%"
    )
    print("denominator: Reading A grammatically; formal status UNMEASURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
