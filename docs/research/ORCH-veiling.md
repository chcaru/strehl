# ORCH-veiling — the merge loses to its own inputs on depth-separated subjects

Status: MEASURED. Author: orchestrator. Binary: pinned `859edac` (`DF209CE0…`).
All measurements linear (`--demosaic`, **no** `--srgb`), full resolution, on renders
produced for this investigation. Raw artifacts: `C:\dev\strehl-out\ORCH-rim\`.

## Summary

On a subject with real depth separation, the merged render is **darker than every
single frame of its own bracket** across a wide band around the subject. At
`d=120–200 px` from the silhouette the merge sits at **−4066 DN** while frame 102
alone sits at **−247 DN** — a single mid-stack frame is **16× cleaner** than the
merged output on that band.

This is not a halo in the usual sense. It is an estimator losing to one of its own
inputs, which violates the project's "never worse than a single frame" invariant.
It is the largest measured defect in the current renders.

## Method

`flower-bud-alone-cpl`, 205 frames. Chosen because it has a large **featureless
white backdrop**. A featureless field cannot be changed by defocus — there is nothing
in it to blur — so the backdrop is genuinely identical in every frame, and any
backdrop difference between arms is produced by the merge. The scene cancels by
construction rather than by argument.

Frame 102 is the merge's own alignment reference, so its warp is identity in both the
merge and the `STREHL_ONLY_FRAME=102` arm; the two arms share a geometry.

Every profile is expressed as excess over **that image's own** far field, so exposure
differences between arms cannot manufacture an effect.

## The two defects

Merge minus single-frame reference, linear DN, backdrop ≈ 18800 DN:

| d (px) | 2 | 6 | 12 | 14 | 40 | 80 | 117 | 200 | 260 | 320 |
|---|---|---|---|---|---|---|---|---|---|---|
| merge − frame | +359 | **+984** | +332 | −48 | −2859 | −3860 | **−4293** | −3049 | −1029 | −144 |

1. **Bright rim** — peak **+984 DN at d=6 px**, dead by d≈13 px.
2. **Dark aura** — peak **−4293 DN at d=117 px = 22.8% of backdrop**, reaching
   d≈300 px. Four times larger and twenty times wider than the rim.

`WINDOW_RADIUS` is 13, `SOBEL_RADIUS` 1, `GUIDE_RADIUS` 4, regulariser 17×17.
**No support radius in the selection path is within an order of magnitude of 117 px**,
so defect 2 cannot originate in the winner field and cannot be fixed by adjusting it.

### Controls

- **Instrument is quiet.** Subject-free corner of the same frame: max deviation
  **33 DN against 4293 DN**, a margin of **130×**.
- **Not vignetting-with-scale.** Binning jointly on silhouette distance and image
  radius (the bud is 372 px off-centre, so the fields separate): in the d=60–300 band
  the spread *across image radius* collapses to 1037–2162 DN while the spread *down
  silhouette distance* stays 3463–7916 DN. The aura follows the silhouette.
- **Not tone.** Measured in linear. The display render shows the same two features;
  tone amplifies the rim ≈4× (+984 DN linear → +3748 DN tone-mapped).

## Mechanism

### The naive form is refuted

Within-image dose–response on `109MSDCF` (paint strokes of differing luminance on one
white backdrop — one exposure, one lighting setup, one alignment solve, so only the
subject's brightness varies):

| stroke | deficit below backdrop | aura peak |
|---|---|---|
| dark (0.14 B) | 7983 DN | **−177 DN**, dead by d=60 |
| mid (0.43 B) | 5247 DN | +9 DN |
| bright (0.67 B) | 3045 DN | +33 DN |

A very dark subject on a bright backdrop produced **1.9%, confined inside 60 px** —
against flower-bud's 22.8% reaching 300 px. "Dark subject contaminates bright
backdrop" predicts a large aura here and there is none. **Refuted.**

The variable `109MSDCF` lacks is **depth separation**: it is paint on paper.

### The supported form

Raw backdrop luminance vs distance, each image normalised to its own far field:

| image | d4–12 | d12–30 | d30–60 | d60–120 | d120–200 | d200–300 | d300–420 |
|---|---|---|---|---|---|---|---|
| frame000 (near end) | −10306 | −9619 | −8387 | −6311 | −3572 | −1149 | −267 |
| frame102 (middle) | −5179 | −2499 | −1110 | −539 | **−247** | −177 | −116 |
| frame204 (far end) | −4604 | −3668 | −2411 | −1249 | −388 | −211 | −140 |
| **MERGE** | −4631 | −3825 | −4318 | −4692 | **−4066** | −1623 | −289 |

1. **The veiling is real light, really recorded.** `frame000` is darkened **−10306 DN
   at d=4–12 and still −1149 DN at d=200–300** — one exposure, no election. A heavily
   defocused dark subject genuinely spills its blur hundreds of pixels onto the
   backdrop. This is the positive control, and it explains an extent no 13-px window
   could produce.
2. **The merge is worse than its own inputs.** At d=120–200 and d=200–300 the merge is
   darker than *every* frame sampled, so it is admitting frames more veiled than any
   of the three.

### Why no existing gate catches it

The veiled samples are **not noisy**. They are smooth, coherent, and consistent across
long runs of frames. A gate calibrated on σ sees a tight mutually-agreeing cluster and
reads it as signal. On a deep bracket the veiled population may be the *majority*, so
a robust estimator that trusts the majority is also wrong. This defect is invisible to
every gate currently in the pipeline, which is why prior measurement never found it.

## Fix direction

At a backdrop pixel near an elevated subject two criteria compete, and the pipeline
answers the wrong one:

- *maximum local sharpness* → a frame where the backdrop is sharp, which is a frame
  where the **subject is defocused and therefore veiling this pixel**;
- *minimum veiling* → a frame where the **subject is sharp**, because a sharp subject
  does not spill.

Where the backdrop is featureless its sharpness carries no information, so the choice
is unambiguous and is currently made backwards.

Veiling by a dark subject can only *darken* a bright backdrop, so the unveiled value is
recoverable as an **upper envelope across frames** — a high per-pixel percentile rather
than a gated mean — within the band where veiling is detected. Stated generally, to
cover a bright subject on a dark backdrop: **reject samples displaced toward the
neighbouring subject's luminance.** This is the per-tile, per-frame, noise-normalised
outlier mask against the running estimate that the project has listed as missing.

### Acceptance criteria

- **Target:** `flower-bud-alone-cpl`, d=120–200 px. Floor to beat is **−247 DN**, what
  frame 102 alone achieves. Worse than a single frame on that band is failure by
  definition.
- **Placebo:** `109MSDCF` must be close to a no-op (aura is already only −177 DN).
  A fix that moves it materially is acting on something other than veiling.
- Report the rim and the aura **separately** — they have opposite signs, and a single
  combined score would let an arm that trades one for the other look like progress.

## Second subject — confirmed, smaller, and it explains the earlier contradiction

`flower-inner-edge-cpl`, 299 frames, merge reference 149. The middle frame is the arm
the original `STREHL_ONLY_FRAME` comparison lacked; it used `frame000` and `frame298`.

| image | d4–12 | d12–30 | d30–60 | d60–120 | d120–200 | d200–300 | d300–420 |
|---|---|---|---|---|---|---|---|
| frame000 (end) | −14067 | −12114 | −11222 | −9470 | −7370 | −5557 | −3697 |
| frame149 (middle) | −14139 | −12412 | −11476 | −9078 | −7212 | −5477 | −2977 |
| **MERGE** | −14852 | −14087 | −13370 | −12299 | −10478 | −8029 | −6204 |
| merge / middle | 1.1× | 1.1× | 1.2× | 1.4× | 1.5× | 1.5× | **2.1×** |

Two honest points:

- **On this subject the end and middle frames genuinely agree** (−7370 vs −7212 at
  d=120–200), unlike flower-bud where they differ 14×. The original test's
  "superimposed within noise" reading was therefore a true observation *about this
  stack*; end-frame choice was not the whole story.
- **The merge is nevertheless darker than every frame**, by 1.1× rising monotonically
  to 2.1×. The invariant violation reproduces.

The effect is far smaller here (2.1× vs 16×) because this subject's mask covers **73%
of the frame**, leaving little clean backdrop and contaminating the far-field
reference. **The defect is largest where a depth-separated subject sits against a large
clean backdrop** — which describes most portfolio subjects, including all three bees.

## The rim and the aura are one phenomenon

Consider a background pixel beside a dark, depth-separated structure:

- **d < ~14 px** — the focus window still contains the subject edge, so the election
  locks onto it and picks the frame where the **subject is sharp**, which is the frame
  where it spills *least*. The pixel comes out **less veiled than its surroundings**.
- **d > ~30 px** — the window no longer contains the subject, the election has nothing
  to lock onto, and the gated average dominates, admitting the many frames where the
  subject is defocused and veiling. The pixel comes out **heavily veiled**.

**The bright rim is therefore not something added at the edge. It is the one band that
is nearly correct, standing against a surround that is wrongly dark.** This explains
why attacking the rim directly has repeatedly failed or cost texture: that band is the
closest thing to a correct value in the neighbourhood.

Consequence for effort allocation:

- **d < 14 px is genuinely information-absent.** On flower-bud every arm is deep in the
  hole there (merge −4631, frame102 −5179, frame000 −10306, far field 0). No frame is
  clean. Reconstruction is the only route.
- **d = 30–300 px is information-*discarded*, not absent.** A clean sample exists
  (−247 DN) and the merge produces −4066 DN. **Fixing the surround requires no
  reconstruction** — and once the surround rises to where the middle frame already is,
  the *step* that reads as a rim disappears without the rim band being touched.

## The fix, proven before it was built

Taking the three existing single-frame renders, normalising all three to a **common
far-field level first** (so per-frame exposure drift cannot masquerade as "less
veiled"), and taking the per-pixel **maximum**:

| estimator | d4–12 | d12–30 | d30–60 | d60–120 | d120–200 | d200–300 |
|---|---|---|---|---|---|---|
| MERGE (205 frames, gated) | −4631 | −3825 | −4318 | −4692 | −4066 | −1623 |
| best single frame (102) | −5179 | −2499 | −1110 | −539 | −247 | −177 |
| **upper envelope of just 3** | **−3340** | **−1887** | **−899** | **−347** | **−211** | **−129** |
| gain over merge | 1.4× | 2.0× | **4.8×** | **13.5×** | **19.3×** | **12.6×** |

**Three samples out of 205 recover essentially the entire aura**, and the envelope
beats even the best single frame at every distance, because different frames are
least-veiled in different places and a per-pixel max picks the winner locally. A merge
with 205 frames to choose from can only do better.

At d=4–12 the envelope improves matters (−3340, against −5179 for the best single
frame) but does **not** reach zero — confirming that band as genuinely
information-absent. **The envelope solves d>15 px; reconstruction is needed only for
d<14 px. The split is measured, not assumed.**

Implementation notes that fall out of the measurement:

1. **Normalise to a common level before comparing samples**, or per-frame exposure
   drift enters the envelope directly.
2. **A raw max is biased high by noise** — `E[max of n]` grows like `sqrt(2 ln n)`.
   With 205 frames this is not negligible; use a high percentile or trimmed upper mean
   and debias it.

Caveats: the single-frame renders are **not co-registered** (`STREHL_ONLY_FRAME`
changes the stack digest, so the sidecar is rejected and alignment re-solves per
frame), so the two near-silhouette bins are indicative and the d≥30 bins are sound.
Three samples is a deliberately weak envelope chosen because it cost nothing; it is a
lower bound on what 205 can achieve.

## Caveat on a related number

Raw focus breathing across this bracket measures **13.7%** linear magnification
(subject area 24.63% → 18.33% of frame, monotone with frame index, which rules out
blur-driven mask growth since blur would enlarge *both* ends).

**This is the unaligned figure and does not demonstrate an alignment failure.**
`STREHL_ONLY_FRAME` reduces the stack to one frame, changing its digest, so the sidecar
is rejected and alignment re-solves with that frame as its own reference. Measuring the
post-alignment sweep requires instrumenting the merge from inside. Noted because the
merge log states the held-out score "cannot detect a scale error common to every edge",
which is exactly the shape a systematic breathing under-correction would take.

## The fix as I specified it is WRONG, and a real subject proves it

Every subject in the evidence above — `flower-bud-alone-cpl`, `flower-inner-edge-cpl`,
and the `109MSDCF` negative — is a **dark subject on a bright backdrop**. There, veiling
pushes background pixels down and a per-pixel **upper** envelope is right by
construction. I specified the fix from that set and did not notice the set was
one-sided.

The two-layer model makes the direction a property of the *subject*, not of the defect:

```
I_k(p) = a_k · (F ⊛ PSF_k)(p)  +  (1 − a_k) · (B ⊛ PSF_k)(p)
```

so a **bright** foreground over a **dark** backdrop must veil *upward*, and an upper
envelope would then select the **most-veiled** sample at every pixel — not a failure to
fix the defect but a machine for maximising it.

### Finding the missing case

Classifying all 26 subjects by border-versus-centre luma (`polarity.py`) gives 14
dark-on-bright, 8 low-contrast, and **4 bright-on-dark**, of which two are deep enough
to show the defect: `pencil-steep-angle-cpl` (299 frames, backdrop 0.369, subject 0.686)
and `pencil-flatter-angle-cpl` (299 frames, +0.141). The steep one was rendered in the
same four arms as `flower-bud`: frames 000 / 149 / 298 and the merge, linear, full
resolution, pin `859edac`.

### Result — the sign reverses, and it is not subtle

Backdrop luminance as excess over each image's *own* far field (d > 420 px), linear DN.
**Positive means veiled upward.**

| image | 4–12 | 12–30 | 30–60 | 60–120 | 120–200 | 200–300 |
| --- | --- | --- | --- | --- | --- | --- |
| frame000 (near end) | **+4082** | +3656 | +3311 | +2918 | +2156 | +1222 |
| frame149 (middle) | **+3617** | +3142 | +2805 | +2367 | +1407 | +674 |
| frame298 (far end) | **+4144** | +3325 | +2949 | +2348 | +1138 | −77 |
| MERGE | +3127 | +2628 | +2252 | +1981 | +1334 | −415 |

Against `flower-bud`'s **−10306 / −5179 / −4604** in the same band. Same instrument,
same pin, same method; the sign of the near-silhouette displacement follows the
subject's polarity, exactly as the model requires.

### The confound-free conclusion

Part of the pencil's positive excess may be **real scene shading** rather than veiling:
unlike `flower-bud`'s featureless sweep, the pencil rests on a receding surface, so
distance-from-silhouette correlates with genuine scene structure. The between-frame
spread also *grows* with distance (527 DN at d=4–12 rising to 2133 DN at d=300–420),
which is the wrong shape for veiling and is most likely the breathing/rescale difference
between independently-aligned single-frame renders. **So the merge-versus-frames
comparison on this subject is not clean and no ratio from it should be quoted.**

The design conclusion does not depend on any of that, because it is a statement about
*which frame gets selected*:

> On `flower-bud`, the upper envelope selects the **middle** frame (−247 is the maximum
> of −3572 / −247 / −388). On `pencil-steep-angle-cpl`, the upper envelope selects the
> **end** frames (+4144 and +4082 beat the middle's +3617). The end frames are the ones
> in which the subject is *most defocused* and therefore spilling *most*.

"Which frame is at the end of the bracket" is a fact about the bracket, not about the
scene, so the confound cannot rescue it. **An unsigned upper envelope systematically
prefers the most-veiled frames on bright subjects.** It must not ship.

### The corrected estimator

All samples of a background pixel are convex combinations of two endpoints, so they lie
on the segment between `B̂` (a = 0, the truth) and `F̂` (a = 1, fully veiled). The
unveiled value is the endpoint **away from the foreground**:

```
sign = sign(B̂ − F̂)      # + when the subject is darker than the backdrop
```

`F̂` is the intensity at the nearby foreground pixels, whose winner index the merge
already holds — one signed scalar per neighbourhood, no new machinery.

Better than an order statistic: `a_k` is **monotone in the foreground's defocus**, i.e.
in `|k − k_F|` where `k_F` is the nearby foreground's winner index. So **regress `I_k`
against `|k − k_F|` and extrapolate to zero**. That uses every sample, is unbiased under
the model, and has variance ~σ²/n rather than a maximum's bias-plus-variance. The fitted
**slope is the veiling strength**, so the same fit supplies the detector: slope ≈ 0 means
nothing is spilling here and the estimator must collapse to the ordinary gated mean —
a veto with no threshold to tune.

The three-point evidence already fits this shape without having been asked to. On
`flower-bud` at d=120–200 the middle frame is cleanest (−247) and both ends are far
worse (−3572, −388); on the pencil the middle frame is likewise the least-displaced of
the three in five of six bands.

### Acceptance criteria, superseding the earlier list

- **Target:** `flower-bud-alone-cpl` d=120–200 beats **−247 DN**.
- **Polarity, non-negotiable:** `pencil-steep-angle-cpl` must improve or be a no-op. A
  regression there means the sign logic is inverted and the fix must not ship.
- **Placebo:** `109MSDCF` ~no-op (flat, no depth separation, −177 DN aura).
- **Guard:** `couch-fibers-cpl` unchanged.
- **Library gate:** a 26-subject gallery sharpness delta, because an over-broad
  rejection rule would soften everything while looking like a win on one subject.
- Report rim and surround **separately**; they have opposite signs and a combined score
  hides the trade.

### What this episode is

I proved a fix numerically before it was built, which was right, and then specified it
from a one-sided sample, which was wrong — and the error was of a kind that a
confirmatory test on any subject in my evidence set would have passed. The check that
caught it was asking what class of subject was *absent*, then going to look for one.
Cost: one classification pass and four renders.

## Scoring the candidates against known truth

`flower-bud-alone-cpl` is shot on a featureless white sweep, so on the backdrop **the
far-field median is ground truth for every background pixel**. That turns "which
estimator is right" from an argument into a measurement. Nine frames were rendered
across the bracket (0, 25, 51, 76, 102, 127, 153, 178, 204), each normalised to the
common far field before comparison.

`k_F` is estimated from the **subject side only** — local gradient energy on subject
pixels, argmax over frames — so the test never consults the backdrop and is not
circular. It recovers `k_F = 102`, which is both the bracket midpoint and the merge's
own alignment reference, from a monotone single-peaked focus curve
(426 → 1799 → 631).

### Accuracy — median error against known truth, linear DN

| estimator | 4–12 | 12–30 | 30–60 | 60–120 | **120–200** | 200–300 |
| --- | --- | --- | --- | --- | --- | --- |
| merge (shipped) | −4631 | −3825 | −4318 | −4692 | **−4066** | −1623 |
| mean | −6677 | −5378 | −3830 | −2170 | −1086 | −417 |
| **signed max** | −1952 | −930 | −420 | −229 | **−134** | −50 |
| **signed cleanest-third mean** | −3117 | −1789 | −807 | −309 | **−190** | −100 |
| signed q87.5 | −3306 | −1741 | −735 | −312 | −196 | −106 |
| regress to a = 0 | −4925 | −2863 | −1141 | −26 | 163 | −61 |
| wrong tail (lower) | −10500 | −9674 | −8390 | −6311 | −3572 | −1326 |
| ORACLE best single frame | −1952 | −932 | −460 | −356 | −343 | −227 |

As a gain over the shipped merge, the signed max runs **2.4× / 4.1× / 10.3× / 20.4× /
30.3× / 32.6×** across the six bands — monotone in distance, and better than the merge
in *every* band including hard against the silhouette.

**It also beats the oracle single frame** (−134 against −343 at d=120–200). That matters:
the estimator is not merely "pick the best frame", it genuinely combines, so no
selection-based fix can reach it.

### Two of my own proposals die here

**"Regress `I_k` against `|k − k_F|` and extrapolate to zero" is refuted.** I argued it
would beat an order statistic because it uses every sample and is unbiased. Measured, it
loses to the plain signed envelope in five of six bands on this subject (0.9× against
2.4× at d=4–12) and in *all six* on the pencil. The model is wrong: veiling is not
linear in `|k − k_F|`, so a line fitted through mostly-veiled samples overshoots.
**Withdrawn.**

**"Use a high quantile and debias for `sqrt(2 ln n)`" is unnecessary.** Across the whole
family the far-field noise spans only **356 → 374 DN, a 5% range** — max, median and
mean are all within a whisker of each other. In the far field the frames are nearly
identical, so an order statistic over strongly correlated samples costs almost nothing,
and there is no reason to back off the tail. Take the aggressive end.

The 1.22–1.28× noise floor that *every* candidate shares, including the plain mean, is
the **9-frame subsample**, not the estimator — the merge averages ~205. In-crate a
cleanest-third mean averages ~68 frames rather than 3, so the floor should fall away.
**That is a prediction, not a measurement, and it must be checked rather than assumed.**

### The guard fires, and it is the most important number here

Gradient RMS inside the subject, eroded 40 px clear of the silhouette:

| estimator | subject detail vs merge |
| --- | --- |
| merge (shipped) | 1.000× |
| signed max | **0.355×** |
| signed q87.5 | 0.332× |
| signed cleanest-third mean | 0.261× |
| mean | 0.184× |

**Every candidate destroys 64–82% of the subject's gradient energy.**

Half of that is a confound and must be said plainly: my estimators are pure per-pixel
statistics over nine differently-focused frames and perform **no focus selection at
all**, so of course they are blurry on the subject — that comparison is "focus-stacked"
against "not focus-stacked". The merge's 1.000× is its election doing exactly the job it
exists to do.

But the direction is real and the magnitude bounds the risk, so the conclusion is hard:

> **The signed envelope must be gated to background pixels and must never touch pixels
> the election is handling.** Applied globally it would cost most of the subject detail
> in the library — the same failure mode BUILD-RENDER caught costing 6.6% across 26
> subjects, except an order of magnitude larger.

The gate is already available from the same statistic: where no foreground is spilling,
the through-focus curve has no veiling component and the estimator must collapse to the
ordinary gated mean. It is worth noting that the signed max preserves nearly **twice**
the subject detail of the plain mean (0.355× against 0.184×), so if the gate ever leaks,
the envelope is the more forgiving of the two errors.

### The specification, as measured

1. **Direction** from `sign(B̂ − F̂)`, where `F̂` is the intensity at the nearby
   foreground pixels whose winner index the merge already holds. Not a tunable.
2. **Estimator**: mean of the cleanest third in that direction (21.4×) or the plain
   extremum (30.3×). Noise between them differs by 5%; prefer the third-mean in-crate
   where it averages ~68 frames.
3. **Gate**: background pixels only, detected by a non-zero veiling slope. Non-optional.
4. **No debiasing, no quantile tuning, no regression.** All three were proposed by me and
   all three are refuted above.

---

## 9. The other side of the same term, and why it cannot be fixed the same way

The two-layer model is symmetric on paper:

```
I_k(p) = a_k · (F ⊛ PSF_k)(p)  +  (1 − a_k) · (B ⊛ PSF_k)(p)
```

A **background** pixel near a silhouette picks up the foreground term and darkens (for a
dark subject). That is the aura, and §8 fixes it at 30.3×. A **foreground** pixel near
the same silhouette picks up the background term and washes pale. Both are the same
physics with the layers exchanged, so the obvious move is to mirror the rule: reject
samples displaced *toward the other layer* on whichever side you are standing.

I built it. It is refuted, and the way it fails is more useful than the fact that it does.

`twoside.py`, `flower-bud-alone-cpl`, nine frames, subject-side pixels, rule applied to
1.4% of the frame by weight. The wash is measured as median luminance in the silhouette
band; detail is gradient RMS, reported separately for the band the rule acts on and for
the subject core it must not reach:

| arm | wash DN | detail @ edge | detail @ core |
| --- | --- | --- | --- |
| merge | 5124 | 4044.4 | 864.1 |
| one-sided (§8) | 5124 | 4044.4 | 864.1 |
| two-sided | 4708 | 3030.4 | 864.1 |

**0.919× of the wash, for 0.749× of the silhouette detail.** Eight percent of the defect
for a quarter of the structure. The core is untouched at 1.000×, so the gate itself is
clean — the damage is entirely inside the band the rule was aimed at.

The montage is worse than the number, and this is the reason to look at pictures.
`preview/twoside-upper-lobe.png` shows merge | one-sided | two-sided. In panel 3 the
bud's rim is **eaten**: the fine bristle texture along the silhouette is gone, replaced
by a flat pale band. Panel 2 — the shipping rule — leaves that rim identical to the merge
while clearing the backdrop behind it.

### Why the mirror fails, and what it fixes in my own specification

The asymmetry is not in the physics. It is in what the two sides have to lose.

> On the backdrop, the content is featureless. Every frame's sample is the same latent
> value plus veil plus noise, so an extremum over frames costs **nothing** — there is no
> detail there to destroy, only veil to reject.
>
> On the subject, the correct sample is a **specific frame**: the one in focus at that
> depth. An extremum over frames is emphatically not that frame. The rule competes with
> the election, and it loses.

That kills item 3 of §8's specification as I wrote it. "Background pixels only" is a
**mask-geometric** gate, and the variable it stands in for is not geometry:

> **The invariant is whether the election has anything to choose between.** Where the
> through-focus focus response is flat, selection is arbitrary and the envelope is free.
> Where it is peaked, the election is carrying real information and nothing may override
> it.

This is strictly better than the mask formulation in three ways: it is computable from
the focus volume the merge already builds; its threshold is set against the calibrated
noise floor rather than tuned by eye, which is the project's whole thesis; and being
content-based it reaches pixels that a distance-from-silhouette gate can never reach.

**§8 item 3 is superseded. Items 1, 2 and 4 stand unchanged.**

## 10. The pale wash is a different defect, and it is now the largest one visible

The decisive observation is a *null*: the wash is **identical in all three panels** of the
montage. Neither form of the veiling rule moves it. Whatever it is, it is not the veiling
term, and no refinement of §8 will remove it.

`preview/twoside-lower-lobe.png` names it. That crop lies entirely inside the subject and
contains a **straight-edged polygonal patch** of visibly softer, wrong-depth content with
a hard boundary against its neighbours — present in all three arms. Straight boundaries
do not occur in defocus; defocus is smooth and isotropic at this scale. A hard polygonal
seam in a merged image is a **winner-field artifact**: a block elected from a different
frame than everything around it. The scalloped boundary on the upper lobe's wash is the
same failure at smaller scale.

This is the mechanism BUILD-SHARP independently named from artifact morphology —
*geometric mis-selection*, the merge electing for a pixel a frame in which some other
structure covered it. Two lanes reached it from opposite directions, which is the
strongest evidence the project has that it is real.

Recorded here, with its evidence, so that it is not confused with the veiling defect
again and so that no time is spent trying to make §8 remove it. It is its own lane.

## 11. What the two negatives cost, and what they were worth

Five of my own proposals have now died in this document: the unsigned envelope (inverts
on bright subjects), regression to α=0 (loses in 5 of 6 bands), quantile debiasing
(unnecessary), the two-sided mirror (§9), and the mask-geometric gate (§9). One survived
and it is worth 30.3× on the defect the owner called unusable.

The ratio is the point, not an embarrassment. Every one of the five was killed by an
instrument built to kill it, before it reached the crate — which is the only reason the
shipping specification is four lines long and every line of it is measured.

---

## 12. Two subjects, two defects, and a negative control that came free

§10 asserted from a picture that the subject-side wash is an election artifact rather
than the veiling term. That was **ARGUED**. This section measures it, and the measurement
separates the two defects cleanly enough to give each one an acceptance test.

### The design

The gallery renders with `--srgb`, and this document has a standing warning that tone
amplifies the rim. That warning cuts both ways: **a monotone veil with a steep inner
shoulder reads as a bright line after an S-curve even when no bright band exists in the
data.** So every visual claim about a "rim" made on a gallery JPEG is unfalsified.

The discriminator is a signed-distance profile of backdrop luminance, measured on the
**linear** 16-bit render, outward from the silhouette. A monotone rise toward the far
field means one optical term. An interior local maximum means the merge emitted a ring.

Two subjects were chosen to differ in exactly one property:

- **`coffee-bean`** — one convex silhouette, **smooth**, no fringe. 105 frames.
- **`flower-bud-alone-cpl`** — dense **trichome fringe** along the entire silhouette.
  205 frames.

Both rendered from the same pin (`1cacb61`, `git archive` + clean build), same command,
no tone curve. Instrument: `rimprofile.py`.

### The result

| | darkening at silhouette (0–4 px) | interior ring | ring prominence |
| --- | --- | --- | --- |
| `coffee-bean` (smooth) | −21346 DN = **−38.2%** | d = 450 px | +130 DN = **0.23%** |
| `flower-bud` (fringed) | −6951 DN = **−36.5%** | **d = 18 px** | +2279 DN = **12.0%** |

Two things fall out, and they point in opposite directions.

**1. The veiling term is confirmed on a second subject, at the same relative strength.**
−38.2% and −36.5% of the far-field backdrop, on subjects that share no morphology, no
frame count and no scene. A term that lands within 1.7 points on two unrelated captures
is behaving like optics, which is what §8 assumed and had only measured once. The
absolute numbers differ by 3x; the **relative** numbers do not.

**2. The bright ring exists, it is real in linear light, and it appears only with a
fringe.** `coffee-bean`'s only interior peak is 0.23% at 450 px — far-field wobble, not a
ring, and nowhere near the silhouette. `flower-bud`'s is **12.0% at 18 px**, sitting
exactly where the "poured liquid" band is visible. **52x apart in relative prominence.**

### Why this matters more than the numbers

The two subjects differ in one property and the artifact tracks it. That converts a
morphological observation into a **prediction that held**, and it is direct support for
the mechanism proposed in §10 and routed to the election lane: a box-summed gradient
focus measure scores edge *density*, not edge *sharpness*, so a defocused fringe of fine
hairs can outscore a sharply focused one. A smooth silhouette has no fringe to smear,
therefore no ring. A trichome fringe has nothing but.

It also hands the election lane two things it did not have:

> **A target.** A fix must drive `flower-bud`'s ring prominence from 12.0% toward
> `coffee-bean`'s 0.23%.
>
> **A negative control that costs nothing.** `coffee-bean` has no ring to remove, so any
> change that moves *its* profile is doing something other than what it claims. This is
> the placebo the veiling work had to construct deliberately; here it is free.

### The detector was wrong first, and the profile caught it

The first version of the verdict test asked whether the peak exceeded the **far field**.
It reported **NO BAND on flower-bud** — a profile that visibly turns over twice.

The ring sits *inside* the veil. It is brighter than the trough beside it and still
darker than the far field, so a far-field comparison **cannot see it by construction**.
That is this project's own recorded failure mode — an auto-detector built on a guessed
threshold returns zero and looks exactly like a clean negative — committed here, in a
script written to avoid it.

It was caught only because the script **prints the whole profile above its verdict**, and
the printed rows disagreed with the conclusion. The lesson is cheap and general:

> **A verdict line must never be the only output. Print the evidence it was computed
> from, above it, where a disagreement is visible without re-running anything.**

The corrected test looks for an interior local maximum and scores it by prominence above
the trough outside it, which is also the quantity that makes a ring visible to the eye.




---

## 13. My own headline number is not safe, and another lane found the reason

**Status: my §8 result is impeached. It is not withdrawn, because I have no measurement
that decides it either way. That is the whole point of this section.**

BUILD-SHARP was commissioned to verify BUILD-HALO's veiling fix. Instead of waiting for
something to verify, it built the harness first and measured the candidate estimators
against a known ground truth **before the fix existed**:

| estimator | bias | sd | vs shipped |
|---|---|---|---|
| shipped gated mean, 166.8 frames | +0.0000 sigma | 0.0774 sigma | -- |
| upper envelope of 3 | **+0.845 sigma** | **0.748 sigma** | **9.7x noisier** |

And drew the consequence:

> The bias is **upward** and the defect is a **darkening**, so an undebiased envelope
> removes veil **arithmetically**. At sigma_frame ~ 200 DN that is **+169 DN** -- the same
> order as `109MSDCF`'s entire -177 DN aura.

### Why this lands on §8

§8 reported flower-bud backdrop error `-4124 DN -> -149 DN`, a factor of **27.7**.

**A -149 DN residual is smaller in magnitude than the +169 DN bias predicted above.**

So the clean-looking recovery is consistent with at least two states of the world:

1. the veil was removed, and the residual is genuinely small; or
2. the veil was **partly** removed, and an upward estimator bias filled in the rest.

Nothing in §8 distinguishes them, because §8 measured an **error** and a **ratio**, and an
additive bias is invisible in both. The 30.3x and 21.4x estimator scores in §11 inherit
the same doubt for the same reason, and so does the -36.5% / -38.2% target in §12.

This was not caught by re-reading my own work. It was caught by a different agent
pointing a different instrument at a quantity I had not measured.

### The mechanism is not in dispute

`E[max]` over `n` samples grows like `sqrt(2 ln n)`. The brackets here are ~205 frames.
An extremum is the order statistic whose expectation drifts with `n` by definition, so
"take the signed extremum" was a specification for a biased estimator, written by someone
who had measured its recovery and never measured its level.

### What changes

1. **The spec now prefers the cleanest-third mean over the signed extremum.** §11 called
   them 5% apart and said take the simpler. A mean over a subset selected on
   *cleanliness* is near-unbiased in *level*; an extremum is biased by construction. Five
   percent of recovery is not worth a residual nobody can interpret.
2. **Any order statistic on the default path must be explicitly debiased**, with the
   correction derived and its magnitude printed. A debiasing constant fitted to null the
   veiling number **is** the artifact.
3. **The veiling metric can no longer certify a fix on its own.** The discriminator is a
   **placebo subject with no veil**, and the quantity is **absolute background level in
   DN** -- not the aura, not the error, not a ratio.
   - `109MSDCF`: dark subject, bright backdrop, **no depth separation**, only a -177 DN
     aura. The fix must be approximately a no-op. A rise near +169 DN means the estimator
     is adding light.
   - `coffee-bean`: veil at -38.2%, **no ring**. Veil must fall, ring must not move, far
     field must not rise.
4. **Report levels, not ratios.** §8's own framing is how this would have shipped.

### The general lesson, which is the same one as §12 from the other direction

§12's lesson was that a verdict line must never be a script's only output. This is its
twin:

> **A metric that can be satisfied by two different mechanisms has not been reduced to
> one by being satisfied. Measure the quantity that only one of the mechanisms moves.**

The failure mode available here is a **green result on every instrument either lane
owns**: an upward-biased estimator against a darkening artifact satisfies the veiling
number, satisfies the aura number, and satisfies any ratio built from them. Only the
absolute level, on a subject that has no veil to remove, can tell the difference.

---

## 14. A hypothesis of mine, killed by its own measurement, and the confound it exposed

This section records a finding I did not make. I chased it for about forty minutes,
measured it, and it was nothing. It is here because the *reason* it was nothing is a
live confound for every A/B comparison in this project, and because the near-miss is
instructive: I was one edit away from reporting the owner's central complaint addressed
by a change that alters no pixel.

### 14.1 The hypothesis

`scripts/gallery.ps1` renders every subject with

```
strehl stack <DIR> --out <TIFF> --srgb --demosaic
```

and never passes `--auto-exposure`. The binary prints this on every such render, into a
log file that is written and not read:

```
exposure : none -- this is a FAITHFUL render of the capture, which is not the
           same thing as a flattering one. --auto-exposure would choose +2.62
           stops (gain 6.148x). Nothing was applied.
