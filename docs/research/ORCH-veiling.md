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


---

## 47. Does the patchwork generalise? Two subjects say yes, one says no, and the no matters

Section 45 proved the polygonal patchwork is the estimator backend rather than
the noise gate. It proved it on **one** subject, by eye, and §45 recorded that
limitation as an explicit uncertainty rather than rounding it up to a general
claim. This is the attempt to close it.

### 47.1 The instrument, and the confound it had to kill

Polygons are *structure in a region that should be smooth*. A defocused
background is smooth by construction -- every input frame is out of focus there,
so any fine structure in the output was manufactured by the merge. So restrict
to blocks whose gradient **on the arm mean** is in the bottom percentile band,
which means neither arm chooses its own ground, and compare the two arms on the
same rectangles.

Run that way, `coffee-bean` returns estimator/pyramid high-pass ratios of
**4.167** on the worst background block and **2.904** across 21 random ones.

That looks conclusive and it is not, because of a confound sitting in the
comparison: the estimator arm renders at `--gate 2` and the pyramid arm at
`--pyramid-gate 4.5`, so the estimator averages fewer frames. **Noise is
high-pass energy too.** A uniform 2.9x excess is exactly what less averaging
produces, and it would say nothing whatever about polygons.

### 47.2 The discriminator: noise dies under averaging, facets do not

Box-average the block by a factor `f` before measuring. White noise falls as
`1/f`. A hard-edged facet boundary tens of pixels across survives essentially
intact. So the ratio's **scale dependence** separates the two explanations
without needing a matched-gate render:

* if the excess is noise, the ratio stays **flat** while both columns fall;
* if the excess is structure, the ratio **grows** with `f`.

`coffee-bean`:

| factor | estimator | pyramid | ratio |
| --- | --- | --- | --- |
| 1 | 0.000814 | 0.000353 | 2.304 |
| 2 | 0.001105 | 0.000301 | 3.674 |
| 4 | 0.001466 | 0.000431 | 3.399 |
| 8 | 0.002330 | 0.000626 | 3.722 |
| 16 | 0.003782 | 0.000902 | **4.194** |

The ratio nearly doubles from 2.304 to 4.194 under 16x averaging. The excess is
**structure that survives averaging**, and the noise explanation is refuted on
this subject. The 1:1 crop agrees: soft mottled blotches across a white sweep in
the estimator arm, a clean field in the pyramid arm at the same rectangle.

**`coffee-bean` is the second subject.** The claim is no longer a single
observation.

### 47.3 The subject that says no

`lavendar-cpl`, same instrument, same procedure:

| factor | estimator | pyramid | ratio |
| --- | --- | --- | --- |
| 1 | 0.001102 | 0.000704 | 1.565 |
| 2 | 0.001378 | 0.000596 | 2.311 |
| 4 | 0.001826 | 0.000869 | 2.103 |
| 8 | 0.002917 | 0.001546 | 1.887 |
| 16 | 0.004530 | 0.002850 | **1.589** |

The ratio rises and then **returns to its starting value**. Under the rule
written above, that is not a facet signature. Most of `lavendar-cpl`'s excess is
noise, and the small mid-scale bump is not enough to call it patchwork.

`flower-bud-alone-cpl` produced **no qualifying blocks at all** -- its background
carries enough sweep gradient that no 520 px block sits far enough below the
threshold. It is counted as not-measured, not as a pass.

### 47.4 What is actually established

**The honest scope: the patchwork is real, it is the estimator, and it is
subject-dependent rather than universal.** It appears where there is a large,
genuinely smooth, deeply defocused background -- `bee-3-cpl` by eye,
`coffee-bean` by a discriminator that survives its own confound -- and it does
not clearly appear on a texture-dominated subject whose background is a near
field grey sweep.

The decision does not depend on which way that split falls, because of the one
result that is uniform across every row of every table above: **the pyramid arm
carries less background structure than the estimator arm at every scale on every
subject measured, and is never worse on this statistic.** A backend that is
sometimes much better and never worse is the one to ship, and the argument for
the flip does not need the defect to be universal.

### 47.5 Rules

> **When two arms differ by more than the variable under test, find a statistic
> whose SCALE DEPENDENCE separates the explanations, rather than re-rendering to
> match.** The confound here was extra noise from a different gate; averaging
> discriminates noise from structure directly, and costs one pass instead of a
> second gallery.

> **A generalisation attempt that returns one yes and one no has succeeded.** It
> replaced a claim believed universal with a claim that is true in a stated
> region, which is a better object than the one it started with. The failure to
> reproduce is the most valuable row in the section and is reported as such.


---

## 48. RETRACTED -- see section 53. The softness had a cause, it was in the path nobody measured, and it is recoverable

BUILD-SHARP was re-tasked into its own lane -- price the resampling chain by
*phase*, not by count -- after its Catmull-Rom refutation killed my skip-guard
request in section 43. It returned the largest quality finding the project has
produced.

### 48.1 The finding

The audit enumerated every resampling site from ARW decode to final TIFF and
partitioned them: **8 sites -> 2 PRICED / 4 NOT-ON-THIS-PATH / 2 NOT-A-RESAMPLE
/ 0 COULD-NOT-INSTRUMENT, summing to 8.**

The alignment gather's phase, measured on a real warpmap rather than assumed --
40,700 samples across 20 frames -- is **near-uniform**: mean distance-to-integer
0.2369, p99 0.4942, **57.3% of samples further than 0.2 from an integer**. That
kills the comfortable assumption that alignment shifts are small enough to be
free.

Composed retained amplitude in the **viewable** render:

| f | green | red/blue |
| ---: | ---: | ---: |
| 0.25 | 0.890 | 0.784 |
| **0.35** | **0.691** | **0.471** |
| 0.50 | 0.421 | 0.199 |

**At f=0.35 the render the photographer looks at keeps 69% of green and 47% of
red and blue.** The single largest contributor at 0.25 and 0.35 is a fixed
`phi=0.25` chroma co-site applied on **both axes**, **serially after** the
alignment gather, at `image_out.rs:956-957`.

### 48.2 The part that is a lesson rather than a bug

Co-siting runs only inside `write_binned` -- the **viewable** path. Every ESF
sharpness number this project has taken was measured on `linear.tif`, which
never passes through it.

> **An instrument aimed at the measurement path can be blind to everything that
> happens on the delivery path.** The project measured sharpness for weeks on a
> file the photographer never sees, and the largest single amplitude loss in the
> pipeline sat in the difference between the two. Whenever a tool has a
> "measurement output" and a "viewable output", the defect budget must be
> computed for **both**, or the honest linear file becomes an alibi for the one
> that ships.

This is the same failure class as section 45, where the shipped default backend
drew the patchwork while every quality measurement was taken on the other one.
Twice in one night, the thing being measured was not the thing being delivered.

### 48.3 The fix, and checking it before it ships

`gather_checked` (`warpmap.rs:441`) is per-plane and takes a `Similarity`. A
constant translation composes exactly, so the co-site can be folded into the R
and B gather transforms and the serial `resample_shift` deleted: same samples,
same kernel, one resample instead of two. It commutes with the merge because it
is an identical shift on every frame, so it passes through a weighted mean and
an argmax alike.

BUILD-SHARP predicted **1.128 / 1.438 / 2.004x** amplitude recovery on R/B at
f = 0.25 / 0.35 / 0.50, i.e. **+20.6 points at f=0.35**.

A code change was about to ship on that number, so it was re-derived
independently from the basis polynomials, importing no project code
(`experiments/ORCH-drift-check/cositecheck.py`):

| f | independent | BUILD-SHARP | delta |
| ---: | ---: | ---: | ---: |
| 0.25 | 1.1346 | 1.128 | +0.6% |
| 0.35 | **1.4677** | **1.438** | +2.1% |
| 0.50 | 2.1157 | 2.004 | +5.6% |

with `taps(0)` exactly `[0,1,0,0]`, taps summing to `1.000000000000` at
`phi=0.25`, and amplitude exactly 1.0 at `phi=0`. **Two independent derivations
agree within 2.1% at the bands that matter**, so the prediction is sound as
arithmetic and the residual risk is entirely in the implementation.

The control that decides whether the fix pays: folding a constant offset into
the gather's own phase distribution must be cheap. On a synthetic near-uniform
phase it costs **-0.03% / -0.10% / -0.07%** -- free, because a uniform
distribution is invariant under a constant offset. BUILD-SHARP measured
0.6 / 2.0 / 5.3% on the real distribution, which is not perfectly uniform; that
is the more conservative figure and it is the one to quote.

### 48.4 What was routed, and the three ways it can still go wrong

Implementation went to a fresh agent, not to the author of the analysis. The
risks named to it, none of which are about the arithmetic:

1. **Sign.** Backwards, and R and B shift the wrong way -- which presents as
   lateral chromatic aberration, on a build where lateral-CA correction is now
   default-on and certified. A sign error would be easy to misattribute to CA
   and hard to unpick.
2. **Planes.** R and B only, G untouched. The bit-identical-G hash is the
   placebo, and it has to be *run*, not argued.
3. **Replacement, not addition.** If the fold sits alongside the serial call
   instead of replacing it, the output gets a full extra 0.25 shift. The
   positive control catches it: R/B would get *softer*, not sharper.

And the measurement itself has a trap already stepped on once: the A/B must be
measured on the **viewable sRGB render**, because that is the only path the
co-site is on. Measured on the linear path the fix will appear to do nothing.

### 48.5 Rule

> **Check a prediction from first principles before code ships on it, and check
> the enabling condition separately from the effect.** Here the effect
> (1.438x) and the condition (folding is free) are different claims with
> different failure modes, and only the second one determines whether the fix
> pays for itself.


---

## 49. Three instances of one error in a single night: measuring across a path boundary

Section 48 recorded that the project's ESF sharpness instrument had been
measuring `linear.tif`, a file the chroma co-site never touches and the
photographer never sees. That looked like an incident. By the end of the night
it had happened three times, in three different lanes, to three different
agents including me, and it is better understood as a **class**.

### 49.1 The three instances

| # | the instrument measured | the product delivered | consequence |
| --- | --- | --- | --- |
| 1 (§45) | the **pyramid** backend, in every quality claim | the **estimator** backend, by compiled default | the shipped default drew the polygonal patchwork while every measurement said the merge was clean |
| 2 (§48) | `linear.tif`, the measurement output | the **viewable** sRGB render | the largest single amplitude loss in the pipeline sat entirely in the gap between them, unpriced for weeks |
| 3 (§49.3) | an **unwarped** rawpy decode as the single-frame reference | the **warped** merge output | *under investigation* -- if confirmed, a per-tile survey reported the merge losing on detail tiles as a mechanical consequence of its own construction |

Each was invisible from inside its own lane. Each was found only by someone
holding two lanes at once.

### 49.2 The rule

> **An instrument and the product must be on the same side of every
> transformation between them.** Whenever a pipeline has a "measurement output"
> and a "delivery output", or a reference arm and a test arm that are produced
> by different paths, the defect budget must be computed for the delivered
> artefact, not the convenient one. The honest linear file is otherwise an alibi
> for the one that ships.

The corollary is what makes it operational, because the error is not detectable
by looking at either arm:

> **Name the path boundary explicitly when designing any A/B.** For each arm,
> write down every transformation it has undergone. If the two lists differ by
> anything other than the variable under test, the difference is in the result
> whether or not anyone intended to measure it.

### 49.3 The third instance, and why it was worth chasing

V-bestframe built a per-tile "never worse than the best single frame"
instrument, deliberately decoding the ARWs with `rawpy` so that it shares no
code with the thing it audits. That instruction was mine and I still think it
was right: an instrument that shares code with its subject cannot find a fault
in the shared code.

But an independent decode of an ARW yields the **unwarped original**, while the
merge output has been through the alignment gather. BUILD-SHARP, holding the
amplitude numbers, asked the question the survey could not ask itself: is the
reference arm warped or not? If unwarped, the single frame pays **zero**
resamples while the merge pays the full chain -- a **1.43x handicap on green**
at f=0.35 and **2.14x on R/B** -- and such a survey reports the merge losing on
textured tiles *even if the merge is perfect*.

The predictions of that hypothesis match the observed table uncomfortably well:
the deficit concentrates in **detail** tiles, which is exactly where resampling
loss bites and where flat tiles are untouched; and the subjects richest in fine
detail rank worst (`109MSDCF`, 246/352 detail tiles, 4.5% pass).

There is a sharp lesson in the headline subject. `flowers-cpl` has only
**48/352** detail tiles and scores 83.3%, mid-pack. Under the original H1
reading that was evidence of capture limitation. Under the handicap hypothesis
it is *also* exactly what would be produced. **The subject the instrument was
built to adjudicate cannot discriminate between the two explanations of the
instrument's own output.**

What survives regardless: H1 for `flowers-cpl` rests on the merge-**independent**
column -- how many detail tiles exist in the *frames* -- which never involves the
merge and is untouched by this objection. A verdict resting on the arm that the
confound cannot reach is a verdict that survives the confound.

### 49.4 What §21 settled, which narrowed the target to one thing

BUILD-SHARP priced the two arms that had fired since §20:

- **Lateral-CA correction is structurally free, not merely cheap.**
  `OpticalProfile::compose` (`optics.rs:297`) returns **one** `Similarity` doing
  alignment and CA together, handed straight to `gather_checked` per CFA plane.
  A radial magnification about a point *is* a similarity, and similarities
  compose. Residual cost **-0.41% / -1.52% / -4.48%**. The counterfactual is the
  number worth keeping: as a separate pass, red would have paid a **14.3% loss
  at f=0.35** -- avoided, not paid.
- **The pyramid backend costs exactly nothing.** Round-trip error **4.441e-16**,
  per-band retention **1.000000** at all three bands. `[1,4,6,4,1]/16` is a
  severe low-pass, but it sits inside a **perfect-reconstruction** filter bank,
  so the blur `expand` adds is exactly the blur subtracted to form the
  Laplacian. **Pricing the kernel alone would have produced a large fictitious
  number** -- a reminder that a filter's cost is a property of the system it
  sits in, not of the filter. Potency shown rather than asserted: scaling the
  finest band by 0.80 returns 0.800000 / 0.800350 / 0.800128, MOVED 3/3.

So the shipped chain is **G 0.698, R/B 0.468 at f=0.35**, and the serial chroma
co-site is **the only removable loss and the whole of it**.

BUILD-SHARP also corrected its own §20 arithmetic in the **conservative**
direction -- it had used `a z + b` where `apply_at` is centre-relative, worth
**+0.29 / +1.04 / +3.17%** -- meaning the original report slightly *overstated*
the loss it had found. A correction that makes your own headline smaller is the
kind that can be trusted.

### 49.5 A latent collision, caught before it landed

The profile `A7C2_FE100GM_2XTC_X4CPL` carries `translation: (0.6294, -0.4240)`
px, which its own documentation calls unattributed and describes as *"the same
order as the ~0.5 px/axis that CFA co-siting predicts"* -- plausibly the very
quantity the co-site fix folds in.

**No collision today:** `resolve_for_capture` returns the `_RADIAL` twin, whose
translation is exactly `(0, 0)`. But wiring the non-radial profile would
silently double-correct by roughly half a pixel per axis on R and B, presenting
as lateral chromatic aberration on a build where CA correction is default-on --
misattributable, and exactly the kind of defect that ships. Routed to the
implementer as an assertion to add rather than an assumption to hold, and the
two files sit in different lanes, which is why it needed a third party to see it
at all.

> **A quantity that appears in two places will eventually be applied twice.**
> The defence is not vigilance but an assertion at the point of use, because the
> collision only becomes reachable under a configuration change made by someone
> who never read either site.


---

## 50. The harness was lying, and the refutation was mis-priced

BUILD-CHROMA was sent to fix a status line. It came back with a worse defect
than the one it was sent for, a refutation of my own refutation, and an
independent arrival at another agent's number from the opposite direction.

### 50.1 The defect was not where the report said, and the real site was worse

The brief said the inverted lateral-CA status line was at
`merge_cmd.rs:3842-3846`. It was -- and it had **already been fixed** by a
different lane at `3a22fd2`. The identical defect was still live verbatim in
**`blend-render.rs:296-302`**, which matters far more, because **`blend-render`
is the project's A/B harness**. Measured stdout at `e718c46`:

```
ARM 1 (unset):             lateral CA : off (STREHL_FIX_CA unset)
ARM 2 (STREHL_FIX_CA=off): lateral CA : CORRECTING, profile "off"
```

Both rows inverted. Byte-proved rather than read: `br_unset` == `br_unset2` ==
`13C89646...` (same-arm determinism control, since `blend-render`'s `--chunks`
was unavailable), `br_off` == `3DBAED99...`. **The arm labelled `off` is the one
that moved the pixels.**

The fix is the structural one rather than a second inversion:
`profile_for_capture` became a *projection of* `resolve_for_capture`, so the
reported profile and the applied profile are one value rather than two that
agree. Three tests where there had been zero, commissioned by planting both
inversion directions, 2/2 caught.

> **When a defect is reported at a location, fix the *class* across the
> codebase, not the coordinate.** The reported site had already been repaired by
> someone else; had the implementer trusted the coordinate it was handed, it
> would have found nothing wrong and closed the item -- while the copy in the
> harness kept lying.

An unresolved consequence, routed to an independent verifier: **any A/B run
through `blend-render` and labelled from its log has its arms swapped.** That
includes, potentially, my own corpus-wide CA census in §46. I am not able to
clear my own instrument here, so I have not.

### 50.2 My refutation of the blue hypothesis was itself wrong

In §44 I killed my own skip-guard proposal by showing that blue's 0.039 px
displacement costs 0.22-0.89% amplitude, and that reproducing the measured 9.36%
loss would need 0.1731 px -- **4.4x** the displacement. I called the gap
unclosable on either an energy or an amplitude reading.

The arithmetic was right and the model was wrong. **The correction does not
apply a single displacement.** It applies `eps_b * r`: zero on the optical axis,
**0.368 px at the corner**. The 0.1199 px required to lose 9.36% *energy* is not
4.4x anything -- it is **0.33 of the corner value**, squarely inside the field.
I had priced a radially varying field at one number and then treated the
mismatch as a refutation.

> **Before declaring a mechanism too small to explain an effect, check whether
> the mechanism is a field rather than a scalar.** A spatially varying quantity
> evaluated at one point will usually look too small, and the error is invisible
> because the arithmetic is correct.

The conclusion I drew from the bad refutation nevertheless survives, for a
different reason. Split-half analysis (400 splits, green null on **identical**
tiles) put blue's fitted `eps_b` at **7.2-37.0 of its own error bars from zero**
on all six stacks, one consistent sign, against the null's 1.3-6.2. Blue's
coefficient is real signal. **No coefficient change and no skip guard** -- the
9.36% is not a defect but the price of a correction that the census says is
worth paying.

Note also what happened to the confound I raised in §44 and could not settle:
blue's radial and tangential components co-scale at ~2.6x green's, which I said
was either a real signal or blue simply being noisier. It resolved **in my
favour on the mechanism** -- the co-scaling is indeed blue having less texture --
**and against me on the conclusion**, because that is per-tile scatter while
`eps` is fitted from the systematic radial term. Being right about the mechanism
and wrong about what it implied is the ordinary case, not the unusual one.

### 50.3 Two agents, two directions, one number

BUILD-SHARP derived the shipped chain's retained amplitude at f=0.35 as **G
0.69, R/B 0.47** by auditing the resample chain and measuring the alignment
phase distribution. BUILD-CHROMA, working on the blue channel from the CA side
and without using that result, measured the co-site's cost to blue as a factor
**0.6813**. Composed against BUILD-SHARP's green figure: 0.69 x 0.6813 =
**0.470**.

Whether that is genuine convergence or two derivations sharing an assumption is
exactly the question to ask of it, and I have put it to the verifier rather than
banking it. But both agents independently identified `image_out.rs:956` -- the
serial chroma co-site -- as the dominant loss, from opposite ends of the
pipeline. That is the second independent arrival at §48's finding.

### 50.4 Two corrections to the corpus, both found by cross-checking before use

- **`restore.rs:573` records its constants at f = 0.40, not f = 0.35.** Found
  because a reproduction matched exactly at 0.25 and 0.50 and mismatched in the
  middle -- a **mislabelled abscissa**, not a wrong value. A cross-check that
  agrees at the ends and disagrees in the middle is describing the x-axis, not
  the y.
- **The amplitude-loss table is an upper bound, not a number.** Lateral-CA
  correction composes into the alignment gather, so its true cost is
  `MTF(phi+s) - MTF(phi)`, which on a uniform phase distribution is *identically
  zero*. Independently the same conclusion as BUILD-SHARP §21 reached from the
  code structure. Quoting the table's entries as costs paid would overstate
  them.

### 50.5 Aperture: the corpus cannot answer, and says so

The gear guard ignores aperture while `optics.rs:357-360` sets `measured_at:
None` with a comment noting that lateral CA varies with aperture. I asked for a
measurement. The corpus **does not span aperture as I assumed** -- 5x f/5.6,
1x f/8, **no f/11**. Measured `eps_r`: 651.9 ppm at f/5.6 against 650.7 ppm at
f/8, a **0.2% difference across a full stop**, versus a **151 ppm** spread
*within* f/5.6.

The right call was made: record the limitation in the code rather than gate on
it, because gating would disable a working correction for a difference smaller
than the within-group scatter. But n=1 at f/8 has no scatter of its own, and
that qualification belongs next to the number.

### 50.6 Two capture requests, and one guard that has never fired

Logged to `docs/captures-needed.md`:

1. **A bracket shot without the teleconverter.** The gear guard's decline path
   has **never once run against a real file** -- every stack in the corpus
   matches. A branch that has only ever been exercised by its own unit test is
   not known to work.
2. **An f/11 bracket**, to give the aperture question a second point.

> **A conditional that has never taken its other branch on real data is
> untested, however many unit tests cover it.** The corpus is not just a sample
> of subjects; it is a sample of *configurations*, and it is currently constant
> in the variables the guard reads.


---

## 51. The flip orphaned a lane, and only a byte comparison found it

Section 49 called measuring across a path boundary a *class* and listed three
instances. The fourth arrived within the hour, and it is the most expensive one
yet: **28 hours of correctly executed measurement, on the arm that stopped being
the product halfway through.**

### 51.1 What happened

`DEFAULT_MERGE_BACKEND` flipped from `Estimator` to `Pyramid` at `5142ace`.
BUILD-HALO had by then spent 28 hours on the occlusion halo -- the owner's
single loudest complaint, and the reason all research was stopped -- building the
adaptive election radius, the silhouette veto, the noise-driven acuity shrink,
and an attribution methodology good enough to isolate a single term
bit-exactly.

**All of it is inside `run_estimator`. None of it is reachable from
`run_pyramid`.**

```
merge_cmd.rs L2521  pub fn run   -> match backend { Pyramid => run_pyramid, Estimator => run_estimator }
              L2528  run_estimator   spans L2528..L4027   <- the acuity block sits at L2806
              L4028  run_pyramid     spans L4028..L4336
```

Searching the whole body of `run_pyramid` for
`acuity|SelectionScale|edgeaware|tighten_by` returns **zero matches**.

### 51.2 The structural argument is the weaker half

The reading above is an inference from source. The measurement is not. I built a
clean binary at HEAD `a4bd795` -- which contains BUILD-HALO's `6430fb2` and
`ce59c31` -- and rendered `coffee-bean` on the shipped configuration, then
compared it to the gallery render produced by the pinned binary at `3e5a03ea`:

| arm | binary | SHA-256 (20) | bytes |
| --- | --- | --- | --- |
| SHIP-V1 | `3e5a03ea`, 9,339,392 B | `C085A0569B9584EC96A3` | 197,798,531 |
| HEAD | `a4bd795`, 9,343,488 B | `C085A0569B9584EC96A3` | 197,798,531 |

**Byte-identical.** Two binaries differing by 4,096 bytes and 1.4 hours of
commits produce the same 197,798,531 bytes. An acuity term that BUILD-RENDER
priced at **-6.6% gradient RMS across 26 subjects** when it was deleted moved
**nothing** on the path that ships.

> **A byte comparison across a version gap answers a question no code reading
> can: not "is this code called?" but "did anything I did reach the product?"**
> It costs one render and one hash, and it is the cheapest orphan detector
> available. Every long-running lane should be made to produce one.

### 51.3 The system had already said so, in a voice nobody was listening to

BUILD-HALO's own byte-freeze rows pass `--merge estimator` and `--photometric
off` **explicitly**. Its attribution script omitted them on the first attempt
and **the tool refused the flag combination outright**. Its note records that
refusal as *"the only reason the omission did not silently produce a confident
wrong attribution."*

That refusal was the defaults moving out from under the frozen rows, announcing
itself. It was read as a near-miss in one script rather than as news about the
product. The signal was correct, arrived on time, and was scoped too narrowly by
its reader -- including by me.

> **When a tool refuses a flag combination that used to work, the news is not
> about your invocation. It is that a default moved.** Ask what else was
> standing on it.

### 51.4 What this does and does not cost

It does not invalidate the work. The estimator path still exists and is still
selectable, and the attribution methodology -- isolating a term with
`STREHL_ACUITY` and requiring **both** arms, because *"off reproduces the old
bytes"* alone would also be satisfied by a build that ignored the flag and moved
nothing -- is the best attribution standard this project has produced. It is now
pointed at the path that ships.

What it does cost is the answer to the owner's actual question. **Nobody has
measured whether the pyramid backend halos at all.** Every halo instrument here
was built against the estimator's winner field, and the pyramid backend has no
winner field; it gates band-wise. Two possibilities, both live:

- pyramid is structurally immune, the flip already answered the complaint, and
  the lane closes with a proof; or
- pyramid halos differently, invisibly to instruments looking for a winner-field
  signature, and **the flip needs re-arguing** -- because `5142ace` was justified
  on the polygonal patchwork, a decision taken *before* the acuity term was
  restored, and a decision made before its counterparty improved may not survive
  it.

Routed to BUILD-HALO with the requirement that a negative result carry a potency
check: an instrument that reports "no halo" without having been shown to detect
one is reporting nothing.

### 51.5 The orchestration lesson, which is mine

Four instances of one class in a single night, and the pattern in *how they were
found* is sharper than the pattern in the failures. None was found by the agent
that owned the lane. Each was found by someone holding two lanes at once and
noticing they disagreed. Section 48 came from an agent auditing a chain rather
than a component; section 50 came from an implementer handed a coordinate who
checked the class instead; this one came from a hash I took for an unrelated
reason.

> **A lane cannot see its own boundary.** The orchestrator's distinctive job is
> not to review work inside lanes -- the lanes are better at that -- but to keep
> asking, of every lane, *is this still attached to the product?* Flipping a
> default is not a local edit. It re-parents every lane downstream of it, and
> the agents inside those lanes will not notice, because from inside a lane
> everything still passes.


---

## 52. What the default path does not do, in its own words

Section 51 established that the flip re-parented BUILD-HALO's lane. Following
that thread one step further produced the more consequential finding, and it did
not need an instrument -- **the binary says it out loud.**

`run_pyramid` prints, on every run:

```
not applied     : photometric gain, clip census, outlier rejection, halo correction,
                  through-focus statistics. Those are the --merge estimator path's
                  stages; this arm is the merge only.
```

So flipping the default did not merely change a merge kernel. It traded the
estimator's polygonal patchwork -- a real defect, measured and reproduced on two
subjects in section 45 and section 47 -- for the loss of **five stages**.

### 52.1 Verified by refusal, not by reading

The banner is a claim like any other, so I tested it on a clean build of
`a4bd795`:

```
$ strehl stack <DIR> --photometric on --srgb -o out.tiff
rc=1
Error: --photometric belongs to the estimator merge, and --merge selected pyramid.
  what to do  : NOT YET IMPLEMENTED on this backend, rather than inapplicable. The
                per-frame affine gain would apply unchanged, but fitting it needs
                every frame's flux before the first frame is folded, which the
                pyramid's single-pass fold does not currently do.
  or          : pass --merge estimator to use --photometric as it stands.
Refused rather than ignored because a flag that silently does nothing looks
exactly like one that works.
```

That last line is the right engineering and deserves recording as a standard.

> **A flag that silently does nothing looks exactly like one that works.** Refuse
> the combination at the boundary, name the counterpart, and distinguish *not
> implemented here* from *inapplicable here* -- they lead a reader to opposite
> conclusions about whether to wait for it.

The error also states the real obstacle precisely: the affine gain *would apply
unchanged*, but fitting it needs every frame's flux **before the first frame is
folded**, which a single-pass fold does not do. That is the architectural seam
the project's own review flagged long ago -- decode is 0.91 s warm, so a second
pass is cheap and preserves O(workers) memory. **The obstacle is the pass
structure, not the estimator.**

### 52.2 Why this matters for the claim being made

Two of the five missing stages are named in this project's own review as things
*"SOTA dies without"*: per-frame **photometric normalisation**, without which the
gate misreads exposure drift as signal; and an **outlier/robustness mask**,
without which one twitching antenna poisons the merge with no defence. The
corpus contains exactly the captures that need them -- a stack that moved, a
stack with bubble motion, and a same-subject pair a full stop apart in exposure.

Against that, the honest counter-evidence: the 26-subject gallery was rendered on
this path, inspected at 1:1 on six subjects, and is clean. On *this* corpus, at
*these* subjects, the missing stages have not visibly cost anything. Both facts
are true and the tension between them is the actual state of the product.

> **A default is a claim about the common case, and swapping one changes which
> defects a user meets by accident.** The estimator's patchwork was visible and
> is gone; the pyramid's gaps are invisible and arrive only on captures that
> happen to contain motion or drift. Trading a loud defect for a quiet one is
> usually right, and is never free -- and the quiet one has to be written down
> where the user will read it, or the trade was not made honestly.

Disclosed in the README rather than left in a startup banner nobody keeps.

### 52.3 Deliberately not fixed tonight

Four agents already share `merge_cmd.rs`. Adding a fifth to port these stages
into `run_pyramid` -- concurrently with the lane being redirected into the same
function -- is how work gets silently clobbered in a shared tree, which this
project has already been bitten by twice. The port is real, wanted, and next;
it is not a thing to start while the file is this busy.


---

## 53. RETRACTION: section 48's central claim was backwards

Section 48 was the largest quality finding I recorded. It is wrong, in the one
way that mattered, and the correction inverts the conclusion rather than
softening it.

**What section 48 claimed:** a fixed phi=0.25 chroma co-site runs serially on the
**viewable** render at `image_out.rs`, costing R/B a factor of ~1.44 at f=0.35;
it lives only inside `write_binned`, so every ESF number the project took on
`linear.tif` **excluded** it; removing it was the largest available sharpness
win.

**What is true:** `write_binned` is not the viewable path. Both callers reach it
only *after* an `if demosaic { ... return }`, and `--srgb` demosaics. **The
co-site never executes on the render the owner is looking at.**

### 53.1 Verified by me, directly, before accepting the contradiction

Two agents disagreed, so I checked the crux myself rather than believing the
newer report:

- **The shipped artefact.** `SHIP-V1\bee-3-cpl.tiff` reads as `(4688, 7032, 3)`,
  `uint16` -- full sensor resolution, three channels. A binned render would be
  half that and is not three-channel by this route.
- **The render's own log**, from the gallery command re-run verbatim:
  `wrote : ... (7032 x 4688, 16-bit RGB, sRGB ... , Malvar-He-Cutler demosaic)`.
- **The branch.** In `merge_cmd.rs` the demosaic arm calls `write_demosaiced` and
  then `return Ok(())`, *above* the `write_binned` call at L5835.

Three independent confirmations, one of them an artefact I had already inspected
at 1:1 and certified as print-grade. **The evidence that refuted section 48 was
sitting in a file I had personally verified weeks earlier.** I had checked that
the gallery was 7032x4688; I never asked what that implied about which writer
produced it.

### 53.2 The instrument bias is real, and points the other way

Section 48's *rule* survives intact and is if anything better supported: an
instrument and the product must be on the same side of every transformation.
What flips is who was on which side.

`write_binned` -- and therefore the co-site -- is on the `--linear-srgb`
**measurement** path. So ESF numbers taken there **carry** a co-site the shipped
render does not. The measurement understates R/B relative to the product, rather
than the product silently paying a cost the measurement missed. Same defect,
opposite sign, and the sign is the whole engineering consequence.

### 53.3 The fix would have damaged the product

This is the part that justifies the implementer's decision not to land, and it
is the reason to be glad the work was measured rather than executed.

Folding the shift into the gather changes what Malvar sees, because Malvar
treats co-sited samples as if they were still at their CFA corners. Measured on
the demosaiced pair: **sd(R-G) x1.235, sd(B-G) x1.230, HF(R-G) x1.313, HF(B-G)
x1.317** -- all worse. And the effect is not a rigid shift the demosaic could
absorb: the implementer's shift estimator reads **0.02 px**, and it is potent
there (a planted 0.5 px recovered at 1.06x, a planted 1.0 px at 1.000x), because
Malvar rebuilds R at three of four sites from the green gradient.

The kernel arithmetic was never in doubt and still is not: the measured fold
reproduced the closed form to **within 1.8% at f=0.35** (1.4325x R, 1.3925x B
against 1.438 predicted), with green **bit-identical** (`50aebee0c023dae6` both
arms, `np.array_equal` True over the whole plane). A correct implementation of
the wrong change, priced exactly, and then declined.

> **"Composing is exact" is a property of an operator, not of its consumers.**
> The gather's transform does compose. Three different writers consume it, and
> one of them *wants* the co-site. A change can be mathematically free and still
> wrong, because correctness lives at the boundary, not in the kernel.

> **An implementer asked to land a fix, who measures first and returns "the fix
> is real, reproduces to 1.8%, and must not ship", has done the job.** Compliance
> would have shipped a measured regression with a green test suite behind it.

### 53.4 What was actually found, which is bigger

**The demosaic is the largest unpriced term on the viewable path**, and no
instrument in this project has ever looked at it.

The merge estimates all four CFA sites per quad independently -- R, both greens,
B -- and then **throws that structure away**, re-interleaving into a Bayer mosaic
so that Malvar can reconstruct what was just estimated. Malvar was designed for a
single noisy exposure; here it is handed merged estimates from tens of frames,
with entirely different noise characteristics, and its cross-channel
assumptions were never re-examined for that input.

Whether a direct upsample of four known planes beats Malvar interpolating them
is genuinely open -- green is sampled at quincunx density and Malvar's gradient
term does add real R/B detail under the slowly-varying-chroma assumption -- but
it has never been measured, and it sits directly on the delivered pixels.

Section 48's partition had bucketed the demosaic as NOT-ON-THIS-PATH, on the
reasoning that a quad collapse never demosaics. Correct about a quad collapse.
The shipped render is not one.

### 53.5 What I got wrong, mechanically

I trusted a module-header comment. `image_out.rs` described `write_binned` as
*"the 'for looking at' render"*, which is false; the implementer has replaced it
with a measured reachability rule. Section 48's audit read the sentence and
propagated it into a headline, and I amplified it -- into a corpus section, into
a task brief for the implementer, into a warning to a second verifier, and into
a status report to the owner.

> **A comment is a claim by an author who is not present, about code that has
> changed since.** Reachability is a property of the call graph and the flags,
> and it is cheap to establish from the artefact: read the shape of the file the
> product actually wrote.

The corollary for how I work: I had the refuting evidence and did not query it.
The gallery's `7032x4688` was in my own notes as a *quality* fact -- full sensor
resolution, good -- and never as a *routing* fact. **A number recorded under one
heading does not get consulted when the question arrives under another.**

## 54. The sharpness module has no callers, and the complaint is softness

The project measured that its own alignment gather costs **1.43x in amplitude at
f=0.35**, confirmed that arithmetic against a real fold to **1.8%**, wrote a
noise-aware module to correct it, and **never connected the module to the
product**. The owner's verdict on the shipped gallery is that it looks bad, and
the quality he is describing is softness.

### 54.1 How I know it has no callers

`crates/strehl-core/src/restore.rs` is 33,461 bytes and exports a complete,
self-testing surface: `gather_mtf`, `RestoreConfig::gain(f, signal_power)`,
`gain_2d`, `RestoreReport`, `autocorrelation`, `design_fir`, `restore_plane`,
`selftest`. `strehl-core/src/lib.rs:29` declares `pub mod restore;`, so it
compiles, raises no dead-code warning, and appears alive to anyone reading the
module list.

I checked reachability rather than inferring it, because section 53 had just
cost the project a headline for exactly that mistake:

- `restore|deconv|unsharp|sharpen|mtf` across `merge_cmd.rs` matches only
  `sharpen_per_octave` at L4178 and L4272, plus a comment at L5103.
- Case-insensitive `restore` across all of `crates/strehl-cli/src/` returns
  **four** hits: `image_out.rs:1512`, `image_out.rs:1554`, `merge_cmd/dump.rs:103`,
  `align_cmd.rs:530`. **I read all four. Every one is the English word
  "restores" inside a comment.** There is no `strehl_core::restore` reference
  anywhere in the CLI crate.
- The only real consumer in the repository is
  `crates/strehl-core/examples/restore-plane.rs` -- an **example** binary, on no
  product path.

A count of four looked at first glance like the module was wired. Reading the
four lines is what turned a plausible yes into a certain no. **A grep count is
not a reachability result; the matched lines are.**

### 54.2 This is a third distinct failure mode, not a repeat

The project has now logged three ways for work to fail to reach the product, and
they need different defences:

| section | failure | signature |
| --- | --- | --- |
| 49, 51 | instrument and product on opposite sides of a transformation | measurements that do not predict the render |
| 52 | a stage exists on the path but is skipped by this backend | the tool prints `not applied: ...` |
| **54** | **code compiles, is complete, is never called** | **nothing at all -- it is invisible** |

The third is the worst of the three, because the other two announce themselves.
A byte comparison across a version gap catches the first. The tool's own banner
catches the second. **Nothing catches the third**, which is why it survived a
research programme that has otherwise been unusually careful, and survived at
least two audits aimed near it.

### 54.3 The rule

> **A module that compiles is not a module that runs. For every finding the
> project claims to have applied, name the call site.** Not the module, not the
> function -- the line on the product path that invokes it, established from the
> call graph and confirmed against the shipped artefact.

The corollary is that "is it wired?" must be asked of *findings*, not of code.
Code review looks at what is there. This defect is entirely about what is
*absent*, and absence has no diff to review.

### 54.4 I had looked at the pixels, and still had not looked at the picture

Section 53.1 records that I inspected `bee-3-cpl.tiff` at 1:1 and certified it.
That is true, and it did not help, because I was answering a **resolution**
question -- is this 7032x4688 and three-channel -- and never asked *is this
good*. Tonight I opened the contact sheet and the 1:1 print-QA sheets to judge
them as photographs for the first time. `lavendar-cpl` renders its hairs as
low-microcontrast mush; `flowers-cpl`, `wrapped-text-2` and
`highly-angled-ruler-mm-cpl` are visibly soft **at one-eighth scale**, which is
severe.

This is the same shape as section 53's closing lesson -- a number recorded under
one heading is not consulted when the question arrives under another -- and it
generalises past numbers to images. **Looking at an image to measure it is not
the same act as looking at it to judge it, and the first does not discharge the
second.** An implementer in another lane reported the identical failure twice in
one night, in its own words: *"I did not look at it as a picture."*

### 54.5 What the gallery actually is, settled from the driver

Worth pinning, because it was assumed twice and is load-bearing for how the
owner's complaint should be read. `C:\dev\strehl-out\ORCH-SHIP\render_ship.ps1`
invokes:

    stack <subject> --merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure -o <out>

So the gallery the owner called horrible **is the pyramid path** -- the same
path another lane has just measured as having **no interior ring at all**
(monotonic from d=1 to d=275 px on `flower-bud`, against 12.65% on the estimator
arm). The bright ring is therefore **not** what he is reacting to. That
reframing is the practical value of this section: the loudest remaining defect
is softness, and there was an unwired sharpness module sitting next to it.

### 54.6 Disposition

Wiring is with the module's author; **independent verification of the module
itself is with a separate agent, dispatched in the same minute**, because the
author has never had an independent reader and I am not willing to put an
unverified restoration on a default path. The two run in parallel and I have
told the author not to land a default-on change until the verifier reports, and
to bring me any disagreement rather than settling it between themselves.

The guard that matters is pre-registered: **a Wiener FIR overshoots at edges,
and an overshoot at a silhouette is a halo.** The current pyramid profile is
monotonic to 275 px. If restoration puts a local maximum back into it, it is not
shippable at that strength regardless of how good its MTF numbers look, and what
I want back is the trade curve rather than a single operating point.
## 55. A night of corrections, and one of them is a habit rather than a fact

Four of my own records were corrected tonight by agents I had sent to check
them. Three are simple errata. The fourth is a reasoning error I want named,
because I will otherwise make it again.

### 55.1 The CA census is correctly signed -- confirmed, not merely assumed

The open worry was that section 46's "25 improved, 0 worsened, 1 no-op" might
have been labelled from the status line that was later found to be lying, in
which case the whole gallery would carry the correction **backwards**.

**It does not.** `GALLERY-FINAL` is CA **off**, `SHIP-V1` is CA **on**, and the
verdict stands. Proven three independent ways: the published numbers match in
direction; the radial physics is right (edge R-G rises **4.2x** from centre to
corner in the off arm and is flat in the on arm, which is what lateral CA does
and what a mislabelled pair could not fake); and a ground-truth control using
`--fix-ca off` against a named profile matches to 3-4 significant figures at
every radius. `cacensus.py` parses **no log line at all**, so the lying status
line could not have reached it, and section 46's arms came from `strehl stack`
rather than from the harness that carried the defect.

Worth recording that the verifier's own first run reported "0/3 plants caught",
which it then traced to `--exact` selecting **zero tests** -- `0 passed` reading
as success. **A vacuous green inside the instrument built to detect vacuous
greens.** It caught it because it checked how many tests ran, not just whether
any failed.

### 55.2 The aperture census I recorded was wrong, and wrong in the direction that costs the owner a shoot

I recorded **5x f/5.6, 1x f/8, no f/11**. A full EXIF census of the corpus finds
**20x f/5.6, 3x f/8, 3x f/11** -- and the f/11 material exists in
`109MSDCF`, `112MSDCF` and `113MSDCF`. My count was right for the six stacks I
happened to look at and wrong as a statement about the corpus, which is what I
wrote it as.

The consequence was nearly a wasted session for the owner: I had priced the f/11
point as a capture request. `docs/captures-needed.md` had **already** self-
corrected this in its own errata -- *"no aperture variation in the corpus" should
have read "none among the CPL stacks"* -- and section 7's aperture-pair request
survives the correction intact, because it asks for something genuinely absent:
a **paired** shoot at matched depth and density. M35 measured that both existing
candidates fail the self-reference gate (`119MSDCF` 2.18x, `112MSDCF` 2.10x,
against `coffee-bean`'s 3.62x), so the request is about **density**, not about
apertures the corpus lacks. **The request was right for a reason I had stated
wrongly.**

### 55.3 A units error that strengthened the argument it was found in

Section 50 priced a chroma residual at **0.1199 px**. The figure is
**0.1731 px**: `caprice.py` returns `1.4826 x MAD`, an *amplitude*, and the
corpus text at line 3782 says "HF amplitude" -- I converted as though it were a
variance-like quantity. The corrected number sits **further** inside the
radially-varying field it needed to fit within, so the conclusion is better
supported than when I wrote it.

### 55.4 The habit: I called a definition a convergence

This is the one that matters beyond tonight.

Section 50 reported, as independent corroboration, that one agent's green figure
of 0.69 times another's 0.6813 gives **0.470**, matching a third measurement of
R/B at 0.47. I presented the agreement of two lanes as evidence the number was
right.

**It is not evidence of anything.** Both quantities derive from the *same
kernel* evaluated at the *same frequency*. "R/B equals green times the co-site
factor" is how those terms are defined; the arithmetic could not have come out
any other way, and no possible measurement could have made it come out
differently. A prediction that cannot fail is not a test, and two lanes agreeing
because they share an input are not two lanes.

> **Before citing an agreement as corroboration, ask what result would have
> counted as disagreement.** If no measurement could have produced one, the
> agreement is a restatement of a definition and carries no evidential weight.

The reason this is a habit and not a slip: an unfalsifiable agreement *feels*
exactly like a strong one, and it arrives with the emotional signature of
independent confirmation -- which is precisely when a claim stops being
examined. I logged it under the same heading as genuine cross-lane convergence,
and nothing in my own record distinguished the two.

### 55.5 One capability confirmed live, by artefact rather than by argument

Against the run of the night, a positive result. The `Hull::InputRange` clamp is
**genuinely applied on the delivered gallery.** Counting exact-zero RGB pixels
in the shipped masters -- a quantity that survives any monotone tone curve and
so needs no cross-path comparison:

| subject | zero RGB px | `lum<500` | unclamped expectation |
| --- | ---: | ---: | --- |
| `flower-bud-alone-cpl` | **0** | 0.009% | 122,416 px / 0.371%, `lum<500` 1.310% |
| `dry-erase-marker-head-cpl` | **0** | 0.000% | 1.048% |
| `bee-3-cpl` | 0 | 0.003% | -- |
| `coffee-bean` | 0 | 0.000% | -- |

I checked this specifically **because** section 54 had just found a documented,
tested, defaulted-looking capability that does not run. `Hull::InputRange` has
the same profile -- an excellent doc comment, a passing potency control, and the
word "default" -- and after `restore.rs` that profile no longer constitutes
evidence. It happens to be true here, and now it is true *measured on the
artefact* rather than inferred from an enum.

**Instrument note:** the cheapness of this test is the point. Exact zero is
preserved by every monotone tone curve, so it is one of the very few quantities
that can be read straight off a `--srgb` master without violating the rule
against measuring across a tone curve. When a defect has a signature that
survives the transformations between instrument and product, the path boundary
stops mattering -- **look for such signatures first.**

### 55.6 An open packaging question

The masters are not all the same size. `flower-bud-alone-cpl` and
`dry-erase-marker-head-cpl` are `(4688, 7040, 3)`; `bee-3-cpl` and `coffee-bean`
are `(4688, 7032, 3)` -- same height, 8 px apart in width. Presumably a
per-subject crop falling out of the alignment solve. Not a quality defect, but a
gallery whose members have different pixel dimensions is a wart for anyone
printing a set, and if the variation tracks alignment drift it is a free
diagnostic. Routed to triage rather than answered here.


## 56. A flat subject is a within-image control, and it says the dark side is blurred

Three things landed in the same hour and they belong together, because the first
is a measurement I could not have got any other way, the second is the third
instance tonight of the same structural failure, and the third is a hole in a
rule I wrote myself and have been enforcing on everyone else.

### 56.1 The ruler

I have been treating "the output is soft" as one fact about the tool. It is not
one fact. Looking at 1:1 print-QA crops across the delivered `SHIP-V1` masters,
the pattern is specific and it is not global:

**Bright textured regions are excellent. Dark and low-contrast regions are
blurred. In the same image, at the same depth, tens of pixels apart.**

The subject that shows it is `flat-on-ruler-cpl`, and it shows it because the
subject is **flat**. A flat subject is the degenerate case for a focus stacker:
a ruler lying in the focal plane has no depth to resolve, every pixel wants the
same one or two in-focus frames, and the merge has no hard decision to make
anywhere. Whatever softness appears there is the pipeline, not the focus
decision. In one 700 px crop:

| site, same crop | gradient | appearance at 1:1 |
| --- | --- | --- |
| brushed-metal grain | **0.05282** | razor sharp; individual brush striations, discrete specular sparkles |
| black engraved mark, ~50 px away | -- | **blurred**; edge fades over ~10-15 px, boundary mottled |

For scale, 0.05282 is *higher* than `bee-3-cpl`'s best site at 0.03072, and
`bee-3-cpl` is the subject I judged print-worthy. So the metal here is as good
as anything the tool has produced, and the mark 50 px away is not.

Corroborating in the same direction, from the same pass: `pencil-steep-angle-cpl`
renders beautifully -- individual wood fibres, crystalline structure in the wood,
a clean graphite/wood boundary, gradient 0.02860. Against that, `flowers-cpl` is
mush at its own sharpest site (0.00939, 3.3x less than `bee-3-cpl`) and
`lavendar-cpl`'s hairs read as low-microcontrast white spaghetti.

**Why this observation is worth more than the several dozen numbers above it.**
It is a *within-image* control. The sharp metal and the blurred mark share the
same subject, the same plane, the same frame set, the same merge invocation, the
same tone treatment, the same alignment solve, the same binary, and they are 50
px apart. Nearly every confound that has produced a retraction in this document
-- two binaries, two black points, one arm toned and one linear, a scene
difference standing in for a treatment difference -- is excluded **by
construction** rather than by care. I have spent this night discovering that my
instruments were measuring across boundaries they should not have crossed. A
within-image control cannot cross one.

> **When a defect can be sited twice inside a single frame, once where it appears
> and once where it does not, prefer that comparison to any comparison between
> two renders. The confounds are excluded by construction rather than by
> discipline, and discipline is what has failed here repeatedly.**

**The mechanism I suspect, tagged ARGUED and handed to the gate lane to kill.**
Where the focus measure has poor signal-to-noise, the noise gate widens and
admits more frames into the average. On a *flat* subject shot as a focus
bracket, most frames are out of focus -- only one or two are sharp. So a gate
that opens wide in a low-SNR region is not averaging redundant in-focus frames
and winning noise; it is averaging **defocused** frames and losing sharpness.
Dark regions have low `S`, hence low SNR under `sigma^2(S) = gS + (RN*g)^2`,
hence a wide gate, hence blur. If that is right, the gate is not trading noise
against noise in these regions; it is trading away resolution exactly where the
picture is darkest.

I am explicit that this is ARGUED and that I can name a competing explanation I
cannot exclude by eye: the mark may be ragged in reality, since paint settling
into brush grooves would genuinely have a soft mottled boundary. So the test I
registered is not "gate 2.0 versus gate 4.5, pick the nicer one". It is against
the invariant the project already claims:

> the merge must never be worse than the best single frame.

Find the source frame sharpest **at the mark's location**, bring it into the
merged geometry through the merge's own alignment, and compare edge profiles in
camera-linear space from one binary -- with the sharp metal site as the built-in
control. If the instrument reports the merge losing sharpness at the *metal*
too, it is measuring misregistration or resampling loss and the mark result
means nothing. If the merge matches the single frame at the metal and is
materially softer at the mark, that is a hard invariant violation localised to
low-SNR regions, and it is the best candidate yet for the owner's complaint.

### 56.2 The third instance, and the first black-box detector for it

`--photometric` is **inert on the shipped path**. Measured by hash, one binary,
one subject, everything else fixed:

| arm | SHA-256 |
| --- | --- |
| unset / `--photometric=on` / `--photometric=off` | all `CF48D6E2...1C2482` |
| `--merge estimator`, unset | `2AA68069...A857EA` |
| `--merge estimator --photometric off` | `180CBA77...A94956` |

The positive control fires, so the identity is the product's, not the harness's.
The photometric fit lives only in `run_estimator`; the default backend is
`Pyramid`; the flag reaches nobody.

That is the **third** instance tonight of work not reaching the product, by a
third distinct route, and the table from section 54.2 now needs a fourth row:

| section | how it fails to reach the product | signature |
| --- | --- | --- |
| 49, 51 | instrument and product on opposite sides of a transformation | measurements do not predict the render |
| 52 | the stage exists but the backend skips it | the tool prints `not applied: ...` |
| 54 | compiles, complete, self-testing, **never called** | nothing at all -- invisible |
| **56** | **the flag is accepted, and silently changes nothing** | **only a hash comparison shows it** |

The last of those is the one worth generalising, because it needs no reading of
the call graph, cannot be fooled by a module that merely compiles, and yields an
artefact that survives argument:

> **A flag is a promise. To find out whether the tool keeps it, set the flag to
> each of its values with everything else fixed and hash the outputs. Byte
> identity across every setting means the promise is not kept -- provided a
> positive control in the same run proves the harness can see a change at all.**

I have commissioned a full census of every flag `stack` accepts on this basis,
with the outcomes required to partition exhaustively -- *changes output*,
*inert*, *refused with the refusal quoted*, *not examined with the reason* --
summing to the number of flags the CLI actually defines. Refusal is honest
behaviour and is not a defect; the quarry is the flag that is accepted and does
nothing.

### 56.3 Two rules, one of which corrects me

**A ratio hides an additive defect in proportion to its baseline.** The
photometric gate `K2` scores a high-frequency energy *ratio*. Its corpus-worst
stack is `foam` at **-50.41 DN**, which `K2` scores at 1.0129 because the
baseline there is 3667.6 DN -- so the gate **mis-orders its own two worst
stacks**. Corpus totals: +33.03 DN removed, -92.48 DN added, net **-59.45 DN**.
The build agent caught this in its own draft, which is the hard direction to
catch it in.

> **Any gate that admits inputs with different baselines must report absolute
> units alongside the ratio. A ratio is a comparison to a denominator you did
> not choose.**

**And the correction to me.** I have been telling every agent to commit
path-scoped -- `git add -- <paths>` then `git commit -- <paths>` -- as the
defence against concurrent agents in one working tree. It is a real defence and
it is not the one I thought it was. `git commit -- <path>` commits the
**current worktree content** of that path, bypassing the index. So it protects
*other files* from your commit, and gives **zero** protection to *your file*
from another agent's commit: two agents editing one file will commit each
other's half-finished work in whichever order fires first. That is exactly what
happened when `6430fb2` swept an uncommitted `merge_cmd.rs` change belonging to
a different agent.

> **Path-scoped commits protect other files from you. They do not protect your
> file from anyone. The only defence against two agents in one file is that
> there are never two agents in one file.**

`merge_cmd.rs` presently violates that, with several agents in it. It is my
allocation error, not theirs, and it is the reason at least one measured result
tonight had to be re-derived.

### 56.4 What this changes about the finish

It narrows it. The five stages the pyramid backend announces it skips looked
like five pieces of work. On the evidence they are mostly not:

| stage | status |
| --- | --- |
| photometric gain | **measured harmful** -- net -59.45 DN, gate fired, three routes agree. Do not port. |
| halo correction | ring **measured gone** on this backend, and confirmed by eye. Not needed. |
| clip census | hull clamp **verified live** on the delivered masters. Not needed. |
| outlier rejection | need **being measured** -- does anything in this corpus actually move? |
| through-focus statistics | wanted for confidence as a *product feature*, not to fix a defect. |

So the remaining quality work is not a five-stage port. It is: whether the gate
blurs the dark side, and whether the unwired restoration recovers the 1.43x the
gather throws away. Two questions, both in flight, both with registered tests.

## 57. Two audits, and the shape of the project changes

Two verifiers reported within an hour of each other. Neither was asked the
question it ended up answering, and between them they overturn section 54,
correct section 56's table, and settle an architectural question I had been
treating as open.

### 57.1 The restoration module's mathematics is exact and its safety case is worthless

V-RESTORE audited `restore.rs` from first principles at `a2582514`, with probe
binaries built into a scratch tree and nothing under `crates/` touched.

What it confirmed matters, because it means the module is worth repairing
rather than discarding. It did not read `align.rs` and trust it. It pushed a
delta through the product's own `Resampler::sample` at 8 phases across 5
resamplers, extracted the taps the sampler *actually applies*, and compared
`gather_mtf` against its own DTFT on a 201-point grid:

| resampler | max abs difference |
| --- | --- |
| nearest | 0.000e+00 |
| bilinear | 0.000e+00 |
| catmull-rom | 0.000e+00 |
| lanczos2 | 3.331e-16 |
| lanczos3 | 4.441e-16 |

The Wiener algebra is equally sound: at infinite SNR the gain converges to
exactly `1/MTF` to six places, `f=0` is exactly 1.0 for every signal power, and
the noise-floor subtraction is present at `design_fir:412`. On real pixels the
mean shifts by -3.2 ppm and the 50% edge crossing does not move at all,
550.000 DN before and 550.000 DN after. **This filter cannot move an edge or
change exposure.** The loss it corrects is real.

Then four defects, and the third is the one that matters.

**The gain cap bounds half the filter.** `restore_plane` convolves separably in
x then y with the same taps, but `design_fir` caps only the 1-D response.
Pushed a checkerboard at exactly fx=fy=0.5 through the shipped code: the report
says `max_gain=1.430534`, the pixels get `2.046517`, and `max_gain^2` is
2.046429. A caller asking for 1.7 gets 2.89.

**At the noise floor the shipped merge actually has, it rings.** The module
header claims that on a real hard edge "the largest profile change anywhere is
0.0035 of the step, and there is no ringing to see." Measured on `lavendar-cpl`:
**7.82% in 1-D, 16.25% at a 2-D corner** -- 22x the module's own claim. The
shape is a multi-lobed decaying ring, `107.95, 89.01, 137.33, 29.62`, because
taps k=2 and k=4 are both positive. On real camera-linear pixels at a real
silhouette, **3.75% of pixels are driven outside the min/max of their own 9-tap
input support**, worst excursion 7107.7 DN; one 13594 DN pixel between two
highlights lands at 6119.9 DN.

That is a halo. On the owner's subject. In the one place this project has just
finished proving it had removed one.

**And the reason the module did not know is that its verdict was measured at a
noise level the product does not have.** The docs reach "measured never to bind"
at sigma^2 = 691.6 and 4983.0. The actual HF noise floor of the shipped
`lavendar-cpl` green plane is **82.15 DN^2** -- 8x to 60x smaller, because the
merge averages frames and its output is quieter than any input. Across that
range `max_gain` swings from 1.005, which is inert, to 1.536, which is nearly
full strength. Nothing in `restore.rs` estimates sigma^2. It is a free parameter,
and whatever the wiring passes decides the entire behaviour of the feature.

**A fifth way for work to fail to reach the product**, and it is the subtlest so
far. The module was not unmeasured. It was measured, honestly, by a competent
author, and the verdict is void because the conditions were not the product's.

> **A module that takes a free parameter has no safety verdict until the product
> pins that parameter.** Its verdict is a claim about the values it was run at
> and about nothing else. Where the parameter is a noise level, note that the
> merge's output is quieter than its inputs, so a value measured on a frame is
> the wrong value for a merge.

> **When a guard is applied per-axis and the operator is separable, the guard
> bounds the square root of what the picture gets.** Assert on the realised
> quantity, never on the designed one.

Two more, both cheap and both of the silent class. `sigma2 = NaN` NaNs all 4096
pixels while `max_gain` reports a reassuring 1.0, because Rust's `f64::max`
ignores NaN and the cap loop never engages. A single NaN input pixel makes
`power_at`'s `p.max(0.0)` clamp the signal power to 1e-12, so the gain is 1.0
everywhere and the designed filter is the identity -- and the report is then
indistinguishable from a legitimate refusal to sharpen, while the NaN still
spreads to a 9x9 block.

### 57.2 The self-test passes a kernel the product does not use

`restore.rs:110-116` claims to pin agreement with `align.rs`'s samplers.
V-RESTORE mutated the Keys inner branch `2.5 -> 2.6`, and separately changed the
kernel outright with `a = -0.5 -> -0.75`. Both move MTF(0.25) from 0.9402 to
about 0.986. Both are a **different kernel from the one the product gathers
with**. `selftest()` returned GREEN for both.

The mechanism is worth stating because it is general. Arm 1 asserts `M(0) == 1`,
but `gather_mtf` divides by the tap sum before evaluating at f=0, so it computes
`sum/sum` and is 1 for any partition-of-unity kernel whatsoever. Arm 2 probes
only integer offsets, where the inner cubic contributes nothing but its constant
term and the outer branch takes over. The entire inner branch is invisible to
the test that exists to pin it. Only the hard-coded constants at line 573 catch
the mutation, and they cover `CatmullRom` alone.

> **A self-test that divides by the quantity it then checks is tautological.**
> The division launders any input into the expected answer.

**And my line 573 claim is withdrawn.** I routed it to an implementer as a
defect. The constants `(0.25, 0.9402), (0.40, 0.7425), (0.50, 0.6251)` are all
correct to five places against an independent DTFT, and 0.7425 is correctly
labelled f=0.40. What is wrong is any document quoting 0.7425 at f=0.35. The
per-axis value there is **0.8211**; the **1.43x everyone has been citing is the
two-dimensional figure**, 0.69776 measured on the real warpmap against 0.6743
under uniform phase.

That is the second unchecked number I relayed in one night, after the
magnification claim in section 55. Both arrived with my authority attached and
neither had my verification attached, and the receiving agent had no way to
tell them apart from something I had measured.

> **A relayed number carries the relayer's authority but not the relayer's
> verification.** Mark every routed claim as measured-by-me, measured-by-named-
> agent, or unchecked -- and instruct the recipient to reject unmarked ones.

### 57.3 The default backend is the least capable one

V-REACH audited reachability across both crates: a 366-item public-symbol census
and an independent 746-function call graph, the latter over-approximating
reachability by letting comment text create call edges, so its complement is a
sound dead set.

| census A: public items | count |
| --- | --- |
| LIVE-DEFAULT | 175 |
| LIVE-BY-FLAG | 154 |
| LIVE-BUT-INERT | 1 |
| TEST-ONLY | 14 |
| DEAD | 22 |
| UNRESOLVED | 0 |
| **total** | **366** |

Census B: 663 functions reachable from `main`, 83 not, totalling 746. One known
false positive among the 83 (`parse_roi`, referenced by a clap attribute rather
than a call), so at least 82 are genuine.

Section 54 found one module with no callers and treated it as an anomaly. It is
not an anomaly. **About 180 KB of finished, tested Rust never executes.**

- **`outlier.rs`, 51 KB, 13 of 13 public items, has zero references from any
  `src/` file in the repository.** No `use`, no path reference, nothing. Only
  four example binaries touch it. It is strictly worse off than `restore.rs`,
  which at least appears in a `pub mod` line. The four `outlier` hits elsewhere
  in the tree are the aligner's own unrelated `outlier_mads`.
- `through_focus.rs`, 90 KB, 12 of 12 public items, live only by flag on a
  backend the product does not use.
- `halo.rs`, 23 KB, estimator-only **and** additionally gated off by env.
- The whole M89 robust-election family is dead on **both** backends.
  `FocusStats::new_robust` has no callers anywhere; it is the only caller of
  `active_arm()`, which is the only reader of `STREHL_ROBUST_ELECTION`; so every
  public item of `robust.rs` is unreachable at runtime. Proved, not inferred:
  the env var gives byte-identical output on both backends against controls that
  differ.
- The measured PRNU is never attached on any path by any flag. This one is
  deliberate -- `profile.rs:778` asserts that the shipped profile must not
  attach a pattern -- but it strands the M71 gain correction with it.

The banner has been telling us this every single run. `not applied : photometric
gain, clip census, outlier rejection, halo correction, through-focus`. Four of
those five are fully written and live inside `run_estimator`; the fifth is
written and wired to nothing. The line is not a status. It is a confession, and
it has been printing on every render for weeks.

**So the project's shape is two merge backends: one holds the quality machinery
and stamps visible slabs, the other merges well and has none of it.** The
estimator is additionally broken out of the box -- `--merge estimator` on
`coffee-bubbles` exits rc=1 with `U3 the eroded low-detail region keeps only
0 px` unless `STREHL_PHOTOMETRIC=off` is pinned.

**The call, made now so it stops being re-litigated: pyramid is the product.**
It wins on picture quality, verified numerically and by eye on two subjects, and
it is about 25% faster. The estimator will not be fixed. Capability comes to
pyramid or it does not ship. And the ranking rule for what comes across is not
code volume:

> **"This is finished and tested, therefore we should use it" is the reasoning
> that put five stages behind a backend that stamps slabs.** Stranded code is a
> sunk cost, not an argument. The only question is whether wiring it changes
> pixels for the better on the owner's own captures.

### 57.4 A dead diagnostic on a live lossy operation

`Hull::InputRange` is the default and clamps every output pixel on the product
path. Its only measurement, `pyramid::clamped_fraction`, is called from an
example binary and from pyramid's own tests, and from nowhere else. **The clamp
fires silently on every shipped render and the number that would say how hard is
never computed.**

Worse, `Hull::Unclamped`'s doc comment claims it is "kept reachable because a
fix whose defect can no longer be reproduced cannot be measured
interventionally." For the product binary that claim is **false**: there is no
`--pyramid-hull` flag and no env var, and the only construction site outside
`pyramid.rs` is an example. The comment is a claim by an absent author about a
reachability that does not exist.

> **A dead diagnostic on a live lossy operation is worse than no diagnostic.**
> Its presence in the source reads as evidence the loss is being watched.

Section 56's table said the clip census was "not needed" because the hull clamp
was already verified live on the delivered masters. That was too quick.
Verifying that a clamp fires is not the same as knowing how much it takes, and
the instrument that would say is the dead one.

### 57.5 What is actually gone

Two things in this audit are not unwired but absent. **No hot-pixel or
defect-pixel correction exists anywhere in either crate** -- every textual hit is
prose. And `restore.rs` is the only MTF-restoration capability in the binary, so
the gather's two-dimensional amplitude loss is uncorrected on every shipped
frame and nothing else could correct it.

One thing I expected to find dead is alive, and it is worth recording because
the auditor checked it specifically for that reason. The lateral CA correction's
*accessors* have no non-test callers, which makes the module look stranded. The
correction itself runs on the product path via `warp_frame_in_place`, and the
ship log proves it: `lateral CA : CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl"
(gear matched; default on)`. Reporting it as dead on the strength of the
accessors would have been exactly the error this section is about, in reverse.


## 58. The output is print-worthy, and the clamp costs 3% not 15%

Section 57 closed on capability that is missing. This one opens on capability
that is present, because for the first time tonight the question "is this good
enough" has an answer taken from pixels rather than from a report.

### 58.1 Three subjects at 1:1, judged by eye

The owner's standing instruction is to work until the stacker produces
award-quality, print-worthy output. That is a judgement about a picture, and no
scalar in this corpus can stand in for it. So it was made the only way it can
be: by pulling true 1:1 tiles out of the delivered masters and looking at them.

`pixelpeep.py` selects the highest-detail tiles in a master by mean absolute
Laplacian on a coarse grid, spaces them so they do not all land on one feature,
and grades them through a single display curve derived once per master from the
whole frame. The single shared curve is not a detail. Deriving a curve per tile
would make two tiles from the same image mutually incomparable, and a
brightness difference between two regions of the subject would read as a
grading difference. That is the same defect that made a matched pair look
geometrically shifted in section 56, and the docstring in `hullcrop.py` now
forbids it by name.

| subject | rank | what is resolved at 1:1 | halo |
| --- | ---: | --- | --- |
| `bee-3-cpl` | 10 | individual plumose hair barbules, incl. the branched side-structure of bee hair | none |
| `leaf-2-cpl` | 6 | vein structure at three scales, cell-level texture, chloroplast speckle | none |
| `112MSDCF` | 4 | crystal dendrites to near single-pixel branch width | none |

All three are print-worthy. The verdict is mine, it is visual, and it is
recorded here as a judgement rather than a measurement so that a later reader
can disagree with it on the same evidence.

**The halo is gone at the place it was worst.** The hardest tile in the whole
delivered set is `bee-3-cpl` at y=964 x=4564: fine pale hairs crossing in front
of the dark, defocused compound eye. That geometry -- a bright thin foreground
over a dark defocused background -- is where every focus stacker in existence
produces a bright rim, and it is where this project's own output was unusable
earlier tonight. There is no rim. The hairs hold their edges across the
boundary and the eye's facet texture reads through behind them.

`leaf-2-cpl` is the more searching test of the two and was chosen for that
reason. Leaf veins are long, high-contrast, and locally straight, which is the
geometry that a Laplacian pyramid rings against most readily. They are clean.

### 58.2 One visible defect remains in the flagship

In `bee-3-cpl` a tarsus and claw around y=2723 x=1998 read soft, low-contrast
and veiled, while hairs a few hundred pixels away stay crisp. It is the only
thing left in that frame that a print would show.

Whether it is fixable is a single question with three possible answers, and the
answer determines the entire response:

- some frame saw it sharply and the merge lost it -- a **merge defect**,
  fixable, and important because the mechanism would be damaging every stack;
- no frame ever saw it sharply -- a **capture limit**, and the honest product
  response is to report it rather than fake it;
- the through-focus response is **bimodal** -- a background element seen through
  defocused foreground, which is the two-layer veiling case and has its own fix.

`throughfocus_probe.py` answers it by reading the CFA green lattice straight
from the raws with no demosaic, no alignment and no tone curve, and reporting
mean absolute Laplacian in a fixed window per frame. Only the shape of the
resulting curve is interpreted, never its height, which makes the measure
independent of scene brightness and of the merge entirely.

### 58.3 The control caught the author, again

The probe requires a control window on structure known to be sharp mid-bracket,
and refuses to interpret the probe at all unless the control produces a clear
interior peak.

On the first run the control commissioned cleanly at a peak-to-floor ratio of
**2.45**, and the probe returned **1.16** -- barely above the flat threshold,
and a number I was one step away from reading as "capture-limited, nothing to
be done."

Dumping the probe window to a PNG and looking at it showed it was sitting on
blank white background with a few stray hairs in one corner. The claw was not
in it. **The reading was correct and the window was wrong.**

> **A window that is not on the subject reads flat no matter what the subject
> does.** Confirm the window contains the thing by dumping it and looking at it,
> at several points along whatever axis the instrument sweeps. Arithmetic that
> maps coordinates between two grids is not confirmation; it is the assumption
> under test.

This is the sixth instrument-across-a-transformation failure recorded tonight
and the third in my own hands. The pattern is now stable enough to state
plainly: every one of them was an instrument reporting confidently about
something it was not actually measuring, and every one was caught by looking at
the intermediate rather than by reasoning about the result.

The claw diagnosis is therefore **unresolved**, and is with a dedicated agent
that has the instrument, the commissioning result, and a written account of how
its author misused it.

### 58.4 The clamp: two instruments, five-fold disagreement, one signature

Section 57 routed a claim that the default hull clamp costs 15.5-18.9%
microcontrast on `coffee-bean`. I measured the same matched pair and get about
**3%**.

First, the pair is sound, because the alternative explanation had to be
eliminated before the number could be doubted. Integer cross-correlation over
+/-40 px gives `dy=0 dx=0`; a planted +17 px roll is reported as -17, so the
search can see a shift when there is one; the silhouette's 50% crossing moves a
mean of +0.20 px across five rows.

| band | period | clamped | unclamped | retained | share of change |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 2 px | 537.83 | 553.02 | 97.25% | 60.4% |
| 1 | 4 px | 889.89 | 919.64 | 96.76% | 28.4% |
| 2 | 8 px | 1181.13 | 1224.61 | 96.45% | 8.9% |
| 3 | 16 px | 1319.67 | 1364.39 | 96.72% | 1.8% |
| residual | >128 px | 36650.07 | 36635.78 | 100.04% | 0.1% |

A global 3x3 Laplacian RMS agrees: 98.80% retained frame-wide, 95.72% at the
worst 700 px tile.

**Both numbers can be honest.** A global RMS is dominated by the strongest
edges in a frame, and a large fractional loss confined to low-amplitude texture
hides inside it almost completely. A local, texture-restricted measure would
report that same loss at full size. The disagreement is therefore probably not
an error by either party but a difference in what is being averaged over, and
the useful question is which of the two quantities corresponds to what a person
sees when they call a print soft. That is with an independent verifier, given
both methods and both numbers and told to define the quantity itself rather
than reuse either.

Two findings survive the disagreement, because both instruments show them:

- **88.8% of the change lives in the 2 px and 4 px bands.** The first hypothesis
  on seeing the percentile table was that the clamp merely shifts tone. The band
  split refutes it. The clamp acts on fine detail.
- **It is not rare.** 24.6% of pixels change, 17.1% by more than 100 DN, 1.9% by
  more than 1000 DN. The source comment at `pyramid.rs:666-674` describing this
  as binding constantly while changing nothing is wrong.

### 58.5 The percentile signature, which may close the workstream

| percentile | clamped | unclamped | delta |
| --- | ---: | ---: | ---: |
| p1 | 1726 | 1589 | **+137 DN** |
| p25 | 6928 | 6720 | **+208 DN** |
| p50 | 22107 | 22105 | +2 DN |
| p75 | 53326 | 53343 | -17 DN |
| p99 | 65535 | 65535 | 0 DN |

The clamp lifts the dark end and leaves midtones and highlights alone. That is
the signature of removing **undershoot**: a Laplacian reconstruction ringing
downward at edges, driven below the hull of every contributing frame.

If that is what it is, the argument inverts completely. Content below the hull
of every contributing frame was seen by no frame. It cannot be detail. Removing
it is correct, the 3% is the price of removing ringing rather than a loss, and
the recommendation changes from "do not ship this unconditionally" to "keep it."

> **Before pricing the removal of an operation, establish what the operation
> removes.** A cost measured without that is a number attached to an unknown
> quantity, and optimising it can as easily restore an artifact as recover
> detail.

The decisive test is not another magnitude. For the pixels the clamp moves,
does the unclamped value lie outside the hull of the contributing frames or
inside it? Outside is ringing, correctly removed. Inside is detail, wrongly
removed. The domain trap from section 57 governs the answer: the clamp bounds
four CFA quad planes before demosaic, any hull computed in demosaiced RGB is a
different and strictly weaker constraint, and a test run in the wrong domain
will answer a question nobody asked.


## 59. Two instruments that measured the wrong thing, and the veil's mechanism

Section 58 reported that the pictures are good. This one reports three things
that were wrong while they were good. Two were found by looking rather than by
reasoning, one of those was mine and had already been sent to two agents as an
instruction, and the third is the mechanism behind the last visible artifact in
the output.

### 59.1 The flower finding, and its retraction

`detailgallery.py` produced the artifact nobody had produced: twenty-six true
1:1 tiles, one per subject, at full resolution. Ranking those subjects by mean
absolute Laplacian in DN put every flower in the corpus in the bottom seven.
Three flower subjects, three of the last seven places, out of twenty-six. That
is the shape of a real pattern, and it was routed to BUILD-TRIAGE as a merge
defect on a subject class and used to justify part of BUILD-SWITCH's brief.

Then the tiles themselves were opened. `flowers-cpl` resolves individual
papillate epidermal cells -- the microscopic domes that give a petal its
texture. `flower-inner-edge-cpl` resolves those *and* pollen grains. Neither is
soft. Both were being ranked last for a reason that has nothing to do with the
merge: they are cream on cream, and a detail statistic in absolute units
measures how much contrast the subject has as much as how much of it the tool
recovered.

`sharpvscontrast.py` divides the detail statistic by the local RMS contrast
actually present in the same window. The ranking moves:

| subject | rank, raw DN | rank, normalised | local contrast (DN) |
| --- | ---: | ---: | ---: |
| `flowers-cpl` | 25 | **5** | **1282** (corpus minimum) |
| `flower-inner-edge-cpl` | 26 | 17 | 1508 |
| `flower-bud-alone-cpl` | 24 | 18 | 2328 |

A normalisation is a claim about an instrument and gets the same treatment as
any other claim, so the script carries a blur-monotone control: progressively
blur each master and require the normalised statistic to fall. It fell on
**26 of 26**. The statistic responds to blur and is not merely dividing one
kind of noise by another, which is the only reason its ranking is allowed to
mean anything.

Retractions went to both agents. The rule:

> **A detail statistic in absolute units measures the subject as much as the
> tool.** Divide by the contrast actually present, and prove the normalisation
> is blur-monotone before believing the ranking it produces.

The genuine bottom is elsewhere, and smaller than the false one: `119MSDCF`
(26th on both statistics) and `109MSDCF` (22nd raw, 25th normalised) are the
only subjects that are under-resolved by both measures. `coffee-bubbles` and
`foam` form a third class -- high contrast, little detail per unit of it --
which is a property of soap films and not a defect.

Two corrections arrived from BUILD-RENDER in the same window, both overturning
descriptions written here. `foam` is not the dark, noisy, flat subject this
corpus called it; it is a soap film with resolved interference banding and the
**lowest** noise-to-gradient ratio in the corpus at 0.072 -- against
`flowers-cpl`'s 0.201, the highest. The v2 ranking defect it was cited for was
sparsity, the ratio falling as one over the square root of the detailed
fraction, not noise. And `highly-angled-ruler-mm-cpl`, which looks poor on every
contact sheet ever made here, is genuinely sharp at 1:1 and sits mid-pack at
1364 DN. Both errors are the same error as the flower error: a summary statistic
or a reduced image standing in for the picture.

### 59.2 The differentiator that does not reach the shipping backend

The README's comparison table against every other stacker had five rows. The
fourth read: *Output -- an image, versus an image plus a per-pixel confidence
map.* It is the row the project's thesis rests on, since a stacker that can
separate "retouch this" from "reshoot this" is an instrument and one that
cannot is a bug report.

Tracing it through the tree:

- `main.rs:787-814` declares a `wrong_backend` table. **Nine** flags are
  refused when `--merge pyramid` is active, and pyramid is the default:
  `--gate`, `--target-n-eff`, `--index-map`, `--n-eff-map`, `--photometric`,
  `--stats`, `--stats-placebo`, `--flat-roi`, `--detail-roi`.
- `--n-eff-map` is the only per-pixel trust artifact that exists. It is written
  by `write_n_eff_map` at `merge_cmd.rs:2636`, called once, at
  `merge_cmd.rs:3782`, from `est.n_eff()` -- the estimator.
- Every other occurrence of the string `confidence` in the CLI crate is inside
  `report_statistics` at `merge_cmd.rs:5257`: console text, not an artifact.
- V-REACH established earlier that `--merge estimator` exits rc=1 out of the
  box.

So the shipping default emits an image and nothing else, and the row was an
overclaim. The README now says so in the table itself rather than in a
footnote, names the nine refused flags, and states that closing the gap is the
top priority after the merge. Correcting the document is not the fix; it is the
precondition for the fix being honest about its own size.

This is the third finding tonight of the same species as section 57's, and the
species deserves its own statement:

> **A capability that exists in the codebase, is flagged, and is documented can
> still be unreachable on the path the product actually runs.** Reachability is
> a property of the default configuration, not of the source tree, and it is
> established by running the shipping command and looking at what it wrote.

BUILD-SWITCH contributed the complement, promoted here because it generalises
past the case that produced it:

> **A flag census enumerates the promises a tool makes and tests whether it
> keeps them. It is structurally blind to a stage that makes no promise.**

Twenty-seven flags were enumerated in an earlier audit. **Zero** of them match
`hull` or `clamp`, which is why an operation touching 24.6% of pixels was
invisible to a census that was otherwise complete and correct. The complement to
a census is not a longer census: it is tracing the default configuration and
asking what the `if let Some` overrides do *not* cover.

### 59.3 The veil is a pedestal error, and the base band is a plain mean

The flagship master has one visible defect left: a haze over the bee's tarsus
and claw. Section 58 recorded a failed attempt to diagnose it -- a probe window
that turned out to be sitting on blank background, caught by its own control.
V-VEILCLAW was given that failure in writing and re-ran it properly. The result
is the most actionable finding of the run.

Probe box `y 2640:2830 x 2080:2270`, all 299 frames, step 1, with the control
kept unchanged and a **null** window added on plain paper:

```
CONTROL: SINGLE-PEAK  floor=83.3  f244 prom=0.24
NULL   : FLAT (no peak with prominence >= 0.10 of floor)
PROBE  : TWO-PEAK     floor=84.2  f182 prom=0.45   f288 prom=0.29
```

The control responds, the null stays quiet, and the probe is **bimodal**: two
peaks on the same pixels, **106 frames apart** (f182 and f288; the source report
said 108, and 288 - 182 = 106 -- corrected here on recomputation). A per-frame
contact sheet says
what each peak is -- `f171-198` is sharp foreground hairs on blank paper,
`f285-291` is the claw with the hairs dissolved. This is the two-layer occlusion
case, directly observed rather than inferred.

Then the decisive measurement, each plane normalised by its own paper white:

| plane | base mean | base p5 | detail rms |
| --- | ---: | ---: | ---: |
| f288 (resolved the claw) | 0.581 | 0.206 | 0.177 |
| f180 (resolved the hairs) | 0.892 | 0.835 | 0.047 |
| **master** | **0.802** | **0.669** | **0.104** |

`corr(master_detail, f288_detail) = +0.852`; `corr(master_detail, f180_detail)
= -0.035`; `master_detail ~= 0.50 * f288_detail`.

**Selection is not the defect.** The merge picked the right frame, and the
claw's structure is present in the master at 0.85 correlation with the frame
that resolved it. What is wrong is the *pedestal*: the master's base sits at
0.802, near the foreground layer's 0.892 rather than the claw's 0.581. The claw
is rendered at half amplitude on the occluder's brightness. The veil is not lost
detail. It is lost base.

The mechanism was reported as an unconfirmed lead and was confirmed here by
reading the source rather than by accepting the report. `pyramid.rs:895` sets
`base: BaseBand::Mean` as the default; `pyramid.rs:673` sets
`DEFAULT_MEAN_COARSE = 0`; `pyramid.rs:608-612` defines `Mean` as a "plain mean
across frames" that "does not depend on position at all." So the base residual
is an unweighted mean over all 299 frames, roughly 290 of which show the
defocused bright foreground at that pixel. The mean drags 0.581 to 0.802, the
detail band is selected correctly, and the correct detail is added to the wrong
pedestal. Signature and mechanism agree.

The sharpest part is that **the file already names this failure mode.**
`pyramid.rs:622-627`, arguing the case *for* the rejected `WeightedFromCoarsest`
arm, says it buys "local tone: at a depth boundary the in-focus frame's low
frequencies win locally instead of being averaged with every defocused frame's
veil." The project wrote down the veil, measured the alternative, found it cost
-2.5% of global level plus about 4% of position-dependent wander on featureless
backdrops, and correctly shipped the arm that has the veil.

Both arms are wrong, and the reason the choice looked forced is that nobody
noticed the two defects live in **disjoint** regions. A featureless backdrop has
no focus signal and no bimodality; an occlusion boundary has both. The base band
does not have to choose between being position-independent everywhere and
position-dependent everywhere -- it needs to be position-independent *where
there is no evidence* and to respect layer structure *where there is*. That is a
third arm neither existing option explored, the detector for it is now built and
commissioned, and it has been routed to the owner of `pyramid.rs`.

> **When two arms of a measured trade-off are both wrong, check whether their
> defects share a domain before accepting the trade.** A trade-off between
> defects that never co-occur is not a trade-off; it is two separate problems
> being solved with one switch.

### 59.4 Two corrections that came with it

**Master-to-raw is not near-identity, and this corpus said it was.** The
recorded fact was that the master at 4688x7032 and the green lattice at
2344x3514 differ by about 4 px and map near-identically. That holds only at the
optical centre. There is roughly 13% magnification breathing across the bracket,
about 0.35 px/frame per axis at the claw, and *within a single frame* the
required registration shift differs by **more than 150 px** between regions,
growing with distance from centre: at f240, region (4000,3400) needs
dy=-186,dx=+20 while region (3285,2065) needs dy=-94,dx=+152. Any fixed box
carried between master and raw coordinates without per-frame drift correction is
measuring the wrong pixels. That is exactly how the first attempt at this
diagnosis failed, and the corrected fact has been sent to every agent whose work
crosses that boundary.

A useful corollary, unlooked for: the drift is smooth and monotonic across the
bracket, which makes it breathing rather than subject motion. That is evidence
*against* the urgency of the dormant outlier-rejection module, and it arrived
from a probe aimed at something else entirely.

**And my own probe was blind to the case it was built for.**
`throughfocus_probe.py` exists to distinguish merge defect from capture limit
from two-layer veiling, and its docstring names bimodality as the important
case. Its `verdict()` takes the argmax of the response curve and asks only
whether that peak is interior. On this window it returned `INTERIOR-PEAK
frame#182` -- the *foreground* peak -- and would have reported MERGE. It cannot
see a second peak at all. The instrument named the case in prose and then
implemented a statistic incapable of expressing it.

> **A statistic that reports the location of a maximum cannot report that there
> were two.** If the docstring names bimodality, the implementation owes a
> prominence test, not an argmax.

The repair is in, and commissioning it turned up a second defect in the same
five lines. `commission_verdict.py` runs the old and the new implementation over
the same seven curves -- four synthetic with truth known by construction, one
decoy built specifically to tempt a spurious second peak, and the real claw
curve. The repaired `verdict()` is correct on **7/7** and catches **3/3**
two-layer cases; the original **missed 3/3**, which is what establishes that
this change repairs something rather than merely rewriting it.

On real data the repaired instrument reproduces the independent measurement:
`TWO-PEAK frame#182 prom=0.45 frame#288 prom=0.29 separation=106 frames`,
against V-VEILCLAW's f182 prom=0.45 / f288 prom=0.29 from its own code. Two
implementations, same numbers.

The second defect: the original returned `INTERIOR-PEAK` on **every** non-flat
curve in the set, including a monotone rise to the end of the bracket. Its
end-of-bracket test read the argmax of the *raw* curve, and near any maximum a
smooth function is flat, so noise moves the argmax several samples -- enough to
push it off the last two and convert "the bracket ran out" into "a frame had
it". The repaired version takes the argmax of the smoothed curve. This defect
was not the one being fixed; it was found because the harness included a case
that had nothing to do with bimodality.

> **Smooth before you take an argmax.** The location of a maximum is the least
> stable thing about a peak, because that is precisely where the derivative is
> zero.

### 59.5 What the three findings have in common

The flower ranking was an instrument reporting confidently about the subject
while being asked about the tool. The confidence row was a document reporting
confidently about the product while describing the source tree. The veil probe
was an instrument whose prose named a case its arithmetic could not express. All
three survived because what they said was, in a narrow sense, true -- the
flowers really do have the lowest Laplacian, the map really is implemented,
frame 182 really is the argmax -- and none would have been caught by checking
the claim as stated. All three fell within minutes of opening the object
itself: the tile, the flag table, and the response curve.

That is now seven instrument failures in this run, four of them in this
orchestrator's own hands, and not one was caught by reasoning about a result.
Every one was caught by opening the intermediate. The pattern is stable enough
to state as a working rule rather than an observation:

> **Confidence in a result is not evidence about the instrument that produced
> it.** The only thing that has ever caught one of these is looking at what the
> instrument looked at.

## 60. The night the orchestrator broadcast two wrong numbers

Sections 56 to 59 each recorded an instrument that misled the person holding it.
This one records something worse: two numbers that were wrong, that I sent to
fourteen agents at once, and that at least one of them then used to deprioritise
its own correct work. The instrument failures were mine to find. This one was
mine to cause.

### 60.1 The hull clamp is exonerated, and it should stay

The clamp had been the leading suspect for the softness since section 51. It is
now settled, and it is innocent. V-HULLCOST re-derived its cost independently and
got **~3.1%**, against the 15.5% in circulation. More useful than the ratio is
the comparison BUILD-HULL made in its section 17: the clamp's effect measured in
units of the merge's own noise floor, per octave.

| subject | sigma | removed at detail0 | removed at base |
|---|---:|---:|---:|
| flower-bud-alone (genuinely clips) | 47.13 | **0.42 sigma** | 4.49 sigma |
| coffee-bean | 340.30 | **0.29 sigma** | 0.68 sigma |
| couch-fibers (placebo) | 196.04 | **0.10 sigma** | 0.12 sigma |

At every scale where detail lives, on every subject tested including the one
that clips hardest, the clamp removes **less than the noise that was already
there**. What it does remove sits at the base octave, and it removes dark
excursions that no contributing frame ever contained -- which is the definition
of an artifact, not of signal. The clamp is a denoiser wearing the costume of a
detail thief. All four of the predictions registered against it were refuted,
two of them mine.

**Keep the clamp.** The 24.6%-of-pixels-changed figure is unaffected and remains
true; it was always a count of pixels touched, never a claim about how much was
taken from each.

### 60.2 The first retraction: a number carried out of the band it was measured in

The 15.5% was real, and it was measured. It was an **aggregate microcontrast**
figure. I relayed it as "the clamp costs 15.5% of microcontrast and is the
leading explanation for the softness we are all chasing", and in doing so I moved
it from the aggregate to the specific -- to the fine octaves where the softness
complaint actually lives, where it had never been measured.

BUILD-SHARP then did the same thing one step further, multiplying it into a
specific frequency to produce "plausibly nearer 0.57", and -- this is the part
worth recording -- **caught its own error independently of the input being
wrong**. Its note is better than anything I would have written:

> Being sourced from a named agent made the input citable; it did not make my
> extrapolation sound.

That defect would have stood even if the 15.5% had held. It generalises past this
incident:

> **A number is only valid in the band it was measured in.** An aggregate is not
> a licence to speak about any particular part of the aggregate, and citing a
> real measurement does not make an extrapolation from it a measurement.

### 60.3 The second retraction: my own instrument, inverted by a factor of 4^k

Having relayed one wrong number, I produced a second one myself. I reported that
**88.8% of the clamp's change lives in the 2 px and 4 px bands** -- which, had it
been true, would have made the clamp exactly the detail thief it was accused of
being.

`hullband.py` weighted each band by its coefficient count: `w = a.size`. A
decimated coefficient at level *k* upsamples to cover 4^k full-resolution pixels
on reconstruction, so each band's contribution to full-resolution energy is
constant-N, not N/4^k. The line under-weighted band *k* by exactly **4^k** --
4096x at the residual. Every fine band was flattered and every coarse band was
buried.

BUILD-HULL caught it. I confirmed it against a construction whose answer is
fixed by definition rather than measured, in `check_hullband_weight.py`:

```
true coarse %  shipped says  corrected says  shipped error
       99.75%         8.88%          99.75%         90.87
       99.00%         2.36%          99.00%         96.64
       80.00%         0.10%          80.00%         79.90
worst absolute error, shipped   : 96.64 points
worst absolute error, corrected :  0.00 points
```

A difference that is **99.75% coarse by construction** was reported by my code as
8.88% coarse. Corrected on the real pair, bands 0-1 fall from **88.8% to 16.8%**
and the residual rises from **0.11% to 45.14%**. BUILD-HULL's independently
written implementation returns 16.8% and 45.14%. Two implementations, two
authors, the same two numbers.

**The first version of my confirmation failed to reproduce the bug.** I tested
pure-coarse and pure-fine inputs, every candidate weighting scored them
correctly, and the script printed `NOT CONFIRMED` on a defect that was entirely
real. When all the energy sits in one band, any positive weighting recovers the
right answer; the error is a *ratio* error and needs at least two bands occupied
before it can express itself.

> **A degenerate case is not a control; it is a test that cannot fail.** Build
> the case where the quantity is spread, and fix the ground truth by
> construction rather than by measuring it.

### 60.4 What the broken instrument actually cost

Not just a wrong number in a report. My own percentile table had said, hours
earlier, that the clamp shifts **p1 by +137 DN, p25 by +208 DN, p50 by +2 DN,
and p99 by 0 DN** -- a floor lift that decays to nothing by the midtone and is
exactly zero at the highlight. That is a tone operation. That is the correct
answer, it was sitting in my own notes, and I **discarded it because the band
split contradicted it**.

The corrected split -- 45.14% of the change in the residual -- says the same
thing the percentiles had been saying all along. I had two instruments agreeing
and I threw away the one that was right, because the one that was broken was the
one that spoke in the units of the question.

> **An instrument that contradicts a hypothesis is not thereby evidence against
> the hypothesis.** Check the instrument before you discard the idea. This is the
> eighth instrument failure of the run and the first that destroyed a correct
> conclusion rather than merely producing a wrong one.

### 60.5 The fleet correction

Both numbers were retracted to all fourteen running agents in a single message,
with an explicit request for one paragraph back *only* where a reported
conclusion rested on a retracted figure -- not a general re-run, which would have
cost the night.

The cost was concentrated and real. BUILD-GHOST had deferred a port on the stated
grounds that a "free 15% recovery" upstream appeared to dominate its own
workstream. That reasoning was void, and the deferral with it. BUILD-SHARP
withdrew a section. The reversal that matters most is in the ranking: with no
free 15% sitting above it, the demosaic's measured **1.297x at f_out = 0.35** is
no longer competing against a larger free win -- it is now the largest measured
ring-free sharpness lever on the board, and it moved from a measurement to a
build order on the strength of the retraction alone.

**The timeline is worse than "I failed to read a retraction", and I only found
that by checking it.** My first draft of this section accused me of relaying a
number that its author had already withdrawn. The commit times refute that:

| time | event |
|---|---|
| (before 08:01) | I broadcast **15.5%** to the fleet |
| **08:01:20** | `63fc9fea` -- **my own section 58.4 records ~3%**, from my own measurement of the matched pair |
| 08:23:53 | `ba5f2346` -- BUILD-HULL retracts its own figure |
| 08:39:17 | `6222142e` -- V-HULLCOST independently confirms 3.1% |
| 09:15:27 | `c99486d4` -- BUILD-HULL catches my band-weighting inversion |
| **09:22:24** | `e570b95e` -- **I finally correct the fleet** |

I did not fail to read someone else's retraction. I **wrote the correct number
into my own research document at 08:01 and left fourteen agents holding the wrong
one for eighty-one minutes**, during which at least one of them made a planning
decision on it. The corpus was right the whole time. The people were not.

> **Correcting the record is not the same as correcting the people.** A document
> is a place where a number goes to be right; a broadcast is a place where it
> goes to be acted on. Fixing the first and not the second leaves every decision
> already made on the bad number standing, and it does so silently, because the
> corpus now reads as though nobody was ever misled.

The general rule survives in a stronger form: **never broadcast a number you
have not measured yourself, and when you do measure it, push the correction to
everyone you sent the original to -- in the same act, not the same session.**

### 60.6 Two verdicts per subject, because there are two questions

Cross-checking my print verdicts against BUILD-TRIAGE's numerical classification
turned up three subjects we disagreed about -- `tweezers-cpl`, `leaf-2-cpl`, and
`flower-bud-with-background-fern-cpl`, which I had called print-worthy and TRIAGE
had called capture-limited. Neither of us was wrong. I was answering *is the
merge doing damage where the subject has structure*, examining crops at 1:1.
TRIAGE was answering *does the bracket cover the subject*, over 64 sites.

A subject can be flawless everywhere it was sampled and still have a coverage gap
elsewhere in the frame.

> **A verdict on a crop and a verdict on a frame are different claims**, and
> collapsing them into one field forces a false choice between them.

The gallery now carries both, colour-separated, and the disagreement became the
most useful thing on the page: **retouch this** versus **reshoot this** is the
distinction a working photographer actually needs, and it exists only because two
instruments pointed at the same subject and returned different answers. The
project has spent the night treating disagreement as a defect to be resolved. It
is sometimes a product feature.

The tally across 26 subjects: 12 good, 10 with coverage gaps, 4 with motion.

### 60.7 Motion and exposure, finally measured rather than asserted

The README had claimed the captures show no motion and no exposure drift. It was
a claim I wrote and never measured. BUILD-GHOST measured it, and the verdict is
**substantially right, for the wrong reason, with one real exception**:

- 22 crops at 1:1 across 15 subjects, **zero visible ghosting**. The partition is
  stated honestly as 15 viewed and 11 not viewed, summing to 26 -- a count that
  cannot be read as coverage it does not have.
- The apparent half-stop exposure ramps are not exposure at all. They are
  **magnification from focus breathing**: `ln flux = -2 ln scale`, no free
  parameter, permutation p = 0.0025, up to 5.06x RMS reduction when the model is
  applied. Adjacent-frame residual after that is 0.003 to 0.006 stops.
- **`foam` is a genuine exception**: 0.32 stops within 8 frames, with EXIF that
  does not corroborate it. Photometric normalisation does not exist on the
  default pyramid path, so this one is deferred rather than fixed, and it is
  recorded as deferred rather than quietly dropped.

The residual is a **lower bound**, and the agent said so unprompted -- the
estimate is biased toward the README being right. That disclosure is worth more
than the number.

### 60.8 The under-resolved category is empty, and the statistic that filled it is discredited

Two subjects, `119MSDCF` and `109MSDCF`, had been recorded as "genuinely
under-resolved, last of 26". Opening them refuted it: both are sharp wherever the
subject has structure. Retracted.

That is the **third** retraction sourced from the same detail-ranking statistic,
after `flowers-cpl` and `flower-inner-edge-cpl` -- and it stayed wrong even after
contrast normalisation, which was the fix applied the first two times. Every one
of the three was a subject with little structure, not an output with little
sharpness.

> **The detail ranking measures the subject, not the tool.** It has now produced
> three wrong verdicts and zero right ones. Do not rank sharpness by a detail
> statistic without opening the image. Normalising it does not repair it, because
> the defect is in what it is a statistic *of*.

No subject in the corpus is currently believed to be under-resolved by the merge.

### 60.9 Where this leaves the softness question

Three candidate explanations entered the night. The clamp is **exonerated** at
0.1 to 0.4 sigma. The merge is **exonerated** by BUILD-TRIAGE at a worst deficit
of 0.49 px against a 0.80 px threshold, though that classification has a zero in
it and a zero is under suspicion until its detector is shown to be potent.
Demosaic is **the survivor**, at a measured 22.9% loss per axis at f_out = 0.35
with an oracle bound of 1.297x, and it is the only one of the three that is now a
build rather than an investigation.

Two of the three suspects were cleared by measurement that contradicted the
people who nominated them, including me. That is the process working. It is also
the reason the third should not be trusted until someone who did not measure it
tries to kill it.

## 61. The dark feature that was never dark

I spent part of this night telling fourteen agents that the shipping product had
a measured quality fix switched off. It did not. The fix had been on the whole
time, and one command would have told me so.

### 61.1 What I claimed, and how I got there

`scripts/check-defaults.py` is mine. It audits every `STREHL_*` runtime switch
found in `crates/` against a hand-maintained registry of what each one defaults
to. It returned `rc=1` with a headline I took straight to the fleet: three
quality switches defaulting off, twenty-two of twenty-six defaults never
verified by anyone. Top of the list was `STREHL_FIX_CA`, annotated in my own
registry as **THE ORIGINAL DARK FEATURE** — a lateral chromatic aberration
correction measured at 61-67% of corner colour fringing removed, `R^2 = 0.9969`,
and blue displacement from 0.363 px to 0.059 px.

I then pulled SHIP-V2's provenance block and found what looked like
confirmation:

```
strehl.exe stack "D:\personal\macro\pencil-steep-angle-cpl" --out ...
  --merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure
```

No `--fix-ca`. I concluded that every master the owner had looked at was
rendered with that correction switched off, and I said so.

### 61.2 What the binary says

Running the shipping binary on the shipping flags, with the flag absent, exactly
as the provenance line describes:

```
$ strehl stack D:\personal\macro\bee-3-cpl --srgb --auto-exposure --limit 6
camera          : ILCE-7CM2
lateral CA      : CORRECTING, profile "a7c2-fe100gm-2xtc-x4cpl"
                  (gear matched; default on)
```

`rc=0`. The correction is default-on, resolved through a gear guard that reads
the body and composed lens id out of the file and declines on a mismatch —
because applying this profile to a different optical path would add an
aberration rather than remove one. `stack --help` says the same in prose. The
absent flag meant the default applied, and the default was on.

The masters had the correction. There was no dark feature. Two agents were
working on promoting something that had already shipped.

> **An argv records what the caller said. Only the run's own banner records what
> the program did.** An absent flag is not an absent behaviour; it is a
> delegation to a default, and reading the argv tells you nothing about which
> way that default fell. This is the third time this run I have inferred a
> measurement instead of taking one, and the cheapest of the three to have
> avoided: the answer printed itself in one line.

### 61.3 The structural defect underneath, which is the more useful finding

Strip that error away and the registry still called two more switches dark:
`STREHL_PHOTOMETRIC` and `STREHL_FIX_HALO`. The same run refutes both, by
omission. Its banner names the merge backend, the CA state and the alignment —
and says nothing whatever about photometric gain or halo correction, because
those are **estimator-path stages and the default backend is the pyramid**. The
pyramid arm's own report has been listing them under `not applied` the entire
time.

So the registry had no notion of *which backend a switch reaches*, and therefore
reported estimator-only stages as dark defaults of a product that never runs
them.

> **Absent and off are both "the product does not apply this", and they have
> opposite remedies.** A dark switch is a flag to flip and costs a decision. An
> absent stage is a thing to build and costs a milestone. A checker that returns
> the same word for both sends people to flip a flag that changes no pixel.

The fix adds a `backend` field — `any`, `pyramid`, `estimator` — defaulting to
`any`, so that **forgetting the field gets a switch checked rather than
excused**. The permissive value has to be the one that gets examined, or the
omission becomes the loophole. Switches that cannot run on the default path now
get their own named, counted bucket in the partition rather than being dropped:
a skipped check must never print the same glyph as a passed one.

### 61.4 Commissioning the field that could hide the defect

The `backend` field is also a new way to silence a check: any genuinely dark
switch can now be excused by declaring it estimator-only. A field that can
silence a check has to be shown load-bearing in both directions before it is
believed, so `experiments/ORCH-drift-check/commission_backend.py` plants both
against the live file, anchored on a unique three-line block that the harness
asserts occurs exactly once and hard-errors if it does not.

| arm | plant | required | result |
| --- | --- | --- | --- |
| A | dark switch, `backend=any` | still caught as dark | dark 0 -> 1, section printed, switch named — **PASS** |
| B | same switch, `backend=estimator` | reported, counted, **not** dark | dark 0 -> 0, not-on-default 2 -> 3, named — **PASS** |

2/2, restored from a `$TEMP` pin and verified byte-identical to the file as
found. The corrected audit now reads **`dark = 0`**: there are no dark quality
switches on the shipping path. The count that survives is `assumed = 21`, which
is a real and separate debt.

### 61.5 What CA actually does, measured on the worst subject for it

Knowing the default is on turns an open item in my print verdict into a
two-render experiment. `foam` is dark cellular plastic with blown specular
highlights — maximum contrast at a hard edge, the worst case for lateral CA —
and its highlights carry visible orange, cyan and magenta rims. Foam also has
thin films, and thin-film iridescence is a real optical effect, so the colour
alone proves nothing. But the two have different geometry, and geometry is
falsifiable: lateral CA is zero on axis by construction and grows with radius.
Iridescence has no such rule.

One binary, one subject, one flag changed. Mean `|R-G|` and `|B-G|` at strong
edges, normalised by local green, in six radial bands. The edge mask is found on
**green**, so it cannot be created by the very colour difference being measured:

| band | | R−G on/off | B−G on/off |
| --- | --- | --- | --- |
| 0 | **centre (the null)** | **1.003x** | 0.996x |
| 1 | | 0.946x | 0.999x |
| 2 | | 0.925x | 0.973x |
| 3 | | 0.895x | 0.985x |
| 4 | | 0.812x | 0.955x |
| 5 | **corner** | **0.758x** | 0.988x |

Monotonic in radius, with the centre untouched at `1.003x`. That is the
signature, and it is not a signature a level shift can fake: 24% of corner
red-green edge colour removed while the frame centre is left exactly alone.

The answer to the original question is therefore **no** — foam's rims are not
lateral CA. That is already corrected on the default path.

### 61.6 The part where I had to correct myself again, one hour later

I ran this first on an `--srgb` render and read the corrected residual as
**flat** across radius, which would have meant nothing but demosaic and noise
remained. Re-run in `--linear-srgb`, which is the mode this project's own rule
says to measure in, the residual is **not** flat: the corner sits at `0.1006`
and `0.1262` against the centre's `0.0870` and `0.0672`, and the blue-green
residual is barely touched by the correction at all (`0.988x`).

The transfer curve had compressed exactly the quantity I was measuring, and it
did not merely shrink the effect — it changed the shape of the conclusion. The
`--srgb` run also understated the correction itself, `0.865x` against `0.758x`
at the corner.

> **A non-linearity does not just scale a result, it can flatten a structure you
> were reading as the finding.** The standing rule against measuring on an
> `--srgb` render exists for this, and I broke it while running an experiment
> designed to be careful about geometry.

So a substantial non-radial colour residual survives at the corner and lateral
correction cannot touch it. Three candidates remain open, in order of my
confidence: longitudinal chromatic aberration, which BUILD-CHROMA is measuring
and which has no radial signature; clipping, since foam carries 0.76% blown
pixels and the channels do not clip together; and iridescence. I am not
asserting which. What I can now say is that the one explanation I could test has
been tested and eliminated, which is more than the entry started with.

### 61.7 And the item I got wrong in the opposite direction

Having retracted two false alarms, I told the same two agents that the surviving
real gap was the pyramid's absent outlier rejection, and that it was the one I
would rather they were looking at. The first half is verified: `pyramid.rs` is
106.4 KB and contains zero matches for `outlier|robust|reject|mad_`. The second
half I had not checked. BUILD-GHOST had already closed it — 17 crops at 1:1
across 13 subjects, zero visible ghosting including bee setae on white and
printed text, largest detection 1.90x over a rigid-subject floor. It was sitting
in the acceptance ledger in state DONE with its evidence attached, one query
away.

The correct status is **deferred, not dismissed**: a known architectural gap,
measured not to bite on the captures in hand, which will bite the first user who
stacks a leaf in a draught. That is the good kind of deferral, because there is
a measurement behind it.

> **Assigning a priority is a claim, and it needs the same evidence as a
> number.** I retracted two claims and then, in the same message, made a third
> one of exactly the kind I had just apologised for.

## 62. Four ways a number survives review, all found in one night

Tonight produced four corrections and they are the same shape. In every case a
number was correct, its label was wrong, and nobody caught it because the label
and the number were read together by people who already believed the label.

### 62.1 The backend trap: a flag that changes what you measured

`strehl merge` infers the estimator backend from any estimator-only flag. So a
harness passing `--gate 2` **without** `--merge` silently gets the estimator,
prints `merge backend : estimator (inferred from --gate)`, and produces a number
the author will file under whatever backend they meant. The binary reports this
pattern at **338 call sites across 185 files**.

Verified directly: `--merge pyramid --gate 2` exits 1 with *"--gate belongs to
the estimator merge"*; `--gate 2` alone runs and infers.

The consequence found: the README's central performance table — every `gate`
row, plus argmax and plain mean — is an **estimator** measurement, and there is
no row at all for the pyramid that actually ships. The likely reason is
mechanical rather than careless: the pyramid *refuses* `--flat-roi`,
`--detail-roi`, `--stats` and `--n-eff-map`, so **the tool cannot measure its own
shipping backend with its own instrumentation.** A table gets written about the
backend that answers questions.

The rule: **infer a backend from a banner, never from an argv.** When I checked
the detail-null arms this way they came back clean — all six print `merge backend
: pyramid (default)`, argv was `stack <src> --out merge.tif` and nothing else,
and the string `inferred from` appears nowhere in the render tree. The check is
cheap and it is the only thing that distinguishes the two cases.

### 62.2 A ceiling that could only return one number

BUILD-SHARP published a 1.297x "oracle headroom" on demosaic reconstruction.
V-DEMOSAIC called it a tautology. I confirmed it without running any of their
code, from the six published rows alone:

```
f      malvar   1/malvar   published headroom   |d|
0.20   1.0604    0.9430    0.943                0.00004
0.25   1.0000    1.0000    1.000                0.00000
0.30   0.9058    1.1040    1.104                0.00000
0.35   0.7713    1.2965    1.297                0.00049
0.40   0.6228    1.6057    1.606                0.00035
0.45   0.5385    1.8570    1.857                0.00001
```

**The headroom column is `1/D_malvar` at every row.** The ceiling arm contributed
the constant 1.0000 everywhere, so the table measures Malvar's loss and then
*asserts* the recoverability that was the whole question. The oracle returns
1.0000 even at `|fx|+|fy| = 0.70`, outside the quincunx support, and returns
0.0000 on a spread case whose truth is 1.0000 — its output tracks whether a
single tone is present, not whether information is recoverable.

Two things worth keeping. First, **a ceiling arm that returns the same number at
every operating point has not been commissioned** — it was never shown able to
return anything else. That is the same defect class as the two focus statistics
killed earlier by their own commissioning, and as `hullband.py`'s inverted
weighting. Third instance this week.

Second, and this is the part that matters for shipping: **the number was wrong
and the direction was also wrong.** Measured on real data the gain is ~1.10x
(mean 1.099 over 8 stacks, 1.045 over all orientations) — but Hamilton-Adams is
*worse* than Malvar off-axis, 0.650 at fy=0.20, and loses outright on
`lead-1-cpl` at 0.991. A wrong magnitude ships a disappointing picture. A wrong
sign ships a worse one.

### 62.3 The retraction I had to make about my own finding

I read `foam`'s coloured highlight rims as a blue radial term the CA correction
was leaving behind. BUILD-CHROMA refuted it with a magnitude argument: their
mechanism predicts 0.55–0.85% centre-to-corner elevation and I had measured
87.8%, a gap of 103–160x. I accepted it.

**A direction agreement between two instruments is worth approximately nothing
when one can predict a magnitude and the other has measured one.**

The true cause turned out to be neither optics nor my term: **channel-asymmetric
highlight saturation**. Green's ceiling is 38921 against blue's 52239, so green
pins first and bright pixels acquire a one-sided blue excess. `B/G` climbs
monotonically 1.0257 -> 1.2903 across nine level deciles, which a fixed
white-balance gain cannot do. Dropping the top 0.76% of luminance collapses
corner/centre 1.878 -> 1.031 while removing the same *count* at random leaves it
at 1.856 ± 0.088 — 7.6 sd, so it is which pixels, not how many. The apparent
radial pattern was **composition**: the corner band is 51.99% highlights against
the centre's 0.68%. Two of us chased a sampling artifact as a field effect.

BUILD-CHROMA also caught themselves: their first gate thresholded on fractions of
65535 when the master's maximum is 52239, removed **zero** pixels, and printed
*"the elevation survives"*. **A threshold expressed as a fraction of a nominal
maximum is a trap when the real maximum is lower.** Two controls had already
caught it and the verdict logic never read them.

### 62.4 The claim that measured the other end of the range

The README asserted **"Highlights are not clipped by the merge"** and supported it
with three numbers, every one of them a count of exact-**zero** pixels. It proved
the shadow end and claimed the highlight end. Nothing in it was false; only the
sentence above the evidence was about a different quantity.

Measurement points the other way: on the pyramid arm, pixels pinned at the
container maximum run 4.65% frame-wide against the estimator's 1.87%, and 20.48%
against 0.0952% within one band.

And the tool cannot see it on the path that ships. `report_clip_census` is
documented as *"Always reported, not hidden behind `--stats`, because a clipped
pixel is a correctness question rather than a diagnostic one"* — and
`run_pyramid` states *"No clip census, no outlier rejection, no halo
correction"*, printing the same at runtime. Nothing is concealed. It is the gap
between two individually correct decisions, which is the kind that survives
review. But *"none of them is what this arm is"* is a good argument about
**estimation stages** and a weak one about a **counter**: counting what you
pinned is not an estimation stage.

**So the one measurement this codebase singles out as a correctness question is
the one the default path does not make.**

### 62.5 What the null actually said, which was friendlier than it sounded

The project's headline `~1.2–1.8x` detail gain is **not observed** — six
subjects, 36 matched sites, two arms indistinguishable to within 0.5 px of
equivalent blur, which is also the instrument's own floor. Selection wins
outright on the planar subject.

Then I opened the crops, and the null inverted. On `flowers-cpl` the merge
renders smooth continuous defocus where argmax **shatters it into hard-edged
plateaus** in a region containing no real structure; on `bee-3-cpl` argmax smears
ghost-hairs into clean white ground. **A detail statistic scores invented edges
as detail.** Argmax ties by manufacturing structure.

Gradient kurtosis in low-detail regions, on sites chosen from the mean of both
arms:

| subject | merge | argmax | ratio | geometry |
|---|---:|---:|---:|---|
| `bee-3-cpl` | 5.83 | 16.26 | **2.79x** | deep, defocused ground |
| `flowers-cpl` | 3.90 | 7.71 | 1.98x | 3D |
| `bee-1-cpl` | 7.85 | 14.81 | 1.89x | 3D |
| `leaf-2-cpl` | 3.52 | 5.54 | 1.57x | 3D |
| `tweezers-cpl` | 4.25 | 4.97 | 1.17x | near-planar |
| **`flat-on-ruler-cpl`** | 4.44 | 4.51 | **1.01x** | **planar** |

**The table explains its own exception.** The single subject where argmax beat
the merge on detail is exactly the one where it invents nothing — a plane, where
selection is well-posed. Published as descriptive, not pre-registered: the
per-subject cut was made after seeing per-tile data.

The defensible claim is narrower than the one that was retracted, and it is
true: **the merge's advantage is noise and the absence of invented structure,
not fineness.**

### 62.6 The print survey finished, and finishing made it weaker evidence

All 26 subjects opened at 1:1. Twenty-four print-worthy, two limited by the
capture rather than the stacker, **zero merge defects anywhere**. The category
"not individually judged at 1:1" is now empty because the survey finished, not
because the standard moved.

That completion cuts the other way and the README now says so. **A complete zero
is a larger claim resting on less support per subject.** Twenty-six inspections
by a single non-blind observer who expected to find nothing is the exact shape of
a result that should be distrusted. What would settle it — a second party opening
the same tiles blind, or a defect planted in a render to prove the survey can
return one — has not been done.

The verifier had to change with it, and the change had to be a **stronger** rule.
`verify_gallery.py` checked `opened == print-worthy`, which was right only while
every examined subject passed. Now 26 != 24. The weak fix is to stop comparing
them. Instead the difference must be discharged by **naming** every subject that
was opened and did not pass, the stated opened count must equal the cards
rendered, and a named non-pass may not also appear in the pass list. Then
commissioned: null arm clean, **6 planted, 6 caught, 0 missed** — including the
two new rules, so their green means something.

`commission_counts.py` earned its keep before that: it **refused to run** rather
than pass, hard-erroring `MUTATION TARGET NOT FOUND ... anchor matched 0 times`
when the prose it plants into had changed. A commissioning harness that silently
no-ops is worse than none, because it prints a green.

### 62.7 The one sentence

Every defect in this section is a **label attached to a real number**: a backend
name, a ceiling column, a radial term, a heading about highlights, a comparative
adverb in a shipped JSON that says "0.88x less pixel noise" where 0.88 means
*more*. None was a computational error. **The arithmetic was right every time.**

So the guard cannot be "check the maths". It has to be: *derive the sentence from
the measurement rather than writing it alongside* — and when the two are
separated by even eight lines of correct reasoning, as `triage.py`'s FLAT-only
policy was from the all-sites average that violated it, they will drift.

## 63. The night the measurements and the product were found to be different products

Two facts sat next to each other tonight and looked like a contradiction. This
corpus has sixty-two sections of measurement discipline, plants that express the
failure they test for, placebos, pre-registration, and a standing refusal to let
an author verify their own work. And the owner's verdict on the output was
*horrible*.

They are not in tension. They have one cause, and I found it four separate times
in one night, each time by accident while chasing something else.

**The configuration that gets measured and the configuration that ships have
drifted apart.** Not once, as an oversight. Four times, in four independent
subsystems, by four different mechanisms, with nothing in the product's own
output that would tell anyone.

### 63.1 The verdict: "state of the art" is not defensible

V-HEADTOHEAD ran strehl against the prior `focus-stack` fork and against Zerene
PMax. Grade removed, 626 and 576 ROIs, tight intervals, both comparators
agreeing in direction.

- **We lose 17–23% to the fork and 16–27% to Zerene PMax at 3–5 px features.**
- We win decisively elsewhere: high-pass rms **0.5025% → 0.1125%, a 4.5×
  reduction**, holding at ≥2.4× under worst-case grade correction; the fork
  clips **32% of the frame** where strehl clips **4e-6**; strehl is lower on
  **all four** rim measures.

What makes it credible is what they tried and failed to do with it. They went
looking for a way to explain the deficit away and could not: it is not capture
sharpening (`crs:Sharpness="0"` in both XMPs), and it is not a grade artifact —
removing the grade properly is what *produced* the numbers, and the naive
comparison would have handed the win to the wrong arm. They also disclosed
**three of their own instruments failing controls** and **two of their own wrong
numbers**, self-corrected.

I retracted the SOTA claim in the README the same night and published the band
table with the losses stated as plainly as the wins, plus three caveats bounding
even the *competitive* claim. A project that would rather be right than look
right has to be willing to print the number that costs it the headline.

### 63.2 The gallery describes a gate the product does not use

Chasing an unrelated BUILD-SPEED aside, I found that `SHIP-V1\bee-3-cpl.tiff`
reproduces byte-for-byte under `--pyramid-gate 4.5`, and **not** under the
compiled default of 2.0.

`SHIP-V1\` had preserved a log and no script. There was no argv to read, so the
provenance had to be *measured*: I rendered a second subject, `109MSDCF`, two
ways through the pinned binary and hashed both.

```
SHIP-V1\109MSDCF.tiff  322C6C4D135C0E9B3123B55FAF7FFE67C537D369C344ADA7463D439F9CEB0590
gate 4.5               322C6C4D...0590   identical
compiled default 2.0   7AACAF79...30CD   different
```

Two subjects, rendered by two different agents at two bracket depths, both land
on 4.5. **The entire 26-card print survey — my own headline quality result —
describes a configuration the product does not ship.**

I wrote the caveat blanket rather than narrowed. The detail-ROI ratio of 0.9945
suggests the findings probably do transfer to gate 2.0, but *probably* is not a
measurement, and the conservative direction is the one that does not need to be
retracted later.

### 63.3 A finished restoration stage nobody switched on

`STREHL_RESTORE` resolves through `gain_cap_from_env()`, which returns `None`
when the variable is unset. The call is guarded by that `Option` at **both**
sites — `run_estimator` and, decisively, **`run_pyramid`**. `pyramid` is the
default backend.

So restore is not a missing feature. It is a **finished stage that nobody
switched on**, on the path that ships. Its own doc comment says it "exists to
carry a measured trade curve to whoever sets the default."

Nobody set the default.

The default banner does not list restore under `not applied`. It does not
mention it at all — so no user, and no agent reading a banner, would learn the
stage exists.

This is also the reading that changes BUILD-SHARP's §24, which measured restore
**inert** when enabled. Alone that says the algorithm is weak. Next to "and it
is off by default on the shipping backend", a second reading opens that has to
be eliminated first: **a restoration stage that changes nothing when you switch
it on is more likely unwired than truly null.** I routed a potency arm — set an
absurd gain cap, hash against the unset render, and if the hashes match the
stage is not reaching pixels and the §24 null is an artifact of the harness.

### 63.4 The correction is absent exactly where the defect was measured

`STREHL_VEIL` defaults to `false` (`DEFAULT_VEIL_ON`), and its sole call site is
in `run_estimator`. It is therefore absent on the shipping backend.

Set that against BUILD-VEILMAP, which measured the veil signature as **localised,
not pervasive**: bimodality **0.324 on `bee-1-cpl`** and **0.199 on `bee-3-cpl`**
against a **corpus median of 0.007**. Their drift null passed four independent
ways, and their potency arm passed at 48/96/192 px and *failed* at 384 — which
they used to bound block size from above rather than quietly drop.

So the veil correction is switched off hardest precisely on the subjects where
the veil was measured to concentrate. `STREHL_FIX_HALO` is the same shape:
`Err(_) => false`, estimator-only, and the pyramid's own report lists `halo
correction` under `not applied`.

### 63.5 The shape

Four subsystems. Four mechanisms — a survey rendered at a non-default flag, a
stage guarded behind an unset `Option`, a constant defaulting to `false`, a
whole backend that the tool's own instrumentation refuses to measure (§62.1).
No two share a cause. Each, taken alone, is a defensible engineering decision
made by someone with good reasons.

Taken together they are one defect: **the product measured and the product
shipped are different products, and nothing in the product's output says so.**

This is the answer to the owner's complaint, and it is worse than a bad
algorithm. A bad algorithm shows up in the next measurement. This does not —
because the measurement is taken on the good configuration, and the render is
taken on the shipped one, and both are correct.

It also reframes the SOTA deficit in §63.1. We do not yet know whether strehl
loses 17–27% at fine detail, or whether *the default configuration of strehl*
loses 17–27% at fine detail while a configuration we have already built and
already measured does not. Those are very different findings and the corpus
cannot currently distinguish them.

### 63.6 The instrument, and its commissioning

`scripts/check-defaults.py` is the ratchet against exactly this. Tonight it went
from **7 undeclared switches** to **0**, its partition sums to **33 = the number
of switches found in `crates/`**, and every one of the six quality switches whose
default nobody had checked now carries `verified="code"` against the resolving
expression, read at source rather than inferred from a name:

| switch | resolving expression | default |
| --- | --- | --- |
| `STREHL_EDGE_AWARE` | unset falls in the **first** match arm | `EdgeArm::Acuity` — ON |
| `STREHL_EDGE_TAU` | derives tau from the guide field | per image, no constant |
| `STREHL_EDGE_CONF` | `env_num(..., 2.0)`, `Err(_) => default` | 2.0 |
| `STREHL_EDGE_FEATHER` | `Err(_) => FEATHER` | the constant |
| `STREHL_FIX_HALO` | `Err(_) => false` | off |
| `STREHL_WINDOW_RADIUS` | `Err(_) => WINDOW_RADIUS` | 13 |

Two of those readings corrected the declaration rather than confirming it.
`EDGE_AWARE` was filed as "on" when what is true is stronger — unset lands in
the first arm, so it is *positively* Acuity, not merely not-off. `EDGE_TAU` was
filed as `built-in`, which reads as a fixed constant; it is derived from each
image's own guide field and there is no constant to quote.

The gate that reports unexamined quality defaults did not fire. **That is only
good news if the gate can fire**, so I commissioned it: demote
`STREHL_WINDOW_RADIUS` back to `verified="assumed"` on an anchored, unique
multi-line string that hard-errors if it does not land, and require RED.

```
ARM A (clean)                                    gate fired: False
ARM B (one switch demoted to assumed)            gate fired: True, names it
                                                 code 13→12, assumed 15→16
restored, sha256 0d44c63e, match=True
```

The original was pinned to `$env:TEMP` and restored in a `finally` block — never
`git checkout --`, which reverts to HEAD and has already destroyed uncommitted
work on this machine.

The script is now **RED, deliberately, for exactly one reason**:
`FAIL: 1 quality switch(es) default to OFF` → `STREHL_RESTORE`. That is the
finding, not a bug in the checker, and I wrote into the registry `note` that
nobody may flip it on to clear the check.

### 63.7 The one sentence

Section 62 found four numbers whose arithmetic was right and whose labels were
wrong. This section found four **configurations** that were measured right and
shipped wrong, which is the same failure moved one level out: in both cases the
work was correct and the thing it was correct *about* was not the thing anyone
would use.

So the guard has to be the same shape too. Not "measure more" — this project's
problem has never been a shortage of measurement. It is: **every quality claim
must name the configuration it was measured on, and something automated must
fail when that configuration is not the one the binary runs by default.**

A measurement that does not name its configuration is not a measurement of the
product. It is a measurement of a product.



## 64. The out-of-box experience, measured -- and a shipped flag that reaches no pixel

Section 63 argued that the product measured and the product shipped are
different products. This section stops arguing and photographs it, and in the
course of doing so found a live defect that no amount of further merge work
would have fixed.

### 64.1 What a photographer actually gets [MEASURED]

One binary, one merge (`--merge pyramid`, `--pyramid-gate 2.00`, named in the
banner rather than inferred from argv), one subject (`109MSDCF`, 22 frames).
The only thing that varies is the render stage, so any difference is
attributable to it and to nothing else. Every rung is shown the way an ordinary
viewer shows a 16-bit file: values mapped linearly onto 0..255. That is the
whole transform.

| rung | resolution | mean luma | median | % near-black |
|---|---|---|---|---|
| **default -- what `strehl stack` writes** | 3516x2344 | **23.5** | 25.6 | **53.5%** |
| `--srgb` | 7032x4688 | 183.6 | 213.3 | 2.7% |
| `--srgb --auto-exposure` | 7032x4688 | 183.6 | 213.3 | 2.7% |

**The default output renders 53.5% of the frame as near-black and sits 7.81x
darker in mean luma than the same pixels rendered for viewing.** Opened side by
side, the default is a murky grey-brown image in which white paper reads as
dark grey and saturated marker strokes read as mud; the `--srgb` render of the
identical merge is brilliant white paper and clean saturated colour.

This is not a defect in the sense of a bug. The tool documents it exactly:

> By DEFAULT the output is BINNED, LINEAR, CAMERA-NATIVE RGB ... **It will look
> dark and grey-green in an ordinary viewer.** That is correct: it is what
> measurement needs.

It is correct, and it is the right default for the corpus, and it is the wrong
default for a photography tool. **The sharpness is identical in both rungs** --
the strokes, the graphite striations and the fine speckles are equally resolved
in the dark one. Nothing about the stack is worse. The owner's standing verdict
that the output looks bad has, at minimum, a large component that is not a
stacking result at all. It is a presentation default, and it is the first thing
anyone sees.

### 64.2 The finding that arrived uninvited: exposure reaches no pixel [MEASURED]

The third rung above should not equal the second. `--auto-exposure` printed

    exposure        : +2.61 stops (gain 6.105x), chosen from the image

and produced an image with the same mean luma to four significant figures. The
first comparison was weak evidence -- 0.331% of samples differing by a maximum
of **1 DN** -- and 1 DN is exactly the size of a benign explanation ("it chose
about zero for this subject"). That is how a defect like this survives
inspection.

So the arm was replaced with one that admits no benign reading: an explicit
`--exposure=-3.0`, a gain of 0.125x, an **eight-fold darkening**.

    differing samples : 0 / 98,898,048        max |diff| : 0 DN
    means             : 47807.7  vs  47807.7

while the banner reported, confidently:

    exposure        : -3.00 stops (gain 0.125x), as asked

**Neither `--exposure` nor `--auto-exposure` reaches a single pixel.** Measured
on the pin `b9b6921e` and again on the current build `C46BDF06A7136F54`, so it
is long-standing and live rather than a fresh regression.

And it is worse than a plain no-op. The two files are **not** byte-identical
(`96039D8E...` against `670E50C2...`) while **zero pixels differ**: the
requested exposure is being recorded in the file's metadata and never applied
to the image. The artefact carries a receipt for a correction it does not
contain.

This is precisely the failure the tool's own help text says it refuses to ship:

> A flag that parses and does nothing is indistinguishable from one that works,
> and this project has shipped that failure before.

### 64.3 Why the unit tests did not catch it

`strehl-core/src/color.rs` already contains
`zero_stops_normalises_to_no_exposure_at_all` and
`exposure_preserves_every_ratio_it_does_not_clip`. The exposure function is
fine. **What does not exist is a test asserting that a non-zero exposure
changes the written file.** An eight-fold gain can therefore evaporate between
a passing unit test and the artefact, and every green run agrees that nothing is
wrong.

A unit test on a function the pipeline cancels is not evidence about the
pipeline. It is the same shape as section 63's finding one level down: the thing
tested and the thing shipped are different things, and nothing automated
notices.

### 64.4 The rule this earns

> **A flag is not wired until an absurd value has visibly ruined the output.**
> Test potency with a setting no benign mechanism could absorb -- an eight-fold
> darkening, a gain cap of a thousand -- because a small measured difference is
> indistinguishable from a small correctly-chosen one, and that ambiguity is
> where dead code lives. The first arm here differed by 1 DN and would have been
> dismissed; the potency arm differed by zero and could not be.

Corollary, from the metadata split: **a provenance line is a claim, and it must
be generated from the value that reached the pixels, not from the value that was
parsed.** A banner printed before the work is a prediction, and this one was
wrong.

### 64.5 Standing

Routed to the owner of the wiring, with the reproduction, the potency arm, a
hypothesis about the cancellation point flagged explicitly as a hypothesis, and
a required deliverable that is not just the fix: an end-to-end gate asserting
the written file changes with exposure, **commissioned by planting the bug back
and confirming the gate goes red**. A gate nobody has seen fire is not evidence.

The out-of-box default is a product decision and is recorded here as one, not
taken unilaterally: the measurement path's byte-frozen output is load-bearing
for the entire corpus, and any change to what `strehl stack` writes by default
must make the old path **missing rather than different**, so that a harness
still expecting it fails loudly instead of silently measuring a tone curve.

## 65. The halo, verified by someone who did not fix it [MEASURED]

The owner's sharpest complaint about this project was not about noise or
sharpness. It was: *"you must tackle the halo situation. it's horrendous as is
-- the stacked photos are entirely unusable with them."*

The shipped help text claims the problem is solved, and states a number:

> Measured on `flower-bud-alone-cpl` through one binary with both arms
> camera-linear and one mask, the estimator's backdrop sits 4739 DN below its
> own far field across the 80-200 px aura zone; the pyramid sits 166 DN below.

That is the implementing agent's measurement of its own fix. The standing rule
is that an author does not verify their own work, so this is a separately
written instrument run on separately produced renders, built so that it could
fail to reproduce the claim.

### 65.1 The first instrument was wrong, and its own control said so

The first version controlled for lens vignetting by planting a fake disc of
equal area at the background pixel furthest from the subject. That pixel is the
frame **corner**, so the fake disc's far field is a different population from
the real one -- 13,891 DN against 18,696 DN, because from the corner the "far
field" contains the dark subject itself. The control read **+5,908 DN** where a
sound one reads about zero, and the control-subtracted verdict it produced was
meaningless. It is withdrawn.

Recorded because the control is the only reason that verdict did not ship. An
instrument whose control reads +5,908 DN is not a strict instrument; it is a
broken one that happened to be caught.

### 65.2 The corrected design needs no planted disc

Both arms come from ONE binary, each at its OWN default -- `--merge estimator`
with no `--gate`, `--merge pyramid` with no `--pyramid-gate` -- which is also
the before/after a user experienced when the default flipped. Both are
camera-linear default output; never `--srgb`.

Both are measured through ONE shared mask and ONE shared distance transform,
built from the MEAN of the two arms so it cannot be drawn to favour either.
Therefore every geometric confound -- vignetting, illumination falloff, mask
placement, band population -- is identical in the two arms and **cancels exactly
in their difference.** The primary statistic is the paired difference per
distance band, and it carries its own control: an aura is local, so the
difference must decay to zero far from the subject. Vignetting does not decay
with distance from the subject. A mask artefact does not. An aura does.

| band (px) | estimator | pyramid | **difference** |
|---|---|---|---|
| 0-20 | -15240.5 | -15476.9 | +236.3 |
| 20-40 | **-3168.0** | **-9.7** | **-3158.3** |
| 40-80 | **-3014.2** | **+485.9** | **-3500.1** |
| 80-200 | -428.7 | +645.8 | -1074.5 |
| 200-400 | +412.2 | +487.3 | -75.1 |
| **400-800** | +347.7 | +350.0 | **-2.3** |

**The far-field difference is -2.3 DN.** The built-in control passes: the
disturbance is local, by a ratio of **1497x** between the worst near band and
the far field. The estimator depresses the background by about 3,000-3,500 DN
in the 20-80 px annulus around the subject; the pyramid, in the same annulus
through the same mask, reads -9.7 to +486 DN.

A second control mirrored the distance transform horizontally, preserving every
radial property of the lens while destroying the correspondence between mask and
subject. It does **not** null cleanly -- it reads -508 to -740 DN in the near
bands -- and the honest reason is that this subject occupies 21.5% of the frame
and is roughly centred, so its mirror still substantially overlaps it. The
mirror is therefore a floor rather than a null. **The aligned signal is 4.7x
that floor**, and both decay to about zero at 400-800 px.

### 65.3 And then the picture, because a profile is not a picture of a halo

Both arms cropped at the same silhouette edge, through one identical linear
stretch computed from the pooled range so that neither arm is flattered.

The estimator shows a bright, blobby, **faceted white rim** tracing the
silhouette -- the "cut-out sticker" artefact, plateaus and all. It is
immediately obvious and it is disfiguring; it is what the owner saw, and
"entirely unusable" is a fair description of it.

The pyramid, same subject, same binary, same crop, same stretch: **no rim.**
The trichomes along the bud's edge are individually resolved against a smooth
background that simply continues to the frame edge.

### 65.4 Verdict

The claim is **reproduced in sign, in structure and in order of magnitude** by
an independently written instrument on independently produced renders, and
confirmed visually. The magnitudes differ from the help text's (-3,500 against
-4,739; the annulus and the mask differ, and this render is on the binned grid)
but the finding does not depend on them.

**The halo is fixed, and the fix is not the author's word for it.**

What this does not say: it is one subject, chosen because it is the one the
claim names. Section 63's discipline applies -- this is a measurement of a
configuration, and the configuration is `--merge pyramid` at its default gate,
which is what ships. That much, at least, is now the product rather than a
product.


## 66. The whole corpus, re-rendered from one binary, and looked at

Twenty-six subjects, 4825 frames, rendered in 27.8 minutes from a single pinned
executable (`C46BDF06A7136F54`) at `--merge pyramid --pyramid-gate 4.5 --srgb`.
Twenty-six succeeded and none failed. Every render kept its own `.err` sidecar
and the log records the binary's hash on line 2, so this gallery can be
reproduced, which is the thing `SHIP-V1` could not do.

I then opened fifteen of the twenty-six at 100%. Not thumbnails, and not a
ranking statistic: actual pixels, chosen by high-frequency energy so the crop
lands on the finest texture in the frame rather than on its strongest edge. An
edge has a 1/f spectrum and wins a gradient contest while containing no fine
detail, which is how a crop selector ends up proving that the tool renders
edges.

What fifteen subjects show:

- `bee-1-cpl` resolves individual plumose hairs on the leg, each with its own
  branching, against a bright background -- the exact geometry that produces a
  halo -- with no rim.
- `leaf-2-cpl` puts a leaf edge against flat grey, the textbook occluding
  boundary, and draws no rim either. Individual epidermal cells are resolved
  inside it.
- `112MSDCF` resolves dendritic filaments to single-pixel tips against a black
  field that stays black. No veiling into the shadow.
- `coffee-bean`, `pencil-steep-angle-cpl`, `tweezers-cpl`, `couch-fibers-cpl`
  hold microcontrast at the limit -- surface pores, graphite facets, machining
  striations, deep inter-fibre gaps.
- `lavendar-cpl` is thousands of overlapping trichomes, the worst occlusion case
  in the corpus, and it is clean.

One subject is not like the others. `flower-bud-alone-cpl` is visibly soft
against the rest, with a milky veil over the green surface, and it carries a
magenta fringe where the bud meets blown-out white. It is also the subject
`V-bestframe` scores worst, at a median merge-to-best-frame ratio of 0.82. The
number and the appearance agree, which is the first time in this project that a
quality statistic and my eye have independently pointed at the same subject.
That agreement is worth more than either alone: a statistic nobody has looked
behind is a rumour, and an impression nobody has measured is a mood.

The deficit belongs to alignment resampling, which is owned and quantified at
17--27%, not to the merge. Two things ride on the same subject and should not be
conflated with it: the highlight is clipped, and clipped highlights are where
every colour reconstruction is worst; and the fringe is at a f/2.8-class
boundary, which is lateral chromatic aberration and a lens property before it is
a stacker property. Neither excuses the softness. Both mean the subject is a
compound case and the resampling fix should be measured on it *and* on a subject
that is not fighting three things at once.

The rule this earns, and it is the counterweight to every rule above about not
trusting your eye:

> A quality metric and a visual survey are two instruments, and the useful
> event is when they *disagree*. Fourteen subjects where they agree tell you the
> metric works. The fifteenth, where they agree on a defect, tells you where to
> spend. A metric that has never been checked against an opened image has not
> been commissioned -- it has only been computed.


## 67. Which flags reach a pixel: the accident, made systematic

> **CORRECTED, 2026-08-26, and the correction is larger than the finding.**
> Three of the four gates this section reported as reaching no pixel were
> **my instrument's failure, not the program's**. `STREHL_SMOOTH` moves
> **96.39%** of samples at `off`; `STREHL_RESTORE` changes `tweezers-cpl`
> outright and banners four gain lines. Only `STREHL_ROBUST_ELECTION` survives,
> and it only corroborated M126. The corrected table and the mechanism are in
> **§68**, which should be read as part of this section rather than after it.
> `scripts/check-defaults.py` is **not** retracted: its subject is real,
> reachable, and genuinely off by default.


Three features of this tool have now been found to be documented, banner-reported,
tested, and inert:

| feature | found by | how |
| --- | --- | --- |
| `--exposure` / `--auto-exposure` | me, §64 | an 8x darkening moved 0 of 98,898,048 samples while the banner said it was applied |
| `STREHL_ROBUST_ELECTION` | M126 | constants quoted correctly in a report; the code never executes |
| `outlier.rs` | M126 | referenced only by `lib.rs:23`; reachable solely from `examples/` |

All three were found **by accident, by parties looking for something else**. That
is the finding. Three independent accidents is not three accidents; it is a
detection rate, and it implies a population. Finding them one at a time, when
somebody happens to trip over one, does not scale and cannot be reported to a
user as a level of assurance.

`scripts/check-potency.py` is the accident made systematic. One rule:

> A flag is not wired until an **absurd** value has changed the output.

Absurdity is doing real work in that sentence. A *small* measured difference is
indistinguishable from a small correctly-chosen one, and that ambiguity is
precisely where dead code survives review. Eight stops, a gate of zero, one
pyramid band: the only reading that cannot be explained away is a difference of
nothing at all.

### The audit judges itself before it judges anything else

Three probes exist only to license the other eleven, because an audit that
reports "all dead" because the renderer crashed is indistinguishable from an
audit that found a catastrophe:

| control | probe | required | measured |
| --- | --- | --- | --- |
| NULL | baseline against itself | byte-identical | byte-identical |
| POSITIVE | `--pyramid-gate 0.0` | must read LIVE | LIVE, 96,397,031 samples, 97.47 % |
| NEGATIVE | `--exposure=-6.0` | must read inert | 0 differing samples |

### Results, one binary before the highlight fix and one after

Fourteen probes, `109MSDCF`, 8 frames, `--merge pyramid --srgb`, banner backend
`pyramid (--merge)` confirmed on every arm.

| probe | pre-fix `C46BDF06` | post-fix `71C0F627` |
| --- | --- | --- |
| `--pyramid-gate 0.0` | LIVE 97.47 % | LIVE 97.47 % |
| `--pyramid-bands 1` | LIVE 97.19 % | LIVE 97.19 % |
| `--pyramid-exponent 0.01` | LIVE 97.13 % | LIVE 97.13 % |
| `--pyramid-sharpen 4.0` | LIVE 88.60 % | LIVE 88.60 % |
| `--resampler nearest` | LIVE 97.48 % | LIVE 97.48 % |
| `STREHL_ALIGN=0` | LIVE 97.60 % | LIVE 97.60 % |
| `STREHL_HIGHLIGHT_KNEE=0.02` | **DEAD** | **LIVE 79.48 %, max 2891 DN** |
| `--exposure=-6.0` | 0 samples | 0 samples |
| `--auto-exposure` | 325,061 samples, **max 1 DN** | 325,061 samples, **max 1 DN** |
| `STREHL_ROBUST_ELECTION=1` | DEAD | DEAD |
| `STREHL_SMOOTH=1` | DEAD | DEAD |
| `STREHL_RESTORE=1` | DEAD | DEAD |

**Exactly one verdict moved between the two builds, and it is the one that was
repaired.** That is the strongest commissioning available: the instrument was
shown able to detect not merely an absence but a *repair*, on a change it had
already scored as absent, without being told which row to watch.

### A third verdict was needed, and `--auto-exposure` is why

`--auto-exposure` moves 325,061 samples with a peak of **exactly 1 DN in 65535**,
while its own banner announces `+2.61 stops (gain 6.105x)`. A differs / does-not-
differ test scores that as working. It is not working; it is rounding. So the
audit has three verdicts, not two:

- **DEAD** — byte-identical. Reaches no pixel.
- **TOKEN** — differs, peak <= 2 DN under an absurd value. **Worse than dead**,
  because it passes every test that asks only whether something changed, and it
  issues a receipt for an effect no pixel carries.
- **LIVE** — a real change.

### Independent confirmation of two other lanes, and one of my own tools

- **BUILD-HIGHLIGHT's null reproduces, and it is not vacuous.** Their claim is
  that `109MSDCF` is byte-identical across their fix because its maxima reach
  only `u <= 0.5707`, below the 0.60 knee, and they state they predicted this
  before rendering. I measured the two default renders: sha256
  `7C77E638...E756F4` on both. But a null is only worth reading if the path
  could have fired, so: on those **same two binaries and the same subject**,
  moving the knee to 0.02 changes 79.48 % of pixels. **Present, potent, and
  correctly silent on data that stays below it.** I withheld this from the
  verifier I had already commissioned, so that their reading stays independent
  of mine and the two can be compared rather than merged.
- **M126's `STREHL_ROBUST_ELECTION` finding reproduces** by a completely
  different method — they read the code, I rendered an image.
- **`STREHL_SMOOTH` and `STREHL_RESTORE` are new**, and the second is the
  uncomfortable one. My own `scripts/check-defaults.py` has been reporting RED
  for exactly one reason: that `STREHL_RESTORE` is off by default. **Turning it
  on changes nothing at all.** My checker has been demanding that somebody flip a
  switch that is not connected to anything, and the demand looked like diligence.

The rule, which I am applying to myself first:

> A checker that demands a setting be changed has asserted that the setting
> matters. That assertion is a claim about the program, it is testable in one
> render, and mine was wrong. Before requiring a gate be turned on, turn it on
> and confirm a pixel moved.

### What this does not establish

DEAD here means *reached no pixel under these conditions*. That is one of two
very different things: genuinely dead code, or code nested behind another gate
that is off. **They produce an identical null and mean opposite things**, and
M126 has already been burned once attributing a byte-identity to a constant in
code that never ran. Separating them requires reading the code, and the audit
prints that warning next to its own results rather than in a footnote.


## 68. `=1` is not an absurd value, and the banner was telling me so

§67 built an instrument on one rule -- *a flag is not wired until an absurd
value has changed the output* -- and then broke that rule in its own probe
table. Every environment gate was probed with `=1`.

**`1` is the multiplicative identity.** For any numeric parameter -- a cap, a
gain, a lambda, a strength -- it is the single most likely value to be either
the default or the documented no-op. Probing a gate with `1` tests whether the
program responds to being told to do exactly what it is already doing.

Two of the four findings died on that:

| gate | what `=1` actually did | corrected probe | result |
| --- | --- | --- | --- |
| `STREHL_RESTORE` | it is a **gain cap** with guard `cap > 1.0`, so `1.0` returns the identical state to unset -- the module's own doc comment calls `1.0` "a documented no-op" | `=8.0` on `tweezers-cpl` | **LIVE**, output changes, banner reports `cap 8.000` and per-plane gains |
| `STREHL_SMOOTH` | `DEFAULT_SMOOTH_LAMBDA = 1.0` and the prior is **ON by default**, so `=1` set it to its own default | `=off` / `=400` | **LIVE, 96.39% / 96.76%** of samples |

A third, `STREHL_ROBUST_ELECTION`, was a fair probe -- `1` maps to `Arm::Soft`,
a real non-default setting -- and its null stands, corroborating M126's
independent code reading. The fourth, `STREHL_HIGHLIGHT_KNEE`, was correct in
both directions.

So the honest score is **one finding, not four**, and the one that survived was
already known.

### The banner was the tell, and my own rule said to read it

This project's hardest-won rule is *quote the banner, not your intent*. I wrote
that rule into three separate agent briefs this week. And `STREHL_RESTORE=1`
emits **zero** restore banner lines, where a live setting emits four. **The
program told me, on the stream I had instructed everyone else to read, that it
had nothing to report -- and I read the pixels instead.**

That is now structural rather than a matter of remembering. The audit
normalises each probe's banner against the baseline's, and:

> **If the program's own banner is unchanged, the arm was never tested.**

A value equal to the default or to the no-op leaves the program with nothing
new to say, and that silence is *distinguishable* from a real null -- but only
by someone who looks at it. The verdict is now **DEGEN**, reported separately
and explicitly not counted as a finding. Both false results above would have
been caught by it without anyone knowing either flag's type.

### What this cost, and the general form

`restore.rs:1234-1241` now carries a doc comment describing this exact mistake,
written by the implementer who caught me:

> *"An orchestrator commissioning this flag set it to `1`, observed
> byte-identical output, and concluded the stage was unreachable on the render
> path; it is reachable, and `1` had merely selected the documented no-op."*

That is the correct place for it. The rule that generalises:

> An "absurd value" is **type-dependent, and the type is the whole problem**.
> For a boolean, absurd is `on`. For a cap or a gain, absurd is *large*. For a
> parameter with a live non-zero default, absurd is *both directions* -- off,
> and far past sane. A single probe convention applied across differently-typed
> parameters will silently generate nulls, and nulls are the finding this
> instrument exists to produce, so its failure mode is to manufacture exactly
> the result it is looking for.

That last clause is the part worth keeping. An instrument whose failure mode
resembles its intended output is not merely unreliable -- it is *confirmatory*,
and it will read as a success every time it breaks.

### One thing I got right by accident

I told BUILD-SHARP, in the message that provoked this: *"Determine it by
reading the code, not by inferring it from this null,"* and *"do not let my
checker's RED bias you toward concluding the feature is merely disabled."* Both
instructions were sound and both were the reason the error surfaced within the
hour. **I gave the correct method to someone else while failing to apply it
myself**, which is its own finding about how this orchestration works: the
briefs are more careful than the hands.


## 69. Twenty of twenty-six, opened: what the corpus actually looks like

Continuing §66's survey to twenty subjects at 1:1, chosen adversarially rather
than representatively -- the defocused background, the stack that moved, the
bubble motion, the deep stack, and high-contrast text.

### The halo is dead, and `wrapped-text-1` is the proof I did not have

Black laser text on white paper. **This is where every focus stacker in the
world shows a halo** -- maximum contrast, a hard edge at a depth discontinuity,
and a flat bright field on one side to show any rim against. It is the geometry
that made the shipped output unusable three days ago.

There is **no rim of any kind**. Not bright, not dark, not a glow. The paper's
fibre texture runs continuously up to the letter boundary, and the individual
toner particles inside each stroke are separately resolved.

I have been treating the halo fix as verified since BUILD-HALO's report and
§65's edge profiles. Those were measurements across a synthetic edge. **This is
the artifact's own habitat, and it is empty.** A measurement says the rim's
amplitude is below threshold; this says a reader looking at a print will not
find it, which is the claim the project actually has to make.

### The gate's adversarial case passes

`flower-bud-with-background-fern-cpl` was the subject I named to BUILD-BLEND as
the case that could still kill gate 4.5 -- a large defocused background is
where a wider gate should drag out-of-focus content into the result. Individual
white trichomes are resolved crossing *over each other* at different depths,
pollen grains are crisp, the dark hairs carry no rim, and the defocused region
stays smooth without contaminating the sharp one. It passes.

### One new defect, and it is a colour defect, not a focus defect

Two subjects show fringing on **small bright features against dark ground**:
`coffee-bubbles` (green-yellow specular rings, some opposing magenta) and
`foam` (rainbow speckle on sub-pixel speculars). Nothing else in the corpus
shows it, and the subjects that *should* show it if it were an edge or depth
problem -- the text, the trichomes -- are clean.

Leading candidate: **green has 2x the sample density in an RGGB CFA**, so a
1-2 px bright feature reconstructs green-biased. Textbook demosaic false
colour. But I have deliberately not concluded that, because three other
mechanisms fit the same pixels, and one of them matters enormously more than
the rest:

> **Does a single unstacked frame show it?** If yes, we inherited it from the
> demosaic or the optics and the fix is a chroma stage. If a single frame is
> clean and the stack is green, **the merge is manufacturing colour** -- per-
> channel weights diverging where signal is sparse -- and that is a defect of
> the estimator rather than a cosmetic one.

Routed to BUILD-HIGHLIGHT with that ladder (single frame, CFA-native,
demosaiced, shipping default) and an instruction to run it *before* proposing
any fix. A false-colour suppressor bolted on top of a merge bug would hide the
more important finding while appearing to succeed -- which is the same shape as
the confirmatory-instrument failure in §68, one layer up.

Note also that this fringe is **green**, while the channel-asymmetric clipping
BUILD-HIGHLIGHT fixed predicts **magenta** (green has 1.53x less headroom and
pins first). Same region of the image, opposite sign. Both can be present; the
sign is what will separate them.

### The standing score

Twenty opened. **Eighteen print-worthy.** One soft (`flower-bud-alone-cpl`,
which is also the worst on merge-vs-best-frame at 0.82 -- the metric and my eye
agreeing independently, still the most useful event in this survey). Two
carrying the specular fringe above, which is real but confined and does not
touch the subjects a macro photographer would print.

That is a materially different sentence from the one this project could write
seventy-two hours ago, and the six unopened subjects are the remaining risk.


## 70. A 68-pixel error on an image that is sharp

BUILD-RENDER's provenance work turned up something better than metadata: **the
sidecar's whitelist kept 6 of 27 fields**, and among the twenty-one it dropped
was the binary stating its own absent stages.

```
not applied : photometric gain, clip census, outlier rejection,
              halo correction, through-focus statistics
```

**That is the fact this fleet spent an evening inferring wrongly from an argv,
printed by the program, in the log, on disk, the whole time.** I read a SHIP-V2
command line, saw no `--fix-ca`, concluded the shipping masters had the fringing
correction off, broadcast it, and sent an agent after a promotion of something
that had already shipped. One line of the program's own self-report would have
made that impossible.

The fix was not to add the two missing keys. **A whitelist re-arms the trap
every time the program learns to say something new**, so the self-report is now
carried verbatim with the extract labelled as an index into it, commissioned by
a fidelity null at 71/71 character-identical lines. `FULL` was also struck from
`FULL ARGV`, correctly: a header promising verbatim truth while silent about
three things that changed pixels is worse than no header, because it licenses
the inference I made.

### Then the partition surfaced something in the shipping set

Held-out alignment error, partitioned so that nothing hides: **19 measured, 6
NOT MEASURED, 1 REFUSED = 26.** The refused one is
`highly-angled-ruler-mm-cpl`, and it is in the print set:

```
alignment : REFUSED -- tilted subject; a global similarity cannot
            describe it (M86). Merging unregistered.
```

And the measured tail is alarming on its face: `pencil-steep-angle-cpl`
**68.20 px**, `pencil-flatter-angle-cpl` **55.79 px**, `lavendar-cpl` 24.24,
`bee-1-cpl` 17.00, against `flower-bud-alone-cpl` at 0.35.

### So I opened the two extremes, and the metric is not measuring what it reads like

- **The unregistered ruler** is crisp. Graduation lines unghosted, machining
  striations resolved, debris specks sharp. **No doubling** -- which is exactly
  the artifact unregistered merging would produce if there were real
  misregistration to correct.
- **The 68.20 px pencil** resolves individual graphite crystal facets glinting
  separately, with extrusion striations across the whole shaft. It is one of the
  sharper images in the corpus.

M86's score asks whether **a global similarity composes across the graph**. On a
steeply tilted subject a global similarity is the wrong model *by construction*
-- different depths move differently -- so a large score reports **model
inadequacy, not residual misregistration**. The merge does not need a globally
correct similarity; it needs local correspondence, and it has it.

> **A number that reads like a defect must carry its caveat at the point of
> publication.** `68.20 px` printed beside a visibly sharp image will be read as
> a failure by every reader who does not also have the paragraph above, and
> relying on the reader to find that paragraph is not a plan.

### The guard is inconsistent, and I am recording rather than fixing it

The guard **refuses** the tilted ruler while `pencil-steep-angle` (68.20) and
`pencil-flatter-angle` (55.79) are the **same geometric class, worse on the
metric, and not refused**. The guard and the metric disagree about one failure
mode. That is a real correctness defect.

It is also **costing no image quality** -- all three subjects look right,
including the unregistered one. So it is logged, not staffed, and the ranking
rule is worth stating because this project's instinct runs the other way:

> **A correctness defect with no measured cost ranks below a defect a reader can
> see.** Rigour is a means here, not the product. If the MTF work in flight
> finds a fine-scale deficit that tracks these subjects, this moves to the top
> the same hour.

### Twenty-two of twenty-six

Both subjects above join the survey. **Twenty print-worthy**, one soft, two with
the specular fringe. And the print masters exist: SHIP-V2 and SHIP-V2-ICC are
both complete at 26/26 with `.ok` markers, sidecars and `COMPLETE.txt` -- my
belief that the batch was still in flight was one of BUILD-RENDER's own test
arms, misread as the batch.

---

## 71. Four ways to be handed the same nothing

Two agents reported on the specular fringe within an hour of each other, and
between them they killed every candidate I had -- including one I never wrote
down because I thought it was obvious. Then, chasing what looked like a
regression, I made the same class of error a fourth time. That fourth one is
the useful part of this section, so it goes last.

### The fringe is not the merge, and it is not the demosaic

BUILD-HIGHLIGHT ran the four-arm ladder on `coffee-bubbles`, one binary, all
`--linear-srgb`, all on one 3516x2344 grid so no arm was resolution-advantaged:

| arm | H (speckle) | L (bands) |
|---|---:|---:|
| K1 single frame, demosaiced | **0.2955** | 0.3083 |
| K3 stack, demosaiced | **0.2558** | 0.3583 |
| K2 stack, never demosaiced | **0.2928** | 0.3660 |
| K5 stack, `--fix-ca off` | **0.2920** | 0.3663 |

**The merge is innocent.** A single frame carries **15.5% more** high-frequency
chroma than the stack of it. The defect is fully present before any merging
happens, and merging *reduces* it. They did not stop at the number either:
`pyramid.rs:990-993` computes `den` once on green luma and shares it across all
planes, pinned by the test `the_selection_is_shared_across_planes` at `:2216` --
and **a shared scalar cannot manufacture chroma**. I had called a merge-origin
fringe "a far more serious finding" than the halo. It is dead, and the pairing
of a measurement with the mechanism that makes the measurement necessary is the
strongest form of argument this project has produced.

> **CORRECTED at section 76, attribution amended at section 78. "The merge is
> innocent" is too broad.** The sentence and the shared-`den` argument beneath it
> were **BUILD-HIGHLIGHT's**; I escalated the conclusion and carried it into this
> log without checking it. Its author asked for that to be recorded as a **joint
> miss** rather than mine, which is the accurate version and is the opposite of
> the direction people usually push an attribution. The 15.5% measurement stands,
> and a shared scalar denominator genuinely
> cannot manufacture chroma *amplitude*. But `den` being computed on green luma
> and shared across planes means R and B are elected at **green's** best focus
> rather than their own, and under longitudinal CA those are not the same frame
> -- measured at `k_R - k_G` = **-0.67 to -1.07 frames**, red forfeiting
> **8.96-14.74%** of its gradient energy. That is not manufactured chroma, it is
> **differential defocus**, and it is field-wide. The three lines I cited as
> exculpatory are the prime suspect. The tell arrived later: **74% of the
> `coffee-bubbles` deficit is already present at r = 0.04**, on axis, where
> lateral CA is identically zero -- and a field-independent chroma defect cannot
> be a radial one.

**My own leading candidate is refuted.** I argued green's 2x CFA sample density
would make fine bright features reconstruct green-biased -- textbook Malvar
false colour. The never-demosaiced arm is **12.6% worse**, on the same lattice.
That is the opposite of what the hypothesis predicts. Recorded as refuted.

### The best catch in the report is a selector that contained its conclusion

BUILD-HIGHLIGHT withdrew three of their own findings before publishing. The
second is the one worth keeping:

> BT.709 luma is 71.5% green, so ranking candidate pixels on luma preferentially
> selects **high-green pixels** -- the very effect I was about to report.

Under `--select-on rb` the blue half of their result collapses
`-0.0882 -> -0.0071 -> +0.0004` and flips sign. That is not a correction to a
finding; it is the difference between a finding and an artifact of how the
pixels were chosen. They found it by deliberately picking a selector that could
not produce their result. The other two withdrawals are the same virtue: a mask
that selected blown cores and printed a confident table of `0.000000` on every
arm -- **neutral by construction**, a number that could not have been anything
else -- and a "the CA correction is making it worse" headline retracted on the
grounds that one selector is not a result.

### And the flower bud is not blown at all

I had told V-HIGHLIGHT that `flower-bud-alone-cpl` carried a magenta fringe
where the bud meets a **blown-out white background**, and registered a
prediction that the highlight roll-off would reduce it. The prediction is
**refuted**, and the reason is worse than being wrong about the mechanism:

```
per-channel ceiling : R 2.8288  G 1.0689  B 1.5595
frame max u         : 0.3125          (the knee is 0.60)
brightest pixel     : 5471 DN of a 16383 container
pixels at 65535     : 0.000000%
```

**Nothing in that image is remotely near clipping.** The background is at a
third of the sensor's range; the `--srgb` tone curve lifts it **2.74x**, and I
read the result as saturation. I have spent this week telling other agents that
a magnitude must be measured in linear -- and then diagnosed a *clipping*
defect by eye, off a tone-mapped render, without once probing the raw. The rule
I had was too narrow. The general form:

> **A saturated appearance is a statement about the render, not about the
> sensor.** "Blown" is a claim about DN against a container and can only be
> settled in the raw domain. Every judgement made from a display-referred image
> inherits the tone curve's opinion.

V-HIGHLIGHT then discarded their *own* first result on the same subject, which
had looked strongly CA-like (antisymmetry -483.8/+483.6, radial growth
-174 -> -1294): `corr(chroma, luminance) = +0.7320` on edges, so an intensity
edge at constant hue fakes a radial chroma trend. On a scale-invariant metric
the shipping arm's radial profile is **flat** (-0.0275 -> -0.0269). CA
correction removes only 19.7% of that fringe. And chroma excess falls
**monotonically 3.1x** from the darkest to the brightest quintile -- which rules
out clipping unaided, since a clipping-driven error must do the opposite.

So on `flower-bud-alone-cpl` the fringe is **unattributed**: not clipping, not
demosaic, not the merge, and only one-fifth CA. That is an honest open state and
it is recorded as one. It also now conflicts with BUILD-HIGHLIGHT's radial
finding on `coffee-bubbles`, and the conflict is live: one used raw chroma, one
used a scale-invariant metric, and V-HIGHLIGHT has shown the raw form is
contaminated by exactly the luminance correlation that a specular-on-dark
subject maximises.

### The fourth way to be handed nothing

Chasing V-HIGHLIGHT's commissioning number, I found what looked like a clean
regression. They measured `STREHL_HIGHLIGHT_KNEE=0.05` moving **67.56%** of
`109MSDCF`. I ran the *more* extreme `0.02` on the same subject and got
byte-identical output -- and byte-identical at `0.05` and at `off` too, all
three the same hash `7C77E638BF7FE597`.

It was not a regression. My pin was built from `96b7e119`, and:

```
$ git cat-file -e 96b7e119:crates/strehl-core/src/highlight.rs
fatal: path exists on disk, but not in '96b7e119'
```

**The feature did not exist in that tree.** The binary had never heard of the
variable, so byte-identical output is the only thing it could possibly have
produced. Confirmed independently: `0.0`, which V-HIGHLIGHT showed must emit a
warning, emits nothing.

Now count them. This audit has produced a false "dead flag" verdict four times,
by four unrelated mechanisms, and **every one of them emitted the identical
glyph**:

| # | cause | what it actually measures | verdict now |
|---|---|---|---|
| 1 | `=1` on a multiplicative gate | the identity element | DEGEN |
| 2 | a value equal to the default | the arm never ran | DEGEN |
| 3 | 8 frames on a frame-pooled gate | the probe's shallowness | SHALLOW |
| 4 | a binary predating the flag | nothing at all | **UNIMPL** |

> **Byte-identical output is the null result of every possible probe failure,
> and from the pixels alone it is indistinguishable from a true negative.**
> Every guard in `check-potency.py` exists to subtract one member of that family
> from the DEAD column, so that DEAD can mean what it says: *present, reached,
> and inert.*

The fourth guard is now wired, and it needs no render. Rust emits
`std::env::var("NAME")` and clap's flag names as literals in `.rdata`, so a flag
absent from the binary's own bytes cannot be under test. Measured on the pin:

```
STREHL_HIGHLIGHT_KNEE    ABSENT  <- cannot be probed
STREHL_SMOOTH_HUBER      PRESENT
STREHL_RESTORE           PRESENT
STREHL_FIX_HALO          PRESENT
STREHL_PHOTOMETRIC       PRESENT
STREHL_WARPMAP           PRESENT
28 distinct STREHL_ env literals found
```

The scanner is commissioned on both halves, because **a scan that finds nothing
looks identical to a binary that contains nothing**: it requires at least ten
real `STREHL_` literals to prove it reaches `.rdata`, and requires a fabricated
token to be *absent* to prove it can say no. Both are checked before any
`UNIMPL` verdict is allowed to print, and the audit hard-exits `2` if either
fails.

There is a lesson here about pins specifically. I have been treating "pin the
binary" as sufficient rigour for weeks. It is not:

> **A pin freezes provenance, which is only a virtue if the provenance contains
> the thing you are testing.** An old pin is a perfect instrument for measuring
> a feature that did not exist -- it will answer every question about it,
> consistently, and always with the same wrong answer.

## 72. The last of the twenty-six

`bee-2-cpl` was the only subject never named in this log. Opened at 1:1 from the
SHIP-V2 master, it is the strongest single frame in the corpus for the question
the owner actually asked.

Individual bee hairs are separable across the whole thorax, each with a tapering
tip, and dozens of them cross from the black body out over the white backdrop --
**thin, low-contrast, translucent structure against a bright field**, which is
the exact geometry that produces a rim if anything in the pipeline is going to
produce one. There is no rim. There is no aura. The white immediately beside the
black chitin is the same white as the far field. Pollen grains on the leg carry
individual surface texture, and the speculars on the chitin are clean, with none
of the green-yellow fringe that `coffee-bubbles` and `foam` show.

That closes the survey at **26 of 26 opened**, which the README had already
recorded and this log had not. The two documents now agree, and the agreement
was reached by looking rather than by copying.

Worth stating plainly, because tonight produced two independent lines of it:

> **The halo complaint is answered.** `wrapped-text-1` (black laser text on white
> paper, toner particles resolved to the letter edge, no rim) and `bee-2-cpl`
> (hair tips over white, no rim) are the two hardest cases in the corpus for
> that defect, and both are clean. The measured backdrop profile on
> `flower-bud-alone-cpl` puts a number on it: **+5.31%** near-band for the
> shipping blend against **-23.71%** for the control arm.

One caution carried forward rather than dropped: `bee-2-cpl`'s lower-left corner
hairs are soft. My read is depth beyond the bracket rather than a merge failure,
on the same grounds as `flowers-cpl` -- but I have not measured it, and it is
recorded here as unmeasured.

## 73. Seven instruments, one night, one failure mode

Four agents reported between midnight and morning. Every one of them found a
defect in their own instrument before finding one in the product, and the
defects are the same defect wearing different clothes. Collected here because
the pattern is now the most transferable thing this project has produced.

### The catalogue

| # | instrument | how it failed | who caught it |
|---|---|---|---|
| 1 | `=1` on a multiplicative gate | probed the identity element | ORCH |
| 2 | a value equal to the default | the arm never ran | ORCH |
| 3 | 8 frames on a frame-pooled gate | measured the probe's depth | M126 |
| 4 | a binary predating the flag | measured nothing | ORCH |
| 5 | luma selector, 71.5% green | **selected the green excess it was about to report** | BUILD-HIGHLIGHT |
| 6 | null window inside the defect | normalised a defect against itself | ORCH |
| 7 | ringing plant on ideal steps | **sensitivity scales with the quantity in dispute** | BUILD-SHARP |

Numbers 1-4 all emit byte-identical output and were folded into
`check-potency.py` in section 71. Numbers 5-7 are worse, because each one
returns *the answer the experimenter was hoping for*, with every control
passing.

**Number 7 is the most dangerous instrument this project has built.** BUILD-SHARP
was sent to test whether the comparator wins by ringing rather than by
resolving. Their detector had an exact null, calibrated plants at
0.05/0.15/0.30, strict monotonicity -- fully commissioned by every rule we had.
Commissioned *on the actual files*, it recovers **1.00x** on synthetic steps,
**0.38x** on the fork's render and **0.08x** on ours:

> The detector is **4.75x more sensitive on the fork's render than on ours**.
> Measuring overshoot on both and comparing would have reported the fork as
> ~5x ringier **with no ringing present anywhere.**

The cause is physical, not a bug: the plant is calibrated on an ideal step, real
edges are blurred, and the kernel's negative lobes land on intermediate values
instead of a plateau. So sensitivity tracks *how step-like the edges are* --
which is the very thing in dispute.

> **An instrument whose sensitivity is a function of the quantity being measured
> will return the expected answer on every subject, forever, and pass every
> control while doing it.**

The fix is not more care. It is: commission **each** render separately and
divide its reading by **its own** recovery fraction; never compare an absolute
magnitude across two images; and use the same subject on both sides.

And a coda in the same register: BUILD-SHARP's commissioning output printed
`amplitude floor 0.0 DN` for a value of `0.00815` because of a `:.1f`. **A
display format nearly retired a working instrument.**

### The corner of the lens correction was never fitted

BUILD-HIGHLIGHT settled the fringe conflict -- `coffee-bubbles` and
`flower-bud-alone-cpl` are different populations, not different statistics, and
both instruments agree wherever they overlap -- and then found the mechanism in
`optics.rs`:

```
support_r_max: Some(0.788)
"outer two annuli empty. The corner is a 1.27x linear extrapolation.
 Declared, not enforced."
```

**No data past r = 0.788. Nothing prevents application to r = 1.0. The residual
grows exactly there.** Three subjects carry the specular fringe, all
specular-on-dark, all radial, and the correction meant to remove it is
extrapolating in the region where it appears. A second reading points the same
way: shipped `eps_r` is **704.5 ppm** against six per-stack fits spanning
**500.9-651.9** -- above every fit that informed it.

*"Declared, not enforced"* is the defect in three words.

The profile itself is sound provenance -- `lens_type3: 33094`, fitted for the
teleconverter from 20 red ROIs and 1071 blue tiles, **not** inherited from the
bare lens as I had guessed. My suspicion was wrong and the real defect is more
interesting than the one I proposed.

### The merge is noisier than one frame on half the corpus

BUILD-TRIAGE fixed a wording bug and a concealed measurement fell out. Of 21
GOOD rows, **11 have the merge cleaner on flats than the best single source
frame and 10 have it noisier** -- and `bee-3-cpl`, at **299 frames** and the
subject I have been holding up as the print reference, is **2.08x noisier than
its own best source frame**.

On the project's thesis -- estimation, not selection -- that is the thesis
failing where it should be strongest. In a flat region every frame is an
independent measurement of the same value and the ceiling is ~1/sqrt(299).

Registered before it is measured: M126's gate 4.5 gave a **9.9x** flat-field
noise reduction on this exact subject, and BUILD-TRIAGE's numbers are at the
compiled default of 2.0. So gate 4.5 should move `bee-3-cpl` from 0.48 to
roughly **4.7** and flip most of the ten. If it does not, M126's 9.9x is
measuring something other than the noise a viewer sees, and the README's
justification for the gate is narrower than I have been writing.

Two artifacts had been printing **contradictory** figures for `bee-3-cpl` --
`makeviewable.py` saying "2.08x noisier on flats" and `triage.json` saying
"0.88x less pixel noise" -- for as long as both existed, and nothing ever put
them side by side.

### A claim of mine, struck

I labelled `flowers-cpl` in the shipping gallery *"soft throughout -- reads as
an incomplete bracket, not a merge failure"* on nothing but a glance. BUILD-SHARP
measured the supportable half and refused the rest:

> *"What I did not establish and will not imply: that the bracket is
> incomplete."*

Per-pixel selection over the same frames recovers nothing the merge lacks, so it
does not count against the tool -- and the cause of the softness is unexplained.
The card now says so, including the words *the cause is NOT established*. Their
route to it cost three instruments and two in-place retractions, including the
observation that **two statistics both normalised by intensity are not
independent when the same 18.5% exposure ramp moves both.**

## 74. The instrument built to test for flatness was flattening the pictures

Section 73 catalogued seven instruments whose failure mode resembled their
intended output. Here is the eighth, and it is mine.

### What I set out to check

The user's complaint was about how the pictures *look*. The shipped masters are
faithful renders -- camera matrix, sRGB curve, one honest gain, no grade -- and
the project's own `DO-NOT-MEASURE.txt` says so in as many words:

> *a faithful `--srgb` master is flat by construction and **reads as poor work
> when it is not**.*

So there is a `_presentation` set, graded, existing precisely so a photographer
can judge the photographs. My hypothesis: the shipping gallery shows the
faithful set, the user judged the tool on flat renders, and pointing the gallery
at the graded set would fix a chunk of the impression.

The first half is true -- `build_view.py` resizes and saves, nothing else.

### The measurement, and my first instrument was blind

I compared faithful against presentation on `p99 - p1` of luma. Median ratio
**1.02x**, median luma shift **-1.6 of 255**. On that reading the grade does
essentially nothing.

**That reading was worthless.** The note claims three operations -- a percentile
black point, a filmic S-curve, and a saturation lift -- and `p99 - p1` is blind
to two of them. An S-curve moves the *midtone slope* and deliberately leaves the
endpoints alone; a saturation lift does not touch luma at all. I had built a
statistic that could only see the one operation I was least interested in.

Rebuilt with one statistic per claimed operation, each commissioned against its
own plant, and the cross-talk reported rather than assumed away:

| claimed operation | statistic | corpus median | verdict |
|---|---|---:|---|
| percentile black point | p1 of luma | **+0.1 / 255** | inert |
| filmic S-curve | p75 - p25 of luma | **0.939x** | **backwards** |
| saturation lift | mean (max-min)/max | **1.106x** | works |

### The defect

```python
c = 0.42
out = out + c * out * (1.0 - out) * (2.0 * out - 1.0) * -1.0
```

That trailing `* -1.0` inverts the curve. `(2x-1)` is negative below the
midpoint and positive above it, so **adding** the term pushes each half away
from the centre, which is contrast; **negating** it pulls both halves toward the
centre, which is the opposite. On a 1001-point ladder:

| | midtone slope | shadow x=0.25 | highlight x=0.75 |
|---|---:|---:|---:|
| identity | 1.000 | 0.2500 | 0.7500 |
| **as shipped** | **0.822** | 0.2894 **lifted** | 0.7106 **pulled down** |
| sign removed | 1.178 | 0.2106 darkened | 0.7894 brightened |

Both versions are monotonic, both hold their endpoints, both produce a
perfectly plausible photograph, and nothing anywhere checked the *direction* of
the contrast. **The script whose docstring asks "do these look bad because they
are SOFT, or because they are FLAT?" was flattening them before anyone looked.**

> **A tone curve has a sign, and a wrong sign is invisible in every structural
> check: monotone, endpoint-preserving, non-clipping, and confidently wrong.**

### The fix, and the subject that refused it

Sign removed, then measured on six subjects against both the faithful master and
the shipped inverted grade:

| subject | faithful | shipped | fixed |
|---|---:|---:|---:|
| `leaf-2-cpl` | 58.9 | 54.7 | **72.0** |
| `coffee-bean` | 156.9 | 145.4 | **177.0** |
| `bee-3-cpl` | 126.6 | 118.6 | **141.7** |
| `109MSDCF` | 125.2 | 124.9 | **140.7** |
| `lavendar-cpl` | 57.3 | 57.3 | **63.5** |
| `flower-bud-alone-cpl` | 13.0 | 17.6 | **9.2** |

Five subjects gain 11-32%. The sixth goes **backwards, and below ungraded** --
`flower-bud-alone-cpl` is a white bud on white at median luma 239/255, an
S-curve brightens highlights, and this subject is already living in them. The
cubic S is symmetric about 0.5 and has no real shoulder, so for a high-key
subject it compresses exactly where all the tones are.

I did not tune the constant until the anomaly disappeared. The grade now
measures its own effect and **backs the strength off until it is not worse than
no grade at all** -- 1.0, 0.5, 0.25, then off -- reporting which subjects were
backed off instead of silently shipping them. `flower-bud-alone-cpl` goes to
**0.000** and lands at 13.5, above the faithful 13.0. That is the merge's own
*never worse than a single frame* invariant, applied to the grade: **a
presentation render that degrades the picture is not a presentation render.**

The guard is commissioned two-sided from a `$TEMP` pin, anchored on a unique
full line that hard-errors if it fails to land: fixed **passes**, sign restored
**fails with the diagnostic naming the inversion**, restored **passes**, and the
restore is byte-verified against the pin.

### What the gallery shows now

Graded full frame for judging the photograph, faithful master at 1:1 for judging
the defect, each labelled on its own caption. The split is the point: a grade is
a tone curve, and nothing in this project judges a defect across one.

### Two negatives worth keeping

**The sRGB gamut ceiling is not costing anything measurable.** I expected a
16-bit sRGB master to clip printable colour on saturated macro subjects. Probe
commissioned two-sided -- planted out-of-gamut **100%**, in-gamut pastel ramp
**0.0000%** -- and all 26 masters read **0.0000%** at both rails. Hypothesis
refuted; do not add a wide-gamut output on my say-so.

But the same run showed **`true-white 0.000%` on every subject**, so my probe's
trigger condition never occurs in this data and the zero means *the signature is
absent from the file*, not *no gamut was clipped*. If the pipeline clamps
negatives and then adds a pedestal, the evidence is destroyed upstream of me.
Routed to BUILD-WIRE as a source read, not another measurement.

**The masters declare no print size.** `XResolution 1.0`, `YResolution 1.0`,
`ResolutionUnit 1 (none)`, and `Software strehl 0.0.0`, on all 26. Everything
else in the file is right -- 16-bit, `SampleFormat (1,1,1)`, a real 2716-byte
ICC that names itself, an `ImageDescription` stating primaries and white point.
A print master whose physical size is undefined is not a print master.

## 75. The plant is not the commissioning arm, and the confound was in the variable

Two lanes reported within an hour of each other. Between them they overturned
two things this project thought it knew about how to commission an instrument.

### The null is the sensitive arm, not the plant

BUILD-SHARP redesigned the ringing detector and found **three** defects in the
redesign. Every one was caught by the **null**. Every one had a **passing
plant**.

| defect | what it did | plant said |
|---|---|---|
| `max(q[-1]-q[0], 1e-12)` clamping a negative denominator | nulls at **4.3e11** | passed, at that scale |
| excursion extrema at profile indices 0 and 28, **inside the samples defining the plateau** | strehl **0.0111**, fork **0.0097** | passed |
| null blurred at 9 taps, plant at 13 | plant **non-monotone in blur** | passed |

> **A passing plant does not commission an instrument.** The plant is large by
> construction and will survive a broken instrument; the null is the sensitive
> arm, and a null that is not exactly zero is the only thing that catches a
> defect big enough to swallow the plant whole.

The middle row is the one to be frightened of. `0.0111` against `0.0097` is a
**tidy near-tie**: small, plausible, faintly in our favour, no dramatic claim
attached — the exact shape a tired reader accepts without checking. It was
produced by measuring extrema inside the very samples that defined the
normalisation. Nothing about the number looks wrong. Only the null did.

Third defect, restated because it is a general test: **heavier blur cannot ring
more.** A plant that is non-monotone in blur is broken regardless of what it
reports. Physical monotonicity is free commissioning and almost nobody checks it.

### The confound was never in the statistic

Section 73 recorded the ringing detector's sensitivity scaling with edge
sharpness. BUILD-SHARP then built a genuinely different instrument to escape it:
a **calibration-free shape test** -- does the plateau-normalised edge profile
leave [0,1]? A non-negative kernel cannot push it out; ringing must. No
amplitude reference anywhere, exact null at every blur level. It should have
escaped.

| | 10-90% edge width | shape test |
|---|---:|---|
| synthetic step | 1.89 px | sees ringing, **0.0636** |
| step + blur 1.5 | 4.33 px | **blind, 0.000000** |
| `wt1-strehl` | 13.52 px | 0.000000 |
| `wt1-fork` | 17.86 px | 0.000000 |

Both renders sit **more than 3x past the blindness threshold**. Their zeros
would read zero whether or not ringing is present.

> **The confound was not in the statistic, it was in the VARIABLE.** Any
> instrument whose usable range is bounded by edge sharpness will fail this
> comparison, because edge sharpness *is* the comparison. Redesigning the
> statistic while staying on that variable reproduces the failure with a new
> mechanism and the same direction.

Two independent instruments, two different mechanisms -- amplitude sensitivity,
then range blindness -- one consequence. That is why ISO 12233 is now the only
live route: it recovers the transfer function from the edge's own spectrum
rather than comparing an amplitude against an external reference. BUILD-RESAMP
has been told to **verify** that immunity across 1.9-18 px of edge width rather
than assume it, because *"I think it is immune"* is what produced both failures.

### The claim that was refused for favouring us

> *"13.52 vs 17.86 is not evidence our edges are sharper. Cross-image magnitude,
> different populations (11,185 edges vs 4,436), inflated by subpixel phase
> averaging. **It favours us, which is why I am not reporting it.**"*

That is the standard. It would have gone straight onto the README, it is
directionally what everyone here wants, and it was killed on methodology the
author had derived two turns earlier.

### A ship blocker, found in passing

**`wt1-strehl.log` says 22 frames, against a directory named `h2h24`.** If our
render consumed 22 frames of that bracket and the fork consumed 24, every
head-to-head number from that pair is **void** -- not biased, void, because the
two sides did not see the same photons and any sharpness difference is partly a
difference in what was available to be sharp. Routed to BUILD-RESAMP, who owns
the fork renders; the finder does not adjudicate their own discrepancy. The
directory name is the weakest evidence in the room and does not arbitrate.

### A false accusation is also an instrument failure

BUILD-TRIAGE's mutation harness failed **by accusing working code**: the wording
mutation left `noise_phrase` monkeypatched, so both later definition mutations
tripped the *wording* gate, and the test reported "gate is blind" while both
gates were fine.

> **A mutation that is not undone silently invalidates every mutation after it,
> and the symptom is a false accusation, not a false pass.**

This is the tenth instrument failure catalogued in three days and the only one
that runs the other way. Everything else in the family returns a comfortable
green. A false accusation at least announces itself -- but it sends you hunting
a defect that does not exist, and its second-order cost is that the next real
accusation gets discounted.

### Near-synonyms read as corroboration

Applying "define every field at the point of display" to their own file,
BUILD-TRIAGE found two more:

- `merge_edge_dnpx / frame_edge_dnpx` **fails to reproduce** `edge_ratio_min` on
  **13 of 25 rows**, worst `bee-2-cpl` at 1.92 against a true 1.43 -- **34%
  out**. Invisible from the names: the DN/px figures are maxima over *possibly
  different sites*, and only the ratio is gather-corrected. Dividing them looks
  like arithmetic and is wrong.
- The sheet read *"instrument floor 0.3 px"* against `BLUR_FLOOR_PX = 0.35`.
  They **deleted the hardcoding** rather than correcting the digit -- making the
  class impossible instead of the instance absent.

And the direction of the gate they nearly did not build: **an orphaned
definition is worse than a missing one**, because a reader who cannot find what
it describes maps it onto the nearest surviving name. That is exactly how
`noise_flat` and `noise_advantage` came to be read as one quantity while
disagreeing by 17x in opposite directions.

## 76. The refusal, and the claim of mine it took down

I granted BUILD-HIGHLIGHT `optics.rs` to fix the specular fringe. **They
declined to edit it**, and their reasoning is better than my brief was. This is
the correct outcome and it is the second time tonight a lane has been right
against me.

### My premise failed on one number

I argued the fringe lives past `support_r_max = 0.788`, where the CA profile
extrapolates 1.27x beyond its data. Per-annulus medians of `(R-G)/Y` on
`coffee-bubbles`, correction on:

| r | 0.04 | 0.37 | 0.61 | 0.86 |
|---|---:|---:|---:|---:|
| median | **-0.2588** | -0.26 | -0.28 | **-0.3549** |

**At r = 0.04 -- on axis, where lateral displacement is identically zero -- the
deficit is already 74% of the corner value.** Direct annulus medians, not a fit.
And only **1.3%** of the population lies past r = 0.788.

> **A defect that is 74% present on axis is not a radial defect.** I had a
> radial statistic, a radial mechanism and a radial remedy, and never checked
> the intercept.

My three proposed remedies -- clamp, taper, higher-order term -- targeted the
minority of a minority.

### They were also out of transform class

`compose` at `:296` returns a **`Similarity`**: a uniform scale `s = 1+eps`,
with no radius in it. `warp_frame_in_place` takes a Similarity, and the doc says
outright *"a single similarity -- adds no second resampling pass."*
`support_r_max` is read **only by a test**, at `:1301`.

So clamp, taper and a higher-order term are not merely unwise, they are
**non-expressible** in the transform the pipeline applies. Each needs a second
resample, which adds a low-pass to R and B -- pushing *toward* the defect, since
the defect is red losing amplitude on fine features.

**My prior "clamping beats extrapolating" is neither confirmed nor refuted; it
is unreachable.** And what data exists leans against it. Outer annuli, CA
**off**: `-0.34, -0.13, -0.15, -0.55`. CA **on**: `-0.28, -0.28, -0.33, -0.35`.
**The correction stabilises the outer field.** That also carries section 73's
band-4 wobble forward with a partial explanation -- it is a CA-**off**
phenomenon, at 1.3% occupancy, small-sample variance not excluded.

### Two withdrawals, both against themselves

**The `eps_r` lead was dead and the retraction was three pages above the table
they quoted.** The 500.9-651.9 ppm per-stack fits are *raw and attenuated*
(x0.69-0.94); de-attenuated they form a band **centred on -704.5**. They had
compared attenuated numbers against a de-attenuated scalar. I had escalated it
to "above every single fit that informed it." Separately M113 already rejected a
global rescale -- gain 1.2496 on bee against 1.0557 on couch, *"does not
transfer"* -- and `captures-needed.md` says x0.692 **"must not ship."**

**The axial-CA attribution was refused outright.** Two instruments, opposite
signs: mean-normalised gave red **-85%** (rejected: conflates level with
sharpness, and disagrees with M107's 8.96-14.74% by an order of magnitude);
variance-normalised, calibrated on planted blur, gave red **+42%** (rejected: a
high-frequency *fraction* is inflated by noise and red has the worst SNR here).

> *"Reporting either would be choosing the one that suited my hypothesis."*

They committed the rejected script **marked REJECTED in its own header** rather
than deleting it. A rejected instrument left in the tree with its verdict
attached is worth more than a clean directory.

### The claim of mine it took down

In section 71 I wrote **"the merge is innocent"** on the strength of
`pyramid.rs:990-993` computing `den` once on green luma and sharing it across
planes: *a shared scalar cannot manufacture chroma*.

The scalar argument is sound and the 15.5% measurement stands. **The conclusion
does not.** A shared *selection* is not a shared *amplitude*: R and B are elected
at **green's** best focus rather than their own, and under longitudinal CA those
are different frames -- `k_R - k_G` = **-0.67 to -1.07 frames**, red forfeiting
**8.96-14.74%** of its gradient energy (M107 fact 1413). That is not
manufactured chroma, it is **differential defocus**, and unlike lateral CA it is
field-wide.

Which is exactly the shape of the measurement: **74% on axis.**

> **The three lines I cited as exculpatory are the prime suspect.** I proved the
> merge could not do one thing and concluded it had done nothing.

A channel elected at the wrong focus is defocused across the whole field and
loses most on the narrowest features -- which is a specular-on-dark subject,
which is all three affected subjects.

**Routed to the election lane, not to optics.** The discriminator is fact 1417's
per-channel focus-index offset. Recommendation accepted in full: **do not change
`optics.rs`.** The correction is right in magnitude, its rescale is already
rejected, its support limit governs 1.3%, and it demonstrably steadies the outer
field.

## 77. Three ways to be too generous to yourself

### A threshold read off the first failing grid point flatters the instrument

BUILD-SHARP was asked to write down their shape test's blindness threshold as a
stated applicability range. Re-deriving it **corrected their own published
number, in the narrowing direction.**

Section 75 recorded 4.33 samples. That figure came from a three-point grid, so
it was **the first width observed to fail** -- an upper bound on where the test
still works, never a measurement of it. Swept finely:

| width 10-90% | plant response | detectable |
|---:|---:|---|
| 1.89 | 0.063624 | yes |
| 2.37 | 0.017203 | yes |
| **2.69** | 0.000988 | **yes -- last** |
| 3.18 | 0.000000 | no |
| 4.33 | 0.000000 | no |

**Detectability does not decay, it falls off a cliff**, and the usable window is
under three samples wide. The two renders are therefore **5.0x and 6.6x** past
the range, not 3.1x and 4.1x. The conclusion is unchanged and strengthened.

> **A threshold read off the first failing grid point always flatters the
> instrument.** You find the first point that fails, not the last that works,
> and the gap between them is invisible unless you look for it.

Theirs was **61% too generous**, and it was their own number in their own
report. Any limit derived from a coarse sweep is biased toward optimism in
exactly the direction that makes the instrument look more applicable than it is.

### A check that always refuses is the same defect as a plant that always passes

They then commissioned the *guard*, which is the step almost nobody takes:

| fixture | width | verdict |
|---|---:|---|
| lanczos, no blur | 1.61 | **RINGING** (0.025239) |
| linear, no blur | 2.02 | **NO RINGING** (0.000000) |
| lanczos, blur 2.0 | 5.29 | **REFUSED** |

Three inputs, three different verdicts. **Row three is the whole argument: a
genuinely ringing image measuring exactly `0.000000`.** Without the guard it
reads clean, with an exact null and a passing plant standing behind it.
`APPLICABLE_MAX_WIDTH = 2.69` is now a module constant carrying its provenance,
and the reporting function prints `VERDICT: REFUSED` with the raw numbers
labelled `NOT A VERDICT` rather than a figure a reader could bank.

### The mutation rule travels with a limit, and the limit inverts the intuition

BUILD-TRIAGE amended their own rule from section 75 before it propagated:

> **The `finally` protects only the state I knew to restore.** Each mutation
> needs its own isolation, and the safest isolation is a **fresh process**, not
> a `finally`.

I had been about to send "use a `finally`" fleet-wide, which would have shipped
the minimum as the pattern. Module-level caches, in-place mutation inside
`main()`, and any mutation added later that forgets its own restore all sit
outside what a hand-written `finally` can see.

The second half is the part I would not have derived:

> The failure was legible **because** the definition mutations were downstream
> of the wording mutation. **A single-mutation harness with the same bug would
> have shown nothing.**

> **The bug's visibility scales with the number of mutations sharing a process,
> so the harnesses most likely to be silently broken are the small ones.**

A one-mutation harness looks simpler and easier to trust, and is the one
configuration in which unrestored state produces no symptom at all.

Checked against my own two instruments rather than assumed: `check-potency.py`
and `commission_grade_guard.py` both run each arm as a **subprocess**, so they
are on the recommended pattern rather than the minimum -- and arm B of the grade
harness demonstrably loaded the mutant, proven by it emitting the
mutant-specific diagnostic rather than a generic failure. Empirically isolated,
not argued to be.

### The eleventh instrument failure was mine, and it was a false accusation

I gave BUILD-TRIAGE the closing task *"confirm every field has its definition
available at the point of display"*, then ran it on my own shipping gallery.

My detector looked for a definition by requiring `=`, an em dash, a colon or the
word "means" between a term and its explanation. It reported **all seven**
displayed terms undefined, including the four verdict badges -- which are in
fact all properly defined, in a legend of the form `<span>showcase</span> the
hardest geometry in the corpus and clean`. **Term, then definition, no separator
at all.** My instrument demanded a syntax the data does not use and returned a
confident, uniform, entirely wrong zero. I nearly "fixed" a correct legend.

Second member of BUILD-TRIAGE's false-accusation class in a day, and the
practical lesson is the same as the plant/null one: **a detector for the
presence of prose must be commissioned against real prose**, because the space
of ways humans write a definition is much larger than the space a regex covers.

**The real hit was the drift they predicted.** The lede said *"Each card shows
the full frame and a 100% crop of actual pixels"* -- and I had changed the full
frame to a **graded** render hours earlier. One sentence restating what the code
does, drifting the moment the code changed. Now corrected, and it states *why*
the halves differ rather than only that they do.

I could not delete the second copy the way BUILD-TRIAGE deleted `0.3 px`, because
prose describing a design decision has no constant to source from. **Mine
remains the weaker class of fix and saying so is part of the fix.**

## 78. Going wrong beats going blind, and a caveat can discredit itself

### An instrument that goes blind announces itself; one that drifts does not

BUILD-RESAMP was asked to find the slanted-edge MTF's blindness threshold, on
the model of section 77's. There is no blindness threshold. There is something
worse.

| w10-90 px | 1.90 | 2.56 | 3.85 | **5.13** | 6.41 | 7.69 | 10.25 | 12.82 | 15.38 | 17.99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| measured / true MTF50 | 0.998 | 1.005 | 1.020 | **1.038** | 1.059 | 1.087 | 1.154 | 1.232 | 1.332 | **1.446** |

> **It does not go blind. It goes wrong -- monotonically, and toward the
> expected answer.**

That distinction inverts how this log has been treating applicability limits:

> **A blind instrument is a safe failure. A biased one is not.** A zero on an
> image that visibly rings is alarming enough to investigate. `1.4404` on a soft
> edge is an entirely plausible number that no reader would question, and it is
> wrong by 44%.

Section 77's shape test was the *lucky* instrument. It failed loudly.

**And the magnitude settles the original question by subtraction.** The two
renders do not share an edge width, so they do not share an inflation:
**1.2593x** (strehl, 13.52 px) against **1.4404x** (fork, 17.86 px), ratio
**1.1438** -- a **14.38% systematic bias from edge width alone**, running in the
direction that makes the fork read sharper, against a claimed deficit of
**17-23%**. Most of the number this project steered by for days was the ruler
bending.

**Three mechanisms, one pair, all flattering the same conclusion:**
nearest-neighbour scoring **+29%/+42%**; a 0.5x downscale scoring **4.35x
better**; and now edge-width inflation. Three unrelated statistics -- a band
ratio, a shape test, a slanted-edge MTF -- and:

> **The confound is in the variable, not the statistic.** Any instrument bounded
> by edge sharpness fails a comparison *of* edge sharpness. Reached
> independently by two agents through two entry points; promoted from lesson to
> measured finding.

The consequence is a **capture**, now filed as `captures-needed.md` section 30
and promoted to #4 in its index: the corpus has no valid slanted edge. Its edges
are 13-18 px wide against a 5.13 px limit, and the instrument pointed at a page
of text reported **3568 of 3570** candidate edges flatter than 0.03 degrees. The
blocker is the corpus, not the code.

### The near-miss: a spurious confirmation of a correct finding

Before gating, BUILD-RESAMP's per-render probe printed recoveries of `0.238x`
and **`-0.967x`** at f=0.05 -- a *negative* sensitivity -- because it divides by
`1 - 0.9877 = 0.0123`, turning a 1% measurement error into an 80% recovery
error. In their words: **"that is arithmetic, not evidence, and it would have
read as a 4x sensitivity difference."**

Section 75's independently measured figure was **4.75x**. They came within one
ungated frequency bin of confirming a true conclusion for a fabricated reason,
and caught it only because a sensitivity came out negative -- not because the
magnitude looked wrong. It did not look wrong. **It looked like agreement.**

> **A spurious confirmation is harder to catch than a spurious refutation,
> because nobody audits the result they were hoping for.**

### A mis-aimed caveat is worse than no caveat

I asked BUILD-HIGHLIGHT to move a warning inline, next to the table it governed.
They complied. Then, auditing their own report with a purpose-built duplicate
detector, they found the warning was **pointed at the wrong table** -- and found
it through the detector's **silence**.

The caveat read *"These rows are ONE measurement, not three"*, sitting directly
above four rows that are four genuinely distinct measurements. The three
collapsed rows had been in an earlier table; when the caveat moved, it attached
to the survivor.

> **A mis-aimed caveat discredits itself.** A reader who checks it against the
> table finds it false and correctly discounts the warning -- and it sits there
> wearing the borrowed authority of a self-criticism.

**This is a defect I introduced by asking for it**, and it is the second time
tonight that a fix has damaged the thing it repaired (section 75's unrestored
mutation was the first). Moving prose next to data couples them; if the prose is
about *different* data, proximity converts a stale note into a false claim.

The honest warning turned out not to be about duplication at all but about
**absence**: that table has **no selector control**, because `edge_mask` ignores
`select_on` outright (`l2_falsecolour.py:73`), so the adversarial-selector
control that overturned half of their section 11 does not operate below that
line. Stronger than the warning I requested, and unlike it, true.

**The method deserves its own line.** They refused to answer by reading their own
tables -- *"reading my own report for a bias I know I have is the same error one
level up"* -- built a detector, calibrated it two-sided (three planted duplicates
-> 2 flags; distinct rows, `0.100` vs `0.101` -> 0), scanned 80 numeric rows,
and reported its two false positives rather than hiding them. Then the finding
came from where it **did not** fire.

> **A calibrated null that contradicts your belief about your own document is
> worth more than any hit.**

### Attribution, corrected in the direction nobody pushes

Section 71's *"the merge is innocent"* was annotated at section 76 as my error.
Its author objected -- to take **more** blame:

> *"I wrote the sentence, and the shared-`den` argument was mine. You escalated
> my conclusion; you didn't originate the error. That distinction belongs in the
> log as a joint miss, not yours."*

Recorded as a joint miss, and section 71's block amended. Both halves were
sound in isolation and neither of us checked the join: **a shared selection is
not a shared amplitude.**

They also flagged the successor claim before anyone could over-trust it: the
axial-CA mechanism is **their hypothesis, generated to explain a residual, still
untested**, backed by two confounded instruments with opposite signs. It goes
forward to the election lane **"with a mechanism and a measurement-shaped hole
where its evidence should be"** -- their phrase, and it travels with the fact.

## 79. The print verdict, and a gate that certifies existence rather than truth

### An unconditioned gamut statistic measures the bokeh

Three subjects were predicted -- by me -- as where out-of-gamut greens would
bite: `flowers-cpl`, `lavendar-cpl`, `flower-bud-with-background-fern-cpl`. All
three refuted. Corrected figures: **`flowers-cpl` 0.25%**, **`lavendar-cpl`
0.00%**. I reasoned from "saturated green macro subject" and never asked what
fraction of those frames is saturated at all. **10 of 26 subjects have no
saturated content whatsoever.**

BUILD-RENDER's own table over-reported, and **looking** is what caught it: the
`flowers-cpl` sheet scored a 90.5% window in which master and printable proof
were indistinguishable by eye, because the crop had landed on background bokeh
and 5 Lab units off a tinted grey is invisible.

> **A gamut statistic not conditioned on saturation measures the background.**
> Almost every macro frame is mostly defocused near-neutral, so an
> unconditioned percentage reports how much bokeh the frame contains -- and
> reports it as a colour problem.

Conditioned on master C\* >= 20, commissioned on two arms *required to
disagree*: tinted neutral **0.00%**, saturated green **100.00%**. Corrections
were large: `flower-bud-alone-cpl` **15.49% -> 3.40%**.

**A 90.5% that looks like nothing is the same near-tie as section 75's
`0.0111 / 0.0097`.** Different lane, different statistic, same trap.

### Deleting an assertion that passed for the wrong reason

> A *sign* assertion I wrote agreed with the data for the wrong reason
> (display-profile TRC, not gamut). **I removed it rather than inverting it to
> fit.**

An assertion that passes for the wrong reason is worse than one that fails: it
keeps passing after the reason changes. Second deletion-over-correction call
tonight, after BUILD-TRIAGE deleted a retyped threshold rather than correcting
it, and both were right.

### The near-black subject prints fine; the defect is upstream

The expected failure did not occur. `coffee-bubbles` scores **1.07** -- the
press slightly *expands* its shadow separation, because black-point
compensation maps master black to paper black. **0 of 26 crushed**, worst 0.66,
midtone control 0.97.

What replaced the dead hypothesis is more useful: the subject carries only
**1.89 L\*** of modulation across **94.67%** of the frame. **Never captured, not
destroyed by print.** That reassigns the defect from output to capture, which is
the distinction this project exists to draw.

Five subjects would not go to a lab as they stand -- yellow-greens to olive
(`flower-inner-edge-cpl` 34.1%, `leaf-2-cpl` 32.2%, `lead-1-cpl` 29.5%) and
blues to slate (`119MSDCF` 25.7%, `109MSDCF` 25.1%) -- and **sharpness is
implicated in none of them.** But the proof ran against **RSWOP, web offset**,
the narrowest realistic target, and the measurer said so themselves:

> **Those five verdicts are almost certainly pessimistic**, and the owner's real
> paper profile would change them more than any available code change.

Filed as `captures-needed.md` section 31. The ICC path is already proven live --
**92 DN** under profile substitution, **3 DN** round trip -- so a real profile
lands on verified machinery.

### Existence is mechanically checkable; truth is not

V-HIGHLIGHT verified BUILD-TRIAGE's definition gate: 31 fields, all defined, no
orphans, reproduced independently off the JSON. Then refuted a number shipped
**inside a field definition** by a factor of six.

| subject | m/f | stated | rel. err |
|---|---:|---:|---:|
| **dry-erase-marker-head-cpl** | **7.138** | 2.316 | **208.2%** |
| bee-2-cpl | 1.918 | 1.429 | 34.3% |

The count of 13/25 holds under two independent criteria. The worst case does
not: `bee-2-cpl` ranks **2 of 25**, and nothing excludes the true leader --
same verdict, same site count. A reader who does the responsible thing and
consults the definition is told the maximum damage is 34% when it is 208%.

> **A gate that proves every field *has* a definition does not prove any
> definition is *true*.** Existence is mechanically checkable; truth is not, and
> the gate's green must say which.

Three definitions were audited for content. **One of the three was wrong.** The
remaining 28 are unverified -- not suspect, unverified, and the distinction is
the whole point of section 75's partitioned-summary rule applied one level up.

### The leak the diagnosis predicted and the fix missed

BUILD-TRIAGE's own caveat was *"the `finally` protects only the state I knew to
restore."* Measured by the verifier: **`commission_wording restored: False`** --
monkeypatched by both mutations, restored by neither, benign only because the
process exits. **The author diagnosed the class and their fix missed the
remaining instance of it**, which is the strongest possible argument for their
own preferred remedy: a subprocess per mutation, so that no `finally` is
load-bearing at all.

### Two verifier behaviours worth naming

**A false positive caught before it landed.** Their first nested-field probe
flagged `evidence` as uncovered; they traced it to their own probe, not to a
defect, and published that they had. A verifier's false positive costs the
author real time.

**A finding in the author's favour, unasked for.** BUILD-TRIAGE's mutation
anchors **fail safe** -- a non-landing anchor makes the run succeed and print
`MUTATION SURVIVED -- FAIL`. That is this project's standing
anti-`replace(x, y, 1)` rule satisfied by construction, found by someone hunting
for the opposite.

## 80. I opened the two subjects that decide the owner's complaint

Two renders judged at 1:1 on the faithful master -- no grade, actual pixels.
This is an eyeball, declared as such, and it is not a measurement.

### The adversarial halo case is clean

`flower-bud-with-background-fern-cpl` is the corpus's hardest geometry:
trichomes crossing a depth boundary, which is precisely where a selection-based
stacker deposits a rim. A hair that is sharp in frame 40 and defocused in frame
41 gives the merge a per-pixel decision with no correct answer, and the classic
failure is a bright halo tracing the hair against the background behind it.

**There is no rim.** Hairs cross from the lit bud surface into the defocused
ground and **fade**, rather than terminating at an edge or doubling into a
ghost. Individual strands stay separable where they overlap. Dew speculars on
the bud surface are clean points, not smeared discs. Pollen grains read as
granular clumps rather than yellow blobs.

The residual softness is real and it is **diffraction**, not merge: at 2x on
f/5.6 behind a 2x teleconverter the effective aperture is far past critical
sampling, and section 12's MTF figures say the finest scales are gone before
any software runs. That is a capture property and no merge can return it.

**The owner's original complaint -- "you must tackle the halo situation, it's
horrendous" -- is answered on the subject most able to reproduce it.**

### The specular fringe is real, visible, and looks field-wide

`coffee-bubbles`, the worst of the three `minor` subjects, at 1:1. The
green-yellow cast on the bright specular arcs around each bubble rim is
**plainly visible** and the card's verdict is honest.

Three things the picture shows:

1. **The speculars are sharp.** The sub-pixel bright points along each rim are
   individually resolved, not smeared. This is a **colour** artifact, not a
   focus or merge-sharpness failure -- which is what the `minor` rank asserts.
2. **The fringe does not strengthen with radius across the crop.** Bubbles at
   different distances from frame centre carry it about equally. That is
   consistent with the per-annulus measurement -- **74% of the deficit present
   at r = 0.04** -- and inconsistent with lateral chromatic aberration, which is
   identically zero on axis and grows monotonically outward.
3. **No halo.** These are bright speculars on a near-black ground, which is the
   bright-object-on-dark-ground geometry where halos are most visible and which
   `captures-needed.md` section 26 exists to isolate. Beyond the genuine
   specular there is no bright rim.

> **This is corroboration, not evidence.** An eye cannot separate a field-wide
> defocus term from a weak radial one, and the mechanism behind this fringe
> remains untested with two instruments disagreeing in sign. What the picture
> settles is only that the artifact is chromatic rather than geometric, and that
> the `minor` rank is not flattering itself.

### Corpus state, counted from the source of truth rather than the page

| verdict | subjects |
|---|---:|
| showcase -- hardest geometry, clean | **7** |
| clean -- no defect found at 1:1 | **14** |
| minor -- small diagnosed defect, named | **3** |
| capture-limited -- the bracket, not the stacker | **2** |
| **total** | **26** |

**21 of 26 carry no defect found at 1:1**, and all three `minor` subjects share
a single unsettled cause. A small note on the count itself: the displayed badge
totals read one higher in every class, because the legend renders one instance
of each badge. My own earlier tally of my own gallery was inflated by exactly
that, in all four classes -- **a legend is a row of examples, and counting the
page counts the examples too.**

## 81. Everything the owner gave us was rendered, and a bare-number search is 5/6 wrong

### Corpus coverage, checked three ways and partitioned

Nobody had verified that every stack the owner delivered actually made it into
the ship set. Checked by set comparison rather than by counting:

```
source stacks with ARW : 26
verdict entries        : 26
rendered masters       : 26

source vs verdicts  diff: NONE - exact match
source vs rendered  diff: NONE - exact match
```

**No stack was silently skipped, and no verdict refers to a subject that does
not exist.** `Compare-Object` in both directions is the check that matters --
three equal counts would pass with a missing subject and a phantom one
cancelling out.

### A retracted number, and what a bare-number search is actually worth

`0.1546x` -- the noise ratio the README calls *"the most persuasive number in
this file"* and then retracts, because it does not reproduce on the shipping
binary (**0.6196x**, `n_eff` 15.077 -> 5.229) -- appears in **11 places** across
the corpus. A naive search flagged **6 of them as unretracted**. Reading them
gave a very different partition:

| site | count | verdict |
|---|---:|---|
| `README.md` | 2 | inside the explicit retraction -- correct |
| `BUILD-PYRNOISE-ADJUDICATION.md` | 5 | **the document is about the number**; it quotes it to prove `REPLICATION EXACT` |
| `SYNTHESIS.md` | 1 | guarded |
| `M91-photometry.md`, `M95-dose.md` | 2 | **coincidental digit collisions** -- `foam`'s planted EV, and a coverage-scale value. Unrelated quantities |
| **`BUILD-THESIS/REPORT.md`** | **1** | **genuine defect -- stated as a live claim, no marker** |
| total | **11** | |

**One real defect out of eleven, and my detector's six accusations were five-
sixths wrong.**

Two failure modes, both already in this log and both committed again by me:

1. **A two-line context window.** Section 76's retraction sat *three pages*
   above the table it governed. Mine looked two lines up and called four
   documents live.
2. **A bare numeric token collides.** `0.1546` is four digits; in a corpus of
   thousands of measurements it occurs by chance, and it did, twice, in tables
   about entirely different quantities.

> **A search for a retracted number finds every place the number is written,
> including the places whose job is to write it.** A document that adjudicates a
> claim must quote the claim. Flagging it is the same error as flagging a
> retraction for containing the thing it retracts.

The rule this project already had -- *anchor a numeric check on a neighbouring
literal, never on the bare token* -- would have cut the six to one directly.
**I own that rule and I did not apply it to my own probe.** Twelfth instrument
failure of the run, and the third of them mine.

### The defect itself

`experiments/BUILD-THESIS/REPORT.md:70` presents **0.1546x** as current fact, in
a report dated today, with no marker -- while the README two directories up
carries a full retraction of it. Its lane has closed, so the number is
**annotated at the point of the claim** rather than rewritten, with the
distinction stated explicitly: *the detail finding that paragraph actually
reports -- no measurable detail difference either way on `leaf-2-cpl` -- is
unaffected; only the noise ratio quoted beside it is withdrawn.*

A retraction that takes a whole paragraph down with the one number it targets
would destroy a measured result that still stands.

## 82. A feature can be finished, tested, documented, and unreachable

### The finding

`STREHL_ROBUST_ELECTION` cannot be turned on in the shipping binary. Not
"defaults to off" -- **cannot be set**, by anyone, by any means.

Six links, each measured:

| # | link | evidence |
|---|---|---|
| 1 | the literal is not in the binary | raw byte scan: `STREHL_ROBUST_ELECTION` **0** occurrences; siblings `STREHL_HIGHLIGHT_KNEE` 1, `STREHL_SMOOTH` 3, `STREHL_RESTORE` 2 |
| 2 | not a stale binary | wiring commit `e0281139` dated 2026-08-24 20:00; exe built 2026-08-26 16:24, **44 h later**; `--is-ancestor ... HEAD` -> 0 |
| 3 | not a feature gate | the only `cfg` in `merge.rs` is `#[cfg(test)]` at L2670 |
| 4 | nothing calls the env reader | workspace scan for `new_robust(` returns **one hit: its own definition**, `merge.rs:850` |
| 5 | production uses the plain ctor | `merge_cmd.rs:2173`, `:3374` -> `FocusStats::new(geom)`, both above that file's `cfg(test)` at L6768 |
| 6 | the tests use the env-free ctor | all 8 `new_robust_with` sites are 4998-5254, i.e. **inside** `merge.rs`'s test module |

In Rust a `const` is inlined at its use sites, so an absent literal is not weak
evidence -- it is **unreachability certified by the linker** rather than inferred
from a null.

### The mechanism, and why it is worth a rule

The test constructor `new_robust_with` takes the arm **directly** instead of
reading the environment. Its doc comment gives the reason, and the reason is
*correct*:

> *"Env-free on purpose... the test suite runs in one process and in parallel, so
> a test that had to set a variable to choose an arm would race every other test
> in the binary."*

That is good practice. It is also precisely what hid the defect. The env-free
path is exercised eight ways; the env-reading path that the CLI would need has
no caller at all. So the suite is green, the feature demonstrably *works*, and
the product cannot reach it.

> **A test that constructs the feature directly proves the feature works and
> says nothing about whether the product can reach it.** Reachability is a
> property of the call graph, not of the unit. No amount of unit coverage
> measures it, and the more carefully the tests avoid global state -- the better
> the engineering -- the more completely they stop testing the wiring.

The cheap detector is the one that caught it: **grep the shipped binary for the
flag's own name.** A gate whose name is absent from `.rdata` is not merely off,
it is unreachable, and that check costs one byte scan and no renders.

### The near-miss, which is the more important half

This finding was **inside an audit that had disqualified itself**. The potency
run printed, above these rows:

```
! NULL FAILED: NULL baseline vs baseline read DEGEN; the renderer is not
  deterministic and no verdict above is meaningful
```

...and exited 2. That verdict was false: the null had *passed perfectly*. The
NULL re-runs the baseline with no args and no env, so it produces byte-identical
pixels **and** an identical banner -- and the degenerate-arm guard upgraded
`DEAD` to `DEGEN` on exactly that unchanged banner. The sibling depth guard four
lines below already carried the right exemption, `prior is None`, with a comment
saying controls are exempt because their expected verdict is a property of
renderer determinism. I wrote that exemption, wrote the reason for it, and
applied it to one of the two guards.

> **A false alarm in commissioning discards the true findings along with the
> noise.** "No verdict above is meaningful" is a load-bearing sentence: it
> invalidates the real rows as thoroughly as the fake ones. A commissioning
> check that fires spuriously is worse than none, because it converts a
> published finding into a discarded one and does it with the full authority of
> a self-check.

Thirteenth instrument failure of the run; the fourth of them mine; and the
first that would have destroyed a true positive rather than manufacturing a
false one. **It is being commissioned by an independent verifier on a 2x2** --
does the null pass, does the guard still fire on a genuine degenerate arm, does
the null still fail under real non-determinism, does the new negative-control
branch fire -- because "the null passes now" would also be true if I had simply
deleted the guard.

### The same scan, run against every flag in the codebase

One byte read found one defect, so it was worth asking whether there were
others. Every `STREHL_*` literal declared anywhere in `crates/`, checked against
the shipped `.exe`:

```
declared: 39   present: 35   ABSENT FROM BINARY: 4
  -> STREHL_BUILD_ID, STREHL_CAPTURES, STREHL_FREEZE_REQUIRE, STREHL_ROBUST_ELECTION
```

**Three of the four absences are correct, and they are the control this scan
came with for free:**

| flag | declared in | why absent |
|---|---|---|
| `STREHL_BUILD_ID` | `strehl-cli/build.rs` | a build script; runs at compile time and is never linked into the product |
| `STREHL_CAPTURES` | `strehl-cli/tests/byte-freeze.rs` | test-only; not compiled into a release binary |
| `STREHL_FREEZE_REQUIRE` | `strehl-cli/tests/byte-freeze.rs` | test-only, same |
| **`STREHL_ROBUST_ELECTION`** | **`strehl-core/src/merge.rs`** | **production source, no `cfg` gate -- the defect** |

Three benign absences with three different, checkable reasons demonstrate the
scan is reading what it claims to read, and leave exactly one flag declared in
production source and missing from the product. **No second instance of this
defect exists**, which is a bounded answer rather than a reassuring one.

### What this scan does and does not prove

The two directions are not symmetric, and conflating them would rebuild the
`DEAD`-glyph problem in a new place:

- **Absent is conclusive.** A `const` is inlined at its use sites, so if the
  name is not in `.rdata` no code can read it. The linker has certified
  unreachability; nothing further need be measured.
- **Present is nearly worthless on its own.** It proves the literal was
  compiled in. It does not prove the code that reads it runs, and it does not
  prove that running it changes a pixel. `--auto-exposure` is present in the
  binary *and* reads `TOKEN`: 325,061 pixels moved, maximum **1 DN**, 0.329% of
  frame. It announces an effect in the banner that no pixel carries.

> **Presence in the binary is necessary and not sufficient; absence is
> sufficient and not necessary.** A name can be linked in and still be dead
> code behind a branch nobody takes. Use the scan to *refute* reachability
> cheaply, never to *establish* it -- establishing it costs a render.

The scan is therefore a fast pre-filter in front of the expensive probe, not a
replacement for it: 39 flags cost one byte read, and the one it condemns needs
no render at all to condemn.

## 83. The complaint is answered, and the comparison still is not

Opened `bee-3-cpl` at 1:1 and as a full frame -- 299 frames, the deepest stack
in the corpus, and the one carrying the strongest claim.

**The artifact the owner called "horrendous" and "entirely unusable" is not
present.** The 1:1 crop lands on the mid-leg: hundreds of individually separable
hairs, tips crossing a bright background, each fading naturally into it. **No
rim, no dark outline, no ghost edge, no doubled strand.** That geometry -- fine
light structures against a bright ground -- is where a halo is loudest, so its
absence there is worth more than its absence anywhere else in the set. Pollen
granules are individually textured; speculars on the black chitin are sharp and
correctly placed.

The full frame holds focus from the near foreleg through the wing tips to the
antenna tip: wing venation crisp with the membrane's cell structure visible,
tarsal claws individually resolved including the small mid-frame ones, the
compound eye a clean dome with correct speculars, and a white ground free of
mottling or silhouette ghosting.

By eye, at 1:1, this is a print-worthy frame.

### Two honest limits on that sentence

**It is soft, and the softness is not the merge's.** Micro-contrast sits below
the best commercial macro work. That is what fact 12 and fact 28 predict: at
this rig's magnification MTF at Nyquist is near zero at every aperture, so the
contrast is destroyed in the optics before any software runs. Selection cannot
recover it and neither can this merge. It is the argument for the deconvolution
work, not evidence against the current pipeline.

**"Print-worthy by eye" is not "state of the art", and I cannot currently claim
the second.** Every instrument aimed at the head-to-head comparison has been
disqualified -- five independent results now, most recently ISO 12233, which did
not go blind but went *wrong*, monotonically, by 14.38% in the flattering
direction. What I can say is bounded and true: **the defect the owner reported is
gone, and the output stands up at 1:1.** What ranks it against another tool
still needs section 30's slanted-edge chart, because the confound lives in the
variable and not in any statistic computed from it.

### A caption that did not demonstrate its own claim

`bee-3-cpl`'s note read *"compound eye resolved"* while its 1:1 crop shows a
**leg**. The claim is true -- the eye is resolved, in the full frame -- so this
was not the `lead-1-cpl` mislabel repeating, and checking the full frame before
accusing myself a fourth time was the right call. But a viewer reading that card
sees a caption about an eye above a crop of a leg, and cannot verify the claim
from what is in front of them.

> **A caption beside a crop is read as a claim about the crop.** Rewritten to
> describe the hairs the crop actually shows -- and to say why that geometry is
> the informative one -- while keeping the full-frame claims explicitly labelled
> as full-frame.

## 84. Two rules I broadcast were wrong, and the fleet corrected both

Twelve agents share one working tree, so I issued a commit-hygiene rule. Two
lanes came back and showed it was incomplete, in two different places, and both
were right.

### Correction 1: path-scoping protects other people's files, not a shared one

BUILD-SHARP: *"path-scoping is necessary and not sufficient; the sufficient
condition is file-exclusive lanes."*

Measured in a throwaway repo. Agent A edits `shared.txt` and **stages** it, so
A's work exists only in the index. Agent B edits the same file in the worktree
and runs `git commit -m "agent B" -- shared.txt`:

```
commit msg : agent B, path-scoped
content    : AGENT-B different change
still staged in index : ''
worktree now          : AGENT-B different change
```

**A's work is gone.** Not committed, not in the index -- the path-scoped commit
*cleared* it -- not in the worktree. No conflict, no warning, exit 0.
`git commit -- <paths>` records **worktree** content and bypasses the index.

And the check I had prescribed cannot see it:

> **A same-file sweep is invisible to a filename audit, because the swept file
> is legitimately yours.** `--name-only` finds cross-lane sweeps and is useless
> against same-file ones. The only check that works is reading the diff you are
> about to record.

### Correction 2: the status check itself lies, but only sometimes

BUILD-ELECT reported that `$LASTEXITCODE` reads **0** after a **failed** git
command piped through `Select-Object -First N`, because `-First` terminates the
pipeline early and the variable keeps its prior value. Their case: real
`index.lock` contention, git exited 128, the loop read 0, committed nothing.

**I tried to reproduce it and got the opposite result** -- a failing
`git commit` through `-First 2` reported 1, correctly. On that evidence they
were wrong.

They were not wrong; my test was. My failing command emitted **one** line, so
`-First 2` was never satisfied and the pipeline drained normally. With three
lines out and exit 42:

```
after -First 1 (3 lines out): 0    <- truth is 42.  MASKED
after Out-Null              : 42
after -Last 1               : 42
```

> **The masking occurs only when the command emits at least N items.** A failure
> printing one line is reported honestly; the same failure printing three lines
> is swallowed silently. Identical code, opposite behaviour, decided by how
> verbose the error happened to be.

Worse than a reliable bug: it passes every terse test and lies the day the
failure is chatty, and lock contention is chatty. **Two careful measurements
reached opposite conclusions because the test was the variable** -- which is the
same lesson as the ISO 12233 confound, arrived at from the process side.

The fix is to stop reading the status variable and assert the artifact: capture
`git rev-parse HEAD` before, and require it to have moved. HEAD moved or it did
not -- no pipeline semantics, no exit-code conventions. Also from BUILD-ELECT,
both measured: **exit codes do not separate** (`index.lock` 128,
nothing-to-commit 1, pathspec-miss 1 -- the two 1s are indistinguishable, so the
code cannot tell "retry" from "never"), and **a retry loop that prints only on
success prints nothing when it fails**.

### Audited rather than assumed

All 13 ORCH commits claimed tonight resolve in the log; my loops used
`Out-Null`, which drains fully and is safe. That is a check I would not have run
without BUILD-ELECT's finding, and "I would have been fine anyway" is not a
reason to skip it -- it is the reason the check is cheap.

The audit also turned up **`docs/research/V-M111-verification.md`**: 46 KB of
independent re-derivation of M111's halo claims, written two days ago and never
committed by its lane. Untracked work is one clean away from gone, and a
*verification* artifact is the class this project can least afford to lose. Now
committed.

### And a fourth false accusation, caught before it was published

BUILD-RENDER pushed back on my calling `coffee-bubbles` a settled reshoot, since
its 1.89 L\* was measured *after* the tone rule and cannot separate "the scene
had no modulation" from "the tone rule gave it none". I told them I was
rewriting section 31 -- **and found nothing to rewrite.** Section 31 contains no
reshoot instruction. I had written that sentence in a *message to them*, and
remembered my own conversation as a document edit.

> **A claim you made in conversation is not a claim in the document, and memory
> does not distinguish them.** The impulse to correct can introduce a defect as
> readily as the original error.

Four this run, two published and two caught by reading the file before writing
to it. Reading first is the entire difference, and it costs one tool call.

## 85. The safety check I issued was itself the defect class

BUILD-SHARP found an **ordering** flaw in the pre-flight probe from section 84,
and verifying it turned up something worse than they reported.

The probe is `git diff --cached --name-only -- <paths>`: non-empty means another
lane has staged work at your path. It works, and it has a clean control --
`shared.txt` fires, `other.txt` is silent. But:

```
[1] probe BEFORE your add:
    diff --cached shared.txt : 'shared.txt'   <- fires
    diff --cached other.txt  : ''             <- control, silent

[2] after you run 'git add -- shared.txt':
    index content : AGENT-B version
    A's work in index? NO - destroyed at ADD, before any commit ran
    probe run NOW : 'shared.txt'  <- still fires, but A's content is already gone
```

**The destruction happens at `git add`, not at `git commit`.** Your own `add`
overwrites the colleague's index entry, so by the time you reach the commit the
evidence is unrecoverable.

And the sting: **the probe still fires afterwards.** Run in the wrong position
it emits output identical to the useful case -- it is now reporting your own
staged change -- so it looks exactly like a working safety check while
certifying a file it has just helped destroy.

> **A check placed after the operation it guards can still emit the signal it
> emits when placed before.** Position is part of the instrument. A probe whose
> output does not depend on whether it ran in time is not a guard, it is
> decoration that resembles one.

Sixth instance tonight of a detector whose useless configuration is
indistinguishable from its useful one -- and the first one that was inside the
safety machinery rather than the measurement machinery.

BUILD-SHARP's second point corrects a confusion of mine: the two probes are
**disjoint**. `git diff --cached` sees a colleague's *staged* work; plain
`git diff` sees their *worktree* edits; **neither sees the other**. I had been
treating them as alternatives. Run both, unconditionally -- deciding which files
are "shared enough to check" is exactly the judgement that fails.

### The standing question

BUILD-SHARP was exposed to section 84's `-First` masking bug and not bitten: their
retry loops piped to `Out-Null` (safe) while their display line used `-First`
(hazardous). Their own account of it is the most useful sentence of the three
corrections:

> **"The two ingredients were one line apart."** *"Anyone auditing my scripts for
> 'does this agent use `-First`?' would have flagged me, and anyone auditing for
> 'does `-First` gate a retry?' would have cleared me. Only the second question
> is the right one."*

Which generalises past git, and is now standing doctrine for any instrument here:

> **What property of the input decides whether this check can see anything, and
> have I varied it?**

Three lanes arrived at that class tonight from unrelated directions -- a shape
test blind past 2.69 px, a band statistic confounded by the variable it
compares, an exit-code probe whose honesty depends on how many lines the failure
printed. **In every case the controls were green and the governing property was
one nobody had thought to vary.**

### Three corrections in one night, all from lanes

Path-scoping is insufficient for shared files (BUILD-SHARP). The status variable
lies conditionally (BUILD-ELECT). The pre-flight probe must precede `add`
(BUILD-SHARP). All three were rules I issued; all three were corrected by the
agents receiving them; all three were verified here before rebroadcast, and one
was *sharpened* in verification rather than merely confirmed.

## §86 — a boolean pass carries no scale; the magnitude caught what the boolean could not

V-HIGHLIGHT confirmed that a path-scoped commit over a colleague's staged file leaves
that colleague's content in the object database as a **dangling blob**, recoverable with
`git cat-file -p <sha>` — but only until the next prune, and `gc --auto` fires on its own.
So the question stopped being theoretical: *had any lane already been swept tonight?*

**Protection first.** `gc.auto` was **unset**, so git's 6700-loose-object default was live
and an ordinary operation could have closed every recovery window without anyone asking.
Set `gc.auto 0`, repo-locally and reversibly. The window is now held open indefinitely.

**Then the census.** Eleven dangling blobs: three `.commitmsg` files, two cargo build logs,
five substantive. The three `.commitmsg` blobs are the sweep mechanism operating in the
wild, benignly — agents `git add`ed them and a later path-scoped commit cleared the index
entry. Field confirmation of BUILD-SHARP's finding, at zero cost.

For the five that mattered I ran two tests, and the second one caught the first one lying.

**Test 1 (boolean).** Grep a distinctive mid-document line from each blob against HEAD;
does the content still exist anywhere? All five: `content-present-in-HEAD = True`.
Reassuring, and for one of them **false**.

**Test 2 (magnitude).** For each blob, how many substantive lines exist *only* in the blob?

| blob | mapped file | blob | head | only-in-blob |
|---|---|---|---|---|
| `72176f909b` | `docs/research/V-ca.md` | 359 | 359 | 0 |
| `d785b4dadd` | `docs/research/M81-estimation-merge.md` | 333 | 474 | 0 |
| `5d1502b39f` | `docs/research/M4-fpn-measured.md` | 584 | 659 | 6 (prose rewording) |
| `f64a1dec4f` | `experiments/m2-fpn/src/main.rs` | 1157 | 1086 | 34 (M2-era refactor) |
| `33130a9e59` | ~~`crates/strehl-cli/examples/m65-election.rs`~~ | 695 | 656 | **422** |

That last row is not a draft. A 422-line divergence is impossible for a file revised in
place — and the impossibility was a statement about my **mapping**, not about the content.
The grep had matched `m65-election.rs` on a generic line shared by every FPN experiment
file. The blob's real home is `experiments/m2-fpn/src/stats.rs`, found by anchoring on its
own first line instead of a middle one. Re-run against the correct target: `blob=695
head=925 only-in-blob=0`. Strictly an earlier draft. No loss.

**Verdict: no lane lost work.** All five are earlier drafts of files that still exist and
are tracked.

The rule is the shape of the error, not the outcome:

> **A boolean pass carries no scale, so it cannot self-check.** `True` looks the same
> whether the identification was right or wrong. Ask the same question in a form that
> returns a **magnitude** and an implausible number will expose an error in your
> identification rather than in your subject.

This is the fourteenth instrument tonight whose failure mode resembled its intended
output, and the first one caught not by suspicion but *by arithmetic that refused to be
plausible*. Worth preferring on those grounds alone: vigilance does not scale, and a
number that cannot be true does not require anyone to be paying attention.

A corollary for the identification step itself: **anchor on a line unique to the artifact
(its first line, its title) and not on a line sampled from its middle.** A middle line is
drawn from exactly the population a sibling file also draws from. This is the same medicine
as §81's "anchor on a neighbouring literal, never the bare token", arriving from the other
direction — there the token was too common inside one document, here it was too common
across a family of them.

V-HIGHLIGHT also sharpened the `-First` boundary: masking occurs at **`N <= lines`**, not
`N < lines`. `-First 3` on exactly three lines is still masked, because `-First` stops the
instant it has N items and never lets the upstream signal completion. The intuition "if it
consumed everything it must have drained" is wrong, and it is the version a careful person
will reason their way into trusting. They added `Select-String` and `Select-Object -Skip`
to the verified-safe list — `Select-String` being the one most of us actually reach for.

## §87 — the check fired on the side nobody reads, and "no trace anywhere" had a fourth place

Two claims from BUILD-HIGHLIGHT, measured in a throwaway repo before rebroadcast. They split:
one corrected a rule I had issued to eleven agents, the other was wrong in an instructive way.

### The polarity defect — CONFIRMED, my rule was wrong

I had told the fleet: before committing a shared file run `git --no-pager diff -- <path>` and
stop if it contains changes you did not make. Same collision as §84, both probes side by side:

```
git diff -- shared.txt            (the rule I issued)
  -AGENT-A halo work, staged not committed    <- the endangered work, as a MINUS
  +AGENT-B different change                   <- your own, as a PLUS

git diff --cached -- shared.txt   (the amendment)
  -ORIGINAL baseline line
  +AGENT-A halo work, staged not committed    <- the endangered work, as a PLUS
```

Both probes surface the collision, so my rule was not inert — it was **mis-polarised**. The
instruction says *"changes you did not make"*, and a reader scanning **additions** for foreign
content sees only their own edit and passes. The colleague's work sits on the minus side, where
it reads exactly like you replacing your own earlier draft.

> **A check can fire correctly and still fail, if it presents the evidence in the polarity the
> reader is not scanning.** Firing is not the same as being read. Position was §85's lesson;
> **presentation** is this one, and it is the subtler of the two.

Note the compounding: my own pre-flight already gated on `--cached` — I wrote the correct check
for myself and the weaker one into the rule. Nobody audits the instruction against their own
practice, because the practice feels like the source of the instruction.

### "The evidence of the failure is exactly what the failure deletes" — REFUTED

BUILD-HIGHLIGHT argued no retrospective audit could ever clear a lane, since destroyed index
content leaves no trace *"not in the commit, not in the index, not in the reflog."* All three
correct. The conclusion is false:

```
A's staged blob : 65084333b90290e18ba8ca8ce9ace0ce9e814203
after the sweep : dangling blob 65084333b90290e18ba8ca8ce9ace0ce9e814203
git cat-file -p -> 'AGENT-A halo work, staged not committed'
```

`git add` writes the blob to the **object database**; the path-scoped commit only detaches the
index entry. §86's census is the audit they had proved impossible, and it came back clean.

> **An exhaustive-sounding list of the places you checked is not an exhaustive list of places.**
> Three correct negatives, delivered with the cadence of completeness, and the trace was in the
> fourth. The rhetorical form of exhaustiveness is available to an incomplete search.

This is the same error as §82's binary scan in the opposite direction — there, absence in the
places I looked *was* conclusive and I had to argue why; here it was not, and the argument was
never made because the list sounded finished.

### Two smaller instruments, same family

**`Measure-Object -Line` silently drops empty lines.** It reported this log at 7614 lines when
`(Get-Content).Count` gives **9866** — a 2199-line discrepancy, and had I quoted it the log would
carry a false measurement of itself. Fifteenth instrument tonight whose output has the shape of
the thing you wanted. Use `(Get-Content $f).Count`.

**`write_agent` fails atomically.** One mistyped recipient id and *zero* of eleven were delivered,
reported loudly. That is the correct design and worth naming, because the tempting alternative —
deliver to the ten valid ones and warn — would have produced a fleet in two different states with
a warning nobody re-read. **Partial success is the failure mode that hides; all-or-nothing is a
kindness.**

## §88 — three probes said no fringe, the fringe was visible, and each said no for a different reason

The remaining defects on the 26-subject corpus are three specular fringes and two soft
subjects. I went to check the two "capture-limited" verdicts, because *capture-limited*
is a self-exculpating conclusion and BUILD-HIGHLIGHT had just handed me the warning that
fits it exactly: **a mechanism that explains why a measurement must hold is the point of
maximum danger.**

`flowers-cpl` survives inspection: trichomes crisp and individually separable, tips clean
against the bright field, pollen textured, no rim. The soft regions are genuine fore- and
background bokeh outside the bracket's depth range.

`flower-bud-alone-cpl` does not. At 1:1 I read a pink rim on the bud silhouette. Three
probes then told me it was not there.

**Probe 1 — silhouette average.** Mean `(R-G, B-G)` over the whole subject/background
boundary: −3.98 / −3.06, both negative, no magenta. *Failure mode: dilution.* The rim is
confined to a few edges and the boundary is mostly green-bud-to-white; the average is
dominated by the population that has no defect. Both of its controls **skipped** for lack
of a blown background, so it was also uncommissioned — a verdict from an instrument that
had failed to demonstrate it could produce any other verdict.

**Probe 2 — local extremes, gated on `|grad luma| >= 60`.** Returned **`edge px = 0`** on
the suspect region *and* on the interior control. *Failure mode: the gate excluded the
defect before the statistic ran.* The rim sits on a **pale bud against white** — a
low-luma-contrast, **high-chroma-contrast** boundary. A luma-gradient gate is structurally
blind to precisely the class of defect it was built to hunt. The shuffle control did fire
(30,393 edges), which is how I knew the zero was real and not a crash.

**Probe 3 — `min(R-G, B-G) > 6 DN` on a chroma-gradient gate.** Scored `flower-bud-alone`
at **0.00%, the lowest of all eight subjects tested.** *Failure mode: the operator encoded
an assumption about the fringe's hue.* `min(R-G,B-G)` demands magenta — both channels above
green. The rim is **red-dominant with blue still below green**.

Three negatives, three different mechanisms, one plainly visible defect. The 3× blowup
(`ORCH-budtip-3x.png`) settles it by eye, and reading the raw pixels settles it by number:

```
row 40   interior              rim band                background
  R-G    +11 +11 +13 +12 +14   +18 +21 +22 +20 +21   +9 +5 +3 +2 -1 -4
                                       ^^^ peak
```

**A mixture of two endpoints cannot exceed both endpoints.** `+22 > +11` and `+22 > −4`,
so this is a chromatic **overshoot** — a reconstruction artifact — not an alpha blend and
not simultaneous contrast, which was the live alternative hypothesis and is hereby refuted.
Reproduced at rows 40/60/90 (+22/+16/+13 against interiors of +11/+11/+8). Row 120 lies
entirely in background and stays flat at −3..−7: the negative control is inside the same
measurement.

Two findings follow, and the second one is the reason the first was worth chasing:

1. **It is a different defect from the specular fringe.** Probe 3's statistic, which fails
   here, *is* commissioned for the other family: `4.19 / 4.30 / 3.98 %` for the three
   reported specular subjects against `1.37 / 1.07 / 0.14 / 0.01 %` for four showcase
   subjects — a clean gap. The gallery card had grouped them as one "unattributed edge
   fringe"; that grouping is now measured to be wrong and the card is corrected.
2. **It discriminates a hypothesis the specular subjects cannot.** This is a diffuse edge.
   Specular clipping has no reason to act here; per-channel focus election does. The two
   instruments that returned opposite signs (−85% / +42%) were both aimed at speculars,
   where both mechanisms are live — which is a candidate explanation for the disagreement
   itself. Routed to BUILD-ELECT with a pre-registered kill condition.

The rule, which is the sharpest form of the standing question yet:

> **An operator encodes a hypothesis about the defect.** A gate encodes one about where it
> lives, an average encodes one about how widely it is spread, and a colour score encodes
> one about its hue. All three of mine were wrong in different directions, and each
> returned a confident, quiet negative. **When a detector disagrees with your eyes on a
> visible artifact, the detector is the thing to doubt first** — and the useful question is
> not "is it broken" but *"which assumption did I compile into it?"*

A corollary I want on the record because it nearly cost me the finding: I built probe 2
*specifically to fix probe 1's dilution*, and introduced a worse blindness while doing so.
**A fix aimed at a known failure mode is not thereby free of new ones**, and the confidence
of having just corrected something is the worst possible frame of mind for auditing the
correction. Third time tonight a repair damaged what it repaired (§75, §78, and now this).

## §89 — the verifier accepted a path and verified something else

Correcting the `flower-bud-alone` card meant rebuilding the gallery. `build_view.py`
takes `src` and `out` positionally and defaults to `GALLERY-NOW` -> `VIEW-NOW`, so my
rebuild went to **VIEW-NOW**, while every asset I had been measuring lives in
**VIEW-SHIP**. I then ran `verify_gallery.py`, which printed **GALLERY VERIFIED**.

It was verifying a third directory, `C:\dev\strehl-out\VIEW`.

Three galleries exist, and the verifier's own paths were module constants:

```
OUT  = C:\dev\strehl-out\VIEW        <- asset root
SHIP = C:\dev\strehl-out\SHIP-V1     <- master set, superseded by SHIP-V2
IDX  = OUT / "index.html"
```

`main()` let `sys.argv[1]` override **`idx` only**. Passing
`VIEW-SHIP\index.html` therefore read the right document and checked its assets against
the wrong directory and its coverage against a **superseded master set** — producing a
verdict that belonged to no single artifact. Given a real path it crashed on a file in
`VIEW\assets\`; given no path it printed a clean bill of health for a page I was not
looking at.

> **A tool that accepts a path argument but keeps its other paths in constants will
> verify a different artifact than the one you named — and the argument is what makes
> you believe it did not.** Supplying a target creates the appearance of targeting.
> Either derive every path from the argument, or print them all and let the reader see
> the mismatch.

It now prints `index / assets / masters / format` before any verdict, and derives the
master set from the asset filenames. This file's own docstring says a generator's
self-report is worthless because it uses "the same variables it used to build the page."
The verifier had the sibling defect: **its variables were unrelated to the thing it was
asked about**, which is worse, because it is not even self-consistent.

Two further defects surfaced once it was pointed at the right page, both from the page
format drifting underneath a pattern:

- **`<h2>([^<]+)</h2>` matched nothing.** Headings gained an inline badge span, and
  `[^<]+` stops at the first `<`. Result: **0 cards against 26 card sections**, so every
  master reported `no card`. The failure was loud, but its *shape* — "no card" for
  everything — reads like a catastrophically broken page rather than a stale regex.
- **Stripping tags left the badge's text**, turning every heading into
  `bee-1-cpl--SHIP-V2 showcase`, so every card then reported as an `orphan card`. A fix
  aimed at the first defect produced a second one with an equally confident output.
  Fourth time tonight (§75, §78, §88, here).

And one that was not a defect at all: `cards missing a quality tag : 26`. The tag and
prose checks were written for a legacy `t-*/g-*` taxonomy; this page uses `badge b-*`.
Twenty-six perfectly good cards were being failed by checks that **did not apply**. Per
the standing partition rule, inapplicable is now reported as `n/a` with its reason rather
than as `0` (which would read as a pass) or as `26` (which reads as a failure):

```
broken image src              : 0
masters with no card          : 0
cards with no master          : 0
cards missing a quality tag   : n/a (badge-format page; legacy tag taxonomy)
1:1 crops under 700px         : 0
GALLERY VERIFIED
```

**Commissioned before being believed**, on a pinned copy of the whole tree — the index
alone is insufficient, since assets resolve relative to it:

| arm | got | expected |
|---|---|---|
| NULL, unmutated | GREEN | GREEN |
| M1 broken `<img src>` | RED | RED |
| M2 deleted one card | RED | RED |
| M3 unbalanced container | RED | RED |
| NULL2, restored | GREEN | GREEN |

5/5. Each mutation is anchored on a unique substring and hard-errors if the anchor is
absent, because a mutation that fails to apply yields a GREEN indistinguishable from a
passing control — the lesson already paid for once tonight.

The deliverable at `VIEW-SHIP` is now genuinely verified: 26 cards, 0 broken sources, 0
orphans, 0 uncovered masters, and the corrected `flower-bud-alone` card live.

## §90 — the crop that shows your best work is the crop that hides your worst

BUILD-WIRE's live intent line read "Blocky election seams seen directly", so I went
looking for a periodic tile lattice in the shipped masters, independently of their
detector so that agreement would mean two instruments rather than one read twice.

**I never found a seam. I built three detectors that could not have found one, and then
found a different defect by looking.**

### Three failures, each producing confident, well-formed output

1. **It read the wrong artifact.** v1 scanned `VIEW-SHIP\assets\*.jpg` — the gallery's
   own preview derivatives — and reported strong periodicity at p=8 with ratios of 24 to
   38, plus lines at 48 and 64. That is the **JPEG DCT lattice and its 16-px MCU
   harmonics**: a property of my viewer, not of the stacker. Had the plant control not
   also been flat, I would have reported blocky seams in the product. This is §89
   committed a second time inside an hour — measuring a neighbouring artifact and
   attributing the reading to the one I named.

2. **It deleted the frequency it was probing.** v2 detrended with a fixed 65-tap moving
   average before the FFT. That is a high-pass with a cutoff near wavelength 65, so a
   period-128 component was *removed by the instrument* before the measurement. The
   planted seam registered a gain of **1.0x** — exact silence — and the silence read as
   "no seam". The fix is to scale the detrend window with the probed period.

3. **It went deaf at the real bit depth.** With the detrend fixed and reading properly,
   an amplitude ladder on `109MSDCF` gave 2.6 -> 9.1 across a 32x range of planted seam
   amplitudes, never reaching the firing threshold. The detector *responds* and cannot
   *conclude*. I stopped there rather than engineer a fourth version.

> **A detector's silence is worth nothing until it has been made to speak at a stated
> amplitude.** "Clean" is only meaningful as "no defect at or above X", with X measured.
> Reported without X, it is indistinguishable from deafness — and all three versions
> above would have been reported as "clean".

### The library was quietly halving the data

While diagnosing, PIL opened a 188.6 MiB master and returned `mode='RGB'`, `dtype=uint8`,
`max=255`. Parsing the IFD out of the raw bytes, with no library in the path:

```
BitsPerSample   [16, 16, 16]      SampleFormat  [1, 1, 1]
Compression     1                 Photometric   2
ImageWidth 7032   ImageLength 4688   -> 197,796,096 bytes raw, file is 197,798,531
```

**Sixteen bits per sample, and Pillow 12.2.0 hands back eight without an exception, a
warning, or a flag.** What it returns is a perfectly well-formed RGB array, which is why
nobody notices.

> **A library that silently narrows your data does not return something broken. It
> returns something well-formed.** There is no defect in the object to find; the loss is
> in the difference between the object and the file, and nothing in the object records it.

Scope of the damage: my own seam scripts only. `build_view.py` already uses `tifffile`,
and §88's chroma transects deliberately read the 8-bit crop PNG, so the +11 -> +22 -> -4
overshoot stands — it was a claim about *shape*, and shape survives a monotone map.

### The same header carried an unshipped product requirement

`XResolution 1/1`, `YResolution 1/1`, `ResolutionUnit 1` — TIFF's "no absolute unit".
**The masters carry no DPI at all.** The `Software` stamp landed (`strehl 0.0.0`); the
resolution half of that task did not. For a deliverable whose entire acceptance criterion
is *print-worthy*, a print shop opening this gets no physical size and invents one.
Routed to BUILD-WIRE with the parser, and with the instruction to read the tags back out
of the written file using a parser other than the one that wrote them.

### What actually found the defect: inverting the crop selector

`build_view.py` picks its 100% crop by **maximum high-frequency energy**, so it lands on
the finest texture in the frame. That is the right choice for judging resolution and it
is the worst possible one for finding anything that hides in texture and shows in smooth
tone. **Every 1:1 crop this project has examined was selected to land where such defects
are least visible.**

> **A sampling rule that optimises for one quality has, by that same rule, blinded itself
> to that quality's complement.** A census is not complete until something is cropped by
> the *defect's* logic rather than the subject's. The gallery was not hiding anything; its
> selector simply could not point at this.

Inverting it — lowest-texture eligible block, excluding near-black and near-clipped —
found the defect immediately, in the first two subjects tried:

| master | crop | what is there |
|---|---|---|
| `coffee-bean--SHIP-V2` | (6000,900) | horizontal dash-shaped dark streaks, ~60-100 px long, soft-ended |
| `flower-bud-alone-cpl--SHIP-V2` | (900,2400) | round dark discs, ~40-70 px across |

**One cause, two shapes: dust in the optical path.** A defocused mote images as a disc;
the inter-frame warp smears it into a dash when the stack moved and leaves it a disc when
it did not. The shape is a readout of how much the aligner had to move that stack.

Measured honestly: the crop spans 59643..62587 of 65535, a 4.5% range, **12 levels once
mapped to 8-bit**, with the dust a few levels below local background. Under a 30x linear
stretch it is blatant. At native 1:1 it is faint but genuinely visible. On a large print
of a near-white field, a few levels of round mottling is what gets a print rejected.

This is item 3 on the owner's own list of gaps, where it is described as "the kind of
defect reviewers of a SOTA claim find in five minutes." It took five minutes, and only
because the crop was chosen by the defect's logic instead of the subject's.

Assigned to BUILD-BLEND in a new module no lane holds, with the design that removes the
dependency on the unshot flat-field capture: **the stack is its own flat field.** Dust is
fixed in sensor coordinates and the subject is not, so an exposure-normalised accumulation
in *sensor* coordinates, before any warp, leaves the subject averaged away and the dust
standing exactly still. Deep stacks make this stronger, not weaker; `bee-3-cpl` has 299
frames. Pre-registered: a stated DN reduction at the two named crops, an unflagged subject
that must come back unchanged within noise, and a kill on any loss of real texture.

## §91 — "wrong by a constant factor" is the most dangerous description of a lossy conversion

I broadcast the PIL truncation to the fleet and told them the damage was that magnitudes
were "wrong by a factor of 256". BUILD-RESAMP measured that sentence and it is harmful,
because **it names a repair, and the repair does not work**:

```
tifffile : uint16   distinct 10440   min 202   max 14439
PIL      : uint8    distinct    57   min   0   max    56
PIL x256 : float    distinct    57   min 0.0   max 14336.0
```

The multiplication restores the scale to within 0.7% and **none of the information**.
Ten thousand distinct values become fifty-seven and *stay* fifty-seven; every recovered
value is a multiple of 256, so true DN is known only to +/-128. The floor is destroyed
as well: `min 202 -> 0`. BUILD-SHARP confirmed it independently on a different file —
11,902 distinct values via tifffile against 57 via PIL, floor 239 -> 0.

> **A scale error is invertible and preserves the count of distinct values. Quantisation
> destroys the count.** So the diagnostic and the disproof are the same statistic, and
> `len(np.unique(arr))` needs **no reference image and no knowledge of what the number
> should be** — which is exactly why "wrong by 256x" required a reference to be caught
> and the unique-count does not.

A lane that applied my repair would hold right-magnitude numbers with 183x too little
tonal resolution, produced by arithmetic that looks like a fix. And it composes with §90:
the dust sits a few levels deep on a crop spanning twelve 8-bit levels, so a PIL-based
dust survey carries one or two levels of signal at a 256 DN quantisation step and would
report **clean on a defect plainly visible to the eye**. The first hazard manufactures a
false negative on the second hazard's subject.

BUILD-SHARP's generalisation, which is the sharpest form of it:

> **A check that certifies the input rather than the output.** They cleared their lane
> with "no `Image.open` anywhere" — a true statement about their *source code*, which
> would not have caught the hazard arriving through a dependency, a cached array, or a
> file another lane wrote. Counting uniques interrogates the array actually measured.
> Structural arguments are cheap and belong first; they do not substitute for reading the
> artifact.

### My own tool had the defect I was warning about

BUILD-RESAMP also measured a real bias in `orch_smoothcrop.py` — the tool I told the
fleet to run "before you call anything clean". Its stretch used **per-block percentiles**,
so display gain varied per crop and identical 40 DN dust read up to 29x differently
between fields, with the bias running the wrong way: the **flatter, cleaner** field was
amplified more and therefore looked dirtiest. My instruction invited precisely the
cross-master ranking that bias invalidates.

Fixed: high-pass at 201 px — dust is local and the scene gradient is not, and at a fixed
gain wide enough not to clip the gradient the defect is too small to see — then a fixed
+/-250 DN window, so gain is a stated constant (0.5100 levels/DN) and clip% is printed
per crop.

**The first commissioning run said NOT COMMISSIONED, and it was right about my harness.**
Severity came back *negative* for the busy field: my "clean" reference was a fixed distant
patch that landed on a trough of the synthetic sinusoid. A defect's depth is local by
definition; measuring each disc against its own annulus fixed it. Fifth time tonight that
a repair introduced a fresh defect (§75, §78, §88, §89, here).

Then the mechanism test, with the prediction registered **before** the run — that the
residual difference was clipping, and must therefore vanish as the window widens:

| window | busy sev | busy clip | flat sev | flat clip | ratio |
|---|---|---|---|---|---|
| 250 | 14.12 | 36.84% | 20.75 | 0.00% | 1.47x |
| 500 | 9.75 | 7.13% | 10.37 | 0.00% | 1.06x |
| 1000 | 5.18 | 0.03% | 5.19 | 0.00% | 1.00x |
| 2000 | 2.59 | 0.00% | 2.59 | 0.00% | 1.00x |

Confirmed exactly. The residual is clipping and nothing else.

> **Do not move a gate you failed; find the mechanism and predict its signature in
> advance.** I could have relaxed the 1.3x threshold to 1.5x and shipped. Registering
> "if this is clipping, widening the window must collapse it to 1.0" converted an
> uncomfortable number into a measurement, and the tool now reports clip% so the
> comparison's validity condition is visible in its output rather than in a caveat
> someone has to remember.

### What the corrected render then showed

At the comparable gain, the `coffee-bean` crop is unambiguous and carries **two**
defects, not one:

- **Dozens of dust trails, all uniformly horizontal**, in loose diagonal rows. The
  uniformity of orientation is the diagnostic: independent debris would vary in shape and
  angle, whereas one shared elongation direction means one shared displacement — the
  aligner's inter-frame translation. This yields a free falsifiable prediction handed to
  BUILD-BLEND: **trail direction and length must match that stack's fitted per-frame
  translation**, or the sensor-coordinate model is wrong.
- **Isolated single coloured pixels** throughout — hot/stuck pixels surviving into the
  shipped master, and the half of the brief the dark frames answer.

They want opposite treatments and must not be merged: dust is a multiplicative
obscuration spread over tens of pixels, corrected by division; a hot pixel is an additive
single-pixel outlier, corrected by exclusion from the gather.

## §92 — a commissioning plant certifies only against the confound it resembles

I tried to turn §90's eye-level dust finding into a corpus-wide number. Two instruments,
and the second one **passed its own commissioning and was still wrong**.

### First instrument: deaf on row one

Per-master statistic — high-pass the smoothest block, measure the dark-tail excess past
`k*MAD`. It died on the first master it saw:

```
109MSDCF   real 1.578%   planted 1.579%   gain 0.001   MAD thr 1571 DN
```

A 60 DN plant moved the statistic by 0.001 against a threshold of 1571 DN. The reason is
structural, not a tuning miss: a 900 px block high-passed at 201 px is dominated by
**scene** structure, so MAD measured subject contrast and both the threshold and the tail
scaled with the subject. The `real 1.578%` reading was a number about composition wearing
the units of a defect. Had I not planted, I would have published it.

### Second instrument: the right physics, commissioned, and still wrong

Dust is fixed in sensor coordinates; subjects are independent between shoots. So take the
**median across masters**: a feature in 1 of 15 cannot survive a median, a feature in 15 of
15 is reinforced. Fifteen masters share the 7032-wide frame exactly. Commissioning had
three arms and the middle one was the point:

| arm | plant | depth |
|---|---|---|
| COMMON | same coordinates in all 15 | 1.5609 |
| INDEP | random coordinates per master | 0.0809 |
| NULL | unplanted, same sites | −0.0391 |

Sensitivity 1.60, discrimination 0.05 — INDEP is 5% of COMMON. **COMMISSIONED.** It then
reported 1319 connected blobs, 1.63% of pixels past median−6σ, the strongest at −7.7σ.

That is a dust map, and it is a lie.

### The discriminator that killed it

The blobs clustered at y≈1500–3300 of 4688 — the vertical middle. **Every macro subject is
centred**, so "appears in the middle of every frame" is a property dust and subject texture
*share*. My INDEP arm planted at random coordinates, so it tested rejection of
**independent** structure; the confound that actually defeated the instrument is
**common**, exactly like the signal. No randomly placed plant can express it.

Dust is a *fixed physical pattern*, so it must reproduce across disjoint subsets. Split the
15 into 8 and 7:

| split | correlation | blobs | top-60 overlap |
|---|---|---|---|
| REGISTERED | 0.0922 | 683 / 1286 | **0.0%** |
| SHIFTED (roll 137) | 0.0143 | 683 / 1286 | 0.0% |
| SHIFTED (roll 311) | 0.0030 | 683 / 1286 | 1.7% |
| SHIFTED (roll 613) | 0.0149 | 683 / 1294 | 1.7% |

**Zero blob overlap between disjoint halves** — the registered split does no better than
one deliberately knocked out of registration. The radial profile settles it:

| radius band | share of blob px | share of area | enrichment |
|---|---|---|---|
| 0.00–0.25 | 26.39% | 4.91% | **5.38x** |
| 0.25–0.50 | 45.48% | 14.72% | 3.09x |
| 0.50–0.75 | 22.35% | 24.55% | 0.91x |
| 0.75–1.00 | 5.66% | 34.35% | 0.16x |
| 1.00–1.50 | 0.12% | 21.47% | **0.01x** |

Five-fold enriched at the centre, five-hundred-fold depleted at the corners. Dust is
spatially uniform — if anything edge-favoured, since central texture hides it. This is a
map of **where macro photographers put the subject**.

> **Commissioning is not a general warrant. It is a warrant against the specific
> alternative the plant embodies.** A plant proves the instrument can tell the signal from
> *that* plant's absence, and nothing more. Before trusting a passed commissioning, name
> the confound you actually fear and ask whether the plant resembles it. Mine did not: I
> controlled for independent structure and was defeated by common structure.

> **Prefer a control that varies the property the physics depends on, over one that varies
> amplitude.** The amplitude ladder said COMMISSIONED. The registration ladder — the same
> data with sensor alignment destroyed — said the registered answer was no better than
> noise, and it cost three `np.roll` calls.

### What survives, and what it means for the build

§90's dust stands: it was **seen at 1:1 at a stated, fixed display gain**, which is a
different and stronger kind of evidence than a summary statistic. What §92 removes is the
*cross-master shortcut*, and the reason is instructive — the masters do not share an array
origin (the corpus splits 15/11 across two widths, 8 px apart, and per-stack alignment
crops need not agree), and the CPL joined the kit partway through, so a common sensor
coordinate is not a common array coordinate.

Which lands exactly where BUILD-BLEND is already building: **the correct level is
within-stack, not across-masters**. A stack's own frames share an origin by construction,
dust is fixed while the subject moves under the warp, and none of §92's confounds apply.
The negative result confirms their level and refutes only my shortcut.

One residual: registered correlation 0.0922 against a shifted control of 0.0108 — 8x, so a
weak genuinely-registered term exists. Given the radial profile it is most likely a
vignetting or warp-boundary residual, not dust. Unresolved and logged, not claimed.

## §93 — nobody audits a withdrawal

V-HIGHLIGHT returned the sharpest single observation of the night, and it is about a
failure mode this log has not named in ninety-two sections, because every instrument error
catalogued so far has run in the opposite direction.

They built a ladder to test whether the highlight roll-off knee left a seam. Version one
scored the **global** maximum adjacent-bin jump, which a natural 60 DN scene feature
dominated, so the statistic never moved:

```
      0.25        60.00         no
     16.00        60.00         no        <- a 16 DN plant, invisible
```

A 64x change in plant amplitude, one constant reading — the same zero-variance signature as
§86's boolean. Their conclusion had they trusted it:

> **NOTHING DETECTED UP TO 16 DN — the statistic is deaf and the claim must be withdrawn.**

The claim was **true**. The instrument was deaf. And then the part that matters:

> Every instrument error I caught in myself tonight until now was a false positive —
> accusing working code. This one is the mirror, and the asymmetry matters: a false
> positive costs an author time and gets argued down, but **a false negative that retracts
> a true claim is self-ratifying, because the retraction looks like rigour. Nobody audits
> a withdrawal.**

> **A retraction is the least-audited artifact a rigorous project produces.** A false
> positive has a defendant — the author whose code was accused will push back, and the
> error surfaces. A false negative that withdraws a true result has no defendant: the
> author is the one withdrawing, the reviewers see conservatism, and conservatism is not
> the thing anybody checks. **The very culture that makes this project's claims
> trustworthy is what makes its withdrawals invisible.**

The corrective is symmetry, and it is cheap: **hold a withdrawal to the same standard as a
claim.** Before retracting, require the instrument that produced the null to have been
shown to speak at a stated amplitude — the same ladder §91 demands before reporting clean.
If it has not, the honest outcome is neither the claim nor its retraction, but an open
question with a named missing measurement.

This bears immediately on live work. `README.md:1090` carries a five-result retraction, and
V-NYQUIST is adjudicating whether a NO-GO and that retraction should re-open. I have
forwarded the rule with an explicit instruction *not* to treat it as a thumb on the scale:
it says where to point scepticism, not which way to rule. A confirmed retraction is a fine
outcome; an unexamined one is not.

### What V-HIGHLIGHT did after fixing the ladder

Requiring the excess to track the plant one-for-one (1.00 DN per DN) made v1 unpassable.
The repaired instrument then **confirmed the original finding** and qualified it:

- natural jump at the plant boundary (43000 DN): **0.00 DN**
- 95th percentile of other adjacent-bin jumps: **27.60 DN**
- detection threshold: A=16 no, A=32 yes

So Phase 1 §6's unqualified *"There is no seam"* becomes **"no seam at or above 32 DN in
the level-binned response on `foam`"** — the continuity result survives intact, and the
floor is now stated: ~0.05% of full scale, set by the roll-off's own steep growth rather
than by sensor noise. **A 10 DN seam would have passed unseen.** That is what a qualified
all-clear looks like, and it is strictly more useful than the unqualified one it replaces.

### A refinement to §91 that matters more than it looks

V-HIGHLIGHT re-measured the PIL truncation on their own file and found the mechanism is a
**right-shift, not a rescale**:

```
tifffile -> uint16 max 23224 | PIL -> uint8 max 90 | ratio 258.04
```

Not 256. `23224 >> 8 = 90`, and 23224/90 = 258.04. So §91's warning gets sharper: a number
read through PIL and then "repaired" by multiplying by 256 is wrong **twice** — once by
the destroyed 183x tonal resolution, and again by up to a percent of scale — and the second
error is the more insidious, because it makes the repaired figure look arithmetically
principled rather than merely rounded. Three independent lanes have now measured this
conversion (ORCH, BUILD-RESAMP, BUILD-SHARP, V-HIGHLIGHT) and each pass has made the
prohibition stronger and the "obvious fix" less defensible.

Their audit method is also better than mine and worth adopting: they checked **all 33** of
their scripts, found four importing PIL, and cleared each by inspecting *what PIL was used
for* — in every case `Image.fromarray(...).save(...)`, a write path, never a read. A grep
for the import name would have flagged four false positives; a grep for `Image.open`
would have missed a hypothetical `Image.frombytes`. The question is not which library is
imported but **which direction the data crosses it**.

## §94 — the audit that replaced the bad audit was defeated by the tool issued with it

§91 said: do not ask whether a number is 256x too small, ask `len(np.unique(arr))`, because
a scale error preserves the distinct-value count and quantisation destroys it, and the
count needs no reference image. Three lanes adopted it. V-HIGHLIGHT then measured it and it
is **also wrong**, in the same shape, one level up.

`len(np.unique(arr))` is a property of the **lattice**, and any averaging operation
destroys the lattice while preserving every bit of the damage:

| operation applied | clean uniques | PIL-x256 uniques | verdict on the DAMAGED array |
|---|---|---|---|
| identity | 13874 | 56 | CAUGHT |
| `/65535` -> float | 13874 | 56 | CAUGHT |
| 3x3 box mean | 741896 | 11651 | **PASSES AS CLEAN** |
| downsample 2x mean | 44134 | 218 | CAUGHT |
| **high-pass r=201** | 1048098 | **949976** | **PASSES AS CLEAN** |

The high-pass at r=201 is **exactly what `orch_smoothcrop.py` does** — the tool I issued in
the same notice, to certify cleanliness. Its output carries 91% of the clean array's
distinct-value count and passes my audit outright. The information is not back:

```
RMS(damaged - clean)                    73.73 DN   (quantisation step 256 DN)
a 3 DN dust feature against that error  SNR 0.041
```

So the audit, applied to the output of the tool shipped alongside it, reports damaged data
as fine — **on precisely the defect the other half of the notice was about.**

> **Quantisation damage is visible only while the lattice is intact. Any averaging step
> erases the evidence while preserving the harm.** Averaging is not a repair; it is a
> concealment that leaves the error and removes the tell.

V-HIGHLIGHT confirmed it is not specific to my statistic — three independent lattice
detectors of their own died identically, each silent on filtered damaged data and correctly
silent on undamaged data, so the negative control was clean and the instrument still blind:

| detector | identity | 3x3 box mean | high-pass r=201 |
|---|---|---|---|
| `len(unique) <= 300` | FIRES | silent | silent |
| all values multiple of 256 | FIRES | silent | silent |
| median level gap > 8 DN | FIRES | silent | silent |
| *(same three on CLEAN data)* | silent | silent | silent |

### The correction I owe BUILD-SHARP

When BUILD-SHARP cleared their lane with "no `Image.open` anywhere", I answered that this
was **a check that certifies the input rather than the output**, true of their source code
rather than of the array they measured, and that structural arguments "do not substitute for
reading the artifact". §91 records it approvingly.

For this hazard that is **backwards, and I am withdrawing it.** The source-level check is
the one that survives: it is size-invariant, operation-invariant, threshold-free, and
unaffected by however many filters sit between the read and the number. The artifact-level
check is the one with the blind spot. BUILD-SHARP's instinct was better than my critique of
it, and §93's warning about unaudited withdrawals is the reason I am writing this down
rather than quietly not repeating it.

The general form, which is what actually transfers:

> **An audit performed on a derived quantity can be defeated by the derivation. Audit the
> provenance, not the product.** Ask where the number came from, not what it looks like —
> because every transformation between the source and the number is an opportunity for the
> evidence and the harm to part company.

And the honest scope note, which V-HIGHLIGHT supplied about themselves unprompted:

> I had the stronger audit **by habit, not by choosing it**, and had you asked me to run
> the array test I would have run it and reported clean.

That is the reason the fleet's cross-checking has value that no individual lane's rigour
can supply. Three passes over one conversion — mine, BUILD-RESAMP's, BUILD-SHARP's,
V-HIGHLIGHT's twice — and every pass has moved the prohibition and weakened the obvious
fix. The current state:

1. **Do not read a `.tiff` through PIL.** Use `tifffile`.
2. **Do not repair a PIL-read number by multiplying by 256.** It is a right-shift; 23224 >> 8 = 90, ratio 258.04, and the tonal resolution is gone regardless.
3. **Do not audit by `len(np.unique(arr))` unless the array is the array as read.** One filter upstream and the check is deaf while looking exactly as reassuring.
4. **Audit by grepping the reader.** That is the only one of the four that has survived being measured.

## §95 — an objective halo number, and four defects found by reading plots rather than numbers

The user's judgement on the shipped masters — the halo is "horrendous", the output
"entirely unusable" — is correct and is an eyeball one. Before any lane can claim to have
fixed it, the project needs a number that is comparable across renders and produced by
someone other than the author of the fix. `experiments/ORCH-drift-check/orch_halo.py`.

**The measurement.** A focus-stack halo is an overshoot ring at an occluding edge. Blur
heavily, take the gradient magnitude to find object boundaries rather than texture, walk
the gradient normal +/-200 master px at sampled edge points, normalise each profile to a
0->1 step from its two far ends, aggregate, and measure the excursion outside [0,1] in the
16-180 px band. That excursion **is** the halo, in units of the step height.

Four defects, each found by looking at something other than the headline number.

**1. 359 step units.** The first run passed a synthetic commissioning at 97% recovery and
then reported overshoots of 35,900% on real masters. Per-profile normalisation divides by
the step height, and sample points on ridges rather than steps have near-zero denominators.
The synthetic arm could not express this because a synthetic step image **contains no
degenerate edges by construction**. Fixed with a minimum-step gate set from each image's
own 1st-99th percentile range, and by aggregating with a **median** rather than a mean so
no minority of survivors can dominate. Then an ARM DEGEN was added — equal-sided ridges
mixed into the synthetic — and it holds to 0.0162.

**2. A control that could only say zero.** The shuffled control read exactly `0.00000` on
all 26 masters, giving `inf` ratios everywhere. It had genuinely run — 528 to 2692
profiles each — but `overshoot()` clamped at zero, so the control could only ever report
"0 or more". Unclamped it reports how far **inside** the step it sits (0.02 to 0.50), which
is a margin rather than a floor. A clamped control and an absent control print the same
glyph.

**3. Thin lines are not steps.** The plotted profiles showed `lead-1-cpl` at **1.94 at
+12px, 0.33 at +48px, and 0.62 at +180px** — where the normalisation guarantees 1.0. Those
profiles were crossing thin bright lines, which clear a minimum-step gate by chance and
never reach a plateau. **The number gave no sign of this; only the shape did.** Fixed with a
plateau-flatness gate requiring each side's inner and outer quarter to agree.

**4. A control that planted the signal.** ARM SPIKE was then added and failed: clutter with
*zero* planted halo read 0.1197. Tightening the plateau gate did nothing between 0.18 and
0.05 and only collapsed at 0.03, where 17 profiles survived. Making the lines wavy to
decorrelate them made it worse — 0.58, and saturated, because the lines had become the
strongest gradients in the frame and the edge finder selected them instead of the step.

The diagnosis is the useful part. **A thin line parallel to an edge sits at a fixed offset
from that edge in every profile — which is exactly the geometry a halo has.** No
aggregation can separate them, because the plant and the signal are the same object.

> **A control that plants the signal is not a hard control, it is a broken one, and no
> amount of tuning will pass it.** When a control cannot be passed even in principle, stop
> adjusting the instrument and ask whether the control is measuring the thing it names.

The honest resolution is §91's own rule turned on my own gate: **report the floor rather
than tune until the number looks acceptable.** ARM SPIKE now states a sensitivity floor of
**0.1197 step units** and readings at or below it are reported UNDETERMINED — neither
clean nor defective.

### The result

Commissioned: ARM SYNTH recovers a planted overshoot at 0.978 / 0.991 / 0.993 / 0.995 over
a 0.05-0.40 ladder with a floor of 0.0002; ARM DEGEN deviates 0.0162; ARM SPIKE floor
0.1197.

| master | halo | side | profiles | note |
|---|---|---|---|---|
| **`tweezers-cpl`** | **0.9452** | bright | 910 | rim peaks at **1.98x the step** at +12px, decaying to 1.0 by ~+85px |
| `lead-1-cpl` | 0.3944 | bright | 106 | 97.3% rejected; weak sample, treat as indicative |
| `wrapped-text-1` | 0.1369 | dark | 643 | just above floor |

Nineteen masters read at or below the floor, three yielded too few surviving profiles, and
`coffee-bubbles` produced only 35 control profiles so its number carries no control at all
and is excluded rather than ranked.

**`tweezers-cpl` is the reference case**: a metal subject against a background, the
geometry where occlusion veiling is worst, and a rim reaching **198% of the step height**.
That is what "horrendous" measures to. Any halo fix must move that number, measured by an
instrument its author did not write.

---

## §96 — I withdraw §95's target: the one certified halo is mostly specular rim light

§95 ended with a sentence I now have to take back: *"`tweezers-cpl` is the reference case
... That is what 'horrendous' measures to."* It is not established that it measures
anything of the sort, and I had already broadcast it to five build lanes as the number to
beat before I checked.

### The question I should have asked before broadcasting

Twenty-six masters. Exactly **one** certified. That one is polished stainless steel — the
most specular subject in the corpus. A metal edge against a dark background is precisely
where a *genuine* rim highlight is physically expected, and in a profile that has been
normalised to a 0 -> 1 step, **a real specular rim and a merge overshoot are the same
shape**. `orch_halo.py` cannot separate them, and nothing in its three commissioning arms
ever asked it to.

I did not catch this from the number. I caught it from the picture: I rendered the four
worst individual sites with `orch_halosite.py`, looked at the crop, and saw shiny metal.

### The control

`orch_halosrc.py`. Decode the source frames with rawpy at stated settings
(`no_auto_bright=True`, `use_camera_wb=True`, `gamma=(1,1)`, `output_bps=16`) and run the
identical profile geometry, gates and normalisation on each. Structure the merge
manufactured is absent from the individual exposures; structure the optics delivered is
present in them. Twelve frames spanning the 100-frame stack:

| frame | halo | | frame | halo |
|---|---|---|---|---|
| 0 | 0.0388 | | 45 | **1.3440** |
| 9 | 0.0510 | | 54 | **1.3450** |
| 18 | 0.0542 | | 63 | 0.2509 |
| 27 | 0.0491 | | 72 | 0.1971 |
| 36 | 0.0684 | | 81 | 0.1906 |
| | | | 99 | 0.0944 |

Shipped master **0.8725**. Single-frame median **0.1280**, range **0.0388..1.3450**.

### The wrong verdict I printed first, and why it was wrong

My first pass sampled five frames, took the median (0.0925), and printed
`VERDICT the merge AMPLIFIES an existing rim by 9.43x`. Widening to twelve moved it to
6.82x. Both are meaningless, and the reason is structural rather than statistical.

**A focus stacker selects the sharpest frame at each edge. At a specular boundary the
sharpest frame is also the one carrying the strongest rim**, because the highlight is only
tight while that edge is in focus. Frames 45-54 are where the tweezer edge comes into
focus; they read 1.34. The frames reading 0.04 are the ones whose edges are defocused
there, which is exactly why the merge does not select them at those pixels. Averaging over
them builds a baseline out of candidates the algorithm correctly rejected.

Against the right baseline the master is **below the strongest frame it could have
chosen** — 0.8725 against 1.3450.

> **When you benchmark a selector's output against its inputs, the baseline is the input
> the selector would have chosen, not the average input.** An average over correctly
> rejected candidates is not a control; it is a strawman that reports an artifact whenever
> the selection is working.

### Standing

**NOT ESTABLISHED as a stacking artifact.** There may still be an artifact component, and
resolving that needs the per-pixel election map at those edges, which I do not have. But
the framing "one subject has a halo and it is 0.945" is not evidence of a merge defect,
the target is withdrawn from all five lanes, and `README.md` must not carry it.

### The pattern, third instance tonight

The dark-tail census, the cross-master median, and now the halo target all passed their own
commissioning and still returned a wrong answer, and all three failed identically: **the
plant tested the amplitude of the effect rather than the alternative explanation for it.**
My synthetic arm planted an overshoot and proved the tool recovers overshoots. It never
asked what else makes that shape.

> **Before trusting a positive reading, name the most plausible innocent explanation for it
> and go measure that specific cause.** Not a null, not a shuffle, not an amplitude ladder.
> A control that varies only amplitude cannot separate two mechanisms that share a shape.

One consolation, and it is not small: if the corpus contains no certified halo, that is bad
news about my metric's value as a regression gate and *good* news about the product.

---

## §97 — the adversarial sweep: no halo anywhere, and dust is now the top visible defect

§96 withdrew the halo target. That left an obvious hole: I had judged the product on three
subjects I chose, which is exactly the favourable sample I have spent all night refusing to
accept from anyone else.

### Three sweeps, increasing in adversarial strength

**1. Full-frame contact sheet** (`orch_contact.py`, 26 masters, 380 px cells). No gross
failure anywhere: no halos, no seams, no colour casts, no misregistration. Two subjects
carry large soft regions -- `flower-inner-edge-cpl` and `flowers-cpl` -- consistent with the
focus bracket not covering the full subject depth, which is a capture-coverage matter and
not a merge defect. **But an 18x downsample can only exclude gross failure.** Halos and
seams live at the pixel scale and cannot appear in this view at all.

**2. 1:1 crops from the gallery.** Sharp and clean across all 26. Still not sufficient: the
gallery picks its crops for interest, so a clean sweep over them is a favourable sample.

**3. The adversarial sweep** (`orch_worst.py`). Per master, take the single edge site with
the **largest** normalised overshoot -- the most artifact-like location in that image, on
the metric's own terms -- and crop it. Worst-site overshoots ranged 2.44 (`flower-bud-alone`)
to 24.12 (`coffee-bubbles`), with a median near 6.

**Every one of the twenty-six looks clean.** The high scorers are legible as physics on
inspection: `coffee-bubbles` at 24.12 is the specular ring of a bubble; `bee-3-cpl` at 10.08
is a lit hair against white; `112MSDCF` at 8.70 is a bright fibre on black. These are the
brightest genuine structures in the corpus, which is precisely what an edge-overshoot
statistic is expected to rank first once no artifact outranks them.

> **A metric with no artifact left to find returns the subject's own brightest structure.
> A ranked list is never empty, so the top of it means nothing until you look at it.**

### What the sweep did find

Two crops carry a small dark speck on a light, otherwise featureless field:
`flower-inner-edge-cpl` near (1988, 3960) and `pencil-flatter-angle-cpl` near (628, 2272).
That is **dust**, and it independently confirms §90 from a completely different direction --
this instrument was built to find halos, knows nothing about sensor defects, and surfaced
dust anyway because it went looking for the worst place in each frame.

It also closes out §92 properly. My cross-master median dust map was wrong, and the correct
reading is the one BUILD-BLEND had: dust must be found **within** a stack, not across
masters. This sweep finds it within single masters, at named coordinates, visible to the
eye.

### Standing

**No halo artifact is present in the shipped corpus at any site the metric can find.** The
user's "horrendous" complaint predates SHIP-V2 and I can find no evidence it still applies.

**Dust is now the top remaining visible defect**, which makes `defect_map.rs` the highest-value
outstanding item rather than any halo work. Two capture-coverage cases (`flower-inner-edge-cpl`,
`flowers-cpl`) are a matter for the capture advisor, not the merge.

Caveat, stated rather than buried: this sweep is adversarial with respect to **edge
overshoot** and nothing else. It has no power against defects that are not edge-localised --
tonal breaks in smooth gradients, chroma error, low-frequency blotching. Those need their
own instruments and do not have them yet.

---

## §98 — the blotch detector indicted the merge for reducing noise

§97 closed by naming its own blind spot: the adversarial sweep is powerful against edge
overshoot and blind to everything else, and the classic non-edge failure of a focus stacker
is **blotching** -- in a smooth region the focus measure has no signal, the winner field goes
arbitrary, and the merge stitches a patchwork that is invisible as an edge and plainly
visible as mottling. So I built the instrument (`orch_blotch.py`).

Statistic: in the flattest 900x900 window of the frame, band-pass at 50-400 px and divide by
the high-frequency residual. Commissioned on a planted blotch field, monotone across a
0.25-4.0 sigma ladder (0.219 -> 0.429 -> 0.851 -> 1.698 -> 3.390) against a pure-noise floor
of 0.0426.

Having learned §96, I built ARM SOURCE in from the start: the same statistic on decoded
source frames, so that structure belonging to the subject could not be charged to the merge.

### It found a large excess, and the excess was mine

```
  bee-1-cpl                 master 2.137   source max 0.867   2.46x
  pencil-flatter-angle-cpl  master 1.517   source max 0.405   3.74x
  coffee-bean               master 1.355   source max 0.492   2.76x
```

A 2.5-3.7x excess over any input, on a commissioned instrument with the source control
already fitted. I nearly reported it.

**The statistic is band power divided by noise power, and merging N frames divides the noise
by about the square root of N while leaving subject structure alone.** A perfectly clean
merge therefore raises this ratio by exactly sqrt(N_eff), with no blotching whatsoever. The
instrument was not measuring a defect. It was measuring the merge working, and dividing by
the very quantity the merge exists to reduce.

### Separating the terms settles it

```
  bee-1-cpl                band DN  master  81.9   source max 118.7   0.69x
                           noise DN master  38.3   source med 133.1   3.47x quieter
  pencil-flatter-angle-cpl band DN  master  42.7   source max  35.0   1.22x
                           noise DN master  28.2   source med  93.8   3.33x quieter
  coffee-bean              band DN  master  50.7   source max 129.5   0.39x
                           noise DN master  37.4   source med 272.0   7.26x quieter
```

Mid-scale structure in the master is **lower** than in the source frames on two subjects and
flat on the third. Only the denominator moved.

> **When a statistic is a ratio, an improvement in the denominator is indistinguishable from
> a defect in the numerator. Report both terms, always, or the instrument will indict the
> system for getting better.**

This is the fourth instrument tonight that would have published a wrong answer, and it is a
new failure mode: the previous three were blind to the thing sought, whereas this one was
**correctly sensitive to the wrong variable**. Its commissioning could not have caught it,
because the planted blotch raised the numerator exactly as intended -- the ladder was
faithful and the conclusion still false.

### The finding underneath

Read the other way, the table is the first direct measurement of the merge's noise benefit
on real captures: **noise reduced 3.3x to 7.3x** while mid-scale structure is not added.
That is the project's thesis -- estimation rather than selection, averaging wherever frames
agree -- measured on the owner's own subjects.

Two caveats, stated rather than buried. The source noise figure is an **upper bound**: the
window is chosen as the flattest region *of the master*, and any residual texture at those
coordinates in an unaligned source frame inflates its noise estimate. And masters are
7032 px wide against a 7040 px sensor, so the windows correspond to better than 99% before
alignment warp, but not exactly.

**No blotch defect is present on the three subjects tested.** The corpus-wide run is not
done; these were the three with the highest ratios, which is where a defect would have shown
first.

---

## §99 — raw DN is not comparable between a master and a source frame, and §98 assumed it was

§98 fixed a ratio by separating its terms, then compared the numerator -- **band DN** -- between
master and source frame. The corpus-wide run flagged three subjects on that basis:

```
  flowers-cpl            band DN master  590.9  source max  342.9   1.72x  "genuine merge defect"
  flower-inner-edge-cpl  band DN master 1251.9  source max  637.2   1.96x  "genuine merge defect"
  flat-on-ruler-cpl      band DN master 8747.1  source max 1809.1   4.84x  "genuine merge defect"
```

Two of those three also reported the master **noisier** than a single source frame -- `flat-on-ruler-cpl`
by 14x. A merge of a hundred frames cannot add noise. **A reading that requires an impossible
mechanism is a reading to look at, not to publish.**

### What the picture showed

`orch_blotchpair.py` renders each flagged window, master beside source frame, one stated
display gain for the pair. The means came out:

```
  flowers-cpl            master 56983.5   source 10684.3   5.33x
  flower-inner-edge-cpl  master  9765.2   source  2079.6   4.70x
  flat-on-ruler-cpl      master 47513.9   source  7475.0   6.36x
```

**The pipeline tone-scales.** A rawpy decode with `no_auto_bright=True, gamma=(1,1)` is not on
the master's tone scale and never was. Band DN and noise DN both scale with brightness, so
every raw-DN comparison in §98 spanned a 5x factor that had nothing to do with the merge.
Corrected, all three "defects" invert: 1.72/5.33 = 0.32x, 1.96/4.70 = 0.42x, 4.84/6.36 = 0.76x.
**The masters carry less mid-scale structure than their own inputs.**

Across the full corpus the factor reaches **25x** (`112MSDCF`: master mean 8524 DN, source
340 DN). At that separation raw DN carries no information about the merge at all.

### The corrected statistic and the corrected result

Contrast -- band divided by the window mean -- is invariant to tone scaling. Recommissioned
(monotone across the same 0.25-4.0 sigma ladder, null floor 0.0002), the three worst subjects
in the corpus read:

```
  foam       contrast master 0.46019   source max 0.70873   0.65x   NOT a defect
  112MSDCF   contrast master 0.24933   source max 0.26846   0.93x   NOT a defect
  113MSDCF   contrast master 0.24306   source max 0.19263   1.26x   NOT a defect
```

Nothing exceeds the 1.3x threshold. **No blotch defect is present in the shipped corpus.**

The eye agrees and agrees emphatically. In all three flagged windows the master is sharp --
pollen grains, dust specks, a hair, brushed-metal texture, a crisp ruler edge -- while the
source frame at the same coordinates is defocused mush. There is no mottling in any of them.

### §98's noise claim is withdrawn

§98 reported "noise reduced 3.3x to 7.3x" as the first direct measurement of the merge's
benefit. That number was computed from **raw noise DN across the same uncorrected tone
difference** and is not valid as published. The direction of the finding survives -- relative
noise still favours the master, and by more than was claimed rather than less -- but the
figure was arrived at wrongly and must be re-derived on relative noise before it is quoted
anywhere. It has been broadcast to six lanes and the correction has gone after it.

> **Two quantities measured in DN are comparable only if they sit on the same tone scale.
> Across a pipeline stage they generally do not, and the violation is silent: both numbers
> are honest, both units match, and the ratio is meaningless.** Normalise by something the
> stage preserves -- contrast, not amplitude -- or measure the scale factor explicitly and
> divide it out.

This is the fifth instrument tonight to produce a wrong answer, and the second to do it by
dividing by the wrong thing. §98 diagnosed exactly this failure in the denominator and then
committed it in the numerator, in the same script, within the same hour.

> **Fixing one term of a ratio does not license trusting the other.**

### §99.1 — why no corrected noise figure is offered

The obvious repair for §98's withdrawn claim is to redo it on **relative** noise, which is
tone-invariant. Computed from the same run:

```
  foam       master 1462.3/ 7990.6 = 0.18300   source 168.3/3171.4 = 0.05307   3.45x NOISIER
  112MSDCF   master  903.8/ 8524.0 = 0.10603   source  38.2/ 340.4 = 0.11222   0.94x
  113MSDCF   master  956.0/ 8354.6 = 0.11443   source  52.1/ 638.2 = 0.08164   1.40x NOISIER
```

On two of three the master is relatively **noisier**, which is again a result requiring an
impossible mechanism. The cause is in the estimator: noise here is
`std(blk - boxblur(blk, 3))`, which captures **all** high-frequency content and cannot
distinguish sensor noise from genuine fine detail. The master is sharp everywhere -- that is
what the tool is for -- while a single source frame at the same coordinates is defocused. The
master's own resolution inflates its noise estimate, and on `foam` (dense fine structure at
every scale) it dominates completely.

**So the instrument cannot measure the merge's noise reduction at all**, in either direction,
and no corrected figure replaces the withdrawn one. Doing that properly needs a region where
master and source are equally defocused, or a variance estimate that excludes structure --
neither of which exists yet.

> **A withdrawn number is better left withdrawn than replaced by a second number from the
> same defective instrument.** The pressure to publish a correction is the pressure that
> produced the error.

## §100 — the gather runs at half resolution, and it costs 51% of contrast at 0.20-0.30

**Status: MEASURED by V-NYQUIST, not by me. I read the report, checked its controls, and routed it. I have not reproduced it.**

This is the largest quality defect measured in the project, and unlike every finding
in §95-§99 it survived its own control.

### What was measured

`align_cmd.rs:1387-1492` gathers each CFA phase on the **plane** grid: 3516x2344
against a 7032x4688 output. `align_enabled()` defaults true and `fit_to_cover` puts
a non-unit scale on every placement, so the default path always resamples, and it
always resamples at half the output's lattice.

Broadband scene, CatmullRom, 16 frames registered and averaged with sub-plane-pixel
drift. The arms differ **only** in whether the gather runs per-CFA-plane or at full
output resolution:

| band (cyc/output px) | shipped (plane gather) | full-res gather | ratio |
|---|---|---|---|
| 0.10-0.20 | 0.8687 | 0.9889 | 1.14x |
| 0.20-0.30 | 0.4881 | 0.9358 | **1.92x** |
| 0.30-0.40 | 0.1183 | 0.8075 | **6.83x** |
| 0.40-0.48 | -0.0022 | 0.6322 | - |

**51% of true contrast lost at 0.20-0.30. 88% at 0.30-0.40.** At 0.40-0.48 coherent
fidelity is **negative** — the gather does not merely fail to carry that content, it
returns it anti-correlated.

### Why I believe it, when I disbelieved five of my own instruments tonight

The control is a **common-mode** one, which is the property §96 taught me to demand.
Both arms run the real `gather_checked` on real non-zero displacements with real CFA
gains through a real 16-frame average in the same window. The single difference is
lattice alignment. That is the discipline I failed in §95: I compared a master against
a *median* source frame and called a working selector an artifact.

Their anchors also fire and are not degenerate:
- zero-drift full-res reads **1.0000 in all six bands**
- whole-plane-pixel drift reads **1.0000** with uniform luma *and* with Bayer R/G/B gains
- two earlier anchors caught real errors in their own harness, so the instrument has
  been shown capable of saying no

And the positive controls behind the related NO-GO fired at large amplitude against an
exact null: `nearest` at +29%/+42%, an absurd-value arm at 4.3506 against NULL 1.0000.

### Three documents were wrong about this, in three different directions

1. **BUILD-RESAMP's Turn-8 self-correction** — *"the 0.25 bound constrains the election,
   not the deliverable detail"* — is **refuted**. It constrains the deliverable detail,
   via the alignment gather, on the default path. Their *original* `spectrum.py` premise
   in `52cb4c4d` was correct. Turn 8 withdrew a true statement. §93 said a retraction is
   the least-audited artifact a rigorous project produces; here is one that took back
   something right.

2. **`BUILD-SHARP.md` §s36.6 point 4** blames the **election** grid. P1b showed elected
   sensel values pass through **bit-exactly** (32768/32768). The gather filters the
   detail, and it does so *before* any election runs. Right recommendation, wrong
   mechanism — which is fragile to the next reader, so it is being fixed.

3. **`BUILD-SHARP.md` §s36.7's dichotomy** — *"if the comparators are ringing we should
   stop chasing it"* — is false as a gate. strehl loses 51% of true contrast to its own
   lattice whether or not Zerene rings. A competitor's defect does not price ours.

4. **V-NYQUIST corrected itself**, and this is the part that earns the rest. It had
   earlier reported the sub-0.25 band *"holds at 94.2%"* — from a **single tone**. A
   single tone is a plant that does not resemble the thing it stands in for. On a
   broadband scene the same path reads 0.4881. The instrument that catches its own
   plant is the instrument worth reading.

### What it does not cover, stated because a report without gaps gets sent back

- The full-res arm prices **demosaic-first**. You cannot interpolate across R/G/B sites
  on a mosaic. Their uniform-luma scene models a world where every site already carries
  a full-resolution estimate, and **it does not include the demosaic's own cost.**
- **No end-to-end run on real ARW exists.** Every arm is synthetic input through the
  real library. Real macro brackets are magnification-dominated with rotation their
  linear 0.37 px/frame drift model omits.
- **No test in the repo covers the gather above 0.25 cyc/output px.** Gate W8a pins only
  identity and inverse-scale. Four documents reason about an untested behaviour.

### Routing

- **BUILD-RESAMP** implements the full-resolution gather in `align_cmd.rs` behind a flag,
  defaulted off, with a byte-identical default path as gate 1. They hold the file's last
  commit and no other lane is in it. Known cost from §9.4 is 549 ms/frame, 216 s over 299
  frames — to be measured, not assumed.
- **BUILD-SHARP** builds the real-ARW measurement, in a different tree, so an instrument
  exists the moment the flag lands. They must not touch `align_cmd.rs`.
- **I score the renders** with `orch_halo.py`, `orch_blotch.py`, `orch_worst.py` — none of
  which either author wrote or may edit. A fix scored by an instrument its author tuned
  is not scored.

The default flip is mine to make, on measured quality and measured time together.

### The rule

> **A single tone is not a scene.** A plant with one frequency, one orientation and one
> phase cannot stand in for broadband content, and an instrument calibrated on it will
> report a number that is true of the plant and false of the subject. V-NYQUIST's own
> 94.2% and its own 0.4881 are the same code on the same path, differing only in what
> was fed to it.

> **A correct recommendation resting on a wrong mechanism is fragile to the next reader.**
> BUILD-SHARP's gather-order call was right for three months of document-time while its
> stated cause was wrong. The next person to touch it would have "fixed" the election.


## §101 — colour and banding: the last declared blind spot, and it is clean

§97 stated the blind spot plainly: no instrument in this tree could see chroma
error or tonal breaks. Every one of them -- `orch_halo.py`, `orch_blotch.py`,
`orch_worst.py` -- reads a luma statistic. A master could carry gross colour
mottling in a smooth background and all three would certify it.

Two instruments now close it. Both are in `orch_chroma.py`.

### Chroma blotch: band-passed RELATIVE chroma, and it acquits the merge

`a/Y` and `b/Y` band-passed at 50-300 px in the window with the flattest chroma.
Dividing by luma is what makes it survive the 2.5x-25x tone scaling that
invalidated two published numbers in §99. Commissioned: null **exactly 0.000000**
on a neutral scene, and a 0.0005-0.016 amplitude ladder linear to within 0.1%
across a 32x span.

Corpus: 22 of 26 masters read below 0.001. Four read high -- `coffee-bubbles`
0.0557, `foam` 0.0311, `lead-1-cpl` 0.0203, `leaf-2-cpl` 0.0200 -- and those are
precisely the four most colourful subjects, which is the innocent explanation
I wrote into the file **before** the first reading.

The source control read min 0.0321, max 0.0481 on `coffee-bubbles`. Master above
every input again -- the §96 shape exactly. And again it is not a defect:

1. **The first render exposed a fatal confound.** Each arm chose its own window.
   The master's landed at (0, 1458); the source's at (2616, 5828). **I had
   compared two different parts of the subject.** The window is now forced to
   the master's, and that is stated in the file rather than fixed silently.
2. **The band-pass render acquits it.** The source frames carry the same
   orange/blue blobs at the same scale -- that structure is the subject's own
   colour, not merge mottling. The master is in fact *cleaner*: both source
   tiles show a CFA checker the master does not have.

**No chroma defect.** The excess is a sharper merge resolving real colour edges.

### Banding: three statistics, two killed on the bench

- **v1, zero-fraction of first differences.** A CONTINUOUS gradient read 0.4996,
  because a 0.5 DN/px slope gives ~50% zero differences by rounding alone. It
  measured gradient steepness. The 0.02 threshold built on it would have flagged
  **all 26**.
- **v2, level occupancy.** Correct in principle -- tracked the predicted N/range
  to within 0.6% -- but ceilinged at WIN/range on a 1-D ramp, so its gate read
  **REJECT-STEEP on 23 of 26**. An instrument that declines to examine 88% of
  its inputs has not measured them, and a partition that large is a result about
  the instrument, not the corpus.
- **v3, spatial run length.** Median run of constant value, plus its step height.
  This is what an eye objects to: banding is visible when a value occupies a wide
  band. Commissioned exact -- 7.0 px predicted 7.0, 112.0 predicted 112.5 -- and
  **invariant at every slope and every range**, which is what killed v1 and v2
  respectively. Noise correctly breaks the bands.

**Corpus: 26 examined, 26 clean, 0 rejected.** Median run 1.0 px on every master.

### The rule

> **A statistic that rejects most of its inputs has reported on itself, not on
> them.** v2's 23-of-26 REJECT was not a clean sheet and must never be read as
> one. The partition is the finding.

## §102 — I raised a tone defect and the picture killed it inside an hour

**RAISED, then WITHDRAWN. Never broadcast. This is the fourth of my own findings
to die tonight and the fourth killed by rendering the image.**

### What I claimed

`orch_tone.py` fits `master = k * source^g` on matched quantiles, alignment-free
because quantiles do not care about the warp. Reference exponents, computed in
the file rather than quoted: **linear 1.0000, sRGB 0.4743, gamma 2.2 0.4546.**

`coffee-bubbles` returned **1.04-1.31** and its median sits at **2517 DN, 3.84%
of a 16-bit scale**. `bee-1-cpl` returned **0.90**. Both near linear, neither near
sRGB, in files whose `ImageDescription` declares sRGB. I concluded the pipeline
writes linear data under an sRGB label -- which would render near-black in every
viewer and would have explained "horrible" completely.

### Why it is false

`orch_tonerender.py` renders the same data two ways at one stated gain, no
autoscaling: **AS SHIPPED** (straight to 8-bit, what a viewer does) and **sRGB
APPLIED** (treat as linear, encode properly).

**AS SHIPPED is right.** The bee is a photograph -- tonality in the fur, a clean
dark eye, white background holding detail. **sRGB APPLIED is washed out.** Even
`coffee-bubbles`, the darkest master and my strongest evidence, is correct as
shipped and a muddy brown mess with the curve applied.

### Three errors, each nameable

1. **I generalised from a subject I had selected for being extreme.**
   `coffee-bubbles` was in front of me because it topped the chroma table. Of 26
   masters, 22 read ENCODED on the corpus sweep. My "this is it" rested on one
   subject chosen for an unrelated reason.
2. **My verdict column measured brightness, not encoding.** `p50 < 0.5*srgb(p50)`
   reduces to `p50 < ~0.25`, because `srgb(x) > x` everywhere. A dark encoded
   image reads LINEAR; a bright linear one reads ENCODED. **The test had no
   dependence on the transfer function it claimed to detect.**
3. **The power-law model does not fit, and running the second arm proved it.**
   Against a linear source the exponent is 0.90; against an sRGB-decoded source
   it is 1.41 -- implying 0.587. Those are mutually inconsistent, so no single
   transfer function explains both, whatever the r2 of 0.96-0.99 suggests. I was
   comparing quantiles across two different **colour pipelines** -- different
   white balance, matrix and highlight handling -- and charging the entire
   difference to the transfer curve.

I also asserted "crushed highlights" from `bee-1-cpl`'s p90. Measured clipping is
**0.02%**. Withdrawn in the same breath as the rest.

### What survives, and it is the most useful thing measured tonight

The renders are good. Not "clean on a metric" -- good photographs, at a size
where softness would show. That is the first evidence in this log bearing on
"print worthy" that comes from looking at the deliverable rather than at a
number computed from it.

### The rules

> **A test whose verdict does not depend on the property it names is not a test
> of that property.** Check the algebra of the threshold before the data.

> **Fit the same model against two different references. If they disagree, the
> model is wrong** -- and a high r2 will not tell you, because a power law fits
> most monotone data over a limited range.

> **When a finding would explain everything, that is the moment to render it.**
> The explanatory reach of this one is exactly what made it attractive, and it
> survived about an hour.

---

## 103. The merge reconstructs. It does not merely select, and it is not sharpening

Every instrument in this log so far asks whether the product has a *defect*.
None of them asked whether it is *good*, which is the only question a focus
stacker exists to answer. Section 103 asks it and the answer is the strongest
result in the corpus.

### 103.1 Why the 560 px figure was not honest, and I published it anyway

Section 102 closed with a 1:1 render showing the master resolving ommatidia
across a bee's compound eye where the source frames were mush. The number beside
it was master-over-best-single-frame at 1 px scale: **4.42x** and **3.09x** on a
30-frame baseline.

That number is not what it appears to be. Across a 560 px crop of a curved eye,
**no single frame can be in focus everywhere**, so the comparison rewards
*coverage* -- and a pure selector that never sharpened one pixel scores well on
it. Coverage is a real product of stacking and it is worth having. It is not
evidence for this project's thesis, which is that estimation beats selection.

> **A ratio measured over a region larger than one depth of field is a coverage
> measurement wearing a sharpness measurement's clothes.** It reads well above
> 1.0 for the behaviour this project exists to improve on.

### 103.2 The honest measurement: patches small enough to be one depth

`orch_sharp1to1.py` now subdivides each site into 70 px patches. At that size
some frame is genuinely in focus across the whole patch, so the best single
frame is a fair and hard baseline, and the ratio means what it says:

| reading | meaning |
| --- | --- |
| ~1.0 | the merge SELECTS -- correct, and what every competitor already does |
| > 1.0 | the merge RECONSTRUCTS -- detail no single frame contains |
| < 1.0 | the merge DESTROYS detail its inputs had |

Commissioned before use, on data built so the answer is known in advance:

```
arm                                                median     expect   verdict
SELECTION   (master == sharpest source)            1.0000       ~1.0   PASS
DEFECT      (master blurred past every source)     0.1717       <1.0   PASS
RECONSTRUCT (master == unblurred latent)           3.4867       >1.0   PASS
COMMISSIONED: all three verdicts are reachable.
```

The identity arm returning exactly `1.0000` is the anchor. The third arm exists
because of BUILD-TRIAGE's finding in the same night's work, below.

Measured on `bee-1-cpl`, 30 source frames, two sites, 128 patches:

```
  site 0   median 2.823x   p10 2.112x   p90 4.442x   master sharper on 64/64
  site 1   median 2.535x   p10 1.257x   p90 4.406x   master sharper on 62/64
  ALL SITES  median 2.756x over 128 measured patches
  -> RECONSTRUCTION: the master carries detail no single frame has.
```

**Median 2.756x, and the master is sharper on 126 of 128 patches.** The p10 of
1.257 matters more than the median: even the tenth-percentile patch, the ones
where the merge does worst, still beats the best single frame.

### 103.3 The innocent explanation, named in advance and then killed

A merge that is simply **sharpened** produces exactly this number. Sharpening and
reconstruction are indistinguishable in any gradient-energy statistic, so the
statistic cannot settle it and no amount of ladder-building will.

The control: unsharp-mask the best source frame until its fine-detail energy
**equals the master's**, then look at all three. The USM arm has the master's
number by construction. The question is whether it has the master's picture.

It needed **x4.64** and **x3.04** to get there, and it does not:

- heavy magenta/green fringing on every ommatidium,
- dark ringing outlines on the hairs,
- display clipping at **11.88%** against the master's 2.21% -- overshoot pushing
  pixels out of range is itself a signature,
- and the defocused regions **stay defocused**. Sharpening amplifies what a
  frame has. It cannot supply what the frame never recorded.

The master has none of the three artifacts and is sharp across the full
curvature. `C:\dev\strehl-out\ORCH-CONTACT\sharp-1to1-bee-1-cpl.png`.

> **A control does not prove the claim. It fails to explain the claim away, and
> that is the most any control does.** This one was built to succeed -- matching
> the number was a binary search, not a fit -- and it still could not produce the
> image.

### 103.4 The display window was crushing the source, and my own new gate caught it

The first run of the three-row render took the display window from the master's
1--99 percentile and applied it to both rows. Shared window, no per-row gain --
section 91's rule, correctly followed. It was still wrong: the source rows
saturated at **19.82%** and **20.24%**, so the source looked softer for a display
reason on top of the optical one, and the picture flattered the master.

The clip-fraction gate I had added an hour earlier -- because V-POTENCY proved
the same defect in `orch_smoothcrop.py` -- fired on my own render immediately.
A **union** window over both arms is still one linear map, so the contrast ratio
between rows is preserved exactly, and saturation fell to **1.79%** and 1.91%.

The patch statistic was never affected: it runs on the registered luma before any
display stretch. **The number was clean and the picture was not**, which is the
reverse of this project's usual failure and worth recording as such.

### 103.5 What this does not establish

- **One subject, two sites, 30 of 299 frames.** `bee-1-cpl` only.
- **The gain is not attributed.** Merge estimation, demosaic differences between
  `strehl` and `rawpy`, and output-path processing are not separated. The USM
  control rules out one specific mechanism, not all of them.
- **`detail()` counts noise as detail.** This runs *against* the finding -- a
  cleaner master scores lower -- so it cannot manufacture the result, but it
  means 2.756x is a floor on the effect only if the master is not noisier.
- **The 70 px patch size is asserted, not measured.** It is claimed to be within
  one depth of field at this magnification; that claim is untested.
- Sites are chosen for high detail *in the master*, which selects for regions the
  merge did well on. The 126/128 win rate is subject to that selection.

### 103.6 BUILD-TRIAGE's rule, and why the third commissioning arm exists

BUILD-TRIAGE (`d6e5a809`) found by inspection that the print-readiness verdict
statistic could not charge for a halo: `edge_slope` is a p99.5 magnitude and
`blur_equiv` floors at 0.0 for any ratio >= 1.0, so the sign of the error is
bounded below by zero. A haloed merge can only ever score at or above a clean
one.

> **A metric can be BLIND to a defect (reads nothing) or PERVERSE on it (reads
> better). Commissioning that plants only degradations cannot tell those apart,
> because both present as a pass.**

Every plant in this log until tonight made the image worse. That is why
`patch_gain`'s commissioning has an *improvement* arm, and it is now the rule for
every instrument here.

Their premise was wrong -- they cited `tweezers-cpl` as "the worst halo in the
corpus", which section 96 withdrew. Re-measured to be certain I was not defending
an old conclusion:

```
ARM MASTER   tweezers-cpl SHIP-V2      halo  0.8725
ARM SINGLE   frame 54 DSC00055.ARW     halo  1.3450   median over 12 frames 0.1280
VERDICT  the master's 0.8725 is BELOW the strongest single frame's 1.3450.
```

The master's rim is **weaker** than the rim of the frame the selector chooses
there. Comparing against the median frame instead would have indicted the merge
at 6.82x, because the median averages in defocused frames the merge never selects
at that edge. The finding survives the wrong premise because it was established
by inspection of their own code; that is the difference between an argument and
an example.



## 104. Four instruments were wrong, the pin could not build, and the gather flip landed anyway

Written after a crash cleared the entire build fleet. Everything below is
measured; where it is argued I say so.

### 104.1 The gather flip, and the one statistic still dissenting

`STREHL_FULLRES_GATHER` now defaults ON (`740e7056`). The old path deinterleaved
the mosaic into four half-resolution phase planes and gathered each separately --
right for colour, since no interpolation ever mixes two channels, but it
band-limits every phase to the PLANE Nyquist, 0.25 cyc per output pixel, and it
does so BEFORE the election, where no later stage can recover it.

Measured, both arms from one binary:

| quantity | plane gather | full-res gather |
| --- | ---: | ---: |
| band corr @ 0.25 cyc/out px | 0.1514 | 0.9329 |
| band corr @ 0.35 | -0.4965 | +0.4478 |
| 79 frames | 27.7 s | 20.1 s |
| 130 frames | 45.9 s | 40.6 s |
| 299 frames | 110.3 s | 97.1 s |

The 0.35 row is the one worth pausing on: the old path was not merely
attenuating that band, it was returning **inverted structure**. That is aliasing,
not softness.

The timing is 40-97 ms/frame FASTER against a prior analysis that predicted +549
ms/frame SLOWER from the added demosaic -- a 600 ms swing in the flattering
direction, which is the shape of an artifact rather than of a win. The proposed
mechanism, four strided plane deinterleaves collapsing into one sequential read
plus a parallel demosaic, is a HYPOTHESIS and has never been measured. It is
routed to V-GATHER rather than banked.

**The dissent, recorded because it has not been resolved.** Two overshoot
statistics disagree. A step-normalised excursion reads the full-res arm as
ringing MORE (0.179 against 0.128 and 0.140), which is past that instrument's own
0.0122 byte-identical floor and therefore not noise. A local-envelope ring
fraction did not move at all (1.086% -> 1.053% at the strongest edge, 1.744% ->
1.744% at the median). I broke the tie by rendering both arms at 1:1 and looking:
paper fibre inside flat white resolves on the new path and is mush on the old,
which sharpening cannot manufacture, and no bright rim appears on the dark side
of any letterform, which sharpening would. **I sided with the statistic that
agreed with my eyes, which is exactly the move this corpus distrusts**, so the
disagreement is logged as open and handed to an independent verifier.

### 104.2 The specificity control I nearly mistook for a failed attribution

The byte-freeze caught the flip, as designed. The attribution script demanded
that BOTH frozen rows move and printed `ATTRIBUTION FAILED` when only one did.

That gate was wrong, and the registry had already said so. `fullres_gather_enabled()`
is read in exactly one place, `warp_frame_in_place`, which is warp application.
The `STREHL_ALIGN=0` row applies no warp, so the flag is **unreachable** there and
must not move. The `6430fb2` note wrote this down in advance and against itself:
*"a change that moved only the sidecar row would have been in warp application and
would not have been this one."* This is that change.

So the unaligned row is a **specificity control**, not an inert arm -- but only
because the prediction was derived from the call site BEFORE the number came
back. The script now carries a per-row expectation and fails on a violation in
**either** direction, so "did not move" could not have been excused after the
fact. Both rows reproduce their standing baseline bit-exactly under
`STREHL_FULLRES_GATHER=0`, which clears the five files left uncommitted in
`crates/` by dead agents -- and every commit since `6430fb2` -- of touching these
bytes. `byte-freeze.rs` had independently measured the new hash and printed it as
`actual` before the script ran; two instruments sharing no code agree to the byte.

**The rule:** a gate that demands every arm move cannot express a change with a
bounded blast radius, and will report a correct localisation as a failure.

### 104.3 The acceptance harness could not build a pin at all

`scripts/finalpass.ps1` is the mechanism the entire acceptance corpus rests on for
provenance -- "ONE BINARY, built from `git archive` so it cannot contain another
agent's uncommitted work." It was broken, in two places, and had been for its
whole life.

1. `git archive $sha | tar -x` **corrupts the archive**. A PowerShell pipeline
   carries .NET objects, not bytes: the tar is decoded to text and re-encoded on
   its way to `tar.exe`, mangling every byte >= 0x80. It presents as ~100 lines of
   `Damaged tar archive (bad header checksum)` followed by cargo reporting no
   `Cargo.toml`, which reads as a git problem and is not one. Same defect class as
   `git show HEAD:path > tmp`, which has already produced a false measurement in
   this project.
2. The cold build then **aborted on its own progress output**. cargo writes
   `Compiling ...` to stderr, `2>&1 |` turns each line into a PowerShell error
   record, and the file-level `$ErrorActionPreference = 'Stop'` kills the pass on
   the first one -- reporting the compile line as the failure, so it reads as a
   compiler error.

**Both defects only fire on a COLD pin.** Every prior run reused a warm one and
never executed either line. A harness can be load-bearing, exercised daily, and
still have never once run the branch that makes it trustworthy.

Fixed by writing a real `.tar` with `-o` and extracting from the file, asserting
`Cargo.toml` landed, and logging the build rather than piping it. Verified end to
end from a cold pin at `740e7056`: 19 frames in 5 s, **0.34 s/frame** against the
1.48 s/frame the header projects under five-agent load.

### 104.4 What the corpus actually looks like now

Rendered from that pin, `--srgb --auto-exposure`, and inspected as whole frames
rather than as crops a statistic chose. On `bee-3-cpl` (299 frames), individual
hairs are separated across the entire thorax, wing venation is crisp, and **there
is no white halo around a dark subject on a bright ground** -- the estimator's
signature defect, which the pyramid merge was built to remove and which is now
absent by inspection as well as by the 4739 DN -> 166 DN aura measurement.
`flower-bud-with-background-fern-cpl` resolves individual trichomes against white
with no rim, and `dry-erase-marker-head-cpl` carries a hard black-to-white
boundary across the frame with no rim on either side.

This is the first time in this project's history that the whole-frame appearance
of the corpus and its statistics have agreed with each other.


---

## 105. Nine subjects instead of one -- and the number went past the arm that defines perfection

Section 103 measured the reconstruction ratio honestly and then stated its own
limitation in bold: **"One subject, two sites, 30 of 299 frames. `bee-1-cpl`
only."** It also warned that the 126/128 win rate was "subject to that
selection". Section 105 removes the selection and reports what happened,
including the part that is a problem.

### 105.1 The sweep

`orch_sharp1to1.py`, unchanged in its metric, run over **nine subjects** of the
26-master SHIP-V3 corpus, full stacks rather than a 30-frame subset, on the
post-gather-flip binary `740e7056`. The arm is now an argument (`STREHL_ARM`)
rather than the frozen `SHIP-V2` string -- the same hard-coded-arm defect fixed
in `643b719d` for the two gates was present here too, and would have made this
sweep silently score a fourteen-hour-old corpus.

| subject | median ratio | patches |
| --- | ---: | ---: |
| `wrapped-text-1` | **4.767x** | 192 |
| `tweezers-cpl` | **4.648x** | 192 |
| `leaf-2-cpl` | **4.565x** | 128 |
| `bee-3-cpl` | **4.139x** | 192 |
| `lavendar-cpl` | **4.120x** | 128 |
| `pencil-steep-angle-cpl` | **3.149x** | 192 |
| `dry-erase-marker-head-cpl` | **1.674x** | 128 |
| `coffee-bean` | **1.598x** | 192 |
| `flower-bud-alone-cpl` | **1.405x** | 128 |

**Median across subjects 4.120x; every subject above 1.0; range 1.405-4.767x.**
On `bee-3-cpl` the master is sharper on **191 of 192** patches. MEASURED.

Section 103's single-subject figure was **2.756x**. This is not a like-for-like
comparison and must not be quoted as an improvement: different subjects,
different frame counts, different binary. What it *does* establish is that the
verdict does not depend on `bee-1-cpl`.

### 105.2 The USM control, which is the only reason the number means anything

The innocent explanation for "the master has more fine detail than any source
frame" is not reconstruction -- it is that **something in the pipeline sharpened
the master**, and a sharpened frame and a reconstructed frame produce the *same
number* here. `usm_match` is the control: unsharp-mask the best source frame
until its fine-detail energy *equals* the master's, then look at the two
pictures.

On `bee-3-cpl` the control needed **USM x3.40, x4.63 and x4.83** at the three
sites. Inspected at 1:1 in
`C:\dev\strehl-out\ORCH-CONTACT\sharp-1to1-bee-3-cpl.png`: the control **rings
and craters visibly** -- dark rims around every hair, blotched inter-hair
texture, chewed wing venation -- while the master at the same detail energy is
clean. The control fails to explain the number away, which is the most any
control does.

> **This is also the clearest answer in the corpus to "the halos are
> horrendous": row 3 of that figure is what a halo looks like, and row 1 is what
> this tool now produces from the same photons.**

### 105.3 The problem, stated rather than buried

Section 103.2's commissioning arms are:

| arm | median | meaning |
| --- | ---: | --- |
| SELECTION (master == sharpest source) | 1.0000 | the anchor |
| DEFECT (master blurred past every source) | 0.1717 | responds downward |
| **RECONSTRUCT (master == unblurred latent)** | **3.4867** | **the arm that defines a perfect answer** |

**Five of the nine subjects read ABOVE 3.4867.** `wrapped-text-1` reads 4.767x
against a perfect-reconstruction arm of 3.4867x.

A real master cannot out-reconstruct the latent image the commission defined as
perfection. So one of these is true, and I do not know which:

1. **The commission's RECONSTRUCT arm is not an upper bound.** Its "latent" is
   whatever synthetic blur that arm removed; a real subject with different blur
   and different contrast is simply not on the same scale, and 3.4867 was never
   a ceiling -- only a demonstration that the metric can read high. If so the
   arm is doing less work than section 103.2's table implies and should be
   relabelled.
2. **The ratio is inflated by contrast, not detail.** The sweep's own clip
   report shows the master clipping **4.00%** where the source clips **0.00%**
   under the shared window at `bee-3-cpl` site 0. A wider master histogram
   inflates any gradient-magnitude ratio. The USM control argues against this
   being the whole story -- matching *energy* still rang -- but it does not
   exclude a contrast component in the size of the number.
3. **Both.**

> **A metric whose perfection arm reads 3.4867 and whose real data reads 4.767
> is not measuring what its own commissioning says it measures.** The direction
> of the verdict survives -- every subject is above 1.0, the DEFECT arm proves
> the instrument responds downward, and the USM control proves the detail is not
> sharpening. **The magnitude does not survive, and no "4.1x sharper" claim
> should be made outside this file until item 1 is settled.**

This is exactly the failure this corpus keeps re-learning: a commissioned metric
is trustworthy only within the range its commission spans, and every arm above
3.4867 here is extrapolation. Recorded as a question rather than a fact.

### 105.4 Status

- **MEASURED and safe to state:** the merge reconstructs rather than selects, on
  nine subjects spanning text, metal, fur, foliage, graphite and a coffee bean;
  every subject above 1.0; the effect is not sharpening, by the USM control.
- **NOT safe to state:** any specific multiple. Pending resolution of 105.3.
- **Removed:** section 103's single-subject caveat.

## 106. The gallery was 19.9% of master width, and that is what was being judged

**Status: MEASURED.** Direct measurement of delivered bytes, `2026-08-27`.

### 106.1 What was found

The owner has twice looked at output and reported it looked bad — once "these
look horrible", once "those stacks don't look too good yet, I can see the
promise". Both times the response here was to go looking for a defect in the
stacker. This section records that a large part of what he was reacting to was
not in the stacker at all.

Measured on the delivered files:

| | |
|---|---|
| master | `7032 x 4688` = 33.0 MP |
| delivered `_presentation/*.jpg` | `1400 x 933` = 1.3 MP, all 26 |
| ratio | **19.9% of master width** — a 5.02x downscale |
| JPEG quantisation DC | 2 (i.e. very high quality — compression was *not* the problem) |
| ICC profile | absent |

The compression was fine. The size was not. `finalpass.ps1` defaulted
`-PresentWidth 1400`, and the presentation directory is the only place in the
output tree holding a file a photographer would naturally double-click; the
masters beside it are 198 MB 16-bit TIFFs.

### 106.2 Why this is worse than merely uninformative

Every property this project is judged on lives above 1400 px:

- reconstruction gain is measured on 1:1 patches (§105)
- the blur budget closes to 2.6% at full scale (`BUILD-SHARP.md` §1)
- halo absence was confirmed on 1:1 grids and the USM control figure

A 5x downscale puts all of it inside the resampling kernel.

And the failure is not symmetric. **A 5x box-down of a correctly sharp image
looks softer than a 5x box-down of an oversharpened one**, because the
oversharpened one carries edge overshoot that survives decimation as apparent
local contrast while the honest one carries only real detail that decimation
removes. So the thumbnail does not merely fail to show the quality — it
*inverts the ordering* it was being used to establish. Every competitor that
oversharpens would have looked better than this one in that gallery, and it
would have looked better precisely to the extent it was worse.

This is the same class of error as the clip gate corrected in commit `04074ab8`
— a statistic (here, an image) that answers a different question than the one
the viewer is asking, and answers it confidently.

### 106.3 What was verified at full resolution

`scripts/deliver.py` now writes the real deliverable: full-resolution JPEG,
quality 95, 4:4:4, sRGB ICC embedded, 300 DPI, plus 1:1 crops with **no
resampling of any kind**. 26/26 rendered, 289 MB, 26 full frames + 78 crops.
ICC and DPI verified on real bytes at `588` and `(300, 300)` for both a full
frame and a crop.

Crop locations are **scored, not chosen** — mean `|Laplacian|` of luma on the
master, top-k under a minimum separation. A deliverable whose crops are picked
by eye is a deliverable that flatters itself. Scoring selects where detail
*exists*, which is also where a stacking failure would be most visible, so the
selection cuts both ways on purpose.

Inspected at 1:1:

- **`bee-3-cpl`** — individual hairs resolved; the fine pale filaments crossing
  dark out-of-focus background are *continuous*, which is the hardest case in
  focus stacking and the one where selection-based tools fragment hairs; the
  pitted cuticle texture on the leg segment survives.
- **`tweezers-cpl`** — machining striations individually resolved, speculars are
  points rather than smears, and the boundary against dark background carries no
  bright rim.
- **`wrapped-text-1`** — the decisive halo geometry, dark ink on light paper. No
  bright rim on any letter: paper immediately adjacent to a stroke matches paper
  far from it. Paper fibre texture and the ink's dot structure both resolved.

### 106.4 The rule

> **A deliverable rendered at a scale below the one the work is judged at is not
> a small version of the result. It is a different measurement, and it can rank
> backwards.**

And the process rule that would have caught it a week earlier:

> **When someone reports that output looks bad, measure what they actually
> looked at before you go looking in the code.** Two rounds of investigation
> here started from the assumption that the reported artifact was in the merge.

### 106.5 What this does *not* excuse

The halos the owner reported in earlier rounds were real, were found, and were
fixed; this section is not a retraction of that. `SHIP-V3` is a genuinely
different and better render than what he saw then. What is claimed here is
narrower and specific: **the gallery used to judge every render to date
understated all of them**, and the most recent "these look horrible" was passed
through a 5x downscale that no amount of stacker quality could have survived.

## 107. A halo detector that had to be commissioned three times, and what it cost each time

**Status: MEASURED.** `experiments/ORCH-drift-check/halo_profile.py` and its
commission, `2026-08-27`.

### 107.1 Why build it

Every halo claim this project has made about the *shipping pyramid path* has
been made by eye on 1:1 crops. `veil_accept.py` and `veil_absolute.py` are both
COMPARATORS — they need an on/off pair from the same stack and they answer "did
this operator help". Neither answers the question a reader of a finished master
asks: *does this picture have a halo, and how big*.

### 107.2 The measurement

Segment the subject as the dark region against a bright backdrop (Otsu, then
morphological open/close), Euclidean distance transform outward, median
background luma per distance band, referenced to a far-field band.

- `overshoot` — the most any near band rises **above** the far field.
- `bump` — the largest **decrease** walking outward. A clean edge's profile
  rises monotonically to the far field, so `bump == 0` by construction; a halo
  is a local maximum, which forces a decrease on its outer flank.

Two statistics with different failure modes, so a halo has to defeat both.
Median not mean, because near bands contain the subject's own stray hairs and
dust and a mean is dragged by them.

### 107.3 The commission killed three versions, and each death was informative

**Death 1 — `veil = min(band)` was measuring optics, not stacking.** The first
version reported a large negative band value as "veiling, the dark aura". On a
clean master the profile is

```
d      2-6    6-12   12-20   20-32   32-50   50-80   80-120   far
    -19951  -11512   -5044   -2033   -1193    -758     -432      0
```

a smooth monotone ramp with no overshoot anywhere — the signature of a *clean*
edge. `min(band)` reads −19951 on it and would have declared the cleanest
subject in the corpus severely defective. That deficit is the subject's own
**out-of-focus penumbra**: the distance transform starts at a thresholded
silhouette and immediately outside any real subject the subject's own blurred
edge still darkens the background. Every photograph ever taken has one.
Penumbra depth is still printed because it describes the picture, but it
carries no verdict.

**Death 2 — the test was wrong, not the instrument.** The second commission
compared the *absolute* overshoot against the planted amplitude and marked a
+600 plant WRONG at +168.3. But the clean baseline is −431.5, so −431.5 + 600 =
+168.5. Measured deltas were **+599.8 and +2000.0 against plants of 600 and
2000** — the statistic was recovering the plant to within 0.03% while being
scored as broken. Recovery is now scored on the delta from the clean baseline,
the only quantity a plant controls.

> **A commission that fails can be indicting the test rather than the
> instrument, and the two look identical from the summary line.**

**Death 3 — narrowing the bands to where a halo lives made it blind.** The
first corpus run flagged six subjects; two checked were confounds
(`tweezers-cpl`, whose bump sat at d=50–80 px crossing the gap between its two
arms; `flat-on-ruler-cpl`, whose background brightens away from the markings —
illumination falloff read as a rim). The physical fix looked obvious: a halo's
width is set by the defocus blur diameter, ~27 µm ≈ 7 px at this sensor's
3.76 µm pitch, so stop the bands at 24 px and use a local far field.

Commissioned, that version reported **bump = 0.0 and Δoveshoot = 0.1 DN for
planted rims of 500, 1500 *and* 4000 DN.** The reason is in the profile: near
the edge the penumbra rises ~4000–5000 DN *per band*, so a rim of a few
thousand DN never breaks monotonicity. **A radial-profile detector cannot see a
rim close to a steep penumbra**, and no band tuning changes that. The
commissioned configuration was restored and the *assumptions were guarded*
instead.

### 107.4 What it measures now, and the floor

Commission passes on six arms with verdicts pre-registered: `bump` exactly 0.0
on the clean monotone ramp; overshoot recovering 100.0% of both planted lifts;
a local ring caught by `bump` that overshoot alone misses (Δoveshoot −0.3 DN
against bump 391.7); and a strictly ordered responsiveness ladder
500:0.0 → 1500:391.7 → 4000:2674.4.

The 500 DN arm is a **pre-registered miss** that brackets the sensitivity
floor between 500 and 1500 DN, set by the steepness of the subject's own
penumbra rather than by the code.

> **A `clean` verdict means no rim above that floor. It does not mean no rim.**

### 107.5 The corpus result, stated honestly

On SHIP-V4, 26 masters: **7 clean, 4 flagged, 15 skipped.** The skips are the
regime guards working — text (79 components, largest 8% of mass), couch fibres
(910 components), flowers (31 components) are not one compact subject on a
uniform field and the commission never covered them.

**All four flags were adjudicated and all four are segmentation confounds, not
halos:**

| subject | reading | what it actually is |
|---|---|---|
| `tweezers-cpl` | bump 1573.7 | non-monotonicity at d=50–80 px, crossing the gap between the two arms. Inspected at 1:1: boundary clean. |
| `flat-on-ruler-cpl` | overshoot +4477 | profile monotone to d=80–120 then lower by 400–900: illumination falloff across a flat card. |
| `lavendar-cpl` | overshoot +526 | the bud is covered in dense white trichomes; Otsu splits *hairs from tissue*, so there is no silhouette. Measures hair density. |
| `dry-erase-marker-head-cpl` | overshoot +232 | "subject" is ink specks, "background" is a curved plastic barrel. Measures the barrel's shading gradient. |

The common failure mode: **Otsu segmentation on subjects with no true
figure/ground separation.** The instrument reports a rim wherever the image has
a large-scale luminance structure that the distance transform happens to order.

### 107.6 What this does and does not establish

**Verified:** on the 7 subjects inside the instrument's commissioned regime,
there is no rim above ~1500 DN. Direct 1:1 inspection of the hardest available
geometries — pale bee hairs crossing dark out-of-focus background, dark ink on
light paper, machined metal against dark ground — shows no rim.

**Not established:** a visibility threshold. The 200 DN gate was chosen, not
commissioned against what a viewer can see, so "+232 DN" carries no claim about
whether anyone could detect it. Linking DN of overshoot to visibility needs a
separate experiment and has not been done.

**Therefore the primary halo evidence remains direct 1:1 inspection**, with
this instrument as a corroborating check on 7 subjects and an honest SKIPPED on
15. That is a weaker claim than "measured halo-free across the corpus" and it
is the one the evidence supports.

## 108. Both merges measure clean for a bright rim, and what that does and does not say

**Status: MEASURED.** `C:\dev\strehl-out\ORCH-HALOAB`, `2026-08-27`, one binary
(pin `740e7056`), one subject, identical flags, differing only in `--merge`.

### 108.1 Why run it

`strehl stack --help` states that the estimator backend "is the arm that draws
the white halo around a dark subject on a bright ground", and prices it: *"the
estimator's backdrop sits 4739 DN below its own far field across the 80-200 px
aura zone; the pyramid sits 166 DN below."* That claim is the justification for
the default having moved to `pyramid`, and it is the direct answer to the
owner's complaint. **It had never been checked by an instrument built
independently of the lane that made it.**

### 108.2 The arms

```
strehl stack D:\personal\macro\flower-bud-alone-cpl --out <arm>.tiff \
    --srgb --exposure 1.0 --merge {pyramid|estimator} --limit 60
```

Same binary, same 60 frames, same exposure, same colour path. Measured with
`halo_profile.py` (section 107), which is an **absolute single-image** detector
commissioned on six arms and blind to which file came from which merge.

### 108.3 The result

| arm | overshoot | bump | penumbra | far field | verdict |
|---|---:|---:|---:|---:|---|
| `estimator` | −6845.8 | **0.0** | −22676.6 | 62597 | clean |
| `pyramid` | −5890.9 | **0.0** | −22893.1 | 62385 | clean |

Both profiles are **strictly monotone outward** — `bump` is exactly 0.0 on each,
which is the no-rim signature section 107 established. **Neither merge draws a
bright rim on this subject at this depth.**

The near-subject backdrop is measurably darker on the estimator: at d = 80–120 px
it sits **955 DN** further below its own far field than the pyramid does. That
is the **same direction** as the help text's claim.

### 108.4 What this does NOT establish, stated because the numbers invite it

**It does not reproduce 4739 / 166, and must not be quoted as confirming them.**
Three differences make the magnitudes incomparable, and all three are mine:

1. The corpus measurement was made **camera-linear**; this one is `--srgb` with
   `--exposure 1.0` (which is **+1 stop, gain 2.000x**, not unity — the flag
   names stops). A transfer curve and a gain both rescale a DN difference.
2. The corpus measurement used **one mask for both arms**. `halo_profile.py`
   segments **each image independently**, and it did: n = 4340 vs 4336 in the
   innermost band, and the far fields differ by 212 DN. Two arms measured
   against two different silhouettes are not a difference of 955 DN in the
   aura; they are a difference of 955 DN plus an unmeasured mask term.
3. 60 frames, not 205. Aura depth may vary with bracket depth; nobody has
   measured that.

**The right instrument for an arm-vs-arm aura depth is the comparator**
(`veil_accept.py` / `veil_absolute.py`), which takes an on/off pair and one
mask. `halo_profile.py` was built for a different question — *does this finished
master have a rim* — and section 107.4's own rule applies to me here: a
commissioned metric is trustworthy only within the range its commission spans,
and its commission spanned single images, not paired arms.

### 108.5 What it does establish

> **The shipping default produces no bright rim on this subject, measured by an
> instrument built independently of the lane that chose the default, and the
> older arm does not either at this depth — the estimator's defect on this
> subject is a dark aura, not a white halo.**

That last clause matters for how the defect is described to users. The help text
calls it "the white halo"; on this subject, at this depth, what is measurable is
a **darkening of the backdrop near the subject**, and both arms have it (−22.7k
and −22.9k DN at d = 2–6 px), with the estimator's decaying more slowly. Against
a bright ground a slowly-decaying dark aura reads to the eye as a halo, so the
word is defensible as description — but the sign of the measured quantity is
negative, and a reader who goes looking for a positive overshoot will not find
one and may wrongly conclude the claim was false.

## 109. The re-render I ordered was unnecessary, and it proved something better than what it was for

**Status: MEASURED.** `2026-08-27`, `SHIP-V3` vs `SHIP-V4`, all 26 masters.

### 109.1 The claim I made, and its refutation

Section 106 and my running notes recorded `SHIP-V3` as **stale — "no ICC/DPI"** —
and I ordered a full 26-subject re-render (`SHIP-V4`, 4,825 frames, 21.0 min) to
obtain masters carrying the colour profile. The premise was wrong:

```
SHIP-V3  wrapped-text-1--SHIP-V3.tiff   icc=2716  xres=(300, 1)  unit=2
SHIP-V4  wrapped-text-1--SHIP-V4.tiff   icc=2716  xres=(300, 1)  unit=2
```

**V3 already had both.** It was rendered after `c7bb6282` landed the ICC work,
and I recorded it as stale from memory rather than from the file. Twenty-one
minutes of machine time were spent to fix a defect that did not exist.

> **A file's properties are a question, not a recollection.** I had `tifffile`
> and one command available the entire time.

### 109.2 What the wasted run actually measured

```
masters v3=26 v4=26 common=26
byte-identical: 26    differ: 0    sum=26 == common=26
```

**All 26 masters are byte-identical between the two arms.** Not merely
pixel-identical — the whole file, including metadata.

That is a determinism result no test in this repository produces. The
byte-freezes pin **two** renders of **one** subject at **20** frames. This pins:

| property | value |
|---|---|
| subjects | 26 |
| frames | 4,825 |
| output | 33 MP, 16-bit RGB, ~198 MB each |
| wall clock | 21.0 min |
| concurrency | 4 worker threads, **under 4-agent machine load** |
| separation | two independent invocations, hours apart |
| result | **26 / 26 byte-identical, 0 differ** |

The load matters. Both runs used a work-stealing multithreaded fold while other
agents competed for the same cores, so **thread scheduling certainly differed
between the two runs** and the output did not. That is evidence the fold's
reduction order is fixed by construction rather than by timing — the specific
failure that makes most parallel float pipelines non-reproducible, and the one
that would be hardest to find later.

### 109.3 Why this belongs in a stacker's evidence and not just its trivia

Reproducibility is a *product* property here, not hygiene. Every quality number
in this corpus is measured on a rendered master; if the renderer were
timing-dependent, every one of them would carry an unmeasured error bar, and
`V-REVIEW`'s nine acquittals — each a comparison between a master and its own
source frames — would be comparisons against a moving target.

**The sidecars correctly differ.** `*.ok` and `*.provenance.txt` differ in all
26 cases, because they record the arm name, timestamp and commit. A run that
produced identical sidecars would mean the provenance was not being written.
Both partitions are the expected reading:

```
masters   : 26 byte-identical,  0 differ
sidecars  :  0 byte-identical, 52 differ   (26 .ok + 26 .provenance.txt)
```

### 109.4 Scope

This shows **determinism**, i.e. that the pipeline returns the same answer twice.
It says nothing about whether that answer is *correct*, and it does not transfer
across commits, hardware, or thread counts — only across two runs of one binary
on one machine. A byte-identical repeat is the weakest useful reproducibility
claim; it is recorded because it was measured, and because it was measured at a
scale the test suite cannot reach.

## 110. Four retractions, and the shape they share

V-GATHER was asked to verify the gather flip (`740e7056`). It upheld the flip and
refuted **three of the four arguments offered in support of it**. Several of those
arguments were mine. This section withdraws them, because a conclusion that
survives its own evidence being wrong is a conclusion held for the wrong reason,
and the next person to lean on it will not know that.

### 110.1 Statistic B was never a ringing metric

`overshoot_frac` in `experiments/ORCH-drift-check/orch_abpair.py` high-passes the
image and counts pixels beyond `3 * sigma` -- where `sigma` is the standard
deviation of that same high-pass. Scaling the image scales the residual and the
threshold identically. **The amplitude cancels algebraically.** What survives is
the tail shape of the distribution, which is not a quantity anyone wanted.

Commissioned, it is worse than useless -- it is inverted:

| arm | expected | measured |
|---|---|---|
| amplitude scaled | rises | invariant to **six significant figures** |
| planted 2 px ring at 40% of step | rises | reads an **improvement** |
| unsharp mask applied | rises | reads an **improvement** |
| blur applied | falls | **rises monotonically** |

`740e7056` cited this statistic as its evidence of no added ringing: *"did not
move (1.086% -> 1.053%, 1.744% -> 1.744%)"*. On the statistic's own commissioning
a fall from 1.086 to 1.053 is the signature of **added sharpening**. The commit
read its most reassuring number backwards.

The tell was available the whole time and it was the reassurance itself. A
statistic that does not move when the image is scaled is not measuring anything
about the image's amplitudes, and ringing is an amplitude. The function is marked
REFUTED in place rather than deleted, so the numbers in `740e7056` stay
reproducible, and its printed columns now read `REFUTED`.

> **A statistic that is amplitude-invariant to six significant figures is not
> measuring an amplitude. The comfort it gave was the tell.**

### 110.2 Statistic A was aimed where ringing does not live

`orch_halo.py` runs `BAND=(8,90)` at `DS=2`, which is **16 to 180 full-resolution
pixels**. A Catmull-Rom or Malvar reconstruction lobe lives at **1 to 4 px**. The
instrument was not weak on the question; it was not pointed at it. Its silence
was mistaken for an answer.

This compounds an error in my own framing. I wrote that the two statistics
disagreed and that a visual tie-break was therefore needed. They did not
disagree -- one was inverted and the other was blind. And the visual tie-break
examined `over_hi` when **100% of the excursion was in `over_lo`**. Three
independent ways of being wrong, arranged so that they agreed.

Ringing was eventually settled by a third instrument that passes narrow-ring,
unsharp, clean-edge **and planted-improvement** commissioning. There is no
ringing regression. That conclusion stands; the two arguments previously offered
for it do not.

### 110.3 The speedup is a harvest of idle cores, not less work

The gather flip was reported as faster. It performs **+1.5 s/frame of additional
CPU work** and is faster only because this machine has cores that were otherwise
idle. That is a real wall-clock gain on this box and a real gain on any box with
spare parallelism, but it is **not an algorithmic throughput property** and must
never be quoted as one. On a core-starved machine the same change is a
regression.

### 110.4 The sharpness budget does not close

`BUILD-SHARP` section 1 reported the budget closing to **2.6%**. Re-measured, the
gap is **+12.09%**, with **17.01 um unattributed**. Retracted. Related: `--gate 0`
is not the exact paired reference it was used as -- the election moves **32.8% to
34.1% of pixels** between the two arms, so the comparison was never holding the
merge fixed.

### 110.5 Costs that were not reported

Upheld does not mean free. The flip carries two costs that no summary mentioned:

- flat-region high-pass rms up **x1.267 to x1.870**, mostly consistent with noise
  *restoration* against a floor of about x2.0;
- **chroma (R-B) high-pass up 25.2% to 48.6%**, traced to a **double demosaic** --
  a warp-time demosaic feeding the final Malvar. Whether that chroma excess is
  restored or manufactured is open, and it decides whether this is honest noise
  or a defect in the shipping path.
- the memory budget is **blown by 29%** on the default path, which makes the
  `WarpScratch` documentation at `align_cmd.rs:1481` false as written.

### 110.6 The rule this earns

Every failure above is the same failure. An instrument was trusted outside the
range its commissioning spanned, or was never commissioned in the direction that
mattered. Both refuted statistics had only ever been shown things that made the
image *worse*.

> **Commission with a planted improvement as well as a planted defect. A metric
> shown only degradations cannot distinguish "blind" from "correct" -- both
> produce the same reassuring flat line.**

This is now the third instrument in this project caught reading backwards, after
`tri.blur_equiv`, whose error was bounded below by zero so that no input could
make it charge for a halo. The pattern is not bad luck. It is what happens when
commissioning is designed by the same person who wants the answer.
