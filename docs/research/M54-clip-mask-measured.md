# M54 — the clip mask, measured

> Milestone M54. Everything below is either MEASURED (a command was run and its
> output read), DERIVED (arithmetic on a measured quantity), or ARGUED. Findings
> are numbered `M54-1 …` so the orchestrator can fold them without colliding
> with any absolute block.

## 0. Pre-registration — written before the deciding run

*(Written at 2026-08-23 ~11:55 local, after the population census in §2 and
before any deficit number existed. The census fixed which stacks are treatable
as controls; it says nothing about the deficit, which is the quantity the
criterion below decides on.)*

### The mechanism under test

`green_luma_with_clip` sets a per-pixel flag but writes luma **identical** to
`green_luma`. The flag is folded only into `ClipCensus`. `FocusField::compute`,
`regularise`, `FocusStats::fold`, `Gate::admits` and `Estimator::fold` never see
it. So a sample pinned at the container maximum enters the focus volume as if it
were a measurement, and enters the gated average as if it were a measurement.

### The observable

For plane pixel `i`, with `w(i)` the frame `FocusStats` elected as winner:

```
deficit(i) = winnerGreenLuma(i) - mergedGreenLuma(i)          [raw DN]
```

`winnerGreenLuma = 0.5*(G1+G2)` of frame `w(i)` at `i`; `mergedGreenLuma =
Estimator::green_mean(i)`. Populations, all at `CONTAINER_MAX_DN = 16383`:

- **WINCLIP** — the elected winner frame was clipped at `i`. Here the winner's
  own evidence is "at least 16383", so any positive deficit is the merge
  emitting a number the winner does not support.
- **CTRL-bright** — never clipped in any frame, focus support never touched a
  clipped sample, winner luma ≥ 0.8·white. This carries the same
  brightness-and-structure confound as WINCLIP (a sharper winner frame at a
  highlight is also a brighter one) and is the matched null.
- **CTRL-all** — never clipped, never contaminated. The global null.

### Success criterion (pre-registered)

**Harm is REAL** iff, at some gate in {0.5, 1.0, 2.0, 4.0}, on `coffee-bean` or
`coffee-bubbles`, **both** hold:

- **(a)** `median deficit(WINCLIP) − median deficit(CTRL-bright) > 1 × σ`, where
  σ is the model's predicted single-sample green-luma sigma at the merged level
  (≈ 27 DN at ISO 50 near white). One σ is the yardstick because a bias below
  one sample sigma is invisible against the pixel's own noise, and this project
  is a noise-aware estimator.
- **(b)** the WINCLIP population exceeds **0.01 % of the plane** (≈ 824 px),
  i.e. at least the scale of fact 203's own `n = 616`.

**Harm is NOT WORTH FIXING** iff (a) or (b) fails at every gate on both stacks.

**Validity control.** On `109MSDCF`, `112MSDCF` and `119MSDCF` the WINCLIP
population must be **exactly 0**, and CTRL-all's median deficit must sit within
±1 σ of 0. If WINCLIP is non-zero on those three, the statistic is measuring
something other than clipping and every number here is void.

### Second criterion, evaluated only if harm is REAL

A candidate fix is accepted iff it (i) reduces `median deficit(WINCLIP)` by
≥ 50 %, (ii) leaves CTRL-all's median deficit unmoved to within 0.1 DN, and
(iii) is a **bit-identical no-op** on a stack containing no clipping.

### Negative control for every "the fix works" claim

Deliberately regress the changed code, confirm the test that guards it goes red,
restore from a `$env:TEMP` copy, reset mtime, and re-run reading the `Compiling`
lines (rule 33).

### Constants this harness shares with the code under test (rule 34)

`CONTAINER_MAX_DN`, `Levels::black/white` as the decoder reports them, the noise
model from `profile::noise_model_for`, `WINDOW_RADIUS`, `REGULARISER_RADIUS`,
`FOCUS_NOISE_SD`. Sharing is unavoidable: the question is not whether any of
those constants is right, it is what the pipeline built from them does at a
clipped pixel. The part that is **not** shared, and is therefore the falsifiable
term, is the deficit null — `deficit ≈ 0` is a statement about the *data*, and it
is evaluated on three stacks that contain no clipping at all, where the harness
has no way to manufacture a zero.

---

## 1. Headline

**Fact 203 is right that the mask is absent and wrong that this is "a
maximum-severity hole": the pre-registered harm criterion FAILED on both
affected stacks, and fact 203's own prescription — mask before the focus volume
and propagate — is 680x to 2100x more destructive than the defect it addresses,
because it darkens real highlights by 1000-3300 DN and moves the elected winner
at 2.7-7.0 % of the plane, 99.6 % of them at pixels that are never clipped in any
frame.**

