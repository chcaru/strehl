# V-HEADTOHEAD — strehl against another stacker, for the first time

> ## RETRACTED IN PART — read this before any number below
>
> **This report's headline finding is withdrawn.** It concluded a *"real deficit
> of 17-27% at 3-5 px features"* and called that "the honest headline". Two
> later lanes have since shown that quantity is **undecidable in either
> direction** on this corpus, and it fails three separate ways:
>
> 1. **The instrument fails its own controls, five ways** — re-derived rather
>    than taken on trust by `V-HEADTOHEAD2`.
> 2. **The gap is a tone curve, not a resolution difference.** A curve fitted to
>    strehl's own pixels using **only 4x4 block averages** — a transform with
>    literally no information above 0.125 cyc/px — reproduces the comparator's
>    0.25-0.30 cyc/px band power to **0.02%** (0.037147 against 0.037138). The
>    comparators were fed TIFFs developed with `Contrast2012=+100`; that is not
>    a caveat on the result, it *is* the result.
> 3. **The band contains no signal.** `V-LINEAR` measured the
>    in-focus/defocused fine-band ratio on **linear** develops at **1.015,
>    1.043, 1.004, 1.138** across four frame pairs, against 2.1-3.0 on the
>    Lightroom develops. **0.20-0.48 cyc/px is a noise band on this corpus.**
>
> **This file is retained, not deleted**, so its numbers stay reproducible and
> the retraction stays auditable — the same treatment given every other refuted
> instrument here. Nothing below has been altered except this banner and the
> marker on the verdict row.
>
> The standing account is `docs/research/V-HEADTOHEAD2.md` and the README's
> *Measured against other stackers* section. **What survives from this report:**
> the noise and clipping wins, which need no registration between two renders
> and were never in question.

