"""Fold the level-drift budget.

Facts 1633-1636, discipline 833, question 139.
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


fact_line = full_line(raw, "| 1632 |")
disc_line = full_line(raw, "832. ")

NEW_FACTS = [
    (
        1633,
        "MEASURED",
        "ORCH",
        "**INTER-FRAME LEVEL DRIFT IS PRESENT ON M93 AT 3.2-8.4% PEAK-TO-PEAK, "
        "INDEPENDENTLY CORROBORATING M24.** Measured over 23 single input frames at six "
        "widely separated background windows of 256 px "
        "(`experiments/ORCH-drift-check/level_drift_budget.py`), the window mean drifts "
        "**3.208% / 3.816% / 6.584% / 6.890% / 7.701% / 8.406%** peak-to-peak. M24 "
        "measured **2.88% / 6.84% / 8.93% / 11.70%** on four different stacks by a "
        "different method; these land inside that range. **Two independent measurements "
        "on different data now agree that the frames a merge gathers differ in level by "
        "several percent.**",
    ),
    (
        1634,
        "MEASURED",
        "ORCH",
        "**THE DRIFT IS A SMOOTH GLOBAL RAMP IN FRAME INDEX, WHICH IS EXACTLY THE SHAPE A "
        "FITTED PER-FRAME GAIN REMOVES.** A straight line in frame index removes **91.8% "
        "of the drift's variance**, leaving a residual sd of **0.449% of level**. The "
        "sequence is monotone across the whole bracket (19624 counts at f120 falling to "
        "18322 at f208). **This matters for the remedy, not just the diagnosis:** "
        "frame-to-frame scatter would need a robust per-frame estimator and would leave "
        "residue, whereas a smooth one-parameter-per-frame trend is the case a simple "
        "fitted gain handles almost completely.",
    ),
    (
        1635,
        "MEASURED",
        "ORCH",
        "**LEVEL DRIFT IS SUFFICIENT TO SUPPLY ROUGHLY HALF THE MERGE'S SPATIAL SWING, "
        "AND THAT IS A LOWER BOUND.** Over the same six windows, drift peak-to-peak "
        "against the merge's spatial sd expressed as a fraction of level: median "
        "**52% of the gate-0 swing and 56% of the gate-4 swing**, ranging 26%-175% "
        "window to window. **The figure is a lower bound on drift's share of the "
        "ARTIFACT**, because the denominator is the window's total spatial variation and "
        "some of those windows contain genuine scene structure (two swing 13-18%, far "
        "above any plausible artifact). **Sufficiency is not attribution** -- nothing "
        "here shows that removing the drift removes the artifact, only that the drift is "
        "large enough to account for a large share of it.",
    ),
    (
        1636,
        "ARGUED",
        "ORCH",
        "**ON THIS EVIDENCE `STREHL_PHOTOMETRIC` IS THE BEST-EVIDENCED UNTESTED "
        "IMPROVEMENT AVAILABLE TO THE SHIPPED RENDER, AND NOBODY HAS RUN IT.** The chain: "
        "the merge gathers different frames in different regions; those frames differ by "
        "several percent in level (fact 1633, M24); the difference is a smooth ramp a "
        "gain fit removes (fact 1634); and it is large enough to supply about half the "
        "observed swing (fact 1635). The correction exists and is **default OFF** "
        "(`main.rs:284`). **This is a prediction, not a result** -- it was pre-registered "
        "to M116 with the instrument to test it (`patchwork_invariant.py`, baseline "
        "1.114x and 7/12 at the shipped gate) and the instruction not to evaluate it on "
        "`109MSDCF`, which M24 measured at 0.91% and is the quietest stack in the "
        "corpus. **A null would be valuable**: it would rule out level drift and point at "
        "the focus decision itself.",
    ),
]

NEW_DISCS = [
    (
        833,
        "**Say 'sufficient' when you have shown sufficiency, and do not let it drift into "
        "'the cause'.** Fact 1635 shows level drift is large enough to account for about "
        "half the merge's spatial swing. That is a real and useful result -- a mechanism "
        "too small to produce the artifact is dead on arrival, and this one is not -- but "
        "**it is one-directional**. The test that converts sufficiency into attribution "
        "is removing the mechanism and re-measuring the artifact, and until someone runs "
        "it the honest word is 'candidate'. The corpus has a bad history here: fact 1580 "
        "promoted a correction on a headline number, and facts 1595-1602 took it back.",
    ),
]

NEW_QS = [
    (
        139,
        "**Is the level drift illumination, or is it focus breathing moving scene content "
        "through a fixed window?** Fact 1633 measures a monotone level ramp at fixed "
        "pixel coordinates across the bracket, and both explanations predict that. They "
        "differ in the remedy: a global per-frame gain removes illumination drift "
        "correctly and would be **wrong** for breathing, which is a geometric "
        "magnification change about the optical axis and should therefore vary with "
        "radius. The six windows measured do not show a clean radial pattern -- (2832, "
        "400) and (2704, 400) sit at similar radii and read 6.890% and 3.208% -- which "
        "argues against pure breathing, but those windows also differ in content, so it "
        "is not decisive. **The clean test is the drift slope against radius over many "
        "windows of matched content.** Cheap, and it decides whether the correction fact "
        "1636 proposes is even the right shape.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for block in (fact_block, disc_block):
    for line in block.split("\n"):
        stripped = _re.sub(r"`[^`]*`", "", line)
        assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != raw, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

q_anchor = full_line(out, "138. ")
q_block = "\n".join("%d. %s" % q for q in NEW_QS)
for line in q_block.split("\n"):
    stripped = _re.sub(r"`[^`]*`", "", line)
    assert stripped.count("**") % 2 == 0, "odd ** in question: %s" % line[:90]
prev = out
out = out.replace(q_anchor, q_anchor + "\n" + q_block, 1)
assert out != prev, "question insertion did not land"

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded discipline %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("folded question %s" % ", ".join(str(q[0]) for q in NEW_QS))
