# M93 — Gating the focus election, and whether the gate eats detail

> **§0 is the pre-registration. It was written into this file and committed
> before any measurement run and before `robust.rs` existed.** Everything from
> §1 onward was written after. Where a criterion was added or changed later, it
> says so, in place, with the reason.

---

## 0. Pre-registration

### 0.1 What the corpus already decided, and what it did not

This milestone is specified by fact **1189**: the average-side mask failed, and
the reason is that **4.78% of `foam`'s output pixels take their value from a
frame that is itself more than 8 sigma discrepant** — motion wins the sharpness
election. Masking the election removes 100% of them; masking the average
recovers 6.0% of the benefit and removes none.

Load-bearing prior results I am building on rather than re-deriving (rule 44 —
fold the delta, not the document):

- Fact **1186** — the contamination statistic: a leave-one-out fourth-difference
  residual along the frame axis `[1,-4,6,-4,1]/6`, normalised by
  `strehl_core::noise`, analytic null `E[z^2] = 1`, measured 0.9897, defocus
  leakage `<= 0.04%`. **I reuse this unchanged. I am not re-validating it.**
- Fact **1187** — `lead-1-cpl` is the measured worst stack (248.6x, 29.1% of
  pixels), `foam` is only 4th (94.4x), **`flowers-cpl` is the cleanest stack in
  the corpus (0.1x)**, and ~8x of raw disagreement is detail composition.
- Fact **1188** — `coffee-bean` is **56.8% photometric**, `foam` is 0.7%. The
  ordering of a robustness stage against a photometric fit is **not settled by
  the corpus**. See §0.7.
- Fact **1190** — the statistic is immune to the fixed-pattern component of
  M90's noise-model defect.

**What the corpus does not know, and what this milestone must decide:** whether
a gate on the election can be built that removes contaminated winners **without
removing correctly-elected sharp frames**. Nothing in the corpus measures that,
and it is the whole risk.

### 0.2 The hazard, stated before building

**This pipeline exists to elect the sharpest frame.** The statistic flags
*disagreement*. A frame can disagree with its temporal neighbours because it
moved, **or because it is the only frame that resolves that pixel** — which is
precisely the frame the merge must keep.

ARGUED, and the reason I expect the gate to be buildable at all: a pixel's
value through focus is a **smooth** function of frame index, because blur radius
varies smoothly with focus position. The fourth-difference kernel annihilates
any cubic, so being in focus does not by itself produce a large `z`. Fact 1186's
`<= 0.04%` leakage bound is measured evidence for this on one stack.

**But that argument has an explicit failure mode and I am registering it now:
under-sampling.** If the focus step is coarse relative to depth of field, `L(f)`
changes sharply between adjacent frames, the fourth difference is large at
exactly the high-detail pixels and exactly near best focus, and **the gate would
preferentially remove the sharpest frames.** Fact 1186's leakage bound was
measured on a 299-frame stack — the most finely sampled in the corpus — so it is
the *best* case for sampling and cannot be assumed to transfer to a 79- or
123-frame stack.

**If I cannot separate "discrepant because it moved" from "discrepant because it
alone resolves this pixel", I will report that as a negative result and will not
ship a gate.**

### 0.3 The design

Two arms, both preserving the architecture. `FocusStats` is a **commutative,
associative, O(1)-per-pixel fold** (`merge.rs:1371`,
`pass_one_elects_the_highest_response_and_is_order_independent`, and
`FocusStats::absorb`). A gate that needs the full through-focus curve per pixel
would cost ~9.8 GB at 299 frames and would break arbitrary worker partitioning.
**Both arms below are argmax folds and preserve every one of those properties.**

- **Arm 0 — ungated.** `argmax_f R_f`. This is the shipped election.
- **Arm H — hard gate.** `argmax_f R_f` over `{f : w(z_f) >= 0.5}`.
- **Arm S — soft demotion.** `argmax_f w(z_f) * R_f`.

`w` is fact 1186's weight, **reused unchanged and with no new constant**:

```
w(z) = 1                          |z| <= 4
w(z) = ((8 - |z|) / 4)^2          4 < |z| < 8
w(z) = 0                          |z| >= 8
```

`R` is the regularised focus response, which is a gradient magnitude and is
therefore non-negative, so `w * R` is a well-defined demotion and arm S is
scale-free. **Arm S is the arm I expect to be correct**, because a frame that is
genuinely far sharper than its neighbours survives a partial penalty, while a
frame that wins by a hair and is discrepant loses. Arm H cannot make that
distinction.

**Fallback, required:** if every frame at a pixel is ineligible (arm H) or every
product is zero (arm S), the pixel falls back to the **ungated** winner. The gate
must never emit a hole and must never leave a pixel unelected.

### 0.4 Registered bars — the guard

**G3 is the bar this milestone exists to satisfy.**

- **G0 — faithfulness.** Arm 0 must reproduce `FocusStats::best_index` at
  **100.000000%** of pixels on every stack tested. If this fails, every other
  number here is void.
- **G1 — placebo, on the measured-cleanest stack.** On `flowers-cpl` the gate
  must be a near-no-op: election changed at **< 0.5%** of pixels **and** mean
  regularised-response drop over the whole frame **< 0.1%**.
- **G2 — the detail control.** On `flowers-cpl`, the election-change rate in the
  **top** populated detail-SNR bin must be **< 10x** the rate in the **median**
  populated bin. Fact 1187 measured that raw disagreement rises ~3 orders of
  magnitude across the detail range; if the gate inherits that on a clean stack
  it is responding to texture, not motion.
- **G3 — the sharp-frame guard.** A **synthetic** through-focus stack is built
  from one real frame: frame `f` is that frame blurred by `sigma(f) = |f - f0| *
  step`, plus noise drawn from the calibrated model at the correct local level.
  **Ground truth is known: `f0` is the unique correct winner at every pixel.**
  - **G3a** at realistic sampling, the gate must elect `f0` at **> 99%** of
    pixels and must rule `f0` ineligible at **< 1%** of pixels.
  - **G3b** the step size is swept and **the step at which `f0`'s gating rate
    first exceeds 5% is reported whatever it is.** That number is the gate's
    operating limit and the project needs it.
  - **Declared failure:** if at realistic sampling the gate removes `f0` at
    **> 5%** of pixels, **the gate eats detail, must not ship, and I will report
    that as the result.**
