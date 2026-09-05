//! M182 shipping-code probe.
//!
//! The primary analysis driver is `../analyze.py`. This binary supplies the
//! parts that must run through production Rust rather than through a Python
//! transcription: `Resampler::sample`, `restore::gather_mtf`,
//! `restore::design_fir`, and `restore::restore_plane`.

use std::f64::consts::PI;

use strehl_core::align::{PlaneRef, Resampler};
use strehl_core::restore::{
    RestoreConfig, design_fir, gather_mtf, restoration_supported, restore_plane, selftest,
};

const KERNELS: [(&str, Resampler); 6] = [
    ("nearest", Resampler::Nearest),
    ("bilinear", Resampler::Bilinear),
    ("catmull-rom", Resampler::CatmullRom),
    ("clamped-catmull-rom", Resampler::ClampedCatmullRom),
    ("lanczos2", Resampler::Lanczos2),
    ("lanczos3", Resampler::Lanczos3),
];

const PHASES: usize = 64;
const CURVE_STEPS: usize = 256;
const N: usize = 512;
const MARGIN: usize = 8;
const W: usize = N + 2 * MARGIN;
const H: usize = 8;
const ROW: f64 = 4.0;
const DENSE_PHASES: usize = 131_072;
const LAMBDAS: [f64; 9] = [0.0, 0.001, 0.01, 0.03, 0.1, 0.15, 0.2, 0.3, 1_000_000.0];

fn offsets(r: Resampler) -> &'static [isize] {
    match r {
        Resampler::Nearest | Resampler::Bilinear => &[0, 1],
        Resampler::CatmullRom | Resampler::ClampedCatmullRom | Resampler::Lanczos2 => {
            &[-1, 0, 1, 2]
        }
        Resampler::Lanczos3 => &[-2, -1, 0, 1, 2, 3],
    }
}

fn cosine_plane(f: f64) -> Vec<f32> {
    let mut plane = vec![0.0f32; W * H];
    for y in 0..H {
        for x in 0..W {
            plane[y * W + x] = (2.0 * PI * f * x as f64).cos() as f32;
        }
    }
    plane
}

fn amplitude(samples: &[f64], f: f64) -> f64 {
    let mut re = 0.0;
    let mut im = 0.0;
    for (i, &v) in samples.iter().enumerate() {
        let theta = 2.0 * PI * f * (MARGIN + i) as f64;
        re += v * theta.cos();
        im += v * theta.sin();
    }
    if f == 0.0 || f == 0.5 {
        re.abs() / samples.len() as f64
    } else {
        2.0 * re.hypot(im) / samples.len() as f64
    }
}

#[derive(Clone, Copy)]
enum Post {
    Identity,
    AddDc,
    Sharpen,
    Blur,
}

fn measured_mtf(r: Resampler, f: f64, post: Post) -> f64 {
    let data = cosine_plane(f);
    let plane = PlaneRef::new(&data, W, H).expect("valid cosine plane");
    let mut total = 0.0;
    for p in 0..PHASES {
        let phi = (p as f64 + 0.5) / PHASES as f64;
        let mut samples = Vec::with_capacity(N);
        for i in 0..N {
            let x = (MARGIN + i) as f64 + phi;
            samples.push(f64::from(r.sample(plane, x, ROW)));
        }
        match post {
            Post::Identity => {}
            Post::AddDc => {
                for v in &mut samples {
                    *v += 137.0;
                }
            }
            Post::Sharpen | Post::Blur => {
                let old = samples.clone();
                for i in 0..N {
                    let left = old[(i + N - 1) % N];
                    let right = old[(i + 1) % N];
                    samples[i] = match post {
                        Post::Sharpen => 1.25 * old[i] - 0.125 * (left + right),
                        Post::Blur => 0.5 * old[i] + 0.25 * (left + right),
                        _ => unreachable!(),
                    };
                }
            }
        }
        total += amplitude(&samples, f);
    }
    total / PHASES as f64
}

