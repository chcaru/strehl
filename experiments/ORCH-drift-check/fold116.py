"""Fold M111's arithmetic re-analysis of ORCH's CA gain table.

Facts 1526-1527, disciplines 785-786, and an in-place WEAKENED marker on the
sqrt(2) clause of fact 1512.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1525 |")
disc_line = full_line(raw, "784. ")

# --- in-place marker on 1512's sqrt(2) clause -------------------------------
SQRT_ANCHOR = (
    "note **1/sqrt(2) = 0.7071** lies inside the measured spread, so a "
    "normalisation discrepancy between where the coefficient is fit and where "
    "it is applied should be sought **before** any fitted scalar is shipped."
)
SQRT_REPLACEMENT = (
    "note **1/sqrt(2) = 0.7071** lies inside the measured spread. "
    "**[WEAKENED by fact 1526 -- that spread is the raw range of seven per-ring "
    "point estimates, NOT a confidence interval on their mean. Weighted by ring "
    "support, sqrt(2) is EXCLUDED at 95 % inside the fitted support (t = +3.53). "
    "Do not spend effort hunting a sqrt(2) normalisation bug on this evidence.]**"
)
assert raw.count(SQRT_ANCHOR) == 1, "sqrt(2) anchor did not match exactly once"

NEW_FACTS = [
    (
        1526,
        "MEASURED",
        "M111",
        "**ORCH's sqrt(2) hypothesis does not survive weighting by ring support, and "
        "the error was quoting a spread as an interval.** Re-analysis of ORCH's own gain "
        "table -- **arithmetic only, not an independent re-measurement** -- gives: all "
        "seven rings, mean **1.4454**, 95 % CI **[1.4095, 1.4814]**, t = +2.12 vs "
        "sqrt(2) = 1.4142, **compatible**; **inside support only (six rings), mean "
        "1.4562, CI [1.4256, 1.4867], t = +3.53, EXCLUDED**. The two rings nearest "
        "sqrt(2) -- 1.505 (n=52) and 1.381 (n=33) -- are the two noisiest and together "
        "carry **7.4 %** of the windows. Implied inverse **0.687**, not 0.7071. **The raw "
        "range 1.381-1.505 that made sqrt(2) look plausible is the scatter of point "
        "estimates, and is roughly 4x wider than the standard error of their mean.** "
        "ORCH has retracted the sqrt(2) steer to M107.",
    ),
    (
        1527,
        "MEASURED",
        "M111",
        "**Fact 1513's flat-in-radius claim is SUPPORTED under window-weighted "
        "regression.** Window-weighted radial trend of the gain is a slope of "
        "**-0.0684 per unit r**, which is **-0.0397 across the entire measured span** "
        "(r = 0.25 to 0.83) against a mean of ~1.45 -- under 3 % of the level. **A single "
        "scalar is the right model shape**, so the correction's error is one of scale, "
        "not of radial form, and the visible fringes at r = 0.879 / 0.822 are not "
        "special. This independently re-confirms the refutation of fact 1501 by a second "
        "route: fact 1513 rested partly on one outside-support ring at n=1, which ORCH "
        "flagged as a possible over-claim; this rests on all seven rings weighted.",
    ),
]

NEW_DISCS = [
    (
        785,
        "**A spread of point estimates is not a confidence interval on their mean, and "
        "quoting one as the other manufactures agreement.** ORCH reported a CA gain range "
        "of 1.381-1.505 and concluded that sqrt(2) = 1.4142 was 'inside the measured "
        "spread'. The standard error of the mean was roughly **4x narrower**, and against "
        "it sqrt(2) is excluded (fact 1526). **The scatter of estimates answers 'how "
        "variable is a single ring', not 'where is the mean'** -- and it is the second "
        "question that a hypothesis about a single global constant is asking. Before "
        "declaring a round number compatible with data, state which of the two you "
        "computed.",
    ),
    (
        786,
        "**Weight binned statistics by their support before reading anything off the "
        "extremes, because the extreme bins are usually the least-supported ones.** In "
        "the CA gain table the highest (1.505) and lowest (1.381) rings carried 52 and 33 "
        "windows against up to 240 elsewhere -- **7.4 % of the data defining 100 % of the "
        "range**. Unweighted, they set the apparent uncertainty and rescued a hypothesis; "
        "weighted, they nearly vanish. This is the same failure mode as fact 1526 seen "
        "from the other side, and the general rule is: **the tails of a binned summary "
        "are where n is smallest, so they are exactly where a conclusion is least "
        "affordable.**",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for block in (fact_block, disc_block, SQRT_REPLACEMENT):
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(SQRT_ANCHOR, SQRT_REPLACEMENT, 1)
assert out != raw, "sqrt(2) marker did not land"
prev = out
out = out.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != prev, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

for fid, _, _, _ in NEW_FACTS:
    assert out.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert out.count("\n%d. " % did) == 1, "discipline %d not unique" % did
assert out.count("WEAKENED by fact 1526") == 1, "marker not unique"

# the 1512 row must still be a well-formed five-pipe table row after the edit
row1512 = full_line(out, "| 1512 |")
assert len(row1512.replace("\\|", "").split("|")) - 1 == 5, "fact 1512 row malformed"

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("fact 1512 marked WEAKENED; row still well formed")
