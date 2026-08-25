//! The estimation merge — **the thing `strehl` exists to build.**
//!
//! [`stack::Selection`](crate::stack) is the named baseline: per-pixel argmax.
//! On **this pipeline's** operator — the normalised Tenengrad that actually
//! ships — M39 measured it at **1.0678x unregularised and 1.0739x regularised**
//! against one unstacked frame (fact 343). Fact 19's widely-quoted **1.253x**
//! was measured on a *different* focus operator and **does not reproduce here**;
//! fact 343's consequence is explicit that it may not be quoted as this
//! pipeline's baseline, so it is not quoted as one. Fact 19 is not refuted — it
//! is a different measurement of a different thing.
//!
//! This module is the baseline's replacement, and it is built out of two
//! measured findings that were priced long before any of this was written:
//!
//! - **Regularise the focus field before choosing a winner.** It cuts absolute
//!   reconstruction error at occluding edges by 35%, 24.79 -> 15.99 DN
//!   (fact 84), which is this operator's own number and is the single largest
//!   measured quality win the baseline left unbuilt.
//!
//!   **Both halves of fact 23 are the retired ring difference, and neither is
//!   this operator's.** Its speckle pair — 34.4% -> 0.868%, which this header
//!   quoted uncaveated until M60c — was measured with the **ring** operator
//!   (`M2-verification.md` section 4; `:205` records the measure, and Tenengrad
//!   did not exist until M14), and **no section-4 row publishes a
//!   regularised-Tenengrad speckle at all**, so there is no operator-matched
//!   pair to put here. Fact 71's **1.010%** is *unregularised* Tenengrad on the
//!   same ROI; the regularised comparable is whatever the binary prints for the
//!   run in hand. Its noise pair fails the same way: on the shipped operator
//!   regularising moves the ratio 1.0678x -> 1.0739x, very slightly the *wrong*
//!   way (fact 343).
//!
//!   **The near-coincidence is why this survived at four sites.** Fact 23's
//!   34.4% -> 0.868% is a *regularisation* effect on the ring; fact 71's
//!   34.381% -> 1.010% is an *operator* effect with no regularisation in it at
//!   all. Both start at ~34.4% and land near 1%, for different reasons, so a
//!   Tenengrad number and a ring number look interchangeable and are not.
//!
//! - **Regularisation alone is not enough.** 1.0739x is still worse than one
//!   frame. *Only averaging goes below one* (fact 23). A plain mean reaches
//!   0.534x (fact 19) but collapses detail by more than half (fact 24), so the
//!   average has to be taken over exactly those frames that genuinely agree.
//!
//! So the merge is: regularise, elect a winner, admit every frame whose focus
//! response is statistically indistinguishable from the winner's, and average
//! them. Where one frame stands far above the rest the acceptance set collapses
//! to that frame and the estimator degenerates to a selector — which is the
//! correct behaviour, and is what facts 263 and 264 say actually happens at a
//! resolved edge, where the peak stands 10^2-10^3 sigma clear.
//!
//! # Why this is two passes and not one
//!
//! The gate needs each frame's focus response *relative to the winner*, and the
//! winner is not known until every frame has been seen. A single bounded fold
//! would have to carry per-pixel through-focus state whose size grows with the
//! acceptance set. Two passes carry O(1) state per pixel instead, and decode is
//! 0.91 s warm (fact 33), so the second pass is cheap. Both passes are
//! order-independent and associative, so both parallelise by partitioning the
//! frame list — see the tests, which pin that property rather than assume it.
//!
//! # What is measured here and what is not
//!
//! [`FOCUS_NOISE_SD`] is measured by [`tests::the_focus_noise_constant_is_the
//! _measured_one`], in this crate, from a pure-noise plane pushed through the
//! real operator. It is not a literature value and not a guess.
//!
//! [`Gate::threshold`] is **not** measured. It is the one free parameter in this
//! module and it is deliberately left explicit at the API boundary rather than
//! buried in a default, because M27 measured the acceptance-set width it
//! controls (`nwide = 3`, fact 212) and that number is the calibration target.
//! [`Estimator::n_eff`] is an output for exactly this reason.

use crate::boxfilter::box_mean;
use crate::noise::NoiseModel;
use crate::plane::{PlaneGeometry, QuadSource};
use crate::robust::{AffineVar, Arm, ResidualOp, RobustElection, Z_HALF};
use crate::softgate::{SoftGate, WEIGHT_FLOOR};
use crate::{CfaPlane, Error, Result};

/// Radius of the merge regulariser: 8, giving the measured 17x17 box.
///
/// Fact 84 priced width 17 at -35% absolute reconstruction error. Fact 86 is the
/// reason this is not a tuning knob reaching down to 1: at width 3 the
/// regulariser is *worse than none at all* (merged noise rises 1.2773 -> 1.3856),
/// because a narrow box correlates neighbouring selections without averaging
/// enough of them to pay for it.
///
/// Fact 36 is the reason it is not tuned upward either: the flat-ROI noise ratio
/// is monotone-decreasing in width with no interior optimum, so anything that
/// minimises noise alone runs to the widest width offered and destroys focus
/// selectivity. Fact 42 supplies the interior optimum only under a *joint*
/// selectivity/noise objective, and only on tilted depth — which is where 17
/// came from.
pub const REGULARISER_RADIUS: usize = 8;

/// Width of the merge regulariser box, in plane pixels.
pub const REGULARISER_WIDTH: usize = 2 * REGULARISER_RADIUS + 1;

/// The noise penalty for selecting one frame instead of averaging. **Currently
/// 1.0 — the measured value was refuted and no admissible replacement exists.**
///
/// A pixel that admitted exactly one frame did not receive an *arbitrary*
/// frame. It received the frame the focus argmax elected, and the argmax
/// prefers whichever frame's noise happened to point upward. So `n = 1` is not
/// "no averaging" — it is selection, and **selection adds noise**. That
/// mechanism is real and is why this hook exists.
///
/// What was refuted is the *number*. This shipped at **1.074×** on the strength
/// of two agreeing measurements (facts 320, 321, 23). M40 audited it under rule
/// 24 and found every defect was a choice, not an arithmetic slip:
///
/// - **It has no defined meaning at any value** (fact 440). The estimator was a
///   ratio of two **spatial** standard deviations against one reference frame;
///   this multiplies a **temporal** per-sample σ by it. A rule-10 units
///   violation, now discipline 264.
/// - **It exceeds its own ceiling** (fact 446). On a pure-noise plant built to
///   maximise the winner's curse the shipped operator can produce at most
///   1.0451×/1.0508× (pixel) and 1.0307×/1.0345× (gradient). 1.074 is above the
///   maximum its own mechanism can generate.
/// - **It is not a constant** (fact 443). The same estimator on six ROIs across
///   two stacks reads 1.0001, 1.0739, 1.0867, 0.9841, 1.0601, 1.2732. The
///   shipped value is one of those six.
/// - **It made the metric worse than doing nothing** (fact 454). On a
///   genuinely detail-free plant the corrected detail metric reads **−11.63 DN
///   where truth is 0** — it crosses zero and lands *further* from truth than
///   the defect it replaced, with `max(0, .)` hiding the sign.
///
/// So this is 1.0 until someone measures the penalty with a **temporal,
/// structure-free** estimator in this crate. Do not substitute 1.045 (fact
/// 446's ceiling) or any other plausible-looking value: an unmeasured constant
/// that happens to be smaller is still an unmeasured constant, and that is the
/// exact failure this revert exists to undo.
///
/// Fact 341 — that `predicted_sigma` reports exactly 1.000× the single-frame σ
/// at gate 0 — is therefore **open again**, and it is the honest state. A known
/// missing term is better than a wrong one.
pub const SELECTION_INFLATION: f32 = 1.0;

/// The noise penalty carried by a pixel that admitted `n` frames.
///
/// **The two-branch shape is right and is deliberately kept** even though both
/// branches currently return 1.0. Fact 458 measured `n_eff = 1` across
/// **41.66%** of the plane at a working gate, so `n = 1` is not a rare corner
/// that could be folded into the averaging case — it is most of the image, and
/// it needs its own term the moment one is measured.
///
/// Fact 448 also settled the *shape* of that term, and it is not this one:
/// plant inflation by acceptance-set size decays **smoothly** — 1.0770, 1.0591,
/// 1.0454, 1.0383, 1.0319, 1.0293, 1.0286, 1.0220 for `n = 1..8` — rather than
/// stepping to zero at `n = 2`. A step drove a 7.4-point discontinuity straight
/// through the 41.66% of the plane sitting at `n = 1`. Whatever replaces this
/// should be a decaying function of `n`, not a two-valued one.
#[inline]
#[must_use]
pub fn selection_inflation(n: u16) -> f32 {
    if n <= 1 { SELECTION_INFLATION } else { 1.0 }
}

/// Standard deviation of the regularised focus response under pure sensor noise.
///
/// **Measured, not assumed** — see `the_focus_noise_constant_is_the_measured_one`.
/// A pure-noise luma plane is pushed through the real
/// [`FocusField`](crate::focus::FocusField) and this regulariser, and the
/// standard deviation of the interior response is read off.
///
/// The units work out to a pure number because
/// [`FocusField::compute`](crate::focus::FocusField::compute) already divides the
/// windowed gradient mean by the noise model's sigma at that pixel. That is what
/// makes a *single* threshold valid across the whole frame and across stacks
/// shot at different ISOs: the response is already in units of its own noise.
/// Without that normalisation this constant would have to be a per-pixel field.
///
/// # What the number says
///
/// A single sample of the sigma-normalised gradient magnitude is Rayleigh with
/// scale `0.125 * sqrt(12) = 0.4330`, so its own standard deviation is
/// `0.4330 * sqrt(2 - pi/2) = 0.2837`. The measured response is 18.6x quieter
/// than that, implying about **348 effective independent samples**. The nominal
/// combined support of a 27-box followed by a 17-box is `43 x 43 = 1849`, so the
/// overlapping Sobel stencils and the triangular box-of-box weighting cost a
/// factor of 5.3 against naive independence. **That factor is exactly why this
/// is measured rather than derived** — a closed form would have had to assume it
/// away, and would have made the gate 2.3x too tight.
///
/// It is a function of [`WINDOW_RADIUS`](crate::focus::WINDOW_RADIUS) and
/// [`REGULARISER_RADIUS`], and it is wrong if either changes. The test asserts
/// against the operator as configured, so changing either breaks it loudly.
pub const FOCUS_NOISE_SD: f32 = 0.015_214;

/// Apply the merge regulariser to one frame's focus field.
///
/// `scratch` and `dst` must be `geom.pixels()` long; `scratch` is overwritten.
/// Separable running sums, so the cost does not depend on the radius.
pub fn regularise(focus: &[f32], geom: PlaneGeometry, scratch: &mut [f32], dst: &mut [f32]) {
    box_mean(focus, geom, REGULARISER_RADIUS, scratch, dst);
}

/// Apply the merge regulariser at an explicit radius.
///
/// The depth-guide pass needs its regulariser capped to its own narrow window:
/// the guide exists to locate silhouettes to a few pixels, and a radius-8 box
/// over it would displace the very step it is being asked to find.
pub fn regularise_at(
    focus: &[f32],
    geom: PlaneGeometry,
    radius: usize,
    scratch: &mut [f32],
    dst: &mut [f32],
) {
    box_mean(focus, geom, radius.min(REGULARISER_RADIUS), scratch, dst);
}

/// Apply the merge regulariser with **depth-layer masked support**.
///
/// The regulariser is a second box cascade over the focus field. Left at its
/// shipped radius 8 while the focus operator is made edge-aware, it averages
/// the newly-correct responses straight back across the silhouette and
/// re-manufactures a rim of its own radius, so the two have to be masked
/// together or neither.
///
/// `dst` is filled with the shipped radius-8 box mean first and only the
/// treated pixels are overwritten, so an empty support is byte-identical to
/// [`regularise`].
pub fn regularise_layered(
    focus: &[f32],
    geom: PlaneGeometry,
    support: &crate::edgeaware::LayerSupport,
    scratch: &mut [f32],
    tmp: &mut [f32],
    acc: &mut [f32],
    dst: &mut [f32],
) {
    box_mean(focus, geom, REGULARISER_RADIUS, scratch, dst);
    support.apply_at(focus, REGULARISER_RADIUS, scratch, tmp, acc, dst);
}


///
/// # Why this must exist and cannot be skipped
///
/// Making only [`FocusField::compute_scaled`](crate::focus::FocusField::compute_scaled)
/// edge-aware does not remove the halo, it moves it. The regulariser is a
/// second box cascade over the focus field; left at radius 8 it takes the
/// newly-correct narrow-support responses next to a silhouette and averages
/// them straight back across it, re-manufacturing a rim of its own radius. The
/// election's total spill is the composition of the two, which is why M121
/// derived a 22 px prediction from `WINDOW_RADIUS = 13` composed with
/// `REGULARISER_RADIUS = 8`. Both ends of that composition have to be told
/// about the depth step or neither is.
///
/// The cap is what keeps this a no-op away from silhouettes: at
/// [`FULL_LEVEL`](crate::edgeaware::FULL_LEVEL) the radius is `min(13, 8) = 8`,
/// which is [`regularise`] exactly.
pub fn regularise_scaled(
    focus: &[f32],
    geom: PlaneGeometry,
    scale: &crate::edgeaware::SelectionScale,
    scratch: &mut [f32],
    ladder: &mut Vec<f32>,
    dst: &mut [f32],
) {
    assert_eq!(scale.geometry(), geom);
    let px = geom.pixels();
    let n = crate::edgeaware::LEVEL_RADII.len();
    if ladder.len() != n * px {
        ladder.resize(n * px, 0.0);
    }
    for (l, &r) in crate::edgeaware::LEVEL_RADII.iter().enumerate() {
        let (_, tail) = ladder.split_at_mut(l * px);
        box_mean(
            focus,
            geom,
            r.min(REGULARISER_RADIUS),
            scratch,
            &mut tail[..px],
        );
    }
    let levels = scale.levels();
    for (i, d) in dst.iter_mut().enumerate() {
        *d = ladder[levels[i] as usize * px + i];
    }
}

/// Apply the merge regulariser **guided by the frame's own observed luma**.
///
/// The shipped regulariser is a radius-8 box mean over the focus field, and it
/// is 8 of the 22 px of total election spill — `SOBEL_RADIUS + WINDOW_RADIUS +
/// REGULARISER_RADIUS`. Shrinking the focus window alone therefore cannot
/// remove the rim: this cascade would average the newly-correct narrow
/// responses straight back across the silhouette and re-manufacture one at its
/// own radius.
///
/// This replaces the box with an edge-stopping filter of the *same* nominal
/// scale, so the noise averaging is retained everywhere it is legitimate and
/// abandoned only where it would cross an occluding edge. That is the trade the
/// adaptive-radius rule depends on: it deliberately gives up window radius near
/// silhouettes, and this is what buys the robustness back.
///
/// `sigma_s` is `REGULARISER_RADIUS` — the same spatial scale, so away from any
/// luma step this is the shipped operator to within the difference between a
/// box and a Gaussian of matched radius.
pub fn regularise_guided(
    focus: &[f32],
    luma: &[f32],
    geom: PlaneGeometry,
    scratch: &mut [f32],
    tmp: &mut [f32],
    dom: &mut [f32],
    dst: &mut [f32],
) {
    crate::edgeaware::domain_transform(
        focus,
        luma,
        geom,
        REGULARISER_RADIUS as f32,
        dst,
        scratch,
        tmp,
        dom,
    );
}

/// The rule admitting a frame to the average at a pixel.
///
/// A frame is admitted when its regularised focus response is within
/// `threshold` standard deviations of the winner's. Both responses are already
/// noise-normalised, and the two frames' sensor noise is independent, so the
/// standard deviation of the *difference* is `sqrt(2) * FOCUS_NOISE_SD`.
///
/// # The winner's curse, and what the corpus does *not* say about the defence
///
/// The reference is a maximum over N frames, so it is biased upward by
/// selection, which makes every gap look larger than it is and shrinks the
/// acceptance set. That much is mechanism and is not in doubt.
///
/// **What this doc used to claim — that the regulariser is what contains it,
/// cited to fact 23's 34.4% -> 0.868% — does not survive.** Three separate
/// problems, any one of which is enough:
///
/// 1. **Wrong operator.** That pair is the retired ring difference, not
///    Tenengrad (see the module header). No corpus row publishes a regularised
///    Tenengrad speckle, so it cannot simply be swapped for a matched one.
/// 2. **Wrong quantity.** Speckle is a property of the winner *index map*. The
///    curse is an upward bias in the winner's *value*, and it is the value that
///    sets the acceptance set. A coherent index map is consistent with a biased
///    winner, not evidence against one.
/// 3. **The closest operator-matched arm points the other way.** Fact 343
///    measures gate-0 selection noise on the shipped operator, same 22 frames
///    and ROI, at **1.0678x unregularised against 1.0739x regularised** —
///    regularising *raises* it slightly. That is the curse's measured effect on
///    the output rather than the acceptance-set size itself, so it is not a
///    refutation; but it is the nearest thing the corpus has, and it does not
///    support the claim.
///
/// DERIVED, and it suggests why the effect should be small in either direction:
/// `threshold` is in units of `FOCUS_NOISE_SD`, which is *defined* as the SD of
/// the **regularised** response. The curse scales with the field's own noise SD
/// and so does the tolerance, so their ratio — which is what actually admits or
/// rejects a frame — is first-order invariant to how hard the field is
/// smoothed. Fact 503 makes the same scaling argument for a constant rescale
/// and predicts the admission set is bit-for-bit unchanged.
///
/// **Status: ARGUED, not measured.** Electing on the regularised field is
/// load-bearing for the winner map and for edge error (fact 84, this
/// operator); its value *for the gate* is unestablished, and the measurement
/// that would settle it is not in the corpus — `n_eff` under regularised versus
/// raw election at a matched tolerance, on real frames. Do not restore a
/// stronger sentence here without that number.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Gate {
    /// Admission half-width, in standard deviations of the response difference.
    pub threshold: f32,
}

/// The gate the shipped default path runs at (M64).
///
/// This is the single exposed knob's resting position, and it is the most
/// contestable number in the merge. What it is chosen against, and what it is
/// *not*:
///
/// # Why 4.0
///
/// The gate compares each frame against a **maximum over N frames**. Under the
/// null that every frame has equal true focus, the winner sits about
/// `E[max of N standard normals]` above the mean — 2.04σ at N = 30 — so a
/// tolerance of `threshold * sqrt(2)` σ admits a statistically indistinguishable
/// frame only once it clears that selection offset plus a tail. **A fixed
/// `threshold` is therefore an N-dependent statement**, and M62 measured where
/// it lands on a 30-frame static burst where every frame is *provably* identical
/// in focus and the correct answer is known exactly (MEASURED, M62 §6.2):
///
/// | `threshold` | mean `n_eff` / 30 | noise reduction | ideal |
/// | --- | --- | --- | --- |
/// | 0 | 1.00 / 30 | 0.9768x | 5.4772 |
/// | 2 | 18.4 / 30 | 3.7764x | 5.4772 |
/// | **4** | **29.5 / 30** | **5.4316x** | 5.4772 |
/// | 8 | 30.0 / 30 | 5.4777x | 5.4772 |
///
/// At `threshold = 2` the merge **rejects 11.6 of 30 frames it should have
/// admitted** — an error in the selector direction, and the direction this
/// project exists to correct. At 4.0 it admits 98.5% of them.
///
/// # Why not 8.0, which scores marginally better
///
/// `threshold = 8` is a tolerance of `8 * sqrt(2) = 11.3` σ of the focus field's
/// own noise, and [`tests::real_focus_contrast_is_far_larger_than_the_noise_scale`]
/// pins real focus contrast at **> 20 σ** — so 8.0 spends over half the
/// discriminating margin to buy 0.8% of noise. It is also off the ladder every
/// corpus stack was measured on, so no real stack has ever been run there.
/// 4.0 is 5.66 σ, 3.5x inside the margin, and M52 measured it on real stacks:
/// `109MSDCF` admits 5.017 of 22 frames, `foam` 1.361 of 24 — still selecting
/// hard, not degenerate (MEASURED, M52 §5.3).
///
/// # What this number costs, stated where it cannot be missed
///
/// **The sharpness price of gate 4.0 on real frames is not measured anywhere in
/// this corpus, on any axis.** Fact 322 bounds noise-corrected detail loss
/// across the whole shipped sweep on `109MSDCF` at −4.6%…−0.5% of mean |∇|,
/// which per rule 18 is admissible against *collapse* only and is not a
/// resolution measurement. M57's 0.496–0.740 px deficit is measured on a
/// **fractional peak-height** gate that runs in the opposite direction, so it
/// does not transfer to this axis except through mean `n_eff`. Anyone raising
/// this constant on the strength of a √N score alone is tuning to a plant where
/// every frame is in focus — see M62's own §4, which says so first.
pub const DEFAULT_GATE: f32 = 4.0;

impl Gate {
    pub fn new(threshold: f32) -> Self {
        assert!(
            threshold >= 0.0 && threshold.is_finite(),
            "gate threshold must be finite and non-negative, got {threshold}"
        );
        Self { threshold }
    }

    /// The admission half-width in response units.
    #[inline]
    pub fn tolerance(&self) -> f32 {
        self.threshold * std::f32::consts::SQRT_2 * FOCUS_NOISE_SD
    }

    /// Is a frame with response `focus` admitted against a winner at `best`?
    ///
    /// A non-finite response is never admitted, because every comparison
    /// against NaN is false.
    #[inline]
    pub fn admits(&self, focus: f32, best: f32) -> bool {
        best - focus <= self.tolerance()
    }
}

/// Environment switch selecting a soft admission kernel.
///
/// Named here so the string lives in exactly one place, for the reason
/// [`crate::optics::CA_ENV`] gives: a switch spelled independently in the code
/// and in a harness's argv is a switch that will eventually be set and not
/// read.
pub const SOFT_GATE_ENV: &str = "STREHL_SOFT_GATE";

/// Which soft admission kernel the merge is folding, if any.
///
/// `None` is the shipped top-hat [`Gate`] and **must remain the default**. Every
/// byte-freeze in the corpus is taken against it; making a soft kernel default
/// would break the entire regression net in one commit.
///
/// Both kernels share [`Gate::tolerance`] exactly, so the only thing that varies
/// across this enum is the *shape* of the kernel over an unchanged, calibrated
/// z-axis. That identity is what makes the comparison in M111 §15.7 a controlled
/// one rather than two differently-scaled estimators.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SoftKernel {
    /// `exp(-0.5 (gap/T)^2)` — [`crate::softgate::SoftGate`], M111's kernel.
    ///
    /// What you get if the response gap is normal with sd `T`, which is what
    /// [`FOCUS_NOISE_SD`](crate::focus::FOCUS_NOISE_SD) was calibrated to
    /// describe, so it is the kernel the existing noise model implies.
    Gaussian,
    /// `exp(-gap/T)` — the kernel [`crate::through_focus`] already folds at the
    /// identical temperature, promoted here from diagnostic to admission.
    ///
    /// Heavier-tailed than the Gaussian, so it admits far-off frames more
    /// readily. That is the direction M111 §15.8 measured `--gate 100000` to
    /// destroy the photograph in, which is precisely why it is priced rather
    /// than assumed.
    Exponential,
}

/// The gap, in tolerances, at which `exp(-z)` reaches [`WEIGHT_FLOOR`].
///
/// `exp(-z) = 2^-16` gives `z = 16 ln 2 = 11.0904`. Derived from the same floor
/// [`crate::softgate::cutoff_tolerances`] uses so the two kernels truncate at
/// the same *weight*, not at the same *distance* — truncating both at one
/// distance would silently make the comparison a comparison of supports.
pub fn exponential_cutoff_tolerances() -> f32 {
    -(f64::from(WEIGHT_FLOOR)).ln() as f32
}

