//! **The host measures the plugin. It does not ask the plugin to declare
//! anything.**
//!
//! This module is workstream E §F5.3 option A, and SYNTHESIS fact 502. The
//! whole of it is one idea: the host already owns a noise plane, the operator's
//! window, its own regulariser and the sigma normalisation, so it can run any
//! candidate operator through its own configuration at registration and read
//! the standard deviation off. Then
//!
//! ```text
//! tol = t * sqrt(2) * calibrate(op, cfg)
//! ```
//!
//! is correct by construction for **any** operator at **any** window under
//! **any** regulariser, and `--gate` becomes the first genuinely dimensionless
//! number in this program.
//!
//! # The configuration is the whole difficulty
//!
//! Getting the *arithmetic* right is trivial. Getting the *configuration* right
//! is what M43 got wrong the first time, and it cost 24.26%:
//!
//! - the operator runs through its **own** window and then the **host's**
//!   regulariser, in that order — fact 500;
//! - the plane is unit-variance white Gaussian noise, under a noise model whose
//!   luma sigma is 1, so the normaliser is exercised without rescaling;
//! - a margin of `stencil + 1 + window + regulariser` is discarded from every
//!   edge, because the box filter is replicate-clamped and the border is not
//!   stationary;
//! - the standard deviation is the **sample** one, `ddof = 1`, taken per seed
//!   and averaged across seeds — never pooled across seeds, which would fold
//!   the between-seed spread into the estimate.
//!
//! Every one of those is a choice that can be made differently and defensibly,
//! which is exactly why [`self_check`] exists and why it checks **two** targets
//! rather than one (discipline 257, fact 501).
//!
//! # Cost
//!
//! Fact 505 bounds this at **~1.7 ms per stage** for a 512x512 plane, derived
//! from the merge's own measured pass-one time. That bound is per seed; the
//! host default runs twelve of them, and [`CalibrationPlan::host_default`]
//! documents the trade.

use strehl_core::merge::FOCUS_NOISE_SD;
use strehl_core::plane::PlaneGeometry;
use strehl_core::through_focus::FINE_FOCUS_NOISE_SD;

use crate::field::{FieldConfig, FieldWorkspace};
use crate::measure::FocusMeasure;
use crate::reference::Tenengrad;
use crate::rng::{CRATE_SEEDS, NoiseSource, unit_sigma_model};

/// Minimum number of interior samples a calibration plane must yield.
///
/// `merge.rs`'s own measurement asserts the same floor. It is not about
/// sampling error — the interior pixels are heavily correlated, so ~219,000 of
/// them are worth about 118 independent measurements — it is a guard against
/// silently calibrating on a plane that the margin has almost entirely eaten.
const MIN_INTERIOR_SAMPLES: usize = 10_000;

/// Largest relative standard error at which a calibration is allowed to stand.
///
/// Above this the band any conformance check could draw is wide enough to admit
/// anything, and the measurement has no power. `merge.rs` uses the same 5%.
const MAX_RELATIVE_SEM: f64 = 0.05;

/// How many standard errors a target may sit from the measurement before
/// [`self_check`] refuses.
///
/// Derived, not picked: the crate's own two measurements use exactly this form
/// (`|measured - declared| / sem < 4`), because a round *relative* tolerance
/// would be picking whether the test passes — the estimate's own relative error
/// is near `1/sqrt(2(n-1))` in the number of *independent* supports, which is
/// about 6.5% for one seed at 512x512.
const SELF_CHECK_SEM_LIMIT: f64 = 4.0;

/// What to measure over. Every field here is a **named choice**; rule 24 says
/// a verifier must re-choose rather than re-compute, so they are all reachable.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CalibrationPlan {
    /// Side of the square calibration plane, in plane pixels.
    pub side: usize,
    /// Seeds to average over. One per plane.
    pub seeds: Vec<u64>,
    /// Which noise source fills the plane.
    pub source: NoiseSource,
}

