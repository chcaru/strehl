//! M123 — does the outlier mask survive contact with real captures?
//!
//! Run:
//! ```text
//! cargo run --release -p strehl-cli --example m123-outlier-real -- --out C:\dev\strehl-out\M123
//! ```
//!
//! **Reads only.** Nothing is written to `D:\`.
//!
//! # What this measures, and what it deliberately does not
//!
//! The question is **not** "does `LowFreq` separate motion from defocus". That
//! is closed: `outlier.rs` marks the arm a MEASURED FAILURE, carries a named
//! regression test for it, and M97r W3 derives why it must fail at every
//! radius — box-averaging divides the noise variance by `m` while an extended
//! defocus residual survives, and the statistic is their ratio, which is
//! independent of the filter radius. `LowFreq` runs here only as an inertness
//! control so the negative is reproducible on real frames.
//!
//! The open question is the one the module names against its own constant:
//! `DEFAULT_MIN_SHIFT_PX` ends "**It has not yet been measured on real frames**".
//! M97r's whole gate configuration was chosen against the four synthetic cases
//! used to report it (M97r §6: "The gate configuration is in-sample"). The
//! corpus is the held-out set.
//!
//! # Why real data is not merely a nicer plant
//!
//! AGENTS rule 34: a plant that supplies its own noise constant cannot detect
//! that constant being wrong. M97r drew its noise from the model and normalised
//! by the same model, so it is scale-invariant in the gain and could not have
//! caught a miscalibration of any size. The `flat-null` and `dark-null` arms
//! here are the only ones in the milestone's history that can falsify the
//! calibration, because their noise comes from photons rather than from `Rng`.
//!
//! # The discriminating pair
//!
//! - `109MSDCF` adjacent frames — focus changes, nothing moves. **TRAP.**
//! - `coffee-bubbles` adjacent frames — focus is constant at 0.2841 m
//!   throughout (`captures-needed.md` line 1264) while bubbles genuinely drift.
//!   **PLANT.** Real subject motion with the defocus confound physically
//!   absent, which is the control no synthetic scene can supply.
//!
//! A trap null means nothing unless `Raw` fires on the same input, so `Raw` is
//! carried through every case as the inertness control (AGENTS rules 11, 20).

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use strehl_core::clip::CONTAINER_MAX_DN;
use strehl_core::noise::NoiseModel;
use strehl_core::outlier::{
    DEFAULT_MIN_SHIFT_PX, Discriminator, Params, RESOLUTION_MARGIN, Scratch, TileGrid,
    chi2_map, mask, mask_tiles, shift_tiles, thresholds,
};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma_with_clip};
use strehl_core::profile;

/// Centred crop of the green-luma plane, in plane pixels.
///
/// Rule 7: the decoded buffer is zero-padded and a statistic over it is dragged
/// toward zero. `green_luma_with_clip` already works in `Frame::geometry()`,
/// which is the active area; cropping to the centre on top of that keeps the
/// measurement clear of the active-area border as well, where `box_mean` clamps
/// its window and understates the variance (`outlier.rs` module docs).
const CROP: usize = 1024;

/// Adjacent pairs per stack. Eight pairs of 1024 tiles is ~8k tile-tests, which
/// resolves the 1% false-positive bar pre-registered in §4.2 with room to spare.
const PAIRS: usize = 8;

/// Planted displacements for the positive control, in plane pixels.
///
/// `0.0` is the placebo — the same pair with no plant, which must not fire.
/// `0.35` is `DEFAULT_MIN_SHIFT_PX` itself, sitting exactly on the bar, so the
/// gate is sampled on both sides of its own threshold rather than only far from
/// it.
const PLANTS: [f32; 6] = [0.0, 0.15, 0.35, 0.5, 1.0, 2.0];

struct Pair {
    a: Vec<f32>,
    b: Vec<f32>,
    geom: PlaneGeometry,
    noise: NoiseModel,
    mean_a: f64,
    mean_b: f64,
}

