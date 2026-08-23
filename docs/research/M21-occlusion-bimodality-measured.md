# M21 — Is the through-focus curve bimodal at occluding edges?

> **NOT INDEPENDENTLY VERIFIED.** Written by the same agent that ran the
> measurements. Rule 12 applies to this document as much as to any milestone
> report: its author is the last person who should be trusted to check it.
> Everything below is labelled MEASURED / DERIVED / ARGUED. Attack it.

Tests proposal **R2** from the external review
([`../proposals/2026-08-external-review.md`](../proposals/2026-08-external-review.md)),
which the triage called the review's second-best idea and which was, until now,
the highest-value *untested* claim in it.

## 1. The claim under test

The review argues that at an occluding edge a background pixel is **veiled** by
defocused foreground:

```
I_k = a_k·(F (*) PSF_k) + (1-a_k)·(B (*) PSF_k)
```

so its through-focus response has **two peaks** — one at the foreground depth,
one at the background depth. No frame shows clean background, therefore no
selector can be correct there, and the halo every stacker produces is a
structural consequence rather than a tuning failure. The review's proposed
remedy is to detect bimodality and unmix the two layers.

The mechanism is plausible on optics alone. The question this milestone asks is
narrower and entirely empirical: **is the second peak actually present in this
rig's data, at a level a detector could act on?**

## 2. What was measured

Focus volume: Sobel magnitude, box-averaged at radius `R`, on the CFA green
plane, over a fixed 1024x1024 crop. A pixel is **multi-peaked** when its
frame-axis response has two or more strict interior local maxima, each rising
at least 4% of the curve's range above both neighbours, after a light [1,2,1]
smoothing along the focus axis.

Enrichment is the ratio of the multi-peak rate at **depth steps** to the rate on
**smooth depth**, where the depth-step map is `|grad|` of a median-filtered
argmax field.

Three real stacks, no plants: `109MSDCF` (22 frames), `119MSDCF` (33),
`coffee-bean` (105, subsampled 5x to 21).

## 3. The first two answers were both wrong, for different reasons

Recorded because both failure modes are reusable.

**Attempt 1 said the effect was absent.** At the shipped operator's radius 13,
109MSDCF gave 11.3% multi-peaked and enrichment **0.36x** — depleted at depth
steps, the opposite of the prediction. That measurement is real but it answers
the wrong question: radius 13 is 27 CFA px, i.e. **54 sensor px**. The veiled
zone at an occluding boundary is far narrower. The window was averaging both
layers together and destroying the very structure being looked for.
**Lesson: a detector inherited from a different stage is not a neutral
instrument.**

**Attempt 2 said the effect was enormous, and was circular.** At radius 2,
`coffee-bean` gave enrichment **29.47x**. But bimodality was being binned
against a depth-step map derived from the *same* focus volume — and a bimodal
pixel makes its own argmax flip between the two peaks, which mechanically
manufactures a high `|grad argmax|` exactly where bimodality is detected. The
statistic was partly measuring itself. Breaking the circularity (below) cut
29.47x to **4.38x**, so roughly **85% of the first number was the tautology**.

This is the second circularity found in as many milestones — see M20's open
concern about fact 27's `B`. It is now a named discipline item.

## 4. The decidable design

Three changes make the number mean something:

1. **Cross-scale binning.** Bimodality is measured at R=2; the depth-step map
   comes from the R=13 argmax, median-filtered 5x5. The median filter removes
   the isolated argmax flips a bimodal pixel produces, so the two statistics no
   longer share their driving mechanism.
2. **Absolute bins,** not percentiles. `step >= 1.0` frame vs `step < 0.25`.
   Percentile bins had silently gone degenerate on `coffee-bean`, whose argmax
   field is piecewise constant over more than half the frame — the earlier run
   printed `nan` for exactly this reason.
3. **A scene-matched permutation placebo.** Permuting the frame order preserves
   every noise statistic *exactly* while destroying all genuine focus structure.
   A real effect must collapse to 1.0x under permutation. This is a far better
   null than a different scene, because it holds sensor, ISO, texture and
   exposure fixed by construction.

## 5. MEASURED — the result

Multi-peak rate at R=2, enrichment binned on the independent R=13 depth-step map:

| stack | frames | overall | at depth step | smooth depth | **enrichment** | permuted |
|---|---:|---:|---:|---:|---:|---:|
| `109MSDCF` | 22 | 60.7% | 53.7% | 61.8% | **0.87x** | 1.01x |
| `119MSDCF` | 33 | 63.3% | 62.6% | 63.2% | **0.99x** | 1.00x |
| `coffee-bean` | 21 | 4.8% | 19.4% | 4.4% | **4.38x** | 1.01x |

**The placebo behaves.** Permutation drives enrichment to 1.01 / 1.00 / 1.01 on
all three stacks. The statistic carries no built-in bias; a null reads as 1.00x.
This is what makes the 4.38x interpretable.

**Stability.** Re-running `coffee-bean` from a different subsample offset gives
**4.43x** against 4.38x.

**The intensity-edge confound runs the other way.** Binning on intensity
gradient *alone* gives **0.00x** — multi-peakedness is strongly *anti*-correlated
with intensity edges (0.0% at the top decile of intensity gradient vs 9.2% in
flat regions). So the effect cannot be an intensity-edge artifact in disguise.

