"""14 -- renumber section 4 subsections after inserting the provenance sections.

Scoped deliberately: this touches SECTION HEADINGS and section cross-references
only. It does NOT touch any "fact N" string. That is the whole lesson of
error 12, where a renumbering script shifted five citations that belonged to
another report.
"""

from __future__ import annotations

import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.normpath(os.path.join(
    HERE, "..", "..", "..", "docs", "research", "M61-ptc-high-iso-measured.md"))

REPS = [
    ('### 4.9 "The polarizer explains it"', '### 4.8 "The polarizer explains it"'),
    ('### 4.10 "Your answer depends', '### 4.9 "Your answer depends'),
    ("### 4.11 What I did", "### 4.10 What I did"),
    ("and §4.7 now tests it against the", "and §4.8 now tests it against the"),
    ("and §4.8 shows that refutation", "and §4.9 shows that refutation"),
]


def main() -> int:
    t = io.open(DOC, encoding="utf-8").read()
    for old, new in REPS:
        n = t.count(old)
        if n != 1:
            raise SystemExit(f"ABORT: {n} matches for {old!r}, expected 1")
        t = t.replace(old, new)
    io.open(DOC, "w", encoding="utf-8", newline="\n").write(t)

    subs = re.findall(r"^### (4\.\d+)", t, re.M)
    print("subsections:", subs)
    print("refs to 4.x:", sorted(set(re.findall(r"§(4\.\d+)", t))))
    print("facts:", re.findall(r"\*\*Fact (\d+) ", t))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
