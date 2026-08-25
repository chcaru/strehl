//! BUILD-SHARP (b) — the ACTUAL per-frame residual alignment error, measured
//! on the owner's real subjects, in the gauge the merge consumes.
//!
//! # Why this exists
//!
//! Every headline alignment number in the corpus (6.76 px held-out, 13.578,
//! 40.3) is an **end-to-end** figure: the worst corner displacement between
//! the first and last frame of the bracket. The merge does not consume that.
//! The merge gathers each frame through **its own placement** and then chooses
//! between neighbours pixel by pixel. What softens or doubles an edge is the
//! disagreement between the frames that actually get chosen next to each
//! other, which is a **per-frame** quantity (AGENTS rule 6; M103 amendment).
//!
//! # The statistic
//!
//! For a span `s`, take frames `i` and `i+s`, gather **both through their own
//! solved placements** into the reference grid, and then re-run the project's
//! own pairwise estimator on the two gathered planes. If the solve were exact,
//! the estimator would return the identity. What it returns instead is the
//! residual, and it is reported the way every other alignment number in this
//! project is reported: worst-corner displacement in plane px.
//!
//! This reuses `align_pair` rather than writing a new correlator, so it
//! inherits M86's validated estimator, its outlier pass and its tile census.
//! A private correlator would be a fifth instrument nobody has nulled.
//!
//! # Controls (both required, both printed)
//!
//! * `--control none` gathers with the **identity** placement — i.e. it
//!   measures the raw, unregistered drift. This must read LARGE. If it does
//!   not, the instrument has no power on this subject and the treatment number
//!   means nothing.
//! * `--control self` gathers frame `i` twice through its own placement and
//!   estimates the residual between the result and itself. This must read
//!   EXACTLY zero. It catches a gather that silently drops or shifts data.
//!
//! Both are printed beside the treatment in the same table (rule 5: report the
//! raw statistic next to every excess-over-control).
//!
//! # What it cannot tell you
//!
//! Defocus is not neutral. Between two frames a long span apart the subject
//! genuinely changes appearance, and a correlator asked to match a sharp edge
//! to a blurred one can report a shift that is real image motion, not a solve
//! error. That is why `--spans` defaults to the SHORT spans: at span 1 the two
//! frames differ by one focus step and the appearance change is minimal, so
//! the residual is almost entirely placement error. The long spans are printed
//! for completeness and should be read as an upper bound.
//!
//! ```text
//! cargo run --release -p strehl-cli --example bs_residual -- <DIR> --sidecar <PATH> [--spans 1,2,4] [--limit N]
//! ```

use std::path::PathBuf;

use anyhow::{Context, Result, bail};
use rayon::prelude::*;
use strehl_core::align::{
    AlignConfig, AlignFrame, AlignPyramid, PlaneRef, Resampler, Similarity, corner_radius,
    gather_into, tile_grid,
};
use strehl_core::plane::{PlaneGeometry, green_luma};
use strehl_core::warpmap::WarpMap;

struct Frame {
    plane: Vec<f32>,
    geom: PlaneGeometry,
}

