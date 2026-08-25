"""Amend fact 1686. I got the sign of 'dominant' backwards.

M120 measured that per-frame brightness drift explains **60.9%** of the patchwork
on `bee-3-cpl` -- a MAJORITY. I folded that as 'on bee-3-cpl it is not the
dominant one', which is simply false, and I did it inside the same session in
which I folded discipline 858 about not misrepresenting my own error rate and
discipline 849 about folds having a systematic sign.

The thing I was reaching for is real and is more interesting than what I wrote:

  M120 (idealised removal of measured level drift, Q metric, 128x128 pure-
  background ROI) says drift accounts for 60.9% of the patchwork on bee-3-cpl.

  M122 (the SHIPPED `--photometric` fit, B12 metric, 12 rule-chosen windows)
  makes bee-3-cpl 6.4% WORSE.

Those are not the same measurement and they do not have to agree -- but the
tension is the finding: the dominant cause is drift, and the tool built to remove
drift fails to remove it on this stack. That indicts the IMPLEMENTATION rather
than the mechanism, and it is a lead. Recording it as unresolved rather than
resolving it in the direction I happened to have written first.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    text = fh.read()

lines = text.split("\n")

hits = [i for i, l in enumerate(lines) if l.startswith("| 1686 |")]
assert len(hits) == 1, "fact 1686 appears %d times" % len(hits)
row = lines[hits[0]]

assert "PER-FRAME BRIGHTNESS DRIFT IS THE MINORITY OF THE EFFECT" in row, \
    "1686 is not the row I think it is"
WRONG = (
    "the two results agree: **drift is a real and "
    "measured contributor, and on `bee-3-cpl` it is not the dominant one.** The "
    "exposure fix was never going to solve this frame."
)
assert WRONG in row, "the erroneous clause is not where I expect it"

RIGHT = (
    "the two results are **in unresolved tension, and "
    "ORCH's first fold of this fact stated it backwards.** Drift is the "
    "**MAJORITY** cause of the patchwork on `bee-3-cpl` (60.9%), yet the shipped "
    "`--photometric` fit makes that same stack **6.4% worse**. The measurements "
    "differ in metric (`Q` over one 128x128 pure-background ROI vs `B12` over 12 "
    "rule-chosen windows) and in method (**idealised removal of the measured level "
    "drift** vs **the fitted correction the code actually applies**), so they need "
    "not agree -- but the gap is the lead: **the dominant cause is drift and the "
    "tool built to remove drift fails to remove it here, which indicts the "
    "implementation rather than the mechanism.** Open question: does an idealised "
    "per-frame level removal beat `--photometric` on `bee-3-cpl`?"
)

# Also fix the headline, which asserted the minority reading.
assert row.count("PER-FRAME BRIGHTNESS DRIFT IS THE MINORITY OF THE EFFECT") == 1
new = row.replace(
    "PER-FRAME BRIGHTNESS DRIFT IS THE MINORITY OF THE EFFECT",
    "PER-FRAME BRIGHTNESS DRIFT IS THE MAJORITY OF THE PATCHWORK, AND THE SHIPPED "
    "FIX STILL MAKES THIS STACK WORSE",
    1,
)
new = new.replace(WRONG, RIGHT, 1)

assert new != row, "amendment did not land"
assert "MINORITY" not in new, "stale headline survived"
assert "not the dominant one" not in new, "stale clause survived"
assert new.count("|") == 5, "pipe count %d" % new.count("|")
assert _re.sub(r"`[^`]*`", "", new).count("**") % 2 == 0, "unbalanced bold"
assert new.startswith("| 1686 | MEASURED | M120 |"), "lost status/attribution"
for ch in new:
    assert ch == "\t" or ord(ch) >= 32, "control char"

lines[hits[0]] = new
out = "\n".join(lines)
assert out.count("| 1686 |") == 1

with io.open(PATH, "w", encoding="utf-8") as fh:
    fh.write(out)
print("amended fact 1686: MINORITY -> MAJORITY, and the false 'not dominant' clause")
print("  the tension with fact 1678 is now recorded as unresolved, with the")
print("  discriminating experiment named.")
