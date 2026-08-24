"""Fold the ORCH gate ablation. Facts 1393-1399, disciplines 692b-695.

Most of this refutes the hypothesis that commissioned it.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1393, "**THE GATE HAS ESSENTIALLY NO EFFECT OUTSIDE FLAT REGIONS.** MEASURED on `bee-3-cpl`, 299 frames, "
           "four arms differing ONLY in `--gate` (sidecar-override, 299 placed / 0 refused, all pinned to "
           "`--exposure=1.54`). Plane-fitted per-channel sigma in three 128 px tiles chosen across the detail "
           "axis, gates 4.00 / 2.00 / 0.7078 / 0.00: **flattest tile** (tile-gx 10.2) `26.2 / 179.7 / 505.5 / "
           "877.3` DN = **33.53x**; **median tile** (gx 350.6) `2658.0 / 2677.9 / 2685.6 / 2690.5` = "
           "**1.01x**; **most-detailed tile** (gx 1609.6) `5661.2 / 5664.5 / 5668.1 / 5669.8` = **1.00x**. The "
           "gate spans a factor of 33 in the flattest tile and **is flat to three significant figures in both "
           "others**.",
     "**This is the whole result and it kills the hypothesis that commissioned the experiment.** I argued "
     "(ARGUED, from mean n_eff 55.321 at the default against fact 324's target of 3) that the gate was a "
     "larger softness term than the resampler kernel. **It is not a sharpness term at all on this stack**: "
     "where there is detail, n_eff is 1 at every gate, so no gate changes those pixels. The mean n_eff of "
     "55.3 is composed **entirely of flat background**, where averaging is free -- 33x less noise at zero "
     "measured cost in detail. **The shipped default gate 4.00 is therefore doing exactly what the design "
     "intends, and my '18.4x above fact 324's target' alarm was misdirected**: a mean n_eff is an average "
     "over pixels with wildly different leverage and cannot be compared to a target derived from peak width. "
     "Consequence for routing: **the gate is cleared as a cause of the owner's softness complaint, which "
     "strengthens the kernel (fact 1373-1374, -0.2360 dex) as the lever.**",
     "ORCH gate ablation (MEASURED); bars G0-G5 registered before the run in `experiments/ORCH-drift-check/gate_ab.ps1`"),

    (1394, "**THE PRINTED `pred sigma gain (model)` COLUMN IS AN IMAGE-WIDE QUANTITY AND IT IS ACCURATE.** "
           "MEASURED: robust high-pass sigma over a decimated grid, gates 4.00 / 2.00 / 0.7078 / 0.00, "
           "relative to gate 4.00: **1.000 / 1.040 / 1.180 / 1.471** against the model's **1.000 / 1.112 / "
           "1.245 / 1.594**. Agreement within ~10%, model **conservative** (over-predicts noise) at every "
           "rung.",
     "**Registered because it looked like a 21x defect and was not.** The flat-ROI measurement (fact 1393) "
     "reads 33.53x where the model prints 1.594x; the naive reading is that the model under-predicts by 21x. "
     "It does not -- **the two numbers measure different populations and both are right.** The model averages "
     "over the whole image, which is dominated by the 38.77% (gate 4.00) to 100% (gate 0.00) of pixels at "
     "n_eff = 1 that cannot change; the ROI measures where the gate has maximum leverage. **The presentation "
     "risk is real and worth recording even though the arithmetic is sound:** a user reading '0.6273x' as "
     "'what happens to my noise' will under-estimate the change in the flat regions where noise is most "
     "visible by a factor of 21.",
     "ORCH gate ablation (MEASURED), `gate_noise2.py`"),

    (1395, "**THE TOOL'S HEADLINE DESCRIPTION OF ITS ONE KNOB IS HALF UNSUPPORTED ON THIS STACK.** `strehl "
           "stack --help` states: *\"low is sharper and noisier, high is cleaner and softer\"*, and the "
           "`--gate` help adds honestly that *\"the sharpness cost of THIS gate on real frames is not "
           "measured in this corpus\"*. MEASURED now: the **noisier** half holds (fact 1393, 1394); the "
           "**sharper** half does not appear at all. By eye at 1:1 with x2 zoom on the most-detailed region "
           "(the compound eye's ommatidia lattice), the four gates are visually indistinguishable in "
           "resolved detail, and the sigma ladder confirms the pixels are numerically almost unchanged "
           "(`5661.2` to `5669.8`, 0.15%).",
     "**The help text was already honest that this was unmeasured; it is now measured and the honest answer "
     "is 'no effect here'.** This does not generalise beyond `bee-3-cpl`: M52 measured the gate that reaches "
     "a given n_eff varying **28.9x** across the corpus, and `foam` cannot reach n_eff = 3 anywhere on the "
     "ladder, so a stack whose detail sits at lower contrast may well show the sharpness cost this one does "
     "not. **What is established is that the claim cannot be stated unconditionally**, and that the one stack "
     "the owner is complaining about is not an instance of it.",
     "ORCH gate ablation (MEASURED); `crates/strehl-cli/src/merge_cmd.rs` --gate help text"),

    (1396, "**`--exposure=<v>` REPRODUCES `--auto-exposure` BYTE-FOR-BYTE AT THE VALUE IT PRINTS.** MEASURED: "
           "the gate-4.00 arm rendered with `--auto-exposure` (which chose `+1.54 stops, gain 2.908x`) and "
           "again with `--exposure=1.54` both hash "
           "`E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112` -- which is **also** the hash "
           "the kernel A/B produced in a previous session (fact 1373).",
     "**Three independent validity claims settled by one hash.** (a) The tool's own printed instruction "
     "*\"reproduce this exact file with --exposure=1.54\"* is exact, not approximate. (b) `--gate 4` passed "
     "explicitly is genuinely identical to the default, so rule 47's worry about defaults is here confirmed "
     "benign. (c) The render is reproducible **across sessions and across two different exposure code "
     "paths**, which is what licenses treating every difference between the four arms as caused by the gate.",
     "ORCH gate ablation, bars G1 and G1b (MEASURED)"),

    (1397, "**--auto-exposure DRIFTED ACROSS THE GATE ARMS, AND THE DRIFT IS THE NOISE CHANGE SEEN THROUGH "
           "THE EXPOSURE RULE.** MEASURED: gates 4.00 / 2.00 / 0.7078 / 0.00 chose **+1.54 / +1.53 / +1.51 / "
           "+1.49 stops**, monotone. The rule puts the 99.9th percentile of linear-sRGB luminance at 0.90; a "
           "lower gate averages fewer frames, so noise is higher, so the 99.9th percentile sits higher, so "
           "less gain is required.",
     "**A registered bar that failed, and the failure was informative twice over.** Bar G0 required identical "
     "exposure across arms *because a brightness difference biases a by-eye sharpness judgement and corrupts "
     "the flat-ROI noise measurement*; it failed at 0.05 stops (~3.5%) and the whole four-arm set was "
     "re-rendered pinned. **But the drift is also a free, independent corroboration of fact 1393**, derived "
     "from a completely different mechanism than the sigma measurement -- the auto-exposure rule is an "
     "unwitting noise meter. **A confound worth removing is not the same as a confound worth ignoring**: "
     "removing it cost four re-renders (~3.6 min) and the discarded arms became evidence.",
     "ORCH gate ablation, bar G0 (MEASURED, FAILED, remediated in `gate_ab_pinned.ps1`)"),

    (1398, "**THE FAR-FIELD BACKGROUND LEVEL FALLS 2.14% AS THE GATE FALLS, AND THE BACKGROUND BECOMES "
           "VISIBLY BLOTCHY.** MEASURED on the silhouette crop: median background in the 130-200 px ring is "
           "`54367.0 / 54050.0 / 53501.0 / 53204.3` DN at gates 4.00 / 2.00 / 0.7078 / 0.00 -- a **1163 DN "
           "(2.14%)** drop -- and the gate-0.00 panel shows large-scale mottling in the background that is "
           "absent at gate 4.00.",
     "**A mechanism the corpus already predicted, now visible in a render.** The merge prints `STATUS: NO "
     "per-frame gain term is fitted or applied`, and M24 measured per-frame photometric drift of 0.91% "
     "(109MSDCF) to 2.88% (119MSDCF). At a high gate, averaging tens of frames per background pixel "
     "**suppresses that drift**; at gate 0 each pixel takes one frame, so neighbouring pixels drawn from "
     "different frames differ by the frame-to-frame level offset and the background acquires patch "
     "structure at the scale of the winner field. **So the blotching at low gate is not noise -- it is "
     "unfitted photometric drift, spatially organised by the election.** This raises the value of the "
     "photometric normalisation work (M91, M99) specifically for the low-gate regime, and it is a second "
     "reason gate 0.00 is not shippable.",
     "ORCH gate ablation, `veil_profile.py` far-field ring (MEASURED); corroborates M24 drift and the "
     "merge's own STATUS line"),

    (1399, "**MY VEIL-VERSUS-GATE INSTRUMENT FAILED AND THE QUESTION IS UNRESOLVED.** By eye the silhouette "
           "veil (facts 1371-1372) clearly weakens from gate 4.00 to gate 0.00. The ring-profile measurement "
           "built to confirm it **cannot support that claim**: every ring including the far 90-130 px ring "
           "moved monotonically in the same direction, which is the signature of a **moving reference** "
           "rather than a localised veil, and the near rings are contaminated by unmasked dark hair tips "
           "(1-5 px ring reads -3232 DN below far field, i.e. darker, not brighter). Fact 1398 identifies "
           "the moving reference: the far-field base itself falls 1163 DN across the arms.",
     "**Reported as a failed instrument, not as a result, and the eye judgement is NOT promoted on its own.** "
     "Two defects, both mine: a ring profile referenced to a ring that itself moves measures nothing, and a "
     "subject mask thresholded at the 45th percentile leaves hair tips in the near rings of a subject that "
     "is 45.2% of the crop. **What survives is narrower but real:** the gate demonstrably changes the "
     "appearance of the silhouette region (4 distinct hashes, fact 1393's arms), so a gate sweep is a valid "
     "*stimulus* for the halo work even though this profile is not a valid *measurement* of it. Handed to "
     "M87 as a stimulus with the instrument's failure stated.",
     "ORCH gate ablation, `veil_profile.py` (MEASURED, INSTRUMENT REFUTED)"),
]

DISCIPLINES = [
    (694, "**Establish where a knob has leverage before attributing an artifact to it, and choose ROIs "
          "across the leverage axis rather than at one extreme.** The first sharpness crop was taken on the "
          "most-detailed tile in the image -- which is precisely the region where the gate provably does "
          "nothing (n_eff = 1 at every gate), so the comparison was inconclusive **by construction** and "
          "would have read as 'no effect' whether or not one existed. Sampling flattest / median / "
          "most-detailed turned the same four renders into a decisive result. Fact 1393."),
    (695, "**A profile referenced to a baseline that itself moves between arms measures the baseline, not "
          "the feature.** When every ring of a radial profile -- including the far ring intended as "
          "background -- shifts monotonically in the same direction across arms, the reference is moving and "
          "no localised claim can be extracted. Either pin the reference to one arm, or measure a quantity "
          "invariant to the shift. Facts 1398, 1399."),
    (696, "**A bar that fails cheaply is worth more than a bar that passes.** Bar G0 (auto-exposure must not "
          "differ between arms) failed at 0.05 stops and forced four re-renders costing ~3.6 minutes -- and "
          "the failed arms then supplied an independent corroboration of the main result through a different "
          "mechanism (fact 1397). Registering a confound check before the run converts a discovered "
          "confound from a retraction into a measurement. Fact 1397."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1392 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^693\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} present"
        rows.append(row)

    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1393-1399 after line {fact_idx}, disciplines 694-696 after line {disc_idx}")


if __name__ == "__main__":
    main()