impl SoftKernel {
    /// The weight a frame with response `focus` earns against a winner at `best`.
    ///
    /// `soft` supplies the tolerance and is constructed from the same threshold
    /// as the [`Gate`], so callers cannot accidentally price two kernels on two
    /// scales. The [`SoftKernel::Gaussian`] arm delegates to M111's tested
    /// implementation rather than restating the arithmetic, so this cannot drift
    /// from the field prediction its cross-language pin is taken against.
    ///
    /// Guard-for-guard identical to [`SoftGate::weight`] on the exponential arm:
    /// non-finite earns `0.0`, a frame at least as good as the winner earns
    /// `1.0`, and a zero tolerance degenerates to the hard argmax.
    #[inline]
    pub fn weight(&self, soft: &SoftGate, focus: f32, best: f32) -> f32 {
        match self {
            SoftKernel::Gaussian => soft.weight(focus, best),
            SoftKernel::Exponential => {
                if !focus.is_finite() || !best.is_finite() {
                    return 0.0;
                }
                let gap = best - focus;
                if gap <= 0.0 {
                    return 1.0;
                }
                let tol = soft.tolerance();
                if tol <= 0.0 {
                    return 0.0;
                }
                let z = gap / tol;
                if z >= exponential_cutoff_tolerances() {
                    return 0.0;
                }
                let w = (-z).exp();
                if w < WEIGHT_FLOOR { 0.0 } else { w }
            }
        }
    }
}

/// A [`SOFT_GATE_ENV`] value that names no kernel.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnknownSoftKernel {
    /// The value as the operator wrote it.
    pub key: String,
}

impl core::fmt::Display for UnknownSoftKernel {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(
            f,
            "unknown soft-gate kernel {:?}; known kernels: gaussian, exponential \
             (unset, \"\", \"0\", \"off\" or \"false\" run the shipped hard gate)",
            self.key
        )
    }
}

impl std::error::Error for UnknownSoftKernel {}

/// Resolve the soft kernel from a [`SOFT_GATE_ENV`] value.
///
/// **Off by default, and it must stay that way** — see [`SoftKernel`].
///
/// The value must **name the kernel**, not merely be truthy, for the reason
/// [`crate::optics::profile_from_setting`] refuses a bare `1`: there are two
/// kernels and "yes, soften the gate" does not say which, so a truthy value is
/// a request this function cannot honour. A typo is an `Err` rather than a
/// `None`, because a typo that silently disables the fix is indistinguishable
/// from the fix not working.
///
/// ```text
/// STREHL_SOFT_GATE unset / "" / "0" / "off" / "false" -> Ok(None)   shipped top-hat
/// STREHL_SOFT_GATE "gaussian"                         -> Ok(Some(Gaussian))
/// STREHL_SOFT_GATE "exponential"                      -> Ok(Some(Exponential))
/// STREHL_SOFT_GATE "1" / "true" / "on"                -> Err(..)    refuses to guess
/// STREHL_SOFT_GATE "typo"                             -> Err(..)    refuses silently-off
/// ```
///
/// Takes the value as an argument rather than reading the environment, so it is
/// testable without mutating global process state from parallel test threads.
pub fn kernel_from_setting(
    value: Option<&str>,
) -> core::result::Result<Option<SoftKernel>, UnknownSoftKernel> {
    let raw = match value {
        None => return Ok(None),
        Some(v) => v.trim(),
    };
    if raw.is_empty()
        || raw == "0"
        || raw.eq_ignore_ascii_case("off")
        || raw.eq_ignore_ascii_case("false")
    {
        return Ok(None);
    }
    if raw.eq_ignore_ascii_case("gaussian") {
        return Ok(Some(SoftKernel::Gaussian));
    }
    if raw.eq_ignore_ascii_case("exponential") {
        return Ok(Some(SoftKernel::Exponential));
    }
    Err(UnknownSoftKernel {
        key: raw.to_string(),
    })
}

/// [`kernel_from_setting`] applied to [`SOFT_GATE_ENV`] in the process
/// environment.
///
/// A plain function rather than a cached `OnceLock`, matching
/// [`crate::optics::active_profile`]: the cost is one `getenv` per merge, and a
/// cache would make the switch un-testable within a process.
pub fn active_kernel() -> core::result::Result<Option<SoftKernel>, UnknownSoftKernel> {
    kernel_from_setting(std::env::var(SOFT_GATE_ENV).ok().as_deref())
}

/// A [`ROBUST_ENV`] value that names no election arm.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UnknownArm {
    /// The value as the operator wrote it.
    pub key: String,
}

/// Names the pass-one election arm. Unset, `""`, `0`, `off` or `false` is the
/// shipped argmax and is the default.
///
/// `soft`, `hard` and `ungated` name [`Arm`] explicitly; `on`, `1` and `true`
/// select [`Arm::Soft`], the only arm safe to default to — see `robust.rs`'s
/// header on why [`Arm::Hard`] cannot tell a frame that moved from the one
/// frame that resolves a pixel. Anything else is refused rather than silently
/// read as off: a typo that disables a gate you believe is running looks
/// exactly like the gate doing nothing.
///
/// `ungated` is not a spelling of off. It runs the whole ring, the whole `z`
/// computation and the whole [`RobustElection`], and only declines to let the
/// weight reach the argmax. It is the control that separates "the gate changed
/// the picture" from "the new plumbing changed the picture".
pub const ROBUST_ENV: &str = "STREHL_ROBUST_ELECTION";

fn arm_from_setting(raw: Option<&str>) -> core::result::Result<Option<Arm>, UnknownArm> {
    let Some(raw) = raw else { return Ok(None) };
    match raw.trim().to_ascii_lowercase().as_str() {
        "" | "0" | "off" | "false" => Ok(None),
        "on" | "1" | "true" | "soft" => Ok(Some(Arm::Soft)),
        "hard" => Ok(Some(Arm::Hard)),
        "ungated" => Ok(Some(Arm::Ungated)),
        _ => Err(UnknownArm {
            key: raw.to_string(),
        }),
    }
}

/// The election arm this process is running, from [`ROBUST_ENV`].
pub fn active_arm() -> core::result::Result<Option<Arm>, UnknownArm> {
    arm_from_setting(std::env::var(ROBUST_ENV).ok().as_deref())
}

/// Pass one's robust-election state: the temporal ring, the statistic and the
/// election. Present only when [`ROBUST_ENV`] asked for it, so with the feature
/// off `FocusStats` carries exactly the fields it always has.
///
/// Frames reach pass one in ascending order within a contiguous chunk
/// (`par_chunks` in `merge_cmd`), which is what makes a streaming ring possible:
/// `z` needs a **centred** window, so frame `c` cannot be scored until frame
/// `c + Z_HALF` has been read. This defers each frame's election by `Z_HALF`
/// frames, and elects the `Z_HALF` frames at each end of a chunk with `z = 0` —
/// `robust.rs`'s documented convention for an undefined window, which leaves
/// them ungated rather than rejected.
///
/// # The chunk must be at least `Z_WINDOW` frames long, and nothing enforces it
///
/// A chunk shorter than the window never produces a centred frame, so **every**
/// frame in it is elected with `z = 0` and the gate does nothing at all. This is
/// not hypothetical and it is not rare: `merge_cmd` sets
/// `chunk_len = frames.div_ceil(workers)` from a *memory* budget, which knows
/// nothing about this statistic, so a short bracket on a wide machine silently
/// disables the whole feature. Measured on this rig: 40 frames over 13 workers
/// gives `chunk_len = 3`, and 22 frames over 11 workers gives `chunk_len = 2`.
/// Both rendered a byte-identical image, reported every frame as elected, and
/// scored `z` exactly zero times.
///
/// That failure is invisible from the outside — the output is simply the
/// shipped argmax, which is a perfectly good photograph — so
/// [`FocusStats::window_starved_frames`] counts it and any caller reporting a
/// gate's effect **must** report that count beside it. A gate that elected
/// every frame with an undefined window did not read quiet; it did not read at
/// all.
#[derive(Debug, Clone)]
struct RobustPassOne {
    op: ResidualOp,
    var: AffineVar,
    election: RobustElection,
    ring_luma: Vec<Vec<f32>>,
    ring_reg: Vec<Vec<f32>>,
    ring_index: Vec<u16>,
    seen: usize,
    zbuf: Vec<f32>,
    zero: Vec<f32>,
    /// Frames elected with `z = 0` because no centred window existed for them.
    starved: u32,
}

impl RobustPassOne {
    fn new(pixels: usize, arm: Arm, var: AffineVar) -> Self {
        let op = ResidualOp::default();
        let w = op.window();
        Self {
            op,
            var,
            election: RobustElection::new(pixels, arm),
            ring_luma: (0..w).map(|_| vec![0.0; pixels]).collect(),
            ring_reg: (0..w).map(|_| vec![0.0; pixels]).collect(),
            ring_index: vec![NO_FRAME; w],
            seen: 0,
            zbuf: vec![0.0; pixels],
            zero: vec![0.0; pixels],
            starved: 0,
        }
    }

    /// Ring slot holding the frame `back` pushes before the most recent one.
    #[inline]
    fn slot(&self, back: usize) -> usize {
        let w = self.op.window();
        (self.seen + w - 1 - back) % w
    }

    /// Fold one frame that is already in the ring, with the given `z` field.
    fn fold_slot(&mut self, s: usize, z_is_zero: bool) -> std::result::Result<(), String> {
        let idx = self.ring_index[s];
        if z_is_zero {
            self.starved += 1;
        }
        // Move the response out so its borrow cannot conflict with `zbuf`.
        let resp = std::mem::take(&mut self.ring_reg[s]);
        let z = if z_is_zero { &self.zero } else { &self.zbuf };
        let r = self.election.fold(idx, &resp, z);
        self.ring_reg[s] = resp;
        r
    }

    /// Score and elect the centre of the currently buffered window.
    fn elect_centre(&mut self) -> std::result::Result<(), String> {
        let w = self.op.window();
        // Oldest first, so the window reaches the kernel in temporal order.
        let order: Vec<usize> = (0..w).map(|j| self.slot(w - 1 - j)).collect();
        {
            let planes: Vec<&[f32]> =
                order.iter().map(|&s| self.ring_luma[s].as_slice()).collect();
            self.op
                .z_field(&planes, self.var.a, self.var.b, &mut self.zbuf);
        }
        self.fold_slot(order[Z_HALF], false)
    }

    fn push(&mut self, index: u16, reg: &[f32], luma: &[f32]) -> std::result::Result<(), String> {
        let w = self.op.window();
        let s = self.seen % w;
        self.ring_luma[s].copy_from_slice(luma);
        self.ring_reg[s].copy_from_slice(reg);
        self.ring_index[s] = index;
        self.seen += 1;
        if self.seen <= Z_HALF {
            // The leading Z_HALF frames never become a centre with a full
            // window, so they are elected at once and ungated.
            return self.fold_slot(s, true);
        }
        if self.seen >= w {
            return self.elect_centre();
        }
        Ok(())
    }

    /// Elect the trailing frames, which never acquire a centred window.
    fn flush(&mut self) -> std::result::Result<(), String> {
        let w = self.op.window();
        // In a chunk shorter than the window nothing was ever centred, so
        // everything past the leading Z_HALF is still unelected.
        let tail = if self.seen < w {
            self.seen.saturating_sub(Z_HALF)
        } else {
            Z_HALF
        };
        for back in (0..tail).rev() {
            let s = self.slot(back);
            self.fold_slot(s, true)?;
        }
        self.seen = 0;
        Ok(())
    }
}

/// Pass one: the regularised winner field.
///
/// Carries O(1) state per pixel and is a commutative, associative fold, so the
/// frame list can be partitioned across workers arbitrarily and reduced with
/// [`FocusStats::absorb`] for bit-identical output.
#[derive(Debug, Clone)]
pub struct FocusStats {
    geom: PlaneGeometry,
    best_focus: Vec<f32>,
    best_index: Vec<u16>,
    frames: u32,
    max_index: u16,
    /// The robust election, or `None` for the shipped argmax.
    ///
    /// `None` is what makes the null byte-identical *by construction*: with it
    /// absent, `fold` runs the code it has always run and no new arithmetic
    /// exists to round differently. It mirrors how `Estimator::wsum` and
    /// `Estimator::censor` encode their features being off.
    robust: Option<Box<RobustPassOne>>,
}

/// Sentinel for "no frame has been folded at this pixel yet".
const NO_FRAME: u16 = u16::MAX;

impl FocusStats {
    pub fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            best_focus: vec![f32::NEG_INFINITY; geom.pixels()],
            best_index: vec![NO_FRAME; geom.pixels()],
            frames: 0,
            max_index: 0,
            robust: None,
        }
    }

    /// Pass one with the robust election available, if [`ROBUST_ENV`] asks for
    /// it. With the variable unset this is [`FocusStats::new`] exactly.
    ///
    /// `var` is the calibrated noise model reduced to `var(L) = a*L + b`; the
    /// caller extracts it so `robust` stays free of crate linkage. It is read
    /// even when the feature is off only in the sense that the caller computes
    /// it — nothing here touches it unless an arm was named.
    pub fn new_robust(
        geom: PlaneGeometry,
        var: AffineVar,
    ) -> core::result::Result<Self, UnknownArm> {
        Ok(match active_arm()? {
            Some(arm) => Self::new_robust_with(geom, arm, var),
            None => Self::new(geom),
        })
    }

    /// [`FocusStats::new_robust`] with the arm given directly.
    ///
    /// Env-free on purpose, mirroring `Estimator::new_soft`: the test suite runs
    /// in one process and in parallel, so a test that had to set a variable to
    /// choose an arm would race every other test in the binary.
    pub fn new_robust_with(geom: PlaneGeometry, arm: Arm, var: AffineVar) -> Self {
        let mut s = Self::new(geom);
        s.robust = Some(Box::new(RobustPassOne::new(geom.pixels(), arm, var)));
        s
    }

    /// Frames elected with `z = 0` because no centred window existed for them,
    /// or `None` with the feature off.
    ///
    /// **Report this beside any claim about what the gate did.** `Z_HALF` frames
    /// at each end of every chunk are unavoidably starved, so a healthy run
    /// shows `2 * Z_HALF * chunks`. A run in which this equals
    /// [`FocusStats::frames_folded`] scored `z` exactly zero times and the gate
    /// was inert — see `RobustPassOne` on why `merge_cmd`'s memory-derived
    /// `chunk_len` makes that a routine outcome rather than an exotic one.
    pub fn window_starved_frames(&self) -> Option<u32> {
        self.robust.as_ref().map(|r| r.starved)
    }

    /// Frames the robust election actually folded, or `None` with the feature
    /// off.
    ///
    /// Must equal [`FocusStats::frames_folded`] once the chunk is finished. The
    /// ring defers each frame by `Z_HALF`, so a ring that drops or repeats a
    /// frame shows up here and nowhere else — an argmax absorbs a duplicate
    /// silently and only loses a little sharpness when it drops one.
    pub fn robust_frames_elected(&self) -> Option<u32> {
        self.robust.as_ref().map(|r| r.election.frames_folded())
    }

    /// The arm this pass one is running, or `None` for the shipped argmax.
    pub fn arm(&self) -> Option<Arm> {
        self.robust.as_ref().map(|r| r.election.arm())
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    pub fn best_focus(&self) -> &[f32] {
        &self.best_focus
    }
    pub fn best_index(&self) -> &[u16] {
        &self.best_index
    }
    pub fn frames_folded(&self) -> u32 {
        self.frames
    }
    /// Highest frame index folded, for the boundary flag.
    pub fn max_index(&self) -> u16 {
        self.max_index
    }
    pub fn allocated_bytes(&self) -> usize {
        self.geom.pixels() * (size_of::<f32>() + size_of::<u16>())
    }

    /// Ties go to the lower frame index, stated rather than left to visitation
    /// order, so the fold is order-independent.
    #[inline]
    fn beats(focus: f32, index: u16, cur_focus: f32, cur_index: u16) -> bool {
        focus > cur_focus || (focus == cur_focus && index < cur_index)
    }

    /// Fold one frame's **regularised** focus field in, with the frame's green
    /// luma alongside it so a robust election can score the frame against its
    /// temporal neighbours.
    ///
    /// **With the feature off this is `fold` and nothing else** — the same
    /// call, not an equivalent one — so the call site may use it
    /// unconditionally and the shipped path cannot drift from it.
    ///
    /// The frames of a chunk must arrive in ascending order, because `z` is a
    /// centred temporal window. Call [`FocusStats::finish_chunk`] when the
    /// chunk is exhausted.
    pub fn fold_with_luma(
        &mut self,
        frame_index: u16,
        regularised: &[f32],
        luma: &[f32],
    ) -> Result<()> {
        if self.robust.is_none() {
            return self.fold(frame_index, regularised);
        }
        if regularised.len() != self.geom.pixels() || luma.len() != self.geom.pixels() {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (regularised.len(), luma.len()),
                want: (self.geom.pixels(), self.geom.pixels()),
            });
        }
        assert_ne!(frame_index, NO_FRAME, "frame index {NO_FRAME} is reserved");
        let r = self.robust.as_mut().expect("checked above");
        r.push(frame_index, regularised, luma)
            .unwrap_or_else(|e| panic!("robust election: {e}"));
        self.frames += 1;
        self.max_index = self.max_index.max(frame_index);
        Ok(())
    }

    /// Finish a contiguous chunk: elect its trailing frames and collapse the
    /// election into the winner field.
    ///
    /// A no-op with the feature off, so it is safe to call unconditionally.
    /// Idempotent, and cheap to repeat.
    pub fn finish_chunk(&mut self) {
        let Some(r) = self.robust.as_mut() else {
            return;
        };
        r.flush().unwrap_or_else(|e| panic!("robust election: {e}"));
        let winners = r.election.winners();
        let resp = r.election.winner_response();
        self.best_index.copy_from_slice(&winners);
        self.best_focus.copy_from_slice(&resp);
    }

    /// Pixels at which every frame was ineligible and the ungated fallback
    /// fired, or `None` with the feature off.
    ///
    /// A large number means the gate is rejecting wholesale and its output is
    /// mostly the shipped election anyway — report it beside any claim that the
    /// gate did something.
    pub fn robust_fallbacks(&self) -> Option<usize> {
        self.robust.as_ref().map(|r| r.election.fallbacks())
    }

    /// The election the shipped code would have made, from the same fold, or
    /// `None` with the feature off.
    pub fn ungated_winners(&self) -> Option<&[u16]> {
        self.robust.as_ref().map(|r| r.election.ungated_winners())
    }

    /// Fold one frame's **regularised** focus field in.
    pub fn fold(&mut self, frame_index: u16, regularised: &[f32]) -> Result<()> {
        assert!(
            self.robust.is_none(),
            "this FocusStats is running a robust election and needs \
             fold_with_luma; folding without luma would silently elect ungated"
        );
        if regularised.len() != self.geom.pixels() {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (regularised.len(), 1),
                want: (self.geom.pixels(), 1),
            });
        }
        assert_ne!(frame_index, NO_FRAME, "frame index {NO_FRAME} is reserved");
        for ((best_f, best_i), &f) in self
            .best_focus
            .iter_mut()
            .zip(self.best_index.iter_mut())
            .zip(regularised)
        {
            if Self::beats(f, frame_index, *best_f, *best_i) {
                *best_f = f;
                *best_i = frame_index;
            }
        }
        self.frames += 1;
        self.max_index = self.max_index.max(frame_index);
        Ok(())
    }

    /// Reduce another worker's partial pass-one state into this one.
    pub fn absorb(&mut self, other: &FocusStats) -> Result<()> {
        if other.geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: usize::MAX,
                got: (other.geom.width, other.geom.height),
                want: (self.geom.width, self.geom.height),
            });
        }
        match (self.robust.as_mut(), other.robust.as_ref()) {
            (Some(a), Some(b)) => {
                // Cross-chunk reduction must compare **gated scores**, not the
                // collapsed raw responses: a contaminated winner from one chunk
                // would otherwise out-argmax a clean winner from another, and
                // the gate would silently stop applying between chunks.
                a.election
                    .absorb(&b.election)
                    .unwrap_or_else(|e| panic!("robust election: {e}"));
                a.starved += b.starved;
                let winners = a.election.winners();
                let resp = a.election.winner_response();
                self.best_index.copy_from_slice(&winners);
                self.best_focus.copy_from_slice(&resp);
                self.frames += other.frames;
                self.max_index = self.max_index.max(other.max_index);
                return Ok(());
            }
            (None, None) => {}
            _ => panic!(
                "cannot reduce a robust pass one into a plain one; \
                 the two elected against different rules"
            ),
        }
        for i in 0..self.geom.pixels() {
            if Self::beats(
                other.best_focus[i],
                other.best_index[i],
                self.best_focus[i],
                self.best_index[i],
            ) {
                self.best_focus[i] = other.best_focus[i];
                self.best_index[i] = other.best_index[i];
            }
        }
        self.frames += other.frames;
        self.max_index = self.max_index.max(other.max_index);
        Ok(())
    }
}

/// Pass two: the noise-gated average.
///
/// Accumulates in `f32` per CFA plane, in **native raw DN** — M26's ruling. No
/// white balance, no colour transform and no black subtraction happens before
/// the gate, because the noise model is calibrated in raw DN and any of those
/// would put the gate and the model in different spaces.
#[derive(Debug, Clone)]
pub struct Estimator {
    geom: PlaneGeometry,
    gate: Gate,
    best_focus: Vec<f32>,
    best_index: Vec<u16>,
    max_index: u16,
    sum: [Vec<f32>; 4],
    /// Number of frames admitted at each pixel. This is `n_eff` for a plain
    /// mean, and it is an output, not a diagnostic — see fact 212.
    ///
    /// Under a [`SoftKernel`] this counts the frames earning a **non-zero**
    /// weight, which is a strictly weaker statement than the count of frames
    /// that meaningfully contributed. The Kish effective count is
    /// [`Estimator::soft_n_eff`]; this field keeps its integer meaning so the
    /// `u16` map format and the exact-equality determinism tests survive.
    n: Vec<u16>,
    /// The soft admission kernel, if any. `None` is the shipped top-hat and is
    /// the default.
    soft: Option<SoftKernel>,
    /// Per-pixel `sum w` and `sum w^2`.
    ///
    /// **Empty unless [`Estimator::new_soft`] built this estimator**, exactly as
    /// `censor` and `luma_sum` encode their features being off. Emptiness is
    /// what makes the hard path byte-identical *by construction*: with these
    /// absent, [`Estimator::value`] takes the original integer divide and no
    /// weighted arithmetic exists to round differently.
    wsum: Vec<f32>,
    wsq: Vec<f32>,
    /// Per-pixel, per-plane censoring state, four bits packed into one byte:
    /// bit `s` of `censor[i]` is set when plane `s` at pixel `i` is censored.
    ///
    /// Empty unless [`Estimator::fold_censored`] is used, in which case bits
    /// `0..=3` mean "the **winner's** own sample on this plane was pinned at
    /// the container maximum", and bits `4..=7` mean "some *other* admitted
    /// frame was pinned there".
    ///
    /// Bits `4..=7` are a **flag, not a behaviour**: such samples are still
    /// summed like any other, exactly as [`Estimator::has_censored_contributor`]
    /// documents. (This sentence previously read "and has been excluded from
    /// the sum", which the code has never done.)
    censor: Vec<u8>,
    /// The container maximum passed to [`Estimator::fold_censored`], once one
    /// has been passed. `None` means the estimator is running the plain
    /// uncensored mean and [`Estimator::value`] takes its original path.
    censor_level: Option<u16>,
    /// Per-pixel, per-plane **gate-weighted mass of contributing samples that
    /// were pinned** at the container maximum. Empty unless
    /// [`Estimator::fold_censored`] is used, allocated beside `censor` and on
    /// the same condition, so one accumulator per CFA plane *is* per-channel by
    /// construction.
    ///
    /// This is the quantity [`Estimator::has_censored_contributor`] is the
    /// boolean shadow of, and the gap between them is the point. On
    /// `dry-erase-marker-head-cpl` M109 measured **10.31%** of the green plane
    /// pinned in *at least one* frame, while only **21.02%** of the ever-pinned
    /// population is pinned in *every* frame. A boolean fires on the former,
    /// which is far wider than the defect; the discriminating quantity is the
    /// *fraction* of contributing weight that was pinned, and this is its
    /// numerator.
    ///
    /// **The denominator is [`Estimator::contributing_weight`], which returns
    /// the exact divisor [`Estimator::value`] uses.** That pairing is not a
    /// convention the caller must honour — it holds because this is incremented
    /// by the same `wt` the sum is, on the same branch, *after* the gate's
    /// `continue`. An unweighted count over a gate-weighted merge is a rate
    /// against the wrong denominator: the merge averages roughly 55 gated
    /// contributors, not 299 frames, and M109's bar B15 predicted 74.7% where
    /// it measured 21.02% for precisely that error.
    ///
    /// # Post-warp, and what that costs
    ///
    /// The value tested here is **post-warp**: the caller resamples the frame
    /// in place before folding it, so the pre-warp sensel is not merely out of
    /// scope — it has been overwritten. Catmull-Rom over a *fully* pinned
    /// neighbourhood reproduces the maximum, but over a *partially* pinned one
    /// returns fractionally less, so `v >= level` **under-counts at edges**,
    /// which is where the residual fringe lives.
    ///
    /// That under-count is deliberate and is the safe direction. The consumer
    /// may only lower a channel toward neutral, so under-counting reaches fewer
    /// pixels than ideal while **never moving a pixel that was not pinned** —
    /// the acceptance property this design was chosen for. Transporting a
    /// pre-warp mask by dilation would over-count and break exactly that. No
    /// epsilon is applied to the test: that trades a known, bounded, directional
    /// bias for an unknown one.
    clip_w: [Vec<f32>; 4],
    /// Per-pixel accumulators for the **admitted-frame green-luma variance**,
    /// in `f64`. Empty unless [`Estimator::track_disagreement`] has been called.
    ///
    /// This is the sufficient statistic for "how much do the frames the merge
    /// actually averages disagree with each other, in units the noise model
    /// predicts". It is a pair of running sums, so it is order-independent,
    /// reduces additively under [`Estimator::absorb`], and needs **no third
    /// pass over the frames** — see [`Estimator::disagreement`] for what it can
    /// and cannot support.
    ///
    /// `f64` and not `f32` on purpose. Over 100 frames of ~15000 DN luma the
    /// sum of squares reaches ~2.4e10 while the variance being recovered from
    /// it is ~1e3, so `sumsq/n - mean^2` cancels about seven significant
    /// figures. `f32` carries roughly seven; `f64` carries sixteen. The
    /// f32-accumulated `sum` field above is *not* reused for the mean for the
    /// same reason.
    luma_sum: Vec<f64>,
    luma_sumsq: Vec<f64>,
    frames: u32,
}

