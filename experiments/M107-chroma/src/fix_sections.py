"""Repair a mis-anchored insertion in the M107 report.

An `edit` whose old_str was the section-12 heading replaced that heading with the
new section 13, leaving 13 sitting above a headless 12. This moves the 13 block to
the end of the file and restores the 12 heading in place, then asserts the result.

Deterministic and re-runnable: it verifies the expected damage before touching
anything and refuses to write if the file is not in exactly that state.
"""

import sys
import pathlib

REPORT = pathlib.Path(
    r"C:\dev\blog\death-of-software\projects\strehl\docs\research\M107-chroma.md"
)

H12 = "## 12. Addendum — the ORCH-kernel arms (E8)"
H13 = "## 13. Provenance — every invocation, recorded in full"
END13 = "That is weaker than §4 as written, and §8's list of open items should be read with it."

text = REPORT.read_text(encoding="utf-8")
lines = text.split("\n")

if H12 in lines:
    print("section 12 heading already present -- nothing to repair")
    sys.exit(0)

i13 = lines.index(H13)
iend = lines.index(END13)

# The 13 block runs from its heading through its last line plus the blank
# separator that followed the original heading.
block = lines[i13 : iend + 1]
rest = lines[:i13] + lines[iend + 1 :]

# Drop the leading blanks the removal exposed, then restore 12's heading there.
while rest[i13:] and rest[i13].strip() == "":
    del rest[i13]
rest[i13:i13] = [H12, ""]

# Append 13 at the end, separated by a blank line.
while rest and rest[-1].strip() == "":
    rest.pop()
out = rest + [""] + block + [""]

new = "\n".join(out)

# Assertions: both headings present, exactly once, and 12 precedes 13.
assert new.count(H12) == 1, "section 12 heading not restored exactly once"
assert new.count(H13) == 1, "section 13 heading duplicated"
assert new.index(H12) < new.index(H13), "section 12 must precede section 13"
assert END13 in new, "section 13 body lost"
# No content may be lost: the repair only reorders.
assert sorted(l for l in new.split("\n") if l.strip()) == sorted(
    l for l in (text + "\n" + H12).split("\n") if l.strip()
), "line multiset changed -- repair lost or invented content"

REPORT.write_text(new, encoding="utf-8")
print("repaired: 12 restored at line", new.split("\n").index(H12) + 1)
print("          13 now at line", new.split("\n").index(H13) + 1)
