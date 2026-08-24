//! `strehl merge` — the estimation merge on real frames.
//!
//! This is the thing the project exists to build, wired to data. Where
//! `strehl stack` selects one frame per pixel (and is therefore the defect),
//! this regularises the focus field, elects a winner from the regularised
//! field, and then **averages every frame the calibrated noise model cannot
//! distinguish from that winner**.
//!
//! # Why two passes over the frames
//!
//! The gate compares each frame's regularised response against the winner's,
//! and the winner is not known until every frame has been seen. A single-pass
//! fold would have to carry per-pixel state that grows with the acceptance set.
//! Decode is 0.91 s warm (fact 33), so a second pass is the cheaper of the two
//! and it keeps peak memory O(workers). Pass two recomputes each frame's focus
//! field rather than caching it; caching would be O(frames) planes.
//!
//! # Why the whole gate sweep runs in one invocation
//!
//! The gate threshold is the merge's one free parameter and it is deliberately
//! unmeasured (question 90). Its calibration target is fact 212's `nwide = 3`.
//! Decode dominates pass two, so folding the same decoded frame into several
//! `Estimator`s at different thresholds costs almost nothing beyond the extra
//! accumulator memory — one run yields the whole calibration curve instead of
//! one point per decode budget. The worker plan is told about the accumulator
//! count so the budget still binds.
//!
//! # What is measured here
//!
//! Two acceptance invariants, and they are a **pair**. Fact 19 measured a plain
//! mean at 0.534x the single-frame noise; fact 24 measured that the same plain
//! mean collapses detail-region gradient by 58%. Either number alone can be won
//! trivially by a merge that is wrong in the other direction, so the report
//! prints them together and neither is a result on its own.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use strehl_core::clip::{CONTAINER_MAX_DN, ClipCensus};
use strehl_core::flat_ratio::{self, FrameFlat};
use strehl_core::focus::FocusField;
use strehl_core::merge::{
    Estimator, FOCUS_NOISE_SD, FocusStats, Gate, REGULARISER_WIDTH, regularise,
};
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;
use strehl_core::stack::{DEFAULT_SPECKLE_TOLERANCE as SPECKLE_TOLERANCE, speckle_fraction};
use strehl_core::through_focus::{
    ConfidenceVector, FINE_FOCUS_NOISE_SD, FLAG_BIMODAL, FLAG_BRACKET_BOUNDARY,
    FLAG_SCALE_DISAGREEMENT, PEAK_SEPARATION, STATS_RADIUS, ThroughFocus, do_not_trust_mask,
    shuffled_indices,
};
use strehl_core::{CfaPlane, Error};
use strehl_raw::Frame;

use crate::image_out;
use crate::stack::{
    MEMORY_BUDGET_BYTES, Roi, flat_roi_stats, mean_and_sigma, provenance_line, report_hp_reference,
    roi_green, srgb_encode,
};

pub struct MergeOptions {
    pub dir: PathBuf,
    pub out: Option<PathBuf>,
    pub limit: Option<usize>,
    pub srgb: bool,
    /// One or more gate thresholds, in units of the combined focus noise. Every
    /// one is folded in the same pass two.
    pub gates: Vec<f32>,
    pub flat_roi: Option<Roi>,
    pub detail_roi: Option<Roi>,
    /// Solve the ladder for the gate that achieves this mean `n_eff`.
    ///
    /// **This, not `gates`, is the parameter the project intends to ship.**
    /// A fixed threshold is not a calibration. M52 re-measured this across all
    /// seven stacks against the current pipeline: at gate 2.0 mean `n_eff` runs
    /// **1.177 (`foam`) to 14.386 (`coffee-bean`), a 12.22x spread**, and the
    /// gate needed to reach `n_eff = 3` runs **0.7618 to 21.9934, a factor of
    /// 28.9**. `foam` cannot reach `n_eff = 3` anywhere on the shipped 0.5-4.0
    /// ladder. A target `n_eff` transfers where a gate does not, and it is the
    /// quantity fact 212 calibrated.
    ///
    /// Fact 324 published "2.26 to 7.42" and "1.1 to 2.9" from a five-stack
    /// sweep taken before commit `2a4f5c5` corrected the ISO-50 gain floor. Its
    /// conclusion held and its magnitude was understated by 3.7x. The numbers
    /// above are M52's (`docs/research/M52-gate-cluster-verified.md`), whose
    /// independent Python merge agrees with the shipped binary to <= 0.09% on
    /// all seven stacks.
    pub target_n_eff: Option<f64>,
    /// Gather per-pixel through-focus sufficient statistics during pass two.
    ///
    /// Opt-in because it is not free, and **two different per-worker figures
    /// are in circulation for it**, so this says which is which:
    ///
    /// * **60 B/px = 494 MB** is [`ThroughFocus`] *alone*, the payload of the
    ///   struct itself. It is the right number for "what does the gathered
    ///   statistic cost", and the wrong one for "what does this flag cost".
    /// * **64 B/px = 527 MB** is what setting this field actually costs, and
    ///   is what a run reports, because it also forces a `FINE_FIELD_PER_PX`
    ///   4 B/px fine focus plane into every pass-two worker. This is the
    ///   number a user deciding whether to pass `--stats` wants.
    ///
    /// Neither is stale; they are two quantities under one label, which is the
    /// failure mode section 5 of `SYNTHESIS.md` calls the corpus's worst. The
    /// 527 figure is `px * (FINE_FIELD_PER_PX + gathers * bytes_per_pixel())`
    /// at `gathers = 1`; `stats_placebo` raises `gathers` to 2 and the total
    /// to 124 B/px, so 527 MB is the floor for this flag, not a constant.
    ///
    /// Either way it reduces the worker count the memory budget licenses. With
    /// it off, the merge path's memory is exactly what M37/M38 measured.
    pub stats: bool,
    /// Also gather a frame-permutation placebo alongside the statistics.
    ///
    /// Doubles the statistics memory. Without it the bimodality channel has no
    /// null on this stack and its absolute value means nothing.
    pub stats_placebo: bool,
    /// Tail fraction per channel for the "do not trust" union mask. M34 used
    /// 0.05 and measured a 14.278% union.
    pub confidence_tail: f64,
}

/// The outcome of solving a measured gate ladder for a target mean `n_eff`.
#[derive(Debug, Clone, Copy, PartialEq)]
pub(crate) enum Solve {
    /// The target lies inside the ladder; this gate reaches it.
    Gate(f64),
    /// The target is below everything the ladder measured. The reported gate is
    /// the ladder's lowest, and it already averages more than asked.
    BelowLadder { lowest_gate: f64, lowest: f64 },
    /// The target is above everything the ladder measured. Extrapolating a gate
    /// from a ladder that never reached the target would be inventing a number.
    AboveLadder { highest_gate: f64, highest: f64 },
    /// The ladder is not usable — fewer than two points, or not monotone.
    Unusable(&'static str),
}

/// Solve a measured `(gate, mean n_eff)` ladder for the gate hitting `target`.
///
/// # Why interpolation and not bisection
///
/// Pass two folds every gate in the ladder into its own accumulator for the
/// price of one decode, so a ladder is nearly free while each bisection step
/// costs a whole pass. One sweep therefore *is* the solve.
///
/// # Why log-log
///
/// The ladder is geometric in the gate and `n_eff` grows superlinearly in it
/// (109MSDCF: 1.414, 1.884, 2.891, 4.987 at gates 0.5, 1, 2, 4). Linear
/// interpolation on those points would systematically overestimate the gate.
/// In log-log the same ladder is close to straight, so the residual curvature
/// between adjacent rungs is small.
///
/// # Monotonicity is checked, not assumed
///
/// Admission is a threshold on a field fixed before the gate is applied, so a
/// larger gate admits a superset and `n_eff` cannot fall. That makes
/// non-monotonicity a bug rather than a property of the data, and it is
/// reported as `Unusable` rather than silently interpolated across.
pub(crate) fn solve_gate_for_n_eff(ladder: &[(f64, f64)], target: f64) -> Solve {
    if ladder.len() < 2 {
        return Solve::Unusable("a ladder needs at least two rungs to interpolate");
    }
    if target.is_nan() || target <= 1.0 {
        return Solve::Unusable("a target n_eff must exceed 1.0; the winner is always admitted");
    }
    let mut v: Vec<(f64, f64)> = ladder.to_vec();
    v.sort_by(|a, b| {
        a.0.partial_cmp(&b.0)
            .expect("gate ladder must not hold NaN")
    });
    if v.windows(2).any(|w| w[1].1 < w[0].1) {
        return Solve::Unusable("n_eff fell as the gate rose, which is a bug, not a measurement");
    }
    if v.iter().any(|r| r.0 <= 0.0 || r.1 <= 0.0) {
        return Solve::Unusable("log-log interpolation needs strictly positive rungs");
    }

    let (lo, hi) = (v[0], v[v.len() - 1]);
    if target < lo.1 {
        return Solve::BelowLadder {
            lowest_gate: lo.0,
            lowest: lo.1,
        };
    }
    if target > hi.1 {
        return Solve::AboveLadder {
            highest_gate: hi.0,
            highest: hi.1,
        };
    }
    for w in v.windows(2) {
        let ((g0, n0), (g1, n1)) = (w[0], w[1]);
        if target >= n0 && target <= n1 {
            if (n1 - n0).abs() < f64::EPSILON {
                return Solve::Gate(g0);
            }
            let f = (target.ln() - n0.ln()) / (n1.ln() - n0.ln());
            return Solve::Gate((g0.ln() + f * (g1.ln() - g0.ln())).exp());
        }
    }
    Solve::Unusable("the target fell between no pair of rungs, which cannot happen")
}

/// Report the solve, or explain why the sweep did not answer the question.
fn report_target_solve(est: &[Estimator], target: Option<f64>) {
    let Some(target) = target else {
        eprintln!(
            "gate solve      : not requested. Pass --target-n-eff 3 to solve the ladder for a\n\
             \x20                 gate, which is what fact 324 says you should be setting."
        );
        eprintln!();
        return;
    };
    let ladder: Vec<(f64, f64)> = est
        .iter()
        .map(|e| (e.gate().threshold as f64, e.mean_n_eff()))
        .filter(|r| r.0 > 0.0)
        .collect();

    eprintln!("--- gate solved for a target n_eff (MEASURED ladder, INTERPOLATED gate) ---");
    match solve_gate_for_n_eff(&ladder, target) {
        Solve::Gate(g) => {
            eprintln!("target n_eff    : {target:.3}");
            eprintln!("gate            : {g:.4}   (log-log interpolation between measured rungs)");
            eprintln!(
                "                  Re-run with --gate {g:.4} to confirm; interpolation is not\n\
                 \x20                 a measurement, and the rungs bracketing it are."
            );
        }
        Solve::BelowLadder {
            lowest_gate,
            lowest,
        } => eprintln!(
            "target n_eff {target:.3} is below the ladder: gate {lowest_gate:.4} already \
             averages {lowest:.3}.\n                  Extend the ladder downward to solve it."
        ),
        Solve::AboveLadder {
            highest_gate,
            highest,
        } => eprintln!(
            "target n_eff {target:.3} is above the ladder: gate {highest_gate:.4} reaches only \
             {highest:.3}.\n                  Extend the ladder upward; extrapolating would be \
             inventing a number."
        ),
        Solve::Unusable(why) => eprintln!("cannot solve    : {why}"),
    }
    eprintln!();
}

///
/// # Why more than one number
///
/// **`m2_pooled_abs` is fact 24's convention**, identified by measurement, not
/// by assumption: M2's harness is not preserved in the repository, so M38 §1
/// computed seven candidate conventions with an independent numpy
/// implementation and asked which reproduced the published 11.89 and 18.58.
/// `mean(0.5*(|dx| + |dy|))` hits both to **0.01% and 0.02%**. The pre-registered
/// guess — single-axis `|dx|`, predicted from the pi/2 ratio between an
/// isotropic magnitude and one component — matched one ROI and missed the other
/// by 17.5%, because ROI `64,800` is **1.43x anisotropic** (`|dy|` 21.84 against
/// `|dx|` 15.32). Reporting this column is what makes any comparison against
/// fact 24 legitimate; the two harnesses differ by 1.55x and 1.60x, an
/// ROI-dependent factor, so the conversion cannot be a constant.
///
/// # Why the correction exists
///
/// **Mean |grad| is confounded by noise, and the confound has the same sign as
/// the effect the metric is used to detect.** Noise contributes gradient. A
/// merge that reduces sigma therefore reduces mean |grad| *even with zero
/// blur*, so an uncorrected reading charges the merge for the very thing it is
/// supposed to do. This is not hypothetical here: M2 measured that argmax
/// *raises* gradient (fact 24), and argmax also raises noise (fact 19) — the
/// same confound, read as a virtue.
///
/// The squared form is additively decomposable where the absolute form is not:
/// `E[dx^2] = E[dx_signal^2] + E[dx_noise^2]`. With forward differences and
/// per-pixel `sigma`, the noise contribution at pixel `i` is exactly
/// `2*sigma_i^2 + sigma_{i+1}^2 + sigma_{i+w}^2`, so
/// `corrected_rms = sqrt(max(0, raw_rms^2 - noise_rms^2))` removes it using the
/// calibrated model rather than an assumption. M77 showed why that subtraction
/// is insufficient after selection: model sigma does not include max-over-N
/// inflation. Invariant 2 now uses [`cross_fitted_detail`]; this field remains
/// for component tests and historical columns only.
#[cfg_attr(not(test), allow(dead_code))]
struct DetailMetrics {
    /// `mean(0.5*(|dx| + |dy|))` — fact 24's convention, for comparability.
    m2_pooled_abs: f64,
    /// `mean(hypot(dx, dy))` — isotropic, rotation-invariant.
    iso_mean: f64,
    /// `sqrt(mean(dx^2 + dy^2))` — signal and noise together.
    raw_rms: f64,
    /// The model's prediction for what the noise alone contributes to it.
    noise_rms: f64,
    /// Model-only correction, not the post-selection acceptance headline.
    corrected_rms: f64,
}

/// Compute [`DetailMetrics`] from co-located values and per-pixel predicted
/// sigmas.
///
/// `sigma[i]` must be the predicted standard deviation of `v[i]` in the same
/// units, which for the merged image means it already carries the `1/sqrt(n)`
/// from averaging.
fn detail_metrics(v: &[f32], sigma: &[f32], w: usize, h: usize) -> DetailMetrics {
    if w < 2 || h < 2 {
        return DetailMetrics {
            m2_pooled_abs: 0.0,
            iso_mean: 0.0,
            raw_rms: 0.0,
            noise_rms: 0.0,
            corrected_rms: 0.0,
        };
    }
    let (mut pooled, mut iso, mut sq, mut nsq) = (0.0f64, 0.0f64, 0.0f64, 0.0f64);
    let mut n = 0usize;
    for y in 0..h - 1 {
        for x in 0..w - 1 {
            let i = y * w + x;
            let dx = (v[i + 1] - v[i]) as f64;
            let dy = (v[i + w] - v[i]) as f64;
            pooled += 0.5 * (dx.abs() + dy.abs());
            iso += (dx * dx + dy * dy).sqrt();
            sq += dx * dx + dy * dy;
            let (s0, s1, sw) = (sigma[i] as f64, sigma[i + 1] as f64, sigma[i + w] as f64);
            nsq += 2.0 * s0 * s0 + s1 * s1 + sw * sw;
            n += 1;
        }
    }
    let n = n as f64;
    let raw_rms = (sq / n).sqrt();
    let noise_rms = (nsq / n).sqrt();
    DetailMetrics {
        m2_pooled_abs: pooled / n,
        iso_mean: iso / n,
        raw_rms,
        noise_rms,
        corrected_rms: (raw_rms * raw_rms - noise_rms * noise_rms).max(0.0).sqrt(),
    }
}

#[derive(Clone, Copy, Debug)]
struct GradientPower {
    raw_sum: f64,
    noise_sum: f64,
    samples: usize,
}

fn gradient_power_columns(
    v: &[f32],
    sigma: &[f32],
    w: usize,
    h: usize,
    x0: usize,
    x1: usize,
) -> GradientPower {
    assert_eq!(v.len(), w * h);
    assert_eq!(sigma.len(), w * h);
    assert!(x0 < x1 && x1 <= w);
    let (mut raw_sum, mut noise_sum, mut samples) = (0.0f64, 0.0f64, 0usize);
    if h < 2 || x1 - x0 < 2 {
        return GradientPower {
            raw_sum,
            noise_sum,
            samples,
        };
    }
    for y in 0..h - 1 {
        for x in x0..x1 - 1 {
            let i = y * w + x;
            let dx = f64::from(v[i + 1] - v[i]);
            let dy = f64::from(v[i + w] - v[i]);
            raw_sum += dx * dx + dy * dy;
            let (s0, s1, sw) = (
                f64::from(sigma[i]),
                f64::from(sigma[i + 1]),
                f64::from(sigma[i + w]),
            );
            noise_sum += 2.0 * s0 * s0 + s1 * s1 + sw * sw;
            samples += 1;
        }
    }
    GradientPower {
        raw_sum,
        noise_sum,
        samples,
    }
}

#[derive(Clone, Copy, Debug)]
struct ControlledDetail {
    raw_power: f64,
    controlled_noise_power: f64,
    signal_power: f64,
    structure: f64,
    inflation_left: f64,
    inflation_right: f64,
}

/// Remove selection-conditioned gradient noise with a contemporaneous flat
/// control rather than a constant transferred between stack lengths.
///
/// The flat and detail regions are split into disjoint left/right sets of
/// gradient anchors. Each detail half is corrected with the scale fitted on the
/// opposite flat half. When the detail ROI is the flat ROI, as in M77's null,
/// no sample is used both to fit and to evaluate its own scale.
fn cross_fitted_detail(
    detail: &[f32],
    detail_sigma: &[f32],
    detail_w: usize,
    detail_h: usize,
    flat: &[f32],
    flat_sigma: &[f32],
    flat_w: usize,
    flat_h: usize,
) -> Result<ControlledDetail> {
    ensure!(
        detail_w >= 4 && detail_h >= 2 && flat_w >= 4 && flat_h >= 2,
        "the repaired detail invariant needs flat and detail ROIs at least 4x2"
    );
    let flat_mid = flat_w / 2;
    let detail_mid = detail_w / 2;
    let flat_left = gradient_power_columns(flat, flat_sigma, flat_w, flat_h, 0, flat_mid);
    let flat_right = gradient_power_columns(flat, flat_sigma, flat_w, flat_h, flat_mid, flat_w);
    let detail_left =
        gradient_power_columns(detail, detail_sigma, detail_w, detail_h, 0, detail_mid);
    let detail_right = gradient_power_columns(
        detail,
        detail_sigma,
        detail_w,
        detail_h,
        detail_mid,
        detail_w,
    );
    ensure!(
        flat_left.samples > 0
            && flat_right.samples > 0
            && detail_left.samples > 0
            && detail_right.samples > 0,
        "the repaired detail invariant has no gradient samples in one ROI half"
    );
    ensure!(
        flat_left.noise_sum > 0.0
            && flat_right.noise_sum > 0.0
            && detail_left.noise_sum > 0.0
            && detail_right.noise_sum > 0.0,
        "the calibrated noise model returned zero gradient power"
    );

    let scale_left = flat_left.raw_sum / flat_left.noise_sum;
    let scale_right = flat_right.raw_sum / flat_right.noise_sum;
    let (scale_for_detail_left, scale_for_detail_right) = (scale_right, scale_left); // M80_CROSS_FITTED_SCALES
    let samples = detail_left.samples + detail_right.samples;
    let raw_sum = detail_left.raw_sum + detail_right.raw_sum;
    let controlled_noise_sum = scale_for_detail_left * detail_left.noise_sum
        + scale_for_detail_right * detail_right.noise_sum;
    ensure!(
        scale_left.is_finite()
            && scale_right.is_finite()
            && controlled_noise_sum.is_finite()
            && controlled_noise_sum > 0.0,
        "the flat-control selection-noise scale is not finite and positive"
    );
    let raw_power = raw_sum / samples as f64;
    let controlled_noise_power = controlled_noise_sum / samples as f64;
    Ok(ControlledDetail {
        raw_power,
        controlled_noise_power,
        signal_power: raw_power - controlled_noise_power,
        structure: (raw_power / controlled_noise_power).sqrt(),
        inflation_left: scale_left.sqrt(),
        inflation_right: scale_right.sqrt(),
    })
}

fn equal_noise_retention(candidate: ControlledDetail, selector: ControlledDetail) -> f64 {
    if selector.raw_power <= 0.0 {
        return f64::NAN;
    }
    ((candidate.signal_power + selector.controlled_noise_power).max(0.0) / selector.raw_power)
        .sqrt()
}

/// Merged green over an ROI, black-subtracted, in plane coordinates.
///
/// Deliberately the same shape as [`roi_green`] so the two sides of the detail
/// ratio are gathered the same way.
fn roi_green_merged(est: &Estimator, roi: Roi, geom: PlaneGeometry, black: f32) -> Vec<f32> {
    let mut out = Vec::with_capacity(roi.width * roi.height);
    for py in roi.y..roi.y + roi.height {
        for px in roi.x..roi.x + roi.width {
            out.push(est.green_mean(geom.index(px, py)) - black);
        }
    }
    out
}

struct SelectedRoi {
    roi: Roi,
    values: Vec<f32>,
    seen: Vec<bool>,
}

impl SelectedRoi {
    fn new(roi: Roi) -> Self {
        Self {
            roi,
            values: vec![0.0; roi.width * roi.height],
            seen: vec![false; roi.width * roi.height],
        }
    }

