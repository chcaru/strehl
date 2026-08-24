"""Fold the ORCH anisotropy / softness-attribution results into SYNTHESIS.md.

Facts 1279-1283, disciplines 628-630.

MECHANICS (learned the hard way, see disciplines in the corpus):
 - Disciplines sit at a HIGHER line index than the fact table, so splice the
   discipline block FIRST; otherwise the earlier insert shifts the later anchor.
 - A fact row is 4 columns = exactly 5 unescaped pipes. A literal pipe inside a
   cell breaks the row.
 - All asserts run BEFORE any write, so a failed fold is safe and re-runnable.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1279, "**THE GATE'S NOISE REDUCTION IS PAID FOR IN RADIAL SMEAR, AND THE PRICE IS ABOUT ONE PIXEL.** "
           "Radial-vs-tangential high-frequency anisotropy of the rendered output falls monotonically with gate at "
           "every radius where the subject is angularly clean. At r=0.45 (angular clustering 0.07-0.08) A reads "
           "**0.7474 / 0.7133 / 0.6994 / 0.6922 / 0.6497** for gates 0/1/2/4/8. Inverting a planted dose curve at "
           "fixed radius on a fixed tile set, so the subject cancels, the cost relative to `--gate 0` is "
           "**+0.28 / +0.44 / +0.68 / +0.79 px** at r=0.35 and **+0.48 / +0.78 / +1.06 / +1.26 px** at r=0.55.",
     "This is the first measurement of residual misregistration in the *photograph* rather than in the solve's own "
     "held-out score, and it prices a trade the project had only argued about: averaging more frames buys noise but "
     "sells geometry. The numbers are upper bounds -- any surviving subject anisotropy inflates them -- but the "
     "between-gate differences are taken on an identical tile set of an identical scene, so the subject cancels from "
     "the difference even where it contaminates the level. Annuli with angular clustering above 0.30 are excluded; on "
     "`bee-3-cpl` the r>0.6 annuli reach 0.42-0.62 and the bee's own hair direction leaks in.",
     "ORCH (MEASURED, 5 gates x 10 annuli, instrument validated by fact 1281); "
     "`experiments/ORCH-drift-check/anisotropy.py`, `aniso_px.py`"),

    (1280, "**THE HALF-DRIFT RESIDUAL DOES NOT ARRIVE AT THE RENDER AS BLUR: IT IS A GEOMETRY DEFECT, NOT THE SOFTNESS.** "
           "Fact 1271 measured ~150.2 plane px of uncorrected drift on `bee-3-cpl`. The smear actually reaching the "
           "output is the ~1 px of fact 1279. The mechanism: the frames that win a given pixel cluster in index, so "
           "averaging them smears by the displacement spread *within the competitive set*, not by the stack's total "
           "end-to-end drift.",
     "This retires the orchestrator's own attribution. When fact 1271 landed I told M103 in writing that the half-drift "
     "was \"the critical path to a sharper photograph\" and that it was the direct cause of the owner's complaint that "
     "the renders look soft. That was ARGUED and it was wrong, and it was corrected only because the claim was measured "
     "afterwards instead of being allowed to stand as the project's working story. The half-drift remains a real defect "
     "worth fixing -- it misplaces features and caps final-render accuracy -- but a milestone that fixes it and does not "
     "produce a visibly sharper photograph has succeeded, not failed. M103 was told so mid-flight.",
     "ORCH (DERIVED from fact 1279 measured against fact 1271); correction issued to M103 in-flight"),

    (1281, "**THE ANISOTROPY INSTRUMENT PASSES FIVE CONTROLS, AND THREE OF THEM FAILED FIRST AND CHANGED ITS DESIGN.** "
           "Final state on `bee-3-cpl-g0`: sensitivity (a planted 10 px radial smear drives A_outer **0.6337 -> 0.0159**), "
           "monotone dose order (**0.6337 / 0.4457 / 0.0812 / 0.0159** at 0/1/3/10 px), specificity (a planted isotropic "
           "Gaussian of sigma 1.6 moves it only **-0.0113**), a built-in null (**A = 1.0224** at r=0.05 untreated, as the "
           "geometry requires), and geometry (at 1 px the outer annuli fall **0.188** against **0.041** at the centre, "
           "**4.6x** harder outside).",
     "The specificity arm is the load-bearing one: without it the metric would have been a softness detector wearing an "
     "orientation costume. It failed on the first build -- an isotropic blur moved A from 0.5268 to 0.3069 -- because a "
     "band mean does not hold the wavevector magnitude fixed between the two wedges, so an isotropic transfer function "
     "weighted them differently. Forming the ratio inside a magnitude ring and averaging afterwards makes the "
     "cancellation exact. Two further controls failed and were also design faults rather than results: see disciplines "
     "629 and 630.",
     "ORCH (MEASURED, 5 controls on real captures); `experiments/ORCH-drift-check/anisotropy.py`"),

    (1282, "**THE 0.9315 COVERAGE CROP IS NOT IMPOSING A HARD BAND LIMIT ON THE RENDER.** "
           "`merge_cmd.rs:1245` reports that the field of view is scaled to 0.9315 so every frame covers every pixel, "
           "\"then upsampled to keep the output dimensions\", which predicts a spectral cliff at **0.4657 cyc/px**. There "
           "is none: planting an *additional* 0.9315 round trip removes **7.8x** of the energy at 0.496 cyc/px, which it "
           "could not do if the render were already limited there.",
     "Claimed narrowly and deliberately: the positive control for this test **did not land** (the knee-finder returned "
     "0.3169 cyc/px for both the render and a known round trip, because steepest-log-gradient finds no cliff in a smooth "
     "power law), so `upsample_check.py` exits 1 and no quantity from it is reportable. The 7.8x ratio above is read off "
     "the raw spectra rather than the broken knee statistic, and it is enough to weaken the hypothesis without "
     "supporting any replacement. Softness must not be blamed on the coverage crop on present evidence. Note the crop is "
     "coupled to M103: a solve that applies the *full* drift will demand a LARGER crop.",
     "ORCH (MEASURED spectra, positive control FAILED, claim limited accordingly); "
     "`experiments/ORCH-drift-check/upsample_check.py`"),

    (1283, "**THE GATE-TO-n_eff LADDER ON A 299-FRAME REAL STACK.** On `bee-3-cpl`: gate 0/1/2/4/8 gives mean n_eff "
           "**1.000 / 4.562 / 19.182 / 55.321 / 68.096**, with **100.00% / 60.89% / 51.15% / 38.77% / 23.86%** of pixels "
           "still at n_eff=1, and a modelled sigma gain of **1.0000x / 0.7810x / 0.6974x / 0.6273x / 0.5497x**.",
     "Gate 1 is the rung that lands nearest fact 212's nwide=3 target, at n_eff 4.562. The gap between gate 2's n_eff of "
     "19.182 and that target is large enough that the difference between the two candidate defaults is not a matter of "
     "taste, which is what M98 is adjudicating. The n_eff=1 column is the more interesting one for the halo and occlusion "
     "work: even at gate 8, **23.86%** of pixels are still pure selection with no averaging at all.",
     "ORCH (MEASURED, single decode pass, 5 gates); `C:\\dev\\strehl-out\\ORCH-gate\\neff-ladder.txt`"),
]

DISCIPLINES = [
    (628, "**An instrument needs specificity as well as sensitivity, and the specificity control is the one that "
          "changes the design.** A plant proves the instrument can respond; it does not prove the instrument responds "
          "to the right thing. Pair every sensitivity plant with a plant of a DIFFERENT defect that the metric claims "
          "to be blind to, and require it to read null. The anisotropy metric passed its sensitivity plant while a "
          "direction-blind Gaussian moved it 44% (0.5268 -> 0.3069) -- it was a softness detector, not an orientation "
          "detector, and only the specificity arm could tell. Fact 1281."),
    (629, "**Choose a plant's sub-step count from its magnitude, or the plant models something other than what it "
          "names.** A radial smear integrated over a fixed 7 sub-steps is not a smear at 150 px, it is seven copies "
          "25 px apart, and a comb's transfer function has passbands rather than a monotone roll-off. That plant left "
          "the outer annuli untouched (0.6337 -> 0.6304) while firing at the CENTRE, where its spacing happened to "
          "land its first zero inside the measurement band -- the exact inverse of the geometry it was supposed to "
          "model, which would have been read as the instrument failing. Require the largest step to be at most half a "
          "pixel, and interpolate: a nearest-neighbour plant at 1 px rounds to a no-op and silently reports mean "
          "|delta| of 0.00 DN."),
    (630, "**Select the measurement population on the UNTREATED data and reuse that exact set in every arm.** A "
          "treatment that destroys signal will otherwise select its own survivors. A per-arm texture-quantile filter "
          "dropped precisely the outer tiles a planted radial smear had hit hardest, leaving a population enriched for "
          "tiles the plant had failed to affect, and a 150 px plant consequently read as a 0.0026 change. This is the "
          "same failure mode as fitting a threshold on the test set, and it is invisible unless the arms are paired by "
          "construction."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    # ---- locate anchors -------------------------------------------------
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1278 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^627\. ", l))
    assert disc_idx > fact_idx, (
        f"expected disciplines below the fact table; got fact {fact_idx}, disc {disc_idx}")

    # ---- build rows and validate BEFORE writing anything ----------------
    fact_rows = []
    for fid, claim, interp, src in FACTS:
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need exactly 5"
        assert "\n" not in row
        fact_rows.append(row)

    disc_rows = []
    for did, body in DISCIPLINES:
        row = f"{did}. {body}"
        assert row.startswith(f"{did}. ")
        assert "\n" not in row
        disc_rows.append(row)

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    # ---- splice: HIGHER index first ------------------------------------
    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = disc_rows
    out[fact_idx + 1:fact_idx + 1] = fact_rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))

    print(f"folded {len(fact_rows)} facts after line {fact_idx}, "
          f"{len(disc_rows)} disciplines after line {disc_idx}")
    print(f"facts {FACTS[0][0]}-{FACTS[-1][0]}, "
          f"disciplines {DISCIPLINES[0][0]}-{DISCIPLINES[-1][0]}")


if __name__ == "__main__":
    main()
