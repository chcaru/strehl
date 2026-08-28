"""Negative control for `vn_verify927.py`.

A green verifier is a claim about the INSTRUMENT, not about the section.  An
uncommissioned verifier and a verifier that checks nothing print the same
GREEN.  So each plant below is a defect the verifier MUST catch, and the run
fails if any of them still reads GREEN.

TWO RULES THIS FILE OBEYS, BOTH LEARNED EXPENSIVELY IN THIS PROJECT.
  1. Every plant is anchored on a string proven UNIQUE in the file, and the
     run hard-errors if the anchor is missing or ambiguous.  A bare
     `replace(x, y, 1)` can silently land on the wrong occurrence, and then a
     GREEN means the plant never happened rather than that the check works.
  2. The pristine file is copied to TEMP and restored from that copy.  It is
     never restored with `git checkout --`, which reverts to HEAD and would
     destroy uncommitted work in a tree six other lanes are writing to.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, "RESULT.md")
VERIFY = os.path.join(HERE, "vn_verify927.py")

PLANTS = [
    ("L0 R last digit",
     "| **1.1628** | [1.1435, 1.1814] | 1.0783 | **FAIL(noise)** |",
     "| **1.1629** | [1.1435, 1.1814] | 1.0783 | **FAIL(noise)** |"),
    ("qualified-band shipping ratio",
     "| `coffee-bubbles` | shipping | 1.4069 | **1.1360** | 1.3562 | 1.6220 |",
     "| `coffee-bubbles` | shipping | 1.4069 | **1.1361** | 1.3562 | 1.6220 |"),
    ("my boundary value",
     "mine reads **0.14** on both subjects against",
     "mine reads **0.20** on both subjects against"),
    ("gauge control cell count",
     "gave **48 of 48 scene cells bit-identical**",
     "gave **47 of 48 scene cells bit-identical**"),
    ("published boundary",
     "published **0.25** and **0.20**",
     "published **0.30** and **0.20**"),
    ("112MSDCF confidence arm",
     "| `112MSDCF` | confidence | 1.0124 | **0.8953** | 0.8697 | 0.9258 |",
     "| `112MSDCF` | confidence | 1.0124 | **0.8952** | 0.8697 | 0.9258 |"),
]


def run_verifier():
    p = subprocess.run([sys.executable, VERIFY], capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    pristine = open(RESULT, encoding="utf-8").read()
    tmp = os.path.join(tempfile.gettempdir(), "vn_RESULT_927_pristine.md")
    shutil.copy2(RESULT, tmp)
    print("pristine copy: %s" % tmp)

    rc, _ = run_verifier()
    if rc != 0:
        print("REFUSING: verifier is not GREEN before any plant is applied")
        sys.exit(1)
    print("baseline GREEN confirmed\n")

    caught = missed = 0
    try:
        for name, old, new in PLANTS:
            n = pristine.count(old)
            if n != 1:
                raise AssertionError(
                    "PLANT ANCHOR NOT UNIQUE: %r occurs %d times for plant %r"
                    % (old, n, name))
            mutated = pristine.replace(old, new, 1)
            if mutated == pristine:
                raise AssertionError("PLANT IS INERT: %r changed nothing" % name)
            with open(RESULT, "w", encoding="utf-8") as fh:
                fh.write(mutated)
            rc, out = run_verifier()
            if rc != 0:
                caught += 1
                print("  CAUGHT   %s" % name)
            else:
                missed += 1
                print("  MISSED   %s  <-- verifier is blind to this defect"
                      % name)
    finally:
        shutil.copy2(tmp, RESULT)
        print("\nrestored from %s" % tmp)

    rc, _ = run_verifier()
    if rc != 0:
        print("RESTORE FAILED: verifier is not GREEN again")
        sys.exit(1)
    print("post-restore GREEN confirmed")

    total = caught + missed
    print("\n  planted %d   caught %d   missed %d" % (total, caught, missed))
    print("  %s" % ("GREEN -- verifier detects every planted defect"
                    if missed == 0 else "RED -- %d blind spot(s)" % missed))
    sys.exit(0 if missed == 0 else 1)


if __name__ == "__main__":
    main()