fn decode(path: &std::path::Path) -> Result<Frame> {
    let f = strehl_raw::decode(path).with_context(|| format!("decode {}", path.display()))?;
    let geom = PlaneGeometry::from_active(f.active.width, f.active.height);
    let mut plane = vec![0.0f32; geom.pixels()];
    green_luma(&f, f.levels.black, &mut plane);
    Ok(Frame { plane, geom })
}

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let dir = PathBuf::from(args.next().context("usage: bs_residual <DIR> --sidecar <PATH>")?);
    let mut sidecar: Option<PathBuf> = None;
    let mut spans: Vec<usize> = vec![1, 2, 4, 8];
    let mut limit: usize = usize::MAX;
    let mut control = String::from("all");
    while let Some(a) = args.next() {
        match a.as_str() {
            "--sidecar" => sidecar = Some(PathBuf::from(args.next().context("--sidecar")?)),
            "--spans" => {
                spans = args
                    .next()
                    .context("--spans")?
                    .split(',')
                    .map(|s| s.trim().parse::<usize>())
                    .collect::<Result<_, _>>()?
            }
            "--limit" => limit = args.next().context("--limit")?.parse()?,
            "--control" => control = args.next().context("--control")?,
            other => bail!("unknown argument {other}"),
        }
    }
    let sidecar = sidecar.context("--sidecar is required")?;

    let map = WarpMap::load(&sidecar).with_context(|| format!("load {}", sidecar.display()))?;
    println!("sidecar   : {}", sidecar.display());
    println!("frames    : {}", map.len());
    println!("resampler : {:?}", map.resampler());

    let mut paths: Vec<PathBuf> = std::fs::read_dir(&dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    paths.sort();
    paths.truncate(limit.min(map.len()));
    let n = paths.len();
    println!("decoding  : {n} frames from {}", dir.display());

    let frames: Vec<Frame> = paths
        .par_iter()
        .map(|p| decode(p))
        .collect::<Result<Vec<_>>>()?;
    let geom = frames[0].geom;
    println!("geometry  : {} x {} plane px", geom.width, geom.height);
    println!("corner r  : {:.1} plane px\n", corner_radius(geom));

    let cfg = AlignConfig::deep();
    let resampler = Resampler::CatmullRom;

    // gather every frame once, through its own placement, and (for the control
    // arm) through the identity.
    let gather = |warped: bool| -> Vec<Vec<f32>> {
        frames
            .par_iter()
            .enumerate()
            .map(|(k, f)| {
                let mut dst = vec![0.0f32; geom.pixels()];
                let t = if warped {
                    map.placement(k).unwrap_or(Similarity::IDENTITY)
                } else {
                    Similarity::IDENTITY
                };
                gather_into(
                    PlaneRef::new(&f.plane, f.geom.width, f.geom.height).unwrap(),
                    t,
                    geom,
                    resampler,
                    &mut dst,
                );
                dst
            })
            .collect()
    };

    let arms: Vec<(&str, Vec<Vec<f32>>)> = match control.as_str() {
        "none" => vec![("UNALIGNED (control)", gather(false))],
        "warp" => vec![("aligned (treatment)", gather(true))],
        _ => vec![
            ("aligned (treatment)", gather(true)),
            ("UNALIGNED (control)", gather(false)),
        ],
    };

    let spots = tile_grid(
        PlaneRef::new(&arms[0].1[0], geom.width, geom.height).unwrap(),
        cfg.fine_tile,
        cfg.fine_grid.0,
        cfg.fine_grid.1,
        cfg.margin.max(cfg.fine_tile),
    )
    .context("tile_grid")?;
    println!("tiles     : {} per pair\n", spots.len());

    println!(
        "{:>22} {:>5} {:>6} {:>10} {:>10} {:>10} {:>10} {:>8}",
        "arm", "span", "pairs", "mean_px", "median_px", "p90_px", "max_px", "used"
    );

    for (label, planes) in &arms {
        for &s in &spans {
            if s >= n {
                continue;
            }
            let pyr: Vec<AlignPyramid> = planes
                .par_iter()
                .map(|p| AlignPyramid::build(PlaneRef::new(p, geom.width, geom.height).unwrap(), &cfg).unwrap())
                .collect();
            let mut errs: Vec<f64> = Vec::new();
            let mut used_tot = 0usize;
            let mut att = 0usize;
            let results: Vec<Option<(f64, usize)>> = (0..n.saturating_sub(s))
                .into_par_iter()
                .map(|i| {
                    let a = AlignFrame {
                        plane: PlaneRef::new(&planes[i], geom.width, geom.height).unwrap(),
                        pyramid: &pyr[i],
                    };
                    let b = AlignFrame {
                        plane: PlaneRef::new(&planes[i + s], geom.width, geom.height).unwrap(),
                        pyramid: &pyr[i + s],
                    };
                    match strehl_core::align::align_pair(a, b, &spots, &cfg) {
                        Ok(fit) => Some((fit.similarity().corner_err(Similarity::IDENTITY, geom), fit.used)),
                        Err(_) => None,
                    }
                })
                .collect();
            for r in results {
                att += 1;
                if let Some((e, u)) = r {
                    errs.push(e);
                    used_tot += u;
                }
            }
            if errs.is_empty() {
                println!("{label:>22} {s:>5} {att:>6}    all pairs failed to correlate");
                continue;
            }
            errs.sort_by(|a, b| a.partial_cmp(b).unwrap());
            let mean = errs.iter().sum::<f64>() / errs.len() as f64;
            let med = errs[errs.len() / 2];
            let p90 = errs[(errs.len() as f64 * 0.9) as usize % errs.len()];
            let max = *errs.last().unwrap();
            println!(
                "{:>22} {:>5} {:>6} {:>10.4} {:>10.4} {:>10.4} {:>10.4} {:>8.1}",
                label,
                s,
                errs.len(),
                mean,
                med,
                p90,
                max,
                used_tot as f64 / errs.len() as f64
            );
        }
    }

    // The self control: a frame against itself must read exactly zero. If it
    // does not, the estimator has a bias and every number above is offset by
    // it.
    let planes = &arms[0].1;
    let pyr0 = AlignPyramid::build(
        PlaneRef::new(&planes[0], geom.width, geom.height).unwrap(),
        &cfg,
    )
    .unwrap();
    let a = AlignFrame {
        plane: PlaneRef::new(&planes[0], geom.width, geom.height).unwrap(),
        pyramid: &pyr0,
    };
    let b = AlignFrame {
        plane: PlaneRef::new(&planes[0], geom.width, geom.height).unwrap(),
        pyramid: &pyr0,
    };
    match strehl_core::align::align_pair(a, b, &spots, &cfg) {
        Ok(f) => println!(
            "\nself control (frame 0 vs itself, must be 0): {:.6} plane px",
            f.similarity().corner_err(Similarity::IDENTITY, geom)
        ),
        Err(e) => println!("\nself control FAILED: {e:?}"),
    }
    Ok(())
}