impl CalibrationPlan {
    /// 512x512, the twelve seeds `merge.rs` measures over, SplitMix64 into
    /// Box-Muller.
    ///
    /// **512 is not arbitrary and neither is 12.** `merge.rs` records that at
    /// 192x192 this measurement reads 10% low, because a sample standard
    /// deviation over a region only a few supports across subtracts a mean that
    /// is itself correlated with the samples; 384 gives `0.015277 +/- 0.000223`
    /// and 512 gives `0.015214 +/- 0.000075`, a difference of 0.27 standard
    /// errors, so the bias is spent by 384 and 512 is kept for the tighter
    /// interval. 512 is also the plane size fact 505's ~1.7 ms cost bound is
    /// derived for.
    #[must_use]
    pub fn host_default() -> Self {
        Self {
            side: 512,
            seeds: CRATE_SEEDS.to_vec(),
            source: NoiseSource::SplitMixBoxMuller,
        }
    }

    /// The reference instrument's configuration: 2048x2048, 8 seeds.
    ///
    /// M43's Python model at this setting reads `FOCUS_NOISE_SD` **+0.47%** and
    /// `FINE_FOCUS_NOISE_SD` **+0.20%**. It is roughly 10x the work of
    /// [`host_default`](Self::host_default) and exists so that the two can be
    /// compared — a constant that moves between them is a constant whose
    /// finite-region bias is not yet spent.
    #[must_use]
    pub fn reference() -> Self {
        Self {
            side: 2048,
            seeds: CRATE_SEEDS[..8].to_vec(),
            source: NoiseSource::SplitMixBoxMuller,
        }
    }

    /// The same plan with a different noise source. The cheapest available
    /// re-choice (rule 24).
    #[must_use]
    pub fn with_source(mut self, source: NoiseSource) -> Self {
        self.source = source;
        self
    }

    /// The same plan at a different plane size.
    #[must_use]
    pub fn with_side(mut self, side: usize) -> Self {
        self.side = side;
        self
    }

    fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: self.side,
            height: self.side,
        }
    }
}

/// A host-measured noise scale for one operator under one field configuration.
///
/// # There is no public constructor, and that is the point
///
/// Every field is private and the only way to obtain one of these is
/// [`calibrate`]. A plugin therefore has no way to supply, override, default or
/// fall back to a noise constant — **fault 5 of workstream E §F4.6 is not
/// detectable here, it is unrepresentable.** That is the difference between
/// option A and option B, and it is a property of this type rather than of any
/// test.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Calibration {
    response_sd: f32,
    sem: f32,
    mean_response: f32,
    seeds: u32,
    interior_samples: u32,
    margin: u32,
    side: u32,
}

impl Calibration {
    /// The standard deviation of this operator's response to unit-variance
    /// noise, through this host's configuration. The quantity the gate is
    /// denominated in.
    #[must_use]
    pub fn response_sd(&self) -> f32 {
        self.response_sd
    }

    /// Standard error of [`response_sd`](Self::response_sd) across seeds.
    #[must_use]
    pub fn sem(&self) -> f32 {
        self.sem
    }

    /// `sem / response_sd`.
    #[must_use]
    pub fn relative_sem(&self) -> f32 {
        self.sem / self.response_sd
    }

    /// Mean of the response over the interior, averaged across seeds.
    ///
    /// Reported because it is the **structural** check on the operator chain:
    /// a silent rescale moves it by orders of magnitude while leaving the
    /// standard deviation looking plausible. For `|grad|` it must be the
    /// Rayleigh mean `0.125 * sqrt(12) * sqrt(pi/2) = 0.5427`, since no box
    /// mean moves a mean.
    #[must_use]
    pub fn mean_response(&self) -> f32 {
        self.mean_response
    }

    #[must_use]
    pub fn seeds(&self) -> u32 {
        self.seeds
    }

