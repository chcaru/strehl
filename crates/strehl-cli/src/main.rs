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

    /// Stack a directory of RAW files into one image.
    ///
    /// TWO MERGES LIVE HERE AND --merge PICKS ONE.
    ///
    ///   pyramid (DEFAULT) A Laplacian multi-band merge. Selection happens per
    ///             band and per coefficient, not per pixel, so a depth boundary
    ///             is a transition inside each band's own frequency range
    ///             instead of a step in the image. The selection exponent ramps
    ///             with scale: near winner-take-all in the fine bands, where
    ///             all the acuity is and where a wrong pick is one
    ///             high-frequency coefficient nobody can see, and gently
    ///             blended in the coarse bands, where a wrong pick IS the
    ///             "cut-out sticker" rim. Every good render in this project's
    ///             research corpus came from this merge; until it was wired
    ///             here it was reachable only from an example binary.
    ///
    ///   estimator The regularised-winner, noise-gated merge described below.
    ///             It is what `strehl stack` did before the default moved, and
    ///             the older quality numbers in the corpus were measured on it.
    ///
    ///             `estimator` is NOT the default any more, and that is a
    ///             measurement rather than an opinion. It is the arm that draws
    ///             the white halo around a dark subject on a bright ground.
    ///             Measured on flower-bud-alone-cpl through one binary with
    ///             both arms camera-linear and one mask, the estimator's
    ///             backdrop sits 4739 DN below its own far field across the
    ///             80-200 px aura zone; the pyramid sits 166 DN below. Pass
    ///             `--merge estimator` to get the merge the older corpus was
    ///             made with -- it is byte-identical to the pre-switch binary.
    ///
    /// STREHL_MERGE=pyramid|estimator does the same for a harness that cannot
    /// edit the command line; the flag wins. An unrecognised value in either
    /// channel is an ERROR, never a silent fall back to the other merge.
    ///
    /// The estimator-only flags -- --gate, --target-n-eff, --index-map,
    /// --n-eff-map, --photometric, --stats, --flat-roi, --detail-roi -- are
    /// REFUSED under the pyramid backend rather than accepted and ignored. A
    /// flag that parses and does nothing is indistinguishable from one that
    /// works, and this project has shipped that failure before.
    ///
    /// NOTE, now that the pyramid is the default: a harness that passes one of
    /// those flags WITHOUT also passing `--merge estimator` still RUNS, and
    /// gets the ESTIMATOR. The backend is inferred from the flags when `--merge`
    /// is absent, so naming an estimator parameter selects the estimator rather
    /// than colliding with a backend the caller never chose. Exit codes are
    /// unchanged: measured, 0 of 8 fail.
    ///
    /// The consequence is the one worth stating plainly. Those call lines are
    /// not broken, but they are no longer on the merge this tool now defaults
    /// to -- they keep the older arm, including the faceted "cut-out sticker"
    /// plateaus the pyramid was made to remove. Swept over this repository at
    /// the time of the flip that is 338 call sites in 185 files, of which 189
    /// are executable; `--gate` alone accounts for 275. So the run log names the
    /// backend AND the reason, and says outright when an inferred backend is
    /// not the default. Drop the flag to get the new merge; pass
    /// `--merge estimator` to say you meant the old one.
    ///
    /// Naming a backend explicitly still refuses a contradicting flag, exactly
    /// as before. Inference applies only where nothing was stated.
    ///
    /// WHAT THE ESTIMATOR BACKEND DOES, by noise-gated ESTIMATION:
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
        /// Where to write the merged 16-bit RGB TIFF. Omit it to measure
        /// without writing an image.
        ///
        /// AT MOST one --gate, which is not the same as requiring one:
        /// omitting --gate folds DEFAULT_GATE and writes an image, which is
        /// the common case. What is refused is TWO or more, because one file
        /// cannot carry two gates.
        ///
        /// The constraint is the estimator's, enforced in `run_estimator`
        /// before a frame is read. Under `--merge pyramid` the band gate is
        /// `--pyramid-gate`, which takes a single value by construction, and
        /// `--gate` is refused outright.
        // This help used to state the constraint backwards, claiming --gate was
        // required. It never was: main.rs fills an empty `gates` with
        // DEFAULT_GATE before run_estimator sees it, and run_estimator refuses
        // only `len() != 1`. The wrong version turned a working command line
        // into one users believed was illegal. Kept as a `//` note rather than
        // `///` so the retired claim does not reach `--help` itself, where a
        // reader would meet the false sentence again.
        #[arg(short, long)]
        out: Option<PathBuf>,
        /// Stack at most this many frames, in filename order.
        #[arg(short, long)]
        limit: Option<usize>,
        /// Which merge produces the pixels: `pyramid` (the default) or
        /// `estimator`. See this subcommand's help for what each one is.
        ///
        /// STREHL_MERGE does the same for a harness that cannot edit the
        /// command line; this flag wins. An unrecognised value is an error in
        /// either channel -- neither can mean a backend by accident.
        #[arg(long = "merge", value_name = "BACKEND")]
        merge_backend: Option<String>,
        /// Number of Laplacian bands in the `pyramid` merge.
        ///
        /// Deeper means the coarsest band is coarser, so overall tone is
        /// carried further from the pixel grid. Too shallow and the base band
        /// still holds structure: `--pyramid-bands 2` keeps acuity but loses
        /// the darkest densities -- grey ink instead of black.
        #[arg(long, value_name = "N")]
        pyramid_bands: Option<usize>,
        /// Multiples of the modelled band-noise power a coefficient's local
        /// energy must exceed before it may influence selection, in the
        /// `pyramid` merge. Below it NO frame wins and the merge averages.
        ///
        /// NOT the same quantity as --gate, which is the estimator's threshold
        /// on a focus field in units of focus noise. They are different numbers
        /// on different scales and must not be transferred between backends.
        #[arg(long, value_name = "F")]
        pyramid_gate: Option<f32>,
        /// Selection exponent at the COARSEST band of the `pyramid` merge; the
        /// floor of the per-octave ramp, not a single global value.
        #[arg(long, value_name = "F")]
        pyramid_exponent: Option<f32>,
        /// How much sharper selection is per octave toward the fine bands, in
        /// the `pyramid` merge. 1.0 disables the ramp and restores a single
        /// global exponent.
        #[arg(long, value_name = "F")]
        pyramid_sharpen: Option<f32>,
        /// Selection rule for the `pyramid` merge: `soft` (the default, a
        /// convex combination weighted by excess band power) or `hard-max`
        /// (the textbook PMax argmax).
        ///
        /// `hard-max` is a CONTROL ARM, not an option to ship: it inherits one
        /// frame's noise everywhere and can take adjacent coefficients from
        /// opposite-signed frames, which is ringing.
        #[arg(long, value_name = "MODE")]
        pyramid_select: Option<String>,
        /// How the `pyramid` merge combines the coarsest residual, the band
        /// that carries overall tone: `mean` (the default) or `weighted`.
        ///
        /// MEASURED on flower-bud-alone-cpl: weighting the base band cost
        /// -475.0 DN of global level and 835.0 DN of position-dependent
        /// structure, against +11.0 DN and 45.0 DN for the mean, with no
        /// difference in aura removal between them. `weighted` is kept
        /// reachable because a default chosen by measurement needs the arm it
        /// beat to remain runnable.
        #[arg(long, value_name = "MODE")]
        pyramid_base: Option<String>,
        /// Render for viewing: camera colour matrix (to sRGB/BT.709 primaries,
        /// D65) then the sRGB transfer curve. For looking at, NOT for
        /// measuring. Changes what pre-M85 --srgb emitted.
        #[arg(long)]
        srgb: bool,
        /// Render into linear sRGB: camera colour matrix (to sRGB/BT.709
        /// primaries, D65) and then STOP. No transfer curve.
        ///
        /// THIS IS THE MODE TO MEASURE IN. The standing rule is that quality is
        /// never judged on an --srgb render, because the transfer curve is a
        /// strong non-linearity that moves every ratio a metric computes; more
        /// than one result in this project has been retracted for exactly that.
        /// But the only alternative used to be the default, whose primaries are
        /// the sensor's own and are stated nowhere -- so a measurement was
        /// either taken through a curve or in an undeclared space. This applies
        /// the matrix and stops before the curve: a STATED colorimetric target
        /// that is still linear.
        ///
        /// The file will look dark in an ordinary viewer. That is correct, and
        /// it is the same darkness the default has; the difference is that this
        /// one says what its primaries are, in the file.
        #[arg(long, conflicts_with = "srgb")]
        linear_srgb: bool,
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
        /// Correct lateral chromatic aberration using a named optical profile.
        ///
        /// Lateral CA is a radial magnification difference between the colour
        /// channels: red is imaged at a slightly different scale from green, so
        /// every edge gains a coloured rim that is absent on axis and grows
        /// with distance from the centre. On this path M107 measured it as a
        /// clean one-parameter fit, `eps_R = -704.5 ppm`, worth about three
        /// output pixels at the corner.
        ///
        /// MEASURED, camera-linear, one binary, two subjects. Mean |R-G| at
        /// strong edges normalised by local green, in six radial bands from
        /// centre to corner:
        ///
        ///   flat-on-ruler-cpl  off  0.070 0.074 0.106 0.150 0.164 0.227
        ///   flat-on-ruler-cpl  on   0.068 0.075 0.084 0.086 0.087 0.089
        ///   foam               off  0.167 0.209 0.278 0.348 0.418 0.461
        ///   foam               on   0.148 0.125 0.127 0.126 0.124 0.152
        ///
        /// What marks the correction as right is not that the numbers fall. It
        /// is that the RADIAL GROWTH is gone and a flat, non-radial floor is
        /// left behind -- demosaic, noise and axial CA, none of which this
        /// touches. The frame centre is unchanged, which is the built-in null:
        /// lateral CA is zero on axis by construction, so anything that moved
        /// the centre would be doing something other than what it claims.
        ///
        /// This is DEFAULTED ON when the gear matches. The profile describes
        /// one specific camera, lens and teleconverter, and applying it to a
        /// different optical path would ADD an aberration rather than remove
        /// one -- so the render path resolves it through the gear guard, which
        /// reads the body and composed lens id out of the file and declines
        /// unless both match. It cannot see a filter change.
        ///
        /// Pass `off` (or `0`/`false`) for an uncorrected render. That is now
        /// the only way to get one, so it is the supported escape hatch rather
        /// than an incidental spelling.
        ///
        /// An unknown key is an error, not a silent no-op -- the failure mode
        /// worth avoiding is a run that looks like it corrected and did not.
        /// Pass any invalid name to be told which profiles exist.
        ///
        /// Takes precedence over the STREHL_FIX_CA environment variable, and
        /// over the gear match, in BOTH directions.
        #[arg(long, value_name = "PROFILE")]
        fix_ca: Option<String>,
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
        ///
        /// ESTIMATOR BACKEND ONLY. Under `--merge pyramid` this is refused, not
        /// ignored. Omitting it entirely means DEFAULT_GATE, exactly as before.
        #[arg(long = "gate", value_name = "T", num_args = 1..)]
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

        /// Also write the election map: a 16-bit grayscale TIFF holding the
        /// index of the frame that won pass one, per pixel.
        ///
        /// DEBUG OUTPUT. It does not change the merged image by a byte -- it
        /// reads state pass one has already finished, before pass two starts.
        ///
        /// On the PLANE grid, half sensor resolution, one election per 2x2 CFA
        /// quad; scale by two to overlay a --demosaic render. Values are the
        /// literal 0-based frame index in filename order, so 0..N-1: autoscale
        /// it to look at it. `STREHL_DUMP_ELECTION=<path>` does the same for a
        /// harness that cannot edit the command line; this flag wins.
        #[arg(long, value_name = "PATH")]
        index_map: Option<PathBuf>,

        /// Also write the n_eff map: a 16-bit grayscale TIFF holding the number
        /// of frames averaged into each pixel.
        ///
        /// DEBUG OUTPUT. It does not change the merged image by a byte -- it
        /// reads state pass two has already finished.
        ///
        /// The twin of --index-map, on the same PLANE grid at half sensor
        /// resolution, so the two overlay pixel-for-pixel with no resampling:
        /// one says WHICH frame won, this says HOW MANY were indistinguishable
        /// from it. Values are literal frame counts starting at 1, so autoscale
        /// it to look at it.
        ///
        /// n_eff is already this project's headline quality number, reported as
        /// a scalar mean -- but the gate that reaches n_eff = 3 varies 0.7618 to
        /// 21.9934 across the corpus, a factor of 28.9, so a mean over a field
        /// that varies that much between scenes is hiding its own structure.
        /// This is where that structure becomes visible.
        ///
        /// AT MOST one --gate, because n_eff is per-gate. Omitting --gate uses
        /// DEFAULT_GATE and writes the map for it; two or more are refused,
        /// rather than silently writing gate[0]'s map under a name that does
        /// not say so. ESTIMATOR BACKEND ONLY: refused under `--merge pyramid`.
        /// `STREHL_DUMP_NEFF=<path>` does the same for a harness that cannot
        /// edit the command line; this flag wins.
        #[arg(long, value_name = "PATH")]
        n_eff_map: Option<PathBuf>,

        /// Fit and apply a per-frame affine photometric gain before the focus
        /// measure. OPT-IN; the default merge is unchanged.
        ///
        /// Three-valued: `off` (the default), `on`, or `auto`. A bare
        /// `--photometric` still means `on`, as it always has.
        ///
        /// M24 measured real per-frame level drift that EXIF does not predict
        /// -- 0.91% peak-to-peak on 109MSDCF, 11.70% on coffee-bean -- so a
        /// gated average without this term is reading an exposure change as a
        /// signal change. The gain is fitted as the MEAN over a fixed,
        /// reference-derived, eroded background region, and the noise model is
        /// scaled with the data so the gate stays calibrated.
        ///
        /// `auto` decides per stack from that same measured drift, because the
        /// unconditional switch is not uniformly good: M122 measured it helping
        /// tweezers-cpl (13.765% drift) and HARMING bee-3-cpl (1.629%) by 6.4%.
        /// When it cannot decide -- too few or too many frames, no usable
        /// drift, no background to fit against -- it says so and falls back to
        /// off. It never falls back silently.
        ///
        /// This corrects frame LEVEL. It is not a sharpness claim.
        /// `STREHL_PHOTOMETRIC=off|on|auto` does the same for a harness that
        /// cannot edit the command line; this flag wins.
        #[arg(
            long,
            value_name = "MODE",
            num_args = 0..=1,
            default_missing_value = "on"
        )]
        photometric: Option<String>,

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

        /// Interpolator each frame is gathered with by the registration:
        /// nearest, bilinear, catmull-rom, lanczos2 or lanczos3.
        ///
        /// THE DEFAULT DOES NOT MOVE. catmull-rom is what every quality number
        /// in this project's corpus was measured through, and a run that omits
        /// this flag is byte-identical to one from before the flag existed.
        /// Whether the default SHOULD move is a pre-registered decision in
        /// docs/research/ORCH-kernel-decision.md, not a setting.
        ///
        /// COST, AND IT IS THE POINT OF THE FLAG. Measured as a BOUND on a
        /// loaded machine rather than as a value (M118 Y10): lanczos3 costs
        /// ROUGHLY 2.9x-3.9x the default's whole-merge wall clock (2.91x bee,
        /// 3.21x text, 3.92x ruler) and lanczos2 2.3x-2.9x. nearest and
        /// bilinear are cheaper (0.37x-0.69x) and worse. A quality change that
        /// cannot be declined is a tax rather than a default, which is why this
        /// flag exists before any default moves.
        ///
        /// WHAT LANCZOS-3 BUYS, honestly: +0.0859 to +0.1125 dex in the detail
        /// decile end-to-end -- of which a closed form over the kernel's own
        /// coefficients, using no image at all, predicts all but 11.9%. It also
        /// sharpens lateral chromatic-aberration fringes into visibility. Read
        /// docs/research/M118-resampler.md before believing the number.
        /// lanczos2 is measured as dead weight (+0.0027 to +0.0052 dex at
        /// 2.3x-2.9x) and is offered for reproducibility, not as a setting.
        ///
        /// It reaches pixels through the SOLVE only. If STREHL_WARPMAP names a
        /// sidecar, that sidecar's own recorded resampler wins and the run says
        /// so on stderr.
        #[arg(long, value_name = "NAME", default_value = align_cmd::DEFAULT_RESAMPLER_NAME)]
        resampler: String,
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
            merge_backend,
            pyramid_bands,
            pyramid_gate,
            pyramid_exponent,
            pyramid_sharpen,
            pyramid_select,
            pyramid_base,
            srgb,
            linear_srgb,
            demosaic,
            binned,
            fix_ca,
            exposure,
            auto_exposure,
            gates,
            flat_roi,
            detail_roi,
            index_map,
            n_eff_map,
            photometric,
            target_n_eff,
            stats,
            stats_placebo,
            confidence_tail,
            resampler,
        } => {
            // The lateral-CA profile is selected from the process environment
            // by `strehl_core::optics::profile_for_capture_env`, which the
            // aligner reads per frame and which the status line resolves the
            // same way. Publishing the flag into the environment here keeps
            // that single source of truth and takes no colour decision inside
            // the merge. An absent flag is not "off": it means the gear guard
            // decides, which is what makes the correction default-on.
            //
            // SAFETY: `set_var` requires that no other thread is touching the
            // environment concurrently. This is the CLI entry point: argument
            // parsing is done, and nothing before this line has spawned a
            // thread. The worker pool is created inside `merge_cmd::run`,
            // below, so the write strictly happens-before any reader exists.
            if let Some(key) = fix_ca.as_deref() {
                unsafe { std::env::set_var(strehl_core::optics::CA_ENV, key) };
            }

            // Resolved here, alongside `resampler` and `photometric`, so that
            // an unrecognised spelling is one error in one place.
            //
            // The refusal table is built FIRST, because the backend is now
            // partly inferred from it: the same rows that say "this flag is
            // refused under the pyramid" also say "this flag belongs to the
            // estimator". Deriving both from one table is the point -- a
            // separate list of family membership would be a second place to
            // record the same fact, and the two would drift.
            let wrong_backend: &[(&str, bool, merge_cmd::MergeBackend, &str)] = &[
                ("--gate", !gates.is_empty(), merge_cmd::MergeBackend::Pyramid,
                 "--pyramid-gate is the pyramid's noise gate, but it is a DIFFERENT QUANTITY: a \
                  multiple of the modelled band-noise power (default 2.0), where --gate is a \
                  multiple of the focus-response SD (default 4.0). The number does NOT carry \
                  over -- re-choose it, do not rename it."),
                ("--target-n-eff", target_n_eff.is_some(), merge_cmd::MergeBackend::Pyramid,
                 "no counterpart. n_eff counts the frames the gated average admitted at a pixel; \
                  the pyramid weights every frame per band coefficient, so there is no per-pixel \
                  frame count to solve a gate against."),
                ("--index-map", index_map.is_some(), merge_cmd::MergeBackend::Pyramid,
                 "no counterpart. The pyramid elects per band coefficient, not per pixel, so no \
                  single frame index owns an output pixel."),
                ("--n-eff-map", n_eff_map.is_some(), merge_cmd::MergeBackend::Pyramid,
                 "no counterpart, for the same reason as --target-n-eff."),
                ("--photometric", photometric.is_some(), merge_cmd::MergeBackend::Pyramid,
                 "NOT YET IMPLEMENTED on this backend, rather than inapplicable. The per-frame \
                  affine gain would apply unchanged, but fitting it needs every frame's flux \
                  before the first frame is folded, which the pyramid's single-pass fold does \
                  not currently do."),
                ("--stats", stats, merge_cmd::MergeBackend::Pyramid,
                 "no counterpart. Through-focus statistics describe the estimator's focus field, \
                  which this backend does not compute."),
                ("--stats-placebo", stats_placebo, merge_cmd::MergeBackend::Pyramid,
                 "no counterpart; it is a control for --stats."),
                ("--flat-roi", flat_roi.is_some(), merge_cmd::MergeBackend::Pyramid,
                 "no counterpart. The ROI diagnostics report on the estimator's noise invariant."),
                ("--detail-roi", detail_roi.is_some(), merge_cmd::MergeBackend::Pyramid,
                 "no counterpart, for the same reason as --flat-roi."),
                ("--pyramid-bands", pyramid_bands.is_some(), merge_cmd::MergeBackend::Estimator,
                 "no counterpart. The estimator has no band pyramid to set a depth on."),
                ("--pyramid-gate", pyramid_gate.is_some(), merge_cmd::MergeBackend::Estimator,
                 "--gate is the estimator's noise gate, but it is a DIFFERENT QUANTITY: a \
                  multiple of the focus-response SD (default 4.0), where --pyramid-gate is a \
                  multiple of the modelled band-noise power (default 2.0). The number does NOT \
                  carry over."),
                ("--pyramid-exponent", pyramid_exponent.is_some(), merge_cmd::MergeBackend::Estimator,
                 "no counterpart. The estimator's selection is a gated average, not a weighted \
                  combination with a tunable exponent."),
                ("--pyramid-sharpen", pyramid_sharpen.is_some(), merge_cmd::MergeBackend::Estimator,
                 "no counterpart; it ramps the exponent across bands."),
                ("--pyramid-select", pyramid_select.is_some(), merge_cmd::MergeBackend::Estimator,
                 "no counterpart; it chooses between soft and hard-max band selection."),
                ("--pyramid-base", pyramid_base.is_some(), merge_cmd::MergeBackend::Estimator,
                 "no counterpart; it chooses how the base band is formed."),
            ];
            // A flag belonging to the other backend is REFUSED, not ignored.
            // The failure this guards against is the one the whole switch
            // exists to escape: a flag that parses, prints nothing, and does
            // nothing is indistinguishable at the terminal from one that
            // works. Each entry pairs the user's spelling with whether they
            // actually passed it, so a default can never trip the refusal.
            //
            // The fourth column is the migration. A bare refusal is correct but
            // it strands the caller, so it names the counterpart -- and says
            // plainly when there ISN'T one. Where a counterpart exists but
            // means something else, that is said too: silently carrying a
            // number across two different quantities is the same class of
            // defect as ignoring the flag.
            let given_of = |want: merge_cmd::MergeBackend| -> Vec<&str> {
                wrong_backend
                    .iter()
                    .filter(|(_, given, refused_under, _)| *given && *refused_under == want)
                    .map(|(flag, _, _, _)| *flag)
                    .collect()
            };
            // "Refused under the pyramid" and "belongs to the estimator" are
            // the same statement read from opposite ends.
            let estimator_flags = given_of(merge_cmd::MergeBackend::Pyramid);
            let pyramid_flags = given_of(merge_cmd::MergeBackend::Estimator);

            let choice = merge_cmd::choose_merge_backend(
                merge_backend.as_deref(),
                &estimator_flags,
                &pyramid_flags,
            )?;
            let backend = choice.backend;
            // Inference must never be silent, or it reintroduces exactly the
            // failure the refusal guards against. After the flip, a caller who
            // passes --gate is opting out of the better merge; they are told so
            // and told how to opt back in.
            eprintln!("merge backend   : {}", choice.why);
            if choice.source == merge_cmd::MergeSource::Inferred
                && backend != merge_cmd::DEFAULT_MERGE_BACKEND
            {
                eprintln!(
                    "                  NOTE: this is not the default merge. Your flags asked \
                     for {}, so that is what runs.",
                    backend.name()
                );
            }

            for (flag, given, refused_under, migration) in wrong_backend {
                anyhow::ensure!(
                    !(*given && backend == *refused_under),
                    "{flag} belongs to the {} merge, and --merge selected {}.\n  \
                     what to do  : {migration}\n  \
                     or          : pass --merge {} to use {flag} as it stands.\n\
                     Refused rather than ignored because a flag that silently does nothing looks \
                     exactly like one that works.",
                    refused_under.other().name(),
                    backend.name(),
                    refused_under.other().name(),
                );
            }

            let mut pyramid = strehl_core::pyramid::MergeConfig::default();
            if let Some(v) = pyramid_bands {
                pyramid.bands = v;
            }
            if let Some(v) = pyramid_gate {
                pyramid.gate = v;
            }
            if let Some(v) = pyramid_exponent {
                pyramid.exponent = v;
            }
            if let Some(v) = pyramid_sharpen {
                pyramid.sharpen_per_octave = v;
            }
            if let Some(v) = &pyramid_select {
                pyramid.select = merge_cmd::parse_select_mode(v)?;
            }
            if let Some(v) = &pyramid_base {
                pyramid.base = merge_cmd::parse_base_band(v)?;
            }

            merge_cmd::run(&MergeOptions {
            dir,
            out,
            limit,
            srgb,
            // Resolved here, once, from the two mutually exclusive flags, so
            // that no colour decision is taken inside the merge code. clap
            // already refuses the pair via `conflicts_with`; this re-checks it
            // because the invariant belongs to the type, not to the argument
            // parser, and `stack.rs` resolves the same way.
            space: image_out::OutputSpace::from_flags(srgb, linear_srgb)?,
            // M95: --srgb is the "for looking at" path, and binning it throws
            // away half the linear resolution of the capture. Full resolution
            // is the default there unless --binned asks for the old behaviour.
            // The measurement path passes neither flag, so this is false for it
            // and the byte-frozen output is untouched.
            demosaic: demosaic || (srgb && !binned),
            exposure,
            auto_exposure,
            // Filled in here rather than by clap, so that "the user passed a
            // gate" and "the user did not" stay distinguishable above. An
            // estimator run that omits --gate is unchanged: it still folds
            // DEFAULT_GATE and exactly that.
            gates: if gates.is_empty() {
                vec![DEFAULT_GATE]
            } else {
                gates
            },
            flat_roi,
            detail_roi,
            index_map,
            n_eff_map,
            // Resolved here, alongside `resampler`, so that an unrecognised
            // spelling is one error in one place. `--photometric` wins over
            // `STREHL_PHOTOMETRIC`; neither can mean ON by accident.
            photometric: merge_cmd::resolve_photometric_mode(photometric.as_deref())?,
            target_n_eff,
            stats,
            stats_placebo,
            confidence_tail,
            // Parsed here, by the same function `strehl align --resampler`
            // uses, so an unknown name is one error message in one place and
            // never a silent fall back to the default.
            resampler: align_cmd::parse_resampler(&resampler)?,
            backend,
            pyramid,
        })
        }
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

