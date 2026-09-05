#!/usr/bin/env python3
"""Commission the six M165 fork-arm pins added to v2954.py.

A pin that has never fired is indistinguishable from a no-op. Each arm below
plants the exact defect one pin claims to catch and requires v2954 to go RED.
One inert arm plants a harmless edit and requires v2954 to stay GREEN, so the
suite is shown to be discriminating rather than merely alarmed.

Two of the pins assert cross-document agreement. Those are mutated on ONE side
only, which is the failure they exist for: an edit that drifts the owner copy
away from the lane copy while the lane copy still reads correctly. A pin that
merely tested presence would pass on the untouched side.

Every mutation is anchored on a full unique string and hard-errors if it does
not match exactly once. A silent no-match would print GREEN and be recorded as
a caught defect that was never planted.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OWNER = ROOT / "docs" / "OWNER-ACTIONS.md"
V2954 = Path(__file__).resolve().parent / "v2954.py"

REV = "4bc7f95e448cf20ee2bdd758403ec43e2612a1c6"
SHA = "691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac"

# (label, exact-unique-find, replace, expect_red)
ARMS = [
    ("A revision drifts on owner side only",
     "> `%s`, rebuilt it, and froze the" % REV,
     "> `%s`, rebuilt it, and froze the" % (REV[:-1] + "0"),
     True),
    ("B executable sha drifts on owner side only",
     "> `%s`" % SHA,
     "> `%s`" % (SHA[:-1] + "0"),
     True),
    ("C ordering claim deleted",
     "> **before** any rendering — the ordering matters, because a hash frozen after",
     "> after rendering — the ordering does not matter, because a hash frozen after",
     True),
    ("D licence quietly discounted",
     "> **What this changes for you: nothing you have to do, and one thing you no\n"
     "> longer have to wait for.** The `$189` still buys the two Zerene arms and\n"
     "> nothing else; the fork is no longer a reason the comparator work would stall\n"
     "> after a purchase.",
     "> **What this changes for you: the purchase is now smaller.** The fork arm is\n"
     "> closed, so less of the comparator remains to be bought.",
     True),
    ("E stated limit dropped on the way to the owner",
     "> after a purchase. Cross-host reproducibility is untested and M165 said so\n"
     "> rather than claiming it.",
     "> after a purchase. The build is reproducible.",
     True),
    ("F INERT cosmetic edit elsewhere in the same document",
     "> **Progress on the `$189` row, so you can see what the money would and would\n"
     "> not still be buying.**",
     "> **Progress on the `$189` row, so you can see exactly what the money would and\n"
     "> would not still be buying.**",
     False),
    ("G one addend drifts inside a published sum",
     "> sittings** (`2 + 1,092 + 1,215 + 686 + 64 + 657`).",
     "> sittings** (`2 + 1,192 + 1,215 + 686 + 64 + 657`).",
     True),
    ("H the not-sufficient boundary is softened",
     "> exists, and they are **not sufficient**, and no quantity of them clears `(a)`.",
     "> exists, and they put the full scorecard within reach once shot.",
     True),
    ("I the three-acquisition finding is dropped",
     "> are three distinct acquisitions with conflicting optical states",
     "> are the same acquisition reused across lanes",
     True),
    ("J INERT rewording inside the capture section",
     "> **The order, ranked by what unblocks a scoreable axis soonest:**",
     "> **The order, ranked by what unblocks a scoreable axis the soonest:**",
     False),
]


def run_v2954():
    p = subprocess.run([sys.executable, str(V2954)],
                       capture_output=True, text=True, cwd=str(ROOT))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    original = OWNER.read_text(encoding="utf-8")

    rc, out = run_v2954()
    if rc != 0:
        print("FATAL: baseline is not GREEN; commissioning is meaningless.")
        print(out[-1500:])
        return 2
    print("baseline            : GREEN (rc=0)")
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
            OWNER.write_text(original.replace(find, repl, 1), encoding="utf-8")
            rc, out = run_v2954()
            went_red = (rc != 0)
            if expect_red:
                if went_red:
                    caught += 1
                    verdict = "CAUGHT"
                else:
                    missed += 1
                    verdict = "MISSED  <-- the pin is a no-op"
            else:
                if went_red:
                    inert_red += 1
                    verdict = "INERT-RED  <-- over-sensitive, fires on a harmless edit"
                else:
                    inert_green += 1
                    verdict = "INERT-GREEN"
            print("%-52s %s" % (label, verdict))
            if expect_red and not went_red:
                print("   (rc=0 with the defect present)")
    finally:
        OWNER.write_text(original, encoding="utf-8")

    rc, out = run_v2954()
    restored = "GREEN" if rc == 0 else "RED"
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
