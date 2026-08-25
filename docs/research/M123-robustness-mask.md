# M123 — the outlier mask meets real captures, and does not survive them

Instrument: `crates/strehl-cli/examples/m123-outlier-real.rs`,
`crates/strehl-cli/examples/m123-trap-decompose.rs`.
Pre-registration: `experiments/M123-robustness-mask/PREREGISTRATION.md`, written
before any result was looked at.
Measured against `crates/strehl-core/src/outlier.rs` unchanged, at
`outlier.rs` sha256 `66CDB1B5A40085E5682F58F2A1BAABE7E208BCC886F77758E9395A86138FC32E`
(identical in the shared tree and in the pinned worktree used for the build).

**Nothing was wired into the merge. The measurement says it should not be.**

---

## 0. What was already known, and what the brief did not know

AGENTS rule 40 requires searching `docs/research/` for the question before
commissioning. The brief named no prior report. **Four exist**, and three of
them already used real captures:

| report | data | verdict |
| --- | --- | --- |
| `M28-robustness-mask-measured.md` | real | detector separable against the *adjacent* frame; no merge effect measured; "NOT INDEPENDENTLY VERIFIED" |
| `M60-robustness-mask-at-merge-time.md` | real | "**I did not build the mask**"; "a mask keyed on chi2 would be a sharpness detector wearing a robustness label" |
| `M89-robustness-mask.md` | real, 23 stacks | "The metric works and should be adopted. **The mask, as specified, should not ship**" |
| `M97r-outlier-mask.md` | **synthetic only** | `LowFreq` fails; `ShiftFree` survives every control |

The brief's discriminating question — *does `LowFreq` fire on motion while
staying quiet on defocus?* — **was already closed, in the tree, with a
derivation of why the answer must be no.** `outlier.rs` marks that arm a
**MEASURED FAILURE** in its own enum documentation and carries the regression
test `low_pass_filtering_does_not_discriminate_defocus_it_amplifies_it`. M97r W3
derives the reason: box-averaging divides the noise variance by `m` while an
extended defocus residual survives, and the statistic is their ratio
(`C*r_d/sigma`), **independent of the filter radius**. No radius helps.

So M123 did not re-ask it. It ran `LowFreq` only as an inertness control, and
asked the question the module names against its own constant instead.

**Two stale statements found in passing:**

1. **`outlier.rs`'s module header is stale against its own enum.** Lines 20–33
   say the module "implements two" discriminators and describe `LowFreq` as the
   arm where defocus "largely cancels". Forty lines below, the enum documents
   **four** and says `LowFreq` is a measured failure. The brief inherited the
   header's version. Not fixed here — `outlier.rs` is not this milestone's to
   edit — but it is what a reader hits first.
2. M116's note that the mask is "unmeasurable — no flag exists at the SHA" is
   true about the CLI and irrelevant to the question: the module is directly
   callable from an example, which is how M97r and this milestone both drove it.

---

## 1. The question, and why real data is not merely a nicer plant

> **Does `ShiftFree` — the only arm surviving M97r's synthetic controls —
> separate real subject motion from real defocus, and does its
> `DEFAULT_MIN_SHIFT_PX = 0.35` bar hold out of sample?**

M97r §6 states its own gate configuration is in-sample: "The design changed four
times in response to measurement … and the 0.35 px bar and the 3.0 margin were
chosen **against the very cases used to report them**." `DEFAULT_MIN_SHIFT_PX`'s
doc comment ends: "**It has not yet been measured on real frames.**" The corpus
is the held-out set.

**AGENTS rule 34 is why this is the highest-value measurement available.** "A
plant that supplies its own noise constant cannot detect that constant being
wrong." M97r drew its noise from the model and normalised by the same model, so
every one of its numbers is scale-invariant in the gain and **could not have
detected a miscalibration of any size**. Only photons can falsify the
calibration.

The discriminating pair is real and physical:

- **TRAP** — `109MSDCF` adjacent frames. Tripod-mounted, focus changes, nothing
  moves. The quietest stack in the corpus.
- **PLANT** — `coffee-bubbles` adjacent frames. Focus **constant** at 0.2841 m
  throughout (`captures-needed.md` line 1264) while bubbles genuinely drift.
  Real subject motion with the defocus confound *physically absent* — the
  control no synthetic scene can supply.

---

## 2. Results