#[cfg(test)]
mod tests {
    use clap::CommandFactory;

    use super::merge_cmd::{DEFAULT_MERGE_BACKEND, MergeBackend};

    /// Every backend, so the assertions below can check the ones that are *not*
    /// the default as well as the one that is. A test that only ever looks at
    /// the winner cannot tell a correct label from a label that is on both.
    ///
    /// Adding a variant breaks [`exhaustive`] below rather than silently
    /// leaving the new backend unexamined here.
    const ALL_BACKENDS: [MergeBackend; 2] = [MergeBackend::Estimator, MergeBackend::Pyramid];

    #[allow(dead_code)]
    fn exhaustive(backend: MergeBackend) {
        match backend {
            MergeBackend::Estimator | MergeBackend::Pyramid => {}
        }
    }

    /// `strehl stack --help` as a user sees it, with runs of whitespace
    /// collapsed so that these assertions are about the words and not about
    /// where clap chose to wrap a column.
    fn stack_help() -> String {
        let mut cli = super::Cli::command();
        let stack = cli
            .find_subcommand_mut("stack")
            .expect("`strehl stack` must exist");
        stack
            .render_long_help()
            .to_string()
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ")
    }

    /// The rendered help must be big enough to be worth asserting against.
    ///
    /// Without this, every assertion below is one clap API change away from
    /// passing against an empty string, and a check that cannot fail is
    /// indistinguishable from a check that passed.
    #[test]
    fn the_help_this_module_reads_is_actually_rendered() {
        let help = stack_help();
        assert!(
            help.len() > 2000,
            "rendered `stack` long help is only {} chars; the label assertions \
             in this module would be vacuous. Did render_long_help() change?",
            help.len()
        );
        for backend in ALL_BACKENDS {
            assert!(
                help.contains(backend.name()),
                "rendered help never mentions the `{}` backend",
                backend.name()
            );
        }
    }