/// Decode one frame and return its centred green-luma crop.
///
/// The noise model comes from the profile at the frame's own ISO, exactly as
/// `merge_cmd.rs` builds it. It is *injected*, never re-derived here: AGENTS
/// rule 3 names a private per-stage noise estimate as the mechanism behind the
/// prior project's 2-5x defect, and this file's whole claim is that the
/// statistic is normalised by the shipped model.
fn load(path: &Path) -> Result<(Vec<f32>, PlaneGeometry, NoiseModel)> {
    let frame =
        strehl_raw::decode(path).with_context(|| format!("decoding {}", path.display()))?;
    let geom = frame.geometry();
    let levels = frame.levels;
    let noise = profile::noise_model_for(&frame.camera, frame.iso, levels);
    let mut luma = vec![0.0f32; geom.pixels()];
    let mut clipped = vec![false; geom.pixels()];
    green_luma_with_clip(&frame, levels.black, CONTAINER_MAX_DN, &mut luma, &mut clipped);

    if CROP > geom.width || CROP > geom.height {
        bail!(
            "crop {CROP} does not fit in plane {}x{}",
            geom.width,
            geom.height
        );
    }
    let (x0, y0) = ((geom.width - CROP) / 2, (geom.height - CROP) / 2);
    let mut out = vec![0.0f32; CROP * CROP];
    for row in 0..CROP {
        let src = (y0 + row) * geom.width + x0;
        out[row * CROP..(row + 1) * CROP].copy_from_slice(&luma[src..src + CROP]);
    }
    let cropped = PlaneGeometry {
        width: CROP,
        height: CROP,
    };
    Ok((out, cropped, noise))
}

fn mean(v: &[f32]) -> f64 {
    if v.is_empty() {
        return 0.0;
    }
    v.iter().map(|x| f64::from(*x)).sum::<f64>() / v.len() as f64
}

fn pair_from(pa: &Path, pb: &Path) -> Result<Pair> {
    let (a, geom, noise) = load(pa)?;
    let (b, gb, _) = load(pb)?;
    if gb != geom {
        bail!("{} and {} differ in geometry", pa.display(), pb.display());
    }
    let (mean_a, mean_b) = (mean(&a), mean(&b));
    Ok(Pair {
        a,
        b,
        geom,
        noise,
        mean_a,
        mean_b,
    })
}

/// Bilinear translation of a plane by `(dx, dy)`, used only by the positive
/// control.
///
/// Bilinear resampling is itself a mild low-pass, so a planted shift arrives
/// slightly blurred. That biases the recovered magnitude **downward**, which is
/// the conservative direction for a positive control: it can make the gate look
/// worse than it is, never better.
fn shifted(v: &[f32], g: PlaneGeometry, dx: f32) -> Vec<f32> {
    let (w, h) = (g.width, g.height);
    let mut out = vec![0.0f32; w * h];
    let fx = dx.floor();
    let t = dx - fx;
    let i0 = fx as i64;
    for y in 0..h {
        for x in 0..w {
            let sx0 = (x as i64 - i0).clamp(0, w as i64 - 1) as usize;
            let sx1 = (x as i64 - i0 - 1).clamp(0, w as i64 - 1) as usize;
            out[y * w + x] = v[y * w + sx0] * (1.0 - t) + v[y * w + sx1] * t;
        }
    }
    out
}

fn quantile(sorted: &[f32], q: f64) -> f32 {
    if sorted.is_empty() {
        return f32::NAN;
    }
    let i = ((sorted.len() - 1) as f64 * q).round() as usize;
    sorted[i]
}

#[derive(Default, Clone)]
struct Acc {
    chi2: Vec<f32>,
    fired: usize,
    tiles: usize,
    mags: Vec<f32>,
    informative: usize,
    gated: usize,
}

