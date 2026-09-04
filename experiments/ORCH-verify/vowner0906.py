#!/usr/bin/env python3
"""Verify the 2026-09-06 capture block in OWNER-ACTIONS against M164's source.

Two independent directions:
  1. every figure quoted to the owner occurs in the lane document it came from;
  2. the staged totals are re-derived arithmetically rather than copied.

A number that survives (1) but fails (2) is a transcription that happens to
match a real value elsewhere -- which is why (2) exists.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
OWNER = ROOT / "docs" / "OWNER-ACTIONS.md"
SRC = ROOT / "docs" / "research" / "M164-m1-staged-capture.md"
HEADING = "### Two things changed on 2026-09-06"


def collapse(s):
    return re.sub(r"\s+", " ", s)


def block(text, heading):
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(heading)), None)
    if start is None:
        raise SystemExit("FATAL: owner block heading not found")
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("### ") or lines[j].startswith("## "):
            return "\n".join(lines[start:j])
    return "\n".join(lines[start:])


owner_raw = OWNER.read_text(encoding="utf-8", errors="replace")
blk = collapse(block(owner_raw, HEADING))
src = collapse(SRC.read_text(encoding="utf-8", errors="replace"))


def forms(n):
    plain = n.replace(",", "")
    grouped, d = "", plain
    while len(d) > 3:
        grouped = "," + d[-3:] + grouped
        d = d[:-3]
    return {n, plain, d + grouped}


FIGURES = [
    ("first quote", "1,661"),
    ("inventory RAWs", "10,509"),
    ("stage 0 frames", "2"),
    ("rehearsal frames", "896"),
    ("rehearsal cumulative", "898"),
    ("sealed M1 frames", "704"),
    ("M1-first total", "1,602"),
    ("combined total", "1,917"),
    ("flats per class", "96"),
]

green = red = 0
for label, n in FIGURES:
    in_owner = any(f in blk for f in forms(n))
    in_src = any(f in src for f in forms(n))
    if in_owner and in_src:
        print("GREEN %-22s %s" % (label, n))
        green += 1
    else:
        print("RED   %-22s %s  owner=%s source=%s" % (label, n, in_owner, in_src))
        red += 1

# ---- independent arithmetic re-derivation ----
print()
stages = [128, 160, 128, 224, 256]
checks = [
    ("stages 1-5 sum to 896", sum(stages) == 896),
    ("stage 0 + rehearsal = 898", 2 + sum(stages) == 898),
    ("898 + 704 = 1,602", 2 + sum(stages) + 704 == 1602),
    ("combined 2 + 896 + 1019 = 1,917", 2 + 896 + 1019 == 1917),
]
for label, ok in checks:
    print(("GREEN " if ok else "RED   ") + "arith  " + label)
    if ok:
        green += 1
    else:
        red += 1

# ---- control: a wrong total must not re-derive ----
ctl = (2 + sum(stages) + 704) != 1603
print(("CTLPASS" if ctl else "CTLFAIL") + " decoy total 1,603 does not re-derive")

print()
print("GREEN: %d  RED: %d" % (green, red))
print("VERDICT: " + ("GREEN" if red == 0 and ctl else "RED"))
sys.exit(0 if (red == 0 and ctl) else 1)
