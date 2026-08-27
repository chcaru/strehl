"""Negative control for verify_band.py. A verifier that has never gone red is a
claim, not a gate.

Each defect is anchored on a UNIQUE FULL-LINE string and the harness hard-errors
if the anchor does not land or is not unique. A bare `replace(x, y, 1)` can
silently mutate the first coincidental match somewhere else in the document and
report GREEN, which is the failure this file exists to exclude.

The document is restored from a copy taken in TEMP. It is never restored with
`git checkout --`, which reverts to HEAD and has destroyed uncommitted work in
this repository before.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))),
                   "docs", "research", "BUILD-GATE-4.md")

DEFECTS = [
    ("D1 12.4 cell 109MSDCF/G170 -10.52 -> -10.62",
     "| `109MSDCF` | +87.27\\* | +43.80\\* | \u221210.52\\* | \u221239.93\\* | \u221270.13\\* | \u221282.02\\* |",
     "| `109MSDCF` | +87.27\\* | +43.80\\* | \u221210.62\\* | \u221239.93\\* | \u221270.13\\* | \u221282.02\\* |",
     "REPORT 12.4 says 109MSDCF/G170"),
    ("D2 12.1 cell coffee-bubbles 0.4931 -> 0.4930",
     "| `coffee-bubbles` | 0.4931 |",
     "| `coffee-bubbles` | 0.4930 |",
     "REPORT 12.1 says coffee-bubbles"),
    ("D3 section 11 retirement notice deleted",
     "\u00a712.3 RETIRES THIS ITEM'S",
     "\u00a712.3 discusses this item's",
     "section 11 marks its item retired"),
    ("D4 the corrected 2.76x reverted to the withdrawn 2.7x",
     "over-predicted by 2.76\u00d7",
     "over-predicted by 2.7\u00d7",
     None),
]


def run():
    p = subprocess.run([sys.executable, os.path.join(HERE, "verify_band.py")],
                       capture_output=True, text=True, cwd=HERE)
    return p.returncode, p.stdout + p.stderr


def main():
    tmp = os.path.join(tempfile.gettempdir(), "BUILD-GATE-4.negctl.md")
    shutil.copyfile(DOC, tmp)
    orig = open(DOC, encoding="utf-8").read()
    rc, out = run()
    if rc != 0:
        print("BASELINE IS NOT GREEN (rc=%d) -- commission aborted" % rc)
        print(out[-2000:])
        return 1
    print("baseline GREEN\n")
    caught = missed = 0
    try:
        for name, old, new, expect in DEFECTS:
            n = orig.count(old)
            if n != 1:
                raise SystemExit("ANCHOR NOT UNIQUE for %s: %d occurrence(s) of %r"
                                 % (name, n, old))
            open(DOC, "w", encoding="utf-8", newline="").write(orig.replace(old, new))
            rc, out = run()
            hit = expect is None or expect in out
            if rc != 0 and hit:
                caught += 1
                print("%-52s RED   CAUGHT" % name)
            else:
                missed += 1
                print("%-52s rc=%d MISSED%s" % (name, rc,
                      "" if rc != 0 else " (verifier stayed green)"))
                if rc != 0:
                    print("     went red but not for the expected reason %r" % expect)
    finally:
        shutil.copyfile(tmp, DOC)
    rc, out = run()
    print("\nrestored, re-verify rc=%d" % rc)
    print("caught %d / %d, missed %d" % (caught, len(DEFECTS), missed))
    return 0 if (missed == 0 and rc == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