`crop 1024x1024` green luma, 1024 tiles of 32 px, `k = 6`, `blur_radius = 6`,
8 adjacent pairs per stack. Disagreement bar `1 + k*sqrt(2/N) = 1.2652`;
displacement bar `1 + k = 7.0` on 2 dof; `min_shift_px = 0.35`.

| case | arm | mean chi2 | sd | p50 | p99.9 | fire% | **gated%** | mean\|s\| | p99.9\|s\| |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| flat-null | Raw | **1.038** | **0.1247** | 0.998 | 1.415 | 7.19% | — | — | — |
| flat-null | ShiftFree | 22.066 | 30.27 | 10.82 | 226.28 | 2.44% | **0.00%** | 2.6646 | 20.24 |
| dark-null | Raw | 0.440 | — | 0.438 | 0.580 | 0.00% | — | — | — |
| defocus **TRAP** | Raw | 1.780 | — | 1.055 | 16.47 | 29.60% | — | — | — |
| defocus **TRAP** | LowFreq | 41.943 | — | 8.069 | 1437.96 | 61.80% | — | — | — |
| defocus **TRAP** | **ShiftFree** | 283.36 | — | 24.06 | 7668.74 | 69.42% | **29.55%** | **0.7260** | 16.25 |
| motion **PLANT** | **ShiftFree** | 3251.39 | — | 314.20 | 70413.23 | 91.94% | **62.78%** | 0.5328 | 7.12 |
| foam **PLANT** | **ShiftFree** | 1708.04 | — | 120.43 | 139878.03 | 77.86% | **6.87%** | 4.8378 | 161.88 |

Positive control — a planted translation on a **real** `109MSDCF` defocus pair:

| planted px | gated% | mean \|s\| |
| ---: | ---: | ---: |
| **0.00** | **24.51%** | 0.9521 |
| 0.15 | 23.44% | 0.9118 |
| 0.35 | 23.54% | 1.2153 |
| 0.50 | 24.71% | 1.6603 |
| 1.00 | 34.77% | 1.9326 |
| 2.00 | 34.57% | 3.6231 |

Displacement-field decomposition (`m123-trap-decompose`), 6 pairs, mean:

| stack | usable tiles | coherent scale | rms \|s\| | rms residual after global fit | explained |
| --- | ---: | ---: | ---: | ---: | ---: |
| `109MSDCF` TRAP | 357–593 | **+780…937 ppm** | 0.5496 | **0.3370** | 62.4% |
| `coffee-bubbles` PLANT | 761–1009 | +636…734 ppm | 0.5263 | **0.2360** | 79.9% |
| `foam` PLANT | **26–91** | erratic | 4.6529 | 3.5401 | 42.1% |

---

## 3. Facts

**M1 — MEASURED. The noise model's absolute calibration is correct on real
photons, and this is the first time that has been checked for this module.**
Two flat frames at 269 DN — same scene, same focus, independent real noise —
give `Raw` mean chi2 **1.038**, median **0.998**. Rule 34 says no plant could
have established this. It is the one unambiguously good result in the milestone,
and it means the `g*S` term is right to about 4% at working signal levels.

**M2 — RETRACTED BY MY OWN FOLLOW-UP. I published this as "the most important
finding here". It was an artefact of my pooling, and the module's `N_eff` is
correct.** The original claim: the observed across-tile sd of chi2 on the
pure-noise flat pair is **0.1247** against a predicted `sqrt(2/1024) = 0.0442`,
ratio **2.822x**, therefore `N_eff` overstated 7.96x, therefore
`threshold_k = 6.0` is really 2.13 true sigma, therefore a **7.19%**
false-positive rate on pure sensor noise.

`m123-null-radius` re-measured the same quantity **per pair** instead of pooling
eight pairs into one distribution:

| pair | mean chi2 | within-pair sd | predicted | ratio |
|---:|---:|---:|---:|---:|
| 0 | 0.9427 | 0.0424 | 0.0442 | **0.96x** |
| 1 | 0.9406 | 0.0415 | 0.0442 | **0.94x** |
| 2 | 0.9410 | 0.0415 | 0.0442 | **0.94x** |
| 3 | 0.9646 | 0.0449 | 0.0442 | **1.02x** |
| 4 | 1.0043 | 0.0453 | 0.0442 | **1.02x** |
| 5 | 1.0819 | 0.0475 | 0.0442 | 1.07x |
| 6 | 1.1559 | 0.0524 | 0.0442 | 1.19x |
| 7 | 1.2758 | 0.0566 | 0.0442 | 1.28x |
| **pooled** | 1.0383 | **0.1247** | 0.0442 | **2.82x** |
| between-pair sd of the means | — | **0.1236** | — | 2.80x |

