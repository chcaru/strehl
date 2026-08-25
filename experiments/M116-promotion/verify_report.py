"""Check every delta in the report's bar table against scores.json.

Row-anchored, not presence-based: each row is located by its (arm, subject)
pair and its three numbers are compared to the values recomputed from
scores.json. A presence check would be satisfied by the same digits appearing
anywhere else in the document, which is how a verifier reads green on a report
it has not actually checked.
"""
import json
import re
import sys
from pathlib import Path

REPORT = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\M116-promotion.md")
SCORES = Path(r"C:\dev\strehl-out\M116\scores.json")

ARM = {
    "A1 photometric": "A1",
    "A2 softgate gaussian": "A2",
    "A3 softgate exponential": "A3",
    "A4 photometric + softgate": "A4",
}

scores = json.loads(SCORES.read_text())
lines = REPORT.read_text(encoding="utf-8").splitlines()

fails = checked = rows = 0
for line in lines:
    if not line.startswith("| A"):
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 5 or cells[0] not in ARM:
        continue
    arm, subj = ARM[cells[0]], cells[1]
    g = scores[subj]["aligned"]["arms"]
    ref = g["A0"]
    rows += 1
    for i, key in enumerate(("N", "D", "Q"), start=2):
        claimed = float(cells[i].strip("`"))
        actual = g[arm][key] - ref[key]
        checked += 1
        if abs(claimed - actual) > 5e-6:
            fails += 1
            print(f"  MISMATCH {arm}/{subj} d{key}: "
                  f"report {claimed:+.5f} vs data {actual:+.5f}")

print(f"checked {rows} rows, {checked} deltas; {fails} mismatched")
if rows != 12:
    print(f"FAIL - expected 12 arm rows, parsed {rows}")
    sys.exit(1)
print("PASS - every delta in the report matches scores.json" if fails == 0
      else "FAIL - report disagrees with the data")
sys.exit(1 if fails else 0)