**Verifier:** V-HEADTOHEAD. **Subject:** the project's standing claim to be *state of the art*.
**Standing:** every quality number in this corpus before tonight is internal — strehl against
strehl, or strehl against its own input frames. This is the first comparison against software
someone else wrote. I wrote every instrument here from scratch under
`experiments/V-HEADTOHEAD/`. Nothing in `crates/` was touched.
**Artifacts:** instruments in `experiments/V-HEADTOHEAD/`, outputs in `C:\dev\strehl-out\V-HEADTOHEAD\`.

## Verdict

| # | Question | Answer |
|---|---|---|
| 1 | Is strehl sharper? | **RETRACTED — see the banner at the top of this file. This row is undecidable in either direction, not a loss.** Original text: *"No — mixed, and it loses where it matters most. Level at coarse scales, ahead ~6-8% at 10-20 px features, behind 17-23% at 3-5 px features against both comparators"* |
| 2 | Fewer artifacts? | **Yes, marginally, and neither stacker has an occlusion halo.** strehl's rim numbers are lower on all four measures; no median profile in either arm overshoots |
| 3 | Less noisy? | **Yes, decisively.** ~4.5x lower high-pass amplitude on flat defocused ground, and what remains is real structure rather than grain |
| 4 | What does the other one do better? | **Fine microcontrast at 0.20-0.40 cyc/px**, and it is *not* a sharpening artifact — the develop had `Sharpness=0` |

**Would a demanding macro photographer choose strehl's output at print size, on this subject?
Mixed, leaning yes** — for the coffee bean, because strehl does not blow 32% of the frame to
paper white and is visibly cleaner. But a photographer who prints large and looks for "bite"
at the pixel level will find the prior stacker's rendering crisper, and they will not be wrong.

**Is "state of the art" defensible tonight? No. It should be retracted.** Two independent
comparators — the owner's `focus-stack` fork and **Zerene Stacker PMax** — both put strehl
behind at the fine-detail scales, on different subjects, with tight confidence intervals.
strehl is *competitive*, and it wins clearly on noise and on not clipping. That is a real and
defensible claim. "State of the art" is not.

---

## 0. What was compared, and the confound that cannot be removed

| | Subject 1 — coffee bean | Subject 2 — frost |
|---|---|---|
| Comparator | `focus-stack` fork, `C:\dev\macro\out\coffee-bean\stack.tif` | **Zerene Stacker PMax**, `D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif` |
| strehl | `SHIP-V2\coffee-bean--SHIP-V2.tiff` (`.ok` sidecar present) | `SHIP-V2\113MSDCF--SHIP-V2.tiff` |
| Frames | **the same 105**, DSC00016-00120 | **the same 63**, DSC00001-00063 |
| Comparator input | Lightroom TIFFs, `Sharpness=0`, `Contrast2012=0`, `LuminanceSmoothing=0` | Lightroom TIFFs, `Sharpness=0`, `Contrast2012=+100`, no NR |
| strehl input | the raw ARWs | the raw ARWs |

**The confound, stated once and never softened:** both comparators were fed *Lightroom-developed*
TIFFs; strehl was fed *raw*. This is a pipeline comparison, not a merge-kernel comparison. I
checked the XMP sidecars precisely because the obvious way to lose this argument is to discover
afterwards that the other pipeline had capture sharpening switched on. **It did not**:
`crs:Sharpness="0"` on both subjects. The comparators' fine-detail advantage is therefore *not*
an unsharp mask, and I cannot explain it away.

A third pairing — the marker-stroke board, prior `stack_v3.tif` vs strehl `109MSDCF` — was
**abandoned**: those are different captures (63 frames on 2026-05-07 vs 22 on 2026-05-17) and
registration failed outright (phase-correlation peak 0.0277, no maximum in a scale sweep from
0.90 to 1.12). It is recorded here as abandoned rather than quietly dropped.

## 1. Making the two images comparable without cheating

**Geometry.** strehl's raster is **3.5063%** larger than the prior's (rotation +0.031°,
translation +14.78/+5.06 px, similarity residual rms 2.18 px over 44 tiles). This matches
strehl's own log: field of view cropped to 0.9653 of the sensor, then upsampled to keep the
output dimensions. **A pure integer shift is globally unsatisfiable** — forcing one leaves a
residual of 36.6 px rms, 78.5 px max.

The standing integer-only-shift rule exists so that no resampling blur is added to the quantity
being measured. I honoured it by **never resampling either arm**: each arm reads its own integer
box covering the same scene area, and every frequency band is defined in *scene* units and read
at `f/scale` in each arm's own grid. Nothing is interpolated, anywhere, in any reported number.

**Tone.** The prior emits **linear Rec.2020**; strehl emits a full viewing render (tone gain,
sRGB transfer, then a display-space S-curve at strength 0.550). I inverted strehl's chain
exactly from `image_out.rs` and then *tested the inversion falsifiably*: if strehl is correctly
linearised and the prior is truly linear, colocated pixels must lie on a straight line through
the origin.

| | as shipped | tone-inverted |
|---|---|---|
| Adding a quadratic term | residual 0.0788 -> 0.0419 (**helps a lot**) | 0.04795 -> 0.04827 (**makes it worse**) |
| Decile bias | ±0.236 | **±0.028** (8.3x reduction) |
| Best-fit gamma | 1.80 | **1.08** (gamma=1 only 0.8% worse) |

Both the inversion and the prior's linearity are confirmed, not assumed.

## 2. Proving the instrument before trusting it — including two failures

Every comparison ran through one `Arm` abstraction with four arms: **real**, **null** (a clone),
**positive** (a known blur), and a **non-degenerate scale confound** that applies strehl's *exact*
geometric operation (crop to 1/1.035, Catmull-Rom upsample) to the *prior* arm, to measure what
that operation manufactures on its own.

**Null control returns exact parity** — all six bands 1.000, max profile difference 0.0.

**The scale confound is not cosmetic.** strehl's own 3.5% upscale destroys **8.9%** of the
0.30-0.40 band and **31.4%** of 0.40-0.48, measured on the prior arm. Any strehl deficit at the
top must be discounted by this; any surplus is understated.

**Detection threshold.** A 0.3 px Gaussian is detected (0.995/0.986/0.975 in the upper bands,
CI width 0.001); a 0.2 px Gaussian is not (1.000 everywhere). "No difference" below ~0.3 px of
equivalent blur is beyond this instrument's reach and is not claimed.

### Three instruments failed their own controls and were discarded

1. **`rise10_90` at the bean silhouette.** A 0.8 px Gaussian moved it by 1.002, CI [-0.71, +1.39].
   The bean edge is a ~40 px shading ramp, not a knife edge, so the metric has **no power**.
   The real-arm value (0.723) is *not* quoted as sharpness anywhere.
2. **Rim instrument v1.** Normalising every gradient-maximum profile by its end plateaus returned
   **+428% bright rim on a clean image** — coffee-bean detail is thin *lines*, so the denominator
   goes to zero. It was measuring its own denominator.
3. **Rim instrument v2.** Taking the rim *of the median profile* smeared it away: a real Lightroom
   USM(40, r=1.0) moved it by **+0.02%**. No power.

Only v3 — per-edge shoulder excursions, median across edges — passed, and its sensitivity floor
is stated in §4 rather than hidden.

## 3. Sharpness: the number, with the grade removed

**The naive answer is wrong and would have flattered the prior stacker.** Band contrast variance
puts strehl at ~0.5 of the prior *flat across two decades of scale* (0.534/0.570/0.585/0.461/
0.438/0.544). A scale-independent ratio cannot be resolution. `grade.py` measured the
non-parametric transfer curve on 16x/24x **box** downsamples and found that over the bean's tonal
range the prior's local slope exceeds the level ratio by a median factor of **1.281**. That alone
predicts a contrast-variance ratio of 1/1.281² = **0.610**; the measured whole-spectrum ratio is
**0.556**. **The contrast gap is a grade, not sharpness.** Pushing the prior *forward* through
strehl's tone chain instead (re-choosing, not re-computing) gives the same flat pattern, so it is
a property of the images and not of the direction of my transform.

Since Lightroom's sliders were all zero, the most likely source is the camera profile's base tone
curve, which Lightroom applies regardless of slider state. I did not prove that and do not need
to: the fix is to normalise it away.

**The sharpness statistic is therefore each arm's spectrum normalised by its own 0.02-0.05 band** —
any scalar grade cancels exactly and only the *shape* survives.

### Subject 1 — coffee bean, 626 ROIs, prior = 1.000

| band (cyc/prior px) | feature size | strehl/prior | 95% CI | after discounting strehl's own upscale |
|---|---|---|---|---|
| 0.05-0.10 | 10-20 px | **1.063** | [1.004, 1.128] | 1.063 |
| 0.10-0.20 | 5-10 px | 1.079 | [0.990, 1.179] | 1.081 |
| 0.20-0.30 | 3.3-5 px | **0.833** | [0.757, 0.915] | 0.847 |
| 0.30-0.40 | 2.5-3.3 px | **0.766** | [0.699, 0.839] | 0.841 |
| 0.40-0.48 | 2.1-2.5 px | 1.060 | [0.983, 1.143] | 1.542 (unreliable — noise-dominated) |

### Subject 2 — frost, 576 ROIs, Zerene PMax = 1.000

This one nearly produced a false headline, and the correction is the most useful thing in this
report. Untone-matched, the comparison read **0.796 / 0.553 / 0.349 / 0.896 / 2.218** — strehl
catastrophically softer. Then I looked at the crops and they showed the *opposite*, so one of the
two was lying.

Both were. My per-panel percentile stretch was not a tone match (it equalises two endpoints, not
the curve between them), and with medians of 0.046 vs 0.214 it pushed Zerene's background to black
and manufactured the impression that strehl resolved more. And the shape statistic's
"grade cancels" assumption needs the tone difference to act as a *local scalar*, which a transfer
curve that different does not. I hypothesised black clipping and **refuted it** (fraction of green
pixels at or below 0.01: 1e-5 Zerene, 0 strehl — nothing is crushed).

The correct control is **histogram matching**: a monotone pointwise remap cannot create or destroy
spatial detail, only equalise the transfer curve. With it:

| band | strehl/Zerene, tone-matched | 95% CI |
|---|---|---|
| 0.05-0.10 | **1.007** | [0.990, 1.025] |
| 0.10-0.20 | 0.936 | [0.913, 0.959] |
| 0.20-0.30 | **0.735** | [0.712, 0.760] |
| 0.30-0.40 | 0.843 | [0.798, 0.892] |
| 0.40-0.48 | 1.511 | [1.426, 1.600] — almost certainly noise (+2.34 stop push) |

**Two independent comparators, two different subjects, the same verdict: parity at coarse scales,
a real deficit of 17-27% at 3-5 px features.** That is the honest headline and it is not the one
this project wanted.

*Caveat that runs the other way:* PMax is Zerene's maximum-detail mode, which its own
documentation says raises contrast and noise relative to DMap. No DMap render exists here. Some
of Zerene's 0.20-0.30 advantage may be contrast enhancement rather than resolution.

### And the look

Tone-matched at 1:1, the two frost renders are **very close**; Zerene's filaments are marginally
more separated. On the bean, the prior reads grittier and crunchier and strehl smoother and
creamier — and a good part of what reads as "more detail" in the prior is, on inspection of the
high-pass residual, grain (§5).

## 4. Occlusion halos — the owner's headline complaint

Rim instrument v3, per-edge shoulder excursion, median over edges, in units of the edge step.
Clipped ROIs are excluded throughout: **the prior's background is 32% blown to white** and a
clipped plateau cannot overshoot, so leaving it in would have handed the prior a free win.

| arm | bright rim | dark rim |
|---|---|---|
| **PRIOR** (focus-stack fork) | +2.46% | +1.57% |
| **STREHL** (SHIP-V2) | **+1.30%** | **-0.55%** |
| prior + USM(40, r=1.0) | +2.10% | +1.92% |
| prior + USM(100, r=2.0) | +5.76% | +6.94% |
| prior + Catmull-Rom upscale | +19.05% | +2.04% |

**Neither stacker's median edge profile exceeds 1.0 anywhere. There is no occlusion halo in
either arm on this subject.** strehl is lower on all four measures. The independent
silhouette-profile harness agrees: no overshoot above 1.0 or undershoot below 0.0 in either arm,
with strehl's transition tighter through the boundary (-0.04 inside at -15 px, +0.06 outside at
0-8 px), i.e. less foreground/background bleed.

**Sensitivity floor, stated plainly:** this instrument detects a strong halo (USM 100/r2) and
detects Catmull-Rom ringing loudly, but it does **not** detect a Lightroom-default USM(40, r=1.0).
So the finding is "no halo above roughly strong-unsharp-mask strength", not "no halo at all".

The scale-confound row is the one to worry about in future work: **resampling alone manufactures a
+19% rim**. Had strehl shown a rim, it could not have been attributed to the merge.

## 5. Noise — strehl's thesis, tested

On flat, defocus-free paper at matched tone, high-pass rms:

| region | prior | strehl | ratio |
|---|---|---|---|
| **flat defocused paper** | 0.5025% | **0.1125%** | **0.224** |
| bean surface | 26.29% | 20.70% | 0.787 |
| in-focus paper | 5.008% | 4.502% | 0.899 |

And the picture is unambiguous where the number could be argued with: the prior's residual on
flat paper is **pure salt-and-pepper grain**; strehl's is **real structure** — dust specks, a
diagonal band, blobs. strehl is ~4.5x quieter in amplitude *and* a larger share of what remains
is signal, so its true noise advantage is larger than 4.5x.

This is not grade-corrected — the transfer slope at paper tones is poorly determined (12 flat ROIs
across a tiny shading range gave an implausible 0.53). Conservative bound: the grade factor never
exceeded ~1.9 anywhere measured, so **at least 2.4x survives the worst case**.
**strehl's estimation-not-selection thesis is supported.**

## 6. What the other stackers do better

1. **Fine microcontrast, 0.20-0.40 cyc/px.** 17-23% against the fork, 16-27% against Zerene.
   Both comparators, both subjects, tight CIs. **Not** an unsharp mask — `Sharpness=0` on both.
   About half of the deficit against the fork is explained by strehl's own 3.5% coverage upscale;
   the rest is the merge. A contributing design difference: the fork aligns with
   `cv::INTER_LANCZOS4` (`task_align.cc:833`), strehl with Catmull-Rom, and Lanczos-4 preserves
   more energy near Nyquist.
2. **Absolute high-frequency amplitude on the subject** — the prior carries ~27% more.
3. **The rendered look.** The prior's 1.281x local-contrast excess is a grade, but many
   photographers will simply prefer it, and "it's only a grade" is not an answer to that.

Against these, strehl's wins are: no clipping (**the prior blows 32% of the frame**; strehl's
clipped fraction is 4e-6), background texture retained rather than blown, ~4.5x less noise,
lower rim numbers, and a tighter occluding boundary.

## 7. What remains unproven

- The residual after grade correction (0.556/0.610 = 0.91) is unattributed.
- The 0.40-0.48 band is noise-dominated in both comparisons; the 1.51 and 1.54 figures are not
  evidence of resolution.
- The Lightroom-vs-raw develop step is a confound in both subjects and cannot be removed without
  re-developing, which would change the comparator the owner actually used.
- One subject has a matched-frame comparison against the fork; one against Zerene. Two subjects,
  two comparators. **That is a floor under "competitive", not a foundation for "state of the art".**
- Zerene DMap was never rendered; only PMax was available.
