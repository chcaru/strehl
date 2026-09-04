"""Structural and source-citation audit for the M135 report."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "research" / "M135-detail-instrument.md"


def normalize(text: str) -> str:
    lines = [re.sub(r"^\s*>\s?", "", line) for line in text.splitlines()]
    return " ".join(" ".join(lines).split())


def main() -> None:
    report = REPORT.read_text(encoding="utf-8")
    findings = []
    commission = json.loads(
        (Path(__file__).resolve().parent / "commission.json").read_text(
            encoding="utf-8"
        )
    )

    citation_pattern = re.compile(
        r"(?P<path>(?:docs|experiments)/[A-Za-z0-9_./-]+)"
        r":(?P<start>\d+)(?:-(?P<end>\d+))?"
    )
    for match in citation_pattern.finditer(report):
        relative = match.group("path")
        path = ROOT / Path(relative)
        start = int(match.group("start"))
        end = int(match.group("end") or start)
        if not path.exists():
            findings.append(
                {"kind": "missing_file", "citation": match.group(0)}
            )
            continue
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if start < 1 or end < start or end > line_count:
            findings.append(
                {
                    "kind": "line_range",
                    "citation": match.group(0),
                    "line_count": line_count,
                }
            )

    quote_checks = {
        "docs/proposals/2026-09-sota-scorecard.md": [
            "The burned grid and the development-only high-resolution slide may "
            "commission a new instrument but may never provide its scored value.",
            "Every primary metric is a hard gate. No win compensates for a loss.",
        ],
        "docs/research/M-CAND1.md": [
            "The observed increase is a failure of this finite estimator, not of DPI.",
        ],
        "docs/research/M-PHASE0-SLANTEDGE.md": [
            "Independent 33-step PCHIP linearisation is the one clean success",
        ],
        "docs/research/M-FRC-VIABILITY.md": [
            "Pre-noise transfer is different: it attenuates or strengthens the "
            "latent signal before fresh downstream noise, so repeat correlation "
            "should move.",
            "FRC is safe-by-null for common invertible postfilters, but it is "
            "responsive to pre-noise information transfer.",
        ],
        "docs/research/M115-deconv-headroom.md": [
            "nothing that uses one capture of one sensor can separate a static "
            "sensor pattern from a static scene.",
        ],
    }
    for relative, quotes in quote_checks.items():
        source = normalize((ROOT / relative).read_text(encoding="utf-8"))
        for quote in quotes:
            if normalize(quote) not in source:
                findings.append(
                    {"kind": "quote_mismatch", "path": relative, "quote": quote}
                )

    required_sections = [
        "## 2. What has already failed",
        "## 3. The precise impossibility result",
        "## 4. Candidate architecture A",
        "## 5. Candidate architecture B",
        "## 7. Frozen challenge battery and outcome",
        "## 8. Admission decision",
        "## 9. Could not determine",
    ]
    for heading in required_sections:
        if heading not in report:
            findings.append({"kind": "missing_heading", "heading": heading})

    if commission.get("status") != "PASS":
        findings.append({"kind": "commission_status", "value": commission.get("status")})
    failed_gates = [name for name, passed in commission.get("gates", {}).items() if not passed]
    if failed_gates:
        findings.append({"kind": "failed_gates", "gates": failed_gates})
    if len(commission.get("gates", {})) != 22:
        findings.append(
            {
                "kind": "gate_count",
                "value": len(commission.get("gates", {})),
                "expected": 22,
            }
        )

    output = {
        "status": "PASS" if not findings else "FAIL",
        "citation_count": len(list(citation_pattern.finditer(report))),
        "verified_tags": report.count("**VERIFIED."),
        "assumed_tags": report.count("**ASSUMED."),
        "findings": findings,
    }
    output_path = Path(__file__).resolve().parent / "audit.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
