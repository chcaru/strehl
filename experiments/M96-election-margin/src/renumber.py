"""Renumber this milestone M94 -> M96 in SOURCE files only.

The orchestrator reassigned the milestone number after the measurements were
already taken. Source files are renamed; the raw run logs under out/ are left
byte-identical because they are the provenance of every number in the report --
rewriting them would make them no longer the output the instrument actually
printed. The report discloses that the logs carry the original label.

NOTE: this script has already been run. The milestone numbers below are built
from digits at runtime rather than written as literals, because the first
version of this file matched its own substitution table and rewrote it, leaving
an artifact that no longer described what it had done.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(".")
OLD = "M" + "9" + "4"
NEW = "M" + "9" + "6"

TARGETS = [
    f"crates/strehl-cli/examples/{NEW.lower()}-election-margin.rs",
    f"docs/research/{NEW}-election-margin.md",
    f"experiments/{NEW}-election-margin/PREREGISTRATION.md",
]
TARGETS += sorted(str(p).replace("\\", "/")
                  for p in (ROOT / f"experiments/{NEW}-election-margin/src").glob("*.py")
                  if p.name != "renumber.py")

SUBS = [
    (OLD.lower() + "_election_margin", NEW.lower() + "_election_margin"),
    (OLD + "-election-margin", NEW + "-election-margin"),
    (OLD.lower() + "-election-margin", NEW.lower() + "-election-margin"),
    ("target-" + OLD.lower(), "target-" + NEW.lower()),
    (OLD.lower(), NEW.lower()),
    (OLD, NEW),
]

RESIDUE = re.compile("[Mm]" + "9" + "4")

total = 0
for rel in TARGETS:
    p = ROOT / rel
    if not p.exists():
        print(f"MISSING {rel}")
        sys.exit(1)
    txt = p.read_text(encoding="utf-8")
    before = len(RESIDUE.findall(txt))
    for a, b in SUBS:
        txt = txt.replace(a, b)
    after = len(RESIDUE.findall(txt))
    if after:
        print(f"RESIDUE {rel}: {after}")
        sys.exit(1)
    p.write_text(txt, encoding="utf-8", newline="\n")
    total += before
    print(f"{rel}: {before} replaced")

print(f"total {total}")

rep = (ROOT / f"docs/research/{NEW}-election-margin.md").read_text(encoding="utf-8")
for needle in ("M93", "1205", "1196", "1177"):
    print(f"  report still cites {needle}: {rep.count(needle)}")
