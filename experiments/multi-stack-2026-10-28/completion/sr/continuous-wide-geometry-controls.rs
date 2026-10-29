//! Predeclared46quad/3grid continuous geometry information arm at insect DN.
//! Original failed discrete-peak baseline remains separately bound.
//! Original signal is synthetic; camera levels/noise are bound to the ROI02 receipt.
#![allow(dead_code)]
#[path = "local-registration-continuous.rs"]
mod local_registration;
#[path = "measured-trajectory-01.rs"]
mod measured;
fn main() {}
#[cfg(test)]
mod controls {
    use super::{local_registration::*, measured::MEASURED};
    use std::f64::consts::TAU;
    use strehl_core::{
        align::{Cx, Similarity},
        noise::{Levels, PlaneNoise},
        plane::{PlaneGeometry, QuadSource},
    };
    struct Raw {
        data: Vec<u16>,
        stride: usize,
    }
    impl QuadSource for Raw {
        fn geometry(&self) -> PlaneGeometry {
            PlaneGeometry {
                width: 256,
                height: 256,
            }
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let i = (2 * y + 3) * self.stride + 5;
            (
                &self.data[i..i + 512],
                &self.data[i + self.stride..i + self.stride + 512],
            )
        }
    }
    fn pulls() -> Vec<Similarity> {
        MEASURED
            .iter()
            .map(|(_, bits)| {
                let p = bits.map(f64::from_bits);
                Similarity {
                    a: Cx::new(p[0], p[1]),
                    b: Cx::new(p[2], p[3]),
                }
            })
            .collect()
    }
    fn scene(x: f64, y: f64, color: usize, high: bool) -> f64 {
        let base = 6000.
            + 900. * (0.121 * x + 0.071 * y).sin()
            + 1100. * (-0.085 * x + 0.143 * y).cos()
            + 450. * (0.233 * x - 0.189 * y).sin();
        if !high {
            return base;
        }
        // This carrier exceeds each red/blue CFA plane's .25 cycle/sensor
        // Nyquist. It is still present in the original CFA data and cannot be
        // treated as a common interpolated texture for registration.
        let carrier = 2800. * (TAU * (0.35 * x + 0.12 * y) + color as f64 * 1.1).sin();
        let colored_edge = 350. * (0.08 * (x - 0.7 * y - 70. - 15. * color as f64)).tanh();
        base + carrier + colored_edge
    }
    fn raw(t: Similarity, f: &dyn Fn(f64, f64, usize) -> f64) -> Raw {
        let stride = 523;
        let mut r = Raw {
            data: vec![65535; stride * 520],
            stride,
        };
        for y in 0..512 {
            for x in 0..512 {
                let color = match (x % 2, y % 2) {
                    (0, 0) => 0,
                    (1, 1) => 2,
                    _ => 1,
                };
                // Independent inverse in absolute sensor coordinates, including
                // the measured full-guide center and nonzero scale/rotation.
                let dx = x as f64 - 256.5 - 2. * t.b.re;
                let dy = y as f64 - 256.5 - 2. * t.b.im;
                let det = t.a.re * t.a.re + t.a.im * t.a.im;
                let px = 256.5 + (t.a.re * dx + t.a.im * dy) / det;
                let py = 256.5 + (-t.a.im * dx + t.a.re * dy) / det;
                r.data[(y + 3) * stride + x + 5] =
                    (512. + f(px, py, color)).round().clamp(0., 65535.) as u16;
            }
        }
        r
    }
    fn view(r: &Raw, i: usize, t: Similarity) -> OriginalView<'_> {
        OriginalView {
            acquisition_id: MEASURED[i].0 as u64,
            source: r,
            color_pulls: [t; 3],
            noise: [PlaneNoise {
                gain_dn_per_e: 0.01,
                read_noise_e: 20.,
                levels: Levels {
                    black: 512.,
                    white: 15360.,
                },
            }; 4],
            gain: 1.,
            frozen_expected_rgb: [6000.; 3],
        }
    }
    fn window() -> Window {
        Window {
            full: PlaneGeometry {
                width: 256,
                height: 256,
            },
            center_sensor: [256.5, 256.5],
            side_quad: 192,
        }
    }
    fn raw_policy() -> Policy {
        Policy {
            tile_quad: 46,
            grid_axis: 3,
            ..Policy::default()
        }
    }
    fn lowpass() -> Policy {
        Policy {
            geometry_lowpass_sigma_quad: 1.2,
            ..raw_policy()
        }
    }
    #[test]
    fn a01_flat_and_one_axis_refuse_with_and_without_geometry_filter() {
        let p = pulls();
        let scenes: [&dyn Fn(f64, f64, usize) -> f64; 2] = [&|_, _, _| 6000., &|x, _, _| {
            6000. + 1000. * (x * 0.16).sin()
        }];
        for f in scenes {
            let a = raw(p[0], f);
            let b = raw(p[1], f);
            for policy in [raw_policy(), lowpass()] {
                for c in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
                    let e =
                        measure_pair(&view(&a, 0, p[0]), &view(&b, 1, p[1]), window(), c, policy)
                            .unwrap();
                    assert!(
                        !e.saved_map_supported && !e.refined_map_supported,
                        "{c:?} sigma{} {e:?}",
                        policy.geometry_lowpass_sigma_quad
                    );
                }
            }
        }
    }
    #[test]
    fn b01_measured_high_frequency_alias_bias_is_removed_from_geometry_objective() {
        let p = pulls();
        let r: Vec<_> = p
            .iter()
            .map(|t| raw(*t, &|x, y, c| scene(x, y, c, true)))
            .collect();
        let pairs: Vec<_> = (0..6)
            .map(|i| (i, i + 1))
            .chain((7..13).map(|i| (i, i + 1)))
            .chain([(3, 10)])
            .collect();
        let mut raw_refused = 0;
        let mut filtered_max = 0f64;
        let mut raw_max = 0f64;
        for (i, j) in pairs {
            for c in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
                let a = view(&r[i], i, p[i]);
                let b = view(&r[j], j, p[j]);
                let unfiltered = measure_pair(&a, &b, window(), c, raw_policy()).unwrap();
                raw_refused += usize::from(!unfiltered.saved_map_supported);
                raw_max = raw_max.max(unfiltered.maximum_saved_disagreement_sensor);
                let filtered = measure_pair(&a, &b, window(), c, lowpass()).unwrap();
                filtered_max = filtered_max.max(filtered.maximum_saved_disagreement_sensor);
                assert!(
                    filtered.saved_map_supported,
                    "measured sources{},{} {c:?}: {filtered:?}",
                    MEASURED[i].0, MEASURED[j].0
                );
            }
        }
        assert!(
            raw_refused >= 4,
            "raw alias foil only refused {raw_refused}/39"
        );
        eprintln!(
            "known truth high-bandwidth: raw refused {raw_refused}/39; raw maximum {raw_max:.6}, filtered maximum {filtered_max:.6} sensor pixels; unchanged .15 bound"
        );
    }
    #[test]
    fn b02_lowpass_signal_remains_a_geometry_positive_not_a_detail_gain() {
        let p = pulls();
        let a = raw(p[3], &|x, y, c| scene(x, y, c, false));
        let b = raw(p[10], &|x, y, c| scene(x, y, c, false));
        for c in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
            let e = measure_pair(
                &view(&a, 3, p[3]),
                &view(&b, 10, p[10]),
                window(),
                c,
                lowpass(),
            )
            .unwrap();
            assert!(e.saved_map_supported, "{c:?} {e:?}");
        }
    }
    #[test]
    fn c01_filtered_wrong_placement_clip_and_inconsistent_motion_still_refuse() {
        let p = pulls();
        let a = raw(p[0], &|x, y, c| scene(x, y, c, true));
        let scenes: [&dyn Fn(f64, f64, usize) -> f64; 3] = [
            &|x, y, c| scene(x, y, c, true),
            &|_, _, _| 16000.,
            &|x, y, c| scene(x + if y > 256. { 1.8 } else { -1.8 }, y, c, true),
        ];
        for (i, f) in scenes.iter().enumerate() {
            let b = raw(p[1], *f);
            let mut reported = p[1];
            if i == 0 {
                reported.b.re += 0.35;
                reported.b.im -= 0.2;
            }
            let e = measure_pair(
                &view(&a, 0, p[0]),
                &view(&b, 1, reported),
                window(),
                PlaneKind::Red,
                lowpass(),
            )
            .unwrap();
            assert!(!e.saved_map_supported, "foil {i}: {e:?}");
        }
    }
    // Bound measured guide means: ROI02 report SHA256 8283759f82cff345be9c493b99285e87942a0120b16657686a5c31901c899ab4
    const ACTUAL_MEAN: [f32; 3] = [182.8062286376953, 564.7222290039062, 213.28857421875];
    fn actual_noise() -> [PlaneNoise; 4] {
        [PlaneNoise {
            gain_dn_per_e: 0.22893773,
            read_noise_e: 4.2,
            levels: Levels {
                black: 512.,
                white: 15360.,
            },
        }; 4]
    }
    fn independent_uniform(mut x: u64) -> f64 {
        x = x.wrapping_add(0x9e3779b97f4a7c15);
        x = (x ^ (x >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
        x = (x ^ (x >> 27)).wrapping_mul(0x94d049bb133111eb);
        x ^= x >> 31;
        ((x >> 40) as f64 / 16777216.) * 2. - 1.
    }
    fn actual_raw(t: Similarity, acquisition: usize, seed: usize, flat: bool) -> Raw {
        let stride = 523;
        let mut out = Raw {
            data: vec![65535; stride * 520],
            stride,
        };
        for y in 0..512 {
            for x in 0..512 {
                let color = match (x % 2, y % 2) {
                    (0, 0) => 0,
                    (1, 1) => 2,
                    _ => 1,
                };
                let dx = x as f64 - 256.5 - 2. * t.b.re;
                let dy = y as f64 - 256.5 - 2. * t.b.im;
                let det = t.a.re * t.a.re + t.a.im * t.a.im;
                let px = 256.5 + (t.a.re * dx + t.a.im * dy) / det;
                let py = 256.5 + (-t.a.im * dx + t.a.re * dy) / det;
                let signal = if flat {
                    ACTUAL_MEAN[color]
                } else {
                    (scene(px, py, color, true) / 6000.) as f32 * ACTUAL_MEAN[color]
                };
                let sigma = f64::from(actual_noise()[0].variance(signal)).sqrt();
                let key = (seed as u64)
                    .wrapping_mul(0x79cf1b9)
                    .wrapping_add((acquisition as u64).wrapping_mul(0x5717a299))
                    .wrapping_add((y * 512 + x) as u64);
                let v = 512. + f64::from(signal) + 3f64.sqrt() * sigma * independent_uniform(key);
                out.data[(y + 3) * stride + x + 5] = v.round().clamp(0., 65535.) as u16;
            }
        }
        out
    }
    fn actual_view(raw: &Raw, i: usize, t: Similarity) -> OriginalView<'_> {
        OriginalView {
            noise: actual_noise(),
            frozen_expected_rgb: ACTUAL_MEAN,
            ..view(raw, i, t)
        }
    }
    #[test]
    fn a00_actual_dn_injected_noise_matches_flat_sensor_model_first() {
        let r = actual_raw(Similarity::IDENTITY, 0, 29, true);
        for color in 0..3 {
            let mut sum = 0f64;
            let mut squares = 0f64;
            let mut count = 0usize;
            for y in 16..496 {
                for x in 16..496 {
                    let c = match (x % 2, y % 2) {
                        (0, 0) => 0,
                        (1, 1) => 2,
                        _ => 1,
                    };
                    if c != color {
                        continue;
                    }
                    let v = f64::from(r.data[(y + 3) * r.stride + x + 5]) - 512.;
                    sum += v;
                    squares += v * v;
                    count += 1;
                }
            }
            let mean = sum / count as f64;
            let variance = (squares - sum * sum / count as f64) / (count - 1) as f64;
            let expected = f64::from(actual_noise()[0].variance(ACTUAL_MEAN[color]));
            assert!((mean - f64::from(ACTUAL_MEAN[color])).abs() < 0.15);
            assert!(
                (variance / expected - 1.).abs() < 0.025,
                "color{color}: observed{variance} expected{expected}"
            );
        }
    }
    #[test]
    fn d01_actual_signal_and_independent_noise_commission_the_fixed_geometry_bar() {
        let p = pulls();
        let pairs = [(3, 4), (9, 10), (3, 10)];
        let mut passed = [0usize; 3];
        let mut finite = [0usize; 3];
        let mut maximum = [0f64; 3];
        for seed in 0..4 {
            for (i, j) in pairs {
                let a = actual_raw(p[i], i, seed, false);
                let b = actual_raw(p[j], j, seed, false);
                for (c, color) in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue]
                    .into_iter()
                    .enumerate()
                {
                    let e = measure_pair(
                        &actual_view(&a, i, p[i]),
                        &actual_view(&b, j, p[j]),
                        window(),
                        color,
                        lowpass(),
                    )
                    .unwrap();
                    passed[c] += usize::from(e.saved_map_supported);
                    finite[c] += usize::from(e.maximum_saved_disagreement_sensor.is_finite());
                    maximum[c] = maximum[c].max(e.maximum_saved_disagreement_sensor);
                }
            }
        }
        eprintln!(
            "actual-DN known-truth commissioning: RGB supported {passed:?}/12 each, finite {finite:?}, maximum heldout sensor error {maximum:?}; same .15 bound, no re-estimated sensor noise"
        );
        assert!(
            passed.iter().all(|n| *n > 0),
            "instrument never supports accurate low-DN placement in at least one color: {passed:?}"
        );
    }
    #[test]
    fn d02_actual_level_noise_does_not_certify_wrong_saved_placement() {
        let p = pulls();
        let a = actual_raw(p[3], 3, 31, false);
        let b = actual_raw(p[4], 4, 31, false);
        let mut wrong = p[4];
        wrong.b.re += 0.35;
        wrong.b.im -= 0.2;
        for color in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
            let e = measure_pair(
                &actual_view(&a, 3, p[3]),
                &actual_view(&b, 4, wrong),
                window(),
                color,
                lowpass(),
            )
            .unwrap();
            assert!(!e.saved_map_supported, "{color:?}: {e:?}");
        }
    }
    #[test]
    fn e01_wrong_correspondence_with_preserved_cfa_colors_is_not_a_certificate() {
        let p = pulls();
        let a = actual_raw(p[3], 3, 177, false);
        let mut b = actual_raw(p[4], 4, 179, false);
        let old = b.data.clone();
        for y in 0..256 {
            for x in 0..256 {
                let sx = (x * 73 + 17) % 256;
                let sy = (y * 53 + 11) % 256;
                for dy in 0..2 {
                    for dx in 0..2 {
                        b.data[(2 * y + 3 + dy) * b.stride + 2 * x + 5 + dx] =
                            old[(2 * sy + 3 + dy) * b.stride + 2 * sx + 5 + dx];
                    }
                }
            }
        }
        for color in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
            let e = measure_pair(
                &actual_view(&a, 3, p[3]),
                &actual_view(&b, 4, p[4]),
                window(),
                color,
                lowpass(),
            )
            .unwrap();
            assert!(
                !e.saved_map_supported && !e.refined_map_supported,
                "wrong correspondence {color:?}: {e:?}"
            );
        }
    }
    #[test]
    fn e02_new_noise_seeds_check_conditional_subpixel_bias_and_useful_acceptance() {
        let p = pulls();
        let pairs = [(3, 4), (9, 10), (3, 10)];
        let mut passed = [0usize; 3];
        let mut seeds = Vec::new();
        for seed in 16..32 {
            let mut sums = [[0f64; 2]; 3];
            let mut counts = [0usize; 3];
            for (i, j) in pairs {
                let a = actual_raw(p[i], i, seed, false);
                let b = actual_raw(p[j], j, seed, false);
                for (c, color) in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue]
                    .into_iter()
                    .enumerate()
                {
                    let e = measure_pair(
                        &actual_view(&a, i, p[i]),
                        &actual_view(&b, j, p[j]),
                        window(),
                        color,
                        lowpass(),
                    )
                    .unwrap();
                    passed[c] += usize::from(e.saved_map_supported);
                    for held in &e.heldout_tiles {
                        for axis in 0..2 {
                            sums[c][axis] += held.saved_error_anchor_sensor[axis];
                        }
                        counts[c] += 1;
                    }
                }
            }
            assert!(
                counts.iter().all(|&n| n >= 4),
                "seed{seed} lacks independent measurable structure"
            );
            seeds.push(std::array::from_fn::<_, 3, _>(|c| {
                sums[c].map(|v| v / counts[c] as f64)
            }));
        }
        let mut means = [[0.; 2]; 3];
        let mut errors = [[0.; 2]; 3];
        for c in 0..3 {
            for axis in 0..2 {
                let mean = seeds.iter().map(|s| s[c][axis]).sum::<f64>() / seeds.len() as f64;
                let variance = seeds
                    .iter()
                    .map(|s| (s[c][axis] - mean).powi(2))
                    .sum::<f64>()
                    / (seeds.len() - 1) as f64;
                means[c][axis] = mean;
                errors[c][axis] = (variance / seeds.len() as f64).sqrt();
                // Seed is the independent statistical unit; correlated patches and
                // shared acquisitions within a seed are never counted as replicas.
                assert!(
                    mean.abs() <= 0.03 + 4. * errors[c][axis],
                    "noise/selection bias color{c} axis{axis}: mean{mean} se{}",
                    errors[c][axis]
                );
            }
        }
        eprintln!(
            "new independent seeds16..31: supportedRGB {passed:?}/48, mean consuming errors {means:?}, seed-standard-errors {errors:?}; conditional/adaptive statistic, not calibration"
        );
        assert!(
            passed.iter().all(|&n| n >= 24),
            "most accurate placements unavailable in a color: {passed:?}"
        );
    }
}
