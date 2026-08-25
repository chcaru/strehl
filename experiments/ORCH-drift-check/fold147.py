"""Discipline 849: the fold is an unaudited transformation, and it is biased.

Every ORCH folding error found tonight moved in the same direction.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    lines = fh.read().split("\n")


def section_bounds(pattern):
    hits = [i for i, l in enumerate(lines) if _re.match(pattern, l)]
    assert hits, "no section heading matching %r" % pattern
    start = hits[-1]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if _re.match(r"^#{1,3} ", lines[i]):
            end = i
            break
    return start, end


def insert_after_entry(number, section_pattern, block):
    start, end = section_bounds(section_pattern)
    hits = [i for i in range(start, end) if lines[i].startswith("%d. " % number)]
    assert len(hits) == 1, "entry %d appears %d times in %s" % (
        number, len(hits), lines[start].strip())
    j = hits[0] + 1
    while j < end and lines[j].strip() and not _re.match(r"^\d+\. ", lines[j]):
        j += 1
    for k, text in enumerate(block):
        lines.insert(j + k, text)
    return lines[start].strip()


NEW_DISCS = [
    (
        849,
        "**THE ORCHESTRATOR'S FOLD IS AN UNAUDITED TRANSFORMATION, AND ON THE NIGHT IT WAS "
        "FIRST AUDITED, EVERY ERROR IN IT RAN THE SAME WAY.** The corpus verifies "
        "milestones. It has never verified **the step that turns a milestone's report into "
        "a fact**, and that step is performed by the one participant nobody checks. Audited "
        "on 2026-08-24/25, six ORCH errors surfaced in a single night: a **synthetic "
        "plant's** number folded as *the real occluding scene* (fact 1598); two experiments "
        "**spliced**, M86's worst-case half-pixel shift borrowed into M87's warp (fact "
        "1595); a mechanism its own author **explicitly labelled ARGUED** folded as MEASURED "
        "(fact 1599); a **700 x 1100 ROI window** folded as *the shipped frame* (fact 1601); "
        "**the largest of five numbers** for one effect quoted without the qualifier that "
        "gives it meaning (fact 1662); and a default-on recommendation that, on a scan of "
        "every document in the corpus, **had no author at all** and had accreted purely in "
        "ORCH's summarising (fact 1663). **Not one of the six ran toward weakening a claim. "
        "All six ran toward strengthening it.** That is a bias, not a scatter, and its "
        "mechanism is plain: summarising drops qualifiers, and a qualifier is almost always "
        "what makes a finding smaller. **Consequences.** Fold from the milestone's own "
        "primary artefacts rather than from its prose wherever a number is load-bearing; "
        "carry the author's own epistemic label (MEASURED / ARGUED) across unchanged, "
        "because downgrading it is a finding and upgrading it is a fabrication; name the "
        "scene, the space and the window in the same sentence as the number; and **treat "
        "the fold as a workstream that requires an independent verifier exactly like any "
        "other**, because the rule that an author must not verify their own work has no "
        "exemption for the person writing it down.",
    ),
]

disc_block = ["%d. %s" % d for d in NEW_DISCS]

for line in disc_block:
    stripped = _re.sub(r"`[^`]*`", "", line)
    assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in line:
        o = ord(ch)
        assert not (o < 0x20 or o == 0x7F), "control char 0x%02X" % o

s = insert_after_entry(848, r"^## 5\. ", disc_block)
with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))
print("discipline 849 -> %s" % s)
