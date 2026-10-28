// Independent control fixtures, included by align_cmd::cfa_lattice_tests.
// No environment mutation. Run the single suite with --test-threads=1.
use strehl_core::align::{PlaneRef, Resampler};
use strehl_core::cfa_lattice::ActiveCfa;
use strehl_core::demosaic::{Mosaic, demosaic_malvar_row};
use strehl_core::noise::{Levels, PlaneNoise};
use strehl_core::pyramid::{BandMerge, FrameWorkspace, MergeConfig, Workspace, level_sizes};

const BLACK: f32 = 512.0;
const SW: usize = 128;
const SH: usize = 128;
const W: usize = 64;
const H: usize = 64;
fn channel(x: usize, y: usize) -> usize {
    if y % 2 == 0 && x % 2 == 0 {
        0
    } else if y % 2 == 1 && x % 2 == 1 {
        2
    } else {
        1
    }
}
fn encoded(v: f32) -> u16 {
    (v + BLACK).round().clamp(0.0, 65535.0) as u16
}
fn source(f: impl Fn(usize, f32, f32) -> f32) -> Vec<u16> {
    (0..SW * SH)
        .map(|i| f(channel(i % SW, i / SW), (i % SW) as f32, (i / SW) as f32))
        .map(encoded)
        .collect()
}
fn malvar(data: &[f32], width: usize, height: usize) -> Vec<f32> {
    let m = Mosaic {
        data,
        width,
        height,
    };
    let mut rgb = vec![0.0; width * height * 3];
    for y in 0..height {
        demosaic_malvar_row(&m, y, &mut rgb[y * width * 3..(y + 1) * width * 3]);
    }
    rgb
}
fn source_planes(raw: &[u16]) -> [Vec<f32>; 3] {
    let mosaic: Vec<f32> = raw.iter().map(|v| *v as f32 - BLACK).collect();
    let rgb = malvar(&mosaic, SW, SH);
    std::array::from_fn(|c| rgb.chunks_exact(3).map(|p| p[c]).collect())
}
#[derive(Clone, Copy)]
struct Pull {
    dx: f32,
    dy: f32,
    scale: f32,
    angle: f32,
}
impl Pull {
    fn at(self, x: f32, y: f32) -> (f32, f32) {
        let (s, c) = self.angle.sin_cos();
        let xx = x - 32.0;
        let yy = y - 32.0;
        (
            64.0 + self.scale * (c * xx - s * yy) + self.dx,
            64.0 + self.scale * (s * xx + c * yy) + self.dy,
        )
    }
}
fn render(raw: &[u16], pull: Pull, direct: bool) -> Vec<f32> {
    let lattice = ActiveCfa::new(raw, SW, 0, 0, SW, SH).unwrap();
    let reconstructed = (!direct).then(|| source_planes(raw));
    let mut mosaic = vec![0.0; W * H];
    for y in 0..H {
        for x in 0..W {
            let ch = channel(x, y);
            let (sx, sy) = pull.at(x as f32, y as f32);
            let sample = if direct {
                lattice.sample_checked(ch, sx as f64, sy as f64).unwrap() - BLACK
            } else {
                let plane = PlaneRef::new(&reconstructed.as_ref().unwrap()[ch], SW, SH).unwrap();
                Resampler::CatmullRom
                    .sample_checked(plane, sx as f64, sy as f64)
                    .unwrap()
            };
            // Match the quantizing CFA sink; these bounded controls never clip.
            mosaic[y * W + x] = encoded(sample) as f32 - BLACK;
        }
    }
    mosaic
}