The residual defect is real but small and is *not* where fact 203 says it is: it
is in the **average**, not in the focus volume, and it touches 0.0004-0.0028 % of
samples. I have fixed exactly that, in `merge.rs`, behind a new entry point that
requires a one-line call-site change in a file M53 owns (§8).

---

## 2. What I measured, and how

A Rust harness at `experiments/M54-clip-mask/` links `strehl-core` and
`strehl-raw` **by path** and drives the *shipped* operator — `green_luma_with_clip`
-> `FocusField::compute` -> `regularise` -> `FocusStats` -> `Gate` -> `Estimator`.
It re-implements exactly one thing, the masked winner election needed for arm B,
and that carries a power check that runs on every invocation: with an all-valid
mask it must reproduce `FocusStats` bit for bit. It did, at all 8 241 504 px, on
every stack. A second cross-check confirms the harness's admission set equals
`Estimator::n_eff` at every pixel and every gate.

Three arms:

| arm | what it is |
|---|---|
| **A** | the shipped pipeline, unmodified |
| **B** | fact 203 taken literally: a pinned sample anywhere in a response's read extent invalidates that response, and the election may not choose it |
| **C** | my fix: the mask reaches the **average only**, keyed on the winner, and never touches the focus volume or the election |

Arm B's propagation is deliberately the *maximal* reading, so it upper-bounds any
softer rule: dilation is the shipped `box_mean` applied at `SUPPORT_RADIUS = 14`
then `REGULARISER_RADIUS = 8`, which yields at each pixel the **fraction of its
combined 43x43 support that is pinned** — exactly `1/841 = 1.189e-3` for a single
pinned sample. I swept the invalidation threshold over that fraction from 0
(fact 203 literal) to 0.5.

---

## 3. Findings

### M54-1 — the mask is absent, exactly as M49 row 4 says (MEASURED, confirms)

`merge.rs` and `focus.rs` contain zero occurrences of `clip`. `green_luma_with_clip`
writes luma identical to `green_luma`, pinned by its own test
`the_clip_mask_reports_clipping_without_altering_the_luma`. `Estimator::fold`
took no clip parameter. The mask reached only `ClipCensus` and the `--stats`
confidence union. **M49 row 4's structural claim is correct and I found no path
it missed.**

### M54-2 — fact 202 is refuted: `113MSDCF` is not clipping-free (MEASURED)

Independent rawpy census, all frames, green planes, "either green of the quad at
or above the level":

| stack | N | max green | ever >= 16383 | always >= 16383 | ever >= 15360 |
|---|---|---|---|---|---|
| coffee-bean | 105 | 16383 | 784 781 (9.52 %) | **0** | 1 439 944 |
| coffee-bubbles | 19 | 16383 | 41 632 (0.51 %) | 724 | 45 807 |
| 109MSDCF | 22 | 7006 | 0 | 0 | 0 |
| 112MSDCF | 79 | 11786 | 0 | 0 | 0 |
| **113MSDCF** | 63 | **16383** | **58** | 0 | **72** |
| 119MSDCF | 33 | 12046 | 0 | 0 | 0 |

The 72 pixels sit in contiguous blobs (e.g. y1464-1467, x1131-1134), appear in
13 of 63 frames, and the same coordinates in `112MSDCF` frame 0 read a maximum of
1953 against a global maximum of 2144 — **genuine scene saturation, a small
specular highlight, not hot pixels.** `113MSDCF` must be struck from any list of
clipping-free stacks. `109/112/119MSDCF` remain exactly zero and are sound
controls.

### M54-3 — 15360 is not a clip point in the data; 16383 is (MEASURED)

Histogram of the top of the green range, `coffee-bean`, 11 frames sampled every
10th. Counts are perfectly smooth across the declared white level — 8136 in
[15359, 15360) against 8356 in [15360, 15361) — and then spike by three orders of
magnitude at exactly 16383: 1 404 312 samples there against 1285 in [16382, 16383).
**`clip.rs`'s refusal to unify `Levels::white = 15360` with
`CONTAINER_MAX_DN = 16383` is correct and now has direct evidence.** Corollary
worth flagging separately: merged green reaches 15871 DN black-subtracted, 6.9 %
beyond the range over which the noise model is calibrated.

### M54-4 — at clipped pixels the gate has already collapsed, so the "mask must reach the gate" half of fact 203 has almost nothing to do (MEASURED)

`n_eff` at pixels whose winner is clipped, against the matched control:

