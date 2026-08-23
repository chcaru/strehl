# M28 — Is a robustness mask separable from defocus in a focus stack?

> **NOT INDEPENDENTLY VERIFIED.** Measured by the orchestrator. Rule 12 binds
> its author exactly as it binds any milestone author.

Review item **R10** asks for a robustness/outlier mask of "Wronski Eq. 5–9
shape": per-tile, per-frame, noise-normalised disagreement against a running
estimate. That shape is right for a **burst**, where every frame is nominally
identical so disagreement means motion. **A focus stack is the opposite case:
the frames are supposed to disagree, and their disagreement is the entire signal
the merge exists to harvest.** So the prior question is whether outlier signal is
separable from defocus at all.

It is, and the correction to R10 is one line: **compare against the immediate
neighbours, not against a running estimate over the stack.**

Instrument: green sublattice of a centred 3072 px crop, three stacks chosen for
what is known about their stability.

| role | stack | n | why |
|---|---|---:|---|
| negative | `109MSDCF` | 22 | photometrically quietest in the corpus (fact 180), no known motion |
| intermediate | `coffee-bubbles` | 19 | bubbles drift and burst |
| positive | `foam` | 50 of 100 | **rejected from the corpus because the scene visibly evolves** — which is exactly what makes it the right known-real positive control here |

## 1. MEASURED — a whole-stack reference buys 10× the geometric residual for nothing

Noise-normalised residual between frames separated by `dk`, on the **clean**
stack (median over pixels, so pure noise would read a flat 0.6745):

| separation `dk` | 1 | 2 | 4 | 8 | 16 |
|---|---:|---:|---:|---:|---:|
| `109MSDCF` (clean) | **1.13** | 1.78 | 3.24 | 5.70 | **12.30** |
| `coffee-bubbles` | 1.32 | 1.65 | 2.25 | 3.07 | 3.53 |
| `foam` | 4.48 | 8.70 | 16.63 | 29.29 | 42.49 |

On the clean stack the residual grows **10.9× over a 16× separation** — very
nearly linear. That is the signature of an **accumulating geometric warp**:
noise would be flat, and defocus difference would *saturate* once a region is
fully blurred. Frames that are adjacent differ by noise (1.13); frames 16 apart
differ by breathing.

The radial test confirms it and gives the decisive number. With a **whole-stack**
reference the residual rises 1.82× from frame centre to corner. With an
**adjacent-frame** reference:

```
radial |z|, adjacent-frame reference, d=8
  0.72  0.82  0.82  0.78  0.73  0.75  0.71  0.70      outer/inner 0.98
```

**Perfectly flat.** One frame of breathing displaces the corner by well under a
pixel, so the geometric term simply is not there.

**Architectural consequence, and it is the opposite of what I predicted.** I
expected to conclude *"a robustness mask cannot run before alignment."* Measured,
the conclusion is that with an adjacent-frame reference **it can** — which is
strictly better news, because it means alignment itself can be protected from
outliers rather than having to precede their detection.

## 2. MEASURED — the noise model predicts the clean residual to within 10%, with no free parameters

Median tile `|z|` against the **0.6745** half-normal expectation for pure noise:

| stack | median tile \|z\| | × pure noise |
|---|---:|---:|
| `109MSDCF` | 0.7416 | **1.099** |
| `coffee-bubbles` | 1.110 | 1.645 |
| `foam` | 1.415 | 2.097 |

M4's `σ²(S) = g·S + (RN_e·g)²` was calibrated on flat patches. Here it predicts
the adjacent-frame residual of 256-sensor-pixel tiles on a real subject to
**9.9%**, on data and at a scale it was never fitted to. That is an independent
validation of the noise model, arrived at incidentally.

## 3. MEASURED — sensitivity, with a plant and a placebo

A `W = 128` green-pixel tile of the middle frame is replaced by the same tile
taken `s` pixels away **in the same frame**, so noise, defocus, illumination and
sensor position are all correct by construction and nothing is synthesised
(facts 61–64 exist because this project has shipped bad plants before). The
**placebo is `s = 0`**, the identical copy, which exercises every line of the
planting machinery.

