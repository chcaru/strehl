//! M123c — does the low-pass variance propagation hold on **real** pixels?
//!
//! Run:
//! ```text
//! cargo run --release -p strehl-cli --example m123-null-radius
//! ```
//!
//! **Reads only.**
//!
//! # The discrepancy this exists to chase
//!
//! `m123-outlier-real` measures `LowFreq` firing on **97.55%** of `foam` tiles.
//! Fact 1189 prices `foam`'s motion contamination at **4.78% of output pixels**.
//! Those are different quantities — per-tile firing against per-output-pixel
//! after election — so they are not required to match. They *are* required to be
//! reconcilable, and a 20x gap is not.
//!
//! The same run also measures `LowFreq` firing on **59.29% of a flat-field
//! pair**: same scene, same focus, no motion, nothing but real sensor noise.
//! That is the tell. An arm with a 59% false-positive floor on pure noise cannot
//! have its 97.55% on `foam` read as motion detection.
//!
//! # The measurement
//!
//! `outlier.rs` divides the predicted variance by `m = (2r+1)^2` and divides
//! `N_eff` by the same `m`, on the reasoning that box-averaging `m` **independent**
//! samples reduces the noise variance by `m`. Under that model `chi2` is
//! **1.0 at every radius**, and the module documents the failure mode of getting
//! it wrong in one direction (forget the division and `chi2` reads `1/m`,
//! "silently inert").
//!
//! Real pixels are not independent. The green luma is `0.5*(G1+G2)`, the lens
//! PSF correlates neighbours, and PRNU is fixed pattern. If neighbouring samples
//! are correlated, box-averaging reduces the variance by **less** than `m`,
//! the divided prediction is too small, and `chi2` reads **high** — the opposite
//! failure from the one the module guards.
//!
//! So sweeping `r` on a pure-noise null is a direct, falsifiable test with a
//! flat prediction: **`chi2(r) = 1` for all `r`**. Any monotone growth measures
//! the correlation the model does not represent, and does it on the one input
//! where there is no scene, no focus difference and no motion to argue about.
//!
//! This is the test AGENTS rule 34 says a plant can never perform: M97r's
//! synthetic scene drew independent samples from an `Rng`, so it satisfies the
//! independence assumption **by construction** and reads 1.0 at every radius no
//! matter how wrong the assumption is about real sensors.

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

const CROP: usize = 1024;
const PAIRS: usize = 4;

/// Radii swept. `0` is `Discriminator::Raw` (`m = 1`), the anchor where the
/// module and reality already agree (`mean chi2 = 1.038`, M123 fact M1).
const RADII: [usize; 7] = [0, 1, 2, 3, 4, 6, 12];

