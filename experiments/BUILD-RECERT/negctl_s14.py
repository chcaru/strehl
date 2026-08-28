"""Negative control for verify_s14.py: plant defects, require each to be CAUGHT.

verify_s14.py's first run found two real errors in section 14 -- the per-level
counts of `x white` entries below 1.0 were written as 9 and 2 where the JSON says
10 and 1. THEY CANCEL: 0 + 9 + 4 + 2 and 0 + 10 + 4 + 1 both total 15, and the
document's stated total of "15 of 100" was correct. A check on the total alone
would have passed both errors. That is the argument for verifying every cell of
a table rather than its summary, and D3 below reinstates exactly that defect.

D6 is the transposition test: it swaps two values between columns, leaving both
present in the line. Every presence-based check passes it trivially and only a
positional cell comparison can catch it. verify_s13.py's commissioning found a
check that could not fail for precisely this reason.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "research" / "BUILD-OUTPUT.md"
VERIFY = Path(__file__).with_name("verify_s14.py")
BACKUP = Path(os.environ["TEMP"]) / "BUILD-OUTPUT.negctl_s14.bak"

DEFECTS = [
    ("D1 the load-bearing L0 minimum pushed below 1.0",
     "| **0** | 25 | **1.0888** | **1.1751** | **1.5504** | **0 of 25** |",
     "| **0** | 25 | **0.9888** | **1.1751** | **1.5504** | **0 of 25** |"),
    ("D2 an L0 entry below 1.0 concealed",
     "| **0** | 25 | **1.0888** | **1.1751** | **1.5504** | **0 of 25** |",
     "| **0** | 25 | **1.0888** | **1.1751** | **1.5504** | **2 of 25** |"),
    ("D3 the ORIGINAL cancelling error reinstated (9 and 2, total still 15)",
     "| 1 | 25 | 0.9275 | 1.0139 | 1.2660 | 10 of 25 |",
     "| 1 | 25 | 0.9275 | 1.0139 | 1.2660 | 9 of 25 |"),
    ("D4 the gate made to look active above level 0",
     "| 1-6 | 0.0% | 0.0% | 3.1% | 11 of 150 |",
     "| 1-6 | 0.0% | 0.4% | 3.1% | 11 of 150 |"),
    ("D5 structure cost understated",
     "| `leaf-2-cpl` | struct 5-13 px | **0.7561** | **1.3635** |",
     "| `leaf-2-cpl` | struct 5-13 px | **0.9561** | **1.3635** |"),
    ("D6 struct and floor TRANSPOSED (both values still on the line)",
     "| `leaf-2-cpl` | grain <=3 px | **0.8626** | **2.2648** |",
     "| `leaf-2-cpl` | grain <=3 px | **2.2648** | **0.8626** |"),
    ("D7 band noise gain ratio inflated",
     "| 3 | 0.0024 | 0.00270 |",
     "| 3 | 0.0024 | 0.00470 |"),
    ("D8 a correlation's sign flipped",
     "| grain ratio FALLS as `x white` rises | **-0.4623** | CONFIRMED |",
     "| grain ratio FALLS as `x white` rises | **+0.4623** | CONFIRMED |"),
    ("D9 the reciprocity claim inflated",
     "gives sharp **0.7451** and grain **2.2953** -- reciprocals",
     "gives sharp **0.6451** and grain **2.2953** -- reciprocals"),
    ("D10 the A/B gating fraction inflated",
     "| `leaf-2-cpl` | 1.5504 | **54.4%** | 7.1% | **7.7x more gating** |",
     "| `leaf-2-cpl` | 1.5504 | **64.4%** | 7.1% | **7.7x more gating** |"),
    ("D11 the floor-rise percentage understated",
     "raises the noise floor by 36%",
     "raises the noise floor by 16%"),
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