    /// The `(DEFAULT)` marker in the backend list must sit on the backend that
    /// [`DEFAULT_MERGE_BACKEND`] actually selects.
    ///
    /// This project has already shipped exactly this defect one level up: a
    /// commit subject asserted that `strehl stack` ran the pyramid merge by
    /// default, a later commit moved the default back, and the claim stayed in
    /// `git log --oneline` where every subsequent reader would meet it. A stale
    /// `(DEFAULT)` in `--help` is the same defect somewhere more people look.
    ///
    /// So this coupling is deliberate. Flipping the constant fails this test
    /// until the prose follows, and the failure names the file to edit.
    #[test]
    fn stack_help_marks_the_backend_the_constant_selects() {
        let help = stack_help();
        for backend in ALL_BACKENDS {
            let marker = format!("{} (DEFAULT)", backend.name());
            let should_be_marked = backend == DEFAULT_MERGE_BACKEND;
            assert_eq!(
                help.contains(&marker),
                should_be_marked,
                "the backend list in `stack --help` {} \"{}\", but \
                 DEFAULT_MERGE_BACKEND is `{}`. The marker is a claim about \
                 merge_cmd.rs's constant; fix the `Stack` doc comment in \
                 main.rs so the two agree.",
                if should_be_marked {
                    "is missing"
                } else {
                    "still carries"
                },
                marker,
                DEFAULT_MERGE_BACKEND.name(),
            );
        }
    }