// Independent scalar convolution oracle: piecewise Keys kernel evaluated by
// distance rather than reusing the implementation's cubic weight vector.
fn keys(t: f64) -> f64 {
    let a = t.abs();
    if a < 1.0 {
        1.5 * a.powi(3) - 2.5 * a.powi(2) + 1.0
    } else if a < 2.0 {
        -0.5 * a.powi(3) + 2.5 * a.powi(2) - 4.0 * a + 2.0
    } else {
        0.0
    }
}
fn independent_taps(ch: usize, x: f64, y: f64) -> Vec<(usize, usize, f64)> {
    let (u, v) = if ch == 1 {
        ((x + y - 1.0) / 2.0, (x - y - 1.0) / 2.0)
    } else {
        let phase = if ch == 2 { 1.0 } else { 0.0 };
        ((x - phase) / 2.0, (y - phase) / 2.0)
    };
    let mut out = Vec::new();
    for j in (v.floor() as isize - 1)..=(v.floor() as isize + 2) {
        for i in (u.floor() as isize - 1)..=(u.floor() as isize + 2) {
            let weight = keys(u - i as f64) * keys(v - j as f64);
            if weight == 0.0 {
                continue;
            }
            let (xx, yy) = if ch == 1 {
                (i + j + 1, i - j)
            } else {
                let phase = if ch == 2 { 1 } else { 0 };
                (2 * i + phase, 2 * j + phase)
            };
            assert!(xx >= 0 && yy >= 0 && xx < SW as isize && yy < SH as isize);
            out.push((xx as usize, yy as usize, weight));
        }
    }
    out
}
struct Rng(u64);
impl Rng {
    fn uniform(&mut self) -> f32 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (((self.0 >> 40) as f32) + 0.5) / 16777216.0
    }
    fn normal(&mut self) -> f32 {
        let u = self.uniform();
        (-2.0 * u.ln()).sqrt() * (std::f32::consts::TAU * self.uniform()).cos()
    }
}
fn flat_noise_first() {
    // One injected manufactured model. This tests propagation, not camera calibration.
    let model = PlaneNoise {
        gain_dn_per_e: 0.25,
        read_noise_e: 4.0,
        levels: Levels {
            black: BLACK,
            white: 15360.0,
        },
    };
    let probes: Vec<(usize, f64, f64)> = (0..3)
        .flat_map(|c| (0..4).map(move |j| (c, 20.25 + 24.0 * j as f64, 30.375 + 17.0 * c as f64)))
        .collect();
    for dc in [1000.0_f32, 4096.0] {
        let sigma = model.sigma(dc);
        let predicted: Vec<f64> = probes
            .iter()
            .map(|(c, x, y)| {
                let taps = independent_taps(*c, *x, *y);
                assert!((taps.iter().map(|t| t.2).sum::<f64>() - 1.0).abs() < 1e-12);
                // Include u16 quantization variance; its independence is approximate.
                taps.iter().map(|t| t.2 * t.2).sum::<f64>()
                    * (model.variance(dc) as f64 + 1.0 / 12.0)
            })
            .collect();
        let mut sums = vec![0.0; probes.len()];
        let mut sums2 = vec![0.0; probes.len()];
        let repeats = 384;
        let mut rng = Rng(0x71234b9a);
        for _ in 0..repeats {
            let raw: Vec<u16> = (0..SW * SH)
                .map(|_| encoded(dc + sigma * rng.normal()))
                .collect();
            let lattice = ActiveCfa::new(&raw, SW, 0, 0, SW, SH).unwrap();
            for (j, (c, x, y)) in probes.iter().enumerate() {
                let v = lattice.sample_checked(*c, *x, *y).unwrap() as f64 - (dc + BLACK) as f64;
                sums[j] += v;
                sums2[j] += v * v;
            }
        }
        let n = repeats as f64;
        let ratios: Vec<f64> = (0..probes.len())
            .map(|j| (sums2[j] - sums[j] * sums[j] / n) / (n - 1.0) / predicted[j])
            .collect();
        let mean = ratios.iter().sum::<f64>() / ratios.len() as f64;
        println!(
            "CFA_CONTROL flat dc={dc} repeats={repeats} probes={} empirical_over_independent_expected={mean:.6} individual={ratios:?}",
            probes.len()
        );
        assert!(
            (mean - 1.0).abs() < 0.12,
            "flat noise transport mismatch: {mean}"
        );
        // A deliberately omitted interpolation attenuation must disagree.
        let attenuation = predicted.iter().sum::<f64>()
            / predicted.len() as f64
            / (model.variance(dc) as f64 + 1.0 / 12.0);
        assert!(
            attenuation < 0.85,
            "flat foil failed to exercise noninteger resampling"
        );
    }
}
fn identity_affine_and_support() {
    let raw = source(|c, x, y| 1000.0 + 1500.0 * c as f32 + 2.0 * x + 3.0 * y);
    // Embed the active image in deliberately poisonous non-active padding.
    let (stride, ax, ay) = (SW + 13, 5, 3);
    let mut padded = vec![u16::MAX; stride * (SH + 8)];
    for y in 0..SH {
        padded[(y + ay) * stride + ax..(y + ay) * stride + ax + SW]
            .copy_from_slice(&raw[y * SW..(y + 1) * SW]);
    }
    let a = ActiveCfa::new(&padded, stride, ax, ay, SW, SH).unwrap();
    let frozen = padded.clone();
    for y in 0..SH {
        for x in 0..SW {
            assert_eq!(
                a.sample_checked(channel(x, y), x as f64, y as f64),
                Some(raw[y * SW + x] as f32)
            );
        }
    }
    for ch in 0..3 {
        for (x, y) in [(21.25, 34.375), (60.5, 72.75), (98.875, 24.25)] {
            let v = a.sample_checked(ch, x, y).unwrap();
            let truth = BLACK + 1000.0 + 1500.0 * ch as f32 + 2.0 * x as f32 + 3.0 * y as f32;
            assert!(
                (v - truth).abs() < 0.003,
                "affine channel{ch} {v} != {truth}"
            );
            let oracle = independent_taps(ch, x, y)
                .iter()
                .map(|(xx, yy, w)| raw[yy * SW + xx] as f64 * w)
                .sum::<f64>();
            assert!((v as f64 - oracle).abs() < 0.003);
        }
    }
    // Wrong-colour/phase foil must be observably wrong, not silently accepted.
    let good = a.sample_checked(0, 60.25, 60.375).unwrap();
    let wrong = a.sample_checked(2, 60.25, 60.375).unwrap();
    assert!((wrong - good).abs() > 2500.0);
    assert!(a.sample_checked(3, 30.0, 30.0).is_none());
    for ch in 0..3 {
        for (x, y) in [
            (f64::NAN, 20.0),
            (20.0, f64::INFINITY),
            (-10.0, 20.0),
            (20.0, -10.0),
            (200.0, 20.0),
        ] {
            assert!(a.sample_checked(ch, x, y).is_none());
        }
    }
    assert_eq!(padded, frozen, "sampler altered immutable sensor input");
    println!("CFA_CONTROL identity affine wrong_phase padding invalid_support PASS");
}
fn diagnostics() {
    // Frozen, no tuning after results. 0.30 can exceed R/B native Nyquist;
    // report the limitation rather than require impossible universal dominance.
    let pulls = [
        Pull {
            dx: 0.25,
            dy: -0.375,
            scale: 1.0,
            angle: 0.0,
        },
        Pull {
            dx: -0.375,
            dy: 0.25,
            scale: 1.015,
            angle: 1.2_f32.to_radians(),
        },
    ];
    for family in ["neutral", "red-only", "blue-only"] {
        for frequency in [0.08_f32, 0.18, 0.30] {
            for degrees in [0.0_f32, 45.0, 73.0] {
                if family != "neutral" && frequency == 0.30 {
                    continue;
                }
                let (s, c) = degrees.to_radians().sin_cos();
                let scene = |ch: usize, x: f32, y: f32| {
                    let active = family == "neutral"
                        || (family == "red-only" && ch == 0)
                        || (family == "blue-only" && ch == 2);
                    2000.0
                        + if active {
                            300.0
                                * (std::f32::consts::TAU * frequency * (c * x + s * y) + 0.37).sin()
                        } else {
                            0.0
                        }
                };
                let raw = source(scene);
                for (pi, pull) in pulls.iter().copied().enumerate() {
                    let mut outcomes = Vec::new();
                    for direct in [false, true] {
                        let cfa = render(&raw, pull, direct);
                        let rgb = malvar(&cfa, W, H);
                        let mut mse = [0.0_f64; 3];
                        let mut cfa_mse = 0.0;
                        let mut n = 0;
                        for y in 8..H - 8 {
                            for x in 8..W - 8 {
                                let (sx, sy) = pull.at(x as f32, y as f32);
                                for ch in 0..3 {
                                    let e = rgb[3 * (y * W + x) + ch] - scene(ch, sx, sy);
                                    mse[ch] += (e * e) as f64;
                                }
                                let e = cfa[y * W + x] - scene(channel(x, y), sx, sy);
                                cfa_mse += (e * e) as f64;
                                n += 1;
                            }
                        }
                        let rms = mse.map(|v| (v / n as f64).sqrt());
                        let cfa_rms = (cfa_mse / n as f64).sqrt();
                        assert!(rms.iter().all(|x| x.is_finite()));
                        outcomes.push((cfa_rms, rms));
                    }
                    println!(
                        "CFA_CONTROL grating family={family} frequency={frequency} degrees={degrees} pull={pi} off={:?} on={:?}",
                        outcomes[0], outcomes[1]
                    );
                }
            }
        }
    }
    // G1/G2 response differences are not automatically a common green field.
    let raw: Vec<u16> = (0..SW * SH)
        .map(|i| {
            if channel(i % SW, i / SW) == 1 {
                if i / SW % 2 == 0 { 1512 } else { 1612 }
            } else {
                9000
            }
        })
        .collect();
    let a = ActiveCfa::new(&raw, SW, 0, 0, SW, SH).unwrap();
    let values = [(50.0, 51.0), (51.0, 50.0), (50.25, 51.375), (51.25, 50.375)]
        .map(|(x, y)| a.sample_checked(1, x, y).unwrap());
    assert_eq!(values[0], 1612.0);
    assert_eq!(values[1], 1512.0);
    println!(
        "CFA_CONTROL green_phase_imbalance samples={values:?}; no phase-response calibration inferred"
    );
}
fn merge_signal_frames(frames: &[Vec<f32>]) -> Vec<f32> {
    let cfg = MergeConfig::default();
    let sizes = level_sizes(W / 2, H / 2, cfg.bands);
    let mut merge = BandMerge::new(W / 2, H / 2, 4, cfg);
    let mut ws = FrameWorkspace::new(&sizes, 4);
    // Noiseless signal isolation. This does not qualify the warped noise floor.
    let variance = vec![0.0; W * H / 4];
    for frame in frames {
        let planes: [Vec<f32>; 4] = std::array::from_fn(|p| {
            let (dx, dy) = match p {
                0 => (0, 0),
                1 => (1, 0),
                2 => (1, 1),
                _ => (0, 1),
            };
            (0..W * H / 4)
                .map(|i| frame[(2 * (i / (W / 2)) + dy) * W + 2 * (i % (W / 2)) + dx])
                .collect()
        });
        let luma: Vec<f32> = planes[1]
            .iter()
            .zip(&planes[3])
            .map(|(a, b)| (a + b) * 0.5)
            .collect();
        ws.next_frame();
        merge.add_frame(
            &[&planes[0], &planes[1], &planes[2], &planes[3]],
            &luma,
            &variance,
            &mut ws,
        );
    }
    let result = merge.finish(&mut Workspace::new(&sizes));
    let mut out = vec![0.0; W * H];
    for y in 0..H {
        for x in 0..W {
            let p = match (x % 2, y % 2) {
                (0, 0) => 0,
                (1, 0) => 1,
                (1, 1) => 2,
                _ => 3,
            };
            out[y * W + x] = result[p][(y / 2) * (W / 2) + x / 2];
        }
    }
    out
}
fn weak_single_frame_line() {
    let angle = 73.0_f32.to_radians();
    let (s, c) = angle.sin_cos();
    let line = |x: f32, y: f32, sigma: f32| {
        let d = c * (x - 32.0) + s * (y - 32.0);
        // Flux-preserving Gaussian defocus, maximum 100 DN at sigma0.65.
        2000.0 + 100.0 * 0.65 / sigma * (-0.5 * (d / sigma).powi(2)).exp()
    };
    let mut off = Vec::new();
    let mut on = Vec::new();
    for (sigma, dx, dy) in [
        (2.0, 0.25, -0.375),
        (0.65, -0.375, 0.25),
        (3.0, 0.375, 0.125),
    ] {
        let pull = Pull {
            dx,
            dy,
            scale: 1.0,
            angle: 0.0,
        };
        let raw = source(|_, x, y| line(x - 32.0 - dx, y - 32.0 - dy, sigma));
        off.push(render(&raw, pull, false));
        on.push(render(&raw, pull, true));
    }
    let mut scores = Vec::new();
    for frames in [&off, &on] {
        let cfa = merge_signal_frames(frames);
        let rgb = malvar(&cfa, W, H);
        let mut errors = [0.0_f64; 3];
        let mut peaks = [f32::NEG_INFINITY; 3];
        let mut n = 0;
        for y in 8..H - 8 {
            for x in 8..W - 8 {
                let truth = line(x as f32, y as f32, 0.65);
                for ch in 0..3 {
                    let value = rgb[3 * (y * W + x) + ch];
                    let e = value - truth;
                    errors[ch] += (e * e) as f64;
                    peaks[ch] = peaks[ch].max(value - 2000.0);
                }
                n += 1;
            }
        }
        scores.push((errors.map(|x| (x / n as f64).sqrt()), peaks));
    }
    println!(
        "CFA_CONTROL weak_single_sharp_frame actual_band_merge_noiseless off={:?} on={:?}",
        scores[0], scores[1]
    );
    assert!(
        scores
            .iter()
            .all(|(_, p)| p.iter().all(|v| v.is_finite() && *v > 1.0)),
        "fixture has no surviving weak line"
    );
}
#[test]
fn cfa_lattice_independent_suite() {
    flat_noise_first();
    identity_affine_and_support();
    diagnostics();
    weak_single_frame_line();
}
