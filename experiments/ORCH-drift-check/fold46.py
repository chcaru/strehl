"""Fold M104 (ex-M98) Phase 1. Facts 1305-1309, disciplines 642-644.

Includes a correction to the orchestrator's own fact 1287: the synthetic
Catmull-Rom gather in resample_budget.py overshoots the operation's real cost
by +0.060 dex, because it was measured on a single rawpy frame rather than on
the render the operation is actually applied to. The registered bar for M95
moves from +0.1301 to about +0.19 -- revised BEFORE the fix lands and before
any post-fix number exists.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1305, "**ON THE RULER STACK, 97.0% OF THE HIGH-FREQUENCY DEFICIT IS THE RESAMPLE, WITH NOTHING LEFT FOR WARP, "
           "MERGE OR DECODER.** M104 measured a pre-fix ruler deficit of **+0.1623 ± 0.0040 dex (1.4530x) at "
           "40.44σ**, then planted the aligner's own scale factor **1.030078** through a true Catmull-Rom gather on "
           "the *unregistered* render and reproduced **+0.1574 ± 0.0042**. Remainder **0.66σ**.",
     "A near-total accounting on an independent chain: M104 recovers the aligner's `k` from a photograph at "
     "**1.59σ**, and -- more impressively -- from `bee-3-cpl` at **0.77σ with no ruler in the frame at all**, which "
     "is its P10 confirmed at **7.5x tighter standard error** on the owner's actual subject. The instrument was "
     "admitted on **7/7 controls**: SELF exactly `1.000000000`, a planted `1.030000` rejected at **25.34σ** by the "
     "very bar the post-fix render must pass, and **DIM** holding `1.0014`/`1.0019` across *changed output "
     "dimensions* -- which matters because the fix changes the output dimensions and would silently mis-register any "
     "instrument that assumed 7032x4688.",
     "M104 (MEASURED, 7/7 controls); `docs/research/M104-*.md`, commits `599a6e0`, `50808ad`, `e1d22ba`"),

    (1306, "**THE RESAMPLE'S COST DOES NOT SCALE WITH THE ENLARGEMENT; IT IS ONE RECONSTRUCTION PASS SET BY THE "
           "INPUT GRID.** M104 swept a **15x dose range** and measured **+0.159 / +0.157 / +0.179 / +0.181 dex** -- "
           "essentially flat. A pure crop loses nothing.",
     "Refutes the intuitive model, including the orchestrator's, that a bigger stretch costs proportionally more. "
     "The damage is done by *reconstructing the signal on a new grid at all*, and the magnitude of the shift is "
     "nearly irrelevant. Two consequences: **reducing the enlargement is worth almost nothing -- it must be removed** "
     "(a 7% stretch and a 100% stretch cost about the same), and any future pipeline stage that resamples 'only a "
     "little' should be treated as costing full price. This also retires the orchestrator's fact-1288 reasoning that "
     "separate resampling costs can be reasoned about additively.",
     "M104 (MEASURED, dose sweep, P4); `docs/research/M104-*.md`"),

    (1307, "**THE RESAMPLE'S COST IS ENTIRELY HIGH-FREQUENCY, WHICH IS HOW A +7.35% ENLARGEMENT SURVIVED "
           "UNDETECTED.** M104 measured the cost as a **null at the comb** and **+0.1623 dex near Nyquist**. Any "
           "metric that averages over frequency dilutes it to nothing.",
     "This is the mechanism of the project's own blindness, stated as a measurement. A global sharpness or "
     "gradient-energy number integrates across the band, and a defect living only in the top octave is invisible "
     "there -- which is consistent with fact 1273's three independent deaths of whole-frame gradient energy as an "
     "adjudicator, and with M87's finding that a Catmull-Rom gather destroying ~49% of gradient energy moved the "
     "halo metric by **+0.6%**. **Any bar on sharpness must be stated in a named frequency band**, and a claim of "
     "'no measurable difference' from a band-averaged metric is not evidence of absence.",
     "M104 (MEASURED, P5); corroborates facts 1273, 1287"),

    (1308, "**ON `bee-3-cpl` THE RESAMPLE IS A MEASURED NULL, BECAUSE REGISTRATION'S GAIN AND THE RESAMPLE'S LOSS "
           "CANCEL.** M104: **+0.0229 ± 0.0419 dex, 0.55σ**. The stack where the enlargement is worst is the stack "
           "where its cost is masked by the benefit of the very operation that causes it.",
     "A genuinely adversarial result for anyone trying to demonstrate the defect on the owner's headline subject, "
     "and an explanation for why this was hard to see: **the two effects are confounded by construction**, since the "
     "coverage crop exists *because* registration moved the frames. It also means a naive A/B of "
     "aligned-and-rescaled against unregistered on this stack reads as no difference, and would license exactly the "
     "wrong conclusion. The fix must therefore be scored as *registration kept, rescale removed* -- a third arm that "
     "neither side of the naive comparison contains.",
     "M104 (MEASURED, P6); `docs/research/M104-*.md`"),

    (1309, "**THE ORCHESTRATOR'S SYNTHETIC GATHER OVERSHOOTS THE REAL COST BY +0.060 dex, SO FACT 1287'S 64.2% IS AN "
           "UPPER BOUND AND THE REGISTERED BAR MOVES.** M104 resolved prediction (j) by **direct planting** of the "
           "actual factor `1.073537`, measuring **+0.1789 ± 0.0055**. The orchestrator's `resample_budget.py` R1 read "
           "**+0.2392** (over by **+0.060**); M104's own linear extrapolation read ~**+0.385** (over by **+0.206**). "
           "**Both overshot, and M104 reported the one that indicted itself alongside the one that indicted the "
           "orchestrator.**",
     "The cause is a proxy mismatch: R1 gathered on a **single rawpy frame**, which carries more high-frequency "
     "energy than the merge, and a resample costs more on sharper input. M104 planted on the **render**, which is "
     "the image the operation is actually applied to. **Corrected accounting on the `bee-3-cpl` chain: the rescale "
     "is ~48% of the +0.3693 dex deficit, not 64.2%, and the post-fix prediction moves from +0.1301 to about "
     "+0.19 dex.** The revision is made **before the fix lands and before any post-fix number exists**, which is the "
     "only point at which moving a registered bar is legitimate; M104's own independent bars (B1-B7) were registered "
     "separately and are unaffected.",
     "M104 (MEASURED, direct planting, P-note j); corrects ORCH fact 1287; "
     "`experiments/ORCH-drift-check/resample_budget.py`"),
]

DISCIPLINES = [
    (642, "**Measure a degradation's cost on the image it will actually be applied to, not on a sharper proxy.** The "
          "orchestrator priced the coverage rescale by gathering on a single rawpy-decoded frame and read **+0.2392 "
          "dex**; M104 planted the same factor on the **render** and read **+0.1789**. A resample costs more on "
          "sharper input, so the proxy inflated the answer by 34% and, through it, a bar registered with two "
          "agents. The general form: a degradation's cost is a property of the *pair* (operation, input spectrum), "
          "never of the operation alone. Fact 1309."),
    (643, "**State every sharpness bar in a named frequency band, and never accept 'no measurable difference' from a "
          "band-averaged metric.** M104 measured the rescale's cost as a **null at the comb and +0.1623 dex near "
          "Nyquist** -- a defect living entirely in the top octave, invisible to any metric that integrates across "
          "the band. That is how a +7.35% interpolated enlargement of every pixel survived in the shipped pipeline. "
          "Corroborated from the other side by M87, where a gather destroying ~49% of gradient energy moved the halo "
          "metric by +0.6%. Fact 1307."),
    (644, "**A stem check is not a lock: it answers whether a number has been taken, not whether it is about to "
          "be.** M104 checked four registers, found `M101` free, and committed first -- and another agent claimed "
          "`M101` within the hour. It renumbered itself rather than standing on precedence, on the grounds that six "
          "renames beat a permanently ambiguous citation stem. With many concurrent agents, treat identifier "
          "allocation as racy by default and prefer yielding to arguing. M104's P10."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1304 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^641\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need 5"
        rows.append(row)

    drows = [f"{did}. {body}" for did, body in DISCIPLINES]

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1305-1309 after line {fact_idx}, disciplines 642-644 after line {disc_idx}")


if __name__ == "__main__":
    main()
