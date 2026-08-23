"""Fold the fact-341 repair and what it exposed, at facts 428-431.

These are my own measurements, run after editing merge.rs/through_focus.rs, so
they are UNVERIFIED by the project's own standard and are labelled that way.
Rule 24 applies to them as much as to anything else.
"""
import re, pathlib

DST = pathlib.Path("docs/research/SYNTHESIS.md")

ROWS = [
    (428, "**MEASURED. Fact 341's defect is repaired, and the repair is worth 3.1× in the artifact it was raised against.** `predicted_sigma` now carries `SELECTION_INFLATION = 1.074` at `n = 1`. On `109MSDCF` with the **flat** ROI `2272,1344,256,256` passed as the *detail* ROI — the negative control M38 never ran — corrected gate-0 detail moves from **+35.47%** (fact 341) to **0.885× = −11.5%**. The measured flat-ROI noise ratios are **unchanged** at 1.074× / 0.973× / 0.890×.",
     "**The spurious credit is gone, and the unchanged noise column proves the merge output did not move — only the prediction did.** The constant is the measured one twice over (1.074× fact 320, 1.075× fact 23), not a fitted knob, and a test pins it there",
     "orchestrator, post-M39 — **MEASURED, NOT INDEPENDENTLY VERIFIED**"),
    (429, "**A shipped acceptance invariant was false, and its test could not have failed.** `the_merged_estimate_is_never_noisier_than_a_single_frame` asserted `merged ≤ single` at every gate, reasoning that averaging scales σ by `1/√n` and `n ≥ 1` is structural. **That reasoning is wrong at `n = 1`**: one admitted frame is not averaging, it is *selection*, and fact 320 measured selection at **1.074× a single frame**. The test passed only because `predicted_sigma` was blind in exactly the same place — **it was proving an invariant against a model that could not express its violation.**",
     "**Fifth no-power check found in this corpus, and the first inside shipped Rust rather than an analysis script.** The invariant now has two branches: `n ≥ 2` strictly beats one frame, `n = 1` is measurably worse. That is *why the gate exists* — it is the mechanism that moves pixels off `n = 1` — and why **gate 0 is a diagnostic, not a shipping configuration**. Rule 20 and discipline 253 now both have a code-side instance",
     "orchestrator — **DERIVED from facts 320/341**, test rewritten to the two-branch contract"),
    (430, "**OPEN. The repair overshoots on the flat ROI: −11.5% where a no-detail region should read ≈1.0×.** The artifact fell 3.1× in magnitude and **flipped sign**, from crediting detail that cannot exist to charging a penalty that also cannot exist. Confounded by the ROI not being strictly detail-free — the single-frame corrected reading is 14.7270, not 0, and much of the region is out of focus in the reference frame.",
     "**Do not report −4.6% … −0.5% (fact 341's revised band) as settled.** The gate-0 denominator moved again, so M38's retention figure needs re-deriving a third time. Question 101",
     "orchestrator — **MEASURED, NOT INDEPENDENTLY VERIFIED**"),
    (431, "**The `n > 1` selection penalty is unmeasured and deliberately set to 1.0.** The acceptance set at any gate is still chosen by a noise-dependent criterion, so some selection bias survives averaging. `selection_inflation(n) = 1.0` for `n ≥ 2` makes `predicted_sigma` a **floor** there, not an estimate.",
     "**Stated in the code, not just here** — the doc comment on `selection_inflation` says which branch is measured and which is assumed, so the next reader cannot mistake the assumption for a measurement. Feeds question 80",
     "orchestrator — **ASSUMED, flagged as such**"),
]

QUESTION = """101. **What should a strictly detail-free region read under the corrected detail metric, and does
     the flat ROI qualify?** Fact 430 measures −11.5% where 1.0× is the naive expectation, but the
     ROI's single-frame corrected reading is 14.7270 rather than 0, so it is low-detail, not
     no-detail. Until this is settled the gate-0 denominator is not trustworthy and M38's retention
     band cannot be quoted. **Testable, and cheap:** synthesise a genuinely flat plane at the ROI's
     mean level with the calibrated noise model, run the same metric, and read the answer directly —
     the simulator (M25) exists to make exactly this kind of question decidable. Then re-derive the
     retention band against whichever denominator survives."""


def main():
    dst = DST.read_text(encoding="utf-8").split("\n")
    cur, lastf, lastq = "", None, None
    for k, l in enumerate(dst):
        if l.startswith("## "):
            cur = l
        if cur.startswith("## 4.") and re.match(r"\| \d+ \|", l):
            lastf = k
        if cur.startswith("## 10.") and (re.match(r"\d+\. \*\*", l) or l.startswith("     ")):
            lastq = k
    assert lastf is not None and lastq is not None and lastq > lastf

    ns = set()
    cur = ""
    for l in dst:
        if l.startswith("## "):
            cur = l
        if cur.startswith("## 4.") and (m := re.match(r"\| (\d+) \|", l)):
            ns.add(int(m.group(1)))
    clash = ns & {r[0] for r in ROWS}
    assert not clash, f"fact collision {clash}"

    block = [f"| {n} | {f} | {c} | {s} |" for n, f, c, s in ROWS]
    dst = dst[: lastq + 1] + QUESTION.split("\n") + dst[lastq + 1 :]
    dst = dst[: lastf + 1] + block + dst[lastf + 1 :]
    DST.write_text("\n".join(dst), encoding="utf-8")
    print("added facts 428-431, question 101")


main()
