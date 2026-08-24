"""Fold M107's chroma attribution. Facts 1413-1418, disciplines 703-704."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1413, "**AXIAL CHROMATIC ABERRATION IS BAKED PERMANENTLY INTO EVERY RENDER, BECAUSE THE ELECTION IS "
           "COMPUTED FROM `green_luma` ALONE AND THE ONE WINNING INDEX IS REUSED ACROSS ALL FOUR CFA "
           "ACCUMULATORS.** Red's best-focus frame leads green's by **0.67-1.07 frames** and blue's by "
           "**0.36-0.75 frames**, on **5 of 5 stacks**, against a `k_G1 - k_G2` null of **<= 0.008 frames**. "
           "**99.7-100% of confident pixels share the sign** where the null sits at **52-54%**. The cost is "
           "measured: red surrenders **8.96-14.74% of its gradient energy** against a null floor of "
           "**0.01-0.04%**.",
     "**This is a structural defect in the merge, not a property of the optics, and it is on the owner's "
     "complaint list.** The lens has axial CA; every lens does. What the merge does is *elect on green and "
     "then gather red and blue at green's frame*, which means red and blue are deliberately sampled from a "
     "frame in which they are known to be defocused -- and unlike the optical term, this one **cannot be "
     "removed downstream**, because the sharp red was in a frame the merge chose not to read. **Every render "
     "the project has ever produced carries it.** This is the first identified defect that the "
     "estimation thesis' own machinery causes rather than cures, and it is a direct argument that the "
     "election must be per-channel or at least chroma-aware.",
     "M107 `a16976f`, Instrument B, 5 stacks, 4 controls incl. a zero-free-parameter label swap (MEASURED)"),

    (1414, "**LATERAL CHROMATIC ABERRATION IS A CLEAN ONE-PARAMETER RADIAL MAGNIFICATION ERROR OF -704.5 ppm "
           "IN RED, AND IT IS WORTH ~3 OUTPUT PIXELS AT THE CORNER.** Radial model `R^2 = 0.9969` over 20 "
           "gated ROIs, permutation **p < 0.0005**, residual rms **0.073 sensel**. It predicts the "
           "un-matrixed `linear` render arm **out of sample** to 1.07x and 1.29x, *including* its own "
           "near-vanishing at `r = 597` sensel. The `G1-G2` null fits `R^2 = 0.0524` and **fails its own "
           "permutation null** at `p = 0.7095`. DERIVED from that coefficient: the CFA half-diagonal is "
           "**2112.9 sensels**, so the corner displacement is **1.489 sensels = 2.977 output px**.",
     "**This is the cheapest large quality win currently identified anywhere in the project, and it is "
     "exactly a lens-profile parameter.** A single scalar per channel, applied as a radial rescale during "
     "the gather that already resamples every pixel (fact 1400), costs no extra pass and no extra "
     "interpolation. Three output pixels of red/blue misregistration at the corner is plainly visible at the "
     "100% magnification the owner inspects at. **It also vindicates the pluggable-optics thesis with a "
     "concrete first citizen**: `eps_R` is a property of the A7C II + FE 100mm F2.8 GM + 2x teleconverter "
     "path, measurable once and shipped as data -- precisely the 'camera and lens specifics should be "
     "pluggable to enhance stacking where available, but optional' requirement. Correcting it must be "
     "**gated and off by default on the frozen linear path**.",
     "M107 `a16976f` e2_lateral (MEASURED); corner arithmetic ORCH (DERIVED)"),

    (1415, "**DEMOSAIC CO-SITING AND THE RESAMPLER ARE BOUNDED SMALL AND ARE NOT THE CAUSE OF THE FRINGING.** "
           "Instrument B **never demosaics at all**, and turning the warp off moves the result by **1.6%**.",
     "**Two of the four candidate mechanisms are eliminated by construction rather than by argument**, which "
     "is what makes the remaining attribution to (a) lateral and (b) axial CA load-bearing. It also "
     "partially answers my fact 1401 speculation, which floated demosaic error as the filler of the top "
     "octave: whatever fills it, it is not driving the chroma defect.",
     "M107 `a16976f` (MEASURED)"),

    (1416, "**M107's REGISTERED BAR B3 FAILED ON ITS SIGN CLAUSE, AND THE FAILURE IS INFORMATIVE.** B3 "
           "predicted red and blue would straddle green in focus depth. Measured: **both sit before green**. "
           "That clause encoded **uncorrected-singlet** behaviour; same-side R and B is the residual "
           "**secondary spectrum** of a deliberately colour-corrected (apochromatic-class) design.",
     "**The bar was reported failed rather than narrowed to fit**, and the physics that explains the failure "
     "is a *better* description of the lens than the one the bar assumed. This is the M87 pattern again "
     "(fact 1404): the mechanism that survives a failed registered prediction is worth more than one "
     "confirmed by a passing bar. **It also means any future chroma model must not assume symmetric "
     "straddling** -- a same-side offset changes the sign structure of any correction fitted to it.",
     "M107 `a16976f` bar B3 (MEASURED, FAILED AS REGISTERED)"),

    (1417, "**PER-CHANNEL ELECTION COSTS ~2.8x CPU AND ~4-4.5x WALL CLOCK, AND CANNOT BE BUILT FIRST.** The "
           "merge is **memory-bound** -- 13 workers by budget against 32 by CPU -- and focus plus "
           "regularisation is **88% of pass-1 work**, so electing per channel multiplies the dominant term. "
           "It also **requires a per-channel noise model first**, because M93's gate is calibrated on green.",
     "**This correctly separates the two chroma fixes by cost, and they should ship in the opposite order to "
     "their discovery.** Lateral CA (fact 1414) is one scalar, no extra pass, and can land now. Axial CA "
     "(fact 1413) is a merge-architecture change gated behind a noise-model prerequisite, and at 4-4.5x wall "
     "clock it is not a default at any point soon. **A cheaper intermediate exists and is unexplored "
     "(ARGUED): keep the single green election but apply a per-channel focus-index OFFSET of the measured "
     "`k_R - k_G` and `k_B - k_G`**, gathering red and blue from a shifted frame at no extra election cost. "
     "That is a lens-profile scalar too, and it is the same shape of fix as fact 1414.",
     "M107 `a16976f` costed against measured per-frame figures (MEASURED); offset proposal ORCH (ARGUED)"),

    (1418, "**M107 MANUFACTURED A 1.0-SENSEL ARTEFACT IN THE DIRECTION THAT WOULD HAVE FALSELY INCRIMINATED "
           "ANOTHER MILESTONE, FOUND IT, AND REPORTED IT.** The binned arm's lattice offsets initially "
           "double-counted `COSITE_SHIFT`, producing exactly the signature that would have blamed M95.",
     "**The error was in the one direction most likely to be believed**, because it agreed with a suspicion "
     "already in the corpus. It was disclosed rather than silently fixed. Together with B3's honest failure "
     "and B2 being flagged **indeterminate as registered** rather than resolved post hoc, this is the "
     "standard the project asks for and rarely gets. Record it as precedent, not as a defect.",
     "M107 `a16976f` self-disclosure (MEASURED)"),
]

DISCIPLINES = [
    (703, "**A defect the pipeline BAKES IN outranks a defect the pipeline merely fails to remove, because "
          "only one of them is still fixable downstream.** Axial CA is optical and universal; what makes "
          "fact 1413 serious is that the merge elects on green and then gathers red and blue at green's "
          "frame, so the sharp red is in a frame the renderer chose not to read and no later stage can "
          "recover it. **When triaging quality defects, sort by whether the information still exists in the "
          "output**, not by effect size."),
    (704, "**Rank a fix by parameters-per-pixel-of-gain, not by how fundamental it sounds.** M107 measured "
          "two chroma mechanisms in one milestone: one needs a merge-architecture change, a per-channel "
          "noise model and 4-4.5x wall clock; the other is **one scalar** worth **~3 output px at the "
          "corner** with no extra pass. The second is the one to ship, and the discovery order was the "
          "reverse of the shipping order. Facts 1414, 1417."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1412 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^702\. ", l))
    assert disc_idx > fact_idx, "discipline list must follow the fact table"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(row)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1413-1418 after line {fact_idx}, disciplines 703-704 after line {disc_idx}")


if __name__ == "__main__":
    main()
