# M46 — pre-registration: is there an admissible detail metric on this sensor?

**Committed before any M46 script is run.** Nothing in `src/` exists at the time
this file is committed. M41's verdict survived its own detail metric collapsing
only because its kill condition was committed first (`f809772`); this file is
that discipline repeated.

**Milestone:** M46. **Owns:** this file, `experiments/m46-detail-metric/**`,
`docs/research/M46-detail-metric-measured.md`.
**Assigned from:** question 118 (the two-capture FRC), question 119 (the paired
statistic), question 120 (the `sb = 0` censoring).
**Writes nothing** under `crates/**`, `experiments/m41-r3-kill/**`, or any
read-only corpus.

---

## 1. The problem, stated so that it can be wrong

`strehl` claims state-of-the-art **quality**. Fact 477 measured that every metric
in the project with power to detect a planted blur *also* fires at ≥ +0.94 on a
**flat** ROI that has no detail in it by construction. So each is a **blur
detector**, not a **resolution detector**, and none separates

- **the merge blurred the scene** — a real resolution loss, the thing that must
  be caught — from
- **the merge smoothed the noise** — the thing the project's whole thesis says
  estimation does and selection does not.

Fact 476 withdrew split-half FRC. Facts 467–469 disqualified raw spatial sd
(6.3× wrong on arm E). Fact 145 made `mean |∇|` one-sided. **There is currently
no admissible detail metric, and therefore no way to score the project's own
central claim.**

## 2. The acceptance bar — verbatim, and assigned

> A metric is **ADMISSIBLE** if, on the planted-blur ladder, it achieves
> **recovery ≥ +0.9 on detail AND ≤ +0.3 on flat.**

Recovery is fact 477's linear definition, unchanged, so the numbers are
comparable to the ones the bar was set from:

```
rec(sb) = ( m(0) - m(sb) ) / ( pred(0) - pred(sb) )
```

where `pred` is the metric evaluated on the **noiseless** source at the same
planted blur — the truth channel. `1.0` = recovers the planted loss exactly,
`0.0` = blind, `< 0` = wrong sign. A censored reading in either channel makes
`rec` **undefined**, not zero: bounds do not divide (fact 475).

`rec` is scored on the **real-detail** source for the first half of the bar and
on the **flat** source for the second half, both at the same planted `sb`, the
same noise model and the same split. The headline `sb` is **2.0 px**, matching
fact 477's headline so the two tables can be read against each other; the whole
ladder `sb ∈ {0, 0.5, 1, 2, 4}` is reported.

**No metric in the corpus has ever passed the second half.**

## 3. Rule 20 — the inputs that would make each outcome happen

Written before running. If an outcome has no input that could produce it, the
gate is a tautology and must be rebuilt.

| Outcome | An input that produces it |
|---|---|
| A metric is **ADMISSIBLE** | A statistic that reads only the *scene's* high-frequency content and is blind to noise power. **The `oracle_fsc` arm is exactly that** — Fourier shell correlation of the observation against the *known* latent — and it is included precisely so that "nothing passes" is falsifiable. |
| A metric **fails the detail half** | Any statistic whose truth channel is censored at `sb = 0` (fact 477's failure mode for the FRC crossing), or one attenuated by common-mode content (fact 478's `(1−ρ)` law). |
| A metric **fails the flat half** | Any statistic that measures total high-frequency power rather than *scene* high-frequency power. `hp_sd`, `p_ratio` and `mean |∇|` are pre-declared to fail here; if they pass, my model of them is wrong. |
| **The bar itself is broken** | `oracle_fsc` failing the flat half. An oracle with the true latent in hand cannot be accused of confusing blur with smoothing, so if even it reads > +0.3 on flat, the *bar* is unachievable and must be rebuilt rather than the metrics discarded. **This is the pre-declared failure mode of the gate, and it is checked first.** |

## 4. What will be run

### 4.1 The two-capture FRC (question 118, assigned)