impl Estimator {
    /// Begin pass two against a completed pass one.
    ///
    /// **This constructor resolves [`SOFT_GATE_ENV`] from the process
    /// environment.** That is deliberate and it is the only reason the soft
    /// kernel is reachable from `strehl stack` at all: the render path
    /// constructs its estimators here, in `merge_cmd.rs`, which this milestone
    /// does not own. Reading the switch at the point of use rather than
    /// threading it through a call site matches
    /// [`crate::optics::active_profile`], which the CA correction already does
    /// for the same reason.
    ///
    /// With the variable unset — the shipped default — this is exactly the old
    /// constructor: `soft` is `None`, `wsum`/`wsq` are unallocated, and no
    /// weighted arithmetic exists anywhere in the fold.
    ///
    /// # Panics
    ///
    /// If [`SOFT_GATE_ENV`] is set to something that names no kernel. Failing
    /// loudly is the point: a typo that silently disables the fix is
    /// indistinguishable from the fix not working. Use [`Estimator::new_soft`]
    /// to construct one without consulting the environment.
    pub fn new(stats: &FocusStats, gate: Gate) -> Self {
        let kernel = match active_kernel() {
            Ok(k) => k,
            Err(e) => panic!("{e}"),
        };
        Self::new_soft(stats, gate, kernel)
    }

    /// Begin pass two with an explicitly chosen admission kernel.
    ///
    /// Ignores the environment, so it is safe to call from parallel tests. The
    /// kernel shares `gate`'s threshold and therefore its tolerance exactly;
    /// only the shape of the weight over the response gap changes.
    ///
    /// `kernel: None` is identical to the shipped hard gate in every observable
    /// way, including the bytes of [`Estimator::value`].
    pub fn new_soft(stats: &FocusStats, gate: Gate, kernel: Option<SoftKernel>) -> Self {
        let n = stats.geom.pixels();
        let (wsum, wsq) = if kernel.is_some() {
            (vec![0.0; n], vec![0.0; n])
        } else {
            (Vec::new(), Vec::new())
        };
        Self {
            geom: stats.geom,
            gate,
            best_focus: stats.best_focus.clone(),
            best_index: stats.best_index.clone(),
            max_index: stats.max_index,
            sum: [vec![0.0; n], vec![0.0; n], vec![0.0; n], vec![0.0; n]],
            n: vec![0; n],
            soft: kernel,
            wsum,
            wsq,
            censor: Vec::new(),
            censor_level: None,
            clip_w: [Vec::new(), Vec::new(), Vec::new(), Vec::new()],
            luma_sum: Vec::new(),
            luma_sumsq: Vec::new(),
            frames: 0,
        }
    }

    /// Begin accumulating the admitted-frame green-luma variance.
    ///
    /// Opt-in, like [`Estimator::fold_censored`]'s censoring, and for the same
    /// reason: it costs **16 B/px** and most callers do not want it. It must be
    /// called before the first fold; calling it after some frames are already
    /// folded would silently produce a variance over a subset, so that panics.
    ///
    /// It **cannot change the merged image.** Nothing in [`Estimator::value`],
    /// [`Estimator::n_eff`] or the gate reads these accumulators.
    pub fn track_disagreement(&mut self) {
        assert_eq!(
            self.frames, 0,
            "track_disagreement must be called before the first fold, or the \
             variance is taken over a subset of the admitted frames"
        );
        let n = self.geom.pixels();
        self.luma_sum = vec![0.0; n];
        self.luma_sumsq = vec![0.0; n];
    }

