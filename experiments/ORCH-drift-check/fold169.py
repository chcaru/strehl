"""ORCH fold 169: M105b-exposure-ship (the agent labelled M101-defect).

The quantisation hazard is broader than ORCH stated: it is not confined to
differencing estimators. Plus a fabricated citation the agent found in its own
report, and a gate that inverted the discipline it was built to honour.

Source: docs/research/M105b-exposure-ship.md (commits 5db2da4, e97a918).
"""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PATH = "docs/research/SYNTHESIS.md"

with open(PATH, encoding="utf-8") as fh:
    text = fh.read()

orig = text

NEW_FACTS = """| 1765 | MEASURED | M105b | **THE QUANTISATION HAZARD IS NOT CONFINED TO DIFFERENCING ESTIMATORS: ANY STATISTIC THAT AVERAGES OVER MANY SAMPLES INHERITS IT.** ORCH broadcast fact 1712's **16x** under-report as a property of split-half, frame-difference and paired estimators, which define noise as what differs between samples. M105b reproduced the effect on an instrument that contains **no differencing estimator at all**: at 14-bit, quantisation displaces `p99.9` **79x** further than matched-RMS dither, on both subjects. **The mechanism it measured is the general one.** Expressed as the fraction of the 1-Lipschitz sup-norm bound actually attained, random dither collapses **0.81 -> 0.009** as independent errors average over the **8,241** samples above the rank, while quantisation stays scattered at **0.16-0.97** because value-deterministic error moves that whole population **together** and therefore never averages down. ORCH's 16x sits inside M105b's range. **Averaging is the vulnerable operation; differencing was merely the first example found.** |
| 1766 | MEASURED | M105b | **A PASSING PREDICTION DOES NOT AUDIT ITS OWN JUSTIFICATION.** M105b pre-registered that ORCH's 16x result *would not* reproduce on its instrument, **because a rank statistic is not a noise estimator**. The registered ordering was confirmed and **the stated reason was refuted**: the effect reproduced at 79x, and did so for a reason -- non-averaging of value-deterministic error -- that has nothing to do with whether the statistic estimates noise. Had M105b banked the correct prediction it would have carried a false mechanism forward under the protection of a green pre-registration. Separately, M105b registered a **caveat against ORCH's replacement guidance** -- that dose-response would be non-monotone for rank statistics -- and **its own data killed it**: Spearman gap **0.0088 / 0.0044** against a pre-registered threshold of **0.15**. |
| 1767 | MEASURED | M105b | **A REPORT CITED A COMMIT HASH THAT NEVER EXISTED, AND IT WAS THE ONE THE AUTHOR FELT TOO SURE OF TO CHECK.** M105b cited `dcb9e8d` for a commit it had made **ten minutes earlier**; the real hash is `be627db`. **Six other cited hashes in the same report were correct** -- so the failure was not carelessness across the board but a single recall that felt too recent to verify. It built `13-verify-citations.ps1` to resolve every cited hash, with a negative control proving the exception list cannot conceal an unlisted bad hash. **The gate's first run then inverted the discipline it was built to honour:** it returned **TOOL** for what was a **SUBJECT** failure, because PowerShell's `ErrorActionPreference='Stop'` promotes git's stderr into a terminating error, so a genuine bad-hash detection was misreported as the checker breaking. |
| 1768 | MEASURED | M105b | **A RATIO WHOSE DENOMINATOR IS A NULL MUST BE DIVIDED BY AN ULP COUNT BEFORE IT IS QUOTED.** M105b's largest measured under-report was **336x** and **it refused to publish it**, because the null arm of that ratio is **0.2 of a single float32 ulp** -- i.e. the denominator is not a small measurement but the absence of one, and the ratio's magnitude is set by floating-point representation rather than by the effect. Related, from the same sweep: **two different doses returned one identical answer** (6-bit and 4-bit both `+5.942e-03`) because the quantity `p0` landed on `21/63` and `5/15`, **both exactly 1/3** -- a grid collision, not a plateau, and it was the *second subject* acting as control that established which. |
| 1769 | MEASURED | M105b | **M105b'S OWN CLEARANCE SURVIVES WITH SIX BITS OF HEADROOM, AND THE EXPOSURE-GATE NESTING IS ABSENT BY DESIGN.** Its estimator `stops = log2(0.90/p99.9)` has **one** measured term and it is an **order statistic**, so the perturbation lands in `p` alone; order statistics are **1-Lipschitz** in sup-norm, confirmed in all 28 cells. On a dose ladder from 3 to 16 bits across two real renders, `dstops = 0.0000` at both real steps and the **first movement appears at 8-bit against a 14-bit sensor**. Controls: null exact, a planted +/-1 stop recovered exactly, 4-bit moves **-0.03** (quiet, not dead). On ORCH's nesting hazard, M105b read source rather than assuming: `merge_cmd.rs:3358-3398` places exposure at **top level of the writer with no alignment conditional**, so it cannot be made inert by `STREHL_ALIGN=0`, **the no-op path announces itself**, and a hash confirms `v4-exp1` != `v4-exp0`. **M100 designed against the hazard before it had a name.** |
"""

NEW_DISCIPLINES = """912. **A CORRECT PREDICTION LICENSES THE ORDERING, NOT THE MECHANISM -- STATE WHICH ONE YOU TESTED.** Fact 1766: M105b's registered direction was right and its registered *reason* was wrong, and only checking the reason separately revealed it. **A pre-registration that binds only the outcome will certify a false mechanism as confirmed**, and that mechanism then propagates as though it had been measured. Register the expected *reason* alongside the expected result, and when the result lands, ask explicitly whether the mechanism it landed by is the one you named.
913. **DO NOT QUOTE A RATIO WITHOUT ASKING WHAT ITS DENOMINATOR IS MADE OF.** Fact 1768: a **336x** under-report was set by float32 representation, because its null arm measured **0.2 ulp** -- the denominator was an absence, not a quantity. The check is arithmetic and takes seconds: **express the denominator in ulps of its own dtype**, and if it is order-unity, the ratio is reporting your number format. The same sweep's identical answers at two doses came from a **grid collision** (`21/63` and `5/15` are both exactly 1/3), which a second subject exposed -- **so a repeated value across doses is a coincidence to rule out, not a plateau to report.**
914. **A GATE BUILT TO HONOUR A DISCIPLINE CAN INVERT IT, SO COMMISSION THE GATE ON THE FAILURE IT EXISTS TO CATCH.** Fact 1767: a citation checker's first run reported **TOOL** for a real **SUBJECT** failure, because `ErrorActionPreference='Stop'` promotes a subprocess's stderr into a terminating error -- turning a successful detection into an apparent malfunction of the detector. **Every checker must be run once against a planted instance of its target failure and required to name that failure correctly**, not merely to be non-green. And the defect that prompted it is worth its own note: **six of seven cited hashes were right, and the wrong one was the most recent** -- recency feels like verification and is not.
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


text = insert_after_fact_row(1764, NEW_FACTS, text)
text = insert_after_discipline(911, NEW_DISCIPLINES, text)

if text == orig:
    print("FAIL: no change")
    sys.exit(1)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(text)

print("fold169 OK: facts 1765-1769, disciplines 912-914")
print("  the quantisation hazard is about AVERAGING, not differencing;")
print("  and a passing prediction does not audit its own justification")
