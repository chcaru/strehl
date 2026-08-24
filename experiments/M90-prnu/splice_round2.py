"""Splice the round 2 section into the M90 report, before section 11.

Anchored on a unique full-line string and hard-errors if it does not land, per
the negative-control discipline: an edit that silently patches nothing is worse
than one that fails loudly.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs" / "research" / "M90-prnu-noise-model.md"
SECTION = pathlib.Path(__file__).resolve().parent / "_round2.md"

MARKER = "\n---\n\n## 11. Reproduction"


def main():
    text = REPORT.read_text(encoding="utf-8")
    norm = text.replace("\r\n", "\n")
    if norm.count(MARKER) != 1:
        raise SystemExit(
            f"ANCHOR NOT FOUND: '## 11. Reproduction' block occurs "
            f"{norm.count(MARKER)} times, expected 1")
    if "M90 round 2" in norm:
        raise SystemExit("round 2 section already present; refusing to double-append")

    body = SECTION.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n")
    out = norm.replace(MARKER, "\n---\n\n" + body + MARKER, 1)
    REPORT.write_text(out, encoding="utf-8", newline="\r\n")
    print(f"spliced {len(body.splitlines())} lines; report now "
          f"{len(out.splitlines())} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