The between-pair spread of the *means* is **0.1236**, which accounts for
essentially the whole pooled **0.1247**. The within-pair spread matches the
prediction to within 6% on the first five pairs. The per-pair mean drifts
monotonically **0.9427 → 1.2758** across the burst, and each pair's sd drifts
with its mean exactly as a chi-square must.

So: **`sqrt(2/N_eff)` is right, `N_eff` is not overstated, `threshold_k = 6.0`
really is about 6 sigma, and the false-positive rate on pure sensor noise is
0.00%, not 7.19%.** I pooled eight pairs whose means drift by 35% and attributed
the resulting spread to the sensor. The correct reading is M11.

*Nothing else in this report depends on M2.* The verdict rests on M4, M5, M7,
M8 and M12, all of which are scene measurements unaffected by this. But M2 was
stated as the headline, it was wrong, and a reader who acted on it would have
loosened a threshold that was already correctly calibrated.

**M11 — MEASURED, and it replaces M2 as the calibration finding. The low-pass
arm's error is not mis-derived variance, it is a coherent nuisance amplified in
exact proportion to the filter footprint: `chi2(m) = 1 + 0.0076*m`.** The module
divides both the predicted variance and `N_eff` by `m = (2r+1)^2`, on the
reasoning that box-averaging `m` *independent* samples reduces variance by `m`.
That predicts **chi2 = 1 at every radius**. Swept on the pure-noise flat pair:

| r | m | mean chi2 | `(chi2-1)/m` | fire% |
|---:|---:|---:|---:|---:|
| 0 (`Raw`) | 1 | **0.947** | — | 0.00% |
| 1 | 9 | 1.050 | 0.0056 | 0.00% |
| 2 | 25 | 1.180 | 0.0072 | 0.46% |
| 3 | 49 | 1.367 | 0.0075 | 3.54% |
| 4 | 81 | 1.615 | 0.0076 | 8.59% |
| **6 (shipped)** | **169** | **2.294** | **0.0077** | **18.58%** |
| 12 | 625 | 5.778 | 0.0076 | 25.22% |

`(chi2-1)/m` is constant at **0.0076 ± 3% across a 25x range in `m`**. The fit
predicts 2.28 at the shipped `r=6` against 2.294 observed, and 5.75 at `r=12`
against 5.778 — better than 1%.

The mechanism the law forces: box-averaging reduces the **white** noise variance
by exactly `m` — that is why the intercept is exactly 1 and why `Raw` at `m=1`
reads 0.947. But a real frame difference also carries a **spatially coherent**
component (illumination drift, black-level drift, the magnification breathing of
M6), and averaging does not attenuate that **at all**. The module divides the
prediction by `m`; the coherent part of the observation does not shrink; chi2
inflates linearly in `m`. **At the shipped `blur_radius = 6` the amplification of
coherent nuisance is 169x.**

This is why no choice of `threshold_k` rescues `LowFreq`. The amplification is
structural, and it is caused by the filter doing precisely its intended job: the
low-pass is there to keep the low frequencies where *translation* lives, and
illumination drift and magnification breathing live in the same passband.
**Signal and nuisance are not separable by this filter because they are the same
frequencies.** M97r's fact W3 derived this; this is the same result measured on
real photons, and it is now a quantitative law rather than a direction.

Note the corollary for the module's own documented failure mode. `outlier.rs`
warns that *forgetting* the `N_eff` division makes the mask "silently inert"
(chi2 reads `1/m`). Real data fails in the **opposite** direction: chi2 reads
`1 + 0.0076m`. The planted control guards the harmless failure and cannot see
the real one, because a synthetic scene drawn from an `Rng` satisfies the
independence assumption by construction and reads 1.0 at every radius no matter
how wrong that assumption is about sensors (AGENTS rule 34).

**M3 — RETRACTED, and the retraction is the point. The dark-frame null reads
0.440, and it is an artefact of my own instrument, not evidence about the noise
model.** `green_luma` clamps at zero (`plane.rs:90`,
`(sample - black).max(0.0)`). On a dark frame the true signal is zero and read
noise straddles black, so roughly half of every sample is clipped and the
variance is destroyed. I had written "the read-noise term is over-stated by
2.3x" before checking the code path. **A null taken below black level is not an
instrument.** Use flats, not darks, to calibrate this statistic.

