//! `strehl` command line.

mod image_out;
mod merge_cmd;
mod stack;

use std::path::{Path, PathBuf};
use std::time::Instant;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use rayon::prelude::*;

use merge_cmd::MergeOptions;
use stack::{MemoryModel, Roi, StackOptions, parse_roi};
use strehl_core::calibration::{AdmissionHistogram, SpectralAccumulator, SpectralConfig};
use strehl_core::focus::FocusField;
use strehl_core::merge::{DEFAULT_GATE, FocusStats, regularise};
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma};
use strehl_core::profile;

#[derive(Parser)]
#[command(name = "strehl", version, about = "Noise-aware RAW focus stacking")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Decode a directory of RAW files and report what was found.
    ///
    /// This exists to make the sensor's real geometry and levels visible before
    /// anything is stacked, and to time decode against the recorded baseline.
    Probe {
        /// Directory containing RAW files.
        dir: PathBuf,
        /// Decode at most this many frames.
        #[arg(short, long)]
        limit: Option<usize>,
    },

    /// Measure the stack-specific spectral target and the spatial gate that
    /// realises it. Experimental M81 calibration; it never writes an image.
    #[command(name = "calibrate-gate")]
    CalibrateGate {
        /// Directory containing RAW files.
        dir: PathBuf,
        /// Stack at most this many frames, in filename order.
        #[arg(short, long)]
        limit: Option<usize>,
        /// Width used to place M70's fixed spectral grid. Defaults to the
        /// decoder's active width.
        #[arg(long)]
        analysis_width: Option<usize>,
        /// Height used to place M70's fixed spectral grid. Defaults to the
        /// decoder's active height.
        #[arg(long)]
        analysis_height: Option<usize>,
        /// Concurrent calibration workers.
        #[arg(long, default_value_t = 6)]
        workers: usize,
    },

    /// Stack a directory of RAW files into one image, by noise-gated
    /// ESTIMATION. This is the default path and the thing strehl is for.
    ///
    /// Two passes. Pass one elects a winner per pixel from a 17x17-REGULARISED
    /// focus field. Pass two averages every frame whose regularised response the
    /// calibrated sensor noise model cannot separate from that winner's. Where
    /// one frame is unambiguously sharpest it degenerates to selection; where
    /// several are indistinguishable it averages them, and averaging is the only
    /// operation that gets BELOW single-frame noise.
    ///
    /// Every shipping focus stacker selects: it picks one frame per pixel and
    /// therefore inherits that frame's noise, and because the pick is made using
    /// that same frame's noise the two are correlated and the noise is amplified
    /// rather than merely retained. On a 30-frame static burst where the right
    /// answer is known exactly to be sqrt(30) = 5.48x less noise, selection
    /// scores 0.77x -- a 1.3x noise INCREASE -- and this path scores 5.43x.
    /// (MEASURED, docs/research/M62-sqrt-n.md.) Run `strehl argmax-baseline` to
    /// reproduce the selector number yourself.
    ///
    /// THERE IS ONE KNOB: --gate. It is a continuum, not a mode switch. Read its
    /// help for what you are trading; the short version is that low is sharper
    /// and noisier, high is cleaner and softer, and the honest price list is
    /// there rather than here.
    ///
    /// It does not yet align, deconvolve, reject outliers, or model occlusion.
    ///
    /// Output is BINNED, NOT DEMOSAICED: each output pixel is one real sensor
    /// quad, R = R, G = (G1+G2)/2, B = B, at half the sensor's linear
    /// resolution. Output is LINEAR and will look very dark in an ordinary
    /// viewer. That is correct: it is what measurement needs. Pass --srgb for
    /// something to look at, and do not measure that file.
    #[command(alias = "merge")]
    Stack {
        /// Directory containing RAW files.
        dir: PathBuf,
        /// Where to write the merged 16-bit RGB TIFF. Requires exactly one
        /// --gate. Omit it to measure without writing an image.
        #[arg(short, long)]
        out: Option<PathBuf>,
        /// Stack at most this many frames, in filename order.
        #[arg(short, long)]
        limit: Option<usize>,
        /// Apply the sRGB transfer curve. For looking at, NOT for measuring.
        #[arg(long)]
        srgb: bool,
        /// The one knob: how much averaging, in units of the focus noise.
        ///
        /// A frame is averaged in where its regularised focus response is within
        /// `T * sqrt(2) * FOCUS_NOISE_SD` of the winner's. T = 0 is pure
        /// selection -- one frame per pixel, the thing every other stacker does.
        /// Raising T admits more frames per pixel and the merge moves along a
        /// CONTINUUM towards a gated mean. There is no second mode; this dial is
        /// the whole tradeoff surface.
        ///
        /// WHAT YOU ARE TRADING. The comparable axis at both ends is the mean
        /// number of frames actually averaged per pixel, `mean n_eff`, which
        /// every run prints. Turning the dial up buys noise and spends
        /// sharpness:
        ///
        ///   NOISE, on a 30-frame static burst where sqrt(30) = 5.48x is
        ///   provably correct (MEASURED, M62): T=0 scores 0.98x, T=2 3.78x,
        ///   T=4 5.43x, T=8 5.48x. On real frames a plain unweighted mean of a
        ///   whole 22-frame stack reaches 0.534x flat-ROI noise (fact 19), and
        ///   the shipped T=2 reaches 0.890x (fact 320).
        ///
        ///   SHARPNESS: that same plain mean collapses detail 58% (fact 24), and
        ///   that is what the gate exists to avoid. The nearest measured price
        ///   for admitting more frames is M57's: going from mean n_eff 12.4 to
        ///   1.45 recovered 0.556 px of PSF width against an oracle-confirmed
        ///   ground truth, and 0.496-0.740 px on 6 of 8 real cells at
        ///   3.95-17.58 sigma. READ THE CAVEAT: M57 swept a FRACTIONAL
        ///   peak-height gate, not this one, and its axis runs the opposite way.
        ///   Mean n_eff is the only axis the two share, so treat those pixels as
        ///   the scale of the price, not as a value of T. The sharpness cost of
        ///   THIS gate on real frames is not measured in this corpus, and no
        ///   number here should be read as claiming otherwise.
        ///
        /// Repeatable: every value is folded in the same pass two, so a sweep
        /// costs one decode budget rather than one per value. Calibrate against
        /// the reported mean n_eff -- the gate that gives a chosen n_eff varies
        /// 28.9x across the corpus (MEASURED, M52), so a gate is not portable
        /// between stacks and a default is a starting point, not a calibration.
        #[arg(long = "gate", value_name = "T", num_args = 1.., default_values_t = [DEFAULT_GATE])]
        gates: Vec<f32>,
        /// Low-detail region for the noise invariant, in PLANE coordinates
        /// (half sensor resolution).
        #[arg(long, value_name = "X,Y,W,H", value_parser = parse_roi)]
        flat_roi: Option<Roi>,
        /// Detail region for the retention invariant, in PLANE coordinates.
        /// The flat ROI alone is not a result: a plain mean wins it at 0.534x
        /// while collapsing detail 58%.
        #[arg(long, value_name = "X,Y,W,H", value_parser = parse_roi)]
        detail_roi: Option<Roi>,

        /// Report which gate would achieve this mean n_eff. A CALIBRATION AID,
        /// NOT A SECOND KNOB.
        ///
        /// It solves the measured gate ladder by interpolation and PRINTS the
        /// answer. It does not change the merged image: --out still writes at
        /// --gate. To use it, run once without --out to read the solved gate,
        /// then pass that gate. This limitation is real and is recorded as
        /// defect 11 in docs/research/M49-unapplied-findings.md; wiring it to
        /// the output needs a third pass over the frames and M64 did not build
        /// one.
        ///
        /// Why the number it prints is worth having: a fixed gate is not a
        /// calibration. M52 re-measured all SEVEN corpus stacks against the
        /// current pipeline and found mean n_eff at gate 2.0 spanning 1.177
        /// (foam) to 14.386 (coffee-bean), a 12.22x spread, with the gates that
        /// solve for a given n_eff spanning 0.7618 to 21.9934 - a factor of
        /// 28.9. foam CANNOT reach n_eff = 3 anywhere on the 0.5-4.0 ladder.
        ///
        /// Fact 324's own numbers for the two ISO-50 stacks are stale: they
        /// were folded before commit 2a4f5c5 corrected the ISO-50 gain floor,
        /// so 119MSDCF is 2.847 and not 2.258, and coffee-bean is 14.386 and
        /// not 7.422. Its stated mechanism - that n_eff is a roughly fixed
        /// fraction of bracket length - is refuted: n_eff/N ranges 11.6x.
        #[arg(long, value_name = "N")]
        target_n_eff: Option<f64>,

        /// Gather per-pixel through-focus SUFFICIENT STATISTICS in pass two.
        ///
        /// The seam the next milestone needs. Retains, per pixel and at a
        /// FIVE-pixel focus window rather than the 27-pixel selection window,
        /// enough state to compute a sub-frame peak by parabola fit, a top-4
        /// frame list, and a bimodality statistic WITHOUT a third pass over the
        /// frames. Fixed 60 B/px, constant in the frame count; a focus volume
        /// would be 4*N B/px and is forbidden.
        ///
        /// Opt-in: it costs 527 MB per worker on this sensor and will reduce
        /// the worker count the memory budget licenses. It cannot change the
        /// merged image.
        ///
        /// That is 64 B/px, not the 60 B/px of `ThroughFocus` alone: the flag
        /// also forces a 4 B/px fine focus plane into every pass-two worker's
        /// scratch (`merge_cmd.rs`'s `FINE_FIELD_PER_PX`). Quoting the struct's
        /// own footprint understated the option's cost by 6.7%, which the
        /// binary contradicted in the same run under `--stats`.
        #[arg(long)]
        stats: bool,

        /// Also gather a frame-permutation placebo beside --stats.
        ///
        /// Same responses per pixel, same winning value, adjacency destroyed.
        /// The bimodality number is not interpretable without it, because the
        /// statistic is a max minus a min and is large by construction.
        #[arg(long, requires = "stats")]
        stats_placebo: bool,

        /// Per-channel tail fraction for the confidence union mask.
        #[arg(long, value_name = "Q", default_value_t = 0.05)]
        confidence_tail: f64,
    },

    /// Stack by plain per-pixel argmax. THE NAIVE BASELINE, NOT THE DEFAULT.
    ///
    /// THIS IS A REFERENCE ARTIFACT, ON PURPOSE, AND YOU SHOULD NOT SHIP ITS
    /// OUTPUT. It selects, per pixel, the single frame with the highest
    /// noise-normalised Tenengrad focus measure and copies that frame's 2x2
    /// quad. Selection is exactly the defect strehl exists to remove, and this
    /// subcommand is the artifact every quality claim is measured against. It
    /// does not align, denoise, regularise the winner map, or blend frames.
    ///
    /// It was `strehl stack` until M64. It scores 0.77x on the 30-frame static
    /// burst whose correct answer is 5.48x -- a 1.3x noise INCREASE (MEASURED,
    /// docs/research/M62-sqrt-n.md). It is kept, and kept runnable, because a
    /// project that deletes its negative control can no longer show that its
    /// instrument can fail. Use `strehl stack --gate 0` for a selector that
    /// shares the estimator's regularised winner field; use this one for the
    /// unregularised argmax as shipped before M64.
    ///
    /// Output is BINNED, NOT DEMOSAICED: each output pixel is one real sensor
    /// quad, R = R, G = (G1+G2)/2, B = B, at half the sensor's linear
    /// resolution. There is no interpolation, so no demosaic artifact
    /// contaminates the baseline.
    ///
    /// Default output is LINEAR and will look very dark in an ordinary viewer.
    /// That is correct: it is what measurement needs. Pass --srgb for something
    /// to look at, and do not measure that file.
    #[command(name = "argmax-baseline")]
    ArgmaxBaseline {
        /// Directory containing RAW files.
        dir: PathBuf,
        /// Where to write the stacked 16-bit RGB TIFF.
        #[arg(short, long)]
        out: PathBuf,
        /// Stack at most this many frames, in filename order.
        #[arg(short, long)]
        limit: Option<usize>,
        /// Apply the sRGB transfer curve. For looking at, NOT for measuring.
        #[arg(long)]
        srgb: bool,
        /// Also write the winner map: a 16-bit grayscale TIFF holding the
        /// literal winning frame index per pixel. Smooth depth-ordered bands
        /// are what a real scene should give; salt-and-pepper speckle in it is
        /// the argmax defect made visible. Values are 0..N-1, so autoscale it
        /// to look at it.
        #[arg(long, value_name = "PATH")]
        index_map: Option<PathBuf>,
        /// Measure the noise penalty over a low-detail region, in PLANE
        /// coordinates (half sensor resolution). Reports the spatial sigma of
        /// the stacked green channel against the same region in the single
        /// middle frame, and their ratio.
        #[arg(long, value_name = "X,Y,W,H", value_parser = parse_roi)]
        flat_roi: Option<Roi>,
        /// How to turn the memory budget into a worker count. `m8` is the
        /// default: buffers plus the MEASURED decoder scratch, rayon reduce
        /// tree and process floor. `buffers` is the pre-M8 model, kept for
        /// comparison — it MEASURED (M8) licenses more workers than the budget
        /// pays for. Output is byte-identical either way; only the worker count
        /// changes. See `docs/research/M8-scratch-measured.md`.
        #[arg(long, value_enum, default_value_t = MemoryModel::M8)]
        memory_model: MemoryModel,
    },
}

