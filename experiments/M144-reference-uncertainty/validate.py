from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT = ROOT / "docs" / "research" / "M144-reference-uncertainty.md"
RESULTS = HERE / "results.json"
TREE_CHECK = HERE / "read-only-tree-verification.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collapse(text: str) -> str:
    return " ".join(text.replace("\n>", "\n").replace("> ", "").split())


def main() -> None:
    report = REPORT.read_text(encoding="utf-8")
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    tree_check = json.loads(TREE_CHECK.read_text(encoding="utf-8"))

    assert results["ciede2000_self_check"]["pass"]
    assert all(tree["unchanged"] for tree in tree_check["trees"])
    assert all(
        tree["baseline_inventory_sha256"] == tree["final_inventory_sha256"]
        for tree in tree_check["trees"]
    )

    for relative, expected in results["source_sha256"].items():
        path = ROOT / relative
        actual = sha256(path)
        assert actual == expected, f"stale source hash: {relative}"

    collapsed_report = collapse(report)
    for axis in [f"M{index}" for index in range(1, 11)]:
        quote = results["scorecard_success_quotes"][axis]["verbatim"]
        assert collapse(quote) in collapsed_report, f"missing verbatim {axis} rule"

    citation_pattern = re.compile(
        r"`((?:docs|experiments)/[^`:\s]+):([0-9][0-9,-]*)`"
    )
    citations = citation_pattern.findall(report)
    assert citations, "no line citations found"
    for relative, line_spec in citations:
        path = ROOT / relative
        assert path.is_file(), f"missing cited file: {relative}"
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        cited_numbers = [int(value) for value in re.findall(r"\d+", line_spec)]
        assert max(cited_numbers) <= line_count, (
            f"citation exceeds EOF: {relative}:{line_spec} > {line_count}"
        )

    required_phrases = [
        "do not spend $660 now",
        "2.6445 DeltaE00",
        "M2 through M10",
        "M1 has no numeric uncertainty threshold",
        "U95 > 0.25 DeltaE00",
        "0.064031–0.107703 native px RMS",
        "8.43% of a unit step",
        "122,237 times",
    ]
    for phrase in required_phrases:
        assert phrase in report, f"missing required conclusion: {phrase}"

    print(
        f"validated report, {len(citations)} line citations, "
        f"{len(results['source_sha256'])} source hashes"
    )


if __name__ == "__main__":
    main()