fn measured_rms_error(r: Resampler, f: f64) -> f64 {
    let data = cosine_plane(f);
    let plane = PlaneRef::new(&data, W, H).expect("valid cosine plane");
    let mut squared_error = 0.0;
    for p in 0..PHASES {
        let phi = (p as f64 + 0.5) / PHASES as f64;
        for i in 0..N {
            let x = (MARGIN + i) as f64 + phi;
            let got = f64::from(r.sample(plane, x, ROW));
            let want = (2.0 * PI * f * x).cos();
            squared_error += (got - want) * (got - want);
        }
    }
    (squared_error / (PHASES * N) as f64).sqrt()
}

fn tap_probe() {
    let base = 20isize;
    let w = 48usize;
    let h = 8usize;
    let row = 4.0;

    for (name, r) in KERNELS {
        let mut impulse_planes = Vec::new();
        for &offset in offsets(r) {
            let mut data = vec![0.0f32; w * h];
            let col = usize::try_from(base + offset).expect("positive probe column");
            for y in 0..h {
                data[y * w + col] = 1.0;
            }
            impulse_planes.push(data);
        }
        let constant = vec![1.0f32; w * h];
        let constant_plane = PlaneRef::new(&constant, w, h).expect("constant plane");

        let mut min_weight = f64::INFINITY;
        let mut max_negative_mass = 0.0f64;
        let mut max_basis_sum_error = 0.0f64;
        let mut max_constant_dc_error = 0.0f64;
        for i in 0..DENSE_PHASES {
            let phi = i as f64 / DENSE_PHASES as f64;
            let x = base as f64 + phi;
            let mut sum = 0.0;
            let mut negative_mass = 0.0;
            for data in &impulse_planes {
                let plane = PlaneRef::new(data, w, h).expect("impulse plane");
                let value = f64::from(r.sample(plane, x, row));
                min_weight = min_weight.min(value);
                sum += value;
                if value < 0.0 {
                    negative_mass -= value;
                }
            }
            max_negative_mass = max_negative_mass.max(negative_mass);
            max_basis_sum_error = max_basis_sum_error.max((sum - 1.0).abs());
            let dc = f64::from(r.sample(constant_plane, x, row));
            max_constant_dc_error = max_constant_dc_error.max((dc - 1.0).abs());
        }
        println!(
            "T\t{name}\t{min_weight:.12}\t{max_negative_mass:.12}\t\
             {max_basis_sum_error:.12}\t{max_constant_dc_error:.12}"
        );
    }
}

fn patch_plane(kind: &str) -> (Vec<f32>, usize, usize, usize) {
    let w = 40usize;
    let h = 8usize;
    let edge = 20usize;
    let mut data = vec![0.0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            data[y * w + x] = match kind {
                "step" if x >= edge => 1000.0,
                "impulse" if x == edge => 1000.0,
                _ => 0.0,
            };
        }
    }
    (data, w, h, edge)
}

fn patch_overshoot(r: Resampler, kind: &str) -> (f64, f64, f64) {
    let (data, w, h, edge) = patch_plane(kind);
    let plane = PlaneRef::new(&data, w, h).expect("valid patch plane");
    let mut worst = 0.0f64;
    let mut worst_phase = 0.0;
    let mut worst_x = 0.0;
    for i in 0..DENSE_PHASES {
        let phi = i as f64 / DENSE_PHASES as f64;
        for base in (edge - 6)..=(edge + 5) {
            let x = base as f64 + phi;
            let value = f64::from(r.sample(plane, x, ROW));
            let excursion = (-value).max(value - 1000.0).max(0.0);
            if excursion > worst {
                worst = excursion;
                worst_phase = phi;
                worst_x = x;
            }
        }
    }
    (worst, worst_phase, worst_x)
}

fn overshoot_probe() {
    for (name, r) in KERNELS {
        let (step, step_phase, step_x) = patch_overshoot(r, "step");
        let (impulse, impulse_phase, impulse_x) = patch_overshoot(r, "impulse");
        println!(
            "O\t{name}\t{step:.12}\t{step_phase:.12}\t{step_x:.12}\t\
             {impulse:.12}\t{impulse_phase:.12}\t{impulse_x:.12}"
        );
    }
}

