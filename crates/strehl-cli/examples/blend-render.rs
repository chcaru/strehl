//! `blend-render` — a full frame rendered through the Laplacian multi-band
//! merge, end to end, so the result can be put beside the shipped pipeline's
//! output and looked at.
//!
//! # Why this is an example and not a `--merge pyramid` flag
//!
//! Six agents share this working tree and the merge path is another agent's
//! lane. Wiring a second merge into `merge_cmd.rs` would mean two arms editing
//! one file, which is how work gets silently clobbered. This binary therefore
//! reads the *same* inputs, runs the *same* registration, and writes through
//! the *same* development code as `strehl stack --srgb --demosaic`, and differs
//! from it in exactly one place: the merge.
//!
//! `align_cmd.rs` and `image_out.rs` are pulled in with `#[path]` rather than
//! reimplemented. That is not a shortcut, it is the whole point — a
//! re-implementation of the develop path would make every tone difference in
//! the comparison ambiguous between "the merge changed" and "my copy of the
//! curve is slightly different". Neither file is modified, or even opened for
//! writing, by this lane.
//!
//! # What it does NOT do, and what that costs
//!
//! * **No photometric normalisation.** The shipped merge fits a per-frame gain
//!   from flux accumulated in a first pass over the frames. Doing that here
//!   would double the decode cost, which is the whole runtime. It is a real
//!   difference and it is stated in the report this binary prints. The expected
//!   consequence is small and *global*: the base band of a multi-band merge is
//!   close to a plain mean across frames, so an un-normalised gain drift lands
//!   as a slight overall exposure shift rather than as any local artefact.
//! * **No clip handling, no outlier rejection.** Both are separate stages in the
//!   shipped path and neither is what this arm is testing.
//!
//! ```text
//! cargo run --release -p strehl-cli --example blend-render -- \
//!     D:\personal\macro\lavendar-cpl C:\dev\strehl-out\BUILD-BLEND\lavendar.tiff
//! ```

#[allow(dead_code)]
#[path = "../src/align_cmd.rs"]
mod align_cmd;
#[allow(dead_code)]
#[path = "../src/image_out.rs"]
mod image_out;

use std::path::{Path, PathBuf};
use std::time::Instant;

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use strehl_core::align::Resampler;
use strehl_core::color;
use strehl_core::noise::{Levels, NoiseModel};
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::profile;
use strehl_core::pyramid::{
    BandMerge, BaseBand, FrameWorkspace, Hull, MergeConfig, SelectMode, Workspace, level_sizes,
    luma_variance,
};
use strehl_core::warpmap::{FrameWarp, WarpMap};

/// The four CFA planes, in the order the merge carries them and the order the
/// output mosaic is interleaved in.
const PLANES: usize = 4;
/// Index into a plane array. RGGB: `R` at (0,0), `G1` at (1,0), `G2` at (0,1),
/// `B` at (1,1) — matching `CfaPlane::rggb_at`.
const P_R: usize = 0;
const P_G1: usize = 1;
const P_G2: usize = 2;
const P_B: usize = 3;
/// `(dx, dy)` of each plane inside the 2x2 quad, in the same order.
const PLANE_OFFSETS: [(usize, usize); PLANES] = [(0, 0), (1, 0), (0, 1), (1, 1)];

struct Args {
    dir: PathBuf,
    out: PathBuf,
    limit: Option<usize>,
    chunks: usize,
    cfg: MergeConfig,
    linear: bool,
    camera_linear: bool,
    exposure_stops: f32,
}

