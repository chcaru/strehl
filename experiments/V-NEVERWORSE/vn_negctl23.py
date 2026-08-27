"""Negative control for vn_verify23.py -- does the checker actually go RED?

A checker that has only ever returned 0 is indistinguishable from one that
cannot fail. This plants defects in RESULT.md section 2.3, one at a time, and
requires each to be caught.

Rules obeyed here: the file is copied to $env:TEMP first and restored from that
copy (never `git checkout --`, which reverts to HEAD and destroys uncommitted
work); every mutation is anchored on a unique full-line string and hard-errors
if the anchor does not land exactly once.

  python vn_negctl23.py     ->  rc 0 only if every plant is caught
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "RESULT.md")
CHK = os.path.join(HERE, "vn_verify23.py")

# (label, unique full line, mutated line, what it should break)
PLANTS = [
    ("D1 blotch min",
     "| blotch factor | 0.9870 (`leaf-2-cpl`) | 0.9996 | 1.0049 (`lavendar-cpl`) |",
     "| blotch factor | 0.9871 (`leaf-2-cpl`) | 0.9996 | 1.0049 (`lavendar-cpl`) |",
     "blotch min"),
    ("D2 worst departure",
     "Worst departure from unity on any subject, either statistic, either arm: **1.53%**. **The",
     "Worst departure from unity on any subject, either statistic, either arm: **1.43%**. **The",
     "worst departure"),
    ("D3 scale range",
     "**0.7745 … 0.9996, median 0.9566** — source windows are magnified by up to **1.29x**. W1",
     "**0.7745 … 0.9997, median 0.9566** — source windows are magnified by up to **1.29x**. W1",
     "fitted scale range"),
    ("D4 frame count",
     "the source arm actually applies, over all **510** admitted frames across the 26 subjects:",
     "the source arm actually applies, over all **511** admitted frames across the 26 subjects:",
     "510 admitted frames"),
    ("D5 magnification",
     "**0.7745 … 0.9996, median 0.9566** — source windows are magnified by up to **1.29x**. W1",
     "**0.7745 … 0.9996, median 0.9566** — source windows are magnified by up to **1.31x**. W1",
     "magnification"),
    ("D6 scale median",
     "**0.7745 … 0.9996, median 0.9566** — source windows are magnified by up to **1.29x**. W1",
     "**0.7745 … 0.9996, median 0.9576** — source windows are magnified by up to **1.29x**. W1",
     "fitted scale median"),
    ("D7 blotch median",
     "| blotch factor | 0.9870 (`leaf-2-cpl`) | 0.9996 | 1.0049 (`lavendar-cpl`) |",
     "| blotch factor | 0.9870 (`leaf-2-cpl`) | 0.9997 | 1.0049 (`lavendar-cpl`) |",
     "blotch median"),
    ("D8 blotch max subject",
     "| blotch factor | 0.9870 (`leaf-2-cpl`) | 0.9996 | 1.0049 (`lavendar-cpl`) |",
     "| blotch factor | 0.9870 (`leaf-2-cpl`) | 0.9996 | 1.0059 (`lavendar-cpl`) |",
     "blotch max"),
    ("D9 chroma min",
     "| chroma factor | 0.9847 (`wrapped-text-1`) | 0.9990 | 1.0000 |",
     "| chroma factor | 0.9837 (`wrapped-text-1`) | 0.9990 | 1.0000 |",
     "chroma min"),
    ("D10 chroma median",
     "| chroma factor | 0.9847 (`wrapped-text-1`) | 0.9990 | 1.0000 |",
     "| chroma factor | 0.9847 (`wrapped-text-1`) | 0.9991 | 1.0000 |",
     "chroma median"),
    ("D11 under-coverage",
     "certified the resampler at `1 + 1.66e-2` = **1.7%**. That is a **17.5x under-coverage**, and",
     "certified the resampler at `1 + 1.66e-2` = **1.7%**. That is a **27.5x under-coverage**, and",
     "17.5x smaller"),
    ("D12 identity departure",
     "   subjects and both statistics, worst departure **3.5e-7**.",
     "   subjects and both statistics, worst departure **3.5e-9**.",
     "identity departure"),
    ("D13 relhf control",
     "**x0.66–x0.90**. The round trip demonstrably moves the quantity that should move and leaves",
     "**x0.86–x0.90**. The round trip demonstrably moves the quantity that should move and leaves",
     "relhf"),
    ("D14 coverage",
     "coverage : field of view scaled to 0.9236 so that EVERY frame covers every pixel",
     "coverage : field of view scaled to 0.9136 so that EVERY frame covers every pixel",
     "coverage"),
    ("N1 placebo -- prose outside the checked span",
     "**Lane question.** Measure the merge-attributable ratio (master against its own source",
     "**Lane question.** Measure the merge-attributed ratio (master against its own source",
     None),
]


def run():
    p = subprocess.run([sys.executable, CHK], cwd=HERE,
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def main():
    orig = open(MD, encoding="utf-8").read()
    keep = os.path.join(tempfile.gettempdir(), "vn_RESULT_negctl.md")
    shutil.copy2(MD, keep)
    print("baseline copy at %s (%d bytes)" % (keep, len(orig)))

    rc, out = run()
    if rc != 0:
        raise SystemExit("BASELINE IS NOT GREEN -- fix that before planting.\n"
                         + out)
    print("baseline: GREEN\n")

    caught = 0
    try:
        for tag, old, new, expect in PLANTS:
            n = orig.count(old)
            if n != 1:
                raise SystemExit("ANCHOR NOT UNIQUE for %s: %d occurrences.\n"
                                 "A plant that does not land reads as a pass."
                                 % (tag, n))
            open(MD, "w", encoding="utf-8").write(orig.replace(old, new, 1))
            rc, out = run()
            # Key on the FAILED: block, not on lines containing "MISMATCH":
            # the checker's own summary line reads "N claims checked, 0
            # MISMATCH", so a substring test matched it on every GREEN run and
            # reported the placebo as a false positive. A detector that fires
            # on the word for "no defects" is not a detector.
            miss = "\n".join(l for l in out.splitlines()
                             if l.strip().startswith("FAILED:"))
            if expect is None:
                # placebo: this text is outside the span the checker reads, so
                # a checker that goes RED here is reading more than it claims.
                ok = rc == 0 and not miss
                caught += ok
                print("  %-42s -> %s" % (
                    tag, "GREEN (correct: placebo)" if ok
                    else "RED -- FALSE POSITIVE, checker over-reaches"))
                continue
            ok = rc != 0 and expect.lower() in miss.lower()
            caught += ok
            print("  %-42s -> %s   %s" % (
                tag, "RED (caught)" if ok else "GREEN -- MISSED",
                "" if ok else "expected a MISMATCH mentioning %r" % expect))
        if os.environ.get("VN_NEGCTL_DEBUG"):
            print("\n--- last run rc=%s ---\n%s" % (rc, out[-2000:]))
    finally:
        shutil.copy2(keep, MD)

    restored = open(MD, encoding="utf-8").read()
    if restored != orig:
        raise SystemExit("RESTORE FAILED -- RESULT.md does not match the copy")
    rc, _ = run()
    print("\nrestored byte-identical; checker back to %s"
          % ("GREEN" if rc == 0 else "RED"))
    print("%d/%d plants caught" % (caught, len(PLANTS)))
    return 0 if (caught == len(PLANTS) and rc == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
