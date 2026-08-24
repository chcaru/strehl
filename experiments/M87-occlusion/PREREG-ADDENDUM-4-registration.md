# M87 addendum 4 — is the halo a registration artifact?

**Registered before any measurement in this addendum. Committed in its own
commit, ahead of the run, per the milestone's non-negotiables.**

---

## A4.1 Why this exists

The orchestrator sent three corrections. Two are bookkeeping. The third is a
hypothesis it labelled **ARGUED and unmeasured**, and it is the only one that
could overturn this milestone's mechanism:

> The shipped binary does not align. A 299-frame macro bracket has focus
> breathing. With no alignment, subject edges translate and scale between
> frames. A per-pixel argmax over misregistered frames will select, at an edge,
> whichever frame happens to place a high-contrast edge over that pixel — which
> manufactures a bright rim that follows every contour, is worst where a dark
> subject meets a bright background, and is present at gate 0.

**The brief's premise is already out of date and I am recording that before I
measure.** `crates/strehl-cli/src/main.rs` at HEAD says the opposite of "does
not align":

> *It ALIGNS BY DEFAULT (M86c): focus breathing changes magnification frame to
> frame, and unregistered deep brackets drift 232.7 px corner-to-corner on
> bee-3-cpl. Set STREHL_ALIGN=0 to disable.*

So the discriminating experiment does not need to wait for M86 and does not
need me to write an aligner. It is a switch.

**And the question is already answered in the corpus — but only by eye.**
Fact 1236 states *"THE CUTOUT HALO IS OCCLUSION, NOT MISREGISTRATION: IT
SURVIVES CORRECT ALIGNMENT UNCHANGED … present and essentially identical."*
It is attributed to the orchestrator and marked MEASURED, but its wording is
visual-inspection wording, and it carries no number, no null and no interval.
It is the same form as fact 1145, which the corpus itself annotates as
*"ARGUED from visual inspection of one subject and is exactly the kind of claim
this project does not accept unmetricated."*

**M87's first deliverable was a halo metric with a measured null. Fact 1236 is
exactly the claim that metric exists to settle.** This addendum settles it.

## A4.2 The M63 question, answered before measuring rather than after

The orchestrator says the two-layer model is already refuted by M63 and that I
must *"first defeat M63 on its own evidence"* rather than route around it.

**I read M63 at source (`docs/research/M63-bimodality.md`, §0.1 and §9) before
writing this.** Its kill is narrower than the brief states, and my model is not
the thing it killed:

- **What M63 refuted** is the inference *bimodality → second depth*. A pixel at
  offset `x` from a high-contrast edge has gradient response `ΔI·G_σ(x)`, which
  is maximised at `σ = |x|`; with `σ_k ≈ rate·|k − k_focus|` this puts a
  **symmetric pair of secondary through-focus peaks** around the primary **at a
  single depth**. §9.1, DERIVED; §9.2 confirms it, and halving the defocus rate
  multiplies the offset by 1.873 against a predicted 2.00.
- **What M63 did not refute** is the two-layer *photometric composite*. Its own
  side-lobe plant is built "composite first, then blur — the physically correct
  order" (§9.2), and §0.1's *What survives Part I* says in terms: *"Within
  roughly 8 px of the silhouette, the plant does recover the true background
  peak 25–44% of the time … A narrowly scoped near-edge estimator is not
  excluded by this milestone."*

**M87 does not use bimodality and never did.** §0 of my report already declines
to rebuild the refuted detector; my layer segmentation is the elected-frame
depth field, not peak counting. So there is nothing here to route around: M63
killed a *detector*, this milestone measured a *photometric residual*. I record
this position **before** the registration result, so it cannot be read as a
retrofit.

**But M63's side-lobe law is a live rival for my artifact and I say so.** It
predicts a bright response at a fixed offset from any high-contrast edge, at one
depth, with no occlusion. That is a competing explanation for a rim, and A4.5
below is the arm that separates it.

## A4.3 The registered experiment

**One factor changes. Everything else is held byte-identical.**

### R1 — the switch, on real data (primary)

Same stack (`bee-3-cpl`, 299 frames), same binary, same `--gate 0` (pure
selection, one frame per output pixel — so nothing here can be blamed on the
averaging gate, per fact 1145), same ROI, same metric.

| arm | `STREHL_ALIGN` | what it is |
| --- | --- | --- |
| **U** | `0` | registration discarded |
| **A** | `1` (default) | M86c similarity warp applied |

Readout: the M87 halo metric (`ISO`, edge-normal isotonic residual) with a
block-bootstrap 95% CI over contiguous row blocks, exactly as in §3 of the
report.

### R1 registered bars — **written down before the run**

