# External review, 2026-08 — triage and disposition

**Status:** Triage. Live document.
**Source:** unsolicited external review of the corpus (`SYNTHESIS.md`, `AGENTS.md`,
`B-algorithms-sota.md`, `captures-needed.md`, `focus.rs`, `stack.rs`) delivered 2026-08.
**Reviewer's own caveat, quoted:** *"everything below is ARGUED, none of it measured, and per
rule 12 it should be treated as hypotheses to falsify, not conclusions."*

That caveat is taken literally. This document is the triage; the disposition column is what the
project actually did, and links to the measurement where one exists.

---

## 1. Disposition

| # | Proposal | Cost to falsify | Disposition |
| --- | --- | --- | --- |
| R1 | Build the priced merge now (regulariser w17 + noise gate + robustness mask) | build | **ACCEPTED → M18 → reassigned to the orchestrator and BUILT (M37).** Facts 84/86/80 already price it and fact 80 guarantees the window won't reopen. Agreed: no open questions sit in front of this build. **Delivered** as `crates/strehl-core/src/merge.rs`: two-pass, 17×17 regularised winner, noise-gated average, `n_eff` and boundary flags as outputs, 21 tests. `FOCUS_NOISE_SD` measured in-crate at `0.015214 ± 0.000075` (facts 310-314). **The robustness mask is NOT in this build** — M28 designed it and it remains unbuilt. Gate threshold unmeasured by choice, question 90 |
| R2 | Posterior over frame-of-best-focus as the merge's central object; confidence = entropy, occlusion = bimodality, "no frame in focus" = boundary mass | design | **SPLIT VERDICT, both halves now MEASURED. Bimodality ACCEPTED → [M21](../research/M21-occlusion-bimodality-measured.md); confidence-as-entropy REFUTED → [M32](../research/M32-posterior-confidence-measured.md).** *Bimodality:* multi-peaked curves are enriched **4.38×** at depth steps on `coffee-bean` (permutation placebo 1.01×; ~2.7× after stratifying out the intensity-gradient confound; 9.5–14.3× in the most textured quintile) — but the effect is undetectable on `109`/`119`, where noise alone flags 60% of pixels, so the detector is deployable only *gated on the calibrated noise floor*. Two constraints follow: bimodality needs a **finer scale** than the merge's focus window (invisible at R=13, present at R=2), binding R14; and M18 must retain sufficient statistics so it lands without a rewrite. *Confidence:* the self-normalised form is **blind and non-monotone** in the evidence (0.6480 → 0.6482 across a 6.1× evidence range; 9% response to a 16× SNR change against the calibrated arm's 22 orders of magnitude), and the **calibrated** form is **degenerate** — the through-focus peak stands at **142–991 σ**, so the posterior is a delta on real data. **The frame choice is not the uncertain part**, and confidence must come from the merged estimate's predicted σ, the acceptance-set width and the sub-frame peak offset instead (question 65). Also corrected: the no-information null is **0.874 at n=53, not 1.0**, and it drifts with `n` — the review's proposal as written would mis-threshold every short stack. **Third fold-in → [M34](../research/M34-confidence-vector-measured.md): entropy survives as ONE CHANNEL of a vector, never as the scalar the review proposed.** Per pixel the posterior is a delta for only **76.5%** of pixels (p99 = 4.74, max = 39.05), and the informative tail correlates with the true sub-frame deficit at **+0.3349** — so `n_eff` ships. But it cannot ship alone: the three real-valued channels flag near-disjoint pixel sets (union **14.278%** against a **15.0%** disjoint ceiling; every pairwise overlap at **0.53–1.35× chance**, against a label-shuffle null that returns chance to four decimals), and predicted σ is **anti**-correlated with the sub-frame deficit (worst-5% lift **0.89×**), so **no monotone scalar summary of them is faithful**. This also qualifies M32's own fact 261: it was measured on binned populations, and a median cannot falsify a claim about a tail |
| R3 | **Elevate multi-frame Wiener deconvolution to the core merge** | cheap | **REFUTED on this rig's data → [M20](../research/M20-deconvolution-ceiling-measured.md).** Mechanism correct, scope wrong. Wins on **15.1%** of pixels; median pixel sits **3.3× past** the crossover; measured benefit is *entirely* noise, detail-fidelity gain ±1.5%. Plan (`B` §7.5, opt-in post-merge) stands unchanged |
| R4 | Metacalibrated alignment edges (per-edge response `R` from planted ±δ, divide by own `R`) | cheap | **QUEUED — highest-value untested item.** The corpus supports it: fact 45's recovery ratios (0.559/0.664 real defocus vs 1.008/0.991 controls) *are* response measurements, and this is per-edge self-measurement, not the scalar transfer fact 52 refuted. Pre-registerable criteria are good as written |
| R5 | Blur-equalised alignment edges (pre-blur each side by the other's defocus increment) | cheap | **QUEUED.** Attacks the cause where the planned `\|c−w\|` weighting attacks the symptom. Composes with R4 |
| R6 | Analysis-by-synthesis alignment against the re-blurred latent (v2) | large | **DEFERRED.** Correct endpoint, needs the latent estimate to exist first |
| R7 | **(mean, max) dual focus response** for fact 73's monotone-edge blind spot, running max via van Herk/Gil-Werman | cheap | **ACCEPTED → M17.** Core claim pre-confirmed by the orchestrator: monotone-edge discrimination ratio **1.0000** (mean, blind) vs **0.2592** (max). Noise cost is real (CV 0.0265 vs 0.0065 at blur 3), which is exactly why the *dual* is right and a replacement is not |
| R8 | Orientation anomaly (question 20) explained by row/column FPN interacting with Sobel-x/y | cheap | **ACCEPTED → M16.** If confirmed, `WINDOW_RADIUS = 13` itself may carry a directional bias, which would touch every window number M13 and M15 produced |
| R9 | Per-frame photometric normalisation (gain + offset) in the forward model | small | **MEASURED — see [M24](../research/M24-photometric-drift-measured.md). Premise confirmed, and the requirement is sharper than stated.** Drift is real and widespread: **2.88% / 6.84% / 8.93% / 11.70%** peak-to-peak on four stacks, with the framing confound discharged (central-ROI ratios 1.50/2.05/0.92, r = +0.85…+0.97). The new part: **EXIF does not predict it in either direction** — two stacks vary 7–9% with a single distinct `(exposure, ISO, f-number)`, and on `coffee-bean`, which *does* change exposure mid-capture, the level moves **16% of what EXIF predicts** (1.0443 vs 1.2800). So the gain must be **fitted from the data, never read from metadata**, and since σ²(S) is signal-dependent the noise model has to see it. Dispatched to M18. **`109MSDCF` is the quietest stack at 0.91%** — the corpus this project measured on is the one that hides this |
| R10 | Robustness/outlier mask (Wronski Eq. 5–9 shape) | small | **MEASURED → M28, and the shape needed correcting.** Wronski's form references a *running estimate over the burst*, which is right when frames are nominally identical — a focus stack is the opposite case. Measured fix: **reference the immediate neighbours.** A whole-stack reference carries **10.9× more** residual on a *clean* stack (1.13 → 12.30 over 16× separation) and a 1.82× centre-to-corner radial ramp that vanishes to **0.98×** between neighbours. **This inverts the pipeline ordering: the mask runs BEFORE alignment**, so alignment is protected by it rather than being a prerequisite. Sensitivity is measured, not assumed — a ≈**20 µm subject displacement** is caught 53.8% at FPR 1%, with a shift-zero placebo at **0.0%**; and **tile scale is not a sensitivity knob** (flat within 10% over 4×), so pick it on compute cost. Clean-calibrated thresholds transfer: **1.01% / 8.33% / 17.88%** flagged on clean / bubbles / evolving |
| R11 | Hot pixels + dust from the 242 delivered darks; dust smears under warp | small | **MEASURED, both halves — [M22](../research/M22-hot-pixels-measured.md) (additive) and [M29](../research/M29-static-defects-measured.md) (multiplicative).** *Hot pixels:* a recurrence-derived map (agreement across the 11 ISO groups, not a σ cut) finds **11,393 real defects = 0.0346%** — but in real 1.3 s frames they displace a pixel by **+3.0 DN, i.e. ≤ 0.39σ**, flat across three signal decades. This sensor is clean; build the map, do not let it preempt the merge. **All 242 darks are 1/100 s while real stacks run 1/60 s–2.5 s**, so the map is complete for the wrong exposure (now `captures-needed.md` §6). *Dust:* the review's most attractive sub-claim — that an estimator dilutes a sensor-fixed shadow for free while a selector copies it whole — **is refuted. `D = 0.999` at `n_eff = 3`.** Suppression is bought by the **span** of frames averaged, not their count, and a focus merge averages **adjacent** frames precisely because they agree (M27: `n_eff ≈ 3`; M28: disagreement grows near-linearly with separation). Adjacent-frame warp is sub-pixel, **0.07–0.22 green px**; a 0.2 px shift does not move a shadow 10–40 px across. **So dust needs explicit handling, and it cannot come from subject frames**: the limit is a **32–50% shadow** against real dust of 1–15%, because the floor is *scene texture* and does not fall with frame count (exponent **+0.025** over a 16× sweep). Flats reach a **0.120%** floor at n=20 — **158× better** — which turns `captures-needed.md` §4 into a specification with σ figures attached. The review's warp-smearing claim remains untested and is still the right follow-up |
| R12 | PRNU term `σ²(S) = gS + (RN·g)² + (κS)²` must enter the *model*, not the report | small | **ACCEPTED, blocked on the flat-field capture** (`captures-needed.md` §4) |
| R13 | Colour management (camera RGB → stated colorimetric target, WB ordering vs noise model) | small | **PARTLY MEASURED — see [M26](../research/M26-colour-clipping-measured.md). The review put "WB ordering vs noise model" in this row almost as an aside; it is the sharpest thing in it.** As-shot WB is a per-channel gain of **2.13–2.86× on red**, varying per stack (auto WB), and the calibrated model is valid only in native raw DN — so gating after WB understates σ by a factor tending to **m** in the shadows, hardest exactly where M2 measured the argmax defect. **Ordering rule fixed: gate in native raw DN, colour after the merge.** M26 also found, unprompted by the review, that **clipping defeats discipline 29** (fact 203). The rest of R13 — colorimetric target, rendering intent, ICC/DNG output — is genuine design and remains unscheduled; it is a decision, not a measurement |
| R14 | Decide the fold's sufficient-statistics seam **before** the merge is written | design | **ACCEPTED → M18, made a hard requirement.** The review is right that deciding this late means rewriting the merge once |
| R15 | Fisher-optimal bracket design; suspicion that the optimum is "open up, take more, finer steps" | cheap | **PARTIALLY MEASURED → [M20 §4.4](../research/M20-deconvolution-ceiling-measured.md), and the suspicion is CORRECT and larger than claimed.** f/11 → f/5.6 multiplies best-frame contrast at 4-px detail by **9.6×** and matched-filter SNR by **13.5×** (fixed time) / **6.9×** (fixed light), for 2× the frames. This is pure optics and needs no deconvolution — the review attached it to the reconstruction merge, but it stands alone |
| R16 | Interleaved half-step passes; aperture-paired passes for two-aperture DfD | capture | **HALF ANSWERED at no cost by [M30](../research/M30-hdr-cobracket-measured.md) + M27; half still open.** Fact 240 makes the photon budget indifferent to how it is split, so the half-step proposal is *purely* a focus-coverage question — and M27 already measured coverage as **saturated** on `coffee-bean` at 53 frames (0.01% of pixels resolved by ≤1 sample). **A half-step pass is a repair for a diagnosable condition, not a default**, and M27's criterion is the diagnostic. The aperture-paired half is a different proposal — it changes the *optics* rather than the allocation, which fact 240 says is the only kind of change that can be large — and remains **QUEUED** behind R15 |
| R17 | HDR-focus co-bracketing | medium | **MEASURED → [M30](../research/M30-hdr-cobracket-measured.md). The premise is right, already paid for, and the demand is absent.** The estimator handles per-frame gain (M24, M28), so nothing needs building. But **exposure allocation is exactly neutral at fixed light** in the shot-noise regime (measured median ratio 1.0004–1.0047 across three stacks), this sensor is shot-noise limited **across its entire usable range** (read noise binds below 0.014–0.044% of full scale; **0.0000%** of pixels measured there), and clipping **at the frames a merge gathers** is **0.075%** max — 2.3× lower than the whole-stack figure, because highlights are disproportionately out of focus. **Verdict: support it, do not default it, trigger it per stack** from clipping-at-gathered-frames, which is the same advisory instrument R19 asked for. **The review's direction is backwards for highlights:** rescuing clipped pixels needs **−2 EV**; +2 EV clips more (1.89% newly clipped on `coffee-bean`). Open: whether a specular subject under flash overturns this (question 55) — the corpus has none |
| R18 | Active texture / speckle projection pass (reviewer flags speculative) | capture | **DEFERRED.** Genuinely novel; out of scope for v1 and needs hardware |
| R19 | Close the reshoot loop — emit a concrete recapture recipe, not a bug report | design | **MEASURED → M27.** The signal exists and needs no optics model. A **hole** in the bracket is blindly detectable from a *single* missing frame (curvature excess +0.45 to +1.39 over a null stable at 1.40–1.43), and **uniform** under-coverage — the commoner failure, where no internal control exists — is readable from an **absolute** statistic: frames within 50% of peak height falls 3→2→1 under decimation, with the min-estimation confound closed. The deployable recipe is the fraction of pixels resolved by ≤1 sample: **0.01%** at 53 frames, **37.46%** at 27, 75.76% at 9. Two side results: `coffee-bean`'s 105-frame bracket is **~2–4× denser than needed**, which (DERIVED) roughly pays for the aperture change M20 wants; and the gap disguises itself as a **better** peak, which is the third instance behind new discipline 120 |
| R20 | Depth + uncertainty as a first-class product | design | **QUEUED** behind R2 |
| R21 | Depth-from-breathing: the fitted `log a` ladder + measured `p` is a metric ruler needing no lens DB | cheap | **QUEUED — attractive.** Cross-checkable against fact 54's pixel-measured focus index |
| R22 | Calibrated simulator / digital twin | medium | **ACCEPTED → M25, in flight.** M20 built a 1-D instance and gated it against facts 12/27/28 to 3–4 digits; it then reproduced fact 24 **unprompted** (−49% vs measured −58%/−53%). That is the compounding value the review predicted. The full 2-D twin is now scheduled because **the absence of ground truth has become the binding constraint on the whole programme** — M21 could measure occlusion *enrichment* but not *correctness*, M13 scored windows on proxies, and facts 61-64 exist because bad plants were caught by vigilance rather than by construction. Pre-registered gates: reproduce fact 35's φ-coupling (a mechanism claim the simulator is not told about), facts 19 and 23, and M21's enrichment on a physically-veiled two-layer scene; **plus a negative control that must make those gates fail when a parameter is mis-specified**, since a validation suite that cannot fail is the failure mode here |
| R23 | Physical ground truth (tilted planar targets), SSIMULACRA2/butteraugli scoring | capture | **ACCEPTED → requested** as [`captures-needed.md`](../captures-needed.md) §8. A plane is the only analytic ground-truth depth obtainable without a rail, and it doubles as the project's first **occlusion null** — any halo or bimodality flag raised on a plane is a false positive by construction |
| R24 | Per-stack self-supervision (predict frame k from k±2); learned adaptivity gate trained only on the twin | medium | **DEFERRED but noted as covenant-safe.** Both avoid risk 3's domain gap |
| R25 | **EDOF/microscopy literature was never surveyed** | cheap | **ACCEPTED → M19.** Correctly identified gap in workstream B |
| R26 | Ship order: merge → confidence → alignment metacal → deconvolution → occlusion → capture designer | process | **ACCEPTED with one change.** M20 moves deconvolution *out* of the core sequence. Revised: **merge (M18) → confidence/posterior → alignment metacal+blur-equalisation → occlusion unmixing → capture designer**, with deconvolution as an opt-in stage whenever someone wants it |
| R27 | Stop measuring, start building — the two next builds have no open questions in front of them | process | **ACCEPTED.** This is the most useful process note in the review. Facts 84 (−35%) and 19 (0.534×) were both verified and unbuilt while metrology continued |

---

## 2. What the review got right that the project had not seen

1. **The sufficient-statistics seam (R14).** Nobody had noticed that the single-pass bounded fold
   cannot retain the through-focus neighbourhood the estimation merge needs. Caught before the
   merge was written, which is exactly when it was worth catching.
2. **Occlusion bimodality (R2).** The observation that a veiled background pixel has a *bimodal*
   through-focus curve, that no selector can be right there, and that the focus volume already
   contains the signal — that is the realisable form of question 16's oracle headroom, and it was
   not in the plan.
3. **The metacalibration import (R4).** Reading fact 45's recovery ratios as *response
   measurements* is a genuinely better reading of the project's own data than the project had.
4. **Process (R27).** The observation that the shipped binary is still, by design, the defect the
   project exists to remove — while two priced wins sit unbuilt — landed.

## 3. Where the review is wrong, and why it matters

**R3, the headline.** The review's strongest recommendation — invert the plan and make
deconvolution the core merge — does not survive contact with this rig's data. The full argument is
in [M20](../research/M20-deconvolution-ceiling-measured.md); the short version:

- The estimator algebra is correct (confirmed three ways), but the stated gain `√(Σ|H|²)` is not
  the gain; `√(Σ|H|²)/max|H|` is.
- **Unguarded, the merge is *worse* than the argmax selector it replaces** — by up to 31%, with
  oracle depth and oracle prior. The review listed the `Σ|H|²` fallback as one of three guards; it
  is the load-bearing one.
- The review's justification — *"the prize there isn't noise, it's contrast that no single frame
  contains"* — is **backwards**. On a noise-immune detail metric (gradient correlation with
  truth), the measured detail gain is **±1.5%, i.e. nothing**. The entire measured benefit is
  noise reduction. mean|∇| says otherwise only because ringing and amplified noise inflate it.
- And "at this rig's magnification it is the only path to actual sharpness" is false at Nyquist,
  where MTF is exactly 0.000 (fact 12) and *nothing* is a path. The path there is R15: open up.

**The irony worth recording:** the review's own §4.4-adjacent hunch (R15, "open up and take more,
finer steps") is correct and is **13.5×**, while the merge machinery it was offered in support of
is **1.15× on 15% of pixels**. The review attached the big finding to the small one.

---

## 4. Assignments

| Milestone | Owns | Covers |
| --- | --- | --- |
| M16 | `experiments/m16-orientation-fpn/**` | R8 |
| M17 | `experiments/m17-dual-response/**` | R7 |
| M18 | `crates/**` | R1, R10, R14 |
| M19 | `docs/research/G-edof-deconvolution.md` | R25 |
| M20 | this + `../research/M20-*.md` | R3, R15, R22 (partial) |

---

## 5. Questions for the repo owner

1. **Stop shooting at marked f/11.** It is optically f/33 (fact 28); MTF@Nyquist is 0.000
   (fact 12); critical sampling is at marked **f/6.21**. M20 §4.4 puts the cost at **9.6×** in
   4-px contrast against f/5.6. The trade is 2× the frames for the same depth — *not* more light.
   Written up as [`captures-needed.md`](../captures-needed.md) §0, with the aperture-pair capture
   that would turn it from DERIVED into MEASURED as §7.
2. **Tilted planar target** — now requested as [`captures-needed.md`](../captures-needed.md) §8.
   A textured flat surface at 30–60° to the sensor, shot as a normal bracket, gives analytic
   ground-truth depth *and* the project's first true occlusion null.
3. The flat-field capture ([`captures-needed.md`](../captures-needed.md) §4) is still the blocker
   for R12 (PRNU).
4. **Two questions about how the corpus was lit and metered**, raised by M24 and worth thirty
   seconds each. (a) Was `coffee-bean` shot in an **auto-exposure** mode? Its EXIF changes `4/5 s`
   → `5/8 s` mid-bracket while the measured level barely moves — the signature of the body
   compensating a drifting light. The answer decides whether in-camera bracketing can be trusted to
   hold exposure fixed at all. (b) Was the lighting **continuous/mains-powered or flash**?
   `112MSDCF` varies 6.84% with entirely constant EXIF at **1/60 s**, which is the classic
   mains-flicker beat.
5. **Process question.** M20 refutes the headline of a review that is, on the whole, unusually
   good — and several of its other proposals (R2 occlusion bimodality, R4 metacalibration, R14 the
   fold seam) are strong. Do you want the reviewer's remaining items worked through at the same
   depth, or should the project return to the build sequence in R26 now that the merge is landing?
6. **The subagent fleet stopped producing anything, and I took the work back.** At 05:45 I
   audited the tree: **nine agents had been running between 1 and 3.1 hours and had written zero
   bytes** — not a partial script, not a stub. Every file created overnight was written by me
   directly (M20 through M37). I sent all four long-runners a stand-down instructing them to
   write nothing further, reply with salvage, and stop, and I then built the merge myself.
   **Nothing was lost and nothing was clobbered**, but it means five workstreams you may have
   assumed were in progress are not: **M16** (orientation/FPN, question 20), **M17** (dual
   mean/max focus measure, question 19), **M19** (the EDOF/microscopy survey the review
   correctly identified as a real gap), **M23** (metacalibrated alignment edges) and **M25**
   (the calibrated simulator). Three verifiers — **M20-verify, M31, M36** — are also in this
   state, which matters more, because it means **facts 210-314 remain unverified by anyone but
   their author**. Do you want these re-run, and if so as agents or by me directly? My read is
   that the verification backlog is now the project's largest risk, ahead of any unbuilt feature.

   > **Retested at the end of the night, and it is not transient.** I launched one more agent —
   > `ultra-verifier`, flagship model, a tightly scoped falsification brief on M38's metric
   > correction, with "write a file to disk as your first action" as an explicit instruction so
   > that progress would be visible. **473 seconds, `total_turns: 0`, zero bytes on disk.** That
   > is the tenth consecutive agent to produce nothing, across three agent types and two
   > models, so it is environmental rather than a bad brief. **I am not launching more**, and
   > every measurement in the corpus from M20 onward therefore has the same author as its
   > verifier, which is exactly the arrangement rule 12 exists to forbid. This is the one thing
   > tonight I could not work around.

7. **The merge's one free parameter needs a decision or a measurement, not a default.**
   `Gate::threshold` sets how far below the winner a frame may sit and still be averaged in.
   Fact 212 already supplies the calibration target (`nwide = 3`) and `Estimator::n_eff` reports
   the achieved value, so this is a half-hour measurement once the merge is wired into the CLI —
   but I did not want to pick a number and have it quietly become the shipped default. See
   question 90.

   > **Measured overnight, and the answer is that the question was wrong.** M38 swept the gate
   > on five stacks: at one fixed threshold `n_eff` runs 2.26 to 7.42, and the threshold needed
   > to hit 3 runs 1.1 to 2.9. **A fixed gate is not a calibration.** `n_eff/N` clusters at
   > 0.068–0.079, so the acceptance set is a fixed *fraction* of the bracket. The parameter
   > should be **the target `n_eff`**, which is also the better API — it is the quantity with a
   > measured calibration behind it and the one you can reason about without knowing the gate's
   > units. **No default has been shipped.** See question 95 for how the solve gets specified.

8. **The detail acceptance metric was measuring noise, and it had been for a while.** This is
   the one thing from the night I would most want a second pair of eyes on, because I found it
   by accident. Mean |∇| over a detail ROI falls when a merge blurs *and* when a merge denoises.
   Read uncorrected, the merge showed a **−45% detail collapse** — which is fact 24's number,
   arriving exactly where the theory predicted a problem. It is an artifact: subtract the
   calibrated model's noise contribution and it is **−4.6%**, replicated at −3.6% on a second
   ROI. Roughly **90% of the apparent loss was the merge being charged for doing its job**.

   The uncomfortable part is the other direction. **Fact 24 credits argmax with *raising*
   gradient, and argmax also raises noise 1.253×** (fact 19) — so some of that flattering number
   is the defect this project exists to remove, scored as sharpness. I have corrected the metric
   going forward (fact 322) and left fact 24 standing with the confound noted, because
   re-deriving it needs M2's frames and ROIs, not just its convention. **Worth deciding whether
   fact 24 should be re-measured before it is cited again.**

9. **A number to re-derive: `at_bracket_boundary` disagrees with fact 300 in a way that looks
   like a stack mix-up.** M38 reads 7.60% on `coffee-bean` and 2.02% on `119MSDCF`; fact 300
   (M35) reports 7.38% for `119MSDCF`. The definitions genuinely differ — all-pixel regularised
   winner index against a parabola-fit peak on a reliable subset — so this is **not yet a
   conflict**, and I have not treated it as one. But 7.60 and 7.38 sitting on different stacks
   is the shape of a transposition, and one of the two should be re-derived before either gets
   cited. Logged in question 95 as well.

   > **Resolved — no action needed, and the cause was mine.** M35's harness *was* preserved, so
   > this took reading one line rather than a re-measurement:
   > `experiments/m35-fit-generality/src/01-build.py:70` counts **two frames deep at each end**,
   > on a **decimated** stack, from an **unregularised** argmax. Mine counts **one** frame deep,
   > full stack, regularised winner. Three systematic differences, all in the same direction.
   > The clincher is that both stacks scale by the same factor between the definitions —
   > **3.65× on `119MSDCF`, 3.41× on `112MSDCF`** — which a transposition would not produce.
   > `coffee-bean` really is the worst-covered stack on the stricter definition; the near-match
   > was coincidence. **The doc comment on `at_bracket_boundary` was citing fact 300 as if it
   > were the same quantity, which is what set the trap. Fixed.** Two things worth keeping from
   > this: preserving M35's script is what made a ten-minute resolution possible where M38 §3
   > cost an afternoon for exactly the opposite reason, and *near-matching numbers on adjacent
   > quantities are a smell worth chasing even when they turn out innocent*.
   >
   > **Checked against the source, not the report:** `experiments/m35-fit-generality/out/01-build.json`
   > holds `frac_argmax_at_boundary` = **0.0738** and **0.0208**, so the ratios quoted above
   > (3.65 and 3.41) come from the JSON M35 actually wrote rather than from prose about it.
