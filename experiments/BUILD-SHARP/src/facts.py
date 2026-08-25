"""Extract specific fact rows from the SYNTHESIS corpus by number.

The corpus is a very large single Markdown table and must not be read linearly.
Rows are `| <n> | <text> | ... |`. Prose inside a cell is wrapped by the editor,
so a phrase can span a line break and a plain grep for it will miss; this reads
whole logical rows instead and collapses whitespace before printing.
"""

from __future__ import annotations

import argparse
import re
import textwrap
from pathlib import Path

SYN = Path("docs/research/SYNTHESIS.md")


def rows(path: Path):
    """Yield (number, raw_row_text) for every numbered fact row."""
    text = path.read_text(encoding="utf-8", errors="replace")
    out = {}
    cur_n, buf = None, []
    for line in text.splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|", line)
        if m:
            if cur_n is not None:
                out[cur_n] = "\n".join(buf)
            cur_n, buf = int(m.group(1)), [line]
        elif cur_n is not None:
            if line.startswith("|"):
                buf.append(line)
            else:
                out[cur_n] = "\n".join(buf)
                cur_n, buf = None, []
    if cur_n is not None:
        out[cur_n] = "\n".join(buf)
    return out


def expand(spec: str):
    want = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            want.extend(range(int(a), int(b) + 1))
        elif part:
            want.append(int(part))
    return want


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("facts", help="e.g. 1359,1372,1603-1607")
    p.add_argument("--file", default=str(SYN))
    p.add_argument("--width", type=int, default=104)
    p.add_argument("--chars", type=int, default=0, help="truncate each fact")
    a = p.parse_args()

    table = rows(Path(a.file))
    for n in expand(a.facts):
        if n not in table:
            print(f"\n--- {n}: NOT FOUND ---")
            continue
        body = re.sub(r"\s+", " ", table[n]).strip()
        if a.chars:
            body = body[: a.chars]
        print(f"\n--- {n} " + "-" * 60)
        print(textwrap.fill(body, a.width))


if __name__ == "__main__":
    main()
