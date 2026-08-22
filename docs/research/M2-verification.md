# M2 verification — the argmax defect, independently re-derived

**Status: MEASURED.** Independent verification of `M2-baseline-skeleton.md` by a second agent
that did not write the skeleton, was told not to trust its report, and re-derived every headline
number from the raw files. All of its code lived outside the repository and was deleted; the
repository was not modified.

This document exists because of project rule 8 and the ultra-mode rule that **the author never
verifies their own work**. It records both what survived and what did not.

## 0. The verdict in one paragraph

**The headline survives and is now causally proven.** The naive argmax baseline really is
**1.253x noisier than one unstacked frame** on a flat region, reproduced digit-for-digit. More
importantly, the control that settles *why* — which the skeleton's author never ran — was run:
replacing argmax with a plain mean over the same 22 frames, the same ROI, the same drift and the
same scene structure gives **0.534x**. Drift and structure alone therefore produce a ratio well
*below* 1.0 and cannot be what pushes argmax above it. **Four supporting numbers were wrong**, one
of them in the unsafe direction: the residual-structure estimate is ~2x low, and the "1.13x hard
floor" built on it collapses to no floor at all. Correctly structure-corrected, the ratio is
**~1.48x**, not the published 1.29-1.31x — the result is *stronger* than claimed, defended by
different evidence than claimed.

## 1. What was confirmed

| Claim | Verdict | Evidence |
| --- | --- | --- |
| `fmt` / `clippy -D warnings` / `test` clean, 52 passing | **CONFIRMED** | Re-run from a cold `--target-dir` so nothing was served from cache. 6 + 38 + 8 = 52. `git grep -c "#[test]"` at `882822c` = 11, confirming the "was 11" baseline |
| **RATIO 1.253x** (35.328 / 28.201 DN) | **CONFIRMED**, digit-for-digit | Independent run, then re-derived from the raw ARWs in a separate crate |
| Byte-identical across reduction trees | **CONFIRMED** | Fresh run reproduced both published SHA-256 digests; `RAYON_NUM_THREADS=3` (3 in flight, not 11) produced *the same two hashes* |
| ROI chosen by structure, not by outcome | **CONFIRMED** | An independent 16x-downsample search ranks `2272,1344` **51st of 26,724** blocks, and **no** block is simultaneously flatter and closer to plane centre. Not cherry-picked |
| Rule 7 — no statistic touches the zero padding | **CONFIRMED** by code reading | Every read in `strehl-core` goes through `Frame::active_row` / `quad_rows`; `.data` is touched only inside `strehl-raw`; active area confirmed at origin (0,0) so there is no offset trap either |
| The output is a real stacked photograph | **CONFIRMED** | IFDs hand-parsed. Only **2.442%** of pixels are identical to decoded frame 0 — exactly frame 0's win share. Mean gradient **1.453x** a single frame. ROI sd read back *from the file* = 35.328 DN |

**The four spec-required tests were mutation-tested** — the core was copied out of the repo, a
defect injected, the suite re-run. All four caught their defect: `Selection::beats` `>`→`>=`;
`sensor_coord` dx/dy swapped; box border dividing by the full window instead of the clamped count;
running-sum priming off-by-one. **They have teeth.** (Naming caveat: `absorb_is_associative_over_
every_partition_of_the_stack` covers every *contiguous* cut plus one 3-way split, which is what
`par_chunks` produces — but not literally every partition. The name overstates.)

**A hypothesis of my own was refuted, and it was backwards.** I suspected "single frame 11" was a
flattering control chosen because it was quiet. Per-frame sigma in that ROI across all 22 frames:
min **22.852** (frame 21), median **25.347**, max **29.560** (frame 10). **Frame 11 at 28.201 is
the 4th-noisiest of 22** — the published control is the *conservative* end. Ratios against min /
median / max are **1.546x / 1.394x / 1.195x**. The mechanism is that single-frame spatial sd in
this ROI tracks how *in focus* the paper fibre is, and frame 11 sits near the focus peak.

## 2. The control that settles causation

Every number in §1 is merely *consistent* with "argmax amplifies noise". None isolates argmax as
the cause: the ROI has structure, the frames are unaligned, and there was an unexplained 1.46x gap
against the noise model. So the decisive experiment was run — identical frames, identical ROI,
identical drift, identical structure, **only the merge rule changed**.

Flat ROI `2272,1344,256,256`:

| Merge rule | sigma (DN) | vs frame 11 |
| --- | --- | --- |
| single frame 11 (no stacking) | 28.201 | 1.000x |
| **argmax — the M2 baseline** | **35.328** | **1.253x** |
| **unweighted mean of 22** | **15.050** | **0.534x** |
| median of 22 | 15.304 | 0.543x |
| **placebo A** — the same winner map shifted by half a ROI: identical marginal frame histogram, identical drift and defocus mixing, blind only to *this pixel's own noise* | **27.673** | **0.981x** |
| placebo B — uniform random frame per pixel | 26.411 | 0.937x |
| **regularised** — argmax of a 17x17-smoothed focus field | **30.305** | **1.075x** |

