//! Times the shipped focus measure against the box-window radius, to show the
//! cost is flat in it.
//!
//! ```text
//! cargo run --release --example focus-window-cost -p strehl-core
//! ```
//!
//! M13 §5 measured 2.53% spread over `w1-w40` on real 109MSDCF tiles and
//! concluded "a wide window is free", which is the entire reason `w13` could be
//! adopted over M11's `w5` without a cost argument. That result holds **only**
//! because `box_mean` is a separable running sum, O(1) per pixel in the radius.
//! A naive `(2w+1)^2` gather at radius 13 would be 841x the taps and the
//! measured spread would be a factor of tens, not 2.53%.
//!
//! This is a measurement, not an assertion. It prints; it does not judge. A
//! timing threshold in the test suite would ratchet the runner rather than the
//! code (SYNTHESIS §5 item 6).

use std::time::Instant;

use strehl_core::boxfilter::box_mean;
use strehl_core::focus::{FocusField, WINDOW_RADIUS, gradient_magnitude};
use strehl_core::noise::{Levels, NoiseModel, PlaneNoise, Provenance};
use strehl_core::plane::PlaneGeometry;

const RADII: [usize; 7] = [0, 1, 5, 13, 20, 30, 40];
const SWEEPS: usize = 9;

fn main() {
    // 0.353 Mpx, the tile size M13's cost table used.
    let geom = PlaneGeometry {
        width: 768,
        height: 460,
    };
    let px = geom.pixels();
    let mpx = px as f64 / 1e6;
    let reps = 40;

    let luma: Vec<f32> = (0..px)
        .map(|i| {
            let (x, y) = ((i % geom.width) as f32, (i / geom.width) as f32);
            3000.0
                + 600.0 * (x * 1.61).sin() * (y * 1.37).cos()
                + 300.0 * (x * 0.53 - y * 0.71).sin()
        })
        .collect();

    let plane = PlaneNoise {
        gain_dn_per_e: 0.229,
        read_noise_e: 1.47,
        levels: Levels {
            black: 512.0,
            white: 15360.0,
        },
    };
    let noise = NoiseModel::new([plane; 4], 100.0, Provenance::Profile);

    let mut grad = vec![0.0f32; px];
    let mut scratch = vec![0.0f32; px];
    let mut out = vec![0.0f32; px];

    // Untimed passes, so the first row does not pay for cold pages.
    for _ in 0..4 {
        gradient_magnitude(&luma, geom, &mut grad);
        box_mean(&grad, geom, WINDOW_RADIUS, &mut scratch, &mut out);
    }

    println!("{px} px ({mpx:.3} Mpx), {reps} reps per timing, {SWEEPS} sweeps\n");
    println!(
        "{:>7}  {:>7}  {:>10}  {:>10}  {:>10}",
        "radius", "window", "min", "median", "mean focus"
    );

    // Interleaved sweeps, alternating direction, reporting the per-radius
    // minimum. One sweep in one direction cannot separate "cost rises with the
    // radius" from "the machine got slower while I measured": on this box a
    // single forward sweep read as -0.7% across w1-w30 and a single reverse
    // sweep as +19% over the same rows. The minimum is the right estimator
    // because contention only ever adds time.
    let mut time_at = |radius: usize| -> (f64, f64) {
        let t = Instant::now();
        for _ in 0..reps {
            gradient_magnitude(&luma, geom, &mut grad);
            if radius == 0 {
                out.copy_from_slice(&grad);
            } else {
                box_mean(&grad, geom, radius, &mut scratch, &mut out);
            }
            for (o, l) in out.iter_mut().zip(&luma) {
                *o /= noise.green_luma_sigma(*l).max(1e-3);
            }
        }
        let ms = t.elapsed().as_secs_f64() * 1e3 / reps as f64 / mpx;
        let mean: f64 = out.iter().map(|v| *v as f64).sum::<f64>() / px as f64;
        (ms, mean)
    };

    let mut samples: Vec<Vec<f64>> = vec![Vec::new(); RADII.len()];
    let mut means = [0.0f64; RADII.len()];
    let mut shipped_samples: Vec<f64> = Vec::new();
    let mut field = FocusField::new(geom);
    for _ in 0..4 {
        field.compute(&luma, &noise);
    }
    for sweep in 0..SWEEPS {
        for i in 0..RADII.len() {
            let i = if sweep % 2 == 0 {
                i
            } else {
                RADII.len() - 1 - i
            };
            let (ms, mean) = time_at(RADII[i]);
            samples[i].push(ms);
            means[i] = mean;
        }
        // Interleaved with the sweep, not appended after it: run last, on this
        // box, it reads ~20% slow purely because the core has been at load for
        // a minute by then.
        let t = Instant::now();
        for _ in 0..reps {
            field.compute(&luma, &noise);
        }
        shipped_samples.push(t.elapsed().as_secs_f64() * 1e3 / reps as f64 / mpx);
    }

    let mut timings: Vec<(usize, f64)> = Vec::new();
    for (i, radius) in RADII.iter().enumerate() {
        samples[i].sort_by(f64::total_cmp);
        let min = samples[i][0];
        let median = samples[i][SWEEPS / 2];
        println!(
            "{radius:>7}  {:>7}  {min:>10.4}  {median:>10.4}  {:>10.4}",
            2 * radius + 1,
            means[i]
        );
        if *radius > 0 {
            timings.push((*radius, min));
        }
    }

    let lo = timings
        .iter()
        .copied()
        .fold((0usize, f64::MAX), |a, b| if b.1 < a.1 { b } else { a });
    let hi = timings
        .iter()
        .copied()
        .fold((0usize, 0.0f64), |a, b| if b.1 > a.1 { b } else { a });
    println!(
        "\nspread over the windowed radii: {:.2}%  (min {:.4} at w{}, max {:.4} at w{})",
        100.0 * (hi.1 - lo.1) / lo.1,
        lo.1,
        lo.0,
        hi.1,
        hi.0
    );
    println!(
        "rule: 100 * (max - min) / min over the per-radius minimum column, windowed rows only."
    );
    println!("M13 §5 measured 2.53% over w1-w40 with its own harness on real RAW.");
    println!(
        "w1-w13, the range this milestone actually moves through: {:.2}%",
        100.0 * (timings[2].1 - timings[0].1).abs() / timings[0].1.min(timings[2].1)
    );

    // The shipped path, for scale. Same work as the w13 row, timed inside the
    // same sweeps, so the two are comparable.
    let shipped = shipped_samples.iter().copied().fold(f64::MAX, f64::min);
    println!(
        "\nFocusField::compute (the shipped w{WINDOW_RADIUS} path): {shipped:.4} ms/frame/Mpx"
    );
}
