#!/usr/bin/env python3
"""Commission the eight STATUS 2.9.77 pins added to v2954.py.

Each arm plants the exact defect one pin claims to catch and requires v2954 to
go RED; two inert arms plant harmless edits and must stay GREEN. Every mutation
is anchored on a unique full string and hard-errors on a miss, so a silent
no-match can never be counted as a caught defect.

The arms are chosen to be the specific ways this record would *improve itself*
if it drifted -- a scoreboard that grows, a kill that softens, an attributed
count that loses its attribution, a flagged assumption that stops being flagged,
and a self-correction that quietly disappears. Those are the edits nobody would
notice, which is exactly why they are the ones pinned.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "docs" / "STATUS.md"
V2954 = Path(__file__).resolve().parent / "v2954.py"

ARMS = [
    ("A scoreboard quietly grows",
     "scoreboard. **The scoreboard is unchanged at `0 of 12`.**",
     "scoreboard. **The scoreboard now stands at `1 of 12`.**",
     True),
    ("B the D8 kill is softened",
     'reads **"Verdict: KILL — STOP/REMOVE RUST;\nretain the split instrument offline."**',
     'reads **"Verdict: QUALIFIED — the split instrument is retained."**',
     True),
    ("C the M8 coupling is dropped",
     "**The structural consequence: M8 cannot be honestly passed before `(a)` closes.**",
     "**The structural consequence: M8 remains independently passable.**",
     True),
    ("D N6's assumption stops being flagged",
     "**This rests on an assumption I have flagged\nrather than hidden**",
     "**This is established**",
     True),
    ("E the 178 loses its attribution",
     "`178` is an **M152**-eligible count,\nnot an M166-eligible one",
     "`178` is the eligible count",
     True),
    ("F the self-correction disappears",
     "and no quantity of them clears `(a)`",
     "and they substantially advance `(a)`",
     True),
    ("G the M4 shortfall stops adding up",
     "**`29` medication + `83` foam = `112` quota sites**",
     "**`29` medication + `83` foam = `150` quota sites**",
     True),
    ("H INERT cosmetic edit inside 2.9.77",
     "Three findings tonight change the shape of the program rather than its\nscoreboard.",
     "Three findings tonight change the shape of the program, rather than its\nscoreboard.",
     False),
    ("I INERT cosmetic edit elsewhere in 2.9.77",
     "**Also landed.** M165 closed the **fork arm of blocker `(d)` at zero cost**",
     "**Also landed this session.** M165 closed the **fork arm of blocker `(d)` at zero cost**",
     False),
]


def run():
    return subprocess.run([sys.executable, str(V2954)],
                          capture_output=True, text=True, cwd=str(ROOT)).returncode


def main():
    original = STATUS.read_text(encoding="utf-8")
    if run() != 0:
        print("FATAL: baseline v2954 is not GREEN; commissioning is meaningless.")
        return 2
    print("baseline            : GREEN")
    print()

    caught = missed = inert_green = inert_red = 0
    try:
        for label, find, repl, expect_red in ARMS:
            n = original.count(find)
            if n != 1:
                raise SystemExit(
                    "MUTATION TARGET NOT FOUND: %r matched %d times (need exactly 1). "
                    "Refusing to report a result for a defect that was never planted."
                    % (label, n))
            STATUS.write_text(original.replace(find, repl, 1), encoding="utf-8")
            red = (run() != 0)
            if expect_red:
                if red:
                    caught += 1
                    v = "CAUGHT"
                else:
                    missed += 1
                    v = "MISSED  <-- the pin is a no-op"
            else:
                if red:
                    inert_red += 1
                    v = "INERT-RED  <-- fires on a harmless edit"
                else:
                    inert_green += 1
                    v = "INERT-GREEN"
            print("%-40s %s" % (label, v))
    finally:
        STATUS.write_text(original, encoding="utf-8")

    restored = "GREEN" if run() == 0 else "RED"
    print()
    print("restored baseline   : %s" % restored)
    print("caught              : %d" % caught)
    print("missed              : %d" % missed)
    print("inert green         : %d" % inert_green)
    print("inert red           : %d" % inert_red)
    print("arms accounted      : %d of %d"
          % (caught + missed + inert_green + inert_red, len(ARMS)))
    ok = (missed == 0 and inert_red == 0 and restored == "GREEN"
          and caught == sum(1 for a in ARMS if a[3]))
    print()
    print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
