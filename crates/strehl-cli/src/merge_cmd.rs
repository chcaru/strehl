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
    MEMORY_BUDGET_BYTES, Roi, flat_roi_stats, mean_and_sigma, provenance_line, roi_green,
    srgb_encode,
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
    /// Fact 324 measured that a fixed threshold is not a calibration: at gate
    /// 2.0 mean `n_eff` runs 2.26 to 7.42 across five stacks, and the gate
    /// needed to reach `n_eff = 3` runs 1.1 to 2.9. A target `n_eff` transfers
    /// where a gate does not, and it is the quantity fact 212 calibrated.
    pub target_n_eff: Option<f64>,
    /// Gather per-pixel through-focus sufficient statistics during pass two.
    ///
    /// Opt-in because it is not free: `ThroughFocus` costs 60 B/px, which on the
    /// A7C II plane is 494 MB per worker and will reduce the worker count the
    /// memory budget licenses. With it off, the merge path's memory is exactly
    /// what M37/M38 measured.
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
/// calibrated model rather than an assumption. That is the number invariant 2
/// is judged on.
struct DetailMetrics {
    /// `mean(0.5*(|dx| + |dy|))` — fact 24's convention, for comparability.
    m2_pooled_abs: f64,
    /// `mean(hypot(dx, dy))` — isotropic, rotation-invariant.
    iso_mean: f64,
    /// `sqrt(mean(dx^2 + dy^2))` — signal and noise together.
    raw_rms: f64,
    /// The model's prediction for what the noise alone contributes to it.
    noise_rms: f64,
    /// `sqrt(max(0, raw_rms^2 - noise_rms^2))` — the headline.
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

struct Plan {
    workers: usize,
    chunks: usize,
    chunk_len: usize,
    pass1_bytes: usize,
    pass2_bytes: usize,
    stats_bytes: usize,
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
        let pass2_bytes =
            px * (PASS2_SCRATCH_PER_PX + gates * ESTIMATOR_PER_PX) + stats_bytes + frame_bytes;
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
    /// decoded it. This is the unstacked reference both invariants compare to.
    flat: Option<Vec<f32>>,
    detail: Option<Vec<f32>>,
    t: Timings,
}

struct Pass2 {
    est: Vec<Estimator>,
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
    );

    // The placebo permutation. Fixed, auditable and reproducible.
    //
    // NOT a rotation. `k -> (k + n/3) mod n` was the first draft and it is an
    // isometry of the index line, so adjacency survives and the placebo returned
    // exactly 1.0000x of the real reading -- a null that had silently become a
    // copy of its own subject. A seeded shuffle is the fix; the core test
    // `shuffle_destroys_adjacency_which_a_rotation_does_not` holds the line.
    let perm: Vec<u16> = shuffled_indices(paths.len(), PLACEBO_SEED);

    eprintln!("strehl merge -- regularised winner + noise-gated average (the estimation merge)");
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
            let (mut flat, mut detail) = (None, None);
            let mut t = Timings::default();

