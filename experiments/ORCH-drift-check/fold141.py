"""Fold the gated two-axis instrument: the control now has a veto, and it works.

Facts 1644-1646, disciplines 838-839. Reuses fold140's section-aware helpers.
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
        1644,
        "MEASURED",
        "ORCH",
        "**THE BLUR CONTROL IS NOW STRUCTURAL, AND IT REPRODUCES THE HAND VERDICT ON ITS "
        "OWN.** `experiments/ORCH-drift-check/switch_gate.py` scores a candidate on two "
        "axes in one pass -- **removal** on the 8 smoothest windows and **preservation** "
        "on the 8 most textured -- both pools drawn from the symmetric mean of the two "
        "arms, and returns PASS only when `removal <= 0.97` **and** `preservation >= "
        "0.97`, so the control holds a veto rather than a footnote. On M116's arms it "
        "recovers facts 1641-1643 with no human in the loop: `A1` (`--photometric`) shows "
        "**no harm on any subject** -- bee `1.0583 / 1.0324`, foam `1.0111 / 1.0080`, "
        "tweezers `0.8264 / 1.0208` PASS -- while `A2`, `A3` and `A4` are all REJECTED on "
        "`bee-3-cpl` at preservation **0.6703 / 0.6345 / 0.6839**.",
    ),
    (
        1645,
        "MEASURED",
        "ORCH",
        "**AND THE HARM IS VISIBLE ON EXACTLY ONE OF THE THREE SUBJECTS.** On "
        "`tweezers-cpl` alone every soft-gate variant **passes its own texture control** "
        "-- preservation **0.9918 / 0.9911 / 1.0141** -- while posting the **best removal "
        "scores in the entire candidate set**, **0.5493 / 0.5622 / 0.5299** against "
        "`0.8264` for photometric. On `foam` every arm reads ~`0.99`-`1.01` on both axes, "
        "i.e. nothing. **Only `bee-3-cpl` exposes the blur at all.** So a campaign run on "
        "tweezers -- the subject that carries the photometric win, and therefore the "
        "natural one to test on -- would have ranked the soft gate first, cleared it on "
        "its control, and promoted a blur. Taking a median across the three subjects does "
        "the same thing, because two of them are silent.",
    ),
    (
        1646,
        "MEASURED",
        "ORCH",
        "**THE INSTRUMENT IS COMMISSIONED BY REJECTING A BLUR, NOT BY DETECTING AN "
        "EFFECT.** `switch_gate.py` refuses to print a verdict on a subject until it has "
        "scored `PLANT-BLUR` -- the base arm passed through an `r=2` box blur and fed in "
        "as though it were a candidate -- and rejected it. It reads removal **0.1130 / "
        "0.2873 / 0.1831** and preservation **0.1908 / 0.2678 / 0.2319** on "
        "bee / foam / tweezers and is REJECTED on all three. The null (`A0` against "
        "itself) reads exactly **1.0000** on both axes on all three subjects, and the "
        "voronoi plant clears its `>1.30` / `<0.77` bars on all three. **A plant that "
        "shows an instrument is sensitive says nothing about whether it is specific**; "
        "this is the control for specificity and it is the one the earlier instrument "
        "lacked.",
    ),
]

NEW_DISCS = [
    (
        838,
        "**Take the worst subject, not the median: a candidate that blurs anywhere is not "
        "rescued by scoring well elsewhere.** All three soft-gate variants pass their "
        "texture control on `tweezers-cpl` and post the best removal numbers measured, "
        "and all three are blurs -- only `bee-3-cpl` shows it, and `foam` is silent "
        "(fact 1645). Discipline 835 said aggregate last; this is the sharper form. "
        "**A subject on which a defect does not appear is not evidence that the defect is "
        "absent, and averaging it in actively conceals the one subject that saw it.** "
        "`switch_gate.py` therefore reports OVERALL REJECT when any single subject "
        "rejects, and never reports a cross-subject mean of the two axes.",
    ),
    (
        839,
        "**Commission a ranking instrument by making it reject a known-BAD candidate, not "
        "merely detect a known-good effect.** Every plant used here until now proved "
        "sensitivity -- can the statistic see the thing we hope it sees. None proved "
        "specificity -- can it decline the thing we hope it declines. The gap is exactly "
        "where tonight's near-miss lived: the old instrument's controls all passed, and "
        "it still ranked a blur first. **Feed the instrument a candidate that is nothing "
        "but the failure mode, and require it to be rejected before any real verdict is "
        "printed** (fact 1646). An instrument that has never rejected anything is not "
        "known to be able to.",
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

s1 = insert_after_fact_row(1643, fact_block)
s2 = insert_after_entry(837, r"^## 5\. ", disc_block)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))

print("facts %s -> %s" % (", ".join(str(f[0]) for f in NEW_FACTS), s1))
print("disciplines %s -> %s" % (", ".join(str(d[0]) for d in NEW_DISCS), s2))
