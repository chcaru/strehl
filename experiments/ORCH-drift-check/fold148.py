"""Fold M123: the outlier mask fails on real captures; ORCH broke rule 40.

Facts 1666-1669, disciplines 850-851.
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


NEW_FACTS = [
    (
        1666,
        "MEASURED",
        "M123",
        "**THE OUTLIER MASK IS BACKWARDS ON REAL CAPTURES: IT FIRES 4.3x LESS ON THE "
        "MOVING SUBJECT THAN ON A STATIONARY ONE.** At the shipped configuration it fires "
        "on **29.55 %** of a *stationary* subject (pre-registered bar: <= 1.0 %, fail "
        "> 5 %). It separates motion from defocus by **2.12x** where the underlying "
        "displacement separates by **0.96x** -- which is to say not at all -- against a "
        "pre-registered bar of 10x. And it does not respond to a **planted** displacement "
        "anywhere below **1.0 px**, firing 24.51 % at d=0 and staying flat to d=0.5. "
        "**Four of six pre-registered criteria FAIL. Verdict: do not ship the mask and do "
        "not wire it**; phase 2 was conditional on phase 1 and was never reached.",
    ),
    (
        1667,
        "MEASURED",
        "M123",
        "**WHAT LOOKS LIKE MOTION DISCRIMINATION IS SUBSTANTIALLY TEXTURE "
        "DISCRIMINATION** -- the second milestone to reach that finding independently, "
        "after M60 wrote that *a mask keyed on chi2 would be a sharpness detector wearing "
        "a robustness label*. **This is the FOURTH milestone to decline to ship this "
        "mask** (M28, M60, M89, now M123; M97r's §6 carried the same caveat). Dependency-"
        "ordered preconditions before it is worth revisiting: fix `N_eff` first, because "
        "the null's **spread** is `0.1247` against a predicted `sqrt(2/N) = 0.0442` -- "
        "**2.82x**, so every threshold in the module is measured against a bar 2.8x "
        "tighter than believed; re-measure the defocus pedestal on **real** scenes "
        "(0.73-0.95 px where the bar assumes 0.35 px); and do not use Lucas-Kanade, whose "
        "small-displacement linearisation **abstains exactly where it is needed**.",
    ),
    (
        1668,
        "MEASURED",
        "M123",
        "**THE DISCRIMINATING QUESTION ORCH COMMISSIONED WAS ALREADY CLOSED IN THE TREE, "
        "WITH A DERIVATION OF WHY THE ANSWER MUST BE NO.** `outlier.rs` marks the `LowFreq` "
        "arm a **MEASURED FAILURE in its own enum documentation** and carries the "
        "regression test `low_pass_filtering_does_not_discriminate_defocus_it_amplifies_"
        "it`. M97r W3 derives the mechanism: box-averaging divides noise variance by `m` "
        "while an extended defocus residual survives, so the statistic is their ratio and "
        "is **independent of the filter radius** -- **no radius helps**. M123 therefore "
        "ran `LowFreq` only as an inertness control. **Also found stale in passing: "
        "`outlier.rs`'s own module header contradicts its enum forty lines below**, saying "
        "the module implements *two* discriminators where the enum documents four, and "
        "describing `LowFreq` as the arm where defocus largely cancels. **ORCH's brief "
        "inherited the header's version**, which is what a reader hits first.",
    ),
    (
        1669,
        "MEASURED",
        "M123",
        "**A NULL CAN PASS ON ITS MEAN AND FAIL ON ITS SPREAD, AND ONLY THE SPREAD IS "
        "LOAD-BEARING FOR A THRESHOLD.** The mask's null mean chi-square is **1.038**, "
        "comfortably inside the pre-registered `[0.90, 1.10]` -- a clean PASS, and the only "
        "null check that had been pre-registered as a threshold. Its **standard deviation** "
        "is `0.1247` against the module's own explicit prediction of `sqrt(2/N) = 0.0442`. "
        "**The distribution the module claims and the distribution it has differ by 2.82x "
        "in width while agreeing to 4 % in centre.** Every FPR bar downstream is therefore "
        "evaluated against a curve of the wrong shape.",
    ),
]

NEW_DISCS = [
    (
        850,
        "**BEFORE COMMISSIONING, SEARCH `docs/research/` FOR THE QUESTION AND NAME THE "
        "PRIOR REPORTS IN THE BRIEF -- ORCH BROKE THIS AND IT COST A WHOLE MILESTONE.** "
        "Rule 40 already required it. ORCH's M123 brief named **no** prior report; **four "
        "existed** (M28, M60, M89, M97r) and **three had already used real captures**. "
        "Worse, ORCH handed the agent M89's 4.78 % figure as *a measured prior to "
        "reproduce* **without saying it was M89's** -- passing along a number from the very "
        "milestone that had written *the mask, as specified, should not ship*. The agent "
        "found all four in twenty minutes and declined to re-ask the closed question. "
        "**The check is mechanical and takes minutes; skipping it spends an entire agent "
        "re-deriving a known no.** Corollary: **search the source too** -- `outlier.rs` "
        "carried a regression test whose *name* was the answer.",
    ),
    (
        851,
        "**A MODULE HEADER IS DOCUMENTATION THAT DRIFTS FROM THE CODE BENEATH IT, AND IT "
        "IS WHAT EVERY READER AND EVERY DISPATCHER HITS FIRST.** `outlier.rs`'s header "
        "describes **two** discriminators where its enum, forty lines below, documents "
        "**four** and marks one of them a measured failure (fact 1668). ORCH read the "
        "header, briefed from it, and commissioned an agent to test an arm the file itself "
        "already recorded as dead. **The nearer documentation is to the top of a file, the "
        "more load it bears and the less often it is re-read when the code changes.** When "
        "a header and an enum disagree, the enum is the code and the header is a claim "
        "about it -- and the claim is the one that was never tested.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = [fact_row(*f) for f in NEW_FACTS]
disc_block = ["%d. %s" % d for d in NEW_DISCS]

for line in fact_block:
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])
for line in fact_block + disc_block:
    stripped = _re.sub(r"`[^`]*`", "", line)
    assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in line:
        o = ord(ch)
        assert not (o < 0x20 or o == 0x7F), "control char 0x%02X in %s" % (o, line[:60])

s1 = insert_after_fact_row(1665, fact_block)
s2 = insert_after_entry(849, r"^## 5\. ", disc_block)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))

print("facts %s -> %s" % (", ".join(str(f[0]) for f in NEW_FACTS), s1))
print("disciplines %s -> %s" % (", ".join(str(d[0]) for d in NEW_DISCS), s2))
