"""Fold M113's independent verification of fact 1420: physics survives, numbers and controls do not."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1465,
     "**LANCZOS-3'S RINGING DOES NOT SURVIVE THE MERGE: 1.00x EXCESS LOCAL EXTREMA, NOT 9.902x, AND THE "
     "MECHANISM IS MEASURED.** On the shipped 299-frame merge, a reference-free artefact census (strict "
     "8-neighbour extrema, no reference image) over two ROIs chosen by a third party before any of this "
     "ran gives lanczos3/catmull-rom ratios of **0.9924 / 0.9938** (thorax hair) and **1.0039 / 1.0048** "
     "(leg + claw). The mechanism is in the run's own log: **mean `n_eff` is 55.3**, so each output "
     "pixel averages ~55 independently-warped frames at ~55 different sub-pixel phases. **Ringing is "
     "phase-dependent and averages down; passband gain is not and does not.** An edge-profile probe does "
     "find the signature but small (+7.91 % of local range on top-1 % edges, a -19.8 DN lobe on a 474 DN "
     "range, no negative lobe at all on the second ROI), and its excursions stay **inside** the "
     "un-resampled `nearest` render's -- recovering contrast, not inventing it.",
     "**This retires the objection that has gated the default since fact 1374, and it does so by "
     "explaining it rather than contradicting it.** Fact 1374's 9.902x is a **single frame at a "
     "half-pixel phase**; a 299-frame merge is a different object, and the quantity does not transfer "
     "across that boundary. M110 reached the same end-to-end conclusion independently by a different "
     "route (edge overshoot <= 1.47/255 and **sign-changed**), and it too was careful to say this does "
     "not refute 1374. **Three uncorrelated by-eye reads -- M113's, M110's and my own (fact 1464) -- now "
     "agree that lanczos3 is sharper on real hairs with no visible fringe or dark rim.** Note the "
     "discarded instrument, recorded so nobody re-derives it: an envelope-based probe read exactly 0.00 "
     "for both arms, which is **a dead instrument, not a clean result**, because a 5x5 min/max envelope "
     "widens with the gradient and is loosest exactly where ringing lives.",
     "M113-kernel-verify sections 5, 9; ROIs from `experiments/ORCH-drift-check/kernel_crops.py`"),
    (1466,
     "**THE END-TO-END KERNEL GAIN IS +0.083 TO +0.099 dex, NOT THE +0.1343 THIS PROJECT HAS QUOTED ALL "
     "NIGHT.** M113 reproduced +0.1343 **synthetically** by its own independent route (+0.1366 dex, "
     "three instruments including two reference-based statistics M95 lacks, over 117 geometrically-"
     "chosen tiles rather than M95's 40 sharpest-by-gradient), then measured it **end-to-end** on two "
     "full 299-frame merges whose sidecars differ by exactly one line: **+0.0887 / +0.0824 / +0.0830 / "
     "+0.0875 dex** on the central half at 64/128/256/512 px tiles, sem 0.0010-0.0031. The catmull-rom "
     "arm re-rendered from scratch is byte-identical twice over, so the arms are reproducible. The "
     "\"9.4x the rescale fix\" multiplier is **cross-instrument**; the matched-instrument figure is "
     "**6.5x**, which `align.rs` itself already states.",
     "**The gain is real, highly significant, and roughly two-thirds of what was claimed.** This is the "
     "second time in one night that a headline number survived as a direction while failing as a "
     "magnitude -- fact 1460 was the first, and the two are the same defect from opposite ends: 1460 "
     "found a quantity measured on an 8-frame sidecar rather than the shipped solve; this finds one "
     "measured in NumPy rather than through the binary. **A synthetic number and an end-to-end number "
     "are different quantities and the corpus was treating them as one.** Facts 1419 and 1420 are "
     "amended in place. I acted on +0.1343 for hours; the decision it drove happens to survive at "
     "+0.085, but that is luck, not method.",
     "M113-kernel-verify sections 3.1, 3.2; `k1_truth.py`, `k2_endtoend.json`"),
    (1467,
     "**THE RESAMPLER IS UPSTREAM OF THE ELECTION, SO A KERNEL A/B IS NOT COMPARING THE SAME PHOTOGRAPH: "
     "8.084 % OF QUADS ELECT A DIFFERENT FRAME.** `merge_cmd.rs::field_for` warps **before** it reads a "
     "pixel, so the kernel feeds the focus field, the gate and the election. The binary's own printed "
     "statistics move (mean `n_eff` 55.321 -> 53.674; winner response median 4.1675 -> 4.2580), and "
     "`--index-map` shows **5.643 % of quads shifting by more than one frame, mean \\|delta index\\| "
     "55.24, max 298**, plus a flat-field level shift of **+8.83 and +8.78 DN** in two independent "
     "ROIs. "
     "Stratifying by election agreement: **+0.0968 dex where agreement >= 0.99, +0.0604 where < 0.95**, "
     "with `corr(agreement, gain)` **+0.30** at 128 px and **+0.41** at 256 px.",
     "**The direction is favourable and that is what makes this a constraint rather than a refutation: "
     "the gain is *larger* where the election held still, so the kernel earns it and the re-election "
     "dilutes it.** Had the correlation pointed the other way, the entire measured gain would have been "
     "attributable to a reshuffled election rather than to interpolation. **Any future end-to-end kernel "
     "comparison must report this split** -- and fact 1374's `nearest` comparison needs it most, since "
     "`nearest` will perturb the election harder than lanczos3 does. It also means the flat-field level "
     "shift is unmodelled: the stack fits no per-frame gain term, which is the photometric-normalisation "
     "gap the external review named and M97 has now wired behind `--photometric`.",
     "M113-kernel-verify section 6; `--index-map`, `k3_diagnose.json`"),
    (1468,
     "**\"4 OF 4 CONTROLS PASSING\" WAS 1 OF 4: TWO CANNOT FAIL AND THE DISCRIMINATING ONE REWARDS "
     "RINGING.** Every published reading reproduces exactly -- the arithmetic is honest, the **power** is "
     "not. C1 (interpolating) is sound and Mitchell really does fail it. **C2 (partition of unity) has "
     "zero power: the weights are divided by their sum three lines above the assertion.** Measured "
     "un-normalised the defect it exists to detect is **5.701e-3**; measured through the normaliser it "
     "is 2.384e-7 against a 1e-6 bar -- **the normaliser removes it by 23914x**, and what passes is f32 "
     "rounding of a six-term sum clearing float epsilon by 4.2x (rule 20). **C3 (support) has zero "
     "power: `if x.abs() >= 3.0 { return 0.0 }` sits six lines above it.** **C4, the only discriminating "
     "one, is an unbounded ordering on passband gain and ranks a 137 %-overshoot kernel first** -- it "
     "prefers every *more* ringing kernel. Separately, fact 1420's claim that a verified patch was "
     "\"carried verbatim\" is false: `align.rs` carries different source.",
     "**A control that asserts a property the code guarantees a few lines earlier is not a weak control, "
     "it is a decoration**, and counting it in a score inflates confidence precisely where confidence is "
     "least earned. The test is mechanical and should be routine: **for each control, name the concrete "
     "change that would make it fail; if you cannot, it has no power.** C4 is the more instructive "
     "failure -- it is not powerless but *anti-correlated*, an ordering statistic pointed at a quantity "
     "that increases with the artefact being guarded against. **A discriminating control that ranks the "
     "worst candidate first would have licensed exactly the wrong kernel had the ladder contained one.** "
     "This is the same family as fact 1457's two-bin Spearman and fact 1463's impossible radius: three "
     "instruments in one night that returned a confident number while measuring nothing, or the wrong "
     "thing.",
     "M113-kernel-verify section 7; `k4_controls.json`"),
    (1469,
     "**`strehl stack` HAS NO `--resampler` FLAG AT ALL, SO A MERGE'S KERNEL IS SET ENTIRELY BY WHICHEVER "
     "SIDECAR THE CACHE HAPPENS TO HOLD.** Confirmed in source and empirically: a virgin cache and a "
     "cache-wiped byte-identical command line both give `9110C686...` (the null passes), but after an "
     "unrelated `align --limit 8 --reference 0 --resampler lanczos3` the same `stack` command yields "
     "`83A79D6C...`, and after `--reference 4` it yields `DAB7F2AF...`. **The exposure is one-sided, not "
     "symmetric:** the hazard is not two arms colliding but **one arm silently receiving a kernel nobody "
     "asked for**, which can move a result in either direction.",
     "**My symmetric-collision reasoning about fact 1446 was correct as far as it went and missed the "
     "larger half.** I reasoned about two arms of a deliberate A/B contaminating each other; the real "
     "hazard is a *single* measurement inheriting a setting from an unrelated earlier command, which has "
     "no tell at all -- no second arm to disagree with it, no hash to compare. **Every measurement taken "
     "through `strehl stack` at any point tonight is exposed unless its cache was isolated**, and the "
     "isolation discipline (`STREHL_WARPMAP`, redirected `STREHL_CACHE_DIR`) is rule 45 for this reason. "
     "It also means shipping the kernel is not a one-line default change: **there is no user-facing "
     "control to flip.** That is a product defect independent of which kernel wins.",
     "M113-kernel-verify section 2, measured at HEAD `e924229`; extends fact 1446"),
]

DISCIPLINES = [
    (748,
     "**For every control, name the concrete change that would make it fail. If you cannot name one, it "
     "has no power and must not be counted in a score.** Two of four controls in fact 1468 asserted "
     "properties the code guarantees three and six lines above the assertion; both passed, both were "
     "counted, and \"4 of 4 passing\" was doing real persuasive work. The rule is mechanical and costs "
     "one sentence per control. **Its sharper form: a control whose statistic is monotone in the artefact "
     "it guards against is worse than absent**, because it will actively rank the worst candidate first "
     "-- C4 preferred a 137 %-overshoot kernel. Check the *direction* of a discriminating statistic "
     "against the failure mode, not merely its ability to separate."),
    (749,
     "**A synthetic number and an end-to-end number are different quantities; never fold one and cite it "
     "as the other.** Fact 1466's +0.1343 dex was pure NumPy over one image and never invoked the "
     "binary; end-to-end through the shipped merge the same comparison is +0.083 to +0.099. Both are "
     "correct measurements of different things. **A folded result must carry the boundary it was "
     "measured inside** -- synthetic / in-crate / end-to-end -- exactly as fact 1460 requires a frame "
     "count and a `stack-digest`. The failure mode is identical in both cases and it is not arithmetic: "
     "a quantity is quoted in a decision whose scope is wider than the measurement's."),
    (750,
     "**When a hazard has a symmetric form and a one-sided form, the one-sided form is the dangerous one, "
     "because it has no tell.** I reasoned about cache contamination as two A/B arms colliding (fact "
     "1446) and missed that a *single* measurement can silently inherit a setting from an unrelated "
     "earlier command (fact 1469). A collision between two arms at least produces two numbers that "
     "disagree; a lone contaminated measurement produces one confident number and nothing to compare it "
     "to. **Ask of any contamination hazard: what would it look like if it happened to exactly one "
     "measurement?** If the answer is \"like a clean result\", isolation is mandatory rather than "
     "prudent."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1464 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^747\. ", l))
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

    # Amend 1419/1420 in place: they are cited widely and their magnitudes are now known wrong.
    n = 0
    for fid, note in (
        (1419, " **AMENDED (fact 1466): these quantities are synthetic and were measured on an 8-frame "
                "quarantined sidecar (fact 1460); the end-to-end figures differ.**"),
        (1420, " **AMENDED (facts 1465, 1466, 1468): the +0.1343 dex is synthetic -- end-to-end it is "
                "+0.083 to +0.099; the \"9.4x\" is cross-instrument and matched-instrument is 6.5x; "
                "\"carried verbatim\" is false; and \"4 of 4 controls\" was 1 of 4.**"),
    ):
        m = re.search(rf"^\| {fid} \| ", text2, re.M)
        assert m, f"fact {fid} row not found for amendment"
        eol = text2.index("\n", m.start())
        row = text2[m.start():eol]
        assert note not in row, f"fact {fid} already amended"
        cells = row.split(" | ")
        assert len(cells) >= 3, f"fact {fid}: unexpected row shape"
        cells[1] = cells[1] + note
        text2 = text2[:m.start()] + " | ".join(cells) + text2[eol:]
        n += 1
    assert n == 2

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write(text2)
    print("folded facts 1465-1469, disciplines 748-750; amended facts 1419, 1420 in place")


if __name__ == "__main__":
    main()
