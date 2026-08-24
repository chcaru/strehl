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

*(to be written after the measurement)*
