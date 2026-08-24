"""Fold 33 -- M96's election-margin milestone, and the joint mechanism that
links it to photometric drift and to the occlusion halo.
"""
import io
import re

SYN = "docs/research/SYNTHESIS.md"


def check(row, want=5):
    n = len(re.findall(r"(?<!\\)\|", row))
    assert n == want, "row has %d unescaped pipes, need %d: %s" % (n, want, row[:170])
    return row


FACTS = [
    check(
        "| 1262 | **THE FOCUS ELECTION IS DECISIVE, NOT A COIN FLIP, SO M93'S "
        "FRAME-REJECTION GATE HAS A WELL-DETERMINED ELECTION TO WORK WITH.** "
        "Across all 7 corpus stacks the median margin at frame-distance 8 is "
        "**0.290-0.813** of the pixel's own through-focus range against "
        "**0.022-0.127** for its paired frame-permutation placebo -- a ratio of "
        "**6.01x to 22.97x** -- and the paired win rate is **96.226% to "
        "99.952%** against a measured null band of **[22.304%, 81.134%]**. | "
        "This was pre-registered as a two-branch question and **the other "
        "branch is falsified on all 7 stacks**: had the winner routinely beaten "
        "the runner-up by less than the noise, removing contaminated frames "
        "could not have made the election decisive and the project would have "
        "needed redirecting. Because the argmax is well determined, a "
        "contaminated frame wins by being pushed *above a genuine peak*, so "
        "rejecting it hands the pixel back to a real competition. That is "
        "M93's precondition, measured on the ungated pipeline. It is **not** a "
        "benefit estimate for M93's gate. | M96 (MEASURED, 7 stacks); "
        "`docs/research/M96-election-margin.md` |"),
    check(
        "| 1263 | **25.247% OF `bee-3-cpl` PIXELS HAVE A *DISCONNECTED* "
        "COMPETITIVE SET, AND THEY ARE THIN CONTOURS ON DEPTH AND OCCLUSION "
        "BOUNDARIES.** At the shipped gate the admitted set spans two or more "
        "separated depths: mean gap **29.12 frames**, `rho` p90 = **243 of "
        "299**, max **295**. The median pixel is tight (`rho` = 1); the tail is "
        "enormous. | M96 reads these as a **correct** response to a bimodal "
        "scene rather than an undetermined election -- two genuinely different "
        "surfaces are in focus at two genuinely different frames -- and that is "
        "the distinction the merge currently cannot express, because it "
        "averages across the gap and prints one value where there are two "
        "depths. This is the occlusion-halo population, identified by a "
        "statistic rather than by eye, on the owner's own stack. | M96 "
        "(MEASURED); `docs/research/M96-election-margin.md` |"),
    check(
        "| 1264 | **PHOTOMETRIC DRIFT RE-ELECTS THE DISCONNECTED PIXELS 16.87x "
        "MORE OFTEN THAN THE CONNECTED ONES, SO NORMALISATION IS A "
        "DEPTH-BOUNDARY FIX AND NOT A TONE FIX.** Registered before running, "
        "then measured on M93's four real `bee-3-cpl` ROIs: enrichment "
        "**2.82x, 13.83x, 19.91x, 32.68x** (median **16.87x**), against a "
        "label-shuffle control of **0.93x-1.01x (median 1.00x)**. The "
        "self-consistency split is the decisive part -- among pixels that "
        "re-elect, the **disconnected** ones move a median of **35, 60, 46 and "
        "5** frames while the **connected** ones move **1, 1, 1, 1**. | This "
        "makes three separately-discovered things one object. A connected "
        "competitive set puts the runner-up next to the winner, so a small bias "
        "moves the election one frame and nothing visible happens; a "
        "disconnected set puts it across the gap, so the *same* 5.31% bias "
        "moves the election to **the wrong depth entirely**. It explains both "
        "the 1s and the 29/44s in fact 1259's table with one mechanism, it "
        "predicts that per-frame normalisation should reduce the halo rather "
        "than merely the tint, and it gives M87 a population to target that was "
        "found by statistic rather than by eye. **Caveats:** this is an "
        "independent Python implementation of the documented focus formula, not "
        "the shipped binary, and its disconnected fractions (4.20-16.69% on "
        "four ROIs) are not comparable to M96's 25.247% whole-frame figure; the "
        "threshold uses a focus-noise SD estimated from this data because "
        "`FOCUS_NOISE_SD` is not transferable across implementations. | "
        "orchestrator (MEASURED); `experiments/ORCH-drift-check/joint.py`; "
        "builds on M96 fact 1263 and orchestrator fact 1259 |"),
    check(
        "| 1265 | **AN ORDER STATISTIC OF A PER-PIXEL MULTISET CANNOT DETECT "
        "FRAME PERMUTATION, AND M96 RETIRED ITS OWN BRIEF'S METRIC FOR IT.** "
        "The metric the orchestrator specified is **bit-identical** under frame "
        "permutation -- **100.00% ties across all 7,985,600 pixels x 7 "
        "stacks** -- because permuting frames permutes the multiset without "
        "changing any of its order statistics. M96 also **retired its own B5 "
        "bar as under-powered**: at a planted delta of 0.02, where B1/B2/B3 all "
        "read NEARLY ARBITRARY, B5 still read DECISIVE, because the 17x17 "
        "regulariser manufactures index coherence. | Two lessons, both against "
        "the author's interest. The first is that a placebo can only falsify a "
        "metric that is *capable* of responding to what the placebo changes -- "
        "the same class of error as discipline 611's straightness blindness and "
        "discipline 615's captured plant, arrived at independently. The second "
        "is that a smoothing stage downstream of a statistic can make that "
        "statistic look decisive no matter what it is fed. **The orchestrator "
        "wrote the metric that failed.** | M96 (MEASURED, negative); "
        "`docs/research/M96-election-margin.md` |"),
    check(
        "| 1266 | **`FOCUS_NOISE_SD` HAS ITS FIRST INDEPENDENT CORROBORATION: "
        "AN ANALYTIC NULL BRACKETS IT AT 1.047x-1.973x ON ALL 7 STACKS.** M89's "
        "estimator runs a 5-point second difference along the **frame** axis of "
        "the focus response, normalised by its L2 norm, and needs **no fitted "
        "constant**; it carries a **4.15x-64.16x** power control. | M69 and M81 "
        "both failed to calibrate this constant and it has been load-bearing in "
        "shipped code the whole time -- `DEFAULT_GATE` is expressed in units of "
        "it. A one-sided upper bound within a factor of two, obtained without "
        "fitting anything, is the first evidence the shipped value is not "
        "arbitrary. It does not license moving it. | M96 (MEASURED, 7 stacks, "
        "one-sided); `docs/research/M96-election-margin.md` |"),
]

L = io.open(SYN, encoding="utf-8").read().split("\n")
i = max(i for i, l in enumerate(L) if l.startswith("| 12"))
assert L[i].startswith("| 1261 |"), L[i][:80]
L[i + 1:i + 1] = FACTS
io.open(SYN, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("SYNTHESIS: facts 1262-1266")