- **G5 — the shuffled-`z` placebo.** Re-run the gate with the `z` field randomly
  permuted across pixel positions, preserving its marginal distribution but
  destroying its spatial correspondence to the image. **This must not reduce
  election speckle on `lead-1-cpl` by more than 5%.** If shuffled `z` works as
  well as real `z`, the gate is not using contamination information at all and
  every benefit number is an artefact of perturbing the election.

### 0.5 Registered bars — the benefit

Scored on `lead-1-cpl` (fact 1187's measured worst case) **and** `foam`. Not on
`foam` alone — fact 1187 records that demonstrating on `foam` would be tuning on
the 4th-worst stack.

- **G4a — hot winners.** Arm S must reduce the hot-winner rate (elected frame's
  own `|z| > 8`) by **>= 90%**. Arm H zeroes this by construction, so for arm H
  it is a sanity check and **not** evidence.
- **G4b — election speckle.** Define speckle as the fraction of pixels whose
  elected frame index differs from the **median elected index of its 3x3
  neighbourhood** by more than 5 frames. The winner field is a depth map and
  should be spatially smooth; motion breaks that. **Registered: the gate must
  reduce speckle by >= 20% on `lead-1-cpl` and on `foam`, and must not increase
  it by more than 2% on `flowers-cpl`.**
- **G4c — split-half disagreement `H`.** The metric M89's average-side mask
  failed at -5.21%. Registered: **>= 10% improvement on `lead-1-cpl`.** Recorded
  with the caveat M89 measured — `H` has a ~60% floor from election ambiguity and
  is detail-confounded — so it is reported as a continuity check against fact
  1189, not as the primary benefit metric.

### 0.6 Rule 30 — a prediction I expect to be able to falsify

I predict **arm S beats arm H on every benefit metric while costing less on
every guard metric**, and specifically that on `flowers-cpl` arm S changes the
election at **less than half** the rate arm H does. Reasoning: arm H discards a
frame that is 10x sharper than any alternative on the same evidence that
discards one that is 1.01x sharper; arm S does not.

I further predict **G3a passes at realistic sampling and G3b's limit lands
between 1.5x and 4x realistic step.** If G3b's limit is below realistic
sampling, the gate cannot ship and §0.2's under-sampling failure mode is real.

### 0.7 The ordering question, named because it cannot be resolved here

Fact 1188 records that mask-first and photometric-fit-first are different
pipelines and the corpus does not know which wins.

**This gate assumes photometric normalisation runs FIRST**, i.e. it consumes
frames whose per-frame gain and offset have already been fitted and removed.
Reason: fact 1188 measured `coffee-bean` at 56.8% photometric, and a gate run
before that fit would rule frames ineligible for a level change that a per-frame
gain explains completely — deleting data M91 can recover, and double-counting
M91's benefit as the gate's.

**I will measure the size of this dependence rather than only assert it**, by
running the gate on `coffee-bean` with and without a simple per-frame gain
normalisation and reporting the difference. That is an **attribution
cross-check** and `coffee-bean` is explicitly **not** used as a benefit
demonstration, because its disagreement is majority photometric and the credit
belongs to M91.

Fact 608's constraint binds either way: the noise model must see **unscaled** DN,
with any scaling carried as `c^2 * var`.

### 0.8 Ownership and the wiring seam

I own **`crates/strehl-core/src/robust.rs`** (new), **`crates/strehl-cli/
examples/m93-election.rs`** (new), **`experiments/M93-election/`**, and this
report.

**I will not edit `lib.rs`.** Discipline 588: shared registration points belong
to the orchestrator, and M85 committing M86's `pub mod align;` line is the
recorded near-miss. `robust.rs` is therefore written to compile **with no
`crate::` references at all** — it takes plain slices and scalars — so it can be
exercised now via `#[path]` inclusion from the example and later dropped into
`lib.rs` with a one-line patch and no edits to its body. **§10 gives that patch
verbatim.**

I will not edit `merge.rs`, `through_focus.rs`, `stack.rs`, `main.rs`,
`merge_cmd.rs`, `align.rs`, `noise.rs`, `profile.rs` or `lib.rs`. I will not
change `DEFAULT_GATE` (question 90 is open and is not settled by eye). I will not
re-specify the average-side mask (fact 1189 rules it out). `D:\personal\macro`
and `D:\macro-dark-frames` are read-only.

---

## 1. Verdict

**The election-side gate works and should ship. The hazard it was commissioned to
test for did not materialise, and the margin is large.** On a synthetic stack
with known ground truth, the gate rules the correct sharp winner ineligible at
**0.0194%** of pixels against a pre-registered failure threshold of 5% — a
**258x** margin — and at **0.0000%** of the highest-detail pixels up to a focus
step 3x beyond where the ungated election itself still works (MEASURED, §3).
On the measured-worst stack `lead-1-cpl` the gate cuts split-half disagreement
by **-25.25%**, versus **-5.21%** for M89's average-side mask on `foam`; on
`foam` itself the gate delivers **-24.46%**, **4.70x** the mask, and it
*improves* the p99.9 tail by **-34.76%** where the mask made it **+38.18%**
worse (MEASURED, §5, §6). On the measured-cleanest stack `flowers-cpl` it is a
near-no-op: **0.18%** of pixels change and mean response falls **0.038%**
(MEASURED, §4).

**Two registered bars failed and one passed for the wrong reason.** G4b
(speckle) failed hard and in the *wrong direction* — the gate *increases*
election speckle by 201-429% on contaminated stacks (§7.2). My rule-30
prediction was falsified: arm S is **2.27x more** aggressive than arm H, not
half as aggressive (§7.3). G4a passed but is worthless as evidence, because both
arms zero the hot-winner rate *by construction* (§7.1). **The recommendation to
ship survives all three**, and §7 gives the reasoning rather than asserting it.

**Ship arm S (soft demotion), not arm H.** It costs more (2.27x the pixels
changed, -3.83% vs -2.89% mean response) and buys more (-25.25% vs -21.50%).
§5.4 argues the trade explicitly rather than assuming §0.6's prediction.

---

## 2. The metric, and how it separates motion from focus

### 2.1 What is reused and what is new

The contamination statistic is fact **1186**, reused **unchanged**: a
leave-one-out fourth-difference residual along the frame axis, kernel
`[1,-4,6,-4,1]/6`, normalised by the calibrated `strehl_core::noise` affine
photon-transfer model at the pixel's own local level, giving an analytic null
`E[z^2] = 1` with no fitted constant. I did not re-derive or re-validate it.
It is **copied into the harness rather than shared** (`m93-election.rs`, the
block headed *"Copied from M89 rather than shared"*), so that this milestone
cannot silently alter M89's committed instrument.

**What is new in M93 is the consumer.** M89 fed `z` to the *averaging* stage and
measured that it recovered 6.0% of the available benefit. M93 feeds the same `z`
to the **election**.

### 2.2 The separation argument, and the measurement that tests it

ARGUED (§0.2, written before building): a pixel's value through focus is a
smooth function of frame index because blur radius varies smoothly with focus
position; the fourth-difference kernel annihilates any cubic; therefore *being in
focus* does not by itself produce a large `z`.

**The measurement that tests this is the strongest single result in the
milestone, and it is structural rather than statistical.** On the synthetic
sweep (§3), the mean `z^2` over the whole frame is:

| base image | step 0.05 | step 0.50 | step 1.00 | step 3.00 | change |
| --- | --- | --- | --- | --- | --- |
| `flowers-cpl` | 1.6932 | 1.6953 | 1.7125 | 1.7203 | **+1.60%** |
| `wrapped-text-1` | 1.6932 | 1.6953 | 1.7126 | 1.7203 | **+1.60%** |

MEASURED. **A 60x change in focus step moves the disagreement statistic by
1.60%.** And two completely different base images — a low-contrast flower and a
high-contrast text target whose top detail bin is 5.5x larger — produce `z^2`
agreeing **to four decimal places at 8 of 10 steps**. If `z` were reading
defocus, neither of those could hold: `z^2` would track step size and would
track scene contrast. It tracks neither. It is noise-dominated by construction
and the data says so.

This is the evidence that the metric measures *disagreement not explained by
smooth focus change*, which is what the milestone needed and what §0.2 said it
had to demonstrate.

### 2.3 The one honest caveat on this

MEASURED: synthetic `z^2` sits at **~1.69**, not at the analytic null of 1.0.
DERIVED: this is an artefact of the synthesis, not a property of the statistic.
Each synthetic frame is the *same* base frame blurred by a different sigma, so
the base frame's own pre-existing real noise is attenuated by a *different*
factor in each frame; that per-frame attenuation is not smooth in the same way
the signal is, and it inflates the fourth difference. Fact 1186's measured null
of **0.9897** was obtained on real frames with independent noise and is the
number that describes the statistic.

**The direction of this artefact is conservative and that is why it does not
undermine G3.** An inflated `z^2` means the synthetic stack applies *more* gating
pressure than a real stack would. G3's near-zero gating rate is therefore an
upper bound on the hazard, not an underestimate.

---

## 3. G3 — the sharp-frame guard, the bar this milestone exists to satisfy

### 3.1 Construction

A synthetic through-focus stack is built from one real decoded frame: frame `f`
is that frame blurred by `sigma(f) = |f - f0| * step`, plus noise drawn from the
calibrated model at the correct local level, 41 frames, `f0 = 20`, 1024x1024
crop. **Ground truth is known: `f0` is the unique correct winner at every
pixel.** Any pixel at which the gate rules `f0` ineligible is a correctly-elected
sharp frame being destroyed — precisely the failure the orchestrator asked me to
register a control for.

A global rate hides the hazard, because the pixels where electing the sharp frame
*matters* are the high-detail ones. **So the rate is also reported inside the top
populated detail-SNR bin.** I added this stratification after seeing the first
global number (0.0194%) and judging it insufficient as evidence — that is a
change made after looking, and it is recorded here as required; it made the bar
**harder**, not easier.

### 3.2 Result — base `flowers-cpl`, top bin >= 2 sigma, 18,102 px

| step | mean z^2 | f0 wins (arm 0) | f0 wins (arm S) | f0 gated, all px | f0 gated, TOP bin |
| --- | --- | --- | --- | --- | --- |
| 0.05 | 1.6932 | 8.1630% | 8.1633% | 0.0001% | **0.0000%** |
| 0.30 | 1.6963 | 38.4181% | 38.4132% | 0.0002% | **0.0000%** |
| 0.50 | 1.6953 | 99.0907% | 99.0471% | 0.0003% | **0.0000%** |
| 1.00 | 1.7125 | 100.0000% | 99.8376% | 0.0075% | **0.0000%** |
| 1.50 | 1.7172 | 100.0000% | 99.7902% | 0.0142% | **0.0000%** |
| 2.00 | 1.7190 | 99.9566% | 99.7292% | 0.0163% | 0.0055% |
| 3.00 | 1.7203 | 99.9503% | 99.7130% | **0.0194%** | 0.0055% |

Re-run on `wrapped-text-1` as a harsher, higher-contrast base (top bin 98,778
px): max `f0 gated, all` **0.0178%**, max `f0 gated, TOP` **0.0132%**.

### 3.3 Verdict on G3

- **G3 PASSES by 258x.** Registered declared failure: gate removes `f0` at >5%.
  Measured maximum anywhere in the sweep, on either base: **0.0194%**.
- **G3a PASSES wherever the question is meaningful.** Registered: elect `f0` at
  >99% and rule `f0` ineligible at <1%. At step >= 0.5, arm S elects `f0` at
  99.05-99.84% and gates it at <= 0.0194%. **Below step 0.5 arm S fails the >99%
  half — but so does the ungated arm 0, at 8-38%.** That is a *sampling* failure
  of the whole election, not of the gate; arm S tracks arm 0 to within 0.005
  percentage points there. Reporting this rather than quietly scoring G3a only
  in its passing range.
- **G3b DID NOT RESOLVE.** Registered: report the step at which `f0`'s gating
  rate first exceeds 5%. **It never does within the swept range** (max 0.0194% at
  step 3.0, a 60x span). The registered operating limit was never reached, so the
  corpus does not get the number it asked for. §0.6's prediction that the limit
  would land "between 1.5x and 4x realistic step" is therefore **not confirmed**;
  the limit is somewhere beyond 3.0 and this milestone did not find it.

**The inversion worth naming:** I expected the hazard to concentrate in
high-detail pixels, because that is where a uniquely-resolving frame exists. It
does the opposite — the top detail bin gates `f0` at **0.0000%** where the global
rate is 0.0142%. DERIVED: high-detail pixels have a large, unambiguous focus
peak, so the winner beats its rivals by a wide margin and survives demotion,
whereas low-detail pixels are elected near-arbitrarily and are cheap to perturb.
**The gate is safest exactly where the product cares most.**

---

## 4. The null — the placebo on the measured-cleanest stack

`flowers-cpl` (176 frames, ISO 100) is fact 1187's measured-cleanest stack
(0.1x). It is the required no-op arm.

| arm | election changed | mean response | `H` | p99 | p99.9 | speckle |
| --- | --- | --- | --- | --- | --- | --- |
| H hard | 0.080258% | -0.0193% | -0.68% | -2.46% | -3.84% | +0.17% |
| S soft | **0.182296%** | **-0.0383%** | -1.06% | -3.87% | -3.91% | +0.72% |

MEASURED. **G1 PASSES on both halves for both arms**: registered <0.5% of pixels
changed and <0.1% mean response drop; arm S measured 0.18% and 0.038%.

The gate touches roughly **one pixel in 550** on a clean stack and costs four
hundredths of one percent of focus response to do it. That is the number the
"does it destroy clean output" question needed.

---

## 5. The gate — design, wiring, and measured effect

### 5.1 Design and why it is shaped this way

`crates/strehl-core/src/robust.rs`. Three arms, all **argmax folds**:

- **Arm 0 — ungated:** `argmax_f R_f`. The shipped election.
- **Arm H — hard gate:** `argmax_f R_f` over `{f : w(z_f) >= 0.5}`.
- **Arm S — soft demotion:** `argmax_f w(z_f) * R_f`.

`w` is fact 1186's weight, reused with **no new constant**: `w = 1` for
`|z| <= 4`, `((8-|z|)/4)^2` for `4 < |z| < 8`, `0` for `|z| >= 8`.

**The architectural constraint that shaped this is not incidental.**
`FocusStats` is a commutative, associative, O(1)-per-pixel fold
(`merge.rs:1371`, `pass_one_elects_the_highest_response_and_is_order_independent`,
and `FocusStats::absorb`). A gate needing the full through-focus curve per pixel
would cost ~9.8 GB at 299 frames and would break arbitrary worker partitioning.
**All three arms preserve every one of those properties**, and `RobustElection`
implements `absorb` with a unit test asserting the ungated sub-state propagates
through it.

**Fallback:** if every frame at a pixel is ineligible (arm H) or every product is
zero (arm S), the pixel falls back to the ungated winner. **MEASURED: the
fallback fired 0 times on every stack tested** — the gate never emitted a hole.

`winner_response()` returns the **raw** `R` at the elected frame, not `w*R`. This
matters and it is the one non-obvious piece of the design: for arm S the score is
`w*R`, so if pass two's admission band `best - focus <= tolerance` were centred on
the score rather than the raw response, the band width would silently change with
the weight.

### 5.2 The noise-model wiring

The threshold is in **sigmas**, never DN. `z` is formed by dividing the
fourth-difference residual by `sqrt(sum_j k_j^2 * var(L_j))` where
`var(L) = a*L + b` comes from `strehl_core::noise` with `a`, `b` looked up per-ISO
from `strehl_core::profile`. The harness prints the model it used, e.g.
`var(L) = 0.114469*L + 0.4623` at ISO 100.

Fact 608's constraint is honoured: the noise model sees **unscaled** DN, with any
per-frame photometric gain `c` carried as `var(cL) = a*c*L' + b*c^2`. This was a
real refactor of `z_at`, not a comment — and I verified it byte-identical to the
pre-refactor committed output by SHA256 before trusting it.

Known deliberate approximation: ISO 50 (`coffee-bean`) falls below `profile`'s
`base_iso` floor and receives ISO 100 coefficients. Measured twice, once with and
once without photometric normalisation; noted rather than hidden.

### 5.3 Measured effect on real stacks (arm S)

| stack | n | ISO | changed | response | hot winners | `H` | p99 | p99.9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `flowers-cpl` | 176 | 100 | 0.18% | -0.04% | 0.0162% -> 0 | -1.06% | -3.87% | -3.91% |
| `lead-1-cpl` | 123 | 100 | 24.28% | -3.83% | 8.0793% -> 0 | **-25.25%** | -39.18% | -36.05% |
| `foam` | 100 | 1000 | 12.26% | -1.81% | 4.7822% -> 0 | -24.46% | -38.67% | -34.76% |
| `coffee-bean` | 105 | 50 | 20.15% | -4.11% | 6.6138% -> 0 | -30.91% | -39.77% | -33.04% |

MEASURED. **G4c PASSES by 2.5x** on `lead-1-cpl`: registered >= 10%, measured
-25.25% (arm S) and -21.50% (arm H).

**An independent-instrument corroboration worth recording:** `foam`'s arm-0
hot-winner rate measures **4.782246%**, reproducing fact 1189's 4.78% exactly
from a separately-written harness. That was not tuned; it is the same quantity
computed by different code and it agreeing to four significant figures is a check
on both.

### 5.4 Arm S or arm H — the recommendation, argued

MEASURED, and it **falsifies §0.6**: arm S is not the gentler arm. It changes
`flowers-cpl`'s election at **2.27x** arm H's rate (0.182% vs 0.080%) and costs
**1.33x** the response on `lead-1-cpl` (-3.83% vs -2.89%).

DERIVED mechanism: arm H is a step at `w >= 0.5`, i.e. at `|z| = 5.172`. Arm S
perturbs the entire `4 < |z| < 5.172` band that arm H leaves **completely
untouched**, and *partially* demotes in `5.172 < |z| < 8` where arm H either
keeps a frame at full strength or deletes it. **Arm S touches strictly more
frames than arm H.** My §0.6 reasoning was right about the *mechanism* — arm S
does preserve a frame that is 10x sharper — and wrong about the *aggregate*,
because I only counted the frames arm S rescues and not the much larger
population it newly touches.

**Recommendation: ship arm S, and the trade is not one-sided.** MEASURED, on
`lead-1-cpl`: benefit per unit of mean response sacrificed is **6.59** for arm S
(-25.25% / -3.83%) and **7.45** for arm H (-21.50% / -2.89%). **Arm H is the more
efficient arm on that ratio.** Arm S wins on total benefit, by 3.75 percentage
points of `H`.

The reason to prefer arm S is §0.3's original one, which G3 now supports with
data rather than intuition: **the cost of aggression is essentially zero where it
would matter.** G3 measures arm S gating the correct sharp frame at **0.0000%**
of top-detail-bin pixels, so the extra response arm S spends is spent in
low-detail pixels whose winner was near-arbitrary anyway. Buying 3.75 points of
disagreement reduction with response the product does not miss is the right
trade.

**If a later milestone measures that arm S's response cost is visible in a
rendered image, arm H is the correct fallback and no new code is needed — it is
already implemented, unit-tested, and selected by a single enum variant.**

---

## 6. The election-vs-average question

This is the question fact 1189 raised and this milestone was commissioned to
answer.

| | M89 average-side mask | M93 election-side gate |
| --- | --- | --- |
| `foam` `H` | **-5.21%** | **-24.46%** |
| `foam` p99.9 | **+38.18%** (worse) | **-34.76%** (better) |
| hot winners removed | 0% | 100% |
| share of benefit reachable | 6.0% | — |

MEASURED (M89 column from facts 1186-1190, verified at source in
`M89-robustness-mask.md` including its sign convention). **The election-side gate
delivers 4.70x the mean-disagreement benefit of the average-side mask on the same
stack, and reverses the sign of the tail effect.**

DERIVED: this is exactly what fact 1189 predicted. The average-side mask cannot
help a pixel whose *elected* frame is the contaminated one, because in a
selection the elected frame is the output. Down-weighting it in an average it
does not participate in changes nothing. The tail degradation M89 measured is the
signature of that: the mask perturbed the average at pixels whose winner was
fine, and left untouched the pixels whose winner was not.

**The specification targeted the wrong stage, the corpus now has the number both
ways, and the question is closed.**

---

## 7. Registered bars — what passed, what failed

### 7.1 Passed

- **G0 — faithfulness. PASS, exact.** Arm 0 reproduces
  `FocusStats::best_index` at **8250880/8250880 = 100.000000%** on `flowers-cpl`
  and `lead-1-cpl`, and **8241504/8241504** on `foam` and `coffee-bean`. Not
  "99.99%" — bit-exact, including tie-break order. §7.4 shows why registering it
  at exactly 100.000000% mattered.
- **G1 — placebo. PASS both halves, both arms.** §4.
- **G2 — the detail control. PASS.** Registered: top populated detail-SNR bin
  change rate < 10x the median populated bin, on `flowers-cpl`. Measured **5.84x**
  (arm S), **7.85x** (arm H). **It passes but not by much, and the raw per-bin
  rise is ~1194x across the populated range (8.79e-5 at bin 1.0 to 1.05e-1 at bin
  8.0) — which must be reported.** The evidence that this rise is contamination
  and not a generic detail response is the **G5 row, which is nearly flat**
  (1.23e-4 to 3.85e-4 across the same bins): a `z` field with the same marginal
  distribution but no spatial correspondence produces no detail gradient at all.
- **G3 — the sharp-frame guard. PASS by 258x.** §3. G3b unresolved.
- **G5 — the shuffled-`z` placebo. PASS.** Registered: shuffled `z` must not
  reduce `lead-1-cpl` speckle by >5%. It *increased* speckle (+357.60%). Stronger
  evidence than the registered form: G5 delivers **-2.34%** `H` against arm S's
  **-25.25%** (10.8x), and removes **6.65%** of hot winners against arm S's
  **100%**.
- **G4a — hot winners. PASS, and self-downgraded to worthless.** Registered as
  evidence for arm S and as a construction check for arm H. **That was wrong when
  I wrote it.** `w(|z| >= 8) = 0` makes the score `w*R = 0`, and `R` is a gradient
  magnitude and therefore non-negative, so **arm S also zeroes hot winners by
  construction.** The bar cannot fail for either arm and is evidence of nothing.
  Recorded rather than deleted.

### 7.2 FAILED — G4b, election speckle, and it failed in the wrong direction

Registered: *"the gate must reduce speckle by >= 20% on `lead-1-cpl` and on
`foam`, and must not increase it by more than 2% on `flowers-cpl`."*

| stack | arm H | arm S | registered |
| --- | --- | --- | --- |
| `lead-1-cpl` | **+201.10%** | **+326.29%** | <= -20% |
| `foam` | **+274.58%** | **+429.15%** | <= -20% |
| `flowers-cpl` | +0.17% | +0.72% | <= +2% (PASS) |

**The contaminated half failed by a wide margin and with the opposite sign from
the one predicted.** The clean half passed.

DERIVED diagnosis: speckle as I defined it — elected index differing from its 3x3
neighbourhood median by more than 5 frames — **penalises any election change
regardless of whether the substitution was correct.** When the gate rejects a
moved frame it must elect a *different* frame, and the replacement is generally
further from the local median than the contaminated winner was, because the
contaminated winner was itself a plausible depth. The metric measures churn, not
correctness. **G4b was a badly-designed bar and the milestone must not claim it
as evidence in either direction.**

MEASURED mitigating context, offered as context and not as a rescue: G5 produces
*more* speckle than the real gate (+357.60% `lead-1-cpl`, +485.17% `foam`) while
changing far fewer pixels. Per point of election changed:

| stack | arm S | arm G5 | ratio |
| --- | --- | --- | --- |
| `lead-1-cpl` | 13.44 | 60.30 | **4.49x** |
| `foam` | 35.00 | 85.13 | **2.43x** |

So the real gate's substitutions are 2.4-4.5x more spatially coherent than random
ones. **That does not convert G4b into a pass and I am not scoring it as one.**

### 7.3 FAILED — the rule-30 prediction

§0.6 predicted arm S changes `flowers-cpl`'s election at **less than half** arm
H's rate. **Measured: arm S changes it at 2.27x arm H's rate.** Falsified.
Mechanism in §5.4. The second half of §0.6 (G3b's limit landing between 1.5x and
4x realistic step) **did not resolve** because the limit was never reached.

### 7.4 The planted defects

Two plants, each restored from a SHA256-verified temp backup — never
`git checkout --`, which would revert to HEAD and destroy sibling agents'
uncommitted work in this shared tree.

**Plant 1 — inverted tie-break.** `robust.rs`'s
`score > cur || (score == cur && index < cur_index)` changed to `index >
cur_index`. This is the most load-bearing line in the module: it must match
`merge.rs::FocusStats::beats` exactly or arm 0 is not the shipped election.

- **3 of 14 unit tests failed** (`ties_go_to_the_lower_frame_index`,
  `soft_still_demotes_a_frame_that_wins_by_a_hair`,
  `soft_keeps_a_far_sharper_frame_under_a_partial_penalty_and_hard_does_not`).
- **G0 went red: 8250859/8250880 = 99.999745%** — a **21-pixel**, 2.5-parts-per-
  million defect, caught.

**MEASURED and worth generalising: G0 caught it only because it was registered at
exactly `100.000000%`.** Any bar written as "~100%", ">99.99%", or "matches the
shipped election" would have scored 99.999745% as a pass. The defect only
manifests on exact float ties, which are rare — and rarity is precisely why the
bar had to be exact.

**Plant 2 — silently disabled gate.** The harness fed a zero `z` field to arms H
and S instead of the real one. Result: `changed` **0.000000%**, hot-winner
reduction **+0.000%** (391971 -> 391971, i.e. none), `dH` **0.000%** on every
arm. Every benefit bar reads exactly null. **And the G5 placebo arm stayed
live** (5.71% changed, -2.21% `dH`), because it consumes the shuffled field —
so the harness distinguishes "gate disabled" from "gate working", not merely
"something changed".

Restoration verified by SHA256 on both files, followed by 14/14 unit tests and
G0 back to 100.000000%.

**A gotcha that nearly voided this check, recorded because it will recur:**
PowerShell `Copy-Item` **preserves the source file's `LastWriteTime`**. Restoring
`robust.rs` from a backup therefore gave it an mtime *older* than the sabotaged
build, and `cargo test` reported the **stale** 3-failure result as if nothing had
been restored. The file must be touched after restore before a rebuild can be
trusted.

### 7.5 The confound I found and closed myself

Not registered in §0; found while reading my own numbers. **The gate lowers the
tolerance band centre, which admits more frames into the average, which lowers
`H` by smoothing alone.** MEASURED: admitted frames rise +5.90% (`lead-1-cpl`),
**+14.71%** (`foam`), +0.007% (`flowers-cpl`).

G5 bounds it, because shuffled `z` raises `adm` the same way with no spatial
contamination information:

| stack | S `dH/dadm` | G5 `dH/dadm` | ratio |
| --- | --- | --- | --- |
| `flowers-cpl` | -152.000 | -2.000 | 76.00 |
| `lead-1-cpl` | -4.279 | -1.738 | **2.46** |
| `foam` | -1.663 | -0.338 | **4.92** |

**This is awkward and is reported as such: on the contaminated stacks the
shuffled-`z` placebo recovers a non-trivial share, and real `z` is only ~2.5-5x
better per unit of response sacrificed.** Partial mitigation (MEASURED): `H` is
not noise-dominated — arm 0's `H` on `foam` is 4.83 sigma against a
pure-noise expectation of 0.798 — which limits how much of the improvement
smoothing can account for.

A separate per-pixel invariant was added to check the instrument rather than the
gate: **`H` must be bit-identical to arm 0 at every pixel whose half-election
band centres are unchanged.** MEASURED: **0 violations across 15 checks**
(3 arms x 5 runs), over 5.6M-8.25M pixels each. My *first* version of this check
printed "NON-ZERO — instrument bug" everywhere; the bug was in the check
(comparing means over different pixel populations), not the instrument.

---

## 8. The contamination survey, normalised for detail-SNR

The orchestrator's point 3: a gate scored on raw disagreement ranks by detail
content. Each stack's per-bin fire rate is reweighted by a common reference
detail distribution (`flowers-cpl`, the measured-cleanest stack).

| stack | `\|z\|>8` % | raw fire % | **normalised fire %** | x placebo | `dH` % |
| --- | --- | --- | --- | --- | --- |
| `flowers-cpl` | 0.0003 | 0.1823 | 0.1824 | 1.0 | -1.06 |
| `lead-1-cpl` | 0.7509 | 24.2807 | **13.2407** | **72.6** | -25.25 |
| `foam` | 0.2852 | 12.2608 | **0.8227** | **4.5** | -24.46 |
| `coffee-bean` | 0.3632 | 20.1539 | 6.8814 | 37.7 | -30.91 |
| `coffee-bean` +gain | 0.2838 | 16.9779 | **0.6434** | **3.5** | -30.36 |

MEASURED. **`foam` falls 15x under normalisation (12.26% -> 0.82%): most of its
raw firing is its very high detail content, not motion.** `lead-1-cpl` remains
72.6x the placebo after normalisation and is unambiguously the worst stack. This
independently reproduces fact 1187's ordering and confirms the orchestrator's
instruction not to demonstrate on `foam`: had I done so I would have tuned on a
stack whose *normalised* contamination is 16x lower than the real worst case.

### 8.1 The ordering question (§0.7, and the orchestrator's point 5)

Fact 1188 records that mask-first and photometric-fit-first are different
pipelines and the corpus does not know which wins. **This gate assumes
photometric normalisation runs first.** I measured the size of that dependence
rather than only asserting it, using `coffee-bean` as an **attribution
cross-check and explicitly not as a benefit demonstration** (fact 1188: 56.8%
photometric; the credit there belongs to M91).

MEASURED: a crude per-frame gain fit removes **90.6%** of `coffee-bean`'s
detail-normalised firing (6.8814% -> 0.6434%), **but the gate's `H` benefit is
nearly identical either way** (-30.91% vs -30.36%).

DERIVED: **ordering matters enormously for attribution and barely at all for
benefit.** A uniform per-frame gain error shifts both split halves equally, so it
largely cancels in `H`. Consequence for M91: **the two stages will not
double-count on `H`, but they will double-count on any contamination-rate
statistic**, and a combined report must fit gain first or it will credit the gate
with M91's work. G5 also weakens sharply after normalisation (6.09% -> 1.80%
changed, -4.01% -> -1.03% `dH`), i.e. the placebo's residual effect is itself
partly photometric.