fn main() -> Result<()> {
    // `rawler` logs a WARN per frame when its lens database has no entry for
    // the reported mount/ID. That is true and irrelevant here — nothing in this
    // pipeline consumes lens metadata yet — and at one line per frame it buries
    // the measurement output. Errors from that module still get through.
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info,rawler::lens=error".into()),
        )
        .init();

    match Cli::parse().command {
        Command::Probe { dir, limit } => probe(&dir, limit),
        Command::CalibrateGate {
            dir,
            limit,
            analysis_width,
            analysis_height,
            workers,
        } => calibrate_gate(&dir, limit, analysis_width, analysis_height, workers),
        Command::ArgmaxBaseline {
            dir,
            out,
            limit,
            srgb,
            index_map,
            flat_roi,
            memory_model,
        } => stack::run(&StackOptions {
            dir,
            out,
            limit,
            srgb,
            index_map,
            flat_roi,
            memory_model,
        }),
        Command::Stack {
            dir,
            out,
            limit,
            srgb,
            gates,
            flat_roi,
            detail_roi,
            target_n_eff,
            stats,
            stats_placebo,
            confidence_tail,
        } => merge_cmd::run(&MergeOptions {
            dir,
            out,
            limit,
            srgb,
            gates,
            flat_roi,
            detail_roi,
            target_n_eff,
            stats,
            stats_placebo,
            confidence_tail,
        }),
    }
}

