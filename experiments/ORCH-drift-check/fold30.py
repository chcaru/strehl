"""Fold 30 -- the merge kills grain and leaves mottle; photometric drift
decides elections on real data; and two of my own instruments failed their
controls before either result was believed.
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
        "| 1258 | **THE MERGE REMOVES GRAIN SUPERBLY AND LEAVES LOW-FREQUENCY "
        "MOTTLE BEHIND, WHICH IS WHY THE BACKGROUND LOOKS BLOTCHY.** In "
        "`bee-3-cpl`'s flat background (18.4% of frame, selected by the "
        "gradient of a heavily smoothed copy so the criterion cannot exclude "
        "the target), fine noise falls from **sigma/mean 0.0080-0.0139** in a "
        "single frame to **0.0011-0.0014** merged -- a ratio of **0.097x (R), "
        "0.134x (G), 0.120x (B)**, against **0.0578x** for a perfect 299-frame "
        "average. But the low-frequency excess over what iid noise predicts "
        "rises from **2.4-2.9x** in a single frame to **8.5-10.6x** merged. | "
        "This is the first direct measurement of the merge's noise performance "
        "on the owner's own photograph rather than on a flat ROI or a static "
        "burst, and it is **good**: an effective N of 56 (green) to 106 (red) "
        "frames. The defect is that averaging is efficient against pixel-scale "
        "noise and inefficient against whatever is correlated across frames, "
        "so the grain goes and the mottle is what is left to see. In absolute "
        "terms the mid-band SD fell ~2.5x; it dominates because everything "
        "around it fell 10x. The candidate mechanism is per-frame photometric "
        "drift printed through the election map, which is fact 1259 and is "
        "**not** established by this measurement. | orchestrator (MEASURED); "
        "`experiments/ORCH-drift-check/mottle2.py`, instrument validated by "
        "placebo -- recovers planted sigma to 0.1%, reads 1.000x on pure iid "
        "noise and 3.61x on a planted sigma-6 blob |"),
    check(
        "| 1259 | **PHOTOMETRIC DRIFT DOES NOT MERELY TINT THE OUTPUT, IT "
        "DECIDES WHICH FRAME WINS -- SO NORMALISATION MUST PRECEDE THE FOCUS "
        "MEASURE, NOT THE MERGE.** `focus.rs` already asserts in CI that a "
        "per-frame gain `g` moves the normalised focus response by **sqrt(g)** "
        "(with a positive control that the *unnormalised* response moves by the "
        "full `g`), so the measured 1.1091x drift is a **5.31%** systematic, "
        "monotone-in-frame-index score advantage to early frames. Measured on "
        "M93's real 299-frame `bee-3-cpl` crops with an independent Python "
        "implementation of the documented formula, validated to **0.001-0.004%** "
        "against the sqrt(g) law: **86-93% of pixels have a top-1/top-2 margin "
        "smaller than the 5.31% bias**, **1.40-6.87% of pixels re-elect** under "
        "per-frame normalisation, and those that move do so by a **median of 1, "
        "1, 29 and 44 frames** out of 299. | The four ROIs show drift of "
        "1.0523x, 1.0776x, 1.1865x and **1.4585x** -- a 1.46x spread within one "
        "stack -- so a scalar per frame may not be enough and a "
        "gain(frame, position) model may be required; this is consistent with "
        "the 1/m^2 breathing mechanism but the ROI positions were not "
        "established, so that reading is ARGUED and part of plane 2's spread "
        "may simply be subject moving through focus. Sent to M99, which owns "
        "`photometric.rs`, with the instruction to site the correction where "
        "the luma plane is produced. **Not claimed:** this reproduces strehl's "
        "documented focus *response to a gain*, not its regulariser, CFA "
        "handling or gate, so the percentages are the behaviour of the formula "
        "on real data and not a bit-exact prediction of the shipped binary; "
        "and re-electing is not shown to *improve* the image, which needs a "
        "different instrument. | orchestrator (MEASURED); "
        "`experiments/ORCH-drift-check/decide.py`; null control -- a constant "
        "gain re-elected **exactly 0** pixels in all four planes, asserted with "
        "`array_equal` |"),
    check(
        "| 1260 | **A PLANT THAT CAPTURES THE ESTIMATOR'S DECISION CANNOT "
        "MEASURE THAT DECISION'S CONSEQUENCE.** To test whether per-frame "
        "brightness variation prints mottle into a selection merge, the "
        "orchestrator planted a 40% brightness ramp across the frames and "
        "required the mid-band SD to rise. It **fell** on three of four planes "
        "(-1.5% to +0.6%), and the registered positive control correctly "
        "declared the instrument blind. The cause: gradient-energy focus scales "
        "as brightness^2, so the ramp made the brightest frames win almost "
        "everywhere, collapsing the elected-index field toward a constant -- "
        "and a constant election produces no spatial mottle at all. The plant "
        "destroyed the very variability it was meant to amplify. | The null "
        "control in the same run passed perfectly (a constant gain changed the "
        "result by 0.0000%), so a run with **only** a null would have reported "
        "a clean, confident, worthless -0.1% to -1.2% effect. This is the "
        "sharpest instance yet of the rule that a null and a positive control "
        "answer different questions. It also produced fact 1259: the reason the "
        "plant captured the election is itself the finding. | orchestrator "
        "(MEASURED, negative); `experiments/ORCH-drift-check/mech.py` -- "
        "superseded, do not cite for any positive claim |"),
]

DISC = [
    "615. **A PLANT MUST NOT PERTURB THE MECHANISM IT IS MEASURING THROUGH.** "
    "A 40% brightness ramp planted to amplify a brightness artifact instead "
    "captured the election -- the brightest frames won everywhere, the elected "
    "field went constant, and the artifact vanished. The plant was applied "
    "upstream of a decision, so it changed the decision rather than the "
    "decision's consequence. Before planting, ask what the estimator does "
    "*differently* in the presence of the plant; if the answer is 'it chooses "
    "differently', freeze the choice first and plant downstream of it. "
    "(fact 1260)",

    "616. **MEASURE NOISE ON A LOCAL RESIDUAL, NEVER BY POOLING MASKED PIXELS "
    "ACROSS A FRAME.** `mottle.py` pooled `img[flat]` over a 7032x4688 frame "
    "and reported a per-channel SD that was dominated by the background's "
    "frame-wide brightness gradient, not by noise. The tell was arithmetic "
    "rather than visual: a 17x17 box blur left the SD unchanged, so the "
    "reported 'mottle' came out at exactly the box size, 17.02x, identically "
    "in all three channels. Subtract a local mean first and every statistic is "
    "about the band you intended. A number that equals a parameter of your own "
    "code is a bug report. (fact 1258)",
]

L = io.open(SYN, encoding="utf-8").read().split("\n")
i_last_disc = next(i for i, l in enumerate(L) if l.startswith("614. "))
end = i_last_disc + 1
while end < len(L) and L[end].strip() and not re.match(r"^\d+\. ", L[end]):
    end += 1
L[end:end] = [""] + [x for p in ((d, "") for d in DISC) for x in p][:-1]

ilast = max(i for i, l in enumerate(L) if l.startswith("| 12"))
assert L[ilast].startswith("| 1257 |"), L[ilast][:80]
L[ilast + 1:ilast + 1] = FACTS
io.open(SYN, "w", encoding="utf-8", newline="\n").write("\n".join(L))
print("SYNTHESIS: facts 1258-1260, disciplines 615-616")
