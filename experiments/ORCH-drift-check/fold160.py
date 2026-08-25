"""ORCH fold 160: M115-deconv-headroom.

Two results, either of which would justify the milestone:

  1. The deconvolution headroom is a NULL. The external reviewer's proposal to
     make multi-frame Wiener deconvolution the CORE of the merge is refuted on
     this rig's own data. "Do not build the Wiener merge."

  2. ORCH's ratio-compression claim is REFUTED -- the THIRD independent
     refutation of the same broadcast triage rule, on a third axis.

Plus a mechanism nobody in the fleet had: quantisation error is CORRELATED
across frames, so the noise estimators are the instrument the hazard disables.
"""
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1731 | MEASURED | M115 | **THE DECONVOLUTION HEADROOM IS A NULL: `1.0014 +/- 0.0184`. DO NOT BUILD THE WIENER MERGE.** The external review's third-ranked proposal -- *"elevate multi-frame deconvolution to the core ... at this rig's magnification it is the only path to actual sharpness"* -- is **refuted on the owner's own captures**. The estimator is not merely quiet: it is **commissioned**, recovering planted effects at **0.9938-0.9974** through the same channel that reads 1.0014 on the real data, so it demonstrably **can** respond. Its verifier runs **34/34 GREEN** and was itself commissioned at **13/13 planted defects caught**. Commit `82b82e9`. This is the most expensive single idea in the external review and it died on contact with data, which is what rule 12 exists for. |
| 1732 | MEASURED | M115 | **ORCH'S `SMALL-OVER-LARGE RATIOS COMPRESS TOWARD 1` IS REFUTED, AND THE TRUTH IS WORSE THAN THE CLAIM.** A band SNR is a power ratio, so a common floor `q` factorises **exactly**: `SNR_A/SNR_B = (P_sig_A/P_sig_B) * ((P_noise_B+q)/(P_noise_A+q))`. **`q` acts only on the noise factor**, so the ratio tends to the **signal-power ratio**, not to 1. Measured with a monotone dose-response positive control (an estimator that always answered `no compression` would pass a null perfectly): beta = **1.0000 / -0.0697 / -0.5674 / -0.8639 / -0.9966 / -1.0130** at doses 0 / 0.25 / 1 / 4 / 32 / 128 x median `P_noise`, asymptote **-1.0186**. **That is a SIGN REVERSAL, not a compression**: the ordering inverts and the log-spread **widens**, +/-1.886 -> +/-2.810. **A shared degradation hands you a confident WRONG RANKING, not a clean null.** Mechanism: contrast and SNR are anti-correlated across the arm set (`MEAN` has the highest SNR, **182.2**, and the lowest `P_sig`). |
| 1733 | MEASURED | M115 | **QUANTISATION ERROR IS NOT NOISE -- IT IS CORRELATED ACROSS FRAMES, SO THE NOISE ESTIMATORS BOOK IT AS SIGNAL.** Rounding is **deterministic in the pixel value**, so every frame of one scene receives the *same* rounding error where it has the same value: cross-half **r = +0.5109** for an 8-bit narrowing against **r = -0.0007** for an independent dither **of identical injected power (2.581e4)**. The consequence is measured and large: the narrowing raises `P_noise` **x3.937** while the equal-power dither raises it **x63.311** -- **a 16x difference in measured noise from the same injected power** -- because split-half, frame-difference and paired estimators credit the correlated half to `P_sig` (x1.262 vs x1.022). **A narrowed dataset therefore looks LESS noisy than it is, and the instrument best placed to catch the hazard is the one the hazard disables.** This was absent from ORCH's triage list and inverts its implication. |
| 1734 | MEASURED | M115 | **M115'S OWN HEADLINE SURVIVED THE ATTACK IT INVITED ON ITSELF.** ORCH's refuted claim (fact 1732) implicated M115 directly -- **its headline is a ratio near 1 reporting a null**, precisely the shape the claim said an artefact takes. Rather than dismiss it, M115 measured it. The dose sweep predicted **beta = -0.8515** at the narrowing's dose; the measurement returned **+0.5861**, and M115 chased the discrepancy instead of banking the favourable half: **H1 (calibration confound) ruled out** -- pinning `s` moved beta by **0.0071**; **H2 (correlated rounding) confirmed** (fact 1733). Inputs were then verified un-narrowed, and **even granting the adverse beta = 0.586, 1.0014 back-solves to 1.0024** -- still null. **A milestone that tests the objection which would destroy its own result, and reports the number that did not fit, is the standard.** |
"""

NEW_DISCIPLINES = """885. **THE SYNTACTIC SHAPE OF A STATISTIC PREDICTS NOTHING ABOUT ITS EXPOSURE. THIS IS THE THIRD INDEPENDENT REFUTATION AND THE RULE IS WITHDRAWN ENTIRELY.** ORCH broadcast a two-question triage -- *is it absolute?* and *does it divide small by large?* -- to the whole fleet. It has now been refuted on three separate axes by three milestones that did not consult each other: **V-M113** (what matters is whether the statistic reads pixel VALUE or feature POSITION -- location statistics dither, dispersion statistics absorb); **M111** (protection depends on the **term disparity** `D`, and a defect-detection contrast is a strong term over a weak one *by construction*, so the rule false-cleared exactly the statistics the fleet was writing); and **M115** (fact 1732 -- a common floor drives a power ratio to the **signal-power ratio**, which can be a sign reversal with *widened* spread). **Do not triage by the form of the expression. Derive what the perturbation does to your specific estimator, or measure it with a dose-response control.**
886. **A SHARED DEGRADATION IS MORE DANGEROUS THAN AN INDEPENDENT ONE, BECAUSE IT SURVIVES THE CANCELLATION YOU ARE RELYING ON.** The intuition that a two-arm ratio on the same data is self-protecting assumes the degradation is common **and cancels**. Fact 1732 shows a common floor does not cancel out of a power ratio -- it cancels out of the *signal* factor and concentrates in the *noise* factor, which is the one carrying the answer. **When you argue cancellation, expand the expression algebraically and see which factor the perturbation actually lands in** (this is the same medicine as the `|B-Y|` control that carried an explicit `R` term).
887. **BEFORE TRUSTING A NOISE ESTIMATOR, ASK WHETHER YOUR CONTAMINANT IS CORRELATED ACROSS THE SAMPLES IT DIFFERENCES.** Fact 1733 is the general case: split-half, frame-difference and paired estimators all measure noise **as the part that differs between samples**, so any contaminant that is *deterministic in the signal* is invisible to them and is booked as signal. Quantisation is the instance the fleet met; fixed-pattern noise, dust, hot pixels and a stuck warp are others. **Injecting equal-power random dither is NOT a valid model of quantisation** -- measured, the two differ 16x in the quantity being estimated.
888. **A POSITIVE CONTROL MUST BE MONOTONE-DOSED, NOT BINARY.** M115 tested a claimed law by sweeping the dose across **six** levels plus the analytic asymptote (fact 1732), which is why it could report the *shape* -- monotone approach to a sign reversal -- rather than merely `effect / no effect`. A single-dose control cannot distinguish `no effect` from `an effect my estimator saturates on`, and it cannot recover a law. **When you are testing a proposed general rule rather than a single hypothesis, the control has to have an axis.**
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    eol = txt.index("\n", i)
    return txt[: eol + 1] + block + txt[eol + 1 :]