**This is the strongest evidence the project has.** Read it in three steps:

1. **The mean lands at 0.534x**, heading toward `sigma/sqrt(22)` and floored by structure it cannot
   remove. So drift and scene structure *by themselves* push the ratio **down**, not up. They are
   not the cause.
2. **Placebo A gives 0.981x.** A selector with argmax's exact frame-usage statistics, mixing the
   same defocus and the same misregistration, but decoupled from the pixel's own noise, is
   harmless. The noise-correlated selection excess is `sqrt(35.328^2 - 27.673^2)` = **21.96 DN**.
3. Therefore **the 1.253x is caused by selection being coupled to noise**, which is precisely the
   thesis.

Second flat ROI `2352,1408` reproduces it: argmax 1.263x, mean 0.506x.

**The N-sweep kills the drift hypothesis outright.** Centred on frame 11, drift ~0.771 px/step:

| N | total drift | argmax | mean |
| --- | --- | --- | --- |
| 3 | 1.5 px | **1.131x** | 0.820x |
| 5 | 3.1 px | 1.183x | 0.751x |
| 7 | 4.6 px | 1.213x | 0.703x |
| 11 | 7.7 px | 1.241x | 0.639x |
| 22 | 16.2 px | 1.253x | 0.534x |

Argmax is already above 1.0 at **N=3 with 1.5 px of total drift**, and grows monotonically in N —
exactly as argmax-over-N-noisy-statistics theory predicts (fact 7: 1.95x at N=10 over pure noise)
and exactly as a drift explanation does not.

### 2.1 Rule 9: the control that should fail, and does

Project rule 9 requires every metric to be paired with a control that ought to break it. Averaging
must destroy detail — that is the entire reason selection exists — so a mean that looked good
everywhere would mean the flat-ROI metric was measuring the wrong thing.

High-detail ROIs `1630,1044` (paint crossing) and `64,800` (busiest block in the frame): the mean's
sigma looks harmless at **0.899x** and **0.995x**, but its mean |gradient| **collapses 11.89 -> 5.02
(-58%)** and **18.58 -> 8.81 (-53%)**, while argmax *raises* it to 13.51 and 25.17. **Sigma alone
cannot see this**, which is why the metric is paired. The flat-ROI number measures what everyone
thinks it measures.

## 3. What was wrong

Five defects, ordered by how much they matter. **Defects 1, 2, 4 and 6 had already propagated into
`SYNTHESIS.md` facts 19-22 and have been corrected in both files.**

1. **HIGH — "residual structure ~10.9 DN" is about 2x low.** A 16x box downsample cannot see
   pixel-scale paper fibre; the 1:1 crop shows diagonal fibre plainly. True value **~20.4 DN**,
   about half the ROI's variance, obtained as ROI variance minus Immerkaer high-pass variance.
   Consequence: **the structure-corrected ratio is 1.48x at `2272,1344` and 1.49x at `2352,1408`**,
   not 1.29-1.31x — which is exactly the doc's own discarded "correction B".
2. **HIGH — the "1.13x hard floor" is unsound and must not be quoted.** It consumes the 10.9 DN
   figure from defect 1. With the correct 20.4 DN, `sqrt(2) * 20.4 = 28.9 DN` exceeds the observed
   excess of 21.3 DN and **the identical argument yields no floor at all** — it degenerates to
   1.0. This was the number the document offered as its challenge-proof fallback, and it was the
   weakest number in it. The conclusion is rescued instead by §2, which is stronger.
3. **MEDIUM — the model comparison compares two different physical quantities.** `19.267 DN` is a
   *temporal per-sample* sigma; `28.201 DN` is a *spatial* sd of noise **plus structure**. Matched
   properly they agree to **1.01x**: an Immerkaer 3x3-Laplacian high-pass of frame 11 in that ROI
   gives **19.473 DN** against the model's 19.267. Validated on synthetic data — given true
   sigma=19.267 plus 20.4 DN of smooth structure, the estimator recovers 19.288 while spatial sd
   rises to 28.103, matching the observed 28.201.
   **This is the same spatial-vs-temporal confusion that got a prior-corpus finding retracted**
   (§4 of `SYNTHESIS.md`, the 1.10x claim). It recurred inside this project, in a document written
   by an agent that had read the retraction. Rule 8 is not paranoia.
4. **MEDIUM — peak RSS does not reproduce.** Published 4.12-4.20 GB; measured **1.81-1.94 GB over
   9 runs** via `Start-Process -PassThru` polling `PeakWorkingSet64`, and still 1.93 GB at 44
   frames. The bounded-working-set *conclusion* holds with far more headroom than published. Likely
   cause: fewer than 11 chunks ever *fold* concurrently — the 11-in-flight peak occurs during the
   first decode wave, before workers touch their Selection/FocusField buffers — so 4.12 GB looks
   like a derived figure mislabelled as observed.
