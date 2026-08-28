"""Negative control for verify_s12.py. A verifier that has never gone RED is a
claim about nothing.

Each defect is anchored on a UNIQUE FULL-LINE string and the script HARD-ERRORS
if the anchor does not land exactly once. A bare `replace(x, y, 1)` can silently
mutate the wrong occurrence -- this project has already recorded a control that
read GREEN because the literal it keyed on occurred earlier somewhere harmless.

The document is restored from a copy taken in $env:TEMP, never with
`git checkout --`, which reverts to HEAD and has destroyed uncommitted work on
this machine before.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "research" / "BUILD-OUTPUT.md"
VERIFY = Path(__file__).resolve().parent / "verify_s12.py"
BACKUP = Path(os.environ["TEMP"]) / "BUILD-OUTPUT.s12.negctl.bak"

DEFECTS = [
    ("D1 corpus sharpness median",
     "| sharpness, struct 5-13 px (0.077-0.20 cyc/px) | 0.8037 | 0.8037 |",
     "| sharpness, struct 5-13 px (0.077-0.20 cyc/px) | 0.8038 | 0.8038 |"),
    ("D2 exchange rate",
     "| sharpness spent per unit of blotch bought | 0.62 | **1.07** |",
     "| sharpness spent per unit of blotch bought | 0.62 | **0.62** |"),
    ("D3 partition (a FLAT WINS that never happened)",
     "**Partition: 25 TRADE, 1 FLAT LOSES, 0 FLAT WINS, 0 refused.**",
     "**Partition: 24 TRADE, 1 FLAT LOSES, 1 FLAT WINS, 0 refused.**"),
    ("D4 worst-trade subject row",
     "| `coffee-bubbles` | 0.9288 | 0.8587 | 7.1 | 14.1 | **1.99** |",
     "| `coffee-bubbles` | 0.8288 | 0.8587 | 7.1 | 14.1 | **1.99** |"),
    ("D5 registration basis partition",
     "`SSD-WELL=18, MEDIAN-ONLY=8`", "`SSD-WELL=20, MEDIAN-ONLY=8`"),
    # --- added with the exchange-rate table and the retraction ----------------
    ("D6 corrected-basis partition",
     "corrected 0.9288 (TRADE) -- giving **26 TRADE, 0 FLAT LOSES, 0 FLAT WINS**. The",
     "corrected 0.9288 (TRADE) -- giving **26 TRADE, 1 FLAT LOSES, 0 FLAT WINS**. The"),
    ("D7 worst corpus exchange rate",
     "2. **The two worst exchange rates in the whole corpus are `109MSDCF` (6.71) and",
     "2. **The two worst exchange rates in the whole corpus are `109MSDCF` (6.17) and"),
    ("D8 the retracted rank (reinstate the false claim)",
     "trade in the entire corpus\". Ranked by exchange rate it is **7th of 26**, and six",
     "trade in the entire corpus\". Ranked by exchange rate it is **1st of 26**, and six"),
    ("D9 exchange-rate column on an already-soft subject",
     "| `109MSDCF` | 0.9683 | 0.7829 | 3.2 | 21.7 | **6.71** worst |",
     "| `109MSDCF` | 0.9683 | 0.7829 | 3.2 | 12.7 | **6.71** worst |"),
]


def run():
    p = subprocess.run([sys.executable, str(VERIFY)], capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1]


def main():
    shutil.copy2(DOC, BACKUP)
    original = DOC.read_text(encoding="utf-8")
    try:
        rc, last = run()
        print(f"  BASELINE (unmutated)                       rc={rc}  {last}")
        if rc != 0:
            print("  baseline is not GREEN -- fix that before trusting any control")
            return 1

        caught = 0
        for name, old, new in DEFECTS:
            n = original.count(old)
            if n != 1:
                raise SystemExit(
                    f"MUTATION TARGET NOT FOUND: {name!r} anchor occurs {n}x, need "
                    f"exactly 1. The control is invalid, not passing.")
            DOC.write_text(original.replace(old, new, 1), encoding="utf-8")
            rc, last = run()
            ok = rc != 0
            caught += ok
            print(f"  {name:<42} rc={rc}  {'CAUGHT' if ok else 'MISSED'}  {last}")
            DOC.write_text(original, encoding="utf-8")

        print(f"\n{caught}/{len(DEFECTS)} planted defects caught  "
              f"{'GREEN' if caught == len(DEFECTS) else 'RED'}")
        return 0 if caught == len(DEFECTS) else 1
    finally:
        DOC.write_text(original, encoding="utf-8")
        assert DOC.read_text(encoding="utf-8") == original, "restore failed"
        rc, last = run()
        print(f"  RESTORED                                   rc={rc}  {last}")


if __name__ == "__main__":
    sys.exit(main())