    /// Interior samples per seed, after the margin was discarded.
    #[must_use]
    pub fn interior_samples(&self) -> u32 {
        self.interior_samples
    }

    /// Margin discarded from every edge.
    #[must_use]
    pub fn margin(&self) -> u32 {
        self.margin
    }

    /// Side of the calibration plane.
    #[must_use]
    pub fn side(&self) -> u32 {
        self.side
    }

    /// `response_sd` as a multiple of the host's compiled-in
    /// [`FOCUS_NOISE_SD`] — fact 439's `k`.
    ///
    /// A plugin that inherited the host constant while having this `k` would
    /// run at an effective gate of `1 / k`.
    #[must_use]
    pub fn k_against_host_constant(&self) -> f32 {
        self.response_sd / FOCUS_NOISE_SD
    }
}

/// Why a calibration was refused.
#[derive(Debug, thiserror::Error, PartialEq)]
pub enum CalibrationError {
    #[error(
        "calibration plane {side}x{side} leaves only {samples} interior samples \
         after a margin of {margin}; at least {min} are needed"
    )]
    PlaneTooSmall {
        side: usize,
        margin: usize,
        samples: usize,
        min: usize,
    },
    #[error("calibration needs at least two seeds to have a standard error, got {0}")]
    TooFewSeeds(usize),
    #[error(
        "operator `{id}` responded with a standard deviation of {sd:e} to unit noise; \
         a response that does not vary cannot denominate a gate"
    )]
    DegenerateResponse { id: String, sd: f32 },
    #[error("operator `{id}` produced a non-finite response to unit noise")]
    NonFiniteResponse { id: String },
    #[error(
        "operator `{id}` calibrated to {sd:e} with a relative standard error of \
         {rel_sem:.4} across {seeds} seeds; above {max:.2} the measurement has no \
         power. Add seeds or enlarge the plane."
    )]
    NoPower {
        id: String,
        sd: f32,
        rel_sem: f64,
        seeds: usize,
        max: f64,
    },
}

/// **Measure an operator's noise scale.** The host-side half of the contract.
///
/// Runs `op` over `plan.seeds.len()` planes of unit-variance white Gaussian
/// noise, through the operator's own window, its normaliser and `cfg`'s
/// regulariser, and returns the standard deviation of the stationary interior.
///
/// # Errors
///
/// Refuses rather than returning a number it does not believe: see
/// [`CalibrationError`]. In particular a **constant-returning operator**
/// (workstream E §F4.6 fault 2 — "confident and wrong", which confluence
/// provably cannot catch) is refused here as
/// [`CalibrationError::DegenerateResponse`], which was not one of the things
/// this design was built to do.
pub fn calibrate(
    op: &dyn FocusMeasure,
    cfg: FieldConfig,
    plan: &CalibrationPlan,
) -> Result<Calibration, CalibrationError> {
    if plan.seeds.len() < 2 {
        return Err(CalibrationError::TooFewSeeds(plan.seeds.len()));
    }
    let geom = plan.geometry();
    let margin = cfg.calibration_margin(op);
    let interior_side = plan.side.saturating_sub(2 * margin);
    let samples = interior_side * interior_side;
    if samples < MIN_INTERIOR_SAMPLES {
        return Err(CalibrationError::PlaneTooSmall {
            side: plan.side,
            margin,
            samples,
            min: MIN_INTERIOR_SAMPLES,
        });
    }

    let noise = unit_sigma_model();
    let mut ws = FieldWorkspace::new(geom);
    let mut plane = vec![0.0f32; geom.pixels()];
    let mut sds: Vec<f64> = Vec::with_capacity(plan.seeds.len());
    let mut means: Vec<f64> = Vec::with_capacity(plan.seeds.len());

    for seed in &plan.seeds {
        plan.source.fill(*seed, &mut plane);
        let field = ws.run(op, cfg, &plane, &noise);
        let (mean, sd) = interior_moments(field, geom, margin);
        if !mean.is_finite() || !sd.is_finite() {
            return Err(CalibrationError::NonFiniteResponse { id: op.id().into() });
        }
        means.push(mean);
        sds.push(sd);
    }

    let n = sds.len() as f64;
    let sd = sds.iter().sum::<f64>() / n;
    let mean = means.iter().sum::<f64>() / n;
    // Spread ACROSS seeds, not within a plane: neighbouring interior responses
    // share almost all of their support, so a within-plane standard error would
    // claim hundreds of times more independence than the measurement has.
    let spread = sds.iter().map(|s| (s - sd).powi(2)).sum::<f64>() / (n - 1.0);
    let sem = (spread / n).sqrt();

    // `sd <= 0.0` catches a constant-returning operator (workstream E §F4.6
    // fault 2); the `is_finite` arm is belt-and-braces, since a NaN would have
    // to survive the per-seed check above to reach here.
    if sd <= 0.0 || !sd.is_finite() {
        return Err(CalibrationError::DegenerateResponse {
            id: op.id().into(),
            sd: sd as f32,
        });
    }
    let rel_sem = sem / sd;
    if rel_sem >= MAX_RELATIVE_SEM {
        return Err(CalibrationError::NoPower {
            id: op.id().into(),
            sd: sd as f32,
            rel_sem,
            seeds: plan.seeds.len(),
            max: MAX_RELATIVE_SEM,
        });
    }

    Ok(Calibration {
        response_sd: sd as f32,
        sem: sem as f32,
        mean_response: mean as f32,
        seeds: plan.seeds.len() as u32,
        interior_samples: samples as u32,
        margin: margin as u32,
        side: plan.side as u32,
    })
}

