"""Fold ORCH's own lateral-CA metrology: a validated inter-channel shift estimator,
the measured gain error of 1.444, the refutation of ORCH's own fact 1501, and the
metric that passed a null and still could not see the effect.

Facts 1511-1517, disciplines 772-777. Also marks fact 1501 REFUTED in place.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1510 |")
disc_line = full_line(raw, "771. ")
f1501 = full_line(raw, "| 1501 |")

NEW_FACTS = [
    (
        1511,
        "MEASURED",
        "ORCH",
        "**An inter-channel radial-shift estimator, validated to 0.045 px.** Sub-pixel "
        "translation of R and of B against G by phase correlation on gradient magnitude "
        "over 128 px windows, projected onto the radial direction from the optical centre. "
        "Positive control is an **integer pixel roll**, which moves data without "
        "resampling and therefore cannot change sharpness: over planted shifts of -2, -1, "
        "0, +1, +2 px with n=40 windows each, max recovery error **0.045 px**. The control "
        "also caught a **full sign inversion** in the estimator's own convention (first run "
        "recovered `-planted`); uncaught, it would have inverted every conclusion below. "
        "The **tangential** component is retained as a built-in noise gauge, since lateral "
        "CA cannot produce one: measured floor **0.033-0.051 px**.",
    ),
    (
        1512,
        "MEASURED",
        "ORCH",
        "**The shipped lateral-CA correction has the right radial shape and a scalar gain "
        "of 1.444 -- it over-corrects by ~44 %.** On M114's byte-controlled `off.tif` vs "
        "`on.tif` pair, with `needed = -R_off`, `applied = R_on - R_off`, `gain = applied "
        "/ needed` (a correct correction gives 1.0): median **1.444**, range **1.381 - "
        "1.505** across seven rings from r=0.25 to r=0.83, 33-240 windows per ring. Peak "
        "red displacement before correction **-0.155 px** at r=0.45; median residual after "
        "correction **0.047 px**, versus a tangential noise floor of ~0.040 px. Implied "
        "single-scalar fix **x0.692**; note **1/sqrt(2) = 0.7071** lies inside the measured "
        "spread, so a normalisation discrepancy between where the coefficient is fit and "
        "where it is applied should be sought **before** any fitted scalar is shipped.",
    ),
    (
        1513,
        "MEASURED",
        "ORCH",
        "**ORCH's own fact 1501 is REFUTED: the CA gain error is flat in radius, so it is "
        "not an extrapolation error.** Fact 1501 hypothesised that the visible fringing "
        "sits past the fit's outer support (r=0.788) and that the correction therefore "
        "over-extrapolates there. Measured gain **inside** support **1.453** (n=6 rings) "
        "versus **outside** **1.381** (n=1 ring): a difference of **-0.072**, i.e. flat, "
        "and if anything slightly *better* outside. **Extending the fit's radial support "
        "would not fix this; rescaling the coefficient would.** A scalar gain error and a "
        "shape or extrapolation error call for different fixes, and the two are separated "
        "by exactly this test.",
    ),
    (
        1514,
        "ARGUED",
        "ORCH",
        "**A gain of 1.444 mechanically explains M107's `RECOLOURED, NOT REMOVED` and its "
        "75.1 % keep-sign failure against a >90 % bar.** Over-correcting a displacement by "
        "1.44x does not shrink the fringe -- it **flips its sign** and leaves it at ~44 % "
        "of the original amplitude. By eye the fringe changes colour and does not go away; "
        "a keep-sign statistic is precisely what a sign flip destroys. **M107's bar was "
        "correct and was reporting a real defect**; the defect is a gain, not a model "
        "failure. Falsifiable: re-render with the red coefficient x0.692 and the median "
        "residual must drop from 0.047 px to below the 0.040 px tangential floor.",
    ),
    (
        1515,
        "MEASURED",
        "ORCH",
        "**No claim is supported about the blue channel's lateral CA in this scene.** "
        "**0 of 10** rings have a blue radial displacement clearing 1.5x the tangential "
        "noise floor (B_off spans -0.011 to +0.053 px against a floor of 0.033-0.051 px). "
        "The numbers hint that the blue correction may push the wrong way (B_off +0.044 -> "
        "B_on +0.067 at r=0.45) but this is **under the floor** and must not be cited in "
        "either direction. Resolving it needs a target with more blue-channel edge content "
        "or a lower-noise estimator.",
    ),
    (
        1516,
        "MEASURED",
        "ORCH",
        "**A CA metric passed its null and still could not see CA.** Scoring lateral CA by "
        "the anti-correlation of the (R-G) and (B-G) residuals at edge pixels gave a "
        "plausible radial table and a clean null (median change **-0.06 %** over 180 "
        "windows at r=0.045, worse in 46 % of windows -- a coin flip). It then **failed a "
        "positive control**: planting more lateral CA moved it in the *wrong direction*, "
        "non-monotonically. Diagnosis -- the statistic reads **-0.778 at the optical "
        "centre**, where lateral CA is zero by construction, so it was dominated by scene "
        "hue structure. The plant was confounded too: bilinear resampling blurred R and B "
        "while leaving G sharp, so the plant changed sharpness and the metric answered "
        "about sharpness. **Both defects had one root: the statistic was a proxy.**",
    ),
    (
        1517,
        "MEASURED",
        "M114",
        "**The CA switch reaches the renderer, and the arm control is byte-exact.** Five "
        "arms over 299 frames from one frozen alignment sidecar (311 of 311 placements "
        "identical to the reference run): `unset`, `unset2`, `zero` (`CA='0'`) and `off` "
        "(`CA='off'`) all produce **sha256 E400A63A...**, while `on` "
        "(`CA='a7c2-fe100gm-2xtc-x4cpl'`) produces **E9580E8A...**. Independently "
        "corroborated by ORCH's own MD5s. This establishes three things at once: the "
        "switch is plumbed, the difference is **not run-to-run noise** (`unset2` is "
        "byte-identical to `unset` across two separate 55 s runs), and **strength-0 is a "
        "true no-op** rather than a differently-parameterised always-on path.",
    ),
]

NEW_DISCS = [
    (
        772,
        "**A null is not validation. A metric that always returns zero passes a null.** "
        "ORCH's first CA metric had a textbook null -- median change -0.06 %, worse in "
        "46 % of windows, at the one radius where the effect is zero by construction -- and "
        "was nonetheless blind to the effect it was built to measure (fact 1516). A null "
        "shows the instrument is **quiet**; only a planted effect of known size shows it "
        "can **respond**. Register both, and register the positive control's pass bar "
        "before running it.",
    ),
    (
        773,
        "**Plant a geometric effect with an INTEGER shift.** A plant that resamples also "
        "blurs, so a metric with any sharpness sensitivity will answer about the blur "
        "rather than the geometry -- which is exactly how ORCH's bilinear CA plant "
        "produced a wrong-signed, non-monotonic response (fact 1516). An integer roll "
        "moves data without touching its spectrum. This is the same principle as "
        "registering paired crops by integer-only shifts, applied to the plant rather than "
        "to the measurement.",
    ),
    (
        774,
        "**Read an estimator's sign convention off its control; never assume it.** ORCH's "
        "phase-correlation estimator recovered `-planted` on first run. The magnitude was "
        "excellent (0.045 px) and every downstream number would have been perfectly "
        "precise and exactly backwards -- reporting a correction that works as a "
        "correction that causes the defect. A control that plants a **signed** quantity "
        "detects this; one that plants only a magnitude does not (fact 1511).",
    ),
    (
        775,
        "**Measure the physical quantity, not a proxy for it -- and disqualify any proxy "
        "that is non-zero where the quantity is zero by construction.** Lateral CA *is* a "
        "radial displacement between channels, measurable in pixels; scoring it by chroma "
        "residual correlation was a proxy that read -0.778 at the optical centre. That "
        "single number was sufficient to disqualify the metric and it was visible in the "
        "very first run, before any comparison was made (fact 1516).",
    ),
    (
        776,
        "**Separate a scalar gain error from a shape error by asking whether the error is "
        "flat in the independent variable.** ORCH assumed a radial-shape failure past the "
        "fit support; the gain measured 1.453 inside and 1.381 outside, which is flat, "
        "which means a coefficient is wrong rather than a model (fact 1513). The two "
        "diagnoses lead to entirely different work -- a new capture campaign versus a "
        "one-line rescale -- so the test is worth running before either is scheduled.",
    ),
    (
        777,
        "**Build the noise floor into the instrument from a component the physics "
        "forbids.** Lateral CA is radial, so the **tangential** displacement the same "
        "estimator returns is a direct, in-band, same-window measurement of the "
        "estimator's own error -- no separate null capture, no synthetic noise model, and "
        "it travels with every measurement automatically. Any radial number that fails to "
        "clear it is not signal, which is how fact 1515 refused a tempting blue-channel "
        "claim from the same table that supported the red one.",
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
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "fold text contains 0x%02X" % o

raw2 = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert raw2 != raw, "fact insertion did not land"
raw3 = raw2.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert raw3 != raw2, "discipline insertion did not land"

# Mark 1501 refuted in place, anchored on the COMPLETE line (discipline 768).
assert f1501.endswith(" |"), "fact 1501 line does not end as a table row"
marked = f1501[:-1] + "**REFUTED by fact 1513: the CA gain error is flat in radius " \
                      "(1.453 inside the fit support vs 1.381 outside), so this is a " \
                      "scalar coefficient error, not an extrapolation error. Do not " \
                      "schedule capture work against this hypothesis.** |"
raw4 = raw3.replace(f1501, marked, 1)
assert raw4 != raw3, "fact 1501 refutation marker did not land"
assert raw4.count("REFUTED by fact 1513") == 1, "refutation marker not unique"

for fid, _, _, _ in NEW_FACTS:
    assert raw4.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw4.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw4)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("marked fact 1501 REFUTED in place")