| stack | gate | n_eff WINCLIP | n_eff CTRL-all |
|---|---|---|---|
| coffee-bubbles | 0.5 / 4.0 | 1.023 / 1.179 | 1.258 / 3.740 |
| coffee-bean | 0.5 / 4.0 | 1.881 / 28.784 | 1.709 / 26.290 |

On `coffee-bubbles` the merge is already a pure selector at clipped pixels: there
is no average there to contaminate. On `coffee-bean` the acceptance set is wide,
so the mechanism does exist — which is why the fix in §6 is keyed on the
*winner's* sample rather than on `n_eff`.

### M54-5 — the pre-registered harm criterion FAILED (MEASURED, decides the brief)

`deficit = winner green luma - merged green luma`, in raw DN:

| stack | gate | WINCLIP n | med WINCLIP | med CTRL-bright | gap | 1 sigma | (a) met? |
|---|---|---|---|---|---|---|---|
| coffee-bubbles | 0.5 | 19 437 | 0.00 | 0.00 | 0.00 | 131.8 | no |
| coffee-bubbles | 4.0 | 19 437 | 0.00 | 0.00 | 0.00 | 131.7 | no |
| coffee-bean | 0.5 | 941 | 0.00 | 0.00 | 0.00 | 42.0 | no |
| coffee-bean | 4.0 | 941 | 0.00 | 0.00 | 0.00 | 41.7 | no |

Criterion (b) passes on both (19 437 = 0.236 % and 941 = 0.0114 % of the plane,
both above the 0.01 % floor). **Criterion (a) fails at every gate on both stacks:
the median gap is exactly zero.** By the criterion I wrote down before running
this, **harm is NOT REAL as fact 203 frames it.**

The *mean* deficit on WINCLIP is non-zero (6-35 DN on `coffee-bubbles`,
224-459 DN on `coffee-bean`) but so is the matched control's (37-107 and
24-247), and the mean was not the pre-registered statistic. I report it as a
secondary, non-deciding observation.

**Validity control: passed.** On `109MSDCF`, `112MSDCF` and `119MSDCF` the
WINCLIP population is exactly 0, contamination is exactly 0, and arm B is
identical to arm A by construction. The statistic does not fire on stacks
without clipping.

### M54-6 — rule 4's "the argmax flees clipped frames" is true only for extended saturation, and reverses for point saturation (MEASURED, contradicts the corpus)

Null: if clipping did not influence the election, `P(winner clips at i) = c(i)/N`
where `c(i)` is the number of frames clipping at `i`. Summed over the
ever-clipped set that gives the expected count.

| stack | median pinned fraction of support | contaminated / clipped | expected | observed | ratio |
|---|---|---|---|---|---|
| 113MSDCF | 0.00322 (~2.7 samples of 841) | 85.2x | 1.8 | 23 | **13.05x seeks** |
| coffee-bubbles | 0.01566 (~13 of 841) | 16.55x | 13 335.3 | 19 437 | **1.4576x seeks** |
| coffee-bean | 1.00000 (all 841) | 1.48x | 92 985.9 | 941 | **0.0101x flees** |

Perfectly monotone in the spatial extent of the saturated region. **The sign is
set by extent relative to the focus window, not by clipping.** A large saturated
patch flattens the gradient inside the window and repels the argmax, which is
rule 4's mechanism and is confirmed. An isolated saturated *point* sits on the
steepest edge in the frame and attracts it by an order of magnitude. Rule 4 and
fact 242 state the flee direction unconditionally; that is a corpus error, and
the contaminated/clipped ratio is a cheap discriminator for which regime a stack
is in.

### M54-7 — fact 203's prescription, implemented literally, is a large regression (MEASURED — the central result)

Arm B at threshold 0, against arm A:

| stack | winners moved | % of plane | of which never clipped | arm A winner clipped there | arm B winner clipped there | median \|dDN\| | mean \|dDN\| |
|---|---|---|---|---|---|---|---|
| coffee-bubbles | 575 138 | **6.98 %** | 545 540 (94.9 %) | 14 707 | **0** | 207.0 | 1058.7 |
| coffee-bean | 224 287 | **2.72 %** | 183 362 (81.8 %) | 941 | **0** | 414.5 | 648.5 |
| 113MSDCF | 4 569 | 0.055 % | 4 511 (98.7 %) | 23 | **0** | 131.0 | 502.1 |
| 109/112/119MSDCF | **0** | 0.000 % | 0 | 0 | 0 | — | — |

Three things make this a regression rather than a change:

1. **The collateral ratio.** Winners moved per winner-clipped pixel actually
   addressed: **29.6x** (`coffee-bubbles`), **238x** (`coffee-bean`), **199x**
   (`113MSDCF`). The overwhelming majority of the moved pixels — 94.9 %, 81.8 %,
   98.7 % — are **never clipped in any frame**. Their own samples are entirely
   valid; arm B discards the frame the operator judged best-focused for reasons
   outside the pixel. There is no account on which that improves the estimate.
