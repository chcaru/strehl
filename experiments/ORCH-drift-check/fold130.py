"""Cross-reference fact 1571's `RECOLOURED, NOT REMOVED` confirmation to fact 1588.

1571(b) is factually correct -- the residual sign does flip -- but read alone it
carries the DEFECT framing the phrase was coined under. Fact 1588 shows a flip
with shrinkage is what a working correction produces. Mark it in place so the
row cannot be read without the reinterpretation.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

MARK = (
    " **REINTERPRETED by fact 1588 (M110): a flip WITH SHRINKAGE is what a working "
    "correction produces, not a defect. The residuals quoted here are 25 % and 5.6 % of "
    "the original amplitude, and 5.6 % is exactly this stack's measured gain of 1.0557. "
    "The sign flip is real; reading it as failure was the bar's error.**"
)

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()

anchor = "\n| 1571 | "
assert raw.count(anchor) == 1, "fact 1571 row is not unique"

i = raw.index(anchor) + 1
j = raw.index("\n", i)
row = raw[i:j]

# Prove we have the right row before touching it.
assert "RECOLOURED, NOT REMOVED" in row, "row 1571 does not contain the expected phrase"
assert "132.3" in row and "36.5" in row, "row 1571 does not contain the expected residuals"
assert MARK not in row, "row 1571 is already marked"

body = row.rstrip()
assert body.endswith("|"), "row 1571 does not end in a pipe"
newrow = body[:-1].rstrip() + MARK + " |"

n = len(newrow.replace("\\|", "").split("|")) - 1
assert n == 5, "marked row has %d unescaped pipes, need 5" % n

import re as _re

stripped = _re.sub(r"`[^`]*`", "", newrow)
assert stripped.count("**") % 2 == 0, "odd ** count in marked row"

out = raw[:i] + newrow + raw[j:]
assert out != raw, "marker did not land"

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("marked fact 1571 REINTERPRETED by fact 1588")
