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

NUMERIC_PLANTS = [
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

# CONCLUSION PLANTS.  ORCH's broadcast of 2026-08-28 names this lane: a report
# verifier of ours tested for the PRESENCE of the string "refuted" and passed
# 712 green checks after that section's verdict was flipped to "confirmed",
# with every number left intact.  A presence test cannot detect a reversed
# conclusion.
#
# Every plant in NUMERIC_PLANTS above perturbs a DIGIT.  None of them reverses
# a claim, so passing all six proves nothing about this failure mode.  These
# plants change no number at all -- they flip only the verdict the section
# asserts -- and a verifier that misses them certifies arithmetic while
# leaving the conclusion unguarded.
CONCLUSION_PLANTS = [
    ("L0 verdict flipped FAIL(noise) -> PASS in the results table",
     "| `coffee-bubbles` | **1.1628** | [1.1435, 1.1814] | 1.0783 | **FAIL(noise)** |",
     "| `coffee-bubbles` | **1.1628** | [1.1435, 1.1814] | 1.0783 | **PASS** |"),
    ("the refutation of my own hypothesis flipped to a confirmation",
     "true scene at MID is exactly zero, **refuted it**: with MID content absent the",
     "true scene at MID is exactly zero, **confirmed it**: with MID content absent the"),
    ("withheld verdict flipped to an asserted one",
     "**The subject-level verdict is WITHHELD, by the file's own cross-check.** The",
     "**The subject-level verdict is CONFIRMED, by the file's own cross-check.** The"),
    ("surviving sign flip flipped to a dead one",
     "**Section 9.23.6's sign flip survives qualification on both subjects, at",
     "**Section 9.23.6's sign flip dies under qualification on both subjects, at"),
    ("the unlicensed acuity claim flipped to a licensed one",
     "from, and the \"9.3% relative sharpness cost\" is not licensed as an acuity",
     "from, and the \"9.3% relative sharpness cost\" is licensed as an acuity"),
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
    blind = []
    try:
        for kind, plants in (("numeric", NUMERIC_PLANTS),
                             ("conclusion", CONCLUSION_PLANTS)):
            print("  -- %s plants --" % kind)
            for name, old, new in plants:
                n = pristine.count(old)
                if n != 1:
                    raise AssertionError(
                        "PLANT ANCHOR NOT UNIQUE: %r occurs %d times for plant "
                        "%r" % (old, n, name))
                mutated = pristine.replace(old, new, 1)
                if mutated == pristine:
                    raise AssertionError(
                        "PLANT IS INERT: %r changed nothing" % name)
                with open(RESULT, "w", encoding="utf-8") as fh:
                    fh.write(mutated)
                rc, out = run_verifier()
                if rc != 0:
                    caught += 1
                    print("    CAUGHT   %s" % name)
                else:
                    missed += 1
                    blind.append("%s: %s" % (kind, name))
                    print("    MISSED   %s  <-- verifier is blind to this"
                          % name)
    finally:
        shutil.copy2(tmp, RESULT)
        print("\nrestored from %s" % tmp)

    rc, _ = run_verifier()
    if rc != 0:
        print("RESTORE FAILED: verifier is not GREEN again")
        sys.exit(1)
    print("post-restore GREEN confirmed")

    # ---- RECORD PLANTS.
    # The conclusion checks above claim to DERIVE their expected wording from
    # the records.  A hardcoded string would pass every document plant just as
    # well, so each derivation is proven live by mutating the RECORD and
    # requiring the unchanged document to fail against it.
    import json
    lb = r"C:\dev\strehl-out\V-NEVERWORSE\l0band\coffee-bubbles.json"
    bak = os.path.join(tempfile.gettempdir(), "vn_l0band_cb_pristine.json")
    shutil.copy2(lb, bak)
    rec_caught = rec_missed = 0
    print("\n  -- record plants (prove the derivation is live) --")
    try:
        for name, key, val in (
                ("boundary_agrees True makes WITHHELD wrong",
                 "boundary_agrees", True),
                ("L0 verdict PASS makes the acuity claim licensed",
                 "verdict", "PASS")):
            d = json.load(open(bak))
            if key == "verdict":
                d["L0"]["verdict"] = val
            else:
                d[key] = val
            with open(lb, "w") as fh:
                json.dump(d, fh, indent=1)
            if json.load(open(lb)) == json.load(open(bak)):
                raise AssertionError("RECORD PLANT IS INERT: %s" % name)
            rc, _ = run_verifier()
            if rc != 0:
                rec_caught += 1
                print("    CAUGHT   %s" % name)
            else:
                rec_missed += 1
                blind.append("record: %s" % name)
                print("    MISSED   %s  <-- conclusion is hardcoded, not "
                      "derived" % name)
    finally:
        shutil.copy2(bak, lb)
        os.remove(bak)
    rc, _ = run_verifier()
    if rc != 0:
        print("RECORD RESTORE FAILED: verifier is not GREEN again")
        sys.exit(1)
    print("  post-restore GREEN confirmed")
    caught += rec_caught
    missed += rec_missed

    total = caught + missed
    print("\n  planted %d   caught %d   missed %d" % (total, caught, missed))
    for b in blind:
        print("    BLIND SPOT  %s" % b)
    print("  %s" % ("GREEN -- verifier detects every planted defect"
                    if missed == 0 else "RED -- %d blind spot(s)" % missed))
    sys.exit(0 if missed == 0 else 1)


if __name__ == "__main__":
    main()
