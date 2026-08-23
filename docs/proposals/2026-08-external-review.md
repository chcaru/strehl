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
| R1 | Build the priced merge now (regulariser w17 + noise gate + robustness mask) | build | **ACCEPTED → M18.** Facts 84/86/80 already price it and fact 80 guarantees the window won't reopen. Agreed: no open questions sit in front of this build |
| R2 | Posterior over frame-of-best-focus as the merge's central object; confidence = entropy, occlusion = bimodality, "no frame in focus" = boundary mass | design | **ACCEPTED in principle; mechanism now MEASURED — see [M21](../research/M21-occlusion-bimodality-measured.md).** Multi-peaked through-focus curves are enriched **4.38x** at depth steps on `coffee-bean` (permutation placebo 1.01x; ~2.7x after stratifying out the intensity-gradient confound; 9.5–14.3x in the most textured quintile). **But the effect is undetectable on `109`/`119`, where noise alone flags 60% of pixels as multi-peaked** — so the detector is only deployable *gated on the calibrated noise floor*, which is exactly strehl's differentiator. Two new constraints follow: bimodality needs a **finer scale** than the merge's focus window (invisible at R=13, present at R=2), which binds R14; and M18 must retain sufficient statistics so this lands without a rewrite |
| R3 | **Elevate multi-frame Wiener deconvolution to the core merge** | cheap | **REFUTED on this rig's data → [M20](../research/M20-deconvolution-ceiling-measured.md).** Mechanism correct, scope wrong. Wins on **15.1%** of pixels; median pixel sits **3.3× past** the crossover; measured benefit is *entirely* noise, detail-fidelity gain ±1.5%. Plan (`B` §7.5, opt-in post-merge) stands unchanged |
| R4 | Metacalibrated alignment edges (per-edge response `R` from planted ±δ, divide by own `R`) | cheap | **QUEUED — highest-value untested item.** The corpus supports it: fact 45's recovery ratios (0.559/0.664 real defocus vs 1.008/0.991 controls) *are* response measurements, and this is per-edge self-measurement, not the scalar transfer fact 52 refuted. Pre-registerable criteria are good as written |
| R5 | Blur-equalised alignment edges (pre-blur each side by the other's defocus increment) | cheap | **QUEUED.** Attacks the cause where the planned `\|c−w\|` weighting attacks the symptom. Composes with R4 |
| R6 | Analysis-by-synthesis alignment against the re-blurred latent (v2) | large | **DEFERRED.** Correct endpoint, needs the latent estimate to exist first |
| R7 | **(mean, max) dual focus response** for fact 73's monotone-edge blind spot, running max via van Herk/Gil-Werman | cheap | **ACCEPTED → M17.** Core claim pre-confirmed by the orchestrator: monotone-edge discrimination ratio **1.0000** (mean, blind) vs **0.2592** (max). Noise cost is real (CV 0.0265 vs 0.0065 at blur 3), which is exactly why the *dual* is right and a replacement is not |
| R8 | Orientation anomaly (question 20) explained by row/column FPN interacting with Sobel-x/y | cheap | **ACCEPTED → M16.** If confirmed, `WINDOW_RADIUS = 13` itself may carry a directional bias, which would touch every window number M13 and M15 produced |
| R9 | Per-frame photometric normalisation (gain + offset) in the forward model | small | **ACCEPTED, unscheduled.** Fact 52's same-subject pair is a full stop apart; risk 8 names it; nothing plans it |
| R10 | Robustness/outlier mask (Wronski Eq. 5–9 shape) | small | **ACCEPTED → M18 stretch goal.** `foam` moves and `coffee-bubbles` has bubble motion; one twitching antenna currently poisons both reference and average |
| R11 | Hot pixels + dust from the 242 delivered darks; dust smears under warp | small | **ACCEPTED, unscheduled.** The darks are already on disk. Reviewer is right that this is what a "SOTA" claim gets caught on |
| R12 | PRNU term `σ²(S) = gS + (RN·g)² + (κS)²` must enter the *model*, not the report | small | **ACCEPTED, blocked on the flat-field capture** (`captures-needed.md` §4) |
| R13 | Colour management (camera RGB → stated colorimetric target, WB ordering vs noise model) | small | **ACCEPTED, unscheduled.** Risk 8, still no plan |
| R14 | Decide the fold's sufficient-statistics seam **before** the merge is written | design | **ACCEPTED → M18, made a hard requirement.** The review is right that deciding this late means rewriting the merge once |
| R15 | Fisher-optimal bracket design; suspicion that the optimum is "open up, take more, finer steps" | cheap | **PARTIALLY MEASURED → [M20 §4.4](../research/M20-deconvolution-ceiling-measured.md), and the suspicion is CORRECT and larger than claimed.** f/11 → f/5.6 multiplies best-frame contrast at 4-px detail by **9.6×** and matched-filter SNR by **13.5×** (fixed time) / **6.9×** (fixed light), for 2× the frames. This is pure optics and needs no deconvolution — the review attached it to the reconstruction merge, but it stands alone |
| R16 | Interleaved half-step passes; aperture-paired passes for two-aperture DfD | capture | **QUEUED** behind R15, which changes what to recommend |
| R17 | HDR-focus co-bracketing | medium | **QUEUED.** Depends on R9 |
| R18 | Active texture / speckle projection pass (reviewer flags speculative) | capture | **DEFERRED.** Genuinely novel; out of scope for v1 and needs hardware |
| R19 | Close the reshoot loop — emit a concrete recapture recipe, not a bug report | design | **ACCEPTED, unscheduled.** Agreed this is the most differentiating product idea in §1 and has no design |
| R20 | Depth + uncertainty as a first-class product | design | **QUEUED** behind R2 |
| R21 | Depth-from-breathing: the fitted `log a` ladder + measured `p` is a metric ruler needing no lens DB | cheap | **QUEUED — attractive.** Cross-checkable against fact 54's pixel-measured focus index |
| R22 | Calibrated simulator / digital twin | medium | **ACCEPTED in part, already earning.** M20 built a 1-D instance and gated it against facts 12/27/28 to 3–4 digits; it then reproduced fact 24 **unprompted** (−49% vs measured −58%/−53%). That is the compounding value the review predicted. A 2-D version is worth building |
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
4. **Process question.** M20 refutes the headline of a review that is, on the whole, unusually
   good — and several of its other proposals (R2 occlusion bimodality, R4 metacalibration, R14 the
   fold seam) are strong. Do you want the reviewer's remaining items worked through at the same
   depth, or should the project return to the build sequence in R26 now that the merge is landing?
