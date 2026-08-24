"""Fold M101's negative result. Facts 1313-1322, disciplines 647-654.

The election does not prefer sensor defects on this sensor, because on this
sensor defects are 1.5 DN tall and the election does not turn on until 100-250.
A planned subsystem is cancelled by its own deciding measurement.

Includes the orchestrator's third briefing defect of the night: a dispatch that
named none of the four prior reports on the same question and asserted a read
noise constant that is not shipped.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1313, "**THE ELECTION LANDS ON SENSOR DEFECTS AT EXACTLY CHANCE.** Of elected pixels, **0.0017782** sit on a "
           "defect against a map density of 0.0017707, a shift control of 0.0017732 and a random control of "
           "0.0017670 -- **z = 0.24**. Enrichment of the election at defect coordinates is **0.987x** against a "
           "pre-registered **1.5x** bar (random 1.007x, permuted 1.024x), and it is flat across five decades of "
           "matched brightness: 1.035, 0.989, 1.014, 0.987, 0.901.",
     "The commission's premise was that `box_mean_27` of the Sobel magnitude over sigma(L) is a local energy "
     "detector, a hot pixel is a local maximum of gradient energy, and so the election has a systematic reason to "
     "prefer whichever frame puts a defect on the pixel being decided. **Measured, it does not.** A defect is "
     "elected in 0.0034 of the frames it is visible in; uniform chance over 299 frames is 0.00334. **No correction "
     "ships and `defect.rs` was not written** -- a planned subsystem cancelled by its own deciding measurement, "
     "which is the cheapest outcome available.",
     "M101 (MEASURED, 4 controls); `docs/research/M101-defect.md` P8-P9"),

    (1314, "**THE DRAG IS REAL AND THE TRAIL IS NOT: ALIGNMENT REDUCES A DEFECT'S DEPOSIT RATHER THAN SMEARING IT.** "
           "Geometric trail across a stack **97.7 px** median, **200.1 px** max -- the scene genuinely is dragged "
           "across the sensor-fixed defect. Pixels actually elected on the trail: **0.931** against a shift null of "
           "**0.937**, while an identity-warp arm gives a geometric trail of 0.0 px and an elected trail of exactly "
           "**1.000**.",
     "**This is the pre-registered acceptance test that M22 section 7 and M48c fact 30 both left explicitly for the "
     "aligner, and the answer is the opposite of what both predicted.** M48c's words were that re-running its script "
     "07 unchanged after alignment would be \"a ready-made, pre-registered acceptance test for a subsystem that does "
     "not exist yet\". The subsystem now exists (M86 solved, M97 wired it in at `885e9f7`, on by default), the test "
     "ran, and warping drives the deposit **below** the identity arm's 1.000 instead of smearing it into a trail. A "
     "prediction held in the corpus for two milestones, refuted the first time it could be run.",
     "M101 (MEASURED, shift null + identity arm); refutes M22 section 7 and fact 30"),

    (1315, "**A REAL HOT PIXEL PERTURBS STREHL'S FOCUS MEASURE BY 0.8% OF THE MEASURE'S OWN NOISE FLOOR.** 320 "
           "synthetic hot pixels at 8 amplitudes: enrichment is flat to 100 DN (1.03, 1.00, 1.00, 0.97, 0.96, 1.06) "
           "then monotone -- **1.20x at 250 DN, 1.43x at 500**. The turn-on was **DERIVED before the run** from the "
           "shipped arithmetic: an isolated spike of amplitude A raises `box_mean_27` by 2.118A/729, so "
           "`dFocus = 0.002905*A/sigma_L`, which at the measured sigma_L = 17.05 DN crosses "
           "`FOCUS_NOISE_SD = 0.015214` **between 100 and 250 DN**. Real defects reach a light frame at **1.5 DN**, "
           "giving dFocus = 1.28e-4 = **0.0084 sigma**.",
     "**This is the measurement that makes the null admissible**: the instrument detects an election preference "
     "where one exists, and begins to do so within one ladder step of a closed form written down in advance. The "
     "margin is at least **67x**, and by the derivation ~120x, below the amplitude that would matter. Planting ran "
     "in its own arm per discipline 615 -- it perturbed 0.206% of the winner map and that map was never used for "
     "the real measurement; unplanted sites inside the planted run read chance. **The focus measure does not love "
     "hot pixels on this sensor, because on this sensor hot pixels are 1.5 DN tall.**",
     "M101 (MEASURED ladder + DERIVED prediction); `M101-defect.md` sections 4.7-4.8, P11"),

    (1316, "**R AND G1 DEFECT DETECTIONS DO NOT REPRODUCE, AND TWO PUBLISHED CENSUSES SHIPPED THEM AS DEFECTS.** "
           "Split-half Jaccard **0.077** (R) and **0.074** (G1) against a random-coordinate placebo of **0.000**. G2 "
           "and B reach **0.401** / **0.380** against placebos of 4.7e-4 / 3.9e-4 -- far above chance, far below the "
           "0.80 bar -- with recovery monotone in amplitude, **0.36** below 0.5 DN rising to **0.86-0.91** above 4 "
           "DN. The odd/even sensor-row asymmetry replicates independently at **61.1x** against M48c's 68x.",
     "The 235 R/G1 sites are consistent with the tail of the noise, not with a defect population, and that is "
     "physically coherent: the two odd rows carry 61x more real defects, so a fixed 6-sigma cut on the even rows is "
     "sampling almost pure noise. **M22 and M48c both published those sites and neither ran a split-half.** The "
     "monotone recovery curve on G2/B is the signature of a real population whose weak end sits on the detection "
     "cut -- a per-group detection probability p yields Jaccard ~ p/(2-p), and the measured 0.40 corresponds to "
     "p ~ 0.57.",
     "M101 (MEASURED, split-half + placebo); corrects M22 fact 160 and M48c facts 783-808"),

    (1317, "**NO POPULOUS DEFECT MAP IS REPRODUCIBLE ON THIS SENSOR.** Replacing the count-based criterion with a "
           "physical, ISO-invariant one (the median across the 11 ISO groups of the gain-normalised excess) and "
           "sweeping the amplitude cut, split-half Jaccard peaks at **0.51**; the only cut that reaches the 0.80 bar "
           "leaves **5 sites on the whole sensor**. Maximum defect amplitude is **11.5 e- on G2** and 8.3 e- on G1 "
           "-- the only two planes the election can see.",
     "Independently replicates M22 fact 162's finding that only **3 pixels** sensor-wide are unambiguous, by a "
     "different criterion. **The map's population and its reliability are in direct tension and no operating point "
     "has both.** The defensible statement is not \"there are 14,604 defects\" but \"there are ~5 defects and a "
     "large penumbra of sites that a 6-sigma cut selects about 57% of the time\".",
     "M101 (MEASURED, cut sweep); replicates M22 fact 162"),

    (1318, "**WHAT THE DELIVERED DARKS MEASURE IS A FIXED PER-SITE OFFSET, NOT DARK CURRENT.** `bee-3-cpl` runs at "
           "**20x** the darks' exposure at the same ISO 100 gain; the in-situ excess is **1.81x**, not 20x. "
           "H_dark-current predicted 20x and is **FALSIFIED**; H_fixed predicted 1x and is approximately confirmed. "
           "A two-point solve over t = 0.01 s and 0.2 s gives a fixed **c = 3.47 e-** and a thermal "
           "**d = 15.4 e-/s**, so **~95% of what a 1/100 s dark measures is the fixed part**.",
     "**Every one of the 242 delivered darks is 1/100 s**, so nothing in the corpus could separate the two terms, "
     "and M22's and M48c's amplitudes are both silently a mixture. The lever came free from the owner's own "
     "photographs. Consequence: the map does **not** scale with exposure the way a dark-current model predicts, and "
     "a 10 s exposure would sit at ~157 e- -- a different regime that this measurement does not cover.",
     "M101 (MEASURED + DERIVED two-point solve); `M101-defect.md` section 4.2, P7"),

    (1319, "**THE SHIPPED ELECTION IS NOW INDEPENDENTLY REPRODUCED TO 0.011%.** An independent Python "
           "reimplementation matches `strehl stack --stats` on the same 299 frames: median **3.5360 vs 3.5364** "
           "unwarped (**-0.011%**, p10 +0.03%, p90 -0.10%). Sobel, box mean, sigma normalisation, the 17x17 "
           "regulariser, argmax and tie-breaking are all exact. On the warped path it reads **+6.46%** (4.2680 vs "
           "4.0088) against a 2% bar.",
     "**The first external reproduction of the shipped decision arithmetic, and it passes.** The registered bar "
     "fails only on the warped limb, which localises the entire disagreement to M101's own Catmull-Rom resampler "
     "rather than to the decision -- candidate causes named and untested: coverage and edge handling in "
     "`warpmap.rs::gather_checked`, and edge-replicating rawpy's 3514 columns up to rawler's 3516 (M48c fact 33). "
     "**The failed limb was reported as failed and the conclusion qualified accordingly**; it does not reach the "
     "headline, because every headline is a ratio between coordinate sets scored inside one winner map, so a global "
     "scale offset cancels exactly.",
     "M101 (MEASURED, dual-arm validation against the shipped binary); P12"),

    (1320, "**THE SHIPPED NOISE MODEL UNDER-PREDICTS DARK-FRAME SPREAD BY 20-30%, NOT BY SIX ORDERS OF MAGNITUDE.** "
           "`sigma_robust / sigma_model` on the neighbour excess at ISO 100, n = 20, is **1.20 to 1.30** across the "
           "four planes, and a 6-sigma model cut flags **21,211** sites against the robust criterion's **14,604** -- "
           "over-flagging by **45%**.",
     "Registered in the right direction: the model carries no DSNU term and does over-flag. But **M48c fact 4's "
     "implied magnitude of ~1e6 is not what a 6-sigma cut on a 20-frame mean produces.** A correction to a "
     "committed fact, and a reminder that an order-of-magnitude claim about a model's error needs the estimator and "
     "the sample size attached to it.",
     "M101 (MEASURED); corrects the magnitude implied by M48c fact 4"),

    (1321, "**THE OWNER'S STABILISATION FRAMES ARE MEASURABLY HARMLESS.** The first two frames of each dark group "
           "differ from the rest by **-0.064 to +0.014 DN**, below read noise in every one of the 11 ISO groups.",
     "The owner flagged \"first 2 shots for stabilization\" when delivering the darks. Measured, discarding them is "
     "unnecessary and the corpus can use all 22 frames per group. A user-supplied caveat checked rather than "
     "obeyed, at the cost of one script arm.",
     "M101 (MEASURED, all 11 ISO groups); P13"),

    (1322, "**THE ORCHESTRATOR'S BRIEF FOR M101 NAMED NONE OF THE FOUR PRIOR REPORTS ON THE SAME QUESTION AND "
           "ASSERTED A CONSTANT THAT IS NOT SHIPPED.** Rule 40 requires a dispatch to name every prior report; rule "
           "43 requires an assertion of absence to carry the search that establishes it. The brief carried neither, "
           "and described the darks as freshly delivered calibration data -- these exact 242 frames had already been "
           "used for this exact purpose by **M22, M48c, M29 and M48**. The brief also stated \"RN ~3 e-\"; "
           "`profile.rs` ships `read_noise_e_low = 4.20` and `read_noise_e_high = 1.2392`.",
     "**The milestone was saved by the agent, not by the orchestrator.** M101 searched `docs/research/` on its own "
     "initiative before measuring anything, found the prior work, and re-ran commission section 1 as an explicit "
     "replication with the two committed censuses as external positive controls -- which is why fact 1316 exists at "
     "all. Taken at face value the brief would have bought 2.5 hours of rediscovering a published map. **Third "
     "briefing defect of the night**, same root as disciplines 640 and 645 (reasoning from memory rather than from "
     "a current read), plus a new failure mode: a fabricated constant stated with the authority of the shipped "
     "source.",
     "ORCH (error acknowledged); M101 section 0.2-0.3; `crates/strehl-core/src/profile.rs`"),
]

DISCIPLINES = [
    (647, "**A split-half is not a placebo, and neither is sufficient alone.** M101's placebo (B2) passed at 0.000 "
          "on the same plane where the split-half (B1) failed at 0.077. They answer different questions: the placebo "
          "proves the instrument is not hallucinating agreement between unrelated coordinate sets; only the "
          "split-half proves the map is a map. **Two published censuses of this sensor ran neither.** Any claim that "
          "a detected population is real needs both. Facts 1316, 1317."),
    (648, "**Cross-census agreement is not reproducibility when both censuses read the same frames.** M101's map "
          "replicates M48c's independent census to **+7.0%** at site-by-site Jaccard **0.90**, and simultaneously "
          "fails its own split-half at **0.077-0.401**. There is no contradiction: two criteria applied to one noise "
          "realisation will agree with each other while each is individually unreliable. **Agreement between "
          "analyses is evidence about the analyses; only resampling the data is evidence about the data.** Fact "
          "1316."),
    (649, "**When a registered bar fails, first ask whether your own instrument caused it.** M101's split-half "
          "halved the frame count, which raised the DN cut, which made the two halves maps of *different "
          "sensitivity*. It re-ran with the cut held fixed in DN at the full map's value: G2 moved 0.352 to 0.401 "
          "and the failure survived. **Do that before either moving the bar or believing the result** -- the bar "
          "must not move, and a self-inflicted failure is not a finding. Fact 1316."),
    (650, "**Give a null an amplitude ladder, not just a control.** \"No enrichment\" is a weak claim that any "
          "insensitive instrument can produce. \"No enrichment below 100 DN, 1.20x at 250, 1.43x at 500, and the "
          "real defect is 1.5 DN\" is a **bound**, and it converts a null into a measured margin of 67x. Every null "
          "this project ships should carry the dose at which the effect would have been visible. Fact 1315."),
    (651, "**Predict where a positive control will turn on before you plant it.** M101 derived "
          "`dFocus = 0.002905*A/sigma_L` from the shipped arithmetic and predicted the election would begin "
          "preferring a planted spike between 100 and 250 DN; it did. A control that confirms only *that* an "
          "instrument responds is far weaker than one that confirms *where* -- the latter tests the model of the "
          "mechanism, not merely the wiring, and it is what licenses extrapolating the null down to the real "
          "amplitude. Fact 1315."),
    (652, "**Never put a numeric constant in a dispatch that you have not read from the shipped source in the same "
          "session.** The M101 brief asserted \"RN ~3 e-\" as this sensor's read noise. `profile.rs` ships 4.20 e- "
          "below ISO 400 and 1.2392 above it; ~3 appears nowhere except as fact 795's re-labelling of 1.2392 into "
          "electrons, which is explicitly not what the model evaluates. **A fabricated constant in a brief carries "
          "the orchestrator's authority** and will be used unless the agent independently re-derives it. Fact 1322."),
    (653, "**Rules 40 and 43 exist because the orchestrator is the one most likely to break them.** The M101 brief "
          "presented as open a question that four committed reports had already worked, and the agent -- not the "
          "orchestrator -- caught it by searching `docs/research/` before measuring. **A subordinate's literature "
          "search is the last line of defence, not the first.** Brief every milestone from a search run in the same "
          "session, and put the search in the dispatch, not the conclusion drawn from it. Fact 1322."),
    (654, "**Look for an accidental lever in data already held before commissioning a capture.** Every one of the "
          "242 delivered darks is 1/100 s, so the calibration set alone could not separate a fixed per-site offset "
          "from dark current, and two published reports quoted the mixture without noticing. The owner's ordinary "
          "photographs run at 20x the exposure at the same gain, and that single uncontrolled difference settled the "
          "fork for free. **A dataset that varies is worth more than one that is internally consistent.** Fact "
          "1318."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1312 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^646\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need 5"
        rows.append(row)

    drows = [f"{did}. {body}" for did, body in DISCIPLINES]

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1313-1322 after line {fact_idx}, disciplines 647-654 after line {disc_idx}")


if __name__ == "__main__":
    main()
