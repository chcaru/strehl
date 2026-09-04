#!/usr/bin/env python3
"""Read-only audit of the existing M8 and M12 score artifacts."""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path
from typing import Any


REGISTERED_COUNTS = (33, 105, 299)
WORKERS = (1, 2, 4, 8, 16)
MODULO_COUNTS = (96, 97, 98, 99)


def find_collapsed_spans(
    path: Path, phrases: tuple[str, ...]
) -> dict[str, list[dict[str, int]]]:
    text = path.read_text(encoding="utf-8")
    result: dict[str, list[dict[str, int]]] = {}
    for phrase in phrases:
        pattern = re.escape(phrase).replace(r"\ ", r"\s+")
        spans = []
        for match in re.finditer(pattern, text):
            spans.append(
                {
                    "start_line": text.count("\n", 0, match.start()) + 1,
                    "end_line": text.count("\n", 0, match.end()) + 1,
                }
            )
        result[phrase] = spans
    return result


def audit_m8(repo: Path) -> dict[str, Any]:
    result_path = repo / "experiments" / "M8-overshoot" / "results.json"
    report_path = repo / "docs" / "research" / "M8-overshoot.md"
    status_path = repo / "docs" / "STATUS.md"
    comparative_path = repo / "docs" / "research" / "M8-COMPARATIVE.md"
    agents_path = repo / "AGENTS.md"

    result = json.loads(result_path.read_text(encoding="utf-8"))
    aggregate = result["aggregate"]

    agents_lines = agents_path.read_text(encoding="utf-8").splitlines()
    ledger_start = next(
        index
        for index, line in enumerate(agents_lines)
        if line.startswith("### Milestone allocation ledger")
    )
    ledger_end = next(
        (
            index
            for index in range(ledger_start + 1, len(agents_lines))
            if agents_lines[index].startswith("### ")
        ),
        len(agents_lines),
    )
    ledger_m8comp_lines = [
        index + 1
        for index in range(ledger_start, ledger_end)
        if "M8COMP" in agents_lines[index]
    ]

    return {
        "result_path": str(result_path.relative_to(repo)),
        "report_path": str(report_path.relative_to(repo)),
        "m8_r": aggregate["m8_r"],
        "m8_o": aggregate["m8_o"],
        "commissioning_passed": result["commissioning"]["passed"],
        "bars_pass": {
            "m8_r_zero": aggregate["m8_r"]["violations"] == 0,
            "m8_o_zero": aggregate["m8_o"]["violations"] == 0,
        },
        "report_evidence_lines": find_collapsed_spans(
            report_path,
            (
                "**Verdict: FAIL; no blocker.**",
                "I measured scorecard v1.7's M8 text",
                "Commissioning passed both directions:",
                "Aggregate M8-R is",
                "aggregate M8-O is",
                "registered source-hull invariant fails.",
            ),
        ),
        "status_evidence_lines": find_collapsed_spans(
            status_path,
            (
                "**M8 is measured. It reads FAIL.**",
                "checked against that file before this section was written.",
                "M8 is the only axis with a value and it reads FAIL.",
            ),
        ),
        "comparative_governance_lines": find_collapsed_spans(
            comparative_path,
            (
                "candidate comparative reading",
                "not an M8 score",
                "scorecard currently owns M8 as a strehl self-check",
                "Final controlled `focus-stack` result: `UNMEASURED`.",
            ),
        ),
        "ledger": {
            "start_line": ledger_start + 1,
            "end_line": ledger_end,
            "m8comp_matches": ledger_m8comp_lines,
        },
    }


