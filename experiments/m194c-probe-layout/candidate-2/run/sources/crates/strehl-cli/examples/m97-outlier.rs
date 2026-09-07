//! M97r — prices the candidate outlier discriminators against each other on
//! synthetic scenes where the ground truth is known by construction.
//!
//! Run: `cargo run --release -p strehl-cli --example m97-outlier`
//!
//! Three scenarios, one per block:
//!
//! - `static`  — same scene, same focus, independent noise. **PLACEBO.** Every
//!   arm must be inert. An arm that fires here is miscalibrated.
//! - `defocus` — same scene, DIFFERENT focus. **The trap.** This is what a
//!   focus stack is made of, and no arm may call it an outlier.
//! - `motion`  — same focus, the scene translated by one pixel. **PLANT.** An
//!   arm that claims to detect motion must fire here, or its `defocus` null is
//!   an inert probe rather than a correct answer.
//!
//! The `defocus` and `motion` blocks together are the whole measurement: an arm
//! is useful only if it separates them. Reporting `mean |s|` in pixels next to
//! the significance is deliberate — a sub-pixel bias can be overwhelmingly
//! significant and still be harmless, and that distinction decides which arm
//! ships.

use strehl_core::boxfilter::box_mean;
use strehl_core::noise::{Levels, NoiseModel, PlaneNoise, Provenance};
use strehl_core::outlier::{
    DEFAULT_MIN_SHIFT_PX, Discriminator, Params, Scratch, TileGrid, chi2_map, fired_fraction,
    mask, mask_tiles, shift_tiles, thresholds,
};
use strehl_core::plane::PlaneGeometry;

const W: usize = 256;
const H: usize = 256;
const SIGMA: f32 = 4.0;

struct Rng(u64);
impl Rng {
    fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    fn unit(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }
    fn normal(&mut self) -> f32 {
        let u1 = self.unit().max(1e-12);
        let u2 = self.unit();
        ((-2.0 * u1.ln()).sqrt() * (std::f64::consts::TAU * u2).cos()) as f32
    }
}

fn model() -> NoiseModel {
    let gain = 1e-6;
    let p = PlaneNoise {
        gain_dn_per_e: gain,
        read_noise_e: SIGMA * std::f32::consts::SQRT_2 / gain,
        levels: Levels {
            black: 0.0,
            white: 16383.0,
        },
    };
    NoiseModel::new([p; 4], 100.0, Provenance::Measured)
}

/// A disc plus a two-axis ripple, so every tile carries gradient in both
/// directions and the displacement arms have something to measure everywhere.
fn scene(dx: f32) -> Vec<f32> {
    let k = std::f32::consts::TAU / 16.0;
    (0..H)
        .flat_map(|y| (0..W).map(move |x| (x, y)))
        .map(|(x, y)| {
            let (fx, fy) = (x as f32 - dx, y as f32);
            let (cx, cy) = (W as f32 / 2.0, H as f32 / 2.0);
            let r = ((fx - cx).powi(2) + (fy - cy).powi(2)).sqrt();
            let base = if r <= 60.0 { 900.0 } else { 200.0 };
            base + 120.0 * ((k * fx).sin() + (k * fy).sin())
        })
        .collect()
}

fn noisy(v: &[f32], seed: u64) -> Vec<f32> {
    let mut r = Rng(seed);
    v.iter().map(|s| s + SIGMA * r.normal()).collect()
}

fn blurred(v: &[f32], g: PlaneGeometry, radius: usize) -> Vec<f32> {
    let mut tmp = vec![0.0; g.pixels()];
    let mut out = vec![0.0; g.pixels()];
    box_mean(v, g, radius, &mut tmp, &mut out);
    out
}

