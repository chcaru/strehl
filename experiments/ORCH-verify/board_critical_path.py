#!/usr/bin/env python3
"""Derive the SOTA board's critical path from the readiness table.

Answers a question I kept answering by eye and getting wrong: not "which blocker
gates the most axes" -- which flatters whichever blocker is largest -- but
"which axes are actually closest to scoreable, and what stands in front of each".

Shares the fail-closed discipline of check_ask3_claim2.py: anchor on the table
heading rather than on row shape, because the axis-DEFINITIONS table at :806-817
has an identical row shape and yields a silent empty parse.
"""

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SC = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
lines = SC.read_text(encoding="utf-8", errors="replace").splitlines()

start = next((i for i, l in enumerate(lines)
              if re.match(r"^###\s+3\.1\s+Measurement readiness", l)), None)
if start is None:
    sys.exit("FATAL: readiness heading not found; this check is blind.")

ROW = re.compile(r"^\|\s*(M\d+)\s*\|(.*?)\|")
rows = {}
for i in range(start, len(lines)):
    if lines[i].startswith("###") and i != start:
        break
    m = ROW.match(lines[i])
    if m and m.group(1) not in rows:
        rows[m.group(1)] = (i + 1, m.group(2).strip())

if len(rows) != 12:
    sys.exit("FATAL: parsed %d rows, expected 12." % len(rows))

NAMES = {"a": "detail instrument", "b": "cover=scale geometry",
         "c": "capture", "d": "licensed comparator"}

board, tally = [], Counter()
for axis in sorted(rows, key=lambda a: int(a[1:])):
    ln, cls = rows[axis]
    codes = sorted(set(re.findall(r"\((a|b|c|d)\)", cls)))
    # Named blockers that carry no letter code still block.
    extra = []
    if "INSTRUMENT VOID" in cls:
        extra.append("instrument-void")
    if "UNMEASURED_COMPARATOR_QUALIFICATION" in cls:
        extra.append("comparator-qual")
    if "DEFINITION BLOCKED" in cls:
        extra.append("definition-blocked")
    if "QUARANTINED" in cls:
        extra.append("timing-quarantine")
    for c in codes:
        tally[c] += 1
    for e in extra:
        tally[e] += 1
    board.append((axis, ln, codes, extra, cls))

print("=== blocker prevalence (how many axes each gates) ===")
for code, n in tally.most_common():
    print("  %-20s %2d   %s" % (code, n, NAMES.get(code, "")))

print("\n=== axes ordered by distance to scoreable ===")
board.sort(key=lambda r: (len(r[2]) + len(r[3]), r[0]))
for axis, ln, codes, extra, cls in board:
    blockers = codes + extra
    print("  %-4s line %-4d  %d blocker(s)  %s"
          % (axis, ln, len(blockers), ",".join(blockers) or "NONE"))

zero = [b[0] for b in board if not b[2] and not b[3]]
print("\naxes with NO listed blocker: %s" % (zero or "none"))
print("  -> these are the only axes whose verdict depends on work alone,")
print("     not on a purchase, a capture, or a missing instrument.")

# Which single blocker, if cleared, leaves the most axes with exactly one left?
print("\n=== marginal value: clearing one blocker ===")
for code in ["a", "b", "c", "d"]:
    after = [b[0] for b in board
             if code in b[2] and len(b[2]) + len(b[3]) == 1]
    nearly = [b[0] for b in board
              if code in b[2] and len(b[2]) + len(b[3]) == 2]
    print("  clear (%s): fully unblocks %-12s leaves 1 blocker on %s"
          % (code, str(after or "none") + ";", nearly or "none"))