---

## 9. Limits — what could make this wrong

1. **G3's ground truth is synthetic, and synthetic in a specific way.** Every
   frame derives from one real frame, so the frames share a single noise
   realisation modulated by blur. That is why `z^2` reads 1.69 rather than
   0.9897. I argue in §2.3 that this cuts conservative, but *argue* is the right
   verb: a stack of genuinely independent captures could in principle put more
   `z` mass on the sharp frame than my construction does.
2. **G3 tests defocus-vs-gate. It does not contain motion.** It proves the gate
   does not remove sharp frames; it does not prove the gate removes the right
   frames. Those are different claims and only the first is established here.
3. **The admitted-count confound (§7.5) is bounded, not eliminated.** Real `z` is
   2.46-4.92x better than shuffled `z` per admitted frame. That is a real margin
   and it is not an overwhelming one.
4. **G4b failed and I have no working spatial-coherence metric.** Speckle
   measures churn. The claim "the gate produces a better depth map" is
   **unsupported by this milestone**; only "lower split-half disagreement" is
   supported.
5. **`H` inherits M89's caveats**: a ~60% floor from election ambiguity and a
   detail confound. It is a continuity metric against fact 1189, not a proxy for
   output quality. **No milestone has yet measured what any of this does to a
   rendered image a human looks at.**
