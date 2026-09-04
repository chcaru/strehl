from __future__ import annotations

import hashlib
import html
import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class ParagraphParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self._parts: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "p":
            self._depth += 1
        elif tag == "br" and self._depth:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag != "p" or not self._depth:
            return
        self._depth -= 1
        if self._depth == 0:
            text = " ".join(html.unescape("".join(self._parts)).split())
            if text:
                self.paragraphs.append(text)
            self._parts.clear()

    def handle_data(self, data: str) -> None:
        if self._depth:
            self._parts.append(data)


def paragraphs(path: Path) -> list[str]:
    parser = ParagraphParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.paragraphs


def slice_body(items: list[str], start: str, end: str) -> list[str]:
    first = next(i for i, value in enumerate(items) if value.startswith(start))
    last = next(i for i, value in enumerate(items[first:], first) if value.startswith(end))
    return items[first : last + 1]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def matching(items: list[str], pattern: re.Pattern[str]) -> list[str]:
    return [item for item in items if pattern.search(item)]


def main() -> None:
    sources = {
        "Zerene Stacker": {
            "file": ROOT / "zerene-license.html",
            "url": "https://zerenesystems.com/cms/stacker/docs/licenseterms",
            "start": "Subject to the following terms and conditions",
            "end": "11. GOVERNING LAW AND GENERAL PROVISIONS.",
        },
        "Helicon Focus": {
            "file": ROOT / "helicon-eula.html",
            "url": "https://www.heliconsoft.com/end-user-license-agreement-helicon-focus/",
            "start": "AUTHOR:",
            "end": "LIABILITY LIMITATION",
        },
    }
    patterns = {
        "benchmark/comparative-publication terms": re.compile(
            r"\bbenchmark(?:ing|s)?\b|\bcomparative\b|\bcomparison\b|"
            r"\bpublish(?:ed|ing)?\b|\bpublication\b|\bpublicly\b|"
            r"\bdisclos(?:e|ed|ing|ure)\b|\btest results?\b|"
            r"\bperformance results?\b",
            re.IGNORECASE,
        ),
        "competitive-development terms": re.compile(
            r"\bcompet(?:e|es|ed|ing|itor|itors|ition|itive)\b|"
            r"\bdevelop(?:ment|ing)\b.{0,80}\b(?:product|software)\b",
            re.IGNORECASE,
        ),
        "reverse-engineering/source-discovery terms": re.compile(
            r"\breverse engineer(?:ing)?\b|\bdecompil(?:e|ing)\b|"
            r"\bdisassembl(?:e|ing)\b|\breverse assembl(?:e|ing)\b|"
            r"\breverse compil(?:e|ing)\b|\bsource code\b|\balgorithms?\b|"
            r"\blook and feel\b",
            re.IGNORECASE,
        ),
    }

    output: list[str] = [
        "# EULA keyword audit",
        "# Generated from complete vendor-page EULA bodies retained beside this script.",
        "",
    ]
    for product, config in sources.items():
        path = config["file"]
        body = slice_body(paragraphs(path), config["start"], config["end"])
        normalized = "\n\n".join(body).encode("utf-8")
        output.extend(
            [
                f"## {product}",
                f"URL: {config['url']}",
                f"Snapshot: {path.name}",
                f"SnapshotSha256: {digest(path.read_bytes())}",
                f"ExtractedParagraphs: {len(body)}",
                f"ExtractedBodySha256: {digest(normalized)}",
            ]
        )
        for label, pattern in patterns.items():
            hits = matching(body, pattern)
            output.append(f"{label}: {len(hits)} match(es)")
            for hit in hits:
                output.append(f"  - {hit}")
        output.append("")

    (ROOT / "eula-keyword-audit.txt").write_text(
        "\n".join(output), encoding="utf-8", newline="\n"
    )


if __name__ == "__main__":
    main()
