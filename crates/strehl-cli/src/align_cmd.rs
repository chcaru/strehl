//! `strehl align` — solve a bracket's geometry once and write a warp sidecar.
//!
//! # Why this is a separate command
//!
//! M86 measured the solve at ~55 s on a 299-frame bracket (6.3 s decode,
//! 48.8 s edge measurement, <1 s solve, 32 threads). That is far too expensive
//! to repeat on every merge, and it is a *calibration* — the same class of
//! artefact as every other profile this project keeps as data. So it runs
//! once, here, and writes a [`WarpMap`] the merge reads.
//!
//! # What it refuses
//!
//! A **global similarity is the wrong model** for a subject that is not normal
//! to the optical axis: when the object plane is tilted, focus change moves
//! different parts of the frame by different amounts and no single scale
//! describes it. M86 established this on `highly-angled-ruler-mm-cpl`, and the
//! guard for it is in [`AlignArgs::guard_subject`] rather than only in prose,
//! because a guard that lives in a report is not a guard.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use rayon::prelude::*;
use strehl_core::align::{
    AlignConfig, AlignEdge, AlignFrame, AlignPyramid, GlobalOptions, PlaneRef, Resampler,
    Similarity, SimilarityParams, Weighting, align_pair, cycle_consistency, edge_errors,
    solve_global, tile_grid, total_drift,
};
use strehl_core::plane::{PlaneGeometry, green_luma};
use strehl_core::warpmap::{FrameWarp, Provenance, StackIdentity, WarpMap};

/// Brackets whose subject is known not to be normal to the optical axis.
///
/// A global similarity cannot describe these and the solve would return a
/// confident, wrong answer rather than an obviously wrong one — which is the
/// worst failure mode available. Matching is on the directory name, which is
/// crude but is the identity the operator actually types.
const TILTED_SUBJECTS: &[&str] = &["highly-angled-ruler-mm-cpl"];

/// The edge ladder used when the merge solves its own alignment.
///
/// Kept identical to `AlignArgs::spans`' default so that a sidecar written by
/// `strehl align` and one solved inside the merge are the same product.
pub const DEFAULT_SPANS: [usize; 9] = [1, 2, 4, 8, 16, 32, 64, 96, 128];

#[derive(Debug, clap::Args)]
pub struct AlignArgs {
    /// Directory of `.arw` frames to solve.
    pub dir: PathBuf,

    /// Where to write the sidecar. Defaults to `<dir>/warpmap.txt`.
    #[arg(long)]
    pub out: Option<PathBuf>,

    /// Frame the placements are relative to.
    #[arg(long, default_value_t = 0)]
    pub reference: usize,

    /// Frame separations to measure edges at.
    ///
    /// A ladder, not a chain: M86 measured that a solve resting only on
    /// short spans is poorly conditioned, and M10 fact 47 records held-out
    /// error bounded by the short edges.
    #[arg(long, value_delimiter = ',', default_values_t = [1usize, 2, 4, 8, 16, 32, 64, 96, 128])]
    pub spans: Vec<usize>,

    /// Worker threads. 0 uses every core.
    #[arg(long, default_value_t = 0)]
    pub threads: usize,

    /// Interpolator recorded in the sidecar for the merge to gather with.
    ///
    /// See `WarpMap::set_resampler` for exactly how evidenced this default is.
    #[arg(long, default_value = "catmull-rom")]
    pub resampler: String,

    /// Solve a bracket flagged as tilted anyway, knowing the model is wrong.
    #[arg(long)]
    pub force_tilted: bool,

    /// Stop after this many frames. For smoke tests.
    #[arg(long)]
    pub limit: Option<usize>,

    /// Run gate W2 on real frames instead of solving: plant a known similarity
    /// of this scale, route it through a sidecar, gather, and report the
    /// residual as a fraction of the damage. Runs the inversion and
    /// transposition controls alongside, which must NOT pass.
    #[arg(long)]
    pub verify_plant: Option<f64>,

    /// Instead of solving, load this sidecar and check it belongs to `dir`.
    ///
    /// This is the check a merge performs before gathering, exposed so it can
    /// be exercised on its own.
    #[arg(long)]
    pub check: Option<PathBuf>,

    /// Instead of solving, measure what a single gather costs in fine detail
    /// for each resampler. See `run_resampler_cost` for why the W2 ratio
    /// cannot answer this.
    #[arg(long)]
    pub resampler_cost: bool,

    /// Gate W8: verify `warp_frame_in_place` on a real decoded frame.
    ///
    /// Checks the Bayer-phase indexing that the merge depends on, which the
    /// sidecar's own W2 gate cannot reach because W2 works on an already
    /// extracted plane.
    #[arg(long)]
    pub verify_warp: bool,
}

impl AlignArgs {
    /// Refuse a subject a global similarity cannot describe.
    fn guard_subject(&self) -> Result<()> {
        let name = self
            .dir
            .file_name()
            .map(|s| s.to_string_lossy().to_lowercase())
            .unwrap_or_default();
        if TILTED_SUBJECTS.iter().any(|t| name.contains(t)) {
            if self.force_tilted {
                eprintln!(
                    "warning: {name} is a tilted subject and a global similarity is the \
                     wrong model for it; --force-tilted was given, so continuing"
                );
                return Ok(());
            }
            bail!(
                "refusing to solve {name}: its subject is not normal to the optical axis, \
                 so focus change moves different parts of the frame by different amounts \
                 and no single similarity describes it. The sidecar would be confidently \
                 wrong. Pass --force-tilted to override."
            );
        }
        Ok(())
    }

    fn resampler(&self) -> Result<Resampler> {
        Ok(match self.resampler.as_str() {
            "nearest" => Resampler::Nearest,
            "bilinear" => Resampler::Bilinear,
            "catmull-rom" => Resampler::CatmullRom,
            other => bail!("unknown resampler {other:?}"),
        })
    }
}

