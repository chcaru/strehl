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