2. **The direction at the pixels it is supposed to help.** Signed change in
   elected winner luma, restricted to ever-clipped pixels:
   `coffee-bubbles` mean **-2883 DN**, median **-3333**; `coffee-bean` mean
   **-1021**, median **-965**; `113MSDCF` mean **-2968**, median **-2311**.
   Arm B darkens saturated highlights by 6.5-22 % of full scale. This is
   structural, not incidental: arm B is *forbidden* from electing any frame that
   clips at the pixel (arm B winner clipped: 0, on every stack), and at a
   specular highlight the in-focus frame is the brightest and therefore the one
   that clips. **The prescription guarantees that the merge can never report a
   highlight at its focused brightness.**
3. **It is a cliff, not a dial.** At threshold 0 one pinned sample in 841
   condemns a response whose value it can barely have moved. Sweeping the
   threshold on `coffee-bubbles`: 575 138 moved at 0, 486 177 at 0.002,
   362 304 at 0.01, 136 531 at 0.05, 45 090 at 0.10, 1199 at 0.25, **0 at 0.50**.
   The rule stops mattering exactly where arm A's argmax already refuses those
   frames on its own — i.e. above half the support pinned, the shipped operator
   is *already* doing what fact 203 asks, for free, via M54-6's flattening
   mechanism.

At gate 0.5 on `coffee-bubbles`, 562 358 of the 575 138 moved pixels have
`n_eff = 1`, where the change in the elected winner **is** the change in the
output: mean 1064 DN, median 210 DN, max 15 559 DN. This is not a subtle effect.

### M54-8 — the residual defect is in the average, is real, and is 0.0004-0.0028 % of samples (MEASURED)

Once the election is left alone, one thing still is provably wrong arithmetic:
where the winner's own sample is pinned, the gated mean averages a **censored**
observation with uncensored ones and emits a value below the pin. A censored
sample means "at least 15871"; a mean of it and a smaller number estimates
neither quantity, and can only move the answer down, away from a bound the
winner's own evidence supports.

Population where this actually bites, per CFA plane, winner's sample pinned:

| stack | gate | pinned-winner samples | of those, diluted | mean drop | max drop |
|---|---|---|---|---|---|
| coffee-bubbles | 0.5 | 32 020 | 99 | 2188 DN (DERIVED) | 7375 |
| coffee-bubbles | 4.0 | 32 020 | 631 | 1871 DN (DERIVED) | 8321 |
| coffee-bean | 0.5 | 1227 | 277 | 823 DN (DERIVED) | 1919 |
| coffee-bean | 4.0 | 1227 | 384 | 1224 DN (DERIVED) | 2018 |

Small — 0.0012-0.0077 % of the plane — but individually large, up to 8321 DN,
which is a highlight rendered at 54 % grey instead of white. And unlike arm B the
blast radius is bounded by the population itself: the repair cannot move a single
pixel that was not already emitting a value its own winner contradicts.

---

## 4. Verdict against the pre-registered criterion

- **(a) median-deficit gap > 1 sigma: NOT MET**, at every gate on both affected
  stacks. Gap is exactly 0.00 DN.
- **(b) WINCLIP > 0.01 % of plane: MET** on both.
- Validity control on `109/112/119MSDCF`: **PASSED** (exactly zero).

By the rule I wrote down first, **"harm is NOT WORTH FIXING" is the verdict on
fact 203 as stated.** Fact 203 overstates this. I nevertheless shipped the narrow
repair in M54-8, because that defect was found *outside* the pre-registered
observable (the deficit statistic is structurally blind to it: `deficit` is 0 by
construction wherever `n_eff = 1`; mean `n_eff` on `coffee-bubbles`' WINCLIP
population is 1.023, so at least **97.7 %** of it sits there — DERIVED),
it is provably-invalid arithmetic rather than a bias question, and
its blast radius is 1:1 rather than 238:1. That is a judgement call and I flag it
as one.

## 5. Statistics I built that turned out to have no power, and why

Recorded because they are the reusable part.

1. `deficit = winner - merged` is **identically zero wherever `n_eff = 1`**. On
   `coffee-bubbles`, mean `n_eff` on WINCLIP is 1.023, so at least 97.7 % of the
   population sits there (DERIVED) and the statistic
   had no power over almost the whole thing. Per-CFA-plane dilution counting is
   the version with power, and it is what found M54-8.