    fn fold(
        &mut self,
        frame: &Frame,
        frame_index: u16,
        best_index: &[u16],
        geom: PlaneGeometry,
        black: f32,
    ) {
        let values = roi_green(frame, self.roi, black);
        for y in 0..self.roi.height {
            for x in 0..self.roi.width {
                let local = y * self.roi.width + x;
                let global = geom.index(self.roi.x + x, self.roi.y + y);
                if best_index[global] == frame_index {
                    assert!(
                        !self.seen[local],
                        "selector ROI pixel {local} was supplied by two frames"
                    );
                    self.values[local] = values[local];
                    self.seen[local] = true;
                }
            }
        }
    }

    fn absorb(&mut self, other: &Self) {
        assert_eq!(self.roi, other.roi);
        for i in 0..self.values.len() {
            if other.seen[i] {
                assert!(
                    !self.seen[i],
                    "selector ROI pixel {i} occurred in two worker chunks"
                );
                self.values[i] = other.values[i];
                self.seen[i] = true;
            }
        }
    }

    fn is_complete(&self) -> bool {
        self.seen.iter().all(|v| *v)
    }
}

struct SelectorRois {
    flat: SelectedRoi,
    detail: SelectedRoi,
}

impl SelectorRois {
    fn new(flat: Roi, detail: Roi) -> Self {
        Self {
            flat: SelectedRoi::new(flat),
            detail: SelectedRoi::new(detail),
        }
    }

    fn fold(
        &mut self,
        frame: &Frame,
        frame_index: u16,
        best_index: &[u16],
        geom: PlaneGeometry,
        black: f32,
    ) {
        self.flat.fold(frame, frame_index, best_index, geom, black);
        self.detail
            .fold(frame, frame_index, best_index, geom, black);
    }

    fn absorb(&mut self, other: &Self) {
        self.flat.absorb(&other.flat);
        self.detail.absorb(&other.detail);
    }

    fn is_complete(&self) -> bool {
        self.flat.is_complete() && self.detail.is_complete()
    }
}

struct Plan {
    workers: usize,
    chunks: usize,
    chunk_len: usize,
    pass1_bytes: usize,
    pass2_bytes: usize,
    stats_bytes: usize,
    roi_bytes: usize,
}

/// Per-worker bytes in pass one: `FocusStats` (f32 focus + u16 index) plus the
/// four scratch planes the fold walks through.
const PASS1_PER_PX: usize = 6 + 4 + 12 + 4 + 4;
/// Per-worker scratch in pass two, excluding the accumulators.
const PASS2_SCRATCH_PER_PX: usize = 4 + 12 + 4 + 4;
/// One `Estimator`: four f32 sums, a u16 count, and the winner field it was
/// built from (f32 + u16).
const ESTIMATOR_PER_PX: usize = 4 * 4 + 2 + 4 + 2;
/// The extra fine focus plane `--stats` needs in every pass-two worker's
/// scratch. `ThroughFocus`'s own footprint is priced separately because it is
/// per gather rather than per frame.
const FINE_FIELD_PER_PX: usize = 4;

impl Plan {
    fn new(
        frames: usize,
        geom: PlaneGeometry,
        frame_bytes: usize,
        gates: usize,
        gathers: usize,
        roi_bytes: usize,
    ) -> Self {
        let px = geom.pixels();
        let pass1_bytes = px * PASS1_PER_PX + frame_bytes;
        // The statistics ride pass two, so they are priced into pass two and
        // therefore into the worker count. This is the honest place for them:
        // pricing them outside the per-worker term would license more workers
        // than the budget pays for, which is exactly the defect M8 measured in
        // the pre-M8 `buffers` model.
        let stats_bytes = if gathers > 0 {
            px * (FINE_FIELD_PER_PX + gathers * ThroughFocus::bytes_per_pixel())
        } else {
            0
        };
        let pass2_bytes = px * (PASS2_SCRATCH_PER_PX + gates * ESTIMATOR_PER_PX)
            + stats_bytes
            + roi_bytes
            + frame_bytes;
        // The binding pass is whichever needs more per worker, so that one
        // worker count is safe for both and the two passes chunk identically.
        let per_worker = pass1_bytes.max(pass2_bytes);
        let by_memory = (MEMORY_BUDGET_BYTES / per_worker).max(1);
        let by_cpu = std::thread::available_parallelism()
            .map(|v| v.get())
            .unwrap_or(1);
        let workers = by_memory.min(by_cpu).min(frames.max(1));
        let chunk_len = frames.div_ceil(workers);
        Self {
            workers,
            chunks: frames.div_ceil(chunk_len),
            chunk_len,
            pass1_bytes,
            pass2_bytes,
            stats_bytes,
            roi_bytes,
        }
    }

    fn describe(&self) -> String {
        let mut s = format!(
            "workers         : {} chunks of <= {} frames ({} allowed by the {} MB budget, {} by CPU)\n\
             working set     : {:.0} MB/worker pass 1, {:.0} MB/worker pass 2 (buffers only, a \
             LOWER BOUND)",
            self.chunks,
            self.chunk_len,
            self.workers,
            MEMORY_BUDGET_BYTES / (1 << 20),
            std::thread::available_parallelism()
                .map(|v| v.get())
                .unwrap_or(1),
            self.pass1_bytes as f64 / 1e6,
            self.pass2_bytes as f64 / 1e6,
        );
        if self.stats_bytes > 0 {
            s.push_str(&format!(
                "\n  of which stats: {:.0} MB/worker of through-focus sufficient statistics, \
                 CONSTANT in the frame count",
                self.stats_bytes as f64 / 1e6
            ));
        }
        if self.roi_bytes > 0 {
            s.push_str(&format!(
                "\n  of which detail control: {:.1} MB/worker, CONSTANT in the frame count",
                self.roi_bytes as f64 / 1e6
            ));
        }
        s
    }
}

/// Everything a worker needs that is identical across both passes.
struct Ctx<'a> {
    geom: PlaneGeometry,
    levels: Levels,
    noise: &'a NoiseModel,
    live: &'a AtomicUsize,
    peak_live: &'a AtomicUsize,
}

/// Per-worker scratch, allocated once per chunk and reused across frames.
///
/// Bundled rather than passed loose because both passes need exactly this set
/// and the memory plan prices it as one unit.
struct Scratch {
    luma: Vec<f32>,
    field: FocusField,
    box_scratch: Vec<f32>,
    reg: Vec<f32>,
    /// The fine focus field, allocated only when `--stats` asked for it.
    fine: Vec<f32>,
    /// Per-pixel clip flags for the frame currently in `luma`.
    clipped: Vec<bool>,
}

impl Scratch {
    fn new(geom: PlaneGeometry, fine: bool) -> Self {
        let px = geom.pixels();
        Self {
            luma: vec![0.0; px],
            field: FocusField::new(geom),
            box_scratch: vec![0.0; px],
            reg: vec![0.0; px],
            fine: if fine { vec![0.0; px] } else { Vec::new() },
            clipped: vec![false; px],
        }
    }
}

#[derive(Default, Clone, Copy)]
struct Timings {
    decode: f64,
    work: f64,
}

impl Timings {
    fn add(&mut self, other: Timings) {
        self.decode += other.decode;
        self.work += other.work;
    }
}

impl Ctx<'_> {
    /// Decode one frame and produce its regularised focus field into
    /// `scratch.reg`.
    ///
    /// Both passes go through here, which is the point: pass two's gate is only
    /// meaningful if the field it compares was produced by the same arithmetic
    /// that elected the winner in pass one.
    fn field_for(
        &self,
        path: &Path,
        index: u16,
        scratch: &mut Scratch,
        t: &mut Timings,
    ) -> Result<Frame> {
        let t0 = Instant::now();
        let in_flight = self.live.fetch_add(1, Ordering::Relaxed) + 1;
        self.peak_live.fetch_max(in_flight, Ordering::Relaxed);
        let frame = match strehl_raw::decode(path) {
            Ok(f) => f,
            Err(e) => {
                self.live.fetch_sub(1, Ordering::Relaxed);
                return Err(e).with_context(|| format!("frame {index}"));
            }
        };
        t.decode += t0.elapsed().as_secs_f64();

        let t0 = Instant::now();
        if frame.levels != self.levels {
            self.live.fetch_sub(1, Ordering::Relaxed);
            bail!(
                "frame {index} ({}) has levels black {} white {}, but the stack was calibrated at \
                 black {} white {}",
                frame.path.display(),
                frame.levels.black,
                frame.levels.white,
                self.levels.black,
                self.levels.white
            );
        }
        green_luma_with_clip(
            &frame,
            self.levels.black,
            CONTAINER_MAX_DN,
            &mut scratch.luma,
            &mut scratch.clipped,
        );
        if scratch.fine.is_empty() {
            scratch.field.compute(&scratch.luma, self.noise);
        } else {
            // One shared gradient pass produces both scales. The selection field
            // is bit-identical either way — pinned by
            // `through_focus::tests::gathering_statistics_cannot_move_the_selection_field`
            // — so turning statistics on cannot move the merge.
            scratch.field.compute_with_fine(
                &scratch.luma,
                self.noise,
                STATS_RADIUS,
                &mut scratch.fine,
            );
        }
        regularise(
            scratch.field.values(),
            self.geom,
            &mut scratch.box_scratch,
            &mut scratch.reg,
        );
        t.work += t0.elapsed().as_secs_f64();
        Ok(frame)
    }

    fn release(&self, frame: Frame) {
        drop(frame);
        self.live.fetch_sub(1, Ordering::Relaxed);
    }
}