    /// Is this estimator accumulating the admitted-frame variance?
    pub fn tracks_disagreement(&self) -> bool {
        !self.luma_sum.is_empty()
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    pub fn gate(&self) -> Gate {
        self.gate
    }
    pub fn frames_folded(&self) -> u32 {
        self.frames
    }
    /// Frames admitted per pixel. Compare against fact 212's `nwide = 3`.
    ///
    /// **Deliberately still `&[u16]` under a soft kernel.** Row 7 of M111
    /// §15.6 proposed returning the Kish count from here; it is not done,
    /// because this accessor has 49 call sites across 10 files, is dumped
    /// through a `u16` map format, and is compared with `assert_eq!` in the
    /// determinism tests. Changing its type would ripple into files this
    /// milestone does not own and would break an exact-equality test that is
    /// load-bearing. The fractional count is [`Estimator::soft_n_eff`].
    pub fn n_eff(&self) -> &[u16] {
        &self.n
    }

    /// The admission kernel this estimator is folding, if any.
    ///
    /// `None` is the shipped hard [`Gate`].
    pub fn soft_kernel(&self) -> Option<SoftKernel> {
        self.soft
    }

    /// Kish effective sample size `(sum w)^2 / sum w^2` at one pixel.
    ///
    /// `None` on the hard path, where [`Estimator::n_eff`] is already exact.
    /// This is the *exact* generalisation of the integer count: on 0/1 weights
    /// it returns that count.
    #[inline]
    pub fn soft_n_eff_at(&self, i: usize) -> Option<f64> {
        if self.wsum.is_empty() {
            return None;
        }
        let ws = f64::from(self.wsum[i]);
        let wq = f64::from(self.wsq[i]);
        Some(if wq > 0.0 { ws * ws / wq } else { 0.0 })
    }

    /// [`Estimator::soft_n_eff_at`] over the whole plane.
    ///
    /// `None` on the hard path. Allocates, so a caller in a loop wants
    /// [`Estimator::soft_n_eff_at`].
    pub fn soft_n_eff(&self) -> Option<Vec<f32>> {
        if self.wsum.is_empty() {
            return None;
        }
        Some(
            (0..self.geom.pixels())
                .map(|i| self.soft_n_eff_at(i).unwrap_or(0.0) as f32)
                .collect(),
        )
    }

    /// Mean over pixels of the Kish effective sample size.
    ///
    /// The soft counterpart of [`Estimator::mean_n_eff`], and the number M111
    /// §15.3's field prediction is stated in. `None` on the hard path.
    pub fn mean_soft_n_eff(&self) -> Option<f64> {
        if self.wsum.is_empty() || self.geom.pixels() == 0 {
            return None;
        }
        let total: f64 = (0..self.geom.pixels())
            .map(|i| self.soft_n_eff_at(i).unwrap_or(0.0))
            .sum();
        Some(total / self.geom.pixels() as f64)
    }
    pub fn best_index(&self) -> &[u16] {
        &self.best_index
    }
    pub fn allocated_bytes(&self) -> usize {
        self.geom.pixels() * (4 * size_of::<f32>() + 2 * size_of::<u16>() + size_of::<f32>())
            + self.censor.len()
            + self.clip_w.iter().map(Vec::len).sum::<usize>() * size_of::<f32>()
            + (self.wsum.len() + self.wsq.len()) * size_of::<f32>()
            + (self.luma_sum.len() + self.luma_sumsq.len()) * size_of::<f64>()
    }

    /// Is this plane's estimate at this pixel a **lower bound** rather than a
    /// measurement?
    ///
    /// True when the winning frame's own sample there was pinned at the
    /// container maximum, which only [`Estimator::fold_censored`] can observe.
    /// A true here means [`Estimator::value`] returns the container maximum and
    /// the real scene value is somewhere at or above it — the merge does not
    /// know where, and neither does the sensor.
    #[inline]
    pub fn is_censored(&self, p: CfaPlane, i: usize) -> bool {
        !self.censor.is_empty() && self.censor[i] & (1 << Self::slot(p)) != 0
    }

    /// Did some *non-winning* admitted frame contribute a pinned sample here?
    ///
    /// This is a flag, not a behaviour: such samples are still summed, exactly
    /// as they are under [`Estimator::fold`]. It is exposed because a censored
    /// contributor biases the mean upward by an unknown amount, and a caller
    /// emitting per-pixel confidence should be able to see that. Changing the
    /// arithmetic here would need a per-plane admitted count, which the
    /// estimator deliberately does not carry.
    #[inline]
    pub fn has_censored_contributor(&self, p: CfaPlane, i: usize) -> bool {
        !self.censor.is_empty() && self.censor[i] & (1 << (Self::slot(p) + 4)) != 0
    }

    /// The **gate-weighted mass of contributing samples that were pinned** at
    /// the container maximum, for this plane at this pixel.
    ///
    /// This is the weighted refinement of
    /// [`Estimator::has_censored_contributor`]. That boolean fires on the whole
    /// ever-pinned population — 10.31% of the green plane on
    /// `dry-erase-marker-head-cpl` — which is far wider than the defect it
    /// would be used to find. This returns the mass instead, so a caller can
    /// ask *what fraction* of the average was saturated.
    ///
    /// `None` when this estimator is not censoring at all, which is a state
    /// deliberately distinguished from "censoring, and nothing was pinned"
    /// (`Some(0.0)`). Collapsing the two would make an unwired probe
    /// indistinguishable from a clean highlight, and a `0.0` that could be
    /// either is worth nothing.
    ///
    /// Pair it with [`Estimator::contributing_weight`] for the denominator.
    /// **The ratio is deliberately not offered.** The threshold at which a
    /// pinned fraction should trigger a correction is the consumer's policy;
    /// baking it in here would put it beyond the reach of the consumer's own
    /// controls.
    #[inline]
    pub fn clipped_weight(&self, p: CfaPlane, i: usize) -> Option<f32> {
        let s = Self::slot(p);
        if self.clip_w[s].is_empty() {
            None
        } else {
            Some(self.clip_w[s][i])
        }
    }

    /// The total weight [`Estimator::value`] divides by at this pixel — the
    /// denominator [`Estimator::clipped_weight`] is a numerator for.
    ///
    /// Under the shipped top-hat every admitted frame carries weight exactly
    /// 1.0 and this is the integer admitted count; under a [`SoftKernel`] it is
    /// `sum w`. Returning `value`'s own divisor rather than recomputing a
    /// plausible one is what makes the pinned fraction commensurable with the
    /// merged value by construction rather than by the caller's care.
    #[inline]
    pub fn contributing_weight(&self, i: usize) -> f32 {
        if self.wsum.is_empty() {
            f32::from(self.n[i])
        } else {
            self.wsum[i]
        }
    }

    /// The container maximum this estimator is censoring against, if any.
    pub fn censor_level(&self) -> Option<u16> {
        self.censor_level
    }

    #[inline]
    fn slot(p: CfaPlane) -> usize {
        match p {
            CfaPlane::R => 0,
            CfaPlane::G1 => 1,
            CfaPlane::B => 2,
            CfaPlane::G2 => 3,
        }
    }

    /// Fold one frame's samples in, admitting it where the gate allows.
    ///
    /// `regularised` must be the same field that was folded into pass one for
    /// this `frame_index`, recomputed or cached.
    ///
    /// The winning frame is admitted **unconditionally** at its own pixels. That
    /// is not a convenience: it is what makes `n_eff >= 1` a structural
    /// guarantee rather than a numerical hope, and `n_eff >= 1` is in turn what
    /// makes "never noisier than one frame" provable instead of measured. It
    /// also makes the merge immune to any drift between the two passes'
    /// arithmetic.
    pub fn fold<S: QuadSource + ?Sized>(
        &mut self,
        frame_index: u16,
        src: &S,
        regularised: &[f32],
    ) -> Result<()> {
        self.fold_inner(frame_index, src, regularised, None, 1.0, 0.0)
    }

    /// [`Estimator::fold`], plus the saturation bookkeeping the plain fold
    /// cannot do.
    ///
    /// `container_max_dn` is the raw value at which the container pins — for
    /// this project [`crate::clip::CONTAINER_MAX_DN`], **not** `Levels::white`,
    /// which is a declared calibration bound and is not where real data pins.
    ///
    /// The rule is keyed on the **winner**, and that is the whole of the design:
    ///
    /// * If the winner's own sample on a plane is pinned, the estimate there is
    ///   a lower bound, not a mean. Averaging a censored observation with
    ///   uncensored ones estimates neither quantity, and it can only move the
    ///   result *down*, away from a value we know the truth is at or above.
    ///   [`Estimator::value`] therefore reports the pin and
    ///   [`Estimator::is_censored`] reports why.
    /// * If the winner's sample is *not* pinned, nothing is excluded. A pinned
    ///   sample from some other admitted frame is recorded by
    ///   [`Estimator::has_censored_contributor`] and still summed.
    ///
    /// What this deliberately does **not** do is let saturation touch the focus
    /// volume or the winner election. M54 measured that: propagating the mask
    /// into the election moves the winner at 2.7% (`coffee-bean`) to 7.0%
    /// (`coffee-bubbles`) of the plane, 30x to 240x more pixels than are
    /// actually clipped at their winner, almost all of them pixels that are
    /// never clipped in any frame, and it darkens real highlights by 1000-3300
    /// DN because it is structurally forbidden from ever electing the frame in
    /// which a highlight is brightest.
    pub fn fold_censored<S: QuadSource + ?Sized>(
        &mut self,
        frame_index: u16,
        src: &S,
        regularised: &[f32],
        container_max_dn: u16,
    ) -> Result<()> {
        self.fold_inner(
            frame_index,
            src,
            regularised,
            Some(container_max_dn),
            1.0,
            0.0,
        )
    }

    /// [`Estimator::fold_censored`], with a per-frame **affine photometric
    /// correction** applied to the disagreement accumulator only.
    ///
    /// `L' = L * luma_scale + luma_offset`. The four `sum` planes, `n_eff`, the
    /// gate and the censoring bits are all untouched, so **this cannot change
    /// the merged image** — it changes only what [`Estimator::disagreement`]
    /// reports.
    ///
    /// It exists to price rival explanations for disagreement, and the affine
    /// form rather than a bare gain is deliberate. M24 measured that per-frame
    /// photometric drift is real across most of the corpus (0.91% peak-to-peak
    /// on `109MSDCF`, 11.70% on `coffee-bean`) and that EXIF does not predict
    /// it, so the correction must be **fitted from the data**. M28 §6 added
    /// *how* to fit the gain — the mean over all pixels, never a median over a
    /// subject-centred region, which absorbs focus signal into what it calls
    /// gain. But M24 §5 left the shape open in as many words: *"Whether a single
    /// global gain per frame suffices, or an offset term is also needed, is
    /// unmeasured."* A scale-only signature cannot ask that question, so this
    /// one carries both terms.
    ///
    /// Passing `luma_offset = 0.0` gives the pure-gain case.
    pub fn fold_censored_probing_photometry<S: QuadSource + ?Sized>(
        &mut self,
        frame_index: u16,
        src: &S,
        regularised: &[f32],
        container_max_dn: u16,
        luma_scale: f32,
        luma_offset: f32,
    ) -> Result<()> {
        self.fold_inner(
            frame_index,
            src,
            regularised,
            Some(container_max_dn),
            luma_scale,
            luma_offset,
        )
    }

    fn fold_inner<S: QuadSource + ?Sized>(
        &mut self,
        frame_index: u16,
        src: &S,
        regularised: &[f32],
        censor_level: Option<u16>,
        luma_scale: f32,
        luma_offset: f32,
    ) -> Result<()> {
        let geom = src.geometry();
        if geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (geom.width, geom.height),
                want: (self.geom.width, self.geom.height),
            });
        }
        if regularised.len() != self.geom.pixels() {
            return Err(Error::DimensionMismatch {
                index: frame_index as usize,
                got: (regularised.len(), 1),
                want: (self.geom.pixels(), 1),
            });
        }
        if let Some(level) = censor_level {
            match self.censor_level {
                None => {
                    self.censor_level = Some(level);
                    self.censor = vec![0u8; self.geom.pixels()];
                    let px = self.geom.pixels();
                    self.clip_w = [vec![0.0; px], vec![0.0; px], vec![0.0; px], vec![0.0; px]];
                }
                Some(prev) => assert_eq!(
                    prev, level,
                    "frames folded against different container maxima are not commensurable"
                ),
            }
        } else if self.censor_level.is_some() {
            panic!("an estimator cannot mix fold and fold_censored");
        }

        let off = [
            CfaPlane::R.rggb_offset(),
            CfaPlane::G1.rggb_offset(),
            CfaPlane::B.rggb_offset(),
            CfaPlane::G2.rggb_offset(),
        ];
        let w = self.geom.width;
        // Constructed once per fold, not per pixel. `Gate::new` has already
        // proved the threshold finite and non-negative, so this cannot trip
        // `SoftGate::new`'s assert. Shares `Gate::tolerance` bit-for-bit.
        let soft = SoftGate::new(self.gate.threshold);

        for py in 0..self.geom.height {
            let (row0, row1) = src.quad_rows(py);
            let base = py * w;
            for px in 0..w {
                let i = base + px;
                let winner = self.best_index[i] == frame_index;
                // `wt`, not `w` -- `w` is the plane width three lines up.
                let wt = match self.soft {
                    None => {
                        if !(winner || self.gate.admits(regularised[i], self.best_focus[i])) {
                            continue;
                        }
                        1.0f32
                    }
                    Some(kernel) => {
                        let raw = kernel.weight(&soft, regularised[i], self.best_focus[i]);
                        // The winner is *pinned* rather than trusted to score a
                        // zero gap. `best_focus[i]` is the max of the
                        // regularised field so a tie is expected and the kernel
                        // already returns 1.0 -- but "the elected frame always
                        // contributes in full" is an invariant of the merge and
                        // must not silently depend on that coincidence.
                        let raw = if winner { raw.max(1.0) } else { raw };
                        if raw <= 0.0 {
                            continue;
                        }
                        raw
                    }
                };
                let mut greens = [0u16; 2];
                for (s, (ox, oy)) in off.iter().enumerate() {
                    let row = if *oy == 0 { row0 } else { row1 };
                    let v = row[2 * px + ox];
                    if let Some(level) = censor_level
                        && v >= level
                    {
                        self.censor[i] |= 1 << if winner { s } else { s + 4 };
                        // The same `wt` the sum below is weighted by, on the
                        // same branch, after the gate's `continue`. Numerator
                        // and denominator therefore cannot drift apart.
                        self.clip_w[s][i] += wt;
                    }
                    // Slots 1 and 3 are G1 and G2 -- see `Estimator::slot`.
                    if s == 1 {
                        greens[0] = v;
                    } else if s == 3 {
                        greens[1] = v;
                    }
                    // Multiplying by a `wt` that is exactly 1.0 on the hard path
                    // is the IEEE-754 identity, so the shipped bytes cannot move
                    // -- and that is proved by render, not by this comment.
                    self.sum[s][i] += wt * v as f32;
                }
                if !self.luma_sum.is_empty() {
                    // The same `L = (G1 + G2)/2` the output and the noise model
                    // use, and captured from the two samples that were just
                    // summed above rather than re-read from the source, so the
                    // variance cannot drift from the mean it belongs to.
                    let raw = 0.5 * (f32::from(greens[0]) + f32::from(greens[1]));
                    // The identity correction holds on every product path, and
                    // the compiler cannot know that, so keep the arithmetic
                    // exact in the common case rather than paying a rounding
                    // step for a diagnostic that is almost never enabled.
                    let luma = if luma_scale == 1.0 && luma_offset == 0.0 {
                        f64::from(raw)
                    } else {
                        f64::from(raw * luma_scale + luma_offset)
                    };
                    // Weighted in step with `sum` above. If `luma_sum` were
                    // weighted and its divisor were not -- or vice versa -- the
                    // noise diagnostic would silently change meaning while still
                    // returning plausible numbers. `disagreement` divides by
                    // `wsum`, and both reduce exactly on 0/1 weights.
                    let wl = f64::from(wt);
                    self.luma_sum[i] += wl * luma;
                    self.luma_sumsq[i] += wl * luma * luma;
                }
                self.n[i] += 1;
                if !self.wsum.is_empty() {
                    self.wsum[i] += wt;
                    self.wsq[i] += wt * wt;
                }
            }
        }
        self.frames += 1;
        Ok(())
    }

    /// Reduce another worker's partial pass-two state into this one.
    ///
    /// Both must have been built from the same pass one, which is checked: the
    /// winner fields must be identical, otherwise the two halves gated against
    /// different references and the sums are not commensurable.
    pub fn absorb(&mut self, other: &Estimator) -> Result<()> {
        if other.geom != self.geom {
            return Err(Error::DimensionMismatch {
                index: usize::MAX,
                got: (other.geom.width, other.geom.height),
                want: (self.geom.width, self.geom.height),
            });
        }
        assert_eq!(
            self.best_index, other.best_index,
            "estimators gated against different winner fields cannot be reduced"
        );
        assert_eq!(self.gate, other.gate, "estimators used different gates");
        assert_eq!(
            self.soft, other.soft,
            "estimators used different admission kernels and cannot be reduced"
        );
        assert_eq!(
            self.censor_level, other.censor_level,
            "estimators censored against different container maxima cannot be reduced"
        );
        if !other.censor.is_empty() {
            if self.censor.is_empty() {
                self.censor = vec![0u8; self.geom.pixels()];
            }
            for (a, b) in self.censor.iter_mut().zip(&other.censor) {
                *a |= *b;
            }
            if self.clip_w[0].is_empty() {
                let px = self.geom.pixels();
                self.clip_w = [vec![0.0; px], vec![0.0; px], vec![0.0; px], vec![0.0; px]];
            }
            for (dst, src) in self.clip_w.iter_mut().zip(&other.clip_w) {
                for (a, b) in dst.iter_mut().zip(src) {
                    *a += *b;
                }
            }
        }
        for i in 0..self.geom.pixels() {
            for s in 0..4 {
                self.sum[s][i] += other.sum[s][i];
            }
            self.n[i] += other.n[i];
        }
        if !self.wsum.is_empty() {
            for i in 0..self.geom.pixels() {
                self.wsum[i] += other.wsum[i];
                self.wsq[i] += other.wsq[i];
            }
        }
        if !other.luma_sum.is_empty() {
            assert!(
                !self.luma_sum.is_empty(),
                "one estimator tracked disagreement and the other did not; their \
                 variances are not commensurable"
            );
            for i in 0..self.geom.pixels() {
                self.luma_sum[i] += other.luma_sum[i];
                self.luma_sumsq[i] += other.luma_sumsq[i];
            }
        } else {
            assert!(
                self.luma_sum.is_empty(),
                "one estimator tracked disagreement and the other did not; their \
                 variances are not commensurable"
            );
        }
        self.frames += other.frames;
        Ok(())
    }

    /// Noise-normalised disagreement among the frames this pixel actually
    /// averaged, or `None` where there is nothing to disagree about.
    ///
    /// Returns `s2 / sigma_pred^2`, where `s2` is the unbiased sample variance
    /// of the admitted frames' green luma and `sigma_pred` is what the
    /// calibrated model predicts for a *single* frame at that luma. **Under the
    /// null "the admitted frames differ only by sensor noise" the expectation is
    /// exactly 1.0, for every `n >= 2`** — the null is analytic, so a clean
    /// stack is a test of this statistic rather than the calibration set for it.
    ///
    /// `None` at every pixel where `n_eff == 1`, and that is not a corner case:
    /// at the shipped gate it is 41.66% of `109MSDCF` and the large majority of
    /// a stack that cannot reach `n_eff = 3` anywhere. A caller that averages
    /// this over "the pixels that have it" is measuring a *sub-population*, and
    /// fact 688 is the standing example of what that costs. Report
    /// [`Estimator::disagreement_exposure`] beside any aggregate of this.
    ///
    /// # What this can and cannot support
    ///
    /// It is a **detector, not a corrector.** A variance says the admitted set
    /// disagrees; it cannot say *which* frame to down-weight, because the
    /// per-frame residuals were summed away. Recovering those needs either a
    /// third pass or per-frame state, and §2 of `M60-robustness-mask-at-merge-time.md`
    /// argues that choice explicitly.
    ///
    /// # Panics
    ///
    /// If [`Estimator::track_disagreement`] was never called.
    pub fn disagreement(&self, noise: &NoiseModel, i: usize, black_dn: f32) -> Option<f64> {
        assert!(
            !self.luma_sum.is_empty(),
            "track_disagreement was not called on this estimator"
        );
        // Reliability-weighted sufficient statistics. On 0/1 weights `wsum` is
        // `n`, `wsq` is `n`, `n_eff` is `n`, and the denominator is
        // `n - n/n = n - 1` -- so every line below reduces *exactly* to the
        // boolean form and the hard path's numbers cannot move.
        let (wsum, denom, n_eff) = if self.wsum.is_empty() {
            let n = f64::from(self.n[i]);
            (n, n - 1.0, n)
        } else {
            let ws = f64::from(self.wsum[i]);
            let wq = f64::from(self.wsq[i]);
            if ws <= 0.0 || wq <= 0.0 {
                return None;
            }
            (ws, ws - wq / ws, ws * ws / wq)
        };
        if n_eff < 2.0 || denom <= 0.0 {
            return None;
        }
        let mean = self.luma_sum[i] / wsum;
        // Unbiased sample variance, clamped at zero: the two-pass form can go
        // very slightly negative on a pixel whose frames are all identical.
        let s2 = ((self.luma_sumsq[i] - wsum * mean * mean) / denom).max(0.0);
        let sigma = f64::from(noise.green_luma_sigma((mean - f64::from(black_dn)) as f32));
        if sigma <= 0.0 {
            return None;
        }
        Some(s2 / (sigma * sigma))
    }

    /// Fraction of pixels at which [`Estimator::disagreement`] is defined.
    ///
    /// This is the **entire surface any robustness mask could ever act on**: a
    /// pixel that admitted one frame has no disagreement to measure and no
    /// second frame to prefer. Every aggregate disagreement number in a report
    /// must be published with this beside it.
    ///
    /// # Panics
    ///
    /// If [`Estimator::track_disagreement`] was never called.
    pub fn disagreement_exposure(&self) -> f64 {
        assert!(
            !self.luma_sum.is_empty(),
            "track_disagreement was not called on this estimator"
        );
        let exposed = if self.wsum.is_empty() {
            self.n.iter().filter(|&&n| n >= 2).count()
        } else {
            // The same admissibility test `disagreement` applies, so the
            // exposure and the statistic can never describe different
            // populations.
            (0..self.geom.pixels())
                .filter(|&i| {
                    let ws = f64::from(self.wsum[i]);
                    let wq = f64::from(self.wsq[i]);
                    wq > 0.0 && ws > 0.0 && ws * ws / wq >= 2.0
                })
                .count()
        };
        exposed as f64 / self.geom.pixels() as f64
    }

    /// The merged estimate for one plane at one pixel, in raw DN.
    ///
    /// Under [`Estimator::fold_censored`] this returns the container maximum
    /// wherever the winner's own sample was pinned there — see
    /// [`Estimator::is_censored`]. Under [`Estimator::fold`] it is always the
    /// plain admitted mean.
    #[inline]
    pub fn value(&self, p: CfaPlane, i: usize) -> f32 {
        let s = Self::slot(p);
        if let Some(level) = self.censor_level
            && self.censor[i] & (1 << s) != 0
        {
            return level as f32;
        }
        let n = self.n[i];
        debug_assert!(n > 0, "pixel {i} admitted no frame");
        if self.wsum.is_empty() {
            self.sum[s][i] / n as f32
        } else {
            self.sum[s][i] / self.wsum[i]
        }
    }

    /// Green as the output uses it, `(G1 + G2) / 2`, still in raw DN.
    #[inline]
    pub fn green_mean(&self, i: usize) -> f32 {
        0.5 * (self.value(CfaPlane::G1, i) + self.value(CfaPlane::G2, i))
    }

    /// Predicted standard deviation of the merged green luma at a pixel, in DN.
    ///
    /// This is confidence channel C1 of M34's vector. It is a *prediction from
    /// the calibrated model*, not a measurement of the output, which is what
    /// makes it available per pixel with no second capture.
    ///
    /// Averaging `n` independent frames divides the standard deviation by
    /// `sqrt(n)`, and `n = 1` is then penalised by [`selection_inflation`]
    /// because one admitted frame means *selection*, not "no averaging". The
    /// frames are independent in their sensor noise; they are not independent
    /// in their fixed-pattern noise, so this remains a floor rather than a
    /// complete account.
    pub fn predicted_sigma(&self, noise: &NoiseModel, i: usize, black_dn: f32) -> f32 {
        let luma = self.green_mean(i) - black_dn;
        let n = self.n[i];
        // Under a soft kernel the mean is a *weighted* one, so the variance it
        // carries falls as `1/n_eff` (Kish), not as `1/n`. Dividing by the raw
        // admitted count here while `value` divides by `wsum` would report a
        // noise floor the estimator does not have -- the same silent
        // change-of-meaning hazard M111 flagged for `disagreement`.
        // `selection_inflation` still keys off the integer count, because
        // "exactly one frame contributed" is a discrete fact about selection.
        let eff = match self.soft_n_eff_at(i) {
            Some(e) => e,
            None => f64::from(n),
        };
        noise.green_luma_sigma(luma) * selection_inflation(n) / (eff as f32).sqrt()
    }

    /// Did this pixel's winner land on the first or last frame of the stack?
    ///
    /// Confidence channel C4. Mass at the bracket boundary means the true peak
    /// is plausibly outside the capture, so no frame here is in focus and the
    /// merge cannot know it.
    ///
    /// **This is not fact 300's quantity, and the two must not be compared.**
    /// M35 measured 7.38% of `119MSDCF` "at the boundary" using
    /// `(argmax <= 1) | (argmax >= n-2)` — two frames deep at each end, on a
    /// *decimated* stack, from an *unregularised* argmax. This is one frame
    /// deep, on the full stack, from the regularised winner, so it reads
    /// strictly lower: 2.02% on the same stack. M38 confirmed the two scale
    /// together (7.38/2.02 = 3.65 against 2.08/0.61 = 3.41 on `112MSDCF`,
    /// agreeing to 7%), which is why this is a definition gap and not a
    /// contradiction. Cite one or the other, never both as one number.
    #[inline]
    pub fn at_bracket_boundary(&self, i: usize) -> bool {
        let k = self.best_index[i];
        k == 0 || k == self.max_index
    }

    /// Every pixel admitted at least one frame.
    ///
    /// Structurally guaranteed by the unconditional admission of the winner, so
    /// a false here is a bug in this module and not a property of the data.
    pub fn every_pixel_is_decided(&self) -> bool {
        self.n.iter().all(|n| *n > 0)
    }

    /// Mean frames admitted per pixel, the stack-level `n_eff`.
    pub fn mean_n_eff(&self) -> f64 {
        if self.geom.pixels() == 0 {
            return 0.0;
        }
        self.n.iter().map(|n| *n as f64).sum::<f64>() / self.geom.pixels() as f64
    }

    /// Mean over pixels of the per-pixel noise gain `predicted_sigma / single`.
    ///
    /// This is the honest answer to "how much did the merge reduce noise", and
    /// it is deliberately routed **through [`Self::predicted_sigma`]** rather
    /// than recomputed from `n`. Facts 452/453: the CLI used to print
    /// `1/sqrt(mean_n_eff)`, which is wrong twice over.
    ///
    /// * It never consulted the noise model, so it could not see
    ///   [`selection_inflation`] and printed exactly `1.0000x` at gate 0 — the
    ///   very number fact 341 filed as a defect.
    /// * `1/sqrt(E[n])` is not `E[1/sqrt(n)]`. Jensen's inequality runs one way
    ///   here — `1/sqrt(.)` is convex, so `E[1/sqrt(n)] >= 1/sqrt(E[n])` — and
    ///   the old form therefore **understated** the achieved sigma, measured at
    ///   4.22%, 5.88%, 4.70% and 2.43% at gates 0.5, 1.0, 2.0 and 4.0. It
    ///   reported the merge as quieter than it is.
    ///
    /// Going through `predicted_sigma` means any future term added to the model
    /// appears here automatically instead of having to be remembered.
    #[must_use]
    pub fn mean_predicted_sigma_gain(&self, noise: &NoiseModel, black_dn: f32) -> f64 {
        let px = self.geom.pixels();
        if px == 0 {
            return 0.0;
        }
        let total: f64 = (0..px)
            .map(|i| {
                let single = noise.green_luma_sigma(self.green_mean(i) - black_dn);
                if single > 0.0 {
                    f64::from(self.predicted_sigma(noise, i, black_dn) / single)
                } else {
                    // A pixel with no modelled noise has no gain to report; 1.0
                    // is the neutral element and keeps the mean well defined.
                    1.0
                }
            })
            .sum();
        total / px as f64
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::focus::FocusField;
    use crate::noise::{Levels, NoiseModel, PlaneNoise, Provenance};
    use crate::plane::testing::QuadGrid;

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    /// A noise model whose green-luma sigma is 1.0 DN and is effectively flat in
    /// signal, so the focus normalisation divides by a known constant.
    ///
    /// The gain must be non-zero. `PlaneNoise` derives its read noise in DN as
    /// `read_noise_e * gain_dn_per_e`, so a zero gain gives a zero sigma, which
    /// `FocusField::compute` then clamps to `SIGMA_EPS` and the whole response
    /// is scaled by 1000. That is exactly the trap this comment exists to stop
    /// the next person falling into: it does not error, it silently rescales.
    fn unit_sigma_model() -> NoiseModel {
        // Var(L) = (Var(G1) + Var(G2)) / 4 = read_dn^2 / 2 for equal planes, so
        // read_dn = sqrt(2) gives sigma_L = 1. Gain is small enough that the
        // shot term is negligible over the signal range these tests use.
        let gain = 1e-4;
        let p = PlaneNoise {
            gain_dn_per_e: gain,
            read_noise_e: std::f32::consts::SQRT_2 / gain,
            levels: Levels {
                black: 0.0,
                white: 16383.0,
            },
        };
        NoiseModel::new([p; 4], 100.0, Provenance::Measured)
    }

    /// Deterministic standard normals. **SplitMix64** feeding Box-Muller: the
    /// tests must not depend on the host's RNG or on a crate.
    ///
    /// The generator choice is load-bearing and was arrived at the hard way. A
    /// plain LCG here made [`FOCUS_NOISE_SD`] vary by **1.30x across seeds**
    /// (0.01172 / 0.01371 / 0.01522) when sampling error on ~19,000 interior
    /// pixels should be well under 1%. Consecutive LCG outputs lie on lattice
    /// planes, Box-Muller consumes them in pairs, and filling a raster grid with
    /// the result lays that lattice out *spatially* — where a 27-box followed by
    /// a 17-box aliases against it differently for every seed. A single-seed
    /// measurement would have silently baked a 30% error into the gate.
    struct Rng(u64);
    impl Rng {
        fn new(seed: u64) -> Self {
            Rng(seed)
        }
        fn next_u64(&mut self) -> u64 {
            self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = self.0;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            z ^ (z >> 31)
        }
        fn uniform(&mut self) -> f64 {
            // In (0, 1], never 0, so ln() is finite.
            ((self.next_u64() >> 11) as f64 + 1.0) / (1u64 << 53) as f64
        }
        fn normal(&mut self) -> f32 {
            let (u1, u2) = (self.uniform(), self.uniform());
            ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
        }
    }

    /// **The measurement behind [`FOCUS_NOISE_SD`].**
    ///
    /// A pure-noise plane carries no focus signal, so every bit of spread in the
    /// regularised response is the operator's own noise. That spread is exactly
    /// the scale the gate needs, and measuring it here rather than deriving it
    /// analytically means the answer includes the correlation between
    /// overlapping Sobel stencils inside the box, which a closed form would have
    /// had to assume away — a factor of 3.2, see [`FOCUS_NOISE_SD`].
    ///
    /// # Why the tolerance is derived and not chosen
    ///
    /// The interior holds ~219,000 pixels but they are **not** 219,000
    /// measurements: each response averages a `43 x 43` support, so neighbouring
    /// responses are nearly the same number and only about `(468/43)^2 = 118`
    /// are independent per seed. An estimated standard deviation from `n`
    /// samples has a relative error near `1/sqrt(2(n-1))`, so one seed is worth
    /// about 6.5%. Picking a round tolerance here would have been picking
    /// whether the test passes: an earlier draft asserted 5% seed-to-seed
    /// stability, which no honest version of this measurement could ever have
    /// met. So the test computes the standard error of its own mean across seeds
    /// and requires the declared constant to sit inside four of them — and
    /// separately requires that standard error to be small, otherwise the band
    /// is wide enough to admit anything and the test has no power.
    ///
    /// # Why the plane is this large
    ///
    /// A sample standard deviation taken over a region only a few supports
    /// across is biased **low**, because the mean it subtracts is itself
    /// correlated with the samples. At `192 x 192` this measured 0.01366 — 10%
    /// under the truth — and it drifted with plane size, which is a falsifiable
    /// signature rather than a mystery. `384` gives `0.015277 +/- 0.000223` and
    /// `512` gives `0.015214 +/- 0.000075`: a difference of 0.27 standard
    /// errors, so the bias is spent by `384` and the number has converged. The
    /// larger plane is kept for the tighter interval.
    ///
    /// The **mean** is checked against closed form as well, and that check is
    /// the one that would catch the operator chain being wrong rather than just
    /// noisy. Under unit luma noise the gradient magnitude is Rayleigh with
    /// scale `0.125 * sqrt(12)`, whose mean is `0.4330 * sqrt(pi/2) = 0.5427`;
    /// neither box mean changes a mean. A silent rescale — the zero-gain trap
    /// documented on `unit_sigma_model` — moves this by three orders of
    /// magnitude while leaving the standard deviation looking plausible.
    /// The selection penalty is a measurement, not a tuning knob — and it is
    /// currently **absent**, not merely small. M40 refuted the shipped 1.074x
    /// on four independent grounds (facts 440, 443, 446, 454): it multiplied a
    /// temporal sigma by a ratio of spatial ones, it exceeded the maximum its
    /// own mechanism can produce, it varied from 0.9841 to 1.2732 across six
    /// ROIs, and on a detail-free plant it drove the corrected metric to
    /// -11.63 DN where truth is 0 — further from truth than the defect it
    /// replaced.
    ///
    /// This test therefore pins 1.0 and exists to make substituting a
    /// plausible-looking value a deliberate act. If you are here because you
    /// want to put a number back, the bar is a **temporal, structure-free**
    /// estimator measured in this crate, and fact 448 says the result should be
    /// a smooth function of `n`, not a step.
    #[test]
    fn the_selection_penalty_is_absent_until_it_is_measured() {
        assert_eq!(
            SELECTION_INFLATION, 1.0,
            "1.074x was refuted by M40 (facts 440/443/446/454) and reverted; a \
             replacement must be measured with a temporal, structure-free \
             estimator in this crate, not assumed"
        );
        assert_eq!(
            selection_inflation(0),
            SELECTION_INFLATION,
            "n = 0 clamps to 1"
        );
        assert_eq!(
            selection_inflation(1),
            SELECTION_INFLATION,
            "n = 1 is selection"
        );
        assert_eq!(
            selection_inflation(2),
            1.0,
            "n > 1 carries no penalty either, for now"
        );
        // The two-branch shape is load-bearing even while both branches agree:
        // fact 458 puts 41.66% of the plane at n = 1 at a working gate.
        assert_eq!(
            selection_inflation(1),
            selection_inflation(9),
            "both branches are 1.0 today; this equality is what a measured \
             penalty is expected to BREAK, and the shape is kept for it"
        );
    }

    #[test]
    fn the_focus_noise_constant_is_the_measured_one() {
        let g = geom(512, 512);
        let noise = unit_sigma_model();
        let margin = crate::focus::SUPPORT_RADIUS + REGULARISER_RADIUS;
        let seeds: [u64; 12] = [
            0xC0FFEE,
            0x5EED,
            0xBADF00D,
            1,
            2,
            3,
            0xDEADBEEF,
            0x1234_5678,
            99,
            0xFACE,
            0xA5A5_A5A5,
            7,
        ];

        let mut sds = Vec::new();
        let mut means = Vec::new();
        let mut field = FocusField::new(g);
        let mut scratch = vec![0.0; g.pixels()];
        let mut reg = vec![0.0; g.pixels()];
        for seed in seeds {
            let mut rng = Rng::new(seed);
            let luma: Vec<f32> = (0..g.pixels()).map(|_| rng.normal()).collect();
            field.compute(&luma, &noise);
            regularise(field.values(), g, &mut scratch, &mut reg);

            let mut vals = Vec::new();
            for y in margin..g.height - margin {
                for x in margin..g.width - margin {
                    vals.push(reg[y * g.width + x] as f64);
                }
            }
            assert!(vals.len() > 10_000, "not enough interior samples");
            let mean = vals.iter().sum::<f64>() / vals.len() as f64;
            let var =
                vals.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (vals.len() - 1) as f64;
            means.push(mean);
            sds.push(var.sqrt());
        }

        // Closed form: Rayleigh(0.125 * sqrt(12)) has mean 0.5427, and a box
        // mean does not move it. This is the structural check.
        let rayleigh_mean = 0.125 * 12f64.sqrt() * (std::f64::consts::PI / 2.0).sqrt();
        for m in &means {
            let r = m / rayleigh_mean;
            assert!(
                (0.97..1.03).contains(&r),
                "pure-noise response mean {m:.4} is {r:.3}x the closed-form \
                 Rayleigh mean {rayleigh_mean:.4}; the operator chain is not \
                 doing what this test assumes"
            );
        }

        let n = sds.len() as f64;
        let mean_sd = sds.iter().sum::<f64>() / n;
        let spread = sds.iter().map(|s| (s - mean_sd).powi(2)).sum::<f64>() / (n - 1.0);
        let sem = (spread / n).sqrt();
        let rel_sem = sem / mean_sd;

        // The test must be able to fail. If the seeds happened to agree to
        // within nothing, the band below would admit any constant at all.
        assert!(
            rel_sem < 0.05,
            "standard error {rel_sem:.4} is too large for this test to have \
             power; add seeds or enlarge the plane. sds = {sds:?}"
        );

        let deviation = ((mean_sd - FOCUS_NOISE_SD as f64) / sem).abs();
        assert!(
            deviation < 4.0,
            "measured focus noise SD {mean_sd:e} +/- {sem:e} is {deviation:.1} \
             standard errors from the declared FOCUS_NOISE_SD \
             {FOCUS_NOISE_SD:e} (relative SEM {rel_sem:.4}); if the operator or \
             either radius changed, re-measure and update the constant"
        );
    }

    /// The constant is only meaningful if it is small against real focus
    /// contrast. If a real through-focus swing were the same size as the noise
    /// SD, the gate would admit everything and the merge would be a plain mean —
    /// which fact 24 says destroys detail.
    #[test]
    fn real_focus_contrast_is_far_larger_than_the_noise_scale() {
        let g = geom(192, 192);
        let noise = unit_sigma_model();
        let mut rng = Rng::new(7);

        // Same texture at two blur levels: a sharp checker versus a 2x2 mean of
        // it, both with the same noise added.
        let sharp: Vec<f32> = (0..g.pixels())
            .map(|i| {
                let (x, y) = (i % g.width, i / g.width);
                let s = if (x / 2 + y / 2) % 2 == 0 { 60.0 } else { 20.0 };
                s + rng.normal()
            })
            .collect();
        let blurred: Vec<f32> = (0..g.pixels())
            .map(|i| {
                let (x, y) = (i % g.width, i / g.width);
                let s = if (x / 4 + y / 4) % 2 == 0 { 45.0 } else { 35.0 };
                s + rng.normal()
            })
            .collect();

        let mut field = FocusField::new(g);
        let mut scratch = vec![0.0; g.pixels()];
        let (mut a, mut b) = (vec![0.0; g.pixels()], vec![0.0; g.pixels()]);
        field.compute(&sharp, &noise);
        regularise(field.values(), g, &mut scratch, &mut a);
        field.compute(&blurred, &noise);
        regularise(field.values(), g, &mut scratch, &mut b);

        let m = crate::focus::SUPPORT_RADIUS + REGULARISER_RADIUS;
        let c = m * g.width + m;
        let contrast = a[c] - b[c];
        assert!(
            contrast > 20.0 * FOCUS_NOISE_SD,
            "focus contrast {contrast:e} is not clear of the noise scale \
             {FOCUS_NOISE_SD:e}; the gate cannot discriminate"
        );
    }

    // ---- gate ----

    #[test]
    fn a_zero_threshold_admits_only_the_winner() {
        let gate = Gate::new(0.0);
        assert!(gate.admits(1.0, 1.0));
        assert!(!gate.admits(1.0 - 1e-6, 1.0));
    }

    #[test]
    fn the_gate_admits_within_its_tolerance_and_not_beyond() {
        let gate = Gate::new(2.0);
        let t = gate.tolerance();
        // Bracketed either side of the boundary rather than exactly on it. The
        // tolerance is ~1e-2 against a reference of 10, so `10.0 - t` is not
        // exactly representable and testing the boundary itself would be
        // testing f32 cancellation rather than the gate.
        assert!(gate.admits(10.0 - 0.5 * t, 10.0));
        assert!(gate.admits(10.0 - 0.99 * t, 10.0));
        assert!(!gate.admits(10.0 - 1.01 * t, 10.0));
        assert!(!gate.admits(10.0 - 2.0 * t, 10.0));
    }

    #[test]
    fn a_non_finite_response_is_never_admitted() {
        let gate = Gate::new(3.0);
        assert!(!gate.admits(f32::NAN, 1.0));
        assert!(!gate.admits(f32::NEG_INFINITY, 1.0));
    }

    #[test]
    #[should_panic(expected = "non-negative")]
    fn a_negative_threshold_is_rejected_rather_than_silently_inverting_the_gate() {
        Gate::new(-1.0);
    }

    // ---- pass one ----

    fn stats_over(order: &[u16], g: PlaneGeometry, f: impl Fn(u16, usize) -> f32) -> FocusStats {
        let mut s = FocusStats::new(g);
        for k in order {
            let field: Vec<f32> = (0..g.pixels()).map(|i| f(*k, i)).collect();
            s.fold(*k, &field).unwrap();
        }
        s
    }

    #[test]
    fn pass_one_elects_the_highest_response_and_is_order_independent() {
        let g = geom(9, 7);
        let f = |k: u16, i: usize| ((i * 37 + k as usize * 11) % 23) as f32;
        let a = stats_over(&[0, 1, 2, 3, 4], g, f);
        let b = stats_over(&[4, 3, 2, 1, 0], g, f);
        let c = stats_over(&[2, 0, 4, 1, 3], g, f);
        assert_eq!(a.best_index(), b.best_index());
        assert_eq!(a.best_index(), c.best_index());
        assert_eq!(a.best_focus(), b.best_focus());
        assert_eq!(a.frames_folded(), 5);
    }

    #[test]
    fn pass_one_absorb_matches_a_single_sequential_fold() {
        let g = geom(9, 7);
        let f = |k: u16, i: usize| ((i * 37 + k as usize * 11) % 23) as f32;
        let whole = stats_over(&[0, 1, 2, 3, 4, 5], g, f);
        for cut in 1..6usize {
            let all: Vec<u16> = (0..6).collect();
            let mut left = stats_over(&all[..cut], g, f);
            let right = stats_over(&all[cut..], g, f);
            left.absorb(&right).unwrap();
            assert_eq!(left.best_index(), whole.best_index(), "cut {cut}");
            assert_eq!(left.best_focus(), whole.best_focus(), "cut {cut}");
            assert_eq!(left.frames_folded(), whole.frames_folded());
            assert_eq!(left.max_index(), whole.max_index());
        }
    }

    #[test]
    fn pass_one_rejects_a_mismatched_field() {
        let mut s = FocusStats::new(geom(4, 4));
        assert!(matches!(
            s.fold(0, &[0.0; 9]),
            Err(Error::DimensionMismatch { .. })
        ));
    }

    // ---- pass two ----

    /// Frame `k` of a synthetic stack: a constant value per frame so the mean
    /// over an acceptance set is exactly predictable.
    fn flat_frame(k: u16, g: PlaneGeometry) -> QuadGrid {
        QuadGrid::new(g.width, g.height, |_, _| {
            let v = 100 + 10 * k;
            [v, v + 1, v + 2, v + 3]
        })
    }

    fn run(
        g: PlaneGeometry,
        n_frames: u16,
        gate: Gate,
        focus: impl Fn(u16, usize) -> f32,
    ) -> Estimator {
        let mut stats = FocusStats::new(g);
        for k in 0..n_frames {
            let field: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
            stats.fold(k, &field).unwrap();
        }
        let mut est = Estimator::new(&stats, gate);
        for k in 0..n_frames {
            let field: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
            est.fold(k, &flat_frame(k, g), &field).unwrap();
        }
        est
    }

    #[test]
    fn with_one_frame_clearly_sharpest_the_estimator_degenerates_to_a_selector() {
        // Frame 3 stands far above everything: exactly facts 263/264's resolved
        // edge, where the peak is 10^2-10^3 sigma clear and there is nothing
        // for an average to harvest.
        let g = geom(4, 4);
        let est = run(g, 6, Gate::new(3.0), |k, _| if k == 3 { 1.0 } else { 0.0 });
        assert!(est.n_eff().iter().all(|n| *n == 1));
        // Frame 3 carries the quad [130, 131, 132, 133] in QuadGrid's order,
        // which is R, G1, G2, B -- not R, G1, B, G2. The green mean is the two
        // greens, 131 and 132.
        assert_eq!(est.value(CfaPlane::R, 0), 130.0);
        assert_eq!(est.value(CfaPlane::G1, 0), 131.0);
        assert_eq!(est.value(CfaPlane::G2, 0), 132.0);
        assert_eq!(est.value(CfaPlane::B, 0), 133.0);
        assert_eq!(est.green_mean(0), 131.5);
        assert!(est.every_pixel_is_decided());
    }

    #[test]
    fn with_frames_that_agree_the_estimator_averages_them() {
        // Three frames tied at the top, three far below. The gate must take the
        // mean of exactly the three, which is fact 23's "only averaging goes
        // below one frame" and fact 212's nwide = 3.
        let g = geom(4, 4);
        let est = run(g, 6, Gate::new(3.0), |k, _| if k < 3 { 5.0 } else { 0.0 });
        assert!(est.n_eff().iter().all(|n| *n == 3));
        // Frames 0,1,2 carry R = 100, 110, 120.
        assert_eq!(est.value(CfaPlane::R, 0), 110.0);
        assert_eq!(est.mean_n_eff(), 3.0);
    }

    /// **The reported noise gain must be Jensen-correct and model-routed.**
    ///
    /// Facts 452/453. The CLI's gate table printed `1/sqrt(mean_n_eff)`, which
    /// is a different number from the mean of the per-pixel gains whenever the
    /// `n` field is not constant — and it is never constant, because that is
    /// the entire point of an adaptive gate. `1/sqrt(.)` is convex, so Jensen
    /// runs strictly one way: the mean of the gains is **greater than or equal
    /// to** the gain of the mean, with equality only in the degenerate case.
    /// The old form therefore always understated sigma, i.e. reported the merge
    /// as quieter than the model says it is. That is the worst direction for a
    /// number whose job is to be checked against a measurement.
    ///
    /// Two things are pinned here. The Jensen direction, with a case that has
    /// genuinely mixed `n` so the inequality is strict; and the routing, so
    /// that a term added to `predicted_sigma` cannot silently fail to appear in
    /// the reported gain the way [`SELECTION_INFLATION`] once did.
    #[test]
    fn the_reported_noise_gain_is_the_mean_of_gains_not_the_gain_of_the_mean() {
        let g = geom(8, 8);
        let noise = unit_sigma_model();
        // A through-focus curve whose *width* varies by five decades across the
        // plane: every pixel peaks at frame 3, but the curvature does not, so
        // the gate admits a different number of frames at different pixels.
        // This is the whole point — a fixture with constant n_eff cannot
        // exercise Jensen, and an earlier version of this test used one.
        let focus = |k: u16, i: usize| {
            let curv = 0.5 * 0.1f32.powi((i % 6) as i32);
            let d = f32::from(k) - 3.0;
            1.0 - curv * d * d
        };
        let mut saw_strict = false;
        for threshold in [0.0f32, 0.1, 0.3, 0.5, 1.0, 2.0, 3.0, 10.0, 30.0, 100.0] {
            let est = run(g, 7, Gate::new(threshold), focus);
            let reported = est.mean_predicted_sigma_gain(&noise, 0.0);

            // Routing: the gain is exactly what predicted_sigma implies, pixel
            // by pixel. Written out independently of the method under test.
            //
            // The tolerance is 1e-6, not something tighter, and deliberately:
            // `reported` multiplies by the luma sigma inside `predicted_sigma`
            // and divides it back out, in f32, so it carries a fraction of an
            // ulp that `by_hand` does not. Measured discrepancy is ~1e-8, about
            // 0.17 ulp at this magnitude. Any *real* routing error is a
            // multiplicative factor — SELECTION_INFLATION was 7.4% — so 1e-6
            // is four orders of magnitude clear of f32 noise and still four
            // orders inside the smallest defect worth catching.
            let by_hand: f64 = (0..g.pixels())
                .map(|i| {
                    let n = est.n_eff()[i];
                    f64::from(selection_inflation(n) / (n as f32).sqrt())
                })
                .sum::<f64>()
                / g.pixels() as f64;
            assert!(
                (reported - by_hand).abs() < 1e-6,
                "t={threshold}: reported {reported} is not the model's own \
                 per-pixel gain {by_hand}"
            );

            // Jensen: never below the old form, and strictly above it wherever
            // the gate actually produced a spread of n.
            let old_form = 1.0 / est.mean_n_eff().sqrt();
            assert!(
                reported >= old_form - 1e-9,
                "t={threshold}: Jensen violated, {reported} < {old_form}"
            );
            let spread = est.n_eff().iter().any(|n| *n != est.n_eff()[0]);
            if spread {
                saw_strict = true;
                assert!(
                    reported > old_form + 1e-6,
                    "t={threshold}: n varies over the plane, so the two forms \
                     must differ; got {reported} vs {old_form}"
                );
            }
        }
        assert!(
            saw_strict,
            "no gate produced a spread of n_eff, so the Jensen gap was never \
             exercised and this test proved nothing"
        );
    }

    /// **The acceptance invariant, as measurement actually supports it.**
    ///
    /// The old form of this test asserted `merged <= single` at *every* gate,
    /// reasoning that averaging `n` samples scales sigma by `1/sqrt(n)` and
    /// `n >= 1` is structural. That reasoning is wrong at `n = 1`, and it
    /// passed only because `predicted_sigma` was blind in exactly the same
    /// place: `n = 1` is not "averaging one sample", it is **selection**, and
    /// fact 320 measured selection at **1.074x a single frame** — noisier, not
    /// equal. The invariant was being proved against a model that could not
    /// express its own violation.
    ///
    /// The true contract has two branches:
    ///   * `n >= 2` — averaging, and strictly better than one frame.
    ///   * `n == 1` — selection, which is *believed* worse but is **not
    ///     currently priced**. M40 refuted the 1.074x that used to price it, so
    ///     `n = 1` reports the bare single-frame sigma. Gate 0 remains a
    ///     diagnostic rather than a shipping configuration for the same
    ///     underlying reason — it maximises the fraction of the plane sitting
    ///     at `n = 1`, where the model is known to be optimistic.
    #[test]
    fn averaging_beats_one_frame_and_selection_does_not() {
        let g = geom(8, 8);
        let noise = unit_sigma_model();
        let mut saw_selection = false;
        let mut saw_averaging = false;
        for threshold in [0.0f32, 0.5, 1.0, 3.0, 100.0] {
            let est = run(g, 7, Gate::new(threshold), |k, i| {
                ((i * 13 + k as usize * 5) % 11) as f32 * 1e-4
            });
            assert!(est.every_pixel_is_decided(), "t={threshold}");
            for i in 0..g.pixels() {
                let n = est.n_eff()[i];
                assert!(n >= 1, "t={threshold} pixel {i} admitted nothing");
                let merged = est.predicted_sigma(&noise, i, 0.0);
                let single = noise.green_luma_sigma(est.green_mean(i));
                if n == 1 {
                    saw_selection = true;
                    // KNOWN GAP (fact 341, reopened by M40): with no measured
                    // penalty this is equality, not the inequality the mechanism
                    // predicts. Pinned so that measuring a penalty turns this
                    // assertion red and forces the contract to be restated.
                    assert!(
                        (merged - single * SELECTION_INFLATION).abs() < 1e-4,
                        "t={threshold} pixel {i}: n = 1 must track \
                         SELECTION_INFLATION exactly, got {merged} vs {single}"
                    );
                } else {
                    saw_averaging = true;
                    assert!(
                        merged < single,
                        "t={threshold} pixel {i}: averaging {n} frames must beat one, \
                         got {merged} vs {single}"
                    );
                }
                // And the scaling is exactly the model, not approximately.
                let expected = single * selection_inflation(n) / (n as f32).sqrt();
                assert!(
                    (merged - expected).abs() < 1e-4,
                    "t={threshold} pixel {i}: {merged} vs {expected}"
                );
            }
        }
        assert!(
            saw_selection,
            "no n = 1 pixel: the selection branch went untested"
        );
        assert!(
            saw_averaging,
            "no n > 1 pixel: the averaging branch went untested"
        );
    }

    #[test]
    fn a_wide_gate_admits_every_frame_and_a_zero_gate_admits_only_the_winner() {
        let g = geom(4, 4);
        // Responses one tolerance-unit apart so the threshold actually bites.
        let focus = |k: u16, _: usize| k as f32 * FOCUS_NOISE_SD;
        let wide = run(g, 5, Gate::new(1e6), focus);
        assert!(wide.n_eff().iter().all(|n| *n == 5));
        let none = run(g, 5, Gate::new(0.0), focus);
        assert!(none.n_eff().iter().all(|n| *n == 1));
    }

    #[test]
    fn the_acceptance_set_widens_monotonically_with_the_threshold() {
        let g = geom(4, 4);
        let focus = |k: u16, _: usize| -(k as f32) * FOCUS_NOISE_SD;
        let mut last = 0.0;
        for t in [0.0f32, 0.5, 1.0, 2.0, 4.0, 8.0] {
            let n = run(g, 8, Gate::new(t), focus).mean_n_eff();
            assert!(n >= last, "n_eff fell from {last} to {n} at threshold {t}");
            last = n;
        }
        assert_eq!(last, 8.0);
    }

    #[test]
    fn pass_two_is_order_independent_and_absorb_matches_a_sequential_fold() {
        let g = geom(6, 5);
        let focus = |k: u16, i: usize| (((i * 7 + k as usize * 3) % 5) as f32) * FOCUS_NOISE_SD;
        let gate = Gate::new(1.5);

        let mut stats = FocusStats::new(g);
        for k in 0..6u16 {
            let f: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
            stats.fold(k, &f).unwrap();
        }
        let fold_set = |ks: &[u16]| {
            let mut e = Estimator::new(&stats, gate);
            for k in ks {
                let f: Vec<f32> = (0..g.pixels()).map(|i| focus(*k, i)).collect();
                e.fold(*k, &flat_frame(*k, g), &f).unwrap();
            }
            e
        };
        let whole = fold_set(&[0, 1, 2, 3, 4, 5]);
        let shuffled = fold_set(&[4, 1, 5, 0, 3, 2]);
        assert_eq!(whole.n_eff(), shuffled.n_eff());
        for i in 0..g.pixels() {
            assert_eq!(whole.value(CfaPlane::R, i), shuffled.value(CfaPlane::R, i));
        }
        for cut in 1..6usize {
            let all: Vec<u16> = (0..6).collect();
            let mut left = fold_set(&all[..cut]);
            left.absorb(&fold_set(&all[cut..])).unwrap();
            assert_eq!(left.n_eff(), whole.n_eff(), "cut {cut}");
            assert_eq!(left.frames_folded(), 6);
            for i in 0..g.pixels() {
                assert!((left.value(CfaPlane::B, i) - whole.value(CfaPlane::B, i)).abs() < 1e-3);
            }
        }
    }

    #[test]
    fn reducing_estimators_from_different_winner_fields_is_refused() {
        let g = geom(4, 4);
        let a = run(g, 3, Gate::new(1.0), |k, _| if k == 0 { 1.0 } else { 0.0 });
        let mut b = run(g, 3, Gate::new(1.0), |k, _| if k == 2 { 1.0 } else { 0.0 });
        assert!(std::panic::catch_unwind(move || b.absorb(&a)).is_err());
    }

    #[test]
    fn a_mismatched_frame_is_rejected_rather_than_silently_cropped() {
        let g = geom(4, 4);
        let stats = FocusStats::new(g);
        let mut est = Estimator::new(&stats, Gate::new(1.0));
        let small = QuadGrid::new(3, 4, |_, _| [1, 1, 1, 1]);
        assert!(matches!(
            est.fold(0, &small, &[0.0; 12]),
            Err(Error::DimensionMismatch { .. })
        ));
    }

    // ---- saturation censoring (M54) ------------------------------------
    //
    // Rule 34 declaration: these fixtures share **no** constant with the code
    // under test. The pin is `TEST_PIN = 4095`, chosen deliberately different
    // from `clip::CONTAINER_MAX_DN = 16383`, so a hard-coded production
    // constant in `fold_censored` would fail every one of these. The expected
    // means below are hand-arithmetic on the fixture's own sample values, not
    // anything read back out of the estimator.

    const TEST_PIN: u16 = 4095;

    /// Three frames tied at the top and one far below, so the gate admits
    /// exactly three. `pinned_at` chooses which of those carries the pinned
    /// greens.
    fn censoring_fixture(g: PlaneGeometry) -> (FocusStats, Vec<Vec<f32>>) {
        // Frame 1 wins everywhere; 0 and 2 sit just inside a threshold-1 gate;
        // frame 3 is far outside it.
        let fields: Vec<Vec<f32>> = (0..4u16)
            .map(|k| {
                let f = match k {
                    1 => 1.0,
                    0 | 2 => 1.0 - 0.5 * FOCUS_NOISE_SD,
                    _ => 0.0,
                };
                vec![f; g.pixels()]
            })
            .collect();
        let mut stats = FocusStats::new(g);
        for (k, f) in fields.iter().enumerate() {
            stats.fold(k as u16, f).unwrap();
        }
        assert!(
            stats.best_index().iter().all(|b| *b == 1),
            "fixture must elect frame 1 everywhere"
        );
        (stats, fields)
    }

    fn censoring_frame(k: u16, g: PlaneGeometry, pinned: &[u16]) -> QuadGrid {
        // R and B stay far from the pin so they act as an in-fixture control:
        // whatever censoring does, it must not touch them.
        let greens = if pinned.contains(&k) { TEST_PIN } else { 1000 };
        QuadGrid::new(g.width, g.height, move |_, _| [200, greens, greens, 300])
    }

    #[test]
    fn a_censored_winner_reports_the_bound_instead_of_a_diluted_mean() {
        let g = geom(4, 4);
        let (stats, fields) = censoring_fixture(g);
        let gate = Gate::new(1.0);

        let mut plain = Estimator::new(&stats, gate);
        let mut cens = Estimator::new(&stats, gate);
        for k in 0..4u16 {
            let frame = censoring_frame(k, g, &[1]);
            plain.fold(k, &frame, &fields[k as usize]).unwrap();
            cens.fold_censored(k, &frame, &fields[k as usize], TEST_PIN)
                .unwrap();
        }

        // Rule 36: the fixture must actually exercise dilution. Three frames
        // admitted, one of them the pinned winner, two of them at 1000.
        assert!(
            cens.n_eff().iter().all(|n| *n == 3),
            "fixture must admit three frames or there is nothing to dilute"
        );
        // Hand arithmetic on the fixture's own numbers: (4095 + 1000 + 1000)/3.
        let diluted = 6095.0f32 / 3.0;
        assert!(diluted < TEST_PIN as f32);
        for i in 0..g.pixels() {
            assert!((plain.value(CfaPlane::G1, i) - diluted).abs() < 1e-3);
            assert_eq!(cens.value(CfaPlane::G1, i), TEST_PIN as f32);
            assert_eq!(cens.value(CfaPlane::G2, i), TEST_PIN as f32);
            assert!(cens.is_censored(CfaPlane::G1, i));
            assert!(!cens.has_censored_contributor(CfaPlane::G1, i));
            // The unsaturated planes must be untouched, and must still be the
            // plain mean rather than any bound.
            assert_eq!(cens.value(CfaPlane::R, i), 200.0);
            assert_eq!(cens.value(CfaPlane::B, i), 300.0);
            assert!(!cens.is_censored(CfaPlane::R, i));
            assert!(!cens.is_censored(CfaPlane::B, i));
        }
        // The bound is strictly brighter than what the plain mean emitted, by
        // the amount the pinned sample was dragged down: 4095 - 2031.67.
        assert!(
            (cens.value(CfaPlane::G1, 0) - plain.value(CfaPlane::G1, 0) - 2063.333).abs() < 0.01
        );
    }

    #[test]
    fn a_censored_contributor_is_flagged_but_never_silently_changes_the_mean() {
        // The other half of the winner-keyed rule: frame 2 is pinned but frame
        // 1 wins, so the winner's own sample is a real measurement and nothing
        // may be substituted for it.
        let g = geom(4, 4);
        let (stats, fields) = censoring_fixture(g);
        let gate = Gate::new(1.0);

        let mut plain = Estimator::new(&stats, gate);
        let mut cens = Estimator::new(&stats, gate);
        for k in 0..4u16 {
            let frame = censoring_frame(k, g, &[2]);
            plain.fold(k, &frame, &fields[k as usize]).unwrap();
            cens.fold_censored(k, &frame, &fields[k as usize], TEST_PIN)
                .unwrap();
        }
        assert!(cens.n_eff().iter().all(|n| *n == 3));
        // Hand arithmetic: (1000 + 1000 + 4095)/3, the same number, because the
        // pinned contributor is still summed.
        let mean = 6095.0f32 / 3.0;
        for i in 0..g.pixels() {
            assert!((cens.value(CfaPlane::G1, i) - mean).abs() < 1e-3);
            assert_eq!(cens.value(CfaPlane::G1, i), plain.value(CfaPlane::G1, i));
            assert!(!cens.is_censored(CfaPlane::G1, i));
            assert!(cens.has_censored_contributor(CfaPlane::G1, i));
            assert!(!cens.has_censored_contributor(CfaPlane::R, i));
        }
    }

    #[test]
    fn censoring_is_a_bit_exact_no_op_when_nothing_reaches_the_container() {
        // The in-test analogue of M54's `109/112/119MSDCF` control: on data that
        // never pins, the censored fold must be indistinguishable from the plain
        // one at every pixel of every plane.
        let g = geom(6, 5);
        let (stats, fields) = censoring_fixture(g);
        let gate = Gate::new(1.0);

        let mut plain = Estimator::new(&stats, gate);
        let mut cens = Estimator::new(&stats, gate);
        for k in 0..4u16 {
            let frame = censoring_frame(k, g, &[]);
            plain.fold(k, &frame, &fields[k as usize]).unwrap();
            cens.fold_censored(k, &frame, &fields[k as usize], TEST_PIN)
                .unwrap();
        }
        assert!(cens.n_eff().iter().all(|n| *n == 3), "fixture must average");
        assert_eq!(cens.censor_level(), Some(TEST_PIN));
        for p in [CfaPlane::R, CfaPlane::G1, CfaPlane::B, CfaPlane::G2] {
            for i in 0..g.pixels() {
                assert_eq!(cens.value(p, i), plain.value(p, i));
                assert!(!cens.is_censored(p, i));
                assert!(!cens.has_censored_contributor(p, i));
            }
        }
    }

    #[test]
    fn censored_estimators_reduce_by_union_of_their_flags() {
        let g = geom(4, 4);
        let (stats, fields) = censoring_fixture(g);
        let gate = Gate::new(1.0);
        let fold_set = |ks: &[u16]| {
            let mut e = Estimator::new(&stats, gate);
            for k in ks {
                let frame = censoring_frame(*k, g, &[1, 2]);
                e.fold_censored(*k, &frame, &fields[*k as usize], TEST_PIN)
                    .unwrap();
            }
            e
        };
        let whole = fold_set(&[0, 1, 2, 3]);
        // Split so that the winner's pin lands in one half and the contributor's
        // in the other -- neither half alone carries both flags.
        let mut left = fold_set(&[0, 1]);
        let right = fold_set(&[2, 3]);
        assert!(left.is_censored(CfaPlane::G1, 0));
        assert!(!left.has_censored_contributor(CfaPlane::G1, 0));
        assert!(!right.is_censored(CfaPlane::G1, 0));
        assert!(right.has_censored_contributor(CfaPlane::G1, 0));
        left.absorb(&right).unwrap();
        assert_eq!(left.frames_folded(), 4);
        for i in 0..g.pixels() {
            assert_eq!(left.n_eff()[i], whole.n_eff()[i]);
            assert_eq!(left.value(CfaPlane::G1, i), whole.value(CfaPlane::G1, i));
            assert_eq!(
                left.is_censored(CfaPlane::G1, i),
                whole.is_censored(CfaPlane::G1, i)
            );
            assert_eq!(
                left.has_censored_contributor(CfaPlane::G1, i),
                whole.has_censored_contributor(CfaPlane::G1, i)
            );
        }
    }

    // ---- the disagreement instrument (M60) ----

    /// A shot-noise-dominated model, so `sigma_pred` genuinely varies with
    /// signal.
    ///
    /// [`unit_sigma_model`] is the right tool for pinning the variance
    /// arithmetic, because it makes `sigma_pred` exactly 1.0 and `chi2` is then
    /// the sample variance itself. But a test that divides by 1.0 has no power
    /// to notice that the normalisation was dropped, hardcoded, or applied to
    /// the wrong quantity — subject and object would be the same value (AGENTS
    /// rule 35). These constants are the A7C II's own order of magnitude but are
    /// **not** read from `profile.rs`: a plant that shares its constants with
    /// the code under test cannot fail when that constant is wrong, which is
    /// fact 738's withdrawal.
    fn shot_noise_model() -> NoiseModel {
        let p = PlaneNoise {
            gain_dn_per_e: 0.3273,
            read_noise_e: 1.24,
            levels: Levels {
                black: 0.0,
                white: 16383.0,
            },
        };
        NoiseModel::new([p; 4], 100.0, Provenance::Measured)
    }

    /// Two pixels, `lumas[frame][pixel]` in both green slots. `focus_step`
    /// separates the frames' focus responses; at 0.0 they tie and every gate
    /// admits everything, which is what the exact-arithmetic tests want.
    ///
    /// `expect_n` is the rule-36 guard: state up front how many frames this
    /// fixture is supposed to admit, and fail loudly if it admitted a different
    /// number. Without it, a fixture that quietly admits only the winner makes
    /// every `disagreement` below `None` and a test of `None == None` ships
    /// permanently green.
    fn disagreement_fixture(
        lumas: &[[u16; 2]],
        gate: Gate,
        focus_step: f32,
        expect_n: u16,
    ) -> Estimator {
        let g = geom(2, 1);
        let field_for = |k: usize| vec![k as f32 * focus_step; g.pixels()];
        let mut stats = FocusStats::new(g);
        for k in 0..lumas.len() {
            stats.fold(k as u16, &field_for(k)).unwrap();
        }
        let mut est = Estimator::new(&stats, gate);
        est.track_disagreement();
        for (k, row) in lumas.iter().enumerate() {
            let row = *row;
            let frame = QuadGrid::new(g.width, g.height, move |x, _| {
                let l = row[x];
                // QuadGrid is raster order: row 0 is [R, G1], row 1 is [G2, B].
                [7, l, l, 9]
            });
            est.fold(k as u16, &frame, &field_for(k)).unwrap();
        }
        assert!(
            est.n_eff().iter().all(|n| *n == expect_n),
            "fixture admitted {:?}, not {expect_n} everywhere",
            est.n_eff()
        );
        est
    }

    #[test]
    fn disagreement_recovers_the_sample_variance_of_the_admitted_frames() {
        // Pixel 0: {100, 110} -> s2 = 10^2/2 = 50. Pixel 1: {95, 115} -> 200.
        let est = disagreement_fixture(&[[100, 95], [110, 115]], Gate::new(1.0), 0.0, 2);
        let m = unit_sigma_model();
        let a = est.disagreement(&m, 0, 0.0).unwrap();
        let b = est.disagreement(&m, 1, 0.0).unwrap();
        // `unit_sigma_model` is unit only up to its shot term, which at luma
        // ~105 is 0.52% of the variance. That is deliberately left in rather
        // than tuned away, and it is asserted *directionally*: shot noise can
        // only raise sigma, so it can only lower chi2. A test that merely
        // bracketed the magnitude would pass if the sign were wrong.
        assert!(a < 50.0 && (50.0 - a) / 50.0 < 6e-3, "pixel 0 read {a}");
        assert!(b < 200.0 && (200.0 - b) / 200.0 < 6e-3, "pixel 1 read {b}");
        // Both pixels share a mean luma of 105, so sigma_pred is identical and
        // cancels: the ratio is exact whatever the model says.
        assert!((b / a - 4.0).abs() < 1e-12, "ratio was {}", b / a);
    }

    #[test]
    fn a_noiseless_pair_reads_its_squared_separation_over_twice_the_variance() {
        // The relation M60's break-even is derived from: two admitted frames
        // separated by `d` with no noise read `chi2 = d^2 / (2 sigma^2)`. With
        // sigma = 1 and d = 4 that is 8, less the same sub-1% shot term.
        let est = disagreement_fixture(&[[100, 100], [104, 100]], Gate::new(1.0), 0.0, 2);
        let m = unit_sigma_model();
        let a = est.disagreement(&m, 0, 0.0).unwrap();
        assert!(a < 8.0 && (8.0 - a) / 8.0 < 6e-3, "read {a}");
        // Identical frames disagree by exactly nothing — not by the small
        // negative number the two-pass form would otherwise produce.
        assert_eq!(est.disagreement(&m, 1, 0.0).unwrap(), 0.0);
    }

    #[test]
    fn disagreement_is_quadratic_in_the_spread_at_a_fixed_signal_level() {
        // Both pixels have mean luma 105, so `sigma_pred` is identical at both
        // and cancels out of the ratio entirely. Twice the spread must be four
        // times the statistic, whatever the noise model says.
        let est = disagreement_fixture(&[[100, 95], [110, 115]], Gate::new(1.0), 0.0, 2);
        let m = shot_noise_model();
        let a = est.disagreement(&m, 0, 0.0).unwrap();
        let b = est.disagreement(&m, 1, 0.0).unwrap();
        assert!((b / a - 4.0).abs() < 1e-12, "ratio was {}", b / a);
    }

    #[test]
    fn the_same_spread_reads_smaller_where_the_signal_is_brighter() {
        // The arm with actual power over the normalisation: identical sample
        // variance (s2 = 50) at two signal levels a decade apart. If
        // `sigma_pred` were dropped or hardcoded these would be equal.
        let est = disagreement_fixture(&[[100, 1000], [110, 1010]], Gate::new(1.0), 0.0, 2);
        let m = shot_noise_model();
        let dim = est.disagreement(&m, 0, 0.0).unwrap();
        let bright = est.disagreement(&m, 1, 0.0).unwrap();
        // Shot-limited, so sigma^2 grows with signal and chi2 falls by roughly
        // the signal ratio 1005/105 = 9.57. Bracketed loosely because the read
        // term is not exactly zero; the point is the direction and the order.
        assert!(
            dim / bright > 8.0 && dim / bright < 11.0,
            "dim {dim} bright {bright} ratio {}",
            dim / bright
        );
    }

    #[test]
    fn disagreement_is_none_wherever_no_second_frame_was_admitted() {
        // Frames a full unit apart in focus, gate closed: only the winner is
        // admitted anywhere, so nothing has anything to disagree with — and
        // `disagreement_exposure` must say so, because an aggregate over an
        // empty surface is fact 688's defect exactly.
        let est = disagreement_fixture(&[[100, 95], [110, 115]], Gate::new(0.0), 1.0, 1);
        let m = unit_sigma_model();
        assert!(est.disagreement(&m, 0, 0.0).is_none());
        assert!(est.disagreement(&m, 1, 0.0).is_none());
        assert_eq!(est.disagreement_exposure(), 0.0);
    }

    #[test]
    fn tracking_disagreement_cannot_change_the_merged_image() {
        // The instrument is a diagnostic. If enabling it moved a single output
        // sample it would not be measuring the merge, it would be a merge.
        let g = geom(4, 4);
        let focus = |k: u16, i: usize| (k as f32) * 0.004 + (i as f32) * 0.01;
        let plain = run(g, 5, Gate::new(2.0), focus);
        let mut stats = FocusStats::new(g);
        for k in 0..5u16 {
            let f: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
            stats.fold(k, &f).unwrap();
        }
        let mut tracked = Estimator::new(&stats, Gate::new(2.0));
        tracked.track_disagreement();
        for k in 0..5u16 {
            let f: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
            tracked.fold(k, &flat_frame(k, g), &f).unwrap();
        }
        let mut averaged = 0;
        for i in 0..g.pixels() {
            for p in [CfaPlane::R, CfaPlane::G1, CfaPlane::B, CfaPlane::G2] {
                assert_eq!(plain.value(p, i), tracked.value(p, i));
            }
            assert_eq!(plain.n_eff()[i], tracked.n_eff()[i]);
            if tracked.n_eff()[i] >= 2 {
                averaged += 1;
            }
        }
        // Rule 36: worthless unless something was actually averaged.
        assert!(averaged > 0, "no pixel admitted a second frame");
        assert!(tracked.allocated_bytes() > plain.allocated_bytes());
    }

    #[test]
    fn disagreement_absorbs_additively_and_matches_a_sequential_fold() {
        // `sum` and `sumsq` are a sufficient statistic, which is the whole
        // argument for the instrument being free: no third pass, no per-frame
        // state, and workers reducible in any order.
        let g = geom(4, 4);
        let focus = |k: u16, i: usize| (k as f32) * 0.05 + (i as f32) * 0.003;
        let mut stats = FocusStats::new(g);
        for k in 0..6u16 {
            let f: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
            stats.fold(k, &f).unwrap();
        }
        let build = |ks: &[u16]| {
            let mut e = Estimator::new(&stats, Gate::new(3.0));
            e.track_disagreement();
            for &k in ks {
                let f: Vec<f32> = (0..g.pixels()).map(|i| focus(k, i)).collect();
                e.fold(k, &flat_frame(k, g), &f).unwrap();
            }
            e
        };
        let whole = build(&[0, 1, 2, 3, 4, 5]);
        let mut left = build(&[4, 1, 5]);
        left.absorb(&build(&[3, 0, 2])).unwrap();
        let m = unit_sigma_model();
        let mut compared = 0;
        for i in 0..g.pixels() {
            match (
                whole.disagreement(&m, i, 0.0),
                left.disagreement(&m, i, 0.0),
            ) {
                (Some(a), Some(b)) => {
                    assert!((a - b).abs() < 1e-9, "pixel {i}: {a} vs {b}");
                    compared += 1;
                }
                (None, None) => {}
                other => panic!("pixel {i} disagrees about being measurable: {other:?}"),
            }
        }
        assert!(compared > 0, "nothing was measurable; this proved nothing");
        assert_eq!(whole.disagreement_exposure(), left.disagreement_exposure());
    }

    #[test]
    fn the_photometric_probe_moves_the_statistic_and_leaves_the_image_alone() {
        let g = geom(2, 1);
        let field = vec![1.0f32; g.pixels()];
        let mut stats = FocusStats::new(g);
        for k in 0..2u16 {
            stats.fold(k, &field).unwrap();
        }
        let lumas = [[100u16, 95], [110, 115]];
        let build = |corr: [(f32, f32); 2]| {
            let mut e = Estimator::new(&stats, Gate::new(1.0));
            e.track_disagreement();
            for (k, row) in lumas.iter().enumerate() {
                let row = *row;
                let frame = QuadGrid::new(g.width, g.height, move |x, _| {
                    let l = row[x];
                    [7, l, l, 9]
                });
                e.fold_censored_probing_photometry(
                    k as u16,
                    &frame,
                    &field,
                    u16::MAX,
                    corr[k].0,
                    corr[k].1,
                )
                .unwrap();
            }
            e
        };
        let flat = build([(1.0, 0.0); 2]);
        // Scaling frame 1 by 100/110 makes the two frames coincide at pixel 0,
        // which must drive that pixel's chi2 to zero.
        let corrected = build([(1.0, 0.0), (100.0 / 110.0, 0.0)]);
        // The offset arm reaches the same place by the other route. It is
        // tested because M24 §5 leaves the *shape* of the correction open, so a
        // scale-only probe would beg the question it was built to ask, and an
        // untested parameter is a parameter that silently does nothing.
        let offset_corrected = build([(1.0, 0.0), (1.0, -10.0)]);
        // Gain and offset must be distinguishable, or the two arms are one arm
        // wearing two hats; pixel 1 is where they separate, asserted below.
        let m = unit_sigma_model();
        // 50 less the same sub-1% shot term as the sibling tests.
        let base = flat.disagreement(&m, 0, 0.0).unwrap();
        assert!(base < 50.0 && (50.0 - base) / 50.0 < 6e-3, "read {base}");
        assert!(corrected.disagreement(&m, 0, 0.0).unwrap() < 1e-6);
        assert!(offset_corrected.disagreement(&m, 0, 0.0).unwrap() < 1e-6);
        // Pixel 1 is where the two arms must part company, and the direction is
        // arithmetic, not taste. Frame 0 reads 95 and frame 1 reads 115, so the
        // gain that zeroed pixel 0 leaves `115*(100/110) - 95 = 9.545` while the
        // offset that zeroed pixel 0 leaves `115 - 10 - 95 = 10.0`. chi2 goes as
        // the square of that, so the gain arm must read `(9.545/10)^2 = 0.9112`
        // of the offset arm, less a sub-percent correction because the two arms
        // land on slightly different means and so on slightly different sigmas.
        // If the offset parameter were silently ignored the two would be equal.
        let gain_at_1 = corrected.disagreement(&m, 1, 0.0).unwrap();
        let offset_at_1 = offset_corrected.disagreement(&m, 1, 0.0).unwrap();
        let ratio = gain_at_1 / offset_at_1;
        assert!(
            gain_at_1 > 1.0 && offset_at_1 > 1.0 && (ratio - 0.9112).abs() < 0.01,
            "gain {gain_at_1}, offset {offset_at_1}, ratio {ratio} (expected 0.9112)"
        );
        // The image is untouched: the probe is a measurement knob, not a merge.
        for i in 0..g.pixels() {
            for p in [CfaPlane::R, CfaPlane::G1, CfaPlane::B, CfaPlane::G2] {
                assert_eq!(flat.value(p, i), corrected.value(p, i));
                assert_eq!(flat.value(p, i), offset_corrected.value(p, i));
            }
        }
    }

    #[test]
    #[should_panic(expected = "track_disagreement was not called")]
    fn reading_disagreement_off_an_untracked_estimator_is_refused() {
        let g = geom(2, 2);
        let est = run(g, 3, Gate::new(2.0), |k, _| k as f32 * 0.01);
        est.disagreement(&unit_sigma_model(), 0, 0.0);
    }

    #[test]
    #[should_panic(expected = "cannot mix fold and fold_censored")]
    fn mixing_the_two_folds_in_one_estimator_is_refused() {
        let g = geom(4, 4);
        let (stats, fields) = censoring_fixture(g);
        let mut est = Estimator::new(&stats, Gate::new(1.0));
        est.fold_censored(0, &censoring_frame(0, g, &[1]), &fields[0], TEST_PIN)
            .unwrap();
        est.fold(1, &censoring_frame(1, g, &[1]), &fields[1])
            .unwrap();
    }

    #[test]
    fn the_bracket_boundary_flag_fires_only_at_the_ends_of_the_stack() {
        let g = geom(3, 1);
        // Pixel 0 peaks at frame 0, pixel 1 mid-stack, pixel 2 at the last.
        let est = run(g, 5, Gate::new(0.0), |k, i| {
            let want = [0u16, 2, 4][i];
            if k == want { 1.0 } else { 0.0 }
        });
        assert!(est.at_bracket_boundary(0));
        assert!(!est.at_bracket_boundary(1));
        assert!(est.at_bracket_boundary(2));
    }

    /// The regulariser is what makes the winner field usable, and this is the
    /// mechanism fact 23 measured: a lone noise spike in one frame's focus field
    /// steals the pixel under a raw argmax and does not under a regularised one.
    ///
    /// It also pins the **limit**, because the regulariser is dilution and not
    /// magic. A `W x W` box divides a spike's excess by `W^2`, so it beats a
    /// deficit `d` in the surrounding response only while
    /// `excess < d * W^2`. At `d = 0.1` and `W = 17` the break-even spike is
    /// `0.9 + 0.1 * 289 = 29.8`, so 20 loses and 50 wins. Both are asserted:
    /// a test that only showed the spike being killed would not distinguish
    /// this regulariser from an arbitrarily strong one.
    #[test]
    fn the_regulariser_dilutes_a_focus_spike_by_its_area_and_no_more() {
        let g = geom(64, 64);
        let c = 32 * 64 + 32;
        let truth: Vec<f32> = vec![1.0; g.pixels()];
        let area = (REGULARISER_WIDTH * REGULARISER_WIDTH) as f32;
        let break_even = 0.9 + 0.1 * area;

        let winner_after_regularising = |spike: f32| {
            let mut spiked = vec![0.9f32; g.pixels()];
            spiked[c] = spike;

            // Raw argmax: any spike above 1.0 steals the pixel outright.
            let mut raw = FocusStats::new(g);
            raw.fold(0, &truth).unwrap();
            raw.fold(1, &spiked).unwrap();
            assert_eq!(raw.best_index()[c], 1, "raw argmax should elect the spike");

            let mut scratch = vec![0.0; g.pixels()];
            let (mut a, mut b) = (vec![0.0; g.pixels()], vec![0.0; g.pixels()]);
            regularise(&truth, g, &mut scratch, &mut a);
            regularise(&spiked, g, &mut scratch, &mut b);
            let mut reg = FocusStats::new(g);
            reg.fold(0, &a).unwrap();
            reg.fold(1, &b).unwrap();
            reg.best_index()[c]
        };

        assert!(break_even > 20.0 && break_even < 50.0, "{break_even}");
        assert_eq!(
            winner_after_regularising(20.0),
            0,
            "a 20x spike should not survive a {REGULARISER_WIDTH}x{REGULARISER_WIDTH} box"
        );
        assert_eq!(
            winner_after_regularising(50.0),
            1,
            "a 50x spike is above the {break_even:.1} break-even and must still win; \
             the regulariser is dilution, not a robust estimator"
        );
    }

    /// The regulariser must not be so strong that it erases a real depth edge —
    /// the other half of fact 82, which found no window/regulariser substitution
    /// at a depth discontinuity.
    #[test]
    fn the_regulariser_preserves_a_real_depth_edge() {
        let g = geom(64, 64);
        let left: Vec<f32> = (0..g.pixels())
            .map(|i| if i % 64 < 32 { 2.0 } else { 0.0 })
            .collect();
        let right: Vec<f32> = (0..g.pixels())
            .map(|i| if i % 64 < 32 { 0.0 } else { 2.0 })
            .collect();
        let mut scratch = vec![0.0; g.pixels()];
        let (mut a, mut b) = (vec![0.0; g.pixels()], vec![0.0; g.pixels()]);
        regularise(&left, g, &mut scratch, &mut a);
        regularise(&right, g, &mut scratch, &mut b);
        let mut s = FocusStats::new(g);
        s.fold(0, &a).unwrap();
        s.fold(1, &b).unwrap();
        // Well clear of the boundary on both sides, the correct frame wins.
        assert_eq!(s.best_index()[32 * 64 + 4], 0);
        assert_eq!(s.best_index()[32 * 64 + 60], 1);
    }

    #[test]
    fn memory_is_bounded_and_independent_of_the_frame_count() {
        let g = geom(100, 100);
        let a = run(g, 3, Gate::new(1.0), |_, _| 1.0);
        let b = run(g, 90, Gate::new(1.0), |_, _| 1.0);
        assert_eq!(a.allocated_bytes(), b.allocated_bytes());
    }

    // ---- the sqrt(N) invariant on the DEFAULT path (M64) -------------------

    /// Frames, plane and scoring window for the static-burst fixture.
    ///
    /// `N = 12` rather than M62's 30 because this runs in `cargo test` on every
    /// commit and the plant is decoded twelve times through two full passes; the
    /// invariant does not depend on `N`, only the tolerances do, and they are
    /// derived from this `N` below.
    const BURST_N: u16 = 12;
    const BURST_W: usize = 128;
    const BURST_H: usize = 128;
    /// Every scored pixel must have its whole support inside the plane.
    /// `SUPPORT_RADIUS` (14 = Sobel 1 + window 13) plus `REGULARISER_RADIUS`
    /// (8) is 22; 32 leaves ten quads of margin.
    const BURST_INSET: usize = 32;
    /// Fixed so the test is deterministic. Not swept: a threshold that only
    /// holds for one seed would be a threshold chosen after seeing the data, and
    /// the margins below (R about 3.4 against a 1.70 floor) are wide enough that
    /// seed choice is not doing the work.
    const BURST_SEED: u64 = 0x4D36_3400_0000_0001;

    /// The latent scene, in DN of green luma. Identical in every frame — this is
    /// a *static burst*, so the only thing that differs between frames is noise.
    ///
    /// It has real gradient structure because the focus response is
    /// `box_mean(|grad L|) / sigma(L)` and a structureless plant would make the
    /// numerator pure noise, which is a different experiment. The level is kept
    /// near 200 DN so that `unit_sigma_model`'s shot term stays negligible
    /// against its read term (1% of variance) and the model the gate uses is the
    /// one the noise was actually drawn from.
    fn burst_latent(px: usize, py: usize) -> f32 {
        let (x, y) = (px as f32, py as f32);
        200.0 + 60.0 * ((x / 7.0).sin() * (y / 5.0).cos() + 0.5 * ((x + y) / 11.0).sin())
    }

    /// One frame of the burst: the latent plus independent read noise on each
    /// green, quantised to `u16` as a real sensor would.
    ///
    /// Per-plane sigma is `sqrt(2)` DN, so the green luma `0.5*(G1+G2)` carries
    /// sigma exactly 1 DN — which is what `unit_sigma_model` declares. R and B
    /// are constant and unused: the score is on green.
    fn burst_frame(rng: &mut Rng) -> QuadGrid {
        let mut noise: Vec<[f32; 2]> = Vec::with_capacity(BURST_W * BURST_H);
        for _ in 0..BURST_W * BURST_H {
            noise.push([
                std::f32::consts::SQRT_2 * rng.normal(),
                std::f32::consts::SQRT_2 * rng.normal(),
            ]);
        }
        QuadGrid::new(BURST_W, BURST_H, |px, py| {
            let l = burst_latent(px, py);
            let n = noise[py * BURST_W + px];
            let q = |v: f32| v.round().clamp(0.0, 65535.0) as u16;
            [1000, q(l + n[0]), q(l + n[1]), 1000]
        })
    }

    /// Pooled RMS of `a - b` over the inset interior.
    fn burst_rms(a: &[f32], b: &[f32]) -> f64 {
        let mut acc = 0.0f64;
        let mut n = 0usize;
        for py in BURST_INSET..BURST_H - BURST_INSET {
            for px in BURST_INSET..BURST_W - BURST_INSET {
                let i = py * BURST_W + px;
                let d = (a[i] - b[i]) as f64;
                acc += d * d;
                n += 1;
            }
        }
        (acc / n as f64).sqrt()
    }

    /// Runs the **whole default path** — `green_luma`, `FocusField::compute`,
    /// `regularise`, pass one, pass two at `gate` — over one static burst.
    ///
    /// Returns `(noise reduction R, mean n_eff, single-frame RMS)`. `R` is the
    /// pooled single-frame RMS against the latent divided by the merged RMS
    /// against the same latent, which is M62's statistic.
    fn burst_score(gate: Gate, seed: u64) -> (f64, f64, f64) {
        let g = PlaneGeometry {
            width: BURST_W,
            height: BURST_H,
        };
        let noise = unit_sigma_model();
        let px = g.pixels();

        let mut rng = Rng::new(seed);
        let frames: Vec<QuadGrid> = (0..BURST_N).map(|_| burst_frame(&mut rng)).collect();

        // The truth, in the same units the merge outputs: green luma of the
        // noiseless latent. `green_luma` subtracts black, which is 0 here.
        let truth: Vec<f32> = (0..px)
            .map(|i| burst_latent(i % BURST_W, i / BURST_W))
            .collect();

        let mut luma = vec![0.0f32; px];
        let mut field = FocusField::new(g);
        let mut scratch = vec![0.0f32; px];
        let mut reg = vec![0.0f32; px];

        // Every frame's regularised response, computed exactly as `merge_cmd`'s
        // `field_for` does, and kept so both passes see the same arithmetic.
        let mut fields: Vec<Vec<f32>> = Vec::with_capacity(BURST_N as usize);
        // The per-frame single-frame error, pooled across frames: the reference
        // an ideal estimator improves on by sqrt(N).
        let mut single_sq = 0.0f64;
        for frame in &frames {
            crate::plane::green_luma(frame, 0.0, &mut luma);
            single_sq += burst_rms(&luma, &truth).powi(2);
            field.compute(&luma, &noise);
            regularise(field.values(), g, &mut scratch, &mut reg);
            fields.push(reg.clone());
        }
        let single = (single_sq / BURST_N as f64).sqrt();

        let mut stats = FocusStats::new(g);
        for (k, f) in fields.iter().enumerate() {
            stats.fold(k as u16, f).unwrap();
        }
        let mut est = Estimator::new(&stats, gate);
        for (k, f) in fields.iter().enumerate() {
            est.fold(k as u16, &frames[k], f).unwrap();
        }
        assert!(est.every_pixel_is_decided());

        let merged: Vec<f32> = (0..px).map(|i| est.green_mean(i)).collect();
        let r = single / burst_rms(&merged, &truth);

        // n_eff over the same scored window, not the whole plane: a pixel whose
        // support runs off the edge is not one this test is reading.
        let (mut acc, mut n) = (0.0f64, 0usize);
        for py in BURST_INSET..BURST_H - BURST_INSET {
            for pxi in BURST_INSET..BURST_W - BURST_INSET {
                acc += est.n_eff()[py * BURST_W + pxi] as f64;
                n += 1;
            }
        }
        (r, acc / n as f64, single)
    }

    /// **The acceptance invariant for the shipped default path (M64).**
    ///
    /// On a static burst — focus untouched, subject still — every frame is an
    /// equally good measurement of the same latent, so the correct answer is
    /// known *exactly*: average them, and the noise falls by `sqrt(N)`. This is
    /// the one test in this project whose right answer is arithmetic rather than
    /// a preference.
    ///
    /// A selector cannot get there. It copies one frame per pixel, so it
    /// inherits that frame's noise, and because the frame is chosen *using* that
    /// same noise the choice is correlated with it and the result is worse than
    /// one frame. M62 measured the shipped argmax at **0.7690x** against
    /// `sqrt(30) = 5.4772` — a 1.30x noise increase — on the identical plant
    /// where the estimating merge scored 5.4778x.
    ///
    /// This test runs the **default path's own code at [`DEFAULT_GATE`]**, not a
    /// hand-built fold: `green_luma` -> [`crate::focus::FocusField::compute`] ->
    /// [`regularise`] -> pass one -> pass two, which is the chain
    /// `merge_cmd::Ctx::field_for` runs. If the default is ever moved back
    /// towards selection this goes red.
    ///
    /// # Why these thresholds and not tighter ones
    ///
    /// The plant is 4096 scored pixels of a 128x128 plane, so the RMS ratio
    /// carries real sampling error, and `R` is bounded above by
    /// `sqrt(mean n_eff)` — a merge cannot beat the arithmetic of what it
    /// admitted. The assertions are therefore: the *ideal* mean of all `N`
    /// recovers `sqrt(N)` (this is the harness calibrating itself, and it is
    /// tight at 2%); the default admits enough frames to be averaging at all;
    /// `R` is far above any selector; and `R` is within 20% of the Jensen bound
    /// its own acceptance set sets. Deliberately loose against `sqrt(N)`,
    /// because `DEFAULT_GATE` is not chosen to maximise this number — see its
    /// doc comment — and a tight band here would silently become a demand that
    /// the gate be raised until this test is happy, which is tuning to a plant
    /// where every frame is in focus.
    ///
    /// The negative control is in the same test, per rule 39: gate 0 is the same
    /// code path with the acceptance set collapsed to the winner alone, and it
    /// must land at or below 1.0. Without it, "R is large" would be consistent
    /// with the harness measuring nothing.
    #[test]
    fn the_default_path_reaches_the_arithmetic_limit_on_a_static_burst() {
        let n = BURST_N as f64;
        let ideal = n.sqrt();

        // (a) The harness, calibrated against itself. A plain mean of every
        //     frame must recover sqrt(N) on this plant, or nothing measured
        //     below means anything.
        let (r_ideal, _, _) = burst_score(Gate::new(1e6), BURST_SEED);
        assert!(
            (r_ideal - ideal).abs() / ideal < 0.02,
            "harness: a gate wide enough to admit every frame scored {r_ideal:.4}, \
             but the arithmetic answer is sqrt({n}) = {ideal:.4}. The plant or the \
             reference is wrong, and no verdict below is readable."
        );

        // (b) The default path.
        let (r, n_eff, _) = burst_score(Gate::new(DEFAULT_GATE), BURST_SEED);
        assert!(
            n_eff >= 3.0,
            "the default gate averaged only {n_eff:.3} frames per pixel on a burst \
             where every frame is an equally valid measurement. Rule 36: a fixture \
             that does not exercise averaging cannot test an estimator."
        );
        assert!(
            r >= 1.70,
            "the DEFAULT path scored {r:.4}x on a static burst where sqrt({n}) = \
             {ideal:.4} is provably correct and a selector scores about 1.0. \
             The shipped default has regressed towards selection."
        );
        let bound = n_eff.sqrt();
        assert!(
            r >= 0.80 * bound,
            "the default path scored {r:.4}x while admitting {n_eff:.3} frames per \
             pixel, whose arithmetic bound is {bound:.4}x. It is wasting samples it \
             already paid to decode."
        );

        // (c) The negative control, in the same test (rule 39). Gate 0 is the
        //     same code with the acceptance set collapsed to the winner alone.
        let (r0, n0, _) = burst_score(Gate::new(0.0), BURST_SEED);
        assert!(
            (n0 - 1.0).abs() < 1e-9,
            "gate 0 admitted {n0:.6} frames per pixel; it must admit exactly the winner"
        );
        assert!(
            r0 <= 1.05,
            "the gate-0 SELECTOR scored {r0:.4}x. A selector cannot beat one frame, \
             so this harness is measuring something other than what it claims."
        );
        assert!(
            r > 2.0 * r0,
            "the default ({r:.4}x) is not separated from selection ({r0:.4}x); \
             whatever this test is measuring, it is not the estimator."
        );

        // Printed so a CI log carries the measurement and not just a green tick.
        // `cargo test -p strehl-core -- --nocapture the_default_path_reaches`.
        eprintln!(
            "sqrt(N) invariant: N = {BURST_N}, ideal = {ideal:.4}\n  \
             all-frames mean : {r_ideal:.4}x  (harness calibration, must be ideal +/- 2%)\n  \
             DEFAULT_GATE {DEFAULT_GATE:<4}: {r:.4}x  at mean n_eff {n_eff:.3}, \
             bound sqrt(n_eff) = {bound:.4}\n  \
             gate 0 selector : {r0:.4}x  at mean n_eff {n0:.3}  (negative control)"
        );
    }

    /// **Where this fixture stops being able to fail**, pinned so the previous
    /// test's power is a measurement rather than a hope.
    ///
    /// A green tick on a √N test proves nothing unless something makes it red.
    /// The negative control at gate 0 is one such input, but gate 0 is a
    /// degenerate special case (the acceptance set is literally the winner), so
    /// on its own it leaves open the possibility that *any* non-zero gate
    /// passes — which would make the invariant unable to see a default quietly
    /// lowered from 4.0 to 0.5.
    ///
    /// This walks the ladder and requires three structural things, none of them
    /// a tuned constant: the acceptance set widens monotonically with the gate;
    /// the score widens with it; and **at least one non-zero gate below
    /// [`DEFAULT_GATE`] scores under the 1.70 floor the invariant asserts**.
    /// That last clause is the power claim, and if a future change to the
    /// operator makes every gate pass, this test goes red and says so.
    ///
    /// # What it also documents
    ///
    /// The reason a static Gaussian burst admits essentially every frame at
    /// `t = 4`: the gate rejects a frame when the winner beats it by more than
    /// `t·√2` SDs of the response, the winner is a max over `N` and so sits
    /// about `E[max of N normals]` = 1.63 SDs up at `N = 12`, and
    /// `4·√2 = 5.66 > 1.63`, so a rejection needs a frame 4 SDs *below* the
    /// mean. That is DERIVED and the ladder below is the MEASURED check on it.
    /// It is also why `DEFAULT_GATE` cannot be chosen from this test: everything
    /// from about 2 upwards looks identical here, and the real cost of the
    /// difference is on a focus axis this plant does not have.
    #[test]
    fn the_burst_fixture_can_fail_below_the_default_gate() {
        let ladder: Vec<(f32, f64, f64)> = [0.25f32, 0.5, 1.0, 2.0, DEFAULT_GATE]
            .iter()
            .map(|t| {
                let (r, n_eff, _) = burst_score(Gate::new(*t), BURST_SEED);
                (*t, r, n_eff)
            })
            .collect();
        for w in ladder.windows(2) {
            let (t0, r0, n0) = w[0];
            let (t1, r1, n1) = w[1];
            assert!(
                n1 >= n0 - 1e-9,
                "acceptance shrank between gate {t0} ({n0:.3}) and gate {t1} ({n1:.3})"
            );
            assert!(
                r1 >= r0 - 1e-9,
                "score fell between gate {t0} ({r0:.4}x) and gate {t1} ({r1:.4}x)"
            );
        }
        let weak = ladder
            .iter()
            .filter(|(t, _, _)| *t > 0.0 && *t < DEFAULT_GATE)
            .find(|(_, r, _)| *r < 1.70);
        assert!(
            weak.is_some(),
            "no non-zero gate below DEFAULT_GATE scored under the 1.70 floor, so the \
             invariant cannot distinguish the shipped default from a near-selector. \
             Ladder: {ladder:?}"
        );
        eprintln!("burst ladder (gate, R, mean n_eff): {ladder:?}");
    }

    // ---- soft admission kernel (M111's hand-off, §15.6) -------------------

    /// A stack whose per-frame focus response is constant over the plane, so
    /// the response gap — the only thing the kernels see — is exactly what the
    /// caller asked for.
    fn soft_stats(g: PlaneGeometry, focus: &[f32]) -> (FocusStats, Vec<Vec<f32>>) {
        let fields: Vec<Vec<f32>> = focus.iter().map(|f| vec![*f; g.pixels()]).collect();
        let mut stats = FocusStats::new(g);
        for (k, f) in fields.iter().enumerate() {
            stats.fold(k as u16, f).unwrap();
        }
        (stats, fields)
    }

    /// Flat frame `k` carrying luma `1000 + 100k` in both green slots.
    fn soft_frame(g: PlaneGeometry, k: u16) -> QuadGrid {
        let v = 1000 + 100 * k;
        QuadGrid::new(g.width, g.height, move |_, _| [200, v, v, 300])
    }

    #[test]
    fn the_soft_gate_switch_names_a_kernel_and_refuses_to_guess() {
        for off in [
            None,
            Some(""),
            Some("   "),
            Some("0"),
            Some("off"),
            Some("OFF"),
            Some("false"),
        ] {
            assert_eq!(
                kernel_from_setting(off),
                Ok(None),
                "{off:?} must run the shipped hard gate"
            );
        }
        assert_eq!(
            kernel_from_setting(Some("gaussian")),
            Ok(Some(SoftKernel::Gaussian))
        );
        assert_eq!(
            kernel_from_setting(Some("Exponential")),
            Ok(Some(SoftKernel::Exponential))
        );
        // Truthy values are refused for the reason `optics::profile_from_setting`
        // refuses them: there are two kernels and "on" does not say which. A
        // typo is an error rather than an absence, because a typo that silently
        // disables the fix looks exactly like the fix not working.
        for bad in ["1", "true", "on", "yes", "gauss", "gausian", "expo"] {
            assert!(
                kernel_from_setting(Some(bad)).is_err(),
                "{bad:?} must not resolve to a kernel"
            );
        }
    }

    #[test]
    fn the_two_kernels_cross_at_exactly_two_tolerances() {
        // `-0.5 z^2 == -z` has roots z = 0 and z = 2. A comparison of the two
        // kernels anchored at two tolerances therefore measures **nothing**,
        // and this is pinned as a test so nobody prices them there and reports
        // a null that is an artefact of the sampling point.
        let soft = SoftGate::new(1.0);
        let tol = soft.tolerance();
        let at = |z: f32, k: SoftKernel| k.weight(&soft, -z * tol, 0.0);

        let (g2, e2) = (at(2.0, SoftKernel::Gaussian), at(2.0, SoftKernel::Exponential));
        assert!(
            (g2 - e2).abs() <= 1e-7,
            "the kernels must agree at the crossing: {g2} vs {e2}"
        );
        // Inside the crossing the Gaussian is the heavier of the two...
        assert!(at(1.0, SoftKernel::Gaussian) > at(1.0, SoftKernel::Exponential));
        // ...and beyond it the exponential is, which is exactly why it is the
        // riskier kernel on a stack carrying far-out-of-focus frames.
        assert!(at(3.0, SoftKernel::Exponential) > at(3.0, SoftKernel::Gaussian));
        // Both agree with the closed forms, computed here rather than taken
        // from the implementation under test.
        assert!((at(1.0, SoftKernel::Gaussian) - (-0.5f32).exp()).abs() < 1e-6);
        assert!((at(1.0, SoftKernel::Exponential) - (-1.0f32).exp()).abs() < 1e-6);
    }

    #[test]
    fn the_exponential_truncates_at_its_own_floor_not_the_gaussians() {
        // Truncating both kernels at one *distance* would silently turn a
        // comparison of shapes into a comparison of supports.
        assert!(exponential_cutoff_tolerances() > crate::softgate::cutoff_tolerances());
        let soft = SoftGate::new(1.0);
        let tol = soft.tolerance();
        let just_inside = exponential_cutoff_tolerances() - 1e-3;
        let w = SoftKernel::Exponential.weight(&soft, -just_inside * tol, 0.0);
        assert!(w >= WEIGHT_FLOOR, "just inside the cutoff must survive: {w}");
        let just_outside = exponential_cutoff_tolerances() + 1e-3;
        assert_eq!(
            SoftKernel::Exponential.weight(&soft, -just_outside * tol, 0.0),
            0.0
        );
    }

    #[test]
    fn a_none_kernel_leaves_every_soft_accessor_absent() {
        let g = geom(4, 4);
        let tol = Gate::new(1.0).tolerance();
        let (stats, fields) = soft_stats(g, &[0.0, -0.5 * tol, -3.0 * tol]);
        let mut hard = Estimator::new_soft(&stats, Gate::new(1.0), None);
        for k in 0..3u16 {
            hard.fold(k, &soft_frame(g, k), &fields[k as usize]).unwrap();
        }
        assert_eq!(hard.soft_kernel(), None);
        assert!(hard.soft_n_eff().is_none());
        assert!(hard.mean_soft_n_eff().is_none());
        assert!(hard.soft_n_eff_at(0).is_none());
        // Rule 36: the fixture must actually exercise the gate. Frames 0 and 1
        // are inside one tolerance, frame 2 is three tolerances out.
        assert!(
            hard.n_eff().iter().all(|n| *n == 2),
            "fixture must admit exactly two, got {:?}",
            hard.n_eff()
        );
        for i in 0..g.pixels() {
            assert_eq!(hard.value(CfaPlane::G1, i), 1050.0);
        }
    }

    #[test]
    fn the_soft_kernel_admits_and_down_weights_a_frame_the_hard_gate_drops() {
        let g = geom(4, 4);
        let tol = Gate::new(1.0).tolerance();
        let (stats, fields) = soft_stats(g, &[0.0, -0.5 * tol, -3.0 * tol]);

        let mut soft = Estimator::new_soft(&stats, Gate::new(1.0), Some(SoftKernel::Gaussian));
        for k in 0..3u16 {
            soft.fold(k, &soft_frame(g, k), &fields[k as usize]).unwrap();
        }
        // The Gaussian's support runs to 4.71 tolerances, so frame 2 at three
        // tolerances is admitted where the hard gate rejected it outright.
        assert!(
            soft.n_eff().iter().all(|n| *n == 3),
            "the soft kernel must admit all three, got {:?}",
            soft.n_eff()
        );

        // Closed-form weights, written here rather than read from the kernel.
        let w = [1.0f64, (-0.125f64).exp(), (-4.5f64).exp()];
        let num: f64 = w[0] * 1000.0 + w[1] * 1100.0 + w[2] * 1200.0;
        let den: f64 = w.iter().sum();
        let expect = (num / den) as f32;
        for i in 0..g.pixels() {
            let got = soft.value(CfaPlane::G1, i);
            assert!(
                (got - expect).abs() < 2e-3,
                "weighted mean at {i}: got {got}, want {expect}"
            );
            // And it must not be the boolean answer, or the weighting is inert.
            assert!((got - 1050.0).abs() > 1.0, "soft value collapsed to the hard mean");
        }

        // Kish sits strictly below the raw admitted count, because the third
        // frame contributes almost nothing.
        let kish = soft.soft_n_eff().unwrap();
        let expect_kish = (den * den / w.iter().map(|x| x * x).sum::<f64>()) as f32;
        for k in kish.iter() {
            assert!((k - expect_kish).abs() < 1e-4, "kish {k} vs {expect_kish}");
            assert!(*k < 3.0, "kish must be below the raw count of 3");
        }
    }

    #[test]
    fn kish_reduces_exactly_to_the_integer_count_when_every_weight_is_one() {
        // Four frames tying on focus: every gap is zero, every weight is
        // exactly 1.0, and the Kish count must return the integer count *to
        // the bit*. This is the reduction that makes the soft path a
        // generalisation rather than a replacement.
        let g = geom(3, 3);
        let (stats, fields) = soft_stats(g, &[0.0; 4]);
        for kernel in [SoftKernel::Gaussian, SoftKernel::Exponential] {
            let mut soft = Estimator::new_soft(&stats, Gate::new(1.0), Some(kernel));
            for k in 0..4u16 {
                soft.fold(k, &soft_frame(g, k), &fields[k as usize]).unwrap();
            }
            let kish = soft.soft_n_eff().unwrap();
            for (i, &k_i) in kish.iter().enumerate() {
                assert_eq!(soft.n_eff()[i], 4, "{kernel:?}");
                assert_eq!(k_i, 4.0, "{kernel:?} kish must be exactly 4.0");
                assert_eq!(soft.soft_n_eff_at(i), Some(4.0), "{kernel:?}");
            }
            assert_eq!(soft.mean_soft_n_eff(), Some(4.0), "{kernel:?}");
            // The weighted mean of equal weights is the plain mean, exactly.
            for i in 0..g.pixels() {
                assert_eq!(soft.value(CfaPlane::G1, i), 1150.0, "{kernel:?}");
            }
        }
    }

    #[test]
    fn the_weighted_disagreement_reduces_bit_for_bit_to_the_boolean_form() {
        // Row 3 of M111 §15.6 is the subtle one: weighting `luma_sum` without
        // weighting its divisor changes what the noise diagnostic *means* while
        // still returning plausible numbers. On all-equal weights the weighted
        // form must return the identical f64, or the reduction is wrong.
        let g = geom(2, 2);
        let (stats, fields) = soft_stats(g, &[0.0; 3]);
        let lumas = [1000u16, 1180, 1090];
        let frame = |k: u16| {
            let v = lumas[k as usize];
            QuadGrid::new(g.width, g.height, move |_, _| [200, v, v, 300])
        };

        let mut hard = Estimator::new_soft(&stats, Gate::new(1.0), None);
        let mut soft = Estimator::new_soft(&stats, Gate::new(1.0), Some(SoftKernel::Gaussian));
        hard.track_disagreement();
        soft.track_disagreement();
        for k in 0..3u16 {
            hard.fold(k, &frame(k), &fields[k as usize]).unwrap();
            soft.fold(k, &frame(k), &fields[k as usize]).unwrap();
        }
        assert!(hard.n_eff().iter().all(|n| *n == 3), "fixture must admit three");

        let m = shot_noise_model();
        for i in 0..g.pixels() {
            let a = hard.disagreement(&m, i, 0.0).unwrap();
            let b = soft.disagreement(&m, i, 0.0).unwrap();
            assert_eq!(a, b, "disagreement must reduce exactly at pixel {i}");
            // Rule 36: a reduction test between two `None`s proves nothing.
            assert!(a > 0.0, "fixture must produce a non-zero disagreement");
        }
        assert_eq!(hard.disagreement_exposure(), soft.disagreement_exposure());
        assert_eq!(hard.disagreement_exposure(), 1.0);
    }

    #[test]
    fn predicted_sigma_follows_the_effective_count_not_the_admitted_count() {
        // `value` divides by `wsum`, so the variance it carries falls as
        // 1/n_eff. Reporting 1/n here would claim a noise floor the estimator
        // does not have.
        let g = geom(2, 2);
        let tol = Gate::new(1.0).tolerance();
        let (stats, fields) = soft_stats(g, &[0.0, -0.5 * tol, -3.0 * tol]);
        let mut soft = Estimator::new_soft(&stats, Gate::new(1.0), Some(SoftKernel::Gaussian));
        for k in 0..3u16 {
            soft.fold(k, &soft_frame(g, k), &fields[k as usize]).unwrap();
        }
        let m = shot_noise_model();
        let kish = f64::from(soft.soft_n_eff().unwrap()[0]);
        assert!(kish < 3.0 && kish > 1.0, "kish {kish} must sit between 1 and 3");
        let luma = soft.green_mean(0);
        let expect = m.green_luma_sigma(luma) * selection_inflation(3) / (kish as f32).sqrt();
        let got = soft.predicted_sigma(&m, 0, 0.0);
        assert!((got - expect).abs() < 1e-4, "got {got}, want {expect}");
        // And it must differ from the integer-count answer, or the change is
        // inert and this test has no power.
        let inert = m.green_luma_sigma(luma) * selection_inflation(3) / 3.0f32.sqrt();
        assert!((got - inert).abs() > 1e-3, "predicted_sigma ignored the weights");
    }

    #[test]
    fn every_pixel_is_still_decided_when_the_gate_is_degenerate() {
        // Threshold 0 gives a zero tolerance, so the kernel returns 0.0 for any
        // positive gap and the merge collapses to the hard argmax. The winner
        // must still contribute — a merge that admits nothing anywhere is the
        // failure this pin exists to catch.
        let g = geom(3, 3);
        let tol = Gate::new(1.0).tolerance();
        let (stats, fields) = soft_stats(g, &[-2.0 * tol, 0.0, -tol]);
        for kernel in [SoftKernel::Gaussian, SoftKernel::Exponential] {
            let mut soft = Estimator::new_soft(&stats, Gate::new(0.0), Some(kernel));
            for k in 0..3u16 {
                soft.fold(k, &soft_frame(g, k), &fields[k as usize]).unwrap();
            }
            assert!(soft.every_pixel_is_decided(), "{kernel:?}");
            assert!(soft.n_eff().iter().all(|n| *n == 1), "{kernel:?}");
            // Frame 1 wins, carrying luma 1100, and it is returned undiluted.
            for i in 0..g.pixels() {
                assert_eq!(soft.value(CfaPlane::G1, i), 1100.0, "{kernel:?}");
                assert_eq!(soft.soft_n_eff_at(i), Some(1.0), "{kernel:?}");
            }
        }
    }

    #[test]
    fn the_two_kernels_produce_different_merges_on_the_same_stack() {
        // If these agreed, pricing them would be theatre.
        let g = geom(2, 2);
        let tol = Gate::new(1.0).tolerance();
        let (stats, fields) = soft_stats(g, &[0.0, -tol, -3.0 * tol]);
        let mut a = Estimator::new_soft(&stats, Gate::new(1.0), Some(SoftKernel::Gaussian));
        let mut b = Estimator::new_soft(&stats, Gate::new(1.0), Some(SoftKernel::Exponential));
        for k in 0..3u16 {
            a.fold(k, &soft_frame(g, k), &fields[k as usize]).unwrap();
            b.fold(k, &soft_frame(g, k), &fields[k as usize]).unwrap();
        }
        let (va, vb) = (a.value(CfaPlane::G1, 0), b.value(CfaPlane::G1, 0));
        assert!((va - vb).abs() > 1.0, "kernels must differ: {va} vs {vb}");
        // Direction, and it is the opposite of the naive "heavier tail admits
        // more, so it reads higher". Frame 1 sits at z = 1, *inside* the z = 2
        // crossing, where the Gaussian is the heavier of the two, and it is
        // also the brighter near frame. The Gaussian therefore pulls the mean
        // up more than the exponential's fatter tail on the distant frame 2
        // pulls it. Measured, then explained -- the first version of this
        // assertion claimed the reverse and the test caught it.
        assert!(va > vb, "gaussian {va} must exceed exponential {vb}");
    }

    #[test]
    #[should_panic(expected = "different admission kernels")]
    fn absorb_refuses_two_different_kernels() {
        let g = geom(2, 2);
        let (stats, fields) = soft_stats(g, &[0.0, 0.0]);
        let mut a = Estimator::new_soft(&stats, Gate::new(1.0), Some(SoftKernel::Gaussian));
        let mut b = Estimator::new_soft(&stats, Gate::new(1.0), Some(SoftKernel::Exponential));
        a.fold(0, &soft_frame(g, 0), &fields[0]).unwrap();
        b.fold(1, &soft_frame(g, 1), &fields[1]).unwrap();
        a.absorb(&b).unwrap();
    }

    #[test]
    fn absorb_reduces_the_weight_sums_additively() {
        let g = geom(2, 2);
        let tol = Gate::new(1.0).tolerance();
        let (stats, fields) = soft_stats(g, &[0.0, -0.5 * tol, -3.0 * tol]);
        let k = SoftKernel::Gaussian;

        let mut whole = Estimator::new_soft(&stats, Gate::new(1.0), Some(k));
        for f in 0..3u16 {
            whole.fold(f, &soft_frame(g, f), &fields[f as usize]).unwrap();
        }
        let mut left = Estimator::new_soft(&stats, Gate::new(1.0), Some(k));
        let mut right = Estimator::new_soft(&stats, Gate::new(1.0), Some(k));
        left.fold(0, &soft_frame(g, 0), &fields[0]).unwrap();
        right.fold(1, &soft_frame(g, 1), &fields[1]).unwrap();
        right.fold(2, &soft_frame(g, 2), &fields[2]).unwrap();
        left.absorb(&right).unwrap();

        for i in 0..g.pixels() {
            // The integer count still reduces exactly, because it is an integer.
            assert_eq!(left.n_eff()[i], whole.n_eff()[i]);

            // The *weighted* accumulators do not, and that is a property of
            // f32 addition, not a bug: `1.0 + (w1 + w2)` and `(1.0 + w1) + w2`
            // round differently. The boolean path never had to face this
            // because its `n` is an integer; the soft path's `wsum` is a float
            // sum whose association order follows the chunking. A soft render
            // is therefore reproducible for a *fixed* chunk length, not across
            // chunk lengths. The bound below is measured, not guessed.
            let (l, w) = (
                left.soft_n_eff_at(i).unwrap(),
                whole.soft_n_eff_at(i).unwrap(),
            );
            let rel = ((l - w) / w).abs();
            assert!(
                rel < 1e-6,
                "kish drifted by {rel:.3e} across the reduction: {l} vs {w}"
            );
            let (lv, wv) = (
                left.value(CfaPlane::G1, i),
                whole.value(CfaPlane::G1, i),
            );
            let vrel = ((lv - wv) / wv).abs();
            assert!(vrel < 1e-6, "value drifted by {vrel:.3e}: {lv} vs {wv}");
            if i == 0 {
                eprintln!("absorb drift: kish rel {rel:.3e}, value rel {vrel:.3e}");
            }
        }
    }

    // ---- gate-weighted clip mass (M109's residual magenta highlights) ----
    //
    // Rule 34 declaration: these reuse `censoring_fixture`, whose pin is
    // `TEST_PIN = 4095` and never `clip::CONTAINER_MAX_DN`. What makes the
    // fixture worth reusing here is frame 3: it is folded but sits far outside
    // a threshold-1 gate, so "the set that was folded" and "the set that
    // contributed" are different sets and the difference is observable.

    #[test]
    fn clip_mass_counts_the_contributing_set_and_not_the_folded_set() {
        let g = geom(4, 4);
        let (stats, fields) = censoring_fixture(g);
        let gate = Gate::new(1.0);
        let mass = |pinned: &[u16]| {
            let mut e = Estimator::new(&stats, gate);
            for k in 0..4u16 {
                let frame = censoring_frame(k, g, pinned);
                e.fold_censored(k, &frame, &fields[k as usize], TEST_PIN)
                    .unwrap();
            }
            (
                e.clipped_weight(CfaPlane::G1, 0).unwrap(),
                e.contributing_weight(0),
            )
        };

        // The null. Frame 3 is pinned, is folded, and is *not admitted*. An
        // accumulator sitting before the gate's `continue` -- a rate against
        // the frames sampled rather than the frames averaged, which is
        // M109's bar B15 error -- would read 1.0 here.
        let (null_mass, denom) = mass(&[3]);
        assert_eq!(denom, 3.0, "fixture must admit exactly three of four frames");
        assert_eq!(null_mass, 0.0, "a gate-excluded frame contributed clip mass");

        // The plant, on the same wiring. Without it the 0.0 above is equally
        // good evidence that the accumulator is simply never written.
        let (plant_mass, plant_denom) = mass(&[0]);
        assert_eq!(plant_denom, 3.0);
        assert_eq!(plant_mass, 1.0, "an admitted pinned frame was not counted");
    }

    #[test]
    fn clip_mass_is_per_channel_and_counts_integers_under_the_top_hat() {
        let g = geom(4, 4);
        let (stats, fields) = censoring_fixture(g);
        let mut e = Estimator::new(&stats, Gate::new(1.0));
        for k in 0..4u16 {
            // 0 and 1 pin their greens, 2 is admitted and clean, 3 is excluded.
            let frame = censoring_frame(k, g, &[0, 1]);
            e.fold_censored(k, &frame, &fields[k as usize], TEST_PIN)
                .unwrap();
        }
        for i in 0..g.pixels() {
            assert_eq!(e.contributing_weight(i), 3.0);
            for p in [CfaPlane::G1, CfaPlane::G2] {
                assert_eq!(e.clipped_weight(p, i), Some(2.0));
            }
            // R and B never approach the pin. A per-pixel accumulator would
            // smear the greens' mass across them and convict a saturated
            // green highlight of being a saturated red object; one accumulator
            // per CFA plane cannot.
            for p in [CfaPlane::R, CfaPlane::B] {
                assert_eq!(e.clipped_weight(p, i), Some(0.0));
            }
        }
    }

    #[test]
    fn clip_mass_carries_the_same_weights_the_merged_value_does() {
        let g = geom(4, 4);
        let (stats, fields) = censoring_fixture(g);
        let gate = Gate::new(1.0);
        let build = |pinned: &[u16]| {
            let mut e = Estimator::new_soft(&stats, gate, Some(SoftKernel::Gaussian));
            for k in 0..4u16 {
                let frame = censoring_frame(k, g, pinned);
                e.fold_censored(k, &frame, &fields[k as usize], TEST_PIN)
                    .unwrap();
            }
            e
        };

        // Every admitted frame is pinned, so the pinned mass and the divisor
        // are the same additions of the same values in the same order. This is
        // exact equality that appeals to no property of the kernel at all: if
        // the numerator were counting while the denominator weighted, a
        // fractional divisor could not equal an integer count.
        let all = build(&[0, 1, 2]);
        for i in 0..g.pixels() {
            let w = all.contributing_weight(i);
            assert!(w > 1.0 && w < 3.0, "soft weights must be fractional, read {w}");
            assert_eq!(all.clipped_weight(CfaPlane::G1, i), Some(w));
        }

        // Only the winner is pinned, and the winner is held at weight exactly
        // 1.0, so this is exact too -- and it reads that invariant a second
        // time from the other side.
        let winner_only = build(&[1]);
        for i in 0..g.pixels() {
            assert_eq!(winner_only.clipped_weight(CfaPlane::G1, i), Some(1.0));
            assert!(winner_only.contributing_weight(i) > 1.0);
        }
    }

    #[test]
    fn clip_mass_is_absent_rather_than_zero_when_nothing_censors() {
        let g = geom(4, 4);
        let (stats, fields) = censoring_fixture(g);
        let mut e = Estimator::new(&stats, Gate::new(1.0));
        for k in 0..4u16 {
            e.fold(k, &censoring_frame(k, g, &[0, 1]), &fields[k as usize])
                .unwrap();
        }
        // `None` and `Some(0.0)` are different claims -- "this estimator never
        // looked" against "it looked and found nothing pinned". Collapsing them
        // would let a consumer read an unwired producer as a clean highlight,
        // which is the failure mode a 0.000 always has to answer for.
        assert_eq!(e.clipped_weight(CfaPlane::G1, 0), None);
        assert_eq!(e.contributing_weight(0), 3.0);
    }

    #[test]
    fn clip_mass_reduces_additively_under_absorb() {
        let g = geom(4, 4);
        let (stats, fields) = censoring_fixture(g);
        let gate = Gate::new(1.0);
        let fold_set = |ks: &[u16]| {
            let mut e = Estimator::new(&stats, gate);
            for k in ks {
                let frame = censoring_frame(*k, g, &[0, 1]);
                e.fold_censored(*k, &frame, &fields[*k as usize], TEST_PIN)
                    .unwrap();
            }
            e
        };
        let whole = fold_set(&[0, 1, 2, 3]);
        let mut left = fold_set(&[0, 1]);
        let right = fold_set(&[2, 3]);
        // The mass sits entirely in one half, so the union is a real reduction
        // rather than one side already carrying the answer.
        assert_eq!(left.clipped_weight(CfaPlane::G1, 0), Some(2.0));
        assert_eq!(right.clipped_weight(CfaPlane::G1, 0), Some(0.0));
        left.absorb(&right).unwrap();
        for i in 0..g.pixels() {
            assert_eq!(
                left.clipped_weight(CfaPlane::G1, i),
                whole.clipped_weight(CfaPlane::G1, i)
            );
            assert_eq!(left.contributing_weight(i), whole.contributing_weight(i));
        }
    }

    // ---- the robust pass-one election ----------------------------------

    /// `|z|` for a centre frame whose luma departs from an otherwise flat
    /// window by `delta`, with `var(L) = b`.
    ///
    /// Hand-derived rather than read back from the code, which is the point of
    /// having it: the kernel annihilates any polynomial of degree <= 2, so a
    /// flat window contributes exactly nothing and the numerator is
    /// `delta * r_centre = delta`. The denominator is `sqrt(b * sum r^2)`, and
    /// `sum r^2` for `W=5, P=2` is `2*(1/6)^2 + 2*(2/3)^2 + 1 = 35/18`.
    fn z_for_delta(delta: f32, b: f32) -> f32 {
        delta / (b * 35.0 / 18.0).sqrt()
    }

    /// Nine frames, all luma flat at 100 except frame 4 which departs by
    /// `delta`, and per-frame constant responses from `resp`.
    ///
    /// Frame 4 is the only index that is both centred (so `z` is defined) and
    /// far enough from both ends that its own contamination of the neighbours'
    /// windows can be reasoned about.
    fn nine_frames(delta: f32, resp: [f32; 9]) -> (Vec<Vec<f32>>, Vec<Vec<f32>>) {
        let px = 4;
        let mut luma = Vec::new();
        let mut reg = Vec::new();
        for (f, &r) in resp.iter().enumerate() {
            let l = if f == 4 { 100.0 + delta } else { 100.0 };
            luma.push(vec![l; px]);
            reg.push(vec![r; px]);
        }
        (luma, reg)
    }

    fn run_arm(arm: Arm, luma: &[Vec<f32>], reg: &[Vec<f32>], b: f32) -> FocusStats {
        let mut s = FocusStats::new_robust_with(geom(2, 2), arm, AffineVar { a: 0.0, b });
        for f in 0..luma.len() {
            s.fold_with_luma(f as u16, &reg[f], &luma[f]).unwrap();
        }
        s.finish_chunk();
        s
    }

    /// The strongest null available: `Ungated` runs the entire ring, the entire
    /// `z` computation and the entire election, and must still land on the same
    /// winner field as the shipped argmax, bit for bit.
    ///
    /// An env-unset test only proves the feature is off. This proves the new
    /// plumbing is *neutral*, which is a different and much stronger claim, and
    /// it is the one that says a difference seen later came from the gate
    /// rather than from the ring.
    #[test]
    fn ungated_arm_reproduces_the_shipped_election_bit_for_bit() {
        let mut rng = Rng::new(0x5EED_1234);
        let g = geom(8, 8);
        let px = g.pixels();
        let n = 11;
        let luma: Vec<Vec<f32>> = (0..n)
            .map(|_| (0..px).map(|_| 100.0 + 10.0 * rng.normal()).collect())
            .collect();
        let reg: Vec<Vec<f32>> = (0..n)
            .map(|_| (0..px).map(|_| rng.normal().abs()).collect())
            .collect();

        let mut plain = FocusStats::new(g);
        for (f, r) in reg.iter().enumerate() {
            plain.fold(f as u16, r).unwrap();
        }

        let mut rob =
            FocusStats::new_robust_with(g, Arm::Ungated, AffineVar { a: 0.0, b: 1.0 });
        for (f, (r, l)) in reg.iter().zip(luma.iter()).enumerate() {
            rob.fold_with_luma(f as u16, r, l).unwrap();
        }
        rob.finish_chunk();

        assert_eq!(rob.best_index(), plain.best_index());
        assert_eq!(rob.best_focus(), plain.best_focus());
        assert_eq!(rob.frames_folded(), plain.frames_folded());
        assert_eq!(rob.robust_fallbacks(), Some(0));
    }

    /// The ring defers every frame by `Z_HALF` and elects the ends with `z = 0`.
    /// A ring that drops or repeats a frame is nearly invisible downstream — an
    /// argmax absorbs a duplicate exactly, and a dropped frame only costs a
    /// little sharpness — so the count is asserted directly, at every chunk
    /// length either side of the window.
    #[test]
    fn the_ring_elects_every_frame_exactly_once_at_every_chunk_length() {
        for n in 1..=12u16 {
            let g = geom(2, 2);
            let mut s =
                FocusStats::new_robust_with(g, Arm::Soft, AffineVar { a: 0.0, b: 1.0 });
            for f in 0..n {
                let reg = vec![1.0 + f as f32; g.pixels()];
                let luma = vec![100.0; g.pixels()];
                s.fold_with_luma(f, &reg, &luma).unwrap();
            }
            s.finish_chunk();
            assert_eq!(
                s.robust_frames_elected(),
                Some(n as u32),
                "chunk of {n} frames"
            );
            // Flat luma is annihilated by the kernel, so nothing is penalised
            // and the plain argmax must survive: the last frame is sharpest.
            assert!(
                s.best_index().iter().all(|&i| i == n - 1),
                "chunk of {n} frames elected {:?}",
                s.best_index()
            );
        }
    }

    /// `finish_chunk` is called once per chunk by the merge, but a caller that
    /// calls it twice must not elect the tail twice.
    #[test]
    fn finish_chunk_is_idempotent() {
        let (luma, reg) = nine_frames(0.0, [1.0; 9]);
        let mut s = run_arm(Arm::Soft, &luma, &reg, 1.0);
        let before = s.best_index().to_vec();
        s.finish_chunk();
        assert_eq!(s.robust_frames_elected(), Some(9));
        assert_eq!(s.best_index(), &before[..]);
    }

    /// **The trap.** A stationary stack in which one frame legitimately
    /// disagrees *because it is the only frame that resolves that pixel*.
    ///
    /// This is `robust.rs`'s central warning made executable. Sharper means more
    /// contrast, which means the uniquely-resolving frame really does depart
    /// from the smooth through-focus trend — so `z` fires on it and there is no
    /// statistic on luma alone that can tell it from motion. Only `Soft`'s
    /// `w * response` survives that, and only because a 100x response beats a
    /// 4x penalty. `Hard` throws the photograph away on the same evidence,
    /// which is why it is not and must not become the default.
    #[test]
    fn trap_soft_keeps_the_only_frame_that_resolves_the_pixel() {
        // z = 6.0 -> w = ((8-6)/4)^2 = 0.25, i.e. a 4x penalty.
        let delta = 6.0 * (35.0f32 / 18.0).sqrt();
        assert!((z_for_delta(delta, 1.0) - 6.0).abs() < 1e-4);
        let mut resp = [1.0f32; 9];
        resp[0] = 1.5; // the runner-up, and ungated because it leads the chunk
        resp[4] = 100.0; // the frame that resolves the pixel

        let (l0, r0) = nine_frames(delta, resp);
        let soft = run_arm(Arm::Soft, &l0, &r0, 1.0);
        assert!(
            soft.best_index().iter().all(|&i| i == 4),
            "Soft unseated the only resolving frame: {:?}",
            soft.best_index()
        );
        assert_eq!(soft.robust_fallbacks(), Some(0));

        // The same evidence under Hard destroys it. Asserted, not assumed:
        // this is the measurement behind the default.
        let (l, r) = nine_frames(delta, resp);
        let hard = run_arm(Arm::Hard, &l, &r, 1.0);
        assert!(
            hard.best_index().iter().all(|&i| i == 0),
            "Hard was expected to discard frame 4 (w=0.25 < HARD_ELIGIBLE): {:?}",
            hard.best_index()
        );
    }

    /// **The plant.** The same wiring, the same arm, and a frame that wins the
    /// ungated election by a hair while disagreeing far beyond the knee — the
    /// signature fact 1189 measured, where a displaced edge is sharper than the
    /// stationary alternative and therefore wins.
    ///
    /// Proves the trap above is a real null and not a disconnected probe.
    #[test]
    fn plant_soft_rejects_a_moved_frame_that_wins_by_a_hair() {
        // z = 8.6 > Z_KNEE_HI -> w = 0 exactly.
        let delta = 12.0;
        assert!(z_for_delta(delta, 1.0) > 8.0);
        let mut resp = [1.0f32; 9];
        resp[4] = 2.0; // sharper than everything, because it moved

        let (l, r) = nine_frames(delta, resp);
        let ungated = run_arm(Arm::Ungated, &l, &r, 1.0);
        assert!(
            ungated.best_index().iter().all(|&i| i == 4),
            "the plant must win the shipped election, or it tests nothing"
        );

        let soft = run_arm(Arm::Soft, &l, &r, 1.0);
        assert!(
            soft.best_index().iter().all(|&i| i != 4),
            "Soft elected the moved frame: {:?}",
            soft.best_index()
        );
        // It declined a frame, it did not blank the pixel.
        assert_eq!(soft.robust_fallbacks(), Some(0));
        assert!(soft.best_focus().iter().all(|&v| v > 0.0));
    }

    /// Cross-chunk reduction must combine the **elections**, not the collapsed
    /// winner fields. Collapsing first and then taking an argmax over raw
    /// responses would compare a gated winner with an ungated one and let a
    /// rejected frame back in at a chunk boundary.
    #[test]
    fn absorb_combines_gated_scores_across_chunks() {
        let delta = 12.0;
        let mut resp = [1.0f32; 9];
        resp[4] = 2.0;
        let (l, r) = nine_frames(delta, resp);
        let g = geom(2, 2);
        let var = AffineVar { a: 0.0, b: 1.0 };

        // Chunk A holds the plant in a full window; chunk B is a clean tail.
        let mut a = FocusStats::new_robust_with(g, Arm::Soft, var);
        for f in 0..7 {
            a.fold_with_luma(f as u16, &r[f], &l[f]).unwrap();
        }
        a.finish_chunk();
        let mut b = FocusStats::new_robust_with(g, Arm::Soft, var);
        for f in 7..9 {
            b.fold_with_luma(f as u16, &r[f], &l[f]).unwrap();
        }
        b.finish_chunk();
        a.absorb(&b).unwrap();

        assert_eq!(a.frames_folded(), 9);
        assert_eq!(a.robust_frames_elected(), Some(9));
        assert!(
            a.best_index().iter().all(|&i| i != 4),
            "the reduce let the rejected frame back in: {:?}",
            a.best_index()
        );
    }

    /// A robust pass one folded without its luma would elect ungated and look
    /// like the gate doing nothing — the exact failure this project keeps
    /// finding. It must be loud.
    #[test]
    #[should_panic(expected = "fold_with_luma")]
    fn folding_without_luma_under_a_robust_election_panics() {
        let g = geom(2, 2);
        let mut s = FocusStats::new_robust_with(g, Arm::Soft, AffineVar { a: 0.0, b: 1.0 });
        s.fold(0, &vec![1.0; g.pixels()]).unwrap();
    }

    /// Reducing a gated pass one into an ungated one would silently discard the
    /// gate over half the frames.
    #[test]
    #[should_panic(expected = "different rules")]
    fn absorbing_a_robust_pass_one_into_a_plain_one_panics() {
        let g = geom(2, 2);
        let mut plain = FocusStats::new(g);
        let rob = FocusStats::new_robust_with(g, Arm::Soft, AffineVar { a: 0.0, b: 1.0 });
        plain.absorb(&rob).unwrap();
    }

    /// `fold_with_luma` must be exactly `fold` with the feature off, so the
    /// call site can use it unconditionally without the shipped path drifting.
    #[test]
    fn fold_with_luma_is_fold_when_the_feature_is_off() {
        let g = geom(4, 4);
        let mut rng = Rng::new(7);
        let reg: Vec<Vec<f32>> = (0..6)
            .map(|_| (0..g.pixels()).map(|_| rng.normal().abs()).collect())
            .collect();
        let mut a = FocusStats::new(g);
        let mut b = FocusStats::new(g);
        let zeros = vec![0.0f32; g.pixels()];
        for (f, r) in reg.iter().enumerate() {
            a.fold(f as u16, r).unwrap();
            b.fold_with_luma(f as u16, r, &zeros).unwrap();
        }
        b.finish_chunk();
        assert_eq!(a.best_index(), b.best_index());
        assert_eq!(a.best_focus(), b.best_focus());
        assert_eq!(b.arm(), None);
        assert_eq!(b.robust_frames_elected(), None);
    }

    /// A chunk shorter than the window elects EVERY frame with `z = 0`, so the
    /// gate does nothing whatever while reporting every frame elected and
    /// producing a perfectly good photograph. This is the defect that made the
    /// first real-data measurement of this feature a false zero: `merge_cmd`
    /// derives `chunk_len` from a memory budget, and 40 frames over 13 workers
    /// gives 3.
    ///
    /// The count is asserted at every length either side of the window, because
    /// the number that matters is not "did it run" but "how much of it ran".
    #[test]
    fn a_chunk_shorter_than_the_window_gates_nothing_and_says_so() {
        for n in 1..=12u16 {
            let g = geom(2, 2);
            let mut s =
                FocusStats::new_robust_with(g, Arm::Soft, AffineVar { a: 0.0, b: 1.0 });
            for f in 0..n {
                s.fold_with_luma(f, &vec![1.0 + f as f32; g.pixels()], &vec![100.0; g.pixels()])
                    .unwrap();
            }
            s.finish_chunk();
            // Z_HALF at each end are unavoidably starved; below the window
            // length every frame is.
            let want = if (n as usize) < Z_HALF * 2 + 1 {
                n as u32
            } else {
                (Z_HALF * 2) as u32
            };
            assert_eq!(
                s.window_starved_frames(),
                Some(want),
                "chunk of {n} frames: starved count"
            );
            if (n as usize) < Z_HALF * 2 + 1 {
                assert_eq!(
                    s.window_starved_frames().unwrap(),
                    s.frames_folded(),
                    "chunk of {n} is shorter than the window, so the gate must \
                     report that it scored nothing at all"
                );
            }
        }
    }

    #[test]
    fn arm_settings_parse_and_typos_are_refused() {
        assert_eq!(arm_from_setting(None), Ok(None));
        for off in ["", "0", "off", "false", " OFF "] {
            assert_eq!(arm_from_setting(Some(off)), Ok(None), "{off}");
        }
        for on in ["on", "1", "true", "soft", "SOFT"] {
            assert_eq!(arm_from_setting(Some(on)), Ok(Some(Arm::Soft)), "{on}");
        }
        assert_eq!(arm_from_setting(Some("hard")), Ok(Some(Arm::Hard)));
        assert_eq!(arm_from_setting(Some("ungated")), Ok(Some(Arm::Ungated)));
        // A typo must not read as off: a gate you believe is running and is
        // not looks exactly like a gate that does nothing.
        assert!(arm_from_setting(Some("sotf")).is_err());
        assert!(arm_from_setting(Some("yes")).is_err());
    }
}