5. **MEDIUM — "the same binary at 200 frames still holds 11 in flight" is false.** 11 is an
   artefact of N=22. `workers = min(20, 32, N)`, so at N=44 the measured value is **15**, and at
   N=200 it is 20. The architectural claim — O(workers), never O(N), saturating at the budget — is
   correct; the sentence is not.
6. **LOW-MEDIUM — "focus + fold is 41% of decode."** The document's own numbers give
   175.1/249.9 = **70%**, and an independent run gives 196.8/267.6 = **73.5% of decode**, which is
   42% of total CPU. Someone conflated "% of decode" with "% of total". The literal sentence
   understates focus cost by ~1.8x.
7. **LOW — the 34.4% speckle figure is published without its null.** See §4.

## 4. Speckle needs its null

| | speckle |
| --- | --- |
| **real argmax** | **34.385%** (tool reports 34.381% including borders) |
| null: uniform random winners | **66.174%** |
| null: winners drawn i.i.d. from the *observed* winner histogram | **53.496%** |
| **regularised — argmax of a 17x17-smoothed focus field** | **0.868%** |

34.4% against an implied null of 0% sounds damning. Against the correct no-information null of
**53.5%** it says something more precise and more useful: the winner map carries *some* spatial
information, but is nowhere near a depth map.

One worry was that speckle is merely an artefact of featureless regions, where no frame is in focus
and any winner is as good as any other. **Partly refuted:** by 64x64-block contrast decile, speckle
is 38.6% in the flattest decile but still **21.7% in the busiest**, with 8 of 10 deciles at 33-39%.
It is not purely a flat-region effect. But the statistic still **cannot** separate "argmax elected
noise" from "no frame is in focus here, so the depth error is harmless". **It is a fair upper bound
on selector instability and nothing more,** and must be quoted that way.

## 5. What this decides

**The regularised row is the important one, and it was not in the plan.** `SYNTHESIS.md` §1.1(a)
argued — on review, not measurement — that the merge reference must come from a *regularised* focus
field rather than a raw per-band argmax. That argument is now measured:

- Regularising the focus field with a 17x17 smooth drops speckle **34.4% -> 0.868%** and noise
  **1.253x -> 1.075x**.
- **But 1.075x is still above 1.0.** Regularisation removes most of the defect and does not remove
  it. Only averaging goes below one frame (0.534x).

So the architecture is confirmed to need **both** halves, and neither alone suffices: a regularised
reference to stop the selector electing noise, *and* a noise-gated estimator that averages wherever
the frames agree within the noise floor. A better selector is not enough. That is the §1 thesis,
measured.

**Secondary, and a preview of M4:** the high-pass (structure-free) decomposition of the mean stack
gives **6.077 DN** against an ideal `sigma/sqrt(22)` = 4.11 DN, leaving ~4.5 DN unaccounted. That is
consistent with a modest static pattern and **inconsistent with a large fixed-pattern floor** —
which is the pillar M4 tests properly on dark frames. Treat it as a hint, not a result: it is one
scene at one ISO, and it is confounded with residual scene structure that averaging cannot remove.

## 6. Gaps — what is still not verified

- **No test covers `report_flat_roi`, `roi_green` or `speckle_fraction`.** The 52 tests are
  synthetic unit tests; **the headline number's own code path has no regression test.** It was
  independently re-derived from the raw files and agreed, but an untested path is an unverified
  path, and this is the number the architecture rests on.
- Peak RSS at 200 frames is unmeasured — verification reached 44. `WorkerPlan` *arithmetic* is
  unit-tested to 400 frames; runtime behaviour is not.
- RSS polling has a ~90 ms blind spot at process exit. A peak occurring solely in the final TIFF
  write could be missed, though that phase allocates only ~49 MB.
- Immerkaer is formally an *upper* bound on noise, so defect 3 proves the model does not
  *under*-predict rather than proving it exact. The mean stack's high-pass sigma corroborates it
  independently.
- The last ~2% of placebo A's gap (0.981x vs 1.0) could not be split into drift versus content.
  Immaterial at this magnitude.
- Argmax's excess is **spatially correlated, not white** — the ring-difference focus measure
  correlates winners over 3-7 px. So high-pass views *understate* argmax damage while raw spatial
  sd *overstates* the ratio through shared structure. **~1.48x is the honest figure** between them.
- **Single scene, single ISO, single camera, one 22-frame stack.** Everything here is n=1. The
  *mechanism* (selection coupled to per-pixel noise) is general and the N-sweep behaves as theory
  predicts; the specific numbers are not claimed to generalise.

## 7. How to quote this result

> A naive per-pixel argmax stack of 22 frames is **1.253x noisier than a single unstacked frame**
> on a flat region, **~1.48x** once shared scene structure is removed. On the same frames and the
> same region, a plain mean gives **0.534x** and a placebo selector with the identical winner
> histogram gives **0.981x** — so neither drift nor scene structure can produce the effect, and
> selection coupled to per-pixel noise is the cause.

**Do not quote the 1.13x floor, the 10.9 DN structure estimate, the 4.12 GB peak RSS, or "41% of
decode".** All four are wrong; the first two are wrong in the direction that loses an argument.
