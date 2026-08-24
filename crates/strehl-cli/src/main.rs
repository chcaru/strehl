//! `strehl` command line.

mod align_cmd;
mod image_out;
mod merge_cmd;
mod stack;

use std::path::{Path, PathBuf};
use std::time::Instant;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};

use merge_cmd::MergeOptions;
use stack::{MemoryModel, Roi, StackOptions, parse_roi};
use strehl_core::merge::DEFAULT_GATE;

#[derive(Parser)]
#[command(name = "strehl", version, about = "Noise-aware RAW focus stacking")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Solve a bracket's inter-frame geometry and write a warp sidecar.
    ///
    /// Focus breathing changes magnification frame to frame, so a deep bracket
    /// is not registered as captured. This fits a similarity ladder over the
    /// stack and writes it to disk with its own provenance and held-out error,
    /// for the merge to gather through.
    Align(align_cmd::AlignArgs),

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
    /// It ALIGNS BY DEFAULT (M86c): focus breathing changes magnification frame
    /// to frame, and unregistered deep brackets drift 232.7 px corner-to-corner
    /// on bee-3-cpl. Set STREHL_ALIGN=0 to disable. Note the field of view
    /// shrinks ~7-10% so that every frame covers every output pixel.
    ///
    /// It does not yet deconvolve, reject outliers, or model occlusion.
    ///
    /// By DEFAULT the output is BINNED, LINEAR, CAMERA-NATIVE RGB: each output
    /// pixel is one real sensor quad, R = R, G = (G1+G2)/2, B = B, at half the
    /// sensor's linear resolution, with white balance but NO colour matrix. It
    /// will look dark and grey-green in an ordinary viewer. That is correct: it
    /// is what measurement needs, and it is the file every number in this
    /// project's corpus was measured on. It is byte-frozen.
    ///
    /// Pass --srgb for something to LOOK AT: it applies the camera's colour
    /// matrix and the sRGB transfer curve, and since M95 it emits at full
    /// sensor resolution by default because binning destroys 10-32 % of
    /// top-octave green power outright. Pass --binned to get the old
    /// half-resolution viewing render back. Do not measure either file. See
    /// docs/research/M85-output-correctness.md and M95-resolution.md.
    ///
    /// --srgb ALONE IS FAITHFUL, NOT FLATTERING. bee-3-cpl's white background
    /// lands at 0.5734 in sRGB because the RAW background sits at 0.296 of the
    /// sensor's usable range and NO pixel in any of its 299 frames reaches 0.99
    /// of white: the capture is ~1.76 stops under-exposed and this reproduces
    /// it exactly. Pass --auto-exposure to have the gain chosen and PRINTED, or
    /// --exposure to set it yourself. Both are exposure only -- one multiply in
    /// linear light -- and both refuse to run without --srgb. See
    /// docs/research/M100-exposure.md.
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
        /// Render for viewing: camera colour matrix (to sRGB/BT.709 primaries,
        /// D65) then the sRGB transfer curve. For looking at, NOT for
        /// measuring. Changes what pre-M85 --srgb emitted.
        #[arg(long)]
        srgb: bool,
        /// Emit at full sensor resolution with a Malvar-He-Cutler demosaic
        /// instead of binning each 2x2 quad to one pixel. Doubles linear
        /// resolution; the extra samples are real, the colour at each is
        /// interpolated. Do not measure resolution on it.
        ///
        /// This is ON BY DEFAULT whenever --srgb is given, because binning
        /// destroys 10-32 % of top-octave green power outright (M95). Pass it
        /// explicitly to force full resolution WITHOUT --srgb.
        #[arg(long, conflicts_with = "binned")]
        demosaic: bool,
        /// Opt out: bin each 2x2 quad to one pixel in the --srgb render, as
        /// strehl did before M95. Halves linear resolution. Has no effect on
        /// the byte-frozen measurement output, which is always binned.
        #[arg(long)]
        binned: bool,
        /// Exposure for the viewing render, in STOPS. Requires --srgb.
        ///
        /// A gain of 2^STOPS applied in LINEAR light, before the sRGB transfer
        /// curve. The order is not a detail: the curve is not homogeneous, so
        /// f(g*x) != g*f(x), and a gain applied to ENCODED values scales R, G
        /// and B by different amounts in linear light -- it shifts the colour
        /// of every non-neutral pixel instead of changing the exposure.
        /// Exposure is photons times a constant, and photons live before the
        /// curve. (Where it sits relative to the colour matrix is free, because
        /// the matrix is linear and the two commute exactly.)
        ///
        /// It is exposure ONLY: one multiply. No contrast curve, no
        /// saturation, no highlight roll-off, nothing local. Every ratio that
        /// does not clip is preserved exactly, so the file is still a faithful
        /// render of the capture that differs from the un-exposed one by a
        /// number you chose.
        ///
        /// 0 is not "a gain of one", it is no exposure at all: the file is
        /// byte-identical to one written without this flag.
        ///
        /// Negative values need the = form: --exposure=-1.5
        #[arg(
            long,
            value_name = "STOPS",
            default_value_t = 0.0,
            allow_negative_numbers = true
        )]
        exposure: f32,
        /// Choose the exposure from the image and PRINT what was chosen.
        /// Requires --srgb; mutually exclusive with --exposure.
        ///
        /// THE RULE: put the 99.9th percentile of linear-sRGB luminance at
        /// 0.90, bounded to +/-6 stops and quantised to 1/100 stop so that the
        /// printed number reproduces the file exactly. Both numbers were
        /// MEASURED by sweeping 7 percentiles x 5 targets x 2 statistics across
        /// seven corpus stacks, not chosen by taste
        /// (docs/research/M100-exposure.md).
        ///
        /// Deterministic and never silent: it is an order statistic of the
        /// merged image, so the same input gives the same answer, and the run
        /// prints the --exposure=N that reproduces the file byte for byte.
        ///
        /// It can DARKEN. coffee-bean and foam are already exposed to the top
        /// of the range and carry 1.42% and 0.76% blown pixels; this pulls them
        /// down to 0.00% and 0.53%. It is an exposure, not a highlight rescue:
        /// what was clipped in the capture stays clipped.
        ///
        /// The statistic is always computed on the BINNED grid, so --demosaic
        /// cannot change the exposure (MEASURED: the two grids put the
        /// percentile at 0.322559 and 0.322549, the same 1/100-stop answer).
        #[arg(long)]
        auto_exposure: bool,
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
        /// Emit at full sensor resolution with a Malvar-He-Cutler demosaic
        /// instead of binning each 2x2 quad to one pixel.
        ///
        /// ON BY DEFAULT with --srgb, matching `stack`. It must match: these
        /// two subcommands exist to be compared against each other, and until
        /// M104c measured it, `stack --srgb` emitted 7032 x 4688 while this one
        /// emitted 3516 x 2344. Magnification reads as sharpness (discipline
        /// 606), so the asymmetry made the naive baseline look softer than it
        /// is -- a bias running TOWARD this project's own thesis.
        #[arg(long, conflicts_with = "binned")]
        demosaic: bool,
        /// Opt out: bin each 2x2 quad to one pixel in the --srgb render.
        /// Halves linear resolution. No effect on the byte-frozen measurement
        /// output, which is always binned.
        #[arg(long)]
        binned: bool,
        /// Also write the winner map: a 16-bit grayscale TIFF holding the
        /// literal winning frame index per pixel. Smooth depth-ordered bands
        /// are what a real scene should give; salt-and-pepper speckle in it is
        /// the argmax defect made visible. Values are 0..N-1, so autoscale it
        /// to look at it.
        #[arg(long, value_name = "PATH")]
        index_map: Option<PathBuf>,
        /// Multiply linear light by `2^STOPS` before the sRGB curve. Requires
        /// `--srgb`; refuses to combine with `--auto-exposure`.
        ///
        /// This exists so that the naive baseline can be compared with `stack`
        /// **at the same exposure**. It was added by M109 because the defect it
        /// was chasing -- blown neutral highlights rendering magenta -- is
        /// amplified 2.8x by a negative exposure, so a comparison run at a
        /// different gain from `stack`'s measures a different thing. Same
        /// reasoning as M104c's resolution fix: these two subcommands exist to
        /// be compared, so an asymmetry between them is a thumb on the scale.
        #[arg(long, default_value_t = 0.0, allow_negative_numbers = true)]
        exposure: f32,
        /// Choose the exposure from the image and print it, exactly as
        /// `stack --auto-exposure` does. Requires `--srgb`.
        #[arg(long)]
        auto_exposure: bool,
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
        Command::Align(args) => align_cmd::run(&args),
        Command::Probe { dir, limit } => probe(&dir, limit),
        Command::ArgmaxBaseline {
            dir,
            out,
            limit,
            srgb,
            demosaic,
            binned,
            index_map,
            flat_roi,
            memory_model,
            exposure,
            auto_exposure,
        } => stack::run(&StackOptions {
            dir,
            out,
            limit,
            srgb,
            // Identical resolution rule to `stack`, and it must stay identical:
            // the two subcommands are compared against each other, so any
            // asymmetry here is a thumb on the scale. The measurement path
            // passes neither flag, leaving this false and the byte-frozen
            // output untouched.
            demosaic: demosaic || (srgb && !binned),
            index_map,
            flat_roi,
            memory_model,
            exposure,
            auto_exposure,
        }),
        Command::Stack {
            dir,
            out,
            limit,
            srgb,
            demosaic,
            binned,
            exposure,
            auto_exposure,
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
            // M95: --srgb is the "for looking at" path, and binning it throws
            // away half the linear resolution of the capture. Full resolution
            // is the default there unless --binned asks for the old behaviour.
            // The measurement path passes neither flag, so this is false for it
            // and the byte-frozen output is untouched.
            demosaic: demosaic || (srgb && !binned),
            exposure,
            auto_exposure,
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
