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

**M2 — MEASURED, and it is the most important finding here. The null's *mean* is
right and its *spread* is wrong by 2.82x, which silently invalidates every
threshold the module derives.** On the same pure-noise flat pair the observed
across-tile standard deviation of chi2 is **0.1247**, against the module's
predicted `sqrt(2/N_eff) = sqrt(2/1024) = 0.0442`.

- Ratio **2.822x**.
- `N_eff` is therefore overstated by **7.96x**: a 1024-sample tile behaves like
  **129 independent samples**, not 1024.
- **`threshold_k = 6.0` is really 2.13 true null standard deviations.**
- Consequence, measured: the 6-sigma bar delivers a **7.19% false-positive rate
  on pure sensor noise**, where an independent-sample model predicts of order
  `1e-7`%.

This is not the low-pass variance propagation, which the module handles and
tests. `Raw` uses `m = 1`, so `N_eff = N` exactly and no propagation is
involved. It is **intrinsic spatial correlation in real data** — the CFA green
luma is `0.5*(G1+G2)`, the lens PSF correlates neighbours, PRNU is fixed — that
the model does not represent at all. The module's docs call `N_eff = N/m`
"conservative"; measured, it is **anti-conservative by 2.82x**.

Every threshold in `outlier.rs`, and any future one of the form
`1 + k*sqrt(2/N_eff)`, is about 2.8x tighter than it claims.

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

---

## 4. Pre-registered criteria: 4 of 6 FAIL

| # | criterion | bar | measured | verdict |
| --- | --- | --- | --- | --- |
| 1 | null mean chi2 | [0.90, 1.10] | 1.038 (flats) | **PASS** |
| 1b | *(not pre-registered)* null sd | `sqrt(2/N)` = 0.0442 | **0.1247** | **FAIL, 2.82x** |
| 2 | trap gated FPR | <= 1.0% (fail > 5%) | **29.55%** | **FAIL** |
| 3 | plant gated rate | >= 20% | 62.78% | **PASS** |
| 4 | separation plant/trap | >= 10x | **2.12x** | **FAIL** |
| 5 | inertness (`Raw` fires) | must fire | 29.60% | **PASS** |
| 6 | plant proportional, no fire at 0 | fire at d>=0.5, not at 0 | **24.51% at d=0, flat to 0.5** | **FAIL** |

Criterion 1b was not pre-registered as a threshold — the pre-registration asked
only that the null "match the predicted one", per the brief's instruction to
check the null's spread as well as its mean. It is recorded as a fail because
the prediction is explicit in the module and the measurement contradicts it.

---

## 5. Verdict

**Do not ship the mask, and do not wire it.** Phase 2 was not reached: it was
conditional on phase 1, and phase 1 fails four of six pre-registered criteria.

At the shipped configuration on real captures the mask
- fires on **29.55%** of a stationary subject,
- fires **4.3x less** on the archetype moving subject than on that stationary
  one,
- separates motion from defocus by **2.12x** where the underlying displacement
  separates by **0.96x**, i.e. not at all, and
- does not respond to a planted displacement anywhere below 1.0 px.

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

**D-M1.** *A statistic's null has two moments and a plant can validate only
one.* M97r's synthetic null landed at 1.00 and was correct; the spread was
2.82x wrong and no synthetic scene could have shown it, because the plant drew
independent samples and real sensors do not produce them. **Check the spread of
a null on real data, not just its mean** — the mean tests the calibration, the
spread tests the independence assumption, and thresholds are built out of the
spread.

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