    /// `--merge`'s own help names a default too, in different words, and it has
    /// to be the same backend.
    #[test]
    fn the_merge_flag_help_names_the_same_default() {
        let help = stack_help();
        for backend in ALL_BACKENDS {
            let claim = format!("`{}` (the default)", backend.name());
            assert_eq!(
                help.contains(&claim),
                backend == DEFAULT_MERGE_BACKEND,
                "`--merge`'s help and DEFAULT_MERGE_BACKEND (`{}`) disagree \
                 about \"{}\"",
                DEFAULT_MERGE_BACKEND.name(),
                claim,
            );
        }
    }

    /// The "is NOT the default yet" caveat has to name a backend that is, in
    /// fact, not the default -- and it has to be there at all.
    ///
    /// Counting matches rather than asserting a single `contains` is what keeps
    /// a deleted caveat from reading as a passed check.
    #[test]
    fn the_not_yet_caveat_names_a_backend_that_is_not_the_default() {
        let help = stack_help();
        let mut caveats = 0usize;
        for backend in ALL_BACKENDS {
            let caveat = format!("`{}` is NOT the default", backend.name());
            if help.contains(&caveat) {
                caveats += 1;
                assert_ne!(
                    backend, DEFAULT_MERGE_BACKEND,
                    "`stack --help` says \"{}\" while DEFAULT_MERGE_BACKEND \
                     selects that same backend",
                    caveat,
                );
            }
        }
        assert_eq!(
            caveats,
            ALL_BACKENDS.len() - 1,
            "expected the non-default backend to carry the \"is NOT the \
             default\" caveat, found {} such caveats in `stack --help`",
            caveats,
        );
    }