            for (offset, path) in chunk.iter().enumerate() {
                let index = first_index + offset as u16;
                let frame = ctx.field_for(path, index, &mut scratch, &mut t)?;
                if index == middle {
                    flat = opts.flat_roi.map(|r| roi_green(&frame, r, levels.black));
                    detail = opts.detail_roi.map(|r| roi_green(&frame, r, levels.black));
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
                detail,
                t,
            })
        })
        .reduce_with(|a, b| match (a, b) {
            (Ok(mut a), Ok(b)) => {
                a.stats.absorb(&b.stats).map_err(|e| map_dim_err(0, e))?;
                a.clip.absorb(&b.clip).map_err(|e| map_dim_err(0, e))?;
                a.flat = a.flat.or(b.flat);
                a.detail = a.detail.or(b.detail);
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
                    if let Err(e) = e.fold(index, &frame, &scratch.reg) {
                        err = Some(map_dim_err(index, e));
                        break;
                    }
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
    eprintln!(
        "single frame {middle:<3}: sigma {single_sigma:8.3} DN   mean {single_mean:9.2} DN   \
         (no stacking at all)"
    );
    eprintln!(
        "model predicts  : sigma {:8.3} DN for one green-luma sample at that level",
        noise.green_luma_sigma(single_mean as f32)
    );
    eprintln!("  gate      sigma DN       mean DN      RATIO   winners in roi");
    for e in &p2.est {
        let s = flat_roi_stats(e, single, roi, geom, levels.black);
        eprintln!(
            "  {:5.2}   {:9.3}   {:11.2}   {:8.3}x   {} distinct, median {}",
            e.gate().threshold,
            s.stacked_sigma,
            s.stacked_mean,
            s.ratio,
            s.distinct_winners,
            s.median_winner
        );
    }
    eprintln!(
        "                  PASS is <= 1.000x. The argmax baseline measured 1.253x here \
         (fact 19/23),"
    );
    eprintln!(
        "                  and a plain unweighted mean measured 0.534x -- which is the floor, not"
    );
    eprintln!("                  a target, because of invariant 2.");
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
    let single_detail = p1
        .detail
        .as_ref()
        .context("the middle frame's detail ROI was never captured")?;
    // The single frame's own predicted sigma, from the same calibrated model
    // the merged side uses. Both sides are model-predicted, so the correction
    // cannot favour one of them by construction.
    let single_sigma_map: Vec<f32> = single_detail
        .iter()
        .map(|v| noise.green_luma_sigma(*v))
        .collect();
    let base = detail_metrics(single_detail, &single_sigma_map, droi.width, droi.height);
    ensure!(
        base.corrected_rms > 0.0,
        "the detail ROI has no signal gradient above the noise model in the middle frame; \
         it is not a detail region"
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
        "                  MEAN |GRAD| IS ALSO CONFOUNDED BY NOISE and that confound has the same"
    );
    eprintln!(
        "                  sign as the effect: cutting sigma cuts gradient with zero blur, so"
    );
    eprintln!(
        "                  an uncorrected reading charges the merge for doing its job. `corrected`"
    );
    eprintln!(
        "                  is sqrt(raw^2 - model^2), the only column judged. `m2` is fact 24's"
    );
    eprintln!("                  convention (M38 §1), reported so that comparison is legitimate.");
    eprintln!(
        "single frame {middle:<3}: corrected {:8.4}   raw rms {:8.4}   model noise {:8.4}   \
         m2 {:8.4}   iso {:8.4}",
        base.corrected_rms, base.raw_rms, base.noise_rms, base.m2_pooled_abs, base.iso_mean
    );
    eprintln!(
        "  gate     corrected     RETENTION   VERDICT      raw rms   model noise         m2        \
         iso"
    );
    for e in &p2.est {
        let merged = roi_green_merged(e, droi, geom, levels.black);
        let sig: Vec<f32> = (droi.y..droi.y + droi.height)
            .flat_map(|py| (droi.x..droi.x + droi.width).map(move |px| (px, py)))
            .map(|(px, py)| e.predicted_sigma(noise, geom.index(px, py), levels.black))
            .collect();
        let m = detail_metrics(&merged, &sig, droi.width, droi.height);
        let retention = m.corrected_rms / base.corrected_rms;
        eprintln!(
            "  {:5.2}   {:9.4}   {:9.3}x   {:9}   {:10.4}   {:11.4}   {:8.4}   {:8.4}",
            e.gate().threshold,
            m.corrected_rms,
            retention,
            detail_verdict(retention),
            m.raw_rms,
            m.noise_rms,
            m.m2_pooled_abs,
            m.iso_mean
        );
    }
    eprintln!(
        "                  The reference is ONE frame of the bracket, so much of this ROI is out"
    );
    eprintln!(
        "                  of focus in it and retention ABOVE 1.0 is expected -- that is the stack"
    );
    eprintln!(
        "                  finding focus the reference does not have. The failure this catches is"
    );
    eprintln!(
        "                  CORRECTED retention falling as the gate opens, which is fact 24's"
    );
    eprintln!("                  collapse arriving and cannot be explained away as noise removal.");
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
    eprintln!(
        "                  detail move it away from that. Fact 23's reference points are 34.4% \
         (ring"
    );
    eprintln!("                  operator, unregularised) and 0.868% (Tenengrad, regularised).");
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

/// One-sided reading of a corrected-retention ratio.
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

/// Corrected retention below this is fact 24's collapse.
///
/// Registered at 0.90 because fact 24's measured collapse is **-58% and -53%**
/// (retention 0.42x and 0.47x) and the orchestrator's simulation independently
/// reproduces a plain mean at -49% to -51%. A 10% floor sits an order of
/// magnitude above the noise on this metric while leaving a wide margin below
/// the failure it is aimed at, so it cannot fire on ordinary gate-to-gate drift
/// (MEASURED tonight: 0.2% on 109MSDCF, 0.6% on 119MSDCF across gate 0 to 2.0).
const DETAIL_COLLAPSE_FLOOR: f64 = 0.90;

/// Corrected retention above this is a flag to investigate, never a pass.
///
/// Set at 1.50 rather than 1.00 because the reference is one frame of a focus
/// bracket and much of a detail ROI is genuinely out of focus in it, so
/// retention above 1 is the *expected* reading — 1.257x and 1.027x tonight. A
/// merge finding 50% more corrected gradient than the sharpest thing in the
/// reference frame is more likely to be ringing than to be focus.
const DETAIL_RISE_FLAG: f64 = 1.50;

// Pinned at compile time rather than in a test, because these are relationships
// between constants and a build that violates one should not link.
//
// The rise flag must sit above 1.0: retention above 1 is EXPECTED here, because
// the reference is one frame of a focus bracket and much of a detail ROI is out
// of focus in it (1.257x and 1.027x MEASURED tonight).
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
        "fine noise sd   : {FINE_FOCUS_NOISE_SD:.6}, MEASURED in-crate, {:.2}x the selection \
         field's {FOCUS_NOISE_SD:.6}",
        FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD
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
        "                  The first is a diagnostic and is expected to be large: the fine field \
         is"
    );
    eprintln!(
        "                  {:.2}x noisier than the selection field, so its argmax moves. The \
         second is",
        FINE_FOCUS_NOISE_SD / FOCUS_NOISE_SD
    );
    eprintln!(
        "                  the actionable one, because off-by-one is still bracketed by the \
         parabola."
    );
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

    /// The five ladders fact 324 measured, as `(gate, mean n_eff)`.
    ///
    /// Kept here verbatim so the solve and the fact check each other: if either
    /// is edited carelessly, `the_solved_gate_spans_the_range_fact_324_claims`
    /// fails.
    const LADDERS: [(&str, [(f64, f64); 4]); 5] = [
        (
            "119MSDCF",
            [(0.5, 1.275), (1.0, 1.581), (2.0, 2.258), (4.0, 3.654)],
        ),
        (
            "109MSDCF",
            [(0.5, 1.414), (1.0, 1.884), (2.0, 2.891), (4.0, 4.987)],
        ),
        (
            "113MSDCF",
            [(0.5, 1.433), (1.0, 2.198), (2.0, 4.774), (4.0, 8.590)],
        ),
        (
            "112MSDCF",
            [(0.5, 1.554), (1.0, 2.572), (2.0, 6.226), (4.0, 12.065)],
        ),
        (
            "coffee-bean",
            [(0.5, 1.516), (1.0, 2.570), (2.0, 7.422), (4.0, 24.700)],
        ),
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
        for (name, l) in LADDERS {
            for (gate, n) in l {
                let g = gate_of(solve_gate_for_n_eff(&l, n));
                assert!(
                    (g - gate).abs() < 1e-9,
                    "{name}: rung {gate} round-tripped to {g}"
                );
            }
        }
    }

    #[test]
    fn the_solved_gate_spans_the_range_fact_324_claims() {
        // Fact 324's design conclusion is that no fixed gate is a calibration.
        // That is a claim about a RANGE, so assert the range — a test that
        // only checked one stack would pass for a broken solve.
        let gates: Vec<f64> = LADDERS
            .iter()
            .map(|(_, l)| gate_of(solve_gate_for_n_eff(l, 3.0)))
            .collect();
        let lo = gates.iter().cloned().fold(f64::INFINITY, f64::min);
        let hi = gates.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        assert!(
            (1.0..1.2).contains(&lo),
            "lowest solved gate {lo} left the claimed band"
        );
        assert!(
            (2.7..3.1).contains(&hi),
            "highest solved gate {hi} left the claimed band"
        );
        assert!(
            hi / lo > 2.4,
            "spread {} no longer supports fact 324",
            hi / lo
        );
    }

    #[test]
    fn a_solved_gate_reproduces_its_target_when_fed_back() {
        // Interpolation is only honest if it inverts the ladder it came from.
        // Rebuild n_eff at the solved gate by interpolating the ladder the
        // other way, and require the target back.
        for (name, l) in LADDERS {
            let g = gate_of(solve_gate_for_n_eff(&l, 3.0));
            let w = l
                .windows(2)
                .find(|w| g >= w[0].0 && g <= w[1].0)
                .expect("gate in ladder");
            let f = (g.ln() - w[0].0.ln()) / (w[1].0.ln() - w[0].0.ln());
            let n = (w[0].1.ln() + f * (w[1].1.ln() - w[0].1.ln())).exp();
            assert!(
                (n - 3.0).abs() < 1e-9,
                "{name}: gate {g} inverted to n_eff {n}"
            );
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
        // Invariant 2 only means something if the CORRECTED quantity detects
        // the collapse fact 24 measured. Correcting for noise must not have
        // made the metric blind to real blur. Noise is zero here so the
        // correction is inert and the fall is entirely optical.
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
        // The property that makes invariant 2 defensible: on a field that is
        // ONLY noise, corrected_rms must collapse toward zero while raw_rms
        // does not. If this fails, the metric is charging the merge for noise
        // reduction, which is the confound the correction exists to remove.
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
        // The decisive pairing: the same signal measured clean and measured
        // with noise added must give the SAME corrected value, while the
        // uncorrected value rises. That is the confound, isolated.
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

        // Tonight's real readings, both stacks, gate 0 through 2.0.
        for r in [1.257, 1.254, 1.027, 1.021] {
            assert_eq!(detail_verdict(r), "ok", "real reading {r} must not flag");
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
        let one = Plan::new(105, geom, frame_bytes, 1, 0);
        let eight = Plan::new(105, geom, frame_bytes, 8, 0);
        assert!(
            eight.workers <= one.workers,
            "more accumulators must not license more workers: {} vs {}",
            eight.workers,
            one.workers
        );
        assert!(eight.workers >= 1);
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
        let off = Plan::new(105, geom, frame_bytes, 1, 0);
        let on = Plan::new(105, geom, frame_bytes, 1, 1);
        let with_placebo = Plan::new(105, geom, frame_bytes, 1, 2);

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
            let p = Plan::new(frames, geom, frame_bytes, 1, 1);
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
            let plan = Plan::new(frames, geom, 66_000_000, 3, 0);
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