def audit_m12(repo: Path) -> dict[str, Any]:
    root = repo / "experiments" / "m12-scorecard"
    campaign = root / "out" / "campaign-16bc3e3d"
    records_path = campaign / "records.jsonl"
    summary_path = campaign / "summary.json"
    audit_path = campaign / "audit.json"

    raw_lines = records_path.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in raw_lines if line.strip()]
    by_kind = collections.Counter(str(row["kind"]) for row in records)
    registration_statuses = sorted(
        {str(row.get("registration_status")) for row in records}
    )

    main_warmups = {
        (int(row["limit"]), int(row["workers"]))
        for row in records
        if row["kind"] == "warmup" and row.get("valid")
    }
    main_scored = {
        (int(row["limit"]), int(row["workers"]), int(row["repetition"]))
        for row in records
        if row["kind"] == "scored" and row.get("valid")
    }
    modulo_warmups = {
        int(row["limit"])
        for row in records
        if row["kind"] == "modulo-warmup" and row.get("valid")
    }
    modulo_scored = {
        (int(row["limit"]), int(row["repetition"]))
        for row in records
        if row["kind"] == "modulo-scored" and row.get("valid")
    }

    expected_main_warmups = {
        (count, workers) for count in REGISTERED_COUNTS for workers in WORKERS
    }
    expected_main_scored = {
        (count, workers, repetition)
        for count in REGISTERED_COUNTS
        for workers in WORKERS
        for repetition in range(1, 7)
    }
    expected_modulo_warmups = set(MODULO_COUNTS)
    expected_modulo_scored = {
        (count, repetition)
        for count in MODULO_COUNTS
        for repetition in range(1, 7)
    }

    load_gate_counts = collections.Counter(
        "true"
        if row.get("load_gate_valid") is True
        else "false"
        if row.get("load_gate_valid") is False
        else "missing"
        for row in records
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    formal_out_manifest = root / "out" / "RUN-MANIFEST.json"
    diagnostic_manifest = root / "out" / "RUN-MANIFEST.operator-diagnostic.json"
    scorecard_manifest = repo / "experiments" / "SCORECARD" / "RUN-MANIFEST.json"

    return {
        "records_path": str(records_path.relative_to(repo)),
        "record_count": len(records),
        "expected_record_count": (
            len(expected_main_warmups)
            + len(expected_main_scored)
            + len(expected_modulo_warmups)
            + len(expected_modulo_scored)
        ),
        "by_kind": dict(sorted(by_kind.items())),
        "invalid_count": sum(not row.get("valid") for row in records),
        "registration_statuses": registration_statuses,
        "coverage": {
            "main_warmups": {
                "actual": len(main_warmups),
                "expected": len(expected_main_warmups),
                "missing": sorted(expected_main_warmups - main_warmups),
                "unexpected": sorted(main_warmups - expected_main_warmups),
            },
            "main_scored": {
                "actual": len(main_scored),
                "expected": len(expected_main_scored),
                "missing": sorted(expected_main_scored - main_scored),
                "unexpected": sorted(main_scored - expected_main_scored),
            },
            "modulo_warmups": {
                "actual": len(modulo_warmups),
                "expected": len(expected_modulo_warmups),
                "missing": sorted(expected_modulo_warmups - modulo_warmups),
                "unexpected": sorted(modulo_warmups - expected_modulo_warmups),
            },
            "modulo_scored": {
                "actual": len(modulo_scored),
                "expected": len(expected_modulo_scored),
                "missing": sorted(expected_modulo_scored - modulo_scored),
                "unexpected": sorted(modulo_scored - expected_modulo_scored),
            },
        },
        "load_gate_counts": dict(sorted(load_gate_counts.items())),
        "manifest_exists": {
            str(formal_out_manifest.relative_to(repo)): formal_out_manifest.exists(),
            str(diagnostic_manifest.relative_to(repo)): diagnostic_manifest.exists(),
            str(scorecard_manifest.relative_to(repo)): scorecard_manifest.exists(),
        },
        "summary": {
            "m12_d_pass": summary["m12_d"]["pass"],
            "m12_s_pass": summary["m12_s_byte_property"]["pass"],
            "m12_s_distinct_hashes_by_n": {
                key: value["distinct_hashes"]
                for key, value in summary["m12_s_byte_property"]["by_n"].items()
            },
            "peak_gib_max": summary["memory"]["peak_gib_max"],
            "peak_n299_over_peak_n33": summary["memory"]["peak_n299_over_peak_n33"],
            "six_gib_pass": summary["memory"]["six_gib_pass"],
            "modulo_spread": summary["modulo"]["spread"],
            "modulo_load_gate_verified": summary["modulo"]["load_gate_verified"],
            "modulo_scorecard_verdict": summary["modulo"]["scorecard_verdict"],
        },
        "audit": {
            "classification": audit["classification"],
            "verified_load_gated_invocation_count": audit["host_load_validity"][
                "verified_load_gated_invocation_count"
            ],
            "sampling_protocol_exactly_achieved": audit["memory"][
                "sampling_protocol_exactly_achieved"
            ],
            "worst_max_gap_ms": audit["memory"]["worst_max_gap_ms"],
            "maximum_missed_intervals": audit["memory"]["maximum_missed_intervals"],
            "elapsed_seconds": audit["provenance"]["elapsed_seconds"],
            "record_count": audit["provenance"]["record_count"],
        },
        "first_record": {
            "line": 1,
            "kind": records[0]["kind"],
            "limit": records[0]["limit"],
            "workers": records[0]["workers"],
            "registration_status": records[0]["registration_status"],
        },
        "last_record": {
            "line": len(records),
            "kind": records[-1]["kind"],
            "limit": records[-1]["limit"],
            "workers": records[-1]["workers"],
            "repetition": records[-1]["repetition"],
            "registration_status": records[-1]["registration_status"],
        },
    }


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    result = {
        "m8": audit_m8(repo),
        "m12": audit_m12(repo),
    }
    output = Path(__file__).resolve().parent / "followup-artifact-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
