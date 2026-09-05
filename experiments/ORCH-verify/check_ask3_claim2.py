#!/usr/bin/env python3
"""Verify the Ask 3 correction: does blocker (d) ever appear alone?

The owner sheet now asserts, as the reason not to expect the $289 purchase to
move the scoreboard by itself:

    "No axis anywhere on the board has (d) as its only blocker."

That is a DERIVED claim and the sheet must not rest on my eyesight, so this
re-derives it mechanically. It also counts (b) independently, because the whole
argument turns on (b) being present wherever (d) is.

WHY THIS FILE HAS A FAIL-CLOSED GUARD.

The first version of this check reported CONFIRMED while examining the wrong
table. `2026-09-sota-scorecard.md` contains an axis-DEFINITIONS table at :806-817
whose rows have the same `| M1 | ... |` shape as the readiness table at :840-851,
but whose second cell is a title rather than a blocker-code set. Taking the first
match per axis found the definitions table, extracted zero codes from all twelve
rows, and concluded "(d) never appears alone" -- which is trivially true of an
empty set. It printed a pass having tested nothing.

So the guard below is the actual deliverable, not the comparison: a parse that
finds no blocker codes at all is a HARNESS FAILURE and exits non-zero. A count
that does not move is the same glyph whether nothing was wrong or nothing was
examined, and only an explicit floor distinguishes them.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SC = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"

lines = SC.read_text(encoding="utf-8", errors="replace").splitlines()

# Anchor on the readiness table's own heading rather than on row shape, because
# row shape does not distinguish it from the definitions table above it.
HEAD = re.compile(r"^###\s+3\.1\s+Measurement readiness")
start = next((i for i, l in enumerate(lines) if HEAD.match(l)), None)
if start is None:
    sys.exit("FATAL: readiness table heading '### 3.1 Measurement readiness' "
             "not found; the anchor moved and this check is blind.")

ROW = re.compile(r"^\|\s*(M\d+)\s*\|(.*?)\|")
rows = {}
for i in range(start, len(lines)):
    line = lines[i]
    if line.startswith("###") and i != start:
        break
    m = ROW.match(line)
    if m and m.group(1) not in rows:
        rows[m.group(1)] = (i + 1, m.group(2).strip())

print("readiness table starts at line %d" % (start + 1))
print("axis  line  blockers    class cell")
d_axes, b_axes, d_alone, coded = [], [], [], []
for axis in sorted(rows, key=lambda a: int(a[1:])):
    ln, cls = rows[axis]
    # (e) is a readiness class, not a blocker.
    blockers = sorted(set(re.findall(r"\((a|b|c|d)\)", cls)))
    print("%-5s %-5d %-11s %s" % (axis, ln, ",".join(blockers) or "-", cls[:58]))
    if blockers:
        coded.append(axis)
    if "d" in blockers:
        d_axes.append(axis)
        if blockers == ["d"]:
            d_alone.append(axis)
    if "b" in blockers:
        b_axes.append(axis)

print()
print("rows parsed:              %d" % len(rows))
print("rows carrying any code:   %d  %s" % (len(coded), coded))
print("axes carrying (d):        %d  %s" % (len(d_axes), d_axes))
print("axes carrying (b):        %d  %s" % (len(b_axes), b_axes))
print("axes where (d) is ALONE:  %d  %s" % (len(d_alone), d_alone))
d_without_b = [a for a in d_axes if a not in b_axes]
print("(d) axes lacking (b):     %d  %s" % (len(d_without_b), d_without_b))

# --- fail-closed guards: an empty parse must never read as a pass -------------
if len(rows) != 12:
    sys.exit("\nHARNESS FAILURE: parsed %d axis rows, expected 12." % len(rows))
if not coded:
    sys.exit("\nHARNESS FAILURE: zero blocker codes found across 12 rows. "
             "This is the wrong table, not a clean board.")
if len(d_axes) < 7:
    sys.exit("\nHARNESS FAILURE: only %d axes carry (d); the sheet claims eight "
             "are gated by it, so the parse is suspect." % len(d_axes))

ok = True
if d_alone:
    print("\nCLAIM FALSE: (d) is the sole blocker on %s" % d_alone)
    ok = False
if d_without_b:
    print("\nCLAIM FALSE: these carry (d) but not (b): %s" % d_without_b)
    ok = False
if ok:
    print("\nCONFIRMED on %d coded rows: (d) never appears alone, and every (d) "
          "axis also carries (b)." % len(coded))
sys.exit(0 if ok else 1)