impl Acc {
    fn report(&self, case: &str, arm: &str) {
        let mut s = self.chi2.clone();
        s.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let mean_chi2 = mean(&self.chi2);
        // Observed spread of the statistic across tiles. The module predicts
        // `sqrt(2/N_eff)` and derives `threshold_k` from it, so this column is
        // the one that says whether the threshold means what it claims.
        let sd = if self.chi2.len() < 2 {
            f64::NAN
        } else {
            let n = self.chi2.len() as f64;
            (self
                .chi2
                .iter()
                .map(|v| (f64::from(*v) - mean_chi2).powi(2))
                .sum::<f64>()
                / (n - 1.0))
                .sqrt()
        };
        let mut m = self.mags.clone();
        m.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let fire = if self.tiles == 0 {
            0.0
        } else {
            self.fired as f64 / self.tiles as f64 * 100.0
        };
        let gate = if self.tiles == 0 {
            0.0
        } else {
            self.gated as f64 / self.tiles as f64 * 100.0
        };
        let has_shift = !self.mags.is_empty();
        println!(
            "{case:<14} {arm:<10} {mean_chi2:>9.3} {sd:>9.4} {:>9.3} {:>9.3} {fire:>8.2}% {:>8} {:>9} {:>9}",
            quantile(&s, 0.50),
            quantile(&s, 0.999),
            if has_shift {
                format!("{gate:.2}%")
            } else {
                "-".into()
            },
            if has_shift {
                format!("{:.4}", mean(&self.mags))
            } else {
                "-".into()
            },
            if has_shift {
                format!("{:.4}", quantile(&m, 0.999))
            } else {
                "-".into()
            },
        );
    }
}

fn run_arm(p: &Pair, params: Params, disc: Discriminator, acc: &mut Acc) {
    let mut sc = Scratch::new(p.geom);
    let c = chi2_map(&p.a, &p.b, p.geom, &p.noise, params, disc, &mut sc);
    let t = thresholds(p.geom, params, disc);
    let m = mask(&c, &t);
    acc.fired += m.iter().filter(|b| **b).count();
    acc.tiles += m.len();
    acc.chi2.extend(c.iter().copied().filter(|v| *v > 0.0));

    if matches!(disc, Discriminator::Shift | Discriminator::ShiftFree) {
        let tiles = shift_tiles(
            &p.a,
            &p.b,
            p.geom,
            &p.noise,
            params,
            disc == Discriminator::ShiftFree,
        );
        let g = mask_tiles(&tiles, DEFAULT_MIN_SHIFT_PX, params.threshold_k);
        acc.gated += g.iter().filter(|b| **b).count();
        acc.informative += tiles.iter().filter(|t| t.informative).count();
        acc.mags.extend(
            tiles
                .iter()
                .filter(|t| t.informative)
                .map(|t| (t.sx * t.sx + t.sy * t.sy).sqrt()),
        );
    }
}

fn arws(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("listing {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .is_some_and(|e| e.eq_ignore_ascii_case("ARW"))
        })
        .collect();
    v.sort();
    Ok(v)
}