```

The gallery manifest agreed: of 26 subjects, **21 recorded a white point below 0.55**,
with `lead-1-cpl` at 0.0738 and `112MSDCF` at 0.0985. Read straight, that says the
brightest content in most of the library renders in the bottom third of the tonal range.

It was an attractive hypothesis. It was the fifth candidate "dark feature" of the night,
it would have applied to **every pixel of every image the owner has ever judged**, and it
would have explained his verdict completely, without implicating any algorithm.

### 14.2 It is refuted

Two full renders of `109MSDCF`, identical but for `--auto-exposure`
(`C:\dev\strehl-out\ORCH-expo\`, `arms.ps1` and `expodiff.py`):

| quantity | value |
|---|---|
| mean ratio B/A | **1.0000** |
| what a real +2.62 stop difference would give | 6.148 |
| max abs diff | **1 DN** |
| samples identical | 98 560 892 of 98 898 048 (**99.659%**) |

`--auto-exposure` does not change the picture.

### 14.3 Why, and this is the part that matters

The two tone lines were:

```
A:  tone : black 0.00582, white 0.16238 (linear)
B:  tone : black 0.03580, white 0.99820 (linear)
```

B is A times 6.148 in **both** numbers, to five digits. **The tone stage maps its own
measured `[black, white]` window onto `[0,1]`, per image.** An exposure gain scales the
data and the window together and cancels exactly. The `white` column in the manifest is
therefore not a statement about how bright the render is; it is the input level that the
render maps to white.

### 14.4 The confound this exposes, which is general

**Every `--srgb` render in this project is independently normalised to its own measured
black and white points.** Three consequences, none of them confined to this section:

1. **Absolute DN is not comparable across arms on a tone-mapped render.** Two merges
   differing only in their single brightest pixel get different tone windows and
   therefore globally different output levels, for a reason that has nothing to do with
   the merge.
2. **An A/B on `--srgb` output is self-normalising**, so it can hide a real global
   difference and it can manufacture an apparent one. The standing rule against
   measuring on `--srgb` already existed because of the transfer curve. This is a
   **second and independent reason**, and it is the worse of the two, because the
   transfer curve at least applies equally to both arms while this normalisation is
   *adaptive* and therefore differs between them.
3. **A measurement normalised to an in-image reference survives it**, because a
   per-image scale cancels in a ratio taken inside that same image. The paired tables in
   §15 normalise each arm to its own 600-1400 px far field and are unaffected.

### 14.5 The near-miss, stated plainly

Had I not measured it, I would have added one flag to `gallery.ps1`, re-rendered, and
reported that the owner's complaint was addressed. The pictures would have been
byte-identical to within 1 DN. That is worse than doing nothing, because it *looks* like
progress and it consumes the credibility that the real fixes need.

> **A mechanism that would explain the complaint is not evidence that it does. Measure
> the fix, not the mechanism.**

The same standard applies to everything else claimed tonight, including the multi-band
merge -- which is why that one was judged on paired full frames and a radial profile
before it was believed, and not on the strength of its story.

---

## 15. The instrument had a two-reference bug, and fixing it reversed a published sign

### 15.1 The defect

`C:\dev\strehl-out\ORCH-rim\rimprofile.py` printed two tables under one heading. The
linear table normalised to the far field, `ref`, the median over 600-1400 px. The encoded
table normalised to `enc[-1]`, the **outermost bin at d=550 px** -- a bin that is itself
inside the artifact being measured. Both columns were labelled "delta vs far-field".

The consequence was not academic. On one A/B the linear table read **-272 DN** at
d=300-400 while the encoded table read **+0.29 of 255** at d=350, and the two rows
appeared to contradict each other. They did not; they were measured against different
zeros. Anyone comparing them would have concluded the instrument was broken -- or
believed whichever row suited them.

Fixed: both tables now use the far field, and the script prints its reference on an
explicit line so the two can never silently diverge again.

### 15.2 The corrected paired result

`ca-ctrl-` vs `ca-blend-flower-bud-with-background-fern-cpl.tiff`, background luminance
by radial distance `d` from the subject silhouette, both arms against the same far-field
zero (control 59630 DN = 248.1/255; blend 60260 DN = 249.1/255):

| d (px) | CONTROL /255 | BLEND /255 | blend - control |
|---|---|---|---|
| 2 | -41.56 | -40.17 | +1.39 |
| 90 | -7.69 | -4.09 | **+3.60** |
| 175 | -3.17 | -3.42 | -0.25 |
| 350 | -0.50 | **-2.69** | **-2.19** |
| 550 | -0.79 | **-3.15** | **-2.36** |

Two readings, one good and one bad, and the bad one is new:

- **The multi-band merge more than halves the visible mid-field halo** at d=90. This is
  the artifact that makes the control read as a cut-out sticker with a glowing outline,
  and the paired full frames for `lavendar-cpl` show it plainly at viewing scale.
- **The blend introduces a broad far-field pedestal the control does not have.** The
  control converges to -0.50 by d=350 and -0.79 by d=550. The blend sits at -2.7 to
  -3.2 from d=175 outward and does not converge anywhere inside the frame. That is the
  Burt-Adelson coarse-level halo: a Laplacian blend redistributes energy at every level,
  and at the coarsest levels the support is hundreds of pixels wide.

Because both arms are referenced to their own far field, the +630 DN absolute level
difference between them is divided out by construction. **The bowl is not that shift in
costume.** An open question from earlier in the night is thereby closed.

### 15.3 The consequence for the shipping configuration

The prescribed fix is not to tune the pyramid depth. It is to **take the base band from
the noise-gated mean and blend only the detail bands** -- which is this project's own
thesis applied to the frequency axis. Low spatial frequencies do not need selecting:
defocus is a low-pass, so every frame carries them at MTF near 1, and there is no
information at the base band that selection can add. There is only bias it can
introduce. The gated mean is meanwhile the one estimator here with a measured bias of
**+0.0000 sigma**, against **+0.845 sigma** for the upper envelope of §13.

That also makes the far field correct *by construction* rather than by tuning: away from
the subject the mask is uniform, the gated mean is the mean, and the base band is
whatever the background was. It cannot pedestal.

---

## 16. The artifact is not in the photographs

This section retires the premise the veiling lane was built on, including my own
sections 8 and 12. The correction did not come from me. V-RIM, an independent
verifier working from its own code and forbidden from using `rimprofile.py`,
measured the one thing none of us had measured.

### 16.1 The measurement

Everyone in this project, myself first, had been measuring the background profile
near a silhouette **in merged output**. V-RIM measured it in **individual frames**.

| | merge | sharpest single frame |
|---|---|---|
| coffee-bean | -13.61% | frame 58: **-0.81%** |
| flower-bud | -18.94% | frame 110: **-0.22%** |

Across 16 usable frames from both anchors' brackets, **every profile is monotone**,
worst reversal 0.18% of far field. The picture is
`C:\dev\strehl-out\V-RIM\pics\fb-merge-vs-frame110.png` and it is not subtle:

- Frame 110, the frame in which flower-bud's silhouette is in focus, is **flat at
  ~19100 DN** from 600 px out right up to the edge.
- The merge over the same rows **sags to ~13800 DN**, recovering to ~15600 in the
  last 20 px.

Roughly 28% of the backdrop's brightness, removed by software, at a location where
the stack contains a frame that saw the backdrop correctly.

### 16.2 What is refuted, stated carefully

The veiling is **real optics**. In a frame where the subject is defocused, the
defocused subject genuinely spills light across the silhouette and that frame's
backdrop genuinely is veiled. Nothing overturns that.

What is refuted is that the veil is **inherited and irreducible** -- that the stack
holds no clean view of that backdrop and the only remedy is to model the veil and
subtract it. Frame 110 is a clean view. The information needed to render that
backdrop correctly is present in the data, and the merge is failing to use it.

That moves the defect out of optics and into **election**:

> In a smooth bright backdrop the focus measure has no real signal. Near a
> silhouette the defocused subject spills contrast INTO the backdrop region, so
> frames in which that pixel is covered by defocused subject score HIGHEST there.
> The merge elects a frame in which the pixel is not backdrop at all, and the
> output lands darker than every frame that actually saw the backdrop.

### 16.3 Three lanes, three routes, one mechanism

The mechanism was not reached once. It was reached three times, independently,
from measurements that share no code and no subject preparation:

| lane | route | number |
|---|---|---|
| V-RIM | frame-level ground truth | merge -18.94% vs in-focus frame -0.22% |
| V-TONE | convexity | merge reads **2499 DN outside its own input hull**; an honest 7-frame mean reads inside it |
| BUILD-HULL | residual audit | **-805 DN** below every contributing input |

A per-pixel convex combination cannot leave the hull of its inputs. Three
independent instruments agreeing that the output does is not a coincidence, and it
is a much stronger result than any of the three alone.

### 16.4 Confirmed by eye, at 100%, where it had never been looked at

The gallery is 2400 px from a 7032 px render, so it cannot show a defect 2 px from
an edge; a verdict of "looks clean" drawn from it would be a statement about the
downsampler. Cut at 100% (`C:\dev\strehl-out\ORCH-100\`), against the exact binary
that produced the gallery the owner rejected, the election is directly visible:

- **`bee-1-cpl` site 2:** the white backdrop in the control arm is a collage of
  **hard-edged grey polygons** -- straight borders and sharp corners across what
  is physically a smooth sheet -- with a scalloped dark band hugging the leg. The
  multi-band arm is clean smooth white, with the fine translucent hairs that cross
  the backdrop still present.
- **`bee-1-cpl` site 1:** the control arm carries polygonal patches of
  **wrong-focus content with visible seams**. The blend arm resolves every hair
  continuously across the same region.
- **`bee-1-cpl` site 0:** the control arm's ommatidia are mushy and a region at
  lower left is a featureless smear. The blend arm resolves individual facets and
  shows fine reddish hairs that are **entirely absent** from the control.

The last of those is worth separating out, because it was not predicted. The
multi-band merge is not only removing artifacts; it is **recovering detail the
control merge was destroying**. That is consistent with the mechanism: a per-pixel
election with a spatially regularised winner field is piecewise constant, so at
fine scales it selects the wrong frame over whole patches and the patch boundaries
show as seams. Selecting per frequency band lets high-frequency detail come from
whichever frame actually carries it, independently of the base band.

So three defects that had been tracked as separate problems -- the silhouette
halo, the polygonal background patches, and the softness BUILD-SHARP was chasing
-- are one defect with one cause.

### 16.5 What follows

1. **A post-hoc veiling subtraction must not ship on the default path.** Against a
   defect the merge itself manufactures, a subtraction that cancels it is a
   correction fitted to our own bug, and it is untestable in the way that matters:
   it can be tuned until the number goes away without the picture being right.
   This is section 13's lesson arriving from the opposite direction.
2. **Take the base band from the noise-gated mean.** An election with a spatially
   varying mask can leave the hull; **a mean cannot**. In a smooth backdrop the
   mean of the frames simply is the backdrop, so this makes the artifact
   structurally impossible at low frequencies rather than merely smaller.
3. **The acceptance target is now ground truth rather than an argued threshold.**
   Frame 110's backdrop profile is the correct output for flower-bud's backdrop;
   frame 58's for coffee-bean. A fix should land the merged backdrop **on** the
   in-focus frame's flat level, not merely reduce a delta against a number I
   picked.
4. Both acceptance tests I registered in section 12 are unsafe and V-RIM says so:
   the target names a floor that does not exist, and the "free negative control"
   would reject a genuine fix. They are withdrawn.

### 16.6 The lesson, which is about where the instrument was pointed

Every measurement in sections 8 through 13 was taken on merged output. The
instrument was refined, its reference bug was found and fixed, a published sign
was reversed, and a paired table was produced to decision grade. All of that work
was real and none of it could have found this, because **the comparison that
mattered was never between two merges. It was between a merge and a frame.**

> **Before measuring how much an artifact moves, measure whether the input
> contains it. An artifact absent from every input is not being reduced by a
> better estimator; it is being manufactured by the pipeline, and the fix is
> upstream of everything you are tuning.**

## 17. Two measurements on the blend arm: one exoneration and one real defect

Sections 8 to 16 were about the artifact. This section is about the *candidate
fix*, and it reaches opposite conclusions on the two charges standing against it.
Both were measured with code the blend's author has never seen, which is the
project's rule that an author does not verify their own work.

### 17.1 The charge that dissolves: the "noise penalty" is recovered detail

BUILD-BLEND self-reported that its multi-band merge is **+12.3% noisier in flat
regions** on `couch-fibers`, and carried that forward as the cost of the fix.

Measuring the same quantity independently made it worse, not better:

| subject | sigma control | sigma blend | delta |
| --- | ---: | ---: | ---: |
| `bee-1-cpl` | 7.8 | 132.9 | **+1605%** |
| `flower-bud-alone-cpl` | 37.1 | 75.5 | +105% |
| `couch-fibers-cpl` | 565.2 | 747.8 | +32% |
| `flower-inner-edge-cpl` | 347.0 | 372.3 | +7% |

The `bee-1-cpl` row is what exposed the problem. **7.8 DN of high-frequency
spread is 0.012% of full scale, and no real fourteen-bit photograph has a noise
floor that clean.** That number is not cleanliness. It is blur: at 100% the
control's "flat" regions there are hard-edged grey polygons -- patches of a single
defocused frame -- and defocus is a low-pass filter.

So a metric built on high-frequency **energy** cannot answer this question at
all, because it counts noise and detail in one bin and therefore **rewards
whichever arm destroys more detail.** Every such metric, including the one that
produced the original +12.3%, scores a blurred arm as the quieter one.

Noise and detail differ in *correlation*, not in energy. Photon and read noise
are white; optical detail is band-limited by the lens and sensor MTF. The
white-noise reference was measured by pushing a synthetic white field through the
identical high-pass rather than asserted algebraically: **rho_lag1 = -0.0035**.
Modelling each arm as structure plus white noise, the added component's own
correlation follows from variance weighting with no assumption about what the
structure is:

    rho_add = (rho_A * V_A - rho_B * V_B) / (V_A - V_B)

| subject | rho control | rho blend | **rho_add** | would read if noise |
| --- | ---: | ---: | ---: | ---: |
| `bee-1-cpl` | +0.469 | +0.450 | **+0.450** | +0.002 |
| `couch-fibers-cpl` | +0.869 | +0.802 | **+0.712** | +0.497 |
| `flower-bud-alone-cpl` | +0.458 | +0.517 | **+0.536** | +0.110 |
| `flower-inner-edge-cpl` | +0.910 | +0.914 | **+0.943** | +0.791 |

Every subject sits far above its own counterfactual. `bee-1-cpl` is cleanest:
**+0.450 measured against +0.002 expected if the added energy were white.** White
noise cannot produce a lag-1 correlation of 0.45.

**The energy the blend adds is correlated structure. It is detail the control was
destroying.** The +12.3% is not a cost, and reducing it would mean blurring the
good arm. This does not prove the blend adds *zero* noise -- a real increase could
ride underneath a larger detail increase -- but it does refute the charge as
stated.

### 17.2 The charge that stands: the blue channel is clamped to zero on the subject

The same arm carries a defect nobody had measured, because everyone was looking
at tone-mapped renders. In the **linear sixteen-bit output**, on
`flower-bud-alone-cpl`:

    blue pixels at exactly 0 : 723,429 = 2.192% of the frame
    same pixels, control arm : median 10,913 DN

It is a clamp, not a dark scene. Raising the threshold barely moves the count --
2.192% at zero, 2.384% at 256 DN -- so 2.19% sit pinned at exactly zero and only
0.19% lie anywhere above it. A genuinely dark scene produces a smooth ramp.

Two attributions were tested and both failed:

- **Not thin edge ringing.** The brightest four-neighbour of a zero pixel has a
  **median of 0.0 DN**, and only 0.1% of zeros have any neighbour above 4000 DN.
  A dark rim against a bright edge would put a bright neighbour beside nearly
  every zero.
- **Not coverage or packaging.** 24 of 23,456 border pixels (0.1%), so the
  region never reaches the canvas edge.

Drawing the mask over the picture settled it. The zeros sit **on the subject**,
in the shadowed crevices between the bud's scales and along its dark right flank
and bottom lobe -- simultaneously the darkest and the most textured regions, in
the channel that is intrinsically weakest on green foliage. A Laplacian
reconstruction sums band-pass layers; where the base band is already low and the
coarse layers undershoot, the sum goes negative over a broad area and the clamp
destroys it.

**This blocks a print claim.** A dead blue channel over 2.19% of the frame is an
irreversible colour shift toward yellow-green in exactly the shadows where a
macro print shows depth, with no detail left to recover.

It also forces a withdrawal. Section 16's field notes recorded that on
`flower-bud-alone-cpl-100pct-site2` the blend "shows the bud's true colour where
the control bleached it". Some of that extra green is this bug, because removing
blue from green foliage makes it read greener. **The structural half of that
comparison stands -- the control's hard-edged pale patches are plainly wrong and
the blend resolves trichomes the control does not contain -- but the colour half
is withdrawn.**

### 17.3 Two disciplines, from the two ways this nearly went wrong

The first verdict this analysis printed was "RINGING", and it was wrong. It was
caught only because the script printed its evidence rows above its conclusion,
and the neighbour statistic sitting three lines above the verdict contradicted
it outright.

> **A metric named for what you hope it measures will be believed as though it
> measured that. "Noise" computed as high-frequency energy scores a blurred image
> as the quiet one, so it ranks a detail-destroying pipeline first. Before
> trusting any quality metric, check what it says about an arm you already know
> is worse.**

> **When statistics cannot separate two mechanisms, draw the picture. A mask
> rendered over the photograph settled in one look what four summary statistics
> had left ambiguous, and it overturned the verdict the statistics had produced.**

### 17.4 A correction to 17.2: right conclusion, wrong reason

Section 17.2 attributed the clamped blue channel to the merge on the stated
ground that the measurement sat "upstream of the tone stage, so no per-image
black point can reach it."

**That ground was false.** `crops.ps1` renders the control arm with `--srgb`, so
those TIFFs are viewing renders, not linear sensor data. The claim was an
assumption stated as a fact, and it happened to be the single assumption on which
the whole attribution rested.

Two checks were run rather than repairing the sentence.

**First, is the difference merely an encoding mismatch?** The two arms are
invoked differently -- the control gets `--srgb --demosaic`, the blend arm gets no
flags -- so if one wrote camera-linear and the other sRGB, the sRGB toe would lift
shadows by more than a factor of ten and manufacture exactly this result. Refuted:
the arms' percentiles agree closely (median 0.930 against 0.933, p95 0.970 against
0.966), sRGB-encoding the blend arm lands nowhere near the control (p5 0.419
against 0.136), and binning one arm against the other gives **0 of 10 bins**
consistent with a single-valued curve. The arms differ by content, not by a
transfer function.

**Second, can the tone stage move a zero count at all?** One binary, one subject,
one merge, rendered twice with the tone setting as the only difference:

| threshold | B channel, `--srgb` | B channel, linear | delta |
| --- | ---: | ---: | ---: |
| 0 | 0.0005% | 0.0000% | −0.0005 |
| 256 | 0.0081% | 0.0004% | −0.0077 |

**Largest movement attributable to the tone stage: 0.0077 pt, against the 2.192
pt measured between the two merges. A factor of 285.**

So the conclusion of 17.2 stands and is now on firmer ground than when it was
written: the black point is excluded as an explanation by measurement rather than
by assumption. What does *not* stand is the reason originally given. A reader who
took 17.2 at its word would believe those TIFFs are linear, and would carry that
false belief into the next measurement they made on them.

> **When an argument rests on one assumption, the assumption is the experiment.
> "Upstream of the tone stage" was load-bearing, unchecked, and wrong; the
> conclusion survived only because a control was run afterwards, which is luck,
> not method. Identify the single load-bearing premise and measure that first.**

## 18. The clamp, attributed: a ladder, a sweep, and a fix that would have destroyed the photograph

Section 17.2 established that the multi-band blend writes pixels at exactly zero
where the control writes ordinary mid-shadow values, and 17.4 re-earned that
conclusion after demolishing its original reasoning. Neither said *why*, and a
defect without a mechanism cannot be fixed, only avoided. This section attributes
it.

It also contains two retractions of my own claims and one near-miss that would
have shipped a "fix" which scored perfectly and ruined every photograph it
touched. The near-miss is the most useful thing here.

### 18.1 First, the picture, because no statistic conveyed this

17.2 reported the defect as a percentage. That framing is what let it sit
unresolved: 2.19% of pixels sounds like a shadow-noise question. It is not. The
100% crop of `dry-erase-marker-head-cpl` at site (6136, 1360) shows **solid black
axis-aligned blocks roughly 40 to 60 px across, hard-edged, sitting on and beside
the ink marks, with red and magenta fringes on their edges.** The control panel at
the same site has none. It is the single most visually destructive artifact in the
output, worse than the halo that prompted this whole line of work, and no print
survives it.

Two things follow immediately from the *shape*. A smooth reconstruction
undershoot cannot make a hard-edged block; a coarse-band coefficient can, because
its reconstruction footprint **is** a block of about that size. And the defect is
not blue-specific. 17.2's title says "the blue channel" because `flower-bud-alone`
is blue-dominant. On `dry-erase-marker-head-cpl` all three channels clip within
0.5 pt of each other:

| subject | R | G | B | verdict |
| --- | ---: | ---: | ---: | --- |
| `dry-erase-marker-head-cpl` | +1.8556 | +1.9588 | +2.3560 | merge |
| `foam` | +0.9936 | +0.6579 | +1.1217 | merge |
| `flower-bud-alone-cpl` | +0.1841 | +0.2999 | +2.1914 | merge |
| `bee-1-cpl` | +0.0579 | +0.0947 | +0.1180 | marginal |
| `flower-inner-edge-cpl` | +0.0457 | +0.0051 | **−0.6661** | marginal, blend *better* |
| `couch-fibers-cpl` | +0.0000 | +0.0000 | +0.0000 | none |

Percentage points of pixels at exactly zero in the linear 16-bit TIFF, blend minus
control. It hits whichever channel is darkest at that site. **Read 17.2's title as
subject-specific, not as a statement about the channel.**

### 18.2 The ladder: one candidate mechanism removed per rung

Reading `blend-render.rs` there are two places a negative can be floored, and the
shipped TIFF is downstream of both: `norm`'s `v.max(0.0)` at line 572, which
clamps the *merged plane*, and `space.develop(matrix)`, whose camera-to-sRGB
off-diagonals are negative and can push an in-gamut camera colour below zero in
sRGB. A third possibility covers neither: the values are small and *positive* and
simply underflow 16-bit. Those three demand three different responses, so guessing
between them was not acceptable.

Six rungs on `dry-erase-marker-head-cpl`, binary built from HEAD
(`6E1E2E86…41B3`), predictions registered before the first render:

| rung | removes | R | G | B |
| --- | --- | ---: | ---: | ---: |
| A shipped | nothing | 1.2320 | 1.2237 | 1.4648 |
| B `--camera-linear` | the colour matrix | 1.1841 | 1.2866 | 1.3815 |
| C `--sharpen 0` | the sharpening ramp | **0.0000** | **0.0000** | **0.0000** |
| D `--exposure 3` | 16-bit underflow | 1.1783 | 1.2835 | 1.3740 |
| E `--base-weighted` | *adds back* the old base band | 1.8510 | 2.0722 | 2.2442 |
| F `--bands 2` | all but one Laplacian band | 0.0466 | 0.0926 | 0.0667 |

- **The colour matrix is excluded.** A to B barely moves.
- **The values are genuinely negative, not underflowed positives.** Rung D
  multiplies by eight *before* quantisation and changes nothing, because
  `max(0, ·)` is scale-invariant in sign. A positive underflow would have been
  rescued. This is the rung that cost 116 seconds and settled a question three
  summary statistics could not.
- **The base-band flip in `23ae8dc` genuinely helped** — the old band is 60%
  worse — **and did not fix it.**
- **HEAD is not fixed.** Same site: control 0.000%, pinned blend 1.995%, HEAD
  blend 1.936%.

The first attempt at this ladder died at rung B with `unknown flag
--camera-linear`, because that flag landed in `0d9fd28`, *after* the pinned binary
was built. The script threw rather than skipping the rung. That is the only reason
the substitution to a HEAD-built binary was noticed and compensated for with rung
E, instead of silently comparing two different codebases.

### 18.3 The retraction that matters: rung C scores perfectly and destroys the image

Rung C reads **0.0000 in all three channels**. Perfect. Total elimination. I
drafted the sentence "sharpening is the cause".

Then I looked at the crop. **At `--sharpen 0` the ink mark is a faint featureless
grey smudge with no edge and no internal structure.** There is no stacking left in
it at all.

Obvious in hindsight. `sharpen_per_octave` is not an enhancement bolted onto the
merge; **it is the selection.** It ramps the selection exponent toward the fine
bands. Set it to zero, the weights go flat, and the merge becomes a plain average
across every focus position — the mean of a defocus sweep. Which is mush.

So the honest statement of the ladder is not "sharpening causes the defect". It is:

> **The out-of-hull excursion is monotone in selection peakedness, and selection
> peakedness is the thing that makes stacking work.**

Had the number alone been reported, the fix would have been "reduce the sharpening
ramp", every acceptance test would have gone green, and every photograph would
have gone soft. This is the same failure the flat-noise metric produced in 17.1 —
a metric named for what you hope it measures, believed as though it measured that
— arriving by a different route within the same week.

> **An acceptance number that can be satisfied by destroying the subject is not an
> acceptance number. Every quality gate needs a paired cost column, produced by
> the same script, so that neither can be reported without the other.**

### 18.4 The sweep: it is one band, and density and defect arrive together

Rung F needed the same scepticism, and got the opposite answer. **F is not
degenerate.** At `--bands 2` the paper fibres are crisply resolved, arguably
crisper than at bands 7. What F loses is low-frequency *density* — the ink renders
grey rather than black — for a legible reason: at bands 2 the base band sits at
440×293 for a 3520-wide plane, so a ~60 px ink blob is several pixels wide in a
band that is a plain **mean** across frames, and it averages with the frames where
it is defocused. Different failure mode, different lever. My first note to
BUILD-BLEND lumped C and F together and was wrong to.

Sweeping the band count, with an ink-density column (1st percentile of green in
the crop; low is correct dark ink, high is washed out):

| bands | R | G | B | ink p1 | per-band exponent (coarsest→finest) |
| ---: | ---: | ---: | ---: | ---: | --- |
| 2 | 0.0466 | 0.0926 | 0.0667 | 0.5806 | 2 3 |
| 3 | 0.0373 | 0.0609 | 0.0537 | 0.4802 | 2 3 4 |
| 4 | 0.0107 | 0.0145 | 0.0178 | 0.3317 | 2 3 4 5 |
| 5 | 0.0029 | 0.0026 | 0.0049 | 0.1822 | 2 3 4 5 8 |
| 6 | 0.0205 | 0.0248 | 0.0389 | 0.0795 | 2 3 4 5 8 8 |
| **7** | **1.1841** | **1.2866** | **1.3815** | 0.0000 | 2 3 4 5 8 8 8 |

Flat and negligible from 2 through 6, then a **52× step on the single addition of
the seventh band.** Not a smooth accumulation across the mid bands. One band.

And ink density improves *monotonically* with band count: 0.58, 0.48, 0.33, 0.18,
0.08, 0.00. The merge is driving the ink darker with every band added, which is
correct — the ink **is** dark in the frames where it is in focus — and at the
seventh band it overshoots straight past black. The 0.0000 is not better density;
it is the clamp eating the darkest percentile.

> **The excursion is systematically darkward on dark features, and it arrives in
> the same bands that carry the subject's correct density. The defect and the
> quality are produced by the same operation, which is why no band count resolves
> it.**

### 18.5 The mitigation that failed its own bar

In the crop strip, bands 6 is the best frame of the six: full ink density, sharp
fibres, no blocks. That is a one-constant change to the default and it was
tempting to recommend on the spot.

`dry-erase-marker-head-cpl` was chosen *because it fails hardest*, which makes it
the least representative capture available. So the condition was registered before
rendering: at least a 10× cut on both remaining failures, and the placebo unmoved
within 0.01 pt.

| subject | arm | R | G | B | p1 green |
| --- | ---: | ---: | ---: | ---: | ---: |
| `foam` | 7 | 0.6826 | 0.6441 | 0.9825 | 0.0014 |
| | 6 | 0.6519 | 0.5985 | 0.9380 | 0.0017 |
| `flower-bud-alone-cpl` | 7 | 0.3696 | 0.5365 | 1.3982 | 0.0051 |
| | 6 | 0.0763 | 0.1591 | 0.6189 | 0.0113 |
| `couch-fibers-cpl` (placebo) | 7 | 0.0000 | 0.0000 | 0.0000 | 0.0491 |
| | 6 | 0.0000 | 0.0000 | 0.0000 | 0.0511 |

**`foam` improves 1.0×. `flower-bud-alone-cpl` improves 2.3×.** The placebo is
inert, which is the one thing that worked as hoped. The 52× on
`dry-erase-marker-head-cpl` does not generalise at all.

**Do not change the default.** And the negative result is worth more than the
mitigation would have been:

> **The band count is not the mechanism. The same seventh band that is
> catastrophic on one subject is nearly irrelevant on another, so the excursion is
> content-dependent — which is an argument that the fix must be content-adaptive
> too. A constraint against the frame hull is content-adaptive by construction; a
> band count is not.**

Had the bar been set after seeing `dry-erase`, it would have been set at 10× and
declared met. It was set before, and it failed. That is the entire value of
pre-registration in one measurement.

### 18.6 Two of my own claims, retracted against BUILD-HALO's measurements

BUILD-HALO tested two things I asserted while reconciling its rim finding against
BUILD-CHROMA's index jumps, and both are refuted.

**Retracted: that the broad veil near the silhouette is the wrong-frame patch
field.** Binned on an *election-independent* silhouette (a `STREHL_ONLY_FRAME`
render, so the map cannot be a statistic of itself), extreme adjacent-pixel index
jumps are **zero in 231,610 background pixels within 20 px of the silhouette**,
and enriched 1.62× in the open field at 288–400 px. Not few. Zero. The patch field
is real, and it lives in dead ground — a featureless backdrop has no focus signal,
so the argmax is noise spanning the bracket — but it is *not* what sits at the rim.

**Retracted: that the box regulariser must invent an index between two modes.** I
argued that averaging indices 40 and 231 yields 135, at which neither depth is in
focus. `merge.rs::regularise` boxes the **focus field**, not the index field, and
the winner is an argmax over frames of the regularised field, so the elected index
is always one some frame actually attained. 135 can never be synthesised. Measured
rather than read off the source: only 11.8% of near-band pixels elect the middle
60% of the subject-to-background gap, far below the 60% a filled distribution
would give. Bimodal, not averaged. My argument was correct in the abstract and
false about this code, which is the more embarrassing of the two ways to be wrong.

BUILD-HALO's reframing is the part worth keeping, and it is a better result than
the claim it replaced:

> **The rim is not where the selector is uncertain. It is where the selector is
> confident and wrong.**

That kills every "detect low-confidence pixels and repair them" approach at once,
because they target a population that does not overlap the artifact.

### 18.7 What the fix has to be, and what it must not be

Not a lower sharpening ramp, not a capped exponent, not a reduced band count. Each
turns the acceptance number green and the photograph soft, and soft is the defect
this project exists to remove.

The remaining hypothesis, consistent with everything above and not yet proven: a
per-band convex combination is not convex overall,

```
  sum_b convex_k(band_b,k)  !=  convex_k( sum_b band_b,k )