fn parse_args() -> Result<Args> {
    let mut it = std::env::args().skip(1);
    let dir = it.next().context(
        "usage: blend-render <DIR> <OUT.tiff> [--limit N] [--bands N] [--gate F] \
         [--exponent F] [--hard-max] [--base-mean] [--base-weighted] [--unclamped] [--chunks N] \
         [--linear] [--camera-linear] [--exposure S]",
    )?;
    let out = it.next().context("an output path is required")?;
    let mut a = Args {
        dir: PathBuf::from(dir),
        out: PathBuf::from(out),
        limit: None,
        chunks: 0,
        cfg: MergeConfig::default(),
        linear: false,
        camera_linear: false,
        exposure_stops: 0.0,
    };
    while let Some(flag) = it.next() {
        let mut val = || -> Result<String> {
            it.next()
                .with_context(|| format!("{flag} needs a value"))
        };
        match flag.as_str() {
            "--limit" => a.limit = Some(val()?.parse()?),
            "--chunks" => a.chunks = val()?.parse()?,
            "--bands" => a.cfg.bands = val()?.parse()?,
            "--gate" => a.cfg.gate = val()?.parse()?,
            "--exponent" => a.cfg.exponent = val()?.parse()?,
            "--sharpen" => a.cfg.sharpen_per_octave = val()?.parse()?,
            "--exposure" => a.exposure_stops = val()?.parse()?,
            "--hard-max" => a.cfg.select = SelectMode::HardMax,
            "--base-mean" => a.cfg.base = BaseBand::Mean,
            // The control arm the default was measured against. Keeping it
            // reachable is what makes `BaseBand::Mean` a measurement rather
            // than a preference.
            "--base-weighted" => a.cfg.base = BaseBand::WeightedFromCoarsest,
            // Reproduces the mid-tone clip: without the hull clamp the
            // reconstruction may emit values no input frame supports, which on
            // real stacks crushes dark pixels to exact zero. See `Hull`.
            "--unclamped" => a.cfg.hull = Hull::Unclamped,
            "--per-level" => a.cfg.hull = Hull::PerLevel,
            "--hull-lambda" => a.cfg.hull_lambda = val()?.parse()?,
            "--linear" => a.linear = true,
            // Camera-native primaries, linear, no matrix and no transfer curve
            // -- `image_out::OutputSpace::CameraLinear`, the byte-frozen
            // measurement output the corpus was built on. This exists so the
            // two arms can be differenced in the space ORCH measured the rim
            // and the aura in. `--linear` is LinearSrgb and DOES apply the
            // colour matrix, so differencing a `--linear` blend against a
            // camera-native control would compare two colour spaces.
            "--camera-linear" => a.camera_linear = true,
            other => bail!("unknown flag {other}"),
        }
    }
    ensure!(a.cfg.bands >= 1, "--bands must be at least 1");
    ensure!(a.cfg.gate >= 0.0, "--gate must be non-negative");
    Ok(a)
}

fn raw_paths(dir: &Path, limit: Option<usize>) -> Result<Vec<PathBuf>> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    paths.sort();
    if let Some(n) = limit {
        // Evenly spread rather than truncated. A truncated prefix of a focus
        // bracket is a *shallower* bracket covering part of the subject, so a
        // quick `--limit 30` look would be a picture of a different scene depth
        // and would say nothing about the full render. Subsampling keeps the
        // same depth span with fewer frames.
        if n < paths.len() && n > 0 {
            let step = paths.len() as f64 / n as f64;
            paths = (0..n)
                .map(|i| paths[((i as f64 + 0.5) * step) as usize % paths.len()].clone())
                .collect();
        }
    }
    ensure!(!paths.is_empty(), "no RAW files found in {}", dir.display());
    Ok(paths)
}

/// One worker's per-frame buffers, allocated once per chunk.
struct Worker {
    merge: BandMerge,
    fws: FrameWorkspace,
    warp: align_cmd::WarpScratch,
    planes: Vec<Vec<f32>>,
    luma: Vec<f32>,
    var: Vec<f32>,
}

impl Worker {
    fn new(geom: PlaneGeometry, cfg: MergeConfig) -> Self {
        let sizes = level_sizes(geom.width, geom.height, cfg.bands);
        let px = geom.pixels();
        Self {
            merge: BandMerge::new(geom.width, geom.height, PLANES, cfg),
            fws: FrameWorkspace::new(&sizes, PLANES),
            warp: align_cmd::WarpScratch::new(geom),
            planes: (0..PLANES).map(|_| vec![0.0; px]).collect(),
            luma: vec![0.0; px],
            var: vec![0.0; px],
        }
    }

