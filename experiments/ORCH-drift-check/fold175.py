"""ORCH fold 175: M110 withdraws item 89 -- the control manufactured the finding.

The excess-over-null and the raw statistic disagreed IN SIGN. The dither
finding was broadcast as a measurement hazard; M110 applied it to null
CONSTRUCTION, which is a domain I did not name.

Source: docs/research/M110-sheet.md section 26 (commit 3ead6ac).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1785 | MEASURED | M110 | **A CONTROL MANUFACTURED A FINDING, AND THE EXCESS-OVER-CONTROL DISAGREED WITH THE RAW STATISTIC IN SIGN.** M110 withdrew its own item 89, the *"+3.35 pp step in the outermost decile"* of `flat-on-ruler-cpl`. **The step does not exist.** With no control subtracted the statistic *falls* by **2.02 pp** in that bin (13.68 to 11.66), continuing a monotone decline running from `r = 0.30` outward; the excess rose only because **the null collapsed by 5.37 pp** in the same bin. `bee-3-cpl` is the same shape (raw 0.31 down, null 1.02 down). **Mechanism:** `ca_overshoot.py:158-163` builds the inert null by injecting `rng.normal(0, rms)` with a **single global rms**, whose sign-flipping efficacy decays as chroma grows toward the corner -- so **the control has its own radial profile along the exact axis being binned.** The correction it stands in for is a lateral-CA resample, **deterministic in position**, which is neither independent nor additive nor globally scaled. The companion claim, item 88, **strengthens** on the same re-read: across the bin holding `r = 0.788` the raw step is **+0.05 pp** on `bee-3-cpl` and **0.54 pp** down on `flat-on-ruler-cpl`, so **the no-kink-at-the-support-edge result never used the invalid control at all.** |
| 1786 | MEASURED | M110 / ORCH | **THE DITHER FINDING GENERALISES FROM MEASUREMENT TO NULL CONSTRUCTION -- A DOMAIN THE BROADCAST DID NOT NAME.** Fact 1765 established that value-deterministic error moves a whole population together while independent random error averages away. **ORCH broadcast that as a hazard to noise *estimators*.** M110 applied it instead to the *control*, and found the same asymmetry: an additive-random null cannot stand in for a **spatially coherent, deterministic** treatment, because the two differ in **correlation length, edge concentration, and radial profile**, and any one of the three can produce an excess where the data has none. **This is the second independent control failure in the same report family** -- the first was algebraic leakage of an `R` term into a `\\|B-Y\\|` control, M110's own item 41 in its local numbering -- reached by a different mechanism and caught by a different instrument. **The recurring object is the control, not the estimator.** |
"""

NEW_DISCIPLINES = """924. **REPORT THE RAW STATISTIC BESIDE EVERY EXCESS-OVER-CONTROL, IN THE SAME TABLE.** Fact 1785: the excess said *step up*, the raw statistic said *falling*, and **they disagreed in sign** -- so the direction of the reported effect was entirely the control's. One extra column would have caught the withdrawn item before it was sent, and the same column showed the surviving item was **stronger** than its author had claimed. A control is a subtrahend, and **a subtrahend with structure of its own is indistinguishable from a result** unless the minuend is printed next to it.
925. **A CONTROL THAT VARIES SYSTEMATICALLY ALONG THE AXIS YOU ARE BINNING ON IS NOT A CONTROL ON THAT AXIS.** Fact 1785: the null's efficacy decayed with radius, and the finding was reported *per radial decile*. The control was strongest where the claim was weakest and collapsed where the claim was made. **Before binning an excess along any axis, plot the control alone against that axis**; if it has a trend there, the excess inherits it and the binned result measures the control. This is the structural analogue of expanding a control **algebraically** in the terms it combines -- **expand it geometrically in the coordinate you are about to slice.**
"""


def insert_after_fact_row(n, block, txt):
    anchor = f"| {n} |"
    i = txt.index(anchor)
    j = txt.index("\n", i) + 1
    return txt[:j] + block + txt[j:]


def insert_after_discipline(n, block, txt):
    anchor = f"\n{n}. **"
    i = txt.index(anchor)
    j = txt.index("\n", i + 1) + 1
    return txt[:j] + block + txt[j:]


text = insert_after_fact_row(1784, NEW_FACTS, text)
text = insert_after_discipline(923, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold175 OK: facts 1785-1786, disciplines 924-925")
print("  the control manufactured the finding; excess and raw disagreed in sign;")
print("  the dither hazard generalises from estimators to null construction")