struct Pass1 {
    stats: FocusStats,
    /// Census of samples pinned at the container maximum. Two bytes per pixel,
    /// constant in the frame count, so the ratchet is untouched.
    clip: ClipCensus,
    /// The middle frame's flat and detail ROIs, kept by whichever worker
    /// decoded it. `flat` now feeds the LEGACY raw ratio only; the noise
    /// invariant references `flat_frames` instead.
    flat: Option<Vec<f32>>,
    /// `(frame index, flat-ROI moments)` for **every** frame. Three `f64` per
    /// frame, so it is constant in the ROI size and irrelevant to the ratchet.
    /// Fact 441: one privileged denominator moves the published ratio 1.60x, so
    /// there is no longer a privileged denominator to move.
    flat_frames: Vec<(u16, FrameFlat)>,
    t: Timings,
}

struct Pass2 {
    est: Vec<Estimator>,
    /// A compact gate-zero reference over only the two requested ROIs. It is
    /// read from the completed pass-one winner map and never touches `est`.
    selector: Option<SelectorRois>,
    /// The through-focus sufficient statistics, and their permutation placebo.
    /// Both `None` unless `--stats` was passed.
    tf: Option<ThroughFocus>,
    placebo: Option<ThroughFocus>,
    t: Timings,
}

fn map_dim_err(index: u16, e: Error) -> anyhow::Error {
    match e {
        Error::DimensionMismatch { got, want, .. } => {
            anyhow::anyhow!("frame {index} has plane geometry {got:?}, expected {want:?}")
        }
        other => anyhow::anyhow!(other),
    }
}