6. **Four stacks, one camera body, three ISOs.** No stack above ISO 1000, none
   below the profile's `base_iso` except `coffee-bean` which is clamped.
7. **The gate has never run inside `merge.rs`.** It is validated as a
   standalone fold that reproduces the shipped election exactly (G0). Porting it
   is a further step with its own failure modes.
8. **`w`'s knees at 4 and 8 sigma are inherited from fact 1186 and were never
   swept here.** They are not tuned to this milestone's data, which is a
   virtue for transfer, but nobody has measured whether they are *right* for the
   election. Discipline 590 warns about fitted constants; these are inherited
   constants, which is a different but not zero risk.
9. **`DEFAULT_GATE` was deliberately untouched** (question 90 is open). Every
   number here is at gate 4, tolerance 0.086063. The gate's benefit may interact
   with that setting and this milestone does not know how.

---

## 10. Candidate facts for the fold

Numbered `P1...` per rule 28. Deltas only, per rule 44 — these do not restate
facts 1186-1190.

**P1 (MEASURED).** An election-side robustness gate that demotes each frame's
focus response by fact 1186's noise-normalised weight cuts split-half
disagreement by 25.25% on `lead-1-cpl` and 24.46% on `foam`, which is 4.70x the
average-side mask's 5.21% on the same stack, and it improves `foam`'s p99.9 tail
by 34.76% where the mask degraded it by 38.18% — closing fact 1189's
election-versus-average question in favour of the election.