2. "Merged luma below the container maximum" is meaningless as a defect count,
   because luma is `0.5*(G1+G2)` while the clip flag is "either green", so a
   half-clipped quad is *expected* to read below the pin. An early version of
   this harness reported 35 % of clipped pixels "diluted" on that basis. It was
   an artefact of the statistic. Per-plane accounting replaced it.
3. `CTRL-bright` had only 22-107 px on `coffee-bubbles` — a rule 36 failure,
   caught by asserting the population size. It needed `coffee-bean`
   (2 430 956 px) to have any power at all.

## 6. What I changed

`crates/strehl-core/src/merge.rs`, additive only; `fold`'s behaviour and
signature are untouched and every pre-existing test still passes unmodified.

- `Estimator::fold_censored(frame_index, src, regularised, container_max_dn)` —
  `fold` plus saturation bookkeeping, sharing one private `fold_inner`.
- `Estimator::is_censored(plane, i)` — the winner's own sample there was pinned.
  `Estimator::value` returns the container maximum at those samples instead of a
  mean that is below a bound the winner supports.
- `Estimator::has_censored_contributor(plane, i)` — some *non-winning* admitted
  frame was pinned. This is a **flag only**; the arithmetic is unchanged, because
  excluding it would need a per-plane admitted count that the estimator
  deliberately does not carry. See §9.
- `Estimator::censor_level()`; `absorb` unions the flags and refuses to reduce
  estimators censored against different maxima; mixing `fold` and `fold_censored`
  in one estimator panics.
- Cost: one byte per pixel (4 winner bits, 4 contributor bits), allocated only on
  first `fold_censored`, and reported through `allocated_bytes`.

Measured effect (arm C, `Estimator::fold_censored` against `Estimator::fold`, on
the same `FocusStats`):

| stack | gate | samples changed | % of samples | mean lift | max lift | contributor flags |
|---|---|---|---|---|---|---|
| coffee-bubbles | 0.5 | 145 | 0.0004 % | 1912.7 | 7504.5 | 909 |
| coffee-bubbles | 4.0 | 932 | 0.0028 % | 1753.6 | 8723.0 | 6884 |
| coffee-bean | 0.5 | 278 | 0.0008 % | 821.7 | 1919.0 | 942 |
| coffee-bean | 4.0 | 385 | 0.0012 % | 1222.3 | 2018.0 | 63 343 |
| 113MSDCF | all | 0 | 0.0000 % | — | — | 0-10 |
| 112MSDCF | all | **0** | 0.0000 % | — | — | 0 |
| 119MSDCF | all | **0** | 0.0000 % | — | — | 0 |

Every change is a **rise** toward the pin — the harness asserts `neg == 0` on
every run rather than hoping. `112/119MSDCF` are a bit-exact no-op, satisfying
criterion (iii). `113MSDCF` changes nothing because all 23 of its winner-clipped
pixels sit at `n_eff = 1`, so there was never anything diluting them: a real
in-corpus case where the defect exists and the repair correctly declines to act.

**Independent cross-check between M54-8 and arm C.** The two are computed by
different code on different state — M54-8 counts pixels where the harness's own
record of the winner's sample is pinned and the *plain* estimator reads below the
pin; arm C diffs two estimators' `value()`. On `coffee-bean`, where R and B
essentially never pin (1 px and 25 px in the whole stack), they must agree, and
they do: 277 against 278 at gate 0.5, and the derived mean drop 823 DN against
arm C's measured mean lift 821.7 DN. On `coffee-bubbles` arm C reads higher
(145 against 99) precisely because R and B *do* pin there (4979 and 12 177 px),
and arm C covers all four planes while M54-8's table covers only the greens. Two
routes to the same quantity, agreeing where they should and differing exactly
where they should.

Compare blast radii at gate 1.0: arm B moves 575 138 px on `coffee-bubbles` and
224 287 on `coffee-bean`; arm C changes 268 and 330 *samples*. Arm B is
**~2100x** and **~680x** larger, and in the harmful direction.

## 7. Negative control

Two deliberate regressions to `merge.rs`, each rebuilt with a visible
`Compiling strehl-core` line (rule 33), restored from `$env:TEMP\M54-merge-good.rs`
with the mtime reset — **never** `git checkout --`.

| regression | expected red | result |
|---|---|---|
| `value()` ignores the censor bit (reverts to the plain mean) | `a_censored_winner_reports_the_bound_instead_of_a_diluted_mean` | **FAILED as required**; other 3 stayed green |
| censoring keyed on *any* admitted frame, not the winner | `a_censored_contributor_is_flagged_but_never_silently_changes_the_mean` | **FAILED as required**, and `censored_estimators_reduce_by_union_of_their_flags` also went red |

