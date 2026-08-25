"""Fold M113: the spectral attribution is not supported; scene-dependence is real.

Facts 1656-1661, disciplines 844-846. Reuses fold140's section-aware helpers.
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
        1656,
        "MEASURED",
        "M113",
        "**THE SPECTRAL ATTRIBUTION OF THE CA SCENE-DEPENDENCE IS NOT SUPPORTED, AND ITS "
        "ONE FALSIFIABLE PREDICTION CAME OUT BACKWARDS.** The hypothesis required that "
        "scenes weighted toward longer wavelengths in red need a *larger* red correction, "
        "monotonically. Pre-registered bar S6 required **positive** rho; across n=8 of the "
        "owner's stacks the measured Spearman rho is **-0.6905**, p=0.058 -- the wrong "
        "sign. It is not noise-limited: R/G spans **10.7%** while `needed` spans "
        "**27.3%**. M113 registered the bar as weak in advance and therefore reports NOT "
        "SUPPORTED rather than REFUTED, honouring its own pre-registration.",
    ),
    (
        1657,
        "MEASURED",
        "M113",
        "**BUT THE SCENE-DEPENDENCE ITSELF IS CONFIRMED AND LARGER THAN FIRST THOUGHT.** "
        "`needed` runs **529.9 -> 674.7 ppm**, a spread of **27.3%** across eight stacks, "
        "against a measured replicate floor of **19.5 ppm** -- an effect roughly fourteen "
        "times the repeatability. All eight passed the fact-1569 chain-transfer "
        "instrument check at **0.9064-1.0004**. **So the correction genuinely differs "
        "between subjects and the mechanism is unidentified**; `scene-dependent` is "
        "established, `spectral` is not.",
    ),
    (
        1658,
        "REFUTED",
        "M113",
        "**FOUR RIVAL EXPLANATIONS DIED ON EXISTING DATA, AND TWO OF THEM DIED ON EXIF "
        "ALONE.** Aperture and the teleconverter: **every `-cpl` stack in the corpus is "
        "f/5.6 on `FE 100mm F2.8 GM + 2X TC`**, so **there is no aperture contrast "
        "anywhere in the library** and an aperture ladder would vary a held-fixed "
        "variable. Magnification and focus distance: `bee-1-cpl` reads 536.2 ppm, "
        "**3.5 ppm** from the bee mean but **118.7 ppm** from `couch` at an identical "
        "focus distance. Subject radial structure: refuted to **+/-15 ppm**. A common "
        "scale error: refuted, CV of B/R **14.9%** against 24.7%.",
    ),
    (
        1659,
        "MEASURED",
        "M113",
        "**THE ALIGNMENT RIVAL WAS REFUTED ONLY AFTER M113 CORRECTED ITS OWN FIRST "
        "ANSWER, AND THE CORRECTION IS THE TRANSFERABLE PART.** Its S5 test initially "
        "read a **64% pipeline contribution**, which would have moved most of the effect "
        "out of optics. **That was the test failing, not the pipeline:** defocused windows "
        "dilute the global fit. Re-run on `flat-on-ruler-cpl` -- flat, so the confound is "
        "**absent by construction** rather than corrected for -- the merge and a single "
        "un-aligned frame agree to **4.8 ppm**. Restricting the bee frame to its sharp "
        "quartile moves the reading **192.0 -> 623.5 ppm**, confirming the dilution "
        "mechanism directly.",
    ),
    (
        1660,
        "MEASURED",
        "M113",
        "**`STREHL_FIX_CA` IS A SILENT NO-OP WHEN `STREHL_ALIGN=0`.** The arms come out "
        "**byte-identical with no warning of any kind**. Anyone A/B-ing the CA correction "
        "with registration disabled -- which is the natural way to isolate an optical "
        "correction from a geometric one -- would measure exactly nothing and correctly "
        "conclude the flag does nothing. This is a live trap for the CA audit and for any "
        "future measurement of that switch.",
    ),
    (
        1661,
        "MEASURED",
        "M113",
        "**ORCH'S PIL TRIAGE LIST CONTAINED A FALSE POSITIVE ON A SHARED READER AND WAS "
        "INCOMPLETE IN ORCH'S OWN DIRECTORY.** `ca_radial.py`'s `load_tiff_u16` calls "
        "`Image.open` **for the tags only** and reads pixels via "
        "`np.memmap(dtype='<u2')`, asserting 16-bit and **validating strip contiguity** "
        "rather than assuming a flat layout; it is byte-identical to `tifffile` on five "
        "files and is imported by several milestones. Five further scripts in "
        "`experiments/ORCH-drift-check/` **were** affected and unlisted, of which "
        "**`patchwork_16bit.py` is the worst case in the project**: a script named for "
        "16-bit handling that reads pixels through PIL and then derives full scale as "
        "`np.iinfo(a.dtype).max`, giving **255 instead of 65535** on top of already "
        "quantised data. Separately, fact 1374's `nearest > catmull-rom` hair-resolution "
        "result was re-run under both readers and is **reader-independent**.",
    ),
]

NEW_DISCS = [
    (
        844,
        "**A new instrument must pass a replicate control before any of its readings are "
        "admitted -- run the replicate before the bar, not after.** M113 withdrew its own "
        "post-hoc bar S8 because the instrument's bee-triplet repeatability is **116 "
        "ppm** against a **145 ppm** effect, so its clean `spread survives` verdict was "
        "inside its own noise. It had run the bar first and the replicate second. **The "
        "order is not cosmetic: a bar run before a replicate cannot be interpreted even "
        "if it passes**, and the temptation to keep the result is strongest exactly then.",
    ),
    (
        845,
        "**When a pipeline test fails, suspect the test, and look for a subject where the "
        "confound is absent by construction rather than corrected for.** M113's first "
        "alignment answer -- 64% of the effect attributable to the pipeline -- was an "
        "artefact of defocused windows diluting a global fit. It was not fixed by a better "
        "estimator but by choosing a **flat** subject, on which the merge is a measured "
        "**4.8 ppm no-op** (fact 1659). **A confound removed by the choice of subject "
        "needs no model and cannot be mis-specified**; a confound removed by a correction "
        "term is only as good as the term.",
    ),
    (
        846,
        "**A triage list distributed to a fleet needs its own negative control, because a "
        "false positive costs more than a miss.** ORCH generated the PIL exposure list "
        "with a grep and broadcast it without reading a single entry. A missed leaf script "
        "leaves one number wrong; **a false positive on a *shared* reader invites several "
        "agents to replace working, validated code and to re-run correct work** (fact "
        "1661). The specific error was greping for the API call rather than for what "
        "happens to its return value: `Image.open` for TIFF **tags** is safe, "
        "`np.asarray(Image.open(p))` on the **pixels** is not. Commission the list "
        "before broadcasting it.",
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

s1 = insert_after_fact_row(1655, fact_block)
s2 = insert_after_entry(843, r"^## 5\. ", disc_block)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))

print("facts %s -> %s" % (", ".join(str(f[0]) for f in NEW_FACTS), s1))
print("disciplines %s -> %s" % (", ".join(str(d[0]) for d in NEW_DISCS), s2))
