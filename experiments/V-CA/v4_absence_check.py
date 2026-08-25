"""V-CA v4 -- rule 43: an assertion of absence is a claim, so measure the absence.

Whitespace-collapse every file under docs/ and search for any sentence that
recommends turning the CA gate ON BY DEFAULT.  Wrapped Markdown breaks phrases
across lines, so plain grep under-reports; this joins first.
"""
from __future__ import annotations
import re
from pathlib import Path

DOCS = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs")
PATS = [
    r"default[- ]on", r"on by default", r"by default", r"enable(?:d)?\s+by\s+default",
    r"should\s+be\s+(?:turned\s+)?on", r"turn\s+(?:it\s+)?on", r"switch(?:ed)?\s+(?:it\s+)?on",
    r"ship\s+it\s+on", r"flag[- ]gated", r"stays?\s+off",
]
RX = re.compile("|".join(f"(?:{p})" for p in PATS), re.I)
CA = re.compile(r"STREHL_FIX_CA|lateral[- ]CA|chromatic aberration|\bCA\b", re.I)

hits = 0
for f in sorted(DOCS.rglob("*.md")):
    if f.name in ("SYNTHESIS.md",):
        continue
    txt = re.sub(r"\s+", " ", f.read_text(encoding="utf-8", errors="replace"))
    for m in re.finditer(r"[^.!?]*[.!?]", txt):
        s = m.group(0).strip()
        if RX.search(s) and CA.search(s):
            hits += 1
            print(f"[{f.relative_to(DOCS)}] {s[:300]}")
            print()
print(f"---- {hits} sentences mention the CA gate AND a default/on-off posture ----")