/// The `.arw` frames of a directory, in the order the warps are indexed.
fn list_frames(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .map(|e| e.to_string_lossy().eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    v.sort();
    if v.is_empty() {
        bail!("no .arw frames in {}", dir.display());
    }
    Ok(v)
}

struct Stack {
    geom: PlaneGeometry,
    planes: Vec<Vec<f32>>,
}

fn decode_stack(paths: &[PathBuf], threads: usize) -> Result<Stack> {
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .context("decode pool")?;
    let decoded: Result<Vec<(PlaneGeometry, Vec<f32>)>> = pool.install(|| {
        paths
            .par_iter()
            .map(|p| {
                let raw =
                    strehl_raw::decode(p).with_context(|| format!("decoding {}", p.display()))?;
                let geom = PlaneGeometry {
                    width: raw.active.width / 2,
                    height: raw.active.height / 2,
                };
                let mut plane = vec![0f32; geom.pixels()];
                green_luma(&raw, raw.levels.black as f32, &mut plane);
                Ok((geom, plane))
            })
            .collect()
    });
    let decoded = decoded?;
    let geom = decoded[0].0;
    if decoded.iter().any(|(g, _)| *g != geom) {
        bail!("frames do not share a plane geometry");
    }
    Ok(Stack {
        geom,
        planes: decoded.into_iter().map(|(_, p)| p).collect(),
    })
}

/// Measure the pairwise edge ladder.
fn measure_edges(
    st: &Stack,
    pairs: &[(usize, usize)],
    cfg: &AlignConfig,
    threads: usize,
) -> Result<Vec<AlignEdge>> {
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .context("measure pool")?;
    let geom = st.geom;

    // Built once per frame, not once per pair: on a dense ladder each frame
    // appears in |spans| pairs and rebuilding would dominate the run.
    let pyramids: Vec<Option<AlignPyramid>> = pool.install(|| {
        st.planes
            .par_iter()
            .map(|p| PlaneRef::from_geometry(p, geom).and_then(|v| AlignPyramid::build(v, cfg)))
            .collect()
    });

    let spots = {
        let p0 = PlaneRef::from_geometry(&st.planes[0], geom).context("plane view")?;
        tile_grid(
            p0,
            cfg.fine_tile,
            cfg.fine_grid.0,
            cfg.fine_grid.1,
            cfg.margin,
        )
        .context("the fine tile grid does not fit in this plane")?
    };
    let edges: Vec<AlignEdge> = pool.install(|| {
        pairs
            .par_iter()
            .filter_map(|&(i, j)| {
                let (pi, pj) = (pyramids[i].as_ref()?, pyramids[j].as_ref()?);
                let a = AlignFrame {
                    plane: PlaneRef::from_geometry(&st.planes[i], geom)?,
                    pyramid: pi,
                };
                let b = AlignFrame {
                    plane: PlaneRef::from_geometry(&st.planes[j], geom)?,
                    pyramid: pj,
                };
                let fit = align_pair(a, b, &spots, cfg).ok()?;
                Some(AlignEdge {
                    i,
                    j,
                    t: fit.similarity(),
                    rms: fit.rms as f64,
                    used: fit.used,
                    lever: fit.lever_rms as f64,
                })
            })
            .collect()
    });
    Ok(edges)
}

pub fn run(args: &AlignArgs) -> Result<()> {
    args.guard_subject()?;
    let resampler = args.resampler()?;

    if let Some(scale) = args.verify_plant {
        return run_verify_plant(args, scale, resampler);
    }

    if args.resampler_cost {
        return run_resampler_cost(args);
    }

    if args.verify_warp {
        return run_verify_warp(args, resampler);
    }

    if let Some(sidecar) = &args.check {
        return run_check(&args.dir, sidecar);
    }

    let mut paths = list_frames(&args.dir)?;
    if let Some(n) = args.limit {
        paths.truncate(n);
    }
    let n = paths.len();
    let name = args
        .dir
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_default();
    if args.reference >= n {
        bail!(
            "--reference {} is out of range for {n} frames",
            args.reference
        );
    }

    // Identity is taken from the file listing, before anything is decoded, so
    // that a sidecar can be checked against a bracket cheaply.
    let identity = StackIdentity::from_paths(&name, &paths)?;
    println!("stack {name}: {n} frames, digest {:016x}", identity.digest);

    let t0 = std::time::Instant::now();
    let st = decode_stack(&paths, args.threads)?;
    println!(
        "  decoded {n} frames in {:.1} s, plane {}x{}",
        t0.elapsed().as_secs_f64(),
        st.geom.width,
        st.geom.height
    );

    let cfg = AlignConfig::deep();
    let mut pairs: Vec<(usize, usize)> = Vec::new();
    for &s in &args.spans {
        for i in 0..n.saturating_sub(s) {
            pairs.push((i, i + s));
        }
    }
    pairs.sort_unstable();
    pairs.dedup();

    let t1 = std::time::Instant::now();
    let edges = measure_edges(&st, &pairs, &cfg, args.threads)?;
    println!(
        "  measured {}/{} edges in {:.1} s ({:.1}% refused)",
        edges.len(),
        pairs.len(),
        t1.elapsed().as_secs_f64(),
        100.0 * (pairs.len() - edges.len()) as f64 / pairs.len() as f64
    );

    let floor = cycle_floor(&edges, st.geom);
    let mut opts = GlobalOptions::new(st.geom);
    opts.weighting = Weighting::Unit;
    let placements = solve_global(&edges, n, &opts)
        .context("the global system is not full rank; the edge ladder is too sparse")?;

    // Held-out error, not fit error. Every other number here would flatter the
    // solve; this one is the only one a consumer can act on.
    let heldout = heldout_error(&edges, n, &opts, st.geom);

    let drift = total_drift(&placements, st.geom);
    let warps: Vec<FrameWarp> = placements
        .iter()
        .enumerate()
        .map(|(k, t)| match t {
            Some(t) => FrameWarp::Placed(rebase(*t, placements[args.reference])),
            None => FrameWarp::Refused(format!(
                "frame {k} is not connected to the solved component by any measured edge"
            )),
        })
        .collect();

    let map = WarpMap::new(
        Provenance {
            stack: identity,
            strategy: "S3-ba-unit".into(),
            heldout_px: heldout,
            cycle_floor_px: floor,
            reference: args.reference,
            note: format!("strehl align, M86b, spans {:?}", args.spans),
        },
        st.geom,
        resampler,
        warps,
    );

    let out = args
        .out
        .clone()
        .unwrap_or_else(|| args.dir.join("warpmap.txt"));
    map.save(&out)?;

    println!(
        "\n  placed {}/{} frames, refused {}",
        map.placed_count(),
        map.len(),
        map.refused_count()
    );
    println!(
        "  total corner drift frame 0 -> {}: {drift:.3} plane px",
        n - 1
    );
    match heldout {
        Some(e) => println!("  held-out corner error (median): {e:.3} plane px"),
        None => println!("  held-out corner error: NOT MEASURED (too few edges)"),
    }
    match floor {
        Some(f) => println!("  cycle-consistency floor: {f:.3} plane px"),
        None => println!("  cycle-consistency floor: NOT MEASURED (no closed triangles)"),
    }
    println!("  wrote {}", out.display());
    if let Some(e) = heldout
        && e > 4.0
    {
        println!(
            "\n  NOTE: held-out error {e:.3} px is above M86's T_usable of 4.0 px. \
                 The sidecar is still a large improvement on no registration at all, \
                 but it is not a precise solve."
        );
    }
    Ok(())
}

/// Re-express a placement relative to a chosen reference frame.
///
/// `solve_global` returns placements relative to frame 0. If the caller asked
/// for a different reference, every placement is composed with the inverse of
/// the reference's own placement. Getting this backwards silently shifts the
/// whole stack, so it is one expression in one place.
fn rebase(t: Similarity, reference: Option<Similarity>) -> Similarity {
    match reference.and_then(|r| r.invert()) {
        Some(inv) => inv.then(t),
        None => t,
    }
}

/// Median cycle-consistency error of the edge set, plane px.
///
/// This is the floor no solver can beat: a solve cannot predict an edge better
/// than the edges agree with each other around a closed triangle. Carrying it
/// in the sidecar is what lets a consumer tell "the solve is bad" from "the
/// measurements are bad", which are different problems with different fixes.
fn cycle_floor(edges: &[AlignEdge], geom: PlaneGeometry) -> Option<f64> {
    let trip = cycle_consistency(edges, geom, 4000);
    if trip.is_empty() {
        return None;
    }
    let mut e: Vec<f64> = trip.iter().map(|t| t.err).collect();
    e.sort_by(|a, b| a.partial_cmp(b).unwrap());
    Some(e[e.len() / 2])
}

/// Median held-out corner error under **M10's protocol**, plane px.
///
/// The test set is the **long-span** edges (`span >= MIN_SPAN`, `used >=
/// MIN_USED`); training is everything else. This is the protocol M10 defined
/// and M86 replicated, and the choice is load-bearing: it asks the solve to
/// predict long-range geometry from short-range measurements, which is the
/// extrapolation a deep bracket actually needs.
///
/// A k-fold stride holdout over the edge list is **not** a substitute and was
/// measured to be optimistic by roughly 4x on `bee-3-cpl` (2.95 px against
/// 11.56 px), because for every held-out edge it leaves near-duplicate edges
/// in training. Reporting that number in the sidecar would tell a consumer the
/// solve was four times better than it is, which defeats the reason the
/// sidecar carries an error at all.
fn heldout_error(
    edges: &[AlignEdge],
    n: usize,
    opts: &GlobalOptions,
    geom: PlaneGeometry,
) -> Option<f64> {
    const MIN_SPAN: usize = 40;
    const MIN_USED: usize = 12;
    let is_test = |e: &AlignEdge| e.j - e.i >= MIN_SPAN && e.used >= MIN_USED;
    let test: Vec<AlignEdge> = edges.iter().filter(|e| is_test(e)).copied().collect();
    let train: Vec<AlignEdge> = edges.iter().filter(|e| !is_test(e)).copied().collect();
    if test.is_empty() || train.is_empty() {
        return None;
    }
    let g = solve_global(&train, n, opts)?;
    let mut errs: Vec<f64> = edge_errors(&g, &test, geom).iter().map(|x| x.err).collect();
    if errs.is_empty() {
        return None;
    }
    errs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    Some(errs[errs.len() / 2])
}

/// Median |a - b| over the interior, skipping uncovered pixels.
fn median_abs_diff(a: &[f32], b: &[f32], geom: PlaneGeometry, margin: usize) -> f64 {
    let mut d = Vec::new();
    for y in margin..geom.height - margin {
        for x in margin..geom.width - margin {
            let i = y * geom.width + x;
            if a[i].is_finite() && b[i].is_finite() {
                d.push((a[i] - b[i]).abs() as f64);
            }
        }
    }
    if d.is_empty() {
        return f64::NAN;
    }
    d.sort_by(|x, y| x.partial_cmp(y).unwrap());
    d[d.len() / 2]
}

/// Gate W2 on real frames, with both silent-bug controls.
///
/// Registered bars: the gate passes at `ratio <= 0.25`; the inversion and
/// transposition controls must reach `ratio >= 0.9`. If a control passes the
/// gate, the gate cannot distinguish a correct warp from a wrong one and
/// proves nothing -- so a passing control is reported as a FAILURE of the
/// verification, not a success.
fn run_verify_plant(args: &AlignArgs, scale: f64, resampler: Resampler) -> Result<()> {
    const GATE: f64 = 0.25;
    const CONTROL: f64 = 0.9;
    let (dx, dy) = (8.0, -3.0);
    println!(
        "M86b GATE W2 -- planted warp undone, on REAL frames\n  {}\n  resampler {:?}",
        args.dir.display(),
        resampler
    );

    let plant = Similarity::from_params(strehl_core::align::SimilarityParams {
        ax: dx,
        ay: dy,
        g: scale - 1.0,
        rot: 0.0,
    });
    let inverted = plant.invert().context("plant is singular")?;
    let p = plant.to_params();
    let transposed = Similarity::from_params(strehl_core::align::SimilarityParams {
        ax: p.ay,
        ay: p.ax,
        g: p.g,
        rot: p.rot,
    });

    let mut ok = true;
    for (label, undo, bar, want_pass) in [
        ("gate (correct placement)", plant, GATE, true),
        ("control: INVERTED", inverted, CONTROL, false),
        ("control: TRANSPOSED", transposed, CONTROL, false),
    ] {
        let (ratio, damage, residual) =
            verify_plant_trial(&args.dir, plant, undo, args.threads, resampler)?;
        let pass = if want_pass {
            ratio <= bar
        } else {
            ratio >= bar
        };
        println!(
            "  {label:<26} ratio {ratio:8.4}  (damage {damage:.5}, residual {residual:.5})  {}",
            if pass { "OK" } else { "FAIL" }
        );
        if !pass {
            ok = false;
            if want_pass {
                println!("    the planted warp was NOT undone: {ratio:.4} > {bar}");
            } else {
                println!(
                    "    this control PASSED the gate at {ratio:.4} < {bar}; the gate cannot \
                     tell a correct warp from a wrong one and proves nothing"
                );
            }
        }
    }
    println!(
        "\n  GATE W2 (real frames): {}",
        if ok { "PASS" } else { "FAIL" }
    );
    if !ok {
        bail!("gate W2 failed");
    }
    Ok(())
}

/// One W2 trial: plant `plant`, try to undo with `undo`, through a sidecar.
fn verify_plant_trial(
    dir: &Path,
    plant: Similarity,
    undo: Similarity,
    threads: usize,
    resampler: Resampler,
) -> Result<(f64, f64, f64)> {
    let paths = list_frames(dir)?;
    let one = vec![paths[0].clone()];
    let st = decode_stack(&one, threads)?;
    let geom = st.geom;
    let orig = &st.planes[0];
    let oref = PlaneRef::from_geometry(orig, geom).context("plane view")?;

    // `orig` pushed forward through `plant`, built as a pull through the EXACT
    // inverse. A linearised inverse here is the trap M86 documented: at a 1%
    // scale the difference between `-(s-1)` and `1/s - 1` is 0.83 plane px on
    // this plane, larger than the effect being measured.
    let inv = plant.invert().context("plant is singular")?;
    let mut warped = vec![0f32; geom.pixels()];
    strehl_core::align::gather_into(oref, inv, geom, resampler, &mut warped);
    let wref = PlaneRef::from_geometry(&warped, geom).context("plane view")?;

    // Route the placement through the sidecar rather than around it.
    let map = WarpMap::new(
        Provenance {
            stack: StackIdentity::from_paths("verify", &one)?,
            strategy: "planted".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: "W2 real-frame plant".into(),
        },
        geom,
        resampler,
        vec![FrameWarp::Placed(undo)],
    );
    let map = WarpMap::from_text(&map.to_text())?;

    let mut got = vec![0f32; geom.pixels()];
    let mut cover = vec![false; geom.pixels()];
    strehl_core::warpmap::gather_frame(&map, 0, wref, &mut got, &mut cover)?;

    let margin = 64;
    let damage = median_abs_diff(&warped, orig, geom, margin);
    let residual = median_abs_diff(&got, orig, geom, margin);
    Ok((residual / damage, damage, residual))
}

/// Load a sidecar and check it against a bracket, as a merge would.
///
/// Prints the provenance and then either confirms the match or reports the
/// mismatch and exits non-zero. Nothing is decoded: the identity is built from
/// the file listing alone, so this is cheap enough for a merge to always do.
fn run_check(dir: &Path, sidecar: &Path) -> Result<()> {
    let map = WarpMap::load(sidecar)?;
    let p = map.provenance();
    println!("sidecar {}", sidecar.display());
    println!(
        "  fitted on   {} (digest {:016x}, {} frames)",
        p.stack.name, p.stack.digest, p.stack.frames
    );
    println!("  strategy    {}", p.strategy);
    println!("  reference   frame {}", p.reference);
    println!("  resampler   {:?}", map.resampler());
    match p.heldout_px {
        Some(e) => println!(
            "  held-out    {e:.3} plane px{}",
            if e > 4.0 {
                "  (above M86 T_usable = 4.0 px)"
            } else {
                ""
            }
        ),
        None => println!("  held-out    NOT MEASURED"),
    }
    match p.cycle_floor_px {
        Some(f) => println!("  edge floor  {f:.3} plane px"),
        None => println!("  edge floor  NOT MEASURED"),
    }
    println!(
        "  placed      {}/{}, refused {}",
        map.placed_count(),
        map.len(),
        map.refused_count()
    );

    let paths = list_frames(dir)?;
    let name = dir
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_default();
    let here = StackIdentity::from_paths(&name, &paths)?;
    println!(
        "\n  applied to  {} (digest {:016x}, {} frames)",
        here.name, here.digest, here.frames
    );
    match map.check_stack(&here) {
        Ok(()) => {
            println!("  MATCH: this sidecar belongs to this bracket");
            Ok(())
        }
        Err(e) => {
            println!("  MISMATCH");
            Err(e.into())
        }
    }
}

/// Measure what one gather costs in fine detail, per resampler.
///
/// # Why the W2 ratio cannot answer this
///
/// W2 plants a warp with resampler `R` and undoes it with the same `R`. That
/// double application lets `R`'s error partly cancel, and for
/// `Resampler::Nearest` it cancels **exactly**: the round trip is a permutation
/// of the lattice, so W2 reads a ratio of 0.0000. That is a degenerate property
/// of the metric, not evidence that nearest preserves detail -- it is the worst
/// interpolator here. Ranking resamplers on W2 would be a measurement of the
/// instrument.
///
/// This measures a **single** gather instead, at a half-pixel shift, which is
/// the phase where an interpolator is worst. Retained gradient energy is the
/// statistic: the sum of squared finite differences, which is what focus
/// measurement and the final render both consume. `1.000` means the gather
/// destroyed nothing.
fn run_resampler_cost(args: &AlignArgs) -> Result<()> {
    let paths = list_frames(&args.dir)?;
    let one = vec![paths[0].clone()];
    let st = decode_stack(&one, args.threads)?;
    let geom = st.geom;
    let orig = &st.planes[0];
    let oref = PlaneRef::from_geometry(orig, geom).context("plane view")?;

    let grad = |p: &[f32]| -> f64 {
        let mut acc = 0f64;
        let m = 64;
        for y in m..geom.height - m {
            for x in m..geom.width - m {
                let i = y * geom.width + x;
                if !p[i].is_finite() {
                    continue;
                }
                let gx = (p[i + 1] - p[i - 1]) as f64;
                let gy = (p[i + geom.width] - p[i - geom.width]) as f64;
                acc += gx * gx + gy * gy;
            }
        }
        acc
    };
    let base = grad(orig);
    println!(
        "M86b -- cost of ONE gather at a half-pixel shift\n  {}\n  baseline gradient energy {base:.4e}\n",
        args.dir.display()
    );
    println!(
        "  {:<14} {:>16} {:>10}",
        "resampler", "gradient energy", "retained"
    );
    for (name, r) in [
        ("nearest", Resampler::Nearest),
        ("bilinear", Resampler::Bilinear),
        ("catmull-rom", Resampler::CatmullRom),
    ] {
        let t = Similarity::from_params(strehl_core::align::SimilarityParams {
            ax: 0.5,
            ay: 0.5,
            g: 0.0,
            rot: 0.0,
        });
        let mut got = vec![0f32; geom.pixels()];
        let mut cover = vec![false; geom.pixels()];
        strehl_core::warpmap::gather_checked(oref, t, geom, r, &mut got, &mut cover)?;
        let e = grad(&got);
        println!("  {name:<14} {e:>16.4e} {:>9.4}", e / base);
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// merge-facing API
// ---------------------------------------------------------------------------
//
// M86 measured that every bracket in the corpus drifts far past `T_usable`:
// 232.7 px corner-to-corner on `bee-3-cpl` and 299.2 px on `bee-2-cpl`. The
// merge combined those frames with no geometric registration at all, so this
// is the path that closes that gap. Everything below exists to be called from
// `merge_cmd`, and nothing below is allowed to fabricate a transform: a frame
// the solve refused is reported as refused, never silently given identity.

/// Environment switch for the merge's registration, which is **on** by default.
///
/// Set `STREHL_ALIGN=0` to turn it off. It is an environment variable rather
/// than a flag because the subcommand definition in `main.rs` is owned by
/// another agent tonight; a flag is the better long-term home and the patch for
/// it is in the M86 report.
pub const ALIGN_ENV: &str = "STREHL_ALIGN";

/// Is registration enabled?
///
/// Anything other than `0`, `off`, `false` or `no` leaves it on.
pub fn align_enabled() -> bool {
    match std::env::var(ALIGN_ENV) {
        Ok(v) => !matches!(
            v.trim().to_ascii_lowercase().as_str(),
            "0" | "off" | "false" | "no"
        ),
        Err(_) => true,
    }
}

/// Is this directory one a global similarity cannot describe?
pub fn is_tilted_subject(dir: &Path) -> bool {
    let name = dir
        .file_name()
        .map(|s| s.to_string_lossy().to_ascii_lowercase())
        .unwrap_or_default();
    TILTED_SUBJECTS.iter().any(|t| name.contains(t))
}

/// The default sidecar location for a bracket.
pub fn sidecar_path(dir: &Path) -> PathBuf {
    dir.join("warpmap.txt")
}

/// Reference frame for a merge-side solve: the **middle** frame.
///
/// The reference is the frame everything else is resampled onto, so the
/// uncovered border grows with distance from it. Referencing frame 0 makes the
/// last frame carry the whole drift; referencing the middle halves the worst
/// case. On `bee-3-cpl`'s measured 186.7 px of end-to-end drift that is the
/// difference between a ~187 px border and a ~93 px one.
pub fn merge_reference(n: usize) -> usize {
    n / 2
}

/// Solve a bracket and return its warp map, without writing anything.
///
/// This is the body `run` uses, factored so the merge can call it. `spans` is
/// the edge ladder; `reference` is the frame placements are expressed against.
pub fn solve_map(
    dir: &Path,
    paths: &[PathBuf],
    reference: usize,
    spans: &[usize],
    threads: usize,
    resampler: Resampler,
    verbose: bool,
) -> Result<WarpMap> {
    let n = paths.len();
    if reference >= n {
        bail!("reference {reference} is out of range for {n} frames");
    }
    let name = dir
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_default();
    let identity = StackIdentity::from_paths(&name, paths)?;
    if verbose {
        println!("stack {name}: {n} frames, digest {:016x}", identity.digest);
    }

    let t0 = std::time::Instant::now();
    let st = decode_stack(paths, threads)?;
    if verbose {
        println!(
            "  decoded {n} frames in {:.1} s, plane {}x{}",
            t0.elapsed().as_secs_f64(),
            st.geom.width,
            st.geom.height
        );
    }

    let cfg = AlignConfig::deep();
    let mut pairs: Vec<(usize, usize)> = Vec::new();
    for &s in spans {
        for i in 0..n.saturating_sub(s) {
            pairs.push((i, i + s));
        }
    }
    pairs.sort_unstable();
    pairs.dedup();

    let t1 = std::time::Instant::now();
    let edges = measure_edges(&st, &pairs, &cfg, threads)?;
    if verbose {
        println!(
            "  measured {}/{} edges in {:.1} s ({:.1}% refused)",
            edges.len(),
            pairs.len(),
            t1.elapsed().as_secs_f64(),
            100.0 * (pairs.len() - edges.len()) as f64 / pairs.len() as f64
        );
    }

    let floor = cycle_floor(&edges, st.geom);
    let mut opts = GlobalOptions::new(st.geom);
    opts.weighting = Weighting::Unit;
    let placements = solve_global(&edges, n, &opts)
        .context("the global system is not full rank; the edge ladder is too sparse")?;
    let heldout = heldout_error(&edges, n, &opts, st.geom);

    let warps: Vec<FrameWarp> = placements
        .iter()
        .enumerate()
        .map(|(k, t)| match t {
            Some(t) => FrameWarp::Placed(rebase(*t, placements[reference])),
            None => FrameWarp::Refused(format!(
                "frame {k} is not connected to the solved component by any measured edge"
            )),
        })
        .collect();

    Ok(WarpMap::new(
        Provenance {
            stack: identity,
            strategy: "S3-ba-unit".into(),
            heldout_px: heldout,
            cycle_floor_px: floor,
            reference,
            note: format!("strehl align, M86b, spans {spans:?}"),
        },
        st.geom,
        resampler,
        warps,
    ))
}

/// Load the sidecar beside a bracket, or solve one and cache it.
///
/// Returns `Ok(None)` when registration is switched off or the subject is one a
/// global similarity cannot describe — both are *deliberate* refusals to
/// register, distinct from a failure. An existing sidecar whose identity does
/// not match the bracket is **not** silently reused; it is re-solved, because a
/// warp map from another stack is worse than none.
pub fn load_or_solve(
    dir: &Path,
    paths: &[PathBuf],
    threads: usize,
) -> Result<Option<(WarpMap, &'static str)>> {
    if !align_enabled() {
        return Ok(None);
    }
    if is_tilted_subject(dir) {
        eprintln!(
            "alignment      : REFUSED -- {} is a tilted subject; a global similarity \
             cannot describe it (M86). Merging unregistered.",
            dir.display()
        );
        return Ok(None);
    }

    let name = dir
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_default();
    let identity = StackIdentity::from_paths(&name, paths)?;
    let side = sidecar_path(dir);

    if side.exists() {
        match WarpMap::load(&side) {
            Ok(map) => match map.check_stack(&identity) {
                Ok(()) if map.len() == paths.len() => return Ok(Some((map, "sidecar"))),
                Ok(()) => eprintln!(
                    "alignment      : sidecar has {} frames but the bracket has {}; re-solving",
                    map.len(),
                    paths.len()
                ),
                Err(e) => eprintln!("alignment      : sidecar rejected ({e}); re-solving"),
            },
            Err(e) => eprintln!("alignment      : sidecar unreadable ({e}); re-solving"),
        }
    }

    let spans = DEFAULT_SPANS.to_vec();
    let map = solve_map(
        dir,
        paths,
        merge_reference(paths.len()),
        &spans,
        threads,
        Resampler::CatmullRom,
        false,
    )?;
    // Best effort: a read-only capture directory must not fail the merge.
    if let Err(e) = map.save(&side) {
        eprintln!("alignment      : could not cache sidecar ({e}); continuing");
    }
    Ok(Some((map, "solved")))
}

/// Apply [`fit_to_cover`] and report what it cost, or explain why it could not.
///
/// Split out so both the merge and any future consumer take the same decision
/// rather than each deciding for itself what to do about uncovered pixels.
///
/// If `STREHL_ALIGN=zoom` this additionally replaces every placement with the
/// *same* global zoom, discarding all relative registration. That is the null
/// control for the sharpness comparison: it pays the identical resampling cost
/// and yields the identical field of view, so any difference that survives
/// between it and the real thing is registration and nothing else. Without it
/// an aligned render is measured against an unaligned one at a different
/// sampling density, and the upsample alone moves gradient energy.
pub fn cover_or_explain(map: WarpMap) -> (WarpMap, Option<f64>) {
    // Catmull-Rom reads one sample before and two after, so the grid must stay
    // that far inside the source or the interpolator's support leaves it.
    let (fitted, k) = match fit_to_cover(&map, 3.0) {
        Some((fitted, k)) => (fitted, Some(k)),
        None => (map, None),
    };
    let zoom_only = std::env::var(ALIGN_ENV)
        .map(|v| v.trim().eq_ignore_ascii_case("zoom"))
        .unwrap_or(false);
    if !zoom_only {
        return (fitted, k);
    }
    let Some(k) = k else { return (fitted, None) };
    let s = Similarity::from_params(SimilarityParams {
        ax: 0.0,
        ay: 0.0,
        g: k - 1.0,
        rot: 0.0,
    });
    let warps: Vec<FrameWarp> = fitted
        .warps()
        .iter()
        .map(|f| match f {
            FrameWarp::Placed(_) => FrameWarp::Placed(s),
            FrameWarp::Refused(why) => FrameWarp::Refused(why.clone()),
        })
        .collect();
    let mut prov = fitted.provenance().clone();
    prov.note = format!("{} | ZOOM-ONLY NULL: registration discarded", prov.note);
    prov.strategy = format!("{} [zoom-only null]", prov.strategy);
    (
        WarpMap::new(prov, fitted.geometry(), fitted.resampler(), warps),
        Some(k),
    )
}

/// Reusable buffers for [`warp_frame_in_place`], so a merge does not allocate
/// four planes per frame.
pub struct WarpScratch {
    src: Vec<f32>,
    dst: Vec<f32>,
    cover: Vec<bool>,
}

impl WarpScratch {
    pub fn new(geom: PlaneGeometry) -> Self {
        let px = geom.pixels();
        Self {
            src: vec![0.0; px],
            dst: vec![0.0; px],
            cover: vec![false; px],
        }
    }
}

/// Resample a decoded frame onto the reference grid, in place.
///
/// # Why this works on the quad grid
///
/// The alignment plane is the **2x2 quad grid**: plane pixel `(px, py)` is
/// sensor quad `(2px, 2py)`, exactly as [`green_luma`] reads it. All four CFA
/// phases therefore live on that same grid, so **one** similarity registers all
/// four — each phase is gathered separately so that no interpolation ever mixes
/// two colours, which is the bug that would show up as colour fringing.
///
/// Uncovered destination pixels are set to the black level rather than left
/// holding unregistered data. They are the border the warp pulls in from
/// outside the source frame; `align.rs` documents why clamping is not an
/// option.
///
/// Returns the fraction of the plane that was covered.
pub fn warp_frame_in_place(
    frame: &mut strehl_raw::Frame,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    scratch: &mut WarpScratch,
) -> Result<f64> {
    let (gw, gh) = (geom.width, geom.height);
    if frame.active.width / 2 != gw || frame.active.height / 2 != gh {
        bail!(
            "frame {} has quad geometry {}x{}, but the warp map was fitted on {gw}x{gh}",
            frame.path.display(),
            frame.active.width / 2,
            frame.active.height / 2
        );
    }
    let black = frame.levels.black;
    let black_dn = black.round().clamp(0.0, u16::MAX as f32) as u16;
    let (stride, ax, ay) = (frame.stride, frame.active.x, frame.active.y);
    let mut covered_total = 0usize;

    for dy in 0..2usize {
        for dx in 0..2usize {
            for py in 0..gh {
                let row = (ay + 2 * py + dy) * stride + ax + dx;
                let out = &mut scratch.src[py * gw..(py + 1) * gw];
                for (px, o) in out.iter_mut().enumerate() {
                    *o = frame.data[row + 2 * px] as f32;
                }
            }
            let src = PlaneRef::from_geometry(&scratch.src, geom)
                .context("warp source plane does not match the bracket geometry")?;
            covered_total += strehl_core::warpmap::gather_checked(
                src,
                t,
                geom,
                resampler,
                &mut scratch.dst,
                &mut scratch.cover,
            )?;
            for py in 0..gh {
                let row = (ay + 2 * py + dy) * stride + ax + dx;
                let lo = py * gw;
                for px in 0..gw {
                    let v = scratch.dst[lo + px];
                    frame.data[row + 2 * px] = if scratch.cover[lo + px] {
                        // Round, then clamp to the container. The source is
                        // u16 and the interpolator can overshoot on an edge.
                        v.round().clamp(0.0, u16::MAX as f32) as u16
                    } else {
                        black_dn
                    };
                }
            }
        }
    }
    Ok(covered_total as f64 / (4 * geom.pixels()) as f64)
}

/// Gate W8 -- `warp_frame_in_place` on a real decoded frame.
///
/// The merge's registration rests on two things the sidecar's own W2 gate
/// cannot see, because W2 operates on an already-extracted plane:
///
///   1. **The Bayer phase indexing.** Each of the four CFA phases must be
///      gathered on the quad grid and written back to the same phase. Getting
///      a phase wrong swaps colour channels; getting the row stride wrong
///      shears the image. Both are silent in a round trip.
///   2. **The direction of the transform**, again.
///
/// The decisive probe is that an **identity** placement must be a bit-exact
/// no-op over the interior. Catmull-Rom at integer coordinates has weights
/// exactly `(0, 1, 0, 0)`, so any indexing error at all produces a non-zero
/// difference. A test that merely "looked close" would pass with a transposed
/// index on a smooth image; this one cannot.
fn run_verify_warp(args: &AlignArgs, resampler: Resampler) -> Result<()> {
    let paths = list_frames(&args.dir)?;
    let raw = strehl_raw::decode(&paths[0])
        .with_context(|| format!("decoding {}", paths[0].display()))?;
    let geom = PlaneGeometry {
        width: raw.active.width / 2,
        height: raw.active.height / 2,
    };
    println!("M86b GATE W8 -- warp_frame_in_place on a real frame");
    println!("  {}", paths[0].display());
    println!("  quad plane {}x{}\n", geom.width, geom.height);

    let original = raw.data.clone();
    let mut scratch = WarpScratch::new(geom);

    // --- W8a: identity is a bit-exact no-op over the interior --------------
    let mut f = raw;
    let cov = warp_frame_in_place(&mut f, Similarity::IDENTITY, geom, resampler, &mut scratch)?;
    let margin = 8usize;
    let (mut diff, mut checked) = (0usize, 0usize);
    for dy in 0..2 {
        for dx in 0..2 {
            for py in margin..geom.height - margin {
                let row = (f.active.y + 2 * py + dy) * f.stride + f.active.x + dx;
                for px in margin..geom.width - margin {
                    let i = row + 2 * px;
                    checked += 1;
                    if f.data[i] != original[i] {
                        diff += 1;
                    }
                }
            }
        }
    }
    println!("  W8a identity no-op");
    println!("    coverage        {:.4}", cov);
    println!("    interior samples {checked}, differing {diff}");
    let a_pass = diff == 0;
    println!("    {}", if a_pass { "PASS" } else { "FAIL" });

    // --- W8b: a planted scale is undone by its exact inverse ---------------
    //
    // Planting s and undoing with 1/s. Note the inverse must be exact: M86
    // measured that using -(s-1) instead of 1/s-1 is off by 0.83 plane px at
    // s = 1.01 on this rig, which is larger than the effect being measured.
    let s = 1.01f64;
    let plant = Similarity::from_params(SimilarityParams {
        ax: 0.0,
        ay: 0.0,
        g: s - 1.0,
        rot: 0.0,
    });
    let undo = plant.invert().context("planted similarity is singular")?;

    let mut f2 = strehl_raw::decode(&paths[0])?;
    warp_frame_in_place(&mut f2, plant, geom, resampler, &mut scratch)?;
    let damage = quad_mad(&f2.data, &original, &f2, geom, 64);
    warp_frame_in_place(&mut f2, undo, geom, resampler, &mut scratch)?;
    let residual = quad_mad(&f2.data, &original, &f2, geom, 64);
    let ratio = residual / damage.max(1e-12);
    println!("\n  W8b plant s={s} then undo with 1/s");
    println!("    damage   {damage:.4} DN");
    println!("    residual {residual:.4} DN");
    println!("    ratio    {ratio:.4}   (bar <= 0.25)");
    let b_pass = ratio <= 0.25;
    println!("    {}", if b_pass { "PASS" } else { "FAIL" });

    // --- W8c: control -- undoing in the WRONG direction must NOT pass ------
    //
    // The classic silent bug: applying the placement again instead of its
    // inverse. On a smooth image this still "looks like an image", which is
    // exactly why it needs a control rather than an eyeball.
    let mut f3 = strehl_raw::decode(&paths[0])?;
    warp_frame_in_place(&mut f3, plant, geom, resampler, &mut scratch)?;
    warp_frame_in_place(&mut f3, plant, geom, resampler, &mut scratch)?;
    let c_res = quad_mad(&f3.data, &original, &f3, geom, 64);
    let c_ratio = c_res / damage.max(1e-12);
    println!("\n  W8c CONTROL -- undo by re-applying the placement, not its inverse");
    println!("    residual {c_res:.4} DN   ratio {c_ratio:.4}   (must be >= 0.9)");
    let c_pass = c_ratio >= 0.9;
    println!(
        "    {}",
        if c_pass {
            "PASS (control correctly fails the gate)"
        } else {
            "FAIL -- the gate cannot tell a wrong warp from a right one"
        }
    );

    println!(
        "\n  GATE W8: {}",
        if a_pass && b_pass && c_pass {
            "PASS"
        } else {
            "FAIL"
        }
    );
    if a_pass && b_pass && c_pass {
        Ok(())
    } else {
        bail!("gate W8 failed")
    }
}

/// Median absolute difference over all four CFA phases, ignoring a margin.
fn quad_mad(
    a: &[u16],
    b: &[u16],
    f: &strehl_raw::Frame,
    geom: PlaneGeometry,
    margin: usize,
) -> f64 {
    let mut v: Vec<f32> = Vec::new();
    for dy in 0..2 {
        for dx in 0..2 {
            for py in (margin..geom.height - margin).step_by(3) {
                let row = (f.active.y + 2 * py + dy) * f.stride + f.active.x + dx;
                for px in (margin..geom.width - margin).step_by(3) {
                    let i = row + 2 * px;
                    v.push((a[i] as f32 - b[i] as f32).abs());
                }
            }
        }
    }
    if v.is_empty() {
        return 0.0;
    }
    v.sort_by(|p, q| p.partial_cmp(q).unwrap());
    v[v.len() / 2] as f64
}

/// Shrink the reference grid until **every** placed frame covers all of it.
///
/// # The defect this fixes
///
/// A placement pulls the destination corner from outside the source frame
/// whenever the frame is far from the reference. `gather_checked` correctly
/// refuses to invent those samples, and `warp_frame_in_place` writes the black
/// level there. Measured on `bee-3-cpl`: that left **9.5% of the rendered
/// frame black**, 63% of the outermost annulus, and it wrecked the render --
/// the merge has no way to know those samples are absent, so they compete in
/// the election and win wherever nothing else is sharp.
///
/// It also silently invalidates any sharpness statistic computed on the
/// result, because the boundary between image and fill is itself an enormous
/// gradient. That is how this was found.
///
/// # What it does
///
/// Composes every placement with a uniform scale `k <= 1` about the plane
/// centre, so the reference grid maps strictly inside every source frame:
/// `t' = S_k . t`. The destination therefore shows the region **all** frames
/// observed, which is the only region a stack of them can honestly describe.
///
/// The cost is real and is not hidden: the field of view shrinks by `k`, and
/// because the output keeps its pixel dimensions the result is upsampled by
/// `1/k`. The alternative -- cropping the output -- keeps every pixel real but
/// changes the image dimensions, which would break the byte-frozen measurement
/// path. That trade is recorded in the M86 report as follow-up work.
///
/// Returns the scale applied, or `None` if no frame is placed.
pub fn fit_to_cover(map: &WarpMap, margin: f64) -> Option<(WarpMap, f64)> {
    let geom = map.geometry();
    let (w, h) = (geom.width as f64, geom.height as f64);
    let (cx, cy) = (w * 0.5, h * 0.5);
    let placed: Vec<Similarity> = map.warps().iter().filter_map(|f| f.placed()).collect();
    if placed.is_empty() {
        return None;
    }

    // A similarity maps a rectangle to a rectangle, so the extreme points of
    // the warped grid are the images of its four corners. Checking those is
    // exact, not a sample.
    let corners = [
        (0.0, 0.0),
        (w - 1.0, 0.0),
        (0.0, h - 1.0),
        (w - 1.0, h - 1.0),
    ];
    let covers = |k: f64| -> bool {
        let s = Similarity::from_params(SimilarityParams {
            ax: 0.0,
            ay: 0.0,
            g: k - 1.0,
            rot: 0.0,
        });
        placed.iter().all(|t| {
            let tp = s.then(*t);
            corners.iter().all(|&(x, y)| {
                let (sx, sy) = tp.apply_at(x, y, cx, cy);
                sx >= margin && sy >= margin && sx <= w - 1.0 - margin && sy <= h - 1.0 - margin
            })
        })
    };

    if covers(1.0) {
        return Some((map.clone(), 1.0));
    }
    // Bisection. `covers` is monotone in k: shrinking the grid can only pull
    // its image further inside every source frame.
    let (mut lo, mut hi) = (0.0f64, 1.0f64);
    for _ in 0..60 {
        let mid = 0.5 * (lo + hi);
        if covers(mid) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    if lo <= 0.0 {
        return None;
    }
    let s = Similarity::from_params(SimilarityParams {
        ax: 0.0,
        ay: 0.0,
        g: lo - 1.0,
        rot: 0.0,
    });
    let warps: Vec<FrameWarp> = map
        .warps()
        .iter()
        .map(|f| match f {
            FrameWarp::Placed(t) => FrameWarp::Placed(s.then(*t)),
            FrameWarp::Refused(why) => FrameWarp::Refused(why.clone()),
        })
        .collect();
    let mut prov = map.provenance().clone();
    prov.note = format!("{} | fit-to-cover k={lo:.6}", prov.note);
    Some((WarpMap::new(prov, geom, map.resampler(), warps), lo))
}
