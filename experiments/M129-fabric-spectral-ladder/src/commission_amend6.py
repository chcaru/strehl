"""Commission check_amend6.py by planting defects it must catch.

It has already caught two errors I did not plant -- two cells of the SNR table read
off a single ROI's row instead of the median -- which is the strongest evidence a
checker can offer. This adds the deliberate half: every class of figure it claims to
guard is corrupted in turn, on a COPY, and the checker must go red and must name the
right line.

Two rules from the house, both learned the hard way and both enforced here:

  Anchor every mutation on a unique full-line string and hard-error if it does not
  land. A bare replace(old, new, 1) that silently misses produces a green run that
  looks like a passing control and is actually a test of nothing.

  Never mutate the real file. The copy lives in TEMP and the original is never
  written, so there is no path by which a failed control can damage the record.

Exit code 0 only if every plant is caught.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(HERE, "PREREGISTRATION.md")
CHECKER = os.path.join(HERE, "src", "check_amend6.py")

# (name, unique full line to find, replacement, substring the failure must name)
PLANTS = [
    ("SNR table, knee row",
     "| knee, 29.3-44.9 cy/mm | 18.6 | 23.1 | 39.7 | 23.2 | 7.7 |",
     "| knee, 29.3-44.9 cy/mm | 18.6 | 23.1 | 39.7 | 23.2 | 9.9 |",
     "knee band, f18"),
    ("SNR table, low row",
     "| low, 7.8-17.6 cy/mm | 2011 | 1707 | 2802 | 2591 | 1730 |",
     "| low, 7.8-17.6 cy/mm | 2011 | 1707 | 2802 | 2591 | 1930 |",
     "low band, f18"),
    ("equalisation cost, a floor multiplier",
     "| 4 | 2.23 | 1.55 | 6.10 | 2.73 |",
     "| 4 | 1.23 | 1.55 | 6.10 | 2.73 |",
     "ROI 4 f11 floor multiplier"),
    ("equalisation cost, a residual ratio",
     "| 2 | 1.65 | 1.48 | 5.59 | 3.39 |",
     "| 2 | 1.65 | 1.48 | 5.59 | 4.39 |",
     "ROI 2 knee ratio after"),
    ("units table, the ratio",
     "| low band, the artefact alone | 1.72x | **3.1 points** |",
     "| low band, the artefact alone | 2.72x | **3.1 points** |",
     "low primary-arm ratio"),
    ("units table, the derived points",
     "| knee band, contaminated by the signal | 5.69x | 9.9 points |",
     "| knee band, contaminated by the signal | 5.69x | 19.9 points |",
     "knee differential points"),
    ("A4 table",
     "| 0.557 | 0.708 | 0.823 | 0.083 | **-0.021** |",
     "| 0.557 | 0.708 | 0.823 | 0.483 | **-0.021** |",
     "high band, f14"),
    ("prose range, floor multiplier",
     "The floor rises by 1.47x to 2.23x, which is a real but modest cost. **The residual",
     "The floor rises by 1.47x to 3.23x, which is a real but modest cost. **The residual",
     "max floor multiplier"),
    ("prose range, residual knee ratio",
     "knee-band ratio of 2.7x to 3.6x is not a failure to equalise: it is the roll-off",
     "knee-band ratio of 1.7x to 3.6x is not a failure to equalise: it is the roll-off",
     "min residual knee ratio"),
]


def run(doc):
    r = subprocess.run([sys.executable, CHECKER, doc], capture_output=True,
                       text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    rc, out = run(DOC)
    print(f"baseline on the real document: exit {rc}")
    if rc != 0:
        print("BASELINE IS NOT GREEN. Commissioning a checker against a document")
        print("that already fails proves nothing; fix the document first.")
        print(out)
        return 1
    print()

    tmpdir = tempfile.mkdtemp(prefix="amend6-")
    with open(DOC, encoding="utf-8") as fh:
        original = fh.read()
    caught = 0
    for name, old, new, must_name in PLANTS:
        n = original.count(old)
        if n != 1:
            print(f"  ANCHOR MISS  {name}: the anchor line occurs {n} times, "
                  f"not once. The plant cannot be placed unambiguously, so this")
            print(f"               control is void rather than passing.")
            return 1
        path = os.path.join(tmpdir, "PREREGISTRATION.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(original.replace(old, new, 1))
        rc, out = run(path)
        named = any(l.startswith("  FAIL") and must_name in l
                    for l in out.splitlines())
        ok = rc != 0 and named
        caught += ok
        if ok:
            verdict = "caught, and named the right line"
        elif rc != 0:
            verdict = f"went red but did NOT name '{must_name}' -- wrong line"
        else:
            verdict = "MISSED, the checker stayed green"
        print(f"  {'ok  ' if ok else 'FAIL'} {name:40s} {verdict}")

    shutil.rmtree(tmpdir, ignore_errors=True)
    print()
    print(f"{caught}/{len(PLANTS)} plants caught")
    if caught == len(PLANTS):
        print("check_amend6.py is commissioned.")
        return 0
    print("check_amend6.py is NOT commissioned; do not rely on its green.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
