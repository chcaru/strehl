"""Fold M111's waxy-blob diagnosis, its refutations, and two instrument defects."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1470,
     "**THE WAXY-BLOB ARTEFACT IS THE GATE'S ADMISSION TOLERANCE BEING ABSOLUTE WHILE THE FOCUS RESPONSE "
     "IS CONTRAST-SCALED.** The tolerance is a fixed **0.086063** in focus-response units "
     "(`4.0*sqrt(2)*FOCUS_NOISE_SD`), but the response it is compared against spans **0.43 to 84** with "
     "contrast. Admission therefore collapses **`n_eff` 275.5 to 1.6** as response rises from 0.62 to 5. "
     "Regions that are visually flat but *not* response-flat land in that band and are rendered as **one "
     "elected frame per plateau -- and the seams between plateaus print.** Measured unconfounded via "
     "`D = luma(gate 4) - luma(gate 1e5)`, which holds frames, alignment, colour and exposure fixed so "
     "`D` is only what selection added: on flat regions with `n_eff <= 8`, **+12.00 DN excess at seams, "
     "ratio 1.248 against a null of 1.002 +/- 0.003, +97.4 sigma**, while both controls fire *below* "
     "null (averaged 0.765, textured 0.880). Selection monotonicity confirms it end to end: boundary p90 "
     "at the blob goes **84 (no selection) -> 1384 (shipped) -> 1557 (gate 0.25)**.",
     "**This is the third independently-diagnosed defect on the owner's default render path, and unlike "
     "the other two it is a design error rather than a wiring gap.** A threshold in absolute units "
     "compared against a quantity that scales with local contrast cannot be correct at both ends of a "
     "195x response range; it is necessarily too tight somewhere and too loose elsewhere. The proposed "
     "fix -- replace the boolean admission with a soft weight `exp(-0.5*((best-focus)/tol)^2)` -- is "
     "**ARGUED but its premise is measured**: at seams the runner-up is a tie at **0.467x tolerance**, "
     "while in texture the winner leads by **2.187x**, a **4.7x separation** that a soft weight can "
     "exploit and a boolean one discards. It also preserves `FOCUS_NOISE_SD`'s unit, which M81's "
     "rejected route did not. **Note what this converges on**: a soft, noise-referenced weight over the "
     "through-focus response *is* the posterior-over-depth object the external review argued for, "
     "arrived at independently from a defect measurement rather than from theory. Cost is real and must "
     "be paid deliberately: it breaks every `stack`/`merge` byte-freeze, forces a `DEFAULT_GATE` "
     "re-solve, and scopes fact 19's 0.534x to the boolean gate.",
     "M111-waxy-blobs sections 1, 3; commits `fc4cbf6`, `9628e57`, `aaf9955`"),
    (1471,
     "**BOTH HYPOTHESES I HANDED M111 WERE REFUTED, AND THE REAL SMOOTHER IS A DIFFERENT CONSTANT IN A "
     "DIFFERENT FILE.** H1 blamed the spatial regulariser: at `REGULARISER_RADIUS = 0` the plateaus "
     "**survive at 54.0 px** against 60.3 px shipped, with amplitude flat across a **32x** range of "
     "radius (1.213 / 1.239 / 1.203). Its premise was separately false -- **0.00 %** of either ROI lies "
     "below the noise ceiling (medians 4.31 and 2.96 against 0.478). The actual smoothing scale is "
     "`focus.rs WINDOW_RADIUS = 13`, a **27x27** window. H2 was refuted as a diagnosis too, and "
     "backwards: the gate fires **hardest** where H2 predicted it would not (median `n_eff` **285** in "
     "the weakest band, **151** across flat regions). **Fact 84 is not implicated in this artefact.**",
     "**I named two mechanisms and both were wrong, which is the outcome the brief was designed to make "
     "cheap rather than embarrassing.** The refutations cost one parameter sweep and one median each, "
     "because the brief demanded a falsifiable premise per hypothesis rather than a hunt for supporting "
     "evidence. Worth recording specifically: **H1's premise was checkable before H1 was tested**, and "
     "checking it first would have killed the hypothesis for free -- 0.00 % of the ROI below the noise "
     "ceiling means the regulariser has nothing to act on there. **Test the premise before the "
     "mechanism; premises are usually one query and mechanisms are usually a sweep.** The deeper lesson "
     "is that I reached for the most recently interesting constant (fact 84's regulariser, priced at "
     "-35 %) rather than the one with the right spatial scale, and 27x27 was sitting in a file I did not "
     "look at.",
     "M111-waxy-blobs section 2; sweep over `REGULARISER_RADIUS`, `focus.rs WINDOW_RADIUS`"),
    (1472,
     "**A CONTROL THAT REMOVED THE MECHANISM ENTIRELY STILL SCORED 1.686 ON THE STATISTIC THAT WAS ABOUT "
     "TO BE THE ANSWER.** M111's first diagnosis rested on blob boundaries coinciding with election "
     "boundaries. At `--gate 1e5` the election **cannot** affect the output at all -- yet "
     "boundary-coincidence still read **1.686**. The statistic was measuring the fact that both maps "
     "have boundaries in the same textured places, not that one causes the other. **Coincidence is not "
     "attribution**, and this also **qualifies fact 1445's immunity claim**, which rested on the same "
     "kind of reasoning.",
     "**This is the strongest single control result of the night, because it killed a conclusion its own "
     "author had already reached.** The design principle it demonstrates is the one that separates a "
     "control from a sanity check: **the control must disable the proposed mechanism while leaving "
     "everything else in place, and the statistic must then go to null.** A statistic that survives the "
     "removal of its own cause is measuring a confounder -- here, that texture drives boundaries in both "
     "maps independently. Note the family resemblance to facts 1457, 1463 and 1468: **four instruments "
     "in one night returned confident numbers while measuring the wrong thing**, and in every case the "
     "catch came from a control rather than from inspecting the number. The replacement evidence "
     "(`D = luma(gate 4) - luma(gate 1e5)`, fact 1470) is causal by construction because it differences "
     "two renders that differ *only* in whether selection happened.",
     "M111-waxy-blobs section 1; the `--gate 1e5` control"),
    (1473,
     "**THE BLOB BOUNDARY STATISTIC WAS COMPUTED INSIDE A MASK DERIVED FROM THE ARM UNDER TEST, AND "
     "REPLACING THE MASK MOVED IT FROM 1384 TO 115.** The mask was the merged image's own **p75**. "
     "Recomputed with a mask taken from an independent third arm, the same quantity falls by **12x**. "
     "Relatedly, the headline blob figure decomposes into **interior 0.67x and exterior 5.36x** -- "
     "mostly the stacker sharpening the *surroundings* rather than degrading the blob -- and **blobA is "
     "not a defect at all** (1.477 against 1.468), so **fact 1444 must be scoped to blobB only**.",
     "**A mask derived from the arm under test makes the arm define its own measurement region, and the "
     "region moves with the effect.** This is the same circularity as scoring a demosaic against another "
     "demosaic's output (captures section 24) and as fact 1468's C2, where the normaliser removed the "
     "defect the control existed to detect -- in each case the instrument's own construction guarantees "
     "the answer. **Any mask, ROI or denominator must come from something that does not vary across the "
     "arms**: a third arm, a fixed geometry, or the input. The interior/exterior split is the more "
     "useful half for the product: it says the visible objection is partly that the stacker sharpens "
     "everything *around* a smooth blob, which is an appearance problem rather than a reconstruction "
     "error, and the two want different remedies.",
     "M111-waxy-blobs section 4; third-arm mask recomputation"),
    (1474,
     "**LANCZOS-3 COSTS 2.478x TO 3.529x THE WALL-CLOCK OF CATMULL-ROM AND THAT PRICE APPEARS NOWHERE IN "
     "THE CORPUS.** Measured by M110 across two subjects (2.478x on the 299-frame bee stack, 3.529x on "
     "the text stack), and independently flagged as unreported by M113. Every kernel discussion in this "
     "project until tonight has been conducted on accuracy alone.",
     "**The owner's brief is \"state of the art high-performance (speed *and* quality)\", so an accuracy "
     "gain quoted without its cost is an incomplete answer to the actual question.** A 2.5x to 3.5x warp "
     "cost against a measured **+0.083 to +0.099 dex** end-to-end gain (fact 1466) is a trade a user "
     "should be allowed to make, which makes fact 1469's finding -- that **`strehl stack` exposes no "
     "kernel control at all** -- the more pressing defect of the two. Note also that the cost is "
     "probably not irreducible: Lanczos-3 is separable and the current path is a scalar gather, so this "
     "is a number to attack rather than to accept.",
     "M110-sheet report; corroborated as unpriced by M113-kernel-verify section 8"),
    (1475,
     "**A PATH-SCOPED COMMIT BROKE THE BUILD BY SWEEPING IN CALL SITES WHOSE MODULE FILE WAS "
     "UNTRACKED.** Commit `e4796e5` included another agent's uncommitted `mod dump;` declaration and its "
     "call sites while `dump.rs` itself was untracked and therefore not swept, leaving `HEAD` "
     "**non-compiling** between `e4796e5` and `fc4cbf6`. Verified resolved: `cargo check --workspace "
     "--all-targets` at `4ad2935` returns **EXIT=0, 0 errors**.",
     "**Path-scoping a commit prevents capturing another agent's files; it does not prevent capturing "
     "another agent's *edits to your files*.** The asymmetry is the trap: a new module is two artefacts "
     "-- an untracked `foo.rs` and a one-line `mod foo;` inside an already-tracked file -- and a "
     "path-scoped commit that names the tracked file takes the reference without the definition. **The "
     "check is `cargo check` on the commit you just made, not on your working tree**, since the working "
     "tree contains the untracked file that makes it compile locally. This is the build-integrity twin "
     "of fact 1460's provenance defect: in both cases the artefact that was *recorded* differs from the "
     "artefact that was *measured*, and in both cases the local copy looked fine.",
     "M111-waxy-blobs section 5; ORCH verification at `4ad2935`"),
]

DISCIPLINES = [
    (751,
     "**A control must disable the proposed mechanism and leave everything else standing; if the "
     "statistic survives that, it is measuring a confounder.** M111's boundary-coincidence statistic "
     "read 1.686 with the election fully disabled, where it could not possibly have had a cause (fact "
     "1472). **Coincidence is not attribution**, and the failure is invisible from the number alone -- "
     "1.686 looks like a result. The constructive form is to build the comparison so causality is "
     "structural: difference two renders that differ *only* in the mechanism under test, as "
     "`D = luma(gate 4) - luma(gate 1e5)` does, and the confounder cancels by construction rather than "
     "by argument."),
    (752,
     "**Never derive a mask, ROI, threshold or denominator from the arm under test.** The blob statistic "
     "used the merged image's own p75 as its mask and read 1384; the same quantity under an independent "
     "third arm's mask read 115 (fact 1473). The region moved with the effect. This is one family with "
     "fact 1468's powerless C2 (the normaliser removed the defect the control existed to detect) and "
     "with scoring one demosaic against another's output: **whenever the instrument is built out of the "
     "thing being measured, the answer is partly guaranteed.** Masks must come from a third arm, a fixed "
     "geometry, or the raw input."),
    (753,
     "**Test the premise before the mechanism.** Premises are usually one query; mechanisms are usually "
     "a sweep. Hypothesis H1 in fact 1471 required regions below the noise ceiling for the regulariser "
     "to act on, and **0.00 %** of either ROI qualified -- a single median would have killed the "
     "hypothesis before any parameter was swept. The related orchestration error is worth naming "
     "separately: **I reached for the most recently interesting constant rather than the one with the "
     "right spatial scale.** Fact 84's regulariser was salient because it was priced at -35 %; the "
     "artefact's 54 px plateaus pointed at a 27x27 window in a file I had not opened. **Match the "
     "candidate to the scale of the symptom, not to its prominence in the record.**"),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1469 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^750\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    text2 = "\n".join(out)

    note = (" **SCOPED (fact 1473): applies to blobB only -- blobA measures 1.477 against a 1.468 "
            "reference and is not a defect; the boundary figure was also mask-circular.**")
    m = re.search(r"^\| 1444 \| ", text2, re.M)
    assert m, "fact 1444 row not found"
    eol = text2.index("\n", m.start())
    row = text2[m.start():eol]
    assert note not in row, "fact 1444 already scoped"
    cells = row.split(" | ")
    assert len(cells) >= 3, "fact 1444: unexpected row shape"
    cells[1] = cells[1] + note
    text2 = text2[:m.start()] + " | ".join(cells) + text2[eol:]

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write(text2)
    print("folded facts 1470-1475, disciplines 751-753; scoped fact 1444 in place")


if __name__ == "__main__":
    main()