`112MSDCF` / `113MSDCF` are the corpus's only same-subject independent pair
(fact 49: preview NCC **+0.9961**; fact 52: two independent captures of one
static subject). Split-half FRC on halves of one capture shares the scene *and*
the fixed pattern; two captures share the fixed pattern only, so per fact 478's
`(1 − ρ)` law the recovery should rise from the measured 0.02–0.37 toward 1.0,
and **the residual shortfall measures the FPN fraction.**

**The exposure difference is handled explicitly and its ordering is stated
before it is measured.** Fact 52 records the pair as "a full stop apart". Whether
that stop is *gain* or *time* changes the noise algebra completely and it will be
read from EXIF, not assumed:

- If it is **ISO** (gain), the electron counts match and only the DN scale and
  the read-noise-in-DN differ.
- If it is **exposure time**, the longer capture collects proportionally more
  photons, so after photometric rescaling by `c` it is **quieter**, not equal.

In both cases the ordering is the same and is fixed now: **the photon-transfer
noise model is evaluated on each capture's own unscaled DN, and the variance is
then carried through the scale as `c²·var`.** Applying the model *after*
rescaling would attribute the scaled signal level's shot noise to a frame that
did not collect it. Getting this backwards manufactures or destroys correlation,
which is the entire measurement.

The photometric scale is measured from matched ROI means and **checked against
the EXIF prediction**; a disagreement worse than 5 % is reported as a failure of
this step, not absorbed.

**Misregistration is the other way to fake this result.** Two independent
captures are not co-registered, and sub-pixel shift destroys high-frequency
correlation, which would look exactly like "the metric has no power". Integer +
sub-pixel phase-correlation alignment is applied, the measured shift is reported,
and a **deliberate-misalignment control** is run to show what the metric does
when alignment is wrong.

**Depth-range matching.** Fact 50 measured that `113` covers only `112`'s frames
**5.5 → 66.6 of 0 → 78**; `112` runs 16 frames further. The two merges are
therefore built over the *matched* subrange so that a depth difference cannot be
read as a resolution difference. Frames outside the overlap are dropped from
`112`, not from `113`.

### 4.2 The planted-blur ladder, with two plant models — both declared now

Fact 477's ladder is reused unchanged (Fourier Gaussian of known sd, exact MTF
`exp(−2π²sb²f²)`, no kernel truncation) on the same three sources: **flat**,
**real detail**, **synthetic broadband**. Two plant models are run, and which
one is used matters more than any metric here:

- **PM-1, post-capture blur.** The blur is applied to the *captured* frame, so
  the fixed pattern is blurred along with the scene. This is what a **merge**
  actually does — a merge low-passes everything it touches — and it is the model
  fact 477 used.
- **PM-2, pre-capture blur.** The blur is applied to the *latent scene* only;
  fixed pattern and shot/read noise are added afterwards, unblurred. This is the
  **optical** model and the one that asks "is this a *resolution* metric?".

**Pre-declared prediction, which is the whole reason both are run:** on a flat
ROI under PM-1, "blurred the scene" and "smoothed the noise" are *the same
operation*, so no statistic can separate them there and every metric will score
near +1.0 on flat. Under PM-2 the flat source's truth channel barely moves, so
recovery on flat should collapse toward 0 or become undefined. **If PM-2 does not
change the flat scores, this prediction is wrong and the report says so.**

### 4.3 The paired statistic (question 119, assigned)

Candidate: the detail reading of a merge **conditioned on that same merge's flat
reading** — `paired = m(detail) − m(flat)`, and its ratio form
`m(detail)/m(flat)`. The claim to be tested is that noise-smoothing moves both
readings together and cancels, while scene-blur moves only the detail reading.

**This cannot be asserted; it needs a plant where only one effect is present**,
so two further plants are registered:

- **BLUR-ONLY** — latent attenuated by a known MTF, noise realisation and σ
  unchanged.
- **SMOOTH-ONLY** — latent untouched, noise σ reduced by a known factor
  (the `1/√n` a merge would buy), nothing else changed.