**It survives stratification.** Within every quintile of intensity gradient,
depth steps remain enriched:

| quintile | offset 0 | offset 2 |
|---|---:|---:|
| Q1 (flattest) | 1.60x | 1.57x |
| Q2 | 1.43x | 1.96x |
| Q3 | 2.33x | 1.51x |
| Q4 | 2.57x | 2.94x |
| Q5 (most textured) | **9.50x** | **14.32x** |
| **pooled (geometric mean)** | **2.65x** | **2.87x** |

So the raw 4.38x decomposes into roughly 1.6x of composition (depth steps sit in
more textured places) and a genuine **~2.7x within-stratum depth-step
enrichment** — which *rises monotonically with texture*, reaching 9.5–14.3x in
the most textured quintile. That ordering matters: the signal is strongest
exactly where a reconstruction would have something to work with.

## 6. MEASURED — why the two shallow stacks show nothing

Not because the physics differs. Because the detector is saturated by noise.

Compare each stack's real multi-peak rate against its own permuted rate — the
rate the detector reports on pure noise with identical statistics:

| stack | real | permuted (noise floor) | headroom |
|---|---:|---:|---:|
| `109MSDCF` | 60.7% | 92.5% | 1.5x |
| `119MSDCF` | 63.3% | 97.8% | 1.5x |
| `coffee-bean` | 4.8% | 86.2% | **18.0x** |

On 109 and 119 at R=2, six pixels in ten are already flagged multi-peaked by
noise alone. There is no dynamic range left for a real second peak to show up
in. On `coffee-bean` the same detector reports 4.8% against a 86.2% noise
ceiling.

This corroborates M20 §7 from a completely independent direction: for the median
pixel on this rig, local noise exceeds local signal structure even in that
pixel's own best frame. Here that fact is not an abstraction — it is the reason
a physically real effect is undetectable on two of three stacks.

DERIVED, not measured: `coffee-bean`'s advantage is presumed to come from being
a 105-frame stack subsampled 5x (coarser effective focus step, so peaks separate
further relative to noise) combined with stronger texture. The subsample-offset
check holds the sampling fixed and so does not separate these two causes. **A
frame-density sweep on `coffee-bean` would separate them and has not been run.**

## 7. What this means for the design

**R2's mechanism is real. R2's detector, as the review states it, is not
deployable on this rig without the noise model.** That is a conditional
endorsement, and the condition is the project's own differentiator:

- A bimodality test thresholded on curve shape alone reports 60% false positives
  on an ordinary 22-frame stack. Any competitor attempting this without
  calibrated noise would ship exactly that.
- The test must instead ask whether the dip between two peaks is deeper than the
  curve's **predicted** noise at that pixel's signal level — which strehl can
  compute from `sigma^2(S) = g*S + (RN*g)^2` and nobody else can.
- ARGUED: this reframes R2 from "add an occlusion detector" to "the noise model
  is what makes occlusion detection possible at all", which is the same shape of
  argument M20 made for the Wiener guard, arrived at independently.

**The scale is not free either.** The effect is invisible at the shipped radius
13 and present at radius 2. Whatever stage detects bimodality cannot reuse the
merge's focus window. That is an architectural constraint on the fold seam
(review item R14) that was not previously on the list: the per-pixel sufficient
statistics must be carried at a **finer scale** than the focus measure, or a
second pass must recompute them.

**It also tightens the capture request.** None of the three stacks contains a
deliberate occluding edge; `coffee-bean`'s depth steps are incidental. The
occlusion captures in [`../captures-needed.md`](../captures-needed.md) §5 are now
blocking a *measured, live* result rather than a hypothesis, and the tilted
planar target (§8) is the matching null — a plane has no occlusions, so any
bimodality flagged on one is a false positive by construction.

## 8. What was NOT measured

- No unmixing was attempted. This milestone establishes that the *signal* exists;
  it says nothing about whether the two-layer fit recovers usable background.
- No ground truth. "Depth step" is inferred from the argmax field, not known.
  Enrichment against true occlusion boundaries is unmeasured.
- One crop, one channel, no alignment. Frames were used as shot. Drift on these
  stacks is sub-pixel to a few px, which is small against R=13 but **not
  negligible against R=2** — this is the most likely defect in the R=2 numbers
  and a verifier should attack it first.
- The 4% peak-prominence threshold and the `>=1.0` step threshold were set once,
  by hand, and never swept. The permutation placebo bounds their *bias* but not
  their sensitivity.
- `foam` was excluded (its scene evolves); `112`/`113` were not run.

## 9. Reproducing

```
experiments/m21-occlusion-bimodality/src/
  01-first-look.py            first look at R=13 -- the wrong-instrument result
  02-radius-sweep.py          R in {2,5,13}; also the circular 29.47x, kept as evidence
  03-permutation-placebo.py   the decidable design; the table in section 5
  04-intensity-stratified.py  subsample stability + the intensity-gradient stratification
```

Needs read access to `C:\dev\macro\test\` and `D:\personal\macro\`. Run in
order; 02 is retained deliberately so the circularity can be re-derived rather
than taken on trust.
