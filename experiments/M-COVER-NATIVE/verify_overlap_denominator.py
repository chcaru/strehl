from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
OUT = LANE / "out"
REPORT = ROOT / "docs" / "research" / "M-COVER-NATIVE.md"
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
COVER_REPORT = ROOT / "docs" / "research" / "cover-default.md"
METHOD_COMMIT = "c829df98"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)


def main() -> int:
    result = read_json(OUT / "SCORECARD-OVERLAP-ADJUDICATION.json")
    report = REPORT.read_text(encoding="utf-8")
    scorecard_lines = SCORECARD.read_text(encoding="utf-8").splitlines()

    require(
        result["status"] == "GRAMMATICAL_READING_A_OPERATIONALLY_UNMEASURED",
        "adjudication status moved",
    )
    require(
        result["source_hashes"]["scorecard"] == sha256(SCORECARD),
        "scorecard hash moved",
    )
    require(
        result["source_hashes"]["cover_default_report"] == sha256(COVER_REPORT),
        "COVER report hash moved",
    )

    arithmetic = result["arithmetic_109msdcf"]
    original = 3516 * 2344
    bare = 3470 * 2312
    inset = 2958 * 1800
    expected = {
        "original_pixels": original,
        "bare_pixels": bare,
        "inset_pixels": inset,
        "bare_vs_original_percent": 100.0 * bare / original,
        "inset_vs_original_percent": 100.0 * inset / original,
        "inset_vs_bare_percent": 100.0 * inset / bare,
    }
    for key in ("original_pixels", "bare_pixels", "inset_pixels"):
        require(arithmetic[key] == expected[key], f"{key} moved")
    for key in (
        "bare_vs_original_percent",
        "inset_vs_original_percent",
        "inset_vs_bare_percent",
    ):
        require(close(arithmetic[key], expected[key]), f"{key} moved")
    require(
        close(
            arithmetic["conditional_reading_a_inset_vs_overlap_percent"],
            expected["inset_vs_bare_percent"],
        ),
        "conditional Reading A arithmetic moved",
    )

    text = result["scorecard_text"]
    require(text["line_225"] == scorecard_lines[224], "scorecard line 225 moved")
    require(text["line_226"] == scorecard_lines[225], "scorecard line 226 moved")
    require(text["line_227"] == scorecard_lines[226], "scorecard line 227 moved")
    require(
        text["common_input_overlap_occurrences"]
        == [
            {
                "line": 226,
                "text": (
                    "- Crops are fixed from the common-input overlap before outputs "
                    "exist. Retained field of"
                ),
            }
        ],
        "common-input overlap gained another definition",
    )

    adjudication = result["adjudication"]
    require(
        adjudication["grammatical_denominator"] == "COMMON_INPUT_OVERLAP",
        "grammatical denominator moved",
    )
    require(adjudication["reading_a_grammatically_supported"], "Reading A moved")
    require(not adjudication["reading_b_grammatically_supported"], "Reading B moved")
    require(
        not adjudication["overlap_construction_defined_by_scorecard"],
        "overlap unexpectedly became defined",
    )
    require(
        adjudication["formal_109_fov_status"] == "UNMEASURED_DENOMINATOR_UNDEFINED",
        "formal 109 status moved",
    )

    for required in (
        "Reading A is the only grammatical reading",
        "`UNMEASURED_DENOMINATOR_UNDEFINED`",
        "**97.344368212%**",
        "**64.604712926%**",
        "**66.367180878%**",
        "default **binned** output representation",
        "per stack/solve",
        "must not be attributed to stack depth alone",
    ):
        require(required in report, f"report omits: {required}")

    method_is_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", METHOD_COMMIT, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    require(method_is_ancestor.returncode == 0, "method commit is not an ancestor")
    method_script_is_frozen = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            METHOD_COMMIT,
            "--",
            "experiments/M-COVER-NATIVE/overlap_denominator.py",
        ],
        cwd=ROOT,
        check=False,
    )
    require(method_script_is_frozen.returncode == 0, "method script drifted")

    print(
        "overlap-denominator verification passed: Reading A grammatical, "
        "109 formally UNMEASURED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