A **resolution** metric fires on BLUR-ONLY and not on SMOOTH-ONLY. A **blur
detector** fires on both. This is reported as a 2×2, per metric, and the
separation is *measured*, not argued.

### 4.4 The `sb = 0` censoring (question 120, assigned)

Fact 477 measured the `sb = 0` reference censored in **6 of 6** source × SNR
cells, in the measured channel *and* in the analytic `SNR/(1+SNR)` channel.
Analytically, censored at `sb = 0` means the per-ring SNR never falls below
**1/6** anywhere up to Nyquist. Two candidate causes, and a test that separates
them:

- **Real content to Nyquist** — aliasing, PRNU, hard edges.
- **Spectral leakage** — the Hann window's sidelobes spreading enormous
  low-frequency power into high rings, creating a floor that is not in the
  signal at all.

**The decisive input is a source that is band-limited by construction**: a latent
with *exactly zero* power above 0.20 cyc/px. Any ring power measured at 0.45
cyc/px on that source is leakage, 100 %, with no modelling assumption. The
window ladder (Hann → Blackman → Blackman-Harris → high-pass pre-filter) is then
priced against that floor.

If the cause is leakage and a better window removes it, the M41 FRC withdrawal
may be partly reversible, and that must be known **before** FRC is discarded
permanently.

## 5. What is held constant

- Green quad plane only (`0.5·(G1 + G2) − 512`), rule 7: `raw_image_visible`.
- Gain `g = ISO/436.8`, `rn_e = 1.47` if ISO ≥ 400 else `4.20` — the same
  calibration M41 used, so numbers are comparable across milestones.
- 512×512 ROIs, `PAD = 32`, selected by the `a1b_rois.py` window-mean procedure
  (**not** the centre-pixel procedure `a1_rois.py` got wrong), applied unchanged
  to the new stacks. Coordinates are an output, not an input.
- `F_SIG = 0.2762` cyc/px (fact 27).
- `nbin = 64`, `thr = 1/7`, two-consecutive-ring crossing rule — M41's, so the
  comparison is like-for-like. **Every crossing is reported with its censoring
  flag** (fact 475); censored values are never divided.
- The merge is M41's arm A (regularised winner field + noise-gated average), the
  shipped-equivalent proxy verified at 1.0101× the Rust `FOCUS_NOISE_SD`
  (fact 460). It is *imported* from the frozen `m41lib.py`, never edited.

## 6. Deviations from the ideal experiment, declared in advance

- **D1.** The pair is not a controlled replicate: `112` has 79 frames at 1/60 and
  `113` has 63 at a different shutter, 76 s later. Exposure, depth range and
  frame count all differ and all are handled explicitly above; none is randomised.
- **D2.** One subject. A metric admissible on this subject is not thereby
  admissible on the corpus, and the report will say so.
- **D3.** The fixed pattern is common to both captures because it is the same
  body. **This is not a nuisance to be removed — it is the quantity being
  measured** (the residual shortfall in the recovery ratio). No dark-frame
  subtraction is applied; `D:\macro-dark-frames` is read-only and is not used.
- **D4.** `oracle_fsc` is not a shippable metric — it needs the latent. It is a
  positive control on the *bar*, and it is labelled as such everywhere.
- **D5.** Recovery is a two-point statistic (`sb = 0` against `sb`). The whole
  ladder is printed so a verifier can re-choose a slope-based definition.

## 7. What "no admissible metric" would mean, written before it is possible

If every candidate — including the two-capture FRC — fails the bar while
`oracle_fsc` passes it, then the finding is **measured and publishable**: on this
sensor, with this corpus, there is no ground-truth-free statistic that separates
scene blur from noise smoothing. That changes what `strehl` may **claim**, not
what it computes. The report will state it as plainly as M44 stated the `0.4961`
diagnosis, and will list what would be needed to lift it.

If `oracle_fsc` also fails the flat half, the bar is unachievable and the report
will say the **gate** is broken, not the metrics.
