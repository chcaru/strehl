# M107b — pre-registration for the lateral-CA correction unit

Written and committed **before** any measurement, per the standard `ed5a929` set for this
milestone. Bars L1–L6 and A1 are quoted verbatim in the report and scored as written. A bar
narrowed after seeing its number is recorded as failed, not as narrowed — that is what
happened to B3 in the parent milestone and it is the precedent I am holding myself to.

## What is being built

A self-contained, unwired unit in `crates/strehl-core/src/optics.rs`:

1. A **versioned optical-profile record** carrying `eps_R`/`eps_B`, the optical path they
   were measured on, the stacks they came from, the fit statistics, and the aperture and
   magnification at which they were measured.
2. A **pure correction function** composing a per-channel radial magnification into the
   `Similarity` the gather already applies.

**Nothing is wired.** `merge_cmd.rs` (M97) and `align_cmd.rs` (M85) are not touched.

## The claim that makes this cheap, stated before it is tested

`align.rs` applies `Similarity` as `z -> a*z + b` about a centre (`apply_at`). A radial
magnification by `1+eps` about a point `c` is **itself a Similarity**:
`z -> c + (1+eps)(z - c)`. Similarities are closed under composition, so the correction
should compose **exactly** into the existing transform — no second interpolation, no extra
pass, no extra kernel application.

**If that is false, I must report it and stop**, because a second interpolation would cost
more sharpness (facts 1373–1374, −0.2360 dex) than the fringing it removes.

## The optical-centre assumption, registered as an assumption

I assume the optical centre coincides with the plane centre already used by `apply_at`.
This is an **assumption, not a measurement**. It is registered here with the bound it
implies: a true centre displaced by `delta` sensels leaves a residual misregistration of
`eps * delta`. **I will compute the empirical bound on `delta`** from the parent fit's
residual rms (0.073 sensel) and `eps_R` and report it. If that bound is looser than 300
sensels I will say the assumption is not adequately constrained.

---

## Bars

### L1 — the zero null. **Byte-exact, not "within tolerance".**

> With `eps_R = eps_B = 0`, the correction must return a `Similarity` **bitwise identical**
> to its input, over >= 10 000 randomised transforms including negative zero, subnormals,
> very large and very small scales, and identity. **Expected: 0 of N differ in any bit.**
> **Falsifier: any single differing bit in any field.** An absent profile must likewise be a
> silent no-op on the same standard.

Scored on raw `f64::to_bits()`, not on `==` (which cannot distinguish `+0.0` from `-0.0`).

### L2 — the positive control. **Does the thing do what its name says?**

> Plant a known radial magnification `eps_plant` into a real red CFA plane, then re-fit with
> the parent milestone's own `e2_lateral` instrument. The **change** in fitted `eps` must
> recover `eps_plant`.
> **Expected: ratio recovered/planted in [0.90, 1.10].**
> **Falsifier: outside [0.80, 1.20], or the recovered sign is wrong.**

Planted at `eps_plant = -2000 ppm`, chosen to sit well above the parent fit's residual
(0.073 sensel) so a null result cannot be blamed on the measurement floor.

**L2-CTRL (interpolation-blur control).** Planting resamples the plane, and resampling
blurs. An ESF *position* estimate is first-order insensitive to symmetric blur, but I am
not assuming that. The fitted edge width `w` must change by **< 10 %** between planted and
unplanted. **If it changes by more, the position estimate may be blur-biased and L2 is not
interpretable** — I will report that rather than the ratio.

### L3 — in-sample correction. **Does it remove the real defect?**

> Applying the fitted `eps_R = -704.5 ppm` must reduce the gated median `|dR|` from its
> uncorrected **1.4274 sensel**.
> **Expected: <= 0.35 sensel (>= 75 % removed).**
> **Falsifier: > 0.70 sensel (less than half removed).**

### L4 — out-of-sample transfer. **The arm that can kill the profile idea.**

> Fit `eps_R` on one stack, apply to a *different* stack from the same optical path, and
> measure the reduction in gated median `|dR|`.
> **Expected: >= 60 % of the reduction the in-sample fit achieves on that same stack.**
> **Falsifier: < 30 %, or the correction increases `|dR|` on the held-out stack.**

Fact 52 is the standing warning that in-scene fits do not transfer. The orchestrator expects
lateral CA to transfer *because it is an optical constant rather than a scene property*.
**That expectation is exactly what this arm exists to falsify, and I am not assuming it.**

### L5 — green must be untouched. **The G1−G2 null must stay dead.**

> Green is the reference channel, so `eps_G = 0` by construction. The two green planes must
> therefore be **byte-identical** before and after correction, and the `G1−G2` radial fit
> must be unchanged from `R^2 = 0.0524`, `p = 0.7095`.
> **Expected: 0 differing bytes; fit statistics identical to all quoted digits.**
> **Falsifier: any differing byte, or any change in the fit.**

This is stronger than "the null stays insignificant": a correction that perturbs green at
all is reaching a channel it has no licence to touch.

### L6 — exact composition, no second interpolation.

> For randomised transforms and points, composing the correction into the `Similarity` and
> applying once must equal applying the transform and then scaling radially, to
> **<= 1e-12 relative**.
> **Expected: max relative discrepancy <= 1e-12.**
> **Falsifier: > 1e-9**, which would mean the correction is *not* a closed-form composition
> and would require its own resampling pass — in which case I stop and report that.

---

## A1 — the axial-offset model, which I am trying to kill rather than confirm

The orchestrator asks whether a **constant** per-channel frame offset is the right model for
the middle option, and flags the concern that the parent milestone reports `k_R - k_G` as a
**range** (−0.67…−1.07), not a constant. That range is *across stacks*; the question is
whether it is also structured *within* a stack.

> Within each stack, regress the per-pixel `k_R - k_G` on `k_G` (a depth proxy) and,
> separately, on image radius, over confident pixels only.
> **A constant offset is adequate if `R^2 < 0.10` on both regressions in all 5 stacks.**
> **A constant offset is the WRONG MODEL if `R^2 >= 0.30` on either regression with a
> consistent sign across stacks** — in which case I say so plainly before anyone builds it.
> Between 0.10 and 0.30 I report it as indeterminate and do not resolve it post hoc.

I have no prediction as to which. The depth regression is the one I expect to matter,
because axial CA is a longitudinal effect and the focus step is the depth axis.

**Confound registered in advance:** `k_R - k_G` and `k_G` are not independent — both contain
`k_G`, so regressing one on the other induces a **spurious negative slope** through shared
noise alone. I will therefore run the same regression on the `k_G1 - k_G2` null, which
carries that identical shared-noise structure and none of the chromatic signal. **The null's
`R^2` is the floor, and A1 is scored against the null, not against zero.** Without that
control the regression would confirm depth-dependence even if none existed.

---

## What would make me report failure

- L6 failing: the correction cannot compose, and the sharpness cost must then be measured
  rather than assumed.
- L4 failing: the profile does not transfer, and the pluggable-optics idea is wrong as
  applied to lateral CA.
- L2-CTRL failing: the instrument is blur-biased and L2/L3/L4 are uninterpretable.

Any of these gets reported as a failure, not narrowed into a pass.
