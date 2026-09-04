#!/usr/bin/env python3
"""Extract scorecard bars and verify read-only M8/M12 checker evidence."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np


sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
BASELINE = ROOT / "docs" / "research" / "SCORECARD-BASELINE.md"
M8_ROOT = ROOT / "experiments" / "M8-overshoot"
M8_STAGE = M8_ROOT / "out" / "stage-attribution"
M12_ROOT = ROOT / "experiments" / "m12-scorecard" / "out"
OUTPUT = Path(__file__).with_name("bar-card-audit.json")

EXPECTED_M8_BILINEAR_ARRAY_HASHES = {
    "flat-et1s": "B348E5BE9D9C7527BFD1ABE812B77B4EA41FA6B92F0A7BCE2B8001E18A506AA8",
    "flat-et2.5s": "FE150A22D9148FD9D7A7154B21F8095CE584F8EB32269A834887DF857A20FB5E",
    "flat-et6s": "DB4C1E9411F06B7126A67308A5B2E8C64DA94A5B40B17B2BDDDC1496F0C912E3",
}
EXPECTED_M8_BILINEAR_R_HASHES = {
    "flat-et1s": "2F5282ED4EE10F39379FB70D370CEF44DE25DA6044B2FD7B7519313FEBACABC3",
    "flat-et2.5s": "3D240E202DDA34543FA712387F187F4E89AE2DE678DB791C614FE3CEF91F70C5",
    "flat-et6s": "E4F9EE3F35948013D5237C106DC57A4E89E281866B3A529C8A335F3529F8D640",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def source(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)).replace("/", "\\"),
        "sha256": sha256(path),
    }


def numbered_lines(path: Path) -> list[tuple[int, str]]:
    return list(enumerate(path.read_text(encoding="utf-8").splitlines(), 1))


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_collapsed(lines: list[tuple[int, str]], phrase: str) -> list[dict[str, Any]]:
    wanted = collapse(phrase)
    hits: list[dict[str, Any]] = []
    for start in range(len(lines)):
        combined = ""
        for end in range(start, min(len(lines), start + 12)):
            combined = collapse(f"{combined} {lines[end][1]}")
            if wanted in combined:
                hits.append(
                    {
                        "start_line": lines[start][0],
                        "end_line": lines[end][0],
                        "text": combined,
                    }
                )
                break
    if not hits:
        return []
    shortest = min(
        hits,
        key=lambda hit: (
            hit["end_line"] - hit["start_line"],
            hit["start_line"],
        ),
    )
    return [shortest]


def extract_scorecard() -> dict[str, Any]:
    lines = numbered_lines(SCORECARD)
    raw = [text for _, text in lines]

    at_glance: dict[str, dict[str, Any]] = {}
    readiness: dict[str, dict[str, Any]] = {}
    standing: dict[str, dict[str, Any]] = {}

    for line_no, text in lines:
        match = re.match(r"^\| (M(?:[1-9]|1[0-2])) \| (.*?) \| (.*?) \|$", text)
        if match and 388 <= line_no < 412:
            axis, metric, bar = match.groups()
            at_glance[axis] = {
                "line": line_no,
                "metric": metric,
                "bar": bar,
                "verbatim": text,
            }

        match = re.match(
            r"^\| (M(?:[1-9]|1[0-2])) \| (.*?) \| (.*?) \|$", text
        )
        if match and 412 <= line_no < 441:
            axis, status, note = match.groups()
            readiness[axis] = {
                "line": line_no,
                "status": status,
                "note": note,
                "verbatim": text,
            }

        cells = text.split(" | ")
        if (
            1134 <= line_no < 1158
            and text.startswith("| M")
            and len(cells) >= 6
        ):
            axis = cells[0].removeprefix("| ")
            if re.fullmatch(r"M(?:[1-9]|1[0-2])", axis):
                standing[axis] = {"line": line_no, "verbatim": text}

    headings: list[tuple[int, str, int]] = []
    for line_no, text in lines:
        match = re.match(r"^### (M(?:[1-9]|1[0-2])) — (.+)$", text)
        if match:
            headings.append((line_no, match.group(1), raw.index(text, line_no - 1)))

    cards: dict[str, dict[str, Any]] = {}
    for heading_index, (line_no, axis, zero_index) in enumerate(headings):
        next_zero = (
            headings[heading_index + 1][2]
            if heading_index + 1 < len(headings)
            else next(
                index
                for index in range(zero_index + 1, len(raw))
                if raw[index].startswith("## ")
            )
        )
        section = raw[zero_index:next_zero]
        section_start = zero_index + 1

        labelled: dict[str, dict[str, Any]] = {}
        label_starts: list[tuple[int, str]] = []
        for offset, text in enumerate(section):
            match = re.match(r"^\*\*(.+?)\.\*\*(.*)$", text)
            if match:
                label_starts.append((offset, match.group(1)))

        for label_index, (offset, label) in enumerate(label_starts):
            end = (
                label_starts[label_index + 1][0]
                if label_index + 1 < len(label_starts)
                else len(section)
            )
            block = section[offset:end]
            while block and not block[-1].strip():
                block.pop()
            labelled[label] = {
                "start_line": section_start + offset,
                "end_line": section_start + offset + len(block) - 1,
                "verbatim_lines": block,
                "collapsed": collapse("\n".join(block)),
            }

        cards[axis] = {
            "start_line": line_no,
            "end_line": next_zero,
            "heading": section[0],
            "labelled_blocks": labelled,
        }

    assert list(at_glance) == [f"M{i}" for i in range(1, 13)]
    assert list(readiness) == [f"M{i}" for i in range(1, 13)]
    assert list(standing) == [f"M{i}" for i in range(1, 13)]
    assert list(cards) == [f"M{i}" for i in range(1, 13)]

    scorecard_text = SCORECARD.read_text(encoding="utf-8")
    section_text = {
        axis: "\n".join(
            raw[cards[axis]["start_line"] - 1 : cards[axis]["end_line"]]
        )
        for axis in cards
    }

    diagnostics = {
        "whole_scorecard_quantile_method_terms": [
            {
                "line": line_no,
                "text": text,
            }
            for line_no, text in lines
            if re.search(r"\b(?:quantile type|percentile method|nearest-rank)\b", text, re.I)
        ],
        "m2_eta_aggregation_terms": [
            term
            for term in (
                "median eta",
                "mean eta",
                "pooled eta",
                "maximum eta",
                "worst eta",
            )
            if term in section_text["M2"].lower()
        ],
        "m3_paired_p99_occurrences": section_text["M3"].count("paired p99"),
        "m4_noise_floor_occurrences": len(
            re.findall(r"\bnoise_floor\b", scorecard_text)
        ),
        "m5_source_signal_occurrences": len(
            re.findall(r"\bsource-signal\b", section_text["M5"])
        ),
        "m7_boundary_minimum_terms": [
            term
            for term in ("minimum boundaries", "at least 20 boundaries", "at least 24 boundaries")
            if term in section_text["M7"].lower()
        ],
        "m10_boundary_bias_success_mentions": cards["M10"]["labelled_blocks"][
            "Success"
        ]["collapsed"].lower().count("boundary bias"),
        "m10_valid_definition_mentions": len(
            re.findall(r"\bvalid(?:ity)? is\b|\bvalid means\b", section_text["M10"], re.I)
        ),
        "m11_live_input_schedule_terms": [
            term
            for term in ("capture cadence", "arrival cadence", "replay cadence", "frame interval")
            if term in section_text["M11"].lower()
        ],
        "m12_sampling_admission_terms": [
            term
            for term in ("jitter", "missed interval", "maximum gap", "max gap", "lateness")
            if term in section_text["M12"].lower()
        ],
        "rgb_metric_channel_semantics": {
            axis: [
                {
                    "line": cards[axis]["start_line"] + offset,
                    "text": text,
                }
                for offset, text in enumerate(
                    raw[cards[axis]["start_line"] - 1 : cards[axis]["end_line"]]
                )
                if re.search(
                    r"\b(per-channel|every channel|channel-wise|luminance|CIELAB|Lab)\b",
                    text,
                    re.I,
                )
            ]
            for axis in ("M2", "M3", "M4", "M5", "M6", "M7")
        },
        "rgb_core_computation_channel_semantics": {
            axis: [
                text
                for block_name in ("Exact computation", "Success")
                for text in cards[axis]["labelled_blocks"]
                .get(block_name, {})
                .get("verbatim_lines", [])
                if re.search(
                    r"\b(per-channel|every channel|channel-wise|luminance|CIELAB|Lab)\b",
                    text,
                    re.I,
                )
            ]
            for axis in ("M2", "M3", "M4", "M5", "M6", "M7")
        },
        "collapsed_phrase_checks": {
            "m8_result_read": find_collapsed(
                lines,
                "Checker commissioned and result read at `76b3d9cc`: FAIL",
            ),
            "m12_quiet_host": find_collapsed(
                lines,
                "the registered N/worker matrix still requires the reserved quiet host",
            ),
        },
    }

    return {
        "source": source(SCORECARD),
        "at_glance": at_glance,
        "readiness": readiness,
        "cards": cards,
        "standing": standing,
        "diagnostics": diagnostics,
    }


def audit_m8_rails() -> dict[str, Any]:
    captures: dict[str, Any] = {}
    aggregate = {
        "violation_coordinates": 0,
        "full_rail": 0,
        "full_rail_below_hull": 0,
        "nonrail": 0,
        "zero_rail": 0,
    }
    bilinear_m8_r = {
        "denominator": 0,
        "violations": 0,
    }

    for capture, expected_hash in EXPECTED_M8_BILINEAR_ARRAY_HASHES.items():
        path = (
            M8_STAGE
            / f"bilinear-scale-{capture}"
            / "m8-o-violations.npy"
        )
        actual_hash = sha256(path)
        assert actual_hash == expected_hash

        values = np.load(path, mmap_mode="r")
        required_fields = {
            "encoded",
            "direction",
            "lo",
            "hi",
            "tolerance",
            "signed_excess",
        }
        assert values.dtype.names is not None
        assert required_fields.issubset(values.dtype.names)

        full_rail = values["encoded"] == np.uint16(65535)
        zero_rail = values["encoded"] == np.uint16(0)
        below_hull = values["direction"] == np.int8(-1)
        impossible_full_rail = (
            full_rail
            & below_hull
            & ((values["lo"] - values["tolerance"]) > np.float32(1.0))
        )

        count = int(values.shape[0])
        full_count = int(np.count_nonzero(full_rail))
        impossible_count = int(np.count_nonzero(impossible_full_rail))
        zero_count = int(np.count_nonzero(zero_rail))
        nonrail_count = count - full_count - zero_count

        captures[capture] = {
            "source": source(path),
            "violation_coordinates": count,
            "full_rail": full_count,
            "full_rail_below_hull": impossible_count,
            "nonrail": nonrail_count,
            "zero_rail": zero_count,
            "minimum_lo_minus_tolerance_for_full_rail_below_hull": (
                float(
                    np.min(
                        values["lo"][impossible_full_rail]
                        - values["tolerance"][impossible_full_rail]
                    )
                )
                if impossible_count
                else None
            ),
            "maximum_lo_minus_tolerance_for_full_rail_below_hull": (
                float(
                    np.max(
                        values["lo"][impossible_full_rail]
                        - values["tolerance"][impossible_full_rail]
                    )
                )
                if impossible_count
                else None
            ),
        }

        aggregate["violation_coordinates"] += count
        aggregate["full_rail"] += full_count
        aggregate["full_rail_below_hull"] += impossible_count
        aggregate["nonrail"] += nonrail_count
        aggregate["zero_rail"] += zero_count

        r_path = M8_STAGE / f"bilinear-scale-{capture}-r.txt"
        assert sha256(r_path) == EXPECTED_M8_BILINEAR_R_HASHES[capture]
        r_result = json.loads(r_path.read_text(encoding="utf-8"))
        bilinear_m8_r["denominator"] += int(r_result["denominator"])
        bilinear_m8_r["violations"] += int(r_result["violations"])

    assert aggregate == {
        "violation_coordinates": 980097,
        "full_rail": 977684,
        "full_rail_below_hull": 977684,
        "nonrail": 2413,
        "zero_rail": 0,
    }

    aggregate["proof"] = (
        "For each full-rail-below-hull coordinate, encoded/65535 is exactly 1.0 "
        "while lo-tolerance is greater than 1.0. No unsigned 16-bit sample can "
        "reach the registered lower hull at that coordinate."
    )
    aggregate["fraction_of_bilinear_m8_o_violations_full_rail_below_hull"] = (
        aggregate["full_rail_below_hull"]
        / aggregate["violation_coordinates"]
    )
    assert bilinear_m8_r == {
        "denominator": 6131678976,
        "violations": 0,
    }

    return {
        "sources": {
            "admitted_results": source(M8_ROOT / "results.json"),
        },
        "captures": captures,
        "aggregate": aggregate,
        "bilinear_m8_r": bilinear_m8_r,
    }


def audit_checker_evidence() -> dict[str, Any]:
    baseline_lines = numbered_lines(BASELINE)
    baseline_phrases = {
        phrase: find_collapsed(baseline_lines, phrase)
        for phrase in (
            "M2 residual efficiency / blur guard",
            "Rail eligibility census",
            "M3–M5 and M8 score checkers were not commissioned",
            "M9/M10 have no compatible product to check",
            "M2 specifies no aggregation functional for eta",
            "M5's “longest failed run along the focus-sweep direction” is undefined",
        )
    }

    m12_hash = json.loads(
        (M12_ROOT / "commission.json").read_text(encoding="utf-8")
    )
    m12_memory = json.loads(
        (M12_ROOT / "memory-commission.json").read_text(encoding="utf-8")
    )
    m12_audit_path = M12_ROOT / "campaign-16bc3e3d" / "audit.json"
    m12_audit = json.loads(m12_audit_path.read_text(encoding="utf-8"))

    return {
        "baseline": {
            "source": source(BASELINE),
            "phrase_checks": baseline_phrases,
        },
        "m12": {
            "hash_checker_source": source(M12_ROOT / "commission.json"),
            "hash_checker_status": m12_hash["status"],
            "one_output_lsb_went_red": m12_hash["hash_gate"][
                "one_output_lsb_went_red"
            ],
            "memory_checker_source": source(M12_ROOT / "memory-commission.json"),
            "memory_checker_status": m12_memory["status"],
            "seven_gib_child_exceeded_six_gib_bar": m12_memory["verdict"][
                "seven_gib_child_exceeded_six_gib_bar"
            ],
            "diagnostic_audit_source": source(m12_audit_path),
            "sampling_protocol_exactly_achieved": m12_audit["memory"][
                "sampling_protocol_exactly_achieved"
            ],
            "requested_sample_interval_ms": m12_audit["memory"][
                "requested_sample_interval_ms"
            ],
            "worst_max_gap_ms": m12_audit["memory"]["worst_max_gap_ms"],
            "ratio_protocol_caveat": m12_audit["memory"][
                "ratio_protocol_caveat"
            ],
        },
    }


def main() -> None:
    scorecard_commit = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "log",
            "-1",
            "--format=%H",
            "--",
            str(SCORECARD.relative_to(ROOT)),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    payload = {
        "schema": 1,
        "scorecard_last_commit": scorecard_commit,
        "method": (
            "Read-only extraction from documents and existing artifacts; no "
            "renderer, stacker, benchmark, or campaign was invoked."
        ),
        "scorecard": extract_scorecard(),
        "m8_rail_audit": audit_m8_rails(),
        "checker_evidence": audit_checker_evidence(),
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
