"""Fold M110's radial-polarity null and its reinterpretation of the W3 bar.

Facts 1587-1591, disciplines 818-819.

The consequential one is 1588: `RECOLOURED, NOT REMOVED` -- which ORCH has cited
all night as evidence of a defect -- is what a sign-retention bar prints when the
correction WORKS. M113's own residuals corroborate it arithmetically.
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


fact_line = full_line(raw, "| 1586 |")
disc_line = full_line(raw, "817. ")

NEW_FACTS = [
    (
        1587,
        "MEASURED",
        "M110",
        "**THERE IS NO POLARITY REVERSAL BEYOND THE FIT'S OUTER SUPPORT, AND NO OVERSHOOT "
        "ANYWHERE.** M110 scored overshoot as the **conjunction** that the word actually "
        "means -- the sign of `R-Y` flips **and** its magnitude grows -- rather than as a "
        "flip alone. Gated at one display level. On `bee-3-cpl` the rate across the "
        "r = 0.788 support boundary runs **9.73 % / 9.78 % / 9.47 %**; on `flat-on-ruler` "
        "it **falls**, **14.22 % / 13.68 % / 11.66 %**. **No discontinuity at the boundary "
        "and no upward trend beyond it**, where an over-large `eps_r` would have to climb "
        "monotonically. The null control reads **0.00 % exactly**. This is a second, "
        "independent burial of fact 1501's extrapolation hypothesis, reached from a "
        "different direction than fact 1571's.",
    ),
    (
        1588,
        "MEASURED",
        "M110",
        "**`RECOLOURED, NOT REMOVED` IS WHAT A SIGN-RETENTION BAR PRINTS WHEN THE "
        "CORRECTION WORKS. The W3 failure ORCH has cited all night as evidence of a defect "
        "is a defect in the BAR.** Flip rates reach **62.9 %** while overshoot is only "
        "**9-19 %**, so **most flips are flips WITH SHRINKAGE** -- fringes driven through "
        "neutral toward grey, which is exactly what a working correction does and exactly "
        "what a keep-sign statistic counts as failure. **M113's independent residuals "
        "corroborate this arithmetically**: the sign-flipped remainders are **132.3 ppm "
        "against 529.9** (25 %) and **36.5 against 654.9** (5.6 %) -- flips at a quarter "
        "and a twentieth of the original amplitude. And 5.6 % is **precisely** M113's "
        "measured `couch-fibers-cpl` gain of 1.0557. **A sign-retention bar cannot "
        "distinguish 'over-corrected by 44 %' from 'corrected to within 6 %'**, and the "
        "project spent a night acting on the first reading.",
    ),
    (
        1589,
        "MEASURED",
        "M110",
        "**THE CORRECTION MAKES FRINGES FAINTER, NOT THINNER -- and the sheet must not "
        "claim otherwise.** Chroma reduction **concentrates at the edge** rather than "
        "spreading uniformly: `bee-3-cpl` falls **-29.4 % at band 0** decaying to "
        "**-9.4 % at band 5**, `flat-on-ruler` **-49.3 %** to **-35.7 %**, so it is not a "
        "uniform recolour. Edge-localised chroma excess drops **61.0 %** and **58.7 %**. "
        "But **half-max width is unchanged** at 1-px resolution -- the peak falls faster "
        "than the tail, taking peak-to-baseline contrast from **2.45x to 1.93x** (flat) "
        "and **1.63x to 1.27x** (bee). M110 flagged this pre-emptively against a claim "
        "nobody had yet made.",
    ),
    (
        1590,
        "MEASURED",
        "M110",
        "**A DETECTION RULE OF ORCH'S CARRIED A COMPONENT WITH NO SIGNAL IN IT.** ORCH "
        "issued the rule *'if an arm completed in roughly full runtime but was "
        "byte-identical to the no-correction arm, re-check its profile key'*. **Runtime "
        "carries no signal**: across four subjects the live CA arms ran **53.0 -> 60.8 s** "
        "(bee), **22.1 -> 23.0**, **21.8 -> 22.0**, and **`wrapped-text-1` 27.7 -> 25.0 s, "
        "i.e. the corrected arm ran FASTER than its own control**. **Byte-distinctness is "
        "the entire instrument.** M110's own manifest already carried the check: "
        "`distinct_hashes_ok = True` and `duplicate_pairs = []` on all four subjects, and "
        "it reproduced ORCH's published `off`/`on` hashes exactly.",
    ),
    (
        1591,
        "MEASURED",
        "M110",
        "**ORCH ASSERTED A `HEAD` THAT WAS FIVE COMMITS STALE WHILE VOUCHING FOR A BUILD "
        "AGAINST IT.** ORCH told the fleet `HEAD` was `9c279d8` and that it had verified a "
        "clean `cargo check` there; `HEAD` was in fact `16f2dd2`. M110's reply: *'if your "
        "build-clean verification was against `9c279d8`, it does not cover what agents "
        "will actually compile tonight.'* With thirteen agents committing, a `HEAD` "
        "quoted in a broadcast is stale before the broadcast is read, so **the commit a "
        "verification covers must be captured by the verification itself and reported with "
        "it**, never restated from memory.",
    ),
]

NEW_DISCS = [
    (
        818,
        "**Score the compound claim, not the component that is easy to count.** "
        "*Overshoot* means a sign flip **and** a magnitude increase; counting flips alone "
        "conflated a working correction with a broken one and reported **62.9 %** where "
        "the real rate was **9-19 %** (facts 1587-1588). The general trap: a statistic "
        "that captures **one** of the conjuncts will fire on the benign case, and it fires "
        "*hardest* exactly when the treatment works best, because a correction that lands "
        "near zero flips the most signs. **Before believing a bar, ask what a perfect "
        "treatment would score on it** -- here, a perfect correction scores near-total "
        "failure.",
    ),
    (
        819,
        "**Every component of a detection rule must be a quantity the mechanism actually "
        "changes -- a plausible-looking one that does not discriminate licenses a false "
        "clear.** ORCH's rule paired byte-identity, which discriminates perfectly, with "
        "runtime, which does not: a live correction arm ran **faster** than its own "
        "control (fact 1590). This is the same error shape as clearing an exit-code gate "
        "because the code looked right (fact 1508). **Ask of each clause: what values does "
        "it take under the defect, and under its absence?** If those overlap, the clause "
        "is not evidence and belongs out of the rule rather than in it as reassurance.",
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

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