    /// `--out` and `--n-eff-map` both constrain how many `--gate` values may be
    /// given, and both used to state that constraint backwards.
    ///
    /// The retired wording read as "you must pass --gate". The enforcement says
    /// otherwise: `main.rs` fills an empty `gates` with `DEFAULT_GATE` before
    /// `run_estimator` sees it, and `run_estimator` refuses only `len() != 1`.
    /// So omitting the flag is legal and writes an image, and it is TWO or more
    /// that are refused. The help was wrong about the tool's own contract in
    /// the direction that turns a working command line into one a user believes
    /// is illegal.
    ///
    /// Counted in both directions on purpose. Asserting only the absence of the
    /// false claim would pass just as well if the whole paragraph were deleted,
    /// which is the failure mode this project keeps rediscovering: a check that
    /// cannot tell "corrected" from "gone".
    #[test]
    fn the_gate_multiplicity_claim_matches_what_is_enforced() {
        let help = stack_help().to_lowercase();

        let false_claim = help.matches("exactly one --gate").count();
        assert_eq!(
            false_claim, 0,
            "`stack --help` still claims \"exactly one --gate\" in {} place(s). \
             Omitting --gate is legal -- main.rs fills DEFAULT_GATE and \
             run_estimator refuses only two or more.",
            false_claim,
        );

        let true_claim = help.matches("at most one --gate").count();
        assert_eq!(
            true_claim, 2,
            "expected the \"at most one --gate\" wording on both --out and \
             --n-eff-map, found {} occurrence(s) in `stack --help`",
            true_claim,
        );
    }