**M4 — MEASURED. `ShiftFree` fires on 29.55% of tiles of a stationary subject.
The synthetic configuration does not transfer.** On `109MSDCF` — tripod, focus
sweep, nothing moving — the shipping conjunction gate fires on **29.55%** of
tiles. M97r measured **0.0%** on its synthetic trap. The brief's own destruction
threshold was "30% of tiles of a still subject will destroy renders". It is at
29.55%.

The mechanism is visible in one number: mean apparent displacement on the trap
is **0.7260 px** (0.95 px on the single pair used for the plant), against a bar
of **0.35 px**. M97r set that bar because its synthetic scene produced a
**0.1027 px** worst-case defocus displacement. Real captures produce **7–9x**
that, as a *mean*. **The bar is underwater.**

This is AGENTS rule 13 exactly — *check the plant can express the failure first*.
A single disc plus a two-axis ripple cannot express the curvature spectrum of a
real macro subject, and M97r's own W5 named curvature as the mechanism. The
mechanism was identified correctly and its magnitude was under-measured by an
order of magnitude, because the plant had almost no curvature in it.

**M5 — MEASURED. The separation is 2.12x against a pre-registered 10x, and the
underlying displacement does not separate at all.** Gated fire rate is 62.78%
on the motion plant against 29.55% on the trap. But the *displacements* are
`rms|s|` **0.5496 px on the still subject** and **0.5263 px on the moving
one** — a ratio of **0.96x**. The still subject shows marginally *more* apparent
displacement than the moving one.

So the 2.12x that does appear in the gated rate is not coming from motion. It is
coming from `coffee-bubbles` having more tiles that pass the significance and
resolution gates, i.e. from contrast and texture. **This is M60's and M89's
finding arriving again by a different route: "a mask keyed on chi2 is
substantially a sharpness detector wearing a robustness label."** Three
milestones, three statistics, same result.

**M6 — MEASURED. The obvious fix is not merely weak, it is inverted.** The trap
carries a large coherent global scale term — **+780 to +937 ppm per adjacent
frame pair**, consistent and same-signed across all six pairs. That is real
magnification drift, and `outlier.rs` has no alignment stage in front of it, so
the natural proposal is "put the mask after alignment and test the residual".

Measured, that makes it worse. After fitting and removing a global similarity
transform:

- trap residual **0.3370 px**
- plant residual **0.2360 px**

**The still subject's post-alignment residual is 1.43x larger than the moving
subject's.** A mask keyed on residual displacement would fire *more* on the
tripod stack than on the bubbles. The control is what made this readable: a low
explained fraction on the trap alone would have been ambiguous between "no
breathing" and "the fit does not work" (rule 20).

**M7 — MEASURED, and it is the worst result in the milestone. On the archetype
stack the mask is anti-correlated with the thing it exists to catch.** `foam` is
the stack the mask was designed for — M60 calls it "the archetype the mask was
designed for" and 4.78% of its output pixels already come from a frame that
moved. `ShiftFree` fires on **6.87%** of `foam`, against **29.55%** on the
static trap. **It fires 4.3x less on the moving subject than on the still one.**

The cause is structural, not a tuning error. Only **26 to 91** of 1024 tiles are
usable on `foam`, against 357–1009 on the other stacks: **91%+ abstain.**
Lucas-Kanade is a small-displacement linearisation. Where motion is large, the
linearisation fails, `sigma_px` inflates, and the resolution gate
(`sigma_px * 3.0 <= 0.35`) vetoes the tile. **The gate abstains hardest exactly
where the motion is biggest.** The abstention logic is individually correct —
"no information is not the same as agreement" — and its aggregate effect is a
detector that goes blind in proportion to the signal.

**M8 — MEASURED. The positive control does not respond across the range that
decides the bar.** A planted translation on a real defocus pair gives gated
rates of **24.51 / 23.44 / 23.54 / 24.71%** for planted **0.00 / 0.15 / 0.35 /
0.50 px**. That is flat to within noise while the planted displacement goes from
nothing to the bar and past it. It moves only at 1.0 px (34.77%), a 1.4x change.
**At a planted 0.00 px the gate already fires on 24.51% of tiles**, so there is
no null to rise from. `mean |s|` does respond monotonically (0.95 → 3.62 px), so
the *estimator* carries signal — it is sitting on a ~0.95 px pedestal of
defocus- and drift-induced displacement that swamps the planted motion.