| outcome | criterion | what I must then say |
| --- | --- | --- |
| **R1-A** | `ISO_A ≤ 0.50 × ISO_U`, CIs disjoint | **Registration is the dominant cause.** Say it loudly and immediately: the fix is alignment, not reconstruction. §14 and §5's real-data arms are contaminated and must be retracted. Fact 1236 is **wrong**. |
| **R1-B** | 10–50% reduction, CIs disjoint | Registration is a **contributing** cause. Report the split; any occlusion fix must be re-measured on aligned input. |
| **R1-C** | reduction < 10%, or CIs overlap | **Registration is not the cause.** Fact 1236 is confirmed and, for the first time, metricated. |

### V — validity gate, registered, and R1 is vacuous without it

**A null result only means something if there was something to correct.** I
must therefore report, as part of R1:

1. the **measured** inter-frame drift actually present in the ROI over the
   sweep, and
2. evidence the aligned arm actually moved the pixels (frames placed, warp
   applied, non-identity).

**If the drift within the analysis ROI is < 3 px peak-to-peak, R1 is declared
uninformative rather than negative.** I will not report "alignment changed
nothing" when alignment had nothing to do.

### C-resample — the control this A/B needs

Any warp resamples, resampling blurs, and **the halo is a fine-scale edge
phenomenon**, so a naive A/B confounds *registration* with *interpolation*.
Registered: if arms U and A differ, I must show the difference is not the
resampler by comparing against an arm that is **resampled but not registered**
(identity warp through the same interpolator), or by demonstrating the
comparison is already resample-matched. A halo *reduction* that is really
interpolation blur is a false positive for R1-A and is the specific way this
experiment can lie to me.

## A4.4 R2 — is misregistration *sufficient* to manufacture a halo?

R1 asks whether registration explains **this** halo. R2 asks whether the
orchestrator's mechanism works **at all**, which is a different and still
valuable question — a negative R1 with a positive R2 would mean the mechanism
is real but not operating here.

Synthetic, fully controlled, **no occlusion anywhere**: one textured plane at
**one depth** carrying a high-contrast straight edge, swept through focus, then
**planted inter-frame drift** of the magnitude the corpus measures (~10% scale
across the sweep). Gate-0 selection, then the same ISO metric.

- **R2 positive** — a rim appears with no occlusion present → misregistration
  alone manufactures halos; a real mechanism, and a warning for anyone tuning a
  repair on unaligned data.
- **R2 negative** — no rim at realistic drift → the proposed mechanism does not
  work even in principle here.

**Why this plant *can* express the failure** (the trap this project keeps
hitting, and the one I am most likely to fall into): the plant must contain
(a) a **high-contrast** edge, since the mechanism is driven by edge contrast,
(b) real **texture**, so selection has something to elect between,
(c) genuine **defocus variation** across frames, so argmax is not degenerate,
and (d) drift large enough to move the edge **across whole pixels** at the ROI.
I will verify (d) numerically — the planted per-frame displacement at the ROI in
px — and report it. **A plant that drifts sub-pixel cannot express the effect
and would produce a fake negative.**

## A4.5 R3 — separating M63's side-lobe from a veil

M63's law predicts a secondary response at offset `|x| = σ = rate·|k − k_focus|`
from **any** high-contrast edge at **one** depth. My model predicts a residual
carrying `sign(F − B)` that requires **two** depths.

Registered discriminator: the single-depth plant of R2, run with **zero drift**
and gate-0 selection. It has a high-contrast edge and one depth, so:

- **side-lobe present, ISO large** → a rim needs no second depth, and my §14
  mechanism is weakened; M63's law is the better explanation and I must say so.
- **ISO at the metric's null** → a single depth does not produce this artifact,
  and two layers remain necessary.

## A4.6 Placebo, registered

The same alignment switch applied to `ROI_FLAT` (no occluding edge, already the
report's placebo region, ISO 0.01269). Alignment must not manufacture or remove
a halo where there is no edge. If ISO changes materially there, the metric is
responding to registration *per se* and R1 is confounded.

## A4.7 What would make me wrong

- **R1-A.** If the halo drops by half or more under alignment, my §14 real-data
  discussion is measuring a geometry bug and I retract it, loudly, in the
  VERDICT block and not in a footnote.
- **R3 side-lobe positive at the null-drift single-depth plant.** Then a rim
  needs no occlusion at all and the two-layer framing is the wrong frame.
- **V fails.** Then I have no result, and I say so rather than banking a
  convenient null.

## A4.8 Scope

Python and the shipped binary as a black box. **No file under `crates/` is
opened for writing.** Report goes in a new §15 of
`docs/research/M87-occlusion.md`; `SYNTHESIS.md`, `AGENTS.md` and
`docs/captures-needed.md` are not mine and are not touched. Fact 1236 belongs to
the orchestrator; I will state what I measure and propose a correction, not edit
its row.
