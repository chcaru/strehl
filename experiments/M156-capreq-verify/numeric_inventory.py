#!/usr/bin/env python3
import re
from pathlib import Path
p = Path("docs/capture-requests/2026-09-319-frame-session.md")
pattern = re.compile(r"\b(frame|frames|shot|shots|exposure|exposures|minute|minutes|interval|intervals|release|releases|total|subtotal|count|counts)\b", re.I)
for number, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
    if pattern.search(line) and re.search(r"\d", line):
        safe = line.encode("ascii", "replace").decode("ascii")
        print(f"{number:4}: {safe}")