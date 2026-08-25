"""Fold M120: the patchwork is proved, and my mechanism for it is refuted.

Amends fact 1604. Adds facts 1682-1687 and disciplines 857-858.

Two things happen here and they must not be blurred together:

  (a) My fact 1604 proposed a mechanism. Two of its three limbs are now REFUTED
      by measurement. But 1604 was folded as ARGUED and carried the word
      'Unverified' in its own text, so this is the labelling system working as
      designed -- NOT another instance of discipline 849, whose subject is
      findings mislabelled or overstated in the fold. I record that distinction
      explicitly, because inflating my own error count is the mirror image of
      the same bias discipline 849 describes.

  (b) The CLASS of the claim survives and is now proved rather than observed,
      and the defect is worse than I reported: it is in the SHIPPED default
      render, not only in the gate-0 image I was shown.
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


def insert_after_fact_row(number, block):
    hits = [i for i, l in enumerate(lines) if l.startswith("| %d |" % number)]
    assert len(hits) == 1, "fact row %d appears %d times" % (number, len(hits))
    for k, text in enumerate(block):
        lines.insert(hits[0] + 1 + k, text)
    return "fact table"


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


# ---------------------------------------------------------------- amendment
AMEND_ANCHOR = "| 1604 | ARGUED | ORCH | "
AMEND_PREFIX = (
    "**[REFUTED IN TWO OF ITS THREE LIMBS by M120, facts 1682-1687. Limb 1 (the "
    "background response is flat and noise-dominated) is FALSE: it stands 15.0x "
    "above the pure-noise ceiling and swings 8.6 noise SD through focus. Limb 2 "
    "(each polygon gathers from a different frame) is FALSE: the shipped gate "
    "averages 166.8 of 299 frames per pixel. Limb 3 (brightness drift makes the "
    "steps) is PARTIAL: drift explains 60.9%, and 39.1% survives removing it "
    "entirely. The prescribed fix, `STREHL_SOFT_GATE`, has separately been "
    "rejected four times. Fact 1603's CLASS survives and is strengthened. This "
    "fact was folded as ARGUED and said 'Unverified' in its own text, so its "
    "refutation is the labelling system working -- it is NOT an instance of "
    "discipline 849, which concerns findings folded as stronger than their "
    "source.]** "
)

hits = [i for i, l in enumerate(lines) if l.startswith(AMEND_ANCHOR)]
assert len(hits) == 1, "fact 1604 anchor appears %d times" % len(hits)
row1604 = lines[hits[0]]
assert "A MECHANISM FOR THE PATCHWORK" in row1604, "1604 is not the row I think it is"
assert "REFUTED IN TWO OF ITS THREE LIMBS" not in row1604, "1604 already amended"
amended = row1604.replace(AMEND_ANCHOR, AMEND_ANCHOR + AMEND_PREFIX, 1)
assert amended != row1604, "amendment did not land"
assert amended.count("|") == 5, "amended 1604 pipe count %d" % amended.count("|")
assert _re.sub(r"`[^`]*`", "", amended).count("**") % 2 == 0, "amended 1604 bold"

NEW_FACTS = [
    (
        1682,
        "MEASURED",
        "M120",
        "**THE MERGE MANUFACTURES STRUCTURE THAT IS IN NO INPUT FRAME, AND THIS IS "
        "NOW A PROOF RATHER THAN AN AESTHETIC JUDGEMENT.** In a 128x128 pure-"
        "background ROI of `bee-3-cpl` where **every one of the 299 input frames is "
        "featureless**, band-pass contrast `Q` (normalised so the **noisiest single "
        "input frame** is 1.0) reads **4.337 for the SHIPPED DEFAULT render**. The "
        "arithmetic mean of the same frames reads **0.343**, a single input frame "
        "**0.308**, and -- the limb that makes it a proof -- **any spatially "
        "constant convex weighting whatsoever is bounded above by 1.284**. The "
        "shipped render exceeds that bound by **3.4x**, so **no fixed set of frame "
        "weights can produce what the merge produced**; the structure is created by "
        "the *spatial variation* of the weights themselves.",
    ),
    (
        1683,
        "MEASURED",
        "M120",
        "**THE PATCHWORK IS IN THE SHIPPED DEFAULT RENDER, NOT ONLY IN THE GATE-0 "
        "IMAGE ORCH WAS SHOWN -- AND M120 RETRACTED ITS OWN EARLIER CLAIM TO THE "
        "CONTRARY.** `Q` = **7.166** at gate 0, **4.615** at gate 2, and **4.337** "
        "at the **shipped gate 4**: raising the gate reduces the defect by 39% and "
        "**does not remove it**, and every arm violates the 1.284 bound. M120's own "
        "intermediate finding that the shipped render was clean is **explicitly "
        "retracted in its final report**. Fact 1603 is therefore right and **worse "
        "than ORCH stated**.",
    ),
    (
        1684,
        "MEASURED",
        "M120",
        "**THE DEFOCUSED BACKGROUND IS NOT NOISE-DOMINATED, WHICH KILLS THE "
        "MECHANISM ORCH PROPOSED.** Fact 1604 assumed that where a region is "
        "defocused in every frame the through-focus response is flat and the argmax "
        "is near-random. Measured: the response stands **15.0x above the pure-noise "
        "ceiling** and swings **8.6 noise SD** through focus. There is real signal "
        "there, so the polygons are **not** a random field snapped flat by the "
        "regulariser, and the soft gate cannot be the cure by that route.",
    ),
    (
        1685,
        "MEASURED",
        "M120",
        "**THE SHIPPED MERGE DOES NOT GATHER EACH POLYGON FROM A DIFFERENT FRAME.** "
        "The second limb of fact 1604 assumed near-singleton selection in the "
        "background. Measured at the shipped gate: **166.8 of 299 frames averaged "
        "per pixel**. The patchwork survives an average over more than half the "
        "stack, which is a far stronger statement about the defect than ORCH's "
        "single-frame story -- **averaging 167 frames is supposed to be what makes "
        "artifacts go away.**",
    ),
    (
        1686,
        "MEASURED",
        "M120",
        "**PER-FRAME BRIGHTNESS DRIFT IS THE MINORITY OF THE EFFECT.** Removing "
        "inter-frame level drift entirely accounts for **60.9%** of the patchwork; "
        "**39.1% survives**. Read together with fact 1678 -- where `--photometric` "
        "cuts blotch **29%** on the highest-drift stack and makes the low-drift "
        "`bee-3-cpl` **6.4% worse** -- the two results agree: **drift is a real and "
        "measured contributor, and on `bee-3-cpl` it is not the dominant one.** The "
        "exposure fix was never going to solve this frame.",
    ),
    (
        1687,
        "MEASURED",
        "M120",
        "**THE INSTRUMENT IS CONTROLLED IN ALL THREE DIRECTIONS AND TWO "
        "IMPLEMENTATIONS AGREE TO FOUR SIGNIFICANT FIGURES.** Null: the plain mean "
        "reads **0.343**, inside the bound. Placebo: gate-4 admitted sets with **all "
        "frames made identical** reads **0.3085**, so the *weighting pattern alone* "
        "produces nothing. Positive control: a planted 24-cell patchwork reads "
        "**6.694**, so the metric responds to the effect it claims to measure. And "
        "the independent M87 **Python** gate-0 arm and the **Rust** "
        "`armM-gate0-binlin.tif` both read **7.166** -- *identical to 4 s.f.* across "
        "two separate implementations. **It consumed no new renders**: every number "
        "comes from artifacts M87, M93 and ORCH had already produced.",
    ),
]

NEW_DISCIPLINES = [
    (
        857,
        "**Turn an aesthetic complaint into a proof by deriving what the estimator "
        "is *incapable* of producing, then showing the output exceeds it.** M120 did "
        "not argue that the patchwork looks wrong; it computed that **any spatially "
        "constant convex weighting is bounded above by Q = 1.284** and measured the "
        "shipped render at **4.337**. That converts *I do not like this background* "
        "into *no fixed set of frame weights can have produced this background*, "
        "which cannot be answered by taste, and which localises the cause to the "
        "spatial variation of the weights. **Where a bound is derivable from the "
        "estimator's own form, derive it -- it is worth more than another ratio.**",
    ),
    (
        858,
        "**A refuted `ARGUED` fact is the labelling system working; do not file it "
        "with the folding errors.** Fact 1604 was wrong in two limbs and was folded "
        "as `ARGUED` with 'Unverified' written into its own text, so it misled "
        "nobody and cost one milestone's dispatch. Discipline 849's subject is "
        "different and narrower: findings folded **stronger than the source "
        "supports** -- a synthetic plant folded as a real scene, `ARGUED` folded as "
        "`MEASURED`, a qualifier dropped. **Counting honest refuted hypotheses as "
        "orchestrator errors inflates the error rate in the pessimistic direction, "
        "which is the same bias with the sign flipped, and it would make the one "
        "discipline that measures my reliability useless.**",
    ),
]

log = []
for number, status, source, text in NEW_FACTS:
    row = "| %d | %s | %s | %s |" % (number, status, source, text)
    assert row.count("|") == 5, "fact %d: pipe count %d" % (number, row.count("|"))
    assert _re.sub(r"`[^`]*`", "", row).count("**") % 2 == 0, "fact %d: bold" % number
    for ch in row:
        assert ch == "\t" or ord(ch) >= 32, "fact %d: control char" % number
    log.append((number, row))

dlog = []
for number, text in NEW_DISCIPLINES:
    entry = "%d. %s" % (number, text)
    assert _re.sub(r"`[^`]*`", "", entry).count("**") % 2 == 0, "disc %d: bold" % number
    for ch in entry:
        assert ch == "\t" or ord(ch) >= 32, "disc %d: control char" % number
    dlog.append((number, entry))

# Every assertion above runs before any mutation.
lines[hits[0]] = amended
print("amended fact 1604")

prev = 1681
for number, row in log:
    where = insert_after_fact_row(prev, [row])
    prev = number
    print("fact %d -> %s" % (number, where))

dprev = 856
for number, entry in dlog:
    where = insert_after_entry(dprev, r"^## 5\. ", [entry])
    dprev = number
    print("discipline %d -> %s" % (number, where))

out = "\n".join(lines)
for number, _ in log:
    assert len([l for l in lines if l.startswith("| %d |" % number)]) == 1, number
for number, _ in dlog:
    assert out.count("\n%d. " % number) == 1, number
assert out.count("REFUTED IN TWO OF ITS THREE LIMBS") == 1
assert "| 1604 | ARGUED | ORCH |" in out, "1604 lost its status/attribution"

with io.open(PATH, "w", encoding="utf-8") as fh:
    fh.write(out)
print("wrote %s" % PATH)