fn mtf_probe() {
    for (name, r) in KERNELS {
        println!("P\t{name}\t{}", restoration_supported(r));
    }
    for i in 0..=CURVE_STEPS {
        let f = 0.5 * i as f64 / CURVE_STEPS as f64;
        for (name, r) in KERNELS {
            let model = if restoration_supported(r) {
                format!("{:.12}", gather_mtf(r, f))
            } else {
                "NA".to_owned()
            };
            let empirical = if !restoration_supported(r) || i % 8 == 0 {
                format!("{:.12}", measured_mtf(r, f, Post::Identity))
            } else {
                "NA".to_owned()
            };
            println!("M\t{name}\t{i}\t{f:.12}\t{model}\t{empirical}");
        }
    }
    for (name, r) in KERNELS {
        for index in [64usize, 128, 192] {
            let f = 0.5 * index as f64 / CURVE_STEPS as f64;
            println!(
                "Q\t{name}\t{index}\t{f:.12}\t{:.12}",
                measured_rms_error(r, f)
            );
        }
    }

    let f = 0.375;
    let baseline = measured_mtf(Resampler::Bilinear, f, Post::Identity);
    let inert = measured_mtf(Resampler::Bilinear, f, Post::AddDc);
    let sharpened = measured_mtf(Resampler::Bilinear, f, Post::Sharpen);
    let blurred = measured_mtf(Resampler::Bilinear, f, Post::Blur);
    println!(
        "C\tmtf-direction\t{f:.12}\t{baseline:.12}\t{inert:.12}\t{sharpened:.12}\t{blurred:.12}"
    );
}

fn fir_response(taps: &[f64], f: f64) -> f64 {
    let mut gain = taps[0];
    for (k, &tap) in taps.iter().enumerate().skip(1) {
        gain += 2.0 * tap * (2.0 * PI * f * k as f64).cos();
    }
    gain
}

fn noise_factors(taps: &[f64]) -> (f64, f64) {
    let energy = taps[0] * taps[0] + 2.0 * taps.iter().skip(1).map(|tap| tap * tap).sum::<f64>();
    // One pass: variance multiplies by energy, so SD multiplies by sqrt(E).
    // Two separable passes: variance multiplies by E^2, so SD multiplies by E.
    (energy.sqrt(), energy)
}

fn restoration_probe() {
    for (name, r) in KERNELS {
        if !restoration_supported(r) {
            continue;
        }
        for lambda in LAMBDAS {
            // An exact flat-spectrum controlled input: total autocorrelation
            // r[0] = signal power 1 + noise power lambda, r[k>0] = 0.
            // design_fir subtracts sigma2, recovering S(f) = 1 exactly.
            let mut autocorrelation = vec![0.0f64; 25];
            autocorrelation[0] = 1.0 + lambda;
            let cfg = RestoreConfig {
                resampler: r,
                grid_factor: 1.0,
                sigma2: lambda,
                gain_cap: 4.0,
            };
            let taps = design_fir(&cfg, &autocorrelation, 4);
            let (noise_sd_1d, noise_sd_2d) = noise_factors(&taps);
            let mut min_gain = f64::INFINITY;
            let mut max_gain = f64::NEG_INFINITY;
            for i in 0..=8192 {
                let f = 0.5 * i as f64 / 8192.0;
                let gain = fir_response(&taps, f);
                min_gain = min_gain.min(gain);
                max_gain = max_gain.max(gain);
            }
            let tap_text = taps
                .iter()
                .map(|tap| format!("{tap:.12}"))
                .collect::<Vec<_>>()
                .join(",");
            println!(
                "F\t{name}\t{lambda:.12}\t{noise_sd_1d:.12}\t{noise_sd_2d:.12}\t\
                 {min_gain:.12}\t{max_gain:.12}\t{tap_text}"
            );
            for i in 0..=CURVE_STEPS {
                let f = 0.5 * i as f64 / CURVE_STEPS as f64;
                let h_mtf = gather_mtf(r, f);
                let gain = fir_response(&taps, f);
                println!(
                    "R\t{name}\t{lambda:.12}\t{i}\t{f:.12}\t{h_mtf:.12}\t\
                     {gain:.12}\t{:.12}",
                    h_mtf * gain
                );
            }
        }
    }
}

