//! `strehl-plugin` — the contribution surface for focus measures, with the
//! **noise scale measured by the host at registration**.
//!
//! # The problem this crate exists to make unrepresentable
//!
//! The merge admits a frame into the per-pixel average when its focus response
//! is within `tol = t * sqrt(2) * FOCUS_NOISE_SD` of the peak, where `t` is the
//! user's `--gate`. Fact 436 verified that relation against the shipped binary
//! at five gates spanning 35x, with `tol/t` constant to 2.0e-6 — it is exactly
//! linear.
//!
//! **Fact 631 scopes what follows from that linearity, and the scoping matters
//! here more than anywhere else in the crate**, because the substitution is the
//! motivating argument. "An operator whose true SD is `k` times the constant
//! runs at `t/k`" is *exact* for the **same** operator rescaled — scaling the
//! operator and its constant by 7 moves 18 pixels in 8,236,816 — and **false
//! across genuinely different operators**, which move `n_eff` by up to 4.54x
//! and the winner map on **71.5%** of pixels. So `t/k` is the right way to
//! *price* a mis-calibration and the wrong way to *undo* one: no rescaling of
//! the gate reproduces a different operator's decisions. That does not weaken
//! the case for measuring the constant; it removes the only escape from it,
//! since a host that knew `k` still could not correct for it by moving the
//! gate.
//!
//! `FOCUS_NOISE_SD = 0.015214` is a property of the **focus operator**, not of
//! the merge: it is the standard deviation of that operator's response to
//! unit-variance noise, after the operator's own box window and after the
//! merge's regulariser. Across seven textbook operators the true value spans
//! **10.4x** (fact 439: ring(1,3) 0.644 to sum-modified-Laplacian 6.680;
//! `examples/calibration-survey` re-measures 10.27x on this crate's own path).
//! **Fact 635 scopes that span too**: it is partly a property of the stencil
//! constants written in this repository, and under one consistent convention it
//! is **2.12x** — see [`reference`] for what moves and what does not. A
//! contributed operator that inherits the host's constant while having a true
//! scale `k` times larger silently runs at effective gate `t/k`; at SML's
//! measured `k` = 6.68 an intended `--gate 1.0` becomes **0.150**, and **89.02%**
//! of pixels fall back to a single frame instead of the intended **41.66%**
//! (MEASURED, M58, `strehl merge` on 109MSDCF). Fact 438: **every such case is
//! indistinguishable from the log, the exit code, and the calibration block.**
//!
//! That illustration used to be written with `k` = 5.94, which is
//! `FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD`. **Fact 500 refuted that pair**: those
//! two constants are measured in different configurations, and the honest
//! same-configuration quantity is 1.815, so no operator reachable through this
//! crate's pipeline has `k` = 5.94 *from that derivation*. SML is used instead
//! because it is a real operator with a host-measured constant, and it prices
//! the seam higher than the mistake did.
//!
//! It is not hypothetical. Facts 509-511: this project's own first pending
//! operator change — `tenengrad-sq` at radius 11 replacing `|grad|` at radius
//! 13 — moves the constant by `k` = 1.528 **on this crate's path**. On the path
//! the change would actually land it moves by more, and by an amount nobody has
//! measured: fact 662 composes facts 583 and 632 to show that `strehl-cli` does
//! not depend on `strehl-plugin` at all, so the edit necessarily reaches
//! `strehl-core/src/focus.rs`, which has a single divide and no degree concept.
//! There, `k` = 1.528 **understates** by roughly the local sigma (8.6-24.6 DN on
//! this corpus). **The pending change is blocked, not calibrated** — question
//! 147 is where the path gets recorded. That this crate can price the edit on
//! its own path and the shipping binary cannot price it on *its* path is the
//! seam, restated as a fact about a commit that is waiting to land.
//!
//! Workstream E §F4's four plugin properties (P1 confluence, P2 sensitivity, P3
//! no residue, P4 calibrated fixture) all **pass** an operator with a wrong
//! noise constant. P4 asserts a peak *location*, and a wrong noise SD does not
//! move the peak — it changes the band width. That is fault 5 in §F4.6's table:
//! "NOTHING BELOW CATCHES IT". A missing contract, not a missing test.
//!
//! # The design: the host measures, the plugin does not declare
//!
//! [`FocusMeasure`] has **no method that reports a noise standard deviation**,
//! and [`Calibration`] has no public constructor. The only way to obtain one is
//! [`calibrate`], which runs the operator over synthetic unit-variance noise
//! through the host's own regulariser and takes the interior SD. An operator
//! carrying the wrong constant is therefore not merely detectable — there is
//! nothing to carry it in.
//!
//! Beyond making the fault unrepresentable, measuring rather than declaring is
//! forced by three further facts:
//!
//! - A declared constant is **under-determined in principle**. The value
//!   depends on the host's regulariser radius, which the plugin cannot know.
//!   Fact 500 is the proof by counterexample: this repository's own two
//!   constants, `FOCUS_NOISE_SD` (0.015214, measured *with* the regulariser)
//!   and `FINE_FOCUS_NOISE_SD` (0.090400, measured *without* it), are not the
//!   same kind of quantity and must never be divided by one another. The
//!   orchestrator made exactly that error and overstated a ratio by 3.27x.
//! - Changing `REGULARISER_RADIUS` would stale every declared constant in the
//!   ecosystem at once, with no way to detect the staleness. A measured one
//!   re-derives.
//! - It removes the parameter from the contract entirely, which is the only
//!   version in which `--gate` is genuinely dimensionless (see [`Gate`]).
//!
//! Fact 505 bounded the cost at ~1.7 ms per stage. **That bound is refuted and
//! its number must not be quoted**: fact 525 measured 5.02 ms per 512² plane
//! and 60.3 ms per registration, 2.95x and 35x the bound, and M58 re-measured
//! 4.98 ms and 59.73 ms on this crate's own probe. Fact 505's *conclusion*
//! survives — 60 ms once per operator per host start is not a cost worth
//! trading a correctness property for — but it survives on the measurement, not
//! on the derivation. [`CalibrationPlan`] documents what this crate actually
//! measured and why 12 seeds is where the cost goes.
//!
//! # Layout
//!
//! - [`measure`] — the [`FocusMeasure`] trait. Its *absence* of a `noise_sd`
//!   method is the design.
//! - [`field`] — [`FieldConfig`] and [`FieldWorkspace`]: the exact pipeline
//!   `respond -> aggregate -> normalise -> regularise`, bit-identical to
//!   [`strehl_core::focus::FocusField::compute`] followed by the merge's
//!   regulariser.
//! - [`rng`] — the synthetic noise sources. Which generator is used is
//!   load-bearing and measured, not incidental; see [`rng::NoiseSource`].
//! - [`calibrate`] — the host-side measurement, and the two-target self-check.
//! - [`reference`] — the seven operators of fact 439, as worked examples and as
//!   the fault-5 subjects.
//! - [`registry`] — calibrated operators in, a dimensionless [`Gate`] out.
//!
//! # Example
//!
//! ```no_run
//! use std::sync::Arc;
//! use strehl_plugin::{CalibrationPlan, FieldConfig, Registry, reference::SumModifiedLaplacian};
//!
//! // The registry refuses to exist unless the calibrator reproduces both of
//! // this repository's measured constants first.
//! let mut reg = Registry::new(FieldConfig::SHIPPED, CalibrationPlan::host_default())?;
//!
//! // A third-party operator with a 6.7x different noise scale. It declares
//! // nothing; the host measures it on the way in.
//! reg.register(Arc::new(SumModifiedLaplacian::at_radius(13)))?;
//! let sml = reg.get("sml-w13").unwrap();
//!
//! // The gate is now in units of the operator's own noise.
//! assert_eq!(sml.gate(1.0).tolerance(), std::f32::consts::SQRT_2);
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```

pub mod calibrate;
pub mod field;
pub mod measure;
pub mod reference;
pub mod registry;
pub mod rng;

pub use calibrate::{
    Calibration, CalibrationError, CalibrationPlan, SelfCheck, SelfCheckError, TargetCheck,
    calibrate, self_check,
};
pub use field::{FieldConfig, FieldWorkspace};
pub use measure::{FocusMeasure, Normalisation, Window};
pub use registry::{Gate, Registered, RegistrationError, Registry};
pub use rng::{NoiseSource, unit_sigma_model};