struct CalibrationScratch {
    luma: Vec<f32>,
    field: FocusField,
    box_scratch: Vec<f32>,
    regularised: Vec<f32>,
}

impl CalibrationScratch {
    fn new(geom: PlaneGeometry) -> Self {
        let pixels = geom.pixels();
        Self {
            luma: vec![0.0; pixels],
            field: FocusField::new(geom),
            box_scratch: vec![0.0; pixels],
            regularised: vec![0.0; pixels],
        }
    }

    fn compute(
        &mut self,
        frame: &strehl_raw::Frame,
        geom: PlaneGeometry,
        levels: Levels,
        camera: &str,
        iso: Option<f32>,
        noise: &NoiseModel,
        index: u16,
    ) -> Result<()> {
        anyhow::ensure!(
            frame.geometry() == geom,
            "frame {index} ({}) has geometry {:?}, expected {:?}",
            frame.path.display(),
            frame.geometry(),
            geom
        );
        anyhow::ensure!(
            frame.levels == levels,
            "frame {index} ({}) has levels {:?}, expected {:?}",
            frame.path.display(),
            frame.levels,
            levels
        );
        anyhow::ensure!(
            frame.camera == camera && frame.iso == iso,
            "frame {index} ({}) has camera/ISO {:?}/{:?}, expected {:?}/{:?}",
            frame.path.display(),
            frame.camera,
            frame.iso,
            camera,
            iso
        );
        green_luma(frame, levels.black, &mut self.luma);
        self.field.compute(&self.luma, noise);
        regularise(
            self.field.values(),
            geom,
            &mut self.box_scratch,
            &mut self.regularised,
        );
        Ok(())
    }
}