Detection rate at scale `d = 8`, thresholds calibrated on the same stack:

| shift `s` | median tile \|z\| | @FPR 5% | @FPR 1% | @FPR 0.1% |
|---:|---:|---:|---:|---:|
| **0 (placebo)** | 0.79 | 8.3% | **0.0%** | **0.0%** |
| 1 | 1.20 | 34.1% | 15.2% | 7.6% |
| 2 | 1.80 | 59.8% | 31.1% | 15.9% |
| 4 | 3.06 | 89.4% | 53.8% | 37.9% |
| 8 | 4.96 | 100.0% | 77.3% | 56.8% |
| 16 | 8.60 | 100.0% | 96.2% | 71.2% |
| 32 | 12.97 | 100.0% | 100.0% | 82.6% |

Monotone at every scale and every operating point. **In physical units**, a
4-green-pixel shift is 8 sensor pixels = **41 µm on the sensor ≈ 20 µm at the
subject** at m ≈ 2.0, caught 89% of the time at FPR 5%.

**The placebo is clean at FPR ≤ 1% and mildly inflated at FPR 5%** (8.3–10.6%
against a nominal 5%). That is not a machinery artefact: the null tiles come from
one frame while the threshold is calibrated across the others, and the middle
frame sits near peak focus. **The threshold should be calibrated per frame, not
per stack.**

## 4. MEASURED — the tile scale is not a sensitivity knob

Detection at FPR 1%, by scale:

| shift | `d = 4` | `d = 8` | `d = 16` |
|---:|---:|---:|---:|
| 1 | 18.2% | 15.2% | 12.9% |
| 4 | 58.3% | 53.8% | 49.2% |
| 8 | 81.1% | 77.3% | 68.2% |
| 16 | 97.7% | 96.2% | 85.6% |

Near-flat across a 4× range of scale, refuting the prediction that detection
would switch on around `s ≈ d`. The reason is visible in the numbers: the median
planted `|z|` rises with `d` (3.06 → 4.36 at `s = 4`) but so does the threshold
(2.62 → 4.39), because the baseline tail is dominated by *deterministic* defocus
structure rather than by noise, so signal and threshold average down together.

**Choose the tile scale for compute cost, not for detection power.** This cuts
against the usual reasoning about burst-denoising tile sizes.

## 5. MEASURED — transfer to real disturbance, ordering predicted in advance

Threshold calibrated **entirely on the clean stack**, then applied unchanged:

| stack | flagged @FPR 5% | @FPR 1% | @FPR 0.1% |
|---|---:|---:|---:|
| `109MSDCF` (clean) | 5.00% | **1.01%** | 0.10% |
| `coffee-bubbles` | 27.70% | **8.33%** | 1.59% |
| `foam` (evolving) | 51.58% | **17.88%** | 3.43% |

The predicted ordering holds, the calibration stack lands on nominal by
construction, and the two disturbed stacks separate by 2.1× from each other.

**Confound, stated plainly:** the three stacks differ in subject and contrast as
well as in stability, so this cannot separate *"more disturbance"* from *"more
contrast"*. The guards are that `|z|` is noise-normalised so ISO is handled by
construction, and that the direction was pre-registered from what the stacks are
rather than read off afterwards.

## 6. MEASURED — my per-frame gain estimator was a confound, and M24 needs a *how*

Script 01 fitted **4.28%** peak-to-peak gain on `109MSDCF`; M24 independently
measured **0.91%**. Four estimators on the same data:

| estimator | `109MSDCF` | `coffee-bubbles` | `foam` |
|---|---:|---:|---:|
| median, all px | **4.28%** | 7.55% | **61.49%** |
| mean, all px | **1.02%** | 12.85% | **11.05%** |
| median, low-gradient px | 0.94% | 7.85% | 84.98% |
| mean, low-gradient px | 0.99% | 5.63% | 47.70% |
| *M24, full-frame green mean* | *0.91%* | — | — |

