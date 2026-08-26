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
