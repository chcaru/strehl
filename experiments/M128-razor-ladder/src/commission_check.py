"""M128 / commission_check — prove src\\check_prereg.py can fail.

A verifier that has only ever printed GREEN is indistinguishable from one that
examines nothing. This plants five defects of different kinds into
PREREGISTRATION.md, one at a time, and requires the checker to go RED on each.

Every mutation is anchored on a unique full-line string and HARD ERRORS if the
anchor does not land exactly once, because a mutation that silently fails to
apply produces a green that means nothing.

The document is copied to %TEMP% first and restored from that copy, never from
git, so uncommitted work cannot be destroyed.

    python src\\commission_check.py

Exit code 0 = all defects caught, 1 = at least one missed.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
DOC = HERE.parent / "PREREGISTRATION.md"
CHECK = HERE / "check_prereg.py"

DEFECTS = [
    ("D1 table-1 cell, last digit of N_eff",
     "| H1 — fact 1149 | 87.00 | 20.899 | 3.7319 | 0.9956 |",
     "| H1 — fact 1149 | 87.00 | 20.898 | 3.7319 | 0.9956 |"),
    ("D2 rise-in-um cell, 0.01 um",
     "| H1 | 13.650 | 18.067 | 23.898 |",
     "| H1 | 13.640 | 18.067 | 23.898 |"),
    ("D3 rise-in-px cell, last digit",
     "| H3 | 1.0123 | 1.2563 | 1.5953 |",
     "| H3 | 1.0123 | 1.2563 | 1.5954 |"),
    ("D4 deleted prose claim (M5 bracket re-expressed)",
     "gives `p` ∈ [1.318, 1.926] — which reproduces fact 1152's",
     "gives a range of values which reproduces fact 1152's"),
    ("D5 separation percentage, 0.01",
     "adjacent gap grows from 11.71% of the largest rise at f/5.6 to 15.82% at",
     "adjacent gap grows from 11.72% of the largest rise at f/5.6 to 15.82% at"),
]


def run_check():
    r = subprocess.run([sys.executable, str(CHECK)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    if not DOC.exists():
        print(f"RED  {DOC} not found")
        return 1

    tmpdir = Path(tempfile.gettempdir())
    backup = tmpdir / "M128_PREREGISTRATION.md.bak"
    shutil.copy2(DOC, backup)
    print(f"backup: {backup}")
    original = DOC.read_text(encoding="utf-8")

    rc, out = run_check()
    print(f"\nbaseline (unmutated): rc={rc}")
    if rc != 0:
        print("RED  baseline is not green; fix the document before "
              "commissioning the checker")
        print(out)
        DOC.write_text(original, encoding="utf-8", newline="")
        return 1
    nclaims = [l for l in out.splitlines() if "claims re-derived" in l]
    print(f"  {nclaims[0].strip() if nclaims else '(no claim count printed)'}")

    results = []
    try:
        for name, old, new in DEFECTS:
            n = original.count(old)
            if n != 1:
                print(f"\nRED  MUTATION TARGET NOT FOUND: {name}")
                print(f"     anchor occurs {n} times, want exactly 1")
                print(f"     anchor: {old!r}")
                results.append((name, "ANCHOR-MISS"))
                continue
            DOC.write_text(original.replace(old, new, 1), encoding="utf-8",
                           newline="")
            rc, out = run_check()
            verdict = "CAUGHT" if rc != 0 else "MISSED"
            detail = [l.strip() for l in out.splitlines()
                      if l.strip().startswith("- ")]
            print(f"\n{name}\n  rc={rc}  {verdict}")
            for d in detail[:3]:
                print(f"    {d}")
            results.append((name, verdict))
    finally:
        DOC.write_text(original, encoding="utf-8", newline="")
        after = DOC.read_text(encoding="utf-8")
        print(f"\nrestored: identical to pre-run = {after == original}")

    rc, out = run_check()
    print(f"post-restore baseline: rc={rc}")

    caught = sum(1 for _, v in results if v == "CAUGHT")
    print(f"\n{caught}/{len(DEFECTS)} defects caught")
    if caught != len(DEFECTS) or rc != 0:
        print("RED  the checker is not fully commissioned")
        for n, v in results:
            if v != "CAUGHT":
                print(f"  - {n}: {v}")
        return 1
    print("GREEN  every planted defect turned the checker red, and it is "
          "green again on the restored document")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
