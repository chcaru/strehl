"""Check Markdown tables for rows whose unescaped-pipe count differs from the
header's.  A renderer silently DISCARDS the surplus cells, so the failure is
invisible in the source and invisible in the output -- it just quietly loses the
end of the row.

The trap is `|x|` written as absolute-value bars inside a table cell.  Escape
them as `\\|`.

    python -u experiments\\M67-focus-correctness\\src\\30-table-lint.py <file>..
"""
from __future__ import annotations

import re
import sys

PIPE = re.compile(r"(?<!\\)\|")


def check(path: str) -> int:
    bad = 0
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    fenced = False
    hdr_n = None
    hdr_line = 0
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("```"):
            fenced = not fenced
            hdr_n = None
            continue
        if fenced:
            continue
        if not (s.startswith("|") and s.endswith("|")):
            hdr_n = None
            continue
        n = len(PIPE.findall(s))
        if hdr_n is None:
            hdr_n, hdr_line = n, i
            continue
        # the |---|---| separator row
        if set(s.replace("|", "").replace(" ", "")) <= set("-:"):
            continue
        if n != hdr_n:
            bad += 1
            print(f"{path}:{i}: {n} unescaped pipes, header (line {hdr_line}) "
                  f"has {hdr_n}: {n - hdr_n} cell(s) past the header's column "
                  f"count are DISCARDED by the renderer")
            print(f"    {s[:160]}")
    return bad


def main() -> int:
    paths = sys.argv[1:]
    if not paths:
        print(__doc__)
        return 2
    bad = sum(check(p) for p in paths)
    print(f"{len(paths)} file(s), {bad} defective row(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
