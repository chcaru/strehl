"""Fold M95/M85 arm 7. Facts 1419-1423, disciplines 705-706. Retracts my own fact 1402."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1419, "**THE GATHER'S SHARPNESS COST IS NON-INTEGER PHASE, NOT SCALE, AND THIS RETRACTS MY OWN FACT "
           "1402.** Measured ladder in dex of high-band loss: real warp plus the 0.9315 coverage scale "
           "**+0.1844**; coverage removed **+0.1701**; **integer translation at unit scale -0.0002**; K1 null "
           "-0.000041. **The gather is free when the phase is integer.** Removing the coverage scale "
           "therefore recovers only **+0.0143 dex, 7.8%** of the cost -- not the 64.2% I registered. It is "
           "**threshold, not dose**: coverage-alone (+0.1836) and warp-alone (+0.1701) each cost nearly as "
           "much as both together, because `fit_to_cover` returns one composed mapping and one gather, and "
           "dropping `k` moves the sampling step from 0.9315 to **1.0009 -- still non-integer**.",
     "**I called crop-to-cover 'the cheapest real sharpness gain currently identified' in fact 1402. That "
     "was wrong, and it was wrong for an instructive reason:** I reasoned from the *size* of the geometric "
     "change (7% of width) to the size of the quality effect, when the mechanism is a **threshold on whether "
     "the sampling phase is integral at all**. Any non-integer step pays nearly the full price. **The crop "
     "is still worth doing** -- +0.0143 dex is real and it costs nothing -- but it is a rounding item, not a "
     "lever, and it must not be sold to the owner as a fix for softness. Fact 1402's recommendation stands; "
     "its ranking does not.",
     "M95/M85 arm 7, commits `2a4ebac`/`dccaea8` (MEASURED -- refutes ORCH fact 1402's ranking)"),

    (1420, "**THE RESAMPLING KERNEL IS THE REAL LEVER AND IT IS WORTH 9.4x THE RESCALE FIX: lanczos3 -0.0663 "
           "dex AGAINST catmull-rom -0.2006 dex, A GAIN OF +0.1343 dex.** A verified patch exists, carried "
           "verbatim in `crates/strehl-cli/examples/m95-lanczos.rs`, with **4 of 4 controls passing** and "
           "control C4 discriminating (0.6466 against 0.4488). The change is a variant on the `Resampler` "
           "enum in `crates/strehl-core/src/align.rs`.",
     "**This is now the largest single measured quality gain available to the shipping binary, and it is "
     "already written and controlled.** It corroborates the independent in-crate measurement of -0.2894 dex "
     "and the -0.2360 dex metric figure: three instruments, three code paths, same conclusion. **The blocker "
     "is file ownership, not evidence** -- `align.rs` has been written by M86, M97 and M103 in the last "
     "twelve hours. Sequencing it, rather than measuring it further, is the remaining work.",
     "M95/M85 arm 7 report section 7, `examples/m95-lanczos.rs` (MEASURED, patch VERIFIED by its author -- "
     "independent verification still owed)"),

    (1421, "**lanczos3 RINGS ~9.9x MORE THAN catmull-rom, WHICH IS WHY ITS AUTHOR RECOMMENDS OPTION, NOT "
           "DEFAULT.** The ringing lands on exactly the high-contrast subject boundaries where M87 is "
           "measuring the occlusion veil (facts 1403, 1405).",
     "**The sharpest kernel and the halo work are competing for the same edges, and neither team can settle "
     "the trade alone.** ARGUED, and unmeasured: the honest resolution is not to pick for the owner but to "
     "**render the A/B and let them judge**, exactly as the kernel and gate montages already do -- the owner "
     "is the only party who has said the renders look wrong. Two intermediate kernels are unpriced and "
     "cheap: **Mitchell-Netravali (B=C=1/3)** and **lanczos2**, both of which sit between catmull-rom and "
     "lanczos3 on both axes. Nobody has measured them, and a three-point ladder would cost one decode "
     "budget.",
     "M95/M85 arm 7 (MEASURED for the 9.9x); intermediates ORCH (ARGUED, UNMEASURED)"),

    (1422, "**THE DEMOSAIC UPGRADE WAS REJECTED BY ITS ARTIFACT CLAUSE, AND A SIGNAL-ONLY BAR WOULD HAVE "
           "SHIPPED A REGRESSION.** CDIFF scored **+0.0124 dex** with artifact share **-0.0096** -- "
           "Pareto-safe but below bar. CDIFF2 scored **+0.0675 dex of signal** but artifact share "
           "**+0.0590**, failing B10. **CDIFF2 is worse than Malvar-He-Cutler on every channel in pixel "
           "error.** All four panels are visually indistinguishable including ground truth.",
     "**This is rule 9 -- pair every sharpness metric with a control -- catching a live regression rather "
     "than being quoted approvingly.** A bar that measured only the thing the change was meant to improve "
     "would have shipped a demosaic that is worse on every channel by the direct measure. **It also "
     "eliminates demosaic as a candidate for the owner's softness complaint**, and it weakens my fact 1401 "
     "speculation that demosaic error fills the top octave: the panels are indistinguishable, including "
     "against ground truth.",
     "M95/M85 arm 7, bar B10 (MEASURED, REJECTED ON ITS OWN BAR)"),

    (1423, "**M95/M85 REFUTED FOUR OF ITS OWN CONTROLS AS STRUCTURALLY BLIND, AND ADDED A FIFTH TO COVER THE "
           "GAP.** K8 cannot see a chroma kernel because the difference is zero on a constant; K10 cannot "
           "see a parity swap because it is 2-shift-invariant; K9 cannot reject NEAREST because replication "
           "is linear; K11 was structurally blind to CDIFF2's green refinement because `decompose`'s per-bin "
           "alpha **absorbs a linear gain by construction**.",
     "**Four controls that would have returned green on a broken pipeline, found by their own author and "
     "reported rather than quietly retired.** The `decompose` finding is the transferable one: a normaliser "
     "that fits a per-bin gain **cannot detect a change that is a gain**, and that class of blindness is "
     "invisible unless you plant the exact defect the control claims to catch. Discipline 706.",
     "M95/M85 arm 7 controls K8-K11 (MEASURED, self-disclosed)"),
]

DISCIPLINES = [
    (705, "**When an ablation reads 'threshold, not dose', stop looking for a proportional term -- the "
          "mechanism is a gate.** Coverage-alone and warp-alone each cost nearly as much as both together, "
          "because the cost is triggered by the sampling phase being non-integral *at all*, not by how far "
          "from integral it is. **I predicted 64.2% from the size of the geometric change and measured "
          "7.8%**, because I reasoned about magnitude where the mechanism was binary. Before pricing a fix "
          "from the size of the thing it removes, check whether the response is graded. Fact 1419."),
    (706, "**A normaliser that fits a free parameter is blind to any defect that looks like that "
          "parameter.** `decompose`'s per-bin alpha absorbs a linear gain by construction, so every control "
          "built on it was structurally incapable of seeing a change that acted as a gain -- and would have "
          "returned green forever. **The only way to find this class of blindness is to plant the exact "
          "defect the control claims to catch and confirm it goes red.** A control that has never been shown "
          "to fail is not a control. Fact 1423."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1418 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^704\. ", l))
    assert disc_idx > fact_idx, "discipline list must follow the fact table"

    # Annotate fact 1402 in place: its ranking is retracted by 1419.
    i1402 = [i for i, l in enumerate(lines) if l.startswith("| 1402 |")]
    assert len(i1402) == 1, f"expected exactly one fact 1402 row, found {len(i1402)}"
    row = lines[i1402[0]]
    marker = ("**RANKING RETRACTED BY FACT 1419: measured at +0.0143 dex, 7.8% of the gather cost, not the "
              "64.2% registered. The crop is still worth doing and is still free; it is not a fix for "
              "softness.** ")
    assert marker not in row, "fact 1402 already annotated"
    cells = row.split(" | ")
    assert len(cells) == 4, f"fact 1402 row has {len(cells)} cells, expected 4"
    cells[2] = marker + cells[2]
    lines[i1402[0]] = " | ".join(cells)
    n = lines[i1402[0]].count("|") - lines[i1402[0]].count("\\|")
    assert n == 5, f"annotated fact 1402: {n} unescaped pipes"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        n = r.count("|") - r.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1419-1423, disciplines 705-706; annotated fact 1402 at line {i1402[0] + 1}")


if __name__ == "__main__":
    main()
