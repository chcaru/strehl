"""Negative control for verify_s13.py: plant defects, require each to be CAUGHT.

verify_s13.py returned 50/50 GREEN on first clean run. That is exactly the
reading a verifier gives when it is checking nothing at all, so it means nothing
until the instrument has been shown capable of going RED.

Two rules this file obeys, both learned the hard way in this repository:

  * Every mutation is anchored on a UNIQUE full-line string and hard-errors if
    the anchor does not land exactly once. A bare `replace(x, y, 1)` silently
    edits the first coincidental match somewhere else in the document and the
    resulting GREEN is a statement about nothing.
  * The document is restored from a copy taken in $env:TEMP, never with
    `git checkout --`, which reverts to HEAD and has destroyed uncommitted work
    on this machine before.

D5 exists specifically to prove the `also=` disambiguation added for `109MSDCF`
targets the RANKED table and not the bit-identity table in 13.1, since that
subject appears in both.
D4 and D8 exist to prove check_flat sees a claim that wraps across a hard line
break -- the failure mode that made the first run of verify_s13.py report
ANCHOR errors on correct numbers.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "research" / "BUILD-OUTPUT.md"
VERIFY = Path(__file__).with_name("verify_s13.py")
BACKUP = Path(os.environ["TEMP"]) / "BUILD-OUTPUT.negctl_s13.bak"

DEFECTS = [
    # The anchor spans into the next row because 13.8 now quotes this row while
    # explaining the defect it exposed. The bare row therefore matches twice,
    # and the hard-error above caught that rather than silently editing the
    # illustration instead of the table.
    ("D1 partition: a regression is hidden",
     "| **REGRESSED** | **0** | **0** | **0** |\n| REFUSED |",
     "| **REGRESSED** | **0** | **1** | **0** |\n| REFUSED |"),
    ("D2 corpus median grain overstated",
     "**0.9417**. Every axis partitions all 26",
     "**0.9317**. Every axis partitions all 26"),
    ("D3 leaf-2-cpl grain improvement inflated",
     "| `leaf-2-cpl` | **0.4357** | **1.3420** | 0.9763 | better on ALL THREE |",
     "| `leaf-2-cpl` | **0.4157** | **1.3420** | 0.9763 | better on ALL THREE |"),
    ("D4 wrapped prose: quieter pct inflated",
     "`leaf-2-cpl` and `lead-1-cpl` are **56% and 51% quieter in fine grain while",
     "`leaf-2-cpl` and `lead-1-cpl` are **66% and 51% quieter in fine grain while"),
    ("D5 ranked-table 109MSDCF, NOT the 13.1 table",
     "| `109MSDCF` | 0.6414 | 1.0067 | 0.9907 | quieter |",
     "| `109MSDCF` | 0.6014 | 1.0067 | 0.9907 | quieter |"),
    ("D6 corpus median sharp overstated",
     "**0.9998**, sharp **1.0009**, grain",
     "**0.9998**, sharp **1.0209**, grain"),
    ("D7 lead-1-cpl sharpness inflated",
     "| `lead-1-cpl` | **0.4940** | **1.2335** | 0.9893 | better on ALL THREE |",
     "| `lead-1-cpl` | **0.4940** | **1.3335** | 0.9893 | better on ALL THREE |"),
    ("D8 wrapped prose: structure gain inflated",
     "carrying 34% and 23% MORE structure.** That is not a trade and it is not a",
     "carrying 44% and 23% MORE structure.** That is not a trade and it is not a"),
    ("D9 blotch IMPROVED count inflated",
     "| IMPROVED | 2 | 5 | **17** |",
     "| IMPROVED | 4 | 5 | **17** |"),
    # D10 is the transposition test. Both values are still present in the line,
    # so any presence-based check passes it trivially; only a positional cell
    # comparison can catch it. This is the exact shape of hole that D1 exposed.
    ("D10 UNCHANGED counts transposed between blotch and sharp",
     "| UNCHANGED | 24 | 21 | 9 |",
     "| UNCHANGED | 21 | 24 | 9 |"),
    ("D11 TOTAL row no longer covers the corpus",
     "| TOTAL | 26 | 26 | 26 |",
     "| TOTAL | 26 | 26 | 25 |"),
]


def run():
    p = subprocess.run([sys.executable, str(VERIFY)], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1]


shutil.copy2(DOC, BACKUP)
try:
    rc, last = run()
    if rc != 0:
        sys.exit(f"BASELINE IS NOT GREEN, cannot commission: {last}")
    print(f"  baseline           GREEN  {last}")

    caught = 0
    for name, old, new in DEFECTS:
        src = BACKUP.read_text(encoding="utf-8")
        if src.count(old) != 1:
            sys.exit(f"MUTATION TARGET NOT FOUND ({src.count(old)}x): {name}\n  {old!r}")
        DOC.write_text(src.replace(old, new), encoding="utf-8")
        rc, last = run()
        ok = rc != 0
        caught += ok
        print(f"  {'CAUGHT ' if ok else 'MISSED '} {name}\n      -> {last}")
finally:
    shutil.copy2(BACKUP, DOC)
    BACKUP.unlink()

rc, last = run()
print(f"\n  restored           {'GREEN' if rc == 0 else 'RED'}  {last}")
print(f"\n{caught}/{len(DEFECTS)} planted defects caught  "
      f"{'GREEN' if caught == len(DEFECTS) and rc == 0 else 'RED'}")
sys.exit(0 if caught == len(DEFECTS) and rc == 0 else 1)