**P2 (MEASURED).** On a synthetic through-focus stack with known ground truth,
the gate rules the correct sharp winner ineligible at 0.0194% of pixels against a
pre-registered failure threshold of 5%, and at 0.0000% of the highest-detail
pixels for every focus step at which the ungated election itself succeeds — so
the sharp-frame hazard that governed the milestone's design does not materialise.

**P3 (MEASURED).** The fourth-difference disagreement statistic's mean `z^2`
moves only 1.60% across a 60x change in synthetic focus step and agrees to four
decimal places between a low-contrast flower and a high-contrast text target,
which is structural evidence that it reads noise-normalised disagreement rather
than defocus or scene contrast.

**P4 (DERIVED).** The election gate is *safest where the product cares most*: the
rate at which it removes the correct sharp frame is 0.0000% in the top detail-SNR
bin against 0.0142% globally, because high-detail pixels have an unambiguous
focus peak whose winner survives demotion while low-detail pixels are elected
near-arbitrarily.

**P5 (MEASURED, falsifying a registered prediction).** Soft demotion
(`argmax w*R`) is *more* aggressive than a hard eligibility gate
(`argmax R over w >= 0.5`), changing 2.27x as many elections on a clean stack,
because it perturbs the entire `4 < |z| < 5.172` band that the hard gate leaves
untouched — the opposite of the milestone's registered rule-30 prediction.