fn header() {
    println!(
        "{:<14} {:<10} {:>9} {:>9} {:>9} {:>9} {:>9} {:>8} {:>9} {:>9}",
        "case", "arm", "mean", "sd", "p50", "p99.9", "fire%", "gated%", "mean|s|", "p99.9|s|"
    );
    println!("{}", "-".repeat(112));
}

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let mut out = PathBuf::from(r"C:\dev\strehl-out\M123");
    let mut only: Option<String> = None;
    while let Some(a) = args.next() {
        if a == "--out" {
            out = PathBuf::from(args.next().context("--out needs a path")?);
        } else if a == "--only" {
            only = Some(args.next().context("--only needs a case name")?);
        }
    }
    std::fs::create_dir_all(&out).ok();

    let params = Params::default();
    let grid = TileGrid::new(
        PlaneGeometry {
            width: CROP,
            height: CROP,
        },
        params.tile,
    );
    let null_sd = (2.0f64 / f64::from(params.tile as u32 * params.tile as u32)).sqrt();

    println!("M123 - the outlier mask against real captures");
    println!(
        "crop {CROP}x{CROP} green luma, {} tiles of {}px, k={}, blur_radius={}",
        grid.len(),
        params.tile,
        params.threshold_k,
        params.blur_radius
    );
    println!(
        "disagreement bar = 1 + k*sqrt(2/N) = {:.4}   displacement bar = 1 + k = {:.1} on 2 dof",
        1.0 + f64::from(params.threshold_k) * null_sd,
        1.0 + params.threshold_k
    );
    println!(
        "min_shift_px = {DEFAULT_MIN_SHIFT_PX}  resolution_margin = {RESOLUTION_MARGIN}"
    );
    println!("PLANT = must fire   TRAP/NULL = must stay quiet\n");

    // ---- real-capture cases -------------------------------------------------
    let cases: [(&str, &str, &str); 5] = [
        ("flat-null", r"D:\personal\macro\flat-fields\flat-fields", "NULL"),
        ("dark-null", r"D:\macro-dark-frames\118MSDCF", "NULL"),
        ("defocus", r"D:\personal\macro\109MSDCF", "TRAP"),
        ("motion", r"D:\personal\macro\coffee-bubbles", "PLANT"),
        ("foam", r"D:\personal\macro\foam", "PLANT"),
    ];

    header();
    let mut trap_pair: Option<Pair> = None;
    for (name, dir, role) in cases {
        if only.as_deref().is_some_and(|o| o != name) {
            continue;
        }
        let d = Path::new(dir);
        if !d.exists() {
            println!("{name:<14} MISSING {dir}");
            continue;
        }
        let paths = arws(d)?;
        if paths.len() < 2 {
            println!("{name:<14} only {} ARW in {dir}", paths.len());
            continue;
        }
        let n = PAIRS.min(paths.len() - 1);
        let mut accs = [Acc::default(), Acc::default(), Acc::default(), Acc::default()];
        let mut lv = (0.0f64, 0.0f64);
        for i in 0..n {
            let p = pair_from(&paths[i], &paths[i + 1])?;
            lv = (p.mean_a, p.mean_b);
            for (j, disc) in [
                Discriminator::Raw,
                Discriminator::LowFreq,
                Discriminator::Shift,
                Discriminator::ShiftFree,
            ]
            .into_iter()
            .enumerate()
            {
                run_arm(&p, params, disc, &mut accs[j]);
            }
            if name == "defocus" && i == 0 {
                trap_pair = Some(p);
            }
        }
        println!(
            "-- {name} [{role}]  {n} adjacent pairs, mean level {:.1} / {:.1} DN",
            lv.0, lv.1
        );
        for (j, arm) in ["Raw", "LowFreq", "Shift", "ShiftFree"].into_iter().enumerate() {
            accs[j].report(name, arm);
        }
        println!();
    }

    // ---- positive control: a planted translation on a real defocus pair -----
    //
    // The plant rides on `109MSDCF`, so the defocus difference is real and
    // still present underneath the planted motion. A plant on a synthetic
    // scene would remove the very nuisance the gate exists to survive.
    let Some(p) = trap_pair else {
        println!("no trap pair available; positive control skipped");
        return Ok(());
    };
    println!("-- plant [POSITIVE CONTROL] planted translation on a real 109MSDCF defocus pair");
    println!(
        "{:<14} {:<10} {:>9} {:>9} {:>9} {:>9} {:>9} {:>8} {:>9} {:>9}",
        "planted px", "arm", "mean", "sd", "p50", "p99.9", "fire%", "gated%", "mean|s|", "p99.9|s|"
    );
    println!("{}", "-".repeat(112));
    for d in PLANTS {
        let b = shifted(&p.b, p.geom, d);
        let pp = Pair {
            a: p.a.clone(),
            b,
            geom: p.geom,
            noise: p.noise.clone(),
            mean_a: p.mean_a,
            mean_b: p.mean_b,
        };
        let mut acc = Acc::default();
        run_arm(&pp, params, Discriminator::ShiftFree, &mut acc);
        acc.report(&format!("{d:.2}"), "ShiftFree");
    }

    Ok(())
}
