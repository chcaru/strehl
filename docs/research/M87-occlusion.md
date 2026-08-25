# M87 — The occlusion halo: measured, explained, and not yet correctly fixed

**Milestone:** M87
**Scope:** the *occlusion halo* (rule 15 — never the bare word) in the shipped
merge's output. Metric, mechanism, prototype fix, evidence.
**Nothing under `crates/` was edited.** All work is Python under
`experiments/M87-occlusion/`. No Rust was written.
**Author-verified only.** Rule 12: this report is not independently verified.
Everything below is a claim by the agent that produced it.

Labels: **MEASURED** (a number I produced from data) / **DERIVED** (follows from
measured numbers plus stated assumptions) / **ARGUED** (reasoning, no number).
Numbers taken from other milestones are namespaced (`M6.`, `M13.`, `M19.`,
`M21.`, `M25.`, `M52.`, `M63.`). Mine are `M87.`. Candidate facts are numbered
`P1…` per rule 28.

Pre-registration: `experiments/M87-occlusion/PREREGISTRATION.md` (committed
`cdb6475`, before any measurement), addendum 1
`PREREG-ADDENDUM-metric-v2.md` (committed `1805708`, before any arm was scored),
addendum 2 `PREREG-ADDENDUM-2-posthoc.md` (post-hoc disclosures, labelled as
such).

---

## 0. VERDICT

> **SHIPPED, AND OFF BY DEFAULT — and by the end of the night that stopped
> being a cautious choice and became the only defensible one. (§16.)** The halo
> correction is real code in the product: `crates/strehl-cli/src/merge_cmd/halo.rs`,
> a third pass reached from `strehl stack` / `strehl merge` by
> `STREHL_FIX_HALO=1`, at `delta = 40` frames and a 40 px yoke. With it off,
> passes one and two are untouched and **the default output is byte-for-byte
> unchanged**. **Is it on by default? NO.** On the full frame it cuts the halo
> metric **72.9%** (ISO 0.06406 → 0.01734, non-overlapping CIs) and **visibly
> destroys the bee's abdomen hair fringe**, replacing it with a milky scalloped
> band worse than the halo it removed (§16.9,
> `34-SHIP-side-by-side-halo.png`). **The metric and the eye disagree and the
> eye is right**: flattening the near-edge profile satisfies my metric whether
> the veil was removed or the neighbourhood was destroyed. On ground truth the
> same setting raises RMSE **+254.6%**, and on a region with **no occlusion at
> all** it raises RMSE **+558.4%** while still "improving" the metric 63.9%. A
> fine-detail control does pass, exactly and non-vacuously: the highest-gradient
> untouched window carries **1.66×** the corrected region's gradient energy and
> differs by **0 DN**. **Do not default this on.**
>
> **Is the halo a misregistration artifact? NO, and the negative is
> quantitative.** **(§15, registered `a66ca28` before measuring.)** The
> orchestrator's hypothesis was given every chance. Its mechanism is **real**:
> on a single-depth, no-occlusion plant, 30 px p-p of planted drift manufactures
> **ISO = 0.0645**, against the real bee leg's 0.0680. Its magnitude is
> **real**: `bee-3-cpl` drifts **63.04 px p-p** (my mask-centroid track) /
> **70.97 px p-p** (the aligner's own warp solve) inside `ROI_LEG`. So it makes
> a sharp prediction — alignment cuts the residual to ~12.6 px p-p, which sits
> in the flat region of the measured `ISO(drift)` ladder, predicting **91.7% of
> the halo should vanish**. **MEASURED: 6.6%** (0.06805 → 0.06356, CIs
> overlapping). **92% predicted, 6.6% observed.** The validity gate passed at
> **21× its bar**, so this is a negative and not an uninformative null.
> `M63.`'s single-depth side lobe is not the cause either: **+0.0045 over a
> truth floor of 0.00799**, ~7%. **No agent needs redirecting; alignment is
> still worth shipping, but it will not fix this.** The brief's premise was also
> out of date — `main.rs` at `HEAD` says the binary **aligns by default**.
>
> **Does the two-layer model explain the occlusion halo?**
> **Partly, and it is the right physics — but it is not the proximate cause.**
> The proximate cause is **selection**. All 299 single frames of `bee-3-cpl`
> score **0.000026 ± 0.0000073** on the halo metric (mean ± SE over frames;
> sd 0.000126, max 0.000861); the merge of those same frames scores
> **0.06804 [0.05981, 0.07982]**. The artifact is **79× the worst single frame**
> (0.0680424 / 0.0008610680 = **79.02**; the ratio is taken against the *worst*
> frame, not the mean), **2597× the frame mean**, and **9299 SE above it**.
> It is manufactured in the merge. The
> two-layer veil is what makes the *selector* go wrong, and it is what makes the
> defect irreducible — see the next line — but nothing in any single exposure
> looks like the rim you see in the output.
>
> **What IS the halo, physically? AN ERASED VEIL, NOT ADDED LIGHT. (§25.7,
> the sharpest statement in this report and the last one found.)** Measured on
> the image the owner actually judged, in linear raw DN: all 299 single frames
> are veiled over the 2–22 px band by a mean **−26.47% ± 3.01%** relative to
> their own far level, the least veiled at **−20.25%**. The merge reads
> **−6.68%** — the least veiled image in the set, **4.51 single-frame sd** above
> the best frame, **74.76% of the veil removed**. A uniformly random per-pixel
> election reads **−25.85%**, inside the single-frame range, so it is not
> mixture, it is *this* election. **Two-layer physics puts a radial darkening
> beside every occluding edge in every observation; the election, a max-like
> operator on brightness in the veiled band, erases three quarters of it; the
> eye reads a flat band abutting a falling gradient as a glow.** This arrived by
> a *registered prediction failing* — I predicted a bright overshoot and there
> is none — and it explains at once why a baseline-difference halo metric reads
> **+0.280%** on that image while the artifact is unmistakable to the eye.
>
> **Is the two-layer model dead? NO — and §13's −28.2% refuted a *propagation*,
> not the model. (§26.2, §74.)** On a depth-spread plant with known truth,
> scored on band RMSE against the unveiled background rather than on any
> suppression number, the two-component fit handed the **true `alpha_k` cube**
> captures **+100.59%** of the available headroom — 1.7837% against a merge at
> 4.5271% and a single-frame noise floor of 1.7999%. **The fit is not the
> limiter.** What is: a **global scalar `k_F` captures −298.83%**, making the
> band 2.8× *worse* than the uncorrected merge, while a **per-pixel `k_F` map
> captures +99.00%** — a **397.83 point** swing, and the whole distance from
> catastrophe to the floor. Once `k_F` is per-pixel, oracle alpha adds
> **+1.59 points** and oracle `c` adds **0.00**. On the flat placebo, where the
> occluder is at one depth, the per-pixel map instead **costs 25.71 points**, so
> it must be gated on measured depth variation rather than applied everywhere.
> The external reviewer's proposal is **live**. Left open and not claimed: the
> plant reaches +99.00% where the real bee reached −28.2%, so a third limiter
> exists that the plant does not contain.
>
> **Is the veil one mechanism or two? TWO, and the owner's argued split is
> confirmed. (§26.4.)** (a) An **election** artifact with two signs — `E(d)`'s
> positive box (+0.14393 at d = 13) and negative shelf (−0.07961 at d = 92) are
> both boundary-registered, and rolling the elected-index field leaves **39.1%**
> of the box and only **7.7%** of the shelf. (b) A **real frame-borne veil** in
> every observation, invisible to `E` by construction: on the ensemble at fixed
> distance, level falls with local occluder coverage at an observable
> **+2.852%** of level, against a rolled-coverage null of 7.5% and a positive
> control recovering **100.6%** of a planted 3%. The shelf is **2.8× the
> frame-borne veil**, so the correction targets the dominant term — but roughly
> **2.9% of veil is unreachable by any selector**, because it is in every frame.
> That residue is precisely what a two-layer reconstruction removes, which is
> the same answer arriving twice.
>
> **Is the owner's "no selector can be correct there" right?**
> **YES, and it is now measured on ground truth rather than argued.** On a
> synthetic two-layer scene with a known answer, the frame in which the
> background is *sharpest* is also the frame in which it is *most veiled*,
> because the occluder is maximally defocused there. Forcing the near-edge band
> to that frame removes 80% of the halo and makes the picture **3.5× more
> wrong** (band RMSE 3.46% → 12.28% of level). There is no frame to select.
>
> **Does bimodality detect it?**
> **Not used, and it should not be.** `M63.` already refuted bimodality as an
> occlusion detector five independent ways (SYNTHESIS 967/968/969), including
> the decisive control that it fires identically at silhouettes on blank card.
> I did not rebuild a refuted detector. The dispatch's framing — "test the
> bimodality claim" — was pointing at a question the project had already closed
> in the negative, and this report replaces it with a detector that does not
> need bimodality at all: **an edge-normal isotonic-residual overshoot**, which
> separates merge from single frames by 79× with no reference to peak counts.
>
> **Does unmixing remove it?**
> **On synthetic data, yes, and correctly: −78.8% halo AND band RMSE 3.46% →
> 1.82% of level, which is the far-field noise floor.** It reconstructs.
> **On the real bee, no: −3.74% with a global depth, −28.2% with a per-pixel
> one, against a registered −50% bar. FAILED.**
>
> **What actually removes it on real data, and at what cost?**
> A **per-pixel mode partition** (the local form of `M19.`'s fact 412 remedy)
> removes **87.9%** on the bee and **84.6%** on the flower with one parameter
> set and no refitting. **Do not ship it as a quality feature.** Judged against
> ground truth on the plant it is the arm that does the most damage: −79.8%
> halo, **+254.6% band RMSE**. The halo metric cannot tell it from the correct
> reconstruction. It is a cosmetic filter.
>
> **False-positive cost.**
> Structurally zero outside the treated set (max |Δ| = **0.0 DN**, verified not
> asserted). Inside it, the treatment is **not depth-selective**: on a planted
> non-occluding edge in the same frame it moves **85.4%** of treated pixels
> versus **82.1%** at the real edge, and on the plant's non-occluding control it
> raises band RMSE **+558.4%**. It cannot tell an occluding edge from any other
> mask edge.
>
> **Does the artifact reverse sign when contrast polarity reverses?**
> **(§14, registered `4e04877` before measuring.)** **On ground truth, yes,
> decisively: −0.0721 for a dark foreground and +0.2784 for a bright one**, same
> geometry, same depths, levels swapped rather than rescaled. It passes a
> zero-free-parameter magnitude test (ratio 0.86–1.27) and a shape test
> (r = 0.51–0.89) in all four arms, and **the flip survives with the
> signal-dependent noise gate replaced by a constant** — so it is not a gate
> artifact. But the plant is *generated* from the two-layer equation, so this is
> a weaker result than it appears; what it genuinely establishes is that
> **selection lands inside the veiled band** rather than escaping to the
> foreground's frame.
> **On real captures the test is INCONCLUSIVE — not failed.** `bee-3-cpl`
> contains no reversed-polarity occlusion with a background large enough
> (~150 px) for the estimator to satisfy its own far-field self-check:
> **0 of 5 sites pass**, and so does 0 of 1 at the cleanest known-mask site,
> after correcting a measured **15.40%-of-mean** photometric drift that by
> itself moved one tail from −0.129 to +0.010. §14.5 specifies the one capture
> that settles it.
>
> **Two things this closes anyway.** The artifact is measured **on native Bayer
> green sites**, upstream of demosaic, white balance, colour matrix, resampling
> and binning — so **none of those is the cause**. §15 closes them a second
> time and independently: a Catmull-Rom gather that destroys ~49% of a frame's
> gradient energy moves the halo metric by **+0.6%**, because the halo lives at
> `d*` = 16 px, far below Nyquist. It is not sharpening overshoot, not ringing,
> not demosaic. And the shipped
> signal-dependent focus normaliser **suppresses the artifact 3.74× at
> bright-foreground boundaries** while barely touching dark ones, so **M90's
> noise-model fix should be expected to make this halo more visible, not less.**
>
> **Bottom line.** The artifact is real, it is made by the selector, the physics
> the owner proposed is the correct physics, the correct fix is reconstruction,
> and **the project does not yet have a working reconstruction for real
> captures.** The best-looking crops in `C:\dev\strehl-out\M87-before-after\`
> are the ones I am telling you not to ship.
>
> **Added in §24, on `flower-bud-alone-cpl`.** The two-layer model survived a
> test that could have killed it: the veil peaks **10.2% below** the far
> background, so it never breaches the convex bound, and my own visual reading
> that it looked *brighter* was wrong. The rim is nevertheless real at
> **+18.97%** against the background beside it, versus a **+0.42%** measured
> bias floor. The "detached white islands" are **not** an election bug —
> 86.3% by count are the veil severed by hair-thin foreground, and **76.6% by
> area is white card seen through genuine holes in the plant and is not a
> defect at all**. The scalloping has **no characteristic lengthscale**
> (`depth(r) ∝ r^0.933`), and the two pre-registered pipeline scales it appeared
> to confirm were both **my own instrument parameters**.

---

**Is the veil a photometric step between elected frames?** For the bright veil,
**NO**, and correcting exposure makes it worse: with the winner field held
bit-for-bit fixed, per-frame level normalisation moves the box from +0.14393 to
**+0.16731 — 16.24% larger** — while a deliberately planted ±10% per-frame ramp
is removed at **89.0%**, so the instrument can see the mechanism and finds none
here. Drift between the frames actually elected is **−0.7424%**, a **19×**
shortfall against the 14.393% box and the wrong sign. **For the dark stand-off
shelf, YES, in part**: photometry alone with the election frozen removes
**32.44%** of it, while a shuffled normaliser that corrects nothing makes it
**55.7% deeper**. This corrects §26.4, which attributed both features to the
election, and scopes §21's "the photometric share is zero" to the box — ISO's
`D_FAR = (48, 96)` baseline window **contains** the shelf at `d = 92`, so §21's
null was measured with an instrument that absorbs the effect into its own
normaliser. §27.

**The photometric step is real, exactly isolated, and supplies a tenth of the
silhouette step.** Differencing two composites that differ *only* in per-frame
gain, with the election frozen bit-for-bit, measures it at **6.34 DN of a 63.50
DN** observed step at the veil peak — **9.98%**, against a registered 25% bar.
Its sign predicts the rendered step at **48.87%**, below chance, while "the
pixel nearer the subject is brighter" predicts it at **65.16%**. So the
orchestrator's mechanism is confirmed as *present* and refuted as *the cause*.
Four controls pass at slope 1.00, after the first attempt's positive control
returned **−1.7375** because a `linspace` plant with ρ = +1 **cancels** this
cube's natural drift at ρ = −0.9289 — a plant must be checked for sign
agreement with the signal already there. §28.

**Is the shortfall a support problem? The prediction holds; the explanation
does not.** Re-scored on the same cached output, the shipped per-pixel unmix
captures −11.01% on the thinnest quartile of boundary points against
−32.80% on the broadest — a **21.78 point** gap at **7.3** null standard
deviations, and scoring all points reproduces the shipped −28.16% to **0.003
points**. So the unmix really does work far worse on thin structures. But
starvation is refuted three ways: the fit regresses across the **frame axis at
each pixel independently**, so there is no spatial support to starve; measured
observations per band pixel are **38.000 thin against 38.000 broad**; and the
recorded arms run the wrong way, since the arm with **more** coverage scored
better. The variant that could have worked — thin structures attenuating
alpha below the admission gate — is **real but non-operative**: alpha does
attenuate **2.1×** (0.1627 against 0.3444), yet the gate still admits **90.51%**
of thin pixels and **97.62%** of the band, so the R² term sets coverage and the
alpha gate rejects almost nothing. Two corrections against myself: §5.1's
global-depth arm is **−3.74%**, a small *improvement*, not the **+3.7%**
*regression* this report stated in eight places, and my own C-T3-COVER was a
two-branch bar that scored a degenerate 100% as PASS — discipline 676, one hour
after being handed it. §29.

## 1. Corrections to the dispatch, loudest first

### 1.1 Two pointers in the brief are wrong

- **MEASURED.** The bimodality milestone is **`docs/research/M63-bimodality.md`**,
  not `M60-*`. `M60-*.md` are the prior-art and robustness-mask reports. Reading
  `M60-*` "in full" as instructed would have given a milestone with nothing to
  say about this question.
- **MEASURED.** **`docs/research/M6-residual-halo-measured.md` is about a
  different halo.** It measures the **plugin halo** — the rectangle expansion an
  alignment warp needs beyond its output tile, 19.42 / 32.39 / 89.23 plane px
  (`M6.`, SYNTHESIS fact 32). M6 line 46: *"a halo is a rectangle expansion"*.
  It is a name collision, which is exactly why rule 15 exists. It is not a prior
  for this milestone.

### 1.2 The most important correction: bimodality was already dead

The dispatch says M60 *"may already tell you how common bimodality is, how to
detect it, and where it fails"* and instructs me to measure a detection and a
false-positive rate for it. `M63.` had already done that and **killed it**:
SYNTHESIS 967 (bimodality is real and abundant, 78.3% of band pixels, AUC 1.000
against controls), 968 (**the inference to two depths is refuted five ways** —
notably it fires at 78.9% on silhouettes against blank card where there is no
background to veil), 969 (*"The two-layer occlusion-unmixing proposal is
DEAD"*). Rebuilding that detector would have burned the night reproducing a
known negative. **I did not build it.** The detector in this report keys on the
shape of the edge-normal profile, not on peak counts.

### 1.3 An independent finding that redirects another agent tonight

**MEASURED.** `bee-3-cpl` drifts **18.09% in level across the sweep** (green
luma over a fixed far-background pixel set; min 3087.2 DN at k=298, max 3704.5
DN at k=103). A per-pixel selector writes one frame's exposure level per pixel,
so that drift is imported into the output as a **level patchwork** across the
whole background. This is a real output defect and it belongs to the
output/colour agent, not to me.

**It is NOT the occlusion halo.** The band-versus-far level step it predicts is
**+77.1 DN** against an observed **−539.8 DN** — wrong sign, 14% of magnitude —
and re-running the merge with each frame's estimate divided by its own `L(k)`
(**selection left bit-identical**, checked) leaves the rim visibly intact
(`out/05-raw.png` vs `out/05-norm.png`). Hypothesis raised and refuted by me,
same night.

### 1.4 Mundane causes eliminated at source, not by inheritance

- **Resampling ringing: eliminated.** `crates/strehl-cli/src/merge_cmd.rs`,
  `write_merged` emits one RGB pixel per CFA 2×2 quad with no interpolation and
  no kernel. There is no resampling kernel in the write path that could
  manufacture a multi-pixel band. (Read at source; no file edited.)
- **Clipping: eliminated.** Max of the owner's `bee3-*.tif` is 53370 / 65535.
- **Missing colour matrix (fact 1144): not the cause.** Every measurement here
  is on a single green plane in linear DN, upstream of any colour transform.
- **Absence of alignment (M86): not the cause, but a live confound.** The rim
  survives in a synthetic plant that has no inter-frame motion at all, so
  motion is not necessary to produce it. It remains a plausible contributor to
  why the *reconstruction* fails on real data (§7.3).

---

## 2. The instrument, and the three that failed first

Rule 39 requires the null with its standard error next to every separation, and
addendum 1 required the instrument to be able to fail. It failed three times.

### 2.1 What the metric is

**ISO — isotonic-residual overshoot** (`src/m87metric2.py::score_iso`). For each
background boundary point of the foreground mask, with outward normal from the
gradient of the Gaussian-smoothed (σ = 4 px) exterior distance transform:

```
s_j(d)  = image(p_j + d·n_j),  d = 0…64            bilinear
q_j(d)  = s_j(d) / median{ s_j(d) : d ∈ [48,64] }  own local asymptote
q~_j    = gaussian_filter1d(q_j, σ = 3)            along d
m_j     = isotonic fit of q~_j    (increasing if q~_j(64) ≥ q~_j(0), else decreasing)
o_j     = max{ q~_j(d) − m_j(d) : d ∈ [3,40] }
ISO     = median_j o_j
```

Uncertainty is a **tile bootstrap** — resampling 64×64 px tiles of profile
origins, not individual profiles — because adjacent profiles share pixels.

**Why this shape** (ARGUED). It is *edge-referenced*, which `M13.` fact 64 makes
mandatory: a per-pixel ROI average is structurally blind to this defect because
the damage lives in a thin band. Its null is a **physical statement, not a
fitted baseline**: a defocused occluding edge in one exposure has a *monotone*
edge-spread profile, so any single frame must score ≈ 0. And it is defined
identically on a merge and on a frame, so the single-frame control is an
**exactly paired** comparison on the same points and the same normals.

**Which direction it can be fooled in** (rule 18). ISO reads *non-monotonicity
of the edge-normal profile*. Anything that puts a bump in that profile scores:
background texture with a scale near the rim width, a second subject part just
outside the edge, or a **reconstruction that flattens the band by discarding
information**. §5 is a measured demonstration of the last one, and it is the
central limitation of this milestone.

### 2.2 The three failures

| version | what it did | how it died |
| --- | --- | --- |
| v1 | radial profile over the whole perimeter, far-field linear baseline | **MEASURED, FAILED bar G1.** `H/H_shift` = 1.71–1.76× on `ROI_LEG` against a required 4×, and **0.78×** on `ROI_BODY`. Cause: the card carries a large-scale illumination gradient, so a perimeter-averaged profile mixes background levels that differ by far more than the rim. The failure direction was written down in the pre-registration §2.1 *before* it happened. |
| v2.0 | per-profile `max` over d, then median | **MEASURED, FAILED bars V2/V3.** `max` over ~29 noisy samples is positively biased; placebos scored +0.024 and +0.027 against a real +0.037. **65–73% of the signal was bias.** |
| v2.1 | mean profile, then max | **MEASURED, FAILED bar V1.** Scored **−0.017** on `ROI_LEG`, wrong sign, `d*` pinned at the window edge. Diagnosed by *looking* at `out/09-overlay.png`: the leg perimeter alternates between **dark hair-fringe** stretches (monotone-rising) and **clean-silhouette** stretches (the rim). Averaging profiles across both buries the rim. Same disease as v1, one level down. |

**Nothing measured with v1, v2.0 or v2.1 appears anywhere else in this report.**

### 2.3 Validation of the instrument on cases where the answer is known

| case | expected | **MEASURED ISO** | verdict |
| --- | --- | --- | --- |
| merge with the artifact, `ROI_LEG` | large | **0.06804** [0.05981, 0.07982], n = 6103 profiles | ✔ |
| the same 299 frames, individually | ≈ 0 | mean **0.000026 ± 0.0000073** (SE), sd 0.000126, **max 0.000861**, 94.3% score exactly 0 | ✔ null |
| placebo C1, mask translated (+512,+512) into empty background | ≈ 0 | **0.01269** [0.00344, 0.03168], n = 1619 | ✘ bar (§2.4) |
| placebo C3, synthetic disc planted in `ROI_FLAT` | ≈ 0 | **0.00622** [0.00100, 0.02582], n = 286 | ✘ bar (§2.4) |
| plant, ground-truth all-in-focus composite | ≈ 0 | **0.00857** | ✘ floor, ✔ separation |
| plant, merged | large | **0.03060** | ✔ 3.6× over truth |
| plant with **no occlusion** (both layers at one depth), merged | small | **0.01367** | ✔ 2.2× below the occluding plant |

The last row is the cleanest validation in the milestone: the same machinery,
the same geometry, the same noise, the only change being whether there are two
depths — and the metric reads 2.2× lower when there is only one.

### 2.4 The placebo bars were MISSED. Disclosed, explained, not tuned away

Registered bar was |O| ≤ 0.005; measured 0.01269 and 0.00622. **Both fail.**

**MEASURED cause:** the merge's own **background patchwork**. Per-pixel election
over a sweep that drifts 18.09% in level (§1.3) writes different frames'
exposure levels into neighbouring background pixels, producing non-monotone
structure *everywhere in the background*, not only at edges. The placebos are
measuring that floor. It is about **one fifth** of the edge amplitude.

Revised bar, stated as a post-hoc revision (addendum 2 D6): **signal ≥ 4 ×
larger placebo**. Measured **5.4×**. A loosened bar is worth only its argument;
the argument is that the floor was measured and explained rather than tuned
away, and that it is common to every arm so it cancels in arm-versus-arm
comparisons.

---

## 3. What the occlusion halo is, measured

### 3.1 It is manufactured by merging

**MEASURED.** Merge 0.06804 versus a 299-frame single-frame null of
0.000026 ± 0.0000073. This was pre-registered as falsifier **W1** with the
opposite outcome flagged as the loud one (*"the halo is scene content — report
immediately"*). W1 fired **for** selection.

### 3.2 It is gate-invariant, now under a metric

**MEASURED.** gate 0: **0.06804** [0.05981, 0.07982]. gate 2: **0.06843**
[0.05924, 0.08120]. Indistinguishable. This confirms fact 1145, which was *"by
inspection at 100%"*, under an instrument with a measured null — the upgrade
that fact's own consequence clause asked for.

### 3.3 The mechanism: a rank seam

**MEASURED**, `ROI_LEG`, gate 0:

| quantity | near band (d ∈ [3,25]) | far field (d ≥ 60) |
| --- | --- | --- |
| percentile rank of the elected value within its own through-focus distribution | **0.675** | **0.429** |
| median \|k_elected − k_F\| | **32** frames | **96** frames |

**DERIVED.** The near band is estimated **max-like** and the far field
**median-like**, and the visible rim is the seam between the two estimators.
`(merge − median_k)/(max_k − median_k)` peaks at **≈ 0.48** at d ≈ 6–13 and
crosses zero at d ≈ 33.

**ARGUED, and it explains the sign.** A near-edge background pixel's focus field
is driven by *foreground-derived* structure: the 27×27 gradient window straddles
the silhouette, and the veil ramp itself carries the foreground's edge into the
background. Those pixels are therefore **yoked** to the foreground's focus
decision and elect k ≈ k_F — which is the frame where the occluder's blur circle
is smallest, hence the **least-veiled** and, the occluder being dark, the
**brightest**. Farther out the yoke releases and selection lands near the
median. Predicted corollary, untested and worth a capture: **a bright subject on
a dark background should produce a *dark* rim.**

### 3.4 How much of it is the window, and how much is the veil

Pre-registered discriminator, committed **before** it was run (`src/12-window-scaling.py`
carries the prediction in its header). If the rim is purely the focus window
straddling the edge, its width `d0` scales with the operator support and ISO
should collapse at tiny support. If it is the veil, ISO should survive.

**MEASURED**, varying (focus radius, regulariser radius):

| support (px) | 5 | 8 | **21 (shipped)** | 41 | 65 |
| --- | --- | --- | --- | --- | --- |
| rim width `d0` (px) | 30 | 30 | **34** | 46 | 64 |
| peak `frac` yoked | 0.155 | 0.242 | **0.483** | 0.575 | 0.615 |
| **ISO** | 0.0616 | 0.0657 | **0.0680** | 0.0524 | 0.0190 |

**Verdict per the pre-registered rule: MIXED.** Yoking through the selector's
window is real and large — `frac` scales 4× with support and `d0` doubles — but
ISO falls only **9%** from support 21 to support 5, so **a substantial residual
survives at a support far too small to straddle the edge.** That residual is the
veil ramp itself, which is the owner's two-layer physics. (Caveat, MEASURED: the
support-65 collapse to 0.0190 is partly an instrument-range artifact — `d0` = 64
there, outside the metric's d ∈ [3,40] residual window.)

Consistent with `M15.` fact 82: at an occluding boundary the window buys
*contrast localisation*, and the regulariser cannot substitute for it.

---

## 4. Where the two-layer model is right, on ground truth

### 4.1 The plant, and why it can express the artifact

Required justification (the dispatch's warning; `M25.` facts 567/568/603 record
a plant that could not express the effect it tested). The plant is the literal
composite `I_k = α_k·(F⊛P_k) + (1−α_k)·(B⊛P_k)` with a dark opaque bar at one
depth (F ≈ 0.08), textured background at another (B̄ = 0.75), `α_k` the matte
blurred by the **foreground's** own defocus, compositing in the order `M25.`
fact 549 measured as first-order (occlude, blur each layer by its own PSF,
composite with the blurred matte). Selection is then run over it with the
shipped focus operator, transcribed from `M52.`. **The rim is not painted in;
it emerges, and it vanishes in the ground-truth composite.**

**The first build of this plant FAILED its capability check and was rejected**:
ground truth scored 0.0774, *above* the merge's 0.0556, i.e. the metric was
reading texture, not the artifact. The rebuild uses high-frequency low-amplitude
texture. It still misses the registered truth floor (0.00857 versus ≤ 0.005) and
passes on separation instead (3.6× over truth, 3.1× over the worst single
frame). Fully disclosed in addendum 2 D7.

### 4.2 The unmixing works, and it works *correctly*

**MEASURED**, plant, background band d ∈ [2,40], RMSE as a fraction of level:

| arm | ISO | ISO vs merge | **band RMSE** | RMSE vs merge | far-field RMSE |
| --- | --- | --- | --- | --- | --- |
| merged (F0) | 0.03060 | — | **0.0346** | — | 0.0180 |
| **F2 two-layer unmixing** | 0.00648 | **−78.8%** | **0.0182** | **−47.4%** | 0.0180 |
| F1-local mode partition, Δ=10 | 0.03391 | +10.8% | 0.0542 | **+56.5%** | 0.0180 |
| F1-local mode partition, Δ=20 | 0.01312 | −57.1% | 0.0827 | **+139.0%** | 0.0180 |
| F1-local mode partition, Δ=40 | 0.00618 | **−79.8%** | **0.1228** | **+254.6%** | 0.0180 |

**This is the load-bearing table in the report.** F2 takes the band error down
to the far-field noise floor (0.0182 versus 0.0180) — it *reconstructs*. F1
removes more of the artifact and makes the band **3.5× more wrong**.

**Why F1 must damage it, and it is the owner's own argument** (DERIVED,
confirmed by the numbers above): the frame in which the background is sharpest
(k = 90 here) is the frame in which the occluder is *most defocused*, so its
blur circle is largest and the background is *most veiled*. Forcing the band to
that frame trades an unveiled-but-blurred sample for a sharp-but-veiled one.
**There is no frame that is both.** The owner's *"no frame anywhere in the stack
shows clean background"* is confirmed, on ground truth, and it is precisely why
a selection-side remedy is cosmetic.

### 4.3 The control that must fail, and does

Same plant, background moved to the **same depth** as the foreground — a
non-occluding edge with ground truth.

| arm | ISO | band RMSE | RMSE vs its own F0 |
| --- | --- | --- | --- |
| F0 | 0.01367 | 0.0181 | — |
| F1-local Δ=40 | 0.00493 (−63.9%) | 0.1190 | **+558.4%** |
| F2 unmixing | 0.00805 | 0.0155 | −14.4% |

**MEASURED.** F1 still "removes 64% of the halo" on a scene that has almost no
halo, and destroys the band doing it. **A fix that improves a region with no
defect is detecting something other than what you think** — which is the exact
test the dispatch asked for, and F1 fails it.

F2's −14.4% on the same control is a mild **placebo violation of its own**: with
`α_k` nearly constant the regression degenerates into an average over frames,
which denoises. Benign, but it is not nothing, and it is reported rather than
rounded away.

### 4.4 The deliberate breakages, and the metric's failure to notice

**MEASURED**, plant, unmixing with four injected errors:

| variant | ground-truth RMSE (rel) | ISO | ISO vs merge |
| --- | --- | --- | --- |
| correct (modelled α) | **0.0171** | 0.00648 | −78.8% |
| oracle α (true matte) | 0.0171 | 0.00648 | −78.8% |
| BROKEN: PSF scale ×2 | 0.0236 | 0.00451 | −85.3% |
| BROKEN: PSF scale ×0.5 | 0.0360 | 0.00707 | −76.9% |
| BROKEN: swapped layer order | **33117** | 0.00676 | −77.9% |
| BROKEN: wrong `k_F` | 0.0933 | 0.03044 | −0.5% |

**Registered bar X4 said the metric must notice. It noticed once in four.**
The swapped-layer variant is wrong by six orders of magnitude and ISO cannot
tell it from the correct answer. The one break it caught, wrong `k_F`, it caught
mostly because coverage collapsed to 0.02% so almost nothing was treated.

**Consequence, and it governs everything downstream:** *a halo metric measures
whether the artifact is gone, not whether the reconstruction is right.* ISO must
never be used as an optimisation objective for a reconstruction, and no
halo-removal arm may be certified on ISO alone. §4.2 is the application of that
rule to the arm that was, on ISO alone, winning.

---

## 5. Where the two-layer model fails: real data

### 5.1 F2 as registered — global depth

**MEASURED**, `bee-3-cpl` `ROI_LEG`: ISO **0.06550** (**−3.74%** — a small
*improvement*; this read "+3.7%, *worse*" until §29.5 and `P110` corrected the sign
against the JSON), median
R² **0.131** over the band, coverage **12.5%** of band pixels at the R² ≥ 0.5
admission gate. Registered bar was −50%. **FAILED.**

**Note against my own earlier reading:** R² is *not* the discriminator. On the
plant, where the same estimator succeeds with RMSE 1.71%, median band R² is
**0.058** — lower than the bee's — and coverage 16.0%, barely above the bee's
12.5%. The fit statistics look the same in the case that works and the case that
does not. What differs is whether the recovered **intercept** is right, and on
real data there is nothing to check it against.

### 5.2 F2 with per-pixel depth — a real but insufficient rescue

Post-hoc extension (addendum 2 D9): take `k_F` per pixel from the merge's own
elected-frame map inside the subject, median-filter it, propagate to the
background by nearest subject pixel, bin into 10 depth bins, build `α_k` per bin.

**MEASURED**, bee `ROI_LEG`, `c` = px of occluder blur radius per frame:

| `c` | median band R² | coverage | ISO | vs F0 |
| --- | --- | --- | --- | --- |
| 0.1 | 0.098 | 0.060 | 0.06618 | −2.7% |
| 0.2 | 0.127 | 0.122 | 0.06157 | −9.5% |
| 0.4 | 0.173 | 0.164 | 0.04890 | **−28.1%** |
| 0.8 | 0.200 | 0.198 | 0.04888 | **−28.2%** |

**DERIVED.** Per-pixel depth turns a −3.74% into a −28.2% and lifts explained
variance from 0.131 to 0.200. So *part* of the step-5.1 negative was a
depth-resolution failure, and a global `k_F` is the wrong object for an occluder
that spans depth. But it still misses the −50% bar, and — per §4.4 — an ISO
improvement is not evidence the reconstruction is right. **The honest status of
two-layer unmixing on real captures is: promising, unvalidated, not shippable.**

The grid was to be extended to `c` ∈ {1.6, 3.2}; those settings imply Gaussian
kernels of σ up to 512 px and the run did not complete in the time available.
The measured trend is flat from 0.4 to 0.8, so a large further gain there is
unlikely but is **not measured**.

### 5.3 Why it fails, ranked

1. **ARGUED, partially tested.** Depth resolution — §5.2 recovers about half the
   registered target by fixing exactly this.
2. **ARGUED.** The hair fringe is a **semi-transparent mat**, not a binary matte.
   `α_k` built by blurring a hard Otsu mask cannot represent it. This is visible
   in `out/09-overlay.png` and is the same structure that killed metric v2.1.
3. **ARGUED.** `F(x)` is not constant across k: the occluder is itself textured
   and moves through focus, so `I_k` is not linear in `α_k` with a fixed slope.
4. **ARGUED.** No inter-frame alignment (`M86.`). Every regression here assumes
   pixel `x` is the same scene point in all 299 frames. The plant satisfies that
   exactly; `bee-3-cpl` does not.

---

## 6. The remedy that works cosmetically, and its price

**F1 — mode partition** is the focus-axis analogue of Wang et al. 2015, which
`M19.` fact 412 tells this project to try **before** anything bespoke: forbid
near-edge background pixels from electing frames in which the foreground is in
focus, so they cannot inherit the foreground's decision. No `α`, `F` or `B`.

### 6.1 Global `k_F` does not generalise; local `k_F` does

**MEASURED**, one parameter set, no refitting between scenes:

| scene | subject k spread (p10–p90) | Δ | **global** `k_F` | **per-pixel** `k_F` |
| --- | --- | --- | --- | --- |
| bee `ROI_LEG` (299 fr) | 79 frames | 40 | −63.4% | **−87.9%** |
| bee `ROI_LEG` | | 80 | −90.4% | **−100.0%** |
| flower + fern (299 fr) | **248 frames** | 40 | **−1.2%** | **−84.6%** |
| flower + fern | | 80 | −16.9% | **−95.9%** |

Absolute values: flower F0 **0.08155** [0.06598, 0.09617] → local Δ=40
**0.01255**; bee F0 **0.06804** → local Δ=40 **0.00827** [0.00264, 0.01868].

**DERIVED.** The global form failed on the flower for a measurable reason: its
foreground spans 248 of 299 frames in depth, so a single modal `k_F` = 41
describes only the nearest bud and the forbidden band sits at the wrong end of
the sweep. The same defect, in the same direction, as §5.1. **Any Rust
implementation must carry a per-pixel foreground depth map.**

### 6.2 What it costs

**MEASURED**, bee `ROI_LEG`, per-pixel Δ = 40:

| quantity | value |
| --- | --- |
| treated pixels whose elected frame changed | **82.1%** |
| median focus-field retention among moved pixels | **0.388** (p05 0.148) |
| max \|Δ\| outside the treated set | **0.0 DN** (verified, not asserted) |
| boundary profiles improved by > 0.005 | **72.7%** |
| boundary profiles **made worse** by > 0.005 | **18.1%** |

Flower, Δ = 40: **94.0%** improved, **2.3%** worse, outside-treated max |Δ| =
0.0 DN.

**The focus-retention number is confounded and must not be read as blur**
(rule 18): a near-edge background pixel's field is inflated by the straddling
foreground edge, so removing those frames *should* lower it. The unconfounded
cost is the ground-truth one, §4.2: **+254.6% band RMSE**.

### 6.3 It is not depth-selective — the false-positive result

**MEASURED.** A synthetic disc planted in the bee's own flat background, treated
identically:

| | real occluding edge | planted non-occluding disc |
| --- | --- | --- |
| treated pixels moved (Δ=40) | 82.1% | **85.4%** |
| median focus retention | 0.388 | **0.356** |

**The treatment cannot distinguish them.** Combined with §4.3's +558% RMSE on
the plant's non-occluding control, the conclusion is unambiguous: **F1 suppresses
the foreground's focus band at every mask edge, whether or not there is a second
depth behind it.** Named risks it will damage:

- **Non-occluding mask edges** — a subject boundary against a surface at the
  same depth. Measured above.
- **Translucent structures.** Bee wings are semi-transparent and sit inside the
  test ROI. There `α` is not a matte at all, both layers are genuinely present
  in every frame, and forbidding the foreground's focus band forbids the wing's
  own focus band. Not separately measured — **an open risk**.
- **Thin structures.** Hairs and claws are narrower than the 40 px yoke, so the
  band on one side overlaps the band on the other and the entire neighbourhood
  is forbidden its own focus frames. Visible as softening in
  `10-BEE-AFTER-F1-local-d80.png`. Not separately measured.

---

## 7. The flower-bud A/B, and why it is weak

**MEASURED, step 0.** The pair is **not** a controlled experiment: different
framing, different pose, frame-0 green means **3093** vs **2087** DN, and
photometric drift of **+26%** and **+44%** across the two sweeps. The fern is
also **lateral**, not behind the bud. No pixel-wise comparison between the two is
licensed and none was made.

What is licensed is a comparison of a dimensionless, self-referencing metric on
each stack's own geometry:

| stack | frames | **ISO (merge)** | single frames, max |
| --- | --- | --- | --- |
| `flower-bud-alone-cpl` | 205 | **0.06313** [0.04211, 0.09633] | 0.00083 |
| `flower-bud-with-background-fern-cpl` | 299 | **0.08155** [0.06598, 0.09617] | 0.00000 |

**Ratio 1.29×, confidence intervals overlapping.** Adding the fern changed the
artifact **very little**.

**DERIVED, and it matters.** The "alone" stack still has a card behind the bud,
so this is not a no-background control — but it does show that adding a second,
nearer, textured background layer barely moves the artifact. That is the same
shape of result as `M63.`'s decisive control (SYNTHESIS 968a: the bimodality
detector fires at **78.9%** on silhouettes against blank card). The occlusion
halo does **not** require a rich occluded scene; **one background surface at a
different depth from the subject is enough**, because the seam is in the
selector.

Both stacks reproduce the headline: single frames ≈ 0, merge large.

---

## 8. Novelty, re-derived rather than inherited

`M83.`'s audit found **13 of 18** load-bearing survey claims overstated, and the
dispatch instructs me not to inherit "nobody does this" phrasing. Re-derived
against the corpus's own primary-source-verified rows:

- **`M19.` fact 411 (VERIFIED against full texts):** *"First to model the
  occlusion halo" is FALSE and must not be claimed.* Prior art runs to
  **Asada et al. 1995/1998**, whose Realistic Projection Blur model
  **explicitly predicts the non-monotonic brightness transition at an occluding
  edge** — which is exactly what the metric in §2.1 measures — plus Bhasin &
  Chaudhuri 2001, Favaro & Soatto 2003, McGuire et al. 2005, Hasinoff &
  Kutulakos 2007, McCloskey et al. 2011, Wang et al. 2015.
- **`M19.` fact 410 (VERIFIED):** Levin 2009, Nagahara 2008 and Aguet 2008 each
  state the depth-discontinuity case lies **outside their own forward model**.

**Conclusion (ARGUED).** Nothing in this milestone is a new phenomenon or a new
model. The isotonic-residual metric is an operationalisation of a 1995
prediction. The defensible claim is narrow and I state it in that form: *this is
a measurement of the occlusion halo in this project's own merge, with a null,
placebos and a ground-truth control.* Do not write "first" anywhere.

---

## 9. Candidate facts (rule 28 — `P` ids, never absolute SYNTHESIS numbers)

Rule 44: checked by content against `docs/research/SYNTHESIS.md`. `P2` is a
metric-backed **strengthening of existing fact 1145**, not a new row, and should
be folded into it rather than beside it.

| id | claim | consequence | status |
| --- | --- | --- | --- |
| **P1** | **The occlusion halo is manufactured by the merge, not photographed.** All 299 single frames of `bee-3-cpl` score **0.000026 ± 0.0000073** (SE; sd 0.000126, max 0.000861, 94.3% exactly 0) on an edge-normal isotonic-residual metric; their merge scores **0.06804** [0.05981, 0.07982] over 6103 profiles. The headline ratio is **merge ÷ worst single frame = 0.0680424 / 0.0008610680 = 79.02×**; against the frame *mean* it is 2597×, and the merge sits **9299 SE** above that mean | The defect is entirely inside the selector's decision rule. Any remedy is a change to how a frame is chosen or to what is reconstructed, never to capture | M87 (MEASURED) |
| **P2** | **Fact 1145's gate invariance holds under a metric with a measured null**: gate 0 **0.06804** [0.05981, 0.07982] vs gate 2 **0.06843** [0.05924, 0.08120] | Fold into 1145; it discharges that fact's own *"if this holds under a real metric"* clause | M87 (MEASURED) |
| **P3** | **The rim is a rank seam.** The elected value sits at percentile **0.675** of its own through-focus distribution in the near band and **0.429** far away; median \|k−k_F\| is **32** near and **96** far | The band is estimated max-like and the far field median-like. Explains the sign: a dark occluder yields a bright rim, and a bright subject on a dark background should yield a **dark** one — a cheap falsifiable capture | M87 (MEASURED + DERIVED) |
| **P4** | **The rim is part window and part veil, and the split is measured.** Rim width scales with the focus operator support (**30/30/34/46/64 px** at supports 5/8/21/41/65) and the yoked fraction scales **0.155→0.615**, but ISO falls only **9%** from support 21 to support 5 | Shrinking the focus window cannot remove it. A residual survives at a support too small to straddle the edge, and that residual is two-layer veiling | M87 (MEASURED; pre-registered discriminator, prediction committed before the run) |
| **P5** | **A halo metric cannot certify a reconstruction.** On a plant with known ground truth, three of four deliberately broken unmixings still improved ISO by 77–85%, including one wrong by **six orders of magnitude** in RMSE | Never optimise a reconstruction against a halo metric, and never certify an occlusion arm on it. Every arm needs a ground-truth control | M87 (MEASURED) — **the most transferable result here** |
| **P6** | **The mode-partition remedy is cosmetic and damaging.** On ground truth it removes **79.8%** of the halo while raising band RMSE **3.46% → 12.28% of level (+254.6%)**; on a non-occluding control it removes **63.9%** while raising band RMSE **+558.4%** | Fact 412's remedy works on the artifact and not on the picture. If it ships, it ships labelled cosmetic. **This partially retires fact 412's "try the cheap remedy first" as a *quality* recommendation** — it is a good diagnostic and a bad fix | M87 (MEASURED) |
| **P7** | **Two-layer unmixing is correct where it can be checked.** On the same plant it removes **78.8%** of the halo and takes band RMSE **3.46% → 1.82%**, the far-field noise floor (0.0180) | The owner's model is the right physics and the right target. It is the only arm measured to make the picture more correct | M87 (MEASURED) |
| **P8** | **But it does not yet work on real captures.** `bee-3-cpl` `ROI_LEG`: **−3.74%** with a global depth (median band R² 0.131, coverage 12.5%; this row read **+3.7%**, the wrong sign, until `P110`); **−28.2%** with a per-pixel depth (R² 0.200, coverage 19.8%), against a registered −50% bar | Depth resolution is worth **24.4 points** (`P110` corrected this from ~30) and is necessary; it is not sufficient. Ranked remaining causes: semi-transparent hair fringe, non-constant F(x), no alignment | M87 (MEASURED) |
| **P9** | **Median R² does not discriminate a working unmixing from a failing one.** The plant, where RMSE is 1.71%, has median band R² **0.058** — *lower* than the bee's **0.131**, where the arm fails | Do not gate admission on R². The quantity that matters is the intercept, and on real data nothing checks it. **A model-fit statistic is not a correctness statistic** | M87 (MEASURED) |
| **P10** | **A global foreground focus frame is the wrong object whenever the occluder spans depth.** Mode partition scores **−63.4%** on a subject spanning 79 frames and **−1.2%** on one spanning 248; per-pixel depth takes both to **−87.9%** and **−84.6%** | Any occlusion-aware stage must carry a per-pixel foreground depth map, not a scalar. Applies identically to both arms | M87 (MEASURED, two scenes, no refitting) |
| **P11** | **`bee-3-cpl` drifts 18.09% in level across its sweep** (green luma, fixed far set; 3087.2 DN at k=298, 3704.5 DN at k=103), and a per-pixel selector imports that as a background level patchwork | An output defect for the output/colour milestone. **Not** the occlusion halo: predicted band step **+77.1 DN** vs observed **−539.8 DN**, and normalising by L(k) with selection bit-identical leaves the rim intact | M87 (MEASURED) |
| **P12** | **A per-pixel merge's background is non-monotone everywhere, not only at edges.** Occlusion-halo placebos on regions with no occluding edge read **0.01269** and **0.00622** against an edge value of 0.06804 — about **one fifth** of the edge amplitude, from the level patchwork of P11 | Any edge-referenced metric on this merge has a floor of ~0.01, and a bar below that is unattainable until frame-level photometric normalisation ships | M87 (MEASURED) |
| **P13** | **The occlusion halo does not need a rich occluded scene.** The same subject with and without a background fern scores **0.06313** [0.04211, 0.09633] and **0.08155** [0.06598, 0.09617] — **1.29×, CIs overlapping** | Independently echoes `M63.`'s decisive control (fact 968a) one level up: one background surface at a different depth is enough, because the seam is in the selector. **Also: this A/B pair cannot serve as ground truth** — different framing, pose, and frame-0 level 3093 vs 2087 DN | M87 (MEASURED) |
| **P14** | **The occlusion halo reverses sign with contrast polarity, on ground truth.** Same plant, same geometry, same depths, same noise, the two luminance levels **swapped**: signed error against truth is **−0.0721** (dark foreground) and **+0.2784** (bright foreground), each at its own peak `d`, with mean tails at `d = 90–120` of +1.1e-4 and −6.7e-4 (RMS 0.0017, 0.0051) | The two-layer veil is the correct **mechanism**, not only the correct **description**. A polarity-independent artifact would have been an overshoot from the focus operator's support instead. Confirms P3's predicted sign | M87 (MEASURED, synthetic ground truth) |
| **P15** | **The veiled band starts where selection stops electing the foreground's frame.** Measured `E(d)` is **statistically indistinguishable from zero out to `d ≈ 15 px`** (near-band RMS 0.0022 and 0.0035 = 7.0% and 2.8% of the respective peaks), then excurses with the sign of `F − B` over `d = 16–35` and `d = 20–56` — **19/19 and 36/36 consecutive samples share the peak's sign** — then falls back under threshold | Near-edge pixels are *unveiled but blurred*; the error lives further out, where the background wins the election and is veiled. **An occlusion stage must treat an annulus, not a rim** — a fix applied at `d < 15` is treating the one place with no photometric error | M87 (MEASURED) |
| **P16** | **The signal-dependent focus normaliser suppresses the artifact asymmetrically by polarity.** Replacing `green_luma_sigma` with a scene-constant divisor, all else identical, changes signed error from **+0.00853 → +0.03194** for a bright foreground (**3.74×**) but only **−0.00508 → −0.00423** for a dark one (0.83×) | **Cross-milestone, actionable now:** fact 1064's over-confident noise model (−12.8% at S = 8000) is currently *masking* the occlusion halo at bright-foreground boundaries. **M90's fix should be expected to make this artifact more visible there, not less** | M87 (MEASURED on the plant; transfer ARGUED — the operator is the shipped one) |
| **P17** | **A luminance-segmented boundary census cannot measure contrast polarity.** Otsu-segmenting the subject then counting boundary tiles gives *"foreground brighter in **0.0%**"*; a depth-segmented census on identical data gives **71.7%** (307/428) | The 0.0% is a restatement of the segmentation, not a fact about the scene. **Any polarity, occlusion or layer-order census must be segmented on depth**, never on brightness | M87 (MEASURED) — a methods trap, cheap to repeat |
| **P18** | **`bee-3-cpl` cannot answer the polarity question, and the reason is geometric.** Its reversed-polarity occlusions are pale hairs over small dark structures whose far layers are tens of px across; the estimator needs `E(d) → 0` at large `d` to certify itself, and **0 of 5 sites** pass that gate (tails −1.10 to +0.09 of level against a 0.02 bar) | The falsifier needs a **purpose-built capture**: a bright subject on a dark background with a large, clean, textured background area. One stack settles it. Specified in §14.5 | M87 (MEASURED) |
| **P19** | **The sweep drifts 15.40% peak-to-peak *of the sweep mean* on a bare-card anchor patch** (min 4025.3, max 4697.2 DN over 299 frames; the same span is 16.69% if referenced to the minimum), and correcting a reference frame for it moves a real site's far-field residual from **−0.129 to +0.010 of level** | Independent corroboration of P11 on a different region with a different estimator. **Any measurement that differences the merge against a single frame must drift-correct first**, or it will read a photometric offset as structure | M87 (MEASURED) |

---

## 10. Rust integration recipe

**Nothing here was implemented. No file under `crates/` was opened for writing.**
This is a specification for a later milestone, ordered by what the evidence
supports.

### 10.1 Ship first: the metric, as a diagnostic

The one artefact here that is validated end to end (null, placebos, a
known-answer case, and a case where it correctly reads *low*).

- New subcommand or `--report` output on `strehl merge`, operating on the merged
  green plane plus the foreground mask.
- Port `boundary_normals`, `sample_profiles`, `valid_profiles`, `iso_overshoot`
  from `experiments/M87-occlusion/src/m87metric2.py`. The only non-trivial piece
  is PAVA isotonic regression — 20 lines, `O(n)`, no dependency.
- Constants as measured: normal from ∇ of the Gaussian-smoothed (σ = 4 px)
  exterior EDT; `d ∈ [0,64]`; asymptote = median over `d ∈ [48,64]`; smoothing
  σ = 3 along d; residual max over `d ∈ [3,40]`; report the **median** over
  profiles with a **64×64 tile bootstrap** CI.
- Foreground mask: Otsu on the merged green plane. **Disclosed deviation** — the
  pre-registered two-mode rule is defective on this corpus because the
  background is itself bimodal (it put 46% of a background-only ROI inside the
  mask).
- **Acceptance test:** on `bee-3-cpl` at gate 0 it must read 0.068 ± 0.010, and
  on any single frame of the same stack ≤ 0.001.

### 10.2 Do **not** ship the mode partition as a quality feature

It is the arm with the best crops and the worst ground truth (§4.2, §4.3, §6.3).
If it ships at all it must be an explicitly cosmetic, off-by-default flag with
the +254% band-RMSE number in its help text. Its parameters, if wanted:
per-pixel `k_F` from the elected-frame map inside the mask, `size = 15` median
filter, propagated by nearest-foreground EDT indices; treat background pixels
within a 40 px EDT band; forbid `|k − k_F(x)| < Δ`, Δ = 40 of 299 frames.

### 10.3 The real target: two-layer unmixing with a per-pixel depth

Ordered by measured contribution.

1. **Per-pixel foreground depth is mandatory** (P10). Take `k_F` from the merge's
   own argmax field inside the mask, median-filter, propagate outward by
   `distance_transform_edt(return_indices=True)` equivalent. Worth ~24 points of
   halo reduction on its own.
2. **Model `α_k(x) = blur(matte, c·|k − k_F(x)|)`** and solve, per pixel, the
   two-parameter least squares `I_k = a₀ + b·α_k` over k. `a₀` is the unveiled
   background. Six running sums per pixel over the frame loop; no extra frame
   storage; fits the existing streaming merge. `c` ≈ 0.4–0.8 binned px per
   frame on `bee-3-cpl` — **must be fitted per stack, not baked** (`M6.`
   fact 32's lesson: a stack-dependent quantity answered once is wrong).
3. **Do not gate admission on R²** (P9). Gate on `α` dynamic range
   (`max α ≥ 0.05` and `max α − min α ≥ 0.05`) and on the estimate lying within
   the far-field level distribution.
4. **Blocking prerequisites, both other milestones' work.** (a) Inter-frame
   alignment (`M86.`) — every regression assumes a fixed scene point per pixel.
   (b) Frame-level photometric normalisation (P11) — an 18% level drift is a
   nuisance regressor the model does not carry.
5. **Acceptance is ground truth, never the halo metric** (P5). The gate for
   shipping is band RMSE against a synthetic two-layer scene, plus the
   non-occluding control of §4.3 showing **no** improvement.
6. **Treat an annulus, not a rim** (P15). Measured `E(d)` is indistinguishable
   from zero out to `d ≈ 15 px` on the plant: those pixels elect the
   foreground's own frame and are unveiled. Applying the model there costs
   accuracy and buys nothing. The inner radius should be derived per site from
   where the elected frame stops tracking `k_F`, not from a fixed EDT
   threshold.
7. **Expect the artifact to grow when M90 lands** (P16). The shipped
   signal-dependent normaliser suppresses the signed error **3.74×** at
   bright-foreground boundaries; correcting fact 1064's over-confidence removes
   part of that accidental suppression. Any acceptance threshold calibrated
   against today's merge will be too loose afterwards. **Re-baseline after
   M90, do not port the number.**
8. **Segment layers on depth, never on brightness** (P17). The census that
   feeds any occlusion stage must derive near/far from the elected-frame field.
   Luminance segmentation gave 0.0% where depth segmentation gave 71.7% on
   identical data.

### 10.4 Cheapest partial win, not measured here

**ARGUED.** P3 says the rim is a seam between a max-like and a median-like
estimator. A merge that estimated the background at a *consistent rank* removes
the seam by construction — measured here as arm F3, ISO exactly **0.00000**, but
it replaces the band with a per-pixel median and destroys background detail, so
it is only a bound. The interesting untested variant is rank-consistency with
the rank chosen from the *far field's own* distribution rather than the median.

---

## 11. Rule discharge

| rule | how discharged |
| --- | --- |
| 8 (a command was run) | every number here comes from a committed script in `src/`, each writing a JSON in `data/` |
| 9 (flat-ROI control) | `ROI_FLAT` placebo C1/C3, §2.3–2.4; placebo crops bit-identical |
| 11 (placebo + null) | placebos §2.4; the 299-frame single-frame null with SE, §2.3 |
| 12 (author never verifies own work) | **NOT discharged — this report is author-verified only** and needs an independent claimant |
| 13 (can the plant express the failure) | §4.1; the **first plant failed and was rejected**, addendum 2 D7 |
| 15 ("halo" is overloaded) | "occlusion halo" throughout; the `M6.` plugin-halo collision called out in §1.1 |
| 18 (say which direction the metric can be fooled) | §2.1, and §4.4 is a measured demonstration of it |
| 20 (write down the input before running the gate) | pre-registration and both addenda; `src/12` carries its prediction in a commit that precedes its run |
| 28 (`P` ids, check by content) | §9 |
| 31 (fold from a committed revision) | scripts and report committed together; base `d3fd535` |
| 32 (`rawpy` buffer view) | `m87lib.read_planes` copies inside the `with` |
| 35/36 (a test with no power to fail) | §4.3 and §4.4 are controls built to fail, and both did |
| 38 (cite by symbol and content) | `merge_cmd.rs::write_merged`, `m87metric2.py::score_iso` |
| 39 (null with its SE) | §0 and §2.3 |
| 42 (`git commit -- <paths>`, never `git add` bare) | explicit paths only; audited with `git show --name-only` |
| 44 (fold the delta) | P2 marked as a strengthening of fact 1145, not a new row |

---

## 12. Limitations, and what would change the verdict

1. **One capture, one ROI, for the mechanism.** P3 and P4 are measured on
   `bee-3-cpl` `ROI_LEG` only. The generalisation evidence (P10, P13) is two
   scenes, which is two, not many.
2. **The plant under-weights sharpness.** Its background texture is deliberately
   low-amplitude, so "recovering the unveiled background" and "recovering the
   unveiled *and sharp* background" are not well separated by its RMSE. A plant
   with stronger texture would separate them — and would need a different way to
   keep the truth-side metric floor low (§4.1's design tension).
3. **No alignment anywhere.** `M86.` measured that the shipped merge aligns
   nothing. Every real-data regression here inherits that.
4. **Translucency is unmeasured.** Bee wings sit in the test ROI and are the
   obvious hard case; I named the risk and did not quantify it.
5. **X3 not run** — the non-occluding-edge control on `flat-on-ruler-cpl` was
   skipped to avoid colliding with the concurrent metrology milestone. The
   planted-disc and plant controls replace it and are weaker (addendum 2 D9).
6. **What would falsify the verdict.** (a) An unmixing that reaches −50% on real
   data *and* holds its band RMSE on the plant would move F2 from "promising" to
   "ship". (b) A mode partition variant that leaves band RMSE flat on the plant
   would rescue F1. (c) A capture of a **bright** subject on a **dark**
   background showing a *bright* rim would refute P3's mechanism outright — that
   is the cheapest falsifier available and it needs one stack. **§14.5 now
   specifies that capture precisely**, after §14 established that no existing
   stack can supply it.
7. **The polarity confirmation is on a plant generated from the model it
   tests** (§14.3). It cannot refute the two-layer model. The real-data arm that
   could is inconclusive for a geometric reason, not a physical one.

---

## 13. Reproduction

```
cd projects/strehl/experiments/M87-occlusion
$env:PYTHONIOENCODING='utf-8'
python src\10-iso-metric.py       # metric, null, placebos, gate invariance
python src\11-mechanism.py        # rank seam
python src\12-window-scaling.py   # window vs veil discriminator
python src\13-unmix.py            # F2, global depth
python src\16-plant.py            # plant, capability check, breakages
python src\17-perpixel-depth.py   # F2, per-pixel depth
python src\18-flower-ab.py        # the A/B, metric-only
python src\20-local-partition.py  # F1 global vs per-pixel, two scenes
python src\21-cost.py             # cost, false positives, crops
python src\22-plant-truth.py      # ground-truth judgement + failing control
```

The polarity falsifier (§14), registered in `PREREG-ADDENDUM-3-polarity.md`:

```
python src\24-polarity-plant.py   # N1/N2/N3 on ground truth, both normalisers
python src\26-depth-polarity.py   # polarity-blind, depth-segmented boundary census
python src\29-real-polarity-v3.py # the validated estimator; plant + real sites
python src\30-drift-and-control.py# 15.40% drift, per-pixel correction, placebo
python src\31-known-mask.py       # known-mask positive control; "not measurable"
python src\32-polarity-figures.py # 12-POLARITY-*.png, 13-POLARITY-curves.png
```

`src/23`, `src/25`, `src/27` and `src/28` are **committed but discarded** —
their faults are documented in their own docstrings and in `A3.8` of the
addendum. `src/25` in particular reports a **tautological 0.0%** that `src/26`
overturns to 71.7% on identical data; it is kept as the worked example.

`src/04` caches two ~1 GB `.npy` cubes under `cache/`; steps 11–21 memmap them.
Owner-facing crops and a `README.txt` explaining them are in
`C:\dev\strehl-out\M87-before-after\`. The read-only corpora were opened
read-only throughout: **MEASURED**, `Get-ChildItem -Force -Recurse` over
`D:\personal\macro`, `C:\dev\macro` and `D:\macro-dark-frames` finds **0**
entries with a write time later than this milestone's first committed file
(`PREREGISTRATION.md`, 2026-08-24 00:11:03).

---

## 14. The polarity falsifier

Registered in `PREREG-ADDENDUM-3-polarity.md`, committed **`4e04877`, before any
polarity measurement existed**. Post-hoc disclosures are in that file's §A3.8,
which is labelled post-hoc and is not part of the registration.

### 14.1 What was asked, and how it was sharpened

The orchestrator proposed that the two-layer model makes a **signed** prediction:
the artifact should carry `sign(F − B)` and **reverse** when contrast polarity
reverses. Offered explicitly as a hypothesis, and treated as one.

A sign test alone is weak — a coin passes it half the time — so the registration
added two stronger tests that could fail with the sign still right:

- **N2 (magnitude):** `|E|` within 2× of a **zero-free-parameter** forward model
  `median_j[ α_k̂(d)·(F̄ − B_j(d)) ]` built from the plant's *known* `α`.
- **N3 (shape):** Pearson `r ≥ 0.5` between measured `E(d)` and that forward model.

It also registered a **fourth outcome the hypothesis did not contain**: `E ≈ 0`
in the veiled band, which would make the halo a *resolution* seam rather than a
*photometric* veil. That outcome was available and did not occur.

### 14.2 On ground truth: N1, N2 and N3 all pass, in all four arms

Levels **swapped, not rescaled**, so both scenes hold the same two luminance
levels and near-identical global signal statistics.

| focus normaliser | arm | measured `E` | forward `E` | ratio \|E\|/\|E_fwd\| | Pearson `r` | N1 | N2 | N3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| signal-dependent (shipped) | dark FG / bright BG | **−0.00508** [−0.00654, −0.00389] | −0.00419 | 1.211 | +0.787 | PASS | PASS | PASS |
| signal-dependent (shipped) | bright FG / dark BG | **+0.00853** [+0.00753, +0.01072] | +0.00988 | 0.863 | +0.509 | PASS | PASS | PASS |
| constant sigma (control C-sig) | dark FG / bright BG | **−0.00423** [−0.00564, −0.00339] | −0.00333 | 1.269 | +0.742 | PASS | PASS | PASS |
| constant sigma (control C-sig) | bright FG / dark BG | **+0.03194** [+0.03133, +0.03608] | +0.03215 | 0.993 | +0.892 | PASS | PASS | PASS |

All **MEASURED**, 287 profiles per arm, 95% CI by block bootstrap over
contiguous 32-row blocks (adjacent profiles share pixels).

**The flip survives the constant-sigma control**, so it is not an artifact of
the signal-dependent noise gate — the alternative the orchestrator correctly
flagged, and the one fact 1064 would predict.

A second, sharper measurement on the same scenes with the final estimator
(step 29), reading the whole curve rather than a band:

| arm | truth peak | estimator peak | at `d` | mean tail (d = 90–120) | tail RMS |
| --- | --- | --- | --- | --- | --- |
| dark FG / bright BG | **−0.07212** | −0.07166 | 17 px | +0.00022 | 0.0017 |
| bright FG / dark BG | **+0.27841** | +0.27890 | 33 px | −0.00012 | 0.0051 |

The truth-free estimator reproduces ground-truth signed error to within
**0.6%** and **0.2%**. The validity gate reads the **mean** tail, because that
is the quantity the two-layer model constrains to zero; the RMS is quoted so
the mean is not mistaken for a precision. See `13-POLARITY-curves.png` and
`12-POLARITY-side-by-side.png`.

### 14.3 Why this is weaker evidence than it looks — and what it does establish

**ARGUED, and it is the honest reading.** The plant is *generated* as
`α·F + (1−α)·B`. A residual carrying `sign(F − B)` is therefore close to a
restatement of how it was built. **The plant cannot refute the two-layer
model, because it is the two-layer model.** This is the same trap the project
hit at facts 567/568/603 and the one the dispatch warned about, arriving from a
new direction: not a plant that cannot express the effect, but a plant that
cannot *fail* to.

What it genuinely establishes is the non-obvious half:

- **MEASURED.** `E(d)` is **statistically indistinguishable from zero out to
  `d ≈ 15 px`** — near-band (d = 2–15) RMS **0.0022** and **0.0035**, which is
  **7.0%** and **2.8%** of the respective peaks — then excurses, then falls back
  under threshold. The excursion is **19/19** and **36/36** consecutive samples
  carrying the peak's sign, over `d = 16–35` and `d = 20–56` respectively.
  Selection **lands in the veiled band** rather than escaping to `k_F`, where
  α = 0 and the error would vanish. That was the registered fourth outcome and
  it did not happen.
- **Correction to my own first draft of this section.** I initially wrote that
  `E(d)` is *exactly* 0.000 in the near band. It is not; it is at the noise
  level. The corrected statement is above and the sign-run statistic replaces
  the overstatement with something checkable.
- **DERIVED.** So the near-edge pixels are *unveiled but blurred*, and the
  photometric error lives in an **annulus** further out. A fix applied at the
  rim is treating the one place with no photometric error. This is P15 and it
  changes where any occlusion stage must act.

### 14.4 On real data: INCONCLUSIVE, and the reason is geometric

**This is the load-bearing negative of this section.**

Three constructions of a real-data estimator failed, for three distinct
diagnosed reasons (all mine; §A3.8.2). The final construction is validated to
sub-percent on ground truth and carries a **physically required self-check**:
the two-layer model says `E(d) → 0` far from the boundary, so a site whose
curve does not return is contaminated and cannot be certified.

| site set | n | pass the tail gate (\|mean E(90–120)\| < 0.02) |
| --- | --- | --- |
| plant, both polarities | 2 | **2/2** (tails 2.2e-4, 1.2e-4) |
| `bee-3-cpl`, depth-selected sites, **no drift correction** | 5 | **0/5** (tails −1.10, −0.61, −0.20, −0.045, +0.087) |
| `bee-3-cpl`, same sites, **drift-corrected**, automatic masks | 4 | **2/4** (+0.010, −0.019 pass; −0.212, −0.272 fail) |
| `bee-3-cpl` `ROI_LEG`, **known Otsu leg mask**, drift-corrected | 1 | **0/1** (tail −0.096) |

**MEASURED. The 2/4 row is the one that must not be read as a success**, and it
is the reason the known-mask row exists. Both passing sites fail on inspection:

- `ROI_LEG` passed at +0.010 with an **automatic** near/far split that measured
  contrast **1.06** and `k_near = 59` — i.e. it called a dark leg on a bright
  card "reversed". Re-run with the **known** leg mask the same site measures
  contrast **0.27**, `k_near = 147` (correct), and its tail is **−0.096**:
  INVALID. The pass was an artifact of a wrong mask.
- The other passing site measured contrast **0.43** once given enough
  background to work with — it is a **normal**-polarity boundary, not a
  reversed one, so it cannot serve the test either way.

**MEASURED.** Two candidate causes of the tail failures were tested, and the
first is now largely excluded:

- **Photometric drift is real and was a major contributor.** **15.40%
  peak-to-peak of the sweep mean** (min 4025.3, max 4697.2 DN; 16.69% if
  referenced to the minimum instead) on a bare-card anchor patch outside every
  analysis box. Correcting a reference frame per pixel by
  `s[argbest]/s[k_near]` moved one site's tail from **−0.12903 to +0.01025**.
  (P19.)
- **It is not sufficient.** With the *correct* leg mask, `ROI_LEG` still fails
  at **−0.096** after correction. What remains is unattributed: candidates are
  the card's large-scale illumination gradient (diagnosed in §2 as the cause of
  metric v1's failure, not itself quantified in DN), residual selection
  inflation, and the absence of alignment.

**MEASURED.** And the reversed-polarity arm cannot be run at all on this
capture. Genuine reversed-polarity occlusions do exist — pale hair over dark
leg or eye, 307/428 depth-boundary tiles with the near layer brighter — but
their far layers are **tens of pixels across**. Widening the box to obtain a
far field swallows the bright card and the site stops being reversed: all three
top candidates re-measured at contrast **0.43 / 0.83 / 0.87**, i.e. normal.
Narrowing it leaves no room for an anchor: **0 of 2 measurable**.

**MEASURED, and it is a control working.** The short-range tail gate built in
step 31 was **rejected by its own validation**: on the small-scale plant the
*ground truth* tail is **+0.06135** for the bright-foreground arm, because
gate-0 selection takes a per-pixel max over a noisy field and biases a dark
background upward. The merge genuinely differs from truth in the far field
there. The gate refused to certify contaminated data and was not used to
certify anything.

> **VERDICT on the polarity falsifier.**
> **On ground truth the two-layer model passes a signed test it could have
> failed, including a zero-free-parameter magnitude and shape test, and the
> pass survives the noise-gate control. On real captures the test is
> INCONCLUSIVE — not failed, not passed — because `bee-3-cpl` contains no
> reversed-polarity occlusion with enough spatial extent for the estimator to
> certify itself, and because even the cleanest normal-polarity site does not
> satisfy the model's own far-field requirement after a measured **15.40% of
> mean** photometric drift is corrected for.**
>
> **This does not change the report's operative conclusions.** §5 already
> measured that two-layer unmixing fails on real captures (−3.74% / −28.2%
> against a −50% bar), and §6 already measured that the cheap remedy is
> cosmetic. The polarity work strengthens the *mechanism* and leaves the
> *engineering* verdict exactly where it was: **do not build the two-layer
> reconstruction into Rust yet.**

### 14.5 The capture that would settle it, specified

**ARGUED, from measured constraints.** §12 already named "a bright subject on
a dark background" as the cheapest falsifier of P3. The polarity work sharpens
it into a specification, and it is now the single highest-value capture for
this line of work:

1. **A bright subject on a dark background** — reversed polarity, which this
   corpus does not currently contain in usable form.
2. **The background must be large and clean** — at least ~150 px of
   uninterrupted background beyond the silhouette on the green lattice, so
   `E(d)` can be shown to return to zero. This is the constraint `bee-3-cpl`
   fails, and it is the reason the arm could not be run.
3. **The background must be textured**, or it has no focus peak of its own,
   no seam, and no halo — the plant's own design tension, measured in §4.
4. **A clean depth separation**, `|Δk| ≥ 30` frames between subject and
   background.
5. Same session, same lighting as a normal-polarity control if possible.

**Predicted result if the two-layer model is right:** a **dark** annulus
outside the bright subject, peaking at `d` of order the foreground's blur
radius at the background's focus frame, returning to zero beyond it. **If the
annulus is bright instead, the veil is refuted as the dominant cause** and the
artifact is an overshoot from the focus operator's support.

I am not editing `docs/captures-needed.md` (owner's file, rule respected).

### 14.6 Corrections to the hypothesis as offered

- **MEASURED. "`bee-3-cpl` has both [polarities]" is not usable as stated.**
  The two boundaries named — pale thorax hairs against the darker body, and the
  dark eye against pale hairs — are **reflectance edges at a single depth**:
  boundary-local depth separation **−3.0** and **−2.0** frames respectively
  (wing margin −5.0). Those are the *placebo* for this milestone, not a
  polarity test. Reversed-polarity *occlusions* do exist elsewhere in the frame,
  but not with usable geometry (§14.4).
- **Pointer. "discipline 572"** in the dispatch does not say what it was cited
  for. SYNTHESIS discipline 572 is the Jensen-inequality noise-gain defect
  (`1/sqrt(E[n])` vs `E[1/sqrt(n)]`). The *instruction* — treat a hypothesis as
  a hypothesis — stands on its own; only the citation is wrong. Same class as
  the M60/M63 and M6 pointer errors in §1.
- **MEASURED. The concern that M85's render fix invalidates my spatial
  statistics does not apply.** Every surviving number in this report is
  computed from `m87lib.read_planes` — the **native Bayer green sites**,
  black-subtracted — not from a rendered image. No demosaic, no white balance,
  no colour matrix, no resample, no 2×2 bin, no alignment. Only the *discarded*
  metric-v1 work (steps 01–03, 06–07) ever read a rendered TIFF. This also
  **eliminates demosaic, colour matrix, white balance and resampling as causes
  outright**, since the artifact is fully present upstream of all of them —
  four of the alternative explanations the orchestrator listed, closed with
  evidence already in hand.
- **Visual reference rebased.** `out/23-full-2-after-prev.png` (local, gitignored
  with every other PNG) is a downsample of M85's `full-2-after.png`. The
  qualitative description in the dispatch — a bright scalloped aura following
  the contour, giving a cut-out quality — is consistent with what I measure at
  normal polarity, but it remains an unmeasured visual impression and nothing
  in this report rests on it.

---

## 15. The registration hypothesis: refuted quantitatively

Registered in `experiments/M87-occlusion/PREREG-ADDENDUM-4-registration.md`,
commit `a66ca28`, **before any of the measurements below existed.**

### 15.0 Verdict

> **Is the halo a misregistration artifact? NO — and the negative is
> quantitative, not merely a null.**
>
> The hypothesis was not tested by a single A/B. It was given every chance to
> be true, and it failed a test it could easily have passed:
>
> 1. **The mechanism is real.** On a **single-depth, no-occlusion** plant with a
>    painted step edge, planted drift manufactures a halo indistinguishable in
>    size from the real one: **ISO = 0.0645 at 30 px p-p**, against the real bee
>    leg's **0.0680**. Drift is *sufficient*. The orchestrator's mechanism is
>    not fantasy.
> 2. **The magnitude is real.** `bee-3-cpl` really does drift that much inside
>    `ROI_LEG`: **63.04 px p-p** by my mask-centroid tracking and **70.97 px
>    p-p** by the shipped aligner's own warp solve — two independent
>    instruments agreeing to **12.6%**.
> 3. **So the hypothesis makes a sharp prediction.** The drift ladder (§15.3)
>    measures `ISO(drift)`. Alignment cuts in-ROI drift from ~71 px p-p to a
>    residual of **~12.6 px p-p**, which sits in the ladder's flat region.
>    Pure drift therefore predicts **91.7% of the halo should disappear.**
> 4. **It does not disappear. MEASURED removal: 6.6%**, ISO
>    **0.06805 [0.05928, 0.08059] → 0.06356 [0.05672, 0.07099]**, CIs heavily
>    overlapping. Registered bar **R1-C**.
>
> **92% predicted, 6.6% observed.** The halo is not misregistration.
>
> **The validity gate passed, so this is a negative and not an
> uninformative one.** There was 63 px p-p of drift inside the ROI to correct —
> **21× the registered 3 px bar** — and the aligner did correct it.
>
> **`M63.`'s side lobe is also not the cause.** At **zero** drift the same
> plant reads **ISO = 0.01248** against a truth floor of **0.00799**. The focus
> measure's own side lobe contributes **+0.0045**, about **7%** of the real
> halo. It is present, it is measurable, and it is small.
>
> **Consequence for tonight.** No agent needs redirecting. The occlusion
> reconstruction remains the right target, and §10's recipe stands.
> **Alignment is still worth shipping** — it is 20× less drift and it fixes
> softness — but it will not fix this artifact, and a halo repair tuned after
> alignment is not being tuned against a registration artifact.

### 15.1 The premise I was given was already out of date

**MEASURED, at source.** The dispatch says "the shipped binary does not align
(`crates/strehl-cli/src/main.rs:62` says so in as many words)". At `HEAD` that
file says the opposite, in capitals: it **ALIGNS BY DEFAULT (M86c)**, noting
that unregistered deep brackets drift **232.7 px** corner-to-corner on
`bee-3-cpl`, and that `STREHL_ALIGN=0` disables it. `M86.` landed while this
milestone was running.

This is good news for the experiment, not bad: the discriminating test is a
switch rather than an aligner I would have had to write, and it uses a
**validated** instrument instead of a hand-rolled one.

**Fact 1236 is the other thing to correct.** It already claims "the cutout halo
is occlusion, not misregistration: it survives correct alignment unchanged …
present and essentially identical". It is marked **MEASURED** but it carries no
number, no interval and no null — the same form this corpus flags on fact 1145
as "exactly the kind of claim this project does not accept unmetricated". §15
supplies the number. **I have not edited its row** (rule: SYNTHESIS is the
owner's); the proposed correction is `P20` in §15.7.

### 15.2 R1 — the A/B, and the control that makes it readable

One factor changes: same stack, same binary, same `--gate 0`, same metric.

| arm | registration | ISO | 95% CI | n profiles | `d*` |
|---|---|---|---|---|---|
| **U** | `STREHL_ALIGN=0` | **0.06805** | [0.05928, 0.08059] | 6348 | 16 |
| **Uw** | none, but resampled once | 0.06844 | [0.05898, 0.08078] | 6605 | 16 |
| **A** | `STREHL_ALIGN=1` (M86c) | **0.06356** | [0.05672, 0.07099] | 6197 | 16 |

**MEASURED.** Total change U → A: **−6.6%**. Decomposed by the `C-resample`
control: **resampling alone +0.6%**, **registration alone −7.2%**.

**Why `C-resample` was not optional.** Arm A resamples and arm U does not. The
M86c gather is Catmull-Rom, and `M86.`'s fact P23 measured that **one
Catmull-Rom gather at a half-pixel shift retains only 0.5139 of a frame's
gradient energy** — an interpolator is a lowpass, so *any* warped arm scores
lower on an edge metric for reasons that have nothing to do with registration.
Without this control the −6.6% would have been uninterpretable, and had it come
out at −55% the control would have been the only thing standing between this
project and a false `R1-A`.

It also produces a result worth keeping: **a resample that destroys ~49% of
gradient energy moves the halo metric by 0.6%.** That is not a contradiction —
it is a measurement that **the halo is a coarse feature**, living at `d* = 16`
px, far below Nyquist, where a half-pixel gather does almost nothing. It is
independent confirmation that the halo is not a sharpening or ringing artifact.

The control was verified before use: the identity warp reproduces the input with
**max |error| = 0** exactly, as a Catmull-Rom gather must at integer positions.

**Cross-instrument agreement, unplanned.** Arm U is the *Rust binary's* gate-0
merge, scored on the full frame. §5's baseline is my *Python* reimplementation
of the merge, scored on a 700×1100 crop. They read **0.068050** and
**0.068042**. Agreement to four decimals is luck — the bootstrap CI is ±13% —
but agreement at two significant figures across two independent merge
implementations is not, and it retroactively validates §5's baseline.

### 15.3 The drift ladder — the instrument that actually decided it

`R1` alone cannot settle the question. A 6.6% removal is only evidence against
the drift hypothesis **if** drift-at-the-residual-level would have produced a
much smaller halo. That requires knowing the *shape* of `ISO(drift)`, so I
measured it. **This possibility was registered in advance**: §A4.3 recorded that
if `ISO(drift)` saturates, `R1`'s null would be uninformative and I would have
to say so.

Single-depth plant, painted step edge, no occluder, no second layer, integer
shifts only (so no interpolation touches it).

| drift px p-p | ISO | | drift px p-p | ISO |
|---|---|---|---|---|
| 0 | 0.01248 | | 16 | 0.01332 |
| 1–8 | 0.01248 | | 24 | 0.03592 |
| 12 | 0.01248 | | 30 | 0.06448 |
| | | | 45 | 0.14645 |
| | | | 60 | 0.16133 |
| | | | 90 | 0.04123 |

**MEASURED. `ISO(drift)` has a threshold near 16–24 px p-p, not a linear ramp.**
Below ~12 px p-p the metric does not move at all.

**That flat region is the load-bearing part of the argument, so I checked it
rather than reporting it.** Eight identical printed values is the signature of a
broken instrument, and this project has produced two of those tonight. It is
real:

- The frames genuinely differ — max |Δ| = **613.3 DN** between the 0 and 12 px
  arms.
- The selection genuinely differs — the argmax field differs, and **72.8%** of
  pixels select a *defocused* frame even at zero drift.
- The ISO values are genuinely different, just equal at five decimals:
  **0.012482189** at 0 px and **0.012477560** at 12 px.
- The reason is measurable: the sampled edge-normal profiles differ at only
  **0.05%** of points. Small drift changes *which* frame is elected across most
  of the field, but not inside the narrow band the metric reads.

**Physically:** drift only manufactures a halo once the edge's displacement is
comparable to the defocus blur scale, at which point a defocused frame's edge
can out-gradient the in-focus frame at a neighbouring pixel.

**Two honesty notes.** The ladder is **non-monotone above 60 px p-p** — the
90 px arm falls back to 0.041 with `d*` collapsing to 3 px, because selection
becomes incoherent and the overshoot migrates into the profile's first few
samples. Do not read the ladder as a calibration curve. And the plant
**over-expresses** relative to reality: at the real in-ROI drift it predicts
~0.16 where the real merge reads 0.068, because the plant's edge is a
full-height, straight, maximum-contrast step and a bee's leg is not. The
argument uses only the ladder's *shape*, within-plant; the 92%-vs-6.6%
comparison is a within-real-data comparison of removal fractions.

### 15.4 Closing the loop: what the aligner actually achieved in the ROI

The 92% prediction needs the post-alignment residual **inside `ROI_LEG`**, so I
took it from the aligner's own warp sidecar rather than assuming it.

**A convention bug I caught and fixed.** Read in raw pixel coordinates the
sidecar puts the solve's fixed point at (−242, −142) — outside the frame — and
the worst corner reads **351 px** against the tool's own reported **186.702 px**.
Read in **centred** coordinates the fixed point lands near the plane centre,
which is what a magnification change about the optical axis must look like, and
the worst corner reads **186.584 px** — a miss of **0.118 px**. The script now
*derives* the convention by reproducing the tool's number and asserts on it,
rather than trusting my first guess. Had I not checked against a number the
tool prints itself, §15.4 would have reported in-ROI drift as 157 px.

| quantity | value | instrument |
|---|---|---|
| in-ROI drift, `ROI_LEG` centre | **70.97 px p-p** | warp sidecar |
| in-ROI drift, same region | **63.04 px p-p** | my mask-centroid track |
| worst-corner drift | 186.71 px p-p | warp sidecar |
| held-out corner error after solve | 13.58 px | `strehl align` |
| → scaled to `ROI_LEG` radius (984/2113) | ~~6.32 px (\~12.6 px p-p)~~ **WITHDRAWN** | see §20 |

**Two independent instruments agree on the drift to 12.6%**, which is what
licenses using either.

> **⚠ The residual estimate on the last row, and the 91.7% prediction derived
> from it, are WITHDRAWN. See §20.** Both were built on `E*`, the aligner's
> held-out corner error, and fact 1295 (M97) has since measured that `E*` is
> **structurally blind** to a common multiplicative gain error — which is the
> error actually present. The true post-solve residual is **150.2 plane px**,
> not \~12.6 px. **§15's conclusion survives on an argument that never used
> `E*` at all**, restated in §20.2.

**Where this could still be wrong.** `E*` is a median over the top-span quartile
at the *worst corner*; scaling it by radius assumes the residual is
scale-dominated. If it is translation-dominated the residual is uniform and
larger at the ROI, but even the full 13.58 px p-p sits at the ladder's threshold
and predicts ≥88% removal. The conclusion is not sensitive to this.

### 15.5 R3 — separating `M63.`'s side lobe from everything else

Same plant, **zero** drift, no occlusion. Anything that appears is the focus
measure's own response.

| arm | ISO | 95% CI |
|---|---|---|
| truth (all-in-focus scene, scored identically) | 0.00799 | [0.00776, 0.00826] |
| merge, zero drift | **0.01248** | [0.01199, 0.01291] |
| merge, 30 px p-p drift | 0.06448 | [0.05733, 0.07066] |
| merge, 60 px p-p drift | 0.16133 | [0.15782, 0.17131] |

**MEASURED.** `M63.`'s side lobe is real and it is small: **+0.0045 above the
truth floor**, ~**7%** of the real bee halo. `M63.` §9.1's law — the boxed
gradient response at offset `x` peaks at `σ = |x|`, so a pixel `d` px from an
edge is maximised by a *defocused* frame — is visible here as the **72.8%** of
pixels electing a defocused frame at zero drift. But that misselection lands
mostly outside the band the halo occupies. **It is not the cause either.**

The non-zero truth floor of 0.00799 is the metric's own bias on a noisy step
edge and is why the plant arms are quoted against it rather than against zero.

### 15.6 Placebos, including one of mine that was broken

**I got a placebo wrong and caught it. Disclosed rather than repaired
silently.** My first pass ran the foreground mask with `hist_roi=ROI_FLAT` —
Otsu on a region containing **only background**. Otsu dutifully split background
noise into two classes and manufactured **615 spurious "edges" out of nothing**,
scoring ISO = **0.0139**. That is an instrument error, not a finding. It is the
same failure class as §2.4's registered-rule deviation: a two-class rule applied
where there are not two classes.

Replaced with the **shipped, validated** placebos:

| placebo | arm U | arm A | shipped (§2.3, crop scale) |
|---|---|---|---|
| **C3** disc planted in `ROI_FLAT` | 0.00741 [0.00199, 0.01346] | 0.02181 [0.00822, 0.06544] | 0.00622 |
| **C1** subject mask shifted (+512,+512) | 0.02514 | 0.01834 | 0.01269 |

**C3 passes and reproduces.** Arm U's 0.00741 agrees with the shipped 0.00622
within overlapping CIs, on a different merge implementation and at a different
image scale. Arm A's point estimate is higher but its CI spans an order of
magnitude at n = 631; it is not evidence of anything.

**C1 is invalid at full-frame scale, and I measured why rather than asserting
it.** The shipped C1 shifts a *crop-scale* leg mask into empty background. At
full-frame scale the mask is the whole bee — 2,878,468 px — and a (512, 512)
shift leaves **64.9%** of it still lying on the real subject. Full-frame C1 is
therefore measuring real edges, which is exactly why it reads high. **No
conclusion in §15 rests on it.** The valid placebo at this scale is C3.

### 15.7 Candidate facts

| id | claim | label |
|---|---|---|
| P20 | **The cutout halo is not misregistration, and the negative is quantitative.** Correcting registration on `bee-3-cpl` (`STREHL_ALIGN` 0→1, gate 0) moves the halo metric from 0.06805 [0.05928, 0.08059] to 0.06356 [0.05672, 0.07099], a **6.6% removal** with overlapping CIs, where the drift hypothesis predicts **91.7%**. Metricates fact 1236, which asserts the same conclusion with no number. | MEASURED |
| P21 | **Misregistration is nonetheless a sufficient halo mechanism.** On a single-depth, no-occlusion plant, 30 px p-p of planted drift yields ISO 0.0645 — 95% of the real bee-leg halo — and 60 px p-p yields 0.1613. A halo is not evidence of occlusion. | MEASURED |
| P22 | **`ISO(drift)` has a threshold near 16–24 px p-p, not a linear ramp.** Below 12 px p-p the metric is flat (0.0124822 at 0 px vs 0.0124776 at 12 px) although 72.8% of pixels change their elected frame; the elected-frame changes fall outside the metric's band, differing at 0.05% of sampled profile points. Drift manufactures a halo only once edge displacement is comparable to the defocus blur scale. | MEASURED |
| P23 | **`bee-3-cpl` drifts 63.04 px p-p (mask-centroid track) / 70.97 px p-p (warp sidecar) inside `ROI_LEG`** — two independent instruments agreeing to 12.6%, at a radius of 984 px against 186.71 px p-p at the worst corner. | MEASURED |
| P24 | **A Catmull-Rom gather that destroys ~49% of gradient energy (`M86.` P23) moves the halo metric by +0.6%.** The halo lives at `d*` = 16 px, far below Nyquist. This independently eliminates sharpening overshoot, resampling ringing and demosaic artifacts as causes. | MEASURED |
| P25 | **`M63.`'s single-depth side lobe is present but small**: on a zero-drift, no-occlusion plant it contributes +0.0045 over a truth floor of 0.00799, ~7% of the real halo, while causing 72.8% of pixels to elect a defocused frame. | MEASURED |
| P26 | **A warp sidecar read in the wrong coordinate origin is silently wrong by 2.2×** (in-ROI drift 157 px vs 71 px). `strehl align` prints its own worst-corner drift; reproducing that number to 0.118 px identifies the convention as centred. Any consumer of `warpmap.txt` should assert against it. | MEASURED |

### 15.8 What would make this wrong

- **If the aligner's in-ROI residual is much larger than 12.6 px p-p** — e.g. if
  the solve is locally bad at `ROI_LEG` specifically — the residual could sit
  above the ladder's threshold and the prediction would collapse. Testing this
  needs per-frame residuals the sidecar does not carry. The `20.1%` refusal rate
  `M86.` reports on this stack makes it worth checking before P20 is promoted.
- **If the real halo is a mixture**, drift and occlusion could each contribute
  and alignment would remove only the drift part. The 6.6% removal *is* that
  part, and it bounds drift's contribution at ~7% — consistent with, and
  independent of, the 7% that §15.5 attributes to the side lobe.
- **If the plant's threshold does not transfer**, because a real leg edge is
  thin, curved and lower-contrast, the transfer point is the *threshold
  location*, not the halo size. A real threshold below ~6 px p-p would restore
  the drift explanation. §15.3's over-expression argues the plant is if anything
  too sensitive, which pushes the threshold the other way.

### 15.9 Reproduction

```powershell
$env:PYTHONIOENCODING='utf-8'
cd experiments\M87-occlusion
$env:CARGO_TARGET_DIR='C:\dev\strehl-target-m87'   # never the shared tree

# arms U and A (gate 0, one frame per pixel, default byte-frozen output)
$env:STREHL_ALIGN='0'; strehl.exe stack "D:\personal\macro\bee-3-cpl" --gate 0 --out cache\align\U-unaligned.tif
$env:STREHL_ALIGN='1'; strehl.exe stack "D:\personal\macro\bee-3-cpl" --gate 0 --out cache\align\A-aligned.tif
strehl.exe align "D:\personal\macro\bee-3-cpl" --out cache\align\bee3-warpmap.txt

python src\35-registration.py          # R1 + validity gate V
python src\36-registration-controls.py # C-resample, C1, C3, owner crops
python src\37-plant-drift.py           # R2 sufficiency + R3 side-lobe
python src\38-drift-ladder.py          # ISO(drift), the deciding instrument
python src\39-warpmap-drift.py         # in-ROI drift and residual
```

Owner crops: `20-REGISTRATION-unaligned.png`, `21-REGISTRATION-aligned.png`,
`22-REGISTRATION-side-by-side.png` (content-matched, same display levels), and
`23-PLANT-*`, `24-PLANT-truth-vs-merge.png` for the plant.


## 16. Shipping decision: the halo fix is real code, and it is OFF by default

> **READ 16.9 FIRST.** On the full-frame, aligned, gated render the correction is
> a **visible regression**: it erases the abdomen hairs and replaces them with a
> milky scalloped blob that is more objectionable than the halo it removed. The
> halo metric improves 72.9% on that same image. **The metric and the eye
> disagree, and the eye is right.** Everything below stands, but this is the
> headline: do not turn this on by default, and do not judge it by my metric.

The orchestrator viewed `10-BEE-AFTER-F1-local-d40.png` directly, confirmed the
white rim on the leg edges is gone, and ordered the fix promoted from prototype
to shipped code tonight, with permission to default it off if the evidence says
so. **The evidence says so, far more emphatically than when that order was
given.** This section is the decision, its defence, and the control that was
asked for.

### 16.1 The plain answers

| Question | Answer |
| --- | --- |
| Is the halo correction in the shipped binary? | **Yes** — `crates/strehl-cli/src/merge_cmd/halo.rs`, reached from `strehl stack` / `strehl merge`. |
| Is it ON by default? | **NO.** |
| How do I turn it on? | `$env:STREHL_FIX_HALO='1'` |
| Which `d`? | **`delta = 40` frames**, yoke 40 px. Override with `STREHL_FIX_HALO_DELTA`. |
| Does the default output change? | **No, not by one bit.** Passes one and two are untouched; the correction is a third pass that does not run unless asked for. |

### 16.2 Why it is not the default, in one table

This is the same ground-truth measurement as §6.3, re-read from
`data/22-plant-truth.json` at source before writing this section. **MEASURED.**

| plant scene | halo metric ISO | RMSE against known truth, in the band |
| --- | --- | --- |
| occluding edge, uncorrected | 0.03060 | 0.03462 |
| occluding edge, `local-d40` | 0.00618 (**-79.8%**) | 0.12276 (**+254.6%**) |
| **non-occluding control**, uncorrected | 0.01367 | 0.01807 |
| **non-occluding control**, `local-d40` | 0.00493 (**-63.9%**) | 0.11900 (**+558.4%**) |

Read the bottom two rows. On a region built to contain **no occlusion at all**,
the correction still "improves" the halo metric by 63.9% while multiplying the
error against truth by 6.6x. The original brief named this failure in advance:
*"A fix that improves a region with no defect is detecting something other than
what you think."* That is exactly what this is. It keys on **silhouettes**, not
on **occlusions**, and it cannot tell them apart — at the bee's real occluding
edge it moves 82.1% of treated pixels, and at a *planted, non-occluding* disc in
the bee's own background it moves 85.4%, which is **more**.

So the correction is cosmetic. It removes the thing that makes the picture look
stacked, and it pays for that by making the picture less like the scene. A user
may legitimately want that trade. They should not be given it silently, and a
default is silent.

### 16.3 Picking `d`, and defending it

The full ladder, **MEASURED**, from `data/20-local-partition.json` and
`data/21-cost.json`. `moved` is the fraction of treated pixels whose value
changed; `retention` is the median fraction of the original focus response the
treated pixels keep, so **lower retention is more damage**.

| `delta` | bee halo | flower halo | moved, real edge | moved, non-occluding control | retention | profiles made worse |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | -80.6% | *not measured* | 67.9% | 73.9% | 0.475 | 13.9% |
| **40** | **-87.9%** | **-84.6%** | **82.1%** | **85.4%** | **0.388** | **18.1%** (bee), 2.3% (flower) |
| 80 | -100.0% | -95.9% | 96.0% | 93.3% | 0.269 | 14.5% (bee), 4.7% (flower) |

`delta = 40` is shipped for three reasons, in order of weight:

1. **It is the only value measured on both real stacks.** `d20` was never run on
   the flower. Shipping a default whose evidence is one capture is how this
   project generated several of its sixteen recorded errors.
2. **`d80` costs the most detail.** Retention falls to 0.269, and hairs and claws
   are narrower than the 40 px yoke, so their two flanking bands overlap and the
   whole neighbourhood is forbidden its own focus frames. That is visible as
   softening in `10-BEE-AFTER-F1-local-d80.png`. `d80`'s extra 12 points of halo
   removal are bought with structure.
3. **`d20` under-treats without buying safety.** It still fires on the
   non-occluding control at 73.9%, so it is no more depth-selective — it is just
   weaker.

**Honest caveat:** none of these three is *good*. `d40` is the least-bad point on
a ladder every rung of which raises error against truth.

### 16.4 The fine-detail control the orchestrator asked for

The request was a control on a region of genuine fine detail — eye facets or
hairs — showing the correction does not touch it. **The honest answer is split,
and one half of it is a failure.**

**Interior fine detail: untouched exactly. MEASURED.**
`max_abs_delta_outside_treated = 0.0` DN at `d20`, `d40` and `d80` alike, on both
the bee and the flower (`data/21-cost.json`). Not "small" — **exactly zero**. The
treated set is background pixels within 40 px of the silhouette, so the bee's eye
facets, being interior subject pixels inside the mask, are never candidates. This
is structural rather than empirical, and it is pinned in the shipped code by the
unit test `an_untreated_pixel_is_never_overridden`.

**Silhouette-adjacent fine detail: damaged, and I could not make this pass.**
Hairs on the abdomen margin are *at* the silhouette, so they are inside the yoke
by construction. At `d40` the treated pixels retain a median 0.388 of their
original focus response, and 18.1% of bee boundary profiles are made worse rather
than better. §6.3 predicted this before it was measured and the measurement
agrees with the prediction.

I did not tune the yoke until this control passed. A yoke small enough to spare
the hairs is smaller than the halo, and would not remove the thing being shipped.
**That is the real reason this is not a default**, stated as plainly as I can:
the correction cannot currently distinguish a hair from a halo, because both are
thin bright structure adjacent to a silhouette.

### 16.5 What the code does, and what it deliberately does not do

`merge_cmd/halo.rs` is the §6 `F1 local` prototype ported exactly:

1. Otsu threshold on the merged green luma; mask = darker than `tau`, closed and
   opened with a radius-3 disc, components under 2000 px dropped.
2. Exact Felzenszwalb-Huttenlocher squared EDT with source indices.
3. `k_F` per treated pixel = the 15x15 median-filtered winner index of its
   **nearest foreground pixel** — a per-pixel map, not a global constant.
4. Treated set = background pixels with EDT distance <= 40 px.
5. Re-elect from frames with `|k - k_F| >= 40`, using the same regularised field
   that elected the pass-one winner.

**The per-pixel map is not a refinement, it is the whole algorithm.** A global
`k_F` removes only 1.2% of the flower's halo, because the flower's subject spans
248 of 299 frames p10-p90 and no single frame is "the foreground". Any future
port must carry the per-pixel map.

Three things it deliberately does not do, each a known cost rather than an
oversight:

- **It does not average.** Treated pixels are re-elected, so inside the yoke the
  gate's noise averaging is lost and the band is noisier. Every M87 measurement
  was made at gate 0, where that is equally true of the uncorrected image, so the
  numbers above are like-for-like; against a **gated** merge this is an extra,
  **unmeasured** cost. ARGUED.
- **It assumes the subject is darker than its background.** True of both stacks
  measured and of the case the halo is worst in. On a bright subject against a
  dark background the mask selects the background instead. Not papered over with
  an unmeasured heuristic.
- **It never invents a pixel.** Where every frame falls inside the forbidden
  band, the pixel keeps its uncorrected value and the run prints how many did.

### 16.6 Verification performed

- `cargo test -p strehl-cli --bins halo` — **6 passed, 0 failed.**
- **Negative control, and it failed as designed.** Two defects were planted: the
  EDT's second column sweep was disabled, and the band comparison was moved from
  `>=` to `>`. Result: **3 passed, 3 failed** — exactly the three EDT and band
  tests, with the unrelated three still green. The tests are live instruments,
  not decoration. The file was then restored from a `$env:TEMP` copy, verified
  byte-identical by `Get-FileHash` against the source tree, **touched** so cargo
  could not serve a stale object, and re-run: **6 passed, 0 failed.**
- `edt_matches_brute_force_on_a_scattered_mask` compares the linear-time
  transform against an O(n^2) brute-force nearest-seed search over every pixel,
  and asserts **exact** equality, not a tolerance.

**Where it was verified, and why that is not the shared tree.** The workspace
does not currently compile: `crates/strehl-core/src/color.rs` is mid-edit by M93
and fails with `the trait bound f32: Eq is not satisfied`. That file is forbidden
to me and I did not touch it. Verification therefore ran against
`git archive HEAD` exported to a private directory with my two files overlaid, so
the core it built against is the **committed** core. `merge_cmd.rs` carries no
foreign edits — `git diff --stat HEAD` shows 98 insertions and 10 deletions, all
mine — so the overlay is exact. **The halo code has not yet been compiled against
M93's in-flight `color.rs`, and that check remains outstanding.**

### 16.7 The exact command that renders the before/after

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$EXE = 'C:\dev\strehl-target-m87v\release\strehl.exe'
$OUT = 'C:\dev\strehl-out\M87-before-after'
# skips the align solve; the sidecar validates its own StackIdentity
$env:STREHL_WARPMAP = 'experiments\M87-occlusion\cache\align\bee3-warpmap.txt'

# BEFORE -- the shipped default, unchanged
Remove-Item Env:STREHL_FIX_HALO -ErrorAction SilentlyContinue
& $EXE merge D:\personal\macro\bee-3-cpl --out "$OUT\30-SHIP-BEFORE-default.tif" --srgb --demosaic --gate 2

# AFTER -- the correction on
$env:STREHL_FIX_HALO = '1'
& $EXE merge D:\personal\macro\bee-3-cpl --out "$OUT\31-SHIP-AFTER-fixhalo.tif" --srgb --demosaic --gate 2
```

The only difference between the two lines is the environment variable.

### 16.8 What was cut, and what it would take to finish

Cut tonight, in the interest of shipping something true rather than something
large:

- **No `--fix-halo` flag.** `main.rs` owns the subcommand definition and is
  forbidden. The switch is an environment variable, following the exact
  precedent `align_cmd.rs` set for `STREHL_ALIGN` for the same reason. The
  verbatim flag patch is in §17.
- **Not promoted into `strehl-core`.** It lives in the CLI crate, declared by
  `pub(crate) mod halo;` inside the allowed `merge_cmd.rs`, so **no shared
  registration point was touched** — neither a `pub mod` line in
  `strehl-core/src/lib.rs` nor a subcommand arm in `main.rs`. The promotion patch
  is in §17.
- **No gate-aware substitution.** See §16.5.
- **No `strehl stack` path.** The correction is wired into the merge/estimator
  path, which is what renders the images the owner looks at.

### 16.9 The full-frame result, and why I am telling you not to enable it

> ⚠ **PARTIALLY WITHDRAWN by §23.3 / P59.** The conclusion — *do not enable
> this by default* — **stands**, on the strengthened evidence of registered bar
> V3, which the correction FAILS: it removes fine structure (0.9058) harder than
> it removes the veil (0.9146). But this section's implication that the result
> is **blur-grade destruction** was too harsh and is withdrawn. Measured against
> a Gaussian blur matched to the same halo suppression, the correction retains
> **90.6%** of the fine band where the blur retains **20.5%** — **BMF = 4.43**.
> I had predicted ≤ 1.05 and registered that prediction before measuring. The
> defect is insufficient *selectivity*, not destruction.

Everything in §6 and §16.1-§16.8 was measured on **ROI crops of an unaligned,
gate-0 merge**. The shipped binary renders something different: the **full
frame**, **aligned** (M86c, on by default), and **gate 2**. I rendered both arms
through the shipped binary and looked at the result. It does not survive.

**What the metric says. MEASURED.** On the byte-frozen linear pair, over 5714
valid boundary profiles in `ROI_LEG`:

| arm | halo metric ISO | 95% CI |
| --- | --- | --- |
| `STREHL_FIX_HALO` unset (default) | 0.06406 | [0.05755, 0.07162] |
| `STREHL_FIX_HALO=1` | 0.01734 | [0.01284, 0.02243] |

A **72.9% reduction**, with non-overlapping intervals. By the instrument this
milestone was built around, the correction works on the shipped output.

**What the picture says. MEASURED, by looking.**
`34-SHIP-side-by-side-halo.png` is a 700x1100 crop at 100%, cut automatically at
the location of the strongest correction in the frame. In the corrected half the
bright rim is gone. So is the fringe of pale hairs along the left flank of the
leg: they have been replaced by a smooth, milky, **scalloped** band that follows
the silhouette. It is larger, softer and more conspicuous than the halo it
replaced. **It looks worse.**

**Both statements are true, and that is the finding.** The halo metric measures
the radial brightness excursion of the background profile as it approaches the
silhouette. Smearing the near-edge background into a flat milky band drives that
excursion to nearly zero. The metric cannot tell "the veil was removed" from
"the neighbourhood was destroyed", because both flatten the profile. §6 already
recorded that the correction raises RMSE against ground truth 254.6% while
cutting the metric 79.8%; §16.9 is what that number looks like at 100% on the
owner's own photograph.

**This is a metric-gaming failure, and my metric is the one being gamed.** It is
the exact defect the brief warned about from the other direction: *"without a
metric that provably responds to the halo, nothing downstream is verifiable."*
The metric does provably respond to the halo (§2, §3). It is simply not
**sufficient** — responding to the halo does not make it safe to optimise
against. I did not discover this until I rendered the full frame and looked,
which is an argument for looking earlier rather than an argument about the
algorithm.

**Why the crops looked good and the full frame does not.** Two differences, both
mine, neither controlled for at the time:

1. **Scale.** The prototype ran on a 700x1100 ROI crop where Otsu cleanly
   separates one dark leg from bright background. On the full frame the mask
   takes in the whole subject at 45.31% of pixels, and the yoke around that much
   longer, more convoluted perimeter covers **13.0%** of the image. The Rust and
   Python masks agree — 45.31% against 45.31%, computed by independent implementations — so this
   is not a port defect. The algorithm is doing exactly what it did before, over
   a boundary of a completely different character.
2. **Structure at the boundary.** The leg crops in `09`/`10` cut across a smooth
   chitin edge. The strongest-correction site on the full frame is a hair fringe,
   which is thin bright structure adjacent to a silhouette — precisely the case
   §16.4 predicted the correction cannot distinguish from a halo. The prediction
   was right and I under-weighted it.

**Consequence for the order I was given.** The instruction was to ship this and,
if the evidence supported it, default it on. It does not. The correct product
decision is the one already taken in §16.1 — shipped, off, honestly documented —
and §16.9 converts that from a cautious reading of a plant into a direct
observation of the owner's own image. **A default-on version of this would have
been visible to the owner as damage in the morning.**

**What would have to change before this is worth enabling.** The correction needs
a foreground-boundary term that distinguishes *thin bright structure attached to
the subject* from *background veiled by the subject*. That is a matting problem,
not a focus problem, and it is not tonight's work. The metric needs a companion
that is sensitive to structure destruction — the ground-truth RMSE of §6.3 is
that companion on a plant, and on real data there is no such number yet, which is
the single largest hole M87 leaves behind.

### 16.10 The fine-detail control, on the shipped binary

§16.4 answered this on the prototype. Here it is on the actual shipped output,
which is what was asked for.

The control region was **not chosen by me**. It is the 600x800 window, on a
100 px grid over the whole 7032x4688 frame, with the highest mean gradient among
all windows the correction left **completely** unchanged — so it cannot have been
picked to flatter the result. It landed at `y 1500..2100, x 3500..4300`.

| quantity | value |
| --- | --- |
| max abs difference, before vs after | **0 DN** of 65535 |
| pixels changed | **0.0000%** |
| mean abs gradient in the control | **687.9** |
| mean abs gradient in the corrected halo crop | 415.6 |

The control carries **1.66x more fine detail than the region being corrected**,
so it is not a vacuous region that changed nothing because there was nothing
there. Interior detail is untouched **exactly**, not approximately, because the
treated set is background pixels within 40 px of the silhouette and interior
subject pixels are inside the mask. `35-SHIP-BEFORE-detail.png` and
`36-SHIP-AFTER-detail.png` are byte-identical crops.

**This control passes, and it is narrower than it sounds.** It proves the
correction cannot reach into the middle of the subject. It says nothing about
structure *at* the silhouette, which §16.9 shows is destroyed.

### 16.11 Whole-frame effect of the shipped correction

MEASURED, on the 16-bit sRGB demosaiced pair:

| quantity | value |
| --- | --- |
| pixels changed | 13.666% of 33.0 M |
| max abs difference | 41887 DN = **63.9%** of full scale |
| subject fraction from the Otsu mask | 45.31% (Rust) / 45.31% (Python, independent) |
| treated pixels | 1072910 = 13.018% of the plane grid |
| treated pixels that found an allowed frame | 1072910 of 1072910; none fell back |
| pass-three cost | 26.9 s on 299 frames, one extra decode pass |

**A note on an error I made and caught.** My first reading of this pair reported
`max |delta| = 163 of 65535`, i.e. 0.25%, and I nearly reported the correction as
having almost no effect. PIL silently converts 16-bit RGB TIFFs to 8-bit on read,
so the true figure was 163 of **255**. Re-read with `tifffile` the maximum is
41887 of 65535. **Every number in §16.9-§16.11 is from `tifffile`, not PIL.** Any
future measurement in this corpus that reads a `strehl` TIFF through PIL is
quantised to 8 bits and should be re-checked.

## 17. Verbatim patches for the shared registration points

Both are **optional**; the code ships and runs without either. Neither file was
edited by me.

### 17.1 `crates/strehl-cli/src/main.rs` — a real flag

Add to the `Stack` variant's field list:

```rust
    /// Remove the occlusion halo: the bright rim a selection stacker leaves
    /// where a dark subject meets a bright out-of-focus background.
    ///
    /// COSMETIC, NOT A FIDELITY FIX, and off unless you ask for it. On a
    /// synthetic scene with known truth it removes 79.8% of the halo and
    /// raises RMSE against that truth by 254.6%. It keys on SILHOUETTES,
    /// not occlusions: on a region containing no occlusion at all it still
    /// moves 85.4% of the pixels it treats. It cannot distinguish a hair
    /// from a halo, so thin structure at the subject outline is softened.
    /// Interior detail is untouched exactly -- 0.0 DN, structurally.
    ///
    /// Use it when you want the picture to stop looking stacked. Do not
    /// measure anything on the result. See docs/research/M87-occlusion.md.
    #[arg(long)]
    fix_halo: bool,
```

and in the `Commands::Stack { .. }` arm, before `stack::run(&opts)`:

```rust
    // The module reads the environment, so a flag sets it. One source of
    // truth for the switch, and `STREHL_FIX_HALO` keeps working.
    if fix_halo {
        // SAFETY: single-threaded, before any worker is spawned.
        unsafe { std::env::set_var(merge_cmd::halo::FIX_ENV, "1") };
    }
```

This requires `pub(crate) mod halo;` in `merge_cmd.rs` to become `pub mod halo;`
(one word, in a file I own).

### 17.2 `crates/strehl-core/src/lib.rs` — optional promotion

Only if the algorithm is moved into the core crate. Add, in alphabetical order
between `focus` and `merge`:

```rust
pub mod halo;
```

There is no reason to do this tonight. The correction consumes an `Estimator`
and a winner field and produces an override of the output; it is a rendering
decision, and the CLI crate is where rendering decisions live.

## 18. Candidate facts — delta only

Self-contained, and additional to §9 (`P1`-`P19`) and §15 (`P20`-`P26`). Numbers
namespaced `M87`.

| id | claim | significance | label |
| --- | --- | --- | --- |
| P27 | The halo correction ships in `strehl` as a third pass reached by `STREHL_FIX_HALO=1`, **off by default**, at `delta = 40` frames and a 40 px yoke. With it off, passes one and two are untouched and the default output is byte-for-byte unchanged. | The corpus's frozen numbers cannot move, so the feature carries no regression risk to any prior measurement. | MEASURED |
| P28 | Against a synthetic two-layer scene with known truth, the shipped correction at `delta = 40` cuts the halo metric 79.8% (ISO 0.03060 to 0.00618) and **raises RMSE against truth 254.6%** (0.03462 to 0.12276). | It is a cosmetic filter that makes the image measurably more wrong. This is the whole reason it is not a default. | MEASURED |
| P29 | On a control region built to contain **no occlusion**, the same correction still cuts the halo metric 63.9% and raises RMSE against truth **558.4%** (0.01807 to 0.11900). | The detector keys on silhouettes, not occlusions. It "fixes" regions with no defect, which is the placebo failure the brief warned about. | MEASURED |
| P30 | The correction moves 82.1% of treated pixels at the bee's real occluding edge and **85.4%** at a planted non-occluding disc in the same image's background — i.e. slightly **more** where there is nothing to fix. | Independent confirmation of P29 on real data rather than a plant. Rules out depth-selectivity as an explanation for why it looks better. | MEASURED |
| P31 | Outside the treated set the correction changes **exactly 0.0 DN** at `delta` 20, 40 and 80, on both real stacks. Interior fine detail (eye facets) is inside the foreground mask and is therefore never a candidate. | The fine-detail guard is structural, not statistical, and is pinned by a unit test. It is the one safety claim here that is unconditional. | MEASURED |
| P32 | Silhouette-adjacent fine detail **is** damaged: at `delta = 40` treated pixels retain a median 0.388 of their original focus response and 18.1% of bee boundary profiles are made worse. Hairs are thinner than the 40 px yoke. | The correction cannot distinguish a hair from a halo. Any future attempt to default it on must solve this first. | MEASURED |
| P33 | The `delta` ladder on real data: 20 gives -80.6% halo at 0.475 retention, 40 gives -87.9% (bee) and -84.6% (flower) at 0.388, 80 gives -100.0% and -95.9% at 0.269. Only `delta = 40` was measured on **both** stacks. | Records the evidence behind the shipped default and shows the halo/detail trade is monotone with no free lunch on the ladder. | MEASURED |
| P34 | A global `k_F` removes only 1.2% of the flower's halo against 84.6% for the per-pixel map, because that subject spans 248 of 299 frames p10-p90. | Any port of this algorithm must carry a per-pixel foreground depth map; the scalar simplification silently fails on deep subjects. | MEASURED |
| P35 | Planting two defects in the shipped module (EDT second sweep disabled; band `>=` to `>`) turned exactly 3 of 6 unit tests red, and restoring from a `$env:TEMP` copy plus an mtime touch returned 6 of 6 green. | The tests are demonstrated instruments rather than decoration, per the corpus discipline on negative controls. | MEASURED |
| P36 | The workspace did not compile for most of M87's shipping window: `crates/strehl-core/src/color.rs` failed with `the trait bound f32: Eq is not satisfied` under M93's in-flight edit, so the halo code was first verified against `git archive HEAD` with the two new files overlaid. **M93 has since landed and the check has been repeated in the real tree: `cargo check -p strehl-cli --bins` exits 0 in 8.51 s, and `cargo test -p strehl-cli --bins halo` reports 6 passed, 0 failed.** | The risk this fact was raised to track is **closed**. The shipped module compiles and passes its tests against M93's landed `color.rs`, not only against a frozen export. | MEASURED |
| P37 | On the **full frame** the shipped correction cuts the halo metric 72.9% (ISO 0.06406 to 0.01734, non-overlapping CIs) while **visibly destroying** the abdomen hair fringe, replacing it with a milky scalloped band more objectionable than the halo. | The halo metric is necessary but **not sufficient**: flattening the near-edge profile satisfies it whether the veil was removed or the neighbourhood was destroyed. Anything optimised against this metric alone must be looked at. | MEASURED |
| P38 | The prototype's crops were ROI crops of an **unaligned gate-0** merge; the shipped binary renders the **full frame, aligned, gate 2**. At that scale the Otsu mask takes 45.31% of pixels and the yoke covers 13.018%, against a small isolated leg edge at crop scale. | A result validated on a crop did not transfer to the full frame. Crop-scale validation is not evidence about the product's output. | MEASURED |
| P39 | Fine-detail control on the shipped binary: the highest-gradient 600x800 window that the correction left completely unchanged carries **1.66x more** gradient energy than the corrected region and differs by **0 DN**. | Interior detail is structurally unreachable, so the correction's damage is confined to the silhouette. It is a real but narrow safety guarantee. | MEASURED |
| P40 | PIL silently converts `strehl`'s 16-bit RGB TIFFs to 8-bit on read. The same before/after pair reads `max delta = 163` through PIL and `41887 / 65535` through `tifffile`. | Any measurement in this corpus taken on a `strehl` TIFF via PIL is quantised to 8 bits. Nearly caused M87 to report the correction as having no effect. | MEASURED |
| P41 | **The registration confound was already separated, and the shipped `d` is clean of it.** Alignment is **already in the merge and ON by default** (`merge_cmd.rs:1199-1283`, `main.rs:71`); it is not pending work. Both shipped renders in §16 set `STREHL_WARPMAP` to a fitted sidecar, so BEFORE and AFTER were **both aligned**. | `d = 40` was **not** tuned against a render whose halo might be misregistration. The concern that a halo repair would bake in a compensation for an alignment bug does not apply to this parameter. | MEASURED |
| P42 | **M87's drift audit independently corroborates M97's half-drift finding, from the other end.** Decoding the 299 placed warps gives scale `\|a\| = 0.922414` — which is **fact 1295's sidecar span 0.92241 to six digits**, reached by a different route (f64 sidecar decode + corner displacement, not a gathered render). The orchestrator's 0.85715 is fact 1295's **true** span 0.85714. The **1.84x** I reported as a disagreement is `(1-0.85714)/(1-0.92241)` = **exactly the reciprocal of the solve's 54.3% application rate**. | The two figures were never in conflict: one is the drift that *exists*, the other the drift the solve *applies*. **I mislabelled a real defect as a bookkeeping dispute.** The corroboration is worth keeping because it is instrument-independent: M97 measured the shortfall by rendering, M87 by decoding, and they agree. | MEASURED |
| P43 | **M87's registration negative is robust to P42.** The verdict rests on the measured alignment switch (ISO 0.06805 -> 0.06356, **6.6%** removal, overlapping CIs) and not on any drift magnitude. A *larger* true drift strengthens the drift hypothesis' prediction that alignment should remove the halo, so P42 can only make the observed 6.6% **more** discrepant, never less. | The 2x drift disagreement cannot rescue the registration hypothesis. No re-measurement after M97 is required before accepting §15. | DERIVED |
| P44 | **The lint failure reported against this file did not exist at `HEAD`.** The quoted S6 row (`ratio \|E\|/\|E_fwd\|`, line 886 not 845) has been escaped since commit `c24e347`, two commits before the shipping commit. `scripts/corpus_lint.py` exits **0**, and an independently written table checker agrees at **0 S6 / 0 S1 over 30 tables** — after a positive control in which a planted unescaped span and a planted extra cell both fired. | A stale lint result was attributed to a milestone by file. Attribution by file is sound only against a current run; re-run before attributing. | MEASURED |
| P45 | **§15.4's post-alignment residual, and the 91.7% prediction built on it, are WITHDRAWN.** Both derived from `E*` = 13.58 px, the aligner's held-out corner error. Fact 1295 measures that `E*` is **structurally blind to a common multiplicative gain error**, which is the error present; the true residual is **150.2 plane px**, ~12x my estimate. | A milestone's own prediction arm was invalidated by a sibling's instrument audit. **The conclusion did not depend on it** — see P46 — but the report said it did, which overstated the evidence. Withdrawn in place rather than quietly repaired. | MEASURED (M97, fact 1295) |
| P46 | **§15's negative survives the withdrawal, restated without any residual estimate.** The solve applies **70.97 px p-p** of in-ROI drift at `ROI_LEG` centre (sidecar, §15.4). The drift ladder (§15.5, single-depth plant, no occlusion) reads ISO **0.06448** at just **30 px p-p** — **94.8%** of the real bee halo's 0.06805. So alignment removed **2.37x more drift than the amount that manufactures 95% of the entire observed halo**, and the halo moved **6.6%** with overlapping CIs. | The refutation needs only the drift *applied* and the ladder, both measured directly. It is now **independent of `E*`, of the residual, and of the true drift span** — the three quantities that turned out to be wrong or unknowable tonight. Stronger than the original form. | DERIVED from MEASURED inputs |
| P47 | **The orchestrator's `bee3-zoomnull` is registered as an M87 control, and M87 had already run its twin.** §15.2 arm **Uw** — FOV- and resampler-matched, registration discarded — reads ISO **0.06844** against unaligned **0.06805** and aligned **0.06356**. The orchestrator's independent visual check of `bee-3-ALIGNED.tif` vs `bee3-zoomnull.tif` at 100% finds the silhouette halo present and unchanged in both. | **Two constructions of the same null, by two agents, agree**: discarding registration does not move the halo, and resampling alone does not move the metric (0.06844 vs 0.06805). This is the placebo that separates a geometry fix from an occlusion fix, and the halo fails it as a geometry defect. | MEASURED |
| P48 | **C-ZOOMNULL passes: the shipped correction is an occlusion fix, not a geometry fix.** With registration fully discarded (`STREHL_ALIGN=0`, gate 2) the correction cuts the halo metric **82.8%** (0.06878 -> 0.01186), against **72.9%** on the aligned render — **ratio 1.135**, inside the ±33% band. | Satisfies the orchestrator's decisive placebo: a fix whose benefit depended on alignment would be repairing geometry. This one does not. **Separately corroborates §15 at a second gate**: alignment alone moves the halo 0.06878 -> 0.06406, a **6.9%** removal, against §15.2's **6.6%** measured at gate 0 on different renders. | MEASURED |
| P49 | **THE PHOTOMETRIC SHARE OF THE HALO IS ZERO OR NEGATIVE AT EVERY CORRECTION STRENGTH.** Re-running the election on gain-normalised frames (`src/53`, lambda sweep of the per-frame gain, `ROI_LEG`, 6103 profiles) gives ISO **0.06804 / 0.06979 / 0.07120 / 0.07225 / 0.07379** at lambda = 0 / 0.25 / 0.5 / 0.75 / 1.0 — **monotone increasing**. Best lambda is **0**, the uncorrected shipped election. | **Per-frame photometric normalisation will not fix the halo**, and a single-point test could not have shown this: the ladder excludes a gentler correction helping. M99 is worth shipping for other reasons, but the halo should not be attributed to photometry. Protects M87's occlusion attribution from being explained away. | MEASURED |
| P50 | **M96's disconnected population and the orchestrator's enrichment both replicate on `ROI_LEG`, independently implemented.** Re-measured, not inherited: **27.083%** disconnected (M96 whole-frame: 25.247%), mean gap **64.51** frames. Gain normalisation re-elects **31.515%** of disconnected pixels against **3.580%** of connected — **enrichment 8.80x**, inside ORCH's 2.82-32.68x range — with a correctly specified label-shuffle null at **0.989x**. Median frame move among movers: **73** disconnected against **2** connected. | The mechanism ORCH describes is **real and reproduced**: photometric drift does attack precisely the disconnected population. **P49 is therefore the sharper result** — the mechanism fires, moves those pixels a long way, and still does not reduce the halo. Firing on the right population is not the same as fixing the defect. | MEASURED |
| P51 | **The halo metric cross-validates across two independent implementations.** A pure-Python re-election from the cached 299-frame cube gives ISO **0.06804** on `ROI_LEG`; §15.2's arm U, produced by the shipped Rust binary, gives **0.06805**. | Agreement to 1 part in 6800 between a Rust merge and a NumPy re-implementation of the documented focus formula. The metric and the harness are not encoding an artefact of either code path. | MEASURED |
| P52 | ~~**My illumination probe disagrees in SIGN with the reported early-frame brightness bias.**~~ **SUPERSEDED by P53 — there was no sign conflict.** The −3.18% was quoted in the *brightness* convention (`lev/ref − 1`); M99's +5.31% is the *correction gain* convention (`ref/lev − 1`). They are reciprocals of one signed statement. My own far-background figure in gain form is **+3.23%**. | Retained struck rather than deleted, because the dispatch that followed it stopped M99 shipping. The lesson is that a disagreement in sign between two probes is a **convention** question first and a measurement question second, and it costs one grep at the source to tell them apart. | SUPERSEDED |
| P53 | **The illumination-probe "sign conflict" was a convention difference, settled at source and not by re-measurement.** `crates/strehl-core/src/photometric.rs:390` computes `let g = (r / f.mean().unwrap_or(r)) as f32` — reference ÷ frame flux, the **correction-gain** convention. M87's −3.18% was the **brightness** convention. In gain form M87 reads **+3.23%**, M99 reads **+5.31%**: same sign, same direction, "the early frames are dim and need boosting". The residual 3.23 vs 5.31 is **region** (far background inside `ROI_LEG` vs a whole-frame low-detail mask ∩ warp coverage), not error. | **M99 is not blocked and should not have been.** ORCH's leading hypothesis — that M99 used a whole-crop median tracking the subject through focus — is **refuted at the source**: `photometric.rs` explicitly rejects patch medians for flux, states why in its header, and carries a unit test `defocus_alone_does_not_move_the_estimated_gain`. Two probes reported in reciprocal conventions look like a contradiction and are not one. | MEASURED (read at source) |
| P54 | **The far-background probe is an unbiased estimator of a planted signed gain.** `src/54`, a signed ramp materialised into the real 299-frame `bee-3-cpl` cube at amplitudes −8/−4/0/+4/+8%, recovered per frame as `ratio_k = lev_planted[k]/lev_base[k]` against the planted `plant_gain[k]`: **slope 1.000000** at every amplitude, **max relative error 1.8e−07** (float32 rounding), sign correct on every arm. The early-decile summary recovers at slope **1.000000**, residual ≤ 6.8e−06 pp. | Answers the dispatch directly: a planted +4% comes back as +4%, so the probe's sign is sound and its magnitude is not diluted. Note the test proves **sign and linearity only** — a global multiply scales every region alike, so it deliberately cannot discriminate regions. That needs P55. | MEASURED |
| P55 | **On a defocus-only null, an illumination estimator's STATISTIC dominates its REGION by ~99×.** Blurring one real frame at sigma = 0/1/2/4/8/16, max drift: whole-crop **median 2.942%** against whole-crop **mean 0.030%** — identical pixels, **98.8×** apart. Region, holding the statistic at mean, moves far less: far background **0.206%** vs a same-area contiguous block **0.041%**, **5.0×**. Subject-only reads **8.474%**. | **Independent corroboration of M99's central design decision** — flux as a mean above black rather than a patch median — reached on a different region with a different statistic from M99's own 18.2% vs 8.7%. Anyone building a photometric probe should spend their care on mean-vs-median before agonising over the region. | MEASURED |
| P56 | **M87's own far-background region is NOT the best available, and its area control failed.** A contiguous same-area block drifts **0.041%** under defocus against far background's **0.206%** — the far-background mask hugs the subject at 60 px and so has a long perimeter adjacent to high contrast, and flux leaks across that perimeter under blur. A registered `SHUF` control (same area, scattered) also beat it at 0.042%, because a uniform scatter estimates the **global mean**, which blur conserves — so `SHUF` was mis-specified as an area control and `BLOCK` replaced it. | Reported against my own instrument. The far-background probe is sound in sign and linearity (P54) and far better than median- or subject-based probes (P55), but **compactness beats subject-avoidance** for blur invariance. A future probe should prefer a compact low-detail patch. | MEASURED |
| P57 | **A truth-free fidelity bar for artifact removal: Blur-Matched Fidelity.** Race the candidate against a Gaussian blur bisected to suppress the **same** named coarse band, then compare on a named fine band: `BMF = fine(candidate)/fine(blur)`. Validated on the real 4688x7032 shipped pair — exactly **1.000000** in both bands where the correction changes nothing, and **0.9058** in the fine band at the site where it visibly destroys hairs. | X4 proved a suppression number cannot certify a reconstruction, and ORCH's "fidelity against truth" cannot bind on a real subject, where no truth exists. This binds without truth, is quiet on a no-op, and fires on known damage. **The general form: certify an artifact removal against the maximally destructive intervention achieving equal suppression.** | MEASURED |
| P58 | **The shipped halo correction is NOT TARGETED: it removes fine structure harder than it removes the veil.** On the real full frame at the strongest-correction site, the FINE band (DoG 1–3 px) falls to **0.905812** while the COARSE band (DoG 8–32 px) falls only to **0.914575** — registered bar V3 **FAILED**. | Turns §16.9's visual finding into a number and gives the annulus milestone its objective: **drive COARSE down and hold FINE at 1**. A correction that takes more fine structure than veil is mis-aimed regardless of how good its halo number looks. | MEASURED |
| P59 | **My registered prediction that the correction is "no better than a blur" was WRONG: BMF = 4.43.** At matched coarse-band suppression a Gaussian blur retains only **20.5%** of the fine band; the correction retains **90.6%**. I predicted BMF ≤ 1.05 before running. | **§16.9's implication of blur-grade destruction is withdrawn.** The correction is genuinely structured, merely insufficiently selective — a different and far more fixable defect than the one I reported. Recorded because a registered prediction that fails is worth more than one quietly dropped. | MEASURED (prediction refuted) |
| P60 | **The detached pale islands in `flower-bud-alone-cpl` are not an election pathology.** The elected frame index inside them has a local 9×9 standard deviation of **0.50 frames**, against **0.42** in deep subject and **28.09 in the open white background**. | Fact 73's texture-free blind spot is real on this stack, but it lives in the **background**, not in the islands. The islands elect as coherently as the subject does. | MEASURED |
| P61 | **All three decidable islands sit at the depth of the surface around them, not the background's** — within 0–3 frames of the surrounding subject ring against 7–34 frames from the nearest background. Controls on matched geometry pass in both directions: untouched discs read SUBJECT **97.3%** (37 decidable), discs with the elected index overwritten by the local background read BACKGROUND **100.0%** (35 decidable). | Rules out the election importing a distant background into the subject's interior. The instrument is demonstrated able to return either answer before the verdict is read. | MEASURED |
| P62 | **The islands are two populations with opposite implications.** By count, **86.3%** rejoin the background under a closing of ρ ≤ 8 binned px — the veil band severed by hair-thin foreground — while a registered broken arm of matched-area discs in deep subject rejoins at **0.0%** (3.4% at ρ = 40). By area, **76.6%** sits 30–250 px from any background and is white card seen through **genuine holes in the plant**; one island holds 74% of all island area at d2bg = 192 px. | A veil correction should reach most islands and must **not** touch most island area. A metric averaging the two would be dominated by the population that is already correct. | MEASURED |
| P63 | **The veil boundary has no characteristic lengthscale.** Cut depth follows `depth(r) ∝ r^0.933` over 1–44 binned px, and the apparent knee tracks the ladder's endpoint — 5.47, 8.60, 11.70, 14.31 at endpoints 12, 22, 31, 44, a drift of **161.5%**. The resolution control passes independently (binned vs 2× render agree to 7.2% on the knee, 3.4% on the plateau), so the curve is physical and scale-free. | No pipeline stage's neighbourhood size is recoverable from the scalloping. The lobes are self-similar over the whole measured range. | MEASURED |
| P64 | **Two pre-registered candidate lengthscales were hit, and both hits were the instrument's own parameters.** A veil-band granulometry returned 2r = 42 px, exactly 2 × (`WINDOW_RADIUS` 13 + `REGULARISER_RADIUS` 8) — but halving `NEAR_VEIL` from 40 to 20 halved the answer, 20.16 to 10.66. A background granulometry returned 28.6 px, within 10% of 2 × `WINDOW_RADIUS` — but it was the ladder endpoint. | **Pre-registration made the artifacts more convincing, not less**: a dense candidate list guarantees an instrument-driven answer lands near a candidate. A registered prediction needs a companion control that varies the instrument's own parameter, not only the data. | MEASURED |
| P65 | **The veil does not breach the two-layer convex bound.** Deep subject 334, far background 4398, rim peak **3951 at d = −7 binned px** — 447 *below* the background, z = −62.8. A convex composite cannot exceed both layers, so an overshoot would have falsified the two-layer model; none is present. | The two-layer composite survives a test that could have killed it, on the strongest real halo case in the corpus. My own visual reading of the crops, which said the rim looked brighter than the background, was wrong. | MEASURED |
| P66 | **The rim is real against the background beside it: +18.97% above the local plateau, versus +0.42% for a registered invented boundary in open background — 45.6× the bias floor.** Scanning ~120 distance bins for a maximum is itself biased and manufactured an apparent +1.8% overshoot at z = 29.7 where there is no edge at all. | Establishes both the halo's amplitude on real data and the floor below which any profile-peak claim is the estimator. Any overshoot under ~2% measured this way is not reportable. | MEASURED |
| P67 | **The correctable rim is ~20 binned px wide and sits inside a ~150 px depression that may not be ours.** The background recovers to 90% of its open level only at **135 binned px** and 95% at **150 px**. A bud in front of a lit card plausibly shadows the card; that cannot be separated from a wide veil without a single-frame comparison. It is not vignetting, which darkens pixels far from centre and so far from the subject, against the observed sign. | Sizes the annulus at ~20 binned px rather than 150, and flags a large slow component that a halo metric would credit a fix for removing without it being a stacking defect at all. | MEASURED |
| P68 | **`flower-bud-alone-cpl` is not clipped anywhere.** On the per-channel maximum that `gallery.py` budgets, both the raw and the exposure-boosted TIFF read **0.0000%** at full scale and **0.0000%** at or above 0.99; the gain is set by the p99.9 target and never reaches the 0.5% clip budget. Background FINE-band rms is 0.002363 against the subject's 0.007493. | The "near-clipping white field" hazard does not exist on this stack and a normalised contrast measure reads it. The real hazard is dilution: the background is 78.67% of the frame at 3.2× less fine-band energy, so a whole-frame band average — but not the in-region BMF bar of §23 — would be swamped by it. | MEASURED |
| P69 | **The judged gallery crop comes from `-exposed.tif`, not `-srgb.tif`** (`gallery.py:135-147` writes `-100pct.png` from the exposure-boosted array). My first pass measured the raw file. | Fact 1324's failure mode, reproduced: the convenient image is not the judged one. Any corpus measurement of gallery output must state which of the two TIFFs it read. | MEASURED |
| P70 | **THE HALO IS AN ERASED VEIL, NOT ADDED LIGHT.** In linear raw DN over d in 2 to 22 binned px, every one of the 299 single frames is veiled by a mean **-26.4668% sd 3.0076%** relative to its own far level, the least veiled being frame 155 at **-20.2495%**. The gate-0 merge reads **-6.6810%** — the least veiled image in the set, **4.51 single-frame sd** above the best frame, **74.76%** of the mean veil removed. A uniformly random per-pixel election reads **-25.8547%**, inside the single-frame range. | The mechanism, restated: two-layer physics puts a radial darkening beside every occluding edge in *every* observation, and the election, being a max-like operator on brightness in the veiled band, erases three quarters of it. The eye reads a flat band abutting a falling gradient as a glow. **A per-pixel mixture as such does nothing** — it is this election. | MEASURED |
| P71 | **A registered prediction can be placed on the wrong window, and only a picture will tell you.** I registered `O`, an overshoot statistic comparing d in 12 to 22 against a 30 to 45 shoulder, and predicted `O(merge) > 0`. It came back **-0.004852**. Plotting the profiles showed the merge has a local maximum near d = 17 and a local minimum near d = 27, so the shoulder sat on the far side of the crossover and the two effects cancelled. | Pre-registration protects against choosing the answer; it does not protect against choosing the window. **Plot a thing you have already tabulated.** The replacement instrument (P72) found a +0.144 band where `O` found -0.005. | MEASURED (prediction refuted) |
| P72 | **A baseline-free halo metric: reference the frame ensemble, not a far window.** `E(d) = [image(d) - mean_k frame_k(d)] / far_level`. On the judged bee it peaks **+0.14393 at d = 13**, has exactly one sign change (**d = 32**), and troughs **-0.07961 at d = 92**; half-maximum spans **d = 2 to 19**. Single frames peak at **+0.03572 sd 0.03639**, max **+0.10115**; a uniformly random election peaks at **+0.01444**, an order of magnitude below the single-frame floor. | Every earlier halo metric needed a far window standing in for unveiled background, and on this image the profile is **still rising at d = 200**, so every available baseline sits inside the artifact. `E` needs none: each frame is a legitimate observation carrying the same veil, so their mean is what an ordinary image looks like at that distance, and any boundary-blind rule gives `E` near zero by construction. | MEASURED |
| P73 | **The band is a box, not a bump.** `E(d)` is flat at +0.13 to +0.14 from d = 3 to d = 19, falls to zero by d = 32, and goes negative to -0.08 by d = 92. | Matches the visible artifact exactly: a nearly uniform bright band with a hard lobed outer edge and *darker* background beyond it. A correction shaped as a rim taper is the wrong shape; the profile calls for a plateau with a sharp outer cutoff. | MEASURED |
| P74 | **The election anomaly and its photometric consequence peak at DIFFERENT distances: dR at d = 6, E at d = 13.** Near the silhouette every frame is heavily veiled, so even the elected sample is dark and `E` is small while the rank statistic is extreme; further out the veil retracts in some frames, so electing the maximum produces a large excess. | A fix keyed on *where the election is wrong* will under-treat *where the brightness error is largest*. These are two annuli, not one, and no design that treats a single radius can address both. | MEASURED |
| P75 | **The milestone's own frozen band-profile instrument is measured-blind on the image the owner judged**: +0.280% on `bee-3-cpl` `ROI_LEG` against +18.97% for the same statistic on the flower bud, on an artifact that is *more* conspicuous. Three causes: a "background" mixing card, cast shadow, defocused body and pale hair; a depression still deepening at d = 200 so no baseline exists inside the ROI; and a registered `C-BROKEN` control that landed on the subject (bee coverage **37.18%**) and returned **-14.502%**. | **A statistic validated on a compact subject against a uniform card can be blind on a tangled one.** Any halo number in this corpus taken with a far-window baseline should state the subject's coverage fraction and whether the profile flattens inside the ROI. | MEASURED |
| P76 | **Election brightness rank: a halo statistic with an exact analytic null and no baseline.** `R(p)` is the mid-rank percentile of the *elected* through-focus sample among that pixel's own 299 samples; null 0.5, invariant to any per-pixel monotone transform. On the judged bee it rises 0.5134 at d = 1 to **0.8758 at d = 5**, holds to d = 12 and falls through 0.55 at d = 27. `C-RANDK` returns 0.5 within 0.0176; the fast profiler reproduces the frozen `band_profile` at **max deviation 0**. | Shading, vignetting, the depression, cast shadow and local card/hair mixture all cancel because every pixel is scored only against itself. Rendered, the high-`R` band traces every leg, hair and claw with the visible lobed boundary — the statistic agreeing with the eye on the judged image. | MEASURED |
| P77 | **A control that failed to return its null became the decomposition.** Rolling the *elected-index field* by (317, 511) preserves the marginal distribution of elected depths, hence any photometric bias, and destroys only their registration with the boundary. So `dR = R_true - R_shuffled` is the occlusion-specific excess **with the photometric share removed by construction**. It peaks **+0.2584 at d = 6** and returns to zero at **d = 21** on bee legs, against the bud's rim peak at **d = 7** measured by an unrelated instrument. `dR(1)` is **negative** (-0.0839). | Cross-class replication of the annulus design constraint, and a reusable trick: shuffling a *label field* rather than the data separates registration-with-geometry from every marginal property at once. `dR(1) < 0` says the anomaly is not at the silhouette. | MEASURED |
| P78 | **The band gate is a threshold, not a gradient.** Split by the depth step across the nearest boundary: `\|dk\|` under 3 frames gives `dR` **-0.0268** (no band at all), `\|dk\|` at 60 and above gives **+0.3926**, and every bin between is **~0 within 0.07**. The registered monotone-ladder clause failed; the placebo clause passed. | An annulus fix should be **gated** on a large depth step rather than scaled by it, and it has a built-in placebo covering the same-depth boundaries, which is where §14's polarity falsifier showed `bee-3-cpl`'s reflectance edges live. | MEASURED |
| P79 | **Two more controls died of absent geometry, making four in this milestone.** `L.shifted_mask` invents a boundary "in open background" by translating the mask 512 px, but at **37.18%** subject coverage it lands on the bee. A windowed dark-class centroid could not move because **32.83%** of the window's border is dark class, so a planted 40 px ramp changed it by **-0.19 px**; restricted to the one border-free component above 2000 px it moves **38.02 px** for the same plant. | After §20's planted discs and §24's depth terciles. **Before trusting a control, measure that the geometry it requires exists where you put it** — coverage fraction for a translated mask, border contact for a windowed centroid. All four failures were silent and all four produced plausible numbers. | MEASURED |
| P80 | **`E*`-free drift verdict, and a registered claim withdrawn.** A tile-wise phase correlation recovers a planted (13, -21) translation exactly and a planted 1.010 magnification as **0.00901 (R-squared 0.9904)**, yet returns **0 of 24 tiles non-zero** between frame 0 and frame 298 of the unaligned raw cube. But registered bar J1 required 80% plant recovery on all five frame pairs and one pair gave **15 of 24**, so **the claim "no image motion in ROI_LEG" is withdrawn as registered.** | Recorded as a withdrawal because the bar was registered before running. The residual evidence — four sweep-spanning pairs at 23 or 24 of 24 tiles at exactly zero, the failing pair being the one with the least expected motion — is suggestive and not established. **§15 does not depend on it**: the band reads +0.2282 unaligned and +0.2651 after applying 70.97 px of warpmap, so it survives either alignment or a deliberate 71 px misregistration. | MEASURED |
| P81 | **The bee rim is a two-layer mixture in linear light, with a small chromatic residue that is 9x the noise floor.** On `ship-before-linear.tif`, chromaticity `(r, b)`: deep subject (0.358601, 0.300083), halo band (0.322687, 0.343316), far background (0.318767, 0.346940). The band lies **91.38%** along the segment with a perpendicular offset of **0.01039** against a `C-CHROMA-NULL` of **0.00113**. Registered bar passed. The scalar convex bound holds too, the band 22.05% below far background. | Bounds M107's demosaic candidate on this subject: the veil is overwhelmingly a two-layer blend, and the resolvable 1.04% off-segment residue is the only room a chromatic mechanism has. **Also a correction of my own §64 arm**, which passed on `bee3-full.tif` — a file `C-LINEAR-2` then measured as gamma-encoded (R-squared 0.9612, quadratic worth 63.8% of range, **92x** the curvature of the linear twin). Convexity is a claim about linear light. | MEASURED |
| P82 | **A positive control on identical content does not validate an estimator that must work across a change.** §66's D1 planted a shift on frame 0 and matched it against frame 0; it passed and was worth nothing. Re-run as frame 0 against frame 298 (G1), the same estimator still recovered the plant exactly — but only the second version was evidence. | General: **a control must be able to fail in the way the instrument actually fails.** Applies to any planted-signal check where the real task involves a domain change the plant does not reproduce. | DERIVED from MEASURED |
| P83 | **The two-component fit is NOT the limiter, and the two-layer model is not refuted.** On a depth-spread plant with known truth, handing the fit the **true `alpha_k` cube** captures **+100.59%** of the available headroom — band RMSE 1.7837% against a merge at 4.5271% and a far-field single-frame noise floor of 1.7999%. It exceeds 100% because the intercept is estimated across 121 frames and is therefore quieter than any one of them. | Answers the orchestrator's Q1. The external reviewer's two-layer bimodal-unmixing proposal is **still live**; §13's −28.2% is not a refutation of the model. | MEASURED |
| P84 | **`k_F` propagation is the entire difference between catastrophe and the floor, and its sign depends on whether the occluder spans depth.** Depth-spread plant: a global scalar `k_F` captures **−298.83%** of the headroom — 12.6769% band RMSE, **2.8x worse than the uncorrected merge** — while a per-pixel `k_F` map captures **+99.00%**. That is a **+397.83 point** swing. On the flat placebo, where the occluder is at one depth, the same substitution **costs −25.71 points** (+99.03% to +73.32%). | The propagation is load-bearing and **conditionally** so. Per-pixel `k_F` must be gated on measured depth variation, not applied unconditionally: on a single-depth occluder the estimated map is noise and makes the reconstruction worse. Reproduces §5.1 vs §5.2's real-data ordering (−3.74% vs −28.2%) with the sign of the catastrophe. | MEASURED |
| P85 | **Once `k_F` is per-pixel there is nothing left in the alpha model.** Oracle alpha minus per-pixel-`k_F` alpha is **+1.59 points** of headroom on the depth-spread plant (100.59% against 99.00%), and oracle `c` alone buys **0.00 points** (arms A and C identical to four decimals on the flat plant, and both catastrophic on the depth-spread one). | Effort spent refining `sigma_k = c\|k − k_F\|`, the blur constant, or the matte is spent on 1.59 points. **Effort spent resolving `k_F` per pixel is worth 397.83.** Also: on real captures per-pixel `k_F` reached only −28.2% while on the plant it reaches +99.00%, so a **third limiter exists that the plant does not contain** — naming it is the next experiment and is not claimed here. | MEASURED |
| P86 | **A decision rule that compares two arms to each other cannot tell "both stalled" from "both perfect".** Registered bar N2 read "if oracle arm E improves at least 2x more than arm B, the fit is not the limiter". It measured **E/B = 1.02x** and fired *"THE FIT IS THE CEILING: step 13 refutes the MODEL"* — the opposite of the truth, **because B had already reached the floor**. | General, and it is a defect in my own preregistration. **Score arms against an achievable floor, not against each other**: `captured = (RMSE_merge − RMSE_arm) / (RMSE_merge − RMSE_floor)`. A ratio between two arms is only interpretable once you know where the ceiling is. The registered output is left standing in §72's stdout and JSON; §74 is the correction, handled the way §15.4 was. | DERIVED from MEASURED |
| P87 | **Fidelity against truth does what suppression could not: it rejects destruction.** The registered broken arm (`alpha` to `1 − alpha`) captures **−2698.00%** of the headroom on the flat plant and **−2292.92%** on the depth-spread one. Bar X4 measured three of four deliberately broken unmixings *improving* the halo metric by 77–85%. | The paired fidelity term the orchestrator asked to be registered before building **works as intended**. Caveat, stated because it limits the claim: on these plants the broken arm also fails the suppression metric (−265.2% and −235.3%), so the plant does **not** reproduce X4's dissociation — it shows the fidelity metric is sound, not that the two metrics disagree here. | MEASURED |
| P88 | **The veil is TWO mechanisms, and the orchestrator's argued split is confirmed.** (a) An **election** artifact with two signs: `E(d)`'s positive box (peak +0.14393 at d = 13) and negative shelf (trough −0.07961 at d = 92) are both boundary-registered — rolling the elected-index field by (317, 511) leaves **39.1%** of the box and only **7.7%** of the shelf. (b) A **real frame-borne veil** present in every observation: on the ensemble, at fixed distance, level falls with local occluder coverage at **+0.534 per unit coverage** (r = 128), an observable amplitude of **+2.852%** of level against a rolled-coverage null of −0.0398 (7.5% of the reading) and a positive control recovering **100.6%** of a planted 3%. | The two are **0.358** apart in size, so the shelf is 2.8x the frame-borne veil — the correction is aimed at the dominant term, but a **~2.9% veil remains that no selector-side fix can reach**, because it is in every frame. That residue is what unmixing, and only unmixing, could remove, which links Q2 back to P83. | MEASURED |
| P89 | **`E(d)` is provably and measurably blind to anything present in every frame, which is why (b) needed a second instrument.** A fixed per-pixel gain scales every `k` at a pixel by the same constant, so `argmax_k` is **exactly** unchanged; `E` then reads **1.67%** of a planted −3% annulus. **My first version of that control reported 56.65%** because it built the planted baseline as `prof(mean_k frame_k)` while the true `E` uses `mean_k prof(frame_k)` — median and mean do not commute. | Fifth self-caught instrument defect in this milestone, and the first where the *control* was wrong and the *claim* was right. **When a control contradicts an analytic argument, check the control against the argument's own algebra before abandoning the argument.** The repaired version carries a bin-constancy check (max deviation **0.0001 DN**) proving the plant is exactly multiplicative within a distance bin. | MEASURED |
| P90 | **The premise of the orchestrator's Q1, and of my own preregistration, was wrong at source.** `13-unmix.py:98` is a global scalar `k_F`, and I registered a ladder on the belief that this produced the −28.2%. §5.2 of this report says otherwise: the global scalar produced **−3.74%** and **−28.2% is already the per-pixel `k_F` arm** (median band R-squared 0.200, coverage 19.8%). | Amended before any arm number was read, and both readings reported. **A line of code being wrong does not make it the line that produced the number** — the arm that shipped a result must be identified from the result's own provenance, not from the most suspicious code nearby. | DERIVED |
| P91 | **The bright veil is NOT a photometric step between elected frames, and correcting exposure makes it worse.** Holding the election *exactly* fixed and changing only what is composited, per-frame level normalisation moves the box from **+0.14393 to +0.16731 — 16.24% larger**, and the wrong way. Gain+offset normalisation with re-election leaves it at **102.22%**. | The registered positive control passes, which is what makes the null readable: a planted ±10% per-frame ramp moves the box **+0.02908** and normalisation removes **89.0%** of that movement. The instrument can remove a photometric step of exactly the proposed kind; it finds none in the box. | MEASURED |
| P92 | **The dark stand-off shelf IS substantially photometric, and this corrects §21 and §26.4.** With the election held *bit-for-bit* fixed, level normalisation alone removes **32.4%** of the shelf (−0.07961 → −0.05379). The election-alone cell moves it the other way, a **−15.7%** share (deeper, −0.08433). Both together remove 37.8%, interaction +29.9%. | §26.4 called both features "boundary-registered election behaviour". That over-attributes the shelf: a third of it survives the election being held constant and is carried by the frames' own levels. The orchestrator's photometric-step mechanism is real here, at the location and sign it predicted. | MEASURED |
| P93 | **A metric's baseline window can contain the very feature a null result is claimed about.** §21 concluded "the photometric share is zero" from ISO, whose `D_NEAR = (1, 24)` reads the box and whose `D_FAR = (48, 96)` is a *linear baseline fit* — and the shelf's trough sits at **d = 92, inside that fit window**. | ISO does not merely under-weight the shelf, it **absorbs the shelf into its own baseline**, so no shelf effect can register as signal. §21's headline is true of the box and structurally unmeasurable for the shelf. Check what a metric's normaliser spans before reporting a null over it. | DERIVED |
| P94 | **A rigid translation cannot discriminate two mechanisms that are both boundary-registered.** §26.4's roll control preserves *every* local winner-field index gradient exactly, merely relocated, so a photometric-step artifact collapses under the roll identically to a veiling artifact. | The roll separates boundary-registered from boundary-independent, which is what it was built for. §26.4 used it to separate two boundary-registered causes, which it cannot do. A control's discriminating power is a property of the transform, not of the hypothesis it is aimed at. | DERIVED |
| P95 | **A share-of-change statistic is sign-blind and will name a driver for a change in the wrong direction.** The registered rule attributed **99.6% of the box's change to photometry** — where the change was a **16.24% increase**. | The rule apportions a change without requiring the change to be a *reduction*, so it certified as "driven by" the mechanism the same numbers most cleanly refute. Direction must be tested before attribution; a ratio of two negatives reads positive and says nothing about benefit. | MEASURED |
| P96 | **Regressing frames on an ensemble reference does not measure exposure in a focus stack; it measures contrast.** The covariance fit reported **109.671% peak-to-peak "gain"** with a 4036 DN offset swing on a 3747 DN level. True per-frame mean level over the same region reads **17.339% p-p**, 6.3× smaller — and that is still an upper bound, containing breathing and defocus spill. | The planted-ramp control recovered the plant to **0.000%** error and was blind to the confound, because a covariance fit recovers a multiplicative plant whether or not it also carries a focus term. A passing positive control bounds sensitivity, not specificity. | MEASURED |
| P97 | **Between the frames actually elected, exposure drift is 19× too small to build the veil and has the wrong sign.** Elected-frame level at the band is **−0.7424%** against the far field — darker, where the veil is brighter — supplying **5.16%** of the 14.393% box. | Independently, the index-gap prediction fails: pooled within-distance Spearman ρ(excess, `\|Δk\|`) = **−0.0800** against a rolled-gap null of **+0.0713**, negative where a photometric step predicts positive. Two independent arms, both against the mechanism, for the box only. | MEASURED |
| P98 | **The photometric step at a silhouette is real, and it supplies about a tenth of the rendered step.** Isolated exactly by a paired difference between two composites that differ only in per-frame gain with the election frozen bit-for-bit, it is **6.34 DN of a 63.50 DN** observed step at the veil peak — **9.98%** — and 11.25% band-wide. | Registered bar: under 25% is not the cause. The mechanism exists, is measurable, and is minor. "Real" and "responsible" are separate questions and only an amplitude answers the second; a correlation cannot. | MEASURED |
| P99 | **Veil geometry beats photometry as a sign predictor, and photometry is below chance.** On the same pairs, the rendered step's sign is predicted by which side lies nearer the subject at **65.16%** at the veil peak (68.87% band-wide) against photometry's **48.87%** (52.38%). | This is the orchestrator's own proposed discriminator — a veiling mechanism has a fixed sign set by which side occludes — and it needs no model fit. Photometry sitting below 50% means the gain difference carries no usable sign information about the veil at all. | MEASURED |
| P100 | **A positive control can be weaker than the effect it is planted on top of, if it is anti-correlated with it.** This cube's natural drift has Spearman ρ = **−0.9289** against frame index; my planted `linspace` ramp has ρ = **+1.0000**. Their product has a *smaller* spread than the drift alone, so the control returned slope **−1.7375** where 1.0 was required. | The hump-shaped plant, ordered the same way as the drift, returned +0.8123 in the same run — the tell. A plant must be checked for sign agreement with the signal already present, not only for magnitude and ordering. Fixed by planting onto a drift-free base, where cancellation is impossible. | MEASURED |
| P101 | **A paired difference turns a hopeless regression into an identity.** Regressing the observed adjacent-pixel step on a predicted photometric step gave R² = **0.0014**, because the step is mostly scene structure. Differencing two composites that differ *only* in per-frame gain, with the election frozen, cancels scene, veil and election exactly and gives R² = **0.9681** at slope **+0.9802**. | The estimator is algebraically exact, so `C-EXACT` is a genuine harness check rather than a finding, and both plant shapes recover at slope 1.003 and 1.002 with the shuffled-gain null at +0.0018. Design the contrast so the nuisance cancels; do not fit through it. | DERIVED |
| P102 | **`bee-3-cpl` independently reproduces M99's drift shape.** Per-frame level peaks at **frame 103** with max/min **1.1894**; M99 measured the hump at frames **103-120** with max/min **1.1818** on different decks with different code. The endpoint ratios differ (1.1316 against 1.0380), so this deck is more strongly ordered end-to-end. | Two milestones, independent regions and independent scripts, agreeing on the location and depth of the hump. It also confirms M99 §12.3's correction of fact 23 at source: the operative property is smooth ordering, not monotonicity. | MEASURED |
| P103 | **The gap-correlation sign flip is an interaction, and single-factor attribution cannot see it.** Of the 2×2 {all band, M96-disconnected} × {M96 competitive-set gap, 5×5 winner range}, only **one** cell is positive: disconnected × M96 gap at **+0.1662** against a +0.0547 null. Changing population alone gives −0.0045; changing statistic alone gives −0.0221. | §27.7's −0.0800 was measured on the diluted population with the other statistic and is superseded for this question. My script compared swing magnitudes and printed "the sign is carried by the POPULATION", which is the same single-factor error class as the sign-blind share statistic of `P95` — the third time in two sections. | MEASURED |
| P104 | **M87's halo metric is not a sharpness proxy, so discipline 674 does not reach it.** ISO is a median *level* profile against distance. `P24` is the direct evidence: a Catmull-Rom gather that destroys ~49% of gradient energy moves the halo metric by **+0.6%**. | Audited on the orchestrator's instruction after a Laplacian-energy proxy rated visible polygonal patchwork 2.73× sharper than the correct render. M87's detail-retention and BMF bars are ratios against an untouched reference on identical content, not absolute high-frequency energy, so none is withdrawn. | DERIVED |
| P105 | **A figure checker that tests presence cannot catch a figure that is wrong in one place and right in another.** Mutating all four instances of a value in §28 turns `verify_s28.py` red; mutating **one of the four** leaves it green. Seven registered controls, including two that mutate the JSON operand with the prose untouched, behave exactly as registered. | This is the checker's known blind spot, measured rather than assumed, and it is why the two operand-mutation controls matter: they prove the harness re-derives from data rather than matching the document against itself. | MEASURED |
| P106 | **The unmix really does work far worse on thin structures — the orchestrator's prediction is confirmed.** Re-scored on the same cached output, the shipped per-pixel arm captures **−11.01%** on the thinnest quartile of boundary points against **−32.80%** on the broadest — a **21.78 point** gap at **7.3** null standard deviations (20 shuffles, p95 \|gap\| 6.44). Scoring all points reproduces the shipped −28.16% to **0.003 points**. | One pooled number concealed a 3x difference between two halves of its own population. This is the strongest structure-dependence measured in M87 and it says where a correction must be aimed. | MEASURED |
| P107 | **But the support explanation is refuted three ways.** (1) `fit()` regresses across the **frame axis at each pixel independently** — there is no spatial neighbourhood to starve. (2) Measured finite observations per band pixel: **38.000 thin against 38.000 broad**. (3) The recorded arms run the wrong way: the per-pixel arm treated **19.8%** of the band against the global arm's 12.5% and did **better**. | More coverage, better result, is the opposite of starvation. A per-pixel through-focus regression has the same n frames on a one-pixel contour as in the middle of a region, so contour geometry cannot starve it by pixel count. The effect of `P106` is real; this explanation of it is not. | MEASURED |
| P108 | **The alpha-attenuation mechanism is real but non-operative, because the gate it would act through is non-binding.** At local blur (σ ≤ 40px) thin structures do attenuate alpha as predicted — median `amax` **0.1627** against **0.3444**, a 2.1x difference — yet the admission gate still passes **90.51%** of thin band pixels and 100.00% of broad. Alpha-gate-only coverage of the band is **97.62%** (100.00% at the shipped σ ≤ 238px) against a recorded **19.8%**. | So the `amax`/`amax − amin` gate rejects almost nothing, and the coverage limit is set by the **R² ≥ 0.5** term instead. A mechanism can be directionally correct and still explain nothing if the valve it operates is already wide open. | MEASURED |
| P109 | **The boundary population is a connected network of ribbons, not thin contours, and the map inverts the reading.** Verified on `argmax-index.tif`: frame 0 **29.8139%**, frame 175 **0.1813%**, boundary **29.9951%**. Median half-width **3.00 px**; 24.32% at ≤1px but 79.49% at ≤8px and p90 **12.37 px**. Of 42 408 components the largest holds **35.45%** of the population and only **4.15%** is speckle. | Rendered by width, the smooth petal-tracing arcs are the **widest** part of the population (≥16px across) while the thinnest part is diffuse speckle that traces nothing. The coherent occlusion contours are wide, which is a further reason a per-pixel fit is not starved on them. | MEASURED |
| P110 | **A sign error in this report: §5.1's `+3.7%, worse` is a small improvement, not a regression.** `13-unmix.json` and `17-perpixel.json` share a **bit-identical** `F0` of 0.0680424463788235 and the same convention, and the global-`k_F` arm scores 0.06549822 = **−3.74%**. So per-pixel depth is worth **24.42 points** (−3.74 to −28.16), not the ~30 stated. | Found while locating which script produced −28.2%. No conclusion overturns — −3.74% still fails the registered −50% bar and §5.1 still reads FAILED — but a load-bearing figure carried the wrong sign into `P8`, §26.2 and a report to the orchestrator. Corrected in place with the original wording shown. | MEASURED |
| P111 | **I failed discipline 676 inside the script written to honour it.** My `C-T3-COVER` control read "coverage ≥ 19.8% means the reconstruction is a superset, PASS". It measured **100.00%** and printed PASS. A gate passing everything is not a valid gate reconstruction, it is a degenerate one, and the two-branch bar had no way to say so. | Rewritten with three branches — broken below 19.8%, plausible to 60%, **degenerate** above — which is what voided T3 and forced the honest reading in `P108`. One hour after being handed the discipline, in the file that cites it. | MEASURED |
| P112 | **When two subsets return an identical statistic, audit the partition before the statistic.** T2/T3 first partitioned band pixels by the interior EDT at the nearest foreground pixel — but the nearest foreground pixel to a background pixel always lies **on the boundary**, where that EDT is ≈1. Both quartile thresholds came back **1.0** and the two subsets returned `amax` medians equal to four decimals. | I first diagnosed the spread of the *statistic* (`amax` IQR 0.124, non-constant) and concluded coincidence. The defect was in the *partition variable*, whose p25 and p75 were the same number and were sitting in the JSON. Repaired by propagating the boundary-point widths, after which the same comparison separates 0.1627 against 0.3444. | MEASURED |
| P113 | **The instance-blindness registered in §28.9 is closed.** `verify_s29.py` asserts an **exact occurrence count** for every figure, not presence, so control_s29.py N2 — which mutates exactly one of three copies of a figure — goes **RED**, where the equivalent §28 control stayed GREEN. 9 of 9 controls behave as registered. | Two of them (N3, N4) move a JSON operand with the prose untouched, which is what distinguishes re-derivation from pattern-matching. The cost is that the checker must be told how many times each figure is legitimately quoted, which is itself a check on the prose. | MEASURED |
| P114 | **The sidecar contamination I declared against myself did not occur, and §15.2's −6.6% is clean.** `A-aligned.tif` was rendered 03:43 with `STREHL_ALIGN=1` and no named sidecar, inside the window (03:15 → 10:32) when `strehl` still defaulted its sidecar into the read-only capture library. Re-rendered now with `STREHL_WARPMAP` pinned to a sidecar I solved into my own scratch at the merge's default reference (149 of 299), the output is **SHA-256 identical** to the original (`e5d6182fff887119e8fc5a12`, max absolute difference 0 DN over 8 241 504 px × 3). Arm U reproduces byte-identically too (`895e458dd8f4722de0dac57d`). | The registration arm A used was the correct 299-frame reference-149 solve after all. **P20 and P46 are restored from provisional to clean**, and now carry the provenance line the original run did not keep: `alignment: ON (sidecar-override), reference frame 149, 299 placed / 0 refused`, solve 0.0 s. A hash equality settles this where an argument could not. | MEASURED |
| P115 | **The `$LASTEXITCODE` truncation trap is a STALE READ, not a zero.** On pwsh 7.6.5 a truncating `Select-Object -First N` stage on a native command leaves `$LASTEXITCODE` **unmodified**, so it reports whatever the previous command left: primed with a success, a truncated **failing** run reads **0** (false green); primed with a failure, a truncated **succeeding** run reads **1** (false red). Windows PowerShell 5.1 returns **−1** in both. Truncating also stops the upstream: 0.3 s against 6.1 s untruncated. | The orchestrator reported this as "reads 0 when there are more than N matches". Measured, the count is not the trigger and 0 is not the value — the gate inherits an unrelated command's status, so **the same script can read green or red depending on what ran before it**. That is worse than a fixed wrong answer because it is not reproducible. `-Last N` drains the stream and preserves the true code, but still hides the diagnosis. | MEASURED |
| P116 | **This report was committed carrying three stray C0 control characters, and it is not the only file.** BEL (U+0007) at §5 and VT (U+000B) twice — in the **P113 fact row** and in §29.7 — where code spans for *alpha* and *verify_s29.py* were written. A PowerShell here-string of the `@"..."@` form treats the backtick as an escape character, so a backtick followed by *v* becomes U+000B and the closing backtick-before-space collapses to a space. A sweep of `docs/research/*.md` found **4 more of the same class** in `M105b-exposure-ship.md` (ESC, BS×2, FF). | The corpus linter does not check for control characters, so these survived `corpus_lint.py`, `tblcheck.py` and a 67-check verifier. **Any agent appending prose through a PowerShell here-string is silently corrupting code spans**, and it is invisible in a rendered diff. Write the appender to a `.py` file instead. | MEASURED |
| P117 | **At HEAD the merge does not read `<stackdir>/warpmap.txt`, and the capture library holds no sidecar.** `align_cmd.rs:861-873` `sidecar_path()` returns `cache_root()/{leaf}-{key:016x}.warpmap.txt` under `%LOCALAPPDATA%\strehl\warpmaps`; every other mention of `warpmap.txt` in the file at HEAD is a doc comment saying it is *deliberately not* that path, or a test fixture. `Get-ChildItem D:\personal\macro -Filter warpmap*.txt -Recurse` returns **0**, before and after two fresh renders. | Reconciles a disagreement rather than winning it: my own binary at `C:\dev\strehl-target-m87v` (built 05:01) **still documents** `--out` as defaulting to `<dir>/warpmap.txt`, so a report of the old behaviour is a report of a pre-`8118dd7` (10:32) build, not an error. The `STREHL_WARPMAP` prescription is correct and adopted regardless: it is hard-validated and never caches. | MEASURED |
| P118 | **The veil is 4133 DN, not “a few DN” — 6.31% of full scale, and plainly visible with no stretch at all.** Measured on `bee-3-cpl` at the shipped default against a LOCAL background reference (mean of far-field pixels beyond 70 px within a 251 px window, which cancels the scene gradient at any order): the residual rises from −35.5 DN at d = 5 px to **+3390.8 DN at d = 25 px** over a −742.5 DN far-field baseline, amplitude **+4133 DN** = **35.7** codes of the diagnostic cast = **16.1 of 255** codes in an 8-bit viewer. | The orchestrator described the step as “a few DN and invisible at normal display gamma” and reached for a 4× stretch to show it. That is wrong by three orders of magnitude, and it matters: the veil is visible in the **as-rendered** panel, so it needs no diagnostic view to justify it and no stretch artefact can be blamed for it. Control C-FAR, the same pipeline against a 180°-rotated subject mask of identical area and shape, returns **−316 DN** with no hump — 13.1× smaller and the wrong sign. | MEASURED |
| P119 | **The render’s noise field is exactly `n_eff` averaging, with no free parameter.** Local noise sd against local mean `n_eff`, over 710 160 background windows spanning `n_eff` 1.3 → 282.8 (211×) and noise 219.0 → 15.4 DN (14×), fits `noise = 283.3 * n_eff^-0.5228`. The exponent predicted by arithmetic alone is **−0.5000**. | Predicted before it was measured: §84’s pocket/far noise ratio of 7.2× implies an `n_eff` ratio of 52, and the run printed **mean n_eff = 55.321** before I looked. This is the strongest quantitative statement in the milestone and it is about the estimator working, not failing — the merge really is averaging √n frames per pixel, everywhere, including in the veil. | MEASURED |
| P120 | **The concentric banding is none of the three things offered — it is the diagnostic cast’s quantum crossing the `n_eff` field.** One output code of the 4× stretch is **115.7 DN**; P119’s noise law sweeps 257 → 15 DN across the region; they cross. Simulating the flatness statistic against the measured lag-1 correlation **+0.4676** and gradient **16.44 DN/px** puts the flatness-0.5 crossing at `n_eff` **12.86**, against **19.10** measured — ratio **0.67×**. | So the band SHAPES are real (they are `n_eff` contours, set by occlusion geometry) while the band VISIBILITY is the 8-bit cast: above the crossing the field posterises into plateaus, below it the noise self-dithers. Neither “veil falling off in steps” nor “quantisation in the stretch” alone. Control C-SIM reproduces the low-`n_eff` flatness the simulator was **not** tuned to — 0.170 predicted against 0.178 measured, **4.6%** error. | MEASURED |
| P121 | **The photometric step at election boundaries is below 1.00 DN per adjacent frame, and a coffee-bean-grade drift is excluded.** Median high-pass on election-index boundaries is **27.0 DN** against 26.0 DN off them — enrichment **1.04×**, rot180 null **0.93×**. Planting a MONOTONE per-frame ramp (M99 fact 23) calibrates that: 1 DN/frame reads 1.115×, 10 reads 1.269×, 100 reads 1.692×. M24’s worst corpus stack (coffee-bean, 11.70% end to end) is 20.0 DN/frame and would read **1.37×**. | **My registered bar was mis-set and I am withdrawing what it said.** “Enrichment ≥ 1.5× means detected” needs a plant of **100 DN/frame** = **58.5%** drift across the bracket, five times the largest drift anyone in this corpus has measured; a bar that only fires at 5× the largest known effect is not a test. The response CURVE is the result, not the threshold I hung on it. At 27.0 DN the step is **0.233** of one output code, so it is invisible in the figure regardless. | MEASURED |
| P122 | **The rendered gate overturned my own scalars on the flagship image.** The shipped correction scored leakage **0.000** into the subject (interior median and p99 both 0.0 DN) and a **96.3%** veil reduction (4133 → 153 DN). The 100% crop then showed the hair tips truncated to stubs against a hard stair-stepped edge. Re-measured on a population defined from the reference render — thin dark structure in near background — tip contrast falls **6316 → 3739 DN**, ratio **0.5919**, with **33.1%** of tip pixels dropping below half the selection threshold. | The scalar was blind for a reason that generalises: **0 of 39 274** hair-tip pixels lie inside the segmented subject mask, so 100% of the damaged population is invisible to a leakage test that only looks for spill INTO the subject. Near a silhouette the hairs ARE the background pixels. Same hole as the +72.9% episode. Controls C-INT (subject interior, untouched) and C-NULL (after replaced by before) both return **1.0000** exactly, so the estimator is sound and the erasure is real. The correction stays OFF, now for a measured reason on `bee-3-cpl` rather than an impression. | MEASURED |
| P123 | **Reproduce another agent’s artefact byte-for-byte before analysing it.** Re-rendering `bee-3-cpl` at the shipped default with `STREHL_WARPMAP` pinned to my own reference-149 sidecar produced a file **SHA-256 identical** to the orchestrator’s `bee-3-cpl.tif` (`e400a63aa9f6ab1f1957940d`), so the `--index-map` and `--n-eff-map` written in the same run are the election and `n_eff` fields OF THAT EXACT FIGURE. | Every claim in §31 about what the figure shows is therefore anchored to the figure rather than to a similar render, and the assertion is in the script so it cannot drift. This is the cheap move that converts “I looked at a render like yours” into evidence, and it cost one hash. | MEASURED |
| P124 | **No M87 render took the 40-frame `bee-3-cpl` sidecar: every render with recorded provenance placed the full 299-frame bracket.** The quarantined file (1560 bytes, a 40-frame solve) is refused by `load_or_solve`'s frame-count guard on any full-bracket run; the trap needs `--limit N` meeting an N-frame sidecar, and `--limit` appears **0** times in M87's 91 measurement scripts. | The evidence is the `alignment:` placed count, not the script tree: **0** of 106 scripts invoke the binary, so every render was hand-run and a flag count over the Python tree cannot speak to renders. My first draft rested on exactly that mistake and the verifier refused it. | MEASURED |
| P125 | **The M86c alignment watershed moves 100% of the render's pixels but only 6.86% of the halo.** Unregistered ISO **0.06878** against aligned **0.06406** on `ROI_LEG`. The correction removes **82.76%** unaligned and **72.93%** aligned, ratio **1.135**. | 27 of M87's data files were written before `885e9f7` (2026-08-24 03:15:23) and so describe an unaligned merge. This bounds what that can have cost: the halo survives registration almost intact, which is why no pre-watershed verdict in this milestone changes. It is also the same operand pair as `P48`, read here for a different question. | MEASURED |
| P126 | **A hash recorded beside the words “the shipped default” is not a record.** §31.1's provenance block named the gate only in prose; it now carries the invocation, the resolved `DEFAULT_GATE` = **4.0** with its source, and the binary's SHA-256. | M106 spent 1.9 hours attributing a regression that had not happened, because three milestones froze three different invocations and none recorded the command. `byte-freeze.rs:855` already says `DEFAULT_GATE` “is 4.0 today and was not always”. My own most recent hash had the identical hole, written hours after I had read the warning. | MEASURED |
| P127 | **A veil metric can be made EXACTLY invariant to a level shift, and exactly calibrated, rather than approximately either.** `V = peak ring residual / (far background level − subject level)` is first-order in the image top and bottom, so `x → a·x + b` cancels. Measured against the orchestrator's 2.14% drift: **V moves 0.000000% while the raw DN amplitude moves 2.1400%**. Planting a known veil returns `V + A/C` with error **0.00e+00** at three of four levels. | Answers the orchestrator's constraint that any veil metric must be invariant to a 2.14% global level shift. Invariance by construction is checkable at 1e−15; invariance by care is not checkable at all. The calibration matters as much as the nulls: it proves the instrument can respond, which no null does. | MEASURED |
| P128 | **The occlusion veil is NOT an admission artifact: it survives a 55.3× change in how many frames are averaged per pixel.** On four `bee-3-cpl` renders differing only in `--gate`, sharing one sidecar and a pinned exposure, mean `n_eff` falls **55.321 → 1.000** (38.77% → 100.00% of pixels at `n_eff = 1`) while V falls only **0.13480 → 0.11906**, r = **0.8833**, peak fixed at **25 px** in every arm. Across 27 parameter settings r ∈ [**0.8717**, **0.9843**], median 0.9076, and **no setting reaches the `GATE-DEPENDENT` branch**. | Refutes the orchestrator's eye judgement, which they had explicitly declined to promote. With resampling excluded by fact 1375 and demosaic by §27, averaging was the last cheap candidate; its exclusion leaves **selection itself**, which is the owner's original hypothesis and cannot be tuned away by any gate setting. | MEASURED |
| P129 | **And 96% of even that 11.7% is a level offset, not the veil.** `delta(d)` correlates with the veil profile at Pearson **0.1569**, slope **0.0186** where 0.1167 was predicted, and stays at **+486 DN** at d = 60 where the veil itself has decayed from +4296 to +838 DN. A constant fits it at RMS **148.4 DN** against **221.1 DN** for a proportional model, ratio 0.671 against a 0.70 bar. Removing the **+473.2 DN** offset gives r = **0.9958**. | The near/far offset is exactly the spatially organised drift the orchestrator described, and it is the one form of level change affine invariance CANNOT cover, because the baseline is taken from the far zone. So 88.3% is a lower bound on veil survival and 99.6% is the better estimate. Reporting both is what makes the conclusion independent of the 4% margin on B18. | MEASURED |
| P130 | **I wrote a control bar that could not recognise a null: `abs(V_ctl / V_real) < 0.25` on a SIGNED hump amplitude.** The repaired rotated-mask control returns **−0.079502** — negative at every distance in the 2–60 px window, so no hump exists to manufacture — and the absolute-value form reported that as **0.590, FAIL**. Two independent nulls of different construction agree: rotated **−0.079502**, translated **−0.093960**. | The third sign-blindness failure in this milestone's family, after `P95`'s share-of-change ratio and the orchestrator's two-branch bar. **A ratio of magnitudes is not a test of a directional claim.** The control was also contaminated by construction — 30.7% of its ring band lay in the real veil band — so one red control had two independent causes and neither was the metric. | MEASURED |
| P131 | **A binary-exact invariance control failed at 2.451e−07 because of the ACCUMULATOR, not a leak.** A 251 px box reference sums ~63 001 samples of magnitude ~5×10⁴, reaching **~1.795e+09** against float32's exact-integer ceiling 2²⁴ = 16 777 216 — **107× over**. In float64 the same three exact factors give **3.664e−15**, **6.69e+07× tighter**. | Extends the standing rule that binary-exact factors must reproduce bit for bit: when they do not, the next question is the accumulator width, because a real leak is width-independent and round-off is not. The bar was diagnosed and met, never relaxed. | MEASURED |
| P132 | **The −28.2% unmix is neither a model failure nor a support failure.** Not the model: with the true `alpha_k` cube the fit captures **+100.59%** of headroom (`P83`). Not the support: the regression runs along the **frame** axis per pixel with **38.000** observations on thin and broad alike, and the arm with **19.8%** coverage beat the one with 12.5% (`P107`). It is a **structure-scale** limiter — **−11.01%** thin against **−32.80%** broad, 21.78 points at 7.3 null sd (`P106`). | Answers the orchestrator's twice-asked routing question with a third option they did not offer. The routing that follows: not a rewrite of the forward model and not a change of support, but whether per-pixel `k_F` is estimable on thin structures at all. `P128` adds that this is unlikely to be a noise-averaging limit, since a 55.3× change in averaging leaves the artifact intact. | DERIVED |
| P133 | **The orchestrator's prediction is falsified by its own citation: −6.6810% is a gate-0 number.** Verified two ways at source -- §25.7 tabulates the row as `gate-0 merge` and `70-veil.py` prints `merge (gate 0)`, computed on the gate-0 elected merge `cache/bee3-leg-sel.npy`. So **74.76%** of the veil is already removed at `n_eff` = 1 with zero averaging, and §25's `C-RANDV` (−25.8547%, inside the single-frame range) already held the per-pixel mixture fixed while destroying selector information, and found no removal. | §25 had already run the orchestrator's causal experiment in a stronger form: it varies selector *informativeness* with averaging held at zero, which isolates the mechanism, where the gate ladder varies averaging with the selector informative in every arm. **Read the cited section, not the fact row** -- the prediction survived only in the compressed rendering. | MEASURED |
| P134 | **Veil depth does not depend on the gate, in the statistic the claim was made in.** §25's `V` across the orchestrator's four pinned arms: `dV` = **+2.3463 pp** against a predicted +19.79 pp, i.e. **11.86%** of the predicted swing **and of the opposite sign**. Branch `B19-FLAT`. Spearman rho(gate, `V`) = −1.0000 -- perfectly monotone, but in the direction where *more* averaging gives *more* veil. | A monotone ladder is not confirmation unless its **sign** matches the prediction. A bar checking only monotonicity would have reported this as support for the mechanism it refutes. | MEASURED |
| P135 | **The entire raw ladder movement is the reference, not the veil.** Signed decomposition of `dV`, taking no ratio of two signed numbers: near-only **−0.0198 pp**, far-only **+2.3667 pp**, cross −0.0006 pp, closure 0.000e+00. The near band spans **0.0673%** across the ladder and the far reference **2.7824%**, a **41.4x** ratio. With the reference pinned to gate 4.00 the ladder range is **0.0572 pp** = **0.289%** of predicted (`B20-NEGLIGIBLE`). | The quantity the mechanism requires to change does not change. Applying the orchestrator's own proposed remedy -- pin the reference -- removes the effect entirely, so their instrument and mine agree once the moving baseline they themselves diagnosed is removed. | MEASURED |
| P136 | **Robust across region and channel.** Same frozen-mask ladder on `ROI_LEG` and on the BLOB region the orchestrator filed as the flagship figure, in green and mean-RGB: near-band spans 0.1259% / 0.1231% / 0.3071%, pinned ranges 0.1073 / 0.1199 / 0.2993 pp, far-over-near ratios 24.2x / 22.7x / 9.6x. Branch `B22-ROBUST`. | On BLOB the **raw** `V` crosses zero across the ladder (−2.6159% to +0.2311%) while the pinned `V` does not move, so a headline statistic can change sign entirely through its denominator. | MEASURED |
| P137 | **The orchestrator's photometric drift is neither multiplicative nor additive.** Gate 4.00 -> 0.00: the far field falls −2.707% (−1162.3 DN) while the dark subject falls only −0.086% (−6.1 DN) -- a percent mismatch of 2.621 pp and an absolute mismatch of 1156.2 DN. Verdict `NEITHER`: the drift is confined to the bright background. | Decides whether a ratio metric is safe, and it is not safe by construction here. `V` survives a pure gain exactly (`C-MULT` 7.105e-15) but this is not a gain, so the reference must be pinned rather than assumed immune. `C-ADD` (−0.3267 pp) proves the instrument is responsive to the hazard, not blind to it. | MEASURED |
| P138 | **The unmix was not fitting an already-removed veil, but the intuition behind that guess is already measured.** Refuted: `P107` and `P132` record that the regression runs along the **frame** axis per pixel, upstream of the election, so the merge's 74.76% removal is invisible to the fit. Sustained in consequence: `P88` measures a **~2.9%** frame-borne veil present in every observation that no selector-side fix can reach. | The headroom available to unmixing on real captures is genuinely small, but because the election already took the reachable part, not because the fit is confused. Right consequence, wrong mechanism -- and the routing from `P132` (structure-scale limiter) is unchanged. | DERIVED |
| P139 | **A discipline this report had already closed came back three sections later, and only a per-section control caught it.** `verify_s34` passed 90 checks on its first run; `control_s34`'s `N10` altered **one of two** prose instances of a figure and it stayed **GREEN**, because every prose assertion was written as presence rather than count -- the exact blind spot `P105` measured in §28 and `P113` recorded as **closed** at §29. Restoring exact occurrence counts turns `N10` red and raises the suite to 97 checks. | The finding is the regression, not the defect. A clean first run is grounds for suspicion rather than comfort: `verify_s33` failed 14 checks on its first run and was the sounder instrument for it. Closing a discipline in one section does not carry it into the next, so each section needs its own controls even -- especially -- when its verifier looks clean. | MEASURED |
| P140 | **Appending §34 broke two verifiers that had been committed green; both defects were in the instrument, not the numbers.** `verify_s33` sliced its scope to end-of-file rather than to the §34 heading, so §34's legitimate citation of `55.321` pushed a count 2 -> 3; at the corrected scope every other count in §33 is unchanged. `verify_s32` re-counts scripts from disk by design, and tonight's new scripts moved its measurement denominator 97 -> 104 -- but both zeros re-derived as **0**, so `P124`'s claim survived and only its denominator was stale. | Neither was repaired by bumping an expectation; `verify_s33`'s own docstring forbids that as the road to a presence check. The harness prefix filter was **not** widened to shrink the denominator, since 0-of-N is stronger at larger N. A later section is the natural adversary of an earlier section's verifier, and re-running only the section under edit would have caught neither. | MEASURED |
| P141 | **The verification shape this milestone runs on preserves exit codes: 180 of 180 observations reported the true code, on runs where the truncation trap demonstrably fired.** Six pipeline shapes against a process whose true code is 1, at 10/200/5000 lines, pre-cleared per arm, repeated 12 times. `Out-String`, `Out-String -Width`, `Select-Object -Last` and capture-first never lost it; the `-First` arms were corrupted in **12 of 12** runs. | Two corrections to the rule as I received it. The corrupted value is **&#8722;1, never 0** on `PSVersion 5.1.26100.9168`, so a probe looking specifically for 0 records a false INCONCLUSIVE -- mine did. And the corrupted-arm count varied **4 to 6 of 6** across 12 identical runs, which confirms the race framing over the count framing by direct observation. **Scoped by `P142`:** both readings are properties of `PSVersion 5.1`, not of PowerShell -- on 7.6.5 the loss is deterministic and the corrupted value is 0. Annotated, not retracted. | MEASURED |
| P142 | **Which mechanism governs `-First`'s exit-code loss is decided by the PowerShell engine -- not by counts, races, or process style: 2880 observations across a 2x2 and a causal manipulation.** The strict quota model holds at **720 of 720** observations on PowerShell 7.6.5 and **587 of 720** on Windows PowerShell 5.1.26100.9168, failing in the same 6 of 9 arms whether run as a child process or dot-sourced in-process. Quota is necessary in both engines: the arms it predicts safe lost **0 of 1040**. Making the emitter sleep 300 ms after its last line drives 5.1 from 80.00% and 75.00% to **100.00%** at both volumes, while 7.6.5 stays flat at 100.00%. | Both published mechanisms are right about their own host and neither generalises, so `P141`'s race clause is scoped rather than retracted. The consequence that bites is the corrupted *value*, not the rate: 7.6.5 yields **0** and 5.1 yields **&#8722;1**, so the guard `if ($code -ne 0) { throw }` catches the trap on one engine and silently passes it on the other -- the one the agent shell runs. A guard verified on a single host is not verified. | MEASURED |
| P143 | **A third verifier broke on the same append, in a third distinct shape, and the common cause is not scope -- it is keying a check to a VALUE instead of to a SITE.** `verify_s29` counted the bolded rendering of its full-coverage figure across the whole document and expected 3 sites; §34's engine ladder quoted two unrelated rates of 100% and pushed the count to 5. The three defects differ in mechanism -- `verify_s33` sliced its scope to end-of-file, `verify_s32` re-counted a denominator from disk, `verify_s29` counted a generic value -- but each was an expectation that any future sentence could move. | Repaired by binding all three real sites to their own anchors rather than bumping 3 to 5, which is strictly stronger than the count it replaces: two of those sites are the same sentence and differ only in whether the verdict word is emphasised, and `control_s29`'s new `N11` collapses one onto the other -- a defect no bare count can see. Three sections appended, three earlier verifiers broken: that is a rate, not an anecdote. | MEASURED |
| P144 | **M87 is structurally out of reach of the unkeyed stack cache, and the warning that named it is superseded at HEAD.** Fact 1446 reports that `StackIdentity` omits `reference` and `resampler`, so an identical command line can return different bytes. Two grounds, both read in the Rust rather than relayed: (a) **no M87 script invokes the binary** -- every cube is a `rawpy` decode of the `.ARW` files (`m87lib.py:124,145`), and `fix_audit.py:58` *asserts* `scripts_invoking_binary` is 0 across the 104 measurement scripts, so this is a guarded property and not a lucky observation; (b) the one render-dependent line, the §33/§34 gate ladder, consumes ORCH's four pinned TIFFs, which were rendered with `STREHL_WARPMAP` set -- and `merge_cmd.rs:1135` resolves that to *an explicitly named sidecar ... otherwise the normal discover-or-solve path*, so the cache is bypassed, nothing is written, and a bracket mismatch is a refusal (`tests/byte-freeze.rs:69`). | **The control ORCH prescribed would have been the weakest evidence in this row, so I ran a stronger one.** Empirically the gate-4.00 arm still hashes `E400A63A...7112` on disk, matching three independent records: ORCH's provenance note, the `provenance.gate_4_sha256` this report's own §34 run stored at measurement time, and fact 1373's kernel A/B from a *different session and a different exposure code path*. All four arms carry distinct hashes at one byte length, so the cache never collapsed them. But a repeated hash alone cannot separate *correct bytes twice* from *the same stale bytes twice* -- only ground (b) does that, which is why the source read is load-bearing and the hashes are corroboration. Fact 1446 was measured before `69f7b4c`; at HEAD `solve_config_key` hashes `reference`, `spans`, `resampler` and every `SOLVE_ENV` variable, so **both** omitted fields are keyed, exactly as ORCH's own later fact 1476 concluded. | MEASURED |
| P145 | **A fourth verifier break, and P143's diagnosis does not cover it: the checks were anchored correctly and applied a REPLICATED RULE.** The harness/measurement split that P124's two zeros are scoped by was written out four times -- in `fix_audit.py`, `verify_s32.py`, `verify_s34.py` and a new probe -- and adding one prefix to one copy turned `verify_s32` and `verify_s34` red and moved the published denominator 104 -> 105 -> 104. Neither verifier was keyed to a value: both re-counted from disk exactly as designed, and both counted correctly under a rule that was no longer the one writing the JSON. | **Consolidating the rule fixes the drift and destroys the evidence, so it cannot be the whole repair.** One owner now defines the split and the other three import it -- after which the audit and its verifiers agree *by construction*, and their agreement stops being a measurement of anything. `verify_s32` therefore gained the check a shared constant cannot fake: a script excluded as harness may not decode a raw or open a frame cube, so the convention is tested against the property it stands for rather than against itself (58 -> 59 checks). **A duplicated definition is worse than a duplicated value**, because a value that drifts makes a check fail loudly, while a rule that drifts makes two instruments disagree about what they are counting -- and whichever runs last looks correct. | MEASURED |

### Capture request

None. Every measurement in §16-§18 reuses `bee-3-cpl`,
`flower-bud-with-background-fern-cpl` and synthetic plants already in the tree.

## 19. The registration confound, closed with the aligner's own warps

**Asked by the orchestrator at 06:31**, alongside a measurement of 603 px of
corner drift and a warning that "some fraction of what currently reads as
occlusion halo may be misregistration", with the reasonable fear that `d = 40`
had been tuned against a registration artifact.

**It had not, and the experiment was already done.**

### 19.1 Alignment is not pending; it is the default, and I used it

**MEASURED, at source.** `crates/strehl-cli/src/merge_cmd.rs:1199-1283` performs
the alignment solve inside `merge`, prints `alignment      : ON (...)`, and
`main.rs:71` documents `It ALIGNS BY DEFAULT (M86c)`. `STREHL_ALIGN=0` disables
it. Wiring alignment into the merge is therefore **already landed**, and §15
tested the halo across that switch on 2026-08-24 rather than waiting for it.

Both §16 renders set `STREHL_WARPMAP` to the fitted sidecar
(§16.7, line 1549), so the shipped BEFORE and AFTER are **both aligned
renders**. The ladder that chose `d = 40` was measured on aligned data.

### 19.2 The drift audit

`src/50-drift-audit.py` decodes all 299 placed warps from the sidecar and
evaluates `|a z + b - z|` at the four plane corners. **MEASURED:**

| quantity | value |
|---|---|
| frames placed | 299 of 299 |
| scale `\|a\|`, frame 298 | 0.922414 (**7.76%** shrink) |
| rotation, frame 298 | +0.4598 deg |
| max corner displacement | **351.4 px** binned (3516x2344) |
| same, at full sensor | **702.8 px** |
| drift at `ROI_LEG` centre, p-p | 157.2 px binned |

Against the two figures in circulation:

| source | corner drift, full sensor | implied `1 - s` |
|---|---|---|
| `main.rs:72` | 232.7 px | 0.0551 |
| orchestrator, 2026-08-24 | 603 px | 0.1427 |
| **fitted warps, this audit** | **702.8 px** measured; 327.9 px under a half-diagonal convention | **0.0776** |

The orchestrator's two numbers are self-consistent with each other under
"corner drift = `(1-s)` x half-diagonal at full resolution"; under that same
convention the fitted warps give 327.9 px, so the disagreement is a genuine
**1.84x on scale**, not a units slip. `main.rs` errs the other way. **I am not
adjudicating this** — it is M86/M97's number — but it should not be left open.

### 19.3 Why none of that moves §15

§15's negative is **not** a claim about drift magnitude. It is a measured
before/after across the alignment switch: **6.6% of the halo removed**, CIs
overlapping, where the drift ladder predicted **91.7%**. Drift magnitude enters
only through the *prediction*, and it enters monotonically — **more** drift
means alignment has **more** to remove, so a larger true drift makes the
observed 6.6% more anomalous, not less. **P42 cannot rescue the registration
hypothesis in either direction.** DERIVED.

Note also §15.2's arm **Uw** — resampled once but *not* aligned, ISO 0.06844
against unaligned 0.06805. Resampling by itself does not move the metric, which
removes the obvious alternative reading of the A/B.

### 19.4 On discipline 600

M87's only plant-then-restore on Rust was the six halo unit tests. The restore
**did** invalidate the build cache: the file was restored from `$env:TEMP`,
confirmed byte-identical with `Get-FileHash`, **`LastWriteTime` was then set to
`Get-Date`**, and the control was proven by **re-running it** (3 passed /
3 failed while planted; 6 passed after restore), never by diffing source.
Discipline 600's trap was avoided rather than survived by luck.


## 20. The half-drift finding lands on §15, and §15 survives it

**M97 fact 1295, folded 2026-08-24:** the alignment solve applies only **54.3%**
of the drift present — true span 0.85714, sidecar span 0.92241 — and `E*`, the
held-out pairwise residual, **cannot detect this**, because a pairwise residual
is blind to a common multiplicative gain error.

### 20.1 What it breaks in my report

§15.4 estimated the post-alignment residual inside `ROI_LEG` by taking
`strehl align`'s own `E*` = 13.58 px and scaling it by radius, giving \~12.6 px
p-p, and concluded the residual "lands in the ladder's flat region", predicting
**91.7%** halo removal. **That chain is invalid.** It rests entirely on `E*`,
and `E*` is now measured to be blind to the dominant error. The true residual is
**150.2 plane px**. The row and the 91.7% figure are struck in place (§15.4).

I record this as an instrument failure of the kind §15.6 already disclosed one
of, and not as a near-miss: **the report asserted a 92%-vs-6.6% contrast whose
larger number was unsupported.**

### 20.2 What it does not break, and why

The refutation can be stated using only quantities that were measured directly,
with **no residual and no true-span estimate**:

| quantity | value | source |
|---|---|---|
| in-ROI drift the solve **applies**, `ROI_LEG` centre | **70.97 px p-p** | §15.4, warp sidecar |
| ladder ISO at **30 px p-p** planted drift, no occlusion | **0.06448** | §15.5 |
| the real bee-leg halo | **0.06805** | §15.2 arm U |
| 30 px p-p as a fraction of the real halo | **94.8%** | DERIVED |
| halo change when those 70.97 px are removed | **6.6%**, CIs overlapping | §15.2 |

**Alignment removed 2.37x more drift than the amount the ladder says
manufactures 95% of the entire observed halo, and the halo did not move.**

This form is *stronger* than the original, because it is independent of `E*`, of
the residual, and of the true drift span — the three quantities that were wrong
or unknown tonight. It needs only the drift actually applied and the plant's own
transfer curve.

**Corroborated independently.** The orchestrator compared
`bee-3-ALIGNED.tif` against its FOV- and resampler-matched
`bee3-zoomnull.tif` at 100% on the leg boundary and found the halo present and
essentially unchanged in both. That is §15.2's arm **Uw** built by a second
agent from different code, and it agrees.

### 20.3 The zoomnull, registered as a standing control

Per the orchestrator's instruction, the FOV/resampler-matched null with
registration discarded is now a **named M87 control**:

> **C-ZOOMNULL.** Any candidate occlusion fix must change the halo metric by
> approximately the same amount with `STREHL_ALIGN=1` as with `STREHL_ALIGN=0`.
> A fix whose benefit depends strongly on alignment is repairing geometry, not
> occlusion, and must be rejected as an occlusion fix.

**RUN, and it PASSES.** `src/51-zoomnull.py`, two fresh gate-2 merges of
`bee-3-cpl` with `STREHL_ALIGN=0` (and `STREHL_WARPMAP` set, so `merge_cmd.rs`
returns no alignment **without solving**, and nothing is cached into the owner's
read-only library — fact 1296):

| arm | subject | ISO before | ISO after | change |
|---|---|---|---|---|
| aligned (as shipped) | 45.31% | 0.06406 | 0.01734 | **−72.9%** |
| **registration discarded** | 42.19% | 0.06878 | 0.01186 | **−82.8%** |

**Ratio 1.135**, inside the ±33% band. The correction's benefit **does not
depend on registration**, so by the orchestrator's own criterion it is repairing
occlusion and not geometry.

**A free corroboration of §15 fell out of this.** These are fresh renders at
**gate 2**, where §15.2's A/B was at **gate 0**. Alignment moves the halo from
0.06878 to 0.06406, a **6.9%** removal — against §15.2's independently measured
**6.6%**. Two render pairs, two gate settings, one conclusion.

### 20.4 Discipline 604, against my own metric

604 warns that agreement on a value is not agreement on a mechanism, and the
orchestrator adds that whole-frame gradient energy is measured-blind to at least
one real geometric defect. **M87's metric is not whole-frame gradient energy** —
it is a radial brightness-excursion profile taken along boundary normals — so
that specific blindness does not apply.

But the warning lands anyway, and §16.9 is the proof: **the metric improved
72.9% while the photograph got visibly worse**, because flattening the near-edge
profile satisfies it whether the veil was removed or the hair fringe was
destroyed. That is 604's disease found independently inside M87, and it is why
the shipped correction is **OFF by default**. A companion metric sensitive to
*structure destruction* remains the largest hole this milestone leaves behind.

### 20.5 A note on what "aligned" now means for §16

The §16 renders are aligned, but fact 1295 means they still carry **~46% of the
drift**. Every §16 number should be read as "with the solve applied as shipped",
not "registered". Since the halo is measured not to respond to registration at
all (§20.2, and the orchestrator's null), this does not affect the halo
conclusions — but it will matter to any future sharpness claim on those files.


## 21. The photometric decomposition: the mechanism is real, the share is zero

**Asked by the orchestrator** on the strength of M96's disconnected competitive
set and facts 1262-1266: separate the halo into a photometric share and an
optical share, so the result cannot be attributed away later.

**Answer: the photometric share is zero or negative. The optical share is all of it.**

### 21.1 The question my own §5 never asked

`src/05-photometry.py` renormalised **the estimate** and left the selection
untouched — its own comment says so. So it could not see the effect that
matters here, which is a gain bias changing **who wins**. `src/52` and `src/53`
apply the gain **before** the focus field is computed.

**Why the test can express the failure (DERIVED, and checked before running).**
The field is `box(sobel(L),13) / max(sigma(L),eps)` with
`sigma ~ sqrt(0.5(gL + rn^2))`. Under a per-frame gain `a` the numerator scales
by `a` and, shot-noise dominated, `sigma` by `sqrt(a)`, so the field scales by
**`sqrt(a)`**. A 5% level bias moves the response ~2.5%, which is large against
`t*sqrt(2)*FOCUS_NOISE_SD`. **A scale-invariant focus measure would have made
this test vacuous. This one is not**, so the plant can express the failure.

### 21.2 The mechanism reproduces

M96's definition is used verbatim and cited, not re-derived. Re-measured on
`ROI_LEG` rather than inherited from M96's whole-frame figure:

| quantity | this ROI | for reference |
|---|---|---|
| disconnected competitive set | **27.083%** | M96 whole-frame 25.247% |
| mean gap | **64.51** frames | M96 29.12 |
| re-election under gain normalisation, disconnected | **31.515%** | — |
| re-election, connected | **3.580%** | — |
| **enrichment** | **8.80x** | ORCH 2.82-32.68x, median 16.87x |
| label-shuffle null | **0.989x** | must be ~1.00 |
| median frame move, disconnected / connected | **73 / 2** | ORCH 35,60,46,5 / 1 |

**The orchestrator's mechanism is real and it reproduces on my ROI with my own
implementation.** Photometric drift does attack exactly the disconnected
population, and it moves those pixels a very long way.

### 21.3 And it does not reduce the halo

| lambda (gain strength) | ISO | 95% CI |
|---|---|---|
| **0.00** (shipped election) | **0.06804** | [0.05981, 0.07982] |
| 0.25 | 0.06979 | [0.05929, 0.08271] |
| 0.50 | 0.07120 | [0.05963, 0.08494] |
| 0.75 | 0.07225 | [0.06025, 0.08661] |
| 1.00 (full correction) | 0.07379 | [0.06144, 0.08771] |

**Monotone increasing. The best correction strength is none.** A single-point
test at lambda = 1 would have shown -8.4% and left open that a gentler
correction helps; the ladder closes that.

**This is the sharper form of the result.** The mechanism fires on the right
population, moves a third of it a median of 73 frames, and the halo does not
improve. **Firing on the right pixels is not the same as fixing the defect** —
which is discipline 604 again, from the opposite direction.

### 21.4 Two instrument defects I hit and fixed, disclosed

1. **My first label-shuffle control read 2.724x where the null is 1.00.** It
   compared the shuffled-positive rate against the **true** connected rate
   instead of recomputing both arms under the shuffled labels. Mis-specified
   control, not a finding. Corrected it reads **0.989x**.
2. **My first illumination probe was a whole-crop median**, which gives a 20.75%
   spread — 3.9x the reported 5.31% — because the subject sweeps through focus
   and the median tracks real scene content. Normalising by it would have
   removed signal. Replaced with far-background pixels only (>60 px from the
   subject), where defocus preserves the mean.

### 21.5 A sign disagreement for M99

> ⚠ **RESOLVED IN §22 — there was never a sign conflict.** The two numbers are
> reciprocal conventions of the same signed statement. This subsection is kept
> as written because it is what triggered the dispatch that stopped M99
> shipping; §22 is the correction.

My far-background probe gives an early-decile bias of **−3.18%**; the
orchestrator reports **+5.31%**. **The signs are opposite.** Total p-p 17.83%,
31-frame-smoothed 12.36%. I am not adjudicating this — different probes on
different regions — but M99 should confirm which probe its normalisation is
built on, because a correction applied with the wrong sign doubles the error it
was meant to remove.

### 21.6 Cross-validation that fell out of it

The pure-Python re-election reproduces the shipped Rust binary's halo:
**0.06804** against §15.2 arm U's **0.06805**, agreement to 1 part in 6800,
through completely independent code. The metric is not an artefact of either
implementation.

## 22. The probe sign, settled at source — and the finding it uncovered

**Dispatched by the orchestrator at 07:08**, which held M99 from shipping until
the sign of the early-frame brightness bias was settled, and asked me for two
things: the exact region definition my probe uses, and a planted signed gain
ramp recovered by it.

Both are below. The answer to the dispatch is that **there was never a sign
conflict**, and the experiment I ran to prove my own probe sound turned up a
more useful result than the dispatch asked for.

### 22.1 The exact region definition

```python
mask  = bee3-leg-mask.npy                      # subject mask on ROI_LEG
probe = distance_transform_edt(~mask) > 60.0   # background, >60 px from subject
lev[k] = luma[k][probe].mean()                 # mean, not median
ref    = median(lev)                           # over all 299 frames
gain[k] = ref / lev[k]                         # CORRECTION-GAIN convention
```

`ROI_LEG` is `(1200, 1900, 300, 1400)` on the binned 3516x2344 frame, expanded
by `MARGIN = 22`; the cube is 299x744x1144. The probe covers **29.19%** of the
crop. Source: `experiments/M87-occlusion/src/52-photometric-share.py`,
function `per_frame_gain`.

### 22.2 There is no sign conflict — it is a convention, and it is readable

The last line above is the whole dispute. My probe returns the **correction
gain** `ref/lev`; the number I reported, **−3.18%**, was quoted in the
**brightness** convention `lev/ref − 1`. Those are reciprocals and they carry
opposite signs by construction.

I did not need to re-measure anything to settle which convention M99 uses.
`crates/strehl-core/src/photometric.rs:390`:

```rust
let g = if k == reference {
    1.0
} else {
    (r / f.mean().unwrap_or(r)) as f32
};
```

`r` is the reference frame's flux, so `g` is **reference ÷ frame flux** — the
correction-gain convention, the same as mine. Converting my figure to match:

| probe | brightness, `lev/ref − 1` | correction gain, `ref/lev − 1` |
| --- | --- | --- |
| M87, far background | **−3.13%** | **+3.23%** |
| M99, as reported | −5.04% | **+5.31%** |

**Same sign, same direction: the early frames are dim and need boosting.** The
residual 3.23 vs 5.31 is a **region** difference — mine is far background inside
`ROI_LEG`, M99's is a whole-frame low-detail mask intersected with warp
coverage — not a disagreement about direction.

**ORCH's leading hypothesis is refuted at the source.** M99 does *not* use a
whole-crop median tracking the subject through focus. `photometric.rs` rejects
patch medians for flux explicitly, gives its reason in the module header
("blur conserves flux… the mean above black over a fixed region is blind to
redistribution"), reports 18.2% for patch medians against 8.7% for conserved
flux, and carries a unit test named
`defocus_alone_does_not_move_the_estimated_gain`.

**M99 is not blocked by me and should not have been held.**

### 22.3 The planted ramp: the probe is unbiased

`src/54-probe-plant.py`. A signed ramp is **materialised** into the real
299-frame cube — every planted frame is actually multiplied and re-probed, so
the recovered slope is a property of the pipeline and not of algebra — at
amplitudes −8 / −4 / 0 / +4 / +8 %.

The primary test involves no median at all: the per-frame ratio
`lev_planted[k] / lev_base[k]` must equal the planted gain, frame by frame.

| arm | amplitudes | slope | max rel. err | sign |
| --- | --- | --- | --- | --- |
| FAR | ±0.04, ±0.08 | **1.000000** | 1.6e−07 … 2.0e−07 | OK |
| CROP | ±0.04, ±0.08 | **1.000000** | 9.4e−08 … 1.1e−07 | OK |
| SUBJ | ±0.04, ±0.08 | 1.000000 / 0.999999 | 1.9e−07 … 2.4e−07 | OK |

**A planted +4% comes back as +4%.** The residual is float32 rounding. The
early-decile summary recovers at slope **1.000000** with residual ≤ 6.8e−06 pp.

**What this test cannot do, stated plainly:** a global multiply scales every
region alike, so *every* arm passes. It proves sign and linearity; it cannot
tell me my region is the right one. That needs §22.4.

**An instrument defect, disclosed.** The first version of `src/54` predicted the
planted shift as `mean(pg[:E])/median(pg) − 1`, which assumes the median of a
product is the product of medians. It is not, and the FAR arm read a slope of
**0.8079** and looked 19% diluted when the probe is exactly linear. The
correction was to make the per-frame ratio primary and to compute the summary's
prediction by the same route as its measurement.

### 22.4 The defocus-only null — and the finding that matters

Blur conserves flux, so a probe that measures **illumination** must not move
when only focus changes. This is the property that discriminates regions, and it
is the same one M99 asserts. One real frame (k = 149), Gaussian blur at
sigma = 0/1/2/4/8/16, max drift from sigma = 0:

| arm | statistic | region | max drift |
| --- | --- | --- | --- |
| GMEAN | mean | whole crop | **0.030%** |
| BLOCK | mean | contiguous, same area as FAR | **0.041%** |
| SHUF | mean | scattered, same area as FAR | 0.042% |
| FAR | mean | background, >60 px from subject | **0.206%** |
| CROP | **median** | whole crop | **2.942%** |
| SUBJ | mean | subject only | **8.474%** |

**The estimator's statistic dominates its region by two orders of magnitude.**
`CROP` and `GMEAN` are the *identical pixels* and differ only in median vs mean:
**2.942% against 0.030%, a factor of 98.8**. Changing the region while holding
the statistic at mean moves things **5.0×** (FAR 0.206% vs BLOCK 0.041%).

This is independent corroboration of M99's central design decision, reached on a
different region with a different statistic from M99's own 18.2% vs 8.7%.
Anyone building a photometric probe should settle mean-vs-median before
agonising over the region.

### 22.5 Against my own instrument: my region is not the best one

My registered prediction was that FAR would drift least of the three real
regions. It did — 0.206% against CROP 2.942% and SUBJ 8.474%, **PASS**.

**My area control FAILED.** A contiguous block of the same area drifts
**0.041%**, five times less than my far-background mask. The reason is
geometric: a mask defined by `distance > 60 px` hugs the subject, so it has a
long perimeter running alongside high-contrast edges, and flux leaks across that
perimeter under blur. **Compactness beats subject-avoidance.**

**A second mis-specified control, disclosed.** The control I registered first was
`SHUF` — FAR's pixel count scattered at random — intended as "same area, wrong
place". It read 0.042% and beat FAR, which looked like a verdict on my region
and was not: a uniform scatter over the whole crop estimates the **global mean**,
and blur conserves the global mean, so `SHUF` is the most blur-invariant
statistic available rather than a same-area control. `BLOCK` replaced it. That
is the third instrument defect I have disclosed against my own harness tonight,
after the label-shuffle in §21 and the prediction formula in §22.3.

### 22.6 What this changes

Nothing in the halo verdict. §21's conclusion is untouched: the photometric
share of the halo is **zero or negative at every correction strength**, and that
conclusion never depended on the sign convention, because the lambda ladder
applies whatever gain the probe produces and measures the halo that results. A
sign error would have shown up as the ladder improving in the other direction;
it does not improve in either.

What it changes is the dispatch: **M99 should be unblocked.**

## 23. The bar for the annulus milestone, built and validated first

**ORCH's next dispatch is the matting-based annulus reconstruction, and says
"the bar is the part I care about most."** I agree, so I built the bar before
arguing about the algorithm. §23.4 is where I disagree with how the bar was
specified; §23.1–§23.3 are the measurements that earn the disagreement.

### 23.1 Why a truth-based fidelity term cannot bind here

The bar as dispatched is "a fidelity term measured against truth", with §6.3's
band RMSE named as its shape. That instrument is real and it works — on the
**synthetic** two-layer scene it separated the working reconstruction
(3.46% → 1.82%, the far-field floor) from the cosmetic mode partition
(**+254.6%**).

But the synthetic scene is **where the last attempt already passed**. It failed
on the real bee, and on the real bee **there is no truth**: you cannot
photograph what is behind an opaque subject. That was recorded as a caution when
the flower-bud A/B was delivered and it still holds. A bar that binds only where
the previous attempt succeeded cannot catch the next failure — which is the
exact shape of the miss in §16.9, where crop-scale evidence did not transfer to
the full frame.

So the real-data bar has to be **truth-free**, and this section builds one.

### 23.2 Blur-Matched Fidelity, and the bands it is stated in

The halo is a **broad veil** (d ≈ 15–40 px). The hair fringe is **fine
structure** (1–4 px). A band-separated comparison can tell "removed the veil"
from "removed the hairs" — but only if it is never band-averaged, which is
discipline 643 and ORCH's explicit warning. Two named bands, never combined:

| band | difference-of-Gaussians | structure |
| --- | --- | --- |
| **FINE** | sigma 1.0 − 3.0 | ~2–6 px: hairs, facets |
| **COARSE** | sigma 8.0 − 32.0 | ~16–64 px: the halo veil |

X4 proved suppression cannot certify anything, so the instrument races the
candidate against **the maximally destructive intervention that achieves the
same suppression**: a Gaussian blur, bisected until its COARSE ratio matches the
candidate's exactly, then compared on FINE.

```
BMF = fine_ratio(candidate) / fine_ratio(coarse-matched blur)
```

`BMF > 1` means the halo suppression was bought more cheaply than destruction
buys it. `BMF ≤ 1` means the candidate is no better than a blur.

### 23.3 Validated on the real full frame, on the known-bad transformation

`src/56-bmf.py`, on the shipped pair `30-SHIP-BEFORE-default.tif` /
`31-SHIP-AFTER-fixhalo.tif` at 4688x7032x3, read with **tifffile, never PIL**
(P40). Bars V1–V4 were written into the script's docstring **before it was
run**, V4 included, as a registered broken arm rather than an afterthought.

| region | changed | max delta | FINE ratio | COARSE ratio |
| --- | --- | --- | --- | --- |
| **NO-OP** y1500..2100 x3500..4300 | 0.00% | 0 | **1.000000** | **1.000000** |
| **DAMAGE** y866..1566 x1050..2150 | 12.42% | 11632 | **0.905812** | **0.914575** |

| bar | result | what it establishes |
| --- | --- | --- |
| **V1** ratios exactly 1.0 where nothing changed | **PASS** | the metric manufactures no signal |
| **V2** FINE < 0.95 at the damage site | **PASS** (0.9058) | it **sees the damage I saw by eye** |
| **V3** COARSE falls further than FINE | **FAIL** (0.9146 vs 0.9058) | the correction is **not targeted** |
| **V4** BMF > 1.05 against a coarse-matched blur | **PASS** (**4.43**) | it is far better than destruction |

**V3 is the important failure.** The shipped correction removes **fine structure
harder than it removes the veil** — 9.42% of the FINE band against 8.54% of the
COARSE band. That is §16.9's visual finding turned into a number, and it is the
precise design target for the annulus version: **drive COARSE down and hold FINE
at 1.**

**My registered V4 prediction was WRONG, and it matters.** I predicted
`BMF ≤ 1.05` — that the correction would prove no better than a blur, because
the render looks like a milky scalloped band. It scores **4.43**: at matched
halo suppression, a Gaussian blur keeps only **20.5%** of the fine band while
the correction keeps **90.6%**. **§16.9's implication that this is blur-grade
destruction was too harsh** and I withdraw that reading. The correction is doing
something genuinely structured; it is simply not *selective* enough, which is a
different and more fixable defect.

### 23.4 What I would change about the dispatch

**I accept the milestone.** I had intended to argue for gating the existing
correction on M96's disconnected set instead, on the grounds that it is cheaper
and targets the default-ON blocker directly. **My own evidence kills that
argument**: the abdomen hair fringe is a semi-transparent mat *at the
silhouette* (§16 line 503), so it is genuinely an occluding boundary and would
be genuinely *disconnected*. A disconnected-set gate would correctly flag it and
correct it, and destroy it exactly as now. Gating cannot fix a matting problem.
ORCH's instinct is right and mine was wrong.

**What I would change is the bar.** Register **both**:

1. the synthetic band RMSE against truth, as dispatched — necessary, and it is
   what caught the cosmetic mode partition at +254.6%; and
2. **the V1–V4 set above on the real full frame** — because it is the only one
   of the two that can bind where the fix actually failed.

Success for the annulus milestone, stated so it cannot be gamed: **V1 exact,
V2 ≥ 0.98, V3 PASS, V4 ≥ 4.4** — hold fine structure while taking more of the
veil than the current correction does, and stay well clear of blur.

## 24. `flower-bud-alone-cpl`: the islands are two things, and neither is an election bug

ORCH dispatched this stack as "the best halo test case in the corpus", described
four features of `flower-bud-alone-cpl-100pct.png`, and asked four questions. I
opened the render first and confirmed all four features by eye — a thick pale
band wrapping the silhouette, a lobed rather than smooth boundary, hard-edged
pale blobs inside the subject, and a mushy green surface. Then I measured them,
and **three of the four descriptions do not survive measurement**, including one
of mine.

Scripts `57-islands.py`, `58-island-depth.py`, `59-lengthscale.py`,
`60-islands-2pop.py`, `61-overshoot.py`; data in `experiments/M87-occlusion/data/`.

### 24.1 I measured the wrong image first, exactly as ORCH warned

`gallery.py:135-147` writes `-100pct.png` — the judged crop — from `out`, the
**exposure-boosted** array, and saves that same array as `-exposed.tif`.
`-srgb.tif` is the raw stack before the boost. My first pass read `-srgb.tif`.
That is fact 1324's failure exactly: scoring on the convenient image rather than
the one somebody looked at. Both arms are reported below.

### 24.2 Ask 2 — the islands. Two populations, and one of them is not a defect

The question was whether the detached pale islands share the veil's mechanism, on
the reasoning that a two-layer composite cannot occur where the background is out
of reach, so islands might instead be fact 73's blind spot: a texture-free cell
electing an arbitrary winner.

**The blind spot is real and it is in the white card, not in the islands.** The
local spread of the elected frame index, taken as the standard deviation in a
9×9 window, is **28.09 frames in the open background** against **0.50 in the
islands** and **0.42 in deep subject**. The islands elect coherently. It is the
featureless background that elects at random, which is the blind spot behaving
exactly as fact 73 says it should — in the region nobody was worried about.

`57`'s first attempt at the depth question compared each region's median elected
index against **global** medians. That test is invalid and I should have caught
it before running: the elected index *is* depth, so it is a function of position,
and a subject spanning 4000 px spans many frames. `58` replaces it with a local
test — island against its own surrounding subject ring and its own nearest
background — and adds the decidability gate that the local test needs, because
where the neighbouring subject and background elect the same frame **no** depth
test can separate them and the question is empty rather than hard.

| island | area (binned px) | d2bg | elected | ring subject | near background | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 12 | 130 | 3 | 140 | 141 | 110 | SUBJECT |
| 31 | 114 | 7 | 143 | 146 | 136 | SUBJECT |
| 35 | 114 | 3 | 137 | 137 | 103 | SUBJECT |

Three of the nine islands above 100 binned px are decidable at a separation of
≥10 frames, and **all three sit at the depth of the surface immediately around
them**, within 0–3 frames, against 7–34 frames from the local background. The
controls pass in both directions on matched geometry: discs left alone read
SUBJECT **97.3%** of the time (37 decidable of 56), and the same discs with the
elected index overwritten by the local background's read BACKGROUND **100.0%**
(35 of 58). The instrument can return either answer and it returns SUBJECT.

My first pair of controls **failed**, and correctly: I planted the positive-arm
discs in far background, where by construction no subject ring exists, so nothing
was classifiable and it scored 0 of 0. That is the same mis-specification as the
`SHUF` area control in §22 — a control whose geometry cannot express the effect
it is meant to detect.

So islands are not the election importing a distant background. They split
geometrically instead, by distance to the nearest background pixel:

| population | islands | % of island area | closing ρ ≤ 8 bridges | reading |
| --- | --- | --- | --- | --- |
| shallow, d2bg < 30 px | 160 | 23.4% | yes | the veil band, severed by thin filaments |
| deep, d2bg ≥ 30 px | 15 | 76.6% | no | genuine gaps through the plant |

A closing of radius ρ fills dark gaps narrower than 2ρ. At **ρ = 8 binned px,
86.3% of islands rejoin the background component**, while the registered broken
arm — matched-area discs planted in deep subject — rejoins at **0.0%**, rising
only to 3.4% at ρ = 40. The closing is not absorbing everything, so the 86.3%
means what it says: most islands are a contiguous bright band cut into pieces by
hair-thin foreground structure, and **a veil correction will reach them**.

The deep population is different and it is **not a defect at all**. One island
holds 10,134 of the 13,644 binned px of island area — 74% of it — at d2bg = 192
binned px. Its crop
(`C:\dev\strehl-out\M87-islands\island-0032-a10134-BACKGROUND.png`) shows white
card seen **through a hole in the plant**, with in-focus filaments crossing it.
The background reaches there because there is a gap. ORCH's phrase "in places
the background cannot physically reach" is false for **76.6% of island area**.

**So the answer to the ask is: two mechanisms, but the split is not the one
proposed.** By count, most islands are severed veil and a veil fix reaches them.
By area, most are real background through real holes and a veil fix must **not**
touch them. A metric averaging both would be dominated by the population that is
already correct.

Registered bar **B1 — that d2bg is bimodal — FAILED**: the 8–30 px trough holds
23.4% of islands against my ≤15% bar. It is bimodal in **area** and unimodal in
**count**, and I am recording the bar I registered rather than switching to the
measure that passes.

### 24.3 Ask 3 — the scallop lengthscale. There is not one, and I produced two false hits finding that out

ORCH's reasoning was that whatever sets the lobe scale — focus window,
regulariser neighbourhood, tile size — is identifiable from the render. It is
not, and the two things that looked like identifications were both my own
instrument parameters.

**False hit one.** `57` ran a granulometry on the veil *band*, defined as bright
pixels within `NEAR_VEIL = 40` px of the subject. Retention collapsed from 93.5%
at r = 16 to 30% at r = 21, and 2r = 42 px is exactly the pre-registered
candidate 2 × (`WINDOW_RADIUS` 13 + `REGULARISER_RADIUS` 8). It is not a lobe
scale: no disc of radius 21 fits inside a band 40 px thick. Halving the parameter
halves the answer — **half-loss r = 20.16 at `NEAR_VEIL` 40 and 10.66 at 20** —
so the measurement returned `NEAR_VEIL`/2 and nothing else.

**False hit two.** Measuring instead on the whole background component, with no
imposed thickness, gave a knee at **14.31 binned px**, a lobe width of 28.6 px,
within 10% of 2 × `WINDOW_RADIUS`. It passed the resolution control — the binned
and 2× render curves overlay to **7.2%** on the knee and **3.4%** on the plateau,
so the curve itself is physical. But the knee is defined against a plateau, and
`depth(r)` never plateaus:

| ladder ends at r | knee | knee / endpoint |
| --- | --- | --- |
| 12 | 5.47 | 0.456 |
| 22 | 8.60 | 0.391 |
| 31 | 11.70 | 0.377 |
| 44 | 14.31 | 0.325 |

**161.5% drift, and `depth(r) ∝ r^0.933`.** A power law has no characteristic
scale. The knee is wherever I stopped the ladder.

The reportable result is therefore a **negative**: the veil boundary has **no
characteristic lengthscale over 1–44 binned px (2–88 render px)**, so no stage's
neighbourhood size can be read off the render this way, and the scalloping is
scale-free over the whole measured range.

The transferable lesson is sharper than the result. **Both false hits were
pre-registered candidates.** Registration did not protect me — it made the
artifacts *more* convincing, because the candidate list was dense enough that any
instrument-parameter-driven answer would land near one of them. What caught both
was varying the instrument's own parameter and watching the answer follow it. A
pre-registered prediction needs a companion control on the instrument, not only
on the data.

### 24.4 The rim is real, but it does not breach the two-layer bound

The crops of islands 35 and 74 look as though the pale band is **brighter** than
the open background beside it. If that were true my whole model would be wrong: a
convex combination of two layers cannot exceed both of them, so an overshoot
would falsify the two-layer composite as the mechanism.

Measured on the signed distance to the silhouette, it is not true. Deep subject
sits at 334, the far background at 4398, and the rim peaks at **3951 at d = −7
binned px** — **447 below** the far background, z = −62.8. **Verdict O1: the
profile stays inside the convex hull, the two-layer model survives, and my visual
read was wrong.**

The registered broken arm earns its place here. An invented boundary drawn in
open background, where there is no edge at all, produced an apparent overshoot of
**+1.8%** at z = 29.7, purely because scanning ~120 distance bins for a maximum
is a biased estimator. Any overshoot claim below about 2% would have been my
estimator talking.

The rim is nevertheless real, because the eye does not compare against the far
field — it compares against the background next to it, and the profile is
non-monotone:

| reference | plateau | rim peak | at d | lift |
| --- | --- | --- | --- | --- |
| silhouette | 3321 | 3951 | −7 | **+18.97%** |
| invented boundary (broken arm) | 4324 | 4342 | −8 | +0.42% |

**+18.97% against a +0.42% bias floor — 45.6×.** So there is a genuine bright
annulus peaking 7 binned px outside the silhouette, sitting on top of a much
broader depression in which the background does not recover to 90% of its open
level until **135 binned px** and 95% until **150 px**.

I am **not** claiming the broad component is occlusion. A bud in front of a lit
card plausibly shadows the card near itself, and I cannot separate a real cast
shadow from a wide veil without a single-frame comparison. What I can say is that
it is not vignetting: vignetting darkens pixels *far* from centre, hence far from
the subject, and would work against the observed sign.

**For the annulus milestone this is the design number.** The correctable rim is
narrow — roughly d ∈ [−20, 0] binned px — and sits inside a 150 px feature that
may not be ours to correct. This is consistent with the earlier finding that
selection lands in the veiled band, and it sharpens it: the annulus is ~20 binned
px, not 150.

### 24.5 Ask 4 — the instrument in a white field. The premise is false

ORCH's caution was that a large near-clipping white background is where a
normalised contrast measure misbehaves. **Nothing is clipped.** On the
per-channel maximum, which is what `gallery.py:119` budgets, both TIFFs read
**0.0000% at or above full scale and 0.0000% at or above 0.99**. `gallery.py`
targets p99.9 at 0.92 in linear light and bisects the gain down whenever clipping
would exceed 0.5%; on this stack the target gain never reached the budget.

The band energies are not degenerate either:

| arm | Otsu τ | FINE rms bg | FINE rms subject | COARSE rms bg | COARSE rms subject |
| --- | --- | --- | --- | --- | --- |
| `-srgb` | 0.3891 | 0.001532 | 0.004852 | 0.007755 | 0.019428 |
| `-exposed` (judged) | 0.6310 | 0.002363 | 0.007493 | 0.011968 | 0.029989 |

The background carries real fine-band energy, so no ratio goes to 0/0. There
**is** a dilution hazard, but it is the one discipline 643 already names: the
background is 78.67% of the frame and carries 3.2× less fine-band energy than the
subject, so a whole-frame band average is dominated by area. The BMF bar of §23
is computed in named bands over a stated region and is unaffected; a band-average
version of it would not be.

### 24.6 Corrections to the dispatch

1. **"roughly as bright as the white background"** — islands sit at a median
   2869 against the background's 4320 in binned merge units, **66%**, and the
   rim peak is 10.2% *below* the far background.
2. **"in places the background cannot physically reach"** — false for **76.6%**
   of island area, which is background seen through genuine holes in the plant.
3. **"a large near-clipping white field"** — **0.0000%** of pixels are clipped
   on either TIFF.
4. **"the crop coordinates are recoverable from `gallery.py`'s `detail_peak`"** —
   true, but the array it crops is `-exposed.tif`, not `-srgb.tif`. I read the
   wrong one first.

None of these change the dispatch's conclusion that this stack is the strongest
halo test case available. It is. The veil is present, it is measurable at 45.6×
its own bias floor, and it now has a width.



## 25. The judged image: the halo is an erased veil, and the instrument that found it

The orchestrator's second dispatch retracted its own claim that the owner's
verdict was mostly about exposure, and named the image he actually judged:
`C:\dev\strehl-out\bee3-full.png`, written 2026-08-23 23:37. I verified that
at source rather than accepting it — the mtimes are 23:37 for `bee3-full.tif`
and `bee3-full.png` and 23:38 for `crop-leg-halo.png`, hours before
`ORCH-gallery` existed, and `62-bee-probe.py` measures the TIFF at
**(2344, 3516, 3) uint16 = 8.242 MP**, exactly half of 7032x4688 in each
direction. The retraction stands and the binning claim is independently
confirmed. Note in passing that the bee merge is 3516 px wide and the flower
merge 3514; nothing downstream may hardcode either.

This section is the work on that image. It is mostly a record of my own
instruments failing, because that is what happened: **the halo metric this
milestone has used since §2 cannot see the artifact in the image the owner
judged.** Five registered arms failed. What replaced them is better than what
they measured, and none of it would have been found by an instrument that
worked.

### 25.1 The frozen instrument is measured-blind on this image

`L.band_profile` takes the median of a value over background pixels at each
rounded distance from the subject mask, and `L.halo_from_profile` compares a
near band against a far baseline. On `flower-bud-alone-cpl` that reads the rim
at **+18.97%** above the local plateau (§24, P66). On `ROI_LEG` of the judged
bee it reads **+0.280%** — sixty-eight times smaller, on an artifact that is
*more* conspicuous to the eye, not less.

Three compounding causes, all measured:

1. The "background" in this crop is not one thing. It is open card, cast
   shadow, the bee's own defocused body seen between limbs, and pale hair
   brighter than the Otsu threshold. Those populations differ in level by more
   than the artifact does, so their median is dominated by mixture, not by the
   halo.
2. There is no baseline available. `68-breathing.py` H3 measures the linear
   radial profile out to 200 px and it is **still rising at d = 200**: 10280 DN
   at d = 1, 13720 at d = 20, 14352 at d = 80, 16659 at d = 200. Every far
   window inside the ROI sits inside the depression, so the statistic compares
   band against band.
3. The registered `C-BROKEN` control was invalid. `L.shifted_mask` translates
   the mask by (512, 512) to invent a boundary "in open background", but the bee
   covers **37.18%** of this frame, so the translated mask lands on the bee. It
   returned a lift of **-14.502%**, larger in magnitude than the real arm. This
   is the **third** control in this milestone whose required geometry was absent
   from where I put it, after §20's planted discs and §24's depth terciles, and
   the fourth arrives in 25.5.

`63-bee-judged.py` records this. Three of its four registered predictions
failed. I am not repairing that script; it is the evidence that the instrument
was inadequate.

### 25.2 The replacement: election brightness rank

`64-rank.py` drops the baseline entirely. For each pixel, take its 299
through-focus samples and ask where the **elected** one falls among them:

```
R(p) = [ #{k : v_k < v_a} + 0.5 * #{k : v_k = v_a, k != a} ] / (n - 1)
```

with `a` the elected frame index. `R = 0.5` is the exact analytic null for an
index chosen independently of brightness. Every pixel is scored only against
itself, so shading, vignetting, the depression, the cast shadow and any local
card/hair mixture cancel identically; `R` is invariant to any per-pixel monotone
transform. It needs no far window and assumes no distance is artifact-free.

Two checks before use. The fast profiler reproduces `L.band_profile` **exactly**
(max absolute deviation **0** over 96 bins), so the geometry is the frozen
geometry. `C-RANDK`, a uniformly random index per pixel, returns **0.5 within
0.0176**.

It works:

| distance d (binned px) | R |
| --- | --- |
| 1 | 0.5134 |
| 5 | 0.8758 |
| 12 | ~0.87 |
| 27 | 0.55 |

Rendered as an image (`C:\dev\strehl-out\M87-bee\64-rank-map.png`), the high-`R`
band traces every leg, hair and claw with the same lobed boundary as the visible
veil, and sits **outside** the silhouette rather than on it. That is the
statistic agreeing with the eye on the image the owner judged, which is the
check §16.9 taught this milestone to run.

### 25.3 The photometric share, and a broken control that turned into the method

`65-decompose.py` answered the orchestrator's decomposition request. Per-frame
gain normalisation (measured span **16.169%**, first-ten mean 0.97052 against
last-ten 0.92330, consistent with M99's early-frame bias) removed only **3.1%**
of the far-field tilt and *raised* the band amplitude 15.6%. Registered arm P1
**failed**: the tilt is not photometric. That is the third independent line
agreeing with P49.

The useful accident was `C-SHUF`. Rolling the **elected-index field** by
(317, 511) was meant to be a broken arm returning the 0.5 null. It did not — it
ran 0.59 to 0.67. The reason is that the roll preserves the marginal
distribution of elected depths, hence any photometric bias, and destroys only
their registration with the boundary. So

```
dR(d) = R_true(d) - R_shuffled(d)
```

is **the occlusion-specific excess with the photometric share removed by
construction**. A control that failed to return its expected null became the
decomposition the dispatch asked for.

`dR` peaks at **+0.2584 at d = 6** and returns to zero at **d = 21**. §24
measured the bud's rim peak at **d = 7** with a completely different instrument
on a completely different subject class. `dR(1)` is **negative** (-0.0839): the
anomaly is not at the silhouette. This is the annulus design constraint,
replicated across subject classes.

### 25.4 The placebo is a threshold, not a gradient

`66-repairs.py` D3 split background pixels by the depth step across the nearest
boundary. Registered as a monotone ladder; it is not one.

| depth step across the boundary | dR |
| --- | --- |
| 0 to 3 frames (median 1.6) | -0.0268 |
| 3 to 60 frames | ~0 within 0.07 |
| 60 frames and above | +0.3926 |

Where the two sides sit at the same depth there is **no band at all**. Where the
step is large the band is at full strength. Everything between is flat. The
registered monotonicity clause failed and the placebo clause passed, and the
threshold shape is the more useful result: an annulus fix should be gated on
`|dk| >= 60`, not scaled by it.

`66` also resolved §25.2's one loose end. Far-field `R` was **0.1745**, not the
0.5 null, and I had recorded that as a failure of arm R1. At **zero** subject
coverage within 96 px, `R = 0.4966` — the null. "Distance 80 from the mask" does
not mean "no subject nearby" in a crop full of criss-crossing legs. The deficit
is the other half of the same mechanism: far from every limb the card's own
texture wins the election, and in the card-sharp frame every surrounding limb is
maximally defocused and veils that pixel most.

### 25.5 The drift disagreement, and the fourth dead control

Three instruments disagreed about frame-to-frame motion in `ROI_LEG`: my FFT
phase correlation said **0 px** across all 299 frames, the aligner's warpmap
sidecar said **70.97 px** peak-to-peak, and §19's mask centroid said
**63.04 px**.

**G1 (67) passed.** Estimating frame 0 against frame 298 as-is gives (0, 0);
with a known (13, -21) planted on frame 298 it gives (-13, +21); the difference
is exactly the plant. The estimator solves a translation across the entire focus
sweep to the pixel, so its zero is a measurement. §66's D1 had validated the
same estimator on *identical content*, which is a control that cannot fail the
way the instrument fails; G1 replaces it.

**G2 (67) failed its own positive control, and its 188.56 px is void.** Planting
a 40 px ramp changed the measured excursion by **-0.19 px**. `68` diagnosed it:
**32.83%** of the analysis window's border is dark class, so the windowed
centroid is pinned by the window rather than by the subject. That is the fourth
control this milestone whose required geometry was absent where I put it. The
repair works — of 1595 dark components exactly one exceeds 2000 px and touches
no border, and its centroid moved **38.02 px** for a planted 40.

**H1 (68) fired its registered falsifier.** Tiling the ROI 4x6 and correlating
frame 0 against frame 298, **0 of 24** tiles returned a non-zero shift, while
`C-SCALE` — a planted 1.010 magnification, which is the focus-breathing
hypothesis that would reconcile all three instruments — was recovered as
**0.00901 with R-squared 0.9904**. The cube is unaligned raw
(`04-through-focus.py` calls `L.read_planes(p, BOX)` at a fixed box), so this is
a measurement of the raw frames, not of an aligned product.

**J1 (69) then failed, and I withdraw the claim.** I registered that "no image
motion in `ROI_LEG`" would be established only if, across five frame pairs, at
least 80% of tiles returned zero as-is *and* at least 80% recovered a planted
(5, -7). Four pairs passed. The pair 140 against 160 recovered the plant in only
**15 of 24** tiles and returned two spurious non-zero shifts as-is. The bar was
registered, it failed, and the claim does not stand as registered. What remains
is weaker and worth stating exactly: the four pairs that actually span the sweep
all returned 23 or 24 of 24 tiles at exactly zero, and the failing pair is the
one with the *smallest* expected motion, failing by spurious locks rather than
by any coherent shift. That is suggestive and it is not established.

**J2 (69)**, the repaired centroid, gives **9.44 px** peak-to-peak — but it
could be tracked in only **9 of 299** frames, because the component must stay
border-free and overlapping. Nine frames is not a sweep. I report it as
corroborating and not as deciding.

The reason this is a small matter rather than a large one was registered in
advance as G3. §66's D2 measured the band at **+0.2282 (d = 6)** unaligned and
**+0.2651 (d = 7)** after applying the warpmap's 70.97 px. Either the true drift
is ~71 px and the band survived alignment, or it is ~0 and the band survived
being deliberately misregistered by 71 px. **Both readings exclude drift.**

### 25.6 The chromaticity arm, re-run on data that is actually linear

§64's convexity test passed on `bee3-full.tif`, and `66`'s `C-LINEAR-2` then
showed that file is not linear: binned medians against linear raw DN give
R-squared **0.9612** with a quadratic term worth **63.8%** of the fitted range,
consistent with a gamma encode. A convex blend is convex *in linear light*, so
that PASS was testing the wrong proposition and does not stand.

`67` re-ran it on `ship-before-linear.tif`, the same merge at the same geometry
in linear RGB. The registered precondition was R-squared above 0.999 **and**
curvature below 0.01; it returned **0.992787** and **0.00694**. The curvature
clause passes with room and the R-squared clause fails. I judge the curvature
clause load-bearing and the R-squared shortfall to be scatter rather than bend —
the same test on `bee3-full.tif` gives 92x more curvature — but that judgement
is post-hoc and I mark it as such.

| population | r | b | linear G |
| --- | --- | --- | --- |
| deep subject | 0.358601 | 0.300083 | 1457 |
| halo band, d in 2 to 20 | 0.322687 | 0.343316 | 12975 |
| far background | 0.318767 | 0.346940 | 16646 |

The band lies **91.38%** of the way from subject to background along the
segment, with a perpendicular offset of **0.01039** of segment length against a
`C-CHROMA-NULL` of **0.00113**. Registered bar: perpendicular below 0.05 and
below `max(3 x null, 0.05)`. **PASS.** The scalar convex bound also holds, the
band sitting between the two layers at 22.05% below far background.

The nuance matters for M107. The offset is 1.04% of the segment, which is small
in absolute terms and **9.2x the measurement floor**. So the bee rim is
overwhelmingly a two-layer mixture, and there is a small, statistically
resolvable chromatic residue that a demosaic artifact could inhabit. I am not
claiming it does.

### 25.7 The registered prediction that was worth more than a pass

`69` asked the question that decides whether this is my defect at all: is the
near-edge structure in the data, or does the election make it? I registered an
overshoot statistic `O`, comparing the profile at d in 12 to 22 against the
shoulder at 30 to 45, normalised by the far level, and predicted `O(merge) > 0`
and above every single frame.

The first clause **failed**.

| image | O |
| --- | --- |
| gate-0 merge | -0.004852 |
| single frames, mean and sd | -0.112036 and 0.020821 |
| least-dipped single frame (144) | -0.077058 |
| most-dipped single frame | -0.158102 |
| uniformly random per-pixel election | -0.112367 |

Zero of 299 frames are positive. The merge does not add a bump; it **flattens**
one. And the random election sits dead inside the single-frame range, so a
per-pixel mixture as such does nothing.

`70` measured the physical quantity `O` was standing in for — how far the band
sits below unveiled background:

| image | veil depth V over d in 2 to 22 |
| --- | --- |
| gate-0 merge | -6.6810% |
| single frames, mean and sd | -26.4668% and 3.0076% |
| least veiled single frame (155) | -20.2495% |
| most veiled single frame (69) | -29.9956% |
| uniformly random per-pixel election | -25.8547% |

**The merge is the least veiled image in the set, 4.51 single-frame standard
deviations above the best single frame, and the election removes 74.76% of the
mean single-frame veil.** `C-RANDV` lands inside the single-frame range.
Registered bar K1: **PASS**.

So the mechanism claim is restated, and this is the form I want carried:

> **The halo is not the presence of extra light. It is the absence of the
> veil's darkening.** Two-layer physics puts a radial gradient beside every
> occluding edge in every observation; the election, being a max-like operator
> on brightness in the veiled band, erases three quarters of it; the eye reads a
> flat band abutting a falling gradient, with a hard lobed outer boundary, as a
> glow.

That reframing came from a registered prediction failing, not from inspecting
the data first, and it explains every earlier anomaly at once: why the frozen
band-profile instrument reads +0.280% (there is no bump to find), why the rank
statistic reads 0.87 (electing near-maximal samples is exactly what flattening
requires), and why a baseline-difference metric was structurally unable to see
the artifact.

`70`'s K2 arm failed and its control declared it void: the median elected index
against distance steps by only **+5.0 frames** over a **51 px** transition, and
the shuffled field gives **+5.0** over **53 px**. The statistic is dominated by
the card pixels that elect the card-sharp frame at every distance. That is why
the *difference* `dR` of 25.3, and not the raw statistic, was necessary.

### 25.8 The instrument this milestone should have had: E(d)

Plotting what I had already tabulated showed `O` was placed wrong. The merge's
profile has a local maximum near d = 17 and a local minimum near d = 27, so the
30-to-45 shoulder sits on the far side of the crossover and the two effects
partly cancel. Registration protects against choosing the answer; it does not
protect against choosing the wrong window. The figure caught it, which is the
argument for plotting a thing you have already put in a table.

`71-ensemble-E.py` replaces the baseline with the frame ensemble:

```
E(d) = [ merge(d) - mean_k frame_k(d) ] / far_level
```

Each frame is a legitimate observation of the same scene through the same optics
carrying the same veil, so their mean is what an ordinary image of this scene
looks like at distance `d`. No far window, no assumption that any distance is
artifact-free, and an exact structural null: any per-pixel rule that ignores the
boundary must give `E` near zero.

All four registered arms passed.

| arm | result |
| --- | --- |
| L1 shape | peak **+0.14393 at d = 13**, exactly one sign change, crossing at **d = 32**, trough **-0.07961 at d = 92**. PASS |
| L4 width | half-maximum from **d = 2 to d = 19**, FWHM **18 px** |
| L2 C-FRAME-E | single frames peak at **+0.03572 sd 0.03639**, max **+0.10115** (frame 166); merge is **1.42x** the most halo-like single frame and **3.0 sd** above the single-frame mean. PASS |
| L3 C-RANDE | random per-pixel election peaks at **+0.01444**, an order of magnitude below the single-frame floor. Control OK |

`C:\dev\strehl-out\M87-bee\71-E.png` plots it. The band is not a peak, it is a
**box**: flat at +0.13 to +0.14 from d = 3 to d = 19, then a cliff to zero by
d = 32, then a negative shelf reaching -0.08 at d = 92. That is the visible
artifact — a nearly uniform bright band with a hard lobed outer edge and
darker background beyond it — measured.

Note that L2's ratio is **1.42x**, not the 79x of §2. The two are different
claims and both are correct: §2's 79x compares an ISO halo metric between the
merge and the worst single frame, and 1.42x compares the ensemble-referenced
band amplitude against the *most halo-like* frame in the stack. A modest ratio
against the strongest frame, with the random election ten times below the
single-frame floor, is the honest form of "no single frame contains this band".

### 25.9 What this changes for the annulus milestone

The design constraint is now measured on both subject classes with two
independent statistics, and they do not agree on where to act:

| quantity | bee legs (judged image) | flower bud (§24) |
| --- | --- | --- |
| election anomaly dR peak | d = 6 | d = 7 |
| dR reach | 21 px | ~20 px |
| brightness excess E peak | d = 13 | not measured |
| E half-maximum span | d = 2 to 19 | not measured |
| median inner distance of the subject | 26.08 px | 106.00 px |
| fraction of a 20 px annulus that is real subject | 40.50% | 9.81% |

Four consequences, in order of how much they constrain the build.

1. **The election anomaly and its photometric consequence peak at different
   distances — 6 and 13.** A fix keyed on where the election is wrong will
   under-treat where the brightness error is largest. Near the silhouette every
   frame is heavily veiled, so even the elected sample is dark and `E` is small
   while `R` is extreme; further out the veil retracts in some frames, so
   electing the maximum produces a large excess. Both need treating and they are
   not the same annulus.
2. **Gate on the depth step as a threshold at `|dk| >= 60`, not as a scale.**
   Below 3 frames there is measurably no band at all.
3. **The geometry does not transfer, and this is the main risk.** A 20 px
   annulus touches **4.13x** more real subject on a bee leg than on the bud. The
   fix must demonstrate on the real bee at full frame that the abdomen hair
   fringe and the eye facets survive, which is exactly where §16.9's version
   failed.
4. **The fidelity term must be band-resolved.** Per M104's discipline 643 and
   §23's `BMF`, a band-averaged fidelity number will dilute precisely the
   damage worth detecting. `E(d)` is a suppression statistic and by bar X4's
   lesson it cannot certify a reconstruction on its own; it goes in paired with
   `BMF`, never alone.

### 25.10 Scoreboard for this section

Registered and **passed**: G1, K1, L1, L2, L3, L4, X1-LINEAR, `C-RANDK`,
`C-SCALE`, `C-RANDV`, `C-RANDE`, `C-CHROMA-NULL`, D3's placebo clause, and the
`band_profile` self-check at exactly zero deviation.

Registered and **failed**, stated as registered rather than repaired after the
fact: `C-BROKEN` (invalid geometry), P1 (the tilt is not photometric), P3 and D3
(no monotone ladder), R1 and F1 (resolved, and my prediction of the trend
direction was backwards), G2 (its own positive control was dead), H1's radial
model, H3's monotonicity, J1 (claim withdrawn), J3's first clause, and K2 (void
under its own shuffle).

That is five instruments of my own that this section broke or discarded. The two
results I would keep if I could keep only two are that **the election removes
74.76% of the veil that every observation carries**, which is the mechanism, and
that **a registered statistic can be placed on the wrong window and only a
picture will tell you**, which is the method.


---

## 26. The two mechanism questions: is the model dead, and is the veil one thing or two?

The orchestrator asked two questions and explicitly excluded a third: **do not
re-verify my own correction.** Nothing below scores the shipped fix.

**Q1.** My header rules out three explanations for the halo — not the gate
(present at `--gate 0`), not misregistration (6.6% observed against 91.7%
predicted), not two depths at the edge (§13's unmix reached −28.2% against a
−50% bar). Three kills and no surviving mechanism. An external reviewer named
two-layer bimodal unmixing as the headline unbuilt idea in this project, so the
question is whether −28.2% refuted the **model** or one **implementation**.

**Q2.** In the uncorrected render there is a bright soft veil at the silhouette
and a darker band standing off from it. The orchestrator has **argued** these
are two things and never measured it.

### 26.1 The premise I was given, and the one I gave myself, were both wrong

`13-unmix.py:98` reads `kF = int(np.bincount(argbest[mask]).argmax())` — a single
global scalar for the whole foreground. I registered an ablation ladder on the
belief that this scalar produced the −28.2%. Then I read §5.2 of this report at
source. **It does not.** The global scalar produced **−3.74%**; the −28.2% is
*already* the per-pixel `k_F` arm. My preregistration compared the oracle against
the wrong baseline, and I amended it to compare against the per-pixel arm —
recorded in the script header, before any arm number existed, with the original
comparison still reported. P90.

A second premise had to be repaired before anything could be measured. The plant
in `16-plant.py` puts its foreground at **one depth**, `KF = 40`. On that plant a
global scalar `k_F` is *correct by construction*, so the failure mode I wanted to
test **cannot occur there**. Running the ladder on it would have returned "no
effect" for entirely the wrong reason — the fifth control-with-absent-geometry
of this milestone, and this time caught before running rather than after. §72
therefore builds a **depth-spread** variant, the foreground split into six
horizontal stripes each at its own sharp frame, blurred separately and summed —
exact, because Gaussian filtering is linear and the stripes partition the matte —
and keeps the original flat plant as the **placebo where the ablation must show
nothing**.

Two incidental equivalence checks fell out and both passed. The rebuilt flat
plant reproduces `16-plant.json` to five significant figures (truth ISO 0.008566
against 0.00857, merge ISO 0.030598 against 0.03060), and its merge band RMSE
over d in [2, 40] reads **3.4617%** against §4.2's **0.0346** — an independent
reproduction of the load-bearing table's merge row. Arms D and E, which differ
only in whether `alpha` is modelled from true inputs or taken from the plant's
own generator, agree to **0.0%** on both plants, so the ladder's machinery is
exact.

`C-CAP` **failed as registered** on both plants (truth ISO 0.00857 against a
≤ 0.005 bar). That is not new: §4.1 already discloses this plant missing the
truth floor and passing on separation instead. The failure reproduces a known,
disclosed state rather than revealing a new one.

### 26.2 Q1 answered: the fit reaches the floor; the propagation is everything

Scored on **band RMSE against the known unveiled background** — fidelity, never
suppression, because bar X4 measured three of four deliberately broken unmixings
*improving* the halo metric by 77–85%. The treated band is identical across all
arms by construction.

**MEASURED**, depth-spread plant, headroom = merge RMSE 4.5271% down to the
far-field single-frame noise floor 1.7999%:

| arm | what is oracle | band RMSE | headroom captured |
| --- | --- | --- | --- |
| A shipped | nothing; **global scalar `k_F`** | 12.6769% | **−298.83%** |
| B | per-pixel **`k_F` map** | 1.8270% | **+99.00%** |
| C | blur constant `c` only | 12.8677% | −305.82% |
| D | matte, `k_F` and `c` | 1.7836% | +100.60% |
| E | the **true `alpha_k` cube** | 1.7837% | **+100.59%** |
| X | *registered broken arm*, `alpha` to `1 − alpha` | 67.0615% | **−2292.92%** |

And the placebo, where the occluder is at one depth:

| arm | band RMSE | headroom captured |
| --- | --- | --- |
| A shipped, global scalar `k_F` | 1.8225% | **+99.03%** |
| B per-pixel `k_F` map | 2.4215% | **+73.32%** |
| E oracle alpha | 1.8186% | +99.19% |
| X *registered broken arm* | 66.9920% | **−2698.00%** |

**The two-component fit is not the limiter.** Handed the true `alpha_k` cube it
captures **100.59%** of the available headroom — it exceeds 100% because the
intercept is estimated across 121 frames and is quieter than any single one.
**The two-layer model is not refuted, and the reviewer's proposal is still
live.** P83.

**`k_F` propagation is the entire difference between catastrophe and the floor.**
Global scalar against per-pixel map is a **+397.83 point** swing on a
depth-spread occluder, where the scalar is not merely insufficient but makes the
band **2.8x worse than the uncorrected merge**. On the flat placebo the same
substitution **costs 25.71 points**. So per-pixel `k_F` is not an unconditional
improvement: on a single-depth occluder the map estimated from the winner field
is noise. P84.

**Once `k_F` is per-pixel, the alpha model has nothing left in it** — oracle
alpha buys **+1.59 points** over the per-pixel arm, and oracle `c` alone buys
**0.00** (arms A and C agree to four decimals). Refining `sigma_k = c|k − k_F|`
is worth 1.59 points; resolving `k_F` is worth 397.83. P85.

The honest residue, and I am not claiming to have identified it: on the plant
per-pixel `k_F` reaches **+99.00%**, and on the real bee the same idea reached
**−28.2%**. A third limiter exists that the plant does not contain. §5.2's ranked
candidates — semi-transparent hair fringe, non-constant `F(x)`, no alignment —
are still the candidates, and naming it is an experiment, not a conclusion.

### 26.3 My own registered rule fired the wrong answer

Bar N2 said: *if oracle arm E improves at least 2x more than arm B, the fit is
not the limiter.* It measured **E/B = 1.02x** and printed

> `N2 -> THE FIT IS THE CEILING: step 13 refutes the MODEL`

which is the opposite of the truth. The rule compares two arms **to each other**,
and "E is no better than B" is equally consistent with both stalling and both
being finished. Here B had **already reached the floor**. A rule that reads
"already perfect" as "refuted" is a defect in the rule.

The correction is `74-adjudicate.py`, which rescores every arm as the fraction of
headroom captured against the far-field noise floor. **The registered output is
left standing** in §72's stdout and JSON rather than repaired in place, the same
handling §15.4 got when fact 1295 invalidated it. P86.

The general form: **score arms against an achievable floor, not against each
other.** A ratio between two arms is uninterpretable until you know where the
ceiling is.

### 26.4 Q2 answered: two mechanisms, and only one of them is the election's fault

The instrument that found the shelf cannot test what the shelf is.
`E(d) = [image(d) − mean_k frame_k(d)] / far` is a difference against the
ensemble of the very frames the election chooses from, so **anything present in
every frame cancels out of it**. A fixed per-pixel gain scales every `k` at a
pixel by the same constant, leaving `argmax_k` **exactly** unchanged, and both
the merge and the ensemble move together. So `E` measures only what the
*election* does, and the hypothesis "there is something real out there" is
precisely the one it cannot address.

`C-E-BLIND` measures this instead of asserting it: a −3% annulus planted into all
299 frames over d in [30, 70], disjoint from the far window so the normaliser is
untouched, moves `E` by **1.67%** of the plant. A bin-constancy check confirms
the plant is exactly multiplicative within a distance bin (max deviation
**0.0001 DN**).

**The first version of that control read 56.65% and declared my argument wrong.**
It was the control that was wrong: it built the planted baseline as the profile
*of the mean image* while the true `E` uses the mean *of the profiles*, and
median and mean do not commute. Fifth self-caught instrument defect of this
milestone, and the first where the control was wrong and the claim was right.
P89.

**(a) The election component, and it is one mechanism with two signs.** Rolling
the elected-index field by (317, 511) — which preserves the marginal
distribution of elected depths exactly, verified, with only 0.377% of pixels
keeping their index — collapses both features:

| feature | `E` true | `E` rolled | survives |
| --- | --- | --- | --- |
| positive box, d = 13 | +0.14393 | +0.05627 | 39.1% |
| negative shelf, d = 92 | −0.07961 | +0.00613 | **7.7%** |

Both are boundary-registered election behaviour. The shelf is if anything *more*
registered than the box. The box's 39.1% residue is the elected-depth
distribution alone, against §71's uniformly-random election at +0.01444 — so
about three fifths of the bright band is boundary registration and two fifths is
which depths get elected at all.

**(b) A real frame-borne veil, which the election cannot be blamed for.** A
second instrument, on the **ensemble** rather than the merge: at fixed distance,
regress level on **local occluder coverage**. Holding distance fixed removes the
radial profile, which is the confound that defeated three earlier baselines here.

**MEASURED**, median over d in [40, 120]:

| coverage radius | within-bin coverage sd | slope, per unit coverage | rolled-coverage null | planted 3% recovered | observable amplitude |
| --- | --- | --- | --- | --- | --- |
| 48 px | 0.0075 | +1.36462 | −0.04396 (3.2%) | 101.6% | +1.029% |
| **128 px** | 0.0534 | +0.53420 | −0.03981 (7.5%) | **100.6%** | **+2.852%** |

Both radii agree in sign and both recover a planted coverage-proportional 3%
gain to within 2%. The observable amplitude is the slope times the coverage
variation that **actually exists** at these distances, not the slope
extrapolated to full coverage, which is far outside the data.

`C-V-NULL` **failed the threshold I registered** (|null| ≤ 0.005) and passes a
scale-free restatement (|null| ≤ 10% of the reading, at 7.5%). The registered
number was written for a ratio-scaled instrument and does not transfer to a
slope-scaled one — I rebuilt the instrument mid-experiment because the original
split each distance bin at its median coverage, and median coverage over the
valid background is **0.0049**, so it was separating near-zero from near-zero.
**The rescaling is legitimate; treating the old absolute threshold as satisfied
would not be, so both readings are reported and the amendment is marked
post-hoc**, exactly as `X1-LINEAR`'s curvature clause was.

**The verdict: two mechanisms, and the orchestrator's argued split is
confirmed.** The election-created shelf is **7.961%** of level; the frame-borne
veil is **2.852%**. Ratio **0.358**. So the correction is aimed at the dominant
term — but a **real veil of roughly 2.9% remains that no selector-side fix can
reach**, because it is in every observation. P88.

That is the link back to Q1. The residue that selection can never remove is
exactly what a two-layer reconstruction removes, and §26.2 measures that the
reconstruction reaches the noise floor when its `k_F` is resolved.

### 26.5 What bar X4 asked for, and whether it works

The orchestrator required a fidelity term registered alongside any suppression
number, because three of four deliberately broken unmixings improved the halo
metric by 77–85%. The registered broken arm captures **−2698%** and **−2293%**
of the headroom on the two plants. **Fidelity against truth rejects
destruction.**

The limit of that claim, stated because it is a limit: on these plants the broken
arm also fails the *suppression* metric (−265.2% and −235.3%). The plant does not
reproduce X4's dissociation, so this shows the fidelity instrument is sound — not
that the two metrics disagree here.

### 26.6 What §26 broke of its own

Registered and **failed**: `C-CAP` on both plants (reproducing a disclosed known
state), N2's decision rule (fired the wrong answer and is corrected in §74, not
repaired in place), `C-V-NULL`'s absolute threshold (instrument rescaled
mid-experiment; both readings reported, amendment marked post-hoc), and the first
`C-E-BLIND`, which was wrong where the claim was right.

Registered and **passed**: N1's placebo (0.2% gap where the ablation must show
nothing), N3's broken arm on both plants, `C-DE`'s machinery check at 0.0% on
both plants, `C-ROLL`'s marginal preservation, the repaired `C-E-BLIND` at 1.67%,
and `C-V-POS` at 100.6%.

Two premises were corrected before they could do damage — the orchestrator's and
mine about which arm produced −28.2%, and my own about whether the plant could
express the failure it was built to test. Both were caught by reading the source
rather than the summary.

## 27. The photometric-step hypothesis: refuted for the veil, confirmed for the shelf

**Asked by the orchestrator**, off the back of a `flowers-cpl` measurement:
`--gate 0` renders hard-edged polygonal patchwork in a smooth defocused petal,
because adjacent low-texture pixels elect frames that disagree photometrically
and every winner-field boundary becomes a visible step. Applied to a silhouette,
where the winner field must jump between two frame indices far apart on the
focus axis, that predicts a **signed** step — bright on one side, dark on the
other — which would make §26.4's "two mechanisms" a **single mechanism with a
sign change**. Three measurements were offered; the orchestrator asked me either
to name the measurement that already excludes this, or to take the third.

**Answer, and it splits: the mechanism is REFUTED for the bright veil and
CONFIRMED for the dark shelf. The orchestrator is right that my kills did not
exclude it, and right about the shelf specifically. §26.4 and §21 are both
corrected below.**

### 27.1 First, the concession: none of my three kills excludes this

I am not going to defend the kills. The orchestrator's reading of them is
correct and one of my published sentences is weaker than I wrote it.

§26.4 concluded that both the box and the shelf are "boundary-registered
election behaviour", on the strength of `W1`: rolling the elected-index field by
(317, 511) leaves 39.1% of the box and 7.7% of the shelf. **That control cannot
discriminate the hypothesis under test.** A roll is a **rigid translation**, so
it preserves every local index gradient `\|k_left − k_right\|` *exactly* — the
steps still exist afterwards, in the same number and the same magnitude, merely
relocated off the silhouette. A photometric-step artifact is therefore *also*
boundary-registered and *also* collapses under the roll. `W1` separates
boundary-registered from boundary-independent, which is what it was built for.
§26.4 used it to separate two boundary-registered *causes*, which it cannot do.
That is `P94`, and it is a defect in my reasoning, not in the control.

The same goes for the other two. "Not the gate" is consistent with a
photometric step, which is present at `--gate 0`. "Not misregistration" is
consistent with it, since alignment cannot fix a photometric step between
correctly registered frames. The orchestrator anticipated both.

**One thing is already excluded and it is worth naming precisely.** The
frame-borne component `V` (+2.852% of level, §26.4) is measured on the
**ensemble mean**, which elects nothing. No property of the election can appear
there. So `V` is safe; the box and the shelf were both live.

### 27.2 What was registered, before anything was run

`src/75-photometric.py`, `src/76-photometric-audit.py`, `src/77-decompose.py`
and `src/78-invariance.py` each carry their preregistration in the module
docstring. In outline:

| id | test | registered decision |
|---|---|---|
| D1 | drift magnitude, and the spread between the frames *actually elected* | below 25% of the box means drift cannot account for it |
| C-D1-POS | plant a ±4% per-frame ramp | must recover to within 10% relative |
| D2 | veil amplitude against local winner-field index gap | mechanism predicts positive ρ; rolled-gap null |
| D3 | normalise gain and offset, **re-elect**, re-merge, recompute `E(d)` | ≥75% survival refutes; ≤25% confirms |
| C-D3-POS | plant a ±10% ramp | must (a) move `E` detectably and (b) be ≥50% removed by normalisation |
| A1 | true exposure = per-frame **mean level** (blur conserves the mean) | the number I quote |
| A3 | **level-only**, focus-neutral normalisation | same 75%/25% thresholds |
| A4 | shuffled normaliser: perturbs the election, corrects nothing | ≥50% of the fitted arm's effect means perturbation |
| B1/B2 | 2×2 holding election and composite fixed one at a time | share >0.60 names the driver |
| C-ID | cell 00 must reproduce the cached `E(d)` | hard abort |
| C-INV | global rescale of every frame must leave `E` unchanged | ≤1e-9 |

`C-D3-POS` is the arm that makes the rest readable, and it exists because bar
`X4` already caught this milestone shipping a suppression number with no
fidelity term. A null from a normaliser never shown to remove a *known* step is
worth nothing.

### 27.3 There is real drift, and my first instrument mismeasured it by 6.3×

`75`'s D1 fitted a per-frame gain and offset by regressing each frame on the
ensemble reference over `d ≥ 140`, and reported:

| quantity | `75`'s covariance fit | `76`'s mean level |
|---|---|---|
| peak-to-peak | **109.671%** | **17.339%** |
| offset swing | 4036.31 DN on a 3747 DN level | — |
| standard deviation | 0.27496 in gain | 5.034% of level |

**No camera drifts by 110% across a focus sweep.** That regression measures
**contrast**, not exposure: a frame whose background is defocused has its
structure smoothed away, so its covariance with a sharp reference collapses and
the fitted gain reads low. In a focus stack, at any radius, the background's
focus is exactly what is changing. Convolution conserves the mean, so per-frame
**mean level** is the estimator that is neutral to defocus, and it reads
**17.339% p-p** — and that is still an *upper* bound, because it also contains
focus breathing and foreground blur spill.

**The corroboration I did not plan.** §21.5's far-background probe, cut at
`> 60` px rather than `≥ 140` px and written for a different purpose, reported
total peak-to-peak of **17.83%**. Two independent regions, two independent
scripts, 17.34% against 17.83%. The level estimator reproduces; the covariance
one does not.

**`C-D1-POS` passed and was blind to this.** A planted ±4% ramp was recovered
with a maximum relative error of **0.000%** — because a covariance fit recovers
a multiplicative plant perfectly whether or not it *also* carries a focus term.
The control bounded the estimator's **sensitivity** and said nothing about its
**specificity**. That is `P96`, and it is the same shape as `P82`.

**My registered A2 rule did not catch it either.** A2 was to declare the fit
confounded if `|ρ(g, focus)| > |ρ(g, level)|`. Measured: **ρ(g, level) =
+0.7485** against **ρ(g, focus) = +0.7084**. By the letter the fit is
level-driven and the 109.671% "stands" — which is wrong, and it is wrong because
in a focus stack level and focus co-vary, so the rule is comparing two
near-equal correlations and cannot resolve them. **A1's direct measurement is
what refutes the number, not A2.** I report the rule as under-powered and the
figure as withdrawn.

### 27.4 The box: three arms and a passing positive control, all against the mechanism

**Arm one — is there enough drift to do the job?** The most a photometric step
can deliver is the brightness difference between the frames *actually elected*.

| quantity | value |
|---|---|
| elected-frame level, band `d ∈ [2,22]` | 0.98670 of the sweep mean |
| elected-frame level, far field `d ∈ [80,120]` | 0.99409 |
| **excess at the band** | **−0.7424%** |
| `E`'s box amplitude | +14.393% |
| **share of the box that drift can supply** | **5.16%, a 19× shortfall** |

It is not merely too small. **It is the wrong sign** — the frames elected at the
band are *darker* than those elected far away, in a band that is *brighter*.

**Arm two — normalise and re-elect, the orchestrator's measurement (3).**

| arm | box at `d = 13` | survives | election agreement |
|---|---|---|---|
| shipped merge | +0.14393 | — | — |
| gain + offset normalised | +0.14713 | **102.22%** | 70.329% |
| **level-only, focus-neutral** | **+0.16741** | **116.32%** | 89.292% |

Not only does the box survive explicit per-frame photometric normalisation, the
focus-neutral version of it makes the box **16.3% larger**. Correcting exposure
makes this artifact worse.

**Arm three — the positive control, which is what licenses reading arms one and
two as nulls.** Planting a ±10% per-frame ramp — several times the true drift —
and re-electing:

| quantity | value |
|---|---|
| box with the planted ramp | +0.17301 |
| **movement caused by the plant** | **+0.02908** (detectable ✓) |
| box after normalising the planted cube | +0.14713 |
| **planted movement removed by normalisation** | **+0.02588 = 89.0%** (≥50% ✓) |

**The instrument demonstrably removes a photometric step of exactly the proposed
kind. It finds none in the box.** Registered verdict: **refuted**, at 102.22%
against a 75% bar.

### 27.5 The 2×2: hold one factor at a time

Normalising frames does two things at once — it changes what is composited and
it changes what the election picks (10.708% of pixels moved even under the
gentle level-only arm). Only the first is the orchestrator's mechanism. `77`
runs all four cells: elect from {original, normalised} × composite from
{original, normalised}.

| cell | elect | composite | box `d=13` | shelf `d=92` |
|---|---|---|---|---|
| 00 | original | original | +0.14393 | −0.07961 |
| 10 | original | **normalised** | **+0.16731** | **−0.05379** |
| 01 | **normalised** | original | +0.14400 | −0.08433 |
| 11 | normalised | normalised | +0.16741 | −0.04949 |

Cell 10 is the clean statement of the mechanism: the winner field is **fixed
bit-for-bit** and only the pixel values change.

- **Box.** Photometry alone moves it from +0.14393 to +0.16731, a **16.24%
  increase**. Election alone moves it by **+0.05%** of its own value — nothing.
  The box is inert to both, and made worse by the one under test.
- **Shelf.** Photometry alone removes **32.44%** of it. Election alone makes it
  **5.93% deeper**. Together they remove 37.84%, with a +29.9% interaction.

**My registered share statistic named the wrong winner for the box and I am
reporting it as a defect.** B1/B3 computes `(E00 − E10) / (E00 − E11)`; for the
box that is `(−0.02338)/(−0.02348) = +99.6%`, and the script duly printed
`driver: PHOTOMETRY (ORCH's mechanism)` — for a change that is a 16.24%
**increase**. The rule apportions a change without ever asking whether the
change is a *reduction*, so a ratio of two negatives reads positive and
certifies the mechanism its own operands most cleanly refute. That is `P95`. The
verdict line in `77`'s output is wrong as printed and the cell values above are
what stand.

### 27.6 The shelf: the orchestrator is right, and this corrects §21 and §26.4

Three arms agree, and they are not the same arm restated:

| arm | shelf at `d = 92` | survives | election agreement |
|---|---|---|---|
| shipped merge | −0.07961 | — | — |
| gain + offset normalised, re-elected | −0.03642 | 45.74% | 70.329% |
| level-only normalised, re-elected | −0.04949 | 62.16% | 89.292% |
| **photometry alone, election frozen** | **−0.05379** | **67.56%** | **100%** |
| shuffled normaliser (corrects nothing) | −0.12395 | **155.69%** | 35.089% |

The last row is the control that settles it. `A4` divides frame `k` by the
fitted gain of a *randomly permuted* frame — the same magnitude of disturbance,
correcting nothing. It perturbs the election far harder (35.089% agreement
against 70.329%) and it moves the shelf **the other way**, making it 55.7%
**deeper**. Perturbation deepens; correction shallows. Opposite signs.

**My registered A4 rule was written for the wrong failure mode.** It tested
*magnitude* — "if the shuffled arm reproduces ≥50% of the fitted arm's
reduction, the effect is perturbation" — on the assumption that perturbation
would push the same direction. It computed −102.6% and returned "photometric",
which is the right answer reached by a rule that could not have distinguished
the interesting case. **The sign is what settles it, and I did not register the
sign.**

**This corrects §26.4.** I wrote that both features are boundary-registered
election behaviour. That over-attributes the shelf: **a third of the shelf
survives the election being held bit-for-bit constant** and is carried by the
frames' own levels. The orchestrator's mechanism is real, at the location it
predicted, with the sign it predicted.

**And it corrects §21, which is the more serious of the two.** §21 concluded
"the photometric share is zero or negative; the optical share is all of it",
from a λ-ladder on the ISO halo metric. That conclusion is sound for the box and
**structurally unmeasurable for the shelf**, because of what ISO is:
`m87lib.halo_from_profile` takes its peak over `D_NEAR = (1, 24)` — the box —
after subtracting a **linear baseline fitted over `D_FAR = (48, 96)`**. The
shelf's trough is at **`d = 92`, inside that fit window**. ISO does not
under-weight the shelf; **it absorbs the shelf into its own baseline**, where a
shelf effect tilts the normaliser instead of registering as signal. `D_MAX = 96`
means the standard profile does not even reach past the shelf. §21's null was
measured with an instrument that cannot express the effect. That is `P93`, and
it is the reason this result went eighteen sections unfound.

### 27.7 The index-gap prediction, with distance partialled out

The orchestrator's measurement (2): a photometric step should grow with
`\|k_left − k_right\|`; veiling need not.

| statistic | value |
|---|---|
| Spearman ρ(excess, gap) over the whole band | **−0.1180** |
| rolled-gap null | +0.0660 |
| **pooled within-distance ρ** | **−0.0800** |
| rolled-gap null, pooled | +0.0713 |

The raw correlation is confounded, because inside `d ∈ [2,22]` both the excess
and the gap vary with `d` — which is why the null read +0.0660 rather than zero.
Recomputing Spearman **within each 1 px distance bin** and pooling by count
removes distance as a driver, and the answer is unchanged in sign: **−0.0800
against a +0.0713 null**. Negative where the mechanism predicts positive. This
agrees in direction with §65's finding that `\|Δk\|` acts as a **threshold, not
a gradient**, and it is now measured on raw amplitude rather than on a rank
statistic that a per-frame gain could itself disturb.

### 27.8 `C-INV` failed as registered, and the diagnosis is arithmetic

`E` is a ratio to the far-field level, so multiplying every frame by a constant
must leave it exactly unchanged. `77` measured **2.768e-09** against a
registered **1e-9** bar. **The bar failed.** `78` diagnoses it rather than waves
at it, on the principle that a leak cannot know whether a scale factor is
binary-exact:

| factor | representable in binary? | max `\|dE\|` over all `d` | at box and shelf |
|---|---|---|---|
| ×0.5 | yes | **0.000e+00** | **0.000e+00** |
| ×2.0 | yes | **0.000e+00** | **0.000e+00** |
| ×4.0 | yes | **0.000e+00** | **0.000e+00** |
| ×1.37 | no | 9.586e-08 | 2.768e-09 |
| ×1.1 | no | 8.149e-08 | 2.406e-08 |
| ×3.7 | no | 4.899e-08 | 1.713e-08 |

**Every binary-exact factor reproduces `E` bit-for-bit.** Only factors that
round move it, and they move it by float32 epsilon (1.192e-07 relative, an
absolute floor of ~1.716e-08 on these values). `E` is invariant; the 1e-9
threshold was registered **below the arithmetic's own resolution**. The worst
deviation across every factor is 2.406e-08 against the smallest effect §27
reports (0.02348) — a factor of **9.8 × 10⁵**.

`78`'s own auxiliary clause also failed, and for the same reason: it required
inexact factors to stay under 1e-8 while the same script computes the float32
floor at 1.716e-08. I registered two thresholds below the noise floor. The
*mechanism* test — exact versus inexact — is what carries the diagnosis, and it
carries it cleanly.

`C-ID` passed exactly: cell 00 reproduces `76`'s baseline `E(d)` at **0.000e+00**
across every finite distance.

### 27.9 What this changes

1. **The bright veil is not a photometric step.** Refuted by three arms with a
   passing positive control, and exposure correction makes it *worse*. §26.4's
   attribution of the box to selection stands, now on a control that can
   actually discriminate.
2. **The dark shelf is at least a third photometric.** §26.4's attribution of it
   to the election is corrected, and §21's "photometric share is zero" is scoped
   to the box.
3. **The orchestrator's "single mechanism with a sign change" is half right, and
   it is the half I had wrong.** The two features are still two mechanisms — but
   not the two I named. The box is a selection artifact that photometry cannot
   touch. The shelf is a genuine composite of both.
4. **A correction that normalises per-frame level before the merge would help the
   shelf and hurt the veil.** That is a real design constraint on the annulus
   milestone: the two features must be treated separately, and any single global
   fix trades one against the other. It also means `--auto-exposure` and any
   per-frame photometric normalisation shipped elsewhere in the pipeline should
   expect to *increase* the measured near-edge halo while improving the far
   band, which is worth saying before someone reads that as a regression.
5. **Four registered rules failed or under-performed in one section** — A2
   under-powered, A4 written for the wrong failure mode, B1/B3 sign-blind, C-INV
   and `78`'s clause set below the arithmetic floor. None of the *conclusions*
   moved, because in each case a second instrument or a mechanism test settled
   it. That is the argument for redundancy, not for the rules.

## 28. The photometric step, measured on what is composited: real, and a tenth of it

**Item 3 withdrawn on the orchestrator's instruction** — M99 owns photometric
normalisation and has measured it. What remains is the hypothesis restated in
the form that does not run through the election: at a silhouette the winner
field jumps between two distant frame indices, and if those frames differ
photometrically the *rendered output* carries a signed step there, independent
of veiling and independent of the election being correct.

**M99 fact 22 makes that the right framing, and it strengthens §27 rather than
weakening it.** A gain propagated into the noise model is election-neutral by
construction — focus response is contrast over sigma, a gain scales both, so the
ratio is exactly invariant; measured at 0.001% against a 0.43-0.74% null. That
promotes §27.5's **cell 10** — election frozen bit-for-bit, composite normalised
— from an artificial control to **the arm that describes a correctly built
correction**. Cell 11, which re-elects, models an *incorrectly* propagated one
(M99's own `A3`/`N1` configuration, which moves 18-40% of the plane). So §27's
headline should be read on cell 10, where the box gets **16.24% worse** and the
shelf **32.44% better**.

**Answer: the mechanism is real and it supplies 9.98% of the rendered step at
the veil peak. Its sign predicts the step at 48.87% — below chance — while veil
geometry predicts it at 65.16%.**

### 28.1 The plant challenge, checked at source, where it had already been corrected

The orchestrator relayed fact 23 as: *any plant must be **monotone** in frame
index or it understates the effect by ~11×*, and asked whether any of my kills
used a non-monotone plant. **M99's own §12.3 has already corrected that wording,
and the correction matters to the answer.** The natural gain that enriched
20.64×/8.32× is *not* monotone — it is a single smooth hump rising to a maximum
at frame 103-120 and falling, `max/min = 1.1818`, endpoint ratio only 1.0380.
M99 restates the operative property as **smoothly ordered (low-frequency) in
frame index**; the pseudo-random plant under-performed because it was
*unordered*, not because it was non-monotone.

**On this cube, measured rather than inherited:**

| quantity | `bee-3-cpl` (M87) | M99 §12.3 |
|---|---|---|
| level peaks at frame | **103** | 103-120 |
| max/min | **1.1894** | 1.1818 |
| endpoint ratio | 1.1316 | 1.0380 |
| Spearman ρ against frame index | **−0.9289** | — |

Two independent milestones, different decks, different code, the same hump. This
deck is also strongly ordered end-to-end, which is why §21.5's early-decile bias
is negative — and M99 §12.3 says so explicitly and independently.

**So my plants satisfy the corrected criterion.** Every plant in §27 is a
`linspace` ramp, `|ρ| = 1` by construction, maximally ordered. None of the three
kills used an unordered plant.

### 28.2 But my plant was wrong for a reason neither of us had named

Ordering was not the problem. **Sign was.** The natural drift runs ρ = −0.9289;
my ramp runs ρ = +1.0000. Multiplying them **cancels**, so `g_real × ramp` has a
*smaller* spread than `g_real` alone: I planted a control that made the effect
it was testing for smaller.

| arm in `79` | slope | required |
|---|---|---|
| `C-POS-RAMP` planted ±10% ramp | **−1.7375** | ≈ 1 |
| `C-POS-HUMP` M99's hump shape | +0.8123 | ≈ 1 |

The ramp failed with the **wrong sign**; the hump, ordered the same way as the
drift, passed in the same run. **I voided `79`'s entire S2 verdict on that
control.** The fix is to plant onto a **drift-free base** — `luma[k] / g_real[k]`
with the election frozen — where there is nothing left to cancel against. That
is `P100`, and it is a plant-design rule I had not seen stated: a positive
control must be checked for **sign agreement with the signal already present**,
not only for magnitude and ordering.

### 28.3 The second defect: a regression that was fitting scene structure

`79` regressed the observed step between adjacent background pixels on the
predicted photometric step and got **R² = 0.0014**. That is not a weak effect,
it is a hopeless estimator: the step between two adjacent pixels is mostly the
*scene* changing, and a slope fitted through that is fitting noise.

The repair is a **paired difference**. Two composites that differ *only* in
per-frame gain, with the election frozen bit-for-bit, contain identical scene
content, so

```
D(p,q) = [with(p) - with(q)] - [without(p) - without(q)]
```

isolates the photometric contribution **exactly**. Scene, veil and election all
cancel. It is the per-pair form of §27.5's cell 10.

| control | slope | R² | sign agreement | bar |
|---|---|---|---|---|
| `C-EXACT` the real drift | **+0.9802** | **0.9681** | 97.94% | 0.90-1.10 ✓ |
| `C-POS-RAMP` on the drift-free base | +1.0026 | 0.9601 | 94.38% | ✓ |
| `C-POS-HUMP` on the drift-free base | +1.0017 | 0.9701 | 92.94% | ✓ |
| `C-NULL` shuffled frame→gain map | +0.0018 | 0.0001 | 55.06% | ±0.25 ✓ |

**All four pass.** R² goes from 0.0014 to 0.9681 on the same data and the same
question, and both plant shapes now recover at slope 1.00 — so the instrument is
not keyed to plant shape, which was the failure `79` exhibited.

### 28.4 The amplitude, which is the number that answers the question

49 986 adjacent background pairs in `d ∈ [2,40]` elected different frames
(14.22% of adjacencies); 13 402 sit at the veil peak.

| region | photometric part | observed step | share |
|---|---|---|---|
| whole band `d ∈ [2,40]` | 6.41 DN | 57.00 DN | **11.25%** |
| **veil peak `d ∈ [8,18]`** | **6.34 DN** | **63.50 DN** | **9.98%** |

Registered bar: under 25% is not the cause. **The photometric step is real,
exactly measured, and supplies about a tenth of the rendered step.** Note the
photometric part is essentially *constant* across the band (6.41 against 6.34
DN) while the observed step rises toward the silhouette — the extra step at the
veil is not photometric.

### 28.5 The head-to-head, which needs no model at all

The orchestrator's cleanest discriminator: a veiling mechanism has a **fixed
sign** set by which side occludes; a photometric step's sign is set by `g`.
Score both predictors on the same pairs.

| region | veil geometry | photometry |
|---|---|---|
| whole band | **68.87%** | 52.38% |
| **veil peak `d ∈ [8,18]`** | **65.16%** | **48.87%** |

**Photometry is below chance at the veil peak.** The gain difference between the
elected frames carries no usable sign information about the veil. Geometry —
simply "the pixel nearer the subject is brighter" — carries 65.16%.

### 28.6 The gap correlation, and a sign flip that is an interaction

The orchestrator asked for this on M96's disconnected competitive set, using
M96's definition verbatim (`t·√2·FOCUS_NOISE_SD`, `gap = (hi − lo + 1) − n > 0`).
It disagrees with §27.7, which read **−0.0800**. Both factors differ, so both
were varied:

| population | statistic | pooled ρ | rolled null |
|---|---|---|---|
| all band | M96 gap | −0.0221 | −0.1151 |
| all band | 5×5 winner range | −0.0876 | +0.0423 |
| **M96 disconnected** | **M96 gap** | **+0.1662** | +0.0547 |
| M96 disconnected | 5×5 winner range | −0.0045 | −0.0271 |

**Only one cell is positive, and it needs both factors.** Changing population
alone gives −0.0045; changing statistic alone gives −0.0221. So this is an
**interaction**, and §27.7's −0.0800 is superseded *for this question* by
+0.1662 on the population the orchestrator specified. The ladder there is
broadly increasing but **not monotone** — gap `[1,5)` +0.01330, `[5,20)`
**−0.00410**, `[20,60)` +0.06861, `[60,150)` +0.07841 — where the mechanism
predicts monotone.

**My script printed "the sign is carried by the POPULATION"**, by comparing
swing magnitudes and taking the larger. That is single-factor attribution over
an interaction, and it is the same error class as `P95`'s sign-blind share
statistic — the third time in two sections that a one-number attribution rule
has been inadequate here. The 2×2 is what stands; the label does not.

### 28.7 Discipline 674, audited against my own bars

**None is withdrawn, and here is the evidence rather than the assertion.** M87's
halo metric is a median **level** profile against distance from the subject — it
contains no gradient or Laplacian term. `P24` is the direct test: a Catmull-Rom
gather that destroys **~49% of gradient energy** moves the halo metric by
**+0.6%**. A metric that barely notices a halving of high-frequency energy is
not a sharpness proxy. The detail-retention and BMF bars in §16 and §23 are
**ratios against an untouched reference on identical content**, which is what
674 asks for.

### 28.8 Where this leaves the mechanism

1. **The orchestrator's mechanism is real, measurable and minor.** It exists, it
   is now isolated exactly rather than argued, and it accounts for ~10% of the
   rendered step at the silhouette. That is a *confirmation* at an amplitude
   that does not make it the cause.
2. **The veil is not it.** Photometry predicts the step's sign below chance
   where the veil is strongest; geometry predicts it at 65%.
3. **§26.4's split survives, with §27's amendment.** The box is selection, and a
   correct photometric correction makes it 16.24% *worse*. The shelf is about a
   third photometric. Neither is a single mechanism with a sign change.
4. **The design constraint for the annulus milestone is unchanged and now has a
   number:** ~10% of the silhouette step will be removed for free once M99's
   correction ships, and the remaining ~90% is what the annulus has to model.

### 28.9 What verifies this section, and what it cannot see

`verify_s28.py` re-derives **58 figures** from the JSON operands rather than
re-reading them: every percentage is recomputed from its full-precision
numerator and denominator, `max/min` and the drift's argmax are recomputed from
the 299 stored per-frame levels, and the 2×2's swings are recomputed from its
four cells. It also cross-checks the two runs against each other — `79` and `80`
must agree to 1e-12 on the drift ρ and on the disconnected-population ρ — and it
checks **every M99 figure quoted here against `M99-photometric.md` itself**, so a
misquotation of another milestone fails the build rather than propagating.

It caught three real defects on first run: a `77-decompose.json` schema I had
assumed rather than read, and — twice — a float32 quotient checked at a 1e-12
bar. **That is §27.8's own lesson, repeated by me in the harness written to
enforce it**, four sections after I recorded it. The bar now sits above float32
epsilon, where the arithmetic actually lives.

`control_s28.py` then plants seven known defects to establish the checker is not
merely agreeable. Each is anchored on a literal that must be found, and the
report is restored from a `%TEMP%` copy and confirmed byte-identical by SHA-256.

| control | mutation | result |
|---|---|---|
| `N1` | all 4 instances of a T4 figure | RED ✓ |
| `N2` | **1 of the same 4 instances** | **GREEN — the blind spot** |
| `N3` | all 3 instances of the drift ρ | RED ✓ |
| `N4` | both instances of a control slope | RED ✓ |
| `N5` | all 7 instances of a re-derived share | RED ✓ |
| `N6` | **the observed-step operand in the JSON**, prose untouched | RED ✓ |
| `N7` | `controls_ok` flipped to false in the JSON | RED ✓ |

`N3` initially reported **`MUTATION TARGET NOT FOUND`** — the prose uses U+2212,
not a hyphen, and the checker normalises them while the mutation did not. A bare
`replace` would have returned a silent green and I would have recorded a control
that never ran.

`N6` and `N7` are the ones that matter: they corrupt the **operand** and leave
the document alone, and the harness still goes red. That is the difference
between re-deriving and pattern-matching a document against itself. `N2` is the
registered limitation: **presence-checking is instance-blind.**

## 29. Is the shortfall a support problem? The prediction holds; the explanation does not

The orchestrator's facts 1360-1362: on `flowers-cpl` the boundary-elected
pixels render as thin curved ribbons tracing petal edges, so *"a fit whose
support assumes a broad region will be starved of pixels on most of the
population, and the shortfall would be a support problem, not a model problem"*.
Requested test: re-score the unmix restricted to contour pixels.

**Answer: the prediction is confirmed and the explanation is refuted.** The
unmix does work far worse on thin structures — **−11.01%** against **−32.80%**,
a 21.78 point gap at 7.3 null standard deviations — but not because anything is
starved.

### 29.1 What the operand says about "contours"

**Verified at source** on `argmax-index.tif` (2344×3520, uint16, frames 0-175):
frame 0 **29.8139%**, frame 175 **0.1813%**, boundary **29.9951%**. The
orchestrator's message quotes 29.81% and 0.18% and both are exact. *(Fact 1361
states 33.74% for the same stack; the index map gives 29.9951%. Worth
reconciling — it may be a different field, since `--index-map` exists only on
`argmax-baseline` and reads the naive argmax, not the regularised winner
field.)*

| statistic | value |
|---|---|
| median half-width | **3.00 px** |
| p10 / p25 / p75 / p90 | 1.00 / 1.41 / 6.71 / **12.37** px |
| at half-width ≤ 1px | 24.32% |
| at half-width ≤ 2px | 39.27% |
| at half-width ≤ 8px | **79.49%** |
| components | 42 408, largest holding **35.45%** |
| in components < 50px (speckle) | **4.15%** |

Registered bar: median ≤ 1.5px is thin contours, ≥ 4.0px is broad. It measured
**3.00 px — MIXED.** And the population is not a scatter of contours: a single
connected component holds over a third of it, with only 4.15% speckle.

**Then I took the orchestrator's own discipline 677 and rendered it by width**
(`81-flowers-width.png`, yellow ≤2px, blue ≥8px). **The map inverts the
reading.** The smooth sweeping arcs that trace the petal outlines — the feature
that reads as "ribbons tracing petal edges" — are the **blue** ones, ≥16px
across. The yellow, genuinely thin population is diffuse speckle scattered
through the petal interiors, tracing nothing. So the coherent occlusion contours
are the *wide* part of the population. P109.

### 29.2 The support hypothesis, refuted three ways

**First, structurally, and it is visible in the source.** `13-unmix.py:fit()`
and `17-perpixel-depth.py` accumulate `s1, sa, saa, si, sai, sii` **over the
frame axis at each pixel independently**. There is no patch, no window, no
neighbourhood. The support of the estimator at a pixel is **n frames**, and a
one-pixel-wide contour has exactly the same n frames as the middle of a broad
region.

**Second, measured.** Finite observations per band pixel, partitioned by the
width of the structure the pixel's nearest boundary point sits on (p25 11.34px,
p75 30.82px): **38.000 thin against 38.000 broad**, relative gap **0.0000**.

**Third, the recorded arms already run the wrong way.** The global-`k_F` arm
treated **12.5%** of the band; the per-pixel arm treated **19.8%** and scored
better. **More coverage, better result** — the opposite of what starvation
predicts. Registered bar: a relative observation-count gap below 0.05 refutes
starvation, above 0.25 confirms it. It measured 0.0000 — **pixel-count
starvation REFUTED**. P107.

### 29.3 The variant that could have worked, and why it does not

Geometry does enter the model, just not through pixel count: `alpha_k =
blur_{sigma_k}(matte)`, and a thin structure blurred by a large sigma loses
amplitude far faster than a broad one. If alpha never rises, the admission gate
`amax >= 0.05 & (amax − amin) >= 0.05` rejects the pixel. That is the
orchestrator's hypothesis in the form this estimator can actually express.

**The attenuation is real. The gate is not.**

| sigma cap | alpha-gate coverage | median `amax` thin | broad | gate pass thin | broad |
|---|---|---|---|---|---|
| ≤ 40px (local) | **97.62%** | **0.1627** | **0.3444** | **90.51%** | 100.00% |
| ≤ 238px (shipped `c` = 0.8) | **100.00%** | 0.4137 | 0.4629 | 100.00% | 100.00% |

Thin structures do attenuate alpha by **2.1×**, exactly as the mechanism
requires. But the gate still admits **90.51%** of them, and admits **97.62%** of
the band overall against a recorded coverage of **19.8%** — so the alpha gate
rejects almost nothing and **the R² ≥ 0.5 term is what sets coverage**. At the
shipped `c` the situation is worse still: sigma reaches **238px** on a 744×1144
ROI, the blur saturates toward a global constant, and alpha carries barely any
geometry at all. A mechanism can be directionally right and still explain
nothing if the valve it operates is already open. P108.

### 29.4 The re-score, which is the part that holds

Boundary points split at the quartiles of their local half-width — thin ≤
**13.19 px**, broad ≥ **34.60 px**.

| population | n | F0 ISO | fixed ISO | ΔISO | absolute |
|---|---|---|---|---|---|
| all points (`C-T4-ALL`) | 6103 | 0.06804 | 0.04888 | **−28.16%** | −0.01916 |
| **thin quartile** | 1526 | 0.04396 | 0.03912 | **−11.01%** | −0.00484 |
| **broad quartile** | 1526 | 0.09229 | 0.06202 | **−32.80%** | −0.03027 |

`C-T4-ALL` reproduces the shipped figure to **0.003 points**. `C-T4-NULL`, 20
shuffles of the width labels, gives mean **−1.01** and p95 |gap| **6.44** points
against a registered ±10 bar. The observed **21.78 point** gap is **7.3 null
standard deviations**. P106.

**The limit of this evidence, stated plainly.** The bee's *thin* quartile is
half-width ≤ 13.19px — **limbs, 26px across**. `flowers-cpl`'s median is 3px
half-width. So this measures limb scale and says nothing directly about the
flowers regime a factor of four thinner; extrapolating across that gap is not
measured. `flowers-cpl` has no matte, no unveiled truth and no cached fit here,
so testing it is a new experiment, not a re-score.

### 29.5 Two disciplines, audited — and I failed one of them in this file

**Discipline 676, and I broke it while citing it.** `C-T3-COVER` was registered
two-branch: *coverage ≥ 19.8% means the alpha gate is a superset of the recorded
gate, PASS*. It measured **100.00%** and printed **PASS**. A gate that passes
every pixel is not a valid superset, it is degenerate, and a two-branch bar had
no way to say so. Rewritten with three branches — broken / plausible /
**degenerate** — which is what voided T3 and produced §29.3's honest reading
instead of a false refutation. One hour after being handed the discipline. P111.

**Discipline 677 generalises past regions, and §29.4 is the demonstration.** My
ISO metric is *not* region-averaged — it is a profile along boundary normals, so
it is not blind in the way region averages are. But it **pools over all boundary
points**, and pooling over a boundary hides a contour/bulk split exactly as an
area average hides a contour. One number, **−28.16%**, concealed **−11.01%** and
**−32.80%**. The rule that survives is stronger than the one about maps:
*before believing a pooled statistic, partition it by the geometry it is pooled
over.*

**And a third, which is mine.** T2 and T3 first partitioned band pixels by the
interior EDT at the nearest foreground pixel — but the nearest foreground pixel
to a background pixel always lies **on the boundary**, where that EDT is ≈1.
Both quartile thresholds came back **1.0**, and the two subsets duly returned
`amax` medians identical to four decimals. I diagnosed the spread of the
*statistic* first, found `amax` genuinely varies (IQR 0.124), and concluded
coincidence. The defect was in the **partition variable**, whose p25 and p75
were the same number and were sitting in the JSON I had already written. P112.

### 29.6 What this leaves for the mechanism

1. **The reviewer's two-layer proposal stays live**, and §26.2 remains the
   reason: handed the true `alpha_k` cube the fit captures **+100.59%** of the
   headroom. Nothing here touches that.
2. **§26.2's unidentified third limiter is now partly located.** It is
   **structure-scale dependent**: the same estimator captures −32.80% on bulk
   and −11.01% on limbs. That is a sharper description than "semi-transparent
   hair fringe, non-constant `F(x)`, no alignment", and it is measured.
3. **The next experiment is not a re-score.** It is whether per-pixel `k_F` is
   *estimable* on thin structures at all — the winner field there is what the
   orchestrator calls structurally undefined, and `k_F` is the term §26.2
   measured as worth 397.83 points.

### 29.7 Verification, and the section 28 blind spot is closed

`verify_s29.py` re-derives every figure in this section from
81-contour-support.json and, for the sign repair, from 13-unmix.json and
17-perpixel.json. It re-computes each quotient rather than reading it back:
all three dISO values, the gap, the null sigma, the gate pass ratio, the alpha
separation and the corrected global arm. **67 checks, 0 failures.**

It also does the one thing the section 28 harness could not. Every figure is
required to appear an **exact number of times**, not merely to be present.
control_s29.py N2 mutates **exactly one of three** copies of the boundary
share and the verifier goes **RED** — the defect class that §28.9 registered as
an open blind spot, where the equivalent control stayed GREEN. P113.

| control | plants | expected | got |
|---|---|---|---|
| N0-NOOP | nothing | GREEN | GREEN |
| N1-ALL | all 3 copies of a figure | RED | RED |
| N2-ONE-OF-3 | **one** of 3 copies | RED | **RED** |
| N3-JSON-FIXED | a JSON operand, prose untouched | RED | RED |
| N4-JSON-SD | a JSON operand, prose untouched | RED | RED |
| N5-SIGN-BACK | one repaired site regressed | RED | RED |
| N6-ROW-CELL | one cell of one table row | RED | RED |
| N7-VERDICT | the registered verdict word | RED | RED |
| N8-ATTENUATION | a derived ratio | RED | RED |

**9/9 behave as registered.** N3 and N4 move the JSON with the prose untouched,
so the verifier is re-deriving and not pattern-matching. Both files are backed
up to %TEMP% and restored with a SHA-256 identity check.


## 30. The sidecar alert: the risk was real, the contamination was not

I declared one of my own numbers contaminated. This section retakes it and
finds it was never contaminated — by a hash equality rather than an argument.

### 30.1 What was declared, and why

`strehl align` once defaulted its warp sidecar to `<stackdir>/warpmap.txt`,
inside the shared read-only capture library, with seven agents live in the
tree. The default moved to a per-config cache at `8118dd7` (10:32). §15.2's
arm A was rendered at **03:43:56**, inside that window, with `STREHL_ALIGN=1`
and no named sidecar — and I kept no `alignment:` provenance line. So the
registration it used was unprovable, and P20/P46's **−6.6%** was provisional.

Exactly one render in this milestone was exposed. §16's before/after pair
(05:07, 05:09) and the C-ZOOMNULL pair (06:44, 06:46) all pinned
`STREHL_WARPMAP` explicitly, which `merge_cmd.rs` hard-validates and never
caches. Arm U discards registration outright, so no sidecar is consulted.

### 30.2 The retake, on a named sidecar

Solved into my own scratch, at the reference the merge would pick itself
(149 of 299), never into the capture library:

```
strehl align D:\personal\macro\bee-3-cpl --reference 149 \
    --out C:\dev\strehl-out\M87-bee\bee3-ref149.warpmap.txt
  stack bee-3-cpl: 299 frames, digest 8d023c0fe355d109
  placed 299/299 frames, refused 0
  held-out corner error (median): 13.578 plane px   cycle floor: 2.908 px
```

Both arms were then re-rendered with `STREHL_WARPMAP` pinned to that file, on
the same binary, same `--gate 0`, same ROI, same metric — and this time the
provenance line was kept:

| arm | `alignment:` line as printed |
|---|---|
| U2 | `OFF -- frames are combined unregistered` |
| A2 | `ON (sidecar-override), reference frame 149, 299 placed / 0 refused`, solve **0.0 s** |

`solve 0.0 s` is the load: the binary took the named sidecar rather than
re-solving. `D:\personal\macro` held **0** `warpmap*.txt` before and after.

### 30.3 The result

**C-BINARY** (validity gate, registered first): the unregistered arm must
reproduce, or nothing downstream is comparable. It reproduces **byte for
byte** — max |U2 − U| = **0 DN**, SHA-256 `895e458dd8f4722de0dac57d`.

Then the finding:

| pair | max abs diff | SHA-256 (first 24) |
|---|---|---|
| A (03:43, unprovable) vs A2 (pinned ref 149) | **0 DN** | `e5d6182fff887119e8fc5a12` |
| U (03:42, `ALIGN=0`) vs U2 | **0 DN** | `895e458dd8f4722de0dac57d` |

The render made with no named sidecar and the render made with an explicitly
named, hard-validated, 299-frame reference-149 sidecar are **the same file**.
Arm A used the correct solve. The declared contamination did not occur.

Scoring confirms it downstream. Re-running §15's pre-registered path on the
retaken renders reproduces `35-registration.json` to 16 significant figures —
ISO_U **0.0722684422027054** (n = 6600, `d*` = 16), ISO_A **0.06642480705112791**
(n = 6380, `d*` = 18), reduction **8.086%**, CIs overlapping, verdict **R1-C**
— including the derived `roi_A` = (1182, 1915, 202, 1354) and scale 1.0473871678.

One clarification for the reader, because these two numbers have confused me
once already: §15.2's table reports **script 36**, which adds the `C-resample`
control and scores all three arms on a matched crop (U **0.06805**, Uw
**0.06844**, A **0.06356**, total **−6.595%**, decomposed +0.579% resample and
−7.174% registration). **Script 35** is the pre-registered R1 without that
control (**−8.086%**). Both are in the tree, both are right, and they answer
slightly different questions. Since A2 is byte-identical to A, script 36's
result transfers unchanged by construction and does not need re-running.

**Verdict CONFIRM**: the retake moved the reduction by **1.49 points** against
a registered ±5.0-point bar, and the R1 class is unchanged. **P20 and P46 are
clean.**

### 30.4 The exit-code trap, measured rather than inherited

The orchestrator reported that a truncating `Select-Object -First N` stage
makes a failing
command read `$LASTEXITCODE = 0` when there are more than N matches. Rule 12
applies to their measurements as to mine, so I measured it. The conclusion
holds and **the stated mechanism does not**:

| arm (pwsh 7.6.5) | true code | reads |
|---|---|---|
| primed by a success, then a truncated **failing** run | 1 | **0** — false green |
| primed by a failure, then a truncated **succeeding** run | 0 | **1** — false red |
| same, Windows PowerShell 5.1 | 1 / 0 | **−1** / 0 |

`$LASTEXITCODE` is not *set* to zero; it is **not updated at all**, so the gate
inherits an unrelated command's status. The match count is not the trigger —
truncation is, and it also stops the upstream (0.3 s against 6.1 s). My first
probe appeared to refute the whole thing by reading a correct `1`, which was
itself a stale read primed by the previous arm; the priming arms are what
separate them.

**My own gates are not exposed, and I checked rather than assumed.**
`control_s29.py:111-114` reads `subprocess.run(...).returncode` inside Python,
never through a shell pipeline, and `verify_s29.py`'s verdict is a printed
count read from a full capture. Both re-run under the capture-then-filter
pattern: **67 checks / 0 failures**, **9/9 controls as registered**.

### 30.5 A defect this file was carrying

Reading the P113 row for this section showed it beginning "… is closed."
followed by "erify_s29.py" — a missing *v*. It was a raw **U+000B**, written
by a PowerShell here-string that consumed a backtick-*v* pair as an escape.
Three such characters were in the committed file (BEL at §5, VT at the P113
row and at §29.7); a sweep of `docs/research/*.md` found four more of the
same class in another milestone's report. `corpus_lint.py`, `tblcheck.py` and
a 67-check verifier all passed over them, because none of them look. Repaired
by `src/ctrlfix2.py` on bytes, preserving all 4088 CRLF endings, three lines
changed.


### 30.6 Verification

`src/verify_s30.py` re-derives every figure in this section from an operand
that is not the prose: the SHA-256 of the four render files, and the JSON
written by `83-arm-a-retake.py`, `35-registration.py` and
`36-registration-controls.py`. Occurrence counts are asserted exactly, not by
presence. It also enforces the one guard nothing else in this toolchain
provides — zero stray C0 control characters in the report.

**51 checks, 0 failures.**

`src/control_s30.py` plants a known defect for each and requires RED:

| control | what it corrupts | expected | got |
|---|---|---|---|
| N0-NOOP | nothing | GREEN | GREEN |
| N1-HASH-1-OF-2 | one of two copies of the hash | RED | RED |
| N2-JSON-ISO | a JSON operand, prose untouched | RED | RED |
| N3-JSON-VERDICT | the JSON verdict word | RED | RED |
| N4-CTRLCHAR | plants a U+000B as a here-string would | RED | RED |
| N5-MOVED | the re-derived shift | RED | RED |
| N6-N-U | a profile count | RED | RED |
| N7-S36 | the script-36 decomposition | RED | RED |

**8/8 behave as registered.** N1 corrupts exactly one of two copies, which a
presence check would pass. N2 and N3 move a JSON operand with the prose
untouched, which is what separates re-derivation from pattern-matching. N4 is
the control that matters most here, because the defect it plants is the one
this report was already carrying and no linter caught. Exit codes are read
through `subprocess.run().returncode` inside Python, never a shell pipeline.

## 31. The wild veil: what the figure actually shows

The orchestrator sent a two-panel figure of `bee-3-cpl` at `(700,3150)
1100x900` — the shipped default gate, an isolated sidecar, the claw and the
hair mass — and asked three things: separate the concentric banding near the
claw into veil-falling-off-in-steps, quantisation in the stretch, or a
separate defect; build a rendered before/after gate on that exact region and
let it outrank any scalar; and say if the wild veil contradicts my model.

The banding is a fourth thing. The gate failed. Both are below.

### 31.1 Provenance: this is that figure, not one like it

Re-rendered from `D:\personal\macro\bee-3-cpl` at the shipped default with
`STREHL_WARPMAP` pinned to my own reference-149 sidecar (rule 45), the output
is SHA-256 **identical** to the orchestrator’s file:

```
strehl stack D:\personal\macro\bee-3-cpl --srgb --auto-exposure \
    --index-map ... --n-eff-map ...        # no --gate flag was passed
gate           : 4.0  (resolved DEFAULT_GATE, `merge.rs:297`; recorded
                 explicitly because a default is not a record --
                 `byte-freeze.rs:855` notes it “was not always” 4.0)
binary         : sha256 d2488939cbaca3e13051263f  (frozen into my own scratch)
alignment      : ON (sidecar-override), reference frame 149, 299 placed / 0 refused
mean n_eff     : 55.321      n_eff = 1: 38.77%      exposure: +1.54 stops
sha256(mine) == sha256(ORCH-gallery3/bee-3-cpl.tif) == e400a63aa9f6ab1f1957940d
```

The `--index-map` and `--n-eff-map` from the same run are therefore the
election and `n_eff` fields *of that figure*, at half resolution on the plane
grid, scaled 2× to overlay. `87-election.py` asserts the equality before it
measures anything (`P123`).

### 31.2 The veil is 4133 DN, and needs no stretch

The covering message said the step is “a few DN and invisible at normal
display gamma”. Reconstructing the diagnostic stretch from `blob.py` shows
that cannot be so: `span = (p99 − p1) * 0.35 = 14 696 DN`, so **one output
code is 115.7 DN** and a 3 DN step is 0.026 of a code — the stretch would
*hide* a few DN, not reveal it. Anything visible in that panel is large.

`86` first measured the veil as median DN against distance from the
silhouette. That was confounded: the subject fills the upper left, so every
far pixel is lower right and the scene’s own gradient rides in. `90-veil.py`
repairs it with a **local** reference — the mean of far-field pixels within a
251 px window — which follows any gradient and cancels it, and whose residual
sd on the far field is 1048.8 DN against the global quadratic’s 1736.3 DN.

| d (px) | 1 | 3 | 5 | 8 | 12 | 18 | **25** | 35 | 50 | 70 | 140 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual (DN) | −11721 | −3976 | −36 | +2077 | +2847 | +3061 | **+3391** | +2782 | +479 | −113 | −836 |

Amplitude **+4133 DN** over the −742.5 DN baseline: 35.7 codes of the
diagnostic cast, 6.31% of full scale, **16.1 of 255** codes in an ordinary
8-bit viewer. Control C-FAR, the same pipeline against a 180°-rotated subject
mask — same area, same perimeter, same shape, no registration to the image —
returns −316 DN and no hump (`P118`).

### 31.3 The noise field is the estimator working

Pass two averages `n_eff` frames per pixel, so if the noise field is nothing
but un-averaged pixels then `noise * sqrt(n_eff)` is constant and the log-log
slope is **−0.5000** exactly. Measured over 710 160 background windows:

| n_eff | 1.3 | 3.6 | 10.4 | 16.0 | 24.5 | 42.2 | 59.7 | 86.2 | 180.9 | 282.8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noise (DN) | 219.0 | 169.1 | 91.6 | 65.3 | 47.4 | 39.4 | 34.1 | 27.2 | 18.5 | 15.4 |

Slope **−0.5228**, intercept 283.3 DN at `n_eff` = 1, across a 211× range of
`n_eff` and 14× of noise. Nothing was fitted to produce the −0.5 (`P119`).

### 31.4 The banding: neither of the two candidates, and the third is wrong too

`84-banding.py` registered a dither discriminator — quantisation introduced
by a uint8 cast is removed by dithering *before* the cast; real 16-bit
structure is not — and it split the region rather than the hypothesis:

| box | noise sd | code/noise | dither ratio | codes | median run |
| --- | --- | --- | --- | --- | --- |
| pocket, inside the claw | 160.1 DN | **0.72×** | 1.0× | 149 | 1.0 px |
| far background | 22.2 DN | **5.20×** | 1.8× | 42 | 2.0 px |

Banding is *impossible* where ORCH reported it (the noise self-dithers) and
*expected* a few hundred px away. Meanwhile the high-pass of the **16-bit**
data at ±480 DN, computed before any cast, still shows concentric arcs. So
there are two phenomena and they are in different places.

The `n_eff` map resolves it: rendered as a map (discipline 677), the arcs
**are** the `n_eff` contours. And P119’s noise law crosses the cast’s 115.7 DN
quantum inside the region, so the same contours become visible as flat
plateaus on one side and dithered speckle on the other. Simulating the
flatness statistic against the measured lag-1 correlation +0.4676 and
gradient 16.44 DN/px puts the crossing at `n_eff` **12.86** against **19.10**
measured, ratio 0.67× (`P120`).

**A wrong bar of mine, disclosed.** I first predicted the crossing at `n_eff`
5.54 from “posterisation appears when the noise falls below about one code”
and scored the 3.45× miss PARTIAL. That constant is simply wrong — adjacent
samples share a code with probability of order `q/s`, and the render’s pixels
are correlated by the demosaic anyway. The miss measured my arithmetic. The
simulation has no closed form to get wrong, and control C-SIM makes it earn
its keep by reproducing the low-`n_eff` flatness it was not tuned to: 0.170
against 0.178, 4.6%.

### 31.5 The photometric step, bounded — and a bar I set too coarse

The election-index boundaries carry **1.04×** the high-pass of non-boundary
background (rot180 null 0.93×). A null is a claim about the instrument, so
`88-controls.py` plants the exact mechanism — `g′ = g + s * index`, monotone
in frame index as M99 fact 23 requires — and sweeps `s`:

| s (DN/frame) | 0 | 1 | 3 | 10 | 30 | 100 | 300 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| enrichment | 1.038 | 1.115 | 1.154 | 1.269 | 1.462 | 1.692 | 1.769 |

My pre-registered “≥ 1.5× means detected” therefore fires only at 100 DN per
frame — **58.5% drift across the bracket**, five times M24’s worst stack. As
written it could not have detected any realistic photometric step and its
“excluded” reading is **withdrawn**. What replaces it is the curve: the
statistic resolves to 1/26 (the high-pass is integer DN on a base of 26), so
a 2-resolution threshold of 1.115× puts an upper limit of **1.00 DN per
adjacent frame** = 0.58% across the bracket. Coffee-bean’s 11.70% would read
1.37× and is excluded (`P121`).

### 31.6 The gate the orchestrator asked for, and what it did

Rendered before/after of exactly `(700,3150) 1100x900`, shipped default gate,
`STREHL_WARPMAP` pinned, AFTER = `STREHL_FIX_HALO=1`
(`C:\dev\strehl-out\M87-bee\BEFORE-AFTER.png`, hair mass at 100% in
`HAIR-100PCT.png`, tips at 2× in `HAIR-TIPS-2X.png`).

The scalars were excellent:

| zone | n | median abs delta | p99 abs delta |
| --- | --- | --- | --- |
| subject interior (>10 px in) | 160 241 | **0.0 DN** | **0.0 DN** |
| subject edge (≤10 px in) | 62 039 | 0.0 DN | 11 832 DN |
| background near (≤40 px) | 147 004 | 5078 DN | 14 182 DN |
| background far (>70 px) | 536 802 | 0.0 DN | 2992 DN |

Leakage into the subject **0.000**; veil amplitude 4133 → 153 DN, **−96.3%**.
By every number I had registered, it worked.

**The render says otherwise.** At 100% the hair tips are truncated to stubs
against a hard stair-stepped boundary, the wispy isolated hairs over the pale
background are gone, and a hard-edged rim with blocky terracing stands where
a soft veil used to be. `92-erasure.py` measures it on a population defined
from the reference render rather than from a mask — thin dark structure in
near background, depth below a 9 px grey dilation — and tip contrast falls
**6316 → 3739 DN**, ratio **0.5919**, with 33.1% of tip pixels dropping below
half the selection threshold. Controls C-INT and C-NULL both return 1.0000.

The reason the scalar was blind generalises past this correction: **0 of
39 274** hair-tip pixels lie inside the segmented subject mask. A leakage
test that looks for spill *into* the subject cannot see damage to a
population that is classified as background — and near a silhouette, the
hairs are the background pixels. This is the same hole as the +72.9%
episode, in a metric written after it (`P122`).

The correction stays **OFF**. That was already the ruling; it now has a
measured reason on the flagship image.

### 31.7 Does the wild veil contradict my model?

No, and the two-layer reading survives, but the population is not the one my
cells were built on. The hair mass is not one silhouette; it is thousands of
occluding edges a few pixels apart, which is the thin-structure regime §29’s
T4 flagged as **not measured** (bee thin quartile ≤ 13.19 px against
flowers’ 3.00 px median). Two things follow, and both are testable rather
than argued:

- The veil profile peaks **25 px** from the silhouette and is still +479 DN
  at 50 px. That is far wider than the spacing between adjacent hairs, so at
  the hair mass the veils of neighbouring edges **overlap**, and a per-edge
  two-layer fit is solving for a background that is itself veiled by the next
  hair over. My cells never had that.
- `n_eff` is 1 in exactly that band and the winner field is structurally
  undefined there, so the correction has no reliable elected index to build
  on — which is consistent with it reaching for the nearest confident
  background and taking the hair tips with it.

### 31.8 Verification

`verify_s31.py` re-derives every figure in this section from the JSON in
`experiments/M87-occlusion/data/`, asserts exact occurrence counts rather
than presence (`P113`), re-hashes both renders, and enforces the
zero-C0-control-character guard. `control_s31.py` runs the registered
negative controls, each anchored on a unique single line with a hard error if
the anchor does not land.

The verifier earned its place on the first run: it rejected the `n_eff`
range I had written as **218×**. I had divided the two *rounded* display values
(282.8 / 1.3) instead of the operands (282.822 / 1.342), which give **210.7×**.
Corrected to 211× in `P119` and §31.3. It is a small number and it changes no
conclusion, but it is precisely the failure this milestone exists to catch — a
figure derived from a compressed rendering of the data rather than from the
data — and it survived my own reading of the draft.

## 32. Two hazards audited against this milestone

The orchestrator quarantined 11 stray sidecars out of the capture library and
filed M106's attribution of the alignment watershed, and asked whether either
re-scopes numbers I have reported. Neither does, and both answers are
measurements rather than reassurances.

### 32.1 The 40-frame sidecar could not have reached M87

`bee-3-cpl\warpmap.txt` held a **40-frame** solve for a **299-frame**
bracket. The trap is not that guard failing — it works — but that a
`--limit 40` run meets a 40-frame sidecar and accepts a solve made from a
different subset at a different reference. So the question is whether any M87
render was short-bracketed.

**The recorded `alignment:` lines answer it directly.** That line prints the
placed count, and a `--limit 40` run cannot print 299. Every render in this
milestone whose provenance I kept prints a full bracket — §30.2's
arm A2 and §31.1's figure render both read `299 placed / 0 refused`. For
those renders the stale sidecar demonstrably did not apply, whatever was
sitting in the library at the time.

For the renders where I kept no provenance line, the argument is the guard
rather than a record: a full-bracket invocation meets a 40-frame sidecar,
the frame count disagrees, `load_or_solve` re-solves, and the stale file is
refused. The trap needs `--limit N` to meet a sidecar of exactly N frames,
and `--limit` appears **0** times in the 104 measurement scripts
here. §30 separately retook the one render exposed to the *align*
default and found it byte-identical to a pinned-sidecar render, 0 DN, which
settled that one by hash rather than by argument (`P124`).

I hold no claim that needs retaking on this account.

**A correction to my own first draft of this section,** because it is the
kind that reads as evidence and is not. I first wrote that `--limit` "appears
0 times across all 30 M87 scripts" and rested the finding on it. There are
**135** scripts, not 30 — and, more to the point,
**0** of them invoke the binary. Every render here was hand-run
from PowerShell, so a count over the Python tree is a true statement about a
population that does not contain the thing being claimed. My own verifier
caught it by re-counting from disk instead of reading the number I had
recorded, which is the entire reason it re-counts.
### 32.2 The watershed moves every pixel and 6.86% of the halo

`885e9f7` at 2026-08-24 03:15:23 moves 100.0000% of pixels at RMS 3594 DN.
**27 of M87's data files predate it**, written between 00:13 and 03:00, and
they include the metric's own definition and the −28.2% unmix. So the
question is fair, and it has an operand already on the table.

`51-zoomnull.json` renders `ROI_LEG` both ways on the same binary:

| arm | halo ISO before | correction removes |
| --- | --- | --- |
| unregistered (`STREHL_ALIGN=0`) | **0.06878** | **82.76%** |
| aligned (shipped default) | **0.06406** | **72.93%** |

Alignment removes **6.86%** of the halo. The artifact is 93.1% intact
without registration, and the correction's benefit agrees across the two to a
ratio of **1.135**, inside the ±33% band I registered. A number
measured on an unaligned merge and a number measured on an aligned one are
therefore in the same magnitude class for every halo quantity M87 reports,
which is why no pre-watershed verdict here flips (`P125`).

That is a bound, not an identity. It says the watershed cannot have
manufactured or hidden this artifact; it does not license quoting a
pre-watershed figure to three decimal places against a post-watershed one.
Where §31 needed precision it re-rendered rather than reached back.

### 32.3 My own hash had the defect M106 paid for

The orchestrator asked that every recorded hash carry its entire invocation,
explicitly including `--gate` even when it is the default. §31.1 —
written hours after I had read the sidecar warnings — recorded its
SHA-256 beside the words “at the shipped default” and nothing more.
That is precisely the record M106 could not use: `byte-freeze.rs:855` already
states `DEFAULT_GATE` “is 4.0 today and was not always”.

Repaired in place. §31.1 now carries the command, `gate 4.0` with
`merge.rs:297` beside it, and the binary's SHA-256 (`P126`).

The general form, and the reason it keeps recurring: **a default is a value
that is resolved elsewhere and may move, so naming it by reference records
the resolution rather than the value.** “The shipped default” is a
pointer. A byte-freeze is a claim about bytes, and a pointer does not pin
bytes.

### 32.4 Verification

`verify_s32.py` re-derives every figure here from `51-zoomnull.json` and
`93-audit.json`, re-hashes the frozen binary, and re-counts `--limit` across
the M87 script tree rather than trusting the recorded zero.


## 33. The gate ladder: averaging is not the mechanism

The orchestrator rendered `bee-3-cpl` four times varying only `--gate`, pinned
the exposure, and reused one solved sidecar so that placements, reference
frame, stack digest, frame count and resampler are byte-identical across the
arms. Their eye judgement, which they explicitly declined to promote to a
finding, was that the veil is strongest at gate 4.00 and substantially weaker
by gate 0.00. If true it would be the first positive localisation of the
mechanism, because fact 1375 has already shown the veil is invariant across
all three resampler kernels.

**It is not true. The veil survives.** Between gate 4.00 and gate 0.00 the
number of frames averaged per pixel changes by **55.3×** and the veil loses
**11.7%** of its amplitude — and §33.5 shows that 96% of even that 11.7% is a
level offset rather than the veil. The gate is not the mechanism.

### 33.1 Provenance (rule 47)

Operands are the orchestrator's four pinned renders in
`C:\dev\strehl-out\ORCH-gate\`, each 197 797 874 bytes:

```
strehl stack D:\personal\macro\bee-3-cpl --gate <G> --srgb --exposure=1.54 \
    --out pin-bee-3-cpl-gate-<G>.tif
env: STREHL_WARPMAP=<orchestrator scratch sidecar>   (sidecar-override)
     STREHL_ALIGN   unset   STREHL_FIX_HALO unset
G in {4.00, 2.00, 0.7078, 0.00};  4.00 is the shipped DEFAULT_GATE
alignment ON, reference frame 149, 299 placed / 0 refused, CatmullRom
```

**The gate-4.00 arm hashes `E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A`
`7ABC30D8E7F17112`, which is byte-identical to this milestone's own
`s31-bee3.tif`.** The assertion is in `96-gate-final.py` and fails the run if
it ever stops holding. So the ladder is anchored on the exact render §31
characterised, and §31's **+4296 DN** is its gate-4.00 point rather than a
separate measurement that has to be reconciled.

Two caveats recorded from the same logs and not swept: the solve's held-out
error is **13.578 px**, above M86's `T_usable` of 4.0 px, and coverage scales
the field of view to **0.9315**. Both apply identically to all four arms, so
they cannot produce a gate difference, but neither arm is a precise
registration. Separately, the owner's original brief recorded gate 2.00 as
`mean n_eff = 23.043` with 46.57% at `n_eff = 1`; this ladder records
**19.182** and **51.15%** for the same stack and gate. Unreconciled, and
plausibly the M86c watershed of §32.2, but not measured here.

### 33.2 The metric the orchestrator's failure demanded

Their own ring-profile instrument failed and they said exactly how, which is
what made this cheap. Both failures are repaired by construction rather than
by care.

**Their failure 1, the reference moved.** Every ring including the far
reference shifted monotonically across arms, because lowering the gate stops
averaging away the unfitted per-frame photometric drift. **Repair R1: every
mask — subject, far field, hair — is derived once from the gate-4.00 arm and
applied unchanged to all four.** The arms are then compared on identical
pixels, so a change is the image and not the segmentation. Deriving a mask per
arm is what let their reference move.

**Their failure 2, hair contamination.** A 45th-percentile threshold on a crop
that is 45.2% subject left hair tips in the near rings, and their 1–5 px ring
read **−3232 DN** — darker than far field, which is hair and not veil.
**Repair R2: thin dark structure is excluded by depth below a 9 px grey
dilation**, the population §31's `92-erasure.py` already uses, at a threshold
proportional to scene contrast rather than an absolute DN so that the excluded
set does not itself move between arms.

They asked for invariance to a 2.14% level shift. Weak invariance is not worth
registering, so the metric is built to be invariant to **any** affine map
`x → a·x + b`:

```
V  =  (peak ring residual)  /  (far background level − subject level)
```

Numerator and denominator are both first-order in the image, so `a` cancels
and `b` cancels twice. The local reference is a ratio of uniform filters,
which is linear, so the residual scales exactly. Medians are affine
equivariant. With the masks frozen by R1 the invariance is **exact**, and
`C-AFFINE` demands bit-level agreement rather than a tolerance.

### 33.3 Two of my own controls failed, and the worse one was my bar

I registered four controls before running and **two went red.** Neither bar
was weakened; both failures were diagnosed to a mechanism first
(`95-control-diag.py`).

**C-AFFINE returned 2.451e−07 against a registered 1e−12.** My own standing
rule is that a binary-exact factor must reproduce bit for bit, and that this
is what separates round-off from a leak. Diagnosis: the local reference sums a
251 px box, ~63 001 samples of magnitude ~5×10⁴, so the accumulator reaches
**~1.795e+09** against float32's exact-integer ceiling of 2²⁴ = 16 777 216 —
**107× over**. The sum cannot be exact, and it rounds differently once the
operands are scaled. Prediction: float64 collapses it. Measured: **3.664e−15,
6.69e+07× tighter**, on the same three factors. A genuine leak is
accumulator-width independent. The metric now runs in float64 and meets the
original bar.

**C-ROT returned 44.5% of the real veil against a registered 25%, and two
separate things were wrong.**

First, the control was contaminated by construction. I rotated the subject
mask *and* the far field *and* the valid set, re-admitting the real bee — 22.5%
of the crop — as ordinary background. Measured: **30.7%** of the rotated
2–60 px ring band lies in the real 2–60 px veil band and **23.4%** of it lies
inside the real subject. §31's `C-FAR` rotated only the distance geometry and
kept the real subject excluded, which is the better construction.

Second, **and this is the more serious error, my bar was sign-blind.** `V` is
a signed peak-hump amplitude and the hypothesis I registered in my own
docstring was directional — *“a hump under C-FAR would mean the estimator
manufactures one”*. I then coded `abs(V_ctl / V_real) < 0.25`. The repaired
control returns **V = −0.079502**: the maximum over the entire 2–60 px search
window is *negative*, so no hump exists at any distance, which is exactly what
a null should look like. `abs()` reported that as “0.590, FAIL”. **I did not
fail to find a null; I built a bar that cannot recognise one.**

That is the third sign-blindness failure in this milestone's family — `P95`'s
share-of-change ratio reading a 16.24% increase as “+99.6%, driver confirmed”,
the orchestrator's two-branch bar printing the wrong verdict for a 7.8× effect,
and now this. **A ratio of magnitudes is not a test of a directional claim.**

The replacement does not relax the threshold; it tests the registered
hypothesis, and then proves the null three ways rather than asserting it:

| control | construction | result | bar | verdict |
|---|---|---|---|---|
| `C-AFFINE` | `x → a·x + b`, a ∈ {0.5, 2, 4} binary-exact, b = 1000 | max \|ΔV\| **3.664e−15** | < 1e−12 | PASS |
| `C-DRIFT` | `x → 0.9786·x`, the measured 2.14% drop | V moves **0.000000%**, raw DN moves **2.1400%** | < 2% | PASS |
| `C-ROT-A` | mask rotated 180°, directional and signed | **−0.079502** against a bar of +0.033699 | < 0.25·V | PASS |
| `C-ROT-B` | shape: any hump in 2–60 px? | max over the window **−150 DN**, negative at every distance | no hump | PASS |
| `C-ROT-C` | independent null: mask **translated** by (−420, 520), band overlap 17.6% | **−0.093960** | < 0.25·V | PASS |
| `C-POS` | plant 0 / 1000 / 2000 / 4000 DN into the 8–45 px band | monotone, and **exactly** `V + A/C` — error **0.00e+00** at three of four levels | calibrated | PASS |

`C-DRIFT` is the one that answers the orchestrator directly: **the hazard they
warned about is real and present in these operands — the raw DN amplitude
moves by exactly the 2.14% they measured — and the metric does not move at
all.** `C-POS` is the one that makes the nulls mean something: an instrument
that is quiet and an instrument that can respond are different claims, and
this one returns a planted amplitude exactly in units of scene contrast.

### 33.4 The ladder

| gate | far level DN | amp DN | C DN | V | V/V(4.00) | peak d |
|---|---|---|---|---|---|---|
| **4.00** (shipped) | 52 527.0 | 4296 | 31 870 | **0.13480** | 1.0000 | 25 px |
| 2.00 | 52 120.0 | 3899 | 31 464 | 0.12393 | 0.9194 | 25 px |
| 0.7078 | 51 939.0 | 3712 | 31 285 | 0.11865 | 0.8803 | 25 px |
| **0.00** | 51 864.0 | 3716 | 31 208 | **0.11906** | **0.8833** | 25 px |

**B15: PARTIAL, r = 0.8833.** Not `GATE-DEPENDENT`, whose branch required
r ≤ 0.70. The peak sits at **25 px in every arm** — the gate does not move the
veil, it barely dents it. The ladder is not even monotone: 0.7078 reads
0.11865 and 0.00 reads 0.11906, a slight rise.

Against the orchestrator's own `neff-ladder.txt` for this stack:

| gate | mean n_eff | n_eff = 1 | veil V | veil retained |
|---|---|---|---|---|
| 4.00 | **55.321** | 38.77% | 0.13480 | — |
| 0.00 | **1.000** | 100.00% | 0.11906 | **88.3%** |

**A 55.3× change in the number of frames averaged per pixel buys an 11.7%
change in the veil.** At gate 0.00 every pixel is a single unaveraged frame,
and 88.3% of the veil is still there.

**B17, robustness.** 27 settings over hair threshold {0.06, 0.12, 0.24}, far
field {50, 70, 100} px and reference window {151, 251, 351} px: r ranges
**0.8717 … 0.9843**, median **0.9076**. Registered `ROBUST` required all of
[0.80, 0.95], so the verdict is **SOFT** — the spread crosses the upper edge.
What matters is which branch it crosses into: **no setting reaches
`GATE-DEPENDENT`, and several land in `GATE-INDEPENDENT`.** The conclusion is
robust in the direction that carries it even though the magnitude is not.
`C-SWEEP-NULL` — each arm against itself — returns r = 1 at all 27 settings.

### 33.5 The residual 11.7% is an offset, not weakening

It would be easy, and wrong, to report “the gate weakens the veil by 11.7%”.

**B16 refutes the proportional reading.** If the gate scaled the veil down,
`delta(d)` would track the veil profile with slope ≈ 1 − 0.8833 = 0.1167.
Measured over 56 rings: Pearson **0.1569**, slope **0.0186**. `NOT
PROPORTIONAL`.

Reading the profile instead of the correlation shows why. The veil residual
falls from **+4296 DN** at d = 25 to **+838 DN** at d = 60 — it has nearly
vanished. The delta over the same span goes **+580 → +486 DN**. A quantity
that stays put while the veil decays by 80% is not a fraction of the veil; it
is an offset sitting underneath it.

**That is precisely the hazard affine invariance does not cover, and the
orchestrator named it.** The metric is immune to `x → a·x + b` applied
globally — `C-DRIFT` proves that at 0.000000%. It is *not* immune to a level
change that differs between the near zone and the far zone, because the
baseline is taken from the far zone. They wrote that the drift is “organised
spatially by the election”; a spatially organised level change *is* a
near/far difference.

**B18** fits two one-parameter models to `delta(d)` over d = 5…60:

| model | fit | RMS residual |
|---|---|---|
| `M_const`: delta = c | **+473.2 DN** | **148.4 DN** |
| `M_prop`: delta = k · veil(d) | 0.1398 · veil | 221.1 DN |

Ratio **0.671** against a registered 0.70 — **`CONSTANT OFFSET`**, and by a
margin of only 4%, which is disclosed rather than rounded away. Its three
controls pass: `C-ZERO` returns 0 for both models on identically zero input,
and the two positive plants — data whose true form I chose — are each labelled
correctly, so the discriminator can respond and not merely stay quiet.

Removing the offset:

| | peak veil | r |
|---|---|---|
| gate 4.00 | 4296 DN | 1.0000 |
| gate 0.00, as measured | 3716 DN | 0.8833 |
| gate 0.00, offset removed | **4189 DN** | **0.9958** |

**96% of the apparent shortfall is the near/far offset.** The better estimate
is that **99.6%** of the veil survives with averaging switched off entirely,
and **88.3% is a lower bound.** The conclusion does not depend on which of the
two is preferred, which is the point of reporting both.

### 33.6 What this closes off

Three candidate mechanisms have now been tested against this artifact and all
three are excluded:

1. **Resampling** — fact 1375, invariant across all three kernels.
2. **The averaging gate** — this section, invariant across a 55.3× change in
   `n_eff`.
3. **Demosaic** — §27's photometric-step work.

The orchestrator's prediction that a gate-dependent veil would have to live in
the regime where the gate acts is a good one, and it is worth noting that it
*fails in the useful direction*: they measured the gate to have no effect where
there is detail (flattest tile 33.5×, most-detailed tile 1.00×), so the veil's
persistence at `n_eff = 1` cannot be dismissed as measuring a region the gate
never reached. The veil sits in flat background adjacent to a hard edge, which
is exactly where the gate *does* act, and it survives anyway.

**What remains is selection itself** — the owner's original hypothesis, and
what §1 found when the halo looked identical at `--gate 0` and `--gate 2`. This
section is that reproduction done with a controlled instrument instead of an
eye, on a 55× wider ladder, with the drift the eye could not have separated
removed by construction.

### 33.7 The standing question: model or support? Neither

The orchestrator has twice asked whether §13's **−28.2%** was a *model* failure
or a *support* failure, and says the two route completely differently. The
answer is already in this report and it is neither. It is a third thing, and
that third thing is now partly located.

**Not the model.** `P83`: hand the fit the true `alpha_k` cube on a plant with
known truth and it captures **+100.59%** of available headroom — band RMSE
1.7837% against a merge at 4.5271% and a single-frame noise floor of 1.7999%.
The forward model is right. It exceeds 100% because the intercept is estimated
across 121 frames and is quieter than any one of them.

**Not the support.** `P107` refutes it three ways. (1) `fit()` regresses across
the **frame axis at each pixel independently** — there is no spatial
neighbourhood that could be starved. (2) Finite observations per band pixel
measure **38.000 thin against 38.000 broad**, identical. (3) The recorded arms
run the wrong way: the per-pixel arm treated **19.8%** of the band against the
global arm's 12.5% and did **better**. More coverage with a better result is
the opposite of starvation.

**It is a third limiter, and it is structure-scale dependent.** `P106`: the
shipped per-pixel arm captures **−11.01%** on the thinnest quartile of boundary
points against **−32.80%** on the broadest — a **21.78 point** gap at **7.3**
null standard deviations. Against the registered −50% bar the thin quartile is
the *worse* performer. One pooled number, −28.16%, concealed a 3× difference
between two halves of its own population.

And `P108` sharpens it further in a way worth repeating, because it is a trap:
the alpha-attenuation mechanism that would explain the split **is real but
non-operative.** Thin structures do attenuate alpha as predicted — median
`amax` **0.1627** against **0.3444**, 2.1× — yet the admission gate still
passes **90.51%** of thin band pixels. The coverage limit is set by the
`R² ≥ 0.5` term instead. *A mechanism can be directionally correct and still
explain nothing if the valve it operates is already wide open.*

So the routing the orchestrator asked for: **not a rewrite of the forward
model, and not a change of support.** The next experiment is whether per-pixel
`k_F` is *estimable* on thin structures at all, which is §29's own conclusion
and remains open. This section adds one constraint to it: since the veil is
unchanged by a 55.3× change in averaging, the difficulty on thin structures is
unlikely to be a noise-averaging problem, which makes an estimability limit
more likely than a precision limit. That is an inference from tonight's
result, not a measurement of it.

### 33.8 The +72.9% concern, restated

The orchestrator's caution stands and is already answered. The metric that
reported **+72.9%** while erasing the bee's abdomen hairs is not the metric
that certifies the correction. `B14` measures **tip contrast on a referenced
thin-structure population** — 6316 → 3739 DN, **33.1%** of tips destroyed —
and that is the number that caught the erasure the halo metric could not see.
The acceptance gate is the rendered 100% crop, outranking every scalar here,
exactly as they asked. `P104` records the audit: M87's halo metric is a median
*level* profile against distance, not a sharpness proxy, and a Catmull-Rom
gather that destroys ~49% of gradient energy moves it by **+0.6%**.

Nothing in §33 is used to certify a correction. It measures what the artifact
*is*, and what it is not caused by.

### 33.9 Verification

`verify_s33.py` re-derives every figure here from `96-gate-final.json`,
`97-gate-attrib.json`, `98-delta-form.json` and `95-control-diag.json`,
re-hashes the gate-4.00 arm against §31's render, and re-reads the `n_eff`
ladder from the orchestrator's `neff-ladder.txt` rather than from my
transcription of it. `control_s33.py` mutates operands with the prose
untouched to prove the harness re-derives rather than matching the document
against itself.

---

## 34. The orchestrator's causal test: does veil removal depend on how many frames are averaged?

The orchestrator sent a sharp prediction derived from this report's own §25
mechanism, and it is the right kind of message to receive: it names a number,
a direction, and a falsifier. Their words:

> at **gate 0.00** the merge is one frame per pixel, so it cannot remove a
> veil by combination and should read close to your single-frame **−26.47%**
> [...] At **gate 4.00** the flat background averages heavily and should
> read close to your merge value of **−6.68%**.

They also offered the alternative branch in advance — "if it is *not*
monotone, that is more interesting still, and it would mean removal is driven
by the election's choice rather than by averaging" — which is the branch the
measurement lands in.

### 34.1 This is not the test §33 ran

§33 measured `V_33` = peak **bright** ring residual over contrast, on the BLOB
region, and found it near-invariant to the gate. That does not settle this
claim. The orchestrator's prediction is stated in §25's statistic — veil
**depth**,

```
V = ( median profile over d in [2,22] - median profile over d in [80,120] )
    / median profile over d in [80,120]              (70-veil.py, verbatim)
```

— a signed **darkening**, on `ROI_LEG`, in linear DN. A statistic that
measures the absence of darkening and a statistic that measures a bright hump
are different quantities, and answering a claim in a statistic it was not made
in is a way of appearing to settle it without doing so. So §34 computes §25's
`V`.

### 34.2 The prediction is falsified by its own citation

The orchestrator reads **−6.68%** as a gate-4 number, the product of heavy
averaging. It is not. Verified at source two ways, because a fact row is a
compressed rendering and this report has already been wrong by trusting one:

1. §25.7 of this report tabulates the row as `| gate-0 merge | −6.6810% |`.
2. `70-veil.py` prints it as `merge (gate 0)` and computes it on
   `cache/bee3-leg-sel.npy`, the gate-0 elected merge.

So **74.76% of the veil was already removed at `n_eff` = 1, with zero
averaging.** The prediction that gate 0.00 should show little removal is
contradicted by the very measurement it cites.

There is more. §25's `C-RANDV` is the control that isolates the cause: a
uniformly random per-pixel election has the **same** per-pixel mixture
structure and an **uninformative** selector, and reads **−25.8547%** — inside
the single-frame range, no removal at all. §25 states the conclusion in as
many words: "A per-pixel mixture as such does nothing — it is this election."

§25 therefore already ran the orchestrator's causal experiment, in a
**stronger** form. The gate ladder varies averaging with the selector held
informative. `C-RANDV` varies selector informativeness with averaging held at
zero. The second isolates the mechanism; the first cannot, because both arms
retain an informative selector. Together they complete a 2x2, and this section
fills the one empty cell: an informative selector at `n_eff` = 55.

### 34.3 The ladder, in §25's statistic

Four registered branches on `dV` = `V`(0.00) − `V`(4.00), signed. The reversal
branch is not decoration: a bar without one has produced a wrong verdict three
times in this milestone's family, twice mine.

| gate | `n_eff` | `V` % | near DN | far DN |
| --- | --- | --- | --- | --- |
| 4.00 | 55.321 | **−14.9412** | 36519.0 | 42933.9 |
| 2.00 | 19.182 | **−14.1166** | 36494.5 | 42493.1 |
| 0.7078 | 3.000 | **−12.9745** | 36497.2 | 41938.5 |
| 0.00 | 1.000 | **−12.5949** | 36510.5 | 41771.6 |

`dV` = **+2.3463 pp** against a predicted **+19.79 pp**. That is **11.86%** of
the predicted swing, **and the sign is opposite to the prediction**: gate 0.00
is *less* veiled, not more. Branch: **B19-FLAT**.

Spearman rho(gate, `V`) = **−1.0000**. The ladder is perfectly monotone — but
in the direction where **more** averaging gives **more** veil, which is the
opposite of a removal mechanism. Monotonicity alone would have looked like
confirmation to a bar that did not check the sign.

### 34.4 The movement is in the reference, not in the veil

The branch understates the result. Look at the two operands separately. The
**near band** — the veiled band itself, the quantity the orchestrator's
mechanism requires to brighten — spans **0.0673%** across the whole ladder.
The **far reference** spans **2.7824%**, which is **41.4x** more.

Since `V` = near/far − 1, a ladder built on a moving reference reports a veil
change when nothing about the veil has changed. That is precisely the failure
the orchestrator self-reported in their own ring profile ("the reference
moved"), and they proposed the remedy: "Pinning the reference to one arm, or
measuring a shift-invariant quantity, are the two obvious routes." Route one,
applied:

| gate | `V` raw % | `V` pinned to gate 4.00 % |
| --- | --- | --- |
| 4.00 | −14.9412 | **−14.9412** |
| 2.00 | −14.1166 | **−14.9984** |
| 0.7078 | −12.9745 | **−14.9920** |
| 0.00 | −12.5949 | **−14.9610** |

Range over the ladder: **0.0572 pp**, which is **0.289%** of the predicted
swing. Branch: **B20-NEGLIGIBLE**.

The signed decomposition puts it beyond argument. It takes **no ratio of two
signed numbers**, because that is the exact construction that produced three
wrong verdicts here already:

| component | pp |
| --- | --- |
| `dV` total | **+2.3463** |
| near-only (the veiled band) | **−0.0198** |
| far-only (the reference) | **+2.3667** |
| cross | −0.0006 |
| closure &#124;sum − `dV`&#124; | 0.000e+00 |

Both positive attribution controls recover a plant whose true attribution I
chose: a 3% change planted on the near band alone is assigned **−2.5518 pp**
to near and **+0.0000 pp** to far; planted on the far band alone it is
assigned **+2.6307 pp** to far and **+0.0000 pp** to near.

### 34.5 Robustness: two regions, two channels

A result that holds only on the crop it was built on is not a result. The same
frozen-mask ladder, on `ROI_LEG` and on the **BLOB** region the orchestrator
filed as the flagship figure, in green and in mean-RGB:

| arm | region | channel | near span % | far span % | ratio | pinned range pp |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | ROI_LEG | mean | 0.1259 | 3.0482 | 24.2x | **0.1073** |
| A2 | BLOB | green | 0.1231 | 2.7969 | 22.7x | **0.1199** |
| A3 | BLOB | mean | 0.3071 | 2.9567 | 9.6x | **0.2993** |

Branch: **B22-ROBUST**. The far reference outruns the veiled band by between
9.6x and 24.2x in every combination.

One detail worth flagging rather than smoothing: on the BLOB region the
**raw** `V` crosses zero, running −2.6159% at gate 4.00 to +0.2311% at gate
0.00 — the band appears to flip from darker than the far field to brighter.
Pinned, it does not move at all (−2.6159% to −2.4960%). A sign flip in a
headline statistic, produced entirely by its denominator, is a good
illustration of why the orchestrator's instrument could not support their
claim and why mine would not have either without pinning.

### 34.6 The form of the drift, which decides whether it is a hazard

The orchestrator warned that any statistic normalised to a far window will
absorb their 2.14% far-field fall, and asked me to check rather than assume
that `E`-like statistics are immune. Checking, not assuming:

`V` is a ratio, so it is **exactly** invariant to `g` -> `a`·`g` and **not**
invariant to `g` -> `g` + `b`. Whether the drift is a hazard therefore depends
entirely on its form, which is measurable: a multiplicative drift moves the
dark subject by the same **percent** as the bright far field; an additive one
moves it by the same **DN**.

| quantity | gate 4.00 -> 0.00 |
| --- | --- |
| far field | −2.707% (−1162.3 DN) |
| dark subject | −0.086% (−6.1 DN) |
| percent mismatch | 2.621 pp |
| absolute mismatch | 1156.2 DN |

Verdict **NEITHER**. The drift is neither a gain nor an offset — it is
confined to the bright background, which is consistent with the orchestrator's
own account of it as unfitted per-frame photometric drift organised spatially
by the election. The consequence is specific: `V` survives a pure gain exactly
(`C-MULT` = 7.105e-15, bar 1e−12) but this **is not** a pure gain, so the
reference has to be pinned explicitly rather than assumed away. `C-ADD`
confirms the instrument is not merely dead to the hazard: a −918.8 DN offset
moves `V` by −0.3267 pp.

`C-POS` shows the instrument would have seen the orchestrator's effect if it
were there. Planting a known extra veil — multiplying the 2–22 px band by 0.90
— moves `V` from −14.9412% to −23.4471%, against an algebraically expected
−23.4471%, an error of **0.0000 pp**. That is a planted swing of 8.51 pp, the
same order as the 19.79 pp the orchestrator predicted, recovered with exact
calibration. A quiet instrument and a dead one are different claims and this
separates them.

`C-FROZEN` reports the same ladder with per-arm masks instead of one frozen
population: `dV` +2.3463 pp frozen against +2.1355 pp free. The verdict does
not depend on the freezing, which is worth knowing because freezing is my
repair of the orchestrator's first failure and it would be circular to let the
repair carry the conclusion.

### 34.7 The unmix question, answered again and differently

The orchestrator speculated that §13's **−28.2%** may have been "an unmix that
assumes the veil is present [...] fitting something the merge had largely
already taken out." The mechanism as stated is **refuted at source**, but the
intuition behind it is sound and this report already contains its measured
form. Both halves matter.

**Refuted:** the unmix does not operate on the merged output. `P107` and
`P132` record that the regression runs along the **frame** axis per pixel,
with 38.000 observations per population. It fits the frame cube, which is
**upstream** of the election. The merge's 74.76% removal happens downstream of
the fit and is invisible to it, so the fit cannot be confused by it.

**But the intuition lands, and `P88` already measured it.** The election
removes the dominant term and leaves a **~2.9% frame-borne veil** that no
selector-side fix can reach, because it is present in every observation. So
the *headroom* available to unmixing on real captures is genuinely small — not
because the unmix is fitting a ghost, but because the election got there first
and took the part that was reachable. The orchestrator reached the right
consequence through the wrong mechanism.

The routing answer from `P132` is unchanged: neither model nor support, but a
**structure-scale** limiter.

### 34.8 What this closes off

Fact 1375 excluded resampling: the veil is invariant across all three
resampler kernels. §27 excluded demosaic. §33 showed the bright-hump statistic
is near-invariant to the gate. §34 now shows the **darkening** statistic — the
one the mechanism is actually stated in — has a veiled band that moves
**0.0673%** across a **55.3x** change in frames averaged per pixel, in two
regions and two channels.

Averaging was the last cheap candidate mechanism. What remains is **selection
itself**, which is where §25's `C-RANDV` pointed before this section was
written: destroy the selector's information and the removal disappears; change
how many frames it averages over by a factor of 55 and nothing happens.

### 34.9 Verification and limits

`verify_s34.py` re-derives every figure above from the JSON operands and
re-hashes the gate-4.00 arm. `control_s34.py` mutates operands with the prose
untouched, to prove the harness re-derives rather than matching the document
against itself.

`control_s34.py` runs eleven arms and every operand mutation goes red:
perturbing a single near or far level by 500 DN fails 10 and 15 checks
respectively, relabelling a branch or a control verdict fails 2, and
relabelling §25.7's `gate-0 merge` row fails the source check. `N11` restores
everything and is green-expected, so the harness is not merely always red.

**`N10` caught me regressing a discipline this report had already closed at
`P113`, and that is worth more than the patch.** `verify_s34` passed 90 checks
on its first run. `N10` then altered **one of two** prose instances of a figure
and it stayed **green**, because I had written every prose assertion as
`figure in text`. That is presence-checking, and presence-checking is
instance-blind: a number wrong in one place and right in another passes. This
is not news to this document. `P105` measured the same blind spot in §28, and
`P113` recorded it **closed** at §29, where `verify_s29.py` started asserting
exact occurrence counts. Three sections later I rebuilt the defect from
scratch.

The repair is the one §29 already established -- exact counts, read off the
document by a reporting mode rather than guessed, every site annotated -- and
`N10` now goes red. The transferable part is not the defect but its return: **a
discipline closed in one section does not propagate to the next by itself.**
Only a per-section control catches the regression, which is an argument for
writing the controls even when the verifier looks clean, and especially
then.

**Appending this section also broke two verifiers that had been committed
green, and in both cases the number was right and the instrument was wrong.**
`verify_s33.py` sliced its scope as `raw[i:]` from the §33 heading to the end
of the file, despite a docstring stating it was scoped to §33 -- so §34's
legitimate citation of `55.321` raised a count from 2 to 3. That docstring
also forbids the repair that suggests itself: bumping the expectation "ends in
someone weakening it to a presence check". The defect was the missing end
delimiter, so §33 now terminates at the §34 heading, and every other count in
it is unchanged at the narrower scope. `verify_s34` had the same unterminated
slice and was correct only by being last; it now looks for a following
section and falls back to EOF.

**The defect then demonstrated itself.** My first attempt to check this fact
pinned the broken scope's reading at 3, and it immediately read 4 -- because
the paragraph you are reading cites the figure again, and the broken scope
swallows §34 too. So the literal 3 is recorded here as history, and what the
verifier actually enforces is an identity: the broken scope reads the correct
count plus however many times §34 quotes the number. A pinned literal in a
growing document is the same class of mistake as the unterminated slice.

`verify_s32` failed differently and by design. It re-counts M87's scripts from
disk rather than trusting `93-audit.json`, because `P124`'s safety argument --
that no measurement script passes the flag that would let a 40-frame sidecar
apply -- is a standing claim about the whole tree, not a snapshot. Tonight's
new scripts moved the measurement denominator from 97 to 104. **The zeros both
re-derived as zero**, so the claim itself survived intact; only its denominator
was stale. §32 already records this same mechanism catching me when I had
written "30 scripts" and there were 116. The running total is deliberately
kept at a **single** live site in §32, maintained by `fix_audit.py`, and is
not restated here: a second copy would be a second thing to go stale, and it
would collide with `verify_s32`'s own assertion that the figure appears
exactly once.

Two notes on how that was repaired, because both could have gone the other
way. Three of tonight's scripts do document harness work but do not match the
`append/verify/control/fix` prefix that `verify_s32` uses to exclude harness,
so they count as measurement scripts. I did **not** widen that filter: "0 of
N" is a stronger claim at larger N, and shrinking N to flatter my own number
is the failure mode this report exists to avoid. The refresh script itself
first landed in the measurement set and **its own assertion fired against it**
-- it quotes the flag in prose and in a regex -- which is precisely the false
positive the prefix filter was built for, so it was renamed to the harness
convention rather than exempted by a new rule.

The generalisation is worth more than either repair: **a later section is the
natural adversary of an earlier section's verifier.** A checker that passed
when it was written is not a checker that passes now, and neither of these
would have been caught by re-running only the section I was working on.

**A last check on the instrument that certified everything above.** Every
green reading in this milestone is `python <verifier> 2>&1 | Out-String`
followed by `$LASTEXITCODE`, and the pass criterion is **0** -- which is the
direction a lost exit code manufactures, so a genuine failure would read as a
pass. The rule I was given says `Out-String` is safe because it must drain the
stream. That rule had already been corrected once, so it was measured:
`exitcode_probe.ps1` runs six pipeline shapes against a process whose true
code is **1**, at 10, 200 and 5000 lines, each arm preceded by a `cmd /c
exit 0` pre-clear so that a failure to set reads 0 rather than the previous
arm's value, and `exitcode_repeat.ps1` repeats the whole thing 12 times.

**The shapes this report relies on never lost the code: 180 of 180
observations** of capture-first, `Out-String`, `Out-String -Width`,
`Select-Object -Last`, and the exact gate shape used tonight all reported the
true **1**, on runs where the trap demonstrably fired. So §29-§34's 599 checks
rest on a shape that was verified rather than assumed.

Two results worth passing back. First, **the trap reports −1, never 0**, on
`PSVersion 5.1.26100.9168` -- in every corrupted observation across all 12
runs. That matters for anyone re-testing it: a gate written `if ($code -ne 0)
{ throw }` *catches* the trap here, while a probe that looks specifically for
0 records a false INCONCLUSIVE. Mine did exactly that on its first run, and
only refused to certify because the positive control was written as a gate
rather than as a note.

Second, **the race framing is confirmed against the count framing by direct
observation**: across 12 identical runs the number of corrupted arms varied
**4 to 6 of 6**, and a `−First` arm at 10 lines read the true code in one run
and −1 in the next. Identical inputs disagreeing is what a race looks like;
no count model can produce it.

**My own error here, since it is the same class as `P139` and `P140`.** I
registered the positive control as `expect = 0`, which encoded the *value* the
orchestrator reported instead of the *property* under test -- that the
observed code differs from the true one. On a host that corrupts to −1 the
control could not fire, and the run came back `INCONCLUSIVE`. That is the
correct failure mode and it is the only reason the mistake was cheap, but the
expectation was inherited rather than derived, which is the habit this report
keeps finding in me.

**And the race framing I just certified is itself engine-scoped.** The rule
was corrected a second time -- deterministic on quota, no volume threshold,
`-First 51` over 50 objects safe -- which contradicts the run-to-run variation
above. Rather than pick an authority, the disagreement was measured as a 2x2:
engine (Windows PowerShell **5.1.26100.9168** against PowerShell **7.6.5**)
crossed with process style (child `-File` against dot-sourced in-process),
nine arms each, 40 repetitions, **1440 observations**.

**The engine is the whole variable and process style contributes nothing.** On
7.6.5 the strict quota model holds at **720 of 720** observations, in a child
and in-process alike. On 5.1 it holds at **587 of 720**, and fails in the same
**6 of 9** arms in both process styles. Quota is **necessary in both**: across
every arm the model predicts safe -- `-First 51` over 50 objects, and
`-Last 3` -- **0 of 320** observations lost the code.

That reconciles the two rules, but only by naming the 5.1 variation rather
than explaining it. The race account says the loss needs the short-circuit to
land while the native process is **still running**, and that is manipulable:
make the emitter sleep after its last line but before it exits. Four
predictions were registered before the data existed -- that on 5.1 the rate
rises with sleep and reaches 100%, that on 7.6.5 sleep changes nothing, and
that the non-quota arms stay at zero at every sleep, because a manipulation
that makes a *safe* shape start losing is not selective and would invalidate
the rest.

**All four held.** On 5.1, `-First 3` loses the code at **80.00% -> 96.67% ->
100.00%** at 5 lines and **75.00% -> 98.33% -> 100.00%** at 50 lines, for
sleeps of 0, 50 and 300 ms. On 7.6.5 it is 100.00% at every sleep.
The six negative-control arms lost **0 of 720**. So on 5.1 the loss is
quota-gated *and* racy, and forcing the process to still be running collapses
it onto exactly the determinism 7.6.5 shows unconditionally. Volume is a proxy
for the same thing and a poor one: pooled over both 5.1 styles the rate runs
**60.00%** at 5 lines, **82.50%** at 10, **77.50%** at 50, **76.25%** at 200
and **100.00%** at 5000 -- ordered at the extremes, flat and out of order in
the middle, which is why no volume threshold was ever going to be found.

**The operationally dangerous half of this is the value, not the rate.** 7.6.5
corrupts the code to exactly **0**; 5.1 corrupts it to **−1**. The guard
published with the rule, `if ($code -ne 0) { throw }`, therefore *catches* the
trap on 5.1 and is *guaranteed* to pass it silently on 7.6.5 -- and 7.6.5 is
the shell these milestones are driven from. The two engines fail in opposite
directions, so no single-host test can establish that a guard is safe, and the
gates in §29-§34 are safe for the stronger reason that they never form the
pipeline at all.

**What this costs me.** `P141`'s race clause was measured under `powershell
-File`, so it is true where it was taken and it is not retracted; but it was
written as a property of PowerShell when it is a property of 5.1, and it is
annotated in place. The same holds in the other direction for the rule I was
given: its quota table is correct in the shell it was measured in. Neither
reading was wrong about its own data. Both generalised one host to the
platform -- the same error, in the same week, from opposite sides, and the
only thing that separated them was crossing the factor instead of arguing
about it.

**A third verifier broke, and it changes what I think the defect is.**
Running the full suite after §34.9 grew, `verify_s29` -- green at its last
commit -- failed exactly one check: it counts the bolded rendering of its
full-coverage figure across the whole document and expects three sites, and
the engine ladder above quotes two unrelated rates of 100%.

That is three earlier verifiers broken by three successive appends, in three
different shapes: `verify_s33` sliced its scope to end-of-file, `verify_s32`
re-counted its denominator from disk, and now `verify_s29` counted a value
generic enough for a later sentence to reproduce by coincidence. **I had been
calling this a scope problem. It is not.** The property the three share is
that each check was keyed to a *value* rather than to a *site*, and a value is
not an identifier: 100% belongs to no section, so every sentence written after
it is a potential collision.

The repair binds each of the three real sites to an anchor that carries its
neighbouring text, which no future section reproduces by accident. It is also
strictly stronger than the total it replaced, and `control_s29` now
demonstrates that rather than asserting it. Two of the three sites are the
*same sentence*, differing only in whether the verdict word is emphasised, so
the new `N11` arm rewrites one into the other. The document is then left still
holding two sentences that quote the figure, and the old count of three would
have been unmoved -- while both anchors that can tell the sites apart go red,
one because it now matches twice and one because it no longer matches at all.

**The rate is the part worth keeping.** Three sections appended, three prior
verifiers broken, and not one of them would have been caught by re-running the
section being edited. A verifier is not something written once and committed
green; it is a standing claim that every later section is entitled to
falsify.

**ORCH's cache-contamination warning does not reach this report, and I
checked that in the Rust rather than by asserting it.** Fact 1446 measured an
identical `strehl stack` command line returning either of two hashes depending
on whether an unrelated `align --reference 40` ran first, because
`StackIdentity` covers the frame set but not `reference` and not `resampler`.
M87 was named explicitly, alongside every other milestone running an A/B.

The prescribed control is run the arm, perturb the cache, re-run the arm, and
compare. I did not make that the primary evidence, because for this report it
is the weakest thing available. **The first ground is that M87 never calls the
binary.** Every number in this document is computed in Python from cubes
decoded straight out of the `.ARW` files with `rawpy`; the merge in §25 is
*reproduced* from the frame cube and the selection map rather than read back
from a rendered TIFF. That is not an observation I made once -- `fix_audit.py`
asserts it on every run, and it currently reports 0 binary invocations across
104 measurement scripts.

**The second ground covers the one place I do consume a render.** The §33/§34
gate ladder runs on ORCH's four pinned TIFFs, and those were rendered with
`STREHL_WARPMAP` pointing at a fixed sidecar. `merge_cmd.rs:1135` documents
that path as resolving an explicitly named sidecar *instead of* the normal
discover-or-solve route, and the byte-freeze suite adds that when the variable
is set nothing is written anywhere and a bracket mismatch is refused rather
than silently re-solved. So those renders never enter the code path the defect
lives in. ORCH's own fact 1476 reaches the same exemption for M113 and M110 on
exactly this reasoning.

**What the hashes add, and what they cannot.** The gate-4.00 TIFF on disk
still hashes `E400A63A...7112`, which agrees with ORCH's provenance note, with
the digest §34 recorded at the moment it measured, and with fact 1373's
catmull-rom arm from a separate session and a separate exposure code path. The
four arms hash to four distinct values at one byte length. That is a four-way
agreement where the control asked for a two-way one -- but I want to be exact
about its limit: **if the cache had served the same wrong bytes on both
occasions, the hashes would agree just as well.** A repeated digest cannot
tell a correct render from a consistently stale one. Only the warpmap bypass
can, which is why the source read carries this and the hashes merely
corroborate it.

**And the warning is stale, which I would not have known from the row alone.**
Fact 1446 was measured before commit `69f7b4c`, an ancestor of HEAD; at HEAD
`solve_config_key` hashes `reference`, `spans`, `resampler` and every
`SOLVE_ENV` variable into the sidecar path, and a recorded resampler that
disagrees with the wanted one forces a re-solve. Both fields the warning names
as missing are now in the key. ORCH had already published that correction as
fact 1476 -- **the fleet-wide alarm and its own retraction were live in the
corpus at the same time**, which is the ordinary condition of a corpus a dozen
agents write concurrently, and the reason a warning is worth re-deriving even
when it arrives from the coordinator marked highest severity.

**Appending §34.9 broke a fourth verifier, and this one refutes the
diagnosis I gave three paragraphs ago.** P143 concluded that the shared cause
of three earlier breaks was keying a check to a *value* rather than to a
*site*. That was true of those three. It is not true of this one, and the
difference matters more than the count does.

Recording P144 required a new script, and classifying it moved the denominator
that P124's two zeros are quoted against. The classification rule -- which
filename prefixes mark a harness script rather than a measurement -- turned out
to be written in full four separate times: in the script that writes the audit,
in the two verifiers that re-derive it, and in the new probe itself. Changing
one copy moved the disk count to 105 while the JSON said 104, and both
verifiers went red.

**Neither of them was keyed to a value.** Both re-counted the scripts from
disk, which is exactly what I had asked them to do, and each counted correctly
under the rule it was holding. The failure was that they were no longer holding
the same rule as the script that wrote the number, and nothing in either
instrument could see that. A stale value fails loudly the moment the document
moves; a stale *rule* keeps producing a well-formed number, and the last
instrument to run looks authoritative.

The repair gives the split a single owner and has the other three import it.
That removes the drift -- and it also removes the evidence, which is the part
worth being careful about. Once the audit and its verifiers share one
definition they agree by construction, and their agreement is no longer a
measurement. So the consolidation is paired with a check that a shared constant
cannot satisfy: any script excluded as harness must genuinely measure nothing
about an image, and may not decode a raw or open a frame cube. The prefix is a
convention; that is the property the convention exists to stand for, and it is
now tested directly.

**The honest tally is four appends, four broken verifiers, and two distinct
causes.** I would rather record that the class I named was incomplete than
present a tidy one. The rate has not changed, but the claim that one diagnosis
explains it has.

Three limits, stated rather than buried.

**The absolute level is not commensurable with §25's −6.6810%.** My frozen
mask has an IoU of **59.19%** against the mask §25 derived from its own cached
merge (subject fraction 41.20% against 37.83%), so the two renders are not the
same registration. The orchestrator's arms are `--srgb` and I linearise them;
§25 worked in linear raw DN throughout. Every number in §34 is therefore a
**within-ladder** comparison, which is what the claim requires, and no
absolute level here should be quoted against §25's.

**The arms are unbinned.** The orchestrator's renders are 7032x4688, twice the
binned output §25's geometry is defined in. §34 crops at 2x, linearises, then
bins 2x2 to land on §25's 744x1144 geometry exactly. A first attempt cropped
`ROI_LEG` directly from the unbinned arm and was measuring the wrong physical
region; the probe that caught it is `99-probe.py`.

**`E(d)` is not run here.** `E(d)` references the frame ensemble rather than a
far window, so it needs the frames rendered through the same path as the arms.
The orchestrator's arms are merged sRGB TIFFs and the ensemble is not
available in that space, so an `E(d)` ladder would compare across two
pipelines. `V` is the statistic the prediction was stated in and it is the one
answered.

