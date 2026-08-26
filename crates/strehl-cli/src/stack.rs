//! `strehl stack` — the walking skeleton.
//!
//! What this is, precisely: `decode -> calibrate -> NO alignment -> Tenengrad
//! focus volume -> plain per-pixel argmax -> 16-bit TIFF`. That is
//! SYNTHESIS §8 step 0, and it deliberately implements the naive selector this
//! whole project argues against, because that selector is the **named baseline
//! artifact** every later quality claim must be a measured delta against, and
//! because running it is how the argmax noise defect gets measured on our own
//! data rather than on someone else's.
//!
//! So: no denoising, no smoothing of the winner map, no top-k, no blending. Its
//! job is to be the honest worst case.
//!
//! # Streaming, not materialised
//!
//! SYNTHESIS §9 lists never-materialise as one of four irreversible decisions,
//! so the skeleton obeys it even though 22 frames would fit. The file list is
//! split into a bounded number of chunks; each chunk is folded by one worker
//! that decodes a frame, folds it, and **drops it before decoding the next**.
//! Peak memory is O(workers), not O(frames), and the worker count is derived
//! from a memory budget rather than from the frame count.
//!
//! `merge_cmd` reuses several of this module's helpers rather than
//! reimplementing them, which is why a few items below are `pub(crate)`. The
//! flat-ROI metric in particular has to be bit-identical across the argmax
//! baseline and the estimation merge, or the comparison between them measures
//! the harness instead of the merge (discipline 210).

use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use strehl_core::color::{self, AppliedExposure, Exposure};
use strehl_core::flat_ratio::{self, FrameFlat};
use strehl_core::focus::FocusField;
use strehl_core::noise::{Levels, NoiseModel, Provenance};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma};
use strehl_core::profile;
use strehl_core::stack::{Selection, speckle_fraction};
use strehl_core::{CfaPlane, Error};
use strehl_raw::Frame;

use crate::image_out;

/// Working-set ceiling used to size the worker pool. SYNTHESIS §3.2 ratchets
/// peak RSS at 8 GB independent of frame count; this leaves headroom for the
/// decoder's own scratch and the output buffers.
///
/// **This budget assumes the process owns the machine.** With several agents
/// rendering in one working tree that is false, and the failure is an abort
/// (`allocation of 33003520 bytes failed`, `0xC0000409`) partway into an
/// unattended full-corpus pass -- the run that most needed to finish. Making it
/// overridable is the right fix and is deliberately NOT done here: the constant
/// is read at nineteen sites across `stack.rs` and `merge_cmd.rs`, and a knob
/// wired at some of them is worse than no knob at all. It also changes the
/// worker count, which sets the fold's reduction order, so it would be an
/// unrecorded input to the byte-freeze unless registered in `RENDER_ENV`
/// alongside `STREHL_PYRAMID_WORKERS`. Logged for routing, not half-built.
pub(crate) const MEMORY_BUDGET_BYTES: usize = 6 << 30;

/// Peak RSS with one chunk on one thread, above that one worker's own buffers:
/// the runtime, the prologue frame's residue, and the epilogue. MEASURED (M8,
/// `experiments/m8-scratch`, `data/floor.csv`): 320.2 MiB at N=1 minus 305.8
/// MiB of buffers, over 3 runs with a spread of 0.06 MiB.
const PROCESS_FLOOR_BYTES: usize = 15_099_494;

/// Marginal peak RSS per concurrent worker *above* `per_worker_bytes`: the
/// decoder's own scratch plus the file-backed pages of the ARW it is reading.
/// MEASURED (M8): 37.0 +/- 5.4 MiB, fitted over 74 real-stack runs with the
/// thread count pinned; independently, an isolated single decode costs 39.4
/// MiB of private commit above its output buffer. See
/// `docs/research/M8-scratch-measured.md`.
const DECODER_SCRATCH_BYTES: usize = 38_797_312;

/// How `WorkerPlan` converts the memory budget into a worker count.
///
/// The default is `M8`, the measured model. The owner took that decision after
/// M8 was independently verified: the `Buffers` model licenses 20 workers when
/// 6 GiB pays for 16, which is a planner error rather than a tuning preference,
/// and both models produce byte-identical output. `Buffers` stays reachable via
/// `--memory-model buffers` so the two can be compared.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, clap::ValueEnum)]
pub enum MemoryModel {
    /// Sum of the per-worker buffers, and nothing else. MEASURED (M2, M8) to
    /// under-count peak RSS by 12% per worker, and to omit both the process
    /// floor and the reduce tree entirely. Kept for comparison only.
    Buffers,
    /// Buffers + measured decoder scratch + the rayon reduce tree + the process
    /// floor. The default. Out-of-sample error 8.4% mean / 17.5% max, against
    /// 12.0% / 25.2% for `Buffers`.
    #[default]
    M8,
}

/// Levels of a binary reduce over `chunks` items, i.e. `ceil(log2(chunks))`.
/// MEASURED (M8): each level holds one more `Selection` alive, in exact 110.04
/// MiB steps at N = 1, 2, 3, 4, 6, 8 on a single thread.
fn reduce_levels(chunks: usize) -> usize {
    if chunks <= 1 {
        0
    } else {
        (chunks - 1).ilog2() as usize + 1
    }
}

/// M8's predicted peak RSS: a process floor, `live` workers each holding their
/// buffers plus the decoder's scratch, and one `Selection` per level of the
/// reduce tree. Out-of-sample error on a stack never used to fit it: mean 8.4%,
/// max 17.5%, against a run-to-run spread of up to 7.3%.
fn m8_peak_bytes(chunks: usize, live: usize, px: usize, per_worker_bytes: usize) -> usize {
    PROCESS_FLOOR_BYTES
        + live * (per_worker_bytes + DECODER_SCRATCH_BYTES)
        + reduce_levels(chunks) * px * 14
}

/// The same model at full overlap, which is the case the planner has to pay
/// for: every chunk live at once.
fn m8_predicted_peak_bytes(chunks: usize, px: usize, per_worker_bytes: usize) -> usize {
    m8_peak_bytes(chunks, chunks, px, per_worker_bytes)
}

/// The largest worker count whose M8-predicted peak still fits the budget.
/// Searched rather than divided, because the reduce-tree term is not linear.
fn m8_worker_cap(px: usize, per_worker_bytes: usize) -> usize {
    let mut workers = 1;
    while m8_predicted_peak_bytes(workers + 1, px, per_worker_bytes) <= MEMORY_BUDGET_BYTES {
        workers += 1;
    }
    workers
}

/// A winner index this far from its 3x3 neighbourhood median is counted as
/// speckle rather than depth structure.
///
/// Re-exported from core rather than defined here so that this number and the
/// merge's speckle companion are the same number by construction. They are
/// quoted against each other; two copies could drift.
use strehl_core::stack::DEFAULT_SPECKLE_TOLERANCE as SPECKLE_TOLERANCE;

