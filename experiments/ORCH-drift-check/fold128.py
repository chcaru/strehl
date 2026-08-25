"""Fold M111's two methodological corrections to ORCH.

Facts 1582-1586, disciplines 815-817.

Both were delivered as replies to ORCH's lateral-CA messages. The CA MAGNITUDE
those messages carried (1.444) has since been refuted by M113 (fact 1567), but
neither of M111's contributions depends on it: one is a statistics error in how
ORCH read its own table, the other is a defect in a control ORCH proposed, and
the control defect is general to any resampling treatment.
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


fact_line = full_line(raw, "| 1581 |")
disc_line = full_line(raw, "814. ")

NEW_FACTS = [
    (
        1582,
        "MEASURED",
        "M111",
        "**ORCH READ ITS OWN TABLE WITH THE WRONG INTERVAL: the dispersion of seven "
        "per-ring estimates is not the standard error of their centre.** ORCH argued a "
        "`sqrt(2)` normalisation bug was plausible because 1.4142 *'sits inside the "
        "measured spread 1.381-1.505'*. That spread is the **range of the seven "
        "estimates**; the uncertainty of their mean is **sem 0.0147**, about **four times "
        "narrower**. All seven rings give CI **1.4095-1.4814** (`t = +2.12`, compatible); "
        "inside-support only gives **1.4256-1.4867** (`t = +3.53`, excluded); "
        "window-weighting moves the centre **away** from `sqrt(2)`. **The verdict flips on "
        "the cut**, and the row responsible is the single OUTSIDE ring at **n = 33, ~2.9 % "
        "of all windows** -- the only row below `sqrt(2)`. Context: the underlying gain "
        "table is itself REFUTED by fact 1567; the reading error is independent of that "
        "and was made on whatever table was in front of it.",
    ),
    (
        1583,
        "MEASURED",
        "M111",
        "**AND THE INTERVAL WAS STILL TOO NARROW, IN THE DIRECTION THAT WEAKENS THE "
        "CONCLUSION.** Seven rings of **one capture sharing one estimator** are not seven "
        "independent draws, so the true uncertainty is wider than any of the three "
        "intervals above. M111 stated this explicitly and drew the correct asymmetric "
        "inference: **wider intervals make an exclusion weaker, never stronger**, so the "
        "`sqrt(2)` exclusion is the claim that degrades and the compatibility finding is "
        "the robust one. It also **caught its own transcription error before reporting**: "
        "it had asserted ORCH's figures against the *mean* when ORCH reported *medians*, "
        "and re-armed its guard to assert medians plus min and max.",
    ),
    (
        1584,
        "MEASURED",
        "M111",
        "**A CONTROL ORCH PROPOSED IS DISQUALIFIED, AND ITS BIAS RUNS TOWARD THE ANSWER "
        "ORCH WANTED.** ORCH proposed a **tangential** displacement as the placebo for the "
        "radial CA correction, reasoning that it shares the code path, the kernel, the "
        "sensel count and therefore *'the same blur'*. **The blur claim is false**: "
        "interpolation blur is set by the displacement's **sub-pixel phase along each "
        "pixel axis**, not by its magnitude, and radial and tangential split an equal "
        "magnitude differently between x and y. Measured high-frequency retention at "
        "`\\|d\\| = 0.155 px` -- **isotropic content 0.653410 vs 0.655221 (0.28 % apart)**, "
        "but **oriented hair-like content 0.514191 vs 0.994494 (93.41 % apart)**. The "
        "tangential arm blurs the direction that is already smooth and so pays almost no "
        "blur penalty, meaning it **under-blurs the arm it stands in for**. ORCH's crops "
        "were hairs and wing membrane: the worst case.",
    ),
    (
        1585,
        "MEASURED",
        "M111",
        "**THE REPLACEMENT CONTROL IS THE SAME CORRECTION AT NEGATIVE STRENGTH, AND IT IS "
        "EXACTLY BLUR-NEUTRAL.** Across 8 magnitudes from 0.069 to 0.450 px, "
        "`\\|retention(+d) - retention(-d)\\|` is **1.11e-16** -- floating-point zero. So a "
        "sign flip holds interpolation blur constant **per pixel**, at the same location, "
        "on the same content, with no new direction logic. It is also a **negative dose "
        "rather than a null**: at r = 0.450 the anti arm carries **2.44x** the uncorrected "
        "displacement, giving a **monotone three-arm ladder spanning 5.5x** (anti 0.379, "
        "off 0.155, on 0.069). M111 validated the instrument before using it: integer "
        "shifts retain **1.000000**, half-pixel retention bottoms at **0.338**.",
    ),
    (
        1586,
        "MEASURED",
        "M111",
        "**AND THE COMPARISON MUST BE `anti` AGAINST `on`, NOT AGAINST `off`.** `anti` and "
        "`on` both resample, so **blur cancels exactly between them** while the CA differs "
        "by 5.5x -- which makes any difference attributable to the CA and not to the "
        "resampler. `off` cannot serve as the blur reference at all, because fact 1517 "
        "established that the zero-strength path **short-circuits rather than resampling "
        "by zero**, so it omits the very nuisance the control exists to hold constant. If "
        "a strict null is wanted instead of a dose, the **round-trip** arm (`+d` then "
        "`-d`) has zero net displacement and **2x** blur, which is conservative: if 2x "
        "blur does not reduce the artifact, 1x did not either.",
    ),
]

NEW_DISCS = [
    (
        815,
        "**Ask which way your control's residual bias points -- a control biased toward "
        "your hypothesis is worse than no control, because it converts a confound into a "
        "confirmation.** The tangential placebo under-blurs on oriented content (fact "
        "1584), so *'the artifact vanished in the placebo arm'* was partly guaranteed by "
        "construction and would have been read as *'the treatment earned it'*. **The "
        "disqualifying property is that the bias is uncontrolled, not that it is large**: "
        "the same control is fine at 0.28 % on isotropic content and fatal at 93.41 % on "
        "hairs, and nothing in the design tells you which regime you are in.",
    ),
    (
        816,
        "**Prefer a negative-dose arm to a null arm: it holds the nuisance exactly "
        "constant and yields a monotone ladder instead of a single contrast.** Running the "
        "treatment at negative strength matched interpolation blur to **1.11e-16** where a "
        "direction change failed by up to 93 % (facts 1584-1585). A null arm answers *'is "
        "the effect there?'*; a dose ladder answers *'does the effect scale with the "
        "treatment?'*, which is much harder for a confound to imitate. **And check that "
        "your null arm actually executes the nuisance** -- a zero-strength path that "
        "short-circuits omits it (fact 1586).",
    ),
    (
        817,
        "**The dispersion of k sub-estimates is not the standard error of their mean, and "
        "sub-estimates from one capture sharing one estimator are not k independent "
        "draws.** ORCH read a range as an interval and a mechanism hunt was dispatched on "
        "it (fact 1582). Two habits follow: **state which interval you are quoting**, and "
        "when the sub-estimates are correlated, note that the honest interval is **wider** "
        "-- then check which of your conclusions that direction weakens (fact 1583). "
        "Correlation always degrades an **exclusion** and always leaves a **compatibility** "
        "finding intact, so the asymmetry is knowable without computing the correlation.",
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