    /// Decode, register and fold one frame.
    fn fold(
        &mut self,
        path: &Path,
        index: usize,
        geom: PlaneGeometry,
        levels: Levels,
        noise: &NoiseModel,
        warps: Option<&WarpMap>,
    ) -> Result<bool> {
        let mut frame = strehl_raw::decode(path).with_context(|| format!("frame {index}"))?;
        ensure!(
            frame.levels == levels,
            "frame {index} has levels black {} white {}, but the stack was calibrated at \
             black {} white {}",
            frame.levels.black,
            frame.levels.white,
            levels.black,
            levels.white
        );
        if let Some(map) = warps {
            match map.warp(index)? {
                FrameWarp::Placed(t) => {
                    align_cmd::warp_frame_in_place(
                        &mut frame,
                        *t,
                        geom,
                        map.resampler(),
                        &mut self.warp,
                    )?;
                }
                // Skipped, not merged unregistered: the solve could not connect
                // this frame to the bracket, so its geometry is unknown and
                // folding it would put mis-registered data into the merge.
                FrameWarp::Refused(_) => return Ok(false),
            }
        }

        let black = levels.black;
        let (stride, ax, ay) = (frame.stride, frame.active.x, frame.active.y);
        let (gw, gh) = (geom.width, geom.height);
        for (p, (dx, dy)) in PLANE_OFFSETS.iter().enumerate() {
            let out = &mut self.planes[p];
            for py in 0..gh {
                let row = (ay + 2 * py + dy) * stride + ax + dx;
                let dst = &mut out[py * gw..py * gw + gw];
                for (px, o) in dst.iter_mut().enumerate() {
                    *o = (f32::from(frame.data[row + 2 * px]) - black).max(0.0);
                }
            }
        }
        drop(frame);

        // Green luma, `L = (G1 + G2) / 2`, exactly as `plane::green_luma`
        // computes it — the plane the shipped election runs on. Selecting on
        // green only is what keeps chroma noise from driving the decision.
        for i in 0..self.luma.len() {
            self.luma[i] = 0.5 * (self.planes[P_G1][i] + self.planes[P_G2][i]);
        }
        luma_variance(&self.luma, noise, &mut self.var);

        let refs: Vec<&[f32]> = self.planes.iter().map(|v| v.as_slice()).collect();
        self.fws.next_frame();
        self.merge
            .add_frame(&refs, &self.luma, &self.var, &mut self.fws);
        Ok(true)
    }
}