struct CalibrationPass1 {
    stats: FocusStats,
    spectral: SpectralAccumulator,
}

fn calibrate_gate(
    dir: &Path,
    limit: Option<usize>,
    analysis_width: Option<usize>,
    analysis_height: Option<usize>,
    workers: usize,
) -> Result<()> {
    anyhow::ensure!(workers > 0, "--workers must be at least 1");
    let paths = raw_paths(dir, limit)?;
    anyhow::ensure!(
        paths.len() < u16::MAX as usize,
        "{} frames exceeds the u16 winner-index range",
        paths.len()
    );
    let first = strehl_raw::decode(&paths[0]).context("decoding the calibration prologue")?;
    let geom = first.geometry();
    let levels = first.levels;
    let camera = first.camera.clone();
    let iso = first.iso;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    let spectral_config = SpectralConfig::new(
        analysis_width.unwrap_or(first.active.width),
        analysis_height.unwrap_or(first.active.height),
    )?;
    drop(first);

    let worker_count = workers.min(paths.len());
    let chunk_len = paths.len().div_ceil(worker_count);
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(worker_count)
        .build()
        .context("building the calibration worker pool")?;

    let pass1_started = Instant::now();
    let pass1_parts: Vec<Result<CalibrationPass1>> = pool.install(|| {
        paths
            .par_chunks(chunk_len)
            .enumerate()
            .map(|(chunk_index, chunk)| {
                let first_index = chunk_index * chunk_len;
                let mut scratch = CalibrationScratch::new(geom);
                let mut stats = FocusStats::new(geom);
                let mut spectral = SpectralAccumulator::new(spectral_config);
                for (offset, path) in chunk.iter().enumerate() {
                    let index = (first_index + offset) as u16;
                    let frame = strehl_raw::decode(path)
                        .with_context(|| format!("decoding calibration frame {index}"))?;
                    scratch.compute(&frame, geom, levels, &camera, iso, &noise, index)?;
                    stats.fold(index, &scratch.regularised)?;
                    spectral.observe(index, &frame, levels.black, &noise)?;
                }
                Ok(CalibrationPass1 { stats, spectral })
            })
            .collect()
    });
    let mut pass1_parts = pass1_parts
        .into_iter()
        .collect::<Result<Vec<CalibrationPass1>>>()?
        .into_iter();
    let mut pass1 = pass1_parts
        .next()
        .context("calibration produced no pass-one workers")?;
    for part in pass1_parts {
        pass1.stats.absorb(&part.stats)?;
        pass1.spectral.absorb(part.spectral)?;
    }
    anyhow::ensure!(
        pass1.stats.frames_folded() as usize == paths.len()
            && pass1.spectral.frames() == paths.len(),
        "pass one did not fold every frame"
    );
    let pass1_seconds = pass1_started.elapsed().as_secs_f64();

    let targets = [
        pass1.spectral.target(0.950)?,
        pass1.spectral.target(1.000)?,
        pass1.spectral.target(1.093)?,
    ];
    let nominal = &targets[1];
    anyhow::ensure!(
        nominal.n_eff.is_finite() && nominal.n_eff >= 1.0 && nominal.n_eff <= paths.len() as f64,
        "nominal spectral target {:.6} is outside [1, {}]",
        nominal.n_eff,
        paths.len()
    );

    let pass2_started = Instant::now();
    let hist_parts: Vec<Result<AdmissionHistogram>> = pool.install(|| {
        paths
            .par_chunks(chunk_len)
            .enumerate()
            .map(|(chunk_index, chunk)| {
                let first_index = chunk_index * chunk_len;
                let mut scratch = CalibrationScratch::new(geom);
                let mut histogram = AdmissionHistogram::new(geom);
                for (offset, path) in chunk.iter().enumerate() {
                    let index = (first_index + offset) as u16;
                    let frame = strehl_raw::decode(path)
                        .with_context(|| format!("decoding admission frame {index}"))?;
                    scratch.compute(&frame, geom, levels, &camera, iso, &noise, index)?;
                    histogram.fold(index, &pass1.stats, &scratch.regularised)?;
                }
                Ok(histogram)
            })
            .collect()
    });
    let mut hist_parts = hist_parts
        .into_iter()
        .collect::<Result<Vec<AdmissionHistogram>>>()?
        .into_iter();
    let mut histogram = hist_parts
        .next()
        .context("calibration produced no pass-two workers")?;
    for part in hist_parts {
        histogram.absorb(part)?;
    }
    anyhow::ensure!(
        histogram.frames_folded() as usize == paths.len(),
        "pass two folded {} frames, expected {}",
        histogram.frames_folded(),
        paths.len()
    );
    let (gate_zero_n_eff, widest_gate_n_eff) = histogram.admission_range();
    let solved = histogram.solve(nominal.n_eff)?;
    let pass2_seconds = pass2_started.elapsed().as_secs_f64();

    println!(
        "M81_CONFIG frames={} workers={} analysis={}x{} patch={} tile={}",
        paths.len(),
        worker_count,
        spectral_config.analysis_width,
        spectral_config.analysis_height,
        strehl_core::calibration::SPECTRAL_PATCH,
        strehl_core::calibration::SPECTRAL_TILE
    );
    for target in &targets {
        println!(
            "M81_SPECTRAL scale={:.3} n_eff={:.9} bands={:.9},{:.9},{:.9} \
                 textured={} frames={}",
            target.noise_scale,
            target.n_eff,
            target.per_band_n_eff[0],
            target.per_band_n_eff[1],
            target.per_band_n_eff[2],
            target.textured_patches,
            target.frames
        );
    }
    println!(
        "M81_GATE target={:.9} gate={:.9} realised={:.9} bracket={:.9},{:.9} \
             gate_zero={:.9} gate_widest={:.9} unreachable={}",
        solved.target_n_eff,
        solved.gate,
        solved.realised_n_eff,
        solved.lower_n_eff,
        solved.upper_n_eff,
        gate_zero_n_eff,
        widest_gate_n_eff,
        solved.unreachable
    );
    println!(
        "M81_TIMING pass1={pass1_seconds:.3} pass2={pass2_seconds:.3} total={:.3}",
        pass1_seconds + pass2_seconds
    );
    Ok(())
}

