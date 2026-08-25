"""Fold M113's independent falsification of ORCH's 1.444 lateral-CA gain.

Facts 1567-1575, disciplines 809-812.
Also marks facts 1511-1514 REFUTED in place.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1566 |")
disc_line = full_line(raw, "808. ")

NEW_FACTS = [
    (
        1567,
        "MEASURED",
        "M113",
        "**ORCH'S 1.444 LATERAL-CA GAIN IS REFUTED. The true gain in an uncontaminated "
        "space is 1.2496 on `bee-3-cpl` and 1.0557 on `couch-fibers-cpl`.** `needed` is "
        "**529.9** and **654.9 ppm** against the shipped **704.5 ppm**. Facts 1511-1514's "
        "headline number does not reproduce. **The implied fix -- multiply the red "
        "coefficient by 0.692 -- MUST NOT SHIP: on `couch-fibers-cpl` it converts a 5.6 % "
        "over-correction into a 27.0 % UNDER-correction**, worse in magnitude than the "
        "defect it removes.",
    ),
    (
        1568,
        "MEASURED",
        "M113",
        "**THE CAUSE: I MEASURED A CROSS-CHANNEL QUANTITY IN A SPACE CONTAINING TWO "
        "CROSS-CHANNEL OPERATORS, ON A FILE WHOSE OWN `--help` SAYS IT IS NOT FOR "
        "MEASURING.** The renders were `--srgb --auto-exposure`. (a) `camera_to_srgb` from "
        "`A7C2_XYZ_TO_CAM` is **non-diagonal**: `R_out = +1.1975 R -0.1250 G -0.0725 B`, "
        "`G_out = -0.4530 R +2.2300 G -0.7770 B`, so output red carries camera green at "
        "**10.4 %** and output green carries camera red at **20.3 %**, **both at zero "
        "displacement** -- a synthetic zero-lag inter-channel signal on top of the "
        "displacement being measured. (b) `demosaic.rs:482` documents that "
        "Malvar-He-Cutler **assumes `R - G` is smoother than either channel**, which a "
        "lateral-CA fringe violates **by definition**. `main.rs:116` on `--srgb`: **'For "
        "looking at, NOT for measuring.'**",
    ),
    (
        1569,
        "MEASURED",
        "M113",
        "**THE INSTRUMENT THAT CAUGHT IT, AND THE MOST TRANSFERABLE RESULT HERE: a "
        "compile-time constant applied by the pipeline is a FREE END-TO-END CALIBRATION OF "
        "THE MEASUREMENT CHAIN.** Since `eps_r = -704.5 ppm` is a known constant in "
        "`optics.rs`, the quantity `applied = eps_on - eps_off` has a **ground truth**, and "
        "`applied / eps_r` calibrates every stage between sensor and file. It reads "
        "**1.3073** (sRGB), **0.6963** (demosaic-linear), **0.9399 / 0.9813** (binned "
        "linear). **The two contaminated spaces are wrong in OPPOSITE directions, +31 % "
        "and -30 %** -- which is why no internal consistency check could have separated "
        "them and only the external constant could.",
    ),
    (
        1570,
        "MEASURED",
        "M113",
        "**NO SCALAR FIX EXISTS, AND THE REASON IS PHYSICAL RATHER THAN STATISTICAL.** "
        "`needed` differs by **23.6 %** between two scenes shot through the same glass "
        "(529.9 vs 654.9 ppm) while per-ring standard deviations are only **8-23 ppm**, so "
        "the ~140 ppm gap is **not noise**. Lateral CA is the separation of each channel's "
        "**effective wavelength**, which is its passband centroid **weighted by the "
        "scene's own spectrum** -- and the scenes differ (R/G **1.0017 vs 0.9381**, B/G "
        "**0.9334 vs 1.0807**). This is fact 52's warning about transferring a "
        "scene-fitted scalar, **now measured**. Any improvement must come from a better "
        "*model* -- spectral or per-capture estimation -- never a better constant.",
    ),
    (
        1571,
        "MEASURED",
        "M113",
        "**WHAT SURVIVES, AND IT IS NOW BETTER SUPPORTED THAN WHEN I CLAIMED IT.** (a) The "
        "radial **shape** is correct: `eps(r)` is flat within **+/-15 ppm** from r = 0.11 "
        "to 0.87 on `couch-fibers-cpl` (bootstrap sd 8-23 ppm). (b) Fact 1514's "
        "`RECOLOURED, NOT REMOVED` is **confirmed on two stacks under two independent "
        "estimators**: residual `eps` flips sign, **-529.9 -> +132.3** and **-654.9 -> "
        "+36.5 ppm**. (c) Fact 1501's refutation stands, though my evidence for it did "
        "not: I used **n = 1 ring, 5.3 % beyond support, in the contaminated space**; the "
        "clean re-measurement gives outside/inside = **1.0128 on 111 outside-support "
        "windows**.",
    ),
    (
        1572,
        "MEASURED",
        "M113",
        "**MY ESTIMATOR WAS NOT BROKEN, AND THE EARLIER INDICTMENT OF IT WAS "
        "SPACE-SPECIFIC RATHER THAN ESTIMATOR-SPECIFIC.** A previous report's claim that "
        "ORCH's estimator is 'blind to 94 % of the field' is withdrawn: run **unmodified** "
        "in the clean binned space, `shift_of` returns gain **1.0595** against M113's "
        "independent **1.0557** (0.4 % apart) and `eps_off` **-593.2** against **-654.9**. "
        "The whitening step `X/\\|X\\|` weights all frequencies equally and therefore "
        "**maximally amplifies a zero-lag contaminant** -- which was genuinely present. "
        "The estimator was correctly reporting a contaminated input.",
    ),
    (
        1573,
        "MEASURED",
        "M113",
        "**A DEFECT IN ORCH'S OWN INSTRUMENT: `ca_gain.py` printed a fabricated noise "
        "floor.** `resid_pred = abs(R_off * (1.0 - median(g)/median(g)))` is **identically "
        "zero by construction** and was captioned *'median abs(residual) if gain were 1.0 "
        "... i.e. at the estimator's floor'*. It printed **0.000 on any input whatsoever**. "
        "Repaired: the line now refuses to print rather than emitting a defensible-looking "
        "zero, and the script carries a SUPERSEDED banner.",
    ),
    (
        1574,
        "MEASURED",
        "M113",
        "**Two of ORCH's stated weaknesses were adjudicated in opposite directions.** The "
        "one I considered **most likely to be real** -- that my positive control plants a "
        "**uniform translation** while the measured quantity is a **radial scale** -- is "
        "**REFUTED as a cause**: introducing the real ramp moves the answer by **0.0004 "
        "px**. The one I listed fourth -- that `needed = -R_off` assumes no other source of "
        "inter-channel radial displacement -- is **CONFIRMED and larger than I thought**, "
        "and is fact 1568. **My ranking of my own weaknesses was inverted.**",
    ),
    (
        1575,
        "MEASURED",
        "M113",
        "**`align` correctly refuses a tilted subject.** `highly-angled-ruler-mm-cpl` "
        "exits 1 with *'refusing to solve ... its subject is not normal to the optical "
        "axis'*. The refusal is correct and was **not** overridden with `--force-tilted`, "
        "so that stack is absent from the CA measurements by design rather than by "
        "oversight.",
    ),
]

NEW_DISCS = [
    (
        809,
        "**Before measuring a cross-channel quantity, enumerate every cross-channel "
        "operator between the sensor and the file.** A colour matrix and a guided demosaic "
        "are both cross-channel, both were present, and both were in a file whose own "
        "`--help` says *'For looking at, NOT for measuring'* (fact 1568). The general "
        "form: **a measurement space is part of the instrument.** Establish that the "
        "quantity survives the space before trusting any number taken in it -- and read "
        "the tool's own warnings, which in this case were correct and ignored.",
    ),
    (
        810,
        "**When a pipeline applies a known compile-time constant, that constant is a free "
        "end-to-end calibration of the measurement chain -- use it to test the instrument "
        "before trusting the instrument's other numbers.** `applied / eps_r` separated "
        "three measurement spaces that no internal consistency check could distinguish, "
        "and revealed two contaminations of **+31 % and -30 %** (fact 1569). Look for such "
        "a constant in any pipeline you are about to measure; if one exists, running it is "
        "nearly free and it is the difference between an instrument and a hope.",
    ),
    (
        811,
        "**An estimator that returns a surprising number is not necessarily broken -- "
        "re-run it in a clean space before indicting it.** ORCH's estimator was accused of "
        "being 'blind to 94 % of the field'; unmodified, in the uncontaminated space, it "
        "agreed with an independent method to **0.4 %** (fact 1572). A whitening step that "
        "weights all frequencies equally will **maximally amplify a zero-lag contaminant**, "
        "so the very design choice that made it look broken is what made it a sensitive "
        "detector of the contamination.",    ),
    (
        812,
        "**Rank your own weaknesses, publish the ranking, and expect it to be inverted.** "
        "ORCH listed five weaknesses and named the first as most likely real; the verifier "
        "**refuted that one at 0.0004 px and confirmed the fourth** (fact 1574). The "
        "ranking was still worth publishing -- it directed the verifier's effort and it is "
        "what made the inversion legible. **Author-supplied uncertainty is useful "
        "precisely because it is checkable, not because it is accurate.**",
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

# Mark the refuted facts in place, anchored on the unique row prefix.
MARK = " **REFUTED by fact 1567 (M113): measured in a cross-channel-contaminated space; true gain 1.2496/1.0557 and no scalar fix is supported.**"
for fid in (1511, 1512, 1513, 1514):
    anchor = "\n| %d | " % fid
    assert out.count(anchor) == 1, "fact %d row not unique" % fid
    i = out.index(anchor) + 1
    j = out.index("\n", i)
    row = out[i:j]
    assert row.rstrip().endswith("|"), "fact %d row does not end in a pipe" % fid
    body = row.rstrip()
    newrow = body[:-1].rstrip() + MARK + " |"
    out = out[:i] + newrow + out[j:]
    n = len(newrow.replace("\\|", "").split("|")) - 1
    assert n == 5, "marked row %d has %d pipes" % (fid, n)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("marked REFUTED in place: 1511, 1512, 1513, 1514")