fn main() -> Result<()> {
    let args = parse_args()?;
    // Ask once, up front, and throw the answer away. `warp_frame_in_place`
    // re-reads the profile per frame, so a typo'd STREHL_FIX_CA would otherwise
    // surface only after a full decode -- which inside a comparison matrix reads
    // as a slow arm rather than a config error.
    align_cmd::preflight_ca_profile()?;
    let t_start = Instant::now();

    let paths = raw_paths(&args.dir, args.limit)?;
    ensure!(
        paths.len() < u16::MAX as usize,
        "{} frames is more than this harness indexes",
        paths.len()
    );

    let t0 = Instant::now();
    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let geom = first.geometry();
    let levels = first.levels;
    let camera = first.camera.clone();
    let iso = first.iso;
    let wb = first.wb_gains();
    let xyz_to_cam = first.xyz_to_cam_rgb_with_source();
    drop(first);
    let prologue = t0.elapsed().as_secs_f64();

    let noise = profile::noise_model_for(&camera, iso, levels);
    let sizes = level_sizes(geom.width, geom.height, args.cfg.bands);

    eprintln!("strehl BUILD-BLEND -- LAPLACIAN MULTI-BAND MERGE (an experiment, not the ship path)");
    eprintln!("camera          : {camera}");
    // Cheap: seeks a few hundred bytes of metadata, no pixel decode.
    let ident = strehl_raw::identity(&paths[0]);
    // Reports the RESOLVED DECISION, not the switch. Those used to be the same
    // thing; the default-on flip decoupled them, and this line kept reading the
    // variable -- printing `CORRECTING, profile "off"` for an uncorrected render
    // and `off (STREHL_FIX_CA unset)` for a corrected one. Wrong in both
    // directions, and this is a harness whose whole job is A/B comparison, so a
    // lying arm label is the worst possible defect to have here.
    //
    // Resolved from the same first frame the aligner reads, through the same
    // call, so the label cannot drift from the pixels without the pixels moving.
    eprintln!(
        "lateral CA      : {}",
        match strehl_core::optics::resolve_for_capture_env(
            ident.model.as_deref(),
            ident.lens_type3,
        ) {
            Ok(d) => d.to_string(),
            // Unreachable: `preflight_ca_profile` rejects an unusable setting
            // before any decode. Stated as `off` because that is what the render
            // would do, rather than guessed at.
            Err(e) => format!("off (unusable setting: {e})"),
        }
    );
    eprintln!(
        "iso             : {}",
        iso.map(|v| format!("{v:.0}")).unwrap_or("UNKNOWN".into())
    );
    eprintln!(
        "levels          : black {}, white {}",
        levels.black, levels.white
    );
    eprintln!("noise model     : {:?}", noise.provenance);
    eprintln!(
        "frames          : {} from {}  (first decode {prologue:.2} s)",
        paths.len(),
        args.dir.display()
    );
    eprintln!(
        "planes          : {} x {} per CFA plane",
        geom.width, geom.height
    );
    eprintln!("--- the merge ---");
    eprintln!(
        "bands           : {} Laplacian levels + 1 base, coarsest {} x {}",
        sizes.len() - 1,
        sizes[sizes.len() - 1].width,
        sizes[sizes.len() - 1].height
    );
    eprintln!(
        "selection       : {}",
        match args.cfg.select {
            SelectMode::SoftPower =>
                "SOFT -- weight = (band power above the noise floor)^exponent, a convex \
                 combination\n                  WITHIN each band. That does NOT make the \
                 reconstruction convex: each band\n                  has its own weight field, so \
                 a sum of convex combinations taken under\n                  different weightings \
                 is not a convex combination of the inputs. The\n                  hull clamp is \
                 what confines the output to what the frames support.",
            SelectMode::HardMax =>
                "HARD -- argmax of band power. THE CONTROL ARM, the textbook PMax rule.",
        }
    );
    eprintln!(
        "noise gate      : {:.2} x the modelled band-noise power. Below it, NO frame may win \
         and the\n                  merge averages -- which is the correct estimator when there \
         is no\n                  information, and the only operation that gets below \
         single-frame noise.",
        args.cfg.gate
    );
    eprintln!("exponent        : {:.2}", args.cfg.exponent);
    eprintln!(
        "per-band exp    : {}   (coarsest -> finest)",
        (0..sizes.len() - 1)
            .rev()
            .map(|k| format!("{:.0}", args.cfg.exponent_at(k, sizes.len() - 1)))
            .collect::<Vec<_>>()
            .join(" ")
    );
    eprintln!(
        "                  sharpness ramps {:.1}x per octave toward the fine bands. A wrong \
         pick in a\n                  fine band is one high-frequency coefficient nobody can \
         see; a wrong pick\n                  in a coarse band IS the rim. So: near-argmax where \
         acuity lives, gentle\n                  blending where the eye reads steps.",
        args.cfg.sharpen_per_octave
    );
    eprintln!(
        "base band       : {}",
        match args.cfg.base {
            BaseBand::Mean => "plain mean across frames",
            BaseBand::WeightedFromCoarsest =>
                "weighted by the coarsest band's weight, reduced once onto the base grid",
        }
    );

    // ---- registration -----------------------------------------------------
    let t_align = Instant::now();
    let alignment = align_cmd::load_or_solve(&args.dir, &paths, 0, Resampler::CatmullRom)?;
    let alignment = alignment.map(|(m, how)| {
        let (m, k) = align_cmd::cover_or_explain(m);
        (m, how, k)
    });
    match &alignment {
        Some((map, how, k)) => {
            let p = map.provenance();
            eprintln!(
                "alignment       : ON ({how}), reference {}, {} placed / {} refused, {:.1} s",
                p.reference,
                map.placed_count(),
                map.refused_count(),
                t_align.elapsed().as_secs_f64()
            );
            match k {
                Some(k) if *k >= 0.999_999 => {
                    eprintln!("  coverage      : every frame covers the whole grid")
                }
                Some(k) => eprintln!(
                    "  coverage      : field of view scaled to {k:.4} so every frame covers \
                     every pixel"
                ),
                None => eprintln!("  coverage      : WARNING -- could not fit a covered grid"),
            }
        }
        None => eprintln!("alignment       : OFF -- frames combined unregistered"),
    }

    // ---- the fold ---------------------------------------------------------
    let workers = if args.chunks > 0 {
        args.chunks
    } else {
        // Each worker holds one accumulator plus one frame's working set, which
        // is hundreds of megabytes. Defaulting to the core count would ask for
        // tens of gigabytes, so the default is deliberately small and the knob
        // is there for a machine that can take more.
        3.min(paths.len().max(1))
    };
    let per_chunk = paths.len().div_ceil(workers);
    {
        let probe = BandMerge::new(geom.width, geom.height, PLANES, args.cfg);
        let fws = FrameWorkspace::new(&sizes, PLANES);
        let acc_mb = probe.accumulator_floats() as f64 * 4.0 / (1 << 20) as f64;
        let ws_mb = fws.floats() as f64 * 4.0 / (1 << 20) as f64;
        // The plane extraction buffers, the luma and the variance field, and
        // one decoded frame, all of which are live at once inside `fold`.
        let frame_mb = (PLANES + 2) as f64 * geom.pixels() as f64 * 4.0 / (1 << 20) as f64
            + 4.0 * geom.pixels() as f64 * 2.0 / (1 << 20) as f64;
        eprintln!(
            "memory plan     : {workers} workers x ({acc_mb:.0} MB accumulator + {ws_mb:.0} MB \
             pyramid scratch + {frame_mb:.0} MB frame)\n                  = {:.1} GB, CONSTANT \
             in the frame count. The merge is a fold: every\n                  accumulator is a \
             sum, so a frame is built, added and dropped.",
            workers as f64 * (acc_mb + ws_mb + frame_mb) / 1024.0
        );
        eprintln!(
            "band noise gain : {}",
            probe
                .band_gain()
                .all()
                .iter()
                .map(|b| format!("{b:.4}"))
                .collect::<Vec<_>>()
                .join(" ")
        );
        eprintln!(
            "                  (E[L_k^2] / sigma_0^2, MEASURED on these operators, not derived. \
             The\n                  derived value compounds an independence assumption that is \
             false after\n                  the first reduction and is an order of magnitude low \
             by level 3.)"
        );
    }

    let warps = alignment.as_ref().map(|(m, _, _)| m);
    let t_fold = Instant::now();
    let indexed: Vec<(usize, PathBuf)> = paths.iter().cloned().enumerate().collect();
    let parts: Vec<Result<(BandMerge, usize)>> = indexed
        .par_chunks(per_chunk)
        .map(|chunk| {
            let mut w = Worker::new(geom, args.cfg);
            let mut folded = 0usize;
            for (i, p) in chunk {
                if w.fold(p, *i, geom, levels, &noise, warps)? {
                    folded += 1;
                }
            }
            Ok((w.merge, folded))
        })
        .collect();

    let mut merged: Option<BandMerge> = None;
    let mut folded_total = 0usize;
    for part in parts {
        let (m, n) = part?;
        folded_total += n;
        match &mut merged {
            Some(a) => a.absorb(&m),
            None => merged = Some(m),
        }
    }
    let merge = merged.context("no frames were folded")?;
    let fold_secs = t_fold.elapsed().as_secs_f64();
    ensure!(folded_total > 0, "every frame was refused by the alignment solve");
    eprintln!();
    eprintln!(
        "folded          : {folded_total} / {} frames in {fold_secs:.1} s ({:.2} s per frame, \
         {workers} workers)",
        paths.len(),
        fold_secs / folded_total as f64
    );
    let frac = merge.averaged_fraction();
    eprintln!(
        "averaged        : {}",
        frac.iter()
            .map(|f| format!("{:.1}%", 100.0 * f))
            .collect::<Vec<_>>()
            .join(" ")
    );
    eprintln!(
        "                  per level, the fraction of coefficients where NO frame cleared the \
         noise\n                  floor and the merge therefore averaged instead of selecting. \
         Near 0%\n                  everywhere would mean the gate is not gating and this is a \
         naive\n                  pyramid stacker."
    );

    // ---- collapse and write ----------------------------------------------
    let t_out = Instant::now();
    let mut ws = Workspace::new(&sizes);
    // What the hull clamp actually did on THIS stack. Measured per render
    // rather than argued once: the clamp's whole justification is that it only
    // removes values no input frame supports, and that claim is checkable.
    let clamped = merge.clamped_fraction(&mut ws, 1.0);
    if !clamped.is_empty() {
        eprintln!(
            "hull clamp      : {}",
            clamped.iter().map(|f| format!("{:.3}%", 100.0 * f)).collect::<Vec<_>>().join(" ")
        );
        eprintln!(
            "                  per plane, the fraction of output pixels the reconstruction put \
             outside\n                  the range its own input frames support, and which were \
             clamped back\n                  into it. Per-band convexity does not imply \
             reconstruction convexity."
        );
    }
    let planes = merge.finish(&mut ws);
    drop(ws);
    drop(merge);

    write_frame(
        &args.out,
        geom,
        levels,
        wb,
        xyz_to_cam.as_ref(),
        &planes,
        args.linear,
        args.camera_linear,
        args.exposure_stops,
    )?;
    eprintln!(
        "wrote           : {} ({} x {}, 16-bit RGB, Malvar-He-Cutler demosaic) in {:.1} s",
        args.out.display(),
        geom.width * 2,
        geom.height * 2,
        t_out.elapsed().as_secs_f64()
    );
    eprintln!("total           : {:.1} s", t_start.elapsed().as_secs_f64());
    Ok(())
}

