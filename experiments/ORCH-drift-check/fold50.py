"""Fold M95, M97b, M102, M87 and M104b. Facts 1323-1337, disciplines 655-662.

The night's two structural results: the default viewing render was binning
32.97 MP to 8.24 MP (fixed, shipped), and the alignment null every milestone
has measured was never a property of alignment -- it is a solve that applies a
third of the drift.

Includes the orchestrator's near-miss: the binning fix does not reach the
artefact the owner complained about, because the gallery already bypassed it.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1323, "**THE DEFAULT VIEWING RENDER WAS BINNING A 32.97 MP CAPTURE TO 8.24 MP, AND THE DISCARDED BAND IS NOT "
           "EMPTY.** Three preconditions, all measured: the optics deliver **44.4%** MTF at the binned Nyquist "
           "(48.94 cy/mm against the sensor's 97.88) even at the most pessimistic magnification swept; the capture "
           "carries green detail there (`E` = **3.824, 3.626, 7.166, 8.360** against a pre-registered bar of 2.0, "
           "with a dose-response tracking the focus sweep at **r = 0.877-0.941**); and the merge *preserves* it "
           "(**1.869-3.884x** a single frame) right up to the final box average. Cost: a **factor of 2 in linear "
           "resolution**, plus **13.8-20.6%** of top-octave green power destroyed inside the band that is retained.",
     "**Shipped at `56bd846`** from M95's verbatim §11 patch, applied by the orchestrator because M95 owns neither "
     "file. The hazard it was shaped around: in `write_merged` the `if demosaic { ... return }` branch sits "
     "**before** the byte-frozen measurement branch, so a naive default-on would have hijacked the measurement path "
     "and invalidated every number in the corpus; keying the default off `--srgb` makes the branch unreachable from "
     "the measurement invocation by pure boolean logic. Byte freeze verified by the orchestrator, not by M95: "
     "SHA256 `D99F5D82...76CA` identical before and after, `--srgb` now 7032x4688, `--srgb --binned` 3516x2344, "
     "`cargo test -p strehl-cli --bins` 59/59.",
     "M95 (MEASURED, B1 fired 4/4, F1-F3 did not fire); applied by ORCH at `56bd846`"),

    (1324, "**THE BINNING DEFECT DOES NOT EXPLAIN THE OWNER'S COMPLAINT, BECAUSE THE ARTEFACT HE JUDGED ALREADY "
           "BYPASSED IT.** `experiments/ORCH-drift-check/gallery.py:63` passes `--demosaic`, and all seven gallery "
           "renders measure **32.97-33.00 MP** on disk. The renders the owner called soft were never binned.",
     "**The orchestrator was one sentence from reporting the binning fix to the owner as the answer to his "
     "complaint.** Fact 1323 is true, ships, and helps every future user; it changes nothing about the specific "
     "images that prompted the verdict. This is the same failure class as facts 1297 and 1304 -- a mechanism "
     "confirmed in general and never checked against the artefact in hand -- caught this time only because the "
     "gallery script was re-read before the claim was made rather than after.",
     "ORCH (MEASURED, tifffile on the 7 emitted files); near-miss disclosed"),

    (1325, "**THE ALIGNMENT NULL WAS NEVER A PROPERTY OF ALIGNMENT.** On `dry-erase-marker-head-cpl` at `--gate 2`, "
           "against a ZOOMNULL denominator that discards relative registration while keeping the same resampler and "
           "field of view: **ALIGNED as shipped removes 33.3% of the drift and scores 1.0330 / 0.9789 / 1.0003** "
           "(centre/mid/outer) -- a null. **Gain-corrected it removes 89.5% and scores 1.1866 / 1.3161 / 1.1492**, a "
           "**19-32% sharpness win**. UNALIGNED reads 1.0742 / 1.0403 / 1.0025, pricing the resampling cost at "
           "**~7%**, which the corrected arm pays and still wins net of.",
     "**Every null this project has measured on alignment was measuring the half-drift defect.** This independently "
     "reproduces M86's 0.9859x and M85's 0.985x on a *different stack* with a *different instrument* -- three routes, "
     "one answer -- and converts them from \"alignment does not help\" to \"a solve that applies a third of the "
     "drift does not help\". This is the largest unshipped improvement to what the owner sees, and it is now "
     "M103's deliverable rather than a characterisation exercise.",
     "M97b (MEASURED, 3 arms + ZOOMNULL); `docs/research/M97b-align-visible.md` §5, P2-P5"),

    (1326, "**THE SEAM CONFOUND RUNS AGAINST THE ALIGNMENT RESULT, SO 19-32% IS A LOWER BOUND.** Gradient energy "
           "rewards misregistration seams: GAINED against a deliberately jittered arm reads **0.674 / 0.665 / "
           "0.851**, i.e. **the jittered render measures sharper**. Better registration produces fewer seams, GAINED "
           "is the best-registered arm, and it still measures the most energy, so the surplus cannot be seams.",
     "A planted confound that was expected to threaten the result and instead bounds it from below. Corroborates "
     "M86's ARGUED seam explanation and M97 §6's independent finding that misregistration raises a band-limited "
     "detail metric by 5.6%. **Report the direction a confound runs, not merely its presence** -- a confound running "
     "against the claim is evidence, not a caveat.",
     "M97b (MEASURED, planted jitter arm); P6"),

    (1327, "**OPENED AT 1:1, THE GAIN-CORRECTED RENDER IS BETTER BUT NOT TRANSFORMATIVE, AND IT BRINGS A NEW "
           "ARTEFACT.** M97b rendered both arms full-resolution through the real binary and looked: centre is a "
           "**marginal call** (as §5 predicts, the scale error is zero at the centre of rotation); lower-right shows "
           "individual fibres separating where the shipped render gives a flatter mass; **and the corrected render "
           "shows waxy, smeared blobs in the bright low-texture region that the shipped render does not**, cause "
           "unknown. The upper-left panel locked at NCC 0.2253 and **no conclusion was drawn from it**.",
     "The honest visual verdict attached to a strong metric result, including an artefact that was inconvenient to "
     "report. Sets the expectation for the owner: shipping the gain correction will be **visible but modest**, not a "
     "different photograph. The blobs must be designed against before it ships -- if they survive, the owner sees "
     "them.",
     "M97b (MEASURED metric + observed render, artefact disclosed); §8"),

    (1328, "**M97b's OWN VIEWER LIED TWICE BEFORE ITS OUTPUT WAS BELIEVED.** (1) The scale ladder returns *the "
           "magnification to apply to B*; it was read as *B's magnification*, so the first run took a smaller crop "
           "from the corrected render and **upscaled** it -- blurring the treatment arm and handicapping the wrong "
           "side. (2) A single full-resolution NCC lock scored **0.9244** on a self-control that must return 1.0000, "
           "because on macro texture the full-resolution signal is dominated by the fine detail that genuinely "
           "differs between arms. Final controls: self-vs-self **1.0000** on all three panels, and a plant that "
           "displaces the starting guess by **(+90, -110) px** still recovers the exact truth.",
     "**A self-control that starts 1 px from the answer does not demonstrate a 158 px search range; the planted one "
     "does.** Both defects were caught by controls that returned a number close to but not equal to the required "
     "one, which is the signature this project keeps finding: 0.9244 against a required 1.0000 is a failure, not a "
     "pass. The comparison crop was also deliberately handicapped *against* the arm expected to win.",
     "M97b (MEASURED, 2 self-caught instrument defects); §8"),

    (1329, "**THE SIMULATOR IS NOT ESTABLISHED, ON ITS OWN REGISTRATION, BECAUSE BOTH DEFECT PLANTS FAILED TO "
           "REDDEN -- AND NEITHER FAILURE WAS THE INSTRUMENT'S.** **D1** planted a one-frame correspondence shift; "
           "the estimator recovered **-1.0000 frames exactly** (n = 44,643) and the bar was `\\|median signed\\| <= "
           "1.0`, so the plant **landed exactly on the threshold and passed**. **D2** sized an unmodelled warp as a "
           "fraction of the *sensor* half-diagonal and it did nothing; swept rather than re-tuned, it reddens at "
           "**2.91 depth-slab widths**, and the median statistic never reddens at any magnitude. Green: round-trip "
           "median `\\|e\\|` **0.0000**, **97.94%** within +/-2, all three realism bars, and a Z2 index map "
           "**bit-identical** to unplanted.",
     "M102 registered in advance that if a defect plant fails to redden then the round-trip is not a check, and then "
     "held itself to it rather than reclassifying a passing bar as success. The two failures are both transferable "
     "lessons about plant design rather than facts about this simulator (disciplines 656, 657).",
     "M102 (MEASURED, self-failed on its own registration); `docs/research/M102-simulator.md`"),

    (1330, "**THE CALIBRATED NOISE MODEL PREDICTS REAL PER-FRAME NOISE ON `bee-3-cpl` TO 0.54%** (ratio 0.9946).",
     "The project's crown jewel, validated against a real capture by an agent that was building something else and "
     "had no stake in the answer. It is also the reason M102 caught its own dead estimator: the same function "
     "returned **exactly 0.000** on all 32 synthetic frames (a MAD over a constant-filled image) in the same run "
     "that returned 0.9946 on the real stack -- the real-data arm was the control that exposed the synthetic arm.",
     "M102 (MEASURED, real vs predicted); P-series"),

    (1331, "**THE ALIGNER RECOVERS 96.96% OF PLANTED DRIFT ON SYNTHETIC DATA, AGAINST 54.3% ON REAL CAPTURES -- AND "
           "THE SYNTHETIC TRACK WAS PLANTED LINEAR.** M102's §6 records that the breathing track was assumed linear "
           "and §7 names the missing capture as **the shape of the track**: fact 1177 gives the total drift and "
           "nothing in the corpus gives its curvature. M102 also measured that **cycle consistency under-states real "
           "alignment error by ~6x** (0.604 px shortfall against its own 0.103 px cycle-consistency floor).",
     "**ARGUED, orchestrator, not measured:** if the solver's model is linear and the plant is linear, 96.96% is a "
     "statement about arithmetic and not about breathing -- circular in exactly the way M102 correctly flagged its "
     "own photometric drift as circular (it reproduces fact 1254's *predicted* 1.1132, not the measured 1.1091, and "
     "M102 warned M99 not to read that agreement as validation). If the real track is curved, the fix is a per-frame "
     "gain rather than a scalar. Routed to M103 as a hypothesis to kill before it multiplies by 1/0.543.",
     "M102 (MEASURED both numbers); ORCH (ARGUED circularity, unmeasured)"),

    (1332, "**AN OUT-OF-TREE GENERATOR EMITTING DNG CATCHES A BUG CLASS AN IN-CRATE ARRAY GENERATOR CANNOT EXPRESS.** "
           "M102's first synthetic file decoded **exit 0, \"3 ok, 0 failed\"** while reporting an active area of "
           "**3737911296 x 646971392** and a black level of 0.0027 -- every inline TIFF tag right, every heap tag "
           "garbage.",
     "The architecture argument settled by measurement rather than by preference: a generator that hands the shipped "
     "binary an in-memory array exercises none of the decode path, and the decode path is where this failure lived. "
     "It also shows the shipped decoder reporting success on a file it had not understood, which is a separate "
     "finding worth its own follow-up.",
     "M102 (MEASURED, first-run decode); §architecture"),

    (1333, "**THE BAR THE ORCHESTRATOR SET FOR THE HALO FIX WAS UNFIT, AND M87 REPLACED IT BEFORE BUILDING.** The "
           "instruction was to pair halo suppression with **fidelity measured against truth**. M87's objection: "
           "truth exists only on synthetic data, **which is where the previous attempt already passed** (band RMSE "
           "3.46% -> 1.82%); it failed on the real bee, where there is no truth. **A bar that binds only where the "
           "previous attempt succeeded cannot catch the next failure.** Its replacement, **Blur-Matched Fidelity**, "
           "is truth-free: race the candidate against a Gaussian blur bisected to suppress the *same named coarse "
           "band*, then compare the *named fine band*.",
     "Registered V1-V4 in the docstring before running, with **V4 as the broken arm**, on the real full frame at "
     "4688x7032 read with tifffile rather than PIL (fact 1302). V1 **PASS** (1.000000 both bands where unchanged), "
     "V2 **PASS**, V4 **PASS** (4.43), **V3 FAIL**. The orchestrator asked for a bar and got a better one plus the "
     "argument for why; discipline 661 is M87's, not mine.",
     "M87 (MEASURED, bars pre-registered in code); `docs/research/M87-occlusion.md` §23, P57-P59"),

    (1334, "**THE SHIPPED HALO CORRECTION REMOVES FINE STRUCTURE HARDER THAN IT REMOVES THE VEIL, AND ITS AUTHOR'S "
           "OWN PREDICTION OF WHY WAS WRONG.** V3 required the coarse band to fall further than the fine band; "
           "measured **0.9146 coarse against 0.9058 fine** -- it fails, and that is §16.9's visual result "
           "(\"it erases the abdomen hair fringe\") expressed as a number. But M87 predicted **BMF <= 1.05**, i.e. "
           "no better than a blur, and measured **4.43**: at matched coarse-band suppression a Gaussian blur keeps "
           "**20.5%** of the fine band while the correction keeps **90.6%**.",
     "**M87 withdrew its own §16.9 implication of blur-grade destruction in place, with a callout at the section "
     "head, and the do-not-enable conclusion now rests on V3 rather than on its reading of a render.** The "
     "reclassification matters for what comes next: **the defect is insufficient selectivity, not destruction**, "
     "which is a far more tractable problem than the corpus previously recorded. The annulus milestone's success "
     "condition is now stated so it cannot be gamed: V1 exact, V2 >= 0.98, V3 PASS, V4 >= 4.4, plus the synthetic "
     "band RMSE.",
     "M87 (MEASURED, own prediction falsified and withdrawn in place); P57-P59"),

    (1335, "**M87 WITHDREW ITS OWN PLANNED DISAGREEMENT ON ITS OWN EVIDENCE.** It intended to argue for gating the "
           "existing correction on M96's disconnected set (fact: 25.247% of `bee-3-cpl` pixels) instead of building "
           "a matting term -- cheaper, and aimed at the default-ON blocker. It killed the idea itself: **the abdomen "
           "hair fringe is a semi-transparent mat at the silhouette, so it is genuinely an occluding boundary and "
           "would be genuinely disconnected.** A gate would flag and destroy it exactly as the current fix does.",
     "**Gating cannot fix a matting problem.** An agent that was invited to disagree, prepared a specific "
     "disagreement, tested it against its own evidence before making it, and reported the refutation instead of the "
     "argument.",
     "M87 (self-refuted before arguing); §23"),

    (1336, "**A BAND-POWER SPREAD ACROSS DEMOSAIC ALGORITHMS IS NOT A MENU OF AVAILABLE WINS.** `AAHD`, `AMAZE`, "
           "`DCB`, `VCD`, `LMMSE` and `DHT` are all **content-adaptive**, so ranking them by band power ranks "
           "**hallucination as resolution**, and the winner of such a ranking is whichever algorithm invents the "
           "most convincing structure. The **0.3518 dex** spread (`LINEAR -3.2552` ... `AAHD -2.9033`) is "
           "simultaneously an upper bound on what could be won and an upper bound on what could be faked, and band "
           "power does not distinguish them.",
     "**Corrects the orchestrator's framing**, which offered the spread to two milestones as \"the second free "
     "win\". The corollary was already implicit in `demosaic.rs:19-51`, which chose MHC precisely because *\"a "
     "linear interpolator can only blur and alias, never hallucinate, so a sharpness metric downstream cannot be "
     "inflated by it\"* -- the orchestrator quoted the spread without reading the reasoning in the file documenting "
     "the choice. Registered by M104b **before any arm was decoded**.",
     "M104b (PRE-REGISTRATION, no measurement taken); `docs/research/M104b-demosaic-lever.md` §1.1"),

    (1337, "**A MAGNITUDE CAN NEVER BE AN UNBIASED ESTIMATOR OF SHARED POWER.** M95 retired two instruments before "
           "admitting a third. The raw high-band ratio (6.46 / 9.61 / 9.21 on subject crops) **failed its own "
           "pre-registered control**: the defocused background, which by construction has no detail, read **7.73**. "
           "A cross-spectrum magnitude `\\|S_xy\\|` then failed two controls -- an independent-noise null reading "
           "**0.181** instead of 0, and a planted-geometry control recovering **0.752-0.776** regardless of whether "
           "+0.50, +0.25 or -0.25 was planted. **A magnitude is non-negative, so smoothing it over a frequency "
           "neighbourhood leaves a bias floor of order 1/sqrt(N).** The admitted instrument de-ramps the "
           "cross-spectrum by the known offset and takes the **real part**, which is zero-mean for independent "
           "noise: null **+0.00385**, positive **+0.82328** (separation **214x**), planted geometry **4/4 exact**.",
     "Three instruments, two killed by their own controls, and **no number in the report uses the inadmissible "
     "one**. The general result is reusable well beyond M95: any shared-power or coherence estimator built on a "
     "smoothed magnitude carries a positive bias that looks exactly like signal.",
     "M95 (MEASURED, 2 instruments retired on their own controls); §7"),
]

DISCIPLINES = [
    (655, "**Verify that a fix reaches the artefact the complaint was about, not merely the defect it names.** M95 "
          "measured a real, large, shipped defect -- the viewing render binned 32.97 MP to 8.24 MP -- and the "
          "orchestrator was one sentence from reporting it to the owner as the answer to his verdict on the gallery. "
          "**`gallery.py` already passed `--demosaic`; every render he judged was 32.97 MP.** A general mechanism "
          "and the particular image in the owner's hands are different claims and need separate evidence. Third "
          "instance of this class after facts 1297 and 1304. Fact 1324."),
    (656, "**A bar must not equal the plant it is meant to detect.** M102's D1 planted a one-frame index shift "
          "against a bar of `|median signed| <= 1.0`; the estimator recovered **-1.0000 exactly** and the plant "
          "passed on the threshold. A plant sitting on its own bar cannot fail, so the arm proves nothing while "
          "reading green. Separate the plant from the bar by a stated margin before running. Fact 1329."),
    (657, "**Size a geometric plant against the scene, not against the sensor.** M102's D2 expressed an unmodelled "
          "warp as a fraction of the sensor half-diagonal and it did nothing. Swept, it reddens only at **2.91 "
          "depth-slab widths**: an index map is blind to geometric error below the scene's depth autocorrelation "
          "length, because shifting a pixel to a neighbour of the same depth changes no index. **The scale that "
          "matters is the one the statistic can resolve**, and it is a property of the content, not the detector. "
          "Fact 1329."),
    (658, "**A synthetic agreement figure is worthless wherever the synthesis assumed the thing being checked.** "
          "M102 flagged this correctly against itself -- its photometric drift reproduces fact 1254's *predicted* "
          "1.1132 rather than the measured 1.1091, and it warned M99 not to read that as validation. **The same "
          "objection applies to its 96.96% aligner recovery**, which was measured against a breathing track M102 "
          "planted as linear because the corpus does not record the track's curvature. Before quoting a simulator "
          "agreement, name what the generator assumed, and check the list against what the number is being used to "
          "prove. Fact 1331."),
    (659, "**A bar that binds only where the previous attempt succeeded cannot catch the next failure.** The "
          "orchestrator required the halo fix to be scored against **truth**; M87 refused, because truth exists only "
          "on synthetic data and the previous attempt **already passed there** (3.46% -> 1.82%) while failing on the "
          "real bee where no truth exists. Before registering a bar, run it mentally against the *last* failure: if "
          "it would have scored that failure green, it is the wrong bar. Fact 1333."),
    (660, "**Report which direction a confound runs, not merely that it exists.** M97b's gradient-energy metric is "
          "genuinely fooled by misregistration seams -- a deliberately jittered render measures **sharper** (0.674 / "
          "0.665 / 0.851). That does not weaken its result, it **bounds it from below**, because the "
          "best-registered arm still measured the most energy. A confound running against the claim is evidence for "
          "it; a confound reported without its direction is an unpriced caveat that invites dismissal. Fact 1326."),
    (661, "**An exact zero from a sensitivity check is a suspect, not a pass.** M95's geometry sweep monkeypatched a "
          "module-level constant that `s6_signal.py` binds as a **default argument**, evaluated once at definition "
          "time, so the patch changed nothing and the run printed a change of **exactly 0.00 percentage points** -- "
          "a number that reads as a clean pass and is in fact the instrument reporting it was never perturbed. The "
          "same run also hard-coded the constant a second time in a loss weight. **The exact zero is what gave it "
          "away**; treat any control that returns a perfectly round null as unverified until the perturbation is "
          "confirmed to have landed. Compare discipline 648. Fact 1337."),
    (662, "**Do not offer a spread across adaptive algorithms as a menu of available wins.** The orchestrator twice "
          "described a 0.3518 dex band-power spread across rawpy's demosaic algorithms as a free win. Six of the "
          "candidates are content-adaptive, so the ranking rewards **hallucination as resolution** -- the spread "
          "bounds what could be won and what could be faked equally, and band power cannot separate them. The "
          "reasoning was already written in `demosaic.rs:19-51`, in the file documenting why MHC was chosen. Fact "
          "1336."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1322 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^654\. ", l))
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
    print(f"folded facts 1323-1337 after line {fact_idx}, disciplines 655-662 after line {disc_idx}")


if __name__ == "__main__":
    main()
