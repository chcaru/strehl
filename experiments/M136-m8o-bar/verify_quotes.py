from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "research" / "M136-m8o-bar.md"
OUTPUT = Path(__file__).resolve().parent / "quote-check.json"
CITATION = re.compile(r"^\(`([^`]+):(\d+)(?:-(\d+))?`\)$")


def normalize(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:>\s*)+", "", line)
        lines.append(line)
    return re.sub(r"\s+", " ", "\n".join(lines)).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    report_lines = REPORT.read_text(encoding="utf-8").splitlines()
    checks = []
    index = 0
    while index < len(report_lines):
        if not report_lines[index].lstrip().startswith(">"):
            index += 1
            continue

        start = index
        quote_lines = []
        while index < len(report_lines) and report_lines[index].lstrip().startswith(">"):
            quote_lines.append(report_lines[index])
            index += 1
        if index >= len(report_lines):
            raise AssertionError(f"quote at report line {start + 1} has no citation")

        match = CITATION.fullmatch(report_lines[index].strip())
        if match is None:
            raise AssertionError(
                f"quote at report line {start + 1} is not followed by one "
                "single-source citation"
            )
        relative, first_text, last_text = match.groups()
        source = ROOT / Path(relative)
        first = int(first_text)
        last = int(last_text or first_text)
        source_lines = source.read_text(encoding="utf-8").splitlines()
        if not (1 <= first <= last <= len(source_lines)):
            raise AssertionError(
                f"{relative}:{first}-{last} is outside a {len(source_lines)}-line file"
            )

        quoted = normalize("\n".join(quote_lines))
        actual = normalize("\n".join(source_lines[first - 1 : last]))
        passed = quoted == actual
        checks.append(
            {
                "report_line": start + 1,
                "source": relative,
                "source_lines": [first, last],
                "source_sha256": sha256(source),
                "quoted_normalized": quoted,
                "source_normalized": actual,
                "passed": passed,
            }
        )
        if not passed:
            raise AssertionError(
                f"quote at report line {start + 1} does not match "
                f"{relative}:{first}-{last}"
            )
        index += 1

    if not checks:
        raise AssertionError("report contains no source quotations")
    payload = {
        "protocol": "M136 quote verification v1",
        "normalization": (
            "collapse all whitespace and strip leading Markdown blockquote markers"
        ),
        "report": str(REPORT),
        "report_sha256": sha256(REPORT),
        "quote_count": len(checks),
        "passed": True,
        "checks": checks,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"verified {len(checks)} quotations")


if __name__ == "__main__":
    main()