/// Mean and **sample** standard deviation over the stationary interior.
fn interior_moments(field: &[f32], geom: PlaneGeometry, margin: usize) -> (f64, f64) {
    let mut vals: Vec<f64> =
        Vec::with_capacity((geom.width - 2 * margin) * (geom.height - 2 * margin));
    for y in margin..geom.height - margin {
        for x in margin..geom.width - margin {
            vals.push(f64::from(field[y * geom.width + x]));
        }
    }
    let n = vals.len() as f64;
    let mean = vals.iter().sum::<f64>() / n;
    let var = vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (n - 1.0);
    (mean, var.sqrt())
}

/// One arm of [`self_check`].
#[derive(Debug, Clone, PartialEq)]
pub struct TargetCheck {
    pub label: &'static str,
    /// The constant the crate declares.
    pub target: f32,
    /// What this calibrator measured.
    pub measured: f32,
    pub sem: f32,
    /// `|measured - target| / sem`.
    pub deviation_sem: f64,
    /// `(measured - target) / target`.
    pub relative_deviation: f64,
    pub passed: bool,
}

/// The result of the two-target instrument check.
#[derive(Debug, Clone, PartialEq)]
pub struct SelfCheck {
    /// `|grad|` at w13 **with** the r8 regulariser, against `FOCUS_NOISE_SD`.
    pub coarse: TargetCheck,
    /// `|grad|` at w2 **without** the regulariser, against
    /// `FINE_FOCUS_NOISE_SD`.
    pub fine: TargetCheck,
}

/// The instrument refused to report.
#[derive(Debug, thiserror::Error)]
pub enum SelfCheckError {
    #[error("calibrating the {arm} target failed: {source}")]
    Calibration {
        arm: &'static str,
        #[source]
        source: CalibrationError,
    },
    #[error(
        "two-target calibration FAILED (discipline 257): {failures}. The pattern of \
         pass and fail localises the fault to what the two configurations differ in \
         — which is the regulariser. Refusing to calibrate anything else."
    )]
    Failed {
        failures: String,
        check: Box<SelfCheck>,
    },
}