After restore: `regression traces left: 0`, 4/4 green with a fresh `Compiling`
line. Note the first regression left `censoring_is_a_bit_exact_no_op_when_nothing_reaches_the_container`
green, which is correct — that test is the no-op control and has no power over
this branch by design. Stating that explicitly is the rule 35/36 discipline.

Rule 34 declaration: the tests use `TEST_PIN = 4095`, deliberately **not**
`CONTAINER_MAX_DN = 16383`, so a hard-coded production constant in
`fold_censored` fails all of them. Expected means are hand-arithmetic on the
fixtures' own sample values. Rule 36: each test asserts `n_eff == 3` before
asserting anything about dilution, so a fixture that stopped admitting three
frames would fail loudly rather than pass vacuously; R and B are held far from
the pin as an in-fixture control that censoring does not touch them.

## 8. What I could not change — hand-off to the owner of `merge_cmd.rs` (M53)

`crates/strehl-cli/src/merge_cmd.rs` is M53's. The core change is inert until one
call site moves. Exactly one line is required:

- **`crates/strehl-cli/src/merge_cmd.rs` line 819**, in pass two's fold loop.
  Change
  ```rust
  if let Err(e) = e.fold(index, &frame, &scratch.reg) {
  ```
  to
  ```rust
  if let Err(e) = e.fold_censored(index, &frame, &scratch.reg, CONTAINER_MAX_DN) {
  ```
  `CONTAINER_MAX_DN` is already in scope — it is imported at line 42
  (`use strehl_core::clip::{CONTAINER_MAX_DN, ClipCensus};`) and already used at
  line 513 for `green_luma_with_clip`. Nothing else changes: `Estimator::new`,
  `absorb`, `value`, `green_mean`, `n_eff` and `predicted_sigma` all keep their
  signatures, and `fold` still exists and still behaves exactly as before, so the
  change is reversible by reverting that one line.

Optional, same file, worth doing but not required for correctness:

- **`--stats` / confidence output.** `Estimator::is_censored(plane, i)` is now a
  per-pixel truth channel: "this value is a lower bound, not a measurement". That
  is a strictly better signal than the existing `--stats` clip union at
  :1631/:1634/:1693, which is a whole-frame OR taken before the election and
  therefore says nothing about whether the *elected* frame was clipped.
  `predicted_sigma` at a censored pixel is currently a number about a mean that
  is no longer being reported, and should be suppressed or flagged there.

I did **not** touch `merge_cmd.rs`, `stack.rs`, `lib.rs`, `flat_ratio.rs`,
`profile.rs`, `clip.rs`, `plane.rs`, `focus.rs`, `SYNTHESIS.md` or `AGENTS.md`.
`plane.rs` and `focus.rs` are mine and needed no change: **the fix must not be in
either of them**, which is the whole content of M54-7.

## 9. Open, and deliberately not closed

- **Censored contributors.** `has_censored_contributor` fires on 63 343 samples
  at gate 4.0 on `coffee-bean` (0.19 % of samples). There the mean is biased
  *upward* by a pinned non-winner. Excluding those needs a per-plane admitted
  count — 4 x `Vec<u16>`, +66 MB at full resolution — so it is a memory decision
  for the orchestrator, not a local one. The flag is exposed so the cost of the
  decision is now measurable rather than hypothetical.
- **Decoder disagreement.** `rawler` reports an active area of 7032x4688 -> plane
  3516x2344 = 8 241 504 px. `rawpy`'s `raw_image_visible` is 4688x7028 -> plane
  3514x2344 = 8 236 816 px, which is the count fact 203 and M26 quote. A
  two-plane-column difference. Noted, not chased; all percentages here use the
  `rawler` count, which is what the shipped pipeline sees.
- **`coffee-bubbles` is ISO 1000**, not ISO 50 (`sigma(14848) = 130.4 DN` against
  41.2 at ISO 50). The brief's ISO attribution covers other stacks.
- **The model is calibrated over `[0, 14848]` and the merge emits up to 15871.**
  Every censored pixel is 6.9 % outside the noise model's calibrated range by
  construction. That is now explicit rather than silent, but it is unresolved.

---

## 10. Re-take under M48's new `read_noise_e_high` (added 12:45, after the report was first committed)

M48 changed `read_noise_e_high: 1.47 -> 1.2392` in commits `f95f6f4` … `9a7e3da`,
timestamped **11:17:59 – 11:27:24**. Several of my harness runs are later than
that, but one intermediate build (`cargo build --release` on the harness alone)
showed only `Compiling m54-clip-mask` and **not** `Compiling strehl-core`, so by
rule 33 my numbers were not admissible evidence either way until re-taken.

### M54-9 — only `coffee-bubbles` was ever exposed (MEASURED, structural)