**M9 — MEASURED. `LowFreq` fails on real data exactly as derived.** On the trap
it fires on **61.80%** of tiles against `Raw`'s 29.60%, at mean chi2 **41.94**
against `Raw`'s **1.78** — a **23.6x amplification** of the very nuisance it was
supposed to cancel. M97r predicted this analytically from synthetic data; it
reproduces on real captures at the predicted sign and rough magnitude. The
brief's stated question is answered, and answered the same way it was already
answered.

**M10 — MEASURED. The inertness control passes, so the nulls above are real.**
`Raw` fires on 29.60% of the trap and 84.11% of the plant, so the harness
demonstrably sees disagreement in these inputs. A `ShiftFree` null would have
been meaningless without it. `ShiftFree`'s gated rate on the flat-field null is
**0.00%**, which is the one place it behaves.

**M12 — MEASURED. Reconciling against fact 1189's 4.78%: the numbers agree and
the agreement is meaningless, because the rate the mask reports is set by its
own abstention rather than by motion.** Fact 1189 prices `foam`'s motion
contamination at **4.78% of output pixels**. `ShiftFree` gates **4.35%** of
`foam`'s tiles over four adjacent pairs (6.87% over eight). Same order — but the
brief asked for the reconciliation shown rather than rounded off, and shown, it
collapses.

Decomposing the gated rate into the two factors that produce it, over three
stacks with known ground truth:

| stack | resolvable% | gated% | fired / resolvable | ground truth |
|---|---:|---:|---:|---|
| `109MSDCF` | 38.82% | **22.73%** | 58.6% | **STILL** (tripod) |
| `coffee-bubbles` | 87.04% | 59.50% | 68.4% | MOVING |
| `foam` | **4.39%** | **4.35%** | **98.9%** | MOVING, 4.78% |

Three things, in order of severity.

1. **The mask ranks the still stack 5.2x above the motion archetype.** A
   tripod-mounted subject that did not move reports 22.73%; the stack the corpus
   names as *the* motion case reports 4.35%. Any consumer reading these as
   contamination estimates gets the ordering exactly backwards.
2. **On `foam`, gated% (4.35%) is within 1% of resolvable% (4.39%)** because the
   mask fires on **98.9%** of everything it can resolve. The reported figure is
   therefore essentially *"4.39% of tiles were resolvable"*. It is a statement
   about Lucas-Kanade's linearisation, not about the subject. Its proximity to
   4.78% is **coincidence** — and that is provable from the same table, because
   the identical instrument reports 22.73% on a stack with no motion at all.
3. **The response to displacement is non-monotone, so the detector is blind at
   both ends.** Small motion falls under `DEFAULT_MIN_SHIFT_PX = 0.35` and is
   discarded; large motion breaks the small-displacement linearisation, inflates
   `sigma_px`, and is vetoed by `sigma_px * RESOLUTION_MARGIN <= 0.35`. Only a
   middle band is visible. `foam`'s mean `|s|` is **4.84 px** — far outside that
   band — which is why the archetype abstains on 95.6% of tiles. **The gate
   abstains hardest exactly where the motion is worst.**

So the honest reconciliation is: the two figures are reconcilable in magnitude
and *not* reconcilable in mechanism. 4.78% is a property of `foam`; 4.35% is a
property of the gate.

**M13 — DERIVED from fact 1189 and confirmed by M12. The mask is on the
averaging side of a 100%/6% split, so its ceiling is 6% of the defect, and the
ceiling is not what is binding.** Fact 1189 prices catching this defect at the
**election** as removing **100%** of the contaminated pixels and catching it in
the **averaging** as recovering **6%**; fact 1554 states that `outlier.rs`
"addresses **6.0%** of this defect even once wired", and fact 1555 prices
election-time `robust.rs` at **~16.7x** the average-time mask. `outlier.rs` is
unambiguously the average-time instrument.

The reason is the mechanism in the brief: a displaced edge is **sharper** than a
correctly-focused stationary one, so motion does not merely survive the
sharpness election, it **wins** it. By the time the averaging runs, the
contaminated frame has already been elected, and a weight applied there can only
recover the 6% residue.

