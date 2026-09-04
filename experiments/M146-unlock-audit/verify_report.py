from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "docs" / "research" / "M146-unlock-audit.md"
SCORECARD_PATH = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
CAPTURE_MAP_PATH = Path(__file__).with_name("capture-map.json")
OUTPUT_PATH = Path(__file__).with_name("verification.json")


SUCCESS_BARS = {
    "M2": {
        "lines": (633, 635),
        "text": (
            "**Success.** The proposal says “strictly lower noise” but supplies no "
            "practical margin (`2026-08-sota-path.md` lines 192–195). "
            "**SCORECARD ADDITION:** `eta <=1.10` and "
            "`UCB95(sigma_strehl / min(sigma_comparator)) <=0.950`."
        ),
    },
    "M3": {
        "lines": (678, 681),
        "text": (
            "**Success.** **SCORECARD ADDITION:** median `h_e` and `v_e <=0.01`; "
            "p99 of each `<=0.05`; affected-edge point rate `<=1%` and Wilson "
            "UCB95 `<=2%`; median edge-width ratio in `[0.95,1.05]`; median "
            "`rho_edge>=0.90`; strehl’s paired p99 is no greater than the best "
            "comparator’s."
        ),
    },
    "M4": {
        "lines": (716, 718),
        "text": (
            "**Success.** **SCORECARD ADDITION:** median `Q_flat<=1.00`; "
            "failed-site point rate `<=1%`, Wilson UCB95 `<=2%`; strehl’s rate "
            "is no greater than the best comparator’s."
        ),
    },
    "M11": {
        "lines": (1092, 1098),
        "text": (
            "**Success.** **PROPOSAL BARS:** warm common-input strehl throughput "
            "`>=2.00x` the best comparator; native-RAW CPU-only at 16 workers "
            "`<=0.15 s/frame`; hybrid `<=0.06 s/frame`; cold `<=warm+20 s`; "
            "first-100 streaming master closed and readable `<=10 s` after "
            "`DSC00100.ARW` becomes available. **SCORECARD FREEZE OF D5'S "
            "“ROUGHLY 2x”:** candidate/default-baseline warm-wall ratio `<=2.00`. "
            "The baseline build/hash and its complete settings are frozen before "
            "the candidate is timed."
        ),
    },
}


EXPECTED_CAPTURE_ROWS = {
    "M2": {
        "requests\\12-bee-iso-var-no-bracket-32-repeat-diff-light": (
            576,
            "CLEAN REGISTERED HOLDOUT",
        ),
        "requests\\10-paper-iso-var": (110, "NOT HOLDOUT"),
        "requests\\6-11-extended-dark-frames": (506, "NOT HOLDOUT"),
    },
    "M3": {
        "duck-tape-side-layers-cpl": (197, "CLEAN REGISTERED HOLDOUT"),
        "chia-seeds-cpl": (130, "CLEAN REGISTERED HOLDOUT"),
        "flower-bud-with-background-fern-cpl": (
            299,
            "CLEAN REGISTERED HOLDOUT",
        ),
        (
            "requests\\19-razor-edge\\horizontal-flat\\"
            "razor-edge-horizontal-flat-sw4-f5.6-cpl"
        ): (67, "NOT HOLDOUT"),
    },
    "M11": {
        "bee-1-cpl": (299, "CLEAN REGISTERED HOLDOUT"),
        "coffee-bean": (105, "NOT HOLDOUT"),
    },
}


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    report_without_quote_markers = re.sub(r"(?m)^>\s?", "", report)
    report_collapsed = collapse(report_without_quote_markers)
    scorecard_lines = SCORECARD_PATH.read_text(encoding="utf-8").splitlines()
    capture_map = json.loads(CAPTURE_MAP_PATH.read_text(encoding="utf-8"))
    checks: list[dict] = []

    for axis, bar in SUCCESS_BARS.items():
        start, end = bar["lines"]
        source = collapse("\n".join(scorecard_lines[start - 1 : end]))
        expected = collapse(bar["text"])
        source_ok = source == expected
        report_ok = expected in report_collapsed
        checks.append(
            {
                "name": f"{axis} success bar exact at lines {start}-{end}",
                "passed": source_ok and report_ok,
                "source_exact": source_ok,
                "report_contains_exact": report_ok,
            }
        )

    rows_by_axis = {
        axis: {row["stack_id"]: row for row in rows}
        for axis, rows in capture_map["axes"].items()
    }
    for axis, expected_rows in EXPECTED_CAPTURE_ROWS.items():
        for stack_id, (frame_count, ruling) in expected_rows.items():
            row = rows_by_axis[axis].get(stack_id)
            checks.append(
                {
                    "name": f"{axis} capture {stack_id}",
                    "passed": bool(
                        row
                        and row["frame_count"] == frame_count
                        and row["ruling"] == ruling
                        and {
                            item["value"]
                            for item in row["settings"]["image_stabilization"]
                        }
                        == {"On"}
                    ),
                }
            )

    bee = rows_by_axis["M2"][
        "requests\\12-bee-iso-var-no-bracket-32-repeat-diff-light"
    ]
    bee_iso100 = [
        segment
        for segment in bee["relevant_segments"]
        if segment["iso"] == 100
    ]
    checks.append(
        {
            "name": "M2 exact ISO-100 blocks",
            "passed": [
                (
                    segment["frame_count"],
                    segment["first_file"],
                    segment["last_file"],
                    segment["exposure_seconds"],
                )
                for segment in bee_iso100
            ]
            == [
                (32, "DSC00328.ARW", "DSC00359.ARW", 1.6),
                (32, "DSC00584.ARW", "DSC00615.ARW", 1.6),
            ],
        }
    )

    checks.append(
        {
            "name": "manifest universal stabilization finding",
            "passed": capture_map["manifest_summary"]["all_arw_image_stabilization"]
            == ["On"],
        }
    )

    for relative, expected_hash in capture_map["sources"].items():
        path = ROOT / Path(relative)
        checks.append(
            {
                "name": f"source hash {relative}",
                "passed": path.is_file() and sha256(path) == expected_hash,
            }
        )

    expected_verdicts = {
        "M2": "NEEDS_NEW_CAPTURE",
        "M3": "BLOCKED_FOR_ANOTHER_REASON",
        "M4": "BLOCKED_FOR_ANOTHER_REASON",
        "M11": "BLOCKED_FOR_ANOTHER_REASON",
    }
    for axis, verdict in expected_verdicts.items():
        checks.append(
            {
                "name": f"report verdict {axis}",
                "passed": bool(
                    re.search(
                        rf"\|\s*{axis}\s*\|\s*\*\*{re.escape(verdict)}\*\*",
                        report,
                    )
                ),
            }
        )

    failed = [check["name"] for check in checks if not check["passed"]]
    output = {
        "schema": "M146-verification-v1",
        "method": (
            "Whitespace-collapsed exact quote checks, source-hash checks, and "
            "metadata/status assertions; no image pixels or score outcomes read."
        ),
        "report": str(REPORT_PATH.relative_to(ROOT)),
        "passed": not failed,
        "failed": failed,
        "checks": checks,
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if failed:
        raise SystemExit("verification failed: " + "; ".join(failed))


if __name__ == "__main__":
    main()
