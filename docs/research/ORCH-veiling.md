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