But M12 shows the ceiling is not the binding constraint. A 6% ceiling on a
detector that reports 22.73% on a still subject and ranks it above the motion
archetype is not a small win; it is a wrong-signed one. Fact 1189 already
measured the average-side specification at **-5.21%** against a registered
**>= +10%**. My independent measurement of the detector explains *why* that
happened, and fact 1189's ruling — **"Do not re-specify the average-side mask;
gate the election"** — stands unchallenged by anything in this milestone.

---

## 3a. The brief's phase-1 question, answered directly

> *Does `LowFreq` fire on genuine subject motion while staying quiet on focus
> difference alone?*

**No, and it fails in the more damaging of the two possible directions: it is
loudest on exactly the nuisance it was built to cancel.** On the `109MSDCF`
defocus trap — a tripod-mounted still subject where adjacent frames differ *only*
in focus —

| arm | mean chi2 | fire% |
|---|---:|---:|
| `Raw` (the control that must fire) | 1.78 | 29.60% |
| `LowFreq` (the arm that should be quiet) | **41.94** | **61.80%** |

`LowFreq` fires **2.1x more often** than the naive port it was designed to
improve on, at a mean chi2 **23.6x higher**. The inertness control passes — `Raw`
fires on the same input, so the harness is live and a `LowFreq` null would have
been readable had one occurred.

The cause is M11, and it is not a tuning error. On a **flat-field pair** — no
scene, no focus difference, no motion, nothing but sensor noise — `LowFreq` still
fires on **59.29%** of tiles at mean chi2 **17.5**, where the module predicts
1.0. An arm with a 59% false-positive floor on pure noise cannot have its 97.55%
on `foam` read as motion detection. `chi2(m) = 1 + 0.0076m` says the low-pass
amplifies coherent nuisance by `m`, which is **169x** at the shipped radius, and
translation, illumination drift and magnification breathing all share that
passband. The filter cannot separate them because they are the same frequencies.

This reproduces M97r's fact W2 (`LowFreq` fires on 100.0% of the trap, an order
of magnitude above `Raw`) on real captures rather than a plant, and supplies the
quantitative law behind M97r's fact W3, which had derived the direction only.

---

## 4. Pre-registered criteria: 3 of 6 FAIL

| # | criterion | bar | measured | verdict |
| --- | --- | --- | --- | --- |
| 1 | null mean chi2 | [0.90, 1.10] | 1.038 (flats) | **PASS** |
| 1b | *(not pre-registered)* null sd | `sqrt(2/N)` = 0.0442 | 0.0415–0.0566 per pair | **PASS** — see M2 retraction |
| 2 | trap gated FPR | <= 1.0% (fail > 5%) | **29.55%** | **FAIL** |
| 3 | plant gated rate | >= 20% | 62.78% | **PASS** |
| 4 | separation plant/trap | >= 10x | **2.12x** | **FAIL** |
| 5 | inertness (`Raw` fires) | must fire | 29.60% | **PASS** |
| 6 | plant proportional, no fire at 0 | fire at d>=0.5, not at 0 | **24.51% at d=0, flat to 0.5** | **FAIL** |

**This count was 4 of 6 in the first version of this report and is now 3 of 6**,
because criterion 1b flipped from FAIL to PASS on re-measurement (see the M2
retraction). Recorded explicitly so the change is not mistaken for a
transcription error.

The verdict is unchanged. 1b was never pre-registered as a bar, and the three
remaining failures are the three that decide the question: the mask fires on
**29.55%** of a still subject against a registered <= 1%, separates motion from
defocus by **2.12x** against a registered >= 10x, and does not respond
proportionally to a planted displacement. A mask can survive a mis-stated null;
it cannot survive failing to tell motion from focus.

Criterion 1b was not pre-registered as a threshold — the pre-registration asked
only that the null "match the predicted one", per the brief's instruction to
check the null's spread as well as its mean. It is recorded as a fail because
the prediction is explicit in the module and the measurement contradicts it.

---

## 5. Verdict

**Do not ship the mask, and do not wire it.** Phase 2 was not reached: it was
conditional on phase 1, and phase 1 fails three of six pre-registered criteria —
including both criteria that test the mask's actual purpose.

At the shipped configuration on real captures the mask
- fires on **29.55%** of a stationary subject,
- fires **4.3x less** on the archetype moving subject than on that stationary
  one, and **ranks the still tripod stack 5.2x above the motion archetype**
  (M12) — the ordering is wrong-signed, not merely weak,