fn load(path: &Path) -> Result<(Vec<f32>, PlaneGeometry, NoiseModel)> {
    let frame =
        strehl_raw::decode(path).with_context(|| format!("decoding {}", path.display()))?;
    let geom = frame.geometry();
    let levels = frame.levels;
    let noise = profile::noise_model_for(&frame.camera, frame.iso, levels);
    let mut luma = vec![0.0f32; geom.pixels()];
    let mut clipped = vec![false; geom.pixels()];
    green_luma_with_clip(&frame, levels.black, CONTAINER_MAX_DN, &mut luma, &mut clipped);
    let (x0, y0) = ((geom.width - CROP) / 2, (geom.height - CROP) / 2);
    let mut out = vec![0.0f32; CROP * CROP];
    for row in 0..CROP {
        let src = (y0 + row) * geom.width + x0;
        out[row * CROP..(row + 1) * CROP].copy_from_slice(&luma[src..src + CROP]);
    }
    Ok((
        out,
        PlaneGeometry {
            width: CROP,
            height: CROP,
        },
        noise,
    ))
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

fn stats(v: &[f32]) -> (f64, f64) {
    if v.len() < 2 {
        return (f64::NAN, f64::NAN);
    }
    let n = v.len() as f64;
    let m = v.iter().map(|x| f64::from(*x)).sum::<f64>() / n;
    let sd = (v
        .iter()
        .map(|x| (f64::from(*x) - m).powi(2))
        .sum::<f64>()
        / (n - 1.0))
        .sqrt();
    (m, sd)
}

fn main() -> Result<()> {
    println!("M123c - low-pass variance propagation against real sensor noise");
    println!("crop {CROP}x{CROP} green luma, tile 32px, k=6, {PAIRS} adjacent pairs per stack");
    println!("MODEL PREDICTION: mean chi2 = 1.000 at EVERY radius, on a pure-noise null.");
    println!("Predicted null sd = sqrt(2/N_eff) = sqrt(2*m/1024).\n");

    for (label, dir) in [
        ("flat-null [PURE NOISE]", r"D:\personal\macro\flat-fields\flat-fields"),
        ("109MSDCF [TRAP]", r"D:\personal\macro\109MSDCF"),
        ("foam [MOTION]", r"D:\personal\macro\foam"),
    ] {
        let d = Path::new(dir);
        if !d.exists() {
            println!("{label} MISSING");
            continue;
        }
        let paths = arws(d)?;
        if paths.len() < 2 {
            bail!("{dir} has {} ARW", paths.len());
        }
        let n = PAIRS.min(paths.len() - 1);
        println!("-- {label}");
        println!(
            "{:>3} {:>6} {:>11} {:>10} {:>10} {:>9} {:>9}",
            "r", "m", "mean chi2", "obs sd", "pred sd", "sd ratio", "fire%"
        );
        println!("{}", "-".repeat(64));

        for r in RADII {
            let disc = if r == 0 {
                Discriminator::Raw
            } else {
                Discriminator::LowFreq
            };
            let m = if r == 0 { 1.0 } else { ((2 * r + 1) * (2 * r + 1)) as f64 };
            let params = Params {
                tile: 32,
                blur_radius: r,
                threshold_k: 6.0,
            };
            let mut all: Vec<f32> = Vec::new();
            let (mut fired, mut total) = (0usize, 0usize);
            for i in 0..n {
                let (a, geom, noise) = load(&paths[i])?;
                let (b, _, _) = load(&paths[i + 1])?;
                let mut sc = Scratch::new(geom);
                let c = chi2_map(&a, &b, geom, &noise, params, disc, &mut sc);
                let t = thresholds(geom, params, disc);
                let msk = mask(&c, &t);
                fired += msk.iter().filter(|b| **b).count();
                total += msk.len();
                all.extend(c.iter().copied().filter(|v| *v > 0.0));
            }
            let (mean, sd) = stats(&all);
            let pred_sd = (2.0 * m / 1024.0).sqrt();
            println!(
                "{r:>3} {m:>6.0} {mean:>11.3} {sd:>10.4} {pred_sd:>10.4} {:>8.2}x {:>8.2}%",
                sd / pred_sd,
                fired as f64 / total as f64 * 100.0
            );
        }
        println!();
    }

    // ---- ADVERSARIAL CHECK ON MY OWN COMMITTED FACT M2 ---------------------
    //
    // `m123-outlier-real` reported the flat-field null at r=0 with an across-tile
    // sd of 0.1247 against a predicted 0.0442, and I published that 2.82x as
    // fact M2: "N_eff is overstated 7.96x, k=6 is really 2.13 true sigma".
    //
    // The sweep above measures the SAME quantity as 0.0438 against 0.0442 -
    // 0.99x, dead on. Both cannot be right. The difference between the runs is
    // that the sweep pools 4 pairs and the original pooled 8.
    //
    // If each pair carries its own coherent DC offset, then pooling pairs mixes
    // several distributions with different MEANS, and the pooled sd picks up the
    // between-pair spread on top of the within-pair spread. That would make the
    // 2.82x an artefact of my own pooling, not a property of the sensor - and
    // fact M2 would be wrong and would have to be retracted.
    //
    // Decide it by reporting the within-pair sd separately from the pooled one.
    println!("-- flat-null r=0: is my committed fact M2 (null sd 2.82x too wide) an artefact?");
    let paths = arws(Path::new(r"D:\personal\macro\flat-fields\flat-fields"))?;
    let params = Params {
        tile: 32,
        blur_radius: 0,
        threshold_k: 6.0,
    };
    let pred = (2.0f64 / 1024.0).sqrt();
    let mut pooled: Vec<f32> = Vec::new();
    let mut per_pair_means: Vec<f64> = Vec::new();
    println!(
        "{:>5} {:>10} {:>10} {:>10} {:>9}",
        "pair", "mean chi2", "within sd", "pred sd", "ratio"
    );
    println!("{}", "-".repeat(50));
    for i in 0..8.min(paths.len() - 1) {
        let (a, geom, noise) = load(&paths[i])?;
        let (b, _, _) = load(&paths[i + 1])?;
        let mut sc = Scratch::new(geom);
        let c = chi2_map(&a, &b, geom, &noise, params, Discriminator::Raw, &mut sc);
        let v: Vec<f32> = c.iter().copied().filter(|x| *x > 0.0).collect();
        let (m, sd) = stats(&v);
        println!(
            "{i:>5} {m:>10.4} {sd:>10.4} {pred:>10.4} {:>8.2}x",
            sd / pred
        );
        per_pair_means.push(m);
        pooled.extend(v);
    }
    let (pm, psd) = stats(&pooled);
    let (bm, bsd) = stats(
        &per_pair_means
            .iter()
            .map(|x| *x as f32)
            .collect::<Vec<f32>>(),
    );
    println!("{}", "-".repeat(50));
    println!(
        "POOLED over all pairs      : mean {pm:.4}  sd {psd:.4}  = {:.2}x predicted",
        psd / pred
    );
    println!(
        "BETWEEN-pair spread of means: mean {bm:.4}  sd {bsd:.4}  = {:.2}x predicted",
        bsd / pred
    );
    println!("  If the within-pair ratios are ~1x and the between-pair sd is large,");
    println!("  fact M2's 2.82x was MY POOLING, not the sensor, and M2 must be retracted.\n");

    // ---- the foam reconciliation, in the denominator that makes it readable --
    //
    // A tile fires if motion touches ANY part of its 32x32 = 1024 pixels, so a
    // per-tile rate is an upper bound on a per-pixel rate. Fact 1189's 4.78% is
    // per output pixel after election; this is per tile, per adjacent pair.
    //
    // The claim under test is NOT "does 4.35% match 4.78%". It is: does the
    // per-tile rate measure MOTION at all, or does it merely report how many
    // tiles Lucas-Kanade could resolve? If `fired / resolvable` is ~99% on the
    // MOVING stack AND on the STILL one, the answer is the latter, the rate is
    // set by abstention rather than by motion, and any agreement with 4.78% is
    // numerology.
    println!("-- reconciliation: is the per-tile rate motion, or just the abstention?");
    println!(
        "{:>18} {:>11} {:>11} {:>9} {:>16}",
        "stack", "resolvable%", "gated%", "fired/res", "ground truth"
    );
    println!("{}", "-".repeat(70));
    for (label, dir, truth) in [
        ("109MSDCF", r"D:\personal\macro\109MSDCF", "STILL (trap)"),
        ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles", "MOVING"),
        ("foam", r"D:\personal\macro\foam", "MOVING 4.78%"),
    ] {
        let d = Path::new(dir);
        if !d.exists() {
            continue;
        }
        let paths = arws(d)?;
        let params = Params::default();
        let (mut gated, mut resolvable, mut total) = (0usize, 0usize, 0usize);
        for i in 0..PAIRS.min(paths.len() - 1) {
            let (a, geom, noise) = load(&paths[i])?;
            let (b, _, _) = load(&paths[i + 1])?;
            let grid = TileGrid::new(geom, params.tile);
            let tiles = shift_tiles(&a, &b, geom, &noise, params, true);
            let g = mask_tiles(&tiles, DEFAULT_MIN_SHIFT_PX, params.threshold_k);
            gated += g.iter().filter(|b| **b).count();
            resolvable += tiles
                .iter()
                .filter(|t| {
                    t.informative
                        && t.sigma_px.is_finite()
                        && t.sigma_px * RESOLUTION_MARGIN <= DEFAULT_MIN_SHIFT_PX
                })
                .count();
            total += grid.len();
        }
        println!(
            "{label:>18} {:>10.2}% {:>10.2}% {:>8.1}% {truth:>16}",
            resolvable as f64 / total as f64 * 100.0,
            gated as f64 / total as f64 * 100.0,
            if resolvable == 0 {
                f64::NAN
            } else {
                gated as f64 / resolvable as f64 * 100.0
            }
        );
    }
    println!("\n  If fired/res is ~99% on BOTH the still and the moving stacks, the mask");
    println!("  is not measuring motion - it reports the resolvable fraction, and its");
    println!("  proximity to fact 1189's 4.78% on foam is coincidence, not agreement.");
    Ok(())
}

