"""Fold the blur control: it disqualifies the arm with the best headline number.

Facts 1641-1643, disciplines 836-837.
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
    """Facts live in a markdown TABLE, so anchor on the unique `| N |` row."""
    hits = [i for i, l in enumerate(lines) if l.startswith("| %d |" % number)]
    assert len(hits) == 1, "fact row %d appears %d times" % (number, len(hits))
    for k, text in enumerate(block):
        lines.insert(hits[0] + 1 + k, text)
    return "fact table"


def insert_after_entry(number, section_pattern, block):
    """Insert AFTER the whole wrapped entry `number.` inside one section only.

    Both defects of fold138/fold139 are excluded by construction here: the
    search is confined to a section, and it walks past indented continuation
    lines instead of stopping at the entry's first physical line.
    """
    start, end = section_bounds(section_pattern)
    hits = [i for i in range(start, end) if lines[i].startswith("%d. " % number)]
    assert len(hits) == 1, "entry %d appears %d times in %s" % (number, len(hits), lines[start].strip())
    j = hits[0] + 1
    while j < end and lines[j].strip() and not _re.match(r"^\d+\. ", lines[j]):
        j += 1
    for k, text in enumerate(block):
        lines.insert(j + k, text)
    return lines[start].strip()


NEW_FACTS = [
    (
        1641,
        "MEASURED",
        "ORCH",
        "**THE SOFT GATE BEATS `--photometric` ON THE TONAL STATISTIC AND IS DISQUALIFIED "
        "BY THE BLUR CONTROL.** Scoring M116's remaining arms with the fact-1637 "
        "instrument -- laplacian-RMS ratio against the default, identical windows across "
        "arms -- the soft-gate arms have the **better headline number on every subject**: "
        "`tweezers-cpl` **0.553** (gaussian), **0.562** (exponential), **0.544** "
        "(gaussian + photometric) against **0.710** for photometric alone, and "
        "`bee-3-cpl` **0.808 / 0.819 / 0.809** against **1.064**. **But on `bee-3-cpl` "
        "the gaussian soft gate cuts the TEXTURED control window by 30.5% (500.8 -> "
        "348.0), which is as large as its effect on that subject's smooth windows "
        "(0.851 / 0.673 / 0.813).** Photometric's textured windows are **1.037** (bee) "
        "and **1.027** (tweezers) -- preserved. Confirmed by eye on a shared stretch: "
        "the soft-gate panel smears the fine hairs along the leg edge and erases a "
        "highlight that the default resolves.",
    ),
    (
        1642,
        "MEASURED",
        "ORCH",
        "**WHICH MEANS THE TWO INSTRUMENTS NOW AGREE ON THE SOFT GATE AND DISAGREE ONLY "
        "ON PHOTOMETRIC -- AND THE BLUR CONTROL IS WHAT SEPARATES THE TWO CASES.** M116 "
        "rejected the soft gate on a detail statistic at **-0.01218**, and fact 1641 "
        "rejects it on a background statistic plus a control, by a different route, on "
        "different windows, with a different measure. **Two independent methods "
        "converging on the same verdict is much stronger than either alone.** The "
        "photometric disagreement (fact 1639) survives this because it is the one arm "
        "whose control window is untouched: it is the only candidate that changes smooth "
        "regions **without** changing textured ones. `A4` (photometric + gaussian soft "
        "gate) inherits the blur -- bee textured **0.711** -- so the combination is not a "
        "way to keep both.",
    ),
    (
        1643,
        "MEASURED",
        "ORCH",
        "**AND THE RANKING WOULD HAVE BEEN WRONG WITHOUT THE CONTROL.** On the defect "
        "statistic alone the correct promotion order is soft-gate-gaussian > "
        "soft-gate-exponential > photometric on both subjects that move. After the blur "
        "control it is photometric alone, and the top two are defects. **The statistic "
        "that identified the defect could not, by itself, tell a fix from a blur** -- "
        "removing structure scores identically either way, and only the region where "
        "structure is legitimate distinguishes them.",
    ),
]

NEW_DISCS = [
    (
        836,
        "**A defect statistic ranks only the candidates that already passed the control; "
        "ranking first and controlling afterwards promotes the blur.** The arm with the "
        "best number on every subject was disqualified by a window it was never supposed "
        "to change (facts 1641, 1643). The general form: **any metric that rewards "
        "removing something can be maximised by removing everything**, so it must be "
        "paired with a region where removal is forbidden, and that pairing must gate the "
        "ranking rather than annotate it.",
    ),
    (
        837,
        "**Anchor a fold on a unique full line, inside the section you mean, and walk to "
        "the end of the wrapped entry.** Two folds in one session inserted into the wrong "
        "place: `fold138` matched question 138 in an early part of the list rather than "
        "its end, and `fold139` matched **discipline** 202 in section 5 instead of "
        "**question** 202 in section 10 -- then split that discipline's bold span, "
        "because section-5 entries wrap onto indented continuation lines and the anchor "
        "was only the first of them. Both were caught by `corpus_lint`, which is the "
        "reason to run it after every fold rather than after a batch. `fold140` carries "
        "`insert_after_entry(number, section_pattern, block)`, which confines the search "
        "to one section and walks past continuations; use it.",
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

s1 = insert_after_fact_row(1640, fact_block)
s2 = insert_after_entry(835, r"^## 5\. ", disc_block)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))

print("facts %s -> %s" % (", ".join(str(f[0]) for f in NEW_FACTS), s1))
print("disciplines %s -> %s" % (", ".join(str(d[0]) for d in NEW_DISCS), s2))