- separates motion from defocus by **2.12x** where the underlying displacement
  separates by **0.96x**, i.e. not at all, and
- does not respond to a planted displacement anywhere below 1.0 px.

And even a mask that did all of this correctly would be capped. `outlier.rs`
acts at the **averaging**, where fact 1189 prices the recoverable share of this
defect at **6%** against **100%** at the election, because motion wins the
sharpness election before the averaging is ever consulted (M13). The 6% ceiling
is real but it is not the binding constraint — the detector is. Fact 1189's
ruling stands: **do not re-specify the average-side mask; gate the election.**

**This is the fourth milestone to decline to ship this mask** (M60, M89, M97r's
own §6 caveat, now M123), and the second to find that what looks like
motion discrimination is substantially texture discrimination.

**What would have to change before it is worth revisiting**, in dependency
order:

1. **Fix `N_eff` first (M2).** Until the null's spread is modelled, no threshold
   in this module means what it says, and every downstream tuning decision is
   made against a bar that is 2.8x tighter than believed. This is cheap: measure
   the correlation length on a flat pair and divide. It also affects any future
   statistic of this shape, not just this mask.
2. **Re-measure the defocus displacement pedestal on real scenes and set the bar
   from that**, not from a synthetic disc. Measured here at 0.73–0.95 px mean
   where the bar is 0.35 px.
3. **Do not use Lucas-Kanade for the arm (M7).** A small-displacement
   linearisation cannot be the detector for large displacements; it abstains
   where it is needed. This is structural and no threshold fixes it.
4. **Do not expect alignment to rescue it (M6).** Measured, the post-alignment
   residual is *inverted* between plant and trap.

M97r's third, unbuilt discriminator — analysis-by-synthesis against the running
estimate re-blurred to the frame's own focus — remains the only proposal where
focus difference is absent from the data term by construction. Nothing here
speaks to it. Everything here speaks against the two that were built.

---

## 6. What this milestone does NOT claim

- **No merge was run and no render was produced.** Every number is a detector
  measurement. `DEFAULT_GATE = 4.0` is not implicated because no gate was
  exercised; no gate-0 negative control is quoted as a result.
- **`crates/strehl-core/src/merge.rs` was never touched.** It carried
  uncommitted modifications from another agent throughout, and left the shared
  tree non-compiling for part of the session (18 errors, all in `merge.rs`).
  The build was done in a pinned worktree at `C:\dev\strehl-out\M123-tree`,
  detached at `1482533`, with `outlier.rs` verified byte-identical to the
  shared tree by SHA-256.
- **`outlier.rs` was not modified.** No behaviour changed; the module is
  measured exactly as M97r left it.
- **Only the centre 1024x1024 of the green-luma plane was used**, on 6–8
  adjacent pairs per stack. Wider crops, other stacks and non-adjacent baselines
  are unmeasured. `109MSDCF` is one stack; the corpus has 24.
- **The flat-field null carries a 269.0 vs 273.6 DN level difference** between
  the two frames. That contamination inflates chi2, so it makes M1's calibration
  pass *conservative* and would not mask a spread defect, but a purpose-shot
  static repeat burst — `captures-needed.md` §12 already asks for one — would be
  a cleaner null than a flat pair.
- **`shifted()` uses bilinear interpolation**, which mildly low-passes the
  planted frame and biases the recovered magnitude downward. Conservative for a
  positive control; it cannot manufacture M8's flat response.
- **I did not verify this.** An independent agent should, and the two cheapest
  places to attack it are M2 (recompute the null spread with a different tile
  size and a different flat pair — the claim is that `N_eff` is wrong, so it must
  scale wrongly with `N` too) and M7 (check whether `foam`'s abstention is really
  the resolution gate by reporting the veto reason per tile).

---

## 7. Disciplines

**D-M1.** *Pooling groups whose means differ inflates the pooled spread, and the
inflation looks exactly like a broken variance model.* I measured the flat null's
across-tile sd as 2.82x its prediction, and published it as the milestone's most
important finding. The per-pair means drift 0.94 → 1.28 across the burst; the
between-pair spread of those means was 0.1236 of the pooled 0.1247, and the
within-pair spread matched the prediction to 6%. **Before attributing an excess
spread to the model, decompose it into within-group and between-group** — a
pooled sd answers a question nobody asked. The tell was available for free: a
chi-square's sd must track its mean, and my per-pair table showed both drifting
together the moment I printed it.