Three of four land at 0.94–1.02% on the clean stack and agree with M24; **the
median over a subject-centred crop is the outlier**, because as focus sweeps the
subject's contrast changes and a median over that region absorbs *focus* signal
into what it calls gain. **M24 established that gain must be fitted rather than
read from EXIF; M28 adds how — the mean over all pixels, never a median over a
subject-centred region.**

Two further observations. The low-gradient restriction is *not* the safe choice
it looks: on `foam` it is the **worst** estimator (84.98%), because "low gradient
in the median reference" selects nothing meaningful when the scene evolves. And
the **disagreement between estimators is itself a scene-instability signal** —
5.6× spread on `foam` against 1.09× on the clean stack — though that is an
observation from three stacks, not a calibrated detector.

## 7. What I got wrong

1. **P1 — predicted the full-resolution residual would be large in every stack
   because it measures defocus. Refuted:** median `|z|` on the clean stack is
   **1.01** at full resolution, the noise floor. Defocus disagreement is confined
   to a textured minority (5.5% of pixels above `|z| > 5`), so the *typical*
   pixel's frame-to-frame difference in a clean focus stack **is noise**.
2. **P2 — predicted lowpassing would collapse the clean stack's residual toward
   the noise floor. Refuted, backwards:** it *rises* 1.01 → 25.07 at d=64,
   because averaging `d²` pixels divides the **noise** by `d` while leaving any
   **deterministic** residual in place. The sweep is an instrument for measuring
   the deterministic term, not the separator it was designed as.
3. **P8 — predicted `z / (|grad|·r)` would be flat if breathing explains the
   radial rise. Failed on all three stacks** (falls 2.6–2.9× from centre to
   corner). ARGUED explanation: at the periphery, breathing displaces by more
   than one decimated pixel, where a first-order `|grad|·dx` model must break
   down. Not measured; §1's separation test settles the same question without
   needing any linearisation, and is the evidence relied on.
4. **P12 — predicted the detection threshold at `s ≈ d`. Refuted** (§4).
5. **The gradient normalisation in script 02 was an artefact of its own divisor**
   — it claimed a 9.25× radial *rise* on `coffee-bubbles` where the raw profile
   *falls* to 0.21×. Both cannot be right; the raw profile is the one to read.
   Discipline 121's lesson, in a second form: check what makes the denominator
   small before dividing by it.

## 8. What was NOT measured

- **Three stacks, one crop size, one operator.** No aligned-stack control: every
  number is from unaligned frames, which is the honest operating condition for a
  pre-alignment mask but not for a post-alignment one.
- **The plant is a rigid translation of a square tile.** Real outliers deform,
  occlude, and change illumination. The measured sensitivity is a lower bound
  for translation and says nothing about the others.
- **No merge output was produced.** This measures a *detector*, not the effect of
  masking on a merged image. Whether flagging 8.33% of `coffee-bubbles`' tiles
  improves or harms the result is unmeasured and is the obvious next question.
- **No leave-one-out.** The whole-stack references in §1 include the frame being
  tested; with 19–50 frames and a median the effect is small but is not zero.
- The 0.6745 comparison in §2 assumes the residual is Gaussian; heavy tails would
  bias the ratio, and the tails are exactly what §3 and §5 measure.

## 9. Proposed record

Facts **220–225**, discipline **130–131**, question **45**. Reconciled by the
orchestrator at fold time, not here.

## 10. Reproducing

```
experiments/m28-robustness-scale/src/
  01-scale-sweep.py   residual vs spatial scale, three stacks    (refutes P1, P2)
  02-identity.py      radial profile + residual vs separation    (the dk result)
  03-confounds.py     gradient-normalisation and gain-fit checks (refutes P8, confirms P9)
  04-sensitivity.py   planted displacement + shift-zero placebo  (refutes P12)
  05-transfer.py      clean-calibrated threshold on real stacks  (confirms P14)
```

Scripts are committed exactly as run; script 05 carries one unused local
(`nt`) that does not affect any result, left in place rather than corrected so
that the committed code is the code that produced the numbers above.