**P6 (MEASURED, a failed bar).** Election speckle — elected index differing from
its 3x3 neighbourhood median by more than 5 frames — is **not** a valid metric for
a robustness gate: the gate *increases* it by 201-429% on contaminated stacks
because the metric penalises any substitution regardless of correctness, and a
milestone registering a spatial-coherence bar needs a metric that can tell a
correct substitution from a wrong one.

**P7 (MEASURED).** `foam`'s raw election-gate firing rate falls 15x under
detail-SNR normalisation (12.26% to 0.82%) while `lead-1-cpl` remains 72.6x the
clean-stack placebo, so most of `foam`'s apparent contamination is its detail
content and any robustness result demonstrated on `foam` alone is measuring
texture.

**P8 (MEASURED/DERIVED).** A per-frame gain fit removes 90.6% of `coffee-bean`'s
detail-normalised gate firing but changes the gate's split-half benefit by only
0.55 percentage points (-30.91% to -30.36%), so the ordering of a robustness
stage against a photometric fit matters enormously for *attribution* and almost
not at all for *benefit* — a uniform gain error shifts both split halves equally
and largely cancels.

**P9 (MEASURED).** A robustness election can be built as a commutative,
associative, O(1)-per-pixel fold that reproduces `FocusStats::best_index` at
exactly 100.000000% of pixels in its ungated arm across four stacks and never
fires its fallback, so the gate costs no memory scaling in frame count and
preserves arbitrary worker partitioning.

