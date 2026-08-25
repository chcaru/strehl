"""Fold M111: the two-arm-ratio protection has a false-clear, and where it lands.

Facts 1716-1720, disciplines 874-876.

This is the second independent correction to ORCH's broadcast triage rule in one
night. M113 corrected the axis (value vs position); M111 corrects the other
question (two-arm ratios are protected) and shows the protection is a property of
the terms' magnitude ratio, not of the expression's form. Both say the same
thing: the SHAPE of the statistic does not determine exposure.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    lines = fh.read().split("\n")


def section_bounds(pattern):
    hits = [i for i, l in enumerate(lines) if _re.match(pattern, l)]
    assert hits
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


def insert_after_entry(number, section_pattern, block):
    start, end = section_bounds(section_pattern)
    hits = [i for i in range(start, end) if lines[i].startswith("%d. " % number)]
    assert len(hits) == 1, "entry %d appears %d times" % (number, len(hits))
    j = hits[0] + 1
    while j < end and lines[j].strip() and not _re.match(r"^\d+\. ", lines[j]):
        j += 1
    for k, text in enumerate(block):
        lines.insert(j + k, text)


NEW_FACTS = [
    (
        1716,
        "MEASURED",
        "M111",
        "**ORCH'S SECOND TRIAGE QUESTION ALSO FALSE-CLEARS, AND THE PROTECTION IS A "
        "PROPERTY OF THE TERMS' MAGNITUDE RATIO RATHER THAN OF THE EXPRESSION'S "
        "FORM.** ORCH measured **-1.0%** for a two-arm ratio under a planted "
        "narrowing and told the fleet such ratios are largely protected by "
        "cancellation. M111 measured **-8.7%** for a statistic that is *also* a "
        "ratio of two arms on the same data. **Both are correct at different "
        "disparities.** Binned by `D` = max/min of the two terms over 1547 tiles, "
        "the median absolute shift runs **0.68% / 0.90% / 3.79% / 6.15% / 6.71% / "
        "7.58% / 8.04%** across `D` in [1.00,1.25) to [8,inf) -- **monotone in "
        "every step**, Spearman **rho = +0.530**. ORCH's number sits at the "
        "comparable-arms end; M111's statistic has **D = 6.105**.",
    ),
    (
        1717,
        "DERIVED",
        "M111",
        "**THE FALSE-CLEAR LANDS ON EXACTLY THE STATISTICS BUILT TO FIND DEFECTS.** "
        "ORCH's two questions are **not independent** -- a two-arm ratio can *be* a "
        "small-over-large ratio -- and **a defect-detection contrast is a strong "
        "term over a weak one almost by definition**. So the rule offering "
        "protection clears precisely the class of statistic this project writes "
        "most often. Combined with fact 1711, the unifying statement is that "
        "**the syntactic shape of a statistic does not determine its exposure**: "
        "what the statistic reads (value vs position) and how unequal its terms "
        "are (disparity `D`) do.",
    ),
    (
        1718,
        "MEASURED",
        "M111",
        "**THE DISPARITY RESULT WAS PRE-REGISTERED 23 SECONDS BEFORE THE DATA "
        "EXISTED.** Registration commit `40da965` at **20:27:57**; run-2 data at "
        "**20:28:20**. 1547 tiles, both readers, every other line identical. This "
        "is the tightest provable ordering of registration and data in the corpus, "
        "and it is what makes a monotone seven-bin table credible rather than a "
        "binning chosen after seeing the shape.",
    ),
    (
        1719,
        "REFUTED",
        "M111",
        "**A MILESTONE'S ACCOUNT OF ITS OWN GATE FAILURE WAS WRONG, AND IT CAUGHT "
        "THAT BY REGISTERING THE ACCOUNT AS A GATE.** Run 1 failed a pre-registered "
        "bar (low-`D` mean **2.92%** against **< 2%**). Rather than switching to "
        "medians -- which would have produced the desired answer with no evidence "
        "the reason was right -- M111 wrote its explanation down as gate **(c)** "
        "(*'the tail is heavy, so the lowest bin's mean will still exceed 2%'*), "
        "committed it, and ran: **(a) PASS, (b) PASS, (c) FAIL**. At n=58 the "
        "lowest bin's mean is **1.89%**, under the bar. The tail is real (mean "
        "exceeds median in all seven bins, **64.52% vs 8.04%** in the top) but was "
        "**not** the cause. The real fault was the gate's own **bin boundary**: it "
        "averaged `D` < 1.5, and by `D` = 1.5 the arms already differ by half and "
        "the shift has reached **3.40%**.",
    ),
    (
        1720,
        "MEASURED",
        "M111",
        "**M111 IS NOT PIL-EXPOSED, CHECKED AT BOTH ENDS.** **Zero `Image.open(` "
        "call sites** across 33 files; every TIFF read is `tifffile.imread`; PIL "
        "appears only as `Image.fromarray`/`Image.new` on the PNG write path. It "
        "also checked **consumption**, which no other milestone did: the three "
        "`ORCH-drift-check` scripts that produced its inputs are clean, and its "
        "control file measures **49 028 distinct levels**, so the baseline is "
        "genuinely 16-bit at source. **A grep for `PIL` false-positives on "
        "'com*pil*ing'** -- count `Image.open(` call sites and then check what "
        "happens to the return value.",
    ),
]

NEW_DISCIPLINES = [
    (
        874,
        "**Ask about the ratio of the *terms*, not the form of the expression.** "
        "'It is a ratio, so quantisation cancels' is true only when the two terms "
        "are comparable: measured shift rises monotonically from **0.68%** at "
        "`D` < 1.25 to **8.04%** at `D` >= 8. Report `D` = max/min of the terms "
        "alongside any cancellation claim. **A defect-detection contrast is a "
        "strong term over a weak one by construction**, so it is never in the "
        "protected regime, however it is written.",
    ),
    (
        875,
        "**When a pre-registered gate fails, register your explanation of the "
        "failure as the next gate before acting on it.** M111's account of why run "
        "1 failed was itself wrong -- the heavy tail was real but innocent, and the "
        "true cause was the gate's own bin boundary. Switching statistic at that "
        "point would have produced the right answer for a reason that was false, "
        "and nothing would have caught it. **A failed gate tells you *that* it "
        "failed, not *why*, and the why is what you carry into the next design.**",
    ),
    (
        876,
        "**Check exposure at both ends: what your scripts read, and what produced "
        "the files they read.** M111 is the only milestone that audited its "
        "*inputs'* provenance rather than only its own call sites, and confirmed "
        "the baseline independently by counting levels in the control file "
        "(**49 028**). A clean reader on a file that was already narrowed upstream "
        "is still a narrowed measurement.",
    ),
]

log = []
for number, status, source, text in NEW_FACTS:
    row = "| %d | %s | %s | %s |" % (number, status, source, text)
    assert row.count("|") == 5, "fact %d: pipe count %d" % (number, row.count("|"))
    assert _re.sub(r"`[^`]*`", "", row).count("**") % 2 == 0, "fact %d: bold" % number
    log.append((number, row))

dlog = []
for number, text in NEW_DISCIPLINES:
    entry = "%d. %s" % (number, text)
    assert _re.sub(r"`[^`]*`", "", entry).count("**") % 2 == 0, "disc %d: bold" % number
    dlog.append((number, entry))

prev = 1715
for number, row in log:
    insert_after_fact_row(prev, [row])
    prev = number
    print("fact %d" % number)

dprev = 873
for number, entry in dlog:
    insert_after_entry(dprev, r"^## 5\. ", [entry])
    dprev = number
    print("discipline %d" % number)

out = "\n".join(lines)
for number, _ in log:
    assert len([l for l in lines if l.startswith("| %d |" % number)]) == 1, number
for number, _ in dlog:
    assert out.count("\n%d. " % number) == 1, number

with io.open(PATH, "w", encoding="utf-8") as fh:
    fh.write(out)
print("wrote %s" % PATH)