`CameraProfile::read_noise_e(iso)` returns `read_noise_e_high` iff
`iso >= second_base_iso = 400.0`, else `read_noise_e_low = 4.20`, which M48 did
not change (`profile.rs:152-158, 188-189`).

| stack | ISO | branch | exposed to M48's change? |
|---|---|---|---|
| coffee-bean | 50 | low, 4.20 | **no** |
| 119MSDCF | 50 | low, 4.20 | **no** |
| 109/112/113MSDCF | 160 | low, 4.20 | **no** |
| coffee-bubbles | 1000 | **high** | **yes** |

**Pre-registered prediction, written before the re-take:** after a forced clean
rebuild, `coffee-bean` and the MSDCF stacks must return **bit-identical**
numbers; only `coffee-bubbles` may move. If `coffee-bean` moves, the rebuild
changed something other than the read-noise constant and the re-take is void.

### M54-10 — the re-take is bit-identical, and my original runs already used 1.2392 (MEASURED)

`cargo clean -p strehl-core -p m54-clip-mask` then rebuild, with
`Compiling strehl-core` / `strehl-raw` / `m54-clip-mask` all visible. Every
quoted figure came back unchanged on both stacks — census, contamination,
winner-clip ratio, the arm B displacement and every signed delta:

| quantity | coffee-bubbles before / after | coffee-bean before / after |
|---|---|---|
| ever >= 16383 | 41 632 / **41 632** | 784 781 / **784 781** |
| winner frame clipped | 19 437 / **19 437** | 941 / **941** |
| winner-clip ratio vs null | 1.4576x / **1.4576x** | 0.0101x / **0.0101x** |
| arm B winners moved | 575 138 / **575 138** | 224 287 / **224 287** |
| signed dDN, ever-clipped | -2883.03 / **-2883.03** | -1020.95 / **-1020.95** |

The prediction held on `coffee-bean` (bit-identical, so the re-take is valid) and
`coffee-bubbles` did not move either. The reason is visible in the harness's own
header: it printed `sigma(0) = 2.0061` for `coffee-bubbles`, and
`1.2392 * (1000/436.8) / sqrt(2) = 2.00606`, whereas the old constant gives
`1.47 * (1000/436.8) / sqrt(2) = 2.3797`. **The original runs had already linked
the new constant.** Nothing in §§1-9 needs revision.

### M54-11 — the clip question is structurally insensitive to read noise (DERIVED)

Worth stating because it means the timing above could not have mattered. At
ISO 1000, `gain = 2.28938 DN/e-`, so at a plane signal of 14 848 DN:

| term | new (1.2392) | old (1.47) |
|---|---|---|
| read-noise variance | 8.05 DN^2 | 11.33 DN^2 |
| shot variance | 33 994.2 DN^2 | 33 994.2 DN^2 |
| green-luma sigma | 130.3854 DN | 130.3917 DN |

Shot noise outweighs read noise **4223:1** there, so a 15.7 % change in the
constant moves sigma at the top of the range by **0.0048 %**. Every population in
this report lives at or near saturation by construction. The same constant moves
`sigma(0)` by **-15.7 %** (2.3797 -> 2.0061), so M48's change is large in the
shadows and arithmetically irrelevant in the highlights — which is the only place
a clip mask can act.

### M54-12 — dependence on `FOCUS_NOISE_SD`, stated and not touched

As instructed I have **not** touched `FOCUS_NOISE_SD` and treat its current value
as given. Splitting my findings by whether they depend on it at all:

- **Independent of it** (argmax-only; the gate is not involved): M54-1
  (structural), M54-2 (census), M54-3 (histogram), M54-6 (winner-clip rate vs
  null), and — importantly — **M54-7's winner-displacement counts and signed
  deltas**, because both arms elect by argmax and `MaskedStats` applies no gate.
  **The central refutation is therefore gate-free and immune to
  `FOCUS_NOISE_SD` entirely.**
- **Dependent on it** (through `Gate::tolerance = threshold * sqrt(2) *
  FOCUS_NOISE_SD`): M54-4 (`n_eff`), M54-5 (the deficit table and hence the
  pre-registered criterion), M54-8 (dilution counts) and §6's arm C blast radius.
  If the constant is later re-derived, those tables must be re-run; the harness
  reproduces them in about 50 s per stack. Note the gate ladder here spans 8x
  (0.5 to 4.0) and M54-5's verdict is unchanged across all four rungs, so it
  would take a change of more than 8x in `FOCUS_NOISE_SD` to disturb the verdict.

For the record: M48 appears to have already closed this at commit `21ae46d`
(12:00:32) — *"M48: FOCUS_NOISE_SD does not descend from the profile; no change
needed"* — folded at `f577f42`. If that ruling stands, no re-run is required.