**P10 (MEASURED).** A faithfulness bar registered at exactly `100.000000%`
detected a planted tie-break inversion that altered only 21 of 8,250,880 pixels
(2.5 ppm); any bar phrased as "~100%" or ">99.99%" would have scored the
sabotaged build as a pass.

**P11 (MEASURED, awkward).** A shuffled-`z` placebo — same marginal distribution,
no spatial correspondence — still recovers 2.34% of the 25.25% split-half benefit
on `lead-1-cpl`, so real contamination information is only 2.46-4.92x better than
noise per admitted frame, and any robustness benefit measured through split-half
disagreement must be normalised by the admitted-frame count it buys.

**P12 (MEASURED).** PowerShell `Copy-Item` preserves the source file's
`LastWriteTime`, so restoring a file from a backup can leave `cargo` treating a
stale build as fresh — a planted-defect restore must touch the file before the
rebuild, or the verification run silently re-reports the sabotaged result.

### Proposed disciplines

**D-a.** When a guard bar's global rate looks acceptable, stratify it by the
covariate that determines whether the guarded failure *matters* before accepting
it — M93's 0.0194% global sharp-frame gating rate was only trustworthy once it
was shown to be 0.0000% in the top detail bin, and the stratification inverted
the expected direction of the hazard.

**D-b.** A spatial-coherence bar must be able to distinguish a correct
substitution from an incorrect one; a metric that scores *change* rather than
*correctness* will fail in the wrong direction and cannot be interpreted, as
M93's speckle bar did at +201% to +429%.

