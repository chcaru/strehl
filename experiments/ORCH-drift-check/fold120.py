"""Fold M97r's outlier mask report, which had 0 citations in SYNTHESIS.

Facts 1541-1546, disciplines 797-799.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1540 |")
disc_line = full_line(raw, "796. ")

NEW_FACTS = [
    (
        1541,
        "MEASURED",
        "M97r",
        "**THE STANDARD ROBUSTNESS MASK IS NOT A DETECTOR ON A FOCUS STACK.** A naive port "
        "of Wronski et al. HDR+ Eq. 5-9 (per-tile disagreement normalised by predicted "
        "noise) fires on **100.0 %** of tiles of a **stationary, differently-focused** "
        "scene, and separates defocus from real motion by a factor of only **1.08** (mean "
        "chi2 85.31 vs 91.80). **HDR+ assumes every frame is the same scene at the same "
        "focus, and a focus stack is the one case where that is false by construction** -- "
        "every frame legitimately disagrees wherever it is differently focused, and that "
        "disagreement **is the signal the stack exists to harvest**. A naive port fires "
        "hardest exactly where the merge is doing its job.",
    ),
    (
        1542,
        "MEASURED",
        "M97r",
        "**Low-pass filtering, the obvious remedy, makes it strictly worse -- and the "
        "reason generalises.** Since defocus is approximately a low-pass, filtering both "
        "sides 'should' make a differently-focused frame agree; instead it fires on "
        "**100.0 %** of the trap at mean chi2 **972.98**, an order of magnitude **above** "
        "the unfiltered 85.31. DERIVED: filtering shrinks the defocus residual but shrinks "
        "the noise faster, and the statistic is their **ratio**. For a step edge the "
        "filtered residual is of order `C*r_d/R` while filtered noise is of order "
        "`sigma/R`, so the ratio is `C*r_d/sigma` -- **independent of the filter radius "
        "R**. **Filtering cannot buy defocus-blindness because it rescales signal and "
        "noise together.**",
    ),
    (
        1543,
        "MEASURED",
        "M97r",
        "**The design pivot: measure DISPLACEMENT, not disagreement, because displacement "
        "is the thing defocus does not have -- except that on curved edges it does.** The "
        "unconditional displacement arm is still fooled on **60.9 %** of the trap. In "
        "edge-normal coordinates the Laplacian carries a curvature term `kappa * ds/dn` "
        "that is **collinear with the gradient**, so **a disc genuinely shrinks under "
        "blur**. This is real image formation, not an artefact, and it is why the obvious "
        "symmetry argument (blur displaces nothing) holds for a straight edge and fails "
        "for a curved one.",
    ),
    (
        1544,
        "MEASURED",
        "M97r",
        "**Entering the Laplacian as an explicit NUISANCE PARAMETER and projecting it out "
        "via its Schur complement cuts the trap response 5.7x at 0.1 % cost to motion "
        "sensitivity.** Mean chi2 on the trap falls **59.17 -> 10.38** and mean "
        "displacement **0.0640 -> 0.0268 px**, while the motion plant moves 30920 -> 30886 "
        "(within noise). Any residual lying in the defocus direction is **absorbed by the "
        "third parameter and cannot inflate the displacement statistic**. This is "
        "**blindness by construction, not by tuning** -- no threshold was fitted to make "
        "the trap quiet.",
    ),
    (
        1545,
        "MEASURED",
        "M97r",
        "**The information matrix built from noisy gradients is biased upward by the "
        "noise's own variance, and the calibrated noise model makes the correction "
        "derivable rather than fitted.** `E[g2_meas] = g2_true + Var(g_noise)`; on a "
        "low-contrast tile the noise term (0.5*var_b = 8) exceeded true gradient energy "
        "(0.165) by **48x**, so the matrix was almost entirely noise. Symptom: the "
        "statistic read **0.50** where the null is 1.00, because the inflated matrix "
        "shrank the estimate toward zero -- **classical regression dilution** -- which "
        "also made the abstention guard measure noise instead of signal. The four bias "
        "terms follow from the noise model (`gxx`/`gyy`: 0.5*var_b; `gll`: 20*var_b; "
        "cross terms: 0 by disjoint samples; Laplacian rhs: 4*var_b). **Subtracting them "
        "moved a planted 1.0 px translation from 0.9934 px to 1.0000 px** -- landing on "
        "known ground truth to four decimals is the evidence it is the *right* correction "
        "and not merely a helpful one.",
    ),
    (
        1546,
        "MEASURED",
        "M97r",
        "**Final configuration reaches placebo 0.0 %, trap 0.0 %, plant 100.0 %, "
        "noise-plant 0.0 % -- and IS NOT WIRED INTO THE MERGE.** Three gates each stop "
        "something the others let through: on the `faint` plant **18 of 20** informative "
        "tiles clear the magnitude bar on noise alone (reaching **2.15 px**, six times the "
        "bar), significance vetoes 14, and the resolution requirement takes the remaining "
        "4 to zero while leaving the motion plant at 100 %. **44 of 64** tiles correctly "
        "abstain on `faint` -- no information is not the same as agreement. The null is "
        "byte-identical **by construction**: `git grep outlier HEAD -- crates/` returns "
        "exactly one reference outside the module and its harness, `lib.rs:23 pub mod "
        "outlier;`. Byte-freeze 5/5 HOLD. **This is the SECOND priced, tested, committed "
        "quality instrument sitting unwired**, alongside `softgate.rs` (fact 1498).",
    ),
]

NEW_DISCS = [
    (
        797,
        "**A detector needs a TRAP it must not fire on, not only a plant it must fire "
        "on.** M97r's decisive arm is `defocus` -- the same scene at a different focus -- "
        "which a focus-stack robustness mask **must** ignore because that disagreement is "
        "the signal. The naive port passed every plant and fired on 100 % of the trap "
        "(fact 1541); the obvious fix made the trap ten times worse (fact 1542). **Neither "
        "failure is visible without an arm designed to stay silent.** A placebo shows the "
        "instrument is quiet on nothing; a trap shows it is quiet on something that looks "
        "exactly like the target and is not.",
    ),
    (
        798,
        "**When a nuisance effect is collinear with your signal, enter it as an explicit "
        "parameter and project it out; do not filter it and do not tune around it.** "
        "Filtering failed because it rescaled signal and noise together (fact 1542), and "
        "thresholding failed because a 0.027 px defocus bias is **10 sigma** significant "
        "when gradients are large. Adding the Laplacian as a third fitted parameter and "
        "taking the Schur complement made the statistic **structurally unable** to express "
        "the nuisance direction (fact 1544). **Blindness by construction survives a change "
        "of scene; blindness by threshold does not.**",
    ),
    (
        799,
        "**Debias any information matrix estimated from noisy measurements, and validate "
        "the debias against known ground truth rather than against plausibility.** "
        "`E[g2_meas] = g2_true + Var(g_noise)` inflated M97r's matrix by 48x on a "
        "low-contrast tile and shrank the estimate to half the null (fact 1545). The "
        "correction is credible **because it moved a planted 1.0 px translation to 1.0000 "
        "px**, not because it improved a score. A correction that merely improves a number "
        "is indistinguishable from a tuned one; a correction that lands on a known truth "
        "to four decimals is not.",
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