pub fn run(opts: &MergeOptions) -> Result<()> {
    ensure!(!opts.gates.is_empty(), "at least one --gate is required");
    ensure!(
        opts.gates.iter().all(|g| g.is_finite() && *g >= 0.0),
        "gate thresholds must be finite and non-negative"
    );
    if opts.out.is_some() {
        ensure!(
            opts.gates.len() == 1,
            "--out writes one image, but {} gates were given; pick one",
            opts.gates.len()
        );
    }

    let paths = crate::raw_paths(&opts.dir, opts.limit)?;
    ensure!(
        paths.len() < u16::MAX as usize,
        "{} frames exceeds the u16 winner-index range",
        paths.len()
    );
    let input_bytes: u64 = paths
        .iter()
        .filter_map(|p| std::fs::metadata(p).ok().map(|m| m.len()))
        .sum();

    let t_prologue = Instant::now();
    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let prologue_secs = t_prologue.elapsed().as_secs_f64();
    let geom = first.geometry();
    let levels = first.levels;
    let camera = first.camera.clone();
    let iso = first.iso;
    let wb = first.wb_gains();
    let frame_bytes = first.allocated_bytes();
    drop(first);

    let noise = profile::noise_model_for(&camera, iso, levels);
    let middle = (paths.len() / 2) as u16;

    for (label, roi) in [
        ("--flat-roi", opts.flat_roi),
        ("--detail-roi", opts.detail_roi),
    ] {
        if let Some(roi) = roi {
            ensure!(
                roi.x + roi.width <= geom.width && roi.y + roi.height <= geom.height,
                "{label} {},{},{},{} does not fit inside the {}x{} plane",
                roi.x,
                roi.y,
                roi.width,
                roi.height,
                geom.width,
                geom.height
            );
        }
    }

    let roi_bytes = match (opts.flat_roi, opts.detail_roi) {
        (Some(flat), Some(detail)) => {
            let flat_px = flat.width * flat.height;
            let detail_px = detail.width * detail.height;
            // One f32 value plus a conservative byte for `Vec<bool>` per
            // captured pixel, and one temporary f32 extraction buffer.
            5 * (flat_px + detail_px) + 4 * flat_px.max(detail_px)
        }
        _ => 0,
    };
    let plan = Plan::new(
        paths.len(),
        geom,
        frame_bytes,
        opts.gates.len(),
        if opts.stats {
            1 + usize::from(opts.stats_placebo)
        } else {
            0
        },
        roi_bytes,
    );

    // The placebo permutation. Fixed, auditable and reproducible.
    //
    // NOT a rotation. `k -> (k + n/3) mod n` was the first draft and it is an
    // isometry of the index line, so adjacency survives and the placebo returned
    // exactly 1.0000x of the real reading -- a null that had silently become a
    // copy of its own subject. A seeded shuffle is the fix; the core test
    // `shuffle_destroys_adjacency_which_a_rotation_does_not` holds the line.
    let perm: Vec<u16> = shuffled_indices(paths.len(), PLACEBO_SEED);

    eprintln!(
        "strehl stack -- regularised winner + noise-gated average (THE DEFAULT PATH, an estimator)"
    );
    eprintln!("camera          : {camera}");
    eprintln!(
        "iso             : {}",
        iso.map(|v| format!("{v:.0}")).unwrap_or("UNKNOWN".into())
    );
    eprintln!(
        "levels          : black {}, white {}",
        levels.black, levels.white
    );
    eprintln!("{}", provenance_line(&noise));
    eprintln!(
        "regulariser     : {REGULARISER_WIDTH}x{REGULARISER_WIDTH} box on the focus field \
         (fact 84: -35% absolute error; fact 86: width 3 is WORSE than none)"
    );
    eprintln!(
        "focus noise sd  : {FOCUS_NOISE_SD:.6} on the regularised field, MEASURED in-crate \
         (facts 310-313)"
    );
    eprintln!(
        "gates           : {}  (UNCALIBRATED -- question 90; target is fact 212's nwide = 3)",
        opts.gates
            .iter()
            .map(|g| format!("{g:.2}"))
            .collect::<Vec<_>>()
            .join(", ")
    );
    eprintln!(
        "planes          : {} x {} per CFA plane",
        geom.width, geom.height
    );
    eprintln!(
        "frames          : {} from {}",
        paths.len(),
        opts.dir.display()
    );
    eprintln!("{}", plan.describe());
    eprintln!();

    let live = AtomicUsize::new(0);
    let peak_live = AtomicUsize::new(0);
    let ctx = Ctx {
        geom,
        levels,
        noise: &noise,
        live: &live,
        peak_live: &peak_live,
    };

    // ---- pass one: regularised winner field -------------------------------
    let t1 = Instant::now();
    let p1 = paths
        .par_chunks(plan.chunk_len)
        .enumerate()
        .map(|(ci, chunk)| -> Result<Pass1> {
            let first_index = (ci * plan.chunk_len) as u16;
            let mut stats = FocusStats::new(geom);
            let mut clip = ClipCensus::new(geom);
            let mut scratch = Scratch::new(geom, false);
            let mut flat = None;
            let mut flat_frames: Vec<(u16, FrameFlat)> = Vec::with_capacity(chunk.len());
            let mut t = Timings::default();

            for (offset, path) in chunk.iter().enumerate() {
                let index = first_index + offset as u16;
                let frame = ctx.field_for(path, index, &mut scratch, &mut t)?;
                if let Some(r) = opts.flat_roi {
                    // Every frame, not only the middle one. The denominator of
                    // the noise invariant is the whole distribution (fact 441).
                    let g = roi_green(&frame, r, levels.black);
                    flat_frames.push((index, flat_ratio::frame_flat(&g, r.width, r.height)));
                    if index == middle {
                        flat = Some(g);
                    }
                }
                ctx.release(frame);
                stats
                    .fold(index, &scratch.reg)
                    .map_err(|e| map_dim_err(index, e))?;
                clip.fold(&scratch.clipped)
                    .map_err(|e| map_dim_err(index, e))?;
            }
            Ok(Pass1 {
                stats,
                clip,
                flat,
                flat_frames,
                t,
            })
        })
        .reduce_with(|a, b| match (a, b) {
            (Ok(mut a), Ok(b)) => {
                a.stats.absorb(&b.stats).map_err(|e| map_dim_err(0, e))?;
                a.clip.absorb(&b.clip).map_err(|e| map_dim_err(0, e))?;
                a.flat = a.flat.or(b.flat);
                a.flat_frames.extend(b.flat_frames);
                a.t.add(b.t);
                Ok(a)
            }
            (Err(e), _) | (Ok(_), Err(e)) => Err(e),
        })
        .expect("at least one chunk")?;
    let pass1_secs = t1.elapsed().as_secs_f64();

    ensure!(
        p1.stats.frames_folded() as usize == paths.len(),
        "pass one folded {} frames, expected {}",
        p1.stats.frames_folded(),
        paths.len()
    );

    let n = paths.len() as f64;
    eprintln!("--- pass one: regularised winner field (MEASURED) ---");
    eprintln!(
        "wall clock      : {pass1_secs:.3} s  ({:.1} ms/frame)",
        1000.0 * pass1_secs / n
    );
    eprintln!(
        "  decode        : {:.3} s summed across workers ({:.1} ms/frame)",
        p1.t.decode,
        1000.0 * p1.t.decode / n
    );
    eprintln!(
        "  focus + reg   : {:.3} s summed across workers ({:.1} ms/frame)",
        p1.t.work,
        1000.0 * p1.t.work / n
    );
    eprintln!();

    // ---- pass two: gated average ------------------------------------------
    let t2 = Instant::now();
    let p2 = paths
        .par_chunks(plan.chunk_len)
        .enumerate()
        .map(|(ci, chunk)| -> Result<Pass2> {
            let first_index = (ci * plan.chunk_len) as u16;
            let mut est: Vec<Estimator> = opts
                .gates
                .iter()
                .map(|g| Estimator::new(&p1.stats, Gate::new(*g)))
                .collect();
            let mut selector = match (opts.flat_roi, opts.detail_roi) {
                (Some(flat), Some(detail)) => Some(SelectorRois::new(flat, detail)),
                _ => None,
            };
            let mut tf = opts.stats.then(|| ThroughFocus::new(&p1.stats));
            let mut placebo = (opts.stats && opts.stats_placebo)
                .then(|| ThroughFocus::new_permuted(&p1.stats, &perm));
            let mut scratch = Scratch::new(geom, opts.stats);
            let mut t = Timings::default();

            for (offset, path) in chunk.iter().enumerate() {
                let index = first_index + offset as u16;
                let frame = ctx.field_for(path, index, &mut scratch, &mut t)?;
                let t0 = Instant::now();
                let mut err = None;
                for e in est.iter_mut() {
                    if let Err(e) = e.fold_censored(index, &frame, &scratch.reg, CONTAINER_MAX_DN) {
                        err = Some(map_dim_err(index, e));
                        break;
                    }
                }
                if err.is_none()
                    && let Some(selector) = selector.as_mut()
                {
                    selector.fold(&frame, index, p1.stats.best_index(), geom, levels.black);
                }
                ctx.release(frame);
                if let Some(e) = err {
                    return Err(e);
                }
                if let Some(tf) = tf.as_mut() {
                    tf.fold(index, &scratch.fine, &scratch.reg)
                        .map_err(|e| map_dim_err(index, e))?;
                }
                if let Some(p) = placebo.as_mut() {
                    p.fold(perm[index as usize], &scratch.fine, &scratch.reg)
                        .map_err(|e| map_dim_err(index, e))?;
                }
                t.work += t0.elapsed().as_secs_f64();
            }
            Ok(Pass2 {
                est,
                selector,
                tf,
                placebo,
                t,
            })
        })
        .reduce_with(|a, b| match (a, b) {
            (Ok(mut a), Ok(b)) => {
                for (x, y) in a.est.iter_mut().zip(b.est.iter()) {
                    x.absorb(y).map_err(|e| map_dim_err(0, e))?;
                }
                if let (Some(x), Some(y)) = (a.selector.as_mut(), b.selector.as_ref()) {
                    x.absorb(y);
                }
                if let (Some(x), Some(y)) = (a.tf.as_mut(), b.tf.as_ref()) {
                    x.absorb(y).map_err(|e| map_dim_err(0, e))?;
                }
                if let (Some(x), Some(y)) = (a.placebo.as_mut(), b.placebo.as_ref()) {
                    x.absorb(y).map_err(|e| map_dim_err(0, e))?;
                }
                a.t.add(b.t);
                Ok(a)
            }
            (Err(e), _) | (Ok(_), Err(e)) => Err(e),
        })
        .expect("at least one chunk")?;
    let pass2_secs = t2.elapsed().as_secs_f64();

    for e in &p2.est {
        ensure!(
            e.frames_folded() as usize == paths.len(),
            "pass two folded {} frames, expected {}",
            e.frames_folded(),
            paths.len()
        );
        ensure!(
            e.every_pixel_is_decided(),
            "some pixel admitted no frame at all; the winner is supposed to be unconditional"
        );
    }
    if let Some(selector) = &p2.selector {
        ensure!(
            selector.is_complete(),
            "the gate-zero selector reference did not capture every requested ROI pixel"
        );
    }

    eprintln!("--- pass two: gated average (MEASURED) ---");
    eprintln!(
        "wall clock      : {pass2_secs:.3} s  ({:.1} ms/frame, {} accumulators)",
        1000.0 * pass2_secs / n,
        opts.gates.len()
    );
    eprintln!(
        "  decode        : {:.3} s summed across workers ({:.1} ms/frame)",
        p2.t.decode,
        1000.0 * p2.t.decode / n
    );
    eprintln!(
        "  field + gate  : {:.3} s summed across workers ({:.1} ms/frame)",
        p2.t.work,
        1000.0 * p2.t.work / n
    );
    eprintln!(
        "total           : {:.3} s  (+{prologue_secs:.3} s prologue), {:.1} MB/s over {:.1} MB",
        pass1_secs + pass2_secs,
        input_bytes as f64 / 1e6 / (pass1_secs + pass2_secs),
        input_bytes as f64 / 1e6
    );
    eprintln!(
        "in-flight frames: {} peak, bound {} (never O(N))",
        peak_live.load(Ordering::Relaxed),
        plan.chunks
    );
    eprintln!();

    report(opts, &p2, &p1, geom, levels, &noise, middle)?;
    if opts.stats {
        report_statistics(opts, &p2, &p1.clip, geom, levels, &noise, &perm)?;
    }

    if let Some(path) = &opts.out {
        write_merged(&p2.est[0], levels, wb, opts.srgb, path)?;
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn report(
    opts: &MergeOptions,
    p2: &Pass2,
    p1: &Pass1,
    geom: PlaneGeometry,
    levels: Levels,
    noise: &NoiseModel,
    middle: u16,
) -> Result<()> {
    eprintln!("--- gate calibration (MEASURED) ---");
    eprintln!(
        "                  n_eff is frames averaged per pixel. Fact 212 measured nwide = 3 at full"
    );
    eprintln!(
        "                  sampling density -- frames within 50% of PEAK HEIGHT, which is a \
         different"
    );
    eprintln!(
        "                  rule from this NOISE gate, so 3 is a target to land near, not to match."
    );
    eprintln!(
        "  gate   tol(DN-norm)     mean n_eff   n_eff=1 %   boundary %   pred sigma gain (model)"
    );
    for e in &p2.est {
        let n_eff = e.n_eff();
        let px = n_eff.len();
        let alone = n_eff.iter().filter(|v| **v <= 1).count() as f64 / px as f64;
        let boundary = (0..px).filter(|i| e.at_bracket_boundary(*i)).count() as f64 / px as f64;
        let mean = e.mean_n_eff();
        eprintln!(
            "  {:5.2}  {:12.6}   {:10.3}   {:8.2}%   {:9.2}%   {:>12.4}x",
            e.gate().threshold,
            e.gate().tolerance(),
            mean,
            100.0 * alone,
            100.0 * boundary,
            e.mean_predicted_sigma_gain(noise, levels.black)
        );
    }
    eprintln!();
    report_target_solve(&p2.est, opts.target_n_eff);

    // The clip census and the photometric bound are correctness statements about
    // the stack, not diagnostics about an ROI, so they must not be gated behind
    // an ROI flag. Reported before the early return for exactly that reason.
    eprintln!();
    report_clip_census(&p1.clip);
    eprintln!();
    report_photometric_sensitivity(p1.stats.best_focus());
    eprintln!();

    let Some(roi) = opts.flat_roi else {
        eprintln!(
            "flat ROI        : not requested. Pass --flat-roi X,Y,W,H for the noise invariant."
        );
        return Ok(());
    };
    let single = p1
        .flat
        .as_ref()
        .context("the middle frame's flat ROI was never captured")?;

    eprintln!("--- ACCEPTANCE INVARIANT 1 of 2: flat-ROI noise (MEASURED) ---");
    eprintln!(
        "roi             : x {} y {} w {} h {} in plane coordinates",
        roi.x, roi.y, roi.width, roi.height
    );
    let (single_mean, single_sigma) = mean_and_sigma(single);
    let model_sigma = f64::from(noise.green_luma_sigma(single_mean as f32));
    eprintln!(
        "single frame {middle:<3}: raw sd {single_sigma:8.3} DN   mean {single_mean:9.2} DN   \
         (no stacking at all)"
    );
    eprintln!(
        "model predicts  : sigma {model_sigma:8.3} DN for one green-luma sample at that level, \
         so this"
    );
    eprintln!(
        "                  ROI's RAW sd is {:.2}x the noise in it -- that excess is scene, and \
         it is",
        single_sigma / model_sigma
    );
    eprintln!("                  why the raw ratio below is a LEGACY column and not the verdict.");

    // ---- the noise statistic ----------------------------------------------
    let per_frame: Vec<(u16, f64)> = p1
        .flat_frames
        .iter()
        .filter_map(|(i, f)| f.hp_sd.map(|v| (*i, v)))
        .collect();
    let reference = flat_ratio::FlatReference::new(&per_frame);
    match &reference {
        Some(reference) => {
            eprintln!();
            report_hp_reference(reference, model_sigma, "                  ");
            eprintln!(
                "  gate       hp sd DN     HP RATIO   over every frame     n frames   \
                 vs frame {middle} alone"
            );
            for e in &p2.est {
                let s = flat_roi_stats(e, single, roi, geom, levels.black);
                match s.stacked_hp_sd {
                    Some(hp) => {
                        let r = reference.ratio(hp);
                        // The last column is exactly the number the old
                        // convention would have printed: one privileged frame in
                        // the denominator. It is here so fact 441's spread is
                        // visible as a difference, not only as an interval.
                        let privileged = s
                            .single_hp_sd
                            .map(|d| format!("{:.3}x", hp / d))
                            .unwrap_or_else(|| "n/a".into());
                        eprintln!(
                            "  {:5.2}   {:10.3}   {:9.3}x   [{:6.3}x .. {:6.3}x]   {:>8}   \
                             {:>14}",
                            e.gate().threshold,
                            hp,
                            r.median,
                            r.lo,
                            r.hi,
                            reference.frames(),
                            privileged
                        );
                    }
                    None => eprintln!(
                        "  {:5.2}   ROI is smaller than one {}x{} high-pass box",
                        e.gate().threshold,
                        flat_ratio::HP_BOX_SIDE,
                        flat_ratio::HP_BOX_SIDE
                    ),
                }
            }
            eprintln!(
                "                  PASS is <= 1.000x against the SAME-OPERATOR baseline: \
                 regularised argmax."
            );
            eprintln!(
                "                  Fact 19's 1.253x was a DIFFERENT focus operator and does \
                 not reproduce"
            );
            eprintln!(
                "                  here; it is not this pipeline's baseline and must not be \
                 quoted as one."
            );
            eprintln!(
                "                  A plain unweighted mean measured 0.534x on the LEGACY \
                 statistic, which"
            );
            eprintln!(
                "                  is a floor and not a target, because of invariant 2. \
                 THE BASELINE FOR"
            );
            eprintln!(
                "                  THIS COLUMN HAS NOT BEEN RE-MEASURED: fact 343's 1.0739x is \
                 a RAW-sd"
            );
            eprintln!(
                "                  number and cannot be carried across to a high-pass sd. Run \
                 `strehl stack`"
            );
            eprintln!(
                "                  on the same frames and ROI for the same-operator argmax \
                 figure."
            );
        }
        None => {
            eprintln!();
            eprintln!(
                "HP RATIO        : NOT AVAILABLE -- no frame's flat ROI holds a whole {}x{} \
                 high-pass box.",
                flat_ratio::HP_BOX_SIDE,
                flat_ratio::HP_BOX_SIDE
            );
        }
    }

    // ---- the number this replaced, kept readable ---------------------------
    eprintln!();
    eprintln!("  gate    LEGACY raw sd    mean DN   LEGACY RATIO   winners in roi");
    for e in &p2.est {
        let s = flat_roi_stats(e, single, roi, geom, levels.black);
        eprintln!(
            "  {:5.2}   {:9.3}   {:11.2}   {:8.3}x   {} distinct, median {}",
            e.gate().threshold,
            s.stacked_sigma,
            s.stacked_mean,
            s.legacy_raw_ratio,
            s.distinct_winners,
            s.median_winner
        );
    }
    eprintln!(
        "                  DO NOT READ THE LEGACY COLUMN AS NOISE (facts 469/441/442/455, \
         597). It"
    );
    eprintln!("                  is a ratio of two RAW SPATIAL sds against ONE arbitrary frame.");
    eprintln!(
        "                  It is structure-dominated -- the corpus's flat reference frames are \
         50.9-80.0%"
    );
    eprintln!(
        "                  scene by variance and this ROI's own excess is printed above -- it \
         moves"
    );
    eprintln!(
        "                  over a 1.60x range with the free choice of denominator frame, and on \
         a"
    );
    eprintln!(
        "                  planted noise explosion it under-reported by 6.3x. It is printed \
         only so"
    );
    eprintln!("                  that reports written before this change stay comparable.");
    eprintln!();

    let Some(droi) = opts.detail_roi else {
        eprintln!(
            "detail ROI      : NOT REQUESTED. Invariant 1 ALONE IS NOT A RESULT -- a plain mean \
             wins it"
        );
        eprintln!(
            "                  at 0.534x while collapsing detail 58% (fact 24). Pass \
             --detail-roi X,Y,W,H."
        );
        return Ok(());
    };
    let selector = p2
        .selector
        .as_ref()
        .context("the gate-zero selector ROIs were not captured")?;
    let selector_flat_sigma: Vec<f32> = selector
        .flat
        .values
        .iter()
        .map(|v| noise.green_luma_sigma(*v))
        .collect();
    let selector_detail_sigma: Vec<f32> = selector
        .detail
        .values
        .iter()
        .map(|v| noise.green_luma_sigma(*v))
        .collect();
    let selector_controlled = cross_fitted_detail(
        &selector.detail.values,
        &selector_detail_sigma,
        droi.width,
        droi.height,
        &selector.flat.values,
        &selector_flat_sigma,
        roi.width,
        roi.height,
    )
    .context("building the gate-zero detail reference")?;
    let selector_metrics = detail_metrics(
        &selector.detail.values,
        &selector_detail_sigma,
        droi.width,
        droi.height,
    );

    eprintln!("--- ACCEPTANCE INVARIANT 2 of 2: detail retention (MEASURED) ---");
    eprintln!(
        "roi             : x {} y {} w {} h {} in plane coordinates",
        droi.x, droi.y, droi.width, droi.height
    );
    eprintln!(
        "                  THIS IS A ONE-SIDED TEST. It is valid against COLLAPSE and against"
    );
    eprintln!(
        "                  nothing else. mean|grad| can be RAISED by ringing, by amplified noise"
    );
    eprintln!(
        "                  and by manufactured edges, so an INCREASE is never evidence of quality."
    );
    eprintln!(
        "                  MEASURED in the orchestrator's calibrated 1-D optics simulation (25"
    );
    eprintln!(
        "                  frames, oracle depth, latent mean|grad| 0.0392): at sigma 0.010 a Wiener"
    );
    eprintln!(
        "                  merge reads 0.0367 against selection's 0.0296 -- 24% MORE gradient --"
    );
    eprintln!(
        "                  while its gradient CORRELATION with truth is 0.7538 against 0.8595, i.e."
    );
    eprintln!(
        "                  12% LESS faithful. At sigma 0.050 argmax reads 0.0455, ABOVE the ground"
    );
    eprintln!(
        "                  truth. A mean-gradient test scores both of those as wins. It must not."
    );
    eprintln!(
        "                  MEAN |GRAD| IS ALSO CONFOUNDED BY NOISE and selection conditions that"
    );
    eprintln!(
        "                  noise on a max over N. A model sigma knows neither the max nor N."
    );
    eprintln!(
        "                  Each row therefore MEASURES its inflation on the flat ROI, separately"
    );
    eprintln!(
        "                  in the left/right halves, and applies the OPPOSITE half's scale to detail."
    );
    eprintln!(
        "                  STRUCTURE = raw / controlled-noise: pure noise reads 1.0x; real detail"
    );
    eprintln!(
        "                  reads above it. RETENTION compares resolved signal at the SAME selector"
    );
    eprintln!(
        "                  noise floor, against the full-stack gate-zero selector -- never one"
    );
    eprintln!(
        "                  arbitrary frame. The flat scale is re-measured per gate, so its N and"
    );
    eprintln!(
        "                  admission dependence come from this run rather than a transferred bar."
    );
    eprintln!(
        "selector gate 0 : q {:+10.3} DN^2   STRUCTURE {:7.3}x   raw {:9.4}   \
         ctrl noise {:9.4}   k(L/R) {:6.3}/{:6.3}   m2 {:8.4}   iso {:8.4}",
        selector_controlled.signal_power,
        selector_controlled.structure,
        selector_controlled.raw_power.sqrt(),
        selector_controlled.controlled_noise_power.sqrt(),
        selector_controlled.inflation_left,
        selector_controlled.inflation_right,
        selector_metrics.m2_pooled_abs,
        selector_metrics.iso_mean
    );
    eprintln!(
        "  gate     q signal    RETENTION   VERDICT    STRUCTURE     raw rms  ctrl noise   \
         k left  k right         m2        iso"
    );
    for e in &p2.est {
        let merged_detail = roi_green_merged(e, droi, geom, levels.black);
        let detail_sig: Vec<f32> = (droi.y..droi.y + droi.height)
            .flat_map(|py| (droi.x..droi.x + droi.width).map(move |px| (px, py)))
            .map(|(px, py)| e.predicted_sigma(noise, geom.index(px, py), levels.black))
            .collect();
        let merged_flat = roi_green_merged(e, roi, geom, levels.black);
        let flat_sig: Vec<f32> = (roi.y..roi.y + roi.height)
            .flat_map(|py| (roi.x..roi.x + roi.width).map(move |px| (px, py)))
            .map(|(px, py)| e.predicted_sigma(noise, geom.index(px, py), levels.black))
            .collect();
        let controlled = cross_fitted_detail(
            &merged_detail,
            &detail_sig,
            droi.width,
            droi.height,
            &merged_flat,
            &flat_sig,
            roi.width,
            roi.height,
        )
        .with_context(|| format!("gate {} detail control", e.gate().threshold))?;
        let m = detail_metrics(&merged_detail, &detail_sig, droi.width, droi.height);
        let retention = equal_noise_retention(controlled, selector_controlled);
        eprintln!(
            "  {:5.2}   {:+10.3}   {:9.3}x   {:9}   {:9.3}x   {:9.4}   {:9.4}   \
             {:7.3}  {:7.3}   {:8.4}   {:8.4}",
            e.gate().threshold,
            controlled.signal_power,
            retention,
            detail_verdict(retention),
            controlled.structure,
            controlled.raw_power.sqrt(),
            controlled.controlled_noise_power.sqrt(),
            controlled.inflation_left,
            controlled.inflation_right,
            m.m2_pooled_abs,
            m.iso_mean
        );
    }
    eprintln!(
        "                  q is SIGNED resolved gradient power. A negative q means the ROI has no"
    );
    eprintln!(
        "                  resolved detail above the cross-fitted flat control; it is not clamped"
    );
    eprintln!(
        "                  before retention. At high STRUCTURE, RETENTION approaches resolved"
    );
    eprintln!(
        "                  signal amplitude. Near 1.0x it honestly shrinks toward no-effect."
    );
    eprintln!(
        "                  A rise is INVESTIGATE, not PASS: see the speckle companion below, which"
    );
    eprintln!("                  is two-sided and shares a cause with manufactured detail.");
    eprintln!();

    // The two-sided companion. mean|grad| cannot tell manufactured detail from
    // real detail; a winner-index map can, because ringing and amplified noise
    // both decorrelate the winner from its neighbours and speckle is exactly
    // that decorrelation. This is the SAME `speckle_fraction` the argmax
    // baseline is quoted against (`strehl stack`), on the merge's own
    // regularised winner, so the two numbers are directly comparable.
    let speckle = speckle_fraction(p1.stats.best_index(), geom, SPECKLE_TOLERANCE);
    eprintln!("--- COMPANION (two-sided): winner-index speckle (MEASURED) ---");
    eprintln!(
        "index speckle   : {:.3}% of pixels differ by more than {SPECKLE_TOLERANCE} from their \
         3x3 median index",
        100.0 * speckle
    );
    eprintln!(
        "                  On the REGULARISED winner, the same statistic and tolerance `strehl \
         stack`"
    );
    eprintln!(
        "                  reports for argmax. Unlike mean|grad| this is two-sided: a real scene \
         gives"
    );
    eprintln!(
        "                  smooth depth with sharp edges, and BOTH over-smoothing and \
         manufactured"
    );
    eprintln!("                  detail move it away from that.");
    eprintln!(
        "                  Fact 23's 34.4% -> 0.868% pair is BOTH the retired ring operator, \
         unregularised"
    );
    eprintln!(
        "                  then 17x17-regularised (M2-verification section 4; :205 states the \
         measure"
    );
    eprintln!(
        "                  was the ring difference, and Tenengrad did not exist until M14). \
         NEITHER is a"
    );
    eprintln!(
        "                  Tenengrad number, and no section-4 row publishes a \
         regularised-Tenengrad"
    );
    eprintln!(
        "                  speckle at all, so there is no cross-operator reference to quote \
         here. The"
    );
    eprintln!(
        "                  operator-matched figure is fact 71's 1.010% for UNREGULARISED \
         Tenengrad on"
    );
    eprintln!(
        "                  this ROI; the regularised comparable is this run's own value, above."
    );
    Ok(())
}

/// Samples pinned at the raw container maximum, and what they do to confidence.
///
/// Always reported, not hidden behind `--stats`, because a clipped pixel is a
/// correctness question rather than a diagnostic one. On a clean stack this
/// costs one comparison per sample and prints zeros — M26 measured that four of
/// six stacks in this corpus have no saturated pixels at all.
fn report_clip_census(clip: &ClipCensus) {
    let ever = clip.ever_clipped_fraction();
    let always = clip.always_clipped_fraction();
    let total = clip.geometry().pixels();
    eprintln!("--- CLIPPING CENSUS (MEASURED) ---");
    eprintln!(
        "container max   : {CONTAINER_MAX_DN} DN. NOT the usable white level (15360) -- these are"
    );
    eprintln!(
        "                  two different numbers for two different purposes and both are right:"
    );
    eprintln!("                  15360 bounds the noise model's calibrated range, 16383 is what");
    eprintln!("                  \"this sample is pinned\" means. Do not unify them.");
    eprintln!(
        "ever clipped    : {:.4}% of pixels ({} of {}) clipped in at least one frame",
        100.0 * ever,
        (ever * total as f64).round() as u64,
        total
    );
    eprintln!(
        "always clipped  : {:.4}% of pixels ({} of {}) pinned in EVERY frame",
        100.0 * always,
        (always * total as f64).round() as u64,
        total
    );
    if always > 0.0 {
        eprintln!(
            "                  ^ these carry ZERO focus information. M26 measured 616 such px on"
        );
        eprintln!(
            "                  coffee-bubbles reading cross-frame focus contrast 1.0000, the"
        );
        eprintln!(
            "                  metric's MAXIMUM, against 0.5398 median on never-clipped px --"
        );
        eprintln!(
            "                  because 85.9% of them have f_min exactly 0 (inside a uniformly"
        );
        eprintln!(
            "                  clipped blob the gradient is identically zero) while f_max is 52x"
        );
        eprintln!(
            "                  typical (the blob edge crosses them in another frame). Discipline"
        );
        eprintln!("                  29 does NOT protect against this: it preferred cross-frame");
        eprintln!("                  contrast to focus magnitude, but on a pinned pixel BOTH read");
        eprintln!("                  their maximum, so they fail in the same direction.");
    } else {
        eprintln!(
            "                  No pixel is pinned in every frame, so the maximum-severity case"
        );
        eprintln!("                  M26 measured on coffee-bubbles does not arise on this stack.");
    }
    eprintln!("                  NOTE 109MSDCF and 119MSDCF are two of the four stacks with NO");
    eprintln!("                  saturation, and 109 is also the quietest photometrically (M24).");
    eprintln!("                  A clean result on them is systematically weaker evidence than it");
    eprintln!("                  looks.");
}

/// How far a per-frame photometric gain drift moves the gate, in gate units.
///
/// # Why this exists, and what it does NOT do
///
/// There is **no per-frame gain term in this merge** (see the module note on
/// `Estimator`). M24 measured that this corpus really does drift: 0.91% peak to
/// peak on `109MSDCF`, 2.88% on `119MSDCF`, and **11.70% on `coffee-bean`**. So
/// the omission has a price, and this prints it rather than leaving it implicit.
///
/// # The conversion, and its one assumption
///
/// The focus response is `box_mean(|grad L|) / sigma(L)`, so scaling a frame's
/// signal by `g` scales the numerator by exactly `g`. In the shot-noise-limited
/// regime `sigma ~ sqrt(S)`, so the denominator scales by `sqrt(g)` and the
/// normalised response scales by **`sqrt(g)`**. A fractional level drift `d`
/// therefore moves the response by `d/2` of itself. That is DERIVED, and it is
/// an UPPER BOUND on the read-noise-dominated end, where sigma is flat in signal
/// and the response scales by the full `g` instead — in deep shadow the
/// sensitivity is twice what is printed here.
///
/// Expressed in gate units, because that is the only scale on which "does this
/// matter" has an answer: one gate unit is `sqrt(2) * FOCUS_NOISE_SD`, the SD of
/// a *difference* of two regularised responses.
fn report_photometric_sensitivity(best_focus: &[f32]) {
    let mut f: Vec<f32> = best_focus
        .iter()
        .copied()
        .filter(|v| v.is_finite())
        .collect();
    if f.is_empty() {
        return;
    }
    f.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let q = |p: f64| -> f64 { f[((p * (f.len() - 1) as f64) as usize).min(f.len() - 1)] as f64 };
    let (med, p10, p90) = (q(0.5), q(0.10), q(0.90));
    let unit = (2.0f64).sqrt() * strehl_core::merge::FOCUS_NOISE_SD as f64;
    // Gate units moved per 1% of level drift: (d/2) * F / unit, with d = 0.01.
    let per_pct = |focus: f64| 0.5 * 0.01 * focus / unit;
    eprintln!("--- PHOTOMETRIC DRIFT SENSITIVITY (DERIVED from a MEASURED response) ---");
    eprintln!(
        "winner response : median {med:.4}, p10 {p10:.4}, p90 {p90:.4}  (regularised, \
         DN-normalised)"
    );
    eprintln!("gate unit       : {unit:.6}  = sqrt(2) * FOCUS_NOISE_SD, the SD of a difference");
    eprintln!(
        "sensitivity     : {:.3} gate units per 1% of per-frame level drift (median pixel),",
        per_pct(med)
    );
    eprintln!(
        "                  {:.3} at p10 and {:.3} at p90. Shot-limited; in read-noise-",
        per_pct(p10),
        per_pct(p90)
    );
    eprintln!("                  dominated shadow it is 2x this.");
    eprintln!(
        "corpus (M24)    : 109MSDCF drifts 0.91% -> {:.2} gate units. 119MSDCF 2.88% -> {:.2}.",
        per_pct(med) * 0.91,
        per_pct(med) * 2.88
    );
    eprintln!(
        "                  coffee-bean 11.70% -> {:.2}. coffee-bubbles 8.93% -> {:.2}.",
        per_pct(med) * 11.70,
        per_pct(med) * 8.93
    );
    eprintln!("                  109MSDCF is the QUIETEST stack in the corpus and is the one most");
    eprintln!(
        "                  of this project's numbers were measured on, so a clean 109 result"
    );
    eprintln!("                  is NOT evidence that photometric variation is handled.");
    eprintln!("STATUS          : NO per-frame gain term is fitted or applied. This merge assumes");
    eprintln!(
        "                  constant photometry across the stack. The number above is the size"
    );
    eprintln!(
        "                  of that assumption, not a correction for it. Do NOT read gain from"
    );
    eprintln!("                  EXIF to fix it: M24 measured two stacks drifting 6.84% and 8.93%");
    eprintln!("                  with CONSTANT EXIF, and coffee-bean moving only 16% of what its");
    eprintln!("                  EXIF change predicts (1.0443 measured vs 1.2800). Fit it.");
}

/// One-sided reading of an equal-noise retention ratio.
///
/// **Deliberately never returns "PASS" for a value above 1.** The orchestrator
/// MEASURED (calibrated 1-D optics simulation, 25 frames, oracle depth, 2026-08)
/// that a Wiener merge can carry **24% more** mean|grad| than selection while
/// having **12% less** gradient correlation with the truth, and that at sigma
/// 0.050 argmax selection reads mean|grad| *above the ground truth's*. Every one
/// of those is a merge inventing detail, and every one of them would be scored a
/// win by a two-sided reading of this number.
///
/// This merge is a regulariser plus a noise gate, not a deconvolution, so it is
/// not itself at risk of manufacturing detail. The verdict exists so the TEST
/// cannot be gamed by a later merge that is.
fn detail_verdict(retention: f64) -> &'static str {
    if retention < DETAIL_COLLAPSE_FLOOR {
        "COLLAPSE"
    } else if retention > DETAIL_RISE_FLAG {
        "INVESTIG."
    } else {
        "ok"
    }
}

/// Equal-noise retention below this is fact 24's collapse.
///
/// The reference is now the full-stack gate-zero selector, with candidate and
/// reference compared at the same measured noise floor. At high structure,
/// 0.90 therefore means a 10% resolved-gradient amplitude loss instead of a
/// ratio to an arbitrarily defocused middle frame. The value is deliberately
/// not tuned here: it still sits well above fact 24's measured 53-58% collapse
/// and the simulated plain mean's 49-51%, but whether 10% is the right product
/// tolerance is a separate decision.
const DETAIL_COLLAPSE_FLOOR: f64 = 0.90;

/// Equal-noise retention above this is a flag to investigate, never a pass.
///
/// The selector reference has already searched the full bracket for focus. A
/// merge carrying 50% more resolved gradient than that reference is therefore
/// a reason to inspect ringing or manufactured texture, never evidence of
/// quality from this one-sided statistic.
const DETAIL_RISE_FLAG: f64 = 1.50;

// Pinned at compile time rather than in a test, because these are relationships
// between constants and a build that violates one should not link.
//
// The rise flag sits above identity so small measurement scatter is not itself
// labelled as manufactured detail.
const _: () = assert!(DETAIL_RISE_FLAG > 1.0);
// The collapse floor must sit above the -49% a plain mean produces in the
// orchestrator's simulation and the -58%/-53% fact 24 measured, or it cannot
// catch the failure it exists for.
const _: () = assert!(DETAIL_COLLAPSE_FLOOR > 0.51);
// And the band must be non-empty, or every reading is a verdict.
const _: () = assert!(DETAIL_COLLAPSE_FLOOR < DETAIL_RISE_FLAG);

/// Report the through-focus sufficient statistics, with their null.
///
/// Every channel here is reported next to the placebo that says what it would
/// read on the same frames with the focus ordering destroyed. That is the only
/// way any of these numbers means anything: the bimodality screen in particular
/// is a max-minus-min and is **large by construction** even on pure noise.
fn report_statistics(
    opts: &MergeOptions,
    p2: &Pass2,
    clip: &ClipCensus,
    geom: PlaneGeometry,
    levels: Levels,
    noise: &NoiseModel,
    perm: &[u16],
) -> Result<()> {
    let Some(tf) = p2.tf.as_ref() else {
        return Ok(());
    };
    let px = geom.pixels();
    let frames = tf.frames_folded() as usize;

    eprintln!();
    eprintln!("--- through-focus sufficient statistics (MEASURED) ---");
    eprintln!(
        "                  Gathered in PASS TWO, anchored on pass one's regularised winner, so"
    );
    eprintln!(
        "                  no third pass over the frames is needed to compute a sub-frame peak,"
    );
    eprintln!("                  a top-k list or a bimodality statistic from them.");
    eprintln!(
        "scale           : {}x{} box on the focus field (fact 152: bimodality is DEPLETED, 0.36x,",
        2 * STATS_RADIUS + 1,
        2 * STATS_RADIUS + 1
    );
    eprintln!(
        "                  at the {REGULARISER_WIDTH}x{REGULARISER_WIDTH} selection scale and only \
         appears at radius {STATS_RADIUS})"
    );
    eprintln!(
        "fine noise sd   : {FINE_FOCUS_NOISE_SD:.6}, MEASURED in-crate. The selection field's is \
         {FOCUS_NOISE_SD:.6},"
    );
    eprintln!(
        "                  but THESE TWO DO NOT DIVIDE. The fine sd is measured with NO \
         regulariser and"
    );
    eprintln!(
        "                  the selection sd with the \
         {REGULARISER_WIDTH}x{REGULARISER_WIDTH} box, so their ratio mixes a window-radius"
    );
    eprintln!(
        "                  change with the presence of a regulariser. Put both at the same \
         regularisation"
    );
    eprintln!(
        "                  and let only the operator window differ and k = 1.815 (fact 500, \
         verified"
    );
    eprintln!(
        "                  independently by M52 at 1.8145). The printed pair's ratio is 5.94 and \
         is NOT"
    );
    eprintln!(
        "                  a k: it overstates the seam by 3.27x. Both constants are correct as \
         consumed."
    );
    eprintln!(
        "memory          : {} B/px = {:.0} MB per gather, CONSTANT in the frame count.",
        ThroughFocus::bytes_per_pixel(),
        tf.allocated_bytes() as f64 / 1e6
    );
    eprintln!(
        "                  A fine focus VOLUME for these {frames} frames would be {} B/px = \
         {:.0} MB and is O(frames).",
        4 * frames,
        (px * 4 * frames) as f64 / 1e6
    );
    eprintln!(
        "                  Break-even is {} frames; the ratchet holds from there up without bound.",
        ThroughFocus::bytes_per_pixel().div_ceil(4)
    );
    eprintln!();

    // (a) sub-frame peak
    let offsets: Vec<f32> = (0..px).filter_map(|i| tf.subframe_offset(i)).collect();
    let deficits: Vec<f32> = (0..px).filter_map(|i| tf.subframe_deficit(i)).collect();
    eprintln!("(a) SUB-FRAME PEAK, by parabola on the fine triple");
    eprintln!(
        "  fitted        : {:.3}% of pixels have a complete concave triple",
        100.0 * offsets.len() as f64 / px as f64
    );
    if !offsets.is_empty() {
        let mean_abs = offsets.iter().map(|v| v.abs() as f64).sum::<f64>() / offsets.len() as f64;
        let near_half = offsets.iter().filter(|v| v.abs() > 0.4).count() as f64;
        eprintln!("  mean |offset| : {mean_abs:.4} frames");
        eprintln!(
            "  |offset|>0.4  : {:.3}% of fitted pixels are nearly half a frame from their peak",
            100.0 * near_half / offsets.len() as f64
        );
    }
    if !deficits.is_empty() {
        let mut d = deficits.clone();
        d.sort_by(|a, b| a.partial_cmp(b).unwrap());
        eprintln!(
            "  deficit (C3)  : median {:.4}, p90 {:.4}, p99 {:.4}   (log fit with baseline \
             subtraction, facts 272/304)",
            d[d.len() / 2],
            d[d.len() * 9 / 10],
            d[d.len() * 99 / 100]
        );
    }
    let disagree = (0..px).filter(|i| !tf.anchor_is_fine_argmax(*i)).count();
    let outside = (0..px).filter(|i| tf.fine_peak_outside_triple(*i)).count();
    eprintln!(
        "  scale disagree: {:.3}% of pixels have a fine argmax different from the regularised \
         winner",
        100.0 * disagree as f64 / px as f64
    );
    eprintln!(
        "  outside triple: {:.3}% have it further than {PEAK_SEPARATION} frames away -- the \
         SCREENING form",
        100.0 * outside as f64 / px as f64
    );
    eprintln!(
        "                  The first is a diagnostic and is expected to be large. The fine field \
         differs"
    );
    eprintln!(
        "                  from the selection field in TWO ways -- a smaller operator window AND \
         no"
    );
    eprintln!(
        "                  regulariser -- so its argmax moves for both reasons. At matched \
         regularisation"
    );
    eprintln!(
        "                  it is noisier by k = 1.815 (fact 500), not the 5.94 the ratio of the \
         two"
    );
    eprintln!(
        "                  published constants suggests. The second is the actionable one, \
         because"
    );
    eprintln!("                  off-by-one is still bracketed by the parabola.");
    eprintln!();

    // (b) top-k
    let full = (0..px)
        .filter(|i| tf.top_indices(*i).iter().all(|k| *k != u16::MAX))
        .count();
    let spread: Vec<f32> = (0..px)
        .map(|i| {
            let t = tf.top_values(i);
            t[0] - t[TOP_K_LAST]
        })
        .filter(|v| v.is_finite())
        .collect();
    eprintln!("(b) TOP-K, k = 4 on the fine field");
    eprintln!(
        "  complete      : {:.3}% of pixels have all four slots filled",
        100.0 * full as f64 / px as f64
    );
    if !spread.is_empty() {
        let mean = spread.iter().map(|v| *v as f64).sum::<f64>() / spread.len() as f64;
        eprintln!(
            "  top1 - top4   : mean {mean:.4} = {:.2} fine sigma",
            mean / (std::f64::consts::SQRT_2 * FINE_FOCUS_NOISE_SD as f64)
        );
    }
    eprintln!();

    // (c) bimodality, against the placebo
    let bimodal: Vec<f32> = (0..px).filter_map(|i| tf.bimodality_sigma(i)).collect();
    eprintln!("(c) BIMODALITY -- an UPPER BOUND on the prominence of a separated second peak");
    // Sort ONCE. An earlier draft passed an unsorted slice to a closure that
    // sorted a copy per call, and one of those calls was inside a per-pixel
    // loop: 8.2 million sorts of an 8.2 million element vector. It did not
    // finish. Sorting up front is the whole fix.
    let mut bimodal_sorted = bimodal.clone();
    bimodal_sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let quant = |s: &[f32], q: f64| -> f32 {
        if s.is_empty() {
            return 0.0;
        }
        s[((q * (s.len() - 1) as f64) as usize).min(s.len() - 1)]
    };
    let real_mean = if bimodal.is_empty() {
        0.0
    } else {
        bimodal.iter().map(|v| *v as f64).sum::<f64>() / bimodal.len() as f64
    };
    eprintln!(
        "  real          : mean {real_mean:.3} sigma, median {:.3}, p99 {:.3}",
        quant(&bimodal_sorted, 0.5),
        quant(&bimodal_sorted, 0.99)
    );
    // Set by the placebo arm below when there is one to set it from.
    let mut bimodal_cut = if bimodal_sorted.is_empty() {
        f32::INFINITY
    } else {
        quant(&bimodal_sorted, 0.99)
    };
    let mut cut_is_circular = true;
    match p2.placebo.as_ref() {
        Some(pl) => {
            let mut fake: Vec<f32> = (0..px).filter_map(|i| pl.bimodality_sigma(i)).collect();
            let fake_mean = if fake.is_empty() {
                0.0
            } else {
                fake.iter().map(|v| *v as f64).sum::<f64>() / fake.len() as f64
            };
            fake.sort_by(|a, b| a.partial_cmp(b).unwrap());
            eprintln!(
                "  placebo       : mean {fake_mean:.3} sigma, median {:.3}, p99 {:.3}   \
                 (seeded shuffle, mean step {:.1} frames, NOT a rotation)",
                quant(&fake, 0.5),
                quant(&fake, 0.99),
                if perm.len() > 1 {
                    (0..perm.len() - 1)
                        .map(|k| perm[k].abs_diff(perm[k + 1]) as f64)
                        .sum::<f64>()
                        / (perm.len() - 1) as f64
                } else {
                    0.0
                }
            );
            eprintln!(
                "  ratio         : {:.4}x  -- BELOW 1 means the through-focus curve is genuinely",
                real_mean / fake_mean
            );
            eprintln!(
                "                  focus-ordered at this scale; AT 1 means the stack carries no"
            );
            eprintln!(
                "                  ordering information here and the screen is reading noise."
            );
            eprintln!(
                "                  The placebo reads HIGH by construction (M21: permutation is a"
            );
            eprintln!("                  null for ENRICHMENT, never for a raw rate).");
            eprintln!(
                "                  THIS RATIO IS NOT AN OCCLUSION TEST AND A READING BELOW 1 IS"
            );
            eprintln!("                  NOT EVIDENCE OF NO OCCLUSION. Occlusion enrichment is a");
            eprintln!(
                "                  CONDITIONAL quantity -- the multi-peak rate at depth steps"
            );
            eprintln!(
                "                  against the rate on smooth depth, binned on an INDEPENDENT"
            );
            eprintln!(
                "                  depth-step map. This is a GLOBAL ratio and it is saturated by"
            );
            eprintln!(
                "                  the fact that permutation manufactures multi-peakedness, so it"
            );
            eprintln!(
                "                  cannot see the effect at all. M21 measures 4.38x on coffee-bean"
            );
            eprintln!(
                "                  conditioned properly, against a null of 1.01x, where this"
            );
            eprintln!(
                "                  global ratio reads 0.86x. Both are correct; only one is an"
            );
            eprintln!(
                "                  answer to the occlusion question. The per-pixel statistic"
            );
            eprintln!(
                "                  supports the conditional test; this summary line does not."
            );
            // The cut for the C4 bimodality flag. Taken from the PLACEBO's p99,
            // never from the real distribution's own p99: the latter flags
            // exactly 1% of pixels by construction and reports the definition
            // of the quantile back as if it were a measurement. An earlier draft
            // did that and printed 82417 px -- 1.0000% -- on both stacks.
            //
            // Against the null's p99, the flagged fraction is a real number: a
            // reading BELOW 1% means the real curve has FEWER prominent far
            // peaks than chance, which is what a focus-ordered stack should do.
            bimodal_cut = quant(&fake, 0.99);
            cut_is_circular = false;
        }
        None => eprintln!(
            "  placebo       : NOT MEASURED. Pass --stats-placebo. Without it the number above \
             is uninterpretable."
        ),
    }
    eprintln!();

    // Confidence vector.
    let est = &p2.est[0];
    let vectors: Vec<ConfidenceVector> = (0..px)
        .map(|i| {
            tf.confidence(
                est.n_eff()[i],
                est.green_mean(i) - levels.black,
                noise,
                i,
                bimodal_cut,
            )
        })
        .collect();
    let (mask, b) = do_not_trust_mask(&vectors, opts.confidence_tail);
    let clip_union = (0..px.min(vectors.len()))
        .filter(|&i| mask[i] || clip.always_clipped(i))
        .count();
    let clip_only = (0..px.min(vectors.len()))
        .filter(|&i| !mask[i] && clip.always_clipped(i))
        .count();
    eprintln!(
        "(d) CONFIDENCE VECTOR at gate {:.2} -- four channels, NOT a score",
        est.gate().threshold
    );
    eprintln!(
        "                  Facts 280-282: C1 is ANTI-correlated with C3's target (0.89x lift), so"
    );
    eprintln!(
        "                  no monotone scalar summary is faithful. The honest answer is the UNION."
    );
    eprintln!(
        "  C1 sigma      : worst {:.1}% at >= {:.3} DN -> {} px",
        100.0 * opts.confidence_tail,
        b.sigma_cut,
        b.by_sigma
    );
    eprintln!(
        "  C2 perplexity : worst {:.1}% at >= {:.3} -> {} px",
        100.0 * opts.confidence_tail,
        b.perplexity_cut,
        b.by_perplexity
    );
    eprintln!(
        "  C3 deficit    : worst {:.1}% at >= {:.4} -> {} px",
        100.0 * opts.confidence_tail,
        b.deficit_cut,
        b.by_deficit
    );
    let flag_count = |f: u8| vectors.iter().filter(|v| v.has(f)).count();
    eprintln!(
        "  C4 flags      : {} px  (boundary {}, bimodal {}, peak outside triple {})",
        b.by_flags,
        flag_count(FLAG_BRACKET_BOUNDARY),
        flag_count(FLAG_BIMODAL),
        flag_count(FLAG_SCALE_DISAGREEMENT)
    );
    eprintln!(
        "                  bimodal cut {bimodal_cut:.3} sigma, from the {}. {:.4}% of pixels \
         clear it;",
        if cut_is_circular {
            "REAL distribution's own p99 -- CIRCULAR, it flags 1% by definition"
        } else {
            "PLACEBO's p99"
        },
        100.0 * flag_count(FLAG_BIMODAL) as f64 / px as f64
    );
    eprintln!(
        "                  1% is the no-effect reading, below 1% means FEWER prominent far peaks"
    );
    eprintln!("                  than chance -- which is what a focus-ordered stack should give.");
    eprintln!(
        "  UNION         : {:.3}% of pixels ({} of {})   -- M34 measured 14.278% at a 5% tail",
        100.0 * b.union as f64 / b.total as f64,
        b.union,
        b.total
    );
    let always_n = (0..px.min(vectors.len()))
        .filter(|&i| clip.always_clipped(i))
        .count();
    eprintln!(
        "  C5 clipped    : {always_n} px pinned in EVERY frame carry no focus information at all."
    );
    eprintln!(
        "                  {clip_only} of them are NOT caught by C1-C4, because a pinned pixel"
    );
    eprintln!(
        "                  reads the confidence metric's MAXIMUM rather than its minimum (M26)."
    );
    eprintln!(
        "  UNION + C5    : {:.3}% of pixels ({} of {})   -- the mask a consumer should use",
        100.0 * clip_union as f64 / b.total as f64,
        clip_union,
        b.total
    );
    // The scale-disagreement channel is new here, so report the union without it
    // too. Comparing a four-channel union against M34's three-channel one and
    // calling the difference a finding would be a reporting defect.
    let m34_like: Vec<ConfidenceVector> = vectors
        .iter()
        .map(|v| {
            let mut c = *v;
            c.flags &= !FLAG_SCALE_DISAGREEMENT;
            c
        })
        .collect();
    let (_, b3) = do_not_trust_mask(&m34_like, opts.confidence_tail);
    eprintln!(
        "  UNION w/o C4' : {:.3}% ({} px) with the NEW scale-disagreement flag removed -- this is",
        100.0 * b3.union as f64 / b3.total as f64,
        b3.union
    );
    eprintln!(
        "                  the channel set M34's 14.278% was measured over, and the only one \
         comparable."
    );
    let mean_pp = (0..px)
        .map(|i| tf.posterior_perplexity(i) as f64)
        .sum::<f64>()
        / px as f64;
    eprintln!(
        "  mean C2       : {mean_pp:.4} against mean n_eff {:.4} at this gate -- the soft and hard",
        est.mean_n_eff()
    );
    eprintln!(
        "                  readings of the same acceptance set, on the same calibrated scale."
    );
    Ok(())
}

/// Index of the last top-k slot. Named so the report cannot silently drift from
/// `strehl_core::through_focus::TOP_K`.
const TOP_K_LAST: usize = strehl_core::through_focus::TOP_K - 1;

/// Seed for the placebo frame permutation. Fixed so a placebo reading is
/// reproducible from the command line alone.
const PLACEBO_SEED: u64 = 0x4D31_385E;

fn write_merged(
    est: &Estimator,
    levels: Levels,
    wb: Option<[f32; 3]>,
    srgb: bool,
    path: &Path,
) -> Result<()> {
    let geom = est.geometry();
    let n = geom.pixels();
    let range = levels.range();
    ensure!(range > 0.0, "white level is not above black level");
    let gains = wb.unwrap_or([1.0, 1.0, 1.0]);

    let encode = |raw: f32, gain: f32| -> u16 {
        let v = ((raw - levels.black).max(0.0) * gain / range).min(1.0);
        let v = if srgb { srgb_encode(v) } else { v };
        (v * u16::MAX as f32 + 0.5) as u16
    };

    let mut rgb = vec![0u16; n * 3];
    let (pixels, _) = rgb.as_chunks_mut::<3>();
    for (i, px) in pixels.iter_mut().enumerate() {
        px[0] = encode(est.value(CfaPlane::R, i), gains[0]);
        px[1] = encode(est.green_mean(i), gains[1]);
        px[2] = encode(est.value(CfaPlane::B, i), gains[2]);
    }
    image_out::write_rgb16(path, geom.width as u32, geom.height as u32, &rgb)?;
    eprintln!();
    eprintln!(
        "wrote           : {} ({} x {}, 16-bit RGB, {}, binned from one 2x2 quad per pixel)",
        path.display(),
        geom.width,
        geom.height,
        if srgb { "sRGB transfer" } else { "linear" }
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Ladder **shapes** for exercising the solver, generated rather than
    /// measured, and that is deliberate.
    ///
    /// Every property the solver has — a rung round-trips to its own gate, a
    /// solved gate inverts back to its target, a target outside the ladder is
    /// refused — holds for **any** monotone ladder. Asserting them against
    /// generated ladders therefore tests strictly *more* than asserting them
    /// against five frozen measurements, and cannot go stale when the pipeline
    /// is recalibrated. The generated family spans `n_eff(2.0)` from 1.07 to
    /// 23.6, which brackets the real corpus's measured 1.177 to 14.386.
    fn generated_ladders() -> Vec<(String, [(f64, f64); 4])> {
        let mut out = Vec::new();
        for p in [0.5_f64, 1.0, 1.5, 2.0, 2.5] {
            for a in [0.1_f64, 0.5, 1.5, 4.0] {
                let rung = |g: f64| (g, 1.0 + a * g.powf(p));
                out.push((
                    format!("a={a} p={p}"),
                    [rung(0.5), rung(1.0), rung(2.0), rung(4.0)],
                ));
            }
        }
        out
    }

    /// The one real ladder still defensible as current, kept so the solver sees
    /// a measured shape and not only analytic ones.
    ///
    /// `109MSDCF` is ISO 160, which puts it outside **both** of the day's
    /// calibration changes: `2a4f5c5` moved only ISO 50, and `f95f6f4` moved
    /// only ISO >= 400. M52 re-measured its gate-2.0 rung against the current
    /// pipeline and got 2.891 against fact 324's 2.891 — the only one of the
    /// five that reproduced exactly. The other four rungs are M38's and are not
    /// independently re-confirmed, so nothing below asserts their values.
    const LADDER_109MSDCF: [(f64, f64); 4] =
        [(0.5, 1.414), (1.0, 1.884), (2.0, 2.891), (4.0, 4.987)];

    /// M52's solved gates for `n_eff = 3`, all seven stacks, measured against
    /// the current pipeline and cross-checked by an independent Python merge
    /// agreeing with the shipped binary to <= 0.09%.
    /// `docs/research/M52-gate-cluster-verified.md` section 4.3, commit `f094c37`.
    ///
    /// **This is a dated snapshot and it will be wrong again.** It was wrong
    /// within one day twice already: `2a4f5c5` (09:41) moved the ISO-50 stacks
    /// and `f95f6f4` (11:17) moved every ISO >= 400 stack. What is asserted
    /// against it below is deliberately **one-sided**, so that the next
    /// calibration change makes these assertions *more* true rather than
    /// quietly false. See `no_single_gate_calibrates_across_the_corpus`.
    const SOLVED_GATES_M52: [(&str, f64); 7] = [
        ("coffee-bean", 0.7618),
        ("112MSDCF", 1.1323),
        ("113MSDCF", 1.3231),
        ("109MSDCF", 2.0964),
        ("119MSDCF", 2.1485),
        ("coffee-bubbles", 3.2144),
        ("foam", 21.9934),
    ];

    fn gate_of(s: Solve) -> f64 {
        match s {
            Solve::Gate(g) => g,
            other => panic!("expected a solved gate, got {other:?}"),
        }
    }

    #[test]
    fn log_log_interpolation_is_exact_on_a_power_law() {
        // n = g^2. The gate for n = 2 is sqrt(2), exactly, and log-log
        // recovers it because a power law is a straight line in log-log.
        // This is the whole reason the solve is not linear: linear
        // interpolation on the same rungs returns 1.3333, which is n = 1.78 —
        // 11% short of the target, biased the same way on every stack.
        let g = gate_of(solve_gate_for_n_eff(
            &[(1.0, 1.0), (2.0, 4.0), (4.0, 16.0)],
            2.0,
        ));
        assert!(
            (g - std::f64::consts::SQRT_2).abs() < 1e-12,
            "log-log gave {g}"
        );

        let linear = 1.0 + (2.0 - 1.0) / (4.0 - 1.0) * (2.0 - 1.0);
        assert!(
            (linear * linear - 2.0f64).abs() > 0.2,
            "linear interpolation must be visibly wrong here, or this test proves nothing"
        );
    }

    #[test]
    fn solving_at_a_rungs_own_value_returns_that_rungs_gate() {
        for (name, l) in generated_ladders() {
            for (gate, n) in l {
                let g = gate_of(solve_gate_for_n_eff(&l, n));
                assert!(
                    (g - gate).abs() < 1e-9,
                    "{name}: rung {gate} round-tripped to {g}"
                );
            }
        }
        for (gate, n) in LADDER_109MSDCF {
            let g = gate_of(solve_gate_for_n_eff(&LADDER_109MSDCF, n));
            assert!(
                (g - gate).abs() < 1e-9,
                "109MSDCF: rung {gate} round-tripped to {g}"
            );
        }
    }

    #[test]
    fn a_solved_gate_reproduces_its_target_when_fed_back() {
        // Interpolation is only honest if it inverts the ladder it came from.
        // Rebuild n_eff at the solved gate by interpolating the ladder the
        // other way, and require the target back. True of any monotone ladder,
        // so it is asserted over the generated family and not over a snapshot.
        let invert = |l: &[(f64, f64); 4], g: f64| {
            let w = l
                .windows(2)
                .find(|w| g >= w[0].0 && g <= w[1].0)
                .expect("gate in ladder");
            let f = (g.ln() - w[0].0.ln()) / (w[1].0.ln() - w[0].0.ln());
            (w[0].1.ln() + f * (w[1].1.ln() - w[0].1.ln())).exp()
        };
        let mut exercised = 0;
        for (name, l) in generated_ladders() {
            // Only ladders that actually bracket the target can be solved; the
            // rest are the refusal path and are covered separately.
            let (lo, hi) = (l[0].1, l[3].1);
            for target in [1.5, 2.0, 3.0, 5.0, 11.0] {
                if target <= lo || target >= hi {
                    continue;
                }
                let g = gate_of(solve_gate_for_n_eff(&l, target));
                let n = invert(&l, g);
                assert!(
                    (n - target).abs() < 1e-9,
                    "{name}: gate {g} inverted to n_eff {n}, wanted {target}"
                );
                exercised += 1;
            }
        }
        // Rule 36: a loop that skipped every case would pass silently.
        assert!(
            exercised > 40,
            "only {exercised} solves were actually exercised; this test would \
             pass vacuously if the generated family stopped bracketing the targets"
        );

        let g = gate_of(solve_gate_for_n_eff(&LADDER_109MSDCF, 3.0));
        let n = invert(&LADDER_109MSDCF, g);
        assert!(
            (n - 3.0).abs() < 1e-9,
            "109MSDCF: gate {g} inverted to n_eff {n}"
        );
    }

    /// **The claim, asserted one-sidedly — and that is the entire design.**
    ///
    /// This test replaces `the_solved_gate_spans_the_range_fact_324_claims`,
    /// which was green while two of its three assertions were false of the
    /// pipeline. It solved a frozen `LADDERS` fixture and compared the result
    /// against bands derived from *that same frozen measurement*, so subject
    /// and object were two copies of one stale snapshot. It could not fail when
    /// the pipeline moved, which is the only thing it existed to detect.
    ///
    /// The rule that generalises out of it: **a claim of the form "X is large"
    /// must be asserted as a one-sided bound, and the bound must be set from
    /// the threshold at which the claim stops meaning anything — never from the
    /// current measurement.** A two-sided band does not encode a claim, it
    /// encodes a measurement, and a measurement expires.
    ///
    /// The old test is the proof of its own rule. Its one-sided `hi / lo > 2.4`
    /// was *correctly calibrated all along*: the spread was 2.7215x before the
    /// ISO-50 gain fix and is 28.8703x after, and that assertion is true of
    /// both. Its two-sided companions — `lo` in `1.0..1.2`, `hi` in `2.7..3.1`
    /// — were false the moment the pipeline moved (`lo` is now 0.7618 and `hi`
    /// 21.9934) and had no way to say so. **The surviving assertion and the
    /// broken ones were in the same function; the difference was one-sidedness.**
    ///
    /// So the floors below are the ones that hold against **both** the pre-fix
    /// five-stack measurement and M52's post-fix seven-stack measurement. That
    /// is the only check available that distinguishes a floor encoding the
    /// claim from a floor encoding today's data, and it is how these two were
    /// chosen: 5.0 and 2.0 were tried first and rejected because they passed
    /// only the newer snapshot.
    ///
    /// A recalibration that ever made the corpus agree would fail this test.
    /// That is correct: it would be the discovery that the gate had become a
    /// calibration after all, and it should stop the build.
    #[test]
    fn no_single_gate_calibrates_across_the_corpus() {
        let gates: Vec<f64> = SOLVED_GATES_M52.iter().map(|(_, g)| *g).collect();
        let lo = gates.iter().copied().fold(f64::INFINITY, f64::min);
        let hi = gates.iter().copied().fold(f64::NEG_INFINITY, f64::max);

        // 2.7215x pre-fix, 28.8703x post-fix. A gate whose required value moves
        // 2.4x across subjects is already not a calibration.
        assert!(
            hi / lo > 2.4,
            "solved gates spanned only {:.4}x ({lo:.4} to {hi:.4}). The claim is \
             that no fixed gate is a calibration; a spread this small would mean \
             it had become one. That is a finding to investigate, not a bound to \
             relax",
            hi / lo
        );

        // The claim is about the corpus, not about its two extremes: a single
        // outlier stack would produce a wide spread while the gate still
        // transferred among the rest. 1.8580x pre-fix, 2.8388x post-fix.
        let mut sorted = gates.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).expect("no NaN"));
        let q1 = sorted[1];
        let q3 = sorted[sorted.len() - 2];
        assert!(
            q3 / q1 > 1.5,
            "discarding the extremes, the gates spanned only {:.4}x ({q1:.4} to \
             {q3:.4}); the spread would then be one outlier rather than a \
             property of the corpus",
            q3 / q1
        );

        // A cross-implementation check, and the one assertion here with a
        // subject distinct from its object. M52 solved 109MSDCF's gate with an
        // independent Python merge and got 2.0964; this crate's own solver, on
        // its own copy of that ladder, must agree. 109MSDCF is the control
        // stack precisely because ISO 160 is untouched by both of the day's
        // calibration commits, and indeed its solved gate is 2.0963 pre-fix
        // against 2.0964 post-fix while the ISO-50 stacks moved by 26% and 94%.
        let ours = gate_of(solve_gate_for_n_eff(&LADDER_109MSDCF, 3.0));
        let theirs = SOLVED_GATES_M52
            .iter()
            .find(|(n, _)| *n == "109MSDCF")
            .expect("109MSDCF is in the snapshot")
            .1;
        assert!(
            (ours - theirs).abs() < 1e-3,
            "this crate solved 109MSDCF to {ours:.4} where M52's independent \
             implementation got {theirs:.4}"
        );
    }

    /// `foam` cannot reach `n_eff = 3` anywhere on the shipped 0.5-4.0 ladder,
    /// so the solver must refuse rather than extrapolate a gate from a ladder
    /// that never got there.
    ///
    /// This one is behavioural rather than a snapshot: it asserts a *code path*
    /// against real measured rungs, and `foam` would have to more than double
    /// its `n_eff` before the assertion changed meaning. Both rungs are M52's,
    /// section 4.3, and M52 quotes the shipped solver's own reply verbatim —
    /// *"target n_eff 3.000 is above the ladder: gate 4.0000 reaches only
    /// 1.361"* — so this is a cross-check against an independent run, not
    /// against itself.
    #[test]
    fn a_stack_the_shipped_ladder_cannot_reach_is_refused_not_extrapolated() {
        let foam = [(2.0, 1.177), (4.0, 1.361)];
        match solve_gate_for_n_eff(&foam, 3.0) {
            Solve::AboveLadder {
                highest_gate,
                highest,
            } => {
                assert!((highest_gate - 4.0).abs() < 1e-12, "got {highest_gate}");
                assert!((highest - 1.361).abs() < 1e-12, "got {highest}");
            }
            other => panic!(
                "foam reaches only n_eff 1.361 at the top of the shipped ladder, so \
                 solving it for 3.0 must refuse; got {other:?}. Extrapolating here \
                 would invent a gate no measurement supports"
            ),
        }
    }

    #[test]
    fn a_target_outside_the_ladder_is_refused_rather_than_extrapolated() {
        let l = [(0.5, 1.414), (1.0, 1.884), (2.0, 2.891)];
        assert!(matches!(
            solve_gate_for_n_eff(&l, 1.1),
            Solve::BelowLadder { .. }
        ));
        assert!(matches!(
            solve_gate_for_n_eff(&l, 9.0),
            Solve::AboveLadder { .. }
        ));
        // And the boundary rungs themselves still solve.
        assert!((gate_of(solve_gate_for_n_eff(&l, 1.414)) - 0.5).abs() < 1e-9);
        assert!((gate_of(solve_gate_for_n_eff(&l, 2.891)) - 2.0).abs() < 1e-9);
    }

    #[test]
    fn a_non_monotone_ladder_is_a_bug_and_is_reported_as_one() {
        // Admission is a threshold on a field fixed before the gate applies, so
        // a larger gate admits a superset. n_eff falling is impossible, and
        // interpolating across it would launder a bug into a number.
        let bad = [(0.5, 1.414), (1.0, 2.500), (2.0, 2.100)];
        assert!(matches!(
            solve_gate_for_n_eff(&bad, 2.2),
            Solve::Unusable(_)
        ));
    }

    #[test]
    fn degenerate_ladders_and_targets_are_refused() {
        assert!(matches!(
            solve_gate_for_n_eff(&[(1.0, 2.0)], 1.5),
            Solve::Unusable(_)
        ));
        assert!(matches!(solve_gate_for_n_eff(&[], 1.5), Solve::Unusable(_)));
        // n_eff cannot go below 1: the winner is admitted unconditionally.
        let l = [(0.5, 1.414), (2.0, 2.891)];
        assert!(matches!(solve_gate_for_n_eff(&l, 1.0), Solve::Unusable(_)));
        assert!(matches!(
            solve_gate_for_n_eff(&l, f64::NAN),
            Solve::Unusable(_)
        ));
        // Gate 0 is a valid measurement but not a valid log-log rung; the
        // caller filters it, and the solve refuses it if the filter is removed.
        assert!(matches!(
            solve_gate_for_n_eff(&[(0.0, 1.0), (2.0, 2.9)], 2.0),
            Solve::Unusable(_)
        ));
    }

    #[test]
    fn an_unsorted_ladder_solves_the_same_as_a_sorted_one() {
        let sorted = [(0.5, 1.414), (1.0, 1.884), (2.0, 2.891), (4.0, 4.987)];
        let shuffled = [(2.0, 2.891), (0.5, 1.414), (4.0, 4.987), (1.0, 1.884)];
        let a = gate_of(solve_gate_for_n_eff(&sorted, 3.0));
        let b = gate_of(solve_gate_for_n_eff(&shuffled, 3.0));
        assert!((a - b).abs() < 1e-12, "{a} != {b}");
    }

    fn gaussian_noise(len: usize, sd: f32, mut state: u64) -> Vec<f32> {
        let mut uniform = || {
            state = state.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = state;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            ((z ^ (z >> 31)) >> 11) as f64 / (1u64 << 53) as f64
        };
        (0..len)
            .map(|_| {
                let (u1, u2) = (uniform().max(1e-12), uniform());
                (f64::from(sd) * (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos())
                    as f32
            })
            .collect()
    }

    fn checker_signal(w: usize, h: usize) -> Vec<f32> {
        (0..w * h)
            .map(|i| {
                let (x, y) = (i % w, i / w);
                if ((x / 3) + (y / 3)) % 2 == 0 {
                    200.0
                } else {
                    -200.0
                }
            })
            .collect()
    }

    fn box_blur_3x3(v: &[f32], w: usize, h: usize) -> Vec<f32> {
        let mut out = vec![0.0; v.len()];
        for y in 0..h {
            for x in 0..w {
                let mut sum = 0.0;
                for dy in [h - 1, 0, 1] {
                    for dx in [w - 1, 0, 1] {
                        sum += v[((y + dy) % h) * w + (x + dx) % w];
                    }
                }
                out[y * w + x] = sum / 9.0;
            }
        }
        out
    }

    fn synthetic_controlled(
        signal: &[f32],
        w: usize,
        h: usize,
        model_sd: f32,
        inflation: f32,
        seed: u64,
    ) -> ControlledDetail {
        let actual_sd = model_sd * inflation;
        let flat = gaussian_noise(w * h, actual_sd, seed);
        let detail_noise = gaussian_noise(w * h, actual_sd, seed ^ 0xD1B5_4A32_D192_ED03);
        let detail: Vec<f32> = signal
            .iter()
            .zip(detail_noise)
            .map(|(s, n)| *s + n)
            .collect();
        let sigma = vec![model_sd; w * h];
        cross_fitted_detail(&detail, &sigma, w, h, &flat, &sigma, w, h)
            .expect("synthetic ROIs are valid")
    }

    fn harmonic(n: usize) -> f64 {
        (1..=n).map(|k| 1.0 / k as f64).sum()
    }

    #[test]
    fn selection_noise_null_tracks_one_across_frame_counts() {
        let (w, h, sd) = (512usize, 512usize, 20.0f32);
        let no_signal = vec![0.0; w * h];
        for (j, n) in [22usize, 130, 299].into_iter().enumerate() {
            let max_scale = harmonic(n).sqrt() as f32;
            let averaged_scale = (1.0 + 0.35 * (harmonic(n) - 1.0)).sqrt() as f32;
            let selector = synthetic_controlled(&no_signal, w, h, sd, max_scale, 0x1000 + j as u64);
            let candidate =
                synthetic_controlled(&no_signal, w, h, sd, averaged_scale, 0x2000 + j as u64);
            let retention = equal_noise_retention(candidate, selector);
            eprintln!(
                "M80 N={n} noise: selector_structure={:.6} candidate_structure={:.6} \
                 retention={retention:.6} fitted_k={:.6}/{:.6}",
                selector.structure,
                candidate.structure,
                candidate.inflation_left,
                candidate.inflation_right
            );
            assert!(
                (0.90..=1.10).contains(&candidate.structure),
                "noise null N={n}: STRUCTURE must read 1, got {:.6}; fitted k={:.4}/{:.4}, \
                 planted inflation={averaged_scale:.4}",
                candidate.structure,
                candidate.inflation_left,
                candidate.inflation_right
            );
            assert!(
                (0.90..=1.10).contains(&retention),
                "noise null N={n}: RETENTION must read 1, got {retention:.6}; \
                 selector STRUCTURE {:.6}, candidate STRUCTURE {:.6}",
                selector.structure,
                candidate.structure
            );
        }
    }

    #[test]
    fn cross_fitted_metric_keeps_detail_and_detects_blur_across_frame_counts() {
        let (w, h, sd) = (512usize, 512usize, 20.0f32);
        let signal = checker_signal(w, h);
        let blurred = box_blur_3x3(&signal, w, h);
        let zero = vec![0.0; w * h];
        let clean_metric = detail_metrics(&signal, &zero, w, h);
        let blur_metric = detail_metrics(&blurred, &zero, w, h);
        let planted_retention = blur_metric.raw_rms / clean_metric.raw_rms;
        eprintln!("M80 positive plant: clean-to-blur gradient retention={planted_retention:.6}");
        assert!(
            planted_retention <= 0.75,
            "positive control cannot express failure: 3x3 blur retained \
             {planted_retention:.6} of gradient amplitude"
        );

        let mut clean_retentions = Vec::new();
        for (j, n) in [22usize, 130, 299].into_iter().enumerate() {
            let max_scale = harmonic(n).sqrt() as f32;
            let averaged_scale = (1.0 + 0.35 * (harmonic(n) - 1.0)).sqrt() as f32;
            let selector = synthetic_controlled(&signal, w, h, sd, max_scale, 0x3000 + j as u64);
            let clean = synthetic_controlled(&signal, w, h, sd, averaged_scale, 0x4000 + j as u64);
            let blur = synthetic_controlled(&blurred, w, h, sd, averaged_scale, 0x5000 + j as u64);
            let clean_retention = equal_noise_retention(clean, selector);
            let blur_retention = equal_noise_retention(blur, selector);
            eprintln!(
                "M80 N={n} detail: structure={:.6} clean_retention={clean_retention:.6} \
                 blur_retention={blur_retention:.6}",
                clean.structure
            );
            assert!(
                clean.structure >= 3.0,
                "detail control N={n}: STRUCTURE was {:.6}",
                clean.structure
            );
            assert!(
                (0.95..=1.05).contains(&clean_retention),
                "detail control N={n}: unchanged signal retained {clean_retention:.6}"
            );
            assert!(
                blur_retention <= 0.80,
                "detail control N={n}: planted blur retained {blur_retention:.6}"
            );
            clean_retentions.push(clean_retention);
        }
        let lo = clean_retentions
            .iter()
            .copied()
            .fold(f64::INFINITY, f64::min);
        let hi = clean_retentions
            .iter()
            .copied()
            .fold(f64::NEG_INFINITY, f64::max);
        assert!(
            hi - lo <= 0.05,
            "unchanged detail moved {:.6} across N: {clean_retentions:?}",
            hi - lo
        );
    }

    #[test]
    fn the_isotropic_column_is_the_analytic_value_on_a_linear_ramp() {
        // A ramp of slope s in x and t in y has |grad| = sqrt(s^2 + t^2)
        // everywhere, so this pins both the differences and the normalisation.
        let (w, h) = (16usize, 12usize);
        let (s, t) = (3.0f32, 4.0f32);
        let v: Vec<f32> = (0..w * h)
            .map(|i| s * (i % w) as f32 + t * (i / w) as f32)
            .collect();
        let m = detail_metrics(&v, &vec![0.0; w * h], w, h);
        assert!(
            (m.iso_mean - 5.0).abs() < 1e-6,
            "ramp gradient should be exactly 5, got {}",
            m.iso_mean
        );
        assert!(
            (m.m2_pooled_abs - 3.5).abs() < 1e-6,
            "pooled should be 0.5*(3+4), got {}",
            m.m2_pooled_abs
        );
    }

    #[test]
    fn the_corrected_column_falls_under_blur_which_is_the_property_it_is_used_for() {
        // The model-only component still has to detect the collapse fact 24
        // measured. The shipping invariant wraps this power in a cross-fitted
        // selection correction; noise is zero here so both forms reduce to the
        // same optical fall.
        let (w, h) = (64usize, 64usize);
        let sharp: Vec<f32> = (0..w * h)
            .map(|i| {
                if ((i % w) / 4 + (i / w) / 4) % 2 == 0 {
                    1000.0
                } else {
                    0.0
                }
            })
            .collect();
        let mut blurred = vec![0.0f32; w * h];
        for y in 1..h - 1 {
            for x in 1..w - 1 {
                let mut acc = 0.0;
                for dy in 0..3 {
                    for dx in 0..3 {
                        acc += sharp[(y + dy - 1) * w + (x + dx - 1)];
                    }
                }
                blurred[y * w + x] = acc / 9.0;
            }
        }
        let zero = vec![0.0f32; w * h];
        let a = detail_metrics(&sharp, &zero, w, h);
        let b = detail_metrics(&blurred, &zero, w, h);
        assert!(a.corrected_rms > 0.0 && b.corrected_rms > 0.0);
        assert!(
            b.corrected_rms < 0.75 * a.corrected_rms,
            "blur must cut the corrected metric substantially: sharp {}, blurred {}",
            a.corrected_rms,
            b.corrected_rms
        );
    }

    #[test]
    fn the_m2_convention_column_reproduces_the_independently_identified_definition() {
        // M38 §1 identified fact 24's convention as mean(0.5*(|dx|+|dy|)) by
        // measurement, against an independent numpy implementation. This pins
        // the Rust column to that definition on a field where it is hand
        // computable: a pure x-ramp of slope 3 has |dx| = 3, |dy| = 0, so the
        // pooled value is 1.5 while the isotropic value is 3.
        let (w, h) = (8usize, 8usize);
        let v: Vec<f32> = (0..w * h).map(|i| 3.0 * (i % w) as f32).collect();
        let s = vec![0.0f32; w * h];
        let m = detail_metrics(&v, &s, w, h);
        assert!((m.m2_pooled_abs - 1.5).abs() < 1e-9, "{}", m.m2_pooled_abs);
        assert!((m.iso_mean - 3.0).abs() < 1e-9, "{}", m.iso_mean);
        // With zero noise the correction must be inert, not merely small.
        assert_eq!(m.noise_rms, 0.0);
        assert!((m.corrected_rms - m.raw_rms).abs() < 1e-9);
    }

    #[test]
    fn the_noise_correction_removes_pure_noise_down_to_sampling_error() {
        // This pins ordinary, unselected noise subtraction only. M77 showed
        // that it says nothing about selected noise; the cross-fitted tests
        // above cover that separate term.
        let (w, h) = (256usize, 256usize);
        let sd = 20.0f32;
        let mut rng = 0x2545_F491_4F6C_DD1Du64;
        let mut next = || {
            rng = rng.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = rng;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            ((z ^ (z >> 31)) >> 11) as f64 / (1u64 << 53) as f64
        };
        let v: Vec<f32> = (0..w * h)
            .map(|_| {
                let (u1, u2) = (next().max(1e-12), next());
                (sd as f64 * (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
            })
            .collect();
        let s = vec![sd; w * h];
        let m = detail_metrics(&v, &s, w, h);
        // Raw rms of pure noise is ~2*sd; the model predicts exactly that.
        assert!(
            (m.raw_rms / m.noise_rms - 1.0).abs() < 0.02,
            "model must predict pure noise: raw {} vs model {}",
            m.raw_rms,
            m.noise_rms
        );
        assert!(
            m.corrected_rms < 0.2 * m.raw_rms,
            "corrected should collapse on pure noise: {} vs raw {}",
            m.corrected_rms,
            m.raw_rms
        );
    }

    #[test]
    fn the_correction_leaves_signal_alone_while_removing_added_noise() {
        // The same unselected signal measured clean and with noise added must
        // give the same model-corrected value. Selection is deliberately absent
        // here and covered by the M80 controls above.
        let (w, h) = (256usize, 256usize);
        let signal: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                400.0 * (x * 0.11).sin() * (y * 0.07).cos()
            })
            .collect();
        let sd = 30.0f32;
        let mut rng = 0x1234_5678_9ABC_DEF0u64;
        let mut next = || {
            rng = rng.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = rng;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            ((z ^ (z >> 31)) >> 11) as f64 / (1u64 << 53) as f64
        };
        let noisy: Vec<f32> = signal
            .iter()
            .map(|v| {
                let (u1, u2) = (next().max(1e-12), next());
                v + (sd as f64 * (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos())
                    as f32
            })
            .collect();
        let clean = detail_metrics(&signal, &vec![0.0; w * h], w, h);
        let dirty = detail_metrics(&noisy, &vec![sd; w * h], w, h);
        assert!(
            dirty.raw_rms > 1.05 * clean.raw_rms,
            "noise must raise the uncorrected metric, else the test proves nothing: {} vs {}",
            dirty.raw_rms,
            clean.raw_rms
        );
        let rel = (dirty.corrected_rms / clean.corrected_rms - 1.0).abs();
        assert!(
            rel < 0.03,
            "corrected must be blind to added noise: clean {} vs noisy {} ({:.1}%)",
            clean.corrected_rms,
            dirty.corrected_rms,
            100.0 * rel
        );
    }

    #[test]
    fn degenerate_rois_do_not_panic() {
        assert_eq!(detail_metrics(&[1.0], &[1.0], 1, 1).corrected_rms, 0.0);
        assert_eq!(detail_metrics(&[1.0, 2.0], &[1.0, 1.0], 2, 1).iso_mean, 0.0);
    }

    /// **The detail invariant is ONE-SIDED and this test is what says so.**
    ///
    /// The orchestrator MEASURED, in a 1-D optics simulation calibrated to
    /// reproduce facts 12/27/28 to 3-4 digits (25 frames, oracle depth, latent
    /// mean|grad| 0.0392):
    ///
    /// | sigma | mean\|grad\| sel | wiener | grad corr sel | grad corr wiener |
    /// |---|---|---|---|---|
    /// | 0.010 | 0.0296 | 0.0367 | 0.8595 | 0.7538 |
    /// | 0.050 | 0.0455 | 0.0293 | 0.5592 | 0.6629 |
    ///
    /// At sigma 0.010 the Wiener merge has **24% more** gradient magnitude and
    /// **12% less** gradient correlation with the truth — the extra magnitude is
    /// ringing sitting where no edge exists. At sigma 0.050 argmax selection
    /// reads 0.0455, **above the ground truth's 0.0392**: pure noise inflating
    /// the metric past the true value.
    ///
    /// A two-sided reading scores both of those as wins. So `detail_verdict`
    /// must never return a passing string for a large increase, and this test
    /// fails if someone later "simplifies" it into `retention >= floor`.
    #[test]
    fn a_gradient_increase_is_never_scored_as_a_pass() {
        // Fact 24's collapse: -58% and -53%.
        assert_eq!(detail_verdict(0.42), "COLLAPSE");
        assert_eq!(detail_verdict(0.47), "COLLAPSE");
        // The orchestrator's plain-mean reproduction: -49% to -51%.
        assert_eq!(detail_verdict(0.51), "COLLAPSE");
        assert_eq!(detail_verdict(0.49), "COLLAPSE");

        // Identity and small measurement scatter are not verdicts.
        for r in [1.0, 1.02, 1.10] {
            assert_eq!(detail_verdict(r), "ok", "near-identity reading {r} flagged");
        }

        // And the direction that matters: a large rise is NOT a pass.
        for r in [1.6, 2.0, 5.0] {
            let v = detail_verdict(r);
            assert_ne!(v, "ok", "retention {r} was scored as acceptable");
            assert_eq!(v, "INVESTIG.");
        }
    }

    /// The merge's speckle companion has to be quoted at the same tolerance as
    /// `strehl stack`'s, or the two numbers are not comparable and the companion
    /// is worthless. One constant, in core, imported by both.
    #[test]
    fn the_speckle_companion_uses_the_same_tolerance_as_the_argmax_baseline() {
        assert_eq!(
            SPECKLE_TOLERANCE,
            strehl_core::stack::DEFAULT_SPECKLE_TOLERANCE
        );
        assert_eq!(SPECKLE_TOLERANCE, crate::stack::speckle_tolerance_in_use());
    }

    #[test]
    fn the_plan_is_bounded_by_memory_and_scales_down_as_accumulators_are_added() {
        let geom = PlaneGeometry::from_active(4688, 7028);
        let frame_bytes = 66_000_000;
        let one = Plan::new(105, geom, frame_bytes, 1, 0, 0);
        let eight = Plan::new(105, geom, frame_bytes, 8, 0, 0);
        let roi_bytes = 3_000_000;
        let with_detail_control = Plan::new(105, geom, frame_bytes, 1, 0, roi_bytes);
        assert!(
            eight.workers <= one.workers,
            "more accumulators must not license more workers: {} vs {}",
            eight.workers,
            one.workers
        );
        assert!(eight.workers >= 1);
        assert_eq!(with_detail_control.roi_bytes, roi_bytes);
        assert_eq!(
            with_detail_control.pass2_bytes - one.pass2_bytes,
            roi_bytes,
            "the compact selector ROIs must be priced into pass two"
        );
        assert!(with_detail_control.workers <= one.workers);
        // The budget is the thing that has to hold, in both passes.
        for p in [&one, &eight] {
            assert!(
                p.chunks * p.pass1_bytes.max(p.pass2_bytes) <= MEMORY_BUDGET_BYTES
                    || p.workers == 1,
                "plan exceeds the budget without being cornered at one worker"
            );
        }
    }

    /// The memory ratchet, extended for `--stats`. Two things have to hold and
    /// they pull in opposite directions: turning the statistics on must be
    /// **priced** (so it cannot license more workers than the budget pays for),
    /// and its price must be **constant in the frame count** (so the ratchet in
    /// SYNTHESIS §3.2.1 is not quietly broken by an O(frames) object).
    #[test]
    fn the_statistics_are_priced_into_the_plan_and_do_not_grow_with_the_stack() {
        let geom = PlaneGeometry::from_active(4688, 7028);
        let frame_bytes = 66_000_000;
        let off = Plan::new(105, geom, frame_bytes, 1, 0, 0);
        let on = Plan::new(105, geom, frame_bytes, 1, 1, 0);
        let with_placebo = Plan::new(105, geom, frame_bytes, 1, 2, 0);

        assert_eq!(off.stats_bytes, 0, "off must cost nothing");
        assert!(
            on.pass2_bytes > off.pass2_bytes,
            "the gather must be priced into pass two, not hidden outside it"
        );
        assert!(
            on.workers <= off.workers,
            "a bigger working set must not license more workers: {} vs {}",
            on.workers,
            off.workers
        );
        assert!(
            with_placebo.stats_bytes > on.stats_bytes,
            "the placebo is a second gather and must be paid for"
        );

        // Constant in the frame count: the whole point of the seam decision.
        for frames in [22usize, 33, 105, 400] {
            let p = Plan::new(frames, geom, frame_bytes, 1, 1, 0);
            assert_eq!(
                p.stats_bytes, on.stats_bytes,
                "{frames} frames changed the statistics footprint; it is supposed \
                 to be O(1) in the stack depth"
            );
        }

        // And it must genuinely beat the object it replaces at corpus depth.
        let px = geom.pixels();
        let volume_22 = px * 4 * 22;
        assert!(
            on.stats_bytes < volume_22,
            "{} B of statistics is not cheaper than a 22-frame fine focus volume \
             at {} B; the seam decision was wrong",
            on.stats_bytes,
            volume_22
        );
        assert!(on.workers >= 1);
        assert!(
            on.chunks * on.pass1_bytes.max(on.pass2_bytes) <= MEMORY_BUDGET_BYTES
                || on.workers == 1,
            "the statistics plan exceeds the budget without being cornered at one worker"
        );
    }

    #[test]
    fn every_frame_is_covered_exactly_once_by_the_chunking() {
        let geom = PlaneGeometry::from_active(4688, 7028);
        for frames in [1usize, 2, 7, 22, 33, 63, 79, 105] {
            let plan = Plan::new(frames, geom, 66_000_000, 3, 0, 0);
            let mut seen = vec![0u32; frames];
            for ci in 0..plan.chunks {
                let start = ci * plan.chunk_len;
                let end = (start + plan.chunk_len).min(frames);
                for s in seen.iter_mut().take(end).skip(start) {
                    *s += 1;
                }
            }
            assert!(
                seen.iter().all(|c| *c == 1),
                "{frames} frames: coverage was {seen:?}"
            );
        }
    }
}