**D-M1a.** *A plant can validate only one moment of a null, and a model's
assumptions fail in the direction the plant cannot express.* `outlier.rs`
documents the failure mode where forgetting the `N_eff` division makes the mask
"silently inert" (chi2 → `1/m`); real data fails the opposite way
(chi2 → `1 + 0.0076m`). A synthetic scene drawn from an `Rng` satisfies the
independence assumption by construction and reads 1.0 at every radius no matter
how wrong that assumption is about sensors. **Sweep the parameter the model says
is irrelevant** — here, the filter radius — because a flat prediction across a
25x range is the cheapest falsifiable test a variance model offers.

**D-M2.** *A null taken outside the instrument's valid range is not a null.*
The dark-frame arm read 0.440 and looked like a headline 2.3x calibration
defect. It was `green_luma`'s clamp at black destroying half the distribution.
**Before believing a null, check that every stage between the sensor and the
statistic is linear over the range the null occupies.**

**D-M3.** *When a mechanism is identified from a plant, the plant bounds its
magnitude and usually understates it.* M97r correctly derived that blur
displaces curved features, then measured 0.1027 px on a scene containing one
disc. Real subjects gave 0.73–0.95 px. **The derivation transferred; the number
did not.** Quote a mechanism from a plant and a magnitude only from the
material the mechanism will meet (AGENTS rule 13).

**D-M4.** *Test the obvious fix before proposing it.* "Put the mask after
alignment and test the residual" is the natural reading of a coherent 900 ppm
drift term, it costs one least-squares fit to check, and it is **inverted** —
the still subject's residual is 1.43x the moving subject's. A proposal that
survives into a report because nobody spent ten minutes measuring it is worse
than no proposal.

**D-M5.** *An abstention rule that is locally correct can be globally
inverting.* Every individual veto in `mask_tiles` is defensible, and their
aggregate on `foam` is a detector that fires 4.3x less on the moving subject
than the still one, because the estimator's validity domain shrinks exactly
where the signal grows. **Report a gate's abstention rate next to its fire rate,
per stack** — 91% abstention is not visible in a fire rate at all.

**D-M6.** *A separation in a gated rate is not a separation in the underlying
quantity.* Gated rates separated 2.12x while `rms|s|` separated 0.96x. The gate
was passing tiles on contrast, not on motion. **When a conjunction gate shows a
separation, check the continuous quantity underneath it before crediting the
gate** — otherwise you are measuring which stack has more texture.

**D-M7.** *Search the index before commissioning, and again before believing a
module's header.* Four prior reports existed on this exact question, three on
real data, and the brief named none (AGENTS rule 40). The module's own header
also contradicted its own enum forty lines below. **Both the corpus index and
the file's own documentation can be stale; the enum and the tests were right.**

**D-M8.** *When a detector abstains, its reported rate is a property of the
abstention, not of the subject — decompose it before comparing it to anything.*
`ShiftFree` gates 4.35% of `foam`, agreeably close to fact 1189's 4.78%. It also
fires on 98.9% of the tiles it can resolve, so the 4.35% is just the resolvable
fraction wearing a contamination label, and the same instrument reports 22.73%
on a stack that never moved. **Always report `fired / resolvable` alongside
`fired / total`**; the first is what the detector decided, the second is mostly
what it declined to look at. A rate that matches a known truth for the wrong
reason is more dangerous than one that misses, because it survives review.

**D-M9.** *Rank-order against known ground truth is a cheaper and harsher test
than any rate.* Three stacks with known truth cost nothing extra to run and
produced the finding that a still tripod stack scores 5.2x above the motion
archetype. No amount of distribution reporting on a single stack would have
exposed that. **Two stacks give a ratio; three give an ordering, and an ordering
is falsifiable.**

**D-M10.** *Price the stage before improving the instrument.* `outlier.rs` is
the better-instrumented of the two modules addressing this defect and it sits at
the averaging stage, where fact 1189 prices the available recovery at **6%**
against **100%** at the election. Motion wins the sharpness election because a
displaced edge is sharper than a stationary focused one, so the contaminated
frame is already chosen before the averaging runs. **A better instrument aimed
at the wrong stage loses to a cruder one aimed at the right stage** (fact 1555);
verify which stage a defence acts at before measuring how well it acts.