text = insert_after_fact_row(1730, NEW_FACTS, text)

m = re.search(r"^884\. .*?(?=\n\d+\. |\n## )", text, re.S | re.M)
assert m, "discipline 884 not found"
text = text[: m.end()] + "\n" + NEW_DISCIPLINES.rstrip() + text[m.end() :]

# ---------------------------------------------------------------- assertions

assert text != orig, "no change"
for n in (1731, 1732, 1733, 1734):
    assert text.count(f"| {n} | MEASURED | M115 |") == 1, f"fact {n}"
for n in (885, 886, 887, 888):
    assert re.search(rf"^{n}\. \*\*", text, re.M), f"discipline {n}"

for line in NEW_FACTS.strip().split("\n"):
    assert line.count("|") == 5, f"pipe count {line.count('|')}: {line[:80]}"
    stripped = re.sub(r"`[^`]*`", "", line)
    assert stripped.count("**") % 2 == 0, f"bold imbalance: {line[:80]}"

# The deconv null must be stated with its commissioning, or it is just a quiet
# instrument -- the exact defect discipline 887 warns about.
i1731 = text.index("| 1731 |")
row1731 = text[i1731 : text.index("\n", i1731)]
assert "0.9938-0.9974" in row1731, "1731 must carry the positive control"
assert "13/13" in row1731, "1731 must carry the verifier commissioning"

# The withdrawal must name all three refutations, or it reads as one dissent.
i885 = text.index("885. **THE SYNTACTIC SHAPE")
seg885 = text[i885 : text.index("\n886.", i885)]
for m_ in ("V-M113", "M111", "M115"):
    assert m_ in seg885, f"discipline 885 must cite {m_}"
assert "withdrawn" in seg885.lower(), "885 must withdraw the rule"

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold160 OK: facts 1731-1734, disciplines 885-888")
print("  DECONV HEADROOM IS NULL -- reviewer proposal #3 refuted")
print("  ORCH triage rule WITHDRAWN after a third independent refutation")