/// **Validate the calibrator against both constants this crate measures
/// in-house, each in its own configuration.**
///
/// Discipline 257, and it exists because it already fired once. M43's first
/// instrument modelled the coarse field *without* the regulariser: it matched
/// `FINE_FOCUS_NOISE_SD` to **+0.20%** and read **+24.26%** high against
/// `FOCUS_NOISE_SD`. One target passing and one failing localises the fault to
/// the single thing the two configurations differ in, which was the bug. **A
/// one-target calibration would have been tuned into agreement** and everything
/// built on it would have been silently wrong by a quarter.
///
/// The two configurations differ in *two* known ways — window radius 13 vs 2,
/// and regulariser present vs absent — which is what makes the pattern
/// diagnostic rather than merely redundant.
///
/// # Errors
///
/// Refuses if either target misses by more than four standard errors, or if
/// either arm cannot be calibrated at all.
pub fn self_check(plan: &CalibrationPlan) -> Result<SelfCheck, SelfCheckError> {
    let coarse = one_target(
        "FOCUS_NOISE_SD",
        FOCUS_NOISE_SD,
        &Tenengrad::shipped(),
        FieldConfig::SHIPPED,
        plan,
    )?;
    let fine = one_target(
        "FINE_FOCUS_NOISE_SD",
        FINE_FOCUS_NOISE_SD,
        &Tenengrad::at_radius(strehl_core::focus::FINE_WINDOW_RADIUS),
        FieldConfig::BARE,
        plan,
    )?;

    let check = SelfCheck { coarse, fine };
    let mut failures = Vec::new();
    for arm in [&check.coarse, &check.fine] {
        if !arm.passed {
            failures.push(format!(
                "{} declares {:e}, measured {:e} +/- {:e} ({:+.2}%, {:.1} sem)",
                arm.label,
                arm.target,
                arm.measured,
                arm.sem,
                100.0 * arm.relative_deviation,
                arm.deviation_sem
            ));
        }
    }
    if failures.is_empty() {
        Ok(check)
    } else {
        Err(SelfCheckError::Failed {
            failures: failures.join("; "),
            check: Box::new(check),
        })
    }
}

