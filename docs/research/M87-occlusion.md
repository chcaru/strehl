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
> **0.06804 [0.05981, 0.07982]**. The artifact is **79× the worst single frame
> and ~2600 SE above the frame null**. It is manufactured in the merge. The
> two-layer veil is what makes the *selector* go wrong, and it is what makes the
> defect irreducible — see the next line — but nothing in any single exposure
> looks like the rim you see in the output.
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
> **On the real bee, no: +3.7% with a global depth, −28.2% with a per-pixel
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

---

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

**MEASURED**, `bee-3-cpl` `ROI_LEG`: ISO **0.06550** (+3.7%, *worse*), median
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

**DERIVED.** Per-pixel depth turns a +3.7% into a −28.2% and lifts explained
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
| **P1** | **The occlusion halo is manufactured by the merge, not photographed.** All 299 single frames of `bee-3-cpl` score **0.000026 ± 0.0000073** (SE; sd 0.000126, max 0.000861, 94.3% exactly 0) on an edge-normal isotonic-residual metric; their merge scores **0.06804** [0.05981, 0.07982] over 6103 profiles — **79× the worst frame** | The defect is entirely inside the selector's decision rule. Any remedy is a change to how a frame is chosen or to what is reconstructed, never to capture | M87 (MEASURED) |
| **P2** | **Fact 1145's gate invariance holds under a metric with a measured null**: gate 0 **0.06804** [0.05981, 0.07982] vs gate 2 **0.06843** [0.05924, 0.08120] | Fold into 1145; it discharges that fact's own *"if this holds under a real metric"* clause | M87 (MEASURED) |
| **P3** | **The rim is a rank seam.** The elected value sits at percentile **0.675** of its own through-focus distribution in the near band and **0.429** far away; median \|k−k_F\| is **32** near and **96** far | The band is estimated max-like and the far field median-like. Explains the sign: a dark occluder yields a bright rim, and a bright subject on a dark background should yield a **dark** one — a cheap falsifiable capture | M87 (MEASURED + DERIVED) |
| **P4** | **The rim is part window and part veil, and the split is measured.** Rim width scales with the focus operator support (**30/30/34/46/64 px** at supports 5/8/21/41/65) and the yoked fraction scales **0.155→0.615**, but ISO falls only **9%** from support 21 to support 5 | Shrinking the focus window cannot remove it. A residual survives at a support too small to straddle the edge, and that residual is two-layer veiling | M87 (MEASURED; pre-registered discriminator, prediction committed before the run) |
| **P5** | **A halo metric cannot certify a reconstruction.** On a plant with known ground truth, three of four deliberately broken unmixings still improved ISO by 77–85%, including one wrong by **six orders of magnitude** in RMSE | Never optimise a reconstruction against a halo metric, and never certify an occlusion arm on it. Every arm needs a ground-truth control | M87 (MEASURED) — **the most transferable result here** |
| **P6** | **The mode-partition remedy is cosmetic and damaging.** On ground truth it removes **79.8%** of the halo while raising band RMSE **3.46% → 12.28% of level (+254.6%)**; on a non-occluding control it removes **63.9%** while raising band RMSE **+558.4%** | Fact 412's remedy works on the artifact and not on the picture. If it ships, it ships labelled cosmetic. **This partially retires fact 412's "try the cheap remedy first" as a *quality* recommendation** — it is a good diagnostic and a bad fix | M87 (MEASURED) |
| **P7** | **Two-layer unmixing is correct where it can be checked.** On the same plant it removes **78.8%** of the halo and takes band RMSE **3.46% → 1.82%**, the far-field noise floor (0.0180) | The owner's model is the right physics and the right target. It is the only arm measured to make the picture more correct | M87 (MEASURED) |
| **P8** | **But it does not yet work on real captures.** `bee-3-cpl` `ROI_LEG`: **+3.7%** with a global depth (median band R² 0.131, coverage 12.5%); **−28.2%** with a per-pixel depth (R² 0.200, coverage 19.8%), against a registered −50% bar | Depth resolution is worth ~30 points and is necessary; it is not sufficient. Ranked remaining causes: semi-transparent hair fringe, non-constant F(x), no alignment | M87 (MEASURED) |
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
   `distance_transform_edt(return_indices=True)` equivalent. Worth ~30 points of
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
> measured that two-layer unmixing fails on real captures (+3.7% / −28.2%
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
| → scaled to `ROI_LEG` radius (984/2113) | **6.32 px** (~12.6 px p-p) | DERIVED |

**Two independent instruments agree on the drift to 12.6%**, which is what
licenses using either. The residual lands in the ladder's flat region, giving
the **91.7%** predicted removal against the **6.6%** measured.

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
| P42 | **Three drift figures for `bee-3-cpl` disagree, and the aligner's own fitted warps sit between them.** Decoding the 299 placed warps (`z' = a z + b`, f64 bit patterns) gives scale `\|a\| = 0.92241` at frame 298 (a **7.76%** shrink) and a **maximum corner displacement of 351.4 px** in the binned 3516x2344 plane = **702.8 px** at full sensor. `main.rs:72` states 232.7 px; the orchestrator measured 603 px full-sensor at scale 0.85715. Under a matched half-diagonal convention the fitted warps give 327.9 px full against the orchestrator's 603 px, a factor **1.84**. | Someone is wrong about the magnification sweep by roughly 2x, and `main.rs` and the orchestrator err in **opposite directions** from the shipped aligner. This is M86/M97's to adjudicate, not M87's, but it should not stay unresolved: it is the number the aligner is judged by. | MEASURED |
| P43 | **M87's registration negative is robust to P42.** The verdict rests on the measured alignment switch (ISO 0.06805 -> 0.06356, **6.6%** removal, overlapping CIs) and not on any drift magnitude. A *larger* true drift strengthens the drift hypothesis' prediction that alignment should remove the halo, so P42 can only make the observed 6.6% **more** discrepant, never less. | The 2x drift disagreement cannot rescue the registration hypothesis. No re-measurement after M97 is required before accepting §15. | DERIVED |
| P44 | **The lint failure reported against this file did not exist at `HEAD`.** The quoted S6 row (`ratio \|E\|/\|E_fwd\|`, line 886 not 845) has been escaped since commit `c24e347`, two commits before the shipping commit. `scripts/corpus_lint.py` exits **0**, and an independently written table checker agrees at **0 S6 / 0 S1 over 30 tables** — after a positive control in which a planted unescaped span and a planted extra cell both fired. | A stale lint result was attributed to a milestone by file. Attribution by file is sound only against a current run; re-run before attributing. | MEASURED |

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
