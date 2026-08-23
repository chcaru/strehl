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
use strehl_core::focus::FocusField;
use strehl_core::merge::{
    Estimator, FOCUS_NOISE_SD, FocusStats, Gate, REGULARISER_WIDTH, regularise,
};
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma};
use strehl_core::profile;
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
}

/// The detail half of the acceptance pair, in four conventions.
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
}

/// Per-worker bytes in pass one: `FocusStats` (f32 focus + u16 index) plus the
/// four scratch planes the fold walks through.
const PASS1_PER_PX: usize = 6 + 4 + 12 + 4 + 4;
/// Per-worker scratch in pass two, excluding the accumulators.
const PASS2_SCRATCH_PER_PX: usize = 4 + 12 + 4 + 4;
/// One `Estimator`: four f32 sums, a u16 count, and the winner field it was
/// built from (f32 + u16).
const ESTIMATOR_PER_PX: usize = 4 * 4 + 2 + 4 + 2;

impl Plan {
    fn new(frames: usize, geom: PlaneGeometry, frame_bytes: usize, gates: usize) -> Self {
        let px = geom.pixels();
        let pass1_bytes = px * PASS1_PER_PX + frame_bytes;
        let pass2_bytes = px * (PASS2_SCRATCH_PER_PX + gates * ESTIMATOR_PER_PX) + frame_bytes;
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
        }
    }

    fn describe(&self) -> String {
        format!(
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
        )
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
}

impl Scratch {
    fn new(geom: PlaneGeometry) -> Self {
        let px = geom.pixels();
        Self {
            luma: vec![0.0; px],
            field: FocusField::new(geom),
            box_scratch: vec![0.0; px],
            reg: vec![0.0; px],
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
        green_luma(&frame, self.levels.black, &mut scratch.luma);
        scratch.field.compute(&scratch.luma, self.noise);
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
    /// The middle frame's flat and detail ROIs, kept by whichever worker
    /// decoded it. This is the unstacked reference both invariants compare to.
    flat: Option<Vec<f32>>,
    detail: Option<Vec<f32>>,
    t: Timings,
}

struct Pass2 {
    est: Vec<Estimator>,
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

    let plan = Plan::new(paths.len(), geom, frame_bytes, opts.gates.len());

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
            let mut scratch = Scratch::new(geom);
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
            }
            Ok(Pass1 {
                stats,
                flat,
                detail,
                t,
            })
        })
        .reduce_with(|a, b| match (a, b) {
            (Ok(mut a), Ok(b)) => {
                a.stats.absorb(&b.stats).map_err(|e| map_dim_err(0, e))?;
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
            let mut scratch = Scratch::new(geom);
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
                t.work += t0.elapsed().as_secs_f64();
            }
            Ok(Pass2 { est, t })
        })
        .reduce_with(|a, b| match (a, b) {
            (Ok(mut a), Ok(b)) => {
                for (x, y) in a.est.iter_mut().zip(b.est.iter()) {
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
        "  gate   tol(DN-norm)     mean n_eff   n_eff=1 %   boundary %   pred sigma gain 1/sqrt(n)"
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
            1.0 / mean.sqrt()
        );
    }
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
        "                  MEAN |GRAD| IS CONFOUNDED BY NOISE and the confound has the same sign"
    );
    eprintln!("                  as the effect: cutting sigma cuts gradient with zero blur, so an");
    eprintln!(
        "                  uncorrected reading charges the merge for doing its job. `corrected` is"
    );
    eprintln!("                  sqrt(raw^2 - model^2), the only column judged. `m2` is fact 24's");
    eprintln!("                  convention (M38 §1), reported so that comparison is legitimate.");
    eprintln!(
        "single frame {middle:<3}: corrected {:8.4}   raw rms {:8.4}   model noise {:8.4}   \
         m2 {:8.4}   iso {:8.4}",
        base.corrected_rms, base.raw_rms, base.noise_rms, base.m2_pooled_abs, base.iso_mean
    );
    eprintln!(
        "  gate     corrected     RETENTION      raw rms   model noise         m2        iso"
    );
    for e in &p2.est {
        let merged = roi_green_merged(e, droi, geom, levels.black);
        let sig: Vec<f32> = (droi.y..droi.y + droi.height)
            .flat_map(|py| (droi.x..droi.x + droi.width).map(move |px| (px, py)))
            .map(|(px, py)| e.predicted_sigma(noise, geom.index(px, py), levels.black))
            .collect();
        let m = detail_metrics(&merged, &sig, droi.width, droi.height);
        eprintln!(
            "  {:5.2}   {:9.4}   {:9.3}x   {:10.4}   {:11.4}   {:8.4}   {:8.4}",
            e.gate().threshold,
            m.corrected_rms,
            m.corrected_rms / base.corrected_rms,
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
    Ok(())
}

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

    #[test]
    fn the_plan_is_bounded_by_memory_and_scales_down_as_accumulators_are_added() {
        let geom = PlaneGeometry::from_active(4688, 7028);
        let frame_bytes = 66_000_000;
        let one = Plan::new(105, geom, frame_bytes, 1);
        let eight = Plan::new(105, geom, frame_bytes, 8);
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

    #[test]
    fn every_frame_is_covered_exactly_once_by_the_chunking() {
        let geom = PlaneGeometry::from_active(4688, 7028);
        for frames in [1usize, 2, 7, 22, 33, 63, 79, 105] {
            let plan = Plan::new(frames, geom, 66_000_000, 3);
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