---

## 11. Status / Changes / Verified / Not verified / Notes

**Status: complete. The gate is built, tested, and recommended to ship (arm S).
Two registered bars failed (§7.2, §7.3) and one passed for the wrong reason
(§7.1, G4a); all three are reported rather than dropped, and the ship
recommendation survives them.**

**Changes** — new files only; no existing file was modified:

- `crates/strehl-core/src/robust.rs` — the gate. Dependency-free (zero `crate::`
  references), 14 unit tests, clippy clean at `-D warnings`.
- `crates/strehl-cli/examples/m93-election.rs` — the measurement harness.
  Modes `gate <DIR> [--limit N] [--gate G] [--photonorm]` and
  `synth <DIR> [--frames N] [--crop N]`.
- `experiments/M93-election/` — outputs and `src/normalise.py`.
- `docs/research/M93-election-gate.md` — this report.

**Verified**

- G0 exact at 100.000000% on 4 stacks / 5 runs; fallback fired 0 times.
- 14/14 unit tests; clippy clean on `strehl-core` and on the example.
- Two planted defects, both caught; both restored from SHA256-verified backups.
- Post-lint-fix output **byte-identical** by SHA256 to the pre-fix baseline
  (`966406E4AE7766B4D40EB0327CCD0DD077C1875753711F5FC281E08DDB4B448E`), so the
  clippy cleanup of `loo_residual_kernel` and `box_mean` is provably
  semantics-free.
- Per-pixel `H` invariant: 0 violations across 15 checks.
- `foam` hot-winner rate 4.782246%, independently reproducing fact 1189.

**Not verified**

- The gate has never run inside `merge.rs` (§9.7).
- No rendered-image comparison; `H` is a proxy (§9.5).
- G3b's operating limit was never reached (§3.3).
- Whether the `w` knees at 4/8 sigma are right *for the election* (§9.8).
- Interaction with `DEFAULT_GATE` (§9.9).

**Notes**

- `lib.rs` was **not** edited. Discipline 588. The one-line patch is §12.
- No file owned by M85, M86, M87, M90 or M91 was touched. `merge.rs`,
  `through_focus.rs`, `noise.rs` and `profile.rs` were read only.
- `D:\personal\macro` and `D:\macro-dark-frames` were read-only throughout.
- Nothing was pushed.

---

## 12. The wiring patch, verbatim

`robust.rs` needs **no body edits** to be ported: it has zero `crate::`
references by construction, so `#[path]` inclusion (how it is exercised today)
and `pub mod` registration are equivalent. **The entire port is one line.**

**File:** `crates/strehl-core/src/lib.rs`

**Insertion point:** between the existing line 23 `pub mod profile;` and the
existing line 24 `pub mod stack;`, preserving the alphabetical order of the
block.

**Context before:**

```rust
pub mod plane;
pub mod profile;
pub mod stack;
pub mod through_focus;
```

**Context after:**

```rust
pub mod plane;
pub mod profile;
pub mod robust;
pub mod stack;
pub mod through_focus;
```

**The added text, on its own line, exactly:**

```rust
pub mod robust;
```

After applying, `crates/strehl-cli/examples/m93-election.rs` may optionally drop
its

```rust
#[path = "../../strehl-core/src/robust.rs"]
#[allow(dead_code)]
mod robust;
```

in favour of `use strehl_core::robust;`. **That is not required and should not be
done in the same commit as the `lib.rs` line** — the `#[path]` form keeps the
example self-contained and compiling either way, which is what allowed it to be
built and tested tonight without touching a shared registration point.

### Where the gate should live when integrated

`RobustElection` is a drop-in peer of `FocusStats` in `merge.rs`'s pass one. The
integration a later milestone needs:

1. Pass one already computes the regularised focus response per frame. It must
   *additionally* be given the `z` field for that frame, which requires a
   5-frame ring of decoded planes plus the `noise`/`profile` lookup — the
   harness's `z_at` is the reference implementation and carries fact 608's
   per-frame gain correctly.
2. Substitute `RobustElection::fold` for `FocusStats::update`, and
   `RobustElection::absorb` for `FocusStats::absorb`. Both signatures preserve
   commutativity and associativity, so
   `pass_one_elects_the_highest_response_and_is_order_independent` should pass
   unchanged.
3. Pass two must centre its admission band on `winner_response()` — the **raw**
   `R`, not the gated score `w*R` — or the band width changes with the weight.
   This is the one place a naive port will silently go wrong.

**What the library does not yet have:** a frame-window abstraction. The gate
needs a 5-frame ring buffer of decoded, photometrically-normalised planes to form
`z`, and `merge.rs` currently streams one frame at a time. That ring is the only
genuinely new infrastructure required, and it is also what M91's per-frame
photometric fit will need, so it should be built once and shared rather than
twice.
