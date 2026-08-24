"""Fold M87's veil mechanism and M103's retraction. Facts 1403-1411, disciplines 698-701."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1403, "**THE OCCLUSION HALO IS THE ABSENCE OF A VEIL, NOT THE PRESENCE OF ADDED LIGHT.** On "
           "`bee-3-cpl`, over an annulus 2-22 px outside the subject boundary, **every single frame** is "
           "darkened relative to far field by **-26.47% +/- 3.01%**. The merge reads **-6.68%**, which is "
           "**4.51 sd above the best individual frame** -- outside the ensemble entirely, not at its edge. "
           "**74.76% of the veil is removed.** A random per-pixel election over the same frames reads "
           "**-25.85%**, i.e. essentially unveiled-at-all, so the removal is a property of *which* frames "
           "the merge picks and how it combines them, not of picking at all.",
     "**This inverts the sign of the entire problem and therefore the shape of any fix.** Every prior "
     "treatment in this corpus, and every treatment in the wider field, models the halo as light spilling "
     "*outward* from the defocused foreground and tries to subtract it. It is the opposite: the surround is "
     "veiled everywhere in the source data, the merge partially *undoes* the veiling, and the bright ring is "
     "where it succeeded, seen against a background where it did not. **An additive-spill model cannot fix "
     "this, and an unmix that assumes the veil is still present is fitting something already 75% removed** "
     "(ARGUED -- this may explain M87's own -28.2% unmix result). The remedy is to make removal *uniform*, "
     "not to subtract a ring.",
     "M87 s25, registered metric over 2-22 px annulus, 299 frames (MEASURED)"),

    (1404, "**THE MECHANISM WAS FOUND BY A REGISTERED PREDICTION FAILING, AND M87 LET IT FAIL.** M87 "
           "pre-registered a bright overshoot outside the subject boundary and measured **no bright "
           "overshoot anywhere**. Ten registered bars failed as written rather than being repaired after the "
           "fact, and the mechanism that survived is the one the failures forced.",
     "**The single strongest piece of evidence in the report is not a number, it is the failure count.** A "
     "mechanism arrived at by ten bars failing is load-bearing in a way that a mechanism arrived at by one "
     "bar passing is not, because the search was demonstrably able to reject. **This is the pattern the "
     "corpus should hold up as the standard**, and it is the direct opposite of the failure mode disciplines "
     "24 and 694 record.",
     "M87 s25 (MEASURED, methodology)"),

    (1405, "**MY VEIL RING PROFILE WAS NOT A FAILED INSTRUMENT -- IT WAS A CORRECT MEASUREMENT READ WITH THE "
           "WRONG SIGN.** I reported it as failed (fact 1399) because I searched for a bright excess near the "
           "subject and found **darkness**, which I attributed to hair contamination. Re-read against fact "
           "1403, the darkness *is* the veil. Gate 4.00, referenced to the 130-200 px ring on a base of "
           "54367 DN: ring 1-5 px **-3232 DN (-5.94%)**, 5-10 **-992.7 (-1.83%)**, 10-20 **-625.7 "
           "(-1.15%)**, 20-30 **-945.3 (-1.74%)**, 30-45 **-2709.2 (-4.98%)**. Darkening throughout, with a "
           "**local minimum of darkening at 10-20 px** -- coinciding with M87's independently measured dR "
           "reach of 21 px and E(d) peak at d=13.",
     "**Two independent instruments, on different crops, with different references, agree on the shape.** "
     "My two stated defects still stand and the profile is still unusable *as-is*: the far-field reference "
     "moves 2.14% between gate arms (fact 1398), so cross-arm comparison is invalid without pinning it, and "
     "the 1-5 px ring does contain hair. **But the reason I declared it failed was wrong.** The instrument "
     "found the signal; I rejected it because the signal had the opposite sign to my expectation. Discipline "
     "700.",
     "ORCH `veil_profile.py` re-read against M87 s25 (MEASURED, RECONCILED)"),

    (1406, "**THE IMAGE THE OWNER JUDGED BREAKS M87'S OWN FROZEN HALO METRIC.** `bee3-full.png` scores "
           "**+0.280%** on the metric, against **+18.97%** on the flower bud fixture the metric was frozen "
           "on. Separately, M105b found that `gallery.py` measures a different image than the one it "
           "displays.",
     "**A metric frozen on one fixture that reads near-zero on the image a human called defective is either "
     "measuring the wrong image or the wrong quantity, and both possibilities are live here.** Until "
     "resolved, no halo number should be quoted against owner-visible quality. **Establishing which image "
     "the owner actually judged is a prerequisite**, not a detail -- two separate agents have now "
     "independently tripped over image-identity confusion in the same area.",
     "M87 s25; M105b `gallery.py` finding (MEASURED, UNRESOLVED -- question)"),

    (1407, "**EVERY ACCEPTANCE BAR THIS PROJECT HAS EVER USED ON THE SOLVE MEASURES ONE FRAME PAIR OUT OF "
           "299, AND THE MERGE DOES NOT USE THAT PAIR.** M97's signtest, M86's span bar, M97b's 'drift "
           "removed', and M103's own B3 are all **end-to-end**: they score the composition from first frame "
           "to last. But the merge gathers **each frame at its own `a_k`**, so per-frame placement is the "
           "quantity that matters. Scored both ways on 39 rungs of an independent RAW ladder in the gauge "
           "the merge actually uses (reference 149): `deep()` **as shipped** is end-to-end **150.3 px** / "
           "per-frame **36.4 px**; `iterated_wide()` is end-to-end **2.9 px** / per-frame **37.5 px**.",
     "**A fifty-fold improvement in the headline number bought nothing where it counts, and slightly "
     "regressed it.** The two quantities are nearly independent, so the project has been optimising and "
     "gating on a summary statistic that is almost uncorrelated with the thing the merge consumes. **This "
     "invalidates the acceptance criterion, not the milestones that met it** -- but every alignment quality "
     "claim in this corpus, including the headline 6.76 px and 13.578 px held-out figures, must now be read "
     "as end-to-end and therefore as *not* a statement about merge input quality. M103 withdrew its own "
     "recommendation on this basis after being told to ship it.",
     "M103 retraction, commit `1111be9`, 39-rung independent RAW ladder (MEASURED)"),

    (1408, "**RULE 6's INSTRUCTION TO DISCARD SPANS 1-2 IS MEASURED HARMFUL: IT TAKES MAX PER-FRAME "
           "PLACEMENT ERROR TO 628.1 px.** The rule was written from the end-to-end evidence that short "
           "edges under-report magnification change and that the bias is coherent under composition. Scored "
           "per frame instead, discarding them removes the densest constraints on local placement and the "
           "worst-placed frame lands **628.1 px** from truth.",
     "**A standing project rule refuted by measurement, and the refutation is only visible in the gauge "
     "fact 1407 introduced.** Both halves can be true at once -- short edges are biased *and* load-bearing "
     "-- which is precisely the case for calibrating them rather than discarding them (the metacalibration "
     "and blur-equalisation proposals). **Rule 6 amended, not quietly dropped.** The discard instruction now "
     "carries its own counter-evidence inline.",
     "M103 retraction, commit `1111be9` (MEASURED)"),

    (1409, "**THE PER-SPAN SCALE RESPONSE IS AN INVERTED U THAT NEVER REACHES 1.0 AT ANY BASELINE.** "
           "Self-measured per-pair response on `bee-3-cpl`: **0.130** at span 1, rising to **0.659** at span "
           "32, falling to **0.102** at span 192.",
     "**The estimator is biased at every baseline, which is a strictly stronger and more useful statement "
     "than 'short spans are unreliable'.** It kills the framing that long edges are trustworthy references "
     "-- span 192 is *worse* than span 32 by this measure. It also means a single global shrinkage constant "
     "cannot exist even within one scene, consistent with fact 52's cross-scene refutation but for a "
     "different reason. **And it is exactly the response function the metacalibration proposal proposes to "
     "divide by**, now measured to vary by 6.5x across the ladder within one stack.",
     "M103 retraction, commit `1111be9`, self-measured planted-increment response (MEASURED)"),

    (1410, "**`bee-3-cpl`'s BREATHING TRACK DEPARTS ITS OWN STRAIGHT CHORD BY 46.1 PLANE px AT j=200, AT A "
           "MONOTONICALLY ACCELERATING RATE.** M102's synthetic plant is linear in `j`.",
     "**M102's 96.96% recovery does not transfer to this stack.** A linear plant on a strongly curved truth "
     "measures the estimator's behaviour on a case that does not occur in the corpus. This confirms the "
     "curvature hypothesis raised against M102 at the time and means any plant used for alignment work must "
     "carry the measured curvature. Fact 63's lesson, in a new place.",
     "M103 retraction control C1, commit `1111be9` (MEASURED)"),

    (1411, "**36.4 px OF PER-FRAME PLACEMENT ERROR CANNOT BLUR A DETAILED PIXEL, BECAUSE DETAILED PIXELS "
           "TAKE ONE FRAME.** Blur from misplacement requires two or more frames with *different* placement "
           "errors landing on the same output pixel. Fact 1393 measured `n_eff = 1` in every detailed region "
           "at **every** gate including 0.00. So in detail, a placement error can only **displace**.",
     "**ARGUED, and it redirects the search for the owner's softness complaint away from alignment.** The "
     "predicted signature of fact 1407's error is therefore **local geometric incoherence**, not softness: "
     "adjacent detailed pixels elect *different* frames carrying *different* errors, so the output is a "
     "mosaic of individually-sharp patches drawn from inconsistently-placed sources -- edges that step, "
     "features that shear at election boundaries. **A candidate mechanism for the waxy blobs M103 found "
     "already present in the shipped render.** The deciding quantity is not the magnitude of `e(j)` but its "
     "frame-to-frame increment `abs(e(j+1) - e(j))`: smooth means a benign slow warp, jittery means the merge "
     "samples an incoherent field. Requested from M103 as a diagnosis, with no corrective to be built.",
     "ORCH, from fact 1393 and fact 1407 (ARGUED -- the increment is unmeasured)"),
]

DISCIPLINES = [
    (698, "**Report every placement number with the gauge it was measured in, because the gauge changes it "
          "by 2.6x.** The same track reads **98.2 px** referenced to frame 0 and **37.5 px** referenced to "
          "rung 144. A bare 'error in px' for an alignment solve is not a number, and two such numbers from "
          "different milestones are not comparable. Facts 1407, 1408."),
    (699, "**Score the bar on what the system actually consumes, not on the most convenient summary of it.** "
          "Four separate acceptance bars, across four milestones, all scored the composition end-to-end "
          "because it is one easy pair -- while the merge gathers all 299 frames independently. The error "
          "survived that long because nobody asked what the *consumer* reads. **Before accepting any bar, "
          "name the consumer and check the bar measures its input.** Fact 1407."),
    (700, "**When a mechanism turns out to have the opposite sign to the one you assumed, re-read your "
          "failed instruments before rebuilding them.** I declared my veil profile a failure because it "
          "found darkness where I predicted brightness, and reached for contamination to explain it away. "
          "The darkness was the signal (facts 1403, 1405). **A measurement that disagrees in *sign* is the "
          "single most likely place a wrong model is hiding** -- an instrument that finds a large, "
          "structured, repeatable effect you did not predict has probably not failed."),
    (701, "**A rule derived from a summary statistic must be re-scored when the gauge changes; it does not "
          "inherit its authority.** Rule 6's discard instruction was correct on every end-to-end measurement "
          "ever run against it and is harmful by 628.1 px per frame. **Standing rules in this corpus are "
          "measurements with a shelf life, not axioms** -- when a new gauge appears, the rules written in "
          "the old one are the first things to re-run. Fact 1408."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1402 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^697\. ", l))
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
    print(f"folded facts 1403-1411 after line {fact_idx}, disciplines 698-701 after line {disc_idx}")


if __name__ == "__main__":
    main()