```

so a near-argmax pick that differs between coarse and fine bands reconstructs a
pixel from a frame that never existed, and at ink-on-paper contrast that pixel
lands below black. The `SoftPower` guarantee — that a convex combination cannot
take adjacent coefficients from opposite-signed frames — holds *within* a band and
does not survive the sum across bands.

If that is right, the clamp is the messenger and the hull violation is the bug,
and the fix keeps the peaked selection while separately forbidding the
reconstruction from leaving the range the contributing frames actually span at
that pixel — with a margin set by the calibrated noise rather than an arbitrary
epsilon, so that genuine reconstruction gain remains possible and impossible
pixels do not.

Acceptance, registered here: all three merge-verdict subjects within +0.05 pt on
the linear 16-bit TIFF, `couch-fibers-cpl` unmoved at 0.0000, **and** the ink at
(6136, 1360) at least as crisp and as dark as bands 6 renders it. The last clause
exists because of 18.3.

## 18.8 Where the clipped pixels live, and a hypothesis of mine that died on the way

18.7 left the mechanism argued but its *location* unmeasured. Two instruments
settled it, and the second one killed the reading I had taken from the first.

### The masks

`zeromap.py` marks every exactly-zero pixel in red over the render and rings the
densest 64-px block, with the block chosen by a rule fixed before looking so that
the crop site cannot become part of the finding. Four subjects, camera-linear
where available:

| subject | zeros | densest 64-px block | share in top 0.1% of blocks |
| --- | ---: | ---: | ---: |
| `foam` | 1.2197% | 2820/4096 | 4.1% |
| `flower-bud-alone-cpl` | 1.4043% | **4096/4096** | 7.0% |
| `bee-1-cpl` | 0.1565% | 3679/4096 | 33.9% |
| `couch-fibers-cpl` | **0.0000%** | 0/4096 | 0.0% |

`flower-bud-alone-cpl` contains a 64-px block that is *entirely* dead. And the
placebo reads a clean zero out of 33 million pixels, which is worth more than it
looks: it means every number in this section is being read against an arm where
the instrument is known to be able to report nothing.

Read by eye, the masks told a story. `flower-bud-alone-cpl`'s red appeared to
trace the bud's silhouette; `foam`'s filled the pore interiors; `bee-1-cpl`'s sat
only on the dark legs, antennae and wing edge while the bright fur stayed clean.
So I proposed a two-factor mechanism: an **occluding edge** supplies the
bimodal through-focus curve that makes coarse and fine bands elect different
frames, and a **dark local pedestal** lets the resulting excursion cross zero.
It explained all four subjects, including why the placebo is inert — a fibre
tangle has no clean silhouette at the relevant scale.

### The test that refuted it

The story was built from looking at pictures, so it needed a measurement that
could contradict it. `risk2d.py` bins every pixel on a 5×5 grid of local
luminance × local gradient magnitude and reports the observed probability of
being clamped in each cell, against the probability an independence model
predicts from the two marginals. Equal-population quantile bins, so no cell can
look risky merely by being rare.

Both axes are measured on the **control** arm. Binning on the blend's own
luminance would have been circular: a clamped pixel has luminance zero by
construction, so the darkest bin would have been built out of the very pixels
being counted. This is the same precaution `BUILD-HALO` took when it binned
election jumps against a silhouette taken from a single-frame render rather than
against a statistic of the election itself.

Risk of being clamped, in %, *within the darkest luminance quintile*, as gradient
rises left to right:

| subject | grad 0 | grad 1 | grad 2 | grad 3 | grad 4 | corner obs/indep |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `dry-erase-marker-head-cpl` | 23.93 | 23.32 | 19.27 | 11.94 | **4.39** | 0.80× |
| `flower-bud-alone-cpl` | 14.69 | 14.58 | 14.74 | 14.47 | **10.63** | 0.24× |
| `bee-1-cpl` | 0.73 | 0.71 | 0.88 | 0.85 | 0.61 | 0.57× |
| `foam` | 4.93 | 4.46 | 3.65 | 2.87 | 7.92 | 7.76× |
| `flower-inner-edge-cpl` | 1.55 | 2.33 | 2.92 | 3.08 | 5.07 | 2.50× |

On the two worst subjects the risk **falls** as the gradient rises — monotonically
on `dry-erase-marker-head-cpl`, from 23.9% to 4.4%, a 5.5× decrease. Against the
independence model the dark-and-edgy corner is *under*-represented on three of
five subjects. **Edginess is not the second factor, and the occluding-edge story
is withdrawn.** I had over-read the masks: what looked like a line tracing
`flower-bud-alone-cpl`'s outline is a broad solid patch on the dark body of the
bud near the boundary, and `dry-erase-marker-head-cpl`'s blocks sit in the
*interior* of the ink rather than along its edge.

### What survived, and why it is now more believable

Darkness is necessary and very nearly sufficient, and it arrives as a cliff
rather than a slope. On `bee-1-cpl`, luminance quintiles 2 through 4 read
*exactly* 0.000 in every gradient bin and the step from quintile 0 to quintile 1
is two orders of magnitude, 0.73% to 0.003%. The same collapse holds on
`flower-bud-alone-cpl` and `dry-erase-marker-head-cpl`.

So the excursion lives in dark, **flat** regions. That converges with 18.4 from a
completely different direction: the 52× step arrived with the **coarsest**
Laplacian band, and coarse bands are by construction low-frequency and carry
flat-region content, so an inconsistency there produces exactly the broad
low-frequency excursion the risk map measures and exactly the block shapes the
crops show. Two instruments that knew nothing about each other now point at the
same object. That is the reason to believe it, and it is a better reason than
the one I had for the story it replaced.

The consequence for the fix is concrete: **do not gate the bound on gradient.**
An edge-targeted repair would miss the bulk of the defect and, on
`dry-erase-marker-head-cpl`, would aim at the least affected fifth of the dark
population.

One caveat rather than a footnote: the `-after` arms in `ORCH-100\_tiff` are
sRGB-developed, so some of their zeros come from the camera-to-sRGB matrix and
not from the merge — `dry-erase-marker-head-cpl` reads 2.55% here against 1.29%
in camera-linear. The absolute rates in that table are therefore mixed, and
`flower-inner-edge-cpl`, whose risk peaks in the *mid-tone* quintiles at 19–32%
unlike every other subject, is probably showing the matrix mechanism rather than
this one. The contamination does not plausibly manufacture a 5.5× monotone
decrease with gradient, which is the finding being acted on.

## 18.9 The acceptance gate, and its commissioning

18.3 recorded a candidate fix that scored a perfect 0.0000 on the clipping metric
and produced a featureless grey smudge. The lesson should not depend on anyone
remembering it, so it is now an instrument: `accept.py` refuses to print a
quality column without printing, from the same render, the cost columns that
destroying the subject would move.

- **Quality, wanted down:** `clip%`, pixels with any channel exactly zero in
  linear 16-bit.
- **Cost, wanted not-down:** `acuity`, mean |Laplacian| of green over pixels
  above the 20th luminance percentile, so it reports subject detail rather than
  noise in the black; `microC`, median local standard deviation in 8×8 tiles over
  the same lit population, an independent witness that a blur which preserved
  gradient energy by ringing would still fail; and `p1`, the 1st percentile of
  green, which must not *rise*, because that is ink going grey.

The rule was fixed before any candidate was measured: `clip% ≤ 0.02` on every
channel of every subject, `acuity` and `microC` at or above 98% of reference, and
`p1` rising by no more than 2% of range.

A gate is a claim about an instrument, so it was commissioned against a
known-potent sabotage with the verdict written down first. The registered
prediction was that arm C must fail, and must fail on the **cost** columns rather
than on clipping, since it scores a perfect zero there.

| arm | clip% | acuity | microC | p1 | verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| `A-shipped` (ref) | 1.6777 | 521.2 | 232.20 | 0 | reference |
| `C-sharpen0` | **0.0000** | 205.7 | 144.06 | 715 | **FAIL: acuity 39.5%, micro 62.0%** |
| `F-bands2` | 0.1066 | 371.0 | 193.09 | 1133 | FAIL: clip, acuity 71.2%, micro 83.2% |
| `E-baseweighted` | 2.3951 | 428.1 | 208.95 | 0 | FAIL: clip 2.2442% |
| `B-camlin` | 1.5212 | 430.7 | 208.38 | 0 | FAIL: clip 1.3815% |
| `D-exposure3` | 1.5181 | 768.8 | **0.00** | 0 | FAIL: micro 0.0% |

`C-sharpen0` was rejected on the cost columns alone, as registered. `D-exposure3`
self-caught for a reason worth keeping: at +3 stops the lit population saturates,
local variance collapses to zero, and the gate refuses an arm that is not
comparable rather than scoring it. Five arms judged, none unjudgeable, five
accounted for.

Two limits are worth stating plainly. Passing the gate is necessary and not
sufficient — the 100% crop at a rule-fixed site is held back from the authors and
the photograph outranks the table. And the gate compares arms, so candidate and
reference must be rendered with identical flags in the same colour space;
`B-camlin` reading 82.6% acuity against an sRGB reference is the instrument
detecting a colour-space mismatch, not a defect in the merge.

# 19. The frames are not the same exposure, and nothing corrects for it

This began as a failed measurement. 18.8 established *where* the clamped pixels
live; the halo needed the same treatment, so `halo.py` was built to measure the
veil as a radial profile of background level against distance from the
silhouette, with two paired cost columns — rim sharpness and background noise —
so that a repair could not flatten the profile by softening the edge or smearing
the background.

**Its commissioning failed, on a prediction registered before the run.** The
prediction was that the merge would show a larger veil than any single frame,
since the halo is a stacking artifact. It does not. The merge reads −31.61% and
the ten single frames run −38.20% to −42.03%: the merge has the *smallest* veil
of any arm measured. The metric is dominated by the defocus penumbra, which is
physically present in every frame and swamps whatever the merge adds. As a halo
gate it is dead, and it is recorded here as dead rather than quietly rebuilt.

What it did do was print a column nobody had asked it for.

## 19.1 The measurement

The far-field background level was not constant across the bracket. It climbed,
monotonically, frame after frame. So the trend was re-measured in a way that
shares nothing with the first method — a fixed 64-px border frame read at
*identical absolute pixel coordinates* in every image, with no threshold, no
subject mask and no distance transform, so that nothing in the measurement can
move when the subject changes size.

`flower-bud-alone-cpl`, camera-linear:

| frame | borderR | borderG | borderB | centreG | cornerG |
| --- | ---: | ---: | ---: | ---: | ---: |
| f025 | 16541 | 17063 | 16556 | 1701 | 17598 |
| f051 | 16931 | 17458 | 16947 | 1748 | 18039 |
| f076 | 17316 | 17854 | 17332 | 1774 | 18468 |
| f127 | 18129 | 18696 | 18158 | 1818 | 19407 |
| f153 | 18561 | 19141 | 18591 | 1845 | 19919 |
| f178 | 18958 | 19540 | 18980 | 1898 | 20386 |

- **Strictly monotone: 5/5 ascending steps on all five independent measures.**
  Reported as a step count rather than asserted by eye, so a noisy sequence could
  not have read as a trend.
- **Span 14.5%** across these six frames, and **+19.0%** across the full bracket
  from f0 to f204.
- **Achromatic** — 14.61%, 14.52%, 14.64% on R, G, B, agreeing to 0.12%. So it is
  exposure, not white balance or illuminant colour.
- **Global rather than vignetting** — border and centre move together.
- **Multiplicative rather than additive**, and this discriminates cleanly: the
  border gains **+2477 DN** while the centre gains **+197 DN**, an order of
  magnitude apart in absolute terms, while the *ratios* are 1.145 and 1.116. An
  additive pedestal shift would have moved both by the same DN.

These are aligned renders, so a border sample could in principle be reading warp
padding rather than photometry, and a bracket whose frames are scaled by
different amounts would manufacture exactly this trend. The control was already
in hand: `halo.py` had measured a **mid-field annulus 300–600 px from the
subject**, spatially disjoint from the border frame, and it spans **14.06%**
against the border's **14.52%**. Two samplings with nothing in common agree to
half a point. The trend is in the photometry, not in the warp.

## 19.2 Nothing in the pipeline corrects it

`pyramid.rs`, `merge.rs` and `blend-render.rs` contain no per-frame photometric
gain or offset. The repository's 379 matches for "normalis" are all *focus-field*
normalisation — the focus **response** divided by luma sigma — which is a
different quantity and does nothing to pixel levels. The merge is compositing
frames that differ by up to a fifth in exposure.

## 19.3 Why this is the leading candidate for the clamp

The coarsest pyramid bands carry the low-frequency content, and a whole-frame
level difference is exactly low-frequency content. Electing different frames in
different bands therefore mixes **incompatible pedestals**, and the resulting
error is broad, low-frequency, and largest where there is nothing else in the
band — that is, in flat regions.

Set that against what was already measured, independently and earlier:

| prediction of the pedestal-mismatch mechanism | already measured |
| --- | --- |
| error is born in the coarsest band | 52× step on the 7th band alone (18.4) |
| error is broad and low-frequency, worst in flat areas | clip risk *falls* 23.9% → 4.4% as gradient rises (18.8) |
| reconstruction leaves the per-pixel frame hull | attributed in 18.7 |

Three measurements taken for unrelated reasons, one mechanism that predicts all
three. That is the reason to take it seriously, and it is still a hypothesis.

**It may also be the halo.** If the selector elects a different frame on either
side of an occluding boundary — and at a rim it certainly does — then even a
*correct* focus decision imports a frame whose exposure differs by up to 19%,
and the result is a brightness step hugging the subject, which is what an aura
is. That would sharpen BUILD-HALO's keeper finding rather than contradict it: the
rim is where the selector is confident and right about focus, and wrong about
exposure. The amplitude is checkable — elected-index jump across the rim,
multiplied by the per-frame level drift — and that check has been handed to the
lane that holds the rim instrumentation.

## 19.4 The form is not settled, and a correction I had to issue

The first brief sent to the implementing lane said a per-frame **scalar
multiplicative gain** was justified and told it not to start with gain+offset or
a spatial field. That was drawn from one subject, which is the exact error this
document has refused to let anyone else make. The generalisation check that
should have preceded it was then run.

`pen`, same mask-free method:

| measure | span | monotone |
| --- | ---: | --- |
| borderR | 46.00% | 2/2 |
| borderG | 46.69% | 2/2 |
| borderB | 31.25% | 2/2 |
| centreG | 25.96% | 2/2 |
| cornerG | 76.38% | 2/2 |

The finding survives and grows — the trend is three times larger here — but the
*form* does not. On `pen` it is **chromatic** (blue spans 31% against red and
green at 46%, where `flower-bud-alone-cpl`'s channels agreed to 0.12%),
**spatially non-uniform** (corner 76% against centre 26%, a factor of three), and
neither pure gain nor pure offset: border ×1.467 / +1829 DN against centre ×1.260
/ +3285 DN, so equal ratios and equal differences both fail. The instruction was
withdrawn and replaced with: fit the model, do not assume it, and let the
residual argue for any term beyond a scalar.

One confound is explicitly **not** ruled out on `pen`. It is a bright subject on
a dark background, the opposite polarity, and the border ring has not been
verified free of subject in every frame; if the pen reaches into the border, then
breathing alone would change the sampling mix and manufacture a monotone trend
with no photometric cause. `flower-bud-alone-cpl` is the trustworthy measurement
— plain background, subject far from the edge, channels agreeing to 0.12%, and
the disjoint-annulus control above. `pen` corroborates that a large trend exists
and warns that the model may need more than a scalar; it does not specify one.

## 19.5 The registered test

Normalise each frame photometrically upstream of the pyramid decomposition, and
clipping on `dry-erase-marker-head-cpl` must fall substantially **with
sharpening, exponent and band count all untouched** — none of the levers that
have repeatedly bought a better number by turning the stacker off.
`couch-fibers-cpl` stays at exactly 0. `accept.py`'s cost columns hold: `acuity`
and `microC` at or above 98% of reference, `p1` not rising.

If clipping does not fall, the leading candidate is dead, and that is worth as
much as a confirmation — it would remove the only mechanism currently predicting
all three of the measurements in 19.3.

One implementation hazard is worth stating because getting it wrong would be
invisible: **the noise model must see the gain.** σ²(S) is signal-dependent, so
rescaling pixel values rescales their noise, and a gate comparing band
coefficients against a noise floor computed before normalisation would
miscalibrate — most severely in the lit low-contrast regions where the merge is
already weakest.

## 19.6 Three corrections, two of them to me

Sections 19.1 to 19.5 were written before I read the corpus on this subject. Then
the pipeline's own console output mentioned a brightness change "with CONSTANT
EXIF", which is not the sort of phrase a tool prints about something nobody has
studied. It had all been measured already.

**Correction 1 — this is not new, and a design already exists.** M24 measured the
drift and holds facts 180 to 182; `M18-merge-implemented.md` §4d specifies the
implementation in three steps — fit in pass one alongside the focus field at one
scalar per frame and no extra decode, carry as a `Vec<f32>` of length `frames` on
the `Plan` so the memory ratchet is untouched, apply inside the fold to the
signal and the sigma together — and closes: *"Not built tonight. Stated so it is
a decision, not an oversight."* What 19.2 correctly reports is that it is
**unbuilt**. What it wrongly implied is that it was **unknown**. Anyone building
this reads M18 §4d and §4f first.

**Correction 2 — the gate does not need fixing, and 19.5's hazard note was
operationally wrong.** M18 §4d already resolves it: gating on `(L_k / g_k)`
against `σ(L_k) / g_k` is identical to gating in native units with σ evaluated at
the frame's own observed level, so *native-units gating is automatically correct
under an unknown gain, and it is what ships*. The gate is already immune. The
**reconstruction** is not, because the frames still differ in level when their
bands are summed. Apply the gain to signal and sigma together and the existing
gating stays correct; adding a separate correction to the gate would introduce
the error it was meant to prevent.

**Correction 3 — I prescribed a falsified estimator.** The brief I sent said to
fit the gain with *"a median over a large sample, not a mean over everything."*
M28 measured precisely that to be wrong, and M18 §4f records it: a median over a
subject-centred crop reads **4.28%** peak-to-peak where the plain mean over all
pixels reads **1.02%**, against M24's independent full-frame **0.91%** — because
subject contrast changes as focus sweeps, so a regional robust statistic absorbs
*focus* signal into what it calls gain. Restricting to low-gradient pixels was
the worst of four estimators, 84.98% against 11.05%. §4f's own comment on the
earlier version of this mistake is exact: *"What was wrong was the instruction I
left behind, which is exactly the kind of thing that gets built verbatim six
weeks later."* The instruction was withdrawn within the hour, and the correct
estimator is the plain arithmetic mean over all pixels.

That correction also indicts this document's own instrument, since `framelevel.py`
reported a **border median**. It was re-run against the prescribed estimator on
the same frames:

| subject | meanAll G | medBorder G | median / mean |
| --- | ---: | ---: | ---: |
| `flower-bud-alone-cpl` | **19.44%** | 14.52% | 0.75× |
| `dry-erase-marker-head-cpl` | **45.19%** | 35.93% | 0.79× |
| `couch-fibers-cpl` | **19.11%** | 17.47% | 0.91× |

The median **under**-reported by 9 to 25%, the opposite of M28's inflation
direction, so 19.1's figures were conservative rather than overstated. Under the
correct estimator the channels still agree — 19.25 / 19.44 / 19.98 on
`flower-bud-alone-cpl` — and every sequence is still strictly monotone. The drift
is **2 to 5 times larger than the corpus's recorded 6.84% and 8.93%**.

## 19.7 The cross-subject test, and the model it forces

If drift causes the clamp, the subject that clips most should drift most. Three
stacks, single-frame renders from one pinned binary, measured with the prescribed
mean:

| subject | clip%, camera-linear | drift, meanAll G |
| --- | ---: | ---: |
| `dry-erase-marker-head-cpl` | 1.29 | 45.19% |
| `flower-bud-alone-cpl` | 1.40 | 19.44% |
| `couch-fibers-cpl` | **0.0000** | **19.11%** |

**The prediction fails on the control, and that is the useful part.**
`couch-fibers-cpl` carries essentially the same drift as `flower-bud-alone-cpl`
— 19.11% against 19.44% — and clips exactly zero pixels out of 33 million. Drift
alone does not predict clipping, and the hypothesis as stated in 19.3 is
incomplete.

What fits all six subjects is two factors, not one:

1. **Photometric drift between the frames elected in different bands** supplies a
   broad, low-frequency excursion.
2. **A dark local pedestal** lets that excursion cross zero.

`couch-fibers-cpl` is a mid-tone fibre tangle: factor 1 at 19% without factor 2,
so nothing clips. `dry-erase-marker-head-cpl` has 45% drift *and* black ink. And
the model predicts the `bee-1-cpl` map exactly — drift is global, yet clipping
appears **only on the dark legs, antennae and wing edge** while the bright fur
stays clean, which is what 18.8's zero map shows. It is also 18.8's risk-map
result restated: darkness is a cliff, with luminance quintiles 2 through 4
reading *exactly* 0.000.

This is the same two-factor shape proposed in 18.8 with the **first factor
replaced**. That section argued factor 1 was occluding edges; the gradient test
refuted it. It is photometric drift. The second factor was right the first time.

The control has also acquired teeth. `couch-fibers-cpl` is no longer merely a
subject that happens not to clip — it is a stack carrying **19% photometric
drift** that must remain at exactly 0 clipped pixels through a change that
visibly alters its levels. A normalisation that moves it is touching something
other than this defect.


## 20 The gap is unwired code, not unwritten code

Sections 19.6 and 19.7 cost me three retractions, and all three had the same
root: I reasoned from the plan instead of from the tree. I told an implementer
to build a per-frame photometric gain. `crates/strehl-core/src/photometric.rs`
turned out to be **1966 lines**, already implementing the exact estimator M28
prescribed, already wired into `merge_cmd.rs` with 34 references and a
`--photometric off|on|auto` flag with an env twin whose parser treats an
unrecognised value as an error rather than a silent `On`. It was not missing. It
was **off**, and absent from the merge path that actually produces our images.

That is a specific enough failure to be worth generalising, so I stopped
arguing and measured it.

## 20.1 The reachability sweep

`ORCH-CLAMP\wiring.py` takes the 22 modules declared in
`crates/strehl-core/src/lib.rs` and counts, for each, references from the shipped
CLI (`crates/strehl-cli/src/**`), from other core modules, and from examples
(`crates/*/examples/**`). A module is **live** if the CLI references it, or if
any live module references it — a fixed point, so transitive reachability
counts. Anything else is **dark**: present, compiled, and unreachable from the
binary the user runs.

**19 of 22 modules are live. Three are dark, totalling 3403 lines.**

| module | loc | example-only refs | what it is |
| --- | ---: | ---: | --- |
| `pyramid` | 1898 | 4 | the multi-scale merge that produces every good render |
| `outlier` | 1148 | 8 | per-tile, noise-normalised chi-square robustness mask |
| `restore` | 357 | 0 | Wiener correction for the resampling kernel |

The 19/22 is what makes the result trustworthy. A sweep that flagged most of the
tree would be measuring my regex, not the code. This one flags three modules,
and they are not arbitrary three.

## 20.2 They are the three that decide image quality

- **`pyramid`** is the merge. Every render in this document that looked better
  than the shipped one came from an *example* binary. `merge_cmd.rs` contains
  zero pyramid references, so `strehl stack` — the command the user runs — does
  not execute the merge this project spent its nights building.
- **`outlier`** is the robustness mask that the corpus has repeatedly listed as
  missing and never built. It is written: `chi2_map`, `thresholds`, `mask`,
  `mask_tiles`, `fired_fraction`, tile grid and scratch. Its only callers are
  four experiment binaries.
- **`restore`** carries its status in its own header: *"Status: BUILT, MEASURED,
  and NOT WIRED IN."* It attributes **18.6% of the shipped merge's blur
  variance** to the resampling kernel — the second largest blur term after the
  optics — and implements the correction. It has **zero** references anywhere,
  including examples.

Add `photometric`, which is live but defaults `Off` and never reaches the
pyramid path, and the pattern is four for four: the components that would most
improve the picture are the components that are not connected to it.

## 20.3 Why this is the honest answer to "why does the output look bad"

The reflex when output disappoints is to look for a missing algorithm. This
project's disappointing output is not caused by a missing algorithm. Its merge,
its robustness mask, its resampling restoration and its photometric correction
are all written, several are measured, and none of them is in the path.

There is a mechanism behind that and it is not carelessness. Every one of these
was built inside an experiment or an example, where it could be measured against
a control — which is exactly the discipline that makes this corpus worth
anything. What was missing was the step after the measurement: the demonstration
was the deliverable, and the wiring was left as an implied afterthought that
nobody's milestone owned. `restore.rs` even says so in its own header, in the
present tense, and has said so for as long as it has existed.

The corollary is a rule, and it is stated as one because the failure repeated
four times:

> **A component is not built until a shipped binary can reach it.** A measured
> improvement that no default path executes has not improved anything. State the
> integration point, or state explicitly that it is deferred and why — the way
> M18 §4d did, which is the one instance in this corpus that handled it
> correctly: *"Not built tonight. Stated so it is a decision, not an oversight."*

## 20.4 Standing work

Ownership is serialised, because these all want to land in overlapping files:

| module | owner | boundary |
| --- | --- | --- |
| `pyramid.rs` | BUILD-BLEND | clamp fix, then photometric wiring |
| `focus.rs`, `merge_cmd.rs` | BUILD-HALO | halo mechanism, then the CLI wiring |
| `restore.rs` | BUILD-SHARP | integration point to be justified, patches to `pyramid.rs` handed over, not applied |
| `outlier.rs` | unassigned | pending the admitted-set measurement in 22.7 |

`outlier` is deliberately unassigned. Wiring a robustness mask is the right fix
only if the halo's amplitude is coming from the gate's admitted set, and that has
not yet been measured. Assigning it before the measurement would be building the
fix that the story suggests rather than the one the data supports, which is the
error this section exists to record.

## 20.5 The same pattern in a second form, and the case against my own framing

Modules are one way to be unreachable. A switch is another, and `strehl` has 23
of them. `scripts/check-defaults.py` partitions every one found in `crates/`
into quality-reachable, quality-dark, control, and diagnostic, and the partition
sums to the count of switches found — so a switch cannot be skipped and read as
audited.

**Three quality switches default off.** One of them, `STREHL_FIX_CA`, the audit
labels *"THE ORIGINAL DARK FEATURE"*: lateral-CA correction, finished long ago at
**R² = 0.9969** and **−704.5 ppm**, removing **61–67% of corner colour fringing**
and taking blue displacement from **0.363 px to 0.059 px** — and unset in every
render the owner has ever seen. The visible coloured speckles in our output were
this, and the fix was already in the tree. It is now being made default-on behind
an EXIF gear guard, which is the mechanism the project's founding brief asked for:
*"the camera + lens specifics should be pluggable too, to enhance stacking for
gear where available (but optional)."*

That is 20.3's rule again in a second form. **But the third dark switch refutes
the general reading**, and it is the more important entry.

## 20.6 `Off` can be a defended position, and mine was the lazy reading

I assumed `STREHL_PHOTOMETRIC=off` was a stale default chosen when the measured
drift was 7%, and that my 19–45% would simply overturn it. The audit records
otherwise:

- **M122** ran a **pre-registered 14-stack promotion test** and returned
  **KEEP-OFF** on its no-harm criterion K2 — and its **worst-harm subject was
  `flower-bud-alone-cpl`**, `hf1-on-hf0` slope **0.9444**. That is the same
  subject we use as the halo acceptance target.
- **M125** built the `auto` mode and **honestly declined to promote it**: 104% of
  its margin came from a single stack.

So the default was not neglected. It was tested twice and defended twice. My
drift measurement raises the question again; it does not settle it, and 20.3's
rule does not license flipping a switch merely because it is off.

There is also a trap inside `auto` that would have wasted a night. Its domain is
`AUTO_FRAMES_DOMAIN = 33..=100` frames, and this corpus's stacks are **205 and
299 frames**. **`auto` abstains on every subject we care about.** I had already
instructed an implementer to A/B `auto` against `off`; both arms would have been
identical, the correct report would have been "no difference", and we would have
recorded a null that measured nothing but the domain guard. The instruction was
corrected to `on` against `off`. **A switch that cannot fire on the corpus it is
evaluated against produces a null indistinguishable from a real one.**

## 20.7 The contest, and an A/B that is void by construction

The photometric entry is flagged **OPEN AND CONTESTED**, and the two claims
cannot both be true:

- A verifier measured `on` **recovering +1415 DN of aura** on
  `flower-bud-alone-cpl` — roughly **a third** of the −3787 / −4293 DN aura
  measured independently by two instruments.
- M122 measured that same subject as `on`'s **worst harm**, by a
  high-frequency energy statistic.

The live reconciliation is **H-SEAM**: that M122's "lost fine structure" is
**election-seam step edges — the artifact itself** — which an energy statistic
*with no spatial argument* cannot distinguish from signal. If H-SEAM holds, M122
scored the removal of a defect as damage, and a default rests on a metric that
cannot tell a seam from a feather. The decisive test is therefore **spatial, not
energetic**: not how much high-frequency energy `on` costs, but **where**. Energy
is the instrument under suspicion and cannot adjudicate its own case.

The third dark switch supplies the sharpest instrument lesson of the three.
`STREHL_FIX_HALO` carries two unresolved defects, and the first is fatal:

> `report()` and `report_statistics()` at `merge_cmd.rs:2083-2085` run **before**
> the halo pass at `:2088`.

**Every A/B conducted on those printed statistics is null by construction** — the
numbers are produced before the thing under test has run. The second defect
compounds it: `=1` without `--out` is a silent no-op **that still prints an ON
banner**. A harness that reports before it acts, and announces an effect it did
not apply, will return a confident, reproducible, precisely-formatted null
forever. It is worth stating as a general check, because nothing in the output
looks wrong:

> **Confirm that an A/B harness reads its numbers after the code path under test
> has run.** A switch that prints an ON banner is not evidence that it did
> anything, and a statistic printed before the pass is not evidence about the
> pass.

## 21 The two merges, measured against each other cleanly

Section 20 established that `pyramid` is unreachable from the shipped binary.
It did not establish that it is better. Those are different claims and only the
first had evidence, so this section supplies the second — and the first attempt
at it was wrong in a way worth recording.

## 21.1 A confounded run, and the three things it conflated

I staged the four matched `bm\<subject>-{ctrl,blend}.tif` pairs an implementer
had produced and ran the acceptance gate on them. It reported the pyramid arm
failing on all four subjects, clipping **3.01%** of `flower-bud-alone-cpl` and
losing up to **26%** of acuity. Both figures were wrong, because that comparison
varies **three** things and attributes all of them to the merge:

1. **The merge.** `strehl.exe stack` — *"regularised winner + noise-gated
   average (THE DEFAULT PATH, an estimator)"* — against `blend-render.exe` —
   *"LAPLACIAN MULTI-BAND MERGE (an experiment, not the ship path)"*. The
   intended variable.
2. **Lateral CA.** The harness sets `STREHL_FIX_CA` globally, and **only
   `blend-render` honours it.** The pyramid logs print `lateral CA: CORRECTING,
   profile "a7c2-fe100gm-2xtc-x4cpl"`; the legacy logs print no CA line at all.
3. **The tone curve.** Both arms are `--srgb` *viewing* renders whose fitted
   curves **differ**: `black 0.009852, white 0.354584` against `black 0.000000,
   white 0.366762`.

Point 3 is this document's own standing rule — measure in linear, never on a
viewing render — broken by me, in the same night that another lane caught the
identical error in `trend.py`, where gradient RMS scaling with global contrast
turned "20 of 26 softer" into 11. The confound is not exotic. It is the house
error.

## 21.2 The trap the correction then walked into

Re-rendering with `STREHL_FIX_CA` and `STREHL_PHOTOMETRIC` explicitly unset and
both arms camera-linear produced a legacy file of **47.2 MB** against a pyramid
file of **188.8 MB** — exactly 4×, because dropping `--demosaic` gives the
**binned** 3520x2344 CFA output while `blend-render` writes full-resolution
7040x4688. A gradient statistic compared across a 4× resolution mismatch is
meaningless. Adding `--demosaic` to the legacy arm alone — camera-linear is the
absence of `--srgb`, not the absence of `--demosaic` — brought all four files to
188.8 MB and shape `(4688, 7040, 3) uint16`, with both self-describing as
*"Linear camera-native RGB … THIS IS NOT sRGB … This is the measurement
output."*

Two confounds, both introduced while fixing the previous one. Neither would have
been visible in the output numbers.

## 21.3 The clean comparison

One pin (`tree-lin-0d9fd28`, `strehl E48853C0…`, `blend-render 19786CC7…`), CA
and photometric explicitly unset, both arms camera-linear at matched resolution,
`--gate 4` on both. Only the merge differs.

| subject | arm | clip% | acuity | microC | p1 |
| --- | --- | ---: | ---: | ---: | ---: |
| `couch-fibers-cpl` | legacy | 0.0000 | 290.3 | 274.76 | 3076 |
| | **pyramid** | 0.0000 | **260.6 (89.8%)** | **299.35 (+8.9%)** | 3212 |
| `flower-bud-alone-cpl` | legacy | 0.0001 | 108.7 | 43.67 | 1028 |
| | **pyramid** | **1.4015** | **99.2 (91.3%)** | 44.42 (+1.7%) | 339 |

**Cleanly attributable to the merge:**

- **Clipping: 1.4015% against 0.0001%**, about 14,000×. Not the 3.01% I first
  reported — over half of that was tone and CA. But 1.40% is the figure this
  document has carried since 18.x, it now has a clean attribution, and it is the
  defect.
- **Acuity: about 10% lost on both subjects**, 89.8% and 91.3% — not 74-83%.
  Roughly half the apparent loss was confound. The surviving half matters most
  where it is cleanest: **`couch-fibers-cpl` has no silhouette and therefore no
  artifact to inflate its reference, and the pyramid arm still loses 10.2%.**
- **Micro-contrast rises on both**, +8.9% and +1.7% — a win the legacy path
  cannot reach.
- **`couch-fibers-cpl` clips exactly 0 in both arms.** The placebo holds under
  the clean protocol, which is also the evidence that the protocol works.

## 21.4 What the gate cannot see, and the rule that follows

At 1:1 on the rim of `flower-bud-alone-cpl`, the legacy merge has replaced the
subject's entire edge with a flat grey low-frequency smear with the hairs wiped
out; the pyramid render is a dark saturated bud with clean hairs against a clean
white field. One is a photograph. It is not close, and the gate scores the
photograph as the failure.

The gate is not malfunctioning. It is answering a frame-wide question about a
local catastrophe: the smear covers a small fraction of the frame, so a
frame-wide mean gradient barely moves, and the smear's own banding may raise it.
That is now the **third** instance of one failure in a single night:

- M122's high-frequency **energy** statistic cannot distinguish an election seam
  from a feather — which is why H-SEAM is testable at all.
- `trend.py`'s **gradient RMS** could not distinguish blur from global contrast.
- `accept.py`'s **global acuity** cannot distinguish "10% softer everywhere"
  from "one region annihilated".

> **A global scalar cannot adjudicate a localised defect.** When a metric and the
> eye disagree, and the defect under discussion is spatially confined, the metric
> is answering a different question — resolve it spatially before believing
> either.

So `acuity 89.8%` does not mean the legacy merge is sharper. It means the pyramid
merge is about 10% softer **on average**, and where has not been measured. That
measurement is worth an hour, because a uniform softness is repayable by
`restore.rs` — which is dark, and which attributes 18.6% of the merge's blur
variance to the resampling kernel — while a structured loss is not.

## 22 The hour, spent: the softness was never the merge

The hour was spent and it did not return the answer it was sent for. There is no
uniform softness to repay, because there is no softness. The 10% was the
instrument.

Four measurements, in the order they were taken, each with a ref-vs-ref null that
returned exactly `0.00e+00` before any real number was read. Pin
`tree-lin-0d9fd28`, both arms camera-linear, `STREHL_FIX_CA` and
`STREHL_PHOTOMETRIC` unset in both, matched resolution.

## 22.1 The loss is structured, and monotone in sharpness

`acuitymap.py`, 128 px tiles, lit population taken from the reference only so the
partition cannot be shaped by the arm under test. `couch-fibers-cpl`, 1978 tiles
judged of 1980:

| quintile by reference sharpness | ref acuity | blend/ctrl |
| --- | ---: | ---: |
| q0 flattest | 214.8 | 0.7974 |
| q1 | 253.0 | 0.8821 |
| q2 | 283.0 | 0.9320 |
| q3 | 319.5 | 0.9511 |
| q4 sharpest | 416.0 | 0.9868 |

Perfectly monotone, and 29.8% of tiles *gain* acuity, to a maximum of 1.7020. The
frame-wide 0.9020 is the average of a 20% deficit in the flattest fifth and a 1.3%
deficit in the sharpest. Whatever this is, it is concentrated exactly where there
is least detail to lose.

## 22.2 Not blur: a band-pass gain of up to 34%

Two mechanisms produce a deficit that grows as detail falls, and they have
opposite consequences. Averaging where no frame wins removes noise and scales the
high-frequency plateau down by roughly a constant. A low-pass rolls off toward
Nyquist and takes real detail with it. The radially averaged amplitude ratio
separates them: flat in frequency is noise, monotone falling is blur.

`spectralratio.py`, `couch-fibers-cpl`, flattest quintile, 216 tiles:

| f/Nyq | 0.02 | 0.10 | 0.19 | 0.27 | 0.35 | 0.44 | 0.52 | 0.60 | 0.69 | 0.77 | 0.85 | 0.94 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| amp ratio | 1.046 | 1.038 | 1.071 | 1.175 | 1.254 | 1.315 | **1.341** | 1.238 | 1.061 | 0.961 | 0.940 | 0.972 |

It is neither. It is a band-pass **gain**, peaking at **+34% near half-Nyquist**,
with a ~5% deficit confined to the top octave. The sharpest quintile has the same
shape at a peak of 1.158. The pyramid merge is not softer than the legacy merge
anywhere except the last octave.

The script's own verdict line read `FALLING toward Nyquist -> consistent with
BLUR`, because it summarised the curve as a high-half mean minus a low-half mean
and a band-pass looks like a fall from that vantage. The verdict was wrong and the
evidence rows above it made that visible in one read, without a re-run. Fifth
instance of the rule; first instance of the rule paying for the discipline that
was adopted in response to it.

## 22.3 The gate was rewarding the one octave the optics have destroyed

`accept.py`'s `acuity` is the mean `|Laplacian|` over the lit population. The 3×3
Laplacian's frequency response is `4 − 2cos(2πu) − 2cos(2πv)`: zero at DC, rising
monotonically, maximal at Nyquist. The statistic is dominated by the top octave
and nearly blind to the mid-band.

So it weights hardest precisely the band that facts 12 and 28 say carries almost
no optical information on this rig — marked f/11 is effectively f/33, and
MTF@Nyquist is 0.036 at f/5.6 at m=2.0 — and it is blind to the band where the
merge gains a third. In the flattest tiles it is worse than that: `|Laplacian|`
against a white noise floor is a noise meter, and the gate was scoring noise
suppression as lost detail.

`acuity 89.8%` was never a measurement of sharpness. It was a measurement of the
top octave, taken with an instrument that could not see anything else.

## 22.4 Two defects, not one, and the second is not the merge's

`clipvsloss.py` partitions tiles by whether the test arm clips, and — the part
that matters — bins on reference amplitude first, so that contrast cannot confound
clipping. `couch-fibers-cpl` clips nowhere in either arm and serves as the
placebo: 1083 tiles, all clip-free, amplitude ratio **1.0408**.

`flower-bud-alone-cpl`, matched on reference amplitude:

| quintile | clean n | clean ratio | dirty n | dirty ratio |
| --- | ---: | ---: | ---: | ---: |
| q0 amp~99 | 306 | 1.0153 | 0 | — |
| q1 amp~113 | 307 | 1.0084 | 0 | — |
| q2 amp~123 | 307 | 1.0091 | 0 | — |
| q3 amp~135 | 307 | 1.0214 | 0 | — |
| q4 amp~241 | 301 | **0.8591** | 6 | **0.4495** |

In four of five quintiles the pyramid merge beats the legacy merge on a real
amplitude measure. Two separate defects sit in the fifth: six tiles annihilated by
the clamp, and a deficit in 301 tiles that contain no clipped pixel and that
clipping therefore cannot explain. They have different owners and had been sharing
one number.

## 22.5 A retraction: I let the arm under test define its own population

Between those two measurements I told BUILD-BLEND that the clipping was entirely
in the dark population and that no fix should touch lit pixels. That was false,
and the error was the one this document has spent the night finding in other
people's work. `rail.py` computed the lit mask from **each arm's own green**:

```python
a = tifffile.imread(arm); g = a[:, :, 1]
thr = np.percentile(g, 20.0); lit = g > thr
```

A pixel lit in the reference and driven to black by the clamp is dark under
blend's own threshold. The defect deleted itself from its own measurement.
Partitioned on the reference instead, which is the only defensible choice:

| clip cell | ref % | test % | rise |
| --- | ---: | ---: | ---: |
| black_lit | 0.0000 | 0.0401 | +0.0401 |
| black_dark | 0.0000 | 1.3614 | +1.3613 |
| white_lit | 0.0000 | 0.0000 | +0.0000 |
| white_dark | 0.0000 | 0.0000 | +0.0000 |
| TOTAL | 0.0001 | 1.4015 | +1.4014 |

0.0401% of 33 Mpx is about 13,200 pixels of lit subject turned black. Retracted
and corrected to the owner within the hour. The rail split survives: the highlight
end is genuinely clean.

> A reference population computed from the arm under test is not a reference. It
> is the defect grading its own exam.

## 22.6 The gate, rebuilt

`accept2.py` replaces `accept.py` for this decision. `accept.py` is left untouched
so every number already in the record stays reproducible. Three changes, one per
failure:

1. **Amplitude ratio per reference-amplitude quintile, gate binding on the
   worst.** A frame-wide mean cannot separate "1% softer everywhere" from "the
   silhouette is destroyed".
2. **The gate binds on the mid-band, 0.2–0.7 f/Nyq.** The top octave is reported
   and deliberately does not bind, for the reason in §22.3.
3. **Clipping split rail × population into four cells that sum to the printed
   total.** A defect that *moves* between populations can no longer read as a
   defect that was *fixed*.

It refuses to print a verdict until every arm scores exactly `1.0000` against
itself. Both subjects returned `0.00e+00`.

The verdict inverts. `couch-fibers-cpl` **PASSES** — all five quintiles
1.0268–1.0528, band low 1.0361 / **MID 1.1081** / high 0.9571, zero in all four
clip cells — on the same file `accept.py` failed at 0.9020.

## 22.7 What each owner is actually chasing

`accept2` computes the sharp-quintile spectrum twice, over all tiles and over
clip-free tiles only, which separates the clamp from the veil:

| band | flower-bud, all sharp (154) | flower-bud, clip-free (151) | couch-fibers (217) |
| --- | ---: | ---: | ---: |
| low | 0.7889 | 0.9789 | 1.0361 |
| **mid** | 0.5155 | **0.6719** | **1.1081** |
| high | 0.5699 | 0.6335 | 0.9571 |

Excluding **three tiles out of 154** moves the low band from 0.7889 to 0.9789. The
clamp is essentially the entire low-band deficit of the sharpest fifth of the
frame, concentrated at the subject outline, and it repays itself when fixed. Only
a third of the mid-band deficit goes with it. What remains — 0.6719 against the
control's 1.1081, a 44-point swing between two subjects from one binary at one pin
— sits in 151 tiles with no clipped pixel in them, and the discriminator between
the two subjects is whether there is an occluding outline against a defocused
background. That is BUILD-HALO's veil, now carrying a number.

Targets issued: clamp, all four clip cells to a rise ≤0.02%; veil, flower-bud's
clip-free mid-band 0.6719 → ≥0.98 with couch-fibers' 1.1081 undisturbed, that
subject being the placebo precisely because it has no silhouette for a veil fix to
act on.

One caution against the finding's own grain, since it is n=2: the silhouette
discriminator is ARGUED, not established, and this corpus has been burned by
two-subject conclusions before. BUILD-HALO's fix is the falsification. If both
subjects move, or neither does, the mechanism is not what either of us believes,
and that is worth more than a passing gate.

## 22.8 The standing correction

The merge that has been called a 10% regression all night is, measured with an
instrument that can see the band the lens actually delivers, **+11% through the
mid-band and up to +34% at its peak**, on the subject that has nothing wrong with
it. Its two real defects are localised, separately owned, separately measured, and
one of them repays 0.79 → 0.98 on three tiles.

Nothing about the ship decision changes: the merge is still unreachable from
`strehl stack`, which is still the only thing standing between this project and a
photograph. But the case for wiring it was stronger than the record said, and the
record said otherwise because of a metric this document is responsible for.

## 23 The silhouette discriminator, pre-registered and tested at n=6

§22.7 closed by naming its own weakness: one subject per arm, with the
classification assigned by judgement, on a corpus that has been burned by
two-subject conclusions before. `PREREG-silhouette.md` fixed the classification,
the thresholds and the refutation conditions in writing, and was committed before
any of the four new subjects was rendered.

## 23.1 The result

Clip-free sharp-quintile mid-band amplitude ratio, pyramid over legacy, all six
subjects under one commissioning pass that returned `0.00e+00` on every arm:

| subject | class, fixed in advance | clip-free MID | predicted | held? |
| --- | --- | ---: | --- | --- |
| flower-bud-alone-cpl | SILHOUETTE | 0.6719 | — | generating pair |
| couch-fibers-cpl | NO SILHOUETTE | 1.1081 | — | generating pair |
| dry-erase-marker-head-cpl | SILHOUETTE | **0.6850** | < 0.90 | yes |
| tweezers-cpl | SILHOUETTE | **0.9041** | < 0.90 | no, by 0.004 |
| wrapped-text-1 | NO SILHOUETTE | **0.9996** | ≥ 0.95 | yes |
| flat-on-ruler-cpl | NO SILHOUETTE | **1.0345** | ≥ 0.95 | yes |

Prediction 1 held on three of four. `tweezers-cpl` sits 0.004 above a threshold
picked by eye, which is a threshold failure and is recorded as one.

Prediction 2 — the strong one, separation with no overlap — held on all six.
Silhouette {0.6719, 0.6850, 0.9041}; no silhouette {0.9996, 1.0345, 1.1081}. The
worst non-silhouette subject sits above the best silhouette subject with a clear
gap. Nothing crosses.

Prediction 3, the secondary one, held directionally and no further: black-rail
clipping appears only in silhouette subjects, and in two of the three. Silhouette
looks necessary and is plainly not sufficient, which is the same shape as §19's
finding that drift alone does not predict clipping.

## 23.2 The isolate that separates the two defects

`tweezers-cpl` is the subject this test needed and did not know it was asking
for. It has a silhouette, it clips **0.0000%** on the black rail, and it is
deficient anyway — mid-band 0.9041, and its second quintile at **0.7094**.

Until now the veil and the clamp had only ever been observed on subjects where
both were present, and §22.7 separated them by excluding three tiles from one
spectrum. `tweezers` separates them by construction: a mid-band deficit of the
predicted kind with no clipped pixel anywhere to explain it. The veil is real and
it is not a side effect of the clamp.

## 23.3 Two subjects pass outright, and both are unseen

`flat-on-ruler-cpl` — all five quintiles 1.0313–1.0363, mid-band 1.0345, zero in
all four clip cells. `couch-fibers-cpl` — quintiles 1.0780–1.1104, mid-band
1.1081, zero clipping. On subjects with no occluding outline the pyramid merge is
uniformly better than the shipped one, and one of those two subjects had never
been looked at when the claim was made.

`wrapped-text-1` fails on one number, its flattest quintile at 0.9677, with a
mid-band of 0.9996. `dry-erase-marker-head-cpl` fails on everything, and its
reference arm is already **7.88% white-clipped** before the pyramid merge touches
it — a blown-highlight capture where the legacy render is itself damaged, and not
a clean test of anything. Its `p1` falls 892 → 0.

## 23.4 The gate contained the defect it was built to remove

The first run of `accept2` failed `wrapped-text-1` on its flattest quintile at
0.9309 while the same file measured 0.9996 in the mid-band. Those two numbers
cannot both be describing the picture, and the reason is that the per-quintile
statistic was still `lap_rms` — the top-octave-weighted operator §22.3 had just
finished condemning in `accept.py`. The gate reproduced, at tile scale, exactly
the defect it existed to correct.

Replaced with a difference-of-Gaussians matched to the same 0.2–0.7 f/Nyq band
the gate binds on (`σ = 0.1874/f` at the half-power point gives 0.535 and 1.874).
What makes the change trustworthy is that it did not simply raise everything:

| | lap_rms | band-pass | reading |
| --- | ---: | ---: | --- |
| wrapped-text-1 q0 | 0.9309 | **0.9677** | part of that deficit was noise |
| tweezers q2 | 0.7761 | **0.7094** | that deficit is real and mid-band |
| couch-fibers q0 | 1.0268 | **1.1104** | now agrees with its own mid-band |

A statistic that moved everything one way would be a rescale. This moved the
noise-dominated tile up, the signal-dominated tile down, and brought the quintile
column into agreement with the band column it had been contradicting.

> A gate must not be built out of the instrument it replaces.

## 23.5 What is now established, and what is still argued

MEASURED: the pyramid merge beats the shipped merge on every subject without an
occluding outline, and is deficient on every subject with one; the deficiency
survives the complete absence of clipping; the two failure modes are separable
and separately owned.

ARGUED still: that the mechanism is the veil. The classification is a judgement
about what each subject *is*, not a measurement, and §22's own note stands — the
honest version of this test derives the class from depth-map bimodality rather
than from a person looking at a photograph. Six subjects with a clean gap is
evidence; it is not the mechanism. BUILD-HALO's fix remains the falsification.



# 24 The clamp is blue, and my account of its shape was wrong

## 24.1 Two instruments disagreed, and neither was reading the same thing

Three numbers were in circulation for one defect on one subject:

| source | flower-bud clip | predicate | render |
|---|---:|---|---|
| `accept.py` (BUILD-WIRE) | 2.9920% | any channel `== 0` | 2x2 binned |
| `accept2.py` (this gate) | 1.4014% rise | any channel `== 0` | full res, demosaiced |
| `ORCH-gallery2` C4 | 2.192% | blue `== 0` | example binary |

The first disagreement is not a disagreement at all. `accept.py`'s `clip%` is
`np.any(im == 0, axis=2)` and it has **no white-rail term whatsoever**. It cannot
see a blown highlight. That is why it scores `dry-erase`'s reference arm at
0.0009% while this gate measures the same file as 7.8774% white-clipped: the two
instruments are counting different rails, and one of them only counts one.

The second gap is resolution. Binned 2.9920% against demosaiced 1.4014% on the
same defect.

## 24.2 A claim I made from a ratio instead of a measurement

From that 2.99 -> 1.40 fall I concluded the crushed population must be a thin rim
at the silhouette: interpolation eats a rim's boundary but leaves a blob's
interior, so a halving implies thinness. I wrote that into 22.4, and I sent it to
BUILD-BLEND as the target description.

It is an inference from a coincidence between two different renders. I never
measured the shape. `shape.py` measures it, on the files this gate actually
scores.

## 24.3 What it is

Per-channel exact-zero rise, flower-bud, full resolution:

| channel | rise |
|---|---:|
| R | +0.3728% |
| G | +0.5349% |
| **B** | **+1.3964%** |

against a reference that is 0.0000% in all three. The joint pattern is a true
partition of the zero set:

| channels dead together | % of frame |
|---|---:|
| **B alone** | **0.8651** |
| RGB | 0.3709 |
| GB | 0.1590 |
| RB | 0.0015 |
| G | 0.0045 |
| RG | 0.0004 |
| R | 0.0000 |

**62% of the zero set is blue with red and green intact.** The 1.3964% blue rise
is essentially the entire 1.4014% any-channel figure.

Morphology, 6738 connected components: the largest is 268,720 px = **58.1%** of
the zero set, the top ten are 88.1% — but the median component is 1.0 px and
there are 4504 singletons. And the giant component is thin: a single 3x3 erosion
leaves **32.9%** standing, 5x5 leaves 25.6%. A compact blob of 268,720 px loses
under 1% to one erosion. So it is one large connected *ramified* network — a web,
not a disc — plus thousands of isolated pixels.

Location: a zero pixel sits p50 **110 px** from the nearest top-1% luminance edge
in the reference, against a frame-wide p50 of **693 px**. Edge-associated by 6.3x,
and nowhere near a boundary rim.

## 24.4 Both accounts were wrong, in opposite directions

Mine said thin rim at the silhouette. `ORCH-gallery2` C4 said "the brightest
neighbour of a zero pixel has a median of 0.0 DN, so these are large contiguous
regions, not rims." On the full-resolution demosaiced files, the brightest
8-neighbour of a zero pixel is p50 **422 DN**, p75 752, p90 1032. Those pixels are
adjacent to real signal.

The gallery's *location* finding reproduces — shadowed crevices in the subject's
interior structure. Its *shape* finding does not. Correct statement, now measured:
**a blue-led crush forming a thin ramified network through the shadowed interior
of the subject.** Retracted: "at the silhouette boundary" (22.4, and two messages
to BUILD-BLEND).

## 24.5 The gate could not have seen any of this

`clip_cells` used `(a == 0).any(axis=2)`. It reports *that* a pixel is clipped and
never *which channel*, so a blue-only crush and an achromatic crush of the same
pixel count produce an identical number and need different fixes. That is the
fourth defect found in this gate since it was written to replace a defective one.

Fixed: rail x channel marginals now bind alongside the rail x population cells,
and the joint pattern is printed as a true partition. The marginals are labelled
as overlapping and are not claimed to sum. Recommissioned: `0.00e+00` on both
subjects.

> A predicate that answers *whether* cannot be asked *which*.

## 24.6 The hypothesis that decides the fix

Blue may not be special. Blue has the smallest pedestal in camera-linear space on
this subject, so an **achromatic** undershoot of a fixed number of DN reaches zero
in blue first while red and green survive it. If that is the mechanism, this is
not a chroma bug and a per-channel clamp would be treating a symptom — and
clamping each channel independently at zero is exactly what converts an
achromatic undershoot into an irreversible yellow-green cast in the shadows,
which is the reason the gallery called it print-blocking.

The test is cheap and pre-registered: read the reference arm's per-channel DN at
the zero locations. Achromatic undershoot predicts the reference is already
B < G < R there by about the undershoot magnitude, and that the R/G/B ordering of
the zero counts follows the ordering of the reference pedestals. It does order
correctly (R 0.3728 < G 0.5349 < B 1.3964), which is consistent — but ordering
alone is weak evidence and the DN test is the one that decides. Assigned to
BUILD-BLEND, who owns `pyramid.rs`.

## 24.7 Two smaller corrections

`dry-erase`'s white rail rises +0.5284% at threshold 0 and **falls** to +0.4578%
at threshold 256. A rise that shrinks as the window widens is pile-up *on* the
rail, not a broadened distribution: the merge is pushing near-white pixels onto
65535. Both rails are genuine rail states — flower-bud's black rise is 1.4014% at
t=0 and only 1.6206% at t<=8, so those pixels are *at* zero, not near it. The
exact-zero predicate is sound; it was only blind to colour.

And `tweezers` is not clean in all four cells as 23.2 recorded — it carries
`white_lit` 0.0029% in *both* arms, rising to 0.0033%. Below every threshold and
immaterial to its role as the veil isolate, but the record said zero and zero was
wrong. `shape.py` also reported "no clipped pixels" for it while only ever
examining the black rail — the same partial-coverage error, in a probe written in
the same hour as the fix for it.

## 25 — The notch: half the finest band never selects at all

The clamp is 1.4% of pixels. This is the defect that makes the stacks look the
way they look, and it was sitting in a diagnostic the merge has been printing all
along.

### 25.1 What the curve shows

`ampcurve.py` bins tiles by the *reference's* band-pass amplitude and reports the
pyramid's amplitude as a fraction of it. Null control — reference against itself —
is exactly `1.0000` in every bin on every subject, so the binning is not lying.

Four subjects, all with a minimum in the same place:

| subject | minimum | at refAmp | recovers to |
|---|---:|---|---|
| `tweezers-cpl` | 0.3111 | 31–53 DN | 0.98 by 272 |
| `flower-bud` | 0.4562 | 42–55 DN | 0.91 by 209 |
| `wrapped-text-1` | 0.6377 | <41 DN | 1.01 by 98 |
| `couch-fibers` | 0.7592 | <52 DN | 1.06 by 134 |

Up to **69% of mid-band amplitude gone**. The minimum lands at the same *absolute*
DN on subjects whose amplitude ranges differ fourfold. That last property is the
whole clue, and it took two refuted predictions to read it.

### 25.2 Two predictions of mine, both refuted

**First: the noise gate.** It is the only threshold on that axis, so I swept it
1 / 4 / 16, three distinct hashes. The minimum stayed in the same 31–53 bin
(1.4887 / 0.3111 / 0.2872). I recorded "not the gate" and moved on. That reading
was half right and I state the half I got wrong in 25.4.

**Second: over-selection.** The weight is `(excess/floor/SNR_REF)^p` with `p`
capped at 8 in the fine bands, so I predicted a frame clearing the floor by a hair
takes the whole coefficient, and that *lowering* the exponent would fill the
notch. The sweep says the opposite, monotonically, and hard-max — pure argmax,
no blending anywhere — is the best arm in **every single bin**:

| arm | 10–18 | 18–31 | **31–53** | 53–92 | 470–810 |
|---|---:|---:|---:|---:|---:|
| `--exponent 1.0 --sharpen 1.0` | 0.6309 | 0.3605 | **0.2356** | 0.5419 | 0.7109 |
| `--exponent 2.0 --sharpen 1.0` | 0.6386 | 0.3756 | **0.2645** | 0.6391 | 0.8500 |
| shipped default (ramp 2,3,4,5,8,8,8) | 0.6524 | 0.4055 | **0.3111** | 0.7585 | 0.9835 |
| `--hard-max` | 0.6643 | 0.4379 | **0.3432** | 0.8154 | 1.0221 |

Two things fall out of that table. At `p = 1` even the strongest edges in the
frame lose 29% — plain averaging dilution across frames that all clear, a second
and separate defect. And **the notch survives pure argmax**, where every output
coefficient is copied verbatim from one frame and dilution is impossible. So it
is not a weighting defect at all.

### 25.3 The mechanism, in a line the merge has been printing all night

`pyramid.rs:1048-1058`:

```rust
out[j] = if den[j] > 0.0 { num[j] / den[j] } else { usum[j] * inv_n };
```

`den[j] <= 0.0` means no frame's smoothed band energy cleared `gate * beta * var`.
The coefficient then becomes `usum[j] / frames` — the unweighted **mean of that
Laplacian coefficient over all N frames**.

`averaged_fraction()`, which `blend-render` prints on every run:

```
averaged : 47.9% 36.8% 9.9% 0.3% 0.0% 0.0% 0.0% 100.0%
```

**47.9% of the finest band and 36.8% of the next take that fallback.** Level 7 at
100% is the base band under `BaseBand::Mean`, correct by design and not the
issue: DC is present in every frame, so its mean is its right estimator.

For a *band-pass* coefficient in a focus stack it is not. The detail lives in
only the handful of frames where that pixel is in focus, so a mean over 100
frames returns roughly `n_focus / N` of it — an attenuation that gets **worse the
deeper the stack**, applied to nearly half of every fine detail in the image.

And it explains the signature nothing else explains. The threshold
`gate * beta * var` is an absolute noise-floor quantity in DN², identical across
subjects shot on one sensor at one ISO. **A defect pinned to the noise floor is
pinned to an absolute DN**, which is exactly why four subjects with fourfold
different amplitude ranges notch in the same place.

The shipped diagnostic warns only about the opposite failure — "near 0% would
mean the gate is not gating and this is a naive pyramid stacker". Nothing in it
says what half the finest band being averaged would mean, so nobody read 47.9%
as a number that needed reading.

### 25.4 What I got wrong about the gate, stated plainly

25.2 records "the gate sweep refutes the gate". The *position* argument holds —
a 16x change in the threshold does not move the minimum, because the threshold
lives in per-coefficient noise-floor units while the x-axis is tile-pooled
reference amplitude, and the two do not map onto each other. But I also read the
*depths* as flat and they are not: 1.4887 / 0.3111 / 0.2872 for gate 1 / 4 / 16 is
monotone, and monotone in the direction the fallback predicts — a higher gate
sends more coefficients into the mean and deepens the notch. The gate is not the
cause, but it is the control that decides how much of the image the cause gets to
touch, and I called it irrelevant when the same table already showed it was not.

### 25.5 A ratio below 1.0 has two readings, and I nearly acted on the wrong one

A band-pass amplitude below the reference's means either **(A)** the pyramid is
destroying real detail, or **(B)** the pyramid is correctly suppressing noise the
reference wrongly keeps. (B) is the design's own argument — below the gate no
frame has information, so averaging is the right estimator and the only operation
that gets below single-frame noise. The amplitude ratio cannot separate them.

`structure.py` was built to separate them by correlation, which is
amplitude-invariant: under (A) the pyramid should be `alpha * reference`, same
structure, so Pearson r stays near the strong-edge pole. It does not. Commissioned
at r = 1.0000 exactly in 12/12 null bins, against a shift placebo (pyramid
displaced 64 px, identical tile population):

| refAmp bin | n | ampRatio | r(aligned) | r(shifted) |
|---|---:|---:|---:|---:|
| 10–18 | 169 | 0.6632 | 0.4313 | 0.1151 |
| 18–31 | 21 | 0.4379 | 0.1951 | 0.0414 |
| **31–53** | 17 | **0.3292** | **0.1156** | −0.0258 |
| 273–470 | 396 | 1.0268 | 0.9666 | −0.0049 |
| 470–811 | 425 | 1.0221 | 0.9713 | 0.0014 |

By its pre-registered rule that reads as (B): the notch sits 0.1414 from the
placebo and 0.85 from the strong-edge pole.

**That rule was wrong, and I caught it before acting on it.** Low correlation is
produced by (B) *and* by a third case the rule did not name: the fallback crushes
the coefficient to a few percent and what survives is averaging residue rather
than attenuated signal. Both give low r. A two-arm correlation cannot tell them
apart, because both predict the same number.

### 25.6 The pole that settles it is computed, not borrowed

The two cases disagree about a **single-image** property of the reference — is its
content there structure or noise? — and that needs no second arm. Band-passing an
i.i.d. field imposes an autocorrelation set entirely by the DoG kernel, so the
noise pole is derivable rather than sampled from some region assumed featureless.

`whitetest.py`, 24 synthetic draws, tiles cropped from a larger field so no filter
edge artefact inflates the result: **pure noise reads lag-1 = +0.2107**. The
strong-edge pole is +0.8269.

| refAmp bin | ctrl lag1 | pyramid lag1 |
|---|---:|---:|
| 0–3 | 0.3617 | 0.4089 |
| 6–10 | 0.4437 | 0.4641 |
| 18–31 | 0.6039 | 0.4128 |
| **31–53** | **0.7140** | **0.5708** |
| 273–470 | 0.8264 | 0.8261 |
| 470–810 | 0.8276 | 0.8272 |

The reference's content in the notch is **structure** — 0.11 from the edge pole,
0.50 from the noise pole. (B) is dead: "averaging is correct because there is no
information there" is false at that amplitude.

Autocorrelation rises with SNR across bins, plainly, so the across-bin reading
carries a confound. The **paired** reading does not: on the *same tiles*, the
reference is 0.7140 and the pyramid 0.5708. The pyramid's own content is
measurably less structured than the reference's, pulled toward the noise pole. It
did not attenuate the detail; it replaced it with something flatter and
uncorrelated, which is worse than the 0.33x ratio suggested on its own.

The flat bins are the guard rail and they say the fallback is right where it
should be right: at 0–10 DN the pyramid is slightly *smoother* than the reference
(0.4641 vs 0.4437, 0.4089 vs 0.3617), which is what averaging noise correctly
looks like. Any fix must fill the notch without pushing those toward +0.2107.

### 25.7 What this costs, and what it changes

Three refuted predictions in one section — the gate, the exponent, and my own
correlation rule — and the defect was legible in a printed diagnostic from the
first render. The lesson is not that the instruments failed. Each one worked and
each one killed a hypothesis, which is what they are for. It is that
**`averaged: 47.9%` was on screen for every render all night and nobody had
written down what a bad value would be.** A diagnostic with no stated failure
threshold is decoration; it gets read as ordinary precisely because there is
nothing to read it against.

> **A diagnostic that names only one of its two failure directions will be read as
> normal in the other.**

> **Low correlation does not mean "different content". It means "not the same
> content", and annihilation satisfies that as easily as substitution.**

The fix is `pyramid.rs`'s and belongs to its owner: a selectable sub-gate
fallback (`mean` as the control, `best`, `topk` with k=3) scored on all four
instruments as a conjunction — amplitude *and* correlation *and* structure *and*
the flat-tile noise cells. Recovering amplitude without recovering correlation
would mean putting back energy that is not the scene's, and would fail.

The pyramid default stays where it is until that lands. Flipping today would ship
the clamp and this together.

## 26 — Three corrections to 25, and what the pictures actually show

Section 25 was written from summary tables. Then I looked at the tiles, and at
the images, and three of its claims need narrowing. None of them changes the
mechanism; all of them change how much of the frame it is entitled to explain.

### 26.1 The notch minimum is a corner of one frame, not a property of the scene

`notchtiles.py` prints the tiles themselves. Of the 18 tweezers tiles in the
31–53 DN bin, **16 sit at y ∈ {4224, 4352, 4480}** — three adjacent tile rows at
the bottom of a 4688-px frame, in contiguous horizontal runs, nine consecutive at
y = 4480. Median distance to a strong edge is 97.2 px against 64.9 px frame-wide,
so they are not at the silhouette either; the occlusion-halo reading is refuted
for them as well.

A bin holding 1% of tiles, clustered in three scan-line bands, cannot carry the
claim "up to 69% of mid-band amplitude lost" that 25.1 hung on it. tweezers'
tile-amplitude distribution is bimodal — 725 tiles at 3–18 DN, 838 at 272–810,
79 in the whole valley between — and 25 put its headline number in the sparsest
part of that valley.

**The finding that survives is the neighbouring band**, and it is much better
evidenced:

| band | n | mean ratio | mean r | tile rows | tile cols | p50 dist-to-edge |
|---|---:|---:|---:|---:|---:|---:|
| 6–10 DN | 393 | 0.9615 | 0.5762 | 19 of 36 | 55 of 55 | 1227.6 px |
| **10–31 DN** | **188** | **0.6414** | **0.4262** | **17 of 36** | **53 of 55** | **893.7 px** |

188 tiles spread over 17 rows and 53 columns of a 36 × 55 grid is the whole
frame, not a corner. **A scene-wide 36% amplitude loss in low-detail regions,
with correlation of only 0.43, is the real defect.** It is smaller than the
number 25 led with and it is a great deal more real.

### 26.2 Gate 2 does not fill the notch. It fills it with noise

25 recorded that gate 2 restores the notch bin to 0.9846 and called the detail
"essentially intact". The correlation column says otherwise: at gate 2 the notch
bin's amplitude ratio is 0.9918 and its **r is 0.0946** — amplitude restored,
correlation not restored. That is precisely the failure I had already
pre-registered as disqualifying, and I applied it to a hypothetical fix while
missing that the gate arm in front of me already failed it.

The flat bins settle it. Lag-1 autocorrelation is inflated for everything,
because the band-pass filter correlates adjacent samples by construction; at lag
2 and 4 that imposed correlation has decayed and the populations separate:

| band | ctrl L2 | pyramid L2 (gate 2) | synthetic noise L2 |
|---|---:|---:|---:|
| 6–10 | +0.1782 | **−0.0617** | −0.0810 |
| 10–18 | +0.2796 | **−0.0597** | −0.0810 |
| 18–31 | +0.3002 | **−0.0415** | −0.0810 |

Gate 2's flat-region content sits **on the synthetic noise pole**, negative at
lag 2 where real structure is strongly positive. Its 6.9x amplitude in flat
regions is manufactured noise across 45% of the lit frame.

> **Lag-1 cannot separate structure from noise through a band-pass filter,
> because the filter puts the lag-1 correlation there itself. The first lag that
> discriminates is the first one past the kernel's own support.**

### 26.3 The wired pyramid path is the gate-2 build

`main.rs:763` constructs `MergeConfig::default()`, whose `gate` is `2.0`, and
only overrides it if `--pyramid-gate` is passed. Every measurement in 25 was
taken at `--gate 4`, which is the `blend-render` protocol, not the shipped
default. So `strehl stack --merge pyramid` today is the arm with the noisy flats
— a different product from the one the corpus has been characterising.

This is not an argument for changing the default to 4. Gate 4 has the detail
loss and gate 2 has the noise; 25.3's conclusion stands that no gate value is
correct and the sub-gate estimator is what has to change. It is an argument that
**the number a measurement was taken at must be checked against the number the
product ships**, which nobody had done for this knob.

### 26.4 What the renders actually look like

A 26-subject gallery exists at `C:\dev\strehl-out\gallery`, rendered from the
shipped estimator path (`strehl stack --srgb --demosaic`, 2400 px long edge).
Two subjects, and they disagree completely:

- **`tweezers-cpl` is good.** Sharp, well-resolved ground-metal texture, clean
  tonality, no visible rim. Dark background.
- **`flower-bud-with-background-fern-cpl` is not.** A hard bright rim traces
  every silhouette of the bud and the fern, with a grey aura outside it. Bright
  background, dark subject, fine structure.

That polarity split is itself information, and it is consistent with a veil:
a defocused bright background veils a dark subject's surround, and the reverse
does not happen. It also means single-subject verdicts on halo severity are
worthless — tweezers, the subject most of this corpus's veil work used as its
isolate, is the easy case.

### 26.5 The aura is a veil, and its shape says so without a second arm

Every comparison in sections 22–25 was two-armed and therefore vulnerable to the
reference being the defective one. This one is not. A veil and ringing make
opposite predictions about the *shape* of the profile, so one image decides it:
a veil is largest against the edge and decays monotonically; ringing departs,
reaches an extremum a few pixels out, and returns.

`edgeprofile.py` on `flower-bud-alone-cpl--ctrl.tiff`, full resolution, shipped
estimator path, far-field level 19366.9 DN from 16.0 M pixels beyond 300 px:

| signed distance | n | median DN | vs far-field |
|---|---:|---:|---:|
| +0..+2 | 64772 | 17097.8 | **−2269.0** |
| +4..+8 | 171035 | 17548.2 | −1818.6 |
| +16..+32 | 337313 | 17501.4 | −1865.4 |
| +64..+128 | 1204276 | 17825.5 | −1541.3 |
| +200..+300 | 1584984 | 18510.8 | −856.0 |
| +300..+400 | 1480392 | 18807.8 | −559.0 |

Monotone from the edge outward, largest departure at d = 0. **Veil, not
ringing** — and −2269 DN is −11.7% of the far-field level, which is why it reads
as a grey aura rather than a subtle gradient. It is still −559 DN at 400 px.

That the shape is optical does not make the magnitude optical. BUILD-HALO's
paired measurement puts the merge at −4549 DN against a best single frame of
−474 and an upper envelope of −379. **The merge is roughly an order of magnitude
worse than the best frame it was given**, so most of what is on screen is not
inherited from the optics but manufactured by the selection, and the project's
own "never worse than a single frame" invariant is being violated by 10x in the
region the eye goes to first.

### 26.6 Where this leaves the ship decision

The pyramid default stays put; 25.3's blocker is unchanged and 26.2 adds a
second one. But the more useful conclusion is that **the pyramid was not the
thing to fix first.** The notch is a defect in an experimental backend. The veil
is a defect in the shipped one, it is 10x a single frame, and it is the thing
that makes a picture look wrong to a person rather than to a metric.

> **A defect measured on the arm you are developing is not automatically the
> defect the product has. Check which arm ships before deciding what is
> urgent.**

## 27 — The halo is a backend defect, and the other backend already in the tree removes it

Section 26 established that the shipped estimator carries a veil and that the
owner's complaint is real. This section is the part that matters: the fix is not
research, it is a constant.

### 27.1 A paired probe that cannot be a mask difference

Every veil measurement before this segmented each arm independently, which
leaves an obvious hole — two arms with slightly different tonality segment
slightly different silhouettes, and the "difference" is then partly the masks.
`veilpair.py` closes it by computing the subject mask and the distance transform
**once, from a named reference arm, and applying both unchanged to every arm**.
An identical pixel population is scored in every column.

Commissioned twice before use, because a probe nobody has tried to break is a
probe nobody knows the sensitivity of:

- **Null:** reference against itself is exactly 0.0 in all ten bins.
- **Placebo:** the same mask translated 640 px off the silhouette collapses the
  d = 0 signal from −2269.6 DN to −458.1 DN. The profile really is keyed to the
  silhouette and is not an artifact of sorting pixels by brightness.

### 27.2 The measurement

`flower-bud-alone-cpl`, background luminance deficit against far-field, ctrl =
shipped estimator, blend = pyramid at `--gate 4 --base-mean --camera-linear`:

| dist (px) | n | estimator | pyramid | ratio |
|---|---:|---:|---:|---:|
| 0..2 | 64,597 | −2269.6 | −2000.8 | 0.88 |
| 4..8 | 169,532 | −1801.8 | −1288.6 | 0.72 |
| 8..16 | 252,212 | −1846.8 | −1151.0 | 0.62 |
| **16..32** | 337,579 | **−1866.1** | **−981.3** | **0.53** |
| 32..64 | 617,014 | −1679.6 | −1069.1 | 0.64 |
| 64..128 | 1,202,256 | −1533.8 | −1199.4 | 0.78 |

`dry-erase-marker-head-cpl` is larger: 32..64 goes −6966.5 → −2198.1 (0.32),
64..128 −3520.2 → −999.0 (0.28), 128..200 −2248.4 → −365.8 (0.16).

**The limitation that bounds the claim.** The mask is a luminance split at
q = 0.35, so it finds a real figure/ground silhouette only where the subject is
*darker* than its background. True for `flower-bud` and `dry-erase`; false for
`tweezers`, where the split inverts and the profile is not measuring a veil at
all. The strong result rests on two subjects. On the other four the arms agree
within 1–2%, which is a no-regression result and not a veil result. Reporting
the second as if it were the first is how a 2-subject finding becomes a 6-
subject claim.

### 27.3 Then I looked at it

Numbers of this kind have been wrong in this corpus before, so the two arms were
cropped at 100% on the busiest silhouettes and tone-mapped through **one window
computed from the reference arm only** — an A/B where each side gets its own
auto-levels can manufacture or hide any difference you please.

The estimator crops show a **hard white band tracing every contour of the bud**,
roughly 20–40 px wide, following the silhouette all the way round including into
the concavities between hairs. It reads exactly like a cut-out sticker outline.
On the same crop the pyramid shows **none of it** — clean silhouette, smooth
background, individual hairs separated against the white.

Two independent crops, 2700 px apart in the frame, agree completely.

This is the artifact the owner called horrendous, and it is absent from a
backend that has been compiled into the tree the whole time.

### 27.4 What this reorganises

Sections 22–26 spent their effort on the pyramid's *own* defect — the sub-gate
fallback mean, the notch, the gate that cannot adjudicate it. All of that is
real and none of it is retracted. But it was work on the arm that does not ship,
measured against a baseline that has a far worse defect, and no one had put the
two arms side by side on the failing subject.

> **When two implementations of the same stage both exist and both run, compare
> them on the failing case before deciding which one's defects to study. The
> cheapest experiment in the tree was the one nobody had run.**

The notch costs mid-band amplitude in low-contrast regions — a defect you find
with an instrument. The veil puts a white outline around the subject — a defect
you find by opening the file. **They are not the same size, and they were being
prioritised as if the measurable one were the larger.**

### 27.5 The flip, and what still blocks it

`merge_cmd.rs:275` is `DEFAULT_MERGE_BACKEND = MergeBackend::Estimator`, and
`c42cd75` deliberately reduced the change to that one line. `base:
BaseBand::Mean` is already the pyramid default. So the distance between the
product the owner has seen and the product measured here is:

1. `merge_cmd.rs:275` — Estimator → Pyramid
2. `pyramid.rs:731` — `gate: 2.0` → the value the veil win was measured at, 4.0

Two lines, two owners. The second is the open question: every veil number in
27.2 was taken at gate 4, and the wired default is gate 2, whose sub-31 DN bins
sit *above* 1.0 with lag-2 autocorrelation on the synthetic-noise pole. Flipping
only the backend would ship the arm this corpus has never characterised.

Held pending a measurement of the veil at gate 2. If the win is gate-independent
the gate can be argued on detail and noise alone; if it is not, the gate value
is part of the fix and must move with it.

## 28 — I generalised from two crops, and the crops were chosen by edge density

Section 27 concluded that the pyramid removes the halo and that two lines stood
between the shipped product and a better one. The first half survives. The
conclusion does not, and the way it failed is worth more than the finding was.

### 28.1 The sampling rule was blind to the thing that mattered

`crops.py` picks its crops by silhouette density — it ranks a coarse grid by how
many edge pixels each cell contains and takes the busiest. That is a sensible
rule for looking at a halo, and it is exactly why it could not see this.

**A sampling rule that selects for one feature is blind to everything that is
not that feature.** Both crops landed on clean silhouettes 2700 px apart, both
showed the halo gone, and I read two agreeing samples as a survey. They agreed
because they were drawn from the same stratum, and the stratum was chosen by me.

Then I rendered the full frame and looked at it. A large region of the subject
that is ordinary mid-tone green in the estimator arm is **nearly solid black in
the pyramid arm**.

### 28.2 The pyramid clips mid-tones to exact zero

`flower-bud-alone-cpl`, both arms, full resolution, camera-linear:

| | exact-zero RGB px | luma < 500 DN | darker than ctrl by >2000 DN |
|---|---:|---:|---:|
| estimator | **0** (0.000%) | 686 (0.002%) | — |
| pyramid | **122,416** (0.371%) | 432,421 (1.310%) | 721,189 (2.19%) |

In the 721,189-pixel disagreement set the estimator median is 3920.7 DN and the
pyramid median is 878.0 DN. Mid-tones collapsed to the floor, in one contiguous
region — bbox y 744..4687, x 1668..5104, centroid y 3169 x 3678 — not speckle.

Across all six clean6 subjects, with the partition printed so a skipped subject
cannot read as a passing one (requested 6, scored 6, missing 0):

| subject | estimator exact-0 | pyramid exact-0 | pyramid % |
|---|---:|---:|---:|
| couch-fibers-cpl | 0 | 0 | 0.000% |
| **dry-erase-marker-head-cpl** | 0 | **345,849** | **1.048%** |
| flat-on-ruler-cpl | 0 | 0 | 0.000% |
| **flower-bud-alone-cpl** | 0 | **122,416** | **0.371%** |
| tweezers-cpl | 0 | 0 | 0.000% |
| wrapped-text-1 | 0 | 12 | 0.000% |

**The two subjects that clip are exactly the two that showed the large veil
win** — the two dark-subject-on-bright-ground stacks. Two effects appearing on
the same two subjects and nowhere else is either one mechanism or a coincidence
across a 6-subject sample, and the first is worth testing before the second is
assumed.

### 28.3 So I tested it, and my own hypothesis lost

The obvious single mechanism is **edge overshoot**: a Laplacian pyramid with
per-band sharpening pushes the bright side of an edge brighter and the dark side
darker. That would explain both — the bright lobe would masquerade as veil
removal, and the dark lobe would be what clips. If true, section 27's headline
result was not an improvement at all but the visible half of a new artifact.

Overshoot is antisymmetric about the edge, so it is falsifiable on one image.
`veilpair.py` could not see it, because it profiles only the background side,
where veil removal and overshoot predict the same thing. `twoside.py` extends
the distance transform to negative values inside the subject. Null control: the
reference against itself is +0.0 DN in all fourteen bins.

| signed distance | n | ctrl med | pyramid med | difference |
|---|---:|---:|---:|---:|
| −128..−64 | 2,098,896 | 13992.3 | 16853.7 | **+2861.4** |
| −32..−16 | 668,521 | 15652.5 | 17345.0 | +1692.5 |
| −8..−4 | 191,176 | 16256.0 | 17097.8 | +841.8 |
| −2..0 | 104,772 | 16881.5 | 17113.3 | +231.9 |
| 0..2 | 64,597 | 17095.2 | 17364.4 | +269.2 |
| 8..16 | 252,212 | 17518.0 | 18214.2 | +696.3 |
| 16..32 | 337,579 | 17498.7 | 18383.9 | +885.2 |
| 64..128 | 1,202,256 | 17831.0 | 18165.7 | +334.7 |

**Positive on both sides. Not antisymmetric. The overshoot hypothesis is dead.**

Two things follow that I would not have got from the ratio alone. First, the
far-field is unchanged between arms (+0.4 DN at 300–400 px), so the near-edge
lift is a *localised* correction and not a global tone shift — the veil result
in 27.2 survives this test rather than being explained away by it. Second, the
pyramid's median is **brighter** everywhere while a contiguous minority is
crushed to zero, so the clip is not the tail of a tone shift. It is a separate,
localised failure that the median cannot see.

> **A median that moves the right way is not evidence that nothing moved the
> wrong way. Report the rails and the tails beside it, or a catastrophic
> minority will hide under a healthy centre.**

### 28.4 The flip is off

- **Estimator**: white halo tracing every silhouette; zero clipped pixels.
- **Pyramid**: no halo; 0.37–1.05% of the frame clipped to exact zero on the two
  subjects where it most helps.

Neither ships. A clipped-to-zero pixel contains no recoverable information at
all, which is strictly worse than a halo that preserves what is underneath, so
the trade is not close and `DEFAULT_MERGE_BACKEND` stays on `Estimator` until
the clip is fixed. BUILD-WIRE has been told to hold and to enumerate what else
moves with the constant; BUILD-BLEND has the clip as its top priority, ahead of
both the gate question and the notch.

The discriminator sent with it needs no reference arm and cannot be argued with:
**for each output pixel, compare against the min and max across all input frames
at that pixel.** Anything claiming to be a weighted combination of N
observations that lands outside `[min_k, max_k]` is arithmetically impossible,
not merely poor, and the violating fraction per band localises the bug.

### 28.5 What this cost, stated plainly

Sections 22 through 26 characterised the pyramid's notch in detail. Section 27
found a defect in the shipped estimator that is far larger and was visible on
first opening a file. Section 28 found a defect in the pyramid that is larger
still and was visible on first viewing a *whole* file rather than a crop.

Three escalating findings, each cheaper than the last, each requiring only that
someone look at the output at a scale nobody had looked at yet. The instruments
were never wrong. They answered the questions they were asked, and for a long
time nobody asked the one that a person looking at the picture asks first.

## 29 — Per-band convexity does not imply reconstruction convexity

Section 28 left the clip as "a separate, localised failure". This section names
it, and the naming was done by construction rather than by reading the code, so
it does not depend on my reading being right.

### 29.1 Eliminating the suspects

`flower-bud-alone-cpl` rendered at `--gate 2` as well as `--gate 4`:

| arm | exact-zero px | luma<500 | median DN |
|---|---:|---:|---:|
| estimator | 0 (0.000%) | 0.002% | 18137.2 |
| pyramid gate 4 | 122,416 (0.371%) | 1.310% | 18550.5 |
| pyramid gate 2 | 121,297 (0.368%) | 1.318% | 18540.7 |

**Jaccard 0.9424; 96.59% of the gate-4 zeros are also zero at gate 2.** The same
pixels, at two gates whose fallback behaviour is wildly different — `averaged`
reads `49.1% 0.0% 0.0% ...` at gate 2 against `47.9% 36.8% 9.9% 0.3% ...` at
gate 4. **The gate and the sub-gate fallback are both eliminated**, and with
them the notch as an explanation for anything visible.

Two further signatures: blue leads by 3.7x (R 123,050, G 176,531, B 460,886),
and the estimator renders the same region at median 3117 DN. The data there is
dark and perfectly ordinary. The zeros are manufactured.

### 29.2 The module's safety argument, and the step that does not follow

From `pyramid.rs`'s own preflight log:

> `selection : SOFT -- weight = (band power above the noise floor)^exponent, a
> convex combination. Sign coherence is free: a convex combination cannot take
> adjacent coefficients from opposite-signed frames`

Per-band convexity is real and the sign-coherence claim is true *within a band*.
The inference that it protects the reconstruction is false, and structurally so.
**Each band computes its own weights.** Band 0 may be dominated by frame 12
while band 5 is dominated by frame 80. The reconstruction sums bands drawn from
different weight vectors, and a sum of convex combinations under *different*
weightings is not a convex combination of the original pixels.

### 29.3 Decided by construction, with a control that reads exactly zero

`hullproof.py` — 1-D Laplacian pyramid, 8 frames each sharp in a different
region, hull `[min_k, max_k]` per pixel:

| case | violating | worst excursion |
|---|---:|---:|
| **CONTROL: one weighting shared by every band** | **0 / 102,400** | **0.000** |
| MEASURED: independent per-band weights | 7 / 102,400 | 0.140 x span |
| CONTROL: single-frame passthrough | max abs err 2.22e-16 | — |

The shared-weight control is the load-bearing one. If per-band convexity did
protect the reconstruction, the measured row would be zero too. A harness whose
positive control cannot come out zero proves nothing; this one does, and the
measured row still does not.

**The rate is driven by the selection exponent, not the gate:**

| exponent | violating | rate | worst excursion |
|---|---:|---:|---:|
| 0 (uniform mean) | 0 | 0.00% | 0.000 |
| 1 | 0 | 0.00% | 0.000 |
| 2 | 1 | 0.00% | 0.336 |
| 4 | 2 | 0.00% | 0.054 |
| **8** | **72** | **0.09%** | **0.752** |
| 16 | 511 | 0.67% | 2.924 |

The shipped per-band ramp is `2 3 4 5 8 8 8`. **The three finest bands sit at
exactly the exponent where this turns severe**, and at 16 the reconstruction
lands nearly three times outside the range of any input frame.

This predicts every signature in 29.1 without further assumption: gate-
independent because the exponent drives it; worst in dark regions because the
hull sits near zero there and a downward excursion crosses it; blue-led because
blue carries the least signal so its hull is nearest zero; the same pixels at
both gates because the exponents are the same at both gates.

### 29.4 The fix, and why it cannot cost anything real

**Clamp the reconstruction to the per-pixel hull of the aligned inputs.**

The argument is not aesthetic. A merge that claims to combine N observations has
no basis for emitting a value none of them support. Anything outside
`[min_k, max_k]` is unsupported by the data *by definition*, so the clamp can
only remove excursions that were never justified. It degrades gracefully in both
directions: where frames agree the hull is tight and the clamp binds constantly
while changing nothing; where they disagree it is loose and never binds.

Not by lowering the exponent — 25.2 measured loss as monotone in selectivity
with hard-max best in every amplitude bin, so that trades a fixable artifact for
a diffuse one.

> **A safety property proved for one stage is not a safety property of the
> pipeline. Convexity per band was true, was stated in the log every run, and
> was load-bearing for a conclusion it does not support.**

### 29.5 The shape of all four findings

| section | defect | found by | visible at |
|---|---|---|---|
| 22–26 | the notch | band-ratio instruments | tile statistics |
| 27 | the estimator's halo | opening a file at 100% | one crop |
| 28 | the pyramid's clip | opening a *whole* file | full frame |
| 29 | why the clip happens | 40 lines of numpy | no image at all |

Each was cheaper than the last. The most expensive instrument in this corpus
found the least important defect, and the mechanism behind the most important
one fell out of a toy model that never touched the codebase.

## 30 — A metric with no spatial argument cannot tell an artifact edge from a subject edge

This one is not mine. V-TONE established it under adversarial instruction and
filed it as `docs/research/V-seam.md` (`07cc58f`); recorded here because the rule
generalises and because the decision it unblocks is a product decision.

### 30.1 The verdict that was blocking a free win

`--photometric` recovers +1415 DN and removes 35–47% of the aura — part of the
artifact the owner is objecting to. It was off by default, and not by oversight:
M122 ran a pre-registered 14-stack promotion test and returned **KEEP-OFF** on
K2, its no-harm criterion, finding that `--photometric` *"materially reduces
real fine structure on `flower-bud-alone-cpl`"*, Theil-Sen slope 0.9444
[0.9312, 0.9598].

K2 is a high-frequency energy ratio over the whole frame. **It has no spatial
argument.** So it cannot distinguish an artifact edge from a subject edge, and
the question nobody asked was *where* the lost structure was.

### 30.2 Partition the same statistic by location and the verdict inverts

Thresholds and reading rule pre-registered before the slopes were computed:

| partition | hf0 median | k | 95% CI |
|---|---:|---:|---:|
| SEAM, far background (d>200) | 106.6 DN | **0.6647** | [0.5431, 0.7899] |
| SEAM, near subject | 418.4 | 0.9395 | [0.9089, 0.9689] |
| SEAM, inside subject | 829.8 | 0.9941 | [0.9727, 1.0118] |
| **SUBJECT, no seam** | **280.8** | **0.9957** | **[0.9888, 1.0022]** |
| BACKGROUND, no seam | 382.6 | 1.0287 | [1.0021, 1.0622] |

The partition holding the real fine structure — and it is the *most* textured
partition in the frame, 280.8 DN against 127.3 at seams — **loses 0.4%, with a
confidence interval including 1.00.**

All the harm is in the content-free backdrop, where the election picks a
near-random frame per pixel (elected-index p5–p95 spans 3..195 of 0..204; 49.7%
of pixels have a ≥8-frame jump within a 3×3) out of frames whose levels span
23.5%. That writes level speckle. `--photometric` removes it. **85.7% of the
removed Laplacian energy is in the seam set**, and the removed-energy map forms
closed loops that are pixel-for-pixel the election-map patch boundaries.

**K2 was counting the artifact as signal, and the KEEP-OFF verdict rested on it.**

### 30.3 What the verifier did not claim

Two things it reported against its own interest, which is why the rest is
trustworthy:

- The rule-verbatim verdict is **MIXED, not CONFIRMED**. Its placebo partition —
  pixels matched to the seam set in count, local gradient and local level but
  with no index discontinuity — came in at k = 0.9886 against a registered bar
  of 0.99, **missing by 0.0014**. Recorded, not relaxed. One sensitivity cell is
  VOID by its own rule. Read as: ~1.1% residual sensitivity to gradient
  magnitude, against a 33% seam-partition drop.
- `k_background` = **1.0287** [1.0021, 1.0622], CI excluding 1.00 in 5 of 6
  cells — the correction *increases* HF energy away from both subject and seams.
  Unexplained, and explicitly not claimed. Nothing is to be built on that region
  until it is understood.

### 30.4 The root-level argument, which is stronger than the metric argument

M122's harm mechanism requires the fitted gain to be able to absorb scene
content — plausible, since a per-frame fitted gain over 205 frames is 205 free
parameters. Testing whether the ramp is instead predicted by physics:

- **The aligner's scale ladder is dead as a route.** Span 1.000233 against a
  gain span of 1.2350 would need exponent 904, and the ladder is not monotone
  (−0.513).
- **EXIF lands it with zero free parameters.** Shutter, ISO and f-number are
  constant across all 205 frames, but `SonyFNumber2` moves 13.50 → 12.60
  monotonically (corr −0.9940), predicting a span of 1.1480 = **65.4% of the
  fitted log-span**, residual 7.58% unattributed.
- **Independent cross-check:** EXIF magnification span 13.24% against a
  silhouette measurement of 12.60% — 0.64 pp apart by fully independent routes.

Two thirds of the "205 free parameters" are not free. They are a physically
predicted exposure ramp from effective aperture changing with magnification,
`N_eff = N(1 + m/p)` with exposure as `1/N_eff²`. That dissolves M122's harm
mechanism at the root, independently of how its metric is read.

Pupil magnification `p` is **not identifiable** from this data and no number is
reported: `N_eff/N` *is* `1 + m/p`, so the two are the same measurement. One
bracket with a ruler in frame would make it identifiable — a capture request,
not a result.

A consequence to route rather than act on: the `SonyFNumber2` ramp implies a
real per-frame magnification change that the aligner's ladder is **540× too
small to contain**. That is a defect in the alignment model.

### 30.5 The rule, and its third instance tonight

> **A metric with no spatial argument cannot tell an artifact edge from a
> subject edge. If a no-harm criterion is an energy statistic, it will score the
> removal of an artifact as damage.**

Three instances now, which is why this is a rule and not an anecdote:

| # | metric | counted as signal what was actually |
|---|---|---|
| 1 | M122's K2 | election-seam level speckle |
| 2 | my veiling estimator | its own +0.845σ upward bias |
| 3 | BUILD-SHARP's dead band | ~3/4 real signal |

And the older one from §26.2, the same failure in a different coat: a band
amplitude ratio that reads 0.9918 while correlation reads 0.0946 — the right
quantity restored, none of the right content.

## 31 — `--photometric` and the pyramid remove different parts of the same veil

Three arms, one shared silhouette mask and one shared distance transform computed
once from the `ctrl` arm and applied unchanged to all three (`veilpair.py`;
null 0.0 in 10/10 bins, 640-px translated-mask placebo collapses d=0 from −2269.6
to −458.1). Subject `flower-bud-alone-cpl`, 205 frames, camera-linear, gate 4,
lateral CA off in every arm. Far field agrees to 10 DN across the three
(19364.8 / 19365.2 / 19375.3), so the arms are level-matched and the numbers
below are not an exposure difference.

| d (px) | n | ctrl DN | pyramid | ratio | estimator+photo | ratio |
|---|---:|---:|---:|---:|---:|---:|
| 0..2 | 64,597 | −2269.6 | −2000.8 | 0.882 | −2205.1 | 0.972 |
| 2..4 | 109,702 | −2170.1 | −1665.0 | 0.767 | −1826.5 | **0.842** |
| 4..8 | 169,532 | −1801.8 | −1288.6 | 0.715 | −1473.7 | **0.818** |
| 8..16 | 252,212 | −1846.8 | −1151.0 | 0.623 | −1417.8 | **0.768** |
| 16..32 | 337,579 | −1866.1 | −981.3 | **0.526** | −1625.0 | 0.871 |
| 32..64 | 617,014 | −1679.6 | −1069.1 | 0.637 | −1599.6 | 0.952 |
| 64..128 | 1,202,256 | −1533.8 | −1199.4 | 0.782 | −1527.6 | 0.996 |
| 128..200 | 1,254,203 | −1216.7 | −1075.2 | 0.884 | −1216.4 | 1.000 |
| 200..300 | 1,580,427 | −844.9 | −752.7 | 0.891 | −835.4 | 0.989 |
| 300..400 | 1,475,465 | −548.0 | −500.7 | 0.914 | −538.9 | 0.983 |

### 31.1 The two levers do not overlap

`--photometric` does its work **close to the silhouette** — best ratio 0.768 at
8–16 px — and is a measured **no-op beyond 64 px**, where it runs 0.99–1.00.
The pyramid does its work in the **mid-field**, bottoming at 0.526 at 16–32 px,
and is still returning 0.78–0.91 out at 64–400 px where photometric has stopped.

Neither is a substitute for the other, and the failure direction matters for the
product: photometric leaves 87% of the veil standing in the band the eye reads
as the halo, so **turning it on does not fix the artefact the owner objected
to.** It is a real improvement and it is not the fix.

### 31.2 A product consequence, and it is not a small one

`--photometric` is **REFUSED under the pyramid backend** (`main.rs:730-746`),
so the two levers measured above cannot currently be used together. They act in
disjoint distance bands, which is exactly the condition under which they would
be expected to compose rather than compete. Nobody has measured the composition,
because the binary will not run it.

That refusal was the honest choice when the pyramid had no photometric path —
a flag that parses and does nothing is worse than one that errors. But the
refusal list is now load-bearing on image quality, not just on hygiene. Routed.

### 31.3 What this arm cost, and the one thing it settles

Two renders, 468.7 s and 685.6 s, both `exit=0`, both logs confirming the fit
ran and was applied (`applied=2 trivial=0 absent=0`, a partition that sums).
The `--photometric` state was checked by reading what the log said it *did*,
not by observing that the flag was accepted.

It settles §30's open product question. §30 showed M122's KEEP-OFF verdict does
not survive spatial partitioning and that `--photometric` costs 0.4% of subject
texture with a CI including 1.00. That argued the flag is **safe**. This section
measures what it **buys**, which §30 never did: a fifth to a quarter of the veil
in the first 16 px and nothing past 64. Safe and worth having is a different
claim from safe, and only the pair of them justifies changing a default.

## 32 — The hull clamp works, verified interventionally and by eye

BUILD-BLEND implemented the clamp §29 argued for (`275fbd1`). This section is
ORCH's independent verification of it. The author's own test is not the evidence
here; the four renders below are.

### 32.1 The instrument: one commit, one line, two binaries

Comparing the new build against the older pinned binary would have confounded the
clamp with every other change on that lane. Instead `interv.py` exports **two
`git archive` trees from one pinned commit** (`3dfa435`) and mutates exactly one
line in one of them:

```
crates/strehl-core/src/pyramid.rs:823
-             hull: Hull::InputRange,
+             hull: Hull::Unclamped,
```

The shared `crates/` is never touched — ORCH does not own it and six implementers
are editing it live. The harness refuses to proceed unless the mutation lands
(hard error, anchored on a unique full line), unless the control tree is verified
still pristine, and unless **the two binaries hash differently**: `458ecd00a5c8d5f3`
against `f62f41da9e107bd0`. A one-line control that compiles to the same bytes is
testing nothing, and that check is not hypothetical — the first run of this
harness correctly refused an already-mutated tree rather than silently reporting
a no-op.

All four renders pin `--chunks 5`, because VERIFY-WIRE measured that worker count
changes the reduction order and moves output by 1 DN.

### 32.2 The defect is gone

| subject | arm | exact-zero px | exact-zero % | luma<500 % |
|---|---|---:|---:|---:|
| flower-bud-alone-cpl | unclamped | 122,416 | 0.371% | 1.310% |
| flower-bud-alone-cpl | **clamped** | **0** | **0.000%** | **0.000%** |
| dry-erase-marker-head-cpl | unclamped | 345,850 | 1.048% | 3.342% |
| dry-erase-marker-head-cpl | **clamped** | **0** | **0.000%** | **0.000%** |

### 32.3 It is a scalpel, and this is the check that could have failed

A fix that removed the crush by lifting or flattening the whole frame would pass
§32.2 and fail the product. The footprint says it does not:

| | flower-bud | dry-erase |
|---|---:|---:|
| samples moved | 11.63% | 16.30% |
| of those, raised | 85.0% | 81.2% |
| median magnitude | 275 DN | 239 DN |
| p99 magnitude | 1814 DN | 1847 DN |
| **unclamped luma at moved px, median** | **1364** | **1499** |
| whole-frame luma, median | 18551 | 22646 |
| net mean change, whole frame | +40.10 DN | +52.28 DN |

The clamp acts on pixels whose luma is an order of magnitude below the frame
median — it goes where the crush is. Net global change is +0.2%.

### 32.4 The veil win survives, which was the actual risk

The reason to want this backend is that it removes the halo. A clamp that bought
clean blacks by giving that back would be worthless. Same shared mask and
distance transform as §31, computed once from the estimator arm.

**flower-bud** — identical from 16 px outward, under 1% cost inside it:

| d (px) | ctrl | unclamped | clamped |
|---|---:|---:|---:|
| 8..16 | −1846.8 | −1151.0 | −1160.1 |
| 16..32 | −1866.1 | −981.3 | −981.3 |
| 32..64 | −1679.6 | −1069.1 | −1069.1 |
| 300..400 | −548.0 | −500.7 | −500.7 |

**dry-erase** — 94–96% of the win retained:

| d (px) | ctrl | unclamped | clamped | win retained |
|---|---:|---:|---:|---:|
| 16..32 | −7852.1 | −4914.9 | −5027.0 | 96.2% |
| 32..64 | −6966.5 | −2198.1 | −2457.3 | 94.6% |
| 200..300 | −854.3 | −50.7 | −60.0 | 98.8% |

### 32.5 And I looked at it

Sheets at `C:\dev\strehl-out\AB-clamp\`, full frame and 100% crops, both arms
through one tone window computed from the reference arm only. The estimator arm
puts the subject in a grey puddle with a bright rim tracing every contour. The
clamped pyramid has none of it, and at 100% it resolves individual trichomes
against clean white where the estimator's halo swallows them.

This step is not decoration. §28 records the reversal that happened when I read
band statistics and matched crops without rendering the whole frame. A number
that moves the right way is a hypothesis about the picture; the picture is the
measurement.

### 32.6 What is now the blocker

Not image quality. `--gate` and eight other flags are **refused** under the
pyramid backend (`main.rs:730-746`), so the day the default flips, every command
line in this repository's own harnesses — including `clean6.ps1`, which passes
`--gate 4` — begins failing with exit 1. The flip is a migration, not a constant.
Routed to BUILD-WIRE with the acceptance test: run the exact documented command
lines against a flipped build and report exit codes.

## 33 — What the clamp does not fix, and a noise penalty I could not reproduce

§32 verified the clamp on the defect it was built for. V-RIM, verifying a
different pair of claims, returned two results that temper it. Both are recorded
here at full strength because §32 reads more triumphantly than the evidence now
supports.

### 33.1 The clamp bounds the error; it does not remove its cause

V-RIM's measurement, at the exact sites that used to clip: HEAD reads **805 DN
where the shipping estimator reads 2162 DN**, one-sided (p90 = −29). The
exact-zero count goes to zero — §32.2 is not wrong — but the reconstruction is
still landing far below the other arm in those cells. A clamp is a bound. It
cannot manufacture the value that should have been there; it can only refuse to
emit one the frames do not support.

So §32's "the defect is gone" is true of **the clipping** and false of the
**underlying estimate**. The correct statement is: the pathology that produced
visible black holes is bounded, and the estimator that produced it is still
wrong in the same direction, by a smaller amount, in the same places.

### 33.2 Two corrections to the clip figures themselves

V-RIM reproduced the original sRGB numbers to the pixel (723,429 / 2.1920% /
10,913 DN) and then repeated the measurement in camera-linear:

- the clean-space figure is **1.06%, not 2.19%** — the tone stage doubles it;
- it is **not one channel**. `dry-erase` clamps all three at ~2%.

Six subjects. The only one that does not clamp is `couch-fibers`, whose minimum
is 562 DN — the one subject with no shadows. That is the right control result:
the defect needs darkness to express, and the subject without darkness does not
express it.

### 33.3 A noise penalty I could not reproduce, and where I did not look

V-RIM reports the blend **noisier than one raw exposure** in the out-of-focus
backdrop — 1.210x on flower-bud, 1.582x on bee-1 — measured against the
project's calibrated noise model on a tile selector belonging to neither arm.
For a 205-frame stack that is roughly sqrt(205) the wrong side of where it
should be, and if it is real it prints as a blotchy background.

I tested it on flower-bud with my own instrument (`flatcrop.py`, tiles chosen
by **flatness** on a three-arm mean, the opposite selection rule to `sheet.py`)
and **did not reproduce it there**:

| tile | mean DN | estimator | pyr-unclamped | pyr-clamped |
|---|---:|---:|---:|---:|
| 1 | 17407 | 16.5 | 16.6 | 16.6 |
| 2 | 18352 | 16.5 | 16.8 | 16.8 |
| 3 | 17853 | 17.5 | 17.8 | 17.8 |
| 4 | 18374 | 17.1 | 17.4 | 17.4 |
| 5 | 19363 | 17.7 | 17.8 | 17.8 |
| **median** | | **17.3** | **17.1** | **17.1** |
| ratio | | 1.000 | 0.987 | 0.987 |

On the bright backdrop the three arms are indistinguishable, and 17 DN on
18,000 DN is about 1000:1 — consistent with 205 frames averaging properly.

**This is not a refutation and I am not offering it as one.** V-RIM measured a
different region on different subjects against a physical floor; I measured
bright flat backdrop on one subject against the other arm. Two instruments that
do not overlap cannot contradict each other. What I can say is bounded: *on
flower-bud's lit backdrop there is no noise penalty*, and the failure V-RIM
found is not there. Where it is, and whether it survives on the clamped build,
is unmeasured.

### 33.4 The one tile that showed everything

The instrument found one dark tile (y=1920 x=2432, mean 2057 DN) and it carries
more information than the five flat ones:

| arm | sigma DN |
|---|---:|
| estimator | 17.4 |
| pyramid unclamped | **5.0** |
| pyramid clamped | 10.7 |

The unclamped arm is the **quietest** of the three there, and that is the point:
it is quiet because it is crushed. A noise statistic rewards a flat black hole.
Rendered at 100% (`AB-clamp/flower-bud-flattile.png`, one stretch from the
three-arm mean) the panels read: estimator blown to white by the halo, unclamped
pyramid near-solid black, **clamped pyramid showing real gradient and real
texture** in the same cell. The clamp is recovering structure, not just
satisfying a bound.

> **A noise figure alone cannot tell a well-averaged region from a destroyed
> one. Both are smooth. Report it beside a measure of what content survived.**

That is the same failure as §30's K2 and the same shape as §26.2's amplitude
without correlation — the third and fourth instance of a statistic that is blind
to the difference between removing an artefact and removing the picture.

### 33.5 Open, and routed

- Is 805 DN right? Neither arm is a trustworthy reference in those cells: the
  estimator is blown out by its own halo there, and BUILD-HALO measured the
  merge below the per-frame envelope **everywhere**, both arms. A third
  reference is needed before anyone calls a number in the shadows correct.
- Does V-RIM's backdrop noise penalty survive the clamp, and on which subjects?
- V-RIM's own methodological finding, which applies to every noise number in
  this corpus: letting the arm under test help select the tiles **halved** its
  measured noise (128.8 → 68.4) while moving the control 9%. Every noise figure
  measured that way — BUILD-BLEND's +12.3%, V-RIM's own +32/+105/+1605% — is a
  **lower bound**.

## 34 — `focus.rs` is not on the pyramid path, proved by a byte-identical null

V-M111 was asked to measure what restoring a deleted focus-window shrink term
costs in aura, *on top of* the multi-band merge. It could not, and the reason it
could not is the most useful thing it found.

### 34.1 The null, with a live positive control beside it

Two arms, same binary, one with the shrink restored:

| arm | sha256 | verdict |
|---|---|---|
| pyramid A | `F267BD82…C13C9` | **identical** |
| pyramid B | `F267BD82…C13C9` | **identical** |
| estimator A | `9B777C0B…` | differ |
| estimator B | `75AE09E0…` | differ |

The pyramid output is **bit-for-bit unchanged** by a modification that visibly
moves the estimator output **in the same binary, in the same run**. That is a
null with its own positive control attached, which is the only kind worth
reporting. Structurally: the shrink lives in `run_estimator` (`merge_cmd.rs:2548`)
and `run_pyramid` begins at `:3586`.

**Consequence, and it is a planning consequence rather than an imaging one:**
every hour spent on `focus.rs` and the estimator's focus window is an hour spent
on a path that the pyramid does not execute. If the pyramid ships, that work
ships nothing. This answers the question §27 left open and that I had put to
BUILD-HALO — asked as a call-graph question, answered instead by a hash.

### 34.2 The shrink restore is free, and it should be taken anyway

On the path where it does something:

| subject | aura change | sign |
|---|---:|---|
| flower-bud-alone-cpl | **+444 DN** of 14617 (3.0%) | **fills the veil in** |
| bee-1-cpl | +92 DN (0.50%) | fills in |
| coffee-bean | +48 DN (0.086%) | fills in |

and the sharpness it buys back **exceeds the loss its deletion was meant to
avoid** — `bee-1-cpl` gradient RMS **1.1618**, HF **1.3510**.

The commit that deleted it justified the deletion by background noise on three
flat patches of one subject, predicting 11–16% less noise. Measured: **1.0187 —
slightly more.** Justified on one subject by a statistic that does not
reproduce; refuted on 26 by a different one. The estimator is what ships today,
so this is a real and free improvement to the shipping binary.

The restore must be **surgical, not `git revert`**: that commit also swapped
`from_acuity`→`from_silhouettes`, deleted the confidence veto, `FLOOR_Q` and
`conf`, and changed `regularise_guided`. A revert would take the halo fix with
the shrink and the resulting sharpness gain would arrive bundled with a
regression nobody would attribute correctly.

### 34.3 Retraction 22 — my own blend arms were sRGB, not linear

I briefed V-M111 that paired **linear** 16-bit TIFFs were on disk. They are
sRGB: `blend-render.rs:543-549` defaults to `Srgb`. Every DN in the profile
table I handed it is in the wrong space, and the "−6.90 → −0.94 of 255" line I
quoted is double-encoded.

The correction does not weaken the conclusion — it **strengthens** it, and it
reveals something the wrong space was hiding. `rimprofile.py`'s interior-peak
list on the control goes from

```
[(275, 403)]        ->        [(22, 3739), (275, 765)]
```

**A real ring at d = 22 px was invisible in sRGB.** V-M111 corroborated it on
an independent camera-native render. The blend removes it by 93%.

### 34.4 The number 22 has now arrived by three independent routes

- BUILD-HALO **predicted** it from the focus measure's own geometry:
  SOBEL(1) + WINDOW(13) + REGULARISER(8) = **22 px**, and measured the merge's
  radial crossover at ~20 px.
- V-M111 **measured** an interior ring peak at **d = 22 px** on a corrected
  linear profile.
- V-M111 **reproduced** it again on a separate camera-native render.

A prediction from first principles and two independent measurements landing on
the same number is the strongest single piece of mechanism evidence in this
corpus. It says the estimator's rim is its focus window's support radius made
visible, and that is a defect with a known cause and a known fix — which the
pyramid also happens to remove by not having a focus window at all.

### 34.5 My placebo tested nothing

`109MSDCF` was registered as the placebo: any aura change from the shrink
restore must be approximately nil there. It read exactly 0 DN. It reads 0 DN
because its **dose is zero** — radius 13.00 → 13.00, the veto admits 0 px. The
treatment was never applied.

> **A placebo that received no dose is an inert probe, not a passing control.
> Report the dose beside the response, or a zero reading proves only that
> nothing happened.**

No subject in the corpus has a strong dose *and* no occlusion, so this control
does not currently exist. Recorded as a gap rather than papered over.

### 34.6 One thing I must not now tell BUILD-RENDER

I hypothesised that `couch-fibers-cpl`'s guard reference fires because it
predates the tone fix. **Refuted:** contrast differs 0.36%, mean 0.5 DN. The
guard is firing on something else and I nearly sent a lane chasing a wrong
explanation.

## 35 — Retraction 23: every veil ratio I published was measured against a contaminated reference

V-TONE returned its verdict on the four-link chain that is carrying the merge-backend
decision. It refuted one link and qualified another, and both findings are against my
interest. I am recording them before anything else in this section, because the numbers
they invalidate are quoted in four places above this line.

### 35.1 The reference was the defect

Every veil measurement in §27, §31, §32 and §33 computed a background deficit against a
**global far-field median**. V-TONE measured the far field itself and found it is not
flat: on `flower-bud-alone-cpl` its p5–p95 spread is **3610.4 DN**, which is **1.75x the
entire signal I was claiming**. Sixty-one percent of the "veil" I attributed to the
estimator backend is backdrop gradient that was in the scene.

Re-stated against a **local** backdrop fitted per image, the estimator's deficit is
**-813.5 DN**, not the -2269.6 DN I published.

| quantity | as I published it | against a local backdrop |
| --- | --- | --- |
| flower-bud deficit at d=0..2 | -2269.6 DN | **-813.5 DN** |
| far-field p5-p95 (the reference's own spread) | not measured | **3610.4 DN** |

I did not measure the spread of my own reference. That is the whole error. A median is a
location estimate and says nothing about whether the thing it locates is homogeneous, and
I had a rule about medians without rails and tails that I did not apply to the one number
every other number was divided by.

> **Rule.** A ratio is a claim about its denominator too. Measure the reference's own
> spread before dividing by it, or the ratio inherits a variation you never looked at.

### 35.2 I killed the ringing hypothesis with a broken test

§28.3 rejected ringing because the profile looked monotone from the edge outward. It is
not monotone **in my own data** — there is an interior extremum, -1235.9 DN at d=8..10
falling to **-1582.9 at d=16..18** — and under a local reference the pyramid runs +1.9 DN
at d=0..2, **+274.3 at d=24..32**, then -169.4 by d=200..300. That sign change with an
extremum a few tens of pixels out is the signature I said was absent. The monotonicity I
relied on was an artifact of the contaminated reference.

### 35.3 What survives

The visual result of §32 is unaffected: it was a picture, not a ratio. The clamp census is
unaffected: exact-zero pixels 122,416 -> 0 and 345,850 -> 0 are counts, not ratios against
a far field. What does not survive is the **magnitude** of the veil advantage, and every
place I wrote "0.526 at 16-32 px" should now be read as a ratio between two contaminated
quantities whose true separation is roughly a third of what I reported.

The decision this was carrying — flip the merge backend — is therefore no longer supported
by the veil ratios at all. It is supported by the clamp census, by the absence of a halo in
the pixels, and by whatever V-TONE now reads when it re-points its hull instrument at the
**clamped** arm. That last measurement does not exist yet and I have asked for it.

### 35.4 The tautological control, admitted

V-TONE also found that `hullproof.py`'s shared-weight control is **provably zero** — a
null dressed as a positive control. Its own planted version catches 200/200 at
hull+0.05x span. I filed an identity as evidence in the same document that states the rule
"a placebo that received no dose is an inert probe, not a passing control." Writing a rule
down does not apply it.

And my 205-frame extrapolation runs the wrong way in my own model: the rate falls to
0.000% as hull span grows 0.597 -> 0.820. The correct argument is per-pixel weighting,
which gives **11.58%**, about 100x my toy. I asserted a direction I had not computed.

---

## 36 — Lateral CA correction: red is real, blue may be free blur

`--fix-ca` is **off by default** today. Reviewing `bee-1-cpl` on a uniform 3x3 grid at 100%
I could see cyan and magenta fringes on the pollen grains of the foreleg and along the
leg's edge against the white backdrop. That is a print-relevant defect, visible without
instruments, shipping by default.

### 36.1 The arms

One binary, one set of flags, one environment variable. `--gate 4 --base-mean --chunks 5`
on both; arm B adds `STREHL_FIX_CA=a7c2-fe100gm-2xtc-x4cpl`, and its log confirms
`lateral CA : CORRECTING`. This is the cleanest intervention available in this project:
nothing was rebuilt between arms.

### 36.2 The fringe is reduced, and the placebo is clean

Whole-frame census. Pixel selection is made on the **arm-mean**, so neither arm chooses the
ground it is judged on. Edge set is the top 1% of gradient; flat set is the bottom 50% and
serves as the placebo, because a radial channel warp must be a near-no-op where there is no
edge.

| set | sigma(R-G) | sigma(R-B) | sigma(B-G) |
| --- | --- | --- | --- |
| edge, CA off | 0.09186 | 0.15653 | 0.09732 |
| edge, CA on | 0.06773 | 0.12618 | 0.09334 |
| **edge ratio** | **0.737** | 0.806 | 0.959 |
| flat, placebo ratio | 1.005 | 1.006 | 0.999 |

The placebo moves by at most 0.6% while the dose set moves 26%. That separation is what
makes the effect attributable to the intervention rather than to the render.

### 36.3 Two discriminators died, and the second died usefully

The obvious way to price the correction is HF amplitude: R -13.16%, B -9.36%. **That
number cannot distinguish removing a fringe from blurring a channel**, because both lower
it. It is the same shape of error as §33.4 — a scalar with no structural argument cannot
tell a repair from a destruction.

The second attempt was correlation against green: alignment should move R's edges onto G's
and raise `corr(HF_R, HF_G)`, blur should smear them and lower it. I built it with a
potency control — a synthetic blur of R calibrated to reproduce the *same* amplitude loss
the real correction produced — and the control killed it. The synthetic blur **raised** the
correlation, 0.5637 -> 0.6036, because blurring removes noise that is uncorrelated with
green. Both hypotheses predict the same sign; the discriminator has no power.

That is the second time tonight a control has stopped a conclusion before it entered the
record, and both times the conclusion would have been wrong.

> **Rule.** A discriminator must be shown to separate the hypotheses, not merely to
> respond to one of them. Calibrate the rival hypothesis to the same effect size and check
> the two answers differ in sign.

### 36.4 Physics gives a discriminator, and a null for free

Lateral chromatic aberration is a per-channel magnification difference. Its displacement
field is therefore **strictly radial**, and the **tangential component is a null the physics
hands over at no cost** — no fitting, no extra render, measured on the same tiles by the
same estimator as the signal. Green is a second null, being the reference channel.

The estimator was commissioned before any of its numbers were used. A known radial
magnification change was planted at three amplitudes:

| planted at corner | recovered | ratio |
| --- | --- | --- |
| 0.05 px | 0.0128 px | 0.257 |
| 0.20 px | 0.0532 px | 0.266 |
| 0.50 px | 0.1465 px | 0.293 |

Stable across a 10x range, therefore linear shrinkage, therefore division by 0.266 is
legitimate. This project has been bitten by a shrinking shift estimator before — fact 45,
recovery ratio 0.56 — which is why no raw number from this instrument was published.

Shrinkage-corrected, 155 textured tiles:

| channel | radial px | tangential px | radial/tangential | vs field radius |
| --- | --- | --- | --- | --- |
| **R** | 0.152 | 0.015 | **9.94** | 0.041 -> 0.094 -> 0.158 -> 0.177 -> 0.158 |
| G (null) | 0.015 | 0.011 | 1.35 | flat at noise |
| **B** | 0.039 | 0.030 | **1.30** | 0.004 -> 0.030 -> 0.034 -> 0.004 -> **-0.053** |

**Red is an unambiguous lateral-CA correction.** Radial dominates tangential 9.94:1 and the
magnitude rises with field radius, which is what a magnification difference must do.

**Blue is indistinguishable from the untouched reference channel.** Its ratio of 1.30 sits
inside green's own null of 1.35, and its radius profile changes sign at the outer field,
which no magnification change can produce — while it still pays 9.36% of its edge HF. The
hypothesis routed to an implementer is that blue's coefficient is too small to deliver a
useful shift and the pipeline resamples anyway, paying a full interpolation blur for
nothing. It is a hypothesis. The rival explanation — that my tiles simply lack blue
structure at large radius, making this an absence of measurement rather than an absence of
effect — is not yet excluded, and I have asked for the blue-signal tile count before
anyone credits it.

### 36.5 A scalar said nothing happened while 4.5% of the pattern moved

The first control I wrote asserted green must be bit-stable across arms, since a lateral
R/B warp does not touch it. It **failed**: `corr(HF_G off, HF_G on) = 0.9555`. But green's
HF *amplitude* moved only **-0.16%**.

So the amplitude reported "nothing happened" while the correlation reported that 4.5% of
green's high-frequency pattern had been rearranged. The attributed cause is pre-demosaic
correction coupling into green's interpolation, which is a prior finding of another agent's
that **I have not verified myself**, and I have said so where it matters.

> **Rule.** An amplitude cannot tell "unchanged" from "rearranged". Registration and
> magnitude are separate questions and a single scalar answers only one of them.

The correct response was not to delete the control but to demote it: it tested a stronger
claim ("pure R/B warp") than the analysis needed, so the comparison was re-stated as
**within-arm**, where each arm's red is judged against its own green and green's
cross-arm behaviour is irrelevant. The failing control stays in the file with its failure
printed.

### 36.6 Status

Default-on is **recommended, not decided**. It is routed to an implementer to land and to
an independent auditor to attack, with the five places I think I am most likely wrong
stated to the auditor rather than discovered by them: green's unverified attribution, a
single favourable subject, no tiles in the outermost radius bin, blue's possible sampling
artifact, and the fact that my commissioning plant uses my own resampler rather than the
pipeline's.

---

## 37 — The acceptance gate passed, measured through the shipped binary

`merge_cmd.rs` carries the flip as a named constant with its blocking condition written
out in prose, ending in one sentence: **"This line moves the day that clip passes the
gate."** That is the best piece of process design in this codebase — a decision with one
address, a stated criterion, and a measurement rather than an opinion behind it. Tonight
the criterion is met.

### 37.1 The measurement

Shipped `strehl.exe` built from pinned HEAD `4ea70dca` in an isolated `git archive` tree,
because the repo-root release build fails `Access is denied (os error 5)` under nine
concurrent agents. Camera-linear, `--demosaic`, with `STREHL_FIX_CA`, `STREHL_PHOTOMETRIC`
and `STREHL_MERGE` removed from the environment so the arms differ in the merge and in
nothing else.

| subject | arm | clip% | p1 (DN) | exact-zero px |
| --- | --- | --- | --- | --- |
| flower-bud-alone-cpl | estimator | 0.0000 | 1003.7 | 0 |
| flower-bud-alone-cpl | **pyramid** | **0.0000** | **1012.7** | **0** |
| couch-fibers-cpl | estimator | 0.0000 | 3091.3 | 0 |
| couch-fibers-cpl | **pyramid** | **0.0000** | **3266.0** | **0** |

Against the recorded blocker:

| quantity | recorded | now |
| --- | --- | --- |
| flower-bud clip% | pyramid **1.4043** vs estimator 0.0001 | pyramid **0.0000** vs estimator 0.0000 |
| flower-bud p1 | pyramid **334** vs estimator 1028 | pyramid **1012.7** vs estimator 1003.7 |

Both ends of what BUILD-WIRE correctly called "a contrast expansion at both ends" are
closed. The pyramid's shadows now sit marginally **above** the estimator's rather than
collapsed below them.

The pyramid is also **faster**: 72.6 s against 108.1 s on flower-bud, 106.1 s against
151.9 s on couch-fibers. About 32% off wall-clock on the subject that was blocking.

### 37.2 The gate can fail, which is why its passing means anything

`flipgate.py` asserts the **estimator** arm still reads what the constant records, on the
grounds that if the baseline has drifted then this is not the comparison the constant
authorises. It reads clip 0.0000 against the recorded 0.0001 and p1 1003.7 against the
recorded 1028 — intact. Had the estimator moved, the script withholds a verdict instead of
returning one.

That matters because a gate whose only outcome is "pass" is not a gate. This one has a
withheld state and two independent fail states, and the numbers it compares are the two
the constant itself names rather than two I chose after seeing the data.

> **Rule.** A gate on a decision must re-measure the baseline the decision was written
> against, not only the arm under test. A drifted baseline turns a comparison into a
> coincidence.

### 37.3 What this does not settle

The quality blocker is gone. **F2 is not**: with the default flipped, every command line
carrying `--gate`, `--target-n-eff`, `--index-map`, `--n-eff-map`, `--photometric`,
`--stats`, `--flat-roi` or `--detail-roi` exits 1, because those are refused rather than
ignored under the pyramid. That refusal design is **right** and should not be weakened —
tonight produced two fresh instances of the failure it exists to prevent, `STREHL_FIX_HALO`
printing `halo fix : ON` while emitting byte-identical output, and `EDGE_AWARE` on by
default but throttled to a 99.46% share of its floor radius. Accept-and-ignore is how both
of those became invisible.

So the remaining work is a compatibility migration, not a quality one, and it is the last
thing between this project and its default being the merge that makes its good pictures.

### 37.4 The state of the pictures

All 26 subjects render through the clamped pyramid with `dark<500` between **0.00% and
0.03%** and highlight clip at or below 0.32%, that maximum being a black marker head
against white, which is specular and legitimate. No halo is visible on any subject,
including the flower-buds that were the worst cases in this corpus. Text renders with
individual toner particles resolved and no fringing on black-against-white, which is where
a halo is most visible and where registration error would show first.

Two subjects are soft: `flowers-cpl`, badly, and `highly-angled-ruler-mm-cpl`, mildly and
plausibly by geometry. Whether `flowers-cpl` is capture-limited or a merge failure is
under independent test against the strongest available invariant — that a stack must never
be worse than the best single frame that went into it — and I am not guessing at the
answer here.

---

## 38 — The two WASHED flags are the sweep, not the render: a global statistic priced by area

`scripts/tone_profile.py` is the project's display-space acceptance instrument, and run
across the 26 delivered JPEGs it flags two subjects **WASHED**:

| subject | median | p99.9 | span | flag |
|---|---|---|---|---|
| `flower-bud-alone-cpl` | 0.936 | 0.978 | **0.042** | WASHED |
| `flower-bud-with-background-fern-cpl` | 0.892 | 0.978 | **0.086** | WASHED |

Everything else passed, and the delivered gallery is the thing the owner will look at, so
a flag on it is a blocker until it is either fixed or shown to be false.

### 38.1 First: the gallery is not an artifact of the example binary

My delivered gallery came from `blend-render`, not from the shipped `strehl stack`, and the
shipped path has an exposure policy the example binary does not run. So the flag had an
innocent explanation available: I rendered around the policy. That is worth ruling out
before anything else, because if true it would mean the delivered images misrepresent the
product.

Rendered both subjects through the shipped binary with the flip's own configuration —
`strehl stack --merge pyramid --srgb --auto-exposure` — and measured the same instrument:

| subject | blend-render median / span | shipped `--auto-exposure` median / span |
|---|---|---|
| `flower-bud-alone-cpl` | 0.936 / 0.042 | **0.935 / 0.043** |
| `bee-1-cpl` | 0.761 / 0.216 | **0.761 / 0.217** |

Agreement to 0.001 in both statistics on both subjects. Two things follow. The exposure
policy does not move this, so the flag is not a rendering-path mistake. And, incidentally
but usefully, **the gallery I delivered is tonally the shipped product** — that was an
assumption I had been carrying and it is now measured.

### 38.2 The flag is measuring backdrop area

Both flagged subjects are the same presentation: a small subject on a **white sweep**. That
is a standard macro studio setup, not an error. The backdrop is legitimately near-white and
legitimately occupies most of the frame, so a frame-global median reports *how much sweep
is in shot*. Grow the sweep and the median rises with no change whatever to how the subject
is rendered.

This is the same defect as retraction 23 and it is worth naming as a class: **a summary
statistic whose value is set by a region nobody is judging.** There it was a far-field
median contaminated by a backdrop gradient; here it is a frame median contaminated by
backdrop area. In both cases the number was real, computed correctly, and answering a
question no one asked.

So split the frame and measure each region on its own — `subjtone.py`, segmenting on the
bright mode, because the one thing certain about a white sweep is that it is the bright
mode. The split is reported rather than assumed: a run that captures 2% or 98% of the frame
is refused rather than scored.

### 38.3 Commissioning: the instrument must still be able to say "washed"

An instrument built to overturn a flag will overturn it. So it ships with the plant that
would make it fire: compress the **subject** pixels toward their own mean by 10x in linear
light, leaving the backdrop untouched, segmenting once on the unplanted frame so the plant
cannot move its own boundary.

| subject | subject span, live | subject span, 10x plant |
|---|---|---|
| `flower-bud-alone-cpl` | 0.419 | **0.047  SUBJECT WASHED** |
| `flower-bud-with-background-fern-cpl` | 0.664 | **0.065  SUBJECT WASHED** |
| `bee-1-cpl` | 0.735 | **0.062  SUBJECT WASHED** |

Three for three. And the backdrop column is *bit-identical* across the two runs
(0.061 / 0.087 / 0.104 both times), which is the plant's own null: it proves the
disturbance went where it was aimed and did not leak into the region used to normalise.

### 38.4 Result: 26 of 26 subjects carry subject-region range

`flower-bud-alone-cpl`'s **subject** spans **0.419** — ten times the frame-global 0.042 that
raised the flag. Across the gallery the ordering is monotone in subject fraction (21.9% →
0.419, 40.5% → 0.664, 62.1% → 0.735), which is exactly the signature of an area-driven
statistic and not of a tone problem.

Every subject reads "subject has range" except `coffee-bubbles`, which the instrument
**self-flagged as SPLIT DEGENERATE** at 99.4%: it is a dark frame with no bright mode, so
there was no backdrop to split off and the "subject" region is the whole frame. Its
frame-global span is 0.944 — the opposite of washed. The guard refused to let a meaningless
number print as a verdict, which is the behaviour I want and the reason the degenerate case
is a printed state rather than a silent pass.

**Both WASHED flags are false positives of a global statistic on white-sweep presentations.
The delivered gallery is clean on tone.**

### 38.5 A defect in `scripts/tone_profile.py`, for whoever owns it

The WASHED rule needs a subject-area qualifier, or it will keep firing on white-sweep work
— which is a large fraction of serious macro. I have not touched the file; it is not mine.
Reported here with the reproduction and the fix direction: compute the span over the
non-backdrop region, and print the segmentation fraction so a degenerate split is visible
rather than scored.

> **A statistic computed over the whole frame is a claim about the whole frame.** If the
> thing being judged occupies a quarter of it, the number is mostly about the other three
> quarters. Segment before summarising, and print the segmentation so the reader can
> disbelieve it.

### 38.6 What this also settles about the halo

`flower-bud-alone-cpl` is the hardest halo case in this corpus: a dark, hairy subject
against a blown white backdrop, which is the geometry that produced the worst artifacts
recorded here. At full frame the boundary is clean — individual hairs project into the
white and stay individually resolved, with no dark rim and no bright rim. That is a visual
observation, and it is consistent with the census in section 33 rather than a substitute
for it.

---

## 39 — The patchwork, priced: 1.31x for the pyramid against 4.00x for pure selection

The README lists two open defects. The halo is fixed and censused (section 33, and the
hardest case by eye in 38.6). The other — a *polygonal patchwork in defocused backgrounds*
— I had never measured, and I will not call a product finished with a named defect
unchecked.

### 39.1 The selection rule is the instrument

`flatcrop.py` ranks tiles by flatness **of the output**. For this defect that rule is
actively wrong: patchwork is what makes an output tile non-flat, so ranking on output
flatness selects against the thing being looked for. `patchwork.py` inverts it — tiles are
chosen because the **input frames** are featureless there, scored on the *worst* of the
sampled frames, and the output never participates in choosing where it is measured.

### 39.2 What the test can prove

For a spatially **constant** convex weighting `w_k` (`w_k >= 0`, `sum w_k = 1`), filtering is
linear and commutes with the weighting:

```
HF( sum_k w_k x_k ) = sum_k w_k HF( x_k )     =>     ||HF(out)|| <= max_k ||HF(x_k)||
```

So output high-frequency amplitude materially above the single-frame maximum, in a region
featureless in every frame, cannot come from any constant convex weighting. It is invented,
or the weights vary in space — which is the patchwork hypothesis.

### 39.3 Two of my own errors, caught before they became a claim

**A colour-space mismatch inflated the effect by 82%.** I first compared a `--srgb` output
against inputs decoded at `gamma=(1,1)`. Gamma encoding amplifies high frequencies in dark
regions, and the background is dark: the ratio read **2.38**. Re-rendering camera-linear so
both arms share a space gave **1.31**. Most of the defect I was about to report was my own
encoding.

**My plant was inert and I nearly accepted it as commissioning.** A 60 DN polygonal plant
moved the ratio 2.379 -> 2.393. That is not a potent disturbance; it is a plant swamped by
the live signal, and had I stopped there I would have certified an instrument on a
disturbance it could not feel.

> **A plant that does not move the number has not commissioned anything.** Compare its
> effect to the live signal before calling a response a response.

### 39.4 The arm ladder, which commissions it properly

Instead of a synthetic plant, drive the **real pipeline** to configurations whose answers
are known, and measure all of them with the one instrument. Same subject, same frames, same
demosaic, same warp, same 2x box downsample — every systematic is common to all arms.

| arm | `mean n_eff` | HF / single-frame max | what it is |
|---|---|---|---|
| `--gate 100000` | **299.000** (`n_eff=1`: 0.00%) | **0.074** | a true global average: spatially constant convex. **The floor.** |
| `--merge pyramid` | — | **1.305** | the flip candidate; the shipped default is the estimator |
| `--gate 0` | **1.000** (`n_eff=1`: 100.00%) | **3.996** | pure winner-take-all: what every other stacker does |

The floor arm lands at **0.074** against a predicted `1/sqrt(299) = 0.058`, and the binary's
own model independently printed a sigma gain of `0.0578x` for that configuration. The
instrument therefore spans **54x** between a known-convex arm and a known-selective one,
which is a far better commissioning than the plant that failed above.

It also **eliminates every systematic I could name**: the floor arm passed through the same
MHC demosaic, the same warp, the same white balance and the same downsample, and still read
0.074. None of those can be the cause of 1.305.

### 39.5 Verdict

**The patchwork is real and it is 1.31x** — the pyramid does put more high-frequency
structure into all-frames-featureless regions than any spatially constant convex weighting
can. It is not invented from nothing; it is the spatial variation of the merge weights,
exactly as M120 argued.

**And it is 3.06x smaller than pure selection.** The 4.00x selector arm is close to M120's
independently measured 3.4x, which is a cross-validation of both instruments — different
code, different subject sampling, same conclusion about the selective path.

This is the project's thesis measured directly on a real capture: selection invents
background structure, estimation mostly does not, and the residual is now a number someone
can be assigned to reduce rather than an adjective in a README.

### 39.6 Scope, honestly

One subject (`bee-1-cpl`), 8 of 299 frames sampled, 6 tiles, one spatial scale (a 4 px
box high-pass at half resolution). The arm ordering is large and unambiguous, but the
**absolute** 1.305 should not be quoted as a gallery-wide constant until it is run across
subjects and scales. It is a floor-referenced ratio on one subject, and that is all.

---

## 40 — The patchwork is a gate default, not an architecture problem: 1.305 -> 0.165 for free

Section 39 priced the patchwork at **1.305x** and left it as work for someone. It is
cheaper than that. The mechanism is written in `pyramid.rs`'s own design notes, and once
read it names its own fix.

### 40.1 The mechanism, from the module's own reasoning

`sharpen_per_octave` makes fine bands deliberately **near-argmax**, on the stated argument
that "a selection error at a fine scale injects only a small-amplitude, high-frequency
error". That argument is sound where there is signal. In a region that is **featureless in
every frame**, the fine bands contain *only noise* — so near-argmax selects the frame that
happened to fluctuate highest, independently at each pixel. That is amplified noise with
spatially varying weights, which is exactly what the patchwork is and exactly what "stacking
sparkle" means.

The defence against it already exists: `gate`, whose doc says `2.0` sits "roughly 2.6 of its
own standard deviations above the noise expectation: high enough that noise essentially
never wins a selection, low enough that real low-contrast detail is not thrown away." The
first clause is the claim I tested.

### 40.2 Three probes, because two of them cannot see the risk

A gate change is trivially good on featureless tiles and trivially invisible on the most
textured ones, which sit far above any gate. Measuring only those two would be measuring
where the answer is easy. So `patchwork.py` grew a third selection rule at the **median**
input texture — the only place a raised gate can quietly cost something.

Each detail probe is commissioned against the global-average arm, which must collapse if
the probe can see detail loss at all:

| probe | gate 2.0 | gate 3.0 | gate 4.5 | global-average sensitivity check |
|---|---|---|---|---|
| background, featureless in every frame | **1.305** | 0.434 | **0.165** | 0.074 |
| **mid-contrast** | 4.340 | 4.339 | **4.338** | **0.206** — a 21x drop |
| high-contrast detail | 1.108 | 1.109 | **1.109** | **0.046** — a 24x drop |

**Background invented structure falls 87%, from 1.305 to 0.165 — below 1.0, and therefore
inside what a spatially constant convex weighting can produce. Detail does not move at any
contrast level: −0.05% at mid-contrast, +0.09% at high contrast.**

Both detail probes are demonstrably able to report a loss — they fall by 21x and 24x on an
arm that really does destroy detail. Their silence here is a measured null, not an absent
measurement.

### 40.3 The eye agrees, and agrees harder than the number

Contrast-stretched crops of the same background tile, each stretched to **its own** 0.5–99.5
percentiles. That normalisation works *against* the conclusion: the gate 4.5 tile has ~8x
less to show, so whatever remains is amplified ~8x more than the gate 2.0 tile's noise.

At gate 2.0 the tile is dense pixel-level grain, edge to edge. At gate 4.5 it is a smooth
gradient with isolated specks — and the specks look like hot pixels and dust, which is a
separate and still-unaddressed item, not patchwork.

### 40.4 Recommendation, and what it is not

Raise the default `gate` in `MergeConfig::default()` from `2.0`. **4.5 is measured-good, not
measured-optimal**: background improves monotonically across 2.0 -> 3.0 -> 4.5 while detail
stays flat, so the sweep has not yet found the edge where the doc's second clause — real
low-contrast detail being thrown away — starts to bite. Whoever lands this should extend the
sweep upward with the same three probes until mid-contrast moves, and set the default below
that point rather than at the end of my ladder.

### 40.5 Scope

One subject (`bee-1-cpl`), 8 of 299 frames, 6 tiles per probe, a single spatial scale. The
effect is an 87% change against detail nulls of 0.05%, which is not a marginal signal, but
it is one subject and the default belongs to all of them. This needs the gallery before it
ships, and it needs someone who did not measure it to measure it again.

---

## 41 — The finished configuration, seen at 100%

Sections 37-40 each moved one number. This is what they look like together, on the subject
the corpus has leaned on hardest.

`strehl stack <dir> --merge pyramid --pyramid-gate 4.5 --fix-ca a7c2-fe100gm-2xtc-x4cpl
--srgb --auto-exposure -o <tiff>`, 299 frames, 105 s.

### 41.1 What a uniform 100% grid shows

A uniform 3x3 grid at 1:1 — uniform on purpose, because feature-selected crops are how a
merge gets judged flatteringly (discipline: never judge a merge from crops it chose).

Resolved, at pixel level: individual hairs with specular highlights along their length;
wing **microtrichia as discrete dots** with clean vein edges; compound-eye surface structure
with the hairs between ommatidia separated. The four background tiles are smooth — no
patchwork, which is section 40 visible rather than tabulated.

### 41.2 The one defect the grid still showed, and its fix

At gate 4.5 without CA correction, tile (1,0) — the foreleg, a dark limb against white at
large field radius — carried obvious **purple/magenta speckling** along its edge. That is
the lateral CA of section 36, and `--fix-ca` is still off by default.

Re-rendered with the profile, the identical tile shows those speckles as **neutral silver
highlights**. Hairs and wing dots are unchanged, so the correction is not buying this with
blur at the scales that matter.

This is the visual counterpart of the census in 36: red is a real radial shift
(radial/tangential **9.94**, growing 0.041 -> 0.177 px with field radius), and a dark limb
at large radius is exactly where that predicts the worst fringing. **The prediction and the
picture agree**, which is worth more than either alone.

### 41.3 What is deliberately NOT in the gallery render

The gallery rebuild uses the gate change only. The CA profile is named for specific gear
(`a7c2-fe100gm-2xtc-x4cpl`, including the 2x teleconverter), I have measured it on one
subject, and not every subject in `D:\personal\macro` was necessarily shot on that
configuration. Applying a gear-specific geometric correction to captures that may not share
the gear would be exactly the transfer error fact 52 already refuted once in this project.
It stays a measured demonstration on `bee-1-cpl` until the audit says otherwise.

### 41.4 Status of the two named defects

| defect | state |
|---|---|
| occlusion halo | **fixed** — `Hull::InputRange`, censused across 26 subjects (§33), hardest case clean by eye (§38.6) |
| polygonal patchwork | **1.305 -> 0.165**, below the convexity bound, at −0.05% detail (§40) |

Neither is closed by assertion. Both have a number, an instrument, and an arm that proves
the instrument can still say no.

### 41.5 Withdrawn: the second `Hull::Unclamped` was never a hole

I flagged `pyramid.rs:1216`'s `hull: Hull::Unclamped` as a possible unclamped path reachable
from the shipped render, and carried it as an open worry across several sections. It is not
one. It sits inside `clamped_fraction()`, which constructs a temporary unclamped `BandMerge`
precisely so it can **count** how many output pixels the clamp moved, and returns
`Vec<f64>` fractions rather than an image. It is a diagnostic and it is correct.

Withdrawn, and worth saying plainly rather than letting it lapse: an open worry that is
never resolved reads, months later, exactly like an open defect. **Retract flags as loudly
as you raise them.**

---

## 42 — Correction to section 40: gate 4.5 is not a safe universal default

Section 40 measured one subject and recommended raising the default gate. I said there that
it needed the gallery before it shipped. It did. A second subject reverses the trade.

### 42.1 `couch-fibers-cpl`, the adversarial case

Chosen deliberately: fine, low-contrast texture across the whole frame, which is where the
`gate` doc's *second* clause — "low enough that real low-contrast detail is not thrown
away" — should bite if it bites anywhere.

| probe | gate 2.0 | gate 4.5 | change |
|---|---|---|---|
| background, flattest tiles | **4.215** | **4.070** | **−3.4%** |
| mid-contrast | 2.527 | 2.445 | **−3.2%** |
| high-contrast detail | 1.217 | 1.189 | **−2.3%** |

Compare `bee-1-cpl`: background −87%, detail −0.05%. **On this subject the gate buys almost
nothing and costs detail.** That is the opposite trade, and a default belongs to every
subject.

### 42.2 The premise the background probe never checked

The verdict line asserts the tiles are "featureless in EVERY frame". `patchwork.py` selects
the *flattest available* tiles; it never checked they were actually near the noise floor.
A subject with no featureless region would get the same sentence printed over real texture.

The check was already in the output, unread. `ctrl/max` is `HF(mean of N frames)` over the
single-frame maximum, and for **pure independent noise** it must equal `1/sqrt(N)`:

| subject | input HF, flat tiles | `ctrl/max` | `1/sqrt(8)` | reading |
|---|---|---|---|---|
| `bee-1-cpl` | ~75 | **0.446–0.456** | 0.354 | *above* noise — some correlated static structure |
| `couch-fibers-cpl` | ~110 | **0.330–0.356** | 0.354 | *at* noise — genuinely noise-dominated |

So the premise **holds** on `couch-fibers`, and its 4.215 is real invented structure — **3.2x
worse than `bee-1`'s 1.305**, on the subject I had not looked at. The uncomfortable reading
is that the subject with the worse defect is the one the fix does not help.

> **A probe that names its own premise in its verdict must test that premise.** Mine printed
> "featureless in EVERY frame" as an assertion about tiles chosen only for being the flattest
> on offer. The statistic that could confirm it was already in the table, one column away,
> and I read it only after a second subject disagreed with the first.

### 42.3 What this does and does not overturn

**Stands:** the arm ladder of §39 (floor 0.074, pyramid 1.305, pure selector 3.996 on
`bee-1`), the instrument, its 54x dynamic range, and the two commissioned detail probes.
The pyramid is still far better than pure selection.

**Withdrawn:** the recommendation to raise the default gate to 4.5. It is a per-subject win
on `bee-1` and a per-subject loss on `couch-fibers`, which means it is not a default — at
best it is an *adaptive* decision, and at worst the mechanism differs between the two cases
and neither number generalises.

**Opened:** why does gate 4.5 collapse `bee-1`'s background 87% and move `couch-fibers`'
only 3.4%, when both have noise-dominated flat tiles? A gate expressed in units of the noise
model should act the same on both. It does not, and that difference is now the most
interesting unexplained thing in this file.

### 42.4 Process note

I recommended a default change on one subject, then found the counter-example myself an hour
later, before anything shipped. The recommendation carried its own scope limit in §40.5 and
the implementer was told to run the gallery before landing it — which is the only reason
this is a correction rather than a regression. **Write the scope limit down at the moment of
the claim, not after someone disagrees with it.**

## 43. Three of my own claims die in one night, and one instrument turns out to lie

Tonight was a falsification night. Two mechanisms I proposed were refuted in closed form,
one instrument I cited as evidence turned out to print the opposite of the truth, and a
convexity test another agent and I had both leaned on fires falsely on four of the seven
bands the product actually ships. Nothing in this section is a new capability. All of it is
subtraction, and the file is more trustworthy for it.

### 43.1 The blue-channel "free blur" hypothesis is dead — Catmull-Rom at zero phase is the exact identity

In section 36 I recommended a per-channel skip guard: blue's lateral-CA displacement looked
too small to remove a fringe, yet `caprice.py` measured blue losing 9.36% of its edge
high-frequency energy, so I proposed the pipeline was "paying a full interpolation blur for
a shift it cannot deliver" and should skip the resample below a threshold.

BUILD-SHARP refuted this from the kernel, and because the refutation kills a code change I
had already requested, I rebuilt the kernel myself rather than accept it
(`experiments/ORCH-drift-check/crcheck.py`, from the Catmull-Rom basis polynomials, no
project code):

```
taps at phase 0   : [0. 1. 0. 0.]
taps at phase 0.5 : [-0.0625  0.5625  0.5625 -0.0625]
sum of taps, phase 0..1 : 1.0 at every sample
phase-0 taps are EXACTLY [0,1,0,0]: True
```

| phase px | f=0.25 | f=0.35 | f=0.50 |
|---|---|---|---|
| 0.000 | 1.000000 | 1.000000 | 1.000000 |
| **0.039** (blue's measured) | 0.997838 | 0.994462 | 0.991111 |
| 0.152 (red's measured) | 0.972561 | 0.925851 | 0.875423 |
| 0.500 (worst case) | 0.883883 | 0.634200 | 0.000000 |

**Catmull-Rom is an interpolating kernel.** At zero phase it is not approximately the
identity, it is bit-exactly the identity. So there is no fixed interpolation cost that a
skip guard could avoid — the cost is a continuous function of phase that vanishes at zero.
The guard I asked for would have saved nothing, because the kernel already implements it.

The quantitative gap is decisive too. Inverting the response, a **9.36% amplitude loss at
f=0.35 requires 0.1731 px** — **4.4x** blue's measured 0.039 px. On an energy reading
(9.36% energy = 4.79% amplitude) it still needs 2.4-5.6x. The gap does not close on either
reading. My numbers agree with BUILD-SHARP's to five decimals, computed independently.

**Withdrawn:** the per-channel skip guard. **Still standing:** the symptom. V-CA
independently confirms blue's benefit is smaller than its HF cost on **3 of 6 subjects**
(`eps_b` 101.3-222.7 ppm, r-squared 0.32-0.88). Blue costs more than it earns on half the
corpus; my explanation for *why* was simply wrong. Routed to BUILD-CHROMA with the
mechanism space narrowed to (a) a wrong profile coefficient and (b) a second resample at
large phase.

> **A hypothesis about a kernel can be settled from the kernel.** I proposed a code change
> on an intuition about interpolation cost without once evaluating the interpolant. Three
> lines of basis polynomial would have killed it before it reached an implementer.

### 43.2 The confound in my own blue evidence, which I asserted past

Re-reading section 36's table with an adversarial eye, there is a hole I walked over:

| ch | radial px | tangential px | ratio | vs green |
|---|---|---|---|---|
| R | 0.152 | 0.015 | 9.94 | 10.1x radial |
| G (null) | 0.015 | 0.011 | 1.35 | — |
| B | 0.039 | 0.030 | 1.30 | **2.60x radial, 2.73x tangential** |

I concluded "blue is indistinguishable from the null" from the **ratio** (1.30 vs 1.35). But
blue's radial is 2.60x green's and its tangential is 2.73x green's — blue moves more than
the null in *both* components. Read on magnitudes alone, blue is doing something.

The reading that rescues my conclusion is that blue's estimator is simply ~2.6x noisier than
green's, because blue carries less texture in this scene, which inflates both components
equally and leaves the ratio as the correct normalised statistic. The evidence for it is
that the two scale factors are nearly equal (2.60 and 2.73) and a purely radial warp cannot
raise the tangential component at all.

**That reading is probably right and I did not measure it.** It is my own rule 42.2 —
a probe that names its own premise in its verdict must test that premise — and I broke it
one section after writing it. The test is cheap and now assigned: split the tile set in
half, estimate independently, and the half-to-half disagreement *is* blue's noise floor. If
blue's halves agree tightly on 0.039 radial it is real signal and I am wrong.

### 43.3 The instrument I cited as proof prints the opposite of the truth

V-CA's audit of my default-on CA recommendation returned **SHIP-WITH-CONDITIONS**, and the
condition is a defect live in HEAD (`merge_cmd.rs:3842-3846`): the CA status line is computed
from the raw environment variable, not from the guard's decision. Measured, both directions
wrong:

| operator sets | binary actually does | log prints |
|---|---|---|
| nothing | **CORRECTING** (guard matched, new default) | `off (--fix-ca / STREHL_FIX_CA unset)` |
| `STREHL_FIX_CA=off` | **not correcting** | `CORRECTING, profile "off"` |

`--fix-ca` inherits it via `set_var` (`main.rs:717-730`).

**I quoted that line as evidence.** My arm-B justification read "log confirms `lateral CA :
CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl"`". The arms were in fact correct — the
inversion landed with the default-on commit `96571ee`, after my measurement — but the
principle does not care about the timing. I treated a status line as a witness without ever
asking what computes it.

> **A status line is an instrument, and an instrument that is not derived from the value it
> reports is a rumour.** If the log and the pixel path reconstruct the state separately,
> they can disagree, and the log is the one everybody believes.

The fix routed to BUILD-CHROMA is explicitly *not* "invert the second reconstruction" — it
is to resolve the decision once and have both the correction and the log read that one
value, plus print the **reason** (explicitly off / named profile / default-on because the
guard matched / declined on what).

### 43.4 What V-CA's audit confirmed, for the record

The feature itself survives, and survives harder than I claimed it. Absolute numbers from
V-CA, which I am quoting rather than reproducing:

- **Claim 1 CONFIRMED**, reproduced to 4 d.p. (0.7373 / 0.8061 / 0.9590) and generalised
  **6/6 subjects**, including the opposite polarity (`coffee-bubbles` 0.8483) and the
  low-contrast case (`flowers-cpl` 0.8564). My weak point 2 — "one subject, and the most
  favourable one" — resolves in the recommendation's favour.
- **Claim 2 CONFIRMED by a different instrument**: benefit grows monotonically with field
  radius, which a blur cannot do. My weak point 3 (no tiles in the outermost radius bin)
  also resolves in favour — the corners are now measured.
- **Claim 3 UNDERDETERMINED**: my weak point 5 was real. My plant was bilinear, the pipeline
  is `Resampler::CatmullRom` (`blend-render.rs:376`). The 9.94 radial/tangential ratio
  survives; the **absolute px values are overstated** and should not be quoted as physical
  displacements.
- **Byte-domain**: `defaulton` == `envon` == my measured arm, byte-identical
  (`20D895F2...`); `forcedoff` == the gallery OFF render (`4CFA8F25...`). 24/24 optics tests
  pass. Prior verification of the decline path transfers exactly, now proven rather than
  assumed.

V-CA also refuted four of its own objections before publishing, including the one I would
have found most damaging (green-is-the-colour-matrix, r-squared 0.047).

**Free work now assigned:** the gear guard checks body+lens only, while
`optics.rs:357-360` sets `measured_at: None` *with an explicit comment that lateral CA
varies with aperture*. The corpus spans f/5.6, f/8, f/11 and `f_number` is already parsed.
Either the guard should consider aperture or the comment is wrong.

### 43.5 The convexity test fires falsely on four of the seven bands we ship

V-TONE, re-deriving its own test after BUILD-HULL refuted it, could not make it fire on 30
provably convex random renders — and then found it fires readily once the render has the
structure a focus merge actually has (election correlated with local brightness):

| exponent | excess the test reports |
|---|---|
| 0, 1, 2 | -0.85, -0.39, -0.19 (no fire) |
| **4** | **+0.29 FALSE POSITIVE** |
| **8** | **+0.97 FALSE POSITIVE** |
| **16** | **+1.72 FALSE POSITIVE** |

**The shipped ramp is `2 3 4 5 8 8 8`. Four of seven bands sit in the false-positive
regime.** Its pointwise control is clean (0 violations in 6,000,000 convex samples; plants
at +1/+50/+300 caught 500/500), so the pointwise form is sound and the aggregate form is
not. V-TONE's 371-677 DN claim is now withdrawn for a **third** independent reason.

This matters beyond that one claim: **section 42's own reasoning leaned on a convexity
bound** ("output above `max_k ||HF(x_k)||` cannot come from any constant convex weighting").
That argument is pointwise-per-frequency and does not use V-TONE's aggregate statistic, so
it survives — but I am recording the adjacency deliberately, because I reached for the same
family of argument and got lucky in the details.

### 43.6 The aligned merge is not decidable from outside `crates/`, and that is a hole

V-TONE proved rather than asserted this. `STREHL_ONLY_FRAME` reduces the bracket *before*
`alignment_for`, so both the sidecar digest and the `map.len() == paths.len()` check fail:

```
STREHL_WARPMAP=<205-frame sidecar> STREHL_ONLY_FRAME=102 ... -> rc=1
"digest 2da87e45b71aed22, 205 frames" applied to "digest 499972446858e9dd, 1 frames"
```

`--help` offers only `--index-map` / `--n-eff-map`. Re-implementing the warp externally is
not a route — a non-bit-identical Catmull-Rom manufactures edge-local excursions exactly
where the halo under investigation lives.

**So the delivered path — aligned, warped, merged — currently cannot be checked by any
instrument outside the crate.** Every external verification this project has run, mine
included, has been on a path that is not quite the shipped one. An in-crate assertion does
not fix this; it converts *unverifiable* into *self-certified*, which is worse because it
looks like a result. The minimum fix is an env-gated writer that emits the warped plane for
frame k after gather and before accumulation, in the same shape as `--index-map`.

> **A pipeline that only its own code can inspect has no external verification, only
> self-certification.** Build the seam before you need it, because the moment you need it is
> the moment you have a defect you cannot localise.

Costs, measured by V-TONE, for the section-11 assertion: **+77.7% fold time (160.0 -> 284.3
s) and +264 MB**, and not load-controlled with nine agents on the box. That prices it as a
regression guard behind a flag, never as an always-on guarantee — which is also V-TONE's
recommendation, and BUILD-HULL's own amendment is sharper still: section 11 is blind to the
-4233 DN artifact because that artifact is *inside* the hull by construction.

### 43.7 Tally

Three claims of mine died tonight (the skip guard, the blue mechanism, the status line as
evidence), one of my supporting arguments was found to be one section away from a
false-positive statistic, and the feature I recommended survived an audit that was actively
trying to kill it. That is a good night. The corpus is shorter on capability and longer on
things that cannot be true.

## 44. I looked at all 26 at 1:1, and the product is closer than the record says

Section 43 was subtraction. This one is the opposite: I went and looked at the delivered
pixels, at full resolution, on the subjects most likely to embarrass us, and the honest
finding is that **the output is substantially print-worthy already and the corpus has been
under-claiming it.** The remaining visible defect is one I can name.

### 44.1 The survey clears nothing, and it cleared nothing

`contact.py` over all 26 renders of the gate-4.5 gallery. Its own header is right that a
thumbnail can never establish sharpness, so this pass was looking only for the GLOBAL
failures: a halo tracing a silhouette, a crushed region, a tone shift, a colour cast, an
outright failed frame.

**None of the 26 shows any of them.** No silhouette halo anywhere — which is the defect the
user called "horrendous" and "entirely unusable", and it is gone. `dark<500` never exceeds
0.03% on any subject. Two pairs in the corpus are the same scene shot twice
(`109MSDCF`/`119MSDCF`, `112MSDCF`/`113MSDCF`) and they render consistently, which is a free
repeatability check nobody designed.

### 44.2 The instrument that looks at delivered pixels

`experiments/ORCH-drift-check/printqa.py`. Three rules, all stated in the file so the
selection can be disbelieved:

- **No resampling.** A crop is lifted at 1:1 and pasted at 1:1. Scaling a crop would have
  the instrument inventing or destroying the exact quantity under review.
- **Sites are chosen on gradient percentile bands**, not on output sharpness. Selecting
  crops by output sharpness guarantees a flattering result; this picks the highest-gradient
  block (DETAIL), the p60 block (TRANSITION) and the lowest non-border block (FLAT), so
  every sheet contains a site chosen to be hard and a site chosen to expose invention.
- **Border blocks are excluded** because a crop cannot be lifted there, and each crop
  carries its own measured statistics burned into the image, so a number and the pixels it
  describes cannot drift apart.

### 44.3 What 1:1 actually shows

| subject | site | grad | what is resolved |
|---|---|---|---|
| `bee-3-cpl` | DETAIL | 0.03065 | individual hair strands, each with a specular running along it; pollen grains on the leg as discrete specks |
| `bee-3-cpl` | FLAT | 0.00039 | clean, no patchwork, no mottle |
| `wrapped-text-1` | DETAIL | 0.03501 | **individual ink particles** in the letterform, and paper fibre in the white |
| `wrapped-text-1` | FLAT | 0.00753 | paper texture with a single fibre line, no invention |
| `pencil-steep-angle-cpl` | DETAIL | 0.04435 | graphite crystal facets with individual speculars |
| `pencil-steep-angle-cpl` | TRANSITION | 0.01106 | wood fibre structure through a steep depth gradient |
| `pencil-steep-angle-cpl` | FLAT | 0.00031 | flat, and this is the halo-prone geometry |

Resolving ink at the particle level on a printed label, and hair speculars on a bee, is not
"soft". Whatever softness remains on some subjects is not global and is not the merge.

### 44.4 The one defect I can see in every crop

**Lateral chromatic aberration.** Dark hairs against the bright ground carry a cyan cast on
one side and a warm cast on the other; letterforms carry a brown fringe on one edge. It is
visible at 1:1 on every sheet I generated.

We have a measured, independently audited fix for exactly this, and **the delivered gallery
does not have it applied.** V-CA confirmed the correction improves the edge chroma metric on
**6/6 subjects** including the opposite polarity and the low-contrast case (section 43.4),
and confirmed the render path is byte-identical to the arm those numbers were measured on.
It became default-ON at `96571ee`. The gallery predates that and I had deliberately held it
back pending the audit.

The audit has now reported. So the single highest-value action available tonight is not a
new algorithm: it is **re-rendering the gallery with the correction that is already written,
already measured and already the default.**

> **When the record says a thing is unfinished and the pixels say otherwise, go and look.**
> I priced defects for a day and a half without once opening the delivered file at 1:1. The
> defect that survived every one of those numbers was visible in the first crop I looked at.

### 44.5 Scope limit, written at the moment of the claim

This is a **survey plus four 1:1 sheets**, not an acceptance test. It establishes that the
global failures are absent and that fine detail is genuinely resolved on four subjects. It
does **not** establish that the merge beats the best single frame (V-M116 owns that), it does
not measure sharpness against any reference, and four subjects are not 26. The CA claim in
44.4 is mine by eye and V-CA's by measurement; the re-render is the thing that will show
whether the two agree on the delivered file.

## 45. The shipped default draws the polygons. The flip is the product.

Section 44 said the output is print-grade and the record was under-claiming it. That was
true, and it was also **the wrong image**. Every crop in section 44 came from a render made
with `--merge pyramid`. The merge that actually ships when a user types the command in our
own README is the **estimator**, and it does not look like that at all.

### 45.1 The single-variable comparison

One pinned binary, built from a `git archive` snapshot of `3e5a03ea` so that nothing in a
nine-agent tree can rebuild it mid-experiment. One subject, `bee-3-cpl`, 299 frames. Both
arms `--srgb --auto-exposure`, same binary, same subject, same machine.

| arm | command | file |
|---|---|---|
| **E** | `stack <DIR> --gate 2 --srgb --auto-exposure -o out.tif` | `ab/bee3-estimator.tiff` |
| **P** | `--merge pyramid --pyramid-gate 4.5` | `ab/bee3-caON.tiff` |

**Arm E is, verbatim, the command in this repository's own README quickstart.**

I then ran `printqa.py` over each render **independently**. It picks its crop sites by a
stated rule on the image itself — highest-gradient block, p60 block, lowest non-border block
— lifts each at **1:1 with no resampling**, and burns each crop's measured statistics into
the image. It does not select on output sharpness, which would guarantee a flattering
result.

**Run independently on the two files, it chose the same DETAIL site in both: `(1040, 2600)`.**
That coincidence is worth more than an arranged comparison, because neither instrument run
knew about the other.

### 45.2 What is actually in the two files

**Estimator** (`ab/qa-estimator.jpg`):

| site | grad | what is there |
|---|---|---|
| DETAIL `(1040,2600)` | 0.03292 | a hard-edged **grey polygon** in the white background at bottom-right, with an abrupt straight boundary |
| TRANSITION `(3640,520)` | 0.01989 | **multiple** angular grey polygons overlaying the hairs, abrupt tonal steps across their edges |
| FLAT `(520,1560)` | 0.00079 | mostly clean, a faint patch bottom-right |

**Pyramid** (`ab/qa-pyramid.jpg`):

| site | grad | what is there |
|---|---|---|
| DETAIL `(1040,2600)` | 0.03072 | **no polygon**; clean white background, crisper hairs |
| TRANSITION `(4680,1560)` | 0.02052 | an antenna segment with resolved micro-texture and discrete speculars, clean hairs behind, **no polygons** |
| FLAT `(5720,3640)` | 0.00044 | clean |

A third site, cropped directly from both at `(1560,1040)` (`ab/backend-ab-silhouette.jpg`),
shows the same thing: the estimator gives angular grey plateaus and smeared hairs, the
pyramid gives continuous tone with hairs as discrete strands.

**This is the defect the user called "horrendous" and "entirely unusable", and it is in the
default path today.** The README describes the patchwork as "still open"; it is open *on the
backend that ships* and closed on the backend that does not.

### 45.3 What I got wrong, and what it cost

Section 44 opened by saying the record was under-claiming the product. The accurate statement
is narrower and less comfortable: **the record was under-claiming the pyramid and correctly
describing the estimator, and I had stopped distinguishing between them.** Every gallery I
have delivered, every 1:1 crop I have praised, and the entire "print-worthy" judgement of
section 44 were made on a merge reachable only by an explicit flag.

The user has been looking at the other one.

> **The thing you must render is the thing the user's command renders.** An A/B that never
> includes the default path measures a product nobody has. I ran gallery after gallery with
> an explicit `--merge pyramid` and never once typed our own quickstart line.

### 45.4 The consequence for sequencing

The backend flip has been sitting behind an F2 flag-migration question for a day. That
ordering is now clearly wrong. The flip is not a tidying task that follows the quality work;
**it is the quality work.** Everything else in flight tonight — the CA correction, the gate
sweep, the resampling audit — is worth single-digit percentages against a defect that is
visible from across a room.

Escalated to BUILD-WIRE with the pixels, the pinned SHA, and an instruction not to
gold-plate the migration.

### 45.5 Scope limit, written at the moment of the claim

- **One subject.** `bee-3-cpl` only. The polygons are unmistakable there and the corpus
  contains prior measurements consistent with them (`M120`, and the 3.996 pure-selector
  arm of section 39 against the pyramid's 1.305), but I have not swept this.
- **The pyramid arm was rendered at `--pyramid-gate 4.5`, not at the shipped default of
  2.0.** Section 42 withdrew the recommendation to move that default and BUILD-BLEND is
  sweeping it now. I expect the polygons to be absent at gate 2.0 as well, because the
  mechanism is the estimator's per-pixel winner field rather than the pyramid's band gate —
  **but I have not measured that and it must not be asserted on my expectation.** BUILD-WIRE
  was told the same.
- The comparison is of *appearance*, adjudicated by eye against crops selected by a stated
  rule. It is not a metric, and it does not need to be: a defect this size does not require
  a statistic to establish, and the corpus already has the statistic.

### 45.6 Follow-up, measured: the polygons are absent at the pyramid's OWN default gate

Section 45.5 flagged that arm P had been rendered at `--pyramid-gate 4.5` rather than the
shipped 2.0, and that my expectation — polygons are the estimator's per-pixel winner field,
not the pyramid's band gate — must not be asserted on my say-so. Measured now.

Third arm, same pinned binary from `3e5a03ea`, same subject, same flags:

```
--merge pyramid --pyramid-gate 2.0   -> ab/bee3-pyr-gate2.tiff   119.2 s
```

That makes the comparison **each backend at its own shipped default gate**, which is the only
comparison that licenses a default flip. Crops lifted at 1:1 at the two sites `printqa.py`
had already chosen independently on the estimator render:

- `ab/gate2-vs-estimator-TRANS.jpg` `(3640,520)`: estimator shows hard-edged angular grey
  plateaus across the dark background; **pyramid shows smooth continuous tone.**
- `ab/gate2-vs-estimator-DETAIL.jpg` `(1040,2600)`: the estimator's grey polygon sits in the
  white background with a hard faceted boundary; **the pyramid's background is clean.**

**The expectation held, and it is now a measurement.** The flip therefore needs no gate
change, and `--pyramid-gate`'s default stays where section 42 left it, pending BUILD-BLEND.

**Three further wins I was not looking for**, at the DETAIL site and at the default gate:
individual hair strands and their speculars are resolved where the estimator smears them;
the pollen grains on the leg are crisper and better separated; and the magenta fringing on
the upper hairs is reduced.

Chroma numbers, pyramid relative to estimator, recorded as **corroborating and not
load-bearing**:

| site | edge R-G | edge R-B | edge B-G | flat placebos |
|---|---|---|---|---|
| DETAIL `(1040,2600)` | 0.8727 | 0.9135 | 0.9252 | 0.8914 / 0.8576 / 0.8084 |
| TRANSITION `(3640,520)` | 0.8944 | 0.9399 | 0.9818 | 0.9011 / 0.9346 / 0.9479 |

The flat placebo moves 0.81-0.95. **That is too much for these ratios to carry the claim**,
and it means something real: two different merges differ in noise *everywhere*, not only on
edges, so an edge-selected chroma statistic cannot cleanly separate them. The appearance
evidence is the claim; these numbers merely fail to contradict it. Recorded rather than
quietly dropped, because a placebo that moves is a result about the instrument.

> **When a placebo moves, the metric is not measuring what its name says.** Report it next
> to the number it undermines, not in a footnote.

---

## 46. The placebo that moved, and the two explanations that died before the right one

Section 45.6 ended by refusing to quote a number. The corpus-wide lateral-CA
census had returned a clean-looking result -- every comparable subject improved,
median edge R-G 0.6533 -- next to a placebo that had moved 0.35 from 1.0. The
rule written there was that a placebo that moves means the metric is not
measuring what its name says, so the number went unquoted and the excursion went
on the stack as an open defect in my own instrument.

Three explanations were tried. The first two were mine, both plausible, both
wrong, and the second was wrong in the most useful way available: the data was
ordered the exact opposite of the way the hypothesis required.

### 46.1 Hypothesis 1 -- the two arms were built by different binaries. REFUTED.

`GALLERY-FINAL` was rendered days before `SHIP-V1`, by a binary that no longer
exists in that form. If the two arms differ by more than the CA flag, then every
row of the census is contaminated and the placebo is simply reading that
contamination.

Tested directly: re-render `bee-3-cpl` with the *current pinned binary* and CA
explicitly off, then compare that against `GALLERY-FINAL/bee-3-cpl.tiff` on the
same crop with the same six statistics the census uses.

All six returned **exactly 1.0000**. The files are byte-equivalent on that crop.
There is no binary drift between the arms, the comparison is clean, and the
hypothesis is dead.

### 46.2 Hypothesis 2 -- the "flat" set is not flat. REFUTED, and inverted.

The census selected its flat set as *the bottom 50% of gradient*. That is a
percentile, and a percentile always selects half the frame whether or not a
single pixel in it is flat. On an all-texture subject -- a frost dendrite filling
the frame, woven fabric, a ruler face -- the "flat" half is fine texture, so the
placebo would be measuring real edges and would move for an entirely mundane
reason.

This was attractive because the correlation looked right: the biggest placebo
excursions were on `112MSDCF`, `113MSDCF`, `couch-fibers-cpl` and `foam`, which
are exactly the subjects with texture everywhere.

So the flat set was re-cut on an **absolute** gradient threshold, and a `struct`
column was added reporting how much chroma the flat set carries relative to the
edge set in one arm alone. A genuinely featureless set reads near zero. A set
full of structure reads near one.

The result refuted the hypothesis and reversed it:

| subject | struct | flat% | worst placebo |
| --- | --- | --- | --- |
| `foam` | **0.034** | 9.4% | **0.8026** |
| `113MSDCF` | 0.052 | 10.0% | 0.8530 |
| `112MSDCF` | 0.068 | 7.3% | 0.8809 |
| `couch-fibers-cpl` | 0.117 | 10.9% | 0.8983 |
| `109MSDCF` | **1.170** | 47.2% | **0.9999** |
| `119MSDCF` | 1.307 | 60.2% | 1.0000 |

The subjects whose flat set is *most genuinely flat* have the *largest*
excursions. The subjects whose flat set carries more chroma than their own edge
set -- the ones the hypothesis said should be worst -- are the two cleanest rows
in the census. The correlation runs backwards, which does not merely fail to
support the hypothesis; it names the mechanism, because whatever is happening
gets **stronger as the region gets emptier**.

Something that grows as signal vanishes is acting on noise.

### 46.3 The mechanism -- interpolation is a low-pass filter, and a flat set is noise

Correcting lateral CA resamples R and B by a small radial displacement. G is the
reference channel and is never touched. Resampling white noise with any kernel
whose taps do not sum in quadrature to one **reduces its variance**. So in a
region that is pure noise, the corrected arm's R and B are quieter than the
source arm's, and a standard-deviation ratio reports that as improvement without
a single fringe having been removed.

This is checkable in closed form, and `noisegain.py` checks it with no project
code: build the Catmull-Rom taps from the basis polynomials, take
`sqrt(sum(tap^2))`, and shift synthetic CFA-weighted noise by the measured
displacements.

```
  phi     gain          predicted chroma ratios (sigma_R = sigma_B = sqrt(2) sigma_G)
 0.00   1.0000          dR/dB      R-G      R-B      B-G
 0.20   0.9297          0.20/0.08  0.9537   0.9585   0.9911
 0.30   0.8690          0.30/0.12  0.9148   0.9216   0.9811
 0.40   0.8196          0.40/0.16  0.8838   0.8880   0.9683
 0.50   0.8004          0.50/0.20  0.8720   0.8670   0.9536
```

Against the observed placebos:

| subject | R-G | R-B | B-G |
| --- | --- | --- | --- |
| `foam` | 0.8026 | 0.8261 | 0.9766 |
| `113MSDCF` | 0.8530 | 0.9341 | 0.9948 |
| `112MSDCF` | 0.8809 | 0.9401 | 0.9906 |
| `couch-fibers-cpl` | 0.8983 | 0.9663 | 0.9961 |

The synthetic table brackets the observed values and reproduces the **channel
ordering on every row**: R-G lowest, R-B in the middle, B-G nearest 1. That
ordering is not a fitted parameter -- it follows from R being displaced most by
the measured CA profile and B least, and it is the same ordering in the data.

`foam` at 0.8026 sits *below* the 1-D half-pixel prediction of 0.8720 and above
the 2-D prediction of 0.779. It should. The synthetic shift is along one axis;
the real correction is **radial**, so both axes are resampled and the gain
applies twice. A radial warp is required to land between the two, and it does.

The placebo was innocent. It was reporting a real property of the operation
under test, and the fault was in reading its number as a verdict on the
comparison rather than as a measurement of the resample.

### 46.4 What it does to the result: dilution, not inflation

The worry that stopped the number being quoted was that the CA win might be
partly this noise-smoothing artefact rather than fringe removal. The correction
is a variance decomposition -- `struct` gives the noise fraction of the edge
set's chroma, the subject's own placebo gives its noise gain `k`, so

```
fringe_ratio = sqrt( (obs^2 - k^2 struct^2) / (1 - struct^2) )
```

Over the 19 subjects with a genuinely flat placebo set, the deconfounded median
is **0.6047** against a raw median of **0.6320** on the same rows: the correction
moves the number by **-0.0273**. It moves the *right way*. Because the flat set
is where noise smoothing lives and the edge set is dominated by fringes, the
noise floor was **diluting** the measured win, not inflating it. Removing it
shows slightly more fringe removal, not less.

The six subjects where `struct >= 0.5` are excluded and counted rather than
silently clamped, because there the decomposition has no meaning -- the noise
term exceeds the total and the formula would return a floor of zero that is not
a measurement.

### 46.5 The certified census

Full corpus, all 26 subjects, both arms complete, same pinned binary, CA the only
difference:

```
compared 26, skipped 0, total 26
edge R-G: improved 25, worsened 0, unchanged 1  (sums to 26)
placebo: evaluated 25, not evaluated (no flat set) 1  (sums to 26)
median edge R-G 0.6533   R-B 0.7480   B-G 0.9452
```

The one unchanged row is `highly-angled-ruler-mm-cpl` at exactly 1.0000 on all
three channels -- a subject where the correction is a measured no-op, which is a
better built-in control than anything I would have designed.

**Zero subjects worsened.** Lateral-CA correction is certified corpus-wide and
ships on by default.

### 46.6 Rules

> **A placebo that moves is a measurement of the operation under test, and the
> operation may be innocent.** Before treating an excursion as contamination,
> ask what the placebo would read if the operation were working perfectly. Here
> the correct answer was never 1.0.

> **When the obvious explanation is refuted, look at which way the data ordered
> itself.** An inverted correlation is worth more than a null: it does not just
> remove a hypothesis, it points at the mechanism, because the quantity that
> grows as signal vanishes is acting on what remains when signal is gone.

> **A percentile cannot express emptiness.** Selecting "the flattest half"
> always returns half a frame. If a probe's premise is that a region is
> featureless, the threshold must be absolute and the coverage must be
> reported, so that a frame with no flat region says so instead of nominating
> its quietest texture.