### M54-13 — `focus.rs:287` deliberately not investigated

`focus.rs` is mine and I did not edit it, because the central finding of this
report is that the fix must **not** live there. Per the orchestrator's
instruction I did not go looking at the hard-coded `1.47` fixture, so I have
**no** opinion on whether its absolute value is load-bearing. It remains open and
unexamined, and should be routed to whoever next has cause to edit that file.

### Workspace state at re-take

**206/206 green** with `Compiling` lines visible for all four crates — not the
187 in the brief, because the tree also carries M53's and M55's in-flight work;
my own contribution is +5. Twice during the re-take a `cargo test` run reported
green with **no** `Compiling` line and was stale: one such run masked a genuine
red, and a forced rebuild exposed
`flat_ratio::tests::the_high_pass_ratio_catches_a_planted_explosion_the_raw_ratio_misses`
failing (120.7943 DN against a quadrature prediction of 120.6923 DN), then a
compile error at `flat_ratio.rs:621`. That file is M53's and was uncommitted-dirty
throughout; it has zero references to `Estimator`, `merge::` or anything I
changed, and it self-resolved within two minutes. Reported as observed
cross-agent state, not touched. **Rule 33 earned its place again here.**

## 11. Filter status of the corpus (added 2026-08-23, after this report was folded)

A circular polariser (Breakthrough X4 CPL 67 mm, in front of the 100 mm GM) was
disclosed after this report was written. **The orchestrator initially broadcast it
as present for every frame in the corpus; that universal quantifier was
withdrawn.** EXIF capture dates then resolved it into a date rule, confirmed by the
owner. The rule below is the orchestrator's and the owner's, from EXIF I did not
read myself; I record it only for what it does to this report's claims.

- **CPL OFF (bare lens), up to 17 May:** `112MSDCF`, `113MSDCF` (7 May),
  `119MSDCF` (9 May), `109MSDCF` (17 May)
- **CPL ON, 25 May onward:** `coffee-bubbles`; `foam` probable, not confirmed
- **`coffee-bean` (10 May): UNKNOWN.** On the off side of the boundary, but the
  owner cannot recall it.

**Nothing here is retracted or hedged as a result, and one thing is strengthened.**

1. **No claim in this report ever rested on the filter.** It contains no reference
   to a polariser, and its two uses of "specular" describe what was found in the
   data rather than inferred from the optics.
2. **The control group is bare-lens, which strengthens the design.** The asymmetry
   this milestone was built on -- clipping present on `coffee-bean` and
   `coffee-bubbles`, absent on `109`/`112`/`113`/`119MSDCF` -- has all four
   never-clipping controls on the OFF side. Those zeros are not filter-suppressed
   floors; they are bare-lens zeros. Had the controls been CPL-ON the design would
   have been weak, because a suppressed specular population and a genuinely absent
   one are indistinguishable in a count.
3. **The headline is bare-lens and stands unqualified.** The **13.05x seek** at
   point saturation (section 3, `113MSDCF`, ~2.7 pinned samples of 841) -- the
   number that made AGENTS rule 4's unconditional "the argmax flees clipped
   frames" a corpus error (fact 683) -- was measured on a 7 May stack with no
   filter. So was this report's finding that `113MSDCF` is not clipping-free
   (fact 202 as amended), which is exactly what a bare lens should be expected to
   produce.
4. **`coffee-bean`'s unknown status does not reach the claim it carries.** It
   supplies the opposite pole, **0.0101x flees** at 1.00000 pinned support. That
   statistic is conditioned on a *measured* pinning fraction -- all 841 samples of
   the support pinned, read from the data -- not on any assumption about how the
   scene came to saturate. A filter changes the exposure needed to reach full
   saturation; it does not change that the support was measured fully saturated.
   The confound is real and unresolvable, and it stops short of this number.
5. **`coffee-bubbles` is CPL ON.** Any statement here about its highlight
   population is a filtered measurement and should be scoped to it by name rather
   than generalised to the corpus.

**My own error, recorded because it is this discipline's own failure mode.** Told
the filter was universal, I proposed amending this report's conclusion to "not
worth fixing *on a CPL-filtered corpus*", reasoning that suppressing speculars can
only lower the clipped population, so every zero here was a floor. The reasoning is
sound and the premise was false: **all four zero-clipping stacks are bare-lens.**
The hedge would have weakened a correct negative result by crediting its strongest
evidence to an instrument that was not present. It never reached this file -- I
gated it on the orchestrator's approval and the retraction arrived first -- but the
shape is worth keeping: **a direction argument that is valid in form makes its
premise feel checked.** That is discipline 409.