fn mean_sd_interior(data: &[f32], w: usize, h: usize, margin: usize) -> f64 {
    let mut count = 0usize;
    let mut sum = 0.0;
    for y in margin..(h - margin) {
        for x in margin..(w - margin) {
            sum += f64::from(data[y * w + x]);
            count += 1;
        }
    }
    let mean = sum / count as f64;
    let mut variance = 0.0;
    for y in margin..(h - margin) {
        for x in margin..(w - margin) {
            let d = f64::from(data[y * w + x]) - mean;
            variance += d * d;
        }
    }
    (variance / count as f64).sqrt()
}

fn restoration_apply_control() {
    let w = 512usize;
    let h = 512usize;
    let lambda = 0.1f64;
    let scale = (3.0 * (1.0 + lambda)).sqrt();
    let mut state = 0x4d31_3832_a5a5_5a5au64;
    let mut plane = Vec::with_capacity(w * h);
    for _ in 0..(w * h) {
        // Deterministic xorshift64* uniform white sequence in [-sqrt(3V),sqrt(3V)].
        state ^= state >> 12;
        state ^= state << 25;
        state ^= state >> 27;
        let bits = state.wrapping_mul(0x2545_f491_4f6c_dd1d);
        let unit = (bits >> 11) as f64 / ((1u64 << 53) as f64);
        plane.push(((2.0 * unit - 1.0) * scale) as f32);
    }
    let before = mean_sd_interior(&plane, w, h, 8);
    let cfg = RestoreConfig {
        resampler: Resampler::Bilinear,
        grid_factor: 1.0,
        sigma2: lambda,
        gain_cap: 4.0,
    };
    let report = restore_plane(&mut plane, w, h, &cfg);
    let after = mean_sd_interior(&plane, w, h, 8);
    let (_, predicted_2d) = noise_factors(&report.taps);
    println!(
        "A\trestore-apply\t{lambda:.12}\t{before:.12}\t{after:.12}\t{:.12}\t\
         {predicted_2d:.12}",
        after / before
    );
}

fn main() {
    selftest().expect("production restore::selftest");
    println!(
        "H\tm182-probe-v1\tphases={PHASES}\tcurve_steps={CURVE_STEPS}\t\
         dense_phases={DENSE_PHASES}\tn={N}"
    );
    tap_probe();
    overshoot_probe();
    mtf_probe();
    restoration_probe();
    restoration_apply_control();
    println!("Z\tok");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bilinear_model_has_expected_endpoints() {
        assert_eq!(gather_mtf(Resampler::Bilinear, 0.0), 1.0);
        assert!((gather_mtf(Resampler::Bilinear, 0.5) - 0.5).abs() < 1e-12);
    }

    #[test]
    fn sharpen_and_blur_controls_move_opposite_ways() {
        let f = 0.375;
        let baseline = measured_mtf(Resampler::Bilinear, f, Post::Identity);
        assert!(measured_mtf(Resampler::Bilinear, f, Post::Sharpen) > baseline);
        assert!(measured_mtf(Resampler::Bilinear, f, Post::Blur) < baseline);
        assert!((measured_mtf(Resampler::Bilinear, f, Post::AddDc) - baseline).abs() < 1e-9);
    }

    #[test]
    fn high_noise_flat_spectrum_design_is_identity() {
        let mut autocorrelation = vec![0.0f64; 25];
        autocorrelation[0] = 1_000_001.0;
        let cfg = RestoreConfig {
            resampler: Resampler::Bilinear,
            grid_factor: 1.0,
            sigma2: 1_000_000.0,
            gain_cap: 4.0,
        };
        assert_eq!(
            design_fir(&cfg, &autocorrelation, 4),
            vec![1.0, 0.0, 0.0, 0.0, 0.0]
        );
    }
}
