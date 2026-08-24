"""Fold ORCH's convention-ratio enumeration, which weakens ORCH's own lead.

Facts 1532-1533, disciplines 791-792.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1531 |")
disc_line = full_line(raw, "790. ")

NEW_FACTS = [
    (
        1532,
        "MEASURED",
        "ORCH",
        "**No simple radius-convention ratio explains the CA gain: the measurement falls "
        "in the GAP between the only two natural candidates.** Enumerating every ratio "
        "between plausible normalisations on the 7032 x 4688 frame -- half and full "
        "width, height and diagonal, each also under a square root -- gives "
        "`sqrt(full-diagonal / half-diagonal) = 1.4142` **below** the inside-support "
        "interval [1.4256, 1.4867] and `full-width / full-height = 1.5000` **above** it, "
        "with the measured mean **1.4562** between them and nothing else closer than 1.33 "
        "or 1.55. **ORCH had already told M107 the arithmetic 'lands in this "
        "neighbourhood' before running it; it does not.** Script: "
        "`experiments/ORCH-drift-check/convention_check.py`.",
    ),
    (
        1533,
        "ARGUED",
        "ORCH",
        "**That exclusion is weaker than it looks, because the interval has no systematic "
        "budget in it.** [1.4256, 1.4867] is the scatter of seven ring estimates about "
        "their mean and carries **statistical error only**. Three systematics in the "
        "instrument are known and **none is quantified**: the positive control plants a "
        "**uniform translation** while the reported quantity is a **radial scale**, so the "
        "control never exercises the geometry the measurement claims; it is **one scene**, "
        "against a profile fitted on two different ones; and the tangential-displacement "
        "noise floor assumes **isotropic** error while M16 measured orientation-dependent "
        "FPN. **A 3 % systematic re-admits both candidates**, and 3 % is small. "
        "Conclusion handed to M107: **the measurement cannot identify the constant, so "
        "read the source rather than matching a number** -- reading is exact and cheap, "
        "refining the measurement is expensive and may still not adjudicate.",
    ),
]

NEW_DISCS = [
    (
        791,
        "**Run the arithmetic before telling anyone it supports your hypothesis.** ORCH "
        "sent M107 a ranked list of convention bugs to hunt, headed 'check 1 first', on "
        "the strength of unrun mental arithmetic that a radius-convention error 'lands in "
        "this numeric neighbourhood'. Enumerated properly it lands in the **gap between** "
        "the two candidates (fact 1532). The cost of being wrong here is not the "
        "orchestrator's -- it is a subordinate spending hours hunting a bug in the wrong "
        "place, on authority.",
    ),
    (
        792,
        "**A statistical interval is not an exclusion when the systematics are unquantified "
        "and plausibly larger.** The same interval was used to exclude sqrt(2) (fact 1526) "
        "and then to exclude every convention ratio (fact 1532) -- but it describes "
        "ring-to-ring scatter, not instrument bias, and the instrument has three known "
        "unquantified biases (fact 1533). **State which errors an interval contains before "
        "using it to rule anything out**, and prefer a decisive cheap observation -- read "
        "the code, measure on the fitting data -- over a tighter version of an interval "
        "that was never measuring the right error in the first place.",
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
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != raw, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

for fid, _, _, _ in NEW_FACTS:
    assert out.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert out.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
