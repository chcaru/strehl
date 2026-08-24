"""Audit every markdown table in a file for pipe hazards.

Two checks, because the repo linter can only do the first:
  (1) row pipe-count vs header pipe-count  - catches DISCARDED cells
  (2) any pipe that is NOT a structural cell separator - catches rows that are
      malformed but coincidentally match the header width, which check (1)
      passes silently. This is the case the brief warns about.

A structural separator is a pipe at the very start or end of a trimmed line, or
one surrounded by whitespace on both sides. Anything else - |H|, |A50|, |c-w| -
is content and must be escaped as \\|.
"""

from __future__ import annotations

import io
import re
import sys

path = sys.argv[1]
lines = io.open(path, encoding="utf-8").read().split("\n")

in_fence = False
tables = []          # (header_lineno, header_pipes)
cur = None
bad_count = []
bad_content = []

for i, ln in enumerate(lines, start=1):
    if ln.lstrip().startswith("```"):
        in_fence = not in_fence
        continue
    if in_fence:
        continue
    s = ln.strip()
    if not (s.startswith("|") and s.endswith("|") and s.count("|") >= 2):
        cur = None
        continue

    # count only UNESCAPED pipes
    n = len(re.findall(r"(?<!\\)\|", s))

    if cur is None:
        cur = {"hdr_line": i, "hdr_pipes": n}
        tables.append(cur)
    else:
        if n != cur["hdr_pipes"]:
            bad_count.append((i, n, cur["hdr_pipes"], cur["hdr_line"], s))

    # check (2): every unescaped pipe must be structural
    for m in re.finditer(r"(?<!\\)\|", s):
        p = m.start()
        if p == 0 or p == len(s) - 1:
            continue
        before = s[p - 1]
        after = s[p + 1]
        if before == " " and after == " ":
            continue
        bad_content.append((i, p, s[max(0, p - 34):p + 34]))

print(f"{path}: {len(tables)} table(s)")

print(f"\n[1] ROWS WHOSE PIPE COUNT DIFFERS FROM THEIR HEADER: {len(bad_count)}")
for i, n, h, hl, s in bad_count:
    print(f"  line {i}: {n} pipes vs header {h} (line {hl}) -> "
          f"{n - h} cell(s) DISCARDED")
    print(f"      {s[:120]}")

print(f"\n[2] NON-STRUCTURAL (CONTENT) PIPES - silent even when the count matches: "
      f"{len(bad_content)}")
seen = {}
for i, p, ctx in bad_content:
    seen.setdefault(i, []).append(ctx)
for i in sorted(seen):
    print(f"  line {i}: {len(seen[i])} content pipe(s)")
    for c in seen[i]:
        print(f"      ...{c}...")

print(f"\nRESULT: {'CLEAN' if not bad_count and not bad_content else 'DEFECTS PRESENT'}")
sys.exit(1 if (bad_count or bad_content) else 0)