fn main() {
    let g = PlaneGeometry {
        width: W,
        height: H,
    };
    let n = model();
    let p = Params {
        tile: 32,
        blur_radius: 12,
        threshold_k: 6.0,
    };
    let grid = TileGrid::new(g, p.tile);

    let base = scene(0.0);
    // A scene whose contrast is comparable to its own noise. The displacement
    // estimator still runs, but its standard error approaches the pixel bar --
    // this is the case that decides whether the significance gate is doing any
    // work or is merely decorative.
    let k = std::f32::consts::TAU / 16.0;
    let faint: Vec<f32> = (0..H)
        .flat_map(|y| (0..W).map(move |x| (x, y)))
        .map(|(x, y)| 400.0 + 1.5 * ((k * x as f32).sin() + (k * y as f32).sin()))
        .collect();
    let cases: [(&str, Vec<f32>, Vec<f32>); 4] = [
        ("static", noisy(&base, 1), noisy(&base, 2)),
        ("defocus", noisy(&base, 3), noisy(&blurred(&base, g, 3), 4)),
        ("motion", noisy(&base, 5), noisy(&scene(1.0), 6)),
        ("faint", noisy(&faint, 7), noisy(&faint, 8)),
    ];

    println!(
        "M97r discriminator pricing - {W}x{H} plane, {} tiles of {}px, k={}, sigma={SIGMA} DN",
        grid.len(),
        p.tile,
        p.threshold_k
    );
    println!(
        "placebo=static (inert)  trap=defocus (must be inert)  plant=motion (must fire)\n"
    );
    println!(
        "{:<8} {:<10} {:>8} {:>8} {:>10} {:>10} {:>9} {:>5} {:>6}",
        "case", "arm", "chi2only", "gated", "mean chi2", "mean|s|px", "max|s|px", "live", "magonly"
    );
    println!("{}", "-".repeat(84));

    for (name, a, b) in &cases {
        for disc in [
            Discriminator::Raw,
            Discriminator::LowFreq,
            Discriminator::Shift,
            Discriminator::ShiftFree,
        ] {
            let mut sc = Scratch::new(g);
            let mut gated: Option<f64> = None;
            let mut live_tiles = 0usize;
            let mut mag_only = 0usize;
            let c = chi2_map(a, b, g, &n, p, disc, &mut sc);
            let t = thresholds(g, p, disc);
            let fired = fired_fraction(&mask(&c, &t));
            let live: Vec<f32> = c.iter().copied().filter(|v| *v > 0.0).collect();
            let mean = if live.is_empty() {
                0.0
            } else {
                live.iter().sum::<f32>() / live.len() as f32
            };
            let mags: Vec<f32> = match disc {
                Discriminator::Shift | Discriminator::ShiftFree => {
                    let tiles =
                        shift_tiles(a, b, g, &n, p, disc == Discriminator::ShiftFree);
                    gated = Some(fired_fraction(&mask_tiles(
                        &tiles,
                        DEFAULT_MIN_SHIFT_PX,
                        p.threshold_k,
                    )));
                    live_tiles = tiles.iter().filter(|t| t.informative).count();
                    mag_only = tiles
                        .iter()
                        .filter(|t| {
                            t.informative
                                && (t.sx * t.sx + t.sy * t.sy).sqrt() > DEFAULT_MIN_SHIFT_PX
                        })
                        .count();
                    tiles
                        .iter()
                        .filter(|t| t.informative)
                        .map(|t| (t.sx * t.sx + t.sy * t.sy).sqrt())
                        .collect()
                }
                _ => Vec::new(),
            };
            let (mean_s, max_s) = if mags.is_empty() {
                (f32::NAN, f32::NAN)
            } else {
                (
                    mags.iter().sum::<f32>() / mags.len() as f32,
                    mags.iter().copied().fold(0.0f32, f32::max),
                )
            };
            println!(
                "{name:<8} {:<10} {:>7.1}% {:>8} {mean:>10.2} {mean_s:>10.4} {max_s:>9.4} {live_tiles:>5} {mag_only:>6}",
                format!("{disc:?}"),
                fired * 100.0,
                gated.map_or("-".to_string(), |v| format!("{:.1}%", v * 100.0)),
            );
        }
        println!();
    }
}
