"""Fold M18 (the sufficient-statistics seam) into SYNTHESIS.md at facts 420-427.

M18 is an implementation milestone and proposed no facts, so these are written
from its measurements by the orchestrator. Every row is MEASURED by M18 and cites
where; none is an orchestrator inference dressed as a measurement.
"""
import re, pathlib

DST = pathlib.Path("docs/research/SYNTHESIS.md")
S = "M18 §1"

ROWS = [
    (420, "**MEASURED. The through-focus statistics are provably non-perturbing.** 109MSDCF merged twice at gate 2.0, once with `--stats --stats-placebo` and once without: SHA256 `DF6C3DE2…C815EE` **both times**, byte-identical over 3516×2344×3 16-bit pixels. Two gathers, a second `box_mean` at radius 2 and a full permutation placebo moved **not one output bit**.",
     "**This is the strongest single check in the corpus, and it is the right shape for all future observers.** A statistic that claims not to affect the merge should prove it by hash, not by argument. Adopt this as the standard for every diagnostic channel strehl adds",
     f"{S} + `nostats.tif`/`withstats.tif`"),
    (421, "**MEASURED/DERIVED. The seam is two-pass, and the per-pixel state is 60 bytes, constant in the frame count.** Anchored on pass one's regularised winner `k*`, the parabola triple `(f[k*−1], f[k*], f[k*+1])` has each slot written by **exactly one** frame, so the fold is exactly commutative and associative — what `par_chunks` requires. The fine focus **volume** would be `4N` B/px: 725 MB at 22 frames, 1088 MB at 33, **3461 MB at 105**. `ThroughFocus` is **494 MB at every stack depth**.",
     "**Resolves the review's item 6, the architectural seam it said must be decided before the merge is written — and the answer is two-pass, not a fatter fold.** Break-even is 15 frames and the corpus starts at 22, so the ratchet wins everywhere it is used and the margin grows without bound",
     f"{S}"),
    (422, "**DERIVED. The posterior entropy is computed over *all* frames, not the top-k, and cannot overflow.** With `u_k = (f_k − anchor_focus)/T`, `u_k ≤ 0` **by construction** because `anchor_focus` is the max over frames, so `exp(u_k) ∈ (0,1]`. `Z = Σexp(u_k)` and `W = Σu_k·exp(u_k)` are exactly mergeable, giving `H = ln Z − W/Z`.",
     "**Necessary, not merely elegant: fact 283's p99 perplexity is 4.74, sitting exactly at the `TOP_K = 4` cap.** Anything computed from the top-k list alone is truncated precisely where it is most interesting. The temperature is fact 260's calibrated `T = √2·FOCUS_NOISE_SD`, never `std_k(f_k)`",
     f"{S}"),
    (423, "**MEASURED. The fine (r=2) focus field is 5.94× noisier than the selection field.** Over 12 SplitMix64 seeds on a 512² plane: fine r=2 sd **0.090400 ± 1.70e-4**; coarse r=13 **0.018847**; regularised r=13-then-8 **0.015214**.",
     "**The last row reproduces the shipped `FOCUS_NOISE_SD = 0.015214` exactly — the instrument check.** The same harness that measures the new constant recovers the old one, which is what licenses believing the new one",
     f"{S}"),
    (424, "**MEASURED. The fine argmax disagrees with the regularised winner at 78.081% (109MSDCF) and 79.237% (119MSDCF) of pixels — and this is not a defect.** It is a 5.94× noisier field behaving as one. The screening flag is therefore `fine_peak_outside_triple` (off by ≥2, so the parabola cannot reach it): **54.843% / 57.247%**.",
     "**Off-by-one disagreement is harmless because the triple still brackets the fine peak.** A raw-disagreement flag would have fired on four-fifths of the image and been discarded as noise; the bracketing form is the one that carries information",
     f"{S}"),
    (425, "**MEASURED/FORCED. The statistics must be gathered at 5×5, not at the 27×27 selection window.** Fact 152 measured bimodality enrichment at **4.38× at radius 2** and **0.36× — depleted — at radius 13**.",
     "**A bimodality statistic read at the selection scale measures nothing.** The cost is the noisier fine field of fact 423, and it is not optional — the two scales cannot be shared, so the merge pays for two fields",
     f"{S} + fact 152"),
    (426, "**DERIVED. The parabola is used for position and explicitly not for height.** Fact 273 gives the parabola 4.03× over argmax for *position* and disqualifies it for *height*, so height comes from a log-domain fit with baseline subtraction (`subframe_deficit`, facts 272/302/304) using the retained `floor`.",
     "**One estimator, two uses, only one of them valid — and the split is honoured in the retained state rather than in a comment.** `triple` serves position; `floor` exists solely so height never reads off the parabola",
     f"{S} + facts 272/273/302/304"),
    (427, "**PROCESS. M18's brief was stale in three of four items and saying so was the deliverable.** Items 1 and 2 were already built; the stated test baseline of 70 was actually **107**; and the acceptance target \"bring the merge under 1.0×\" was quoted against the pre-M37 binary when M38 already reached **0.890× at gate 2**.",
     "**Milestone numbering is not the order the work happened in, and a brief written before a reordering will silently ask for work already done.** Every implementation brief from here must be checked against the tree before code is written, and the check reported. Discipline 254",
     "M18 §0"),
]

DISCIPLINE = """254. **Check the brief against the tree before writing code, and report the check.** M18's brief
     asked for four things; two were already built, its stated test baseline was 70 when the tree
     had 107, and its acceptance target was quoted against a binary two milestones out of date.
     Milestone numbering is not the order the work happened in. **An agent that silently implements
     a stale brief produces a duplicate, and one that silently skips it produces an unexplained
     gap** — the deliverable is the reconciliation, in writing, before the first edit."""


def main():
    block = [f"| {n} | {f} | {c} | {s} |" for n, f, c, s in ROWS]
    dst = DST.read_text(encoding="utf-8").split("\n")

    cur, lastf, lastd = "", None, None
    for k, l in enumerate(dst):
        if l.startswith("## "):
            cur = l
        if cur.startswith("## 4.") and re.match(r"\| \d+ \|", l):
            lastf = k
        if cur.startswith("## 5.") and (re.match(r"\d+\. \*\*", l) or l.startswith("     ")):
            lastd = k
    assert lastf is not None and lastd is not None and lastd > lastf

    dst = dst[: lastd + 1] + DISCIPLINE.split("\n") + dst[lastd + 1 :]
    dst = dst[: lastf + 1] + block + dst[lastf + 1 :]
    DST.write_text("\n".join(dst), encoding="utf-8")
    print(f"added facts {ROWS[0][0]}-{ROWS[-1][0]}, discipline 254")


main()
