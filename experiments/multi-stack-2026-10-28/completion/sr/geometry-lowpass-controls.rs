//! Root-scheduled geometry-only low-pass controls. No photographed inputs.
#![allow(dead_code)]
#[path = "local-registration.rs"]
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
    fn lowpass() -> Policy {
        Policy {
            geometry_lowpass_sigma_quad: 1.2,
            ..Policy::default()
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
            for policy in [Policy::default(), lowpass()] {
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
                let unfiltered = measure_pair(&a, &b, window(), c, Policy::default()).unwrap();
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
}
