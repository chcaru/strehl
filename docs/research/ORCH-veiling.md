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


