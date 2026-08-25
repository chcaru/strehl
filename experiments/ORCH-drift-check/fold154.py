"""Fold V-M116: the merge-beats-single-frame headline, verified and split.

Facts 1698-1702, disciplines 864-866.

The value here is not the confirmation -- the arithmetic was right -- but the
two refutations and the mechanism the verifier built to find them. The two-band
decomposition it introduces is the first statistic in this corpus that can tell
selection and estimation apart, and it does not give the same answer on every
subject.
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
        1698,
        "MEASURED",
        "V-M116",
        "**THE ARITHMETIC AND THE FRAME CHOICE BOTH SURVIVE INDEPENDENT ATTACK.** "
        "An independent reimplementation (integral-image box filter, own structure "
        "field, no shared code) reproduces M116's `+0.15207 / +0.16661 / +0.33319` "
        "**to five decimal places**, and an independent re-render of a source frame "
        "matched to **delta +0.0000000**. The 'sharpest single frame' claim was "
        "attacked the only way that settles it -- **all 100 frames of each subject "
        "were rendered through the same recipe** -- and the chosen frames rank "
        "**2/100, 1/100 and 5/100**, so the comparison is against a near-optimal "
        "single frame, not a flattering one. Gain confound **<=0.008 dex**, biasing "
        "*against* the merge on two of three subjects.",
    ),
    (
        1699,
        "REFUTED",
        "V-M116",
        "**THE HEADLINE SAID 'THE DEFAULT MERGE' AND THE ARM HAD ALIGNMENT OFF.** "
        "The merge side is `B1u` = `stack --gate 4` with **`STREHL_ALIGN=0`**, a "
        "configuration whose own log prints *'alignment : OFF -- frames are combined "
        "unregistered'*, while `stack --help` says *'It ALIGNS BY DEFAULT'*. The "
        "aligned default arm `A0` **was never compared to any single frame**. The "
        "flag is disclosed in the report's section 7 and inside the claim's body, "
        "**but not in the sentence that travels** -- which is the only place it "
        "would have had to appear to prevent the error.",
    ),
    (
        1700,
        "MEASURED",
        "V-M116",
        "**THE STATISTIC THAT PRODUCED THE HEADLINE ALSO RANKS GROSS VISIBLE "
        "PATCHWORK ABOVE THE MERGE.** With masks taken from `B0` so that neither "
        "merge chose them, `--gate 0` pure selection (`M0u`) -- the arm whose output "
        "M111 describes as gross visible patchwork -- **out-scores the gate-4 merge "
        "on `D` on all three subjects** (bee `-0.07909`, foam `-0.00557`, tweezers "
        "`-0.00404` for merge-minus-selection). **A single-band sharpness statistic "
        "cannot separate detail from retained noise**, so it cannot adjudicate "
        "selection against estimation -- which is precisely the question the project "
        "exists to answer.",
    ),
    (
        1701,
        "MEASURED",
        "V-M116",
        "**THE TWO-BAND DECOMPOSITION SPLITS THE VERDICT BY SUBJECT, AND THE SPLIT "
        "TRACKS DRIFT.** Scoring the flat band `N` and the detail band `D` "
        "separately and taking `Q = D - N`: on **`bee-3-cpl`** the merge wins "
        "decisively (`B1u` **0.61255** vs single frame **0.14585** vs gate-0 "
        "**0.19623**), because it *lowers* the flat band (1.99949 -> **1.65173**) "
        "while raising detail. On **`tweezers-cpl`** it **loses to the single "
        "frame** (`B1u` **0.37376** vs `B0` **0.84177**), because it *raises* the "
        "flat band instead (1.98049 -> **2.70200**). **`tweezers-cpl` is M122's "
        "highest-drift stack at 13.765% and `bee-3-cpl` its lowest at 1.629%** -- so "
        "this corroborates fact 1675's rho=+0.7011 from an independent statistic, "
        "though at n=2 it is corroboration and not evidence.",
    ),
    (
        1702,
        "MEASURED",
        "V-M116",
        "**THE POOLED HEADLINE HIDES A HIGHLY NON-UNIFORM EFFECT, AND THE REPORT "
        "GAVE NO DISPERSION.** Per-64x64-tile spread of the same contrast is "
        "**0.29 / 0.24 / 0.53 dex, i.e. 1.5x to 1.9x the headline value itself**. On "
        "`bee-3-cpl` the merge has more detail-band energy in **25.8% of detail "
        "tiles** -- a **minority**, against a pooled number that reads as a uniform "
        "win; on `tweezers-cpl`, **67.9%**. The *sign* is robust (**0 of 36** "
        "harness variants negative, sd 0.040/0.029/0.047 dex; mask-source worst case "
        "**-0.080 dex**) but the third digit is not, and `P1`'s 'run-to-run spread "
        "is exactly 0' measures determinism, not this dispersion.",
    ),
]

NEW_DISCIPLINES = [
    (
        864,
        "**A single-band sharpness statistic cannot adjudicate selection against "
        "estimation, because it rewards retained noise.** V-M116's `D` ranked "
        "`--gate 0` patchwork above the gate-4 merge on all three subjects. "
        "**Score the flat band and the detail band separately and report both**; "
        "`Q = D - N` reversed the ranking on one subject and confirmed it on "
        "another. Any future 'sharper' claim in this project must carry its flat-band "
        "number beside it or it is not a claim about picture quality.",
    ),
    (
        865,
        "**A non-default configuration must appear in the sentence that travels, not "
        "only in the section that explains.** M116 disclosed `STREHL_ALIGN=0` in its "
        "section 7 and in the claim body, and still shipped a headline saying 'the "
        "default merge'. **Headlines are what get folded, quoted and told to the "
        "owner** -- an accurate body does not repair an inaccurate headline, because "
        "the two travel separately. Put the flag in the noun phrase.",
    ),
    (
        866,
        "**Report the dispersion of any pooled contrast, and state what fraction of "
        "the field carries it.** V-M116 found per-tile sd of **1.5x to 1.9x the "
        "headline**, and that the bee headline was carried by **25.8% of tiles**. A "
        "pooled mean with a robust sign reads as a uniform improvement and can be a "
        "minority effect with a confident sign -- the two are indistinguishable "
        "without the spread. Both were true here, on the same number.",
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

prev = 1697
for number, row in log:
    insert_after_fact_row(prev, [row])
    prev = number
    print("fact %d" % number)

dprev = 863
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
