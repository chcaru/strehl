"""O13 -- an INDEPENDENT check for renderer-truncated table cells.

ORCH reported M95-election-quality.md:241 as red on S1/S6. It is not, and has
not been since 9d70a38. But taking the all-clear from `corpus_lint` alone would
be trusting the one instrument whose miss would look exactly like this: a row
that renders short is invisible to any reader of the rendered page, and a check
that shares the lint's parsing shares its blind spots.

So this reimplements the test from the renderer's rule instead of the lint's:
GitHub splits a table row on every `|` not preceded by a backslash, BEFORE it
parses code spans. Backticks do not protect the pipe. A row with more unescaped
pipes than its header has its excess cells DISCARDED silently.

Deliberately does not import or consult scripts/corpus_lint.py.

BAR, stated before the run: zero rows in the M95 docs may have an unescaped-pipe
count differing from their header's. Any mismatch is a truncated or short row.

Self-check: the run is only meaningful if this file can see the defect at all,
so it plants a known-bad row and a known-good row and requires the exact verdict
on each before reporting on the real files.
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

DOCS = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research"
TARGETS = ["M95-election-quality.md", "M95-tile-provenance.md"]


def bars(line: str) -> int:
    """Unescaped pipes, counted the way the renderer splits."""
    return sum(1 for i, c in enumerate(line) if c == "|" and (i == 0 or line[i - 1] != "\\"))


def scan(text: str):
    """Yield (lineno, header_bars, row_bars) for every row disagreeing with its header."""
    bad = []
    lines = text.splitlines()
    hdr = None
    for n, ln in enumerate(lines, 1):
        s = ln.strip()
        if not s.startswith("|"):
            hdr = None
            continue
        if re.fullmatch(r"\|(\s*:?-{3,}:?\s*\|)+", s):
            hdr = bars(lines[n - 2].strip()) if n >= 2 else None
            if hdr is not None and bars(s) != hdr:
                bad.append((n, hdr, bars(s), "delimiter width"))
            continue
        if hdr is None:
            continue
        b = bars(s)
        if b != hdr:
            bad.append((n, hdr, b, s[:70]))
    return bad


def selfcheck() -> None:
    good = "| a | `\\|D\\| < 1 %` | b |\n"
    bad = "| a | `|D| < 1 %` | b |\n"
    head = "| x | y | z |\n| --- | --- | --- |\n"
    g = scan(head + good)
    b = scan(head + bad)
    assert not g, f"SELF-CHECK FAILED: escaped row flagged: {g}"
    assert len(b) == 1 and b[0][2] == 6, f"SELF-CHECK FAILED: unescaped row not caught: {b}"
    print(f"self-check: escaped row clean; unescaped row caught "
          f"({b[0][2]} bars vs header {b[0][1]}) -- instrument responds\n")


def main() -> int:
    selfcheck()
    total = 0
    seen = 0
    for name in TARGETS:
        p = DOCS / name
        if not p.exists():
            raise SystemExit(f"COVERAGE FAILURE: {p} missing")
        seen += 1
        rows = scan(p.read_text(encoding="utf-8"))
        total += len(rows)
        print(f"{name}: {len(rows)} mismatched row(s)")
        for n, h, b, s in rows:
            print(f"  L{n}: header {h} bars, row {b} bars  {s}")
    if seen != len(TARGETS):
        raise SystemExit("COVERAGE FAILURE: not all targets scanned")
    print(f"\nfiles scanned {seen}, mismatched rows {total}")
    print("VERDICT:", "CLEAN" if total == 0 else "TRUNCATION PRESENT")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
