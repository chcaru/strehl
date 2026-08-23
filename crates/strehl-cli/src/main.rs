//! `strehl` command line.

mod image_out;
mod merge_cmd;
mod stack;

use std::path::{Path, PathBuf};
use std::time::Instant;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};

use merge_cmd::MergeOptions;
use stack::{MemoryModel, Roi, StackOptions, parse_roi};

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

    /// Stack a directory of RAW files by plain per-pixel argmax.
    ///
    /// THIS IS THE NAIVE BASELINE, ON PURPOSE. It selects, per pixel, the
    /// single frame with the highest noise-normalised Tenengrad focus measure
    /// and copies that frame's 2x2 quad. Selection is exactly the
    /// defect strehl exists to remove, and this subcommand is the reference
    /// artifact every later quality claim is measured against. It does not
    /// align, denoise, regularise the winner map, or blend frames.
    ///
    /// Output is BINNED, NOT DEMOSAICED: each output pixel is one real sensor
    /// quad, R = R, G = (G1+G2)/2, B = B, at half the sensor's linear
    /// resolution. There is no interpolation, so no demosaic artifact
    /// contaminates the baseline.
    ///
    /// Default output is LINEAR and will look very dark in an ordinary viewer.
    /// That is correct: it is what measurement needs. Pass --srgb for something
    /// to look at, and do not measure that file.
    Stack {
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

    /// Merge a directory of RAW files by noise-gated estimation.
    ///
    /// THIS IS THE THESIS. Two passes: pass one elects a winner per pixel from
    /// a 17x17-REGULARISED focus field, pass two averages every frame whose
    /// regularised response the calibrated noise model cannot separate from
    /// that winner. Where one frame is unambiguously sharpest it degenerates to
    /// selection; where several are indistinguishable it averages them, which
    /// is the only operation that goes below single-frame noise.
    ///
    /// It does not yet align, deconvolve, reject outliers, or model occlusion.
    ///
    /// The gate threshold is UNCALIBRATED on purpose. Pass several `--gate`
    /// values and they all run in the same pass two for the cost of one decode
    /// budget; calibrate against the reported mean n_eff.
    ///
    /// Output is BINNED, NOT DEMOSAICED, and LINEAR unless --srgb is passed.
    /// Do not measure an --srgb file.
    Merge {
        /// Directory containing RAW files.
        dir: PathBuf,
        /// Where to write the merged 16-bit RGB TIFF. Requires exactly one
        /// --gate. Omit it to measure without writing an image.
        #[arg(short, long)]
        out: Option<PathBuf>,
        /// Merge at most this many frames, in filename order.
        #[arg(short, long)]
        limit: Option<usize>,
        /// Apply the sRGB transfer curve. For looking at, NOT for measuring.
        #[arg(long)]
        srgb: bool,
        /// Gate threshold, in units of the combined focus noise: a frame is
        /// averaged in where its regularised response is within
        /// `t * sqrt(2) * FOCUS_NOISE_SD` of the winner's. Repeatable; every
        /// value is folded in the same pass two, so a sweep costs one decode
        /// budget rather than one per value.
        #[arg(long = "gate", value_name = "T", num_args = 1.., default_values_t = [0.5, 1.0, 2.0, 4.0])]
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

        /// Solve the gate ladder for the gate achieving this mean n_eff.
        ///
        /// This is the parameter to set, not --gate. A fixed gate is not a
        /// calibration, and the effect is far larger than fact 324 published:
        /// M52 re-measured all SEVEN stacks against the current pipeline and
        /// found mean n_eff at gate 2.0 spanning 1.177 (foam) to 14.386
        /// (coffee-bean), a 12.22x spread, with the gates that solve for a
        /// given n_eff spanning 0.7618 to 21.9934 - a factor of 28.9.
        ///
        /// Fact 324's own numbers for the two ISO-50 stacks are stale: they
        /// were folded before commit 2a4f5c5 corrected the ISO-50 gain floor,
        /// so 119MSDCF is 2.847 and not 2.258, and coffee-bean is 14.386 and
        /// not 7.422. Its stated mechanism - that n_eff is a roughly fixed
        /// fraction of bracket length - is refuted: n_eff/N ranges 11.6x.
        ///
        /// Practical consequence: foam CANNOT reach n_eff = 3 anywhere on the
        /// shipped 0.5-4.0 ladder. Fact 212's nwide = 3 is the calibration
        /// target, and on some stacks this flag is the only way to hit it.
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
        Command::Stack {
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
        Command::Merge {
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
