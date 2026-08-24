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
> and binning — so **none of those is the cause**. And the shipped
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