/// RAW files in `dir`, sorted by filename so that frame index is capture order.
fn raw_paths(dir: &Path, limit: Option<usize>) -> Result<Vec<PathBuf>> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .map(|e| matches!(e.to_ascii_lowercase().as_str(), "arw"))
                .unwrap_or(false)
        })
        .collect();
    paths.sort();
    if let Some(n) = limit {
        paths.truncate(n);
    }
    anyhow::ensure!(!paths.is_empty(), "no RAW files found in {}", dir.display());
    Ok(paths)
}

fn probe(dir: &Path, limit: Option<usize>) -> Result<()> {
    let paths = raw_paths(dir, limit)?;

    let bytes: u64 = paths
        .iter()
        .filter_map(|p| std::fs::metadata(p).ok().map(|m| m.len()))
        .sum();

    let t0 = Instant::now();
    let frames = strehl_raw::decode_all(&paths);
    let elapsed = t0.elapsed().as_secs_f64();

    let (ok, failed): (Vec<_>, Vec<_>) = frames.into_iter().partition(|r| r.is_ok());
    for e in &failed {
        if let Err(e) = e {
            tracing::error!("{e}");
        }
    }
    let ok: Vec<_> = ok.into_iter().map(|r| r.unwrap()).collect();
    anyhow::ensure!(!ok.is_empty(), "every frame failed to decode");

    let f = &ok[0];
    println!("camera          : {}", f.camera);
    println!(
        "iso             : {}",
        f.iso
            .map(|v| format!("{v:.0}"))
            .unwrap_or_else(|| "UNKNOWN".to_string())
    );
    println!("buffer          : {} x {}", f.stride, f.buffer_height);
    println!(
        "active area     : {} x {} at ({}, {})  [{:.2} MP]",
        f.active.width,
        f.active.height,
        f.active.x,
        f.active.y,
        f.active.pixels() as f64 / 1e6
    );
    println!(
        "levels          : black {}, white {}",
        f.levels.black, f.levels.white
    );
    println!(
        "wb coeffs       : [{}, {}, {}, {}]",
        f.wb_coeffs[0], f.wb_coeffs[1], f.wb_coeffs[2], f.wb_coeffs[3]
    );
    println!(
        "allocation      : {:.1} MB/frame, {:.1} MB useful ({:.1}% padding)",
        f.allocated_bytes() as f64 / 1e6,
        f.useful_bytes() as f64 / 1e6,
        100.0 * (1.0 - f.useful_bytes() as f64 / f.allocated_bytes() as f64)
    );
    println!();
    println!("decoded         : {} ok, {} failed", ok.len(), failed.len());
    println!("elapsed         : {elapsed:.3} s");
    println!("per frame       : {:.4} s", elapsed / ok.len() as f64);
    println!("throughput      : {:.1} MB/s", bytes as f64 / 1e6 / elapsed);
    println!(
        "60-frame stack  : {:.2} s",
        60.0 * elapsed / ok.len() as f64
    );

    Ok(())
}
