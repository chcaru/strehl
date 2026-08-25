"""Fold the photometric A/B: the first measured, visible removal of the mosaic.

Facts 1637-1640, disciplines 834-835. Marks fact 1636 CONFIRMED.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1636 |")
disc_line = full_line(raw, "833. ")
q_line = full_line(raw, "202. ")

NEW_FACTS = [
    (
        1637,
        "MEASURED",
        "ORCH",
        "**`--photometric` REMOVES FINE STRUCTURE FROM SMOOTH BACKGROUND ON ONE OF THREE "
        "SUBJECTS AND IS INERT ON THE OTHER TWO.** Scored M116's own A0 (default) and A1 "
        "(`--photometric`) arms -- same frozen warp map, so registration is held constant "
        "-- on 12 windows per subject chosen from the **symmetric mean of the two arms**, "
        "so neither arm picks the pixels it is judged on "
        "(`experiments/ORCH-drift-check/photometric_ab.py`). Laplacian-RMS ratio, test "
        "over base: **`tweezers-cpl` median 0.710**, and within it the effect tracks "
        "window smoothness -- the six smoothest windows fall **0.632 to 0.812** while "
        "textured windows sit at **0.99 to 1.03**. `bee-3-cpl` median **1.064** and "
        "`foam` **1.013**, both roughly uniform across smooth and textured windows. In "
        "the subject that moves, the test arm converges to a **floor near 45-53 counts** "
        "from a base of 56-79.",
    ),
    (
        1638,
        "MEASURED",
        "ORCH",
        "**AND THE PIXELS SHOW WHAT THE NUMBER MEANS: THE DEFAULT MERGE COVERS A "
        "DEFOCUSED BACKGROUND IN BLOTCHES AND `--photometric` REMOVES THEM.** At "
        "`tweezers-cpl` x=912 y=400 under a **shared stretch taken from the base arm** "
        "(`PHOTOMETRIC-tweezers-cpl-smooth-912x400.png`), the default arm shows dozens of "
        "soft oval patches over a smooth tonal gradient; the photometric arm shows the "
        "gradient and no patches. **A defocused region cannot contain structure at that "
        "scale** -- defocus is a low-pass filter -- so the patches are manufactured, which "
        "is the invariant of fact 1631 stated visually. **The blur control passes:** at "
        "x=400 y=656 the tweezer edge, its grain and the speckled texture are preserved "
        "indistinguishably, so this is not smoothing. Cost is **+3.7 s mean over three "
        "subjects (45.81 -> 49.52 s)** and on `tweezers-cpl` the photometric arm was "
        "**faster** (52.01 -> 45.80 s), so run-to-run variance exceeds the effect. **This "
        "is the first measured, visible removal of the mosaic from a shipped-path render.**",
    ),
    (
        1639,
        "MEASURED",
        "ORCH",
        "**M116'S `KEEP-OFF` VERDICT ON PHOTOMETRIC IS NOT REFUTED BY THIS -- ITS BAR WAS "
        "ON THE WRONG AXIS.** M116 scored the identical arms with a global sharpness "
        "statistic and measured **+0.00477 (bee), -0.00003 (foam), +0.00835 (tweezers) "
        "against a +0.010 promotion bar**, and returned KEEP-OFF. **Every one of those "
        "numbers is at or above zero** -- its own data says the instrument never hurt "
        "sharpness on any subject -- and the arm simply failed a threshold defined on an "
        "axis the defect does not live on. The defect is **tonal**: patchy per-region "
        "level offsets change tone, not sharpness. Both measurements are correct and they "
        "are measuring different things.",
    ),
    (
        1640,
        "ARGUED",
        "ORCH",
        "**THE MECHANISM CHAIN FOR THE MOSAIC IS NOW COMPLETE END TO END, WHICH IS WHY "
        "THIS IS MORE THAN ONE SUBJECT'S RESULT.** Frames differ in level by 3.2-8.4% "
        "peak-to-peak (fact 1633, corroborating M24); the difference is a smooth ramp in "
        "frame index that a per-frame gain fit removes almost entirely (fact 1634, 91.8% "
        "of variance); the merge elects different frames in different regions; so regions "
        "inherit different levels and the background acquires plateaus (fact 1638's "
        "blotches); and fitting the gain removes them (facts 1637, 1638). **Every link is "
        "measured.** The prediction that survives is that a subject shows the defect in "
        "proportion to its level drift, which explains why `bee-3-cpl` -- whose default "
        "background already sits at 33-47 counts, **smoother than the photometric arm on "
        "`tweezers-cpl`** -- has nothing to fix. **Untested:** whether that proportionality "
        "holds across the corpus. That is the measurement that would justify flipping the "
        "default, and it needs the drift figure and the blotch figure on the same stacks.",
    ),
]

NEW_DISCS = [
    (
        834,
        "**A promotion bar is defined on an axis, and it silently rejects wins on every "
        "other axis.** M116 built a careful campaign, pre-registered a threshold, ran 12 "
        "arm-subject pairs, and correctly reported that none cleared it (fact 1639). The "
        "same files, scored with a statistic shaped like the defect actually complained "
        "of, contain a 29% effect and an obvious visual one (facts 1637, 1638). **Nothing "
        "was done wrong** -- and that is the point, because no amount of rigour inside the "
        "bar detects that the bar points elsewhere. **Before accepting a null, state what "
        "the metric would have to be blind to for the null to be false, and check.**",
    ),
    (
        835,
        "**When an effect is real but confined to one subject, report the covariate before "
        "reporting the average.** The cross-subject median for photometric is 1.013, which "
        "reads as 'no effect' and is how a summary row would have recorded it. The "
        "per-window table shows the effect tracks background smoothness within "
        "`tweezers-cpl` and that `bee-3-cpl` starts below the floor the fix converges to "
        "(fact 1637). **The median destroyed the finding; the covariate explained it.** "
        "Aggregate last.",
    ),
]

NEW_QS = [
    (
        203,
        "**Does blotch severity track measured level drift across the corpus?** Fact 1640 "
        "makes this the deciding measurement for flipping `STREHL_PHOTOMETRIC` on by "
        "default. The instruments both exist and are cheap: `level_drift_budget.py` gives "
        "the per-stack drift and `photometric_ab.py` gives the per-stack blotch response, "
        "so the test is one scatter plot over every stack in `D:\\personal\\macro`. **A "
        "positive correlation promotes the default and predicts which stacks benefit; a "
        "null means the tweezers result has some other cause and the mechanism chain of "
        "fact 1640 has a broken link.**",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)
q_block = "\n".join("%d. %s" % q for q in NEW_QS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for block in (fact_block, disc_block, q_block):
    for line in block.split("\n"):
        stripped = _re.sub(r"`[^`]*`", "", line)
        assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw
for anchor, block, what in (
    (fact_line, fact_block, "facts"),
    (disc_line, disc_block, "disciplines"),
    (q_line, q_block, "questions"),
):
    prev = out
    out = out.replace(anchor, anchor + "\n" + block, 1)
    assert out != prev, "%s insertion did not land" % what

# fact 1636 predicted this and has now been tested -- mark it in place.
OLD = "| 1636 | ARGUED | ORCH | **ON THIS EVIDENCE"
NEW = ("| 1636 | ARGUED | ORCH | **CONFIRMED in part by facts 1637-1638 (visible fix on "
       "one of three subjects; the promotion question is now 203).** **ON THIS EVIDENCE")
assert OLD in out, "fact 1636 anchor not found"
prev = out
out = out.replace(OLD, NEW, 1)
assert out != prev, "fact 1636 marking did not land"
row = full_line(out, "| 1636 |")
n = len(row.replace("\\|", "").split("|")) - 1
assert n == 5, "fact 1636 now has %d pipes" % n

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("folded question %s" % ", ".join(str(q[0]) for q in NEW_QS))
print("marked fact 1636 CONFIRMED in part")
