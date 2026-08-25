"""Fold V-CA: the CA correction is real, ORCH's headline was the largest of five.

Facts 1662-1665, disciplines 847-848.
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
        1662,
        "MEASURED",
        "V-CA",
        "**ORCH'S `61.0 %` CA HEADLINE IS REAL, MEASURED ON A CLEAN ARM, AND "
        "MIS-DESCRIBED.** Unlike the halo failure of fact 1596, the figure comes from a "
        "**full-frame, aligned, default-gate, default-resampler, full-stack** render -- the "
        "audit checked the argv, and that part is clean. But it is **not a chroma "
        "reduction**: it is the fall in edge-localised chroma **excess**, a derived "
        "contrast against a baseline five pixels away. The same correction on the same file "
        "gives raw edge chroma **-29.4 %**, near-edge **-20.5 %**, and whole-frame "
        "**-4.9 %**. **ORCH quoted the largest of five available numbers for one effect, "
        "without the qualifier that makes it mean what it means.**",
    ),
    (
        1663,
        "MEASURED",
        "V-CA",
        "**NO AUTHOR ANYWHERE RECOMMENDS ENABLING `STREHL_FIX_CA` BY DEFAULT; TWO "
        "RECOMMEND AGAINST, AND SO DOES THE CODE.** A whitespace-collapsed sentence scan of "
        "all `docs/**/*.md` (`v4_absence_check.py`) found the recommendation has **no "
        "source** -- it originated with ORCH. Against it: a fit on **20 ROIs** where its "
        "own author says a shipped correction needs 100; a coefficient that differs "
        "**23.6 %** between two scenes through the same glass; an out-of-sample transfer "
        "that **split 0.950 / 0.541** against a 0.60 bar; over-correction that **flips the "
        "residual's sign** on both stacks checked; and movement of **blue**, a channel it "
        "declares it does not touch, by >4 display levels on up to **2.26 %** of pixels by "
        "an unidentified mechanism.",
    ),
    (
        1664,
        "ARGUED",
        "V-CA",
        "**THE CORRECTION IS NEVERTHELESS BETTER, AND THE BY-EYE CLAIM SURVIVED AUDIT.** "
        "The 5x-crop judgement was ruled a real observation rather than an ORCH paraphrase, "
        "independently reproduced. The audit's own recommendation is therefore **keep the "
        "default OFF and recommend the flag scoped to the owner's own optical path** -- "
        "`STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl`, which is **case-sensitive**, with `1` / "
        "`true` / `on` **deliberately rejected** so the software never guesses a lens, and "
        "a typo raised as an error rather than a silent no-op. Three standing caveats: "
        "fringes get **fainter, not thinner**; the residual is **red-biased**; and it has "
        "**never been compared against anything but an arm that does no resampling at "
        "all**.",
    ),
    (
        1665,
        "MEASURED",
        "V-CA",
        "**THE PROJECT'S HEADLINE CA NUMBER HAS NEVER BEEN MEASURED IN THE SPACE THE "
        "PROJECT SAYS TO MEASURE IN.** The `61.0 %` was taken in `--srgb`, whose own "
        "`--help` reads *For looking at, NOT for measuring*, and which M113 measured as "
        "**cross-channel contaminated** (chain transfer 1.3073 against 0.9399 / 0.9813 "
        "binned-linear). The `lin-*.tif` renders already exist, so the re-measurement is "
        "cheap. Ranked second of five things that would change the verdict, behind running "
        "the **`anti` arm** (negative-strength vs on), which needs only a strength knob in "
        "`optics.rs` and **one render**.",
    ),
]

NEW_DISCS = [
    (
        847,
        "**When one effect admits several numbers, the honest headline is the one whose "
        "qualifier fits in the sentence -- and quoting the largest without it is a "
        "misdescription even when every number is correctly measured.** ORCH's CA headline "
        "was the largest of five (fact 1662); ORCH's halo headline was likewise the most "
        "flattering member of a family (fact 1596). **Twice in one night, and both times an "
        "auditing agent caught it rather than the author.** The rule: **state the "
        "denominator in the same breath as the number**, or quote the plainest member of "
        "the family. `-29.4 % of edge chroma` needs no qualifier; `-61.0 % of "
        "edge-localised chroma excess against a 5 px baseline` cannot survive without one, "
        "and will be repeated without it.",
    ),
    (
        848,
        "**A recommendation with no author is a recommendation nobody checked -- scan for "
        "its source before shipping it.** V-CA's `v4_absence_check.py` did a "
        "whitespace-collapsed sentence scan of every document in the corpus and found that "
        "**not one author recommended enabling the CA correction by default; two "
        "recommended against, and so did the code and ORCH's own fact 1593** (fact 1663). "
        "The recommendation had accreted in the orchestrator's summarising rather than "
        "arriving from any measurement. **The check is mechanical and should precede any "
        "default change**: grep the corpus for a sentence that actually recommends the "
        "thing, and if the only source is the summary, there is no source.",
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

s1 = insert_after_fact_row(1661, fact_block)
s2 = insert_after_entry(846, r"^## 5\. ", disc_block)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))

print("facts %s -> %s" % (", ".join(str(f[0]) for f in NEW_FACTS), s1))
print("disciplines %s -> %s" % (", ".join(str(d[0]) for d in NEW_DISCS), s2))