    /// The NOTE about pre-flip command lines makes a MEASURED claim ("0 of 8
    /// fail") about a list it also enumerates. Those two must not drift apart.
    ///
    /// The claim was false once already: before backend inference landed, the
    /// NOTE said those flags "now fails where it used to run", and after
    /// inference every one of them runs and selects the estimator. Measured
    /// 0 of 8 failing. Prose that describes the tool's exit codes is as
    /// load-bearing as prose that names a default, so it gets the same
    /// treatment: coupled to something that changes when the truth changes.
    ///
    /// Adding a ninth estimator-only flag now fails this test until the
    /// measured count is re-taken, which is the point.
    #[test]
    fn the_migration_note_counts_the_flags_it_enumerates() {
        // The help is hard-wrapped, so collapse before matching: every one of
        // these phrases spans a line break at some terminal width.
        let help = stack_help();
        let flat = help.split_whitespace().collect::<Vec<_>>().join(" ");

        assert!(
            !flat.contains("now fails where it used to run"),
            "`stack --help` still claims the estimator-only flags fail without \
             `--merge estimator`. Backend inference makes them run and select \
             the estimator; measured 0 of 8 failing."
        );

        let list = flat
            .split_once("The estimator-only flags -- ")
            .and_then(|(_, r)| r.split_once(" -- are REFUSED"))
            .map(|(l, _)| l)
            .expect("could not find the estimator-only flag enumeration in --help");
        let enumerated = list.split(',').filter(|s| s.contains("--")).count();

        let claimed = flat
            .split_once("unchanged: measured, 0 of ")
            .and_then(|(_, r)| r.split_once(" fail"))
            .map(|(n, _)| n.trim().to_string())
            .expect("could not find the measured \"0 of N fail\" claim in --help");

        assert_eq!(
            claimed,
            enumerated.to_string(),
            "`stack --help` enumerates {} estimator-only flags but reports the \
             measurement over {}. Re-run \
             C:\\dev\\strehl-out\\BUILD-WIRE\\notecheck.ps1 and update both.",
            enumerated,
            claimed,
        );
    }

    /// [`MergeBackend::default()`] and [`DEFAULT_MERGE_BACKEND`] are one
    /// decision with one address, not two that happen to agree today.
    #[test]
    fn the_default_impl_defers_to_the_constant() {
        assert_eq!(MergeBackend::default(), DEFAULT_MERGE_BACKEND);
    }
}
