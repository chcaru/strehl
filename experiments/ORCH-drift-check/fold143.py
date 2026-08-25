"""Fold M115: the deconvolution headroom is ~zero. Do not build the Wiener merge.

Facts 1650-1655, disciplines 841-843. Reuses fold140's section-aware helpers.
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
        1650,
        "MEASURED",
        "M115",
        "**THE MULTI-FRAME WIENER DECONVOLUTION MERGE HAS NO HEADROOM OVER THE MERGE "
        "THAT ALREADY SHIPS. DO NOT BUILD IT.** At matched contrast, focus-axis Wiener "
        "deconvolution beats the already-shipping noise-gated average by "
        "`R_SNR = **1.0014** +/- 0.0184`, 95% CI **[0.965, 1.038]** -- an interval that "
        "contains 1 and excludes any worthwhile gain. The diffraction-free matched filter "
        "reads **0.9844** +/- 0.0182, i.e. slightly *worse*. It **looks** dramatically "
        "better -- contrast reaches **2.51x** +/- 0.63 that of the sharpest frame at "
        "f=0.205 -- but noise rises to **2.03x** +/- 0.57 in step. **It reallocates "
        "information; it does not create it.** This refutes proposal 3 of the external "
        "review (`docs/proposals/2026-08-external-review.md`), which argued deconvolution "
        "was the only path to real sharpness at this rig's magnification.",
    ),
    (
        1651,
        "MEASURED",
        "M115",
        "**AND IT RINGS.** The Wiener arms put **29.5-36.4%** of pixels outside the "
        "convex hull of the source stack -- values no input frame contains -- with a "
        "**halo peaking at 70.7%** of pixels in the 8-16 px shell around edges and a "
        "p99.9 excess of **18-26x** the hull width. **All five convex arms read exactly "
        "0.0000%.** So the failure is not a tuning artefact of one parameter choice: it "
        "is the signature of the estimator class, and it is the same artefact family as "
        "the halo that is already this project's lead defect.",
    ),
    (
        1652,
        "REFUTED",
        "M115",
        "**OTF SELF-CALIBRATION FROM THE THROUGH-FOCUS CURVE DOES NOT WORK.** The "
        "external review proposed that per-frame OTF widths could be self-calibrated from "
        "the through-focus response curve itself, so that no lens model would be "
        "load-bearing. Measured, the curve width **over-estimates `s` by 1.87x and "
        "2.15x**, and the resulting model claims an **OTF magnitude of 0.021** at a "
        "frequency where direct measurement reads **0.638** -- wrong by a factor of 30. "
        "The guard that "
        "was supposed to make the deconvolution safe without a lens database is itself "
        "unsound.",    ),
    (
        1653,
        "MEASURED",
        "M115",
        "**M115'S PRE-REGISTERED PRIMARY CHANNEL FAILED ITS OWN NULL, AND FAILED IN THE "
        "DIRECTION OF ITS HYPOTHESIS.** The antithetic-injection channel returned "
        "**SNR 84.9 on a scene-free capture**, under-estimating noise **73x**, because "
        "the election flips on **100.0%** of tiles. M115 caught it, discarded the "
        "channel, and replaced it with a split-stack channel that carries no noise model "
        "and reads consistency **1.0000**. **Had the failed channel been trusted, every "
        "number in the report would have favoured deconvolution by an order of "
        "magnitude** -- i.e. the instrument's failure mode pointed precisely at the "
        "conclusion the milestone was dispatched hoping to find.",
    ),
    (
        1654,
        "MEASURED",
        "M115",
        "**A SHARPNESS CLAIM REPORTED AS CONTRAST IS UNFALSIFIABLE; REPORTED AS SNR AT "
        "MATCHED CONTRAST IT IS NOT.** M115's gain-invariance control (C3) applied "
        "post-filters that changed measured contrast by up to **3.94x**: `R_SNR` moved "
        "**<= 0.54%**, while a naive gradient sharpness metric on the same arms was fooled "
        "by **8.25x**. The positive control (C2, exact Fourier blur) was monotone with "
        "8/8 recovery ratios in **[0.9938, 0.9974]**.",
    ),
    (
        1655,
        "MEASURED",
        "M115",
        "**THE PIL NARROWING IS WORSE THAN 241x ON LOW-CONTRAST CROPS, AND RATIO-OF-ARMS "
        "STATISTICS LARGELY SURVIVE IT.** M115 is not exposed (its only reader is "
        "`rawpy.imread`; inputs verified `uint16` at 2420 / 4906 / 7367 distinct levels), "
        "but it commissioned the check by planting the narrowing into its own loader. "
        "Three refinements to the hazard: (a) **damage scales with the file's OCCUPIED "
        "range, not the full 16-bit range** -- a detail ROI spanning ~2100 DN was left "
        "with **9 distinct levels, not 256**; (b) absolute readings are destroyed -- noise "
        "power **3.5x** too high, sigma off **1.9x**, band SNR **0.438x** of truth, and "
        "the OTF fit moved **+23.7%**; (c) **a ratio of two arms on the same data is "
        "largely protected by cancellation** -- `R_SNR(WIENER)/R_SNR(GATE)` moved only "
        "**-1.0%** (0.9340 -> 0.9248).",
    ),
]

NEW_DISCS = [
    (
        841,
        "**Report sharpness as SNR at matched contrast, never as contrast.** Any operator "
        "that multiplies high frequencies raises a contrast metric, so a contrast-shaped "
        "number cannot distinguish sharpening from information gain and cannot be "
        "falsified. Measured: a gain-invariance control moved `R_SNR` by <=0.54% while a "
        "naive gradient metric moved **8.25x** on the same arms (fact 1654). **If a "
        "candidate's headline can be manufactured by a post-filter, it is not a "
        "measurement of the candidate.**",
    ),
    (
        842,
        "**Two independent milestones hit the same failure on the same night: a scoring "
        "rule that rewards removing or adding structure, with no term forbidding it.** "
        "M115 reported its registered decision rule defective because `R_SNR` alone "
        "**rewards blur**, so a `MEAN` arm scored highest; ORCH's background statistic "
        "ranked a soft gate first for the same reason (facts 1641-1645). **This is not a "
        "coincidence of two careless authors -- it is the default shape of a "
        "single-axis quality metric**, and it is why disciplines 836 and 839 are "
        "structural requirements rather than advice. Every scoring rule in this project "
        "must name, in advance, the thing it would reward that nobody wants.",
    ),
    (
        843,
        "**Triage a narrowed reader by asking whether the statistic is a ratio of two "
        "arms on the same data or an absolute quantity.** Measured: ratio-of-arms moved "
        "**-1.0%** under a planted narrowing, while absolute noise power moved **3.5x** "
        "and band SNR fell to **0.438x** of truth (fact 1655). Combined with fact 1649's "
        "small-over-large compression, this gives a two-question triage that needs no "
        "re-run: **is it absolute (suspect), and does it divide a small quantity by a "
        "large one (suspect)?** Note also that damage scales with the **occupied** range, "
        "so a low-contrast ROI can be left with single-digit levels where the full-range "
        "figure suggests 256.",
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

s1 = insert_after_fact_row(1649, fact_block)
s2 = insert_after_entry(840, r"^## 5\. ", disc_block)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))

print("facts %s -> %s" % (", ".join(str(f[0]) for f in NEW_FACTS), s1))
print("disciplines %s -> %s" % (", ".join(str(d[0]) for d in NEW_DISCS), s2))
