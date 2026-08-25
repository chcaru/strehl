"""Fold M121-halo-polarity, and repair ORCH's own wrong citations.

Facts 1703-1709, disciplines 867-870.
Amends fact 1621 and discipline 830 (merge.rs:3027 -> 3341, merge.rs:298 -> 299).

The irony is worth stating in the text: discipline 830 is about looking up what
a thing IS before building on it, and it cited the wrong line while saying so.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()

# ---------------------------------------------------------------- amendments
# Verified directly against crates/strehl-core/src/merge.rs this session:
#   93   pub const REGULARISER_RADIUS: usize = 8;
#   299  pub const DEFAULT_GATE: f32 = 4.0;
#   3341 // (c) The negative control, in the same test (rule 39). Gate 0 is the
#   3346 "gate 0 admitted {n0:.6} frames per pixel; it must admit exactly the winner"
AMENDMENTS = [
    ("`merge.rs:3027` labels it in so many words", "`merge.rs:3341` labels it in so many words"),
    ("(`merge.rs:298`), which is the `armM4-gate4-binlin.tif` arm", "(`merge.rs:299`), which is the `armM4-gate4-binlin.tif` arm"),
    ("`merge.rs:3027` calls gate 0 a **negative control**", "`merge.rs:3341` calls gate 0 a **negative control**"),
    ("and `merge.rs:298` sets the shipped default to 4.0 (fact 1621)", "and `merge.rs:299` sets the shipped default to 4.0 (fact 1621)"),
]
for stale, fresh in AMENDMENTS:
    assert raw.count(stale) == 1, "amendment anchor %r appears %d times" % (stale, raw.count(stale))
    raw = raw.replace(stale, fresh)

TAIL = (
    " **ORCH's citation in this entry was itself wrong** -- it read line **3027** "
    "for the negative control and line **298** for the default gate; the lines are "
    "**3341** and **299**, corrected by M121 and re-verified against the source. An "
    "entry about looking a thing up before building on it cited the wrong line "
    "while saying so; the *claim*, checked again, holds."
)
anchor = "Make identifying the arm part of loading it, not part of writing it up."
assert raw.count(anchor) == 1, "discipline 830 anchor not unique"
raw = raw.replace(anchor, anchor + TAIL)

lines = raw.split("\n")


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
        1703,
        "MEASURED",
        "M121",
        "**THE HALO CARRIES THE FOCUS WINDOW'S LENGTH SCALE, MEASURED THREE "
        "INDEPENDENT WAYS.** Rim half-width **w50 = 10.00 px**, rim cutoff **13.25 "
        "px**, and election-agreement **w50 = 10.50 px** (10% at 21.10 px), against "
        "`WINDOW_RADIUS = 13` (`focus.rs:83`). The radius is **fixed, not "
        "adaptive** -- all 30 references are constant expressions -- and "
        "`FINE_WINDOW_RADIUS = 2` feeds statistics, not selection. **Nothing else "
        "in the pipeline has this length scale**: not the defocus blur, not object "
        "size, not the focus step. The rim *ends* by 12 px (`+0.2735 / +0.1911 / "
        "-0.0036 / -0.0431 / -0.0240` across 0-24 px), which is what a bounded "
        "window predicts and a gradient does not.",
    ),
    (
        1704,
        "MEASURED",
        "M121",
        "**THE HALO IS IDENTICAL AT GATE 0 AND GATE 4, WHICH IS WHAT A SELECTION "
        "ARTIFACT AND ONLY A SELECTION ARTIFACT SHOULD DO.** `merge.rs:3341` "
        "establishes that gate 0 admits **exactly the winner** -- it is the pure "
        "winner-take-all limit, not merely a low setting. Rim in the surround: "
        "dark-object class **+0.0634** (gate 4, n=70, 93% positive) vs **+0.0658** "
        "(gate 0, n=45, 96% positive). **The estimator and the pure selector "
        "produce the same halo**, so the defect is in *which frame is elected*, not "
        "in how the elected frames are blended. Independently reproduces fact 1625.",
    ),
    (
        1705,
        "REFUTED",
        "M121",
        "**ORCH'S PROPOSED CONTRAST MECHANISM FOR THE HALO IS REJECTED "
        "OUT-OF-SAMPLE.** Fitting the dark-object class and predicting the "
        "bright-object class (`e2b_law.py`): **CONTRAST (ORCH) REJECTED**, "
        "**ADDITIVE REJECTED**, and a **MULTIPLICATIVE** law -- surround x (1+g), "
        "g ~ **+2.3%** -- is the only one reproducing both rows. The in-sample "
        "discriminator meant to separate them is **underpowered and reported as an "
        "honest null** (CVs 0.811 / 0.948 / 1.270, fully overlapping CIs, all "
        "R^2 ~ 0). **P-WIDTH alone does not identify the mechanism** -- any "
        "window-based process leaves a window-sized mark -- so the discriminating "
        "test is still outstanding.",
    ),
    (
        1706,
        "MEASURED",
        "M121",
        "**THE MILESTONE REJECTED ITS OWN MOST EXCITING RESULT, CORRECTLY.** A "
        "second subject (`tweezers-cpl`, bright metal on dark ground) rendered to "
        "supply the class the bee could not, and read **+0.1326, n=96, 100% "
        "positive** -- apparently the killer prediction firing. It was then killed "
        "by its own shape test: the tweezers profile is **still +0.0884 at 18-24 "
        "px and never ends**, and **a single unmerged frame reproduces its shape at "
        "one third amplitude** (separation **2.8x**, against **28x** on "
        "`bee-3-cpl`). It is a background gradient. **A rim that does not end is "
        "not a rim.**",
    ),
    (
        1707,
        "MEASURED",
        "M121",
        "**A SELF-ADDED CONTROL CAUGHT A DEFECT THAT WOULD HAVE INVERTED PART OF "
        "THE RESULT.** N4 found **113 of 334** forced profiles accepted in "
        "featureless background reading **-0.30**: with no step, the normaliser `A` "
        "is noise and everything divides by it. Fixed with `MIN_AMPLITUDE = 2000 "
        "DN`, chosen from a 2.7x separation (real edges >= 2879 DN, flat ROI <= "
        "1052) **before any verdict was read**, applied uniformly to the headline, "
        "every control and the plants; N4 then reads 0/334. **The contaminating "
        "bias was negative while the headline is positive**, so it could not have "
        "manufactured the result -- which is the check that makes the repair "
        "credible rather than merely applied.",
    ),
    (
        1708,
        "MEASURED",
        "M121",
        "**QUANTISATION DAMAGES A NORMALISED STATISTIC THROUGH RE-DETECTION, NOT "
        "THROUGH THE PIXEL VALUE.** M121 re-ran its headline on a deliberately "
        "narrowed arm (commissioned first: the candidate narrowing was required to "
        "be **byte-identical to PIL over all 786 432 samples**). Both verdicts "
        "survive (headline **+0.0634 -> +0.0619, -2.4%**; the null stays inside its "
        "CI). But the same class measured twice shifts **+0.4% with the read band "
        "pinned** and **-31% under free re-detection**. The prediction from "
        "occupied range was **wrong** -- the worst-hit class has the *highest* "
        "median amplitude (10 260 DN). **Where you measure is decided from the "
        "pixels too.**",
    ),
    (
        1709,
        "MEASURED",
        "M121",
        "**A THIRD INSTANCE OF THE SILENT-NARROWING CLASS, AND THIS ONE CHANGES "
        "FRAME IDENTITIES.** M96's `elected-index.tif` is **uint8 RGB -- a "
        "colour-mapped preview, not raw indices**; anything that read frame numbers "
        "from it read a palette. Distinctly worse than quantisation: `bee-3-cpl` "
        "has **299 frames**, so a uint8 index map **wraps at 256** and every frame "
        "from 256 up silently becomes a different frame. M121's own index readers "
        "assert `uint16`. Separately, **`through_focus.rs:1145` already computes "
        "`SOBEL_RADIUS + 1 + WINDOW_RADIUS + REGULARISER_RADIUS`** as *'the widest "
        "any of them needs'* -- the codebase's own tests already depended on the "
        "22 px spill radius M121 derived.",
    ),
]

NEW_DISCIPLINES = [
    (
        867,
        "**Before reading a null, count how many members of the class could have "
        "expressed the effect.** M121's bright-object row read a flat +0.0009 and "
        "superficially refuted its own prediction; only **5 of those 18 edges "
        "straddle a depth discontinuity**, and under *every* mechanism on the table "
        "a same-depth edge shows nothing. **A class that cannot express the "
        "prediction is not evidence against it, it is a sample that cannot address "
        "it** -- and it will look exactly like a refutation.",
    ),
    (
        868,
        "**Require a claimed localised feature to END.** M121's most exciting "
        "reading (+0.1326, n=96, 100% positive) died because its profile was still "
        "+0.0884 at 18-24 px, while the genuine rim went negative by 12 px. A "
        "gradient, a vignette and a lighting falloff all produce large, "
        "consistently-signed, high-n readings near an edge. **The discriminator is "
        "not amplitude or significance, it is spatial support** -- measure the "
        "profile out to several times the expected width and require it to return "
        "to zero.",
    ),
    (
        869,
        "**Third triage question for a narrowed reader, after 'is my statistic "
        "absolute' and 'does it divide small by large': is anything about WHERE I "
        "measure decided from the narrowed pixels?** M121 measured the same class "
        "twice through the same defect: **+0.4% with the band pinned, -31% under "
        "free re-detection**. A milestone that scored at fixed coordinates is far "
        "less exposed than one that found its own features, *with an identical "
        "statistic*. Amplitude did not predict which classes moved; re-detection "
        "did.",
    ),
    (
        870,
        "**Index maps are pixels, and their failure mode is worse than "
        "quantisation.** A narrowed intensity image gives you a wrong *value*; a "
        "narrowed index map gives you the **wrong frame** -- `bee-3-cpl`'s 299 "
        "frames wrap silently in uint8. Assert `uint16` on index maps, and read "
        "them **nearest-neighbour only**: interpolating an index map invents frames "
        "nobody elected.",
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

prev = 1702
for number, row in log:
    insert_after_fact_row(prev, [row])
    prev = number
    print("fact %d" % number)

dprev = 866
for number, entry in dlog:
    insert_after_entry(dprev, r"^## 5\. ", [entry])
    dprev = number
    print("discipline %d" % number)

out = "\n".join(lines)
assert "merge.rs:3027" not in out, "stale citation survived"
assert "`merge.rs:298`" not in out, "stale DEFAULT_GATE citation survived"
assert out.count("merge.rs:3341") >= 3, "corrected citation not present"
for number, _ in log:
    assert len([l for l in lines if l.startswith("| %d |" % number)]) == 1, number
for number, _ in dlog:
    assert out.count("\n%d. " % number) == 1, number

with io.open(PATH, "w", encoding="utf-8") as fh:
    fh.write(out)
print("wrote %s" % PATH)