fn one_target(
    label: &'static str,
    target: f32,
    op: &dyn FocusMeasure,
    cfg: FieldConfig,
    plan: &CalibrationPlan,
) -> Result<TargetCheck, SelfCheckError> {
    let cal = calibrate(op, cfg, plan)
        .map_err(|source| SelfCheckError::Calibration { arm: label, source })?;
    let deviation_sem =
        (f64::from(cal.response_sd()) - f64::from(target)).abs() / f64::from(cal.sem());
    let relative_deviation = (f64::from(cal.response_sd()) - f64::from(target)) / f64::from(target);
    Ok(TargetCheck {
        label,
        target,
        measured: cal.response_sd(),
        sem: cal.sem(),
        deviation_sem,
        relative_deviation,
        passed: deviation_sem < SELF_CHECK_SEM_LIMIT,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::measure::{Normalisation, Window};
    use crate::reference::{SumModifiedLaplacian, TenengradSquared};
    use strehl_core::focus::WINDOW_RADIUS;

    /// **The deliverable's central verification, and it is two-target by
    /// construction: it refuses to pass if either constant misses.**
    ///
    /// Rule 20 — inputs that make this fail, every one of them a mistake
    /// somebody has actually made in this repository:
    ///
    /// - applying the regulariser to the fine arm: fine reads ~0.0276 against a
    ///   target of 0.0904, a 3.3x miss (this is fact 500's error, inverted);
    /// - omitting it from the coarse arm: coarse reads **+24%** (this is
    ///   fact 501, verbatim);
    /// - normalising before windowing, a different `SIGMA_EPS`, a wrong margin,
    ///   or a lattice-structured RNG (which moved this constant 1.30x across
    ///   seeds when `merge.rs` tried an LCG).
    ///
    /// A single target could be matched by a wrong implementation with a
    /// compensating error, and in this repository one nearly was.
    #[test]
    fn the_calibrator_reproduces_both_in_crate_constants() {
        let plan = CalibrationPlan::host_default();
        let check = self_check(&plan).expect("two-target calibration must pass");

        println!(
            "coarse: crate {:e}  measured {:e} +/- {:e}  ({:+.3}%, {:.2} sem)",
            check.coarse.target,
            check.coarse.measured,
            check.coarse.sem,
            100.0 * check.coarse.relative_deviation,
            check.coarse.deviation_sem
        );
        println!(
            "fine:   crate {:e}  measured {:e} +/- {:e}  ({:+.3}%, {:.2} sem)",
            check.fine.target,
            check.fine.measured,
            check.fine.sem,
            100.0 * check.fine.relative_deviation,
            check.fine.deviation_sem
        );

        assert!(check.coarse.passed, "coarse target missed: {check:?}");
        assert!(check.fine.passed, "fine target missed: {check:?}");
        // And the band has to be narrow enough to mean something: 4 sem at a
        // relative sem of ~0.5% is +/-2%, which rejects fact 501's +24.26%,
        // fact 509's +52.8% and fact 510's +12.5% alike.
        let band =
            SELF_CHECK_SEM_LIMIT * f64::from(check.coarse.sem) / f64::from(check.coarse.target);
        assert!(
            band < 0.05,
            "the coarse acceptance band is +/-{:.2}%, too wide to reject a real \
             miscalibration",
            100.0 * band
        );
    }

    /// **Discipline 257's power, demonstrated rather than asserted.**
    ///
    /// Run the coarse arm in the *fine* arm's configuration — no regulariser —
    /// which is exactly the bug M43's first instrument had, and show that the
    /// coarse target fails while the fine target still passes. That asymmetric
    /// pattern is the diagnosis; a one-target harness would have seen only a
    /// number it could tune.
    #[test]
    fn dropping_the_regulariser_fails_the_coarse_target_and_not_the_fine_one() {
        let plan = CalibrationPlan::host_default();
        let wrong = one_target(
            "FOCUS_NOISE_SD",
            FOCUS_NOISE_SD,
            &Tenengrad::shipped(),
            FieldConfig::BARE, // the injected fault
            &plan,
        )
        .expect("the wrong configuration still calibrates, which is the problem");
        let right = one_target(
            "FINE_FOCUS_NOISE_SD",
            FINE_FOCUS_NOISE_SD,
            &Tenengrad::at_radius(strehl_core::focus::FINE_WINDOW_RADIUS),
            FieldConfig::BARE,
            &plan,
        )
        .expect("fine arm");

        println!(
            "unregularised coarse arm: {:e} against {:e} = {:+.2}%",
            wrong.measured,
            wrong.target,
            100.0 * wrong.relative_deviation
        );
        assert!(
            !wrong.passed,
            "omitting the regulariser must fail the coarse target; measured \
             {:e} ({:+.2}%)",
            wrong.measured,
            100.0 * wrong.relative_deviation
        );
        assert!(
            wrong.relative_deviation > 0.15,
            "M43 measured this fault at +24.26%; got {:+.2}%",
            100.0 * wrong.relative_deviation
        );
        assert!(right.passed, "the fine target must still pass: {right:?}");
    }

    /// A constant-returning focus measure — workstream E §F4.6 **fault 2**,
    /// "confident and wrong", which the document says confluence provably
    /// cannot catch — is refused at calibration.
    ///
    /// This was not a design goal. It falls out of measuring instead of
    /// declaring: a constant has no spread, and a scale of zero cannot
    /// denominate a gate.
    #[test]
    fn a_constant_returning_operator_is_refused() {
        struct ConfidentConstant;
        impl FocusMeasure for ConfidentConstant {
            fn id(&self) -> &str {
                "confident-constant"
            }
            fn stencil_radius(&self) -> usize {
                1
            }
            fn window(&self) -> Window {
                Window::Box { radius: 13 }
            }
            fn normalisation(&self) -> Normalisation {
                Normalisation::None
            }
            fn respond(&self, _luma: &[f32], _geom: PlaneGeometry, out: &mut [f32]) {
                out.fill(0.5);
            }
        }
        let err = calibrate(
            &ConfidentConstant,
            FieldConfig::SHIPPED,
            &CalibrationPlan::host_default(),
        )
        .unwrap_err();
        assert!(
            matches!(err, CalibrationError::DegenerateResponse { .. }),
            "got {err:?}"
        );
    }

    #[test]
    fn a_non_finite_operator_is_refused() {
        struct Nan;
        impl FocusMeasure for Nan {
            fn id(&self) -> &str {
                "nan"
            }
            fn stencil_radius(&self) -> usize {
                0
            }
            fn window(&self) -> Window {
                Window::None
            }
            fn normalisation(&self) -> Normalisation {
                Normalisation::None
            }
            fn respond(&self, _luma: &[f32], _geom: PlaneGeometry, out: &mut [f32]) {
                out.fill(f32::NAN);
            }
        }
        let err = calibrate(&Nan, FieldConfig::BARE, &CalibrationPlan::host_default()).unwrap_err();
        assert!(
            matches!(err, CalibrationError::NonFiniteResponse { .. }),
            "got {err:?}"
        );
    }

    #[test]
    fn a_plane_the_margin_eats_is_refused_rather_than_calibrated_on_a_sliver() {
        let plan = CalibrationPlan::host_default().with_side(64);
        let err = calibrate(&Tenengrad::shipped(), FieldConfig::SHIPPED, &plan).unwrap_err();
        assert!(
            matches!(err, CalibrationError::PlaneTooSmall { .. }),
            "got {err:?}"
        );
        let err = calibrate(
            &Tenengrad::shipped(),
            FieldConfig::SHIPPED,
            &CalibrationPlan {
                side: 512,
                seeds: vec![1],
                source: NoiseSource::SplitMixBoxMuller,
            },
        )
        .unwrap_err();
        assert!(
            matches!(err, CalibrationError::TooFewSeeds(1)),
            "got {err:?}"
        );
    }

    /// The structural anchor `merge.rs` uses: under unit luma noise the
    /// gradient magnitude is Rayleigh with scale `0.125 * sqrt(12)`, whose mean
    /// is 0.5427, and **no box mean moves a mean**.
    ///
    /// This is the check that catches the operator chain being wrong rather
    /// than merely noisy — the zero-gain trap moves it by three orders of
    /// magnitude while leaving the standard deviation looking plausible.
    #[test]
    fn the_calibration_mean_is_the_closed_form_rayleigh_mean() {
        let plan = CalibrationPlan::host_default();
        let rayleigh = 0.125 * 12f64.sqrt() * (std::f64::consts::PI / 2.0).sqrt();
        for cfg in [FieldConfig::SHIPPED, FieldConfig::BARE] {
            let cal = calibrate(&Tenengrad::shipped(), cfg, &plan).unwrap();
            let r = f64::from(cal.mean_response()) / rayleigh;
            assert!(
                (0.97..1.03).contains(&r),
                "mean {} is {r:.4}x the closed form {rayleigh:.4}",
                cal.mean_response()
            );
        }
    }

    /// **Rule 24: re-choose, not re-compute.** The two constants must survive a
    /// different generator, a different transform and a different plane size.
    ///
    /// The RNG is the choice point with a measured history of mattering:
    /// `merge.rs` records an LCG moving this constant **1.30x across seeds**.
    /// If any of these three re-choices moved the answer, the constant would be
    /// a property of the instrument rather than of the operator.
    #[test]
    fn the_constants_survive_re_choosing_the_generator_the_transform_and_the_plane() {
        let base = CalibrationPlan::host_default();
        let arms = [
            ("splitmix+box-muller @512", base.clone()),
            (
                "pcg32+box-muller @512",
                base.clone().with_source(NoiseSource::PcgBoxMuller),
            ),
            (
                "splitmix+irwin-hall @512",
                base.clone().with_source(NoiseSource::SplitMixIrwinHall),
            ),
            ("splitmix+box-muller @768", base.clone().with_side(768)),
        ];
        let mut coarse = Vec::new();
        let mut fine = Vec::new();
        for (label, plan) in &arms {
            let c = calibrate(&Tenengrad::shipped(), FieldConfig::SHIPPED, plan).unwrap();
            let f = calibrate(
                &Tenengrad::at_radius(strehl_core::focus::FINE_WINDOW_RADIUS),
                FieldConfig::BARE,
                plan,
            )
            .unwrap();
            println!(
                "{label:<26} coarse {:.6} ({:+.2}%)   fine {:.6} ({:+.2}%)",
                c.response_sd(),
                100.0 * (c.response_sd() / FOCUS_NOISE_SD - 1.0),
                f.response_sd(),
                100.0 * (f.response_sd() / FINE_FOCUS_NOISE_SD - 1.0),
            );
            coarse.push(f64::from(c.response_sd()));
            fine.push(f64::from(f.response_sd()));
        }
        for (label, vals, target) in [
            ("coarse", &coarse, f64::from(FOCUS_NOISE_SD)),
            ("fine", &fine, f64::from(FINE_FOCUS_NOISE_SD)),
        ] {
            for v in vals {
                let dev = (v - target) / target;
                assert!(
                    dev.abs() < 0.03,
                    "{label}: an arm read {v:.6} against {target:.6} ({:+.2}%); \
                     re-choosing the instrument must not move the constant by more \
                     than the between-seed spread",
                    100.0 * dev
                );
            }
        }
    }

    /// **Fault 5, and the proof that the measured constant tracks the operator
    /// rather than the host.**
    ///
    /// Rule 20 — this fails if `calibrate` ignored the operator (every `k`
    /// would be 1.000), if it returned the host constant (same), or if SML were
    /// accidentally implemented as the shipped operator. The shipped arm is the
    /// discriminator: it must read 1.000 in the *same* call that reads 6-7 for
    /// SML, so a calibrator that simply returned something large fails too.
    #[test]
    fn the_measured_constant_tracks_the_operator_not_the_host_default() {
        let plan = CalibrationPlan::host_default();
        let shipped = calibrate(&Tenengrad::shipped(), FieldConfig::SHIPPED, &plan).unwrap();
        let sml = calibrate(
            &SumModifiedLaplacian::at_radius(WINDOW_RADIUS),
            FieldConfig::SHIPPED,
            &plan,
        )
        .unwrap();
        let sq = calibrate(
            &TenengradSquared::at_radius(WINDOW_RADIUS),
            FieldConfig::SHIPPED,
            &plan,
        )
        .unwrap();

        println!(
            "shipped k = {:.4}   sml k = {:.4} (fact 439: 6.680)   tenengrad-sq k = {:.4} \
             (fact 439: 1.367)",
            shipped.k_against_host_constant(),
            sml.k_against_host_constant(),
            sq.k_against_host_constant()
        );

        assert!(
            (0.97..1.03).contains(&shipped.k_against_host_constant()),
            "the shipped operator must read k = 1 by construction, got {}",
            shipped.k_against_host_constant()
        );
        assert!(
            (5.5..8.0).contains(&sml.k_against_host_constant()),
            "SML must land near fact 439's 6.680, got {}",
            sml.k_against_host_constant()
        );
        assert!(
            (1.25..1.50).contains(&sq.k_against_host_constant()),
            "tenengrad-squared must land near fact 439's 1.367, got {}",
            sq.k_against_host_constant()
        );
    }
}