/// The tolerance this command actually passed to `speckle_fraction`.
///
/// Exists so `merge_cmd`'s companion-metric test can assert the two commands
/// quote the same number, rather than asserting it against a literal that could
/// be changed in one place.
#[cfg(test)]
pub fn speckle_tolerance_in_use() -> u16 {
    SPECKLE_TOLERANCE
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Roi {
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}

pub fn parse_roi(s: &str) -> std::result::Result<Roi, String> {
    let parts: Vec<&str> = s.split(',').map(str::trim).collect();
    if parts.len() != 4 {
        return Err(format!("expected X,Y,W,H, got {s:?}"));
    }
    let v: std::result::Result<Vec<usize>, _> = parts.iter().map(|p| p.parse::<usize>()).collect();
    let v = v.map_err(|e| format!("{s:?}: {e}"))?;
    if v[2] == 0 || v[3] == 0 {
        return Err(format!("{s:?}: width and height must be non-zero"));
    }
    Ok(Roi {
        x: v[0],
        y: v[1],
        width: v[2],
        height: v[3],
    })
}

pub struct StackOptions {
    pub dir: PathBuf,
    pub out: PathBuf,
    pub limit: Option<usize>,
    pub srgb: bool,
    /// Emit at full sensor resolution instead of binning each 2x2 quad to one
    /// pixel. Defaults ON with `--srgb` and OFF otherwise, exactly as in
    /// `stack`, so the byte-frozen measurement path is never reached by a
    /// default. See the demosaic branch in `write_selected` for why the two
    /// subcommands must agree on this.
    pub demosaic: bool,
    pub index_map: Option<PathBuf>,
    pub flat_roi: Option<Roi>,
    pub memory_model: MemoryModel,
    /// Stops of linear gain before the sRGB curve; `0.0` is the identity and is
    /// the default, so the byte-frozen measurement path never multiplies.
    pub exposure: f32,
    /// Choose the gain from the image instead. Mutually exclusive with a
    /// non-zero `exposure`; both require `srgb`.
    pub auto_exposure: bool,
}

pub fn run(opts: &StackOptions) -> Result<()> {
    // Refuse an impossible exposure request before decoding 299 frames, exactly
    // as `merge_cmd::run` does. `write_outputs` resolves it again where it is
    // used; resolution is pure, so the two cannot disagree.
    Exposure::resolve(opts.srgb, opts.exposure, opts.auto_exposure)?;
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

    // One frame up front, for geometry, levels, camera and ISO. The noise model
    // is built once here and injected; AGENTS.md rule 3 forbids any stage
    // deriving its own.
    let t_prologue = Instant::now();
    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let prologue_secs = t_prologue.elapsed().as_secs_f64();

    let geom = first.geometry();
    let levels = first.levels;
    let camera = first.camera.clone();
    let iso = first.iso;
    let wb = first.wb_gains();
    // Consumed only by the output path; see `Frame::xyz_to_cam_rgb`.
    let xyz_to_cam = first.xyz_to_cam_rgb_with_source();
    let frame_bytes = first.allocated_bytes();
    drop(first);

    let noise = profile::noise_model_for(&camera, iso, levels);
    let middle = (paths.len() / 2) as u16;

    if let Some(roi) = opts.flat_roi {
        ensure!(
            roi.x + roi.width <= geom.width && roi.y + roi.height <= geom.height,
            "--flat-roi {},{},{},{} does not fit inside the {}x{} plane",
            roi.x,
            roi.y,
            roi.width,
            roi.height,
            geom.width,
            geom.height
        );
    }

    let plan = WorkerPlan::new(paths.len(), geom, frame_bytes, opts.memory_model);

    eprintln!(
        "strehl argmax-baseline -- naive per-pixel argmax (NOT THE DEFAULT; a negative control)"
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
    eprintln!(
        "white balance   : {}",
        wb.map(|g| format!("R {:.4}  G 1.0000  B {:.4} (green-normalised)", g[0], g[2]))
            .unwrap_or("UNAVAILABLE -- writing unbalanced linear output".into())
    );
    eprintln!("{}", provenance_line(&noise));
    eprintln!(
        "planes          : {} x {} per CFA plane (active {} x {} halved)",
        geom.width,
        geom.height,
        geom.width * 2,
        geom.height * 2
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
    let ctx = FoldContext {
        geom,
        levels,
        noise: &noise,
        middle,
        roi: opts.flat_roi,
        live: &live,
        peak_live: &peak_live,
    };

    let t0 = Instant::now();
    let merged = paths
        .par_chunks(plan.chunk_len)
        .enumerate()
        .map(|(chunk_index, chunk)| ctx.fold_chunk((chunk_index * plan.chunk_len) as u16, chunk))
        .reduce_with(|a, b| match (a, b) {
            (Ok(mut a), Ok(b)) => {
                a.absorb(b)?;
                Ok(a)
            }
            (Err(e), _) | (Ok(_), Err(e)) => Err(e),
        })
        .expect("at least one chunk")?;
    let stack_secs = t0.elapsed().as_secs_f64();

    let n = merged.selection.frames_folded() as f64;
    ensure!(
        merged.selection.frames_folded() as usize == paths.len(),
        "folded {} frames, expected {}",
        merged.selection.frames_folded(),
        paths.len()
    );

    eprintln!("--- throughput (MEASURED) ---");
    eprintln!("wall clock      : {stack_secs:.3} s  (+{prologue_secs:.3} s prologue frame)");
    eprintln!("per frame       : {:.1} ms", 1000.0 * stack_secs / n);
    eprintln!(
        "throughput      : {:.1} MB/s over {:.1} MB of ARW",
        input_bytes as f64 / 1e6 / stack_secs,
        input_bytes as f64 / 1e6
    );
    eprintln!(
        "  decode        : {:.3} s summed across workers ({:.1} ms/frame)",
        merged.decode_secs,
        1000.0 * merged.decode_secs / n
    );
    eprintln!(
        "  focus + fold  : {:.3} s summed across workers ({:.1} ms/frame)",
        merged.fold_secs,
        1000.0 * merged.fold_secs / n
    );
    eprintln!(
        "in-flight frames: {} peak, bound {} (never O(N))",
        peak_live.load(Ordering::Relaxed),
        plan.chunks
    );
    eprintln!();

    report_winners(&merged.selection);

    let t_speckle = Instant::now();
    let speckle = speckle_fraction(merged.selection.index(), geom, SPECKLE_TOLERANCE);
    eprintln!("--- argmax defect (MEASURED) ---");
    eprintln!(
        "index speckle   : {:.3}% of pixels differ by more than {} from their 3x3 median index",
        100.0 * speckle,
        SPECKLE_TOLERANCE
    );
    eprintln!(
        "                  (depth is piecewise smooth, so this is argmax electing noise; {:.2} s to compute)",
        t_speckle.elapsed().as_secs_f64()
    );

    if let Some(roi) = opts.flat_roi {
        report_flat_roi(&merged, roi, geom, levels, &noise, middle)?;
    } else {
        eprintln!(
            "flat ROI        : not requested. Pass --flat-roi X,Y,W,H to measure the noise penalty."
        );
    }
    eprintln!();

    let t_write = Instant::now();
    write_outputs(&merged.selection, levels, wb, xyz_to_cam.as_ref(), opts)?;
    eprintln!("write           : {:.3} s", t_write.elapsed().as_secs_f64());

    Ok(())
}

/// The one line that tells a user how much to trust every number under it.
///
/// **This string is a claim about `strehl_core::profile`, so it goes stale when
/// that module is corrected and nothing here changes.** It already did once:
/// commit `2a4f5c5` fixed the ISO-50 gain and rewrote `profile.rs`'s doc
/// comment to record that the gain relation now has a photon-transfer curve
/// behind it, while this line went on telling every user the opposite —
/// "DERIVED from white-level consistency, not a photon-transfer measurement" —
/// on every run of both subcommands. If `profile.rs` changes what it claims,
/// this changes with it.
pub(crate) fn provenance_line(noise: &NoiseModel) -> String {
    match noise.provenance {
        // Wording tracks `profile.rs`'s own doc comments rather than
        // paraphrasing them: `gain_divisor` ("the PTC now exists and the
        // relation survives it at true gain steps"), `base_iso` ("MEASURED
        // twice, independently" + question 126's unlocated boundary), and
        // `read_noise_e_low`/`_high` (dark frames, with a shape error the
        // module asserts rather than hides).
        //
        // The boundary citation is `SYNTHESIS question 126`, not "fact 200a".
        // `200a` is a report-local sub-item at `M25-simulator-measured.md:858`
        // and folded into SYNTHESIS as a *question*, so it has no fact number
        // and a reader who went looking for one found nothing (fact 717). The
        // claim itself is true and unchanged; only the label was unresolvable.
        //
        // `profile.rs`'s own `base_iso` doc carries the same resolution in a
        // longer form that keeps M25's provenance. That form is right for a doc
        // comment and wrong here: this string is printed to a *user*, who has
        // no access to the M25 report and can only follow a SYNTHESIS number.
        Provenance::Profile => format!(
            concat!(
                "noise model     : PROVENANCE=Profile -- camera profile at ISO {:.0}. ",
                "Trustworthy for ranking.\n",
                "                  GAIN: anchored by a PHOTON-TRANSFER MEASUREMENT on signal ",
                "(M25 fact 200,\n",
                "                  SYNTHESIS fact 550). The divisor was originally DERIVED by ",
                "reproducing the\n",
                "                  camera's own white level, which checks one relation and is ",
                "not a PTC; the\n",
                "                  PTC now exists and the relation survives it at true gain ",
                "steps -- the ISO 160\n",
                "                  control measures 0.3273 DN/e- against the relation's 0.3663, ",
                "10.7% low.\n",
                "                  READ NOISE: not photon-transfer measured. DERIVED from dark ",
                "frames, and below\n",
                "                  ISO 400 it carries a shape error `profile.rs` asserts rather ",
                "than hides.\n",
                "                  This is a PROFILE, NOT A PER-BODY CALIBRATION: the constants ",
                "describe the\n",
                "                  camera MODEL and nothing here was fitted from this stack. ",
                "Below the profile's\n",
                "                  base ISO the sensor reads out at base-ISO gain (extended/pull ",
                "ISO); that floor\n",
                "                  is measured, but the ISO at which it starts is not (SYNTHESIS ",
                "question 126\n",
                "                  -- the corpus holds no ISO 64 or 80 capture)."
            ),
            noise.iso
        ),
        Provenance::Measured => format!(
            "noise model     : PROVENANCE=Measured -- fitted from this stack at ISO {:.0}.",
            noise.iso
        ),
        Provenance::Fallback => concat!(
            "noise model     : PROVENANCE=Fallback -- NO CALIBRATION. Unity gain and 4 e- read ",
            "noise were guessed because the body is unprofiled or the file reported no ISO. ",
            "Every number below is untrustworthy."
        )
        .to_string(),
    }
}

/// How the stack is split across workers, and why.
struct WorkerPlan {
    workers: usize,
    chunks: usize,
    chunk_len: usize,
    per_worker_bytes: usize,
    px: usize,
    model: MemoryModel,
}

impl WorkerPlan {
    fn new(frames: usize, geom: PlaneGeometry, frame_bytes: usize, model: MemoryModel) -> Self {
        // Selection is f32 focus + 4 u16 channels + u16 index; FocusField is
        // three f32 planes (gradient, box scratch, focus -- unchanged by M14's
        // move from the ring difference to Tenengrad); luma is one more.
        let px = geom.pixels();
        let per_worker_bytes = px * (14 + 12 + 4) + frame_bytes;
        let by_memory = match model {
            MemoryModel::Buffers => (MEMORY_BUDGET_BYTES / per_worker_bytes).max(1),
            MemoryModel::M8 => m8_worker_cap(px, per_worker_bytes),
        };
        let by_cpu = std::thread::available_parallelism()
            .map(|v| v.get())
            .unwrap_or(1);
        let workers = by_memory.min(by_cpu).min(frames);
        let chunk_len = frames.div_ceil(workers);
        Self {
            workers,
            chunks: frames.div_ceil(chunk_len),
            chunk_len,
            per_worker_bytes,
            px,
            model,
        }
    }

    /// What the buffer model alone accounts for. A lower bound, and known to be
    /// one: it omits the process floor, the decoder's scratch, and the reduce
    /// tree.
    fn buffers_only_bytes(&self) -> usize {
        self.chunks * self.per_worker_bytes
    }

    fn describe(&self) -> String {
        format!(
            "workers         : {} chunks of <= {} frames ({} allowed by the {} MB budget, {} by CPU, \
             model {:?})\n\
             working set     : {:.0} MB/worker buffers, >= {:.2} GB peak (LOWER BOUND -- buffers \
             only)\n\
             predicted peak  : {:.2} GB (MEASURED model, M8: + {:.0} MB/worker decoder scratch, \
             + {} x {:.0} MB reduce tree, + {:.0} MB floor; +/-8.4% out of sample)",
            self.chunks,
            self.chunk_len,
            self.workers,
            MEMORY_BUDGET_BYTES / (1 << 20),
            std::thread::available_parallelism()
                .map(|v| v.get())
                .unwrap_or(1),
            self.model,
            self.per_worker_bytes as f64 / 1e6,
            self.buffers_only_bytes() as f64 / 1e9,
            m8_predicted_peak_bytes(self.chunks, self.px, self.per_worker_bytes) as f64 / 1e9,
            DECODER_SCRATCH_BYTES as f64 / 1e6,
            reduce_levels(self.chunks),
            (self.px * 14) as f64 / 1e6,
            PROCESS_FLOOR_BYTES as f64 / 1e6,
        )
    }
}

/// One worker's partial result.
struct Partial {
    selection: Selection,
    /// Black-subtracted green over the flat ROI, from the middle frame, kept by
    /// whichever worker happened to decode it. Feeds the LEGACY raw ratio only.
    middle_roi: Option<Vec<f32>>,
    /// `(frame index, that frame's flat-ROI moments)` for **every** frame, not
    /// just the middle one. Three `f64` per frame, so it is constant in the ROI
    /// size and irrelevant to the memory ratchet, and it is what makes fact
    /// 441's privileged-denominator defect unrepresentable.
    flat_frames: Vec<(u16, FrameFlat)>,
    decode_secs: f64,
    fold_secs: f64,
}

impl Partial {
    fn absorb(&mut self, other: Partial) -> Result<()> {
        self.selection.absorb(&other.selection)?;
        if self.middle_roi.is_none() {
            self.middle_roi = other.middle_roi;
        }
        self.flat_frames.extend(other.flat_frames);
        self.decode_secs += other.decode_secs;
        self.fold_secs += other.fold_secs;
        Ok(())
    }
}

/// Everything a worker needs that is the same for every worker. The noise model
/// is borrowed, never cloned per worker — it is injected exactly once
/// (`AGENTS.md` rule 3).
struct FoldContext<'a> {
    geom: PlaneGeometry,
    levels: Levels,
    noise: &'a NoiseModel,
    middle: u16,
    roi: Option<Roi>,
    live: &'a AtomicUsize,
    peak_live: &'a AtomicUsize,
}

impl FoldContext<'_> {
    fn fold_chunk(&self, first_index: u16, chunk: &[PathBuf]) -> Result<Partial> {
        let mut selection = Selection::new(self.geom);
        let mut field = FocusField::new(self.geom);
        let mut luma = vec![0.0f32; self.geom.pixels()];
        let mut middle_roi = None;
        let mut flat_frames = Vec::with_capacity(chunk.len());
        let (mut decode_secs, mut fold_secs) = (0.0, 0.0);

        for (offset, path) in chunk.iter().enumerate() {
            let index = first_index + offset as u16;

            let t = Instant::now();
            let in_flight = self.live.fetch_add(1, Ordering::Relaxed) + 1;
            self.peak_live.fetch_max(in_flight, Ordering::Relaxed);
            let frame = match strehl_raw::decode(path) {
                Ok(f) => f,
                Err(e) => {
                    self.live.fetch_sub(1, Ordering::Relaxed);
                    return Err(e).with_context(|| format!("frame {index}"));
                }
            };
            decode_secs += t.elapsed().as_secs_f64();

            let t = Instant::now();
            let result = self.fold_one(
                &mut selection,
                &mut field,
                &mut luma,
                index,
                &frame,
                &mut middle_roi,
                &mut flat_frames,
            );
            // Explicit: the frame is gone before the next decode starts. This
            // is the whole memory argument.
            drop(frame);
            self.live.fetch_sub(1, Ordering::Relaxed);
            fold_secs += t.elapsed().as_secs_f64();
            result?;
        }

        Ok(Partial {
            selection,
            middle_roi,
            flat_frames,
            decode_secs,
            fold_secs,
        })
    }

    #[allow(clippy::too_many_arguments)]
    fn fold_one(
        &self,
        selection: &mut Selection,
        field: &mut FocusField,
        luma: &mut [f32],
        index: u16,
        frame: &Frame,
        middle_roi: &mut Option<Vec<f32>>,
        flat_frames: &mut Vec<(u16, FrameFlat)>,
    ) -> Result<()> {
        if frame.levels != self.levels {
            bail!(
                "frame {index} ({}) has levels black {} white {}, but the stack was calibrated at black {} white {}",
                frame.path.display(),
                frame.levels.black,
                frame.levels.white,
                self.levels.black,
                self.levels.white
            );
        }
        green_luma(frame, self.levels.black, luma);
        field.compute(luma, self.noise);
        selection
            .fold(index, frame, field.values())
            .map_err(|e| match e {
                Error::DimensionMismatch { got, want, .. } => anyhow::anyhow!(
                    "frame {index} ({}) has plane geometry {got:?}, expected {want:?}",
                    frame.path.display()
                ),
                other => anyhow::anyhow!(other),
            })?;
        if let Some(roi) = self.roi {
            // Every frame, not only the middle one: the reference for the noise
            // invariant is the distribution, and a distribution needs all of it.
            let g = roi_green(frame, roi, self.levels.black);
            flat_frames.push((index, flat_ratio::frame_flat(&g, roi.width, roi.height)));
            if index == self.middle {
                *middle_roi = Some(g);
            }
        }
        Ok(())
    }
}

/// Black-subtracted `(G1 + G2) / 2` over an ROI in plane coordinates.
pub(crate) fn roi_green(frame: &Frame, roi: Roi, black: f32) -> Vec<f32> {
    let (g1x, g1y) = CfaPlane::G1.rggb_offset();
    let (g2x, g2y) = CfaPlane::G2.rggb_offset();
    let mut out = Vec::with_capacity(roi.width * roi.height);
    for py in roi.y..roi.y + roi.height {
        let (row0, row1) = frame.quad_rows(py);
        let g1_row = if g1y == 0 { row0 } else { row1 };
        let g2_row = if g2y == 0 { row0 } else { row1 };
        for px in roi.x..roi.x + roi.width {
            let g1 = g1_row[2 * px + g1x] as f32 - black;
            let g2 = g2_row[2 * px + g2x] as f32 - black;
            out.push(0.5 * (g1 + g2));
        }
    }
    out
}

pub(crate) fn mean_and_sigma(v: &[f32]) -> (f64, f64) {
    if v.is_empty() {
        return (0.0, 0.0);
    }
    let n = v.len() as f64;
    let mean = v.iter().map(|x| *x as f64).sum::<f64>() / n;
    let var = v.iter().map(|x| (*x as f64 - mean).powi(2)).sum::<f64>() / n;
    (mean, var.sqrt())
}

fn report_winners(selection: &Selection) {
    let frames = selection.frames_folded() as usize;
    let mut hist = vec![0u64; frames];
    for i in selection.index() {
        hist[*i as usize] += 1;
    }
    let total = selection.geometry().pixels() as f64;
    eprintln!("--- winner distribution ---");
    if frames <= 40 {
        for (k, count) in hist.iter().enumerate() {
            let pct = 100.0 * *count as f64 / total;
            let bar = "#".repeat((pct * 0.8).round() as usize);
            eprintln!("  frame {k:>3} : {pct:6.2}%  {bar}");
        }
    } else {
        let won = hist.iter().filter(|c| **c > 0).count();
        eprintln!("  {won} of {frames} frames won at least one pixel");
    }
    eprintln!();
}

/// The numbers behind the headline ratio.
///
/// Split out from the reporting because the ratio is the number the whole
/// milestone rests on and it had no regression test of its own — the 52 library
/// tests all exercised synthetic units, and an independent re-derivation is not
/// a substitute for covering the code that actually produced the figure
/// (`AGENTS.md` rule 11). `report_flat_roi` is now printing only.
/// Anything that can be asked for a merged green value and a per-pixel winner
/// index over a plane.
///
/// This exists so that [`flat_roi_stats`] has exactly one implementation. The
/// argmax baseline's ratio and the estimation merge's ratio have to
/// be produced by the same arithmetic on the same ROI or the comparison is
/// worthless — M35 lost an afternoon to two harnesses that differed by a
/// convention, and discipline 210 is the rule that came out of it.
///
/// The baseline number is **1.0678x unregularised / 1.0739x regularised** on
/// the shipped operator (fact 343), not fact 19's 1.253x, which was measured on
/// a different operator and does not reproduce here.
pub(crate) trait GreenField {
    fn green_mean_at(&self, i: usize) -> f32;
    fn winner_index(&self) -> &[u16];
}

impl GreenField for Selection {
    fn green_mean_at(&self, i: usize) -> f32 {
        self.green_mean(i)
    }
    fn winner_index(&self) -> &[u16] {
        self.index()
    }
}

impl GreenField for strehl_core::merge::Estimator {
    fn green_mean_at(&self, i: usize) -> f32 {
        self.green_mean(i)
    }
    fn winner_index(&self) -> &[u16] {
        self.best_index()
    }
}

pub(crate) struct FlatRoiStats {
    pub pixels: usize,
    pub stacked_mean: f64,
    pub stacked_sigma: f64,
    pub single_mean: f64,
    pub single_sigma: f64,
    /// **LEGACY, structure-dominated. Not a noise measurement.**
    ///
    /// `stacked_sigma / single_sigma`: two RAW spatial sds. Retained so that
    /// every number the corpus published against it stays readable, and for no
    /// other purpose. Fact 469 measured it under-reporting a real noise
    /// explosion by 6.3x, because on a real "flat" ROI ~99 % of the raw
    /// variance is residual scene (76.272 DN raw against a modelled 8.77 DN).
    /// Use [`FlatRoiStats::stacked_hp_sd`] against a
    /// [`strehl_core::flat_ratio::FlatReference`] instead.
    pub legacy_raw_ratio: f64,
    /// High-pass residual sd of the merged ROI, DN. The noise statistic.
    /// `None` when the ROI is smaller than one high-pass box.
    pub stacked_hp_sd: Option<f64>,
    /// High-pass residual sd of `middle_roi`, DN. One frame, so it is only a
    /// like-for-like partner for the legacy column; the reference a ratio
    /// should be taken against is the whole per-frame distribution (fact 441).
    pub single_hp_sd: Option<f64>,
    pub distinct_winners: usize,
    pub median_winner: u16,
}

pub(crate) fn flat_roi_stats<F: GreenField + ?Sized>(
    field: &F,
    middle_roi: &[f32],
    roi: Roi,
    geom: PlaneGeometry,
    black: f32,
) -> FlatRoiStats {
    let stacked: Vec<f32> = (roi.y..roi.y + roi.height)
        .flat_map(|py| (roi.x..roi.x + roi.width).map(move |px| (px, py)))
        .map(|(px, py)| field.green_mean_at(geom.index(px, py)) - black)
        .collect();

    let (stacked_mean, stacked_sigma) = mean_and_sigma(&stacked);
    let (single_mean, single_sigma) = mean_and_sigma(middle_roi);

    let mut roi_index: Vec<u16> = (roi.y..roi.y + roi.height)
        .flat_map(|py| (roi.x..roi.x + roi.width).map(move |px| (px, py)))
        .map(|(px, py)| field.winner_index()[geom.index(px, py)])
        .collect();
    roi_index.sort_unstable();
    let median_winner = roi_index[roi_index.len() / 2];
    roi_index.dedup();

    FlatRoiStats {
        pixels: stacked.len(),
        stacked_mean,
        stacked_sigma,
        single_mean,
        single_sigma,
        legacy_raw_ratio: stacked_sigma / single_sigma,
        stacked_hp_sd: flat_ratio::highpass_sd(&stacked, roi.width, roi.height),
        single_hp_sd: flat_ratio::highpass_sd(middle_roi, roi.width, roi.height),
        distinct_winners: roi_index.len(),
        median_winner,
    }
}

/// The lines that turn a high-pass sd into a readable acceptance verdict.
///
/// Shared by `strehl stack` and `strehl merge` so the two subcommands cannot
/// drift into printing two different invariants (discipline 210). `indent` is
/// the continuation prefix each caller already uses.
pub(crate) fn report_hp_reference(
    reference: &flat_ratio::FlatReference,
    model_sigma: f64,
    indent: &str,
) {
    let contamination = flat_ratio::structure_contamination(reference.median(), model_sigma);
    eprintln!(
        "reference hp sd : median {:8.3} DN over {} frames   \
         min {:8.3} (frame {})   max {:8.3} (frame {})",
        reference.median(),
        reference.frames(),
        reference.min(),
        reference.min_frame(),
        reference.max(),
        reference.max_frame()
    );
    eprintln!(
        "{indent}NO SINGLE REFERENCE FRAME. Fact 441: holding the merge fixed and \
         sweeping which"
    );
    eprintln!(
        "{indent}frame supplies the denominator moved the old published ratio over a \
         1.60x range,"
    );
    eprintln!(
        "{indent}so the whole distribution is carried. This stack's own spread is \
         {:.4}x.",
        reference.spread()
    );
    eprintln!(
        "{indent}high pass is x - box{}(x) on the ROI's valid interior, the kernel \
         behind fact 469;",
        flat_ratio::HP_BOX_SIDE
    );
    eprintln!(
        "{indent}white noise of sd s comes out at s * {:.6} (DERIVED: sqrt(1 - 1/{})), \
         so the",
        flat_ratio::HP_NOISE_GAIN,
        flat_ratio::HP_BOX_SIDE * flat_ratio::HP_BOX_SIDE
    );
    eprintln!(
        "{indent}sd above reads against the calibrated model rather than in arbitrary \
         units."
    );
    eprintln!(
        "{indent}STRUCTURE FLOOR: median hp sd is {contamination:.4}x the model's \
         per-sample sigma."
    );
    eprintln!(
        "{indent}Rule 10 -- that is a SPATIAL sd over a TEMPORAL sigma, so it is a \
         one-sided"
    );
    eprintln!(
        "{indent}reading, not an equality: 1.0000x means noise-dominated and the excess \
         is"
    );
    eprintln!(
        "{indent}residual scene. IT IS ALSO THE FACTOR BY WHICH EVERY RATIO BELOW \
         UNDER-REPORTS A"
    );
    eprintln!(
        "{indent}LARGE EXPLOSION, so these ratios are LOWER BOUNDS. The legacy raw ratio's \
         own"
    );
    eprintln!(
        "{indent}floor on this ROI is raw sd / sigma, printed above, and it is the 6.3x \
         of fact 469."
    );
}

fn report_flat_roi(
    merged: &Partial,
    roi: Roi,
    geom: PlaneGeometry,
    levels: Levels,
    noise: &NoiseModel,
    middle: u16,
) -> Result<()> {
    let single = merged
        .middle_roi
        .as_ref()
        .context("the middle frame's ROI was never captured")?;
    let s = flat_roi_stats(&merged.selection, single, roi, geom, levels.black);

    eprintln!();
    eprintln!("--- flat-ROI noise control (MEASURED) ---");
    eprintln!(
        "roi             : x {} y {} w {} h {} in plane coordinates ({} px)",
        roi.x, roi.y, roi.width, roi.height, s.pixels
    );
    eprintln!(
        "stacked green   : sigma {:8.3} DN   mean {:9.2} DN   (argmax over {} frames)",
        s.stacked_sigma,
        s.stacked_mean,
        merged.selection.frames_folded()
    );
    eprintln!(
        "single frame {middle:<3}: sigma {:8.3} DN   mean {:9.2} DN   (no stacking at all)",
        s.single_sigma, s.single_mean
    );
    eprintln!(
        "model predicts  : sigma {:8.3} DN for one green-luma sample at that level",
        noise.green_luma_sigma(s.single_mean as f32)
    );
    eprintln!(
        "                  that is a TEMPORAL per-sample sigma; the two above are SPATIAL sds"
    );
    eprintln!(
        "                  of noise plus whatever scene structure the ROI still has, so they"
    );
    eprintln!("                  are not the same quantity and are not expected to match.");
    let model_sigma = f64::from(noise.green_luma_sigma(s.single_mean as f32));

    // ---- the noise statistic ------------------------------------------------
    let per_frame: Vec<(u16, f64)> = merged
        .flat_frames
        .iter()
        .filter_map(|(i, f)| f.hp_sd.map(|v| (*i, v)))
        .collect();
    match (flat_ratio::FlatReference::new(&per_frame), s.stacked_hp_sd) {
        (Some(reference), Some(stacked_hp)) => {
            eprintln!();
            eprintln!(
                "stacked hp sd   : {stacked_hp:8.3} DN   (argmax over {} frames)",
                merged.selection.frames_folded()
            );
            report_hp_reference(&reference, model_sigma, "                  ");
            let r = reference.ratio(stacked_hp);
            eprintln!(
                "HP RATIO        : {:.3}x vs the median frame   [{:.3}x .. {:.3}x] over every \
                 frame",
                r.median, r.lo, r.hi
            );
            if let Some(d) = s.single_hp_sd {
                // What the old privileged-denominator convention would have
                // printed, in the same units, so fact 441 is visible as a
                // difference and not only as an interval.
                eprintln!(
                    "                  against frame {middle} alone -- the frame the old \
                     convention privileged --"
                );
                eprintln!(
                    "                  the same statistic reads {:.3}x.",
                    stacked_hp / d
                );
            }
            eprintln!(
                "                  ABOVE 1.0 MEANS THE STACK IS NOISIER THAN ONE UNSTACKED \
                 FRAME."
            );
        }
        _ => {
            eprintln!();
            eprintln!(
                "HP RATIO        : NOT AVAILABLE -- the ROI is smaller than one {}x{} high-pass \
                 box.",
                flat_ratio::HP_BOX_SIDE,
                flat_ratio::HP_BOX_SIDE
            );
        }
    }

    // ---- the number this replaced, kept readable ----------------------------
    eprintln!();
    eprintln!(
        "LEGACY RAW RATIO: {:.3}x  -- DO NOT READ AS NOISE.",
        s.legacy_raw_ratio
    );
    eprintln!("                  Two RAW spatial sds. Fact 469: on a real flat ROI ~99% of that");
    eprintln!(
        "                  variance is residual scene, and this ratio under-reported a \
         planted"
    );
    eprintln!("                  noise explosion by 6.3x. Printed only so older reports remain");
    eprintln!("                  comparable. The HP RATIO above is the acceptance number.");
    eprintln!(
        "winners in roi  : {} distinct frames, median {}",
        s.distinct_winners, s.median_winner
    );
    Ok(())
}

pub(crate) fn srgb_encode(v: f32) -> f32 {
    if v <= 0.003_130_8 {
        12.92 * v
    } else {
        1.055 * v.powf(1.0 / 2.4) - 0.055
    }
}

fn write_outputs(
    selection: &Selection,
    levels: Levels,
    wb: Option<[f32; 3]>,
    xyz_to_cam: Option<&([[f32; 3]; 3], String)>,
    opts: &StackOptions,
) -> Result<()> {
    let geom = selection.geometry();
    let n = geom.pixels();
    let range = levels.range();
    ensure!(range > 0.0, "white level is not above black level");
    let gains = wb.unwrap_or([1.0, 1.0, 1.0]);

    // As in `merge_cmd::write_merged`: the colour matrix rides with `--srgb`,
    // and the default linear path stays byte-frozen for the corpus (M85).
    let matrix = if opts.srgb {
        xyz_to_cam.and_then(|(m, _)| strehl_core::color::camera_to_srgb(*m))
    } else {
        None
    };
    if opts.srgb {
        match (matrix, xyz_to_cam) {
            (Some(_), Some((_, src))) => {
                eprintln!(
                    "colour          : camera RGB -> sRGB (BT.709 primaries, D65), from {src}"
                );
            }
            _ => {
                eprintln!(
                    "colour          : no usable camera characterisation; emitting CAMERA-NATIVE RGB."
                );
            }
        }
    }

    let r = selection.plane(CfaPlane::R);
    let b = selection.plane(CfaPlane::B);

    // Exposure, chosen and applied exactly as `merge_cmd::write_merged` does:
    // the statistic is always taken on the BINNED quad grid even under
    // --demosaic, so an interpolation cannot move the gain (M100). It is read
    // through the un-ceilinged matrix on purpose -- see `display_luminance`.
    let exposure = Exposure::resolve(opts.srgb, opts.exposure, opts.auto_exposure)?;
    let applied = match exposure {
        Exposure::None => AppliedExposure::IDENTITY,
        Exposure::Stops(stops) => AppliedExposure {
            stops,
            automatic: false,
        },
        Exposure::Auto => {
            let pre = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain / range;
            let mut luma: Vec<f32> = (0..n)
                .map(|i| {
                    color::display_luminance(
                        [
                            pre(r[i] as f32, gains[0]),
                            pre(selection.green_mean(i), gains[1]),
                            pre(b[i] as f32, gains[2]),
                        ],
                        matrix.as_ref(),
                    )
                })
                .collect();
            color::choose_exposure(&mut luma).unwrap_or_else(|| {
                eprintln!(
                    "exposure        : --auto-exposure found no positive luminance; leaving it alone."
                );
                AppliedExposure::IDENTITY
            })
        }
    };
    if !applied.is_identity() || applied.automatic {
        eprintln!(
            "exposure        : {applied}, {}",
            if applied.automatic {
                "chosen from the image"
            } else {
                "as asked"
            }
        );
        if applied.automatic {
            eprintln!(
                "                  rule: linear-sRGB luma p{} -> {:.2} on the binned grid (M100).",
                color::AUTO_EXPOSURE_PERCENTILE,
                color::AUTO_EXPOSURE_TARGET
            );
            eprintln!(
                "                  reproduce this exact file with {}",
                applied.reproduce_flag()
            );
        }
    }

    // The matrix now carries the sensor's saturation ceiling (M109). Without it
    // the matrix is handed triples in which green is pinned at the container
    // maximum while white balance has carried red and blue past it, and blown
    // neutral white renders magenta. The ceiling scales with the exposure gain
    // for the same reason `norm` folds it: `clip_{K*g}(g*v) == g*clip_K(v)`.
    // See `docs/research/M109-highlights.md`.
    let matrix = matrix.map(|render| {
        render.with_ceiling(color::saturation_ceiling(levels, gains, applied.gain()))
    });
    let eg = applied.gain();

    if opts.demosaic {
        // Full resolution, mirroring `merge_cmd::write_merged`'s demosaic
        // branch. The argmax copies a whole 2x2 quad from the winning frame,
        // so all four CFA sites are already present -- this is pure
        // interleaving of data that was already there, not an inference, and
        // the selection itself is untouched.
        //
        // This branch exists because M104c measured an asymmetry that biased
        // the project's own comparison: `stack --srgb` emitted 7032 x 4688
        // while `argmax-baseline --srgb` still emitted 3516 x 2344. These two
        // subcommands exist to be compared against each other, magnification
        // reads as sharpness (discipline 606), and the bias ran TOWARD the
        // estimator and away from the baseline it is measured against.
        let (mw, mh) = (geom.width * 2, geom.height * 2);
        let mut mosaic = vec![0.0f32; mw * mh];
        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain * eg / range;
        let g1 = selection.plane(CfaPlane::G1);
        let g2 = selection.plane(CfaPlane::G2);
        for py in 0..geom.height {
            let (top, bot) = mosaic[py * 2 * mw..].split_at_mut(mw);
            for px in 0..geom.width {
                let i = py * geom.width + px;
                // RGGB, matching `CfaPlane::rggb_at`: R G1 on the even row,
                // G2 B on the odd one.
                top[px * 2] = norm(r[i] as f32, gains[0]);
                top[px * 2 + 1] = norm(g1[i] as f32, gains[1]);
                bot[px * 2] = norm(g2[i] as f32, gains[1]);
                bot[px * 2 + 1] = norm(b[i] as f32, gains[2]);
            }
        }
        // Route through `OutputSpace` rather than building a `Develop` by hand
        // so that `stack --srgb` gets the same photographic tone rendering as
        // `merge --srgb`. `matrix` is already `None` off the `--srgb` path
        // (L1008), so this is the identity for the byte-frozen linear output.
        let dev = image_out::OutputSpace::from_flags(opts.srgb, false)?.develop(matrix);
        image_out::write_demosaiced(&opts.out, mw, mh, &mosaic, &dev)?;
        eprintln!(
            "wrote           : {} ({mw} x {mh}, 16-bit RGB, {}, Malvar-He-Cutler demosaic)",
            opts.out.display(),
            dev.caveat()
        );
        eprintln!(
            "                  Full sensor resolution, matching `stack --srgb` so the two are"
        );
        eprintln!(
            "                  comparable. Interpolated -- do not measure resolution on it."
        );
    } else if let Some(m) = matrix {
        let norm = |raw: f32, gain: f32| ((raw - levels.black).max(0.0)) * gain * eg / range;
        let mut lin = vec![0.0f32; n * 3];
        let (pixels, _) = lin.as_chunks_mut::<3>();
        for (i, px) in pixels.iter_mut().enumerate() {
            px[0] = norm(r[i] as f32, gains[0]);
            px[1] = norm(selection.green_mean(i), gains[1]);
            px[2] = norm(b[i] as f32, gains[2]);
        }
        // As above: `matrix` is `Some` only on the `--srgb` path, so the space
        // this resolves to is always `Srgb` here.
        let dev = image_out::OutputSpace::from_flags(opts.srgb, false)?.develop(Some(m));
        image_out::write_binned(&opts.out, geom.width, geom.height, &lin, &dev)?;
        eprintln!(
            "wrote           : {} ({} x {}, 16-bit RGB, {}, binned from one 2x2 quad per pixel -- NOT demosaiced)",
            opts.out.display(),
            geom.width,
            geom.height,
            dev.caveat()
        );
    } else {
        // ------------------------------------------------------------------
        // The measurement path. **Byte-frozen.** See the note on the same
        // branch in `merge_cmd::write_merged`.
        // ------------------------------------------------------------------
        let encode = |raw: f32, gain: f32| -> u16 {
            let v = ((raw - levels.black).max(0.0) * gain / range).min(1.0);
            let v = if opts.srgb { srgb_encode(v) } else { v };
            (v * u16::MAX as f32 + 0.5) as u16
        };
        let mut rgb = vec![0u16; n * 3];
        let (pixels, _) = rgb.as_chunks_mut::<3>();
        for (i, px) in pixels.iter_mut().enumerate() {
            px[0] = encode(r[i] as f32, gains[0]);
            px[1] = encode(selection.green_mean(i), gains[1]);
            px[2] = encode(b[i] as f32, gains[2]);
        }
        image_out::write_rgb16(&opts.out, geom.width as u32, geom.height as u32, &rgb)?;
        eprintln!(
            "wrote           : {} ({} x {}, 16-bit RGB, {}, binned from one 2x2 quad per pixel -- NOT demosaiced)",
            opts.out.display(),
            geom.width,
            geom.height,
            if opts.srgb {
                "camera-native RGB with an sRGB transfer curve"
            } else {
                "linear camera-native RGB"
            }
        );
    }

    if let Some(path) = &opts.index_map {
        ensure!(
            (0..n).all(|i| selection.is_decided(i)),
            "some pixels were never decided; the index map would be meaningless"
        );
        image_out::write_gray16(
            path,
            geom.width as u32,
            geom.height as u32,
            selection.index(),
        )?;
        eprintln!(
            "wrote           : {} ({} x {}, 16-bit gray, literal frame index 0..{} -- autoscale to view)",
            path.display(),
            geom.width,
            geom.height,
            selection.frames_folded().saturating_sub(1)
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// **Every citation this binary prints must be resolvable by the person
    /// reading it**, and the only documents that person can reach are
    /// `SYNTHESIS.md` and the source. Report-local labels are not resolvable.
    ///
    /// This is the regression pin for fact 717. `provenance_line` printed
    /// "(fact 200a -- the corpus holds no ISO 64 or 80 capture)" on every
    /// `stack` and `merge` run. `200a` is a sub-item of `M25-simulator-
    /// measured.md:858` and folded into SYNTHESIS as **question 126**; it has
    /// no fact number, so a reader who searched for one found nothing. The
    /// claim was and remains true — only the label was dangling.
    ///
    /// Rule 35: the subject is the rendered string and the object is a
    /// *pattern class* ("no `fact <digits><letter>` token"), not another copy
    /// of the same literal. An edit that reintroduced any report-local
    /// sub-item label, not merely `200a`, fails this.
    ///
    /// Rule 36: the fixture asserts it actually reached the interesting branch
    /// — the `Profile` arm is the only one carrying citations, and a fixture
    /// that silently rendered `Fallback` would pass a token scan vacuously.
    #[test]
    fn every_citation_the_binary_prints_resolves_to_synthesis_or_the_source() {
        use strehl_core::noise::PlaneNoise;

        let plane = PlaneNoise {
            gain_dn_per_e: 0.3273,
            read_noise_e: 1.2392,
            levels: Levels {
                black: 512.0,
                white: 15360.0,
            },
        };
        let rendered: Vec<String> = [
            Provenance::Profile,
            Provenance::Measured,
            Provenance::Fallback,
        ]
        .into_iter()
        .map(|p| provenance_line(&NoiseModel::new([plane; 4], 160.0, p)))
        .collect();

        // Rule 36: prove the interesting branch was exercised and is the one
        // that carries citations at all.
        assert!(
            rendered[0].contains("PROVENANCE=Profile"),
            "the Profile arm did not render; this scan would be vacuous"
        );
        assert!(
            rendered[0].contains("fact 550") && rendered[0].contains("question 126"),
            "the Profile arm is supposed to be the citation-bearing one: {}",
            rendered[0]
        );

        for line in &rendered {
            // A report-local sub-item label: a fact number with a letter glued
            // to it. These exist only inside `docs/research/M*.md` and never
            // in SYNTHESIS, so they are unresolvable to a reader of this output.
            let mut chars = line.char_indices();
            for (i, _) in chars.by_ref() {
                let Some(rest) = line[i..].strip_prefix("fact ") else {
                    continue;
                };
                let digits: String = rest.chars().take_while(char::is_ascii_digit).collect();
                if digits.is_empty() {
                    continue;
                }
                let after = rest[digits.len()..].chars().next();
                assert!(
                    !after.is_some_and(|c| c.is_ascii_alphabetic()),
                    "printed output cites report-local sub-item `fact {}{}`, which no \
                     reader can resolve; cite the SYNTHESIS fact or question it folded \
                     as. Full line:\n{}",
                    digits,
                    after.unwrap_or(' '),
                    line
                );
            }
        }
    }

    #[test]
    fn roi_parses_four_unsigned_fields() {
        assert_eq!(
            parse_roi("10,20,30,40").unwrap(),
            Roi {
                x: 10,
                y: 20,
                width: 30,
                height: 40
            }
        );
        assert_eq!(parse_roi(" 1 , 2 , 3 , 4 ").unwrap().width, 3);
    }

    #[test]
    fn roi_rejects_malformed_and_degenerate_input() {
        assert!(parse_roi("1,2,3").is_err());
        assert!(parse_roi("1,2,3,4,5").is_err());
        assert!(parse_roi("a,2,3,4").is_err());
        assert!(parse_roi("-1,2,3,4").is_err());
        assert!(parse_roi("1,2,0,4").is_err());
        assert!(parse_roi("1,2,3,0").is_err());
    }

    #[test]
    fn srgb_transfer_hits_its_endpoints_and_is_monotone() {
        assert!(srgb_encode(0.0).abs() < 1e-9);
        assert!((srgb_encode(1.0) - 1.0).abs() < 1e-6);
        // The standard 0.5 reference point.
        assert!((srgb_encode(0.5) - 0.7354).abs() < 1e-3);
        let mut prev = -1.0;
        for i in 0..=100 {
            let v = srgb_encode(i as f32 / 100.0);
            assert!(v > prev);
            prev = v;
        }
    }

    #[test]
    fn worker_plan_is_bounded_by_memory_not_by_frame_count() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        // 400 frames must not give 400 workers.
        let plan = WorkerPlan::new(400, geom, 73_400_320, MemoryModel::Buffers);
        assert!(plan.chunks <= plan.workers);
        assert!(plan.per_worker_bytes * plan.chunks <= MEMORY_BUDGET_BYTES);
        assert!(plan.chunk_len * plan.chunks >= 400);
        // And a stack smaller than the worker count does not over-split.
        let small = WorkerPlan::new(3, geom, 73_400_320, MemoryModel::Buffers);
        assert!(small.chunks <= 3);
    }

    /// The pre-M8 model must stay reachable and must keep reproducing exactly
    /// the plan that shipped before M8, so the two remain comparable. It is no
    /// longer the default — see `the_default_memory_model_is_m8`.
    #[test]
    fn the_buffers_model_still_reproduces_the_pre_m8_plan() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        let plan = WorkerPlan::new(400, geom, 73_400_320, MemoryModel::Buffers);
        // px * 30 + frame_bytes, with px = 3516 * 2344.
        assert_eq!(plan.per_worker_bytes, 320_645_440);
        assert_eq!(MEMORY_BUDGET_BYTES / plan.per_worker_bytes, 20);
        // 22 frames, 105 frames, 220 frames, as M2 and M8 measured them.
        for (frames, chunks) in [(22usize, 11usize), (105, 18), (220, 20)] {
            let p = WorkerPlan::new(frames, geom, 73_400_320, MemoryModel::Buffers);
            assert_eq!(p.chunks, chunks, "{frames} frames");
        }
    }

    /// The owner adopted M8 as the default after independent verification. The
    /// `Buffers` model licenses 20 workers where 6 GiB pays for 16, and both
    /// models produce byte-identical output, so the only thing this changes is
    /// that the plan stops exceeding the budget it claims to respect.
    #[test]
    fn the_default_memory_model_is_m8() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        assert_eq!(MemoryModel::default(), MemoryModel::M8);
        let px = geom.pixels();
        let per_worker = px * 30 + 73_400_320;
        // MEASURED (M8): the reference 22-frame stack does not move at all.
        for (frames, chunks) in [(22usize, 11usize), (105, 15), (220, 16)] {
            let p = WorkerPlan::new(frames, geom, 73_400_320, MemoryModel::default());
            assert_eq!(p.chunks, chunks, "{frames} frames");
            assert!(
                m8_predicted_peak_bytes(p.chunks, px, per_worker) <= MEMORY_BUDGET_BYTES,
                "the default plan for {frames} frames exceeds its own budget"
            );
        }
    }

    /// `ceil(log2(chunks))`, which MEASURED (M8, `data/floor.csv`) is how many
    /// extra `Selection`s the reduce tree holds alive.
    #[test]
    fn reduce_levels_is_ceil_log2() {
        for (chunks, levels) in [
            (0usize, 0usize),
            (1, 0),
            (2, 1),
            (3, 2),
            (4, 2),
            (5, 3),
            (8, 3),
            (9, 4),
            (16, 4),
            (17, 5),
            (18, 5),
            (20, 5),
            (32, 5),
            (33, 6),
        ] {
            assert_eq!(reduce_levels(chunks), levels, "chunks = {chunks}");
        }
    }

    /// The two measured constants, checked against the measurements they came
    /// from rather than against themselves. If someone edits either, this goes
    /// red and names the datum it violated.
    #[test]
    fn the_m8_constants_match_the_measurements_they_came_from() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        let px = geom.pixels();
        let per_worker = px * 30 + 73_400_320;
        let mib = |v: f64| v * (1u64 << 20) as f64;

        // MEASURED (M8, data/floor.csv): coffee-bean N=1, RAYON_NUM_THREADS=1,
        // peak working set 320.2 MiB over 3 runs, spread 0.06 MiB.
        let floor_from_data = mib(320.2) - per_worker as f64;
        assert!(
            (PROCESS_FLOOR_BYTES as f64 - floor_from_data).abs() / floor_from_data < 0.05,
            "PROCESS_FLOOR_BYTES = {PROCESS_FLOOR_BYTES} but N=1 measured a floor of \
             {floor_from_data:.0} B"
        );

        // MEASURED (M8, data/floor.csv): the peak steps by exactly 110.04 MiB
        // as chunks crosses 1 -> 2 -> 3 -> 5, i.e. one Selection per level.
        let step = m8_peak_bytes(2, 1, px, per_worker) - m8_peak_bytes(1, 1, px, per_worker);
        assert_eq!(step, px * 14);
        assert!((step as f64 - mib(110.04)).abs() / mib(110.04) < 0.005);
        assert_eq!(
            m8_peak_bytes(4, 1, px, per_worker),
            m8_peak_bytes(3, 1, px, per_worker),
            "chunks 3 and 4 are the same reduce depth; MEASURED 540.4 and 540.3 MiB"
        );
    }

    /// The scratch term, tested where it is actually resident: full overlap,
    /// every chunk live at once. Tolerance 8%, against a MEASURED run-to-run
    /// spread of up to 7.3% and an out-of-sample error of 8.4% mean.
    #[test]
    fn the_m8_model_reproduces_the_measured_full_overlap_peaks() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        let px = geom.pixels();
        let per_worker = px * 30 + 73_400_320;
        // (chunks, MEASURED mean peak working set in MiB) at RAYON_NUM_THREADS
        // >= chunks and chunk_len >= 2, so live == chunks. Sources: 109MSDCF
        // N=22 (n=5), 119MSDCF N=33 holdout (n=4), coffee-bean N=105 (n=5) and
        // N=40 (n=5). experiments/m8-scratch/data/*.csv.
        for (chunks, measured_mib) in [
            (11usize, 4121.7f64),
            (17, 5978.0),
            (18, 6900.6),
            (20, 7360.8),
        ] {
            let predicted =
                m8_predicted_peak_bytes(chunks, px, per_worker) as f64 / (1u64 << 20) as f64;
            let err = (predicted - measured_mib) / measured_mib;
            assert!(
                err.abs() < 0.08,
                "chunks = {chunks}: predicted {predicted:.0} MiB vs measured {measured_mib:.0} \
                 MiB ({:+.1}%)",
                100.0 * err
            );
        }
        // It must never claim a plan is cheaper than its buffers alone, and it
        // must be monotone in the worker count.
        let mut prev = 0;
        for chunks in 1..=64 {
            let p = m8_predicted_peak_bytes(chunks, px, per_worker);
            assert!(p > chunks * per_worker);
            assert!(p > prev);
            prev = p;
        }
    }

    /// KNOWN LIMITATION, recorded so it cannot be forgotten: at one live worker
    /// the peak is reached during the *fold*, not the decode, so no decoder
    /// scratch is resident and the model over-predicts. Over-predicting is the
    /// safe direction for a budget, but it is not accuracy.
    #[test]
    fn the_m8_model_over_predicts_at_a_single_live_worker() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        let px = geom.pixels();
        let per_worker = px * 30 + 73_400_320;
        // (chunks, MEASURED peak working set in MiB at RAYON_NUM_THREADS=1)
        for (chunks, measured_mib) in [
            (1usize, 320.2f64),
            (2, 430.3),
            (4, 540.3),
            (8, 650.4),
            (18, 836.0),
        ] {
            let predicted = m8_peak_bytes(chunks, 1, px, per_worker) as f64 / (1u64 << 20) as f64;
            let err = (predicted - measured_mib) / measured_mib;
            assert!(
                (0.0..0.15).contains(&err),
                "chunks = {chunks}, live = 1: predicted {predicted:.0} MiB vs measured \
                 {measured_mib:.0} MiB ({:+.1}%); the model is supposed to over-predict here, \
                 by under 15%",
                100.0 * err
            );
        }
    }

    /// The opt-in model plans fewer, larger chunks on big stacks and leaves
    /// small ones alone, and its plan fits the budget it was derived from.
    #[test]
    fn the_m8_memory_model_is_opt_in_and_plans_within_the_budget() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        let px = geom.pixels();
        let per_worker = px * 30 + 73_400_320;
        assert_eq!(m8_worker_cap(px, per_worker), 16);
        // MEASURED (M8): N=22 is unchanged, N=105 drops 18 -> 15, N=220 drops
        // 20 -> 16. If any of these move, the report is stale.
        for (frames, buffers_chunks, m8_chunks) in [
            (22usize, 11usize, 11usize),
            (33, 17, 11),
            (105, 18, 15),
            (220, 20, 16),
        ] {
            let b = WorkerPlan::new(frames, geom, 73_400_320, MemoryModel::Buffers);
            let m = WorkerPlan::new(frames, geom, 73_400_320, MemoryModel::M8);
            assert_eq!(b.chunks, buffers_chunks, "buffers, {frames} frames");
            assert_eq!(m.chunks, m8_chunks, "m8, {frames} frames");
            assert!(m.chunks <= b.chunks, "m8 must never plan MORE workers");
            assert!(
                m8_predicted_peak_bytes(m.chunks, px, per_worker) <= MEMORY_BUDGET_BYTES,
                "m8 plan for {frames} frames exceeds the budget it was derived from"
            );
            assert!(m.chunk_len * m.chunks >= frames);
        }
    }

    /// `describe()` must state the honest figure whichever model is in force,
    /// and must not present the buffer sum as anything but a lower bound.
    #[test]
    fn describe_reports_both_the_lower_bound_and_the_measured_prediction() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        for model in [MemoryModel::Buffers, MemoryModel::M8] {
            let plan = WorkerPlan::new(105, geom, 73_400_320, model);
            let text = plan.describe();
            assert!(text.contains("LOWER BOUND"), "{text}");
            assert!(text.contains("predicted peak"), "{text}");
            assert!(text.contains("MEASURED model, M8"), "{text}");
            assert!(
                m8_predicted_peak_bytes(plan.chunks, plan.px, plan.per_worker_bytes)
                    > plan.buffers_only_bytes(),
                "the predicted peak must exceed the buffer-only lower bound"
            );
        }
    }

    #[test]
    fn every_frame_is_covered_exactly_once_by_the_chunking() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        for model in [MemoryModel::Buffers, MemoryModel::M8] {
            for frames in [1usize, 2, 3, 22, 60, 199, 200] {
                let plan = WorkerPlan::new(frames, geom, 73_400_320, model);
                let mut seen = 0usize;
                for c in 0..plan.chunks {
                    let start = c * plan.chunk_len;
                    let end = ((c + 1) * plan.chunk_len).min(frames);
                    assert!(start < end, "empty chunk for {frames} frames");
                    seen += end - start;
                }
                assert_eq!(seen, frames);
            }
        }
    }

    #[test]
    fn mean_and_sigma_match_the_population_definition() {
        let (m, s) = mean_and_sigma(&[2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]);
        assert!((m - 5.0).abs() < 1e-9);
        assert!((s - 2.0).abs() < 1e-9);
        assert_eq!(mean_and_sigma(&[]), (0.0, 0.0));
    }

    /// The two crates each carry a moment helper, and the acceptance invariant
    /// mixes their outputs in one ratio. If they ever disagreed the report would
    /// be measuring the harness (discipline 210), so assert they do not.
    #[test]
    fn the_core_and_cli_moment_helpers_agree() {
        let mut rng = Lcg(0x0053_0001);
        let v: Vec<f32> = (0..4096)
            .map(|_| 800.0 + 37.0 * rng.normal() as f32)
            .collect();
        let (m1, s1) = mean_and_sigma(&v);
        let (m2, s2) = strehl_core::flat_ratio::mean_and_sd(&v);
        assert!((m1 - m2).abs() < 1e-12, "{m1} vs {m2}");
        assert!((s1 - s2).abs() < 1e-12, "{s1} vs {s2}");
        assert_eq!(strehl_core::flat_ratio::mean_and_sd(&[]), (0.0, 0.0));
    }

    /// Sentinel for the padding and for everything outside the active area.
    /// Real padding is zeros, which black subtraction would turn into a large
    /// negative and might not be noticed; this fails loudly instead.
    const POISON: u16 = 60_000;

    const TEST_BLACK: f32 = 500.0;

    /// A synthetic frame carrying the two geometry hazards the real decoder
    /// has: the buffer is wider and taller than the active area, and the active
    /// area does not begin at `(0, 0)`. Any read that uses `stride` instead of
    /// the active row width, or forgets the origin, lands on [`POISON`].
    ///
    /// The origin is even in both axes so the RGGB phase is preserved, which is
    /// the only origin a CFA plane mapping can accept.
    fn synthetic_frame(
        pw: usize,
        ph: usize,
        mut quad: impl FnMut(usize, usize) -> [u16; 4],
    ) -> Frame {
        let (aw, ah) = (2 * pw, 2 * ph);
        let (ox, oy) = (2usize, 4usize);
        let stride = aw + ox + 3;
        let buffer_height = ah + oy + 2;
        let mut data = vec![POISON; stride * buffer_height];
        for py in 0..ph {
            for px in 0..pw {
                let q = quad(px, py);
                for (plane, v) in [CfaPlane::R, CfaPlane::G1, CfaPlane::G2, CfaPlane::B]
                    .into_iter()
                    .zip(q)
                {
                    let (dx, dy) = plane.rggb_offset();
                    data[(oy + 2 * py + dy) * stride + ox + 2 * px + dx] = v;
                }
            }
        }
        Frame {
            data,
            stride,
            buffer_height,
            active: strehl_raw::Region {
                x: ox,
                y: oy,
                width: aw,
                height: ah,
            },
            levels: Levels {
                black: TEST_BLACK,
                white: 15360.0,
            },
            iso: Some(100.0),
            wb_coeffs: [2.0, 1.0, 1.5, f32::NAN],
            // No characterisation: these fixtures test the geometry and the
            // merge, and the colour path has its own tests. An empty matrix is
            // also the honest default -- it is what a body `rawler` does not
            // know decodes to, and it keeps these tests on the byte-frozen
            // camera-native path.
            xyz_to_cam_rgbe: [[0.0; 3]; 4],
            color_matrices: Vec::new(),
            camera: "synthetic".into(),
            path: PathBuf::from("synthetic"),
        }
    }

    /// Deterministic Gaussian source. A fixed seed keeps every assertion below
    /// reproducible run to run.
    struct Lcg(u64);

    impl Lcg {
        fn unit(&mut self) -> f64 {
            self.0 = self
                .0
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            ((self.0 >> 32) as u32 as f64 + 0.5) / 4_294_967_296.0
        }

        fn normal(&mut self) -> f64 {
            let (u1, u2) = (self.unit(), self.unit());
            (-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()
        }
    }

    /// Hand-computed values, and the one that matters is the corner.
    ///
    /// The frame's active sample at `(x, y)` is `1000 + 10 * y + x`, so the
    /// green of plane pixel `(px, py)` is
    /// `0.5 * (G1 + G2) = 1000 + 20 * py + 2 * px + 5.5`, and after black
    /// subtraction `505.5 + 20 * py + 2 * px`.
    #[test]
    fn roi_green_is_hand_computable_and_never_reads_the_padding() {
        let f = synthetic_frame(6, 5, |px, py| {
            let at = |dx: usize, dy: usize| (1000 + 10 * (2 * py + dy) + (2 * px + dx)) as u16;
            [at(0, 0), at(1, 0), at(0, 1), at(1, 1)]
        });
        let expect = |px: usize, py: usize| 505.5 + 20.0 * py as f32 + 2.0 * px as f32;

        // Interior, and row-major order.
        let roi = Roi {
            x: 1,
            y: 1,
            width: 3,
            height: 2,
        };
        let got = roi_green(&f, roi, TEST_BLACK);
        assert_eq!(got.len(), 6);
        for (i, v) in got.iter().enumerate() {
            let (px, py) = (roi.x + i % roi.width, roi.y + i / roi.width);
            assert!((v - expect(px, py)).abs() < 1e-3, "at ({px},{py}): {v}");
        }

        // The bottom-right corner quad — the last real row and column, one
        // sample away from the padding in both axes.
        let corner = Roi {
            x: 5,
            y: 4,
            width: 1,
            height: 1,
        };
        let got = roi_green(&f, corner, TEST_BLACK);
        assert_eq!(got.len(), 1);
        assert!(
            (got[0] - expect(5, 4)).abs() < 1e-3,
            "corner was {}",
            got[0]
        );
        // POISON would have shown up as a value three orders of magnitude out.
        assert!(got[0] < 1000.0);

        // The whole plane, edges included, still never sees the padding.
        let all = roi_green(
            &f,
            Roi {
                x: 0,
                y: 0,
                width: 6,
                height: 5,
            },
            TEST_BLACK,
        );
        assert_eq!(all.len(), 30);
        assert!(all.iter().all(|v| *v < 1000.0));
    }

    /// The estimator recovers a sigma that was put in on purpose, and the
    /// green average halves the variance.
    ///
    /// The second half is what `--flat-roi`'s "model predicts" line depends on:
    /// the output green is the mean of two independent sensor samples, so its
    /// noise is a factor of sqrt(2) below a single green sample's.
    #[test]
    fn roi_green_and_mean_and_sigma_recover_an_injected_noise_level() {
        const LEVEL: f64 = 4000.0;
        const SIGMA: f64 = 50.0;
        let (pw, ph) = (128usize, 128usize);

        // G1 and G2 given the *same* deviation: the average keeps it intact.
        let mut rng = Lcg(0x5EED_1234);
        let common = synthetic_frame(pw, ph, |_, _| {
            let v = (LEVEL + SIGMA * rng.normal()).round() as u16;
            [v, v, v, v]
        });
        let roi = Roi {
            x: 0,
            y: 0,
            width: pw,
            height: ph,
        };
        let (mean, sigma) = mean_and_sigma(&roi_green(&common, roi, TEST_BLACK));
        assert!(
            (mean - (LEVEL - TEST_BLACK as f64)).abs() < 1.0,
            "mean {mean}"
        );
        assert!((sigma / SIGMA - 1.0).abs() < 0.02, "sigma {sigma}");

        // G1 and G2 given *independent* deviations: the average must land a
        // factor of sqrt(2) lower.
        let mut rng = Lcg(0x5EED_1234);
        let independent = synthetic_frame(pw, ph, |_, _| {
            let mut s = || (LEVEL + SIGMA * rng.normal()).round() as u16;
            [s(), s(), s(), s()]
        });
        let (_, sigma) = mean_and_sigma(&roi_green(&independent, roi, TEST_BLACK));
        let want = SIGMA / 2.0f64.sqrt();
        assert!((sigma / want - 1.0).abs() < 0.03, "sigma {sigma} vs {want}");
    }

    /// Stacking one frame must give a ratio of exactly 1.000.
    ///
    /// This is the headline path's identity check. The two sides of the ratio
    /// are produced by different code — `roi_green` walks the decoded frame,
    /// `flat_roi_stats` walks the merged `Selection` — so if they disagree
    /// about which pixels the ROI names, or in which order, this fails.
    #[test]
    fn a_single_frame_stack_has_a_flat_roi_ratio_of_exactly_one() {
        let (pw, ph) = (32usize, 24usize);
        let geom = PlaneGeometry {
            width: pw,
            height: ph,
        };
        let mut rng = Lcg(0xC0FF_EE01);
        let f = synthetic_frame(pw, ph, |_, _| {
            let mut s = || (4000.0 + 80.0 * rng.normal()).round() as u16;
            [s(), s(), s(), s()]
        });

        let mut sel = Selection::new(geom);
        sel.fold(0, &f, &vec![1.0f32; geom.pixels()]).unwrap();

        let roi = Roi {
            x: 3,
            y: 5,
            width: 20,
            height: 14,
        };
        let single = roi_green(&f, roi, TEST_BLACK);
        let s = flat_roi_stats(&sel, &single, roi, geom, TEST_BLACK);

        assert_eq!(s.pixels, 20 * 14);
        assert!(
            (s.legacy_raw_ratio - 1.0).abs() < 1e-9,
            "ratio {}",
            s.legacy_raw_ratio
        );
        assert!((s.stacked_sigma - s.single_sigma).abs() < 1e-6);
        assert!((s.stacked_mean - s.single_mean).abs() < 1e-6);
        // The high-pass side has to agree for the same reason, and it walks a
        // different buffer again (`stacked` is gathered from the `Selection`).
        let (a, b) = (
            s.stacked_hp_sd.expect("20x14 holds a 9x9 box"),
            s.single_hp_sd.expect("20x14 holds a 9x9 box"),
        );
        assert!((a - b).abs() < 1e-6, "hp sd {a} vs {b}");
        assert_eq!(s.distinct_winners, 1);
        assert_eq!(s.median_winner, 0);
    }

    /// A winner that is k times noisier reports a ratio of k.
    ///
    /// Frame 1 is given a strictly higher focus everywhere, so argmax must
    /// select it at every pixel; its green swings +/- 3d about the same level
    /// the control swings +/- d about. The population sd of a two-valued
    /// alternation is exactly its amplitude, so the expected ratio is exactly
    /// 3.0 with no sampling slack.
    #[test]
    fn the_flat_roi_ratio_is_the_ratio_of_the_two_sigmas() {
        let (pw, ph) = (16usize, 16usize);
        let geom = PlaneGeometry {
            width: pw,
            height: ph,
        };
        let level = 4000.0f32;
        let d = 10.0f32;

        let swing = |px: usize, py: usize, amp: f32| {
            let sign = if (px + py).is_multiple_of(2) {
                1.0
            } else {
                -1.0
            };
            (level + sign * amp).round() as u16
        };
        let quiet = synthetic_frame(pw, ph, |px, py| {
            let v = swing(px, py, d);
            [v, v, v, v]
        });
        let loud = synthetic_frame(pw, ph, |px, py| {
            let v = swing(px, py, 3.0 * d);
            [v, v, v, v]
        });

        let mut sel = Selection::new(geom);
        sel.fold(0, &quiet, &vec![1.0f32; geom.pixels()]).unwrap();
        sel.fold(1, &loud, &vec![2.0f32; geom.pixels()]).unwrap();

        let roi = Roi {
            x: 0,
            y: 0,
            width: pw,
            height: ph,
        };
        let control = roi_green(&quiet, roi, TEST_BLACK);
        let s = flat_roi_stats(&sel, &control, roi, geom, TEST_BLACK);

        assert_eq!(s.distinct_winners, 1);
        assert_eq!(s.median_winner, 1);
        assert!(
            (s.single_sigma - d as f64).abs() < 1e-6,
            "{}",
            s.single_sigma
        );
        assert!(
            (s.stacked_sigma - 3.0 * d as f64).abs() < 1e-6,
            "{}",
            s.stacked_sigma
        );
        assert!(
            (s.legacy_raw_ratio - 3.0).abs() < 1e-9,
            "ratio {}",
            s.legacy_raw_ratio
        );
        // The high-pass ratio sees the same 3x. A checkerboard at the Nyquist
        // frequency is entirely in the box's pass band, so this fixture cannot
        // separate the two statistics — that separation is
        // `flat_ratio::the_high_pass_ratio_catches_a_planted_explosion_the_raw_ratio_misses`,
        // where the fixture carries structure. What it does check is that the
        // new column agrees with the old one where they must agree, and that
        // both absolute sds land on their closed form.
        //
        // A 9x9 box over a checkerboard covers 41 cells of one sign and 40 of
        // the other, so its mean is ±d/81 and the residual is ±d·80/81 at every
        // interior pixel. The interior here is 8x8, an even checkerboard, so
        // the residual mean is 0 and the sd is exactly d·80/81.
        //
        // Tolerance is DERIVED, not tuned. `boxfilter::horizontal_sums` stores
        // its running row sums as f32 (`boxfilter.rs`), so each of the 9 row
        // sums (≤ 9·3518 ≈ 31662, where f32 ulp is 2^-8) carries up to
        // 0.00195 DN of rounding; the box mean therefore carries up to
        // 9·0.00195/81 ≈ 2.2e-4 DN. Against a 9.88 DN residual that is 2.2e-5
        // relative, and the ratio can carry roughly that again. 1e-3 DN
        // absolute and 1e-4 relative are those bounds with margin. This
        // fixture is a deliberately hostile 353:1 pedestal-to-residual ratio;
        // a real flat ROI runs nearer 41:1.
        let hp_quiet = s.single_hp_sd.expect("16x16 holds a 9x9 box");
        let hp_loud = s.stacked_hp_sd.expect("ditto");
        let closed_form = d as f64 * 80.0 / 81.0;
        assert!(
            (hp_quiet - closed_form).abs() < 1e-3,
            "single hp sd {hp_quiet} vs closed form {closed_form}"
        );
        assert!(
            (hp_loud - 3.0 * closed_form).abs() < 1e-3,
            "stacked hp sd {hp_loud} vs closed form {}",
            3.0 * closed_form
        );
        let hp_ratio = hp_loud / hp_quiet;
        assert!((hp_ratio - 3.0).abs() < 1e-4, "hp ratio {hp_ratio}");

        // Both sides are black-subtracted, so the means agree even though only
        // one of them passed through `roi_green`.
        assert!((s.stacked_mean - s.single_mean).abs() < 1e-6);
        assert!((s.single_mean - (level - TEST_BLACK) as f64).abs() < 1e-6);
    }
}