/// Interleave the four merged planes back into an RGGB mosaic and develop it
/// through the shipped `image_out` path.
///
/// Every line of arithmetic here is copied from `merge_cmd::write_merged`'s
/// `--demosaic` branch and must stay that way: the comparison this binary
/// exists for is only honest if the two arms differ in the merge and nowhere
/// else.
#[allow(clippy::too_many_arguments)]
fn write_frame(
    path: &Path,
    geom: PlaneGeometry,
    levels: Levels,
    wb: Option<[f32; 3]>,
    xyz_to_cam: Option<&([[f32; 3]; 3], String)>,
    planes: &[Vec<f32>],
    linear: bool,
    camera_linear: bool,
    exposure_stops: f32,
) -> Result<()> {
    let range = levels.range();
    ensure!(range > 0.0, "white level is not above black level");
    let gains = wb.unwrap_or([1.0, 1.0, 1.0]);
    let space = if camera_linear {
        image_out::OutputSpace::CameraLinear
    } else if linear {
        image_out::OutputSpace::LinearSrgb
    } else {
        image_out::OutputSpace::Srgb
    };
    let matrix = if space.wants_matrix() {
        xyz_to_cam.and_then(|(m, _)| color::camera_to_srgb(*m))
    } else {
        None
    };
    match (&matrix, xyz_to_cam) {
        (Some(_), Some((_, src))) => eprintln!("colour          : camera RGB -> sRGB ({src})"),
        _ => eprintln!("colour          : no characterisation; CAMERA-NATIVE RGB"),
    }
    let eg = 2.0f32.powf(exposure_stops);
    let dev = space.develop(
        matrix.map(|r| r.with_ceiling(color::saturation_ceiling(levels, gains, eg))),
    );

    let (mw, mh) = (geom.width * 2, geom.height * 2);
    let mut mosaic = vec![0.0f32; mw * mh];
    // The merged planes are already black-subtracted, so `norm` is the shipped
    // expression with its `- black` term already applied.
    let norm = |v: f32, gain: f32| v.max(0.0) * gain * eg / range;
    for py in 0..geom.height {
        let (top, bot) = mosaic[py * 2 * mw..].split_at_mut(mw);
        for px in 0..geom.width {
            let i = py * geom.width + px;
            top[px * 2] = norm(planes[P_R][i], gains[0]);
            top[px * 2 + 1] = norm(planes[P_G1][i], gains[1]);
            bot[px * 2] = norm(planes[P_G2][i], gains[1]);
            bot[px * 2 + 1] = norm(planes[P_B][i], gains[2]);
        }
    }
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).ok();
    }
    image_out::write_demosaiced(path, mw, mh, &mosaic, &dev)
}

