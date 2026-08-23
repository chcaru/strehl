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
//! `FOCUS_NOISE_SD = 0.015214` is a property of the **focus operator**, not of
//! the merge: it is the standard deviation of that operator's response to
//! unit-variance noise, after the operator's own box window and after the
//! merge's regulariser. Across seven textbook operators the true value spans
//! **10.4x** (fact 439: ring(1,3) 0.644 to sum-modified-Laplacian 6.680). A
//! contributed operator that inherits the host's constant while having a true
//! scale `k` times larger silently runs at effective gate `t/k`; at `k = 5.94`
//! an intended `--gate 1.0` becomes 0.168 and 87.8% of pixels fall back to a
//! single frame instead of the intended 41.7%. Fact 438: **every such case is
//! indistinguishable from the log, the exit code, and the calibration block.**
//!
//! It is not hypothetical. Facts 509-511: this project's own first pending
//! operator change — `tenengrad-sq` at radius 11 replacing `|grad|` at radius
//! 13 — moves the constant by `k = 1.528`, turning `--gate 1.0` into 0.654.
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
//! Fact 505 bounds the cost at ~1.7 ms per stage; [`CalibrationPlan`] documents
//! what this crate actually measured, which is larger, and why.
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
